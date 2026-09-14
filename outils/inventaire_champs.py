"""L'inventaire des champs par source active — **le préalable du chantier 12**.

*« L'inventaire de champs par source active — approuvé mais jamais livré. C'est le
préalable : sans lui, le chantier reste au niveau de la source et ne trouve rien. »*
**Le 12 part d'une sphère et cherche, dans ce qu'on possède DÉJÀ, ce qui pourrait la
servir** — l'audit le démontre sur l'assurance, *déclarée sans source alors que six
champs déjà captés portent son déclencheur*. **Ce n'est pas « aucune source », c'est
« aucune source seule ».**

**Deux colonnes, et la seconde est celle qui sauve le chantier de lui-même.**

*Ce que le code DÉCLARE capter* — lu dans les connecteurs, par l'arbre syntaxique,
jamais recopié à la main : un connecteur a changé le 2026-09-13, et une liste recopiée
serait fausse au commit suivant sans que personne le voie.

*Ce que les données portent VRAIMENT* — taux de remplissage et nombre de valeurs
distinctes, mesurés sur les signaux en base. **Un champ déclaré n'est pas un champ
rempli** : `description_tender` était déclaré par le connecteur SEAO depuis toujours et
**vide dans 100 % des cas** *(mesuré le 2026-09-13 sur un fichier réel)*. Un inventaire
tiré du code seul aurait offert ce champ à une règle d'assurance, qui se serait bâtie
sur du vide.

**Trois écarts que le croisement fait apparaître, et chacun veut dire autre chose :**

    déclaré, jamais rempli   le connecteur écrit une clé que la source ne porte pas
    rempli, non déclaré      une clé arrive par une expansion (`**`) ou un chemin oublié
    déclaré, non ingéré      la source n'a produit aucun signal — absence de mesure

**Le nombre de valeurs distinctes sert le livrable 4** *(normaliser le texte libre déjà
capté, dont l'échec d'agrégation est documenté : 211 valeurs distinctes sur 311
notifications)*. **Un champ à presque autant de valeurs que de signaux est du texte
libre**, et l'inventaire le montre sans avoir à le déclarer.

**⚠️ Ce que cet outil NE FAIT PAS.** Il n'attribue aucune sphère à aucun champ. *Le
diagnostic à rebours est le livrable 2 du chantier 12, il demande une réfutation contre
l'historique réel (livrable 5), et ce garde-fou n'est opérationnel qu'avec le taux de
rejet du chantier 13.* **Proposer ici un lien champ → sphère produirait exactement ce
que la règle de réfutation existe pour empêcher : quelque chose de plausible.**

**Ce que ça coûte** : une lecture des signaux des sources visées. Sans base, l'outil
rend la première colonne seule — et le dit.

    python outils/inventaire_champs.py --sans-base     # le code seul, hors hôte
    python outils/inventaire_champs.py                 # les deux colonnes

Sur l'hôte, l'environnement d'abord :

    set -a; . /etc/falkye/falkye.env; set +a
"""
from __future__ import annotations

import argparse
import ast
import pathlib
import sys
from collections import Counter, defaultdict

RACINE = pathlib.Path(__file__).resolve().parents[1]

#: Les attributs de `RawSignal` qui portent une valeur du monde, pas de la mécanique.
#: `source_ref` et `signal_type_id` sont des identifiants du produit — les inventorier
#: ferait croire au chantier 12 qu'il a sous la main une matière qu'il n'a pas.
ATTRIBUTS_PORTEURS = (
    "neq", "adresse", "ville", "region", "secteur_activite", "site_web",
    "valeur_associee", "titre_ou_description",
)


def champs_declares(module: str) -> dict:
    """Ce qu'un connecteur déclare produire — lu dans l'ARBRE, pas par expression
    régulière.

    Une expression régulière sur `"clé":` attraperait aussi les dictionnaires
    voisins — les en-têtes d'inspection de zip, les tables de décodage. *L'arbre sait
    quel dictionnaire est passé à `champs=` et quel autre ne l'est pas.*
    """
    chemin = RACINE / (module.replace(".", "/") + ".py")
    if not chemin.exists():
        return {"erreur": f"module introuvable : {module}"}

    arbre = ast.parse(chemin.read_text(encoding="utf-8"))
    cles: set[str] = set()
    attributs: set[str] = set()
    dynamiques = False
    for noeud in ast.walk(arbre):
        if not (isinstance(noeud, ast.Call) and getattr(noeud.func, "id", None) == "RawSignal"):
            continue
        for mot in noeud.keywords:
            if mot.arg in ATTRIBUTS_PORTEURS:
                attributs.add(mot.arg)
            if mot.arg != "champs" or not isinstance(mot.value, ast.Dict):
                continue
            for cle in mot.value.keys:
                if cle is None:
                    # `**quelque_chose` : des clés que seul le RUN révèle. Le dire
                    # plutôt que de rendre une liste qu'on croirait complète.
                    dynamiques = True
                elif isinstance(cle, ast.Constant) and isinstance(cle.value, str):
                    cles.add(cle.value)
    return {"champs": sorted(cles), "attributs": sorted(attributs), "dynamiques": dynamiques}


