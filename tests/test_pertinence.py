"""Tests du score de pertinence (falkye/pertinence.py) — spec section 6,
restructurée le 2026-09-01 ; spec section 8bis (sphères N:N pondérées + axe
"qui"), 2026-09-03. Logique pure et fixtures minimales, aucune donnée de
prospect réelle (principe directeur #1)."""
from datetime import datetime, timedelta, timezone

from falkye.matching import MatchResult, SphereMatch
from falkye.models.client_cible import ID_AUCUNE_RESTRICTION
from falkye.models.company import Company
from falkye.models.notification import NiveauPertinence
from falkye.models.profile import ProfileNeed
from falkye.models.signal import Signal
from falkye.pertinence import (
    BONUS_QUI_MAX,
    PonderationValeurs,
    base_match_pour_sphere,
    bonus_et_redirection_qui,
    bonus_signal_absence,
    bonus_velocite,
    calculer_pertinence,
    filtrer_champs_pertinents,
    franchit_seuil_sensibilite,
    meilleure_sphere_pour_match,
)


def _need_avec_sphere(sphere_id="gestion_projet", poids=100.0):
    from falkye.models.profile_need_sphere import ProfileNeedSphere

    need = ProfileNeed(profile_id=1, usage_precis="test")
    need.spheres_liees = [ProfileNeedSphere(sphere_id=sphere_id, poids=poids)]
    return need


def _match(sphere_id="gestion_projet", poids=100.0, generique=True, qualitatif=False, need=None):
    """Construit un MatchResult minimal — `generique` détermine si sphere_id
    entre dans spheres_generiques_ids (correspondance via la table
    signal->sphères) ; qualitatif force correspondance_qualitative."""
    need = need or _need_avec_sphere(sphere_id, poids)
    return MatchResult(
        profile_need=need,
        spheres_liees=[SphereMatch(sphere_id=sphere_id, poids=poids)],
        spheres_generiques_ids={sphere_id} if generique else set(),
        correspondance_qualitative=qualitatif,
    )


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


# --- base_match_pour_sphere : les trois tiers ---


def test_base_match_qualitatif_est_le_plus_fort(registry):
    match = _match("rh_recrutement_dotation", qualitatif=True)
    assert base_match_pour_sphere(match, "rh_recrutement_dotation", "recrutement_massif", registry) == 90.0


def test_base_match_sphere_principale_est_intermediaire(registry):
    """classement_croissance liste "gestion_projet" en première position
    (falkye/registry/signal_types.yaml) — donc sphère PRINCIPALE."""
    match = _match("gestion_projet")
    assert base_match_pour_sphere(match, "gestion_projet", "classement_croissance", registry) == 60.0


def test_base_match_sphere_secondaire_est_le_plus_faible(registry):
    """"rh_recrutement_dotation" est listée après "gestion_projet" pour
    classement_croissance — sphère secondaire, pas la principale."""
    match = _match("rh_recrutement_dotation")
    assert base_match_pour_sphere(match, "rh_recrutement_dotation", "classement_croissance", registry) == 30.0


def test_base_match_pour_sphere_none_si_sphere_non_liee(registry):
    match = _match("gestion_projet")
    assert base_match_pour_sphere(match, "sphere_inexistante", "classement_croissance", registry) is None


def test_base_match_pour_sphere_none_si_pas_generique_ni_qualitatif(registry):
    """Sphère liée, mais ni probable pour ce signal ni correspondance
    qualitative — rien à en tirer (comme avant l'évolution plusieurs-à-plusieurs)."""
    match = _match("gestion_projet", generique=False, qualitatif=False)
    assert base_match_pour_sphere(match, "gestion_projet", "classement_croissance", registry) is None


# --- Pondération plusieurs-à-plusieurs (spec section 8bis) ---


def test_base_match_pour_sphere_mis_a_l_echelle_par_le_poids(registry):
    """Un lien à poids 50 (partage exact, ex. le cas Hector) atterrit à
    mi-chemin — un lien à poids 100 se comporte exactement comme avant."""
    match_100 = _match("gestion_projet", poids=100.0)
    match_50 = _match("gestion_projet", poids=50.0)
    assert base_match_pour_sphere(match_100, "gestion_projet", "classement_croissance", registry) == 60.0
    assert base_match_pour_sphere(match_50, "gestion_projet", "classement_croissance", registry) == 30.0


