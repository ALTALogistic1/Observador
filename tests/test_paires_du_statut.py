"""Les paires du statut — lire avant d'en faire une règle.

⚠️ **Ce que ces tests verrouillent : que la sortie ne fournisse pas un substitut
à ce qui manque.** *Il n'existe aucune date de radiation. `date_maj_req` en est
voisine et n'en est pas une* — l'afficher serait le défaut du 20 septembre, une
colonne vraie lue à la place de l'absente.
"""
from __future__ import annotations

import datetime as _dt

import pytest

from falkye.models.company import Company
from falkye.models.req_entry import REQEntry
from falkye.models.signal import Signal
from falkye.sources.column_mapping import normaliser
from outils import paires_du_statut as outil


class _Match:
    def __init__(self, statut, score=100.0):
        self.entry = type("E", (), {"statut": statut})()
        self.score = score


# ---------------------------------------------------------------------------
# LES LOTS — et la divergence l'emporte
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("statuts, egalite, attendu", [
    (["immatriculee", "radiee"], True, outil.EGALITE),
    (["immatriculee", "radiee"], False, outil.ECART),
    (["radiee", "radiee"], True, outil.VIDE),
    # ⚠️ `ni` fait diverger les deux formes : c'est un dossier de DÉCISION.
    (["immatriculee", "ni"], True, outil.DIVERGENCE),
    (["ni", "radiee"], True, outil.DIVERGENCE),
    # Deux immatriculées : l'exclusion ne départage pas, le dossier n'est pas lu.
    (["immatriculee", "immatriculee"], True, None),
])
def test_le_lot_se_choisit_et_la_DIVERGENCE_l_emporte(statuts, egalite, attendu):
    assert outil.lot_du_dossier([_Match(s) for s in statuts], egalite) == attendu


@pytest.mark.parametrize("statuts, exclusion, attendu", [
    (["immatriculee", "ni", "radiee"], outil.GARDER_IMMATRICULEES, 1),
    (["immatriculee", "ni", "radiee"], outil.ECARTER_RADIEES, 2),
    (["radiee", "radiee"], outil.ECARTER_RADIEES, 0),
])
def test_ce_que_chaque_exclusion_laisse_debout(statuts, exclusion, attendu):
    assert len(outil.restants_apres([_Match(s) for s in statuts], exclusion)) == attendu


def test_le_balayage_est_EMPRUNTE_jamais_recopie():
    """*C'est lui qui porte le cas 19, tombé deux fois cette semaine.*"""
    from outils import lecture_des_dossiers

    assert outil.a_pas_constant is lecture_des_dossiers.a_pas_constant


def test_ce_qui_n_est_pas_rendu_est_NOMME_dans_le_code():
    assert "date_maj_req" in outil.CE_QUI_NEST_PAS_RENDU
    assert "PAS une date de radiation" in outil.CE_QUI_NEST_PAS_RENDU


# ---------------------------------------------------------------------------
# LA LECTURE, DE BOUT EN BOUT
# ---------------------------------------------------------------------------

#: ⚠️ Une date distinctive : si elle sort quelque part, la garde de N192 a sauté.
DATE_PIEGE = _dt.datetime(2019, 3, 7)


@pytest.fixture()
def decor(db_session, monkeypatch):
    """Les quatre lots, un dossier chacun."""
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")

    #: (nom détecté, [(nom au registre, statut)])
    dossiers = [
        ("Pecheries Alpha inc",
         [("Pecheries Alpha inc", "immatriculee"), ("Pecheries Alpha inc", "radiee")]),
        ("Pecheries Beta inc",
         [("Pecheries Beta inc", "immatriculee"), ("Pecheries Beta inc", "ni")]),
        ("Pecheries Gamma inc",
         [("Pecheries Gamma inc", "radiee"), ("Pecheries Gamma inc", "radiee")]),
        # ⚠️ Écart de 5 : le score désignait déjà un gagnant.
        ("Pecheries Delta inc",
         [("Pecheries Delta inc", "immatriculee"), ("Pecheries Delta", "radiee")]),
    ]
    for i, (nom, au_registre) in enumerate(dossiers):
        company = Company(neq=None, nom_detecte=nom,
                          nom_detecte_normalise=normaliser(nom), ville="Québec")
        db_session.add(company)
        db_session.flush()
        db_session.add(Signal(
            company_id=company.id, source_id="seao",
            signal_type_id="recrutement_massif",
            detected_at=_dt.datetime(2026, 1, 1), champs={},
        ))
        for j, (nom_req, statut) in enumerate(au_registre):
            db_session.add(REQEntry(
                neq=f"11{i}000000{j}", nom=nom_req, nom_normalise=normaliser(nom_req),
                statut=statut, ville=None, date_maj_req=DATE_PIEGE))
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def _sortie(capsys):
    return capsys.readouterr().out


