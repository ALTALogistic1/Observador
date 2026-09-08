"""Le délai maximal d'une exécution — LU depuis l'unité, jamais recopié.

**Pourquoi ce module existe plutôt qu'une constante.** Le seuil au-delà duquel
une exécution ne peut plus tourner vient de `TimeoutStartSec` dans
`deploiement/falkye-cycle.service`. Il vaut 5 400 s aujourd'hui, dimensionné sur
un cycle en régime mesuré à 29 min 10 s. Il a déjà valu 3 600 puis 10 800, et
chacune de ces deux valeurs a tué un cycle. Il changera encore.

Une constante recopiée ici serait exactement la faute que la table de prix du
coût de lecture vient de nous apprendre : une valeur mesurée une fois, juste au
moment où on l'écrit, et fausse ensuite sans que rien ne le dise. Même forme,
même remède — on lit la valeur réelle, et quand on ne peut pas la lire, la
valeur de repli porte sa provenance et se déclare périmée si elle diverge.

**Ce que le module ne peut pas faire.** Hors de systemd — développement, tests,
cycle lancé à la main — il n'y a pas d'unité à interroger, donc pas de délai à
lire. Ce n'est pas un échec : c'est l'information que la déduction « systemd
l'aurait tuée » ne s'applique pas là. Voir `falkye/sante_source.py`.
"""
from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)

UNITE_CYCLE = "falkye-cycle.service"

#: Valeur de repli, avec sa provenance. Employée UNIQUEMENT quand l'unité n'est
#: pas interrogeable, et jamais en silence : `DelaiUnite.lu` dit d'où elle vient.
DELAI_REPLI_SECONDES = 5400
DELAI_REPLI_PROVENANCE = (
    "deploiement/falkye-cycle.service, TimeoutStartSec=5400, posé le 2026-09-08 "
    "sur un cycle en régime mesuré à 29 min 10 s (marge 3,1)"
)

#: `systemctl show` rend une durée en format humain : « 1h 30min », « 5400s »,
#: « 1min 30s », « infinity ». Aucune option ne donne les microsecondes brutes.
_UNITES = {
    "us": 1e-6, "usec": 1e-6, "ms": 1e-3, "msec": 1e-3,
    "s": 1, "sec": 1, "second": 1, "seconds": 1,
    "min": 60, "m": 60, "minute": 60, "minutes": 60,
    "h": 3600, "hr": 3600, "hour": 3600, "hours": 3600,
    "d": 86400, "day": 86400, "days": 86400,
    "w": 604800, "week": 604800, "weeks": 604800,
}


def analyser_duree(texte: str) -> float | None:
    """« 1h 30min » → 5400.0. None si la durée n'est pas exploitable.

    `infinity` rend None à dessein : un délai infini veut dire qu'AUCUNE durée
    ne permet de conclure qu'une exécution est morte. Rendre un très grand
    nombre ferait passer cette impossibilité pour un seuil très haut.
    """
    texte = (texte or "").strip()
    if not texte or texte == "infinity":
        return None
    total = 0.0
    trouve = False
    for valeur, unite in re.findall(r"(\d+(?:\.\d+)?)\s*([a-zA-Z]+)", texte):
        facteur = _UNITES.get(unite.lower())
        if facteur is None:
            return None
        total += float(valeur) * facteur
        trouve = True
    return total if trouve else None


@dataclass(frozen=True)
class DelaiUnite:
    """Le délai, et d'où il vient. La provenance voyage avec le fait."""

    secondes: float | None
    lu: bool
    provenance: str

    @property
    def perime(self) -> bool:
        """Vrai quand la valeur de repli diverge de ce que l'unité déclare.

        Ne peut se savoir que si l'unité a été lue. Une divergence est le signal
        qu'il faut reprendre `DELAI_REPLI_SECONDES` — pas l'ignorer, pas la
        corriger en douce depuis un environnement qui n'est pas l'hôte.
        """
        return self.lu and self.secondes is not None and self.secondes != DELAI_REPLI_SECONDES


def _demander_a_systemd(unite: str) -> str | None:
    try:
        resultat = subprocess.run(
            ["systemctl", "show", unite, "--property=TimeoutStartUSec", "--value"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.debug("systemctl injoignable : %s", exc)
        return None
    if resultat.returncode != 0:
        return None
    return resultat.stdout.strip() or None


def delai_maximal(unite: str = UNITE_CYCLE) -> DelaiUnite:
    """Le délai déclaré par l'unité, ou la valeur de repli avec sa provenance.

    `systemctl show` est une LECTURE que tout utilisateur fait sans privilège —
    aucune entrée de sudoers n'est nécessaire, et c'est pourquoi le fichier de
    permissions n'en porte pas (voir deploiement/falkye-deploiement.sudoers).
    """
    brut = _demander_a_systemd(unite)
    if brut is not None:
        secondes = analyser_duree(brut)
        if secondes is not None:
            return DelaiUnite(
                secondes=secondes,
                lu=True,
                provenance=f"systemctl show {unite} --property=TimeoutStartUSec → « {brut} »",
            )
        return DelaiUnite(
            secondes=None,
            lu=True,
            provenance=f"{unite} déclare « {brut} » — aucune durée n'en dérive",
        )
    return DelaiUnite(
        secondes=float(DELAI_REPLI_SECONDES),
        lu=False,
        provenance=f"valeur de repli : {DELAI_REPLI_PROVENANCE}",
    )
