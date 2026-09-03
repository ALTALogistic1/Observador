"""Tests du Niveau 2 de l'assistance à la configuration du profil par IA,
dimension sphère (falkye/assistance_sphere_ia.py) — spec section 8bis
(2026-09-03), enveloppe mince autour du moteur généralisé
falkye/assistance_ia.py. Le SDK anthropic est entièrement mocké — voir
docstring du module testé : jamais exécuté contre une vraie clé API dans cet
environnement de développement (même situation que Stripe/HubSpot/Pipedrive)."""
import json
from types import SimpleNamespace

import pytest

from falkye.assistance_sphere import SuggestionSphere
from falkye.assistance_sphere_ia import (
    AssistanceIANonConfiguree,
    PlanInsuffisantPourAssistanceIA,
    departager_spheres_niveau2,
    suggerer_spheres_niveau2,
)
from falkye.models.diagnostic_journal import DiagnosticJournal, TypeDiagnostic
from falkye.models.profile import PlanTarifaire, Profile
from falkye.models.sphere import Sphere
from falkye.models.sphere_synonyme import SphereSynonyme


def _profile(db_session, plan=PlanTarifaire.RADAR):
    p = Profile(courriel="test@exemple.com", nom="Profil Test", plan=plan)
    db_session.add(p)
    db_session.flush()
    return p


def _semer_spheres(db_session):
    db_session.add_all(
        [
            Sphere(id="cybersecurite", nom="Cybersécurité"),
            Sphere(id="logistique_transport_flotte", nom="Logistique / transport / gestion de flotte"),
        ]
    )
    db_session.flush()


def _mock_reponse_anthropic(mocker, payload: dict):
    """Reproduit la forme d'une réponse `client.messages.create(...)` avec
    output_config json_schema : le premier bloc de contenu est du texte JSON
    valide (voir docstring du module testé et la référence du SDK)."""
    reponse = SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(payload))])
    mock_client = mocker.Mock()
    mock_client.messages.create.return_value = reponse
    mock_anthropic_cls = mocker.patch("anthropic.Anthropic", return_value=mock_client)
    return mock_anthropic_cls, mock_client


# --- Gating de plan / configuration (partagé, vérifié via l'enveloppe sphère) ---


def test_leve_si_plan_echo(db_session, mocker):
    profile = _profile(db_session, plan=PlanTarifaire.ECHO)
    mock_anthropic_cls = mocker.patch("anthropic.Anthropic")
    with pytest.raises(PlanInsuffisantPourAssistanceIA):
        suggerer_spheres_niveau2(db_session, profile, "une description")
    mock_anthropic_cls.assert_not_called()


