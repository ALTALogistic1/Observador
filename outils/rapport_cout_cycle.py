"""Ce qu'un cycle a coûté en lectures, ventilé par source et par chemin.

    python outils/rapport_cout_cycle.py                 # le dernier cycle
    python outils/rapport_cout_cycle.py --jours 30      # tout l'historique récent

**Deux colonnes, deux natures, et le rapport le dit à chaque ligne.**

`appels` est un COMPTE — incrémenté au point d'appel dans le moteur, exact.
`lignes ~` est une DÉRIVATION — le compte multiplié par le prix du chemin, lui
même fonction de la population sans NEQ **du moment où le rapport est lu**. Le
tilde est là pour qu'on ne puisse pas la citer plus tard comme une mesure.

**⚠️ Ce rapport ne couvre QUE les trois chemins de résolution d'identité.** Tout
le reste du cycle — le chargement des signaux d'une entreprise, la génération des
notifications, l'enrichissement, les écritures — n'a pas de compteur et
n'apparaît nulle part ici. **Un zéro sur les trois chemins n'est donc pas un
cycle sans lectures** : le 2026-09-11, ce rapport affichait zéro pendant que le
compteur de l'hébergeur avançait de 411 963 777 lectures. La portée est imprimée
en pied de sortie, pas seulement dans cette docstring — voir `PORTEE` dans
`falkye/cout_lectures.py`.

Le vrai `rows_read` n'est pas accessible ici : le pilote libSQL qu'utilise
SQLAlchemy ne l'expose pas, seul le protocole Hrana le rend. Le jour où la
colonne `nb_lignes_lues_base` sera renseignée, elle s'affichera à côté de la
dérivation plutôt qu'à sa place — et l'écart entre les deux sera lui-même une
information.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone

CHEMINS_COLONNES = (
    ("exact", "nb_resolutions_exact"),
    ("prefixe", "nb_resolutions_prefixe"),
    ("sous_chaine", "nb_resolutions_sous_chaine"),
)


def lignes_du_rapport(db_session, depuis: datetime):
    from sqlalchemy import select

    from falkye.models.run_log import SourceRunLog

    return (
        db_session.execute(
            select(SourceRunLog)
            .where(SourceRunLog.started_at >= depuis)
            .order_by(SourceRunLog.started_at)
        )
        .scalars()
        .all()
    )


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--jours", type=int, default=1, help="fenêtre à rapporter (défaut : 1)")
    args = parseur.parse_args(argv)

    from falkye.cout_lectures import (
        AVERTISSEMENT_DERIVATION,
        PORTEE,
        PROVENANCE,
        lignes_lues_derivees,
        peremption,
        population_sans_neq,
    )
    from falkye.db import bases_sur_repli, cible_annoncee

    # La cible EN TÊTE, toujours. Deux outils qui ne disent pas à quelle base ils
    # parlent peuvent rendre des verdicts opposés sans que rien ne le signale —
    # c'est arrivé le 2026-09-09, dans la même session root.
    print(cible_annoncee())
    if bases_sur_repli():
        print(
            "\nREFUS — aucune cible n'a été choisie : "
            f"{', '.join(bases_sur_repli())} absente(s), et le repli par défaut est relatif au répertoire courant.\n"
            "  Un verdict rendu sur une base vide est le plus rassurant de tous.\n"
            "  Sur l'hôte : set -a; . /etc/falkye/falkye.env; set +a",
            file=sys.stderr,
        )
        return 2

    from falkye.db import get_session

    session = get_session()
    try:
        # **Trois absences à ne pas confondre**, et c'est tout l'objet du
        # chantier : « les colonnes n'existent pas » (base non migrée), « aucune
        # exécution » (rien n'a tourné), et « aucun coût » (ça a tourné sans rien
        # emprunter). Sans cette garde, la première se présenterait comme une
        # trace de pile, et la deuxième se lirait comme la troisième.
        # Deux chemins d'import parce que les outils se lancent des deux
        # façons : `python outils/x.py` met `outils/` sur sys.path (pas la
        # racine), la suite de tests met la racine. Emprunter la fonction de la
        # migration plutôt que de réécrire la liste des colonnes est ce qui
        # garantit qu'une colonne ajoutée là-bas est vue ici.
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
            return 2

        depuis = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=args.jours)
        lignes = lignes_du_rapport(session, depuis)
        if not lignes:
            print(f"Aucune exécution depuis {depuis:%Y-%m-%d %H:%M} — rien à rapporter.")
            print("(« aucune exécution » n'est pas « aucun coût » : c'est une absence de mesure.)")
            print(f"\n{PORTEE}")
            return 0

        population = population_sans_neq(session)
        perime = peremption(session)

        print(f"population sans NEQ au moment de la lecture : {population}")
        print(f"prix mesurés le {PROVENANCE.mesure_le} — {PROVENANCE.methode}")
        print("portée : les trois chemins de résolution SEULEMENT — détail en pied de sortie")
        if perime:
            print(f"\n⚠ TABLE DE PRIX PÉRIMÉE\n  {perime}")
            print("  Les COMPTES ci-dessous restent exacts; la dérivation est suspendue.")
        print()

        entete = f"{'source':<28}{'statut':<13}{'durée':>8}"
        for nom, _ in CHEMINS_COLONNES:
            entete += f"{nom + ' appels':>16}{nom + ' lignes ~':>18}"
        print(entete)

        totaux = {nom: 0 for nom, _ in CHEMINS_COLONNES}
        for ligne in lignes:
            appels = {nom: getattr(ligne, col) or 0 for nom, col in CHEMINS_COLONNES}
            derivees = (
                {nom: "—" for nom, _ in CHEMINS_COLONNES}
                if perime
                else lignes_lues_derivees(appels, population)
            )
            duree = f"{ligne.duree_ms / 1000:.1f}s" if ligne.duree_ms is not None else "—"
            sortie = f"{ligne.source_id:<28}{ligne.statut:<13}{duree:>8}"
            for nom, _ in CHEMINS_COLONNES:
                sortie += f"{appels[nom]:>16}{derivees[nom]:>18}"
                totaux[nom] += appels[nom]
            print(sortie)

        print()
        if perime:
            print(f"{'TOTAL (appels seulement)':<28}{'':<13}{'':>8}", end="")
            for nom, _ in CHEMINS_COLONNES:
                print(f"{totaux[nom]:>16}{'—':>18}", end="")
            print("\n\nDérivation suspendue : reprendre la table de prix.")
            print(f"\n{PORTEE}")
            return 3

        derivees_totales = lignes_lues_derivees(totaux, population)
        print(f"{'TOTAL':<28}{'':<13}{'':>8}", end="")
        for nom, _ in CHEMINS_COLONNES:
            print(f"{totaux[nom]:>16}{derivees_totales[nom]:>18}", end="")
        print(f"\n\nlignes lues dérivées, toutes sources : ~{sum(derivees_totales.values())}")

        part_repli = derivees_totales["sous_chaine"]
        if part_repli:
            pct = 100 * part_repli / max(1, sum(derivees_totales.values()))
            print(
                f"dont {pct:.0f} % par le repli par sous-chaîne "
                f"({totaux['sous_chaine']} appel(s)) — le seul chemin que l'index "
                "composite ne corrige pas."
            )
        else:
            print("le repli par sous-chaîne n'a pas été emprunté.")

        if not sum(totaux.values()):
            # Le cas qui a fait écrire la portée : trois zéros exacts, et un
            # cycle qui avait quand même lu 412 millions de lignes. Sans cette
            # phrase, la sortie la plus rassurante est celle qui couvre le
            # moins. Voir le journal des cas.
            print(
                "\n⚠ AUCUN des trois chemins n'a été emprunté — ce n'est PAS "
                "« ce cycle n'a rien lu ».\n"
                "  Ce rapport ne compte que ces trois chemins-là. Le total "
                "réel du cycle se lit\n"
                "  au compteur de l'hébergeur, relevé avant et après."
            )

        print(f"\n{AVERTISSEMENT_DERIVATION}")
        print(f"\n{PORTEE}")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
