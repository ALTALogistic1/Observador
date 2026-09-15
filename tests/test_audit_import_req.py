"""L'audit de l'import REQ — fonctions pures, sans archive ni base."""
from outils.audit_import_req import profil_de_coupure, serie_du_nom


def test_une_denomination_numerique_rend_sa_serie():
    assert serie_du_nom("9309-3927 QUÉBEC INC.") == "9309"
    assert serie_du_nom("9309-1319 QUÉBEC INC.") == "9309"


def test_la_serie_est_celle_du_NOM_pas_celle_du_NEQ():
    """Le NEQ est un nombre à dix chiffres sans rapport avec la série."""
    assert serie_du_nom("1170123456") is None


def test_un_nom_ordinaire_na_pas_de_serie():
    assert serie_du_nom("Plomberie Tremblay inc.") is None
    assert serie_du_nom("") is None
    assert serie_du_nom(None) is None


def test_les_espaces_de_tete_ne_cachent_pas_la_serie():
    assert serie_du_nom("  9309-3927 QUÉBEC INC.") == "9309"


def test_une_forme_approchante_nest_pas_une_serie():
    """Trois chiffres, ou pas de tiret : ce n'est pas une dénomination
    numérique du Registraire."""
    assert serie_du_nom("930-3927 QUEBEC INC") is None
    assert serie_du_nom("93093927 QUEBEC INC") is None


def test_le_profil_dun_ensemble_vide_ne_ment_pas():
    """L'absence de mesure n'est pas une mesure nulle : pas de min ni de max
    inventés."""
    assert profil_de_coupure(set()) == {"n": 0, "min": None, "max": None}


def test_le_profil_rend_les_bornes_reelles():
    profil = profil_de_coupure({"1170000005", "1170000001", "1170000009"})
    assert profil == {"n": 3, "min": "1170000001", "max": "1170000009"}
