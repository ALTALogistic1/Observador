#!/usr/bin/env python3
"""Où passent les noms entre `Nom.csv` et `req_noms`?

**Le fait qui a écrit cet outil** *(2026-09-16)*. Le réimport a mis **1 505 879**
noms dans `req_noms`. L'analyse du 15 septembre annonçait **1 705 806 noms
jetés par le chargeur** — donc au moins autant à récupérer. *Deux cent mille de
moins, et personne ne pouvait dire où.*

⚠️ **Les deux chiffres ne comptent pas la même chose, et c'est le fond du
problème.** L'analyse comptait des **LIGNES de `Nom.csv`**; la table stocke des
**paires `(NEQ, nom NORMALISÉ)` distinctes**. Entre les deux il y a au moins
quatre péages, et aucun n'avait été chiffré :

1. `NEQ` ou `NOM_ASSUJ` vide;
2. `STAT_NOM` ≠ `V` — les noms retirés, écartés à dessein;
3. **un nom qui se normalise en chaîne vide** — il n'apparierait rien et
   apparierait tout;
4. ⚠️ **deux graphies différentes qui se normalisent PAREIL pour le même NEQ.**
   *« Les Entreprises ABC inc. » et « LES ENTREPRISES ABC INC » sont deux lignes
   du registre et une seule porte vers le NEQ.* La clé primaire les fusionne, et
   c'est voulu — **mais ça veut dire que « noms jetés » n'est pas « portes
   gagnées », et que le second chiffre est toujours plus petit.**

*Un chiffre recopié est une promesse que personne ne tient* : cet outil fait
payer chaque péage devant témoin, et compare le reste à ce que la table porte
vraiment.

⚠️ **PORTÉE.** Lecture seule : l'archive et un `count(*)`. N'écrit rien.

Usage, SUR L'HÔTE :
    python3 -m outils.entonnoir_noms_req
    python3 -m outils.entonnoir_noms_req --archive /opt/falkye/import
"""
from __future__ import annotations

from outils.nombres import milliers

import argparse
import csv
import io
import sys
import zipfile
from pathlib import Path

from falkye.sources.column_mapping import normaliser

DEPOT_PAR_DEFAUT = Path("/opt/falkye/import")


def _rss_mo() -> float | None:
    """La mémoire du processus, ou `None`. *L'absence de mesure n'est pas une
    mesure nulle* — cet outil garde en mémoire une empreinte par paire, et le
    dire est moins cher que de le découvrir sur un hôte à 8 Go."""
    try:
        with open("/proc/self/statm") as f:
            return int(f.read().split()[1]) * 4096 / 1048576
    except OSError:
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--archive", default=str(DEPOT_PAR_DEFAUT),
                        help="archive .zip ou répertoire de dépôt")
    args = parser.parse_args(argv)

    from outils.archives_req import resoudre

    chemin = resoudre(Path(args.archive))
    if chemin is None:
        print(f"⛔ Aucune archive REQ trouvée sous {args.archive}", file=sys.stderr)
        return 2

    print("=" * 78)
    print("L'ENTONNOIR DES NOMS — de Nom.csv à req_noms")
    print("=" * 78)
    print(f"\narchive : {chemin.name}")
    print("PORTÉE  : lecture seule. L'archive et un count(*). N'écrit rien.\n")

    lignes = vides = retires = norm_vide = doublons = 0
    #: Les paires déjà vues. **La clé primaire de `req_noms` est
    #: `(neq, nom_normalise)`** — compter autrement mesurerait autre chose que
    #: ce que la table stocke.
    vues: set[str] = set()
    par_type: dict[str, int] = {}

    with zipfile.ZipFile(chemin) as zf, zf.open("Nom.csv") as brut:
        texte = io.TextIOWrapper(brut, encoding="utf-8-sig", errors="replace")
        for row in csv.DictReader(texte):
            lignes += 1
            neq = (row.get("NEQ") or "").strip()
            nom = (row.get("NOM_ASSUJ") or "").strip()
            if not neq or not nom:
                vides += 1
                continue
            if (row.get("STAT_NOM") or "").strip().upper() != "V":
                retires += 1
                continue
            nom_norm = normaliser(nom)
            if not nom_norm:
                norm_vide += 1
                continue
            cle = f"{neq}|{nom_norm}"
            if cle in vues:
                doublons += 1
                continue
            vues.add(cle)
            t = (row.get("TYP_NOM_ASSUJ") or "").strip() or "(vide)"
            par_type[t] = par_type.get(t, 0) + 1
            if lignes % 1_000_000 == 0:
                print(f"   … {milliers(lignes)} lignes lues", flush=True)

    attendu = len(vues)

    print("-" * 78)
    print("LES PÉAGES, DANS L'ORDRE OÙ LE CHARGEUR LES APPLIQUE")
    print("-" * 78)
    def ligne(libelle: str, n: int) -> None:
        part = 100 * n / lignes if lignes else 0.0
        print(f"   {libelle:<48} {n:>9,}  {part:>5.1f} %")

    ligne("lignes de Nom.csv", lignes)
    ligne("  NEQ ou NOM vide", vides)
    ligne("  STAT_NOM ≠ V (noms retirés, écartés à dessein)", retires)
    ligne("  se normalise en chaîne VIDE", norm_vide)
    ligne("  même (NEQ, nom normalisé) déjà vu", doublons)
    ligne("= paires distinctes attendues dans req_noms", attendu)

    if par_type:
        print("\n   par type de nom (parmi les paires retenues) :")
        for t, n in sorted(par_type.items(), key=lambda kv: -kv[1])[:8]:
            print(f"      {t:<10} {n:>9,}")

    print("\n" + "-" * 78)
    print("CE QUE LA TABLE PORTE VRAIMENT")
    print("-" * 78)
    from falkye.db import refuser_si_cible_non_choisie

    code = refuser_si_cible_non_choisie()
    if code:
        return code

    from sqlalchemy import func, select

    from falkye.db import get_session
    from falkye.models.req_nom import REQNom

    session = get_session()
    try:
        reel = session.execute(select(func.count()).select_from(REQNom)).scalar() or 0
    finally:
        session.close()

    print(f"\n   count(*) sur req_noms : {milliers(reel)}")
    print(f"   attendu par l'archive : {milliers(attendu)}")
    ecart = reel - attendu
    if ecart == 0:
        print("\n   ✅ IDENTIQUES — la table porte exactement ce que l'archive donne.")
    else:
        print(f"\n   ⚠️ ÉCART DE {ecart:+,}")
        print("      Un écart NÉGATIF veut dire que des lignes envoyées n'ont pas")
        print("      atterri — `OR IGNORE` absorbe en silence. Un écart POSITIF")
        print("      veut dire que la table porte des restes d'un import antérieur :")
        print("      rien n'efface req_noms entre deux imports.")

    rss = _rss_mo()
    if rss is not None:
        print(f"\n   mémoire de CET outil : {rss:.0f} Mo (une empreinte par paire)")
    else:
        print("\n   mémoire de CET outil : non lisible — pas mesurée, pas nulle")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
