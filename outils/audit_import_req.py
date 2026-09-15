#!/usr/bin/env python3
"""Pourquoi le miroir ne porte qu'une société d'une série qui en compte des
milliers — mesuré **sur l'archive**, pas déduit.

**Le fait qui justifie cet outil** *(Alexandre, 2026-09-16)*. La trace d'un cas
entier a nommé le mur : `9309-3927 QUÉBEC INC.` **n'est pas dans le miroir**, par
aucun chemin — ni par NEQ, ni par nom brut, ni par sous-chaîne, ni par nom
normalisé. Et :

    nom_normalise GLOB '9309*'   →  1 ligne
    nom          LIKE '9309%'    →  1 ligne

**Une seule société en `9309-xxxx` dans 2 730 146 entrées**, là où le Registraire
en attribue des milliers. *Le moteur a fait exactement ce qu'il devait : il a
comparé la seule ligne disponible et l'a refusée. C'est le bon comportement sur
une base amputée.*

**Trois causes possibles, et elles n'ont pas le même remède.**

| cause | ce qui la prouve | remède |
|---|---|---|
| le fichier source est incomplet | la série manque **dans `Nom.csv`** | rien à faire ici — c'est au Registraire |
| l'import filtre quelque chose | la série est dans le fichier, **absente de l'index élu** | corriger le filtre |
| l'import s'arrête avant la fin | l'index **se coupe** à un rang, et la coupure est nette | corriger le parcours |

**Ce que l'outil mesure, dans cet ordre.**

1. **Les membres de l'archive, avec leurs tailles.** *Un `Nom.csv` scindé en
   plusieurs parties ferait lire une fraction sans qu'aucune erreur ne sorte* —
   `zf.open("Nom.csv")` n'ouvre qu'un membre.
2. **Les comptes bruts** : lignes et NEQ distincts par fichier.
3. **La série demandée**, comptée à trois étages : dans `Nom.csv`, dans l'index
   des noms élus, et dans le miroir. **C'est la comparaison des trois qui désigne
   la cause**, pas l'un des chiffres pris seul.
4. **Ce que l'import LAISSE TOMBER**, ligne par cause : NEQ vide, ou aucun nom
   dans l'index. *Le code le dit lui-même — « Ne devrait pas arriver […] ignorer
   plutôt que deviner un nom ».* **Un « ne devrait pas arriver » qui arrive
   224 968 fois est une mesure, pas une exception.**
5. **Le profil de coupure** : le plus grand NEQ de chaque fichier, et le plus
   grand de l'index. *Un import qui s'arrête laisse une coupure NETTE; un filtre
   laisse des trous répartis.* **La forme de l'absence distingue les deux.**

⚠️ **Il emprunte `_charger_index_noms` et `_resoudre_entreprise` au moteur.** *Un
parcours recopié à côté mesurerait sa propre copie*, et c'est précisément l'écart
qu'on cherche.

⚠️ **PORTÉE.** Lecture seule. L'archive n'est pas modifiée, le miroir non plus.
*La comparaison au miroir est facultative* — sans base, les étapes 1 à 5 tiennent
et suffisent à trancher entre les trois causes.

Usage :
    python3 outils/audit_import_req.py --chemin /opt/falkye/import/JeuDonnees.zip
    python3 outils/audit_import_req.py --chemin … --serie 9309 --sans-miroir
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import zipfile
from collections import Counter

#: Une dénomination numérique du Registraire : quatre chiffres, un tiret, quatre
#: chiffres. **C'est la FORME du nom, pas celle du NEQ** — le NEQ est un nombre à
#: dix chiffres sans rapport avec la série.
MOTIF_SERIE = re.compile(r"^(\d{4})-(\d{4})")

CSV_ATTENDUS = ("Entreprise.csv", "Nom.csv", "Etablissements.csv")


def serie_du_nom(nom: str) -> str | None:
    """La série d'une dénomination numérique, ou `None`. **`9309-3927` rend
    `9309`** — c'est le bloc que le Registraire attribue par tranches."""
    correspondance = MOTIF_SERIE.match((nom or "").strip())
    return correspondance.group(1) if correspondance else None


