"""Tests du résumé groupé — falkye/summary.py.

Ce module n'avait AUCUN test avant le 2026-09-05, et c'est exactement pourquoi
trois défauts y ont survécu jusqu'à la phase 0 du chantier 28 : le lot perdu en
silence, la divergence avec l'autre chemin de livraison, et l'inclusion des
signaux hors profil. Chacun a son test ci-dessous, écrit pour échouer sur la
version d'avant.
"""
from datetime import datetime, timedelta, timezone

import pytest

from falkye.models.company import Company, StatutLegal, StatutResolution, StatutVerification
from falkye.models.notification import (
    ModeUsage,
    NiveauConfiance,
    NiveauPertinence,
    Notification,
    NotificationSignal,
)
from falkye.models.profile import Profile
from falkye.models.signal import Signal
from falkye.notifications.base import DeliveryResult, NotificationChannel
from falkye.registry.loader import NotificationChannelDef
from falkye.summary import generer_et_envoyer_resume, generer_resume, notifications_en_attente


class _CanalEspion(NotificationChannel):
    """Canal qui note ce qu'on lui demande d'envoyer, sans rien envoyer."""

    journal: list = []
    succes: bool = True

    def envoyer(self, destinataire, contenu):
        type(self).journal.append((self.channel_def.id, destinataire, contenu))
        if type(self).succes:
            return DeliveryResult(succes=True)
        return DeliveryResult(succes=False, erreur="panne simulée du fournisseur")


@pytest.fixture()
def espion(monkeypatch):
    _CanalEspion.journal = []
    _CanalEspion.succes = True
    monkeypatch.setattr(
        NotificationChannelDef, "charger_canal", lambda self: _CanalEspion(channel_def=self)
    )
    return _CanalEspion


def _profile(db_session, courriel="alexandre@exemple.com"):
    p = Profile(courriel=courriel, nom="Profil Test")
    db_session.add(p)
    db_session.flush()
    return p


def _company(db_session, nom="Transport Bourassa"):
    c = Company(
        nom_detecte=nom,
        nom_detecte_normalise=nom.lower(),
        ville="Laval",
        statut_legal=StatutLegal.IMMATRICULEE,
        statut_resolution=StatutResolution.RESOLU,
        statut_verification=list(StatutVerification)[0],
    )
    db_session.add(c)
    db_session.flush()
    return c


def _notification(db_session, profile, company, *, hors_profil=False, avec_signal=True):
    n = Notification(
        company_id=company.id,
        profile_id=profile.id,
        mode=ModeUsage.VEILLE_CONTINUE,
        score_confiance=72.0,
        niveau_confiance=NiveauConfiance.ELEVE,
        score_pertinence=80.0,
        niveau_pertinence=NiveauPertinence.AA,
        justification_resumee="résumé de test",
        hors_profil=hors_profil,
    )
    db_session.add(n)
    db_session.flush()
    if avec_signal:
        s = Signal(
            company_id=company.id,
            source_id="seao",
            signal_type_id="appel_offres",
            detected_at=datetime.now(timezone.utc),
        )
        db_session.add(s)
        db_session.flush()
        db_session.add(
            NotificationSignal(
                notification_id=n.id,
                signal_id=s.id,
                justification="contrat public de 45 990 $ obtenu ce mois-ci",
            )
        )
        db_session.flush()
    return n


# --- Défaut 1 : le lot perdu en silence ------------------------------------


def test_envoi_reussi_marque_les_opportunites_comme_livrees(db_session, espion):
    profile = _profile(db_session)
    _notification(db_session, profile, _company(db_session))

    summary = generer_et_envoyer_resume(db_session, profile)

    assert summary.envoye_le is not None
    assert notifications_en_attente(db_session, profile, avant=datetime.now(timezone.utc)) == []


def test_envoi_echoue_ne_marque_rien_et_le_lot_repart_au_cycle_suivant(db_session, espion):
    """Le test central du défaut 1.

    Sur la version d'avant, les notifications étaient marquées AVANT l'envoi et
    sélectionnées par fenêtre de dates : un échec les perdait définitivement.
    """
    profile = _profile(db_session)
    _notification(db_session, profile, _company(db_session))

    espion.succes = False
    premier = generer_et_envoyer_resume(db_session, profile)

    assert premier.envoye_le is None
    en_attente = notifications_en_attente(db_session, profile, avant=datetime.now(timezone.utc))
    assert len(en_attente) == 1, "une opportunité non livrée doit rester en attente"

    # Le cycle suivant, le fournisseur répond de nouveau : le lot sort.
    espion.succes = True
    second = generer_et_envoyer_resume(db_session, profile)

    assert second.envoye_le is not None
    assert len(second.notification_ids) == 1
    assert notifications_en_attente(db_session, profile, avant=datetime.now(timezone.utc)) == []


