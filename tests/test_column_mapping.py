"""Tests des utilitaires de résolution de colonnes CSV (falkye/sources/column_mapping.py)
— importants car REQ et Guichet-Emplois dépendent de cette résolution robuste plutôt
que de noms de colonnes codés en dur (voir notes dans req.py/guichet_emplois.py)."""
import pytest

from falkye.sources.column_mapping import normaliser, resolve_columns


def test_normaliser_enleve_accents_et_ponctuation():
    assert normaliser("Numéro d'Entreprise du Québec") == "numero d entreprise du quebec"


def test_resolve_columns_trouve_alias_exact():
    fieldnames = ["NEQ", "Nom_Assujetti", "Statut_Immat"]
    aliases = {"neq": ["neq"], "nom": ["nom_assujetti"], "statut": ["statut_immat"]}
    resolved = resolve_columns(fieldnames, aliases)
    assert resolved == {"neq": "NEQ", "nom": "Nom_Assujetti", "statut": "Statut_Immat"}


def test_resolve_columns_leve_erreur_explicite_si_colonne_manquante():
    fieldnames = ["NEQ", "AutreChose"]
    aliases = {"neq": ["neq"], "nom": ["nom_assujetti", "nom_entreprise"]}
    with pytest.raises(ValueError) as excinfo:
        resolve_columns(fieldnames, aliases)
    assert "nom" in str(excinfo.value)
    assert "AutreChose" in str(excinfo.value)  # les en-têtes réelles sont dans le message
