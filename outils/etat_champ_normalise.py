#!/usr/bin/env python3
"""L'état RÉEL de `req_entries.nom_normalise` — et laquelle des trois réparations
le cas demande.

**Le fait qui justifie cet outil** *(Alexandre, 2026-09-15)*. Sur l'hôte,
**1 371 730 des 2 730 146 lignes du miroir (50,2 %) ont un `nom_normalise` vide
ou absent**, et une ligne dont `nom` vaut `9309-3927 QUÉBEC INC.` porte un
`nom_normalise` de `9309 3927 quebec` — *la forme juridique retirée d'un seul
côté.* **Les 4 873 « candidats trop faibles », 58 % du mur d'appariement, sont
probablement presque tous là-dedans.**

**Ce que le code du dépôt dit, et qui contredit la donnée.** `nom` et
`nom_normalise` sont écrits **ensemble, dans la même instruction, depuis la même
chaîne**, aux quatre seuls endroits qui les écrivent *(`req.py` 469, 477-478,
869, 899)*. `normaliser` n'a pas changé depuis le 3 septembre. Et elle ne rend
vide sur aucun des noms relevés. **Donc une prémisse est fausse, et aucune
lecture de code ne dira laquelle.**

⚠️ **La contradiction centrale, à vérifier AVANT tout le reste.** Un score de 0
exige que les candidats récupérés portent une chaîne **vide** *(mesuré :
`process.extract` sur cent valeurs vides rend `('', 0.0)`)*. Or ils ont été
récupérés par `GLOB 'préfixe*'` — **qui porte sur cette même colonne**. *Une
chaîne vide ne peut pas satisfaire ce filtre.* **Si le contrôle 3 ci-dessous
montre des lignes rendues par le filtre dont la valeur lue est vide, alors le
filtre et la lecture ne voient pas la même valeur** — et le défaut n'est pas dans
la donnée, il est sous elle *(encodage de la colonne, moteur, liaison)*.

**LES TROIS RÉPARATIONS, et ce qui les départage.**

| ce que la mesure montre | réparation | coût |
|---|---|---|
| `normaliser(nom)` rend la bonne chaîne, `nom` est juste | **recalcul sur place** de la colonne | minutes, 0 écriture facturée |
| `nom` est faux ou vide lui aussi | **réimport** de l'archive | ~33 min, 3,5 Go de pic |
| `normaliser(nom)` rend elle-même une mauvaise chaîne | **réécrire la normalisation**, PUIS recalculer | à instruire |

*C'est le contrôle 4 qui tranche, et il tranche par un compte, pas par un exemple.*

⚠️ **PORTÉE.** Lecture seule, sur le miroir LOCAL. **Rien n'est écrit, aucune
colonne n'est recalculée** — un défaut mesuré n'est pas un défaut corrigé, et le
recalcul est une décision d'Alexandre. Aucune écriture facturée : le miroir est
un fichier local *(falkye/db.py, deux moteurs liés par métadonnée)*.

Usage :
    python3 outils/etat_champ_normalise.py
    python3 outils/etat_champ_normalise.py --prefixe ferme --exemples 30
    python3 outils/etat_champ_normalise.py --echantillon 50000
"""
from __future__ import annotations

from outils.nombres import milliers

import argparse
import sys
from collections import Counter

#: Le préfixe du contrôle de contradiction. `ferme` est celui du cas réel —
#: `Ferme Dallaire Frères SENC`, score 0 avec cent candidats récupérés.
PREFIXE_DEFAUT = "ferme"


def classer_ecart(nom: str, stocke: str | None, attendu: str) -> str:
    """Dit EN QUOI la valeur stockée s'écarte de celle que `normaliser` rendrait.

    **Les classes appellent des réparations différentes** — c'est la seule raison
    de les séparer. *Un compte global dirait « la moitié est cassée » et ne dirait
    pas quoi faire.*
    """
    # **L'ordre est le résultat.** Un `nom` source vide est testé EN PREMIER parce
    # qu'il décide seul de la réparation : aucun recalcul ne répare une ligne dont
    # il n'y a rien à recalculer. Classée « VIDE » d'abord, elle serait comptée
    # comme réparable et le verdict désignerait le mauvais chemin.
    if not nom.strip():
        return "nom source VIDE — rien à normaliser"
    if stocke is None:
        return "ABSENT (NULL)"
    if stocke == "":
        return "VIDE ('')"
    if stocke == attendu:
        return "conforme"
    if attendu.startswith(stocke) and attendu != stocke:
        # Le cas 9309-3927 : la valeur stockée est un PRÉFIXE de l'attendue.
        manque = attendu[len(stocke):].strip()
        return f"TRONQUÉ en queue (manque {manque!r})" if len(manque) <= 12 else "TRONQUÉ en queue"
    if stocke.startswith(attendu):
        return "plus LONG que l'attendu"
    return "DIVERGENT (ni préfixe ni suffixe)"


