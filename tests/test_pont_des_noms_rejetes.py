"""Le pont des noms rejetés — fonctions pures, sans archive ni base."""
from collections import Counter

from falkye.sources.column_mapping import normaliser
from outils.pont_des_noms_rejetes import classer_appariement, part, statut_du_nom


def test_un_appariement_au_nom_ELU_nest_pas_un_gain_du_pont():
    """Elle se résoudrait déjà : son échec a une autre cause, et la compter
    gonflerait le chiffre du pont."""
    classe = classer_appariement(
        "Construction Pierre Robert inc.", "CONSTRUCTION PIERRE ROBERT INC.", normaliser
    )
    assert classe == "apparié au nom ÉLU — le pont n'y changerait rien"


def test_un_appariement_a_un_nom_JETE_est_le_pont():
    classe = classer_appariement(
        "Construction Pierre Robert inc.",
        "Pierre Robert - Entrepreneur Général inc.",
        normaliser,
    )
    assert classe == "apparié à un nom JETÉ par le chargeur — LE PONT"


def test_un_NEQ_sans_nom_elu_nest_PAS_au_miroir():
    """96,6 % des NEQ sans nom élu sont des personnes physiques : le Registraire
    ne publie pas leur nom, et aucun pont n'y changera rien."""
    classe = classer_appariement(None, "Ferme Dallaire Frères SENC", normaliser)
    assert classe == "aucun nom élu — l'entreprise n'est PAS au miroir"


def test_la_comparaison_passe_par_la_normalisation_des_DEUX_cotes():
    """Accents et casse ne doivent pas faire passer un nom élu pour un nom jeté."""
    assert classer_appariement("9309-3927 QUÉBEC INC.", "9309-3927 Quebec inc", normaliser) \
        == "apparié au nom ÉLU — le pont n'y changerait rien"


def test_le_statut_du_nom_se_lit_en_clair():
    assert statut_du_nom("V", "M") == "en vigueur, dénomination sociale"
    assert statut_du_nom("V", "N") == "en vigueur, nom"


def test_un_statut_inconnu_est_rendu_TEL_QUEL_jamais_deviné():
    assert statut_du_nom("A", "X") == "statut A, type X"
    assert statut_du_nom("", "") == "statut (vide), type (vide)"


def test_une_part_sur_un_compteur_vide_ne_divise_pas_par_zero():
    assert part(Counter(), "x") == 0.0
    assert part(Counter({"a": 1, "b": 3}), "b") == 75.0
