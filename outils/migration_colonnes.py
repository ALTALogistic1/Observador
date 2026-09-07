"""Rapprocher le schéma d'une base existante des modèles — les COLONNES.

**Le défaut que cet outil comble.** `falkye/db.py::init_db()` appelle
`create_all()`, qui crée les tables MANQUANTES et rien d'autre. Une colonne
ajoutée à une table qui existe déjà n'est jamais créée : `create_all` ne
regarde pas l'intérieur des tables présentes. La chaîne de déploiement
(`deploiement/falkye-migration.service`) hérite du même angle mort.

Constaté sur la base de production le 2026-09-06 : `profiles.desabonne_le`,
posée par le chantier 28, était absente de la base distante alors que les deux
NOUVELLES tables du même chantier, elles, s'y étaient créées. Une lecture de
profil suffisait à lever `no such column`.

**Ce que cet outil fait, et rien de plus.** Il AJOUTE les colonnes manquantes
(`ALTER TABLE ... ADD COLUMN`), opération additive et réversible par abandon.
Il ne renomme rien, ne supprime rien, ne change aucun type : ces gestes-là
perdent de la donnée et exigent une décision humaine, jamais un outil qui
tourne au déploiement.

Il ne remplace pas Alembic — il rend visible et réparable la dérive en
attendant, ce que le silence de `create_all` ne fait pas.

    python outils/migration_colonnes.py              # rapporte, ne touche à rien
    python outils/migration_colonnes.py --appliquer  # ajoute les colonnes
"""
from __future__ import annotations

import argparse
import sys

from sqlalchemy import inspect, text

import falkye.models  # noqa: F401 -- enregistre tous les modèles
from falkye.db import get_engine, get_engine_miroir, init_db
from falkye.models.base import Base, BaseMiroir


# Les DEUX cibles, chacune avec sa métadonnée — voir falkye/models/base.py.
# Une seule aurait laissé la moitié du schéma sans surveillance : une colonne
# ajoutée à un modèle miroir n'aurait jamais été rapportée, et la dérive y est
# aussi silencieuse qu'ailleurs.
def cibles() -> list[tuple[str, object, object]]:
    return [
        ("produit", Base.metadata, get_engine()),
        ("miroirs", BaseMiroir.metadata, get_engine_miroir()),
    ]


def colonnes_manquantes(engine, metadata=None) -> dict[str, list]:
    """{nom de table: [Column, ...]} pour les tables DÉJÀ présentes."""
    metadata = Base.metadata if metadata is None else metadata
    insp = inspect(engine)
    presentes = set(insp.get_table_names())
    manquantes: dict[str, list] = {}
    for nom, table in metadata.tables.items():
        if nom not in presentes:
            continue  # create_all s'en charge
        reelles = {c["name"] for c in insp.get_columns(nom)}
        absentes = [c for c in table.columns if c.name not in reelles]
        if absentes:
            manquantes[nom] = absentes
    return manquantes


def _defaut_sql(colonne) -> str | None:
    """Le défaut SERVEUR de la colonne, tel qu'il doit apparaître dans l'ALTER.

    Un défaut Python (`default=`) ne suffit pas : il ne s'applique qu'aux
    insertions faites par SQLAlchemy, jamais aux lignes DÉJÀ en base au moment
    de l'ajout. Seul `server_default` remplit l'existant.
    """
    if colonne.server_default is None:
        return None
    arg = getattr(colonne.server_default, "arg", None)
    return str(getattr(arg, "text", arg))


def _clause_ajout(table: str, colonne) -> str:
    type_sql = colonne.type.compile(dialect=None)
    defaut = _defaut_sql(colonne)
    if not colonne.nullable and defaut is None:
        # SQLite refuse une colonne NOT NULL sans défaut sur une table peuplée,
        # et inventer une valeur ici fabriquerait de la donnée que personne n'a
        # voulue. À trancher à la main.
        raise SystemExit(
            f"{table}.{colonne.name} est NOT NULL sans défaut serveur : "
            "cet outil ne devine pas de valeur de remplissage."
        )
    clause = f"ALTER TABLE {table} ADD COLUMN {colonne.name} {type_sql}"
    if defaut is not None:
        # Sans ce DEFAULT, l'ALTER passerait mais les lignes existantes
        # porteraient NULL dans une colonne déclarée NOT NULL — une base qui se
        # relit mal, ce qui est pire qu'un refus franc.
        clause += f" NOT NULL DEFAULT {defaut}" if not colonne.nullable else f" DEFAULT {defaut}"
    return clause


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--appliquer",
        action="store_true",
        help="exécute les ALTER TABLE (sans ce drapeau, l'outil ne fait que rapporter)",
    )
    args = parser.parse_args()

    if args.appliquer:
        init_db()  # les tables manquantes des deux côtés d'abord

    rien_a_faire = True
    for nom_cible, metadata, engine in cibles():
        manquantes = colonnes_manquantes(engine, metadata)
        if not manquantes:
            continue
        rien_a_faire = False
        for table, colonnes in sorted(manquantes.items()):
            for colonne in colonnes:
                clause = _clause_ajout(table, colonne)
                if args.appliquer:
                    with engine.begin() as connexion:
                        connexion.execute(text(clause))
                    print(f"appliqué [{nom_cible}] : {clause}")
                else:
                    print(f"à appliquer [{nom_cible}] : {clause}")

    if rien_a_faire:
        print("Schéma à jour des deux côtés : aucune colonne manquante.")
        return 0
    if not args.appliquer:
        print("\nRien n'a été modifié. Relancer avec --appliquer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
