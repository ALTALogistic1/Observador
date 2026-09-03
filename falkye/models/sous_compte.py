"""Sous-comptes et territoires assignés, avec rôles — spec section 4bis,
fonctionnalité Radar+ "au-delà de la collaboration d'équipe simple, une
structure organisationnelle — territoire/secteur assigné par sous-compte,
permissions différenciées (admin/analyste/lecture seule)."

CORRIGÉ le 2026-09-02 (falkye/auth.py) : la limite honnête documentée ici
depuis la construction de ce modèle — "`--sous-compte-id` est un paramètre
déclaratif, pas une preuve d'identité" — ne tient plus. `mot_de_passe_hash`
(ci-dessous) + falkye/auth.py (authentification par mot de passe + session,
CLI `falkye auth login`) permettent maintenant de PROUVER "cet appel CLI est
fait par CE sous-compte précis", pas seulement de le déclarer. La vérification
de rôle (falkye/cli.py, via `_identite_courante`) s'appuie désormais sur une
identité VÉRIFIÉE (session résolue côté serveur), pas un entier passé en
paramètre.

RESTE UNE LIMITE HONNÊTE, DÉLIBÉRÉE : un "mode opérateur"
(`FALKYE_OPERATOR=1`, voir falkye/auth.py) contourne intentionnellement cette
vérification pour Alexandre — FALKYE reste un outil dont TOUTES les données
transitent par un seul opérateur technique (Alexandre), qui doit pouvoir
dépanner/administrer n'importe quel profil sans se connecter comme chacun de
ses clients. Ce mode est un choix architectural documenté, pas une faille
oubliée — mais il veut dire que la frontière réelle protège les sous-comptes
LES UNS DES AUTRES (et d'un tiers qui n'a pas de session valide), jamais
contre Alexandre lui-même, qui a accès à la base de données sous-jacente par
construction. Cette nuance doit être présentée honnêtement, pas glissée sous
silence, si jamais évoquée dans le matériel de vente.

Autre limite honnête, distincte : l'authentification prouve qui a exécuté une
commande CLI, pas qui l'a physiquement TAPÉE sur un clavier — un sous-compte
qui partage son mot de passe reste indétectable, comme pour tout système
d'authentification par mot de passe. Pas une faiblesse propre à FALKYE."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from falkye.models.base import Base, utcnow


class RoleSousCompte(str, enum.Enum):
    ADMIN = "admin"
    ANALYSTE = "analyste"
    LECTURE_SEULE = "lecture_seule"


class SousCompte(Base):
    __tablename__ = "sous_comptes"
    __table_args__ = (UniqueConstraint("courriel", name="uq_sous_compte_courriel"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), nullable=False)  # compte Radar+ parent

    # Unique globalement (pas seulement par profil) — nécessaire pour que
    # falkye/auth.py::authentifier puisse résoudre un courriel de connexion
    # vers UN SEUL principal sans ambiguïté (voir Profile.courriel, déjà
    # unique depuis la Phase 1 pour la même raison).
    courriel: Mapped[str] = mapped_column(String(320), nullable=False)
    nom: Mapped[str] = mapped_column(String(200), nullable=False)

    # Authentification réelle (falkye/auth.py, ajoutée le 2026-09-02) — jamais
    # le mot de passe en clair, jamais fabriqué : NULL tant que personne n'a
    # défini de mot de passe pour ce sous-compte (`falkye auth
    # definir-mot-de-passe`, mode opérateur — bootstrap nécessaire, un
    # sous-compte ne peut pas prouver son identité AVANT d'avoir un mot de
    # passe). Un sous-compte sans mot de passe ne peut simplement pas se
    # connecter — pas une erreur, l'état de départ normal.
    mot_de_passe_hash: Mapped[str | None] = mapped_column(String(200), nullable=True)
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
