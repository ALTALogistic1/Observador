#!/usr/bin/env python3
"""CE QUE LE TROISIÈME TEMPS CHANGE — **une mesure, elle n'écrit rien.**

## La décision, et ce qu'elle demande de vérifier

**Alexandre, 23 septembre 2026 — registre D52** : *« Le second temps.
`resolve_neq_by_name` ne consulte les noms retirés que si aucun nom en vigueur
n'a trouvé l'entreprise. Je ne plafonne pas les scores : ça ferait perdre des
changements de nom qui sont justes. »*

⚠️ **Ce que la forme retenue garantit, et qu'aucune mesure n'a besoin
d'établir.** *Écarter des formes ne peut qu'ABAISSER des scores.* Donc le
premier temps ne retient jamais moins que le troisième, et **quand il ne retient
rien, le troisième rejoue exactement le comportement d'avant.**

> **La règle ne change l'issue que là où un nom EN VIGUEUR désigne quelqu'un
> d'AUTRE que le nom retiré.** *« Perdre son NEQ » est donc impossible par
> construction — et l'outil le VÉRIFIE au lieu de s'en remettre au raisonnement.*

## Les trois sections

**1. Les dossiers DÉJÀ POSÉS** — combien changeraient de NEQ, combien le
perdraient *(attendu : zéro)*. ⚠️ *Rien ne change tout seul : un NEQ posé reste
posé tant qu'une passe de reprise ne le réécrit pas.* **Ce tableau dit ce qu'une
reprise ferait, pas ce qui s'est produit.**

**2. Les RESTANTS** — combien gagneraient un NEQ. *Écarter un nom retiré peut
faire tomber un concurrent sous l'écart, donc RÉSOUDRE un dossier qui était
ambigu.* **C'est le gain, et il est du même mécanisme que le risque.**

**3. Les dossiers dont le rejeu ne retrouve plus le NEQ posé.** *La mesure du
22 septembre en comptait 14 sans les expliquer.* Deux causes, et elles ne se
confondent pas : **le lot a grandi et le NEQ est passé sous la coupe**, ou **la
porte a disparu — plus aucun nom ne le récupère.**

⚠️ **RIEN N'EST ÉCRIT. Les échelles ne bougent pas : seuil 92, écart 8.**

Usage, SUR L'HÔTE :
    python3 -m outils.second_temps_des_noms_retires
    python3 -m outils.second_temps_des_noms_retires --paires 20
"""
from __future__ import annotations

import argparse
from collections import Counter

from outils.nombres import milliers

#: Ce qu'une reprise ferait d'un dossier déjà posé. ⚠️ **Chacun est un
#: RÉSULTAT**, et `PERDU` ne devrait jamais se remplir.
INCHANGE = "garde le même NEQ"
CHANGE = "⚠️ CHANGERAIT de NEQ"
PERDU = "⛔ PERDRAIT son NEQ — impossible par construction"
ISSUES_DES_POSES = (INCHANGE, CHANGE, PERDU)

#: Ce que la règle fait d'un dossier sans NEQ.
GAGNE = "✅ GAGNERAIT un NEQ"
TOUJOURS_SANS = "reste sans NEQ"
ISSUES_DES_RESTANTS = (GAGNE, TOUJOURS_SANS)

#: Pourquoi un rejeu ne retrouve plus le NEQ posé. *Deux causes, deux suites.*
SOUS_LA_COUPE = "⚠️ le lot a GRANDI — le NEQ est passé sous la coupe"
PORTE_DISPARUE = "⛔ la PORTE a disparu — plus aucun nom ne le récupère"
CAUSES_DE_LA_PERTE = (SOUS_LA_COUPE, PORTE_DISPARUE)

LARGEUR = max(len(t) for t in
              ISSUES_DES_POSES + ISSUES_DES_RESTANTS + CAUSES_DE_LA_PERTE) + 1


def _part(k: int, n: int) -> str:
    return f"{100 * k / n:.1f} %" if n else "—"


def _ligne(etiquette: str, k: int, n: int = 0) -> str:
    part = f" {_part(k, n):>8}" if n else ""
    return f"   {etiquette:<{LARGEUR}} {milliers(k):>9}{part}"


def les_deux_regles(session, company):
    """`(neq d'avant, neq d'après, matches d'après)` — **par DEUX APPELS de la
    production**, jamais par une copie du scoreur.

    *`retires_en_dernier=False` rejoue le comportement du 17 au 22 septembre.*
    """
    from falkye.resolution import neq_retenu
    from falkye.sources import req as req_source

    avant = req_source.resolve_neq_by_name(
        session, company.nom_detecte, ville=company.ville,
        retires_en_dernier=False)
    apres = req_source.resolve_neq_by_name(
        session, company.nom_detecte, ville=company.ville)
    return neq_retenu(avant), neq_retenu(apres), apres


