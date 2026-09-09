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

#: ⚠️ Le nom porte l'unité qu'il désigne, et c'est délibéré. Il s'est d'abord
#: appelé `UNITE_CYCLE` — un nom de CATÉGORIE pour une unité PRÉCISE — et il
#: servait de valeur par défaut à `delai_maximal()`. Deux unités lancent le
#: cycle, avec des délais qui vont du simple au octuple :
#:
#:     falkye-cycle.service                 TimeoutStartSec=5400   (1 h 30)
#:     falkye-cycle-sans-livraison.service  TimeoutStartSec=43200  (12 h)
#:
#: La réconciliation lisait donc 5 400 s pour TOUTES les lignes, y compris
#: celles du cycle d'observation, qu'elle refermait en `interrompue` alors
#: qu'elles tournaient encore — avec un motif chiffré qui se lit comme vérifié.
#:
#: **La règle qui en sort : un seuil déduit d'un réglage se lit sur l'instance
#: qui a produit la ligne, jamais sur une constante nommée d'après une seule
#: d'entre elles.** Un nom de catégorie qui désigne un cas particulier fait
#: passer ce cas pour la règle, et le défaut se lit alors comme une évidence.
UNITE_CYCLE_LIVRAISON = "falkye-cycle.service"
UNITE_CYCLE_OBSERVATION = "falkye-cycle-sans-livraison.service"

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


def delai_maximal(unite: str) -> DelaiUnite:
    """Le délai déclaré par CETTE unité. L'argument n'a pas de défaut, exprès.

    `systemctl show` est une LECTURE que tout utilisateur fait sans privilège —
    aucune entrée de sudoers n'est nécessaire, et c'est pourquoi le fichier de
    permissions n'en porte pas (voir deploiement/falkye-deploiement.sudoers).

    **Aucune valeur par défaut.** Un appelant qui ne sait pas quelle unité a
    produit la ligne ne doit pas obtenir un délai plausible : il doit être
    obligé de le dire. Le défaut d'hier rendait 5 400 s à qui ne demandait
    rien, ce qui est la forme la plus discrète du glissement du décidé au fait.

    **Le repli ne vaut que pour l'unité qu'il décrit.** `DELAI_REPLI_SECONDES`
    a été mesuré sur le cycle de livraison; l'appliquer au cycle d'observation
    reproduirait le défaut sous un autre nom. Pour toute autre unité, hors
    systemd, on rend `None` — aucune durée ne permet de conclure.
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
    if unite != UNITE_CYCLE_LIVRAISON:
        return DelaiUnite(
            secondes=None,
            lu=False,
            provenance=(
                f"{unite} n'est pas interrogeable et aucune valeur de repli ne la "
                "décrit — le repli connu vaut pour "
                f"{UNITE_CYCLE_LIVRAISON} seule"
            ),
        )
    return DelaiUnite(
        secondes=float(DELAI_REPLI_SECONDES),
        lu=False,
        provenance=f"valeur de repli : {DELAI_REPLI_PROVENANCE}",
    )
