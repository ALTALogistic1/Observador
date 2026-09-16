"""L'outil qui ferme 4a interroge-t-il la bonne colonne?

⚠️ **C'est tout l'enjeu.** La production compare `Company.nom_detecte_normalise`,
la valeur **STOCKÉE**. *Un compte fait sur `normaliser(nom_detecte)` recalculé
répondrait à une autre question, et rien dans sa sortie ne le dirait* — cas 33.

Le décor met les deux valeurs **en désaccord** : deux dossiers dont la forme
STOCKÉE est identique et dont les noms bruts se normalisent différemment
aujourd'hui. *Un outil qui recalculerait ne les verrait pas.*
"""
from __future__ import annotations

import pytest

from falkye.models.company import Company
from outils import doublons_forme_stockee


@pytest.fixture()
def cible(db_session, monkeypatch):
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def test_sans_doublon_il_ferme_la_question(cible, capsys):
    cible.add(Company(neq=None, nom_detecte="Ferme Dallaire",
                      nom_detecte_normalise="ferme dallaire"))
    cible.commit()
    assert doublons_forme_stockee.main([]) == 0
    sortie = capsys.readouterr().out
    assert "AUCUNE LIGNE RENDUE" in sortie
    assert "pas qu'il est" in sortie, (
        "le zéro doit dire ce qu'il ne dit pas : la borne sans ordre peut créer "
        "cette condition demain"
    )


def test_la_colonne_STOCKEE_est_celle_qui_compte(cible, capsys):
    """⚠️ **Le test qui porte la distinction.** Les deux dossiers ont la MÊME
    forme stockée et des noms bruts que `normaliser` sépare aujourd'hui.

    *Un outil qui recalculerait ne trouverait rien ici — et il rendrait un zéro
    exact sur le mauvais périmètre.*
    """
    cible.add_all([
        Company(neq=None, nom_detecte="Annexair Inc", nom_detecte_normalise="forme periMEE"),
        Company(neq=None, nom_detecte="Zzyzx Totalement Autre",
                nom_detecte_normalise="forme periMEE"),
    ])
    cible.commit()
    assert doublons_forme_stockee.main([]) == 1, "le doublon de forme stockée n'est pas vu"
    sortie = capsys.readouterr().out
    assert "PEUT lever" in sortie
    assert "Annexair Inc" in sortie and "Zzyzx Totalement Autre" in sortie


def test_la_forme_VIDE_partagee_est_un_doublon(cible, capsys):
    """*`nom_detecte_normalise == ''` rend plusieurs lignes comme n'importe
    quelle autre valeur* — et `scalar_one_or_none()` lève pareil."""
    cible.add_all([
        Company(neq=None, nom_detecte="???", nom_detecte_normalise=""),
        Company(neq=None, nom_detecte="!!!", nom_detecte_normalise=""),
    ])
    cible.commit()
    assert doublons_forme_stockee.main([]) == 1
    assert "forme stockée VIDE  : 2" in capsys.readouterr().out


def test_il_NECRIT_RIEN(cible):
    from sqlalchemy import select

    cible.add(Company(neq=None, nom_detecte="X", nom_detecte_normalise="x"))
    cible.commit()
    avant = {c.id: c.nom_detecte_normalise
             for c in cible.execute(select(Company)).scalars().all()}
    doublons_forme_stockee.main([])
    cible.expire_all()
    apres = {c.id: c.nom_detecte_normalise
             for c in cible.execute(select(Company)).scalars().all()}
    assert avant == apres
