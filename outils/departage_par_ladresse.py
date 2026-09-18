#!/usr/bin/env python3
"""Le départageur d'adresse sur les ambigus — et les trois choses qu'il doit rendre.

**Ce qui l'a décidé** *(mesure des trois départageurs, hôte, 2026-09-17)*. Sur
les **5 002 ambigus** : code postal **1 805 (36,1 %)**, dont **725 seul**; ville
**1 235 (24,7 %)**, dont **187 seule**; activité **166 (3,3 %)**, dont **97**.
**Le code postal est le départageur, la ville est son repli, l'activité attend
le chantier 22** — *sa comparaison par libellé est un plancher, et sa mesure sera
à refaire avec la table `(code, rôle) → sphère`.*

## Ce que cet outil rend, et pourquoi dans cet ordre

1. ⚠️ **La non-régression sur les RETENUS — en premier, parce que c'est un
   CRITÈRE et non un effet secondaire acceptable.** *Si elle échoue, l'outil
   sort en erreur et les chiffres qui suivent ne valent rien.*
2. **Ce que l'adresse sépare, par NIVEAU** — code complet, région de tri, ville —
   ⚠️ **et ce que le découpage a changé**, avec son critère : *aucun départage
   perdu, aucun gagnant déplacé.*
3. **Ce que chaque niveau apporte SEUL**, rejoué sur toute la population —
   *un niveau qui ne sépare rien que le précédent ne séparait déjà ne mérite pas
   son rang.*
4. **Les cas où un fait CORRIGE le score** — *« ce sont eux à regarder en
   premier »*, et ils se paginent **à part** (`--corrections N --depuis K`),
   **avec le niveau qui a tranché sur chaque ligne**.
5. **« Les exclut tous »** — *soit le bon candidat n'est pas dans le lot, soit le
   fait est sale.* **Sur un échantillon, lequel des deux — et ce que coûterait de
   le savoir sur toute la population.**

⚠️ **AUCUNE ÉCRITURE.** *La passe de reprise est la demande suivante; celle-ci
construit le départageur et le mesure.* **Un départage ÉCARTE un candidat; il
n'en CONFIRME aucun — les paires se regardent une à une.**

⚠️ **Le seuil de 92 et l'écart de 8 ne sont pas touchés.** Ils sont lus pour
savoir *qui sont les concurrents*, jamais pour être changés.

Usage, SUR L'HÔTE :
    python3 -m outils.departage_par_ladresse
    python3 -m outils.departage_par_ladresse --corrections 50           # les 50 premières
    python3 -m outils.departage_par_ladresse --corrections 50 --depuis 50
    python3 -m outils.departage_par_ladresse --departages 40 --depuis 200
    python3 -m outils.departage_par_ladresse --echantillon 0            # sans la section 4
"""
from __future__ import annotations

import argparse
import time
from collections import Counter

from outils.departageur_adresse import (
    ISSUES_QUI_APPELLENT_LE_REPLI,
    NIVEAU_CODE_COMPLET,
    NIVEAU_REGION_DE_TRI,
    NIVEAU_VILLE,
    NIVEAUX,
    NIVEAUX_DAVANT,
    NOMS_DES_NIVEAUX,
    Niveau,
    PasUnAmbigu,
    champs_des_dossiers,
    departager_ladresse,
    departager_le_dossier,
    faits_des_dossiers,
    faits_du_candidat,
)
from outils.departageurs import AUCUN_COMPATIBLE, DEPARTAGE, ISSUES
from outils.nombres import milliers

#: De combien la borne du moteur est multipliée pour demander *« le bon candidat
#: était-il seulement dans le lot? »*. ⚠️ **La borne elle-même est LUE dans le
#: moteur à l'exécution, jamais recopiée** — *une constante décorative vaut la
#: valeur qu'elle avait à l'import, pas celle du moteur.*
FACTEUR_BORNE_ELARGIE = 10

#: Combien de candidats la récupération élargie rend, pour aller chercher un bon
#: candidat que la fenêtre des concurrents n'aurait pas montré.
CANDIDATS_ELARGIS = 50

