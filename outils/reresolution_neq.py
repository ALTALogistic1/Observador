#!/usr/bin/env python3
"""Reprend les entreprises sans NEQ que le chemin de résolution résout MAINTENANT.

**Le fait qui a écrit cet outil** *(2026-09-16)*. Le miroir porte 1 505 879 noms
qu'il ne portait pas, et la borne qui empêchait le pont d'être emprunté est
levée. Le diagnostic passe de **313 à 804 « résolubles maintenant »**.

⚠️ **Mais rien ne les reprend.** `generer_notifications` n'appelle jamais
`resolve_company` : *une entreprise qui a échoué une fois n'est jamais
réessayée*, quel que soit ce qui a changé dans le miroir depuis. C'est le cercle
noté en N36. **Cet outil est la porte de sortie du cercle**, et il est explicite
plutôt qu'automatique : *un mécanisme automatique ne doit pas interrompre le
travail; un geste humain mal formé, si.*

## Ce qu'il fait, et ce qu'il refuse de faire

Pour chaque `Company` sans NEQ, il rejoue **le chemin de production** —
`resolve_neq_by_name` puis `neq_retenu`, jamais une règle recopiée — et classe :

- **LIBRE** : le NEQ n'appartient à aucun autre dossier → il est posé.
- ⚠️ **PRIS** : le NEQ appartient DÉJÀ à un autre dossier → **rien n'est
  touché.** Le rapprochement est *journalisé* comme candidat de fusion, à
  examiner par un humain.
- **NON RÉSOLU** : aucun NEQ retenu → inchangé.

**CONSERVATION, JAMAIS FUSION** *(décision d'Alexandre, 2026-09-16)*. `Company.
neq` est `unique=True` : poser un NEQ déjà pris est impossible, et le chemin
« naturel » serait de fusionner les deux dossiers. **On ne fusionne pas.** *Deux
dossiers séparés se fusionnent plus tard; deux dossiers fusionnés ne se séparent
pas.* La conservation coûte un doublon visible; la fusion coûte une histoire
perdue, en silence.

## Trois gardes avant le premier octet écrit

1. **Le rapport est le mode par DÉFAUT.** Écrire demande `--appliquer`.
2. **`--comparer N` montre les paires** — nom détecté contre nom du registre,
   score, second, et par où le candidat est arrivé. *La dernière vérification
   avant un geste irréversible se fait sur des paires, pas sur un total.*
3. **Un instantané JSON est écrit AVANT le commit**, avec l'état d'avant de
   chaque dossier touché. ⚠️ *Sans lui, « reversible » est une intention.*

Usage, SUR L'HÔTE :
    python3 -m outils.reresolution_neq --comparer 20      # ne touche à rien
    python3 -m outils.reresolution_neq --appliquer
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

#: Où l'instantané d'avant est déposé. Le même répertoire que les témoins et le
#: miroir — le seul que les unités peuvent écrire (`ReadWritePaths`).
DOSSIER_INSTANTANE = Path("/var/lib/falkye")


def _sans_champs_de_travail(paire: dict) -> dict:
    """La paire sans ses champs de calcul (préfixés `_`).

    *L'instantané porte l'état d'AVANT, ce qui suffit à défaire le geste* — y
    mêler les intermédiaires de décision rendrait son format dépendant de la
    façon dont la passe raisonne ce jour-là.
    """
    return {k: v for k, v in paire.items() if not k.startswith("_")}


def _resoudre_une(db_session, company) -> tuple[str | None, list]:
    """`(neq retenu ou None, matches)` — **par le chemin de production**.

    *Une règle de décision recopiée mesurerait sa propre copie* : `neq_retenu`
    est la fonction que le produit appelle, extraite exprès pour ça.
    """
    from falkye.resolution import neq_retenu
    from falkye.sources import req as req_source

    matches = req_source.resolve_neq_by_name(
        db_session, company.nom_detecte, ville=company.ville
    )
    return neq_retenu(matches), matches


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--appliquer", action="store_true",
                        help="ÉCRIRE (défaut : rapport seul, aucune écriture)")
    parser.add_argument("--comparer", type=int, default=0, metavar="N",
                        help="montrer N paires « nom détecté / nom du registre »")
    parser.add_argument("--limite", type=int, default=None,
                        help="n'examiner que les N premières (mise au point)")
    parser.add_argument("--instantane", default=str(DOSSIER_INSTANTANE),
                        help="où déposer l'instantané d'avant")
    args = parser.parse_args(argv)

    from sqlalchemy import select

    from falkye.db import refuser_si_cible_non_choisie

    code = refuser_si_cible_non_choisie()
    if code:
        return code

    from falkye.db import get_session
    from falkye.models.company import Company, StatutResolution

    print("=" * 78)
    print("REPRISE DES ENTREPRISES SANS NEQ")
    print("=" * 78)
    print("\nMODE    :", "⚠️ ÉCRITURE" if args.appliquer else "rapport seul, aucune écriture")
    print("RÈGLE   : CONSERVATION, jamais fusion. Un NEQ déjà pris n'est pas posé;")
    print("          le rapprochement est journalisé pour examen humain.")
    print()

    session = get_session()
    try:
        requete = select(Company).where(Company.neq.is_(None)).order_by(Company.id)
        if args.limite:
            requete = requete.limit(args.limite)
        entreprises = list(session.execute(requete).scalars().all())
        print(f"   entreprises sans NEQ : {len(entreprises)}")

        libres: list[dict] = []
        pris: list[dict] = []
        non_resolues = 0

        for company in entreprises:
            neq, matches = _resoudre_une(session, company)
            if neq is None:
                non_resolues += 1
                continue
            top = matches[0]
            detenteur = session.execute(
                select(Company).where(Company.neq == neq)
            ).scalar_one_or_none()
            paire = {
                "company_id": company.id,
                "nom_detecte": company.nom_detecte,
                "ville": company.ville,
                "neq": neq,
                "nom_registre": top.entry.nom,
                "score": round(top.score, 1),
                "second": round(matches[1].score, 1) if len(matches) > 1 else 0.0,
                "candidats": len(matches),
                # L'état d'AVANT, pour que l'instantané soit réversible.
                "neq_avant": None,
                "statut_avant": getattr(company.statut_resolution, "value", None),
                # Sert à départager une collision interne au lot. Préfixé `_`
                # parce qu'il est retiré avant l'écriture de l'instantané : ce
                # fichier porte l'état d'avant, pas les intermédiaires de calcul.
                "_anciennete": (
                    company.first_detected_at.isoformat()
                    if company.first_detected_at else None
                ),
            }
            if detenteur is not None:
                paire["detenteur_id"] = detenteur.id
                paire["detenteur_nom"] = detenteur.nom_detecte
                pris.append(paire)
            else:
                libres.append(paire)

        # --- LES COLLISIONS À L'INTÉRIEUR DU LOT ------------------------------
        # ⚠️ **Le défaut du 2026-09-16, 19 h 03.** La disponibilité était vérifiée
        # contre les dossiers EXISTANTS, jamais contre ce que la passe elle-même
        # allait poser. *Deux dossiers du lot visant le même NEQ libre : le
        # premier le prend, le second viole `UNIQUE(companies.neq)`* — et la
        # transaction entière est annulée, donc **rien** n'est posé.
        #
        # Le rapport le laissait voir : 69 NEQ déjà pris, tous des doublons de
        # graphie (« Annexair inc. » contre « Annexair Inc »). *Si la base porte
        # déjà ces doublons, le lot en porte aussi* — mais personne ne l'avait lu
        # ainsi.
        #
        # **Résolu ICI, avant l'affichage, et pas au moment de poser.** Le
        # premier arrivé serait un ordre d'itération, donc un tirage — et
        # `ORDER BY` a été posé ce matin précisément pour qu'un geste
        # irréversible ne dépende pas d'un tirage. Ici la règle est nommée, elle
        # est visible dans `--comparer`, et elle rend la même chose à chaque
        # exécution.
        par_neq: dict[str, list[dict]] = {}
        for paire in libres:
            par_neq.setdefault(paire["neq"], []).append(paire)

        collisions = {neq: v for neq, v in par_neq.items() if len(v) > 1}
        libres = []
        for neq, pretendants in par_neq.items():
            if len(pretendants) == 1:
                libres.append(pretendants[0])
                continue
            # LE PLUS ANCIEN GAGNE — `first_detected_at`, départagé par `id`.
            #
            # **Ce n'est pas une échelle neuve : c'est celle du produit.**
            # `falkye/dedup_entreprises.py` la pose déjà pour le cas analogue —
            # *« le PRINCIPAL est toujours le dossier le plus ANCIEN
            # (first_detected_at) »*. Inventer un second critère ici ferait
            # dépendre l'identité d'une entreprise de la table par laquelle on
            # arrive.
            #
            # ⚠️ **Et l'ancienneté n'est pas la vérité.** Le dossier le plus vieux
            # peut être le plus mal saisi. Mais ce choix ne décide pas quel nom
            # est juste : il décide seulement qui PORTE le NEQ pendant qu'un
            # humain regarde la paire. **C'est la conservation qui rend ce choix
            # bon marché** — le perdant n'est pas perdu, il est journalisé.
            pretendants.sort(key=lambda x: (x["_anciennete"] is None,
                                            x["_anciennete"], x["company_id"]))
            gagnant, *perdants = pretendants
            libres.append(gagnant)
            for perdant in perdants:
                perdant["detenteur_id"] = gagnant["company_id"]
                perdant["detenteur_nom"] = gagnant["nom_detecte"]
                perdant["motif"] = "collision dans le lot — le plus ancien garde le NEQ"
                pris.append(perdant)

        print(f"   NEQ retenu, NEQ LIBRE          : {len(libres)}")
        if collisions:
            en_trop = sum(len(v) for v in collisions.values()) - len(collisions)
            print(f"   dont COLLISIONS dans le lot    : {len(collisions)} NEQ visés par "
                  f"plusieurs dossiers, {en_trop} dossier(s) écarté(s)")
        print(f"   NEQ retenu, NEQ DÉJÀ PRIS      : {len(pris)}   (conservés, jamais fusionnés)")
        print(f"   aucun NEQ retenu               : {non_resolues}")

        if args.comparer:
            print("\n" + "=" * 78)
            print(f"LES PAIRES — {min(args.comparer, len(libres))} sur {len(libres)} à poser")
            print("=" * 78)
            print("\n⚠️ Lire le NOM DU REGISTRE contre le NOM DÉTECTÉ. Un score de 100 sur")
            print("   deux raisons sociales différentes est une fausse résolution, et c'est")
            print("   la seule chose qu'un total ne montre jamais.\n")
            for p in libres[: args.comparer]:
                ecart = p["score"] - p["second"]
                print(f"   #{p['company_id']}  {p['neq']}   score {p['score']:.1f}"
                      f"  (2e {p['second']:.1f}, écart {ecart:.1f}, {p['candidats']} candidats)")
                print(f"      détecté  : {p['nom_detecte']}")
                print(f"      registre : {p['nom_registre']}")
                if p["ville"]:
                    print(f"      ville    : {p['ville']}")
                print()
            if pris:
                print("-" * 78)
                print(f"ET LES {min(args.comparer, len(pris))} PREMIERS NEQ DÉJÀ PRIS — rien ne sera touché")
                print("-" * 78 + "\n")
                for p in pris[: args.comparer]:
                    print(f"   #{p['company_id']} « {p['nom_detecte']} »")
                    print(f"      voudrait {p['neq']}, déjà porté par "
                          f"#{p['detenteur_id']} « {p['detenteur_nom']} »")
                    print()

        if not args.appliquer:
            print("=" * 78)
            print("   RAPPORT SEUL — rien n'a été écrit.")
            print("   Relancer avec --appliquer pour poser les NEQ libres.")
            print("=" * 78)
            return 0

        if not libres and not pris:
            print("\n   Rien à appliquer.")
            return 0

        # --- L'INSTANTANÉ D'AVANT, ÉCRIT AVANT LE COMMIT -----------------------
        # ⚠️ *Sans lui, « réversible » est une intention.* Il porte l'état de
        # chaque dossier AVANT le geste, donc il suffit à le défaire.
        horodatage = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        dossier = Path(args.instantane)
        try:
            dossier.mkdir(parents=True, exist_ok=True)
            chemin = dossier / f"reresolution-{horodatage}.json"
            chemin.write_text(
                json.dumps(
                    {
                        "a_poser": [_sans_champs_de_travail(x) for x in libres],
                        "conserves": [_sans_champs_de_travail(x) for x in pris],
                    },
                    ensure_ascii=False, indent=1,
                ),
                encoding="utf-8",
            )
        except OSError as exc:
            print(f"\n⛔ REFUS : l'instantané ne peut pas être écrit ({exc}).\n"
                  "   Rien n'a été modifié. Un geste irréversible sans trace de l'état\n"
                  "   d'avant n'est pas un geste réversible — c'est le même défaut que\n"
                  "   le chemin d'archive du diff, une table plus loin.",
                  file=sys.stderr)
            return 3
        print(f"\n   instantané d'avant : {chemin}")

        from falkye.dedup_entreprises import journaliser_candidat_fusion
        from falkye.resolution import _enrich_from_req

        poses = 0
        tardifs = 0
        for p in libres:
            company = session.get(Company, p["company_id"])
            # ⚠️ **LA DISPONIBILITÉ RE-VÉRIFIÉE AU MOMENT DE POSER**, et pas
            # seulement au moment de décider. Les collisions internes au lot
            # sont déjà résolues plus haut; celle-ci attrape l'autre cas — **un
            # cycle de production qui aurait pris ce NEQ entre le rapport et
            # l'écriture.** *Une vérification faite d'avance répond à l'état
            # d'avant, jamais à celui du moment où l'on écrit.*
            occupant = session.execute(
                select(Company).where(Company.neq == p["neq"])
            ).scalar_one_or_none()
            if occupant is not None:
                p["detenteur_id"] = occupant.id
                p["detenteur_nom"] = occupant.nom_detecte
                p["motif"] = "NEQ pris entre le rapport et l'écriture"
                pris.append(p)
                tardifs += 1
                continue
            company.neq = p["neq"]
            company.statut_resolution = StatutResolution.RESOLU
            _enrich_from_req(session, company, p["neq"])
            session.flush()  # la contrainte parle ICI, sur UNE ligne nommée
            poses += 1

        journalises = 0
        for p in pris:
            company = session.get(Company, p["company_id"])
            detenteur = session.get(Company, p["detenteur_id"])
            if company is None or detenteur is None:
                continue
            # Le DÉTENTEUR est le principal : il porte déjà le NEQ, donc il est
            # le dossier que le registre désigne. Le rapprochement est proposé,
            # jamais exécuté — `statut="a_examiner"`.
            journaliser_candidat_fusion(
                session, detenteur, company, p["score"], statut="a_examiner"
            )
            journalises += 1

        session.commit()
        print(f"\n   NEQ posés                  : {poses}")
        if tardifs:
            print(f"   pris entre rapport et écriture : {tardifs}   (journalisés, non posés)")
        print(f"   rapprochements journalisés : {journalises}   (aucune fusion)")
        print("\n" + "=" * 78)
        print("   Pour défaire : l'instantané ci-dessus porte l'état d'avant de")
        print("   chaque dossier touché (neq_avant, statut_avant).")
        print("=" * 78)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
