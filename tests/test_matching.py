"""Tests de la correspondance signal -> sphère et mots-clés (falkye/matching.py)."""
from datetime import datetime, timezone

from falkye.matching import correspondance_qualitative_titre, match_profile, spheres_probables
from falkye.models.profile import Profile, ProfileNeed
from falkye.models.profile_need_sphere import ProfileNeedSphere
from falkye.sources.base import RawSignal


def _need(sphere_id="gestion_projet", poids=100.0, usage_precis="test", territoire=None, profile_id=1):
    """Construit un ProfileNeed avec UN lien sphère (spec section 8bis, lien
    plusieurs-à-plusieurs) — objets Python nus, sans session, comme le reste
    de ce fichier."""
    need = ProfileNeed(
        profile_id=profile_id, usage_precis=usage_precis, territoire=territoire, type_besoin="offre"
    )
    need.spheres_liees = [ProfileNeedSphere(sphere_id=sphere_id, poids=poids)]
    return need


def test_spheres_probables_appel_offres(registry):
    spheres = spheres_probables("appel_offres", registry)
    assert "gestion_projet" in spheres


def test_spheres_probables_type_inconnu_retourne_liste_vide(registry):
    assert spheres_probables("signal_qui_n_existe_pas", registry) == []


def test_spheres_probables_financement_expansion_inclut_financement_acces_capital(registry):
    """Régression du bogue trouvé le 2026-09-02 (question d'Alexandre) :
    financement_acces_capital existait dans spheres.yaml (avec
    signal_absence_pertinent) mais n'avait jamais été ajoutée ici — un profil
    configuré sur cette sphère ne recevait donc AUCUNE notification via le
    chemin générique de match_profile, seulement via bonus_signal_absence
    (falkye/pertinence.py), qui suppose déjà un autre match."""
    assert "financement_acces_capital" in spheres_probables("financement_expansion", registry)


def test_match_profile_financement_acces_capital_matche_un_signal_financement(registry):
    """Bout en bout (pas seulement spheres_probables) : un profil sur cette
    sphère doit maintenant produire un MatchResult pour un signal
    financement_expansion, alors que ce n'était pas le cas avant le correctif."""
    profile = Profile(courriel="test@exemple.com", nom="Profil Test")
    need = _need(sphere_id="financement_acces_capital", usage_precis="cautionnement")
    profile.besoins = [need]

    raw = RawSignal(
        signal_type_id="financement_expansion",
        nom_entreprise="Entreprise Test Inc.",
        detected_at=datetime.now(timezone.utc),
        source_ref="ref-1",
    )

    matches = match_profile(raw, profile, registry)
    assert len(matches) == 1
    assert matches[0].sphere_generique is True
    assert matches[0].spheres_generiques_ids == {"financement_acces_capital"}


def test_correspondance_qualitative_detecte_mot_cle_profil():
    trouves = correspondance_qualitative_titre(
        "Chef de projet — implantation ERP/WMS", mots_cles_profil=["implantation erp"]
    )
    assert any("implantation" in m for m in trouves)


def test_correspondance_qualitative_detecte_base_transformation_sans_mots_cles_profil():
    trouves = correspondance_qualitative_titre("Directeur de la transformation", mots_cles_profil=[])
    assert trouves  # doit matcher la base MOTS_CLES_TRANSFORMATION même sans mot-clé utilisateur


def test_correspondance_qualitative_titre_neutre_ne_matche_rien():
    trouves = correspondance_qualitative_titre("Commis aux ventes", mots_cles_profil=["implantation erp"])
    assert trouves == []


def test_correspondance_qualitative_titre_absent():
    assert correspondance_qualitative_titre(None, mots_cles_profil=["implantation"]) == []


# --- Sphères multiples pondérées (spec section 8bis, 2026-09-03) ---


