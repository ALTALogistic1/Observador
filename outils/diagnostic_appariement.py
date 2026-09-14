"""Pourquoi les noms échouent — le préalable des chantiers 3 et 4, jamais fait.

**Le fait qui justifie cet outil.** `outils/apport_ville.py` a mesuré que **404 des 437
entreprises décidables restent non résolues même avec la ville**. *Donc le blocage n'est
pas de départager entre deux candidats : c'est qu'aucun candidat ne sort.* **Mais
« aucun candidat ne sort » recouvre deux échecs opposés**, et personne ne les avait
séparés.

    aucun candidat RÉCUPÉRÉ     la requête n'a rien rendu à scorer
    candidats trop FAIBLES      des candidats existent, aucun n'atteint 92
    AMBIGU                      le premier atteint 92, mais le second est trop proche

**Ils appellent trois correctifs différents**, et c'est pour ça que la distribution
décide. *Un meilleur score ne sert à rien si la récupération ne rend rien; un meilleur
index ne sert à rien si le score est le problème.*

⚠️ **Ce que le code dit d'avance, et que la mesure doit confirmer ou infirmer.** La
récupération est **ancrée sur la TÊTE de la chaîne** — préfixe du premier mot, puis
repli sur les six premiers caractères *(`req.candidats_par_nom`)*. **Une différence en
tête n'abaisse pas le score : elle empêche le candidat d'être récupéré du tout.**

**PORTÉE** *(guide d'ingénierie — un instrument déclare ce qu'il ne regarde pas)* :

- **Il ne lit que les `Company` SANS NEQ** de la base durable. *Une entreprise résolue à
  tort ne sera pas vue : cet outil mesure l'échec, jamais la justesse.*
- **Il rejoue la résolution contre le MIROIR LOCAL** — `req_entries`. *Donc il ne coûte
  aucune lecture facturée, et il ne vaut que ce que vaut l'état du miroir.*
- **Il emprunte les fonctions du moteur** — `candidats_par_nom`, `resolve_neq_by_name`,
  `neq_retenu`. *Jamais une copie : une copie mesurerait sa propre règle.*
- ⚠️ **Le rejeu N'EST PAS la production, et voici exactement où ils diffèrent.** *La
  production résout à chaque signal, avec le nom ET la ville DE CE SIGNAL. Cet outil
  rejoue UNE fois par entreprise, avec le nom et la ville ACCUMULÉS sur la fiche.*
  **Deux conséquences opposées** : la ville accumulée peut donner un bonus que la
  production n'avait pas à ce moment-là *(le rejeu devient optimiste — `--sans-ville`
  le teste)*; le nom accumulé est celui du PREMIER signal, alors que la production a
  aussi essayé ceux des suivants *(le rejeu devient pessimiste)*. **Aucun des deux
  n'est corrigeable sans rejouer les signaux un par un, ce que cet outil ne fait pas.**
- **Le diagnostic de la DIFFÉRENCE est une heuristique, pas une vérité.** *Il propose
  ce qui distingue le nom détecté des noms du registre; il ne prouve pas la cause.*

    python outils/diagnostic_appariement.py                 # 300 entreprises
    python outils/diagnostic_appariement.py --toutes
    python outils/diagnostic_appariement.py --exemples 15   # détail des sans-candidat

Sur l'hôte, l'environnement et l'identité du service :

    sudo bash -c 'set -a; . /etc/falkye/falkye.env; set +a
      exec runuser -u falkye -- /opt/falkye/venv/bin/python outils/diagnostic_appariement.py'
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter

#: Les mots de tête qui ne portent aucune information distinctive. Une chaîne qui
#: commence par l'un d'eux voit la récupération par préfixe partir sur un mot commun
#: à des dizaines de milliers d'entrées.
TETES_NON_SIGNIFICATIVES = {"le", "la", "les", "l", "les", "de", "du", "des", "groupe",
                            "entreprise", "entreprises", "construction", "constructions",
                            "service", "services", "gestion", "societe", "compagnie", "cie"}

#: Les mots de forme juridique. Présents d'un côté et absents de l'autre, ils ajoutent
#: du bruit au score sans rien distinguer.
FORMES_JURIDIQUES = {"inc", "ltee", "ltd", "limitee", "limited", "senc", "sencrl",
                     "srl", "corp", "corporation", "co", "enr", "sec", "spa"}

ECHANTILLON_DEFAUT = 300


def mots_significatifs(nom_norm: str) -> list[str]:
    """Les mots qui portent de l'information — ni forme juridique, ni mot de tête vide."""
    return [m for m in nom_norm.split()
            if m not in FORMES_JURIDIQUES and m not in TETES_NON_SIGNIFICATIVES and len(m) > 1]


