"""Les gestes qu'un courriel peut déclencher — désabonnement et rétroaction.

Ce module porte la LOGIQUE. Le point d'entrée HTTPS qui l'expose n'en est que
l'enveloppe : tout ce qui suit se teste sans serveur, et le serveur n'aura rien
à décider.

**Pourquoi POST et non GET, pour le geste lui-même.** Les analyseurs de liens
des messageries et des antivirus suivent les GET des courriels avant que
l'humain ne les ouvre. Un désabonnement sur GET partirait donc tout seul, et une
rétroaction « pas pertinent » sur GET fabriquerait de la donnée que personne n'a
voulue — dans le seul mécanisme de correction du produit. Le RFC 8058 impose
d'ailleurs POST pour cette raison exacte. Règle : **GET montre, POST agit.**

**Idempotence.** Un second appel ne refait rien mais ne se plaint pas non plus.
Un désabonnement redemandé confirme; le présenter comme une erreur pousserait
vers le bouton « pourriel », ce qui coûte infiniment plus cher.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from falkye.models.jeton_lien import ActionJeton, JetonLien, empreinte, engendrer_jeton
from falkye.models.notification import Notification
from falkye.models.profile import Profile

# Chemins du point d'entrée. Courts délibérément : ils voyagent dans un en-tête
# de courriel, et certains agents tronquent les URL longues à l'affichage.
CHEMIN_DESABONNEMENT = "d"
CHEMIN_PAS_PERTINENT = "r"

# Identifiant du statut au registre (registry/statuts_suivi.yaml). Nommé ici
# plutôt que déduit de la valeur de l'énumération : les deux se ressemblent
# aujourd'hui, mais rien ne les lie — et un test qui repose sur une
# ressemblance vérifie une coïncidence, pas un comportement.
STATUT_PAS_PERTINENT = "pas_pertinent"

_CHEMIN_PAR_ACTION = {
    ActionJeton.DESABONNEMENT: CHEMIN_DESABONNEMENT,
    ActionJeton.PAS_PERTINENT: CHEMIN_PAS_PERTINENT,
}


class LienInvalide(Exception):
    """Jeton inconnu, ou jeton employé pour une action qui n'est pas la sienne."""


def base_url() -> str:
    """L'origine publique du point d'entrée, ex. https://lien.falkye.com.

    Absente, on ne devine pas : un résumé partirait alors avec un en-tête de
    désabonnement inutilisable, c'est-à-dire décoratif — précisément ce que le
    mandat interdit. Mieux vaut ne pas envoyer que d'envoyer sans issue de
    sortie.
    """
    valeur = os.environ.get("FALKYE_LIEN_BASE_URL")
    if not valeur:
        raise RuntimeError(
            "FALKYE_LIEN_BASE_URL n'est pas configurée — impossible de construire un lien de "
            "désabonnement. Un résumé ne doit jamais partir sans lien de désabonnement "
            "fonctionnel (voir .env.example)."
        )
    return valeur.rstrip("/")


def _creer(
    db_session: Session, action: ActionJeton, profile_id: int, notification_id: int | None = None
) -> str:
    jeton = engendrer_jeton()
    db_session.add(
        JetonLien(
            jeton_empreinte=empreinte(jeton),
            action=action,
            profile_id=profile_id,
            notification_id=notification_id,
        )
    )
    db_session.flush()
    return jeton


def _url(action: ActionJeton, jeton: str) -> str:
    return f"{base_url()}/{_CHEMIN_PAR_ACTION[action]}/{jeton}"


