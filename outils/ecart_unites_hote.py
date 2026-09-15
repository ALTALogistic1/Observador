#!/usr/bin/env python3
"""Les unités du dépôt et celles de l'hôte disent-elles la même chose?

**Le fait qui a écrit cet outil** *(2026-09-16)*. `deploiement/falkye-miroir-req.service`
portait `-m` dans le dépôt; l'hôte lançait encore le script par son chemin. **Le
code était à jour, l'unité ne l'était pas**, et `daemon-reload` n'y pouvait rien :
*ce n'est pas un cache, c'est un fichier qui n'a jamais été recopié.*

**Et la chaîne ne les a JAMAIS copiées.** `.github/workflows/deploiement.yml`
`rsync` le dépôt vers `/opt/falkye/code/` — *les unités y arrivent bien, mais
systemd lit `/etc/systemd/system/`, et rien ne fait le pont.* **Depuis le premier
déploiement, les unités de l'hôte sont ce que quelqu'un y a installé à la main, un
jour.**

⚠️ **Et ce n'est pas un oubli à réparer en ajoutant une ligne.** Le fichier de
permissions dit pourquoi : *« une chaîne compromise peut redémarrer le service,
jamais lire la base »* — `deploy` a le droit de **démarrer sept actions nommées**,
pas d'écrire dans `/etc/systemd/system/`. **Lui donner ce droit lui donnerait
celui de faire exécuter n'importe quoi en root.** *La séparation est une propriété
de sécurité, pas une lacune.*

**Ce que cet outil fait à la place : DÉTECTER.** *Lire ne demande aucun
privilège* — `systemctl cat` et `/etc/systemd/system/` sont ouverts à tous. **La
chaîne peut donc constater la dérive même si elle n'a pas le droit de la
corriger**, et c'est la seule chose qui manquait.

**Trois écarts, et ils ne se soignent pas pareil.**

1. **Une unité du dépôt ABSENTE de l'hôte** — elle n'a jamais été installée.
2. **Une unité dont les DIRECTIVES diffèrent** — *c'est celle qui a coûté la
   soirée.* L'outil compare les directives, pas les commentaires : *un commentaire
   qui diffère ne change rien à ce que la machine fait.*
3. ⚠️ **Un DROP-IN sur l'hôte que le dépôt ignore.** *Un drop-in surcharge un
   fichier d'unité réel* — c'est le cas 36, et il rend l'unité de l'hôte
   différente de son fichier **sans que le fichier change**. `systemctl cat` les
   montre; lire `/etc/systemd/system/x.service` seul les rate.

⚠️ **PORTÉE.** Lecture seule, aucune écriture, aucun `systemctl` privilégié.
*Il dit ce qui diverge; il n'installe rien* — **l'installation d'une unité est un
geste humain en root, et elle doit le rester.**

Usage, SUR L'HÔTE :
    python3 -m outils.ecart_unites_hote
    python3 -m outils.ecart_unites_hote --detail     # le texte complet des écarts
"""
from __future__ import annotations

import argparse
import difflib
import re
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_UNITES = RACINE / "deploiement"

#: Les directives qui décident de ce que la machine FAIT. Un écart ailleurs
#: (`Description`, un commentaire) est rapporté mais ne fait pas rougir — *une
#: garde qui crie pour une virgule finit par être ignorée.*
DIRECTIVES_QUI_COMPTENT = (
    "ExecStart", "ExecStartPre", "ExecStartPost", "ExecStop",
    "WorkingDirectory", "User", "Group", "EnvironmentFile", "Environment",
    "Type", "TimeoutStartSec", "ReadWritePaths", "ProtectSystem", "ProtectHome",
    "NoNewPrivileges", "PrivateTmp", "OnCalendar", "Persistent", "Unit",
)


def directives(texte: str) -> dict[str, list[str]]:
    """Les directives d'un fichier d'unité, continuations recollées.

    **Les commentaires et les lignes vides sont écartés** : ils ne changent pas
    ce que systemd exécute, et les comparer ferait rougir la garde sur une
    reformulation. *Ce qu'on compare est le comportement, pas la prose.*
    """
    recolle = texte.replace("\\\n", " ")
    trouvees: dict[str, list[str]] = {}
    for ligne in recolle.splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#") or ligne.startswith(";"):
            continue
        m = re.match(r"^([A-Za-z]+)\s*=\s*(.*)$", ligne)
        if not m:
            continue
        cle, valeur = m.group(1), re.sub(r"\s+", " ", m.group(2).strip())
        trouvees.setdefault(cle, []).append(valeur)
    return trouvees


def comparer(depot: dict, hote: dict) -> list[tuple[str, list[str], list[str]]]:
    """Les directives QUI COMPTENT dont la valeur diffère. **Triées par nom**,
    pour que deux exécutions du même outil se comparent entre elles."""
    ecarts = []
    for cle in sorted(set(depot) | set(hote)):
        if cle not in DIRECTIVES_QUI_COMPTENT:
            continue
        a, b = depot.get(cle, []), hote.get(cle, [])
        if a != b:
            ecarts.append((cle, a, b))
    return ecarts


