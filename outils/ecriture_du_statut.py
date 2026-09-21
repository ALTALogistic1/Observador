#!/usr/bin/env python3
"""L'écriture du départage par le STATUT — **élargie aux confirmations.**

## La décision d'Alexandre, du 20 au 21 septembre

**Le 20 :** la forme « n'écarter que les radiées », restreinte aux **égalités
strictes**. *1 065 NEQ posés, instantané `statut-20260921T040739.json`.*

**Le 21, la portée s'élargit :** l'exclusion s'écrit **aussi là où le score
désignait déjà un gagnant**, à la condition stricte que le statut désigne **LE
MÊME**. *Le statut ne départage plus : il confirme.* **Deux instruments
indépendants désignent le même candidat — c'est la forme du 19 septembre, où
l'adresse confirmait le score.**

Les deux portées, disjointes, et leur union est exactement *« le survivant est
seul ET au score du sommet »* :

| portée | ce que le NOM avait fait | ce que le STATUT fait |
|---|---|---|
| `égalités` | il ne désignait **personne** — au moins deux ex æquo au sommet | il **départage** |
| `confirmations` | il désignait **un gagnant** — sommet unique | il **confirme** |

## ⚠️ CE QUI NE CHANGE PAS : LES RESTANTS SOUS LE SOMMET

**Un survivant moins bien scoré que le meilleur reste EN SUSPENS** — les **78**
du 20 septembre, et tous ceux que l'élargissement fait apparaître. *Deux
instruments s'y contredisent, et rien ne dit lequel a raison.* **Un départage non
écrit se reprend; un départage écrit à tort coûte une identité.**

⚠️ *Cette condition n'est pas redondante avec la portée, et c'est elle qui exclut
`Les Ruchers du Roi Bourdon`* — voir `TEMOIN_DE_LA_CONTRADICTION`, que la sortie
affiche par son nom plutôt que de l'affirmer ici.

## ⚠️ LA RÉSERVE SUR L'ÉLARGISSEMENT — elle ne se lève pas

**1. La condition ne compare le survivant qu'à ses CONCURRENTS, jamais au
DOSSIER.** *Le score est relatif au lot; le statut est relatif au lot.* Élargie,
la règle se lit exactement ainsi : **« poser `matches[0]` quand tous ses
concurrents sont radiés ».** Les deux instruments ne sont indépendants que par
leur source; **aucun des deux ne répond à « ce candidat est-il l'entreprise du
signal? »**

**2. L'ADRESSE, elle, compare au dossier — et elle a contredit cet accord.**
*Deux fois dans les paires du statut déjà lues* : `#18572 9133-4961 QUEBEC INC.`
(dossier `G9A2G9`, survivant `G8Z0A3`) et `#1101 Amar Transport` (dossier
Vaughan ON, survivant Laval), tous deux *« aucun concurrent compatible — le fait
les exclut tous »*. ⚠️ **Elle est donc rendue ici en COLONNE et en COMPTE, jamais
en condition** *(`ce_que_ladresse_dit`)* — la décision reste à Alexandre, mais le
chiffre se lit avant `--appliquer`.

**3. Le cas que la condition laisserait passer à tort : le bon candidat absent du
lot.** *`resolve_neq_by_name` plafonne le lot à CINQ* — vu 2 fois sur 32 paires
lues. **Quand le vrai match n'est pas dans le lot, « tous les concurrents sont
radiés » devient un argument POUR poser un NEQ faux**, avec deux instruments qui
paraissent s'accorder.

**4. Une entreprise radiée peut être la bonne.** *Un signal ancien peut désigner
une entreprise fermée depuis, et `REQEntry` ne porte AUCUNE date de radiation.*
**L'exclusion peut garder le mauvais candidat, et rien ne le dirait.**

## Les deux populations, séparées

**Les égalités DÉJÀ POSÉES ne sont pas retouchées, et ce n'est pas une
intention : c'est une structure.** *La passe ne lit que `Company.neq IS NULL`* —
un dossier posé le 20 septembre n'entre pas dans la population. `--instantane-
precedent FICHIER` le **vérifie** sur les 1 065 plutôt que de l'affirmer.

## La forme du 19 septembre

*Rapport par défaut*, `--appliquer` sur demande explicite, **instantané écrit
AVANT le commit** avec `neq_avant` et `statut_avant`, `--defaire` pour revenir.
**Un NEQ déjà pris n'est pas posé** : le rapprochement est journalisé et **les
deux dossiers restent**. **Refus au-delà de deux prétendants.**

⚠️ **Les échelles ne bougent pas : seuil 92, écart 8.**

Usage, SUR L'HÔTE :
    python3 -m outils.ecriture_du_statut                        # rapport seul
    python3 -m outils.ecriture_du_statut --comparer 20          # ce qui SERAIT écrit
    python3 -m outils.ecriture_du_statut --suspendus 40         # ce qu'on ne pose PAS
    python3 -m outils.ecriture_du_statut --portee confirmations
    python3 -m outils.ecriture_du_statut \
        --instantane-precedent /var/lib/falkye/statut-20260921T040739.json
    python3 -m outils.ecriture_du_statut --appliquer
    python3 -m outils.ecriture_du_statut --defaire FICHIER.json
"""
from __future__ import annotations

