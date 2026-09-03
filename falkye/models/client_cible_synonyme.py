"""Synonyme/mot-clé associé à un client cible ("qui") — Niveau 1 de
l'assistance IA (spec section 8bis, 2026-09-03). Miroir exact de
`falkye/models/sphere_synonyme.py::SphereSynonyme` — mêmes deux origines,
même politique de resynchronisation (`falkye.db.
seed_client_cible_synonymes_from_registry`), même enrichissement silencieux
par le Niveau 2 (`falkye/assistance_client_cible_ia.py`, origine="ia_niveau2")
sur une catégorie EXISTANTE seulement, jamais la création d'une nouvelle
catégorie."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from falkye.models.base import Base, utcnow


class ClientCibleSynonyme(Base):
    __tablename__ = "client_cible_synonymes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_cible_id: Mapped[str] = mapped_column(ForeignKey("clients_cibles.id"), nullable=False)
    texte: Mapped[str] = mapped_column(String(200), nullable=False)
    origine: Mapped[str] = mapped_column(String(20), nullable=False, default="registre")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    client_cible = relationship("ClientCible")
