"""Sous-comptes et territoires assignés, avec rôles — spec section 4bis,
fonctionnalité Radar+ "au-delà de la collaboration d'équipe simple, une
structure organisationnelle — territoire/secteur assigné par sous-compte,
permissions différenciées (admin/analyste/lecture seule)."

LIMITE HONNÊTE, À NE PAS PASSER SOUS SILENCE : ce produit n'a AUCUN système
d'authentification/de connexion (FALKYE est un outil CLI mono-opérateur en
Phase 1/2, voir README — un seul utilisateur exécute la CLI localement, aucune
notion de session ou d'identité vérifiée). Ce modèle et les commandes CLI qui
l'accompagnent (`falkye souscompte`) construisent la STRUCTURE DE DONNÉES —
territoire assigné, rôle — mais ne peuvent PAS réellement authentifier "cet
appel CLI est fait par CE sous-compte précis" : `--sous-compte-id` est un
paramètre déclaratif, pas une preuve d'identité. La vérification de rôle
(falkye/cli.py::dashboard_statut) filtre donc un usage de bonne foi (éviter
qu'un script automatisé écrivant "au nom" d'un sous-compte lecture-seule ne le
fasse par erreur), **JAMAIS une frontière de sécurité contre un utilisateur
malveillant qui contrôle déjà la CLI — cette phrase reste vraie et ne doit
JAMAIS être présentée autrement dans le produit ou le matériel de vente,
quelle que soit l'urgence commerciale ci-dessous.**

CLARIFICATION D'ALEXANDRE (2026-09-02), URGENCE RÉVISÉE À LA BAISSE : le vrai
besoin identifié chez les personas Radar+ réels (développement économique
régional, cabinets multi-agents) est la RÉPARTITION DE VOLUME entre collègues
d'une même organisation (distribuer automatiquement les bonnes notifications
à la bonne personne selon son secteur/territoire assigné, pour réduire le
bruit) — PAS l'étanchéité de sécurité entre organisations ou contre un
collègue malveillant de la même organisation. Une authentification réelle par
utilisateur reste un vrai prérequis à construire avant de présenter les rôles
comme une séparation STRICTE, mais n'est PLUS un bloqueur au premier client
payant Radar+ : le produit peut être vendu et utilisé pour la répartition de
volume dès maintenant, tant qu'il ne prétend jamais être une frontière de
sécurité."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from falkye.models.base import Base, utcnow


class RoleSousCompte(str, enum.Enum):
    ADMIN = "admin"
    ANALYSTE = "analyste"
    LECTURE_SEULE = "lecture_seule"


class SousCompte(Base):
    __tablename__ = "sous_comptes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), nullable=False)  # compte Radar+ parent

    courriel: Mapped[str] = mapped_column(String(320), nullable=False)
    nom: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[RoleSousCompte] = mapped_column(
        Enum(RoleSousCompte, native_enum=False), nullable=False, default=RoleSousCompte.ANALYSTE
    )

    # Territoire/secteur assigné (spec) — texte libre, même principe que
    # ProfileNeed.usage_precis/territoire : ne présume d'aucun découpage
    # géographique particulier. Comparé à Company.region/ville par
    # correspondance simple (falkye/cli.py::dashboard_voir), pas une
    # hiérarchie territoriale formelle.
    territoire: Mapped[str | None] = mapped_column(String(200), nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    profile = relationship("Profile")
