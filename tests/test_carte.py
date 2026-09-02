"""Tests de la carte géographique interactive (falkye/carte.py) — spec section
4bis. Logique pure (aucun accès réseau/DB ici), points de test fabriqués."""
from falkye.carte import PointCarte, generer_carte_html


def _point(id_=1, niveau="AAA"):
    return PointCarte(
        notification_id=id_,
        nom_entreprise="Entreprise Test Inc.",
        latitude=45.5,
        longitude=-73.6,
        niveau_pertinence=niveau,
        niveau_confiance="eleve",
        ville="Montréal",
    )


def test_carte_vide_reste_valide():
    html_carte = generer_carte_html([])
    assert "<html" in html_carte
    assert "L.map" in html_carte


def test_carte_contient_les_coordonnees_des_points():
    html_carte = generer_carte_html([_point()])
    assert "45.5" in html_carte
    assert "-73.6" in html_carte


def test_carte_echappe_le_nom_de_l_entreprise():
    """Protection XSS de base — un nom d'entreprise contenant du HTML ne doit
    jamais s'injecter tel quel dans la page (principe de robustesse générale,
    pas spécifique aux données réelles de ce projet)."""
    point = _point()
    point.nom_entreprise = "<script>alert(1)</script>"
    html_carte = generer_carte_html([point])
    assert "<script>alert(1)</script>" not in html_carte
    assert "&lt;script&gt;" in html_carte


def test_carte_utilise_une_couleur_differente_par_niveau_de_pertinence():
    html_aaa = generer_carte_html([_point(niveau="AAA")])
    html_a = generer_carte_html([_point(niveau="A")])
    # Les couleurs assignées par niveau doivent différer dans le JSON des marqueurs.
    assert "#1a7f37" in html_aaa
    assert "#8a8f98" in html_a


def test_carte_gere_niveau_pertinence_absent():
    """Notification historique (antérieure au système de pertinence) — pas de
    crash, couleur par défaut."""
    point = _point(niveau=None)
    html_carte = generer_carte_html([point])
    assert "n/d" in html_carte
