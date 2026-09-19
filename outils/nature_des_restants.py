#!/usr/bin/env python3
"""D'où viennent les restants, et de quelle nature ils sont — **trois mesures, une passe.**

⚠️ **CE QUE CES MESURES NE DIRONT PAS, et il faut le lire avant les chiffres :
qu'une entreprise sans NEQ soit RÉCUPÉRABLE.** *Elles disent d'où viennent les
restants et de quelle nature ils sont — pas ce qui les débloquerait.*

## 1. La ventilation par SOURCE, avec l'adresse

Trois théories d'un coup, et **aucune ne se tranche par la source seule** :

- **L'origine pancanadienne.** *`rob_top_growing` et `deloitte_fast50` sont des
  classements canadiens, et le registre des sources les porte à
  `territoire: null`.* ⚠️ **Vérifié plus fort que ça** : `province_code` est
  **null sur TOUTES les sources**, et c'est le seul champ que
  `falkye/expansion_interprovinciale.py` lit pour la province. *Rien ne filtre
  par province nulle part, et le mécanisme prévu pour le faire n'a pas de
  données.*
- **Les personnes physiques.** *Le Registraire ne publie pas leur nom. Elles sont
  au bassin parce qu'une source les a détectées — donc elles portent une
  activité réelle.*
- **Les indépartageables.** *2 970 ambigus que ni l'adresse ni l'activité ne
  séparent.*

> ⚠️ **L'origine ne dit pas la pertinence.** *`Altis Human Resources (Ottawa)
> Inc.` est une entité d'Ottawa qui dessert le Québec, et qui y est
> immatriculée.* **Donc la mesure rend l'ADRESSE, pas seulement la source.**

⚠️ **Et une ventilation des restants SEULE ne peut pas dire « surreprésentée ».**
*Il faut la même ventilation sur les dossiers RÉSOLUS et le rapport des deux* —
sinon « 12 % des restants viennent de X » ne se compare à rien.

## 2. Les champs multi-entités

**Une conjonction entre DEUX FORMES JURIDIQUES** — `« 9528-9393 Québec inc.,
Fabrication A.S. inc. & Maurice Milette »`.

⚠️ **La règle est plus stricte que celle du chiffrage de la parenthèse**, qui
comptait toute conjonction et rendait 17 sur 148 *(11,5 %)*. **Les deux chiffres
ne sont pas comparables** : *`« Gagnon et Fils inc. »` passait pour un consortium
avec l'ancienne règle et n'en est pas un.*

## 3. Les doublons du produit

**Deux dossiers qui désignent la même entreprise sous des noms différents.**

⚠️ **Ce qui se compte ici est l'EXACT sur la forme normalisée** — *donc les
variantes de casse et de ponctuation, `AYE3D inc.` contre `AYE3D Inc.`* **Ce qui
ne s'y compte pas, et qui est nommé plutôt que tu :** `PHILIPS CANADA` contre
`PHILIPS ÉLECTRONIQUE LTÉE`. *Aucune clé exacte ne les réunit; il faudrait une
passe floue, qui est une autre mesure.*

## ⚠️ Ce que 2 et 3 servent à décider

**Elles ne cherchent pas un correctif. Elles disent si le chantier 3 — une
identité, plusieurs identifiants, plusieurs noms — vaut ce qu'il coûte.**

*Un consortium demande DEUX NEQ sur un dossier; un doublon demande UN dossier qui
porte DEUX noms.* **Le modèle actuel ne permet ni l'un ni l'autre.**

⚠️ **AUCUNE ÉCRITURE. Les échelles ne bougent pas : seuil 92, écart 8.**

Usage, SUR L'HÔTE :
    python3 -m outils.nature_des_restants
    python3 -m outils.nature_des_restants --comparer 30
"""
from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict

from outils.nombres import milliers

#: Les formes juridiques, telles qu'un nom détecté les porte. *Une observation,
#: pas une nomenclature* — le Registraire en publie d'autres, et celles-ci sont
#: celles qui apparaissent dans les noms captés.
FORME_JURIDIQUE = re.compile(
    r"\b(?:inc|ltee|ltée|ltd|llc|l\.?l\.?c|s\.?e\.?n\.?c(?:\.?r\.?l)?|srl|enr|"
    r"corp|corporation|cie|limitee|limitée|limited|incorporated|"
    r"cooperative|coopérative|coop)\b\.?",
    re.IGNORECASE,
)

#: Ce qui sépare deux entités nommées dans un même champ.
SEPARATEUR_DENTITES = re.compile(r"\s+et\s+|\s*&\s*|\s*,\s*(?=\S)", re.IGNORECASE)

