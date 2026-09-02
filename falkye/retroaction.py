"""Rétroaction de pertinence — spec section 4bis, "un statut 'Pas pertinent' sert
une double fonction... signal de rétroaction pour le moteur de pertinence : quand
un prospect est marqué ainsi, le système doit légèrement réduire le poids des
mots-clés/sphères qui ont produit sa correspondance pour les prochaines
notifications de cet utilisateur. Règle simple, pas de ML."

Granularité SPHÈRE — voir falkye/models/retroaction_pertinence.py pour la
décision documentée. Règle simple et bornée, pas de ML : chaque marquage réduit
le poids d'un pas fixe, jamais en dessous d'un plancher (une sphère ne devient
jamais complètement invisible — "légèrement réduire", pas supprimer)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from falkye.models.notification import Notification
from falkye.models.retroaction_pertinence import RetroactionPertinence

# Réduction par marquage "Pas pertinent" — pas fixe, pas proportionnel (même
# philosophie que falkye/pertinence.py:BONUS_ABSENCE_SIGNAL_ATTENDU, un bonus
# fixe plutôt qu'une granularité non justifiée par l'usage réel).
PAS_REDUCTION = 0.15
POIDS_PLANCHER = 0.4
POIDS_PAR_DEFAUT = 1.0


def poids_pour_sphere(db_session: Session, profile_id: int, sphere_id: str) -> float:
    """Poids courant (0.4 à 1.0) à appliquer au score de pertinence de base pour
    cette sphère, pour ce profil — 1.0 (aucune réduction) si aucune rétroaction
    n'a encore été enregistrée."""
    ligne = db_session.execute(
        select(RetroactionPertinence).where(
            RetroactionPertinence.profile_id == profile_id,
            RetroactionPertinence.sphere_id == sphere_id,
        )
    ).scalar_one_or_none()
    return ligne.poids if ligne is not None else POIDS_PAR_DEFAUT


def enregistrer_pas_pertinent(db_session: Session, notification: Notification) -> None:
    """Applique la rétroaction d'UNE notification marquée "Pas pertinent" — réduit
    le poids de sa sphère probable pour ce profil. Silencieux (ne lève pas) si la
    notification n'a pas de sphère probable (ex. notification antérieure au
    système de pertinence, sphere_probable_id NULL) : rien à quoi rattacher la
    rétroaction, pas une erreur."""
    if not notification.sphere_probable_id:
        return

    ligne = db_session.execute(
        select(RetroactionPertinence).where(
            RetroactionPertinence.profile_id == notification.profile_id,
            RetroactionPertinence.sphere_id == notification.sphere_probable_id,
        )
    ).scalar_one_or_none()

    if ligne is None:
        ligne = RetroactionPertinence(
            profile_id=notification.profile_id,
            sphere_id=notification.sphere_probable_id,
            poids=POIDS_PAR_DEFAUT,
            compte_marques_pas_pertinent=0,
        )
        db_session.add(ligne)

    ligne.compte_marques_pas_pertinent += 1
    ligne.poids = max(POIDS_PLANCHER, ligne.poids - PAS_REDUCTION)
