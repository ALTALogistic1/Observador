"""Ce que ces tests protègent : **une table rangée du mauvais côté**.

Depuis le 2026-09-06, le produit et les miroirs vivent sur deux cibles
distinctes — la base distante pour les ~3 000 lignes qui ne se reconstruisent
pas, un fichier local pour les 5,7 millions de lignes qui se refont (voir
falkye/models/base.py::BaseMiroir).

Deux cibles, deux façons de se tromper, et les deux seraient SILENCIEUSES :

  - une table miroir laissée sur `Base` partirait dans la base distante. Son
    import prendrait environ 168 heures au lieu de 33 minutes et consommerait
    2,7 millions d'écritures facturées — sans erreur, seulement de la lenteur;
  - une table produit passée sur `BaseMiroir` atterrirait dans un fichier local
    que rien ne sauvegarde. Elle disparaîtrait au premier disque perdu, et c'est
    exactement ce que le chantier 29 existe pour empêcher.

D'où une liste EXPLICITE des tables attendues de chaque côté. Elle est
redondante avec le code — c'est le but : une redondance qu'il faut mettre à jour
sciemment rend le déplacement d'une table visible en revue, là où un test
calculé à partir des mêmes classes ne prouverait que la cohérence du code avec
lui-même.
"""
import pytest
from sqlalchemy import create_engine, inspect

import falkye.models  # noqa: F401 -- enregistre tous les modèles
from falkye.models.base import Base, BaseMiroir

# --- La cible de chaque table, écrite à la main -----------------------------

TABLES_MIROIR = {
    # Miroirs de sources : reconstruits par un import du fichier d'origine.
    "req_entries",
    "req_etablissements",
    "corporations_federales_entries",
    "licences_municipales_entries",
    # État de diff : reconstruit par un run de référence sur la source.
    "etat_ligne_source",
    "etat_schema_source",
    "diff_run_historique",
    "diff_quarantaines",
}

TABLES_PRODUIT = {
    "profiles",
    "profile_needs",
    "profile_need_spheres",
    "profile_need_clients_cibles",
    "sous_comptes",
    "sessions_auth",
    "companies",
    "signals",
    "notifications",
    "notification_signals",
    "notification_deliveries",
    "periodic_summaries",
    "livraisons_resume",
    "jetons_lien",
    "journal_exploitation",
    "journal_diagnostic",
    "source_run_logs",
    "spheres",
    "sphere_synonymes",
    "clients_cibles",
    "client_cible_synonymes",
    "statuts_suivi",
    "retroaction_pertinence",
    "ponderations_personnalisees",
    "subscriptions",
    "crm_connections",
    "crm_sync_records",
    "liens_interprovinciaux",
}


def test_les_tables_miroir_sont_exactement_celles_attendues():
    assert set(BaseMiroir.metadata.tables) == TABLES_MIROIR


def test_les_tables_produit_sont_exactement_celles_attendues():
    """Une table NEUVE fait échouer ce test, et c'est voulu : sa cible est une
    décision, pas un défaut de la base déclarative dont on a hérité par
    copier-coller."""
    assert set(Base.metadata.tables) == TABLES_PRODUIT


def test_aucune_table_ne_vit_des_deux_cotes():
    """Le même nom dans les deux métadonnées créerait deux tables homonymes sur
    deux cibles, et la session en choisirait une sans que rien ne le dise."""
    assert set(Base.metadata.tables) & set(BaseMiroir.metadata.tables) == set()


# --- Ce que la création produit réellement ---------------------------------


@pytest.fixture()
def deux_moteurs(tmp_path):
    """Deux fichiers DISTINCTS — c'est la seule façon de voir où chaque table
    atterrit vraiment."""
    produit = create_engine(f"sqlite:///{tmp_path / 'produit.db'}")
    miroir = create_engine(f"sqlite:///{tmp_path / 'miroirs.db'}")
    Base.metadata.create_all(produit)
    BaseMiroir.metadata.create_all(miroir)
    return produit, miroir


def test_la_creation_range_chaque_table_du_bon_cote(deux_moteurs):
    produit, miroir = deux_moteurs

    tables_produit = set(inspect(produit).get_table_names())
    tables_miroir = set(inspect(miroir).get_table_names())

    assert TABLES_MIROIR <= tables_miroir
    assert TABLES_MIROIR & tables_produit == set(), (
        "une table miroir créée dans la base du produit partirait au distant — "
        "168 heures d'import au lieu de 33 minutes"
    )
    assert TABLES_PRODUIT <= tables_produit
    assert TABLES_PRODUIT & tables_miroir == set(), (
        "une table produit créée dans le fichier local ne serait pas sauvegardée"
    )


def test_le_miroir_req_est_du_cote_miroir(deux_moteurs):
    """Nommément vérifié parce que c'est LA table qui a motivé le découpage :
    2,73 M lignes, 33 minutes en local, environ 168 heures au distant."""
    produit, miroir = deux_moteurs

    assert "req_entries" in inspect(miroir).get_table_names()
    assert "req_entries" not in inspect(produit).get_table_names()


# --- Le routage d'une session liée aux deux --------------------------------


def test_une_session_route_chaque_modele_vers_son_moteur(db_session):
    """La propriété qui rend le découpage invisible aux appelants : aucune des
    59 utilisations de `get_session()` n'a eu à changer."""
    from falkye.models.company import Company
    from falkye.models.req_entry import REQEntry

    moteur_produit = db_session.get_bind(Company)
    moteur_miroir = db_session.get_bind(REQEntry)

    assert moteur_produit is not moteur_miroir


def test_les_deux_cotes_secrivent_et_se_relisent_dans_la_meme_session(db_session):
    """Le cas réel : l'ingestion écrit une entreprise (produit) et une entrée de
    miroir (miroir) dans la même unité de travail."""
    from falkye.models.company import Company
    from falkye.models.req_entry import REQEntry

    db_session.add(
        Company(nom_detecte="Transport Bourassa", nom_detecte_normalise="transport bourassa")
    )
    db_session.add(
        REQEntry(
            neq="1160000001",
            nom="Transport Bourassa inc.",
            nom_normalise="transport bourassa inc",
            statut="immatriculee",
        )
    )
    db_session.commit()

    assert db_session.get(REQEntry, "1160000001").nom == "Transport Bourassa inc."
    assert db_session.query(Company).count() == 1


# --- La cible par défaut ----------------------------------------------------


def test_les_miroirs_ne_suivent_jamais_la_base_du_produit(monkeypatch):
    """`FALKYE_MIROIR_DB_URL` est INDÉPENDANTE de `FALKYE_DB_URL` à dessein.

    Faire dériver l'une de l'autre — « si le produit est au distant, les miroirs
    aussi » — aurait rendu le découpage implicite, et un déploiement l'aurait
    défait sans qu'on s'en aperçoive.
    """
    from falkye.db import get_miroir_db_url

    monkeypatch.setenv("FALKYE_DB_URL", "libsql://falkye-exemple.turso.io")
    monkeypatch.delenv("FALKYE_MIROIR_DB_URL", raising=False)

    assert get_miroir_db_url().startswith("sqlite:///")
