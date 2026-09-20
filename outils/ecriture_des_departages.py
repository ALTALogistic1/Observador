#!/usr/bin/env python3
"""Écrire les départages de l'adresse — **restreints au CODE POSTAL COMPLET.**

**La décision qui l'écrit** *(Alexandre, 2026-09-19, après relecture de 50 paires
sur 292)*. Le départageur d'adresse sépare **2 032** ambigus à ses trois niveaux.
**On n'en écrit que 1 764** — ceux que le **code postal complet** a tranchés.

## Pourquoi le niveau décide, et pas le score

Un **code complet** désigne un immeuble, parfois un côté de rue. *Deux
entreprises qui le partagent sont voisines ou à la même adresse.* Une **région de
tri** couvre une ville entière :

```
KONE INC.        tranché par : région de tri
   au dossier    : '6775, Financial Dr, Suite 100, ON L5N0A4'   comparé sur ['L5N']
 × 1172439623  KONE INC.                ville='Montréal'      complet=H4S1Y4
 → 1144414308  DROLET KONE ELEVATORS    ville='Mississauga'   complet=L5N7J6
```

> ⚠️ **`L5N` ne dit que « quelque part à Mississauga ».** *Le fait ne retient pas
> ce candidat parce que l'autre est exclu par une adresse — il le retient parce
> qu'il est dans la même ville.* **C'est de la ville, sous un nom qui ne le dit
> pas.**

**Sur les 50 relues, environ 8 % sont douteux, et les cas de région de tri en
sont.**

## ⚠️ Les 268 ne sont pas REFUSÉS : ils sont EN SUSPENS

*Un départage non écrit ne coûte rien qu'on ne puisse reprendre; un départage
écrit à tort coûte une identité.* **La restriction se trompe dans le bon sens.**

**Ce qui les débloquerait est l'activité économique** — *elle distinguerait un
`KONE` d'ascenseurs d'un autre.* **Chantier 22.**

⚠️ **Et un outil qui écrit 1 764 sur 2 032 doit dire lesquels il n'a pas
touchés**, sinon la différence se lit comme une perte. *Ils sont comptés,
ventilés par niveau, et `--suspendus N` les montre un par un.*

## Ce qui ne change pas de la passe de reprise

**La machinerie d'écriture est EMPRUNTÉE** *(`outils/pose_du_neq.py`)* : le même
instantané, la même conservation, le même refus au-delà de deux prétendants, la
même re-vérification au moment de poser, le même `--defaire`. ⚠️ *Recopier une
règle de conservation sur un chemin d'écriture perdrait une identité que
l'instantané de l'autre copie ne rendrait pas.*

⚠️ **Un départage ÉCARTE un candidat; il n'en CONFIRME aucun.** *Les cas douteux
qui restent dans les 1 764 — `SDI CANADA` → `BIOMEDSHIELD`, `ENVIRO CONNEXIONS`
→ `ENTREPRISE SANITAIRE F.A.` — sont des questions d'ENTITÉ (filiale,
successeure), pas des erreurs de localisation.* **Et la conservation les couvre :
le NEQ est posé, rien n'est supprimé, l'instantané permet de défaire.**

⚠️ **Les échelles ne bougent pas : seuil 92, écart 8.**

Usage, SUR L'HÔTE :
    python3 -m outils.ecriture_des_departages                      # rapport seul
    python3 -m outils.ecriture_des_departages --comparer 50        # les paires à poser
    python3 -m outils.ecriture_des_departages --suspendus 50       # celles qu'on ne pose PAS
    python3 -m outils.ecriture_des_departages --appliquer
    python3 -m outils.ecriture_des_departages --defaire /var/lib/falkye/departages-….json
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from outils import pose_du_neq
from outils.departageur_adresse import (
    NIVEAU_CODE_COMPLET,
    NOMS_DES_NIVEAUX,
    PasUnAmbigu,
    champs_des_dossiers,
    departager_le_dossier,
    faits_des_dossiers,
    faits_du_candidat,
)
from outils.nombres import milliers

#: ⚠️ **Le seul niveau dont les départages s'écrivent.** *Décision d'Alexandre du
#: 19 septembre, sur relecture de paires — pas un réglage.* **Les autres niveaux
#: continuent de départager; c'est l'ÉCRITURE qui est restreinte, pas le
#: départageur.**
NIVEAU_QUI_SECRIT = NIVEAU_CODE_COMPLET

#: Où l'instantané d'avant est déposé — le seul répertoire que les unités peuvent
#: écrire (`ReadWritePaths=/var/lib/falkye`).
#: ⚠️ **Empruntée à `outils/pose_du_neq.py`, plus recopiée** — elle y vit
#: près du geste qu'elle gouverne. *Le nom est conservé ici pour les
#: appelants.*
DOSSIER_INSTANTANE = pose_du_neq.DOSSIER_INSTANTANE


def _part(k: int, n: int) -> str:
    return f"{100 * k / n:.1f} %" if n else "—"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--appliquer", action="store_true",
                        help="ÉCRIRE (défaut : rapport seul, aucune écriture)")
    parser.add_argument("--comparer", type=int, default=0, metavar="N",
                        help="montrer N paires À POSER")
    parser.add_argument("--suspendus", type=int, default=0, metavar="N",
                        help="montrer N départages LAISSÉS EN SUSPENS, et pourquoi")
    parser.add_argument("--depuis", type=int, default=0, metavar="K")
    parser.add_argument("--defaire", default=None, metavar="FICHIER",
                        help="rejouer un instantané à l'envers")
    parser.add_argument("--limite", type=int, default=None, help="borner (mise au point)")
    parser.add_argument("--instantane", default=str(DOSSIER_INSTANTANE))
    args = parser.parse_args(argv)

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
    )

    session = get_session()
    try:
        if args.defaire:
            return pose_du_neq.defaire(session, Path(args.defaire))

        print("=" * 78)
        print("ÉCRIRE LES DÉPARTAGES — RESTREINTS AU CODE POSTAL COMPLET")
        print("=" * 78)
        print(f"""
