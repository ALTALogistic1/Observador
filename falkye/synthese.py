"""Tableaux de bord agrégés par territoire — spec section 4bis, fonctionnalité
Radar+ "au-delà des prospects un à un, une vue agrégée ('X entreprises en
croissance détectées dans votre région ce trimestre, réparties par secteur') —
sert un besoin concret de reddition de comptes pour des personas comme le
développement économique régional, qui doivent justifier leur propre impact à
un conseil ou à un palier gouvernemental."

Logique PURE (aucun accès DB ici) — prend une liste de Notification déjà
chargée (avec ses relations `company`/`profile_need`) et produit un résumé
agrégé. La requête DB (période, filtre territoire) reste dans
falkye/cli.py::dashboard_synthese, comme pour falkye/carte.py::
generer_carte_html."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from falkye.models.notification import Notification

SECTEUR_NON_PRECISE = "(non précisé)"
TERRITOIRE_AUCUN = "(aucun territoire assigné)"


@dataclass
class SyntheseAgregee:
    nb_entreprises: int  # distinctes, pas le nombre de notifications
    par_secteur: Counter = field(default_factory=Counter)
    par_niveau_pertinence: Counter = field(default_factory=Counter)
    par_territoire: Counter = field(default_factory=Counter)


def generer_synthese(notifications: list[Notification]) -> SyntheseAgregee:
    """Une entreprise comptée UNE SEULE FOIS même si plusieurs notifications
    existent pour elle dans la période (ex. plusieurs signaux détectés à des
    moments différents) — "X entreprises détectées", pas "X notifications"."""
    par_secteur: Counter = Counter()
    par_niveau: Counter = Counter()
    par_territoire: Counter = Counter()
    entreprises_vues: set[int] = set()

    for n in notifications:
        if n.company_id in entreprises_vues:
            continue
        entreprises_vues.add(n.company_id)

        secteur = n.company.secteur_activite_libelle or SECTEUR_NON_PRECISE
        par_secteur[secteur] += 1

        niveau = n.niveau_pertinence.value if n.niveau_pertinence else "n/d (historique)"
        par_niveau[niveau] += 1

        territoire = (n.profile_need.territoire if n.profile_need else None) or TERRITOIRE_AUCUN
        par_territoire[territoire] += 1

    return SyntheseAgregee(
        nb_entreprises=len(entreprises_vues),
        par_secteur=par_secteur,
        par_niveau_pertinence=par_niveau,
        par_territoire=par_territoire,
    )
