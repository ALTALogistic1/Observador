"""Connecteur Corporations Canada (ISED) — spec section 7, Signal 4. Équivalent
fédéral du REQ, mais pancanadien — couvre les entreprises incorporées sous une
loi fédérale partout au Canada (répond au besoin de couverture Canada anglais).

Jeu de données CKAN "Federal Corporations" (0032ce54-c5dd-4b66-99a0-320a7b5e99f2)
sur open.canada.ca, dont les ressources (CSV, 4 sous-ensembles : sociétés par
actions actives/inactives, autres corporations actives/inactives — CHACUN
publié en français ET en anglais, mêmes corporations sous en-têtes traduites,
même nom de ressource dans les deux langues — voir `_filtrer_langue_francaise`,
découverte le 2026-09-04) sont en réalité hébergées sur
`d4bf66bykfyaf.cloudfront.net` (CloudFront/AWS) — domaine autorisé et validé
avec le vrai fichier le 2026-08-31 (694 844 corporations actives réelles
ingérées — voir docs/STATUT_RESEAU.md). `COLUMN_ALIASES` reflète les vraies
en-têtes françaises confirmées, pas une estimation — les ressources anglaises
sont délibérément exclues plutôt que doublées ou mal mappées.

Rôle : SOURCE DE SIGNAL en soi, par diff entre deux rafraîchissements du
miroir local (CorporationFederaleEntry). Ce n'est PAS un pivot de résolution
de Company partagé avec les autres sources (voir docs/ARCHITECTURE.md,
"Généralisation du pivot d'identité", décision inchangée) : le NEQ reste le
seul pivot pour resolve_company. Ce module expose en revanche (2026-09-01,
pour licences_affaires_municipales) `resolve_corp_federale_by_name`, une
vérification croisée plus étroite — confirmer qu'un nom détecté correspond à
une corporation fédérale EXISTANTE, comme porte de calibration pour une
source hors Québec, jamais pour résoudre un Company — voir la docstring de
falkye/models/corp_federale_entry.py pour la distinction complète.

CORRECTION DE CALIBRATION (2026-08-31, en validant avec le vrai fichier, 111 Mo
/ ~695 000 corporations actives) : le code d'origine traitait toute NOUVELLE
corporation détectée par le diff comme un signal — au premier import réel,
ça aurait produit ~695 000 signaux (une nouvelle incorporation n'est pas une
entreprise EN croissance, exactement le même problème identifié et corrigé
pour le REQ le même jour — voir docs/STATUT_RESEAU.md). Corrigé : seul un
changement d'ADRESSE pour une corporation DÉJÀ connue produit un signal
(analogue au "changement d'adresse du siège" du REQ) — une toute nouvelle
incorporation ne produit plus rien.
"""
from __future__ import annotations

import csv
import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone

from dateutil import parser as dateutil_parser
from rapidfuzz import fuzz, process
from sqlalchemy import select
from sqlalchemy.orm import Session

from falkye.diff_engine import LigneSnapshot, executer_diff, seuils_depuis_registre
from falkye.models.corp_federale_entry import CorporationFederaleEntry
from falkye.registry.loader import get_registry
from falkye.sources.base import RawSignal, SourceConnector
from falkye.sources.ckan_client import OPEN_CANADA_BASE, CKANClient
from falkye.sources.column_mapping import normaliser as _normaliser
from falkye.sources.column_mapping import resolve_columns

logger = logging.getLogger(__name__)

CORPORATIONS_PACKAGE_ID = "0032ce54-c5dd-4b66-99a0-320a7b5e99f2"