#: Les codes de province, tels qu'une adresse les écrit. ⚠️ **`ON` est le seul
#: ambigu** — *c'est aussi un mot français et anglais* — et il n'est reconnu que
#: comme JETON isolé, jamais comme sous-chaîne.
PROVINCES = ("QC", "ON", "AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "PE",
             "SK", "YT")


def entites_nommees(nom: str | None) -> list[str]:
    """Les morceaux du nom qui portent une FORME JURIDIQUE.

    ⚠️ **Deux formes juridiques séparées par une conjonction, pas une
    conjonction quelconque.** *`« Gagnon et Fils inc. »` n'a qu'une forme : ce
    n'est pas un consortium.* **`« X inc. & Y inc. »` en a deux.**
    """
    if not nom:
        return []
    return [m for m in SEPARATEUR_DENTITES.split(nom) if FORME_JURIDIQUE.search(m)]


def nomme_plusieurs_entites(nom: str | None) -> bool:
    return len(entites_nommees(nom)) >= 2


def provinces_du_texte(texte: str | None) -> set[str]:
    """Les codes de province présents **comme jetons**. *`« Mississauga, ON L5N
    0A4 »` rend `{'ON'}`; `« Ontario »` n'en rend aucun* — on lit ce qui est
    écrit, pas ce qu'on devine."""
    if not texte:
        return set()
    jetons = set(re.findall(r"[A-Za-z]+", texte.upper()))
    return jetons & set(PROVINCES)


