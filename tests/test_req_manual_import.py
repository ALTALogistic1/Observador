"""Tests du chemin d'import manuel par fichier pour le REQ (spec section 9) —
falkye/sources/req.py:ingest_snapshot(fichier_local=...) et
falkye/manual_import.py:importer_fichier_source.

Deux générations de tests dans ce fichier :
  1. Le chemin "fichier plat" LEGACY (_ecrire_csv_test, COLUMN_ALIASES) — des
     hypothèses de colonnes écrites AVANT l'inspection réelle du fichier REQ,
     qui ne correspondent PAS au vrai fichier (jamais un CSV plat). Gardées
     uniquement pour valider la mécanique générique (dédoublonnage,
     déclenchement du pipeline) et le repli réseau dormant
     (REQConnector.detect) — pas pour prétendre valider le vrai schéma.
  2. Le chemin RÉEL (_ecrire_zip_req_reel) — Entreprise.csv + Nom.csv +
     Etablissements.csv avec les VRAIES colonnes, confirmées le 2026-08-31 par
     Alexandre via `import-manuel inspecter` sur le vrai fichier téléchargé
     depuis son navigateur (SHA-256 vérifié). Ces tests utilisent des
     entreprises CLAIREMENT FICTIVES mais un schéma de colonnes RÉEL — voir
     docs/STATUT_RESEAU.md pour le détail complet de la découverte.

Note de calibration (spec section 6) : une NOUVELLE IMMATRICULATION seule
(aucun établissement secondaire, aucun changement d'adresse) ne produit PLUS
de signal, dans aucun des deux chemins — une entreprise qui vient de naître
n'est pas une entreprise EN croissance. Voir _stats_vers_signaux."""
import csv
import zipfile

import pytest

from falkye.manual_import import ImportManuelError, importer_fichier_source
from falkye.models.req_entry import REQEntry
from falkye.models.req_etablissement_entry import REQEtablissementEntry
from falkye.sources.req import REQConnector, ingest_snapshot, inspect_zip

# ---------------------------------------------------------------------------
# Chemin legacy (fichier plat) — mécanique générique uniquement
# ---------------------------------------------------------------------------


def _ecrire_csv_test(tmp_path, lignes, nom_fichier="req_test.csv"):
    chemin = tmp_path / nom_fichier
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
        nom_fichier="req_test_1.csv",
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
        nom_fichier="req_test_2.csv",
    )
    stats2 = ingest_snapshot(db_session, fichier_local=chemin2)

    assert len(stats2.changements_adresse) == 1
    assert stats2.changements_adresse[0]["nouvelle_adresse"] == "2 rue B"


def test_importer_fichier_source_produit_des_signaux_et_dedoublonne(db_session, registry, tmp_path):
    # Import de référence (baseline) : aucun signal — une simple immatriculation
    # n'est pas un signal de croissance (voir note de calibration en tête de fichier).
    chemin1 = _ecrire_csv_test(
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
        nom_fichier="req_test_1.csv",
    )
    signaux0 = importer_fichier_source(db_session, "req", chemin1, registry=registry)
    assert signaux0 == []

    # Deuxième import avec changement d'adresse du siège -> UN signal (moyen).
    chemin2 = _ecrire_csv_test(
        tmp_path,
        [
            [
                "3333333333",
                "Entreprise Test Trois inc.",
                "IMMATRICULEE",
                "2 rue Nouvelle",
                "Laval",
                "H7H 2H2",
                "Laval",
                "1234",
                "Secteur test",
                "2026-02-01",
            ]
        ],
        nom_fichier="req_test_2.csv",
    )
    signaux1 = importer_fichier_source(db_session, "req", chemin2, registry=registry)
    assert len(signaux1) == 1
    assert signaux1[0].methode_acces == "import_manuel"
    assert signaux1[0].signal_type_id == "registre_corporatif"

    # Réimporter le même fichier ne doit pas créer de doublon (dédoublonnage
    # par source_ref, comme pour une source automatisée).
    signaux2 = importer_fichier_source(db_session, "req", chemin2, registry=registry)
    assert signaux2 == []


