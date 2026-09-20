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
import re
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(autouse=True)
def cible_archive_declaree(tmp_path, monkeypatch):
    """Une cible nommée pour l'archive du diff, dans le répertoire du test.

    **Le fait qui a écrit ce décor** *(2026-09-16)*. `FALKYE_DIFF_ARCHIVE_DIR`
    n'était posée nulle part, et le repli — `./cache/diff_archive` — est
    RELATIF au répertoire courant. *Sur l'hôte, sous `ProtectSystem=strict`,
    l'import du REQ est mort dessus après trente minutes de travail.* **Ici, il
    ne mourait pas : la suite déposait ses archives dans l'arbre de travail du
    dépôt**, invisible parce que `/cache/` est ignoré par git.

    ⚠️ *Un test qui passe parce qu'il a le droit d'écrire là où la production
    ne l'a pas ne verrouille rien* — c'est la troisième forme décrite en tête de
    ce fichier, à un répertoire près.

    **`setattr`, pas `setenv`** : `diff_engine.ARCHIVE_DIR` est lu À L'IMPORT du
    module, donc une variable posée après le chargement n'aurait aucun effet —
    et le test passerait pour la mauvaise raison.
    """
    from falkye import diff_engine

    monkeypatch.setattr(diff_engine, "ARCHIVE_DIR", tmp_path / "diff_archive")


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


def compte_de_la_ligne(ligne: str) -> str:
    """Le nombre d'une ligne de tableau — **lu par MOTIF, jamais par rang de jeton.**

    ⚠️ **Le défaut que ce helper existe pour empêcher, et qui a été commis
    QUATRE fois** *(N144, N158, puis deux récidives)* : `ligne.split()[-2]` sur
    une ligne qui finit par `« 2   66.7 % »` rend **`66.7`**, parce que la part
    se découpe en deux jetons. *Et toute marque ajoutée en fin de ligne —
    `→ repli`, `← surreprésentée`, `⛔ fin` — déplace encore les index.*

    **Il vit dans `conftest.py` parce que c'est le seul endroit que le PROCHAIN
    fichier de test trouvera sans y penser.** *Une note au tampon se relit; elle
    n'empêche rien. Un helper recopié dans trois fichiers ne protège pas le
    quatrième.*
    """
    trouve = re.search(r"[\s:](\d[\d ]*)\s+\d+\.\d %", ligne)
    assert trouve, f"aucun compte lisible dans : {ligne!r}"
    return trouve.group(1).strip()
