"""Pondération personnalisée du moteur de score de pertinence — spec section
4bis, fonctionnalité Radar+ "pondération du moteur de score personnalisable" :
"l'utilisateur Radar+ ajuste lui-même les poids relatifs des facteurs de
pertinence (sphère, vélocité, mots-clés) selon sa propre méthodologie interne."

Une ligne par profil (au plus), tous les champs nullables : NULL = "utilise la
valeur par défaut de FALKYE pour ce facteur précis" (falkye/pertinence.py::
PONDERATION_DEFAUT), pas une valeur inventée — un profil Radar+ peut ajuster UN
SEUL facteur (ex. seulement bonus_velocite_max) sans devoir redéfinir les
autres. Voir falkye/ponderation.py::ponderation_pour_profil pour la résolution
NULL -> défaut."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from falkye.models.base import Base, utcnow


class PonderationPersonnalisee(Base):
    __tablename__ = "ponderations_personnalisees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), nullable=False, unique=True)

    # Miroir de falkye/pertinence.py::PonderationValeurs — voir PONDERATION_DEFAUT
    # pour les valeurs par défaut appliquées quand un champ est NULL ici.
    base_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    base_aa: Mapped[float | None] = mapped_column(Float, nullable=True)
    base_aaa: Mapped[float | None] = mapped_column(Float, nullable=True)
    bonus_absence: Mapped[float | None] = mapped_column(Float, nullable=True)
    bonus_velocite_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    bonus_velocite_par_signal: Mapped[float | None] = mapped_column(Float, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    profile = relationship("Profile")
