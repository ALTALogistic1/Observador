"""Tests des tableaux de bord agrégés par territoire (falkye/synthese.py) —
spec section 4bis, "au-delà des prospects un à un, une vue agrégée". Le
`registry` fixture (tests/conftest.py) charge le registre réel, y compris
`registry/secteurs_grossiers.yaml` — la classification par mots-clés testée
ici est donc la même que celle utilisée en production, pas une simulation."""
from falkye.models.company import Company
from falkye.models.notification import ModeUsage, NiveauConfiance, NiveauPertinence, Notification
from falkye.models.profile import ProfileNeed
from falkye.synthese import SECTEUR_NON_CLASSE, SECTEUR_NON_PRECISE, TERRITOIRE_AUCUN, generer_synthese


def _notification(company_id, company, profile_need=None, niveau_pertinence=NiveauPertinence.AA):
    n = Notification(
        company_id=company_id, profile_id=1, mode=ModeUsage.VEILLE_CONTINUE,
        score_confiance=70.0, niveau_confiance=NiveauConfiance.ELEVE,
        niveau_pertinence=niveau_pertinence, justification_resumee="test",
    )
    n.company = company
    n.profile_need = profile_need
    return n


def test_synthese_vide(registry):
    s = generer_synthese([], registry)
    assert s.nb_entreprises == 0


def test_synthese_compte_les_entreprises_distinctes_pas_les_notifications(registry):
    company = Company(nom_detecte="Entreprise A", nom_detecte_normalise="entreprise a")
    n1 = _notification(1, company)
    n2 = _notification(1, company)  # même entreprise, deuxième notification
    s = generer_synthese([n1, n2], registry)
    assert s.nb_entreprises == 1


def test_synthese_repartition_par_secteur_regroupe_par_mots_cles(registry):
    """Deux libellés REQ bruts DIFFÉRENTS mais du même thème (fabrication)
    tombent dans la même catégorie grossière — c'est tout le point du
    regroupement (solution intermédiaire, 2026-09-02) : un libellé exact ne se
    répète presque jamais dans les données réelles."""
    c1 = Company(nom_detecte="A", nom_detecte_normalise="a", secteur_activite_libelle="Manufacturier")
    c2 = Company(
        nom_detecte="B", nom_detecte_normalise="b",
        secteur_activite_libelle="FABRICATION D'ASPIRATEUR CENTRAL",
    )
    c3 = Company(nom_detecte="C", nom_detecte_normalise="c")  # secteur non capté
    s = generer_synthese([_notification(1, c1), _notification(2, c2), _notification(3, c3)], registry)
    assert s.par_secteur["Fabrication / manufacture"] == 2
    assert s.par_secteur[SECTEUR_NON_PRECISE] == 1


def test_synthese_secteur_non_classe_distinct_de_secteur_non_precise(registry):
    """Un libellé PRÉSENT mais qu'aucune catégorie ne reconnaît (~25% des cas
    réels) est compté séparément d'une entreprise SANS secteur du tout — les
    deux ne doivent jamais être confondus (voir Registry.classer_secteur)."""
    c1 = Company(
        nom_detecte="A", nom_detecte_normalise="a",
        secteur_activite_libelle="xyz totalement hors des catégories connues",
    )
    c2 = Company(nom_detecte="B", nom_detecte_normalise="b")  # secteur non capté
    s = generer_synthese([_notification(1, c1), _notification(2, c2)], registry)
    assert s.par_secteur[SECTEUR_NON_CLASSE] == 1
    assert s.par_secteur[SECTEUR_NON_PRECISE] == 1


def test_synthese_secteur_detail_garde_le_libelle_brut(registry):
    """La granularité d'origine n'est jamais perdue — par_secteur_detail garde
    le libellé REQ brut même quand par_secteur regroupe."""
    c1 = Company(nom_detecte="A", nom_detecte_normalise="a", secteur_activite_libelle="Manufacturier")
    c2 = Company(
        nom_detecte="B", nom_detecte_normalise="b",
        secteur_activite_libelle="FABRICATION D'ASPIRATEUR CENTRAL",
    )
    s = generer_synthese([_notification(1, c1), _notification(2, c2)], registry)
    assert s.par_secteur_detail["Manufacturier"] == 1
    assert s.par_secteur_detail["FABRICATION D'ASPIRATEUR CENTRAL"] == 1
    # Regroupées ensemble dans par_secteur, mais distinguables dans le détail.
    assert s.par_secteur["Fabrication / manufacture"] == 2


def test_synthese_repartition_par_niveau_pertinence(registry):
    c1 = Company(nom_detecte="A", nom_detecte_normalise="a")
    c2 = Company(nom_detecte="B", nom_detecte_normalise="b")
    s = generer_synthese([
        _notification(1, c1, niveau_pertinence=NiveauPertinence.AAA),
        _notification(2, c2, niveau_pertinence=None),  # historique
    ], registry)
    assert s.par_niveau_pertinence["AAA"] == 1
    assert s.par_niveau_pertinence["n/d (historique)"] == 1


def test_synthese_repartition_par_territoire(registry):
    c1 = Company(nom_detecte="A", nom_detecte_normalise="a")
    c2 = Company(nom_detecte="B", nom_detecte_normalise="b")
    need_qc = ProfileNeed(profile_id=1, territoire="Québec")
    s = generer_synthese(
        [_notification(1, c1, profile_need=need_qc), _notification(2, c2, profile_need=None)], registry
    )
    assert s.par_territoire["Québec"] == 1
    assert s.par_territoire[TERRITOIRE_AUCUN] == 1
