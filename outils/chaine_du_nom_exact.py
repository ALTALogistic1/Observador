#!/usr/bin/env python3
"""Un nom EXACTEMENT présent au registre : où la chaîne casse-t-elle?

**Le fait qui écrit cet outil** *(2026-09-17, relevé par Alexandre)*.
`outils/impact_tous_les_noms.py` a rendu **6 009 « résolutions franches »** — des
dossiers sans NEQ dont le nom détecté s'apparie EXACTEMENT à un nom de
`Nom.csv` ne menant qu'à un seul NEQ.

> ⚠️ **6 009 ne peut pas coexister avec 805 retenus**, et le rejeu complet du 16
> septembre a rendu 805 / 3 244 / 4 733 / 149 **chiffre pour chiffre.**

**Ce que la lecture du code établit, et qui explique la contradiction sans la
résoudre** : `impact_tous_les_noms` compare `Nom.csv` — **l'archive sur disque** —
aux dossiers du produit. *Il ne consulte JAMAIS `req_noms`.* **Il ne peut donc
pas distinguer un nom déjà indexé le 16 septembre d'un nom qui manquerait
encore.** Son 6 009 est un **plafond d'appariement exact**, pas un gain
incrémental.

## Ce que cet outil mesure, et il le mesure contre le MIROIR

La chaîne entière, maillon par maillon — *et chaque chute nomme son mécanisme* :

```
   1. le nom est-il AU MIROIR (req_entries ∪ req_noms)?      ← manque à l'import
   2. combien de NEQ DISTINCTS portent cette forme?          ← ambiguïté du nom
   3. le NEQ est-il DANS LE LOT que la récupération rend?     ← LA BORNE
   4. que décide le moteur (seuil 92, écart 8)?               ← les échelles
```

⚠️ **Le premier chiffre est celui qui tranche la question d'Alexandre.** *S'il
est proche de 6 009, les noms sont déjà en base et le 6 009 n'est pas un gain
neuf — c'est le même mur, vu depuis l'import.* **S'il est très inférieur, il
manque vraiment des noms au miroir, et cette correction-là passe devant l'index
par mots.**

⚠️ **DEUX CORRECTIONS À NE PAS MÉLANGER** *(Alexandre, 2026-09-17)*. « Garder
tous les noms à l'import » et « changer la clé de récupération » sont deux
corrections distinctes, sur deux mécanismes distincts, avec deux coûts
distincts. *Chiffrer l'une en croyant chiffrer l'autre ferait décider sur le
mauvais chiffre.* **Cet outil ne mesure que la seconde moitié de la chaîne —
celle qui vit dans le miroir.**

⚠️ **Aucune écriture, aucune règle modifiée** — seuil 92, écart 8, borne 2 000.

Usage, SUR L'HÔTE :
    python3 -m outils.chaine_du_nom_exact
"""
from __future__ import annotations

import argparse
from collections import Counter

from outils.nombres import milliers


