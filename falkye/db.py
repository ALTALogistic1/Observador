"""Connexion base de données.

Deux cibles, choisies par `FALKYE_DB_URL` :

  - **fichier SQLite local** (défaut) — `sqlite:///./data/falkye.sqlite3`. Suffit
    pour un usage solo, mais ne survit PAS au recyclage du conteneur : tout état
    de diff écrit là est perdu, et un état de diff perdu perd des signaux
    définitivement (voir falkye/models/etat_diff_source.py).
  - **base gérée compatible SQLite, en HTTPS** — `libsql://<hôte>`, avec le jeton
    dans `FALKYE_DB_AUTH_TOKEN`. C'est la cible durable du chantier 29. Le choix
    du dialecte n'est pas une préférence : l'égress du conteneur est limité au
    port 443, donc aucun PostgreSQL n'est joignable — c'est le PORT qui
    disqualifie PostgreSQL, pas le dialecte.

**Le jeton ne passe PAS par l'URL.** Mesuré le 2026-09-04 contre un point d'entrée
vivant : le dialecte `sqlalchemy-libsql` range `authToken` dans la chaîne de requête
de l'URL qu'il donne à `libsql_experimental.connect()`, mais ce pilote ne lit pas la
chaîne de requête — sa signature porte `auth_token=''` en argument nommé. Résultat
sans ce détour : `401 Unauthorized — empty JWT token`, à la première requête et pas
à la connexion. Le jeton voyage donc par `connect_args`.
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from falkye.models.base import Base

DEFAULT_DB_URL = "sqlite:///./data/falkye.sqlite3"

PREFIXE_LIBSQL = "libsql://"


def get_db_url() -> str:
    return os.environ.get("FALKYE_DB_URL", DEFAULT_DB_URL)


def est_base_distante(db_url: str | None = None) -> bool:
    """Vrai si l'URL désigne la base durable distante plutôt qu'un fichier local.

    Sert aux garde-fous qui doivent se comporter différemment selon la cible —
    typiquement : refuser une opération destructive quand elle porterait sur la
    base durable (voir outils/sonde_persistance.py)."""
    return (db_url if db_url is not None else get_db_url()).startswith(PREFIXE_LIBSQL)


def resoudre_cible(db_url: str) -> tuple[str, dict]:
    """Traduit `FALKYE_DB_URL` en (URL SQLAlchemy, connect_args).

    Échoue TÔT et explicitement quand le jeton manque : sans ce garde-fou, une
    URL distante sans jeton produit un `401 empty JWT token` opaque au premier
    accès à la base, donc loin du vrai défaut."""
    if db_url.startswith(PREFIXE_LIBSQL):
        hote = db_url.removeprefix(PREFIXE_LIBSQL)
        jeton = os.environ.get("FALKYE_DB_AUTH_TOKEN", "").strip()
        if not jeton:
            raise RuntimeError(
                "FALKYE_DB_URL désigne la base distante "
                f"({PREFIXE_LIBSQL}{hote}) mais FALKYE_DB_AUTH_TOKEN est absente ou vide. "
                "Sans jeton, le serveur répond « 401 Unauthorized — empty JWT token » "
                "au premier accès à la base, pas à la connexion."
            )
        # `secure=true` fait bâtir une URL https:// par le dialecte ; le jeton,
        # lui, doit être un argument NOMMÉ du pilote (voir l'en-tête du module).
        return f"sqlite+libsql://{hote}?secure=true", {
            "auth_token": jeton,
            "check_same_thread": False,
        }
    if db_url.startswith("sqlite"):
        return db_url, {"check_same_thread": False}
    return db_url, {}


def _ensure_sqlite_dir(db_url: str) -> None:
    if db_url.startswith("sqlite:///") and not db_url.startswith("sqlite:////"):
        rel_path = db_url.removeprefix("sqlite:///")
        Path(rel_path).parent.mkdir(parents=True, exist_ok=True)


_engine = None
_SessionLocal: sessionmaker | None = None


def get_engine():
    global _engine
    if _engine is None:
        db_url = get_db_url()
        _ensure_sqlite_dir(db_url)
        url_sqlalchemy, connect_args = resoudre_cible(db_url)
        _engine = create_engine(url_sqlalchemy, connect_args=connect_args)
    return _engine


def reinitialiser_moteur() -> None:
    """Oublie le moteur et la fabrique de sessions mémorisés.

    Le moteur est mémorisé au niveau du module : sans ce point d'entrée, un test
    qui change `FALKYE_DB_URL` continue de parler à la cible précédente."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def get_sessionmaker() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SessionLocal


def get_session() -> Session:
    return get_sessionmaker()()


def init_db() -> None:
    """Crée les tables manquantes. Pas d'outil de migration en Phase 1 (prototype
    mono-utilisateur) — à introduire (Alembic) avant tout usage multi-utilisateur
    ou production."""
    import falkye.models  # noqa: F401 -- garantit que tous les modèles sont importés

    Base.metadata.create_all(get_engine())


