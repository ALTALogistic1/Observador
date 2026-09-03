"""Lien sphère↔besoin, pondéré, plusieurs-à-plusieurs — spec section 8bis
(2026-09-03), évolution de `falkye/models/profile.py::ProfileNeed`.

Remplace COMPLÈTEMENT `ProfileNeed.sphere_id` (colonne unique retirée, pas
gardée en parallèle comme raccourci dénormalisé — décision explicite
d'Alexandre : "aucune source de vérité qui peut diverger"). Née du constat
qu'un service peut légitimement appartenir à plusieurs sphères à la fois — un
cas réel (implantation de systèmes ERP/WMS touchant à la fois la
technologie/systèmes et les opérations) a produit un partage à ÉGALITÉ EXACT
entre deux sphères au Niveau 1 de l'assistance IA ; forcer un seul gagnant
aurait perdu du signal.

`poids` (0-100, même échelle que `falkye/scoring.py`/`falkye/pertinence.py`/
rapidfuzz — cohérence avec le reste du projet) : PAS de colonne
`est_primaire` séparée — la sphère "principale" d'un besoin est TOUJOURS
dérivée du lien au poids le plus élevé (`ProfileNeed.sphere_principale`),
jamais stockée séparément, pour ne jamais avoir deux sources de vérité qui
peuvent se contredire.

Alimenté par `falkye/assistance_sphere.py` (Niveau 1, gratuit) et
`falkye/assistance_sphere_ia.py` (Niveau 2, Radar/Radar+) via la commande
conversationnelle `falkye profile configurer-besoin` — jamais un écran de
pourcentages : l'utilisateur décrit son service en texte libre, ces poids
sont calculés pour lui, jamais quelque chose qu'il doit lire ou manipuler
pour configurer son profil. Le raffinement manuel (`falkye profile
lier-sphere` / `definir-sphere-principale`) reste une option, jamais une
étape obligatoire.

Consommé par `falkye/matching.py::match_profile` (un besoin matche un signal
via N'IMPORTE LEQUEL de ses liens) et `falkye/pertinence.py::base_match`
(le poids du lien retenu module le score de base — un lien à poids 100 se
comporte exactement comme avant cette évolution, un lien à poids 50 atterrit
à mi-chemin)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from falkye.models.base import Base, utcnow


class ProfileNeedSphere(Base):
    __tablename__ = "profile_need_spheres"
    __table_args__ = (
        UniqueConstraint("profile_need_id", "sphere_id", name="uq_profile_need_sphere"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_need_id: Mapped[int] = mapped_column(ForeignKey("profile_needs.id"), nullable=False)
    sphere_id: Mapped[str] = mapped_column(ForeignKey("spheres.id"), nullable=False)
    poids: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    profile_need = relationship("ProfileNeed", back_populates="spheres_liees")
    sphere = relationship("Sphere")
