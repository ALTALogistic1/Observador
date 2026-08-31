"""Miroir local du Registre des entreprises du Québec (REQ), rafraîchi depuis les
données ouvertes (observador/sources/req.py).

Sert de DEUX façons distinctes (spec section 7 et 9) :
  1. Index de résolution nom -> NEQ pour TOUTES les sources (le NEQ n'apparaît pas
     directement dans SEAO/RDPRM/Guichet-Emplois — seul le REQ le fournit à partir
     d'un nom d'entreprise). C'est le "pivot" décrit en section 9.
  2. Base de diff pour détecter les signaux propres au REQ (nouvel établissement,
     changement d'adresse) en comparant deux rafraîchissements successifs — voir
     observador/sources/req.py:detect().

Ce n'est PAS le dossier cumulatif d'une entreprise (voir Company) : une ligne existe
ici pour CHAQUE entreprise du registre, détectée par une autre source ou non. Une
Company n'est créée qu'une fois qu'une entreprise est effectivement repérée par un
signal.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from observador.models.base import Base, utcnow


class REQEntry(Base):
    __tablename__ = "req_entries"

    neq: Mapped[str] = mapped_column(String(20), primary_key=True)
    nom: Mapped[str] = mapped_column(String(300), nullable=False)
    nom_normalise: Mapped[str] = mapped_column(String(300), nullable=False, index=True)

    adresse: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ville: Mapped[str | None] = mapped_column(String(200), nullable=True)
    region: Mapped[str | None] = mapped_column(String(200), nullable=True)
    code_postal: Mapped[str | None] = mapped_column(String(10), nullable=True)

    secteur_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    secteur_libelle: Mapped[str | None] = mapped_column(String(300), nullable=True)

    statut: Mapped[str] = mapped_column(String(30), nullable=False)  # immatriculee | radiee
    date_maj_req: Mapped[datetime | None] = mapped_column(nullable=True)

    first_seen_at: Mapped[datetime] = mapped_column(default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    __table_args__ = (Index("ix_req_entries_nom_normalise_prefix", "nom_normalise"),)