def test_importer_fichier_source_refuse_source_pas_en_import_manuel(db_session, registry, tmp_path):
    chemin = _ecrire_csv_test(tmp_path, [])

    with pytest.raises(ImportManuelError, match="import_manuel"):
        importer_fichier_source(db_session, "seao", chemin, registry=registry)


# ---------------------------------------------------------------------------
# Garde-fou multi-CSV générique + inspecteur
# ---------------------------------------------------------------------------


def _ecrire_zip_multi_csv(tmp_path, fichiers: dict[str, list[list[str]]], nom_zip="req_multi.zip"):
    """Construit un .zip avec plusieurs CSV distincts à l'intérieur, avec des
    en-têtes/valeurs clairement fictives, pour valider le comportement de garde
    (échec explicite) et l'inspecteur — pas un vrai mapping de colonnes."""
    chemin = tmp_path / nom_zip
    with zipfile.ZipFile(chemin, "w") as zf:
        for nom, lignes in fichiers.items():
            buffer = "\n".join(",".join(ligne) for ligne in lignes)
            zf.writestr(nom, buffer)
    return str(chemin)


def test_ingest_snapshot_refuse_un_zip_a_plusieurs_csv_inconnu_plutot_que_de_les_fusionner(db_session, tmp_path):
    # Seulement 2 des 3 fichiers réels requis (Nom.csv manque) -> pas reconnu
    # comme le vrai fichier REQ, donc pas de fusion silencieuse non plus.
    chemin = _ecrire_zip_multi_csv(
        tmp_path,
        {
            "Entreprise.csv": [["NEQ", "NOM"], ["1234567890", "Entreprise Test inc."]],
            "Etablissements.csv": [["NEQ", "ADRESSE"], ["1234567890", "1 rue Test"]],
        },
    )
    with pytest.raises(RuntimeError, match="Entreprise.csv"):
        ingest_snapshot(db_session, fichier_local=chemin)


def test_inspect_zip_lit_en_tete_et_exemple_de_chaque_csv_sans_les_fusionner(tmp_path):
    chemin = _ecrire_zip_multi_csv(
        tmp_path,
        {
            "Entreprise.csv": [["NEQ", "NOM"], ["1234567890", "Entreprise Test inc."]],
            "Etablissements.csv": [["NEQ", "ADRESSE"], ["1234567890", "1 rue Test"]],
        },
    )
    infos = inspect_zip(chemin)

    assert set(infos.keys()) == {"Entreprise.csv", "Etablissements.csv"}
    assert infos["Entreprise.csv"]["colonnes"] == ["NEQ", "NOM"]
    assert infos["Entreprise.csv"]["exemple"] == {"NEQ": "1234567890", "NOM": "Entreprise Test inc."}
    assert infos["Etablissements.csv"]["colonnes"] == ["NEQ", "ADRESSE"]


def test_req_connector_inspect_file_delegue_a_inspect_zip(tmp_path, registry):
    chemin = _ecrire_zip_multi_csv(tmp_path, {"Entreprise.csv": [["NEQ", "NOM"]]})
    connector = REQConnector(source_def=registry.sources["req"])
    infos = connector.inspect_file(chemin)
    assert "Entreprise.csv" in infos


# ---------------------------------------------------------------------------
# Chemin RÉEL (Entreprise.csv + Nom.csv + Etablissements.csv, vraies colonnes
# confirmées le 2026-08-31 — voir docs/STATUT_RESEAU.md)
# ---------------------------------------------------------------------------

