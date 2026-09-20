#!/usr/bin/env python3
"""L'adresse, de la source au dossier — **quatre états, et trois écarts.**

**Ce qui l'écrit** *(ventilation des restants, 2026-09-20)*. Les deux sources
québécoises surreprésentées chez les restants sont **celles qui ne portent
presque aucune adresse** :

```
source                   restants   rapport   ville   code post.
investissement_quebec         438      ×2.2    5,5 %       6,6 %
contrats_federaux             191      ×5.3    1,6 %       2,1 %
eimt                        3 053      ×0.9  100,0 %     100,0 %
```

**Elles ne résolvent pas mal parce qu'elles seraient pancanadiennes — le
départageur d'adresse n'a rien à lire chez elles.** *Et c'est exactement le motif
de l'EIMT : adresse captée à 100 % dans `Signal.champs`, jamais promue en
`RawSignal.adresse`. Il a fallu la promouvoir pour que la ville serve.*

## Les quatre états, et ce que chaque écart veut dire

| état | d'où il vient | l'écart avec le suivant |
|---|---|---|
| **déclaré** | `sources.yaml: champs_pertinents` | *déclaré et jamais lu* — une déclaration qui ne coûte rien |
| **lu par le connecteur** | **AST du module**, jamais une liste recopiée | *lu et jamais rangé* — le champ meurt dans le connecteur |
| **arrivé dans `Signal.champs`** | la base | ⚠️ *rangé et jamais promu* — **le motif EIMT** |
| **promu en `RawSignal.adresse`** | l'AST du connecteur | — |

⚠️ **Le seul écart qui se corrige en une ligne est le dernier.** *Les autres
demandent du travail de connecteur, ou n'ont pas de correctif du tout.*

## ⚠️ CE QUE CET OUTIL NE PEUT PAS ÉTABLIR

**Qu'une source ne PUBLIE pas d'adresse.** *Le dépôt contient ce que le
connecteur lit, pas ce que la source offre.* **Un champ absent des quatre
colonnes veut dire « personne ici ne le connaît » — jamais « la source ne l'a
pas ».**

*Une subvention fédérale n'a peut-être pas d'adresse d'entreprise à publier, et
alors la piste se ferme.* **Mais ça se vérifie en ouvrant la source**, comme
l'archive REQ a dû être ouverte pour trouver `DENOMN_SOC`. ⚠️ *Conclure
« la source ne l'a pas » depuis un connecteur muet, c'est classer un fichier sur
son nom.*

⚠️ **Et une déclaration n'est pas une observation** : `description_tender` était
déclaré par le connecteur SEAO **depuis toujours et vide dans 100 % des cas**.
*La colonne « déclaré » est donc une prétention qu'on confronte, pas une source
de vérité.*

⚠️ **AUCUNE ÉCRITURE. Les échelles ne bougent pas : seuil 92, écart 8.**

Usage, SUR L'HÔTE :
    python3 -m outils.adresse_par_connecteur
    python3 -m outils.adresse_par_connecteur --source investissement_quebec
    python3 -m outils.adresse_par_connecteur --exemples 5
"""
from __future__ import annotations

import argparse
import ast
import re
from collections import Counter, defaultdict
from pathlib import Path

from outils.nombres import milliers

#: Ce qui, dans un nom de champ, annonce une adresse. *Une observation des clés
#: rencontrées, pas une norme* — et volontairement large : **mieux vaut lister un
#: champ qui n'en est pas que taire celui qui l'est.**
INDICE_DADRESSE = re.compile(
    r"adresse|address|ville|city|municipal|localite|localité|locality|"
    r"code_?post|postal|zip|province|region|région|rue|street|lieu|emplacement",
    re.IGNORECASE,
)

#: Les emplacements de `RawSignal` qui portent une adresse PROMUE, et **ce qui
#: s'y range**. *Les seuls que le moteur lit ensuite — `champs` reste un sac que
#: personne n'interroge.*
EMPLACEMENTS = {
    "adresse": re.compile(r"adresse|address|rue|street|lieu|emplacement", re.I),
    "ville": re.compile(r"ville|city|municipal|localite|localité|locality", re.I),
    "region": re.compile(r"region|région|province", re.I),
}
CHAMPS_PROMUS = tuple(EMPLACEMENTS)

