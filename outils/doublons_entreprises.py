#!/usr/bin/env python3
"""Combien de dossiers d'entreprise en désignent une seule?

**Le fait qui a écrit cet outil** *(2026-09-16)*. La passe de reprise a buté sur
`UNIQUE constraint failed: companies.neq`. En cherchant pourquoi, son rapport
montrait **69 NEQ déjà pris, tous des doublons de graphie** — « Annexair inc. »
contre « Annexair Inc », « AYE3D inc. » contre « AYE3D Inc. ».

⚠️ **Ces 69 sont ceux que cette passe-là a rencontrés. Rien ne dit que c'est
tout.** *Un compte agrégé répond « combien », jamais « où »* — et personne
n'avait jamais posé la question à la base entière.

**PORTÉE : mesure seule. Cet outil n'écrit rien, ne fusionne rien, ne propose
rien.** *Alexandre l'a demandé ainsi, et c'est juste : on ne corrige pas une
population qu'on n'a pas encore regardée.*

## Trois familles, et elles ne se recouvrent pas

1. **Graphie IDENTIQUE** — même `nom_detecte_normalise`. Le cas le moins
   discutable : la normalisation a déjà retiré casse, accents et ponctuation, et
   il reste deux dossiers.
2. **Graphie PROCHE, tous deux sans NEQ** — mesuré avec
   `trouver_meilleur_candidat_fusion`, **la fonction du produit et ses seuils**
   (90 candidat / 95 fusion auto). *Une règle recopiée mesurerait sa propre
   copie.*
3. ⚠️ **Un dossier RÉSOLU et un dossier NON RÉSOLU pour la même entreprise.**
   `Company.neq` est `unique=True`, donc **deux dossiers résolus ne peuvent pas
   être doublons** — la contrainte l'interdit. *Mais un résolu et un non-résolu
   cohabitent sans rien violer*, et c'est exactement ce que la passe a trouvé.
   **C'est la famille que la contrainte rend invisible.**

⚠️ **La famille 2 sous-compte, et il faut le savoir.**
`trouver_meilleur_candidat_fusion` rend le MEILLEUR candidat, pas tous : un
groupe de trois dossiers proches est vu comme des paires, jamais comme un
groupe. *Le chiffre est un plancher, pas un total* — et c'est le chiffre que le
produit voit lui-même, ce qui est la mesure honnête de ce qu'il rate.

Usage, SUR L'HÔTE :
    python3 -m outils.doublons_entreprises
    python3 -m outils.doublons_entreprises --exemples 30
    python3 -m outils.doublons_entreprises --sans-flou     # familles 1 et 3 seules
"""
from __future__ import annotations

from outils.nombres import milliers

