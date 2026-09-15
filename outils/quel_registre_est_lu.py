#!/usr/bin/env python3
"""Quel fichier de registre le produit lit-il RÉELLEMENT — et depuis quand
diverge-t-il de celui du dépôt.

**Le fait qui justifie cet outil** *(2026-09-16)*. La sonde d'Alexandre, lancée
sur l'hôte, a compté **dix adresses** au registre des sources. La mienne, dans le
conteneur, en a compté **trois**. Et `falkye/registry/sources.yaml` du dépôt n'en
porte que **trois**, vérifié par balayage du YAML brut. *Les deux registres ne
sont donc pas le même fichier.*

**Pourquoi c'est structurel et pas accidentel.** Le chargeur résout son chemin
ainsi :

    REGISTRY_DIR = Path(__file__).parent          # falkye/registry/loader.py:18
    path = REGISTRY_DIR / filename

**Le registre est donc lu À CÔTÉ DU PAQUET INSTALLÉ, pas dans le dépôt.** *Si
`falkye` est installé en copie (`pip install .`) plutôt qu'en lien
(`pip install -e .`), le YAML lu est une COPIE figée au moment de
l'installation* — et elle diverge du dépôt à chaque fusion qui touche le
registre, **sans que rien ne le signale.**

⚠️ **C'est la même famille que le cas 35 et que N20** : *rien n'échoue, chaque
geste réussit, et l'écart n'apparaît qu'à l'autre bout.* **Quatrième fois le
16 septembre que le chemin y ramène.**

**Ce que l'outil rend, et pourquoi chaque champ compte.**

- **Le chemin résolu** — celui que Python ouvre, pas celui qu'on croit.
- **Le mode d'installation** — copie ou lien, déduit du chemin lui-même.
- **L'empreinte SHA-256** — *deux fichiers de même taille et même date peuvent
  différer; l'empreinte est la seule comparaison qui ne ment pas.*
- **La date de modification** — qui donne le **depuis quand**.
- **Le compte d'adresses** — le chiffre en litige, relu sur le fichier réellement
  lu.
- **La comparaison avec le dépôt**, quand le dépôt est là.

⚠️ **PORTÉE.** Il lit des fichiers, rien d'autre. *Il ne dit pas lequel des deux
DOIT faire foi* — il dit lequel est lu. **C'est l'hôte qui fait foi pour ce que
le produit fait; c'est le dépôt qui fait foi pour ce qu'on a décidé.** Quand les
deux divergent, c'est le déploiement qui est en cause, pas l'un des fichiers.

Usage :
    python3 outils/quel_registre_est_lu.py
    python3 outils/quel_registre_est_lu.py --fichier spheres.yaml
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

#: Le motif d'adresse, identique à celui de `adresses_sans_temoin.py` — les deux
#: outils doivent compter la même chose, sinon leurs chiffres ne se comparent pas.
MOTIF_URL = re.compile(r"https?://[^\s\"'<>)\]]+")

#: Les registres que le produit charge. Le défaut est celui en litige.
FICHIER_DEFAUT = "sources.yaml"


def empreinte(chemin: Path) -> str:
    """SHA-256. **Deux fichiers de même taille et même date peuvent différer** —
    l'empreinte est la seule comparaison qui ne ment pas."""
    condensat = hashlib.sha256()
    with chemin.open("rb") as fichier:
        for bloc in iter(lambda: fichier.read(1024 * 256), b""):
            condensat.update(bloc)
    return condensat.hexdigest()


def mode_installation(chemin: Path) -> str:
    """Copie ou lien, déduit du chemin. **C'est le mode qui décide si le registre
    peut diverger** : un paquet installé en lien lit le dépôt, un paquet installé
    en copie lit un instantané figé à l'installation."""
    texte = str(chemin)
    if "site-packages" in texte or "dist-packages" in texte:
        return "COPIE (site-packages) — fige le registre à l'installation"
    return "en place (arbre source) — suit le dépôt"


def decrire(chemin: Path) -> dict:
    """Tout ce qu'on peut dire d'un fichier de registre sans l'interpréter."""
    if not chemin.is_file():
        return {"chemin": chemin, "existe": False}
    contenu = chemin.read_text(encoding="utf-8", errors="replace")
    return {
        "chemin": chemin,
        "existe": True,
        "octets": chemin.stat().st_size,
        "modifie": datetime.fromtimestamp(chemin.stat().st_mtime, tz=timezone.utc),
        "empreinte": empreinte(chemin),
        "adresses": len(MOTIF_URL.findall(contenu)),
        "lignes": contenu.count("\n") + 1,
    }


