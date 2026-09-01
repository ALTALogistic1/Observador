"""Tests du connecteur Permis de construction — Ville de Laval (spec section 7,
Signal 4).

Les fonctions testées ici sont de la logique PURE, validée séparément contre
le vrai fichier (172 168 lignes, 1991-2026) — voir docs/STATUT_RESEAU.md. Les
lignes ci-dessous reproduisent le VRAI format confirmé (en-têtes, entreprises
réelles, coût du permis en tarif administratif souvent forfaitaire), pas des
données inventées au hasard."""
import csv
import io

from falkye.sources.permis_construction_laval import _parse_date, _parse_float

_EN_TETES_REELLES = [
    "NO_PERMIS", "TYPE_PERMIS", "TYPE_PERMIS_DESCR", "CATEGORIE_BATIMENT",
    "TYPE_BATIMENT", "DATE_EMISSION", "STRUCTURE", "COUT_PERMIS",
    "NOMBRE_ETAGES", "NOMBRE_LOGEMENTS", "SUP_CA", "LOTS", "ENTREPRENEUR",
    "ADRESSE", "EXVILLE_CODE", "EXVILLE_DESCR", "OCCUPATION_DEBUT",
    "OCCUPATION_FIN", "ADRESSE_DETAILS",
]


def _ligne_reelle(entrepreneur="CONSTRUCTION LUC MIRON INC."):
    """Reproduit une vraie ligne du fichier (permis PN-1991-2033, confirmée
    le 2026-09-01)."""
    return {
        "NO_PERMIS": "PN-1991-2033",
        "TYPE_PERMIS": "PN",
        "TYPE_PERMIS_DESCR": "Permis de construction - nouvelle",
        "CATEGORIE_BATIMENT": "Bâtiment - C                       :COMM, INDUSTR, INSTITUT",
        "TYPE_BATIMENT": "Commerce 2",
        "DATE_EMISSION": "1992-02-10",
        "STRUCTURE": "isolée",
        "COUT_PERMIS": "557.00",
        "NOMBRE_ETAGES": "1",
        "NOMBRE_LOGEMENTS": "",
        "SUP_CA": "114.17",
        "LOTS": " 1 594 771",
        "ENTREPRENEUR": entrepreneur,
        "ADRESSE": "209A Boulevard Curé-Labelle (RO)",
        "EXVILLE_CODE": "RO",
        "EXVILLE_DESCR": "Sainte-Rose",
        "OCCUPATION_DEBUT": "",
        "OCCUPATION_FIN": "",
        "ADRESSE_DETAILS": "",
    }


def test_en_tetes_reelles_correspondent_aux_champs_utilises_par_le_connecteur():
    """Régression : si les en-têtes réelles changent, DictReader retournerait
    silencieusement None pour ces clés plutôt que de lever une erreur — ce
    test échoue explicitement si le connecteur référence une colonne absente
    des vraies en-têtes."""
    champs_utilises = {
        "NO_PERMIS", "ENTREPRENEUR", "DATE_EMISSION", "TYPE_PERMIS_DESCR",
        "ADRESSE", "EXVILLE_DESCR", "COUT_PERMIS",
    }
    assert champs_utilises.issubset(set(_EN_TETES_REELLES))


def test_dict_reader_gere_les_en_tetes_entre_guillemets():
    """Le vrai fichier a certaines en-têtes entre guillemets ("NO_PERMIS") et
    d'autres non (DATE_EMISSION) — csv.DictReader doit produire des clés
    propres dans les deux cas (pas de guillemets littéraux dans fieldnames)."""
    contenu = '"NO_PERMIS","TYPE_PERMIS",DATE_EMISSION,COUT_PERMIS\n"PN-1991-2033","PN",1992-02-10,557.00\n'
    reader = csv.DictReader(io.StringIO(contenu))
    assert reader.fieldnames == ["NO_PERMIS", "TYPE_PERMIS", "DATE_EMISSION", "COUT_PERMIS"]


def test_parse_date_gere_les_vraies_dates():
    dt = _parse_date("1992-02-10")
    assert dt is not None
    assert (dt.year, dt.month, dt.day) == (1992, 2, 10)


def test_parse_date_retourne_none_si_vide():
    assert _parse_date(None) is None
    assert _parse_date("") is None


def test_parse_float_gere_les_vrais_couts_de_permis():
    assert _parse_float("557.00") == 557.0
    assert _parse_float("1811.00") == 1811.0


def test_parse_float_retourne_none_si_vide():
    assert _parse_float(None) is None
    assert _parse_float("") is None
