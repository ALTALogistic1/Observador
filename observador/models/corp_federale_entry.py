"""Miroir local de Corporations Canada (registre fédéral, ISED), rafraîchi par
observador/sources/corporations_canada.py — même principe que REQEntry
(observador/models/req_entry.py) mais un mirroir séparé et plus léger : en
Phase 1, Corporations Canada sert de SOURCE DE SIGNAL en soi (nouvelle
incorporation active détectée par diff entre deux rafraîchissements), pas de
pivot de résolution partagé avec les autres sources — le NEQ (via REQEntry)
reste le seul pivot utilisé pour la résolution croisée en Phase 1 (spec :
"pas de changement de schéma maintenant, extension additive prévue plus tard"
— voir docs/ARCHITECTURE.md, "Généralisation du pivot d'identité")."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from observador.models.base import Base, utcnow


class CorporationFederaleEntry(Base):
    __tablename__ = "corporations_federales_entries"

    numero_corporation: Mapped[str] = mapped_column(String(20), primary_key=True)
    nom: Mapped[str] = mapped_column(String(300), nullable=False)
    statut: Mapped[str] = mapped_column(String(50), nullable=False)
    adresse: Mapped[str | None] = mapped_column(String(500), nullable=True)
    loi_constitutive: Mapped[str | None] = mapped_column(String(200), nullable=True)
    date_incorporation: Mapped[datetime | None] = mapped_column(nullable=True)

    first_seen_at: Mapped[datetime] = mapped_column(default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
