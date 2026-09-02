"""Tests de l'interface générique des fournisseurs CRM (falkye/notifications/
crm/base.py) — intégration CRM (Radar et Radar+, ajoutée le 2026-09-02)."""
from falkye.models.crm_connection import CrmConnection
from falkye.models.profile import PlanTarifaire, Profile
from falkye.notifications.base import NotificationContent
from falkye.notifications.crm.base import (
    CrmProvider,
    CrmPushResult,
    CrmStatutDistant,
    mappage_effectif,
    proprietes_pour_mappage,
    valeurs_a_pousser,
)
from falkye.registry.loader import CrmProviderDef


class _FakeProvider(CrmProvider):
    """Implémentation minimale pour tester CrmProvider.resoudre_connexion sans
    dépendre d'un vrai fournisseur (hubspot/pipedrive)."""

    def pousser(self, connection, contenu, crm_object_id):
        return CrmPushResult(succes=True, crm_object_id="1")

    def tirer_statut(self, connection, crm_object_id):
        return CrmStatutDistant(succes=True, stage_brut=None)


def _provider_def(champs_mappage=None):
    return CrmProviderDef(
        id="hubspot", nom="HubSpot", statut="actif",
        module="falkye.notifications.crm.hubspot_channel", objet_crm_cible="companies",
        champs_mappage=champs_mappage or {},
    )


def _profile(plan=PlanTarifaire.RADAR, connexions=None):
    p = Profile(courriel="t@t.com", nom="T", plan=plan)
    p.connexions_crm = connexions or []
    return p


# --- CrmProvider.resoudre_connexion : gating Radar ET Radar+ (pas juste Radar+) ---


def test_resoudre_connexion_retourne_la_connexion_pour_radar():
    provider = _FakeProvider(provider_def=_provider_def())
    connexion = CrmConnection(profile_id=1, fournisseur="hubspot", jeton_api="jeton", actif=True)
    profile = _profile(plan=PlanTarifaire.RADAR, connexions=[connexion])
    assert provider.resoudre_connexion(profile) is connexion


def test_resoudre_connexion_retourne_la_connexion_pour_radar_plus():
    """Différent du webhook générique (réservé Radar+ seul) : le CRM est
    disponible dès Radar."""
    provider = _FakeProvider(provider_def=_provider_def())
    connexion = CrmConnection(profile_id=1, fournisseur="hubspot", jeton_api="jeton", actif=True)
    profile = _profile(plan=PlanTarifaire.RADAR_PLUS, connexions=[connexion])
    assert provider.resoudre_connexion(profile) is connexion


def test_resoudre_connexion_none_pour_echo():
    provider = _FakeProvider(provider_def=_provider_def())
    connexion = CrmConnection(profile_id=1, fournisseur="hubspot", jeton_api="jeton", actif=True)
    profile = _profile(plan=PlanTarifaire.ECHO, connexions=[connexion])
    assert provider.resoudre_connexion(profile) is None


def test_resoudre_connexion_none_sans_connexion_configuree():
    provider = _FakeProvider(provider_def=_provider_def())
    profile = _profile(plan=PlanTarifaire.RADAR, connexions=[])
    assert provider.resoudre_connexion(profile) is None


def test_resoudre_connexion_none_si_connexion_desactivee():
    provider = _FakeProvider(provider_def=_provider_def())
    connexion = CrmConnection(profile_id=1, fournisseur="hubspot", jeton_api="jeton", actif=False)
    profile = _profile(plan=PlanTarifaire.RADAR, connexions=[connexion])
    assert provider.resoudre_connexion(profile) is None


def test_resoudre_connexion_ignore_un_autre_fournisseur():
    provider = _FakeProvider(provider_def=_provider_def())
    connexion = CrmConnection(profile_id=1, fournisseur="pipedrive", jeton_api="jeton", actif=True)
    profile = _profile(plan=PlanTarifaire.RADAR, connexions=[connexion])
    assert provider.resoudre_connexion(profile) is None


# --- mappage_effectif : défaut du fournisseur, overrides de connexion gagnent ---


