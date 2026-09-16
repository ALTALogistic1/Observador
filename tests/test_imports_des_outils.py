"""Les imports `falkye.*` des outils désignent-ils quelque chose qui existe?

**Le fait qui a écrit ces tests** *(2026-09-16)*. `outils/profil_memoire_import.py`
importait `falkye.models.etat_ligne_source`. **Ce module n'a jamais existé** — le
vrai est `etat_diff_source`. Le nom avait été *déduit* de celui de la classe
(`EtatLigneSource`) au lieu d'être lu.

⚠️ **Et rien ne pouvait le dire avant l'hôte, pour deux raisons qui se
cumulent.**

1. **L'import était DANS une fonction**, après `parse_args` — donc ni le
   chargement du module, ni `--help`, ni aucun test du fichier ne l'atteignait.
   *C'est le cas 26 une troisième fois : un import qui peut échouer doit échouer
   au chargement, ou être vérifié autrement.*
2. **Un `except ImportError` l'enveloppait**, écrit pour une dépendance tierce
   absente. Il a donc **habillé un défaut du dépôt en problème
   d'environnement** — et le message a envoyé son lecteur chercher une panne de
   déploiement qui n'existait pas.

**Ce que ces tests font, et pourquoi c'est mécanique plutôt que vigilant.** Ils
parcourent l'AST de chaque outil, **à toute profondeur** — dans les fonctions,
dans les `try`, partout où un import peut se cacher — et vérifient que chaque
module `falkye.*` visé existe, puis que chaque nom importé y est défini.

⚠️ **`find_spec`, jamais un import réel.** *Importer exécuterait le module, donc
le test dépendrait des dépendances tierces installées* — et un environnement sans
`sqlalchemy-libsql` ferait rougir la garde pour une raison qui n'est pas la
sienne. **Une garde ne couvre que ce que la mesure couvrait** : celle-ci couvre
l'existence, pas l'exécutabilité.
"""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

#: Les paquets du dépôt. ⚠️ `outils` a été AJOUTÉ le 2026-09-16, quelques
#: heures après la création de ce fichier : un outil importait
#: `outils.archives_req.resoudre_archive`, qui n'existe pas — le vrai est
#: `resoudre` — et cette garde ne l'a pas vu parce qu'elle ne regardait que
#: `falkye.*`. **Le défaut exact qu'elle existe pour attraper, hors de sa
#: propre portée.** *Une garde ne couvre que ce que la mesure couvrait — y
#: compris quand c'est la garde elle-même qui a fixé la mesure.*
PREFIXES = ("falkye", "outils")

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_OUTILS = RACINE / "outils"


def _outils() -> list[Path]:
    return sorted(p for p in DOSSIER_OUTILS.glob("*.py") if p.name != "__init__.py")


def _imports_falkye(chemin: Path) -> list[tuple[int, str, tuple[str, ...]]]:
    """`(ligne, module, noms)` de chaque import `falkye.*`, À TOUTE PROFONDEUR.

    **`ast.walk` et non une lecture des seuls nœuds de premier niveau** : le
    défaut du 16 septembre était précisément un import enfoui dans une fonction,
    sous un `try`. *Ne regarder que le module en surface l'aurait manqué.*
    """
    arbre = ast.parse(chemin.read_text(encoding="utf-8"), filename=str(chemin))
    trouves: list[tuple[int, str, tuple[str, ...]]] = []
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.ImportFrom):
            # `from . import x` a `module is None`; il ne nous concerne pas.
            if noeud.level or not noeud.module or not noeud.module.startswith(PREFIXES):
                continue
            noms = tuple(a.name for a in noeud.names if a.name != "*")
            trouves.append((noeud.lineno, noeud.module, noms))
        elif isinstance(noeud, ast.Import):
            for alias in noeud.names:
                if alias.name.startswith(PREFIXES):
                    trouves.append((noeud.lineno, alias.name, ()))
    return trouves


