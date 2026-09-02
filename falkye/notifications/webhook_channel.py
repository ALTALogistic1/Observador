"""Canal webhook générique — spec section 4bis, fonctionnalité Radar+ "accès
API/webhook complet" : "pousser chaque nouveau signal (filtré par seuils de
confiance/pertinence du profil) vers un système externe de l'institution plutôt
que d'exiger la consultation d'un dashboard — transforme FALKYE d'un outil
consulté en infrastructure intégrée aux systèmes internes du client."

Réservé au plan RADAR_PLUS (`resoudre_destinataire` ci-dessous) — Radar et Écho
n'ont pas cette couche. L'URL est PROPRE à chaque profil (`Profile.webhook_url`),
pas une configuration globale par variable d'environnement comme le laissait
supposer l'ancienne entrée `webhook_generique` du registre (statut `a_developper`
depuis le scaffold initial, jamais implémenté avant cette fonctionnalité)."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import requests

from falkye.notifications.base import DeliveryResult, NotificationChannel, NotificationContent

if TYPE_CHECKING:
    from falkye.models.profile import Profile

logger = logging.getLogger(__name__)


class WebhookChannel(NotificationChannel):
    def resoudre_destinataire(self, profile: "Profile") -> str | None:
        from falkye.models.profile import PlanTarifaire

        if profile.plan != PlanTarifaire.RADAR_PLUS:
            return None  # spec section 4bis : réservé Radar+
        return profile.webhook_url or None

    def envoyer(self, destinataire: str, contenu: NotificationContent) -> DeliveryResult:
        # Toujours un payload structuré si disponible (spec : "un système externe...
        # pas un dashboard") — repli sur sujet/corps_texte seulement si le contenu
        # n'a jamais été construit avec de quoi le peupler (ne devrait pas arriver
        # en usage normal, voir falkye/notifications/formatter.py).
        payload = contenu.donnees_structurees or {"sujet": contenu.sujet, "corps_texte": contenu.corps_texte}
        try:
            resp = requests.post(destinataire, json=payload, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Échec d'envoi webhook vers %s: %s", destinataire, exc)
            return DeliveryResult(succes=False, erreur=str(exc))
        return DeliveryResult(succes=True)


CHANNEL_CLASS = WebhookChannel
