"""Ce que la promotion rendrait — et la réponse n'est pas la même aux deux niveaux.

⚠️ *Le départageur lit `Signal.champs` directement; la promotion sert
`RawSignal`.* **Si tout ce qui compte passe déjà par `faits_du_dossier`, la
promotion est un travail de propreté, pas un gain.**
"""
from __future__ import annotations

import datetime as _dt

import pytest
from sqlalchemy import select

from falkye.models.company import Company
from falkye.models.req_entry import REQEntry
from falkye.models.signal import Signal
from falkye.sources.column_mapping import normaliser
from outils import chiffrage_de_la_promotion as outil
from tests.conftest import compte_de_la_ligne as _compte


# ---------------------------------------------------------------------------
# LES DEUX LECTEURS — et les clés que chacun connaît
# ---------------------------------------------------------------------------

def test_le_lecteur_de_VILLE_ignore_la_cle_agregee_du_SEAO():
    """⚠️ **Ce qui explique l'asymétrie du SEAO — 88,7 % contre 9,6 %.**

    *Le champ agrégé porte les deux; seul le lecteur de CODE POSTAL le
    connaît.* **La ville du SEAO n'est pas absente : elle est invisible au
    lecteur qui la cherche.**
    """
    from outils.departageur_adresse import CLES_ADRESSE
    from outils.villes_des_signaux import CLE_ADRESSE, CLES_VILLE

    assert "adresse_entreprise_adjudicataire" in CLES_ADRESSE
    assert "adresse_entreprise_adjudicataire" not in CLES_VILLE
    assert CLE_ADRESSE == "adresse"


def test_villes_des_signaux_prend_des_CLES_en_parametre(db_session):
    """⚠️ *Un chiffrage demande « et si on lisait une clé de plus? » par un APPEL
    de cette fonction, jamais par une copie.*"""
    from outils.villes_des_signaux import villes_des_signaux

    c = Company(neq=None, nom_detecte="X inc.",
                nom_detecte_normalise=normaliser("X inc."))
    db_session.add(c)
    db_session.flush()
    db_session.add(Signal(
        company_id=c.id, source_id="seao", signal_type_id="contrat",
        detected_at=_dt.datetime(2026, 1, 1),
        champs={"adresse_entreprise_adjudicataire": "Lévis, QC G6V 1A1"}))
    db_session.commit()

    assert villes_des_signaux(db_session, {c.id}) == {}
    elargi = villes_des_signaux(
        db_session, {c.id},
        cles_adresse=("adresse", "adresse_entreprise_adjudicataire"))
    assert elargi[c.id].ville == "Lévis"


# ---------------------------------------------------------------------------
# LA MESURE
# ---------------------------------------------------------------------------

@pytest.fixture()
def decor(db_session, monkeypatch):
    """Un SEAO dont la clé agrégée porte une VILLE, un autre dont elle porte une
    RUE, et un EIMT déjà lu par les deux lecteurs."""
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")

    for neq, nom, ville, cp in (
        ("1000000001", "Gagnon Freres inc", "Levis", "G6V 1A1"),
        ("1000000002", "Gagnon Freres ltee", "Laval", "H7A 1B1"),
    ):
        db_session.add(REQEntry(neq=neq, nom=nom, nom_normalise=normaliser(nom),
                                statut="IMMATRICULÉE", ville=ville, code_postal=cp))

    seao_ville = Company(neq=None, nom_detecte="Gagnon Freres",
                         nom_detecte_normalise=normaliser("Gagnon Freres"))
    seao_rue = Company(neq=None, nom_detecte="Autre inc.",
                       nom_detecte_normalise=normaliser("Autre inc."))
    eimt = Company(neq=None, nom_detecte="Troisieme inc.",
                   nom_detecte_normalise=normaliser("Troisieme inc."))
    db_session.add_all([seao_ville, seao_rue, eimt])
    db_session.flush()
    db_session.add_all([
        Signal(company_id=seao_ville.id, source_id="seao", signal_type_id="contrat",
               detected_at=_dt.datetime(2026, 1, 1),
               champs={"adresse_entreprise_adjudicataire": "Lévis, QC G6V 1A1"}),
        # ⚠️ La tête de chaîne y est une RUE, pas une municipalité.
        Signal(company_id=seao_rue.id, source_id="seao", signal_type_id="contrat",
               detected_at=_dt.datetime(2026, 1, 1),
               champs={"adresse_entreprise_adjudicataire":
                       "123 rue Principale, Montréal, QC H2N 1A1"}),
        # L'EIMT : `adresse` est lue par les DEUX lecteurs déjà.
        Signal(company_id=eimt.id, source_id="eimt",
               signal_type_id="recrutement_massif",
               detected_at=_dt.datetime(2026, 1, 1),
               champs={"adresse": "St-Isidore, QC J0L 2A1"}),
    ])
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def _sortie(capsys):
    return capsys.readouterr().out