def _noms_lies_au_module(module: str) -> set[str] | None:
    """Les noms définis au PREMIER NIVEAU d'un module `falkye.*`, sans l'exécuter.

    Rend `None` si le module n'a pas de source lisible (paquet natif, namespace) —
    *l'absence de source n'est pas une absence de nom*, et une garde qui
    confondrait les deux ferait rougir pour rien.
    """
    try:
        spec = importlib.util.find_spec(module)
    except (ImportError, ValueError):
        return None
    if spec is None or not spec.origin or not spec.origin.endswith(".py"):
        return None
    arbre = ast.parse(Path(spec.origin).read_text(encoding="utf-8"), filename=spec.origin)
    lies: set[str] = set()
    for noeud in arbre.body:
        if isinstance(noeud, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            lies.add(noeud.name)
        elif isinstance(noeud, (ast.Import, ast.ImportFrom)):
            for alias in noeud.names:
                if alias.name == "*":
                    # Un ré-export en étoile rend l'inventaire incomplet : on se
                    # tait plutôt que d'accuser à tort.
                    return None
                lies.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(noeud, ast.Assign):
            for cible in noeud.targets:
                if isinstance(cible, ast.Name):
                    lies.add(cible.id)
        elif isinstance(noeud, ast.AnnAssign) and isinstance(noeud.target, ast.Name):
            lies.add(noeud.target.id)
        elif isinstance(noeud, ast.Try):
            # `try: from x import y / except ImportError: y = None` — motif courant.
            for sous in ast.walk(noeud):
                if isinstance(sous, (ast.Import, ast.ImportFrom)):
                    for alias in sous.names:
                        if alias.name != "*":
                            lies.add(alias.asname or alias.name.split(".")[0])
                elif isinstance(sous, ast.Assign):
                    for cible in sous.targets:
                        if isinstance(cible, ast.Name):
                            lies.add(cible.id)
    return lies


def test_il_y_a_des_outils_a_verifier():
    """Une garde qui ne trouve rien à garder passe pour verte.
    L'absence de mesure n'est pas une mesure nulle."""
    assert _outils(), f"aucun outil trouvé dans {DOSSIER_OUTILS}"


@pytest.mark.parametrize("outil", _outils(), ids=lambda p: p.name)
def test_chaque_module_falkye_importe_existe(outil: Path):
    """Le module visé existe-t-il? **C'est exactement le défaut du 16 septembre.**

    `falkye.models.etat_ligne_source` n'a jamais existé; le vrai est
    `etat_diff_source`. *Le nom avait été déduit de celui de la classe.*
    """
    manquants = []
    for ligne, module, _ in _imports_falkye(outil):
        try:
            existe = importlib.util.find_spec(module) is not None
        except (ImportError, ValueError):
            existe = False
        if not existe:
            manquants.append(f"{outil.name}:{ligne} → {module}")
    assert not manquants, (
        "modules `falkye.*` importés et INEXISTANTS :\n  " + "\n  ".join(manquants)
        + "\n\nUn import enfoui dans une fonction, sous un `except ImportError`, "
        "ne se signale qu'à l'exécution — et le message accuse alors "
        "l'environnement plutôt que le dépôt."
    )


@pytest.mark.parametrize("outil", _outils(), ids=lambda p: p.name)
def test_chaque_nom_importe_est_defini_dans_son_module(outil: Path):
    """Le module existe : y trouve-t-on le nom demandé?

    *Un bon module et un mauvais symbole échouent de la même façon, et se font
    absorber par la même garde.* Les modules sans source lisible ou portant un
    ré-export en étoile sont **écartés en silence** : on ne mesure pas, donc on
    n'accuse pas.
    """
    absents = []
    for ligne, module, noms in _imports_falkye(outil):
        if not noms:
            continue
        lies = _noms_lies_au_module(module)
        if lies is None:
            continue
        for nom in noms:
            # `from falkye.a import b` où `b` est un SOUS-MODULE reste valide.
            if nom in lies:
                continue
            try:
                if importlib.util.find_spec(f"{module}.{nom}") is not None:
                    continue
            except (ImportError, ValueError, ModuleNotFoundError):
                pass
            absents.append(f"{outil.name}:{ligne} → {module}.{nom}")
    assert not absents, (
        "noms importés et INTROUVABLES dans leur module :\n  " + "\n  ".join(absents)
    )
