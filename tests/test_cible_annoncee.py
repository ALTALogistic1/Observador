"""Un outil de schéma doit nommer sa cible, et refuser d'en fabriquer une.

Le 2026-09-09, deux outils lancés dans la même session root ont rendu des
verdicts opposés sur le schéma. Ni l'un ni l'autre ne disait à quelle base il
parlait. `migration_colonnes.py` répondait « Schéma à jour des deux côtés » —
sur un fichier vide qu'il venait de créer, où TOUTES les colonnes manquaient.

Deux défauts distincts, deux garde-fous, et chacun a son test :

1. **Le repli est silencieux et relatif au répertoire courant.** Sur l'hôte,
   `/etc/falkye/falkye.env` n'est chargé que par les unités systemd.
2. **Un verdict rendu sur une base vide est le plus rassurant de tous.** La
   comparaison saute les tables absentes — juste sur une base qu'on étend,
   faux sur une base qui n'a rien.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from falkye.db import DEFAULT_DB_URL, cible_annoncee, sur_repli_par_defaut

RACINE = Path(__file__).resolve().parents[1]
DISTANTE = "libsql://falkye-altalogistic.aws-us-east-1.turso.io"


def _lancer(outil: str, repertoire: Path, *args: str) -> subprocess.CompletedProcess:
    """L'outil, sans identifiants — la condition exacte d'un shell root."""
    env = {
        "PATH": "/usr/bin:/bin",
        "PYTHONPATH": str(RACINE),
        "HOME": str(repertoire),
    }
    return subprocess.run(
        [sys.executable, str(RACINE / "outils" / outil), *args],
        cwd=repertoire, env=env, capture_output=True, text=True, check=False,
    )


# --- La cible se nomme, sans jamais l'ouvrir ------------------------------


def test_la_cible_distante_se_nomme_sans_le_jeton():
    """Le jeton n'est pas dans l'URL — il est un argument nommé du pilote. Ce
    test verrouille qu'aucune évolution ne le fasse entrer dans une sortie."""
    ligne = cible_annoncee(DISTANTE)

    assert "distante" in ligne
    assert "libsql://" in ligne
    assert "auth" not in ligne.lower()


def test_le_repli_par_defaut_se_signale_avec_son_chemin_reel():
    """Le chemin relatif est le piège : il change avec le répertoire d'où on
    lance. L'afficher résolu est ce qui rend le fantôme visible."""
    ligne = cible_annoncee(DEFAULT_DB_URL)

    assert "REPLI PAR DÉFAUT" in ligne
    assert "chemin réel" in ligne
    assert "relatif au répertoire courant" in ligne


def test_annoncer_la_cible_ne_cree_aucun_fichier(tmp_path, monkeypatch):
    """**LE test du garde-fou.** Une fonction qui sert à dire « attention,
    mauvaise cible » ne doit pas fabriquer cette cible en le disant.
    `get_engine()`, lui, crée le répertoire du repli."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FALKYE_DB_URL", raising=False)

    cible_annoncee()

    assert list(tmp_path.iterdir()) == []


def test_une_cible_choisie_nest_pas_un_repli(monkeypatch):
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:///./autre.sqlite3")
    assert sur_repli_par_defaut() is False

    monkeypatch.delenv("FALKYE_DB_URL", raising=False)
    assert sur_repli_par_defaut() is True


# --- Les trois outils refusent le repli, et le disent ---------------------


@pytest.mark.parametrize(
    "outil",
    ["migration_colonnes.py", "rapport_cout_cycle.py", "migration_chantier2_execution.py"],
)
def test_un_outil_de_schema_refuse_le_repli_par_defaut(outil, tmp_path):
    fait = _lancer(outil, tmp_path)

    assert fait.returncode == 2, fait.stdout + fait.stderr
    assert "REFUS" in fait.stdout + fait.stderr
    # La cible s'annonce AVANT le refus : le lecteur doit voir ce qui a été visé.
    assert "REPLI PAR DÉFAUT" in fait.stdout


@pytest.mark.parametrize(
    "outil",
    ["migration_colonnes.py", "rapport_cout_cycle.py", "migration_chantier2_execution.py"],
)
def test_un_outil_de_schema_ne_cree_rien_en_refusant(outil, tmp_path):
    """Refuser en créant le fichier qu'on refuse de juger serait le même défaut,
    déplacé d'une ligne."""
    _lancer(outil, tmp_path)

    assert not (tmp_path / "data").exists()


# --- Une base vide ne rend jamais un verdict vert -------------------------


def test_une_base_vide_ne_passe_pas_pour_un_schema_a_jour(tmp_path):
    """Le défaut du 9 septembre, reproduit puis fermé. Zéro table présente
    donnait zéro colonne manquante — donc « Schéma à jour des deux côtés » et
    un code de sortie 0, sur une base où TOUT manquait."""
    fait = _lancer("migration_colonnes.py", tmp_path, "--repli-par-defaut")

    assert fait.returncode == 2, fait.stdout + fait.stderr
    assert "Schéma à jour" not in fait.stdout
    assert "companies" in fait.stdout + fait.stderr
    assert "vide ou étrangère" in fait.stdout + fait.stderr


def test_le_refus_sur_base_vide_dit_pourquoi_le_vert_serait_trompeur(tmp_path):
    """« Table témoin absente » ne dit pas ce qui est en jeu. Le rapport doit
    nommer la conséquence, sinon il se range dans les avertissements."""
    fait = _lancer("migration_colonnes.py", tmp_path, "--repli-par-defaut")

    assert "elles manquent TOUTES" in fait.stdout + fait.stderr
