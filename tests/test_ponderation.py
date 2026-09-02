"""Tests de la pondération personnalisée (falkye/ponderation.py) — spec section
4bis, fonctionnalité Radar+ "pondération du moteur de score personnalisable"."""
from falkye.models.ponderation_personnalisee import PonderationPersonnalisee
from falkye.models.profile import PlanTarifaire, Profile
from falkye.pertinence import PONDERATION_DEFAUT
from falkye.ponderation import ponderation_pour_profil


def _profile(db_session, plan):
    p = Profile(courriel="test@exemple.com", nom="Profil Test", plan=plan)
    db_session.add(p)
    db_session.flush()
    return p


def test_echo_utilise_toujours_la_ponderation_par_defaut(db_session):
    profile = _profile(db_session, PlanTarifaire.ECHO)
    assert ponderation_pour_profil(db_session, profile) == PONDERATION_DEFAUT


def test_radar_utilise_toujours_la_ponderation_par_defaut(db_session):
    profile = _profile(db_session, PlanTarifaire.RADAR)
    assert ponderation_pour_profil(db_session, profile) == PONDERATION_DEFAUT


def test_radar_plus_sans_ligne_utilise_la_ponderation_par_defaut(db_session):
    profile = _profile(db_session, PlanTarifaire.RADAR_PLUS)
    assert ponderation_pour_profil(db_session, profile) == PONDERATION_DEFAUT


def test_radar_plus_avec_ligne_partielle_applique_seulement_les_champs_definis(db_session):
    """Un profil peut n'ajuster QU'UN SEUL facteur — les autres restent aux
    valeurs par défaut de FALKYE (voir docstring de PonderationPersonnalisee)."""
    profile = _profile(db_session, PlanTarifaire.RADAR_PLUS)
    db_session.add(PonderationPersonnalisee(profile_id=profile.id, bonus_velocite_max=50.0))
    db_session.flush()

    pond = ponderation_pour_profil(db_session, profile)
    assert pond.bonus_velocite_max == 50.0
    assert pond.base_a == PONDERATION_DEFAUT.base_a
    assert pond.base_aa == PONDERATION_DEFAUT.base_aa
    assert pond.base_aaa == PONDERATION_DEFAUT.base_aaa


def test_radar_plus_avec_ligne_complete(db_session):
    profile = _profile(db_session, PlanTarifaire.RADAR_PLUS)
    db_session.add(
        PonderationPersonnalisee(
            profile_id=profile.id,
            base_a=10.0, base_aa=50.0, base_aaa=95.0,
            bonus_absence=5.0, bonus_velocite_max=40.0, bonus_velocite_par_signal=10.0,
        )
    )
    db_session.flush()

    pond = ponderation_pour_profil(db_session, profile)
    assert pond.base_a == 10.0
    assert pond.base_aa == 50.0
    assert pond.base_aaa == 95.0
    assert pond.bonus_absence == 5.0
    assert pond.bonus_velocite_max == 40.0
    assert pond.bonus_velocite_par_signal == 10.0


def test_ligne_ignoree_si_le_profil_n_est_plus_radar_plus(db_session):
    """Une ligne enregistrée mais le profil rétrogradé (ex. abonnement annulé) —
    la pondération personnalisée ne s'applique plus, même si la ligne existe
    toujours (spec : réservé à Radar+, pas une propriété permanente du profil)."""
    profile = _profile(db_session, PlanTarifaire.RADAR)
    db_session.add(PonderationPersonnalisee(profile_id=profile.id, base_a=1.0))
    db_session.flush()

    assert ponderation_pour_profil(db_session, profile) == PONDERATION_DEFAUT
