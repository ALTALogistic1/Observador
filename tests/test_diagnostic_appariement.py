"""Le diagnostic d'appariement — les fonctions pures, sans base."""
from outils.diagnostic_appariement import (
    formes_du_nom,
    classer_difference,
    est_numero,
    mots_significatifs,
)


def test_les_formes_juridiques_ne_sont_pas_significatives():
    assert mots_significatifs("plomberie tremblay inc") == ["plomberie", "tremblay"]
    assert mots_significatifs("toitures gagnon ltee") == ["toitures", "gagnon"]


def test_les_mots_de_tete_vides_ne_sont_pas_significatifs():
    """« construction » distingue mal dans un registre d'entrepreneurs."""
    assert mots_significatifs("les constructions bergeron inc") == ["bergeron"]


def test_une_denomination_numerique_est_reconnue():
    assert est_numero("9231 4567 quebec inc")
    assert not est_numero("plomberie tremblay inc")


def test_un_nom_a_un_seul_chiffre_nest_pas_une_denomination_numerique():
    assert not est_numero("2 freres toiture")


def test_la_denomination_numerique_prime_sur_les_autres_motifs():
    motif = classer_difference("9231 4567 quebec inc", ["quebec construction"])
    assert "numérique" in motif


def test_une_tete_non_significative_est_nommee_comme_telle():
    motif = classer_difference("les constructions bergeron", ["constructions bergeron"])
    assert "tête non significative" in motif


def test_aucun_voisin_veut_dire_absent_du_registre():
    motif = classer_difference("zzyx toiture", [])
    assert "absent du registre" in motif


def test_les_mots_presents_mais_pas_en_tete_sont_distingues():
    """Le cas qui compte : le registre PORTE le nom, la récupération ne le voit pas."""
    motif = classer_difference("toiture bergeron", ["entreprises bergeron toiture enr"])
    assert "PAS EN TÊTE" in motif


def test_un_voisin_aux_mots_distincts_suggere_une_enseigne():
    motif = classer_difference("toiture bergeron", ["bergeron transport"])
    assert "enseigne" in motif


def test_les_formes_dun_nom_ne_sexcluent_pas():
    """« 9164-4187 Quebec Inc » est à la fois numérique et porteur d'une forme juridique."""
    formes = formes_du_nom("9164-4187 Quebec Inc")
    assert "dénomination numérique" in formes
    assert "forme juridique en fin" in formes


def test_une_abreviation_pointee_est_relevee():
    assert "abréviation pointée" in formes_du_nom("F.M. Resto Design inc.")


def test_les_accents_sont_releves_sur_le_nom_BRUT():
    """La normalisation les retire — la forme se lit avant elle."""
    assert "accents" in formes_du_nom("Agropur coopérative")
    assert "accents" not in formes_du_nom("Agropur cooperative")


def test_un_nom_tout_en_majuscules_est_releve():
    assert "tout en MAJUSCULES" in formes_du_nom("LE POTAGER GRANDMONT")


def test_un_nom_dun_seul_mot_est_releve():
    assert "un seul mot" in formes_du_nom("agileDSS")


def test_un_nom_sans_particularite_le_dit():
    assert formes_du_nom("Patates Orleans") == {"(aucune forme relevée)"}
