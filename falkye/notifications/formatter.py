"""Construit le contenu d'une notification consolidée (spec section 6, restructurée) :
DEUX axes indépendants affichés — confiance (Faible/Moyen/Élevé) et pertinence
(A/AA/AAA) — jamais fusionnés en un seul chiffre, plus chaque signal contributif
listé avec sa source et sa justification propre."""
from __future__ import annotations

from falkye.models.notification import Notification
from falkye.notifications.base import NotificationContent
from falkye.registry.loader import Registry

_NIVEAU_AFFICHAGE = {"faible": "Faible", "moyen": "Moyen", "eleve": "Élevé"}


def formatter_notification(notification: Notification, registry: Registry) -> NotificationContent:
    company = notification.company
    nom = company.nom_officiel_req or company.nom_detecte
    niveau_txt = _NIVEAU_AFFICHAGE[notification.niveau_confiance.value]
    # Notifications antérieures au 2026-09-01 (avant la restructuration en deux
    # axes) n'ont pas de pertinence calculée — affichée comme "non disponible"
    # plutôt qu'une valeur inventée pour combler l'historique.
    pertinence_txt = notification.niveau_pertinence.value if notification.niveau_pertinence else "non disponible"

    sphere_txt = ""
    if notification.sphere_probable_id:
        sphere = registry.sphere(notification.sphere_probable_id)
        if sphere:
            sphere_txt = f"Sphère de besoin probable : {sphere.nom}\n"

    lignes_signaux = []
    for ns in notification.signaux_contributifs:
        signal = ns.signal
        source = registry.sources.get(signal.source_id)
        source_nom = source.nom if source else signal.source_id
        lignes_signaux.append(f"  • [{source_nom}] {ns.justification}")

    corps_texte = (
        f"Entreprise repérée : {nom}\n"
        f"Niveau de confiance : {niveau_txt} (score {notification.score_confiance}/100)\n"
        f"Niveau de pertinence : {pertinence_txt}\n"
        f"{sphere_txt}"
        f"\nSignaux ayant contribué à ce repérage :\n" + "\n".join(lignes_signaux) + "\n\n"
        f"Adresse : {company.adresse or 'non disponible'}"
        + (f", {company.ville}" if company.ville else "")
        + "\n"
        f"NEQ : {company.neq or 'non résolu'}\n"
        + (f"Site web : {company.site_web}\n" if company.site_web else "")
        + f"\n{notification.justification_resumee}\n"
    )

    sujet = f"[FALKYE] {nom} — confiance {niveau_txt} / pertinence {pertinence_txt}"

    return NotificationContent(sujet=sujet, corps_texte=corps_texte)
