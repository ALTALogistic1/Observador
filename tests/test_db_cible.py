"""Résolution de la cible de base de données (chantier 29).

Deux cibles possibles : un fichier SQLite local, ou la base durable distante en
HTTPS. Ces tests portent sur la TRADUCTION de `FALKYE_DB_URL` en moteur — pas
sur la base elle-même, qu'aucun test ne doit joindre.

Le cas qui justifie le fichier : mesuré le 2026-09-04 contre un point d'entrée
vivant, le dialecte `sqlalchemy-libsql` range `authToken` dans la chaîne de
requête de l'URL, mais le pilote ne la lit pas — il attend `auth_token` en
argument NOMMÉ. La conséquence est un `401 empty JWT token` au premier accès à
la base, pas à la connexion : loin du vrai défaut, et donc coûteux à
diagnostiquer. Ces tests figent la forme qui fonctionne."""
import pytest

from falkye import db as db_module

URL_DISTANTE = "libsql://falkye-exemple.aws-us-east-1.turso.io"


@pytest.fixture(autouse=True)
def _moteur_propre():
    """Le moteur est mémorisé au niveau du module : sans remise à zéro, un test
    hérite de la cible du précédent."""
    db_module.reinitialiser_moteur()
    yield
    db_module.reinitialiser_moteur()


def test_url_locale_reste_inchangee(monkeypatch):
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:///./data/falkye.sqlite3")
    url, connect_args = db_module.resoudre_cible(db_module.get_db_url())
    assert url == "sqlite:///./data/falkye.sqlite3"
    assert connect_args == {"check_same_thread": False}
    assert db_module.est_base_distante() is False


def test_url_distante_passe_en_https_et_le_jeton_en_argument_nomme(monkeypatch):
    monkeypatch.setenv("FALKYE_DB_URL", URL_DISTANTE)
    monkeypatch.setenv("FALKYE_DB_AUTH_TOKEN", "jeton-de-test")

    url, connect_args = db_module.resoudre_cible(db_module.get_db_url())

    assert url == "sqlite+libsql://falkye-exemple.aws-us-east-1.turso.io?secure=true"
    assert connect_args["auth_token"] == "jeton-de-test"
    assert db_module.est_base_distante() is True


def test_le_jeton_ne_voyage_jamais_dans_l_url(monkeypatch):
    """La forme qui échoue en 401. Elle doit rester impossible à produire —
    et accessoirement, un jeton dans l'URL finit dans les journaux et les
    messages d'erreur de SQLAlchemy."""
    monkeypatch.setenv("FALKYE_DB_URL", URL_DISTANTE)
    monkeypatch.setenv("FALKYE_DB_AUTH_TOKEN", "jeton-de-test")

    url, _ = db_module.resoudre_cible(db_module.get_db_url())

    assert "authToken" not in url
    assert "jeton-de-test" not in url


def test_url_distante_sans_jeton_echoue_tot_et_explicitement(monkeypatch):
    """Sans ce garde-fou, l'absence de jeton ne se manifeste qu'au premier
    accès à la base, sous la forme d'un 401 opaque."""
    monkeypatch.setenv("FALKYE_DB_URL", URL_DISTANTE)
    monkeypatch.delenv("FALKYE_DB_AUTH_TOKEN", raising=False)

    with pytest.raises(RuntimeError) as erreur:
        db_module.resoudre_cible(db_module.get_db_url())

    assert "FALKYE_DB_AUTH_TOKEN" in str(erreur.value)


def test_jeton_vide_ou_blanc_traite_comme_absent(monkeypatch):
    monkeypatch.setenv("FALKYE_DB_URL", URL_DISTANTE)
    monkeypatch.setenv("FALKYE_DB_AUTH_TOKEN", "   ")

    with pytest.raises(RuntimeError):
        db_module.resoudre_cible(db_module.get_db_url())


def test_get_engine_construit_bien_le_moteur_distant(monkeypatch):
    """Vérifie le chemin complet `get_engine()`, sans jamais ouvrir de
    connexion (SQLAlchemy est paresseux : le moteur se construit sans joindre
    le serveur)."""
    monkeypatch.setenv("FALKYE_DB_URL", URL_DISTANTE)
    monkeypatch.setenv("FALKYE_DB_AUTH_TOKEN", "jeton-de-test")

    moteur = db_module.get_engine()

    assert moteur.dialect.name == "sqlite"
    assert moteur.dialect.driver == "libsql"
    assert "jeton-de-test" not in str(moteur.url)


def test_reinitialiser_moteur_libere_la_cible_precedente(monkeypatch, tmp_path):
    monkeypatch.setenv("FALKYE_DB_URL", f"sqlite:///{tmp_path}/a.sqlite3")
    premier = db_module.get_engine()
    assert db_module.get_engine() is premier  # mémorisé

    db_module.reinitialiser_moteur()
    monkeypatch.setenv("FALKYE_DB_URL", f"sqlite:///{tmp_path}/b.sqlite3")
    assert db_module.get_engine() is not premier
