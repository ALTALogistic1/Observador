"""Ce qu'une fusion ajoutera au schéma — sans toucher à aucune base réelle.

**La distinction qui a fait exister cet outil.** Le passage à blanc de
`migration_colonnes.py` répond à DEUX questions à la fois, et une seule se pose
au moment de fusionner :

    (1) qu'est-ce que CETTE FUSION ajoutera au schéma?
    (2) qu'est-ce qui manque à la PRODUCTION en ce moment?

La (2) demande les identifiants de la base durable. Les mettre dans le dépôt
défait la propriété que toute l'architecture du chantier 29 protège — une chaîne
compromise peut redémarrer le service, jamais lire la base. On ne l'échange pas
contre une commodité de vérification.

La (1), elle, ne demande rien : elle se répond en comparant les MODÈLES de deux
révisions. C'est ce que fait cet outil. Aucun secret, aucun accès à l'hôte,
aucune nouvelle surface.

**Ce que cet outil NE DIT PAS, et qui doit rester écrit dans sa sortie.** Il ne
sait rien de la dérive déjà présente en production. Une colonne qui manque
depuis six mois ne l'intéresse pas, parce qu'elle n'est pas ajoutée par cette
fusion-ci. Taire cette limite remplacerait une discipline par un mécanisme qui
rassure au-delà de ce qu'il couvre, et ce serait un recul.

**Trois catégories, dont la troisième est celle qu'on oublie.**

  ajoutées    — la chaîne les posera au déploiement;
  inchangées  — rien à faire;
  RETIRÉES du modèle — la chaîne ne les enlèvera JAMAIS de la base. Elle
                n'ajoute que. Une colonne retirée du modèle reste en production
                pour toujours, et personne ne le signale : c'est le seul endroit
                du flux où l'écart entre le modèle et la base se creuse en
                silence.

    python outils/schema_de_la_fusion.py --relever schema.json
    python outils/schema_de_la_fusion.py --comparer base.json pr.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone

#: Rappelé sous CHAQUE rapport, y compris quand il n'y a rien à dire. Une
#: vérification qui ne nomme pas sa limite finit par être lue comme couvrant
#: plus qu'elle ne couvre.
LIMITE = (
    "Cette vérification compare les MODÈLES de deux révisions : elle dit ce que "
    "la fusion ajoutera. Elle ne dit RIEN de la dérive déjà présente en "
    "production — pour ça, `migration_colonnes.py` sur l'hôte."
)


def _revision() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5, check=False,
        ).stdout.strip() or "inconnue"
    except (OSError, subprocess.SubprocessError):
        return "inconnue"


def relever() -> dict:
    """Le schéma que les modèles DE CE DÉPÔT décrivent. Aucune base ouverte.

    On lit les métadonnées SQLAlchemy directement plutôt que de créer une base
    en mémoire : `create_all` produirait le même résultat en ouvrant un moteur
    pour rien, et un moteur ouvert est une occasion de se tromper de cible.
    """
    import falkye.models  # noqa: F401 -- enregistre tous les modèles
    from falkye.models.base import Base, BaseMiroir

    bases = {}
    for nom, metadata in (("produit", Base.metadata), ("miroirs", BaseMiroir.metadata)):
        tables = {}
        for nom_table, table in sorted(metadata.tables.items()):
            tables[nom_table] = {
                "colonnes": {
                    c.name: str(c.type.compile(dialect=None)) for c in table.columns
                },
                "index": {
                    i.name: {
                        "colonnes": [c.name for c in i.columns],
                        "unique": bool(i.unique),
                    }
                    for i in table.indexes
                },
            }
        bases[nom] = tables
    return {
        "revision": _revision(),
        "releve_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bases": bases,
    }


def comparer(avant: dict, apres: dict) -> dict:
    """Ce qui change entre deux relevés, par base."""
    changements: dict[str, dict] = {}
    for nom_base, tables_apres in apres["bases"].items():
        tables_avant = avant["bases"].get(nom_base, {})
        tables_neuves, colonnes, index, retires = [], [], [], []

        for table, apres_t in sorted(tables_apres.items()):
            avant_t = tables_avant.get(table)
            if avant_t is None:
                tables_neuves.append(table)
                continue  # une table neuve apporte toutes ses colonnes avec elle
            for col, typesql in sorted(apres_t["colonnes"].items()):
                if col not in avant_t["colonnes"]:
                    colonnes.append(f"{table}.{col}  {typesql}")
            for nom_i, detail in sorted(apres_t["index"].items()):
                if nom_i not in avant_t["index"]:
                    u = "UNIQUE " if detail["unique"] else ""
                    index.append(f"{u}{nom_i}  sur {table} ({', '.join(detail['colonnes'])})")
            for col in sorted(avant_t["colonnes"]):
                if col not in apres_t["colonnes"]:
                    retires.append(f"colonne {table}.{col}")
            for nom_i in sorted(avant_t["index"]):
                if nom_i not in apres_t["index"]:
                    retires.append(f"index {nom_i} (sur {table})")

        for table in sorted(tables_avant):
            if table not in tables_apres:
                retires.append(f"table {table}")

        if tables_neuves or colonnes or index or retires:
            changements[nom_base] = {
                "tables": tables_neuves,
                "colonnes": colonnes,
                "index": index,
                "retires_du_modele": retires,
            }
    return changements


def rendre(changements: dict, revision_avant: str, revision_apres: str) -> str:
    """Le rapport, en Markdown. **Il s'écrit même quand il n'y a rien.**

    « Cette fusion n'ajoute rien au schéma » est une information : c'est ce qui
    distingue une vérification qui a tourné et n'a rien trouvé d'une
    vérification qui n'a pas tourné. Un silence ne les sépare pas.
    """
    lignes = ["### Ce que cette fusion ajoutera au schéma", ""]
    lignes.append(f"*comparaison `{revision_avant}` → `{revision_apres}`*")
    lignes.append("")

    if not changements:
        lignes.append("**Cette fusion n'ajoute rien au schéma.** Aucune table, "
                      "aucune colonne, aucun index.")
    for nom_base, detail in sorted(changements.items()):
        lignes.append(f"#### base « {nom_base} »")
        lignes.append("")
        for titre, entrees in (
            ("tables neuves", detail["tables"]),
            ("colonnes ajoutées", detail["colonnes"]),
            ("index ajoutés", detail["index"]),
        ):
            if entrees:
                lignes.append(f"**{titre}**")
                lignes.extend(f"- `{e}`" for e in entrees)
                lignes.append("")
        if detail["retires_du_modele"]:
            lignes.append("**⚠️ retirés du MODÈLE — la chaîne ne les retirera pas de la base**")
            lignes.extend(f"- `{e}`" for e in detail["retires_du_modele"])
            lignes.append("")
            lignes.append(
                "  La chaîne de déploiement n'AJOUTE que : ces objets resteront en "
                "production, indéfiniment, sans que rien ne le signale. Les retirer "
                "est un geste manuel et destructif."
            )
            lignes.append("")

    lignes.append("")
    lignes.append("---")
    lignes.append(f"*{LIMITE}*")
    return "\n".join(lignes)


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--relever", metavar="FICHIER", help="écrit le relevé du dépôt courant")
    parseur.add_argument(
        "--comparer", nargs=2, metavar=("AVANT", "APRES"), help="compare deux relevés"
    )
    args = parseur.parse_args(argv)

    if args.relever:
        with open(args.relever, "w", encoding="utf-8") as f:
            json.dump(relever(), f, ensure_ascii=False, indent=2)
        print(f"relevé écrit dans {args.relever}")
        return 0

    if args.comparer:
        with open(args.comparer[0], encoding="utf-8") as f:
            avant = json.load(f)
        with open(args.comparer[1], encoding="utf-8") as f:
            apres = json.load(f)
        print(rendre(comparer(avant, apres), avant["revision"], apres["revision"]))
        return 0

    parseur.error("choisir --relever ou --comparer")
    return 2


if __name__ == "__main__":
    sys.exit(main())
