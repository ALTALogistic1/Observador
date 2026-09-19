"""Connecteur REQ (Registre des entreprises du Québec) — spec section 7, Signal 4,
et section 9 ("Le NEQ comme identifiant pivot").

Double rôle, comme documenté dans registry/sources.yaml :
  1. Base de résolution/vérification pour TOUTES les sources : résoudre un nom
     d'entreprise en NEQ, obtenir adresse/secteur/statut légal (resolve_neq_by_name,
     get_by_neq — appelées par falkye/resolution.py et falkye/verification.py).
  2. Source de signal en soi : nouvel établissement secondaire ou changement
     d'adresse du siège social, détecté en comparant deux rafraîchissements
     successifs du miroir local (REQEntry). Les mises à jour purement
     administratives (aucun changement d'adresse/statut) sont exclues.

STRUCTURE RÉELLE CONFIRMÉE le 2026-08-31 (Alexandre a téléchargé le vrai fichier
depuis son navigateur et inspecté son contenu réel via `import-manuel inspecter`
— voir docs/STATUT_RESEAU.md pour le détail complet) : le fichier en vrac n'est
PAS un CSV plat, c'est une archive de SIX CSV liés entre eux par NEQ :
  - `Entreprise.csv` (~630 Mo) : une ligne par entreprise — NEQ, statut
    (COD_STAT_IMMAT, codes confirmés ci-dessous), secteur/adresse de repli.
  - `Nom.csv` (~280 Mo) : historique des noms par NEQ (plusieurs lignes possibles
    par entreprise) — voir STAT_NOM/TYP_NOM_ASSUJ ci-dessous pour choisir le nom
    légal actuel.
  - `Etablissements.csv` (~35 Mo) : un ou plusieurs établissements par NEQ
    (IND_ETAB_PRINC='O' pour le siège, 'N' pour un établissement secondaire) —
    adresse/secteur les plus fiables, et source du signal "nouvel établissement
    secondaire" (spec section 7, Signal 4).
  - `DomaineValeur.csv` (~90 Ko) : table de décodage code→libellé générique,
    utilisée ici pour confirmer les codes STAT_IMMAT/STAT_NOM/TYP_NOM (les
    descriptions de secteur d'activité sont déjà en texte dans Entreprise.csv/
    Etablissements.csv, pas besoin de décodage supplémentaire).
  - `FusionScissions.csv`, `ContinuationsTransformations.csv` : événements
    corporatifs hors des 5 champs requis par la spec section 7 (NEQ, nom,
    secteur, adresse, statut) — non utilisés pour l'instant.

La vraie jointure (Entreprise.csv + Nom.csv + Etablissements.csv) est
implémentée dans `_ingest_zip_req_reel`/`_upsert_entreprise_reelle` ci-dessous,
routée automatiquement par `ingest_snapshot` quand le fichier importé contient
ces 3 CSV (`FICHIERS_REQ_REELS`). Le chemin "fichier plat" historique
(`_iter_csv_rows`/`_upsert_row`/`COLUMN_ALIASES`) reste en place uniquement pour
(1) le repli réseau `REQConnector.detect` (dormant en Phase 1) et (2) des tests
de mécanique avec un CSV synthétique à une seule table — le vrai fichier REQ ne
passera plus jamais par ce chemin.
"""
from __future__ import annotations

import ast
import csv
import io
import logging
import re
import sys
import zipfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone

from dateutil import parser as dateutil_parser
from rapidfuzz import fuzz, process
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from falkye.diff_engine import (
    LigneSnapshot,
    RapportExecution,
    SpecificationDiff,
    executer_diff_groupe,
    seuils_depuis_registre,
)
from falkye.models.req_entry import REQEntry
from falkye.models.req_nom import REQNom
from falkye.registry.loader import get_registry
from falkye.sources.base import RawSignal, SourceConnector
from falkye.sources.ckan_client import DONNEES_QUEBEC_BASE, CKANClient
from falkye.sources.column_mapping import normaliser as _normaliser
from falkye.sources.column_mapping import resolve_columns

logger = logging.getLogger(__name__)

REQ_PACKAGE_ID = "registre-des-entreprises"

# Les 3 CSV qui portent les champs requis par la spec (NEQ, nom, secteur, adresse,
# statut) — leur présence simultanée dans un .zip déclenche le chemin de jointure
# réelle (_ingest_zip_req_reel) plutôt que le chemin "fichier plat" legacy.
FICHIERS_REQ_REELS = {"Entreprise.csv", "Nom.csv", "Etablissements.csv"}

# --- Chemin "fichier plat" legacy (mécanique/tests + repli réseau dormant) -----
# Ces alias/valeurs étaient des HYPOTHÈSES avant l'inspection réelle du 2026-08-31
# et NE CORRESPONDENT PAS au vrai fichier REQ (qui n'est jamais un CSV plat) —
# gardés seulement pour ne pas casser REQConnector.detect() et les tests de
# mécanique existants. Chaque valeur est une liste de motifs (sous-chaîne,
# insensible à la casse/accents) essayés dans l'ordre contre les en-têtes réelles.
COLUMN_ALIASES: dict[str, list[str]] = {
    "neq": ["neq"],
    "nom": ["nom_assujetti", "nom_entreprise", "nomassujetti", "nom"],
    "statut": ["cod_statut_immat", "statut_immat", "statut"],
    "adresse": ["adr_dom_lig", "adresse_dom", "adresse"],
    "ville": ["adr_dom_vil", "ville_dom", "ville"],
    "code_postal": ["adr_dom_cp", "code_postal", "codepostal"],
    "region": ["adr_dom_reg", "region_adm", "region"],
    "secteur_code": ["cae_princ", "code_secteur", "cae"],
    "secteur_libelle": ["desc_cae_princ", "descr_secteur", "secteur"],
    "date_maj": ["dat_maj", "date_maj", "date_mise_a_jour"],
}

STATUTS_RADIES = {"radiee", "radié", "radiée", "rad", "fermee", "fermée", "dissoute"}


def _parse_statut(raw: str) -> str:
    n = _normaliser(raw or "")
    return "radiee" if n in STATUTS_RADIES else "immatriculee"


# --- Chemin réel (Entreprise.csv + Nom.csv + Etablissements.csv) --------------
# Codes confirmés par inspection réelle de DomaineValeur.csv (TYP_DOM_VAL=
# 'STAT_IMMAT') le 2026-08-31 : IM=Immatriculée, AI=Avis d'intention de
# constitution, NI=Non immatriculée, RD=Radiée sur demande, RO=Radiée d'office,
# RX=Radiée d'office (article 59). Seul RD/RO/RX correspond à la vérification
# obligatoire "radiée" (spec section 6) — AI/NI ne sont ni l'un ni l'autre et
# gardent leur code brut plutôt que d'être devinés vers une catégorie non confirmée.
STATUTS_RADIES_CODES_REELS = {"RD", "RO", "RX"}

# --- Rebranchement sur le moteur de diff générique (Chantier 1, suivi
# 2026-09-04 : « rebrancher REQ en premier ») --------------------------------
# REQ a DEUX grains de diff distincts, jamais fusionnés en un seul appel au
# moteur : le grain ENTREPRISE (registry/sources.yaml:req.champs_pertinents —
# détecte le changement d'adresse du siège) et le grain ÉTABLISSEMENT (interne
# à ce module, pas dans le registre — détecte le nouvel établissement
# secondaire). Ce sont deux partitions indépendantes de falkye/diff_engine.py
# ("req" et "req_etablissements"), chacune avec son propre état et sa propre
# quarantaine — un schéma cassé dans Etablissements.csv seul ne doit jamais
# passer inaperçu simplement parce qu'Entreprise.csv, lui, est intact.
CHAMPS_PERTINENTS_REQ = {"neq", "nom_entreprise", "secteur_activite", "adresses", "statut", "date_derniere_maj"}
CHAMPS_PERTINENTS_REQ_ETABLISSEMENTS = {
    "adresse", "ville", "code_postal", "secteur_libelle", "nom_etablissement", "principal",
}
# "secteur_code" est délibérément EXCLU de l'empreinte comparée par le moteur
# (mais reste capté dans le signal — voir plus bas) : l'ancien miroir bespoke
# REQEtablissementEntry ne l'a jamais stocké, donc l'état migré depuis ce
# miroir (chantier 1, migration plutôt qu'un run de référence) ne pourrait
# jamais le connaître — comparer contre une valeur structurellement absente
# ferait apparaître une "modification" sur la quasi-totalité des
# établissements dès le premier vrai import suivant la migration, un faux
# positif de masse, pas un vrai changement. secteur_libelle (déjà dans
# l'empreinte) porte la même information de façon lisible.


def _decoder_statut_reel(code: str | None) -> str:
    code = (code or "").strip().upper()
    if code in STATUTS_RADIES_CODES_REELS:
        return "radiee"
    if code == "IM":
        return "immatriculee"
    return code.lower() or "inconnu"


_VILLE_PROVINCE_RE = re.compile(r"^(?P<ville>.+?)\s*\((?P<province>[^)]+)\)\s*$")


def _decouper_adresse(lign1: str, lign2: str, lign3: str, lign4: str) -> tuple[str | None, str | None, str | None]:
    """Découpe les 4 lignes d'adresse réelles du REQ — confirmé par inspection
    réelle (Etablissements.csv/Entreprise.csv, 2026-08-31) : LIGN1 est la rue,
    LIGN2 est typiquement "Ville (Province)", LIGN3 est presque toujours vide,
    LIGN4 est le code postal sans espace (ex. 'H1J1Z1')."""
    lign1, lign2, lign3, lign4 = lign1.strip(), lign2.strip(), lign3.strip(), lign4.strip()

    ville = None
    if lign2:
        m = _VILLE_PROVINCE_RE.match(lign2)
        ville = m.group("ville").strip() if m else lign2  # forme inattendue -> garder tel quel

    parties_adresse = [p for p in (lign1, lign3) if p]
    adresse = ", ".join(parties_adresse) if parties_adresse else None
    return adresse, ville, (lign4 or None)


def _desc_secteur(desc: str | None) -> str | None:
    """DESC_ACT_ECON_ETAB/DESC_ACT_ECON_ASSUJ sont déjà du texte lisible dans le
    vrai fichier (ex. 'FABRICATION DE JOUETS DE BOIS') — pas besoin de décoder
    via DomaineValeur.csv. '-' signifie "non précisé" dans le vrai fichier."""
    desc = (desc or "").strip()
    return desc if desc and desc != "-" else None


@dataclass
class _EtabLeger:
    """Un établissement, réduit aux champs utiles — pour garder l'index
    Etablissements.csv (potentiellement des centaines de milliers de lignes)
    léger en mémoire plutôt que d'y garder les 17 colonnes brutes de chaque
    ligne."""

    no_suf_etab: str
    principal: bool
    adresse: str | None
    ville: str | None
    code_postal: str | None
    secteur_code: str | None
    secteur_libelle: str | None
    nom_etablissement: str | None


def _en_tete_csv(zf: zipfile.ZipFile, nom: str) -> list[str]:
    with zf.open(nom) as raw:
        text = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace")
        return next(csv.reader(text), [])


def _charger_index_noms(zf: zipfile.ZipFile) -> dict[str, str]:
    """Construit l'index NEQ -> nom légal actuel en lisant Nom.csv en flux, avec
    une mémoire bornée au nombre d'ENTREPRISES distinctes (pas au nombre total de
    lignes d'historique de noms). Priorité confirmée par inspection réelle du
    2026-08-31 : un nom STAT_NOM='V' (en vigueur) est préféré, avec
    TYP_NOM_ASSUJ='M' (dénomination sociale) > 'N' (nom) > autre type. À défaut
    d'un nom en vigueur (ex. entreprise radiée, dont le dernier nom repasse à
    STAT_NOM='A' — confirmé sur un vrai NEQ radié), on retient le nom antérieur
    le plus récent comme meilleur effort : l'entreprise sera de toute façon
    exclue par la vérification de statut (section 6), mais garde un nom pour la
    résolution par les AUTRES sources qui l'auraient connue sous ce nom."""
    meilleurs: dict[str, tuple[int, str, str]] = {}  # neq -> (rang, date_tri, nom)
    with zf.open("Nom.csv") as raw:
        text = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace")
        for row in csv.DictReader(text):
            neq = (row.get("NEQ") or "").strip()
            nom = (row.get("NOM_ASSUJ") or "").strip()
            if not neq or not nom:
                continue
            stat = (row.get("STAT_NOM") or "").strip().upper()
            typ = (row.get("TYP_NOM_ASSUJ") or "").strip().upper()
            if stat == "V":
                rang = 0 if typ == "M" else (1 if typ == "N" else 2)
                date_tri = ""
            else:
                rang = 3
                date_tri = (row.get("DAT_FIN_NOM_ASSUJ") or row.get("DAT_INIT_NOM_ASSUJ") or "").strip()

            actuel = meilleurs.get(neq)
            if actuel is None:
                meilleurs[neq] = (rang, date_tri, nom)
                continue
            rang_actuel, date_actuelle, _ = actuel
            if rang < rang_actuel or (rang == rang_actuel == 3 and date_tri > date_actuelle):
                meilleurs[neq] = (rang, date_tri, nom)
    # EN PLACE, et pas `return {neq: nom for neq, (…) in meilleurs.items()}` :
    # la compréhension construit le second dictionnaire pendant que le premier
    # est encore vivant. Mesuré le 2026-09-16 : ~708 Mo au lieu de ~543 sur la
    # population réelle, au moment précis du retour — un doublement transitoire
    # de 165 Mo pour une ligne de code.
    #
    # `popitem()` vide `meilleurs` au fur et à mesure, donc les deux structures
    # ne sont jamais pleines en même temps. L'ordre n'a aucune importance ici :
    # le résultat est un dictionnaire, et l'élection a déjà eu lieu.
    resultat: dict[str, str] = {}
    while meilleurs:
        neq, (_, _, nom) = meilleurs.popitem()
        resultat[neq] = nom
    return resultat


