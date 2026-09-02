"""Table de correspondance entre une entreprise FALKYE et l'objet CRM qui la
représente côté HubSpot/Pipedrive (Company/Organization) — condition pour un
UPSERT propre (mettre à jour la MÊME fiche à chaque nouvelle notification pour
cette entreprise) plutôt qu'un doublon créé à chaque cycle de veille. Intégration
CRM, ajoutée le 2026-09-02 — voir falkye/crm_sync.py."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from falkye.models.base import Base, utcnow


class CrmSyncRecord(Base):
    __tablename__ = "crm_sync_records"
    __table_args__ = (
        UniqueConstraint(
            "profile_id", "company_id", "fournisseur", name="uq_crm_sync_profile_company_fournisseur"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    fournisseur: Mapped[str] = mapped_column(String(64), nullable=False)  # voir registry/crm_providers.yaml

    crm_object_id: Mapped[str] = mapped_column(String(200), nullable=False)

    # Dernier statut_suivi_id que FALKYE a LUI-MÊME poussé vers le CRM — permet au
    # sondage retour (falkye/crm_sync.py::sonder_statuts_crm) de raisonner sur
    # l'origine d'un changement, en complément de dernier_stage_crm_connu.
    dernier_statut_pousse_id: Mapped[str | None] = mapped_column(
        ForeignKey("statuts_suivi.id"), nullable=True
    )
    # Dernière valeur BRUTE d'étape/stage lue côté CRM (texte propre au compte du
    # client, pas forcément présente dans CrmConnection.mapping_statuts) —
    # comparée au sondage suivant pour ne traiter qu'un CHANGEMENT, jamais
    # retraiter un état stable à chaque cycle de veille.
    dernier_stage_crm_connu: Mapped[str | None] = mapped_column(String(200), nullable=True)

    derniere_synchro_le: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    profile = relationship("Profile")
    company = relationship("Company")
