"""Décors partagés de la suite.

**Un test doit passer parce que le code est correct, jamais parce que son
environnement le lui permet.** Le motif s'est produit trois fois en deux jours,
sous trois formes, et il vaut la peine d'être surveillé :

  - *une variable d'environnement présente sur la machine* — sept tests
    vérifiaient une configuration et non un comportement (2026-09-05);
  - *un état que l'opération fautive produit aussi* — un test regardait
    `session.new`, que `flush()` vide comme `commit()`, donc la mutation qui
    remettait un `flush()` passait sans rien casser (2026-09-07);
  - *les privilèges du compte qui lance la suite* — un test rendait un
    répertoire non inscriptible par `chmod 0500`, mais la suite tourne en root
    dans le conteneur de développement et root passe outre les bits de
    permission (2026-09-07). Pour rendre un chemin réellement impossible à
    créer, mettre un FICHIER en guise de parent : `mkdir` lève alors pour tout
    le monde.

La question qui les attrape tous : **quel test tomberait si je défaisais ce que
je viens de faire?** Si la réponse est « aucun », le test ne verrouille rien.
"""
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
