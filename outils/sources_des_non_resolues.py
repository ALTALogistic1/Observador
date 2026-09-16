#!/usr/bin/env python3
"""D'où viennent les entreprises sans NEQ, et que leur source peut-elle contenir?

**L'hypothèse à réfuter** *(Alexandre, 2026-09-16, déclarée comme telle)* : **une
part des dossiers sans NEQ n'a pas de NEQ à trouver.** *Le REQ ne contient que
les entités immatriculées au Québec.* Une entreprise détectée par l'EIMT est un
employeur qui embauche un travailleur étranger — elle peut être fédérale,
extraprovinciale, ou immatriculée sous un nom que le Québec ne connaît pas. Une
entreprise vue par les contrats fédéraux peut n'avoir aucune existence
québécoise.

**Neuf hypothèses sont tombées sur ce mur, et toutes les neuf demandaient
POURQUOI LA COMPARAISON ÉCHOUE.** *Celle-ci demande s'il y a quelque chose à
comparer.* **Rien ne l'établit à ce jour, et elle peut tomber comme les neuf
autres.**

⚠️ **PORTÉE : mesure seule. Ne classe aucun dossier, ne filtre rien, ne purge
rien.** *Ce que la mesure suggérerait d'une population hors registre est une
DÉCISION DE PRODUIT, pas un correctif* — et elle revient à Alexandre.

## Le second terme se LIT au registre, il ne se déduit pas

⚠️ **Et le registre porte DEUX champs qu'il ne faut pas confondre** *(D41)* :

- **`territoire`** — le FILTRE réel, lu par `falkye/territoire.py::appartient`.
  *Quand il est `null`, `appartient()` RETIENT TOUT* — à dessein : « une valeur
  absente est retenue, jamais rejetée », sinon une source qui ne sait pas
  renseigner la région verrait tout son contenu disparaître.
- **`region`** — du **texte libre**, « région couverte ». *Il ne filtre rien.*

**Une source dont `region` dit « Québec » et dont `territoire` est `null` n'est
pas filtrée.** C'est le cas mesuré du SEAO, deux fois plutôt qu'une.

Usage, SUR L'HÔTE :
    sudo -u falkye bash -c 'set -a; . /etc/falkye/falkye.env; set +a; \
        cd /opt/falkye/code && \
        /opt/falkye/venv/bin/python -m outils.sources_des_non_resolues'
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from outils.nombres import milliers

RACINE = Path(__file__).resolve().parent.parent


def _registre() -> dict[str, dict]:
    """Ce que le registre DÉCLARE, lu tel quel. Jamais une déduction."""
    import yaml

    brut = yaml.safe_load((RACINE / "falkye" / "registry" / "sources.yaml").read_text(encoding="utf-8"))
    entrees = brut.get("sources", brut) if isinstance(brut, dict) else brut
    if isinstance(entrees, dict):
        entrees = [dict(v, id=k) for k, v in entrees.items()]
    return {str(e.get("id")): e for e in entrees}


def _part(n: int, total: int) -> str:
    return f"{100 * n / total:.1f} %" if total else "—"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--exemples", type=int, default=0,
                        help="montrer N dossiers par source (0 = aucun)")
    args = parser.parse_args(argv)

    from sqlalchemy import func, select

    from falkye.db import refuser_si_cible_non_choisie

    code = refuser_si_cible_non_choisie()
    if code:
        return code

    from falkye.db import get_session
    from falkye.models.company import Company
    from falkye.models.signal import Signal

    print("=" * 78)
    print("D'OÙ VIENNENT LES DOSSIERS SANS NEQ, ET QUE LEUR SOURCE PEUT CONTENIR")
    print("=" * 78)
    print("\n⚠️ PORTÉE : mesure seule. Elle ne CLASSE aucun dossier, ne filtre rien,")
    print("   ne purge rien. Elle borne ce qu'on peut espérer, pas ce qui est.\n")

    registre = _registre()
    session = get_session()
    try:
        orphelins = list(session.execute(
            select(Company.id).where(Company.neq.is_(None))
        ).scalars().all())
        total = len(orphelins)
        ensemble = set(orphelins)

        sources_par_dossier: dict[int, set[str]] = {}
        for company_id, source_id in session.execute(
            select(Signal.company_id, Signal.source_id).distinct()
        ).all():
            if company_id in ensemble:
                sources_par_dossier.setdefault(company_id, set()).add(source_id or "(sans source)")

        sans_signal = total - len(sources_par_dossier)
        par_source: Counter = Counter()
        for sources in sources_par_dossier.values():
            for s in sources:
                par_source[s] += 1
        multi = Counter(len(s) for s in sources_par_dossier.values())

        # --- 1. LA VENTILATION ------------------------------------------------
        print("-" * 78)
        print("1. LES DOSSIERS SANS NEQ, PAR SOURCE")
        print("-" * 78)
        print(f"\n   dossiers sans NEQ            : {milliers(total)}")
        print(f"   dont AUCUN signal rattaché   : {milliers(sans_signal)}")
        if sans_signal:
            print("      ⚠️ Un dossier sans signal n'a AUCUNE source, donc aucune")
            print("         ligne ci-dessous. Il échappe entièrement au croisement.")
        print(f"\n   dossiers portant PLUSIEURS sources :")
        for combien, n in sorted(multi.items()):
            etiquette = "1 source" if combien == 1 else f"{combien} sources"
            print(f"      {etiquette:<12} {milliers(n):>8} dossier(s)")
        if sum(par_source.values()) != len(sources_par_dossier):
            print("\n   ⚠️ LA SOMME DES COLONNES CI-DESSOUS DÉPASSE LE NOMBRE DE DOSSIERS.")
            print("      Un dossier à deux sources compte dans les deux. *Un total de")
            print("      colonnes n'est pas un total de dossiers* — et l'addition de")
            print("      pourcentages n'aurait aucun sens ici.")

        # --- 2. LE CROISEMENT AVEC LE REGISTRE --------------------------------
        print("\n" + "-" * 78)
        print("2. CE QUE CHAQUE SOURCE DÉCLARE — lu au registre, jamais déduit")
        print("-" * 78)
        print(f"\n   {'source':<24} {'dossiers':>9}  {'territoire (FILTRE)':<22} {'region (TEXTE)':<18} statut")
        print("   " + "-" * 92)
        for source_id, n in par_source.most_common():
            e = registre.get(source_id, {})
            terr = e.get("territoire")
            terr_txt = ", ".join(terr) if isinstance(terr, list) else ("AUCUN" if terr is None else str(terr))
            marque = "" if terr else "  ←"
            print(f"   {source_id:<24} {milliers(n):>9}  {terr_txt:<22} "
                  f"{str(e.get('region'))[:18]:<18} {str(e.get('statut'))}{marque}")
            if source_id not in registre:
                print("      ⚠️ SOURCE ABSENTE DU REGISTRE — rien de déclaré à croiser.")

        non_filtrees = sum(n for s, n in par_source.items()
                           if not registre.get(s, {}).get("territoire"))
        print(f"\n   ⚠️ dossiers venus d'une source SANS filtre territorial : "
              f"{milliers(non_filtrees)}  ({_part(non_filtrees, total)} des dossiers)")
        print("      `territoire: null` ⇒ `appartient()` RETIENT TOUT. C'est délibéré")
        print("      — « une valeur absente est retenue, jamais rejetée » — mais ça")
        print("      veut dire que rien n'a borné le territoire de ces dossiers.")

        # --- 3. CE QUE LA MESURE NE PEUT PAS DIRE -----------------------------
        print("\n" + "=" * 78)
        print("3. ⚠️ CE QUE CETTE MESURE NE PEUT PAS DIRE")
        print("=" * 78)
        print("""
   • Une source pancanadienne NE PROUVE PAS qu'un dossier est hors Québec.
     Elle dit qu'il PEUT l'être. La ventilation borne ce qu'on peut espérer;
     elle ne classe aucun dossier.

   • ⚠️ `territoire: ['Québec']` ne prouve pas l'inverse non plus. Pour l'EIMT,
     le filtre porte sur la PROVINCE DE L'EMPLOI, pas sur le lieu
     d'immatriculation de l'entreprise. *Un employeur qui embauche au Québec
     peut être constitué au fédéral ou ailleurs* — et c'est exactement la
     distinction sur laquelle porte l'hypothèse. Le registre ne peut pas y
     répondre.

   • `region` est du TEXTE LIBRE et ne filtre rien. Une source dont la region
     dit « Québec » avec `territoire: null` n'est pas filtrée — mesuré sur le
     SEAO, deux fois plutôt qu'une (journal, cas 40).

   • Elle ne dit rien des entités PUBLIQUES (D27 ⬜, D28 ⬜) ni des donneurs
     d'ouvrage, qui n'existent comme entité nulle part (D43 ⬜).

   • Et elle ne dit RIEN de ce qu'il faudrait faire. Une entreprise hors Québec
     dans un produit de portée québécoise est une DÉCISION DE PRODUIT, pas un
     correctif. Aucune valeur par défaut n'est posée ici.
""")
        if args.exemples:
            print("-" * 78)
            print(f"UN ÉCHANTILLON — {args.exemples} par source, par id croissant")
            print("-" * 78)
            print("\n   ⚠️ Par id croissant, donc reproductible — mais PAS représentatif.")
            print("      Un ordre de table promu en échantillon est le cas 19.\n")
            for source_id, _ in par_source.most_common():
                ids = sorted(i for i, s in sources_par_dossier.items() if source_id in s)
                print(f"   [{source_id}]")
                for company in session.execute(
                    select(Company).where(Company.id.in_(ids[: args.exemples]))
                ).scalars():
                    print(f"      #{company.id:<7} « {company.nom_detecte} »"
                          f"   {company.ville or '(sans ville)'}")
                print()
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
