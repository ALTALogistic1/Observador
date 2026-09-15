"""Les témoins de résolution — le classement, sans base."""
from outils.temoins_resolution import classer

AVANT = {"id": 1, "nom_detecte": "Gagnon inc.", "neq": "1111111111"}


def test_le_meme_NEQ_est_inchange():
    assert classer(AVANT, "1111111111", existe=True) == "inchangée"


def test_aucun_NEQ_est_une_DERESOLUTION_acceptable():
    """Visible et réversible : l'entreprise redevient candidate, rien de faux
    n'est présenté."""
    assert classer(AVANT, None, existe=True) == "DÉRÉSOLUE — visible et réversible"


def test_un_AUTRE_NEQ_est_le_cas_GRAVE():
    """Une entreprise qui bascule vers une mauvaise réponse est pire qu'une qui
    bascule vers l'ambigu : la seconde se voit, la première se présente comme
    un fait."""
    assert classer(AVANT, "2222222222", existe=True) == \
        "MAL RÉSOLUE — le dossier change d'identité"


def test_une_entreprise_disparue_nest_ni_deresolue_ni_mal_resolue():
    """Fusionnée par la déduplication — un cas distinct, à examiner à part."""
    assert classer(AVANT, None, existe=False) == "l'entreprise n'existe plus — fusionnée"
    assert classer(AVANT, "2222222222", existe=False) == \
        "l'entreprise n'existe plus — fusionnée"
