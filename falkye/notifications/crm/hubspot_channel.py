"""Client CRM HubSpot — intégration CRM (Radar et Radar+, ajoutée le
2026-09-02). Authentification par jeton d'application privée (Private App
token, `CrmConnection.jeton_api`) — API CRM v3, objet Companies.

Comme tout le reste de ce dossier (voir TheirStack/Stripe/géocodage), aucun
accès réseau vers la vraie API HubSpot dans cet environnement — construit et
testé contre des mocks HTTP réalistes (tests/test_hubspot_channel.py, via
`responses`), validation en conditions réelles à faire par Alexandre une fois
qu'un jeton HubSpot réel est disponible."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import requests

from falkye.notifications.crm.base import (
    CrmProvider,
    CrmPushResult,
    CrmStatutDistant,
    mappage_effectif,
    proprietes_pour_mappage,
    valeurs_a_pousser,
)

if TYPE_CHECKING:
    from falkye.models.crm_connection import CrmConnection
    from falkye.notifications.base import NotificationContent

logger = logging.getLogger(__name__)

BASE_URL = "https://api.hubapi.com"


class HubspotProvider(CrmProvider):
    def _headers(self, connection: "CrmConnection") -> dict[str, str]:
        return {"Authorization": f"Bearer {connection.jeton_api}", "Content-Type": "application/json"}

    def pousser(
        self, connection: "CrmConnection", contenu: "NotificationContent", crm_object_id: str | None
    ) -> CrmPushResult:
        mappage = mappage_effectif(self.provider_def, connection)
        proprietes = proprietes_pour_mappage(valeurs_a_pousser(contenu, connection), mappage)
        payload = {"properties": proprietes}
        try:
            if crm_object_id is None:
                resp = requests.post(
                    f"{BASE_URL}/crm/v3/objects/companies",
                    json=payload, headers=self._headers(connection), timeout=15,
                )
            else:
                resp = requests.patch(
                    f"{BASE_URL}/crm/v3/objects/companies/{crm_object_id}",
                    json=payload, headers=self._headers(connection), timeout=15,
                )
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Échec push HubSpot (company %s): %s", crm_object_id, exc)
            return CrmPushResult(succes=False, erreur=str(exc))

        data = resp.json()
        nouvel_id = str(data.get("id")) if data.get("id") is not None else crm_object_id
        return CrmPushResult(succes=True, crm_object_id=nouvel_id)

    def tirer_statut(self, connection: "CrmConnection", crm_object_id: str) -> CrmStatutDistant:
        mappage = mappage_effectif(self.provider_def, connection)
        propriete_statut = mappage.get("statut_suivi")
        if not propriete_statut:
            return CrmStatutDistant(succes=True, stage_brut=None)
        try:
            resp = requests.get(
                f"{BASE_URL}/crm/v3/objects/companies/{crm_object_id}",
                params={"properties": propriete_statut},
                headers=self._headers(connection), timeout=15,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Échec sondage HubSpot (company %s): %s", crm_object_id, exc)
            return CrmStatutDistant(succes=False, erreur=str(exc))

        proprietes = resp.json().get("properties") or {}
        return CrmStatutDistant(succes=True, stage_brut=proprietes.get(propriete_statut))


PROVIDER_CLASS = HubspotProvider
