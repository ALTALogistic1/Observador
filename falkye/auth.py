"""Authentification réelle par utilisateur (mot de passe + session) — CLI
login, ajoutée le 2026-09-02. Prérequis avant de vendre les rôles/sous-comptes
Radar+ comme une vraie séparation (voir falkye/models/sous_compte.py pour le
contexte complet : ce que ça corrige, et la limite honnête qui reste — le
mode opérateur, voir falkye/cli.py::_identite_courante).

Deux types de principal, tous deux authentifiables — le PROPRIÉTAIRE d'un
profil (Profile.mot_de_passe_hash) et un SOUS-COMPTE (SousCompte.
mot_de_passe_hash) : aucun des deux n'était vérifié avant cette fonctionnalité
(un `--profile-id` bare dans falkye/cli.py suffisait à agir sur N'IMPORTE
QUEL profil, pas seulement les sous-comptes — corriger seulement ces derniers
aurait laissé un trou plus large ouvert).

Hachage par hashlib.scrypt (stdlib, aucune nouvelle dépendance) — un KDF
délibérément lent, comme bcrypt/argon2, pour rendre une attaque par force
brute coûteuse même si la base de données fuit. Jeton de session : `secrets.
token_urlsafe` (déjà à haute entropie, pas besoin d'un KDF lent), dont seul le
HASH (sha256) est stocké côté serveur (falkye/models/session_auth.py) — le
jeton BRUT ne vit que dans le fichier local du principal
(~/.falkye/session)."""
from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from falkye.models.profile import Profile
from falkye.models.session_auth import SessionAuth
from falkye.models.sous_compte import RoleSousCompte, SousCompte

# --- Hachage de mot de passe (hashlib.scrypt, stdlib) ---

_SCRYPT_N = 2**14  # coût CPU/mémoire — valeur stdlib recommandée pour un usage interactif
_SCRYPT_R = 8
_SCRYPT_P = 1
_SALT_BYTES = 16