def seed_spheres_from_registry() -> None:
    """Synchronise la table Sphere avec le registre YAML (spheres.yaml), sans jamais
    toucher aux sphères personnalisées ajoutées par les utilisateurs (est_personnalisee=True)."""
    from falkye.models.sphere import Sphere
    from falkye.registry.loader import get_registry

    registry = get_registry()
    session = get_session()
    try:
        existing_ids = {s.id for s in session.query(Sphere.id).all()}
        for sphere_def in registry.spheres.values():
            if sphere_def.id not in existing_ids:
                session.add(Sphere(id=sphere_def.id, nom=sphere_def.nom, est_personnalisee=False))
        session.commit()
    finally:
        session.close()


def seed_sphere_synonymes_from_registry() -> None:
    """Synchronise la table SphereSynonyme avec registry/spheres.yaml (champ
    `synonymes`), sans jamais toucher aux synonymes appris par le Niveau 2 de
    l'assistance IA (origine="ia_niveau2" — spec Radar+, point 8) : seules les
    entrées origine="registre" sont gérées ici, même principe que
    seed_spheres_from_registry pour les sphères personnalisées. Idempotent :
    ignore les paires (sphere_id, texte) déjà présentes."""
    from falkye.models.sphere_synonyme import SphereSynonyme
    from falkye.registry.loader import get_registry

    registry = get_registry()
    session = get_session()
    try:
        existants = {
            (s.sphere_id, s.texte.lower())
            for s in session.query(SphereSynonyme.sphere_id, SphereSynonyme.texte)
            .filter(SphereSynonyme.origine == "registre")
            .all()
        }
        for sphere_def in registry.spheres.values():
            for texte in sphere_def.synonymes:
                cle = (sphere_def.id, texte.lower())
                if cle not in existants:
                    session.add(
                        SphereSynonyme(sphere_id=sphere_def.id, texte=texte, origine="registre")
                    )
                    existants.add(cle)
        session.commit()
    finally:
        session.close()


def seed_clients_cibles_from_registry() -> None:
    """Synchronise la table ClientCible avec registry/clients_cibles.yaml —
    même principe que seed_spheres_from_registry (spec section 8bis,
    2026-09-03)."""
    from falkye.models.client_cible import ClientCible
    from falkye.registry.loader import get_registry

    registry = get_registry()
    session = get_session()
    try:
        existing_ids = {c.id for c in session.query(ClientCible.id).all()}
        for client_cible_def in registry.clients_cibles.values():
            if client_cible_def.id not in existing_ids:
                session.add(
                    ClientCible(id=client_cible_def.id, nom=client_cible_def.nom, est_personnalisee=False)
                )
        session.commit()
    finally:
        session.close()


def seed_client_cible_synonymes_from_registry() -> None:
    """Synchronise la table ClientCibleSynonyme avec registry/clients_cibles.yaml
    (champ `synonymes`) — même principe que seed_sphere_synonymes_from_registry :
    seules les entrées origine="registre" sont gérées ici, jamais les synonymes
    appris par le Niveau 2 (origine="ia_niveau2"). Idempotent."""
    from falkye.models.client_cible_synonyme import ClientCibleSynonyme
    from falkye.registry.loader import get_registry

    registry = get_registry()
    session = get_session()
    try:
        existants = {
            (s.client_cible_id, s.texte.lower())
            for s in session.query(ClientCibleSynonyme.client_cible_id, ClientCibleSynonyme.texte)
            .filter(ClientCibleSynonyme.origine == "registre")
            .all()
        }
        for client_cible_def in registry.clients_cibles.values():
            for texte in client_cible_def.synonymes:
                cle = (client_cible_def.id, texte.lower())
                if cle not in existants:
                    session.add(
                        ClientCibleSynonyme(
                            client_cible_id=client_cible_def.id, texte=texte, origine="registre"
                        )
                    )
                    existants.add(cle)
        session.commit()
    finally:
        session.close()


def seed_statuts_suivi_from_registry() -> None:
    """Synchronise la table StatutSuivi avec le registre YAML (statuts_suivi.yaml),
    sans jamais toucher aux statuts personnalisés ajoutés par les utilisateurs
    (est_personnalise=True) — même principe que seed_spheres_from_registry."""
    from falkye.models.statut_suivi import StatutSuivi
    from falkye.registry.loader import get_registry

    registry = get_registry()
    session = get_session()
    try:
        existing_ids = {s.id for s in session.query(StatutSuivi.id).all()}
        for statut_def in registry.statuts_suivi.values():
            if statut_def.id not in existing_ids:
                session.add(StatutSuivi(id=statut_def.id, nom=statut_def.nom, est_personnalise=False))
        session.commit()
    finally:
        session.close()
