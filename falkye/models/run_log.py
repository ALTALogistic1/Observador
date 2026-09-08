"""Journal d'exécution par source — visibilité opérationnelle sur le moteur qui boucle
sur les sources actives (spec section 9).

**Chantier 2, travail 1bis.** Cette table est l'une des TROIS qui décrivent la
même exécution. Les deux autres — `DiffRunHistorique` et `DiffQuarantaine` —
vivent dans la base des MIROIRS, un fichier local; celle-ci vit dans la base du
PRODUIT, distante. Le rattachement passe donc par `execution_id`, une valeur
opaque partagée, jamais une clé étrangère : aucune contrainte d'intégrité ne
traverse deux bases. Voir falkye/execution.py.
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from falkye.models.base import Base, utcnow


class StatutExecution(str, enum.Enum):
    """Les issues d'une exécution de source, jamais réduites à un booléen.

    **`SUCCES` désigne la réussite PUBLIÉE, et rien d'autre.** C'est le premier
    critère d'acceptation du chantier 2, et il échouait : une source mise en
    quarantaine retourne zéro signal, et `ingest_source` l'enregistrait comme un
    succès ordinaire à zéro signal — mot pour mot ce qu'enregistre un territoire
    calme. `QUARANTAINE` sépare les deux : la donnée a été obtenue et lue, le
    diff a été jugé aberrant, rien n'a été publié.

    `ERREUR` est l'échec TECHNIQUE : la donnée n'a jamais été obtenue.
    `IGNOREE` n'est pas un échec : la source n'a pas de connecteur, elle n'a pas
    été tentée — la compter ailleurs gonflerait le dénominateur et ferait passer
    un effondrement complet pour une panne partielle.

    Les quatre valeurs historiques sont conservées telles quelles : les lignes
    déjà en base restent lisibles sans réécriture. Seule `QUARANTAINE` s'ajoute.
    """

    EN_COURS = "en_cours"
    SUCCES = "succes"
    QUARANTAINE = "quarantaine"
    ERREUR = "erreur"
    IGNOREE = "ignoree"


class SourceRunLog(Base):
    __tablename__ = "source_run_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False)
    mode: Mapped[str] = mapped_column(String(30), nullable=False)  # veille_continue | recherche_ponctuelle

    # Rattache cette ligne aux traces de la même exécution dans la base des
    # miroirs. NULL pour les lignes écrites avant le chantier 2, et pour toute
    # trace écrite hors d'une exécution ouverte — jamais un identifiant
    # fabriqué (falkye/execution.py).
    execution_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)

    started_at: Mapped[datetime] = mapped_column(default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    statut: Mapped[str] = mapped_column(
        String(20), nullable=False, default=StatutExecution.EN_COURS.value
    )
    nb_signaux_detectes: Mapped[int] = mapped_column(Integer, default=0)
    nb_entreprises_nouvelles: Mapped[int] = mapped_column(Integer, default=0)
    erreur: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Ce que l'exécution a COÛTÉ, à côté de ce qu'elle a produit.
    #
    # **Deux grandeurs, deux noms, jamais un `nb_lignes_lues` nu.** Le mandat
    # demande de conserver « le volume de lignes lues » : dans son contexte,
    # celles du FICHIER SOURCE. Ce que le quota facture est autre chose — les
    # lignes que la base distante a dû parcourir. Deux mesures sans rapport sous
    # un seul nom, dans la même table, c'est le motif du projet en miniature.
    #
    # Écrits dès la première exécution, lus plus tard : une norme de volume ne
    # devient calculable qu'avec de l'historique, et l'historique ne se rattrape
    # pas en accélérant après coup.
    nb_lignes_source: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # NULL tant que la mesure n'est pas disponible : le pilote libSQL utilisé par
    # SQLAlchemy n'expose pas `rows_read` (seul le protocole Hrana le rend). Un
    # zéro écrit à la place d'une absence de mesure ferait lire « cette exécution
    # n'a rien coûté » — la troisième forme du silence indistinct.
    nb_lignes_lues_base: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duree_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
