#!/usr/bin/env python3
"""Les PAIRES du statut — lire avant d'en faire une règle.

## Le motif

**C'est le chemin du 19 septembre** : une mesure, puis des paires lues, puis
l'écriture. *Le statut laisse **un seul** candidat debout sur **1 710** ambigus —
mais un compte ne dit pas si le restant est la bonne entreprise.*

⚠️ **Et la réserve est la raison même de cette lecture.** *Une entreprise radiée
peut être la bonne : un signal ancien peut désigner une entreprise fermée
depuis.* **`REQEntry` ne porte AUCUNE date de radiation** — donc l'exclusion peut
garder le mauvais candidat **et rien ne le dirait.**

## ⚠️ CE QUE CETTE LECTURE NE FERA PAS — à lire avant les paires

**Poser la règle.** *Préférer un statut est une échelle, et elle se pose avec
Alexandre.* ⚠️ **Les deux formes — ne garder que les immatriculées, ou n'écarter
que les radiées — se distinguent sur 39 dossiers seulement**, et ce chiffre fait
partie de ce qu'il doit avoir en main. *Une section leur est réservée.*

**Ni juger à notre place.** *La lecture dit si le restant est PLAUSIBLE, jamais
s'il est JUSTE.*

## ⚠️ Ce que la sortie ne montrera PAS, et pourquoi c'est délibéré

**`date_maj_req`.** *C'est `DAT_MAJ_INDEX_NOM` — la mise à jour de l'index des
noms, **pas une date de radiation**.* ⚠️ **L'afficher à côté d'une radiée serait
exactement le défaut du 20 septembre** *(N192)* : **une colonne vraie posée à
côté de celle qui manque, et que le lecteur lit à sa place.** *Un lecteur ne
cherche pas la colonne absente.*

**Elle est donc NOMMÉE et non rendue** — pour qu'on ne parte pas la chercher.

## Ce que chaque paire porte

Le **nom détecté**, ses **sources**, l'**âge du signal**, l'**adresse** telle
qu'écrite et telle que le départageur la lit — puis **le candidat qui reste**
avec son statut, son lieu, son secteur, et **chacun des écartés** de même.

⚠️ **Et une indication d'adresse, calculée par `departager_ladresse`** — *la
fonction du produit, pas une règle de plus.* **Elle dit si le lieu concorde,
s'il exclut, ou s'il est inconnu d'un côté** — et `inconnu ≠ non`.

## ⚠️ Répartis, jamais pris en tête de table

**C'est le cas 19, et il est tombé deux fois cette semaine.** *Balayage à pas
constant, sur toute la longueur de chaque lot.*

⚠️ **AUCUNE ÉCRITURE. Les échelles ne bougent pas : seuil 92, écart 8.**

Usage, SUR L'HÔTE :
    python3 -m outils.paires_du_statut
    python3 -m outils.paires_du_statut --par-lot 12 --depuis 2
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone

from outils.nombres import milliers
# ⚠️ **Le balayage est EMPRUNTÉ**, jamais recopié — c'est lui qui porte le cas 19.
from outils.lecture_des_dossiers import a_pas_constant
from outils.statut_sur_les_egalites import (
    ECARTER_RADIEES,
    GARDER_IMMATRICULEES,
    IMMATRICULEE,
    LES_DEUX_EXCLUSIONS,
    RADIEE,
    ex_aequo,
)

#: Combien de paires par lot, par défaut.
PAR_LOT_DEFAUT = 8

#: ⚠️ **Nommée pour qu'on ne parte pas la chercher, et NON rendue.** *Voir N192 :
#: une colonne vraie à côté de celle qui manque se lit à sa place.*
CE_QUI_NEST_PAS_RENDU = (
    "date_maj_req — c'est DAT_MAJ_INDEX_NOM, la mise à jour de l'index des NOMS. "
    "Ce n'est PAS une date de radiation, et le miroir n'en porte aucune."
)

#: Les lots, et ils ne se lisent pas de la même façon.
EGALITE = "égalité stricte — le nom ne départage plus rien"
ECART = "écart non nul — le score désignait DÉJÀ un gagnant"
DIVERGENCE = "les deux formes DIVERGENT — c'est là que le choix se fait"
VIDE = "l'exclusion VIDE le lot — tous les candidats sont fermés"
ORDRE_DES_LOTS = (EGALITE, ECART, DIVERGENCE, VIDE)


def restants_apres(groupe, exclusion: str) -> list:
    """Les candidats que l'exclusion laisse debout."""
    if exclusion == GARDER_IMMATRICULEES:
        return [m for m in groupe if m.entry.statut == IMMATRICULEE]
    return [m for m in groupe if m.entry.statut != RADIEE]


