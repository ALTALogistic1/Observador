"""Lien candidat entre deux Company de provinces différentes, découvert par
rapprochement flou de nom — spec Radar+, point 7 ("Détection d'expansion
inter-provinciale"), plan confirmé le 2026-09-03.

Un LIEN, jamais une fusion : les deux dossiers cumulatifs (Company) restent
distincts et traçables — voir falkye/expansion_interprovinciale.py pour le
mécanisme complet et les deux garde-fous (structurel + textuel) qui empêchent
de présenter ce rapprochement comme garanti.

`company_id_a`/`company_id_b` sont toujours ordonnés (`company_id_a <
company_id_b`, canonicalisé à l'écriture) pour qu'une paire ne soit jamais
enregistrée deux fois sous ses deux ordres possibles."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from falkye.models.base import Base, utcnow


class LienInterprovincial(Base):
    __tablename__ = "liens_interprovinciaux"
    __table_args__ = (
        UniqueConstraint("company_id_a", "company_id_b", name="uq_lien_interprovincial_paire"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id_a: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    company_id_b: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    # Code de province (SourceDef.province_code) associé à chaque moitié de la
    # paire au moment de la découverte — chaque Company n'ayant, en pratique,
    # de signaux que d'UNE seule source provinciale (raison d'être même de ce
    # lien : deux dossiers séparés faute d'identifiant commun).
    province_a: Mapped[str] = mapped_column(String(8), nullable=False)
    province_b: Mapped[str] = mapped_column(String(8), nullable=False)
    # Score rapidfuzz (fuzz.WRatio, 0-100) du rapprochement par nom — jamais
    # affiché comme un fait, toujours accompagné du libellé hedgé (voir
    # falkye/expansion_interprovinciale.py::evaluer_pour_company).
    score_correspondance: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    company_a = relationship("Company", foreign_keys=[company_id_a])
    company_b = relationship("Company", foreign_keys=[company_id_b])