def _part(k: int, n: int) -> str:
    return f"{100 * k / n:.1f} %" if n else "—"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--comparer", type=int, default=0, metavar="N",
                        help="montrer N champs multi-entités et N groupes de doublons")
    parser.add_argument("--limite", type=int, default=None, help="borner (mise au point)")
    args = parser.parse_args(argv)

    from sqlalchemy import select

    from falkye.db import refuser_si_cible_non_choisie

    code = refuser_si_cible_non_choisie()
    if code:
        return code

    from falkye.db import get_session
    from falkye.models.company import Company
    from falkye.models.signal import Signal
    from falkye.resolution import SEUIL_AMBIGUITE_ECART_MIN, SEUIL_RESOLUTION_CONFIANTE
    from outils.departageur_adresse import (
        CLES_ADRESSE,
        champs_des_dossiers,
        texte_des_champs,
    )
    from outils.departageurs import codes_postaux
    from outils.villes_des_signaux import villes_des_signaux

    print("=" * 78)
    print("D'OÙ VIENNENT LES RESTANTS, ET DE QUELLE NATURE ILS SONT")
    print("=" * 78)
    print(f"""
⚠️ CE QUE CES MESURES NE DIRONT PAS — à lire avant tout chiffre

   QU'UNE ENTREPRISE SANS NEQ SOIT RÉCUPÉRABLE. Elles disent d'où viennent
   les restants et de quelle nature ils sont — pas ce qui les débloquerait.

   L'ORIGINE NE DIT PAS LA PERTINENCE. `Altis Human Resources (Ottawa) Inc.`
   est une entité d'Ottawa qui dessert le Québec, et qui y est immatriculée.
   Une source pancanadienne ne veut pas dire « rien à trouver ».

   ⚠️ ET UNE VENTILATION DES RESTANTS SEULE NE DIT PAS « SURREPRÉSENTÉE ».
   C'est le RAPPORT avec la même ventilation sur les dossiers résolus qui le
   dit. Les deux sont rendues ci-dessous, jamais l'une sans l'autre.

   AUCUNE ÉCRITURE. Seuil {SEUIL_RESOLUTION_CONFIANTE:.0f}, écart
   {SEUIL_AMBIGUITE_ECART_MIN:.0f} — inchangés.
""")

    session = get_session()
    try:
        requete = select(Company).order_by(Company.id)
        if args.limite:
            requete = requete.limit(args.limite)
        tous = list(session.execute(requete).scalars().all())
        restants = [c for c in tous if c.neq is None]
        resolus = [c for c in tous if c.neq is not None]
        n = len(restants)
        print(f"   dossiers au total : {milliers(len(tous))}")
        print(f"   RESTANTS (sans NEQ) : {milliers(n)}"
              f"   ·   résolus : {milliers(len(resolus))}\n")
        if not restants:
            print("   Aucun restant à mesurer.")
            return 0

        # ---- les sources de chaque dossier, en une passe --------------------
        sources: dict[int, set[str]] = defaultdict(set)
        for company_id, source_id in session.execute(
            select(Signal.company_id, Signal.source_id).execution_options(yield_per=2000)
        ):
            sources[company_id].add(source_id)

        # ---- 1. PAR SOURCE, avec l'adresse ----------------------------------
        print("-" * 78)
        print("1. PAR SOURCE — les restants, les résolus, et le RAPPORT des deux")
        print("-" * 78)
        par_source_restants: Counter = Counter()
        par_source_resolus: Counter = Counter()
        for c in restants:
            for s in sources.get(c.id, {"(aucun signal)"}):
                par_source_restants[s] += 1
        for c in resolus:
            for s in sources.get(c.id, {"(aucun signal)"}):
                par_source_resolus[s] += 1
        print("\n   ⚠️ Un dossier CUMULE les signaux, donc il compte dans CHAQUE source")
        print("      qui l'a vu. *Les colonnes ne s'additionnent pas au total* — et")
        print("      les présenter comme une partition serait faux.\n")
        print(f"   {'source':<30} {'restants':>9} {'part':>8} "
              f"{'résolus':>9} {'part':>8} {'rapport':>9}")
        for source, k in par_source_restants.most_common():
            r = par_source_resolus.get(source, 0)
            part_rest = 100 * k / n
            part_res = 100 * r / len(resolus) if resolus else 0.0
            # ⚠️ **Une source dont AUCUN dossier n'est résolu est le cas le plus
            # fort, pas un cas manquant.** *Écrire `—` y masquerait ce que la
            # mesure cherche* : une source présente chez les restants et nulle
            # part ailleurs.
            if part_res:
                rapport = f"×{part_rest / part_res:.1f}"
                marque = "  ← surreprésentée" if part_rest / part_res >= 1.5 else ""
            else:
                rapport = "AUCUN"
                marque = "  ← JAMAIS résolue"
            print(f"   {source:<30} {milliers(k):>9} {part_rest:>7.1f} % "
                  f"{milliers(r):>9} {part_res:>7.1f} % {rapport:>9}{marque}")
        print("\n   ⚠️ « rapport » est la part chez les restants divisée par la part")
        print("      chez les résolus. *Au-dessus de 1, la source est plus présente")
        print("      chez les restants* — ce qui dit qu'elle résout moins bien, jamais")
        print("      POURQUOI. Une source pancanadienne et une source dont les noms")
        print("      sont sales donnent le même rapport.")

        # --- l'adresse, par source ------------------------------------------
        champs = champs_des_dossiers(session, {c.id for c in restants})
        villes = villes_des_signaux(session, {c.id for c in restants})
        adresse_par_source: dict[str, Counter] = defaultdict(Counter)
        provinces_par_source: dict[str, Counter] = defaultdict(Counter)
        for c in restants:
            texte = " ".join(filter(None, [
                c.adresse, c.code_postal,
                texte_des_champs(champs.get(c.id), CLES_ADRESSE),
            ]))
            a_ville = bool(c.ville or (c.id in villes))
            a_code = codes_postaux(texte) is not None
            provs = provinces_du_texte(texte)
            for s in sources.get(c.id, {"(aucun signal)"}):
                adresse_par_source[s]["dossiers"] += 1
                adresse_par_source[s]["ville"] += 1 if a_ville else 0
                adresse_par_source[s]["code postal"] += 1 if a_code else 0
                adresse_par_source[s]["province"] += 1 if provs else 0
                for p in provs:
                    provinces_par_source[s][p] += 1

        print(f"\n   {'source':<30} {'dossiers':>9} {'ville':>8} "
              f"{'code post.':>11} {'province':>9}")
        for source, _ in par_source_restants.most_common():
            a = adresse_par_source[source]
            print(f"   {source:<30} {milliers(a['dossiers']):>9} "
                  f"{_part(a['ville'], a['dossiers']):>8} "
                  f"{_part(a['code postal'], a['dossiers']):>11} "
                  f"{_part(a['province'], a['dossiers']):>9}")
            provs = provinces_par_source.get(source)
            if provs:
                detail = "  ".join(f"{p} {milliers(k)}" for p, k in provs.most_common(5))
                print(f"      {detail}")
        print("\n   ⚠️ La province est lue comme un JETON de l'adresse — `« …, ON L5N »`")
        print("      rend `ON`, `« Ontario »` ne rend rien. *On lit ce qui est écrit,")
        print("      pas ce qu'on devine.* Et `ON` est le seul code ambigu.")
        print("   ⚠️ Une adresse hors Québec NE VEUT PAS DIRE hors registre : `Altis")
        print("      Human Resources (Ottawa) Inc.` est immatriculée au Québec.")

        # ---- 2. LES CHAMPS MULTI-ENTITÉS -------------------------------------
        print("\n" + "-" * 78)
        print("2. LES CHAMPS MULTI-ENTITÉS — deux formes juridiques, une conjonction")
        print("-" * 78)
        multi = [c for c in restants if nomme_plusieurs_entites(c.nom_detecte)]
        print(f"\n   {'restants dont le nom désigne PLUSIEURS entités':<50} "
              f"{milliers(len(multi)):>9} {_part(len(multi), n):>8}")
        print("""
   ⚠️ LA RÈGLE EST PLUS STRICTE QUE CELLE DU CHIFFRAGE DE LA PARENTHÈSE, qui
      comptait toute conjonction et rendait 17 sur 148 (11,5 %). Les deux
      chiffres ne sont PAS comparables : « Gagnon et Fils inc. » passait pour
      un consortium avec l'ancienne règle, et n'en est pas un.

   ⚠️ Ce compte ne cherche pas un correctif. Un consortium demande DEUX NEQ
      sur un dossier, et le modèle n'en permet qu'un — `Company.neq` est
      unique, et la contrainte est portée par la base.
""")
        if args.comparer and multi:
            print(f"   quelques-uns — {min(args.comparer, len(multi))} sur "
                  f"{milliers(len(multi))} :\n")
            for c in multi[: args.comparer]:
                parts = entites_nommees(c.nom_detecte)
                print(f"      {(c.nom_detecte or '')[:62]}")
                print(f"         {len(parts)} entités : {[p.strip()[:26] for p in parts]}")
            print()

        # ---- 3. LES DOUBLONS DU PRODUIT --------------------------------------
        print("-" * 78)
        print("3. LES DOUBLONS DU PRODUIT — même forme normalisée, dossiers distincts")
        print("-" * 78)
        par_forme: dict[str, list] = defaultdict(list)
        for c in tous:
            if c.nom_detecte_normalise:
                par_forme[c.nom_detecte_normalise].append(c)
        groupes = [g for g in par_forme.values() if len(g) > 1]
        en_trop = sum(len(g) - 1 for g in groupes)
        avec_un_resolu = [g for g in groupes if any(x.neq for x in g)]
        graphie_seule = [
            g for g in groupes
            if len({x.nom_detecte for x in g}) > 1
        ]
        print(f"\n   {'groupes de dossiers à forme normalisée IDENTIQUE':<50} "
              f"{milliers(len(groupes)):>9}")
        print(f"   {'dossiers EN TROP (le groupe moins un)':<50} "
              f"{milliers(en_trop):>9} {_part(en_trop, len(tous)):>8}")
        print(f"   {'dont un membre porte DÉJÀ un NEQ':<50} "
              f"{milliers(len(avec_un_resolu)):>9}")
        print(f"   {'dont les graphies DIFFÈRENT (casse, ponctuation)':<50} "
              f"{milliers(len(graphie_seule)):>9}")
        print("""
   ⚠️ CE QUI NE SE COMPTE PAS ICI, et il faut le dire : `PHILIPS CANADA` contre
      `PHILIPS ÉLECTRONIQUE LTÉE`, `Casa Grecque Drummondville` contre
      `3038947 Canada Inc.` Aucune clé EXACTE ne les réunit — il faudrait une
      passe floue, qui est une autre mesure. Ce compte est donc un PLANCHER.

   ⚠️ Et il ne cherche pas un correctif. Un doublon demande UN dossier qui
      porte DEUX noms; le modèle n'en permet qu'un.

   Indices antérieurs, d'une autre nature : 32 dossiers en trop sur 805
   retenus au 16 septembre, et les 111 NEQ « déjà pris » de la passe.
""")
        if args.comparer and graphie_seule:
            print(f"   quelques groupes — {min(args.comparer, len(graphie_seule))} "
                  f"sur {milliers(len(graphie_seule))} :\n")
            for g in graphie_seule[: args.comparer]:
                for x in g:
                    neq = x.neq or "—"
                    print(f"      #{x.id:<7} {neq:<12} {(x.nom_detecte or '')[:46]}")
                print()

        print("=" * 78)
        print("   RIEN N'A ÉTÉ ÉCRIT. Ces mesures disent D'OÙ VIENNENT les restants")
        print("   et DE QUELLE NATURE ils sont — jamais qu'ils soient récupérables.")
        print("=" * 78)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
