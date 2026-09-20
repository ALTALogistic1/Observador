"""Les deux limites du statut — les `ni`, et le restant moins bien scoré.

⚠️ **Ce que ces tests verrouillent : le REFUS de classer.** *Les paires lues
contiennent `Ville de Bedford`, `CIUSSS`, `Commission scolaire` — exactement les
mots qu'une heuristique de noms emploierait.* **`outils/donneurs_douvrage.py` a
déjà refusé cette tentation pour D28; ce fichier vérifie qu'on ne la reprend
pas.**
"""
from __future__ import annotations

import datetime as _dt

import pytest

from falkye.models.company import Company
from falkye.models.req_entry import REQEntry
from falkye.models.signal import Signal
from falkye.sources.column_mapping import normaliser
from outils import limites_du_statut as outil
from tests.conftest import compte_de_la_ligne as _compte


class _Match:
    def __init__(self, statut, score, neq="8813424544", secteur="7512"):
        self.entry = type("E", (), {"statut": statut, "neq": neq,
                                    "secteur_code": secteur})()
        self.score = score


# ---------------------------------------------------------------------------
# LES DEUX LIMITES, AVANT LA MESURE
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("statuts, attendu", [
    (["immatriculee", "radiee"], 0),
    (["immatriculee", "ni"], 1),
    (["ni", "ai", "radiee"], 2),
    # ⚠️ Un code inconnu compte aussi : il n'est ni l'un ni l'autre.
    (["zz", "immatriculee"], 1),
])
def test_ni_parmi_attrape_TOUT_ce_qui_n_est_ni_immatricule_ni_radie(statuts, attendu):
    assert len(outil.ni_parmi([_Match(s, 100.0) for s in statuts])) == attendu


def test_le_restant_MOINS_BIEN_SCORE_est_celui_des_Ruchers():
    """*L'exclusion garde 88,2 et écarte 95.*"""
    groupe = [_Match("ni", 95.0), _Match("immatriculee", 88.2)]
    seul = outil.moins_bien_score(groupe, 95.0, outil.GARDER_IMMATRICULEES)
    assert seul is not None and seul.score == 88.2


def test_une_EGALITE_au_sommet_n_est_PAS_un_restant_moins_bien_score():
    """⚠️ *Plusieurs candidats partagent la première place, et le restant en
    est un : le mécanisme n'a contredit aucun gagnant.*"""
    groupe = [_Match("immatriculee", 100.0), _Match("radiee", 100.0)]
    assert outil.moins_bien_score(groupe, 100.0, outil.GARDER_IMMATRICULEES) is None


def test_sans_restant_UNIQUE_la_question_ne_se_pose_pas():
    for statuts in (["immatriculee", "immatriculee"], ["radiee", "radiee"]):
        groupe = [_Match(s, 100.0) for s in statuts]
        assert outil.moins_bien_score(groupe, 100.0, outil.GARDER_IMMATRICULEES) is None


@pytest.mark.parametrize("neq, attendu", [
    ("8813424544", "88"), ("1143041938", "11"), (None, "(vide)"), ("", "(vide)"),
])
def test_le_prefixe_est_les_deux_premiers_chiffres(neq, attendu):
    assert outil.prefixe_du_neq(neq) == attendu


# ---------------------------------------------------------------------------
# LE REFUS DE CLASSER — la garde principale
# ---------------------------------------------------------------------------

def test_le_module_ne_porte_AUCUNE_heuristique_de_NOMS():
    """⚠️ **La garde principale.** *Une heuristique de noms produirait une
    classification qui aurait l'air d'une mesure.* **Le module ne compile aucune
    expression régulière, et n'importe pas `re`** — il n'a donc aucun moyen de
    reconnaître « Ville de » ou « CIUSSS »."""
    import ast
    from pathlib import Path

    source = Path(outil.__file__).read_text(encoding="utf-8")
    arbre = ast.parse(source)
    importe = {
        alias.name.split(".")[0]
        for n in ast.walk(arbre) if isinstance(n, (ast.Import, ast.ImportFrom))
        for alias in n.names
    } | {n.module.split(".")[0] for n in ast.walk(arbre)
         if isinstance(n, ast.ImportFrom) and n.module}
    assert "re" not in importe, "le module a de quoi reconnaître un NOM"


def test_les_decisions_ouvertes_qui_fourniraient_le_critere_sont_NOMMEES():
    numeros = {n for n, _t in outil.DECISIONS_OUVERTES}
    assert numeros == {"D27", "D28"}


def test_la_tentation_est_NOMMEE_pour_etre_refusee():
    """*Elle contient les mots mêmes des paires lues.*"""
    for mot in ("Ville de", "CIUSSS", "Commission scolaire"):
        assert mot in outil.LA_TENTATION, mot
    assert "devinée" in outil.LA_TENTATION


def test_les_prefixes_documentes_sont_ceux_du_GUIDE():
    assert outil.PREFIXES_DOCUMENTES == ("11", "22", "33")


