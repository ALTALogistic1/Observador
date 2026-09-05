"""Tests du canal d'envoi Postmark — falkye/notifications/postmark_channel.py.

Les réponses simulées ici sont les réponses RÉELLES de `api.postmarkapp.com`,
relevées le 2026-09-05 avec le jeton de test documenté (voir
`outils/sonde_postmark.py`, qui rejoue le contrat contre la vraie API). Simuler
une forme inventée ne prouverait rien — c'est la section 8 de la charte, ne
jamais présumer une capacité non testée.
"""
import json

import pytest
import responses
from requests.exceptions import ConnectionError as ErreurConnexion

from falkye.notifications.base import NotificationContent
from falkye.notifications.postmark_channel import URL_ENVOI, PostmarkChannel
from falkye.registry.loader import get_registry


@pytest.fixture()
def canal():
    return PostmarkChannel(channel_def=get_registry().canal("postmark"))


@pytest.fixture()
def configure(monkeypatch):
    monkeypatch.setenv("FALKYE_POSTMARK_SERVER_TOKEN", "jeton-de-test")
    monkeypatch.setenv("FALKYE_POSTMARK_FROM_ADDR", "avis@avis.falkye.com")
    monkeypatch.delenv("FALKYE_POSTMARK_MESSAGE_STREAM", raising=False)


def _contenu(**kwargs):
    base = {"sujet": "[FALKYE] Résumé", "corps_texte": "une opportunité"}
    base.update(kwargs)
    return NotificationContent(**base)


def _reponse_acceptee():
    return responses.add(
        responses.POST,
        URL_ENVOI,
        json={
            "ErrorCode": 0,
            "Message": "Test job accepted",
            "MessageID": "9a338ce6-8d3c-4b4b-a20e-f47a5223bac6",
            "SubmittedAt": "2026-09-05T22:01:01.0615102Z",
            "To": "alexandre@exemple.com",
        },
        status=200,
    )


# --- Configuration ---------------------------------------------------------


def test_sans_configuration_echoue_explicitement(canal, monkeypatch):
    """Une configuration absente échoue en le disant, jamais en simulant un envoi."""
    monkeypatch.delenv("FALKYE_POSTMARK_SERVER_TOKEN", raising=False)
    monkeypatch.delenv("FALKYE_POSTMARK_FROM_ADDR", raising=False)

    resultat = canal.envoyer("alexandre@exemple.com", _contenu())

    assert resultat.succes is False
    assert "FALKYE_POSTMARK_SERVER_TOKEN" in resultat.erreur


# --- Le flux de diffusion, qui est le piège du chantier --------------------


@responses.activate
def test_le_flux_par_defaut_est_la_diffusion_jamais_le_transactionnel(canal, configure):
    """Un résumé hebdomadaire est une diffusion. Se tromper de flux par simple
    oubli de configuration est le risque le plus cher de ce module."""
    _reponse_acceptee()

    canal.envoyer("alexandre@exemple.com", _contenu())

    charge = json.loads(responses.calls[0].request.body)
    assert charge["MessageStream"] == "broadcast"


@responses.activate
def test_le_flux_reste_surclassable(canal, configure, monkeypatch):
    monkeypatch.setenv("FALKYE_POSTMARK_MESSAGE_STREAM", "resume-hebdo")
    _reponse_acceptee()

    canal.envoyer("alexandre@exemple.com", _contenu())

    assert json.loads(responses.calls[0].request.body)["MessageStream"] == "resume-hebdo"


# --- La charge envoyée -----------------------------------------------------


@responses.activate
def test_la_charge_porte_le_jeton_lexpediteur_et_le_contenu(canal, configure):
    _reponse_acceptee()

    resultat = canal.envoyer("alexandre@exemple.com", _contenu())

    assert resultat.succes is True
    requete = responses.calls[0].request
    assert requete.headers["X-Postmark-Server-Token"] == "jeton-de-test"
    charge = json.loads(requete.body)
    assert charge["From"] == "avis@avis.falkye.com"
    assert charge["To"] == "alexandre@exemple.com"
    assert charge["Subject"] == "[FALKYE] Résumé"
    assert charge["TextBody"] == "une opportunité"
    assert "HtmlBody" not in charge, "pas de corps HTML vide envoyé pour rien"


