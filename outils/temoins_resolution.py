#!/usr/bin/env python3
"""Les témoins de résolution — **capturer avant le réimport, vérifier après.**

**La consigne qui fait exister cet outil** *(Alexandre, 2026-09-16)* : *« Les 43
menacées ne doivent pas disparaître dans le bruit. Écris-les quelque part — après
le réimport, il faudra vérifier qu'elles se sont bien DÉRÉSOLUES, et non qu'elles
ont MAL RÉSOLU. Une entreprise qui bascule vers une mauvaise réponse est pire
qu'une qui bascule vers l'ambigu. »*

**La distinction est tout l'outil, et aucun compte agrégé ne la porte.**

| après le réimport | ce que ça vaut |
|---|---|
| même NEQ retenu | **inchangée** — le correctif ne l'a pas touchée |
| plus aucun NEQ retenu | **dérésolue** — *visible, réversible, sans conséquence fausse* |
| **un AUTRE NEQ retenu** | ⛔ **mal résolue** — *le dossier change d'identité en silence* |
| l'entreprise n'existe plus | fusionnée par la déduplication — à examiner |

⚠️ **Il capture TOUTES les résolues, pas les 43.** *Les 43 sont une PRÉDICTION,
tirée d'un appariement exact sur l'archive; le moteur, lui, compare par score et
peut en toucher d'autres.* **Une garde qui ne surveille que ce qu'elle a prévu ne
surveille rien** — le surensemble coûte quelques milliers de lignes de JSON et
couvre ce qu'on n'a pas vu venir.

⚠️ **PORTÉE.** *Aucune écriture, dans les deux sens.* La capture lit et écrit un
fichier hors base; la vérification lit la base et **ne corrige rien** — elle
rapporte. *Un basculement constaté est une décision, pas une suite.*

⚠️ **Ce qu'il ne peut pas dire** : si le NEQ retenu est le **bon**. *Il compare un
avant à un après; ni l'un ni l'autre n'est une vérité terrain.* **Un changement
d'identité est un signal d'alerte, pas une preuve d'erreur** — et l'inverse est
vrai aussi : une résolution inchangée peut avoir toujours été fausse.

Usage :
    # AVANT le réimport, et il faut que ce soit avant
    python3 outils/temoins_resolution.py --capturer --vers /var/lib/falkye/temoins.json

    # APRÈS
    python3 outils/temoins_resolution.py --verifier --depuis /var/lib/falkye/temoins.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

#: Montrées par classe. Les mal résolues sont montrées **toutes**, quelle que
#: soit cette borne — *c'est le cas qu'on ne veut pas voir tronqué.*
EXEMPLES_DEFAUT = 15


def classer(avant: dict, neq_apres: str | None, existe: bool) -> str:
    """Le verdict d'un témoin. **Quatre issues, et la troisième est la seule
    grave.**"""
    if not existe:
        return "l'entreprise n'existe plus — fusionnée"
    if neq_apres is None:
        return "DÉRÉSOLUE — visible et réversible"
    if neq_apres == avant["neq"]:
        return "inchangée"
    return "MAL RÉSOLUE — le dossier change d'identité"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--capturer", action="store_true", help="relever l'état AVANT")
    parser.add_argument(
        "--non-resolues", action="store_true",
        help="capturer les SANS NEQ plutôt que les résolues — la ligne de base "
             "du mur, irrécupérable une fois le miroir réécrit",
    )
    parser.add_argument("--verifier", action="store_true", help="comparer l'état APRÈS")
    parser.add_argument("--vers", help="fichier de capture à écrire")
    parser.add_argument("--depuis", help="fichier de capture à relire")
    parser.add_argument("--exemples", type=int, default=EXEMPLES_DEFAUT)
    args = parser.parse_args(argv)

    if args.capturer == args.verifier:
        print("Choisir --capturer OU --verifier, pas les deux ni aucun.", file=sys.stderr)
        return 2
    chemin = Path(args.vers or args.depuis or "")
    if not str(chemin):
        print("Donner --vers (capture) ou --depuis (vérification).", file=sys.stderr)
        return 2

    try:
        from sqlalchemy import select

        from falkye.db import get_session
        from falkye.models.company import Company
        from falkye.resolution import neq_retenu
        from falkye.sources.req import resolve_neq_by_name
    except ImportError as exc:  # pragma: no cover - dépend de l'environnement
        print(f"Import impossible ({exc}). Lancer depuis la racine du dépôt.", file=sys.stderr)
        return 2

    # LA CIBLE, ANNONCÉE ET EXIGÉE — juste avant d'ouvrir, jamais après
    # `parse_args` : un mode qui ne touche aucune base ne doit pas être
    # refusé. Sans ce refus, le repli CRÉE `./data/*.sqlite3` dans le
    # répertoire courant et le verdict porte sur une base vide.
    from falkye.db import refuser_si_cible_non_choisie

    code = refuser_si_cible_non_choisie()
    if code:
        return code

    session = get_session()
    try:
        # ---- CAPTURE ------------------------------------------------------
        if args.capturer:
            # LA LIGNE DE BASE DU MUR, et elle est IRRÉCUPÉRABLE après le réimport :
            # le miroir aura changé, et « ce que l'appariement rendait avant » ne
            # se recalcule plus. Le meilleur score est relevé ligne à ligne, pas
            # seulement le statut — un statut dit qu'on a échoué, un score dit
            # de combien.
            if args.non_resolues:
                cibles = session.execute(
                    select(Company).where(Company.neq.is_(None))
                ).scalars().all()
            else:
                cibles = session.execute(
                    select(Company).where(Company.neq.is_not(None))
                ).scalars().all()
            temoins = []
            for c in cibles:
                fiche = {
                    "id": c.id,
                    "nom_detecte": c.nom_detecte,
                    "ville": c.ville,
                    "neq": c.neq,
                    "statut_resolution": (
                        c.statut_resolution.value if c.statut_resolution else None
                    ),
                }
                if args.non_resolues:
                    matches = resolve_neq_by_name(
                        session, c.nom_detecte or "", ville=c.ville
                    )
                    fiche["meilleur_score"] = matches[0].score if matches else None
                    fiche["meilleur_neq"] = matches[0].entry.neq if matches else None
                    fiche["second_score"] = matches[1].score if len(matches) > 1 else None
                    fiche["nb_candidats"] = len(matches)
                temoins.append(fiche)
            chemin.parent.mkdir(parents=True, exist_ok=True)
            chemin.write_text(
                json.dumps(
                    {
                        "capture_le": datetime.now(timezone.utc).isoformat(),
                        "temoins": temoins,
                    },
                    ensure_ascii=False,
                    indent=1,
                ),
                encoding="utf-8",
            )
            print("=" * 78)
            print("CAPTURE DES TÉMOINS — AVANT LE RÉIMPORT")
            print("=" * 78)
            quoi = "SANS NEQ (ligne de base du mur)" if args.non_resolues else "résolues"
            print(f"\n   {len(temoins)} entreprise(s) {quoi} relevée(s)")
            print(f"   écrites dans : {chemin}")
            if args.non_resolues:
                print("\n   ⚠️ Le meilleur SCORE est relevé, pas seulement le statut :")
                print("      un statut dit qu'on a échoué, un score dit de COMBIEN.")
                print("      Après le réimport, cet avant ne se recalcule plus.")
            else:
                print("\n   ⚠️ TOUTES les résolues, pas les 43 prédites : une garde qui ne")
                print("      surveille que ce qu'elle a prévu ne surveille rien.")
            print("\n   ⚠️ Cette capture doit précéder le réimport. Faite après, elle")
            print("      relèverait l'état d'arrivée et ne comparerait rien.")
            return 0

        # ---- VÉRIFICATION --------------------------------------------------
        if not chemin.is_file():
            print(f"⛔ capture introuvable : {chemin}", file=sys.stderr)
            print("   Sans elle, il n'y a pas d'AVANT — et donc rien à comparer.",
                  file=sys.stderr)
            return 2
        donnees = json.loads(chemin.read_text(encoding="utf-8"))
        temoins = donnees["temoins"]

        print("=" * 78)
        print("VÉRIFICATION DES TÉMOINS — APRÈS LE RÉIMPORT")
        print("=" * 78)
        print(f"\n   capture du : {donnees.get('capture_le', '(inconnue)')}")
        print(f"   témoins     : {len(temoins)}")
        print("\nPORTÉE : aucune écriture. Un basculement constaté est une décision,")
        print("         pas une suite. Et ni l'avant ni l'après n'est une vérité terrain.")

        classes: Counter = Counter()
        mal_resolues: list = []
        deresolues: list = []
        for avant in temoins:
            company = session.get(Company, avant["id"])
            if company is None:
                classes[classer(avant, None, existe=False)] += 1
                continue
            matches = resolve_neq_by_name(
                session, avant["nom_detecte"] or "", ville=avant.get("ville")
            )
            neq_apres = neq_retenu(matches)
            classe = classer(avant, neq_apres, existe=True)
            classes[classe] += 1
            if classe.startswith("MAL RÉSOLUE"):
                mal_resolues.append((avant, neq_apres, matches))
            elif classe.startswith("DÉRÉSOLUE"):
                deresolues.append((avant, matches))

        print("\n" + "-" * 78)
        print("LE RÉSULTAT")
        print("-" * 78)
        print()
        for classe, n in classes.most_common():
            marque = "   ⛔" if classe.startswith("MAL RÉSOLUE") else ""
            print(f"   {n:>7}  {classe}{marque}")

        # Les mal résolues sont montrées TOUTES — jamais tronquées.
        if mal_resolues:
            print("\n" + "=" * 78)
            print(f"⛔ LES {len(mal_resolues)} MAL RÉSOLUES — toutes, jamais tronquées")
            print("=" * 78)
            print("\n   Une entreprise qui bascule vers une MAUVAISE réponse est pire")
            print("   qu'une qui bascule vers l'ambigu : la seconde se voit, la")
            print("   première se présente comme un fait.")
            for avant, neq_apres, matches in mal_resolues:
                print(f"\n   détecté   : {(avant['nom_detecte'] or '')[:60]}")
                print(f"   neq AVANT : {avant['neq']}")
                print(f"   neq APRÈS : {neq_apres}")
                for m in matches[:3]:
                    print(f"      {m.score:>6.1f}  {m.entry.neq}  {(m.entry.nom or '')[:44]}")
        else:
            print("\n   ✅ Aucune mal résolue. C'est le résultat qu'on voulait.")

        if deresolues:
            print("\n" + "-" * 78)
            print(f"DÉRÉSOLUES — {len(deresolues)}, dont "
                  f"{min(args.exemples, len(deresolues))} montrée(s)")
            print("-" * 78)
            print("\n   Acceptable : l'entreprise redevient candidate, rien de faux")
            print("   n'est présenté. Mais chacune est une résolution PERDUE.")
            for avant, matches in deresolues[: args.exemples]:
                print(f"\n   détecté   : {(avant['nom_detecte'] or '')[:60]}")
                print(f"   neq perdu : {avant['neq']}")
                for m in matches[:2]:
                    print(f"      {m.score:>6.1f}  {m.entry.neq}  {(m.entry.nom or '')[:44]}")

        print("\n" + "=" * 78)
        print("   ⚠️ Un changement d'identité est un signal d'ALERTE, pas une preuve")
        print("      d'erreur — et l'inverse tient aussi : une résolution inchangée")
        print("      peut avoir toujours été fausse.")
        return 1 if mal_resolues else 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
