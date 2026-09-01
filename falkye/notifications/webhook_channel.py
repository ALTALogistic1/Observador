"""Canal webhook générique (Slack/Discord/autre) — statut `a_developper`, gardé au
registre pour démontrer l'extensibilité (non demandé pour l'instant, voir
registry/notification_channels.yaml)."""
from __future__ import annotations

from falkye.notifications.base import StubChannel

CHANNEL_CLASS = StubChannel
