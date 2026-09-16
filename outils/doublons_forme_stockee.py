#!/usr/bin/env python3
"""Deux dossiers non résolus partagent-ils la forme que la PRODUCTION compare?

**Ce que cette requête ferme** *(Alexandre, 2026-09-16)*. `_find_unresolved_
company` traverse le cycle à chaque signal non résolu et se termine par
`scalar_one_or_none()` — **qui LÈVE si deux lignes reviennent.**

    aucune ligne rendue  ⇒ le défaut n'est jamais survenu et ne PEUT PAS
                           survenir dans l'état actuel;
    des lignes rendues   ⇒ il peut lever, et le correctif passe devant.

⚠️ **Et la colonne interrogée n'est pas négociable.** La production compare
`Company.nom_detecte_normalise`, **la valeur STOCKÉE** — pas
`normaliser(nom_detecte)` recalculé. *Une colonne dérivée a été écrite par le
normaliseur de son jour, et `normaliser` a changé le 15 septembre 2026.* **Un
compte fait sur la valeur recalculée répondrait à une autre question, et rien
dans sa sortie ne le dirait** *(cas 33)*.

⚠️ **POURQUOI UN OUTIL PLUTÔT QU'UNE LIGNE DE SQL.** La base du produit est
**distante**, et une commande lancée sans l'environnement chargé retombe sur
`./data/falkye.sqlite3` — *qu'elle CRÉE, puis interroge.* **Une base vide rend
zéro ligne, et ce zéro se lit exactement comme la bonne réponse.** *C'est le cas
30 et le cas 41 : un verdict rendu sur une base vide est le plus rassurant de
tous.* `refuser_si_cible_non_choisie()` l'interdit ici.

⚠️ **PORTÉE : lecture seule.** Un `SELECT` et un `count(*)`.

Usage, SUR L'HÔTE :
    sudo -u falkye bash -c 'set -a; . /etc/falkye/falkye.env; set +a; \
        cd /opt/falkye/code && /opt/falkye/venv/bin/python -m outils.doublons_forme_stockee'
"""
from __future__ import annotations

from outils.nombres import milliers


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--exemples", type=int, default=20)
    args = parser.parse_args(argv)

    from sqlalchemy import func, select

    from falkye.db import refuser_si_cible_non_choisie

    code = refuser_si_cible_non_choisie()
    if code:
        return code

    from falkye.db import get_session
    from falkye.models.company import Company

    print("=" * 78)
    print("LA FORME STOCKÉE EST-ELLE UNIQUE PARMI LES DOSSIERS SANS NEQ?")
    print("=" * 78)
    print("\n   Colonne interrogée : `companies.nom_detecte_normalise` — la valeur")
    print("   STOCKÉE, celle que la production compare. Pas un recalcul.\n")

    session = get_session()
    try:
        total = session.execute(
            select(func.count()).select_from(Company).where(Company.neq.is_(None))
        ).scalar() or 0
        vides = session.execute(
            select(func.count()).select_from(Company)
            .where(Company.neq.is_(None), Company.nom_detecte_normalise == "")
        ).scalar() or 0

        groupes = session.execute(
            select(Company.nom_detecte_normalise, func.count().label("n"))
            .where(Company.neq.is_(None))
            .group_by(Company.nom_detecte_normalise)
            .having(func.count() > 1)
            .order_by(func.count().desc())
        ).all()

        print(f"   dossiers sans NEQ        : {milliers(total)}")
        print(f"   dont forme stockée VIDE  : {milliers(vides)}")
        if vides > 1:
            print("      ⚠️ Une forme vide partagée est un doublon comme un autre :")
            print("         `nom_detecte_normalise == ''` rend plusieurs lignes.")
        print(f"\n   formes PARTAGÉES         : {milliers(len(groupes))}")

        if not groupes:
            print("\n" + "=" * 78)
            print("   ✅ AUCUNE LIGNE RENDUE.")
            print("   `scalar_one_or_none()` ne peut pas lever dans l'état actuel,")
            print("   et il n'a jamais pu — la condition n'existe pas en base.")
            print("\n   ⚠️ « Dans l'état actuel » : la borne sans ordre du")
            print("      dédoublonnage peut créer cette condition demain. Ce zéro")
            print("      dit que le défaut n'est pas SURVENU, pas qu'il est")
            print("      impossible.")
            print("=" * 78)
            return 0

        print("\n" + "=" * 78)
        print("   ⛔ DES LIGNES SONT RENDUES — le chemin de production PEUT lever.")
        print("=" * 78)
        for forme, n in groupes[: args.exemples]:
            print(f"\n   « {forme} »  ×{n}")
            for c in session.execute(
                select(Company).where(
                    Company.neq.is_(None), Company.nom_detecte_normalise == forme
                )
            ).scalars():
                print(f"      #{c.id:<7} « {c.nom_detecte} »")
        if len(groupes) > args.exemples:
            print(f"\n   … {milliers(len(groupes) - args.exemples)} forme(s) de plus.")
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
