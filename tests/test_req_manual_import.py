"""Tests du chemin d'import manuel par fichier pour le REQ (spec section 9) —
observador/sources/req.py:ingest_snapshot(fichier_local=...) et
observador/manual_import.py:importer_fichier_source.

IMPORTANT : le vrai schéma CSV du REQ reste NON CONFIRMÉ (accès réseau bloqué
pour cette session — voir docs/STATUT_RESEAU.md). Ces tests utilisent un CSV
local avec les en-têtes les plus probables (COLUMN_ALIASES) et des entreprises
CLAIREMENT FICTIVES pour valider la MÉCANIQUE (lecture d'un fichier local
plutôt qu'un téléchargement, diff/upsert, dédoublonnage, déclenchement du
pipeline complet) — pas pour prétendre valider le vrai mapping de colonnes,
qui ne sera confirmé qu'au premier import réel par Alexandre. Si les vraies
en-têtes diffèrent, resolve_columns() échouera explicitement (déjà testé dans
tests/test_column_mapping.py), pas silencieusement."""
import csv

from observador.manual_import import ImportManuelError, importer_fichier_source
from observador.models.req_entry import REQEntry
from observador.sources.req import ingest_snapshot


def _ecrire_csv_test(tmp_path, lignes):
    chemin = tmp_path / "req_test.csv"
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "NEQ",
                "NOM_ASSUJETTI",
                "STATUT_IMMAT",
                "ADRESSE_DOM",
                "VILLE_DOM",
                "CODE_POSTAL",
                "REGION_ADM",
                "CAE_PRINC",
                "DESC_CAE_PRINC",
                "DATE_MAJ",
            ]
        )
        writer.writerows(lignes)
    return str(chemin)


def test_ingest_snapshot_lit_un_fichier_local_sans_reseau(db_session, tmp_path):
    chemin = _ecrire_csv_test(
        tmp_path,
        [
            [
                "1111111111",
                "Entreprise Test Un inc.",
                "IMMATRICULEE",
                "1 rue Test",
                "Montréal",
                "H1H 1H1",
                "Montréal",
                "1234",
                "Secteur test",
                "2026-01-01",
            ]
        ],
    )
    stats = ingest_snapshot(db_session, fichier_local=chemin)
    assert stats.lignes_lues == 1
    assert stats.entrees_nouvelles == 1
    entry = db_session.get(REQEntry, "1111111111")
    assert entry is not None
    assert entry.nom == "Entreprise Test Un inc."
    assert entry.statut == "immatriculee"


def test_ingest_snapshot_detecte_changement_adresse_entre_deux_imports(db_session, tmp_path):
    chemin1 = _ecrire_csv_test(
        tmp_path,
        [
            [
                "2222222222",
                "Entreprise Test Deux inc.",
                "IMMATRICULEE",
                "1 rue A",
                "Québec",
                "G1G 1G1",
                "Capitale-Nationale",
                "1234",
                "Secteur test",
                "2026-01-01",
            ]
        ],
    )
    ingest_snapshot(db_session, fichier_local=chemin1)

    chemin2 = _ecrire_csv_test(
        tmp_path,
        [
            [
                "2222222222",
                "Entreprise Test Deux inc.",
                "IMMATRICULEE",
                "2 rue B",
                "Québec",
                "G2G 2G2",
                "Capitale-Nationale",
                "1234",
                "Secteur test",
                "2026-02-01",
            ]
        ],
    )
    stats2 = ingest_snapshot(db_session, fichier_local=chemin2)

    assert len(stats2.changements_adresse) == 1
    assert stats2.changements_adresse[0]["nouvelle_adresse"] == "2 rue B"


def test_importer_fichier_source_produit_des_signaux_et_dedoublonne(db_session, registry, tmp_path):
    chemin = _ecrire_csv_test(
        tmp_path,
        [
            [
                "3333333333",
                "Entreprise Test Trois inc.",
                "IMMATRICULEE",
                "1 rue Test",
                "Laval",
                "H7H 1H1",
                "Laval",
                "1234",
                "Secteur test",
                "2026-01-01",
            ]
        ],
    )

    signaux1 = importer_fichier_source(db_session, "req", chemin, registry=registry)
    assert len(signaux1) == 1
    assert signaux1[0].methode_acces == "import_manuel"
    assert signaux1[0].signal_type_id == "registre_corporatif"

    # Réimporter le même fichier ne doit pas créer de doublon (dédoublonnage
    # par source_ref, comme pour une source automatisée).
    signaux2 = importer_fichier_source(db_session, "req", chemin, registry=registry)
    assert signaux2 == []


def test_importer_fichier_source_refuse_source_pas_en_import_manuel(db_session, registry, tmp_path):
    chemin = _ecrire_csv_test(tmp_path, [])
    import pytest

    with pytest.raises(ImportManuelError, match="import_manuel"):
        importer_fichier_source(db_session, "seao", chemin, registry=registry)
