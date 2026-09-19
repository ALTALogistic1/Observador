"""Le départageur d'adresse — UN mécanisme, DEUX niveaux, et un seul interdit.

⚠️ *La ville ne parle JAMAIS là où le code postal a exclu tout le monde* — ce
serait bâtir un départage par-dessus une contradiction établie.

⚠️ *Et la non-régression sur les retenus est un CRITÈRE* : `departager_le_dossier`
refuse un dossier que le nom a déjà tranché, au lieu de réussir discrètement.
"""
from __future__ import annotations

import pytest

from outils import departageur_adresse as da
from outils.departageurs import (
    AUCUN_COMPATIBLE,
    DEPARTAGE,
    PLUSIEURS_COMPATIBLES,
    SANS_FAIT_AU_DOSSIER,
    SANS_FAIT_CHEZ_UN_CONCURRENT,
    codes_postaux,
    fait_de_la_ville,
)


def _faits(cp: str | None, ville: str | None) -> da.FaitsDAdresse:
    return da.FaitsDAdresse(codes_postaux(cp), fait_de_la_ville(ville))


# ---------------------------------------------------------------------------
# LES TROIS NIVEAUX — et ce qui distingue les deux résolutions du code postal
# ---------------------------------------------------------------------------

def test_la_compatibilite_du_fait_COMBINE_est_celle_de_la_REGION_DE_TRI():
    """⚠️ **Le fait qui a fait naître les trois niveaux.**

    *`codes_postaux` range `jeton[:3]` À CÔTÉ de chaque code complet.* Donc deux
    faits combinés s'intersectent **si et seulement si** leurs régions de tri
    s'intersectent — **le code complet ne tranchait rien, jamais.** *Wazoom
    n'était pas un cas limite : c'était tout le niveau.*
    """
    paires = [("G5R 3A7", "G5R 3Y8"), ("H2N 1A1", "H2N 1A1"),
              ("H2N 1A1", "H2N 5X9"), ("K2E 7L6", "K2E"),
              ("G5R 3A7", "H2N 1A1")]
    for a, b in paires:
        fa, fb = _faits(a, None), _faits(b, None)
        combine = fa.code_postal.compatible_avec(fb.code_postal)
        region = (fa.region_de_tri is not None and fb.region_de_tri is not None
                  and fa.region_de_tri.compatible_avec(fb.region_de_tri))
        assert combine == region, (a, b)


def test_le_CODE_COMPLET_tranche_ce_que_la_region_de_tri_ne_separait_pas():
    """*Trois `TRIGONIX` dans la même région de tri : la région en laisse deux
    debout, le code complet en laisse un.*"""
    d = da.departager_ladresse(
        _faits("H2N 1A1", None), [_faits("H2N 1A1", None), _faits("H2N 5X9", None)]
    )
    assert (d.issue, d.niveau, d.gagnant) == (DEPARTAGE, da.NIVEAU_CODE_COMPLET, 0)
    assert d.par_niveau == ((da.NIVEAU_CODE_COMPLET, DEPARTAGE),)


def test_la_REGION_DE_TRI_parle_quand_le_code_complet_les_EXCLUT_TOUS():
    """⚠️ **La porte à ne pas fermer — le cas `Wazoom`.**

    *`G5R3A7` contre `G5R3Y8` s'excluent au code complet, et c'est exactement ce
    que la dégradation tolère : même axe, résolution plus basse.* **Sans cette
    porte, les départages de la région de tri disparaîtraient.**
    """
    d = da.departager_ladresse(
        _faits("G5R 3A7", "Riviere-du-Loup"),
        [_faits("G5R 3Y8", "CP 235"), _faits("H2N 1A1", "Montreal")],
    )
    assert d.par_niveau == (
        (da.NIVEAU_CODE_COMPLET, AUCUN_COMPATIBLE),
        (da.NIVEAU_REGION_DE_TRI, DEPARTAGE),
    )
    assert (d.niveau, d.gagnant) == (da.NIVEAU_REGION_DE_TRI, 0)


