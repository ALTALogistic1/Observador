"""Tests du Niveau 1 de l'assistance à la configuration du profil par IA
(falkye/assistance_sphere.py) — matching local par mots-clés, sans appel API."""
from falkye.assistance_sphere import suggerer_spheres_niveau1
from falkye.models.sphere import Sphere
from falkye.models.sphere_synonyme import SphereSynonyme


def _semer_spheres(db_session):
    db_session.add_all(
        [
            Sphere(id="rh_recrutement_dotation", nom="Ressources humaines / recrutement / dotation"),
            Sphere(id="logistique_transport_flotte", nom="Logistique / transport / gestion de flotte"),
            Sphere(id="cybersecurite", nom="Cybersécurité"),
        ]
    )
    db_session.add_all(
        [
            SphereSynonyme(sphere_id="rh_recrutement_dotation", texte="recrutement", origine="registre"),
            SphereSynonyme(sphere_id="rh_recrutement_dotation", texte="dotation", origine="registre"),
            SphereSynonyme(sphere_id="logistique_transport_flotte", texte="camionnage", origine="registre"),
            SphereSynonyme(sphere_id="logistique_transport_flotte", texte="gestion de flotte", origine="registre"),
            SphereSynonyme(sphere_id="cybersecurite", texte="cybersécurité", origine="registre"),
        ]
    )
    db_session.flush()


def test_trouve_la_sphere_avec_le_plus_de_mots_cles_matches(db_session):
    _semer_spheres(db_session)
    suggestions = suggerer_spheres_niveau1(
        db_session, "Nous faisons du recrutement et de la dotation de personnel spécialisé"
    )
    assert suggestions
    assert suggestions[0].sphere_id == "rh_recrutement_dotation"
    assert suggestions[0].score == 2
    assert set(suggestions[0].mots_cles_matches) == {"recrutement", "dotation"}


def test_correspondance_insensible_a_la_casse(db_session):
    _semer_spheres(db_session)
    suggestions = suggerer_spheres_niveau1(db_session, "Service de CAMIONNAGE longue distance")
    assert suggestions
    assert suggestions[0].sphere_id == "logistique_transport_flotte"


def test_aucune_correspondance_retourne_liste_vide(db_session):
    _semer_spheres(db_session)
    suggestions = suggerer_spheres_niveau1(db_session, "Vente de meubles artisanaux faits main")
    assert suggestions == []


def test_description_vide_retourne_liste_vide(db_session):
    _semer_spheres(db_session)
    assert suggerer_spheres_niveau1(db_session, "") == []
    assert suggerer_spheres_niveau1(db_session, "   ") == []


def test_acronyme_court_ne_matche_pas_a_l_interieur_d_un_mot(db_session):
    """Régression : "TI" ne doit pas matcher dans "implantation" (sous-chaîne
    "...ta-TI-on...") — seule une occurrence bornée par des limites de mot compte."""
    db_session.add(Sphere(id="technologie_systemes_ti", nom="Technologie / systèmes / TI"))
    db_session.add(SphereSynonyme(sphere_id="technologie_systemes_ti", texte="TI", origine="registre"))
    db_session.flush()
    suggestions = suggerer_spheres_niveau1(
        db_session, "Implantation de systèmes de gestion d'inventaire"
    )
    assert suggestions == []


def test_limite_le_nombre_de_suggestions(db_session):
    _semer_spheres(db_session)
    suggestions = suggerer_spheres_niveau1(
        db_session,
        "recrutement, dotation, camionnage, gestion de flotte, cybersécurité",
        limite=2,
    )
    assert len(suggestions) == 2
