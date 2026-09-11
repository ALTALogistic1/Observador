"""Poser les index qui manquent aux chargements PAR ENTREPRISE.

**Ce que ces index réparent.** Le cycle charge les signaux d'une entreprise à la
fois, et `signals.company_id` ne portait aucun index : en SQLite, une clé
étrangère n'en crée pas. Chaque appel balayait donc la table entière. Mesuré sur
la base réelle le 2026-09-11, par le compteur de l'hébergeur et ses requêtes les
plus coûteuses :

    SELECT … FROM signals WHERE ? = signals.company_id
        Average Rows Read : 17 800   Count : 23 100   Avg time : 2,78 ms

23 100 × 17 800 ≈ 411 M — et le compteur a mesuré 411 963 777 lectures pour ce
cycle-là, **qui n'avait résolu aucune entreprise**. *(journal, cas 33; registre,
D37.)*

**Le second index, trouvé en le cherchant.** `evaluer_pour_company` interroge
`liens_interprovinciaux` une fois par entreprise aussi, sur `company_id_a OU
company_id_b`. La contrainte unique de la paire donne un index dont
`company_id_a` est la colonne de TÊTE : ce côté-là est couvert, l'autre ne l'est
pas, et SQLite ne peut unir deux recherches que si les deux sont indexables.
Invisible aujourd'hui parce que la table est petite, et elle ne le restera pas.

**Pourquoi un outil et pas `init_db()`.** `create_all` ne crée que les TABLES
manquantes; il n'ajoute pas un index à une table qui existe déjà. Sur une base
neuve les modèles suffisent, sur la base en service il faut ce passage — même
raison que `outils/migration_index_neq_nom.py`, dont cet outil reprend la forme.

**Pourquoi il VÉRIFIE au lieu de se croire.** Un `CREATE INDEX` qui réussit ne
prouve pas que le planificateur s'en servira : l'index partiel du 8 septembre
réussissait et le plan ne bougeait pas. L'outil relit donc `EXPLAIN QUERY PLAN`
APRÈS coup et sort en échec si une requête balaie encore.

**Et les requêtes vérifiées sont celles du MOTEUR, jamais recopiées ici.** Celle
des liens est empruntée à `falkye.expansion_interprovinciale`. Celle des signaux
n'existe dans aucune fonction — c'est SQLAlchemy qui l'émet en chargeant la
relation — elle est donc DÉRIVÉE de la relation elle-même (`Company.signals`),
paramètre à gauche compris, plutôt que réécrite de mémoire.

    python outils/migration_index_chargement.py                # ne fait que lire
    python outils/migration_index_chargement.py --appliquer

Sur l'hôte, l'environnement d'abord, sans quoi la cible est un fichier fantôme :

    set -a; . /etc/falkye/falkye.env; set +a
"""
from __future__ import annotations

import argparse
import sys

#: (nom, table, création). Déclarés AUSSI dans les modèles — ici pour la base en
#: service, là pour une base neuve. Les deux doivent dire la même chose : un test
#: le verrouille (tests/test_index_chargement.py).
INDEX = (
    ("ix_signals_company_id", "signals", "CREATE INDEX IF NOT EXISTS ix_signals_company_id ON signals (company_id)"),
    (
        "ix_liens_interprovinciaux_company_id_b",
        "liens_interprovinciaux",
        "CREATE INDEX IF NOT EXISTS ix_liens_interprovinciaux_company_id_b "
        "ON liens_interprovinciaux (company_id_b)",
    ),
)


def connexion_produit(session):
    """La connexion du moteur du PRODUIT, jamais celle des miroirs.

    La session porte DEUX moteurs, routés par métadonnée. Un `text()` brut
    n'appartient à aucune métadonnée et la session refuse de choisir : il faut
    nommer la cible par un modèle. *(falkye/db.py::get_sessionmaker.)*
    """
    from falkye.models.company import Company

    return session.connection(bind_arguments={"mapper": Company.__mapper__})


def requete_chargement_des_signaux(company_id: int = 1):
    """La requête que SQLAlchemy émet en chargeant `Company.signals`.

    **Dérivée de la relation, pas réécrite.** Le chargement d'une relation n'est
    écrit nulle part dans le code du moteur : il est émis par le chargeur, et sa
    forme — `? = signals.company_id`, paramètre à GAUCHE — vient de la paire
    locale/distante de la relation. La reconstruire depuis cette paire est ce qui
    garantit qu'on mesure le plan de la requête qui tourne vraiment. *Une requête
    tapée de mémoire à côté ne prouverait rien d'elle.*
    """
    from sqlalchemy import inspect, literal, select

    from falkye.models.company import Company

    relation = inspect(Company).relationships["signals"]
    ((_, distante),) = relation.local_remote_pairs
    return select(relation.mapper.class_).where(literal(company_id) == distante)


