#!/usr/bin/env python3
"""Que rendraient trois corrections, simulées — et elles ne sont pas de même nature.

**Le cas qui a ouvert la question** *(2026-09-17)*. Un dossier classé « trop
faible » échouait de **deux points** :

    détecté  : '11888935 canada inc workstaff'
    registre : '11888935 canada inc'          → 90.00
    seuil    : 92   →  ⛔ TROP FAIBLE

⚠️ **UN CAS, PAS UNE PROPORTION.** Cet outil existe pour donner la proportion —
et la première version, le 2026-09-17, a rendu deux chiffres qu'Alexandre a
refusés. **Les deux refus sont la raison d'être de cette version.**

## Ce que la première version a raté, et qui est corrigé ici

**1. Elle recopiait le scoreur du moteur au lieu de l'emprunter.** La seconde
passe rescorait à la main, `fuzz.WRatio` contre la seule dénomination sociale
élue, *sans les autres noms du NEQ et sans le bonus de ville*. Le moteur, lui,
prend **le meilleur des noms de chaque NEQ** (`req_noms` compris) et **ajoute
cinq points quand la ville concorde**. La copie rendait donc des scores plus bas
partout — et faisait passer **un défaut d'instrument pour une perte de la
correction** (-338 RETENU). *C'est le cas 41, dans mon propre outil, contre une
règle écrite dans la docstring que je recopiais.*

**2. Elle comptait le gain d'un seuil abaissé sans dire où allaient les autres.**
1 623 dossiers ont un meilleur score dans `[90 – 91[`, et l'abaissement à 90 n'en
rendait que 79 « récupérés ». *Les 1 544 restants franchissaient bien le seuil —
et tombaient dans l'AMBIGU, retenus par la SECONDE échelle.* Un chiffrage qui
n'affiche que le gain laisse croire qu'ils n'existent pas. **Ici, toute masse qui
franchit le seuil simulé est suivie jusqu'à sa destination.**

## Les trois corrections, et leurs deux natures

**(a) Retirer le contenu entre parenthèses** est une **correction de données**.
⚠️ *Et elle n'est pas gratuite pour autant* : retirer la parenthèse change le
premier mot du nom détecté, donc le **préfixe**, donc **quelles lignes la
récupération rend**. Elle DÉPLACE la récupération autant qu'elle rapproche les
chaînes. Cet outil rend les deux effets séparément.

**(b) Abaisser le seuil** (92) et **(c) abaisser l'écart minimal** (8) sont des
**changements d'échelle**. *Ils récupèrent du VRAI ET du FAUX.*

⚠️ **L'ÉCART EST PLUS DANGEREUX QUE LE SEUIL, PAS MOINS.** *Le seuil dit « le
candidat ressemble assez »; l'écart dit « le second ne ressemble pas trop ».*
L'abaisser, c'est accepter de trancher entre deux candidats proches — exactement
la situation des 26 organisations publiques à 95-100 sur le NEQ `8879690699`.
**Le chiffrage de (c) rend donc le faux AVANT le gain.**

⚠️ **NI LE SEUIL DE 92 NI L'ÉCART DE 8 NE BOUGENT ICI.** *Ce sont deux échelles
existantes, et elles se changent avec Alexandre, jamais dans une demande de
mesure.* Un raisonnement donne l'axe; **seul un incident donne le seuil**.
**Aucune règle n'est modifiée, aucune écriture n'a lieu.**

Usage, SUR L'HÔTE :
    sudo -u falkye bash -c 'set -a; . /etc/falkye/falkye.env; set +a; \
        cd /opt/falkye/code && \
        /opt/falkye/venv/bin/python -m outils.chiffrage_corrections'
"""
from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from dataclasses import dataclass

from outils.nombres import milliers

#: Le contenu entre parenthèses, avec les parenthèses. *Non gourmand, pour que
#: deux groupes sur la même ligne soient deux retraits et non un seul qui
#: avalerait ce qui les sépare.*
PARENTHESES = re.compile(r"\s*\([^)]*\)")

#: Les paliers de l'histogramme des scores. **Resserrés près du seuil** : c'est
#: là que la question se joue — *« manquer de deux points » et « manquer de
#: cinquante » ne s'appellent pas le même défaut.*
PALIERS = (0, 40, 60, 75, 85, 88, 90, 91, 92)

