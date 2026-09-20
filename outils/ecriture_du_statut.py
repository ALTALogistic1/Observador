#!/usr/bin/env python3
"""L'écriture du départage par le STATUT — restreinte aux égalités strictes.

## La décision d'Alexandre, en trois points

**La FORME : « n'écarter que les radiées ».** *Elle garde les 39 dossiers à
candidat `ni`, dont 32 où ce candidat est le mieux scoré* — les entités publiques
des paires. **L'autre forme ne rendait que 16 dossiers de plus.**

**La PORTÉE : les égalités strictes seulement.** *C'est la population où le nom a
fini son travail.*

**EN SUSPENS, et non refusés** : les **78** dossiers où le restant est moins bien
scoré que le meilleur, dont **49** sur le couple `100 contre 95`. *Deux
instruments s'y contredisent, et rien ne dit lequel a raison.* **Un départage non
écrit se reprend; un départage écrit à tort coûte une identité.**

## ⚠️ UNE RÉSERVE SUR LA PORTÉE, VÉRIFIÉE EN EXÉCUTANT LE CODE

**« Les égalités strictes » et « le statut ne contredit aucun gagnant » ne sont
PAS la même population.** *Contre-exemple, produit et exécuté avant d'écrire une
ligne :*

    candidats : radiée 100,0 · radiée 100,0 · immatriculée 95,0
    → égalité stricte au sommet : OUI (deux candidats à 100)
    → le restant après exclusion : 95,0 — SOUS le sommet

⚠️ **Un dossier peut donc être une égalité stricte ET voir le statut retenir un
candidat sous les premiers ex æquo** — exactement le cas laissé en suspens.
*Restreindre aux seules égalités strictes ne l'exclurait pas.*

**Donc l'écriture applique DEUX conditions, pas une :**

1. **égalité stricte** — au moins deux candidats au score du sommet;
2. **le restant est PARMI les premiers ex æquo** — jamais en dessous.

*La seconde est ce qui réalise « le statut ne contredit aucun gagnant ».* **Sans
elle, une partie des 78 serait écrite malgré la décision.**

## ⚠️ LA RÉSERVE QUI NE SE LÈVE PAS

**Une entreprise radiée peut être la bonne.** *Un signal ancien peut désigner une
entreprise fermée depuis, et `REQEntry` ne porte AUCUNE date de radiation.*
**L'exclusion peut garder le mauvais candidat, et rien ne le dirait.**

## La forme du 19 septembre

*Rapport par défaut*, `--appliquer` sur demande explicite, **instantané écrit
AVANT le commit** avec `neq_avant` et `statut_avant`, `--defaire` pour revenir.
**Un NEQ déjà pris n'est pas posé** : le rapprochement est journalisé et **les
deux dossiers restent**. **Refus au-delà de deux prétendants.**

⚠️ **Et la restriction est dite dans la sortie** — *combien sont posés, combien
sont laissés en suspens et POURQUOI.* **Un outil qui écrit une partie doit dire
lesquels il n'a pas touchés, sinon la différence se lit comme une perte.**

⚠️ **Les échelles ne bougent pas : seuil 92, écart 8.**

Usage, SUR L'HÔTE :
    python3 -m outils.ecriture_du_statut                       # rapport seul
    python3 -m outils.ecriture_du_statut --comparer 30         # ce qui SERAIT écrit
    python3 -m outils.ecriture_du_statut --suspendus 40        # ce qu'on ne pose PAS
    python3 -m outils.ecriture_du_statut --appliquer
    python3 -m outils.ecriture_du_statut --defaire FICHIER.json
"""
from __future__ import annotations

import argparse
from collections import Counter

from outils import pose_du_neq
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

#: Les raisons de laisser en suspens, **dans l'ordre où elles se lisent.**
#: ⚠️ *Chacune est un RÉSULTAT* : « le lot est vide » et « le restant est sous le
#: sommet » appellent deux suites différentes.
PAS_UNE_EGALITE = "pas une égalité stricte — le score désignait un gagnant"
LOT_VIDE = "l'exclusion vide le lot — tous les candidats sont radiés"
PAS_UN_SEUL = "l'exclusion laisse PLUSIEURS candidats"
SOUS_LE_SOMMET = "⚠️ le restant est SOUS les premiers ex æquo — deux instruments se contredisent"
RAISONS = (PAS_UNE_EGALITE, SOUS_LE_SOMMET, PAS_UN_SEUL, LOT_VIDE)

