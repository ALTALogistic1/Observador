"""Candidat de nouvelle sphère — journal des cas que le Niveau 2 de l'assistance
IA (spec Radar+, point 8, ajoutée le 2026-09-03) n'a pu rattacher à AUCUNE sphère
existante avec confiance.

Garde-fou non négociable de la spec, préservé ici structurellement (pas
seulement par instruction au modèle, voir falkye/assistance_sphere_ia.py) : le
Niveau 2 ne crée JAMAIS lui-même une nouvelle sphère dans le registre officiel.
Un cas non résolu est journalisé ici, à examiner par Alexandre — exactement
comme la sphère "financement_acces_capital" a été ajoutée par décision humaine
après avoir croisé plusieurs personas, jamais par un mécanisme automatique (voir
falkye/registry/spheres.yaml). Le rattachement à une nouvelle sphère éventuelle,
si Alexandre décide d'en créer une, reste une modification manuelle du registre —
cette table ne fait qu'archiver le signal.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from falkye.models.base import Base, utcnow


class CandidatSphere(Base):
    __tablename__ = "candidats_spheres"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), nullable=False)

    # Description libre TELLE QUE saisie par l'utilisateur — jamais reformulée ni
    # résumée à cette étape (principe directeur #1, "jamais fabriquer une
    # valeur") : la valeur brute est ce qu'Alexandre doit voir pour juger si un
    # nouveau besoin réel se dessine.
    texte_description: Mapped[str] = mapped_column(Text, nullable=False)

    # Résumé/raisonnement renvoyé par le Niveau 2 (Claude) expliquant pourquoi
    # aucune sphère existante ne convenait — aide à la lecture par Alexandre,
    # jamais utilisé pour une décision automatique.
    resume_niveau2: Mapped[str | None] = mapped_column(Text, nullable=True)

    # "a_examiner" (défaut) | "sphere_creee" | "rattache_existante" | "ecarte" —
    # mis à jour manuellement par Alexandre après examen, jamais par le système.
    statut: Mapped[str] = mapped_column(String(20), nullable=False, default="a_examiner")

    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    profile = relationship("Profile")
