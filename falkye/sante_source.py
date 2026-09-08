"""Santé de source — chantier 2, faille F.

Le chantier 1 traite la source qui produit TROP. Celui-ci traite l'inverse, plus
fréquent : une source qui ne produit rien. Cinq causes distinctes pour un seul
symptôme observable, dont deux qui ne sont pas techniques.

**Ce module ne classe encore rien.** Il porte, pour l'instant, la seule lecture
dont tout le reste dépend : *quand cette source a-t-elle réussi pour la dernière
fois?* — au sens strict, celui d'une exécution qui a PUBLIÉ.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from falkye.models.run_log import SourceRunLog, StatutExecution


def derniere_execution_reussie(db_session: Session, source_id: str) -> SourceRunLog | None:
    """La dernière exécution qui a PUBLIÉ. Jamais une quarantaine.

    **C'est le premier critère d'acceptation du chantier 2.** Trois choses qu'il
    ne faut pas confondre se ressemblent toutes de loin : une exécution qui a
    échoué techniquement, une qui a lu la donnée et refusé de la publier
    (quarantaine), et une qui a publié. La deuxième est la piégeuse — elle rend
    zéro signal sans lever, exactement comme un territoire calme.

    Ce que cette date commande, et pourquoi elle doit être juste : la fenêtre de
    rattrapage de la veille continue (travail 4 du mandat) en dérivera son
    `since`. Prendre une quarantaine pour une réussite ferait avancer la fenêtre
    au-dessus de données jamais publiées — et ce qui a été sauté ne revient pas.

    `finished_at` plutôt que `started_at` : c'est la fin qui atteste, et une
    ligne restée ouverte n'atteste de rien.
    """
    return db_session.execute(
        select(SourceRunLog)
        .where(
            SourceRunLog.source_id == source_id,
            SourceRunLog.statut == StatutExecution.SUCCES.value,
            SourceRunLog.finished_at.is_not(None),
        )
        .order_by(SourceRunLog.finished_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def date_derniere_reussite(db_session: Session, source_id: str) -> datetime | None:
    """La date seule, ou None si cette source n'a jamais publié.

    None est un état RICHE, pas un manque : une source qui n'a jamais publié est
    peut-être neuve, peut-être en attente d'une clé, peut-être défaillante depuis
    toujours. Ce module ne tranche pas encore entre ces cas — mais il ne doit
    surtout pas les aplatir sur une date par défaut.
    """
    ligne = derniere_execution_reussie(db_session, source_id)
    return ligne.finished_at if ligne else None
