"""Les trois départageurs sur les ambigus — recouvrement, combinaison, coût.

⚠️ *Trois départageurs qui séparent les mêmes 1 500 dossiers ne valent pas trois
fois un* — et la ligne « indépartageable » est un **résultat**, pas une absence
de mesure.
"""
from __future__ import annotations

import datetime as _dt

import pytest
from sqlalchemy import select

from falkye.models.company import Company
from falkye.models.req_entry import REQEntry
from falkye.models.signal import Signal
from falkye.sources.column_mapping import normaliser
from outils import mesure_des_departageurs


def _cible(monkeypatch):
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")


def _entree(db_session, neq, nom, **kw):
    db_session.add(REQEntry(neq=neq, nom=nom, nom_normalise=normaliser(nom),
                            statut="IMMATRICULÉE", **kw))


@pytest.fixture()
def ambigus(db_session, monkeypatch):
    """Trois dossiers ambigus, un par départageur qui les sépare.

    ⚠️ **Chacun n'est séparé que par UN des trois** — c'est ce qui rend la ligne
    « apporte seul » lisible, et un décor où les trois séparent tout ne
    verrouillerait pas le recouvrement.
    """
    _cible(monkeypatch)
    # (a) séparé par la VILLE seule
    _entree(db_session, "1000000001", "Beton Bolduc inc", ville="Sainte-Marie")
    _entree(db_session, "1000000002", "Beton Bolduc ltee", ville="Laval")
    a = Company(neq=None, nom_detecte="Beton Bolduc", ville="Laval",
                nom_detecte_normalise=normaliser("Beton Bolduc"))
    # (b) séparé par le CODE POSTAL seul — même ville des deux côtés
    _entree(db_session, "2000000001", "Gagnon Freres inc", ville="Levis",
            code_postal="G6V 1A1")
    _entree(db_session, "2000000002", "Gagnon Freres ltee", ville="Levis",
            code_postal="G7A 2B2")
    b = Company(neq=None, nom_detecte="Gagnon Freres", ville="Levis",
                nom_detecte_normalise=normaliser("Gagnon Freres"))
    # (c) séparé par l'ACTIVITÉ seule — ni ville ni code postal au dossier
    _entree(db_session, "3000000001", "Gerard et Fils inc",
            secteur_libelle="Travaux de pavage et revetement")
    _entree(db_session, "3000000002", "Gerard et Fils ltee",
            secteur_libelle="Entrepreneurs en plomberie")
    c = Company(neq=None, nom_detecte="Gerard et Fils",
                secteur_activite_libelle="Entrepreneurs en plomberie",
                nom_detecte_normalise=normaliser("Gerard et Fils"))
    db_session.add_all([a, b, c])
    db_session.flush()
    db_session.add(Signal(
        company_id=b.id, source_id="eimt", signal_type_id="recrutement_massif",
        detected_at=_dt.datetime(2026, 1, 1),
        champs={"adresse": "Levis, QC G7A 2B2"},
    ))
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def test_le_decor_produit_bien_TROIS_ambigus(ambigus, capsys):
    """*Un décor qui n'aurait aucun ambigu ne verrouillerait rien.*"""
    assert mesure_des_departageurs.main([]) == 0
    assert "dont AMBIGUS      : 3" in capsys.readouterr().out


def test_ce_que_la_mesure_ne_dira_pas_vient_AVANT_les_chiffres(ambigus, capsys):
    assert mesure_des_departageurs.main([]) == 0
    sortie = capsys.readouterr().out
    assert sortie.index("NE DIRA PAS") < sortie.index("dont AMBIGUS")
    assert "IL N'EN CONFIRME AUCUN" in sortie
    assert "« Je ne sais pas » n'est\n   pas « non »" in sortie or "n'est" in sortie
    assert "UNSPSC" in sortie and "PLANCHER" in sortie


def test_chaque_departageur_separe_SON_dossier(ambigus, capsys):
    assert mesure_des_departageurs.main([]) == 0
    sortie = capsys.readouterr().out
    for nom in ("VILLE", "CODE POSTAL", "ACTIVITÉ"):
        bloc = sortie.split(f"▸ {nom}")[1]
        ligne = next(l for l in bloc.splitlines() if "DÉPARTAGÉ" in l)
        assert ligne.split()[1] == "1", (nom, ligne)


def test_le_RECOUVREMENT_est_rendu_et_lapport_SEUL_aussi(ambigus, capsys):
    """⚠️ *Trois départageurs qui séparent les mêmes dossiers ne valent pas trois
    fois un.*"""
    assert mesure_des_departageurs.main([]) == 0
    sortie = capsys.readouterr().out
    assert "SÉPARÉS PAR AU MOINS UN : 3 sur 3" in sortie, sortie
    assert "somme des trois pris isolément : 3" in sortie, sortie
    assert "recouvrement : 0 dossier(s)" in sortie, sortie
    bloc = sortie.split("APPORTE SEUL")[1]
    for nom in ("ville", "code postal", "activité"):
        ligne = next(l for l in bloc.splitlines() if l.strip().startswith(nom))
        assert ligne.split()[-1] == "1", (nom, ligne)


def test_les_INDEPARTAGEABLES_sont_un_resultat(ambigus, capsys):
    assert mesure_des_departageurs.main([]) == 0
    sortie = capsys.readouterr().out
    assert "INDÉPARTAGEABLES PAR LES TROIS : 0" in sortie
    assert "C'est un résultat, pas une absence de mesure" in sortie


def test_le_COUT_distingue_CORRIGE_de_EXCLUT_TOUT(ambigus, capsys):
    """*« Désigne un autre » n'est pas une erreur; « les exclut tous » n'est pas
    un départage.* **Deux formes, deux natures.**"""
    assert mesure_des_departageurs.main([]) == 0
    sortie = capsys.readouterr().out
    assert "désigne UN AUTRE que le mieux scoré" in sortie
    assert "les exclut TOUS" in sortie
    assert "n'est PAS une erreur" in sortie
    assert "est un SIGNAL, pas un départage" in sortie


def test_il_NECRIT_RIEN(ambigus):
    avant = {c.id: (c.neq, c.ville) for c in ambigus.execute(select(Company)).scalars()}
    assert mesure_des_departageurs.main([]) == 0
    ambigus.expire_all()
    apres = {c.id: (c.neq, c.ville) for c in ambigus.execute(select(Company)).scalars()}
    assert avant == apres


def test_les_echelles_ne_bougent_pas(ambigus):
    from falkye import resolution

    assert mesure_des_departageurs.main([]) == 0
    assert resolution.SEUIL_RESOLUTION_CONFIANTE == 92.0
    assert resolution.SEUIL_AMBIGUITE_ECART_MIN == 8.0
