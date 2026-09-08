"""Retirer de la base du produit ce qu'un filtre territorial aurait dû écarter.

**Pourquoi cet outil existe.** Le filtre territorial est arrivé le 2026-09-07,
après que le programme des travailleurs étrangers temporaires eut déjà écrit
26 175 employeurs dont 66 % hors Québec. Le filtre empêche la suite; il ne
défait pas le passé.

**Pourquoi supprimer plutôt que garder « au cas où ».** Ces lignes faussent tous
les comptes, pèsent sur le quota d'écritures, et reviendraient à l'identique le
jour d'une expansion — le fichier source les porte toujours. Les garder coûte
sans rien préserver.

**LA RÈGLE QUI PROTÈGE.** Une entreprise hors territoire vue AUSSI par une autre
source est CONSERVÉE. Elles existent : au 2026-09-07, 41 entreprises — 21 du
palmarès ROB Top Growing, 14 vues au SEAO, 5 du Deloitte Fast 50 — hors Québec
mais visibles par des sources qui, elles, concernent le produit. Les supprimer
détruirait de l'observation légitime.

**La comparaison vient de falkye/territoire.py**, jamais d'une égalité recopiée
ici : un outil qui trierait autrement que le moteur supprimerait autre chose que
ce que le moteur écarte.

    python outils/purge_hors_territoire.py --source eimt --territoire Québec
    python outils/purge_hors_territoire.py --source eimt --territoire Québec --appliquer

Sans `--appliquer`, il ne fait que compter. C'est le défaut, parce que l'inverse
d'une suppression n'existe pas.
"""
from __future__ import annotations

import argparse
import sys

# Les écritures partent par lots BORNÉS EN TEMPS, pas seulement en nombre : la
# base distante annule une transaction portant une écriture non validée après
# moins de dix secondes d'inactivité (mesuré le 2026-09-07, voir
# docs/DEPLOIEMENT.md). Un lot de 400 identifiants tient largement dans la
# fenêtre; un `DELETE` unique sur 30 000 lignes ne le tiendrait pas.
TAILLE_LOT = 400


def _par_lots(valeurs: list, taille: int = TAILLE_LOT):
    for i in range(0, len(valeurs), taille):
        yield valeurs[i : i + taille]


def cibler(session, source_id: str, territoires: list[str]) -> tuple[list[int], list[int]]:
    """(à supprimer, conservées) — les entreprises vues par `source_id` dont la
    région n'appartient pas au territoire déclaré."""
    from sqlalchemy import distinct, select

    from falkye.models.company import Company
    from falkye.models.signal import Signal
    from falkye.territoire import appartient

    regions = [r for (r,) in session.execute(select(distinct(Company.region))).all()]
    hors = [r for r in regions if r is not None and not appartient(r, territoires)]

    vues = select(distinct(Signal.company_id)).where(Signal.source_id == source_id).scalar_subquery()
    cibles = select(Company.id).where(
        Company.id.in_(vues), Company.region.in_(hors)
    ).scalar_subquery()
    gardees = select(distinct(Signal.company_id)).where(
        Signal.company_id.in_(cibles), Signal.source_id != source_id
    ).scalar_subquery()

    a_supprimer = [i for (i,) in session.execute(
        select(Company.id).where(Company.id.in_(cibles), Company.id.notin_(gardees))
    ).all()]
    conservees = [i for (i,) in session.execute(
        select(Company.id).where(Company.id.in_(gardees))
    ).all()]
    return a_supprimer, conservees


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--territoire", action="append", required=True)
    parser.add_argument("--appliquer", action="store_true",
                        help="Sans ce drapeau, rien n'est supprimé — seulement compté.")
    args = parser.parse_args(argv)

    from sqlalchemy import delete, func, select

    from falkye.db import get_session
    from falkye.models.company import Company
    from falkye.models.diagnostic_journal import DiagnosticJournal
    from falkye.models.signal import Signal

    session = get_session()
    try:
        avant_e = session.execute(select(func.count()).select_from(Company)).scalar()
        avant_s = session.execute(select(func.count()).select_from(Signal)).scalar()

        a_supprimer, conservees = cibler(session, args.source, args.territoire)
        nb_signaux = 0
        for lot in _par_lots(a_supprimer):
            nb_signaux += session.execute(
                select(func.count()).select_from(Signal).where(Signal.company_id.in_(lot))
            ).scalar() or 0

        print(f"source                : {args.source}")
        print(f"territoire déclaré    : {args.territoire}")
        print(f"état avant            : {avant_e:,} entreprises, {avant_s:,} signaux".replace(",", " "))
        print(f"à supprimer           : {len(a_supprimer):,} entreprises, {nb_signaux:,} signaux".replace(",", " "))
        print(f"CONSERVÉES (autre src): {len(conservees):,}".replace(",", " "))

        if not args.appliquer:
            print("\n(compté seulement — relancer avec --appliquer pour supprimer)")
            return 0

        # L'ORDRE COMPTE : les lignes qui pointent vers une entreprise partent
        # avant elle, sinon on laisse des orphelins que rien ne signalerait.
        efface_diag = 0
        for lot in _par_lots(a_supprimer):
            efface_diag += session.execute(
                delete(DiagnosticJournal).where(
                    DiagnosticJournal.company_id_principal.in_(lot)
                )
            ).rowcount or 0
            efface_diag += session.execute(
                delete(DiagnosticJournal).where(
                    DiagnosticJournal.company_id_candidat.in_(lot)
                )
            ).rowcount or 0
            session.commit()

        efface_sig = 0
        for lot in _par_lots(a_supprimer):
            efface_sig += session.execute(
                delete(Signal).where(Signal.company_id.in_(lot))
            ).rowcount or 0
            session.commit()

        efface_ent = 0
        for i, lot in enumerate(_par_lots(a_supprimer), 1):
            efface_ent += session.execute(
                delete(Company).where(Company.id.in_(lot))
            ).rowcount or 0
            session.commit()
            if i % 10 == 0:
                print(f"  ... {efface_ent:,} entreprises retirées".replace(",", " "), flush=True)

        apres_e = session.execute(select(func.count()).select_from(Company)).scalar()
        apres_s = session.execute(select(func.count()).select_from(Signal)).scalar()
        print("\n--- SUPPRESSION APPLIQUÉE ---")
        print(f"journal de diagnostic : {efface_diag:,} ligne(s)".replace(",", " "))
        print(f"signaux               : {efface_sig:,}".replace(",", " "))
        print(f"entreprises           : {efface_ent:,}".replace(",", " "))
        print(f"état après            : {apres_e:,} entreprises, {apres_s:,} signaux".replace(",", " "))
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
