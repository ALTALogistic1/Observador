"""Ce que la ville d'une source APPORTE — mesuré en la retirant, pas en la comptant.

**La question** *(Alexandre, 2026-09-11)* : *combien d'entreprises doivent leur
ville à une source, et pour combien d'entre elles cette ville a permis une
résolution?* Compter les entreprises qu'une source crée dit ce qu'elle COÛTE;
seul ce rejeu dit ce qu'elle APPORTE.

**Comment.** Pour chaque entreprise retenue, la résolution par nom est rejouée
DEUX fois contre le miroir REQ — avec sa ville, puis sans — et les deux issues
sont comparées par la règle du moteur (`falkye.resolution.neq_retenu`, empruntée,
jamais recopiée). *La ville vaut +5 au score et sert de départage entre deux
entrées du REQ : son apport est exactement l'écart entre ces deux rejeux.*

**Ce que ça coûte : presque rien.** Le miroir REQ est un fichier LOCAL — les
2,7 M d'entrées ne sont jamais facturées. Sur la base durable, l'outil lit les
entreprises et les signaux une fois chacun *(~30 000 lignes)*. **Le rejeu, lui,
est gratuit**, et c'est ce qui rend cette mesure prenable.

**⚠️ Ce que l'outil ne peut PAS décider, et il le dit ligne par ligne.** Une
entreprise DÉJÀ RÉSOLUE a pu recevoir sa ville du REQ *après* sa résolution —
`_enrich_from_req` remplit `ville` quand elle est vide. Si la ville stockée est
celle du REQ, **rien ne distingue « la source l'a fournie » de « le REQ l'a
complétée »**, et la créditer à la source serait une preuve fabriquée. Ces
entreprises sont comptées à part, jamais dans le résultat.

**La population décidable** est donc : les entreprises NON résolues qui portent
une ville *(elle ne peut venir que d'un connecteur)*, plus les résolues dont la
ville DIFFÈRE de celle du REQ.

**Et le rejeu mesure le code d'AUJOURD'HUI contre le miroir d'AUJOURD'HUI**, pas
ce qui s'est passé au moment de la résolution. C'est une réponse à *« la ville
sert-elle? »*, pas à *« la ville a-t-elle servi ce jour-là? »* — la seconde n'est
écrite nulle part.

    python outils/apport_ville.py --source rob_top_growing --source deloitte_fast50
    python outils/apport_ville.py                       # toutes les entreprises

Sur l'hôte, l'environnement d'abord :

    set -a; . /etc/falkye/falkye.env; set +a
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict


def entreprises_exclusives(db_session, sources: list[str]) -> set[int]:
    """Les entreprises dont TOUS les signaux viennent des sources nommées.

    L'exclusivité est ce qui rend la ville attribuable : une entreprise vue aussi
    par une autre source a pu recevoir sa ville de celle-là. *Même règle que
    `provenance_entreprises.py` — une entreprise vue ailleurs n'appartient à
    personne.*
    """
    from sqlalchemy import select

    from falkye.models.signal import Signal

    par_company: dict[int, set[str]] = defaultdict(set)
    for company_id, source_id in db_session.execute(
        select(Signal.company_id, Signal.source_id)
    ).all():
        par_company[company_id].add(source_id)

    vises = set(sources)
    return {cid for cid, vues in par_company.items() if vues and vues <= vises}


def rejouer(db_session, nom: str, ville: str | None):
    """(neq avec la ville, neq sans) — la règle du moteur, des deux côtés."""
    from falkye.resolution import neq_retenu
    from falkye.sources import req as req_source

    avec = neq_retenu(req_source.resolve_neq_by_name(db_session, nom, ville=ville))
    sans = neq_retenu(req_source.resolve_neq_by_name(db_session, nom, ville=None))
    return avec, sans


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--source", action="append", default=[], help="source à mesurer (répétable)")
    parseur.add_argument("--limite", type=int, default=0, help="s'arrêter après N entreprises (0 = toutes)")
    args = parseur.parse_args(argv)

    from falkye.db import bases_sur_repli, cible_annoncee

    print(cible_annoncee())
    if bases_sur_repli():
        print(
            "\nREFUS — aucune cible n'a été choisie : "
            f"{', '.join(bases_sur_repli())} absente(s).\n"
            "  Un miroir vide rendrait « la ville n'apporte rien » pour toutes les entreprises.\n"
            "  Sur l'hôte : set -a; . /etc/falkye/falkye.env; set +a",
            file=sys.stderr,
        )
        return 2

    from sqlalchemy import func, select

    from falkye.db import get_session
    from falkye.models.company import Company
    from falkye.models.req_entry import REQEntry

    session = get_session()
    try:
        entrees_miroir = session.execute(select(func.count()).select_from(REQEntry)).scalar() or 0
        if not entrees_miroir:
            print(
                "\nREFUS — le miroir REQ est vide : le rejeu ne pourrait rien résoudre,\n"
                "  et « zéro apport » se lirait comme un verdict. Voir docs/MIROIRS.md.",
                file=sys.stderr,
            )
            return 2
        print(f"miroir REQ : {entrees_miroir} entrées")

        requete = select(Company)
        if args.source:
            ids = entreprises_exclusives(session, args.source)
            print(f"entreprises exclusives à {', '.join(args.source)} : {len(ids)}")
            if not ids:
                print("(rien à mesurer)")
                return 0
            requete = requete.where(Company.id.in_(ids))

        companies = session.execute(requete).scalars().all()

        sans_ville = 0
        non_decidables = 0
        decidables = []
        for c in companies:
            if not c.ville:
                sans_ville += 1
                continue
            if c.neq:
                # Résolue : la ville a pu être écrite par le REQ APRÈS coup.
                entry = session.execute(
                    select(REQEntry).where(REQEntry.neq == c.neq)
                ).scalars().first()
                meme_que_req = bool(
                    entry and entry.ville and entry.ville.strip().lower() == c.ville.strip().lower()
                )
                if meme_que_req:
                    non_decidables += 1
                    continue
            decidables.append(c)

        if args.limite:
            decidables = decidables[: args.limite]

        change_lissue = 0
        deja_resolue_sans = 0
        rien_ni_avec_ni_sans = 0
        for c in decidables:
            avec, sans = rejouer(session, c.nom_detecte, c.ville)
            if avec and not sans:
                change_lissue += 1
            elif avec and sans and avec != sans:
                change_lissue += 1  # pas le même NEQ : la ville a départagé
            elif sans:
                deja_resolue_sans += 1
            else:
                rien_ni_avec_ni_sans += 1

        total = len(companies)
        print(f"\nentreprises examinées : {total}")
        print(f"  sans ville : {sans_ville}")
        print(f"  ville NON DÉCIDABLE (résolue, ville identique à celle du REQ) : {non_decidables}")
        print(f"  ville décidable : {len(decidables)}")
        print("\nRejeu sur la population décidable :")
        print(f"  la ville CHANGE l'issue : {change_lissue}")
        print(f"  résolue même sans la ville : {deja_resolue_sans}")
        print(f"  non résolue dans les deux cas : {rien_ni_avec_ni_sans}")
        if decidables:
            print(f"\napport de la ville : {100 * change_lissue / len(decidables):.1f} % de la population décidable")

        print(
            "\n⚠ Portée. Ce rejeu mesure le code d'aujourd'hui contre le miroir "
            "d'aujourd'hui.\n"
            "  Il répond à « la ville sert-elle », pas à « la ville a-t-elle servi ce "
            "jour-là » —\n  la seconde n'est écrite nulle part. Et il ne dit rien de la "
            "PERTINENCE des\n  entreprises ainsi résolues : une résolution réussie sur "
            "un mastodonte reste\n  une entreprise qui n'est pas la clientèle visée."
        )
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
