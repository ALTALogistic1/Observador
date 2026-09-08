"""Poser l'index composite (neq, nom_detecte_normalise) sur `companies`.

**Ce que cet index répare.** La résolution d'une entreprise sans NEQ lisait
TOUTE la population non résolue, à chaque signal neuf. Mesuré le 2026-09-08 sur
la base réelle par `rows_read` du protocole Hrana — 11 556 entreprises, dont
8 395 sans NEQ :

    neq = ?                                        →       0 ligne lue
    neq IS NULL AND nom_normalise = ?              →   8 396 lignes lues
    neq IS NULL AND nom_normalise GLOB 'préfixe*'  →   8 396 lignes lues

`ix_companies_neq` est UNIQUE : SQLite estime donc que `neq = ?` rend UNE ligne.
Mais un index unique accepte autant de NULL qu'on veut, et il y en a 8 395. Le
planificateur choisit l'index qu'il croit parfait et lit tout. Coût réel :
~16 800 lignes lues par signal neuf non résolu, soit le quota mensuel de lectures
épuisé par ~600 signaux. Les trois passages de l'EIMT l'ont vidé.

**Pourquoi un outil et pas `init_db()`.** `Base.metadata.create_all()` ne crée
que les TABLES manquantes; il n'ajoute pas un index à une table qui existe déjà.
Sur une base neuve le modèle suffit, sur la base en service il faut ce passage.

**Pourquoi il VÉRIFIE au lieu de se croire.** Un `CREATE INDEX` qui réussit ne
prouve pas que le planificateur s'en servira — l'index partiel essayé d'abord
réussissait, et le plan ne bougeait pas. L'outil relit donc `EXPLAIN QUERY PLAN`
des deux requêtes chères APRÈS coup, et sort en échec si elles retombent sur
`ix_companies_neq`. Les requêtes viennent des modules du moteur
(`falkye.resolution`, `falkye.dedup_entreprises`), jamais recopiées ici : un plan
mesuré sur une requête réécrite à côté ne dirait rien de celle qui tourne.

    python outils/migration_index_neq_nom.py                    # ne fait que lire
    python outils/migration_index_neq_nom.py --appliquer
    python outils/migration_index_neq_nom.py --appliquer --retirer-index-redondant

Sans `--appliquer`, il montre l'état et les plans actuels sans rien écrire.
"""
from __future__ import annotations

import argparse
import sys

INDEX_COMPOSITE = "ix_companies_neq_nom_normalise"
INDEX_REDONDANT = "ix_companies_nom_detecte_normalise"

CREATION = (
    f"CREATE INDEX IF NOT EXISTS {INDEX_COMPOSITE} "
    "ON companies (neq, nom_detecte_normalise)"
)


def connexion_produit(session):
    """La connexion du moteur du PRODUIT, jamais celle des miroirs.

    La session porte DEUX moteurs, routés par métadonnée (voir
    falkye/db.py::get_sessionmaker). Une requête ORM sur `Company` sait donc où
    aller — mais un `text()` brut n'appartient à aucune métadonnée, et la session
    refuse de choisir. Il faut nommer la cible par son modèle : sans ça, un outil
    de schéma peut lire ou écrire dans le mauvais fichier sans rien signaler.
    """
    from falkye.models.company import Company

    return session.connection(bind_arguments={"mapper": Company.__mapper__})


def index_existants(session) -> set[str]:
    from sqlalchemy import text

    lignes = connexion_produit(session).execute(
        text("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='companies'")
    ).all()
    return {nom for (nom,) in lignes if nom}


def _plan(session, requete) -> str:
    """Le plan d'exécution d'une requête ORM, en une ligne lisible."""
    from sqlalchemy import text
    from sqlalchemy.dialects import sqlite

    sql = str(
        requete.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True})
    )
    lignes = connexion_produit(session).execute(text("EXPLAIN QUERY PLAN " + sql)).all()
    return " ; ".join(str(l[-1]) for l in lignes)


def plans(session) -> dict[str, str]:
    """Les DEUX requêtes que l'index doit corriger — importées du moteur.

    Le repli par sous-chaîne n'est pas ici : aucun index ne le corrige, et
    l'inclure ferait échouer une vérification qui a raison de passer.
    """
    from falkye.dedup_entreprises import requete_candidats_prefixe
    from falkye.resolution import requete_nom_exact

    return {
        "nom exact (resolution.py)": _plan(session, requete_nom_exact("construction abc")),
        "préfixe GLOB (dedup_entreprises.py)": _plan(
            session, requete_candidats_prefixe("construction")
        ),
    }


def verifier(session) -> list[str]:
    """Les plans qui n'utilisent PAS l'index composite. Vide = l'index sert."""
    return [
        f"{nom} → {plan}"
        for nom, plan in plans(session).items()
        if INDEX_COMPOSITE not in plan
    ]


def appliquer(session, retirer_redondant: bool = False) -> None:
    from sqlalchemy import text

    connexion = connexion_produit(session)
    connexion.execute(text(CREATION))
    if retirer_redondant:
        connexion.execute(text(f"DROP INDEX IF EXISTS {INDEX_REDONDANT}"))
    session.commit()


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--appliquer", action="store_true", help="écrire (défaut : lire seulement)")
    parseur.add_argument(
        "--retirer-index-redondant",
        action="store_true",
        help=(
            f"retirer aussi {INDEX_REDONDANT} : les TROIS requêtes du code portent "
            "`neq IS NULL`, donc l'index simple ne sert plus rien une fois le "
            "composite en place — il ne coûte que du poids en écriture. Séparé "
            "parce que retirer un index d'office ferait diverger une base migrée "
            "d'une base neuve."
        ),
    )
    args = parseur.parse_args(argv)

    from falkye.db import get_session

    session = get_session()
    try:
        avant = index_existants(session)
        print("index présents sur `companies` :")
        for nom in sorted(avant):
            print(f"    {nom}")

        print("\nplans AVANT :")
        for nom, plan in plans(session).items():
            print(f"    {nom:<38} {plan}")

        if not args.appliquer:
            print(
                f"\n(lecture seule — relancer avec --appliquer pour poser {INDEX_COMPOSITE})"
            )
            return 0

        appliquer(session, retirer_redondant=args.retirer_index_redondant)
        print(f"\n{INDEX_COMPOSITE} posé.")
        if args.retirer_index_redondant:
            print(f"{INDEX_REDONDANT} retiré.")

        print("\nplans APRÈS :")
        for nom, plan in plans(session).items():
            print(f"    {nom:<38} {plan}")

        manques = verifier(session)
        if manques:
            print(
                f"\nÉCHEC : l'index existe mais le planificateur l'ignore.\n"
                + "\n".join(f"    {m}" for m in manques)
            )
            return 1
        print("\nLes deux requêtes chères passent par l'index composite.")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