import argparse
from collections import Counter

from outils import pose_du_neq
from outils.departageurs import AUCUN_COMPATIBLE, DEPARTAGE
from outils.nombres import milliers
from outils.paires_du_statut import restants_apres
from outils.statut_sur_les_egalites import ECARTER_RADIEES, ex_aequo

#: ⚠️ **La forme retenue par Alexandre.** *Nommée ici pour que l'outil ne
#: puisse pas en employer une autre par accident* — et pour qu'un lecteur voie
#: laquelle, sans relire le code.
FORME_QUI_SECRIT = ECARTER_RADIEES

#: ⚠️ **Empruntée, jamais recopiée** — elle vit dans `outils/pose_du_neq.py`,
#: près du geste qu'elle gouverne. *Elle était recopiée dans trois outils; ce
#: quatrième ne l'a pas été.*
DOSSIER_INSTANTANE = pose_du_neq.DOSSIER_INSTANTANE

# ---------------------------------------------------------------------------
# LES DEUX PORTÉES — disjointes, et comptées à part
# ---------------------------------------------------------------------------
#: ⚠️ **Elles se distinguent par ce que le NOM avait fait, pas par ce que le
#: statut fait.** *Dans les deux, le survivant est seul et au score du sommet;
#: ce qui change est qu'il y avait, ou non, un gagnant à confirmer.*
EGALITE = "égalité stricte — le nom ne désignait personne"
CONFIRMATION = "confirmation — le score désignait, le statut désigne LE MÊME"
PORTEES = (EGALITE, CONFIRMATION)

#: Ce que `--portee` accepte, et ce que chaque valeur ouvre. *`les-deux` est le
#: défaut parce qu'un seul chemin d'écriture vaut mieux que deux outils.*
PORTEES_DEMANDEES = {
    "egalites": (EGALITE,),
    "confirmations": (CONFIRMATION,),
    "les-deux": PORTEES,
}

#: Les raisons de laisser en suspens, **dans l'ordre où elles se lisent.**
#: ⚠️ *Chacune est un RÉSULTAT* : « le lot est vide » et « le restant est sous le
#: sommet » appellent deux suites différentes.
#:
#: ⚠️ **`PAS_UNE_EGALITE` a disparu de cette liste le 21 septembre** — ce n'est
#: plus un blocage, c'est la portée `CONFIRMATION`. *Ce qui bloquait hier et ne
#: bloque plus aujourd'hui se dit, sinon l'écart se lit comme un oubli.*
SOUS_LE_SOMMET = "⚠️ le restant est SOUS le sommet — deux instruments se contredisent"
PAS_UN_SEUL = "l'exclusion laisse PLUSIEURS candidats"
LOT_VIDE = "l'exclusion vide le lot — tous les candidats sont radiés"
HORS_PORTEE = "hors de la portée demandée par --portee"
RAISONS = (SOUS_LE_SOMMET, PAS_UN_SEUL, LOT_VIDE, HORS_PORTEE)

