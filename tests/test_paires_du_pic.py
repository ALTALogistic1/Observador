"""Dix paires du pic, et surtout : COMMENT elles sont tirées.

⚠️ **Le piège que ces tests gardent, et il a un numéro.** *Dix dossiers pris par
`id` croissant, c'est le cas 19 — le tri du fichier promu au rang d'échantillon.*
L'ordre des `id` est celui d'arrivée des signaux, donc celui des fichiers
sources : dix premiers, c'est dix dossiers de la même source et du même
trimestre.
"""
from __future__ import annotations

import pytest

from falkye.models.company import Company
from falkye.models.req_entry import REQEntry
from falkye.sources.column_mapping import normaliser
from outils import paires_du_pic
from outils.paires_du_pic import Paire, tirage_reparti


def _paire(id_, score, prefixe="gestion"):
    return Paire(id=id_, nom_detecte=f"{prefixe} {id_}", nom_norm=f"{prefixe} {id_}",
                 prefixe=prefixe, score=score, neq=f"{id_:010d}",
                 nom_registre=f"{prefixe} {id_} inc", nom_registre_norm=f"{prefixe} {id_} inc",
                 ville_registre=None, ville_dossier=None, second=0.0)


def test_le_tirage_couvre_le_BAS_et_le_HAUT_de_la_fenetre():
    """*Le pic fait trois points de large; dix dossiers tous à 85.1 ne diraient
    rien de ce qui se passe à 87.9.*"""
    paires = [_paire(i, 85.0 + i * 0.03, prefixe=f"p{i}") for i in range(100)]
    pris = tirage_reparti(paires, 10)
    assert len(pris) == 10
    scores = [p.score for p in pris]
    assert min(scores) < 85.3, "le bas de la fenêtre n'est pas représenté"
    assert max(scores) > 87.5, "le haut de la fenêtre n'est pas représenté"


def test_le_tirage_nest_PAS_les_dix_premiers_par_id():
    """⚠️ **Le cas 19, verrouillé.** *Si les rangs choisis étaient les premiers
    `id`, le tirage serait l'ordre des fichiers sources.*"""
    paires = [_paire(i, 88.0 - i * 0.03, prefixe=f"p{i}") for i in range(100)]
    pris = tirage_reparti(paires, 10)
    assert [p.id for p in pris] != list(range(10))


def test_deux_paires_ne_partagent_pas_le_MEME_PREFIXE():
    """*Sinon dix variantes de « gestion… » rempliraient la page* — et la lecture
    porterait sur un seul motif de récupération."""
    paires = [_paire(i, 85.0 + i * 0.01, prefixe="gestion") for i in range(50)]
    paires += [_paire(100 + i, 86.0 + i * 0.01, prefixe=f"autre{i}") for i in range(20)]
    pris = tirage_reparti(paires, 10)
    prefixes = [p.prefixe for p in pris]
    assert len(prefixes) == len(set(prefixes)), prefixes


def test_le_tirage_rend_le_compte_demande_meme_en_avancant():
    """⚠️ *Avancer jusqu'au prochain préfixe neuf plutôt que SAUTER le rang* —
    sauter rendrait moins de dix paires."""
    paires = [_paire(i, 85.0 + i * 0.05, prefixe=f"p{i % 12}") for i in range(60)]
    assert len(tirage_reparti(paires, 10)) == 10


def test_une_fenetre_plus_petite_que_le_tirage_rend_tout():
    paires = [_paire(i, 85.0 + i, prefixe=f"p{i}") for i in range(3)]
    assert len(tirage_reparti(paires, 10)) == 3
    assert tirage_reparti([], 10) == []


def _cible_declaree(monkeypatch):
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")


@pytest.fixture()
def population(db_session, monkeypatch):
    """Un dossier dont le meilleur score tombe dans la fenêtre 85-88."""
    _cible_declaree(monkeypatch)
    registre = "Bâtiments d'acier Finar inc."
    db_session.add(REQEntry(neq="5000000000", nom=registre,
                            nom_normalise=normaliser(registre), ville="Lévis",
                            statut="IMMATRICULÉE"))
    detecte = "Bâtiments d'acier Finar et Frères"
    db_session.add(Company(neq=None, nom_detecte=detecte,
                           nom_detecte_normalise=normaliser(detecte)))
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def test_le_decor_tombe_bien_dans_la_fenetre(population):
    """*Un test qui « passe » sur une fenêtre vide ne verrouille rien.*"""
    from rapidfuzz import fuzz

    score = fuzz.WRatio(normaliser("Bâtiments d'acier Finar et Frères"),
                        normaliser("Bâtiments d'acier Finar inc."))
    assert 85.0 <= score < 88.0, score


def test_ce_que_la_lecture_ne_dira_pas_vient_AVANT_les_paires(population, capsys):
    assert paires_du_pic.main([]) == 0
    sortie = capsys.readouterr().out
    assert sortie.index("CE QUE CETTE LECTURE NE DIRA PAS") < sortie.index("dans la fenêtre")
    assert "ne sont pas une proportion" in sortie
    assert "l'outil ne CLASSE rien" in sortie


def test_la_paire_est_rendue_BRUTE_et_normalisee(population, capsys):
    """*Brut, pas un compte* — et la forme comparée en dessous, parce que c'est
    elle que le scoreur voit."""
    assert paires_du_pic.main([]) == 0
    sortie = capsys.readouterr().out
    assert "détecté  : \"Bâtiments d'acier Finar et Frères\"" in sortie, sortie
    assert "Bâtiments d'acier Finar inc." in sortie
    assert "batiments d acier finar inc" in sortie, "la forme comparée manque"
    assert "il manque" in sortie


def test_la_regle_de_tirage_est_ANNONCEE(population, capsys):
    assert paires_du_pic.main([]) == 0
    sortie = capsys.readouterr().out
    assert "TIRAGE : rangs régulièrement espacés" in sortie


def test_le_mode_premiers_dit_quil_ne_represente_RIEN(population, capsys):
    """*Un échantillon qui ne représente rien reste utile si personne ne croit
    qu'il représente quelque chose.*"""
    assert paires_du_pic.main(["--premiers"]) == 0
    sortie = capsys.readouterr().out
    assert "LES PREMIERS PAR `id`" in sortie
    assert "ne représente" in sortie and "RIEN" in sortie
    assert "cas 19" in sortie


def test_il_NECRIT_RIEN(population):
    from sqlalchemy import select

    avant = {c.id: c.neq for c in population.execute(select(Company)).scalars().all()}
    assert paires_du_pic.main([]) == 0
    population.expire_all()
    apres = {c.id: c.neq for c in population.execute(select(Company)).scalars().all()}
    assert avant == apres
