"""Le README ne doit pas contredire le registre — ce qu'il en reste à vérifier.

**Ce test garde peu, et c'est voulu.** Le 2026-09-10, le README a cessé de
lister les sources : leur vérité vit au registre, et un inventaire recopié est
une promesse de le tenir à jour. Ce qui n'est plus écrit ne peut plus mentir,
donc ce test n'a presque rien à vérifier. C'est le résultat souhaité, pas le
signe qu'il est inutile — il garde ce qui reste, il ne compense pas ce qu'on
aurait dû retirer.

**Ce qu'il n'exige surtout PAS : qu'un identifiant nommé soit actif.**
Guichet-Emplois a raison de figurer dans la documentation comme source en
pause. Un test qui l'interdirait forcerait à retirer une information vraie
pour passer au vert.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from falkye.registry.loader import get_registry

RACINE = Path(__file__).resolve().parents[1]
README = RACINE / "README.md"

#: Les mots de statut du vocabulaire des sources, tels qu'ils s'écrivent au
#: registre. Un mot de statut accolé à un identifiant est une AFFIRMATION, et
#: c'est la seule chose que ce test compare.
STATUTS = ("actif", "en_pause", "a_developper", "inactif")


@pytest.fixture(scope="module")
def texte() -> str:
    return README.read_text(encoding="utf-8")


def _identifiants_cites(texte: str, connus: set[str]) -> set[str]:
    """Les identifiants de source du registre cités entre accents graves."""
    return {m for m in re.findall(r"`([a-z0-9_]+)`", texte) if m in connus}


# --- Pourquoi la première assertion convenue n'est PAS implémentée ici -----
#
# « Tout identifiant de source nommé dans le README existe au registre » est
# juste, et mécaniquement indécidable : rien dans la FORME d'un mot entre
# accents graves ne distingue `guichet_emplois` de `create_all`,
# `journal_diagnostic` ou `plan_minimum`. Une heuristique sur les soulignés a
# été écrite, puis retirée — elle tombait sur quatre mots sains, donc elle
# aurait cassé sans défaut et rassuré sans couverture. C'est le premier des
# quatre pièges du guide.
#
# Ce qui reste couvre le cas qui MENT : un identifiant du registre cité avec un
# statut qui n'est pas le sien. Un identifiant inconnu cité SANS statut ne
# trompe personne — il ne prétend rien.


def test_un_statut_accole_a_un_identifiant_correspond_au_registre(texte):
    """Nommer sans statuer reste permis. Statuer engage."""
    registre = get_registry().sources
    cites = _identifiants_cites(texte, set(registre))

    for identifiant in cites:
        fenetre = "".join(
            texte[m.start(): m.start() + 220]
            for m in re.finditer(rf"`{re.escape(identifiant)}`", texte)
        )
        for mot in STATUTS:
            if mot in fenetre:
                assert registre[identifiant].statut == mot, (
                    f"{identifiant} : le README dit « {mot} », "
                    f"le registre dit « {registre[identifiant].statut} »"
                )


def test_le_readme_ne_recopie_plus_l_inventaire_des_sources(texte):
    """Le vrai remède n'est pas le test, c'est le retrait. Si l'inventaire
    revient, ce test tombe avant que l'écart ne se rouvre."""
    actives = [s.id for s in get_registry().sources_actives()]
    nommees = [s for s in actives if f"`{s}`" in texte]

    assert len(nommees) <= 2, (
        "le README recense de nouveau les sources actives "
        f"({nommees}) — leur vérité vit au registre"
    )


def test_le_readme_renvoie_a_la_commande_du_registre(texte):
    """Retirer l'inventaire sans dire où le lire déplacerait le défaut."""
    assert "falkye registry sources" in texte


def test_la_distinction_automatisee_manuel_est_expliquee(texte):
    """La seule exception retenue : une carte doit dire comment lire ce vers
    quoi elle renvoie. `actif` ne veut pas dire « tourne dans un cycle », et un
    lecteur qui suit le renvoi sans cette clé compte faux."""
    assert "sources_actives_automatisees" in texte
    assert "import manuel" in texte.lower()
