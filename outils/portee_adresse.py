#!/usr/bin/env python3
"""Qui porte une adresse, des deux côtés — et sous quelle forme?

**LE PRÉALABLE, ET IL EST OBLIGATOIRE.** *Mesurer un appariement par adresse
contre un champ vide reproduirait la série d'hypothèses tombées du 14 au 16
septembre, où le second terme de la comparaison n'existait pas.* **Cet outil ne
mesure AUCUN appariement.** Il établit seulement si les deux termes existent.

⚠️ **Le défaut qui rend ce préalable nécessaire, vérifié au code le
2026-09-16.** `falkye/sources/eimt.py` construit son `RawSignal` ainsi :

    yield RawSignal(
        nom_entreprise=employeur,
        …
        champs={"adresse": row.get(columns["adresse"]), …},
    )

**L'adresse est capturée dans `champs` et n'est JAMAIS promue en
`RawSignal.adresse`** — le paramètre existe pourtant (`falkye/sources/base.py`).
*Donc `company.adresse` reste vide sur la source qui touche la plus grande part
de la base.* **Le champ existe, la donnée existe, et le pont entre les deux
n'existe pas.**

## Ce que l'outil établit, et rien de plus

1. **Côté produit** — combien de `Company` portent une `adresse`, en tout et
   **parmi les non résolues**, qui sont la population qu'on voudrait apparier.
2. **Côté produit, gisement caché** — combien de `Signal.champs` portent une
   adresse, **par source**. *C'est là que vit celle de l'EIMT.*
3. **Côté miroir** — combien d'entrées REQ portent une adresse, et combien
   d'établissements.
4. ⚠️ **LA FORME** — un échantillon brut de chaque côté, **côte à côte**. *Deux
   taux de remplissage élevés ne disent pas que les deux chaînes se comparent :
   « 123 rue Principale, Bureau 200 » et « 123 RUE PRINCIPALE » sont deux
   remplissages et un seul appariement.* **C'est ce que la normalisation devra
   franchir, et personne ne l'a regardé.**

⚠️ **PORTÉE : lecture seule.** N'écrit rien, ne promeut rien, ne normalise rien.

Usage, SUR L'HÔTE :
    python3 -m outils.portee_adresse
    python3 -m outils.portee_adresse --exemples 15
"""
from __future__ import annotations

import argparse
from collections import Counter

from outils.nombres import milliers