def test_match_profile_matche_via_n_importe_laquelle_des_spheres_liees(registry):
    """Un besoin peut être lié à plusieurs sphères à la fois — un signal
    matche dès qu'UNE SEULE d'entre elles est probable pour ce type de
    signal, peu importe son poids."""
    profile = Profile(courriel="test@exemple.com", nom="Profil Test")
    need = ProfileNeed(profile_id=1, usage_precis="test", type_besoin="offre")
    need.spheres_liees = [
        ProfileNeedSphere(sphere_id="gestion_projet", poids=50.0),
        ProfileNeedSphere(sphere_id="rh_recrutement_dotation", poids=50.0),
    ]
    profile.besoins = [need]

    raw = RawSignal(
        signal_type_id="appel_offres",
        nom_entreprise="Entreprise Test Inc.",
        detected_at=datetime.now(timezone.utc),
        source_ref="ref-1",
    )
    matches = match_profile(raw, profile, registry)
    assert len(matches) == 1
    assert matches[0].spheres_generiques_ids == {"gestion_projet"}
    # Les deux liens restent portés par le match (pour l'attribution qualitative
    # éventuelle), même si un seul est probable pour CE signal précis.
    assert {sm.sphere_id for sm in matches[0].spheres_liees} == {"gestion_projet", "rh_recrutement_dotation"}


def test_match_profile_besoin_sans_sphere_liee_ne_matche_que_par_mots_cles(registry):
    """Un besoin sans AUCUNE sphère liée (pas encore configuré côté "quoi")
    ne peut jamais matcher via la table générique — seule une correspondance
    qualitative (mots-clés) peut encore produire un MatchResult."""
    profile = Profile(courriel="test@exemple.com", nom="Profil Test")
    need = ProfileNeed(profile_id=1, usage_precis="test", mots_cles="implantation", type_besoin="offre")
    need.spheres_liees = []
    profile.besoins = [need]

    raw = RawSignal(
        signal_type_id="recrutement_massif",
        nom_entreprise="Entreprise Test Inc.",
        detected_at=datetime.now(timezone.utc),
        source_ref="ref-1",
        titre_ou_description="Directeur implantation ERP",
    )
    matches = match_profile(raw, profile, registry)
    assert len(matches) == 1
    assert matches[0].spheres_generiques_ids == set()
    assert matches[0].correspondance_qualitative is True


# --- Territoire par besoin (spec section 4bis, "Profils de recherche multiples
# simultanés") ---


def _profile_avec_besoin(sphere_id="gestion_projet", territoire=None):
    profile = Profile(courriel="test@exemple.com", nom="Profil Test")
    need = _need(sphere_id=sphere_id, territoire=territoire)
    profile.besoins = [need]
    return profile, need


def _raw(signal_type_id="classement_croissance", ville=None, region=None):
    return RawSignal(
        signal_type_id=signal_type_id,
        nom_entreprise="Entreprise Test Inc.",
        detected_at=datetime.now(timezone.utc),
        source_ref="ref-1",
        ville=ville,
        region=region,
    )


def test_match_profile_sans_territoire_ignore_la_localisation(registry):
    """Comportement historique préservé : un besoin sans territoire matche
    peu importe où est l'entreprise (Profile.ville/region ne filtraient déjà
    rien avant cette fonctionnalité)."""
    profile, _ = _profile_avec_besoin(territoire=None)
    raw = _raw(ville="Toronto", region="Ontario")
    assert len(match_profile(raw, profile, registry)) == 1


def test_match_profile_avec_territoire_matche_si_ville_correspond(registry):
    profile, _ = _profile_avec_besoin(territoire="Montréal")
    raw = _raw(ville="Montréal", region="Québec")
    assert len(match_profile(raw, profile, registry)) == 1


def test_match_profile_avec_territoire_matche_si_region_correspond(registry):
    profile, _ = _profile_avec_besoin(territoire="Ontario")
    raw = _raw(ville="Toronto", region="Ontario")
    assert len(match_profile(raw, profile, registry)) == 1


def test_match_profile_avec_territoire_rejette_si_aucune_correspondance(registry):
    profile, _ = _profile_avec_besoin(territoire="Ontario")
    raw = _raw(ville="Montréal", region="Québec")
    assert match_profile(raw, profile, registry) == []


def test_match_profile_deux_besoins_meme_sphere_territoires_differents(registry):
    """Le cas central de la spec : recrutement-QC et recrutement-ON sous un
    seul profil, chacun une combinaison indépendante."""
    profile = Profile(courriel="test@exemple.com", nom="Profil Test")
    need_qc = _need(sphere_id="gestion_projet", usage_precis="QC", territoire="Québec")
    need_on = _need(sphere_id="gestion_projet", usage_precis="ON", territoire="Ontario")
    profile.besoins = [need_qc, need_on]

    raw_qc = _raw(ville="Québec", region="Québec")
    matches = match_profile(raw_qc, profile, registry)
    assert len(matches) == 1
    assert matches[0].profile_need.usage_precis == "QC"