def test_ce_que_la_lecture_ne_fera_pas_vient_AVANT_les_paires(decor, capsys):
    assert outil.main(["--pas", "0", "--par-lot", "3"]) == 0
    sortie = _sortie(capsys)
    assert sortie.index("POSER LA RÈGLE") < sortie.index("AMBIGUS :")
    assert "NI JUGER À NOTRE PLACE" in sortie
    assert "PLAUSIBLE" in sortie and "JUSTE" in sortie


def test_la_reserve_sur_la_radiation_est_dite_avant_les_paires(decor, capsys):
    assert outil.main(["--pas", "0", "--par-lot", "3"]) == 0
    sortie = _sortie(capsys)
    assert "UNE ENTREPRISE RADIÉE PEUT ÊTRE LA BONNE" in sortie
    assert "AUCUNE\n   date de radiation" in sortie


def test_date_maj_req_est_NOMMEE_et_JAMAIS_rendue(decor, capsys):
    """⚠️ **La garde principale du fichier.** *Une colonne vraie posée à côté de
    celle qui manque se lit à sa place — c'est N192.*"""
    assert outil.main(["--pas", "0", "--par-lot", "3"]) == 0
    sortie = _sortie(capsys)
    assert "date_maj_req" in sortie, "elle doit être NOMMÉE, pour qu'on ne la cherche pas"
    assert "PAS une date de radiation" in sortie
    # ⚠️ Et sa VALEUR ne sort nulle part.
    assert "2019" not in sortie, "la date a fui dans la sortie"


def test_les_quatre_lots_sont_rendus_et_comptes(decor, capsys):
    assert outil.main(["--pas", "0", "--par-lot", "3"]) == 0
    sortie = _sortie(capsys)
    for lot in outil.ORDRE_DES_LOTS:
        assert lot.upper() in sortie, lot
    assert "LA DIVERGENCE L'EMPORTE" in sortie


def test_le_lot_a_ECART_porte_son_avertissement(decor, capsys):
    """*Si l'exclusion garde un AUTRE candidat que le mieux scoré, c'est le cas
    le plus lourd de la lecture.*"""
    assert outil.main(["--pas", "0", "--par-lot", "3"]) == 0
    sortie = _sortie(capsys)
    assert "LE SCORE DÉSIGNAIT DÉJÀ UN GAGNANT" in sortie


def test_un_lot_VIDE_se_lit_autrement_et_la_sortie_le_dit(decor, capsys):
    assert outil.main(["--pas", "0", "--par-lot", "3"]) == 0
    sortie = _sortie(capsys)
    assert "N'EST PAS UN DÉPARTAGE MANQUÉ" in sortie
    assert "soit l'entreprise a" in sortie


def test_chaque_paire_rend_le_restant_ET_les_ecartes_avec_leur_statut(decor, capsys):
    assert outil.main(["--pas", "0", "--par-lot", "3"]) == 0
    bloc = _sortie(capsys).split(outil.EGALITE.upper())[1]
    assert "RESTE" in bloc and "écarté" in bloc
    assert "[immatriculee]" in bloc and "[radiee]" in bloc


def test_l_indication_d_adresse_vient_du_DEPARTAGEUR_du_produit(decor, capsys):
    """*La fonction du produit, jamais une règle de plus.*"""
    from outils.departageurs import ISSUES

    assert outil.main(["--pas", "0", "--par-lot", "3"]) == 0
    sortie = _sortie(capsys)
    assert "le lieu :" in sortie
    assert any(issue in sortie for issue in ISSUES), "aucune issue du départageur"


def test_l_exclusion_retenue_est_dite_dans_la_sortie(decor, capsys):
    assert outil.main(["--pas", "0", "--par-lot", "3", "--exclusion", "radiees"]) == 0
    assert outil.ECARTER_RADIEES in _sortie(capsys)


def test_aucune_ecriture(decor, capsys):
    from falkye.resolution import SEUIL_AMBIGUITE_ECART_MIN, SEUIL_RESOLUTION_CONFIANTE

    avant = {c.id: c.neq for c in decor.query(Company).all()}
    assert outil.main(["--pas", "0", "--par-lot", "3"]) == 0
    sortie = _sortie(capsys)
    assert (f"seuil {SEUIL_RESOLUTION_CONFIANTE:.0f}, "
            f"écart {SEUIL_AMBIGUITE_ECART_MIN:.0f}") in sortie
    assert "RIEN N'A ÉTÉ ÉCRIT" in sortie
    assert {c.id: c.neq for c in decor.query(Company).all()} == avant
