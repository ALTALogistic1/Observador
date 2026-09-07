"""Ce que ces tests protègent : **les deux refus qui doivent arriver AVANT
qu'on ait touché à quoi que ce soit**.

L'import du miroir tourne sur le serveur, sans personne devant l'écran. Ses deux
modes de panne ne lèvent aucune erreur d'eux-mêmes :

  - sans `FALKYE_MIROIR_DB_URL`, le miroir vise un chemin relatif hors des
    répertoires que l'unité peut écrire, et l'erreur parlerait de permissions
    plutôt que de la variable manquante;
  - pointé sur la base distante, il tournerait ~168 heures au lieu de 33 minutes
    en consommant 2,7 millions d'écritures facturées — sans erreur, juste de la
    lenteur, découverte bien plus tard.

Les deux doivent donc échouer *bruyamment et tôt*, et le message doit nommer ce
qu'il faut corriger.
"""
import hashlib

import pytest

from outils.import_miroir_req import ImportImpossible, verifier_archive, verifier_cible


# --- La cible ---------------------------------------------------------------


def test_sans_variable_le_refus_nomme_la_variable_et_le_chemin(monkeypatch):
    monkeypatch.delenv("FALKYE_MIROIR_DB_URL", raising=False)

    with pytest.raises(ImportImpossible) as echec:
        verifier_cible()

    message = str(echec.value)
    assert "FALKYE_MIROIR_DB_URL" in message
    assert "/var/lib/falkye/miroirs.sqlite3" in message


def test_la_base_distante_est_refusee(monkeypatch):
    """Le garde-fou central de ce script : viser le distant ne produirait
    aucune erreur, seulement sept jours d'import."""
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "libsql://falkye-exemple.turso.io")

    with pytest.raises(ImportImpossible, match="168 heures"):
        verifier_cible()


def test_une_variable_vide_compte_comme_absente(monkeypatch):
    """`FALKYE_MIROIR_DB_URL=` dans un fichier d'environnement définit la
    variable à la chaîne vide — l'oubli le plus probable, et il ne doit pas
    passer pour une configuration."""
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "   ")

    with pytest.raises(ImportImpossible, match="n'est pas définie"):
        verifier_cible()


def test_un_fichier_local_est_accepte(monkeypatch):
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////var/lib/falkye/miroirs.sqlite3")

    assert verifier_cible() == "sqlite:////var/lib/falkye/miroirs.sqlite3"


# --- L'archive --------------------------------------------------------------


@pytest.fixture()
def archive(tmp_path):
    chemin = tmp_path / "JeuDonnees.zip"
    chemin.write_bytes(b"contenu d'archive")
    return chemin, hashlib.sha256(b"contenu d'archive").hexdigest()


def test_une_archive_absente_arrete_avant_tout(tmp_path):
    with pytest.raises(ImportImpossible, match="introuvable"):
        verifier_archive(tmp_path / "absente.zip", None)


def test_lempreinte_qui_correspond_laisse_passer(archive):
    chemin, empreinte = archive

    assert verifier_archive(chemin, empreinte) == empreinte


def test_une_empreinte_differente_arrete_limport(archive):
    """Un transfert tronqué produirait un ZIP partiellement lisible : l'import
    ne planterait pas, il chargerait un miroir incomplet."""
    chemin, _ = archive

    with pytest.raises(ImportImpossible, match="rien n'a été importé"):
        verifier_archive(chemin, "0" * 64)


def test_sans_empreinte_attendue_larchive_passe_mais_son_empreinte_est_rendue(archive):
    """Le contrôle est facultatif — mais l'empreinte réelle est toujours
    calculée et remontée, pour qu'elle apparaisse au journal du service."""
    chemin, empreinte = archive

    assert verifier_archive(chemin, None) == empreinte