def test_leve_si_cle_manquante(db_session, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    profile = _profile(db_session, plan=PlanTarifaire.RADAR)
    with pytest.raises(AssistanceIANonConfiguree):
        suggerer_spheres_niveau2(db_session, profile, "une description")


# --- Classification complète (le Niveau 1 a échoué) ---


def test_sphere_existante_retournee_et_synonyme_enregistre(db_session, monkeypatch, mocker):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-x")
    profile = _profile(db_session, plan=PlanTarifaire.RADAR_PLUS)
    _semer_spheres(db_session)
    _mock_reponse_anthropic(
        mocker,
        {
            "liens": [{"id": "cybersecurite", "poids": 100}],
            "sentinelle": None,
            "confiance": "elevee",
            "raisonnement": "L'utilisateur décrit des tests d'intrusion.",
            "synonyme_a_retenir": "pentest",
        },
    )

    suggestion = suggerer_spheres_niveau2(db_session, profile, "On fait du pentest pour des PME")

    assert len(suggestion.liens) == 1
    assert suggestion.liens[0].sphere_id == "cybersecurite"
    assert suggestion.liens[0].sphere_nom == "Cybersécurité"
    assert suggestion.liens[0].poids == 100.0
    assert suggestion.confiance == "elevee"
    assert suggestion.synonyme_retenu == "pentest"
    assert suggestion.candidat_diagnostic_id is None

    ligne = db_session.query(SphereSynonyme).filter_by(sphere_id="cybersecurite", texte="pentest").one()
    assert ligne.origine == "ia_niveau2"

    # Jamais de création de sphère — seules les 2 semées existent toujours.
    assert db_session.query(Sphere).count() == 2


def test_plusieurs_spheres_retournees_a_la_fois(db_session, monkeypatch, mocker):
    """Cas central de l'évolution plusieurs-à-plusieurs : le modèle peut
    retourner PLUSIEURS sphères à la fois, chacune avec son propre poids."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-x")
    profile = _profile(db_session, plan=PlanTarifaire.RADAR)
    _semer_spheres(db_session)
    _mock_reponse_anthropic(
        mocker,
        {
            "liens": [
                {"id": "cybersecurite", "poids": 100},
                {"id": "logistique_transport_flotte", "poids": 40},
            ],
            "sentinelle": None,
            "confiance": "moyenne",
            "raisonnement": "Les deux sphères s'appliquent, la cybersécurité domine.",
            "synonyme_a_retenir": None,
        },
    )

    suggestion = suggerer_spheres_niveau2(db_session, profile, "Sécurisation des systèmes de suivi de flotte")

    assert {(l.sphere_id, l.poids) for l in suggestion.liens} == {
        ("cybersecurite", 100.0),
        ("logistique_transport_flotte", 40.0),
    }


def test_ne_duplique_pas_un_synonyme_deja_present(db_session, monkeypatch, mocker):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-x")
    profile = _profile(db_session, plan=PlanTarifaire.RADAR)
    _semer_spheres(db_session)
    db_session.add(SphereSynonyme(sphere_id="cybersecurite", texte="Pentest", origine="registre"))
    db_session.flush()
    _mock_reponse_anthropic(
        mocker,
        {
            "liens": [{"id": "cybersecurite", "poids": 100}],
            "sentinelle": None,
            "confiance": "moyenne",
            "raisonnement": "correspond",
            "synonyme_a_retenir": "pentest",
        },
    )

    suggestion = suggerer_spheres_niveau2(db_session, profile, "pentest pour PME")

    assert suggestion.synonyme_retenu is None
    assert db_session.query(SphereSynonyme).filter_by(sphere_id="cybersecurite").count() == 1


def test_aucune_correspondance_journalise_un_diagnostic(db_session, monkeypatch, mocker):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-x")
    profile = _profile(db_session, plan=PlanTarifaire.RADAR)
    _semer_spheres(db_session)
    _mock_reponse_anthropic(
        mocker,
        {
            "liens": [],
            "sentinelle": "aucune_correspondance",
            "confiance": "faible",
            "raisonnement": "Aucune sphère du catalogue ne couvre l'apiculture urbaine.",
            "synonyme_a_retenir": None,
        },
    )

    suggestion = suggerer_spheres_niveau2(db_session, profile, "Conseil en apiculture urbaine")

    assert suggestion.liens == []
    assert suggestion.candidat_diagnostic_id is not None

    candidat = db_session.get(DiagnosticJournal, suggestion.candidat_diagnostic_id)
    assert candidat.type_diagnostic == TypeDiagnostic.CANDIDAT_SPHERE
    assert candidat.profile_id == profile.id
    assert candidat.texte_description == "Conseil en apiculture urbaine"
    assert candidat.statut == "a_examiner"

    # Jamais de sphère créée pour ce cas.
    assert db_session.query(Sphere).count() == 2


# --- Départage d'égalité (spec section 8bis) — le Niveau 1 a déjà trouvé un tie ---


def test_departage_retourne_des_poids_parmi_les_candidats_donnes(db_session, monkeypatch, mocker):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-x")
    profile = _profile(db_session, plan=PlanTarifaire.RADAR_PLUS)
    _semer_spheres(db_session)
    candidats = [
        SuggestionSphere(sphere_id="cybersecurite", sphere_nom="Cybersécurité", score=2, mots_cles_matches=["a", "b"]),
        SuggestionSphere(
            sphere_id="logistique_transport_flotte",
            sphere_nom="Logistique / transport / gestion de flotte",
            score=2,
            mots_cles_matches=["c", "d"],
        ),
    ]
    _mock_reponse_anthropic(
        mocker,
        {
            "liens": [
                {"id": "cybersecurite", "poids": 70},
                {"id": "logistique_transport_flotte", "poids": 30},
            ],
            "confiance": "moyenne",
            "raisonnement": "Le contexte penche vers la cybersécurité.",
            "synonyme_a_retenir": None,
        },
    )

    suggestion = departager_spheres_niveau2(db_session, profile, "texte ambigu", candidats)

    assert {(l.sphere_id, l.poids) for l in suggestion.liens} == {
        ("cybersecurite", 70.0),
        ("logistique_transport_flotte", 30.0),
    }
    assert suggestion.candidat_diagnostic_id is None
