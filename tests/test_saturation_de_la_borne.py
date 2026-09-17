"""La borne de récupération coupe-t-elle le lot — et l'outil sait-il le dire?

⚠️ **Ce que ces tests gardent.** *Un outil qui écrirait `2000` en dur
continuerait à annoncer « saturé » sur une borne qui aurait changé.* La borne se
lit dans le moteur, et la récupération mesurée est **la vraie**, pas une requête
recopiée à côté.
"""
from __future__ import annotations

import pytest

from falkye.models.company import Company
from falkye.models.req_entry import REQEntry
from falkye.sources import req as req_source
from falkye.sources.column_mapping import normaliser
from outils import saturation_de_la_borne
from outils.saturation_de_la_borne import _forme_du_prefixe


def test_la_forme_du_prefixe_separe_trois_populations():
    """*Un préfixe numérique est quasi unique, un préfixe parlant ne l'est pas —
    et une moyenne des deux ne décrirait aucun des deux.*"""
    assert _forme_du_prefixe("11888935") == "numérique"
    assert _forme_du_prefixe("9224") == "numérique"
    assert _forme_du_prefixe("gestion") == "parlant"
    assert _forme_du_prefixe("") == "(vide)"


def _cible_declaree(monkeypatch):
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")


# ---------------------------------------------------------------------------
# LE JOURNAL DE LA RÉCUPÉRATION — chemin de production inchangé
# ---------------------------------------------------------------------------


def test_le_journal_ne_change_RIEN_au_resultat(db_session):
    """⚠️ **La garde qui compte.** *`journal` remplit un dictionnaire; il ne
    doit pas déplacer une seule ligne du lot rendu.*"""
    for i in range(5):
        nom = f"Gestion Boreal {i}"
        db_session.add(REQEntry(neq=f"10000000{i}", nom=nom,
                                nom_normalise=normaliser(nom), statut="IMMATRICULÉE"))
    db_session.commit()

    sans = req_source.candidats_par_nom(db_session, normaliser("Gestion Boreal"))
    journal: dict = {}
    avec = req_source.candidats_par_nom(
        db_session, normaliser("Gestion Boreal"), journal=journal
    )
    assert [c.neq for c in sans] == [c.neq for c in avec]
    assert journal["total"] == len(sans)
    assert journal["prefixe"] == "gestion"
    assert journal["sature"] is False


def test_le_journal_dit_SATURE_quand_la_borne_coupe(db_session):
    """*Le seul chiffre qui départage l'hypothèse* — il doit être vrai quand la
    borne coupe, et faux quand elle ne coupe pas."""
    for i in range(6):
        nom = f"Gestion Boreal {i}"
        db_session.add(REQEntry(neq=f"20000000{i}", nom=nom,
                                nom_normalise=normaliser(nom), statut="IMMATRICULÉE"))
    db_session.commit()

    journal: dict = {}
    lot = req_source.candidats_par_nom(
        db_session, normaliser("Gestion Boreal"), limite=3, journal=journal
    )
    assert len(lot) == 3
    assert journal["sature"] is True
    assert journal["limite"] == 3
    assert journal["glob_principal"] == 3, "la requête principale a bien été coupée"


def test_le_journal_dit_le_REPLI_par_sous_chaine(db_session):
    """*Le préfixe sans réponse et le repli par sous-chaîne sont deux chemins
    différents, et le second n'est pas une récupération normale.*"""
    nom = "Entreprises Zephyr du Nord"
    db_session.add(REQEntry(neq="3000000000", nom=nom, nom_normalise=normaliser(nom),
                            statut="IMMATRICULÉE"))
    db_session.commit()

    journal: dict = {}
    # « zephyr… » ne préfixe rien; les six premiers caractères, si.
    req_source.candidats_par_nom(db_session, "zephyr du nord", journal=journal)
    assert journal["repli_principal"] is True


@pytest.fixture()
def population(db_session, monkeypatch):
    _cible_declaree(monkeypatch)
    nom = "Transport Boreal inc"
    db_session.add(REQEntry(neq="4000000000", nom=nom, nom_normalise=normaliser(nom),
                            statut="IMMATRICULÉE"))
    db_session.add(Company(neq=None, nom_detecte="Transport Boreal inc",
                           nom_detecte_normalise=normaliser("Transport Boreal inc")))
    db_session.add(Company(neq=None, nom_detecte="11888935 Canada inc",
                           nom_detecte_normalise=normaliser("11888935 Canada inc")))
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def test_ce_que_la_mesure_ne_dira_pas_vient_AVANT_les_chiffres(population, capsys):
    assert saturation_de_la_borne.main([]) == 0
    sortie = capsys.readouterr().out
    assert sortie.index("CE QUE CETTE MESURE NE DIRA PAS") < sortie.index("dossiers sans NEQ")
    assert "ELLE COMPTE DES COUPES, PAS DES PERTES" in sortie
    assert "REPRODUCTIBLE, pas MEILLEUR" in sortie
    assert "RIEN N'EST CONSTRUIT ICI" in sortie


def test_la_borne_est_LUE_dans_le_moteur_jamais_recopiee(population, capsys):
    """⚠️ *Un outil qui écrirait `2000` en dur mentirait si la borne changeait.*"""
    assert saturation_de_la_borne.main([]) == 0
    sortie = capsys.readouterr().out
    assert f"BORNE EN VIGUEUR : {req_source.LIMITE_CANDIDATS_PAR_NOM}" in sortie


def test_le_verdict_est_rendu_quand_la_borne_ne_coupe_JAMAIS(population, capsys):
    """*Si elle ne sature jamais, le lot est complet et l'hypothèse ne récupère
    rien* — et l'outil doit le dire, pas laisser lire un tableau de zéros."""
    assert saturation_de_la_borne.main([]) == 0
    sortie = capsys.readouterr().out
    assert "lots COUPÉS par la borne : 0 sur 2" in sortie, sortie
    assert "LA BORNE NE COUPE JAMAIS" in sortie
    assert "l'hypothèse se" in sortie.lower()


def test_la_ventilation_par_forme_de_prefixe_est_rendue(population, capsys):
    assert saturation_de_la_borne.main([]) == 0
    sortie = capsys.readouterr().out
    bloc = sortie[sortie.index("PAR FORME DU PRÉFIXE"):]
    assert "numérique" in bloc and "parlant" in bloc
    # Un dossier de chaque forme dans le décor.
    ligne_num = next(l for l in bloc.splitlines() if l.strip().startswith("numérique"))
    assert ligne_num.split()[1] == "1", ligne_num


def test_il_NECRIT_RIEN(population):
    from sqlalchemy import select

    avant = {c.id: c.neq for c in population.execute(select(Company)).scalars().all()}
    assert saturation_de_la_borne.main([]) == 0
    population.expire_all()
    apres = {c.id: c.neq for c in population.execute(select(Company)).scalars().all()}
    assert avant == apres


def test_les_echelles_ne_bougent_pas(population):
    from falkye import resolution

    assert saturation_de_la_borne.main([]) == 0
    assert resolution.SEUIL_RESOLUTION_CONFIANTE == 92.0
    assert resolution.SEUIL_AMBIGUITE_ECART_MIN == 8.0
