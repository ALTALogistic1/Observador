"""Résumé périodique — spec section 5, "en complément des notifications
individuelles" (ne les remplace pas, les deux formats coexistent)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from falkye.models.notification import Notification, PeriodicSummary
from falkye.models.profile import Profile
from falkye.notifications.base import NotificationContent
from falkye.registry.loader import Registry, get_registry

_NIVEAU_AFFICHAGE = {"faible": "Faible", "moyen": "Moyen", "eleve": "Élevé"}


def generer_resume(
    db_session: Session, profile: Profile, periode_debut: datetime, periode_fin: datetime
) -> tuple[PeriodicSummary, list[Notification]]:
    notifications = (
        db_session.execute(
            select(Notification).where(
                Notification.profile_id == profile.id,
                Notification.created_at >= periode_debut,
                Notification.created_at < periode_fin,
            )
        )
        .scalars()
        .all()
    )

    summary = PeriodicSummary(
        profile_id=profile.id,
        periode_debut=periode_debut,
        periode_fin=periode_fin,
        notification_ids=[n.id for n in notifications],
    )
    db_session.add(summary)
    for n in notifications:
        n.inclus_dans_resume = True
    db_session.flush()
    return summary, notifications


def formatter_resume(
    summary: PeriodicSummary, notifications: list[Notification], registry: Registry | None = None
) -> NotificationContent:
    registry = registry or get_registry()

    if not notifications:
        corps = "Aucune nouvelle entreprise repérée durant cette période."
    else:
        lignes = []
        for n in sorted(notifications, key=lambda n: n.score_confiance, reverse=True):
            nom = n.company.nom_officiel_req or n.company.nom_detecte
            niveau = _NIVEAU_AFFICHAGE[n.niveau.value]
            lignes.append(f"  • {nom} — confiance {niveau} ({n.score_confiance}/100)")
        corps = f"{len(notifications)} entreprise(s) repérée(s) durant cette période :\n\n" + "\n".join(lignes)

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

    for channel_def in registry.canaux_actifs():
        channel = channel_def.charger_canal()
        if channel is None:
            continue
        result = channel.envoyer(profile.courriel, contenu)
        if result.succes and channel_def.id == "email":
            summary.envoye_le = datetime.now(timezone.utc)

    db_session.commit()
    return summary