def test_base_match_pour_sphere_qualitatif_jamais_mis_a_l_echelle(registry):
    """Confirmé par Alexandre : la correspondance qualitative est une preuve
    indépendante du poids de la sphère, jamais mise à l'échelle."""
    match_faible_poids = _match("rh_recrutement_dotation", poids=10.0, qualitatif=True)
    assert (
        base_match_pour_sphere(match_faible_poids, "rh_recrutement_dotation", "recrutement_massif", registry)
        == 90.0
    )


def test_meilleure_sphere_pour_match_retient_le_meilleur_score(registry):
    from falkye.models.profile_need_sphere import ProfileNeedSphere

    need = ProfileNeed(profile_id=1, usage_precis="test")
    need.spheres_liees = [
        ProfileNeedSphere(sphere_id="gestion_projet", poids=100.0),  # principale, poids plein -> 60
        ProfileNeedSphere(sphere_id="rh_recrutement_dotation", poids=100.0),  # secondaire, poids plein -> 30
    ]
    match = MatchResult(
        profile_need=need,
        spheres_liees=[SphereMatch(sphere_id="gestion_projet", poids=100.0), SphereMatch(sphere_id="rh_recrutement_dotation", poids=100.0)],
        spheres_generiques_ids={"gestion_projet", "rh_recrutement_dotation"},
        correspondance_qualitative=False,
    )
    score, sphere_id = meilleure_sphere_pour_match(match, "classement_croissance", registry)
    assert sphere_id == "gestion_projet"
    assert score == 60.0


def test_meilleure_sphere_pour_match_aucune_sphere_liee_retourne_none(registry):
    need = ProfileNeed(profile_id=1, usage_precis="test")
    need.spheres_liees = []
    match = MatchResult(profile_need=need, spheres_liees=[], spheres_generiques_ids=set())
    assert meilleure_sphere_pour_match(match, "classement_croissance", registry) == (0.0, None)


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


# --- bonus_et_redirection_qui (spec section 8bis, 2026-09-03) ---


def test_bonus_qui_nul_sans_restriction_declaree():
    assert bonus_et_redirection_qui(["pme_privees_generales"], []) == (0.0, False)


def test_bonus_qui_nul_si_aucune_restriction_liee():
    assert bonus_et_redirection_qui(["pme_privees_generales"], [(ID_AUCUNE_RESTRICTION, 100.0)]) == (0.0, False)


def test_bonus_qui_nul_si_entreprise_inconnue():
    """Absence d'info sur le "qui" de l'entreprise n'est JAMAIS un malus."""
    assert bonus_et_redirection_qui([], [("organismes_publics_institutionnels", 100.0)]) == (0.0, False)


def test_bonus_qui_positif_si_recoupement():
    bonus, hors_profil = bonus_et_redirection_qui(
        ["organismes_publics_institutionnels"], [("organismes_publics_institutionnels", 100.0)]
    )
    assert bonus == BONUS_QUI_MAX
    assert hors_profil is False


def test_bonus_qui_proportionnel_au_poids_du_lien():
    bonus, _ = bonus_et_redirection_qui(
        ["organismes_publics_institutionnels"], [("organismes_publics_institutionnels", 50.0)]
    )
    assert bonus == BONUS_QUI_MAX * 0.5


def test_bonus_qui_desaccord_confirme_redirige_jamais_un_malus():
    bonus, hors_profil = bonus_et_redirection_qui(
        ["pme_privees_generales"], [("organismes_publics_institutionnels", 100.0)]
    )
    assert bonus == 0.0
    assert hors_profil is True


# --- calculer_pertinence (bout en bout) ---


def test_calculer_pertinence_qualitatif_donne_aaa(registry):
    company = _company()
    s = _signal(company, "recrutement_massif", sig_id=1, titre="Chef de projet — implantation ERP/WMS")
    match = _match("rh_recrutement_dotation", qualitatif=True)

    result = calculer_pertinence(company, [s], {s.id: [match]}, "rh_recrutement_dotation", registry)
    assert result.niveau == NiveauPertinence.AAA


def test_calculer_pertinence_sphere_secondaire_seule_donne_a(registry):
    company = _company()
    s = _signal(company, "classement_croissance", sig_id=1)
    match = _match("rh_recrutement_dotation")  # sphère secondaire pour classement_croissance

    result = calculer_pertinence(company, [s], {s.id: [match]}, "rh_recrutement_dotation", registry)
    assert result.niveau == NiveauPertinence.A


