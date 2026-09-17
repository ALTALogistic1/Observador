#!/usr/bin/env python3
"""Les noms PUBLIÉS d'un NEQ, avec la table d'où chacun vient.

**Pourquoi une fonction partagée plutôt qu'une par outil.** Deux outils la
recopiaient déjà; un troisième l'aurait recopiée aussi. *Et la question qu'elle
répond — « d'où vient ce candidat » — est la même partout* : la dénomination
sociale élue (`req_entries`) ou un des autres noms en vigueur (`req_noms`), que
le chargeur jetait avant le 2026-09-16.

⚠️ **Aucun score n'est calculé ici.** *On MONTRE ce que le registre écrit; on ne
rejoue pas le scoreur.* **C'est précisément une recopie du scoreur qui a produit
les -338 du 2026-09-17**, et la leçon vaut aussi pour un affichage : un outil qui
rescorerait « pour savoir quelle forme a gagné » afficherait le gagnant de sa
copie, pas celui du moteur.
"""
from __future__ import annotations

TABLE_ELUE = "req_entries (dénomination élue)"
TABLE_AUTRE = "req_noms (autre nom)"


def formes_publiees(db_session, neqs: list[str]) -> list[tuple[str, str, str]]:
    """Pour un lot de NEQ, la liste des `(neq, nom publié, table)`.

    L'ordre est stable — les dénominations élues d'abord, puis les autres noms,
    chacune triée — *pour que deux exécutions du même diagnostic se lisent
    côte à côte.*
    """
    from sqlalchemy import select

    from falkye.models.req_entry import REQEntry
    from falkye.models.req_nom import REQNom

    if not neqs:
        return []
    formes: list[tuple[str, str, str]] = []
    for neq, nom in db_session.execute(
        select(REQEntry.neq, REQEntry.nom)
        .where(REQEntry.neq.in_(neqs))
        .order_by(REQEntry.neq)
    ).all():
        formes.append((neq, nom or "", TABLE_ELUE))
    for neq, nom in db_session.execute(
        select(REQNom.neq, REQNom.nom)
        .where(REQNom.neq.in_(neqs))
        .order_by(REQNom.neq, REQNom.nom_normalise)
    ).all():
        formes.append((neq, nom or "", TABLE_AUTRE))
    return formes
