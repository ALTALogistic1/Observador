"""Où casse la chaîne d'un nom exactement présent au registre?

⚠️ **La contradiction que cet outil tranche** : `impact_tous_les_noms.py` annonce
**6 009 résolutions franches**, et le rejeu du 16 septembre a rendu **805
retenus**. *Les deux ne peuvent pas être vrais du même mécanisme.*
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from falkye.models.company import Company
from falkye.models.req_entry import REQEntry
from falkye.models.req_nom import REQNom
from falkye.sources.column_mapping import normaliser
from outils import chaine_du_nom_exact


def _cible(monkeypatch):
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")


def _entree(neq, nom, **kw):
    return REQEntry(neq=neq, nom=nom, nom_normalise=normaliser(nom),
                    statut="IMMATRICULÉE", **kw)


def _dossier(nom, **kw):
    return Company(neq=None, nom_detecte=nom,
                   nom_detecte_normalise=normaliser(nom), **kw)


@pytest.fixture()
def chaine(db_session, monkeypatch):
    """Un dossier par maillon : absent du miroir, plusieurs NEQ, hors du lot,
    refusé par les échelles, et un qui traverse."""
    _cible(monkeypatch)
    # ⚠️ La borne est abaissée à 2 pour que la coupe se reproduise sans charger
    # 2 000 lignes dans un test.
    monkeypatch.setattr("falkye.sources.req.LIMITE_CANDIDATS_PAR_NOM", 2)

    db_session.add_all([
        _entree("1000000001", "Traverse Complete inc"),
        # deux NEQ pour la MÊME forme — maillon 2
        _entree("1000000002", "Deux Maisons Pareilles"),
        _entree("1000000003", "Deux Maisons Pareilles"),
        # la tranche alphabétique sature avant d'atteindre le bon — maillon 3
        _entree("1000000004", "Coupe 1"),
        _entree("1000000005", "Coupe 2"),
        _entree("1000000006", "Coupe Zzz Cible"),
    ])
    db_session.add_all([
        _dossier("Traverse Complete inc"),
        _dossier("Zzyzx Absent Du Miroir"),
        _dossier("Deux Maisons Pareilles"),
        _dossier("Coupe Zzz Cible"),
    ])
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def test_ce_que_la_mesure_ne_dira_pas_vient_AVANT_les_chiffres(chaine, capsys):
    assert chaine_du_nom_exact.main([]) == 0
    sortie = capsys.readouterr().out
    assert sortie.index("NE DIRA PAS") < sortie.index("dossiers sans NEQ")
    assert "ne consulte jamais `req_noms`" in sortie
    assert "DEUX corrections distinctes" in sortie


def test_chaque_maillon_a_son_dossier(chaine, capsys):
    """*Chaque chute nomme son mécanisme* — et le décor en produit une par
    maillon, sinon le tableau ne verrouillerait rien."""
    assert chaine_du_nom_exact.main([]) == 0
    sortie = capsys.readouterr().out
    for maillon, attendu in (
        ("1 ⛔ le nom n'est PAS au miroir", "1"),
        ("2 ⛔ le nom mène à PLUSIEURS NEQ", "1"),
        ("3 ⛔ LE NEQ N'EST PAS DANS LE LOT — la borne", "1"),
        ("4 ✓ RETENU — la chaîne tient", "1"),
    ):
        ligne = next(l for l in sortie.splitlines() if maillon in l)
        assert ligne.split()[-3] == attendu, ligne


def test_le_chiffre_a_comparer_au_6009_est_rendu(chaine, capsys):
    """⚠️ **Le chiffre qui tranche la question d'Alexandre.**"""
    assert chaine_du_nom_exact.main([]) == 0
    sortie = capsys.readouterr().out
    assert "à comparer au 6 009" in sortie
    ligne = next(l for l in sortie.splitlines() if "menant à UN SEUL NEQ" in l)
    # 4 dossiers : 1 absent, 1 à deux NEQ → 2 mènent à un seul NEQ.
    assert "2" in ligne, ligne
    assert "Proche de 6 009" in sortie and "Très inférieur" in sortie


def test_la_provenance_du_nom_au_miroir_est_dite(chaine, db_session, capsys):
    """*`req_entries` ou `req_noms`* — la seconde est le pont du 15 septembre, et
    savoir lequel des deux porte le nom change ce qu'on corrige."""
    nom = "Par Le Pont Seulement"
    db_session.add(_entree("1000000007", "9999-9999 Quebec inc"))
    db_session.add(REQNom(neq="1000000007", nom=nom, statut="V",
                          type_nom="AUTRE NOM UTILISE AU QUEBEC",
                          nom_normalise=normaliser(nom)))
    db_session.add(_dossier(nom))
    db_session.commit()

    assert chaine_du_nom_exact.main([]) == 0
    sortie = capsys.readouterr().out
    assert "req_noms (autre nom) — le pont du 15 septembre" in sortie


def test_il_NECRIT_RIEN(chaine):
    avant = {c.id: c.neq for c in chaine.execute(select(Company)).scalars().all()}
    assert chaine_du_nom_exact.main([]) == 0
    chaine.expire_all()
    apres = {c.id: c.neq for c in chaine.execute(select(Company)).scalars().all()}
    assert avant == apres


def test_les_echelles_ne_bougent_pas(chaine):
    from falkye import resolution

    assert chaine_du_nom_exact.main([]) == 0
    assert resolution.SEUIL_RESOLUTION_CONFIANTE == 92.0
    assert resolution.SEUIL_AMBIGUITE_ECART_MIN == 8.0
