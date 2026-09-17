#!/usr/bin/env python3
"""Que rendraient deux corrections, simulées — et elles ne sont pas de même nature.

**Le cas qui a ouvert la question** *(2026-09-17)*. Un dossier classé « trop
faible » échouait de **deux points** :

    détecté  : '11888935 canada inc workstaff'
    registre : '11888935 canada inc'          → 90.00
    seuil    : 92   →  ⛔ TROP FAIBLE

*La récupération était parfaite* — préfixe numérique, une ligne rendue, borne non
atteinte, bon candidat présenté au scoreur. **Le mur était dans le score**, et la
cause était `(Workstaff)` : un nom commercial entre parenthèses qui survit à la
normalisation, ajoute un mot, et fait tomber un appariement qui serait à 100 sans
lui.

⚠️ **UN CAS, PAS UNE PROPORTION.** Cet outil existe pour donner la proportion.

## ⚠️ Les deux corrections ne sont PAS de même nature

**(a) Retirer le contenu entre parenthèses** est une **correction de données**.
*Elle ne peut que rapprocher des chaînes qui désignent la même entreprise* — un
nom commercial entre parenthèses n'est pas une autre entité.

**(b) Abaisser le seuil** est un **changement d'échelle**. *Il récupère du VRAI
ET du FAUX*, et un chiffrage qui ne compterait que le gain ferait paraître
l'abaissement gratuit. **On sait à quoi ressemble le faux** : le NEQ
`8879690699` attirait 26 organisations publiques distinctes à 95-100.

**Donc (b) rend DEUX chiffres** : ce qu'il récupère, et ce qu'il laisse passer —
mesuré par les prétendants multiples, la seule forme de faux qu'on ait vue de
près.

⚠️ **LE SEUIL DE 92 NE BOUGE PAS ICI.** *C'est une échelle existante, et elle se
change avec Alexandre, jamais dans une demande de mesure.* Un raisonnement donne
l'axe; **seul un incident donne le seuil** — et un cas unique n'est pas encore un
incident. **Aucune règle n'est modifiée, aucune écriture n'a lieu.**

## Le coût

**Deux passes** sur la population sans NEQ. La seconde est le prix de la
simulation (a) : *retirer la parenthèse change aussi le PRÉFIXE, donc la
récupération* — la simuler sans rejouer la récupération mesurerait autre chose.

Usage, SUR L'HÔTE :
    sudo -u falkye bash -c 'set -a; . /etc/falkye/falkye.env; set +a; \
        cd /opt/falkye/code && \
        /opt/falkye/venv/bin/python -m outils.chiffrage_corrections'
"""
from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict

from outils.nombres import milliers

#: Le contenu entre parenthèses, avec les parenthèses. *Non gourmand, pour que
#: deux groupes sur la même ligne soient deux retraits et non un seul qui
#: avalerait ce qui les sépare.*
PARENTHESES = re.compile(r"\s*\([^)]*\)")

#: Les paliers du histogramme des scores. **Resserrés près du seuil** : c'est là
#: que la question se joue — *« manquer de deux points » et « manquer de
#: cinquante » ne s'appellent pas le même défaut.*
PALIERS = (0, 40, 60, 75, 85, 88, 90, 91, 92)


def _sans_parentheses(nom: str | None) -> str:
    return PARENTHESES.sub("", nom or "").strip()


