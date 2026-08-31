"""Connecteur Subventions et contributions gouvernementales — divulgation
proactive fédérale (spec section 7, Signal 2). Couvre tous les ministères
fédéraux (absorbe DEC, PARI-CNRC, CanExport, FedDev Ontario, FedNor, APECA,
PrairiesCan, PacifiCan comme des filtres sur cette même source, pas des sources
séparées).

ACCÈS RÉEL CONFIRMÉ le 2026-08-31 : jeu de données CKAN
432527ab-7aac-45b5-81d6-7597107a7013 sur open.canada.ca, ressource "Proactive
Disclosure - Grants and Contributions". Le fichier CSV brut pèse ~2,3 Go (tout
l'historique fédéral depuis ~2017) — ingérable en entier dans une session.
`datastore_active=True` sur cette ressource : on interroge donc l'API Datastore
CKAN (`datastore_search`, triée par date décroissante, avec pagination) plutôt
que de télécharger le fichier — toujours des "données ouvertes gratuites" au
sens de la spec, juste un accès ciblé plutôt qu'un fichier brut complet.
"""
from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import datetime, timezone

from dateutil import parser as dateutil_parser

from observador.sources.base import RawSignal, SourceConnector
from observador.sources.ckan_client import OPEN_CANADA_BASE, CKANClient

logger = logging.getLogger(__name__)

SUBVENTIONS_PACKAGE_ID = "432527ab-7aac-45b5-81d6-7597107a7013"
_RESOURCE_NAME = "Proactive Disclosure - Grants and Contributions"


def _parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = dateutil_parser.parse(raw)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError):
        return None


def _parse_float(raw) -> float | None:
    if raw is None or raw == "":
        return None
    try:
        return float(str(raw).replace(",", "").strip())
    except ValueError:
        return None


def _find_resource_id(client: CKANClient) -> str:
    resources = client.resources(SUBVENTIONS_PACKAGE_ID, format_filter="CSV")
    for r in resources:
        if r.get("name") == _RESOURCE_NAME and r.get("datastore_active"):
            return r["id"]
    raise RuntimeError(
        f"Ressource {_RESOURCE_NAME!r} introuvable ou pas indexée dans le Datastore "
        f"(package {SUBVENTIONS_PACKAGE_ID!r}) — le jeu de données a peut-être changé."
    )


class SubventionsFederalesConnector(SourceConnector):
    """`region` sur cette source est "Canada" (spec) ; `province` restreint la
    requête pour la Phase 1 (foyer Québec) sans que ce soit une limite de
    l'architecture — passer province=None couvre tout le Canada."""

    def __init__(self, source_def, limit: int | None = 500, province: str | None = "QC"):
        super().__init__(source_def)
        self.limit = limit
        self.province = province

    def detect(self, since: datetime | None, db_session) -> Iterator[RawSignal]:
        client = CKANClient(OPEN_CANADA_BASE)
        try:
            resource_id = _find_resource_id(client)
        except RuntimeError as exc:
            logger.warning("Subventions fédérales: %s", exc)
            return

        filters = {"recipient_province": self.province} if self.province else None
        page_size = min(500, self.limit) if self.limit else 500
        offset = 0
        n = 0

        while True:
            result = client.datastore_search(
                resource_id,
                filters=filters,
                sort="agreement_start_date desc",
                limit=page_size,
                offset=offset,
            )
            records = result.get("records", [])
            if not records:
                break

            for rec in records:
                if self.limit is not None and n >= self.limit:
                    return
                n += 1

                nom = (rec.get("recipient_legal_name") or "").strip()
                if not nom:
                    continue

                date_signature = _parse_date(rec.get("agreement_start_date"))
                if since and date_signature and date_signature < since:
                    return  # trié par date décroissante : tout le reste est plus vieux

                montant = _parse_float(rec.get("agreement_value"))
                titre = rec.get("agreement_title_fr") or rec.get("agreement_title_en")
                programme = rec.get("prog_name_fr") or rec.get("prog_name_en")

                yield RawSignal(
                    signal_type_id="financement_expansion",
                    nom_entreprise=nom,
                    detected_at=date_signature or datetime.now(timezone.utc),
                    source_ref=f"subventions_federales:{rec.get('ref_number')}:{rec.get('amendment_number')}",
                    ville=rec.get("recipient_city"),
                    region=rec.get("recipient_province"),
                    valeur_associee=montant,
                    titre_ou_description=titre or programme,
                    champs={
                        "nature_bien": programme,  # réutilisé par le scoring (nature du programme)
                        "programme": programme,
                        "ministere": rec.get("owner_org_title"),
                        "description": rec.get("description_fr") or rec.get("description_en"),
                        "type_entente": rec.get("agreement_type"),  # G=subvention, C=contribution, O=autre
                        "date_signature": rec.get("agreement_start_date"),
                    },
                )

            offset += page_size
            if len(records) < page_size:
                break


CONNECTOR_CLASS = SubventionsFederalesConnector
