"""Tests de la rétroaction de pertinence (falkye/retroaction.py) — spec section
4bis, "Lien avec la rétroaction utilisateur". Granularité sphère (voir
falkye/models/retroaction_pertinence.py pour la décision documentée)."""
from falkye.models.notification import ModeUsage, Notification, NiveauConfiance, NiveauPertinence
from falkye.models.profile import Profile
from falkye.models.sphere import Sphere
from falkye.retroaction import (
    PAS_REDUCTION,
    POIDS_PAR_DEFAUT,
    POIDS_PLANCHER,
    enregistrer_pas_pertinent,
    poids_pour_sphere,
)


def _profile(db_session):
    p = Profile(courriel="test@exemple.com", nom="Profil Test")
    db_session.add(p)
    db_session.flush()
    return p


def _sphere(db_session, sphere_id="gestion_projet"):
    s = db_session.get(Sphere, sphere_id)
    if s is None:
        s = Sphere(id=sphere_id, nom=sphere_id)
        db_session.add(s)
        db_session.flush()
    return s


def _notification(db_session, profile, sphere_id, company_id=1):
    n = Notification(
        company_id=company_id,
        profile_id=profile.id,
        mode=ModeUsage.VEILLE_CONTINUE,
        score_confiance=50.0,
        niveau_confiance=NiveauConfiance.MOYEN,
        score_pertinence=60.0,
        niveau_pertinence=NiveauPertinence.AA,
        sphere_probable_id=sphere_id,
        justification_resumee="test",
    )
    db_session.add(n)
    db_session.flush()
    return n


def test_poids_par_defaut_est_1_sans_retroaction(db_session):
    profile = _profile(db_session)
    assert poids_pour_sphere(db_session, profile.id, "gestion_projet") == POIDS_PAR_DEFAUT


def test_un_marquage_reduit_le_poids_d_un_pas(db_session):
    profile = _profile(db_session)
    _sphere(db_session)
    n = _notification(db_session, profile, "gestion_projet")

    enregistrer_pas_pertinent(db_session, n)

    poids = poids_pour_sphere(db_session, profile.id, "gestion_projet")
    assert poids == round(POIDS_PAR_DEFAUT - PAS_REDUCTION, 10)


def test_marquages_repetes_ne_descendent_jamais_sous_le_plancher(db_session):
    profile = _profile(db_session)
    _sphere(db_session)
    for i in range(20):
        n = _notification(db_session, profile, "gestion_projet", company_id=i + 1)
        enregistrer_pas_pertinent(db_session, n)

    poids = poids_pour_sphere(db_session, profile.id, "gestion_projet")
    assert poids == POIDS_PLANCHER


def test_retroaction_est_isolee_par_sphere(db_session):
    profile = _profile(db_session)
    _sphere(db_session, "gestion_projet")
    _sphere(db_session, "rh_recrutement_dotation")

    n = _notification(db_session, profile, "gestion_projet")
    enregistrer_pas_pertinent(db_session, n)

    assert poids_pour_sphere(db_session, profile.id, "gestion_projet") < POIDS_PAR_DEFAUT
    assert poids_pour_sphere(db_session, profile.id, "rh_recrutement_dotation") == POIDS_PAR_DEFAUT


def test_retroaction_est_isolee_par_profil(db_session):
    profile_a = _profile(db_session)
    profile_b = Profile(courriel="autre@exemple.com", nom="Profil B")
    db_session.add(profile_b)
    db_session.flush()
    _sphere(db_session)

    n = _notification(db_session, profile_a, "gestion_projet")
    enregistrer_pas_pertinent(db_session, n)

    assert poids_pour_sphere(db_session, profile_a.id, "gestion_projet") < POIDS_PAR_DEFAUT
    assert poids_pour_sphere(db_session, profile_b.id, "gestion_projet") == POIDS_PAR_DEFAUT


def test_enregistrer_pas_pertinent_ignore_notification_sans_sphere(db_session):
    """Notification antérieure au système de pertinence (sphere_probable_id
    NULL) — rien à quoi rattacher la rétroaction, pas une erreur."""
    profile = _profile(db_session)
    n = Notification(
        company_id=1,
        profile_id=profile.id,
        mode=ModeUsage.VEILLE_CONTINUE,
        score_confiance=50.0,
        niveau_confiance=NiveauConfiance.MOYEN,
        sphere_probable_id=None,
        justification_resumee="test",
    )
    db_session.add(n)
    db_session.flush()

    enregistrer_pas_pertinent(db_session, n)  # ne doit lever aucune exception