def _part(k: int, n: int) -> str:
    return f"{100 * k / n:.1f} %" if n else "—"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--limite", type=int, default=None, help="borner (mise au point)")
    parser.add_argument("--exemples", type=int, default=6)
    args = parser.parse_args(argv)

    from sqlalchemy import select

    from falkye.db import refuser_si_cible_non_choisie

    code = refuser_si_cible_non_choisie()
    if code:
        return code

    from falkye.db import get_session
    from falkye.models.company import Company
    from falkye.models.req_entry import REQEntry
    from falkye.models.req_nom import REQNom
    from falkye.resolution import FAMILLES, famille_de
    from falkye.sources import req as req_source
    from falkye.sources.column_mapping import normaliser

    print("=" * 78)
    print("LA CHAÎNE DU NOM EXACT — où casse-t-elle?")
    print("=" * 78)
    print(f"""
⚠️ CE QUE CETTE MESURE NE DIRA PAS — à lire avant tout chiffre

   ELLE NE MESURE PAS L'IMPORT. `impact_tous_les_noms.py` compare `Nom.csv`
   sur disque aux dossiers du produit et ne consulte jamais `req_noms` : son
   6 009 est un PLAFOND d'appariement exact, pas un gain incrémental.
   Cet outil-ci part du MIROIR — donc de ce que le moteur peut réellement voir.

   ⚠️ « Garder tous les noms à l'import » et « changer la clé de récupération »
   sont DEUX corrections distinctes. Chiffrer l'une en croyant chiffrer
   l'autre ferait décider sur le mauvais chiffre.

   ET UN APPARIEMENT EXACT N'EST PAS UN APPARIEMENT JUSTE. Deux entreprises
   distinctes peuvent porter le même nom — c'est le maillon 2, et il se
   compte, pas se suppose.

   Aucune écriture. Seuil 92, écart 8, borne {req_source.LIMITE_CANDIDATS_PAR_NOM}.
""")

    session = get_session()
    try:
        requete = select(Company).where(Company.neq.is_(None)).order_by(Company.id)
        if args.limite:
            requete = requete.limit(args.limite)
        orphelins = list(session.execute(requete).scalars().all())
        total = len(orphelins)
        print(f"   dossiers sans NEQ : {milliers(total)}\n")

        maillons: Counter = Counter()
        par_table: Counter = Counter()
        familles_au_bout: Counter = Counter()
        exemples: dict[str, list[str]] = {"borne": [], "echelles": [], "absent": []}

        for i, company in enumerate(orphelins):
            if i and i % 1000 == 0:
                print(f"   … {milliers(i)} examinés", flush=True)
            forme = normaliser(company.nom_detecte or "")
            if not forme:
                maillons["forme normalisée vide"] += 1
                continue

            # ---- maillon 1 : le nom est-il AU MIROIR? ------------------------
            neqs_elus = set(session.execute(
                select(REQEntry.neq).where(REQEntry.nom_normalise == forme)
            ).scalars().all())
            neqs_autres = set(session.execute(
                select(REQNom.neq).where(REQNom.nom_normalise == forme)
            ).scalars().all())
            neqs = neqs_elus | neqs_autres
            if not neqs:
                maillons["1 ⛔ le nom n'est PAS au miroir"] += 1
                if len(exemples["absent"]) < args.exemples:
                    exemples["absent"].append(f"#{company.id} {forme!r}")
                continue
            if neqs_elus and neqs_autres:
                par_table["les deux tables"] += 1
            elif neqs_elus:
                par_table["req_entries (dénomination élue)"] += 1
            else:
                par_table["req_noms (autre nom) — le pont du 15 septembre"] += 1

            # ---- maillon 2 : combien de NEQ portent cette forme? -------------
            if len(neqs) > 1:
                maillons["2 ⛔ le nom mène à PLUSIEURS NEQ"] += 1
                continue
            (neq,) = tuple(neqs)

            # ---- maillon 3 : le NEQ est-il DANS LE LOT? ----------------------
            # ⚠️ La VRAIE récupération, empruntée — une requête recopiée
            # mesurerait sa propre copie.
            lot = {c.neq for c in req_source.candidats_par_nom(session, forme)}
            if neq not in lot:
                maillons["3 ⛔ LE NEQ N'EST PAS DANS LE LOT — la borne"] += 1
                if len(exemples["borne"]) < args.exemples:
                    exemples["borne"].append(
                        f"#{company.id} {forme[:44]!r} → {neq} absent du lot "
                        f"({milliers(len(lot))} candidats)"
                    )
                continue

            # ---- maillon 4 : que décide le moteur? ---------------------------
            matches = req_source.resolve_neq_by_name(
                session, company.nom_detecte, ville=company.ville
            )
            famille = famille_de(matches)
            familles_au_bout[famille] += 1
            if famille == "RETENU":
                maillons["4 ✓ RETENU — la chaîne tient"] += 1
            else:
                maillons["4 ⛔ présenté, mais REFUSÉ par les échelles"] += 1
                if len(exemples["echelles"]) < args.exemples:
                    haut = matches[0].score if matches else 0.0
                    second = matches[1].score if len(matches) > 1 else 0.0
                    exemples["echelles"].append(
                        f"#{company.id} {forme[:38]!r} → {famille}  "
                        f"top {haut:.1f}, 2e {second:.1f}"
                    )

        # ---- LE TABLEAU DE LA CHAÎNE ----------------------------------------
        print("\n" + "=" * 78)
        print("LA CHAÎNE, MAILLON PAR MAILLON")
        print("=" * 78 + "\n")
        ordre = (
            "forme normalisée vide",
            "1 ⛔ le nom n'est PAS au miroir",
            "2 ⛔ le nom mène à PLUSIEURS NEQ",
            "3 ⛔ LE NEQ N'EST PAS DANS LE LOT — la borne",
            "4 ⛔ présenté, mais REFUSÉ par les échelles",
            "4 ✓ RETENU — la chaîne tient",
        )
        for cle in ordre:
            k = maillons.get(cle, 0)
            print(f"   {cle:<48} {milliers(k):>9} {_part(k, total):>8}")

        au_miroir = total - maillons.get("1 ⛔ le nom n'est PAS au miroir", 0) \
            - maillons.get("forme normalisée vide", 0)
        franc = au_miroir - maillons.get("2 ⛔ le nom mène à PLUSIEURS NEQ", 0)
        print(f"\n   ⇒ nom EXACTEMENT présent au miroir : {milliers(au_miroir)}")
        print(f"   ⇒ dont menant à UN SEUL NEQ        : {milliers(franc)}"
              f"   ← à comparer au 6 009 de `impact_tous_les_noms`")
        print("""
   ⚠️ COMMENT SE LIT CETTE COMPARAISON

      Proche de 6 009  → les noms sont DÉJÀ en base. Le 6 009 n'est pas un
                         gain neuf : c'est le même mur, vu depuis l'import,
                         et il ne passe pas devant l'index par mots.
      Très inférieur   → il manque vraiment des noms au miroir, et CETTE
                         correction-là passe devant tout le reste.
""")
        if par_table:
            print(f"   {'où le nom vit, au miroir':<48} {'dossiers':>9}")
            for cle, k in par_table.most_common():
                print(f"   {cle:<48} {milliers(k):>9}")

        if familles_au_bout:
            print(f"\n   {'ce que le moteur décide, une fois PRÉSENTÉ':<48} {'dossiers':>9}")
            for f in FAMILLES:
                k = familles_au_bout.get(f, 0)
                print(f"   {f:<48} {milliers(k):>9}")

        for titre, cle in (
            ("LE NEQ EXISTE ET N'EST PAS DANS LE LOT — la borne", "borne"),
            ("PRÉSENTÉ ET REFUSÉ PAR LES ÉCHELLES", "echelles"),
            ("LE NOM N'EST PAS AU MIROIR", "absent"),
        ):
            if exemples[cle]:
                print(f"\n   {titre} :")
                for ligne in exemples[cle]:
                    print(f"      {ligne}")

        print("\n" + "=" * 78)
        print("   CE QUE CE CHIFFRE NE DIT PAS : qu'un appariement exact soit JUSTE.")
        print("   Deux entreprises distinctes peuvent porter le même nom.")
        print("=" * 78)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
