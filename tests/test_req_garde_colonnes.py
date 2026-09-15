"""Le garde-fou des colonnes déclarées — une colonne absente ne lève pas, et
c'est exactement ce qui l'a rendue invisible."""
import pytest

from falkye.sources.req import (
    ColonnesDeclareesAbsentes,
    colonnes_brutes_lues,
    colonnes_declarees_absentes,
    refuser_si_colonnes_absentes,
)

SOURCE = '''
def _charger_index_noms(zf):
    for row in lecteur:
        neq = (row.get("NEQ") or "").strip()
        nom = (row.get("NOM_ASSUJ") or "").strip()

def _resoudre_entreprise(row, noms, etabs):
    return row.get("COD_STAT_IMMAT")

def _charger_index_etablissements(zf):
    return row.get("LIGN1_ADR")
'''

ENTETES_COMPLETES = {
    "Nom.csv": ["NEQ", "NOM_ASSUJ"],
    "Entreprise.csv": ["COD_STAT_IMMAT"],
    "Etablissements.csv": ["LIGN1_ADR"],
}


def test_les_colonnes_lues_sortent_du_code_pas_dune_liste_recopiee():
    assert colonnes_brutes_lues(SOURCE, "_charger_index_noms") == {"NEQ", "NOM_ASSUJ"}


def test_une_fonction_inconnue_ne_rend_aucune_colonne():
    assert colonnes_brutes_lues(SOURCE, "_fonction_qui_nexiste_pas") == set()


def test_une_entete_complete_ne_declenche_rien():
    assert colonnes_declarees_absentes(ENTETES_COMPLETES, SOURCE) == {}


def test_une_colonne_absente_est_nommee_avec_son_csv():
    entetes = dict(ENTETES_COMPLETES, **{"Nom.csv": ["NEQ"]})
    assert colonnes_declarees_absentes(entetes, SOURCE) == {"Nom.csv": ["NOM_ASSUJ"]}


def test_une_virgule_oubliee_produit_une_colonne_qui_nexiste_pas():
    """`row.get("A" "B")` est du Python VALIDE : deux littéraux collés n'en font
    qu'un. L'AST rend la chaîne telle que Python la voit — et c'est ce qui rend
    la faute visible, là où `.get` rendrait None sans rien dire."""
    source = '''
def _charger_index_noms(zf):
    stat = row.get("STAT_NOM"
                   "TYP_NOM_ASSUJ")
'''
    assert colonnes_brutes_lues(source, "_charger_index_noms") == {"STAT_NOMTYP_NOM_ASSUJ"}
    absentes = colonnes_declarees_absentes(
        {"Nom.csv": ["STAT_NOM", "TYP_NOM_ASSUJ"]}, source
    )
    assert absentes["Nom.csv"] == ["STAT_NOMTYP_NOM_ASSUJ"]


def test_un_csv_entierement_absent_de_lentete_est_signale():
    """Une archive sans Nom.csv rendrait une en-tête vide, pas une erreur."""
    absentes = colonnes_declarees_absentes(dict(ENTETES_COMPLETES, **{"Nom.csv": []}), SOURCE)
    assert absentes["Nom.csv"] == ["NEQ", "NOM_ASSUJ"]


def test_le_refus_nomme_la_colonne_et_dit_que_rien_na_ete_importe():
    with pytest.raises(ColonnesDeclareesAbsentes) as exc:
        refuser_si_colonnes_absentes({"Nom.csv": [], "Entreprise.csv": [], "Etablissements.csv": []})
    message = str(exc.value)
    assert "NOM_ASSUJ" in message
    assert "Nom.csv" in message
    assert "Rien n'a été importé" in message
    assert "virgule" in message


def test_le_refus_se_tait_sur_une_archive_conforme():
    """Le garde-fou ne doit jamais refuser un import valide — sinon il serait
    retiré au premier faux positif, et ne protégerait plus rien."""
    import pathlib

    from falkye.sources.req import _LECTEURS_PAR_CSV

    src = pathlib.Path("falkye/sources/req.py").read_text()
    entetes = {
        csv_nom: sorted(colonnes_brutes_lues(src, fonction))
        for csv_nom, fonction in _LECTEURS_PAR_CSV.items()
    }
    refuser_si_colonnes_absentes(entetes)  # ne lève pas


def test_les_colonnes_surveillees_par_la_quarantaine_sont_laissees_passer():
    """La quarantaine est une MEILLEURE réponse qu'un refus : elle laisse
    REQEntry intact et journalise le motif. Le garde-fou ne doit pas la
    préempter — sinon on perdrait l'incident."""
    import pathlib

    from falkye.sources.req import colonnes_couvertes_par_la_quarantaine

    src = pathlib.Path("falkye/sources/req.py").read_text()
    couvertes = colonnes_couvertes_par_la_quarantaine(src)
    assert "NOM_ASSUJ" in couvertes and "COD_STAT_IMMAT" in couvertes
    # Une Entreprise.csv privée de COD_STAT_IMMAT part en quarantaine, pas en refus.
    absentes = colonnes_declarees_absentes(
        {
            "Entreprise.csv": ["ADR_DOMCL_ADR_DISP", "ADR_DOMCL_LIGN2_ADR",
                               "ADR_DOMCL_LIGN3_ADR", "ADR_DOMCL_LIGN4_ADR", "COD_ACT_ECON_CAE"],
            "Nom.csv": ["DAT_FIN_NOM_ASSUJ", "DAT_INIT_NOM_ASSUJ", "STAT_NOM", "TYP_NOM_ASSUJ"],
            "Etablissements.csv": ["COD_ACT_ECON", "LIGN3_ADR", "NO_SUF_ETAB"],
        },
        src,
    )
    assert absentes == {}


def test_la_couverture_ne_sattrape_pas_sur_un_in_de_dictionnaire():
    """`"clé" in un_dict` n'est pas une vérification d'en-tête. Compté comme
    telle, il élargirait la couverture en silence — donc rétrécirait le
    garde-fou sans que personne ne le voie."""
    from falkye.sources.req import colonnes_couvertes_par_la_quarantaine

    source = '''
def f(entete_nom, options):
    if "NOM_ASSUJ" in entete_nom:
        pass
    if "_local_path" in options:
        pass
'''
    assert colonnes_couvertes_par_la_quarantaine(source) == {"NOM_ASSUJ"}