# Alias vérifiés contre les vraies en-têtes du fichier réel (2026-08-31) :
# 'Numéro de société', 'Dénomination sociale - version 1', 'Régime législatif',
# 'Statut', 'Rue', 'Municipalité/ville', 'Province/territoire', 'Code postal'.
# PAS de colonne "date d'incorporation" dans le fichier réel (seulement "Date
# d'anniversaire", "Année du dernier dépôt annuel" — aucune n'est fiablement la
# date de constitution) : ce champ n'est donc PAS extrait, plutôt que de
# deviner un mapping incorrect vers un champ qui ne veut pas dire la même
# chose. L'adresse est composée à partir de plusieurs colonnes (pas une seule
# colonne "adresse" comme espéré à l'origine) — voir _upsert_row.
COLUMN_ALIASES: dict[str, list[str]] = {
    "numero": ["numero_de_societe"],
    "nom": ["denomination_sociale_version_1"],
    "statut": ["statut"],
    "rue": ["rue"],
    "ville": ["municipalite_ville"],
    "province": ["province_territoire"],
    "code_postal": ["code_postal"],
}
# Alias optionnels — best-effort, ne bloquent pas l'ingestion s'ils sont absents.
COLUMN_ALIASES_OPTIONNELS: dict[str, list[str]] = {
    "loi": ["regime_legislatif"],
}

STATUTS_ACTIFS = {"active", "actif", "active corporation"}

# Rebranchement sur le moteur de diff générique (Chantier 1, suivi 2026-09-04)
# — un seul grain ici (pas de sous-structure "établissement" comme le REQ),
# le vocabulaire logique correspond directement à registry/sources.yaml:
# corporations_canada.champs_pertinents.
CHAMPS_PERTINENTS_CORP = {
    "numero_corporation_federale", "nom", "statut", "adresse_bureau_enregistre", "date_incorporation",
    "loi_constitutive",
}


def _parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = dateutil_parser.parse(raw)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError):
        return None


@dataclass
class IngestStats:
    lignes_lues: int = 0
    nouvelles_corporations_actives: list[dict] = field(default_factory=list)  # comptage/audit seulement, pas un signal
    changements_adresse: list[dict] = field(default_factory=list)
    # Rebranchement chantier 1 : un run mis en quarantaine par falkye/
    # diff_engine.py ne touche NI CorporationFederaleEntry NI aucun signal.
    quarantaine: bool = False
    quarantaine_motif: str | None = None


def _filtrer_ressources_actives(resources: list[dict]) -> list[dict]:
    """Exclut les ressources "inactive" d'une liste déjà filtrée par
    name_contains="active" — DÉCOUVERTE (2026-08-31) : "inactive" contient la
    sous-chaîne "active", donc un simple name_contains="active" attrape aussi
    "Other inactive corporations"/"Inactive business corporations", d'où des
    lignes "Dissoute" dans les résultats sans cette exclusion explicite."""
    return [r for r in resources if "inactive" not in (r.get("name") or "").lower()]


def _filtrer_langue_francaise(resources: list[dict]) -> list[dict]:
    """DÉCOUVERTE (2026-09-04, en rebranchant sur le moteur générique — voir
    docs/ARCHITECTURE.md) : le jeu de données publie chaque catégorie
    "active" en DEUX exemplaires — français ET anglais, mêmes corporations,
    en-têtes traduites — avec le MÊME nom de ressource dans les deux langues
    (le filtre par nom ci-dessus ne peut donc pas les distinguer). Sans ce
    filtre, la boucle d'ingestion planterait sur les en-têtes anglaises
    (COLUMN_ALIASES ne connaît que le français, délibérément — voir plus
    haut) ou, si l'alias était étendu aux deux langues, doublerait chaque
    corporation. Le champ `language` de CKAN distingue les deux versions de
    façon fiable (vérifié en direct : ['fr'] vs ['en']). Une ressource sans
    champ `language` (fixtures de test, ou futur jeu de données unilingue)
    est conservée par prudence plutôt que silencieusement exclue."""
    return [r for r in resources if not r.get("language") or "fr" in r["language"]]


@dataclass(frozen=True)
class _CorporationResolue:
    numero: str
    nom: str
    statut_brut: str
    adresse: str | None
    province: str | None
    loi: str | None


