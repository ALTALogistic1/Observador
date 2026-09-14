"""Le pont dort-il déjà dans l'archive du REQ? — combien de NEQ portent PLUSIEURS noms.

**Ce que le connecteur fait aujourd'hui, et ce qu'il jette.** `_charger_index_noms`
lit `Nom.csv`, **élit UN nom par NEQ** — un nom en vigueur (`STAT_NOM='V'`), de type
dénomination sociale (`'M'`) de préférence à `'N'` — **et écarte tous les autres**.
Le miroir ne garde donc qu'une chaîne par entreprise.

⚠️ **Or `Nom.csv` porte l'historique ET les noms simultanés.** Une entreprise peut
avoir, EN MÊME TEMPS, une dénomination sociale et un ou plusieurs autres noms
utilisés au Québec — *exactement l'enseigne sous laquelle les autres sources la
nomment.* **Si c'est fréquent, le pont que cherchent les chantiers 3 et 4 est déjà
en notre possession, et il est écarté au chargement.**

**Cet outil ne construit rien : il compte.** Il lit l'archive telle quelle et rend la
distribution du nombre de noms par NEQ, en séparant ce qui est simultané de ce qui
est de l'historique.

**PORTÉE** *(guide d'ingénierie)* :

- **Il lit l'ARCHIVE, pas le miroir** — le miroir a déjà jeté ce qu'on cherche.
- **Il ne dit pas si un second nom aiderait** : il dit combien il y en a. *Savoir si
  ces noms-là apparient les entreprises bloquées demande `diagnostic_appariement.py`
  et une comparaison, pas ce compte.*
- **Il ne décide d'aucun correctif.**

    python outils/noms_multiples_req.py --chemin /opt/falkye/import/JeuDonnees.zip
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
import zipfile
from collections import Counter, defaultdict

#: Les valeurs de `TYP_NOM_ASSUJ` rencontrées à l'inspection réelle du 2026-08-31 :
#: 'M' dénomination sociale, 'N' nom. Tout autre type est compté sous son code brut —
#: **jamais rangé dans « autre »**, pour qu'un type inconnu se voie.
TYPES_CONNUS = {"M": "dénomination sociale", "N": "nom"}


def compter_noms(zf: zipfile.ZipFile, limite: int | None = None) -> dict:
    """Parcourt `Nom.csv` en flux et compte, par NEQ, les noms en vigueur et les autres."""
    en_vigueur: dict[str, set] = defaultdict(set)
    anciens: dict[str, set] = defaultdict(set)
    types_en_vigueur: Counter = Counter()
    lignes = 0
    with zf.open("Nom.csv") as brut:
        texte = io.TextIOWrapper(brut, encoding="utf-8-sig", errors="replace")
        for ligne in csv.DictReader(texte):
            neq = (ligne.get("NEQ") or "").strip()
            nom = (ligne.get("NOM_ASSUJ") or "").strip()
            if not neq or not nom:
                continue
            lignes += 1
            if limite is not None and lignes > limite:
                break
            statut = (ligne.get("STAT_NOM") or "").strip().upper()
            typ = (ligne.get("TYP_NOM_ASSUJ") or "").strip().upper()
            if statut == "V":
                en_vigueur[neq].add(nom)
                types_en_vigueur[typ] += 1
            else:
                anciens[neq].add(nom)
    return {
        "lignes": lignes,
        "en_vigueur": en_vigueur,
        "anciens": anciens,
        "types_en_vigueur": types_en_vigueur,
    }


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--chemin", required=True, help="l'archive ZIP du REQ")
    parseur.add_argument("--limite", type=int, default=None,
                         help="s'arrêter après N lignes de Nom.csv (essai rapide)")
    args = parseur.parse_args(argv)

    try:
        zf = zipfile.ZipFile(args.chemin)
    except Exception as e:
        print(f"REFUS — archive illisible : {e}", file=sys.stderr)
        return 2
    if "Nom.csv" not in zf.namelist():
        print(f"REFUS — pas de Nom.csv dans l'archive. Contenu : {zf.namelist()[:8]}", file=sys.stderr)
        return 2

    print(f"archive : {args.chemin}")
    if args.limite:
        print(f"⚠️ PORTÉE RESTREINTE : les {args.limite} premières lignes seulement.")
        print("   Le fichier est ordonné par NEQ — ce n'est PAS un échantillon aléatoire.")

    r = compter_noms(zf, args.limite)
    en_vigueur, anciens = r["en_vigueur"], r["anciens"]
    tous = set(en_vigueur) | set(anciens)
    if not tous:
        print("\n⚠️ AUCUN nom lu. Ce n'est pas « le REQ n'en porte pas » — vérifier le fichier.")
        return 0

    print(f"\nlignes de Nom.csv lues : {r['lignes']}")
    print(f"NEQ distincts          : {len(tous)}")

    dist = Counter(len(v) for v in en_vigueur.values())
    plusieurs = sum(k for n, k in dist.items() if n > 1)
    print("\n" + "=" * 74)
    print("NOMS EN VIGUEUR (STAT_NOM='V') PAR NEQ — les noms SIMULTANÉS")
    print("=" * 74)
    for n in sorted(dist):
        print(f"   {n} nom(s) en vigueur : {dist[n]:>8}  ({100*dist[n]/max(len(en_vigueur),1):>5.1f} %)")
    print(f"\n   → {plusieurs} NEQ portent PLUSIEURS noms en vigueur"
          f"  ({100*plusieurs/max(len(en_vigueur),1):.1f} % de ceux qui en ont un)")
    print("   Ce sont eux le pont : le miroir n'en garde qu'un.")

    print("\n   types rencontrés parmi les noms en vigueur :")
    for typ, k in r["types_en_vigueur"].most_common():
        libelle = TYPES_CONNUS.get(typ, f"type inconnu « {typ} »")
        print(f"      {typ or '(vide)':>8}  {libelle:26} {k:>9}")

    avec_anciens = sum(1 for neq in tous if anciens.get(neq))
    print("\n" + "=" * 74)
    print("NOMS ANTÉRIEURS (STAT_NOM ≠ 'V')")
    print("=" * 74)
    print(f"   NEQ portant au moins un nom antérieur : {avec_anciens}"
          f"  ({100*avec_anciens/len(tous):.1f} %)")
    print("   ⚠️ Un nom antérieur n'est PAS un pont vers le présent — mais une source")
    print("      qui a connu l'entreprise sous son ancien nom s'apparierait par lui.")

    print("\n⚠️ Ce compte ne dit PAS que ces noms résoudraient les entreprises bloquées.")
    print("   Il dit combien il y en a. Le gain se mesure avec diagnostic_appariement.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
