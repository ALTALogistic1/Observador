"""La distribution UNSPSC — les fonctions pures, testées sans base."""
from collections import Counter

from outils.distribution_unspsc import (
    PALIERS,
    _codes_pour_part,
    classifications_des_signaux,
    profondeur_unspsc,
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


def test_profondeur_un_code_entierement_renseigne():
    assert profondeur_unspsc("43211508") == 4


def test_profondeur_dun_segment_utilise_tel_quel():
    """`72000000` ne dit que son segment — les trois autres paires sont vides."""
    assert profondeur_unspsc("72000000") == 1


def test_profondeur_dun_code_arrete_a_la_famille():
    assert profondeur_unspsc("81100000") == 2


def test_profondeur_dun_code_arrete_a_la_classe():
    assert profondeur_unspsc("81101500") == 3


def test_profondeur_un_zero_interne_ne_coupe_pas_le_compte():
    """Seules les paires FINALES à 00 sont vides — une paire 00 au milieu compte."""
    assert profondeur_unspsc("81001501") == 4


def test_profondeur_rend_none_hors_huit_chiffres():
    assert profondeur_unspsc("8810") is None
    assert profondeur_unspsc("881015012") is None


def test_profondeur_ignore_la_ponctuation():
    assert profondeur_unspsc("72-00-00-00") == 1
