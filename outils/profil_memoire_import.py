#!/usr/bin/env python3
"""Où passe la mémoire de la phase 1 — **mesurée sur l'hôte, étape par étape.**

**Le fait qui a écrit cet outil** *(2026-09-16, après l'OOM)*. L'import est mort à
**7 372 Mo, en phase 1**. Mon inventaire, extrapolé d'une mesure locale, en
explique **3 390** :

    index des noms élus                             543 Mo
    index des établissements (257 563 lignes)       100 Mo
    resolues                                      1 078 Mo
    lignes_entreprise                             1 669 Mo
                                                  -------
    TOTAL expliqué                                3 390 Mo
    NON EXPLIQUÉ                                  3 982 Mo

⛔ **Il manque plus que tout ce que j'ai proposé de retirer.** *Et mon correctif
le plus gros — l'archivage en flux, 1 179 Mo — vit dans le moteur de diff, APRÈS
la phase 1 : il ne touche pas la phase qui a tué l'import.*

**Donc on ne relance pas, et on ne construit pas : on mesure.** *Décider sur une
extrapolation quand une mesure coûte cinq minutes est exactement ce qu'on s'est
interdit ce matin.*

**Deux raisons plausibles à l'écart, et cet outil les départage.**

*(1)* **`tracemalloc` compte les objets vivants; le système compte la RSS.**
*L'allocateur de Python ne rend pas volontiers la mémoire libérée, et 2,7 millions
de petits objets créés-puis-jetés la fragmentent.* **La RSS peut dépasser de
beaucoup la somme des objets vivants**, et aucun calcul ne le prédit.

*(2)* **Mon extrapolation est LINÉAIRE**, faite sur 200 000 objets. *À 2,7
millions, les redimensionnements de dictionnaires et de listes ne se comportent
pas pareil.*

**Ce que l'outil fait, et ne fait pas.**

- Il refait la **phase 1 seule**, dans l'ordre réel, en empruntant les fonctions
  du moteur — et relève la **RSS du système** à chaque étape, pas une estimation.
- ⚠️ **Il n'ouvre AUCUNE base, n'écrit rien, ne déclenche aucun diff.** *Pas de
  quarantaine, pas d'archive, pas de ligne d'état.* **Un profilage qui laisserait
  une trace en base ne serait pas un profilage.**
- Avec `--lignes`, il s'arrête après N lignes d'`Entreprise.csv` : **lancer
  100 000, puis 500 000, puis 1 000 000 donne une COURBE**, et une courbe
  mesurée vaut mieux qu'une droite supposée.

Usage, SUR L'HÔTE :
    python3 -m outils.profil_memoire_import --chemin /opt/falkye/import --lignes 100000
    python3 -m outils.profil_memoire_import --chemin /opt/falkye/import --lignes 500000
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
import zipfile
from pathlib import Path


def rss_mo() -> float | None:
    """La mémoire RÉSIDENTE du processus, vue par le système.

    **`/proc/self/statm` et non `tracemalloc`** : c'est la RSS qui décide de
    l'OOM, pas la somme des objets vivants. *Les deux peuvent différer d'un
    facteur deux sans qu'aucun bogue n'existe* — l'allocateur garde ce qu'il a
    pris.
    """
    try:
        pages = int(Path("/proc/self/statm").read_text().split()[1])
    except (OSError, ValueError, IndexError):
        return None
    import resource

    return pages * resource.getpagesize() / 1024 / 1024


def _etape(nom: str, avant: float | None) -> float | None:
    """Imprime la RSS et le delta depuis l'étape précédente. **`None` reste
    `None`** — sur une machine sans `/proc`, l'outil dit qu'il ne mesure pas
    plutôt que d'afficher zéro."""
    maintenant = rss_mo()
    if maintenant is None:
        print(f"   {nom:<46} RSS non lisible")
        return None
    delta = f"{maintenant - avant:+8.0f}" if avant is not None else "       —"
    print(f"   {nom:<46} {maintenant:8.0f} Mo  ({delta} Mo)", flush=True)
    return maintenant


