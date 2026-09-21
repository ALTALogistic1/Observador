"""Les noms périmés sont-ils déjà en production — **une mesure, elle n'écrit rien.**

⚠️ **Ce que ces tests verrouillent :** que « plus en vigueur » ne se confonde
jamais avec « statut inconnu », et que la mesure lise **la forme qui a gagné**,
pas la dénomination élue. *La garde du chargeur a été retirée le 17 septembre et
la règle du moteur n'a jamais été posée — c'est ce trou que cet outil chiffre.*
"""
from __future__ import annotations

import datetime as _dt

import pytest

from falkye.models.company import Company, StatutResolution
from falkye.models.req_entry import REQEntry
from falkye.models.req_nom import REQNom
from falkye.sources.column_mapping import normaliser
from outils import noms_perimes_en_production as outil


class _Forme:
    def __init__(self, statut, elue=False, nom="x", gisement="NOM_ASSUJ"):
        self.statut = statut
        self.est_la_denomination_elue = elue
        self.nom_publie = nom
        self.nom_normalise = nom
        self.gisement = gisement


@pytest.mark.parametrize("forme, attendu", [
    (_Forme("V"), outil.EN_VIGUEUR),
    (_Forme("v"), outil.EN_VIGUEUR),
    (_Forme("A"), outil.PERIME),
    (_Forme(None), outil.NON_QUALIFIE),
    (_Forme("?"), outil.NON_QUALIFIE),
    (_Forme("V", elue=True), outil.ELUE),
    (None, outil.NON_QUALIFIE),
])
def test_chaque_nature_est_un_RESULTAT_distinct(forme, attendu):
    """⚠️ *« Statut inconnu » n'est pas « en vigueur ».* **Les confondre ferait
    passer pour sûr ce dont le gisement ne dit rien.**"""
    assert outil.nature_de(forme) == attendu


def test_le_statut_non_qualifie_est_EMPRUNTE_au_module_du_REQ():
    from falkye.sources.req import STATUT_NON_QUALIFIE

    assert outil.nature_de(_Forme(STATUT_NON_QUALIFIE)) == outil.NON_QUALIFIE


def test_la_colonne_tient_toutes_ses_etiquettes():
    for nature in outil.NATURES:
        assert len(nature) < outil.LARGEUR, nature


@pytest.fixture()
def decor(db_session, monkeypatch):
    """Un NEQ posé dont la porte d'entrée est un nom PLUS EN VIGUEUR."""
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")

    db_session.add(Company(neq="1400000001", nom_detecte="Tannerie Zibeline inc",
                           nom_detecte_normalise=normaliser("Tannerie Zibeline inc"),
                           statut_resolution=StatutResolution.RESOLU,
                           first_detected_at=_dt.datetime(2026, 1, 1)))
    # ⚠️ La dénomination élue ne ressemble PAS au nom détecté : seule la forme
    # périmée de `req_noms` peut faire entrer ce candidat.
    db_session.add(REQEntry(neq="1400000001", nom="9999-0000 Québec inc.",
                            nom_normalise=normaliser("9999-0000 Québec inc."),
                            statut="immatriculee"))
    db_session.add(REQNom(neq="1400000001", nom="Tannerie Zibeline inc",
                          nom_normalise=normaliser("Tannerie Zibeline inc"),
                          statut="A", type_nom="NOM", gisement="NOM_ASSUJ"))
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def test_la_mesure_N_ECRIT_RIEN_et_compte_le_nom_PERIME(decor, capsys):
    avant = {c.id: c.neq for c in decor.query(Company).all()}
    assert outil.main(["--pas", "0", "--exemples", "3"]) == 0
    sortie = capsys.readouterr().out
    assert {c.id: c.neq for c in decor.query(Company).all()} == avant
    assert "RIEN N'A ÉTÉ ÉCRIT" in sortie
    from tests.conftest import compte_de_la_ligne

    ligne = next(l for l in sortie.splitlines()
                 if l.strip().startswith(outil.PERIME))
    assert compte_de_la_ligne(ligne) == "1", ligne
    # ⚠️ Et la paire montre la forme QUI A DÉCIDÉ, pas la dénomination élue.
    assert "a scoré sur « Tannerie Zibeline inc »" in sortie
    assert "[nom : A]" in sortie


def test_la_garde_retiree_et_la_regle_manquante_sont_DITES(decor, capsys):
    """⚠️ *Une garde retirée d'un endroit et jamais posée dans l'autre ne laisse
    aucune trace.* **La sortie la nomme, avec son commit.**"""
    assert outil.main(["--pas", "0"]) == 0
    sortie = capsys.readouterr().out
    assert "a362d35" in sortie
    assert "porte à PLEINE FORCE" in sortie.replace("\n", " ")
    assert "L'EXPOSITION, JAMAIS L'ERREUR" in sortie


def test_la_prediction_sur_les_lignes_SANS_GISEMENT_est_controlee(decor, capsys):
    """*Les lignes d'avant le 17 devraient toutes être en vigueur.* ⚠️ **Si la
    prédiction tombe, la sortie le dit avant qu'on interprète la suite.**"""
    assert outil.main(["--pas", "0"]) == 0
    sortie = capsys.readouterr().out
    assert "LA PRÉDICTION, ET SON CONTRÔLE" in sortie
    assert "attendu : 0" in sortie