#: Les écarts minimaux à simuler. **8 est la valeur en vigueur** : elle ouvre
#: l'échelle pour que le tableau se lise comme un déplacement, jamais comme un
#: choix déjà fait.
ECARTS_SIMULES = (8.0, 6.0, 4.0, 2.0, 0.0)

#: Au-delà de deux dossiers sur un même NEQ, on ne tranche plus par ancienneté —
#: c'est la forme de faux mesurée le 2026-09-16 (26 organisations publiques
#: distinctes convergeant sur `8879690699` à 95-100).
PRETENDANTS_MAX = 2


@dataclass
class Releve:
    """Un dossier, vu une fois par la VRAIE règle. *Un relevé par dossier, pas
    un compteur : une simulation qui n'aurait que des compteurs ne pourrait plus
    dire OÙ va la masse qu'elle déplace.*"""

    id: int
    nom: str
    prefixe: str
    parenthese: bool
    famille: str
    top: float
    second: float
    neq_top: str | None
    neq_second: str | None


def _sans_parentheses(nom: str | None) -> str:
    return PARENTHESES.sub("", nom or "").strip()


def _palier(score: float) -> str:
    for bas, haut in zip(PALIERS, PALIERS[1:]):
        if bas <= score < haut:
            return f"[{bas:>3} – {haut:>3}["
    return f"[{PALIERS[-1]:>3} et + ["


def _part(k: int, n: int) -> str:
    return f"{100 * k / n:.1f} %" if n else "—"


