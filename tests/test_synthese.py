"""Tests des tableaux de bord agrégés par territoire (falkye/synthese.py) —
spec section 4bis, "au-delà des prospects un à un, une vue agrégée"."""
from falkye.models.company import Company
from falkye.models.notification import ModeUsage, NiveauConfiance, NiveauPertinence, Notification
from falkye.models.profile import ProfileNeed
from falkye.synthese import SECTEUR_NON_PRECISE, TERRITOIRE_AUCUN, generer_synthese


def _notification(company_id, company, profile_need=None, niveau_pertinence=NiveauPertinence.AA):
    n = Notification(
        company_id=company_id, profile_id=1, mode=ModeUsage.VEILLE_CONTINUE,
        score_confiance=70.0, niveau_confiance=NiveauConfiance.ELEVE,
        niveau_pertinence=niveau_pertinence, justification_resumee="test",
    )
    n.company = company
    n.profile_need = profile_need
    return n


def test_synthese_vide():
    s = generer_synthese([])
    assert s.nb_entreprises == 0


def test_synthese_compte_les_entreprises_distinctes_pas_les_notifications():
    company = Company(nom_detecte="Entreprise A", nom_detecte_normalise="entreprise a")
    n1 = _notification(1, company)
    n2 = _notification(1, company)  # même entreprise, deuxième notification
    s = generer_synthese([n1, n2])
    assert s.nb_entreprises == 1


def test_synthese_repartition_par_secteur():
    c1 = Company(nom_detecte="A", nom_detecte_normalise="a", secteur_activite_libelle="Manufacturier")
    c2 = Company(nom_detecte="B", nom_detecte_normalise="b", secteur_activite_libelle="Manufacturier")
    c3 = Company(nom_detecte="C", nom_detecte_normalise="c")  # secteur non capté
    s = generer_synthese([_notification(1, c1), _notification(2, c2), _notification(3, c3)])
    assert s.par_secteur["Manufacturier"] == 2
    assert s.par_secteur[SECTEUR_NON_PRECISE] == 1


def test_synthese_repartition_par_niveau_pertinence():
    c1 = Company(nom_detecte="A", nom_detecte_normalise="a")
    c2 = Company(nom_detecte="B", nom_detecte_normalise="b")
    s = generer_synthese([
        _notification(1, c1, niveau_pertinence=NiveauPertinence.AAA),
        _notification(2, c2, niveau_pertinence=None),  # historique
    ])
    assert s.par_niveau_pertinence["AAA"] == 1
    assert s.par_niveau_pertinence["n/d (historique)"] == 1


def test_synthese_repartition_par_territoire():
    c1 = Company(nom_detecte="A", nom_detecte_normalise="a")
    c2 = Company(nom_detecte="B", nom_detecte_normalise="b")
    need_qc = ProfileNeed(profile_id=1, sphere_id="x", territoire="Québec")
    s = generer_synthese([_notification(1, c1, profile_need=need_qc), _notification(2, c2, profile_need=None)])
    assert s.par_territoire["Québec"] == 1
    assert s.par_territoire[TERRITOIRE_AUCUN] == 1
