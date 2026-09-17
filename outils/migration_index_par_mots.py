#!/usr/bin/env python3
"""Poser au miroir EN SERVICE ce que les modèles déclarent depuis le 2026-09-17.

**Pourquoi un outil et pas `init_db()`.** `create_all` crée les TABLES
manquantes; **il n'ajoute jamais une COLONNE à une table qui existe déjà.** *Sur
une base neuve les modèles suffisent; sur le miroir en service il faut ce
passage* — même raison que `outils/migration_index_chargement.py`, dont cet outil
reprend la forme.

## Ce qu'il pose

1. **`req_noms.gisement`** — de quel gisement la forme vient. *Quatre gisements
   dans l'archive, un seul indexé jusqu'ici.*
2. **`req_mots` et `req_mots_frequence`** — l'index par mots et la fréquence qui
   permet de choisir le mot le plus rare.

⚠️ **Il ne REMPLIT rien.** *Les tables et la colonne restent vides jusqu'au
prochain import* — c'est l'import qui reconstruit, et lui seul. **Une migration
qui remplirait produirait un index bâti sur un état du miroir, pas sur
l'archive.**

    python outils/migration_index_par_mots.py                # ne fait que lire
    python outils/migration_index_par_mots.py --appliquer

Sur l'hôte, l'environnement d'abord, sans quoi la cible est un fichier fantôme :

    set -a; . /etc/falkye/falkye.env; set +a
"""
from __future__ import annotations

import argparse


def colonnes_existantes(db_session, table: str) -> set[str]:
    """Les colonnes que la base porte RÉELLEMENT — lues à la base, jamais
    déduites du modèle. *Le modèle dit ce qui devrait être; seule la base dit ce
    qui est.*"""
    from sqlalchemy import text

    from falkye.models.req_nom import REQNom

    rangees = db_session.execute(
        text(f"PRAGMA table_info({table})"), bind_arguments={"mapper": REQNom}
    ).all()
    return {r[1] for r in rangees}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--appliquer", action="store_true",
                        help="ÉCRIRE le schéma (défaut : rapport seul)")
    args = parser.parse_args(argv)

    from sqlalchemy import text

    from falkye.db import refuser_si_cible_non_choisie

    code = refuser_si_cible_non_choisie()
    if code:
        return code

    from falkye.db import get_engine_miroir, get_session
    from falkye.models.base import BaseMiroir
    from falkye.models.req_mot import REQMot, REQMotFrequence  # noqa: F401
    from falkye.models.req_nom import REQNom

    print("=" * 78)
    print("MIGRATION DU MIROIR — index par mots et colonne de gisement")
    print("=" * 78)
    print("\nMODE :", "⚠️ ÉCRITURE" if args.appliquer else "rapport seul")
    print("\n⚠️ Cet outil ne REMPLIT rien. Les tables et la colonne restent vides")
    print("   jusqu'au prochain import — c'est lui qui reconstruit, et lui seul.\n")

    session = get_session()
    try:
        colonnes = colonnes_existantes(session, "req_noms")
        manque_colonne = "gisement" not in colonnes
        moteur = get_engine_miroir()
        tables = set(
            r[0] for r in session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'"),
                bind_arguments={"mapper": REQNom},
            ).all()
        )
        manquantes = [t for t in ("req_mots", "req_mots_frequence") if t not in tables]

        print(f"   req_noms.gisement      : {'⛔ ABSENTE' if manque_colonne else '✓ présente'}")
        for table in ("req_mots", "req_mots_frequence"):
            print(f"   {table:<22} : "
                  f"{'⛔ ABSENTE' if table in manquantes else '✓ présente'}")

        if not manque_colonne and not manquantes:
            print("\n   Rien à poser.")
            return 0
        if not args.appliquer:
            print("\n" + "=" * 78)
            print("   RAPPORT SEUL — rien n'a été écrit.")
            print("   Relancer avec --appliquer.")
            print("=" * 78)
            return 0

        if manque_colonne:
            session.execute(
                text("ALTER TABLE req_noms ADD COLUMN gisement VARCHAR(20)"),
                bind_arguments={"mapper": REQNom},
            )
            session.commit()
            print("\n   ✓ req_noms.gisement posée")
        if manquantes:
            # `create_all` ne touche pas aux tables qui existent — il crée
            # exactement celles qui manquent, et c'est ce qu'on veut ici.
            BaseMiroir.metadata.create_all(
                moteur,
                tables=[BaseMiroir.metadata.tables[t] for t in manquantes],
            )
            print(f"   ✓ {', '.join(manquantes)} créée(s)")

        # ⚠️ **On RELIT après coup.** *Un `ALTER TABLE` qui réussit ne prouve pas
        # que la colonne est là — c'est la leçon de l'index partiel du
        # 8 septembre, qui réussissait sans que le plan ne bouge.*
        session.expire_all()
        apres = colonnes_existantes(session, "req_noms")
        if "gisement" not in apres:
            print("\n⛔ VÉRIFICATION ÉCHOUÉE : `gisement` est toujours absente.")
            return 4
        print("\n   vérifié après coup : la colonne est là.")
        print("\n" + "=" * 78)
        print("   ⚠️ L'index reste VIDE jusqu'au prochain import du REQ.")
        print("=" * 78)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