# ---------------------------------------------------------------------------
# LA MESURE, DE BOUT EN BOUT
# ---------------------------------------------------------------------------

@pytest.fixture()
def decor(db_session, monkeypatch):
    """Un ambigu dont le `ni` est le mieux scoré, et un ambigu à égalité."""
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")

    #: (nom détecté, [(nom au registre, statut, neq)])
    dossiers = [
        # ⚠️ Le `ni` est à 100, l'immatriculée à 95 : l'exclusion stricte garde
        # un candidat MOINS BIEN SCORÉ. C'est le cas des Ruchers.
        ("Pecheries Alpha inc",
         [("Pecheries Alpha inc", "ni", "8813424544"),
          ("Pecheries Alpha", "immatriculee", "1143041938")]),
        # Égalité au sommet : le restant EST un des premiers.
        ("Pecheries Beta inc",
         [("Pecheries Beta inc", "immatriculee", "1143041939"),
          ("Pecheries Beta inc", "radiee", "1143041940")]),
    ]
    for i, (nom, au_registre) in enumerate(dossiers):
        company = Company(neq=None, nom_detecte=nom,
                          nom_detecte_normalise=normaliser(nom))
        db_session.add(company)
        db_session.flush()
        db_session.add(Signal(
            company_id=company.id, source_id="eimt",
            signal_type_id="recrutement_massif",
            detected_at=_dt.datetime(2026, 1, 1), champs={},
        ))
        for nom_req, statut, neq in au_registre:
            db_session.add(REQEntry(
                neq=neq, nom=nom_req, nom_normalise=normaliser(nom_req),
                statut=statut, ville=None, secteur_code="8511"))
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def _sortie(capsys):
    return capsys.readouterr().out


def test_le_refus_de_classer_vient_AVANT_les_chiffres(decor, capsys):
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    assert sortie.index("CLASSER UNE ENTITÉ") < sortie.index("AMBIGUS :")
    assert "donneurs_douvrage.py" in sortie
    assert "D27" in sortie and "D28" in sortie


def test_ce_que_le_produit_n_a_pas_est_rendu_comme_un_RESULTAT(decor, capsys):
    """⚠️ *« Si le produit n'a pas de quoi les reconnaître, le dire est le
    résultat. »*"""
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    assert "le dire EST le résultat" in sortie
    assert "RIEN. Et ce n'est pas une lacune découverte ici" in sortie


def test_les_ambigus_portant_un_ni_sont_comptes_avec_leur_POSITION(decor, capsys):
    """*Quand le non-immatriculé est le mieux scoré, l'exclusion écarte le
    candidat de tête.*"""
    assert outil.main(["--pas", "0"]) == 0
    bloc = _sortie(capsys).split("1. LES AMBIGUS QUI PORTENT")[1]
    porte = next(l for l in bloc.splitlines() if "au moins un tel candidat" in l)
    tete = next(l for l in bloc.splitlines() if "le MIEUX scoré du lot" in l)
    assert _compte(porte) == "1", porte
    assert _compte(tete) == "1", tete


def test_le_prefixe_hors_guide_est_MARQUE_et_dit_non_critere(decor, capsys):
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    assert "hors 11/22/33" in sortie
    assert "NI LE PRÉFIXE NI LE SECTEUR NE SONT UN CRITÈRE" in sortie


def test_le_croisement_du_miroir_est_dit_FAIT_et_non_critere(decor, capsys):
    assert outil.main(["--pas", "0"]) == 0
    bloc = _sortie(capsys).split("3. PRÉFIXE × STATUT")[1]
    assert "C'EST UN FAIT, PAS UN CRITÈRE" in bloc
    assert "elle ne se promeut pas en règle" in bloc


def test_le_restant_moins_bien_score_est_compte_pour_les_DEUX_exclusions(decor, capsys):
    assert outil.main(["--pas", "0"]) == 0
    bloc = _sortie(capsys).split("5. LE RESTANT MOINS BIEN SCORÉ")[1]
    stricte = next(l for l in bloc.splitlines()
                   if l.strip().startswith(outil.GARDER_IMMATRICULEES))
    assert _compte(stricte) == "1", stricte
    assert "deux instruments se contredisent" in bloc


def test_aucune_ecriture(decor, capsys):
    from falkye.resolution import SEUIL_AMBIGUITE_ECART_MIN, SEUIL_RESOLUTION_CONFIANTE

    avant = {c.id: c.neq for c in decor.query(Company).all()}
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    assert (f"seuil {SEUIL_RESOLUTION_CONFIANTE:.0f}, "
            f"écart {SEUIL_AMBIGUITE_ECART_MIN:.0f}") in sortie
    assert "AUCUNE ENTITÉ N'A ÉTÉ CLASSÉE" in sortie
    assert {c.id: c.neq for c in decor.query(Company).all()} == avant
