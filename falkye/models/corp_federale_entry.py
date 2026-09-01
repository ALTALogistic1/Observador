"""Miroir local de Corporations Canada (registre fédéral, ISED), rafraîchi par
falkye/sources/corporations_canada.py — même principe que REQEntry
(falkye/models/req_entry.py) mais un mirroir séparé et plus léger.

Rôle : Corporations Canada sert de SOURCE DE SIGNAL en soi (changement
d'adresse détecté par diff entre deux rafraîchissements — voir
corporations_canada.py). Le NEQ (via REQEntry) reste le seul pivot de
RÉSOLUTION DE Company (spec : "pas de changement de schéma maintenant,
extension additive prévue plus tard" — voir docs/ARCHITECTURE.md,
"Généralisation du pivot d'identité") — ceci n'a PAS changé.

Ce qui s'ajoute (2026-09-01, activation de licences_affaires_municipales) :
`nom_normalise` (indexé), pour une recherche par nom — PAS un nouveau pivot
de résolution de Company, mais une vérification croisée plus étroite et
autonome : `resolve_corp_federale_by_name` (dans corporations_canada.py)
sert de PORTE (calibration, spec section 7, "Principe de calibration") pour
les sources hors Québec qui n'ont pas de nom de demandeur fiable côté REQ —
confirmer qu'un nom détecté correspond à une corporation fédérale déjà
EXISTANTE avant de produire un signal, jamais pour créer/résoudre un
Company. Même discipline GLOB (pas LIKE) que REQEntry.nom_normalise — voir
req.py:resolve_neq_by_name pour l'explication complète du choix."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from falkye.models.base import Base, utcnow


class CorporationFederaleEntry(Base):
    __tablename__ = "corporations_federales_entries"

    numero_corporation: Mapped[str] = mapped_column(String(20), primary_key=True)
    nom: Mapped[str] = mapped_column(String(300), nullable=False)
    nom_normalise: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    statut: Mapped[str] = mapped_column(String(50), nullable=False)
    adresse: Mapped[str | None] = mapped_column(String(500), nullable=True)
    province: Mapped[str | None] = mapped_column(String(50), nullable=True)
    loi_constitutive: Mapped[str | None] = mapped_column(String(200), nullable=True)
    date_incorporation: Mapped[datetime | None] = mapped_column(nullable=True)

    first_seen_at: Mapped[datetime] = mapped_column(default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
