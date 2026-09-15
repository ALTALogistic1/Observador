"""L'impact de « garder tous les noms » — fonctions pures."""
from outils.impact_tous_les_noms import (
    LIGNES_DE_REFERENCE,
    MINUTES_DE_REFERENCE,
    OCTETS_PAR_LIGNE,
    estimer_duree,
)


def test_la_duree_est_une_FOURCHETTE_jamais_un_nombre():
    """L'écriture en masse est plus rapide que l'upsert de référence, et de
    combien n'a pas été mesuré. Un nombre serait une promesse."""
    basse, haute = estimer_duree(LIGNES_DE_REFERENCE)
    assert basse < haute
    assert haute == MINUTES_DE_REFERENCE


def test_la_borne_haute_suppose_le_meme_prix_par_ligne():
    _basse, haute = estimer_duree(LIGNES_DE_REFERENCE * 2)
    assert haute == MINUTES_DE_REFERENCE * 2


def test_zero_ligne_ne_coute_rien():
    assert estimer_duree(0) == (0.0, 0.0)


def test_lestimation_doctets_est_un_ordre_de_grandeur_declare():
    """Un chiffre recopié est une promesse que personne ne tient — celui-ci est
    annoncé comme un ordre de grandeur dans la sortie."""
    assert 50 < OCTETS_PAR_LIGNE < 500
