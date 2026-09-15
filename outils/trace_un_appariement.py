#!/usr/bin/env python3
"""UN appariement, montré en entier — la requête, les candidats, et ce qui est
passé au scoreur.

**La question qu'il tranche** *(Alexandre, 2026-09-16)* : *« Pour
`9309-3927 Quebec inc`, est-ce que `9309-3927 QUÉBEC INC.` est dans les candidats
récupérés? S'il y est et score 66, le score ment. S'il n'y est pas, la requête ne
le trouve pas — et c'est là qu'est le mur. »*

**Pourquoi un cas entier plutôt qu'une distribution de plus.** Trois hypothèses
ont été mesurées et sont tombées : *le seuil* (la masse est trop basse), *la
normalisation* (rejeu à zéro gain sur 4 873), *le champ `nom_normalise`*. **Il
reste la récupération des candidats, et rien d'autre** — et une distribution ne
dira pas si une ligne précise est dans une liste précise. **Un compte agrégé
répond « combien »; il ne répond jamais « où ».**

**Ce que l'outil montre, étape par étape, sans en sauter une.**

1. La normalisation de la requête, avec `repr` et longueur — *pas une
   description : la valeur.*
2. Le préfixe extrait, et **le SQL RÉELLEMENT ÉMIS**, valeurs liées comprises.
3. Le plan d'exécution SQLite (`EXPLAIN QUERY PLAN`) — *un SEARCH et un SCAN ne
   récupèrent pas le même lot.*
4. Les candidats rendus : `neq`, `nom`, `nom_normalise`, sa longueur et son
   `typeof` SQLite.
5. **La ligne ATTENDUE est-elle dedans?** Si non, quatre recherches directes la
   cherchent par d'autres chemins — *pour distinguer « absente du miroir » de
   « présente mais non récupérée », qui appellent des correctifs opposés.*
6. Le dictionnaire `choices` **tel qu'il est passé** à `process.extract`, et son
   classement complet.
7. Le score recalculé sur les deux formes affichées, à côté du score rendu.

⚠️ **Il emprunte les fonctions du moteur** — `candidats_par_nom`,
`resolve_neq_by_name`, `normaliser`. *Une requête recopiée à côté mesurerait sa
propre copie*, et c'est exactement l'écart qu'on cherche.

⚠️ **PORTÉE.** Lecture seule, sur le miroir local. Un seul nom. *Ce qu'il montre
vaut pour CE cas* — **une cause établie sur une ligne n'est pas une cause
établie sur 4 873**, et l'étape 5 dit laquelle des deux familles ce cas rejoint.

Usage :
    python3 outils/trace_un_appariement.py --nom "9309-3927 Quebec inc" \\
        --attendu "9309-3927 QUÉBEC INC."
    python3 outils/trace_un_appariement.py --nom "Ferme Dallaire Frères SENC"
"""
from __future__ import annotations

import argparse
import sys

#: Combien de candidats sont détaillés ligne à ligne. Au-delà, seul le compte est
#: rendu — **et le fait qu'il y ait eu troncature est dit**, jamais tu.
DETAIL_MAX = 40


def apercu(valeur, largeur: int = 58) -> str:
    """`repr` tronqué. **`repr` et pas `str`** : une chaîne vide, une chaîne d'un
    espace et `None` se ressemblent à l'affichage et n'ont pas la même cause."""
    texte = repr(valeur)
    return texte if len(texte) <= largeur else texte[: largeur - 1] + "…"


