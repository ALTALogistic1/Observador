"""Connecteur Corporations Canada (ISED) — spec section 7, Signal 4. Équivalent
fédéral du REQ, mais pancanadien — couvre les entreprises incorporées sous une
loi fédérale partout au Canada (répond au besoin de couverture Canada anglais).

Jeu de données CKAN "Federal Corporations" (0032ce54-c5dd-4b66-99a0-320a7b5e99f2)
sur open.canada.ca, dont les ressources (CSV, 4 sous-ensembles : sociétés par
actions actives/inactives, autres corporations actives/inactives) sont en
réalité hébergées sur `d4bf66bykfyaf.cloudfront.net` (CloudFront/AWS) — domaine
autorisé et validé avec le vrai fichier le 2026-08-31 (694 844 corporations
actives réelles ingérées — voir docs/STATUT_RESEAU.md). `COLUMN_ALIASES`
reflète les vraies en-têtes confirmées, pas une estimation.

Rôle : SOURCE DE SIGNAL en soi, par diff entre deux rafraîchissements du
miroir local (CorporationFederaleEntry). Ce n'est PAS un pivot de résolution
de Company partagé avec les autres sources (voir docs/ARCHITECTURE.md,
"Généralisation du pivot d'identité", décision inchangée) : le NEQ reste le
seul pivot pour resolve_company. Ce module expose en revanche (2026-09-01,
pour licences_affaires_municipales) `resolve_corp_federale_by_name`, une
vérification croisée plus étroite — confirmer qu'un nom détecté correspond à
une corporation fédérale EXISTANTE, comme porte de calibration pour une
source hors Québec, jamais pour résoudre un Company — voir la docstring de
observador/models/corp_federale_entry.py pour la distinction complète.

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

from observador.models.corp_federale_entry import CorporationFederaleEntry
from observador.sources.base import RawSignal, SourceConnector
from observador.sources.ckan_client import OPEN_CANADA_BASE, CKANClient
from observador.sources.column_mapping import normaliser as _normaliser
from observador.sources.column_mapping import resolve_columns

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


def _filtrer_ressources_actives(resources: list[dict]) -> list[dict]:
    """Exclut les ressources "inactive" d'une liste déjà filtrée par
    name_contains="active" — DÉCOUVERTE (2026-08-31) : "inactive" contient la
    sous-chaîne "active", donc un simple name_contains="active" attrape aussi
    "Other inactive corporations"/"Inactive business corporations", d'où des
    lignes "Dissoute" dans les résultats sans cette exclusion explicite."""
    return [r for r in resources if "inactive" not in (r.get("name") or "").lower()]


def ingest_snapshot(db_session: Session, limit: int | None = None) -> IngestStats:
    """Télécharge les ressources "corporations actives" (une par langue/type) et
    met à jour le miroir local, en détectant les nouvelles corporations actives
    (signal) par comparaison à l'état précédemment connu."""
    client = CKANClient(OPEN_CANADA_BASE)
    resources = _filtrer_ressources_actives(
        client.resources(CORPORATIONS_PACKAGE_ID, format_filter="CSV", name_contains="active")
    )
    if not resources:
        raise RuntimeError(
            f"Aucune ressource CSV 'active' trouvée pour {CORPORATIONS_PACKAGE_ID!r} — "
            "le jeu de données a peut-être changé de structure."
        )

    stats = IngestStats()
    columns: dict[str, str] | None = None
    colonnes_optionnelles: dict[str, str] = {}

    for resource in resources:
        path = client.download(resource)
        with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
            reader = csv.DictReader(f)
            if columns is None:
                fieldnames = reader.fieldnames or []
                columns = resolve_columns(fieldnames, COLUMN_ALIASES)
                for logical, aliases in COLUMN_ALIASES_OPTIONNELS.items():
                    try:
                        colonnes_optionnelles.update(resolve_columns(fieldnames, {logical: aliases}))
                    except ValueError:
                        pass  # champ optionnel absent — pas bloquant

            for row in reader:
                if limit is not None and stats.lignes_lues >= limit:
                    break
                stats.lignes_lues += 1
                _upsert_row(db_session, row, columns, colonnes_optionnelles, stats)

        if limit is not None and stats.lignes_lues >= limit:
            break

    db_session.commit()
    return stats


def _upsert_row(
    db_session: Session, row: dict, columns: dict[str, str], colonnes_optionnelles: dict[str, str], stats: IngestStats
) -> None:
    numero = (row.get(columns["numero"]) or "").strip()
    if not numero:
        return
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

    date_inc = None  # pas de colonne fiable pour la date de constitution — voir COLUMN_ALIASES
    loi = None
    if "loi" in colonnes_optionnelles:
        loi = (row.get(colonnes_optionnelles["loi"]) or "").strip() or None

    existing = db_session.get(CorporationFederaleEntry, numero)
    if existing is None:
        entry = CorporationFederaleEntry(
            numero_corporation=numero,
            nom=nom,
            nom_normalise=_normaliser(nom),
            statut=statut_brut,
            adresse=adresse,
            province=province,
            loi_constitutive=loi,
            date_incorporation=date_inc,
        )
        db_session.add(entry)
        # Comptage/audit seulement (ex. logging) — PAS un signal : une toute
        # nouvelle incorporation n'est pas une entreprise en croissance (voir
        # correction de calibration dans la docstring du module).
        if statut_brut.lower() in STATUTS_ACTIFS:
            stats.nouvelles_corporations_actives.append({"numero": numero, "nom": nom, "adresse": adresse})
        return

    changement_adresse = (
        adresse is not None
        and adresse != existing.adresse
        and existing.adresse is not None
        and statut_brut.lower() in STATUTS_ACTIFS
    )
    if changement_adresse:
        stats.changements_adresse.append(
            {"numero": numero, "nom": nom, "ancienne_adresse": existing.adresse, "nouvelle_adresse": adresse}
        )

    existing.nom = nom
    existing.nom_normalise = _normaliser(nom)
    existing.statut = statut_brut
    existing.adresse = adresse
    existing.province = province
    existing.loi_constitutive = loi
    existing.date_incorporation = date_inc


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
    docstring de observador/models/corp_federale_entry.py pour ce que c'est
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
