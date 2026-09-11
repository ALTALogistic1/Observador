"""La suppression des copies miroir vides — point 27.9.

L'outil supprime des tables. Ce qui est testé n'est donc pas surtout qu'il
supprime : c'est **tout ce qu'il refuse de supprimer**. Une table du bon nom
existe légitimement, avec des données, dans le fichier miroir — le même
`DROP TABLE` y serait une perte irréversible.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, inspect, text

from outils import supprimer_copies_miroir_distantes as outil

TABLE_TEMOIN = outil.TABLE_TEMOIN


@pytest.fixture(autouse=True)
def cible_declaree(monkeypatch, tmp_path):
    """Une cible nommée : l'outil refuse celle que personne n'a choisie.

    Même raison qu'au test de la migration du chantier 2 — le garde-fou lit
    l'environnement, et ces tests lui fournissent une cible réelle plutôt que
    de le contourner.
    """
    monkeypatch.setenv("FALKYE_DB_URL", f"sqlite:///{tmp_path}/produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", f"sqlite:///{tmp_path}/miroirs.sqlite3")


@pytest.fixture()
def base_produit(monkeypatch, tmp_path):
    """Une base de produit avec la table témoin et les huit copies vides."""
    chemin = tmp_path / "produit.sqlite3"
    moteur = create_engine(f"sqlite:///{chemin}")
    with moteur.begin() as connexion:
        connexion.execute(text(f'CREATE TABLE "{TABLE_TEMOIN}" (id INTEGER PRIMARY KEY)'))
        for nom in outil.tables_miroir():
            connexion.execute(text(f'CREATE TABLE "{nom}" (id INTEGER PRIMARY KEY)'))
    monkeypatch.setattr(outil, "get_engine", lambda: moteur)
    return moteur


def test_la_liste_vient_des_modeles(base_produit):
    """Huit tables, et elles viennent de BaseMiroir — pas d'une constante."""
    noms = outil.tables_miroir()
    assert len(noms) == 8
    assert "req_entries" in noms
    assert "diff_run_historique" in noms
    assert "diff_quarantaines" in noms


def test_passage_a_blanc_ne_supprime_rien(base_produit, capsys):
    import sys

    sys.argv = ["outil"]
    assert outil.main() == 0
    restantes = set(inspect(base_produit).get_table_names())
    for nom in outil.tables_miroir():
        assert nom in restantes, f"{nom} supprimée par un passage à blanc"
    assert "PASSAGE À BLANC" in capsys.readouterr().out


def test_appliquer_supprime_les_huit_et_garde_le_reste(base_produit):
    import sys

    sys.argv = ["outil", "--appliquer"]
    assert outil.main() == 0
    restantes = set(inspect(base_produit).get_table_names())
    assert restantes == {TABLE_TEMOIN}


def test_une_table_peuplee_arrete_tout(base_produit):
    """Le point 27.9 suppose des copies VIDES. La supposition fausse arrête tout.

    Et elle arrête tout : les sept autres ne sont pas supprimées « en
    attendant ». Une table miroir qui reçoit des lignes sur la base du produit
    veut dire que quelque chose y écrit, et les sept autres sont la trace qui
    permet de trouver quoi.
    """
    with base_produit.begin() as connexion:
        connexion.execute(text('INSERT INTO "req_entries" (id) VALUES (1)'))

    import sys

    sys.argv = ["outil", "--appliquer"]
    assert outil.main() == 2

    restantes = set(inspect(base_produit).get_table_names())
    for nom in outil.tables_miroir():
        assert nom in restantes, f"{nom} supprimée alors qu'une autre était peuplée"


def test_sans_table_temoin_l_outil_refuse(monkeypatch, tmp_path):
    """Une base étrangère ou vide rendrait « rien à supprimer » — exact et trompeur."""
    chemin = tmp_path / "etrangere.sqlite3"
    moteur = create_engine(f"sqlite:///{chemin}")
    with moteur.begin() as connexion:
        connexion.execute(text("CREATE TABLE autre_chose (id INTEGER PRIMARY KEY)"))
    monkeypatch.setattr(outil, "get_engine", lambda: moteur)

    import sys

    sys.argv = ["outil", "--appliquer"]
    assert outil.main() == 2
    assert "autre_chose" in set(inspect(moteur).get_table_names())


def test_refuse_la_cible_que_personne_n_a_choisie(monkeypatch):
    """Sur un repli vide, les huit tables sont absentes et l'outil dirait
    « rien à supprimer » — on le croirait fait."""
    monkeypatch.delenv("FALKYE_DB_URL", raising=False)
    monkeypatch.delenv("FALKYE_MIROIR_DB_URL", raising=False)

    import sys

    sys.argv = ["outil", "--appliquer"]
    assert outil.main() == 2
