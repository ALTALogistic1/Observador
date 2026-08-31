"""Sphère de besoin (spec section 4).

Table alimentée au démarrage à partir de observador/registry/spheres.yaml
(voir db.seed_spheres_from_registry), et extensible en cours d'usage : un
utilisateur qui ne se reconnaît dans aucune sphère existante peut en proposer
une nouvelle (est_personnalisee=True) sans casser la structure ni nécessiter
de migration.
"""
from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from observador.models.base import Base


class Sphere(Base):
    __tablename__ = "spheres"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    nom: Mapped[str] = mapped_column(String(200), nullable=False)
    est_personnalisee: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    proposee_par: Mapped[str | None] = mapped_column(String(200), nullable=True)
