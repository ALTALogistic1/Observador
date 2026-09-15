#!/usr/bin/env python3
"""Le pont qui dort dans `Nom.csv` — **combien des non résolues s'apparient à un
nom que le chargeur a jeté**, et **ce qu'elles sont juridiquement**.

**Les deux faits qui font exister cet outil** *(2026-09-16)*.

*(1)* **Le chargeur élit UN nom par NEQ et jette les autres.**
`_charger_index_noms` retient le nom en vigueur de type `M` (dénomination
sociale), puis `N`, puis autre — *et tous les autres noms de l'entreprise sont
perdus à l'entrée du miroir.* **Donc `Construction Pierre Robert inc.` et
`Pierre Robert - Entrepreneur Général inc.` ne se rejoignent pas aujourd'hui,
alors que le registre leur donne le même NEQ.** *Le pont est dans le fichier
depuis le début.*

*(2)* **Le miroir est complet pour ce que la source publie.** La ventilation du
16 septembre a montré que **96,6 % des NEQ sans nom élu sont des personnes
physiques exploitant une entreprise individuelle**, et 0 % chez les présents :
*le Registraire ne publie pas leur nom, et c'est légitime.* **Donc une non
résolue introuvable au miroir n'est pas forcément un défaut du produit — c'est
peut-être une entreprise que la source ne nomme pas.**

**Les trois questions, et elles se répondent dans cet ordre.**

1. **Combien des non résolues s'apparient à un nom de `Nom.csv`** — *tous* les
   noms, pas seulement l'élu.
2. Parmi celles-là, **combien s'apparient à un nom que le chargeur a JETÉ**.
   *C'est ça, la mesure du pont* : celles qui s'apparient au nom élu se
   résoudraient déjà, et leur échec a une autre cause.
3. **Quelle forme juridique elles portent** *(`COD_FORME_JURI`)*, **et par
   source**. ⚠️ **C'est cette ventilation qui décide si le mur est un défaut ou
   une limite** : *si la majorité sont des personnes physiques, ce ne sont pas des
   prospects que le produit rate — ce sont des prospects qu'il ne devrait
   peut-être pas détecter.* **Le corpus vise les PME en croissance; une
   exploitation individuelle n'est pas cette clientèle.**

⚠️ **PORTÉE, et elle est étroite.**

- **L'appariement se fait par ÉGALITÉ de forme normalisée**, jamais par score.
  *Le compte rendu est un PLANCHER* — une entreprise dont le nom diffère d'un
  caractère n'est pas comptée. **La question posée est « le pont existe-t-il »,
  pas « jusqu'où peut-on l'étirer ».**
- **Rien n'est écrit.** Aucun NEQ posé, aucun nom ajouté au miroir. *Un pont
  mesuré n'est pas un pont construit.*
- ⚠️ **Un nom d'entreprise individuelle peut être apparié à tort.** *Deux
  personnes différentes peuvent déclarer le même nom commercial*, et l'égalité
  de forme ne les sépare pas. **Le compte des NEQ multiples par nom est rendu
  pour que ça se voie.**
- **Mémoire** : l'index des noms élus est celui du moteur, tenu en entier
  (~2,7 M entrées). *Le reste est borné aux noms recherchés, pas au fichier.*

Usage :
    python3 outils/pont_des_noms_rejetes.py --chemin /opt/falkye/import
    python3 outils/pont_des_noms_rejetes.py --chemin … --exemples 30
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
import zipfile
from collections import Counter

#: Au-delà, la ventilation cesse d'être lisible et le code redevient l'information.
VALEURS_MAX = 20


def statut_du_nom(stat: str, typ: str) -> str:
    """La graphie lisible d'un couple `STAT_NOM` / `TYP_NOM_ASSUJ`.

    **`V` = en vigueur, `M` = dénomination sociale, `N` = nom.** *Le chargeur élit
    `V`+`M`, puis `V`+`N`, puis le reste — tout ce qui n'est pas élu est perdu.*
    """
    etat = "en vigueur" if (stat or "").upper() == "V" else f"statut {stat or '(vide)'}"
    genre = {"M": "dénomination sociale", "N": "nom"}.get((typ or "").upper(),
                                                          f"type {typ or '(vide)'}")
    return f"{etat}, {genre}"


def classer_appariement(nom_elu: str | None, nom_apparie: str, normaliser) -> str:
    """Le nom apparié est-il celui que le chargeur a retenu, ou un qu'il a jeté?

    **C'est la distinction qui mesure le pont.** *Une non résolue qui s'apparie au
    nom ÉLU se résoudrait déjà : son échec a une autre cause, et la compter comme
    un gain du pont gonflerait le chiffre.*
    """
    if nom_elu is None:
        return "aucun nom élu — l'entreprise n'est PAS au miroir"
    if normaliser(nom_elu) == normaliser(nom_apparie):
        return "apparié au nom ÉLU — le pont n'y changerait rien"
    return "apparié à un nom JETÉ par le chargeur — LE PONT"


def part(compteur: Counter, valeur: str) -> float:
    total = sum(compteur.values())
    return 100.0 * compteur.get(valeur, 0) / total if total else 0.0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--chemin", required=True, help="l'archive, ou le répertoire")
    parser.add_argument("--exemples", type=int, default=15)
    args = parser.parse_args(argv)

    try:
        from sqlalchemy import select

        from falkye.db import get_session
        from falkye.models.company import Company
        from falkye.models.signal import Signal
        from falkye.sources.column_mapping import normaliser
        from falkye.sources.req import _charger_index_noms
    except ImportError as exc:  # pragma: no cover - dépend de l'environnement
        print(f"Import impossible ({exc}). Lancer depuis la racine du dépôt.", file=sys.stderr)
        return 2

    from outils.archives_req import avertissement, ligne_de_provenance, resoudre
    from outils.profil_des_absents_req import charger_domaines, ventilation_comparee

    archive = resoudre(args.chemin)
    if archive is None:
        print(f"⛔ aucune archive à {args.chemin!r}.", file=sys.stderr)
        return 2

    print("=" * 78)
    print("LE PONT QUI DORT DANS Nom.csv")
    print("=" * 78)
    print(f"\n{ligne_de_provenance(archive)}")
    vieil = avertissement(archive)
    if vieil:
        print(f"\n{vieil}")
    print("\nPORTÉE : appariement par ÉGALITÉ de forme normalisée, jamais par score.")
    print("         Le compte rendu est un PLANCHER. Rien n'est écrit en base.")

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
        # --- les non résolues, et la source qui les a créées ----------------
        entreprises = session.execute(
            select(Company).where(Company.neq.is_(None))
        ).scalars().all()
        sources_par_company: dict[int, set[str]] = {}
        for company_id, source_id in session.execute(
            select(Signal.company_id, Signal.source_id)
        ).all():
            sources_par_company.setdefault(company_id, set()).add(source_id)

        cherchees: dict[str, list] = {}
        for company in entreprises:
            forme = normaliser(company.nom_detecte or "")
            if forme:
                cherchees.setdefault(forme, []).append(company)
        print(f"\nentreprises sans NEQ        : {len(entreprises)}")
        print(f"formes normalisées distinctes : {len(cherchees)}")
        if not cherchees:
            print("Rien à chercher.")
            return 0

        # --- passe 1 : TOUS les noms de Nom.csv, bornée aux formes cherchées -
        with zipfile.ZipFile(archive) as zf:
            libelles = charger_domaines(zf)
            trouves: dict[str, list[dict]] = {}
            lignes_nom = 0
            with zf.open("Nom.csv") as brut:
                texte = io.TextIOWrapper(brut, encoding="utf-8-sig", errors="replace")
                for rangee in csv.DictReader(texte):
                    lignes_nom += 1
                    nom = (rangee.get("NOM_ASSUJ") or "").strip()
                    if not nom:
                        continue
                    forme = normaliser(nom)
                    if forme not in cherchees:
                        continue
                    trouves.setdefault(forme, []).append({
                        "neq": (rangee.get("NEQ") or "").strip(),
                        "nom": nom,
                        "stat": (rangee.get("STAT_NOM") or "").strip(),
                        "typ": (rangee.get("TYP_NOM_ASSUJ") or "").strip(),
                    })
            print(f"lignes lues dans Nom.csv      : {lignes_nom:,}".replace(",", " "))

            # --- l'index des noms ÉLUS, celui du moteur ---------------------
            print("\n… élection des noms par la fonction DU MOTEUR (quelques minutes)",
                  flush=True)
            elus = _charger_index_noms(zf)

            # --- les formes juridiques des NEQ appariés ---------------------
            neqs_apparies = {e["neq"] for lot in trouves.values() for e in lot if e["neq"]}
            formes_juridiques: dict[str, str] = {}
            if neqs_apparies:
                with zf.open("Entreprise.csv") as brut:
                    texte = io.TextIOWrapper(brut, encoding="utf-8-sig", errors="replace")
                    for rangee in csv.DictReader(texte):
                        neq = (rangee.get("NEQ") or "").strip()
                        if neq in neqs_apparies:
                            formes_juridiques[neq] = (
                                rangee.get("COD_FORME_JURI") or ""
                            ).strip() or "(vide)"

        # --- le classement ---------------------------------------------------
        classes: Counter = Counter()
        formes_pont: Counter = Counter()
        formes_toutes: Counter = Counter()
        par_source_apparie: Counter = Counter()
        par_source_total: Counter = Counter()
        exemples: dict[str, list] = {}
        noms_ambigus = 0

        for forme, companies in cherchees.items():
            lot = trouves.get(forme) or []
            neqs_distincts = {e["neq"] for e in lot if e["neq"]}
            if len(neqs_distincts) > 1:
                noms_ambigus += 1
            for company in companies:
                for source_id in sources_par_company.get(company.id, {"(aucune)"}):
                    par_source_total[source_id] += 1
                if not lot:
                    classes["introuvable dans Nom.csv — la source ne la NOMME pas"] += 1
                    if len(exemples.setdefault("introuvable", [])) < args.exemples:
                        exemples["introuvable"].append((company, None, None))
                    continue
                entree = lot[0]
                classe = classer_appariement(elus.get(entree["neq"]), entree["nom"], normaliser)
                classes[classe] += 1
                code = formes_juridiques.get(entree["neq"], "(inconnu)")
                formes_toutes[code] += 1
                if classe.endswith("LE PONT"):
                    formes_pont[code] += 1
                    for source_id in sources_par_company.get(company.id, {"(aucune)"}):
                        par_source_apparie[source_id] += 1
                cle = "pont" if classe.endswith("LE PONT") else "elu"
                if len(exemples.setdefault(cle, [])) < args.exemples:
                    exemples[cle].append((company, entree, elus.get(entree["neq"])))

        # --- 1. le pont --------------------------------------------------------
        print("\n" + "=" * 78)
        print("1. LE PONT — combien s'apparient à un nom que le chargeur a JETÉ")
        print("=" * 78)
        print()
        for classe, n in classes.most_common():
            marque = "   ←" if classe.endswith("LE PONT") else ""
            print(f"   {n:>7}  {classe}{marque}")
        pont = sum(n for c, n in classes.items() if c.endswith("LE PONT"))
        print(f"\n   → {pont} entreprise(s) se résoudraient si le chargeur gardait TOUS les noms.")
        if noms_ambigus:
            print(f"\n   ⚠️ {noms_ambigus} forme(s) de nom correspondent à PLUSIEURS NEQ.")
            print("      Deux personnes peuvent déclarer le même nom commercial, et")
            print("      l'égalité de forme ne les sépare pas. Ces appariements-là ne")
            print("      sont pas résolvables sans autre chose que le nom.")

        # --- 2. la forme juridique ---------------------------------------------
        print("\n" + "=" * 78)
        print("2. LA FORME JURIDIQUE — défaut du produit, ou limite de la clientèle?")
        print("=" * 78)
        print("\n   Ventilation des appariées par COD_FORME_JURI.")
        print("   ⚠️ Si la majorité sont des personnes physiques, ce ne sont pas des")
        print("      prospects que le produit rate — ce sont des prospects qu'il ne")
        print("      devrait peut-être pas détecter. Le corpus vise les PME en croissance.")
        print(f"\n   {'code':<10}{'toutes':>10}{'dont pont':>12}{'part':>9}   libellé")
        for code, n in formes_toutes.most_common(VALEURS_MAX):
            libelle = libelles.get(("FORM_JURI", code), "")
            print(f"   {code:<10}{n:>10}{formes_pont.get(code, 0):>12}"
                  f"{part(formes_toutes, code):>8.1f}%   {libelle[:40]}")
        if not formes_toutes:
            print("      aucune appariée — rien à ventiler.")
            print("      ⚠️ Ce n'est pas « 0 % de personnes physiques » : c'est zéro mesure.")

        # --- 3. par source ------------------------------------------------------
        print("\n" + "=" * 78)
        print("3. PAR SOURCE — laquelle fabrique le mur, et laquelle le pont réparerait")
        print("=" * 78)
        print(f"\n   {'source':<28}{'non résolues':>14}{'réparées par le pont':>22}{'part':>8}")
        for source_id, total in par_source_total.most_common():
            repare = par_source_apparie.get(source_id, 0)
            print(f"   {source_id:<28}{total:>14}{repare:>22}"
                  f"{100 * repare / total if total else 0:>7.1f}%")
        print("\n   ⚠️ Une entreprise détectée par trois sources compte dans les trois.")
        print("      Ces parts décrivent des SOURCES, pas des populations disjointes.")

        # --- les exemples -------------------------------------------------------
        for cle, titre in (
            ("pont", "APPARIÉES À UN NOM JETÉ — le pont, en clair"),
            ("elu", "APPARIÉES AU NOM ÉLU — leur échec a une AUTRE cause"),
            ("introuvable", "INTROUVABLES DANS Nom.csv — la source ne les nomme pas"),
        ):
            lot = exemples.get(cle) or []
            if not lot:
                continue
            print("\n" + "-" * 78)
            print(f"{titre}  —  {len(lot)} montrée(s)")
            print("-" * 78)
            for company, entree, nom_elu in lot:
                print(f"\n   détecté : {(company.nom_detecte or '')[:64]}")
                if entree:
                    print(f"   Nom.csv : {entree['nom'][:64]}")
                    print(f"             neq={entree['neq']}  "
                          f"{statut_du_nom(entree['stat'], entree['typ'])}")
                    print(f"   élu     : {(nom_elu or '(aucun)')[:64]}")
                    code = formes_juridiques.get(entree["neq"], "(inconnu)")
                    print(f"   forme   : {code}  {libelles.get(('FORM_JURI', code), '')[:40]}")

        print("\n" + "=" * 78)
        print("   Rien n'a été écrit. Un pont mesuré n'est pas un pont construit.")
        print("   ⚠️ Et le chiffre du pont est un PLANCHER : l'appariement est exact,")
        print("      donc un nom qui diffère d'un caractère n'y est pas compté.")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
