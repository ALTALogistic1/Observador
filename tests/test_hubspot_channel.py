"""Tests du client CRM HubSpot (falkye/notifications/crm/hubspot_channel.py) —
intégration CRM (Radar et Radar+, ajoutée le 2026-09-02). Mocks HTTP via
`responses` — aucun accès réseau vers la vraie API HubSpot dans cet
environnement (même situation que TheirStack/Stripe/géocodage)."""
import json

import responses

from falkye.models.crm_connection import CrmConnection
from falkye.notifications.base import NotificationContent
from falkye.notifications.crm.hubspot_channel import HubspotProvider
from falkye.registry.loader import get_registry


def _provider():
    registry = get_registry()
    return HubspotProvider(provider_def=registry.fournisseur_crm("hubspot"))


def _connexion(**kwargs):
    kwargs.setdefault("profile_id", 1)
    kwargs.setdefault("fournisseur", "hubspot")
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
        responses.POST, "https://api.hubapi.com/crm/v3/objects/companies",
        json={"id": "42", "properties": {}}, status=201,
    )
    provider = _provider()
    result = provider.pousser(_connexion(), _contenu(), None)

    assert result.succes is True
    assert result.crm_object_id == "42"
    body = json.loads(responses.calls[0].request.body)
    assert body["properties"]["name"] == "Entreprise Test"
    assert body["properties"]["falkye_neq"] == "1234567890"
    assert responses.calls[0].request.headers["Authorization"] == "Bearer jeton-test"


@responses.activate
def test_pousser_met_a_jour_un_objet_existant_sans_creer_de_doublon():
    responses.add(
        responses.PATCH, "https://api.hubapi.com/crm/v3/objects/companies/42",
        json={"id": "42", "properties": {}}, status=200,
    )
    provider = _provider()
    result = provider.pousser(_connexion(), _contenu(), "42")

    assert result.succes is True
    assert result.crm_object_id == "42"
    assert responses.calls[0].request.method == "PATCH"


@responses.activate
def test_pousser_echoue_proprement_sur_erreur_http():
    responses.add(
        responses.POST, "https://api.hubapi.com/crm/v3/objects/companies", status=401,
    )
    provider = _provider()
    result = provider.pousser(_connexion(), _contenu(), None)
    assert result.succes is False
    assert result.erreur is not None


@responses.activate
def test_tirer_statut_lit_la_propriete_mappee():
    responses.add(
        responses.GET, "https://api.hubapi.com/crm/v3/objects/companies/42",
        json={"id": "42", "properties": {"falkye_statut_suivi": "Contacté"}}, status=200,
    )
    provider = _provider()
    resultat = provider.tirer_statut(_connexion(), "42")
    assert resultat.succes is True
    assert resultat.stage_brut == "Contacté"
    assert responses.calls[0].request.params.get("properties") == "falkye_statut_suivi"


@responses.activate
def test_tirer_statut_echoue_proprement_sur_erreur_http():
    responses.add(responses.GET, "https://api.hubapi.com/crm/v3/objects/companies/42", status=500)
    provider = _provider()
    resultat = provider.tirer_statut(_connexion(), "42")
    assert resultat.succes is False
    assert resultat.erreur is not None


def test_tirer_statut_retourne_succes_sans_stage_si_pas_de_mappage_statut():
    """Un fournisseur configuré sans clé 'statut_suivi' dans son mappage ne
    doit pas lever — juste "rien à signaler", et aucun appel HTTP émis."""
    from falkye.registry.loader import CrmProviderDef

    provider_def_sans_statut = CrmProviderDef(
        id="hubspot", nom="HubSpot", statut="actif",
        module="falkye.notifications.crm.hubspot_channel", objet_crm_cible="companies",
        champs_mappage={"nom": "name"},  # pas de clé "statut_suivi"
    )
    provider = HubspotProvider(provider_def=provider_def_sans_statut)
    resultat = provider.tirer_statut(_connexion(), "42")
    assert resultat.succes is True
    assert resultat.stage_brut is None
