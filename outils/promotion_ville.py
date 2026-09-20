#!/usr/bin/env python3
"""Promouvoir la ville de `Signal.champs` vers le dossier — du code, pas une échelle.

**Le fait qui écrit cet outil** *(mesuré le 17 septembre, `outils/departage_par_ville.py`)*.
L'EIMT capte une adresse sur **14 105 signaux, 100 %**, et ne la promeut jamais
en `RawSignal.adresse` *(`falkye/sources/eimt.py`)*. **2 484 dossiers ambigus
portent donc une ville que le moteur n'a jamais vue** — alors qu'il ajoute déjà
`+5` quand elle concorde *(`resolve_neq_by_name`)*.

> **Il ne s'agit pas de changer une règle. Il s'agit de donner au moteur ce
> qu'il ne voit pas.**

## ⚠️ Ce que ce geste NE FAIT PAS, et il faut le lire avant le reste

**Promouvoir la ville ne résout AUCUN dossier par lui-même.** *Une résolution
réussie n'écrit jamais dans le dossier qui a échoué* — c'est le défaut de fond
du chantier. **Les 1 111 départages mesurés ne se matérialisent que si la passe
de reprise tourne APRÈS cette promotion**, et ses chiffres d'aujourd'hui (705)
auront changé d'ici là.

⚠️ **L'ordre des deux gestes n'est donc pas indifférent** : *promouvoir d'abord,
re-mesurer la passe ensuite.* **Appliquer la passe sur les 705 puis promouvoir
oblige à refaire la passe.**

**Et une ville qui concorde ne prouve pas l'identité.** *Un départage ÉCARTE un
candidat; il n'en confirme aucun.* **Le total n'autorise aucune écriture — les
paires se regardent une à une** *(`--comparer N --depuis K`)*.

## Les trois gardes

1. **Le rapport est le mode par défaut.** Écrire demande `--appliquer`.
2. **On ne remplit que ce qui est VIDE** — `company.ville is None`. *Donc une
   seconde exécution ne fait rien : le geste est idempotent par construction, et
   il n'écrase jamais une ville posée par une source.*
3. **Un instantané JSON est écrit AVANT le commit**, et `--defaire` le rejoue à
   l'envers. ⚠️ *Sans commande pour défaire, « réversible » reste une intention.*

⚠️ **Un dossier dont les signaux se CONTREDISENT est refusé, pas départagé.**
*Deux signaux qui nomment deux villes ne se tranchent pas par un ordre de tri* —
même discipline que le refus au-delà de deux prétendants.

Usage, SUR L'HÔTE :
    python3 -m outils.promotion_ville                         # rapport seul
    python3 -m outils.promotion_ville --comparer 50           # les 50 premières paires
    python3 -m outils.promotion_ville --comparer 50 --depuis 50   # les 50 suivantes
    python3 -m outils.promotion_ville --appliquer
    python3 -m outils.promotion_ville --defaire /var/lib/falkye/promotion-ville-….json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from outils import pose_du_neq

from outils.nombres import milliers
from outils.villes_des_signaux import villes_des_signaux

#: Où l'instantané d'avant est déposé — le seul répertoire que les unités
#: peuvent écrire (`ReadWritePaths=/var/lib/falkye`).
#: ⚠️ **Empruntée à `outils/pose_du_neq.py`, plus recopiée** — elle y vit
#: près du geste qu'elle gouverne. *Le nom est conservé ici pour les
#: appelants.*
DOSSIER_INSTANTANE = pose_du_neq.DOSSIER_INSTANTANE


def _part(k: int, n: int) -> str:
    return f"{100 * k / n:.1f} %" if n else "—"


def _defaire(session, chemin: Path) -> int:
    """Rejoue l'instantané à l'envers. **Et refuse de toucher ce qui a bougé
    depuis** : une ville différente de celle qu'on avait posée appartient à
    quelqu'un d'autre, et la défaire serait écraser un tiers."""
    from falkye.models.company import Company

    contenu = json.loads(chemin.read_text(encoding="utf-8"))
    promues = contenu.get("promues", [])
    print(f"   instantané : {chemin}")
    print(f"   villes promues à défaire : {milliers(len(promues))}\n")
    defaites = ignorees = introuvables = 0
    for p in promues:
        company = session.get(Company, p["company_id"])
        if company is None:
            introuvables += 1
            continue
        if company.ville != p["ville_posee"]:
            ignorees += 1
            continue
        company.ville = p["ville_avant"]
        defaites += 1
    session.commit()
    print(f"   défaites     : {milliers(defaites)}")
    print(f"   ignorées     : {milliers(ignorees)}   (la ville a changé depuis — "
          f"elle n'est plus la nôtre)")
    if introuvables:
        print(f"   introuvables : {milliers(introuvables)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--appliquer", action="store_true",
                        help="ÉCRIRE (défaut : rapport seul, aucune écriture)")
    parser.add_argument("--comparer", type=int, default=0, metavar="N",
                        help="montrer N paires « adresse du signal / ville extraite »")
    parser.add_argument("--depuis", type=int, default=0, metavar="K",
                        help="commencer à la K-ième paire — pour les regarder PAR LOT")
    parser.add_argument("--defaire", default=None, metavar="FICHIER",
                        help="rejouer un instantané à l'envers")
    parser.add_argument("--sans-familles", action="store_true",
                        help="sauter la ventilation par famille (coûteuse)")
    parser.add_argument("--limite", type=int, default=None, help="borner (mise au point)")
    parser.add_argument("--instantane", default=str(DOSSIER_INSTANTANE))
    args = parser.parse_args(argv)

    from sqlalchemy import select

    from falkye.db import refuser_si_cible_non_choisie

    code = refuser_si_cible_non_choisie()
    if code:
        return code

    from falkye.db import get_session
    from falkye.models.company import Company

    session = get_session()
    try:
        if args.defaire:
            print("=" * 78)
            print("DÉFAIRE UNE PROMOTION DE VILLE")
            print("=" * 78 + "\n")
            return _defaire(session, Path(args.defaire))

        print("=" * 78)
        print("PROMOTION DE LA VILLE — de `Signal.champs` vers le dossier")
        print("=" * 78)
        print("\nMODE  :", "⚠️ ÉCRITURE" if args.appliquer else
              "rapport seul, aucune écriture")
        print("RÈGLE : on ne remplit que ce qui est VIDE. Jamais d'écrasement.")
        print("""
