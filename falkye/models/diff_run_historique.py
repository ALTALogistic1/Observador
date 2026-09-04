"""Journal d'exécution du moteur de diff (Chantier 1, suivi du 2026-09-04 —
réponse d'Alexandre au premier livrable : « journaliser l'amplitude de
chaque diff à chaque run, même très en dessous du seuil »).

Une ligne PAR APPEL à `falkye/diff_engine.py::executer_diff`, quel que soit
le chemin de sortie (run de référence, quarantaine — schéma, volume ou
lecture —, ou diff accepté normalement). Distinct de `DiffQuarantaine`
(qui n'existe que pour un INCIDENT) : cette table existe pour accumuler un
historique même quand tout va bien, faute de quoi la calibration des
seuils reste impossible indéfiniment — l'attente pure n'accumule rien,
seule la journalisation systématique le fait.

Sert deux usages directs :
  1. Observer dans le temps le taux de doublons de clé naturelle d'une
     source (`taux_doublons`) — un passage de 0,5% à 5% est le même type
     de signal qu'un changement de schéma : quelque chose a changé en
     amont, même si aucun seuil de quarantaine n'est franchi.
  2. Alimenter `falkye/diff_engine.py::proposer_seuils` — UNE PROPOSITION
     de seuil par source une fois assez d'historique accumulé, jamais une
     auto-application (voir la docstring de cette fonction)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from falkye.models.base import Base, utcnow


class DiffRunHistorique(Base):
    __tablename__ = "diff_run_historique"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    executed_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)

    run_reference: Mapped[bool] = mapped_column(default=False)
    quarantaine: Mapped[bool] = mapped_column(default=False)
    # Chaîne libre (valeur de MotifQuarantaine.value) plutôt que l'enum lui-même
    # — cette ligne existe aussi pour les runs SANS incident (motif=None),
    # jamais de FK vers DiffQuarantaine (un run normal n'en crée aucune).
    motif_quarantaine: Mapped[str | None] = mapped_column(String(64), nullable=True)

    nb_lignes_actuelles: Mapped[int] = mapped_column(default=0)
    nb_lignes_precedentes: Mapped[int] = mapped_column(default=0)

    # Nuls uniquement pour les deux quarantaines qui se déclenchent AVANT
    # tout calcul de diff (lecture_echouee, schéma). Renseignés partout
    # ailleurs, y compris sur un run de référence (où ils valent
    # nb_lignes_actuelles/0/0 — 100% d'apparitions, résultat structurel et
    # non signifiant pour la calibration, mais journalisé quand même pour
    # que l'historique reste lisible) et sur une quarantaine de VOLUME (le
    # diff est calculé avant de refuser de l'appliquer — l'amplitude est
    # connue et journalisée même là).
    nb_apparitions: Mapped[int | None] = mapped_column(nullable=True)
    nb_disparitions: Mapped[int | None] = mapped_column(nullable=True)
    nb_modifications: Mapped[int | None] = mapped_column(nullable=True)
    pct_apparitions: Mapped[float | None] = mapped_column(nullable=True)
    pct_disparitions: Mapped[float | None] = mapped_column(nullable=True)
    pct_modifications: Mapped[float | None] = mapped_column(nullable=True)

    # Doublons de clé naturelle rencontrés dans les lignes BRUTES de ce run
    # (avant dédoublonnage — voir _dedoublonner_lignes) — distingue les
    # doublons inoffensifs (contenu identique) des doublons DIVERGENTS
    # (signe d'une ambiguïté réelle sur la clé naturelle déclarée pour
    # cette source, jamais confondu avec un simple doublon).
    nb_doublons_identiques: Mapped[int] = mapped_column(default=0)
    nb_doublons_divergents: Mapped[int] = mapped_column(default=0)
    taux_doublons: Mapped[float] = mapped_column(default=0.0)

    # Seuils EFFECTIVEMENT appliqués à ce run (après resserrement de prudence
    # éventuel — voir NB_RUNS_MINIMUM_AVANT_SEUILS_NORMAUX) — conservés tels
    # quels plutôt que recalculés après coup, pour que l'historique reste
    # lisible même si la politique de seuils change plus tard.
    seuils_apparitions_pct: Mapped[float | None] = mapped_column(nullable=True)
    seuils_apparitions_abs: Mapped[int | None] = mapped_column(nullable=True)
    seuils_disparitions_pct: Mapped[float | None] = mapped_column(nullable=True)
    seuils_disparitions_abs: Mapped[int | None] = mapped_column(nullable=True)
    seuils_modifications_pct: Mapped[float | None] = mapped_column(nullable=True)
    seuils_modifications_abs: Mapped[int | None] = mapped_column(nullable=True)
    seuils_prudence_debut: Mapped[bool] = mapped_column(default=False)

    avertissements: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
