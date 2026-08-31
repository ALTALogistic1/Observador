"""Connecteur REQ (Registre des entreprises du Québec) — spec section 7, Signal 4,
et section 9 ("Le NEQ comme identifiant pivot").

Double rôle, comme documenté dans registry/sources.yaml :
  1. Base de résolution/vérification pour TOUTES les sources : résoudre un nom
     d'entreprise en NEQ, obtenir adresse/secteur/statut légal (resolve_neq_by_name,
     get_by_neq — appelées par observador/resolution.py et observador/verification.py).
  2. Source de signal en soi : nouvel établissement secondaire ou changement
     d'adresse du siège social, détecté en comparant deux rafraîchissements
     successifs du miroir local (REQEntry). Les mises à jour purement
     administratives (aucun changement d'adresse/statut) sont exclues.

IMPORTANT — schéma CSV non encore confirmé : le format exact des colonnes du fichier
REQ n'a pas pu être inspecté (accès réseau bloqué au moment de l'écriture — voir
docs/STATUT_RESEAU.md). COLUMN_ALIASES ci-dessous liste les noms de colonnes les plus
probables d'après la documentation publique du jeu de données; resolve_columns()
échoue avec un message explicite (colonnes attendues vs colonnes réellement présentes)
si aucun alias ne correspond, plutôt que de mal interpréter silencieusement les
données. Premier réflexe après déblocage réseau : lancer l'ingestion sur un seul
fichier et ajuster ces alias si l'erreur le demande.
"""
from __future__ import annotations

import csv
import io
import logging
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone

from dateutil import parser as dateutil_parser
from rapidfuzz import fuzz, process
from sqlalchemy import select
from sqlalchemy.orm import Session

from observador.models.req_entry import REQEntry
from observador.sources.base import RawSignal, SourceConnector
from observador.sources.ckan_client import DONNEES_QUEBEC_BASE, CKANClient
from observador.sources.column_mapping import normaliser as _normaliser
from observador.sources.column_mapping import resolve_columns

logger = logging.getLogger(__name__)

REQ_PACKAGE_ID = "registre-des-entreprises"

# Chaque valeur est une liste de motifs (sous-chaîne, insensible à la casse/accents)
# essayés dans l'ordre contre les en-têtes réelles du CSV.
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


def _parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = dateutil_parser.parse(raw)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError):
        return None


def _iter_csv_rows(path) -> Iterator[dict[str, str]]:
    """Lit un CSV (ou un .zip contenant un ou plusieurs CSV) en flux, sans tout
    charger en mémoire — les fichiers REQ complets peuvent être volumineux."""
    if str(path).lower().endswith(".zip"):
        with zipfile.ZipFile(path) as zf:
            for name in zf.namelist():
                if not name.lower().endswith(".csv"):
                    continue
                with zf.open(name) as raw:
                    text = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace")
                    yield from csv.DictReader(text)
    else:
        with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
            yield from csv.DictReader(f)


@dataclass
class IngestStats:
    lignes_lues: int = 0
    entrees_nouvelles: int = 0
    entrees_mises_a_jour: int = 0
    changements_adresse: list[dict] | None = None
    nouveaux_etablissements: list[dict] | None = None

    def __post_init__(self):
        self.changements_adresse = self.changements_adresse or []
        self.nouveaux_etablissements = self.nouveaux_etablissements or []


def ingest_snapshot(db_session: Session, limit: int | None = None) -> IngestStats:
    """Télécharge LE fichier REQ en vrac (une seule requête HTTP vers la ressource
    CKAN, mise à jour deux fois par mois — spec section 7) et met à jour le miroir
    local (REQEntry) à partir de son contenu, en détectant au passage les
    changements pertinents (nouvel établissement, changement d'adresse) par
    comparaison à l'état précédemment connu. Toute résolution nom->NEQ ou NEQ->fiche
    pour les AUTRES sources (resolve_neq_by_name, get_by_neq) n'interroge QUE ce
    miroir local — jamais une requête réseau par entreprise (spec section 7 : le
    fichier en vrac est la méthode principale, pas des requêtes individuelles sur
    le site de consultation). `limit` borne le nombre de lignes traitées — utile
    pour un premier test raisonnable plutôt que le registre complet (accepté comme
    limite de volume, pas comme donnée fictive : chaque ligne traitée reste une
    vraie ligne du REQ)."""
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
        path = client.download(resource)
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
# API de résolution publique — utilisée par observador/resolution.py et
# observador/verification.py, indépendamment du rôle "source de signal".
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
    candidates = (
        db_session.execute(
            select(REQEntry).where(REQEntry.nom_normalise.like(f"{prefix}%")).limit(2000)
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


class REQConnector(SourceConnector):
    """Utilisé par le moteur comme n'importe quel autre connecteur pour le signal
    `registre_corporatif`. L'ingestion (téléchargement + diff) se fait ici; la
    résolution NEQ pour les AUTRES sources passe par resolve_neq_by_name/get_by_neq
    ci-dessus, appelées directement par observador/resolution.py (pas via detect())."""

    def detect(self, since, db_session: Session) -> Iterator[RawSignal]:
        stats = ingest_snapshot(db_session, limit=None)
        logger.info(
            "REQ: %s lignes lues, %s nouvelles, %s mises à jour, %s changements d'adresse retenus",
            stats.lignes_lues,
            stats.entrees_nouvelles,
            stats.entrees_mises_a_jour,
            len(stats.changements_adresse),
        )

        now = datetime.now(timezone.utc)

        for nouveau in stats.nouveaux_etablissements:
            yield RawSignal(
                signal_type_id="registre_corporatif",
                nom_entreprise=nouveau["nom"],
                detected_at=now,
                source_ref=f"req:nouvel_etablissement:{nouveau['neq']}",
                neq=nouveau["neq"],
                adresse=nouveau["adresse"],
                titre_ou_description="Nouvelle immatriculation au REQ",
                champs={"type_changement": "nouvel_etablissement", **nouveau},
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


CONNECTOR_CLASS = REQConnector