#: Les quatre lectures possibles d'une exclusion, **et elles s'excluent**. *Les
#: deux premières sont (a) « le bon candidat n'est pas dans le lot »; la
#: troisième est (b) « le fait est sale »; la dernière ne tranche pas, et c'est
#: un résultat.*
HORS_FENETRE = "(a) le bon candidat ÉTAIT rendu, hors de la fenêtre"
HORS_DU_LOT = "(a) le bon candidat n'était PAS dans le lot récupéré"
FAIT_SUSPECT = "(b) le fait est sale — PLUSIEURS codes complets au dossier"
NI_L_UN_NI_L_AUTRE = "ni l'un ni l'autre — aucun compatible nulle part"

#: La largeur des colonnes de libellé. ⚠️ *Un libellé plus long que son champ
#: décale la colonne de droite sans rien dire* — et deux chiffres qui ne
#: s'alignent plus se relisent comme deux échelles différentes.
LARGEUR_LIBELLE = 58


def _part(k: int, n: int) -> str:
    return f"{100 * k / n:.1f} %" if n else "—"


def _echantillon(population: list, combien: int) -> list:
    """Un tirage **À PAS CONSTANT sur toute la population**, jamais les N premiers.

    ⚠️ *Prendre la tête promeut l'ordre de la base au rang de critère* — c'est le
    cas 19, et c'est exactement ce qui avait fait lire « sept sur dix en tête
    d'alphabet » comme une fréquence alors que c'était un artefact du tirage.
    """
    if combien <= 0 or not population:
        return []
    if combien >= len(population):
        return list(population)
    pas = len(population) / combien
    return [population[int(i * pas)] for i in range(combien)]


def _formes(fait) -> str:
    return ",".join(sorted(fait.formes)[:3]) if fait is not None else "—"