def test_un_code_TRONQUE_va_droit_a_la_region_de_tri():
    """⚠️ *L'EIMT écrit `'St-Isidore, QC J0L  2A'` — cinq caractères sur six.*
    **Le dossier ne porte alors AUCUN code complet**, et le premier niveau se
    tait au lieu d'exclure."""
    d = da.departager_ladresse(
        _faits("St-Isidore, QC J0L  2A", None),
        [_faits("1 rue A H2X 1Y4", None), _faits("2 rue B J0L 2A1", None)],
    )
    assert d.issue_du_niveau(da.NIVEAU_CODE_COMPLET) == SANS_FAIT_AU_DOSSIER
    assert (d.niveau, d.gagnant) == (da.NIVEAU_REGION_DE_TRI, 1)


def test_aucun_code_ne_sinvente_par_FENETRE_GLISSANTE():
    """⚠️ *`STISIDOREQCJ0L2A` contient `L2A`, qui n'est pas une région de tri.*"""
    assert codes_postaux("St-Isidore QC") is None


def test_un_fait_VIDE_a_une_resolution_rend_None_et_non_un_ensemble_vide():
    """*Sinon « le dossier ne porte pas le fait » deviendrait « le fait ne
    concorde avec personne » — un silence pris pour un démenti.*"""
    faits = _faits("J0L", None)          # une région de tri seule
    assert faits.region_de_tri is not None
    assert faits.code_complet is None


# ---------------------------------------------------------------------------
# LE REPLI — trois portes ouvertes, et une qui dépend du niveau suivant
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("dossier_cp, concurrents_cp, issue_attendue", [
    # le dossier ne porte pas de code postal du tout
    (None, ["G6V 1A1", "H2X 1Y4"], SANS_FAIT_AU_DOSSIER),
    # ⚠️ « inconnu ≠ non » — 837 dossiers bloqués là sur l'hôte
    ("G6V 1A1", ["G6V 1A1", None], SANS_FAIT_CHEZ_UN_CONCURRENT),
    # le code postal réduit sans trancher
    ("G6V 1A1", ["G6V 1A1", "G6V 1A1"], PLUSIEURS_COMPATIBLES),
])
def test_la_ville_PARLE_quand_le_code_postal_na_pas_tranche(
    dossier_cp, concurrents_cp, issue_attendue
):
    """**Les trois portes du repli, une par issue qui n'est pas une décision.**"""
    d = da.departager_ladresse(
        _faits(dossier_cp, "Levis"),
        [_faits(cp, v) for cp, v in zip(concurrents_cp, ["Laval", "Levis"])],
    )
    assert d.issue_du_niveau(da.NIVEAU_REGION_DE_TRI) == issue_attendue
    assert (d.issue, d.niveau, d.gagnant) == (DEPARTAGE, da.NIVEAU_VILLE, 1)


def test_la_ville_NE_PARLE_PAS_quand_la_region_de_tri_les_exclut_TOUS():
    """⚠️ **La porte fermée, et c'est la règle la plus importante du module.**

    *Le code postal du dossier dément tous les candidats, à ses DEUX
    résolutions. La ville est un AUTRE fait, plus grossier* — la laisser
    désigner un gagnant serait bâtir un départage par-dessus une contradiction
    établie.
    """
    d = da.departager_ladresse(
        _faits("Levis, QC G7A 2B2", "Levis"),
        # la ville, elle, désignerait le second sans hésiter
        [_faits("1 rue A H2X 1Y4", "Laval"), _faits("2 rue B G6V 1A1", "Levis")],
    )
    assert d.issue == AUCUN_COMPATIBLE
    assert d.niveau is None and d.gagnant is None
    assert d.par_niveau == (
        (da.NIVEAU_CODE_COMPLET, AUCUN_COMPATIBLE),
        (da.NIVEAU_REGION_DE_TRI, AUCUN_COMPATIBLE),
    )
    assert d.issue_du_niveau(da.NIVEAU_VILLE) is None


