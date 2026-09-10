"""Refermer une ligne d'exécution qu'aucune règle ne permet de conclure.

**Quand cet outil sert, et quand il ne doit pas servir.** La bascule automatique
(falkye/sante_source.py::refermer_executions_interrompues) referme les exécutions
lancées PAR L'UNITÉ dont le délai est dépassé : systemd les aurait tuées, la
déduction est vérifiable. Elle refuse de conclure sur les autres — un cycle lancé
à la main n'est gouverné par aucun délai, et il y en a eu beaucoup.

Ces lignes-là restent ouvertes, et se signalent à chaque cycle comme non
décidables. C'est juste, et c'est aussi un coût : **une erreur bénigne mais
permanente apprend à ignorer une ligne rouge**, ce qui défait un journal
construit pour distinguer une panne d'un silence (guide d'ingénierie). Le mandat
du chantier 2 prévoit la sortie — *quand le code ne peut pas faire la distinction
automatiquement, il demande une déclaration explicite plutôt que de laisser
l'ambiguïté.*

**Trois conditions, sans lesquelles ce serait une inférence déguisée.**

1. Un AUTEUR nommé. Une décision sans auteur n'est pas une décision.
2. Un MOTIF écrit, d'au moins vingt caractères. « ok » n'est pas une raison,
   c'est une case cochée — et une case cochée ne se relit pas dans six mois.
3. Un STATUT DISTINCT — `interrompue_declaree`, jamais `interrompue`. Le statut
   est ce qu'on lit en premier, et une conclusion humaine n'a pas la même force
   de preuve qu'une déduction vérifiable.

    python outils/fermer_execution_declaree.py                     # montre les candidates
    python outils/fermer_execution_declaree.py --run 12 --run 13 \\
        --par "Alexandre Quevillon" \\
        --motif "Cycles lancés à la main le 7 septembre, tués par SIGTERM ; \\
                 aucun délai ne les gouvernait." \\
        --appliquer

Sans `--appliquer`, il ne fait que lire.
"""
from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument(
        "--run", type=int, action="append", default=[], help="identifiant de ligne à refermer"
    )
    parseur.add_argument("--par", help="qui décide — nom réel, pas un rôle")
    parseur.add_argument("--motif", help="pourquoi, en une phrase qui se relira")
    parseur.add_argument("--appliquer", action="store_true", help="écrire (défaut : lire)")
    args = parseur.parse_args(argv)

    from falkye.db import bases_sur_repli, cible_annoncee
    from falkye.sante_source import (
        DeclarationRefusee,
        executions_non_decidables,
        fermer_par_declaration,
    )

    # LA CIBLE ET LE MODE, EN TÊTE, AVANT TOUT LE RESTE.
    #
    # La cible : cet outil ÉCRIT, et il était le seul des quatre à ne pas dire
    # à quelle base — l'oubli du 2026-09-09 (journal, cas 30), un cran plus haut
    # puisqu'ici une erreur de cible poserait un statut humain sur les mauvaises
    # lignes.
    #
    # Le mode : les deux passages affichaient la MÊME liste de candidates, et
    # seule la dernière ligne distinguait « j'ai fermé » de « je pourrais
    # fermer ». Un lecteur pressé pouvait croire avoir appliqué. Le fait
    # décisif se met devant, jamais en bas — même règle que la cible.
    print(cible_annoncee())
    print("mode  : ÉCRITURE — les lignes seront refermées" if args.appliquer
          else "mode  : LECTURE SEULE — rien ne sera écrit")
    if bases_sur_repli():
        print(
            "\nREFUS — aucune cible n'a été choisie : "
            f"{', '.join(bases_sur_repli())} absente(s), et le repli par défaut est relatif au répertoire courant.\n"
            "  Poser une décision humaine sur une base que personne n'a choisie serait "
            "pire qu'un verdict faux : elle porterait un nom.\n"
            "  Sur l'hôte : set -a; . /etc/falkye/falkye.env; set +a",
            file=sys.stderr,
        )
        return 2
    print()

    from falkye.db import get_session

    session = get_session()
    try:
        # Même garde que `rapport_cout_cycle.py`, pour la même raison : sur une
        # base non migrée, la requête meurt en trace de pile et « les colonnes
        # n'existent pas » se présente comme un défaut du code. Trois absences
        # à ne pas confondre — base non migrée, aucune ligne ouverte, aucune
        # ligne non décidable.
        try:
            from outils.migration_chantier2_execution import manquantes
        except ModuleNotFoundError:  # pragma: no cover -- lancé comme script
            from migration_chantier2_execution import manquantes

        restantes = manquantes(session)
        if restantes:
            print("La migration du chantier 2 n'est pas appliquée sur cette base.")
            for _, table, colonne, _ in restantes:
                print(f"    manquante : {table}.{colonne}")
            print("\n    python outils/migration_chantier2_execution.py --appliquer")
            return 3

        candidates = executions_non_decidables(session)
        print("lignes ouvertes qu'aucune règle ne peut conclure :")
        if not candidates:
            print("    (aucune)")
        for ligne in candidates:
            print(
                f"    #{ligne.id:<5} {ligne.source_id:<26} débutée {ligne.started_at} "
                f"| lancée par : {ligne.lance_par or 'inconnu'}"
            )

        if not args.appliquer:
            print(
                "\nRien n'a été écrit (mode LECTURE SEULE, annoncé en tête).\n"
                "Pour refermer : --run <id> --par <nom> --motif <phrase> --appliquer"
            )
            return 0

        try:
            rapport = fermer_par_declaration(
                session, args.run, par=args.par or "", motif=args.motif or ""
            )
        except DeclarationRefusee as exc:
            # Bruyant, à dessein : un geste humain mal formé doit échouer, pas
            # se contenter d'un avertissement qu'on saute.
            print(f"\nREFUSÉ — {exc}")
            return 2

        print(f"\n{rapport.resume_lisible()}")
        if rapport.introuvables:
            print("Des identifiants visés n'existent pas — rien n'a été inventé pour eux.")
            return 1
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
