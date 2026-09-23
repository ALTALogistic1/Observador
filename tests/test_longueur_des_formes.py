"""De quoi POSER une borne de longueur au scorage — **la mesure n'écrit rien,
et elle ne propose AUCUNE valeur.**

⚠️ *« Je ne veux pas de valeur posée pour débloquer : je la poserai avec
Claude »* (Alexandre, 2026-09-23). **Un test le verrouille** : l'outil ne doit
jamais nommer une borne recommandée.
"""
from __future__ import annotations

import datetime as _dt

import pytest

from falkye.models.company import Company, StatutResolution
from falkye.models.req_entry import REQEntry
from falkye.models.req_nom import REQNom
from falkye.sources.column_mapping import normaliser
from outils import longueur_des_formes as outil


def test_la_longueur_se_mesure_sur_la_forme_NORMALISEE():
    """*C'est la forme normalisée que le scoreur compare* — borner sur le nom
    publié bornerait une chaîne que personne ne score."""
    transformer = outil.transformateur_de_borne(3)
    assert transformer("LA") == ""                      # « la » — 2 caractères
    assert transformer("Boulangerie") == "Boulangerie"


def test_l_UNITE_TRANCHEE_est_la_LETTRE():
    """✅ **Tranchée par Alexandre le 2026-09-23** *(registre D60)* : *« c'est la
    seule qui traite `« LA »` et `« L.A. »` comme la même porte. »*

    ⬜ *La VALEUR, elle, n'est toujours pas posée* — et le test qui l'interdit
    est juste en dessous.
    """
    import inspect

    assert inspect.signature(outil.transformateur_de_borne).parameters[
        "mesure"].default == "lettres"
    # Et le défaut de la ligne de commande dit la même chose.
    assert outil.transformateur_de_borne(3)("L.A.") == ""
    assert outil.transformateur_de_borne(3)("LA") == ""


def test_les_TROIS_mesures_ne_classent_PAS_pareil():
    """⛔ **La sous-question, verrouillée par le cas qui la pose.** *`« L.A. »`
    se normalise en `« l a »` : 3 caractères, 2 lettres, 2 mots.* **Une borne
    de 3 caractères retirerait `« LA »` et garderait `« L.A. »`, qui est la même
    porte.**"""
    assert outil.MESURES["caracteres"][1]("l a") == 3
    assert outil.MESURES["lettres"][1]("l a") == 2
    assert outil.MESURES["mots"][1]("l a") == 2
    assert outil.transformateur_de_borne(3, "caracteres")("L.A.") == "L.A."
    assert outil.transformateur_de_borne(3, "lettres")("L.A.") == ""


def test_la_forme_gagnante_n_est_PAS_la_denomination_elue():
    """⚠️ **Le défaut d'affichage du 21 septembre, verrouillé.** *`_scorer`
    prend le MEILLEUR des noms d'un NEQ* — lire `entry.nom` mesurerait une
    forme qui n'a pas scoré."""
    import inspect

    source = inspect.getsource(outil.forme_gagnante)
    assert "return matches[0].forme_normalisee" in source
    assert "return matches[0].entry.nom" not in source
    assert outil.forme_gagnante([]) is None


def test_les_tranches_couvrent_toutes_les_longueurs():
    for longueur in range(1, 60):
        assert outil.tranche_de(longueur) in outil.TRANCHES
    assert outil.tranche_de(10_000) == outil.TRANCHES[-1]


def test_la_borne_1_est_le_TEMOIN():
    """*Si la ligne du témoin n'est pas à zéro, l'instrument ment.*"""
    assert 1 in outil.BORNES_PAR_DEFAUT
    transformer = outil.transformateur_de_borne(1)
    assert transformer("LA") == "LA"  # rien n'est retiré


