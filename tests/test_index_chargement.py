"""Les chargements par entreprise passent par un index — et on le vérifie au plan.

Le 2026-09-11, `signals.company_id` était une clé étrangère **sans index** : en
SQLite une clé étrangère n'en crée aucun, et charger les signaux d'une entreprise
balayait la table. 17 800 lignes par appel, 23 100 appels, **411 963 777 lectures
facturées pour un cycle qui n'avait résolu aucune entreprise** *(journal,
cas 33)*.

**Le verdict porte sur le PLAN, jamais sur l'existence de l'index.** C'est la
leçon du 8 septembre : l'index partiel essayé ce jour-là se créait sans erreur et
le planificateur l'ignorait *(journal, cas 23)*.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import event, text

from outils.migration_index_chargement import (
    INDEX,
    requete_chargement_des_signaux,
    verifier,
)

RACINE = Path(__file__).resolve().parents[1]


def _index_de(session, table: str) -> set[str]:
    from falkye.models.company import Company

    connexion = session.connection(bind_arguments={"mapper": Company.__mapper__})
    lignes = connexion.execute(
        text(f"SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='{table}'")
    ).all()
    return {nom for (nom,) in lignes if nom}


@pytest.mark.parametrize("nom,table,_creation", INDEX)
def test_une_base_neuve_porte_deja_lindex(nom, table, _creation, db_session):
    """Les modèles et l'outil doivent dire la même chose : l'un sert une base
    neuve, l'autre la base en service. Qu'ils divergent ferait deux schémas."""
    assert nom in _index_de(db_session, table)


def test_les_deux_chargements_passent_par_un_index(db_session):
    assert verifier(db_session) == []


def test_le_defaut_se_reproduit_quand_on_retire_lindex(db_session):
    """Le 11 septembre en petit. Sans cette reproduction, le test ci-dessus
    passerait aussi sur une base où l'index n'aurait jamais rien changé."""
    from falkye.models.company import Company

    connexion = db_session.connection(bind_arguments={"mapper": Company.__mapper__})
    for nom, _table, _creation in INDEX:
        connexion.execute(text(f"DROP INDEX {nom}"))

    manques = verifier(db_session)

    assert len(manques) == 2
    assert all("SCAN" in m for m in manques)


def test_la_requete_verifiee_est_CELLE_que_le_moteur_emet(db_session):
    """La fidélité, et c'est le test qui porte l'outil.

    Le chargement d'une relation n'est écrit dans aucune fonction du moteur :
    SQLAlchemy l'émet. Vérifier le plan d'une requête tapée à côté ne dirait rien
    de celle qui tourne — d'où la dérivation depuis la relation elle-même. Ce
    test capture le SQL RÉELLEMENT émis et exige qu'il soit le même.
    """
    from sqlalchemy.dialects import sqlite

    from falkye.models.company import Company
    from falkye.models.signal import Signal

    company = Company(nom_detecte="Test", nom_detecte_normalise="test")
    db_session.add(company)
    db_session.flush()
    db_session.add(
        Signal(
            company_id=company.id, source_id="seao", signal_type_id="appel_offres",
            detected_at=__import__("datetime").datetime.now(), champs={},
        )
    )
    db_session.commit()
    db_session.expire_all()

    emises: list[str] = []
    moteur = db_session.get_bind(mapper=Company.__mapper__)

    @event.listens_for(moteur, "before_cursor_execute")
    def _noter(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        emises.append(statement)

    try:
        recharge = db_session.get(Company, company.id)
        list(recharge.signals)  # LE chargement de relation, pour de vrai
    finally:
        event.remove(moteur, "before_cursor_execute", _noter)

    chargements = [s for s in emises if "FROM signals" in s]
    assert len(chargements) == 1, emises

    derivee = str(
        requete_chargement_des_signaux(company.id).compile(
            dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}
        )
    )

    def _forme(sql: str) -> str:
        """La clause qui décide du plan, sans les paramètres ni les blancs."""
        return " ".join(sql.split()).split("WHERE")[-1].replace("?", "X").replace(
            str(company.id), "X"
        )

    assert _forme(derivee) == _forme(chargements[0])


def test_loutil_refuse_une_cible_que_personne_na_choisie(tmp_path):
    """Poser un index sur une base vide réussit sans rien corriger — le verdict
    le plus rassurant de tous *(journal, cas 30)*."""
    fait = subprocess.run(
        [sys.executable, str(RACINE / "outils" / "migration_index_chargement.py"), "--appliquer"],
        cwd=tmp_path,
        env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(RACINE), "HOME": str(tmp_path)},
        capture_output=True, text=True, check=False,
    )

    assert fait.returncode == 2, fait.stdout + fait.stderr
    assert "REFUS" in fait.stdout + fait.stderr
    assert not (tmp_path / "data").exists()
