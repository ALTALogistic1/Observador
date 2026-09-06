"""Tests des gestes déclenchables depuis un courriel — falkye/liens.py.

Désabonnement (RFC 8058) et rétroaction « pas pertinent », tous deux sans
session authentifiée : c'est le jeton dans l'URL qui porte l'autorisation.
"""
from datetime import datetime, timezone

import pytest

from falkye.liens import (
    LienInvalide,
    consommer_desabonnement,
    consommer_pas_pertinent,
    decrire,
    url_desabonnement,
    url_pas_pertinent,
)
from falkye.models.company import Company, StatutLegal, StatutResolution, StatutVerification
from falkye.models.jeton_lien import ActionJeton, JetonLien
from falkye.models.notification import ModeUsage, NiveauConfiance, NiveauPertinence, Notification
from falkye.models.profile import Profile
from falkye.models.retroaction_pertinence import RetroactionPertinence
from falkye.models.sphere import Sphere


def _profile(db_session):
    p = Profile(courriel="alexandre@exemple.com", nom="Alexandre")
    db_session.add(p)
    db_session.flush()
    return p


def _notification(db_session, profile, sphere_id="gestion_projet"):
    if db_session.get(Sphere, sphere_id) is None:
        db_session.add(Sphere(id=sphere_id, nom=sphere_id))
        db_session.flush()
    c = Company(
        nom_detecte="Transport Bourassa",
        nom_detecte_normalise="transport bourassa",
        statut_legal=StatutLegal.IMMATRICULEE,
        statut_resolution=StatutResolution.RESOLU,
        statut_verification=list(StatutVerification)[0],
    )
    db_session.add(c)
    db_session.flush()
    n = Notification(
        company_id=c.id,
        profile_id=profile.id,
        mode=ModeUsage.VEILLE_CONTINUE,
        score_confiance=70.0,
        niveau_confiance=NiveauConfiance.ELEVE,
        niveau_pertinence=NiveauPertinence.AA,
        sphere_probable_id=sphere_id,
        justification_resumee="test",
    )
    db_session.add(n)
    db_session.flush()
    return n


def _jeton_de(url):
    return url.rsplit("/", 1)[-1]


# --- Le jeton lui-même -----------------------------------------------------


def test_le_jeton_en_clair_nest_jamais_stocke(db_session):
    """Une copie de la base ne doit rendre aucun lien utilisable."""
    profile = _profile(db_session)
    jeton = _jeton_de(url_desabonnement(db_session, profile))

    ligne = db_session.query(JetonLien).one()
    assert jeton not in ligne.jeton_empreinte
    assert len(ligne.jeton_empreinte) == 64  # SHA-256 en hexadécimal


def test_un_jeton_inconnu_est_refuse(db_session):
    with pytest.raises(LienInvalide):
        consommer_desabonnement(db_session, "jeton-qui-nexiste-pas")


def test_un_jeton_ne_sert_pas_pour_une_autre_action(db_session):
    """Un jeton de rétroaction ne désabonne pas, et réciproquement — c'est la
    portée qui protège, pas le secret seul."""
    profile = _profile(db_session)
    n = _notification(db_session, profile)
    jeton_retro = _jeton_de(url_pas_pertinent(db_session, n))

    with pytest.raises(LienInvalide):
        consommer_desabonnement(db_session, jeton_retro)
    assert profile.desabonne_le is None


# --- Désabonnement ---------------------------------------------------------


def test_le_desabonnement_coupe_lenvoi(db_session):
    profile = _profile(db_session)
    jeton = _jeton_de(url_desabonnement(db_session, profile))

    consommer_desabonnement(db_session, jeton)

    assert profile.desabonne_le is not None


def test_le_desabonnement_est_idempotent(db_session):
    """Un second clic confirme, il n'échoue pas — une erreur affichée ici
    pousse vers le bouton « pourriel »."""
    profile = _profile(db_session)
    jeton = _jeton_de(url_desabonnement(db_session, profile))

    consommer_desabonnement(db_session, jeton)
    premiere_date = profile.desabonne_le
    consommer_desabonnement(db_session, jeton)

    assert profile.desabonne_le == premiere_date


def test_les_anciens_liens_de_desabonnement_restent_valables(db_session):
    """Le lien d'un courriel de la semaine dernière doit encore fonctionner.

    Seule l'empreinte étant conservée, chaque envoi émet un jeton neuf; révoquer
    les précédents casserait les courriels encore en boîte de réception.
    """
    profile = _profile(db_session)
    ancien = _jeton_de(url_desabonnement(db_session, profile))
    url_desabonnement(db_session, profile)  # l'envoi suivant

    consommer_desabonnement(db_session, ancien)

    assert profile.desabonne_le is not None


