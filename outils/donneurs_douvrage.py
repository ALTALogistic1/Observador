"""Qui sont les donneurs d'ouvrage que le produit voit passer — et il ne les classe pas.

**La question** *(Alexandre, 2026-09-13)* : *combien de donneurs d'ouvrage distincts
dans les données du SEAO, et de quels types?* **L'obligation de publier au SEAO ne
pèse que sur les organismes publics** — ministères, santé, éducation, municipalités —
*mais d'autres peuvent l'utiliser volontairement* : sociétés d'État à vocation
commerciale, OSBL, entreprises privées. **La population n'est donc pas homogène**, et
c'est exactement ce qui touche D27 à D29.

**⚠️ Cet outil COMPTE et NE CLASSE PAS, et c'est une décision, pas une limite
technique.** Trier ces noms en « public » et « privé » est précisément **D28**, une
décision ouverte — *la règle de classement doit avoir une réponse par défaut quand elle
ne tranche pas, sinon on remplace une ambiguïté de source par une ambiguïté d'entité.*
Un outil qui appliquerait ici une heuristique de noms *(« Ville de », « CISSS », «
Ministère »)* **produirait une classification qui aurait l'air d'une mesure**, et
personne ne saurait plus qu'elle a été devinée. *Charte, règle 5 : inventer la règle
serait prendre la décision que personne n'a prise.* **Le relevé sert à la préparer, pas
à la remplacer.**

**Ce que l'outil lit.** Le champ `donneur_ordre` des signaux — présent chez le SEAO,
les contrats fédéraux et la Nouvelle-Écosse. *Il vit dans `Signal.champs`, conservé
intégralement, et n'est jamais promu au dossier d'une entreprise : le donneur d'ouvrage
n'existe pas comme entité dans le produit.*

**Ce que ça coûte** : une lecture des signaux des sources visées (~2 000 lignes
facturées aujourd'hui). Il n'écrit rien.

    python outils/donneurs_douvrage.py
    python outils/donneurs_douvrage.py --source seao --top 40

Sur l'hôte, l'environnement d'abord :

    set -a; . /etc/falkye/falkye.env; set +a
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter

#: Les sources dont le connecteur écrit un `donneur_ordre`. Lue ici plutôt que
#: devinée : trois connecteurs le font, et un quatrième qui s'ajouterait sans
#: être inscrit ici serait invisible — d'où le compte de couverture ci-dessous,
#: qui le ferait voir.
SOURCES_AVEC_DONNEUR = ("seao", "contrats_federaux", "contrats_nouvelle_ecosse")


def releve(db_session, sources: list[str]) -> dict:
    from sqlalchemy import select

    from falkye.models.signal import Signal

    requete = select(Signal.source_id, Signal.champs, Signal.valeur_associee)
    if sources:
        requete = requete.where(Signal.source_id.in_(sources))

    par_source = Counter()
    avec_donneur = Counter()
    avec_montant = Counter()
    donneurs = Counter()
    for source_id, champs, valeur in db_session.execute(requete).all():
        par_source[source_id] += 1
        nom = (champs or {}).get("donneur_ordre")
        if nom and str(nom).strip():
            avec_donneur[source_id] += 1
            donneurs[str(nom).strip()] += 1
        if valeur is not None:
            avec_montant[source_id] += 1
    return {
        "par_source": par_source,
        "avec_donneur": avec_donneur,
        "avec_montant": avec_montant,
        "donneurs": donneurs,
    }


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--source", action="append", default=[], help="limiter à ces sources (répétable)")
    parseur.add_argument("--top", type=int, default=25, help="nombre de donneurs à afficher (défaut : 25)")
    args = parseur.parse_args(argv)

    from falkye.db import bases_sur_repli, cible_annoncee

    print(cible_annoncee())
    if bases_sur_repli():
        print(
            "\nREFUS — aucune cible n'a été choisie : "
            f"{', '.join(bases_sur_repli())} absente(s).\n"
            "  « Zéro donneur d'ouvrage » sur une base vide se lit comme un résultat.\n"
            "  Sur l'hôte : set -a; . /etc/falkye/falkye.env; set +a",
            file=sys.stderr,
        )
        return 2

    from falkye.db import get_session

    session = get_session()
    try:
        r = releve(session, args.source or list(SOURCES_AVEC_DONNEUR))
        total = sum(r["par_source"].values())
        if not total:
            print("\nAucun signal pour ces sources — absence de mesure, pas absence de donneurs.")
            return 0

        print(f"\n{'source':<28}{'signaux':>9}{'avec donneur':>14}{'avec montant':>14}")
        for source_id, n in r["par_source"].most_common():
            d, m = r["avec_donneur"][source_id], r["avec_montant"][source_id]
            print(
                f"{source_id:<28}{n:>9}{d:>9} ({100*d/n:3.0f}%){m:>9} ({100*m/n:3.0f}%)"
            )

        print(f"\ndonneurs d'ouvrage DISTINCTS : {len(r['donneurs'])}")
        print(f"(sur {sum(r['avec_donneur'].values())} signaux qui en portent un)\n")
        print(f"{'donneur d ouvrage':<58}{'signaux':>9}")
        for nom, n in r["donneurs"].most_common(args.top):
            print(f"{nom[:56]:<58}{n:>9}")
        restants = len(r["donneurs"]) - args.top
        if restants > 0:
            print(f"… et {restants} autres (--top pour en voir plus)")

        print(
            "\n⚠ AUCUN TYPE N'EST ATTRIBUÉ ICI, et c'est délibéré. Classer ces noms en\n"
            "  public/privé est la décision D28, ouverte — une heuristique de noms\n"
            "  rendrait une classification DEVINÉE avec l'apparence d'une mesure.\n"
            "  Ce relevé sert à préparer la règle, pas à la remplacer.\n\n"
            "  Et ce que ce compte ne dit pas : un donneur d'ouvrage n'existe pas comme\n"
            "  entité dans le produit. Il vit dans `Signal.champs`, jamais au dossier."
        )
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
