"""Canal courriel (SMTP) — statut `actif` en Phase 1 (registry/notification_channels.yaml,
priorité 1, décision produit 2026-08-31 : "le plus simple à mettre en place")."""
from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from falkye.notifications.base import DeliveryResult, NotificationChannel, NotificationContent

logger = logging.getLogger(__name__)


class EmailChannel(NotificationChannel):
    def envoyer(self, destinataire: str, contenu: NotificationContent) -> DeliveryResult:
        host = os.environ.get("SMTP_HOST")
        port = int(os.environ.get("SMTP_PORT", "587"))
        username = os.environ.get("SMTP_USERNAME")
        password = os.environ.get("SMTP_PASSWORD")
        from_addr = os.environ.get("SMTP_FROM_ADDR")
        use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() != "false"

        if not host or not from_addr:
            return DeliveryResult(
                succes=False,
                erreur=(
                    "Configuration SMTP incomplète (SMTP_HOST/SMTP_FROM_ADDR manquants) — "
                    "voir .env.example."
                ),
            )

        msg = MIMEMultipart("alternative")
        msg["Subject"] = contenu.sujet
        msg["From"] = from_addr
        msg["To"] = destinataire
        msg.attach(MIMEText(contenu.corps_texte, "plain", "utf-8"))
        if contenu.corps_html:
            msg.attach(MIMEText(contenu.corps_html, "html", "utf-8"))

        try:
            with smtplib.SMTP(host, port, timeout=20) as server:
                if use_tls:
                    server.starttls()
                if username and password:
                    server.login(username, password)
                server.sendmail(from_addr, [destinataire], msg.as_string())
        except (smtplib.SMTPException, OSError) as exc:
            logger.warning("Échec d'envoi courriel à %s: %s", destinataire, exc)
            return DeliveryResult(succes=False, erreur=str(exc))

        return DeliveryResult(succes=True)


CHANNEL_CLASS = EmailChannel
