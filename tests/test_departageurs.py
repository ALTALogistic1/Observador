"""Trois faits qui séparent deux candidats — et la règle qui les encadre.

⚠️ **La règle est plus stricte qu'il n'y paraît** : *« je ne sais pas » n'est pas
« non »*. Un fait absent chez un concurrent ne l'exclut pas — sans quoi le
départageur deviendrait un filtre sur le remplissage du registre.
"""
from __future__ import annotations

import pytest

from outils.departageurs import (
    AUCUN_COMPATIBLE,
    DEPARTAGE,
    PLUSIEURS_COMPATIBLES,
    SANS_FAIT_AU_DOSSIER,
    SANS_FAIT_CHEZ_UN_CONCURRENT,
    codes_postaux,
    departager,
    fait_de_lactivite,
    fait_de_la_ville,
)


# --- le code postal --------------------------------------------------------


def test_un_code_TRONQUE_rend_sa_region_de_tri():
    """⚠️ *L'EIMT écrit `'St-Isidore, QC J0L  2A'` — cinq caractères sur six.*
    **Comparer un tronqué à un complet sur six rendrait toujours faux**, et le
    départageur paraîtrait inutile alors qu'il est mal lu."""
    assert codes_postaux("St-Isidore, QC J0L  2A").formes == frozenset({"J0L"})


def test_un_code_COMPLET_rend_les_deux_niveaux():
    formes = codes_postaux("200 rue des Commandeurs, Lévis, QC G6V 1A1").formes
    assert formes == frozenset({"G6V", "G6V1A1"})


def test_un_tronque_et_un_complet_de_la_MEME_region_concordent():
    assert codes_postaux("QC J0L 2A").compatible_avec(codes_postaux("J0L 1M0"))


def test_la_lecture_se_fait_par_JETONS_jamais_par_fenetre_glissante():
    """⚠️ **Le faux code, éliminé par conception.** *`STISIDOREQCJ0L2A` contient
    `L2A`, qui a la forme d'une région de tri et n'en est pas une* — et un faux
    code rend un mauvais candidat « compatible », donc produit un FAUX
    DÉPARTAGE. C'est le seul coût que ce départageur puisse avoir."""
    formes = codes_postaux("St-Isidore, QC J0L  2A").formes
    assert "L2A" not in formes, formes
    formes = codes_postaux("Lévis, QC G6V 1A1").formes
    assert "V1A" not in formes, formes


def test_un_texte_sans_code_postal_ne_rend_RIEN():
    assert codes_postaux("123 rue Principale") is None
    assert codes_postaux("") is None
    assert codes_postaux(None) is None


# --- l'activité ------------------------------------------------------------


def test_les_mots_VIDES_dune_activite_sont_retires():
    """*Les garder ferait « concorder » une boulangerie et une plomberie sur
    « autres services ».*"""
    assert fait_de_lactivite("Autres services de plomberie et chauffage").formes == (
        frozenset({"plomberie", "chauffage"})
    )
    assert fait_de_lactivite("Autres services généraux non classés ailleurs") is None


def test_deux_activites_differentes_ne_concordent_pas():
    """*Deux « Gérard et Fils », l'une en pavage et l'autre en plomberie.*"""
    pavage = fait_de_lactivite("Travaux de pavage et revêtement")
    plomberie = fait_de_lactivite("Entrepreneurs en plomberie")
    assert not pavage.compatible_avec(plomberie)


# --- la ville --------------------------------------------------------------


def test_la_ville_ne_NORMALISE_PAS_les_municipalites():
    """⚠️ *`St-Isidore` et `Saint-Isidore` ne sont pas la même forme ici* — la
    normalisation des municipalités est un chantier à part, et l'inventer ferait
    passer pour un départage ce qui est une graphie."""
    assert not fait_de_la_ville("St-Isidore").compatible_avec(
        fait_de_la_ville("Saint-Isidore")
    )
    assert fait_de_la_ville("LÉVIS").compatible_avec(fait_de_la_ville("lévis"))


# --- LA RÈGLE --------------------------------------------------------------


def test_un_seul_concurrent_compatible_DEPARTAGE():
    issue, gagnant = departager(
        fait_de_la_ville("Lévis"),
        [fait_de_la_ville("Laval"), fait_de_la_ville("Lévis")],
    )
    assert (issue, gagnant) == (DEPARTAGE, 1)


def test_un_fait_ABSENT_chez_un_concurrent_ne_lexclut_PAS():
    """⚠️ **La règle qui distingue un départageur d'un filtre.** *Sans elle, un
    candidat sans code postal serait écarté pour n'avoir pas de code postal.*"""
    issue, gagnant = departager(
        fait_de_la_ville("Lévis"), [None, fait_de_la_ville("Lévis")]
    )
    assert issue == SANS_FAIT_CHEZ_UN_CONCURRENT
    assert gagnant is None


def test_un_dossier_sans_fait_ne_departage_rien():
    issue, _ = departager(None, [fait_de_la_ville("Lévis")])
    assert issue == SANS_FAIT_AU_DOSSIER


def test_deux_concurrents_dans_la_MEME_ville_ne_se_departagent_pas():
    """*469 ambigus avaient des concurrents dans la même ville.*"""
    issue, _ = departager(
        fait_de_la_ville("Laval"),
        [fait_de_la_ville("Laval"), fait_de_la_ville("Laval")],
    )
    assert issue == PLUSIEURS_COMPATIBLES


def test_un_fait_qui_exclut_TOUT_LE_MONDE_est_un_signal_pas_un_departage():
    """*Soit le bon candidat n'est pas dans le lot, soit le fait est sale.*
    **Aucun départage n'est prononcé.**"""
    issue, gagnant = departager(
        fait_de_la_ville("Gaspé"),
        [fait_de_la_ville("Laval"), fait_de_la_ville("Lévis")],
    )
    assert (issue, gagnant) == (AUCUN_COMPATIBLE, None)
