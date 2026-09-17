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

#: Au-delà de ce nombre de dossiers visant un même NEQ libre, **personne ne
#: l'obtient**. *Deux prétendants, c'est un doublon plausible — la situation pour
#: laquelle la conservation a été pensée. Au-delà, c'est un nom qui désigne une
#: FAMILLE d'entités*, et départager par l'ancienneté y perd tout sens.
#:
#: ⚠️ **Ce n'est pas un seuil de score.** Le NEQ 8879690699 attirait 26 CISSS,
#: CIUSSS et centres hospitaliers distincts avec des scores de 95 à 100 — *monter
#: le seuil n'y ferait rien.* **Le nombre de prétendants est une preuve d'une
#: autre nature que le score.**
PRETENDANTS_MAX_POUR_TRANCHER = 2

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


#: Les champs que `falkye/resolution.py::_enrich_from_req` réécrit après avoir
#: posé un NEQ. **La liste est ici parce que l'instantané doit couvrir EXACTEMENT
#: ce que le geste touche** — un champ ajouté là-bas et oublié ici rendrait le
#: retour arrière partiel, en silence. *Un test compare les deux.*
CHAMPS_ENRICHIS = (
    "nom_officiel_req", "statut_legal", "adresse", "ville", "region",
    "code_postal", "secteur_activite_code", "secteur_activite_libelle",
)


def _champs_enrichis(company) -> dict:
    """L'état d'avant des champs que l'enrichissement va réécrire."""
    return {
        champ: getattr(getattr(company, champ), "value", getattr(company, champ))
        for champ in CHAMPS_ENRICHIS
    }


