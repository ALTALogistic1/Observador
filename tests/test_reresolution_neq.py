"""La passe de reprise pose-t-elle les NEQ libres, et CONSERVE-t-elle le reste?

**La décision que ces tests verrouillent** *(Alexandre, 2026-09-16)* :
**conservation plutôt que fusion, parce qu'elle est réversible.** *Deux dossiers
séparés se fusionnent plus tard; deux dossiers fusionnés ne se séparent pas.*

`Company.neq` est `unique=True`. Quand la reprise trouve un NEQ **déjà porté par
un autre dossier**, le chemin « naturel » serait de fusionner les deux. ⚠️ **La
passe ne le fait pas, et ces tests existent pour que personne ne le fasse plus
tard sans le décider** — un rapprochement est *journalisé*, à examiner par un
humain, et **les deux dossiers sortent intacts**.

Le reste tient en trois exigences, chacune avec son test :

1. **Le rapport est le mode par défaut** — `--appliquer` est le seul chemin qui
   écrit. *Un outil qui écrit par défaut est un outil qu'on lance une fois de
   trop.*
2. **L'instantané d'avant précède le commit.** *Sans lui, « réversible » est une
   intention* — et si l'instantané ne peut pas s'écrire, **rien n'est modifié**.
3. **La décision passe par `neq_retenu`**, la fonction du produit. *Une règle
   recopiée mesurerait sa propre copie.*
"""
from __future__ import annotations

import json

import pytest

from falkye.models.company import Company, StatutResolution
from falkye.models.diagnostic_journal import DiagnosticJournal, TypeDiagnostic
from falkye.models.req_entry import REQEntry
from falkye.sources.column_mapping import normaliser
from outils import reresolution_neq


@pytest.fixture()
def decor(db_session, tmp_path, monkeypatch):
    """Trois dossiers sans NEQ : un que le registre résout vers un NEQ libre, un
    vers un NEQ DÉJÀ PRIS, un que rien ne résout. Plus le détenteur."""
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")
    monkeypatch.setattr(reresolution_neq, "DOSSIER_INSTANTANE", tmp_path)

    for neq, nom in (
        ("1111111111", "boulangerie saint-viateur inc"),
        ("2222222222", "plomberie rousseau et fils ltee"),
    ):
        db_session.add(
            REQEntry(neq=neq, nom=nom, nom_normalise=normaliser(nom),
                     statut="IMMATRICULÉE")
        )

    libre = Company(neq=None, nom_detecte="Boulangerie Saint-Viateur Inc",
                    nom_detecte_normalise=normaliser("Boulangerie Saint-Viateur Inc"))
    a_conserver = Company(neq=None, nom_detecte="Plomberie Rousseau et Fils Ltee",
                          nom_detecte_normalise=normaliser("Plomberie Rousseau et Fils Ltee"))
    detenteur = Company(neq="2222222222", nom_detecte="Plomberie Rousseau",
                        nom_detecte_normalise=normaliser("Plomberie Rousseau"))
    introuvable = Company(neq=None, nom_detecte="Zzyzx Quelque Chose Qui Nexiste Pas",
                          nom_detecte_normalise=normaliser("Zzyzx Quelque Chose Qui Nexiste Pas"))
    db_session.add_all([libre, a_conserver, detenteur, introuvable])
    db_session.commit()

    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return {"libre": libre.id, "a_conserver": a_conserver.id,
            "detenteur": detenteur.id, "introuvable": introuvable.id,
            "session": db_session, "tmp": tmp_path}


def test_sans_appliquer_rien_nest_ecrit(decor, capsys):
    """**Le mode par défaut est le rapport.** Un outil qui écrit par défaut est
    un outil qu'on lance une fois de trop."""
    assert reresolution_neq.main([]) == 0

    session = decor["session"]
    session.expire_all()
    assert session.get(Company, decor["libre"]).neq is None, "un NEQ a été posé sans --appliquer"
    assert not list(session.execute(
        __import__("sqlalchemy").select(DiagnosticJournal)).scalars().all()
    ), "un rapprochement a été journalisé sans --appliquer"
    assert "rien n'a été écrit" in capsys.readouterr().out.lower()


