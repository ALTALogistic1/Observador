"""Tests du connecteur Deloitte Technology Fast 50 (spec section 7, Signal 1).

Les fonctions testées ici sont de la logique PURE (parsing regex sur du texte),
validée séparément contre le vrai PDF 2025 (82 entrées réelles, 3 catégories,
noms d'entreprises avec parenthèses/esperluettes/apostrophes) — voir
docs/STATUT_RESEAU.md. Les fragments de texte ci-dessous reproduisent le VRAI
format confirmé (motif "AAAA <Catégorie> ranking" + "<rang> <nom> – <ville>
<province> <taux>%"), pas des données inventées au hasard."""
from falkye.sources.deloitte_fast50 import (
    _RE_PDF_HREF,
    _categorie_et_annee,
    _iter_entrees,
)

_PAGE_ENTETE_PLUS_TITRE = (
    "2025\n"
    "Technology Fast 50 ranking Enterprise—Industry Leaders ranking Companies-to-Watch ranking\n"
    "2025 Technology Fast 50 ranking\n"
)


def test_categorie_et_annee_ignore_l_entete_de_navigation_partagee():
    """L'en-tête de navigation (ligne 2) répète les 3 catégories sur CHAQUE
    page — un bug réel trouvé en développant : sans distinguer la vraie ligne
    de titre (ligne 3, format "AAAA <Catégorie> ranking"), toutes les pages
    étaient classées "Technology Fast 50" à tort."""
    resultat = _categorie_et_annee(_PAGE_ENTETE_PLUS_TITRE)
    assert resultat == ("Technology Fast 50", 2025)


def test_categorie_et_annee_distingue_chaque_categorie():
    texte = "2025\nTechnology Fast 50 ranking Enterprise—Industry Leaders ranking Companies-to-Watch ranking\n2025 Enterprise—Industry Leaders ranking\n"
    assert _categorie_et_annee(texte) == ("Enterprise—Industry Leaders", 2025)


def test_categorie_et_annee_retourne_none_si_pas_une_page_de_classement():
    texte = "2025\nTechnology Fast 50 ranking Enterprise—Industry Leaders ranking Companies-to-Watch ranking\nTechnology Fast 50 program winners\n"
    assert _categorie_et_annee(texte) is None


def test_iter_entrees_lit_les_deux_colonnes_d_une_meme_ligne():
    """La catégorie principale (50 gagnants) est présentée sur deux colonnes —
    le texte extrait garde les deux entrées sur UNE ligne visuelle."""
    ligne = "1 Red Rock Regeneration Inc. – Etobicoke ON 12166% 26 Vetster – Toronto ON 1175%\n"
    entrees = list(_iter_entrees(ligne))
    assert len(entrees) == 2
    assert entrees[0] == {
        "rang": 1,
        "nom": "Red Rock Regeneration Inc.",
        "ville": "Etobicoke",
        "province": "ON",
        "taux_croissance": 12166.0,
    }
    assert entrees[1]["rang"] == 26
    assert entrees[1]["nom"] == "Vetster"


def test_iter_entrees_gere_les_noms_avec_parentheses_et_esperluette():
    ligne = "25 Hydreight Technologies Inc (TSX-V: NURS) – Vancouver BC 1238%\n"
    entrees = list(_iter_entrees(ligne))
    assert len(entrees) == 1
    assert entrees[0]["nom"] == "Hydreight Technologies Inc (TSX-V: NURS)"
    assert entrees[0]["ville"] == "Vancouver"


def test_iter_entrees_gere_les_villes_a_apostrophe():
    ligne = "19 CoLab Software – St. John’s NL 1730%\n"
    entrees = list(_iter_entrees(ligne))
    assert len(entrees) == 1
    assert entrees[0]["ville"] == "St. John’s"
    assert entrees[0]["province"] == "NL"


def test_re_pdf_href_trouve_le_lien_peu_importe_l_annee():
    html = (
        '<a class="cmp-download__text-link" aria-label="Download PDF (2MB)" '
        'href="/content/dam/assets-zone3/ca/en/docs/industries/technology-media-telecommunications/'
        '2025/ca-fast-50-winners-2025-en-aoda.pdf" download>Download PDF (2MB)</a>'
    )
    m = _RE_PDF_HREF.search(html)
    assert m is not None
    assert m.group(1).endswith("ca-fast-50-winners-2025-en-aoda.pdf")
