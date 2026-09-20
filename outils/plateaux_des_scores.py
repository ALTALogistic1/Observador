#!/usr/bin/env python3
"""Les PLATEAUX du scoreur — la distribution réelle des scores sur les ambigus.

## Le motif, et ce qu'il avance

**Lu sur 32 dossiers le 20 septembre** : sur 102 lignes de candidats, **91
tenaient sur quatre valeurs** — `85,5`, `90,0`, `100,0`, `95,0` — et les onze
autres étaient toutes uniques. *Les scores ne formaient pas un continuum : ils
formaient des paliers.*

**Mesuré sur `rapidfuzz`, et c'est ce qui a lancé cette mesure** : un nom du
registre **entièrement contenu** dans le nom détecté rend **exactement 90,0**,
toujours — `fuzz.WRatio` y applique son composant partiel à taux plein, pondéré.

**Ce que le motif avance** : si un dossier reste ambigu parce que son meilleur et
son second tombent sur deux paliers voisins, **ce qui le retient n'est pas sa
ressemblance à ses concurrents — c'est le palier où son vrai match atterrit.**

⚠️ **Cette mesure dit si les quatre paliers tiennent sur 3 267 dossiers ou
seulement sur 102 lignes.** *Une lecture de 32 dossiers ne prouve pas une
population, et c'est exactement ce qu'on vient vérifier.*

## ⚠️ CE QUE CETTE MESURE NE DIRA PAS — à lire avant tout chiffre

**Qu'un dossier serait BIEN APPARIÉ si l'écart changeait.** *Elle décrit des
DISTANCES, jamais des IDENTITÉS.* **Deux noms à 5 points l'un de l'autre peuvent
désigner la même entreprise ou deux entreprises sans rapport — le score ne le
dit pas, et cette mesure encore moins.**

⚠️ **Et elle ne touche à rien.** *Le seuil de **92** et l'écart de **8** ne se
rouvrent qu'en dernier recours, et c'est une décision d'Alexandre, inchangée.*
**Les chiffrages existent pour ce jour-là, pas pour l'autoriser.**

## ⚠️ Une correction de ma propre lecture, avant de compter

**J'ai écrit que `90,0 → 85,5` fait un ambigu. C'est faux.** Un ambigu exige
`meilleur ≥ 92` *(`falkye/resolution.py::famille_de`)* — donc **un dossier dont
le meilleur vaut 90 est « trop faible », jamais ambigu.** *Le couple
`90 → 85,5` vit chez les trop faibles*, et il n'est **pas mesuré ici** : la
demande porte sur les ambigus.

**Ce qui reste atteignable sur cette population**, et c'est ce qui se compte :

| meilleur | second doit être | couple de paliers possible |
|---|---|---|
| `100,0` | **> 92** | `100 → 95`, `100 → 97` |
| `95,0` | **> 87** | `95 → 90` |
| `92,0`–`93,4` | **> 84**–`85,4` | `92 → 85,5` |

## ⚠️ Le bonus de ville déplace la distribution, et il faut le savoir

`_scorer` ajoute **+5** au candidat dont la ville concorde — **après** la coupe à
cinq. *Un score observé à 95 peut donc être un 90 déplacé.* **Le score d'avant
n'est pas conservé**, donc il ne se reconstitue pas.

**Ce que la mesure fait à la place** : elle compte les scores qui portent le
bonus, et rend la distribution **deux fois** — sur tous les couples, puis sur les
seuls couples **sans bonus d'aucun côté**, où le score observé est la valeur brute
de la bibliothèque. *La seconde est la vue propre des paliers; la première est ce
que le moteur voit.*

⚠️ **AUCUNE ÉCRITURE. Les échelles ne bougent pas : seuil 92, écart 8.**

Usage, SUR L'HÔTE :
    python3 -m outils.plateaux_des_scores
    python3 -m outils.plateaux_des_scores --couples 25
"""
from __future__ import annotations

import argparse
from collections import Counter

from outils.nombres import milliers

#: À partir de combien de dossiers une valeur de score est appelée un PALIER.
#: ⚠️ **Une borne d'affichage, choisie d'avance et arbitraire** — *la sortie rend
#: la distribution ENTIÈRE au-dessus, pour que le choix se conteste sur pièce
#: plutôt que sur parole.* **Elle ne décide rien : elle nomme.**
PLANCHER_DUN_PALIER = 50