#: Lignes de `req_noms` écrites entre deux commits. Le même ordre de grandeur que
#: `_INTERVALLE_COMMIT` pour l'entreprise-grain — assez gros pour que le coût par
#: ligne disparaisse, assez petit pour qu'une interruption ne perde pas tout.
_INTERVALLE_COMMIT_NOMS = 20000


#: ⚠️ **LES QUATRE GISEMENTS DE NOMS DE L'ARCHIVE** *(inventaire du 2026-09-17,
#: sur l'archive du 2 septembre — le produit n'en indexait qu'UN, filtré)*.
#:
#: `(gisement, fichier, colonne du nom, colonne de statut ou None)`
#:
#: ⚠️ **`DENOMN_SOC` de `FusionScissions.csv` n'est PAS une relation NEQ→NEQ.**
#: *Classée comme telle par lecture trop rapide, elle est restée ignorée une
#: journée de plus.* La relation est `NEQ_ASSUJ_REL`; la dénomination est **un nom
#: rattaché à un NEQ vivant**, rempli à 99,9 %.
#:
#: ⚠️ **Tout gisement ajouté ici doit AUSSI être déclaré à `_LECTEURS_PAR_CSV`**,
#: sans quoi ses colonnes sortent de la vérification d'en-tête, en silence.
GISEMENTS_DE_NOMS: tuple[tuple[str, str, str, str | None], ...] = (
    ("NOM_ASSUJ", "Nom.csv", "NOM_ASSUJ", "STAT_NOM"),
    ("NOM_ETRNG", "Nom.csv", "NOM_ASSUJ_LANG_ETRNG", "STAT_NOM"),
    ("NOM_ETAB", "Etablissements.csv", "NOM_ETAB", None),
    ("DENOMN_SOC", "FusionScissions.csv", "DENOMN_SOC", None),
)

#: Le statut porté par une forme qu'aucune colonne ne qualifie. *Ni « en vigueur »
#: ni « retiré » — le fichier ne le dit pas, et l'inventer serait affirmer.*
STATUT_NON_QUALIFIE = "?"


def _relever_la_borne_de_champ() -> None:
    """⚠️ **Sans ça, la lecture LÈVE sur `OBJET_SOC`.** *Le champ d'objet social
    dépasse la borne par défaut de `csv` (131 072 caractères), et l'erreur tombe
    au milieu du fichier — donc après des minutes de travail.*

    **Relevée à la plus grande valeur que la plateforme accepte**, en redescendant
    tant qu'elle refuse : `sys.maxsize` dépasse un `long` C sur certaines
    plateformes, et `field_size_limit` le refuse alors.
    """
    borne = sys.maxsize
    while True:
        try:
            csv.field_size_limit(borne)
            return
        except OverflowError:
            borne //= 2


def _lecteur_csv(zf: zipfile.ZipFile, fichier: str) -> "Iterator[dict[str, str]]":
    """Un `DictReader` sur un membre du zip, avec les trois pièges de l'archive
    réelle désarmés *(vérifiés sur l'archive du 2 septembre)*.

    1. ⚠️ **Le BOM colle au premier nom de colonne** — `﻿NEQ` et non `NEQ`.
       `utf-8-sig` le retire, **et les en-têtes sont nettoyées en plus** : un
       fichier relu autrement ne doit pas faire échouer `row.get("NEQ")` en
       silence.
    2. ⚠️ **`newline=""`**, comme la documentation de `csv` l'exige. *`OBJET_SOC`
       porte des retours de ligne dans des champs entre guillemets* — une
       traduction de fin de ligne par la couche texte couperait un enregistrement
       en deux.
    3. ⚠️ **La borne de champ relevée**, sinon la lecture lève.

    *Et c'est pourquoi un compte de LIGNES PHYSIQUES est faux : 2 955 115 lignes
    pour 2 955 114 enregistrements. On compte des enregistrements.*
    """
    _relever_la_borne_de_champ()
    with zf.open(fichier) as brut:
        texte = io.TextIOWrapper(brut, encoding="utf-8-sig", errors="replace", newline="")
        lecteur = csv.reader(texte)
        entete = [(colonne or "").lstrip("\ufeff").strip() for colonne in next(lecteur, [])]
        for rangee in lecteur:
            yield dict(zip(entete, rangee))


def _charger_tous_les_noms(
    zf: zipfile.ZipFile,
    db_session: Session,
    limite: int | None = None,
    gisements: tuple[tuple[str, str, str, str | None], ...] | None = None,
    statuts_retenus: frozenset[str] | None = None,
) -> int:
    """Écrit dans `req_noms` **toutes les formes des QUATRE gisements de noms**.

    **Pourquoi une passe SÉPARÉE, et pas l'index en mémoire.** L'import tient déjà
    simultanément l'index des noms élus (~2,7 M), celui des établissements et deux
    instantanés — *pic mesuré à 3 535 Mo pour 8 Go d'hôte.* Cette passe relit les
    fichiers **en flux** et écrit par lots : **la mémoire ne bouge pas, le coût
    est une lecture de plus.**

    `statuts_retenus` filtre sur la colonne de statut du gisement, quand il en a
    une. **`None` veut dire : tout garder**, et le statut réel est écrit en
    colonne pour que la décision se révise **sans réimport**.

    ⚠️ **Le nom ÉLU y figure aussi**, et c'est volontaire : la table répond seule à
    « quels noms mènent à ce NEQ », sans joindre `REQEntry`. *Une table qui ne
    porte que les exceptions oblige tous ses lecteurs à connaître la règle.*

    Rend le nombre de lignes écrites.
    """
    from sqlalchemy import insert

    from falkye.models.req_nom import REQNom

    # INSERT OR IGNORE plutôt que `session.add` ligne à ligne, pour DEUX raisons
    # distinctes qu'il ne faut pas confondre :
    #   1. un RÉIMPORT réécrit les mêmes clés. Avec `add`, la seconde insertion
    #      lève `IntegrityError` et fait tomber l'import entier — mesuré sur les
    #      tests du 2026-09-16.
    #   2. des millions de lignes passées par l'ORM une à une coûteraient des
    #      dizaines de minutes; par lots de dictionnaires, c'est une écriture en
    #      masse.
    # `OR IGNORE` est propre à SQLite, et le miroir EST toujours SQLite
    # (`outils/import_miroir_req.py` refuse toute autre cible avant de démarrer).
    requete = insert(REQNom).prefix_with("OR IGNORE")

    ecrites = 0
    lot: list[dict] = []
    vus: set[tuple[str, str]] = set()

    def _vider():
        nonlocal lot
        if lot:
            db_session.execute(requete, lot)
            db_session.commit()
            lot = []
            vus.clear()  # les lots suivants ne peuvent plus entrer en conflit entre eux

    # ⚠️ Les gisements d'un MÊME fichier se lisent en UNE passe. *Deux passes sur
    # `Nom.csv` (4,65 M d'enregistrements) pour deux colonnes de la même rangée
    # coûteraient le double sans rien rendre de plus.*
    par_fichier: dict[str, list[tuple[str, str, str | None]]] = {}
    for gisement, fichier, colonne, colonne_statut in (gisements or GISEMENTS_DE_NOMS):
        par_fichier.setdefault(fichier, []).append((gisement, colonne, colonne_statut))

    presents = set(zf.namelist())
    for fichier, colonnes in par_fichier.items():
        if fichier not in presents:
            # ⚠️ **Signalé, jamais avalé.** *Un fichier attendu et absent est un
            # changement de forme de l'archive* — la revue d'archive le refuse
            # bruyamment; ici on note pour que le journal d'import le porte.
            logger.warning(
                "REQ: %s absent de l'archive — gisements %s non chargés",
                fichier, [g for g, _, _ in colonnes],
            )
            continue
        lues = 0
        for rangee in _lecteur_csv(zf, fichier):
            if limite is not None and lues >= limite:
                break
            lues += 1
            neq = (rangee.get("NEQ") or "").strip()
            if not neq:
                continue
            for gisement, colonne, colonne_statut in colonnes:
                nom = (rangee.get(colonne) or "").strip()
                if not nom:
                    continue
                statut = (
                    (rangee.get(colonne_statut) or "").strip().upper()
                    if colonne_statut else STATUT_NON_QUALIFIE
                )
                if (
                    colonne_statut
                    and statuts_retenus is not None
                    and statut not in statuts_retenus
                ):
                    continue
                nom_norm = _normaliser(nom)
                if not nom_norm:
                    # Un nom qui se normalise en chaîne vide n'apparierait rien
                    # et apparierait TOUT — c'est le défaut du 15 septembre.
                    continue
                cle = (neq, nom_norm)
                if cle in vus:
                    # Deux gisements peuvent porter la même graphie pour le même
                    # NEQ. `OR IGNORE` l'absorberait; le retirer ici évite
                    # d'envoyer la ligne.
                    continue
                vus.add(cle)
                lot.append({
                    "neq": neq,
                    "nom_normalise": nom_norm,
                    "nom": nom,
                    "statut": statut,
                    "type_nom": (rangee.get("TYP_NOM_ASSUJ") or "").strip(),
                    "gisement": gisement,
                })
                ecrites += 1
                if len(lot) >= _INTERVALLE_COMMIT_NOMS:
                    _vider()
                    logger.info("REQ: %s formes indexées jusqu'ici", ecrites)
        _vider()
        logger.info("REQ: %s — %s enregistrement(s) lus", fichier, lues)
    _vider()
    return ecrites


def construire_index_par_mots(db_session: Session) -> tuple[int, int]:
    """Reconstruit `req_mots` et `req_mots_frequence` **depuis `req_noms`**.

    **Deux requêtes, et rien ne passe par la mémoire de Python.** *Le découpage
    en mots se fait en SQL, sur `nom_normalise` — qui ne porte que `[a-z0-9 ]`,
    donc une espace sépare deux mots et rien d'autre.*

    ⚠️ **Reconstruction TOTALE, jamais incrémentale.** *Une reconstruction
    partielle laisserait une moitié périmée, et c'est invisible.*

    ⚠️ **Le découpeur doit être LE MÊME des deux côtés.** L'index est bâti sur
    `nom_normalise`; la requête découpe le nom cherché avec `mots_du_nom`, sur la
    même forme normalisée. *Deux découpeurs différents feraient baisser le rappel
    sans qu'aucune erreur ne se produise.*

    Rend `(couples, mots distincts)`.
    """
    from sqlalchemy import func, select as _select, text

    from falkye.models.req_mot import REQMot, REQMotFrequence

    # ⚠️ **Le SQL brut doit être ROUTÉ explicitement.** *La session est liée par
    # MODÈLE — `Company` va à la base distante, `REQMot` au miroir local — et un
    # `text()` ne porte aucune métadonnée, donc SQLAlchemy ne sait pas où
    # l'envoyer et lève.* **C'est le découpage produit/miroir qui l'exige, et
    # c'est bien qu'il lève plutôt que de deviner.**
    def _brut(requete: str) -> None:
        db_session.execute(
            text(requete).execution_options(
                synchronize_session=False
            ),
            bind_arguments={"mapper": REQMot},
        )

    _brut("DELETE FROM req_mots")
    _brut("DELETE FROM req_mots_frequence")
    db_session.commit()

    # Le découpage récursif : une ligne par (mot, NEQ). SQLite n'a pas de
    # `split`, donc on consomme la chaîne mot à mot dans une CTE.
    _brut("""
        INSERT OR IGNORE INTO req_mots (mot, neq)
        WITH decoupe(neq, mot, reste) AS (
            SELECT neq,
                   CASE WHEN instr(nom_normalise, ' ') = 0 THEN nom_normalise
                        ELSE substr(nom_normalise, 1, instr(nom_normalise, ' ') - 1) END,
                   CASE WHEN instr(nom_normalise, ' ') = 0 THEN ''
                        ELSE substr(nom_normalise, instr(nom_normalise, ' ') + 1) END
              FROM req_noms
             WHERE nom_normalise <> ''
            UNION ALL
            SELECT neq,
                   CASE WHEN instr(reste, ' ') = 0 THEN reste
                        ELSE substr(reste, 1, instr(reste, ' ') - 1) END,
                   CASE WHEN instr(reste, ' ') = 0 THEN ''
                        ELSE substr(reste, instr(reste, ' ') + 1) END
              FROM decoupe
             WHERE reste <> ''
        )
        SELECT mot, neq FROM decoupe WHERE mot <> ''
    """)
    db_session.commit()

    _brut("""
        INSERT OR IGNORE INTO req_mots_frequence (mot, neqs)
        SELECT mot, COUNT(*) FROM req_mots GROUP BY mot
    """)
    db_session.commit()

    couples = db_session.execute(
        _select(func.count()).select_from(REQMot)
    ).scalar() or 0
    mots = db_session.execute(
        _select(func.count()).select_from(REQMotFrequence)
    ).scalar() or 0
    logger.info("REQ: index par mots — %s couples, %s mots distincts", couples, mots)
    return couples, mots


def _charger_index_etablissements(zf: zipfile.ZipFile) -> dict[str, list[_EtabLeger]]:
    """Construit l'index NEQ -> liste d'établissements en lisant Etablissements.csv
    en flux — réduit à _EtabLeger (7 champs) par ligne plutôt que de garder les 17
    colonnes brutes, pour limiter la mémoire sur un fichier à potentiellement des
    centaines de milliers de lignes."""
    index: dict[str, list[_EtabLeger]] = {}
    with zf.open("Etablissements.csv") as raw:
        text = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace")
        for row in csv.DictReader(text):
            neq = (row.get("NEQ") or "").strip()
            if not neq:
                continue
            adresse, ville, code_postal = _decouper_adresse(
                row.get("LIGN1_ADR") or "",
                row.get("LIGN2_ADR") or "",
                row.get("LIGN3_ADR") or "",
                row.get("LIGN4_ADR") or "",
            )
            index.setdefault(neq, []).append(
                _EtabLeger(
                    no_suf_etab=(row.get("NO_SUF_ETAB") or "").strip(),
                    principal=(row.get("IND_ETAB_PRINC") or "").strip().upper() == "O",
                    adresse=adresse,
                    ville=ville,
                    code_postal=code_postal,
                    secteur_code=(row.get("COD_ACT_ECON") or "").strip() or None,
                    secteur_libelle=_desc_secteur(row.get("DESC_ACT_ECON_ETAB")),
                    nom_etablissement=(row.get("NOM_ETAB") or "").strip() or None,
                )
            )
    return index


