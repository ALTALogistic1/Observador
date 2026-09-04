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

import csv
import io
import logging
import re
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone

from dateutil import parser as dateutil_parser
from rapidfuzz import fuzz, process
from sqlalchemy import select
from sqlalchemy.orm import Session

from falkye.diff_engine import (
    LigneSnapshot,
    RapportExecution,
    SpecificationDiff,
    executer_diff_groupe,
    seuils_depuis_registre,
)
from falkye.models.req_entry import REQEntry
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
    return {neq: nom for neq, (_, _, nom) in meilleurs.items()}


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
    elif (row.get("ADR_DOMCL_ADR_DISP") or "").strip().upper() == "O":
        # Repli sur l'adresse du domicile (Entreprise.csv) — seulement quand aucun
        # établissement n'est trouvé ET qu'elle est marquée disponible (confirmé
        # réel : ADR_DOMCL_ADR_DISP='N' est fréquent, l'adresse est alors absente
        # même remplie, donc on ne l'utilise QUE si disponible='O').
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


def get_by_neq(db_session: Session, neq: str) -> REQEntry | None:
    return db_session.get(REQEntry, neq)


def resolve_neq_by_name(
    db_session: Session, nom: str, ville: str | None = None, limit: int = 5
) -> list[REQMatch]:
    """Résout un nom d'entreprise en candidats NEQ, par correspondance floue sur le
    miroir local. Nécessite que ingest_snapshot() ait déjà été exécuté au moins une
    fois (sinon la table req_entries est vide et rien ne peut être résolu — c'est
    un état normal avant le premier scan REQ, pas une erreur)."""
    nom_norm = _normaliser(nom)
    if not nom_norm:
        return []

    prefix = nom_norm.split(" ")[0]
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
            select(REQEntry).where(REQEntry.nom_normalise.op("GLOB")(f"{prefix}*")).limit(2000)
        )
        .scalars()
        .all()
    )
    if not candidates:
        # repli : recherche par sous-chaîne si le préfixe est trop restrictif
        candidates = (
            db_session.execute(
                select(REQEntry).where(REQEntry.nom_normalise.contains(nom_norm[:6])).limit(2000)
            )
            .scalars()
            .all()
        )

    if not candidates:
        return []

    choices = {c.neq: c.nom_normalise for c in candidates}
    ranked = process.extract(nom_norm, choices, scorer=fuzz.WRatio, limit=limit)

    by_neq = {c.neq: c for c in candidates}
    matches = [REQMatch(entry=by_neq[neq], score=score) for _, score, neq in ranked]

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
