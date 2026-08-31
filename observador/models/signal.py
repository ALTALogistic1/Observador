"""Signal détecté (spec section 7). Un signal appartient toujours à un Company (dossier
cumulatif) et référence une source + un type de signal du registre (observador/registry)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from observador.models.base import Base, utcnow


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)

    source_id: Mapped[str] = mapped_column(String(64), nullable=False)        # voir registry/sources.yaml
    signal_type_id: Mapped[str] = mapped_column(String(64), nullable=False)   # voir registry/signal_types.yaml

    # Identifiant/URL de la ressource source, pour traçabilité et déduplication à
    # l'ingestion (éviter de recréer le même signal à chaque exécution du connecteur).
    source_ref: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)

    detected_at: Mapped[datetime] = mapped_column(nullable=False)  # date de l'évènement source
    ingested_at: Mapped[datetime] = mapped_column(default=utcnow)   # date de notre collecte

    # Valeur générique (montant $, nombre de postes, rang, etc. selon le signal) utilisée
    # par observador/scoring.py — l'unité dépend du signal_type_id, pas figée ici.
    valeur_associee: Mapped[float | None] = mapped_column(Float, nullable=True)

    titre_ou_description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Les champs pertinents complets extraits pour ce signal (voir champs_pertinents
    # dans sources.yaml), conservés intégralement pour ne rien perdre même si le
    # scoring n'en utilise qu'une partie.
    champs: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    score_signal: Mapped[float | None] = mapped_column(Float, nullable=True)
    spheres_probables: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    company: Mapped["Company"] = relationship(back_populates="signals")

    __table_args__ = ()