def _parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = dateutil_parser.parse(raw)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError):
        return None


def _iter_csv_rows(path) -> Iterator[dict[str, str]]:
    """Lit un CSV (ou un .zip contenant EXACTEMENT un CSV) en flux, sans tout
    charger en mémoire. Le vrai fichier en vrac du REQ contient en réalité SIX
    CSV liés entre eux (Entreprise.csv, Etablissements.csv, Nom.csv,
    DomaineValeur.csv, FusionScissions.csv, ContinuationsTransformations.csv —
    découvert le 2026-08-31 par inspection réelle, voir docs/STATUT_RESEAU.md),
    pas un fichier plat — un .zip à plusieurs CSV lève donc une erreur
    explicite ici plutôt que de les concaténer comme s'ils avaient le même
    schéma, ce qui produirait des lignes mal interprétées en silence (interdit
    par ce projet). La vraie jointure multi-fichiers reste à écrire une fois
    les colonnes confirmées via `REQConnector.inspect_file`/
    `import-manuel inspecter`."""
    if str(path).lower().endswith(".zip"):
        with zipfile.ZipFile(path) as zf:
            noms_csv = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if len(noms_csv) > 1:
            raise RuntimeError(
                f"{path!r} contient {len(noms_csv)} fichiers CSV liés entre eux "
                f"({', '.join(noms_csv)}) plutôt qu'un seul fichier plat — les "
                "traiter comme un seul schéma produirait des données mal "
                "interprétées en silence. Lancez d'abord "
                f"`import-manuel inspecter --source-id req --chemin {path}` pour "
                "obtenir les vraies colonnes de chaque fichier ; la jointure "
                "multi-fichiers (Entreprise.csv + Etablissements.csv + "
                "DomaineValeur.csv) n'est pas encore implémentée."
            )
        with zipfile.ZipFile(path) as zf:
            for name in noms_csv:
                with zf.open(name) as raw:
                    text = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace")
                    yield from csv.DictReader(text)
    else:
        with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
            yield from csv.DictReader(f)


def inspect_zip(path) -> dict[str, dict]:
    """Inspecte un .zip contenant plusieurs CSV liés (le vrai fichier en vrac
    du REQ) SANS tout décompresser ni tout charger en mémoire : ne lit que
    l'en-tête et une ligne d'exemple de chaque CSV membre (les gros fichiers,
    ex. Entreprise.csv ~630 Mo, sont lus en flux — coûte quelques Ko, pas la
    taille totale). Sert à confirmer les vrais noms de colonnes avant d'écrire
    la logique de jointure entre fichiers, plutôt que de deviner à l'aveugle
    sur une structure relationnelle où une mauvaise supposition risquerait une
    jonction silencieusement erronée (pas seulement une colonne manquante)."""
    infos: dict[str, dict] = {}
    with zipfile.ZipFile(path) as zf:
        for zinfo in zf.infolist():
            if not zinfo.filename.lower().endswith(".csv"):
                continue
            with zf.open(zinfo) as raw:
                text = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace")
                reader = csv.reader(text)
                en_tete = next(reader, [])
                premiere_ligne = next(reader, [])
            infos[zinfo.filename] = {
                "colonnes": en_tete,
                "exemple": dict(zip(en_tete, premiere_ligne)) if premiere_ligne else {},
                "taille_decompressee_octets": zinfo.file_size,
            }
    return infos


@dataclass
class IngestStats:
    lignes_lues: int = 0
    entrees_nouvelles: int = 0
    entrees_mises_a_jour: int = 0
    changements_adresse: list[dict] | None = None
    nouveaux_etablissements: list[dict] | None = None  # chemin plat legacy uniquement (voir docstring)
    nouveaux_etablissements_secondaires: list[dict] | None = None  # chemin réel — signal "fort"
    # Rebranchement chantier 1 : un import (entreprise OU établissement grain)
    # mis en quarantaine par falkye/diff_engine.py ne touche NI REQEntry NI
    # aucun signal — voir _ingest_zip_req_reel. `quarantaine_motif` porte la
    # valeur de l'enum MotifQuarantaine (chaîne) du premier grain en cause.
    quarantaine: bool = False
    quarantaine_motif: str | None = None
    #: Noms EN VIGUEUR indexés dans `req_noms` (tous, pas seulement l'élu).
    #: **None tant que la passe n'a pas tourné** — un import en quarantaine n'en
    #: écrit aucun, et zéro s'y lirait « le registre n'en porte aucun ».
    noms_alternatifs: int | None = None

    def __post_init__(self):
        self.changements_adresse = self.changements_adresse or []
        self.nouveaux_etablissements = self.nouveaux_etablissements or []
        self.nouveaux_etablissements_secondaires = self.nouveaux_etablissements_secondaires or []


@dataclass(frozen=True)
class _EntrepriseResolue:
    """Une ligne d'Entreprise.csv déjà jointe à Nom.csv/Etablissements.csv —
    prête pour l'upsert REQEntry, SANS aucune décision de diff (déléguée au
    moteur générique, voir _ingest_zip_req_reel). Extrait de l'ancien
    `_upsert_entreprise_reelle`, qui mêlait jointure, upsert et diff en une
    seule passe — désormais trois responsabilités séparées."""

    neq: str
    nom: str
    statut: str
    date_maj: datetime | None
    adresse: str | None
    ville: str | None
    code_postal: str | None
    secteur_code: str | None
    secteur_libelle: str | None


def _resoudre_entreprise(
    row: dict, noms: dict[str, str], etablissements: dict[str, list[_EtabLeger]]
) -> _EntrepriseResolue | None:
    """Jointure PURE (aucune écriture, aucune décision de diff) d'une ligne
    d'Entreprise.csv aux index NEQ->nom et NEQ->établissements."""
    neq = (row.get("NEQ") or "").strip()
    if not neq:
        return None

    nom = noms.get(neq)
    if not nom:
        # Ne devrait pas arriver (chaque NEQ d'Entreprise.csv a un historique dans
        # Nom.csv) mais REQEntry.nom est non-nullable — ignorer plutôt que
        # deviner un nom, conforme au principe de ne jamais interpréter en silence.
        logger.warning("REQ: NEQ %s présent dans Entreprise.csv mais absent de Nom.csv, ignoré", neq)
        return None

    statut = _decoder_statut_reel(row.get("COD_STAT_IMMAT"))
    date_maj = _parse_date(row.get("DAT_MAJ_INDEX_NOM"))

    etabs = etablissements.get(neq, [])
    principal = next((e for e in etabs if e.principal), etabs[0] if etabs else None)

    if principal is not None:
        adresse, ville, code_postal = principal.adresse, principal.ville, principal.code_postal
        secteur_code, secteur_libelle = principal.secteur_code, principal.secteur_libelle
    elif (row.get("ADR_DOMCL_ADR_DISP") or "").strip().upper() != "O":
        # Repli sur l'adresse du domicile (Entreprise.csv) quand aucun
        # établissement n'est trouvé.
        #
        # ⚠️ CE TEST ÉTAIT INVERSÉ jusqu'au 2026-09-06, et le commentaire qui le
        # justifiait affirmait le contraire de la documentation. Le guide
        # d'utilisation officiel du REQ (Données Québec, section 4.1, position
        # 33) dit : « Indicateur relatif à la DISPENSE de fournir l'adresse du
        # domicile […] tous les éléments de l'adresse seront vides, car
        # l'entreprise a été dispensée de nous fournir cette adresse. »
        #
        # 'O' veut donc dire « dispensée », c'est-à-dire ADRESSE ABSENTE — et
        # c'était le seul cas où l'ancien code acceptait de la lire. Mesuré sur
        # l'édition du 2026-09-01 :
        #
        #   ADR_DOMCL_ADR_DISP='N' : 2 954 554 lignes, dont 1 943 990 avec adresse
        #   ADR_DOMCL_ADR_DISP='O' :       119 lignes, dont         0 avec adresse
        #
        # Le repli ne se déclenchait donc jamais utilement, et les seules villes
        # du miroir venaient d'Etablissements.csv, qui ne couvre que 201 853 NEQ
        # sur 2 955 114 — 6,8 %. Conséquence produit : plus de neuf entreprises
        # sur dix sans localisation, donc invisibles à tout filtre territorial.
        #
        # La comparaison reste sur 'O' plutôt que sur 'N' : une valeur vide (441
        # lignes) ou inattendue signifie « pas de dispense connue », et tenter la
        # lecture ne coûte rien puisqu'une adresse absente ressort de toute façon
        # à None.
        adresse, ville, code_postal = _decouper_adresse(
            row.get("ADR_DOMCL_LIGN1_ADR") or "",
            row.get("ADR_DOMCL_LIGN2_ADR") or "",
            row.get("ADR_DOMCL_LIGN3_ADR") or "",
            row.get("ADR_DOMCL_LIGN4_ADR") or "",
        )
        secteur_code = (row.get("COD_ACT_ECON_CAE") or "").strip() or None
        secteur_libelle = _desc_secteur(row.get("DESC_ACT_ECON_ASSUJ"))
    else:
        adresse, ville, code_postal = None, None, None
        secteur_code = (row.get("COD_ACT_ECON_CAE") or "").strip() or None
        secteur_libelle = _desc_secteur(row.get("DESC_ACT_ECON_ASSUJ"))

    return _EntrepriseResolue(
        neq=neq, nom=nom, statut=statut, date_maj=date_maj,
        adresse=adresse, ville=ville, code_postal=code_postal,
        secteur_code=secteur_code, secteur_libelle=secteur_libelle,
    )


def _upsert_entreprise_reelle(db_session: Session, r: _EntrepriseResolue) -> None:
    """Upsert PUR de REQEntry (miroir de résolution — falkye/resolution.py,
    falkye/verification.py) — plus aucune décision de diff ici, seulement
    appelé APRÈS que le moteur générique (falkye/diff_engine.py) ait confirmé
    que ce run n'est pas en quarantaine."""
    existing = db_session.get(REQEntry, r.neq)
    if existing is None:
        db_session.add(
            REQEntry(
                neq=r.neq, nom=r.nom, nom_normalise=_normaliser(r.nom),
                adresse=r.adresse, ville=r.ville,
                region=None,  # pas de région administrative dans le vrai schéma REQ — voir docstring module
                code_postal=r.code_postal, secteur_code=r.secteur_code, secteur_libelle=r.secteur_libelle,
                statut=r.statut, date_maj_req=r.date_maj,
            )
        )
    else:
        existing.nom = r.nom
        existing.nom_normalise = _normaliser(r.nom)
        existing.adresse = r.adresse
        existing.ville = r.ville
        existing.code_postal = r.code_postal
        existing.secteur_code = r.secteur_code
        existing.secteur_libelle = r.secteur_libelle
        existing.statut = r.statut
        existing.date_maj_req = r.date_maj


def _ligne_entreprise(r: _EntrepriseResolue) -> LigneSnapshot:
    return LigneSnapshot(
        cle=r.neq,
        champs={
            "neq": r.neq,
            "nom_entreprise": r.nom,
            "secteur_activite": r.secteur_libelle,
            "adresses": r.adresse,
            "statut": r.statut,
            "date_derniere_maj": str(r.date_maj) if r.date_maj else None,
        },
    )


def _cle_etablissement(neq: str, no_suf_etab: str) -> str:
    return f"{neq}|{no_suf_etab}"


def _ligne_etablissement(neq: str, etab: _EtabLeger) -> LigneSnapshot:
    # "secteur_code" volontairement absent — voir CHAMPS_PERTINENTS_REQ_ETABLISSEMENTS.
    return LigneSnapshot(
        cle=_cle_etablissement(neq, etab.no_suf_etab),
        champs={
            "adresse": etab.adresse,
            "ville": etab.ville,
            "code_postal": etab.code_postal,
            "secteur_libelle": etab.secteur_libelle,
            "nom_etablissement": etab.nom_etablissement,
            "principal": etab.principal,
        },
    )


#: Quelle fonction lit quel CSV. **Le garde-fou se branche ici**, et nulle part
#: ailleurs : ajouter un CSV à l'import sans l'ajouter à cette table le laisserait
#: hors vérification, en silence.
_LECTEURS_PAR_CSV = {
    "Entreprise.csv": "_resoudre_entreprise",
    "Nom.csv": "_charger_index_noms",
    "Etablissements.csv": "_charger_index_etablissements",
}

#: ⚠️ **Les colonnes des gisements se DÉCLARENT, elles ne se lisent pas par AST.**
#: *La passe des gisements fait `rangee.get(colonne)` où `colonne` vient de
#: `GISEMENTS_DE_NOMS` — un littéral qu'aucun arbre syntaxique ne voit.* **Sans
#: cette déclaration, les quatre gisements sortaient de la vérification d'en-tête
#: en silence**, ce qui est exactement le défaut que le garde existe pour
#: attraper. *(Relevé à l'écriture, le 2026-09-17.)*
#:
#: `TYP_NOM_ASSUJ` n'y figure pas volontairement : la passe le lit au mieux, il
#: n'existe que dans `Nom.csv`, et il DÉCRIT sans DÉCIDER. *Le déclarer ferait
#: refuser l'import sur les deux autres fichiers.*


