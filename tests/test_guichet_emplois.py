"""Tests du connecteur Guichet-Emplois (spec section 7, Signal 3).

`_extraire_employeur` est de la logique PURE (parsing HTML), validée séparément
contre une vraie page de détail d'offre (offre 50196187, capturée le
2026-09-01) — voir docs/STATUT_RESEAU.md. Le fragment ci-dessous reproduit la
VRAIE structure confirmée (`job-posting-details-employer-wrapper` > `h2` pour
le nom, premier `<li><span class="details">` pour le secteur), pas une
structure inventée."""
from falkye.sources.guichet_emplois import (
    COLUMN_ALIASES,
    URL_OFFRE_TEMPLATE,
    _extraire_employeur,
    _parse_date,
    _parse_int,
)
from falkye.sources.column_mapping import resolve_columns

_FRAGMENT_REEL = """
<div class="job-posting-details-employer-wrapper">
  <h2>KAVURU'S INDIAN BISTRO</h2>
  <ul>
    <li><span class="details">Restauration</span></li>
    <li><span class="details">1-4 employés</span></li>
  </ul>
</div>
"""

# Vraies en-têtes (extrait) du fichier CSV téléchargé le 2026-09-01 — 65
# colonnes au total, ici seulement celles utilisées par COLUMN_ALIASES.
_EN_TETES_REELLES = [
    "ID WIC Lieu emploi",
    "Appellation d'emploi",
    "Code CNP 2021",
    "Nombre de postes vacants",
    "Détail rémunération",
    "Ville",
    "Provinces/Territoires",
    "Date initiale affichage de l'offre d'emploi",
]


def test_extraire_employeur_lit_le_nom_et_le_secteur():
    resultat = _extraire_employeur(_FRAGMENT_REEL)
    assert resultat == {"nom": "KAVURU'S INDIAN BISTRO", "secteur": "Restauration"}


def test_extraire_employeur_retourne_none_si_le_bloc_est_absent():
    """Page d'erreur / offre retirée : pas de bloc employeur, pas de nom à
    deviner."""
    assert _extraire_employeur("<html><body>Not Found</body></html>") is None


def test_extraire_employeur_retourne_none_si_h2_vide():
    html = '<div class="job-posting-details-employer-wrapper"><h2></h2></div>'
    assert _extraire_employeur(html) is None


def test_url_offre_template_correspond_au_vrai_format():
    assert URL_OFFRE_TEMPLATE.format(id="50196187") == (
        "https://www.guichetemplois.gc.ca/jobsearch/jobposting/50196187"
    )


def test_column_aliases_resolvent_contre_les_vraies_en_tetes():
    """Régression du bogue d'encodage/délimiteur du 2026-08-31 : vérifie que
    les alias correspondent aux vraies en-têtes normalisées du fichier réel,
    pas à une supposition."""
    colonnes = resolve_columns(_EN_TETES_REELLES, COLUMN_ALIASES)
    assert colonnes["id_offre"] == "ID WIC Lieu emploi"
    assert colonnes["titre_poste"] == "Appellation d'emploi"
    assert colonnes["province"] == "Provinces/Territoires"
    assert colonnes["date_publication"] == "Date initiale affichage de l'offre d'emploi"
    assert "employeur" not in colonnes  # confirmé absent du fichier réel — voir docstring du module


def test_parse_date_gere_les_dates_reelles():
    dt = _parse_date("2026-07-15")
    assert dt is not None
    assert dt.year == 2026 and dt.month == 7 and dt.day == 15


def test_parse_date_retourne_none_si_vide():
    assert _parse_date(None) is None
    assert _parse_date("") is None


def test_parse_int_gere_les_nombres_avec_virgule():
    assert _parse_int("1,234") == 1234
    assert _parse_int(None) is None