def _resoudre_corporation(row: dict, columns: dict[str, str], colonnes_optionnelles: dict[str, str]) -> _CorporationResolue | None:
    """Extraction PURE (aucune écriture, aucune décision de diff) d'une ligne
    brute — voir ingest_snapshot pour la séparation en deux phases."""
    numero = (row.get(columns["numero"]) or "").strip()
    if not numero:
        return None
    nom = (row.get(columns["nom"]) or "").strip()
    statut_brut = (row.get(columns["statut"]) or "").strip()
    province = (row.get(columns["province"]) or "").strip() or None

    parties_adresse = [
        (row.get(columns["rue"]) or "").strip(),
        (row.get(columns["ville"]) or "").strip(),
        province or "",
        (row.get(columns["code_postal"]) or "").strip(),
    ]
    adresse = ", ".join(p for p in parties_adresse if p) or None

    loi = None
    if "loi" in colonnes_optionnelles:
        loi = (row.get(colonnes_optionnelles["loi"]) or "").strip() or None

    return _CorporationResolue(numero=numero, nom=nom, statut_brut=statut_brut, adresse=adresse, province=province, loi=loi)


def _ligne_corporation(r: _CorporationResolue) -> LigneSnapshot:
    return LigneSnapshot(
        cle=r.numero,
        champs={
            "numero_corporation_federale": r.numero,
            "nom": r.nom,
            "statut": r.statut_brut,
            "adresse_bureau_enregistre": r.adresse,
            "date_incorporation": None,  # jamais dérivée de façon fiable — voir docstring module
            "loi_constitutive": r.loi,
        },
    )


def _upsert_corporation(db_session: Session, r: _CorporationResolue) -> None:
    """Upsert PUR de CorporationFederaleEntry — plus aucune décision de diff
    ici, seulement appelé APRÈS que le moteur générique ait confirmé que ce
    run n'est pas en quarantaine."""
    existing = db_session.get(CorporationFederaleEntry, r.numero)
    if existing is None:
        db_session.add(
            CorporationFederaleEntry(
                numero_corporation=r.numero, nom=r.nom, nom_normalise=_normaliser(r.nom),
                statut=r.statut_brut, adresse=r.adresse, province=r.province,
                loi_constitutive=r.loi, date_incorporation=None,
            )
        )
    else:
        existing.nom = r.nom
        existing.nom_normalise = _normaliser(r.nom)
        existing.statut = r.statut_brut
        existing.adresse = r.adresse
        existing.province = r.province
        existing.loi_constitutive = r.loi
        existing.date_incorporation = None


def ingest_snapshot(db_session: Session, limit: int | None = None) -> IngestStats:
    """Télécharge les ressources "corporations actives" (une par langue/type) et
    met à jour le miroir local, en détectant les changements pertinents par
    comparaison à l'état précédemment connu. Rebranché sur le moteur de diff
    générique (Chantier 1, suivi 2026-09-04) — DEUX PHASES, comme falkye/
    sources/req.py::_ingest_zip_req_reel : la phase 1 construit l'instantané
    SANS RIEN ÉCRIRE (ici), la phase 2 (upsert + dérivation des signaux, voir
    `_traiter_instantane`) n'a lieu QUE si le moteur confirme que ce run n'est
    pas en quarantaine — un import corrompu ne doit rien écrire nulle part,
    pas seulement s'abstenir de signal."""
    client = CKANClient(OPEN_CANADA_BASE)
    resources = _filtrer_langue_francaise(
        _filtrer_ressources_actives(
            client.resources(CORPORATIONS_PACKAGE_ID, format_filter="CSV", name_contains="active")
        )
    )
    if not resources:
        raise RuntimeError(
            f"Aucune ressource CSV 'active' trouvée pour {CORPORATIONS_PACKAGE_ID!r} — "
            "le jeu de données a peut-être changé de structure."
        )

    lignes: list[LigneSnapshot] = []
    resolues: list[_CorporationResolue] = []
    lignes_lues = 0
    colonnes_vues: dict[str, str] = {}

    for resource in resources:
        path = client.download(resource)
        with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            columns = resolve_columns(fieldnames, COLUMN_ALIASES)
            colonnes_optionnelles: dict[str, str] = {}
            for logical, aliases in COLUMN_ALIASES_OPTIONNELS.items():
                try:
                    colonnes_optionnelles.update(resolve_columns(fieldnames, {logical: aliases}))
                except ValueError:
                    pass  # champ optionnel absent — pas bloquant, mais compte pour colonnes_vues plus bas
            # numero/nom/statut/adresse_bureau_enregistre dépendent tous de
            # colonnes OBLIGATOIRES (resolve_columns aurait déjà levé une
            # exception sinon) — toujours "vues" une fois qu'on atteint ce
            # point. "loi_constitutive" est la seule dérivée d'une colonne
            # optionnelle — sa disparition SILENCIEUSE (aujourd'hui : devient
            # simplement None pour tout le monde, personne ne le remarque)
            # est exactement ce que le moteur doit détecter.
            colonnes_vues.setdefault("numero_corporation_federale", "str")
            colonnes_vues.setdefault("nom", "str")
            colonnes_vues.setdefault("statut", "str")
            colonnes_vues.setdefault("adresse_bureau_enregistre", "str")
            if "loi" in colonnes_optionnelles:
                colonnes_vues["loi_constitutive"] = "str"

            for row in reader:
                if limit is not None and lignes_lues >= limit:
                    break
                lignes_lues += 1
                r = _resoudre_corporation(row, columns, colonnes_optionnelles)
                if r is None:
                    continue
                resolues.append(r)
                lignes.append(_ligne_corporation(r))

        if limit is not None and lignes_lues >= limit:
            break

    return _traiter_instantane(db_session, lignes, resolues, colonnes_vues, lignes_lues)


