"""Tests du registre lui-même — chargement, et le principe directeur non négociable
#3 ("aucune source n'est activée sans règle de calibration documentée")."""
import pytest

from falkye.registry.loader import (
    ChampsPertinentsDef,
    CrmProviderDef,
    Registry,
    SecteurGrossierDef,
    SourceDef,
    StatutSuiviDef,
    load_registry,
)


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


# --- Fournisseurs CRM (intégration CRM, ajoutée le 2026-09-02) ---


def test_registre_reel_a_hubspot_et_pipedrive_actifs():
    registry = load_registry()
    ids = {p.id for p in registry.fournisseurs_crm_actifs()}
    assert ids == {"hubspot", "pipedrive"}


def test_registre_reel_hubspot_a_un_mappage_par_defaut_avec_statut_suivi():
    registry = load_registry()
    hubspot = registry.fournisseur_crm("hubspot")
    assert hubspot is not None
    assert "statut_suivi" in hubspot.champs_mappage
    assert hubspot.champs_mappage["neq"] == "falkye_neq"


def test_registre_reel_hubspot_et_pipedrive_ont_domaine_type_et_avantage_concret():
    """Format standard des cartes de source à l'étape de connexion, portail
    Radar/Radar+ (spec section 9bis, ajoutée le 2026-09-02) — jamais un nom de
    marque seul. Texte exact du tableau de référence de la spec."""
    registry = load_registry()

    hubspot = registry.fournisseur_crm("hubspot")
    assert hubspot.domaine_type == "CRM marketing + vente unifiés"
    assert hubspot.avantage_concret == (
        "Pour unifier marketing et vente, ou si vous faites déjà du marketing entrant"
    )

    pipedrive = registry.fournisseur_crm("pipedrive")
    assert pipedrive.domaine_type == "CRM vente pure"
    assert pipedrive.avantage_concret == (
        "Simple et rapide à configurer, abordable, pour une équipe de vente sans marketing intégré"
    )


def test_fournisseur_crm_retourne_none_pour_un_id_inconnu():
    registry = load_registry()
    assert registry.fournisseur_crm("salesforce") is None


def test_fournisseurs_crm_actifs_exclut_un_fournisseur_a_developper():
    registry = Registry(
        crm_providers={
            "x": CrmProviderDef(id="x", nom="X", statut="a_developper", module=None, objet_crm_cible=None),
            "y": CrmProviderDef(id="y", nom="Y", statut="actif", module=None, objet_crm_cible=None),
        }
    )
    assert [p.id for p in registry.fournisseurs_crm_actifs()] == ["y"]


# --- Regroupement grossier de secteurs REQ (tableaux de bord, solution
# intermédiaire ajoutée le 2026-09-02) ---


def test_registre_reel_a_des_categories_de_secteurs_grossiers():
    registry = load_registry()
    assert len(registry.secteurs_grossiers) > 0


def test_classer_secteur_retourne_none_si_libelle_vide_ou_absent():
    registry = load_registry()
    assert registry.classer_secteur(None) is None
    assert registry.classer_secteur("") is None


def test_classer_secteur_retourne_none_si_aucune_categorie_ne_matche():
    """Jamais forcé dans une catégorie approximative — principe directeur #1."""
    registry = load_registry()
    assert registry.classer_secteur("xyz totalement hors des catégories connues") is None


def test_classer_secteur_reconnait_un_libelle_reel_de_fabrication():
    registry = load_registry()
    assert registry.classer_secteur("FABRICATION D'ASPIRATEUR CENTRAL") == "fabrication"


def test_classer_secteur_premiere_categorie_qui_matche_gagne():
    registry = Registry(
        secteurs_grossiers=[
            SecteurGrossierDef(id="a", nom="A", mots_cles=["fabricat"]),
            SecteurGrossierDef(id="b", nom="B", mots_cles=["construction"]),
        ]
    )
    # Matche les deux motifs — la catégorie déclarée en premier dans la liste gagne.
    assert registry.classer_secteur("FABRICATION ET DISTRIBUTION DE MATÉRIAUX DE CONSTRUCTION") == "a"


def test_secteur_grossier_retourne_none_pour_un_id_inconnu():
    registry = load_registry()
    assert registry.secteur_grossier("id_inexistant_xyz") is None


def test_secteur_grossier_retourne_la_definition_declaree():
    registry = Registry(secteurs_grossiers=[SecteurGrossierDef(id="a", nom="A", mots_cles=["x"])])
    assert registry.secteur_grossier("a").nom == "A"


# --- province_code (spec Radar+, point 7, ajouté le 2026-09-03) ---


def test_province_code_par_defaut_est_none():
    source = _source("x", "actif")
    assert source.province_code is None


def test_registre_reel_a_les_quatre_sources_provinciales_attendues():
    """Régression du bogue YAML réel trouvé en construisant cette grille : "on"
    (Ontario) nu est lu comme booléen True par PyYAML (YAML 1.1) — doit rester
    quoté ("on") dans sources.yaml, sinon licences_toronto.province_code
    devient True au lieu de "on"."""
    registry = load_registry()
    codes = {
        source_id: s.province_code for source_id, s in registry.sources.items() if s.province_code
    }
    assert codes == {
        "req": "qc",
        "contrats_nouvelle_ecosse": "ns",
        "licences_vancouver": "bc",
        "licences_toronto": "on",
    }
    assert all(isinstance(code, str) for code in codes.values())


# --- Retrait de "gestion_inventaire_actifs" (correction d'architecture, 2026-09-03) ---


def test_gestion_inventaire_actifs_retiree_du_registre_des_spheres():
    """Ce n'était pas une catégorie de besoin générique mais un service précis
    (le cas d'usage d'origine du projet) — retirée au profit d'un rattachement
    par l'assistance IA à deux paliers (falkye/assistance_sphere.py /
    falkye/assistance_sphere_ia.py). Régression : aucun dangling id ne doit
    subsister nulle part dans le registre."""
    registry = load_registry()
    assert "gestion_inventaire_actifs" not in registry.spheres

    signal_type = registry.signal_type("financement_expansion")
    assert "gestion_inventaire_actifs" not in signal_type.spheres_probables


# --- Registre clients_cibles.yaml (spec section 8bis, 2026-09-03) ---


def test_registre_reel_a_l_entree_sentinelle_aucune_restriction():
    from falkye.models.client_cible import ID_AUCUNE_RESTRICTION

    registry = load_registry()
    assert ID_AUCUNE_RESTRICTION in registry.clients_cibles


def test_registre_reel_a_une_categorie_institutionnelle_publique():
    """Ajoutée en réponse directe au gap trouvé contre le vrai miroir REQ —
    voir docs/ARCHITECTURE.md."""
    registry = load_registry()
    assert "organismes_publics_institutionnels" in registry.clients_cibles


def test_client_cible_retourne_none_pour_un_id_inconnu():
    registry = load_registry()
    assert registry.client_cible("id_inexistant_xyz") is None
