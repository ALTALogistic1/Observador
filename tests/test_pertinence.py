"""Tests du score de pertinence (falkye/pertinence.py) — spec section 6,
restructurée le 2026-09-01. Logique pure et fixtures minimales, aucune donnée de
prospect réelle (principe directeur #1)."""
from datetime import datetime, timedelta, timezone

from falkye.matching import MatchResult
from falkye.models.company import Company
from falkye.models.notification import NiveauPertinence
from falkye.models.profile import ProfileNeed
from falkye.models.signal import Signal
from falkye.pertinence import (
    base_match,
    bonus_signal_absence,
    bonus_velocite,
    calculer_pertinence,
    franchit_seuil_sensibilite,
)


def _need(sphere_id="gestion_projet"):
    return ProfileNeed(profile_id=1, sphere_id=sphere_id, service_precis="test")


def _company(nom="Entreprise Test Inc."):
    return Company(nom_detecte=nom, nom_detecte_normalise=nom.lower())


def _signal(company, signal_type_id, detected_at=None, sig_id=1, titre=None):
    s = Signal(
        id=sig_id,
        company_id=1,
        source_id="test_source",
        signal_type_id=signal_type_id,
        source_ref=f"ref-{sig_id}",
        detected_at=detected_at or datetime.now(timezone.utc),
        titre_ou_description=titre,
        champs={},
    )
    company.signals.append(s)
    return s


# --- base_match : les trois tiers ---


def test_base_match_qualitatif_est_le_plus_fort(registry):
    match = MatchResult(profile_need=_need(), sphere_generique=True, correspondance_qualitative=True)
    assert base_match(match, "recrutement_massif", registry) == 90.0


def test_base_match_sphere_principale_est_intermediaire(registry):
    """classement_croissance liste "gestion_projet" en première position
    (falkye/registry/signal_types.yaml) — donc sphère PRINCIPALE."""
    match = MatchResult(profile_need=_need("gestion_projet"), sphere_generique=True, correspondance_qualitative=False)
    assert base_match(match, "classement_croissance", registry) == 60.0


def test_base_match_sphere_secondaire_est_le_plus_faible(registry):
    """"rh_recrutement_dotation" est listée après "gestion_projet" pour
    classement_croissance — sphère secondaire, pas la principale."""
    match = MatchResult(
        profile_need=_need("rh_recrutement_dotation"), sphere_generique=True, correspondance_qualitative=False
    )
    assert base_match(match, "classement_croissance", registry) == 30.0


# --- bonus_signal_absence ---


def test_bonus_absence_present_si_signal_attendu_manque(registry):
    """Cas réel du persona investisseur providentiel (spec section 6) :
    croissance visible (recrutement) mais AUCUN financement — traction précoce."""
    company = _company()
    _signal(company, "recrutement_massif", sig_id=1)
    bonus = bonus_signal_absence(company, "financement_acces_capital", registry)
    assert bonus > 0


def test_bonus_absence_nul_si_signal_attendu_present(registry):
    company = _company()
    _signal(company, "recrutement_massif", sig_id=1)
    _signal(company, "financement_expansion", sig_id=2)
    bonus = bonus_signal_absence(company, "financement_acces_capital", registry)
    assert bonus == 0.0


def test_bonus_absence_nul_si_aucun_signal_du_tout(registry):
    """Pas de signal du tout = rien à comparer, pas un cas "d'absence
    pertinente" (voir docstring bonus_signal_absence)."""
    company = _company()
    assert bonus_signal_absence(company, "financement_acces_capital", registry) == 0.0


def test_bonus_absence_nul_pour_une_sphere_sans_regle_declaree(registry):
    company = _company()
    _signal(company, "recrutement_massif", sig_id=1)
    assert bonus_signal_absence(company, "gestion_projet", registry) == 0.0


# --- bonus_velocite ---


def test_bonus_velocite_nul_pour_un_seul_signal():
    now = datetime.now(timezone.utc)
    s1 = Signal(id=1, company_id=1, source_id="x", signal_type_id="y", detected_at=now, champs={})
    assert bonus_velocite([s1]) == 0.0


def test_bonus_velocite_positif_pour_signaux_rapproches():
    now = datetime.now(timezone.utc)
    signaux = [
        Signal(id=1, company_id=1, source_id="x", signal_type_id="a", detected_at=now, champs={}),
        Signal(id=2, company_id=1, source_id="x", signal_type_id="b", detected_at=now - timedelta(days=10), champs={}),
        Signal(id=3, company_id=1, source_id="x", signal_type_id="c", detected_at=now - timedelta(days=20), champs={}),
    ]
    assert bonus_velocite(signaux) > 0.0