def _ligne_candidat(match, faits, marque: str = " ") -> str:
    """⚠️ **Les deux résolutions du code postal s'affichent SÉPARÉMENT.** *Une
    paire tranchée sur `G5R` et une paire tranchée sur `G5R3Y8` ne valent pas la
    même chose, et les écrire dans la même colonne rendait la seconde
    indiscernable de la première.*"""
    entry = match.entry
    return (f"      {marque} {entry.neq}  {match.score:>6.2f}  "
            f"{(entry.nom or '')[:34]:<36} ville={(entry.ville or '—')[:18]!r:<20} "
            f"complet={_formes(faits.code_complet):<16} "
            f"tri={_formes(faits.region_de_tri)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--corrections", type=int, default=0, metavar="N",
                        help="montrer N cas où le fait CORRIGE le score (lot à part)")
    parser.add_argument("--departages", type=int, default=0, metavar="N",
                        help="montrer N départages, correction ou non")
    parser.add_argument("--depuis", type=int, default=0, metavar="K",
                        help="commencer au K-ième du lot demandé")
    parser.add_argument("--echantillon", type=int, default=40, metavar="N",
                        help="taille de l'échantillon « les exclut tous » (0 = sauter)")
    parser.add_argument("--limite", type=int, default=None, help="borner (mise au point)")
    args = parser.parse_args(argv)

    # ⚠️ **Un seul lot à la fois** : `--depuis` désigne un rang DANS UN LOT, et
    # le partager entre deux paginations ferait afficher deux pages différentes
    # sous le même numéro.
    if args.corrections and args.departages:
        parser.error("`--corrections` et `--departages` ne se demandent pas ensemble : "
                     "`--depuis` désigne un rang dans UN lot.")

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
    print("LE DÉPARTAGEUR D'ADRESSE — LE CODE POSTAL, PUIS LA VILLE EN REPLI")
    print("=" * 78)
    print(f"""
⚠️ CE QUE CET OUTIL NE DIRA PAS — à lire avant tout chiffre

   UN DÉPARTAGE ÉCARTE UN CANDIDAT; IL N'EN CONFIRME AUCUN. Deux entreprises
   distinctes peuvent partager une région de tri, et c'est le cas courant.

   UN FAIT ABSENT CHEZ UN CONCURRENT NE L'EXCLUT PAS. « Je ne sais pas » n'est
   pas « non ».

   ⚠️ LA VILLE NE PARLE JAMAIS LÀ OÙ LE CODE POSTAL A EXCLU TOUT LE MONDE.
   Ce serait bâtir un départage PAR-DESSUS une contradiction établie — la
   section 5 regarde ces cas-là au lieu de les trancher.

   L'ACTIVITÉ N'EST PAS CONSTRUITE. 97 dossiers qu'elle seule séparait, et sa
   comparaison par libellé est un PLANCHER. Elle attend la table
   (code, rôle) → sphère du chantier 22, et sa mesure sera à refaire.

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

        # ---- 0. LA POPULATION, par la règle du moteur ------------------------
        ambigus: list[tuple[Company, list]] = []
        retenus: list[tuple[Company, list]] = []
        for i, company in enumerate(orphelins):
            if i and i % 500 == 0:
                print(f"   … {milliers(i)} examinés", flush=True)
            matches = req_source.resolve_neq_by_name(
                session, company.nom_detecte, ville=company.ville
            )
            famille = famille_de(matches)
            if famille == "ambigu":
                ambigus.append((company, matches))
            elif famille == "RETENU":
                retenus.append((company, matches))
        print(f"\n   dossiers sans NEQ : {milliers(len(orphelins))}")
        print(f"   dont RETENUS      : {milliers(len(retenus))}   ← à NE PAS toucher")
        print(f"   dont AMBIGUS      : {milliers(len(ambigus))}   ← la population\n")

        # ---- 1. LA NON-RÉGRESSION — le critère, AVANT tout le reste ----------
        print("-" * 78)
        print("1. LA NON-RÉGRESSION SUR LES RETENUS — un CRITÈRE, pas un effet secondaire")
        print("-" * 78)
        print("""
   ⚠️ Elle n'est pas espérée : elle est STRUCTURELLE. `departager_le_dossier`
      lève `PasUnAmbigu` sur tout dossier que le nom a déjà tranché. On le
      VÉRIFIE ici sur les retenus réels, un par un — parce qu'une garde qu'on
      n'exécute pas est une intention.
""")
        # ⚠️ **Une seule collecte pour les DEUX populations.** *Chaque appel
        # balaie tous les signaux; quatre balayages pour deux lectures, c'est le
        # genre de coût qu'on paie sans le voir.*
        tous = [c for c, _ in retenus] + [c for c, _ in ambigus]
        champs = champs_des_dossiers(session, {c.id for c in tous})
        adresses = faits_des_dossiers(session, tous, champs=champs)
        refuses = touches = 0
        for company, matches in retenus:
            try:
                departager_le_dossier(matches, adresses[company.id])
            except PasUnAmbigu:
                refuses += 1
            else:
                touches += 1
        print(f"   retenus soumis au départageur        : {milliers(len(retenus)):>9}")
        print(f"   REFUSÉS par la garde                 : {milliers(refuses):>9} "
              f"{_part(refuses, len(retenus)):>8}")
        print(f"   ⛔ départages prononcés sur un retenu : {milliers(touches):>9}")
        if touches:
            print("\n   ⛔ CRITÈRE ÉCHOUÉ. Un dossier retenu a été re-décidé par")
            print("      l'adresse. Rien de ce qui suit ne doit être lu, et rien")
            print("      ne doit être écrit.")
            return 1
        print("\n   ✔ Aucun retenu n'est re-décidé par l'adresse. *Le nom tranche")
        print("     seul les 2 634; l'adresse ne parle que là où il se tait.*")

        if not ambigus:
            print("\n   Aucun ambigu — rien à départager.")
            return 0

        # ---- 2. CE QUE L'ADRESSE SÉPARE, PAR NIVEAU --------------------------
        n = len(ambigus)
        par_niveau_final: Counter = Counter()
        issues_du_niveau: dict[str, Counter] = {nom: Counter() for nom in NOMS_DES_NIVEAUX}
        departages: list[tuple] = []   # (company, matches, concurrents, departage)
        corrections: list[tuple] = []
        exclusions: list[tuple] = []
        #: Les concurrents de chaque dossier, gardés pour la section 3. *Les
        #: recalculer serait rejouer la récupération pour rien.*
        concurrents_du_dossier: dict[int, list] = {}
        # La forme d'AVANT, jouée en parallèle — **par un APPEL du même
        # mécanisme**, jamais par une réécriture de ce qu'on veut comparer.
        croisement: Counter = Counter()
        gagnants_differents: list[tuple] = []
        perdus: list[tuple] = []

        for company, matches in ambigus:
            faits = adresses[company.id]
            departage, concurrents = departager_le_dossier(matches, faits)
            concurrents_du_dossier[company.id] = concurrents
            davant = departager_ladresse(
                faits, [faits_du_candidat(m.entry) for m in concurrents],
                niveaux=NIVEAUX_DAVANT,
            )
            for nom, issue in departage.par_niveau:
                issues_du_niveau[nom][issue] += 1
            if departage.prononce:
                par_niveau_final[departage.niveau] += 1
                ligne = (company, matches, concurrents, departage)
                departages.append(ligne)
                if departage.gagnant != 0:
                    corrections.append(ligne)
            elif departage.issue == AUCUN_COMPATIBLE:
                exclusions.append((company, matches, concurrents, departage))
            croisement[(departage.niveau, davant.prononce)] += 1
            if davant.prononce and not departage.prononce:
                perdus.append((company, matches, concurrents, departage))
            elif davant.prononce and departage.gagnant != davant.gagnant:
                gagnants_differents.append((company, departage, davant))

        separes = sum(par_niveau_final.values())
        separes_davant = sum(k for (_, avant), k in croisement.items() if avant)
        L = LARGEUR_LIBELLE
        print("\n" + "-" * 78)
        print("2. CE QUE L'ADRESSE SÉPARE — un départageur, TROIS niveaux")
        print("-" * 78)
        print("""
   ⚠️ Le niveau unique d'avant mélangeait deux résolutions qui ne valent pas la
      même chose. `codes_postaux` range la région de tri À CÔTÉ de chaque code
      complet, donc deux faits s'intersectaient si et seulement si leurs RÉGIONS
      DE TRI s'intersectaient — le code complet ne tranchait rien, jamais.

      Un code COMPLET désigne un côté de rue, parfois un immeuble.
      Une RÉGION DE TRI couvre une ville entière : `G5R` est Rivière-du-Loup.
      *C'est de la ville déguisée en code postal, et ce découpage la dénude.*
""")
        titres = {
            NIVEAU_CODE_COMPLET: "CODE POSTAL COMPLET — un immeuble, un côté de rue",
            NIVEAU_REGION_DE_TRI: "RÉGION DE TRI — la finesse d'une ville, déclarée",
            NIVEAU_VILLE: "VILLE — en repli, là où le code postal se tait",
        }
        print(f"   {'niveau qui a tranché':<{L}} {'dossiers':>9} {'part':>8}")
        for nom in NOMS_DES_NIVEAUX:
            print(f"   {titres[nom]:<{L}} {milliers(par_niveau_final[nom]):>9} "
                  f"{_part(par_niveau_final[nom], n):>8}")
        total_adresse = "⇒ SÉPARÉS PAR L'ADRESSE"
        reste = "⛔ indépartageables par l'adresse"
        print(f"   {total_adresse:<{L}} {milliers(separes):>9} {_part(separes, n):>8}")
        print(f"\n   {reste:<{L}} {milliers(n - separes):>9} {_part(n - separes, n):>8}")
        print("      *C'est un résultat, pas une absence de mesure.*")

        # --- le CRITÈRE de ce découpage : ne rien perdre ----------------------
        print(f"\n   {'— ce que le découpage a CHANGÉ —':^{L + 20}}\n")
        print(f"   {'séparés par la forme D AVANT (les deux résolutions mêlées)':<{L}} "
              f"{milliers(separes_davant):>9}")
        print(f"   {'séparés par la forme À TROIS NIVEAUX':<{L}} {milliers(separes):>9}")
        ajoutes = croisement.get((NIVEAU_CODE_COMPLET, False), 0)
        print(f"\n   {'⇒ AJOUTÉS par le code complet, que la région seule ratait':<{L}} "
              f"{milliers(ajoutes):>9}")
        print("      *Plusieurs candidats partageaient la région de tri; UN SEUL")
        print("       partage le code complet. Le niveau fin tranche là où le")
        print("       niveau grossier ne pouvait pas — c'est un gain, et il se")
        print("       décide, il ne se subit pas.*")
        print(f"\n   {'⛔ PERDUS — séparés avant, plus maintenant':<{L}} "
              f"{milliers(len(perdus)):>9}")
        print(f"   {'⛔ GAGNANT DIFFÉRENT du même dossier':<{L}} "
              f"{milliers(len(gagnants_differents)):>9}")
        if perdus or gagnants_differents:
            print("\n   ⛔ CRITÈRE ÉCHOUÉ. Le découpage devait rendre la granularité")
            print("      LISIBLE, pas écrire moins ni écrire autrement. Rien de ce")
            print("      qui suit ne doit être lu.")
            for company, _, _, dep in perdus[:5]:
                print(f"      perdu : {(company.nom_detecte or '')[:50]}  {dep.issue}")
            for company, dep, davant in gagnants_differents[:5]:
                print(f"      gagnant : {(company.nom_detecte or '')[:40]}  "
                      f"{davant.gagnant} → {dep.gagnant}")
            return 1
        print("\n   ✔ Aucun départage perdu, aucun gagnant déplacé. *Le découpage")
        print("     nomme ce qui décidait déjà; il ne décide pas à sa place.*")

        # --- les issues de chaque niveau -------------------------------------
        for rang, niveau in enumerate(NIVEAUX):
            total_niveau = sum(issues_du_niveau[niveau.nom].values())
            suivant = NIVEAUX[rang + 1] if rang + 1 < len(NIVEAUX) else None
            print(f"\n   ▸ {niveau.nom.upper()}   "
                  f"({milliers(total_niveau)} dossier(s) consulté(s))")
            for issue in ISSUES:
                k = issues_du_niveau[niveau.nom].get(issue, 0)
                if not k and issue not in (DEPARTAGE, AUCUN_COMPATIBLE):
                    continue
                marque = ""
                if issue == DEPARTAGE:
                    marque = "  ←"
                elif suivant is None:
                    marque = "  ⛔ fin"
                elif issue in ISSUES_QUI_APPELLENT_LE_REPLI:
                    marque = "  → repli"
                elif issue == AUCUN_COMPATIBLE:
                    marque = ("  → repli (même fait, dégradé)"
                              if suivant.degradation_du_precedent
                              else "  ⛔ la ville NE PARLE PAS")
                print(f"      {issue:<{LARGEUR_LIBELLE}} {milliers(k):>8} "
                      f"{_part(k, total_niveau):>8}{marque}")
        print("""
   ⚠️ « Le fait les exclut tous » se franchit vers une DÉGRADATION DU MÊME FAIT,
      jamais vers un autre fait. Le code complet laisse donc parler la région de
      tri — `G5R3A7` contre `G5R3Y8` s'excluent au code complet, et c'est
      exactement ce que la dégradation tolère. La région de tri, elle, ne laisse
      pas parler la ville : ce serait bâtir un départage PAR-DESSUS une
      contradiction établie.
""")

        # ---- 3. CE QUE CHAQUE NIVEAU APPORTE SEUL ---------------------------
        print("-" * 78)
        print("3. CE QUE CHAQUE NIVEAU APPORTE SEUL — mérite-t-il son rang?")
        print("-" * 78)
        print("""
   ⚠️ Deux lectures, et la seconde seule répond à la question.

      EN CASCADE (tableau 2), un niveau ne voit que ce que le précédent n'a pas
      tranché : son compte EST déjà sa contribution marginale. Mais il ne dit
      pas si ce niveau aurait su trancher ailleurs.

      SEUL, chaque niveau est rejoué sur TOUTE la population comme s'il était le
      seul fait. On voit alors ce qu'il couvre, ce qu'il partage avec les autres,
      et ce qu'il est LE SEUL à savoir séparer.
""")
        seuls: dict[str, set[int]] = {}
        for niveau in NIVEAUX:
            couvre: set[int] = set()
            for company, matches in ambigus:
                dep = departager_ladresse(
                    adresses[company.id],
                    [faits_du_candidat(m.entry) for m in concurrents_du_dossier[company.id]],
                    niveaux=(Niveau(niveau.nom),),
                )
                if dep.prononce:
                    couvre.add(company.id)
            seuls[niveau.nom] = couvre

        # ⚠️ **La population se LIT, elle ne s'écrit pas dans le libellé.** *Un
        # compte figé dans une étiquette donne l'autorité d'une mesure à un
        # texte, et c'est l'endroit où personne ne va le vérifier.*
        entete_seuls = f"niveau, joué SEUL sur les {milliers(n)} ambigus"
        print(f"   {entete_seuls:<{L}} {'couvre':>9} {'LUI SEUL':>10}")
        for niveau in NIVEAUX:
            autres: set[int] = set()
            for autre in NIVEAUX:
                if autre.nom != niveau.nom:
                    autres |= seuls[autre.nom]
            propre = seuls[niveau.nom] - autres
            print(f"   {niveau.nom:<{L}} {milliers(len(seuls[niveau.nom])):>9} "
                  f"{milliers(len(propre)):>10}")
        union: set[int] = set()
        for niveau in NIVEAUX:
            union |= seuls[niveau.nom]
        somme = sum(len(seuls[niveau.nom]) for niveau in NIVEAUX)
        print(f"\n   union des trois joués seuls : {milliers(len(union))}"
              f"   recouvrement : {milliers(somme - len(union))}")
        print("\n   ⚠️ Un niveau dont la colonne « LUI SEUL » est vide ne sépare rien")
        print("      que les autres ne séparaient déjà — et ne mérite pas son rang.")
        print("      *Mais la colonne « couvre » ne l'absout pas : couvrir beaucoup")
        print("       en double ne vaut rien.*")

        # ---- 4. LES CORRECTIONS — le lot à regarder en premier ---------------
        print("\n" + "-" * 78)
        print("4. LES CAS OÙ UN FAIT CORRIGE LE SCORE — le lot à regarder en PREMIER")
        print("-" * 78)
        print("""
   ⚠️ « Désigne un autre » n'est PAS une erreur : c'est le cas où le fait
      CORRIGE le score au lieu de le confirmer, et c'est précisément ce qu'on
      cherche. *Mais c'est aussi là que le départageur engage le plus.*
""")
        par_niveau_corrige: Counter = Counter(d.niveau for _, _, _, d in corrections)
        print(f"   {'niveau qui corrige':<{L}} {'dossiers':>9} {'des départages':>16}")
        for nom in NOMS_DES_NIVEAUX:
            k = par_niveau_corrige.get(nom, 0)
            print(f"   {nom:<{L}} {milliers(k):>9} "
                  f"{_part(k, par_niveau_final[nom]):>16}")
        print(f"   {'⇒ TOTAL à relire une à une':<{L}} "
              f"{milliers(len(corrections)):>9} "
              f"{_part(len(corrections), separes):>16}")

        lot, titre, depuis = [], "", args.depuis
        if args.corrections:
            lot, titre = corrections, "CORRECTIONS"
        elif args.departages:
            lot, titre = departages, "DÉPARTAGES"
        if not lot:
            print(f"\n   `--corrections N --depuis K` les montre PAR LOT "
                  f"(1 à {milliers(len(corrections))}).")
            print("   `--departages N --depuis K` montre TOUS les départages, "
                  "correction ou non.")
            print("   ⚠️ Un seul des deux à la fois : `--depuis` désigne un rang "
                  "dans UN lot.")
        else:
            combien = args.corrections or args.departages
            page = lot[depuis: depuis + combien]
            print(f"\n   {titre} {depuis + 1} à {depuis + len(page)} "
                  f"sur {milliers(len(lot))} :")
            print("   *Le fait du dossier est donné BRUT, pas seulement comparé —")
            print("    on ne relit pas une paire sur la forme qu'on a calculée.*\n")
            for company, matches, concurrents, departage in page:
                faits = adresses[company.id]
                du_dossier = faits.de_niveau(departage.niveau)
                print(f"   ── {(company.nom_detecte or '')[:64]}")
                print(f"      tranché par : {departage.niveau}")
                print(f"      au dossier  : {(du_dossier.brut or '')[:70]!r}")
                print(f"      comparé sur : {sorted(du_dossier.formes)[:6]}")
                for rang, m in enumerate(concurrents):
                    marque = "→" if rang == departage.gagnant else (
                        "×" if rang == 0 else " ")
                    print(_ligne_candidat(m, faits_du_candidat(m.entry), marque))
                print()
            print("   → = retenu par l'adresse    × = mieux scoré, écarté")
            print("   ⚠️ Un départage ÉCARTE un candidat; il n'en CONFIRME aucun.")

        # ---- 5. « LES EXCLUT TOUS » — lequel des deux, et à quel prix --------
        print("\n" + "-" * 78)
        print("5. « LE FAIT LES EXCLUT TOUS » — lequel des deux, sur un échantillon")
        print("-" * 78)
        par_niveau_exclut: Counter = Counter(
            d.par_niveau[-1][0] for _, _, _, d in exclusions
        )
        print(f"\n   {'niveau qui exclut tout le monde':<{L}} {'dossiers':>9}")
        for nom in NOMS_DES_NIVEAUX:
            print(f"   {nom:<{L}} {milliers(par_niveau_exclut.get(nom, 0)):>9}")
        print(f"   {'⇒ TOTAL':<{L}} {milliers(len(exclusions)):>9}")
        print("""
   ⚠️ Ce n'est PAS un départage : le fait du dossier ne concorde avec aucun
      candidat, et aucun gagnant n'est prononcé. **Deux causes possibles, et
      elles n'appellent pas le même correctif :**

      (a) LE BON CANDIDAT N'EST PAS DANS LE LOT — la récupération ne l'a pas
          rendu. Correctif : la borne, ou un gisement de noms de plus.
      (b) LE FAIT EST SALE — le code postal lu au dossier n'est pas celui de
          l'entreprise (adresse d'un tiers, adresse de chantier, code du
          donneur d'ouvrage). Correctif : la lecture du champ.
""")
        if args.echantillon <= 0 or not exclusions:
            print("   (échantillon sauté — `--echantillon N` pour le demander)")
        else:
            borne = FACTEUR_BORNE_ELARGIE * req_source.LIMITE_CANDIDATS_PAR_NOM
            tires = _echantillon(exclusions, args.echantillon)
            print(f"   Échantillon : {milliers(len(tires))} sur "
                  f"{milliers(len(exclusions))}, TIRÉ À PAS CONSTANT sur toute la")
            print("   population — *pas les N premiers : l'ordre de la base n'est pas")
            print(f"   un critère (cas 19)*. Borne élargie : {milliers(borne)} "
                  f"(×{FACTEUR_BORNE_ELARGIE}).\n")

            causes: Counter = Counter()
            porte_plusieurs_codes = 0
            depart = time.perf_counter()
            for company, matches, concurrents, departage in tires:
                niveau = departage.par_niveau[-1][0]
                du_dossier = adresses[company.id].de_niveau(niveau)
                # ⚠️ **Un indicateur PAR CAS, jamais le compteur cumulé.** *Lire
                # un total là où on interroge un dossier fait classer le
                # deuxième cas d'après le premier.*
                #
                # ⚠️ Et il se lit sur le CODE COMPLET du dossier, quel que soit le
                # niveau qui a exclu : *deux codes complets veulent dire deux
                # adresses, et c'est vrai même quand c'est la région de tri qui a
                # prononcé l'exclusion.*
                complets = adresses[company.id].code_complet
                plusieurs_codes = (
                    niveau in (NIVEAU_CODE_COMPLET, NIVEAU_REGION_DE_TRI)
                    and complets is not None and len(complets.formes) > 1
                )
                porte_plusieurs_codes += 1 if plusieurs_codes else 0

                def _compatible(candidats, exclure: set[str]) -> bool:
                    for m in candidats:
                        if m.entry.neq in exclure:
                            continue
                        fait = faits_du_candidat(m.entry).de_niveau(niveau)
                        if fait is not None and du_dossier.compatible_avec(fait):
                            return True
                    return False

                # (i) GRATUIT — le bon candidat était-il rendu, hors de la fenêtre?
                en_lice = {m.entry.neq for m in concurrents}
                if _compatible(matches, en_lice):
                    causes[HORS_FENETRE] += 1
                    continue
                # (ii) COÛTEUX — et hors du lot récupéré? *C'est ce coût-là que la
                # section chiffre : le reste est gratuit.*
                elargis = req_source.resolve_neq_by_name(
                    session, company.nom_detecte, ville=company.ville,
                    limit=CANDIDATS_ELARGIS, limite_candidats=borne,
                )
                if _compatible(elargis, {m.entry.neq for m in matches}):
                    causes[HORS_DU_LOT] += 1
                elif plusieurs_codes:
                    causes[FAIT_SUSPECT] += 1
                else:
                    causes[NI_L_UN_NI_L_AUTRE] += 1
            secondes = time.perf_counter() - depart

            k = len(tires)
            entete = "ce que l'échantillon montre"
            indicateur = "le dossier porte PLUSIEURS codes postaux complets"
            print(f"   {entete:<{L}} {'cas':>6} {'part':>8}")
            for cause in (HORS_FENETRE, HORS_DU_LOT, FAIT_SUSPECT, NI_L_UN_NI_L_AUTRE):
                v = causes.get(cause, 0)
                print(f"   {cause:<{L}} {v:>6} {_part(v, k):>8}")
            print("\n   indicateur, INDÉPENDANT du classement ci-dessus :")
            print(f"   {indicateur:<{L}} "
                  f"{porte_plusieurs_codes:>6} {_part(porte_plusieurs_codes, k):>8}")
            print("   *Deux codes complets au dossier veulent dire deux adresses —")
            print("    et rien ne dit laquelle est celle de l'entreprise.*")
            print("""
   ⚠️ La dernière ligne ne tranche PAS entre (a) et (b) : « aucun candidat
      compatible même à la borne élargie » se lit aussi bien comme « l'entreprise
      n'est pas au registre » que comme « le code postal lu est celui d'un
      tiers ». *Ce que l'échantillon sépare, c'est ce qui est MÉCANIQUEMENT
      vérifiable; le reste demande une paire lue.*

   ⚠️ Et un échantillon dit qu'une chose EXISTE dans une proportion; il ne dit
      pas où elle tombe dossier par dossier. *Aucune écriture ne se décide
      dessus.*
""")
            par_cas = secondes / k if k else 0.0
            # ⚠️ **Le séparateur de milliers vient de `outils/nombres.py`**, et
            # jamais d'une substitution posée sur la ligne entière : *celle-là
            # mange aussi la virgule du libellé, en silence.* ⚠️ *Et la garde qui
            # l'interdit lit des LIGNES, pas de la syntaxe — écrire l'idiome dans
            # un commentaire la fait tomber comme si on l'avait employé.*
            print(f"   CE QUE ÇA A COÛTÉ   : {milliers(secondes, 1)} s pour "
                  f"{milliers(k)} cas ({milliers(par_cas, 2)} s/cas)")
            print("   CE QUE COÛTERAIT DE LE SAVOIR SUR TOUS :")
            print(f"      les {milliers(len(exclusions))} exclusion(s) de l'adresse : "
                  f"≈ {milliers(par_cas * len(exclusions) / 60, 1)} min de machine")
            print("      + la relecture humaine des paires que la machine ne")
            print("        tranche pas — c'est CELLE-LÀ qui décide du prix.")

        print("\n" + "=" * 78)
        print("   RIEN N'A ÉTÉ ÉCRIT. La passe de reprise est la demande suivante,")
        print("   et elle se décide sur les paires, pas sur le total.")
        print("=" * 78)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
