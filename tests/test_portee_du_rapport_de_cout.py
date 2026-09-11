"""La portée d'un instrument s'affiche à côté de sa sortie.

Le 2026-09-11, `rapport_cout_cycle.py` a rendu **zéro sur les trois chemins**
pour un cycle dont le compteur de l'hébergeur a mesuré **411 963 777 lectures**.
L'instrument ne mentait pas : il comptait exactement ce qu'il avait été construit
pour compter — les trois chemins de résolution d'identité — et le consommateur
réel était ailleurs (le chargement des signaux par `company_id`, une requête par
entreprise, sur une colonne sans index).

**Forme neuve du motif du projet : un instrument JUSTE, dont la portée est plus
étroite que ce qu'on croyait qu'il couvrait.** Sans sa portée écrite à côté de sa
sortie, son zéro se lit comme une absence de coût. *(journal, cas 33)*
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]

PREPARATION = """
import sys
from datetime import datetime, timezone
sys.path.insert(0, {racine!r})
from falkye.db import get_session, init_db
from falkye.models.run_log import SourceRunLog

init_db()
s = get_session()
s.add(
    SourceRunLog(
        source_id="eimt", mode="veille_continue", statut="succes",
        started_at=datetime.now(timezone.utc).replace(tzinfo=None),
        finished_at=datetime.now(timezone.utc).replace(tzinfo=None),
        duree_ms=1000,
        nb_resolutions_exact=0, nb_resolutions_prefixe=0, nb_resolutions_sous_chaine=0,
    )
)
s.commit()
s.close()
"""


def _env(repertoire: Path) -> dict:
    return {
        "PATH": "/usr/bin:/bin",
        "PYTHONPATH": str(RACINE),
        "HOME": str(repertoire),
        "FALKYE_DB_URL": f"sqlite:///{repertoire}/produit.sqlite3",
        "FALKYE_MIROIR_DB_URL": f"sqlite:///{repertoire}/miroirs.sqlite3",
    }


def _un_cycle_a_zero(repertoire: Path) -> subprocess.CompletedProcess:
    """Une exécution réelle, trois compteurs à zéro — le 11 septembre en petit."""
    env = _env(repertoire)
    prep = subprocess.run(
        [sys.executable, "-c", PREPARATION.format(racine=str(RACINE))],
        cwd=repertoire, env=env, capture_output=True, text=True, check=False,
    )
    assert prep.returncode == 0, prep.stdout + prep.stderr
    return subprocess.run(
        [sys.executable, str(RACINE / "outils" / "rapport_cout_cycle.py")],
        cwd=repertoire, env=env, capture_output=True, text=True, check=False,
    )


def test_la_portee_nomme_ce_qui_est_compte_et_ce_qui_ne_lest_pas():
    from falkye.cout_lectures import PORTEE

    assert "trois chemins" in PORTEE.lower() or "TROIS chemins" in PORTEE
    assert "NON compté" in PORTEE
    # Les deux consommateurs hors portée qui ont fait écrire cette constante.
    assert "signaux" in PORTEE
    assert "hébergeur" in PORTEE


def test_le_rapport_imprime_sa_portee(tmp_path):
    fait = _un_cycle_a_zero(tmp_path)

    assert fait.returncode == 0, fait.stdout + fait.stderr
    assert "PORTÉE DE CET INSTRUMENT" in fait.stdout


def test_trois_zeros_ne_se_presentent_jamais_comme_un_cycle_sans_lectures(tmp_path):
    """Le défaut du 11 septembre, reproduit puis refermé. La sortie la plus
    rassurante était celle qui couvrait le moins."""
    fait = _un_cycle_a_zero(tmp_path)

    assert "n'a été emprunté" in fait.stdout
    assert "ce cycle n'a rien lu" in fait.stdout  # la lecture fausse, nommée pour être écartée
    assert "compteur de l'hébergeur" in fait.stdout
