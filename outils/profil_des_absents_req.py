#!/usr/bin/env python3
"""Ce que désigne la plage des NEQ sans nom — **une exclusion par nature, ou un
trou dans le fichier?**

**Le fait qui justifie cet outil** *(Alexandre, 2026-09-16)*. L'audit a montré que
l'import ne s'arrête pas — même borne haute des deux côtés, `8881817611` — et que
`Nom.csv` porte **224 968 NEQ de moins** qu'`Entreprise.csv`, exactement l'écart.
**Mais la forme des absences retient de conclure** :

    Entreprise.csv        2 955 114   de 1140000002 à 8881817611
    SANS nom élu            224 968   de 1173929648 à 2282522335

*Les absences vivent toutes entre `11` et `22`, alors que le fichier va jusqu'à
`88`.* **C'est étroit, et les NEQ ne sont pas attribués au hasard.**

**Ce que dit le guide officiel du Registraire** *(`Guide d'utilisation`, page 16,
lexique — relevé le 2026-09-16)* :

> *« Numéro d'entreprise du Québec (NEQ) — Numéro de 10 chiffres attribué à chaque
> entreprise au moment de son immatriculation au registre des entreprises.* **Les
> deux premiers chiffres correspondent à la forme juridique de l'entreprise et
> sont 11, 22 ou 33.** *»*

**Donc le préfixe du NEQ EST une forme juridique**, et la plage observée couvre
**deux des trois** formes documentées, sans toucher `33`. ⚠️ **Et la borne haute
observée commence par `88`, qui n'est PAS dans les trois valeurs documentées** —
*le guide ne couvre donc pas tout ce que le fichier porte, et c'est à relever
plutôt qu'à lisser.*

**Les deux questions, et l'outil ne répond qu'en les posant ensemble.**

*(1)* **Par quoi les absents se distinguent-ils?** Ventilation des absents contre
les présents sur chaque code d'`Entreprise.csv` — `COD_FORME_JURI`,
`COD_REGIM_JURI`, `COD_STAT_IMMAT`, `IND_FAIL`, `COD_INTVAL_EMPLO_QUE` — **et
c'est l'ÉCART entre les deux ventilations qui désigne, jamais le compte des
absents seul.** *Si 100 % des absents portent une forme juridique que 0,1 % des
présents portent, la cause est nommée. Si les deux ventilations se ressemblent,
ce n'est pas une exclusion par nature.*

*(2)* **LE SENS INVERSE** *(question d'Alexandre, et c'est elle qui tranche)* :
*la plage `1173929648`–`2282522335` contient-elle aussi des NEQ qui ONT un nom?*
**Si oui, l'exclusion n'est pas la plage — c'est autre chose à l'intérieur.**

⚠️ **Les libellés viennent de `DomaineValeur.csv`**, un fichier de l'archive que
le produit **ne lit nulle part ailleurs**. *Un code sans son libellé se recopie
de travers; un libellé lu à la source ne se discute pas.*

⚠️ **PORTÉE.** Lecture seule sur l'archive, aucune base ouverte. *Il ne dit pas
s'il faut corriger quoi que ce soit* — il dit si l'absence a une forme, et
laquelle. **Une exclusion volontaire du Registraire et un trou d'import se
soignent différemment; ils se ressemblent dans un total.**

Usage :
    python3 outils/profil_des_absents_req.py --chemin /opt/falkye/import
    python3 outils/profil_des_absents_req.py --chemin … --exemples 20
"""
from __future__ import annotations

from outils.nombres import milliers

import argparse
import csv
import io
import sys
import zipfile
from collections import Counter

#: Les codes d'`Entreprise.csv` sur lesquels on ventile. Tirés du guide officiel
#: (§ 4.1) et non devinés. **`COD_INTVAL_EMPLO_QUE` est dans le lot** : le guide
#: le décrit comme *« ordre de grandeur du nombre d'employés au Québec »*.
CODES_A_VENTILER = (
    ("COD_FORME_JURI", "FORM_JURI", "forme juridique"),
    ("COD_REGIM_JURI", "REGIM_JURI", "régime juridique"),
    ("COD_STAT_IMMAT", "STAT_IMMAT", "statut d'immatriculation"),
    ("COD_INTVAL_EMPLO_QUE", "INTVAL_EMPLO_QUE", "ordre de grandeur des employés"),
    ("IND_FAIL", None, "indicateur de faillite"),
)

#: Au-delà, la ventilation n'est plus lisible et le code devient l'information.
VALEURS_MAX = 25


def prefixe_neq(neq: str) -> str:
    """Les deux premiers chiffres — **la forme juridique, selon le guide.**"""
    return (neq or "")[:2]


