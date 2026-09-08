"""La migration des colonnes du chantier 2 — et le contrôle qui peut échouer.

Elle écrit dans DEUX bases : `source_run_logs` est dans celle du produit,
`diff_run_historique` et `diff_quarantaines` dans celle des miroirs. Une
migration qui se tromperait de cible poserait des colonnes dans le mauvais
fichier sans rien signaler — c'est ce que ces tests empêchent.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from outils import migration_chantier2_execution as migration


@pytest.fixture()
def base_non_migree(db_session):
    """Retire les colonnes du chantier 2 pour retrouver l'état d'avant.

    Les INDEX d'abord : SQLite refuse `DROP COLUMN` tant qu'un index porte sur
    la colonne (« error in index … after drop column »). C'est aussi l'ordre du
    retour arrière réel, et c'est pour ça qu'il est écrit ici plutôt que supposé.
    """
    for modele, nom_index, _, _, _ in migration.INDEX:
        migration.connexion(db_session, modele).execute(
            text(f"DROP INDEX IF EXISTS {nom_index}")
        )
    for modele, table, colonne, _ in migration.COLONNES:
        migration.connexion(db_session, modele).execute(
            text(f"ALTER TABLE {table} DROP COLUMN {colonne}")
        )
    db_session.commit()
    return db_session


def test_manquantes_detecte_une_base_non_migree(base_non_migree):
    """Un contrôle qui passe toujours ne contrôle rien."""
    restantes = migration.manquantes(base_non_migree)
    assert len(restantes) == len(migration.COLONNES)


def test_appliquer_pose_les_six_colonnes(base_non_migree):
    faits = migration.appliquer(base_non_migree)

    assert len(faits) == len(migration.COLONNES)
    assert migration.manquantes(base_non_migree) == []


def test_appliquer_est_idempotent(base_non_migree):
    migration.appliquer(base_non_migree)
    assert migration.appliquer(base_non_migree) == []
    assert migration.manquantes(base_non_migree) == []


def test_chaque_colonne_va_dans_la_base_de_son_modele(base_non_migree):
    """La colonne du produit ne doit pas apparaître dans la base des miroirs, ni
    l'inverse. Deux moteurs, deux fichiers — une erreur de routage est muette."""
    migration.appliquer(base_non_migree)

    produit = migration.colonnes_presentes(base_non_migree, "SourceRunLog", "source_run_logs")
    assert {"execution_id", "nb_lignes_source", "nb_lignes_lues_base", "duree_ms"} <= produit

    miroir = migration.colonnes_presentes(
        base_non_migree, "DiffRunHistorique", "diff_run_historique"
    )
    assert "execution_id" in miroir
    assert "nb_lignes_lues_base" not in miroir, (
        "le coût en lectures facturées n'a rien à faire dans la base LOCALE"
    )


def test_main_sans_appliquer_necrit_rien(base_non_migree, monkeypatch, capsys):
    monkeypatch.setattr("falkye.db.get_session", lambda: base_non_migree)
    monkeypatch.setattr(base_non_migree, "close", lambda: None)

    assert migration.main([]) == 0

    assert len(migration.manquantes(base_non_migree)) == len(migration.COLONNES)
    assert "relancer avec --appliquer" in capsys.readouterr().out


def test_main_sort_en_echec_si_une_colonne_manque_encore(
    base_non_migree, monkeypatch
):
    """Une migration ne se déclare pas faite parce que la commande n'a pas levé —
    c'est le défaut que l'index partiel a montré le 2026-09-08."""
    monkeypatch.setattr("falkye.db.get_session", lambda: base_non_migree)
    monkeypatch.setattr(base_non_migree, "close", lambda: None)
    monkeypatch.setattr(migration, "appliquer", lambda session: [])

    assert migration.main(["--appliquer"]) == 1
