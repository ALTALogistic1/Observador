"""Notification consolidée (spec section 6, restructurée) : DEUX axes indépendants
par notification — score de confiance (le signal est-il réel et fort) et score de
pertinence (ce signal correspond-il au profil précis de cet utilisateur) — combinés
en matrice, jamais en moyenne, jamais fusionnés en un seul chiffre. Toujours UN SEUL
indice PAR AXE, pas de jauges parallèles supplémentaires (ex. urgence) à l'intérieur
d'un même axe — voir falkye/scoring.py (confiance) et falkye/pertinence.py
(pertinence, nouveau)."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import JSON, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from falkye.models.base import Base, utcnow


class NiveauConfiance(str, enum.Enum):
    FAIBLE = "faible"
    MOYEN = "moyen"
    ELEVE = "eleve"


class NiveauPertinence(str, enum.Enum):
    """A / AA / AAA (spec section 6, restructurée) — registre positif avec
    gradation, jamais un niveau "sans pertinence" : un MatchResult (falkye/
    matching.py) doit déjà exister pour qu'une notification soit envisagée du
    tout, donc A est le plancher, pas une absence de correspondance."""

    A = "A"
    AA = "AA"
    AAA = "AAA"


class ModeUsage(str, enum.Enum):
    VEILLE_CONTINUE = "veille_continue"
    RECHERCHE_PONCTUELLE = "recherche_ponctuelle"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), nullable=False)

    mode: Mapped[ModeUsage] = mapped_column(Enum(ModeUsage, native_enum=False), nullable=False)

    score_confiance: Mapped[float] = mapped_column(Float, nullable=False)  # 0-100
    niveau_confiance: Mapped[NiveauConfiance] = mapped_column(
        Enum(NiveauConfiance, native_enum=False), nullable=False
    )

    # Nullable : les notifications antérieures au 2026-09-01 (avant la
    # restructuration du score en deux axes) n'ont pas de pertinence calculée
    # rétroactivement — jamais de valeur inventée pour combler l'historique
    # (principe directeur #1). NULL = notification antérieure au système de
    # pertinence, pas une pertinence nulle/manquante à corriger.
    score_pertinence: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-100, interne
    niveau_pertinence: Mapped[NiveauPertinence | None] = mapped_column(
        Enum(NiveauPertinence, native_enum=False), nullable=True
    )

    sphere_probable_id: Mapped[str | None] = mapped_column(ForeignKey("spheres.id"), nullable=True)
    justification_resumee: Mapped[str] = mapped_column(Text, nullable=False)

    # Combinaison sphère/usage × territoire à l'origine de cette notification —
    # spec section 4bis, "Profils de recherche multiples simultanés" (ajoutée
    # le 2026-09-02) : permet de filtrer le tableau de bord par usage ou par
    # territoire quand un compte gère plusieurs combinaisons en parallèle sous
    # un seul profil. Nullable pour l'historique (jamais de valeur inventée,
    # principe directeur #1) — les notifications antérieures à cette
    # fonctionnalité n'ont qu'une seule combinaison possible par profil de
    # toute façon (un seul ProfileNeed était la norme avant cette mise à jour).
    profile_need_id: Mapped[int | None] = mapped_column(ForeignKey("profile_needs.id"), nullable=True)

    # Statut de suivi du tableau de bord (spec section 4bis, "Radar et Radar+
    # seulement", ajoutée le 2026-09-02) — propre à l'utilisateur, distinct des
    # deux axes confiance/pertinence ci-dessus. Nullable pour les notifications
    # antérieures à cette fonctionnalité (jamais de valeur inventée pour combler
    # l'historique, principe directeur #1) ; falkye/engine.py attribue le statut
    # par défaut du registre (registry/statuts_suivi.yaml) à toute NOUVELLE
    # notification, mais ne retouche jamais l'historique existant.
    statut_suivi_id: Mapped[str | None] = mapped_column(ForeignKey("statuts_suivi.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    inclus_dans_resume: Mapped[bool] = mapped_column(default=False)

    company = relationship("Company", back_populates="notifications")
    profile = relationship("Profile")
    profile_need = relationship("ProfileNeed")
    statut_suivi = relationship("StatutSuivi")
    signaux_contributifs: Mapped[list["NotificationSignal"]] = relationship(
        back_populates="notification", cascade="all, delete-orphan"
    )
    livraisons: Mapped[list["NotificationDelivery"]] = relationship(
        back_populates="notification", cascade="all, delete-orphan"
    )


class NotificationSignal(Base):
    """Association notification <-> signal, avec la justification PROPRE à ce signal
    (section 6 : "présente chaque signal ayant contribué à la détection, avec sa
    source et sa justification propre")."""

    __tablename__ = "notification_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    notification_id: Mapped[int] = mapped_column(ForeignKey("notifications.id"), nullable=False)
    signal_id: Mapped[int] = mapped_column(ForeignKey("signals.id"), nullable=False)
    justification: Mapped[str] = mapped_column(Text, nullable=False)

    notification: Mapped[Notification] = relationship(back_populates="signaux_contributifs")
    signal = relationship("Signal")


class NotificationDelivery(Base):
    """Une tentative de livraison d'une notification sur un canal donné (registre
    des canaux, falkye/notifications/). Une notification peut être livrée sur
    plusieurs canaux si l'utilisateur en active plusieurs."""

    __tablename__ = "notification_deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    notification_id: Mapped[int] = mapped_column(ForeignKey("notifications.id"), nullable=False)
    channel_id: Mapped[str] = mapped_column(String(64), nullable=False)  # voir notification_channels.yaml
    statut: Mapped[str] = mapped_column(String(30), nullable=False)  # envoyee | echec | a_developper
    tentee_le: Mapped[datetime] = mapped_column(default=utcnow)
    erreur: Mapped[str | None] = mapped_column(Text, nullable=True)

    notification: Mapped[Notification] = relationship(back_populates="livraisons")


class PeriodicSummary(Base):
    """Résumé périodique (spec section 5, en complément des notifications individuelles,
    ne les remplace pas)."""

    __tablename__ = "periodic_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), nullable=False)
    periode_debut: Mapped[datetime] = mapped_column(nullable=False)
    periode_fin: Mapped[datetime] = mapped_column(nullable=False)
    notification_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    genere_le: Mapped[datetime] = mapped_column(default=utcnow)
    envoye_le: Mapped[datetime | None] = mapped_column(nullable=True)

    profile = relationship("Profile")
