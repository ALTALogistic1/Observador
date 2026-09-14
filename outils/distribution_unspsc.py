"""Que portent VRAIMENT nos signaux SEAO en fait de classification normalisée?

**Pourquoi cet outil existe, et pourquoi il ne propose rien.** La correspondance
code → sphère est une décision de produit *(charte, règle 5; registre, D48)*. Avant de
la prendre, il faut savoir **quels codes le produit porte réellement** — pas les 1 242
codes distincts d'une semaine complète du SEAO, mais ceux des signaux en base depuis la
reprise du 14 septembre 2026.

**Ce que l'outil rend, et rien d'autre** : des comptes, des parts cumulées, et la
disponibilité des libellés. **Il n'attribue aucune sphère et n'en suggère aucune.**

**La question qu'il sert à trancher : la forme de la table.** *Si vingt codes couvrent
80 % des signaux, la table s'écrit à la main. Si la distribution est plate, il faut
associer à un niveau plus large — et le niveau est une décision en soi, puisque UNSPSC
est hiérarchique.* D'où les quatre paliers ci-dessous, qui rendent ce choix mesurable
plutôt que deviné.

    88-10-15-01   commodité (8 chiffres) — le code tel que la source le donne
    88-10-15      classe     (6)
    88-10         famille    (4)
    88            segment    (2)

**PORTÉE** — ce que cet outil ne regarde pas, pour qu'aucun zéro ne se lise comme une
absence *(guide d'ingénierie)* :

- **Il ne lit que les signaux `source_id == "seao"` EN BASE.** *Il ne relit aucun fichier
  source : un code absent ici peut très bien exister au SEAO et n'avoir jamais été
  ingéré — la fenêtre de 30 jours écarte ~80 % de chaque fichier (journal, cas 40).*
- **Il ne dit rien du donneur d'ouvrage ni du fournisseur** : un avis porte deux
  prospects *(registre, D43)*, et un code ne dit pas à qui il s'applique.
- **Il ne déduplique pas les avis entre eux** : chaque signal compte pour un.

**PROVENANCE** — la base durable annoncée par `falkye.db.cible_annoncee()`, à la date
d'exécution, imprimée en tête de chaque passage.

    python outils/distribution_unspsc.py                 # les 40 premiers codes
    python outils/distribution_unspsc.py --tous          # tous
    python outils/distribution_unspsc.py --palier 4      # agrégé à la famille
    python outils/distribution_unspsc.py --csv chemin.csv

Sur l'hôte, l'environnement d'abord — et l'identité du service :

    sudo bash -c 'set -a; . /etc/falkye/falkye.env; set +a
      exec runuser -u falkye -- /opt/falkye/venv/bin/python outils/distribution_unspsc.py'
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter

#: Les quatre paliers de la hiérarchie UNSPSC, en nombre de chiffres conservés.
#: `None` = le code entier tel que la source l'écrit — jamais tronqué ni complété.
PALIERS = {8: "commodité", 6: "classe", 4: "famille", 2: "segment"}

#: Le seuil qui sert à répondre « à la main ou pas ». Choisi par Alexandre le
#: 2026-09-14 : « si vingt codes couvrent 80 % des signaux, elle se fait à la main ».
PART_DE_REFERENCE = 80.0


def tronquer(code: str, chiffres: int) -> str | None:
    """Le préfixe hiérarchique, ou None si le code ne peut pas le porter.

    **Un code trop court n'est pas complété par des zéros** : ce serait inventer une
    position dans la hiérarchie. Il est compté à part, et la sortie le dit.
    """
    nu = "".join(c for c in code if c.isdigit())
    if len(nu) < chiffres:
        return None
    return nu[:chiffres]


def profondeur_unspsc(code: str) -> int | None:
    """Combien de paliers un code RENSEIGNE réellement, de 1 à 4 — ou None s'il n'a
    pas huit chiffres.

    **UNSPSC se lit par paires** : segment · famille · classe · commodité. Une paire à
    `00` n'est pas une valeur, c'est une position laissée vide par le classificateur.
    *`72000000` ne dit que son segment; `81100000` s'arrête à la famille.*

    **Pourquoi ce compte décide quelque chose** : pour toute occurrence dont la
    profondeur est déjà ≤ 2, **agréger à la famille ne perd RIEN** — la source n'avait
    rien écrit de plus fin. *La troncature ne coûte que sur le reste.*
    """
    nu = "".join(c for c in code if c.isdigit())
    if len(nu) != 8:
        return None
    paires = [nu[i:i + 2] for i in range(0, 8, 2)]
    profondeur = 0
    for rang, paire in enumerate(paires, start=1):
        if paire != "00":
            profondeur = rang
    return profondeur


def classifications_des_signaux(db_session) -> tuple[list[tuple[str, str | None, str | None]], int, int]:
    """(entrées, nb_signaux, nb_signaux_sans_classification).

    Une entrée = (code, libellé, schéma) pour UN signal. Un signal portant trois codes
    produit trois entrées — c'est voulu, et les deux comptes sont rendus séparément
    plus bas pour qu'on ne les confonde pas.
    """
    from sqlalchemy import select

    from falkye.models.signal import Signal

    entrees: list[tuple[str, str | None, str | None]] = []
    signaux = db_session.execute(select(Signal).where(Signal.source_id == "seao")).scalars().all()
    sans = 0
    for signal in signaux:
        classifications = (signal.champs or {}).get("secteur_nature_contrat") or []
        if not classifications:
            sans += 1
            continue
        for entree in classifications:
            if not isinstance(entree, dict) or not entree.get("code"):
                continue
            entrees.append((str(entree["code"]), entree.get("libelle"), entree.get("scheme")))
    return entrees, len(signaux), sans


def _tableau_agrege(compte: Counter, membres: dict[str, Counter], total: int,
                    limite: int | None, nb_libelles: int) -> None:
    """Le palier agrégé, **avec les libellés des codes à huit chiffres qu'il regroupe**.

    *Un préfixe n'a pas de libellé : la source n'en donne qu'au code entier. Sans ces
    libellés, une table se nommerait sur des numéros nus — illisible et invérifiable.*
    """
    cumul = 0
    for rang, (prefixe, n) in enumerate(compte.most_common(), start=1):
        cumul += n
        if limite is not None and rang > limite:
            continue
        print(f"\n{prefixe:>8}  {n:>7}  {100*n/total:>5.1f}%  cumul {100*cumul/total:>5.1f}%")
        for libelle, k in membres.get(prefixe, Counter()).most_common(nb_libelles):
            print(f"{'':>10}· {k:>5}  {libelle[:62]}")
        restants = len(membres.get(prefixe, Counter())) - nb_libelles
        if restants > 0:
            print(f"{'':>10}  … et {restants} autre(s) libellé(s) dans cette entrée")
    if limite is not None and len(compte) > limite:
        print(f"\n{'…':>8}  et {len(compte) - limite} entrée(s) de plus — `--tous` pour les voir")


def _tableau(compte: Counter, libelles: dict[str, str], total: int, limite: int | None) -> None:
    print(f"\n{'code':>12}  {'signaux':>8}  {'part':>6}  {'cumul':>6}  libellé")
    print(f"{'-'*12}  {'-'*8}  {'-'*6}  {'-'*6}  {'-'*40}")
    cumul = 0
    for rang, (code, n) in enumerate(compte.most_common(), start=1):
        cumul += n
        if limite is not None and rang > limite:
            continue
        libelle = libelles.get(code) or "— (aucun libellé dans les données)"
        print(f"{code:>12}  {n:>8}  {100*n/total:>5.1f}%  {100*cumul/total:>5.1f}%  {libelle[:60]}")
    if limite is not None and len(compte) > limite:
        restants = len(compte) - limite
        print(f"{'…':>12}  {'':>8}  {'':>6}  {'':>6}  et {restants} code(s) de plus — `--tous` pour les voir")


def _codes_pour_part(compte: Counter, total: int, part: float) -> int:
    """Combien de codes distincts faut-il pour couvrir `part` % des occurrences."""
    cumul = 0
    for rang, (_, n) in enumerate(compte.most_common(), start=1):
        cumul += n
        if 100 * cumul / total >= part:
            return rang
    return len(compte)


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description="Distribution des codes UNSPSC des signaux SEAO en base.")
    parseur.add_argument("--palier", type=int, choices=sorted(PALIERS), default=8,
                         help="chiffres conservés : 8 commodité (défaut), 6 classe, 4 famille, 2 segment")
    parseur.add_argument("--tous", action="store_true", help="afficher tous les codes, pas seulement les 40 premiers")
    parseur.add_argument("--libelles", type=int, default=4, metavar="N",
                         help="libellés les plus fréquents affichés sous chaque entrée agrégée (défaut 4)")
    parseur.add_argument("--csv", metavar="CHEMIN", help="écrire le tableau complet en CSV (n'écrit RIEN en base)")
    args = parseur.parse_args(argv)

    from falkye.db import bases_sur_repli, cible_annoncee

    print(cible_annoncee())
    if bases_sur_repli():
        print(
            "\nREFUS — aucune cible n'a été choisie : "
            f"{', '.join(bases_sur_repli())} absente(s).\n"
            "  « Aucun code trouvé » sur une base vide se lit comme une distribution plate.\n"
            "  Sur l'hôte : set -a; . /etc/falkye/falkye.env; set +a",
            file=sys.stderr,
        )
        return 2

    from falkye.db import get_session

    session = get_session()
    try:
        entrees, nb_signaux, sans_classification = classifications_des_signaux(session)
    finally:
        session.close()

    print("\nPORTÉE : les signaux `seao` EN BASE, jamais les fichiers source.")
    print("         Un code absent ici peut exister au SEAO sans avoir été ingéré.")
    print(f"\nsignaux SEAO en base                : {nb_signaux}")
    if nb_signaux == 0:
        print("\n⚠️ AUCUN signal SEAO en base. Ce n'est pas une distribution plate —")
        print("   c'est une absence de mesure (guide d'ingénierie).")
        return 0
    part_sans = 100 * sans_classification / nb_signaux
    print(f"  sans aucune classification        : {sans_classification}  ({part_sans:.1f} %)")
    print(f"  portant au moins un code          : {nb_signaux - sans_classification}")
    print(f"occurrences de code (un signal peut en porter plusieurs) : {len(entrees)}")

    if not entrees:
        print("\n⚠️ AUCUNE classification en base. Ce n'est PAS « le SEAO n'en publie pas » :")
        print("   vérifier que la reprise du 14 septembre a bien été appliquée.")
        return 0

    schemas = Counter(s or "(aucun)" for _, _, s in entrees)
    print(f"\nschémas rencontrés : {dict(schemas)}")
    if len(schemas) > 1:
        print("   ⚠️ PLUSIEURS schémas — un code n'a de sens que dans le sien. Ne pas les mélanger.")

    avec_libelle = sum(1 for _, libelle, _ in entrees if libelle and str(libelle).strip())
    print(f"libellé présent    : {avec_libelle}/{len(entrees)}  ({100*avec_libelle/len(entrees):.1f} %)")
    if avec_libelle < len(entrees):
        print("   ⚠️ Une table écrite sur des numéros nus est illisible et invérifiable.")

    # Un libellé par code : le plus fréquent, et on signale si un code en porte plusieurs.
    par_code_libelles: dict[str, Counter] = {}
    for code, libelle, _ in entrees:
        if libelle and str(libelle).strip():
            par_code_libelles.setdefault(code, Counter())[str(libelle).strip()] += 1
    divergents = [c for c, lib in par_code_libelles.items() if len(lib) > 1]
    if divergents:
        print(f"   ⚠️ {len(divergents)} code(s) portent PLUSIEURS libellés distincts — le plus fréquent est affiché.")

    print("\n" + "=" * 78)
    print("À QUELLE PROFONDEUR LA SOURCE CLASSE-T-ELLE DÉJÀ?")
    print("=" * 78)
    profondeurs = Counter()
    for code, _, _ in entrees:
        profondeurs[profondeur_unspsc(code)] += 1
    noms = {1: "segment seul (………00000000)", 2: "jusqu'à la famille",
            3: "jusqu'à la classe", 4: "commodité complète", None: "code sans huit chiffres"}
    cumul_large = 0
    for niveau in (1, 2, 3, 4, None):
        n = profondeurs.get(niveau, 0)
        if not n:
            continue
        if niveau in (1, 2):
            cumul_large += n
        print(f"   {noms[niveau]:32} {n:>6}  {100*n/len(entrees):>5.1f} %")
    print(f"\n   déjà classé au palier FAMILLE ou plus large : {cumul_large}"
          f"  ({100*cumul_large/len(entrees):.1f} %)")
    print("   → pour cette part, agréger à la famille ne perd RIEN : la source")
    print("     n'avait rien écrit de plus fin. La troncature ne coûte que sur le reste.")

    print("\n" + "=" * 78)
    print("CE QUE CHAQUE PALIER COÛTERAIT À ÉCRIRE — c'est la question de la forme")
    print("=" * 78)
    print(f"\n{'palier':>18}  {'codes':>7}  {'codes pour ' + str(int(PART_DE_REFERENCE)) + ' %':>16}  {'tronqués':>9}")
    for chiffres, nom in sorted(PALIERS.items(), reverse=True):
        agrege = Counter()
        impossibles = 0
        for code, _, _ in entrees:
            prefixe = tronquer(code, chiffres)
            if prefixe is None:
                impossibles += 1
                continue
            agrege[prefixe] += 1
        if not agrege:
            continue
        besoin = _codes_pour_part(agrege, sum(agrege.values()), PART_DE_REFERENCE)
        print(f"{nom + ' (' + str(chiffres) + ')':>18}  {len(agrege):>7}  {besoin:>16}  {impossibles:>9}")
    print("\n  « codes pour 80 % » = combien d'entrées une table à la main devrait porter")
    print("  pour couvrir 80 % des occurrences À CE PALIER. « tronqués » = codes trop")
    print("  courts pour ce palier, comptés à part et JAMAIS complétés par des zéros.")

    # Le tableau détaillé, au palier demandé.
    agrege = Counter()
    libelles: dict[str, str] = {}
    membres: dict[str, Counter] = {}
    for code, _, _ in entrees:
        prefixe = tronquer(code, args.palier) if args.palier != 8 else code
        if prefixe is None:
            continue
        agrege[prefixe] += 1
        if code in par_code_libelles:
            libelle = par_code_libelles[code].most_common(1)[0][0]
            if args.palier == 8:
                libelles[code] = libelle
            else:
                membres.setdefault(prefixe, Counter())[libelle] += 1
    total_agrege = sum(agrege.values())
    print("\n" + "=" * 78)
    print(f"DISTRIBUTION AU PALIER « {PALIERS[args.palier]} » ({args.palier} chiffres)")
    print("=" * 78)
    if args.palier == 8:
        _tableau(agrege, libelles, total_agrege, None if args.tous else 40)
    else:
        print("\nUn préfixe n'a PAS de libellé — la source n'en donne qu'au code entier.")
        print(f"Sous chaque entrée : les {args.libelles} libellés les plus fréquents qu'elle")
        print("regroupe, pour qu'elle se nomme sur ce qu'elle porte et non sur son numéro.")
        _tableau_agrege(agrege, membres, total_agrege, None if args.tous else 40, args.libelles)

    if args.csv:
        cumul = 0
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            ecrivain = csv.writer(f)
            ecrivain.writerow(["code", "occurrences", "part_pct", "cumul_pct", "libelle",
                               "libelles_regroupes"])
            for code, n in agrege.most_common():
                cumul += n
                regroupes = " | ".join(
                    f"{lib} ({k})" for lib, k in membres.get(code, Counter()).most_common(args.libelles)
                )
                ecrivain.writerow([code, n, round(100*n/total_agrege, 3), round(100*cumul/total_agrege, 3),
                                   libelles.get(code, ""), regroupes])
        print(f"\nécrit : {args.csv}  (aucune écriture en base)")

    print("\n⚠️ Cet outil n'attribue AUCUNE sphère et n'en propose aucune.")
    print("   La correspondance code → sphère est une décision de produit (registre, D48),")
    print("   et le garde-fou du chantier 22 s'y applique : un code ne doit pas ouvrir")
    print("   cinq sphères d'un coup — ce qui transforme une correspondance en lecture,")
    print("   c'est la CONDITION, pas le code.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
