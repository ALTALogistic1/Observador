"""Tests de falkye/statut_suivi.py::appliquer_statut — factorisé le 2026-09-02
(intégration CRM) pour être partagé entre le tableau de bord
(falkye/cli.py::dashboard_statut) et le sondage retour CRM
(falkye/crm_sync.py::sonder_statuts_crm) : même règle de rétroaction peu
importe l'origine du changement de statut."""
from falkye.models.notification import ModeUsage, NiveauConfiance, NiveauPertinence, Notification
from falkye.models.profile import Profile
from falkye.models.sphere import Sphere
from falkye.statut_suivi import appliquer_statut


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


def _notification(db_session, profile, sphere_id="gestion_projet"):
    n = Notification(
        company_id=1, profile_id=profile.id, mode=ModeUsage.VEILLE_CONTINUE,
        score_confiance=50.0, niveau_confiance=NiveauConfiance.MOYEN,
        score_pertinence=60.0, niveau_pertinence=NiveauPertinence.AA,
        sphere_probable_id=sphere_id, justification_resumee="test",
    )
    db_session.add(n)
    db_session.flush()
    return n


def test_appliquer_statut_change_le_statut(db_session, registry):
    profile = _profile(db_session)
    n = _notification(db_session, profile)
    appliquer_statut(db_session, n, "a_joindre", registry)
    assert n.statut_suivi_id == "a_joindre"


def test_appliquer_statut_declenche_la_retroaction_pour_pas_pertinent(db_session, registry):
    """"pas_pertinent" est le seul statut déclencheur de rétroaction dans le
    registre réel (voir tests/test_registry.py)."""
    profile = _profile(db_session)
    _sphere(db_session)
    n = _notification(db_session, profile)

    retroaction_appliquee = appliquer_statut(db_session, n, "pas_pertinent", registry)

    assert retroaction_appliquee is True
    assert n.statut_suivi_id == "pas_pertinent"


def test_appliquer_statut_ne_declenche_pas_la_retroaction_pour_un_autre_statut(db_session, registry):
    profile = _profile(db_session)
    n = _notification(db_session, profile)
    retroaction_appliquee = appliquer_statut(db_session, n, "a_joindre", registry)
    assert retroaction_appliquee is False


def test_appliquer_statut_leve_pas_pour_un_statut_inconnu_au_registre():
    """Ne valide PAS que statut_id existe dans le registre — l'appelant décide
    comment réagir (ClickException en CLI, id ignoré pour un sondage
    automatisé). Un id absent de registry.statuts_suivi ne déclenche
    simplement jamais de rétroaction (statut_def est None)."""
    from falkye.models.notification import ModeUsage as _ModeUsage
    from falkye.registry.loader import get_registry

    n = Notification(
        company_id=1, profile_id=1, mode=_ModeUsage.VEILLE_CONTINUE,
        score_confiance=50.0, niveau_confiance=NiveauConfiance.MOYEN,
        justification_resumee="test",
    )
    retroaction_appliquee = appliquer_statut(None, n, "statut_inexistant_xyz", get_registry())
    assert retroaction_appliquee is False
    assert n.statut_suivi_id == "statut_inexistant_xyz"
