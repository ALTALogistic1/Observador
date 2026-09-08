"""Santé de source — chantier 2, faille F.

Le chantier 1 traite la source qui produit TROP. Celui-ci traite l'inverse, plus
fréquent : une source qui ne produit rien. Cinq causes distinctes pour un seul
symptôme observable, dont deux qui ne sont pas techniques.

**Ce module ne classe encore rien.** Il porte, pour l'instant, la seule lecture
dont tout le reste dépend : *quand cette source a-t-elle réussi pour la dernière
fois?* — au sens strict, celui d'une exécution qui a PUBLIÉ.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from falkye.delai_unite import DelaiUnite, delai_maximal
from falkye.execution import Lancement
from falkye.models.run_log import SourceRunLog, StatutExecution

logger = logging.getLogger(__name__)


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


# ---------------------------------------------------------------------------
# Refermer ce qui est resté ouvert
# ---------------------------------------------------------------------------


@dataclass
class RapportInterruptions:
    """Ce que la reprise a refermé, et ce qu'elle a refusé de conclure."""

    delai: DelaiUnite
    refermees: list[int] = field(default_factory=list)
    #: Ouvertes, trop vieilles, mais lancées à la main ou d'origine inconnue :
    #: aucun délai ne les gouvernait, donc rien ne permet de conclure. Elles
    #: restent `en_cours` et se SIGNALENT — ce qui n'est pas les ignorer.
    non_decidables: list[int] = field(default_factory=list)
    #: Ouvertes et encore dans le délai : elles tournent peut-être vraiment.
    encore_possibles: list[int] = field(default_factory=list)

    def resume_lisible(self) -> str:
        if self.delai.secondes is None:
            return (
                "exécutions interrompues : indécidable — aucun délai exploitable "
                f"({self.delai.provenance})"
            )
        parts = [f"{len(self.refermees)} refermée(s)"]
        if self.non_decidables:
            parts.append(
                f"{len(self.non_decidables)} NON DÉCIDABLE(S) (hors unité) : "
                + ", ".join(f"#{i}" for i in self.non_decidables)
            )
        if self.encore_possibles:
            parts.append(f"{len(self.encore_possibles)} encore dans le délai")
        if self.delai.perime:
            parts.append(
                "⚠ le délai de repli DIVERGE de l'unité "
                f"({self.delai.provenance}) — le reprendre"
            )
        return "exécutions interrompues : " + ", ".join(parts)


def refermer_executions_interrompues(
    db_session: Session, maintenant: datetime | None = None
) -> RapportInterruptions:
    """Ferme les lignes `en_cours` qui ne peuvent plus tourner. Ne lève jamais.

    **La déduction, et sa condition.** Au-delà du `TimeoutStartSec` de l'unité,
    une exécution démarrée PAR L'UNITÉ ne peut plus tourner : systemd l'aurait
    tuée. La condition est dans la phrase — elle ne vaut que sous l'unité. Une
    exécution lancée à la main n'est gouvernée par aucun délai, et il y en a eu
    beaucoup cette semaine; la conclure `interrompue` serait vrai sous une
    hypothèse jamais vérifiée.

    **Le délai se LIT**, il ne se recopie pas : il a valu 3 600, puis 10 800,
    puis 5 400 s, et chacune des deux premières valeurs a tué un cycle. Voir
    falkye/delai_unite.py — la valeur de repli porte sa provenance et se déclare
    périmée si elle diverge de ce que l'unité déclare.

    **Idempotente.** Ne referme que ce qui est ENCORE ouvert : une ligne
    refermée proprement entre-temps n'est jamais réécrite. Le `WHERE` porte sur
    `statut == en_cours` et `finished_at is None`, pas sur une liste calculée
    avant.
    """
    delai = delai_maximal()
    rapport = RapportInterruptions(delai=delai)
    if delai.secondes is None:
        # Délai infini ou illisible : aucune durée ne permet de conclure.
        # Ne rien refermer est la bonne réponse, et le dire est la seconde.
        logger.warning("%s", rapport.resume_lisible())
        return rapport

    maintenant = maintenant or datetime.now(timezone.utc).replace(tzinfo=None)
    limite = maintenant - timedelta(seconds=delai.secondes)

    ouvertes = (
        db_session.execute(
            select(SourceRunLog).where(
                SourceRunLog.statut == StatutExecution.EN_COURS.value,
                SourceRunLog.finished_at.is_(None),
            )
        )
        .scalars()
        .all()
    )

    for ligne in ouvertes:
        debut = ligne.started_at
        if debut is not None and debut.tzinfo is not None:
            debut = debut.replace(tzinfo=None)
        if debut is None or debut > limite:
            rapport.encore_possibles.append(ligne.id)
            continue
        if ligne.lance_par != Lancement.UNITE.value:
            rapport.non_decidables.append(ligne.id)
            continue
        ligne.statut = StatutExecution.INTERROMPUE.value
        ligne.finished_at = maintenant
        # Pas de `erreur` inventée : on ne sait PAS pourquoi. Le détail dit ce
        # qu'on sait — que le délai est dépassé — et rien de plus.
        ligne.erreur = (
            f"Aucune fin écrite au-delà du délai de l'unité ({int(delai.secondes)} s). "
            "Cause inconnue : la trace de la panne n'a pas pu être écrite."
        )
        rapport.refermees.append(ligne.id)

    if rapport.refermees:
        db_session.commit()
    if rapport.non_decidables or delai.perime:
        logger.warning("%s", rapport.resume_lisible())
    return rapport