def test_le_repli_dit_par_quel_maillon_chaque_niveau_a_echoue():
    """*« La ville a séparé » ne dit pas si le code postal était muet ou bloqué
    par « inconnu ≠ non » — et ce sont deux correctifs différents.*"""
    d = da.departager_ladresse(
        _faits("G6V 1A1", "Levis"),
        [_faits(None, "Laval"), _faits("G6V 1A1", "Levis")],
    )
    assert d.par_niveau == (
        (da.NIVEAU_CODE_COMPLET, SANS_FAIT_CHEZ_UN_CONCURRENT),
        (da.NIVEAU_REGION_DE_TRI, SANS_FAIT_CHEZ_UN_CONCURRENT),
        (da.NIVEAU_VILLE, DEPARTAGE),
    )


def test_aucun_niveau_ne_tranche_reste_un_RESULTAT():
    d = da.departager_ladresse(
        _faits(None, None), [_faits("G6V 1A1", "Levis"), _faits("H2X 1Y4", "Laval")]
    )
    assert d.issue == SANS_FAIT_AU_DOSSIER
    assert not d.prononce


# ---------------------------------------------------------------------------
# LA FORME D'AVANT — gardée pour MESURER l'écart, pas pour décider
# ---------------------------------------------------------------------------

def test_la_forme_DAVANT_se_rejoue_par_un_APPEL_du_meme_mecanisme():
    """⚠️ *Un départageur recopié à la main est déjà arrivé une fois (cas 41).*"""
    faits = _faits("G5R 3A7", "Riviere-du-Loup")
    concurrents = [_faits("G5R 3Y8", "CP 235"), _faits("H2N 1A1", "Montreal")]
    davant = da.departager_ladresse(faits, concurrents, niveaux=da.NIVEAUX_DAVANT)
    assert (davant.issue, davant.niveau, davant.gagnant) == (
        DEPARTAGE, da.NIVEAU_CODE_POSTAL, 0)


def test_la_forme_a_trois_niveaux_ne_PERD_aucun_departage_de_la_forme_davant():
    """⚠️ **Le critère du découpage** : *rendre la granularité lisible, pas
    écrire moins ni écrire autrement.*

    Toute compatibilité de la forme d'avant est une compatibilité de région de
    tri; le code complet n'en ajoute jamais. **Donc un départage d'hier se
    retrouve soit au code complet, soit à la région de tri — avec le même
    gagnant.**
    """
    decors = [
        ("G5R 3A7", ["G5R 3Y8", "H2N 1A1"]),
        ("H2N 1A1", ["H2N 1A1", "H2N 5X9"]),
        ("K2E 7L6", ["K2E 7L6", "H2X 1Y4"]),
        ("J0L", ["J0L 2A1", "H2X 1Y4"]),
        ("G6V 1A1", ["H2X 1Y4", "H7A 1B1"]),
        (None, ["H2X 1Y4", "H7A 1B1"]),
    ]
    for cp, concurrents_cp in decors:
        faits = _faits(cp, "Levis")
        concurrents = [_faits(c, "Levis") for c in concurrents_cp]
        davant = da.departager_ladresse(faits, concurrents, niveaux=da.NIVEAUX_DAVANT)
        apres = da.departager_ladresse(faits, concurrents)
        if davant.prononce:
            assert apres.prononce, (cp, concurrents_cp)
            assert apres.gagnant == davant.gagnant, (cp, concurrents_cp)


# ---------------------------------------------------------------------------
# LA GARDE SUR LE VOCABULAIRE — une issue nouvelle ne tombe pas « par défaut »
# ---------------------------------------------------------------------------