def lire_hote(unite: str) -> tuple[str | None, list[str]]:
    """`(texte effectif, drop-ins)` vus par systemd, ou `(None, [])` s'il ignore
    l'unité.

    **`systemctl cat` et non la lecture du fichier** : il rend le fichier ET ses
    drop-ins, dans l'ordre où systemd les applique. *Lire
    `/etc/systemd/system/x.service` seul raterait une surcharge — le cas 36.*
    """
    try:
        r = subprocess.run(
            ["systemctl", "cat", unite], capture_output=True, text=True, timeout=20
        )
    except (OSError, subprocess.SubprocessError):
        return None, []
    if r.returncode != 0:
        return None, []
    fichiers = re.findall(r"^# (/\S+)$", r.stdout, flags=re.MULTILINE)
    dropins = [f for f in fichiers if ".d/" in f]
    return r.stdout, dropins


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--detail", action="store_true",
                        help="afficher le diff textuel complet des unités qui divergent")
    args = parser.parse_args(argv)

    unites = sorted(DOSSIER_UNITES.glob("*.service")) + sorted(DOSSIER_UNITES.glob("*.timer"))

    print("=" * 78)
    print("LES UNITÉS DU DÉPÔT CONTRE CELLES DE L'HÔTE")
    print("=" * 78)
    print("\nPORTÉE : lecture seule. Il DIT ce qui diverge, il n'installe rien —")
    print("         l'installation d'une unité est un geste humain en root.")
    print("\n⚠️ La chaîne de déploiement ne copie PAS les unités, et c'est délibéré :")
    print("   `deploy` peut démarrer sept actions nommées, pas écrire dans")
    print("   /etc/systemd/system. Lui donner ce droit lui donnerait celui de")
    print("   faire exécuter n'importe quoi en root.")

    if not unites:
        print(f"\n⛔ Aucune unité dans {DOSSIER_UNITES}.")
        return 2

    absentes, divergentes, conformes, dropins_inconnus = [], [], [], []
    for chemin in unites:
        texte_depot = chemin.read_text(encoding="utf-8")
        texte_hote, dropins = lire_hote(chemin.name)
        if texte_hote is None:
            absentes.append(chemin.name)
            continue
        if dropins:
            dropins_inconnus.append((chemin.name, dropins))
        ecarts = comparer(directives(texte_depot), directives(texte_hote))
        (divergentes if ecarts else conformes).append((chemin.name, ecarts,
                                                       texte_depot, texte_hote))

    print("\n" + "-" * 78)
    print("LE RELEVÉ")
    print("-" * 78)
    print(f"\n   unités au dépôt                : {len(unites)}")
    print(f"   conformes à l'hôte             : {len(conformes)}")
    print(f"   DIVERGENTES                    : {len(divergentes)}")
    print(f"   inconnues de systemd           : {len(absentes)}")
    print(f"   portant un DROP-IN             : {len(dropins_inconnus)}")

    if absentes:
        print("\n   ⚠️ INCONNUES DE SYSTEMD — jamais installées, ou nommées autrement :")
        for nom in absentes:
            print(f"      {nom}")
        print("      (systemd absent de cette machine donne le même résultat —")
        print("       cet outil se lance SUR L'HÔTE.)")

    for nom, dropins in dropins_inconnus:
        print(f"\n   ⚠️ {nom} porte {len(dropins)} drop-in(s) :")
        for f in dropins:
            print(f"      {f}")
        print("      Un drop-in SURCHARGE le fichier d'unité, et le dépôt ne le")
        print("      porte pas. C'est le cas 36 : l'unité de l'hôte diffère de son")
        print("      fichier sans que le fichier change.")

    for nom, ecarts, texte_depot, texte_hote in divergentes:
        print("\n" + "=" * 78)
        print(f"⛔ {nom} — {len(ecarts)} directive(s) divergente(s)")
        print("=" * 78)
        for cle, au_depot, sur_hote in ecarts:
            print(f"\n   {cle}")
            print(f"      dépôt : {au_depot or '(absente)'}")
            print(f"      hôte  : {sur_hote or '(absente)'}")
        if args.detail:
            print("\n   --- diff textuel ---")
            for ligne in difflib.unified_diff(
                texte_hote.splitlines(), texte_depot.splitlines(),
                fromfile=f"hôte:{nom}", tofile=f"dépôt:{nom}", lineterm="", n=2,
            ):
                print(f"   {ligne}")

    print("\n" + "=" * 78)
    if divergentes or absentes or dropins_inconnus:
        print("   POUR INSTALLER — geste humain, en root, sur l'hôte :")
        print("\n      sudo install -m 0644 /opt/falkye/code/deploiement/*.service \\")
        print("                            /opt/falkye/code/deploiement/*.timer \\")
        print("                            /etc/systemd/system/")
        print("      sudo systemctl daemon-reload")
        print("\n   ⚠️ `daemon-reload` NE redémarre rien : il relit les définitions.")
        print("      Une unité oneshot prendra la nouvelle au prochain démarrage;")
        print("      un service durable garde l'ancienne jusqu'à son redémarrage.")
        return 1
    print("   ✅ Toutes les unités du dépôt sont installées et conformes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
