"""Le profil des absents du REQ — fonctions pures, sans archive."""
from collections import Counter

from outils.profil_des_absents_req import (
    charger_domaines,
    part,
    prefixe_neq,
    ventilation_comparee,
)


def test_le_prefixe_est_la_forme_juridique_selon_le_guide():
    """« Les deux premiers chiffres correspondent à la forme juridique de
    l'entreprise et sont 11, 22 ou 33. » — guide du Registraire, p. 16."""
    assert prefixe_neq("1173929648") == "11"
    assert prefixe_neq("2282522335") == "22"
    assert prefixe_neq("8881817611") == "88"
    assert prefixe_neq("") == ""


def test_une_part_sur_un_compteur_vide_ne_divise_pas_par_zero():
    assert part(Counter(), "x") == 0.0
    assert part(Counter({"a": 3, "b": 1}), "a") == 75.0


def test_la_ventilation_trie_par_ECART_pas_par_compte():
    """Une valeur portée par 90 % des absents ne dit rien si 90 % des présents la
    portent aussi. Trier par compte ferait remonter le banal."""
    # « banal » est le PLUS COMPTÉ chez les absents (600) mais sa part y est la
    # même que chez les présents (60 %) : écart nul. « distinctif » est quatre
    # fois moins compté et pourtant c'est lui qui désigne.
    absents = Counter({"banal": 600, "distinctif": 400})
    presents = Counter({"banal": 9000, "autre": 1000})
    lignes = ventilation_comparee(absents, presents, {}, None)
    assert lignes[0][1] == "distinctif"      # 40 % des absents, 0 % des présents
    assert lignes[0][0] == 40.0
    ecarts = {valeur: ecart for ecart, valeur, *_ in lignes}
    assert ecarts["banal"] == -30.0          # le plus COMPTÉ, pas le plus distinctif


def test_un_ecart_negatif_compte_autant_quun_positif():
    """Une valeur ABSENTE des absents et massive chez les présents désigne tout
    autant — le tri porte sur la valeur absolue."""
    absents = Counter({"a": 100})
    presents = Counter({"a": 10, "b": 90})
    lignes = ventilation_comparee(absents, presents, {}, None)
    assert lignes[0][1] in ("a", "b")
    assert abs(lignes[0][0]) == 90.0


def test_le_libelle_vient_du_domaine_demande():
    libelles = {("FORM_JURI", "12"): "Société par actions", ("AUTRE", "12"): "Pas celui-là"}
    lignes = ventilation_comparee(Counter({"12": 1}), Counter(), libelles, "FORM_JURI")
    assert lignes[0][2] == "Société par actions"


def test_sans_domaine_aucun_libelle_nest_invente():
    lignes = ventilation_comparee(Counter({"12": 1}), Counter(), {"x": "y"}, None)
    assert lignes[0][2] == ""


class FauxZip:
    def __init__(self, membres):
        self._membres = membres

    def namelist(self):
        return list(self._membres)

    def open(self, nom):
        import io as _io

        return _io.BytesIO(self._membres[nom].encode("utf-8"))


def test_les_domaines_se_lisent_du_fichier_de_larchive():
    zf = FauxZip({
        "DomaineValeur.csv":
            "TYP_DOM_VAL,COD_DOM_VAL,VAL_DOM_FRAN\n"
            "FORM_JURI,12,Société par actions\n"
            "STAT_IMMAT,IM,Immatriculée\n"
    })
    domaines = charger_domaines(zf)
    assert domaines[("FORM_JURI", "12")] == "Société par actions"
    assert domaines[("STAT_IMMAT", "IM")] == "Immatriculée"


def test_un_domaine_absent_ne_leve_pas_et_laisse_les_codes_nus():
    """L'outil reste utilisable, et il le dit — plutôt que de tomber."""
    assert charger_domaines(FauxZip({"Entreprise.csv": "NEQ\n"})) == {}