def lot_du_dossier(groupe, est_une_egalite: bool) -> str | None:
    """Dans quel lot ce dossier se lit — **ou `None` s'il ne se lit pas ici.**

    ⚠️ *La DIVERGENCE l'emporte sur les deux autres* : un dossier où les deux
    formes ne rendent pas la même chose est d'abord un dossier de décision, et
    le ranger ailleurs le noierait.
    """
    restes = {e: restants_apres(groupe, e) for e in LES_DEUX_EXCLUSIONS}
    tailles = {e: len(r) for e, r in restes.items()}
    if tailles[GARDER_IMMATRICULEES] != tailles[ECARTER_RADIEES]:
        return DIVERGENCE
    if all(t == 0 for t in tailles.values()):
        return VIDE
    if not all(t == 1 for t in tailles.values()):
        return None
    return EGALITE if est_une_egalite else ECART


def _lieu(entry) -> str:
    morceaux = [entry.ville, entry.code_postal]
    lieu = " · ".join(m for m in morceaux if m)
    secteur = f"secteur {entry.secteur_code}" if entry.secteur_code else "secteur —"
    return f"{lieu or '(pas de lieu)'}   ·   {secteur} {(entry.secteur_libelle or '')[:28]}"


def _ligne_candidat(role: str, match, marque: str = "") -> None:
    entry = match.entry
    print(f"      {role:<10} {match.score:>6.1f}  {entry.neq}  "
          f"{(entry.nom or '')[:38]}   [{entry.statut}]{marque}")
    print(f"      {'':<10} {_lieu(entry)}")


def rendre_la_paire(company, sources, faits_du_dossier_ci, age, matches, groupe,
                    restant, ecartes, rang: int, total: int, lot: str) -> None:
    """Une paire ENTIÈRE. ⚠️ **Aucun verdict n'y est porté.**"""
    from outils.departageur_adresse import departager_ladresse, faits_du_candidat

    print("─" * 78)
    print(f"[{lot.split(' — ')[0]}]  paire {rang} de {total}   ·   #{company.id}")
    print("─" * 78)
    print(f"   nom détecté      {company.nom_detecte or '(vide)'}")
    print(f"   sources          {', '.join(sorted(sources)) or '(aucun signal)'}"
          f"   ·   signal le + récent  "
          f"{'(aucun daté)' if age is None else milliers(age) + ' jour(s)'}")
    adresse = " · ".join(filter(None, [company.adresse, company.ville,
                                       company.region, company.code_postal]))
    print(f"   adresse au dossier  {adresse or '(rien)'}")
    lu = []
    if faits_du_dossier_ci is not None:
        if faits_du_dossier_ci.code_complet is not None:
            lu.append(f"code complet {sorted(faits_du_dossier_ci.code_complet.formes)}")
        elif faits_du_dossier_ci.region_de_tri is not None:
            lu.append(f"région de tri {sorted(faits_du_dossier_ci.region_de_tri.formes)}")
        if faits_du_dossier_ci.ville is not None:
            lu.append(f"ville {sorted(faits_du_dossier_ci.ville.formes)}")
    print(f"   adresse LUE par le départageur  {' · '.join(lu) or '(rien)'}")
    second = matches[1].score if len(matches) > 1 else None
    print(f"   scores           meilleur {matches[0].score:.1f}"
          + (f"  ·  second {second:.1f}  ·  écart {matches[0].score - second:.1f}"
             if second is not None else "  ·  (un seul candidat)"))

    print()
    if restant is not None:
        _ligne_candidat("RESTE", restant)
        # ⚠️ **L'indication d'adresse vient de `departager_ladresse`** — la
        # fonction du produit, et jamais une règle de plus. Elle dit si le lieu
        # CONCORDE, s'il exclut, ou s'il est inconnu d'un côté.
        if faits_du_dossier_ci is not None:
            verdict = departager_ladresse(
                faits_du_dossier_ci, [faits_du_candidat(restant.entry)])
            niveau = f" au niveau « {verdict.niveau} »" if verdict.niveau else ""
            print(f"      {'':<10} ⚠️ le lieu : {verdict.issue}{niveau}")
    else:
        print("      RESTE      (aucun — l'exclusion a vidé le lot)")
    for m in ecartes:
        _ligne_candidat("écarté", m)
    print()