def test_calculer_pertinence_poids_sphere_reduit_la_base_mais_pas_les_bonus(registry):
    """spec section 4bis : la rétroaction ("Pas pertinent") réduit le poids de la
    SPHÈRE, pas les bonus signal-par-absence/vélocité — deux mécanismes
    indépendants du choix de sphère (voir docstring de calculer_pertinence)."""
    company = _company()
    s1 = _signal(company, "recrutement_massif", sig_id=1)
    match = _match("financement_acces_capital")

    plein_poids = calculer_pertinence(
        company, [s1], {s1.id: [match]}, "financement_acces_capital", registry, poids_sphere=1.0
    )
    poids_reduit = calculer_pertinence(
        company, [s1], {s1.id: [match]}, "financement_acces_capital", registry, poids_sphere=0.7
    )

    assert poids_reduit.score_pertinence < plein_poids.score_pertinence
    # Le bonus d'absence (financement_expansion absent, un seul signal présent)
    # est identique dans les deux cas — seule la base est affectée par le poids.
    assert poids_reduit.bonus_absence == plein_poids.bonus_absence


def test_calculer_pertinence_respecte_une_ponderation_personnalisee(registry):
    """spec section 4bis, Radar+ "pondération du moteur de score
    personnalisable" — une base_aa personnalisée doit se refléter dans le score,
    et les bonus doivent utiliser les plafonds/pas personnalisés."""
    company = _company()
    s1 = _signal(company, "classement_croissance", sig_id=1)
    match = _match("gestion_projet")  # sphère PRINCIPALE de classement_croissance -> AA

    ponderation_agressive = PonderationValeurs(base_a=30.0, base_aa=99.0, base_aaa=100.0)
    resultat = calculer_pertinence(
        company, [s1], {s1.id: [match]}, "gestion_projet", registry, ponderation=ponderation_agressive
    )
    resultat_defaut = calculer_pertinence(company, [s1], {s1.id: [match]}, "gestion_projet", registry)

    assert resultat.score_pertinence == 99.0
    assert resultat.score_pertinence > resultat_defaut.score_pertinence


def test_base_match_utilise_la_ponderation_fournie(registry):
    match = _match("gestion_projet", qualitatif=True)
    ponderation_custom = PonderationValeurs(base_aaa=42.0)
    assert base_match_pour_sphere(match, "gestion_projet", "recrutement_massif", registry, ponderation_custom) == 42.0


def test_bonus_velocite_utilise_la_ponderation_fournie():
    now = datetime.now(timezone.utc)
    signaux = [
        Signal(id=1, company_id=1, source_id="x", signal_type_id="a", detected_at=now, champs={}),
        Signal(id=2, company_id=1, source_id="x", signal_type_id="b", detected_at=now - timedelta(days=5), champs={}),
    ]
    ponderation_custom = PonderationValeurs(bonus_velocite_max=3.0, bonus_velocite_par_signal=100.0)
    # Sans le plafond personnalisé (3.0), 1 signal rapproché supplémentaire * 100 = 100.
    assert bonus_velocite(signaux, ponderation_custom) == 3.0


def test_calculer_pertinence_absence_augmente_le_score(registry):
    """Le bonus d'absence est un tout-ou-rien dès qu'AU MOINS UN signal existe
    et que le type attendu n'y est pas (voir docstring bonus_signal_absence) —
    donc le vrai contrôle n'est pas "un signal vs deux", mais "le signal
    financement_expansion attendu est présent" vs "il est absent"."""
    match = _match("financement_acces_capital")

    # Contrôle : le signal attendu (financement_expansion) est présent -> pas de bonus.
    company_presence = _company()
    s1 = _signal(company_presence, "recrutement_massif", sig_id=1)
    _signal(company_presence, "financement_expansion", sig_id=2)
    sans_absence = calculer_pertinence(
        company_presence, [s1], {s1.id: [match]}, "financement_acces_capital", registry
    )

    # Le signal attendu est absent -> bonus.
    company_absence = _company()
    s3 = _signal(company_absence, "recrutement_massif", sig_id=3)
    avec_absence = calculer_pertinence(
        company_absence, [s3], {s3.id: [match]}, "financement_acces_capital", registry
    )

    assert avec_absence.score_pertinence > sans_absence.score_pertinence
    assert avec_absence.bonus_absence > 0
    assert sans_absence.bonus_absence == 0


