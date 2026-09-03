"""Synonyme/mot-clé associé à une sphère, pour l'assistance à la configuration
du profil par IA — Niveau 1 (spec Radar+, point 8, ajoutée le 2026-09-03).

Deux origines, jamais confondues :
  - "registre"   : synonymes du noyau curé, chargés depuis
                    falkye/registry/spheres.yaml::SphereDef.synonymes (voir
                    db.seed_sphere_synonymes_from_registry) — resynchronisés à
                    chaque démarrage, jamais modifiés directement en base.
  - "ia_niveau2" : synonyme APPRIS par le Niveau 2 (falkye/assistance_sphere_ia.py)
                    quand Claude rattache avec confiance une description libre à
                    une sphère EXISTANTE que le Niveau 1 n'a pas su reconnaître —
                    enrichissement silencieux du dictionnaire de CETTE sphère,
                    jamais création d'une nouvelle sphère (voir
                    falkye/models/diagnostic_journal.py pour le cas contraire).

Le texte reste toujours ce qu'il est : un point de repère pour le matching local
(Niveau 1), jamais une garantie que la sphère est LA bonne pour un utilisateur
donné — la suggestion finale reste une proposition que l'utilisateur confirme ou
corrige (spec, garde-fou non négociable), jamais une classification silencieuse.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from falkye.models.base import Base, utcnow


class SphereSynonyme(Base):
    __tablename__ = "sphere_synonymes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sphere_id: Mapped[str] = mapped_column(ForeignKey("spheres.id"), nullable=False)
    texte: Mapped[str] = mapped_column(String(200), nullable=False)
    # "registre" | "ia_niveau2" — voir docstring du module.
    origine: Mapped[str] = mapped_column(String(20), nullable=False, default="registre")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    sphere = relationship("Sphere")