def test_le_neq_libre_est_pose(decor):
    assert reresolution_neq.main(["--appliquer"]) == 0
    session = decor["session"]
    session.expire_all()
    repris = session.get(Company, decor["libre"])
    assert repris.neq == "1111111111"
    assert repris.statut_resolution == StatutResolution.RESOLU


def test_un_neq_deja_pris_ne_fusionne_RIEN(decor):
    """⚠️ **Le test qui porte la décision.** Les deux dossiers sortent intacts,
    et le rapprochement n'est qu'une proposition.

    *Deux dossiers séparés se fusionnent plus tard; deux dossiers fusionnés ne se
    séparent pas.*
    """
    from sqlalchemy import select

    assert reresolution_neq.main(["--appliquer"]) == 0
    session = decor["session"]
    session.expire_all()

    conserve = session.get(Company, decor["a_conserver"])
    detenteur = session.get(Company, decor["detenteur"])
    assert conserve is not None, "le dossier a été SUPPRIMÉ — c'est une fusion"
    assert conserve.neq is None, "un NEQ déjà pris a été posé sur un second dossier"
    assert detenteur is not None and detenteur.neq == "2222222222", "le détenteur a bougé"

    entrees = list(session.execute(select(DiagnosticJournal)).scalars().all())
    rapprochements = [
        e for e in entrees if e.type_diagnostic == TypeDiagnostic.CANDIDAT_FUSION_ENTREPRISE
    ]
    assert len(rapprochements) == 1, "le rapprochement n'a pas été journalisé pour examen"
    assert rapprochements[0].statut == "a_examiner"
    assert rapprochements[0].company_id_principal == decor["detenteur"]
    assert rapprochements[0].company_id_candidat == decor["a_conserver"]


def test_linstantane_porte_letat_davant(decor):
    """*Sans instantané, « réversible » est une intention.*"""
    assert reresolution_neq.main(["--appliquer"]) == 0
    fichiers = list(decor["tmp"].glob("reresolution-*.json"))
    assert len(fichiers) == 1, f"aucun instantané écrit ({fichiers})"

    contenu = json.loads(fichiers[0].read_text(encoding="utf-8"))
    a_poser = {p["company_id"]: p for p in contenu["a_poser"]}
    assert decor["libre"] in a_poser
    assert a_poser[decor["libre"]]["neq_avant"] is None, (
        "l'état d'AVANT manque — l'instantané ne permet pas de défaire"
    )
    conserves = {p["company_id"] for p in contenu["conserves"]}
    assert decor["a_conserver"] in conserves


def test_un_instantane_impossible_ANNULE_tout(decor, monkeypatch):
    """⚠️ **Si la trace ne peut pas s'écrire, le geste n'a pas lieu.**

    Le même défaut que le chemin d'archive du diff, une table plus loin : un
    geste irréversible sans trace de l'état d'avant n'est pas réversible.
    """
    barrage = decor["tmp"] / "barrage"
    barrage.write_text("un fichier, pas un répertoire")
    monkeypatch.setattr(reresolution_neq, "DOSSIER_INSTANTANE", barrage / "dedans")

    assert reresolution_neq.main(["--appliquer"]) == 3
    session = decor["session"]
    session.expire_all()
    assert session.get(Company, decor["libre"]).neq is None, (
        "un NEQ a été posé alors que l'instantané n'a pas pu être écrit"
    )


def test_ce_que_rien_ne_resout_reste_intact(decor):
    assert reresolution_neq.main(["--appliquer"]) == 0
    session = decor["session"]
    session.expire_all()
    assert session.get(Company, decor["introuvable"]).neq is None