@responses.activate
def test_les_entetes_sont_traduits_au_format_postmark(canal, configure):
    """Le point d'accroche de `List-Unsubscribe` (RFC 8058) — Postmark attend une
    LISTE de {Name, Value}, pas un objet. Vérifié par appel réel."""
    _reponse_acceptee()

    canal.envoyer(
        "alexandre@exemple.com",
        _contenu(
            entetes={
                "List-Unsubscribe": "<https://lien.falkye.com/d/JETON>",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            }
        ),
    )

    entetes = json.loads(responses.calls[0].request.body)["Headers"]
    assert {"Name": "List-Unsubscribe", "Value": "<https://lien.falkye.com/d/JETON>"} in entetes
    assert {"Name": "List-Unsubscribe-Post", "Value": "List-Unsubscribe=One-Click"} in entetes


# --- Les échecs, dans leurs formes réelles ---------------------------------


@responses.activate
def test_jeton_invalide(canal, configure):
    """Réponse réelle relevée le 2026-09-05."""
    responses.add(
        responses.POST,
        URL_ENVOI,
        json={"ErrorCode": 10, "Message": "Request does not contain a valid Server token."},
        status=401,
    )

    resultat = canal.envoyer("alexandre@exemple.com", _contenu())

    assert resultat.succes is False
    assert "401" in resultat.erreur and "ErrorCode 10" in resultat.erreur


@responses.activate
def test_adresse_malformee(canal, configure):
    """Réponse réelle relevée le 2026-09-05 — le message est exploitable tel quel."""
    responses.add(
        responses.POST,
        URL_ENVOI,
        json={
            "ErrorCode": 300,
            "Message": "Error parsing 'To': Illegal email address 'pas-une-adresse'. "
            "It must contain the '@' symbol.",
        },
        status=422,
    )

    resultat = canal.envoyer("pas-une-adresse", _contenu())

    assert resultat.succes is False
    assert "Illegal email address" in resultat.erreur


@responses.activate
def test_un_code_derreur_non_nul_sur_un_200_reste_un_echec(canal, configure):
    """Un faux succès ferait marquer un lot comme livré alors qu'il ne l'est pas
    — exactement le défaut que la réunification des chemins vient de corriger."""
    responses.add(responses.POST, URL_ENVOI, json={"ErrorCode": 406, "Message": "Inactive recipient"}, status=200)

    resultat = canal.envoyer("alexandre@exemple.com", _contenu())

    assert resultat.succes is False
    assert "Inactive recipient" in resultat.erreur


@responses.activate
def test_une_reponse_illisible_est_un_echec_jamais_un_succes(canal, configure):
    """Une page d'erreur de proxy n'est pas du JSON. Le repli par défaut doit
    être l'échec, sans quoi une panne d'infrastructure passerait pour un envoi."""
    responses.add(responses.POST, URL_ENVOI, body="<html>502 Bad Gateway</html>", status=502)

    resultat = canal.envoyer("alexandre@exemple.com", _contenu())

    assert resultat.succes is False
    assert "illisible" in resultat.erreur


@responses.activate
def test_une_panne_reseau_est_rapportee_sans_lever(canal, configure):
    """Une exception qui remonte interromprait le résumé entier. Le canal la
    traduit en échec de livraison, que l'appelant sait déjà traiter."""
    # Le type exact que `requests` lève sur une panne réseau — c'est lui que le
    # canal doit attraper, pas l'exception intégrée du même nom.
    responses.add(responses.POST, URL_ENVOI, body=ErreurConnexion("réseau coupé"))

    resultat = canal.envoyer("alexandre@exemple.com", _contenu())

    assert resultat.succes is False
    assert resultat.erreur


# --- Le raccordement au registre -------------------------------------------


def test_le_canal_est_actif_et_sert_le_resume(canal):
    registre = get_registry()
    postmark = registre.canal("postmark")
    assert postmark.est_actif
    assert postmark.sert_forme("resume")
    assert not postmark.sert_forme("unitaire")


def test_smtp_nest_plus_actif_pour_ne_pas_envoyer_le_resume_en_double():
    registre = get_registry()
    actifs_resume = [c.id for c in registre.canaux_actifs() if c.sert_forme("resume")]
    assert actifs_resume == ["postmark"]


def test_la_destination_reste_le_courriel_du_profil(canal):
    """Le canal n'a pas de résolution propre — il hérite du courriel du profil,
    seule donnée de contact universelle."""

    class _Profil:
        courriel = "alexandre@exemple.com"

    assert canal.resoudre_destinataire(_Profil()) == "alexandre@exemple.com"