import argparse
from collections import defaultdict


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--exemples", type=int, default=12, help="paires montrées par famille")
    parser.add_argument("--sans-flou", action="store_true",
                        help="sauter la famille 2 (la plus coûteuse : une requête par dossier)")
    parser.add_argument("--limite", type=int, default=None, help="borner la famille 2")
    args = parser.parse_args(argv)

    from sqlalchemy import func, select

    from falkye.db import refuser_si_cible_non_choisie

    code = refuser_si_cible_non_choisie()
    if code:
        return code

    from falkye.db import get_session
    from falkye.models.company import Company

    print("=" * 78)
    print("LES DOUBLONS DE DOSSIER — combien en désignent une seule entreprise?")
    print("=" * 78)
    print("\nPORTÉE : mesure seule. N'écrit rien, ne fusionne rien, ne propose rien.\n")
    # LA PORTÉE, DANS LA SORTIE ET PAS DANS LA DOCUMENTATION (cas 33).
    # *Un instrument mesure ce qu'il a été construit pour mesurer; son zéro ne
    # dit rien de ce qu'il ne regarde pas.*
    print("⚠️ PÉRIMÈTRE DE CETTE MESURE — à lire avant les chiffres")
    print("   Elle porte sur les `Company` du produit, résolues contre le REQ.")
    print("   Le REQ est le registre des entités PRIVÉES.")
    print("   Elle ne dit donc RIEN de :")
    print("     • les entités PUBLIQUES — aucun registre pivot n'est choisi (D27 ⬜),")
    print("       aucune règle de classement public/privé n'existe (D28 ⬜);")
    print("     • les donneurs d'ouvrage du SEAO — ils n'existent comme entité")
    print("       NULLE PART dans le produit (D43 ⬜), donc aucune ligne les concernant")
    print("       n'entre dans ce compte;")
    print("     • la FAMILLE d'entité — la structure actuelle ne la porte pas.")
    print("   Sur le SEAO : identifiant de l'organisme acheteur présent à 100 %,")
    print("   celui du fournisseur jamais un NEQ — 56 % d'ambiguïté sur les")
    print("   entreprises, ZÉRO sur les organismes publics (mandat, chantiers 3+4).")
    print("   *Le chiffre ci-dessous est vrai sur son périmètre, et son périmètre")
    print("   est la moitié privée d'une population qui en compte deux.*")
    print()


    session = get_session()
    try:
        total = session.execute(select(func.count()).select_from(Company)).scalar() or 0
        sans_neq = session.execute(
            select(func.count()).select_from(Company).where(Company.neq.is_(None))
        ).scalar() or 0
        print(f"   dossiers au total      : {milliers(total)}")
        print(f"   dont sans NEQ          : {milliers(sans_neq)}")

        # --- FAMILLE 1 : graphie identique -----------------------------------
        print("\n" + "-" * 78)
        print("FAMILLE 1 — GRAPHIE IDENTIQUE (même nom normalisé)")
        print("-" * 78)
        groupes = session.execute(
            select(Company.nom_detecte_normalise, func.count().label("n"))
            .group_by(Company.nom_detecte_normalise)
            .having(func.count() > 1)
            .order_by(func.count().desc())
        ).all()
        dossiers_1 = sum(n for _, n in groupes)
        print(f"\n   groupes                : {milliers(len(groupes))}")
        print(f"   dossiers impliqués     : {milliers(dossiers_1)}")
        print(f"   dossiers EN TROP       : {milliers(dossiers_1 - len(groupes))}")
        for nom_norm, n in groupes[: args.exemples]:
            membres = session.execute(
                select(Company).where(Company.nom_detecte_normalise == nom_norm)
            ).scalars().all()
            print(f"\n   « {nom_norm} »  ×{n}")
            for c in membres:
                marque = f"NEQ {c.neq}" if c.neq else "sans NEQ"
                print(f"      #{c.id:<7} {marque:<18} « {c.nom_detecte} »")

        # --- FAMILLE 3 : un résolu et un non résolu ---------------------------
        # Placée AVANT la famille 2 : elle est peu coûteuse, et c'est celle que
        # la contrainte d'unicité rend invisible.
        print("\n" + "-" * 78)
        print("FAMILLE 3 — UN DOSSIER RÉSOLU ET UN NON RÉSOLU, même graphie normalisée")
        print("-" * 78)
        print("\n   ⚠️ `Company.neq` est UNIQUE : deux dossiers RÉSOLUS ne peuvent pas")
        print("      être doublons. Cette famille est celle que la contrainte cache.\n")
        mixtes = 0
        exemples_3 = []
        for nom_norm, _ in groupes:
            membres = session.execute(
                select(Company).where(Company.nom_detecte_normalise == nom_norm)
            ).scalars().all()
            resolus = [c for c in membres if c.neq]
            orphelins = [c for c in membres if not c.neq]
            if resolus and orphelins:
                mixtes += 1
                if len(exemples_3) < args.exemples:
                    exemples_3.append((nom_norm, resolus, orphelins))
        print(f"   groupes MIXTES         : {milliers(mixtes)}")
        for nom_norm, resolus, orphelins in exemples_3:
            print(f"\n   « {nom_norm} »")
            for c in resolus:
                print(f"      #{c.id:<7} RÉSOLU    {c.neq}  « {c.nom_detecte} »")
            for c in orphelins:
                print(f"      #{c.id:<7} sans NEQ        « {c.nom_detecte} »")

        # --- FAMILLE 2 : graphie proche, tous deux sans NEQ -------------------
        print("\n" + "-" * 78)
        print("FAMILLE 2 — GRAPHIE PROCHE, les deux sans NEQ")
        print("-" * 78)
        if args.sans_flou:
            print("\n   SAUTÉE (--sans-flou). ⚠️ Sautée n'est pas nulle.")
            return 0

        from falkye.dedup_entreprises import (
            SEUIL_FUSION_AUTO,
            SEUIL_FUSION_CANDIDAT,
            trouver_meilleur_candidat_fusion,
        )

        print(f"\n   seuils DU PRODUIT : candidat ≥ {SEUIL_FUSION_CANDIDAT:.0f}, "
              f"fusion auto ≥ {SEUIL_FUSION_AUTO:.0f}")
        print("   ⚠️ Plancher, pas total : la fonction rend le MEILLEUR candidat,")
        print("      donc un groupe de trois est vu comme des paires.\n")

        requete = select(Company).where(Company.neq.is_(None)).order_by(Company.id)
        if args.limite:
            requete = requete.limit(args.limite)
        orphelins = list(session.execute(requete).scalars().all())

        paires: set[tuple[int, int]] = set()
        scores_par_paire: dict[tuple[int, int], float] = {}
        for i, company in enumerate(orphelins):
            if i and i % 1000 == 0:
                print(f"   … {milliers(i)} dossiers examinés", flush=True)
            meilleur = trouver_meilleur_candidat_fusion(
                session, company.nom_detecte_normalise, company.ville,
                exclure_id=company.id,
            )
            if meilleur is None:
                continue
            paire = tuple(sorted((company.id, meilleur.company.id)))
            if paire not in paires:
                paires.add(paire)
                scores_par_paire[paire] = meilleur.score

        # Les groupes connexes, pour ne pas compter un trio comme trois doublons.
        voisins: dict[int, set[int]] = defaultdict(set)
        for a, b in paires:
            voisins[a].add(b)
            voisins[b].add(a)
        vus: set[int] = set()
        groupes_flous = 0
        dossiers_flous = 0
        for depart in voisins:
            if depart in vus:
                continue
            pile, groupe = [depart], []
            while pile:
                n = pile.pop()
                if n in vus:
                    continue
                vus.add(n)
                groupe.append(n)
                pile.extend(voisins[n] - vus)
            groupes_flous += 1
            dossiers_flous += len(groupe)

        auto = sum(1 for s in scores_par_paire.values() if s >= SEUIL_FUSION_AUTO)
        print(f"\n   dossiers examinés      : {milliers(len(orphelins))}")
        print(f"   paires trouvées        : {milliers(len(paires))}")
        print(f"   groupes connexes       : {milliers(groupes_flous)}")
        print(f"   dossiers impliqués     : {milliers(dossiers_flous)}")
        print(f"   dossiers EN TROP       : {milliers(dossiers_flous - groupes_flous)}")
        print(f"   dont score ≥ {SEUIL_FUSION_AUTO:.0f}       : {milliers(auto)} paire(s)")

        for paire, score in sorted(scores_par_paire.items(), key=lambda kv: -kv[1])[: args.exemples]:
            a, b = (session.get(Company, paire[0]), session.get(Company, paire[1]))
            print(f"\n   score {score:.1f}")
            print(f"      #{a.id:<7} « {a.nom_detecte} »   {a.ville or '(sans ville)'}")
            print(f"      #{b.id:<7} « {b.nom_detecte} »   {b.ville or '(sans ville)'}")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
