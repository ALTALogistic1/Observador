"""Tests du connecteur Licences d'affaires — Ville de Toronto (spec section
7, Signal registre_corporatif).

Les fonctions testées ici sont de la logique PURE, validée séparément contre
le vrai portail CKAN (159 647 lignes réelles, historique depuis 1946) — voir
docs/STATUT_RESEAU.md. Les fragments ci-dessous reproduisent le VRAI format
confirmé (champs `Client Name`/`Licence Address Line 1-3`, et le quirk réel
où un champ texte vide est encodé par la chaîne littérale "None"), pas des
données inventées au hasard."""
from observador.sources.licences_toronto import (
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
