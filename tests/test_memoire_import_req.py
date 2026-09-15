"""Ce qui a tué l'import du 16 septembre — l'archivage et l'index des noms."""
import json
import zipfile

from falkye.diff_engine import LigneSnapshot, _archiver_snapshot
from falkye.sources.req import _charger_index_noms

_ENTETE = "NEQ,NOM_ASSUJ,STAT_NOM,TYP_NOM_ASSUJ,DAT_INIT_NOM_ASSUJ,DAT_FIN_NOM_ASSUJ"


def test_larchive_reste_un_tableau_json_valide(tmp_path, monkeypatch):
    """L'écriture passe en flux; le FORMAT ne change pas. Un lecteur existant
    doit relire le fichier sans rien savoir du changement."""
    import falkye.diff_engine as moteur

    monkeypatch.setattr(moteur, "ARCHIVE_DIR", tmp_path)
    lignes = [
        LigneSnapshot(cle=f"11{i:08d}", champs={"neq": f"11{i:08d}", "nom": f"Société {i} inc."})
        for i in range(5)
    ]
    chemin = _archiver_snapshot("req", lignes)
    relu = json.loads(open(chemin, encoding="utf-8").read())
    assert relu == [{"cle": l.cle, "champs": l.champs} for l in lignes]


def test_une_archive_VIDE_reste_un_tableau_vide(tmp_path, monkeypatch):
    """Le cas limite de l'écriture en flux : sans lignes, il faut quand même
    écrire `[]` — un fichier vide ne serait pas du JSON."""
    import falkye.diff_engine as moteur

    monkeypatch.setattr(moteur, "ARCHIVE_DIR", tmp_path)
    assert json.loads(open(_archiver_snapshot("req", []), encoding="utf-8").read()) == []


def test_une_seule_ligne_na_pas_de_virgule_en_trop(tmp_path, monkeypatch):
    import falkye.diff_engine as moteur

    monkeypatch.setattr(moteur, "ARCHIVE_DIR", tmp_path)
    chemin = _archiver_snapshot("req", [LigneSnapshot(cle="1", champs={"a": "b"})])
    assert json.loads(open(chemin, encoding="utf-8").read()) == [{"cle": "1", "champs": {"a": "b"}}]


def test_les_accents_ne_sont_pas_echappes(tmp_path, monkeypatch):
    """`ensure_ascii=False` était là avant; le flux ne doit pas le perdre —
    sinon le fichier double de taille et devient illisible à l'œil."""
    import falkye.diff_engine as moteur

    monkeypatch.setattr(moteur, "ARCHIVE_DIR", tmp_path)
    chemin = _archiver_snapshot("req", [LigneSnapshot(cle="1", champs={"nom": "QUÉBEC INC."})])
    assert "QUÉBEC" in open(chemin, encoding="utf-8").read()


def test_lindex_des_noms_rend_la_meme_chose_quavant(tmp_path):
    """Le retour passe par `popitem()` pour ne pas tenir deux dictionnaires
    pleins en même temps. Le RÉSULTAT doit être identique."""
    chemin = tmp_path / "n.zip"
    with zipfile.ZipFile(chemin, "w") as zf:
        zf.writestr("Nom.csv", "\n".join([
            _ENTETE,
            "1111111111,DÉNOMINATION SOCIALE INC.,V,M,2010-01-01,",
            "1111111111,Autre nom,V,N,2010-01-01,",
            "2222222222,Radiée inc.,A,M,1998-01-01,2020-01-01",
        ]))
    index = _charger_index_noms(zipfile.ZipFile(chemin))
    # 'M' en vigueur l'emporte sur 'N' ; une entreprise sans nom en vigueur
    # garde son dernier nom antérieur.
    assert index["1111111111"] == "DÉNOMINATION SOCIALE INC."
    assert index["2222222222"] == "Radiée inc."


def test_lindex_vide_ne_leve_pas(tmp_path):
    """`popitem()` sur un dictionnaire vide lèverait KeyError si la boucle
    était mal écrite."""
    chemin = tmp_path / "vide.zip"
    with zipfile.ZipFile(chemin, "w") as zf:
        zf.writestr("Nom.csv", _ENTETE)
    assert _charger_index_noms(zipfile.ZipFile(chemin)) == {}


def test_la_memoire_de_lhote_est_lue_ou_declaree_inconnue():
    """Un pic sans la machine à côté ne dit rien : 3 500 Mo est confortable sur
    16 Go et mortel sur 4. Et `None` doit rester `None`, jamais 0."""
    from outils.import_miroir_req import _memoire_totale_mo

    valeur = _memoire_totale_mo()
    assert valeur is None or valeur > 0