def _part(n: int, total: int) -> str:
    return f"{100 * n / total:.1f} %" if total else "—"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--exemples", type=int, default=8)
    args = parser.parse_args(argv)

    from sqlalchemy import func, select

    from falkye.db import refuser_si_cible_non_choisie

    code = refuser_si_cible_non_choisie()
    if code:
        return code

    from falkye.db import get_session
    from falkye.models.company import Company
    from falkye.models.req_entry import REQEntry
    from falkye.models.signal import Signal

    print("=" * 78)
    print("LE PRÉALABLE DE L'ADRESSE — qui en porte une, et sous quelle forme")
    print("=" * 78)
    print("\n⚠️ PÉRIMÈTRE : cet outil n'apparie RIEN et ne mesure aucun rendement.")
    print("   Il établit seulement si les deux termes de la comparaison existent.")
    print("   Un appariement mesuré contre un champ vide rendrait zéro, et ce zéro")
    print("   se lirait comme « l'adresse ne sert à rien ».")
    print("\n   Il ne couvre pas les entités PUBLIQUES (D27 ⬜, D28 ⬜) ni les")
    print("   donneurs d'ouvrage (D43 ⬜) — ils n'existent pas comme entité.\n")

    session = get_session()
    try:
        # --- 1. Côté produit -------------------------------------------------
        print("-" * 78)
        print("1. CÔTÉ PRODUIT — la colonne `Company.adresse`")
        print("-" * 78)
        total = session.execute(select(func.count()).select_from(Company)).scalar() or 0
        avec = session.execute(
            select(func.count()).select_from(Company).where(Company.adresse.is_not(None))
        ).scalar() or 0
        sans_neq = session.execute(
            select(func.count()).select_from(Company).where(Company.neq.is_(None))
        ).scalar() or 0
        sans_neq_avec = session.execute(
            select(func.count()).select_from(Company)
            .where(Company.neq.is_(None), Company.adresse.is_not(None))
        ).scalar() or 0
        print(f"\n   dossiers              : {milliers(total)}")
        print(f"   avec une adresse      : {milliers(avec)}  ({_part(avec, total)})")
        print(f"\n   dossiers SANS NEQ     : {milliers(sans_neq)}   ← la population à apparier")
        print(f"   dont avec une adresse : {milliers(sans_neq_avec)}  ({_part(sans_neq_avec, sans_neq)})")
        if sans_neq and not sans_neq_avec:
            print("\n   ⛔ AUCUNE des entreprises à apparier ne porte d'adresse.")
            print("      Toute mesure d'appariement par adresse rendrait zéro, et ce")
            print("      zéro ne dirait rien de l'adresse — seulement du champ.")

        # --- 2. Le gisement caché --------------------------------------------
        print("\n" + "-" * 78)
        print("2. CÔTÉ PRODUIT, GISEMENT CACHÉ — l'adresse dans `Signal.champs`")
        print("-" * 78)
        print("\n   ⚠️ C'est là que vit celle de l'EIMT : capturée, jamais promue.\n")
        par_source: Counter = Counter()
        avec_adresse: Counter = Counter()
        formes: dict[str, list[str]] = {}
        for signal in session.execute(
            select(Signal).execution_options(yield_per=2000)
        ).scalars():
            sid = signal.source_id or "(sans source)"
            par_source[sid] += 1
            champs = signal.champs or {}
            valeur = champs.get("adresse") or champs.get("address")
            if valeur:
                avec_adresse[sid] += 1
                formes.setdefault(sid, [])
                if len(formes[sid]) < args.exemples:
                    formes[sid].append(str(valeur))
        for sid, n in par_source.most_common():
            k = avec_adresse.get(sid, 0)
            marque = "  ←" if k and not sans_neq_avec else ""
            print(f"   {sid:<28} {milliers(n):>9}  avec adresse {milliers(k):>9}"
                  f"  ({_part(k, n)}){marque}")

        # --- 3. Côté miroir ---------------------------------------------------
        print("\n" + "-" * 78)
        print("3. CÔTÉ MIROIR — l'adresse du registre")
        print("-" * 78)
        req_total = session.execute(select(func.count()).select_from(REQEntry)).scalar() or 0
        req_adr = session.execute(
            select(func.count()).select_from(REQEntry).where(REQEntry.adresse.is_not(None))
        ).scalar() or 0
        print(f"\n   entrées REQ           : {milliers(req_total)}")
        print(f"   avec une adresse      : {milliers(req_adr)}  ({_part(req_adr, req_total)})")

        # --- 4. LA FORME ------------------------------------------------------
        print("\n" + "=" * 78)
        print("4. ⚠️ LA FORME — ce que la normalisation devra franchir")
        print("=" * 78)
        print("\n   Deux taux de remplissage élevés ne disent PAS que les deux chaînes")
        print("   se comparent. C'est la seule chose qu'un taux ne montre jamais.\n")
        print("   CÔTÉ PRODUIT (Signal.champs) :")
        montres = 0
        for sid, exemples in formes.items():
            for ex in exemples[:3]:
                print(f"      [{sid}] {ex!r}")
                montres += 1
                if montres >= args.exemples:
                    break
            if montres >= args.exemples:
                break
        if not montres:
            print("      (aucune adresse trouvée dans les signaux)")
        print("\n   CÔTÉ MIROIR (REQEntry.adresse) :")
        echantillon = session.execute(
            select(REQEntry.adresse, REQEntry.ville)
            .where(REQEntry.adresse.is_not(None))
            .order_by(REQEntry.neq)
            .limit(args.exemples)
        ).all()
        for adresse, ville in echantillon:
            print(f"      {adresse!r}  ville={ville!r}")
        if not echantillon:
            print("      (aucune adresse dans le miroir)")

        print("\n" + "=" * 78)
        print("   CE QUE CET OUTIL NE DIT PAS : combien s'apparieraient.")
        print("   Cette mesure-là vient APRÈS, et seulement si les deux termes")
        print("   existent des deux côtés.")
        print("=" * 78)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
