#!/usr/bin/env python3
"""Ce que « garder tous les noms » change au miroir — **volume, gain ET coût en
précision**, mesurés AVANT le réimport.

**La réserve d'Alexandre, posée d'avance** *(2026-09-16)* : *« Plus de noms veut
dire plus de candidats récupérés, donc plus d'ambiguïtés possibles. Le rejeu de
ce matin mesurait le gain et son coût en précision ensemble. Fais pareil ici. »*

**Ce que l'outil rend, et pourquoi les trois vont ensemble.**

1. **LE VOLUME** — lignes d'index, octets, durée d'import estimée. *1,7 million de
   noms de plus, ce n'est pas rien, et un import de 33 minutes qui en devient 50
   se décide avant, pas pendant.*
2. **LE GAIN** — combien des non résolues trouvent un NEQ par un nom jeté, **et
   combien en trouvent UN SEUL**. *Un nom qui mène à trois NEQ ne résout rien : il
   déplace le problème du « aucun candidat » vers le « trop de candidats », et le
   moteur refusera les deux.*
3. **LE COÛT** — combien d'entreprises **DÉJÀ RÉSOLUES** verraient apparaître un
   concurrent. ⚠️ **C'est le vrai risque, et il est invisible dans le gain** : une
   entreprise résolue aujourd'hui dont le nom devient partagé par un second NEQ
   **bascule vers l'ambigu et se dérésout**. *Un correctif qui gagne 2 217 et en
   perd 300 n'est pas un correctif qui gagne 2 217.*

⚠️ **PORTÉE — ce que la mesure du coût NE couvre PAS.** Elle compare des formes
normalisées **exactes**. *Le moteur, lui, compare par score flou : un nom
simplement PROCHE peut aussi resserrer l'écart avec le second candidat sans être
identique.* **Le coût rendu ici est donc un PLANCHER**, comme le gain — les deux
sous-estiment dans le même sens, ce qui rend leur rapport lisible même si les
valeurs absolues ne le sont pas.

⚠️ **Rien n'est écrit, rien n'est importé.** *Un impact mesuré n'est pas un impact
subi* — c'est le chiffre sur lequel le réimport se décide.

Usage :
    python3 outils/impact_tous_les_noms.py --chemin /opt/falkye/import
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
import zipfile
from collections import Counter

#: Mesures du 2026-09-06, sur l'hôte : 2 730 146 entrées importées en 33 minutes.
#: **Sert à ESTIMER, jamais à promettre** — la passe des noms est une écriture en
#: masse, pas un upsert ligne à ligne, donc elle ne coûte pas le même prix par
#: ligne. L'estimation est donnée avec sa borne haute pour cette raison.
LIGNES_DE_REFERENCE = 2_730_146
MINUTES_DE_REFERENCE = 33.0

#: Octets par ligne de `req_noms`, estimés : NEQ (10) + nom (~40) + normalisé
#: (~40) + statut + type + horodatage + l'index. **Un ordre de grandeur, annoncé
#: comme tel** — un chiffre recopié est une promesse que personne ne tient.
OCTETS_PAR_LIGNE = 160


def estimer_duree(lignes: int) -> tuple[float, float]:
    """(minutes basses, minutes hautes) pour écrire `lignes` en masse.

    **Une fourchette, jamais un nombre.** *L'écriture en masse est plus rapide
    que l'upsert de référence — combien, on ne l'a pas mesuré.* La borne basse
    suppose 5× plus rapide, la haute suppose le même prix par ligne.
    """
    haute = MINUTES_DE_REFERENCE * lignes / LIGNES_DE_REFERENCE
    return haute / 5.0, haute


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--chemin", required=True, help="l'archive, ou le répertoire")
    parser.add_argument("--exemples", type=int, default=15)
    args = parser.parse_args(argv)

    try:
        from sqlalchemy import select

        from falkye.db import get_session
        from falkye.models.company import Company
        from falkye.sources.column_mapping import normaliser
    except ImportError as exc:  # pragma: no cover - dépend de l'environnement
        print(f"Import impossible ({exc}). Lancer depuis la racine du dépôt.", file=sys.stderr)
        return 2

    from outils.archives_req import avertissement, ligne_de_provenance, resoudre

    archive = resoudre(args.chemin)
    if archive is None:
        print(f"⛔ aucune archive à {args.chemin!r}.", file=sys.stderr)
        return 2

    print("=" * 78)
    print("CE QUE « GARDER TOUS LES NOMS » CHANGE — AVANT LE RÉIMPORT")
    print("=" * 78)
    print(f"\n{ligne_de_provenance(archive)}")
    vieil = avertissement(archive)
    if vieil:
        print(f"\n{vieil}")
    print("\nPORTÉE : rien n'est écrit, rien n'est importé.")
    print("         Gain ET coût sont des PLANCHERS — appariement exact des deux côtés.")

    session = get_session()
    try:
        # Les deux populations du produit, lues une fois.
        non_resolues: dict[str, list] = {}
        resolues: dict[str, list] = {}
        for company in session.execute(select(Company)).scalars().all():
            forme = normaliser(company.nom_detecte or "")
            if not forme:
                continue
            (resolues if company.neq else non_resolues).setdefault(forme, []).append(company)
        print(f"\nentreprises SANS NEQ : {sum(len(v) for v in non_resolues.values())}"
              f"   ({len(non_resolues)} formes)")
        print(f"entreprises AVEC NEQ : {sum(len(v) for v in resolues.values())}"
              f"   ({len(resolues)} formes)")

        interessantes = set(non_resolues) | set(resolues)

        # --- une seule passe sur Nom.csv -----------------------------------
        neqs_par_forme: dict[str, set[str]] = {}
        lignes_en_vigueur = 0
        formes_vides = 0
        lues = 0
        with zipfile.ZipFile(archive) as zf:
            with zf.open("Nom.csv") as brut:
                texte = io.TextIOWrapper(brut, encoding="utf-8-sig", errors="replace")
                for rangee in csv.DictReader(texte):
                    lues += 1
                    nom = (rangee.get("NOM_ASSUJ") or "").strip()
                    neq = (rangee.get("NEQ") or "").strip()
                    if not nom or not neq:
                        continue
                    if (rangee.get("STAT_NOM") or "").strip().upper() != "V":
                        continue
                    forme = normaliser(nom)
                    if not forme:
                        formes_vides += 1
                        continue
                    lignes_en_vigueur += 1
                    if forme in interessantes:
                        neqs_par_forme.setdefault(forme, set()).add(neq)

        # --- 1. le volume ---------------------------------------------------
        print("\n" + "=" * 78)
        print("1. LE VOLUME")
        print("=" * 78)
        octets = lignes_en_vigueur * OCTETS_PAR_LIGNE
        basse, haute = estimer_duree(lignes_en_vigueur)
        print(f"\n   lignes de Nom.csv lues        : {lues:,}".replace(",", " "))
        print(f"   noms EN VIGUEUR à indexer     : {lignes_en_vigueur:,}".replace(",", " "))
        print(f"   écartés (normalisés vides)    : {formes_vides:,}".replace(",", " "))
        print(f"\n   taille estimée de req_noms    : ~{octets / 1024 / 1024:.0f} Mo"
              f"   ({OCTETS_PAR_LIGNE} o/ligne, ordre de grandeur)")
        print(f"   durée d'import ajoutée        : entre ~{basse:.0f} et ~{haute:.0f} min")
        print("\n   ⚠️ Une FOURCHETTE, pas un nombre : l'écriture en masse est plus")
        print("      rapide que l'upsert de référence, et de combien n'a pas été mesuré.")
        print("   ⚠️ La mémoire ne bouge PAS : la passe relit Nom.csv en flux et")
        print("      écrit par lots, elle n'ajoute rien au pic de 3 535 Mo.")

        # --- 2. le gain -----------------------------------------------------
        print("\n" + "=" * 78)
        print("2. LE GAIN — non résolues qui trouveraient un NEQ")
        print("=" * 78)
        gain: Counter = Counter()
        exemples_gain: list = []
        for forme, companies in non_resolues.items():
            neqs = neqs_par_forme.get(forme) or set()
            if not neqs:
                gain["aucun NEQ pour ce nom — rien ne change"] += len(companies)
            elif len(neqs) == 1:
                gain["UN SEUL NEQ — résolution franche"] += len(companies)
                if len(exemples_gain) < args.exemples:
                    exemples_gain.append((companies[0], next(iter(neqs))))
            else:
                gain[f"PLUSIEURS NEQ — ambigu, le moteur refusera"] += len(companies)
        print()
        for classe, n in gain.most_common():
            marque = "   ←" if classe.startswith("UN SEUL") else ""
            print(f"   {n:>7}  {classe}{marque}")
        francs = gain.get("UN SEUL NEQ — résolution franche", 0)
        print(f"\n   → {francs} entreprise(s) se résoudraient franchement.")
        print("   ⚠️ « Franchement » veut dire : un seul NEQ pour ce nom. Le moteur")
        print("      applique encore son seuil de 92 et son écart de 8 — ce compte")
        print("      est un PLAFOND du gain, pas le gain.")

        # --- 3. le coût en précision ----------------------------------------
        print("\n" + "=" * 78)
        print("3. LE COÛT — entreprises DÉJÀ RÉSOLUES qui verraient un concurrent")
        print("=" * 78)
        print("\n   Invisible dans le gain, et c'est le vrai risque : une résolue dont")
        print("   le nom devient partagé bascule vers l'ambigu et SE DÉRÉSOUT.")
        cout: Counter = Counter()
        exemples_cout: list = []
        for forme, companies in resolues.items():
            neqs = neqs_par_forme.get(forme) or set()
            for company in companies:
                autres = neqs - {company.neq}
                if not autres:
                    cout["aucun concurrent — inchangée"] += 1
                else:
                    cout["un concurrent APPARAÎT — risque de dérésolution"] += 1
                    if len(exemples_cout) < args.exemples:
                        exemples_cout.append((company, sorted(autres)[:3]))
        print()
        for classe, n in cout.most_common():
            marque = "   ⚠️" if "APPARAÎT" in classe else ""
            print(f"   {n:>7}  {classe}{marque}")
        menacees = cout.get("un concurrent APPARAÎT — risque de dérésolution", 0)
        print(f"\n   → {menacees} entreprise(s) résolues sont MENACÉES.")
        print(f"\n   RAPPORT : {francs} gain(s) franc(s) pour {menacees} menacée(s)"
              + (f"   ({francs / menacees:.1f} pour 1)" if menacees else "   (aucune menacée)"))
        print("\n   ⚠️ Menacée ne veut pas dire perdue : le concurrent doit encore")
        print("      scorer assez haut pour resserrer l'écart sous 8 points. Ce compte")
        print("      est un PLAFOND du risque, comme le gain est un plafond du gain.")

        for titre, lot in (("GAINS FRANCS", exemples_gain), ("MENACÉES", exemples_cout)):
            if not lot:
                continue
            print("\n" + "-" * 78)
            print(f"{titre} — {len(lot)} montrée(s)")
            print("-" * 78)
            for company, cible in lot:
                print(f"\n   détecté : {(company.nom_detecte or '')[:62]}")
                print(f"   {'trouverait' if titre.startswith('GAIN') else 'neq actuel'} : "
                      f"{company.neq or cible}")
                if titre == "MENACÉES":
                    print(f"   concurrent(s) : {', '.join(cible)}")

        print("\n" + "=" * 78)
        print("   Rien n'a été importé. Les deux comptes sont des PLAFONDS mesurés")
        print("   sur un appariement EXACT; le moteur, lui, compare par score.")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
