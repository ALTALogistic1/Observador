"""Ajouter les colonnes du chantier 2 aux trois journaux d'exécution.

**Ce que cette migration installe.** Un identifiant d'exécution partagé, et les
deux mesures de coût d'une exécution :

    source_run_logs      (base du PRODUIT, distante)
        execution_id, nb_lignes_source, nb_lignes_lues_base, duree_ms,
        nb_resolutions_exact, nb_resolutions_prefixe, nb_resolutions_sous_chaine,
        lance_par
    diff_run_historique  (base des MIROIRS, fichier local)
        execution_id
    diff_quarantaines    (base des MIROIRS, fichier local)
        execution_id
    journal_exploitation (base du PRODUIT, distante)
        repli_id — index UNIQUE

**Deux bases, et c'est le fait qui commande.** Le mandat demande « un
identifiant d'exécution partagé permettant de rattacher les trois traces à un
même run ». Il ne pouvait pas savoir que le découpage des bases (2026-09-06) est
arrivé après sa phase 0. Conséquence : l'identifiant ne peut PAS être une clé
étrangère, aucune requête SQL ne joint les trois tables, et cette migration écrit
dans DEUX cibles — dont une seule est facturée.

**Pourquoi un outil et pas `init_db()`.** `create_all()` ne crée que les tables
manquantes; il n'ajoute jamais une colonne à une table qui existe déjà.

**Retour arrière.** Additive : les colonnes sont nullables et rien n'est réécrit.
Le retour arrière est `DROP INDEX` puis `ALTER TABLE ... DROP COLUMN`, dans cet
ordre — SQLite refuse de retirer une colonne tant qu'un index porte dessus
(« error in index … after drop column »). Pas une restauration : celle-ci est le
filet des migrations qui MODIFIENT des données, et celle-ci n'en modifie aucune.

    python outils/migration_chantier2_execution.py               # ne fait que lire
    python outils/migration_chantier2_execution.py --appliquer

Sans `--appliquer`, il montre l'état des deux bases sans rien écrire.
"""
from __future__ import annotations

import argparse
import sys

# (modèle, table, colonne, type SQL). Le modèle sert à router vers la BONNE base :
# la session porte deux moteurs, et un `text()` brut n'appartient à aucune
# métadonnée (voir falkye/db.py::get_sessionmaker).
COLONNES: tuple[tuple[str, str, str, str], ...] = (
    ("SourceRunLog", "source_run_logs", "execution_id", "VARCHAR(32)"),
    ("SourceRunLog", "source_run_logs", "nb_lignes_source", "INTEGER"),
    ("SourceRunLog", "source_run_logs", "nb_lignes_lues_base", "INTEGER"),
    ("SourceRunLog", "source_run_logs", "duree_ms", "INTEGER"),
    ("SourceRunLog", "source_run_logs", "nb_resolutions_exact", "INTEGER"),
    ("SourceRunLog", "source_run_logs", "nb_resolutions_prefixe", "INTEGER"),
    ("SourceRunLog", "source_run_logs", "nb_resolutions_sous_chaine", "INTEGER"),
    ("DiffRunHistorique", "diff_run_historique", "execution_id", "VARCHAR(32)"),
    ("DiffQuarantaine", "diff_quarantaines", "execution_id", "VARCHAR(32)"),
    ("SourceRunLog", "source_run_logs", "lance_par", "VARCHAR(10)"),
    ("JournalExploitation", "journal_exploitation", "repli_id", "VARCHAR(32)"),
)

# (modèle, nom, table, colonne, unique). `repli_id` est UNIQUE : deux reprises
# concurrentes du journal de repli doivent se heurter à la base plutôt que de se
# fier chacune à une lecture faite juste avant.
INDEX = (
    ("SourceRunLog", "ix_source_run_logs_execution_id", "source_run_logs", "execution_id", False),
    ("DiffRunHistorique", "ix_diff_run_historique_execution_id", "diff_run_historique", "execution_id", False),
    ("DiffQuarantaine", "ix_diff_quarantaines_execution_id", "diff_quarantaines", "execution_id", False),
    ("JournalExploitation", "ix_journal_exploitation_repli_id", "journal_exploitation", "repli_id", True),
)


