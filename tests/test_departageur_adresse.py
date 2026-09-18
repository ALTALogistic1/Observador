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
# LE PREMIER NIVEAU — le code postal, et ses deux formes
# ---------------------------------------------------------------------------

def test_le_code_postal_tranche_SEUL_quand_il_suffit():
    """*« Le code postal, en premier et seul s'il le faut. »*"""
    d = da.departager_ladresse(
        _faits("Levis, QC G7A 2B2", "Levis"),
        [_faits("100 rue X G6V 1A1", "Levis"), _faits("200 rue Y G7A 2B2", "Levis")],
    )
    assert d.issue == DEPARTAGE
    assert d.niveau == da.NIVEAU_CODE_POSTAL
    assert d.gagnant == 1
    # ⚠️ La ville n'a pas été consultée : elle n'aurait rien séparé ici (même
    # ville des deux côtés), et surtout **c'est fini**.
    assert d.par_niveau == ((da.NIVEAU_CODE_POSTAL, DEPARTAGE),)


def test_un_code_TRONQUE_tranche_sur_la_region_de_tri():
    """⚠️ *L'EIMT écrit `'St-Isidore, QC J0L  2A'` — cinq caractères sur six.*"""
    d = da.departager_ladresse(
        _faits("St-Isidore, QC J0L  2A", None),
        [_faits("1 rue A H2X 1Y4", None), _faits("2 rue B J0L 2A1", None)],
    )
    assert (d.issue, d.niveau, d.gagnant) == (DEPARTAGE, da.NIVEAU_CODE_POSTAL, 1)


def test_aucun_code_ne_sinvente_par_FENETRE_GLISSANTE():
    """⚠️ *`STISIDOREQCJ0L2A` contient `L2A`, qui n'est pas une région de tri.*"""
    assert codes_postaux("St-Isidore QC") is None


# ---------------------------------------------------------------------------
# LE REPLI — trois portes ouvertes, une fermée
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("dossier_cp, concurrents_cp, issue_attendue", [
    # le dossier ne porte pas de code postal
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
    assert d.issue_du_niveau(da.NIVEAU_CODE_POSTAL) == issue_attendue
    assert (d.issue, d.niveau, d.gagnant) == (DEPARTAGE, da.NIVEAU_VILLE, 1)


def test_la_ville_NE_PARLE_PAS_quand_le_code_postal_les_exclut_TOUS():
    """⚠️ **La règle la plus importante du module.**

    *Le code postal du dossier dément tous les candidats. Laisser la ville
    désigner un gagnant rendrait un départage dont on sait déjà qu'un fait plus
    précis le contredit.*
    """
    d = da.departager_ladresse(
        _faits("Levis, QC G7A 2B2", "Levis"),
        # la ville, elle, désignerait le second sans hésiter
        [_faits("1 rue A H2X 1Y4", "Laval"), _faits("2 rue B G6V 1A1", "Levis")],
    )
    assert d.issue == AUCUN_COMPATIBLE
    assert d.niveau is None and d.gagnant is None
    # ⚠️ Le second niveau n'a pas été CONSULTÉ — pas « consulté et muet ».
    assert d.par_niveau == ((da.NIVEAU_CODE_POSTAL, AUCUN_COMPATIBLE),)
    assert d.issue_du_niveau(da.NIVEAU_VILLE) is None


def test_le_repli_dit_par_quel_maillon_le_premier_niveau_a_echoue():
    """*« La ville a séparé » ne dit pas si le code postal était muet ou bloqué
    par « inconnu ≠ non » — et ce sont deux correctifs différents.*"""
    d = da.departager_ladresse(
        _faits("G6V 1A1", "Levis"),
        [_faits(None, "Laval"), _faits("G6V 1A1", "Levis")],
    )
    assert d.par_niveau == (
        (da.NIVEAU_CODE_POSTAL, SANS_FAIT_CHEZ_UN_CONCURRENT),
        (da.NIVEAU_VILLE, DEPARTAGE),
    )


def test_aucun_niveau_ne_tranche_reste_un_RESULTAT():
    d = da.departager_ladresse(
        _faits(None, None), [_faits("G6V 1A1", "Levis"), _faits("H2X 1Y4", "Laval")]
    )
    assert d.issue == SANS_FAIT_AU_DOSSIER
    assert not d.prononce


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


def test_un_ambigu_passe_la_garde_et_se_departage():
    matches = [_Match("A", 95.0, cp="H2X 1Y4"), _Match("B", 94.0, cp="G6V 1A1")]
    d, concurrents = da.departager_le_dossier(matches, _faits("G6V 1A1", None))
    assert len(concurrents) == 2
    assert (d.issue, d.niveau, d.gagnant) == (DEPARTAGE, da.NIVEAU_CODE_POSTAL, 1)


def test_les_concurrents_sont_ceux_a_MOINS_DE_LECART_du_meilleur():
    """*C'est exactement l'ensemble sur lequel un abaissement de l'écart
    trancherait à l'aveugle.*"""
    from falkye.resolution import SEUIL_AMBIGUITE_ECART_MIN

    matches = [_Match("A", 95.0), _Match("B", 94.0), _Match("C", 95.0 - SEUIL_AMBIGUITE_ECART_MIN)]
    assert [m.entry.neq for m in da.concurrents_de(matches)] == ["A", "B"]


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
