"""Couche de paiement intégré Stripe — spec section 9bis, plan Radar
("l'utilisateur paie pour débloquer, nous gérons l'accès à la source"). Choix de
Stripe confirmé par Alexandre le 2026-09-02, sans comparatif requis ("choix
standard pour ce type de produit au Canada").

Isolée du reste du moteur : AUCUN autre module n'importe le SDK stripe directement,
seulement celui-ci — pour que la logique d'attribution de plan
(traiter_evenement_webhook) reste testable sans réseau, en mockant les deux seuls
points d'entrée SDK utilisés ici (stripe.checkout.Session.create,
stripe.Webhook.construct_event).

STATUT DE VALIDATION — IMPORTANT : ce module est construit et testé unitairement
contre le SDK Stripe mocké (voir tests/test_billing.py), jamais exécuté contre un
vrai compte Stripe — aucune clé API réelle n'est disponible dans cet environnement
de développement. Comme pour les sources bloquées par le proxy réseau (voir
docs/STATUT_RESEAU.md), la validation de bout en bout (vraie session de paiement,
vrai webhook livré à un point de terminaison HTTP public) reste à faire une fois
qu'Alexandre a un compte Stripe réel et un point de terminaison déployé capable de
recevoir les webhooks — ni l'un ni l'autre n'existe encore, et aucun des deux n'est
buildable dans ce bac à sable (pas d'URL publique). En attendant, `traiter_evenement_
webhook` accepte un événement DÉJÀ décodé (voir séparation ci-dessous), pour rester
utilisable via un chemin manuel équivalent à l'import manuel (spec section 9) —
voir la commande CLI `falkye billing traiter-webhook`."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import stripe
from sqlalchemy import select
from sqlalchemy.orm import Session

from falkye.models.profile import PlanTarifaire, Profile
from falkye.models.subscription import Subscription

logger = logging.getLogger(__name__)

# Statuts Stripe qui doivent faire perdre l'accès Radar — spec : "l'utilisateur
# paie pour débloquer" implique, symétriquement, que cesser de payer reprend
# l'accès. Vocabulaire natif Stripe, pas traduit (voir Subscription.statut).
_STATUTS_STRIPE_INACTIFS = {"canceled", "unpaid", "incomplete_expired"}


def _stripe_configure() -> None:
    cle = os.environ.get("FALKYE_STRIPE_SECRET_KEY")
    if not cle:
        raise RuntimeError(
            "FALKYE_STRIPE_SECRET_KEY non configurée (voir .env.example) — impossible d'appeler l'API Stripe."
        )
    stripe.api_key = cle


def creer_session_paiement_radar(profile: Profile) -> str:
    """Crée une session Stripe Checkout (mode abonnement) pour le plan Radar et
    retourne son URL. `client_reference_id` porte l'id du profil pour que le
    webhook (_appliquer_checkout_complete) relie l'événement au bon profil sans
    dépendre d'une correspondance par courriel — plus fragile, un utilisateur peut
    payer avec une adresse différente de celle de son profil FALKYE."""
    _stripe_configure()
    prix_id = os.environ.get("FALKYE_STRIPE_PRICE_ID_RADAR")
    if not prix_id:
        raise RuntimeError("FALKYE_STRIPE_PRICE_ID_RADAR non configuré (voir .env.example).")

    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": prix_id, "quantity": 1}],
        client_reference_id=str(profile.id),
        customer_email=profile.courriel,
        success_url=os.environ.get("FALKYE_STRIPE_SUCCESS_URL", "https://falkye.example/radar/succes"),
        cancel_url=os.environ.get("FALKYE_STRIPE_CANCEL_URL", "https://falkye.example/radar/annule"),
    )
    return session.url


def verifier_signature_webhook(payload: bytes, signature_entete: str) -> dict:
    """Vérifie la signature Stripe d'un webhook livré par un vrai point de
    terminaison HTTP (obligatoire avant de faire confiance à un payload externe)
    et retourne l'événement décodé. Lève stripe.error.SignatureVerificationError
    si invalide. Séparée de traiter_evenement_webhook pour que celui-ci reste
    appelable sur un événement obtenu autrement (voir docstring du module —
    traitement manuel en attendant un point de terminaison public réel)."""
    secret = os.environ.get("FALKYE_STRIPE_WEBHOOK_SECRET")
    if not secret:
        raise RuntimeError("FALKYE_STRIPE_WEBHOOK_SECRET non configuré (voir .env.example).")
    return stripe.Webhook.construct_event(payload, signature_entete, secret)


def traiter_evenement_webhook(event: dict, db_session: Session) -> None:
    """Applique UN événement Stripe déjà décodé au profil concerné."""
    type_evenement = event.get("type")
    data = event.get("data", {}).get("object", {})

    if type_evenement == "checkout.session.completed":
        _appliquer_checkout_complete(data, db_session)
    elif type_evenement in ("customer.subscription.updated", "customer.subscription.deleted"):
        _appliquer_maj_abonnement(data, db_session)
    else:
        logger.info("Événement Stripe ignoré (type non traité ici) : %s", type_evenement)


def _profil_depuis_reference(data: dict, db_session: Session) -> Profile | None:
    profile_id = data.get("client_reference_id") or (data.get("metadata") or {}).get("profile_id")
    if not profile_id:
        return None
    try:
        return db_session.get(Profile, int(profile_id))
    except (TypeError, ValueError):
        return None


def _abonnement_pour_profil(db_session: Session, profile_id: int) -> Subscription:
    abo = db_session.execute(select(Subscription).where(Subscription.profile_id == profile_id)).scalar_one_or_none()
    if abo is None:
        abo = Subscription(profile_id=profile_id)
        db_session.add(abo)
    return abo


def _appliquer_checkout_complete(data: dict, db_session: Session) -> None:
    profile = _profil_depuis_reference(data, db_session)
    if profile is None:
        logger.warning(
            "Webhook checkout.session.completed sans profil résolu (client_reference_id manquant/invalide)."
        )
        return

    abo = _abonnement_pour_profil(db_session, profile.id)
    abo.stripe_customer_id = data.get("customer") or abo.stripe_customer_id
    abo.stripe_subscription_id = data.get("subscription") or abo.stripe_subscription_id
    abo.statut = "active"
    abo.updated_at = datetime.now(timezone.utc)

    # Ne rétrograde jamais un Radar+ existant vers Radar — ce paiement ne débloque
    # que le palier Radar (spec section 9bis).
    if profile.plan == PlanTarifaire.ECHO:
        profile.plan = PlanTarifaire.RADAR

    db_session.commit()


def _appliquer_maj_abonnement(data: dict, db_session: Session) -> None:
    stripe_subscription_id = data.get("id")
    statut = data.get("status")
    if not stripe_subscription_id or not statut:
        return

    abo = db_session.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == stripe_subscription_id)
    ).scalar_one_or_none()
    if abo is None:
        logger.warning("Webhook d'abonnement pour un stripe_subscription_id inconnu : %s", stripe_subscription_id)
        return

    abo.statut = statut
    periode_fin = data.get("current_period_end")
    if periode_fin:
        abo.periode_courante_fin = datetime.fromtimestamp(periode_fin, tz=timezone.utc)
    abo.updated_at = datetime.now(timezone.utc)

    if statut in _STATUTS_STRIPE_INACTIFS:
        profile = db_session.get(Profile, abo.profile_id)
        # Ne rétrograde PAS Radar+ automatiquement : Radar+ n'est pas (encore)
        # facturé via cet abonnement Stripe (gestion de clés utilisateur, spec
        # section 9bis, non construite — voir docs/STATUT_RESEAU.md) — seul le
        # plan Radar dépend de ce statut d'abonnement.
        if profile is not None and profile.plan == PlanTarifaire.RADAR:
            profile.plan = PlanTarifaire.ECHO

    db_session.commit()