def _traiter_instantane(
    db_session: Session,
    lignes: list[LigneSnapshot],
    resolues: list[_CorporationResolue],
    colonnes_vues: dict[str, str],
    lignes_lues: int,
) -> IngestStats:
    """Soumet l'instantané (déjà construit — voir `ingest_snapshot`) au moteur
    de diff générique, puis applique/dérive les signaux si non quarantiné.
    Extrait pour être testable SANS dépendance réseau (CKANClient) — les
    tests construisent `lignes`/`resolues`/`colonnes_vues` directement."""
    registry = get_registry()
    source_def = registry.sources.get("corporations_canada")
    seuils = seuils_depuis_registre(source_def.seuils_quarantaine) if source_def else None
    rapport = executer_diff(db_session, "corporations_canada", lignes, colonnes_vues, CHAMPS_PERTINENTS_CORP, seuils=seuils)

    stats = IngestStats(lignes_lues=lignes_lues)
    if rapport.quarantaine:
        stats.quarantaine = True
        stats.quarantaine_motif = rapport.motif_quarantaine.value if rapport.motif_quarantaine else None
        logger.warning(
            "Corporations Canada: import mis en quarantaine (%s) — CorporationFederaleEntry non touché, "
            "aucun signal produit. Voir `falkye quarantaine lister`.",
            stats.quarantaine_motif,
        )
        db_session.commit()
        return stats

    # --- Phase 2 : upsert du miroir (jamais de diff ici) ---
    for r in resolues:
        _upsert_corporation(db_session, r)

    # --- Dérivation des signaux à partir du diff déjà calculé par le moteur ---
    if rapport.run_reference:
        # Run de référence : amorce l'état, jamais de signal (une corporation
        # nouvellement DÉCOUVERTE par ce mécanisme n'est pas nouvellement
        # incorporée — voir la correction de calibration en tête du module).
        stats.nouvelles_corporations_actives = [
            {"numero": l.cle, "nom": l.champs["nom"], "adresse": l.champs["adresse_bureau_enregistre"]}
            for l in lignes
            if l.champs["statut"].lower() in STATUTS_ACTIFS
        ]
    else:
        stats.nouvelles_corporations_actives = [
            {"numero": l.cle, "nom": l.champs["nom"], "adresse": l.champs["adresse_bureau_enregistre"]}
            for l in rapport.resultat.apparitions
            if l.champs["statut"].lower() in STATUTS_ACTIFS
        ]
        for m in rapport.resultat.modifications:
            if (
                "adresse_bureau_enregistre" in m.champs_changes
                and m.champs_avant.get("adresse_bureau_enregistre") is not None
                and (m.champs_apres.get("statut") or "").lower() in STATUTS_ACTIFS
            ):
                stats.changements_adresse.append(
                    {
                        "numero": m.cle,
                        "nom": m.champs_apres.get("nom") or "",
                        "ancienne_adresse": m.champs_avant.get("adresse_bureau_enregistre"),
                        "nouvelle_adresse": m.champs_apres.get("adresse_bureau_enregistre"),
                    }
                )

    db_session.commit()
    return stats


