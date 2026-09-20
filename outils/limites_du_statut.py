#!/usr/bin/env python3
"""Les DEUX limites du mécanisme du statut — les `ni`, et le restant moins bien
scoré.

## Le motif, tiré de 32 paires lues

**Le mécanisme tient sur les entreprises ordinaires** : les égalités strictes
sont des réimmatriculations au même endroit — *`AUTOROULE INC.` à Val-d'Or,
trois entrées, même code postal, même secteur, une seule vivante.*

⚠️ **Il échoue sur les entités publiques.** *Cinq des huit divergences lues en
sont* — CIUSSS, commissions et centres de services scolaires, une ville. **Elles
portent `ni`, donc « ne garder que les immatriculées » les VIDE.** Et
`Ville de Bedford` garde *l'Association des pompiers volontaires* en écartant la
ville.

⚠️ **Et un cas contre le mécanisme, à ne pas noyer** : *Les Ruchers du Roi
Bourdon* — l'exclusion garde un candidat à **88,2** et écarte celui à **95**. *Le
restant semble le bon, même nom, même code postal.* **Mais le mécanisme a retenu
un candidat MOINS BIEN SCORÉ, et rien ne dit que ça marche toujours.**

## ⚠️ CE QUE CETTE MESURE NE FERA PAS — à lire avant tout chiffre

**Classer une entité en publique ou privée.** ⚠️ **C'est D28, une décision
ouverte**, et D27 — *trouver un registre officiel des entités publiques
québécoises* — est son préalable. **Le produit n'a rien pour les reconnaître, et
le corpus le dit déjà.**

⚠️ **Le précédent est dans le dépôt** : `outils/donneurs_douvrage.py` **compte et
ne classe pas**, et sa docstring nomme exactement la tentation d'ici —

> *« Un outil qui appliquerait ici une heuristique de noms (« Ville de »,
> « CISSS », « Ministère ») produirait une classification qui aurait l'air d'une
> mesure, et personne ne saurait plus qu'elle a été devinée. »*

**Les noms lus dans les paires sont précisément ceux-là.** *La tentation est
nommée pour être refusée, pas contournée.*

## Ce que la mesure rend à la place

**Des FAITS que les candidats `ni` portent** — leur **préfixe de NEQ** et leur
**secteur** — plus le **croisement préfixe × statut sur tout le miroir**, qui dit
si `88` et `ni` sont la même chose.

⚠️ **Ni le préfixe ni le secteur ne sont un critère de « public ».** *Ils sont la
matière de D27, pas son remplaçant.* **Le guide du Registraire documente `11`,
`22`, `33`; `88` n'y est pas** *(relevé par `profil_des_absents_req`, le 16
septembre)* — et ce qu'il désigne n'est écrit nulle part.

⚠️ **AUCUNE ÉCRITURE. Les échelles ne bougent pas : seuil 92, écart 8.**

Usage, SUR L'HÔTE :
    python3 -m outils.limites_du_statut
    python3 -m outils.limites_du_statut --secteurs 20
"""
from __future__ import annotations

import argparse
from collections import Counter

from outils.nombres import milliers
from outils.statut_sur_les_egalites import (
    ECARTER_RADIEES,
    GARDER_IMMATRICULEES,
    IMMATRICULEE,
    LES_DEUX_EXCLUSIONS,
    RADIEE,
)
from outils.paires_du_statut import restants_apres

#: Les préfixes que le guide du Registraire documente. ⚠️ **`88` n'y est pas**,
#: et ce qu'il désigne n'est écrit nulle part — *relevé par
#: `outils/profil_des_absents_req.py` le 2026-09-16.*
PREFIXES_DOCUMENTES = ("11", "22", "33")

#: La décision ouverte qui fournirait un critère, et son préalable.
DECISIONS_OUVERTES = (
    ("D27", "Trouver un registre officiel des entités publiques québécoises"),
    ("D28", "Règle de classement d'une entité en publique ou privée"),
)

#: ⚠️ **Nommée pour être refusée.** *Ce sont les mots que les paires lues
#: contiennent, et `outils/donneurs_douvrage.py` a déjà refusé de s'en servir.*
LA_TENTATION = (
    "une heuristique de noms — « Ville de », « CIUSSS », « Commission scolaire », "
    "« Centre de services » — produirait une classification qui aurait l'air "
    "d'une mesure, et personne ne saurait plus qu'elle a été devinée"
)


