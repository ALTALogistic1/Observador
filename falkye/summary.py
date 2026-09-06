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

from falkye.liens import url_desabonnement, url_pas_pertinent
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
    notification: Notification,
    registry: Registry,
    lien_pas_pertinent: str | None = None,
    ligne_interpretation: str | None = None,
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

    if lien_pas_pertinent:
        # La rétroaction minimale — la seule boucle de correction du produit.
        # Formulée par l'action qu'elle appelle, jamais comme un jugement sur
        # l'opportunité (charte section 16).
        lignes.append(f"    Pas pertinent pour vous? {lien_pas_pertinent}")

    return "\n".join(lignes)


def formatter_resume(
    summary: PeriodicSummary,
    notifications: list[Notification],
    registry: Registry | None = None,
    liens_pas_pertinent: dict[int, str] | None = None,
    lien_desabonnement: str | None = None,
) -> NotificationContent:
    registry = registry or get_registry()
    liens_pas_pertinent = liens_pas_pertinent or {}

    if not notifications:
        # Formulation à revoir au chantier 14 : la charte (section 16) demande de
        # dire une absence par le travail accompli — combien d'entreprises ont été
        # suivies et qu'aucune n'a franchi le seuil — plutôt que par le vide, qui
        # se lit comme une panne. Ce compte n'existe pas encore; le fabriquer ici
        # serait pire que la phrase neutre. Laissé tel quel, sciemment.
        corps = "Aucune nouvelle entreprise repérée durant cette période."
    else:
        blocs = [
            _bloc_opportunite(n, registry, lien_pas_pertinent=liens_pas_pertinent.get(n.id))
            for n in notifications
        ]
        pluriel = "s" if len(notifications) > 1 else ""
        corps = (
            f"{len(notifications)} entreprise{pluriel} repérée{pluriel} :\n\n"
            + "\n\n".join(blocs)
            + "\n"
        )

    entetes = None
    if lien_desabonnement:
        # Le lien visible dans le corps ET l'en-tête : l'un pour la personne qui
        # lit, l'autre pour le bouton natif de sa messagerie (RFC 8058). Les deux
        # mènent à la même URL, donc au même geste.
        corps += f"\n---\nNe plus recevoir ces résumés : {lien_desabonnement}\n"
        entetes = {
            "List-Unsubscribe": f"<{lien_desabonnement}>",
            # Sans cet en-tête, Gmail et Yahoo n'affichent pas le bouton natif :
            # c'est lui qui déclare que l'URL accepte le POST en un clic.
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        }

    debut = summary.periode_debut.strftime("%Y-%m-%d")
    fin = summary.periode_fin.strftime("%Y-%m-%d")
    sujet = f"[FALKYE] Résumé du {debut} au {fin}"
    return NotificationContent(sujet=sujet, corps_texte=corps, entetes=entetes)


def generer_et_envoyer_resume(
    db_session: Session, profile: Profile, jours: int = 7
) -> PeriodicSummary | None:
    """None si le profil est désabonné — rien n'est généré ni marqué.

    La garde est ICI et pas seulement à la résolution de destinataire : sans
    elle, un résumé serait bien construit, n'aurait aucun canal où aller, ne
    serait donc jamais marqué envoyé, et les opportunités s'accumuleraient
    indéfiniment en attente. Le désabonné coûterait un résumé mort par cycle,
    pour toujours.
    """
    if profile.desabonne_le is not None:
        return None

    registry = get_registry()
    periode_fin = datetime.now(timezone.utc)
    periode_debut = periode_fin - timedelta(days=jours)

    summary, notifications = generer_resume(db_session, profile, periode_debut, periode_fin)

    # Les jetons sont créés AVANT le formatage : ce sont eux qui portent les
    # URL. `url_desabonnement` lève si le point d'entrée n'est pas configuré —
    # aucun résumé ne part alors, ce qui est voulu (voir falkye/liens.py).
    lien_desabo = url_desabonnement(db_session, profile)
    liens_retro = {n.id: url_pas_pertinent(db_session, n) for n in notifications}

    contenu = formatter_resume(
        summary,
        notifications,
        registry,
        liens_pas_pertinent=liens_retro,
        lien_desabonnement=lien_desabo,
    )

    resultats = livrer(db_session, profile, contenu, registry, FORME_RESUME, summary=summary)

    if au_moins_un_succes(resultats):
        summary.envoye_le = datetime.now(timezone.utc)
        for n in notifications:
            n.inclus_dans_resume = True
    # Sinon : `envoye_le` reste NULL et rien n'est marqué. Les opportunités
    # repartiront au prochain résumé. Le PeriodicSummary non envoyé subsiste comme
    # trace de la tentative — c'est ce qui distingue « rien à envoyer » de
    # « l'envoi a échoué ».
    #
    # `envoye_le` ne dit que « le fournisseur a accepté ». Le refus du
    # destinataire arrive plus tard et défait ces deux marquages —
    # falkye/reconciliation.py, appelé au début du cycle suivant.

    db_session.commit()
    return summary
