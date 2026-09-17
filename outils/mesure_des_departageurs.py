#!/usr/bin/env python3
"""Trois départageurs sur les ambigus — recouvrement, combinaison, et coût.

**Le fait qui l'écrit** *(2026-09-17)*. Le second temps a fait chuter les « trop
faibles » de 73 % et **monter les ambigus à 5 002**. *Un ambigu n'est pas un
dossier sans candidat : c'est un dossier avec DEUX candidats que le nom ne sépare
pas.* **Le nom a donné tout ce qu'il avait.**

⚠️ **AUCUN départageur ne touche à une échelle.** *Ils ajoutent un fait; ils
n'abaissent pas une garde.* Le seuil de **92** et l'écart de **8** ne bougent
pas, et cet outil n'existe pas pour les rouvrir.

## Ce qu'il rend, et pourquoi dans cet ordre

1. **Le recouvrement de chacun** — qui porte le fait, qui sépare, et **qui reste
   indépartageable, ventilé par MAILLON MANQUANT**. *Cette dernière ligne est un
   résultat : « le dossier n'a pas le fait » et « un concurrent ne l'a pas »
   appellent deux correctifs différents.*
2. **Ce qu'ils rendent COMBINÉS, et leur recouvrement mutuel.** ⚠️ *Trois
   départageurs qui séparent les mêmes 1 500 dossiers ne valent pas trois fois
   un.*
3. **Le coût.** Pour la ville il était nul par nature. *Pour les deux autres, ça
   se vérifie* — et le coût d'un départageur est **le nombre de fois où il
   désigne un AUTRE candidat que le mieux scoré**, plus les fois où **il les
   exclut tous**.

⚠️ **Un départage écarte un candidat; il n'en confirme aucun.** *Les paires se
regardent une à une avant toute écriture, et cet outil n'écrit rien.*

Usage, SUR L'HÔTE :
    python3 -m outils.mesure_des_departageurs
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict

from outils.departageur_adresse import (
    CLES_ADRESSE,  # noqa: F401 -- **empruntée, pas recopiée** (voir plus bas)
    champs_des_dossiers,
    concurrents_de,
    faits_des_dossiers,
    faits_du_candidat,
    texte_des_champs as _texte_des_champs,
)
from outils.departageurs import (
    AUCUN_COMPATIBLE,
    DEPARTAGE,
    ISSUES,
    Fait,
    departager,
    fait_de_lactivite,
)
from outils.nombres import milliers

# ⚠️ **`CLES_ADRESSE`, la lecture des faits d'adresse et le découpage des
# concurrents sont EMPRUNTÉS à `outils/departageur_adresse.py`.** *Une mesure qui
# lit une adresse pendant que la construction en lit une autre est un rapport sur
# une population imaginaire* — et un départageur recopié à la main est déjà
# arrivé une fois (cas 41).

#: Où vit une classification d'activité côté signal. *Seule la lecture de
#: l'ACTIVITÉ reste ici : elle n'est pas construite, et n'a donc pas de module.*
CLES_ACTIVITE = ("secteur_nature_contrat", "secteur_activite", "profession")


def _part(k: int, n: int) -> str:
    return f"{100 * k / n:.1f} %" if n else "—"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--limite", type=int, default=None, help="borner (mise au point)")
    parser.add_argument("--exemples", type=int, default=5)
    args = parser.parse_args(argv)

    from sqlalchemy import select

    from falkye.db import refuser_si_cible_non_choisie

    code = refuser_si_cible_non_choisie()
    if code:
        return code

    from falkye.db import get_session
    from falkye.models.company import Company
    from falkye.resolution import (
        SEUIL_AMBIGUITE_ECART_MIN,
        SEUIL_RESOLUTION_CONFIANTE,
        famille_de,
    )
    from falkye.sources import req as req_source

    print("=" * 78)
    print("TROIS DÉPARTAGEURS SUR LES AMBIGUS")
    print("=" * 78)
    print(f"""
