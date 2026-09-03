"""Tests du Niveau 2 de l'assistance à la configuration du profil par IA,
dimension "qui" (falkye/assistance_client_cible_ia.py) — spec section 8bis
(2026-09-03). Miroir condensé de tests/test_assistance_sphere_ia.py — le
moteur partagé (falkye/assistance_ia.py) est déjà testé en détail là-bas ;
ici on vérifie surtout ce qui est SPÉCIFIQUE à "qui" (la sentinelle unique,
"aucune_restriction" comme membre normal du catalogue)."""
import json
from types import SimpleNamespace

import pytest

from falkye.assistance_client_cible_ia import (
    AssistanceIANonConfiguree,
    PlanInsuffisantPourAssistanceIA,
    suggerer_clients_cibles_niveau2,
)
from falkye.models.client_cible import ClientCible
from falkye.models.diagnostic_journal import DiagnosticJournal, TypeDiagnostic
from falkye.models.profile import PlanTarifaire, Profile


def _profile(db_session, plan=PlanTarifaire.RADAR):
    p = Profile(courriel="test@exemple.com", nom="Profil Test", plan=plan)
    db_session.add(p)
    db_session.flush()
    return p


def _semer_categories(db_session):
    db_session.add_all(
        [
            ClientCible(id="aucune_restriction", nom="Aucune restriction — s'applique largement"),
            ClientCible(id="organismes_publics_institutionnels", nom="Organismes publics et institutionnels"),
        ]
    )
    db_session.flush()


def _mock_reponse_anthropic(mocker, payload: dict):
    reponse = SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(payload))])
    mock_client = mocker.Mock()
    mock_client.messages.create.return_value = reponse
    mocker.patch("anthropic.Anthropic", return_value=mock_client)


def test_leve_si_plan_echo(db_session):
    profile = _profile(db_session, plan=PlanTarifaire.ECHO)
    with pytest.raises(PlanInsuffisantPourAssistanceIA):
        suggerer_clients_cibles_niveau2(db_session, profile, "une description")


def test_leve_si_cle_manquante(db_session, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    profile = _profile(db_session, plan=PlanTarifaire.RADAR)
    with pytest.raises(AssistanceIANonConfiguree):
        suggerer_clients_cibles_niveau2(db_session, profile, "une description")


def test_aucune_restriction_selectionnee_normalement_pas_une_sentinelle(db_session, monkeypatch, mocker):
    """"aucune_restriction" est un id du catalogue comme un autre — le modèle
    le sélectionne via `liens`, pas via un champ sentinelle séparé."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-x")
    profile = _profile(db_session, plan=PlanTarifaire.RADAR)
    _semer_categories(db_session)
    _mock_reponse_anthropic(
        mocker,
        {
            "liens": [{"id": "aucune_restriction", "poids": 100}],
            "sentinelle": None,
            "confiance": "elevee",
            "raisonnement": "Le texte indique explicitement une clientèle non restreinte.",
            "synonyme_a_retenir": None,
        },
    )

    suggestion = suggerer_clients_cibles_niveau2(db_session, profile, "On travaille avec n'importe quel type de client")

    assert len(suggestion.liens) == 1
    assert suggestion.liens[0].client_cible_id == "aucune_restriction"
    assert suggestion.candidat_diagnostic_id is None


def test_aucune_correspondance_journalise_un_diagnostic_client_cible(db_session, monkeypatch, mocker):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-x")
    profile = _profile(db_session, plan=PlanTarifaire.RADAR)
    _semer_categories(db_session)
    _mock_reponse_anthropic(
        mocker,
        {
            "liens": [],
            "sentinelle": "aucune_correspondance",
            "confiance": "faible",
            "raisonnement": "Ni une catégorie précise, ni une clientèle non restreinte ne ressort du texte.",
            "synonyme_a_retenir": None,
        },
    )

    suggestion = suggerer_clients_cibles_niveau2(db_session, profile, "Texte totalement ambigu sur la clientèle")

    assert suggestion.liens == []
    candidat = db_session.get(DiagnosticJournal, suggestion.candidat_diagnostic_id)
    assert candidat.type_diagnostic == TypeDiagnostic.CANDIDAT_CLIENT_CIBLE
    assert candidat.profile_id == profile.id
