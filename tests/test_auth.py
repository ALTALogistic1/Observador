"""Tests de falkye/auth.py — authentification réelle par utilisateur (mot de
passe + session), ajoutée le 2026-09-02. Voir falkye/models/sous_compte.py
pour le contexte complet (ce que ça corrige)."""
from datetime import timedelta

import pytest

from falkye.auth import (
    AuthentificationError,
    authentifier,
    creer_session,
    definir_mot_de_passe,
    hacher_mot_de_passe,
    resoudre_session,
    revoquer_session,
    verifier_mot_de_passe,
)
from falkye.models.profile import Profile
from falkye.models.sous_compte import RoleSousCompte, SousCompte


def _profile(db_session, courriel="proprio@exemple.com", mot_de_passe=None):
    p = Profile(courriel=courriel, nom="Proprio Test")
    if mot_de_passe:
        definir_mot_de_passe(p, mot_de_passe)
    db_session.add(p)
    db_session.flush()
    return p


def _sous_compte(db_session, profile, courriel="analyste@exemple.com", mot_de_passe=None, role=RoleSousCompte.ANALYSTE):
    sc = SousCompte(profile_id=profile.id, courriel=courriel, nom="Analyste Test", role=role)
    if mot_de_passe:
        definir_mot_de_passe(sc, mot_de_passe)
    db_session.add(sc)
    db_session.flush()
    return sc


# --- Hachage ---


def test_hacher_puis_verifier_reussit_avec_le_bon_mot_de_passe():
    h = hacher_mot_de_passe("correct-horse-battery-staple")
    assert verifier_mot_de_passe(h, "correct-horse-battery-staple") is True


def test_verifier_echoue_avec_un_mauvais_mot_de_passe():
    h = hacher_mot_de_passe("correct-horse-battery-staple")
    assert verifier_mot_de_passe(h, "mauvais-mot-de-passe") is False


def test_deux_hachages_du_meme_mot_de_passe_sont_differents():
    """Sel aléatoire à chaque appel — jamais le même hash pour le même mot de
    passe, même principe que tout KDF avec sel correctement implémenté."""
    assert hacher_mot_de_passe("test") != hacher_mot_de_passe("test")


def test_verifier_echoue_proprement_sur_un_hash_mal_forme():
    assert verifier_mot_de_passe("pas-un-hash-scrypt-valide", "test") is False
    assert verifier_mot_de_passe("", "test") is False


# --- authentifier ---


def test_authentifier_reussit_pour_le_proprietaire_du_profil(db_session):
    _profile(db_session, courriel="alex@exemple.com", mot_de_passe="motdepasse123")
    principal = authentifier(db_session, "alex@exemple.com", "motdepasse123")
    assert principal.type == "profile"
    assert principal.sous_compte is None


def test_authentifier_reussit_pour_un_sous_compte(db_session):
    profile = _profile(db_session)
    _sous_compte(db_session, profile, courriel="colleague@exemple.com", mot_de_passe="autremotdepasse")
    principal = authentifier(db_session, "colleague@exemple.com", "autremotdepasse")
    assert principal.type == "sous_compte"
    assert principal.profile.id == profile.id


def test_authentifier_insensible_a_la_casse_du_courriel(db_session):
    _profile(db_session, courriel="Alex@Exemple.com", mot_de_passe="motdepasse123")
    principal = authentifier(db_session, "alex@exemple.com", "motdepasse123")
    assert principal.type == "profile"


def test_authentifier_leve_pour_un_courriel_inconnu(db_session):
    with pytest.raises(AuthentificationError):
        authentifier(db_session, "inconnu@exemple.com", "peu-importe")


def test_authentifier_leve_pour_un_mauvais_mot_de_passe(db_session):
    _profile(db_session, courriel="alex@exemple.com", mot_de_passe="motdepasse123")
    with pytest.raises(AuthentificationError):
        authentifier(db_session, "alex@exemple.com", "mauvais")


def test_authentifier_leve_si_aucun_mot_de_passe_defini(db_session):
    """Un principal sans mot de passe défini (bootstrap pas encore fait) ne
    peut simplement pas se connecter — pas une erreur de programmation."""
    _profile(db_session, courriel="alex@exemple.com")  # pas de mot de passe
    with pytest.raises(AuthentificationError):
        authentifier(db_session, "alex@exemple.com", "peu-importe")