def _mesurer_etat_precedent(source_id: str) -> int:
    """Ce que l'état précédent du moteur de diff coûte, **dans les deux formes**.

    *La mesure du 16 septembre a montré que la phase 1 coûte ~3 000 Mo sur un pic
    de 7 372 : le reste vient du moteur de diff.* **Celui-ci chargeait la ligne
    ENTIÈRE, `donnees_normalisees` comprise, pour 2,7 millions de lignes** — alors
    que ce champ n'est lu que pour les quelques milliers de clés modifiées.

    L'outil charge les deux formes **l'une après l'autre**, en libérant entre les
    deux, et rend la RSS de chacune. *Le gain se MESURE, il ne s'annonce pas.*

    ⚠️ **Lecture seule sur le miroir.** Aucune écriture, aucun diff.
    """
    try:
        import gc

        from sqlalchemy import select

        from falkye.db import get_session
        from falkye.models.etat_ligne_source import EtatLigneSource
    except ImportError as exc:  # pragma: no cover - dépend de l'environnement
        print(f"Import impossible ({exc}).", file=sys.stderr)
        return 2

    print("=" * 78)
    print(f"L'ÉTAT PRÉCÉDENT DU MOTEUR DE DIFF — source {source_id!r}")
    print("=" * 78)
    print("\nPORTÉE : lecture seule sur le miroir. Aucune écriture, aucun diff.")
    print()

    session = get_session()
    try:
        rss = _etape("au démarrage", None)

        # L'ANCIENNE forme : la ligne entière, `donnees_normalisees` comprise.
        ancien = {
            row.cle_naturelle: row
            for row in session.execute(
                select(
                    EtatLigneSource.cle_naturelle,
                    EtatLigneSource.empreinte,
                    EtatLigneSource.donnees_normalisees,
                ).where(EtatLigneSource.source_id == source_id)
            ).all()
        }
        rss_ancien = _etape(f"ANCIENNE forme : ligne entière ({len(ancien)} clés)", rss)
        n = len(ancien)
        del ancien
        gc.collect()
        rss = _etape("  … libérée", rss_ancien)

        # La NEUVE : clé -> empreinte, en flux.
        neuf: dict[str, str] = {}
        for cle, empreinte in session.execute(
            select(EtatLigneSource.cle_naturelle, EtatLigneSource.empreinte)
            .where(EtatLigneSource.source_id == source_id)
            .execution_options(yield_per=5000)
        ):
            neuf[cle] = empreinte
        rss_neuf = _etape(f"NEUVE forme : clé -> empreinte ({len(neuf)} clés)", rss)

        print("\n" + "-" * 78)
        print("LE GAIN, MESURÉ")
        print("-" * 78)
        if rss_ancien is None or rss_neuf is None or rss is None:
            print("\n   RSS non lisible — aucune conclusion. Ce n'est pas zéro gain,")
            print("   c'est zéro mesure.")
            return 0
        print(f"\n   clés dans l'état précédent : {n}")
        print("\n   ⚠️ LIRE LES DELTAS DE LA COLONNE DE DROITE, pas les totaux.")
        print("      Le premier `+` est ce que coûte l'ANCIENNE forme; le dernier,")
        print("      ce que coûte la NEUVE. **La libération entre les deux ne rend")
        print("      pas forcément la mémoire au système** — l'allocateur de Python")
        print("      garde ce qu'il a pris, donc un delta de libération proche de")
        print("      zéro n'est pas une fuite : c'est le comportement normal.")
        print("\n   ⚠️ Et le gain réel à l'import est SUPÉRIEUR à cet écart : la forme")
        print("      neuve lit en flux, donc elle évite aussi la liste intermédiaire")
        print("      que `.all()` matérialisait avant de construire le dictionnaire.")
        return 0
    finally:
        session.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--chemin", default=None,
                        help="l'archive, ou le répertoire (requis sauf avec --etat-precedent)")
    parser.add_argument("--lignes", type=int, default=None,
                        help="s'arrêter après N lignes d'Entreprise.csv (défaut : toutes)")
    parser.add_argument("--etat-precedent", metavar="SOURCE_ID", default=None,
                        help="mesurer L'ÉTAT PRÉCÉDENT du moteur de diff pour cette "
                             "source (ex. req) — les DEUX formes, l'ancienne et la neuve")
    args = parser.parse_args(argv)

    if args.etat_precedent:
        return _mesurer_etat_precedent(args.etat_precedent)
    if not args.chemin:
        print("Donner --chemin (l'archive) ou --etat-precedent (la base).", file=sys.stderr)
        return 2

    try:
        from falkye.sources.req import (
            _charger_index_etablissements,
            _charger_index_noms,
            _ligne_entreprise,
            _resoudre_entreprise,
        )
    except ImportError as exc:  # pragma: no cover - dépend de l'environnement
        print(f"Import impossible ({exc}). Lancer depuis la racine du dépôt.", file=sys.stderr)
        return 2

    from outils.archives_req import ligne_de_provenance, resoudre

    archive = resoudre(args.chemin)
    if archive is None:
        print(f"⛔ aucune archive à {args.chemin!r}.", file=sys.stderr)
        return 2

    print("=" * 78)
    print("OÙ PASSE LA MÉMOIRE DE LA PHASE 1")
    print("=" * 78)
    print(f"\n{ligne_de_provenance(archive)}")
    print(f"lignes d'Entreprise.csv : {args.lignes or 'toutes'}")
    print("\nPORTÉE : aucune base ouverte, aucune écriture, aucun diff déclenché.")
    print("         RSS du système, pas une estimation — c'est elle qui décide de l'OOM.")
    print()

    rss = _etape("au démarrage", None)
    with zipfile.ZipFile(archive) as zf:
        noms = _charger_index_noms(zf)
        rss = _etape(f"index des noms élus ({len(noms)} NEQ)", rss)

        etablissements = _charger_index_etablissements(zf)
        total_etab = sum(len(v) for v in etablissements.values())
        rss = _etape(f"index des établissements ({total_etab} lignes)", rss)

        resolues = []
        lignes_entreprise = []
        lues = 0
        jalon = 0
        with zf.open("Entreprise.csv") as brut:
            texte = io.TextIOWrapper(brut, encoding="utf-8-sig", errors="replace")
            for rangee in csv.DictReader(texte):
                if args.lignes is not None and lues >= args.lignes:
                    break
                lues += 1
                r = _resoudre_entreprise(rangee, noms, etablissements)
                if r is None:
                    continue
                resolues.append(r)
                lignes_entreprise.append(_ligne_entreprise(r))
                # Un jalon tous les 250 000 : la COURBE est le résultat, pas le
                # point final. Un saut brusque désignerait un redimensionnement.
                if lues - jalon >= 250_000:
                    jalon = lues
                    rss = _etape(f"  … {lues} lignes lues", rss)

        rss = _etape(f"phase 1 terminée ({lues} lues, {len(resolues)} retenues)", rss)

        # `lignes_etab` : la structure que l'import n'a jamais atteinte.
        lignes_etab = [
            (neq, etab) for neq, etabs in etablissements.items() for etab in etabs
        ]
        rss = _etape(f"lignes_etab ({len(lignes_etab)} lignes)", rss)

    print("\n" + "-" * 78)
    print("CE QUE ÇA DIT")
    print("-" * 78)
    if rss is None:
        print("\n   RSS non lisible sur cette machine — aucune conclusion.")
        print("   ⚠️ Ce n'est pas « zéro mémoire » : c'est zéro mesure.")
        return 0
    if args.lignes:
        par_ligne = None
        if lues:
            par_ligne = rss / lues
            print(f"\n   {rss:.0f} Mo pour {lues} lignes")
            print(f"   ⚠️ L'extrapolation NAÏVE à 2 730 146 lignes donnerait "
                  f"{par_ligne * 2_730_146:.0f} Mo.")
            print("      Elle suppose que TOUT croît linéairement, y compris les deux")
            print("      index qui sont déjà complets. **Elle surestime.** Refaire la")
            print("      mesure à 500 000 puis 1 000 000 donne la vraie pente.")
    else:
        print(f"\n   {rss:.0f} Mo à la fin de la phase 1, sur la population entière.")
        print("   C'est le chiffre à comparer à la mémoire de la machine — et c'est")
        print("   lui qui décide si l'import passe.")
    print("\n   ⚠️ Le moteur de diff vient APRÈS, et il ajoute encore : l'état")
    print("      précédent (2,7 M lignes lues de la base) et l'archivage du")
    print("      snapshot. Ce relevé est un PLANCHER du pic de l'import.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
