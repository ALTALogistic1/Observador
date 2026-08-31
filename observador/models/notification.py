"""Notification consolidée (spec section 6) : un seul score de confiance unifié par
notification, potentiellement corroborée par plusieurs signaux indépendants."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import JSON, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from observador.models.base import Base, utcnow


class NiveauConfiance(str, enum.Enum):
    FAIBLE = "faible"
    MOYEN = "moyen"
    ELEVE = "eleve"


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
    niveau: Mapped[NiveauConfiance] = mapped_column(
        Enum(NiveauConfiance, native_enum=False), nullable=False
    )

    sphere_probable_id: Mapped[str | None] = mapped_column(ForeignKey("spheres.id"), nullable=True)
    justification_resumee: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    inclus_dans_resume: Mapped[bool] = mapped_column(default=False)

    company = relationship("Company", back_populates="notifications")
    profile = relationship("Profile")
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
    des canaux, observador/notifications/). Une notification peut être livrée sur
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
