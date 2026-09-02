"""Résolution de la pondération de pertinence par profil — spec section 4bis,
Radar+ "pondération du moteur de score personnalisable". Réservé au plan
RADAR_PLUS (même principe de gate qu'ailleurs dans cette fonctionnalité : le
stockage n'est pas ce qui gate l'accès, la vérification de plan au moment de
l'USAGE l'est — voir falkye/notifications/webhook_channel.py pour le même
principe appliqué au webhook)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from falkye.models.ponderation_personnalisee import PonderationPersonnalisee
from falkye.models.profile import PlanTarifaire, Profile
from falkye.pertinence import PONDERATION_DEFAUT, PonderationValeurs


def ponderation_pour_profil(db_session: Session, profile: Profile) -> PonderationValeurs:
    """PONDERATION_DEFAUT pour Écho/Radar, ou pour un Radar+ sans pondération
    personnalisée enregistrée. Pour un Radar+ avec une ligne enregistrée, chaque
    champ NULL retombe individuellement sur sa valeur par défaut (voir docstring
    de PonderationPersonnalisee) — un profil peut n'ajuster qu'UN seul facteur."""
    if profile.plan != PlanTarifaire.RADAR_PLUS:
        return PONDERATION_DEFAUT

    ligne = db_session.execute(
        select(PonderationPersonnalisee).where(PonderationPersonnalisee.profile_id == profile.id)
    ).scalar_one_or_none()
    if ligne is None:
        return PONDERATION_DEFAUT

    return PonderationValeurs(
        base_a=ligne.base_a if ligne.base_a is not None else PONDERATION_DEFAUT.base_a,
        base_aa=ligne.base_aa if ligne.base_aa is not None else PONDERATION_DEFAUT.base_aa,
        base_aaa=ligne.base_aaa if ligne.base_aaa is not None else PONDERATION_DEFAUT.base_aaa,
        bonus_absence=ligne.bonus_absence if ligne.bonus_absence is not None else PONDERATION_DEFAUT.bonus_absence,
        bonus_velocite_max=(
            ligne.bonus_velocite_max
            if ligne.bonus_velocite_max is not None
            else PONDERATION_DEFAUT.bonus_velocite_max
        ),
        bonus_velocite_par_signal=(
            ligne.bonus_velocite_par_signal
            if ligne.bonus_velocite_par_signal is not None
            else PONDERATION_DEFAUT.bonus_velocite_par_signal
        ),
    )