def _modele(nom: str):
    from falkye.models.diff_quarantaine import DiffQuarantaine
    from falkye.models.diff_run_historique import DiffRunHistorique
    from falkye.models.journal_exploitation import JournalExploitation
    from falkye.models.run_log import SourceRunLog

    return {
        "SourceRunLog": SourceRunLog,
        "DiffRunHistorique": DiffRunHistorique,
        "DiffQuarantaine": DiffQuarantaine,
        "JournalExploitation": JournalExploitation,
    }[nom]


def connexion(session, nom_modele: str):
    """La connexion du moteur qui porte CE modèle — jamais l'autre."""
    return session.connection(bind_arguments={"mapper": _modele(nom_modele).__mapper__})


def colonnes_presentes(session, nom_modele: str, table: str) -> set[str]:
    from sqlalchemy import text

    lignes = connexion(session, nom_modele).execute(
        text(f"SELECT name FROM pragma_table_info('{table}')")
    ).all()
    return {nom for (nom,) in lignes}


def manquantes(session) -> list[tuple[str, str, str, str]]:
    """Les colonnes qui restent à poser. Vide = la migration est faite."""
    cache: dict[tuple[str, str], set[str]] = {}
    restantes = []
    for modele, table, colonne, typesql in COLONNES:
        cle = (modele, table)
        if cle not in cache:
            cache[cle] = colonnes_presentes(session, modele, table)
        if colonne not in cache[cle]:
            restantes.append((modele, table, colonne, typesql))
    return restantes


def appliquer(session) -> list[str]:
    """Pose les colonnes et leurs index. Rend la liste des gestes faits."""
    from sqlalchemy import text

    faits = []
    for modele, table, colonne, typesql in manquantes(session):
        connexion(session, modele).execute(
            text(f"ALTER TABLE {table} ADD COLUMN {colonne} {typesql}")
        )
        faits.append(f"{table}.{colonne}")
    for modele, nom_index, table, colonne, unique in INDEX:
        mot = "UNIQUE INDEX" if unique else "INDEX"
        connexion(session, modele).execute(
            text(f"CREATE {mot} IF NOT EXISTS {nom_index} ON {table} ({colonne})")
        )
    session.commit()
    return faits


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--appliquer", action="store_true", help="écrire (défaut : lire seulement)")
    args = parseur.parse_args(argv)

    from falkye.db import get_session

    session = get_session()
    try:
        restantes = manquantes(session)
        print("colonnes attendues par le chantier 2 :")
        for modele, table, colonne, _ in COLONNES:
            present = (modele, table, colonne) not in {(m, t, c) for m, t, c, _ in restantes}
            print(f"    {'✓' if present else ' '} {table}.{colonne}")

        if not args.appliquer:
            if restantes:
                print(f"\n({len(restantes)} manquante(s) — relancer avec --appliquer)")
            else:
                print("\n(rien à faire)")
            return 0

        faits = appliquer(session)
        print(f"\n{len(faits)} colonne(s) posée(s) : {', '.join(faits) or 'aucune'}")

        # VÉRIFIER, pas se croire : une migration qui se déclare faite parce que
        # la commande n'a pas levé est le défaut que l'index partiel a montré le
        # 2026-09-08 (voir outils/migration_index_neq_nom.py).
        reste = manquantes(session)
        if reste:
            print("\nÉCHEC : après application, il manque encore " +
                  ", ".join(f"{t}.{c}" for _, t, c, _ in reste))
            return 1
        print(f"Les {len(COLONNES)} colonnes sont en place dans les deux bases.")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