def test_une_ISSUE_non_classee_leve_au_lieu_de_tomber_du_bon_cote(monkeypatch):
    """⚠️ *Sans elle, ajouter une issue à `departageurs.py` la ferait
    silencieusement tomber du côté « ne replie pas ».*"""
    monkeypatch.setattr(da, "ISSUES", da.ISSUES + ("une issue toute neuve",))
    with pytest.raises(da.IssueNonClassee) as capture:
        da._refuser_si_une_issue_nest_pas_classee()
    assert "une issue toute neuve" in str(capture.value)


def test_toutes_les_issues_daujourdhui_sont_classees():
    da._refuser_si_une_issue_nest_pas_classee()  # ne lève pas


# ---------------------------------------------------------------------------
# LA NON-RÉGRESSION — un CRITÈRE, pas un effet secondaire acceptable
# ---------------------------------------------------------------------------

class _Entree:
    def __init__(self, neq, score, ville=None, cp=None, adresse=None):
        self.neq, self.ville, self.code_postal, self.adresse = neq, ville, cp, adresse
        self.nom = neq


class _Match:
    def __init__(self, neq, score, **kw):
        self.entry = _Entree(neq, score, **kw)
        self.score = score


@pytest.mark.parametrize("matches, famille", [
    ([_Match("A", 99.0), _Match("B", 80.0)], "RETENU"),
    ([_Match("A", 99.0)], "RETENU"),
    ([_Match("A", 70.0), _Match("B", 60.0)], "trop faible"),
    ([], "aucun candidat"),
])
def test_le_departageur_REFUSE_tout_ce_qui_nest_pas_ambigu(matches, famille):
    """⚠️ **La non-régression sur les 2 634 retenus est STRUCTURELLE.**

    *Un retenu ne peut pas être re-décidé par l'adresse — non parce qu'on
    n'appellera pas, mais parce que l'appel échoue.*
    """
    with pytest.raises(da.PasUnAmbigu) as capture:
        da.departager_le_dossier(matches, _faits("G6V 1A1", "Levis"))
    assert famille in str(capture.value)


def test_les_concurrents_sont_ceux_a_MOINS_DE_LECART_du_meilleur():
    """*C'est exactement l'ensemble sur lequel un abaissement de l'écart
    trancherait à l'aveugle.*"""
    from falkye.resolution import SEUIL_AMBIGUITE_ECART_MIN

    matches = [_Match("A", 95.0), _Match("B", 94.0), _Match("C", 95.0 - SEUIL_AMBIGUITE_ECART_MIN)]
    assert [m.entry.neq for m in da.concurrents_de(matches)] == ["A", "B"]


def test_un_ambigu_passe_la_garde_et_se_departage():
    matches = [_Match("A", 95.0, cp="H2X 1Y4"), _Match("B", 94.0, cp="G6V 1A1")]
    d, concurrents = da.departager_le_dossier(matches, _faits("G6V 1A1", None))
    assert len(concurrents) == 2
    assert (d.issue, d.niveau, d.gagnant) == (DEPARTAGE, da.NIVEAU_CODE_COMPLET, 1)


def test_les_echelles_ne_sont_pas_touchees():
    from falkye import resolution

    assert resolution.SEUIL_RESOLUTION_CONFIANTE == 92.0
    assert resolution.SEUIL_AMBIGUITE_ECART_MIN == 8.0


# ---------------------------------------------------------------------------
# LA LECTURE DES FAITS — empruntée, jamais recopiée
# ---------------------------------------------------------------------------

class _Dossier:
    def __init__(self, adresse=None, code_postal=None, ville=None):
        self.id = 1
        self.adresse, self.code_postal, self.ville = adresse, code_postal, ville


def test_le_fait_du_dossier_lit_AUSSI_une_adresse_IMBRIQUEE():
    """*Le SEAO range la sienne sous `adresse_entreprise_adjudicataire`.*"""
    faits = da.faits_du_dossier(
        _Dossier(),
        {"adresse_entreprise_adjudicataire": {"ligne1": "12 rue X", "cp": "G6V 1A1"}},
    )
    assert faits.code_postal is not None
    assert "G6V1A1" in faits.code_postal.formes and "G6V" in faits.code_postal.formes


