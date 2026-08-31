"""Connecteur Divulgation proactive des contrats fédéraux (spec section 7,
Signal 5) — équivalent pancanadien du SEAO, contrats de plus de 10 000$ accordés
par les ministères fédéraux.

ACCÈS RÉEL CONFIRMÉ le 2026-08-31 : jeu de données CKAN
d8f85d91-7dec-4fd1-8055-483b77225d8b sur open.canada.ca, ressource "Contracts
over $10,000". Fichier CSV brut ~640 Mo (tout l'historique fédéral) —
`datastore_active=True`, donc interrogé via l'API Datastore CKAN comme pour les
subventions fédérales (observador/sources/subventions_federales.py), pas
téléchargé en entier.
"""
from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import datetime, timezone

from dateutil import parser as dateutil_parser

from observador.sources.base import RawSignal, SourceConnector
from observador.sources.ckan_client import OPEN_CANADA_BASE, CKANClient

logger = logging.getLogger(__name__)

CONTRATS_PACKAGE_ID = "d8f85d91-7dec-4fd1-8055-483b77225d8b"
_RESOURCE_NAME = "Contracts over $10,000"


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
    resources = client.resources(CONTRATS_PACKAGE_ID, format_filter="CSV")
    for r in resources:
        if r.get("name") == _RESOURCE_NAME and r.get("datastore_active"):
            return r["id"]
    raise RuntimeError(
        f"Ressource {_RESOURCE_NAME!r} introuvable ou pas indexée dans le Datastore "
        f"(package {CONTRATS_PACKAGE_ID!r}) — le jeu de données a peut-être changé."
    )


class ContratsFederauxConnector(SourceConnector):
    def __init__(self, source_def, limit: int | None = 500):
        super().__init__(source_def)
        self.limit = limit

    def detect(self, since: datetime | None, db_session) -> Iterator[RawSignal]:
        client = CKANClient(OPEN_CANADA_BASE)
        try:
            resource_id = _find_resource_id(client)
        except RuntimeError as exc:
            logger.warning("Contrats fédéraux: %s", exc)
            return

        page_size = min(500, self.limit) if self.limit else 500
        offset = 0
        n = 0

        while True:
            result = client.datastore_search(
                resource_id,
                sort="contract_date desc",
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

                nom = (rec.get("vendor_name") or "").strip()
                if not nom:
                    continue

                date_contrat = _parse_date(rec.get("contract_date"))
                if since and date_contrat and date_contrat < since:
                    return  # trié par date décroissante : tout le reste est plus vieux

                # Valeur finale = valeur d'origine + modifications (si connues),
                # sinon la valeur de contrat rapportée directement.
                valeur = _parse_float(rec.get("contract_value")) or _parse_float(
                    rec.get("original_value")
                )

                yield RawSignal(
                    signal_type_id="appel_offres",
                    nom_entreprise=nom,
                    detected_at=date_contrat or datetime.now(timezone.utc),
                    source_ref=f"contrats_federaux:{rec.get('reference_number')}",
                    valeur_associee=valeur,
                    titre_ou_description=rec.get("description_fr") or rec.get("description_en"),
                    champs={
                        "donneur_ordre": rec.get("buyer_name") or rec.get("owner_org_title"),
                        "ministere": rec.get("owner_org_title"),
                        "valeur_contrat": valeur,
                        "valeur_originale": _parse_float(rec.get("original_value")),
                        "date_attribution": rec.get("contract_date"),
                        "code_bien_service": rec.get("commodity_code"),
                    },
                )

            offset += page_size
            if len(records) < page_size:
                break


CONNECTOR_CLASS = ContratsFederauxConnector