#: Les quatre paliers relevés dans la lecture du 20 septembre, sur 102 lignes.
#: ⚠️ **Ils sont l'HYPOTHÈSE, pas la mesure.** *La sortie dit lesquels la
#: population confirme, et surtout lesquels elle ajoute* — une mesure qui ne
#: chercherait que les quatre attendus confirmerait sa propre liste.
PALIERS_DE_LA_LECTURE = (100.0, 95.0, 90.0, 85.5)

#: Combien de valeurs distinctes la sortie détaille avant de résumer le reste.
VALEURS_DETAILLEES = 20


def _part(k: int, n: int) -> str:
    return f"{100 * k / n:.1f} %" if n else "—"


def paliers_observes(compteur: Counter, plancher: int = PLANCHER_DUN_PALIER
                     ) -> list[float]:
    """Les valeurs qui portent au moins `plancher` dossiers, **triées par
    score décroissant.** *Trouvées dans la population, jamais fournies.*"""
    return sorted((v for v, k in compteur.items() if k >= plancher), reverse=True)


def sur_un_palier(score: float, paliers) -> bool:
    return score in set(paliers)


def porte_le_bonus_de_ville(company, match) -> bool:
    """Le candidat a-t-il reçu le **+5** de `_scorer`?

    ⚠️ *La condition est recopiée du moteur, et c'est le seul endroit de cet
    outil où ça se produit* — `_scorer` ne l'expose pas, et le score d'avant
    n'est pas conservé. **Donc ce compte est un indicateur, pas une
    reconstitution** : si le moteur changeait sa condition, celle-ci
    divergerait en silence.
    """
    from falkye.sources.column_mapping import normaliser

    if not company.ville or not match.entry.ville:
        return False
    return normaliser(match.entry.ville) == normaliser(company.ville)


