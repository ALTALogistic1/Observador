"""Rétroaction de pertinence — spec section 4bis ("Lien avec la rétroaction
utilisateur... résolu ici", ajoutée le 2026-09-02) : quand un prospect est marqué
"Pas pertinent" (falkye/registry/statuts_suivi.yaml), le système réduit LÉGÈREMENT
le poids de la sphère qui a produit sa correspondance, pour les prochaines
notifications de CE profil. Voir falkye/retroaction.py pour le mécanisme et
falkye/pertinence.py pour son application au score.

Granularité SPHÈRE, pas mot-clé (décision d'implémentation assumée, documentée
ici plutôt que laissée implicite) : la spec dit "mots-clés/sphères" sans préciser
le mécanisme exact. `Notification.sphere_probable_id` est déjà une donnée
structurée et fiable ; le mot-clé qualitatif exact qui a produit une
correspondance AAA n'est aujourd'hui capturé que dans un texte libre
(NotificationSignal.justification), pas dans un champ structuré — l'ajouter
demanderait une capture de données supplémentaire, pas seulement une couche de
calcul, contrairement au principe déjà établi pour le score de pertinence
lui-même (falkye/pertinence.py). Affinage possible plus tard si l'usage réel le
justifie (principe directeur #9 : ne pas complexifier pour du non confirmé)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from falkye.models.base import Base, utcnow


class RetroactionPertinence(Base):
    __tablename__ = "retroaction_pertinence"
    __table_args__ = (UniqueConstraint("profile_id", "sphere_id", name="uq_retroaction_profile_sphere"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), nullable=False)
    sphere_id: Mapped[str] = mapped_column(ForeignKey("spheres.id"), nullable=False)

    # Multiplicateur appliqué au score de pertinence de base pour cette sphère,
    # pour CE profil (falkye/pertinence.py) — jamais en dessous de POIDS_PLANCHER
    # (falkye/retroaction.py) : "légèrement réduire", jamais supprimer.
    poids: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    compte_marques_pas_pertinent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    profile = relationship("Profile")
