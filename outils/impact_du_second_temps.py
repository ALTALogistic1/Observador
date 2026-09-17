#!/usr/bin/env python3
"""Ce que le SECOND TEMPS change, gain ET coût — **la mesure E, dans la demande
qui construit.**

**La réserve d'Alexandre, posée d'avance et jamais levée** : *« Un correctif qui
gagne 114 et en perd 300 n'est pas un correctif. »*

⚠️ **E ne pouvait pas exister avant la construction** : son second terme est **le
lot que l'élargissement présente**, et ce lot n'existait pas. *Il existe
maintenant.*

## Ce que l'outil rend

**La transition de chaque dossier**, le second temps coupé puis branché —
`elargir=False` contre `elargir=True`, la même population, le même scorage.

| | |
|---|---|
| **le gain** | `trop faible` / `aucun candidat` → **`RETENU`** |
| ⚠️ **le coût** | `RETENU` → **`ambigu`** — *une résolution qui SE DÉRÉSOUT* |
| le déplacement | `trop faible` → `ambigu` : *ni gagné ni perdu, mais plus près* |

⚠️ **Le coût devrait être NUL par construction** — le second temps ne s'exécute
que là où `neq_retenu` a déjà rendu `None`, donc jamais sur un RETENU. **S'il
n'est pas nul, la garantie structurelle est fausse et le correctif est à
reprendre.** *C'est le premier chiffre à lire, avant le gain.*

⚠️ **Aucune écriture, aucune règle modifiée** — seuil 92, écart 8, borne 2 000.

Usage, SUR L'HÔTE, APRÈS un import qui a construit l'index :
    python3 -m outils.impact_du_second_temps
"""
from __future__ import annotations

import argparse
from collections import Counter

from outils.nombres import milliers


def _part(k: int, n: int) -> str:
    return f"{100 * k / n:.1f} %" if n else "—"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--limite", type=int, default=None, help="borner (mise au point)")
    parser.add_argument("--exemples", type=int, default=8)
    args = parser.parse_args(argv)

    from sqlalchemy import func, select

    from falkye.db import refuser_si_cible_non_choisie

    code = refuser_si_cible_non_choisie()
    if code:
        return code

    from falkye.db import get_session
    from falkye.models.company import Company
    from falkye.models.req_mot import REQMot
    from falkye.resolution import FAMILLES, famille_de
    from falkye.sources import req as req_source

    print("=" * 78)
    print("CE QUE LE SECOND TEMPS CHANGE — gain ET coût")
    print("=" * 78)
    print("""
⚠️ CE QUE CETTE MESURE NE DIRA PAS — à lire avant tout chiffre

   ELLE NE DIT PAS QU'UN APPARIEMENT GAGNÉ SOIT JUSTE. Elle compte des
   franchissements de règle, pas des entreprises correctement identifiées.
   *Un dossier qui passe à RETENU peut être apparié à la mauvaise entreprise.*

   ET LE COÛT DEVRAIT ÊTRE NUL PAR CONSTRUCTION : le second temps ne
   s'exécute que là où le premier a échoué. S'il ne l'est pas, ce n'est pas
   un arbitrage à faire — c'est la garantie qui est fausse.

   Aucune écriture. Seuil 92, écart 8, borne 2 000.
""")

    session = get_session()
    try:
        couples = session.execute(
            select(func.count()).select_from(REQMot), bind_arguments={"mapper": REQMot}
        ).scalar() or 0
        print(f"   index par mots : {milliers(couples)} couple(s) (mot, NEQ)")
        if not couples:
            print("\n⛔ L'INDEX EST VIDE. Le second temps ne peut rien élargir, et")
            print("   cette mesure rendrait zéro pour la mauvaise raison.")
            print("   Lancer un import du REQ d'abord — c'est lui qui le construit.")
            return 2

        requete = select(Company).where(Company.neq.is_(None)).order_by(Company.id)
        if args.limite:
            requete = requete.limit(args.limite)
        orphelins = list(session.execute(requete).scalars().all())
        total = len(orphelins)
        print(f"   dossiers sans NEQ : {milliers(total)}\n")

        transitions: Counter = Counter()
        avant_par_famille: Counter = Counter()
        apres_par_famille: Counter = Counter()
        gains: list[tuple[str, str, float]] = []
        couts: list[str] = []

        for i, company in enumerate(orphelins):
            if i and i % 500 == 0:
                print(f"   … {milliers(i)} examinés", flush=True)
            sans = req_source.resolve_neq_by_name(
                session, company.nom_detecte, ville=company.ville, elargir=False
            )
            avec = req_source.resolve_neq_by_name(
                session, company.nom_detecte, ville=company.ville
            )
            f_avant, f_apres = famille_de(sans), famille_de(avec)
            avant_par_famille[f_avant] += 1
            apres_par_famille[f_apres] += 1
            if f_avant != f_apres:
                transitions[(f_avant, f_apres)] += 1
            if f_apres == "RETENU" and f_avant != "RETENU" and len(gains) < args.exemples:
                gains.append((company.nom_detecte or "", avec[0].entry.nom or "",
                              avec[0].score))
            if f_avant == "RETENU" and f_apres != "RETENU" and len(couts) < args.exemples:
                couts.append(f"{company.nom_detecte} : RETENU → {f_apres}")

        # ---- LE COÛT, EN PREMIER --------------------------------------------
        perdus = sum(k for (a, b), k in transitions.items()
                     if a == "RETENU" and b != "RETENU")
        print("\n" + "=" * 78)
        print("LE COÛT — il devrait être NUL par construction")
        print("=" * 78)
        marque = "✓ " if perdus == 0 else "⛔"
        print(f"\n   {marque} RETENUS perdus : {milliers(perdus)}")
        if perdus:
            print("\n   ⛔ LA GARANTIE STRUCTURELLE EST FAUSSE. Le second temps ne devait")
            print("      s'exécuter que là où `neq_retenu` a rendu None, donc jamais sur")
            print("      un RETENU. Le correctif est à reprendre, pas à arbitrer.\n")
            for ligne in couts:
                print(f"      {ligne}")
        else:
            print("      *Le second temps ne s'exécute que là où le premier a échoué.*")

        # ---- LE GAIN ---------------------------------------------------------
        gagnes = sum(k for (a, b), k in transitions.items()
                     if b == "RETENU" and a != "RETENU")
        print("\n" + "=" * 78)
        print("LE GAIN")
        print("=" * 78)
        print(f"\n   ⇒ RETENUS gagnés : {milliers(gagnes)}  ({_part(gagnes, total)} "
              f"des {milliers(total)} dossiers sans NEQ)")

        print(f"\n   {'famille':<18} {'avant':>9} {'après':>9} {'écart':>9}")
        for f in FAMILLES:
            a, b = avant_par_famille.get(f, 0), apres_par_famille.get(f, 0)
            print(f"   {f:<18} {milliers(a):>9} {milliers(b):>9} {b - a:>+9}")

        if transitions:
            print(f"\n   {'transition':<40} {'dossiers':>9}")
            for (a, b), k in sorted(transitions.items(), key=lambda kv: -kv[1]):
                fleche = f"{a} → {b}"
                print(f"   {fleche:<40} {milliers(k):>9}")

        for detecte, registre, score in gains:
            print(f"\n      {detecte[:56]}")
            print(f"         → {registre[:56]!r}  {score:.2f}")

        print("\n" + "=" * 78)
        print("   ⚠️ Un franchissement n'est PAS un appariement juste. Les paires se")
        print("      regardent une à une avant toute écriture.")
        print("=" * 78)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
