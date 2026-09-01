import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    """Base SQLite en mémoire, tables créées à partir des modèles réels — pas de
    données de prospects fabriquées, seulement le schéma."""
    from falkye.models.base import Base
    import falkye.models  # noqa: F401 -- enregistre tous les modèles

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def registry():
    from falkye.registry.loader import load_registry

    return load_registry()
