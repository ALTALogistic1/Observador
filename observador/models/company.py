"""Entreprise repérée = le "dossier cumulatif par entreprise" (spec section 5).

Une ligne Company par NEQ résolu (le NEQ est le pivot de déduplication, section 9).
Toute la corroboration multi-signaux et l'historique dans le temps se lisent via
Company.signals — jamais en traitant chaque détection comme un événement isolé.
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from observador.models.base import Base, utcnow


class StatutResolution(str, enum.Enum):
    RESOLU = "resolu"              # NEQ trouvé avec confiance suffisante
    AMBIGU = "ambigu"               # plusieurs NEQ candidats, aucun retenu avec confiance
    NON_TROUVE = "non_trouve"        # aucun NEQ correspondant au REQ
    EN_ATTENTE = "en_attente"        # résolution pas encore tentée


class StatutLegal(str, enum.Enum):
    IMMATRICULEE = "immatriculee"
    RADIEE = "radiee"
    INCONNU = "inconnu"


class StatutVerification(str, enum.Enum):
    """Résultat des vérifications de base obligatoires (spec section 6).
    Un prospect qui échoue une vérification est exclu SILENCIEUSEMENT — ce statut
    sert au journal interne, jamais affiché tel quel à l'utilisateur avec un
    avertissement."""

    VERIFIE = "verifie"
    EXCLU_RADIEE = "exclu_radiee"
    EXCLU_SITE_INACTIF = "exclu_site_inactif"
    EXCLU_RESOLUTION_AMBIGUE = "exclu_resolution_ambigue"
    NON_VERIFIE = "non_verifie"  # pas encore passé par le pipeline de vérification


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    neq: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True, index=True)
    statut_resolution: Mapped[StatutResolution] = mapped_column(
        Enum(StatutResolution, native_enum=False),
        nullable=False,
        default=StatutResolution.EN_ATTENTE,
    )

    nom_detecte: Mapped[str] = mapped_column(String(300), nullable=False)
    # Nom normalisé (voir observador/sources/column_mapping.normaliser), indexé pour
    # retrouver rapidement un Company non résolu (neq IS NULL) par nom sans avoir à
    # comparer en Python contre TOUTES les entreprises non résolues à chaque signal
    # ingéré — un balayage Python complet ici serait quadratique sur le volume total.
    nom_detecte_normalise: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    nom_officiel_req: Mapped[str | None] = mapped_column(String(300), nullable=True)

    adresse: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ville: Mapped[str | None] = mapped_column(String(200), nullable=True)
    region: Mapped[str | None] = mapped_column(String(200), nullable=True)
    code_postal: Mapped[str | None] = mapped_column(String(10), nullable=True)

    secteur_activite_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    secteur_activite_libelle: Mapped[str | None] = mapped_column(String(300), nullable=True)

    statut_legal: Mapped[StatutLegal] = mapped_column(
        Enum(StatutLegal, native_enum=False), nullable=False, default=StatutLegal.INCONNU
    )

    site_web: Mapped[str | None] = mapped_column(String(500), nullable=True)
    site_web_vérifié_le: Mapped[datetime | None] = mapped_column(nullable=True)

    statut_verification: Mapped[StatutVerification] = mapped_column(
        Enum(StatutVerification, native_enum=False),
        nullable=False,
        default=StatutVerification.NON_VERIFIE,
    )

    first_detected_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    signals: Mapped[list["Signal"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    notifications: Mapped[list["Notification"]] = relationship(back_populates="company")

    def est_presentable(self) -> bool:
        """Vérifications de base obligatoires, section 6 : jamais présenté sans ça."""
        return self.statut_verification == StatutVerification.VERIFIE
