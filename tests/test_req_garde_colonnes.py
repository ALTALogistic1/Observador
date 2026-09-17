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

# ⚠️ **Les colonnes des GISEMENTS s'ajoutent à celles que l'AST voit** — elles
# sont DÉCLARÉES dans `GISEMENTS_DE_NOMS`, parce que la passe les prend dans une
# table et qu'aucun arbre syntaxique ne peut les y lire. *Sans elles dans ce
# décor, le garde refuse — et il a raison de refuser.*
ENTETES_COMPLETES = {
    "Nom.csv": ["NEQ", "NOM_ASSUJ", "NOM_ASSUJ_LANG_ETRNG", "STAT_NOM"],
    "Entreprise.csv": ["COD_STAT_IMMAT"],
    "Etablissements.csv": ["LIGN1_ADR", "NEQ", "NOM_ETAB"],
    "FusionScissions.csv": ["NEQ", "DENOMN_SOC"],
}


def test_les_colonnes_lues_sortent_du_code_pas_dune_liste_recopiee():
    assert colonnes_brutes_lues(SOURCE, "_charger_index_noms") == {"NEQ", "NOM_ASSUJ"}


def test_une_fonction_inconnue_ne_rend_aucune_colonne():
    assert colonnes_brutes_lues(SOURCE, "_fonction_qui_nexiste_pas") == set()


def test_une_entete_complete_ne_declenche_rien():
    assert colonnes_declarees_absentes(ENTETES_COMPLETES, SOURCE) == {}


def test_une_colonne_absente_est_nommee_avec_son_csv():
    entetes = dict(ENTETES_COMPLETES,
                   **{"Nom.csv": ["NEQ", "NOM_ASSUJ_LANG_ETRNG", "STAT_NOM"]})
    assert colonnes_declarees_absentes(entetes, SOURCE) == {"Nom.csv": ["NOM_ASSUJ"]}


def test_une_colonne_de_GISEMENT_absente_est_refusee(): 
    """⚠️ **Le test qui verrouille le défaut trouvé à l'écriture.** *La passe des
    gisements fait `rangee.get(colonne)` où `colonne` vient d'une table — donc
    l'AST ne la voit pas, et sans déclaration les quatre gisements sortaient de
    la vérification EN SILENCE.*"""
    for csv_nom, colonne in (("Nom.csv", "NOM_ASSUJ_LANG_ETRNG"),
                             ("Etablissements.csv", "NOM_ETAB"),
                             ("FusionScissions.csv", "DENOMN_SOC")):
        entetes = dict(ENTETES_COMPLETES)
        entetes[csv_nom] = [c for c in entetes[csv_nom] if c != colonne]
        absentes = colonnes_declarees_absentes(entetes, SOURCE)
        assert absentes.get(csv_nom) == [colonne], (csv_nom, colonne, absentes)


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
        dict(ENTETES_COMPLETES, **{"Nom.csv": ["STAT_NOM", "TYP_NOM_ASSUJ",
                                               "NOM_ASSUJ_LANG_ETRNG", "NEQ"]}),
        source,
    )
    assert "STAT_NOMTYP_NOM_ASSUJ" in absentes["Nom.csv"]


def test_un_csv_entierement_absent_de_lentete_est_signale():
    """Une archive sans Nom.csv rendrait une en-tête vide, pas une erreur."""
    absentes = colonnes_declarees_absentes(dict(ENTETES_COMPLETES, **{"Nom.csv": []}), SOURCE)
    assert absentes["Nom.csv"] == ["NEQ", "NOM_ASSUJ", "NOM_ASSUJ_LANG_ETRNG", "STAT_NOM"]


def test_le_refus_nomme_la_colonne_et_dit_que_rien_na_ete_importe():
    with pytest.raises(ColonnesDeclareesAbsentes) as exc:
        refuser_si_colonnes_absentes({"Nom.csv": [], "Entreprise.csv": [],
                                      "Etablissements.csv": [], "FusionScissions.csv": []})
    message = str(exc.value)
    assert "NOM_ASSUJ" in message
    assert "Nom.csv" in message
    assert "Rien n'a été importé" in message
    assert "virgule" in message


def test_le_refus_se_tait_sur_une_archive_conforme():
    """Le garde-fou ne doit jamais refuser un import valide — sinon il serait
    retiré au premier faux positif, et ne protégerait plus rien."""
    import pathlib

    from falkye.sources.req import _LECTEURS_PAR_CSV, colonnes_des_gisements

    src = pathlib.Path("falkye/sources/req.py").read_text()
    des_gisements = colonnes_des_gisements()
    entetes: dict[str, list[str]] = {}
    for csv_nom, fonction in _LECTEURS_PAR_CSV.items():
        entetes[csv_nom] = sorted(colonnes_brutes_lues(src, fonction))
    for csv_nom, colonnes in des_gisements.items():
        entetes[csv_nom] = sorted(set(entetes.get(csv_nom, [])) | colonnes)
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
    #
    # ⚠️ Les colonnes des GISEMENTS restent exigées : la quarantaine ne les
    # surveille pas, et *une colonne de gisement qui disparaît doit échouer
    # BRUYAMMENT* — c'est la règle posée le 2026-09-17. Elles sont donc dans le
    # décor, comme dans une archive réelle.
    absentes = colonnes_declarees_absentes(
        {
            "Entreprise.csv": ["ADR_DOMCL_ADR_DISP", "ADR_DOMCL_LIGN2_ADR",
                               "ADR_DOMCL_LIGN3_ADR", "ADR_DOMCL_LIGN4_ADR", "COD_ACT_ECON_CAE"],
            "Nom.csv": ["DAT_FIN_NOM_ASSUJ", "DAT_INIT_NOM_ASSUJ", "STAT_NOM",
                        "TYP_NOM_ASSUJ", "NOM_ASSUJ_LANG_ETRNG", "NEQ"],
            "Etablissements.csv": ["COD_ACT_ECON", "LIGN3_ADR", "NO_SUF_ETAB",
                                   "NEQ", "NOM_ETAB"],
            "FusionScissions.csv": ["NEQ", "DENOMN_SOC"],
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