def _groupes_multiples(neqs: list[str | None]) -> tuple[int, int]:
    """Les NEQ visés par PLUS DE DEUX dossiers, et les dossiers qu'ils portent.
    *La seule forme de faux qu'on ait vue de près.*"""
    par_neq: Counter = Counter(n for n in neqs if n)
    gros = {neq: k for neq, k in par_neq.items() if k > PRETENDANTS_MAX}
    return len(gros), sum(gros.values())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--seuil-simule", type=float, default=90.0,
                        help="le seuil abaissé à simuler (défaut 90)")
    parser.add_argument("--limite", type=int, default=None, help="borner (mise au point)")
    parser.add_argument("--sans-simulation-parentheses", action="store_true",
                        help="sauter la seconde passe (coûteuse)")
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
    from falkye.sources.column_mapping import normaliser

    print("=" * 78)
    print("CHIFFRAGE DE TROIS CORRECTIONS — simulées, aucune appliquée")
    print("=" * 78)

    # ---- CE QUE LA MESURE NE DIRA PAS, AVANT LES CHIFFRES --------------------
    print(f"""
⚠️ CE QUE CETTE MESURE NE DIRA PAS — à lire avant tout chiffre

   Une correction SIMULÉE dit ce que la règle rendrait sur la population
   D'AUJOURD'HUI, jamais ce qu'elle rendrait en production.

   En production, d'autres chemins écrivent — et un appariement réussi
   CRÉE UN DOSSIER NEUF au lieu de réparer celui qui échoue
   (`falkye/resolution.py::resolve_company`). Un gain simulé ici ne se
   transforme donc PAS en dossiers résolus là-bas sans la passe de reprise.

   Elle ne dit pas non plus si un appariement récupéré est JUSTE. Elle compte
   des franchissements de règle, pas des entreprises correctement identifiées.
   *La seule forme de faux qu'elle sache compter est la convergence : plusieurs
   dossiers distincts sur un même NEQ.* D'autres formes existent et ne sont pas
   mesurées ici.

   ⚠️ Et les DEUX échelles ne bougent pas : seuil {SEUIL_RESOLUTION_CONFIANTE:.0f},
   écart minimal {SEUIL_AMBIGUITE_ECART_MIN:.0f}. Elles se changent avec Alexandre,
   jamais dans une demande de mesure. Aucune règle n'est modifiée ici, aucune
   écriture n'a lieu.

   UNITÉ : des DOSSIERS, jamais des formes normalisées.
""")

    session = get_session()
    try:
        requete = select(Company).where(Company.neq.is_(None)).order_by(Company.id)
        if args.limite:
            requete = requete.limit(args.limite)
        orphelins = list(session.execute(requete).scalars().all())
        total = len(orphelins)
        print(f"   dossiers sans NEQ : {milliers(total)}\n")

        # ---- PASSE 1 : la VRAIE règle, empruntée et non recopiée -------------
        releves: list[Releve] = []
        for i, company in enumerate(orphelins):
            if i and i % 1000 == 0:
                print(f"   … passe 1 : {milliers(i)} examinés", flush=True)
            matches = req_source.resolve_neq_by_name(
                session, company.nom_detecte, ville=company.ville
            )
            nom_norm = normaliser(company.nom_detecte or "")
            releves.append(Releve(
                id=company.id,
                nom=company.nom_detecte or "",
                prefixe=nom_norm.split(" ")[0] if nom_norm else "",
                parenthese="(" in (company.nom_detecte or ""),
                famille=famille_de(matches),
                top=matches[0].score if matches else 0.0,
                second=matches[1].score if len(matches) > 1 else 0.0,
                neq_top=matches[0].entry.neq if matches else None,
                neq_second=matches[1].entry.neq if len(matches) > 1 else None,
            ))

        familles: Counter = Counter(r.famille for r in releves)
        par_id = {r.id: r for r in releves}

        # ---- 1. LES PARENTHÈSES ---------------------------------------------
        print("\n" + "-" * 78)
        print("1. LES DOSSIERS PORTANT UNE PARENTHÈSE, PAR FAMILLE")
        print("-" * 78)
        avec_parenthese = sum(1 for r in releves if r.parenthese)
        familles_par: Counter = Counter(r.famille for r in releves if r.parenthese)
        print(f"\n   avec une parenthèse : {milliers(avec_parenthese)} dossier(s) "
              f"sur {milliers(total)}\n")
        print(f"   {'famille':<18} {'total':>9} {'dont ( )':>10} {'part':>8}")
        for f in FAMILLES:
            n, k = familles.get(f, 0), familles_par.get(f, 0)
            print(f"   {f:<18} {milliers(n):>9} {milliers(k):>10} {_part(k, n):>8}")
        print("\n   ⚠️ Ce tableau donne le PLAFOND de la correction (a) : elle ne peut")
        print("      rien pour un dossier qui ne porte pas de parenthèse.")

        # ---- 2. LA DISTRIBUTION DES TROP FAIBLES ----------------------------
        print("\n" + "-" * 78)
        print("2. LES « TROP FAIBLES » — manquent-ils de PEU ou de LOIN?")
        print("-" * 78)
        scores_tf = [r.top for r in releves if r.famille == "trop faible"]
        n_tf = len(scores_tf)
        histo: Counter = Counter(_palier(s) for s in scores_tf)
        print()
        for palier in sorted(histo):
            k = histo[palier]
            barre = "█" * max(1, round(40 * k / max(1, n_tf)))
            print(f"   {palier}  {milliers(k):>8}  {barre}")
        if n_tf:
            proches = sum(1 for s in scores_tf if s >= 88)
            print(f"\n   à MOINS DE 4 POINTS du seuil (≥ 88) : {milliers(proches)}"
                  f"  ({_part(proches, n_tf)} des trop faibles)")
        print("\n   ⚠️ Un score proche du seuil ne dit PAS que l'appariement est juste.")
        print("      Il dit que le mur n'est pas l'absence du bon candidat.")

        # ---- 3b. LE SEUIL ABAISSÉ — la DESTINATION, pas le seul gain ---------
        seuil_sim = args.seuil_simule
        print("\n" + "-" * 78)
        print(f"3b. SEUIL ABAISSÉ À {seuil_sim:.0f} — un CHANGEMENT D'ÉCHELLE")
        print("    où va la masse qui le franchit?")
        print("-" * 78)
        print("\n   ⚠️ La question n'est pas « combien franchissent », c'est « combien")
        print("      DEVIENNENT RETENUS ». Les deux ne sont pas le même chiffre :")
        print(f"      l'écart minimal de {SEUIL_AMBIGUITE_ECART_MIN:.0f} points retient")
        print("      une part de ceux qui franchissent, et les verse dans AMBIGU.\n")

        franchissent = [
            r for r in releves
            if r.famille != "RETENU" and r.top >= seuil_sim
        ]
        destinations: Counter = Counter(
            famille_de(
                _faux_matches(r),
                seuil=seuil_sim,
                ecart_min=SEUIL_AMBIGUITE_ECART_MIN,
            )
            for r in franchissent
        )
        print(f"   dossiers non RETENUS dont le meilleur score ≥ {seuil_sim:.0f} : "
              f"{milliers(len(franchissent))}\n")
        print(f"   {'destination au seuil simulé':<32} {'dossiers':>10} {'part':>8}")
        for f in FAMILLES:
            k = destinations.get(f, 0)
            print(f"   {f:<32} {milliers(k):>10} {_part(k, len(franchissent)):>8}")

        # La ventilation par palier : c'est la bande [90 – 91[ qui a ouvert la
        # question, et une bande isolée se lit mieux qu'une moyenne.
        print(f"\n   Par palier, entre {seuil_sim:.0f} et "
              f"{SEUIL_RESOLUTION_CONFIANTE:.0f} :\n")
        print(f"   {'palier':<14} {'dossiers':>9} {'→ RETENU':>10} {'→ ambigu':>10}")
        bandes: dict[str, list[Releve]] = defaultdict(list)
        for r in franchissent:
            if r.top < SEUIL_RESOLUTION_CONFIANTE:
                bandes[_palier(r.top)].append(r)
        for palier in sorted(bandes):
            lot = bandes[palier]
            d: Counter = Counter(
                famille_de(_faux_matches(r), seuil=seuil_sim,
                           ecart_min=SEUIL_AMBIGUITE_ECART_MIN)
                for r in lot
            )
            print(f"   {palier:<14} {milliers(len(lot)):>9} "
                  f"{milliers(d.get('RETENU', 0)):>10} "
                  f"{milliers(d.get('ambigu', 0)):>10}")

        gagnes = [
            r for r in franchissent
            if famille_de(_faux_matches(r), seuil=seuil_sim,
                          ecart_min=SEUIL_AMBIGUITE_ECART_MIN) == "RETENU"
        ]
        n_multi, n_dans_multi = _groupes_multiples(
            [r.neq_top for r in releves if r.famille == "RETENU"] +
            [r.neq_top for r in gagnes]
        )
        print(f"\n   CE QU'IL RÉCUPÈRE      : {milliers(len(gagnes))} dossier(s) de plus")
        print("   CE QU'IL LAISSE PASSER :")
        print(f"      NEQ visés par PLUS DE {PRETENDANTS_MAX} dossiers : {milliers(n_multi)}")
        print(f"      dossiers dans ces groupes            : {milliers(n_dans_multi)}")
        print(f"\n   ⚠️ {milliers(len(franchissent) - len(gagnes))} dossier(s) franchissent")
        print("      le seuil simulé SANS devenir RETENUS. Ce n'est pas le seuil qui")
        print("      les retient — c'est l'ÉCART, et c'est l'objet de 3c.")

        # ---- 3c. L'ÉCART ABAISSÉ — le FAUX d'abord --------------------------
        print("\n" + "-" * 78)
        print(f"3c. ÉCART MINIMAL ABAISSÉ (en vigueur : "
              f"{SEUIL_AMBIGUITE_ECART_MIN:.0f}) — un CHANGEMENT D'ÉCHELLE")
        print("    seuil INCHANGÉ")
        print("-" * 78)
        print("""
   ⚠️ CETTE ÉCHELLE EST PLUS DANGEREUSE QUE LE SEUIL, PAS MOINS.

      Le seuil dit « le candidat ressemble assez ». L'écart dit « le SECOND ne
      ressemble pas trop ». L'abaisser, c'est accepter de trancher entre deux
      candidats proches — la situation exacte des 26 organisations publiques
      distinctes à 95-100 sur le NEQ 8879690699.

      Le faux est donc rendu AVANT le gain.
""")
        retenus_actuels = [r for r in releves if r.famille == "RETENU"]
        print(f"   {'écart':>6} │ {'FAUX : NEQ > ' + str(PRETENDANTS_MAX):>18} "
              f"{'dossiers dedans':>16} {'2e NEQ à moins de':>18} │ {'gain':>8}")
        print("   " + "─" * 74)
        for ecart in ECARTS_SIMULES:
            neufs = [
                r for r in releves
                if r.famille != "RETENU"
                and famille_de(_faux_matches(r), seuil=SEUIL_RESOLUTION_CONFIANTE,
                               ecart_min=ecart) == "RETENU"
            ]
            n_m, n_d = _groupes_multiples(
                [r.neq_top for r in retenus_actuels] + [r.neq_top for r in neufs]
            )
            # Le faux PROPRE à l'écart : un second candidat qui est une AUTRE
            # entité, à portée de l'écart abaissé. *Chaque dossier de cette
            # colonne est une décision entre deux entreprises différentes.*
            serres = sum(
                1 for r in neufs
                if r.neq_second and r.neq_second != r.neq_top
                and (r.top - r.second) < SEUIL_AMBIGUITE_ECART_MIN
            )
            # ⚠️ TÉMOIN. À l'écart en vigueur, la simulation rejoue la règle
            # actuelle : le gain DOIT être nul. *Un gain non nul sur cette ligne
            # dirait que la simulation et le moteur ne classent pas pareil, et
            # tout le reste du tableau serait à jeter.*
            marque = ("  ← en vigueur — TÉMOIN, le gain doit être 0"
                      if ecart == SEUIL_AMBIGUITE_ECART_MIN else "")
            print(f"   {ecart:>6.0f} │ {milliers(n_m):>18} {milliers(n_d):>16} "
                  f"{milliers(serres):>18} │ {milliers(len(neufs)):>8}{marque}")
        print("\n   « 2e NEQ à moins de » : des dossiers où le second candidat est une")
        print(f"   AUTRE entité à moins de {SEUIL_AMBIGUITE_ECART_MIN:.0f} points du premier.")
        print("   ⚠️ Chacun est une décision entre deux entreprises différentes, prise")
        print("      par la machine. C'est ce que l'écart de 8 refuse aujourd'hui.")

        # ---- Les deux échelles ensemble -------------------------------------
        print("\n   Les deux échelles ensemble — gain seulement :\n")
        print(f"   {'':>8}" + "".join(f"{'écart ' + f'{e:.0f}':>12}" for e in ECARTS_SIMULES))
        for seuil in (SEUIL_RESOLUTION_CONFIANTE, 91.0, 90.0, 88.0):
            ligne = f"   seuil {seuil:>2.0f}"
            for ecart in ECARTS_SIMULES:
                n = sum(
                    1 for r in releves
                    if r.famille != "RETENU"
                    and famille_de(_faux_matches(r), seuil=seuil, ecart_min=ecart) == "RETENU"
                )
                ligne += f"{milliers(n):>12}"
            print(ligne)
        print("\n   ⚠️ Ce tableau ne rend QUE le gain, et deux changements d'échelle")
        print("      ensemble ne s'additionnent pas — ils se multiplient, parce que")
        print("      chacun retire une garde que l'autre ne remplace pas. La colonne")
        print("      du faux ci-dessus reste la lecture qui compte.")

        # ---- 3a. LES PARENTHÈSES RETIRÉES — seconde passe --------------------
        print("\n" + "-" * 78)
        print("3a. PARENTHÈSES RETIRÉES DES DEUX CÔTÉS — une CORRECTION DE DONNÉES")
        print("-" * 78)
        if args.sans_simulation_parentheses:
            print("\n   SAUTÉE (--sans-simulation-parentheses). ⚠️ Sautée n'est pas nulle.")
            return 0
        print("""
   ⚠️ DEUX EFFETS, ET ILS NE VONT PAS DANS LE MÊME SENS.

      Côté DÉTECTÉ, retirer la parenthèse change le premier mot, donc le
      PRÉFIXE, donc QUELLES LIGNES la récupération rend. Elle DÉPLACE la
      récupération autant qu'elle rapproche les chaînes — et un déplacement
      peut PERDRE un appariement qui marchait.

      Côté REGISTRE, le retrait ne change que les SCORES : la récupération
      cherche le préfixe du nom DÉTECTÉ dans la colonne stockée, et la
      simulation ne réécrit pas cette colonne. *Une correction appliquée à
      l'import, elle, la réécrirait — et changerait alors la récupération des
      deux côtés. Ce n'est pas ce qui est simulé ici.*

      ⚠️ Et le retrait côté registre se fait sur les noms PUBLIÉS, pas sur la
      colonne normalisée : `normaliser` remplace déjà la ponctuation par des
      espaces, donc « Canada inc. (Workstaff) » y est « canada inc workstaff ».
      *Les parenthèses ont disparu comme caractères et leur contenu est resté
      comme mot.* Simuler le retrait sur la colonne normalisée aurait rendu un
      no-op déguisé en mesure.
""")
        apres: dict[int, str] = {}
        prefixe_change = 0
        for i, company in enumerate(orphelins):
            if i and i % 1000 == 0:
                print(f"   … passe 2 : {milliers(i)} examinés", flush=True)
            nom_propre = _sans_parentheses(company.nom_detecte)
            if not nom_propre:
                apres[company.id] = "aucun candidat"
                continue
            nom_norm = normaliser(nom_propre)
            if nom_norm.split(" ")[0] != par_id[company.id].prefixe:
                prefixe_change += 1
            # ⚠️ Le scoreur du MOTEUR, emprunté. `transformer_forme` retire la
            # parenthèse côté registre À L'INTÉRIEUR du moteur — donc sur TOUS
            # les noms du NEQ (`req_noms` compris), avec le regroupement par NEQ
            # et le bonus de ville. *Rescorer à la main contre la seule
            # dénomination sociale élue, sans bonus, était le défaut de la
            # version du 2026-09-17.*
            matches = req_source.resolve_neq_by_name(
                session, nom_propre, ville=company.ville,
                transformer_forme=_sans_parentheses,
            )
            apres[company.id] = famille_de(matches)

        familles_apres: Counter = Counter(apres.values())
        print(f"\n   {'famille':<18} {'avant':>9} {'après':>9} {'écart':>9}")
        for f in FAMILLES:
            a, b = familles.get(f, 0), familles_apres.get(f, 0)
            print(f"   {f:<18} {milliers(a):>9} {milliers(b):>9} {b - a:>+9}")

        # ---- Le diagnostic des PERTES : d'où vient un dossier perdu? ---------
        perdus = [r for r in releves if r.famille == "RETENU" and apres[r.id] != "RETENU"]
        gagnes_par = [r for r in releves if r.famille != "RETENU" and apres[r.id] == "RETENU"]
        print(f"\n   RETENUS perdus : {milliers(len(perdus))}   "
              f"| RETENUS gagnés : {milliers(len(gagnes_par))}")
        perdus_avec = sum(1 for r in perdus if r.parenthese)
        print(f"\n   {'les perdus, ventilés':<44} {'dossiers':>10}")
        print(f"   {'parenthèse DANS LE NOM DÉTECTÉ':<44} {milliers(perdus_avec):>10}")
        print(f"   {'AUCUNE parenthèse dans le nom détecté':<44} "
              f"{milliers(len(perdus) - perdus_avec):>10}")
        print(f"\n   dossiers dont le PRÉFIXE change : {milliers(prefixe_change)}")
        print("""
   ⚠️ COMMENT SE LIT CETTE VENTILATION

      Un dossier SANS parenthèse dans le nom détecté reçoit exactement la même
      chaîne aux deux passes : même préfixe, mêmes lignes récupérées. S'il
      change de famille, la cause est le retrait CÔTÉ REGISTRE, et rien d'autre.

      Un dossier AVEC parenthèse peut changer pour l'une ou l'autre raison, et
      la ligne « préfixe change » dit combien ont vu leur récupération se
      déplacer.

      *Si les perdus se concentrent chez ceux qui portent une parenthèse, la
      perte est un MÉCANISME et non un défaut : la correction déplace la
      récupération. Si elle se concentre chez ceux qui n'en portent pas,
      l'instrument est en cause et le chiffre ne vaut rien.*
""")
        if perdus:
            print("   quelques perdus, pour les regarder :\n")
            for r in perdus[:5]:
                print(f"      [{'( )' if r.parenthese else '   '}] {r.nom[:52]:<52}"
                      f"  {r.top:>6.2f} → {apres[r.id]}")
        return 0
    finally:
        session.close()


@dataclass
class _FauxMatch:
    """Le strict nécessaire pour rejouer la DÉCISION sur un relevé : un score et
    un NEQ. *On rejoue la règle du moteur sur des scores déjà mesurés — on ne
    rejoue pas le scoreur, qui lui n'est jamais recopié.*"""

    entry: object
    score: float


@dataclass
class _FauxEntry:
    neq: str | None


def _faux_matches(r: "Releve") -> list:
    """Reconstitue la liste de candidats telle que la règle la voit : le premier,
    et le second quand il existe. **Deux éléments suffisent** — `neq_retenu` ne
    regarde que ceux-là."""
    if r.neq_top is None:
        return []
    matches = [_FauxMatch(entry=_FauxEntry(neq=r.neq_top), score=r.top)]
    if r.neq_second is not None:
        matches.append(_FauxMatch(entry=_FauxEntry(neq=r.neq_second), score=r.second))
    return matches


if __name__ == "__main__":
    raise SystemExit(main())
