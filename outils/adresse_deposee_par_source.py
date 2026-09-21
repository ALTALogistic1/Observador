#!/usr/bin/env python3
"""QUELLE ADRESSE CHAQUE SOURCE DÉPOSE — **une mesure, elle n'écrit rien.**

## La question d'Alexandre, du 21 septembre

*« Plusieurs "exclut tous" prononcés par la région de tri portent sur des noms
identiques, dont des sociétés à numéro : #4314 (dossier J0H, retenu J3H), #1721,
#1765, #4318, #1978. Une société à numéro est unique, donc le retenu est le bon,
et c'est l'adresse du dossier qui désigne un autre lieu : un lieu de travail
(EIMT), un chantier (SEAO), un bureau. »*

⚠️ **Si c'est vrai à grande échelle, ça touche le mandat du chantier 4**, qui
pose *« l'adresse comme axe principal, le nom en corroborateur »*.

## Trois instruments, et le deuxième ne demande RIEN au registre

**1. CE QUE LE CODE DÉPOSE.** *Lu par arbre syntaxique* — emprunté à
`outils/adresse_par_connecteur.py`, jamais recopié. Il dit **où** l'adresse
atterrit, **jamais ce qu'elle est**.

**2. ⚠️ LA DISPERSION INTRA-SOURCE — l'instrument qui tranche.** *Une adresse
d'ENTREPRISE ne varie pas d'un signal à l'autre; un lieu d'ÉVÉNEMENT varie.*
**Ni NEQ, ni registre, ni appariement** : la question se pose à l'intérieur d'une
source, sur les dossiers qu'elle a vus plusieurs fois.

⚠️ *Une adresse constante ne PROUVE pas un siège* — une entreprise à un seul
établissement rend la même adresse dans les deux régimes. **Le constat est
asymétrique : la variation réfute « adresse d'entreprise »; la constance ne la
confirme pas.**

**3. LA CONCORDANCE AVEC SON PROPRE NEQ.** *Sur les dossiers DÉJÀ POSÉS, plus
aucune ambiguïté de candidat* : on compare l'adresse déposée par une source à
l'entrée du registre du NEQ que le dossier porte.

⚠️ **Un désaccord a DEUX lectures, et le produit ne les sépare pas** : soit
l'adresse déposée n'est pas celle de l'entreprise *(l'hypothèse d'Alexandre)*,
soit **le NEQ a été posé sur la mauvaise entreprise** *(point 25, la mesure de
justesse, qui n'existe pas)*. **Le compte est le même; les deux suites ne le sont
pas.**

⚠️ **Et le registre lui-même porte le DOMICILE de l'entreprise**
*(`Entreprise.csv`, adresse du domicile)*, pas ses établissements. **Une
entreprise à plusieurs établissements peut donc être en désaccord avec sa propre
adresse d'établissement** — les adresses d'établissement vivent ailleurs
*(`etat_ligne_source`, partition `req_etablissements`)* et ne sont pas lues ici.

⚠️ **RIEN N'EST ÉCRIT. Les échelles ne bougent pas : seuil 92, écart 8.**

Usage, SUR L'HÔTE :
    python3 -m outils.adresse_deposee_par_source
    python3 -m outils.adresse_deposee_par_source --exemples 5
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path

from outils.nombres import milliers

#: Ce que chaque source dépose, **selon la colonne qu'elle lit et le nom que la
#: source lui donne**. ⚠️ *C'est une lecture du connecteur et de l'en-tête du
#: gisement, jamais une mesure* — et la dernière colonne dit ce que le dépôt ne
#: permet PAS d'établir.
CE_QUE_LE_CODE_MONTRE = {
    "eimt": ("colonne « Address » de la Positive LMIA Employers List, "
             "une ligne par (employeur × profession × trimestre)"),
    "seao": ("`parties[].address` du fournisseur dans la publication OCDS — "
             "l'adresse de l'ORGANISATION, pas le lieu du contrat"),
    "investissement_quebec": "aucun champ d'adresse lu",
    "contrats_federaux": "aucun champ d'adresse lu",
    "rob_top_growing": "`ville` et `region` promues en RawSignal",
    "deloitte_fast50": "`ville` et `region` promues en RawSignal",
}

#: Les trois régimes que la dispersion sépare. ⚠️ **Chacun est un RÉSULTAT**, y
#: compris « une seule observation » — qui ne dit rien et doit se compter à part
#: pour ne pas gonfler la constance.
CONSTANTE = "adresse CONSTANTE sur tous les signaux"
VARIABLE = "⚠️ adresse VARIABLE d'un signal à l'autre"
UNE_SEULE = "une seule observation — ne dit rien"
REGIMES = (CONSTANTE, VARIABLE, UNE_SEULE)

#: Le résultat d'une concordance, **dans l'ordre du plus fin au plus grossier**.
AUCUN_NIVEAU = "⚠️ aucun niveau — l'adresse déposée ne concorde PAS"
SANS_ADRESSE = "le dossier ne porte pas d'adresse par cette source"

LARGEUR = 46


def fait_du_signal(champs: dict | None):
    """L'adresse qu'UN signal dépose — **par les lecteurs de la production.**

    *`faits_du_dossier` mélange `Company` et tous les signaux; ici il faut la
    contribution d'UNE source, isolée.* ⚠️ **Les clés sont celles du
    départageur**, empruntées et non recopiées.
    """
    from outils.departageur_adresse import (
        CLES_ADRESSE,
        FaitsDAdresse,
        texte_des_champs,
    )
    from outils.departageurs import codes_postaux, fait_de_la_ville
    from outils.villes_des_signaux import CLES_VILLE, ville_depuis_adresse

    if not champs:
        return None
    texte = texte_des_champs(champs, CLES_ADRESSE)
    ville = next((champs.get(c) for c in CLES_VILLE
                  if isinstance(champs.get(c), str) and champs.get(c)), None)
    if ville is None:
        ville = ville_depuis_adresse(texte)
    faits = FaitsDAdresse(codes_postaux(texte), fait_de_la_ville(ville))
    return faits if (faits.code_postal or faits.ville) else None


def _empreinte(faits) -> str:
    """Ce qui fait que deux adresses sont « la même ». *Le code postal complet
    s'il existe, sinon la région de tri, sinon la ville* — **du plus fin au plus
    grossier**, pour qu'une variation de graphie de rue ne compte pas comme un
    déplacement."""
    for niveau in ("code complet", "region", "ville"):
        fait = (faits.code_complet if niveau == "code complet"
                else faits.region_de_tri if niveau == "region" else faits.ville)
        if fait is not None:
            return f"{niveau}:{sorted(fait.formes)[0]}"
    return "—"


def regime_de(empreintes: set[str]) -> str:
    if len(empreintes) > 1:
        return VARIABLE
    return UNE_SEULE if len(empreintes) < 1 else CONSTANTE


def _part(k: int, n: int) -> str:
    return f"{100 * k / n:.1f} %" if n else "—"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--exemples", type=int, default=0, metavar="N",
                        help="montrer N dossiers à adresse VARIABLE, par source")
    parser.add_argument("--limite", type=int, default=None, help="borner (mise au point)")
    args = parser.parse_args(argv)

    from sqlalchemy import select

    from falkye.db import refuser_si_cible_non_choisie

    code = refuser_si_cible_non_choisie()
    if code:
        return code

    from falkye.db import get_session
    from falkye.models.company import Company
    from falkye.models.req_entry import REQEntry
    from falkye.models.signal import Signal
    from outils.adresse_par_connecteur import (
        champs_promus_par_le_module,
        cles_du_sac_par_le_module,
    )
    from outils.departageur_adresse import (
        NOMS_DES_NIVEAUX,
        departager_ladresse,
        faits_du_candidat,
    )
    from outils.departageurs import DEPARTAGE

    session = get_session()
    try:
        print("=" * 78)
        print("QUELLE ADRESSE CHAQUE SOURCE DÉPOSE — une MESURE")
        print("=" * 78)
        print("""
