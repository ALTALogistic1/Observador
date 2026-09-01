"""Tests du mécanisme générique d'import manuel (falkye/manual_import.py)
— spec section 9, "Import manuel de documents sources". Utilise le vrai
registre (RDPRM y est configuré en import_manuel) plutôt qu'une source
fabriquée, pour valider le chemin réel."""
import pytest

from falkye.manual_import import ImportManuelError, importer_document_manuel


def test_import_reussit_pour_une_source_en_import_manuel(db_session, registry):
    signal = importer_document_manuel(
        db_session,
        "rdprm",
        "Entreprise Test inc.",
        valeur_associee=75000,
        champs={"nature_bien": "équipement de production"},
        importe_par="test@exemple.com",
        registry=registry,
    )
    assert signal.id is not None
    assert signal.source_id == "rdprm"
    assert signal.methode_acces == "import_manuel"
    assert signal.importe_par == "test@exemple.com"
    assert signal.valeur_associee == 75000
    assert signal.company.nom_detecte == "Entreprise Test inc."


def test_import_refuse_source_qui_n_est_pas_en_import_manuel(db_session, registry):
    with pytest.raises(ImportManuelError, match="import_manuel"):
        importer_document_manuel(db_session, "seao", "Entreprise Test inc.", registry=registry)


def test_import_refuse_source_inconnue(db_session, registry):
    with pytest.raises(ImportManuelError, match="inconnue"):
        importer_document_manuel(db_session, "source_qui_n_existe_pas", "Entreprise Test", registry=registry)


def test_deux_imports_meme_entreprise_non_resolue_restent_un_seul_dossier(db_session, registry):
    s1 = importer_document_manuel(db_session, "rdprm", "Entreprise Fantome inc.", registry=registry)
    s2 = importer_document_manuel(db_session, "rdprm", "Entreprise Fantome inc.", registry=registry)
    assert s1.company_id == s2.company_id  # dossier cumulatif, spec section 5
