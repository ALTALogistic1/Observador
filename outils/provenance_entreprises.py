"""D'où viennent les entreprises de `companies` — par source, et en exclusivité.

**La question qui a fait exister cet outil** *(Alexandre, 2026-09-11)* : *combien
des 11 600 entreprises viennent de Globe and Mail Top Growing et de Deloitte
Fast 50?* Ces deux palmarès listent des entreprises au sommet de la croissance
canadienne — des mastodontes — et la spéc. 8.2 dit déjà que sans normalisation,
tout signal de volume favorise mécaniquement les grandes entreprises, **celles qui
ne sont pas la clientèle visée**. Si elles ne corroborent rien d'utile, elles
créent des dossiers que rien ne servira, **et chacun coûte une question de plus
dans la boucle du cycle** *(registre, D37)*.

**Deux nombres, jamais un seul, et c'est tout l'objet.**

*Touchées* — les entreprises qu'au moins un signal de cette source désigne. C'est
la portée de la source, et elle se recoupe avec les autres.

*EXCLUSIVES* — les entreprises qu'**aucune autre source** ne voit. **C'est le seul
nombre qui dit ce qui disparaîtrait** si la source était retirée. Les autres
resteraient : elles existent pour une autre raison. *Règle déjà écrite dans
`outils/purge_hors_territoire.py` — « une entreprise hors territoire vue AUSSI par
une autre source est CONSERVÉE » — et c'est la même ici : une source qui ne fait
que corroborer ne crée rien.*

**Ce que cet outil COÛTE** — un balayage de `signals`, soit ~18 000 lignes lues
facturées, **une fois**. Il ne lit rien d'autre. *(Le dire fait partie du geste :
un outil qui mesure un coût sans annoncer le sien serait mal placé pour le faire.)*

**Ce qu'il ne dit PAS.** Ni la pertinence d'une source, ni la qualité de ses
dossiers, ni ce qu'elle ajoute au dossier une fois le signal détecté — trois
questions distinctes, dont aucune ne se lit dans un compte.

    python outils/provenance_entreprises.py
    python outils/provenance_entreprises.py --source rob_top_growing --source deloitte_fast50

Sur l'hôte, l'environnement d'abord, sans quoi la cible est un fichier fantôme :

    set -a; . /etc/falkye/falkye.env; set +a
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict


def paires(db_session) -> list[tuple[int, str]]:
    """(company_id, source_id) — UN balayage, tout le reste se calcule ici.

    Compter par requêtes groupées demanderait un passage par source; une seule
    lecture coûte moins et rend des comptes cohérents entre eux, pris au même
    instant.
    """
    from sqlalchemy import select

    from falkye.models.signal import Signal

    return [
        (cid, sid)
        for cid, sid in db_session.execute(select(Signal.company_id, Signal.source_id)).all()
    ]


def ventiler(paires_lues: list[tuple[int, str]]) -> dict:
    sources_par_company: dict[int, set[str]] = defaultdict(set)
    for company_id, source_id in paires_lues:
        sources_par_company[company_id].add(source_id)

    touchees: dict[str, int] = defaultdict(int)
    exclusives: dict[str, int] = defaultdict(int)
    for sources in sources_par_company.values():
        for source_id in sources:
            touchees[source_id] += 1
        if len(sources) == 1:
            exclusives[next(iter(sources))] += 1

    return {
        "touchees": dict(touchees),
        "exclusives": dict(exclusives),
        "entreprises_avec_signal": len(sources_par_company),
        "signaux": len(paires_lues),
    }


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument(
        "--source", action="append", default=[],
        help="mettre ces sources en évidence (répétable). Toutes sont rapportées de toute façon.",
    )
    args = parseur.parse_args(argv)

    from falkye.db import bases_sur_repli, cible_annoncee

    print(cible_annoncee())
    if bases_sur_repli():
        print(
            "\nREFUS — aucune cible n'a été choisie : "
            f"{', '.join(bases_sur_repli())} absente(s), et le repli par défaut est relatif au répertoire courant.\n"
            "  Zéro entreprise sur une base vide se lit exactement comme zéro entreprise.\n"
            "  Sur l'hôte : set -a; . /etc/falkye/falkye.env; set +a",
            file=sys.stderr,
        )
        return 2

    from sqlalchemy import func, select

    from falkye.db import get_session
    from falkye.models.company import Company

    session = get_session()
    try:
        total = session.execute(select(func.count()).select_from(Company)).scalar() or 0
        v = ventiler(paires(session))

        print(f"\nentreprises en base : {total}")
        print(f"  dont au moins un signal : {v['entreprises_avec_signal']}")
        sans_signal = total - v["entreprises_avec_signal"]
        if sans_signal:
            # Ni une anomalie ni un détail : une entreprise sans signal a été
            # créée par un autre chemin (fusion, import, enrichissement), et elle
            # pèse dans la boucle comme les autres.
            print(f"  sans aucun signal : {sans_signal} — créées par un autre chemin")
        print(f"  signaux lus : {v['signaux']}\n")

        entete = f"{'source':<26}{'touchées':>10}{'EXCLUSIVES':>12}{'part excl.':>12}"
        print(entete)
        for source_id in sorted(v["touchees"], key=lambda s: -v["touchees"][s]):
            t = v["touchees"][source_id]
            e = v["exclusives"].get(source_id, 0)
            part = f"{100 * e / total:.1f} %" if total else "—"
            marque = "→ " if source_id in args.source else "  "
            print(f"{marque}{source_id:<24}{t:>10}{e:>12}{part:>12}")

        if args.source:
            ens_exclusives = sum(v["exclusives"].get(s, 0) for s in args.source)
            print(
                f"\nSources mises en évidence : {', '.join(args.source)}\n"
                f"  entreprises qui disparaîtraient si elles étaient retirées : {ens_exclusives}"
                + (f" ({100 * ens_exclusives / total:.1f} % de la base)" if total else "")
            )
            print(
                "  ⚠ Somme d'exclusivités PAR SOURCE — une entreprise vue par ces deux\n"
                "    sources-là et par aucune autre n'y figure pas : elle n'est exclusive\n"
                "    à ni l'une ni l'autre. Le retrait des DEUX en ferait disparaître plus."
            )

        print(
            "\nCe compte ne dit ni la pertinence d'une source, ni ce qu'elle ajoute au\n"
            "dossier une fois le signal détecté. Trois questions distinctes."
        )
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