def test_decrire_naffecte_rien(db_session):
    """La page de confirmation (GET) montre, elle n'agit pas — les analyseurs de
    liens des messageries suivent les GET avant l'humain."""
    profile = _profile(db_session)
    jeton = _jeton_de(url_desabonnement(db_session, profile))

    description = decrire(db_session, jeton, ActionJeton.DESABONNEMENT)

    assert description["courriel"] == "alexandre@exemple.com"
    assert description["deja_fait"] is False
    assert profile.desabonne_le is None


# --- Rétroaction -----------------------------------------------------------


def test_la_retroaction_marque_le_statut_et_alimente_la_pertinence(db_session):
    profile = _profile(db_session)
    n = _notification(db_session, profile)
    jeton = _jeton_de(url_pas_pertinent(db_session, n))

    consommer_pas_pertinent(db_session, jeton)

    assert n.statut_suivi_id == "pas_pertinent"
    retro = db_session.query(RetroactionPertinence).one()
    assert retro.compte_marques_pas_pertinent == 1
    assert retro.poids < 1.0


def test_deux_clics_ne_pesent_pas_double_sur_la_sphere(db_session):
    """La rétroaction est cumulative : un lien cliqué deux fois — ou prérécupéré
    puis cliqué — compterait deux marquages pour une seule opinion."""
    profile = _profile(db_session)
    n = _notification(db_session, profile)
    jeton = _jeton_de(url_pas_pertinent(db_session, n))

    consommer_pas_pertinent(db_session, jeton)
    poids_apres_un = db_session.query(RetroactionPertinence).one().poids
    consommer_pas_pertinent(db_session, jeton)

    retro = db_session.query(RetroactionPertinence).one()
    assert retro.compte_marques_pas_pertinent == 1
    assert retro.poids == poids_apres_un


def test_la_retroaction_ne_demande_ni_session_ni_palier(db_session):
    """Le profil est au plan Écho par défaut et n'a aucune session ouverte —
    c'était l'obstacle réel, et le jeton le contourne par construction."""
    from falkye.models.profile import PlanTarifaire

    profile = _profile(db_session)
    assert profile.plan == PlanTarifaire.ECHO
    n = _notification(db_session, profile)

    consommer_pas_pertinent(db_session, _jeton_de(url_pas_pertinent(db_session, n)))

    assert n.statut_suivi_id == "pas_pertinent"


# --- Le raccordement au résumé --------------------------------------------


def test_le_resume_porte_les_entetes_rfc_8058_et_le_lien_visible(db_session, monkeypatch):
    from falkye.summary import formatter_resume, generer_resume

    monkeypatch.setenv("FALKYE_LIEN_BASE_URL", "https://lien.falkye.com")
    profile = _profile(db_session)
    n = _notification(db_session, profile)
    maintenant = datetime.now(timezone.utc)
    summary, notifications = generer_resume(db_session, profile, maintenant, maintenant)

    lien = url_desabonnement(db_session, profile)
    contenu = formatter_resume(
        summary,
        notifications,
        liens_pas_pertinent={n.id: url_pas_pertinent(db_session, n)},
        lien_desabonnement=lien,
    )

    assert contenu.entetes["List-Unsubscribe"] == f"<{lien}>"
    assert contenu.entetes["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    assert lien in contenu.corps_texte, "le lien doit aussi être visible pour qui lit"
    assert "/r/" in contenu.corps_texte, "chaque opportunité porte son lien de rétroaction"


def test_sans_point_dentree_configure_aucun_resume_ne_part(db_session, monkeypatch):
    """Un en-tête de désabonnement inutilisable serait décoratif — le mandat
    l'interdit. Refuser d'envoyer est la seule position tenable."""
    from falkye.summary import generer_et_envoyer_resume

    monkeypatch.delenv("FALKYE_LIEN_BASE_URL", raising=False)
    profile = _profile(db_session)
    _notification(db_session, profile)

    with pytest.raises(RuntimeError, match="FALKYE_LIEN_BASE_URL"):
        generer_et_envoyer_resume(db_session, profile)


def test_un_profil_desabonne_naccumule_pas_de_resumes_morts(db_session):
    """Sans la garde, le résumé serait construit, n'aurait aucun canal où
    aller, ne serait jamais marqué envoyé — et les opportunités
    s'accumuleraient en attente pour toujours."""
    from falkye.summary import generer_et_envoyer_resume

    profile = _profile(db_session)
    n = _notification(db_session, profile)
    consommer_desabonnement(db_session, _jeton_de(url_desabonnement(db_session, profile)))

    resultat = generer_et_envoyer_resume(db_session, profile)

    assert resultat is None
    assert n.inclus_dans_resume is False
    assert db_session.query(Notification).count() == 1
