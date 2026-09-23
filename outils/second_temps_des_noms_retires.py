#!/usr/bin/env python3
"""CE QUE LE TROISIÈME TEMPS CHANGE — **une mesure, elle n'écrit rien.**

## La décision, et ce qu'elle demande de vérifier

**Alexandre, 23 septembre 2026 — registre D52** : *« Le second temps.
`resolve_neq_by_name` ne consulte les noms retirés que si aucun nom en vigueur
n'a trouvé l'entreprise. Je ne plafonne pas les scores : ça ferait perdre des
changements de nom qui sont justes. »*

## ⚠️ LA GARANTIE ANNONCÉE ÉTAIT FAUSSE, ET LA MESURE L'A DIT

**Cet outil annonçait : « perdre son NEQ est impossible par construction ».**
*Le raisonnement : écarter des formes ne peut qu'abaisser des scores, donc quand
le premier temps ne retient rien, le troisième rejoue le comportement d'avant.*

⛔ **La mesure du 23 septembre a rendu 9 pertes.** **La garde s'est déclenchée au
lieu de rendre un succès** — *c'est ce qu'on lui demandait, et c'est la seule
raison pour laquelle on le sait.*

**Où le raisonnement se casse.** *Le troisième temps rejoue les formes d'avant,
**mais pas le LOT d'avant**.* Quand le premier temps ne retient rien, **le second
temps s'ouvre** — celui du mot rare — et y ajoute des candidats. *L'ancienne
règle, elle, retenait dès le préfixe et **ne voyait jamais ces candidats-là**.*

> **La garantie valait pour les FORMES, jamais pour le LOT.** ⚠️ *Et le lot
> décide autant que les formes : un candidat de plus à moins de 8 points fait un
> ambigu.*

**Cet outil ne conclut donc plus : il MESURE laquelle des deux causes agit**,
dossier par dossier, en rejouant avec `elargir=False` — *le drapeau qui coupe le
second temps.*

## Les trois sections

**1. Les dossiers DÉJÀ POSÉS** — combien changeraient de NEQ, combien le
perdraient *(attendu : zéro)*. ⚠️ *Rien ne change tout seul : un NEQ posé reste
posé tant qu'une passe de reprise ne le réécrit pas.* **Ce tableau dit ce qu'une
reprise ferait, pas ce qui s'est produit.**

**2. Les RESTANTS** — combien gagneraient un NEQ. *Écarter un nom retiré peut
faire tomber un concurrent sous l'écart, donc RÉSOUDRE un dossier qui était
ambigu.* **C'est le gain, et il est du même mécanisme que le risque.**

**3. Les dossiers que la résolution d'aujourd'hui NE RÉSOUT PLUS.** ⚠️ *Cet outil
en nommait la cause « le NEQ est passé sous la coupe ». **C'était faux** :
`neq_retenu` ne lit que `matches[0]` et `matches[1]`, donc relever le plafond du
lot ne change aucune décision.* **La vraie cause est la FAMILLE que la résolution
rend aujourd'hui** — le plus souvent *ambigu*, parce que le lot a grandi et qu'un
concurrent est arrivé à moins de 8 points.

**4. Les PRÉTENDANTS MULTIPLES.** ⚠️ *La garde du 17 septembre — « le nombre de
prétendants est une preuve contre l'appariement » — **n'existe que dans
`outils/`**.* **Rien dans `falkye/` ne compte les prétendants, et
`resolve_company` rattache au MÊME `Company` deux dossiers résolus vers le même
NEQ.**

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

#: ⚠️ **CORRIGÉ le 23 septembre.** *Cet outil nommait « le NEQ est passé sous la
#: coupe » la cause d'un dossier que le rejeu ne résout plus.* **C'était faux, et
#: c'était l'instrument pris pour le monde** : `neq_retenu` ne lit QUE `matches[0]`
#: et `matches[1]`, donc **le plafond à cinq ne change aucune décision** — et les
#: paires montraient le NEQ posé aux rangs 2 et 3, bien à l'intérieur de la coupe.
#:
#: *La vraie cause est la FAMILLE que la résolution rend aujourd'hui.* ⚠️ **Troisième
#: fois qu'une borne d'instrument est nommée comme un fait du monde** — après l'axe
#: des candidats du portrait et le « aucun n'a plus de 5 candidats » du plan.
DEVENU_AMBIGU = "⚠️ devenu AMBIGU — un concurrent est arrivé à moins de 8 points"
DEVENU_TROP_FAIBLE = "devenu TROP FAIBLE — le sommet est passé sous le seuil"
SANS_CANDIDAT = "aucun candidat aujourd'hui"
CAUSES_DE_LA_PERTE = (DEVENU_AMBIGU, DEVENU_TROP_FAIBLE, SANS_CANDIDAT)

#: Où le NEQ posé se trouve dans le lot d'aujourd'hui. ⚠️ *Rendu pour qu'on cesse
#: de confondre « le dossier n'est plus résolu » et « le NEQ a disparu ».*
ENCORE_EN_TETE = "le NEQ posé est encore le MIEUX scoré"
ENCORE_DANS_LE_LOT = "le NEQ posé est encore dans le lot, plus bas"
ABSENT_DU_LOT = "⛔ le NEQ posé n'est plus dans le lot du tout"
RANGS = (ENCORE_EN_TETE, ENCORE_DANS_LE_LOT, ABSENT_DU_LOT)

#: Laquelle des deux causes fait perdre un NEQ. *Mesuré, jamais supposé.*
PAR_LE_SECOND_TEMPS = "⚠️ le SECOND TEMPS — le lot s'est élargi, un ambigu est né"
PAR_LE_PREMIER_TEMPS = "le PREMIER TEMPS — sans le nom retiré, le sommet ne passe plus"
CAUSES_DE_PERTE_REELLE = (PAR_LE_SECOND_TEMPS, PAR_LE_PREMIER_TEMPS)

#: ⚠️ **La garde des PRÉTENDANTS MULTIPLES est DESCENDUE dans la résolution**
#: *(2026-09-23, sur demande d'Alexandre)*. `PRETENDANTS_MAX_POUR_TRANCHER` vit
#: désormais dans `falkye/resolution.py`, et `outils/pose_du_neq.py` l'emprunte.
#: **Mais la forme du refus a changé en descendant** : la passe par lot refuse à
#: TOUS les prétendants, la résolution refuse au NOUVEAU VENU — *le détenteur a
#: déjà le NEQ, et `Company.neq` est UNIQUE.* Voir `garde_des_pretendants`.
TROP_DE_PRETENDANTS = "⛔ NEQ visé par PLUS DE DEUX dossiers — la garde du 17 sept."

LARGEUR = max(len(t) for t in
              ISSUES_DES_POSES + ISSUES_DES_RESTANTS + CAUSES_DE_LA_PERTE
              + RANGS + CAUSES_DE_PERTE_REELLE + (TROP_DE_PRETENDANTS,)) + 1


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


def ce_qui_a_change(session, company, matches, profondeur: int):
    """`(cause, où est le NEQ posé, rang)` — pourquoi le dossier n'est plus résolu.

    ⚠️ **La cause est la FAMILLE que la résolution rend aujourd'hui**, jamais le
    plafond du lot : `neq_retenu` ne lit que `matches[0]` et `matches[1]`, donc
    **relever la coupe ne change aucune décision.**
    """
    from falkye.resolution import famille_de
    from falkye.sources import req as req_source

    famille = famille_de(matches)
    cause = {"ambigu": DEVENU_AMBIGU, "trop faible": DEVENU_TROP_FAIBLE}.get(
        famille, SANS_CANDIDAT)
    profonds = req_source.resolve_neq_by_name(
        session, company.nom_detecte, ville=company.ville, limit=profondeur)
    for rang, m in enumerate(profonds):
        if m.entry.neq == company.neq:
            return cause, (ENCORE_EN_TETE if rang == 0 else ENCORE_DANS_LE_LOT), rang
    return cause, ABSENT_DU_LOT, None


def cause_dune_perte(session, company) -> str:
    """Laquelle des deux causes fait perdre ce NEQ — **par un APPEL.**

    *`elargir=False` coupe le second temps.* **Si la perte disparaît alors, c'est
    le lot élargi qui l'a causée; sinon, c'est le premier temps.**
    """
    from falkye.resolution import neq_retenu
    from falkye.sources import req as req_source

    sans_second = neq_retenu(req_source.resolve_neq_by_name(
        session, company.nom_detecte, ville=company.ville, elargir=False))
    return (PAR_LE_SECOND_TEMPS if sans_second == company.neq
            else PAR_LE_PREMIER_TEMPS)


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
⛔ CET OUTIL A ANNONCÉ UNE GARANTIE QUI ÉTAIT FAUSSE

   Il disait : « perdre son NEQ est impossible par construction ». La
   mesure du 23 septembre a rendu 9 pertes. La garde s'est déclenchée au
   lieu de rendre un succès, et c'est la seule raison pour laquelle on le
   sait.

   OÙ LE RAISONNEMENT SE CASSE. Le troisième temps rejoue les FORMES
   d'avant, mais pas le LOT d'avant. Quand le premier temps ne retient
   rien, le SECOND TEMPS s'ouvre — celui du mot rare — et ajoute des
   candidats que l'ancienne règle ne voyait jamais, parce qu'elle
   retenait dès le préfixe. Un candidat de plus à moins de 8 points fait
   un ambigu.

   La garantie valait pour les FORMES, jamais pour le LOT.

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
            print(f"\n   ⛔ {milliers(par_issue[PERDU])} DOSSIER(S) PERDRAIENT LEUR NEQ — "
                  "et par quelle cause :\n")
            par_cause_reelle: Counter = Counter()
            for company, avant, apres, _m in changent:
                if apres is None:
                    par_cause_reelle[cause_dune_perte(session, company)] += 1
            for cause in CAUSES_DE_PERTE_REELLE:
                print(_ligne(cause, par_cause_reelle.get(cause, 0),
                             par_issue[PERDU]))
            print("""
   ⚠️ CE QUE CHACUNE APPELLE. « Le second temps » veut dire que le lot
      s'est élargi et qu'un ambigu est né : le dossier EST ambigu, et
      l'ancienne règle le retenait par IGNORANCE — elle n'avait jamais vu
      le concurrent. « Le premier temps » veut dire que sans le nom
      retiré, plus rien ne franchit le seuil.

   ⚠️ ET AUCUNE DES DEUX NE RETIRE UN NEQ DE LA BASE. Une reprise POSE,
      elle n'efface pas : un dossier qui cesse d'être résolu garde le NEQ
      qu'il porte. La perte est une perte de RECONFIRMATION.""")
        else:
            print("""
   ✅ Aucun dossier ne perd son NEQ sur cette population.""")

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

        # ---- 3. CEUX QUI NE SONT PLUS RÉSOLUS -----------------------------
        print("\n" + "-" * 78)
        print("3. LES DOSSIERS QUE LA RÉSOLUTION D'AUJOURD'HUI NE RÉSOUT PLUS")
        print("-" * 78)
        print(f"""
   ⛔ CORRECTION DU 23 SEPTEMBRE. Cet outil nommait « le NEQ est passé
      sous la coupe » la cause de ces dossiers. C'ÉTAIT FAUX.
      `neq_retenu` ne lit que matches[0] et matches[1] : relever le
      plafond du lot NE CHANGE AUCUNE DÉCISION. Et les paires montraient
      le NEQ posé aux rangs 2 et 3, bien à l'intérieur de la coupe.

      C'est la troisième fois qu'une borne d'instrument est nommée comme
      un fait du monde, après l'axe des candidats du portrait.

   LA VRAIE CAUSE est la FAMILLE que la résolution rend aujourd'hui.
""")
        par_cause: Counter = Counter()
        par_rang: Counter = Counter()
        detail: list = []
        for company in introuvables:
            _avant, _apres, matches = les_deux_regles(session, company)
            cause, ou, rang = ce_qui_a_change(session, company, matches,
                                              args.profondeur)
            par_cause[cause] += 1
            par_rang[ou] += 1
            detail.append((company, cause, ou, rang))
        for cause in CAUSES_DE_LA_PERTE:
            print(_ligne(cause, par_cause.get(cause, 0), len(introuvables)))
        print()
        for ou in RANGS:
            print(_ligne(ou, par_rang.get(ou, 0), len(introuvables)))
        print("""
   ⚠️ LA DÉRIVE EST RÉELLE, ET C'EST ELLE LE FAIT. `req_noms` n'oublie
      rien, `_scorer` prend le MEILLEUR des noms d'un NEQ, donc les
      scores montent et le lot grossit. Un dossier résolu hier devient
      ambigu aujourd'hui sans que personne ait rien changé.

   ⚠️ MAIS UNE REPRISE NE RETIRE RIEN. `reresolution_neq` POSE un NEQ là
      où la famille est RETENU; il n'efface jamais. Un dossier devenu
      ambigu garde le NEQ qu'il porte.
""")

        # ---- 4. LES PRÉTENDANTS MULTIPLES ---------------------------------
        # ✅ **La garde est DESCENDUE dans la résolution le 2026-09-23.** *Elle
        # n'a vécu que dans `outils/` du 17 au 23 septembre, et pendant ces six
        # jours `resolve_company` rattachait tous les dossiers visant un même
        # NEQ au MÊME `Company` — fusionnés de fait.* **La forme du refus a
        # changé en descendant**, et c'est la seule chose qu'elle pouvait faire
        # : le détenteur porte déjà le NEQ, et `Company.neq` est UNIQUE.
        from falkye.resolution import PRETENDANTS_MAX_POUR_TRANCHER

        vises: Counter = Counter()
        for _c, _a, apres, _m in changent + gagnent:
            if apres:
                vises[apres] += 1
        en_bloc = {neq: k for neq, k in vises.items()
                   if k > PRETENDANTS_MAX_POUR_TRANCHER}
        print("-" * 78)
        print("4. LES PRÉTENDANTS MULTIPLES — la garde du 17 septembre")
        print("-" * 78)
        print(f"""
   ✅ CETTE GARDE EST DESCENDUE DANS LA RÉSOLUTION le 23 septembre.
      `PRETENDANTS_MAX_POUR_TRANCHER = {PRETENDANTS_MAX_POUR_TRANCHER}` vit dans `falkye/resolution.py`,
      et `outils/pose_du_neq.py` l'EMPRUNTE. Du 17 au 23, elle n'a
      protégé que les passes par LOT.

   ⚠️ LA FORME DU REFUS A CHANGÉ EN DESCENDANT, et elle ne pouvait pas
      ne pas changer. La passe par LOT voit tous les prétendants
      ensemble et décide AVANT que quiconque ait le NEQ : elle peut donc
      refuser à TOUT LE MONDE. La résolution voit UN dossier à la fois,
      et le détenteur porte DÉJÀ le NEQ — que `Company.neq` soit UNIQUE
      interdit de le partager, et le lui retirer serait une écriture qui
      EFFACE une identité, pas une garde. Elle refuse donc au NOUVEAU
      VENU : il reste un dossier SÉPARÉ, sans NEQ, et le refus est
      journalisé (`statut="pretendant_refuse"`).

   ⚠️ CE QUI N'EST PAS DESCENDU, ET QUI RESTE À TRANCHER : le SEUIL.
      Au-delà de {PRETENDANTS_MAX_POUR_TRANCHER}, la passe par lot retire le NEQ à tout le
      monde; ici le premier arrivé le garde, et le rang est seulement
      ÉCRIT au journal pour rendre ces NEQ visibles. Révoquer le NEQ
      d'un détenteur est une décision d'Alexandre.
""")
        print(_ligne("NEQ visés par au moins un changement ou un gain", len(vises)))
        print(_ligne(TROP_DE_PRETENDANTS, len(en_bloc), len(vises)))
        if en_bloc:
            print()
            for neq, k in sorted(en_bloc.items(), key=lambda t: -t[1]):
                dossiers = [c for c, _a, ap, _m in changent + gagnent if ap == neq]
                print(f"      {neq}   {k} dossiers   "
                      f"{', '.join('#' + str(c.id) for c in dossiers[:8])}")
                for c in dossiers[:4]:
                    print(f"         #{c.id}  {(c.nom_detecte or '')[:60]}")
        print("""
   ⚠️ À TRANCHER AVANT TOUTE INTÉGRATION, que le cas se produise ou non
      sur cette population. La garde doit DESCENDRE dans la résolution,
      ou la règle ne doit pas y MONTER. Et le cas touche D27 et D28, qui
      ne sont pas tranchées : des établissements publics DISTINCTS
      finiraient sur une seule entité.
""")

        if args.paires and detail:
            print("=" * 78)
            print(f"LES DOSSIERS QUI NE SONT PLUS RÉSOLUS — {min(args.paires, len(detail))} "
                  f"sur {milliers(len(detail))}")
            print("=" * 78)
            for company, cause, ou, rang in detail[:args.paires]:
                print(f"\n   #{company.id}   {(company.nom_detecte or '')[:54]}")
                print(f"      NEQ posé : {company.neq}")
                print(f"      {cause}")
                print(f"      {ou}" + (f"   (rang {rang + 1})" if rang is not None else ""))

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
