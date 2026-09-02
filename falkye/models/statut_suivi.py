"""Statut de suivi du tableau de bord (spec section 4bis, ajoutée le 2026-09-02,
"Tableau de bord et statut de suivi — Radar et Radar+ seulement").

Table alimentée au démarrage à partir de falkye/registry/statuts_suivi.yaml (voir
db.seed_statuts_suivi_from_registry), et extensible en cours d'usage — même
principe que falkye/models/sphere.py::Sphere : un statut qui n'existe pas peut
être ajouté (est_personnalise=True) sans casser la structure ni nécessiter de
migration (spec : "un statut n'existant pas doit pouvoir être ajouté sans
restructuration")."""
from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from falkye.models.base import Base


class StatutSuivi(Base):
    __tablename__ = "statuts_suivi"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    nom: Mapped[str] = mapped_column(String(200), nullable=False)
    est_personnalise: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    proposee_par: Mapped[str | None] = mapped_column(String(200), nullable=True)
