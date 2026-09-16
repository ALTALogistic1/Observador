#!/usr/bin/env python3
"""Que rapporterait un dossier capable de porter PLUSIEURS noms?

**La question d'Alexandre** *(2026-09-16)*. Le miroir permet plusieurs noms par
NEQ — **1 505 879 paires, 41,7 % des entreprises du registre**. Le dossier ne le
permet pas : un nom, un NEQ. *Donc le produit suppose qu'une entreprise n'est
nommée que d'une façon, et le registre dit le contraire.*

⚠️ **PORTÉE : mesure seule.** Aucune écriture, aucune structure créée, aucune
proposition appliquée. *On ne change pas une forme avant d'avoir chiffré ce
qu'elle rapporte.*

## Ce qui est compté, et la nuance qui décide

La récupération **ne change pas** : `resolve_neq_by_name` rend les mêmes
candidats, et `neq_retenu` décide pareil. **Ce qui change, c'est ce qu'on peut
FAIRE d'une résolution réussie.**

Aujourd'hui, un NEQ retenu ne sert que si le NEQ est **libre**. Trois issues
échouent, et les trois sont des noms de plus :

1. le NEQ est **déjà porté** par un autre dossier;
2. **deux dossiers du lot** visent le même NEQ — un seul peut l'avoir;
3. *(hors de portée ici)* un futur signal portant ce nom-là.

*Compter ces issues comme des échecs, c'est compter une entreprise identifiée
comme une entreprise inconnue.*

⚠️ **Et le chiffre qui recadre tout : les NEQ DISTINCTS.** Si les 8 931 dossiers
sans NEQ désignent beaucoup moins d'entreprises réelles, alors « 8 931
entreprises sans identité » n'est pas la bonne phrase — *c'est 8 931 DOSSIERS,
et le nombre d'entreprises est plus petit.* **Un compte de dossiers répond
« combien de lignes », jamais « combien d'entreprises ».**

Usage, SUR L'HÔTE :
    python3 -m outils.apport_noms_multiples
    python3 -m outils.apport_noms_multiples --exemples 20
"""
from __future__ import annotations

from outils.nombres import milliers

import argparse
from collections import Counter, defaultdict


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--exemples", type=int, default=10)
    parser.add_argument("--limite", type=int, default=None, help="borner (mise au point)")
    args = parser.parse_args(argv)

    from sqlalchemy import select

    from falkye.db import refuser_si_cible_non_choisie

    code = refuser_si_cible_non_choisie()
    if code:
        return code

    from falkye.db import get_session
    from falkye.models.company import Company
    from falkye.resolution import neq_retenu
    from falkye.sources import req as req_source

    print("=" * 78)
    print("CE QUE RAPPORTERAIT UN DOSSIER À PLUSIEURS NOMS")
    print("=" * 78)
    print("\nPORTÉE : mesure seule. N'écrit rien, ne crée aucune structure.\n")
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
        requete = select(Company).where(Company.neq.is_(None)).order_by(Company.id)
        if args.limite:
            requete = requete.limit(args.limite)
        orphelins = list(session.execute(requete).scalars().all())
        print(f"   dossiers sans NEQ      : {milliers(len(orphelins))}")

        resolus: list[tuple] = []   # (company, neq, score)
        sans_resolution = 0
        for i, company in enumerate(orphelins):
            if i and i % 1000 == 0:
                print(f"   … {milliers(i)} examinés", flush=True)
            matches = req_source.resolve_neq_by_name(
                session, company.nom_detecte, ville=company.ville
            )
            neq = neq_retenu(matches)
            if neq is None:
                sans_resolution += 1
                continue
            resolus.append((company, neq, matches[0].score))

        # Qui détient déjà quoi.
        neqs = {n for _, n, _ in resolus}
        detenus = {}
        for neq in neqs:
            porteur = session.execute(
                select(Company).where(Company.neq == neq)
            ).scalar_one_or_none()
            if porteur is not None:
                detenus[neq] = porteur

        par_neq: dict[str, list] = defaultdict(list)
        for company, neq, score in resolus:
            par_neq[neq].append((company, score))

        deja_pris = [x for x in resolus if x[1] in detenus]
        libres = {neq: v for neq, v in par_neq.items() if neq not in detenus}
        contestes = {neq: v for neq, v in libres.items() if len(v) > 1}
        posables = len(libres)                      # un NEQ libre = un dossier posé
        perdants = sum(len(v) for v in contestes.values()) - len(contestes)

        print("\n" + "-" * 78)
        print("CE QUE LA RÉSOLUTION TROUVE (identique dans les deux formes)")
        print("-" * 78)
        print(f"\n   un NEQ est RETENU pour      : {milliers(len(resolus))}")
        print(f"   aucun NEQ retenu            : {milliers(sans_resolution)}")

        print("\n" + "-" * 78)
        print("CE QUE LA FORME ACTUELLE PEUT EN FAIRE — un nom, un dossier")
        print("-" * 78)
        print(f"\n   NEQ posés                   : {milliers(posables)}")
        print(f"   PERDUS, NEQ déjà porté      : {milliers(len(deja_pris))}")
        print(f"   PERDUS, contesté dans le lot: {milliers(perdants)}")
        print("\n   ⚠️ « Perdu » veut dire : le produit SAIT quelle entreprise c'est,")
        print("      et n'a nulle part où le mettre.")

        print("\n" + "-" * 78)
        print("CE QU'UN DOSSIER À PLUSIEURS NOMS EN FERAIT")
        print("-" * 78)
        gain = len(deja_pris) + perdants
        print(f"\n   dossiers rattachés à un NEQ : {milliers(len(resolus))}")
        print(f"   GAIN sur la forme actuelle  : {milliers(gain)}"
              + f"   (+{100*gain/max(1,posables):.0f} %)")
        print("\n   Aucun nom ne se perd : un NEQ déjà porté devient un NOM DE PLUS")
        print("   sur le dossier qui le porte, et le dossier d'origine reste.")

        print("\n" + "-" * 78)
        print("⚠️ LE CHIFFRE QUI RECADRE — combien d'ENTREPRISES, pas de dossiers")
        print("-" * 78)
        distincts = len(neqs)
        print(f"\n   dossiers avec un NEQ retenu : {milliers(len(resolus))}")
        print(f"   NEQ DISTINCTS visés         : {milliers(distincts)}")
        print(f"   dossiers en trop            : {milliers(len(resolus) - distincts)}")
        print("\n   Un compte de DOSSIERS répond « combien de lignes », jamais")
        print("   « combien d'entreprises ». La seconde question est celle qui compte.")

        distribution = Counter(len(v) for v in par_neq.values())
        print("\n   dossiers par NEQ visé :")
        for combien, n in sorted(distribution.items()):
            print(f"      {combien} dossier(s) → {milliers(n)} NEQ")

        if args.exemples:
            print("\n" + "=" * 78)
            print("LES NOMS QUE LE PRODUIT PERD AUJOURD'HUI")
            print("=" * 78)
            montres = 0
            for neq, membres in sorted(par_neq.items(), key=lambda kv: -len(kv[1])):
                if len(membres) < 2 and neq not in detenus:
                    continue
                if montres >= args.exemples:
                    break
                montres += 1
                porteur = detenus.get(neq)
                print(f"\n   NEQ {neq}")
                if porteur is not None:
                    print(f"      DÉJÀ PORTÉ par #{porteur.id} « {porteur.nom_detecte} »")
                for company, score in membres:
                    print(f"      #{company.id:<7} « {company.nom_detecte} »   score {score:.1f}")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
