"""La distribution UNSPSC — les fonctions pures, testées sans base."""
from collections import Counter

import pytest

from outils.distribution_unspsc import (
    PALIERS,
    classifications_des_signaux,
    _codes_pour_part,
    tronquer,
)


class _SignalFactice:
    def __init__(self, champs):
        self.champs = champs


class _ScalarsFactice:
    def __init__(self, valeurs):
        self._valeurs = valeurs

    def scalars(self):
        return self

    def all(self):
        return self._valeurs


class _SessionFactice:
    def __init__(self, signaux):
        self._signaux = signaux

    def execute(self, _requete):
        return _ScalarsFactice(self._signaux)


def test_tronquer_rend_le_prefixe_hierarchique():
    assert tronquer("88101501", 8) == "88101501"
    assert tronquer("88101501", 6) == "881015"
    assert tronquer("88101501", 4) == "8810"
    assert tronquer("88101501", 2) == "88"


def test_un_code_trop_court_nest_JAMAIS_complete_par_des_zeros():
    """Compléter inventerait une position dans la hiérarchie."""
    assert tronquer("8810", 8) is None
    assert tronquer("8810", 4) == "8810"


def test_tronquer_ignore_la_ponctuation_du_code():
    assert tronquer("88-10-15-01", 4) == "8810"


def test_codes_pour_part_compte_les_entrees_dune_table_a_la_main():
    compte = Counter({"a": 80, "b": 10, "c": 5, "d": 5})
    assert _codes_pour_part(compte, 100, 80.0) == 1
    assert _codes_pour_part(compte, 100, 95.0) == 3


def test_codes_pour_part_sur_une_distribution_plate():
    compte = Counter({chr(97 + i): 1 for i in range(100)})
    assert _codes_pour_part(compte, 100, 80.0) == 80


def test_un_signal_portant_trois_codes_produit_trois_entrees():
    signal = _SignalFactice({"secteur_nature_contrat": [
        {"code": "88101501", "libelle": "A", "scheme": "UNSPSC"},
        {"code": "88101502", "libelle": "B", "scheme": "UNSPSC"},
        {"code": "72000000", "libelle": "C", "scheme": "UNSPSC"},
    ]})
    entrees, nb, sans = classifications_des_signaux(_SessionFactice([signal]))
    assert len(entrees) == 3
    assert nb == 1        # un signal
    assert sans == 0


def test_les_signaux_sans_classification_sont_comptes_a_part():
    signaux = [
        _SignalFactice({"secteur_nature_contrat": [{"code": "88101501"}]}),
        _SignalFactice({"secteur_nature_contrat": []}),
        _SignalFactice({}),
        _SignalFactice(None),
    ]
    entrees, nb, sans = classifications_des_signaux(_SessionFactice(signaux))
    assert (len(entrees), nb, sans) == (1, 4, 3)


def test_une_entree_sans_code_est_ignoree_sans_lever():
    signal = _SignalFactice({"secteur_nature_contrat": [{"libelle": "sans code"}, "pas un dict"]})
    entrees, _, sans = classifications_des_signaux(_SessionFactice([signal]))
    assert entrees == []
    assert sans == 0      # il PORTE une classification, elle est juste inexploitable


def test_les_quatre_paliers_de_la_hierarchie_sont_declares():
    assert sorted(PALIERS) == [2, 4, 6, 8]
