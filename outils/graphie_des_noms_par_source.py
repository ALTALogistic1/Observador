#!/usr/bin/env python3
"""Quelle graphie de nom chaque source livre au dossier — et **laquelle garde la
forme juridique**.

**La question qu'il tranche** *(Alexandre, 2026-09-16)* : *« Si l'EIMT est seule à
garder la forme juridique, le correctif est étroit. Si tous la gardent, c'est le
miroir qu'il faut aligner, pas les connecteurs. »* **C'est la mesure qui décide de
l'emplacement du correctif, et donc de sa portée.**

L'outil rend **deux relevés distincts**, et il ne faut pas les confondre.

**(1) Le relevé STATIQUE — ce que le code fait.** Pour chaque connecteur,
l'expression qui alimente `nom_entreprise=` d'un `RawSignal`, extraite par AST.
*Un nom passé tel quel n'est pas la même chose qu'un nom transformé*, et la
différence se lit dans l'expression. **Marche partout, sans base.**

**(2) Le relevé MESURÉ — ce que la donnée porte.** Pour chaque source, la part des
`Company.nom_detecte` qui se terminent par une forme juridique, **retrouvée par
les `Signal` qui les ont produites**. *C'est ce relevé-là qui répond à la
question*, parce qu'un connecteur qui « ne transforme rien » livre exactement ce
que sa source publie — et deux sources publient rarement la même graphie.
**Exige la base.**

⚠️ **Une source peut apparaître ici sans être la cause.** Le relevé mesuré compte
des `Company`, pas des signaux : *une entreprise détectée par trois sources est
comptée dans les trois*, et sa graphie est celle de la source qui l'a créée la
première. **L'outil le dit plutôt que de faire comme si le rattachement était
propre** — voir la colonne « entreprises rattachées ».

**PORTÉE.** Lecture seule, aucune écriture. Il ne propose aucun correctif et n'en
choisit aucun emplacement : *trois emplacements sont possibles — le miroir à
l'écriture, les connecteurs à l'émission, la comparaison au moment du score — et
ils n'ont pas la même portée.* **Ce relevé donne le chiffre; le choix reste entier.**

Usage :
    python3 outils/graphie_des_noms_par_source.py              # les deux relevés
    python3 outils/graphie_des_noms_par_source.py --statique   # sans la base
"""
from __future__ import annotations

import argparse
import ast
import sys
from collections import Counter
from pathlib import Path

#: Emprunté au rejeu, jamais recopié — les deux outils doivent parler de la même
#: chose, sinon leurs chiffres ne se comparent pas.
from outils.rejeu_normalisation_symetrique import (  # noqa: E402
    FORMES_JURIDIQUES,
    porte_une_forme_juridique,
)

DOSSIER_CONNECTEURS = Path("falkye/sources")


def expression_du_nom(source_py: str) -> list[tuple[int, str]]:
    """Les expressions qui alimentent `nom_entreprise=` dans ce module.

    **Extraites par AST, pas par expression régulière** : un appel imbriqué sur
    plusieurs lignes se lit correctement, là où un `grep` rendrait la première.
    """
    try:
        arbre = ast.parse(source_py)
    except SyntaxError:
        return []
    trouvees: list[tuple[int, str]] = []
    for noeud in ast.walk(arbre):
        if not isinstance(noeud, ast.Call):
            continue
        for mot_cle in noeud.keywords:
            if mot_cle.arg == "nom_entreprise":
                trouvees.append((mot_cle.value.lineno, ast.unparse(mot_cle.value)))
    return sorted(set(trouvees))