#: Ce que l'ADRESSE dit du candidat retenu — ⚠️ **une COLONNE, jamais une
#: condition.** *Elle est le seul instrument qui compare le survivant au
#: DOSSIER, et elle a contredit l'accord score+statut dans les paires lues.*
ADRESSE_ACCORD = "l'adresse désigne LE MÊME"
ADRESSE_CONTRE = "⚠️ l'adresse désigne un AUTRE candidat"
ADRESSE_EXCLUT_TOUS = "⚠️ l'adresse les exclut TOUS — le bon n'est peut-être pas dans le lot"
ADRESSE_MUETTE = "l'adresse ne dit rien"
VERDICTS_DADRESSE = (ADRESSE_ACCORD, ADRESSE_CONTRE, ADRESSE_EXCLUT_TOUS, ADRESSE_MUETTE)

#: ⚠️ **Le dossier qu'Alexandre a nommé comme contradiction.** *La sortie le
#: CHERCHE et affiche ce que l'outil en fait* — plutôt que d'affirmer ici qu'il
#: est exclu. **Un témoin qu'on affiche se réfute; un témoin qu'on affirme ne se
#: réfute pas.** Si le nom ne se trouve plus dans la population, la sortie le dit
#: au lieu de laisser la preuve disparaître en silence.
TEMOIN_DE_LA_CONTRADICTION = "Les Ruchers du Roi Bourdon"

#: Les autres étiquettes de la colonne de gauche du rapport. ⚠️ *Une étiquette
#: plus longue que sa colonne pousse le nombre* — la largeur se CALCULE sur
#: toutes les étiquettes réellement imprimées, elle ne se devine pas.
ETIQUETTES_DU_RAPPORT = (
    "✅ À POSER — le survivant est seul, AU sommet",
    "⛔ NEQ déjà porté — conservé et journalisé",
    "⛔ refusés — plus de deux prétendants",
    "dont ÉGALITÉS STRICTES (le nom ne désignait personne)",
    "dont CONFIRMATIONS (le score désignait le même)",
    "dont égalités strictes (les 78 du 20 septembre)",
    "dont sommet unique (apparus avec l'élargissement)",
)
LARGEUR_DUNE_RAISON = max(
    len(t) for t in RAISONS + ETIQUETTES_DU_RAPPORT + VERDICTS_DADRESSE) + 1


def portee_de(matches) -> str:
    """`EGALITE` ou `CONFIRMATION` — **ce que le NOM avait fait, rien d'autre.**

    *Les deux valeurs sont exhaustives et disjointes : un lot a des ex æquo au
    sommet, ou il n'en a pas.*
    """
    return EGALITE if len(ex_aequo(matches)) >= 2 else CONFIRMATION


def ce_qui_bloque(matches, concurrents, portees=PORTEES):
    """`(raison ou None, restant, portée)` — **les conditions, dans l'ordre.**

    ⚠️ *La condition qui porte la décision du 21 septembre est la TROISIÈME* :
    le survivant doit être **AU score du sommet**. Elle vaut dans les deux
    portées, et c'est elle qui laisse en suspens les 78 du 20 septembre comme
    les contradictions que l'élargissement fait apparaître.
    """
    restes = restants_apres(concurrents, FORME_QUI_SECRIT)
    if not restes:
        return LOT_VIDE, None, None
    if len(restes) > 1:
        return PAS_UN_SEUL, None, None
    seul = restes[0]
    if seul.score < matches[0].score:
        return SOUS_LE_SOMMET, seul, portee_de(matches)
    portee = portee_de(matches)
    if portee not in portees:
        return HORS_PORTEE, seul, portee
    return None, seul, portee


