"""Interface générique des canaux de notification (voir
registry/notification_channels.yaml). Même principe que les sources : le moteur
(falkye/engine.py) ne connaît que cette interface, jamais un canal précis."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from falkye.models.profile import Profile
    from falkye.registry.loader import NotificationChannelDef


# Formes de livraison (charte, section 16 : "le groupement est la forme par défaut;
# l'envoi unitaire est l'exception justifiée, jamais l'inverse — l'exception a besoin
# d'un seuil explicite, sinon elle redevient la norme par glissement").
#
# Déclarées PAR CANAL au registre (registry/notification_channels.yaml,
# `formes_livraison`) plutôt que décidées dans le moteur : un canal qui pousse vers un
# système (webhook, CRM) livre à l'unité parce qu'une machine consomme des événements;
# un canal lu par un humain livre groupé. Le moteur ne connaît ni l'un ni l'autre — il
# demande au registre quels canaux servent la forme qu'il est en train de livrer.
FORME_RESUME = "resume"
FORME_UNITAIRE = "unitaire"
FORMES_LIVRAISON = (FORME_RESUME, FORME_UNITAIRE)


@dataclass
class NotificationContent:
    sujet: str
    corps_texte: str
    corps_html: str | None = None
    # Payload structuré (spec section 4bis, Radar+ "accès API/webhook complet" :
    # "pousser chaque nouveau signal... vers un système externe" — un CRM/ERP a
    # besoin de champs, pas d'un texte à reparser). Rempli par
    # falkye/notifications/formatter.py::formatter_notification pour TOUT canal
    # (pas un formatter séparé pour webhook) ; les canaux texte (email, sms) l'
    # ignorent simplement, WebhookChannel s'en sert comme corps JSON.
    donnees_structurees: dict | None = None
    # En-têtes de message supplémentaires — point d'accroche pour
    # `List-Unsubscribe` / `List-Unsubscribe-Post` (RFC 8058), exigés par Gmail et
    # Yahoo. Volontairement générique plutôt qu'un champ `list_unsubscribe` dédié :
    # un canal qui n'a pas de notion d'en-tête (SMS, webhook) l'ignore simplement,
    # au lieu d'avoir à connaître une exigence propre au courriel.
    entetes: dict[str, str] | None = None


@dataclass
class DeliveryResult:
    succes: bool
    erreur: str | None = None
    # Identifiant du message CHEZ le fournisseur, quand il en donne un.
    # `succes=True` veut dire « accepté », jamais « livré » — c'est cette
    # référence qui permet de lui redemander plus tard ce qui est réellement
    # arrivé (voir falkye/reconciliation.py). Un canal qui n'en fournit pas
    # laisse None : sa remise ne sera simplement jamais réconciliée.
    reference: str | None = None


class EtatLivraison(str, Enum):
    """Ce que le fournisseur dit d'un envoi qu'il a DÉJÀ accepté."""

    CONFIRMEE = "confirmee"
    REBONDIE = "rebondie"
    # Encore en vol, ou hors de la fenêtre de rétention du fournisseur. Ne rien
    # savoir n'est pas savoir que c'est perdu : ce cas ne remet rien en attente.
    INCONNUE = "inconnue"


@dataclass
class VerdictLivraison:
    etat: EtatLivraison
    detail: str | None = None


class NotificationChannel(ABC):
    def __init__(self, channel_def: "NotificationChannelDef"):
        self.channel_def = channel_def

    @abstractmethod
    def envoyer(self, destinataire: str, contenu: NotificationContent) -> DeliveryResult:
        raise NotImplementedError

    def resoudre_destinataire(self, profile: "Profile") -> str | None:
        """Destination pour CE canal à partir du profil — par défaut le courriel
        (seule donnée de contact universelle en Phase 1). Un canal dont la
        destination dépend d'une configuration propre au profil (ex.
        WebhookChannel avec `profile.webhook_url`, réservé Radar+) redéfinit
        cette méthode plutôt que de dépendre d'un champ codé en dur dans
        falkye/engine.py — retourner None signifie "aucune destination valide
        pour ce profil", auquel cas la livraison sur ce canal est simplement
        ignorée pour cette notification (pas une erreur).

        **Un profil désabonné n'a plus de destination humaine.** Le contrôle est
        ici, et non chez chaque canal, parce que c'est le seul endroit où la
        destination « la personne » se calcule — un canal humain ajouté demain
        hérite du respect du désabonnement sans avoir à y penser, et ne peut pas
        l'oublier. WebhookChannel redéfinit cette méthode et n'est donc pas
        concerné, ce qui est voulu : se désabonner d'un courriel n'est pas
        résilier une intégration (voir Profile.desabonne_le)."""
        if profile.desabonne_le is not None:
            return None
        return profile.courriel

    def etat_des_livraisons(self, references: list[str]) -> dict[str, VerdictLivraison]:
        """Ce que le fournisseur dit d'envois qu'il a déjà acceptés.

        Défaut : un dictionnaire vide — « ce canal ne sait pas dire ». C'est le
        comportement correct pour un canal sans notion de remise différée (un
        webhook répond dans l'appel, il n'y a rien à réconcilier plus tard), et
        c'est aussi ce qui fait qu'ajouter un canal n'oblige pas à écrire cette
        méthode pour que le reste fonctionne.

        Ne jamais lever : une panne du fournisseur pendant la réconciliation est
        une panne d'OBSERVATION. Si elle interrompait le cycle, on perdrait les
        envois de la semaine en plus de l'information sur ceux de la précédente.
        Retourner {} laisse les remises en `acceptee`, donc réexaminées au cycle
        suivant — le comportement sûr.
        """
        return {}


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
