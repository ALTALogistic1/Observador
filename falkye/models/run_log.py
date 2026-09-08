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
    #: L'exécution n'a pas fini, et personne n'a pu écrire pourquoi. Distincte
    #: d'`ERREUR`, qui veut dire « on a vu l'échec et on l'a consigné » :
    #: `INTERROMPUE` veut dire « on ne sait pas pourquoi, seulement que ça n'a
    #: pas fini ». Le 2026-09-08 en donne les deux exemples — un SIGTERM, et un
    #: quota épuisé qui empêchait d'écrire la trace de sa propre panne.
    INTERROMPUE = "interrompue"


#: Les statuts qui décrivent **la source**, et eux seuls, entrent dans sa santé :
#: norme de volume, escalade de quarantaine, dernière exécution réussie.
#:
#: `INTERROMPUE` n'en est pas. Un quota épuisé n'est pas huit connecteurs qui se
#: dégradent, c'est l'infrastructure qui tombe — et le statut décrit l'exécution,
#: pas le connecteur. Le compter dans la santé recréerait, par le statut même qui
#: les distingue, la confusion des causes que ce chantier existe pour lever.
#:
#: Il reste VISIBLE au tableau de bord d'exploitation : ne pas dégrader une
#: source n'est pas se taire.
STATUTS_DE_SOURCE = frozenset(
    {
        StatutExecution.SUCCES.value,
        StatutExecution.QUARANTAINE.value,
        StatutExecution.ERREUR.value,
    }
)

#: Ce qui décrit l'INFRASTRUCTURE — l'hôte, la base, le quota —, jamais la source.
STATUTS_DINFRASTRUCTURE = frozenset({StatutExecution.INTERROMPUE.value})


def decrit_la_source(statut: str) -> bool:
    """Ce statut doit-il peser sur la santé de la source?

    Ni `EN_COURS` (rien n'est conclu) ni `IGNOREE` (la source n'a pas été
    tentée) ni `INTERROMPUE` (l'infrastructure a lâché) n'y entrent.
    """
    return statut in STATUTS_DE_SOURCE


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

    # Qui a démarré cette exécution — `unite`, `manuel`, ou `inconnu` pour les
    # lignes écrites avant que ce champ existe.
    #
    # **Ce champ est la condition de validité d'une déduction**, pas une
    # curiosité. Refermer une ligne restée ouverte s'appuie sur « au-delà du
    # délai de l'unité, systemd l'aurait tuée » — ce qui suppose que systemd la
    # surveillait. Un cycle lancé à la main n'est gouverné par aucun délai. Sans
    # ce champ, la bascule serait vraie sous une condition non vérifiée.
    lance_par: Mapped[str | None] = mapped_column(String(10), nullable=True)

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

    # --- Ventilation par CHEMIN DE RÉSOLUTION (falkye/cout_lectures.py).
    #
    # Des COMPTES exacts, mesurés par incrément au point d'appel — pas des
    # lignes lues. Les lignes se DÉRIVENT de ces comptes et de la population du
    # moment, à la lecture du rapport, jamais ici : le prix d'un chemin dépend
    # du nombre d'entreprises sans NEQ, donc un total figé dans cette ligne
    # vieillirait sans que rien ne le signale.
    #
    # `nb_resolutions_sous_chaine` est celui qui compte : c'est le seul des
    # trois chemins que l'index composite du 2026-09-08 ne corrige pas, et il
    # lit toute la population sans NEQ à chaque appel. Sa fréquence décide s'il
    # se borne ou se retire.
    nb_resolutions_exact: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nb_resolutions_prefixe: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nb_resolutions_sous_chaine: Mapped[int | None] = mapped_column(Integer, nullable=True)
