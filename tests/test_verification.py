"""Tests des vérifications de base obligatoires (falkye/verification.py) —
spec section 6 : exclusion silencieuse, jamais de présentation avec avertissement."""
from falkye.enrichment import EnrichmentResult
from falkye.models.company import Company, StatutLegal, StatutResolution, StatutVerification
from falkye.verification import (
    appliquer_verification,
    verifier_apres_enrichissement,
    verifier_avant_enrichissement,
)


def _company(**kwargs):
    defaults = dict(nom_detecte="Entreprise Test inc.", statut_resolution=StatutResolution.RESOLU, statut_legal=StatutLegal.IMMATRICULEE)
    defaults.update(kwargs)
    return Company(**defaults)


def test_entreprise_radiee_est_exclue_peu_importe_le_reste():
    c = _company(statut_legal=StatutLegal.RADIEE)
    assert verifier_avant_enrichissement(c) == StatutVerification.EXCLU_RADIEE


def test_resolution_ambigue_est_exclue():
    c = _company(statut_resolution=StatutResolution.AMBIGU)
    assert verifier_avant_enrichissement(c) == StatutVerification.EXCLU_RESOLUTION_AMBIGUE


def test_resolution_non_trouvee_est_exclue():
    c = _company(statut_resolution=StatutResolution.NON_TROUVE)
    assert verifier_avant_enrichissement(c) == StatutVerification.EXCLU_RESOLUTION_AMBIGUE


def test_entreprise_saine_sans_enrichissement_est_verifiee():
    c = _company()
    assert verifier_apres_enrichissement(c, enrichment=None) == StatutVerification.VERIFIE


def test_absence_de_site_web_n_exclut_pas(monkeypatch=None):
    c = _company()
    enrichment = EnrichmentResult(site_web=None, trouve=False, indique_inactivite=False)
    assert verifier_apres_enrichissement(c, enrichment) == StatutVerification.VERIFIE


def test_site_indiquant_une_fermeture_exclut():
    c = _company()
    enrichment = EnrichmentResult(site_web="https://exemple.test", trouve=True, indique_inactivite=True)
    assert verifier_apres_enrichissement(c, enrichment) == StatutVerification.EXCLU_SITE_INACTIF


def test_radiee_reste_exclue_meme_si_site_actif():
    c = _company(statut_legal=StatutLegal.RADIEE)
    enrichment = EnrichmentResult(site_web="https://exemple.test", trouve=True, indique_inactivite=False)
    assert verifier_apres_enrichissement(c, enrichment) == StatutVerification.EXCLU_RADIEE


def test_appliquer_verification_met_a_jour_le_statut_sur_company():
    c = _company(statut_legal=StatutLegal.RADIEE)
    statut = appliquer_verification(c, enrichment=None)
    assert statut == StatutVerification.EXCLU_RADIEE
    assert c.statut_verification == StatutVerification.EXCLU_RADIEE
    assert c.est_presentable() is False
