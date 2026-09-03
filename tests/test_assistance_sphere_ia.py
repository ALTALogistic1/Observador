"""Tests du Niveau 2 de l'assistance à la configuration du profil par IA
(falkye/assistance_sphere_ia.py). Le SDK anthropic est entièrement mocké — voir
docstring du module testé : jamais exécuté contre une vraie clé API dans cet
environnement de développement (même situation que Stripe/HubSpot/Pipedrive)."""
import json
from types import SimpleNamespace

import pytest

from falkye.assistance_sphere_ia import (
    AssistanceIANonConfiguree,
    PlanInsuffisantPourAssistanceIA,
    _construire_schema_sortie,
    suggerer_sphere_niveau2,
)
from falkye.models.candidat_sphere import CandidatSphere
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


# --- Gating de plan / configuration ---


def test_leve_si_plan_echo(db_session, monkeypatch, mocker):
    profile = _profile(db_session, plan=PlanTarifaire.ECHO)
    mock_anthropic_cls = mocker.patch("anthropic.Anthropic")
    with pytest.raises(PlanInsuffisantPourAssistanceIA):
        suggerer_sphere_niveau2(db_session, profile, "une description")
    mock_anthropic_cls.assert_not_called()


def test_leve_si_cle_manquante(db_session, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    profile = _profile(db_session, plan=PlanTarifaire.RADAR)
    with pytest.raises(AssistanceIANonConfiguree):
        suggerer_sphere_niveau2(db_session, profile, "une description")


# --- Sortie contrainte au catalogue fermé (le garde-fou structurel) ---


def test_schema_sortie_enum_est_le_catalogue_plus_la_sentinelle():
    schema = _construire_schema_sortie(["cybersecurite", "logistique_transport_flotte"])
    enum_sphere_id = schema["schema"]["properties"]["sphere_id"]["enum"]
    assert enum_sphere_id == ["cybersecurite", "logistique_transport_flotte", "aucune_correspondance"]
    assert schema["schema"]["additionalProperties"] is False


# --- Sphère existante trouvée : enrichissement silencieux, jamais de création ---


def test_sphere_existante_retournee_et_synonyme_enregistre(db_session, monkeypatch, mocker):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-x")
    profile = _profile(db_session, plan=PlanTarifaire.RADAR_PLUS)
    _semer_spheres(db_session)
    _mock_reponse_anthropic(
        mocker,
        {
            "sphere_id": "cybersecurite",
            "confiance": "elevee",
            "raisonnement": "L'utilisateur décrit des tests d'intrusion.",
            "synonyme_a_retenir": "pentest",
        },
    )

    suggestion = suggerer_sphere_niveau2(db_session, profile, "On fait du pentest pour des PME")

    assert suggestion.sphere_id == "cybersecurite"
    assert suggestion.sphere_nom == "Cybersécurité"
    assert suggestion.confiance == "elevee"
    assert suggestion.synonyme_retenu == "pentest"
    assert suggestion.candidat_sphere_id is None

    ligne = (
        db_session.query(SphereSynonyme)
        .filter_by(sphere_id="cybersecurite", texte="pentest")
        .one()
    )
    assert ligne.origine == "ia_niveau2"

    # Jamais de création de sphère — seules les 2 semées existent toujours.
    assert db_session.query(Sphere).count() == 2


def test_ne_duplique_pas_un_synonyme_deja_present(db_session, monkeypatch, mocker):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-x")
    profile = _profile(db_session, plan=PlanTarifaire.RADAR)
    _semer_spheres(db_session)
    db_session.add(SphereSynonyme(sphere_id="cybersecurite", texte="Pentest", origine="registre"))
    db_session.flush()
    _mock_reponse_anthropic(
        mocker,
        {
            "sphere_id": "cybersecurite",
            "confiance": "moyenne",
            "raisonnement": "correspond",
            "synonyme_a_retenir": "pentest",
        },
    )

    suggestion = suggerer_sphere_niveau2(db_session, profile, "pentest pour PME")

    assert suggestion.synonyme_retenu is None
    assert db_session.query(SphereSynonyme).filter_by(sphere_id="cybersecurite").count() == 1


# --- Aucune correspondance : journalisé, jamais de sphère créée ---


def test_aucune_correspondance_journalise_un_candidat(db_session, monkeypatch, mocker):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-x")
    profile = _profile(db_session, plan=PlanTarifaire.RADAR)
    _semer_spheres(db_session)
    _mock_reponse_anthropic(
        mocker,
        {
            "sphere_id": "aucune_correspondance",
            "confiance": "faible",
            "raisonnement": "Aucune sphère du catalogue ne couvre l'apiculture urbaine.",
            "synonyme_a_retenir": None,
        },
    )

    suggestion = suggerer_sphere_niveau2(db_session, profile, "Conseil en apiculture urbaine")

    assert suggestion.sphere_id is None
    assert suggestion.sphere_nom is None
    assert suggestion.candidat_sphere_id is not None

    candidat = db_session.get(CandidatSphere, suggestion.candidat_sphere_id)
    assert candidat.profile_id == profile.id
    assert candidat.texte_description == "Conseil en apiculture urbaine"
    assert candidat.statut == "a_examiner"

    # Jamais de sphère créée pour ce cas.
    assert db_session.query(Sphere).count() == 2


# --- Cas réel volontairement ambigu (retenu par Alexandre le 2026-09-03, en
# retirant "gestion_inventaire_actifs" du registre — voir registry/spheres.yaml
# et docs/ARCHITECTURE.md, section "Extensibilité des sphères de besoin") ---


def test_cas_reel_ambigu_gestion_inventaire_logistique_vs_ti(db_session, monkeypatch, mocker):
    """"Spécialiste de gestion d'inventaire et en implantation de solutions
    logistiques" (le cas d'usage d'origine du projet, Alexandre lui-même) ne
    correspond à aucune sphère dédiée depuis le retrait de
    "gestion_inventaire_actifs" du registre — volontairement ambigu entre
    Logistique/transport/gestion de flotte et Technologie/systèmes/TI, sans
    réponse évidente d'avance (confirmé côté Niveau 1 : aucune correspondance
    locale, voir tests/test_assistance_sphere.py). Ce test valide que le
    Niveau 2 reste capable de trancher — vers L'UNE des deux sphères
    plausibles, jamais une troisième inventée — sur cette description réelle,
    pas seulement sur un exemple synthétique."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-x")
    profile = _profile(db_session, plan=PlanTarifaire.RADAR_PLUS)
    _semer_spheres(db_session)  # cybersecurite + logistique_transport_flotte
    db_session.add(Sphere(id="technologie_systemes_ti", nom="Technologie / systèmes / TI"))
    db_session.flush()

    _mock_reponse_anthropic(
        mocker,
        {
            "sphere_id": "logistique_transport_flotte",
            "confiance": "moyenne",
            "raisonnement": (
                "La gestion d'inventaire et l'implantation de solutions logistiques "
                "relèvent d'abord de la chaîne logistique ; Technologie/systèmes/TI "
                "serait aussi défendable, mais le vocabulaire employé (inventaire, "
                "solutions logistiques) penche vers la logistique elle-même."
            ),
            "synonyme_a_retenir": "solutions logistiques",
        },
    )

    suggestion = suggerer_sphere_niveau2(
        db_session,
        profile,
        "Spécialiste de gestion d'inventaire et en implantation de solutions logistiques",
    )

    # Le résultat retenu par le modèle est L'UNE des deux sphères plausibles du
    # catalogue — jamais une autre, jamais inventée (garde-fou structurel).
    assert suggestion.sphere_id in {"logistique_transport_flotte", "technologie_systemes_ti"}
    assert suggestion.candidat_sphere_id is None
    assert suggestion.synonyme_retenu == "solutions logistiques"