def _part(k: int, n: int) -> str:
    return f"{100 * k / n:.1f} %" if n else "—"


def prefixe_du_neq(neq: str | None) -> str:
    """Les deux premiers chiffres. *Le guide dit que c'est une forme juridique.*"""
    return (neq or "")[:2] or "(vide)"


def ni_parmi(groupe) -> list:
    """Les candidats qui ne sont **ni immatriculés ni radiés.**

    ⚠️ *`ni` et `ai` gardent leur code brut* — voir
    `falkye/sources/req.py::_decoder_statut_reel`. **Ce sont eux qui séparent les
    deux exclusions.**
    """
    return [m for m in groupe if m.entry.statut not in (IMMATRICULEE, RADIEE)]


def moins_bien_score(groupe, meilleur_score: float, exclusion: str):
    """Le restant unique **strictement moins bien scoré que le meilleur**, ou
    `None`.

    ⚠️ *Une ÉGALITÉ au sommet n'est pas « moins bien scoré »* : plusieurs
    candidats partagent alors la première place, et le restant en est un.
    """
    restes = restants_apres(groupe, exclusion)
    if len(restes) != 1:
        return None
    seul = restes[0]
    return seul if seul.score < meilleur_score else None


def croisement_prefixe_statut(db_session) -> list[tuple[str, str, int]]:
    """`(préfixe, statut, compte)` sur **tout le miroir**, en une requête.

    ⚠️ *C'est ce croisement qui dit si `88` et `ni` sont la même chose* — et la
    réponse est un fait, pas un critère.
    """
    from sqlalchemy import func, select

    from falkye.models.req_entry import REQEntry

    prefixe = func.substr(REQEntry.neq, 1, 2)
    lignes = db_session.execute(
        select(prefixe, REQEntry.statut, func.count())
        .group_by(prefixe, REQEntry.statut)
        .order_by(func.count().desc())
    ).all()
    return [(p or "(vide)", s or "(vide)", k) for p, s, k in lignes]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--secteurs", type=int, default=15, metavar="N",
                        help="combien de secteurs détailler chez les candidats `ni`")
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
    from outils.departageur_adresse import concurrents_de
    from outils.reresolution_neq import _resoudre_une

    print("=" * 78)
    print("LES DEUX LIMITES DU STATUT — les `ni`, et le restant moins bien scoré")
    print("=" * 78)
    print(f"""
⚠️ CE QUE CETTE MESURE NE FERA PAS — avant tout chiffre

   CLASSER UNE ENTITÉ EN PUBLIQUE OU PRIVÉE. C'est D28, une décision
   ouverte, et D27 — trouver un registre officiel des entités publiques
   québécoises — en est le préalable. LE PRODUIT N'A RIEN POUR LES
   RECONNAÎTRE, et le corpus le dit déjà.

   LE PRÉCÉDENT EST DANS LE DÉPÔT. `outils/donneurs_douvrage.py` compte et
   NE CLASSE PAS, et sa docstring nomme exactement la tentation d'ici :
   {LA_TENTATION}.

   Les noms lus dans les paires sont précisément ceux-là. La tentation est
   nommée pour être refusée, pas contournée.

   AUCUNE ÉCRITURE. Les échelles ne bougent pas : seuil {SEUIL_RESOLUTION_CONFIANTE:.0f}, écart {SEUIL_AMBIGUITE_ECART_MIN:.0f}.
""")

    session = get_session()
    try:
        requete = select(Company).where(Company.neq.is_(None)).order_by(Company.id)
        if args.limite:
            requete = requete.limit(args.limite)
        restants = list(session.execute(requete).scalars().all())
        if not restants:
            print("   Aucun restant à mesurer.")
            print("   RIEN N'A ÉTÉ ÉCRIT. Les échelles n'ont pas bougé.")
            return 0

        print(f"… rejeu de la résolution sur {milliers(len(restants))} restants, "
              f"par le chemin de production", flush=True)
        n_amb = 0
        avec_ni = 0
        ni_prefixes: Counter = Counter()
        ni_secteurs: Counter = Counter()
        ni_statuts: Counter = Counter()
        ni_par_position: Counter = Counter()
        moins_bien: dict[str, int] = {e: 0 for e in LES_DEUX_EXCLUSIONS}
        ecarts_du_moins_bien: Counter = Counter()
        for i, company in enumerate(restants, 1):
            if args.pas and i % args.pas == 0:
                print(f"   … {milliers(i)} / {milliers(len(restants))}", flush=True)
            _neq, matches = _resoudre_une(session, company)
            if famille_de(matches) != "ambigu":
                continue
            n_amb += 1
            groupe = concurrents_de(matches)
            les_ni = ni_parmi(groupe)
            if les_ni:
                avec_ni += 1
                # ⚠️ Le `ni` est-il le MIEUX scoré du lot? C'est ce qui décide
                # si l'exclusion stricte écarte le candidat de tête.
                ni_par_position["le mieux scoré du lot"] += (
                    1 if any(m.score == matches[0].score for m in les_ni) else 0)
            for m in les_ni:
                ni_statuts[m.entry.statut] += 1
                ni_prefixes[prefixe_du_neq(m.entry.neq)] += 1
                ni_secteurs[m.entry.secteur_code or "(vide)"] += 1
            for exclusion in LES_DEUX_EXCLUSIONS:
                seul = moins_bien_score(groupe, matches[0].score, exclusion)
                if seul is not None:
                    moins_bien[exclusion] += 1
                    if exclusion == GARDER_IMMATRICULEES:
                        ecarts_du_moins_bien[round(matches[0].score - seul.score, 1)] += 1

        print(f"\n   AMBIGUS : {milliers(n_amb)}")
        if not n_amb:
            print("   Aucun ambigu — rien à ventiler, et ce n'est pas « 0 ».")
            print("   RIEN N'A ÉTÉ ÉCRIT. Les échelles n'ont pas bougé.")
            return 0

        # ---- 1. LES AMBIGUS QUI PORTENT UN `ni` ---------------------------
        print("\n" + "-" * 78)
        print("1. LES AMBIGUS QUI PORTENT AU MOINS UN CANDIDAT NI IMMATRICULÉ NI RADIÉ")
        print("-" * 78)
        print(f"\n   {'ambigus portant au moins un tel candidat':<52} "
              f"{milliers(avec_ni):>9} {_part(avec_ni, n_amb):>8}")
        print(f"   {'dont ce candidat est le MIEUX scoré du lot':<52} "
              f"{milliers(ni_par_position['le mieux scoré du lot']):>9} "
              f"{_part(ni_par_position['le mieux scoré du lot'], avec_ni):>8}")
        print(f"\n   statuts de ces candidats — " + "  ·  ".join(
            f"{s} {milliers(k)}" for s, k in ni_statuts.most_common()) or "(aucun)")
        print("""
   ⚠️ LA SECONDE LIGNE EST CELLE QUI COÛTE. Quand le candidat non
      immatriculé est le mieux scoré, « ne garder que les immatriculées »
      écarte le candidat de tête — et c'est ce qui vide les lots des
      entités publiques lues dans les paires.
""")

        # ---- 2. CE QUE CES CANDIDATS PORTENT ------------------------------
        print("-" * 78)
        print("2. CE QUE CES CANDIDATS PORTENT — des FAITS, jamais des critères")
        print("-" * 78)
        total_ni = sum(ni_prefixes.values())
        print(f"\n   préfixe de NEQ — {milliers(total_ni)} candidat(s)\n")
        for prefixe, k in ni_prefixes.most_common():
            marque = "" if prefixe in PREFIXES_DOCUMENTES else "   ⚠️ hors 11/22/33"
            print(f"      {prefixe:<8} {milliers(k):>9} {_part(k, total_ni):>8}{marque}")
        print(f"\n   secteur d'activité du registre\n")
        for secteur, k in ni_secteurs.most_common(args.secteurs):
            print(f"      {secteur:<8} {milliers(k):>9} {_part(k, total_ni):>8}")
        reste = len(ni_secteurs) - min(args.secteurs, len(ni_secteurs))
        if reste > 0:
            print(f"      {'…':<8} répartis sur {milliers(reste)} autres secteurs")
        print("""
   ⚠️ NI LE PRÉFIXE NI LE SECTEUR NE SONT UN CRITÈRE DE « PUBLIC ». Ce sont
      la matière de D27, pas son remplaçant. Le guide du Registraire
      documente 11, 22 et 33; ce que 88 désigne n'est écrit nulle part —
      relevé par `profil_des_absents_req.py` le 16 septembre.
""")

        # ---- 3. LE CROISEMENT SUR LE MIROIR -------------------------------
        print("-" * 78)
        print("3. PRÉFIXE × STATUT SUR TOUT LE MIROIR — `88` et `ni`, même chose?")
        print("-" * 78)
        croise = croisement_prefixe_statut(session)
        total_m = sum(k for _p, _s, k in croise)
        print(f"\n   {milliers(total_m)} entrée(s) au miroir\n")
        print(f"      {'préfixe':<9} {'statut':<16} {'entrées':>12} {'part':>8}")
        for prefixe, statut, k in croise[:20]:
            marque = "" if prefixe in PREFIXES_DOCUMENTES else "   ⚠️ hors 11/22/33"
            print(f"      {prefixe:<9} {statut:<16} {milliers(k):>12} "
                  f"{_part(k, total_m):>8}{marque}")
        if len(croise) > 20:
            print(f"      {'…':<9} {'':<16} répartis sur {milliers(len(croise) - 20)} "
                  f"autres couples")
        print("""
   ⚠️ C'EST UN FAIT, PAS UN CRITÈRE. Si un préfixe et un statut coïncident
      parfaitement, ça dit comment le registre est bâti — jamais ce qu'une
      entité EST. La coïncidence se lit; elle ne se promeut pas en règle.
""")

        # ---- 4. CE QUE LE PRODUIT N'A PAS ---------------------------------
        print("-" * 78)
        print("4. RECONNAÎTRE UNE ENTITÉ PUBLIQUE — ce que le produit n'a pas")
        print("-" * 78)
        print("""
   RIEN. Et ce n'est pas une lacune découverte ici : le corpus la porte
   déjà comme deux décisions ouvertes, datées et déclenchées.
""")
        for numero, titre in DECISIONS_OUVERTES:
            print(f"      {numero}   {titre}")
        print(f"""
   ⚠️ DONC LA SECONDE MOITIÉ DE LA QUESTION SE RÉPOND PAR LÀ. Combien de
      ces dossiers sont des entités publiques reconnaissables? Le produit
      n'a pas de quoi les reconnaître, et le dire EST le résultat.

   ⚠️ {LA_TENTATION}.
      `outils/donneurs_douvrage.py` l'a déjà refusée pour la même raison.
""")
        return _moins_bien(n_amb, moins_bien, ecarts_du_moins_bien)
    finally:
        session.close()


