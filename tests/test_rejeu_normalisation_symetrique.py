"""Le rejeu de la normalisation symétrique — fonctions pures, sans base."""
from outils.rejeu_normalisation_symetrique import (
    classer_rejeu,
    normaliser_symetrique,
    porte_une_forme_juridique,
)


def test_la_forme_juridique_finale_est_retiree():
    assert normaliser_symetrique("9309 3927 quebec inc") == "9309 3927 quebec"
    assert normaliser_symetrique("ferme dallaire freres senc") == "ferme dallaire freres"


def test_plusieurs_formes_empilees_sont_toutes_retirees():
    assert normaliser_symetrique("gestion tremblay inc ltee") == "gestion tremblay"


def test_une_forme_juridique_au_MILIEU_reste():
    """« Les Entreprises Ltée Gagnon » : retirer un mot au milieu changerait le
    nom, pas sa graphie."""
    assert normaliser_symetrique("les entreprises ltee gagnon") == "les entreprises ltee gagnon"


def test_un_nom_reduit_a_rien_est_rendu_INCHANGE():
    """Une chaîne vide s'apparierait avec n'importe quoi — c'est exactement le
    défaut qu'on vient de traquer trois jours."""
    assert normaliser_symetrique("inc") == "inc"
    assert normaliser_symetrique("") == ""


def test_un_nom_sans_forme_juridique_ne_bouge_pas():
    assert normaliser_symetrique("patates orleans") == "patates orleans"


def test_la_detection_de_forme_juridique_exige_un_AUTRE_mot():
    assert porte_une_forme_juridique("9309 3927 quebec inc")
    assert not porte_une_forme_juridique("inc")
    assert not porte_une_forme_juridique("patates orleans")


def test_le_gain_est_compte_seulement_si_lecart_au_second_tient():
    """Franchir 92 ne suffit pas : le moteur refuse un candidat trop proche du
    suivant, et retirer la forme juridique rapproche les homonymes."""
    assert classer_rejeu(66.0, 100.0, 12.0, 92.0, 8.0) == "RÉSOLU par la symétrie"
    assert classer_rejeu(66.0, 100.0, 3.0, 92.0, 8.0) == \
        "franchit 92 mais devient AMBIGU — pas un gain"


def test_une_entreprise_deja_resolue_nest_pas_comptee_comme_un_gain():
    assert classer_rejeu(95.0, 97.0, 20.0, 92.0, 8.0) == "déjà résolu avant"


def test_une_perte_est_nommee_comme_telle():
    assert classer_rejeu(95.0, 80.0, 20.0, 92.0, 8.0) == "PERDU par la symétrie"


def test_ce_qui_reste_sous_le_seuil_est_dit_tel_quel():
    assert classer_rejeu(41.0, 55.0, 20.0, 92.0, 8.0) == "toujours sous le seuil"