def test_bonus_velocite_nul_pour_signaux_etales_sur_longue_periode():
    """"une entreprise avec 3 signaux étalés sur 2 ans" (spec section 6) —
    aucun ne tombe dans la même fenêtre de 60 jours."""
    now = datetime.now(timezone.utc)
    signaux = [
        Signal(id=1, company_id=1, source_id="x", signal_type_id="a", detected_at=now, champs={}),
        Signal(id=2, company_id=1, source_id="x", signal_type_id="b", detected_at=now - timedelta(days=365), champs={}),
        Signal(id=3, company_id=1, source_id="x", signal_type_id="c", detected_at=now - timedelta(days=700), champs={}),
    ]
    assert bonus_velocite(signaux) == 0.0


def test_bonus_velocite_trois_signaux_rapproches_plus_fort_que_deux():
    now = datetime.now(timezone.utc)
    deux = [
        Signal(id=1, company_id=1, source_id="x", signal_type_id="a", detected_at=now, champs={}),
        Signal(id=2, company_id=1, source_id="x", signal_type_id="b", detected_at=now - timedelta(days=5), champs={}),
    ]
    trois = deux + [
        Signal(id=3, company_id=1, source_id="x", signal_type_id="c", detected_at=now - timedelta(days=10), champs={})
    ]
    assert bonus_velocite(trois) > bonus_velocite(deux)


# --- calculer_pertinence (bout en bout) ---


def test_calculer_pertinence_qualitatif_donne_aaa(registry):
    company = _company()
    s = _signal(company, "recrutement_massif", sig_id=1, titre="Chef de projet — implantation ERP/WMS")
    need = _need("rh_recrutement_dotation")
    match = MatchResult(profile_need=need, sphere_generique=True, correspondance_qualitative=True, mots_cles_trouves=["implantation"])

    result = calculer_pertinence(company, [s], {s.id: [match]}, need.sphere_id, registry)
    assert result.niveau == NiveauPertinence.AAA


def test_calculer_pertinence_sphere_secondaire_seule_donne_a(registry):
    company = _company()
    s = _signal(company, "classement_croissance", sig_id=1)
    need = _need("rh_recrutement_dotation")  # sphère secondaire pour classement_croissance
    match = MatchResult(profile_need=need, sphere_generique=True, correspondance_qualitative=False)

    result = calculer_pertinence(company, [s], {s.id: [match]}, need.sphere_id, registry)
    assert result.niveau == NiveauPertinence.A


def test_calculer_pertinence_absence_augmente_le_score(registry):
    """Le bonus d'absence est un tout-ou-rien dès qu'AU MOINS UN signal existe
    et que le type attendu n'y est pas (voir docstring bonus_signal_absence) —
    donc le vrai contrôle n'est pas "un signal vs deux", mais "le signal
    financement_expansion attendu est présent" vs "il est absent"."""
    need = _need("financement_acces_capital")
    match = MatchResult(profile_need=need, sphere_generique=True, correspondance_qualitative=False)

    # Contrôle : le signal attendu (financement_expansion) est présent -> pas de bonus.
    company_presence = _company()
    s1 = _signal(company_presence, "recrutement_massif", sig_id=1)
    _signal(company_presence, "financement_expansion", sig_id=2)
    sans_absence = calculer_pertinence(company_presence, [s1], {s1.id: [match]}, need.sphere_id, registry)

    # Le signal attendu est absent -> bonus.
    company_absence = _company()
    s3 = _signal(company_absence, "recrutement_massif", sig_id=3)
    avec_absence = calculer_pertinence(company_absence, [s3], {s3.id: [match]}, need.sphere_id, registry)

    assert avec_absence.score_pertinence > sans_absence.score_pertinence
    assert avec_absence.bonus_absence > 0
    assert sans_absence.bonus_absence == 0


# --- franchit_seuil_sensibilite (axe pertinence, indépendant de l'axe confiance) ---


def test_franchit_seuil_sensibilite_faible_exige_aaa():
    assert franchit_seuil_sensibilite(NiveauPertinence.AAA, "faible") is True
    assert franchit_seuil_sensibilite(NiveauPertinence.AA, "faible") is False


def test_franchit_seuil_sensibilite_eleve_laisse_passer_a():
    assert franchit_seuil_sensibilite(NiveauPertinence.A, "eleve") is True