def ce_que_ladresse_dit(concurrents, du_dossier, neq_retenu) -> str:
    """Le verdict de l'adresse sur le candidat retenu — ⚠️ **rendu, jamais
    appliqué.**

    *L'appel passe par `departager_ladresse`, le mécanisme du produit* — un
    départageur recopié à la main est déjà arrivé une fois.
    """
    from outils.departageur_adresse import departager_ladresse, faits_du_candidat

    departage = departager_ladresse(
        du_dossier, [faits_du_candidat(m.entry) for m in concurrents])
    if departage.issue == AUCUN_COMPATIBLE:
        return ADRESSE_EXCLUT_TOUS
    if departage.issue != DEPARTAGE or departage.gagnant is None:
        return ADRESSE_MUETTE
    gagnant = concurrents[departage.gagnant]
    return ADRESSE_ACCORD if gagnant.entry.neq == neq_retenu else ADRESSE_CONTRE


def _part(k: int, n: int) -> str:
    return f"{100 * k / n:.1f} %" if n else "—"


def _ligne_comptee(etiquette: str, k: int, n: int = 0) -> str:
    part = f" {_part(k, n):>8}" if n else ""
    return f"   {etiquette:<{LARGEUR_DUNE_RAISON}} {milliers(k):>9}{part}"


def _montrer(lot: list[dict], depuis: int, combien: int, titre: str) -> None:
    """Des paires ENTIÈRES — **de ce qui serait ÉCRIT**, jamais de ce qui est
    départageable. ⚠️ *Ce n'est pas la même population, et c'est la lecture qui
    décide.*"""
    tranche = lot[depuis: depuis + combien]
    print("\n" + "=" * 78)
    print(f"{titre} — {depuis + 1} à {depuis + len(tranche)} sur {milliers(len(lot))}")
    print("=" * 78)
    if not tranche:
        print("\n   (aucun dossier dans cette population)")
    for paire in tranche:
        print(f"\n   #{paire['company_id']}   {(paire['nom_detecte'] or '')[:54]}")
        print(f"      → {paire['neq']}  {paire['score']:>6.1f}  "
              f"{(paire['nom_registre'] or '')[:40]}   [{paire['statut_registre']}]")
        for m in paire["_concurrents"]:
            marque = "→" if m.entry.neq == paire["neq"] else "×"
            print(f"      {marque} {m.entry.neq}  {m.score:>6.1f}  "
                  f"{(m.entry.nom or '')[:34]:<36} [{m.entry.statut}]  "
                  f"{(m.entry.ville or '—')[:16]}")
        if paire.get("adresse"):
            print(f"      ✳️ {paire['adresse']}")
        if paire.get("motif"):
            print(f"      ⛔ {paire['motif']}"
                  f"  (dossier #{paire.get('detenteur_id')})")


def _montrer_le_temoin(suspendus: list[dict], a_poser: list[dict], nom: str) -> None:
    """⚠️ **Le cas nommé par Alexandre, CHERCHÉ et affiché tel qu'il ressort.**

    *Ni affirmé exclu, ni supposé présent* : la sortie dit ce que l'outil en
    fait, y compris « il n'est plus dans la population ».
    """
    print("\n" + "-" * 78)
    print(f"LE TÉMOIN NOMMÉ — « {nom} »")
    print("-" * 78)
    cle = nom.casefold()
    trouves = [(ligne, ligne.get("_raison")) for ligne in suspendus
               if cle in (ligne["nom_detecte"] or "").casefold()]
    trouves += [(ligne, None) for ligne in a_poser
                if cle in (ligne["nom_detecte"] or "").casefold()]
    if not trouves:
        print(f"""
   ⚠️ INTROUVABLE dans la population d'aujourd'hui.

      Ce n'est pas une preuve que la condition l'exclut : le dossier peut
      avoir été posé, fusionné ou renommé. La preuve manque, et la sortie
      le dit plutôt que de la laisser disparaître en silence.""")
        return
    for ligne, raison in trouves:
        print(f"\n   #{ligne['company_id']}   {(ligne['nom_detecte'] or '')[:54]}")
        for m in ligne["_concurrents"]:
            print(f"        {m.score:>6.1f}  {m.entry.neq}  "
                  f"{(m.entry.nom or '')[:34]:<36} [{m.entry.statut}]")
        if raison is None:
            print("      ✅ IL SERAIT ÉCRIT — la condition ne l'exclut PAS.")
            print("         ⚠️ À lire avant d'appliquer : Alexandre l'a nommé"
                  " comme une contradiction.")
        else:
            print(f"      ⛔ LAISSÉ EN SUSPENS — {raison}")


