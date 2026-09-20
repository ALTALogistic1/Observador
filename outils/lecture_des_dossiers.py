#!/usr/bin/env python3
"""Des DOSSIERS ENTIERS à lire — **pas des comptes.**

## Le motif

**Quatorze hypothèses sont tombées. La seule qui ait tenu — l'activité
économique — venait d'un cas tracé de bout en bout**, jamais d'une ventilation.
*Elle ne serait sortie d'aucune des mesures qu'on avait demandées.* **C'est ce
geste-là qu'on refait.**

## ⚠️ CE QUE CET OUTIL N'EST PAS, et il faut le lire avant sa sortie

**Ce n'est pas une mesure, et sa sortie ne s'habille pas en mesure.** *Une part,
un pourcentage ou un rapport tiré d'une lecture de vingt dossiers se relirait
comme une population dans trois semaines.* ⚠️ **Aucun pourcentage n'est imprimé
dans les dossiers** — un test le vérifie.

**Ce n'est pas un classement par jugement.** *Pas de « probablement
récupérable ».* **L'outil rend ce que le dossier PORTE; ce qu'on en lit vient
après, et il n'en est pas l'auteur.**

## Ce qu'il rend, et pourquoi chaque pièce y est

Pour chaque dossier : **le nom détecté tel quel**, sa forme normalisée, **ses
sources**, **le sac de champs ENTIER**, l'adresse telle qu'elle est écrite, l'âge
du signal — puis **chaque candidat** avec son NEQ, sa dénomination élue, ⚠️ **la
forme du registre qui a REMPORTÉ le score** *(cas 33 — la dénomination élue n'est
presque jamais celle qui a décidé)*, son score, sa ville, son code postal et son
secteur.

⚠️ **Le sac de champs est rendu ENTIER, jamais filtré.** *Choisir les champs à
montrer, c'est déjà avoir décidé où regarder* — et la piste de l'activité est
sortie d'un champ que personne n'avait demandé.

## ⚠️ RÉPARTIS, jamais pris en tête de table

**C'est le cas 19 : un tri promu en échantillon.** *Les cinq cas du 19 septembre
décrivaient la tête — 100 % de sociétés à numéro contre 22,3 % dans la
population.* **Le balayage est à PAS CONSTANT, et par FAMILLE** : ambigu, trop
faible, aucun candidat, chacune parcourue sur toute sa longueur.

## Les lectures déjà faites, pour qu'on ne les refasse pas

⚠️ **Elles sont d'Alexandre, et AUCUNE n'est mesurée.** *Ce sont des lectures,
pas des prémisses — si les dossiers en contredisent une, c'est un résultat.*

1. **L'entreprise serait plus récente que l'archive.** *Les signaux de 30 jours
   ou moins sont ×1,6 chez les restants, et le miroir date du 2 septembre.*
2. **Un nom d'un seul mot ne peut pas ouvrir d'écart.** *239 dossiers, ×3,4 — le
   rapport le plus fort du portrait après l'adresse.*
3. **Le bon candidat ne serait pas dans le lot.** *Tous les restants ont de 3 à 5
   candidats.* **On sait ce que la récupération rend; personne n'a vérifié si la
   bonne entreprise en fait partie.**
4. **Les 974 noms en lettres sans code postal seraient d'une autre nature.**
   *57,3 % de trop faibles contre 18 % ailleurs.*

⚠️ **AUCUNE ÉCRITURE. Les échelles ne bougent pas : seuil 92, écart 8.**

Usage, SUR L'HÔTE :
    python3 -m outils.lecture_des_dossiers
    python3 -m outils.lecture_des_dossiers --par-famille 12 --depuis 1
    python3 -m outils.lecture_des_dossiers --lentille un-seul-mot --par-famille 8
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone

from outils.nombres import milliers

#: Combien de dossiers par famille, par défaut. *Assez pour qu'un motif se
#: répète, assez peu pour qu'on les lise vraiment.*
PAR_FAMILLE_DEFAUT = 8

#: Les lentilles — **pour VÉRIFIER un motif APRÈS l'avoir vu, jamais pour le
#: chercher.** ⚠️ *Une lentille employée d'abord rend une lecture qui confirme ce
#: qu'on est allé chercher* — c'est le défaut que le cas 19 décrit, sous une
#: autre forme. **La sortie le redit quand une lentille est active.**
LENTILLES = {
    "un-seul-mot": ("le nom normalisé ne porte qu'un mot",
                    lambda c, ctx: len((c.nom_detecte_normalise or "").split()) == 1),
    "sans-code-postal": ("aucun code postal, à aucune résolution",
                         lambda c, ctx: ctx["finesse"](c) not in ctx["avec_code"]),
    "tete-numerique": ("la tête du nom est numérique",
                       lambda c, ctx: ctx["est_numero"](c.nom_detecte_normalise or "")),
    "signal-recent": ("le signal le plus récent a 30 jours ou moins",
                      lambda c, ctx: (ctx["age"](c) or 10**6) <= 30),
    "signal-vieux": ("le signal le plus récent a plus d'un an",
                     lambda c, ctx: (ctx["age"](c) or 0) > 365),
}


def a_pas_constant(lot: list, combien: int, depuis: int = 0) -> list:
    """Un balayage **à pas constant** sur toute la longueur du lot.

    ⚠️ **`lot[:combien]` rendrait la TÊTE**, et la tête d'une liste triée par
    identifiant est la plus ancienne — *c'est le cas 19, et il a déjà coûté une
    lecture entière.* **`depuis` décale le balayage sans le resserrer**, pour
    qu'une seconde lecture porte sur d'autres dossiers et non sur les mêmes.
    """
    if combien <= 0 or not lot:
        return []
    if combien >= len(lot):
        return list(lot)
    pas = len(lot) / combien
    return [lot[min(len(lot) - 1, int(i * pas) + depuis)] for i in range(combien)]


#: `STAT_NOM`, décodé. ⚠️ **Lu dans le code, pas supposé** :
#: `falkye/sources/req.py::_charger_index_noms` documente les deux valeurs,
#: *« confirmé par inspection réelle du 2026-08-31 »* et *« confirmé sur un vrai
#: NEQ radié »*. **Toute autre valeur est rendue NUE** — inventer un libellé pour
#: un code qu'on n'a pas lu est pire que de l'afficher tel quel.
LIBELLE_DU_STATUT_DE_NOM = {"V": "en vigueur", "A": "antérieur"}


def statut_du_nom(code: str | None) -> str:
    """⚠️ **C'est le statut du NOM, jamais celui de l'ENTREPRISE.**

    *Un nom passe à `A` quand l'entreprise en change — et AUSSI quand elle est
    radiée, son dernier nom repassant à `A`.* **Donc `A` ne veut pas dire
    radiée**, et lire l'un pour l'autre fait conclure sur la mauvaise colonne.
    """
    if not code:
        return "(inconnu)"
    libelle = LIBELLE_DU_STATUT_DE_NOM.get(code.strip().upper())
    return f"{code} ({libelle})" if libelle else f"{code} (libellé non lu)"


def _valeur_lisible(valeur, largeur: int = 96) -> str:
    """Une valeur de `Signal.champs`, rendue **sans être interprétée.**

    *Une liste de classifications, un nombre, une chaîne* — tout passe par ici,
    et rien n'y est traduit. ⚠️ **Tronquer est le seul geste permis**, parce
    qu'une ligne de deux mille caractères ne se lit pas.
    """
    texte = repr(valeur) if not isinstance(valeur, str) else valeur
    texte = " ".join(texte.split())
    return texte if len(texte) <= largeur else texte[: largeur - 1] + "…"


def rendre_le_dossier(company, sources, champs, faits, age, matches,
                      formes, rang: int, total: int, famille: str) -> None:
    """Un dossier ENTIER. ⚠️ **Aucun pourcentage n'entre ici.**"""
    print("─" * 78)
    print(f"[{famille}]  dossier {rang} de {total}   ·   #{company.id}")
    print("─" * 78)
    print(f"   nom détecté      {company.nom_detecte or '(vide)'}")
    print(f"   normalisé        {company.nom_detecte_normalise or '(vide)'}")
    print(f"   sources          {', '.join(sorted(sources)) or '(aucun signal)'}")
    jours = "(aucun signal daté)" if age is None else f"{milliers(age)} jour(s)"
    print(f"   signal le + récent  {jours}")
    adresse = " · ".join(filter(None, [company.adresse, company.ville,
                                       company.region, company.code_postal]))
    print(f"   adresse au dossier  {adresse or '(rien)'}")
    fait = faits
    lu = []
    if fait is not None:
        if fait.code_complet is not None:
            lu.append(f"code complet {sorted(fait.code_complet.formes)}")
        elif fait.region_de_tri is not None:
            lu.append(f"région de tri {sorted(fait.region_de_tri.formes)}")
        if fait.ville is not None:
            lu.append(f"ville {sorted(fait.ville.formes)}")
    print(f"   adresse LUE par le départageur  {' · '.join(lu) or '(rien)'}")

    print(f"\n   LE SAC DE CHAMPS — entier, jamais filtré")
    if not champs:
        print("      (vide)")
    for cle in sorted(champs or {}):
        print(f"      {cle:<32} {_valeur_lisible(champs[cle])}")

    print(f"\n   LES CANDIDATS — {milliers(len(matches))} rendu(s) par la récupération")
    # ⚠️ **Deux statuts distincts, et les confondre fait conclure de travers.**
    # *Le premier est une propriété de l'entreprise, le second du nom qui a
    # matché* — un nom `antérieur` sur une entreprise `immatriculée` est
    # ordinaire, c'est un changement de nom.
    print("      ⚠️ DEUX STATUTS DISTINCTS : celui de l'ENTREPRISE "
          "(immatriculée / radiée,")
    print("         COD_STAT_IMMAT) et celui du NOM qui a matché "
          "(V / A, STAT_NOM).")
    if not matches:
        print("      (aucun)")
    for m in matches:
        entry = m.entry
        retenue = formes.get((entry.neq, m.forme_normalisee))
        print(f"      {m.score:>6.1f}  {entry.neq}  {(entry.nom or '')[:40]}"
              f"   [entreprise : {entry.statut}]")
        # ⚠️ **Cas 33** : la dénomination élue n'est presque jamais celle qui a
        # remporté le score. La taire ferait lire la décision sur une chaîne qui
        # n'a pas décidé.
        if retenue is not None:
            marque = "" if retenue.est_la_denomination_elue else "   ⚠️ AUTRE que l'élue"
            print(f"              forme qui a MATCHÉ : {(retenue.nom_publie or m.forme_normalisee or '')[:44]}{marque}")
            print(f"              gisement {retenue.gisement or '(inconnu)'}"
                  f" · statut DU NOM {statut_du_nom(retenue.statut)}")
        elif m.forme_normalisee:
            print(f"              forme qui a MATCHÉ : {m.forme_normalisee[:44]}   (non retrouvée au registre)")
        lieu = " · ".join(filter(None, [entry.ville, entry.code_postal]))
        print(f"              {lieu or '(pas de lieu)'}"
              f"   ·   secteur {entry.secteur_code or '—'} "
              f"{(entry.secteur_libelle or '')[:34]}")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--par-famille", type=int, default=PAR_FAMILLE_DEFAUT,
                        metavar="N", help="dossiers à rendre par famille")
    parser.add_argument("--depuis", type=int, default=0, metavar="K",
                        help="décaler le balayage — une SECONDE lecture, pas la même")
    parser.add_argument("--lentille", choices=sorted(LENTILLES), default=None,
                        help="VÉRIFIER un motif déjà vu — jamais pour en chercher un")
    parser.add_argument("--limite", type=int, default=None, help="borner (mise au point)")
    parser.add_argument("--pas", type=int, default=500, metavar="N",
                        help="cadence du témoin d'avancement du rejeu")
    args = parser.parse_args(argv)

    from sqlalchemy import select

    from falkye.db import refuser_si_cible_non_choisie

    code = refuser_si_cible_non_choisie()
    if code:
        return code

    from falkye.db import get_session
    from falkye.models.company import Company
    from falkye.models.signal import Signal
    from falkye.resolution import (
        FAMILLES,
        SEUIL_AMBIGUITE_ECART_MIN,
        SEUIL_RESOLUTION_CONFIANTE,
        famille_de,
    )
    from falkye.sources.req import formes_retenues
    from outils.departageur_adresse import champs_des_dossiers, faits_des_dossiers
    from outils.diagnostic_appariement import est_numero
    from outils.portrait_des_restants import (
        NIVEAU_CODE_COMPLET,
        NIVEAU_REGION_DE_TRI,
        finesse_de,
    )
    from outils.reresolution_neq import _resoudre_une

    print("=" * 78)
    print("DES DOSSIERS ENTIERS À LIRE — pas des comptes")
    print("=" * 78)
    print(f"""
⚠️ CE QUE CETTE SORTIE N'EST PAS

   CE N'EST PAS UNE MESURE. Une part, un pourcentage ou un rapport tiré
   d'une lecture de vingt dossiers se relirait comme une population dans
   trois semaines. AUCUN POURCENTAGE N'EST IMPRIMÉ dans les dossiers.

   CE N'EST PAS UN CLASSEMENT PAR JUGEMENT. L'outil rend ce que le dossier
   PORTE. Ce qu'on en lit vient après, et il n'en est pas l'auteur.

⚠️ RÉPARTIS, JAMAIS PRIS EN TÊTE DE TABLE

   C'est le cas 19 — un tri promu en échantillon. Les cinq cas du 19
   septembre décrivaient la TÊTE : 100 % de sociétés à numéro contre
   22,3 % dans la population. Le balayage est à PAS CONSTANT, par famille,
   sur toute la longueur de chacune.

LES LECTURES DÉJÀ FAITES — d'Alexandre, et AUCUNE n'est mesurée

   1. L'entreprise serait plus récente que l'archive (signaux ≤30 j, ×1,6).
   2. Un nom d'un seul mot ne peut pas ouvrir d'écart (239 dossiers, ×3,4).
   3. Le bon candidat ne serait pas dans le lot — jamais vérifié.
   4. Les 974 noms en lettres sans code postal seraient d'une autre nature.
   Ce sont des LECTURES, pas des prémisses : les contredire est un résultat.

   AUCUNE ÉCRITURE. Les échelles ne bougent pas : seuil {SEUIL_RESOLUTION_CONFIANTE:.0f}, écart {SEUIL_AMBIGUITE_ECART_MIN:.0f}.
""")

    session = get_session()
    try:
        requete = select(Company).where(Company.neq.is_(None)).order_by(Company.id)
        if args.limite:
            requete = requete.limit(args.limite)
        restants = list(session.execute(requete).scalars().all())
        if not restants:
            print("   Aucun restant à lire.")
            return 0

        sources: dict[int, set[str]] = defaultdict(set)
        dernier: dict[int, datetime] = {}
        for company_id, source_id, quand in session.execute(
            select(Signal.company_id, Signal.source_id, Signal.detected_at)
            .execution_options(yield_per=2000)
        ):
            sources[company_id].add(source_id)
            if quand is not None and (company_id not in dernier
                                      or quand > dernier[company_id]):
                dernier[company_id] = quand
        champs = champs_des_dossiers(session, {c.id for c in restants})
        faits = faits_des_dossiers(session, restants, champs=champs)
        maintenant = datetime.now(timezone.utc)

        def _age(company):
            quand = dernier.get(company.id)
            if quand is None:
                return None
            if quand.tzinfo is None:
                quand = quand.replace(tzinfo=timezone.utc)
            return (maintenant - quand).days

        contexte = {
            "finesse": lambda c: finesse_de(faits.get(c.id)),
            "avec_code": {NIVEAU_CODE_COMPLET, NIVEAU_REGION_DE_TRI},
            "est_numero": est_numero,
            "age": _age,
        }
        if args.lentille:
            description, garde = LENTILLES[args.lentille]
            avant = len(restants)
            restants = [c for c in restants if garde(c, contexte)]
            print(f"""⚠️ LENTILLE ACTIVE — « {args.lentille} » : {description}
   {milliers(len(restants))} dossier(s) retenus sur {milliers(avant)}.
   ⚠️ UNE LENTILLE SERT À VÉRIFIER UN MOTIF DÉJÀ VU, jamais à en chercher un.
      Employée d'abord, elle rend une lecture qui confirme ce qu'on est allé
      chercher — le cas 19 sous une autre forme.
""")
            if not restants:
                print("   Aucun dossier sous cette lentille.")
                return 0

        print(f"… rejeu de la résolution sur {milliers(len(restants))} dossier(s), "
              f"par le chemin de production", flush=True)
        par_famille: dict[str, list] = defaultdict(list)
        matches_du_dossier: dict[int, list] = {}
        for i, company in enumerate(restants, 1):
            if args.pas and i % args.pas == 0:
                print(f"   … {milliers(i)} / {milliers(len(restants))}", flush=True)
            _neq, matches = _resoudre_une(session, company)
            par_famille[famille_de(matches)].append(company)
            matches_du_dossier[company.id] = matches

        print("\n   familles : " + "  ·  ".join(
            f"{f} {milliers(len(par_famille[f]))}" for f in FAMILLES
            if par_famille.get(f)))
        print(f"   balayage à PAS CONSTANT, {args.par_famille} par famille"
              + (f", décalé de {args.depuis}" if args.depuis else ""))

        for famille in FAMILLES:
            lot = par_famille.get(famille) or []
            if not lot:
                continue
            choisis = a_pas_constant(lot, args.par_famille, args.depuis)
            print("\n" + "=" * 78)
            print(f"FAMILLE « {famille} » — {milliers(len(choisis))} dossier(s) lus "
                  f"sur {milliers(len(lot))}")
            print("=" * 78 + "\n")
            for rang, company in enumerate(choisis, 1):
                matches = matches_du_dossier[company.id]
                rendre_le_dossier(
                    company, sources.get(company.id, set()), champs.get(company.id),
                    faits.get(company.id), _age(company), matches,
                    formes_retenues(session, matches), rang, len(choisis), famille,
                )

        print("=" * 78)
        print("   RIEN N'A ÉTÉ ÉCRIT. Les échelles n'ont pas bougé.")
        print("   ⚠️ CE QUI PRÉCÈDE EST UNE LECTURE, PAS UNE MESURE. Un motif vu")
        print("   trois fois se dit « vu trois fois », jamais « fréquent ».")
        print("=" * 78)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
