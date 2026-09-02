"""Application d'un changement de statut de suivi — factorisé pour être partagé
entre le tableau de bord (falkye/cli.py::dashboard_statut, origine humaine) et le
sondage retour CRM (falkye/crm_sync.py::sonder_statuts_crm, origine CRM, ajouté
le 2026-09-02) : la même règle de rétroaction de pertinence (spec section 4bis)
doit s'appliquer peu importe QUI a déclenché le changement de statut."""
from __future__ import annotations

from sqlalchemy.orm import Session

from falkye.models.notification import Notification
from falkye.registry.loader import Registry
from falkye.retroaction import enregistrer_pas_pertinent


def appliquer_statut(db_session: Session, notification: Notification, statut_id: str, registry: Registry) -> bool:
    """Change le statut de suivi d'une notification et déclenche la rétroaction
    de pertinence si ce statut est marqué `declenche_retroaction` au registre
    (ex. "Pas pertinent"). Retourne True si la rétroaction a été appliquée (pour
    l'affichage), False sinon.

    Ne valide PAS que `statut_id` existe (l'appelant décide comment réagir à un
    id inconnu — une ClickException en CLI, un id ignoré silencieusement pour
    un sondage automatisé) et ne commit PAS (laisse l'appelant gérer sa
    transaction — le sondage CRM traite plusieurs enregistrements dans une
    seule transaction)."""
    notification.statut_suivi_id = statut_id
    statut_def = registry.statut_suivi(statut_id)
    if statut_def is not None and statut_def.declenche_retroaction:
        enregistrer_pas_pertinent(db_session, notification)
        return True
    return False
