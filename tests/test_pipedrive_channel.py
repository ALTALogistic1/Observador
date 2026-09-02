"""Tests du client CRM Pipedrive (falkye/notifications/crm/pipedrive_channel.py)
— intégration CRM (Radar et Radar+, ajoutée le 2026-09-02). Mocks HTTP via
`responses` — aucun accès réseau vers la vraie API Pipedrive dans cet
environnement (même situation que TheirStack/Stripe/géocodage)."""
import json

import responses

from falkye.models.crm_connection import CrmConnection
from falkye.notifications.base import NotificationContent
from falkye.notifications.crm.pipedrive_channel import PipedriveProvider
from falkye.registry.loader import get_registry


def _provider():
    registry = get_registry()
    return PipedriveProvider(provider_def=registry.fournisseur_crm("pipedrive"))


def _connexion(**kwargs):
    kwargs.setdefault("profile_id", 1)
    kwargs.setdefault("fournisseur", "pipedrive")
    kwargs.setdefault("jeton_api", "jeton-test")
    return CrmConnection(**kwargs)


def _contenu():
    return NotificationContent(
        sujet="s", corps_texte="c",
        donnees_structurees={
            "entreprise": {"nom": "Entreprise Test", "neq": "1234567890"},
            "sphere_probable_id": "efficacite_energetique",
            "score_pertinence": 80.0,
            "niveau_pertinence": "AA",
            "score_confiance": 70.0,
            "niveau_confiance": "eleve",
            "statut_suivi_id": "a_joindre",
        },
    )


@responses.activate
def test_pousser_cree_un_nouvel_objet_si_aucun_id_connu():
    responses.add(
        responses.POST, "https://api.pipedrive.com/v1/organizations",
        json={"success": True, "data": {"id": 99}}, status=201,
    )
    provider = _provider()
    result = provider.pousser(_connexion(), _contenu(), None)

    assert result.succes is True
    assert result.crm_object_id == "99"
    body = json.loads(responses.calls[0].request.body)
    assert body["name"] == "Entreprise Test"
    assert body["falkye_neq"] == "1234567890"
    assert responses.calls[0].request.params.get("api_token") == "jeton-test"


@responses.activate
def test_pousser_met_a_jour_un_objet_existant_via_put():
    responses.add(
        responses.PUT, "https://api.pipedrive.com/v1/organizations/99",
        json={"success": True, "data": {"id": 99}}, status=200,
    )
    provider = _provider()
    result = provider.pousser(_connexion(), _contenu(), "99")

    assert result.succes is True
    assert result.crm_object_id == "99"
    assert responses.calls[0].request.method == "PUT"


@responses.activate
def test_pousser_utilise_le_mappage_override_de_la_connexion():
    """Nécessaire en pratique pour Pipedrive : les clés de champ personnalisé
    sont des hachages propres à chaque compte client (voir registry/
    crm_providers.yaml)."""
    responses.add(
        responses.POST, "https://api.pipedrive.com/v1/organizations",
        json={"success": True, "data": {"id": 99}}, status=201,
    )
    provider = _provider()
    connexion = _connexion(champs_mappage_override={"neq": "07a1b2c3d4e5"})
    provider.pousser(connexion, _contenu(), None)

    body = json.loads(responses.calls[0].request.body)
    assert body["07a1b2c3d4e5"] == "1234567890"
    assert "falkye_neq" not in body


@responses.activate
def test_pousser_echoue_proprement_sur_erreur_http():
    responses.add(responses.POST, "https://api.pipedrive.com/v1/organizations", status=401)
    provider = _provider()
    result = provider.pousser(_connexion(), _contenu(), None)
    assert result.succes is False
    assert result.erreur is not None


@responses.activate
def test_tirer_statut_lit_le_champ_mappe():
    responses.add(
        responses.GET, "https://api.pipedrive.com/v1/organizations/99",
        json={"success": True, "data": {"falkye_statut_suivi": "Contacté"}}, status=200,
    )
    provider = _provider()
    resultat = provider.tirer_statut(_connexion(), "99")
    assert resultat.succes is True
    assert resultat.stage_brut == "Contacté"


@responses.activate
def test_tirer_statut_echoue_proprement_sur_erreur_http():
    responses.add(responses.GET, "https://api.pipedrive.com/v1/organizations/99", status=500)
    provider = _provider()
    resultat = provider.tirer_statut(_connexion(), "99")
    assert resultat.succes is False
    assert resultat.erreur is not None


def test_tirer_statut_retourne_succes_sans_stage_si_pas_de_mappage_statut():
    from falkye.registry.loader import CrmProviderDef

    provider_def_sans_statut = CrmProviderDef(
        id="pipedrive", nom="Pipedrive", statut="actif",
        module="falkye.notifications.crm.pipedrive_channel", objet_crm_cible="organizations",
        champs_mappage={"nom": "name"},
    )
    provider = PipedriveProvider(provider_def=provider_def_sans_statut)
    resultat = provider.tirer_statut(_connexion(), "99")
    assert resultat.succes is True
    assert resultat.stage_brut is None