_ENTETE_ENTREPRISE = [
    "NEQ",
    "COD_STAT_IMMAT",
    "DAT_MAJ_INDEX_NOM",
    "COD_ACT_ECON_CAE",
    "DESC_ACT_ECON_ASSUJ",
    "ADR_DOMCL_ADR_DISP",
    "ADR_DOMCL_LIGN1_ADR",
    "ADR_DOMCL_LIGN2_ADR",
    "ADR_DOMCL_LIGN3_ADR",
    "ADR_DOMCL_LIGN4_ADR",
]
_ENTETE_NOM = ["NEQ", "NOM_ASSUJ", "STAT_NOM", "TYP_NOM_ASSUJ", "DAT_INIT_NOM_ASSUJ", "DAT_FIN_NOM_ASSUJ"]
_ENTETE_ETABLISSEMENTS = [
    "NEQ",
    "NO_SUF_ETAB",
    "IND_ETAB_PRINC",
    "LIGN1_ADR",
    "LIGN2_ADR",
    "LIGN3_ADR",
    "LIGN4_ADR",
    "COD_ACT_ECON",
    "DESC_ACT_ECON_ETAB",
    "NOM_ETAB",
]


def _ecrire_zip_req_reel(tmp_path, *, entreprises, noms, etablissements, nom_zip="req_reel.zip"):
    """Construit un .zip avec la vraie structure à 3 CSV requise (Entreprise.csv
    + Nom.csv + Etablissements.csv), en-têtes réelles, entreprises fictives."""
    chemin = tmp_path / nom_zip

    def _buf(entete, lignes):
        w = [",".join(entete)]
        w += [",".join(str(v) for v in ligne) for ligne in lignes]
        return "\n".join(w)

    with zipfile.ZipFile(chemin, "w") as zf:
        zf.writestr("Entreprise.csv", _buf(_ENTETE_ENTREPRISE, entreprises))
        zf.writestr("Nom.csv", _buf(_ENTETE_NOM, noms))
        zf.writestr("Etablissements.csv", _buf(_ENTETE_ETABLISSEMENTS, etablissements))
    return str(chemin)


def test_ingest_zip_reel_joint_nom_et_adresse_via_etablissement_principal(db_session, tmp_path):
    chemin = _ecrire_zip_req_reel(
        tmp_path,
        entreprises=[["9990000001", "IM", "2026-01-01", "7311", "", "N", "", "", "", ""]],
        noms=[["9990000001", "Entreprise Fictive Alpha inc.", "V", "N", "1994-01-01", ""]],
        etablissements=[
            [
                "9990000001",
                "1",
                "O",
                "100 rue Fictive",
                "Montréal (Québec)",
                "",
                "H1H1H1",
                "7311",
                "Services fictifs",
                "Entreprise Fictive Alpha inc.",
            ]
        ],
    )
    stats = ingest_snapshot(db_session, fichier_local=chemin)
    assert stats.lignes_lues == 1
    assert stats.entrees_nouvelles == 1

    entry = db_session.get(REQEntry, "9990000001")
    assert entry.nom == "Entreprise Fictive Alpha inc."
    assert entry.statut == "immatriculee"
    assert entry.adresse == "100 rue Fictive"
    assert entry.ville == "Montréal"
    assert entry.code_postal == "H1H1H1"
    assert entry.secteur_libelle == "Services fictifs"
    # Pas de région administrative dans le vrai schéma REQ — voir docstring du module.
    assert entry.region is None


def test_ingest_zip_reel_decode_les_codes_statut_radies(db_session, tmp_path):
    for code, statut_attendu in [("RD", "radiee"), ("RO", "radiee"), ("RX", "radiee"), ("IM", "immatriculee")]:
        chemin = _ecrire_zip_req_reel(
            tmp_path,
            entreprises=[[f"999000{code}", code, "2026-01-01", "", "", "N", "", "", "", ""]],
            noms=[[f"999000{code}", "Entreprise Fictive inc.", "V", "N", "1994-01-01", ""]],
            etablissements=[],
            nom_zip=f"req_{code}.zip",
        )
        ingest_snapshot(db_session, fichier_local=chemin)
        entry = db_session.get(REQEntry, f"999000{code}")
        assert entry.statut == statut_attendu, f"code {code}"