def test_mappage_effectif_retourne_le_defaut_sans_override():
    provider_def = _provider_def(champs_mappage={"neq": "falkye_neq"})
    connexion = CrmConnection(profile_id=1, fournisseur="hubspot", jeton_api="jeton")
    assert mappage_effectif(provider_def, connexion) == {"neq": "falkye_neq"}


def test_mappage_effectif_override_gagne_sur_le_defaut():
    """Nécessaire en pratique pour Pipedrive (clés de champ personnalisé
    propres à chaque compte client, voir registry/crm_providers.yaml)."""
    provider_def = _provider_def(champs_mappage={"neq": "falkye_neq", "nom": "name"})
    connexion = CrmConnection(
        profile_id=1, fournisseur="pipedrive", jeton_api="jeton",
        champs_mappage_override={"neq": "07a1b2c3d4e5"},
    )
    assert mappage_effectif(provider_def, connexion) == {"neq": "07a1b2c3d4e5", "nom": "name"}


# --- valeurs_a_pousser / proprietes_pour_mappage ---


def _contenu(sphere="efficacite_energetique", statut_id="a_joindre"):
    return NotificationContent(
        sujet="s", corps_texte="c",
        donnees_structurees={
            "entreprise": {"nom": "Entreprise Test", "neq": "1234567890", "ville": "Laval"},
            "sphere_probable_id": sphere,
            "score_pertinence": 80.0,
            "niveau_pertinence": "AA",
            "score_confiance": 70.0,
            "niveau_confiance": "eleve",
            "statut_suivi_id": statut_id,
        },
    )


def test_valeurs_a_pousser_extrait_les_champs_de_base():
    connexion = CrmConnection(profile_id=1, fournisseur="hubspot", jeton_api="jeton")
    valeurs = valeurs_a_pousser(_contenu(), connexion)
    assert valeurs["nom"] == "Entreprise Test"
    assert valeurs["neq"] == "1234567890"
    assert valeurs["sphere_probable_id"] == "efficacite_energetique"
    assert valeurs["score_pertinence"] == 80.0


def test_valeurs_a_pousser_statut_suivi_brut_sans_mapping():
    """Sans CrmConnection.mapping_statuts, le statut FALKYE brut est poussé tel
    quel — jamais bloqué par l'absence de correspondance."""
    connexion = CrmConnection(profile_id=1, fournisseur="hubspot", jeton_api="jeton")
    valeurs = valeurs_a_pousser(_contenu(statut_id="a_joindre"), connexion)
    assert valeurs["statut_suivi"] == "a_joindre"


def test_valeurs_a_pousser_statut_suivi_traduit_si_mapping_present():
    connexion = CrmConnection(
        profile_id=1, fournisseur="hubspot", jeton_api="jeton",
        mapping_statuts={"a_joindre": "Étape 1"},
    )
    valeurs = valeurs_a_pousser(_contenu(statut_id="a_joindre"), connexion)
    assert valeurs["statut_suivi"] == "Étape 1"


def test_valeurs_a_pousser_statut_suivi_none_sans_statut():
    connexion = CrmConnection(profile_id=1, fournisseur="hubspot", jeton_api="jeton")
    valeurs = valeurs_a_pousser(_contenu(statut_id=None), connexion)
    assert valeurs["statut_suivi"] is None


def test_proprietes_pour_mappage_ne_garde_que_les_champs_declares():
    valeurs = {"nom": "X", "neq": "123", "adresse": None}
    mappage = {"nom": "name", "neq": "falkye_neq", "adresse": "falkye_adresse"}
    # adresse=None n'est jamais poussé (jamais fabriquer/pousser une valeur vide)
    assert proprietes_pour_mappage(valeurs, mappage) == {"name": "X", "falkye_neq": "123"}


def test_proprietes_pour_mappage_ignore_un_champ_non_mappe():
    valeurs = {"nom": "X", "score_pertinence": 80.0}
    mappage = {"nom": "name"}
    assert proprietes_pour_mappage(valeurs, mappage) == {"name": "X"}
