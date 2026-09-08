"""Entreprise repérée = le "dossier cumulatif par entreprise" (spec section 5).

Une ligne Company par NEQ résolu (le NEQ est le pivot de déduplication, section 9).
Toute la corroboration multi-signaux et l'historique dans le temps se lisent via
Company.signals — jamais en traitant chaque détection comme un événement isolé.
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Enum, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from falkye.models.base import Base, utcnow


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

    # **L'index composite (neq, nom_detecte_normalise) n'est pas un raffinement,
    # c'est ce qui borne le coût de la résolution.** Mesuré le 2026-09-08 sur la
    # base réelle (11 556 entreprises, dont 8 395 sans NEQ), par `rows_read` du
    # protocole Hrana :
    #
    #     neq = ?                                      →       0 ligne lue
    #     neq IS NULL AND nom_normalise = ?            →   8 396 lignes lues
    #     neq IS NULL AND nom_normalise GLOB 'préfixe*' →   8 396 lignes lues
    #
    # Pourquoi l'index simple sur `nom_detecte_normalise` n'y suffisait pas.
    # `ix_companies_neq` est UNIQUE, donc SQLite estime que `neq = ?` rend UNE
    # ligne — mais un index unique accepte autant de NULL qu'on veut, et il y en
    # a 8 395. Le planificateur choisit donc l'index qu'il croit parfait, et lit
    # toute la population non résolue. Le prédicat ajouté pour la justesse
    # annulait l'optimisation GLOB documentée dans falkye/sources/req.py.
    # `EXPLAIN QUERY PLAN` le dit mot pour mot :
    #
    #     avec neq IS NULL   → SEARCH USING INDEX ix_companies_neq (neq=?)
    #     sans neq IS NULL   → SEARCH USING COVERING INDEX ix_companies_nom_…
    #
    # Avec l'index composite, les deux requêtes chères passent en recherche par
    # PLAGE dans un index couvrant. Un index PARTIEL (`WHERE neq IS NULL`) a été
    # essayé d'abord : il corrige l'égalité, pas le GLOB — le planificateur reste
    # sur `ix_companies_neq`. Vérifié sur réplique locale de même population.
    #
    # Ce que ça coûtait : ~16 800 lignes lues par signal neuf non résolu, soit le
    # quota mensuel de lectures consommé par ~600 signaux. Trois passages de
    # l'EIMT (23 142 signaux chacun) l'ont épuisé le 2026-09-08.
    #
    # L'index simple ci-dessous devient redondant — les TROIS requêtes du code
    # portent `neq IS NULL`. Il est conservé par défaut (le retirer est un geste
    # séparé, `outils/migration_index_neq_nom.py --retirer-index-redondant`) :
    # il ne coûte que du poids en écriture, et le retirer d'office ferait diverger
    # une base migrée d'une base neuve.
    __table_args__ = (Index("ix_companies_neq_nom_normalise", "neq", "nom_detecte_normalise"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    neq: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True, index=True)
    statut_resolution: Mapped[StatutResolution] = mapped_column(
        Enum(StatutResolution, native_enum=False),
        nullable=False,
        default=StatutResolution.EN_ATTENTE,
    )

    nom_detecte: Mapped[str] = mapped_column(String(300), nullable=False)
    # Nom normalisé (voir falkye/sources/column_mapping.normaliser), indexé pour
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

    # Coordonnées trouvées via l'enrichissement contextuel (spec section 10) —
    # déjà extraites par falkye/enrichment.py (EnrichmentResult.coordonnees) mais
    # jamais persistées avant le tableau de bord (spec section 4bis, "le lien vers
    # le site web du prospect ET les coordonnées trouvées via l'enrichissement
    # contextuel") : simple complétion d'une capture de donnée déjà faite, pas une
    # nouvelle source. Nullable — beaucoup de sites n'exposent ni l'un ni l'autre,
    # jamais une valeur inventée pour combler l'absence (principe directeur #1).
    telephone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    courriel_contact: Mapped[str | None] = mapped_column(String(320), nullable=True)

    # Géocodage pour la carte géographique interactive (spec section 4bis, voir
    # falkye/geocoding.py) — géocode_tente_le distingue "jamais tenté" de "tenté,
    # aucune correspondance trouvée" (même principe de cache que
    # site_web_vérifié_le ci-dessus), pour ne jamais refaire un appel réseau
    # inutile à chaque génération de carte.
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    geocode_tente_le: Mapped[datetime | None] = mapped_column(nullable=True)

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
