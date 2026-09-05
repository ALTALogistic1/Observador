"""Canal courriel par API HTTPS — Postmark.

**Pourquoi il remplace SMTP.** Mesuré le 2026-09-04 : l'égress est limité au
port 443, le port 587 est en délai d'attente, et aucune liste blanche de domaines
ne l'ouvre. `email_channel.py` est correct et testé, mais son transport n'existe
pas ici. Il reste au registre pour un hôte qui l'autoriserait; l'envoi réel passe
par ce module.

**Pourquoi Postmark plutôt qu'un autre.** Un petit expéditeur n'a pas de
réputation propre : il hérite de celle du parc partagé de son fournisseur. Le
critère qui départage n'est donc pas le prix mais la sévérité avec laquelle chaque
fournisseur surveille son propre parc — et Postmark est le plus regardant.

**Le flux de DIFFUSION, pas le transactionnel.** Un résumé hebdomadaire est une
diffusion. Postmark sépare les deux en flux distincts, sur des IP distinctes, et
prend la distinction au sérieux : une suspension au lancement coûterait
infiniment plus que l'écart entre les deux. D'où `broadcast` par défaut plutôt
que `outbound`, et un défaut explicite plutôt qu'une variable obligatoire de plus
— se tromper de flux par oubli de configuration est le risque le plus cher ici.

**Contrat éprouvé en direct contre `api.postmarkapp.com` le 2026-09-05**, avec le
jeton de test documenté `POSTMARK_API_TEST` (accepte l'appel, ne livre rien) :

    envoi accepté        200  {"ErrorCode":0,"Message":"Test job accepted",...}
    jeton invalide       401  {"ErrorCode":10,"Message":"Request does not
                              contain a valid Server token."}
    adresse malformée    422  {"ErrorCode":300,"Message":"Error parsing 'To':
                              Illegal email address ..."}

`Headers` (pour `List-Unsubscribe` / `List-Unsubscribe-Post`), `MessageStream` et
`HtmlBody` sont acceptés — vérifié par un appel réel, pas supposé.

Un `ErrorCode` non nul est traité comme un échec même sur un 200 : la
documentation ne garantit pas que le code HTTP porte toute l'information, et un
faux succès ferait marquer un lot comme livré alors qu'il ne l'est pas — c'est
exactement le défaut que la réunification des chemins de livraison vient de
corriger.
"""
from __future__ import annotations

import logging
import os

import requests

from falkye.notifications.base import DeliveryResult, NotificationChannel, NotificationContent

logger = logging.getLogger(__name__)

URL_ENVOI = "https://api.postmarkapp.com/email"

# Flux de diffusion — voir la docstring. Surclassable par
# FALKYE_POSTMARK_MESSAGE_STREAM si un flux au nom différent est créé au compte.
FLUX_PAR_DEFAUT = "broadcast"

DELAI_SECONDES = 20


class PostmarkChannel(NotificationChannel):
    def envoyer(self, destinataire: str, contenu: NotificationContent) -> DeliveryResult:
        jeton = os.environ.get("FALKYE_POSTMARK_SERVER_TOKEN")
        expediteur = os.environ.get("FALKYE_POSTMARK_FROM_ADDR")
        flux = os.environ.get("FALKYE_POSTMARK_MESSAGE_STREAM") or FLUX_PAR_DEFAUT

        if not jeton or not expediteur:
            return DeliveryResult(
                succes=False,
                erreur=(
                    "Configuration Postmark incomplète (FALKYE_POSTMARK_SERVER_TOKEN / "
                    "FALKYE_POSTMARK_FROM_ADDR manquants) — voir .env.example."
                ),
            )

        charge = {
            "From": expediteur,
            "To": destinataire,
            "Subject": contenu.sujet,
            "TextBody": contenu.corps_texte,
            "MessageStream": flux,
        }
        if contenu.corps_html:
            charge["HtmlBody"] = contenu.corps_html
        if contenu.entetes:
            charge["Headers"] = [{"Name": nom, "Value": valeur} for nom, valeur in contenu.entetes.items()]

        try:
            reponse = requests.post(
                URL_ENVOI,
                json=charge,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "X-Postmark-Server-Token": jeton,
                },
                timeout=DELAI_SECONDES,
            )
        except requests.RequestException as exc:
            logger.warning("Échec d'appel Postmark pour %s : %s", destinataire, exc)
            return DeliveryResult(succes=False, erreur=f"{type(exc).__name__}: {exc}")

        return _interpreter(reponse, destinataire)


def _interpreter(reponse, destinataire: str) -> DeliveryResult:
    """Traduit la réponse Postmark en DeliveryResult.

    Le corps JSON porte toujours `ErrorCode` et `Message`, y compris sur une
    erreur — c'est lui qui explique, pas le code HTTP seul. Une réponse
    illisible (proxy, page d'erreur HTML) est un échec, jamais un succès par
    défaut.
    """
    try:
        corps = reponse.json()
    except ValueError:
        extrait = (reponse.text or "")[:200]
        return DeliveryResult(
            succes=False, erreur=f"réponse Postmark illisible (HTTP {reponse.status_code}) : {extrait}"
        )

    code = corps.get("ErrorCode")
    message = corps.get("Message", "")

    if reponse.status_code == 200 and code == 0:
        return DeliveryResult(succes=True)

    logger.warning(
        "Postmark a refusé l'envoi à %s — HTTP %s, ErrorCode %s : %s",
        destinataire,
        reponse.status_code,
        code,
        message,
    )
    return DeliveryResult(succes=False, erreur=f"HTTP {reponse.status_code}, ErrorCode {code} : {message}")


CHANNEL_CLASS = PostmarkChannel
