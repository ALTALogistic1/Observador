#!/usr/bin/env python3
"""Combien d'entreprises franchiraient 92 **si les deux côtés étaient normalisés
de la même façon** — mesuré par rejeu, sans rien corriger ni importer.

**Le fait qui justifie cet outil** *(Alexandre, 2026-09-16)*. Le miroir retire la
forme juridique, le connecteur de l'EIMT ne la retire pas :

    détecté  9309-3927 Quebec inc   →  norm  « 9309 3927 quebec inc »   (20)
    miroir   9309-3927 QUÉBEC INC.  →  norm  « 9309 3927 quebec »       (16)
                                                        score 66

**Quatre caractères sur vingt, et le score tombe à 66.** Et **74,9 % des noms de
l'EIMT portent une forme juridique en fin** — donc si l'asymétrie explique la
bande 0-64, c'est là que se joue le mur, et la correction est d'une ligne.

**Ce que l'outil mesure, exactement.** Pour chaque `Company` sans NEQ : le score
que le moteur rend AUJOURD'HUI, puis le score qu'il rendrait si la requête et la
chaîne stockée passaient toutes deux par la même normalisation symétrique. **La
différence est la mesure; elle n'est pas une prédiction de gain.**

⚠️ **Trois réserves, et elles pèsent autant que le chiffre.**

*(1)* **Franchir 92 ne suffit pas à résoudre.** Le moteur exige AUSSI un écart
d'au moins 8 points avec le deuxième candidat *(`SEUIL_AMBIGUITE_ECART_MIN`)*.
**Retirer la forme juridique rapproche mécaniquement les homonymes** — deux
« Transport Gagnon inc. » et « Transport Gagnon ltée » deviennent identiques.
*L'outil compte donc séparément ce qui devient RÉSOLU et ce qui devient AMBIGU,
et un basculement vers l'ambiguïté n'est pas un gain.*

*(2)* **La récupération n'est pas rejouée.** Elle est ancrée sur la TÊTE de la
chaîne *(`req.candidats_par_nom`)*, et une forme juridique en FIN ne change pas
la tête — *donc le lot de candidats est le même, et c'est vérifiable dans la
sortie.* **Une entreprise absente du lot reste absente : aucune normalisation ne
la fait apparaître.**

*(3)* ⚠️ **L'outil ne tranche pas d'où vient l'asymétrie.** Il constate que la
chaîne stockée et la chaîne recalculée diffèrent, et il le rapporte ligne par
ligne. *Savoir si c'est l'écriture du miroir ou la lecture du connecteur qui
dévie est une autre question* — celle-là se lit dans la colonne « stocké vs
recalculé » ci-dessous, pas dans le total.

**PORTÉE.** Lecture seule. Rien n'est écrit, aucun NEQ n'est posé, aucune colonne
n'est recalculée en base. *Un rejeu n'est pas une correction* — c'est le chiffre
sur lequel la correction se décide.

Usage :
    python3 outils/rejeu_normalisation_symetrique.py
    python3 outils/rejeu_normalisation_symetrique.py --exemples 30
    python3 outils/rejeu_normalisation_symetrique.py --echantillon 500
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter

#: Les formes juridiques, telles qu'elles apparaissent APRÈS `normaliser` — donc
#: sans accent, sans ponctuation, en minuscules. **Retirées seulement en FIN de
#: chaîne** : « Inc. Gestion Tremblay » n'existe pas, mais « Les Entreprises
#: Ltée Gagnon » pourrait, et retirer un mot au milieu changerait le nom.
FORMES_JURIDIQUES = frozenset({
    "inc", "ltee", "ltd", "limitee", "limited", "senc", "sencrl", "srl",
    "cie", "co", "corp", "corporation", "sec", "snc", "enr", "reg",
    "association", "cooperative", "coop", "societe", "sa", "sas",
})

#: Le seuil du moteur, emprunté et non recopié — voir `falkye/resolution.py`.
#: Recopié ici, il vieillirait sans que rien ne le signale.


def normaliser_symetrique(nom_norm: str) -> str:
    """Retire les formes juridiques **en fin de chaîne**, et elles seules.

    Plusieurs peuvent s'empiler — « gestion tremblay inc ltee » — donc la boucle
    continue tant que le dernier mot en est une. **Un nom RÉDUIT À RIEN est rendu
    inchangé** : « Les Entreprises Inc. » ne doit pas devenir la chaîne vide, ce
    qui le ferait apparier avec n'importe quoi *(et c'est exactement le défaut
    qu'on vient de passer trois jours à traquer)*.
    """
    mots = nom_norm.split()
    while len(mots) > 1 and mots[-1] in FORMES_JURIDIQUES:
        mots.pop()
    return " ".join(mots) if mots else nom_norm


def porte_une_forme_juridique(nom_norm: str) -> bool:
    """Vrai si le nom se termine par une forme juridique. **Mesuré à 74,9 % sur
    les noms de l'EIMT** — c'est ce taux qui donne au défaut sa portée."""
    mots = nom_norm.split()
    return len(mots) > 1 and mots[-1] in FORMES_JURIDIQUES


def classer_rejeu(avant: float, apres: float, ecart_apres: float,
                  seuil: float, ecart_min: float) -> str:
    """Le verdict d'une entreprise, et il a **quatre** issues, pas deux.

    *Compter « au-dessus de 92 » sans compter l'ambiguïté surestimerait le gain* :
    le moteur refuse un candidat trop proche du suivant, et retirer la forme
    juridique rapproche les homonymes.
    """
    franchit_avant = avant >= seuil
    franchit_apres = apres >= seuil
    if franchit_apres and ecart_apres < ecart_min:
        return "franchit 92 mais devient AMBIGU — pas un gain"
    if franchit_apres and not franchit_avant:
        return "RÉSOLU par la symétrie"
    if franchit_avant and not franchit_apres:
        return "PERDU par la symétrie"
    if franchit_avant:
        return "déjà résolu avant"
    return "toujours sous le seuil"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--echantillon", type=int, default=None,
                        help="limiter à N entreprises (défaut : toutes)")
    parser.add_argument("--exemples", type=int, default=15,
                        help="exemples montrés par classe (défaut 15)")
    args = parser.parse_args(argv)

    try:
        from rapidfuzz import fuzz, process
        from sqlalchemy import select

        from falkye.db import get_session
        from falkye.models.company import Company
        from falkye.resolution import SEUIL_AMBIGUITE_ECART_MIN, SEUIL_RESOLUTION_CONFIANTE
        from falkye.sources.column_mapping import normaliser
        from falkye.sources.req import candidats_par_nom, resolve_neq_by_name
    except ImportError as exc:  # pragma: no cover - dépend de l'environnement
        print(f"Import impossible ({exc}). Lancer depuis la racine du dépôt.", file=sys.stderr)
        return 2

    session = get_session()
    try:
        requete = select(Company).where(Company.neq.is_(None))
        if args.echantillon:
            requete = requete.limit(args.echantillon)
        entreprises = session.execute(requete).scalars().all()

        print("=" * 78)
        print("REJEU — ET SI LES DEUX CÔTÉS ÉTAIENT NORMALISÉS PAREIL ?")
        print("=" * 78)
        print("\nPORTÉE : lecture seule. Rien n'écrit, rien n'importe, rien ne corrige.")
        print(f"         seuil de résolution {SEUIL_RESOLUTION_CONFIANTE:.0f}, "
              f"écart minimal avec le 2e {SEUIL_AMBIGUITE_ECART_MIN:.0f}")
        print(f"\nentreprises sans NEQ examinées : {len(entreprises)}")
        if not entreprises:
            print("Rien à rejouer.")
            return 0

        classes: Counter = Counter()
        exemples: dict[str, list] = {}
        asymetries: Counter = Counter()
        avec_forme_juridique = 0
        lots_identiques = 0
        lots_examines = 0
        sans_candidat = 0

        for company in entreprises:
            nom = company.nom_detecte or ""
            nom_norm = normaliser(nom)
            if not nom_norm:
                continue
            if porte_une_forme_juridique(nom_norm):
                avec_forme_juridique += 1

            candidats = candidats_par_nom(session, nom_norm)
            if not candidats:
                sans_candidat += 1
                continue

            # --- AVANT : exactement ce que le moteur fait aujourd'hui ---------
            matches = resolve_neq_by_name(session, nom, ville=company.ville)
            if not matches:
                sans_candidat += 1
                continue
            avant = matches[0].score
            avant_second = matches[1].score if len(matches) > 1 else 0.0

            # --- APRÈS : la MÊME normalisation des deux côtés -----------------
            # La récupération n'est pas rejouée : elle est ancrée sur la tête de
            # la chaîne, qu'une forme juridique en fin ne change pas. Le lot est
            # donc le même, et la sortie le vérifie plutôt que de l'affirmer.
            lots_examines += 1
            requete_sym = normaliser_symetrique(nom_norm)
            choix = {c.neq: normaliser_symetrique(c.nom_normalise or "") for c in candidats}
            if set(choix) == {c.neq for c in candidats}:
                lots_identiques += 1
            classement = process.extract(requete_sym, choix, scorer=fuzz.WRatio, limit=5)
            apres = classement[0][1] if classement else 0.0
            apres_second = classement[1][1] if len(classement) > 1 else 0.0

            # L'asymétrie elle-même : la chaîne stockée est-elle celle que
            # `normaliser` rendrait sur le nom brut du miroir ?
            meilleur = matches[0].entry
            stocke = meilleur.nom_normalise or ""
            recalcule = normaliser(meilleur.nom or "")
            if stocke == recalcule:
                asymetries["stocké == recalculé"] += 1
            elif not stocke:
                asymetries["stocké VIDE"] += 1
            elif recalcule.startswith(stocke):
                asymetries["stocké TRONQUÉ en queue"] += 1
            else:
                asymetries["stocké DIVERGENT"] += 1

            classe = classer_rejeu(avant, apres, apres - apres_second,
                                   SEUIL_RESOLUTION_CONFIANTE, SEUIL_AMBIGUITE_ECART_MIN)
            classes[classe] += 1
            if len(exemples.setdefault(classe, [])) < args.exemples:
                exemples[classe].append({
                    "detecte": nom, "norm": nom_norm, "sym": requete_sym,
                    "miroir": meilleur.nom, "stocke": stocke,
                    "miroir_sym": normaliser_symetrique(stocke),
                    "avant": avant, "avant_2e": avant_second,
                    "apres": apres, "apres_2e": apres_second,
                    "candidats": len(candidats),
                })

        # ---- le résultat ----------------------------------------------------
        print("\n" + "=" * 78)
        print("LE RÉSULTAT")
        print("=" * 78)
        total = sum(classes.values())
        print(f"\n   rejouées                       : {total}")
        print(f"   sans aucun candidat récupéré   : {sans_candidat}"
              "   ← aucune normalisation ne les répare")
        part = 100 * avec_forme_juridique / max(1, len(entreprises))
        print(f"   noms portant une forme juridique en fin : {avec_forme_juridique}"
              f"  ({part:.1f} %)")
        print()
        for classe, n in classes.most_common():
            marque = "  ←" if classe.startswith("RÉSOLU") else ""
            print(f"   {n:>7}  {classe}{marque}")

        gagnees = classes.get("RÉSOLU par la symétrie", 0)
        ambigues = classes.get("franchit 92 mais devient AMBIGU — pas un gain", 0)
        perdues = classes.get("PERDU par la symétrie", 0)
        print(f"\n   → {gagnees} entreprise(s) deviendraient RÉSOLUBLES.")
        print(f"   → {ambigues} franchiraient 92 sans être résolues (trop proches du 2e).")
        print(f"   → {perdues} seraient PERDUES par la symétrie.")
        print(f"\n   gain net : {gagnees - perdues:+d}")

        print("\n   LE LOT DE CANDIDATS, vérifié plutôt qu'affirmé :")
        print(f"      {lots_identiques} lot(s) sur {lots_examines} sont identiques avant et après.")
        print("      La récupération est ancrée sur la TÊTE; une forme juridique en")
        print("      fin ne la change pas. Un écart ici démentirait cette portée.")

        print("\n   L'ASYMÉTRIE ELLE-MÊME — stocké contre recalculé, sur le meilleur candidat :")
        for motif, n in asymetries.most_common():
            print(f"      {n:>7}  {motif}")
        print("      ⚠️ Ce tableau dit OÙ est l'écart, pas QUI l'a créé.")

        for classe in ("RÉSOLU par la symétrie",
                       "franchit 92 mais devient AMBIGU — pas un gain",
                       "PERDU par la symétrie",
                       "toujours sous le seuil"):
            lignes = exemples.get(classe) or []
            if not lignes:
                continue
            print("\n" + "-" * 78)
            print(f"{classe}  —  {classes[classe]} au total, {len(lignes)} montrée(s)")
            print("-" * 78)
            for e in lignes:
                print(f"\n   {e['avant']:.1f} → {e['apres']:.1f}   ({e['candidats']} candidat(s))")
                print(f"      détecté   : {e['detecte'][:62]}")
                print(f"      miroir    : {(e['miroir'] or '')[:62]}")
                print(f"      norm dét. : [{e['norm'][:60]}]")
                print(f"      norm mir. : [{e['stocke'][:60]}]")
                print(f"      sym dét.  : [{e['sym'][:60]}]")
                print(f"      sym mir.  : [{e['miroir_sym'][:60]}]")
                print(f"      2e        : {e['avant_2e']:.1f} → {e['apres_2e']:.1f}"
                      f"   (écart après : {e['apres'] - e['apres_2e']:.1f})")

        print("\n" + "=" * 78)
        print("CE QUE CE CHIFFRE NE DIT PAS")
        print("=" * 78)
        print("   • Il ne dit pas que les appariements gagnés sont JUSTES. Retirer la")
        print("     forme juridique rapproche aussi ce qui devait rester distinct.")
        print("   • Il ne dit pas d'où vient l'asymétrie — écriture du miroir ou")
        print("     lecture du connecteur. Le tableau ci-dessus la situe, sans l'imputer.")
        print("   • Rien n'a été écrit. Un rejeu n'est pas une correction.")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
