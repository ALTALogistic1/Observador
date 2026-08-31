"""Interface générique des canaux de notification (voir
registry/notification_channels.yaml). Même principe que les sources : le moteur
(observador/engine.py) ne connaît que cette interface, jamais un canal précis."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from observador.registry.loader import NotificationChannelDef


@dataclass
class NotificationContent:
    sujet: str
    corps_texte: str
    corps_html: str | None = None


@dataclass
class DeliveryResult:
    succes: bool
    erreur: str | None = None


class NotificationChannel(ABC):
    def __init__(self, channel_def: "NotificationChannelDef"):
        self.channel_def = channel_def

    @abstractmethod
    def envoyer(self, destinataire: str, contenu: NotificationContent) -> DeliveryResult:
        raise NotImplementedError


class StubChannel(NotificationChannel):
    """Canal au statut `a_developper` : n'envoie jamais réellement, échoue de façon
    explicite plutôt que de simuler un envoi réussi."""

    def envoyer(self, destinataire: str, contenu: NotificationContent) -> DeliveryResult:
        return DeliveryResult(
            succes=False,
            erreur=(
                f"Canal '{self.channel_def.id}' au statut 'a_developper' — pas encore "
                f"implémenté (voir registry/notification_channels.yaml)."
            ),
        )