def charger_domaines(zf: zipfile.ZipFile) -> dict[tuple[str, str], str]:
    """`(domaine, code) -> libellé`, depuis `DomaineValeur.csv`.

    **Un fichier de l'archive que le produit ne lit nulle part ailleurs.** *Un
    code sans son libellé se recopie de travers.* Rend un dictionnaire vide si le
    fichier est absent — *l'outil reste utilisable avec des codes nus, et le dit.*
    """
    if "DomaineValeur.csv" not in zf.namelist():
        return {}
    domaines: dict[tuple[str, str], str] = {}
    with zf.open("DomaineValeur.csv") as brut:
        texte = io.TextIOWrapper(brut, encoding="utf-8-sig", errors="replace")
        for rangee in csv.DictReader(texte):
            domaine = (rangee.get("TYP_DOM_VAL") or "").strip()
            code = (rangee.get("COD_DOM_VAL") or "").strip()
            libelle = (rangee.get("VAL_DOM_FRAN") or "").strip()
            if domaine and code:
                domaines[(domaine, code)] = libelle
    return domaines


def part(compteur: Counter, valeur: str) -> float:
    """La part d'une valeur, en pourcentage. **0 quand le compteur est vide**, et
    l'appelant doit savoir que ce zéro-là veut dire « rien à diviser »."""
    total = sum(compteur.values())
    return 100.0 * compteur.get(valeur, 0) / total if total else 0.0


