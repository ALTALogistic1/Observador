"""L'état du champ normalisé — fonctions pures, sans base."""
from collections import Counter

from outils.etat_champ_normalise import classer_ecart, resume_longueurs, verdict


def test_une_valeur_conforme_est_reconnue():
    assert classer_ecart("Plomberie Tremblay inc.", "plomberie tremblay inc",
                         "plomberie tremblay inc") == "conforme"


def test_une_valeur_absente_et_une_valeur_vide_ne_sont_pas_la_meme_chose():
    """NULL et '' appellent des lectures différentes : une colonne non nullable
    qui porte NULL dit que la table n'a pas été créée par ce modèle."""
    assert classer_ecart("X inc", None, "x inc") == "ABSENT (NULL)"
    assert classer_ecart("X inc", "", "x inc") == "VIDE ('')"


def test_le_cas_reel_est_classe_comme_tronque_en_queue():
    """`9309-3927 QUÉBEC INC.` stocké sans `inc` — quatre caractères sur vingt,
    et le score tombe à 66."""
    cl = classer_ecart("9309-3927 QUÉBEC INC.", "9309 3927 quebec", "9309 3927 quebec inc")
    assert cl == "TRONQUÉ en queue (manque 'inc')"


def test_un_nom_source_vide_est_distingue_dune_normalisation_ratee():
    """La distinction décide de la réparation : un nom source vide ne se
    recalcule pas, il se réimporte."""
    assert classer_ecart("   ", "", "") == "nom source VIDE — rien à normaliser"


def test_une_valeur_sans_rapport_est_declaree_divergente():
    assert classer_ecart("Ferme Dallaire", "toitures gagnon", "ferme dallaire") \
        == "DIVERGENT (ni préfixe ni suffixe)"


def test_la_tranche_1_4_est_nommee_par_sa_signature():
    """Une cible de 1 à 4 caractères contre une requête de 20 produit un score
    de 60 à 68 — c'est la signature mesurée du 66, et elle doit se compter."""
    tranches = dict(resume_longueurs([0, 2, 3, 4, 12, 30, 80]))
    assert tranches["0 (vide)"] == 1
    assert tranches["1-4  ⚠️ signature du score 60-68"] == 3
    assert tranches["11-20"] == 1
    assert tranches["21-40"] == 1
    assert tranches["41+"] == 1


def test_une_tranche_vide_ne_sort_pas(  ):
    """Un zéro écrit à la place d'une absence ferait lire « mesuré à zéro »."""
    assert [k for k, _ in resume_longueurs([12, 12])] == ["11-20"]


def test_un_nom_source_exploitable_designe_le_recalcul():
    v = "\n".join(verdict(Counter({"VIDE ('')": 900, "conforme": 100})))
    assert "RECALCUL SUR PLACE" in v
    assert "RÉIMPORT" not in v


def test_un_nom_source_vide_en_masse_designe_le_reimport():
    v = "\n".join(verdict(Counter({"nom source VIDE — rien à normaliser": 900, "conforme": 100})))
    assert "RÉIMPORT" in v


def test_tout_conforme_ne_designe_aucune_reparation():
    v = "\n".join(verdict(Counter({"conforme": 1000})))
    assert "CONFORMES" in v
    assert "RECALCUL" not in v and "RÉIMPORT" not in v


def test_aucune_ligne_examinee_ne_rend_pas_un_verdict_vide():
    """L'absence de mesure n'est pas une mesure nulle."""
    assert "Aucune ligne examinée" in "\n".join(verdict(Counter()))