def _ventiler(titre: str, compteur: Counter, total: int, paliers,
              plancher: int = PLANCHER_DUN_PALIER) -> None:
    """La distribution d'une colonne de scores, **entière au-dessus du plancher**."""
    print(f"\n   {titre}\n")
    print(f"   {'score':>8} {'dossiers':>9} {'part':>8}   ")
    rangs = compteur.most_common()
    for valeur, k in rangs[:VALEURS_DETAILLEES]:
        marque = "  ← PALIER" if valeur in set(paliers) else ""
        vu = "  (vu dans la lecture)" if valeur in PALIERS_DE_LA_LECTURE else ""
        print(f"   {valeur:>8.1f} {milliers(k):>9} {_part(k, total):>8}{marque}{vu}")
    reste = rangs[VALEURS_DETAILLEES:]
    if reste:
        print(f"   {'…':>8} {milliers(sum(k for _v, k in reste)):>9} "
              f"{_part(sum(k for _v, k in reste), total):>8}"
              f"   répartis sur {milliers(len(reste))} autres valeurs")
    print(f"\n   valeurs distinctes : {milliers(len(rangs))}"
          f"   ·   paliers (≥ {plancher} dossiers) : {milliers(len(paliers))}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--couples", type=int, default=15, metavar="N",
                        help="combien de couples (meilleur, second) détailler")
    # ⚠️ **La borne est un paramètre, pas une constante enfouie.** *Une borne
    # d'affichage qu'on ne peut pas bouger ne se conteste pas : elle se subit.*
    parser.add_argument("--plancher", type=int, default=PLANCHER_DUN_PALIER,
                        metavar="N", help="dossiers minimum pour qu'une valeur "
                                          "soit appelée un PALIER")
    parser.add_argument("--limite", type=int, default=None, help="borner (mise au point)")
    parser.add_argument("--pas", type=int, default=500, metavar="N",
                        help="cadence du témoin d'avancement du rejeu")
    args = parser.parse_args(argv)

    from sqlalchemy import select

    from falkye.db import refuser_si_cible_non_choisie

    code = refuser_si_cible_non_choisie()
    if code:
        return code

    from falkye.db import get_session
    from falkye.models.company import Company
    from falkye.resolution import (
        SEUIL_AMBIGUITE_ECART_MIN,
        SEUIL_RESOLUTION_CONFIANTE,
        famille_de,
    )
    from outils.reresolution_neq import _resoudre_une

    print("=" * 78)
    print("LES PALIERS DU SCOREUR — la distribution réelle, sur les ambigus")
    print("=" * 78)
    print(f"""
⚠️ CE QUE CETTE MESURE NE DIRA PAS — avant tout chiffre

   QU'UN DOSSIER SERAIT BIEN APPARIÉ SI L'ÉCART CHANGEAIT. Elle décrit des
   DISTANCES, jamais des IDENTITÉS. Deux noms à cinq points l'un de l'autre
   peuvent désigner la même entreprise ou deux sans rapport : le score ne le
   dit pas, et cette mesure encore moins.

   ET ELLE NE TOUCHE À RIEN. Le seuil de {SEUIL_RESOLUTION_CONFIANTE:.0f} et l'écart de {SEUIL_AMBIGUITE_ECART_MIN:.0f} ne se rouvrent
   qu'en dernier recours, décision d'Alexandre, inchangée. Les chiffrages
   existent pour ce jour-là, pas pour l'autoriser.

⚠️ UNE CORRECTION DE MA PROPRE LECTURE, avant de compter

   J'avais écrit que « 90,0 → 85,5 » fait un ambigu. C'EST FAUX. Un ambigu
   exige meilleur ≥ {SEUIL_RESOLUTION_CONFIANTE:.0f} : un dossier dont le meilleur vaut 90 est « trop
   faible », jamais ambigu. Ce couple-là vit chez les trop faibles, et il
   n'est PAS mesuré ici — la demande porte sur les ambigus.

⚠️ LE BONUS DE VILLE DÉPLACE LA DISTRIBUTION

   `_scorer` ajoute +5 au candidat dont la ville concorde, APRÈS la coupe à
   cinq. Un score observé à 95 peut être un 90 déplacé, et le score d'avant
   n'est pas conservé. La distribution est donc rendue DEUX FOIS : sur tous
   les couples, puis sur les seuls couples SANS bonus d'aucun côté.
""")

    session = get_session()
    try:
        requete = select(Company).where(Company.neq.is_(None)).order_by(Company.id)
        if args.limite:
            requete = requete.limit(args.limite)
        restants = list(session.execute(requete).scalars().all())
        if not restants:
            print("   Aucun restant à mesurer.")
            return 0

        print(f"… rejeu de la résolution sur {milliers(len(restants))} restants, "
              f"par le chemin de production", flush=True)
        meilleurs: Counter = Counter()
        seconds: Counter = Counter()
        couples: Counter = Counter()
        couples_sans_bonus: Counter = Counter()
        meilleurs_sans_bonus: Counter = Counter()
        seconds_sans_bonus: Counter = Counter()
        avec_bonus = Counter()
        n_amb = 0
        par_famille: Counter = Counter()
        for i, company in enumerate(restants, 1):
            if args.pas and i % args.pas == 0:
                print(f"   … {milliers(i)} / {milliers(len(restants))}", flush=True)
            _neq, matches = _resoudre_une(session, company)
            famille = famille_de(matches)
            par_famille[famille] += 1
            if famille != "ambigu":
                continue
            n_amb += 1
            premier, second = matches[0], matches[1]
            meilleurs[premier.score] += 1
            seconds[second.score] += 1
            couples[(premier.score, second.score)] += 1
            b1 = porte_le_bonus_de_ville(company, premier)
            b2 = porte_le_bonus_de_ville(company, second)
            if b1:
                avec_bonus["le meilleur porte le +5"] += 1
            if b2:
                avec_bonus["le second porte le +5"] += 1
            if b1 or b2:
                avec_bonus["l'un des deux au moins"] += 1
            if not b1 and not b2:
                couples_sans_bonus[(premier.score, second.score)] += 1
                meilleurs_sans_bonus[premier.score] += 1
                seconds_sans_bonus[second.score] += 1

        print("\n   familles du rejeu : " + "  ·  ".join(
            f"{f} {milliers(k)}" for f, k in par_famille.most_common()))
        print(f"   AMBIGUS MESURÉS : {milliers(n_amb)}")
        if not n_amb:
            # ⚠️ *Une mesure dit toujours qu'elle n'a rien écrit*, y compris
            # quand elle n'a rien trouvé — sinon le silence se lit comme une
            # interruption.
            print("   Aucun ambigu — rien à ventiler, et ce n'est pas « 0 palier ».")
            print("   RIEN N'A ÉTÉ ÉCRIT. Les échelles n'ont pas bougé.")
            return 0

        # ---- 1. LES PALIERS TIENNENT-ILS? ----------------------------------
        print("\n" + "-" * 78)
        print("1. LES PALIERS — la population les confirme-t-elle?")
        print("-" * 78)
        paliers_m = paliers_observes(meilleurs, args.plancher)
        paliers_s = paliers_observes(seconds, args.plancher)
        _ventiler("LE MEILLEUR CANDIDAT", meilleurs, n_amb, paliers_m, args.plancher)
        _ventiler("LE SECOND", seconds, n_amb, paliers_s, args.plancher)

        tous = sorted(set(paliers_m) | set(paliers_s), reverse=True)
        attendus = set(PALIERS_DE_LA_LECTURE)
        confirmes = [p for p in tous if p in attendus]
        ajoutes = [p for p in tous if p not in attendus]
        manquants = sorted(attendus - set(tous), reverse=True)
        print(f"""
   L'HYPOTHÈSE DE LA LECTURE, CONFRONTÉE À {milliers(n_amb)} DOSSIERS

   quatre paliers annoncés : {', '.join(f'{p:.1f}' for p in PALIERS_DE_LA_LECTURE)}
   confirmés par la population : {', '.join(f'{p:.1f}' for p in confirmes) or 'aucun'}
   ⚠️ NON confirmés            : {', '.join(f'{p:.1f}' for p in manquants) or 'aucun'}
   ⚠️ AJOUTÉS par la population : {', '.join(f'{p:.1f}' for p in ajoutes) or 'aucun'}

   ⚠️ LA TROISIÈME LIGNE EST LA PLUS UTILE. Une mesure qui n'aurait cherché
      que les quatre attendus aurait confirmé sa propre liste — ce sont les
      paliers AJOUTÉS qui disent si la lecture avait vu la bonne forme.
   ⚠️ Et « palier » veut dire ici : au moins {args.plancher} dossiers sur cette valeur
      exacte. C'est une borne d'affichage, choisie d'avance, et la
      distribution entière est au-dessus pour qu'elle se conteste.
""")
        return _couples(n_amb, couples, couples_sans_bonus, tous, avec_bonus,
                        meilleurs_sans_bonus, seconds_sans_bonus, args.couples,
                        args.plancher)
    finally:
        session.close()


