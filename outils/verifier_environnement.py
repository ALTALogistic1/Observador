"""Comparer ce que le code DEMANDE, ce que `.env.example` DÉCLARE, et ce que
l'environnement PORTE réellement.

**Pourquoi cet outil existe.** Trois fois en deux jours, un fichier de
configuration s'est révélé incomplet au pire moment, et jamais avant :

  - le groupe `systemd-journal` manquant à `deploy`, découvert quand la chaîne
    n'a rien pu rapporter d'un import de 33 minutes;
  - la ligne `stop` absente du fichier de sudoers, découverte quand il a fallu
    interrompre un cycle et qu'il a fallu réveiller quelqu'un;
  - `FALKYE_LIEN_BASE_URL` absente de `/etc/falkye/falkye.env`, découverte par le
    refus du premier envoi réel — le dernier livrable du chantier 28.

Le point commun n'est aucune des trois variables. C'est que **rien ne comparait
ce qui est déclaré à ce qui existe**. `.env.example` porte la liste, à jour et
commentée, mais ce n'est qu'un document : personne ne le confronte au réel.

C'est la même forme que `outils/migration_colonnes.py`, qui compare les colonnes
que les modèles déclarent à celles que la base porte. Même dérive, même remède.

**Trois comparaisons, dont deux entièrement dérivées.**

1. *Le code lit une variable que `.env.example` ne déclare pas.* Dérivé par
   balayage du code — aucune liste à tenir à jour. C'est la dérive la plus
   traître : le document a l'air complet et ne l'est pas. Trouvé au premier
   passage : `FALKYE_DB_AUTH_TOKEN`, sans quoi la base distante est injoignable.

2. *`.env.example` déclare une variable que le code ne lit plus.* Une
   déclaration morte fait perdre du temps à qui remplit le fichier.

3. *Une variable requise pour un rôle manque à l'environnement.* Celle-là ne se
   dérive pas : `.env.example` laisse volontairement vides des dizaines
   d'entrées (Stripe, agrégateur, SMTP inactif) et les signaler toutes ferait
   crier l'outil à chaque exécution — un avertissement permanent qu'on finit par
   ignorer. Les rôles ci-dessous sont donc explicites, courts, et un test vérifie
   qu'ils ne nomment que des variables réellement lues par le code.

    python outils/verifier_environnement.py                      # dérive seulement
    python outils/verifier_environnement.py --role base --role envoi

**Les deux contrôles de dérive tournent partout et toujours** : ils ne dépendent
pas de la machine, seulement du dépôt. Les contrôles de RÔLE, eux, s'activent à
la demande — en développement, l'absence des clés Postmark est normale, et les
signaler à chaque exécution ferait de cet outil un avertissement permanent, donc
ignoré. Sur l'hôte, la chaîne les nomme explicitement.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent

# Les variables SANS lesquelles un rôle ne peut pas faire son travail, avec la
# raison — le message doit suffire à réparer sans aller lire le code.
ROLES: dict[str, dict[str, str]] = {
    "base": {
        "FALKYE_DB_URL": "base du produit; sans elle, un fichier SQLite local (falkye/db.py)",
        "FALKYE_DB_AUTH_TOKEN": "jeton de la base distante; sans lui, elle est injoignable",
        "FALKYE_MIROIR_DB_URL": "base des miroirs; TOUJOURS un fichier local (docs/MIROIRS.md)",
    },
    "envoi": {
        "FALKYE_LIEN_BASE_URL": (
            "origine des liens de désabonnement; sans elle AUCUN résumé ne part "
            "— falkye/liens.py refuse, et c'est voulu"
        ),
        "FALKYE_POSTMARK_SERVER_TOKEN": "jeton du serveur Postmark, jamais celui du compte",
        "FALKYE_POSTMARK_FROM_ADDR": "expéditeur; doit appartenir au domaine vérifié",
    },
}

_LECTURE = re.compile(r"""os\.environ(?:\.get\(\s*|\[)["']([A-Z0-9_]+)["']""")
_DECLARATION = re.compile(r"^\s*([A-Z][A-Z0-9_]*)\s*=", re.M)


def variables_lues_par_le_code(racine: Path = RACINE) -> dict[str, str]:
    """{nom: premier fichier qui la lit} — dérivé, jamais tenu à la main."""
    trouve: dict[str, str] = {}
    for dossier in ("falkye", "outils"):
        for chemin in sorted((racine / dossier).rglob("*.py")):
            for nom in _LECTURE.findall(chemin.read_text()):
                trouve.setdefault(nom, str(chemin.relative_to(racine)))
    return trouve


def variables_declarees(exemple: Path) -> set[str]:
    """Les entrées non commentées de `.env.example`."""
    lignes = [l for l in exemple.read_text().splitlines() if not l.lstrip().startswith("#")]
    return set(_DECLARATION.findall("\n".join(lignes)))


def verifier(
    environnement: dict[str, str], roles: list[str] | None = None, racine: Path = RACINE
) -> list[str]:
    """Retourne les anomalies, la plus bloquante d'abord. Vide = tout va bien."""
    lues = variables_lues_par_le_code(racine)
    declarees = variables_declarees(racine / ".env.example")
    anomalies: list[str] = []

    # Aucun rôle demandé = aucun contrôle d'environnement. Voir la docstring :
    # crier en développement sur des clés absentes à raison rendrait l'outil
    # inutile là où il sert.
    for role in roles or []:
        for nom, raison in ROLES.get(role, {}).items():
            valeur = environnement.get(nom, "")
            if not valeur.strip():
                anomalies.append(f"MANQUANTE  [{role}] {nom} — {raison}")

    for nom, fichier in sorted(lues.items()):
        if nom not in declarees and not nom.startswith(("SONDE_", "PYTEST")):
            anomalies.append(
                f"NON DÉCLARÉE  {nom} — lue par {fichier}, absente de .env.example. "
                "Le document a l'air complet et ne l'est pas."
            )

    for nom in sorted(declarees - set(lues)):
        anomalies.append(
            f"DÉCLARATION MORTE  {nom} — dans .env.example, lue nulle part dans le code."
        )
    return anomalies


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--role", action="append", choices=sorted(ROLES),
        help="Vérifier aussi que l'environnement porte les variables de ce rôle. "
             "Sans lui, seuls les deux contrôles de dérive du dépôt s'exécutent.")
    args = parser.parse_args(argv)

    anomalies = verifier(dict(os.environ), args.role)
    if not anomalies:
        print("environnement conforme — rien à signaler")
        return 0
    print(f"{len(anomalies)} anomalie(s) :\n")
    for a in anomalies:
        print(f"  {a}")
    # Sortie non nulle : cet outil doit pouvoir garder une chaîne de déploiement.
    return 1


if __name__ == "__main__":
    sys.exit(main())