@dataclass
class CorporationMatch:
    entry: CorporationFederaleEntry
    score: float  # 0-100, confiance de correspondance du nom


def get_by_numero(db_session: Session, numero: str) -> CorporationFederaleEntry | None:
    return db_session.get(CorporationFederaleEntry, numero)


def resolve_corp_federale_by_name(
    db_session: Session, nom: str, province: str | None = None, limit: int = 5
) -> list[CorporationMatch]:
    """Résout un nom d'entreprise en candidats de corporation fédérale, par
    correspondance floue sur le miroir local — même mécanique que
    req.py:resolve_neq_by_name, appliquée à un autre registre (voir la
    docstring de falkye/models/corp_federale_entry.py pour ce que c'est
    et n'est PAS : une porte de calibration, pas un pivot de résolution de
    Company). Nécessite que ingest_snapshot() ait déjà tourné au moins une
    fois (sinon la table est vide — état normal avant le premier scan, pas
    une erreur)."""
    nom_norm = _normaliser(nom)
    if not nom_norm:
        return []

    prefix = nom_norm.split(" ")[0]
    # GLOB plutôt que LIKE — même raison que pour REQEntry (voir req.py:
    # resolve_neq_by_name) : comparaison sensible à la casse, index B-tree
    # utilisable en SEARCH plutôt qu'un SCAN complet. nom_normalise ne
    # contient jamais de métacaractère GLOB (_normaliser() ne produit que
    # [a-z0-9 ]), donc aucun échappement n'est nécessaire.
    candidates = (
        db_session.execute(
            select(CorporationFederaleEntry)
            .where(CorporationFederaleEntry.nom_normalise.op("GLOB")(f"{prefix}*"))
            .limit(2000)
        )
        .scalars()
        .all()
    )
    if not candidates:
        candidates = (
            db_session.execute(
                select(CorporationFederaleEntry)
                .where(CorporationFederaleEntry.nom_normalise.contains(nom_norm[:6]))
                .limit(2000)
            )
            .scalars()
            .all()
        )
    if not candidates:
        return []

    choices = {c.numero_corporation: c.nom_normalise for c in candidates}
    ranked = process.extract(nom_norm, choices, scorer=fuzz.WRatio, limit=limit)

    by_numero = {c.numero_corporation: c for c in candidates}
    matches = [CorporationMatch(entry=by_numero[numero], score=score) for _, score, numero in ranked]

    if province:
        province_norm = _normaliser(province)
        for m in matches:
            if m.entry.province and _normaliser(m.entry.province) == province_norm:
                m.score = min(100.0, m.score + 5.0)  # léger bonus, même principe que la ville pour REQ

    return sorted(matches, key=lambda m: m.score, reverse=True)


class CorporationsCanadaConnector(SourceConnector):
    def detect(self, since, db_session: Session) -> Iterator[RawSignal]:
        stats = ingest_snapshot(db_session, limit=None)
        logger.info(
            "Corporations Canada: %s lignes lues, %s nouvelles corporations actives (non signalées, "
            "voir docstring module), %s changements d'adresse retenus",
            stats.lignes_lues,
            len(stats.nouvelles_corporations_actives),
            len(stats.changements_adresse),
        )
        now = datetime.now(timezone.utc)
        for chgt in stats.changements_adresse:
            yield RawSignal(
                signal_type_id="registre_corporatif",
                nom_entreprise=chgt["nom"],
                detected_at=now,
                source_ref=f"corporations_canada:changement_adresse:{chgt['numero']}:{chgt['nouvelle_adresse']}",
                adresse=chgt["nouvelle_adresse"],
                titre_ou_description="Changement d'adresse — corporation fédérale",
                champs={"type_changement": "changement_adresse", **chgt},
            )


CONNECTOR_CLASS = CorporationsCanadaConnector