def est_numero(nom_norm: str) -> bool:
    """« 9231 4567 quebec inc » — une société à dénomination numérique.

    *Elle existe au registre sous ce numéro, mais les sources la nomment presque
    toujours par son enseigne : aucun pont ne peut exister sur le nom seul.*
    """
    premier = nom_norm.split(" ")[0] if nom_norm else ""
    return premier.isdigit() and len(premier) >= 4


def classer_difference(nom_norm: str, voisins: list[str]) -> str:
    """Pourquoi ce nom n'a rien récupéré — proposition, jamais verdict."""
    if est_numero(nom_norm):
        return "dénomination numérique (9xxx…) — la source la nomme par son enseigne"
    premier = nom_norm.split(" ")[0] if nom_norm else ""
    if not premier:
        return "nom vide après normalisation"
    if premier in TETES_NON_SIGNIFICATIVES:
        return "tête non significative — la récupération part sur un mot très commun"
    if not voisins:
        return "aucun nom voisin dans le miroir — nom absent du registre sous cette forme"
    mots = set(mots_significatifs(nom_norm))
    for v in voisins:
        if mots and mots.issubset(set(v.split())):
            return "mots présents dans un nom du registre, mais PAS EN TÊTE"
    return "nom voisin trouvé, mots distincts — enseigne, filiale ou coentreprise probable"


def voisins_par_mot_long(db_session, nom_norm: str, limite: int = 5) -> list[str]:
    """Ce que le miroir porte autour du mot le plus long du nom détecté.

    *La récupération du moteur part de la TÊTE; celle-ci part du mot le plus
    distinctif. L'écart entre les deux est précisément ce qu'on cherche à voir.*
    """
    from sqlalchemy import select

    from falkye.models.req_entry import REQEntry

    mots = sorted(mots_significatifs(nom_norm), key=len, reverse=True)
    if not mots:
        return []
    return [
        r.nom_normalise
        for r in db_session.execute(
            select(REQEntry).where(REQEntry.nom_normalise.contains(mots[0])).limit(limite)
        ).scalars().all()
    ]


