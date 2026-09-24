#!/usr/bin/env python3
"""De quoi POSER une borne de longueur minimale au scorage — **une mesure.**

**Le défaut** *(relevé par Alexandre le 2026-09-23)*. **Rien ne borne la
LONGUEUR d'une forme du registre au scorage.** *`rapidfuzz.WRatio` rend au moins
**90,0** quand un nom du registre est entièrement contenu dans le nom détecté* —
et **deux lettres suffisent** : `« LA »` a scoré **95,0** sur le dossier `#5476`.

⚠️ **Alexandre ne veut AUCUNE valeur posée pour débloquer.** *« Je la poserai
avec Claude. »* ✅ **L'UNITÉ, elle, est tranchée depuis le 2026-09-23 : la
LETTRE** *(registre D60)*. **Cet outil ne propose donc pas de borne : il rend de
quoi en poser une** — la distribution des longueurs de la forme GAGNANTE chez les
retenus et chez les restants, ce que chaque borne possible retirerait, et ce que
le corpus porte déjà de comparable.

## ⚠️ Ce que cet outil ne peut PAS dire

**Lesquels des appariements retirés étaient BONS.** *La justesse des NEQ posés
n'a jamais été mesurée* — c'est le point 10 de la §13, encore à construire.
**Ce qui est rendu ici est un nombre d'appariements RETENUS, jamais un nombre de
bons appariements**, et les deux ne se confondent pas.

## Comment la borne est simulée — par un APPEL, jamais par une copie

`transformer_forme` reçoit le nom PUBLIÉ de chaque forme et son résultat est
renormalisé avant d'être scoré. **Rendre la chaîne vide pour une forme trop
courte, c'est exactement ce qu'une borne ferait** : la forme ne score plus, et
un NEQ dont toutes les formes sont courtes tombe du lot.

⚠️ **Le chemin de simulation ignorait `sans_les_retires` jusqu'au 2026-09-23** —
*il aurait réintroduit les 3,2 millions de formes retirées dans le PREMIER temps
du même geste*, et cette mesure aurait attribué à la borne ce que le troisième
temps faisait. **Corrigé dans `falkye/sources/req.py` avant d'écrire cet
outil.**

⚠️ **RIEN NE S'ÉCRIT EN BASE.**
"""
from __future__ import annotations

import argparse
from collections import Counter

from outils.nombres import milliers

#: Les bornes mises à l'épreuve par défaut. ⚠️ **Ce ne sont pas des
#: propositions** : ce sont les valeurs dont on rend le coût, pour qu'Alexandre
#: en pose une. *`1` est la borne qui ne retire rien — elle sert de témoin.*
BORNES_PAR_DEFAUT = (1, 2, 3, 4, 5, 6, 8)

#: Les tranches de longueur, en CARACTÈRES de la forme normalisée.
TRANCHES = ((1, 2), (3, 3), (4, 5), (6, 9), (10, 19), (20, 10_000))

#: ⚠️ **TROIS façons de mesurer une longueur, et elles ne classent pas pareil.**
#: *`« L.A. »` se normalise en `« l a »` — **trois caractères, deux lettres, deux
#: mots**.*
#:
#: ✅ **L'UNITÉ EST TRANCHÉE le 2026-09-23 : LA LETTRE** *(registre D60)*.
#: *« C'est la seule qui traite `« LA »` et `« L.A. »` comme la même porte. »*
#: **Une borne en CARACTÈRES retirerait l'une en gardant l'autre.** ⬜ *La VALEUR
#: attend la mesure.* **Les deux autres mesures restent lisibles par `--mesure`,
#: pour que la décision se relise contre ce qu'elle a écarté.**
MESURES = {
    "caracteres": ("caractères de la forme normalisée, espaces compris",
                   lambda forme: len(forme)),
    "lettres": ("caractères sans les espaces",
                lambda forme: len(forme.replace(" ", ""))),
    "mots": ("mots", lambda forme: len(forme.split())),
}


def etiquette_de_tranche(bas: int, haut: int) -> str:
    if haut >= 10_000:
        return f"{bas} caractères et plus"
    if bas == haut:
        return f"{bas} caractères"
    return f"{bas} à {haut} caractères"


def tranche_de(longueur: int) -> tuple[int, int]:
    for bas, haut in TRANCHES:
        if bas <= longueur <= haut:
            return (bas, haut)
    return TRANCHES[-1]


