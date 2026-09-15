"""Les unités systemd lancent-elles ce que le dépôt peut réellement exécuter?

**Le fait qui a écrit ces tests** *(2026-09-16, cas 26 pour la DEUXIÈME fois)*.
`outils/import_miroir_req.py` marchait à la main et mourait sous l'unité :

    ModuleNotFoundError: No module named 'outils'

*Deux fois le même jour, un outil a marché à la main et échoué sous systemd.*
**Une vigilance de plus n'est pas un correctif** — ces tests reproduisent les
conditions de l'unité, et rougissent avant l'hôte.

**Ce qu'ils vérifient, et pourquoi chacun.**

1. **La forme d'invocation.** `python outils/x.py` met `outils/` en tête de
   `sys.path`, jamais la racine — donc `import outils.y` meurt. `python -m
   outils.x` met le **répertoire courant** en tête, et `WorkingDirectory` le rend
   juste. *La règle est vérifiable mécaniquement; la vigilance ne l'est pas.*
2. **Le module se charge VRAIMENT**, dans un sous-processus, avec le répertoire
   courant à la racine et **`PYTHONPATH` retiré de l'environnement**. ⚠️ *Sans le
   retirer, le test passerait ici et échouerait sur l'hôte* — c'est exactement
   l'écart qu'on cherche à fermer.
3. **`WorkingDirectory` existe sur toute unité qui lance `-m`.** *Sans lui,
   `-m` ne trouve rien non plus, et la panne serait identique.*
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_UNITES = RACINE / "deploiement"

#: `ExecStart=…/python -m outils.x` ou `…/python outils/x.py`. Le motif capture
#: les deux formes pour pouvoir REFUSER la seconde en la nommant.
MOTIF_PYTHON = re.compile(
    r"ExecStart=\S*?/python3?\s+(?P<forme>-m\s+(?P<module>[\w.]+)|(?P<fichier>\S+\.py))"
)


def _unites() -> list[Path]:
    return sorted(DOSSIER_UNITES.glob("*.service"))


def _lignes_execstart(unite: Path) -> str:
    """Les `ExecStart` d'une unité, continuations `\\` recollées — sinon un
    `ExecStart` sur trois lignes échapperait au motif et le test se tairait."""
    return unite.read_text(encoding="utf-8").replace("\\\n", " ")


def test_il_y_a_des_unites_a_verifier():
    """Une garde qui ne trouve rien à garder passe pour verte. L'absence de
    mesure n'est pas une mesure nulle."""
    assert _unites(), f"aucune unité trouvée dans {DOSSIER_UNITES}"


@pytest.mark.parametrize("unite", _unites(), ids=lambda p: p.name)
def test_aucune_unite_ne_lance_un_script_par_son_chemin(unite: Path):
    """`python outils/x.py` met `outils/` en tête de sys.path, jamais la racine.

    `import falkye.x` y survit — le paquet est installé dans le venv — mais
    `import outils.y` meurt. **Deux familles d'imports dans le même fichier, dont
    une seule survit à l'unité**, et rien ne le signale avant l'hôte.
    """
    fautifs = [
        m.group("fichier")
        for m in MOTIF_PYTHON.finditer(_lignes_execstart(unite))
        if m.group("fichier")
    ]
    assert not fautifs, (
        f"{unite.name} lance {fautifs} par son chemin. "
        "Utiliser `python -m outils.<module>` : lancer un FICHIER met son propre "
        "répertoire en tête de sys.path, donc `import outils.x` échoue sous "
        "l'unité alors qu'il marche à la main (cas 26)."
    )


def _modules_des_unites() -> list[tuple[str, str]]:
    trouves = []
    for unite in _unites():
        for m in MOTIF_PYTHON.finditer(_lignes_execstart(unite)):
            if m.group("module"):
                trouves.append((unite.name, m.group("module")))
    return trouves


@pytest.mark.parametrize(
    "unite_nom,module", _modules_des_unites(), ids=lambda v: str(v)
)
def test_le_module_se_charge_dans_les_conditions_de_lunite(unite_nom: str, module: str):
    """Le module s'importe-t-il VRAIMENT, sans `PYTHONPATH`, depuis la racine?

    ⚠️ **`PYTHONPATH` est retiré de l'environnement du sous-processus.** Sans ça,
    le test hériterait du chemin de la session et passerait ici en échouant sur
    l'hôte — *c'est précisément l'écart qu'il existe pour fermer.*

    ⚠️ Et c'est un **import**, pas un `--help` : le 16 septembre, l'import fautif
    était DANS `main()`, après `parse_args`, donc `--help` sortait avant de
    l'atteindre. **Un import qui peut échouer doit échouer au chargement.**
    """
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    resultat = subprocess.run(
        [sys.executable, "-c", f"import {module}"],
        cwd=RACINE,
        env=env,
        capture_output=True,
        text=True,
    )
    assert resultat.returncode == 0, (
        f"{unite_nom} lance `-m {module}`, et le module ne se charge pas dans les "
        f"conditions de l'unité (racine du dépôt, sans PYTHONPATH) :\n"
        f"{resultat.stderr.strip()[-600:]}"
    )


@pytest.mark.parametrize(
    "unite_nom,module", _modules_des_unites(), ids=lambda v: str(v)
)
def test_une_unite_qui_lance_m_declare_son_repertoire_de_travail(
    unite_nom: str, module: str
):
    """`-m` résout depuis le répertoire COURANT. Sans `WorkingDirectory`, il ne
    trouve rien non plus — et la panne serait identique à celle qu'on ferme."""
    texte = (DOSSIER_UNITES / unite_nom).read_text(encoding="utf-8")
    assert "WorkingDirectory=" in texte, (
        f"{unite_nom} lance `-m {module}` sans WorkingDirectory. "
        "`-m` résout depuis le répertoire courant : sans lui, le module reste "
        "introuvable."
    )
