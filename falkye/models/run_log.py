"""Journal d'exécution par source — visibilité opérationnelle sur le moteur qui boucle
sur les sources actives (spec section 9)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from falkye.models.base import Base, utcnow


class SourceRunLog(Base):
    __tablename__ = "source_run_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False)
    mode: Mapped[str] = mapped_column(String(30), nullable=False)  # veille_continue | recherche_ponctuelle
    started_at: Mapped[datetime] = mapped_column(default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    statut: Mapped[str] = mapped_column(String(20), nullable=False, default="en_cours")
    nb_signaux_detectes: Mapped[int] = mapped_column(Integer, default=0)
    nb_entreprises_nouvelles: Mapped[int] = mapped_column(Integer, default=0)
    erreur: Mapped[str | None] = mapped_column(Text, nullable=True)