def forme_gagnante(matches: list) -> str | None:
    """La forme normalisée qui a SCORÉ au sommet — `None` s'il n'y a rien.

    ⚠️ **Pas la dénomination élue.** *`_scorer` prend le MEILLEUR des noms d'un
    NEQ, `req_noms` compris*, et un outil qui lirait `entry.nom` mesurerait une
    forme qui n'a pas scoré. **C'est le défaut d'affichage qui a coûté deux
    jours de lecture fausse le 21 septembre** (`Elevage des reines Le Roi
    Bourdon`, 61,5 annoncé 95,0).
    """
    if not matches:
        return None
    return matches[0].forme_normalisee


def transformateur_de_borne(borne: int, mesure: str = "lettres"):
    """Un `transformer_forme` qui EFFACE les formes plus courtes que `borne` —
    *la borne, simulée par le SCOREUR DU PRODUIT.*

    ⚠️ **La longueur se mesure sur la forme NORMALISÉE**, jamais sur le nom
    publié : c'est la forme normalisée que le scoreur compare, et borner sur le
    publié bornerait une chaîne que personne ne score.

    ✅ **`mesure` vaut `lettres` par défaut depuis le 2026-09-23** *(registre
    D60, tranché par Alexandre)* : `« L.A. »` fait trois caractères, **deux
    lettres** et deux mots, et la lettre est la seule unité qui en fasse la même
    porte que `« LA »`. *Les deux autres restent disponibles pour relire la
    décision contre ce qu'elle a écarté.*
    """
    from falkye.sources.req import _normaliser

    longueur = MESURES[mesure][1]

    def transformer(nom_publie: str) -> str:
        return "" if longueur(_normaliser(nom_publie or "")) < borne else nom_publie

    return transformer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bornes", type=int, nargs="*", default=list(BORNES_PAR_DEFAUT),
                        help="les bornes à chiffrer (défaut : 1 2 3 4 5 6 8)")
    parser.add_argument("--mesure", choices=sorted(MESURES), default="lettres",
                        help="ce qu'on appelle « longueur » — défaut : la LETTRE, "
                             "tranchée le 2026-09-23 (registre D60)")
    parser.add_argument("--paires", type=int, default=0, metavar="N",
                        help="montrer N formes gagnantes les plus COURTES")
    parser.add_argument("--limite", type=int, default=None, help="borner (mise au point)")
    parser.add_argument("--pas", type=int, default=500, metavar="N")
    args = parser.parse_args(argv)

    from sqlalchemy import select

    from falkye.db import refuser_si_cible_non_choisie

    code = refuser_si_cible_non_choisie()
    if code:
        return code

    from falkye.db import get_session
    from falkye.models.company import Company
    from falkye.resolution import famille_de
    from falkye.sources import req as req_source

    session = get_session()
    try:
        print("=" * 78)
        print("LA LONGUEUR MINIMALE D'UNE FORME AU SCORAGE — de quoi la POSER")
        print("=" * 78)
        print("""
⚠️ AUCUNE BORNE N'EST PROPOSÉE ICI. Alexandre la posera avec Claude.
   Cet outil rend la distribution, le coût de chaque borne, et ce que le
   corpus porte déjà de comparable. Rien de plus.

⛔ ET IL NE DIT PAS LESQUELS ÉTAIENT BONS. La justesse des NEQ posés n'a
   jamais été mesurée (§13, point 10). Ce qui suit compte des
   appariements RETENUS, jamais des BONS appariements.

⚠️ RIEN N'EST ÉCRIT.
""")
        requete = select(Company).order_by(Company.id)
        if args.limite:
            requete = requete.limit(args.limite)
        dossiers = list(session.execute(requete).scalars().all())

        print(f"… résolution de {milliers(len(dossiers))} dossiers", flush=True)

        # (company, famille, forme gagnante) — une seule résolution par dossier.
        lus: list = []
        for i, company in enumerate(dossiers, 1):
            if args.pas and i % args.pas == 0:
                print(f"   … {milliers(i)} / {milliers(len(dossiers))}", flush=True)
            matches = req_source.resolve_neq_by_name(
                session, company.nom_detecte, ville=company.ville)
            lus.append((company, famille_de(matches), forme_gagnante(matches), matches))

        # ---- 1. LA DISTRIBUTION -------------------------------------------
        print("\n" + "-" * 78)
        print("1. LA LONGUEUR DE LA FORME GAGNANTE — retenus contre restants")
        print("-" * 78)
        print("""
   ⚠️ LA FORME GAGNANTE, PAS LA DÉNOMINATION ÉLUE. `_scorer` prend le
      MEILLEUR des noms d'un NEQ, `req_noms` compris. Lire `entry.nom`
      mesurerait une forme qui n'a pas scoré — c'est le défaut
      d'affichage qui a coûté deux jours de lecture fausse le 21.
""")
        retenus = [(c, f, g) for c, f, g, _m in lus if f == "RETENU"]
        restants = [(c, f, g) for c, f, g, _m in lus if f != "RETENU"]
        par_tranche: dict[str, Counter] = {"retenus": Counter(), "restants": Counter()}
        for lot, nom_du_lot in ((retenus, "retenus"), (restants, "restants")):
            for _c, _f, gagnante in lot:
                if gagnante is None:
                    par_tranche[nom_du_lot]["aucune forme — aucun candidat"] += 1
                else:
                    par_tranche[nom_du_lot][etiquette_de_tranche(*tranche_de(len(gagnante)))] += 1

        etiquettes = [etiquette_de_tranche(b, h) for b, h in TRANCHES]
        etiquettes.append("aucune forme — aucun candidat")
        largeur = max(len(e) for e in etiquettes) + 1
        print(f"   {'':<{largeur}} {'retenus':>18} {'restants':>18}")
        print(f"   {'':<{largeur}} {milliers(len(retenus)):>18} {milliers(len(restants)):>18}")
        print()
        for e in etiquettes:
            a, b = par_tranche["retenus"][e], par_tranche["restants"][e]
            pa = f"{100 * a / len(retenus):.1f} %" if retenus else "—"
            pb = f"{100 * b / len(restants):.1f} %" if restants else "—"
            print(f"   {e:<{largeur}} {milliers(a):>9} {pa:>8} {milliers(b):>9} {pb:>8}")

        # ---- 2. CE QUE CHAQUE BORNE RETIRERAIT ----------------------------
        print("\n" + "-" * 78)
        print("2. CE QUE CHAQUE BORNE RETIRERAIT — par un APPEL de la production")
        print("-" * 78)
        print("""
   COMMENT. `transformer_forme` rend la chaîne vide pour toute forme du
   registre plus courte que la borne : elle ne score plus, et un NEQ
   dont toutes les formes sont courtes tombe du lot. C'est exactement ce
   qu'une borne ferait, et c'est le SCOREUR DU PRODUIT qui l'exécute.

   ⚠️ LA BORNE 1 NE RETIRE RIEN — c'est le témoin. Si sa ligne n'est pas
      à zéro, l'instrument ment, et le reste du tableau ne vaut rien.
""")
        print(f"   longueur mesurée en : {MESURES[args.mesure][0]}\n")
        print(f"   {'':>9} {'RETENUS perdus':>16} {'RETENUS gagnés':>16} "
              f"{'NEQ changé':>12}")
        print()
        for borne in sorted(args.bornes):
            transformer = transformateur_de_borne(borne, args.mesure)
            perdus = gagnes = change = 0
            exemples: list = []
            for i, (company, famille, _g, matches) in enumerate(lus, 1):
                if args.pas and i % args.pas == 0:
                    print(f"      … borne {borne} : {milliers(i)} / {milliers(len(lus))}",
                          flush=True)
                avec = req_source.resolve_neq_by_name(
                    session, company.nom_detecte, ville=company.ville,
                    transformer_forme=transformer)
                nouvelle = famille_de(avec)
                if famille == "RETENU" and nouvelle != "RETENU":
                    perdus += 1
                    if len(exemples) < 5:
                        exemples.append((company, matches[0] if matches else None))
                elif famille != "RETENU" and nouvelle == "RETENU":
                    gagnes += 1
                elif famille == "RETENU" and nouvelle == "RETENU" and matches and avec:
                    if matches[0].entry.neq != avec[0].entry.neq:
                        change += 1
            print(f"   borne {borne:>3} {milliers(perdus):>16} "
                  f"{milliers(gagnes):>16} {milliers(change):>12}")
            if args.paires and exemples:
                for company, m in exemples[:args.paires]:
                    forme = m.forme_normalisee if m is not None else "—"
                    print(f"          #{company.id}  "
                          f"{(company.nom_detecte or '')[:34]:<36} "
                          f"« {forme} » {m.score if m else 0:.1f}")
        print("""
   ⚠️ « RETENUS PERDUS » N'EST PAS « BONS APPARIEMENTS PERDUS ». Un
      appariement gagné par une forme de deux lettres est exactement le
      cas qu'on soupçonne d'être faux. Le tableau dit COMBIEN bouge,
      jamais dans quel sens ça va.

   ⚠️ ET UNE BORNE FAIT GAGNER AUTANT QU'ELLE FAIT PERDRE. Retirer une
      forme courte fait tomber un concurrent sous l'écart, donc RÉSOUT
      un dossier qui était ambigu — même mécanisme que le troisième
      temps, même prudence.

   ⛔ UNE SOUS-QUESTION, ET ELLE SE POSE AVEC LA BORNE. « Longueur » veut
      dire trois choses, et elles ne classent pas pareil :

         « L.A. » se normalise en « l a »
            3 caractères · 2 lettres · 2 mots

      ✅ TRANCHÉE LE 23 SEPTEMBRE : L'UNITÉ EST LA LETTRE (registre D60).
      C'est la seule qui traite « LA » et « L.A. » comme la même porte —
      une borne en CARACTÈRES retirerait l'une en gardant l'autre.

      ⬜ LA VALEUR, ELLE, N'EST PAS POSÉE. `--mesure` garde les deux
      autres lisibles, pour que la décision se relise contre ce qu'elle
      a écarté.
""")

        # ---- 3. CE QUE LE CORPUS PORTE DÉJÀ -------------------------------
        print("-" * 78)
        print("3. CE QUE LE CORPUS PORTE DÉJÀ DE COMPARABLE")
        print("-" * 78)
        print("""
   UNE SEULE MESURE VOISINE, et elle porte sur l'AUTRE CÔTÉ.
   §3+4, « Le nom court, second discriminant » mesure la longueur du nom
   DÉTECTÉ, en MOTS :

      1 mot          restants 5,1 %   résolus 1,5 %   rapport ×3,4
      2 mots         restants 14,8 %  résolus 10,0 %  rapport ×1,5
      3 mots et plus restants 80,1 %  résolus 88,6 %  rapport ×0,9

   ⛔ ET ELLE NE S'APPLIQUE PAS ICI, pour deux raisons.

      1. Ce n'est pas le même côté. Le nom DÉTECTÉ vient de la source;
         la forme du REGISTRE est ce contre quoi on score. Borner l'un
         ou l'autre ne retire pas les mêmes dossiers.

      2. La CAUSE du ×3,4 est connue, et elle est dans notre code :
         `candidats_par_mot_rare` exige un deuxième mot, qu'un nom d'un
         mot n'a pas (§12bis). Le ×3,4 mesure donc un défaut de
         RÉCUPÉRATION, pas une faiblesse du nom court au SCORAGE. Le
         lire comme un argument pour une borne serait lire un défaut
         d'instrument comme un fait du monde — pour la quatrième fois.

   LES AUTRES BORNES DE LONGUEUR DU DÉPÔT, pour l'échelle :

      `nom_normalise[:6]`  le repli par sous-chaîne de `dedup_entreprises`
                           — une borne de RÉCUPÉRATION, jamais de scorage
      le préfixe           le premier mot du nom détecté, sans plancher

   ⚠️ AUCUNE N'EST UNE BORNE DE SCORAGE. Il n'y a rien à reprendre :
      celle-ci serait la première.
""")

        # ---- 4. LES FORMES GAGNANTES LES PLUS COURTES ---------------------
        if args.paires:
            courtes = sorted(
                ((c, f, g) for c, f, g in retenus + restants if g),
                key=lambda t: len(t[2]))[:args.paires]
            print("=" * 78)
            print(f"LES {len(courtes)} FORMES GAGNANTES LES PLUS COURTES")
            print("=" * 78)
            for company, famille, gagnante in courtes:
                print(f"\n   #{company.id}   {(company.nom_detecte or '')[:50]}")
                print(f"      forme gagnante : « {gagnante} »  "
                      f"({len(gagnante)} caractères)")
                print(f"      famille        : {famille}")
                print(f"      NEQ posé       : {company.neq or '—'}")

        print("\n" + "=" * 78)
        print("   RIEN N'A ÉTÉ ÉCRIT. Aucune borne n'a été posée.")
        print("=" * 78)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
