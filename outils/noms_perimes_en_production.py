#!/usr/bin/env python3
"""LES NOMS PÉRIMÉS SONT-ILS DÉJÀ EN PRODUCTION — **une mesure, elle n'écrit rien.**

## ⚠️ CE QUI L'ÉCRIT — une garde retirée, une règle jamais posée

**Avant le 17 septembre**, `_charger_tous_les_noms` portait cette garde, et la
documentait comme **une décision** :

> *« Seuls les noms EN VIGUEUR (`STAT_NOM='V'`) entrent. L'historique des noms
> retirés ferait apparier une entreprise sous un nom qu'elle n'utilise plus — et
> une résolution vers une entreprise qui a changé de nom il y a dix ans est une
> fausse résolution, pas un rappel de plus. »*

**Le commit `a362d35` (17 septembre, 19 h 53) l'a retirée**, et l'a dit en une
phrase : *« la règle qui dit quoi faire d'un nom retiré se pose dans le moteur,
pas dans le chargeur… `statuts_retenus` reste disponible et vaut `None` par
défaut. »*

⚠️ **La règle n'est jamais arrivée dans le moteur.** *Vérifié : `candidats_par_nom`,
`_scorer` et `resolve_neq_by_name` ne lisent nulle part `REQNom.statut`.* **Un
nom retiré est aujourd'hui une porte à pleine force, indiscernable d'un nom en
vigueur.**

**Et `docs/CONCEPTION-TRAITEMENT-ARCHIVE-REQ.md` avait nommé le faux d'avance** :
*« un nom plus en vigueur peut appartenir à une AUTRE entreprise aujourd'hui —
une forme de faux que le pont actuel n'a pas, et aucune mesure ne la couvre »*.
Il proposait deux gardes — *« soit `resolve_neq_by_name` ne les consulte qu'en
second temps, soit leur score est plafonné »* — **et les appelait une décision
d'Alexandre.** *Ni l'une ni l'autre n'est construite.*

## Ce que cet outil mesure, et ce qu'il ne mesure pas

**1. Ce que `req_noms` porte** — par statut et par gisement. ⚠️ *Prédiction
vérifiable : les lignes sans gisement sont celles d'avant le 17, donc toutes en
`V` par construction.* **Si elle tombe, c'est la lecture de l'historique qui est
fausse, et il faut le savoir avant d'en conclure quoi que ce soit.**

**2. Ce que les NEQ POSÉS doivent à un nom périmé** — par rejeu de la résolution
sur les dossiers qui portent un NEQ, en lisant **la forme qui a gagné** et son
statut *(`formes_retenues`, le mécanisme du produit)*.

⚠️ **Ce que ça NE dit PAS : qu'un appariement par nom périmé soit FAUX.** *Un
nom abandonné mène souvent à la bonne entreprise* — un signal antérieur au
changement de nom, une source qui recopie l'inscription d'origine. **Le compte
dit l'EXPOSITION, jamais l'erreur.** *La mesurer est le point 25, et il n'existe
pas.*

⚠️ **RIEN N'EST ÉCRIT. Les échelles ne bougent pas : seuil 92, écart 8.**

Usage, SUR L'HÔTE :
    python3 -m outils.noms_perimes_en_production
    python3 -m outils.noms_perimes_en_production --exemples 15
"""
from __future__ import annotations

import argparse
from collections import Counter

from outils.nombres import milliers

#: Le code de `STAT_NOM` qui dit « en vigueur ». *Les autres sont des noms que
#: l'entreprise n'utilise plus.* ⚠️ **La valeur vient du chargeur d'avant le
#: 17 septembre**, qui comparait exactement à cette chaîne.
STATUT_EN_VIGUEUR = "V"

#: Ce que la ligne d'un gisement sans colonne de statut porte. *Emprunté, jamais
#: recopié* — `falkye/sources/req.py` le nomme.
def _statut_non_qualifie() -> str:
    from falkye.sources.req import STATUT_NON_QUALIFIE

    return STATUT_NON_QUALIFIE


#: Les trois natures d'une forme gagnante, **et chacune appelle une suite
#: différente.**
EN_VIGUEUR = "nom EN VIGUEUR"
PERIME = "⚠️ nom PLUS EN VIGUEUR — porte ouverte le 17 septembre"
NON_QUALIFIE = "statut non qualifié — le gisement n'a pas de colonne"
ELUE = "la dénomination élue de `req_entries`"
NATURES = (ELUE, EN_VIGUEUR, PERIME, NON_QUALIFIE)