def afficher(titre: str, fiche: dict) -> None:
    print(f"\n   {titre}")
    if not fiche["existe"]:
        print(f"      {fiche['chemin']}")
        print("      ⛔ ABSENT")
        return
    print(f"      chemin     : {fiche['chemin']}")
    print(f"      mode       : {mode_installation(fiche['chemin'])}")
    print(f"      octets     : {fiche['octets']:,}".replace(",", " "))
    print(f"      lignes     : {fiche['lignes']}")
    print(f"      modifié le : {fiche['modifie']:%Y-%m-%d %H:%M:%S} UTC")
    print(f"      empreinte  : {fiche['empreinte']}")
    print(f"      adresses   : {fiche['adresses']}   ← le chiffre en litige")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--fichier", default=FICHIER_DEFAUT,
                        help=f"le registre à examiner (défaut {FICHIER_DEFAUT})")
    args = parser.parse_args(argv)

    print("=" * 78)
    print("QUEL REGISTRE LE PRODUIT LIT-IL RÉELLEMENT")
    print("=" * 78)
    print("\nPORTÉE : il dit lequel est LU, jamais lequel doit faire foi.")
    print("         L'hôte fait foi pour ce que le produit FAIT.")
    print("         Le dépôt fait foi pour ce qu'on a DÉCIDÉ.")
    print("         Quand ils divergent, c'est le déploiement qui est en cause.")

    try:
        from falkye.registry import loader
    except ImportError as exc:  # pragma: no cover - dépend de l'environnement
        print(f"\nImport impossible ({exc}).", file=sys.stderr)
        return 2

    # Le chemin que le chargeur résout LUI-MÊME, emprunté et non reconstruit.
    lu = Path(loader.REGISTRY_DIR) / args.fichier
    fiche_lue = decrire(lu)
    afficher("CE QUE LE PRODUIT LIT", fiche_lue)

    # Le même fichier dans l'arbre source, s'il est là et s'il est distinct.
    depot = Path.cwd() / "falkye" / "registry" / args.fichier
    fiche_depot = decrire(depot)
    if fiche_depot["existe"] and depot.resolve() == lu.resolve():
        print("\n   LE DÉPÔT")
        print("      C'est le MÊME fichier (chemins identiques après résolution).")
        print("      → aucun écart possible ici.")
        divergent = False
    else:
        afficher("CE QUE LE DÉPÔT PORTE", fiche_depot)
        divergent = (
            fiche_depot["existe"] and fiche_lue["existe"]
            and fiche_depot["empreinte"] != fiche_lue["empreinte"]
        )

    print("\n" + "-" * 78)
    print("LE VERDICT")
    print("-" * 78)
    if not fiche_lue["existe"]:
        print("\n   ⛔ Le produit n'a aucun registre à lire à ce chemin.")
        return 1
    if not fiche_depot["existe"]:
        print("\n   Le dépôt n'est pas accessible d'ici — rien à comparer.")
        print("   Relancer cet outil depuis la racine du dépôt pour la comparaison.")
        return 0
    if not divergent:
        print("\n   ✅ Les deux fichiers ont la MÊME empreinte. Aucun écart.")
        print(f"      {fiche_lue['adresses']} adresse(s) des deux côtés.")
        return 0

    print("\n   ⛔ LES DEUX FICHIERS DIVERGENT.")
    print(f"      lu par le produit : {fiche_lue['adresses']} adresse(s), "
          f"modifié {fiche_lue['modifie']:%Y-%m-%d %H:%M} UTC")
    print(f"      dans le dépôt     : {fiche_depot['adresses']} adresse(s), "
          f"modifié {fiche_depot['modifie']:%Y-%m-%d %H:%M} UTC")
    ecart = fiche_depot["modifie"] - fiche_lue["modifie"]
    jours = abs(ecart.total_seconds()) / 86400
    plus_vieux = "lu par le produit" if ecart.total_seconds() > 0 else "du dépôt"
    print(f"\n      Le fichier {plus_vieux} est le plus ANCIEN, de {jours:.1f} jour(s).")
    print("      ⚠️ La date de modification dit quand le FICHIER a été écrit,")
    print("         pas quand la divergence a commencé : une installation")
    print("         réécrit la copie même sans changement de contenu.")
    print("         Pour dater la divergence, comparer l'empreinte lue au")
    print("         `git log` de falkye/registry/" + args.fichier + ".")
    if "site-packages" in str(fiche_lue["chemin"]):
        print("\n   LA CAUSE EST NOMMÉE : le paquet est installé en COPIE.")
        print("      `pip install .` fige le registre; `pip install -e .` le suit.")
        print("      Chaque fusion touchant le registre creuse l'écart, en silence.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
