"""Sonde du contrat Postmark — chantier 28.

Rejoue contre la VRAIE API les quatre réponses sur lesquelles
`falkye/notifications/postmark_channel.py` est bâti, et sur lesquelles ses tests
sont calqués. Sans elle, ces tests ne prouveraient que la cohérence du code avec
lui-même — c'est la section 8 de la charte : ne jamais présumer une capacité non
testée.

**Aucun courriel n'est livré.** La sonde emploie le jeton de test documenté
`POSTMARK_API_TEST`, que Postmark accepte en retournant un succès sans rien
envoyer. Le seul autre appel utilise un jeton volontairement invalide, refusé
avant tout traitement. Il n'y a donc pas d'issue où un message parte.

Usage (aucune dépendance hors `requests`, déjà au projet) :

    PYTHONPATH=. python outils/sonde_postmark.py

Résultat du 2026-09-05 : 4/4. Le contrat tenait exactement ce que le module en
suppose, y compris `Headers`, `MessageStream` et `HtmlBody`.
"""
import json

import requests

from falkye.notifications.postmark_channel import URL_ENVOI

JETON_DE_TEST = "POSTMARK_API_TEST"  # documenté par Postmark, ne livre jamais
DESTINATION = "sonde@example.com"  # domaine réservé par la RFC 2606
EXPEDITEUR = "sonde@avis.falkye.com"

resultats = []


def verdict(nom, ok, detail=""):
    resultats.append((nom, ok))
    print(f"  [{'OK ' if ok else 'ÉCHEC'}] {nom}" + (f" — {detail}" if detail else ""))


def appeler(charge, jeton=JETON_DE_TEST):
    reponse = requests.post(
        URL_ENVOI,
        json=charge,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Postmark-Server-Token": jeton,
        },
        timeout=25,
    )
    return reponse.status_code, reponse.json()


BASE = {"From": EXPEDITEUR, "To": DESTINATION, "Subject": "sonde de contrat", "TextBody": "sonde"}

print("=== SONDE POSTMARK — contrat de l'API d'envoi ===\n")

# 1. Envoi accepté — la forme du succès.
code, corps = appeler(dict(BASE))
verdict(
    "Envoi accepté (jeton de test)",
    code == 200 and corps.get("ErrorCode") == 0,
    f"HTTP {code}, ErrorCode {corps.get('ErrorCode')}, « {corps.get('Message')} »",
)

# 2. Jeton invalide — la forme du refus d'authentification.
code, corps = appeler(dict(BASE), jeton="jeton-volontairement-invalide")
verdict(
    "Jeton invalide refusé",
    code == 401 and corps.get("ErrorCode") == 10,
    f"HTTP {code}, ErrorCode {corps.get('ErrorCode')}",
)

# 3. Destinataire malformé — la forme du refus de validation, et le message
#    qu'on remonte tel quel à l'exploitation.
code, corps = appeler({**BASE, "To": "pas-une-adresse"})
verdict(
    "Adresse malformée refusée",
    code == 422 and corps.get("ErrorCode") == 300,
    f"HTTP {code}, ErrorCode {corps.get('ErrorCode')}",
)

# 4. Les trois champs dont dépend le module : les en-têtes de désabonnement
#    (RFC 8058), le flux de diffusion, et le corps HTML.
code, corps = appeler(
    {
        **BASE,
        "HtmlBody": "<p>sonde</p>",
        "MessageStream": "broadcast",
        "Headers": [
            {"Name": "List-Unsubscribe", "Value": "<https://lien.falkye.com/d/JETON>"},
            {"Name": "List-Unsubscribe-Post", "Value": "List-Unsubscribe=One-Click"},
        ],
    }
)
verdict(
    "Headers + MessageStream + HtmlBody acceptés",
    code == 200 and corps.get("ErrorCode") == 0,
    f"HTTP {code}, ErrorCode {corps.get('ErrorCode')}",
)

print("\n=== VERDICT ===")
echecs = [nom for nom, ok in resultats if not ok]
print(("ROUGE — " + ", ".join(echecs)) if echecs else f"VERT — {len(resultats)}/{len(resultats)}")
raise SystemExit(1 if echecs else 0)