def profil_de_coupure(neqs: set[str]) -> dict:
    """De quoi distinguer une COUPURE d'un TROU.

    *Un import qui s'arrête laisse un maximum franc et aucun trou avant lui; un
    filtre laisse des absences réparties sur toute l'étendue.* **La forme de
    l'absence distingue les deux causes, et aucun total ne le fait.**
    """
    if not neqs:
        return {"n": 0, "min": None, "max": None}
    tries = sorted(neqs)
    return {"n": len(neqs), "min": tries[0], "max": tries[-1]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--chemin", required=True, help="l'archive JeuDonnees.zip")
    parser.add_argument("--serie", default="9309",
                        help="la série de dénominations numériques à pister (défaut 9309)")
    parser.add_argument("--sans-miroir", action="store_true",
                        help="ne pas ouvrir la base (les étapes 1 à 5 suffisent)")
    parser.add_argument("--exemples", type=int, default=10)
    args = parser.parse_args(argv)

    try:
        from falkye.sources.req import (
            _charger_index_etablissements,
            _charger_index_noms,
            _en_tete_csv,
            _resoudre_entreprise,
        )
    except ImportError as exc:  # pragma: no cover - dépend de l'environnement
        print(f"Import impossible ({exc}). Lancer depuis la racine du dépôt.", file=sys.stderr)
        return 2

    from outils.archives_req import avertissement, ligne_de_provenance, resoudre

    archive = resoudre(args.chemin)
    if archive is None:
        print(f"⛔ aucune archive à {args.chemin!r}.", file=sys.stderr)
        return 2
    args.chemin = str(archive)

    print("=" * 78)
    print("POURQUOI LE MIROIR NE PORTE QU'UNE SOCIÉTÉ DE LA SÉRIE")
    print("=" * 78)
    print(f"\n{ligne_de_provenance(archive)}")
    # La provenance AU-DESSUS du chiffre, jamais en bas de page : un chiffre lu
    # sans sa date est une promesse que personne ne tient.
    vieillissement = avertissement(archive)
    if vieillissement:
        print(f"\n{vieillissement}")
    print(f"série   : {args.serie}-xxxx")
    print("\nPORTÉE : lecture seule. Ni l'archive ni le miroir ne sont modifiés.")

    try:
        zf = zipfile.ZipFile(args.chemin)
    except (OSError, zipfile.BadZipFile) as exc:
        print(f"\n⛔ archive illisible : {exc}", file=sys.stderr)
        return 2

    with zf:
        # --- 1. les membres ------------------------------------------------
        print("\n" + "-" * 78)
        print("1. LES MEMBRES DE L'ARCHIVE — un fichier SCINDÉ se lit ici")
        print("-" * 78)
        print("\n   `zf.open(\"Nom.csv\")` n'ouvre QU'UN membre. Si le Registraire")
        print("   publie Nom_1.csv, Nom_2.csv…, l'import lit une fraction et")
        print("   rien ne le signale.\n")
        membres = zf.infolist()
        for info in sorted(membres, key=lambda i: -i.file_size):
            marque = "  ←" if info.filename in CSV_ATTENDUS else ""
            print(f"      {info.file_size:>14,}".replace(",", " ")
                  + f"  {info.filename}{marque}")
        familles = Counter(re.sub(r"[_-]?\d+(?=\.csv$)", "", m.filename) for m in membres)
        scindes = {n: c for n, c in familles.items() if c > 1}
        if scindes:
            print("\n   ⚠️ FICHIERS APPAREMMENT SCINDÉS :")
            for nom, combien in scindes.items():
                print(f"      {nom} → {combien} membres")
            print("      L'import n'en lit QU'UN. C'est une cause suffisante à elle seule.")
        else:
            print("\n   Aucun fichier scindé : chaque CSV attendu est en un seul membre.")

        manquants = [n for n in CSV_ATTENDUS if n not in zf.namelist()]
        if manquants:
            print(f"\n   ⛔ CSV attendu(s) absent(s) : {', '.join(manquants)}")
            return 1

        # --- 2. les comptes bruts -------------------------------------------
        print("\n" + "-" * 78)
        print("2. LES COMPTES BRUTS")
        print("-" * 78)
        neqs_par_fichier: dict[str, set[str]] = {}
        noms_de_la_serie: list[tuple[str, str]] = []
        lignes_par_fichier: dict[str, int] = {}
        for nom_csv in CSV_ATTENDUS:
            neqs: set[str] = set()
            lignes = 0
            with zf.open(nom_csv) as brut:
                texte = io.TextIOWrapper(brut, encoding="utf-8-sig", errors="replace")
                for rangee in csv.DictReader(texte):
                    lignes += 1
                    neq = (rangee.get("NEQ") or "").strip()
                    if neq:
                        neqs.add(neq)
                    if nom_csv == "Nom.csv":
                        valeur = (rangee.get("NOM_ASSUJ") or "").strip()
                        if serie_du_nom(valeur) == args.serie:
                            noms_de_la_serie.append((neq, valeur))
            neqs_par_fichier[nom_csv] = neqs
            lignes_par_fichier[nom_csv] = lignes
            print(f"\n   {nom_csv}")
            print(f"      lignes        : {lignes:,}".replace(",", " "))
            print(f"      NEQ distincts : {len(neqs):,}".replace(",", " "))
            print(f"      en-tête       : {len(_en_tete_csv(zf, nom_csv))} colonne(s)")

        # --- 3. la série, à trois étages -------------------------------------
        print("\n" + "-" * 78)
        print(f"3. LA SÉRIE {args.serie}-xxxx, À TROIS ÉTAGES")
        print("-" * 78)
        noms = _charger_index_noms(zf)
        elus_serie = {neq: n for neq, n in noms.items() if serie_du_nom(n) == args.serie}
        neqs_serie_fichier = {neq for neq, _ in noms_de_la_serie if neq}
        print(f"\n   dans Nom.csv (toutes lignes)   : {len(noms_de_la_serie):,}".replace(",", " "))
        print(f"   NEQ distincts porteurs         : {len(neqs_serie_fichier):,}".replace(",", " "))
        print(f"   dans l'index des noms ÉLUS     : {len(elus_serie):,}".replace(",", " "))
        perdus_a_lelection = neqs_serie_fichier - set(elus_serie)
        print(f"   perdus à l'ÉLECTION du nom     : {len(perdus_a_lelection):,}".replace(",", " "))
        if perdus_a_lelection:
            print("      ⚠️ Ces NEQ portent un nom de la série dans Nom.csv, mais le nom")
            print("         ÉLU pour eux est un autre — l'entreprise existe au miroir")
            print("         sous un nom différent. Ce n'est PAS une absence.")
            for neq in sorted(perdus_a_lelection)[: args.exemples]:
                print(f"         neq={neq}  élu={noms.get(neq)!r}")
        for neq, valeur in noms_de_la_serie[: args.exemples]:
            print(f"      exemple : neq={neq}  {valeur!r}")

        # --- 4. ce que l'import laisse tomber ---------------------------------
        print("\n" + "-" * 78)
        print("4. CE QUE L'IMPORT LAISSE TOMBER — par cause, pas en bloc")
        print("-" * 78)
        etablissements = _charger_index_etablissements(zf)
        causes: Counter = Counter()
        retenus: set[str] = set()
        abandons_serie: list[str] = []
        with zf.open("Entreprise.csv") as brut:
            texte = io.TextIOWrapper(brut, encoding="utf-8-sig", errors="replace")
            for rangee in csv.DictReader(texte):
                neq = (rangee.get("NEQ") or "").strip()
                resolue = _resoudre_entreprise(rangee, noms, etablissements)
                if resolue is None:
                    if not neq:
                        causes["NEQ vide dans Entreprise.csv"] += 1
                    elif not noms.get(neq):
                        causes["aucun nom dans l'index — LIGNE ABANDONNÉE"] += 1
                        if neq in neqs_serie_fichier:
                            abandons_serie.append(neq)
                    else:
                        causes["abandonnée pour une autre raison"] += 1
                else:
                    causes["retenue"] += 1
                    retenus.add(resolue.neq)
        print()
        total = sum(causes.values())
        for cause, combien in causes.most_common():
            part = f"  ({100 * combien / total:.2f} %)" if total else ""
            print(f"      {combien:>10,}".replace(",", " ") + f"  {cause}{part}")
        print(f"\n   entreprises RETENUES : {len(retenus):,}".replace(",", " "))
        if abandons_serie:
            print(f"\n   ⚠️ {len(abandons_serie)} NEQ de la série {args.serie} sont ABANDONNÉS")
            print("      faute de nom dans l'index. C'est la cause « l'import filtre ».")
            for neq in abandons_serie[: args.exemples]:
                print(f"         neq={neq}")

        # --- 5. coupure ou trou ? ---------------------------------------------
        print("\n" + "-" * 78)
        print("5. COUPURE OU TROU — la FORME de l'absence désigne la cause")
        print("-" * 78)
        for libelle, ensemble in (
            ("NEQ d'Entreprise.csv", neqs_par_fichier["Entreprise.csv"]),
            ("NEQ de Nom.csv", neqs_par_fichier["Nom.csv"]),
            ("NEQ ayant un nom élu", set(noms)),
            ("NEQ retenus par l'import", retenus),
        ):
            profil = profil_de_coupure(ensemble)
            print(f"\n   {libelle}")
            print(f"      {profil['n']:,}".replace(",", " ")
                  + f"   de {profil['min']} à {profil['max']}")
        sans_nom = neqs_par_fichier["Entreprise.csv"] - set(noms)
        if sans_nom:
            profil = profil_de_coupure(sans_nom)
            print(f"\n   NEQ d'Entreprise.csv SANS nom élu : {profil['n']:,}".replace(",", " "))
            print(f"      de {profil['min']} à {profil['max']}")
            print("\n      ⚠️ Lecture : si ces NEQ sont TOUS au-dessus d'un seuil, le")
            print("         parcours de Nom.csv s'est arrêté — c'est « l'import s'arrête ».")
            print("         S'ils sont RÉPARTIS sur toute l'étendue, c'est un filtre ou")
            print("         une absence du fichier source. **Deux remèdes opposés.**")

        # --- 6. le miroir, si on l'a ------------------------------------------
        if args.sans_miroir:
            print("\n(miroir non consulté — --sans-miroir)")
            return 0
        try:
            from sqlalchemy import text

            from falkye.db import get_session
            from falkye.models.req_entry import REQEntry
        except ImportError as exc:  # pragma: no cover
            print(f"\n(miroir non consultable : {exc})")
            return 0

        # LA CIBLE, ANNONCÉE ET EXIGÉE — juste avant d'ouvrir, jamais après
        # `parse_args` : un mode qui ne touche aucune base ne doit pas être
        # refusé. Sans ce refus, le repli CRÉE `./data/*.sqlite3` dans le
        # répertoire courant et le verdict porte sur une base vide.
        from falkye.db import refuser_si_cible_non_choisie

        code = refuser_si_cible_non_choisie()
        if code:
            return code

        session = get_session()
        try:
            print("\n" + "-" * 78)
            print("6. LE MIROIR, EN FACE")
            print("-" * 78)
            # LE PIÈGE DES DEUX BASES. La session porte DEUX moteurs (falkye/db.py) et
            # aucun n'est le défaut : SQLAlchemy route par métadonnée, donc une requête
            # ORM sur `REQEntry` trouve son moteur seule, mais un `text()` n'a aucune
            # métadonnée à router et lève `UnboundExecutionError`. La connexion se
            # demande explicitement, par le mapper du modèle visé — même geste que
            # `falkye/cout_lectures.py` et les outils de migration.
            connexion_miroir = session.connection(bind_arguments={"mapper": REQEntry.__mapper__})
            total_miroir = connexion_miroir.execute(
                text("SELECT count(*) FROM req_entries")
            ).scalar() or 0
            dans_miroir = connexion_miroir.execute(
                text("SELECT count(*) FROM req_entries WHERE nom LIKE :m"),
                {"m": f"{args.serie}-%"},
            ).scalar() or 0
            print(f"\n   entrées au miroir              : {total_miroir:,}".replace(",", " "))
            print(f"   entreprises RETENUES à l'import : {len(retenus):,}".replace(",", " "))
            ecart = len(retenus) - total_miroir
            if ecart:
                print(f"\n   ⚠️ ÉCART DE {ecart:+,}".replace(",", " ")
                      + " entre ce que l'import retient et ce que le miroir porte.")
                print("      L'import a donc été interrompu, ou le miroir a été écrit")
                print("      par une autre exécution que celle-ci.")
            else:
                print("\n   ✅ Les deux comptes concordent : l'import est allé au bout.")
            print(f"\n   série {args.serie} au miroir        : {dans_miroir}")
            print(f"   série {args.serie} retenue à l'import : "
                  f"{len(set(elus_serie) & retenus)}")
            print("\n   ⚠️ Un écart ICI désigne le miroir; un accord désigne l'archive.")
            return 0
        finally:
            session.close()


if __name__ == "__main__":
    raise SystemExit(main())