#: La largeur de la colonne des raisons. ⚠️ *Une étiquette plus longue que sa
#: colonne pousse le nombre* — cinquième occurrence évitée, pas corrigée.
LARGEUR_DUNE_RAISON = max(len(r) for r in RAISONS) + 1


def ce_qui_bloque(matches, concurrents) -> tuple[str | None, object]:
    """`(raison ou None, restant)` — **les DEUX conditions, dans l'ordre.**

    ⚠️ *La seconde condition n'est pas redondante avec la première* : une
    égalité stricte au sommet entre deux radiées laisse un restant SOUS le
    sommet, et c'est exactement le cas qu'Alexandre laisse en suspens.
    """
    if len(ex_aequo(matches)) < 2:
        return PAS_UNE_EGALITE, None
    restes = restants_apres(concurrents, FORME_QUI_SECRIT)
    if not restes:
        return LOT_VIDE, None
    if len(restes) > 1:
        return PAS_UN_SEUL, None
    seul = restes[0]
    if seul.score < matches[0].score:
        return SOUS_LE_SOMMET, seul
    return None, seul


def _part(k: int, n: int) -> str:
    return f"{100 * k / n:.1f} %" if n else "—"


def _montrer(lot: list[dict], depuis: int, combien: int, titre: str) -> None:
    """Des paires ENTIÈRES — **de ce qui serait ÉCRIT**, jamais de ce qui est
    départageable. ⚠️ *Ce n'est pas la même population, et c'est la lecture qui
    décide.*"""
    tranche = lot[depuis: depuis + combien]
    print("\n" + "=" * 78)
    print(f"{titre} — {depuis + 1} à {depuis + len(tranche)} sur {milliers(len(lot))}")
    print("=" * 78)
    for paire in tranche:
        print(f"\n   #{paire['company_id']}   {(paire['nom_detecte'] or '')[:54]}")
        print(f"      → {paire['neq']}  {paire['score']:>6.1f}  "
              f"{(paire['nom_registre'] or '')[:40]}   [{paire['statut_registre']}]")
        for m in paire["_concurrents"]:
            marque = "→" if m.entry.neq == paire["neq"] else "×"
            print(f"      {marque} {m.entry.neq}  {m.score:>6.1f}  "
                  f"{(m.entry.nom or '')[:34]:<36} [{m.entry.statut}]  "
                  f"{(m.entry.ville or '—')[:16]}")
        if paire.get("motif"):
            print(f"      ⛔ {paire['motif']}"
                  f"  (dossier #{paire.get('detenteur_id')})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--appliquer", action="store_true",
                        help="ÉCRIRE (défaut : rapport seul, aucune écriture)")
    parser.add_argument("--comparer", type=int, default=0, metavar="N",
                        help="montrer N paires de ce qui SERAIT ÉCRIT")
    parser.add_argument("--suspendus", type=int, default=0, metavar="N",
                        help="montrer N dossiers LAISSÉS EN SUSPENS, et pourquoi")
    parser.add_argument("--depuis", type=int, default=0, metavar="K")
    parser.add_argument("--defaire", default=None, metavar="FICHIER",
                        help="rejouer un instantané à l'envers")
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
    from outils.departageur_adresse import concurrents_de
    from outils.reresolution_neq import _resoudre_une

    session = get_session()
    try:
        if args.defaire:
            return pose_du_neq.defaire(session, Path(args.defaire))

        print("=" * 78)
        print("L'ÉCRITURE DU DÉPARTAGE PAR LE STATUT — égalités strictes seulement")
        print("=" * 78)
        print(f"""
LA DÉCISION D'ALEXANDRE

   FORME   : « {FORME_QUI_SECRIT} »
   PORTÉE  : les ÉGALITÉS STRICTES seulement.

⚠️ ET UNE SECONDE CONDITION, QUI N'EST PAS REDONDANTE AVEC LA PREMIÈRE

   Une égalité stricte au sommet entre DEUX RADIÉES laisse un restant SOUS
   le sommet — vérifié en exécutant le code. Restreindre aux seules
   égalités strictes n'exclurait donc PAS les dossiers où le statut
   contredit le score. L'écriture exige les deux :

     1. au moins deux candidats au score du sommet;
     2. le restant est PARMI eux, jamais en dessous.

⚠️ LA RÉSERVE QUI NE SE LÈVE PAS

   UNE ENTREPRISE RADIÉE PEUT ÊTRE LA BONNE. Un signal ancien peut
   désigner une entreprise fermée depuis, et `REQEntry` ne porte AUCUNE
   date de radiation. L'exclusion peut garder le mauvais candidat, et rien
   ne le dirait.

   Les échelles ne bougent pas : seuil {SEUIL_RESOLUTION_CONFIANTE:.0f}, écart {SEUIL_AMBIGUITE_ECART_MIN:.0f}.
""")

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
        n_amb = 0
        for i, company in enumerate(restants, 1):
            if args.pas and i % args.pas == 0:
                print(f"   … {milliers(i)} / {milliers(len(restants))}", flush=True)
            _neq, matches = _resoudre_une(session, company)
            if famille_de(matches) != "ambigu":
                continue
            n_amb += 1
            concurrents = concurrents_de(matches)
            raison, seul = ce_qui_bloque(matches, concurrents)
            ligne = {
                "company_id": company.id,
                "nom_detecte": company.nom_detecte,
                "_concurrents": concurrents,
                "_raison": raison,
                "score_du_sommet": round(matches[0].score, 1),
            }
            if raison is not None:
                par_raison[raison] += 1
                ligne["score_restant"] = round(seul.score, 1) if seul else None
                suspendus.append(ligne)
                continue
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

        # ---- CE QUI SE POSE, ET CE QU'ON NE TOUCHE PAS --------------------
        print("\n" + "-" * 78)
        print("1. CE QUI SE POSE, ET CE QU'ON NE TOUCHE PAS")
        print("-" * 78)
        print(f"\n   ambigus rejoués : {milliers(n_amb)}\n")
        print(f"   {'✅ À POSER — les deux conditions tenues':<{LARGEUR_DUNE_RAISON}} "
              f"{milliers(len(a_poser)):>9} {_part(len(a_poser), n_amb):>8}")
        print(f"   {'⛔ NEQ déjà porté — conservé et journalisé':<{LARGEUR_DUNE_RAISON}} "
              f"{milliers(len(pris)):>9} {_part(len(pris), n_amb):>8}")
        if refuses_en_bloc:
            print(f"   {'⛔ refusés — plus de deux prétendants':<{LARGEUR_DUNE_RAISON}} "
                  f"{milliers(len(refuses_en_bloc)):>9}")
        print()
        for raison in RAISONS:
            k = par_raison.get(raison, 0)
            print(f"   {raison:<{LARGEUR_DUNE_RAISON}} {milliers(k):>9} "
                  f"{_part(k, n_amb):>8}")
        print(f"""
   ⛔ LAISSÉS EN SUSPENS, ET NON REFUSÉS : {milliers(len(suspendus))}   (aucun n'a été touché)

   ⚠️ « {SOUS_LE_SOMMET[2:]} »
      est la ligne qu'Alexandre a mise en suspens. Un départage non écrit
      se reprend; un départage écrit à tort coûte une identité.

   ⚠️ UN OUTIL QUI ÉCRIT UNE PARTIE DOIT DIRE LESQUELS IL N'A PAS TOUCHÉS,
      sinon la différence se lit comme une perte.
""")
        if collisions:
            print(f"   ⚠️ {milliers(len(collisions))} collision(s) de NEQ entre dossiers"
                  " — le plus ancien garde, les autres sont conservés.\n")

        if args.comparer:
            _montrer(a_poser, args.depuis, args.comparer,
                     "CE QUI SERAIT ÉCRIT")
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
            print("   Relancer avec --appliquer pour poser les NEQ des égalités.")
            print("=" * 78)
            return 0

        if not a_poser and not pris:
            print("\n   Rien à appliquer.")
            return 0

        chemin = pose_du_neq.ecrire_instantane(args.instantane, "statut", {
            "forme": FORME_QUI_SECRIT,
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