def colonnes_brutes_lues(source_module: str, nom_fonction: str) -> set[str]:
    """Les en-têtes CSV que cette fonction lit RÉELLEMENT, extraites de son code.

    **Lues par AST plutôt que recopiées dans une liste à côté.** Une liste
    recopiée se désynchronise à la première colonne ajoutée, et le garde-fou
    vérifierait alors sa propre copie *(même règle que pour les requêtes :
    emprunter, jamais recopier)*.

    ⚠️ **C'est ce qui rend une virgule manquante VISIBLE.** `row.get("A" "B")`
    — deux littéraux collés par une virgule oubliée — est du Python valide : il
    lit une colonne nommée `"AB"`, qui n'existe pas, et `.get` rend `None` sans
    rien signaler. *L'AST rend la chaîne telle que Python la voit*, donc `"AB"`,
    et la vérification d'en-tête la refuse en la nommant.
    """
    arbre = ast.parse(source_module)
    for noeud in ast.walk(arbre):
        if not isinstance(noeud, ast.FunctionDef) or noeud.name != nom_fonction:
            continue
        return {
            appel.args[0].value
            for appel in ast.walk(noeud)
            if isinstance(appel, ast.Call)
            and isinstance(appel.func, ast.Attribute)
            and appel.func.attr == "get"
            and appel.args
            and isinstance(appel.args[0], ast.Constant)
            and isinstance(appel.args[0].value, str)
        }
    return set()


def colonnes_couvertes_par_la_quarantaine(source_module: str) -> set[str]:
    """Les colonnes brutes que le moteur de diff surveille DÉJÀ.

    `_colonnes_entreprise_vues` teste `"X" in entete_...` pour chaque champ
    logique; `_MAPPING_COLONNES_ETABLISSEMENTS` fait la même chose par sa table.
    **Quand une de ces colonnes disparaît, l'import part en QUARANTAINE** —
    `REQEntry` reste intact, l'incident est journalisé, `falkye quarantaine
    lister` le montre.

    ⚠️ **C'est une meilleure réponse qu'un refus, et le garde-fou ne doit pas
    la préempter** : un refus levé plus tôt ferait perdre l'incident et son motif.
    *Extraites du code, comme les colonnes lues — les deux mécanismes restent
    ainsi synchronisés sans qu'on ait à y penser.*
    """
    arbre = ast.parse(source_module)
    couvertes: set[str] = set()
    for noeud in ast.walk(arbre):
        # `if "COD_STAT_IMMAT" in entete_entreprise:` — le côté DROIT doit être
        # une en-tête, sinon n'importe quel `"clé" in dict` du module entrerait
        # ici et élargirait la couverture en silence (`_local_path` l'a fait).
        if (
            isinstance(noeud, ast.Compare)
            and isinstance(noeud.left, ast.Constant)
            and isinstance(noeud.left.value, str)
            and any(isinstance(op, ast.In) for op in noeud.ops)
            and any(
                isinstance(c, ast.Name) and c.id.startswith("entete") for c in noeud.comparators
            )
        ):
            couvertes.add(noeud.left.value)
        # la table de correspondance des établissements
        if isinstance(noeud, ast.Assign) and any(
            isinstance(c, ast.Name) and c.id == "_MAPPING_COLONNES_ETABLISSEMENTS"
            for c in noeud.targets
        ):
            if isinstance(noeud.value, ast.Dict):
                couvertes.update(
                    v.value for v in noeud.value.values
                    if isinstance(v, ast.Constant) and isinstance(v.value, str)
                )
    return couvertes


def colonnes_des_gisements() -> dict[str, set[str]]:
    """Par fichier, les colonnes dont la passe des gisements a BESOIN.

    **`NEQ` en fait toujours partie** — sans lui, une forme ne mène nulle part.
    """
    par_fichier: dict[str, set[str]] = {}
    for _gisement, fichier, colonne, colonne_statut in GISEMENTS_DE_NOMS:
        colonnes = par_fichier.setdefault(fichier, {"NEQ"})
        colonnes.add(colonne)
        if colonne_statut:
            colonnes.add(colonne_statut)
    return par_fichier


def colonnes_declarees_absentes(
    entetes: dict[str, list[str]], source_module: str | None = None
) -> dict[str, list[str]]:
    """`CSV -> colonnes déclarées par le code mais ABSENTES de l'en-tête réelle`.

    **Le garde-fou posé après le 15 septembre 2026** *(décision d'Alexandre)* :
    vérifier que **toutes les colonnes déclarées existent**, pas seulement celles
    dont on constate qu'elles servent.

    **Le défaut qu'il ferme, et pourquoi rien ne l'attrapait.** `dict.get` d'une
    colonne inexistante rend `None`. Ce `None` devient `""` par le `or ""`
    habituel, puis une chaîne normalisée **vide** écrite en base. *Aucune
    exception, aucun avertissement, aucun test rouge — et la moitié d'un miroir
    de 2,7 millions de lignes devient inutilisable sans que rien n'échoue.*
    **C'est la forme la plus coûteuse qui soit : une faute invisible à
    l'exécution.**

    **Sa portée est le POINT AVEUGLE, et rien d'autre.** Les colonnes dont
    dépend un champ *logique* — `NOM_ASSUJ`, `COD_STAT_IMMAT`, `LIGN1_ADR`… —
    sont déjà surveillées par le moteur de diff, qui met l'import en quarantaine
    en laissant `REQEntry` intact et en journalisant le motif. *Ce garde-fou les
    laisse passer exprès.* **Il ne couvre que celles qu'aucun champ logique ne
    représente** — `STAT_NOM`, `TYP_NOM_ASSUJ`, `ADR_DOMCL_ADR_DISP`,
    `NO_SUF_ETAB`, les dates de `Nom.csv` — *qui décident du nom élu et de
    l'adresse retenue, et dont la disparition ne déclenche rien du tout.*

    ⚠️ **Ce que ce garde-fou NE couvre PAS**, et qu'il ne faut pas lui prêter :
    il compare des NOMS d'en-tête. *Une colonne présente mais vide, renommée avec
    le même sens, ou remplie d'autre chose passe sans rien dire* — **une garde ne
    couvre que ce que la mesure couvrait.**
    """
    if source_module is None:
        source_module = Path(__file__).read_text(encoding="utf-8")
    couvertes = colonnes_couvertes_par_la_quarantaine(source_module)
    absentes: dict[str, list[str]] = {}
    # ⚠️ DEUX sources de vérité, et il faut les deux : l'AST pour les lecteurs
    # qui nomment leurs colonnes en littéral, la déclaration pour la passe des
    # gisements, qui les prend dans une table.
    des_gisements = colonnes_des_gisements()
    a_verifier = set(_LECTEURS_PAR_CSV) | set(des_gisements)
    for csv_nom in sorted(a_verifier):
        presentes = set(entetes.get(csv_nom) or [])
        fonction = _LECTEURS_PAR_CSV.get(csv_nom)
        lues = colonnes_brutes_lues(source_module, fonction) if fonction else set()
        lues |= des_gisements.get(csv_nom, set())
        # Les colonnes que la quarantaine surveille sont RETIRÉES d'ici : sur
        # celles-là le moteur de diff a déjà une réponse, meilleure que le refus.
        manquantes = sorted(lues - presentes - couvertes)
        if manquantes:
            absentes[csv_nom] = manquantes
    return absentes


class ColonnesDeclareesAbsentes(RuntimeError):
    """L'import refuse AVANT d'avoir lu une seule ligne."""


def refuser_si_colonnes_absentes(entetes: dict[str, list[str]]) -> None:
    """Lève si une colonne déclarée manque à l'appel. **Refuser, pas dégrader.**

    *Un import qui dégrade produit un miroir utilisable en apparence, et le
    défaut ne se voit qu'à la résolution, des jours plus tard.* Le refus coûte
    deux secondes — la vérification porte sur les en-têtes, avant toute lecture
    de ligne — contre 33 minutes d'import et un miroir à refaire.
    """
    absentes = colonnes_declarees_absentes(entetes)
    if not absentes:
        return
    detail = "; ".join(f"{csv_nom} → {', '.join(cols)}" for csv_nom, cols in absentes.items())
    raise ColonnesDeclareesAbsentes(
        "REQ : le code lit des colonnes qui N'EXISTENT PAS dans l'archive — "
        f"{detail}. Rien n'a été importé. Une colonne absente ne lève pas à la "
        "lecture : `dict.get` rend None, et la valeur finit vide en base sans "
        "qu'aucun test ne rougisse. Vérifier une virgule oubliée entre deux noms "
        "de colonne (deux littéraux collés n'en font qu'un) avant de conclure que "
        "le schéma du REQ a changé."
    )


def _colonnes_entreprise_vues(entete_entreprise: list[str], entete_nom: list[str], entete_etablissements: list[str]) -> dict[str, str]:
    """`colonnes_vues` du grain entreprise pour le moteur générique — dans le
    VOCABULAIRE LOGIQUE de CHAMPS_PERTINENTS_REQ (comme `LigneSnapshot.champs`,
    pas les en-têtes CSV brutes : c'est ce que teste déjà
    tests/test_diff_engine.py), mais renseigné seulement quand la colonne
    brute dont ce champ logique dépend RÉELLEMENT existe encore dans les 3
    CSV joints — sinon la disparition d'une colonne brute (ex. NOM_ASSUJ
    retiré de Nom.csv) resterait invisible au moteur, qui ne verrait jamais
    passer le nom logique "manquant" puisque `noms.get(neq)` retournerait
    simplement None pour tout le monde plutôt que déclencher la quarantaine."""
    colonnes: dict[str, str] = {}
    if "NEQ" in entete_entreprise:
        colonnes["neq"] = "str"
    if "NOM_ASSUJ" in entete_nom:
        colonnes["nom_entreprise"] = "str"
    if "COD_STAT_IMMAT" in entete_entreprise:
        colonnes["statut"] = "str"
    if "DAT_MAJ_INDEX_NOM" in entete_entreprise:
        colonnes["date_derniere_maj"] = "str"
    # adresses/secteur_activite : dérivables via Etablissements.csv (voie
    # principale) OU, à défaut, le repli domicile d'Entreprise.csv — pertinent
    # tant qu'AU MOINS une des deux voies existe encore.
    if "LIGN1_ADR" in entete_etablissements or "ADR_DOMCL_LIGN1_ADR" in entete_entreprise:
        colonnes["adresses"] = "str"
    if "DESC_ACT_ECON_ETAB" in entete_etablissements or "DESC_ACT_ECON_ASSUJ" in entete_entreprise:
        colonnes["secteur_activite"] = "str"
    return colonnes


_MAPPING_COLONNES_ETABLISSEMENTS = {
    "adresse": "LIGN1_ADR",
    "ville": "LIGN2_ADR",  # ville dérivée de LIGN2_ADR, voir _decouper_adresse
    "code_postal": "LIGN4_ADR",
    # "secteur_code" volontairement absent — voir CHAMPS_PERTINENTS_REQ_ETABLISSEMENTS.
    "secteur_libelle": "DESC_ACT_ECON_ETAB",
    "nom_etablissement": "NOM_ETAB",
    "principal": "IND_ETAB_PRINC",
}


def _colonnes_etablissements_vues(entete_etablissements: list[str]) -> dict[str, str]:
    return {
        logique: "str"
        for logique, brute in _MAPPING_COLONNES_ETABLISSEMENTS.items()
        if brute in entete_etablissements
    }


_INTERVALLE_COMMIT = 5000  # lignes entre deux commits intermédiaires (phase d'upsert uniquement)


def _deriver_signaux_req(
    stats: IngestStats, rapports: list[RapportExecution], etablissements: dict[str, list[_EtabLeger]]
) -> None:
    """Dérivation des signaux REQ à partir des DEUX `RapportExecution` DÉJÀ
    calculés par le moteur — appelée UNIQUEMENT par `executer_diff_groupe`
    (voir `_ingest_zip_req_reel`), et donc UNIQUEMENT quand les deux grains
    sont simultanément acceptés (ni référence, ni quarantaine, sur AUCUN des
    deux) : cette fonction n'a plus besoin de vérifier `run_reference`
    elle-même, et ne PEUT structurellement pas être invoquée sur un run de
    référence — chantier 1, suivi 2026-09-04 (correction demandée par
    Alexandre après le constat réel sur licences_toronto/licences_vancouver,
    voir falkye/diff_engine.py, docstring de module).

    Corrige au passage un bogue latent jamais manifesté en pratique : avant
    cette correction, le grain établissement dérivait ses signaux dès que
    LUI-MÊME n'était pas un run de référence, indépendamment du grain
    entreprise — si le grain entreprise avait été en référence (ou en
    quarantaine) pendant que le grain établissement ne l'était pas,
    `neq_nouvelles_entreprises` (ci-dessous) serait retombé sur un ensemble
    vide (faute de `rapport_entreprise.resultat`), et TOUS les
    établissements seraient passés à tort pour "secondaires d'une entreprise
    déjà connue". La décision conjointe portée par `executer_diff_groupe`
    empêche structurellement ce cas."""
    rapport_entreprise, rapport_etab = rapports
    stats.entrees_nouvelles = len(rapport_entreprise.resultat.apparitions)
    stats.entrees_mises_a_jour = len(rapport_entreprise.resultat.modifications)
    for m in rapport_entreprise.resultat.modifications:
        # Même règle de calibration qu'avant : un changement d'adresse ne
        # compte que si une adresse était DÉJÀ connue (une entreprise qui
        # en obtient une pour la première fois n'a pas "changé" d'adresse).
        if "adresses" in m.champs_changes and m.champs_avant.get("adresses") is not None:
            stats.changements_adresse.append(
                {
                    "neq": m.cle,
                    "nom": m.champs_apres.get("nom_entreprise") or "",
                    "ancienne_adresse": m.champs_avant.get("adresses"),
                    "nouvelle_adresse": m.champs_apres.get("adresses"),
                }
            )

    # Signal fort UNIQUEMENT pour un établissement SECONDAIRE apparu chez une
    # entreprise DÉJÀ connue — "déjà connue" est ici exprimé par le moteur
    # lui-même : un NEQ qui apparaît CE run au grain entreprise (jamais vu
    # avant) exclut ses établissements de ce signal, même règle de
    # calibration que l'ancien `entreprise_deja_connue`.
    neq_nouvelles_entreprises = {l.cle for l in rapport_entreprise.resultat.apparitions}
    # secteur_code n'est pas dans l'empreinte diffée (voir CHAMPS_PERTINENTS_
    # REQ_ETABLISSEMENTS) mais reste voulu dans le signal — récupéré ici
    # directement depuis l'index déjà en mémoire (source de vérité pour CE
    # run), pas depuis l.champs.
    secteur_code_par_cle = {
        _cle_etablissement(neq, e.no_suf_etab): e.secteur_code for neq, etabs in etablissements.items() for e in etabs
    }
    for l in rapport_etab.resultat.apparitions:
        neq, no_suf_etab = l.cle.split("|", 1)
        if neq in neq_nouvelles_entreprises or l.champs.get("principal"):
            continue
        stats.nouveaux_etablissements_secondaires.append(
            {
                "neq": neq,
                "no_suf_etab": no_suf_etab,
                "adresse": l.champs.get("adresse"),
                "nom_etablissement": l.champs.get("nom_etablissement"),
                "secteur_code": secteur_code_par_cle.get(l.cle),
                "secteur_libelle": l.champs.get("secteur_libelle"),
            }
        )


