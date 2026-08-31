"""Profil utilisateur (spec section 4) et la "porte ouverte" fournisseur/client
(section 4, sous-section "Porte ouverte : profils fournisseur et client" + section 9,
"Extensibilité du type de profil").

Important : `type_profil` existe dès la Phase 1 avec ses 3 valeurs possibles, mais
SEULEMENT la mécanique fournisseur est implémentée par le moteur (observador/engine.py).
Un profil `client` ou `les_deux` peut être créé et stocké sans erreur ; la mise en
correspondance bidirectionnelle client-fournisseur n'est PAS construite en Phase 1 — le
moteur ignore simplement les profils qui ne sont pas (au moins en partie) fournisseurs.
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from observador.models.base import Base, utcnow


class TypeProfil(str, enum.Enum):
    FOURNISSEUR = "fournisseur"
    CLIENT = "client"
    LES_DEUX = "les_deux"


class Sensibilite(str, enum.Enum):
    FAIBLE = "faible"
    MOYEN = "moyen"
    ELEVE = "eleve"


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    courriel: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    nom: Mapped[str] = mapped_column(String(200), nullable=False)

    type_profil: Mapped[TypeProfil] = mapped_column(
        Enum(TypeProfil, native_enum=False), nullable=False, default=TypeProfil.FOURNISSEUR
    )

    # Localisation
    ville: Mapped[str | None] = mapped_column(String(200), nullable=True)
    region: Mapped[str | None] = mapped_column(String(200), nullable=True)
    etat_province: Mapped[str | None] = mapped_column(String(200), nullable=True)
    pays: Mapped[str] = mapped_column(String(100), nullable=False, default="Canada")
    rayon_km: Mapped[float | None] = mapped_column(Float, nullable=True)

    sensibilite: Mapped[Sensibilite] = mapped_column(
        Enum(Sensibilite, native_enum=False), nullable=False, default=Sensibilite.MOYEN
    )

    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    besoins: Mapped[list["ProfileNeed"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )

    def besoins_fournisseur(self) -> list["ProfileNeed"]:
        """Paires sphère+service actives pour la mécanique fournisseur (seule
        implémentée par le moteur en Phase 1)."""
        return [b for b in self.besoins if b.type_besoin == "offre"]


class ProfileNeed(Base):
    """Une paire sphère de besoin + service précis (section 4 : "plusieurs paires
    sphère+service possibles en parallèle", chacune scannée séparément).

    `type_besoin` distingue, pour la porte ouverte fournisseur/client :
      - "offre"   : ce que l'utilisateur offre comme fournisseur (mécanique Phase 1)
      - "besoin"  : un besoin propre à l'utilisateur en tant que client (structure
                    prévue, aucune mécanique de mise en correspondance en Phase 1)
    """

    __tablename__ = "profile_needs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), nullable=False)
    sphere_id: Mapped[str] = mapped_column(ForeignKey("spheres.id"), nullable=False)

    type_besoin: Mapped[str] = mapped_column(String(20), nullable=False, default="offre")

    # Service précis : texte libre (chaque utilisateur décrit sa spécialité avec ses
    # propres mots — ex. "implantation de systèmes d'inventaire", "courtage
    # d'assurance commerciale", "recrutement spécialisé TI" selon l'utilisateur).
    # Vide pour type_besoin="besoin". Volontairement libre plutôt qu'une liste
    # fermée (spec section 4) : le produit ne présume d'aucun secteur ou service en
    # particulier (spec section 9, "Polyvalence d'utilisation").
    service_precis: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Mots-clés/tags optionnels (texte séparé par virgules) utilisés pour la
    # correspondance qualitative avec les titres de poste (spec section 7, Signal 3).
    mots_cles: Mapped[str | None] = mapped_column(String(500), nullable=True)

    profile: Mapped[Profile] = relationship(back_populates="besoins")
    sphere = relationship("Sphere")

    def liste_mots_cles(self) -> list[str]:
        if not self.mots_cles:
            return []
        return [m.strip() for m in self.mots_cles.split(",") if m.strip()]
