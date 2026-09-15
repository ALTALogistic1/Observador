"""Un outil qui ouvre une session annonce-t-il sa cible et refuse-t-il le repli?

**Le fait qui a écrit ces tests** *(2026-09-16)*. Le garde-fou du 11 septembre
existait depuis cinq jours — `bases_sur_repli()`. **Mais il était recopié à la
main, outil par outil, et quinze des vingt-huit outils qui ouvrent une session
ne le portaient pas.** *Une convention protège les fichiers où quelqu'un a pensé
à l'écrire; elle ne dit rien des autres, et elle ne dit surtout pas qu'elle n'y
est pas.*

⚠️ **Et ce qui arrive sans elle n'est pas une panne franche.** Reproduit le
2026-09-16 dans un répertoire vierge, sans `FALKYE_MIROIR_DB_URL` :

    $ ls data/
    miroirs.sqlite3     # 0 octet — l'outil vient de le CRÉER

**L'outil a fabriqué la base qu'il prétendait interroger.** Sur l'hôte il est
tombé sur un `PermissionError`, mais *uniquement parce que le répertoire courant
n'était pas inscriptible* — **ce n'est pas une garde, c'est un accident de
permissions.** Le même outil lancé depuis un répertoire inscriptible rend un
verdict vert sur une base vide.

*Un verdict rendu sur une base vide est le plus rassurant de tous.*

**Ce que ces tests font.** Ils listent les outils qui ouvrent une session
(`get_session`, `get_session_miroir`, `get_engine`) et exigent que chacun porte
la garde — soit `refuser_si_cible_non_choisie()`, soit le couple historique
`cible_annoncee()` + `bases_sur_repli()` que treize outils portaient déjà.

⚠️ **La PRÉSENCE est mécanique, le PLACEMENT reste humain.** La garde doit
tomber *juste avant* l'ouverture de la session, jamais après `parse_args` en
aveugle : `profil_memoire_import` a un mode qui ne touche aucune base, et une
garde posée trop tôt le refuserait à tort. *Le test ne peut pas juger ça; il
peut garantir qu'on n'a pas simplement oublié.*
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_OUTILS = RACINE / "outils"

#: Ouvrir l'une de ces portes engage une cible. `cible_annoncee()` en est
#: exclue à dessein : sa docstring dit qu'elle n'ouvre AUCUN moteur, et c'est
#: précisément pour pouvoir dire « mauvaise cible » sans la fabriquer.
OUVERTURES = ("get_session", "get_session_miroir", "get_engine", "get_engine_miroir")

#: Les deux formes acceptées : le helper, ou le couple historique complet.
HELPER = "refuser_si_cible_non_choisie"
COUPLE = ("cible_annoncee", "bases_sur_repli")


def _appels(arbre: ast.AST) -> set[str]:
    """Les noms de fonction APPELÉS, `x()` comme `mod.x()`. *Un import sans
    appel ne garde rien* — c'est la différence entre porter la garde et l'avoir
    mentionnée."""
    trouves: set[str] = set()
    for n in ast.walk(arbre):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                trouves.add(f.id)
            elif isinstance(f, ast.Attribute):
                trouves.add(f.attr)
    return trouves


def _outils_qui_ouvrent() -> list[Path]:
    trouves = []
    for p in sorted(DOSSIER_OUTILS.glob("*.py")):
        if p.name == "__init__.py":
            continue
        try:
            appels = _appels(ast.parse(p.read_text(encoding="utf-8")))
        except SyntaxError:  # pragma: no cover - un fichier cassé a son propre test
            continue
        if appels & set(OUVERTURES):
            trouves.append(p)
    return trouves


def test_il_y_a_des_outils_qui_ouvrent_une_session():
    """Une garde qui ne trouve rien à garder passe pour verte.
    L'absence de mesure n'est pas une mesure nulle."""
    assert _outils_qui_ouvrent(), "aucun outil n'ouvre de session — motif de recherche faux?"


@pytest.mark.parametrize("outil", _outils_qui_ouvrent(), ids=lambda p: p.name)
def test_un_outil_qui_ouvre_une_session_refuse_le_repli(outil: Path):
    """La garde est-elle APPELÉE, pas seulement importée?

    *Quinze outils sur vingt-huit ne la portaient pas, et rien ne le disait.*
    """
    appels = _appels(ast.parse(outil.read_text(encoding="utf-8")))
    if HELPER in appels:
        return
    manquants = [nom for nom in COUPLE if nom not in appels]
    assert not manquants, (
        f"{outil.name} ouvre une session sans refuser le repli "
        f"(manque : {', '.join(manquants)}).\n"
        "Poser, JUSTE AVANT l'ouverture de la session :\n"
        "    from falkye.db import refuser_si_cible_non_choisie\n"
        "    code = refuser_si_cible_non_choisie()\n"
        "    if code:\n"
        "        return code\n"
        "Sans elle, le repli CRÉE `./data/*.sqlite3` dans le répertoire courant "
        "et le verdict porte sur une base vide — reproduit le 2026-09-16."
    )
