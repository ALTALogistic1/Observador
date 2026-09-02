"""Tests de la couche de paiement intégré Stripe (falkye/billing/stripe_client.py)
— spec section 9bis. Le SDK stripe est entièrement mocké (voir docstring du module
testé : jamais exécuté contre un vrai compte Stripe dans cet environnement)."""
from datetime import datetime, timezone

import pytest

from falkye.billing import stripe_client
from falkye.models.profile import PlanTarifaire, Profile
from falkye.models.subscription import Subscription


def _profile(db_session, plan=PlanTarifaire.ECHO, profile_id=None):
    p = Profile(courriel=f"test{profile_id or 1}@exemple.com", nom="Profil Test", plan=plan)
    db_session.add(p)
    db_session.flush()
    return p


# --- creer_session_paiement_radar ---


def test_creer_session_paiement_radar_appelle_stripe_avec_les_bons_parametres(db_session, monkeypatch, mocker):
    monkeypatch.setenv("FALKYE_STRIPE_SECRET_KEY", "sk_test_x")
    monkeypatch.setenv("FALKYE_STRIPE_PRICE_ID_RADAR", "price_radar_x")

    profile = _profile(db_session)

    mock_create = mocker.patch("stripe.checkout.Session.create")
    mock_create.return_value.url = "https://checkout.stripe.com/session-test"

    url = stripe_client.creer_session_paiement_radar(profile)

    assert url == "https://checkout.stripe.com/session-test"
    _, kwargs = mock_create.call_args
    assert kwargs["mode"] == "subscription"
    assert kwargs["client_reference_id"] == str(profile.id)
    assert kwargs["customer_email"] == profile.courriel
    assert kwargs["line_items"] == [{"price": "price_radar_x", "quantity": 1}]


def test_creer_session_paiement_radar_leve_si_cle_manquante(db_session, monkeypatch):
    monkeypatch.delenv("FALKYE_STRIPE_SECRET_KEY", raising=False)
    profile = _profile(db_session)
    with pytest.raises(RuntimeError, match="FALKYE_STRIPE_SECRET_KEY"):
        stripe_client.creer_session_paiement_radar(profile)


def test_creer_session_paiement_radar_leve_si_prix_manquant(db_session, monkeypatch):
    monkeypatch.setenv("FALKYE_STRIPE_SECRET_KEY", "sk_test_x")
    monkeypatch.delenv("FALKYE_STRIPE_PRICE_ID_RADAR", raising=False)
    profile = _profile(db_session)
    with pytest.raises(RuntimeError, match="FALKYE_STRIPE_PRICE_ID_RADAR"):
        stripe_client.creer_session_paiement_radar(profile)


# --- traiter_evenement_webhook : checkout.session.completed ---


def test_checkout_complete_fait_passer_le_profil_echo_a_radar(db_session):
    profile = _profile(db_session, plan=PlanTarifaire.ECHO)
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "client_reference_id": str(profile.id),
                "customer": "cus_test123",
                "subscription": "sub_test123",
            }
        },
    }
    stripe_client.traiter_evenement_webhook(event, db_session)

    db_session.refresh(profile)
    assert profile.plan == PlanTarifaire.RADAR

    abo = db_session.query(Subscription).filter_by(profile_id=profile.id).one()
    assert abo.stripe_customer_id == "cus_test123"
    assert abo.stripe_subscription_id == "sub_test123"
    assert abo.statut == "active"


def test_checkout_complete_ne_retrograde_jamais_radar_plus(db_session):
    profile = _profile(db_session, plan=PlanTarifaire.RADAR_PLUS)
    event = {
        "type": "checkout.session.completed",
        "data": {"object": {"client_reference_id": str(profile.id), "customer": "cus_x", "subscription": "sub_x"}},
    }
    stripe_client.traiter_evenement_webhook(event, db_session)

    db_session.refresh(profile)
    assert profile.plan == PlanTarifaire.RADAR_PLUS  # inchangé


def test_checkout_complete_sans_reference_ne_plante_pas(db_session):
    event = {"type": "checkout.session.completed", "data": {"object": {"customer": "cus_x"}}}
    stripe_client.traiter_evenement_webhook(event, db_session)  # ne doit lever aucune exception
    assert db_session.query(Subscription).count() == 0


# --- traiter_evenement_webhook : customer.subscription.updated/deleted ---


