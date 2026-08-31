"""Connecteur Guichet-Emplois (Job Bank Canada) — spec section 7, Signal 3.

Données ouvertes CKAN (open.canada.ca), jeu de données
"ea639e28-c0fc-48bf-b5dd-b8899bd43072" ("Job Postings Advertised on Canada's
National Job Bank Website"), fichiers CSV mensuels.

Produit UN signal `recrutement_massif` par offre d'emploi individuelle (avec son
titre intégral — indispensable à l'analyse qualitative des mots-clés, spec section
7 : "un titre de poste orienté transformation/implantation... signal fort même avec
un seul poste"). Le regroupement volumétrique (plusieurs postes chez le même
employeur) et la correspondance qualitative aux mots-clés du profil se font en aval,
dans observador/matching.py et observador/scoring.py — le connecteur reste un simple
extracteur.

IMPORTANT — schéma CSV non encore confirmé en pratique (accès réseau bloqué au
moment de l'écriture, voir docs/STATUT_RESEAU.md). Mêmes garde-fous que pour REQ :
COLUMN_ALIASES + resolve_columns() échouent explicitement plutôt que de deviner.
"""
from __future__ import annotations

import csv
import logging
from collections.abc import Iterator
from datetime import datetime, timezone

from dateutil import parser as dateutil_parser

from observador.sources.base import RawSignal, SourceConnector
from observador.sources.ckan_client import OPEN_CANADA_BASE, CKANClient
from observador.sources.column_mapping import resolve_columns

logger = logging.getLogger(__name__)

GUICHET_EMPLOIS_PACKAGE_ID = "ea639e28-c0fc-48bf-b5dd-b8899bd43072"

COLUMN_ALIASES: dict[str, list[str]] = {
    "employeur": ["employer", "business_name", "employeur", "nom_employeur"],
    "titre_poste": ["job_title", "title", "titre_poste", "titre"],
    "cnp": ["noc_code", "noc", "cnp"],
    "nombre_postes": ["vacancies", "number_of_positions", "nb_postes", "nombre_postes"],
    "salaire": ["salary", "wage", "salaire"],
    "ville": ["city", "ville"],
    "province": ["province", "region"],
    "date_publication": ["date_posted", "posting_date", "date_publication", "date"],
    "url_offre": ["url", "job_url", "lien"],
}


def _parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = dateutil_parser.parse(raw)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError):
        return None


def _parse_int(raw: str | None) -> int | None:
    if not raw:
        return None
    try:
        return int(float(str(raw).replace(",", "").strip()))
    except ValueError:
        return None


class GuichetEmploisConnector(SourceConnector):
    def __init__(self, source_def, limit: int | None = None):
        super().__init__(source_def)
        # Limite raisonnable de lignes traitées par exécution — évite de charger un
        # fichier national complet à chaque scan. Chaque ligne reste une vraie offre
        # réelle du Guichet-Emplois, ce n'est pas une donnée simulée.
        self.limit = limit

    def detect(self, since: datetime | None, db_session) -> Iterator[RawSignal]:
        client = CKANClient(OPEN_CANADA_BASE)
        resources = client.resources(GUICHET_EMPLOIS_PACKAGE_ID, format_filter="CSV")
        if not resources:
            logger.warning("Guichet-Emplois: aucune ressource CSV trouvée sur CKAN")
            return

        # Le fichier le plus récent suffit pour une veille continue (mise à jour
        # mensuelle) ; une recherche ponctuelle plus large peut en parcourir plusieurs.
        cibles = resources[:1] if since is None else resources[:3]

        columns: dict[str, str] | None = None
        lignes_lues = 0

        for resource in cibles:
            path = client.download(resource)
            with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
                reader = csv.DictReader(f)
                if columns is None:
                    columns = resolve_columns(reader.fieldnames or [], COLUMN_ALIASES)

                for row in reader:
                    if self.limit is not None and lignes_lues >= self.limit:
                        break
                    lignes_lues += 1

                    employeur = (row.get(columns["employeur"]) or "").strip()
                    titre = (row.get(columns["titre_poste"]) or "").strip()
                    if not employeur or not titre:
                        continue

                    date_pub = _parse_date(row.get(columns["date_publication"]))
                    if since and date_pub and date_pub < since:
                        continue

                    yield RawSignal(
                        signal_type_id="recrutement_massif",
                        nom_entreprise=employeur,
                        detected_at=date_pub or datetime.now(timezone.utc),
                        source_ref=f"guichet_emplois:{resource['id']}:{row.get(columns['url_offre'], '')}"
                        or f"guichet_emplois:{resource['id']}:{employeur}:{titre}",
                        ville=(row.get(columns["ville"]) or "").strip() or None,
                        region=(row.get(columns["province"]) or "").strip() or None,
                        titre_ou_description=titre,
                        valeur_associee=_parse_int(row.get(columns["nombre_postes"])),
                        champs={
                            "titre_poste": titre,
                            "cnp": row.get(columns["cnp"]),
                            "nombre_postes": _parse_int(row.get(columns["nombre_postes"])),
                            "salaire_offert": row.get(columns["salaire"]),
                            "date_publication": row.get(columns["date_publication"]),
                        },
                    )

            if self.limit is not None and lignes_lues >= self.limit:
                break


CONNECTOR_CLASS = GuichetEmploisConnector