⚠️ LA QUESTION, ET POURQUOI ELLE TOUCHE LE MANDAT

   Le mandat du chantier 4 pose « l'adresse comme axe principal, le nom en
   corroborateur ». Si une source dépose le LIEU D'UN ÉVÉNEMENT plutôt que
   l'adresse d'une entreprise, l'axe principal compare deux choses qui n'ont
   aucune raison de concorder.

⚠️ CE QUE LA DISPERSION PROUVE, ET CE QU'ELLE NE PROUVE PAS

   La VARIATION réfute « adresse d'entreprise ». La CONSTANCE ne la
   confirme pas : une entreprise à un seul établissement rend la même
   adresse dans les deux régimes. Le constat est asymétrique.

⚠️ RIEN N'EST ÉCRIT.
""")

        # ---- 1. CE QUE LE CODE DÉPOSE -------------------------------------
        print("-" * 78)
        print("1. CE QUE LE CODE DÉPOSE — lu par arbre syntaxique")
        print("-" * 78 + "\n")
        for source, lecture in CE_QUE_LE_CODE_MONTRE.items():
            chemin = Path("falkye/sources") / f"{source}.py"
            if not chemin.exists():
                continue
            promus = sorted(champs_promus_par_le_module(chemin))
            sac = sorted(k for k in cles_du_sac_par_le_module(chemin)
                         if any(m in k for m in ("adresse", "ville", "region",
                                                 "postal", "lieu", "province")))
            print(f"   {source}")
            print(f"      promu en RawSignal : {', '.join(promus) or '—'}")
            print(f"      clés du sac        : {', '.join(sac) or '—'}")
            print(f"      ce que c'est       : {lecture}")
        print("""
   ⚠️ CE TABLEAU DIT OÙ L'ADRESSE ATTERRIT, JAMAIS CE QU'ELLE EST. La
      nature se lit dans l'en-tête du gisement, et se VÉRIFIE par la
      dispersion ci-dessous.
