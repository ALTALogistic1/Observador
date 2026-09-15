#!/usr/bin/env python3
"""L'entonnoir, étage par étage — **laquelle des trois vérifications bloque, et
dans quelle proportion.**

**Le fait qui justifie cet outil** *(Alexandre, 2026-09-16)* :

    11 556  entreprises détectées
     8 395  sans identité                          73 % du portefeuille
     3 161  avec un NEQ
        92  passent la vérification complète       ← pourquoi seulement 92 ?

**Le corpus exige trois choses** *(spec section 6)* : un **statut légal** non
radié, un **signe d'activité** que le web ne contredit pas, et une **cohérence
d'identité** — la résolution NEQ. *Le correctif du 16 septembre règle la
troisième.* **Personne n'a mesuré laquelle des deux autres bloque.**

⚠️ **Et c'est ce qui décide si le correctif rapporte vraiment.** *2 217
entreprises de plus avec un NEQ ne servent à rien si elles échouent ensuite sur
la même chose.* **À lancer APRÈS le réimport, pas avant** — avant, il mesure
l'état qu'on s'apprête à changer, et le chiffre serait périmé en trente minutes.

**Ce que l'outil sépare, et pourquoi chaque séparation compte.**

1. **L'entonnoir brut** : détectées → avec NEQ → vérifiées. *Les trois comptes
   qu'on cite de mémoire, relus à la source.*
2. **Le motif d'exclusion, par étage.** `EXCLU_RADIEE`, `EXCLU_RESOLUTION_AMBIGUE`,
   `EXCLU_SITE_INACTIF`, `NON_VERIFIE` — **quatre états, jamais trois** : *une
   entreprise qui n'a jamais été vérifiée n'est pas une entreprise qui a échoué,
   et les fondre ferait lire un blocage là où il n'y a qu'une absence de passage.*
3. **Le statut de résolution croisé avec le statut légal.** *Une entreprise
   radiée ET ambiguë est comptée une fois dans le motif qui l'a exclue en
   premier* — l'ordre des vérifications est celui du moteur, emprunté, pas
   réinventé ici.
4. **Ce que le correctif peut atteindre.** Parmi les exclues pour résolution, la
   part qui deviendrait vérifiable **si et seulement si** la résolution réussit —
   c'est-à-dire celles dont le statut légal ne les exclut pas déjà. ⚠️ **Le
   signe d'activité, lui, ne peut PAS être préjugé** : il dépend d'un
   enrichissement web qui n'a pas eu lieu pour une entreprise jamais vérifiée.
   *L'outil compte donc un PLAFOND, et le dit.*

⚠️ **PORTÉE.** Lecture seule, base durable. Il **emprunte
`verifier_avant_enrichissement`** au moteur plutôt que de recopier ses règles —
*une vérification recopiée mesurerait sa propre copie.* Aucun enrichissement
n'est déclenché : le statut du web est lu tel qu'il a été enregistré, jamais
rejoué.

Usage :
    python3 outils/entonnoir_verification.py
    python3 outils/entonnoir_verification.py --exemples 20
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter


def part(compteur: Counter, valeur) -> float:
    total = sum(compteur.values())
    return 100.0 * compteur.get(valeur, 0) / total if total else 0.0


def barre(valeur: int, total: int, largeur: int = 28) -> str:
    """Une barre proportionnelle. **Vide quand le total est nul** — pas une barre
    pleine, pas une barre d'un caractère : rien, parce qu'il n'y a rien à
    représenter."""
    if not total:
        return ""
    plein = max(1, round(largeur * valeur / total)) if valeur else 0
    return "█" * plein


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--exemples", type=int, default=10)
    args = parser.parse_args(argv)

    try:
        from sqlalchemy import select

        from falkye.db import get_session
        from falkye.models.company import (
            Company,
            StatutLegal,
            StatutResolution,
            StatutVerification,
        )
        from falkye.verification import verifier_avant_enrichissement
    except ImportError as exc:  # pragma: no cover - dépend de l'environnement
        print(f"Import impossible ({exc}). Lancer depuis la racine du dépôt.", file=sys.stderr)
        return 2

    session = get_session()
    try:
        entreprises = session.execute(select(Company)).scalars().all()
        total = len(entreprises)

        print("=" * 78)
        print("L'ENTONNOIR — laquelle des trois vérifications bloque")
        print("=" * 78)
        print("\nPORTÉE : lecture seule. Aucun enrichissement déclenché — le statut")
        print("         du web est lu tel qu'enregistré, jamais rejoué.")
        print("         Les règles sont EMPRUNTÉES à falkye/verification.py.")

        if not total:
            print("\nAucune entreprise en base. Rien à mesurer.")
            print("⚠️ Ce n'est pas « 0 % passent » : c'est zéro mesure.")
            return 0

        avec_neq = [c for c in entreprises if c.neq]
        verifiees = [c for c in entreprises
                     if c.statut_verification == StatutVerification.VERIFIE]

        # --- 1. l'entonnoir brut --------------------------------------------
        print("\n" + "-" * 78)
        print("1. L'ENTONNOIR")
        print("-" * 78)
        print()
        for libelle, n in (
            ("détectées", total),
            ("avec un NEQ", len(avec_neq)),
            ("vérifiées (présentables)", len(verifiees)),
        ):
            print(f"   {libelle:<28}{n:>8}{100 * n / total:>8.1f}%  {barre(n, total)}")

        # --- 2. le motif, par étage ------------------------------------------
        print("\n" + "-" * 78)
        print("2. LE MOTIF — quatre états, jamais trois")
        print("-" * 78)
        print("\n   ⚠️ NON_VERIFIE n'est pas un échec : c'est une entreprise qui n'est")
        print("      jamais passée par la vérification. Le fondre avec les exclusions")
        print("      ferait lire un blocage là où il n'y a qu'une absence de passage.")
        motifs: Counter = Counter(
            (c.statut_verification.value if c.statut_verification else "(aucun)")
            for c in entreprises
        )
        print()
        for motif, n in motifs.most_common():
            print(f"   {motif:<32}{n:>8}{part(motifs, motif):>8.1f}%  {barre(n, total)}")

        # --- 3. les deux autres conditions, isolées ---------------------------
        print("\n" + "-" * 78)
        print("3. LES TROIS CONDITIONS, ISOLÉES — sur les entreprises AVEC un NEQ")
        print("-" * 78)
        print("\n   La résolution est acquise pour celles-ci. Reste le statut légal")
        print("   et le signe d'activité. C'est ICI que se lit ce qui bloque.")
        if not avec_neq:
            print("\n   Aucune entreprise avec un NEQ — rien à isoler.")
        else:
            legal: Counter = Counter(
                (c.statut_legal.value if c.statut_legal else "(inconnu)") for c in avec_neq
            )
            print(f"\n   STATUT LÉGAL ({len(avec_neq)} entreprises)")
            for valeur, n in legal.most_common():
                print(f"      {valeur:<28}{n:>8}{part(legal, valeur):>8.1f}%  {barre(n, len(avec_neq))}")

            # Le verdict AVANT enrichissement, emprunté au moteur : il isole ce
            # que le statut légal et la résolution excluent, sans le web.
            avant: Counter = Counter(
                verifier_avant_enrichissement(c).value for c in avec_neq
            )
            print(f"\n   VERDICT AVANT ENRICHISSEMENT (règle du moteur)")
            for valeur, n in avant.most_common():
                print(f"      {valeur:<28}{n:>8}{part(avant, valeur):>8.1f}%  {barre(n, len(avec_neq))}")

            passent_avant = avant.get(StatutVerification.NON_VERIFIE.value, 0)
            bloquees_apres = passent_avant - len(verifiees)
            print(f"\n   → {passent_avant} passent les deux premières conditions.")
            print(f"   → {len(verifiees)} sont finalement vérifiées.")
            if bloquees_apres > 0:
                print(f"\n   ⛔ {bloquees_apres} SE PERDENT ENTRE LES DEUX.")
                print("      C'est le SIGNE D'ACTIVITÉ, ou un enrichissement jamais fait.")
                print("      ⚠️ Les deux se ressemblent dans ce compte et n'ont pas le")
                print("         même remède : un site qui contredit le signal est une")
                print("         exclusion; un enrichissement jamais lancé est une lacune.")
                print(f"      Le motif `{StatutVerification.EXCLU_SITE_INACTIF.value}` "
                      f"les sépare : {motifs.get(StatutVerification.EXCLU_SITE_INACTIF.value, 0)}"
                      " l'ont explicitement.")
            elif bloquees_apres == 0:
                print("\n   ✅ Aucune ne se perd après : le blocage est entièrement")
                print("      dans les deux premières conditions.")

        # --- 4. ce que le correctif peut atteindre ----------------------------
        print("\n" + "-" * 78)
        print("4. CE QUE LE CORRECTIF DES NOMS PEUT ATTEINDRE")
        print("-" * 78)
        sans_neq = [c for c in entreprises if not c.neq]
        radiees_sans_neq = sum(
            1 for c in sans_neq if c.statut_legal == StatutLegal.RADIEE
        )
        ambigues = sum(
            1 for c in entreprises if c.statut_resolution == StatutResolution.AMBIGU
        )
        print(f"\n   sans NEQ                         : {len(sans_neq)}")
        print(f"   … dont déjà connues RADIÉES      : {radiees_sans_neq}"
              "   (le NEQ ne les sauverait pas)")
        print(f"   classées AMBIGUËS                 : {ambigues}")
        print(f"\n   PLAFOND atteignable par le correctif : "
              f"{len(sans_neq) - radiees_sans_neq}")
        print("\n   ⚠️ C'est un PLAFOND, et il est large. Le signe d'activité ne peut")
        print("      pas être préjugé : il dépend d'un enrichissement web qui n'a pas")
        print("      eu lieu pour une entreprise jamais vérifiée. **Une entreprise qui")
        print("      gagne un NEQ entre dans l'entonnoir; elle n'en sort pas pour autant.**")

        # --- les exemples -------------------------------------------------------
        for motif in (StatutVerification.EXCLU_SITE_INACTIF,
                      StatutVerification.EXCLU_RADIEE):
            lot = [c for c in entreprises if c.statut_verification == motif][: args.exemples]
            if not lot:
                continue
            print("\n" + "-" * 78)
            print(f"{motif.value} — {len(lot)} montrée(s)")
            print("-" * 78)
            for c in lot:
                print(f"   {(c.nom_detecte or '')[:52]:<54} neq={c.neq or '—'}")

        print("\n" + "=" * 78)
        print("   ⚠️ À relancer APRÈS le réimport. Lancé avant, il mesure l'état")
        print("      qu'on s'apprête à changer — et le chiffre serait périmé en")
        print("      trente minutes.")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
