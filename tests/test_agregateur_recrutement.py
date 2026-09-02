"""Tests du connecteur générique agrégateur de recrutement (spec section 7 Signal 3,
section 9bis) — falkye/sources/agregateur_recrutement.py.

IMPORTANT (voir docstring du module testé) : la forme des réponses TheirStack/Apify
ci-dessous est une hypothèse plausible d'après la documentation publique, PAS une
vraie réponse capturée (les deux domaines sont bloqués par le proxy réseau de cet
environnement — aucun appel réel n'a pu être fait). Ces tests valident donc la
LOGIQUE de normalisation (tolérance à plusieurs noms de champs, rejet explicite si
un champ essentiel manque) contre des fixtures de schéma, pas contre des données
réelles — même distinction que pour n'importe quelle donnée d'entreprise fabriquée
(principe directeur #1) : aucun NOM D'ENTREPRISE RÉEL n'est inventé ici, seulement
une enveloppe JSON de test."""
from datetime import datetime, timezone

import responses

from falkye.sources.agregateur_recrutement import (
    APIFY_MAPPING_CHAMPS_DEFAUT,
    THEIRSTACK_URL,
    AgregateurRecrutementConnector,
    ApifyActeurGeneriqueProvider,
    OffreAgregateur,
    TheirStackProvider,
    _normaliser_apify,
    _normaliser_theirstack,
    fournisseur_depuis_env,
)


# --- _normaliser_theirstack : tolérance aux noms de champs plausibles ---


def test_normaliser_theirstack_forme_plate():
    item = {
        "company_name": "Entreprise Test Inc.",
        "job_title": "Chef de projet — implantation ERP",
        "id": "12345",
        "date_posted": "2026-08-15",
        "location": "Montréal",
        "url": "https://example.test/jobs/12345",
    }
    offre = _normaliser_theirstack(item)
    assert offre is not None
    assert offre.entreprise == "Entreprise Test Inc."
    assert offre.titre == "Chef de projet — implantation ERP"
    assert offre.source_ref == "theirstack:12345"
    assert offre.date_publication == datetime(2026, 8, 15, tzinfo=timezone.utc)


def test_normaliser_theirstack_forme_imbriquee():
    """Deuxième hypothèse plausible (company comme objet, pas une chaîne) —
    _premier doit essayer les deux avant d'abandonner."""
    item = {
        "company": {"name": "Autre Entreprise Inc."},
        "title": "Directeur de la transformation",
        "job_url": "https://example.test/jobs/999",
    }
    offre = _normaliser_theirstack(item)
    assert offre is not None
    assert offre.entreprise == "Autre Entreprise Inc."
    assert offre.source_ref == "theirstack:https://example.test/jobs/999"


def test_normaliser_theirstack_retourne_none_si_champ_essentiel_manque():
    """Pas de nom d'entreprise trouvable dans aucune des formes plausibles — aucun
    signal deviné (principe directeur #1)."""
    assert _normaliser_theirstack({"job_title": "Poste sans entreprise identifiable"}) is None


# --- _normaliser_apify ---


def test_normaliser_apify_avec_mapping_par_defaut():
    item = {
        "company": "Entreprise Apify Test",
        "title": "Gestionnaire d'amélioration continue",
        "url": "https://example.test/jobs/apify-1",
        "datePosted": "2026-08-20",
        "location": "Québec",
    }
    offre = _normaliser_apify(item, APIFY_MAPPING_CHAMPS_DEFAUT)
    assert offre is not None
    assert offre.entreprise == "Entreprise Apify Test"
    assert offre.source_ref == "apify:https://example.test/jobs/apify-1"


def test_normaliser_apify_mapping_personnalise():
    """Un acteur Apify différent (une fois choisi) peut nommer ses champs
    autrement — le mapping est injectable sans toucher au code."""
    item = {"employer": "Troisième Entreprise", "job_title": "Chef de projet", "link": "abc"}
    mapping = {**APIFY_MAPPING_CHAMPS_DEFAUT, "entreprise": "employer", "titre": "job_title", "ref": "link"}
    offre = _normaliser_apify(item, mapping)
    assert offre is not None
    assert offre.entreprise == "Troisième Entreprise"
    assert offre.source_ref == "apify:abc"