def sql_emis(requete) -> str:
    """Le SQL avec ses valeurs liées substituées — *ce que SQLite reçoit, pas ce
    que SQLAlchemy annonce.*"""
    try:
        return str(requete.compile(compile_kwargs={"literal_binds": True}))
    except Exception as exc:  # noqa: BLE001 - un type non littéralisable n'est pas un échec
        return f"(non littéralisable : {type(exc).__name__}) {requete}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--nom", required=True, help="le nom détecté, tel que la source l'a livré")
    parser.add_argument("--attendu", default=None,
                        help="le nom du miroir qu'on s'attend à voir apparier")
    parser.add_argument("--neq", default=None, help="le NEQ attendu, si on le connaît")
    parser.add_argument("--ville", default=None, help="la ville du dossier (bonus de +5)")
    args = parser.parse_args(argv)

    try:
        from rapidfuzz import fuzz, process
        from sqlalchemy import func, select, text

        from falkye.db import get_session
        from falkye.models.req_entry import REQEntry
        from falkye.sources.column_mapping import normaliser
        from falkye.sources.req import candidats_par_nom, resolve_neq_by_name
    except ImportError as exc:  # pragma: no cover - dépend de l'environnement
        print(f"Import impossible ({exc}). Lancer depuis la racine du dépôt.", file=sys.stderr)
        return 2

    session = get_session()
    try:
        print("=" * 78)
        print("UN APPARIEMENT, EN ENTIER")
        print("=" * 78)
        print("\nPORTÉE : lecture seule, miroir local, UN seul nom.")
        print("         Ce qui est montré vaut pour CE cas, pas pour les 4 873.")

        # --- 1. la normalisation -----------------------------------------
        print("\n" + "-" * 78)
        print("1. LA REQUÊTE, NORMALISÉE")
        print("-" * 78)
        nom_norm = normaliser(args.nom)
        print(f"\n   détecté brut   : {apercu(args.nom)}")
        print(f"   normalisé      : {apercu(nom_norm)}   ({len(nom_norm)} car.)")
        if args.attendu:
            attendu_norm = normaliser(args.attendu)
            print(f"\n   attendu brut   : {apercu(args.attendu)}")
            print(f"   normalisé      : {apercu(attendu_norm)}   ({len(attendu_norm)} car.)")
            print(f"   les deux formes normalisées sont ÉGALES : {nom_norm == attendu_norm}")
            print(f"   WRatio(norm, norm) = {fuzz.WRatio(nom_norm, attendu_norm):.1f}")
        else:
            attendu_norm = None

        # --- 2. la requête réellement émise -------------------------------
        print("\n" + "-" * 78)
        print("2. LE SQL RÉELLEMENT ÉMIS")
        print("-" * 78)
        prefixe = nom_norm.split(" ")[0]
        print(f"\n   préfixe extrait : {apercu(prefixe)}")
        requete_prefixe = (
            select(REQEntry).where(REQEntry.nom_normalise.op("GLOB")(f"{prefixe}*")).limit(2000)
        )
        requete_repli = (
            select(REQEntry).where(REQEntry.nom_normalise.contains(nom_norm[:6])).limit(2000)
        )
        print(f"\n   PRÉFIXE :\n      {sql_emis(requete_prefixe)}")
        print(f"\n   REPLI (si le préfixe ne rend rien) :\n      {sql_emis(requete_repli)}")

        # --- 3. le plan d'exécution ---------------------------------------
        print("\n" + "-" * 78)
        print("3. LE PLAN D'EXÉCUTION — un SEARCH et un SCAN ne rendent pas le même lot")
        print("-" * 78)
        try:
            plan = session.execute(
                text(f"EXPLAIN QUERY PLAN {sql_emis(requete_prefixe)}")
            ).all()
            for ligne in plan:
                print(f"   {ligne[-1]}")
        except Exception as exc:  # noqa: BLE001 - un moteur non SQLite n'a pas ce plan
            print(f"   (plan indisponible : {type(exc).__name__} — moteur non SQLite?)")

        # --- 4. les candidats, tels que le moteur les récupère -------------
        print("\n" + "-" * 78)
        print("4. LES CANDIDATS RÉCUPÉRÉS — par la fonction DU MOTEUR")
        print("-" * 78)
        candidats = candidats_par_nom(session, nom_norm)
        n_prefixe = len(session.execute(requete_prefixe).scalars().all())
        print(f"\n   le préfixe seul rend    : {n_prefixe} ligne(s)")
        print(f"   candidats_par_nom rend  : {len(candidats)} ligne(s)")
        if n_prefixe == 0 and candidats:
            print("   ⚠️ LE REPLI A SERVI : le préfixe n'a rien rendu.")
        print()
        for i, c in enumerate(candidats[:DETAIL_MAX], start=1):
            stocke = c.nom_normalise
            print(f"   {i:>3}. neq={c.neq}")
            print(f"        nom            = {apercu(c.nom)}")
            print(f"        nom_normalise  = {apercu(stocke)}   ({len(stocke or '')} car.)")
        if len(candidats) > DETAIL_MAX:
            print(f"\n   … {len(candidats) - DETAIL_MAX} candidat(s) de plus, non détaillés.")

        # Le type SQLite de la colonne, sur ces lignes : un BLOB n'est JAMAIS
        # apparié par GLOB, et se relit en octets côté Python.
        if candidats:
            neqs = [c.neq for c in candidats[:DETAIL_MAX]]
            marques = ",".join(f"'{n}'" for n in neqs)
            try:
                types = session.execute(text(
                    f"SELECT typeof(nom_normalise) AS t, count(*) FROM req_entries "
                    f"WHERE neq IN ({marques}) GROUP BY t"
                )).all()
                print("\n   typeof(nom_normalise) sur ces lignes :")
                for t_, n in types:
                    print(f"      {str(t_):<10} {n}")
            except Exception as exc:  # noqa: BLE001
                print(f"   (typeof indisponible : {type(exc).__name__})")

        # --- 5. LA LIGNE ATTENDUE EST-ELLE DEDANS ? ------------------------
        print("\n" + "-" * 78)
        print("5. LA LIGNE ATTENDUE — dans le lot, ou introuvable ?")
        print("-" * 78)
        if not (args.attendu or args.neq):
            print("\n   (aucun --attendu ni --neq donné : étape sautée)")
        else:
            dans_le_lot = [
                c for c in candidats
                if (args.neq and c.neq == args.neq)
                or (args.attendu and (c.nom or "") == args.attendu)
                or (attendu_norm and (c.nom_normalise or "") == attendu_norm)
            ]
            if dans_le_lot:
                print(f"\n   ✅ ELLE EST DANS LE LOT ({len(dans_le_lot)} ligne(s)).")
                print("      → si son score est bas, le MUR EST DANS LE SCORE.")
                for c in dans_le_lot:
                    print(f"\n      neq={c.neq}")
                    print(f"      nom            = {apercu(c.nom)}")
                    print(f"      nom_normalise  = {apercu(c.nom_normalise)}")
                    print(f"      WRatio(requête_norm, nom_normalise) = "
                          f"{fuzz.WRatio(nom_norm, c.nom_normalise or ''):.1f}")
            else:
                print("\n   ⛔ ELLE N'EST PAS DANS LE LOT.")
                print("      → le mur est dans la RÉCUPÉRATION, pas dans le score.")
                print("\n   Quatre recherches directes, pour distinguer « absente du miroir »")
                print("   de « présente mais non récupérée » — deux correctifs opposés :")
                recherches = []
                if args.neq:
                    recherches.append(("par NEQ exact", select(REQEntry).where(REQEntry.neq == args.neq)))
                if args.attendu:
                    recherches.append(("par nom BRUT exact",
                                       select(REQEntry).where(REQEntry.nom == args.attendu)))
                    recherches.append(("par nom brut, sous-chaîne",
                                       select(REQEntry).where(
                                           REQEntry.nom.contains(args.attendu[:12])).limit(10)))
                if attendu_norm:
                    recherches.append(("par nom_normalise exact",
                                       select(REQEntry).where(
                                           REQEntry.nom_normalise == attendu_norm)))
                for libelle, requete in recherches:
                    lignes = session.execute(requete.limit(10)).scalars().all()
                    print(f"\n      {libelle} : {len(lignes)} ligne(s)")
                    for c in lignes[:5]:
                        print(f"         neq={c.neq}  nom={apercu(c.nom, 44)}")
                        print(f"         nom_normalise={apercu(c.nom_normalise, 44)}"
                              f"  ({len(c.nom_normalise or '')} car.)")
                        commence = (c.nom_normalise or "").startswith(prefixe)
                        print(f"         commence par {prefixe!r} : {commence}"
                              + ("" if commence else "   ⚠️ LE GLOB NE PEUT PAS LA TROUVER"))

                # Combien de lignes du miroir commencent par ce préfixe, en SQL pur.
                try:
                    n_glob = session.execute(text(
                        "SELECT count(*) FROM req_entries WHERE nom_normalise GLOB :m"
                    ), {"m": f"{prefixe}*"}).scalar()
                    n_like = session.execute(text(
                        "SELECT count(*) FROM req_entries WHERE nom LIKE :m"
                    ), {"m": f"{prefixe}%"}).scalar()
                    print(f"\n      lignes dont nom_normalise GLOB '{prefixe}*' : {n_glob}")
                    print(f"      lignes dont nom       LIKE '{prefixe}%'      : {n_like}")
                    if n_like and n_glob is not None and n_glob < n_like:
                        print(f"      ⚠️ ÉCART DE {n_like - n_glob} : le nom BRUT commence par")
                        print("         le préfixe, la colonne normalisée non. La récupération")
                        print("         ne voit pas des lignes qui sont pourtant là.")
                except Exception as exc:  # noqa: BLE001
                    print(f"      (comptes indisponibles : {type(exc).__name__})")

        # --- 6. ce qui est passé au scoreur --------------------------------
        print("\n" + "-" * 78)
        print("6. CE QUI EST PASSÉ AU SCOREUR — le dictionnaire tel quel")
        print("-" * 78)
        choix = {c.neq: c.nom_normalise for c in candidats}
        print(f"\n   process.extract(")
        print(f"       query   = {apercu(nom_norm)},")
        print(f"       choices = {{  # {len(choix)} entrée(s)")
        for neq, valeur in list(choix.items())[:DETAIL_MAX]:
            print(f"           {neq!r}: {apercu(valeur, 46)},")
        if len(choix) > DETAIL_MAX:
            print(f"           …  {len(choix) - DETAIL_MAX} de plus")
        print("       },")
        print("       scorer  = fuzz.WRatio, limit = 5)")
        classement = process.extract(nom_norm, choix, scorer=fuzz.WRatio, limit=5)
        print("\n   → rendu :")
        for valeur, score, cle in classement:
            print(f"        {score:>6.2f}   neq={cle}   valeur={apercu(valeur, 44)}")
        if not classement:
            print("        (aucun)")

        # --- 7. le score rendu par le moteur, à côté du recalculé ----------
        print("\n" + "-" * 78)
        print("7. LE SCORE DU MOTEUR, ET LE MÊME RECALCULÉ")
        print("-" * 78)
        matches = resolve_neq_by_name(session, args.nom, ville=args.ville)
        if not matches:
            print("\n   le moteur ne rend AUCUN candidat scoré.")
        else:
            for m in matches:
                recalcul = fuzz.WRatio(nom_norm, m.entry.nom_normalise or "")
                ecart = "   ← ÉCART" if abs(recalcul - m.score) > 0.05 else ""
                print(f"\n   score rendu {m.score:>6.2f}   neq={m.entry.neq}")
                print(f"      nom affiché    = {apercu(m.entry.nom, 46)}")
                print(f"      nom_normalise  = {apercu(m.entry.nom_normalise, 46)}")
                print(f"      recalcul WRatio(requête_norm, nom_normalise) = {recalcul:.2f}{ecart}")
            if args.ville:
                print(f"\n   ⚠️ --ville {args.ville!r} donné : un bonus de +5 a pu s'appliquer,")
                print("      ce qui explique un écart de exactement 5 points avec le recalcul.")

        print("\n" + "=" * 78)
        print("   Rien n'a été écrit. Ce cas dit où est le mur POUR LUI —")
        print("   l'étendre aux 4 873 demande de le rejouer sur les 4 873.")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