def ventilation_non_resolues(db_session, ids: list[int]) -> None:
    """D'où viennent les entreprises qui échouent — par source, et en exclusivité.

    **Le nombre qui compte est l'EXCLUSIF** *(même règle que
    `outils/provenance_entreprises.py`)* : une entreprise vue par une seule source
    disparaîtrait avec elle. **Une source dont les entreprises ne sont résolubles par
    aucun correctif — parce qu'elles ne sont pas immatriculées au Québec — découpe le
    mur en deux : ce qui est réparable, et ce qui n'est pas là.**
    """
    from collections import defaultdict

    from sqlalchemy import select

    from falkye.models.signal import Signal

    if not ids:
        return
    par_company = defaultdict(set)
    for cid, sid in db_session.execute(
        select(Signal.company_id, Signal.source_id).where(Signal.company_id.in_(ids))
    ).all():
        par_company[cid].add(sid)
    touchees, exclusives = Counter(), Counter()
    sans_signal = len(ids) - len(par_company)
    for sources in par_company.values():
        for sid in sources:
            touchees[sid] += 1
        if len(sources) == 1:
            exclusives[next(iter(sources))] += 1

    print("\n" + "=" * 78)
    print("D'OÙ VIENNENT LES NON RÉSOLUES — et laquelle en est la seule source")
    print("=" * 78)
    print(f"\n{'source':<26}{'touchées':>10}{'EXCLUSIVES':>12}{'part excl.':>12}")
    total = len(ids)
    for sid in sorted(touchees, key=lambda s: -exclusives.get(s, 0)):
        e = exclusives.get(sid, 0)
        print(f"{sid:<26}{touchees[sid]:>10}{e:>12}{100*e/total:>11.1f}%")
    if sans_signal:
        print(f"\n   ⚠️ {sans_signal} entreprise(s) sans AUCUN signal rattaché — à expliquer.")
    print("\n   « EXCLUSIVES » = vues par cette source et par aucune autre.")
    print("   C'est le seul nombre qui dise ce qui disparaîtrait si la source partait.")


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--toutes", action="store_true", help="toutes les non résolues (défaut : un échantillon)")
    parseur.add_argument("--echantillon", type=int, default=ECHANTILLON_DEFAUT)
    parseur.add_argument("--exemples", type=int, default=10, help="sans-candidat détaillés (défaut 10)")
    parseur.add_argument("--sans-ville", action="store_true",
                         help="rejouer SANS le bonus de ville (+5) — teste si les « résolubles » en dépendent")
    args = parseur.parse_args(argv)

    from falkye.db import bases_sur_repli, cible_annoncee

    print(cible_annoncee())
    if bases_sur_repli():
        print(
            "\nREFUS — aucune cible n'a été choisie : "
            f"{', '.join(bases_sur_repli())} absente(s).\n"
            "  « Aucune entreprise non résolue » sur une base vide se lit comme un succès.\n"
            "  Sur l'hôte : set -a; . /etc/falkye/falkye.env; set +a",
            file=sys.stderr,
        )
        return 2

    from sqlalchemy import select

    from falkye.db import get_session
    from falkye.models.company import Company
    from falkye.sources.column_mapping import normaliser
    from falkye.sources.req import candidats_par_nom, resolve_neq_by_name
    from falkye.resolution import SEUIL_AMBIGUITE_ECART_MIN, SEUIL_RESOLUTION_CONFIANTE

    # UNE session, DEUX moteurs : SQLAlchemy route par métadonnée (falkye/db.py).
    # `Company` part vers la base durable, `REQEntry` vers le miroir local, sans
    # que cet outil ait à le savoir.
    session = get_session()
    miroir = session
    try:
        requete = select(Company).where(Company.neq.is_(None))
        if not args.toutes:
            requete = requete.limit(args.echantillon)
        entreprises = session.execute(requete).scalars().all()
        total_non_resolues = session.execute(
            select(Company).where(Company.neq.is_(None))
        ).scalars().all()

        print("\nPORTÉE : les Company SANS NEQ, rejouées contre le MIROIR LOCAL.")
        print("         Aucune lecture facturée. L'outil mesure l'échec, jamais la justesse.")
        print(f"\nentreprises sans NEQ en base : {len(total_non_resolues)}")
        print(f"examinées ici                : {len(entreprises)}"
              + ("  (toutes)" if args.toutes else f"  (échantillon des {args.echantillon} premières)"))
        if not args.toutes and len(total_non_resolues) > len(entreprises):
            print("         ⚠️ échantillon PRIS DANS L'ORDRE DE LA TABLE, pas au hasard —")
            print("            provenance déclarée : ce n'est pas un tirage représentatif.")

        if not entreprises:
            print("\n⚠️ AUCUNE entreprise sans NEQ. Ce n'est pas forcément un succès :")
            print("   vérifier d'abord que la base porte des entreprises.")
            return 0

        familles = Counter()
        differences = Counter()
        dates_resolubles: list = []
        sans_candidat: list[tuple[str, str, list[str]]] = []
        for company in entreprises:
            nom = company.nom_detecte or ""
            nom_norm = normaliser(nom)
            if not nom_norm:
                familles["nom vide après normalisation"] += 1
                continue
            candidats = candidats_par_nom(miroir, nom_norm)
            if not candidats:
                familles["aucun candidat RÉCUPÉRÉ"] += 1
                voisins = voisins_par_mot_long(miroir, nom_norm)
                motif = classer_difference(nom_norm, voisins)
                differences[motif] += 1
                if len(sans_candidat) < args.exemples:
                    sans_candidat.append((nom, motif, voisins[:3]))
                continue
            matches = resolve_neq_by_name(
                miroir, nom, ville=None if args.sans_ville else company.ville
            )
            if not matches:
                familles["candidats récupérés, aucun scoré"] += 1
                continue
            top = matches[0].score
            second = matches[1].score if len(matches) > 1 else 0.0
            if top < SEUIL_RESOLUTION_CONFIANTE:
                familles[f"candidats trop FAIBLES (top < {SEUIL_RESOLUTION_CONFIANTE:.0f})"] += 1
            elif top - second < SEUIL_AMBIGUITE_ECART_MIN and len(matches) > 1:
                familles[f"AMBIGU (écart < {SEUIL_AMBIGUITE_ECART_MIN:.0f})"] += 1
            else:
                familles["RÉSOLUBLE maintenant — à expliquer"] += 1
                if company.first_detected_at:
                    dates_resolubles.append(company.first_detected_at)

        n = sum(familles.values())
        print("\n" + "=" * 78)
        print("POURQUOI CHACUNE ÉCHOUE")
        print("=" * 78)
        for libelle, k in familles.most_common():
            print(f"   {libelle:52} {k:>5}  {100*k/n:>5.1f} %")

        if differences:
            print("\n" + "=" * 78)
            print("PARMI LES « AUCUN CANDIDAT RÉCUPÉRÉ » — ce qui diffère (heuristique)")
            print("=" * 78)
            m = sum(differences.values())
            for libelle, k in differences.most_common():
                print(f"   {libelle:60} {k:>5}  {100*k/m:>5.1f} %")

        if sans_candidat:
            print("\n" + "=" * 78)
            print("EXEMPLES — le nom détecté, et ce que le miroir porte autour de son mot le plus long")
            print("=" * 78)
            for nom, motif, voisins in sans_candidat:
                print(f"\n   détecté : {nom[:66]}")
                print(f"   motif   : {motif}")
                for v in voisins:
                    print(f"       miroir · {v[:64]}")
                if not voisins:
                    print("       miroir · (rien)")

        if dates_resolubles:
            dates_resolubles.sort()
            print("\n" + "=" * 78)
            print("LES « RÉSOLUBLES MAINTENANT » — quand ont-elles été détectées?")
            print("=" * 78)
            milieu = dates_resolubles[len(dates_resolubles) // 2]
            print(f"   la plus ancienne : {dates_resolubles[0]:%Y-%m-%d %H:%M}")
            print(f"   médiane          : {milieu:%Y-%m-%d %H:%M}")
            print(f"   la plus récente  : {dates_resolubles[-1]:%Y-%m-%d %H:%M}")
            print("\n   ⚠️ À comparer avec la DATE D'IMPORT DU MIROIR REQ.")
            print("      Si toutes précèdent l'import, le miroir a changé depuis — et le rejeu")
            print("      ne contredit pas la production. Si certaines la suivent, l'explication")
            print("      est ailleurs : le code, ou l'écart de rejeu déclaré en portée.")

        ventilation_non_resolues(session, [c.id for c in entreprises])

        print("\n⚠️ Le classement des DIFFÉRENCES est une proposition, pas un verdict.")
        print("   Il dit ce qui distingue les chaînes; il ne prouve pas la cause.")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