def _ingest_zip_req_reel(db_session: Session, zf: zipfile.ZipFile, limit: int | None) -> IngestStats:
    """Ingestion du VRAI fichier REQ (Entreprise.csv + Nom.csv + Etablissements.csv
    joints par NEQ — voir docstring du module pour la structure confirmée le
    2026-08-31). Rebranchée sur le moteur de diff générique (Chantier 1, suivi
    2026-09-04) — DEUX PHASES, jamais mélangées :

    Phase 1 — construit les DEUX instantanés (grain entreprise, grain
    établissement) SANS ÉCRIRE UNE SEULE LIGNE en base, puis les soumet
    ENSEMBLE au moteur générique (falkye/diff_engine.py::executer_diff_groupe)
    comme UN SEUL groupe lié. Si L'UN OU L'AUTRE grain est mis en quarantaine,
    la phase 2 n'a jamais lieu : le miroir de résolution REQEntry (falkye/
    resolution.py, falkye/verification.py — utilisé par TOUTES les autres
    sources) reste INTACT, exactement comme l'état de diff lui-même — un
    import REQ corrompu ne doit pas seulement s'abstenir de produire un
    signal, il ne doit RIEN écrire nulle part (extension du garde-fou du
    mandat à la totalité du pipeline REQ, pas seulement à ses signaux).

    Phase 2 — seulement si aucun grain n'est en quarantaine : upsert PUR de
    REQEntry (`_upsert_entreprise_reelle`, plus aucune décision de diff, déjà
    prise par le moteur — a lieu aussi bien au run de référence qu'à un run
    normal, puisqu'il s'agit du miroir de résolution, pas d'un signal). La
    dérivation des RawSignal, elle, est portée par `_deriver_signaux_req`,
    passée à `executer_diff_groupe` comme callback `apres_diff_accepte` —
    le moteur ne l'invoque QUE si les DEUX grains sont simultanément acceptés
    (chantier 1, suivi 2026-09-04 : cette fonction n'a donc plus jamais à
    vérifier `rapport.run_reference` elle-même, voir sa docstring).

    REQEtablissementEntry n'est plus alimenté : sa seule raison d'être était
    ce diff établissement-grain, désormais porté par `EtatLigneSource
    ("req_etablissements")` — voir falkye/models/req_etablissement_entry.py.

    Mémoire : les deux index (Nom.csv, Etablissements.csv) et les deux
    instantanés (entreprise, établissement) sont tenus en mémoire simultanément
    pendant la phase 1 — de l'ordre de quelques Go sur le fichier réel actuel
    (~2,7M entreprises), validé lors de la macro-vérification du chantier 1."""
    # LE GARDE-FOU, posé avant TOUTE lecture de ligne. Deux secondes sur les
    # en-têtes contre 33 minutes d'import et un miroir à refaire — et surtout
    # contre un miroir utilisable EN APPARENCE, dont le défaut ne se voit qu'à
    # la résolution, des jours plus tard.
    refuser_si_colonnes_absentes(
        {
            # ⚠️ **Les en-têtes se collectent sur TOUS les fichiers que le code
            # lit, gisements compris.** *Un fichier lu et non collecté rend une
            # en-tête VIDE au garde, qui refuse alors un import valide* — donc le
            # garde serait retiré au premier faux positif, et ne protégerait plus
            # rien. **Un membre ABSENT rend bien une liste vide, et là le refus
            # est le comportement voulu** : un fichier attendu et absent doit
            # échouer bruyamment.
            **{
                fichier: (
                    _en_tete_csv(zf, fichier) if fichier in zf.namelist() else []
                )
                for fichier in sorted(
                    set(_LECTEURS_PAR_CSV) | set(colonnes_des_gisements())
                )
            },
        }
    )

    noms = _charger_index_noms(zf)
    etablissements = _charger_index_etablissements(zf)

    # --- Phase 1 : instantanés, aucune écriture ---
    entete_entreprise: list[str] = []
    lignes_entreprise: list[LigneSnapshot] = []
    resolues: list[_EntrepriseResolue] = []
    lignes_lues = 0
    with zf.open("Entreprise.csv") as raw:
        text = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace")
        reader = csv.DictReader(text)
        entete_entreprise = list(reader.fieldnames or [])
        for row in reader:
            if limit is not None and lignes_lues >= limit:
                break
            lignes_lues += 1
            r = _resoudre_entreprise(row, noms, etablissements)
            if r is None:
                continue
            resolues.append(r)
            lignes_entreprise.append(_ligne_entreprise(r))

    entete_nom = _en_tete_csv(zf, "Nom.csv")
    entete_etablissements = _en_tete_csv(zf, "Etablissements.csv")
    colonnes_entreprise = _colonnes_entreprise_vues(entete_entreprise, entete_nom, entete_etablissements)
    colonnes_etab = _colonnes_etablissements_vues(entete_etablissements)
    lignes_etab = [
        _ligne_etablissement(neq, etab) for neq, etabs in etablissements.items() for etab in etabs
    ]

    registry = get_registry()
    source_def = registry.sources.get("req")
    seuils_entreprise = seuils_depuis_registre(source_def.seuils_quarantaine) if source_def else None

    stats = IngestStats(lignes_lues=lignes_lues)
    rapport_entreprise, rapport_etab = executer_diff_groupe(
        db_session,
        [
            SpecificationDiff("req", lignes_entreprise, colonnes_entreprise, CHAMPS_PERTINENTS_REQ, seuils=seuils_entreprise),
            SpecificationDiff("req_etablissements", lignes_etab, colonnes_etab, CHAMPS_PERTINENTS_REQ_ETABLISSEMENTS),
        ],
        apres_diff_accepte=lambda rapports: _deriver_signaux_req(stats, rapports, etablissements),
    )

    if rapport_entreprise.quarantaine or rapport_etab.quarantaine:
        motif = rapport_entreprise.motif_quarantaine or rapport_etab.motif_quarantaine
        stats.quarantaine = True
        stats.quarantaine_motif = motif.value if motif else None
        logger.warning(
            "REQ: import mis en quarantaine (grain entreprise=%s, grain établissements=%s) — "
            "REQEntry non touché, aucun signal produit. Voir `falkye quarantaine lister`.",
            rapport_entreprise.motif_quarantaine.value if rapport_entreprise.quarantaine else "ok",
            rapport_etab.motif_quarantaine.value if rapport_etab.quarantaine else "ok",
        )
        db_session.commit()  # persiste l'incident de quarantaine déjà journalisé par le moteur
        return stats

    # --- Phase 2 : upsert du miroir de résolution (jamais de diff ici) — a
    # lieu aussi bien au run de référence qu'à un run normal, voir docstring
    # de fonction. Les signaux, eux, ont déjà été dérivés (ou non) par
    # `_deriver_signaux_req` ci-dessus, au moment même de l'appel au moteur. ---
    for i, r in enumerate(resolues, start=1):
        _upsert_entreprise_reelle(db_session, r)
        if i % _INTERVALLE_COMMIT == 0:
            db_session.commit()
            logger.info("REQ (fichier réel): %s lignes de résolution appliquées jusqu'ici", i)

    # TOUS les noms des QUATRE gisements, en passe séparée — après l'upsert,
    # jamais avant : si le miroir n'a pas été écrit, les noms n'ont rien à
    # indexer.
    stats.noms_alternatifs = _charger_tous_les_noms(zf, db_session, limite=limit)
    logger.info("REQ: %s formes indexées dans req_noms", stats.noms_alternatifs)

    # ---- L'INDEX PAR MOTS, reconstruit ENTIÈREMENT ------------------------
    # ⚠️ **Après les noms, et depuis `req_noms` — jamais depuis les fichiers.**
    # *Un index bâti sur une autre source que la table qu'il indexe se
    # désynchronise, et c'est invisible.*
    construire_index_par_mots(db_session)

    # ---- LE TÉMOIN DU DÉCOUPEUR ------------------------------------------
    # ⚠️ **La seule dégradation silencieuse que l'index par mots puisse subir :
    # deux découpeurs différents.** *L'index découpe en SQL, la requête découpe
    # en Python — si les deux divergeaient, le rappel baisserait sans qu'aucune
    # erreur ne se produise.* **Donc on vérifie qu'un nom connu se retrouve
    # lui-même, et l'import REFUSE sinon.**
    refuser_si_le_decoupeur_diverge(db_session)

    if rapport_entreprise.run_reference:
        # Run de référence (jamais de candidat, mandat chantier 1) : amorce
        # l'état, REQEntry peuplé, mais aucun changements_adresse/nouvel_
        # etablissement_secondaire (le callback ci-dessus n'a pas été
        # invoqué) — même comportement qu'avant (une toute première
        # immatriculation n'est jamais un signal). Comptage informationnel
        # seulement, jamais un signal — sans risque à dériver ici même sans
        # passer par le callback moteur.
        stats.entrees_nouvelles = len(lignes_entreprise)

    db_session.commit()
    return stats


def ingest_snapshot(
    db_session: Session, limit: int | None = None, fichier_local: str | None = None
) -> IngestStats:
    """Met à jour le miroir local (REQEntry + REQEtablissementEntry) à partir du
    fichier REQ en vrac (mise à jour deux fois par mois — spec section 7), en
    détectant au passage les changements pertinents (nouvel établissement
    secondaire, changement d'adresse du siège) par comparaison à l'état
    précédemment connu. Toute résolution nom->NEQ ou NEQ->fiche pour les AUTRES
    sources (resolve_neq_by_name, get_by_neq) n'interroge QUE ce miroir local —
    jamais une requête réseau par entreprise (spec section 7 : le fichier en
    vrac est la méthode principale, pas des requêtes individuelles sur le site
    de consultation). `limit` borne le nombre de lignes d'Entreprise.csv
    traitées — utile pour un premier test raisonnable plutôt que le registre
    complet (accepté comme limite de volume, pas comme donnée fictive : chaque
    ligne traitée reste une vraie ligne du REQ) ; les index Nom.csv/
    Etablissements.csv sont chargés en entier quel que soit `limit` (ils sont
    nécessaires pour joindre n'importe quelle ligne d'Entreprise.csv).

    `fichier_local` : chemin d'un fichier déjà téléchargé PAR L'UTILISATEUR
    (spec section 9, "Import manuel de documents sources") — voir
    falkye/manual_import.py:importer_fichier_source et
    docs/STATUT_RESEAU.md (le téléchargement automatisé depuis cette session
    est bloqué par une règle Cloudflare visant les plages IP infonuagiques,
    pas un problème de méthode d'accès — voir REQConnector.detect ci-dessous,
    conservé documenté mais plus branché dans le registre pour la Phase 1). Si
    omis, retombe sur le téléchargement automatisé via CKAN (chemin plat legacy
    — voir docstring du module : le vrai fichier REQ n'est jamais un CSV plat,
    ce repli réseau n'a donc plus de vraie utilité pratique en Phase 1, gardé
    documenté au cas où l'accès redeviendrait praticable)."""
    if fichier_local is not None:
        if str(fichier_local).lower().endswith(".zip"):
            with zipfile.ZipFile(fichier_local) as zf:
                noms_csv = {n for n in zf.namelist() if n.lower().endswith(".csv")}
                if FICHIERS_REQ_REELS.issubset(noms_csv):
                    return _ingest_zip_req_reel(db_session, zf, limit)
        resources = [{"_local_path": fichier_local}]
    else:
        client = CKANClient(DONNEES_QUEBEC_BASE)
        # Le jeu de données réel n'a que 2 ressources : le fichier de données en vrac
        # (format ZIP, contenant le/les CSV) et un guide d'utilisation (format PDF) —
        # confirmé en inspectant la vraie réponse CKAN. On cible explicitement le ZIP ;
        # ne JAMAIS retomber sur "toutes les ressources" (ça inclurait le PDF, qui
        # casserait le parsing CSV en aval) ni interroger autre chose qu'UN téléchargement
        # en vrac par exécution — spec section 7 : le fichier en vrac de Données Québec
        # est la méthode principale, pas des requêtes individuelles par entreprise (voir
        # docs/STATUT_RESEAU.md pour la confirmation qu'aucune requête par entreprise
        # n'existe ailleurs dans ce connecteur).
        resources = client.resources(REQ_PACKAGE_ID, format_filter="ZIP") or client.resources(
            REQ_PACKAGE_ID, format_filter="CSV"
        )
        if not resources:
            raise RuntimeError(
                f"Aucune ressource ZIP ou CSV trouvée pour le jeu de données CKAN {REQ_PACKAGE_ID!r} "
                "(le format du jeu de données a peut-être changé — vérifier avec package_show)."
            )

    stats = IngestStats()
    columns: dict[str, str] | None = None

    for resource in resources:
        path = resource["_local_path"] if "_local_path" in resource else client.download(resource)
        rows_iter = _iter_csv_rows(path)
        try:
            first_row = next(rows_iter)
        except StopIteration:
            continue
        if columns is None:
            columns = resolve_columns(list(first_row.keys()), COLUMN_ALIASES)

        for row in _chain_one(first_row, rows_iter):
            if limit is not None and stats.lignes_lues >= limit:
                break
            stats.lignes_lues += 1
            _upsert_row(db_session, row, columns, stats)

        if limit is not None and stats.lignes_lues >= limit:
            break

    db_session.commit()
    return stats


