"""L'axe de fraîcheur : l'ordre de publication, borné par le déjà-vu.

Deux connecteurs fédéraux filtraient sur la date de l'entente ou du contrat, triée
décroissante, avec un `return` au premier enregistrement hors fenêtre. **Or la
divulgation proactive publie des ententes commencées des mois plus tôt** : zéro signal,
trois secondes, un succès. Et chez les contrats, deux dates FUTURES en tête du tri
produisaient les deux seuls signaux de la source.
"""
from __future__ import annotations

from datetime import datetime

import pytest

from falkye.sources.fraicheur_datastore import (
    ARRET_APRES_CONNUS,
    PAGES_MAX,
    TAILLE_PAGE,
    parcourir_par_publication,
    refs_connues,
)


class _ClientFactice:
    """Un datastore qui rend des pages, et qui NOTE le tri qu'on lui demande."""

    def __init__(self, records):
        self.records, self.tris, self.appels = records, [], 0

    def datastore_search(self, resource_id, filters=None, sort=None, limit=None, offset=0):
        self.tris.append(sort)
        self.appels += 1
        return {"records": self.records[offset : offset + (limit or TAILLE_PAGE)]}


def _rec(n):
    return {"reference_number": f"r{n}"}


def _ref(rec):
    return f"essai:{rec['reference_number']}"


def test_le_tri_demande_est_lordre_de_PUBLICATION(db_session):
    client = _ClientFactice([_rec(i) for i in range(3)])

    list(parcourir_par_publication(client, "res", "essai", db_session, _ref))

    assert client.tris[0] == "_id desc"


def test_tout_est_neuf_quand_la_base_est_vide(db_session):
    client = _ClientFactice([_rec(i) for i in range(5)])

    rendus = list(parcourir_par_publication(client, "res", "essai", db_session, _ref))

    assert len(rendus) == 5


def test_la_limite_borne_le_parcours(db_session):
    client = _ClientFactice([_rec(i) for i in range(50)])

    rendus = list(parcourir_par_publication(client, "res", "essai", db_session, _ref, limite=7))

    assert len(rendus) == 7


def test_il_sarrete_apres_assez_de_refs_CONSECUTIVES_deja_connues(db_session):
    """La borne décidée avec Alexandre : bornée et vérifiable, contre un balayage
    complet qui ferait ~475 appels pour le seul Québec."""
    from falkye.models.company import Company
    from falkye.models.signal import Signal

    c = Company(nom_detecte="X", nom_detecte_normalise="x")
    db_session.add(c)
    db_session.flush()
    total = ARRET_APRES_CONNUS + 40
    for i in range(total):
        db_session.add(
            Signal(company_id=c.id, source_id="essai", signal_type_id="appel_offres",
                   detected_at=datetime.now(), source_ref=_ref(_rec(i)), champs={})
        )
    db_session.commit()
    client = _ClientFactice([_rec(i) for i in range(total)])

    rendus = list(parcourir_par_publication(client, "res", "essai", db_session, _ref))

    assert rendus == []


def test_un_seul_connu_au_milieu_de_neufs_NARRETE_PAS(db_session):
    """Pas 1 : le chargement de la source n'est pas garanti strictement
    chronologique, et un enregistrement republié peut réapparaître parmi des neufs."""
    from falkye.models.company import Company
    from falkye.models.signal import Signal

    c = Company(nom_detecte="X", nom_detecte_normalise="x")
    db_session.add(c)
    db_session.flush()
    db_session.add(
        Signal(company_id=c.id, source_id="essai", signal_type_id="appel_offres",
               detected_at=datetime.now(), source_ref=_ref(_rec(1)), champs={})
    )
    db_session.commit()
    client = _ClientFactice([_rec(i) for i in range(5)])

    rendus = list(parcourir_par_publication(client, "res", "essai", db_session, _ref))

    assert len(rendus) == 4  # les quatre neufs, le connu sauté


def test_le_parcours_est_borne_en_PAGES_meme_si_rien_nest_reconnu(db_session):
    """Le filet contre la réserve : si l'ordre `_id` cessait de suivre la
    publication, le parcours ne reconnaîtrait plus rien et irait au bout."""
    client = _ClientFactice([_rec(i) for i in range((PAGES_MAX + 5) * TAILLE_PAGE)])

    list(parcourir_par_publication(client, "res", "essai", db_session, _ref))

    assert client.appels == PAGES_MAX


def test_refs_connues_ne_confond_pas_les_sources(db_session):
    from falkye.models.company import Company
    from falkye.models.signal import Signal

    c = Company(nom_detecte="X", nom_detecte_normalise="x")
    db_session.add(c)
    db_session.flush()
    db_session.add(
        Signal(company_id=c.id, source_id="autre", signal_type_id="appel_offres",
               detected_at=datetime.now(), source_ref="essai:r1", champs={})
    )
    db_session.commit()

    assert refs_connues(db_session, "essai", ["essai:r1"]) == set()
    assert refs_connues(db_session, "essai", []) == set()


@pytest.mark.parametrize("module", ("subventions_federales", "contrats_federaux"))
def test_la_cle_nest_ecrite_QUUNE_fois(module):
    """Écrite deux fois — une pour le signal, une pour le parcours — une divergence
    d'un caractère ferait tout reparcourir à chaque cycle sans jamais rien
    reconnaître, et le connecteur paraîtrait simplement lent."""
    import importlib
    import inspect

    source = inspect.getsource(importlib.import_module(f"falkye.sources.{module}"))

    assert source.count(f'f"{module}:') == 1
    assert "construire_ref=source_ref_pour" in source