#: L'ordre d'affichage des trois cas, **et il est celui de la question posée** :
#: *un couple dont les DEUX scores sont des paliers est un couple dont l'écart
#: est une différence de deux constantes de la bibliothèque*, jamais une mesure
#: de ressemblance.
LES_DEUX = "les DEUX sur un palier"
UN_SEUL = "un seul sur un palier"
AUCUN = "aucun des deux"
ORDRE_DES_CAS = (LES_DEUX, UN_SEUL, AUCUN)


def _cas_du_couple(meilleur: float, second: float, paliers) -> str:
    sur = set(paliers)
    combien = (meilleur in sur) + (second in sur)
    return {2: LES_DEUX, 1: UN_SEUL, 0: AUCUN}[combien]


def _table_des_couples(couples: Counter, total: int, paliers, combien: int,
                       titre: str) -> None:
    print(f"\n   {titre}\n")
    print(f"   {'meilleur':>9} {'second':>8} {'écart':>7} {'dossiers':>9} "
          f"{'part':>8}   ")
    for (m, s), k in couples.most_common(combien):
        marque = "  ← deux paliers" if _cas_du_couple(m, s, paliers) == LES_DEUX else ""
        print(f"   {m:>9.1f} {s:>8.1f} {m - s:>7.1f} {milliers(k):>9} "
              f"{_part(k, total):>8}{marque}")
    reste = len(couples) - min(combien, len(couples))
    if reste > 0:
        vus = sum(k for _c, k in couples.most_common(combien))
        print(f"   {'…':>9} {'':>8} {'':>7} {milliers(total - vus):>9} "
              f"{_part(total - vus, total):>8}"
              f"   répartis sur {milliers(reste)} autres couples")


