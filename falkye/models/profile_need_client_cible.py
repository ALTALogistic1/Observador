"""Lien besoin↔client cible ("qui"), pondéré, plusieurs-à-plusieurs — miroir
structurel de `falkye/models/profile_need_sphere.py::ProfileNeedSphere`, spec
section 8bis (2026-09-03).

Une ligne pointant vers `ClientCible.id == "aucune_restriction"` (voir
falkye/models/client_cible.py) représente une déclaration EXPLICITE
"s'applique largement" — distincte de l'absence totale de ligne pour ce
besoin (qui veut dire "qui" pas encore configuré, pas "aucune restriction").
Une entrée `aucune_restriction` se suffit normalement à elle-même (poids 100,
seule ligne) plutôt que d'être combinée à d'autres catégories."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from falkye.models.base import Base, utcnow


class ProfileNeedClientCible(Base):
    __tablename__ = "profile_need_clients_cibles"
    __table_args__ = (
        UniqueConstraint("profile_need_id", "client_cible_id", name="uq_profile_need_client_cible"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_need_id: Mapped[int] = mapped_column(ForeignKey("profile_needs.id"), nullable=False)
    client_cible_id: Mapped[str] = mapped_column(ForeignKey("clients_cibles.id"), nullable=False)
    poids: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    profile_need = relationship("ProfileNeed", back_populates="clients_cibles_lies")
    client_cible = relationship("ClientCible")