LARGEUR = max(len(n) for n in NATURES) + 1


def nature_de(forme) -> str:
    """La nature d'une forme gagnante. ⚠️ *`None` ne se confond pas avec « en
    vigueur »* — une forme introuvable n'est pas une forme valide."""
    if forme is None:
        return NON_QUALIFIE
    if forme.est_la_denomination_elue:
        return ELUE
    if forme.statut is None or forme.statut == _statut_non_qualifie():
        return NON_QUALIFIE
    return EN_VIGUEUR if forme.statut.strip().upper() == STATUT_EN_VIGUEUR else PERIME


def _part(k: int, n: int) -> str:
    return f"{100 * k / n:.1f} %" if n else "—"


def _ligne(etiquette: str, k: int, n: int = 0) -> str:
    part = f" {_part(k, n):>8}" if n else ""
    return f"   {etiquette:<{LARGEUR}} {milliers(k):>11}{part}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--exemples", type=int, default=0, metavar="N",
                        help="montrer N dossiers posés sur un nom PÉRIMÉ")
    parser.add_argument("--limite", type=int, default=None, help="borner (mise au point)")
    parser.add_argument("--pas", type=int, default=500, metavar="N")
    args = parser.parse_args(argv)

    from sqlalchemy import func, select

    from falkye.db import refuser_si_cible_non_choisie

    code = refuser_si_cible_non_choisie()
    if code:
        return code

    from falkye.db import get_session
    from falkye.models.company import Company
    from falkye.models.req_nom import REQNom
    from falkye.sources import req as req_source
    from outils.reresolution_neq import _resoudre_une

    session = get_session()
    try:
        print("=" * 78)
        print("LES NOMS PÉRIMÉS SONT-ILS DÉJÀ EN PRODUCTION — une MESURE")
        print("=" * 78)
        print("""
⚠️ UNE GARDE RETIRÉE, UNE RÈGLE JAMAIS POSÉE

   Avant le 17 septembre, seuls les noms EN VIGUEUR entraient dans
   `req_noms`, et le chargeur documentait ce filtre comme une DÉCISION. Le
   commit a362d35 l'a retiré en disant que la règle se poserait « dans le
   moteur, pas dans le chargeur ». Vérifié : ni `candidats_par_nom`, ni
   `_scorer`, ni `resolve_neq_by_name` ne lisent `REQNom.statut`.

   Un nom retiré est donc aujourd'hui une porte à PLEINE FORCE.

⚠️ CE QUE CE COMPTE NE DIT PAS

   Qu'un appariement par nom périmé soit FAUX. Un nom abandonné mène
   souvent à la bonne entreprise — un signal antérieur au changement de
   nom, une source qui recopie l'inscription d'origine. LE COMPTE DIT
   L'EXPOSITION, JAMAIS L'ERREUR.

⚠️ RIEN N'EST ÉCRIT.
""")

        # ---- 1. CE QUE `req_noms` PORTE -----------------------------------
        print("-" * 78)
        print("1. CE QUE `req_noms` PORTE AUJOURD'HUI")
        print("-" * 78 + "\n")
        total = session.execute(
            select(func.count()).select_from(REQNom)).scalar_one()
        par_statut = session.execute(
            select(REQNom.statut, func.count()).group_by(REQNom.statut)).all()
        for statut, combien in sorted(par_statut, key=lambda t: -t[1]):
            etiquette = (f"statut « {statut} »" if statut else "statut absent")
            if statut and statut.strip().upper() == STATUT_EN_VIGUEUR:
                etiquette += "  (en vigueur)"
            elif statut and statut != _statut_non_qualifie():
                etiquette += "  ⚠️ PLUS EN VIGUEUR"
            print(_ligne(etiquette, combien, total))
        print(_ligne("TOTAL", total))

        sans_gisement, _ = req_source.lignes_sans_gisement(session)
        perimes_sans_gisement = session.execute(
            select(func.count()).select_from(REQNom).where(
                REQNom.gisement.is_(None),
                func.upper(REQNom.statut) != STATUT_EN_VIGUEUR)
        ).scalar_one()
        print(f"""
   LA PRÉDICTION, ET SON CONTRÔLE

      Les lignes SANS gisement sont celles d'avant le 17 septembre, donc
      chargées sous le filtre « en vigueur seulement ». Elles devraient
      toutes porter « V ».

         lignes sans gisement          : {milliers(sans_gisement):>11}
         … dont PAS en vigueur         : {milliers(perimes_sans_gisement):>11}   (attendu : 0)
""")
        if perimes_sans_gisement:
            print("   ⚠️ LA PRÉDICTION TOMBE. La lecture de l'historique est fausse,")
            print("      et rien de ce qui suit ne doit s'interpréter avant de savoir")
            print("      pourquoi.\n")

        # ---- 2. CE QUE LES NEQ POSÉS DOIVENT À UN NOM PÉRIMÉ --------------
        requete = select(Company).where(Company.neq.is_not(None)).order_by(Company.id)
        if args.limite:
            requete = requete.limit(args.limite)
        poses = list(session.execute(requete).scalars().all())
        if not poses:
            print("   Aucun dossier ne porte de NEQ.")
            return 0

        print("-" * 78)
        print("2. SUR QUELLE FORME LES NEQ POSÉS ONT-ILS ÉTÉ TROUVÉS")
        print("-" * 78)
        print(f"\n… rejeu de la résolution sur {milliers(len(poses))} dossiers posés, "
              f"par le chemin de production", flush=True)

        par_nature: Counter = Counter()
        sur_perime: list[tuple] = []
        introuvables = 0
        for i, company in enumerate(poses, 1):
            if args.pas and i % args.pas == 0:
                print(f"   … {milliers(i)} / {milliers(len(poses))}", flush=True)
            _neq, matches = _resoudre_une(session, company)
            retenu = next((m for m in matches if m.entry.neq == company.neq), None)
            if retenu is None:
                # ⚠️ Le rejeu ne retrouve pas le NEQ posé. *C'est un RÉSULTAT* —
                # la résolution d'aujourd'hui ne rendrait plus ce dossier.
                introuvables += 1
                continue
            formes = req_source.formes_retenues(session, [retenu])
            forme = formes.get((retenu.entry.neq, retenu.forme_normalisee))
            nature = nature_de(forme)
            par_nature[nature] += 1
            if nature == PERIME:
                sur_perime.append((company, retenu, forme))

        n = sum(par_nature.values())
        print()
        for nature in NATURES:
            print(_ligne(nature, par_nature.get(nature, 0), n))
        if introuvables:
            print(_ligne("⚠️ le rejeu ne retrouve plus le NEQ posé",
                         introuvables, len(poses)))
        print(f"""
   ⚠️ « PLUS EN VIGUEUR » N'EST PAS « FAUX ». C'est l'EXPOSITION : le
      nombre de NEQ posés dont la porte d'entrée est un nom que
      l'entreprise n'utilise plus. Ce que ça vaut se lit dans les paires.

   ⚠️ ET LA GARDE MANQUANTE EST UNE DÉCISION D'ALEXANDRE, déjà nommée
      dans la conception du 17 septembre : soit `resolve_neq_by_name` ne
      consulte les noms périmés qu'en SECOND TEMPS, soit leur score est
      PLAFONNÉ. Ni l'une ni l'autre n'est construite.
""")

        if args.exemples and sur_perime:
            print("=" * 78)
            print(f"DES DOSSIERS POSÉS SUR UN NOM PÉRIMÉ — "
                  f"{min(args.exemples, len(sur_perime))} sur {milliers(len(sur_perime))}")
            print("=" * 78)
            for company, retenu, forme in sur_perime[:args.exemples]:
                print(f"\n   #{company.id}   {(company.nom_detecte or '')[:54]}")
                print(f"      → {company.neq}  {retenu.score:>6.1f}  "
                      f"{(retenu.entry.nom or '—')[:40]}   [{retenu.entry.statut}]")
                print(f"      ↳ a scoré sur « {(forme.nom_publie or '—')[:44] } »"
                      f"   ({forme.gisement})   [nom : {forme.statut}]")

        print("\n" + "=" * 78)
        print("   RIEN N'A ÉTÉ ÉCRIT. Les échelles n'ont pas bougé.")
        print("   ⚠️ Le compte dit l'EXPOSITION, jamais l'erreur.")
        print("=" * 78)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
