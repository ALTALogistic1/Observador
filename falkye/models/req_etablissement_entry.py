"""Miroir local des ÉTABLISSEMENTS du REQ (Etablissements.csv du fichier en vrac
réel — voir falkye/sources/req.py et docs/STATUT_RESEAU.md, découverte du
2026-08-31).

Distinct de REQEntry (une ligne par ENTREPRISE/NEQ) : une entreprise peut avoir
PLUSIEURS établissements (un siège + des établissements secondaires), chacun avec
sa propre adresse. Ce miroir existe pour UNE SEULE raison — détecter, par diff
entre deux imports, l'apparition d'un NOUVEL établissement SECONDAIRE chez une
entreprise déjà connue (spec section 7, Signal 4 : "nouvel établissement
secondaire = fort"), un signal distinct du changement d'adresse du siège
(REQEntry.adresse, "moyen") et qui ne peut pas être détecté avec un miroir à une
seule ligne par NEQ.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from falkye.models.base import Base, utcnow


class REQEtablissementEntry(Base):
    __tablename__ = "req_etablissements"

    neq: Mapped[str] = mapped_column(String(20), primary_key=True)
    no_suf_etab: Mapped[str] = mapped_column(String(10), primary_key=True)

    principal: Mapped[bool] = mapped_column(default=False)
    adresse: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ville: Mapped[str | None] = mapped_column(String(200), nullable=True)
    code_postal: Mapped[str | None] = mapped_column(String(10), nullable=True)
    secteur_libelle: Mapped[str | None] = mapped_column(String(300), nullable=True)
    nom_etablissement: Mapped[str | None] = mapped_column(String(300), nullable=True)

    first_seen_at: Mapped[datetime] = mapped_column(default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