def test_une_opportunite_plus_vieille_que_la_fenetre_reste_livrable(db_session, espion):
    """La sélection porte sur l'état d'attente, jamais sur une fenêtre basse."""
    profile = _profile(db_session)
    n = _notification(db_session, profile, _company(db_session))
    n.created_at = datetime.now(timezone.utc) - timedelta(days=90)
    db_session.flush()

    summary = generer_et_envoyer_resume(db_session, profile, jours=7)

    assert n.id in summary.notification_ids


# --- Défaut 2 : les deux chemins de livraison ------------------------------


def test_le_resume_ne_sollicite_que_les_canaux_de_forme_resume(db_session, espion):
    """Le canal webhook est actif au registre mais déclaré `unitaire`.

    Sur la version d'avant, il recevait l'adresse courriel du profil comme si
    c'était une URL — une livraison en échec parasite à chaque résumé, et la
    réserve de palier Radar+ contournée.
    """
    profile = _profile(db_session)
    _notification(db_session, profile, _company(db_session))

    generer_et_envoyer_resume(db_session, profile)

    canaux_sollicites = {ligne[0] for ligne in espion.journal}
    assert "webhook_generique" not in canaux_sollicites
    assert canaux_sollicites, "au moins un canal de forme `resume` doit avoir été sollicité"


def test_la_date_denvoi_ne_depend_daucun_identifiant_de_canal_code_en_dur(db_session, espion, registry):
    """Sur la version d'avant, `envoye_le` n'était posée que si l'identifiant du
    canal valait exactement "email" — le nouveau canal aurait cessé de la
    remplir en silence."""
    profile = _profile(db_session)
    _notification(db_session, profile, _company(db_session))

    summary = generer_et_envoyer_resume(db_session, profile)

    identifiants = {c.id for c in registry.canaux_actifs() if c.sert_forme("resume")}
    assert "email" in identifiants  # état actuel du registre
    assert summary.envoye_le is not None
    # Et la garantie qui compte : la date vient du SUCCÈS, pas de l'identifiant.
    assert {ligne[0] for ligne in espion.journal} <= identifiants


# --- Défaut 3 (troisième divergence trouvée en réunifiant) -----------------


def test_les_signaux_hors_profil_sont_exclus_du_resume(db_session, espion):
    """Un signal redirigé hors du profil déclaré n'est jamais mélangé aux
    notifications normales (spec section 8bis) — la livraison unitaire l'excluait
    déjà, le résumé non."""
    profile = _profile(db_session)
    company = _company(db_session)
    normale = _notification(db_session, profile, company)
    hors = _notification(db_session, profile, company, hors_profil=True)

    summary = generer_et_envoyer_resume(db_session, profile)

    assert normale.id in summary.notification_ids
    assert hors.id not in summary.notification_ids
    assert hors.inclus_dans_resume is False


# --- Le motif du repérage --------------------------------------------------


def test_le_resume_porte_le_motif_du_reperage_et_jamais_le_nom_de_la_source(db_session, espion, registry):
    """Charte section 16 : un nom d'entreprise sans le motif précis du repérage
    ne vaut pas mieux qu'une liste achetée ailleurs. Et charte section 6 : jamais
    le nom d'une source dans un libellé visible."""
    profile = _profile(db_session)
    _notification(db_session, profile, _company(db_session))

    generer_et_envoyer_resume(db_session, profile)

    corps = espion.journal[0][2].corps_texte
    assert "Transport Bourassa" in corps
    assert "contrat public de 45 990 $ obtenu ce mois-ci" in corps, "le motif doit être livré"
    categorie = registry.signal_types["appel_offres"].nom
    assert categorie in corps
    assert "seao" not in corps.lower(), "aucun libellé ne doit nommer une source"


def test_generer_resume_ne_marque_rien_par_lui_meme(db_session):
    """La génération et la livraison sont deux gestes distincts — c'est ce qui
    permet à un échec de ne rien perdre."""
    profile = _profile(db_session)
    n = _notification(db_session, profile, _company(db_session))
    maintenant = datetime.now(timezone.utc)

    generer_resume(db_session, profile, maintenant - timedelta(days=7), maintenant)

    assert n.inclus_dans_resume is False