def _defaire(db_session, chemin: Path) -> int:
    """Rejoue l'instantané à l'envers. **Et refuse de toucher ce qui a bougé
    depuis** : un dossier dont le NEQ n'est plus celui qu'on avait posé n'est
    plus le nôtre, et le défaire écraserait quelqu'un d'autre."""
    import json as _json

    from falkye.models.company import Company, StatutLegal, StatutResolution

    contenu = _json.loads(chemin.read_text(encoding="utf-8"))
    a_defaire = contenu.get("a_poser", [])
    print(f"   instantané : {chemin}")
    print(f"   NEQ posés à défaire : {len(a_defaire)}\n")
    defaits = ignores = introuvables = 0
    for p in a_defaire:
        company = db_session.get(Company, p["company_id"])
        if company is None:
            introuvables += 1
            continue
        if company.neq != p["neq"]:
            ignores += 1
            continue
        company.neq = p["neq_avant"]
        if p.get("statut_avant"):
            company.statut_resolution = StatutResolution(p["statut_avant"])
        for champ, valeur in (p.get("champs_avant") or {}).items():
            if champ == "statut_legal":
                setattr(company, champ, StatutLegal(valeur) if valeur else None)
            else:
                setattr(company, champ, valeur)
        defaits += 1
    db_session.commit()
    print(f"   défaits      : {defaits}")
    print(f"   ignorés      : {ignores}   (le NEQ a changé depuis — plus le nôtre)")
    if introuvables:
        print(f"   introuvables : {introuvables}")
    print("\n   ⚠️ Les rapprochements JOURNALISÉS ne sont pas retirés : ce sont des")
    print("      observations, pas des écritures sur les dossiers.")
    return 0


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
        par_neq: dict[str, list[dict]] = {}
        for paire in libres:
            par_neq.setdefault(paire["neq"], []).append(paire)

        collisions = {neq: v for neq, v in par_neq.items() if len(v) > 1}
        refuses_en_bloc: dict[str, int] = {}
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
            # ⛔ **AU-DELÀ DE DEUX PRÉTENDANTS, PERSONNE NE L'OBTIENT.**
            #
            # *Le fait qui a écrit ce refus* (2026-09-17, relevé par Alexandre) :
            # **le NEQ 8879690699 attirait 26 dossiers** — CISSS de la
            # Montérégie-Centre, CISSS Gaspésie, CIUSSS de l'Outaouais, CHUM,
            # Centre universitaire de santé McGill, Institut de Cardiologie…
            # **26 organisations RÉELLEMENT DISTINCTES, scores de 95 à 100.**
            #
            # ⚠️ **Le nombre de prétendants est lui-même une preuve CONTRE
            # l'appariement.** Deux dossiers qui convergent, c'est un doublon
            # plausible — la situation pour laquelle la conservation a été
            # pensée. *Vingt-six, c'est un nom qui désigne une FAMILLE d'entités,
            # et l'ancienneté n'y a plus aucun sens* : elle désignerait un
            # gagnant dans un groupe dont probablement AUCUN membre n'est le bon.
            #
            # **Ce n'est pas un réglage de seuil.** Les noms se ressemblent
            # réellement; le scoreur ne se trompe pas, il répond à une autre
            # question que celle qu'on lui pose. *Monter le seuil n'y ferait
            # rien — ces scores sont à 100.*
            #
            # **Le refus ne peut que RÉDUIRE les écritures**, jamais en produire
            # une. Les 26 restent des dossiers séparés, tous journalisés.
            if len(pretendants) > PRETENDANTS_MAX_POUR_TRANCHER:
                for pretendant in pretendants:
                    pretendant["detenteur_id"] = None
                    pretendant["detenteur_nom"] = None
                    pretendant["motif"] = (
                        f"REFUS — {len(pretendants)} dossiers visent ce NEQ; "
                        "le nombre de prétendants est une preuve contre "
                        "l'appariement, et aucun ne l'obtient"
                    )
                    pris.append(pretendant)
                refuses_en_bloc[neq] = len(pretendants)
                continue

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
        deja_journalises = 0
        from falkye.models.diagnostic_journal import DiagnosticJournal, TypeDiagnostic

        def _deja_au_journal(principal_id: int, candidat_id: int | None,
                             type_diagnostic) -> bool:
            """⚠️ **La passe était idempotente sur les DOSSIERS et ne l'était pas
            sur le JOURNAL** *(relevé le 2026-09-17, avant d'appliquer)*.

            Un dossier posé sort de la population — `Company.neq IS NULL` ne le
            rend plus. **Mais un dossier CONSERVÉ y reste, donc il était
            re-journalisé à chaque exécution.** *Et c'est précisément la file
            qu'un humain doit dépiler : la polluer de doublons rend le travail
            plus long à chaque relance.*
            """
            requete = select(DiagnosticJournal.id).where(
                DiagnosticJournal.type_diagnostic == type_diagnostic,
                DiagnosticJournal.company_id_principal == principal_id,
                DiagnosticJournal.statut == "a_examiner",
            )
            requete = requete.where(
                DiagnosticJournal.company_id_candidat.is_(None)
                if candidat_id is None
                else DiagnosticJournal.company_id_candidat == candidat_id
            )
            return session.execute(requete.limit(1)).scalar_one_or_none() is not None

        for p in pris:
            company = session.get(Company, p["company_id"])
            if company is None:
                continue
            attendu = (
                TypeDiagnostic.PROBLEME_AUTRE_CHANTIER
                if p.get("detenteur_id") is None
                else TypeDiagnostic.CANDIDAT_FUSION_ENTREPRISE
            )
            principal = (company.id if p.get("detenteur_id") is None
                         else p["detenteur_id"])
            candidat = None if p.get("detenteur_id") is None else company.id
            if _deja_au_journal(principal, candidat, attendu):
                deja_journalises += 1
                continue
            if p.get("detenteur_id") is None:
                # ⚠️ **UN GROUPE REFUSÉ N'A PAS DE PRINCIPAL, ET C'EST LE FOND.**
                # `journaliser_candidat_fusion` demande deux dossiers et affirme
                # que l'un est le bon — *exactement ce qu'on vient de refuser
                # d'affirmer.* Le journaliser ainsi contredirait le refus.
                #
                # Journalisé donc comme un PROBLÈME à examiner, rattaché au seul
                # dossier concerné. **Sans ça, les 26 disparaissaient du
                # journal** : le `continue` d'origine les écartait en silence, et
                # « refusé » se serait lu comme « jamais rencontré ».
                session.add(DiagnosticJournal(
                    type_diagnostic=TypeDiagnostic.PROBLEME_AUTRE_CHANTIER,
                    profile_id=None,
                    texte_description=(
                        f"Reprise NEQ refusée — #{company.id} « {company.nom_detecte} » "
                        f"vise {p['neq']} ({p.get('motif', '')}). Score {p['score']}, "
                        f"registre « {p['nom_registre']} »."
                    ),
                    statut="a_examiner",
                    company_id_principal=company.id,
                    company_id_candidat=None,
                    score_similarite=p["score"],
                ))
                journalises += 1
                continue
            detenteur = session.get(Company, p["detenteur_id"])
            if detenteur is None:
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