def _moins_bien(n_amb: int, moins_bien: dict[str, int],
                ecarts: Counter) -> int:
    """Le restant unique **moins bien scoré que le meilleur.**"""
    print("-" * 78)
    print("5. LE RESTANT MOINS BIEN SCORÉ QUE LE MEILLEUR")
    print("-" * 78)
    print("""
   Le cas des Ruchers du Roi Bourdon : l'exclusion garde un candidat à
   88,2 et écarte celui à 95. Le restant semblait le bon — mais le
   mécanisme a retenu un candidat MOINS BIEN SCORÉ, et rien ne dit que ça
   marche toujours.
""")
    print(f"   {'':<44} {'dossiers':>9} {'part':>8}")
    for exclusion in LES_DEUX_EXCLUSIONS:
        k = moins_bien[exclusion]
        print(f"   {exclusion:<44} {milliers(k):>9} {_part(k, n_amb):>8}")
    if ecarts:
        total_e = sum(ecarts.values())
        print(f"\n   l'écart entre le meilleur et le restant — "
              f"« {GARDER_IMMATRICULEES} »\n")
        for ecart, k in sorted(ecarts.items()):
            print(f"      {ecart:>6.1f} {milliers(k):>9} {_part(k, total_e):>8}")
    print("""
   ⚠️ UNE ÉGALITÉ AU SOMMET N'EST PAS COMPTÉE ICI. Plusieurs candidats y
      partagent la première place, et le restant en est un : le mécanisme
      n'a contredit aucun gagnant.

   ⚠️ ET CE COMPTE NE DIT PAS QUE CES DOSSIERS SONT MAL APPARIÉS. Il dit
      que deux instruments se contredisent sur eux — le score désigne
      l'un, le statut l'autre. Lequel a raison ne se lit pas dans un
      compte, et il se lit une paire à la fois.
""")
    print("=" * 78)
    print("   RIEN N'A ÉTÉ ÉCRIT. Les échelles n'ont pas bougé.")
    print("   ⚠️ AUCUNE ENTITÉ N'A ÉTÉ CLASSÉE. Le produit n'a pas de quoi le faire,")
    print("   et l'inventer ici serait prendre la décision que personne n'a prise.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
