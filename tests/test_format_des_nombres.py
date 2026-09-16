"""Un outil applique-t-il encore une mise en forme à toute sa ligne?

**Le fait qui a écrit ce test** *(2026-09-16)*. L'idiome répandu dans `outils/`
était `f"… {n:,}".replace(",", " ")`. ⚠️ **`.replace` porte sur la LIGNE, pas sur
le nombre** : la virgule du LIBELLÉ disparaît avec celles du nombre.

    « PERDUS, NEQ déjà porté »  →  « PERDUS  NEQ déjà porté »

*Trouvé par un test qui cherchait un libellé et ne l'a pas trouvé* — et il
traînait déjà dans `purge_hors_territoire.py` et `entonnoir_noms_req.py`, où
**personne ne l'avait remarqué parce qu'on lit les chiffres, pas la
ponctuation.**

**La règle : une transformation destinée à UNE valeur ne s'applique pas à la
ligne qui la contient.** `outils/nombres.py::milliers` formate la valeur seule.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_OUTILS = RACINE / "outils"

#: L'idiome refusé, dans ses écritures usuelles.
MOTIF = re.compile(r'\.replace\(\s*","\s*,\s*"[\s ]"\s*\)')


def _outils() -> list[Path]:
    return sorted(p for p in DOSSIER_OUTILS.glob("*.py") if p.name != "__init__.py")


def test_il_y_a_des_outils_a_verifier():
    """Une garde qui ne trouve rien à garder passe pour verte."""
    assert _outils()


@pytest.mark.parametrize("outil", _outils(), ids=lambda p: p.name)
def test_aucun_outil_ne_reformate_sa_ligne_entiere(outil: Path):
    fautives = [
        f"{outil.name}:{i}"
        for i, ligne in enumerate(outil.read_text(encoding="utf-8").splitlines(), 1)
        # `nombres.py` cite l'idiome dans sa docstring pour l'expliquer : c'est
        # sa raison d'être, pas une rechute. La citation vit dans une ligne de
        # `print(` d'exemple, jamais exécutée.
        if MOTIF.search(ligne) and outil.name != "nombres.py"
    ]
    assert not fautives, (
        f"{fautives} applique une mise en forme à la LIGNE entière. "
        "Utiliser `outils.nombres.milliers(valeur)` : la virgule du libellé "
        "disparaît autrement, en silence."
    )


def test_milliers_ne_touche_que_le_nombre():
    from outils.nombres import milliers

    ligne = f"PERDUS, NEQ déjà porté : {milliers(1505879)}"
    assert "PERDUS, NEQ" in ligne, "la virgule du libellé a été mangée"
    assert milliers(1505879).replace(" ", " ") == "1 505 879"