def remplissage(db_session, source_id: str) -> dict:
    """Taux de remplissage et nombre de valeurs distinctes, par clé, pour une source."""
    from sqlalchemy import select

    from falkye.models.signal import Signal

    lignes = db_session.execute(
        select(Signal.champs, Signal.valeur_associee, Signal.titre_ou_description)
        .where(Signal.source_id == source_id)
    ).all()
    if not lignes:
        return {"signaux": 0, "par_cle": {}}

    remplis: Counter = Counter()
    valeurs: dict[str, set] = defaultdict(set)
    for champs, valeur, titre in lignes:
        paires = list((champs or {}).items())
        paires += [("valeur_associee", valeur), ("titre_ou_description", titre)]
        for cle, v in paires:
            if v is None or v == "" or v == [] or v == {}:
                continue
            remplis[cle] += 1
            valeurs[cle].add(str(v)[:200])
    return {
        "signaux": len(lignes),
        "par_cle": {
            cle: {"remplis": n, "distinctes": len(valeurs[cle])}
            for cle, n in sorted(remplis.items(), key=lambda kv: -kv[1])
        },
    }


def _afficher_source(source_id: str, declare: dict, mesure: dict | None) -> None:
    print(f"\n── {source_id} " + "─" * max(0, 58 - len(source_id)))
    if declare.get("erreur"):
        print(f"   {declare['erreur']}")
        return
    if declare["attributs"]:
        print(f"   promus au dossier : {', '.join(declare['attributs'])}")
    else:
        print("   promus au dossier : aucun")
    if declare["dynamiques"]:
        print("   ⚠ clés DYNAMIQUES (`**`) — la liste déclarée est incomplète par nature")

    if mesure is None:
        for cle in declare["champs"]:
            print(f"      {cle:38} déclaré")
        return

    n = mesure["signaux"]
    if not n:
        print("   aucun signal en base — absence de mesure, pas absence de champ")
        for cle in declare["champs"]:
            print(f"      {cle:38} déclaré, non ingéré")
        return

    print(f"   {n} signaux en base")
    vues = set(mesure["par_cle"])
    for cle in sorted(set(declare["champs"]) | vues):
        info = mesure["par_cle"].get(cle)
        if info is None:
            print(f"      {cle:38} ⚠ DÉCLARÉ, JAMAIS REMPLI")
            continue
        taux = 100 * info["remplis"] / n
        marque = "  " if cle in declare["champs"] else "+ "  # rempli, non déclaré
        libre = "  ← texte libre?" if info["distinctes"] > 0.8 * info["remplis"] > 8 else ""
        print(
            f"   {marque}{cle:38} {taux:5.1f} %   "
            f"{info['distinctes']:>5} valeur(s) distincte(s){libre}"
        )


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument(
        "--sans-base", action="store_true",
        help="rendre la colonne du CODE seule — utile hors de l'hôte, et l'outil le dit",
    )
    args = parseur.parse_args(argv)

    from falkye.registry.loader import get_registry

    registry = get_registry()
    sources = [s for s in registry.sources_actives() if s.connecteur]
    print(f"{len(sources)} source(s) active(s) portant un connecteur, lues au registre")

    session = None
    if not args.sans_base:
        from falkye.db import bases_sur_repli, cible_annoncee

        print(cible_annoncee())
        if bases_sur_repli():
            print(
                "\nREFUS — aucune cible n'a été choisie : "
                f"{', '.join(bases_sur_repli())} absente(s).\n"
                "  Un taux de remplissage de 0 % sur une base vide se lit comme un champ mort.\n"
                "  Relancer avec --sans-base pour la colonne du code seule,\n"
                "  ou sur l'hôte : set -a; . /etc/falkye/falkye.env; set +a",
                file=sys.stderr,
            )
            return 2
        from falkye.db import get_session

        session = get_session()

    try:
        for source in sources:
            declare = champs_declares(source.connecteur)
            mesure = None if session is None else remplissage(session, source.id)
            _afficher_source(source.id, declare, mesure)

        print("\n" + "─" * 64)
        if session is None:
            print(
                "COLONNE DU CODE SEULE — le taux de remplissage n'a pas été mesuré.\n"
                "  Un champ déclaré n'est pas un champ rempli : `description_tender` était\n"
                "  déclaré depuis toujours et vide dans 100 % des cas. **Ne pas bâtir un lien\n"
                "  champ → sphère sur cette sortie-ci.**"
            )
        else:
            print(
                "Légende : `+` = rempli mais NON déclaré (expansion `**` ou chemin oublié).\n"
                "  « DÉCLARÉ, JAMAIS REMPLI » = le connecteur écrit une clé que la source ne\n"
                "  porte pas. « déclaré, non ingéré » = aucune mesure, pas un champ mort."
            )
        print(
            "\n⚠ AUCUNE SPHÈRE N'EST ATTRIBUÉE ICI. Le diagnostic à rebours est le livrable 2\n"
            "  du chantier 12; il exige une réfutation contre l'historique réel (livrable 5),\n"
            "  opérationnelle seulement avec le taux de rejet du chantier 13. Proposer un lien\n"
            "  ici produirait exactement ce que la règle de réfutation existe pour empêcher."
        )
        return 0
    finally:
        if session is not None:
            session.close()


if __name__ == "__main__":
    sys.exit(main())