def test_ingest_zip_reel_prefere_le_nom_en_vigueur_au_nom_anterieur(db_session, tmp_path):
    # Deux lignes Nom.csv pour le même NEQ : un ancien nom (A) et le nom actuel
    # (V) — l'ordre des lignes ne doit pas influencer le choix.
    chemin = _ecrire_zip_req_reel(
        tmp_path,
        entreprises=[["9990000002", "IM", "2026-01-01", "", "", "N", "", "", "", ""]],
        noms=[
            ["9990000002", "Ancien Nom Fictif inc.", "A", "M", "1994-01-01", "2010-01-01"],
            ["9990000002", "Nouveau Nom Fictif inc.", "V", "N", "2010-01-01", ""],
        ],
        etablissements=[],
    )
    ingest_snapshot(db_session, fichier_local=chemin)
    entry = db_session.get(REQEntry, "9990000002")
    assert entry.nom == "Nouveau Nom Fictif inc."


def test_ingest_zip_reel_repli_sur_nom_anterieur_le_plus_recent_si_aucun_nom_en_vigueur(db_session, tmp_path):
    # Entreprise radiée : plus aucun nom "en vigueur" (confirmé sur un vrai NEQ
    # radié le 2026-08-31) — on retient le nom antérieur le plus récent.
    chemin = _ecrire_zip_req_reel(
        tmp_path,
        entreprises=[["9990000003", "RO", "2026-01-01", "", "", "N", "", "", "", ""]],
        noms=[
            ["9990000003", "Premier Nom Fictif inc.", "A", "N", "1994-01-01", "1997-01-01"],
            ["9990000003", "Dernier Nom Fictif inc.", "A", "N", "1997-01-01", "2000-01-01"],
        ],
        etablissements=[],
    )
    ingest_snapshot(db_session, fichier_local=chemin)
    entry = db_session.get(REQEntry, "9990000003")
    assert entry.nom == "Dernier Nom Fictif inc."
    assert entry.statut == "radiee"


def test_ingest_zip_reel_signale_nouvel_etablissement_secondaire_pour_entreprise_deja_connue(db_session, tmp_path):
    # Import 1 : entreprise connue avec seulement son établissement principal.
    chemin1 = _ecrire_zip_req_reel(
        tmp_path,
        entreprises=[["9990000004", "IM", "2026-01-01", "", "", "N", "", "", "", ""]],
        noms=[["9990000004", "Entreprise Fictive Beta inc.", "V", "N", "1994-01-01", ""]],
        etablissements=[
            ["9990000004", "1", "O", "1 rue Siège", "Québec (Québec)", "", "G1G1G1", "", "", ""],
        ],
        nom_zip="req_etab_1.zip",
    )
    stats1 = ingest_snapshot(db_session, fichier_local=chemin1)
    assert stats1.nouveaux_etablissements_secondaires == []  # tout premier établissement -> pas de signal

    # Import 2 : un établissement SECONDAIRE apparaît -> signal fort.
    chemin2 = _ecrire_zip_req_reel(
        tmp_path,
        entreprises=[["9990000004", "IM", "2026-02-01", "", "", "N", "", "", "", ""]],
        noms=[["9990000004", "Entreprise Fictive Beta inc.", "V", "N", "1994-01-01", ""]],
        etablissements=[
            ["9990000004", "1", "O", "1 rue Siège", "Québec (Québec)", "", "G1G1G1", "", "", ""],
            [
                "9990000004", "2", "N", "2 rue Secondaire", "Laval (Québec)", "", "H7H7H7",
                "541330", "Fabrication de matériel énergétique", "Succursale Laval",
            ],
        ],
        nom_zip="req_etab_2.zip",
    )
    stats2 = ingest_snapshot(db_session, fichier_local=chemin2)
    assert len(stats2.nouveaux_etablissements_secondaires) == 1
    assert stats2.nouveaux_etablissements_secondaires[0]["adresse"] == "2 rue Secondaire"
    # Trouvé le 2026-09-02 (spec section 6, "Filtrage par champ, contextuel au
    # profil") : secteur_code/secteur_libelle étaient déjà captés sur
    # _EtabLeger mais jamais propagés jusqu'au signal — corrigé, capturé
    # largement à l'ingestion pour que la grille de pertinence par champ ait
    # quelque chose à filtrer plus tard, par profil.
    assert stats2.nouveaux_etablissements_secondaires[0]["secteur_code"] == "541330"
    assert stats2.nouveaux_etablissements_secondaires[0]["secteur_libelle"] == "Fabrication de matériel énergétique"

    etab = db_session.get(REQEtablissementEntry, ("9990000004", "2"))
    assert etab is not None
    assert etab.principal is False


