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

   ⚠️ **Et la paire montre LA FORME QUI A DÉCIDÉ, pas seulement la dénomination
   élue.** *Le score d'un NEQ est le meilleur de ses noms* — donc
   `16790224 Canada Inc.` peut scorer **100** contre
   `LES ENTREPRISES DOUGLAS POWERTECH INC.` sans un caractère commun, parce que
   la décision s'est prise sur une TROISIÈME chaîne que le registre porte aussi.
   **Lire « registre : X » quand la décision s'est prise sur Y, c'est le
   cas 33** — et c'est précisément ce qu'on relit avant d'écrire.
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
from collections import Counter

from outils import pose_du_neq
# ⚠️ **La machinerie d'écriture est EMPRUNTÉE, jamais recopiée.** *Deux passes
# posent des NEQ; elles ne diffèrent que par la façon dont la paire est
# produite.* **Recopier une règle de conservation sur un chemin d'écriture
# perdrait une identité que l'instantané de l'autre copie ne rendrait pas.**
from outils.pose_du_neq import (  # noqa: F401 -- noms conservés pour les appelants
    CHAMPS_ENRICHIS,
    PRETENDANTS_MAX_POUR_TRANCHER,
    champs_enrichis as _champs_enrichis,
    defaire as _defaire,
    sans_champs_de_travail as _sans_champs_de_travail,
    statut_lisible as _statut_lisible,
)
from datetime import datetime, timezone
from pathlib import Path

#: ⛔ Le refus au-delà de deux prétendants vit désormais dans
#: `outils/pose_du_neq.py`, avec le geste qu'il gouverne — *une règle se
#: range près de ce qu'elle interdit.* Il est réexporté ci-dessus parce que
#: la sortie de cette passe le cite.