⚠️ CE QUE CE GESTE NE FAIT PAS — à lire avant les chiffres

   IL NE RÉSOUT AUCUN DOSSIER. Une résolution réussie n'écrit jamais dans le
   dossier qui a échoué : les départages mesurés ne se matérialisent que si la
   PASSE DE REPRISE tourne APRÈS. Promouvoir d'abord, re-mesurer la passe
   ensuite — l'inverse oblige à refaire la passe.

   UNE VILLE QUI CONCORDE NE PROUVE PAS L'IDENTITÉ. Un départage écarte un
   candidat; il n'en confirme aucun.

   ET LA VILLE DU REGISTRE EST SALE (`ville='LOCAL RC27'`). Ce geste ne la
   nettoie pas — il ajoute celle du produit, qui a ses propres défauts.
""")
        requete = (
            select(Company)
            .where(Company.neq.is_(None), Company.ville.is_(None))
            .order_by(Company.id)
        )
        if args.limite:
            requete = requete.limit(args.limite)
        sans_ville = list(session.execute(requete).scalars().all())
        trouvees = villes_des_signaux(session, {c.id for c in sans_ville})

        promouvables = [c for c in sans_ville
                        if c.id in trouvees and not trouvees[c.id].contradictoire]
        refuses = [c for c in sans_ville
                   if c.id in trouvees and trouvees[c.id].contradictoire]

        print("-" * 78)
        print("1. LE GISEMENT")
        print("-" * 78)
        print(f"\n   dossiers sans NEQ ET sans ville : {milliers(len(sans_ville))}")
        print(f"   dont une ville existe au signal : {milliers(len(trouvees))}"
              f"  ({_part(len(trouvees), len(sans_ville))})")
        print(f"\n   ⇒ À PROMOUVOIR                  : {milliers(len(promouvables))}")
        print(f"   ⛔ REFUSÉS — signaux contradictoires : {milliers(len(refuses))}")
        if refuses:
            print("      *Deux signaux qui nomment deux villes ne se tranchent pas par")
            print("      un ordre de tri.* Ils restent sans ville, et se regardent à la")
            print("      main. Quelques-uns :")
            for c in refuses[:5]:
                print(f"         #{c.id} {(c.nom_detecte or '')[:38]:<40} "
                      f"{list(trouvees[c.id].variantes)[:3]}")

        par_provenance: Counter = Counter(
            trouvees[c.id].provenance for c in promouvables
        )
        par_source: Counter = Counter(trouvees[c.id].source_id for c in promouvables)
        print(f"\n   {'provenance':<34} {'dossiers':>9}")
        for cle, k in par_provenance.most_common():
            print(f"   {cle:<34} {milliers(k):>9}")
        print(f"\n   {'source':<34} {'dossiers':>9}")
        for cle, k in par_source.most_common(8):
            print(f"   {cle:<34} {milliers(k):>9}")

        # ---- 2. CE QU'ON AUTORISE, VENTILÉ PAR FAMILLE ----------------------
        if not args.sans_familles:
            print("\n" + "-" * 78)
            print("2. CE QU'ON AUTORISE — ventilé par famille, AVANT promotion")
            print("-" * 78)
            print("\n   ⚠️ Seule la part AMBIGUË a été mesurée pour son effet de départage")
            print("      (1 111 sur 3 244, le 17 septembre). *Le reste est promu aussi —")
            print("      c'est une correction de données, pas un correctif ciblé — mais")
            print("      son rendement n'est pas mesuré.*\n")
            from falkye.resolution import FAMILLES, famille_de
            from falkye.sources import req as req_source

            familles: Counter = Counter()
            for i, company in enumerate(promouvables):
                if i and i % 500 == 0:
                    print(f"   … {milliers(i)} examinés", flush=True)
                familles[famille_de(req_source.resolve_neq_by_name(
                    session, company.nom_detecte, ville=None
                ))] += 1
            print(f"   {'famille':<18} {'dossiers':>9} {'part':>8}")
            for f in FAMILLES:
                k = familles.get(f, 0)
                print(f"   {f:<18} {milliers(k):>9} "
                      f"{_part(k, len(promouvables)):>8}")

        # ---- 3. LES PAIRES, PAR LOT -----------------------------------------
        print("\n" + "-" * 78)
        print(f"3. LES PAIRES À REGARDER — {milliers(len(promouvables))} en tout")
        print("-" * 78)
        if not args.comparer:
            print("\n   `--comparer N --depuis K` les montre PAR LOT.")
            print(f"   Pour tout voir par lots de 50 : "
                  f"--depuis 0, 50, 100 … {50 * (len(promouvables) // 50)}")
        else:
            lot = promouvables[args.depuis: args.depuis + args.comparer]
            print(f"\n   paires {args.depuis + 1} à {args.depuis + len(lot)} "
                  f"sur {milliers(len(promouvables))}\n")
            print("   ⚠️ Ce qui se vérifie ici est l'EXTRACTION, pas l'appariement :")
            print("      la tête de l'adresse est-elle bien une municipalité?\n")
            for c in lot:
                v = trouvees[c.id]
                print(f"   #{c.id}  {(c.nom_detecte or '')[:52]}")
                print(f"      {v.provenance}  [{v.source_id}]")
                print(f"      ville extraite : {v.ville!r}")
                print()

        if not args.appliquer:
            print("=" * 78)
            print("   RAPPORT SEUL — rien n'a été écrit.")
            print("   Relancer avec --appliquer pour promouvoir les villes.")
            print("=" * 78)
            return 0

        if not promouvables:
            print("\n   Rien à appliquer.")
            return 0

        # ---- L'INSTANTANÉ, AVANT LE COMMIT ----------------------------------
        horodatage = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        dossier = Path(args.instantane)
        try:
            dossier.mkdir(parents=True, exist_ok=True)
            chemin = dossier / f"promotion-ville-{horodatage}.json"
            chemin.write_text(json.dumps({
                "promues": [
                    {
                        "company_id": c.id,
                        "nom_detecte": c.nom_detecte,
                        "ville_avant": None,
                        "ville_posee": trouvees[c.id].ville,
                        "provenance": trouvees[c.id].provenance,
                        "source_id": trouvees[c.id].source_id,
                    }
                    for c in promouvables
                ],
                "refuses_contradictoires": [c.id for c in refuses],
            }, ensure_ascii=False, indent=1), encoding="utf-8")
        except OSError as exc:
            print(f"\n⛔ REFUS : l'instantané ne peut pas être écrit ({exc}).\n"
                  "   Rien n'a été modifié. Un geste sans trace de l'état d'avant\n"
                  "   n'est pas un geste réversible.", file=sys.stderr)
            return 3
        print(f"\n   instantané d'avant : {chemin}")

        promues = deja = 0
        for c in promouvables:
            company = session.get(Company, c.id)
            if company is None:
                continue
            # ⚠️ **RE-VÉRIFIÉ AU MOMENT D'ÉCRIRE**, pas seulement au moment de
            # décider. *Un cycle de production a pu poser une ville entre le
            # rapport et l'écriture, et on n'écrase jamais.*
            if company.ville:
                deja += 1
                continue
            company.ville = trouvees[c.id].ville
            promues += 1
        session.commit()
        print(f"\n   villes promues            : {milliers(promues)}")
        if deja:
            print(f"   déjà remplies entre-temps : {milliers(deja)}   (non écrasées)")
        print("\n" + "=" * 78)
        print(f"   Pour défaire : --defaire {chemin}")
        print("   ⚠️ Et RIEN n'est résolu par ce geste. La passe de reprise doit")
        print("      tourner ensuite, et ses chiffres auront changé.")
        print("=" * 78)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