def requete_liens(company_id: int = 1):
    """Empruntée au moteur — jamais recopiée."""
    from falkye.expansion_interprovinciale import requete_liens_pour_company

    return requete_liens_pour_company(company_id)


#: Les chargements par entreprise, et l'index que chacun doit emprunter.
CHEMINS: tuple[tuple[str, str, str], ...] = (
    ("signaux d'une entreprise", "requete_chargement_des_signaux", "ix_signals_company_id"),
    ("liens d'une entreprise (OU)", "requete_liens", "ix_liens_interprovinciaux_company_id_b"),
)


def _requetes():
    fabriques = {
        "requete_chargement_des_signaux": requete_chargement_des_signaux,
        "requete_liens": requete_liens,
    }
    return [(libelle, fabriques[nom](), attendu) for libelle, nom, attendu in CHEMINS]


def _plan(session, requete) -> str:
    from sqlalchemy import text
    from sqlalchemy.dialects import sqlite

    sql = str(requete.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}))
    lignes = connexion_produit(session).execute(text("EXPLAIN QUERY PLAN " + sql)).all()
    return " ; ".join(str(l[-1]) for l in lignes)


def plans(session) -> dict[str, str]:
    return {libelle: _plan(session, requete) for libelle, requete, _ in _requetes()}


def index_existants(session, table: str) -> set[str]:
    from sqlalchemy import text

    lignes = connexion_produit(session).execute(
        text(f"SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='{table}'")
    ).all()
    return {nom for (nom,) in lignes if nom}


def verifier(session) -> list[str]:
    """Les chemins qui BALAIENT encore. Vide = les index servent.

    Le verdict porte sur le plan, pas sur l'existence de l'index : c'est toute la
    leçon du 8 septembre — un index posé que le planificateur ignore ne corrige
    rien et se lit comme une correction.
    """
    plan_par_libelle = plans(session)
    manques = []
    for libelle, _, attendu in _requetes():
        plan = plan_par_libelle[libelle]
        if attendu not in plan or "SCAN" in plan:
            manques.append(f"{libelle} → {plan}")
    return manques


def appliquer(session) -> None:
    from sqlalchemy import text

    connexion = connexion_produit(session)
    for _, _, creation in INDEX:
        connexion.execute(text(creation))
    session.commit()


def _afficher(plan_par_libelle: dict[str, str]) -> None:
    for libelle, plan in plan_par_libelle.items():
        marque = "!" if "SCAN" in plan else " "
        print(f"  {marque} {libelle:<30} {plan}")


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--appliquer", action="store_true", help="écrire (défaut : lire seulement)")
    args = parseur.parse_args(argv)

    from falkye.db import bases_sur_repli, cible_annoncee

    # La cible EN TÊTE, toujours — un outil de schéma qui ne dit pas à quelle
    # base il parle peut rendre un verdict sur un fichier vide (journal, cas 30).
    print(cible_annoncee())
    if bases_sur_repli():
        print(
            "\nREFUS — aucune cible n'a été choisie : "
            f"{', '.join(bases_sur_repli())} absente(s), et le repli par défaut est relatif au répertoire courant.\n"
            "  Un index posé sur une base vide se pose sans erreur, et ne corrige rien.\n"
            "  Sur l'hôte : set -a; . /etc/falkye/falkye.env; set +a",
            file=sys.stderr,
        )
        return 2

    from falkye.db import get_session

    session = get_session()
    try:
        for nom, table, _ in INDEX:
            presents = index_existants(session, table)
            etat = "déjà posé" if nom in presents else "ABSENT"
            print(f"\nindex sur `{table}` : {etat}")
            for existant in sorted(presents):
                print(f"    {existant}")

        print("\nplans AVANT :")
        _afficher(plans(session))

        if not args.appliquer:
            print("\n(lecture seule — relancer avec --appliquer pour poser les index)")
            return 0

        appliquer(session)
        print("\nindex posés.")
        print("\nplans APRÈS :")
        _afficher(plans(session))

        manques = verifier(session)
        if manques:
            print(
                "\nÉCHEC : l'index existe mais le planificateur balaie encore.\n"
                + "\n".join(f"    {m}" for m in manques)
            )
            return 1
        print(
            "\nLes deux chargements par entreprise passent par un index.\n"
            "  ⚠ Ce que ça ne dit PAS : le nombre d'appels. L'index change le prix "
            "d'un appel,\n    pas le fait qu'il y en ait un par entreprise, deux fois "
            "par cycle (registre, D37).\n"
            "  Le gain réel se lit au compteur de l'hébergeur, avant et après un cycle."
        )
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
