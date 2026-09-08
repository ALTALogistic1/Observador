"""Ce que ces tests protègent : **`create_all` ne voit pas l'intérieur d'une
table qui existe déjà**.

Une colonne ajoutée à un modèle n'apparaît jamais dans une base déjà créée, et
le silence de `create_all` fait croire le contraire. C'est ce qui a laissé la
base de production sans `profiles.desabonne_le` alors que les deux nouvelles
TABLES du même chantier s'y étaient bien créées.
"""
import pytest
from sqlalchemy import create_engine, inspect, text

from outils.migration_colonnes import colonnes_manquantes


@pytest.fixture()
def moteur_en_derive(tmp_path):
    """Une base réelle à laquelle il manque exactement une colonne.

    Fabriquée en RETIRANT la colonne d'une table créée à partir du modèle réel,
    plutôt qu'en écrivant un schéma à la main : un schéma copié se figerait et
    cesserait de représenter le modèle dès la prochaine évolution.
    """
    import falkye.models  # noqa: F401
    from falkye.models.base import Base

    engine = create_engine(f"sqlite:///{tmp_path / 'derive.db'}")
    Base.metadata.create_all(engine)
    with engine.begin() as c:
        c.execute(text("ALTER TABLE profiles DROP COLUMN desabonne_le"))
    return engine


def test_la_colonne_absente_est_reperee(moteur_en_derive):
    manquantes = colonnes_manquantes(moteur_en_derive)
    assert [c.name for c in manquantes["profiles"]] == ["desabonne_le"]


def test_create_all_ne_repare_pas_la_derive(moteur_en_derive):
    """La raison d'être de l'outil, écrite comme un test : si `create_all`
    suffisait un jour, ce test tomberait et l'outil pourrait disparaître."""
    import falkye.models  # noqa: F401
    from falkye.models.base import Base

    Base.metadata.create_all(moteur_en_derive)

    assert "profiles" in colonnes_manquantes(moteur_en_derive)


def test_une_base_a_jour_ne_reporte_rien(tmp_path):
    import falkye.models  # noqa: F401
    from falkye.models.base import Base

    engine = create_engine(f"sqlite:///{tmp_path / 'ajour.db'}")
    Base.metadata.create_all(engine)

    assert colonnes_manquantes(engine) == {}


def test_la_clause_ajoutee_rend_la_colonne_lisible(moteur_en_derive):
    """L'ALTER produit doit être exécutable tel quel — pas seulement bien formé."""
    from outils.migration_colonnes import _clause_ajout

    colonne = colonnes_manquantes(moteur_en_derive)["profiles"][0]
    with moteur_en_derive.begin() as c:
        c.execute(text(_clause_ajout("profiles", colonne)))

    assert "desabonne_le" in {
        col["name"] for col in inspect(moteur_en_derive).get_columns("profiles")
    }
    assert colonnes_manquantes(moteur_en_derive) == {}


def test_une_colonne_obligatoire_sans_defaut_arrete_loutil(moteur_en_derive):
    """Remplir une colonne NOT NULL exige une valeur que personne n'a décidée :
    l'outil s'arrête plutôt que d'en inventer une."""
    from sqlalchemy import Column, String

    from outils.migration_colonnes import _clause_ajout

    obligatoire = Column("obligatoire", String(10), nullable=False)
    with pytest.raises(SystemExit, match="NOT NULL"):
        _clause_ajout("profiles", obligatoire)


# --- Le défaut serveur, sans quoi l'ALTER passe mais la base se relit mal ---


@pytest.fixture()
def moteur_sans_compteur(tmp_path):
    """Base réelle à laquelle il manque `profiles.rebonds_consecutifs` — une
    colonne NOT NULL avec défaut serveur, le cas que l'outil refusait avant."""
    import falkye.models  # noqa: F401
    from falkye.models.base import Base

    from sqlalchemy.orm import Session

    from falkye.models.profile import Profile

    engine = create_engine(f"sqlite:///{tmp_path / 'sans_compteur.db'}")
    Base.metadata.create_all(engine)
    # La ligne existante est insérée par le MODÈLE, pas par un INSERT écrit à la
    # main : un INSERT recopié se fige dès qu'une colonne obligatoire apparaît.
    with Session(engine) as session:
        session.add(Profile(courriel="a@b.c", nom="A"))
        session.commit()
    with engine.begin() as c:
        c.execute(text("ALTER TABLE profiles DROP COLUMN rebonds_consecutifs"))
    return engine


def test_une_colonne_not_null_avec_defaut_serveur_est_ajoutee(moteur_sans_compteur):
    """Sans le DEFAULT dans l'ALTER, la ligne existante porterait NULL dans une
    colonne déclarée NOT NULL — une base qui se relit mal, pire qu'un refus."""
    from outils.migration_colonnes import _clause_ajout

    colonne = colonnes_manquantes(moteur_sans_compteur)["profiles"][0]
    clause = _clause_ajout("profiles", colonne)
    assert "NOT NULL DEFAULT 0" in clause

    with moteur_sans_compteur.begin() as c:
        c.execute(text(clause))
        valeur = c.execute(text("SELECT rebonds_consecutifs FROM profiles")).scalar()

    assert valeur == 0, "la ligne DÉJÀ en base doit porter le défaut, pas NULL"
    assert colonnes_manquantes(moteur_sans_compteur) == {}