def _palier(score: float) -> str:
    for bas, haut in zip(PALIERS, PALIERS[1:]):
        if bas <= score < haut:
            return f"[{bas:>3} – {haut:>3}["
    return f"[{PALIERS[-1]:>3} et + ["


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

    from rapidfuzz import fuzz

    from falkye.db import get_session
    from falkye.models.company import Company
    from falkye.resolution import (
        SEUIL_AMBIGUITE_ECART_MIN,
        SEUIL_RESOLUTION_CONFIANTE,
        neq_retenu,
    )
    from falkye.sources import req as req_source
    from falkye.sources.column_mapping import normaliser

    print("=" * 78)
    print("CHIFFRAGE DE DEUX CORRECTIONS — simulées, aucune appliquée")
    print("=" * 78)

    # ---- CE QUE LA MESURE NE DIRA PAS, AVANT LES CHIFFRES --------------------
    print("""
⚠️ CE QUE CETTE MESURE NE DIRA PAS — à lire avant tout chiffre

   Une correction SIMULÉE dit ce que la règle rendrait sur la population
   D'AUJOURD'HUI, jamais ce qu'elle rendrait en production.

   En production, d'autres chemins écrivent — et un appariement réussi
   CRÉE UN DOSSIER NEUF au lieu de réparer celui qui échoue
   (`falkye/resolution.py::resolve_company`). Un gain simulé ici ne se
   transforme donc PAS en dossiers résolus là-bas sans la passe de reprise.

   ⚠️ Et le seuil de 92 NE BOUGE PAS. C'est une échelle existante : elle se
   change avec Alexandre, jamais dans une demande de mesure. Aucune règle
   n'est modifiée ici, aucune écriture n'a lieu.

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

        familles: Counter = Counter()
        familles_parenthese: Counter = Counter()
        avec_parenthese = 0
        scores_trop_faibles: list[float] = []
        # Pour la simulation du seuil : (top, second, neq_du_top) par dossier
        releves: list[tuple[float, float, str]] = []

        for i, company in enumerate(orphelins):
            if i and i % 1000 == 0:
                print(f"   … passe 1 : {milliers(i)} examinés", flush=True)
            a_parenthese = "(" in (company.nom_detecte or "")
            avec_parenthese += 1 if a_parenthese else 0
            matches = req_source.resolve_neq_by_name(
                session, company.nom_detecte, ville=company.ville
            )
            decide = neq_retenu(matches)
            if decide is not None:
                f = "RETENU"
            elif not matches:
                f = "aucun candidat"
            elif matches[0].score < SEUIL_RESOLUTION_CONFIANTE:
                f = "trop faible"
                scores_trop_faibles.append(matches[0].score)
            else:
                f = "ambigu"
            familles[f] += 1
            if a_parenthese:
                familles_parenthese[f] += 1
            if matches:
                releves.append((
                    matches[0].score,
                    matches[1].score if len(matches) > 1 else 0.0,
                    matches[0].entry.neq,
                ))

        # ---- 1. LES PARENTHÈSES ---------------------------------------------
        print("\n" + "-" * 78)
        print("1. LES DOSSIERS PORTANT UNE PARENTHÈSE, PAR FAMILLE")
        print("-" * 78)
        print(f"\n   avec une parenthèse : {milliers(avec_parenthese)} dossier(s) "
              f"sur {milliers(total)}\n")
        print(f"   {'famille':<18} {'total':>9} {'dont ( )':>10} {'part':>8}")
        for f in ("RETENU", "ambigu", "trop faible", "aucun candidat"):
            n, k = familles.get(f, 0), familles_parenthese.get(f, 0)
            part = f"{100 * k / n:.1f} %" if n else "—"
            print(f"   {f:<18} {milliers(n):>9} {milliers(k):>10} {part:>8}")

        # ---- 2. LA DISTRIBUTION DES TROP FAIBLES ----------------------------
        print("\n" + "-" * 78)
        print("2. LES « TROP FAIBLES » — manquent-ils de PEU ou de LOIN?")
        print("-" * 78)
        print("\n   C'est le renversement du rejeu du 16, où trois dossiers à 45, 38")
        print("   et 25 manquaient de loin. *Si la masse est à 88-91, la cause est")
        print("   une de plus du même genre; si elle est à 40, c'est autre chose.*\n")
        histo: Counter = Counter(_palier(s) for s in scores_trop_faibles)
        n_tf = len(scores_trop_faibles)
        for palier in sorted(histo, key=lambda p: PALIERS[0] if not p else p):
            k = histo[palier]
            barre = "█" * max(1, round(40 * k / max(1, n_tf)))
            print(f"   {palier}  {milliers(k):>8}  {barre}")
        if n_tf:
            proches = sum(1 for s in scores_trop_faibles if s >= 88)
            print(f"\n   à MOINS DE 4 POINTS du seuil (≥ 88) : {milliers(proches)}"
                  f"  ({100 * proches / n_tf:.1f} % des trop faibles)")

        # ---- 3b. LE SEUIL ABAISSÉ — les deux chiffres -----------------------
        print("\n" + "-" * 78)
        print(f"3b. SEUIL ABAISSÉ À {args.seuil_simule:.0f} — un CHANGEMENT D'ÉCHELLE")
        print("-" * 78)
        gagnes = 0
        par_neq_simule: dict[str, int] = defaultdict(int)
        for top, second, neq in releves:
            assez_sur = top >= args.seuil_simule
            assez_detache = (top - second) >= SEUIL_AMBIGUITE_ECART_MIN or second == 0.0
            if assez_sur and assez_detache:
                par_neq_simule[neq] += 1
                if top < SEUIL_RESOLUTION_CONFIANTE:
                    gagnes += 1
        multi = {neq: n for neq, n in par_neq_simule.items() if n > 2}
        print(f"\n   CE QU'IL RÉCUPÈRE   : {milliers(gagnes)} dossier(s) de plus")
        print(f"   CE QU'IL LAISSE PASSER :")
        print(f"      NEQ visés par PLUS DE DEUX dossiers : {milliers(len(multi))}")
        print(f"      dossiers dans ces groupes            : "
              f"{milliers(sum(multi.values()))}")
        print("\n   ⚠️ La seconde ligne est la forme de FAUX qu'on a vue de près :")
        print("      26 organisations publiques distinctes à 95-100 sur un même NEQ.")
        print("      **Un chiffrage qui ne compterait que le gain ferait paraître")
        print("      l'abaissement gratuit.**")
        if multi:
            print("\n      les plus gros groupes au seuil simulé :")
            for neq, n in sorted(multi.items(), key=lambda kv: -kv[1])[:5]:
                print(f"         {neq}  ×{n}")

        # ---- 3a. LES PARENTHÈSES RETIRÉES — seconde passe --------------------
        print("\n" + "-" * 78)
        print("3a. PARENTHÈSES RETIRÉES DES DEUX CÔTÉS — une CORRECTION DE DONNÉES")
        print("-" * 78)
        if args.sans_simulation_parentheses:
            print("\n   SAUTÉE (--sans-simulation-parentheses).")
            print("   ⚠️ Sautée n'est pas nulle.")
            return 0
        print("\n   ⚠️ Seconde passe : retirer la parenthèse change aussi le PRÉFIXE,")
        print("      donc la RÉCUPÉRATION. La simuler sans rejouer la récupération")
        print("      mesurerait autre chose.\n")
        familles_apres: Counter = Counter()
        for i, company in enumerate(orphelins):
            if i and i % 1000 == 0:
                print(f"   … passe 2 : {milliers(i)} examinés", flush=True)
            nom_propre = _sans_parentheses(company.nom_detecte)
            if not nom_propre:
                familles_apres["aucun candidat"] += 1
                continue
            matches = req_source.resolve_neq_by_name(
                session, nom_propre, ville=company.ville
            )
            # Le côté MIROIR aussi : on rescore contre le nom du registre
            # débarrassé de ses parenthèses. *« Des deux côtés » est la demande,
            # et ne le faire que d'un côté mesurerait une demi-correction.*
            cible = normaliser(_sans_parentheses(nom_propre))
            rescores = []
            for m in matches:
                propre = normaliser(_sans_parentheses(m.entry.nom))
                rescores.append((fuzz.WRatio(cible, propre), m))
            rescores.sort(key=lambda x: -x[0])
            if not rescores:
                familles_apres["aucun candidat"] += 1
                continue
            top = rescores[0][0]
            second = rescores[1][0] if len(rescores) > 1 else 0.0
            if top >= SEUIL_RESOLUTION_CONFIANTE and (
                (top - second) >= SEUIL_AMBIGUITE_ECART_MIN or len(rescores) == 1
            ):
                familles_apres["RETENU"] += 1
            elif top < SEUIL_RESOLUTION_CONFIANTE:
                familles_apres["trop faible"] += 1
            else:
                familles_apres["ambigu"] += 1

        print(f"\n   {'famille':<18} {'avant':>9} {'après':>9} {'écart':>9}")
        for f in ("RETENU", "ambigu", "trop faible", "aucun candidat"):
            a, b = familles.get(f, 0), familles_apres.get(f, 0)
            print(f"   {f:<18} {milliers(a):>9} {milliers(b):>9} {b - a:>+9}")
        print("\n   ⚠️ Cette correction ne peut que RAPPROCHER des chaînes qui")
        print("      désignent la même entreprise — un nom commercial entre")
        print("      parenthèses n'est pas une autre entité. *C'est ce qui la")
        print("      distingue d'un abaissement de seuil, qui récupère du faux.*")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
