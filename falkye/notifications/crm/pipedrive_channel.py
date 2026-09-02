"""Client CRM Pipedrive — intégration CRM (Radar et Radar+, ajoutée le
2026-09-02). Authentification par jeton API personnel (`CrmConnection.
jeton_api`), passé en paramètre de requête `api_token` (mécanique Pipedrive
v1, pas un en-tête comme HubSpot) — API v1, objet Organizations.

LIMITE RÉELLE documentée dans registry/crm_providers.yaml : les clés de champ
personnalisé Pipedrive sont des hachages opaques propres au compte de chaque
client — `champs_mappage` du registre n'est qu'un défaut illustratif, chaque
connexion réelle doit fournir ses vraies clés via
`CrmConnection.champs_mappage_override`.

Comme tout le reste de ce dossier (voir TheirStack/Stripe/géocodage), aucun
accès réseau vers la vraie API Pipedrive dans cet environnement — construit et
testé contre des mocks HTTP réalistes (tests/test_pipedrive_channel.py, via
`responses`), validation en conditions réelles à faire par Alexandre une fois
qu'un jeton Pipedrive réel est disponible."""
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

BASE_URL = "https://api.pipedrive.com/v1"


class PipedriveProvider(CrmProvider):
    def pousser(
        self, connection: "CrmConnection", contenu: "NotificationContent", crm_object_id: str | None
    ) -> CrmPushResult:
        mappage = mappage_effectif(self.provider_def, connection)
        proprietes = proprietes_pour_mappage(valeurs_a_pousser(contenu, connection), mappage)
        params = {"api_token": connection.jeton_api}
        try:
            if crm_object_id is None:
                resp = requests.post(f"{BASE_URL}/organizations", params=params, json=proprietes, timeout=15)
            else:
                resp = requests.put(
                    f"{BASE_URL}/organizations/{crm_object_id}", params=params, json=proprietes, timeout=15
                )
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Échec push Pipedrive (organization %s): %s", crm_object_id, exc)
            return CrmPushResult(succes=False, erreur=str(exc))

        data = (resp.json() or {}).get("data") or {}
        nouvel_id = str(data.get("id")) if data.get("id") is not None else crm_object_id
        return CrmPushResult(succes=True, crm_object_id=nouvel_id)

    def tirer_statut(self, connection: "CrmConnection", crm_object_id: str) -> CrmStatutDistant:
        mappage = mappage_effectif(self.provider_def, connection)
        champ_statut = mappage.get("statut_suivi")
        if not champ_statut:
            return CrmStatutDistant(succes=True, stage_brut=None)
        params = {"api_token": connection.jeton_api}
        try:
            resp = requests.get(f"{BASE_URL}/organizations/{crm_object_id}", params=params, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Échec sondage Pipedrive (organization %s): %s", crm_object_id, exc)
            return CrmStatutDistant(succes=False, erreur=str(exc))

        data = (resp.json() or {}).get("data") or {}
        return CrmStatutDistant(succes=True, stage_brut=data.get(champ_statut))


PROVIDER_CLASS = PipedriveProvider