def test_ingest_zip_reel_ne_signale_pas_le_secondaire_du_tout_premier_import(db_session, tmp_path):
    # Une entreprise TOUTE NOUVELLE avec un établissement secondaire dès le
    # départ ne doit PAS déclencher le signal fort (elle vient de naître, ce
    # n'est pas une expansion — voir note de calibration en tête de fichier).
    chemin = _ecrire_zip_req_reel(
        tmp_path,
        entreprises=[["9990000005", "IM", "2026-01-01", "", "", "N", "", "", "", ""]],
        noms=[["9990000005", "Entreprise Fictive Gamma inc.", "V", "N", "1994-01-01", ""]],
        etablissements=[
            ["9990000005", "1", "O", "1 rue Siège", "Québec (Québec)", "", "G1G1G1", "", "", ""],
            ["9990000005", "2", "N", "2 rue Secondaire", "Laval (Québec)", "", "H7H7H7", "", "", ""],
        ],
    )
    stats = ingest_snapshot(db_session, fichier_local=chemin)
    assert stats.nouveaux_etablissements_secondaires == []


def test_importer_fichier_source_avec_vrai_zip_declenche_le_pipeline(db_session, registry, tmp_path):
    chemin1 = _ecrire_zip_req_reel(
        tmp_path,
        entreprises=[["9990000006", "IM", "2026-01-01", "", "", "N", "", "", "", ""]],
        noms=[["9990000006", "Entreprise Fictive Delta inc.", "V", "N", "1994-01-01", ""]],
        etablissements=[
            ["9990000006", "1", "O", "1 rue Siège", "Québec (Québec)", "", "G1G1G1", "", "", ""],
        ],
        nom_zip="req_pipeline_1.zip",
    )
    assert importer_fichier_source(db_session, "req", chemin1, registry=registry) == []

    chemin2 = _ecrire_zip_req_reel(
        tmp_path,
        entreprises=[["9990000006", "IM", "2026-02-01", "", "", "N", "", "", "", ""]],
        noms=[["9990000006", "Entreprise Fictive Delta inc.", "V", "N", "1994-01-01", ""]],
        etablissements=[
            ["9990000006", "1", "O", "1 rue Siège", "Québec (Québec)", "", "G1G1G1", "", "", ""],
            ["9990000006", "2", "N", "2 rue Secondaire", "Laval (Québec)", "", "H7H7H7", "", "", ""],
        ],
        nom_zip="req_pipeline_2.zip",
    )
    signaux = importer_fichier_source(db_session, "req", chemin2, registry=registry)
    assert len(signaux) == 1
    assert signaux[0].methode_acces == "import_manuel"
    assert signaux[0].champs["type_changement"] == "nouvel_etablissement_secondaire"

    # Dédoublonnage : réimporter le même fichier ne recrée pas le signal.
    assert importer_fichier_source(db_session, "req", chemin2, registry=registry) == []
