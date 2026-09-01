"""Canal SMS — statut `a_developper` (Phase 2, registry/notification_channels.yaml,
priorité 2). Fournisseur pressenti : Twilio. Compte/identifiants à régler par
Alexandre avant activation (TWILIO_ACCOUNT_SID/TWILIO_AUTH_TOKEN/TWILIO_SMS_FROM_NUMBER,
voir .env.example)."""
from __future__ import annotations

from falkye.notifications.base import StubChannel

CHANNEL_CLASS = StubChannel
