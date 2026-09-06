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


@pytest.fixture(autouse=True)
def environnement_isole(monkeypatch):
    """Aucun test ne doit dépendre de l'environnement de qui le lance.

    `FALKYE_LIEN_BASE_URL` gouverne les liens de désabonnement, et sans elle le
    résumé refuse de partir — à raison. Posée ici pour toute la suite : sans
    ça, les tests passaient sur la machine qui avait la variable et échouaient
    ailleurs, ce qui aurait vérifié une configuration plutôt qu'un
    comportement. Un test qui veut éprouver son ABSENCE la retire lui-même
    (`monkeypatch.delenv`), ce qui rend cette intention visible.
    """
    monkeypatch.setenv("FALKYE_LIEN_BASE_URL", "https://lien.exemple.test")


@pytest.fixture()
def registry():
    from falkye.registry.loader import load_registry

    return load_registry()