def _chain_one(first, rest: Iterator[dict]) -> Iterator[dict]:
    yield first
    yield from rest


def _upsert_row(db_session: Session, row: dict, columns: dict[str, str], stats: IngestStats) -> None:
    """Chemin "fichier plat" legacy — voir docstring du module : le vrai fichier
    REQ n'est jamais un CSV plat, cette fonction ne sert plus qu'au repli réseau
    dormant (REQConnector.detect) et aux tests de mécanique avec un CSV
    synthétique à une seule table."""
    neq = (row.get(columns["neq"]) or "").strip()
    if not neq:
        return

    nom = (row.get(columns["nom"]) or "").strip()
    statut = _parse_statut(row.get(columns["statut"], ""))
    adresse = (row.get(columns["adresse"]) or "").strip() or None
    ville = (row.get(columns["ville"]) or "").strip() or None
    region = (row.get(columns["region"]) or "").strip() or None
    code_postal = (row.get(columns["code_postal"]) or "").strip() or None
    secteur_code = (row.get(columns["secteur_code"]) or "").strip() or None
    secteur_libelle = (row.get(columns["secteur_libelle"]) or "").strip() or None
    date_maj = _parse_date(row.get(columns["date_maj"]))

    existing = db_session.get(REQEntry, neq)

    if existing is None:
        entry = REQEntry(
            neq=neq,
            nom=nom,
            nom_normalise=_normaliser(nom),
            adresse=adresse,
            ville=ville,
            region=region,
            code_postal=code_postal,
            secteur_code=secteur_code,
            secteur_libelle=secteur_libelle,
            statut=statut,
            date_maj_req=date_maj,
        )
        db_session.add(entry)
        stats.entrees_nouvelles += 1
        stats.nouveaux_etablissements.append({"neq": neq, "nom": nom, "adresse": adresse})
        return

    changement_adresse = adresse is not None and adresse != existing.adresse and existing.adresse is not None
    if changement_adresse:
        stats.changements_adresse.append(
            {"neq": neq, "nom": nom, "ancienne_adresse": existing.adresse, "nouvelle_adresse": adresse}
        )

    if (
        existing.nom != nom
        or existing.adresse != adresse
        or existing.statut != statut
        or existing.secteur_code != secteur_code
    ):
        stats.entrees_mises_a_jour += 1

    existing.nom = nom
    existing.nom_normalise = _normaliser(nom)
    existing.adresse = adresse
    existing.ville = ville
    existing.region = region
    existing.code_postal = code_postal
    existing.secteur_code = secteur_code
    existing.secteur_libelle = secteur_libelle
    existing.statut = statut
    existing.date_maj_req = date_maj


# ---------------------------------------------------------------------------
# API de résolution publique — utilisée par falkye/resolution.py et
# falkye/verification.py, indépendamment du rôle "source de signal".
# ---------------------------------------------------------------------------


@dataclass
class REQMatch:
    entry: REQEntry
    score: float  # 0-100, confiance de correspondance du nom
    #: ⚠️ **La forme du registre qui a REMPORTÉ le score**, normalisée.
    #:
    #: *Le score d'un NEQ est le meilleur de ses noms* — donc la forme qui a
    #: décidé n'est presque jamais `entry.nom`, qui est la dénomination sociale
    #: ÉLUE. **Afficher `entry.nom` en disant « registre » fait lire la décision
    #: sur une chaîne qui n'a pas décidé** : `16790224 Canada Inc.` contre
    #: `LES ENTREPRISES DOUGLAS POWERTECH INC.` à 100, sans un caractère commun.
    #:
    #: *C'est le cas 33 : un instrument doit dire sur quoi il a décidé.*
    #: `formes_retenues()` la traduit en nom publié, gisement et statut.
    forme_normalisee: str | None = None


#: Ce qu'on affiche quand le gisement d'une forme est la dénomination sociale
#: élue elle-même. *Ce n'est pas un gisement de `GISEMENTS_DE_NOMS` : c'est la
#: ligne de `req_entries`, et la nommer autrement ferait croire à un cinquième.*
GISEMENT_DENOMINATION_ELUE = "(dénomination élue)"

#: ⚠️ **Les lignes de `req_noms` chargées AVANT que la colonne `gisement`
#: existe** *(pont du 15 septembre, colonne ajoutée le 17)*. **1 505 879 lignes
#: sur 5 071 984 — 29,7 % de la table** *(mesuré sur l'hôte le 19 septembre)*.
#:
#: *Le pont d'origine ne lisait que `NOM_ASSUJ` : c'était le seul gisement qui
#: existait alors.* **Donc `NOM_ASSUJ` par construction** — mais l'étiquette le
#: DIT, au lieu de laisser croire que la valeur a été lue.
#:
#: ⚠️ **Et ça ne se remplira pas tout seul.** *`_charger_tous_les_noms` écrit en
#: `INSERT OR IGNORE` sur une clé `(neq, nom_normalise)`, et rien ne vide
#: `req_noms`* — **un réimport SAUTE ces lignes au lieu de les réécrire.**
GISEMENT_ANTERIEUR_A_LA_COLONNE = "NOM_ASSUJ (antérieur à la colonne)"


def lignes_sans_gisement(db_session: Session) -> tuple[int, int]:
    """`(sans gisement, total)` de `req_noms` — **pour qu'une ventilation par
    gisement ne se lise jamais comme complète.**

    ⚠️ *Le chiffre n'est pas faux, il est incomplet* — et rien dans une
    ventilation ne le dit si personne ne l'écrit à côté.
    """
    from falkye.models.req_nom import REQNom

    total = db_session.execute(
        select(func.count()).select_from(REQNom)
    ).scalar_one()
    sans = db_session.execute(
        select(func.count()).select_from(REQNom).where(REQNom.gisement.is_(None))
    ).scalar_one()
    return sans, total


@dataclass(frozen=True)
class FormeRetenue:
    """La forme qui a décidé, **telle qu'elle se lit** — publiée, avec sa
    provenance et son statut.

    ⚠️ *`REQNom` sert à TROUVER, jamais à NOMMER* : `nom_publie` s'affiche À CÔTÉ
    de la dénomination élue, jamais à sa place.
    """

    nom_normalise: str
    nom_publie: str | None
    gisement: str | None
    statut: str | None
    est_la_denomination_elue: bool

    @property
    def introuvable(self) -> bool:
        """*Une forme que ni `req_entries` ni `req_noms` ne portent.* **Arrive
        sur le chemin de SIMULATION**, où les formes sont transformées avant
        d'être scorées — et nulle part ailleurs."""
        return self.nom_publie is None and not self.est_la_denomination_elue


def formes_retenues(db_session: Session, matches: list) -> dict[tuple[str, str], FormeRetenue]:
    """`(neq, forme_normalisée) -> FormeRetenue`, **en une seule requête**.

    *Une lecture par paire affichée ferait N requêtes pour un rapport de
    cinquante lignes; sur les 2 523 de la passe, ça se paie.*
    """
    voulues = {
        (m.entry.neq, m.forme_normalisee) for m in matches
        if m.forme_normalisee is not None
    }
    if not voulues:
        return {}
    par_neq: dict[str, REQEntry] = {m.entry.neq: m.entry for m in matches}
    lignes = db_session.execute(
        select(REQNom.neq, REQNom.nom_normalise, REQNom.nom, REQNom.gisement,
               REQNom.statut).where(REQNom.neq.in_([neq for neq, _ in voulues]))
    ).all()
    depuis_req_noms = {
        (neq, forme): (nom, gisement, statut)
        for neq, forme, nom, gisement, statut in lignes
    }
    rendu: dict[tuple[str, str], FormeRetenue] = {}
    for neq, forme in voulues:
        entry = par_neq[neq]
        elue = entry.nom_normalise == forme
        nom, gisement, statut = depuis_req_noms.get((neq, forme), (None, None, None))
        if elue:
            etiquette = GISEMENT_DENOMINATION_ELUE
        elif gisement is None and (neq, forme) in depuis_req_noms:
            # ⚠️ **La ligne EXISTE et sa colonne est vide** : c'est le pont du
            # 15 septembre, pas un gisement inconnu. *Le dire plutôt que d'écrire
            # « inconnu », qui envoie chercher une lecture manquée.*
            etiquette = GISEMENT_ANTERIEUR_A_LA_COLONNE
        else:
            etiquette = gisement
        rendu[(neq, forme)] = FormeRetenue(
            nom_normalise=forme,
            # ⚠️ Quand la forme EST la dénomination élue, le nom publié est celui
            # de `req_entries` — et `req_noms` peut en porter une ligne aussi.
            nom_publie=entry.nom if elue else nom,
            gisement=etiquette,
            statut=statut,
            est_la_denomination_elue=elue,
        )
    return rendu


def get_by_neq(db_session: Session, neq: str) -> REQEntry | None:
    return db_session.get(REQEntry, neq)


#: Diviseur de la part de `limite` RÉSERVÉE aux candidats venus de `req_noms`.
#: Un quart : assez pour que le pont existe même quand la requête principale
#: sature, assez peu pour que la récupération principale reste dominante.
#: **Ce n'est pas un réglage fin, c'est un plancher** — la valeur exacte se
#: mesurera sur le rendement par chemin, jamais ici.
PART_RESERVEE_AUX_AUTRES_NOMS = 4

#: La borne du lot soumis au score. **Nommée pour qu'un outil qui la mesure ne
#: la recopie pas** : un outil qui écrirait `2000` en dur continuerait à annoncer
#: « saturé » sur une borne qui aurait changé, ou le contraire.
#:
#: ⚠️ **Ce n'est pas un classement par pertinence.** L'`ORDER BY` posé le
#: 2026-09-16 rend le tirage REPRODUCTIBLE, pas MEILLEUR : sur 50 000
#: « gestion… », les 2 000 retenus restent une tranche alphabétique. *Savoir
#: combien de fois cette tranche est une COUPE est une mesure à part —
#: `outils/saturation_de_la_borne.py`.*
LIMITE_CANDIDATS_PAR_NOM = 2000


