"""Tableaux de bord agrégés par territoire — spec section 4bis, fonctionnalité
Radar+ "au-delà des prospects un à un, une vue agrégée ('X entreprises en
croissance détectées dans votre région ce trimestre, réparties par secteur') —
sert un besoin concret de reddition de comptes pour des personas comme le
développement économique régional, qui doivent justifier leur propre impact à
un conseil ou à un palier gouvernemental."

Logique PURE côté DB (aucun accès DB ici) — prend une liste de Notification
déjà chargée (avec ses relations `company`/`profile_need`) et produit un
résumé agrégé. La requête DB (période, filtre territoire) reste dans
falkye/cli.py::dashboard_synthese, comme pour falkye/carte.py::
generer_carte_html. `registry` (paramètre, comme falkye/pertinence.py::
calculer_pertinence) sert au regroupement grossier par secteur ci-dessous —
config en mémoire, pas un accès DB.

RÉPARTITION PAR SECTEUR — solution INTERMÉDIAIRE ajoutée le 2026-09-02
(demande d'Alexandre) : `Company.secteur_activite_libelle` (texte libre du
REQ) est trop granulaire pour être utile agrégé tel quel — LIMITE déjà
documentée (docs/STATUT_RESEAU.md, "Portail Radar/Radar+ construit contre un
premier cas concret") : ~211 valeurs quasi toutes distinctes sur 311
notifications réelles. Un regroupement par les libellés les PLUS FRÉQUENTS
littéralement ne fonctionne pas non plus (vérifié : le top 20 des libellés
exacts ne couvre que ~10% des notifications avec secteur — presque aucun ne
se répète mot pour mot). `par_secteur` regroupe donc par MOTS-CLÉS récurrents
(`registry/secteurs_grossiers.yaml`, `Registry.classer_secteur`) — ~75%
classés contre la base réelle, le reste honnêtement "(non classé)" plutôt que
forcé. `par_secteur_detail` garde le libellé brut (granularité d'origine,
jamais perdue) pour qui veut inspecter ce qui tombe dans "(non classé)". PAS
un remplacement du SCIAN/NAICS — un vrai regroupement par code SCIAN reste
l'amélioration future si le volume de notifications justifie
l'investissement (voir docs/ARCHITECTURE.md)."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from falkye.models.notification import Notification
from falkye.registry.loader import Registry

SECTEUR_NON_PRECISE = "(non précisé)"
SECTEUR_NON_CLASSE = "(non classé)"
TERRITOIRE_AUCUN = "(aucun territoire assigné)"


@dataclass
class SyntheseAgregee:
    nb_entreprises: int  # distinctes, pas le nombre de notifications
    par_secteur: Counter = field(default_factory=Counter)  # regroupement grossier (mots-clés)
    par_secteur_detail: Counter = field(default_factory=Counter)  # libellé REQ brut, granularité d'origine
    par_niveau_pertinence: Counter = field(default_factory=Counter)
    par_territoire: Counter = field(default_factory=Counter)


def generer_synthese(notifications: list[Notification], registry: Registry) -> SyntheseAgregee:
    """Une entreprise comptée UNE SEULE FOIS même si plusieurs notifications
    existent pour elle dans la période (ex. plusieurs signaux détectés à des
    moments différents) — "X entreprises détectées", pas "X notifications"."""
    par_secteur: Counter = Counter()
    par_secteur_detail: Counter = Counter()
    par_niveau: Counter = Counter()
    par_territoire: Counter = Counter()
    entreprises_vues: set[int] = set()

    for n in notifications:
        if n.company_id in entreprises_vues:
            continue
        entreprises_vues.add(n.company_id)

        libelle_brut = n.company.secteur_activite_libelle
        par_secteur_detail[libelle_brut or SECTEUR_NON_PRECISE] += 1

        if not libelle_brut:
            par_secteur[SECTEUR_NON_PRECISE] += 1
        else:
            categorie_id = registry.classer_secteur(libelle_brut)
            if categorie_id is None:
                par_secteur[SECTEUR_NON_CLASSE] += 1
            else:
                categorie = registry.secteur_grossier(categorie_id)
                par_secteur[categorie.nom if categorie else categorie_id] += 1

        niveau = n.niveau_pertinence.value if n.niveau_pertinence else "n/d (historique)"
        par_niveau[niveau] += 1

        territoire = (n.profile_need.territoire if n.profile_need else None) or TERRITOIRE_AUCUN
        par_territoire[territoire] += 1

    return SyntheseAgregee(
        nb_entreprises=len(entreprises_vues),
        par_secteur=par_secteur,
        par_secteur_detail=par_secteur_detail,
        par_niveau_pertinence=par_niveau,
        par_territoire=par_territoire,
    )
