"""Résumé périodique — la forme de livraison PAR DÉFAUT depuis le 2026-09-05.

Charte section 16 : « le groupement est la forme par défaut; l'envoi unitaire est
l'exception justifiée, jamais l'inverse — l'exception a besoin d'un seuil
explicite, sinon elle redevient la norme par glissement ». Le courriel individuel
par notification ne part plus (voir falkye/engine.py::deliver_notification, qui ne
sert plus que les canaux poussant vers un système).

Deux corrections structurelles apportées le 2026-09-05, l'une et l'autre invisibles
en test parce que ce module n'en avait AUCUN :

**Le lot ne se perd plus.** L'ancienne version marquait les notifications
« incluses » AVANT d'envoyer, et les sélectionnait par fenêtre de dates. Un envoi
en échec laissait donc des opportunités marquées comme livrées, définitivement :
la fenêtre suivante ne les voyait plus. C'était le même motif que la quarantaine
du chantier 1 — un filet qui capture sans livrer. Désormais la sélection porte sur
l'ÉTAT (`inclus_dans_resume`), pas sur une fenêtre, et le marquage n'a lieu
qu'après un envoi réussi. Une opportunité attend donc autant de cycles qu'il le
faut, et sort au premier envoi qui aboutit.

**Un seul chemin de livraison.** L'envoi passe par
falkye/notifications/livraison.py, comme la livraison unitaire — voir ce module
pour ce que la divergence des deux chemins coûtait.

`periode_debut` reste enregistrée comme métadonnée du résumé (la fenêtre que
l'appelant avait en tête), mais ne filtre plus rien : c'est l'état d'attente qui
décide. Conséquence assumée, à connaître : un tout premier résumé sur une base qui
porte déjà des notifications les emporte toutes. Le plafond d'antériorité du
chantier 25 est ce qui bornera ça — il n'entre pas ici.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from falkye.models.notification import Notification, PeriodicSummary
from falkye.models.profile import Profile
from falkye.notifications.base import FORME_RESUME, NotificationContent
from falkye.notifications.livraison import au_moins_un_succes, livrer
from falkye.registry.loader import Registry, get_registry

_NIVEAU_AFFICHAGE = {"faible": "Faible", "moyen": "Moyen", "eleve": "Élevé"}


def notifications_en_attente(db_session: Session, profile: Profile, avant: datetime) -> list[Notification]:
    """Les opportunités qui n'ont encore été livrées par aucun résumé.

    Deux filtres, et pas de fenêtre de dates basse — voir la docstring du module.

    `hors_profil` est exclu : un signal redirigé hors du profil déclaré n'est
    « jamais mélangé aux notifications normales » (spec section 8bis) et ne se
    consulte qu'au tableau de bord. L'ancienne version l'incluait au résumé alors
    que la livraison unitaire l'excluait déjà — troisième divergence entre les
    deux chemins, corrigée ici.
    """
    return list(
        db_session.execute(
            select(Notification)
            .where(
                Notification.profile_id == profile.id,
                Notification.inclus_dans_resume.is_(False),
                Notification.hors_profil.is_(False),
                Notification.created_at < avant,
            )
            .order_by(Notification.score_confiance.desc())
        )
        .scalars()
        .all()
    )


def generer_resume(
    db_session: Session, profile: Profile, periode_debut: datetime, periode_fin: datetime
) -> tuple[PeriodicSummary, list[Notification]]:
    """Construit le résumé SANS marquer quoi que ce soit comme livré.

    Le marquage appartient à `generer_et_envoyer_resume`, après un envoi réussi —
    c'est toute la correction du lot perdu.
    """
    notifications = notifications_en_attente(db_session, profile, avant=periode_fin)

    summary = PeriodicSummary(
        profile_id=profile.id,
        periode_debut=periode_debut,
        periode_fin=periode_fin,
        notification_ids=[n.id for n in notifications],
    )
    db_session.add(summary)
    db_session.flush()
    return summary, notifications


def _bloc_opportunite(
    notification: Notification, registry: Registry, ligne_interpretation: str | None = None
) -> str:
    """Une opportunité : ce qu'elle est, pourquoi elle a été repérée.

    Le MOTIF DU REPÉRAGE est ce qui manquait au résumé. Charte section 16 : « un
    résultat n'est bon que s'il donne une raison d'agir maintenant, pas seulement
    un nom — un nom d'entreprise sans le motif précis du repérage ne vaut pas mieux
    qu'une liste achetée ailleurs ». Les motifs viennent de la structure de faits
    déjà produite par le moteur (`NotificationSignal.justification`), reprise ici
    telle quelle plutôt que reformulée.

    La CATÉGORIE de signal est affichée, jamais le nom de la source — neutralité
    des libellés (charte section 6), même règle que le formateur individuel.

    `ligne_interpretation` est la place RÉSERVÉE, et volontairement vide, pour la
    ligne d'interprétation du chantier 21 (gabarits liés au couple signal ×
    sphère). Elle ne se remplit pas ici : ce chantier livre la version brute. Le
    paramètre existe pour que la place ne soit pas à rouvrir, et le rendu n'émet
    rien tant que rien ne lui est passé — jamais un texte de remplissage, qui
    serait précisément l'encouragement non mérité que la section 16 interdit.
    """
    nom = notification.company.nom_officiel_req or notification.company.nom_detecte
    niveau = _NIVEAU_AFFICHAGE[notification.niveau_confiance.value]
    pertinence = notification.niveau_pertinence.value if notification.niveau_pertinence else "non disponible"

    lignes = [f"• {nom} — confiance {niveau} ({notification.score_confiance}/100), pertinence {pertinence}"]

    if ligne_interpretation:
        lignes.append(f"    {ligne_interpretation}")

    for ns in notification.signaux_contributifs:
        signal_type = registry.signal_types.get(ns.signal.signal_type_id)
        categorie = signal_type.nom if signal_type else ns.signal.signal_type_id
        lignes.append(f"    [{categorie}] {ns.justification}")

    ville = notification.company.ville
    if ville:
        lignes.append(f"    {ville}")

    return "\n".join(lignes)


def formatter_resume(
    summary: PeriodicSummary, notifications: list[Notification], registry: Registry | None = None
) -> NotificationContent:
    registry = registry or get_registry()

    if not notifications:
        # Formulation à revoir au chantier 14 : la charte (section 16) demande de
        # dire une absence par le travail accompli — combien d'entreprises ont été
        # suivies et qu'aucune n'a franchi le seuil — plutôt que par le vide, qui
        # se lit comme une panne. Ce compte n'existe pas encore; le fabriquer ici
        # serait pire que la phrase neutre. Laissé tel quel, sciemment.
        corps = "Aucune nouvelle entreprise repérée durant cette période."
    else:
        blocs = [_bloc_opportunite(n, registry) for n in notifications]
        pluriel = "s" if len(notifications) > 1 else ""
        corps = (
            f"{len(notifications)} entreprise{pluriel} repérée{pluriel} :\n\n"
            + "\n\n".join(blocs)
            + "\n"
        )

    debut = summary.periode_debut.strftime("%Y-%m-%d")
    fin = summary.periode_fin.strftime("%Y-%m-%d")
    sujet = f"[FALKYE] Résumé du {debut} au {fin}"
    return NotificationContent(sujet=sujet, corps_texte=corps)


def generer_et_envoyer_resume(db_session: Session, profile: Profile, jours: int = 7) -> PeriodicSummary:
    registry = get_registry()
    periode_fin = datetime.now(timezone.utc)
    periode_debut = periode_fin - timedelta(days=jours)

    summary, notifications = generer_resume(db_session, profile, periode_debut, periode_fin)
    contenu = formatter_resume(summary, notifications, registry)

    resultats = livrer(db_session, profile, contenu, registry, FORME_RESUME)

    if au_moins_un_succes(resultats):
        summary.envoye_le = datetime.now(timezone.utc)
        for n in notifications:
            n.inclus_dans_resume = True
    # Sinon : `envoye_le` reste NULL et rien n'est marqué. Les opportunités
    # repartiront au prochain résumé. Le PeriodicSummary non envoyé subsiste comme
    # trace de la tentative — c'est ce qui distingue « rien à envoyer » de
    # « l'envoi a échoué ».

    db_session.commit()
    return summary