def test_normaliser_apify_retourne_none_si_champ_essentiel_manque():
    assert _normaliser_apify({"title": "Poste sans entreprise"}, APIFY_MAPPING_CHAMPS_DEFAUT) is None


# --- Sélection du fournisseur par variable d'environnement ---


def test_fournisseur_depuis_env_absent_par_defaut(monkeypatch):
    monkeypatch.delenv("FALKYE_AGREGATEUR_RECRUTEMENT_FOURNISSEUR", raising=False)
    assert fournisseur_depuis_env() is None


def test_fournisseur_depuis_env_theirstack_sans_cle_reste_none(monkeypatch):
    monkeypatch.setenv("FALKYE_AGREGATEUR_RECRUTEMENT_FOURNISSEUR", "theirstack")
    monkeypatch.delenv("FALKYE_THEIRSTACK_API_KEY", raising=False)
    assert fournisseur_depuis_env() is None


def test_fournisseur_depuis_env_theirstack_avec_cle(monkeypatch):
    monkeypatch.setenv("FALKYE_AGREGATEUR_RECRUTEMENT_FOURNISSEUR", "theirstack")
    monkeypatch.setenv("FALKYE_THEIRSTACK_API_KEY", "cle-test")
    fournisseur = fournisseur_depuis_env()
    assert isinstance(fournisseur, TheirStackProvider)


def test_fournisseur_depuis_env_apify_avec_token_et_acteur(monkeypatch):
    monkeypatch.setenv("FALKYE_AGREGATEUR_RECRUTEMENT_FOURNISSEUR", "apify")
    monkeypatch.setenv("FALKYE_APIFY_API_TOKEN", "token-test")
    monkeypatch.setenv("FALKYE_APIFY_ACTOR_ID", "acteur-test")
    fournisseur = fournisseur_depuis_env()
    assert isinstance(fournisseur, ApifyActeurGeneriqueProvider)


# --- TheirStackProvider.rechercher : appel HTTP mocké ---


@responses.activate
def test_theirstack_provider_rechercher_normalise_la_reponse():
    responses.add(
        responses.POST,
        THEIRSTACK_URL,
        json={
            "data": [
                {"company_name": "Fixture A", "job_title": "Chef de projet", "id": "1"},
                {"job_title": "Poste orphelin sans entreprise"},  # rejeté, champ manquant
            ]
        },
        status=200,
    )
    provider = TheirStackProvider(api_key="cle-test")
    offres = list(provider.rechercher(["chef de projet"], None, 50))
    assert len(offres) == 1
    assert offres[0].entreprise == "Fixture A"


# --- AgregateurRecrutementConnector : orchestration ---


def test_connector_disponible_faux_sans_fournisseur(registry):
    source_def = registry.sources["agregateur_recrutement_tiers"]
    connector = AgregateurRecrutementConnector(source_def, fournisseur=None)
    assert connector.disponible() is False
    assert list(connector.detect(None, db_session=None)) == []


class _FournisseurFactice:
    def rechercher(self, mots_cles, since, limit):
        yield OffreAgregateur(
            entreprise="Entreprise Factice Inc.",
            titre="Directeur de la transformation numérique",
            source_ref="factice:1",
            date_publication=datetime(2026, 8, 1, tzinfo=timezone.utc),
            ville="Montréal",
        )


def test_connector_detect_produit_un_rawsignal_recrutement_massif(registry):
    source_def = registry.sources["agregateur_recrutement_tiers"]
    connector = AgregateurRecrutementConnector(source_def, fournisseur=_FournisseurFactice())
    signaux = list(connector.detect(None, db_session=None))
    assert len(signaux) == 1
    assert signaux[0].signal_type_id == "recrutement_massif"
    assert signaux[0].nom_entreprise == "Entreprise Factice Inc."
    assert signaux[0].source_ref == "factice:1"
