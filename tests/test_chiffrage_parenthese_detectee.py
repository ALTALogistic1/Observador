"""Le retrait de la parenthèse — **côté DÉTECTÉ seulement**.

⚠️ *Une mesure qui rendrait « les parenthèses » sans dire de quel côté se
relirait comme celle du 17 septembre*, qui retirait des deux et perdait 13
dossiers par le registre.
"""
from __future__ import annotations

import re

import pytest
from sqlalchemy import select

from falkye.models.company import Company
from falkye.models.req_entry import REQEntry
from falkye.sources.column_mapping import normaliser
from outils import chiffrage_parenthese_detectee as outil
from tests.conftest import compte_de_la_ligne as _compte


def _entree(db_session, neq, nom, **kw):
    db_session.add(REQEntry(neq=neq, nom=nom, nom_normalise=normaliser(nom),
                            statut="IMMATRICULÉE", **kw))




# ---------------------------------------------------------------------------
# LA RÈGLE DE RETRAIT — sur le nom PUBLIÉ, et fermée seulement
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("nom, attendu", [
    ("9031-8395 Québec inc. (Réfrigération Air C)", "9031-8395 Québec inc."),
    ("11888935 Canada Inc. (Workstaff)", "11888935 Canada Inc."),
    # ⚠️ Une parenthèse NON FERMÉE n'est pas touchée : deviner où elle
    # s'arrêterait serait inventer.
    ("9125-5455 Québec inc. (Construction béton 4", "9125-5455 Québec inc. (Construction béton 4"),
    ("Sans parenthèse inc.", "Sans parenthèse inc."),
    (None, ""),
])
def test_le_retrait_porte_sur_le_nom_PUBLIE(nom, attendu):
    assert outil.sans_la_parenthese(nom) == attendu


def test_le_retrait_ne_serait_quun_NO_OP_sur_la_forme_NORMALISEE():
    """⚠️ **Le défaut du 17 septembre, verrouillé.**

    *`normaliser` remplace les parenthèses par des espaces : leur CONTENU
    survit comme mots.* **Appliquer la règle à la forme normalisée ne
    retirerait rien** — et rendrait un no-op déguisé en mesure.
    """
    nom = "Canada inc. (Workstaff)"
    assert "workstaff" in normaliser(nom)
    assert outil.sans_la_parenthese(normaliser(nom)) == normaliser(nom)
    assert "workstaff" not in normaliser(outil.sans_la_parenthese(nom))


# ---------------------------------------------------------------------------
# LA MESURE
# ---------------------------------------------------------------------------

@pytest.fixture()
def decor(db_session, monkeypatch):
    """Un dossier que le retrait SAUVE, un RETENU, un consortium, un sans
    parenthèse, et une parenthèse non fermée."""
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")

    # (a) trop faible → RETENU : le jumeau exact est là, la parenthèse le cache.
    _entree(db_session, "1000000001", "9031-8395 Québec inc.")
    sauve = Company(neq=None, nom_detecte="9031-8395 Québec inc. (Réfrigération Air C)",
                    nom_detecte_normalise=normaliser(
                        "9031-8395 Québec inc. (Réfrigération Air C)"))

    # (b) un consortium : les DEUX entités existent au registre.
    _entree(db_session, "2000000001", "9141-2189 Québec inc.")
    _entree(db_session, "2000000002", "Transfobec Mauricie")
    consortium = Company(
        neq=None,
        nom_detecte="9141-2189 Québec inc. (F.A.S. Transfobec Mauricie) et 9254-6",
        nom_detecte_normalise=normaliser("9141-2189 Québec inc. et 9254-6"))

    # (c) une parenthèse NON FERMÉE — hors de portée de la règle.
    tronque = Company(neq=None, nom_detecte="9125-5455 Québec inc. (Construction béton 4",
                      nom_detecte_normalise=normaliser("9125-5455 Québec inc."))

    # (d) sans parenthèse — hors du plafond.
    _entree(db_session, "3000000001", "Boulangerie Untel inc.")
    hors = Company(neq=None, nom_detecte="Boulangerie Untel inc.",
                   nom_detecte_normalise=normaliser("Boulangerie Untel inc."))

    db_session.add_all([sauve, consortium, tronque, hors])
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return {"session": db_session, "sauve": sauve.id}


def _sortie(capsys):
    return capsys.readouterr().out


