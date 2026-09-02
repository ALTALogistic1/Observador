"""Tests du registre lui-même — chargement, et le principe directeur non négociable
#3 ("aucune source n'est activée sans règle de calibration documentée")."""
import pytest

from falkye.registry.loader import ChampsPertinentsDef, Registry, SourceDef, StatutSuiviDef, load_registry


def _source(id_, statut, regle_calibration=None, plan_minimum="echo"):
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
        plan_minimum=plan_minimum,
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


# --- Structure de plans tarifaires (spec section 9bis) ---


def test_plan_minimum_par_defaut_est_echo():
    source = _source("x", "actif")
    assert source.plan_minimum == "echo"
    assert source.disponible_pour_plan("echo")


def test_source_echo_disponible_pour_tous_les_plans():
    source = _source("x", "actif", plan_minimum="echo")
    assert source.disponible_pour_plan("echo")
    assert source.disponible_pour_plan("radar")
    assert source.disponible_pour_plan("radar_plus")


def test_source_radar_indisponible_pour_echo_mais_disponible_pour_radar_plus():
    source = _source("x", "actif", plan_minimum="radar")
    assert not source.disponible_pour_plan("echo")
    assert source.disponible_pour_plan("radar")
    assert source.disponible_pour_plan("radar_plus")


def test_source_radar_plus_disponible_seulement_pour_radar_plus():
    source = _source("x", "actif", plan_minimum="radar_plus")
    assert not source.disponible_pour_plan("echo")
    assert not source.disponible_pour_plan("radar")
    assert source.disponible_pour_plan("radar_plus")


# --- Statuts de suivi du tableau de bord (spec section 4bis) ---


def test_registre_reel_a_un_seul_statut_par_defaut():
    registry = load_registry()
    defaut = registry.statut_suivi_par_defaut()
    assert defaut.id == "a_joindre"


def test_registre_reel_a_pas_pertinent_comme_declencheur_de_retroaction():
    registry = load_registry()
    ids = {s.id for s in registry.statuts_suivi_declencheurs_retroaction()}
    assert ids == {"pas_pertinent"}


def test_statut_suivi_par_defaut_leve_si_aucun_defaut_declare():
    registry = Registry(statuts_suivi={"x": StatutSuiviDef(id="x", nom="X", est_defaut=False)})
    with pytest.raises(ValueError, match="défaut"):
        registry.statut_suivi_par_defaut()


def test_load_registry_leve_si_aucun_statut_par_defaut_dans_le_yaml(monkeypatch):
    """La validation d'unicité du défaut se fait au chargement (load_registry),
    pas seulement via l'API — un registre mal formé ne doit jamais se charger
    silencieusement avec zéro ou plusieurs défauts."""
    import falkye.registry.loader as loader_module

    vraie_charge = loader_module._load_yaml

    def _charge_avec_statuts_casses(filename):
        if filename == "statuts_suivi.yaml":
            return {"statuts_suivi": [{"id": "a", "nom": "A", "est_defaut": False}]}
        return vraie_charge(filename)

    monkeypatch.setattr(loader_module, "_load_yaml", _charge_avec_statuts_casses)
    with pytest.raises(ValueError, match="statuts_suivi"):
        loader_module.load_registry()


# --- Grille de pertinence par champ (spec section 6, "Filtrage par champ,
# contextuel au profil") ---


def test_registre_reel_a_une_grille_pour_efficacite_energetique_req():
    registry = load_registry()
    assert registry.champs_pertinents_pour("efficacite_energetique", "req") == [
        "secteur_code", "secteur_libelle",
    ]


def test_champs_pertinents_pour_retourne_none_sans_entree_declaree():
    """Défaut sûr : aucune entrée déclarée = aucun filtrage, jamais une perte
    de donnée par simple omission de registre."""
    registry = Registry(
        champs_pertinents={
            ("energie", "req"): ChampsPertinentsDef(
                sphere_id="energie", source_id="req", champs_pertinents=["secteur_code"]
            )
        }
    )
    assert registry.champs_pertinents_pour("gestion_projet", "req") is None
    assert registry.champs_pertinents_pour("energie", "seao") is None


def test_champs_pertinents_pour_retourne_la_liste_declaree():
    registry = Registry(
        champs_pertinents={
            ("energie", "req"): ChampsPertinentsDef(
                sphere_id="energie", source_id="req", champs_pertinents=["secteur_code", "secteur_libelle"]
            )
        }
    )
    assert registry.champs_pertinents_pour("energie", "req") == ["secteur_code", "secteur_libelle"]