def test_subscription_updated_synchronise_statut_et_periode(db_session):
    profile = _profile(db_session, plan=PlanTarifaire.RADAR)
    abo = Subscription(profile_id=profile.id, stripe_subscription_id="sub_abc", statut="active")
    db_session.add(abo)
    db_session.flush()

    fin_periode = int(datetime(2026, 10, 1, tzinfo=timezone.utc).timestamp())
    event = {
        "type": "customer.subscription.updated",
        "data": {"object": {"id": "sub_abc", "status": "past_due", "current_period_end": fin_periode}},
    }
    stripe_client.traiter_evenement_webhook(event, db_session)

    db_session.refresh(abo)
    assert abo.statut == "past_due"
    # SQLite ne conserve pas le fuseau horaire à la relecture (comportement
    # connu du projet) — comparaison sur la valeur naïve équivalente.
    assert abo.periode_courante_fin == datetime(2026, 10, 1, tzinfo=timezone.utc).replace(tzinfo=None)
    # past_due n'est pas dans _STATUTS_STRIPE_INACTIFS : le profil garde Radar
    # (spec implicite : un retard de paiement n'est pas encore une annulation).
    db_session.refresh(profile)
    assert profile.plan == PlanTarifaire.RADAR


def test_subscription_canceled_retrograde_le_profil_radar_vers_echo(db_session):
    profile = _profile(db_session, plan=PlanTarifaire.RADAR)
    abo = Subscription(profile_id=profile.id, stripe_subscription_id="sub_xyz", statut="active")
    db_session.add(abo)
    db_session.flush()

    event = {
        "type": "customer.subscription.deleted",
        "data": {"object": {"id": "sub_xyz", "status": "canceled"}},
    }
    stripe_client.traiter_evenement_webhook(event, db_session)

    db_session.refresh(profile)
    assert profile.plan == PlanTarifaire.ECHO
    db_session.refresh(abo)
    assert abo.statut == "canceled"


def test_subscription_canceled_ne_retrograde_pas_radar_plus(db_session):
    """Radar+ n'est pas (encore) facturé via cet abonnement Stripe — annuler
    l'abonnement Radar sous-jacent ne doit pas toucher un profil déjà Radar+."""
    profile = _profile(db_session, plan=PlanTarifaire.RADAR_PLUS)
    abo = Subscription(profile_id=profile.id, stripe_subscription_id="sub_rp", statut="active")
    db_session.add(abo)
    db_session.flush()

    event = {"type": "customer.subscription.deleted", "data": {"object": {"id": "sub_rp", "status": "canceled"}}}
    stripe_client.traiter_evenement_webhook(event, db_session)

    db_session.refresh(profile)
    assert profile.plan == PlanTarifaire.RADAR_PLUS


def test_subscription_updated_pour_id_inconnu_ne_plante_pas(db_session):
    event = {
        "type": "customer.subscription.updated",
        "data": {"object": {"id": "sub_inconnu", "status": "active"}},
    }
    stripe_client.traiter_evenement_webhook(event, db_session)  # ne doit lever aucune exception


# --- verifier_signature_webhook ---


def test_verifier_signature_webhook_appelle_stripe_webhook_construct_event(monkeypatch, mocker):
    monkeypatch.setenv("FALKYE_STRIPE_WEBHOOK_SECRET", "whsec_test")
    mock_construct = mocker.patch("stripe.Webhook.construct_event")
    mock_construct.return_value = {"type": "checkout.session.completed"}

    resultat = stripe_client.verifier_signature_webhook(b'{"type": "x"}', "sig_test")

    assert resultat == {"type": "checkout.session.completed"}
    mock_construct.assert_called_once_with(b'{"type": "x"}', "sig_test", "whsec_test")


def test_verifier_signature_webhook_leve_si_secret_manquant(monkeypatch):
    monkeypatch.delenv("FALKYE_STRIPE_WEBHOOK_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="FALKYE_STRIPE_WEBHOOK_SECRET"):
        stripe_client.verifier_signature_webhook(b"{}", "sig_test")


# --- type d'événement non traité ---


def test_evenement_non_traite_est_ignore_silencieusement(db_session):
    event = {"type": "invoice.paid", "data": {"object": {}}}
    stripe_client.traiter_evenement_webhook(event, db_session)  # ne doit lever aucune exception