⚠️ CE QUE CETTE MESURE NE DIRA PAS — à lire avant tout chiffre

   UN DÉPARTAGE ÉCARTE UN CANDIDAT; IL N'EN CONFIRME AUCUN. Deux entreprises
   distinctes peuvent partager une ville, un code postal et un secteur.

   UN FAIT ABSENT CHEZ UN CONCURRENT NE L'EXCLUT PAS. « Je ne sais pas » n'est
   pas « non » — sans cette règle, le départageur deviendrait un filtre sur le
   remplissage du registre, pas sur l'identité.

   ⚠️ L'ACTIVITÉ SE COMPARE PAR LIBELLÉ, JAMAIS PAR CODE. Le SEAO classe en
   UNSPSC, le REQ en CAE, et aucune table ne les relie. Ce qu'elle rend est un
   PLANCHER de ce qu'elle donnerait avec la vraie table — celle que le
   chantier 22 construira pour son propre usage.

   AUCUNE ÉCRITURE. Seuil {SEUIL_RESOLUTION_CONFIANTE:.0f}, écart
   {SEUIL_AMBIGUITE_ECART_MIN:.0f} — inchangés, et cet outil n'existe pas pour
   les rouvrir.
""")

    session = get_session()
    try:
        requete = select(Company).where(Company.neq.is_(None)).order_by(Company.id)
        if args.limite:
            requete = requete.limit(args.limite)
        orphelins = list(session.execute(requete).scalars().all())

        # ---- LA POPULATION : les ambigus, par la règle du moteur -------------
        ambigus: list[tuple[Company, list]] = []
        for i, company in enumerate(orphelins):
            if i and i % 500 == 0:
                print(f"   … {milliers(i)} examinés", flush=True)
            matches = req_source.resolve_neq_by_name(
                session, company.nom_detecte, ville=company.ville
            )
            if famille_de(matches) == "ambigu":
                ambigus.append((company, matches))
        print(f"\n   dossiers sans NEQ : {milliers(len(orphelins))}")
        print(f"   dont AMBIGUS      : {milliers(len(ambigus))}   ← la population\n")
        if not ambigus:
            print("   Rien à départager.")
            return 0

        ids = {c.id for c, _ in ambigus}
        champs_par_dossier = champs_des_dossiers(session, ids)
        # ⚠️ **Les faits d'adresse viennent du module qui les CONSTRUIT.** *Les
        # deux niveaux se mesurent ici séparément, mais ils se LISENT là-bas.*
        adresses = faits_des_dossiers(
            session, [c for c, _ in ambigus], champs=champs_par_dossier
        )

        def _fait_ville(company) -> Fait | None:
            return adresses[company.id].ville

        def _fait_postal(company) -> Fait | None:
            return adresses[company.id].code_postal

        def _fait_activite(company) -> Fait | None:
            texte = " ".join(filter(None, [
                company.secteur_activite_libelle,
                _texte_des_champs(champs_par_dossier.get(company.id, {}), CLES_ACTIVITE),
            ]))
            return fait_de_lactivite(texte)

        DEPARTAGEURS = (
            ("ville", _fait_ville, lambda e: faits_du_candidat(e).ville),
            ("code postal", _fait_postal, lambda e: faits_du_candidat(e).code_postal),
            ("activité", _fait_activite, lambda e: fait_de_lactivite(e.secteur_libelle)),
        )

        issues: dict[str, Counter] = {nom: Counter() for nom, _, _ in DEPARTAGEURS}
        separes: dict[str, set[int]] = {nom: set() for nom, _, _ in DEPARTAGEURS}
        corrige: Counter = Counter()
        exclut_tout: Counter = Counter()
        exemples: dict[str, list[str]] = defaultdict(list)

        for company, matches in ambigus:
            # ⚠️ **Le découpage des concurrents est EMPRUNTÉ**, pas refait ici :
            # *c'est lui qui définit la population de tous les départageurs.*
            concurrents = concurrents_de(matches)
            for nom, du_dossier, du_candidat in DEPARTAGEURS:
                issue, gagnant = departager(
                    du_dossier(company), [du_candidat(m.entry) for m in concurrents]
                )
                issues[nom][issue] += 1
                if issue == DEPARTAGE:
                    separes[nom].add(company.id)
                    if gagnant != 0:
                        corrige[nom] += 1
                        if len(exemples[nom]) < args.exemples:
                            exemples[nom].append(
                                f"{(company.nom_detecte or '')[:40]:<42} "
                                f"mieux scoré {concurrents[0].entry.neq} → "
                                f"retenu {concurrents[gagnant].entry.neq}"
                            )
                elif issue == AUCUN_COMPATIBLE:
                    exclut_tout[nom] += 1

        # ---- 1. LE RECOUVREMENT DE CHACUN -----------------------------------
        n = len(ambigus)
        print("-" * 78)
        print("1. CHAQUE DÉPARTAGEUR — et pourquoi il ne sépare pas, quand il ne sépare pas")
        print("-" * 78)
        for nom, _, _ in DEPARTAGEURS:
            print(f"\n   ▸ {nom.upper()}")
            for issue in ISSUES:
                k = issues[nom].get(issue, 0)
                marque = "  ←" if issue == DEPARTAGE else ""
                print(f"      {issue:<52} {milliers(k):>8} {_part(k, n):>8}{marque}")

        # ---- 2. COMBINÉS, ET LEUR RECOUVREMENT ------------------------------
        print("\n" + "-" * 78)
        print("2. COMBINÉS — et ce qu'ils se recouvrent")
        print("-" * 78)
        union: set[int] = set()
        for nom, _, _ in DEPARTAGEURS:
            union |= separes[nom]
        print(f"\n   ⇒ SÉPARÉS PAR AU MOINS UN : {milliers(len(union))} sur "
              f"{milliers(n)}  ({_part(len(union), n)})")
        somme = sum(len(separes[nom]) for nom, _, _ in DEPARTAGEURS)
        print(f"   somme des trois pris isolément : {milliers(somme)}")
        print(f"   ⚠️ recouvrement : {milliers(somme - len(union))} dossier(s) comptés")
        print("      plusieurs fois. *Trois départageurs qui séparent les mêmes")
        print("      dossiers ne valent pas trois fois un.*")

        print(f"\n   {'ce que chacun APPORTE SEUL (les autres échouent)':<52} {'dossiers':>9}")
        for nom, _, _ in DEPARTAGEURS:
            autres: set[int] = set()
            for autre, _, _ in DEPARTAGEURS:
                if autre != nom:
                    autres |= separes[autre]
            seul = separes[nom] - autres
            print(f"   {nom:<52} {milliers(len(seul)):>9}")

        indepartageables = n - len(union)
        print(f"\n   ⛔ INDÉPARTAGEABLES PAR LES TROIS : {milliers(indepartageables)}"
              f"  ({_part(indepartageables, n)})")
        print("      *C'est un résultat, pas une absence de mesure* — ces dossiers")
        print("      demandent un fait que le produit ne possède pas.")

        # ---- 3. LE COÛT ------------------------------------------------------
        print("\n" + "-" * 78)
        print("3. LE COÛT — un départageur peut-il se tromper?")
        print("-" * 78)
        print("\n   Deux formes, et elles ne sont pas de même nature :\n")
        print(f"   {'départageur':<16} {'désigne UN AUTRE que le mieux scoré':>38} "
              f"{'les exclut TOUS':>18}")
        for nom, _, _ in DEPARTAGEURS:
            print(f"   {nom:<16} {milliers(corrige.get(nom, 0)):>38} "
                  f"{milliers(exclut_tout.get(nom, 0)):>18}")
        print("""
   ⚠️ « Désigne un autre » n'est PAS une erreur : c'est le cas où le fait
      CORRIGE le score au lieu de le confirmer, et c'est précisément ce qu'on
      cherche. *Mais c'est aussi là que le départageur engage le plus* — ces
      paires-là se regardent en premier.

   ⚠️ « Les exclut tous » est un SIGNAL, pas un départage : le fait du dossier
      ne concorde avec aucun candidat. *Soit le bon candidat n'est pas dans le
      lot, soit le fait est sale.* Aucun départage n'est prononcé.
""")
        for nom, _, _ in DEPARTAGEURS:
            if exemples[nom]:
                print(f"   quelques cas où {nom} CORRIGE :")
                for ligne in exemples[nom]:
                    print(f"      {ligne}")
                print()

        print("=" * 78)
        print("   RIEN N'A ÉTÉ ÉCRIT. Les paires se regardent une à une.")
        print("=" * 78)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
