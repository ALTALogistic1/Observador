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


def test_la_cause_est_la_FAMILLE_et_jamais_la_coupe(decor, capsys):
    """⚠️ **La correction du 23 septembre.** *L'outil nommait « le NEQ est passé
    sous la coupe » la cause d'un dossier qu'il ne résout plus.* **C'était faux :
    `neq_retenu` ne lit que `matches[0]` et `matches[1]`, donc relever le plafond
    du lot ne change aucune décision.**"""
    assert outil.main(["--pas", "0", "--paires", "5"]) == 0
    sortie = capsys.readouterr().out
    # ⚠️ La fausse cause n'est plus une ÉTIQUETTE — elle n'apparaît que dans sa
    # propre rétractation. *Un outil qui se corrige doit pouvoir NOMMER ce qu'il
    # disait; l'interdire l'obligerait à se corriger en silence.*
    assert not any("coupe" in c for c in outil.CAUSES_DE_LA_PERTE)
    assert "C'ÉTAIT FAUX" in sortie
    assert "NE CHANGE AUCUNE DÉCISION" in sortie
    assert "LA VRAIE CAUSE est la FAMILLE" in sortie
    # ⚠️ Et « ne résout plus » ne se confond pas avec « le NEQ a disparu ».
    assert any(l.strip().startswith(outil.ABSENT_DU_LOT)
               for l in sortie.splitlines())


def test_une_reprise_NE_RETIRE_RIEN_et_la_sortie_le_dit(decor, capsys):
    """*`reresolution_neq` POSE un NEQ là où la famille est RETENU; il n'efface
    jamais.* **Un dossier devenu ambigu garde le NEQ qu'il porte.**"""
    assert outil.main(["--pas", "0"]) == 0
    sortie = capsys.readouterr().out
    assert "UNE REPRISE NE RETIRE RIEN" in sortie
    assert "RIEN NE CHANGE TOUT SEUL" in sortie


def test_la_FAUSSE_GARANTIE_est_retractee_LA_OU_elle_etait(decor, capsys):
    """⚠️ **Un outil qui s'est trompé doit le dire à l'endroit où il se
    trompait.** *La garantie « perdre son NEQ est impossible » était imprimée en
    tête; la rétractation l'est aussi.*"""
    assert outil.main(["--pas", "0"]) == 0
    sortie = capsys.readouterr().out
    avant = sortie.index("LES DOSSIERS DÉJÀ POSÉS")
    assert sortie.index("UNE GARANTIE QUI ÉTAIT FAUSSE") < avant
    assert sortie.index("valait pour les FORMES, jamais pour le LOT") < avant
    assert "NE PEUT RIEN FAIRE PERDRE" not in sortie


def test_la_garde_des_pretendants_est_dite_DESCENDUE_dans_la_resolution(decor, capsys):
    """⚠️ **Le point le plus grave du 23 septembre, et il est corrigé.** *La
    garde n'a vécu que dans `outils/` du 17 au 23; la sortie dit maintenant
    qu'elle est descendue, ET que la FORME du refus a changé en descendant.*

    ⛔ *Ce test affirmait l'inverse jusqu'au 2026-09-23* — il est retourné, pas
    supprimé : la trace de ce que la sortie disait avant vaut autant que ce
    qu'elle dit maintenant."""
    assert outil.main(["--pas", "0"]) == 0
    sortie = capsys.readouterr().out
    assert "CETTE GARDE EST DESCENDUE DANS LA RÉSOLUTION" in sortie
    assert "LA FORME DU REFUS A CHANGÉ EN DESCENDANT" in sortie
    assert "CE QUI N'EST PAS DESCENDU" in sortie
    assert "D27" in sortie and "D28" in sortie


def test_la_garde_des_pretendants_vit_MAINTENANT_dans_falkye():
    """*Vérifié sur le code, pas sur la sortie* — contre-épreuve du test qui
    affirmait son absence jusqu'au 2026-09-23."""
    import pathlib

    resolution = pathlib.Path("falkye/resolution.py").read_text(encoding="utf-8")
    assert "PRETENDANTS_MAX_POUR_TRANCHER = 2" in resolution
    # ⚠️ EMPRUNTÉE, jamais recopiée — le geste est un geste d'ÉCRITURE.
    pose = pathlib.Path("outils/pose_du_neq.py").read_text(encoding="utf-8")
    assert "from falkye.resolution import PRETENDANTS_MAX_POUR_TRANCHER" in pose
    assert "PRETENDANTS_MAX_POUR_TRANCHER = 2" not in pose