#: Où l'instantané d'avant est déposé. Le même répertoire que les témoins et le
#: miroir — le seul que les unités peuvent écrire (`ReadWritePaths`).
#: ⚠️ **Empruntée à `outils/pose_du_neq.py`, plus recopiée** — elle y vit
#: près du geste qu'elle gouverne. *Le nom est conservé ici pour les
#: appelants.*
DOSSIER_INSTANTANE = pose_du_neq.DOSSIER_INSTANTANE


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
    parser.add_argument("--depuis", type=int, default=0, metavar="K",
                        help="commencer à la K-ième paire — pour les regarder PAR LOT")
    parser.add_argument("--defaire", default=None, metavar="FICHIER",
                        help="rejouer un instantané à l'envers")
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
        if args.defaire:
            print("\n" + "=" * 78)
            print("DÉFAIRE UNE REPRISE")
            print("=" * 78 + "\n")
            return _defaire(session, Path(args.defaire))

        requete = select(Company).where(Company.neq.is_(None)).order_by(Company.id)
        if args.limite:
            requete = requete.limit(args.limite)
        entreprises = list(session.execute(requete).scalars().all())
        print(f"   entreprises sans NEQ : {len(entreprises)}")

        libres: list[dict] = []
        pris: list[dict] = []
        non_resolues = 0
        #: Tous les `REQMatch` retenus, pour traduire les formes gagnantes en
        #: gisement et statut **en une passe** plutôt qu'une requête par paire.
        tetes: list = []

        for company in entreprises:
            neq, matches = _resoudre_une(session, company)
            if neq is None:
                non_resolues += 1
                continue
            top = matches[0]
            tetes.append(top)
            detenteur = session.execute(
                select(Company).where(Company.neq == neq)
            ).scalar_one_or_none()
            paire = {
                "company_id": company.id,
                "nom_detecte": company.nom_detecte,
                "ville": company.ville,
                "neq": neq,
                "nom_registre": top.entry.nom,
                # ⚠️ Préfixés `_` : ce sont des éléments de LECTURE, pas l'état
                # d'avant. *L'instantané porte ce qu'il faut pour défaire, et
                # rien d'autre* — `_sans_champs_de_travail` les retire avant l'écriture.
                "_forme_normalisee": top.forme_normalisee,
                "score": round(top.score, 1),
                "second": round(matches[1].score, 1) if len(matches) > 1 else 0.0,
                "candidats": len(matches),
                # L'état d'AVANT, pour que l'instantané soit réversible.
                "neq_avant": None,
                "statut_avant": getattr(company.statut_resolution, "value", None),
                # ⚠️ **Et les huit champs que `_enrich_from_req` réécrit.**
                # *Sans eux, défaire rendait le NEQ et laissait l'adresse, la
                # ville, le secteur et le statut légal du registre* — un dossier
                # ni dans son état d'avant, ni dans celui d'après. **« Réversible »
                # ne veut rien dire si l'instantané ne porte qu'une partie de ce
                # que le geste touche.** *(Relevé le 2026-09-17, avant d'appliquer.)*
                "champs_avant": _champs_enrichis(company),
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
        libres, collisions, refuses_en_bloc = pose_du_neq.resoudre_les_collisions(
            libres, pris)
        print(f"   NEQ retenu, NEQ LIBRE          : {len(libres)}")
        if collisions:
            en_trop = sum(len(v) for v in collisions.values()) - len(collisions)
            print(f"   dont COLLISIONS dans le lot    : {len(collisions)} NEQ visés par "
                  f"plusieurs dossiers, {en_trop} dossier(s) écarté(s)")
        if refuses_en_bloc:
            total_refuses = sum(refuses_en_bloc.values())
            print(f"\n   ⛔ REFUSÉS EN BLOC              : {len(refuses_en_bloc)} NEQ, "
                  f"{total_refuses} dossier(s) — AUCUN ne reçoit son NEQ")
            print(f"      Au-delà de {PRETENDANTS_MAX_POUR_TRANCHER} prétendants, le nombre")
            print("      est une preuve CONTRE l'appariement : un nom qui désigne une")
            print("      famille d'entités, pas une entreprise. L'ancienneté n'y a")
            print("      aucun sens — elle désignerait un gagnant dans un groupe dont")
            print("      aucun membre n'est probablement le bon.")
            for neq, combien in sorted(refuses_en_bloc.items(), key=lambda kv: -kv[1])[:5]:
                print(f"         {neq}  ×{combien}")
        print(f"   NEQ retenu, NEQ DÉJÀ PRIS      : {len(pris)}   (conservés, jamais fusionnés)")
        print(f"   aucun NEQ retenu               : {non_resolues}")

        # ---- SUR QUOI LA DÉCISION S'EST PRISE, sur TOUTE la population ------
        # ⚠️ *Cinquante paires lues ne disent pas combien sont dans ce cas.* Si
        # c'est deux, c'est anecdotique; si c'est trois cents, la relecture ne
        # disait pas ce qu'on croyait qu'elle disait.
        from falkye.sources import req as req_source

        formes = req_source.formes_retenues(session, tetes)

        def _forme_de(paire: dict):
            return formes.get((paire["neq"], paire["_forme_normalisee"]))

        autrement = [
            p for p in libres
            if (f := _forme_de(p)) is not None and not f.est_la_denomination_elue
        ]
        k = len(autrement)
        print("\n   ⚠️ SUR QUOI LA DÉCISION S'EST PRISE — et ce n'est pas toujours "
              "ce qu'on lit\n")
        part = f" ({100 * k / len(libres):.1f} %)" if libres else ""
        print(f"      forme AUTRE que la dénomination sociale élue : "
              f"{k} sur {len(libres)}{part}")
        print("      *Là, « registre : X » NOMME l'entreprise mais ne dit pas ce qui")
        print("       a été COMPARÉ.* Les deux lignes de chaque paire le disent.")
        if autrement:
            par_gisement: Counter = Counter(
                (_forme_de(p).gisement or "(inconnu)") for p in autrement
            )
            print(f"\n      {'gisement de la forme qui a décidé':<46} {'paires':>8}")
            for gisement, combien in par_gisement.most_common():
                print(f"      {gisement:<46} {combien:>8}")
            print("\n      ⚠️ `denomn_soc` vient de `FusionScissions.csv` : c'est une")
            print("         dénomination sociale, pas une relation NEQ→NEQ.")

            # ⚠️ **La couverture de la colonne, À CÔTÉ de la ventilation.**
            # *Une ventilation par gisement lue comme complète alors qu'un tiers
            # des lignes n'en portent pas sous-estime le gisement majoritaire
            # d'autant — et rien ne le dit si personne ne l'écrit ici.*
            sans, total = req_source.lignes_sans_gisement(session)
            part = f"{100 * sans / total:.1f} %" if total else "—"
            print(f"\n      ⚠️ COUVERTURE DE LA COLONNE `gisement` dans `req_noms` :")
            print(f"         {sans} lignes sur {total} n'en portent pas ({part}).")
            print("         Ce sont celles du pont du 15 septembre, chargées avant")
            print(f"         que la colonne existe — comptées ci-dessus sous")
            print(f"         « {req_source.GISEMENT_ANTERIEUR_A_LA_COLONNE} ».")
            print("      ⚠️ Et un réimport NE LES RÉÉCRIT PAS : `req_noms` s'écrit")
            print("         en `INSERT OR IGNORE` et rien ne la vide, donc les")
            print("         lignes existantes sont SAUTÉES. *La colonne ne se")
            print("         remplira pas d'elle-même le 2 octobre.*")

        if args.comparer:
            print("\n" + "=" * 78)
            lot = libres[args.depuis: args.depuis + args.comparer]
            print(f"LES PAIRES — {args.depuis + 1} à {args.depuis + len(lot)} "
                  f"sur {len(libres)} à poser")
            print("=" * 78)
            print("\n⚠️ Lire le NOM DU REGISTRE contre le NOM DÉTECTÉ. Un score de 100 sur")
            print("   deux raisons sociales différentes est une fausse résolution, et c'est")
            print("   la seule chose qu'un total ne montre jamais.\n")
            for p in lot:
                ecart = p["score"] - p["second"]
                print(f"   #{p['company_id']}  {p['neq']}   score {p['score']:.1f}"
                      f"  (2e {p['second']:.1f}, écart {ecart:.1f}, {p['candidats']} candidats)")
                print(f"      détecté  : {p['nom_detecte']}")
                print(f"      registre : {p['nom_registre']}")
                # ⚠️ **Les deux lignes qui disent sur quoi on a décidé.** *Sans
                # elles, `16790224 Canada Inc.` contre
                # `LES ENTREPRISES DOUGLAS POWERTECH INC.` à 100 se lit comme une
                # fausse résolution — alors que c'est la bonne, prise sur une
                # troisième chaîne.* **Cas 33 : l'instrument dit sur quoi il a
                # décidé.**
                forme = _forme_de(p)
                if forme is None:
                    print("      ⚠️ a matché : forme inconnue — le scoreur n'a "
                          "pas dit laquelle")
                else:
                    marque = "  " if forme.est_la_denomination_elue else "⚠️"
                    print(f"      {marque} a matché : "
                          f"{forme.nom_publie or '(forme simulée)'}")
                    # ⚠️ *La dénomination élue vit dans `req_entries`, qui ne
                    # porte pas de statut DE NOM* — écrire « statut inconnu » y
                    # ferait chercher une lecture manquée là où il n'y a rien à
                    # lire. **Un statut absent sur une forme de `req_noms`, lui,
                    # est une vraie lacune et se dit.**
                    statut = ("" if forme.est_la_denomination_elue and forme.statut is None
                              else f" · statut {_statut_lisible(forme.statut)}")
                    print(f"         gisement {forme.gisement or '(inconnu)'}{statut}")
                if p["ville"]:
                    print(f"      ville    : {p['ville']}")
                print()
            if pris:
                lot_pris = pris[args.depuis: args.depuis + args.comparer]
                print("-" * 78)
                print(f"ET LES NEQ DÉJÀ PRIS {args.depuis + 1} à "
                      f"{args.depuis + len(lot_pris)} sur {len(pris)} — rien ne sera touché")
                print("-" * 78 + "\n")
                for p in lot_pris:
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

        poses, tardifs = pose_du_neq.poser_les_neq(session, libres, pris)
        journalises, deja_journalises = pose_du_neq.journaliser_les_conserves(
            session, pris, "Reprise NEQ refusée")
        session.commit()
        print(f"\n   NEQ posés                  : {poses}")
        if tardifs:
            print(f"   pris entre rapport et écriture : {tardifs}   (journalisés, non posés)")
        print(f"   rapprochements journalisés : {journalises}   (aucune fusion)")
        if deja_journalises:
            print(f"   déjà au journal            : {deja_journalises}   "
                  f"(non redoublés)")
        print("\n" + "=" * 78)
        print("   Pour défaire : l'instantané ci-dessus porte l'état d'avant de")
        print("   chaque dossier touché (neq_avant, statut_avant).")
        print("=" * 78)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