def test_la_ville_EXPLICITE_du_dossier_prime_sur_celle_vue_dans_un_signal():
    """*Une ville promue a été décidée; une ville vue a été trouvée.*"""
    faits = da.faits_du_dossier(_Dossier(ville="Lévis"), None, ville_vue="Laval")
    assert faits.ville.brut == "Lévis"


def test_le_fait_du_candidat_joint_adresse_ET_code_postal():
    faits = da.faits_du_candidat(_Entree("1", 0, ville="Laval", cp="H7A 1B2",
                                         adresse="3 rue Z"))
    assert faits.code_postal.formes == frozenset({"H7A1B2", "H7A"})
    assert faits.ville is not None


# ---------------------------------------------------------------------------
# UN GAGNANT DÉPLACÉ — et la seule route qui y mène
# ---------------------------------------------------------------------------

def _routes_entre_les_deux_formes():
    """Balaie EXHAUSTIVEMENT de petits décors et rend les routes observées.

    ⚠️ *Un balayage exhaustif sur un petit domaine dit ce qui est POSSIBLE; dix
    cas tirés ne disent que ce qui est arrivé.* **C'est la différence entre
    « je n'en ai pas vu d'autre » et « il n'y en a pas d'autre ».**
    """
    import itertools

    codes = [None, "G5R 3A7", "G5R 3Y8", "G5R", "H2N 1A1"]
    villes = [None, "Levis", "Laval"]
    perdus: set = set()
    deplaces: set = set()
    for dcp, dv in itertools.product(codes, villes):
        for c1 in itertools.product(codes, villes):
            for c2 in itertools.product(codes, villes):
                dossier = _faits(dcp, dv)
                conc = [_faits(*c1), _faits(*c2)]
                avant = da.departager_ladresse(dossier, conc, niveaux=da.NIVEAUX_DAVANT)
                apres = da.departager_ladresse(dossier, conc)
                if avant.prononce and not apres.prononce:
                    perdus.add((avant.niveau, apres.issue))
                elif (avant.prononce and apres.prononce
                        and avant.gagnant != apres.gagnant):
                    deplaces.add((avant.niveau, apres.niveau))
    return perdus, deplaces


def test_AUCUNE_route_ne_perd_un_departage_de_la_forme_davant():
    """⚠️ **Le découpage ne peut pas écrire moins, et ce n'est pas une
    observation : c'est une propriété du treillis.**

    *La compatibilité de la forme d'avant EST celle de la région de tri, et
    celle du code complet en est un sous-ensemble.* **Donc un départage d'hier
    se retrouve soit au code complet, soit à la région de tri.**
    """
    perdus, _ = _routes_entre_les_deux_formes()
    assert perdus == set(), perdus


def test_la_SEULE_route_dun_gagnant_deplace_est_VILLE_vers_CODE_COMPLET():
    """⚠️ **Ce qui tranche entre « un défaut » et « le gain ».**

    Un gagnant ne peut changer que d'une façon : *la forme d'avant tombait sur
    la VILLE faute de trancher au code postal, et le CODE COMPLET tranche
    maintenant, vers un autre candidat.* **Aucune autre route n'existe** — donc
    un déplacement n'est jamais un artefact d'ordre d'évaluation.

    *Et c'est le même mécanisme que les départages ajoutés : si le code complet
    tranche là où la région ne pouvait pas, il tranche aussi autrement là où la
    région tranchait mal.*
    """
    _, deplaces = _routes_entre_les_deux_formes()
    assert deplaces == {(da.NIVEAU_VILLE, da.NIVEAU_CODE_COMPLET)}, deplaces