def test_un_defaut_python_seul_ne_compte_pas_comme_defaut_serveur():
    """`default=` ne s'applique qu'aux insertions faites par SQLAlchemy : il ne
    remplit jamais les lignes déjà en base."""
    from sqlalchemy import Column, Integer

    from outils.migration_colonnes import _clause_ajout

    python_seulement = Column("compteur", Integer, nullable=False, default=0)
    with pytest.raises(SystemExit, match="NOT NULL"):
        _clause_ajout("profiles", python_seulement)


# --- Les deux cibles — 2026-09-06 ------------------------------------------


def test_la_derive_est_surveillee_du_cote_miroir_aussi(tmp_path):
    """Une seule cible surveillée aurait laissé la moitié du schéma sans
    surveillance : une colonne ajoutée à un modèle miroir n'aurait jamais été
    rapportée, et la dérive y est aussi silencieuse qu'ailleurs."""
    import falkye.models  # noqa: F401
    from falkye.models.base import BaseMiroir

    engine = create_engine(f"sqlite:///{tmp_path / 'miroirs.db'}")
    BaseMiroir.metadata.create_all(engine)
    with engine.begin() as c:
        c.execute(text("ALTER TABLE req_entries DROP COLUMN ville"))

    manquantes = colonnes_manquantes(engine, BaseMiroir.metadata)

    assert [c.name for c in manquantes["req_entries"]] == ["ville"]


def test_les_tables_de_lautre_cible_ne_sont_pas_reportees_comme_manquantes(tmp_path):
    """Sans la métadonnée en paramètre, l'outil aurait cherché les tables du
    produit dans le fichier des miroirs et inversement — un rapport de dérive
    entièrement faux, sur une base pourtant saine."""
    import falkye.models  # noqa: F401
    from falkye.models.base import Base, BaseMiroir

    miroir = create_engine(f"sqlite:///{tmp_path / 'miroirs.db'}")
    BaseMiroir.metadata.create_all(miroir)

    assert colonnes_manquantes(miroir, BaseMiroir.metadata) == {}
    # Les tables du produit sont ABSENTES de cette base : l'outil ne les
    # examine pas plutôt que de les déclarer incomplètes.
    assert colonnes_manquantes(miroir, Base.metadata) == {}


# --- Le même angle mort, un cran plus bas : les INDEX ------------------------


@pytest.fixture()
def moteur_sans_index(tmp_path):
    """Une base réelle à laquelle il manque exactement un index.

    Le cas réel du 2026-09-08 : la chaîne de déploiement avait posé toutes les
    colonnes du chantier 2 et AUCUN de leurs index — `source_run_logs` et
    `journal_exploitation` n'en portaient pas un seul en production.
    """
    import falkye.models  # noqa: F401
    from falkye.models.base import Base

    engine = create_engine(f"sqlite:///{tmp_path / 'sans_index.db'}")
    Base.metadata.create_all(engine)
    with engine.begin() as c:
        c.execute(text("DROP INDEX ix_journal_exploitation_repli_id"))
    return engine


def test_lindex_absent_est_repere(moteur_sans_index):
    from outils.migration_colonnes import index_manquants

    manquants = index_manquants(moteur_sans_index)

    assert [i.name for i in manquants["journal_exploitation"]] == [
        "ix_journal_exploitation_repli_id"
    ]


def test_create_all_ne_repare_pas_non_plus_les_index(moteur_sans_index):
    """La raison d'être de l'ajout, écrite comme un test — jumeau exact de
    `test_create_all_ne_repare_pas_la_derive`, un cran plus bas."""
    import falkye.models  # noqa: F401
    from falkye.models.base import Base
    from outils.migration_colonnes import index_manquants

    Base.metadata.create_all(moteur_sans_index)

    assert "journal_exploitation" in index_manquants(moteur_sans_index)


def test_la_clause_recree_lindex_avec_son_unicite(moteur_sans_index):
    """`repli_id` est UNIQUE, et ce n'est pas de la performance : c'est ce qui
    fait que deux reprises concurrentes du journal de repli se heurtent à la
    base au lieu de se fier chacune à une lecture prise juste avant. Un index
    recréé sans son unicité rendrait la garantie muette."""
    from outils.migration_colonnes import _clause_index, index_manquants

    (index,) = index_manquants(moteur_sans_index)["journal_exploitation"]
    clause = _clause_index(index)
    assert "UNIQUE" in clause

    with moteur_sans_index.begin() as c:
        c.execute(text(clause))
        c.execute(
            text(
                "INSERT INTO journal_exploitation (evenement, moment, repli_id) "
                "VALUES ('cycle_debut', '2026-09-08', 'a')"
            )
        )
    assert index_manquants(moteur_sans_index) == {}

    with pytest.raises(Exception):  # noqa: B017 -- l'unicité doit MORDRE
        with moteur_sans_index.begin() as c:
            c.execute(
                text(
                    "INSERT INTO journal_exploitation (evenement, moment, repli_id) "
                    "VALUES ('cycle_fin', '2026-09-08', 'a')"
                )
            )


def test_une_base_a_jour_ne_reporte_aucun_index(tmp_path):
    import falkye.models  # noqa: F401
    from falkye.models.base import Base
    from outils.migration_colonnes import index_manquants

    engine = create_engine(f"sqlite:///{tmp_path / 'a_jour.db'}")
    Base.metadata.create_all(engine)

    assert index_manquants(engine) == {}
