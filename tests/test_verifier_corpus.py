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


# --------------------------------------------------------------------------
# LE REFUS — ajouté le 2026-09-24, sur demande d'Alexandre
# --------------------------------------------------------------------------


def test_il_TROUVE_le_corpus_depuis_la_racine_du_depot():
    """⛔ **Le défaut du 2026-09-24.** *Le script faisait `glob.glob("*.md")` et
    ne voyait que le répertoire courant.* Lancé depuis la racine il rendait
    **« 2 documents · 0 section de charte · 0 cas »** et déclarait cassés tous
    les renvois du tampon — **un vert vide, rapporté plusieurs fois comme un
    état du dépôt.**"""
    rendu = _lancer(RACINE)
    assert rendu.returncode == 0, rendu.stdout + rendu.stderr
    assert "0 section de charte" not in rendu.stdout
    assert "24 sections de charte" in rendu.stdout
    assert "0 renvoi(s) à corriger" in rendu.stdout


def test_il_REFUSE_quand_il_ne_trouve_pas_le_corpus(tmp_path):
    """⛔ **Cassé volontairement.** *Le script est recopié dans un arbre qui ne
    porte aucun corpus* — ni sous le pied, ni à `docs/spec`. **Il doit REFUSER,
    pas passer** : un rapport vert sur un corpus introuvable se lit comme une
    vérification réussie, ce qui est pire qu'une erreur."""
    faux_depot = tmp_path / "faux-depot"
    (faux_depot / "outils").mkdir(parents=True)
    copie = faux_depot / "outils" / "verifier-corpus.py"
    copie.write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
    (faux_depot / "vide").mkdir()

    rendu = subprocess.run(
        [sys.executable, str(copie)],
        cwd=faux_depot / "vide", capture_output=True, text=True, check=False,
    )
    assert rendu.returncode != 0, rendu.stdout
    sortie = rendu.stdout + rendu.stderr
    assert "REFUS" in sortie
    assert "charte-falkye.md" in sortie
    assert "falkye-journal-des-cas.md" in sortie
    # ⛔ Et surtout : il ne prononce AUCUN verdict.
    assert "renvoi(s) à corriger" not in sortie


def test_le_temoin_dit_l_age_des_documents_ET_ce_qu_il_ne_dit_pas():
    """⚠️ **Le témoin de la règle du 2026-09-24.** *Le tampon enflait d'un côté,
    les documents vieillissaient de l'autre, et les deux faits ne se
    rencontraient nulle part.*

    ⛔ *Première forme écartée le jour même* : dater un document par la date la
    plus récente qu'il ÉCRIT rendait **2026-10-02** sur le chantier 3+4 —
    l'archive du 2 octobre, **une date à venir.**
    """
    rendu = _lancer(RACINE)
    assert "Dernière écriture des documents de chantier" in rendu.stdout
    assert "falkye-chantier-3-4-identite-appariement.md" in rendu.stdout
    # La limite est dans la sortie, pas seulement dans la documentation.
    assert "CE QUE CE TÉMOIN NE DIT PAS" in rendu.stdout
    assert "une retouche d'une virgule" in rendu.stdout


def test_le_rappel_du_tampon_dit_la_REGLE_de_cloture():
    """*La phrase « elles s'écrivent d'un coup à la fin de la tâche » disait le
    contraire de la règle du 2026-09-24* — et elle était la cause écrite des
    269 notes en attente."""
    rendu = _lancer(RACINE)
    assert "d'un coup à la fin de la tâche" not in rendu.stdout
    assert "MÊME demande de fusion" in rendu.stdout