def test_calculer_pertinence_qui_integre_le_bonus_et_le_hors_profil(registry):
    company = _company()
    s1 = _signal(company, "classement_croissance", sig_id=1)
    match = _match("gestion_projet")

    avec_recoupement = calculer_pertinence(
        company, [s1], {s1.id: [match]}, "gestion_projet", registry,
        client_cible_ids_entreprise=["organismes_publics_institutionnels"],
        clients_cibles_lies_besoin=[("organismes_publics_institutionnels", 100.0)],
    )
    assert avec_recoupement.bonus_qui == BONUS_QUI_MAX
    assert avec_recoupement.hors_profil is False

    avec_desaccord = calculer_pertinence(
        company, [s1], {s1.id: [match]}, "gestion_projet", registry,
        client_cible_ids_entreprise=["pme_privees_generales"],
        clients_cibles_lies_besoin=[("organismes_publics_institutionnels", 100.0)],
    )
    assert avec_desaccord.bonus_qui == 0.0
    assert avec_desaccord.hors_profil is True
    # Jamais un malus : le score sans "qui" du tout reste le plancher.
    sans_qui = calculer_pertinence(company, [s1], {s1.id: [match]}, "gestion_projet", registry)
    assert avec_desaccord.score_pertinence == sans_qui.score_pertinence


# --- filtrer_champs_pertinents (spec section 6, "Filtrage par champ, contextuel
# au profil", ajouté le 2026-09-02) ---


def test_filtrer_champs_pertinents_inchange_sans_entree_de_registre(registry):
    """Défaut sûr : aucune entrée déclarée pour (sphère, source) = tous les
    champs comptent, rien n'est retiré — jamais une perte de donnée par simple
    omission de registre (le risque déjà vécu avec la sphère "Financement")."""
    champs = {"secteur_code": "541330", "type_changement": "nouvel_etablissement"}
    resultat = filtrer_champs_pertinents(champs, "gestion_projet", "req", registry)
    assert resultat == champs


def test_filtrer_champs_pertinents_ne_garde_que_les_champs_autorises(registry):
    """efficacite_energetique × req est déclarée dans registry/champs_pertinents.yaml
    avec [secteur_code, secteur_libelle] — adresse doit être retirée de la vue."""
    champs = {
        "secteur_code": "541330",
        "secteur_libelle": "Fabrication de matériel énergétique",
        "adresse": "123 rue Test",
    }
    resultat = filtrer_champs_pertinents(champs, "efficacite_energetique", "req", registry)
    assert resultat == {"secteur_code": "541330", "secteur_libelle": "Fabrication de matériel énergétique"}


def test_filtrer_champs_pertinents_ne_fabrique_pas_une_cle_absente(registry):
    """Une liste blanche déclare des clés PERMISES, pas des clés GARANTIES — si
    secteur_libelle n'a jamais été capté pour ce signal, il ne doit pas
    apparaître comme None inventé dans la vue filtrée."""
    champs = {"secteur_code": "541330"}
    resultat = filtrer_champs_pertinents(champs, "efficacite_energetique", "req", registry)
    assert resultat == {"secteur_code": "541330"}


def test_filtrer_champs_pertinents_gere_un_dict_vide(registry):
    assert filtrer_champs_pertinents({}, "efficacite_energetique", "req", registry) == {}


def test_filtrer_champs_pertinents_inchange_si_sphere_id_est_none(registry):
    """notification.sphere_probable_id peut être None (notifications antérieures
    à la restructuration en deux axes) — aucun filtrage plutôt qu'une erreur."""
    champs = {"secteur_code": "541330", "adresse": "123 rue Test"}
    resultat = filtrer_champs_pertinents(champs, None, "req", registry)
    assert resultat == champs


# --- franchit_seuil_sensibilite (axe pertinence, indépendant de l'axe confiance) ---


def test_franchit_seuil_sensibilite_faible_exige_aaa():
    assert franchit_seuil_sensibilite(NiveauPertinence.AAA, "faible") is True
    assert franchit_seuil_sensibilite(NiveauPertinence.AA, "faible") is False


def test_franchit_seuil_sensibilite_eleve_laisse_passer_a():
    assert franchit_seuil_sensibilite(NiveauPertinence.A, "eleve") is True
