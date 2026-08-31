"""Canal WhatsApp — statut `a_developper` (Phase 2, registry/notification_channels.yaml,
priorité 3). Fournisseur pressenti : WhatsApp Business Cloud API (ou Twilio). Compte à
régler par Alexandre avant activation (WHATSAPP_PROVIDER_TOKEN/WHATSAPP_PHONE_ID, voir
.env.example)."""
from __future__ import annotations

from observador.notifications.base import StubChannel

CHANNEL_CLASS = StubChannel