@pytest.fixture()
def decor(db_session, monkeypatch):
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")
    # ⚠️ LE CAS RÉEL : une forme de DEUX LETTRES qui score 95 parce qu'elle est
    # entièrement contenue dans le nom détecté (`#5476`, « LA »).
    db_session.add(REQEntry(neq="2100000001", nom="9412-0002 Québec inc.",
                            nom_normalise="9412 0002 quebec inc",
                            statut="immatriculee"))
    db_session.add(REQNom(neq="2100000001", nom="LA", nom_normalise="la",
                          statut="V", type_nom="NOM", gisement="NOM_ASSUJ"))
    for nom in ("Boulangerie Saint-Zephirin", ):
        db_session.add(REQEntry(neq="2100000002", nom=nom,
                                nom_normalise=normaliser(nom), statut="immatriculee"))
        db_session.add(REQNom(neq="2100000002", nom=nom, nom_normalise=normaliser(nom),
                              statut="V", type_nom="NOM", gisement="NOM_ASSUJ"))
    for nom, neq in (("LA", None), ("Boulangerie Saint-Zephirin", "2100000002")):
        db_session.add(Company(
            neq=neq, nom_detecte=nom, nom_detecte_normalise=normaliser(nom),
            statut_resolution=(StatutResolution.RESOLU if neq
                               else StatutResolution.AMBIGU),
            first_detected_at=_dt.datetime(2026, 1, 1)))
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def test_la_sortie_ne_propose_AUCUNE_borne(decor, capsys):
    """⛔ **La contrainte d'Alexandre, verrouillée par un test.**"""
    assert outil.main(["--pas", "0", "--bornes", "1", "3"]) == 0
    sortie = capsys.readouterr().out
    assert "AUCUNE BORNE N'EST PROPOSÉE ICI" in sortie
    for mot in ("recommandé", "recommande", "je propose", "il faudrait poser"):
        assert mot not in sortie.lower()


def test_la_sortie_refuse_de_confondre_RETENU_et_BON(decor, capsys):
    """⛔ *La justesse des NEQ posés n'a jamais été mesurée* (§13, point 10)."""
    assert outil.main(["--pas", "0", "--bornes", "1"]) == 0
    sortie = capsys.readouterr().out
    assert "IL NE DIT PAS LESQUELS ÉTAIENT BONS" in sortie
    assert "« RETENUS PERDUS » N'EST PAS « BONS APPARIEMENTS PERDUS »" in sortie


def test_la_sortie_rend_les_trois_choses_demandees(decor, capsys):
    """*La distribution, le coût de chaque borne, et ce que le corpus porte.*"""
    assert outil.main(["--pas", "0", "--bornes", "1", "3"]) == 0
    sortie = capsys.readouterr().out
    assert "1. LA LONGUEUR DE LA FORME GAGNANTE" in sortie
    assert "2. CE QUE CHAQUE BORNE RETIRERAIT" in sortie
    assert "3. CE QUE LE CORPUS PORTE DÉJÀ DE COMPARABLE" in sortie
    # ⚠️ La mesure voisine du corpus est citée AVEC la raison qui l'écarte.
    assert "×3,4" in sortie
    assert "candidats_par_mot_rare" in sortie


def test_le_temoin_ne_retire_rien_sur_le_decor(decor, capsys):
    """*Si la borne 1 retirait quoi que ce soit, le reste ne vaudrait rien.*"""
    assert outil.main(["--pas", "0", "--bornes", "1"]) == 0
    lignes = [ligne for ligne in capsys.readouterr().out.splitlines()
              if ligne.strip().startswith("borne   1")]
    assert lignes, "la ligne du témoin doit être imprimée"
    assert lignes[0].split()[2:] == ["0", "0", "0"]


def test_une_borne_de_trois_retire_bien_la_forme_de_DEUX_LETTRES(decor, capsys):
    """⚠️ **Le cas qui a fait poser la question** — `« LA »` à 95,0."""
    assert outil.main(["--pas", "0", "--bornes", "3", "--paires", "3"]) == 0
    sortie = capsys.readouterr().out
    assert "« la »" in sortie