def _rendre_le_lot(lot: str, dossiers: list, combien: int, depuis: int,
                   contexte) -> None:
    if not dossiers:
        print(f"\n   Aucun dossier dans ce lot — et ce n'est pas « 0 paire ».\n")
        return
    choisis = a_pas_constant(dossiers, combien, depuis)
    print(f"\n   {milliers(len(choisis))} paire(s) lues sur {milliers(len(dossiers))}"
          f", à PAS CONSTANT\n")
    for rang, (company, matches, groupe, restant, ecartes) in enumerate(choisis, 1):
        rendre_la_paire(
            company, contexte["sources"].get(company.id, set()),
            contexte["faits"].get(company.id), contexte["age"](company),
            matches, groupe, restant, ecartes, rang, len(choisis), lot,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--par-lot", type=int, default=PAR_LOT_DEFAUT, metavar="N",
                        help="paires à rendre par lot")
    parser.add_argument("--depuis", type=int, default=0, metavar="K",
                        help="décaler le balayage — une SECONDE lecture")
    parser.add_argument("--exclusion", choices=["strict", "radiees"], default="strict",
                        help="quelle forme désigne le RESTANT dans les lots 1 et 2 "
                             "(strict = ne garder que les immatriculées)")
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
        SEUIL_AMBIGUITE_ECART_MIN,
        SEUIL_RESOLUTION_CONFIANTE,
        famille_de,
    )
    from outils.departageur_adresse import (
        champs_des_dossiers,
        concurrents_de,
        faits_des_dossiers,
    )
    from outils.reresolution_neq import _resoudre_une

    exclusion = (GARDER_IMMATRICULEES if args.exclusion == "strict"
                 else ECARTER_RADIEES)

    print("=" * 78)
    print("LES PAIRES DU STATUT — lire avant d'en faire une règle")
    print("=" * 78)
    print(f"""
⚠️ CE QUE CETTE LECTURE NE FERA PAS

   POSER LA RÈGLE. Préférer un statut est une échelle, et elle se pose avec
   Alexandre. Les deux formes — ne garder que les IMMATRICULÉES, ou
   n'écarter que les RADIÉES — se distinguent sur peu de dossiers, et un
   lot leur est réservé parce que c'est là que le choix se fait.

   NI JUGER À NOTRE PLACE. La lecture dit si le restant est PLAUSIBLE,
   jamais s'il est JUSTE.

⚠️ LA RÉSERVE QUI MOTIVE CETTE LECTURE

   UNE ENTREPRISE RADIÉE PEUT ÊTRE LA BONNE. Un signal ancien peut
   désigner une entreprise fermée depuis, et `REQEntry` ne porte AUCUNE
   date de radiation : l'exclusion peut garder le mauvais candidat, et
   rien ne le dirait.

⚠️ CE QUI N'EST PAS RENDU, ET C'EST DÉLIBÉRÉ

   {CE_QUI_NEST_PAS_RENDU}
   L'afficher à côté d'une radiée serait le défaut du 20 septembre : une
   colonne vraie posée à côté de celle qui manque, et lue à sa place.

   Forme retenue pour désigner le RESTANT : « {exclusion} » (--exclusion).
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
            print("   RIEN N'A ÉTÉ ÉCRIT. Les échelles n'ont pas bougé.")
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

        print(f"… rejeu de la résolution sur {milliers(len(restants))} restants, "
              f"par le chemin de production", flush=True)
        lots: dict[str, list] = {nom: [] for nom in ORDRE_DES_LOTS}
        n_amb = 0
        for i, company in enumerate(restants, 1):
            if args.pas and i % args.pas == 0:
                print(f"   … {milliers(i)} / {milliers(len(restants))}", flush=True)
            _neq, matches = _resoudre_une(session, company)
            if famille_de(matches) != "ambigu":
                continue
            n_amb += 1
            groupe = concurrents_de(matches)
            egalite = len(ex_aequo(matches)) >= 2
            lot = lot_du_dossier(groupe, egalite)
            if lot is None:
                continue
            restes = restants_apres(groupe, exclusion)
            restant = restes[0] if len(restes) == 1 else None
            gardes = {id(m) for m in restes}
            ecartes = [m for m in groupe if id(m) not in gardes]
            lots[lot].append((company, matches, groupe, restant, ecartes))

        print(f"\n   AMBIGUS : {milliers(n_amb)}")
        print(f"   {'lot':<52} {'dossiers':>9}")
        for nom in ORDRE_DES_LOTS:
            print(f"   {nom:<52} {milliers(len(lots[nom])):>9}")
        print("""
   ⚠️ LA DIVERGENCE L'EMPORTE sur les deux premiers lots. Un dossier où les
      deux formes ne rendent pas la même chose est d'abord un dossier de
      DÉCISION, et le ranger ailleurs le noierait.
""")

        contexte = {"sources": sources, "faits": faits, "age": _age}
        for nom in ORDRE_DES_LOTS:
            print("=" * 78)
            print(nom.upper())
            print("=" * 78)
            if nom == ECART:
                print("\n   ⚠️ ICI LE SCORE DÉSIGNAIT DÉJÀ UN GAGNANT. Si l'exclusion")
                print("      garde un AUTRE candidat que le mieux scoré, c'est le cas")
                print("      le plus lourd de la lecture — et il se lit une paire à la")
                print("      fois, jamais dans un compte.")
            if nom == VIDE:
                print("\n   ⚠️ UN LOT VIDÉ N'EST PAS UN DÉPARTAGE MANQUÉ. C'est un")
                print("      dossier dont TOUS les candidats sont des entreprises")
                print("      fermées — et ça se lit autrement : soit l'entreprise a")
                print("      changé de NEQ, soit elle n'est pas dans ce lot du tout.")
            _rendre_le_lot(nom, lots[nom], args.par_lot, args.depuis, contexte)

        print("=" * 78)
        print("   RIEN N'A ÉTÉ ÉCRIT. Les échelles n'ont pas bougé.")
        print("   ⚠️ CETTE LECTURE DIT SI LE RESTANT EST PLAUSIBLE, JAMAIS S'IL EST")
        print("   JUSTE. Une radiée peut être la bonne, et le miroir ne porte aucune")
        print("   date de radiation pour en juger.")
        print("=" * 78)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
