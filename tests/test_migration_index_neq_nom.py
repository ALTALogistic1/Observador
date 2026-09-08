"""L'index composite, et surtout : la vérification qui refuse de se croire.

Ce que ces tests verrouillent, dans l'ordre d'importance :

1. `verifier()` DÉTECTE une base non migrée. Un contrôle qui passe toujours ne
   contrôle rien — c'est le troisième cas de la série consignée dans
   tests/conftest.py, et il coûterait ici une migration réputée faite.
2. Les plans mesurés viennent des requêtes DU MOTEUR. Si l'outil recopiait la
   requête au lieu de l'importer, il vérifierait le plan d'une requête que
   personne n'exécute.
3. Sans `--appliquer`, rien n'est écrit.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select, text

from falkye.models.company import Company
from outils import migration_index_neq_nom as migration

INDEX = migration.INDEX_COMPOSITE
REDONDANT = migration.INDEX_REDONDANT


@pytest.fixture()
def base_non_migree(db_session):
    """Une base à l'état de la production avant le 2026-09-08 : l'index composite
    n'existe pas, et il y a assez d'entreprises pour que le plan soit celui du
    volume réel — un plan mesuré sur une table vide ne dirait rien du plan choisi
    sur 11 556 lignes."""
    migration.connexion_produit(db_session).execute(text(f"DROP INDEX IF EXISTS {INDEX}"))
    for i in range(400):
        db_session.add(
            Company(
                neq=None if i < 300 else f"11{i:08d}",
                nom_detecte=f"construction {i:04d}",
                nom_detecte_normalise=f"construction {i:04d}",
            )
        )
    db_session.commit()
    return db_session


def test_verifier_detecte_une_base_non_migree(base_non_migree):
    manques = migration.verifier(base_non_migree)
    assert manques, "le contrôle passe sur une base SANS l'index — il ne contrôle rien"
    assert any("ix_companies_neq" in m for m in manques)


def test_appliquer_pose_lindex_et_le_plan_le_prend(base_non_migree):
    assert INDEX not in migration.index_existants(base_non_migree)

    migration.appliquer(base_non_migree)

    assert INDEX in migration.index_existants(base_non_migree)
    assert migration.verifier(base_non_migree) == []

    plans = migration.plans(base_non_migree)
    assert INDEX in plans["exact (resolution.py)"]
    assert INDEX in plans["préfixe GLOB (dedup_entreprises.py)"]


def test_appliquer_est_idempotent(base_non_migree):
    migration.appliquer(base_non_migree)
    migration.appliquer(base_non_migree)  # ne doit pas lever
    assert INDEX in migration.index_existants(base_non_migree)


def test_retirer_index_redondant_est_un_geste_separe(base_non_migree):
    migration.appliquer(base_non_migree)
    assert REDONDANT in migration.index_existants(base_non_migree)

    migration.appliquer(base_non_migree, retirer_redondant=True)
    assert REDONDANT not in migration.index_existants(base_non_migree)
    assert migration.verifier(base_non_migree) == []


def test_sans_appliquer_rien_nest_ecrit(base_non_migree, capsys, monkeypatch):
    monkeypatch.setattr("falkye.db.get_session", lambda: base_non_migree)
    monkeypatch.setattr(base_non_migree, "close", lambda: None)

    assert migration.main([]) == 0

    assert INDEX not in migration.index_existants(base_non_migree)
    assert "lecture seule" in capsys.readouterr().out


def test_main_sort_en_echec_si_le_plan_ignore_lindex(base_non_migree, monkeypatch):
    """Poser l'index ne prouve pas qu'il sert : l'index PARTIEL essayé le
    2026-09-08 se créait sans erreur et le planificateur restait sur
    `ix_companies_neq`. La sortie non nulle est la seule chose qui l'aurait dit."""
    monkeypatch.setattr("falkye.db.get_session", lambda: base_non_migree)
    monkeypatch.setattr(base_non_migree, "close", lambda: None)
    monkeypatch.setattr(migration, "_plan", lambda session, requete: "SCAN companies")

    assert migration.main(["--appliquer"]) == 1


def test_les_plans_viennent_des_requetes_du_moteur(base_non_migree, monkeypatch):
    """Si l'outil recopiait la requête au lieu de l'importer, ce test passerait
    quand même — c'est pourquoi il patche la fonction D'ORIGINE et exige que la
    sortie de l'outil change avec elle.

    `ville` n'est pas indexée : le plan de la requête témoin est donc un balayage,
    reconnaissable entre tous. S'il apparaît, l'outil a bien exécuté la requête du
    moteur; s'il n'apparaît pas, il en exécute une autre.
    """
    temoin = select(Company).where(Company.ville == "temoin-unique")
    monkeypatch.setattr("falkye.resolution.requete_nom_exact", lambda nom: temoin)

    plan = migration.plans(base_non_migree)["exact (resolution.py)"]

    assert "SCAN" in plan
    assert "ix_companies_neq" not in plan


def test_le_repli_par_sous_chaine_est_rapporte_mais_hors_verdict(base_non_migree):
    """La fuite est réduite, pas fermée — et le rapport doit le montrer.

    Aucun index ne rattrape un `LIKE '%…%'` : ce chemin balaie toujours, et c'est
    une lecture FACTURÉE de la base durable, pas du miroir local. L'exclure du
    verdict est délibéré; l'exclure du rapport ferait lire « deux plans corrigés »
    comme « la fuite est fermée ».
    """
    migration.appliquer(base_non_migree)

    plans = migration.plans(base_non_migree)
    repli = plans["sous-chaîne (dedup_entreprises.py)"]

    assert repli, "le repli doit figurer au rapport"
    assert INDEX not in repli, "un index ne corrige pas une sous-chaîne non ancrée"
    assert migration.verifier(base_non_migree) == [], "il ne doit pas peser au verdict"
