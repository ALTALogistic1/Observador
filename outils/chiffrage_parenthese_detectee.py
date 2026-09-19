#!/usr/bin/env python3
"""Retirer la parenthèse du nom DÉTECTÉ — **et du sien seulement.**

**Les cas qui l'écrivent** *(cinq « trop faibles » tracés, 2026-09-19)* :

```
'9031-8395 Québec inc. (Réfrigération Air C)'   → 9031-8395 QUÉBEC INC.   90.00
'11888935 Canada Inc. (Workstaff)'              → 11888935 Canada Inc.    90.00
```

**Le bon candidat est présenté au scoreur, il est exact, et la parenthèse le
fait tomber de 100 à 90.** *La borne ne coupe pas, le repli ne sert pas, le
jumeau exact est introuvable parce que le nom détecté porte un mot de plus.*

## ⚠️ CE N'EST PAS LA CORRECTION DÉJÀ CHIFFRÉE

| | côté | rendu | quand |
|---|---|---|---|
| chiffrage du 17 septembre | **les DEUX côtés** | **+17 net** — 30 gagnés, **13 perdus** | fait |
| **celui-ci** | ⚠️ **le nom DÉTECTÉ seul** | *jamais mesuré* | ici |

**Les 13 perdus venaient du côté REGISTRE** : *`FERME BELLEVUE (1997) INC.`
privée de sa parenthèse passe de 86 à 95, et l'écart au second s'effondre.*
**Ici le registre n'est pas touché, donc aucun discriminant n'y est perdu.**

⚠️ **Une mesure qui rendrait « les parenthèses » sans dire de quel côté se
relirait comme la précédente.** *Le nom de ce fichier porte le côté, et chaque
tableau le rappelle.*

## ⚠️ Ce que le retrait touche AUSSI, et qui n'est pas le score

**`candidats_par_nom` cherche sur le nom DÉTECTÉ** *(`falkye/sources/req.py`)*.
Transformer ce nom change donc **les lignes rendues**, pas seulement les scores.

*Le préfixe est le PREMIER mot et la parenthèse n'est jamais première, donc la
récupération de premier temps ne bouge pas.* **Mais le second temps choisit le
mot le plus RARE du nom** — retirer des mots peut changer ce choix, donc le lot
élargi. **C'est mesuré et compté**, au lieu d'être supposé nul.

## Ce que le retrait ne résout pas — le consortium

```
'9141-2189 Québec inc. (F.A.S. Transfobec Mauricie) et 9254-6…'
   90.00  9141-2189 QUÉBEC INC.
   90.00  TRANSFOBEC MAURICIE      ← les deux existent au registre
```

**Le dossier désigne DEUX entreprises, et le produit trouve les deux.** *Ce n'est
pas un défaut de seuil* — **c'est le consortium, et il attend le chantier 3.**
⚠️ *Le retrait de la parenthèse ne le résout pas : il le déplace.* **Ces dossiers
sont comptés à part et signalés, jamais retirés du total** — *les écarter
changerait les chiffres en silence.*

⚠️ **AUCUNE ÉCRITURE. Les échelles ne bougent pas : seuil 92, écart 8.**

Usage, SUR L'HÔTE :
    python3 -m outils.chiffrage_parenthese_detectee
    python3 -m outils.chiffrage_parenthese_detectee --comparer 40
"""
from __future__ import annotations

import argparse
import re
from collections import Counter

from outils.nombres import milliers

#: Une parenthèse FERMÉE et ce qu'elle contient. ⚠️ **Une parenthèse non fermée
#: n'est pas touchée** — *un nom tronqué à la capture (`« … (Construction béton
#: 4 »`) n'a pas de fin, et deviner où elle s'arrêterait serait inventer.* Elles
#: sont **comptées à part**, pour que « la règle ne les atteint pas » soit un
#: chiffre et non un silence.
PARENTHESE_FERMEE = re.compile(r"\s*\([^()]*\)")

#: Une parenthèse OUVERTE que rien ne ferme.
PARENTHESE_NON_FERMEE = re.compile(r"\([^()]*$")

#: Ce qui, HORS parenthèse, fait qu'un nom désigne plusieurs entreprises. *Une
#: FORME, pas une certitude* — elle signale, elle ne tranche pas.
CONJONCTION = re.compile(r"\s(?:et|&)\s", re.IGNORECASE)

#: Une société à NUMÉRO : `9031-8395 Québec inc.`, `11888935 Canada Inc.`
SOCIETE_A_NUMERO = re.compile(r"^\s*\d[\d\s-]{4,}")