def test_la_question_qui_decide_vient_AVANT_les_chiffres(decor, capsys):
    assert outil.main([]) == 0
    sortie = _sortie(capsys)
    assert sortie.index("SE LIT DANS LE CODE, PAS DANS UNE MESURE") < sortie.index("seao")
    assert "repli sur la SEULE clé 'adresse'" in sortie


def test_pour_lEIMT_la_cle_najoute_RIEN_donc_la_promotion_est_de_la_proprete(decor, capsys):
    """⚠️ *`champs['adresse']` est lu par les DEUX lecteurs déjà.*"""
    assert outil.main(["--source", "eimt"]) == 0
    sortie = _sortie(capsys)
    ligne = next(l for l in sortie.splitlines() if "une VILLE de plus" in l)
    assert _compte(ligne) == "0", ligne
    assert "elle servirait le PORTRAIT" in sortie
    assert "travail de propreté, pas un gain" in sortie


def test_pour_le_SEAO_la_cle_ajoute_des_villes_ET_montre_les_RUES(decor, capsys):
    """⚠️ *Une rue prise pour une ville ne manque pas un départage : elle en
    PRONONCE un faux.*"""
    assert outil.main(["--source", "seao"]) == 0
    sortie = _sortie(capsys)
    ligne = next(l for l in sortie.splitlines() if "une VILLE de plus" in l)
    assert _compte(ligne) == "2", ligne
    assert "→ tête : 'Lévis'" in sortie
    assert "⚠️ RUE?" in sortie
    assert "→ tête : '123 rue Principale'" in sortie
    suspectes = next(l for l in sortie.splitlines() if "COMMENCENT PAR UN NUMÉRO" in l)
    assert "1 sur 2" in suspectes, suspectes


def test_lecart_au_DEPARTAGE_est_chiffre_et_non_suppose(decor, capsys):
    assert outil.main(["--source", "seao"]) == 0
    sortie = _sortie(capsys)
    assert "départagés AUJOURD'HUI" in sortie
    assert "départagés AVEC la clé de plus" in sortie
    assert "⇒ écart" in sortie


def test_la_mesure_ne_tranche_PAS_RawSignal(decor, capsys):
    """⚠️ *C'est une décision de modèle, pas une conséquence de ces chiffres.*"""
    assert outil.main([]) == 0
    sortie = _sortie(capsys)
    assert "n'a toujours pas d'emplacement" in sortie
    assert "décision de modèle" in sortie


def test_il_NECRIT_RIEN(decor):
    avant = {c.id: c.neq for c in decor.execute(select(Company)).scalars()}
    assert outil.main([]) == 0
    decor.expire_all()
    assert {c.id: c.neq for c in decor.execute(select(Company)).scalars()} == avant


def test_les_echelles_ne_bougent_pas(decor):
    from falkye import resolution

    assert outil.main([]) == 0
    assert resolution.SEUIL_RESOLUTION_CONFIANTE == 92.0
    assert resolution.SEUIL_AMBIGUITE_ECART_MIN == 8.0