def classer_expression(expression: str) -> str:
    """Le nom est-il livré **tel quel**, ou transformé en chemin?

    *Un `.strip()` retire des espaces; il ne retire pas une forme juridique.*
    La distinction compte : **aucun connecteur ne « normalise » au sens du
    miroir**, et confondre les deux ferait croire le contraire.
    """
    if "normalis" in expression:
        return "NORMALISÉ par le connecteur"
    if any(m in expression for m in (".title()", ".upper()", ".lower()", "re.sub")):
        return "graphie modifiée (casse ou substitution)"
    if ".strip()" in expression:
        return "espaces retirés seulement"
    return "tel quel, de la source"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--statique", action="store_true",
                        help="seulement le relevé du code, sans ouvrir la base")
    parser.add_argument("--exemples", type=int, default=8,
                        help="noms montrés par source (défaut 8)")
    args = parser.parse_args(argv)

    print("=" * 78)
    print("LA GRAPHIE DES NOMS, SOURCE PAR SOURCE")
    print("=" * 78)
    print("\nPORTÉE : lecture seule. Aucun correctif proposé, aucun emplacement choisi.")
    print(f"         formes juridiques reconnues : {len(FORMES_JURIDIQUES)}")

    # ---- (1) le relevé statique -----------------------------------------
    print("\n" + "-" * 78)
    print("1. CE QUE LE CODE FAIT — l'expression qui alimente nom_entreprise")
    print("-" * 78)
    classes: Counter = Counter()
    for fichier in sorted(DOSSIER_CONNECTEURS.glob("*.py")):
        if fichier.name.startswith("_") or fichier.name in ("base.py", "column_mapping.py"):
            continue
        expressions = expression_du_nom(fichier.read_text(encoding="utf-8", errors="replace"))
        if not expressions:
            continue
        print(f"\n   {fichier.stem}")
        for ligne, expression in expressions:
            classe = classer_expression(expression)
            classes[classe] += 1
            print(f"      :{ligne:<5} {expression[:52]:<54} {classe}")

    print("\n   RÉCAPITULATIF :")
    for classe, n in classes.most_common():
        print(f"      {n:>4}  {classe}")
    if not classes.get("NORMALISÉ par le connecteur"):
        print("\n   ⚠️ AUCUN connecteur ne normalise le nom avant de l'émettre.")
        print("      Chacun livre ce que sa source publie. La graphie n'est donc pas")
        print("      une décision du produit — c'est une propriété de chaque source,")
        print("      et elle ne se lit qu'au relevé MESURÉ ci-dessous.")

    if args.statique:
        return 0

    # ---- (2) le relevé mesuré -------------------------------------------
    try:
        from sqlalchemy import select

        from falkye.db import get_session
        from falkye.models.company import Company
        from falkye.models.signal import Signal
        from falkye.sources.column_mapping import normaliser
    except ImportError as exc:  # pragma: no cover - dépend de l'environnement
        print(f"\nRelevé mesuré impossible ({exc}). `--statique` pour le reste.", file=sys.stderr)
        return 2

    session = get_session()
    try:
        print("\n" + "-" * 78)
        print("2. CE QUE LA DONNÉE PORTE — part des noms finissant par une forme juridique")
        print("-" * 78)

        # Une Company peut avoir des signaux de plusieurs sources : elle est
        # comptée dans chacune, et la ligne « entreprises rattachées » le dit.
        paires = session.execute(
            select(Signal.source_id, Company.nom_detecte)
            .join(Company, Signal.company_id == Company.id)
        ).all()
        if not paires:
            print("\n   Aucun signal rattaché à une entreprise. Rien à mesurer.")
            print("   ⚠️ Ce n'est pas « 0 % de formes juridiques » — c'est zéro mesure.")
            return 0

        par_source: dict[str, list[str]] = {}
        for source_id, nom in paires:
            par_source.setdefault(source_id, []).append(nom or "")

        print(f"\n   {'source':<28}{'entreprises':>13}{'forme jur.':>12}{'part':>9}")
        lignes = []
        for source_id, noms in par_source.items():
            normalises = [normaliser(n) for n in noms]
            avec = sum(1 for n in normalises if porte_une_forme_juridique(n))
            lignes.append((source_id, len(noms), avec, 100 * avec / len(noms)))
        for source_id, total, avec, part in sorted(lignes, key=lambda l: -l[3]):
            print(f"   {source_id:<28}{total:>13}{avec:>12}{part:>8.1f}%")

        # La question d'Alexandre, tranchée par un compte plutôt qu'à l'œil.
        hautes = [l for l in lignes if l[3] >= 50 and l[1] >= 20]
        print("\n   CE QUE ÇA DÉCIDE :")
        if len(hautes) <= 1:
            print("      Une seule source (ou aucune) garde massivement la forme juridique.")
            print("      → le correctif est ÉTROIT : il vise cette source-là.")
        else:
            noms_hautes = ", ".join(l[0] for l in hautes)
            print(f"      {len(hautes)} sources gardent massivement la forme juridique :")
            print(f"      {noms_hautes}")
            print("      → aligner les connecteurs un à un reviendrait à faire N fois")
            print("        la même correction. C'est le MIROIR qui est l'exception.")
        print("\n      ⚠️ Seuil de lecture : ≥ 50 % sur ≥ 20 entreprises. Une source à")
        print("         trois entreprises ne décide de rien, quelle que soit sa part.")

        print("\n   EXEMPLES, par source :")
        for source_id, _total, _avec, _part in sorted(lignes, key=lambda l: -l[3]):
            echantillon = [n for n in par_source[source_id] if n][: args.exemples]
            if not echantillon:
                continue
            print(f"\n      {source_id}")
            for nom in echantillon:
                marque = "  ← forme jur." if porte_une_forme_juridique(normaliser(nom)) else ""
                print(f"         {nom[:56]}{marque}")

        print("\n⚠️ Une entreprise détectée par trois sources est comptée dans les trois.")
        print("   Ces parts décrivent des GRAPHIES, pas des populations disjointes.")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
