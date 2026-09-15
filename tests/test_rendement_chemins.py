"""Ce que chaque chemin de résolution RAPPORTE, en face de ce qu'il coûte.

Le coût seul ne tranche pas D14 : le repli par sous-chaîne prend 98 % du budget
pour 14 % des appels, et s'il résout ce que les deux autres ne trouvent pas, il
vaut son prix."""
from falkye.cout_lectures import (
    CHEMIN_EXACT,
    CHEMIN_PREFIXE,
    CHEMIN_SOUS_CHAINE,
    ComptesResolution,
    compter,
    compter_abouti,
    comptes_courants,
    ouvrir_comptes,
)


def test_un_chemin_emprunte_sans_aboutir_compte_zero_reussite():
    c = ComptesResolution()
    c.compter(CHEMIN_SOUS_CHAINE)
    c.compter(CHEMIN_SOUS_CHAINE)
    assert c.appels[CHEMIN_SOUS_CHAINE] == 2
    assert c.abouties[CHEMIN_SOUS_CHAINE] == 0
    assert c.rendement(CHEMIN_SOUS_CHAINE) == 0.0


def test_un_chemin_jamais_emprunte_na_PAS_un_rendement_de_zero():
    """L'absence de mesure n'est pas une mesure nulle : écrit `0`, un chemin
    jamais emprunté se lirait « n'a rien résolu »."""
    assert ComptesResolution().rendement(CHEMIN_PREFIXE) is None


def test_le_rendement_est_une_part_des_appels_de_CE_chemin():
    c = ComptesResolution()
    for _ in range(4):
        c.compter(CHEMIN_PREFIXE)
    c.compter_abouti(CHEMIN_PREFIXE)
    assert c.rendement(CHEMIN_PREFIXE) == 25.0
    # Et il ne se dilue pas dans les autres chemins.
    c.compter(CHEMIN_EXACT)
    assert c.rendement(CHEMIN_PREFIXE) == 25.0


def test_les_aboutissements_ne_depassent_jamais_les_appels_dans_le_moteur():
    """Un taux au-dessus de 100 % passerait pour un arrondi au lieu d'un défaut."""
    with ouvrir_comptes() as c:
        compter(CHEMIN_EXACT)
        compter_abouti(CHEMIN_EXACT)
        compter(CHEMIN_EXACT)
        assert all(c.abouties[ch] <= c.appels[ch] for ch in c.appels)
        assert c.total == 2 and c.total_abouti == 1


def test_compter_abouti_est_silencieux_hors_execution():
    """Un appel depuis un outil ou la ligne de commande ne doit ni lever ni
    s'inventer un compteur — même règle que `compter`."""
    assert comptes_courants() is None
    compter_abouti(CHEMIN_SOUS_CHAINE)  # ne lève pas


def test_un_compteur_neuf_ne_recupere_pas_les_aboutissements_du_precedent():
    with ouvrir_comptes() as externe:
        compter_abouti(CHEMIN_EXACT)
        with ouvrir_comptes() as interne:
            compter_abouti(CHEMIN_EXACT)
            assert interne.total_abouti == 1
        assert externe.total_abouti == 1
