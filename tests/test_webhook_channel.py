"""Tests du canal webhook générique (falkye/notifications/webhook_channel.py) —
spec section 4bis, fonctionnalité Radar+ "accès API/webhook complet"."""
import responses

from falkye.models.profile import PlanTarifaire, Profile
from falkye.notifications.base import NotificationContent
from falkye.notifications.email_channel import EmailChannel
from falkye.notifications.webhook_channel import WebhookChannel
from falkye.registry.loader import get_registry


def _profile(plan=PlanTarifaire.RADAR_PLUS, webhook_url="https://exemple.test/webhook", courriel="t@t.com"):
    return Profile(courriel=courriel, nom="T", plan=plan, webhook_url=webhook_url)


def _channel():
    registry = get_registry()
    return WebhookChannel(channel_def=registry.canal("webhook_generique"))


def test_resoudre_destinataire_retourne_url_pour_radar_plus():
    channel = _channel()
    profile = _profile(plan=PlanTarifaire.RADAR_PLUS)
    assert channel.resoudre_destinataire(profile) == "https://exemple.test/webhook"


def test_resoudre_destinataire_none_pour_radar():
    channel = _channel()
    profile = _profile(plan=PlanTarifaire.RADAR)
    assert channel.resoudre_destinataire(profile) is None


def test_resoudre_destinataire_none_pour_echo():
    channel = _channel()
    profile = _profile(plan=PlanTarifaire.ECHO)
    assert channel.resoudre_destinataire(profile) is None


def test_resoudre_destinataire_none_si_radar_plus_sans_url_configuree():
    channel = _channel()
    profile = _profile(plan=PlanTarifaire.RADAR_PLUS, webhook_url=None)
    assert channel.resoudre_destinataire(profile) is None


def test_email_channel_resoudre_destinataire_utilise_le_courriel():
    """Le comportement par défaut (NotificationChannel.resoudre_destinataire)
    reproduit exactement l'ancien hardcodage de falkye/engine.py."""
    registry = get_registry()
    channel = EmailChannel(channel_def=registry.canal("email"))
    profile = _profile(courriel="alexandre@exemple.com")
    assert channel.resoudre_destinataire(profile) == "alexandre@exemple.com"


@responses.activate
def test_envoyer_poste_les_donnees_structurees_en_json():
    responses.add(responses.POST, "https://exemple.test/webhook", json={"ok": True}, status=200)
    channel = _channel()
    contenu = NotificationContent(
        sujet="test", corps_texte="test", donnees_structurees={"notification_id": 42, "entreprise": {"nom": "X"}}
    )
    result = channel.envoyer("https://exemple.test/webhook", contenu)
    assert result.succes is True
    assert responses.calls[0].request.url == "https://exemple.test/webhook"
    import json

    assert json.loads(responses.calls[0].request.body) == {"notification_id": 42, "entreprise": {"nom": "X"}}


@responses.activate
def test_envoyer_replie_sur_sujet_corps_texte_sans_donnees_structurees():
    responses.add(responses.POST, "https://exemple.test/webhook", json={"ok": True}, status=200)
    channel = _channel()
    contenu = NotificationContent(sujet="Sujet test", corps_texte="Corps test")
    result = channel.envoyer("https://exemple.test/webhook", contenu)
    assert result.succes is True
    import json

    assert json.loads(responses.calls[0].request.body) == {"sujet": "Sujet test", "corps_texte": "Corps test"}


@responses.activate
def test_envoyer_echoue_proprement_sur_statut_http_erreur():
    responses.add(responses.POST, "https://exemple.test/webhook", status=500)
    channel = _channel()
    contenu = NotificationContent(sujet="test", corps_texte="test")
    result = channel.envoyer("https://exemple.test/webhook", contenu)
    assert result.succes is False
    assert result.erreur is not None
