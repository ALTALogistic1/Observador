"""Ce que la vérification du corpus attrape — et ce qu'elle doit refuser de taire.

Le script `outils/verifier-corpus.py` vient du corpus, pas du dépôt. Ces tests
verrouillent les DEUX ajouts faits en le branchant, et rien d'autre : ils ne
réécrivent pas sa logique d'origine.

1. **Deux cas du journal ne peuvent pas porter le même numéro.** La collision
   s'est produite deux fois en une semaine. Un numéro dupliqué ne rend pas un
   renvoi mort, il le rend AMBIGU — ce qui est pire, parce qu'il mène encore
   quelque part.
2. **La limite est dans la SORTIE**, y compris sous un rapport vert. Le script
   vérifie qu'une cible existe, jamais qu'elle contient encore ce qu'on y
   cherche : trois renvois vers la section 11 de la charte, vidée le
   7 septembre, lui sont passés sous le nez.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
SCRIPT = RACINE / "outils" / "verifier-corpus.py"
CORPUS = RACINE / "docs" / "spec"

JOURNAL = "falkye-journal-des-cas.md"


def _lancer(repertoire: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=repertoire, capture_output=True, text=True, check=False,
    )


def _corpus_copie(tmp_path: Path) -> Path:
    for fichier in CORPUS.glob("*.md"):
        (tmp_path / fichier.name).write_text(
            fichier.read_text(encoding="utf-8"), encoding="utf-8"
        )
    return tmp_path


def test_le_corpus_du_depot_passe_sa_propre_verification():
    """Le cas dont on connaît la réponse. S'il tombe, c'est le corpus qui a
    dérivé, pas le script — et c'est exactement ce qu'on veut apprendre."""
    fait = _lancer(CORPUS)

    assert fait.returncode == 0, fait.stdout
    assert "0 renvoi(s) à corriger" in fait.stdout


def test_deux_cas_du_meme_numero_font_echouer_la_verification(tmp_path):
    repertoire = _corpus_copie(tmp_path)
    journal = repertoire / JOURNAL
    journal.write_text(
        journal.read_text(encoding="utf-8").replace("## Cas 27 —", "## Cas 26 —"),
        encoding="utf-8",
    )

    fait = _lancer(repertoire)

    assert fait.returncode == 1
    assert "cas 26 apparaît 2 fois" in fait.stdout


def test_le_doublon_est_nomme_avec_sa_consequence(tmp_path):
    """« Cas 26 en double » ne dit pas pourquoi c'est grave. Un rapport qui
    n'énonce pas la conséquence se fait ranger dans les avertissements."""
    repertoire = _corpus_copie(tmp_path)
    journal = repertoire / JOURNAL
    journal.write_text(
        journal.read_text(encoding="utf-8").replace("## Cas 27 —", "## Cas 26 —"),
        encoding="utf-8",
    )

    fait = _lancer(repertoire)

    assert "AMBIGU" in fait.stdout


def test_la_limite_est_dans_la_sortie_meme_quand_tout_passe():
    """Le passage vert est celui qu'on serait tenté de raccourcir, et c'est
    celui où la limite compte le plus."""
    fait = _lancer(CORPUS)

    assert fait.returncode == 0
    assert "vérifie qu'une cible EXISTE" in fait.stdout
    assert "section 11" in fait.stdout


def test_la_limite_est_aussi_dans_la_sortie_en_echec(tmp_path):
    repertoire = _corpus_copie(tmp_path)
    journal = repertoire / JOURNAL
    journal.write_text(
        journal.read_text(encoding="utf-8").replace("## Cas 27 —", "## Cas 26 —"),
        encoding="utf-8",
    )

    fait = _lancer(repertoire)

    assert fait.returncode == 1
    assert "vérifie qu'une cible EXISTE" in fait.stdout


def test_un_renvoi_vers_un_fichier_absent_du_corpus_est_vu(tmp_path):
    """Le contrôle d'origine, gardé sous test parce que le branchement le fait
    tourner sur un répertoire (`docs/spec/`) où un fichier peut disparaître par
    une fusion sans que personne ne relise les renvois."""
    repertoire = _corpus_copie(tmp_path)
    (repertoire / "charte-falkye.md").write_text(
        "# Charte\n\nÀ lire avec `falkye-document-qui-nexiste-pas.md`.\n",
        encoding="utf-8",
    )

    fait = _lancer(repertoire)

    assert fait.returncode == 1
    assert "falkye-document-qui-nexiste-pas.md" in fait.stdout