def test_le_PLAFOND_compte_les_parentheses_FERMEES_et_signale_les_autres(decor, capsys):
    assert outil.main([]) == 0
    sortie = _sortie(capsys)
    plafond = next(l for l in sortie.splitlines() if "porte une PARENTHÈSE" in l)
    assert _compte(plafond) == "2", plafond          # (a) et (b)
    ouverte = next(l for l in sortie.splitlines() if "OUVERTE que rien ne ferme" in l)
    assert _compte(ouverte) == "1", ouverte          # (c)
    assert "La règle ne les atteint pas" in sortie


def test_le_compte_du_17_septembre_est_REMPLACE_et_non_confirme(decor, capsys):
    """*La population a changé — deux écritures ont eu lieu depuis.*"""
    assert outil.main([]) == 0
    sortie = _sortie(capsys)
    assert "259 sur 8 931" in sortie
    assert "remplace l'autre, il ne le confirme pas" in sortie


def test_le_RETRAIT_fait_passer_le_dossier_de_trop_faible_a_RETENU(decor, capsys):
    assert outil.main([]) == 0
    bloc = _sortie(capsys).split("famille AVANT")[1]
    ligne = next(l for l in bloc.splitlines()
                 if l.strip().startswith("trop faible") and "RETENU" in l)
    assert "← le gain cherché" in ligne, ligne


def test_les_RETENUS_PERDUS_sont_rendus_AVANT_le_gain(decor, capsys):
    """⚠️ *C'est le critère, pas un effet secondaire* — donc avant le tableau."""
    assert outil.main([]) == 0
    sortie = _sortie(capsys)
    assert sortie.index("RETENUS PERDUS") < sortie.index("famille AVANT")
    ligne = next(l for l in sortie.splitlines() if "RETENUS PERDUS" in l)
    assert ligne.split()[-1] == "0", ligne
    assert "Le registre n'étant pas touché" in sortie


def test_la_sortie_DIT_de_quel_cote_et_rappelle_lautre_chiffrage(decor, capsys):
    """⚠️ *Une mesure qui ne dit pas de quel côté se relira comme la
    précédente.*"""
    assert outil.main([]) == 0
    sortie = _sortie(capsys)
    assert "ELLE NE TOUCHE PAS AU REGISTRE" in sortie
    assert "+17 net, 30 gagnés pour 13 PERDUS" in sortie
    assert "SEUL LE NOM DÉTECTÉ EST TRANSFORMÉ" in sortie
    assert "LE REGISTRE N'A PAS ÉTÉ TOUCHÉ" in sortie


def test_le_CONSORTIUM_est_compte_a_part_et_jamais_retire(decor, capsys):
    """⚠️ *Le retrait ne le résout pas : il le déplace.*"""
    assert outil.main([]) == 0
    sortie = _sortie(capsys)
    ligne = next(l for l in sortie.splitlines() if "PLUSIEURS entreprises" in l)
    assert _compte(ligne) == "1", ligne
    assert "attend le chantier 3" in sortie
    assert "jamais retirés du total" in sortie


def test_la_TETE_DE_TABLE_est_comparee_a_la_population(decor, capsys):
    """⚠️ *Cinq cas pris par `id` croissant décrivent peut-être la tête* —
    cas 19, et la mesure doit le dire."""
    assert outil.main([]) == 0
    sortie = _sortie(capsys)
    assert "si la TÊTE DE TABLE est représentative" in sortie
    assert "écart entre la tête et la population" in sortie
    # ⚠️ La taille RÉELLE de la tête, pas celle demandée : le décor n'a que deux
    # dossiers à parenthèse, donc `--tete 5` ne peut pas en montrer cinq.
    assert "les 2 premiers par id" in sortie, sortie
    assert "Ça ne vaut que pour CE critère" in sortie


def test_le_changement_de_LOT_est_compte_et_non_suppose(decor, capsys):
    """*Retirer des mots change le mot le plus RARE, donc le lot du second
    temps.*"""
    assert outil.main([]) == 0
    sortie = _sortie(capsys)
    assert "le lot de candidats a CHANGÉ" in sortie
    assert "n'est donc pas qu'un changement de" in sortie


def test_il_NECRIT_RIEN(decor):
    session = decor["session"]
    avant = {c.id: c.neq for c in session.execute(select(Company)).scalars()}
    assert outil.main([]) == 0
    session.expire_all()
    assert {c.id: c.neq for c in session.execute(select(Company)).scalars()} == avant


def test_les_echelles_ne_bougent_pas(decor):
    from falkye import resolution

    assert outil.main([]) == 0
    assert resolution.SEUIL_RESOLUTION_CONFIANTE == 92.0
    assert resolution.SEUIL_AMBIGUITE_ECART_MIN == 8.0