def hacher_mot_de_passe(mot_de_passe: str) -> str:
    """Retourne "scrypt$<sel hex>$<hash hex>" — jamais le mot de passe en
    clair, jamais stocké tel quel nulle part (Profile.mot_de_passe_hash /
    SousCompte.mot_de_passe_hash)."""
    sel = secrets.token_bytes(_SALT_BYTES)
    hache = hashlib.scrypt(mot_de_passe.encode("utf-8"), salt=sel, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return f"scrypt${sel.hex()}${hache.hex()}"


def verifier_mot_de_passe(hash_stocke: str, mot_de_passe: str) -> bool:
    """Compare en temps constant (hmac.compare_digest) — jamais un simple
    `==`, qui fuiterait la position du premier octet différent par timing."""
    try:
        algo, sel_hex, hache_hex = hash_stocke.split("$")
    except ValueError:
        return False
    if algo != "scrypt":
        return False
    sel = bytes.fromhex(sel_hex)
    attendu = bytes.fromhex(hache_hex)
    calcule = hashlib.scrypt(mot_de_passe.encode("utf-8"), salt=sel, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return hmac.compare_digest(calcule, attendu)


def definir_mot_de_passe(principal_obj: Profile | SousCompte, mot_de_passe: str) -> None:
    """Fixe (ou remplace) le mot de passe d'un Profile ou d'un SousCompte —
    ne commit pas, laisse l'appelant gérer sa transaction."""
    principal_obj.mot_de_passe_hash = hacher_mot_de_passe(mot_de_passe)


# --- Principal (identité vérifiée) ---


@dataclass
class Principal:
    """Une identité vérifiée — soit le PROPRIÉTAIRE d'un profil (sous_compte
    est None), soit un sous-compte de ce profil. `.profile` est TOUJOURS
    renseigné (même pour un sous-compte, via sa relation parente) — la
    majorité des commandes CLI, qui n'ont besoin que du profil, n'ont jamais à
    distinguer les deux cas."""

    type: str  # "profile" | "sous_compte"
    profile: Profile
    sous_compte: SousCompte | None = None

    @property
    def role(self) -> RoleSousCompte:
        # Le propriétaire d'un profil a toujours l'équivalent d'un rôle admin
        # — c'est SON compte. Seul un sous-compte porte un rôle restreint.
        return self.sous_compte.role if self.sous_compte else RoleSousCompte.ADMIN

    @property
    def nom_affichage(self) -> str:
        if self.sous_compte:
            return f"{self.sous_compte.nom} (sous-compte, profil #{self.profile.id})"
        return f"{self.profile.nom} (propriétaire, profil #{self.profile.id})"


class AuthentificationError(Exception):
    """Message volontairement générique ("Identifiants invalides.") — ne
    révèle jamais si un courriel existe, si c'est le mot de passe qui est
    faux, ou si le courriel est ambigu (voir authentifier ci-dessous) :
    pratique standard pour ne pas faciliter l'énumération de comptes."""


def _principal_par_courriel(db_session: Session, courriel: str) -> Profile | SousCompte | None:
    """Résout `courriel` vers UN SEUL principal candidat (avant vérification
    du mot de passe) — Profile.courriel OU SousCompte.courriel, dont
    l'unicité globale est garantie au niveau du schéma (voir leurs modèles).
    Retourne None si aucun match ; une ambiguïté (les deux tables matchent,
    ne devrait jamais arriver vu les contraintes d'unicité, mais une donnée
    historique ne doit jamais se résoudre au hasard) est aussi traitée comme
    None — échec net plutôt que deviner."""
    courriel_norm = courriel.strip().lower()
    profile = db_session.execute(
        select(Profile).where(func.lower(Profile.courriel) == courriel_norm)
    ).scalar_one_or_none()
    sous_compte = db_session.execute(
        select(SousCompte).where(func.lower(SousCompte.courriel) == courriel_norm)
    ).scalar_one_or_none()
    if profile is not None and sous_compte is not None:
        return None
    return profile or sous_compte


def authentifier(db_session: Session, courriel: str, mot_de_passe: str) -> Principal:
    """Résout `courriel` vers un principal et vérifie le mot de passe. Lève
    AuthentificationError dans TOUS les cas d'échec (courriel inconnu,
    ambigu, mot de passe incorrect, ou principal sans mot de passe défini) —
    jamais de distinction dans le message ni le type d'exception selon la
    cause précise."""
    candidat = _principal_par_courriel(db_session, courriel)
    if candidat is None:
        raise AuthentificationError("Identifiants invalides.")

    if not candidat.mot_de_passe_hash or not verifier_mot_de_passe(candidat.mot_de_passe_hash, mot_de_passe):
        raise AuthentificationError("Identifiants invalides.")

    if isinstance(candidat, Profile):
        return Principal(type="profile", profile=candidat)
    return Principal(type="sous_compte", profile=candidat.profile, sous_compte=candidat)


# --- Sessions ---

DUREE_SESSION_PAR_DEFAUT = timedelta(days=30)


def _hacher_jeton(jeton: str) -> str:
    return hashlib.sha256(jeton.encode("utf-8")).hexdigest()


def creer_session(db_session: Session, principal: Principal, duree: timedelta = DUREE_SESSION_PAR_DEFAUT) -> str:
    """Crée une session et retourne le jeton BRUT — à écrire dans le fichier
    local du principal (falkye/cli.py::_ecrire_jeton_local), jamais renvoyé
    une deuxième fois : seul son hash persiste ici."""
    jeton = secrets.token_urlsafe(32)
    session_auth = SessionAuth(
        type_principal=principal.type,
        principal_id=principal.sous_compte.id if principal.sous_compte else principal.profile.id,
        jeton_hash=_hacher_jeton(jeton),
        expires_at=datetime.now(timezone.utc) + duree,
    )
    db_session.add(session_auth)
    db_session.commit()
    return jeton


def resoudre_session(db_session: Session, jeton: str) -> Principal | None:
    """Retourne le Principal pour ce jeton, ou None s'il est introuvable,
    expiré, ou révoqué — jamais d'exception ici (un jeton invalide est un
    état attendu, pas une erreur de programmation) ; à l'appelant de décider
    comment réagir (falkye/cli.py : "Non connecté — voir `falkye auth
    login`.")."""
    session_auth = db_session.execute(
        select(SessionAuth).where(SessionAuth.jeton_hash == _hacher_jeton(jeton))
    ).scalar_one_or_none()
    if session_auth is None or session_auth.revoked_at is not None:
        return None

    expires_at = session_auth.expires_at
    if expires_at.tzinfo is None:
        # SQLite renvoie un datetime naïf même si utcnow()/`expires_at` a été
        # écrit avec tzinfo — même précaution que falkye/scoring.py.
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None

    if session_auth.type_principal == "profile":
        profile = db_session.get(Profile, session_auth.principal_id)
        if profile is None:
            return None
        return Principal(type="profile", profile=profile)

    sous_compte = db_session.get(SousCompte, session_auth.principal_id)
    if sous_compte is None:
        return None
    return Principal(type="sous_compte", profile=sous_compte.profile, sous_compte=sous_compte)


def revoquer_session(db_session: Session, jeton: str) -> None:
    """`falkye auth logout` — marque la session révoquée plutôt que de
    supprimer la ligne (garde une trace), résoudre_session la traite ensuite
    comme invalide."""
    session_auth = db_session.execute(
        select(SessionAuth).where(SessionAuth.jeton_hash == _hacher_jeton(jeton))
    ).scalar_one_or_none()
    if session_auth is not None and session_auth.revoked_at is None:
        session_auth.revoked_at = datetime.now(timezone.utc)
        db_session.commit()