def url_desabonnement(db_session: Session, profile: Profile) -> str:
    """Un jeton neuf à chaque envoi, et TOUS les anciens restent valables.

    Puisque seule l'empreinte est conservée, la valeur en clair d'un jeton
    passé n'est plus reconstructible : chaque résumé doit donc en émettre un
    nouveau. La question est ce qu'on fait des précédents, et la réponse est :
    rien.

    Les révoquer casserait le lien de désabonnement de tous les courriels
    encore dans la boîte de réception — or celui qui se désabonne depuis un
    message de la semaine dernière est précisément celui qu'il faut laisser
    partir sans friction. Un lien de désabonnement mort ne fait pas rester
    l'abonné : il le pousse vers le bouton « pourriel », qui coûte à la
    réputation du domaine d'envoi tout entier.

    Et il n'y a rien à gagner à les révoquer : tous les jetons d'un même profil
    autorisent exactement le même geste, sur la même cible. Leur nombre ne
    donne aucun pouvoir de plus qu'un seul. Le coût est une ligne par envoi,
    soit une cinquantaine par an et par profil.
    """
    jeton = _creer(db_session, ActionJeton.DESABONNEMENT, profile.id)
    return _url(ActionJeton.DESABONNEMENT, jeton)


def url_pas_pertinent(db_session: Session, notification: Notification) -> str:
    jeton = _creer(
        db_session, ActionJeton.PAS_PERTINENT, notification.profile_id, notification_id=notification.id
    )
    return _url(ActionJeton.PAS_PERTINENT, jeton)


def _resoudre(db_session: Session, jeton: str, action: ActionJeton) -> JetonLien:
    ligne = db_session.execute(
        select(JetonLien).where(JetonLien.jeton_empreinte == empreinte(jeton))
    ).scalar_one_or_none()
    if ligne is None or ligne.action != action:
        # Même réponse dans les deux cas : ne pas révéler qu'un jeton existe
        # mais pour une autre action.
        raise LienInvalide("jeton inconnu")
    return ligne


def decrire(db_session: Session, jeton: str, action: ActionJeton) -> dict:
    """Ce qu'une page de confirmation (GET) a besoin d'afficher, sans rien changer."""
    ligne = _resoudre(db_session, jeton, action)
    profile = db_session.get(Profile, ligne.profile_id)
    description = {
        "action": ligne.action.value,
        "courriel": profile.courriel if profile else None,
        "deja_fait": ligne.utilise_le is not None,
    }
    if ligne.notification_id is not None:
        notification = db_session.get(Notification, ligne.notification_id)
        if notification is not None and notification.company is not None:
            description["entreprise"] = (
                notification.company.nom_officiel_req or notification.company.nom_detecte
            )
    return description


def consommer_desabonnement(db_session: Session, jeton: str) -> Profile:
    """Coupe l'envoi de courriel pour ce profil. Idempotent."""
    ligne = _resoudre(db_session, jeton, ActionJeton.DESABONNEMENT)
    profile = db_session.get(Profile, ligne.profile_id)
    if profile is None:
        raise LienInvalide("jeton inconnu")

    maintenant = datetime.now(timezone.utc)
    if profile.desabonne_le is None:
        profile.desabonne_le = maintenant
    if ligne.utilise_le is None:
        ligne.utilise_le = maintenant
    db_session.flush()
    return profile


def consommer_pas_pertinent(db_session: Session, jeton: str, registry=None) -> Notification:
    """Marque la notification « pas pertinent ». Idempotent.

    Réutilise `appliquer_statut`, qui déclenche déjà la rétroaction de
    pertinence quand le statut le déclare au registre — même règle que le
    marquage depuis le tableau de bord, pas un second chemin. C'est la
    discipline que la réunification des chemins de livraison vient d'appliquer
    ailleurs.
    """
    from falkye.registry.loader import get_registry
    from falkye.statut_suivi import appliquer_statut

    ligne = _resoudre(db_session, jeton, ActionJeton.PAS_PERTINENT)
    notification = db_session.get(Notification, ligne.notification_id) if ligne.notification_id else None
    if notification is None:
        raise LienInvalide("jeton inconnu")

    if ligne.utilise_le is None:
        # Le second clic ne réapplique PAS le statut : la rétroaction de
        # pertinence est cumulative (elle compte les marquages), et un lien
        # cliqué deux fois pèserait double sur la sphère.
        appliquer_statut(db_session, notification, STATUT_PAS_PERTINENT, registry or get_registry())
        ligne.utilise_le = datetime.now(timezone.utc)
        db_session.flush()
    return notification
