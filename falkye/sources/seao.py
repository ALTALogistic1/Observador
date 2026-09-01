"""Connecteur SEAO (Système électronique d'appel d'offres du Québec) — spec section
7, Signal 5.

Données ouvertes CKAN (donneesquebec.ca), fichiers JSON hebdomadaires/mensuels
(hebdo_YYYYMMDD_YYYYMMDD.json / mensuel_YYYYMMDD_YYYYMMDD.json) au format inspiré de
l'Open Contracting Data Standard (OCDS) depuis mars 2021 — releases contenant des
"awards" (contrats attribués), chacun avec un ou plusieurs fournisseurs (adjudicataires).

IMPORTANT — schéma JSON non encore confirmé en pratique (accès réseau bloqué au
moment de l'écriture, voir docs/STATUT_RESEAU.md) : le parsing ci-dessous suit la
structure OCDS standard documentée publiquement (release.awards[].suppliers,
release.awards[].value, release.buyer / release.parties[role=buyer]). Si le fichier
réel diverge, `_extraire_awards` lève une erreur explicite plutôt que de produire des
signaux silencieusement incorrects — premier réflexe après déblocage réseau : lancer
sur un seul fichier récent et ajuster ici si besoin.
"""
from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterator
from datetime import datetime, timezone

from dateutil import parser as dateutil_parser

from falkye.sources.base import RawSignal, SourceConnector
from falkye.sources.ckan_client import DONNEES_QUEBEC_BASE, CKANClient

logger = logging.getLogger(__name__)

SEAO_PACKAGE_ID = "systeme-electronique-dappel-doffres-seao"

_FILENAME_DATE_RANGE = re.compile(r"(\d{8})_(\d{8})")


def _parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = dateutil_parser.parse(raw)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError):
        return None


def _resource_covers(resource: dict, since: datetime | None) -> bool:
    if since is None:
        return True
    match = _FILENAME_DATE_RANGE.search(resource.get("name", "") or resource.get("url", ""))
    if not match:
        return True  # nom non daté : on ne peut pas filtrer, on l'inclut par prudence
    _start, end = match.groups()
    end_dt = datetime.strptime(end, "%Y%m%d").replace(tzinfo=timezone.utc)
    return end_dt >= since


def _buyer_name(release: dict) -> str | None:
    buyer = release.get("buyer") or {}
    if buyer.get("name"):
        return buyer["name"]
    for party in release.get("parties", []):
        if "buyer" in (party.get("roles") or []):
            return party.get("name")
    return None


def _extraire_awards(data) -> Iterator[tuple[dict, dict]]:
    """Retourne des paires (release, award) pour chaque contrat attribué trouvé."""
    if isinstance(data, dict) and "releases" in data:
        releases = data["releases"]
    elif isinstance(data, list):
        releases = data
    else:
        raise ValueError(
            "Structure JSON SEAO inattendue (ni {'releases': [...]}, ni liste de "
            f"releases). Clés de premier niveau reçues: "
            f"{list(data.keys()) if isinstance(data, dict) else type(data)}"
        )

    for release in releases:
        for award in release.get("awards", []) or []:
            yield release, award


class SEAOConnector(SourceConnector):
    def detect(self, since: datetime | None, db_session) -> Iterator[RawSignal]:
        client = CKANClient(DONNEES_QUEBEC_BASE)
        resources = client.resources(SEAO_PACKAGE_ID, format_filter="JSON")
        if not resources:
            logger.warning("SEAO: aucune ressource JSON trouvée sur CKAN")
            return

        cibles = [r for r in resources if _resource_covers(r, since)]
        if not cibles:
            cibles = resources[:1]  # au minimum le plus récent

        for resource in cibles:
            path = client.download(resource)
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            for release, award in _extraire_awards(data):
                for supplier in award.get("suppliers", []) or []:
                    nom = (supplier.get("name") or "").strip()
                    if not nom:
                        continue

                    date_attribution = _parse_date(award.get("date")) or _parse_date(
                        release.get("date")
                    )
                    if since and date_attribution and date_attribution < since:
                        continue

                    value = award.get("value") or {}
                    montant = value.get("amount")

                    yield RawSignal(
                        signal_type_id="appel_offres",
                        nom_entreprise=nom,
                        detected_at=date_attribution or datetime.now(timezone.utc),
                        source_ref=f"seao:{release.get('ocid', release.get('id', ''))}:{award.get('id', '')}",
                        valeur_associee=float(montant) if montant is not None else None,
                        titre_ou_description=(release.get("tender") or {}).get("title"),
                        champs={
                            "donneur_ordre": _buyer_name(release),
                            "valeur_contrat": montant,
                            "devise": value.get("currency"),
                            "date_attribution": award.get("date"),
                            "statut_attribution": award.get("status"),
                            "description_tender": (release.get("tender") or {}).get("description"),
                        },
                    )


CONNECTOR_CLASS = SEAOConnector
