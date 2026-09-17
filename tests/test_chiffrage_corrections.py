"""Le chiffrage rend-il les deux natures de correction, et ce qu'il ne dit pas?

⚠️ **Le piège que ces tests gardent** : un chiffrage qui ne compterait que le
GAIN d'un abaissement de seuil ferait paraître l'abaissement gratuit. *On sait à
quoi ressemble le faux — 26 organisations publiques distinctes à 95-100 sur un
même NEQ.*
"""
from __future__ import annotations

import pytest

from falkye.models.company import Company
from falkye.models.req_entry import REQEntry
from falkye.sources.column_mapping import normaliser
from outils import chiffrage_corrections
from outils.chiffrage_corrections import _sans_parentheses


def test_le_retrait_des_parentheses_ne_touche_que_les_parentheses():
    assert _sans_parentheses("11888935 Canada inc. (Workstaff)") == "11888935 Canada inc."
    assert _sans_parentheses("Acme (A) et (B) inc.") == "Acme et inc.", (
        "deux groupes sur la même ligne doivent être DEUX retraits — un motif "
        "gourmand avalerait « et » entre les deux"
    )
    assert _sans_parentheses("Sans parenthèse") == "Sans parenthèse"
    assert _sans_parentheses(None) == ""


@pytest.fixture()
def population(db_session, monkeypatch):
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")

    registre = "11888935 canada inc"
    db_session.add(REQEntry(neq="1188893500", nom=registre,
                            nom_normalise=normaliser(registre), statut="IMMATRICULÉE"))
    # Le cas réel : deux points sous le seuil, à cause de la parenthèse.
    db_session.add(Company(
        neq=None, nom_detecte="11888935 Canada inc. (Workstaff)",
        nom_detecte_normalise=normaliser("11888935 Canada inc. (Workstaff)"),
    ))
    db_session.add(Company(
        neq=None, nom_detecte="Zzyzx Rien Du Tout",
        nom_detecte_normalise=normaliser("Zzyzx Rien Du Tout"),
    ))
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def test_ce_que_la_mesure_ne_dira_pas_vient_AVANT_les_chiffres(population, capsys):
    """*Une correction simulée dit ce que la règle rendrait sur la population
    d'aujourd'hui, jamais ce qu'elle rendrait en production* — où un appariement
    réussi crée un dossier neuf au lieu de réparer celui qui échoue."""
    assert chiffrage_corrections.main([]) == 0
    sortie = capsys.readouterr().out
    avant = sortie.index("CE QUE CETTE MESURE NE DIRA PAS")
    chiffres = sortie.index("dossiers sans NEQ")
    assert avant < chiffres, "l'avertissement est APRÈS les chiffres"
    assert "CRÉE UN DOSSIER NEUF" in sortie
    assert "seuil de 92 NE BOUGE PAS" in sortie


def test_les_parentheses_sont_ventilees_par_famille(population, capsys):
    assert chiffrage_corrections.main([]) == 0
    sortie = capsys.readouterr().out
    assert "LES DOSSIERS PORTANT UNE PARENTHÈSE, PAR FAMILLE" in sortie
    assert "avec une parenthèse : 1 dossier(s) sur 2" in sortie


def test_labaissement_rend_LES_DEUX_chiffres(population, capsys):
    """⚠️ **Le test qui porte la distinction.** Un abaissement de seuil est un
    changement d'échelle : il récupère du vrai ET du faux."""
    assert chiffrage_corrections.main([]) == 0
    sortie = capsys.readouterr().out
    assert "CE QU'IL RÉCUPÈRE" in sortie
    assert "CE QU'IL LAISSE PASSER" in sortie
    assert "PLUS DE DEUX dossiers" in sortie, (
        "le faux n'est pas mesuré — le chiffrage ferait paraître l'abaissement "
        "gratuit"
    )


def test_les_deux_natures_sont_nommees(population, capsys):
    assert chiffrage_corrections.main([]) == 0
    sortie = capsys.readouterr().out
    assert "CHANGEMENT D'ÉCHELLE" in sortie
    assert "CORRECTION DE DONNÉES" in sortie


def test_il_NECRIT_RIEN(population):
    from sqlalchemy import select

    avant = {c.id: c.neq for c in population.execute(select(Company)).scalars().all()}
    assert chiffrage_corrections.main([]) == 0
    population.expire_all()
    apres = {c.id: c.neq for c in population.execute(select(Company)).scalars().all()}
    assert avant == apres, "un chiffrage a modifié la base"


def test_le_seuil_du_produit_nest_pas_modifie(population):
    """**Aucune règle n'est changée.** *Le seuil se change avec Alexandre, jamais
    dans une demande de mesure.*"""
    from falkye import resolution

    avant = resolution.SEUIL_RESOLUTION_CONFIANTE
    chiffrage_corrections.main(["--seuil-simule", "80"])
    assert resolution.SEUIL_RESOLUTION_CONFIANTE == avant == 92.0
