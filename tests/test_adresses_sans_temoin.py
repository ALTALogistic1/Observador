"""Les adresses du registre — fonctions pures, sans réseau ni registre."""
from outils.adresses_sans_temoin import classer, est_citee_dans_le_code, urls_dune_valeur


class FausseSource:
    def __init__(self, est_import_manuel=False, est_actif=True):
        self.est_import_manuel = est_import_manuel
        self.est_actif = est_actif


def test_une_adresse_enterree_dans_une_note_compte_autant_quun_lien():
    """Elle sera lue par un humain exactement pareil."""
    assert urls_dune_valeur("voir https://exemple.qc.ca/a pour le détail") == \
        ["https://exemple.qc.ca/a"]


def test_la_ponctuation_finale_nentre_pas_dans_ladresse():
    """`…aspx.` sondée telle quelle rendrait un faux 404."""
    assert urls_dune_valeur("l'adresse est https://exemple.qc.ca/x.aspx.") == \
        ["https://exemple.qc.ca/x.aspx"]
    assert urls_dune_valeur("(https://exemple.qc.ca/y)") == ["https://exemple.qc.ca/y"]


def test_les_structures_imbriquees_sont_parcourues():
    valeur = {"a": ["https://un.qc.ca", {"b": "https://deux.qc.ca"}]}
    assert urls_dune_valeur(valeur) == ["https://un.qc.ca", "https://deux.qc.ca"]


def test_une_valeur_sans_adresse_ne_rend_rien():
    assert urls_dune_valeur(None) == []
    assert urls_dune_valeur("aucune adresse ici") == []
    assert urls_dune_valeur(42) == []


def test_la_citation_est_litterale_jamais_par_domaine():
    """Deux sources du même portail partagent un domaine sans partager une
    adresse — compter l'une pour l'autre rendrait la mesure fausse dans le sens
    rassurant."""
    py = {"falkye/sources/a.py": 'URL = "https://portail.qc.ca/jeu-A"'}
    assert est_citee_dans_le_code("https://portail.qc.ca/jeu-A", py) == ["falkye/sources/a.py"]
    assert est_citee_dans_le_code("https://portail.qc.ca/jeu-B", py) == []


def test_une_adresse_citee_par_le_code_est_eprouvee():
    assert classer(FausseSource(), "u", ["falkye/sources/a.py"]) == "citée par le code"


def test_une_source_en_import_manuel_na_pas_de_temoin():
    assert classer(FausseSource(est_import_manuel=True), "u", []) == \
        "SANS TÉMOIN — source en import manuel"


def test_une_source_inactive_na_pas_de_temoin_non_plus():
    assert classer(FausseSource(est_actif=False), "u", []) == "SANS TÉMOIN — source inactive"


def test_un_connecteur_actif_dont_ladresse_nest_pas_citee_est_signale():
    """Le cas le plus inquiétant : la source tourne, mais rien ne prouve que
    c'est CETTE adresse qu'elle appelle."""
    assert classer(FausseSource(), "u", []) == \
        "SANS TÉMOIN — connecteur actif, adresse non citée"