def cause_de_la_perte(session, company, profondeur: int):
    """`(cause, rang)` — pourquoi le rejeu ne retrouve plus le NEQ posé.

    ⚠️ *Le plafond est relevé par un APPEL, pas par une réécriture de la
    récupération* : ce qui remonte alors a bien été RÉCUPÉRÉ, et c'est la coupe
    qui l'écartait.
    """
    from falkye.sources import req as req_source

    profonds = req_source.resolve_neq_by_name(
        session, company.nom_detecte, ville=company.ville, limit=profondeur)
    for rang, m in enumerate(profonds):
        if m.entry.neq == company.neq:
            return SOUS_LA_COUPE, rang
    return PORTE_DISPARUE, None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--paires", type=int, default=0, metavar="N",
                        help="montrer N dossiers de chaque cas qui CHANGE")
    parser.add_argument("--profondeur", type=int, default=200, metavar="N",
                        help="plafond du lot rejoué pour la section 3")
    parser.add_argument("--limite", type=int, default=None, help="borner (mise au point)")
    parser.add_argument("--pas", type=int, default=500, metavar="N")
    args = parser.parse_args(argv)

    from sqlalchemy import select

    from falkye.db import refuser_si_cible_non_choisie

    code = refuser_si_cible_non_choisie()
    if code:
        return code

    from falkye.db import get_session
    from falkye.models.company import Company
    from falkye.sources import req as req_source

    session = get_session()
    try:
        print("=" * 78)
        print("CE QUE LE TROISIÈME TEMPS CHANGE — une MESURE")
        print("=" * 78)
        print("""
⚠️ LA RÈGLE NE PEUT RIEN FAIRE PERDRE, ET C'EST STRUCTUREL

   Écarter des formes ne peut qu'ABAISSER des scores. Le premier temps ne
   retient donc jamais moins que le troisième, et quand il ne retient
   rien, le troisième rejoue exactement le comportement d'avant. La règle
   ne change l'issue que là où un nom EN VIGUEUR désigne quelqu'un
   d'AUTRE. L'outil le VÉRIFIE plutôt que de s'en remettre au raisonnement.

⚠️ ET RIEN NE CHANGE TOUT SEUL

   Un NEQ posé reste posé tant qu'une passe de reprise ne le réécrit pas.
   Ce qui suit dit ce qu'une reprise FERAIT, jamais ce qui s'est produit.

⚠️ RIEN N'EST ÉCRIT.
""")

        requete = select(Company).order_by(Company.id)
        if args.limite:
            requete = requete.limit(args.limite)
        dossiers = list(session.execute(requete).scalars().all())
        poses = [c for c in dossiers if c.neq]
        restants = [c for c in dossiers if not c.neq]

        print(f"… rejeu des DEUX règles sur {milliers(len(dossiers))} dossiers "
              f"({milliers(len(poses))} posés, {milliers(len(restants))} restants)",
              flush=True)

        par_issue: Counter = Counter()
        par_restant: Counter = Counter()
        changent: list = []
        gagnent: list = []
        introuvables: list = []
        for i, company in enumerate(dossiers, 1):
            if args.pas and i % args.pas == 0:
                print(f"   … {milliers(i)} / {milliers(len(dossiers))}", flush=True)
            avant, apres, matches = les_deux_regles(session, company)
            if company.neq:
                if apres == company.neq:
                    par_issue[INCHANGE] += 1
                elif apres is None:
                    # ⚠️ Le rejeu d'AVANT retrouvait-il seulement ce NEQ? Sinon
                    # ce n'est pas la règle qui le perd — c'est déjà perdu.
                    if avant == company.neq:
                        par_issue[PERDU] += 1
                        changent.append((company, avant, apres, matches))
                    else:
                        introuvables.append(company)
                else:
                    par_issue[CHANGE] += 1
                    changent.append((company, avant, apres, matches))
            else:
                par_restant[GAGNE if apres else TOUJOURS_SANS] += 1
                if apres:
                    gagnent.append((company, avant, apres, matches))

        print("\n" + "-" * 78)
        print("1. LES DOSSIERS DÉJÀ POSÉS — ce qu'une reprise ferait")
        print("-" * 78 + "\n")
        n = len(poses)
        for issue in ISSUES_DES_POSES:
            print(_ligne(issue, par_issue.get(issue, 0), n))
        print(_ligne("⚠️ le rejeu ne retrouvait DÉJÀ plus ce NEQ", len(introuvables), n))
        if par_issue.get(PERDU):
            print(f"""
   ⛔ {milliers(par_issue[PERDU])} DOSSIER(S) PERDRAIENT LEUR NEQ, ET C'EST IMPOSSIBLE.
      Le raisonnement structurel est donc faux quelque part, et rien de
      ce qui suit ne doit s'appliquer avant de savoir où.""")
        else:
            print("""
   ✅ Aucun dossier ne perd son NEQ. La garantie structurelle tient sur
      la population réelle, et pas seulement sur le papier.""")

        print("\n" + "-" * 78)
        print("2. LES RESTANTS — ce que la règle en récupère")
        print("-" * 78 + "\n")
        for issue in ISSUES_DES_RESTANTS:
            print(_ligne(issue, par_restant.get(issue, 0), len(restants)))
        print("""
   ⚠️ LE GAIN EST DU MÊME MÉCANISME QUE LE RISQUE. Écarter un nom retiré
      fait tomber un concurrent sous l'écart, donc RÉSOUT un dossier qui
      était ambigu. C'est la même opération qui déplace un NEQ ailleurs.
""")

        # ---- 3. LES INTROUVABLES ------------------------------------------
        print("-" * 78)
        print("3. LES DOSSIERS DONT LE REJEU NE RETROUVE PLUS LE NEQ POSÉ")
        print("-" * 78)
        print(f"""
   La mesure du 22 septembre en comptait 14 sans les expliquer. Deux
   causes, et elles n'appellent pas la même suite. Le plafond est relevé
   à {args.profondeur} par un APPEL de la production : ce qui remonte alors a bien
   été RÉCUPÉRÉ, et c'est la coupe qui l'écartait.
""")
        par_cause: Counter = Counter()
        detail: list = []
        for company in introuvables:
            cause, rang = cause_de_la_perte(session, company, args.profondeur)
            par_cause[cause] += 1
            detail.append((company, cause, rang))
        for cause in CAUSES_DE_LA_PERTE:
            print(_ligne(cause, par_cause.get(cause, 0), len(introuvables)))
        print(f"""
   ⚠️ « SOUS LA COUPE » EST LA DÉRIVE ANNONCÉE. `req_noms` n'oublie rien,
      `_scorer` prend le MEILLEUR des noms d'un NEQ, donc les scores ne
      peuvent que monter et le lot que grandir. Un NEQ posé hier sort du
      lot aujourd'hui sans que personne ait rien changé.

   ⚠️ « LA PORTE A DISPARU » EST AUTRE CHOSE. Plus aucun nom ne récupère
      ce NEQ — le dossier a changé de nom détecté, ou le NEQ a été posé
      par un chemin qui n'est pas celui du nom.
""")

        if args.paires and detail:
            print("=" * 78)
            print(f"LES DOSSIERS INTROUVABLES — {min(args.paires, len(detail))} "
                  f"sur {milliers(len(detail))}")
            print("=" * 78)
            for company, cause, rang in detail[:args.paires]:
                print(f"\n   #{company.id}   {(company.nom_detecte or '')[:54]}")
                print(f"      NEQ posé : {company.neq}")
                print(f"      {cause}" + (f"   (rang {rang + 1})" if rang is not None else ""))

        if args.paires and changent:
            print("\n" + "=" * 78)
            print(f"LES DOSSIERS QUI CHANGERAIENT DE NEQ — "
                  f"{min(args.paires, len(changent))} sur {milliers(len(changent))}")
            print("=" * 78)
            formes = req_source.formes_retenues(
                session, [m for _c, _a, _p, ms in changent[:args.paires] for m in ms[:3]])
            for company, avant, apres, matches in changent[:args.paires]:
                print(f"\n   #{company.id}   {(company.nom_detecte or '')[:54]}")
                print(f"      posé aujourd'hui sur : {company.neq}")
                print(f"      l'ancienne règle rendait : {avant or '—'}")
                print(f"      ⚠️ la nouvelle rendrait  : {apres or '—'}")
                for m in matches[:3]:
                    forme = formes.get((m.entry.neq, m.forme_normalisee))
                    marque = "→" if m.entry.neq == apres else " "
                    print(f"      {marque} {m.entry.neq}  {m.score:>6.1f}  "
                          f"{(m.entry.nom or '—')[:36]:<38} [{m.entry.statut}]")
                    if forme is not None and not forme.est_la_denomination_elue:
                        print(f"         ↳ a scoré sur "
                              f"« {(forme.nom_publie or '—')[:40]} »"
                              f"   [nom : {forme.statut}]")

        print("\n" + "=" * 78)
        print("   RIEN N'A ÉTÉ ÉCRIT. Les échelles n'ont pas bougé.")
        print("   ⚠️ Un NEQ posé reste posé tant qu'une reprise ne le réécrit pas.")
        print("=" * 78)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