#: ⚠️ **`RawSignal` n'a AUCUN emplacement pour un code postal.** *Vérifié dans
#: `falkye/sources/base.py` : `adresse`, `ville`, `region` — et rien d'autre.*
#:
#: **Donc aucun connecteur ne PEUT en promouvoir un**, quelle que soit la source.
#: *Et le code postal complet est le niveau le plus FORT du départageur
#: d'adresse* — il ne fonctionne aujourd'hui que parce que le départageur va le
#: chercher lui-même dans `Signal.champs`, en fouillant le sac.
CE_QUI_NA_PAS_DEMPLACEMENT = re.compile(r"code_?post|postal|zip", re.I)

#: Où vivent les connecteurs.
DOSSIER_CONNECTEURS = Path(__file__).resolve().parent.parent / "falkye" / "sources"


def cles_lues_par_le_module(chemin: Path) -> set[str]:
    """Les clés que le module lit par `.get("…")` ou `…["…"]`, **par AST**.

    ⚠️ **Extraites du code, jamais recopiées dans une liste à côté.** *Une liste
    recopiée se désynchronise à la première clé ajoutée, et le garde-fou
    vérifierait alors sa propre copie* — même règle que
    `falkye/sources/req.py::colonnes_brutes_lues`, dont ceci est la forme
    généralisée.
    """
    try:
        arbre = ast.parse(chemin.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return set()
    cles: set[str] = set()
    for noeud in ast.walk(arbre):
        if (isinstance(noeud, ast.Call)
                and isinstance(noeud.func, ast.Attribute)
                and noeud.func.attr == "get"
                and noeud.args
                and isinstance(noeud.args[0], ast.Constant)
                and isinstance(noeud.args[0].value, str)):
            cles.add(noeud.args[0].value)
        elif (isinstance(noeud, ast.Subscript)
                and isinstance(noeud.slice, ast.Constant)
                and isinstance(noeud.slice.value, str)):
            cles.add(noeud.slice.value)
    return cles


def champs_promus_par_le_module(chemin: Path, champs=CHAMPS_PROMUS) -> set[str]:
    """Les champs que le module passe à `RawSignal(...)`.

    ⚠️ *Un `adresse=` dans un appel à autre chose que `RawSignal` ne compte
    pas* — sinon un `_CorporationResolue(adresse=…)` interne ferait croire à une
    promotion qui n'a pas lieu.

    ⚠️ **`champs` existe pour qu'un autre chiffrage demande d'autres
    emplacements PAR UN APPEL, jamais par une copie de ce lecteur.** *Le défaut
    est connu : un second lecteur d'arbre syntaxique diverge du premier sans que
    rien ne le dise.* **Le défaut de ce paramètre est celui de la production.**
    """
    try:
        arbre = ast.parse(chemin.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return set()
    promus: set[str] = set()
    for noeud in ast.walk(arbre):
        if not isinstance(noeud, ast.Call):
            continue
        nom = getattr(noeud.func, "id", None) or getattr(noeud.func, "attr", None)
        if nom != "RawSignal":
            continue
        for mot in noeud.keywords:
            if mot.arg in champs:
                # ⚠️ `adresse=None` n'est pas une promotion.
                if isinstance(mot.value, ast.Constant) and mot.value.value is None:
                    continue
                promus.add(mot.arg)
    return promus


def cles_du_sac_par_le_module(chemin: Path) -> set[str]:
    """Les clés que le module ÉCRIT dans `champs={…}` d'un `RawSignal`, **par AST.**

    ⚠️ **Ce n'est pas `cles_lues_par_le_module`, et les confondre fait vérifier
    la mauvaise chose.** *Celle-là relève ce que le connecteur LIT de son fichier
    source — `row.get("Occupation")`. Celle-ci relève ce qu'il DÉPOSE dans le sac
    — `champs={"profession": …}`.* **Une table qui déclare des clés de
    `Signal.champs` doit se recouper contre la seconde**; contre la première,
    elle passerait pour vérifiée sans l'être.

    *Seules les clés constantes d'un littéral de dictionnaire sont vues* — une
    clé calculée ne peut pas être relevée sans exécuter le code, et une garde
    qui prétendrait la voir mentirait.
    """
    try:
        arbre = ast.parse(chemin.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return set()
    cles: set[str] = set()
    for noeud in ast.walk(arbre):
        if not isinstance(noeud, ast.Call):
            continue
        nom = getattr(noeud.func, "id", None) or getattr(noeud.func, "attr", None)
        if nom != "RawSignal":
            continue
        for mot in noeud.keywords:
            if mot.arg == "champs" and isinstance(mot.value, ast.Dict):
                cles.update(
                    cle.value for cle in mot.value.keys
                    if isinstance(cle, ast.Constant) and isinstance(cle.value, str)
                )
    return cles


def _part(k: int, n: int) -> str:
    return f"{100 * k / n:.1f} %" if n else "—"


def _adresses(cles) -> set[str]:
    return {c for c in cles if INDICE_DADRESSE.search(c)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--source", action="append", default=None, metavar="ID",
                        help="se limiter à ces sources (répétable)")
    parser.add_argument("--exemples", type=int, default=0, metavar="N",
                        help="montrer N valeurs réelles par champ d'adresse trouvé")
    parser.add_argument("--limite", type=int, default=None, help="borner (mise au point)")
    args = parser.parse_args(argv)

    from sqlalchemy import select

    from falkye.db import refuser_si_cible_non_choisie

    code = refuser_si_cible_non_choisie()
    if code:
        return code

    from falkye.db import get_session
    from falkye.models.company import Company
    from falkye.models.signal import Signal
    from falkye.registry.loader import get_registry
    from outils.departageurs import codes_postaux

    print("=" * 78)
    print("L'ADRESSE, DE LA SOURCE AU DOSSIER — QUATRE ÉTATS, TROIS ÉCARTS")
    print("=" * 78)
    print("""
⚠️ CE QUE CET OUTIL NE PEUT PAS ÉTABLIR — à lire avant tout chiffre

   QU'UNE SOURCE NE PUBLIE PAS D'ADRESSE. Le dépôt contient ce que le
   connecteur LIT, pas ce que la source OFFRE. Un champ absent des quatre
   colonnes veut dire « personne ici ne le connaît » — jamais « la source ne
   l'a pas ». Ça se vérifie en ouvrant la source, comme l'archive REQ a dû
   être ouverte pour trouver DENOMN_SOC.

   ET UNE DÉCLARATION N'EST PAS UNE OBSERVATION. `description_tender` était
   déclaré par le connecteur SEAO depuis toujours et vide dans 100 % des cas.
   La colonne « déclaré » est une prétention qu'on confronte.

   AUCUNE ÉCRITURE.
""")

    session = get_session()
    try:
        registre = get_registry()
        # ⚠️ `registre.sources` est un DICT indexé par id, pas une liste.
        declares: dict[str, set[str]] = {
            source_id: set(getattr(definition, "champs_pertinents", None) or [])
            for source_id, definition in registre.sources.items()
        }

        # ---- ce qui ARRIVE réellement, par source ---------------------------
        requete = select(Signal.source_id, Signal.champs, Signal.company_id)
        if args.limite:
            requete = requete.limit(args.limite)
        cles_vues: dict[str, Counter] = defaultdict(Counter)
        remplies: dict[str, Counter] = defaultdict(Counter)
        signaux: Counter = Counter()
        exemples: dict[tuple[str, str], list[str]] = defaultdict(list)
        code_postal_ailleurs: Counter = Counter()
        sans_neq: set[int] = {
            c for (c,) in session.execute(
                select(Company.id).where(Company.neq.is_(None)))
        }
        for source_id, champs, company_id in session.execute(
            requete.execution_options(yield_per=2000)
        ):
            if args.source and source_id not in args.source:
                continue
            signaux[source_id] += 1
            porte_un_code = False
            for cle, valeur in (champs or {}).items():
                cles_vues[source_id][cle] += 1
                if valeur not in (None, "", [], {}):
                    remplies[source_id][cle] += 1
                    if (args.exemples
                            and INDICE_DADRESSE.search(cle)
                            and len(exemples[(source_id, cle)]) < args.exemples):
                        exemples[(source_id, cle)].append(str(valeur)[:60])
                if codes_postaux(str(valeur)) is not None:
                    porte_un_code = True
            if porte_un_code and company_id in sans_neq:
                code_postal_ailleurs[source_id] += 1

        ordre = sorted(signaux, key=lambda s: -signaux[s])
        if not ordre:
            print("   Aucun signal à examiner.")
            return 0

        for source_id in ordre:
            chemin = DOSSIER_CONNECTEURS / f"{source_id}.py"
            lues = cles_lues_par_le_module(chemin) if chemin.exists() else set()
            promus = champs_promus_par_le_module(chemin) if chemin.exists() else set()
            d = _adresses(declares.get(source_id, set()))
            l = _adresses(lues)
            arrivees = _adresses(cles_vues[source_id])
            n = signaux[source_id]

            print("-" * 78)
            print(f"{source_id}   ({milliers(n)} signaux)")
            print("-" * 78)
            if not chemin.exists():
                print(f"   ⚠️ pas de module `{chemin.name}` — *le connecteur porte un autre")
                print("      nom, et les colonnes lues/promues ne sont pas lisibles ici.*")

            print(f"\n   {'déclaré (sources.yaml)':<26} "
                  f"{', '.join(sorted(d)) if d else '—'}")
            print(f"   {'lu par le connecteur':<26} "
                  f"{', '.join(sorted(l)) if l else '—'}")
            print(f"   {'arrivé dans Signal.champs':<26} "
                  f"{', '.join(sorted(arrivees)) if arrivees else '—'}")
            print(f"   {'PROMU en RawSignal':<26} "
                  f"{', '.join(sorted(promus)) if promus else '⛔ AUCUN'}")

            # --- les trois écarts, nommés -----------------------------------
            print()
            declare_jamais_lu = d - l
            lu_jamais_arrive = l - arrivees - d
            # ⚠️ **L'écart se juge EMPLACEMENT PAR EMPLACEMENT.** *Une source qui
            # promeut `region` et laisse `adresse` dans le sac est exactement le
            # motif EIMT* — juger « promeut quelque chose » le masquerait.
            jamais_promus = {
                cle for cle in arrivees
                if not any(motif.search(cle) and emplacement in promus
                           for emplacement, motif in EMPLACEMENTS.items())
            }
            sans_emplacement = {c for c in arrivees
                                if CE_QUI_NA_PAS_DEMPLACEMENT.search(c)}
            if declare_jamais_lu:
                print(f"   ⚠️ DÉCLARÉ ET JAMAIS LU : {', '.join(sorted(declare_jamais_lu))}")
                print("      *Une déclaration qui ne coûte rien. Travail de connecteur.*")
            if lu_jamais_arrive:
                print(f"   ⚠️ LU ET JAMAIS RANGÉ : {', '.join(sorted(lu_jamais_arrive))}")
                print("      *Le champ meurt dans le connecteur.*")
            if jamais_promus - sans_emplacement:
                print(f"   ⛔ RANGÉ ET JAMAIS PROMU — LE MOTIF EIMT : "
                      f"{', '.join(sorted(jamais_promus - sans_emplacement))}")
                print("      *Le seul écart qui se corrige en une ligne* — "
                      "l'emplacement existe,")
                print("       le connecteur ne s'en sert pas.")
            if sans_emplacement:
                print(f"   ⛔ AUCUN EMPLACEMENT POUR CE CHAMP : "
                      f"{', '.join(sorted(sans_emplacement))}")
                print("      ⚠️ *`RawSignal` porte `adresse`, `ville`, `region` — et")
                print("       RIEN pour un code postal.* **Aucun connecteur ne PEUT")
                print("       en promouvoir un.** Et c'est le niveau le plus FORT du")
                print("       départageur : il ne marche aujourd'hui que parce qu'il")
                print("       va le chercher lui-même dans le sac.")
            if not d and not l and not arrivees:
                print("   ⛔ AUCUN CHAMP D'ADRESSE NULLE PART")
                print("      ⚠️ *Ça ne veut PAS dire que la source n'en publie pas.*")
                print("       **Ça veut dire que personne ici ne le sait.** À vérifier")
                print("       en ouvrant la source — c'est la seule façon de fermer")
                print("       la piste.")

            # --- le remplissage réel ----------------------------------------
            if arrivees:
                print(f"\n   {'champ arrivé':<34} {'présent':>9} {'rempli':>9}")
                for cle in sorted(arrivees):
                    print(f"   {cle:<34} {_part(cles_vues[source_id][cle], n):>9} "
                          f"{_part(remplies[source_id][cle], n):>9}")
                    for valeur in exemples.get((source_id, cle), []):
                        print(f"      · {valeur}")
                print("   ⚠️ *« présent » compte la CLÉ, « rempli » la VALEUR.* Un champ")
                print("      présent à 100 % et rempli à 0 % est une promesse vide.")

            # --- le code postal, ailleurs dans les champs --------------------
            k = code_postal_ailleurs.get(source_id, 0)
            print(f"\n   un code postal existe QUELQUE PART dans les champs : "
                  f"{milliers(k)} signal(aux)")
            print("      *Sur des dossiers SANS NEQ, tous champs confondus — donc y")
            print("       compris hors des clés qui s'annoncent comme une adresse.*")
            print("      ⚠️ La ville est le niveau le plus FAIBLE du départageur. Une")
            print("         source qui n'a qu'elle vaut moins qu'une qui porte un code.")
            print()

        print("=" * 78)
        print("   RIEN N'A ÉTÉ ÉCRIT. Et un champ absent de ces quatre colonnes")
        print("   n'est pas un champ que la source ne publie pas — c'est un champ")
        print("   que personne ici ne connaît.")
        print("=" * 78)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
