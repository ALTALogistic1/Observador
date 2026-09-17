"""La mesure E — ce que le second temps gagne ET ce qu'il coûte.

⚠️ **Le coût devrait être NUL par construction.** *Le second temps ne s'exécute
que là où `neq_retenu` a rendu `None`, donc jamais sur un RETENU.* **S'il ne
l'est pas, ce n'est pas un arbitrage à faire — c'est la garantie qui est fausse**,
et l'outil le dit en ces termes.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from falkye.models.company import Company
from falkye.models.req_entry import REQEntry
from falkye.models.req_nom import REQNom
from falkye.sources.column_mapping import normaliser
from falkye.sources.req import construire_index_par_mots
from outils import impact_du_second_temps


def _cible(monkeypatch):
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")


def _entree(db_session, neq, nom):
    db_session.add(REQEntry(neq=neq, nom=nom, nom_normalise=normaliser(nom),
                            statut="IMMATRICULÉE"))
    db_session.add(REQNom(neq=neq, nom=nom, nom_normalise=normaliser(nom),
                          statut="V", type_nom="M", gisement="NOM_ASSUJ"))


@pytest.fixture()
def population(db_session, monkeypatch):
    """Le cas de `l` en miniature : la tranche sature sur « l atelier … » et le
    vrai candidat, « l industrie mondiale … », tombe hors borne."""
    _cible(monkeypatch)
    monkeypatch.setattr("falkye.sources.req.LIMITE_CANDIDATS_PAR_NOM", 3)
    for i in range(5):
        _entree(db_session, f"700000000{i}", f"L'Atelier {i} inc.")
    _entree(db_session, "7100000000", "L'Industrie Mondiale du Nord inc.")
    db_session.add(Company(
        neq=None, nom_detecte="L'Industrie Mondiale du Nord inc.",
        nom_detecte_normalise=normaliser("L'Industrie Mondiale du Nord inc."),
    ))
    db_session.commit()
    construire_index_par_mots(db_session)
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def test_le_COUT_se_lit_AVANT_le_gain(population, capsys):
    """⚠️ *Lire le gain d'abord fait accepter un correctif dont la garantie est
    fausse.*"""
    assert impact_du_second_temps.main([]) == 0
    sortie = capsys.readouterr().out
    assert sortie.index("LE COÛT") < sortie.index("LE GAIN")
    assert sortie.index("NE DIRA PAS") < sortie.index("index par mots")


def test_le_cout_est_NUL_et_loutil_le_dit(population, capsys):
    assert impact_du_second_temps.main([]) == 0
    sortie = capsys.readouterr().out
    assert "✓  RETENUS perdus : 0" in sortie, sortie
    assert "LA GARANTIE STRUCTURELLE EST FAUSSE" not in sortie


def test_le_gain_est_compte_et_montre(population, capsys):
    assert impact_du_second_temps.main([]) == 0
    sortie = capsys.readouterr().out
    assert "RETENUS gagnés : 1" in sortie, sortie
    assert "trop faible → RETENU" in sortie or "aucun candidat → RETENU" in sortie, sortie
    assert "L'Industrie Mondiale du Nord inc." in sortie


def test_un_index_VIDE_refuse_au_lieu_de_rendre_zero(db_session, monkeypatch, capsys):
    """⚠️ **Un zéro sur un index vide se lirait « le second temps ne sert à
    rien ».** *C'est le motif le plus coûteux du projet, et il se refuse.*"""
    _cible(monkeypatch)
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    assert impact_du_second_temps.main([]) == 2
    sortie = capsys.readouterr().out
    assert "L'INDEX EST VIDE" in sortie
    assert "rendrait zéro pour la mauvaise raison" in sortie


def test_il_NECRIT_RIEN(population):
    avant = {c.id: c.neq for c in population.execute(select(Company)).scalars().all()}
    assert impact_du_second_temps.main([]) == 0
    population.expire_all()
    apres = {c.id: c.neq for c in population.execute(select(Company)).scalars().all()}
    assert avant == apres


def test_les_echelles_ne_bougent_pas(population):
    from falkye import resolution

    assert impact_du_second_temps.main([]) == 0
    assert resolution.SEUIL_RESOLUTION_CONFIANTE == 92.0
    assert resolution.SEUIL_AMBIGUITE_ECART_MIN == 8.0
