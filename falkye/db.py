"""Connexion base de données.

SQLite par défaut (fichier local, largement suffisant pour un usage solo en Phase 1) —
voir FALKYE_DB_URL dans .env.example. Le choix technique de la base de données
appartient à l'implémentation (README : "ces choix technique t'appartiennent"). Passer
à PostgreSQL plus tard ne demande qu'un changement d'URL, le code ORM ne présume pas
du moteur.
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from falkye.models.base import Base

DEFAULT_DB_URL = "sqlite:///./data/falkye.sqlite3"


def get_db_url() -> str:
    return os.environ.get("FALKYE_DB_URL", DEFAULT_DB_URL)


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
        connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
        _engine = create_engine(db_url, connect_args=connect_args)
    return _engine


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
