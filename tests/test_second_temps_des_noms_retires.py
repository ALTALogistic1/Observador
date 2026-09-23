"""Ce que le troisième temps change — **une mesure, elle n'écrit rien.**

⚠️ **Ce que ces tests verrouillent :** que « perdre son NEQ » et « le rejeu ne
le retrouvait déjà plus » ne se confondent jamais — *le premier accuserait la
règle nouvelle d'une perte qui lui préexiste* — et que les deux causes d'un NEQ
introuvable restent distinctes.
"""
from __future__ import annotations

import datetime as _dt

import pytest

from falkye.models.company import Company, StatutResolution
from falkye.models.req_entry import REQEntry
from falkye.models.req_nom import REQNom
from falkye.sources.column_mapping import normaliser
from outils import second_temps_des_noms_retires as outil


def test_la_colonne_tient_toutes_ses_etiquettes():
    for t in (outil.ISSUES_DES_POSES + outil.ISSUES_DES_RESTANTS
              + outil.CAUSES_DE_LA_PERTE):
        assert len(t) < outil.LARGEUR, t


def test_les_deux_regles_passent_par_DEUX_APPELS_de_la_production():
    """*Une règle recopiée mesurerait sa propre copie.* **Le drapeau
    `retires_en_dernier` existe pour que la comparaison soit un APPEL.**"""
    import inspect

    from falkye.sources.req import resolve_neq_by_name

    assert "retires_en_dernier" in inspect.signature(resolve_neq_by_name).parameters
    source = inspect.getsource(outil.les_deux_regles)
    assert source.count("resolve_neq_by_name") == 2
    assert "retires_en_dernier=False" in source


@pytest.fixture()
def decor(db_session, monkeypatch):
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")

    def entreprise(neq, elue, autres=()):
        db_session.add(REQEntry(neq=neq, nom=elue, nom_normalise=normaliser(elue),
                                statut="immatriculee"))
        for nom, statut in autres:
            db_session.add(REQNom(neq=neq, nom=nom, nom_normalise=normaliser(nom),
                                  statut=statut, type_nom="NOM", gisement="NOM_ASSUJ"))

    def dossier(nom, neq=None):
        db_session.add(Company(
            neq=neq, nom_detecte=nom, nom_detecte_normalise=normaliser(nom),
            statut_resolution=(StatutResolution.RESOLU if neq
                               else StatutResolution.AMBIGU),
            first_detected_at=_dt.datetime(2026, 1, 1)))

    # ⚠️ CHANGE DE NEQ : le nom retiré de l'un, en vigueur chez l'autre.
    entreprise("1800000001", "Carbotech Innovation Inc.",
               [("Zibeline Robotique inc", "A")])
    entreprise("1800000002", "Zibeline Robotique inc",
               [("Zibeline Robotique inc", "V")])
    dossier("Zibeline Robotique inc", "1800000001")

    # INCHANGÉ : son propre ancien nom, personne d'autre ne le porte.
    entreprise("1800000003", "Les Entreprises Douglas Powertech inc.",
               [("Tannerie Orfevre Canada inc", "A")])
    dossier("Tannerie Orfevre Canada inc", "1800000003")

    # ⚠️ INTROUVABLE, PORTE DISPARUE : le NEQ posé n'est récupérable par aucun nom.
    entreprise("1800000004", "Papeterie Lointaine Sans Rapport inc")
    dossier("Chapellerie Introuvable Ailleurs inc", "1800000004")

    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def test_la_mesure_N_ECRIT_RIEN(decor, capsys):
    avant = {c.id: c.neq for c in decor.query(Company).all()}
    assert outil.main(["--pas", "0"]) == 0
    assert {c.id: c.neq for c in decor.query(Company).all()} == avant
    assert "RIEN N'A ÉTÉ ÉCRIT" in capsys.readouterr().out


def test_un_NEQ_deja_introuvable_n_est_PAS_compte_comme_PERDU(decor, capsys):
    """⚠️ **La distinction qui décide.** *Un dossier dont le rejeu ne retrouvait
    DÉJÀ plus le NEQ avant la règle ne se perd pas à cause d'elle.* **Les
    confondre accuserait la règle nouvelle d'une perte qui lui préexiste.**"""
    assert outil.main(["--pas", "0"]) == 0
    sortie = capsys.readouterr().out
    from tests.conftest import compte_de_la_ligne

    perdu = next(l for l in sortie.splitlines() if l.strip().startswith(outil.PERDU))
    deja = next(l for l in sortie.splitlines()
                if "le rejeu ne retrouvait DÉJÀ plus" in l)
    assert compte_de_la_ligne(perdu) == "0", perdu
    assert compte_de_la_ligne(deja) == "1", deja
    assert "Aucun dossier ne perd son NEQ" in sortie


def test_le_changement_de_NEQ_est_compte_et_rendu(decor, capsys):
    assert outil.main(["--pas", "0", "--paires", "5"]) == 0
    sortie = capsys.readouterr().out
    from tests.conftest import compte_de_la_ligne

    change = next(l for l in sortie.splitlines() if l.strip().startswith(outil.CHANGE))
    assert compte_de_la_ligne(change) == "1", change
    bloc = sortie.split("QUI CHANGERAIENT DE NEQ")[1]
    assert "1800000001" in bloc and "1800000002" in bloc
    assert "l'ancienne règle rendait" in bloc


def test_les_deux_causes_d_un_NEQ_introuvable_restent_DISTINCTES(decor, capsys):
    """*« Le lot a grandi » et « la porte a disparu » n'appellent pas la même
    suite* — la première est une dérive annoncée, la seconde un dossier qui a
    changé de nom."""
    assert outil.main(["--pas", "0", "--paires", "5"]) == 0
    sortie = capsys.readouterr().out
    from tests.conftest import compte_de_la_ligne

    disparue = next(l for l in sortie.splitlines()
                    if l.strip().startswith(outil.PORTE_DISPARUE))
    assert compte_de_la_ligne(disparue) == "1", disparue
    assert "1800000004" in sortie
    assert "LA DÉRIVE ANNONCÉE" in sortie


def test_la_garantie_structurelle_est_DITE_avant_les_chiffres(decor, capsys):
    assert outil.main(["--pas", "0"]) == 0
    sortie = capsys.readouterr().out
    assert sortie.index("NE PEUT RIEN FAIRE PERDRE") < sortie.index(
        "LES DOSSIERS DÉJÀ POSÉS")
    assert "RIEN NE CHANGE TOUT SEUL" in sortie
    assert "LE GAIN EST DU MÊME MÉCANISME QUE LE RISQUE" in sortie
