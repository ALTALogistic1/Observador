"""Tests du connecteur Globe and Mail Top Growing Companies (spec section 7,
Signal 1).

Les fonctions testées ici sont de la logique PURE, validée séparément contre
le vrai classement 2025 (400 entreprises réelles, dont des entreprises
québécoises confirmées — ex. Boreas Technologies, NUAGE Logistics) — voir
docs/STATUT_RESEAU.md. Les fragments ci-dessous reproduisent le VRAI format
confirmé (page-hub avec plusieurs années + variante "-provincial", bloc
`Fusion.globalContent=`, `const sheetID = "..."`), pas des données inventées
au hasard."""
from falkye.sources.rob_top_growing import (
    _RE_LIEN_ANNEE,
    _RE_SHEET_ID,
    _extraire_bloc_json,
    _parse_float,
    _parse_int,
    _parse_ville_region,
)

_FRAGMENT_HUB = (
    '<a href="/business/rob-magazine/top-growing-companies/'
    'article-ranking-canadas-top-growing-companies-of-2024/">2024</a>\n'
    '<a href="/business/rob-magazine/top-growing-companies/'
    'article-ranking-canadas-top-growing-companies-of-2025-provincial/">Provincial</a>\n'
    '<a href="/business/rob-magazine/top-growing-companies/'
    'article-ranking-canadas-top-growing-companies-of-2025/">2025</a>\n'
)

_FRAGMENT_SHEET_ID = (
    '<script>\n'
    '  const sheetID = "1gUvaUbvUd0fDet79lyoZ3hvMlwJsI3L58V9w6LpBEIc"; // Google Sheet ID\n'
    '</script>'
)


def test_re_lien_annee_ignore_la_variante_provinciale_et_trouve_les_deux_annees():
    """La page-hub réelle garde le lien de l'année précédente ET la variante
    "-provincial" du classement en cours — le motif ne doit matcher ni l'une
    ni l'autre comme "2025" à tort (elles ont un chemin distinct)."""
    candidats = _RE_LIEN_ANNEE.findall(_FRAGMENT_HUB)
    annees = sorted(int(a) for _, a in candidats)
    assert annees == [2024, 2025]
    # le chemin associé à 2025 ne contient pas "-provincial"
    chemin_2025 = next(c for c, a in candidats if a == "2025")
    assert "provincial" not in chemin_2025


def test_re_sheet_id_trouve_le_vrai_identifiant():
    m = _RE_SHEET_ID.search(_FRAGMENT_SHEET_ID)
    assert m is not None
    assert m.group(1) == "1gUvaUbvUd0fDet79lyoZ3hvMlwJsI3L58V9w6LpBEIc"


def test_extraire_bloc_json_gere_les_accolades_imbriquees_dans_les_chaines():
    """Régression du piège qui casserait un simple regex non-gourmand : une
    valeur de chaîne contenant elle-même des accolades (ex. un blob CSS/JS
    imbriqué, comme dans le vrai contenu de cette page)."""
    html = (
        'window.x=1;Fusion.globalContent={"a":1,"style":"body{margin:0}",'
        '"nested":{"b":2}};window.y=2;'
    )
    resultat = _extraire_bloc_json(html, "Fusion.globalContent=")
    assert resultat == {"a": 1, "style": "body{margin:0}", "nested": {"b": 2}}


def test_extraire_bloc_json_retourne_none_si_marqueur_absent():
    assert _extraire_bloc_json("<html></html>", "Fusion.globalContent=") is None


def test_parse_ville_region_separe_ville_et_province():
    assert _parse_ville_region("Longueuil, Que.") == ("Longueuil", "Que.")
    assert _parse_ville_region("Bromont, Que.") == ("Bromont", "Que.")


def test_parse_ville_region_laisse_la_region_absente_pour_une_grande_ville_seule():
    """Les grandes villes ("Montreal", "Toronto"...) sont données sans
    suffixe de province dans le vrai fichier — pas une donnée manquante à
    deviner, juste une région non fournie ici (résolue via le REQ)."""
    assert _parse_ville_region("Montreal") == ("Montreal", None)


def test_parse_ville_region_gere_l_absence():
    assert _parse_ville_region(None) == (None, None)
    assert _parse_ville_region("") == (None, None)


def test_parse_float_gere_les_vrais_taux_de_croissance():
    assert _parse_float("20064") == 20064.0
    assert _parse_float(None) is None
    assert _parse_float("") is None


def test_parse_int_gere_les_vrais_rangs():
    assert _parse_int("1") == 1
    assert _parse_int(None) is None
