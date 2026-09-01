"""Miroir local des licences d'affaires municipales (Vancouver, Toronto — spec
section 7, Signal registre_corporatif), rafraîchi par
falkye/sources/licences_municipales_communes.py et les connecteurs par
ville (ex. falkye/sources/licences_vancouver.py).

Nécessaire pour la règle de calibration "NON NÉGOCIABLE" du registre (voir
sources.yaml:licences_affaires_municipales) : une licence ne doit produire un
signal QUE si elle représente un NOUVEL établissement, jamais un simple
renouvellement annuel. Les jeux de données municipaux réels (confirmé pour
Vancouver, 2026-09-01) attribuent un NOUVEAU numéro de licence CHAQUE ANNÉE
(le folderyear est encodé dans le numéro lui-même) et ne remontent que sur
une fenêtre glissante de quelques années — impossible de distinguer
"nouveau" de "renouvellement" à partir d'un seul instantané. Ce miroir
accumule donc les entreprises+adresses déjà vues d'un scan à l'autre, même
principe que REQEntry/CorporationFederaleEntry pour leurs propres signaux de
diff (nouvel établissement / changement d'adresse).

Clé = (municipalite, nom_normalise, adresse_normalisee) — PAS le numéro de
licence municipal (instable d'une année à l'autre) : une entreprise qui
ouvre une DEUXIÈME adresse dans la même ville est un nouvel établissement
légitime même si son nom est déjà connu (même logique que le REQ : nouvel
établissement secondaire d'une entreprise déjà connue = signal)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from falkye.models.base import Base, utcnow


class LicenceMunicipaleEntry(Base):
    __tablename__ = "licences_municipales_entries"
    __table_args__ = (UniqueConstraint("municipalite", "cle_entreprise", name="uq_licence_municipale"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    municipalite: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    cle_entreprise: Mapped[str] = mapped_column(String(600), nullable=False)  # nom_normalise + "|" + adresse_normalisee

    nom: Mapped[str] = mapped_column(String(300), nullable=False)
    adresse: Mapped[str | None] = mapped_column(String(500), nullable=True)
    type_entreprise: Mapped[str | None] = mapped_column(String(200), nullable=True)

    first_seen_at: Mapped[datetime] = mapped_column(default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