def _couples(n_amb: int, couples: Counter, couples_sans_bonus: Counter,
             paliers, avec_bonus: Counter, meilleurs_sans_bonus: Counter,
             seconds_sans_bonus: Counter, combien: int,
             plancher: int = PLANCHER_DUN_PALIER) -> int:
    """Les couples `(meilleur, second)`, **et la part décisive du motif.**"""
    print("-" * 78)
    print("2. LES COUPLES (meilleur, second) — et l'écart de chacun")
    print("-" * 78)
    _table_des_couples(couples, n_amb, paliers, combien,
                       f"TOUS LES COUPLES — {milliers(n_amb)} ambigus")
    print("""
   ⚠️ TOUS CES ÉCARTS SONT SOUS 8, et ce n'est pas un résultat : c'est la
      DÉFINITION d'un ambigu. Ce que la colonne « écart » sert à lire, c'est
      sur QUELLES valeurs il tombe — pas qu'il soit petit.
""")

    # ---- 3. LA PART DÉCISIVE --------------------------------------------
    print("-" * 78)
    print("3. LA PART DÉCISIVE — l'écart est-il une différence de CONSTANTES?")
    print("-" * 78)
    par_cas: Counter = Counter()
    for (m, s), k in couples.items():
        par_cas[_cas_du_couple(m, s, paliers)] += k
    print(f"\n   {'':<34} {'dossiers':>9} {'part':>8}")
    for cas in ORDRE_DES_CAS:
        print(f"   {cas:<34} {milliers(par_cas.get(cas, 0)):>9} "
              f"{_part(par_cas.get(cas, 0), n_amb):>8}")
    print(f"""
   ⚠️ CE QUE DIT LA PREMIÈRE LIGNE, ET CE QU'ELLE NE DIT PAS. Un couple dont
      les deux scores sont des paliers a un écart qui est la DIFFÉRENCE DE
      DEUX CONSTANTES de la bibliothèque. Ce qui retient ces dossiers sous
      l'écart n'est donc pas une mesure de leur ressemblance aux concurrents :
      c'est le palier où leur meilleur candidat atterrit.

      ⛔ ELLE NE DIT PAS que ces dossiers seraient bien appariés autrement.
      Un palier peut porter le bon candidat comme le mauvais — la distance
      est décrite, l'identité ne l'est pas.

   ⚠️ ET LA DERNIÈRE LIGNE EST L'AUTRE MOITIÉ DU RÉSULTAT. Les couples dont
      aucun score n'est un palier sont ceux où le scoreur a rendu une valeur
      graduée. Si cette ligne est grosse, le motif ne porte qu'une partie de
      la population — et le dire est un résultat.
""")

    # ---- 4. LE BONUS DE VILLE --------------------------------------------
    print("-" * 78)
    print("4. LE BONUS DE VILLE — combien de scores il déplace")
    print("-" * 78)
    print(f"\n   {'':<34} {'dossiers':>9} {'part':>8}")
    for etiquette in ("le meilleur porte le +5", "le second porte le +5",
                      "l'un des deux au moins"):
        k = avec_bonus.get(etiquette, 0)
        print(f"   {etiquette:<34} {milliers(k):>9} {_part(k, n_amb):>8}")
    n_propre = sum(couples_sans_bonus.values())
    print(f"   {'AUCUN des deux — vue propre':<34} {milliers(n_propre):>9} "
          f"{_part(n_propre, n_amb):>8}")
    print("""
   ⚠️ LA CONDITION DU BONUS EST RECOPIÉE DU MOTEUR, et c'est le seul endroit
      de cet outil où ça se produit — `_scorer` ne l'expose pas, et le score
      d'avant n'est pas conservé. Ce compte est donc un INDICATEUR, pas une
      reconstitution : si le moteur changeait sa condition, celle-ci
      divergerait en silence.
""")
    if n_propre:
        paliers_propres = sorted(
            set(paliers_observes(meilleurs_sans_bonus, plancher))
            | set(paliers_observes(seconds_sans_bonus, plancher)), reverse=True)
        print("-" * 78)
        print("5. LA VUE PROPRE — les couples que le bonus n'a pas touchés")
        print("-" * 78)
        _table_des_couples(couples_sans_bonus, n_propre, paliers_propres, combien,
                           f"SANS BONUS D'AUCUN CÔTÉ — {milliers(n_propre)} couples")
        par_cas_propre: Counter = Counter()
        for (m, s), k in couples_sans_bonus.items():
            par_cas_propre[_cas_du_couple(m, s, paliers_propres)] += k
        print(f"\n   {'':<34} {'dossiers':>9} {'part':>8}")
        for cas in ORDRE_DES_CAS:
            print(f"   {cas:<34} {milliers(par_cas_propre.get(cas, 0)):>9} "
                  f"{_part(par_cas_propre.get(cas, 0), n_propre):>8}")
        print(f"""
   ⚠️ LES PALIERS SONT RECALCULÉS SUR CETTE SOUS-POPULATION, jamais repris de
      la précédente. *Un palier de la population entière peut n'en plus être
      un ici*, et le reprendre ferait lire l'ancienne forme sur la nouvelle.
      Paliers trouvés ici : {', '.join(f'{p:.1f}' for p in paliers_propres) or 'aucun'}
""")
    else:
        print("\n   ⚠️ AUCUN couple sans bonus — la vue propre n'existe pas sur")
        print("      cette population. Ce n'est pas « le bonus ne déplace rien ».")

    print("=" * 78)
    print("   RIEN N'A ÉTÉ ÉCRIT. Les échelles n'ont pas bougé.")
    print("   ⚠️ CETTE MESURE DÉCRIT DES DISTANCES, PAS DES IDENTITÉS. Elle ne dit")
    print("   pas qu'un dossier serait bien apparié si l'écart changeait, et elle")
    print("   n'autorise aucune ouverture des échelles.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
