"""Tests du connecteur Licences d'affaires — Ville de Vancouver (spec
section 7, Signal registre_corporatif).

Les fonctions testées ici sont de la logique PURE, validée séparément contre
le vrai portail (205 329 lignes réelles, très à jour) — voir
docs/STATUT_RESEAU.md. Les fragments ci-dessous reproduisent le VRAI format
confirmé (champs Opendatasoft `businessname`/`unit`/`house`/`street`/...),
pas des données inventées au hasard."""
import responses

from falkye.models.licence_municipale_entry import LicenceMunicipaleEntry
from falkye.sources.licences_vancouver import API_URL, LicencesVancouverConnector, _composer_adresse, _parse_date

# Vraie ligne (tronquée) confirmée le 2026-09-01 — "Lululemon Athletica Canada Inc"
_LIGNE_REELLE_AVEC_UNITE = {
    "unit": "1100",
    "house": "1280",
    "street": "BURRARD ST",
    "city": "Vancouver",
    "province": "BC",
}

# Vraie ligne réelle sans adresse structurée (business à domicile/mobile,
# fréquent pour les praticiens individuels — voir docstring du module)
_LIGNE_REELLE_SANS_ADRESSE = {
    "unit": None,
    "house": None,
    "street": None,
    "city": "Vancouver",
    "province": "BC",
}


def test_parse_date_gere_les_vraies_dates_opendatasoft():
    dt = _parse_date("2025-11-17T18:52:44+00:00")
    assert dt is not None
    assert (dt.year, dt.month, dt.day) == (2025, 11, 17)


def test_parse_date_retourne_none_si_vide():
    assert _parse_date(None) is None
    assert _parse_date("") is None


def test_composer_adresse_avec_unite_complete():
    assert _composer_adresse(_LIGNE_REELLE_AVEC_UNITE) == "1100, 1280, BURRARD ST, Vancouver, BC"


def test_composer_adresse_se_limite_a_ville_province_si_rien_de_plus_structure():
    """Cas réel fréquent (voir docstring du module) : praticiens individuels
    sans unité/numéro/rue dans le jeu de données — l'adresse composée se
    limite alors à ville+province plutôt que d'inventer un numéro/une rue."""
    assert _composer_adresse(_LIGNE_REELLE_SANS_ADRESSE) == "Vancouver, BC"


def test_composer_adresse_retourne_none_si_absolument_rien():
    assert _composer_adresse({"unit": None, "house": None, "street": None, "city": None, "province": None}) is None


def test_composer_adresse_ignore_les_champs_numeriques_house_house_zero():
    """`house` est parfois un entier JSON (ex. 1280) plutôt qu'une chaîne —
    régression : str(None) donnerait littéralement "None" dans l'adresse
    sans la conversion explicite dans _composer_adresse."""
    ligne = {"unit": None, "house": 1280, "street": "BURRARD ST", "city": "Vancouver", "province": "BC"}
    adresse = _composer_adresse(ligne)
    assert "None" not in adresse
    assert "1280" in adresse


# ---------------------------------------------------------------------------
# Rebranchement sur le moteur de diff générique (Chantier 1, suivi
# 2026-09-04) — quarantaine AVANT tout signal ET avant toute mutation de
# LicenceMunicipaleEntry.
# ---------------------------------------------------------------------------
_URL_DATASTORE = API_URL


def _ligne_brute(numero, nom):
    return {
        "licencenumber": numero,
        "businessname": nom,
        "businesstype": "Type test",
        "issueddate": "2026-01-01T00:00:00+00:00",
        "status": "Issued",
        "unit": None,
        "house": "1",
        "street": "TEST ST",
        "city": "Vancouver",
        "province": "BC",
    }


def _reponse(lignes):
    return {"results": lignes}


@responses.activate
def test_vancouver_run_reference_amorce_etat_sans_signal(db_session, registry):
    lignes = [_ligne_brute(f"L{i}", f"Entreprise {i} inc.") for i in range(5)]
    responses.add(responses.GET, _URL_DATASTORE, json=_reponse(lignes), status=200)

    connector = LicencesVancouverConnector(source_def=registry.sources["licences_vancouver"])
    assert list(connector.detect(None, db_session)) == []


@responses.activate
def test_vancouver_quarantaine_ne_touche_pas_licencemunicipaleentry(db_session, registry):
    connector = LicencesVancouverConnector(source_def=registry.sources["licences_vancouver"])

    lignes_ref = [_ligne_brute(f"L{i:04d}", f"Entreprise {i} inc.") for i in range(300)]
    responses.add(responses.GET, _URL_DATASTORE, json=_reponse(lignes_ref), status=200)
    list(connector.detect(None, db_session))
    assert db_session.query(LicenceMunicipaleEntry).filter_by(municipalite="Vancouver").count() == 300

    responses.add(responses.GET, _URL_DATASTORE, json=_reponse([_ligne_brute("L9999", "Nouvelle inc.")]), status=200)
    signaux = list(connector.detect(None, db_session))
    assert signaux == []
    assert db_session.query(LicenceMunicipaleEntry).filter_by(municipalite="Vancouver").count() == 300
