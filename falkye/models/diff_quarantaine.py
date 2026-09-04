"""Quarantaine de diff (Chantier 1, spec section 8bis — audit du 2026-09-03,
faille E). Une exécution mise en quarantaine ne publie RIEN — l'état
précédent (falkye/models/etat_diff_source.py) reste intact, le diff suspect
est archivé (fichier brut sur disque, voir falkye/diff_engine.py) et cette
table garde la trace structurée pour révision humaine et journalisation de la
levée (qui, quand, motif — jamais silencieuse, réservée au mode opérateur)."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import JSON, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from falkye.models.base import Base, utcnow


class MotifQuarantaine(str, enum.Enum):
    SCHEMA_COLONNE_RETIREE = "schema_colonne_retiree"
    SCHEMA_TYPE_MODIFIE = "schema_type_modifie"
    VOLUME_APPARITIONS = "volume_apparitions"
    VOLUME_DISPARITIONS = "volume_disparitions"
    VOLUME_MODIFICATIONS = "volume_modifications"
    LECTURE_ECHOUEE = "lecture_echouee"


class StatutQuarantaine(str, enum.Enum):
    EN_ATTENTE = "en_attente"
    ACCEPTEE = "acceptee"
    REJETEE = "rejetee"


class DiffQuarantaine(Base):
    __tablename__ = "diff_quarantaines"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    motif: Mapped[MotifQuarantaine] = mapped_column(Enum(MotifQuarantaine, native_enum=False), nullable=False)

    # Détail structuré du diff suspect — comptes par type, seuils dépassés,
    # colonnes en cause selon le motif, ET le diff calculé au complet
    # (apparitions/disparitions/modifications) — une levée acceptée
    # (falkye/diff_engine.py::lever_quarantaine) APPLIQUE ce diff tel quel,
    # jamais en relançant une nouvelle collecte contre la source (qui aurait
    # pu changer entretemps) : "accepter" confirme que CE diff précis était
    # réel, pas qu'un diff plus récent l'est aussi.
    detail: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Chemin du fichier brut archivé (falkye/diff_engine.py::ARCHIVE_DIR),
    # pour inspection humaine du diff suspect — jamais rechargé automatiquement.
    chemin_archive: Mapped[str | None] = mapped_column(String(500), nullable=True)

    statut: Mapped[StatutQuarantaine] = mapped_column(
        Enum(StatutQuarantaine, native_enum=False), nullable=False, default=StatutQuarantaine.EN_ATTENTE
    )
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    # Renseignés uniquement une fois levée — jamais par le système lui-même
    # (levée toujours une action humaine explicite, mode opérateur).
    levee_par: Mapped[str | None] = mapped_column(String(320), nullable=True)
    levee_le: Mapped[datetime | None] = mapped_column(nullable=True)
    levee_motif: Mapped[str | None] = mapped_column(Text, nullable=True)
