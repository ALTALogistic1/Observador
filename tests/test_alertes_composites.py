"""Tests des alertes composites préconfigurées (falkye/alertes_composites.py) —
spec section 4bis, remplace l'ancienne pondération par curseur générique."""
from falkye.alertes_composites import ALERTES_COMPOSITES, alerte_composite
from falkye.pertinence import PONDERATION_DEFAUT


def test_trois_presets_disponibles():
    assert set(ALERTES_COMPOSITES.keys()) == {
        "alerte_cautionnement", "alerte_financement_precoce", "alerte_acquisition",
    }


def test_alerte_composite_retourne_none_pour_id_inconnu():
    assert alerte_composite("inexistant") is None


def test_alerte_cautionnement_favorise_la_velocite():
    a = alerte_composite("alerte_cautionnement")
    assert a.ponderation.bonus_velocite_max > PONDERATION_DEFAUT.bonus_velocite_max
    # Les autres leviers restent aux valeurs par défaut — seule la vélocité change.
    assert a.ponderation.bonus_absence == PONDERATION_DEFAUT.bonus_absence
    assert a.ponderation.base_aaa == PONDERATION_DEFAUT.base_aaa


def test_alerte_financement_precoce_favorise_l_absence():
    a = alerte_composite("alerte_financement_precoce")
    assert a.ponderation.bonus_absence > PONDERATION_DEFAUT.bonus_absence
    assert a.ponderation.bonus_velocite_max == PONDERATION_DEFAUT.bonus_velocite_max


def test_alerte_acquisition_favorise_la_precision_de_sphere_et_la_velocite():
    a = alerte_composite("alerte_acquisition")
    assert a.ponderation.base_aaa > PONDERATION_DEFAUT.base_aaa
    assert a.ponderation.bonus_velocite_max > PONDERATION_DEFAUT.bonus_velocite_max
    assert a.ponderation.bonus_absence < PONDERATION_DEFAUT.bonus_absence


def test_chaque_preset_a_un_nom_et_une_description_non_vides():
    for a in ALERTES_COMPOSITES.values():
        assert a.nom
        assert a.description
