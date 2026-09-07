import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    """DEUX bases SQLite en mémoire, comme en production — pas une seule.

    Le produit et les miroirs vivent sur des cibles distinctes depuis le
    2026-09-06 (voir falkye/models/base.py::BaseMiroir). Les réunir ici en une
    seule base rendrait les tests aveugles à la classe de défaut la plus
    probable du découpage : une table rangée du mauvais côté. Avec deux moteurs,
    un modèle miroir laissé sur `Base` voit sa table créée dans la base du
    produit — et toute requête dessus échoue bruyamment.

    Les tables sont créées à partir des modèles réels : pas de schéma recopié à
    la main, qui se figerait à la première colonne ajoutée.
    """
    import falkye.models  # noqa: F401 -- enregistre tous les modèles
    from falkye.models.base import Base, BaseMiroir

    engine = create_engine("sqlite:///:memory:")
    engine_miroir = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    BaseMiroir.metadata.create_all(engine_miroir)

    Session = sessionmaker(binds={Base: engine, BaseMiroir: engine_miroir})
    session = Session()
    # Les modules qui ouvrent leur propre session (cycle, exploitation, CLI)
    # doivent parler aux MÊMES bases que le test, sinon ils écriraient ailleurs
    # sans que rien ne le dise.
    monkeypatch.setattr("falkye.db.get_engine", lambda: engine)
    monkeypatch.setattr("falkye.db.get_engine_miroir", lambda: engine_miroir)
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