def _deplacement(dossier, concurrents):
    avant = da.departager_ladresse(dossier, concurrents, niveaux=da.NIVEAUX_DAVANT)
    apres = da.departager_ladresse(dossier, concurrents)
    return da.expliquer_le_deplacement(dossier, concurrents, avant, apres), avant, apres


def test_un_deplacement_est_EXPLIQUE_quand_le_niveau_fin_exclut_lancien():
    """*La ville désignait `Laval`; le code complet désigne l'autre — et il
    EXCLUT celui que la ville avait retenu.*"""
    dossier = _faits("H2N 1A1", "Laval")
    concurrents = [_faits("H2N 5X9", "Laval"), _faits("H2N 1A1", "Quebec")]
    expl, avant, apres = _deplacement(dossier, concurrents)
    assert (avant.niveau, apres.niveau) == (da.NIVEAU_VILLE, da.NIVEAU_CODE_COMPLET)
    assert expl.explique and expl.motif == da.EXPLIQUE


@pytest.mark.parametrize("rang_avant, rang_apres, motif", [
    (da.NIVEAU_CODE_COMPLET, da.NIVEAU_VILLE, da.PAS_PLUS_FIN),
    (da.NIVEAU_REGION_DE_TRI, da.NIVEAU_REGION_DE_TRI, da.PAS_PLUS_FIN),
])
def test_un_niveau_qui_nest_PAS_plus_fin_nexplique_rien(rang_avant, rang_apres, motif):
    """⚠️ *Sans cette condition, le critère accepterait qu'un fait plus grossier
    renverse un fait plus fin* — exactement ce que le repli interdit."""
    from outils.departageur_adresse import Departage

    dossier = _faits("H2N 1A1", "Laval")
    concurrents = [_faits("H2N 5X9", "Laval"), _faits("H2N 1A1", "Quebec")]
    avant = Departage(DEPARTAGE, rang_avant, 0, ())
    apres = Departage(DEPARTAGE, rang_apres, 1, ())
    expl = da.expliquer_le_deplacement(dossier, concurrents, avant, apres)
    assert not expl.explique and expl.motif == motif


def test_un_ancien_gagnant_SANS_le_fait_fin_nest_pas_EXCLU_mais_INCONNU():
    """⚠️ **« Je ne sais pas » n'est pas « non », ici aussi.**

    *Un ancien gagnant qui ne porte pas de code complet n'est pas réfuté par le
    code complet — il lui est invisible.* **Le déplacement resterait donc
    inexpliqué**, et la cascade ne peut pas le produire : elle aurait rendu
    « un concurrent ne porte pas le fait ».
    """
    from outils.departageur_adresse import Departage

    dossier = _faits("H2N 1A1", "Laval")
    concurrents = [_faits("H2N", "Laval"), _faits("H2N 1A1", "Quebec")]
    expl = da.expliquer_le_deplacement(
        dossier, concurrents,
        Departage(DEPARTAGE, da.NIVEAU_VILLE, 0, ()),
        Departage(DEPARTAGE, da.NIVEAU_CODE_COMPLET, 1, ()),
    )
    assert not expl.explique and expl.motif == da.ANCIEN_NON_EXCLU


def test_le_niveau_DAVANT_est_range_au_rang_de_la_REGION_DE_TRI():
    """⚠️ *Il s'appelait « code postal » et mêlait les deux résolutions, mais sa
    compatibilité était celle de la RÉGION DE TRI.* **Le ranger plus fin qu'il
    n'était ferait passer une correction légitime pour un déplacement
    inexpliqué.**"""
    assert (da.RANG_DES_NIVEAUX[da.NIVEAU_CODE_POSTAL]
            == da.RANG_DES_NIVEAUX[da.NIVEAU_REGION_DE_TRI])
    assert (da.RANG_DES_NIVEAUX[da.NIVEAU_CODE_COMPLET]
            < da.RANG_DES_NIVEAUX[da.NIVEAU_CODE_POSTAL])