def test_authentifier_message_generique_peu_importe_la_cause(db_session):
    """Jamais de distinction dans le message — courriel inconnu et mot de
    passe incorrect donnent EXACTEMENT le même message, pour ne pas
    faciliter l'énumération de comptes."""
    _profile(db_session, courriel="alex@exemple.com", mot_de_passe="motdepasse123")
    try:
        authentifier(db_session, "alex@exemple.com", "mauvais")
    except AuthentificationError as exc:
        message_mauvais_mdp = str(exc)
    try:
        authentifier(db_session, "inconnu@exemple.com", "peu-importe")
    except AuthentificationError as exc:
        message_inconnu = str(exc)
    assert message_mauvais_mdp == message_inconnu


# --- Sessions ---


def test_creer_puis_resoudre_session_retourne_le_meme_principal(db_session):
    profile = _profile(db_session, courriel="alex@exemple.com", mot_de_passe="motdepasse123")
    principal = authentifier(db_session, "alex@exemple.com", "motdepasse123")
    jeton = creer_session(db_session, principal)

    resolu = resoudre_session(db_session, jeton)
    assert resolu is not None
    assert resolu.type == "profile"
    assert resolu.profile.id == profile.id


def test_creer_puis_resoudre_session_pour_un_sous_compte(db_session):
    profile = _profile(db_session)
    sc = _sous_compte(db_session, profile, courriel="colleague@exemple.com", mot_de_passe="autremotdepasse")
    principal = authentifier(db_session, "colleague@exemple.com", "autremotdepasse")
    jeton = creer_session(db_session, principal)

    resolu = resoudre_session(db_session, jeton)
    assert resolu is not None
    assert resolu.type == "sous_compte"
    assert resolu.sous_compte.id == sc.id
    assert resolu.profile.id == profile.id


def test_resoudre_session_retourne_none_pour_un_jeton_inconnu(db_session):
    assert resoudre_session(db_session, "jeton-qui-n-existe-pas") is None


def test_resoudre_session_retourne_none_pour_un_jeton_expire(db_session):
    profile = _profile(db_session, courriel="alex@exemple.com", mot_de_passe="motdepasse123")
    principal = authentifier(db_session, "alex@exemple.com", "motdepasse123")
    jeton = creer_session(db_session, principal, duree=timedelta(seconds=-1))  # déjà expiré
    assert resoudre_session(db_session, jeton) is None
    assert profile.id  # supprime un avertissement de variable inutilisée, garde le contexte lisible


def test_resoudre_session_retourne_none_apres_revocation(db_session):
    _profile(db_session, courriel="alex@exemple.com", mot_de_passe="motdepasse123")
    principal = authentifier(db_session, "alex@exemple.com", "motdepasse123")
    jeton = creer_session(db_session, principal)
    assert resoudre_session(db_session, jeton) is not None

    revoquer_session(db_session, jeton)
    assert resoudre_session(db_session, jeton) is None


def test_revoquer_session_est_idempotente(db_session):
    """Un deuxième logout sur un jeton déjà révoqué ne doit pas lever."""
    _profile(db_session, courriel="alex@exemple.com", mot_de_passe="motdepasse123")
    principal = authentifier(db_session, "alex@exemple.com", "motdepasse123")
    jeton = creer_session(db_session, principal)
    revoquer_session(db_session, jeton)
    revoquer_session(db_session, jeton)  # ne doit lever aucune exception


# --- Principal.role / nom_affichage ---


def test_principal_role_du_proprietaire_est_admin(db_session):
    _profile(db_session, courriel="alex@exemple.com", mot_de_passe="motdepasse123")
    principal = authentifier(db_session, "alex@exemple.com", "motdepasse123")
    assert principal.role == RoleSousCompte.ADMIN


def test_principal_role_d_un_sous_compte_est_le_sien():
    from falkye.auth import Principal

    profile = Profile(courriel="p@t.com", nom="P")
    sc = SousCompte(profile_id=1, courriel="s@t.com", nom="S", role=RoleSousCompte.LECTURE_SEULE)
    principal = Principal(type="sous_compte", profile=profile, sous_compte=sc)
    assert principal.role == RoleSousCompte.LECTURE_SEULE
