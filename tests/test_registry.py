"""Tests du registre lui-même — chargement, et le principe directeur non négociable
#3 ("aucune source n'est activée sans règle de calibration documentée")."""
import pytest

from observador.registry.loader import Registry, SourceDef, load_registry


def _source(id_, statut, regle_calibration=None):
    return SourceDef(
        id=id_,
        nom=id_,
        signal_associe=[],
        statut=statut,
        blocage_type=None,
        methode_acces=None,
        champs_pertinents=[],
        cout=None,
        region=None,
        connecteur=None,
        regle_calibration=regle_calibration,
    )


def test_registre_reel_se_charge_sans_erreur():
    registry = load_registry()
    assert len(registry.sources) > 0
    assert len(registry.sources_actives()) >= 3


def test_toutes_les_sources_actives_reelles_ont_une_regle_de_calibration():
    """Le registre réel du projet respecte déjà le principe #3 — pas seulement le
    mécanisme de validation en isolation (voir tests ci-dessous)."""
    registry = load_registry()
    registry.valider_calibration()  # ne doit lever aucune exception


def test_valider_calibration_leve_une_erreur_si_source_active_sans_regle():
    registry = Registry(sources={"x": _source("x", "actif", regle_calibration=None)})
    with pytest.raises(ValueError, match="x"):
        registry.valider_calibration()


def test_valider_calibration_ok_si_source_active_avec_regle():
    registry = Registry(sources={"x": _source("x", "actif", regle_calibration="règle documentée")})
    registry.valider_calibration()  # ne doit pas lever


def test_valider_calibration_ignore_les_sources_non_actives_sans_regle():
    registry = Registry(sources={"x": _source("x", "a_developper", regle_calibration=None)})
    registry.valider_calibration()  # une source a_developper peut ne pas avoir de règle
