"""Abonnement Stripe pour le plan Radar (spec section 9bis, "paiement intégré").

Distinct de `Profile.plan` : `Profile.plan` est l'état EFFECTIF utilisé par le
moteur (falkye/engine.py) pour filtrer les signaux, tandis que `Subscription`
suit l'état côté Stripe (identifiants, statut du cycle de facturation) qui a
produit ce plan — falkye/billing/stripe_client.py synchronise le second vers le
premier à chaque événement webhook, jamais l'inverse. Une seule ligne par profil
(pas d'historique des abonnements précédents en Phase 1 — cohérent avec l'absence
d'outil de migration formel du projet, voir falkye/db.py:init_db)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from falkye.models.base import Base, utcnow


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), nullable=False, unique=True)

    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Statuts Stripe natifs (trialing/active/past_due/canceled/unpaid/
    # incomplete/incomplete_expired) — reflétés tels quels plutôt que traduits
    # dans un vocabulaire propre au projet, pour rester exact face à ce que
    # Stripe envoie réellement (voir falkye/billing/stripe_client.py).
    statut: Mapped[str | None] = mapped_column(String(30), nullable=True)
    periode_courante_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    profile = relationship("Profile")