""")

        # ---- 2. LA DISPERSION INTRA-SOURCE --------------------------------
        requete = select(Signal.company_id, Signal.source_id, Signal.champs)
        if args.limite:
            requete = requete.limit(args.limite)
        par_couple: dict[tuple[int, str], set[str]] = defaultdict(set)
        signaux: Counter = Counter()
        for company_id, source_id, champs in session.execute(
                requete.execution_options(yield_per=2000)):
            signaux[(company_id, source_id)] += 1
            faits = fait_du_signal(champs)
            if faits is not None:
                par_couple[(company_id, source_id)].add(_empreinte(faits))

        par_source: dict[str, Counter] = defaultdict(Counter)
        variables: dict[str, list] = defaultdict(list)
        for (company_id, source_id), n_sig in signaux.items():
            if n_sig < 2:
                continue
            empreintes = par_couple.get((company_id, source_id), set())
            regime = regime_de(empreintes)
            par_source[source_id][regime] += 1
            if regime == VARIABLE:
                variables[source_id].append((company_id, sorted(empreintes)))

        print("-" * 78)
        print("2. L'ADRESSE VARIE-T-ELLE D'UN SIGNAL À L'AUTRE?")
        print("-" * 78)
        print("\n   Sur les dossiers vus AU MOINS DEUX FOIS par la même source.\n")
        print(f"   {'':<{LARGEUR}} {'dossiers':>9} {'constante':>10} "
              f"{'VARIABLE':>10} {'muette':>8}")
        for source_id in sorted(par_source, key=lambda s: -sum(par_source[s].values())):
            compte = par_source[source_id]
            n = sum(compte.values())
            print(f"   {source_id:<{LARGEUR}} {milliers(n):>9} "
                  f"{milliers(compte[CONSTANTE]):>10} "
                  f"{milliers(compte[VARIABLE]):>10} "
                  f"{milliers(compte[UNE_SEULE]):>8}   "
                  f"{_part(compte[VARIABLE], n)}")
        if not par_source:
            print("   (aucun dossier vu deux fois par une même source)")

        if args.exemples:
            for source_id, lot in variables.items():
                print(f"\n   « {source_id} » — {min(args.exemples, len(lot))} "
                      f"dossiers à adresse variable sur {milliers(len(lot))}")
                for company_id, empreintes in lot[:args.exemples]:
                    print(f"      #{company_id}   {' · '.join(empreintes[:4])}")

        # ---- 3. LA CONCORDANCE AVEC SON PROPRE NEQ ------------------------
        poses = {
            cid: neq for cid, neq in session.execute(
                select(Company.id, Company.neq).where(Company.neq.is_not(None)))
        }
        entrees: dict[str, REQEntry] = {}
        if poses:
            for entree in session.execute(
                    select(REQEntry).where(REQEntry.neq.in_(list(poses.values())))
            ).scalars():
                entrees[entree.neq] = entree

        concordance: dict[str, Counter] = defaultdict(Counter)
        for company_id, source_id, champs in session.execute(
                select(Signal.company_id, Signal.source_id, Signal.champs)
                .execution_options(yield_per=2000)):
            neq = poses.get(company_id)
            if neq is None or neq not in entrees:
                continue
            faits = fait_du_signal(champs)
            if faits is None:
                concordance[source_id][SANS_ADRESSE] += 1
                continue
            departage = departager_ladresse(
                faits, [faits_du_candidat(entrees[neq])])
            concordance[source_id][
                departage.niveau if departage.issue == DEPARTAGE and departage.niveau
                else AUCUN_NIVEAU] += 1

        print("\n" + "-" * 78)
        print("3. L'ADRESSE DÉPOSÉE CONCORDE-T-ELLE AVEC LE NEQ DU DOSSIER?")
        print("-" * 78)
        print("""
   Sur les dossiers QUI PORTENT DÉJÀ un NEQ — plus aucune ambiguïté de
   candidat. Un signal, une ligne.

   ⚠️ UN DÉSACCORD A DEUX LECTURES, ET LE PRODUIT NE LES SÉPARE PAS :
      l'adresse déposée n'est pas celle de l'entreprise, OU le NEQ a été
      posé sur la mauvaise entreprise (point 25). Même compte, deux suites.

   ⚠️ ET LE REGISTRE PORTE LE DOMICILE, pas les établissements. Une
      entreprise à plusieurs établissements peut être en désaccord avec sa
      propre adresse d'établissement.
""")
        colonnes = list(NOMS_DES_NIVEAUX) + [AUCUN_NIVEAU, SANS_ADRESSE]
        for source_id in sorted(concordance, key=lambda s: -sum(concordance[s].values())):
            compte = concordance[source_id]
            n = sum(compte.values())
            avec = n - compte[SANS_ADRESSE]
            print(f"\n   {source_id}   —   {milliers(n)} signaux, "
                  f"{milliers(avec)} portant une adresse")
            for colonne in colonnes:
                if not compte[colonne]:
                    continue
                base = n if colonne == SANS_ADRESSE else avec
                print(f"      {colonne:<{LARGEUR}} {milliers(compte[colonne]):>9} "
                      f"{_part(compte[colonne], base):>8}")

        print("\n" + "=" * 78)
        print("   RIEN N'A ÉTÉ ÉCRIT. Les échelles n'ont pas bougé.")
        print("   ⚠️ La VARIATION réfute « adresse d'entreprise »;")
        print("      la CONSTANCE ne la confirme pas.")
        print("=" * 78)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
