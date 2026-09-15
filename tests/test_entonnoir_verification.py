"""L'entonnoir de vérification — fonctions pures."""
from collections import Counter

from outils.entonnoir_verification import barre, part


def test_une_barre_sur_un_total_nul_est_VIDE():
    """Pas une barre pleine, pas un caractère : rien, parce qu'il n'y a rien à
    représenter."""
    assert barre(0, 0) == ""
    assert barre(5, 0) == ""


def test_une_valeur_nulle_ne_dessine_rien():
    assert barre(0, 100) == ""


def test_une_valeur_minuscule_dessine_au_moins_un_caractere():
    """92 sur 11 556 ferait zéro caractère par arrondi — et se lirait comme un
    zéro alors que ce n'est pas zéro."""
    assert barre(92, 11556) == "█"


def test_une_barre_pleine_occupe_toute_la_largeur():
    assert barre(100, 100, largeur=10) == "█" * 10


def test_une_part_sur_un_compteur_vide_ne_divise_pas_par_zero():
    assert part(Counter(), "x") == 0.0
    assert part(Counter({"a": 1, "b": 1}), "a") == 50.0
