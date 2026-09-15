#!/usr/bin/env python3
"""Ce que sont les non résolues **introuvables dans `Nom.csv`** — et par quelle
autre porte les chercher.

⚠️ **LA MESURE DEMANDÉE N'EST PAS EXÉCUTABLE TELLE QUE POSÉE, et il faut le dire
avant de rendre autre chose.** *« Cherche-les dans `Entreprise.csv` — pas dans
`Nom.csv` — et ventile leur forme juridique. »* **`Entreprise.csv` ne porte aucun
nom** : ses 37 colonnes vont de `NEQ` à `ADR_DOMCL_LIGN4_ADR`, et le nom vit
exclusivement dans `Nom.csv` *(guide officiel, § 4.1 et § 4.2)*. **La seule clé de
jointure est le NEQ — précisément ce qu'on n'a pas pour ces entreprises.**

**Ce que l'outil fait à la place, et pourquoi ça répond quand même.** Il existe
un TROISIÈME gisement de noms dans l'archive, que le produit parse déjà sans
jamais s'en servir pour apparier : **`Etablissements.csv`, colonne `NOM_ETAB`** —
*« nom désignant l'établissement »*. Une entreprise dont la dénomination sociale
est numérique peut fort bien nommer son établissement `Ferme Dallaire Frères`.

    Nom.csv            → NOM_ASSUJ        déjà exploité (le pont du 16 septembre)
    Etablissements.csv → NOM_ETAB         JAMAIS utilisé pour apparier   ←
    Entreprise.csv     → aucun nom        impossible par construction

**Donc : chercher les introuvables dans `NOM_ETAB`, récupérer leur NEQ, puis
ventiler `COD_FORME_JURI` depuis `Entreprise.csv`.** *La ventilation demandée est
rendue; c'est le chemin pour y arriver qui change.*

**Les trois causes que ça départage** *(Alexandre, 2026-09-16)*.

| ce que la mesure montre | cause | ce que ça veut dire |
|---|---|---|
| trouvées, majorité **personne physique** | nom jamais publié | **le mur devient une LIMITE** — la question redevient celle de l'EIMT |
| trouvées, majorité **société par actions** | nom trop éloigné | **il reste du travail** — leur nom existe, on ne le trouve pas |
| **introuvables même par `NOM_ETAB`** | ni nommée, ni immatriculée | *reste l'adresse, la seule autre prise* |

⚠️ **Ce que ce troisième cas NE prouve pas.** *Une entreprise absente des trois
fichiers peut être non immatriculée au Québec, une personne physique, ou nommée
autrement.* **L'outil les compte ensemble et le dit** — les séparer demande
l'adresse, qui n'est pas construite.

⚠️ **PORTÉE.** Appariement exact sur forme normalisée, lecture seule, rien
d'écrit. Le compte est un **plancher**.

Usage :
    python3 outils/profil_des_6176.py --chemin /opt/falkye/import
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
import zipfile
from collections import Counter

VALEURS_MAX = 20


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
    except ImportError as exc:  # pragma: no cover - dépend de l'environnement
        print(f"Import impossible ({exc}). Lancer depuis la racine du dépôt.", file=sys.stderr)
        return 2

    from outils.archives_req import avertissement, ligne_de_provenance, resoudre
    from outils.profil_des_absents_req import charger_domaines, part

    archive = resoudre(args.chemin)
    if archive is None:
        print(f"⛔ aucune archive à {args.chemin!r}.", file=sys.stderr)
        return 2

    print("=" * 78)
    print("LES INTROUVABLES DANS Nom.csv — ce qu'elles sont")
    print("=" * 78)
    print(f"\n{ligne_de_provenance(archive)}")
    vieil = avertissement(archive)
    if vieil:
        print(f"\n{vieil}")
    print("\n⚠️ `Entreprise.csv` NE PORTE AUCUN NOM — la recherche par nom y est")
    print("   impossible par construction. L'outil passe par `NOM_ETAB` des")
    print("   établissements, un troisième gisement jamais utilisé pour apparier.")

    session = get_session()
    try:
        non_resolues: dict[str, list] = {}
        for company in session.execute(
            select(Company).where(Company.neq.is_(None))
        ).scalars().all():
            forme = normaliser(company.nom_detecte or "")
            if forme:
                non_resolues.setdefault(forme, []).append(company)
        sources_par_company: dict[int, set[str]] = {}
        for company_id, source_id in session.execute(
            select(Signal.company_id, Signal.source_id)
        ).all():
            sources_par_company.setdefault(company_id, set()).add(source_id)

        with zipfile.ZipFile(archive) as zf:
            libelles = charger_domaines(zf)

            # Passe 1 — les noms de Nom.csv, pour ÉCARTER celles que le pont règle.
            deja_pontees: set[str] = set()
            with zf.open("Nom.csv") as brut:
                texte = io.TextIOWrapper(brut, encoding="utf-8-sig", errors="replace")
                for rangee in csv.DictReader(texte):
                    forme = normaliser((rangee.get("NOM_ASSUJ") or "").strip())
                    if forme in non_resolues:
                        deja_pontees.add(forme)
            restantes = {f: c for f, c in non_resolues.items() if f not in deja_pontees}
            print(f"\n   non résolues            : {sum(len(v) for v in non_resolues.values())}")
            print(f"   réglées par le pont     : {sum(len(non_resolues[f]) for f in deja_pontees)}")
            print(f"   RESTANTES à expliquer   : {sum(len(v) for v in restantes.values())}")

            # Passe 2 — NOM_ETAB.
            neq_par_forme: dict[str, set[str]] = {}
            with zf.open("Etablissements.csv") as brut:
                texte = io.TextIOWrapper(brut, encoding="utf-8-sig", errors="replace")
                for rangee in csv.DictReader(texte):
                    forme = normaliser((rangee.get("NOM_ETAB") or "").strip())
                    if forme and forme in restantes:
                        neq = (rangee.get("NEQ") or "").strip()
                        if neq:
                            neq_par_forme.setdefault(forme, set()).add(neq)

            # Passe 3 — la forme juridique des NEQ retrouvés.
            cibles = {n for lot in neq_par_forme.values() for n in lot}
            formes: dict[str, str] = {}
            if cibles:
                with zf.open("Entreprise.csv") as brut:
                    texte = io.TextIOWrapper(brut, encoding="utf-8-sig", errors="replace")
                    for rangee in csv.DictReader(texte):
                        neq = (rangee.get("NEQ") or "").strip()
                        if neq in cibles:
                            formes[neq] = (rangee.get("COD_FORME_JURI") or "").strip() or "(vide)"

        # --- le verdict ------------------------------------------------------
        classes: Counter = Counter()
        ventilation: Counter = Counter()
        par_source: Counter = Counter()
        exemples: dict[str, list] = {}
        for forme, companies in restantes.items():
            neqs = neq_par_forme.get(forme) or set()
            for company in companies:
                for source_id in sources_par_company.get(company.id, {"(aucune)"}):
                    par_source[source_id] += 1
                if not neqs:
                    classes["introuvable AUSSI par NOM_ETAB"] += 1
                    if len(exemples.setdefault("rien", [])) < args.exemples:
                        exemples["rien"].append((company, None))
                    continue
                classes["retrouvée par NOM_ETAB" + (" (ambigu)" if len(neqs) > 1 else "")] += 1
                code = formes.get(sorted(neqs)[0], "(inconnu)")
                ventilation[code] += 1
                if len(exemples.setdefault("trouvee", [])) < args.exemples:
                    exemples["trouvee"].append((company, sorted(neqs)[0]))

        print("\n" + "=" * 78)
        print("LE RÉSULTAT")
        print("=" * 78)
        print()
        for classe, n in classes.most_common():
            print(f"   {n:>7}  {classe}")

        print("\n   FORME JURIDIQUE des retrouvées :")
        if not ventilation:
            print("      aucune retrouvée — rien à ventiler.")
            print("      ⚠️ Ce n'est pas « 0 % de personnes physiques » : c'est zéro mesure.")
        for code, n in ventilation.most_common(VALEURS_MAX):
            print(f"      {code:<10}{n:>8}{part(ventilation, code):>8.1f}%   "
                  f"{libelles.get(('FORM_JURI', code), '')[:38]}")

        print("\n   PAR SOURCE :")
        for source_id, n in par_source.most_common():
            print(f"      {source_id:<28}{n:>8}")

        for cle, titre in (("trouvee", "RETROUVÉES PAR NOM_ETAB"),
                           ("rien", "INTROUVABLES PAR LES TROIS FICHIERS")):
            lot = exemples.get(cle) or []
            if not lot:
                continue
            print("\n" + "-" * 78)
            print(f"{titre} — {len(lot)} montrée(s)")
            print("-" * 78)
            for company, neq in lot:
                print(f"\n   détecté : {(company.nom_detecte or '')[:62]}")
                if neq:
                    code = formes.get(neq, "(inconnu)")
                    print(f"   neq     : {neq}   forme {code} "
                          f"{libelles.get(('FORM_JURI', code), '')[:34]}")

        print("\n" + "=" * 78)
        print("   ⚠️ « Introuvable par les trois fichiers » compte ENSEMBLE trois cas :")
        print("      non immatriculée au Québec, personne physique, ou nommée autrement.")
        print("      Les séparer demande l'ADRESSE, qui n'est pas construite.")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
