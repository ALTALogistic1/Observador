"""Tests du connecteur Licences d'affaires — Ville de Toronto (spec section
7, Signal registre_corporatif).

Les fonctions testées ici sont de la logique PURE, validée séparément contre
le vrai portail CKAN (159 647 lignes réelles, historique depuis 1946) — voir
docs/STATUT_RESEAU.md. Les fragments ci-dessous reproduisent le VRAI format
confirmé (champs `Client Name`/`Licence Address Line 1-3`, et le quirk réel
où un champ texte vide est encodé par la chaîne littérale "None"), pas des
données inventées au hasard."""
import responses

from falkye.models.licence_municipale_entry import LicenceMunicipaleEntry
from falkye.sources.licences_toronto import (
    CKAN_BASE,
    LicencesTorontoConnector,
    _composer_adresse,
    _nettoyer,
    _parse_date,
    _ville_province,
)

# Vraie ligne (tronquée) confirmée le 2026-09-01 — "9003088 CANADA CORP"
_LIGNE_REELLE = {
    "Licence Address Line 1": "2124 LAWRENCE AVE E",
    "Licence Address Line 2": "TORONTO, ON",
    "Licence Address Line 3": "M1R 3A3",
}

# Vraie ligne "junk" confirmée (artefact réel du jeu de données, catégorie
# "** Class record not on file. (138)") — tous les champs texte valent la
# chaîne littérale "None", pas un JSON null.
_LIGNE_JUNK = {
    "Licence No.": "None",
    "Client Name": "None",
    "Licence Address Line 1": "None",
    "Licence Address Line 2": "None",
    "Licence Address Line 3": "None",
}


def test_nettoyer_traite_la_chaine_none_comme_vide():
    """Régression du quirk réel : ce portail encode un champ texte vide par
    la chaîne littérale "None", pas un JSON null."""
    assert _nettoyer("None") is None
    assert _nettoyer(None) is None
    assert _nettoyer("") is None


def test_nettoyer_garde_les_vraies_valeurs():
    assert _nettoyer(" TIM WEBSTER INVESTMENTS INC ") == "TIM WEBSTER INVESTMENTS INC"


def test_parse_date_gere_les_vraies_dates_et_le_quirk_none():
    dt = _parse_date("2026-10-01")
    assert dt is not None
    assert (dt.year, dt.month, dt.day) == (2026, 10, 1)
    assert _parse_date("None") is None
    assert _parse_date(None) is None


def test_composer_adresse_avec_une_vraie_ligne():
    assert _composer_adresse(_LIGNE_REELLE) == "2124 LAWRENCE AVE E, TORONTO, ON, M1R 3A3"


def test_composer_adresse_retourne_none_pour_une_ligne_junk():
    """Régression : une ligne "junk" du jeu de données (tous les champs à la
    chaîne "None") ne doit produire aucune adresse inventée."""
    assert _composer_adresse(_LIGNE_JUNK) is None


def test_ville_province_separe_le_vrai_format():
    assert _ville_province(_LIGNE_REELLE) == ("TORONTO", "ON")


def test_ville_province_gere_l_absence():
    assert _ville_province(_LIGNE_JUNK) == (None, None)


# ---------------------------------------------------------------------------
# Rebranchement sur le moteur de diff générique (Chantier 1, suivi
# 2026-09-04) — quarantaine AVANT tout signal ET avant toute mutation de
# LicenceMunicipaleEntry.
# ---------------------------------------------------------------------------
_URL_DATASTORE = f"{CKAN_BASE}/api/3/action/datastore_search"


def _ligne_brute(numero, nom):
    return {
        "Licence No.": numero,
        "Client Name": nom,
        "Category": "Type test",
        "Issued": "2026-01-01",
        "Cancel Date": "",
        "Licence Address Line 1": "1 rue Test",
        "Licence Address Line 2": "TORONTO, ON",
        "Licence Address Line 3": "",
        "Operating Name": nom,
    }


def _reponse(lignes):
    return {"success": True, "result": {"records": lignes}}


@responses.activate
def test_toronto_run_reference_amorce_etat_sans_signal(db_session, registry):
    lignes = [_ligne_brute(f"L{i}", f"Entreprise {i} inc.") for i in range(5)]
    responses.add(responses.GET, _URL_DATASTORE, json=_reponse(lignes), status=200)

    connector = LicencesTorontoConnector(source_def=registry.sources["licences_toronto"])
    assert list(connector.detect(None, db_session)) == []


@responses.activate
def test_toronto_quarantaine_ne_touche_pas_licencemunicipaleentry(db_session, registry):
    connector = LicencesTorontoConnector(source_def=registry.sources["licences_toronto"])

    # Run de référence : 300 licences réelles distinctes.
    lignes_ref = [_ligne_brute(f"L{i:04d}", f"Entreprise {i} inc.") for i in range(300)]
    responses.add(responses.GET, _URL_DATASTORE, json=_reponse(lignes_ref), status=200)
    list(connector.detect(None, db_session))
    assert db_session.query(LicenceMunicipaleEntry).filter_by(municipalite="Toronto").count() == 300

    # Deuxième run : plus AUCUNE des 300 licences précédentes (disparitions
    # massives), une seule licence nouvelle sans rapport.
    responses.add(responses.GET, _URL_DATASTORE, json=_reponse([_ligne_brute("L9999", "Nouvelle inc.")]), status=200)
    signaux = list(connector.detect(None, db_session))
    assert signaux == []
    # LicenceMunicipaleEntry INTACT — ni la nouvelle licence, ni les 300 précédentes retirées.
    assert db_session.query(LicenceMunicipaleEntry).filter_by(municipalite="Toronto").count() == 300