def candidats_par_nom(
    db_session: Session,
    nom_norm: str,
    limite: int | None = None,
    journal: dict | None = None,
) -> list[REQEntry]:
    """Les entrées du miroir soumises au score flou — **extraite pour être empruntée**.

    `resolve_neq_by_name` rend un classement; il ne dit pas si la liste est vide
    parce qu'AUCUN candidat n'a été récupéré ou parce qu'aucun candidat récupéré
    n'a passé le score. **Ce sont deux échecs différents, et ils appellent deux
    correctifs différents.** `outils/diagnostic_appariement.py` doit les distinguer,
    et il doit le faire sur la VRAIE récupération — une requête recopiée à côté
    mesurerait sa propre copie *(même règle que `requete_nom_exact` et
    `neq_retenu`)*.

    ⚠️ **La récupération est ancrée sur la TÊTE de la chaîne** : préfixe du premier
    mot, puis repli sur les six premiers caractères. *Une différence en tête — un
    article, un préfixe juridique, une enseigne au lieu de la raison sociale —
    n'abaisse pas le score : elle empêche le candidat d'être récupéré du tout.*

    `journal`, s'il est fourni, est REMPLI avec ce que la récupération a fait :
    combien de lignes chaque requête a rendues, si un repli a servi, si le pont a
    rogné la liste principale. **Il vaut `None` en production et ne change rien
    au résultat** — il existe pour qu'un outil mesure la VRAIE récupération au
    lieu d'en recopier une à côté *(même règle que `requete_nom_exact`,
    `neq_retenu` et `famille_de`)*.
    """
    # ⚠️ **La borne est lue À L'APPEL, pas figée à la définition.** *Écrite en
    # valeur par défaut (`limite: int = LIMITE_CANDIDATS_PAR_NOM`), la constante
    # était décorative : Python l'évalue une fois à l'import, et la changer
    # ensuite — dans un test, dans un outil — n'avait aucun effet.* **Une
    # constante qu'on ne peut pas faire varier n'est pas la source de vérité,
    # c'est une copie de plus.** *(Relevé le 2026-09-17, par un test qui passait
    # sur un lot non coupé.)*
    if limite is None:
        limite = LIMITE_CANDIDATS_PAR_NOM
    if journal is not None:
        journal["limite"] = limite
        journal["prefixe"] = nom_norm.split(" ")[0] if nom_norm else ""
    prefix = nom_norm.split(" ")[0]
    # ⚠️ **`ORDER BY` OBLIGATOIRE AVEC `LIMIT`** *(2026-09-16, relevé par
    # Alexandre)*. Un `LIMIT` sans ordre ne rend pas « les 2 000 meilleurs » : il
    # rend **2 000 lignes au hasard de l'index**, et « au hasard » veut dire
    # *susceptible de changer entre deux exécutions* — après un réimport, après
    # un `VACUUM`, après une insertion. **Deux passages du même rejeu pouvaient
    # donner deux chiffres différents**, et une passe qui ÉCRIT dans la base ne
    # peut pas s'appuyer là-dessus.
    #
    # L'ordre est celui de l'index (`nom_normalise`), donc SQLite le suit sans
    # trier — le coût est nul sur le chemin GLOB. Le repli par sous-chaîne
    # balaie déjà la table entière; y ajouter un tri borné à `limite` lignes ne
    # change pas son ordre de grandeur.
    #
    # ⚠️ **Ce n'est pas un classement par PERTINENCE.** Trier par `nom_normalise`
    # rend le tirage REPRODUCTIBLE, pas meilleur : sur 50 000 « gestion… », les
    # 2 000 retenus restent une tranche alphabétique arbitraire. *Rendre la
    # récupération pertinente est un autre chantier, et il reste ouvert.*
    # GLOB plutôt que LIKE, pour la recherche par préfixe — vérifié (2026-08-31,
    # après le premier import réel du REQ, ~2,7M lignes) : LIKE 'prefix%' avec un
    # paramètre lié force SQLite à un SCAN complet de la table (150x plus lent,
    # confirmé par EXPLAIN QUERY PLAN), parce que la comparaison par défaut de LIKE
    # est insensible à la casse et l'index n'a pas de collation NOCASE. GLOB est
    # nativement sensible à la casse, ce qui permet à SQLite d'utiliser l'index en
    # SEARCH — sans perte de correspondance puisque nom_normalise et prefix sont
    # déjà tous deux passés par _normaliser() (minuscules uniquement) des deux
    # côtés. _normaliser() ne produit que [a-z0-9 ] — jamais de métacaractère GLOB
    # (*, ?, [, ]) — donc aucun échappement n'est nécessaire ici.
    candidates = (
        db_session.execute(
            select(REQEntry)
            .where(REQEntry.nom_normalise.op("GLOB")(f"{prefix}*"))
            .order_by(REQEntry.nom_normalise, REQEntry.neq)
            .limit(limite)
        )
        .scalars()
        .all()
    )
    if journal is not None:
        journal["glob_principal"] = len(candidates)
        journal["repli_principal"] = not candidates
    if not candidates:
        # repli : recherche par sous-chaîne si le préfixe est trop restrictif
        candidates = (
            db_session.execute(
                select(REQEntry)
                .where(REQEntry.nom_normalise.contains(nom_norm[:6]))
                .order_by(REQEntry.nom_normalise, REQEntry.neq)
                .limit(limite)
            )
            .scalars()
            .all()
        )

    # --- LES AUTRES NOMS DE L'ENTREPRISE (chantier du 2026-09-16) -------------
    # `REQEntry.nom_normalise` ne porte QUE la dénomination sociale élue. Mesuré :
    # 41,7 % des NEQ portent plusieurs noms en vigueur, et 2 217 des 8 395
    # entreprises non résolues s'apparient EXACTEMENT à un nom que le chargeur
    # jetait — dont 98,8 % de sociétés par actions.
    #
    # La même requête, sur `req_noms` : même préfixe GLOB, même repli, même borne.
    # **Une recherche qui ne couvrirait pas les deux tables ferait dépendre le
    # résultat de la table où le nom se trouve**, ce qu'aucun appelant ne peut savoir.
    neqs_deja = {c.neq for c in candidates}
    autres = (
        db_session.execute(
            select(REQNom.neq)
            .where(REQNom.nom_normalise.op("GLOB")(f"{prefix}*"))
            .order_by(REQNom.nom_normalise, REQNom.neq)
            .limit(limite)
        )
        .scalars()
        .all()
    )
    if journal is not None:
        journal["pont_glob"] = len(autres)
        journal["repli_pont"] = not autres
    if not autres:
        autres = (
            db_session.execute(
                select(REQNom.neq)
                .where(REQNom.nom_normalise.contains(nom_norm[:6]))
                .order_by(REQNom.nom_normalise, REQNom.neq)
                .limit(limite)
            )
            .scalars()
            .all()
        )
    if journal is not None:
        journal["principal_retenu"] = len(candidates)
        journal["pont_brut"] = len(autres)
    manquants = [n for n in dict.fromkeys(autres) if n not in neqs_deja]
    if journal is not None:
        journal["pont_manquants"] = len(manquants)
        journal["rognage"] = 0
        journal["pont_ajoutes"] = 0
    if manquants:
        # ⚠️ UNE PART RÉSERVÉE, et non « ce qui reste ». **Corrigé le 2026-09-16,
        # après un réimport qui n'a rien changé du tout.**
        #
        # La version précédente prenait `reste = limite - len(candidates)`. La
        # borne était bien respectée — *et le pont n'ajoutait JAMAIS personne dès
        # que la première requête saturait la borne.* Or le préfixe de
        # récupération est le PREMIER MOT du nom : « gestion », « les »,
        # « construction », « entreprises ». **La saturation n'est pas un cas
        # limite, c'est le cas courant — et c'est exactement là que le pont
        # servirait.**
        #
        # *Mesuré : 1 505 879 noms ajoutés au miroir, et le diagnostic inchangé À
        # L'UNITÉ PRÈS sur trois catégories (3 061 ambigus, 313 résolubles).* Pas
        # « peu de gain » : zéro effet. **Une borne qui protège du coût en
        # supprimant l'apport protège du gain.**
        #
        # Ici, le pont a un PLANCHER garanti, et la liste principale est rognée
        # pour lui faire place. Le total reste borné par `limite` : le coût ne
        # bouge pas. *Et les candidats du pont valent mieux que ceux qu'ils
        # remplacent* — ils sont ciblés par leur préfixe, là où les derniers de
        # la liste principale sont une tranche arbitraire (le `LIMIT` n'a pas
        # d'`ORDER BY` : sur 50 000 « gestion… », SQLite en rend 2 000 au hasard
        # de l'index).
        reserve = min(len(manquants), max(1, limite // PART_RESERVEE_AUX_AUTRES_NOMS))
        place = limite - reserve
        if len(candidates) > place:
            if journal is not None:
                journal["rognage"] = len(candidates) - place
            candidates = list(candidates)[:place]
        a_chercher = manquants[: limite - len(candidates)]
        if journal is not None:
            journal["pont_ajoutes"] = len(a_chercher)
        if a_chercher:
            candidates = list(candidates) + list(
                db_session.execute(
                    select(REQEntry).where(REQEntry.neq.in_(a_chercher))
                )
                .scalars()
                .all()
            )

    if journal is not None:
        journal["total"] = len(candidates)
        journal["sature"] = len(candidates) >= limite
    return candidates


def _formes_transformees(
    db_session: Session, candidates: list, transformer_forme: "Callable[[str], str]"
) -> dict[str, list[str]]:
    """Les formes de chaque NEQ, reconstruites depuis les noms BRUTS, transformées,
    puis renormalisées. **Chemin de SIMULATION uniquement.**

    ⚠️ **Pourquoi les noms bruts, et pas la colonne normalisée.** `_normaliser`
    remplace la ponctuation par des espaces : `« Canada inc. (Workstaff) »`
    devient `« canada inc workstaff »`. *Les parenthèses ont disparu comme
    caractères, et leur CONTENU est resté comme mot.* Une transformation qui
    retire « le contenu entre parenthèses » ne peut donc rien faire sur la forme
    normalisée — elle n'y trouve plus de parenthèse à laquelle s'accrocher.

    **Simuler le retrait côté registre depuis `nom_normalise` rendrait un
    NO-OP déguisé en mesure.** D'où la relecture des noms publiés.
    """
    formes: dict[str, list[str]] = {}
    neqs = [c.neq for c in candidates]
    for c in candidates:
        forme = _normaliser(transformer_forme(c.nom or ""))
        if forme:
            formes.setdefault(c.neq, []).append(forme)
    for neq, nom in db_session.execute(
        select(REQNom.neq, REQNom.nom).where(REQNom.neq.in_(neqs))
    ).all():
        forme = _normaliser(transformer_forme(nom or ""))
        if forme:
            formes.setdefault(neq, []).append(forme)
    return formes


class DecoupeurDivergent(RuntimeError):
    """L'index par mots et la requête ne découpent pas pareil. **L'import
    refuse**, parce que le défaut ne se verrait nulle part ailleurs."""


def refuser_si_le_decoupeur_diverge(db_session: Session, combien: int = 20) -> None:
    """Un nom de `req_noms` doit se retrouver LUI-MÊME par l'index par mots.

    ⚠️ **C'est le seul garde possible contre deux découpeurs.** *Une divergence
    ne lève pas, ne journalise rien, et ne se voit qu'à la baisse du rappel —
    des jours plus tard, sur un chiffre qu'on attribuera à autre chose.*

    **Vingt formes prises dans l'ordre de la clé** — donc reproductibles, et pas
    un tirage. *Chacune doit rendre son propre NEQ parmi les candidats.*
    """
    from falkye.models.req_nom import REQNom

    echantillon = db_session.execute(
        select(REQNom.neq, REQNom.nom_normalise)
        .where(REQNom.nom_normalise != "")
        .order_by(REQNom.neq, REQNom.nom_normalise)
        .limit(combien)
    ).all()
    manques: list[tuple[str, str]] = []
    for neq, forme in echantillon:
        trouves = {c.neq for c in candidats_par_mot_rare(db_session, forme)}
        if neq not in trouves:
            manques.append((neq, forme))
    if not manques:
        return
    detail = "; ".join(f"{neq} ← {forme!r}" for neq, forme in manques[:5])
    raise DecoupeurDivergent(
        "REQ : l'index par mots ne retrouve pas des formes qu'il porte — "
        f"{len(manques)} sur {len(echantillon)} témoins échouent ({detail}). "
        "L'index et la requête ne découpent pas pareil : `mots_du_nom` d'un côté, "
        "le découpage SQL de `construire_index_par_mots` de l'autre. Une "
        "divergence ne lève nulle part ailleurs — elle fait seulement baisser le "
        "rappel, et le chiffre sera attribué à autre chose."
    )


def mots_du_nom(nom_norm: str) -> list[str]:
    """Le découpage en mots d'une forme normalisée.

    ⚠️ **LE MÊME des deux côtés, et c'est la seule dégradation silencieuse qui
    guette l'index par mots.** *`construire_index_par_mots` découpe sur l'espace
    en SQL; cette fonction découpe sur l'espace en Python.* **Si les deux
    divergeaient, le rappel baisserait sans qu'aucune erreur ne se produise** —
    d'où une fonction nommée, empruntée, et un témoin à chaque import.

    `nom_normalise` ne porte que `[a-z0-9 ]` *(`column_mapping.normaliser`)* :
    une espace sépare deux mots, et rien d'autre ne sépare quoi que ce soit.
    """
    return [mot for mot in nom_norm.split(" ") if mot]


#: Au-delà de ce nombre de NEQ, un mot est jugé trop courant pour borner seul le
#: lot — on l'INTERSECTE alors avec le deuxième plus rare. *C'est le point aveugle
#: nommé dans la conception du 17 septembre : « les entreprises du québec » n'a
#: aucun mot rare, et l'intersection est ce qui le rattrape.*
#:
#: ⚠️ **Ce n'est pas une échelle de décision** — ni seuil de score, ni écart. Il
#: ne change jamais QUI est retenu : il change combien de formes sont présentées
#: au scoreur. *Une valeur plus basse rend un lot plus petit, jamais un
#: appariement différent à lot égal.*
MOT_TROP_COURANT = 5000


def candidats_par_mot_rare(
    db_session: Session,
    nom_norm: str,
    limite: int | None = None,
    journal: dict | None = None,
) -> list[REQEntry]:
    """Les entrées dont au moins une forme partage **le mot le plus RARE** du nom.

    **Pourquoi le plus rare et non le premier.** *`ferme leger parent` se
    récupère par `parent`* — quelques dizaines de NEQ — **au lieu de `ferme`, qui
    en rend 23 061 dont on ne voit que 8,7 %.**

    ⚠️ **Et si même le plus rare est trop courant, on INTERSECTE avec le
    deuxième.** *C'est le point aveugle des noms faits de mots courants, et il est
    traité plutôt que laissé ouvert.*

    Rend une liste d'`REQEntry`, comme `candidats_par_nom` — *pour que le second
    temps passe par le même scorage, sans le savoir.*
    """
    from falkye.models.req_mot import REQMot, REQMotFrequence

    if limite is None:
        limite = LIMITE_CANDIDATS_PAR_NOM
    mots = mots_du_nom(nom_norm)
    if journal is not None:
        journal["mots_du_nom"] = len(mots)
    if not mots:
        return []

    frequences = dict(db_session.execute(
        select(REQMotFrequence.mot, REQMotFrequence.neqs).where(
            REQMotFrequence.mot.in_(mots)
        )
    ).all())
    # ⚠️ **À fréquence ÉGALE, le mot le plus LONG gagne** — et le départage par
    # ordre alphabétique est refusé. *Sur un index réel « du » est partout, donc
    # jamais le plus rare; mais rien ne garantit qu'un mot vide ne se retrouve
    # pas à égalité, et choisir alors « du » plutôt que « mondiale » serait un
    # tirage promu en critère.* **La longueur est une règle énoncée, contestable
    # et reproductible; l'alphabet n'est rien de tout ça.**
    connus = sorted((n, -len(mot), mot) for mot, n in frequences.items())
    connus = [(n, mot) for n, _longueur, mot in connus]
    if journal is not None:
        journal["mots_connus"] = len(connus)
        journal["frequence_du_plus_rare"] = connus[0][0] if connus else None
    if not connus:
        # ⚠️ **Aucun mot du nom n'est à l'index.** *Ce n'est pas « pas de
        # candidat » : c'est « l'index ne connaît pas ce vocabulaire »*, et les
        # deux appellent des correctifs différents.
        if journal is not None:
            journal["aucun_mot_a_lindex"] = True
        return []

    combien, mot = connus[0]
    requete = select(REQMot.neq).where(REQMot.mot == mot)
    if combien > MOT_TROP_COURANT and len(connus) > 1:
        # L'intersection est faite par SQLite, pas en mémoire.
        second = connus[1][1]
        requete = requete.intersect(
            select(REQMot.neq).where(REQMot.mot == second)
        )
        if journal is not None:
            journal["mot_intersecte"] = second
    # ⚠️ **Le bind explicite.** *Un `INTERSECT` produit un SELECT composé dont
    # SQLAlchemy ne sait plus déduire la base* — la session est liée par MODÈLE,
    # et le composé n'en porte aucun. **Il lève plutôt que de deviner, et c'est
    # bien : deviner enverrait la requête à la base du produit.**
    neqs = list(db_session.execute(
        requete.limit(limite), bind_arguments={"mapper": REQMot}
    ).scalars().all())
    if journal is not None:
        journal["mot_retenu"] = mot
        journal["neqs_par_le_mot"] = len(neqs)
    if not neqs:
        return []
    return list(db_session.execute(
        select(REQEntry).where(REQEntry.neq.in_(neqs))
    ).scalars().all())


def resolve_neq_by_name(
    db_session: Session,
    nom: str,
    ville: str | None = None,
    limit: int = 5,
    transformer_forme: Callable[[str], str] | None = None,
    limite_candidats: int | None = None,
    journal: dict | None = None,
    elargir: bool = True,
) -> list[REQMatch]:
    """Résout un nom d'entreprise en candidats NEQ, par correspondance floue sur le
    miroir local. Nécessite que ingest_snapshot() ait déjà été exécuté au moins une
    fois (sinon la table req_entries est vide et rien ne peut être résolu — c'est
    un état normal avant le premier scan REQ, pas une erreur).

    `transformer_forme` reçoit le nom PUBLIÉ de chaque forme du registre (jamais
    sa forme normalisée — voir `_formes_transformees`), et son résultat est
    renormalisé avant d'être scoré. **Il vaut `None` en production et le chemin est alors
    strictement celui d'avant** — il existe pour qu'un outil qui SIMULE une
    correction de données (ex. retirer le contenu entre parenthèses des deux
    côtés) emprunte ce scoreur au lieu d'en recopier un à côté.

    ⚠️ *Recopier ce scoreur, c'est mesurer sa copie* : il regroupe par NEQ, prend
    le MEILLEUR des noms de chaque NEQ (`req_noms` compris) et ajoute le bonus de
    ville. Une copie qui scorerait la seule dénomination sociale élue, sans bonus,
    rendrait des scores plus bas — et ferait passer un défaut d'instrument pour
    une perte de la correction. *(Hameçon posé le 2026-09-17, après exactement
    cette confusion.)*

    Il ne touche PAS la récupération : `candidats_par_nom` cherche sur le nom
    DÉTECTÉ. Transformer le nom détecté change donc les lignes rendues; le
    transformateur, lui, ne change que les scores.

    `limite_candidats` remplace la borne de RÉCUPÉRATION. Il vaut `None` en
    production — la borne est alors `LIMITE_CANDIDATS_PAR_NOM`, comme avant.

    ⚠️ **Il existe pour SIMULER une borne levée, sur un échantillon, et pour rien
    d'autre.** *Un préfixe comme `l` rend 309 788 lignes : une borne levée en
    production coûterait sur CHAQUE résolution ce qu'une mesure coûte une fois.*
    Le passer depuis le pipeline serait un changement de règle sans Alexandre.

    `journal`, comme pour `candidats_par_nom`, est rempli avec ce que la
    récupération a fait. `None` en production.

    ## ⚠️ DEUX TEMPS — et le second ne s'exécute que là où le premier échoue

    **Premier temps** : le préfixe, inchangé. **Si `neq_retenu` rend un NEQ, on
    s'arrête là.** *Les 805 dossiers retenus aujourd'hui ne voient jamais le
    second temps : la non-régression est STRUCTURELLE, pas mesurée.*

    **Second temps** : les NEQ qui partagent **le mot le plus RARE** du nom
    (`candidats_par_mot_rare`), ajoutés en **UNION** au lot du préfixe — *jamais
    en remplacement*. Puis le même scorage, par la même fonction.

    `elargir=False` coupe le second temps — **pour mesurer l'état d'avant**, et
    pour rien d'autre.
    """
    nom_norm = _normaliser(nom)
    if not nom_norm:
        return []

    candidates = candidats_par_nom(
        db_session,
        nom_norm,
        journal=journal,
        **({} if limite_candidats is None else {"limite": limite_candidats}),
    )
    matches = _scorer(db_session, nom_norm, candidates, ville, limit, transformer_forme)

    # ---- LE SECOND TEMPS ----------------------------------------------------
    #
    # ⚠️ **Il ne s'exécute QUE là où le premier a échoué**, et c'est ce qui rend
    # la non-régression STRUCTURELLE : *les 805 dossiers retenus aujourd'hui ne
    # voient jamais cette branche.* **Toutes les autres directions envisagées le
    # 17 septembre demandaient une non-régression MESURÉE; celle-ci la rend
    # impossible à violer.**
    #
    # Ce qu'il élargit avec : **le mot le plus RARE du nom**, pas le premier.
    # *`l industrie mondiale du nord` se récupère par `mondiale`, et le gisement
    # de 309 788 lignes du préfixe `l` n'est jamais touché.*
    if not elargir:
        return matches
    from falkye.resolution import neq_retenu  # importé ici : `resolution` importe
    #                                           ce module, donc pas au sommet.
    if neq_retenu(matches) is not None:
        return matches
    supplement = candidats_par_mot_rare(
        db_session, nom_norm, limite=limite_candidats, journal=journal
    )
    deja = {c.neq for c in candidates}
    neufs = [c for c in supplement if c.neq not in deja]
    if journal is not None:
        journal["second_temps"] = True
        journal["mots_neufs"] = len(neufs)
    if not neufs:
        return matches
    # ⚠️ **UNION, jamais remplacement.** *Le lot du préfixe reste présenté* — un
    # candidat que le préfixe trouvait et que les mots ne trouvent pas ne doit
    # pas disparaître.
    return _scorer(
        db_session, nom_norm, list(candidates) + neufs, ville, limit, transformer_forme
    )


def _scorer(
    db_session: Session,
    nom_norm: str,
    candidates: list,
    ville: str | None,
    limit: int,
    transformer_forme: "Callable[[str], str] | None",
) -> list[REQMatch]:
    """Le SCORAGE, séparé de la RÉCUPÉRATION — *pour que le second temps rejoue
    la même règle et non une copie.* **C'est la leçon des -338 du 17 septembre,
    appliquée à la structure plutôt qu'à un outil.**"""
    if not candidates:
        return []

    # --- UN NEQ, UNE ENTITÉ (décision d'Alexandre, 2026-09-16) ---------------
    #
    # « Une entreprise n'a pas plusieurs identités parce qu'elle a plusieurs
    # noms. » **Le NEQ est l'entité; les noms ne sont que des portes vers elle.**
    #
    # Deux conséquences, et la seconde corrige un défaut du correctif du matin :
    #
    #   1. Le score d'un NEQ est le MEILLEUR de ses noms. Scorer la requête
    #      contre la seule dénomination sociale élue ferait retrouver
    #      `Ferme M.G. Bellavance` par la récupération, puis la comparerait à
    #      `9224-5842 QUÉBEC INC.` — score au plancher, refus. **La porte serait
    #      ouverte et le seuil infranchissable.**
    #   2. L'ambiguïté se compte sur les NEQ DISTINCTS. Deux noms du même NEQ qui
    #      se disputent la première place ne sont pas une ambiguïté : c'est la
    #      même entreprise deux fois. *Regrouper AVANT de comparer peut donc
    #      résoudre des cas aujourd'hui classés ambigus.*
    noms_par_neq: dict[str, list[str]] = {}
    for c in candidates:
        if c.nom_normalise:
            noms_par_neq.setdefault(c.neq, []).append(c.nom_normalise)
    for neq, forme in db_session.execute(
        select(REQNom.neq, REQNom.nom_normalise).where(
            REQNom.neq.in_([c.neq for c in candidates])
        )
    ).all():
        noms_par_neq.setdefault(neq, []).append(forme)

    if transformer_forme is not None:
        noms_par_neq = _formes_transformees(db_session, candidates, transformer_forme)

    by_neq = {c.neq: c for c in candidates}
    scores: list[tuple[str, float, str]] = []
    for neq, formes in noms_par_neq.items():
        # `process.extractOne` sur les noms DE CE NEQ : le meilleur l'emporte, et
        # les autres ne comptent pas — ils ne sont pas des concurrents, ils sont
        # la même entreprise.
        meilleur = process.extractOne(nom_norm, formes, scorer=fuzz.WRatio)
        if meilleur is not None:
            # ⚠️ **On garde AUSSI la forme gagnante.** *Sans elle, l'appelant
            # affiche la dénomination élue et fait lire la décision sur une
            # chaîne qui n'a pas décidé* — cas 33.
            scores.append((neq, meilleur[1], meilleur[0]))
    scores.sort(key=lambda t: t[1], reverse=True)

    matches = [
        REQMatch(entry=by_neq[neq], score=score, forme_normalisee=forme)
        for neq, score, forme in scores[:limit]
    ]

    if ville:
        ville_norm = _normaliser(ville)
        for m in matches:
            if m.entry.ville and _normaliser(m.entry.ville) == ville_norm:
                m.score = min(100.0, m.score + 5.0)  # léger bonus, ne domine jamais le score du nom

    return sorted(matches, key=lambda m: m.score, reverse=True)


def _stats_vers_signaux(stats: IngestStats) -> Iterator[RawSignal]:
    """Convertit les diffs détectés par ingest_snapshot en RawSignal — factorisé
    pour être identique que l'ingestion vienne du réseau (REQConnector.detect,
    dormant en Phase 1) ou d'un fichier importé manuellement
    (REQConnector.detect_from_file, actif en Phase 1 — voir docs/STATUT_RESEAU.md).

    Une NOUVELLE IMMATRICULATION (stats.nouveaux_etablissements, chemin plat
    legacy uniquement) n'est PAS un signal — une entreprise qui vient de
    naître n'est pas une entreprise EN croissance, et la traiter comme un
    signal violerait le principe de calibration (spec section 6 : distinguer
    un vrai signal de croissance du bruit). Seul le chemin réel (Entreprise.csv
    + Nom.csv + Etablissements.csv) produit les deux signaux confirmés par la
    spec (section 7, Signal 4) : nouvel établissement SECONDAIRE d'une
    entreprise déjà connue (fort) et changement d'adresse du siège (moyen)."""
    now = datetime.now(timezone.utc)

    for etab in stats.nouveaux_etablissements_secondaires:
        yield RawSignal(
            signal_type_id="registre_corporatif",
            nom_entreprise=etab.get("nom_etablissement") or "",
            detected_at=now,
            source_ref=f"req:etablissement_secondaire:{etab['neq']}:{etab['no_suf_etab']}",
            neq=etab["neq"],
            adresse=etab.get("adresse"),
            titre_ou_description="Nouvel établissement secondaire au REQ",
            champs={"type_changement": "nouvel_etablissement_secondaire", **etab},
        )

    for chgt in stats.changements_adresse:
        yield RawSignal(
            signal_type_id="registre_corporatif",
            nom_entreprise=chgt["nom"],
            detected_at=now,
            source_ref=f"req:changement_adresse:{chgt['neq']}:{chgt['nouvelle_adresse']}",
            neq=chgt["neq"],
            adresse=chgt["nouvelle_adresse"],
            titre_ou_description="Changement d'adresse au REQ",
            champs={"type_changement": "changement_adresse", **chgt},
        )


class REQConnector(SourceConnector):
    """La résolution NEQ pour les AUTRES sources passe par
    resolve_neq_by_name/get_by_neq ci-dessus, appelées directement par
    falkye/resolution.py (pas via detect()/detect_from_file()).

    `detect()` (téléchargement automatisé réseau) reste implémenté et
    fonctionnel, mais REQ n'est PLUS branché sur `detect()` dans le registre
    pour la Phase 1 (`methode_acces: import_manuel`, `connecteur` conservé
    uniquement pour `detect_from_file`) — le téléchargement automatisé depuis
    cette session cloud est bloqué par une règle Cloudflare visant les plages
    IP infonuagiques partagées, pas un problème avec cette méthode d'accès en
    soi (voir docs/STATUT_RESEAU.md pour l'analyse complète). Gardé au cas où
    l'accès redeviendrait praticable (réseau différent, levée du blocage)."""

    def detect(self, since, db_session: Session) -> Iterator[RawSignal]:
        stats = ingest_snapshot(db_session, limit=None)
        logger.info(
            "REQ (réseau): %s lignes lues, %s nouvelles, %s mises à jour, %s changements d'adresse retenus",
            stats.lignes_lues,
            stats.entrees_nouvelles,
            stats.entrees_mises_a_jour,
            len(stats.changements_adresse),
        )
        yield from _stats_vers_signaux(stats)

    def inspect_file(self, path) -> dict[str, dict]:
        """Voir inspect_zip ci-dessus — à lancer sur le vrai ZIP téléchargé par
        Alexandre AVANT le premier `import-manuel fichier`, pour confirmer les
        vraies colonnes des 6 CSV liés plutôt que de deviner (découverte du
        2026-08-31, voir docs/STATUT_RESEAU.md)."""
        return inspect_zip(path)

    def detect_from_file(
        self, path, db_session: Session, *, limit: int | None = None
    ) -> Iterator[RawSignal]:
        """Chemin ACTIF en Phase 1 (spec section 9, "Import manuel de documents
        sources") : Alexandre télécharge lui-même le fichier en vrac depuis
        https://www.donneesquebec.ca/recherche/dataset/registre-des-entreprises
        (lien direct vers la ressource ZIP, voir SourceDef.lien_recherche dans
        registry/sources.yaml) et l'importe via
        `falkye import-manuel req --fichier <chemin>`. Réutilise EXACTEMENT
        la même logique de parsing/diff que le chemin automatisé
        (ingest_snapshot), seule la provenance du fichier change.

        `limit` est transmis tel quel à `ingest_snapshot` — CRITIQUE pour le
        chemin réel (`_ingest_zip_req_reel`) : celui-ci ne produit ses signaux
        qu'APRÈS avoir traité tout Entreprise.csv (pas un générateur
        ligne-par-ligne), donc un bornage appliqué seulement aux signaux
        produits par l'appelant (comme le fait manual_import.
        importer_fichier_source en filet de sécurité) ne réduirait pas le
        volume réellement lu — seul `ingest_snapshot(limit=...)` le fait."""
        stats = ingest_snapshot(db_session, limit=limit, fichier_local=path)
        logger.info(
            "REQ (fichier importé): %s lignes lues, %s nouvelles, %s mises à jour, %s changements d'adresse retenus",
            stats.lignes_lues,
            stats.entrees_nouvelles,
            stats.entrees_mises_a_jour,
            len(stats.changements_adresse),
        )
        yield from _stats_vers_signaux(stats)


CONNECTOR_CLASS = REQConnector
