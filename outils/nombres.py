"""Un nombre lisible, sans toucher au reste de la ligne.

**Le fait qui a écrit ce module** *(2026-09-16)*. L'idiome répandu dans `outils/`
était :

    print(f"   PERDUS, NEQ déjà porté : {n:,}".replace(",", " "))

⚠️ **`.replace` s'applique à TOUTE la ligne, pas au nombre.** La virgule du
LIBELLÉ disparaît avec celles du nombre — « PERDUS, NEQ déjà porté » devient
« PERDUS  NEQ déjà porté ». *Trouvé par un test qui cherchait un libellé et ne
l'a pas trouvé*, dans un outil écrit le jour même; et il traînait déjà dans
`purge_hors_territoire.py` et `entonnoir_noms_req.py`, où personne ne l'avait
remarqué parce qu'on lit les chiffres et pas la ponctuation.

**LA RÈGLE. Une transformation destinée à UNE valeur ne s'applique pas à la
ligne qui la contient.** *La ligne n'est pas la valeur* — et le jour où le
libellé change, la sortie change sans que le code ait bougé.
"""
from __future__ import annotations

#: **Espace insécable étroite** (U+202F), la convention québécoise et française
#: pour les milliers. Une espace ordinaire laisserait « 1 505 879 » se couper en
#: fin de ligne, et un nombre coupé se relit comme deux.
SEPARATEUR_MILLIERS = " "


def milliers(valeur: int | float, decimales: int = 0) -> str:
    """`1505879` → `« 1 505 879 »`. **Rend une chaîne, jamais une ligne.**"""
    return f"{valeur:,.{decimales}f}".replace(",", SEPARATEUR_MILLIERS)
