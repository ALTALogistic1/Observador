"""L'outil de mesure des doublons compte-t-il ce qu'il annonce?

**Un outil de mesure qui se trompe est pire qu'une absence de mesure** : il rend
un chiffre qu'on croira. Ces tests vérifient les trois familles sur une
population dont on connaît la réponse à l'avance, et que l'outil **n'écrit
rien** — c'est sa portée déclarée.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from falkye.models.company import Company
from falkye.sources.column_mapping import normaliser
from outils import doublons_entreprises


@pytest.fixture()
def population(db_session, monkeypatch):
    """Trois familles, chacune avec un nombre connu.

    - **1 groupe de graphie identique**, de deux dossiers, tous deux sans NEQ;
    - **1 groupe MIXTE** : un résolu et un non résolu, même graphie normalisée —
      *la famille que la contrainte d'unicité rend invisible*;
    - **1 dossier seul**, qui ne doit apparaître nulle part.
    """
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")

    def c(nom, neq=None):
        return Company(neq=neq, nom_detecte=nom, nom_detecte_normalise=normaliser(nom))

    db_session.add_all([
        c("Annexair Inc"), c("annexair inc."),                 # famille 1
        c("Acti-Sol inc.", neq="4444444444"), c("ACTI-SOL INC"),  # familles 1 + 3
        c("Quelque Chose De Vraiment Unique"),                   # ni l'un ni l'autre
    ])
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def test_la_graphie_identique_est_comptee(population, capsys):
    assert doublons_entreprises.main(["--sans-flou"]) == 0
    sortie = capsys.readouterr().out
    assert "groupes                : 2" in sortie, (
        "deux groupes de graphie identique attendus (annexair, acti-sol)"
    )
    assert "dossiers EN TROP       : 2" in sortie


def test_le_groupe_MIXTE_est_isole(population, capsys):
    """*Un résolu et un non résolu cohabitent sans rien violer* — c'est ce que la
    passe a trouvé, et la contrainte d'unicité ne peut pas le signaler."""
    assert doublons_entreprises.main(["--sans-flou"]) == 0
    sortie = capsys.readouterr().out
    assert "groupes MIXTES         : 1" in sortie, (
        "le couple résolu/non-résolu (acti-sol) n'est pas isolé"
    )


def test_un_dossier_seul_napparait_nulle_part(population, capsys):
    assert doublons_entreprises.main(["--sans-flou"]) == 0
    assert "Quelque Chose De Vraiment Unique" not in capsys.readouterr().out


def test_loutil_NECRIT_RIEN(population):
    """**Sa portée déclarée est « mesure seule ».** Un outil qui écrit en
    mesurant change ce qu'il mesure."""
    avant = {
        c.id: (c.neq, c.nom_detecte)
        for c in population.execute(select(Company)).scalars().all()
    }
    assert doublons_entreprises.main([]) == 0
    population.expire_all()
    apres = {
        c.id: (c.neq, c.nom_detecte)
        for c in population.execute(select(Company)).scalars().all()
    }
    assert avant == apres, "l'outil de MESURE a modifié la base"


def test_sauter_le_flou_le_dit(population, capsys):
    """*Sautée n'est pas nulle* — l'absence de mesure ne doit jamais se lire
    comme un zéro."""
    assert doublons_entreprises.main(["--sans-flou"]) == 0
    sortie = capsys.readouterr().out
    assert "SAUTÉE" in sortie and "n'est pas nulle" in sortie


def test_le_perimetre_est_dans_la_sortie(population, capsys):
    """**Cas 33.** La portée s'écrit à côté de la sortie, jamais seulement dans
    la documentation — sinon un total se lit comme la population entière."""
    assert doublons_entreprises.main(["--sans-flou"]) == 0
    sortie = capsys.readouterr().out
    assert "PÉRIMÈTRE DE CETTE MESURE" in sortie
    assert "D27" in sortie and "D43" in sortie