def sans_la_parenthese(nom: str | None) -> str:
    """Le nom **publié**, privé de ses parenthèses fermées.

    ⚠️ **Sur le nom PUBLIÉ, jamais sur la forme normalisée.** *`normaliser`
    remplace les parenthèses par des espaces : leur CONTENU survit comme mots.*
    **Une transformation appliquée à la forme normalisée serait un no-op déguisé
    en mesure** — c'est le défaut du 17 septembre, une table plus loin.
    """
    if not nom:
        return ""
    return PARENTHESE_FERMEE.sub("", nom).strip()


def porte_une_parenthese(nom: str | None) -> bool:
    return bool(nom) and bool(PARENTHESE_FERMEE.search(nom))


def _part(k: int, n: int) -> str:
    return f"{100 * k / n:.1f} %" if n else "—"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--comparer", type=int, default=0, metavar="N",
                        help="montrer N dossiers dont la FAMILLE change")
    parser.add_argument("--depuis", type=int, default=0, metavar="K")
    parser.add_argument("--tete", type=int, default=5, metavar="N",
                        help="taille de la TÊTE de table à comparer au reste (cas 19)")
    parser.add_argument("--limite", type=int, default=None, help="borner (mise au point)")
    args = parser.parse_args(argv)

    from sqlalchemy import select

    from falkye.db import refuser_si_cible_non_choisie

    code = refuser_si_cible_non_choisie()
    if code:
        return code

    from falkye.db import get_session
    from falkye.models.company import Company
    from falkye.resolution import (
        FAMILLES,
        SEUIL_AMBIGUITE_ECART_MIN,
        SEUIL_RESOLUTION_CONFIANTE,
        famille_de,
    )
    from falkye.sources import req as req_source

    print("=" * 78)
    print("RETIRER LA PARENTHÈSE DU NOM DÉTECTÉ — ET DU SIEN SEULEMENT")
    print("=" * 78)
    print(f"""
⚠️ CE QUE CETTE MESURE N'EST PAS

   ELLE NE TOUCHE PAS AU REGISTRE. Le chiffrage du 17 septembre retirait la
   parenthèse DES DEUX CÔTÉS : +17 net, 30 gagnés pour 13 PERDUS — et les
   perdus venaient du registre. « FERME BELLEVUE (1997) INC. » privée de sa
   parenthèse passe de 86 à 95, et l'écart au second s'effondre.

   ICI, SEUL LE NOM DÉTECTÉ EST TRANSFORMÉ. Aucun discriminant n'est retiré
   du registre. C'est une correction PLUS ÉTROITE, jamais mesurée.

   ⚠️ ELLE TOUCHE AUSSI LA RÉCUPÉRATION, et pas seulement les scores. Le
   préfixe est le premier mot, donc le premier temps ne bouge pas; mais le
   second temps choisit le mot le plus RARE, et retirer des mots peut changer
   ce choix. C'est compté plus bas.

   AUCUNE ÉCRITURE. Seuil {SEUIL_RESOLUTION_CONFIANTE:.0f}, écart
   {SEUIL_AMBIGUITE_ECART_MIN:.0f} — inchangés.
""")

    session = get_session()
    try:
        requete = select(Company).where(Company.neq.is_(None)).order_by(Company.id)
        if args.limite:
            requete = requete.limit(args.limite)
        orphelins = list(session.execute(requete).scalars().all())

        # ---- 1. LE PLAFOND ---------------------------------------------------
        avec = [c for c in orphelins if porte_une_parenthese(c.nom_detecte)]
        non_fermees = [
            c for c in orphelins
            if c.nom_detecte and PARENTHESE_NON_FERMEE.search(c.nom_detecte)
            and not porte_une_parenthese(c.nom_detecte)
        ]
        n_tot = len(orphelins)
        print("-" * 78)
        print("1. LE PLAFOND — combien de dossiers la règle peut seulement ATTEINDRE")
        print("-" * 78)
        print(f"\n   dossiers sans NEQ                      : {milliers(n_tot):>8}")
        print(f"   dont le nom détecté porte une PARENTHÈSE : {milliers(len(avec)):>6} "
              f"{_part(len(avec), n_tot):>8}   ← le plafond")
        print(f"   parenthèse OUVERTE que rien ne ferme     : {milliers(len(non_fermees)):>6} "
              f"{_part(len(non_fermees), n_tot):>8}")
        print("      ⚠️ *La règle ne les atteint pas : un nom tronqué à la capture")
        print("       n'a pas de fin, et deviner où elle s'arrêterait serait inventer.*")
        print("\n   ⚠️ Le compte du 17 septembre était 259 sur 8 931. *La population a")
        print("      changé — deux écritures ont eu lieu depuis* — donc ce chiffre-ci")
        print("      remplace l'autre, il ne le confirme pas.")
        if not avec:
            print("\n   Aucun dossier à mesurer.")
            return 0

        # ---- 2. LA COMPOSITION, ET LA TÊTE DE TABLE (cas 19) -----------------
        a_numero = [c for c in avec if SOCIETE_A_NUMERO.match(c.nom_detecte or "")]
        tete = avec[: args.tete]
        tete_a_numero = [c for c in tete if SOCIETE_A_NUMERO.match(c.nom_detecte or "")]
        print("\n" + "-" * 78)
        print("2. LA COMPOSITION — et si la TÊTE DE TABLE est représentative")
        print("-" * 78)
        print(f"""
   ⚠️ Les cinq cas tracés ont été pris par `id` CROISSANT. *Si les sociétés à
      numéro sont surreprésentées en tête, cinq cas décrivent la tête et pas la
      population* — c'est le cas 19, et la mesure doit le dire au lieu de
      laisser le lecteur le supposer.
""")
        print(f"   {'population':<44} {'à numéro':>10} {'part':>8}")
        print(f"   {'TOUS les dossiers à parenthèse':<44} "
              f"{milliers(len(a_numero)):>10} {_part(len(a_numero), len(avec)):>8}")
        # ⚠️ **La taille RÉELLE de la tête, pas celle demandée.** *Un libellé qui
        # annonce cinq au-dessus d'un compte de deux donne l'autorité d'une
        # mesure à un paramètre* — c'est le défaut du compte figé, en plus
        # discret.
        print(f"   {f'la TÊTE — les {len(tete)} premiers par id':<44} "
              f"{milliers(len(tete_a_numero)):>10} "
              f"{_part(len(tete_a_numero), len(tete)):>8}")
        ecart = abs(_taux(len(tete_a_numero), len(tete))
                    - _taux(len(a_numero), len(avec)))
        print(f"\n   écart entre la tête et la population : {ecart:.1f} points")
        print("   " + ("⚠️ La tête N'EST PAS représentative — les cinq cas décrivent"
                       if ecart >= 20 else
                       "✔ La tête ressemble à la population sur ce critère —"))
        print("      " + ("la tête, pas la population."
                          if ecart >= 20 else
                          "les cinq cas ne sont pas un artefact du tri."))
        print("   ⚠️ *Ça ne vaut que pour CE critère.* Un tirage par `id` peut rester")
        print("      biaisé sur un autre que personne n'a regardé.")

        # ---- 3. CE QUE LE RETRAIT REND --------------------------------------
        print("\n" + "-" * 78)
        print("3. CE QUE LE RETRAIT REND — par FAMILLE d'origine et de destination")
        print("-" * 78)
        destinations: dict[str, Counter] = {f: Counter() for f in FAMILLES}
        changes: list[tuple] = []
        perdus: list[tuple] = []
        lot_change = 0
        consortiums = 0
        for i, company in enumerate(avec):
            if i and i % 200 == 0:
                print(f"   … {milliers(i)} mesurés", flush=True)
            nom_nu = sans_la_parenthese(company.nom_detecte)
            avant = req_source.resolve_neq_by_name(
                session, company.nom_detecte, ville=company.ville)
            apres = req_source.resolve_neq_by_name(
                session, nom_nu, ville=company.ville)
            f_avant, f_apres = famille_de(avant), famille_de(apres)
            destinations[f_avant][f_apres] += 1
            if {m.entry.neq for m in avant} != {m.entry.neq for m in apres}:
                lot_change += 1
            if CONJONCTION.search(sans_la_parenthese(company.nom_detecte)):
                consortiums += 1
            if f_avant != f_apres:
                changes.append((company, nom_nu, avant, apres, f_avant, f_apres))
                if f_avant == "RETENU":
                    perdus.append((company, nom_nu, avant, apres))

        # ⚠️ LE CRITÈRE, AVANT LE GAIN.
        print(f"\n   {'⛔ RETENUS PERDUS':<44} {milliers(len(perdus)):>10}")
        print("      *C'est le critère, pas un effet secondaire.* Un RETENU perdu")
        print("      est un dossier que le produit résolvait et ne résout plus.")
        if perdus:
            print("\n      les voici — à lire avant tout gain :")
            for company, nom_nu, avant, apres in perdus[:10]:
                print(f"         {(company.nom_detecte or '')[:52]}")
                print(f"            sans la parenthèse : {nom_nu[:52]!r}")
                print(f"            avant {avant[0].score:.1f} « {avant[0].entry.nom[:34]} »")
                if apres:
                    print(f"            après {apres[0].score:.1f} "
                          f"« {apres[0].entry.nom[:34]} »"
                          + (f", 2e à {apres[1].score:.1f}" if len(apres) > 1 else ""))
        else:
            print("      ✔ Aucun. *Le registre n'étant pas touché, aucun discriminant")
            print("        n'y est perdu — c'est ce que cette forme étroite protège.*")

        print(f"\n   {'famille AVANT':<20} {'→ après':<20} {'dossiers':>9}")
        for origine in FAMILLES:
            total = sum(destinations[origine].values())
            if not total:
                continue
            for destination in FAMILLES:
                k = destinations[origine].get(destination, 0)
                if not k:
                    continue
                marque = ""
                if origine == "trop faible" and destination == "RETENU":
                    marque = "  ← le gain cherché"
                elif origine == "trop faible" and destination == "ambigu":
                    marque = "  ← bascule en ambigu"
                elif origine == "RETENU" and destination != "RETENU":
                    marque = "  ⛔ PERDU"
                fleche = "(inchangé)" if origine == destination else destination
                print(f"   {origine:<20} {fleche:<20} {milliers(k):>9}{marque}")
        print("\n   ⚠️ Le tableau dit où va CHAQUE dossier, pas seulement ce qui est")
        print("      gagné. *Un gain annoncé sans sa destination laisse croire que")
        print("      le reste n'a pas bougé.*")

        # ---- 4. CE QUE LA MESURE NE DIT PAS ---------------------------------
        print("\n" + "-" * 78)
        print("4. CE QUE CE CHIFFRE NE DIT PAS")
        print("-" * 78)
        print(f"\n   {'le lot de candidats a CHANGÉ':<44} {milliers(lot_change):>10} "
              f"{_part(lot_change, len(avec)):>8}")
        print("      *Retirer des mots change le mot le plus RARE, donc le lot du")
        print("       second temps.* **Le retrait n'est donc pas qu'un changement de")
        print("       score** — et là où le lot bouge, le gain vient des deux.")
        print(f"\n   {'noms qui désignent PLUSIEURS entreprises':<44} "
              f"{milliers(consortiums):>10} {_part(consortiums, len(avec)):>8}")
        print("      ⚠️ *Une conjonction HORS parenthèse — `et`, `&`.* **Le retrait")
        print("       ne les résout pas : il les déplace.** C'est le consortium, et il")
        print("       attend le chantier 3. *Comptés ici, jamais retirés du total —")
        print("       les écarter changerait les chiffres en silence.*")

        if args.comparer:
            lot = changes[args.depuis: args.depuis + args.comparer]
            print("\n" + "=" * 78)
            print(f"LES DOSSIERS QUI CHANGENT DE FAMILLE — {args.depuis + 1} à "
                  f"{args.depuis + len(lot)} sur {milliers(len(changes))}")
            print("=" * 78 + "\n")
            for company, nom_nu, avant, apres, f_avant, f_apres in lot:
                print(f"   {f_avant} → {f_apres}")
                print(f"      détecté : {(company.nom_detecte or '')[:64]!r}")
                print(f"      sans () : {nom_nu[:64]!r}")
                for etiquette, matches in (("avant", avant), ("après", apres)):
                    if not matches:
                        print(f"      {etiquette} : aucun candidat")
                        continue
                    tete_m = matches[0]
                    second = f", 2e {matches[1].score:.1f}" if len(matches) > 1 else ""
                    print(f"      {etiquette} : {tete_m.score:>6.2f}  {tete_m.entry.neq}"
                          f"  « {(tete_m.entry.nom or '')[:38]} »{second}")
                print()

        print("=" * 78)
        print("   RIEN N'A ÉTÉ ÉCRIT, ET LE REGISTRE N'A PAS ÉTÉ TOUCHÉ.")
        print("=" * 78)
        return 0
    finally:
        session.close()


def _taux(k: int, n: int) -> float:
    return 100 * k / n if n else 0.0


if __name__ == "__main__":
    raise SystemExit(main())
