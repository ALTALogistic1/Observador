"""Le chemin de livraison — UN SEUL, pour toutes les formes.

Pourquoi ce module existe. Il y avait deux chemins : `engine.deliver_notification`
pour la notification unitaire, et `summary.generer_et_envoyer_resume` pour le
résumé groupé. Ils ont divergé, et la divergence n'était visible d'aucun test
parce que le second n'en avait aucun :

  - le résumé appelait `channel.envoyer(profile.courriel, ...)` en dur, sans passer
    par `resoudre_destinataire` — donc le canal webhook, actif au registre,
    recevait une adresse courriel à la place d'une URL. Chaque résumé produisait
    une livraison en échec parasite, et la réserve de palier du webhook
    (RADAR_PLUS seulement) était contournée;
  - la date d'envoi du résumé n'était posée que si `channel_def.id == "email"`,
    identifiant codé en dur — le nouveau canal aurait cessé de la remplir en
    silence.

Un troisième canal par-dessus deux chemins divergents en aurait fait trois. D'où
la réunification avant l'ajout, plutôt qu'après.

Ce que ce module garantit, pour toute forme de livraison :
  1. le registre décide quels canaux servent la forme demandée
     (`formes_livraison`, voir base.py::FORMES_LIVRAISON) — jamais le moteur;
  2. chaque canal résout SA destination (`resoudre_destinataire`), ce qui porte
     aussi les réserves de palier;
  3. un canal sans destination valide est ignoré, ce n'est pas un échec;
  4. le résultat par canal remonte à l'appelant, qui seul sait quoi en faire.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from falkye.models.notification import Notification, NotificationDelivery
from falkye.models.profile import Profile
from falkye.notifications.base import NotificationContent
from falkye.registry.loader import Registry


@dataclass
class ResultatCanal:
    channel_id: str
    succes: bool
    erreur: str | None = None


def livrer(
    db_session: Session,
    profile: Profile,
    contenu: NotificationContent,
    registry: Registry,
    forme: str,
    notification: Notification | None = None,
) -> list[ResultatCanal]:
    """Livre `contenu` sur tous les canaux actifs servant `forme`.

    `notification` n'est fourni que pour une livraison unitaire : il sert
    uniquement à enregistrer la trace `NotificationDelivery`. Un résumé n'a pas
    de notification unique à rattacher — sa trace est `PeriodicSummary.envoye_le`.
    """
    resultats: list[ResultatCanal] = []
    for channel_def in registry.canaux_actifs():
        if not channel_def.sert_forme(forme):
            continue
        channel = channel_def.charger_canal()
        if channel is None:
            continue
        destinataire = channel.resoudre_destinataire(profile)
        if destinataire is None:
            # Pas de destination valide pour ce profil (webhook non configuré,
            # palier insuffisant) — silencieux, pas un échec de livraison.
            continue
        resultat = channel.envoyer(destinataire, contenu)
        resultats.append(
            ResultatCanal(channel_id=channel_def.id, succes=resultat.succes, erreur=resultat.erreur)
        )
        if notification is not None:
            db_session.add(
                NotificationDelivery(
                    notification_id=notification.id,
                    channel_id=channel_def.id,
                    statut="envoyee" if resultat.succes else "echec",
                    erreur=resultat.erreur,
                )
            )
    return resultats


def au_moins_un_succes(resultats: list[ResultatCanal]) -> bool:
    """Vrai si au moins un canal a livré.

    Faux quand AUCUN canal n'a servi la forme demandée — et c'est voulu : un
    résumé que personne n'a reçu n'est pas un résumé envoyé, que la cause soit un
    échec du fournisseur ou l'absence de canal configuré. C'est ce qui fait que
    les opportunités restent en attente au lieu d'être marquées livrées.
    """
    return any(r.succes for r in resultats)