def ventilation_comparee(absents: Counter, presents: Counter,
                         libelles: dict, domaine: str | None) -> list[tuple]:
    """Les valeurs triées par **ÉCART de part** entre absents et présents.

    *C'est l'écart qui désigne, jamais le compte des absents seul* : une valeur
    portée par 90 % des absents ne dit rien si 90 % des présents la portent
    aussi. **Trier par compte ferait remonter le banal; trier par écart fait
    remonter le distinctif.**
    """
    lignes = []
    for valeur in set(absents) | set(presents):
        p_abs, p_pre = part(absents, valeur), part(presents, valeur)
        libelle = libelles.get((domaine, valeur), "") if domaine else ""
        lignes.append((p_abs - p_pre, valeur, libelle,
                       absents.get(valeur, 0), presents.get(valeur, 0), p_abs, p_pre))
    return sorted(lignes, key=lambda l: -abs(l[0]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--chemin", required=True, help="l'archive, ou le répertoire")
    parser.add_argument("--exemples", type=int, default=10)
    args = parser.parse_args(argv)

    try:
        from falkye.sources.req import _charger_index_noms
    except ImportError as exc:  # pragma: no cover - dépend de l'environnement
        print(f"Import impossible ({exc}). Lancer depuis la racine du dépôt.", file=sys.stderr)
        return 2

    from outils.archives_req import avertissement, ligne_de_provenance, resoudre

    archive = resoudre(args.chemin)
    if archive is None:
        print(f"⛔ aucune archive à {args.chemin!r}.", file=sys.stderr)
        return 2

    print("=" * 78)
    print("CE QUE DÉSIGNE LA PLAGE DES NEQ SANS NOM")
    print("=" * 78)
    print(f"\n{ligne_de_provenance(archive)}")
    vieillissement = avertissement(archive)
    if vieillissement:
        print(f"\n{vieillissement}")
    print("\nPORTÉE : lecture seule sur l'archive. Aucune base ouverte.")
    print("         Il dit si l'absence a une FORME, pas s'il faut la corriger.")
    print("\nLe guide du Registraire (p. 16) : « Les deux premiers chiffres")
    print("correspondent à la forme juridique de l'entreprise et sont 11, 22 ou 33. »")

    with zipfile.ZipFile(archive) as zf:
        libelles = charger_domaines(zf)
        if libelles:
            print(f"\nDomaineValeur.csv lu : {len(libelles)} libellé(s).")
        else:
            print("\n⚠️ DomaineValeur.csv ABSENT — les codes restent nus.")

        noms = _charger_index_noms(zf)

        absents_par_code: dict[str, Counter] = {c: Counter() for c, _, _ in CODES_A_VENTILER}
        presents_par_code: dict[str, Counter] = {c: Counter() for c, _, _ in CODES_A_VENTILER}
        prefixes_absents: Counter = Counter()
        prefixes_presents: Counter = Counter()
        exemples_absents: list[dict] = []
        bornes_absents: list[str] = []
        n_absents = n_presents = 0

        with zf.open("Entreprise.csv") as brut:
            texte = io.TextIOWrapper(brut, encoding="utf-8-sig", errors="replace")
            for rangee in csv.DictReader(texte):
                neq = (rangee.get("NEQ") or "").strip()
                if not neq:
                    continue
                absent = not noms.get(neq)
                if absent:
                    n_absents += 1
                    bornes_absents.append(neq)
                    prefixes_absents[prefixe_neq(neq)] += 1
                    if len(exemples_absents) < args.exemples:
                        exemples_absents.append(
                            {c: (rangee.get(c) or "").strip() for c, _, _ in CODES_A_VENTILER}
                            | {"NEQ": neq, "DAT_IMMAT": (rangee.get("DAT_IMMAT") or "").strip()}
                        )
                else:
                    n_presents += 1
                    prefixes_presents[prefixe_neq(neq)] += 1
                cible = absents_par_code if absent else presents_par_code
                for code, _dom, _lib in CODES_A_VENTILER:
                    cible[code][(rangee.get(code) or "").strip() or "(vide)"] += 1

        print("\n" + "-" * 78)
        print("LES DEUX POPULATIONS")
        print("-" * 78)
        print(f"\n   sans nom élu : {milliers(n_absents)}")
        print(f"   avec nom élu : {milliers(n_presents)}")

        # --- le préfixe, c'est-à-dire la forme juridique ------------------
        print("\n" + "-" * 78)
        print("LE PRÉFIXE DU NEQ — la forme juridique, selon le guide")
        print("-" * 78)
        print(f"\n   {'préfixe':<10}{'absents':>12}{'présents':>12}"
              f"{'part abs.':>11}{'part prés.':>12}")
        for prefixe in sorted(set(prefixes_absents) | set(prefixes_presents)):
            a, p = prefixes_absents.get(prefixe, 0), prefixes_presents.get(prefixe, 0)
            marque = "" if prefixe in ("11", "22", "33") else "   ⚠️ hors 11/22/33"
            print(f"   {prefixe:<10}{a:>12,}"
                  + f"{p:>12,}"
                  + f"{part(prefixes_absents, prefixe):>10.1f}%"
                  + f"{part(prefixes_presents, prefixe):>11.1f}%{marque}")

        # --- LE SENS INVERSE ----------------------------------------------
        print("\n" + "-" * 78)
        print("LE SENS INVERSE — la plage contient-elle aussi des NEQ QUI ONT un nom?")
        print("-" * 78)
        if not bornes_absents:
            print("\n   Aucun absent : la question ne se pose pas.")
        else:
            bas, haut = min(bornes_absents), max(bornes_absents)
            dans_plage_avec_nom = sum(
                1 for neq in noms if bas <= neq <= haut
            )
            print(f"\n   plage des absents      : {bas} à {haut}")
            print(f"   NEQ AVEC un nom dans cette plage : {milliers(dans_plage_avec_nom)}"
                  )
            print(f"   NEQ SANS nom dans cette plage    : {milliers(n_absents)}")
            if dans_plage_avec_nom:
                total_plage = dans_plage_avec_nom + n_absents
                print(f"\n   ⛔ L'EXCLUSION N'EST PAS LA PLAGE.")
                print(f"      {100 * dans_plage_avec_nom / total_plage:.1f} % des NEQ de cette")
                print("      plage ONT un nom. La plage n'est donc pas une catégorie exclue —")
                print("      c'est autre chose à l'intérieur, et la ventilation ci-dessous")
                print("      est le seul endroit où ce « autre chose » peut se voir.")
            else:
                print("\n   ✅ AUCUN NEQ de cette plage n'a de nom.")
                print("      La plage EST la catégorie. Reste à dire laquelle, ci-dessous.")

        # --- la ventilation comparée ---------------------------------------
        for code, domaine, libelle_code in CODES_A_VENTILER:
            print("\n" + "-" * 78)
            print(f"{code} — {libelle_code}")
            print("-" * 78)
            lignes = ventilation_comparee(
                absents_par_code[code], presents_par_code[code], libelles, domaine
            )
            print(f"\n   {'valeur':<14}{'absents':>11}{'présents':>11}"
                  f"{'part abs.':>11}{'part prés.':>11}{'écart':>9}")
            for ecart, valeur, lib, n_a, n_p, p_a, p_p in lignes[:VALEURS_MAX]:
                marque = "  ←" if abs(ecart) >= 20 else ""
                print(f"   {valeur[:13]:<14}{n_a:>11,}"
                      + f"{n_p:>11,}"
                      + f"{p_a:>10.1f}%{p_p:>10.1f}%{ecart:>+8.1f}{marque}")
                if lib:
                    print(f"      └ {lib[:66]}")
            if len(lignes) > VALEURS_MAX:
                print(f"\n   … {len(lignes) - VALEURS_MAX} valeur(s) de plus, écart moindre.")
            plus_grand = lignes[0] if lignes else None
            if plus_grand and abs(plus_grand[0]) >= 20:
                print(f"\n   ⚠️ ÉCART DE {plus_grand[0]:+.1f} POINTS sur {plus_grand[1]!r}"
                      + (f" ({plus_grand[2]})" if plus_grand[2] else ""))
                print("      C'est un candidat sérieux pour « exclusion par nature ».")

        if exemples_absents:
            print("\n" + "-" * 78)
            print("DIX ABSENTS, EN ENTIER")
            print("-" * 78)
            for ligne in exemples_absents:
                print()
                for cle, valeur in ligne.items():
                    print(f"      {cle:<24} {valeur!r}")

        print("\n" + "=" * 78)
        print("   ⚠️ L'écart entre les deux ventilations DÉSIGNE; il ne prouve pas.")
        print("      Une forme juridique portée par tous les absents et par aucun")
        print("      présent est une exclusion; une ventilation qui se ressemble")
        print("      des deux côtés dit que la cause est ailleurs.")
        print("   ⚠️ Et si c'est une exclusion du Registraire, AUCUN correctif d'ici")
        print("      n'y changera rien — le mur cesse d'être un défaut pour devenir")
        print("      une limite, et c'est une réponse aussi utile que l'autre.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