def _verifier_l_instantane_precedent(session, chemin) -> None:
    """⚠️ **Les 1 065 du 20 septembre ne sont pas retouchés — vérifié, pas
    affirmé.**

    *La passe ne lit que `Company.neq IS NULL`, donc un dossier posé n'entre pas
    dans la population.* **C'est une structure, et ce contrôle la met à
    l'épreuve** au lieu de la laisser au rang d'intention.
    """
    import json

    from sqlalchemy import select

    from falkye.models.company import Company

    charge = json.loads(chemin.read_text(encoding="utf-8"))
    poses = [x for x in charge.get("a_poser", []) if x.get("company_id")]
    print("\n" + "-" * 78)
    print("LES ÉGALITÉS DÉJÀ POSÉES — ce que l'outil ne doit pas retoucher")
    print("-" * 78)
    print(f"\n   instantané lu : {chemin}")
    print(_ligne_comptee("dossiers posés à cette passe", len(poses)))
    if not poses:
        return
    ids = [x["company_id"] for x in poses]
    sans_neq = session.execute(
        select(Company.id).where(Company.id.in_(ids), Company.neq.is_(None))
    ).scalars().all()
    print(_ligne_comptee("… revenus SANS NEQ dans la population", len(sans_neq)))
    if sans_neq:
        print(f"""
   ⚠️ {milliers(len(sans_neq))} dossier(s) posé(s) le 20 septembre n'ont PLUS de NEQ.
      Attendu : 0. Les identifiants : {', '.join(str(i) for i in sans_neq[:20])}
      Ne pas appliquer avant d'avoir lu pourquoi.""")
    else:
        print("""
   ✅ Aucun. La séparation des deux populations tient par CONSTRUCTION :
      la passe ne lit que `Company.neq IS NULL`.""")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--appliquer", action="store_true",
                        help="ÉCRIRE (défaut : rapport seul, aucune écriture)")
    parser.add_argument("--portee", choices=sorted(PORTEES_DEMANDEES),
                        default="les-deux",
                        help="quelle population écrire (défaut : les-deux)")
    parser.add_argument("--comparer", type=int, default=0, metavar="N",
                        help="montrer N paires de ce qui SERAIT ÉCRIT, par portée")
    parser.add_argument("--suspendus", type=int, default=0, metavar="N",
                        help="montrer N dossiers LAISSÉS EN SUSPENS, et pourquoi")
    parser.add_argument("--depuis", type=int, default=0, metavar="K")
    parser.add_argument("--temoin", default=TEMOIN_DE_LA_CONTRADICTION, metavar="NOM",
                        help="le dossier nommé dont la sortie montre le sort")
    parser.add_argument("--defaire", default=None, metavar="FICHIER",
                        help="rejouer un instantané à l'envers")
    parser.add_argument("--instantane-precedent", default=None, metavar="FICHIER",
                        help="vérifier qu'aucun dossier déjà posé n'est revenu")
    parser.add_argument("--instantane", default=str(DOSSIER_INSTANTANE))
    parser.add_argument("--limite", type=int, default=None, help="borner (mise au point)")
    parser.add_argument("--pas", type=int, default=500, metavar="N")
    args = parser.parse_args(argv)

    from pathlib import Path

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
    from outils.departageur_adresse import concurrents_de, faits_des_dossiers
    from outils.reresolution_neq import _resoudre_une

    portees = PORTEES_DEMANDEES[args.portee]
    session = get_session()
    try:
        if args.defaire:
            return pose_du_neq.defaire(session, Path(args.defaire))

        print("=" * 78)
        print("L'ÉCRITURE DU DÉPARTAGE PAR LE STATUT — élargie aux confirmations")
        print("=" * 78)
        print(f"""
LA DÉCISION D'ALEXANDRE, DU 21 SEPTEMBRE

   FORME   : « {FORME_QUI_SECRIT} »
   PORTÉE  : {args.portee}

   L'exclusion s'écrit AUSSI là où le score désignait déjà un gagnant, à la
   condition stricte que le statut désigne LE MÊME. Le statut ne départage
   plus : il CONFIRME.

⚠️ CE QUI NE CHANGE PAS : LES RESTANTS SOUS LE SOMMET

   Le survivant doit être le candidat LE MIEUX SCORÉ du lot, et SEUL. Un
   survivant moins bien scoré reste EN SUSPENS — les 78 du 20 septembre, et
   tous ceux que l'élargissement fait apparaître. Un départage non écrit se
   reprend; un départage écrit à tort coûte une identité.

⚠️ LA RÉSERVE SUR L'ÉLARGISSEMENT, QUI NE SE LÈVE PAS

   1. La condition ne compare le survivant qu'à ses CONCURRENTS, jamais au
      DOSSIER. Élargie, la règle se lit : « poser le mieux scoré quand tous
      ses concurrents sont radiés ».
   2. L'ADRESSE, elle, compare au dossier — et elle a contredit cet accord
      deux fois dans les paires lues. Elle est rendue ici en COLONNE et en
      COMPTE, JAMAIS en condition.
   3. Le bon candidat peut être ABSENT du lot : resolve_neq_by_name le
      plafonne à CINQ. Vu 2 fois sur 32 paires lues.
   4. UNE ENTREPRISE RADIÉE PEUT ÊTRE LA BONNE. Un signal ancien peut
      désigner une entreprise fermée depuis, et `REQEntry` ne porte AUCUNE
      date de radiation. L'exclusion peut garder le mauvais candidat, et
      rien ne le dirait.

   Les échelles ne bougent pas : seuil {SEUIL_RESOLUTION_CONFIANTE:.0f}, écart {SEUIL_AMBIGUITE_ECART_MIN:.0f}.
""")

        if args.instantane_precedent:
            _verifier_l_instantane_precedent(
                session, Path(args.instantane_precedent))

        requete = select(Company).where(Company.neq.is_(None)).order_by(Company.id)
        if args.limite:
            requete = requete.limit(args.limite)
        restants = list(session.execute(requete).scalars().all())
        if not restants:
            print("   Aucun restant.")
            print("   RIEN N'A ÉTÉ ÉCRIT.")
            return 0

        print(f"… rejeu de la résolution sur {milliers(len(restants))} restants, "
              f"par le chemin de production", flush=True)
        a_poser: list[dict] = []
        pris: list[dict] = []
        suspendus: list[dict] = []
        par_raison: Counter = Counter()
        sous_le_sommet_par_portee: Counter = Counter()
        n_amb = 0
        retenus: dict[int, Company] = {}
        for i, company in enumerate(restants, 1):
            if args.pas and i % args.pas == 0:
                print(f"   … {milliers(i)} / {milliers(len(restants))}", flush=True)
            _neq, matches = _resoudre_une(session, company)
            if famille_de(matches) != "ambigu":
                continue
            n_amb += 1
            concurrents = concurrents_de(matches)
            raison, seul, portee = ce_qui_bloque(matches, concurrents, portees)
            ligne = {
                "company_id": company.id,
                "nom_detecte": company.nom_detecte,
                "_concurrents": concurrents,
                "_raison": raison,
                "portee": portee,
                "score_du_sommet": round(matches[0].score, 1),
            }
            if raison is not None:
                par_raison[raison] += 1
                if raison == SOUS_LE_SOMMET:
                    sous_le_sommet_par_portee[portee] += 1
                ligne["score_restant"] = round(seul.score, 1) if seul else None
                suspendus.append(ligne)
                continue
            retenus[company.id] = company
            detenteur = session.execute(
                select(Company).where(Company.neq == seul.entry.neq)
            ).scalar_one_or_none()
            ligne.update({
                "neq": seul.entry.neq,
                "nom_registre": seul.entry.nom,
                "statut_registre": seul.entry.statut,
                "score": round(seul.score, 1),
                "forme": FORME_QUI_SECRIT,
                "neq_avant": None,
                "statut_avant": getattr(company.statut_resolution, "value", None),
                "champs_avant": pose_du_neq.champs_enrichis(company),
                "_anciennete": (company.first_detected_at.isoformat()
                                if company.first_detected_at else None),
            })
            if detenteur is not None:
                ligne["detenteur_id"] = detenteur.id
                ligne["detenteur_nom"] = detenteur.nom_detecte
                ligne["motif"] = "NEQ déjà porté par un autre dossier"
                pris.append(ligne)
            else:
                a_poser.append(ligne)

        a_poser, collisions, refuses_en_bloc = pose_du_neq.resoudre_les_collisions(
            a_poser, pris)

        # ---- L'ADRESSE, EN COLONNE — une seule lecture des signaux ---------
        # ⚠️ **Jamais une condition.** *Elle est rendue pour être lue avant
        # d'appliquer, parce qu'elle est le seul instrument qui compare le
        # survivant au DOSSIER.*
        par_adresse: Counter = Counter()
        if a_poser:
            faits = faits_des_dossiers(
                session, [retenus[x["company_id"]] for x in a_poser])
            for paire in a_poser:
                verdict = ce_que_ladresse_dit(
                    paire["_concurrents"], faits[paire["company_id"]], paire["neq"])
                paire["adresse"] = verdict
                par_adresse[verdict] += 1

        # ---- CE QUI SE POSE, ET CE QU'ON NE TOUCHE PAS --------------------
        print("\n" + "-" * 78)
        print("1. CE QUI SE POSE, ET CE QU'ON NE TOUCHE PAS")
        print("-" * 78)
        print(f"\n   ambigus rejoués : {milliers(n_amb)}\n")
        print(_ligne_comptee(ETIQUETTES_DU_RAPPORT[0], len(a_poser), n_amb))
        for portee in PORTEES:
            k = sum(1 for x in a_poser if x["portee"] == portee)
            etiquette = (ETIQUETTES_DU_RAPPORT[3] if portee == EGALITE
                         else ETIQUETTES_DU_RAPPORT[4])
            print(_ligne_comptee("   " + etiquette, k, n_amb))
        print(_ligne_comptee(ETIQUETTES_DU_RAPPORT[1], len(pris), n_amb))
        if refuses_en_bloc:
            print(_ligne_comptee(ETIQUETTES_DU_RAPPORT[2], len(refuses_en_bloc)))
        print()
        for raison in RAISONS:
            print(_ligne_comptee(raison, par_raison.get(raison, 0), n_amb))
            if raison == SOUS_LE_SOMMET:
                for portee in PORTEES:
                    etiquette = (ETIQUETTES_DU_RAPPORT[5] if portee == EGALITE
                                 else ETIQUETTES_DU_RAPPORT[6])
                    print(_ligne_comptee(
                        "   " + etiquette,
                        sous_le_sommet_par_portee.get(portee, 0), n_amb))
        print(f"""
   ⛔ LAISSÉS EN SUSPENS, ET NON REFUSÉS : {milliers(len(suspendus))}   (aucun n'a été touché)

   ⚠️ « {SOUS_LE_SOMMET[2:].lstrip()} »
      est la ligne qu'Alexandre laisse en suspens, et l'élargissement ne la
      touche pas. Un départage non écrit se reprend; un départage écrit à
      tort coûte une identité.

   ⚠️ UN OUTIL QUI ÉCRIT UNE PARTIE DOIT DIRE LESQUELS IL N'A PAS TOUCHÉS,
      sinon la différence se lit comme une perte.
""")
        if collisions:
            print(f"   ⚠️ {milliers(len(collisions))} collision(s) de NEQ entre dossiers"
                  " — le plus ancien garde, les autres sont conservés.\n")

        # ---- CE QUE L'ADRESSE EN DIT --------------------------------------
        print("-" * 78)
        print("2. CE QUE L'ADRESSE EN DIT — une COLONNE, jamais une condition")
        print("-" * 78)
        print(f"""
   L'adresse est le seul instrument qui compare le survivant au DOSSIER.
   Elle n'écarte rien ici : elle est comptée pour être lue avant d'appliquer.
""")
        for verdict in VERDICTS_DADRESSE:
            print(_ligne_comptee(verdict, par_adresse.get(verdict, 0), len(a_poser)))
        print()

        _montrer_le_temoin(suspendus, a_poser, args.temoin)

        if args.comparer:
            for portee in PORTEES:
                _montrer([x for x in a_poser if x["portee"] == portee],
                         args.depuis, args.comparer,
                         f"CE QUI SERAIT ÉCRIT — {portee}")
        if args.suspendus:
            tranche = suspendus[args.depuis: args.depuis + args.suspendus]
            print("\n" + "=" * 78)
            print(f"LES DOSSIERS EN SUSPENS — {args.depuis + 1} à "
                  f"{args.depuis + len(tranche)} sur {milliers(len(suspendus))}")
            print("=" * 78)
            for ligne in tranche:
                print(f"\n   #{ligne['company_id']}   "
                      f"{(ligne['nom_detecte'] or '')[:54]}")
                print(f"      ⛔ {ligne['_raison']}")
                for m in ligne["_concurrents"]:
                    print(f"        {m.score:>6.1f}  {m.entry.neq}  "
                          f"{(m.entry.nom or '')[:34]:<36} [{m.entry.statut}]")

        if not args.appliquer:
            print("=" * 78)
            print("   RAPPORT SEUL — rien n'a été écrit.")
            print("   Relancer avec --appliquer pour poser les NEQ.")
            print("=" * 78)
            return 0

        if not a_poser and not pris:
            print("\n   Rien à appliquer.")
            return 0

        chemin = pose_du_neq.ecrire_instantane(args.instantane, "statut", {
            "forme": FORME_QUI_SECRIT,
            "portee": args.portee,
            "a_poser": [pose_du_neq.sans_champs_de_travail(x) for x in a_poser],
            "conserves": [pose_du_neq.sans_champs_de_travail(x) for x in pris],
        })
        if chemin is None:
            return 3
        print(f"\n   instantané d'avant : {chemin}")

        poses, tardifs = pose_du_neq.poser_les_neq(session, a_poser, pris)
        journalises, deja = pose_du_neq.journaliser_les_conserves(
            session, pris, "Départage par le statut refusé")
        session.commit()

        print(f"\n   NEQ posés                  : {milliers(poses)}")
        if tardifs:
            print(f"   pris entre le rapport et l'écriture : {milliers(tardifs)}")
        print(f"   rapprochements journalisés : {milliers(journalises)}")
        if deja:
            print(f"   déjà au journal            : {milliers(deja)}")
        print(f"   ⛔ laissés en suspens        : {milliers(len(suspendus))}"
              "   (aucun n'a été touché)")
        print("\n" + "=" * 78)
        print(f"   Pour défaire : --defaire {chemin}")
        print("=" * 78)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
