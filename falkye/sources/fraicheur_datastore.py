"""Parcourir un datastore CKAN par ordre de PUBLICATION, et s'arrêter sur le déjà-vu.

**Le défaut que ce module ferme.** Deux connecteurs fédéraux — subventions et contrats
— filtraient sur la date de l'entente ou du contrat, triée décroissante, avec un
`return` au premier enregistrement hors fenêtre. **Or la divulgation proactive publie
des ententes commencées des mois plus tôt** : mesuré le 2026-09-14, la plus récente
date d'entente québécoise était le 2026-08-01 *(fenêtre au 15 août ⇒ zéro signal)*, et
la plus récente date de contrat réelle remontait à 53 jours.

**Il n'existe aucun champ de date de publication.** *`amendment_date` est remplie à
27,8 % sur les enregistrements récemment publiés — pas un axe.* **Le seul repère de
« neuf pour nous » est ce qu'on n'a pas déjà ingéré**, et le moteur le sait déjà :
`source_ref`.

**L'axe retenu : `_id desc`.** Mesuré le 2026-09-14 — trié ainsi, le datastore rend les
lignes les plus récemment chargées, dont les dates d'entente sont de mai-juin 2026.
*C'est exactement le décalage : de nouvelles publications portent des dates plus
anciennes.* **L'ordre d'insertion EST l'axe de fraîcheur que la source ne publie pas.**

**⚠️ RÉSERVE, à lire avant de s'y fier.** `_id` est **un artefact du datastore, pas une
donnée publiée**. Le tri croissant rend des ententes de 2021, donc la table paraît
**ajoutée en fin** plutôt que reconstruite — *mais c'est une inférence sur leur
processus de chargement, pas une garantie documentée*. **Si la ressource était un jour
rechargée en entier, l'ordre changerait sans prévenir** — et le connecteur deviendrait
muet exactement comme avant, sans erreur. *Le garde-fou est le compteur de pages
ci-dessous : un parcours qui va au bout sans rien reconnaître se signale.*

**La borne : `ARRET_APRES_CONNUS` références consécutives déjà en base.** *Décidée avec
Alexandre le 2026-09-14 : bornée et vérifiable, contre un balayage complet qui ferait
~475 appels pour le seul Québec — gratuit en quota, pas en temps.*
"""
from __future__ import annotations

import logging
from collections.abc import Callable, Iterator

logger = logging.getLogger(__name__)

#: Combien de références consécutives DÉJÀ CONNUES arrêtent le parcours.
#:
#: Pas 1 : une seule référence connue au milieu de nouveautés arrêterait tout — le
#: chargement de la source n'est pas garanti strictement chronologique, et un
#: enregistrement republié peut réapparaître parmi des neufs. Pas 1 000 non plus :
#: la borne perdrait son sens. **Cette valeur est un réglage assumé, pas une mesure**
#: — à revoir quand on saura combien de lignes une publication ajoute par semaine.
ARRET_APRES_CONNUS = 200

#: Combien de pages au maximum, quoi qu'il arrive. Filet contre la réserve ci-dessus :
#: si l'ordre `_id` cessait de correspondre à la publication, le parcours ne
#: reconnaîtrait plus rien et irait au bout de la source. **Il s'arrête et le DIT.**
PAGES_MAX = 40
TAILLE_PAGE = 500


def refs_connues(db_session, source_id: str, refs: list[str]) -> set[str]:
    """Celles de ces références qui sont déjà en base, pour cette source.

    Une seule requête par page, sur une colonne indexée (`signals.source_ref`).
    """
    if not refs:
        return set()
    from sqlalchemy import select

    from falkye.models.signal import Signal

    return set(
        db_session.execute(
            select(Signal.source_ref).where(
                Signal.source_id == source_id, Signal.source_ref.in_(refs)
            )
        ).scalars()
    )


def parcourir_par_publication(
    client,
    resource_id: str,
    source_id: str,
    db_session,
    construire_ref: Callable[[dict], str],
    filters: dict | None = None,
    limite: int | None = None,
) -> Iterator[dict]:
    """Les enregistrements NEUFS, du plus récemment publié au plus ancien.

    S'arrête quand `ARRET_APRES_CONNUS` références consécutives sont déjà en base, ou
    au bout de `PAGES_MAX` pages — **et dans ce second cas, il le journalise** : aller
    au bout sans rien reconnaître est le symptôme d'un `_id` qui a cessé de suivre la
    publication, pas d'une source prolifique.
    """
    connus_consecutifs = 0
    rendus = 0
    for page in range(PAGES_MAX):
        resultat = client.datastore_search(
            resource_id,
            filters=filters,
            sort="_id desc",
            limit=TAILLE_PAGE,
            offset=page * TAILLE_PAGE,
        )
        records = resultat.get("records", [])
        if not records:
            return

        refs = [construire_ref(rec) for rec in records]
        deja = refs_connues(db_session, source_id, refs)
        for rec, ref in zip(records, refs):
            if ref in deja:
                connus_consecutifs += 1
                if connus_consecutifs >= ARRET_APRES_CONNUS:
                    logger.info(
                        "%s : arrêt après %d références consécutives déjà connues "
                        "(%d enregistrement(s) neuf(s) rendu(s)).",
                        source_id, connus_consecutifs, rendus,
                    )
                    return
                continue
            connus_consecutifs = 0
            rendus += 1
            yield rec
            if limite is not None and rendus >= limite:
                return
    logger.warning(
        "%s : %d pages parcourues sans jamais atteindre %d références connues "
        "consécutives. Soit la source a beaucoup publié, soit l'ordre `_id` ne suit "
        "plus la publication — voir la réserve de falkye/sources/fraicheur_datastore.py.",
        source_id, PAGES_MAX, ARRET_APRES_CONNUS,
    )
