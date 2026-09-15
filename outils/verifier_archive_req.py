#!/usr/bin/env python3
"""L'archive du REQ vérifiée AVANT l'import — sur ses en-têtes, pas sur ses lignes.

**Deux secondes contre 33 minutes.** L'import lit 2,7 millions de lignes et écrit
un miroir. *Si une colonne déclarée par le code manque à l'archive, il vaut mieux
l'apprendre maintenant que découvrir dans trois jours un miroir chargé et
inutilisable* — **l'état le plus coûteux, parce qu'il a l'air du bon**.

**Le défaut qu'il ferme** *(2026-09-15)*. `dict.get` d'une colonne inexistante
rend `None`. Ce `None` devient `""`, puis une chaîne normalisée **vide** écrite en
base. Aucune exception, aucun test rouge — **et la moitié d'un miroir de
2 730 146 lignes devient inutilisable sans que rien n'échoue**.

⚠️ **Il emprunte les fonctions du moteur** — `_en_tete_csv`,
`colonnes_declarees_absentes`, `colonnes_couvertes_par_la_quarantaine`. *Une
vérification recopiée à côté vérifierait sa propre copie*, et c'est précisément
ce genre d'écart qui a produit le défaut qu'elle cherche.

⚠️ **PORTÉE.** Il compare des NOMS d'en-tête. *Une colonne présente mais vide,
renommée avec le même sens, ou remplie d'autre chose passe sans rien dire* —
**une garde ne couvre que ce que la mesure couvrait.** Il n'ouvre aucune base,
n'écrit rien, et ne lit pas une seule ligne de donnée.

Usage :
    python3 outils/verifier_archive_req.py --chemin /opt/falkye/import/JeuDonnees.zip
"""
from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

CSV_ATTENDUS = ("Entreprise.csv", "Nom.csv", "Etablissements.csv")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--chemin", required=True, help="l'archive JeuDonnees.zip")
    args = parser.parse_args(argv)

    try:
        from falkye.sources.req import (
            _en_tete_csv,
            _LECTEURS_PAR_CSV,
            colonnes_brutes_lues,
            colonnes_couvertes_par_la_quarantaine,
            colonnes_declarees_absentes,
        )
    except ImportError as exc:  # pragma: no cover - dépend de l'environnement
        print(f"Import impossible ({exc}). Lancer depuis la racine du dépôt.", file=sys.stderr)
        return 2

    print("=" * 78)
    print("L'ARCHIVE DU REQ, VÉRIFIÉE SUR SES EN-TÊTES")
    print("=" * 78)
    print(f"\narchive : {args.chemin}")

    try:
        zf = zipfile.ZipFile(args.chemin)
    except (OSError, zipfile.BadZipFile) as exc:
        print(f"\n⛔ archive illisible : {exc}", file=sys.stderr)
        return 2

    with zf:
        presents = set(zf.namelist())
        manquants = [n for n in CSV_ATTENDUS if n not in presents]
        if manquants:
            # Dit AVANT les en-têtes : une en-tête vide se lirait « toutes les
            # colonnes manquent », ce qui est vrai mais cache la vraie cause.
            print(f"\n⛔ CSV absent(s) de l'archive : {', '.join(manquants)}")
            print("   Les fichiers présents :")
            for n in sorted(presents):
                print(f"      {n}")
            return 1

        entetes = {n: _en_tete_csv(zf, n) for n in CSV_ATTENDUS}

    print()
    for nom, cols in entetes.items():
        print(f"   {nom:<22} {len(cols)} colonne(s)")

    # Croisées PAR CSV, jamais en bloc : `NOM_ASSUJ` appartient à Nom.csv, et le
    # signaler absent d'Entreprise.csv serait une fausse alerte. **Une garde qui
    # crie à tort est retirée au premier agacement, et ne protège plus rien.**
    source = Path("falkye/sources/req.py").read_text(encoding="utf-8")
    couvertes = colonnes_couvertes_par_la_quarantaine(source)
    absentes_couvertes = {}
    for csv_nom, fonction in _LECTEURS_PAR_CSV.items():
        lues_ici = colonnes_brutes_lues(source, fonction)
        manquantes = sorted((lues_ici & couvertes) - set(entetes.get(csv_nom) or []))
        if manquantes:
            absentes_couvertes[csv_nom] = manquantes

    absentes = colonnes_declarees_absentes(entetes)

    print("\n" + "-" * 78)
    print("LE POINT AVEUGLE — colonnes lues par le code, qu'aucun champ logique ne représente")
    print("-" * 78)
    if not absentes:
        print("\n   aucune colonne déclarée absente.")
        print("   L'import ne refusera pas sur ce motif.")
    else:
        for nom, cols in absentes.items():
            print(f"\n   ⛔ {nom}")
            for c in cols:
                print(f"        {c}")
        print("\n   L'import REFUSERA de démarrer, et rien ne sera écrit.")
        print("   ⚠️ Vérifier d'abord une VIRGULE OUBLIÉE entre deux noms de colonne :")
        print('      `row.get("A" "B")` est du Python valide et lit une colonne "AB".')
        print("      Ensuite seulement, conclure que le schéma du REQ a changé.")

    print("\n" + "-" * 78)
    print("CE QUE LA QUARANTAINE COUVRE DÉJÀ — informatif, pas un refus")
    print("-" * 78)
    if not absentes_couvertes:
        print("\n   toutes les colonnes surveillées par le moteur de diff sont présentes.")
    else:
        for nom, cols in absentes_couvertes.items():
            print(f"\n   ⚠️ {nom} : {', '.join(cols)}")
        print("\n   L'import PARTIRA EN QUARANTAINE plutôt que de refuser : REQEntry")
        print("   reste intact, l'incident est journalisé, `falkye quarantaine lister`")
        print("   le montre. C'est une meilleure réponse qu'un refus, pas une moins bonne.")

    print("\n⚠️ Cette vérification porte sur des NOMS d'en-tête. Une colonne présente")
    print("   mais vide, ou remplie d'autre chose, passe ici sans rien dire.")
    return 1 if absentes else 0


if __name__ == "__main__":
    raise SystemExit(main())