⚠️ CE QUE CET OUTIL NE FERA PAS — à lire avant tout chiffre

   IL N'ÉCRIT QUE LES DÉPARTAGES DU CODE POSTAL COMPLET. Un code complet
   désigne un immeuble, parfois un côté de rue. Une région de tri couvre une
   ville entière — `L5N` ne dit que « quelque part à Mississauga ».

   LES AUTRES NE SONT PAS REFUSÉS, ILS SONT EN SUSPENS. Un départage non
   écrit se reprend; un départage écrit à tort coûte une identité. Ce qui les
   débloquerait est l'activité économique — chantier 22.

   IL NE FUSIONNE JAMAIS. Un NEQ déjà pris n'est pas posé : le rapprochement
   est journalisé, les deux dossiers restent.

   UN DÉPARTAGE ÉCARTE UN CANDIDAT; IL N'EN CONFIRME AUCUN.

   Seuil {SEUIL_RESOLUTION_CONFIANTE:.0f}, écart {SEUIL_AMBIGUITE_ECART_MIN:.0f}
   — inchangés, et cet outil n'existe pas pour les rouvrir.
""")

        requete = select(Company).where(Company.neq.is_(None)).order_by(Company.id)
        if args.limite:
            requete = requete.limit(args.limite)
        orphelins = list(session.execute(requete).scalars().all())

        from falkye.sources import req as req_source

        # ---- La population, puis le départage ------------------------------
        ambigus: list[tuple] = []
        for i, company in enumerate(orphelins):
            if i and i % 500 == 0:
                print(f"   … {milliers(i)} examinés", flush=True)
            matches = req_source.resolve_neq_by_name(
                session, company.nom_detecte, ville=company.ville
            )
            ambigus.append((company, matches))

        champs = champs_des_dossiers(session, {c.id for c, _ in ambigus})
        adresses = faits_des_dossiers(
            session, [c for c, _ in ambigus], champs=champs
        )

        a_poser: list[dict] = []
        pris: list[dict] = []
        suspendus: list[tuple] = []
        par_niveau: Counter = Counter()
        for company, matches in ambigus:
            try:
                departage, concurrents = departager_le_dossier(
                    matches, adresses[company.id]
                )
            except PasUnAmbigu:
                # ⚠️ **La garde de la non-régression, à sa place.** *Un dossier
                # que le NOM a déjà tranché n'est pas de cette passe* — c'est la
                # passe de reprise qui le pose.
                continue
            if not departage.prononce:
                continue
            par_niveau[departage.niveau] += 1
            gagnant = concurrents[departage.gagnant]
            ligne = (company, departage, concurrents, gagnant)
            if departage.niveau != NIVEAU_QUI_SECRIT:
                suspendus.append(ligne)
                continue
            detenteur = session.execute(
                select(Company).where(Company.neq == gagnant.entry.neq)
            ).scalar_one_or_none()
            paire = {
                "company_id": company.id,
                "nom_detecte": company.nom_detecte,
                "neq": gagnant.entry.neq,
                "nom_registre": gagnant.entry.nom,
                "score": round(gagnant.score, 1),
                "niveau": departage.niveau,
                "neq_avant": None,
                "statut_avant": getattr(company.statut_resolution, "value", None),
                "champs_avant": pose_du_neq.champs_enrichis(company),
                "_anciennete": (
                    company.first_detected_at.isoformat()
                    if company.first_detected_at else None
                ),
                "_departage": departage,
                "_concurrents": concurrents,
            }
            if detenteur is not None:
                paire["detenteur_id"] = detenteur.id
                paire["detenteur_nom"] = detenteur.nom_detecte
                paire["motif"] = "NEQ déjà porté par un autre dossier"
                pris.append(paire)
            else:
                a_poser.append(paire)

        a_poser, collisions, refuses_en_bloc = pose_du_neq.resoudre_les_collisions(
            a_poser, pris)

        # ---- CE QUI SE POSE, ET CE QU'ON NE TOUCHE PAS ----------------------
        separes = sum(par_niveau.values())
        print("-" * 78)
        print("1. CE QUI SE POSE, ET CE QU'ON NE TOUCHE PAS")
        print("-" * 78)
        print(f"\n   {'niveau qui a tranché':<46} {'dossiers':>9} {'':>12}")
        for nom in NOMS_DES_NIVEAUX:
            k = par_niveau.get(nom, 0)
            marque = "→ à écrire" if nom == NIVEAU_QUI_SECRIT else "→ EN SUSPENS"
            print(f"   {nom:<46} {milliers(k):>9}   {marque}")
        print(f"   {'⇒ séparés par l adresse':<46} {milliers(separes):>9}")
        print(f"\n   {'⛔ LAISSÉS EN SUSPENS':<46} {milliers(len(suspendus)):>9} "
              f"{_part(len(suspendus), separes):>8}")
        print("      *Ils ne sont pas refusés. Un départage non écrit se reprend;")
        print("       un départage écrit à tort coûte une identité.*")
        print("      Ce qui les débloquerait : l'activité économique — chantier 22.")

        print(f"\n   {'NEQ à poser, NEQ LIBRE':<46} {milliers(len(a_poser)):>9}")
        if collisions:
            en_trop = sum(len(v) for v in collisions.values()) - len(collisions)
            print(f"   {'dont COLLISIONS dans le lot':<46} "
                  f"{milliers(len(collisions)):>9} NEQ, {en_trop} écarté(s)")
        if refuses_en_bloc:
            total = sum(refuses_en_bloc.values())
            print(f"   {'⛔ REFUSÉS EN BLOC':<46} {milliers(len(refuses_en_bloc)):>9} "
                  f"NEQ, {total} dossier(s)")
            print("      Au-delà de deux prétendants, le nombre est une preuve CONTRE")
            print("      l'appariement — l'ancienneté n'y a aucun sens.")
        print(f"   {'NEQ à poser, DÉJÀ PRIS':<46} {milliers(len(pris)):>9}"
              "   (conservés, jamais fusionnés)")

        # ---- LES PAIRES ------------------------------------------------------
        if args.comparer:
            _montrer(a_poser[args.depuis: args.depuis + args.comparer],
                     args.depuis, len(a_poser), "LES PAIRES À POSER")
        if args.suspendus:
            print("\n" + "=" * 78)
            lot = suspendus[args.depuis: args.depuis + args.suspendus]
            print(f"LES DÉPARTAGES EN SUSPENS — {args.depuis + 1} à "
                  f"{args.depuis + len(lot)} sur {milliers(len(suspendus))}")
            print("=" * 78)
            print("\n⚠️ Ceux-là ne seront PAS écrits. *Les lire est ce qui dira si la")
            print("   restriction laisse dehors des cas nets* — 50 paires sur 292 ne")
            print("   disent pas où les douteux tombent dossier par dossier.\n")
            for company, departage, concurrents, gagnant in lot:
                faits = adresses[company.id]
                du_dossier = faits.de_niveau(departage.niveau)
                print(f"   ── {(company.nom_detecte or '')[:60]}")
                print(f"      tranché par : {departage.niveau}   ⛔ non écrit")
                print(f"      au dossier  : {(du_dossier.brut or '')[:66]!r}")
                print(f"      comparé sur : {sorted(du_dossier.formes)[:4]}")
                for rang, m in enumerate(concurrents):
                    fc = faits_du_candidat(m.entry)
                    marque = "→" if rang == departage.gagnant else "×"
                    print(f"      {marque} {m.entry.neq}  {m.score:>6.2f}  "
                          f"{(m.entry.nom or '')[:32]:<34} "
                          f"ville={(m.entry.ville or '—')[:18]!r:<20} "
                          f"complet={_formes(fc.code_complet)}")
                print()

        if not args.appliquer:
            print("=" * 78)
            print("   RAPPORT SEUL — rien n'a été écrit.")
            print("   Relancer avec --appliquer pour poser les NEQ du code complet.")
            print("=" * 78)
            return 0

        if not a_poser and not pris:
            print("\n   Rien à appliquer.")
            return 0

        chemin = pose_du_neq.ecrire_instantane(args.instantane, "departages", {
            "a_poser": [pose_du_neq.sans_champs_de_travail(x) for x in a_poser],
            "conserves": [pose_du_neq.sans_champs_de_travail(x) for x in pris],
        })
        if chemin is None:
            return 3
        print(f"\n   instantané d'avant : {chemin}")

        poses, tardifs = pose_du_neq.poser_les_neq(session, a_poser, pris)
        journalises, deja = pose_du_neq.journaliser_les_conserves(
            session, pris, "Départage d'adresse refusé")
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


def _formes(fait) -> str:
    return ",".join(sorted(fait.formes)[:2]) if fait is not None else "—"


def _montrer(lot: list[dict], depuis: int, total: int, titre: str) -> None:
    print("\n" + "=" * 78)
    print(f"{titre} — {depuis + 1} à {depuis + len(lot)} sur {milliers(total)}")
    print("=" * 78)
    print("\n⚠️ Lire le NOM DU REGISTRE contre le NOM DÉTECTÉ, et le code complet")
    print("   des DEUX côtés. *Un départage écarte un candidat; il n'en confirme")
    print("   aucun.*\n")
    for p in lot:
        departage, concurrents = p["_departage"], p["_concurrents"]
        print(f"   #{p['company_id']}  {p['neq']}   score {p['score']:.1f}"
              f"   tranché par {departage.niveau}")
        print(f"      détecté  : {p['nom_detecte']}")
        print(f"      registre : {p['nom_registre']}")
        for rang, m in enumerate(concurrents):
            fc = faits_du_candidat(m.entry)
            marque = "→" if rang == departage.gagnant else "×"
            print(f"      {marque} {m.entry.neq}  {m.score:>6.2f}  "
                  f"{(m.entry.nom or '')[:32]:<34} "
                  f"complet={_formes(fc.code_complet)}")
        print()


if __name__ == "__main__":
    raise SystemExit(main())
