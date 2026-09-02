"""Profil utilisateur (spec section 4) et la "porte ouverte" fournisseur/client
(section 4, sous-section "Porte ouverte : profils fournisseur et client" + section 9,
"Extensibilité du type de profil").

Important : `type_profil` existe dès la Phase 1 avec ses 3 valeurs possibles, mais
SEULEMENT la mécanique fournisseur est implémentée par le moteur (falkye/engine.py).
Un profil `client` ou `les_deux` peut être créé et stocké sans erreur ; la mise en
correspondance bidirectionnelle client-fournisseur n'est PAS construite en Phase 1 — le
moteur ignore simplement les profils qui ne sont pas (au moins en partie) fournisseurs.
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from falkye.models.base import Base, utcnow


class TypeProfil(str, enum.Enum):
    FOURNISSEUR = "fournisseur"
    CLIENT = "client"
    LES_DEUX = "les_deux"


class Sensibilite(str, enum.Enum):
    FAIBLE = "faible"
    MOYEN = "moyen"
    ELEVE = "eleve"


class PlanTarifaire(str, enum.Enum):
    """Structure à trois plans (spec section 9bis, 2026-09-02) — un seul portail de
    sources payantes sous-jacent (falkye/registry/loader.py::SourceDef.
    plan_minimum), deux couches par-dessus :
      - ÉCHO : sources gratuites uniquement (le registre au grand complet à ce jour).
      - RADAR : Écho + sous-ensemble de sources payantes choisies par nous, paiement
        intégré (falkye/billing/stripe_client.py) — nous payons et gérons l'accès.
      - RADAR_PLUS : Radar + n'importe quelle source payante externe déjà possédée
        par l'utilisateur, via ses propres clés API. Valeur acceptée dès maintenant
        (porte ouverte au niveau du modèle/registre, comme TypeProfil dès la Phase 1)
        mais le mécanisme de gestion de clés utilisateur n'est PAS construit tant que
        Radar n'a pas été validé avec un premier cas payant réel (décision
        d'Alexandre, 2026-09-02) — voir docs/STATUT_RESEAU.md."""

    ECHO = "echo"
    RADAR = "radar"
    RADAR_PLUS = "radar_plus"


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

    # Deux curseurs INDÉPENDANTS (spec section 6, restructurée) : confiance (le
    # signal est-il réel et fort) et pertinence (correspond-il au profil précis de
    # cet utilisateur) sont deux axes distincts, chacun avec son propre seuil —
    # "montre-moi seulement AA et AAA, peu importe la confiance" doit être
    # exprimable sans forcer un compromis sur l'autre axe. Un seul curseur combiné
    # empêcherait ça.
    sensibilite_confiance: Mapped[Sensibilite] = mapped_column(
        Enum(Sensibilite, native_enum=False), nullable=False, default=Sensibilite.MOYEN
    )
    sensibilite_pertinence: Mapped[Sensibilite] = mapped_column(
        Enum(Sensibilite, native_enum=False), nullable=False, default=Sensibilite.MOYEN
    )

    # Structure de plans tarifaires (spec section 9bis) — gouverne quels signaux
    # (via SourceDef.plan_minimum) entrent en ligne de compte pour CE profil dans
    # falkye/engine.py, en plus des deux portes confiance/pertinence ci-dessus.
    # Changé normalement par falkye/billing/stripe_client.py (webhook d'abonnement),
    # jamais directement par l'utilisateur.
    plan: Mapped[PlanTarifaire] = mapped_column(
        Enum(PlanTarifaire, native_enum=False), nullable=False, default=PlanTarifaire.ECHO
    )

    # Accès API/webhook complet — spec section 4bis, fonctionnalité Radar+
    # ("pousser chaque nouveau signal... vers un système externe de
    # l'institution"). Le champ existe pour tout profil (comme plan lui-même),
    # mais falkye/notifications/webhook_channel.py::resoudre_destinataire ne
    # l'utilise que pour un profil RADAR_PLUS — stocker l'URL n'est pas ce qui
    # gate l'accès, la vérification de plan au moment de la livraison l'est.
    webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    besoins: Mapped[list["ProfileNeed"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )

    # Intégration CRM (HubSpot/Pipedrive, ajoutée le 2026-09-02) — voir
    # falkye/models/crm_connection.py. Disponible pour Radar ET Radar+
    # (contrairement au webhook, réservé Radar+ seul).
    connexions_crm: Mapped[list["CrmConnection"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )

    def besoins_fournisseur(self) -> list["ProfileNeed"]:
        """Paires sphère+usage actives pour la mécanique fournisseur (seule
        implémentée par le moteur en Phase 1)."""
        return [b for b in self.besoins if b.type_besoin == "offre"]


class ProfileNeed(Base):
    """Une paire sphère de besoin + usage précis (section 4 : "plusieurs paires
    sphère+usage possibles en parallèle", chacune scannée séparément).

    Vocabulaire "usage" (pas "service") depuis le 2026-09-02 — spec section 9,
    principe directeur #6 révisé : "le produit doit rester utilisable par une
    multitude de types d'utilisateurs — pas seulement des fournisseurs de
    services B2B." Un consultant en implantation a un "service", mais une
    chambre de commerce qui suit son territoire pour un rapport n'en a pas —
    "usage" couvre les deux sans présumer d'un contexte commercial. Renommé
    `usage_precis` (colonne SQL renommée sur la base réelle, migration
    ponctuelle — voir docs/STATUT_RESEAU.md) ; `service_precis` n'existe plus.

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

    # Usage précis : texte libre (chaque utilisateur décrit sa spécialité ou son
    # usage avec ses propres mots — ex. "implantation de systèmes d'inventaire",
    # "courtage d'assurance commerciale", "suivi de la croissance manufacturière
    # régionale" pour un usage hors vente). Vide pour type_besoin="besoin".
    # Volontairement libre plutôt qu'une liste fermée (spec section 4) : le
    # produit ne présume d'aucun secteur, service ou finalité en particulier
    # (spec section 9, "Polyvalence d'utilisation").
    usage_precis: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Mots-clés/tags optionnels (texte séparé par virgules) utilisés pour la
    # correspondance qualitative avec les titres de poste (spec section 7, Signal 3).
    mots_cles: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Territoire propre à CE besoin — spec section 4bis, "Profils de recherche
    # multiples simultanés (multi-usage × multi-territoire)" (ajoutée le
    # 2026-09-02) : un compte Radar+ gère plusieurs combinaisons sphère/usage ×
    # territoire sous UN SEUL profil plutôt qu'un profil par combinaison (ex.
    # recrutement-QC, recrutement-ON, formation-QC, formation-ON). Texte libre,
    # même principe que SousCompte.territoire — comparé à Company.region/ville
    # par correspondance simple (falkye/matching.py::match_profile), pas une
    # hiérarchie territoriale formelle.
    #
    # NULL = aucun filtrage géographique pour ce besoin (comportement par
    # défaut, préserve exactement le comportement historique — Profile.ville/
    # region/rayon_km existaient depuis la Phase 1 mais ne filtraient déjà
    # rien, voir docs/ARCHITECTURE.md ; ce champ n'introduit donc un vrai
    # filtrage géographique QUE pour un besoin qui le définit explicitement).
    territoire: Mapped[str | None] = mapped_column(String(200), nullable=True)

    profile: Mapped[Profile] = relationship(back_populates="besoins")
    sphere = relationship("Sphere")

    def liste_mots_cles(self) -> list[str]:
        if not self.mots_cles:
            return []
        return [m.strip() for m in self.mots_cles.split(",") if m.strip()]
