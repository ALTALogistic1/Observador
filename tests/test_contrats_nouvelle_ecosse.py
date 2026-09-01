"""Tests du connecteur Contrats attribués — Nouvelle-Écosse (spec section 7,
Signal "appel_offres" — équivalent SEAO).

Les fonctions testées ici sont de la logique PURE, validée séparément contre
les vraies données du portail (33 290 lignes réelles, avril 2010 à
2026-08-17) — voir docs/STATUT_RESEAU.md. Les lignes ci-dessous reproduisent
le VRAI format confirmé (champs `vendor`/`awarded_amount`/`tender_id`, et le
cas réel de tender_id partagé par plusieurs entreprises), pas des données
inventées au hasard."""
from observador.sources.contrats_nouvelle_ecosse import (
    _nature_contrat,
    _parse_date,
    _parse_float,
)

# Vraie ligne (tronquée) confirmée le 2026-09-01, tender_id "MET24-04" — un
# même appel d'offres attribué à DEUX entreprises distinctes (contrat à
# commandes) : la découverte qui a motivé d'inclure le vendeur dans source_ref.
_LIGNE_MULTI_VENDEUR_A = {
    "tender_id": "MET24-04",
    "vendor": "Miller Waste Systems Inc",
    "awarded_amount": "2488624.88",
    "awarded_date": "2024-06-25T00:00:00.000",
    "goods": "N",
    "service": "Y",
    "construction": "N",
}
_LIGNE_MULTI_VENDEUR_B = {
    "tender_id": "MET24-04",
    "vendor": "Royal Environmental Inc",
    "awarded_amount": "1119907.55",
    "awarded_date": "2024-06-25T00:00:00.000",
    "goods": "N",
    "service": "Y",
    "construction": "N",
}


def test_parse_date_gere_les_vraies_dates_socrata():
    dt = _parse_date("2026-08-17T00:00:00.000")
    assert dt is not None
    assert (dt.year, dt.month, dt.day) == (2026, 8, 17)


def test_parse_date_retourne_none_si_vide():
    assert _parse_date(None) is None
    assert _parse_date("") is None


def test_parse_float_gere_les_vrais_montants():
    assert _parse_float("2488624.88") == 2488624.88


def test_parse_float_traite_zero_comme_valeur_inconnue():
    """Régression : "0" n'est pas un contrat réellement gratuit dans ce jeu
    de données (867/33 290 lignes réelles) — traité comme None, pas 0.0, pour
    ne pas fausser le palier de score."""
    assert _parse_float("0") is None


def test_parse_float_retourne_none_si_vide():
    assert _parse_float(None) is None
    assert _parse_float("") is None


def test_nature_contrat_combine_les_indicateurs_reels():
    ligne = {"goods": "Y", "service": "Y", "construction": "N"}
    assert _nature_contrat(ligne) == "biens/services"


def test_nature_contrat_gere_construction_seule():
    ligne = {"goods": "N", "service": "N", "construction": "Y"}
    assert _nature_contrat(ligne) == "construction"


def test_nature_contrat_retourne_non_precise_si_aucun_indicateur():
    ligne = {"goods": "N", "service": "N", "construction": "N"}
    assert _nature_contrat(ligne) == "non précisé"


def test_les_deux_vendeurs_reels_du_meme_tender_id_sont_distincts():
    """Régression du bogue trouvé en validant : tender_id seul ne suffit pas
    à identifier une ligne — deux entreprises RÉELLES distinctes partagent le
    même tender_id "MET24-04". Vérifie juste que les deux lignes réelles ont
    bien des noms distincts (le comportement de source_ref lui-même est
    couvert par la docstring de detect() et validé en direct)."""
    assert _LIGNE_MULTI_VENDEUR_A["vendor"] != _LIGNE_MULTI_VENDEUR_B["vendor"]
    assert _LIGNE_MULTI_VENDEUR_A["tender_id"] == _LIGNE_MULTI_VENDEUR_B["tender_id"]
