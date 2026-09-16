"""Un nom de fichier porte-t-il un compte qui va se périmer?

**Le fait qui a écrit ce test** *(2026-09-16, relevé par Alexandre)*.
`outils/profil_des_6176.py` portait un compte dans son nom. ⚠️ **Ce compte
n'était produit par AUCUNE requête du fichier** : sa requête de population est,
au caractère près, celle de `diagnostic_appariement.py` —

    select(Company).where(Company.neq.is_(None))

*Le 6 176 venait d'une mesure passée, gelée dans le nom.* Le plan portait
8 931 entre-temps.

**Deux défauts distincts, et le second est le pire.**

1. **Un compte recopié ne se met pas à jour quand la population bouge.** La
   ventilation du plan datait du 16 septembre; le nom aurait été faux la semaine
   suivante.
2. ⚠️ **Il donne l'autorité d'une MESURE à ce qui n'est qu'une ÉTIQUETTE.** *Un
   lecteur qui voit `profil_des_6176` croit que l'outil porte sur 6 176 lignes —
   personne ne va vérifier le nom d'un fichier contre une requête.*

**La règle, et c'est celle du corpus sur les chiffres recopiés, appliquée aux
noms :** *un chiffre recopié est une promesse que personne ne tient* — **et un
nom de fichier est l'endroit où personne ne va le vérifier.**

*Un numéro de version, une année, un numéro de chantier ne sont pas des comptes :
la garde ne refuse que les nombres assez grands pour être une population.*
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent

#: Trois chiffres consécutifs ou plus. **En dessous, on ne distingue pas un
#: compte d'un numéro de chantier ou d'une année tronquée** — et une garde qui
#: crie pour un `2` finit par être ignorée.
MOTIF_COMPTE = re.compile(r"\d{3,}")

#: Les années sont des repères, pas des comptes. *Un fichier daté dit QUAND, ce
#: qui ne se périme jamais; un fichier compté dit COMBIEN, ce qui se périme.*
ANNEES = re.compile(r"(19|20)\d{2}")


def _fichiers() -> list[Path]:
    trouves: list[Path] = []
    for dossier in ("outils", "falkye", "tests"):
        trouves.extend(
            p for p in (RACINE / dossier).rglob("*.py")
            if "__pycache__" not in p.parts
        )
    return sorted(trouves)


def test_il_y_a_des_fichiers_a_verifier():
    """Une garde qui ne trouve rien à garder passe pour verte."""
    assert _fichiers()


@pytest.mark.parametrize("fichier", _fichiers(), ids=lambda p: p.name)
def test_aucun_nom_de_fichier_ne_porte_un_compte(fichier: Path):
    nom_sans_annees = ANNEES.sub("", fichier.stem)
    trouve = MOTIF_COMPTE.search(nom_sans_annees)
    assert trouve is None, (
        f"{fichier.name} porte « {trouve.group(0)} » dans son nom.\n"
        "Si c'est un COMPTE, il se périmera sans que personne le voie, et il "
        "donne l'autorité d'une mesure à une étiquette : le nom d'un fichier est "
        "l'endroit où personne ne va vérifier un chiffre.\n"
        "Nommer ce que l'outil FAIT, pas ce qu'il a trouvé un jour."
    )