def resume_longueurs(longueurs: list[int]) -> list[tuple[str, int]]:
    """Distribution des longueurs par tranche. **Une valeur de 1 à 4 caractères
    contre une requête de 20 produit un score dans la bande 60-68** — c'est la
    signature mesurée du 66, et elle doit se compter, pas se deviner."""
    tranches = Counter()
    for n in longueurs:
        if n == 0:
            tranches["0 (vide)"] += 1
        elif n <= 4:
            tranches["1-4  ⚠️ signature du score 60-68"] += 1
        elif n <= 10:
            tranches["5-10"] += 1
        elif n <= 20:
            tranches["11-20"] += 1
        elif n <= 40:
            tranches["21-40"] += 1
        else:
            tranches["41+"] += 1
    ordre = ["0 (vide)", "1-4  ⚠️ signature du score 60-68", "5-10", "11-20", "21-40", "41+"]
    return [(k, tranches[k]) for k in ordre if tranches[k]]


def verdict(classes: Counter) -> list[str]:
    """La réparation que les comptes désignent. **Rendue comme une lecture, pas
    comme une instruction** — c'est Alexandre qui tranche."""
    total = sum(classes.values())
    if not total:
        return ["Aucune ligne examinée — rien à lire."]
    conformes = classes.get("conforme", 0)
    source_vide = classes.get("nom source VIDE — rien à normaliser", 0)
    lignes = []
    if conformes == total:
        lignes.append("Toutes les lignes examinées sont CONFORMES. Le défaut n'est pas ici.")
        return lignes
    if source_vide > total * 0.05:
        lignes.append(f"⚠️ {source_vide} ligne(s) ont un `nom` SOURCE vide ou blanc.")
        lignes.append("   Un recalcul ne les répare pas — il n'y a rien à recalculer.")
        lignes.append("   → RÉIMPORT de l'archive, pour ces lignes-là au moins.")
    if total - conformes - source_vide > 0:
        lignes.append(f"{total - conformes - source_vide} ligne(s) ont un `nom` EXPLOITABLE")
        lignes.append("   dont la normalisation recalculée diffère de la valeur stockée.")
        lignes.append("   → RECALCUL SUR PLACE suffisant pour celles-là : le nom est en base,")
        lignes.append("     la fonction rend la bonne chaîne, rien à retélécharger.")
    lignes.append("")
    lignes.append("⚠️ Ce verdict porte sur les lignes EXAMINÉES. Il ne dit pas que la")
    lignes.append("   fonction de normalisation est bonne dans l'absolu — il dit qu'elle")
    lignes.append("   rend, sur ces lignes, autre chose que ce qui est stocké.")
    return lignes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--echantillon", type=int, default=20000,
                        help="lignes examinées pour la comparaison stocké/recalculé (défaut 20000)")
    parser.add_argument("--exemples", type=int, default=15,
                        help="exemples montrés par classe d'écart (défaut 15)")
    parser.add_argument("--prefixe", default=PREFIXE_DEFAUT,
                        help=f"préfixe du contrôle de contradiction (défaut {PREFIXE_DEFAUT!r})")
    args = parser.parse_args(argv)

    try:
        from sqlalchemy import func, select, text

        from falkye.db import get_session
        from falkye.models.req_entry import REQEntry
        from falkye.sources.column_mapping import normaliser
    except ImportError as exc:  # pragma: no cover - dépend de l'environnement
        print(f"Import impossible ({exc}). Lancer depuis la racine du dépôt.", file=sys.stderr)
        return 2

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
        print("=" * 78)
        print("L'ÉTAT RÉEL DE req_entries.nom_normalise")
        print("=" * 78)
        print("\nPORTÉE : lecture seule, miroir LOCAL. Rien n'est écrit, rien n'est recalculé.")

        # --- 1. les comptes bruts, en SQL, sans passer par l'ORM -------------
        print("\n" + "-" * 78)
        print("1. LES COMPTES — posés en SQL, sans interprétation")
        print("-" * 78)
        total = session.execute(select(func.count()).select_from(REQEntry)).scalar() or 0
        print(f"   lignes au miroir                   : {milliers(total)}")
        for libelle, condition in [
            ("nom_normalise IS NULL", "nom_normalise IS NULL"),
            ("nom_normalise = ''", "nom_normalise = ''"),
            ("nom_normalise blanc (que des espaces)", "trim(nom_normalise) = '' AND nom_normalise <> ''"),
            ("nom IS NULL ou ''", "nom IS NULL OR nom = ''"),
        ]:
            n = session.execute(text(f"SELECT count(*) FROM req_entries WHERE {condition}")).scalar() or 0
            part = f"  ({100 * n / total:.1f} %)" if total else ""
            print(f"   {libelle:<35}: {milliers(n)}" + part)

        # ⚠️ `typeof()` : si la colonne porte des BLOB plutôt que du TEXT, GLOB ne
        # peut PAS les apparier (SQLite compare les types), et Python les relit en
        # bytes. C'est une des rares façons dont filtre et lecture divergeraient.
        print("\n   typeof(nom_normalise) — un BLOB n'est jamais apparié par GLOB :")
        for typ, n in session.execute(
            text("SELECT typeof(nom_normalise) AS t, count(*) FROM req_entries GROUP BY t")
        ):
            print(f"      {str(typ):<10} {milliers(n)}")

        # --- 2. la distribution des longueurs --------------------------------
        print("\n" + "-" * 78)
        print("2. LA DISTRIBUTION DES LONGUEURS — la signature du score 66 se compte")
        print("-" * 78)
        for libelle, n in session.execute(text(
            "SELECT CASE"
            "  WHEN nom_normalise IS NULL THEN 'ABSENT (NULL)'"
            "  WHEN length(nom_normalise) = 0 THEN '0 (vide)'"
            "  WHEN length(nom_normalise) <= 4 THEN '1-4  signature du score 60-68'"
            "  WHEN length(nom_normalise) <= 10 THEN '5-10'"
            "  WHEN length(nom_normalise) <= 20 THEN '11-20'"
            "  WHEN length(nom_normalise) <= 40 THEN '21-40'"
            "  ELSE '41+' END AS tranche, count(*)"
            " FROM req_entries GROUP BY tranche ORDER BY 2 DESC"
        )):
            part = f"  ({100 * n / total:.1f} %)" if total else ""
            print(f"   {libelle:<34} {milliers(n)}" + part)

        # --- 3. LA CONTRADICTION ---------------------------------------------
        print("\n" + "-" * 78)
        print(f"3. LA CONTRADICTION — le filtre GLOB '{args.prefixe}*' et ce qu'on relit")
        print("-" * 78)
        print("   Une chaîne vide ne PEUT PAS satisfaire GLOB. Si des lignes rendues par")
        print("   ce filtre se relisent vides, le filtre et la lecture divergent, et le")
        print("   défaut n'est pas dans la donnée — il est sous elle.")
        rendues = session.execute(
            select(REQEntry).where(REQEntry.nom_normalise.op("GLOB")(f"{args.prefixe}*")).limit(2000)
        ).scalars().all()
        vides_rendues = [r for r in rendues if not (r.nom_normalise or "").strip()]
        hors_prefixe = [
            r for r in rendues
            if (r.nom_normalise or "") and not (r.nom_normalise or "").startswith(args.prefixe)
        ]
        print(f"\n   lignes rendues par le filtre            : {len(rendues)}")
        print(f"   … dont la valeur RELUE est vide/blanche : {len(vides_rendues)}"
              + ("   ⚠️ CONTRADICTION" if vides_rendues else "   (aucune — cohérent)"))
        print(f"   … dont la valeur RELUE ne commence pas  : {len(hors_prefixe)}"
              f"   par « {args.prefixe} »"
              + ("   ⚠️ CONTRADICTION" if hors_prefixe else ""))
        for r in (vides_rendues + hors_prefixe)[: args.exemples]:
            print(f"      neq={r.neq}  nom={r.nom[:44]!r}")
            print(f"         nom_normalise relu = {r.nom_normalise!r}")

        # --- 4. CE QUI TRANCHE ENTRE LES TROIS RÉPARATIONS -------------------
        print("\n" + "-" * 78)
        print("4. STOCKÉ CONTRE RECALCULÉ — c'est CE compte qui choisit la réparation")
        print("-" * 78)
        lot = session.execute(select(REQEntry).limit(args.echantillon)).scalars().all()
        print(f"   {len(lot)} ligne(s) examinée(s)"
              + ("   ⚠️ PRISES DANS L'ORDRE DE LA TABLE, pas au hasard —"
                 if len(lot) < total else ""))
        if len(lot) < total:
            print("      provenance déclarée : ce n'est pas un tirage représentatif.")
        classes: Counter = Counter()
        exemples: dict[str, list] = {}
        longueurs: list[int] = []
        for r in lot:
            stocke = r.nom_normalise
            attendu = normaliser(r.nom or "")
            cl = classer_ecart(r.nom or "", stocke, attendu)
            classes[cl] += 1
            longueurs.append(len(stocke or ""))
            if len(exemples.setdefault(cl, [])) < args.exemples and cl != "conforme":
                exemples[cl].append((r.neq, r.nom, stocke, attendu))
        print()
        for cl, n in classes.most_common():
            part = f"  ({100 * n / len(lot):.1f} %)" if lot else ""
            print(f"   {n:>8}  {cl}" + part)
        print("\n   longueurs de la valeur STOCKÉE, sur ce même lot :")
        for libelle, n in resume_longueurs(longueurs):
            print(f"      {n:>8}  {libelle}")

        for cl, lignes in exemples.items():
            if not lignes:
                continue
            print(f"\n   — {cl} —")
            for neq, nom, stocke, attendu in lignes:
                print(f"      neq {neq}")
                print(f"        nom       : {(nom or '')[:64]}")
                print(f"        stocké    : {stocke!r}")
                print(f"        recalculé : {attendu!r}")

        print("\n" + "=" * 78)
        print("CE QUE CES COMPTES DÉSIGNENT")
        print("=" * 78)
        for ligne in verdict(classes):
            print("   " + ligne)
        print("\n   ⚠️ Rien n'a été écrit. Le recalcul est une décision, pas une suite.")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
