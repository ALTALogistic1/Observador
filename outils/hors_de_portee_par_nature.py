#!/usr/bin/env python3
"""Combien des restants sont **hors de portée par nature** — des entreprises que
le Registraire ne nommera jamais.

## ⚠️ LA DIFFICULTÉ, ET ELLE SE NOMME AVANT DE CHERCHER UNE MÉTHODE

**On ne connaît la forme juridique que d'une entreprise DÉJÀ IDENTIFIÉE.** *C'est
la réserve posée sur `NOM_ETAB`, et elle vaut ici :* **un dossier sans NEQ n'a pas
de forme juridique lisible.**

⚠️ **Et la clé qui manque est exactement ce qu'on cherche.** Les **224 968** NEQ
absents de `Nom.csv` n'ont **aucun nom publié**. *Un restant ne porte qu'un nom.*
**On ne peut donc pas les joindre : le croisement demandé n'est pas difficile, il
est sans clé.** *Le dire est un résultat, et c'est le premier de cet outil.*

**Donc toute mesure ici est INDIRECTE**, et chacune porte son étiquette.

## Ce qui est déjà établi, et n'est PAS remesuré

- `outils/profil_des_absents_req.py`, **le 16 septembre** : **96,6 %** des
  **224 968** NEQ absents de `Nom.csv` sont des **personnes physiques**.
- **`NOM_ETAB` confirmé par un autre chemin** : ses **5** récupérations étaient
  **toutes de forme `IND`**.

*Ces deux chiffres sont cités, jamais recalculés.*

## Les deux cibles, et les confondre ruinerait tout

**T1 — « c'est une personne physique ».** *Une forme juridique.* **Mesurable sur
les dossiers résolus**, puisqu'ils portent un NEQ.

**T2 — « le registre ne la nommera jamais ».** *Ce qu'on cherche.* **Non mesurable
sur les résolus** : *ils sont résolus, donc le registre les a nommés.* ⚠️ **Une
précision calculée sur les résolus mesure T1, jamais T2** — et les présenter l'une
pour l'autre serait le défaut que cet outil existe pour éviter.

**Le pont entre les deux se mesure, lui, et sans heuristique** *(section 6)* : la
part des personnes physiques du registre **qui n'ont aucun nom publié**.

## Les méthodes, et ce que chacune est

1. **MÉTHODE A — la forme du nom détecté.** `« Lessard, Martin »`,
   `« DUBÉ, RICHARD »`. ⚠️ **Une heuristique, pas une lecture.** *Elle se trompe
   dans les deux sens.* **Deux règles, deux chiffres, JAMAIS additionnés** — une
   stricte et une lâche, pour que le desserrage se voie au lieu de se supposer.
2. **MÉTHODE B — par la source.** *Le taux de personnes physiques mesuré chez les
   RÉSOLUS de chaque source* — une base réelle, pas une intuition sur ce qu'une
   source capte.

## ⚠️ Laquelle des deux erreurs l'heuristique préfère, et pourquoi

**Elle préfère MANQUER une personne physique plutôt que compter une entreprise.**
*C'est la seule préférence qui rend le chiffre lisible comme un **plancher*** : un
comptage qui déborde n'est plus un plancher, c'est une estimation. **Toutes les
exclusions de la règle stricte vont donc dans ce sens, et le compte de ce que
chacune retire est rendu** — *une exclusion qui ne se voit pas ne se discute pas.*

⚠️ **CE QUE CET OUTIL NE FERA PAS : poser un chiffre sur une heuristique sans dire
qu'elle en est une.** *Un plancher estimé se relit comme un plancher mesuré dans
trois semaines.* **Chaque chiffre porte donc, sur sa ligne, ce qu'il est.**

⚠️ **AUCUNE ÉCRITURE. Les échelles ne bougent pas : seuil 92, écart 8.**

Usage, SUR L'HÔTE :
    python3 -m outils.hors_de_portee_par_nature
    python3 -m outils.hors_de_portee_par_nature --chemin /opt/falkye/import
    python3 -m outils.hors_de_portee_par_nature --chemin … --comparer 30
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import zipfile
from collections import Counter, defaultdict

from outils.nombres import milliers

# ⚠️ **Importée, jamais recopiée.** *Une règle recopiée à la main diverge de son
# original sans que rien ne le dise* — c'est le défaut qu'on a déjà payé quatre
# fois sur les gardes.
from outils.nature_des_restants import FORME_JURIDIQUE

#: La règle du verdict, **posée avant de voir le moindre chiffre**. *Un seuil
#: choisi après coup n'est pas un seuil, c'est une justification.* **Au-dessus,
#: la règle stricte ne tient pas comme plancher** : un plancher qui compte une
#: entreprise sur cinq à tort n'est plus un plancher.
FAUX_POSITIFS_MAX_POUR_UN_PLANCHER = 20.0

#: Ce que la règle stricte accepte comme jeton de patronyme. **Les lettres
#: accentuées en sont**, le trait d'union et l'apostrophe aussi — `« Saint-Jean »`
#: et `« O'Brien »` sont des noms de famille.
#:
#: ⚠️ **AUCUN CHIFFRE N'Y PASSE, et c'est ce qui écarte les sociétés à numéro** —
#: `« 9528-9393 Québec inc. »` tombe ici, avant toute autre exclusion. *Une
#: vérification `porte_un_chiffre` séparée a été écrite puis RETIRÉE : elle ne
#: pouvait jamais se déclencher, ce jeton-ci l'ayant déjà fait.* **Une garde qui
#: ne se déclenche jamais se lit comme une protection sans en être une.**
JETON_DE_NOM = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'’.-]*$")

#: Au-delà, ce n'est plus « Nom, Prénom » — c'est une raison sociale à virgule.
JETONS_MAX_PAR_MORCEAU = 2

#: Des mots qui désignent une activité, jamais une personne. ⚠️ **Une
#: OBSERVATION, pas une nomenclature** — tirée des noms effectivement captés, et
#: le Registraire n'en connaît pas la liste. *Elle sert à EXCLURE, donc elle va
#: dans le sens de l'erreur qu'on préfère : elle fait manquer, elle ne fait pas
#: déborder.* **Ce qu'elle retire est compté et affiché.**
MOTS_DENTREPRISE = (
    "construction", "transport", "services", "service", "entreprises",
    "entreprise", "groupe", "group", "consultants", "consultant", "conseil",
    "immobilier", "immobiliers", "gestion", "technologies", "technologie",
    "solutions", "solution", "systemes", "systèmes", "systems", "industries",
    "industrie", "distribution", "equipements", "équipements", "mecanique",
    "mécanique", "electrique", "électrique", "plomberie", "excavation",
    "renovation", "rénovation", "developpement", "développement", "holding",
    "investissements", "placements", "assurances", "courtage", "clinique",
    "restaurant", "boutique", "atelier", "garage", "ferme", "fils", "freres",
    "frères", "associes", "associés", "partners", "canada", "quebec", "québec",
    "international", "inter", "national", "agence", "studio", "laboratoire",
)

RETENU = "retenu"
REJET_PAS_LA_FORME = "la forme n'est pas celle d'un patronyme"
REJET_FORME_JURIDIQUE = "porte une forme juridique (inc., ltée, …)"
REJET_MOT_DENTREPRISE = "porte un mot d'activité"

#: L'ordre dans lequel la ventilation des rejets se lit. **La FORME d'abord** :
#: on veut savoir ce que les exclusions retirent *parmi les noms qui ont déjà la
#: forme voulue*, pas combien de noms n'ont pas la forme.
ORDRE_DES_REJETS = (
    REJET_PAS_LA_FORME, REJET_FORME_JURIDIQUE, REJET_MOT_DENTREPRISE,
)

#: Ce qui désigne une personne physique dans `DomaineValeur.csv`, domaine
#: `FORM_JURI`. ⚠️ **Le libellé est lu À LA SOURCE** — *un code recopié de
#: mémoire se recopie de travers.* `IND` est la graine : c'est le code des 5
#: récupérations de `NOM_ETAB`, établi le 16 septembre.
MOTIF_PERSONNE_PHYSIQUE = re.compile(
    r"personne\s+physique|entreprise\s+individuelle", re.IGNORECASE
)
CODE_PERSONNE_PHYSIQUE_CONNU = "IND"


def jetons(morceau: str) -> list[str]:
    return [j for j in re.split(r"\s+", morceau.strip()) if j]


def porte_un_mot_dentreprise(nom: str) -> bool:
    mots = {j.strip(".,'’-").lower() for j in jetons(nom)}
    return bool(mots & set(MOTS_DENTREPRISE))


def _disqualifications(nom: str) -> str | None:
    """Les exclusions communes aux deux règles, **dans l'ordre de lecture.**"""
    if FORME_JURIDIQUE.search(nom):
        return REJET_FORME_JURIDIQUE
    if porte_un_mot_dentreprise(nom):
        return REJET_MOT_DENTREPRISE
    return None


def examiner_stricte(nom: str | None) -> str:
    """`« Lessard, Martin »` — **une virgule, deux morceaux courts, rien d'autre.**

    Rend `RETENU`, ou la raison du rejet. *Rendre la RAISON et non un booléen est
    ce qui permet d'afficher ce que chaque exclusion retire* — et une exclusion
    qui ne se voit pas ne se discute pas.
    """
    if not nom:
        return REJET_PAS_LA_FORME
    brut = " ".join(jetons(nom))
    if brut.count(",") != 1:
        return REJET_PAS_LA_FORME
    morceaux = [m.strip() for m in brut.split(",")]
    if not all(morceaux):
        return REJET_PAS_LA_FORME
    for morceau in morceaux:
        lot = jetons(morceau)
        if not 1 <= len(lot) <= JETONS_MAX_PAR_MORCEAU:
            return REJET_PAS_LA_FORME
        if not all(JETON_DE_NOM.match(j) for j in lot):
            return REJET_PAS_LA_FORME
    return _disqualifications(brut) or RETENU


def examiner_lache(nom: str | None) -> str:
    """`« Martin Lessard »` — **deux jetons nus, sans virgule.**

    ⚠️ **Cette règle attrape `« Bell Canada »`.** *Elle est rendue pour que le
    desserrage se VOIE, jamais pour servir de plancher* — et son taux de faux
    positifs, mesuré en section 4, est ce qui justifie de ne pas l'employer.
    """
    if not nom:
        return REJET_PAS_LA_FORME
    brut = " ".join(jetons(nom))
    if "," in brut:
        return REJET_PAS_LA_FORME
    lot = jetons(brut)
    if len(lot) != 2 or not all(JETON_DE_NOM.match(j) for j in lot):
        return REJET_PAS_LA_FORME
    return _disqualifications(brut) or RETENU


REGLES = (
    ("STRICTE — « Nom, Prénom »", examiner_stricte),
    ("LÂCHE — deux jetons nus", examiner_lache),
)


def codes_de_personne_physique(libelles: dict[tuple[str, str], str]) -> dict[str, str]:
    """Les codes `FORM_JURI` qui désignent une personne physique, **avec leur
    libellé lu à la source.**

    ⚠️ **Si `DomaineValeur.csv` est absent, il ne reste que la graine `IND`** — et
    l'appelant doit le dire, parce qu'une classification repliée sur un seul code
    n'est pas la même mesure.
    """
    trouves = {
        code: libelle
        for (domaine, code), libelle in libelles.items()
        if domaine == "FORM_JURI" and MOTIF_PERSONNE_PHYSIQUE.search(libelle or "")
    }
    trouves.setdefault(
        CODE_PERSONNE_PHYSIQUE_CONNU,
        libelles.get(("FORM_JURI", CODE_PERSONNE_PHYSIQUE_CONNU), "(libellé absent)"),
    )
    return trouves


def _part(k: int, n: int) -> str:
    return f"{100 * k / n:.1f} %" if n else "—"


def neqs_nommes(zf: zipfile.ZipFile) -> set[str]:
    """Les NEQ qui ont **au moins un nom** dans `Nom.csv`.

    *Pas le nom élu, pas le nom retenu par le chargeur : au moins un nom.* **La
    question de la section 6 est « le registre la nomme-t-il, oui ou non »**, et
    une ligne suffit à répondre oui.
    """
    trouves: set[str] = set()
    with zf.open("Nom.csv") as brut:
        texte = io.TextIOWrapper(brut, encoding="utf-8-sig", errors="replace")
        for rangee in csv.DictReader(texte):
            neq = (rangee.get("NEQ") or "").strip()
            if neq and (rangee.get("NOM_ASSUJ") or "").strip():
                trouves.add(neq)
    return trouves


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--chemin", default=None,
                        help="l'archive du REQ, ou son répertoire. SANS elle, les "
                             "sections qui lisent une forme juridique rendent "
                             "« zéro mesure » — jamais « 0 % ».")
    parser.add_argument("--comparer", type=int, default=0, metavar="N",
                        help="montrer N noms retenus par chaque règle")
    parser.add_argument("--limite", type=int, default=None, help="borner (mise au point)")
    args = parser.parse_args(argv)

    from sqlalchemy import select

    from falkye.db import refuser_si_cible_non_choisie

    archive = None
    if args.chemin:
        from outils.archives_req import resoudre

        archive = resoudre(args.chemin)
        if archive is None:
            print(f"⛔ aucune archive à {args.chemin!r}.", file=sys.stderr)
            return 2

    code = refuser_si_cible_non_choisie()
    if code:
        return code

    from falkye.db import get_session
    from falkye.models.company import Company
    from falkye.models.req_entry import REQEntry
    from falkye.models.signal import Signal
    from falkye.resolution import SEUIL_AMBIGUITE_ECART_MIN, SEUIL_RESOLUTION_CONFIANTE
    from outils.profil_des_absents_req import charger_domaines

    print("=" * 78)
    print("HORS DE PORTÉE PAR NATURE — ce que le registre ne nommera jamais")
    print("=" * 78)
    print(f"""
⚠️ LA DIFFICULTÉ, ET ELLE SE LIT AVANT TOUT CHIFFRE

   ON NE CONNAÎT LA FORME JURIDIQUE QUE D'UNE ENTREPRISE DÉJÀ IDENTIFIÉE.
   C'est la réserve posée sur NOM_ETAB, et elle vaut ici : un dossier sans
   NEQ n'a pas de forme juridique lisible.

   ⚠️ ET LA CLÉ QUI MANQUE EST EXACTEMENT CE QU'ON CHERCHE. Les 224 968 NEQ
   absents de `Nom.csv` n'ont AUCUN nom publié; un restant ne porte qu'un
   nom. Le croisement demandé n'est donc pas difficile — IL EST SANS CLÉ.
   Le dire est un résultat, et c'est le premier de cet outil.

   DONC TOUTE MESURE CI-DESSOUS EST INDIRECTE, et chacune porte son
   étiquette : MESURE, ou HEURISTIQUE.

CE QUI EST DÉJÀ ÉTABLI, ET N'EST PAS REMESURÉ ICI

   profil_des_absents_req.py, le 16 septembre : 96,6 % des 224 968 NEQ
   absents de `Nom.csv` sont des PERSONNES PHYSIQUES.
   NOM_ETAB, par un autre chemin : ses 5 récupérations étaient toutes de
   forme `IND`.
   Ces deux chiffres sont CITÉS. Cet outil ne les recalcule pas.

⚠️ LES DEUX CIBLES, ET LES CONFONDRE RUINERAIT TOUT

   T1  « c'est une personne physique »        — mesurable sur les RÉSOLUS.
   T2  « le registre ne la nommera jamais »   — ce qu'on cherche, et NON
       mesurable sur les résolus : ils sont résolus, donc nommés.
   Le pont T1 → T2 se mesure en section 6, SANS heuristique.

   AUCUNE ÉCRITURE. Les échelles ne bougent pas : seuil {SEUIL_RESOLUTION_CONFIANTE:.0f}, écart {SEUIL_AMBIGUITE_ECART_MIN:.0f}.

LA RÈGLE DU VERDICT, POSÉE AVANT DE VOIR LE MOINDRE CHIFFRE

   La règle stricte ne tient comme PLANCHER que si son taux de faux
   positifs mesuré reste sous {FAUX_POSITIFS_MAX_POUR_UN_PLANCHER:.0f} %.
   Au-dessus, la sortie dit que la méthode NE TIENT PAS — et « aucune
   méthode ne tient » est un résultat, pas un échec.
""")

    session = get_session()
    try:
        requete = select(Company).order_by(Company.id)
        if args.limite:
            requete = requete.limit(args.limite)
        tous = list(session.execute(requete).scalars().all())
        restants = [c for c in tous if c.neq is None]
        resolus = [c for c in tous if c.neq is not None]
        n = len(restants)
        print(f"   dossiers au total : {milliers(len(tous))}")
        print(f"   RESTANTS (sans NEQ) : {milliers(n)}"
              f"   ·   résolus : {milliers(len(resolus))}\n")
        if not restants:
            print("   Aucun restant à mesurer.")
            return 0

        # ---- 3. MÉTHODE A — la forme du nom détecté -------------------------
        print("-" * 78)
        print("3. MÉTHODE A — LA FORME DU NOM DÉTECTÉ   ⚠️ HEURISTIQUE")
        print("-" * 78)
        print("""
   ⚠️ UNE HEURISTIQUE, PAS UNE LECTURE. Elle se trompe dans les deux sens.
      Elle PRÉFÈRE MANQUER une personne physique plutôt que compter une
      entreprise — c'est la seule préférence qui rend le chiffre lisible
      comme un PLANCHER. Un comptage qui déborde n'est plus un plancher.

   ⚠️ DEUX RÈGLES, DEUX CHIFFRES, JAMAIS ADDITIONNÉS. La lâche est rendue
      pour que le desserrage SE VOIE, jamais pour servir de plancher.
""")
        retenus: dict[str, list] = {}
        rejets: dict[str, Counter] = {}
        for etiquette, examiner in REGLES:
            verdicts = [(c, examiner(c.nom_detecte)) for c in restants]
            retenus[etiquette] = [c for c, v in verdicts if v == RETENU]
            rejets[etiquette] = Counter(v for _c, v in verdicts if v != RETENU)

        for etiquette, _examiner in REGLES:
            lot = retenus[etiquette]
            print(f"   {etiquette:<34} {milliers(len(lot)):>8} "
                  f"{_part(len(lot), n):>8}   sur {milliers(n)} restants")
            for raison in ORDRE_DES_REJETS:
                k = rejets[etiquette].get(raison, 0)
                if k:
                    print(f"      écartés · {raison:<44} {milliers(k):>8}")
            print()
        print("   ⚠️ Les deux lots se CHEVAUCHENT-ils? Non : la stricte exige une")
        print("      virgule, la lâche l'interdit. Ils sont disjoints par construction,")
        print("      et les additionner resterait faux pour une autre raison — la")
        print("      lâche n'a pas la précision qui ferait un plancher.")

        if args.comparer:
            for etiquette, _examiner in REGLES:
                lot = retenus[etiquette]
                montres = lot[: args.comparer]
                print(f"\n   {etiquette} — {len(montres)} sur {milliers(len(lot))} :")
                for c in montres:
                    print(f"      #{c.id:<7} {(c.nom_detecte or '')[:56]}")

        # ---- 4. CALIBRAGE — la spécificité sur le registre PUBLIÉ -----------
        # *Rendu en premier parce qu'il ne demande AUCUNE archive* — l'outil
        # rend ainsi toujours au moins un calibrage, et les numéros de section
        # se lisent dans l'ordre où ils sortent.
        print("\n" + "-" * 78)
        print("4. CALIBRAGE — LA SPÉCIFICITÉ SUR LE REGISTRE PUBLIÉ   ✅ MESURE")
        print("-" * 78)
        print("""
   Toute entité du miroir EST nommée par le registre. Donc tout nom que la
   règle y retient est un FAUX POSITIF pour T2, sans exception et sans
   supposition. C'est la base la plus large dont on dispose.

   ⚠️ Ce que cette section mesure est une SPÉCIFICITÉ — la part des entités
      nommées que la règle accuserait à tort. Ce n'est PAS une précision, et
      les présenter l'une pour l'autre serait le défaut qu'on évite ici.
""")
        total_miroir = session.execute(
            select(REQEntry.neq).execution_options(yield_per=20000)
        )
        n_miroir = 0
        for _ in total_miroir:
            n_miroir += 1
        faux_positifs_miroir: dict[str, int] = {}
        exemples_miroir: dict[str, list[str]] = defaultdict(list)
        # ⚠️ La règle stricte EXIGE une virgule : la borner par `LIKE '%, %'` ne
        # change pas son résultat, seulement le nombre de lignes traversées. La
        # lâche l'interdit, donc elle se lit sur tout le miroir.
        for etiquette, examiner in REGLES:
            requete_noms = select(REQEntry.nom)
            if examiner is examiner_stricte:
                requete_noms = requete_noms.where(REQEntry.nom.like("%,%"))
            k = 0
            for (nom,) in session.execute(
                requete_noms.execution_options(yield_per=20000)
            ):
                if examiner(nom) == RETENU:
                    k += 1
                    if len(exemples_miroir[etiquette]) < 5:
                        exemples_miroir[etiquette].append(nom)
            faux_positifs_miroir[etiquette] = k

        print(f"   entités nommées au miroir : {milliers(n_miroir)}\n")
        for etiquette, _examiner in REGLES:
            k = faux_positifs_miroir[etiquette]
            print(f"   {etiquette:<34} {milliers(k):>8} {_part(k, n_miroir):>8}"
                  f"   ← faux positifs")
            for exemple in exemples_miroir[etiquette]:
                print(f"      {exemple[:64]}")
        if not n_miroir:
            print("   ⚠️ MIROIR VIDE — ce n'est pas « 0 % de faux positifs », c'est")
            print("      ZÉRO MESURE. Le calibrage n'a pas eu lieu.")

        # ---- ce qui demande l'archive ---------------------------------------
        print("\n" + "-" * 78)
        print("5. CALIBRAGE — LA PRÉCISION SUR LES RÉSOLUS   ⚠️ CIBLE T1, PAS T2")
        print("-" * 78)
        if archive is None:
            print("""
   ⚠️ ZÉRO MESURE — pas « 0 % ». Sans --chemin, aucune forme juridique n'est
      lisible, et les sections 5, 6 et le volet « forme » de la 7 ne sont pas
      rendues. Relancer avec --chemin /opt/falkye/import.
""")
            return _verdict(None, None, n, retenus, faux_positifs_miroir, n_miroir)

        from outils.archives_req import avertissement, ligne_de_provenance

        print(f"\n   {ligne_de_provenance(archive)}")
        vieillissement = avertissement(archive)
        if vieillissement:
            print(f"   {vieillissement}")

        neq_des_resolus = {c.neq for c in resolus if c.neq}
        with zipfile.ZipFile(archive) as zf:
            libelles = charger_domaines(zf)
            physiques = codes_de_personne_physique(libelles)
            print("\n… lecture de Nom.csv puis d'Entreprise.csv (quelques minutes)",
                  flush=True)
            nommes = neqs_nommes(zf)
            forme_par_neq: dict[str, str] = {}
            formes_vues: Counter = Counter()
            physiques_total = 0
            physiques_sans_nom = 0
            with zf.open("Entreprise.csv") as brut:
                texte = io.TextIOWrapper(brut, encoding="utf-8-sig", errors="replace")
                for rangee in csv.DictReader(texte):
                    neq = (rangee.get("NEQ") or "").strip()
                    forme = (rangee.get("COD_FORME_JURI") or "").strip() or "(vide)"
                    formes_vues[forme] += 1
                    if forme in physiques:
                        physiques_total += 1
                        if neq not in nommes:
                            physiques_sans_nom += 1
                    if neq in neq_des_resolus:
                        forme_par_neq[neq] = forme

        if not libelles:
            print("\n   ⚠️ DomaineValeur.csv ABSENT — la classification se replie sur")
            print(f"      la seule graine `{CODE_PERSONNE_PHYSIQUE_CONNU}`. Ce n'est pas la même mesure,")
            print("      et le chiffre qui suit est un plancher d'un plancher.")
        print("\n   Les codes FORM_JURI comptés comme PERSONNE PHYSIQUE — libellés lus")
        print("   à la source, jamais recopiés de mémoire :\n")
        for codes, libelle in sorted(physiques.items()):
            print(f"      {codes:<8} {libelle[:56]}   ({milliers(formes_vues.get(codes, 0))} au registre)")
        print("\n   Les autres codes rencontrés, pour que la frontière se VOIE :\n")
        autres = [(c, k) for c, k in formes_vues.most_common() if c not in physiques]
        for codes, k in autres[:10]:
            print(f"      {codes:<8} {libelles.get(('FORM_JURI', codes), '')[:46]:<46}"
                  f" {milliers(k):>10}")
        if len(autres) > 10:
            print(f"      … et {milliers(len(autres) - 10)} autre(s) code(s).")

        print("\n   LA PRÉCISION, RÈGLE PAR RÈGLE — sur les dossiers RÉSOLUS :\n")
        precisions: dict[str, tuple[int, int]] = {}
        for etiquette, examiner in REGLES:
            flags = [c for c in resolus if examiner(c.nom_detecte) == RETENU]
            lisibles = [c for c in flags if c.neq in forme_par_neq]
            vrais = [c for c in lisibles if forme_par_neq[c.neq] in physiques]
            faux = len(lisibles) - len(vrais)
            precisions[etiquette] = (faux, len(lisibles))
            if not lisibles:
                print(f"   {etiquette:<34} ZÉRO MESURE — aucun résolu retenu par")
                print("      cette règle n'a de forme juridique lisible. Ce n'est pas")
                print("      « 0 % de faux positifs ».")
                continue
            print(f"   {etiquette:<34} {milliers(len(lisibles)):>8} résolu(s) retenu(s)")
            print(f"      dont personnes physiques (vrais) {milliers(len(vrais)):>8} "
                  f"{_part(len(vrais), len(lisibles)):>8}")
            print(f"      dont entreprises      (FAUX POSITIFS) {milliers(faux):>8} "
                  f"{_part(faux, len(lisibles)):>8}")
        print("""
   ⚠️ CE QUE CETTE SECTION MESURE EST T1, PAS T2. Un résolu retenu par la
      règle ET réellement personne physique est un VRAI positif pour « c'est
      une personne physique » — et un dossier que le registre A NOMMÉ, donc
      pas hors de portée. La précision T1 ne se lit pas comme une précision
      T2, et c'est la section 6 qui fait le pont.

   ⚠️ ET LE TAUX DE FAUX NÉGATIFS N'EST MESURABLE NULLE PART. La population
      témoin est faite de dossiers que le registre a nommés : elle ne
      contient presque aucune personne physique sans nom, c'est-à-dire
      exactement celles qu'on cherche. On mesure donc ce qui déborde, jamais
      ce qui manque — et c'est pour ça que le chiffre est un PLANCHER.
""")

        # ---- 6. LE PONT T1 → T2 ---------------------------------------------
        print("-" * 78)
        print("6. LE PONT T1 → T2 — mesuré, SANS heuristique   ✅ MESURE")
        print("-" * 78)
        taux_pont = 100 * physiques_sans_nom / physiques_total if physiques_total else None
        print(f"""
   « Personne physique » ne veut pas dire « hors de portée » : celle qui a
   déclaré un nom d'emprunt est nommée, donc joignable. La part qui compte
   est celle des personnes physiques SANS AUCUN nom publié — et elle se lit
   directement dans l'archive, sans supposer quoi que ce soit.

   personnes physiques au registre          {milliers(physiques_total):>12}
   dont AUCUN nom dans Nom.csv              {milliers(physiques_sans_nom):>12}"""
              f"   {_part(physiques_sans_nom, physiques_total):>8}")
        if taux_pont is None:
            print("\n   ⚠️ ZÉRO MESURE — aucune personne physique lue. Le pont n'existe")
            print("      pas dans cette archive, et ce n'est pas « 0 % ».")

        # ---- 7. MÉTHODE B — par la source ------------------------------------
        print("\n" + "-" * 78)
        print("7. MÉTHODE B — PAR LA SOURCE   ✅ base mesurée, ⚠️ report extrapolé")
        print("-" * 78)
        sources: dict[int, set[str]] = defaultdict(set)
        for company_id, source_id in session.execute(
            select(Signal.company_id, Signal.source_id).execution_options(yield_per=2000)
        ):
            sources[company_id].add(source_id)
        restants_par_source: Counter = Counter()
        resolus_par_source: Counter = Counter()
        physiques_par_source: Counter = Counter()
        for c in restants:
            for s in sources.get(c.id, {"(aucun signal)"}):
                restants_par_source[s] += 1
        for c in resolus:
            lisible = forme_par_neq.get(c.neq)
            for s in sources.get(c.id, {"(aucun signal)"}):
                if lisible is not None:
                    resolus_par_source[s] += 1
                    if lisible in physiques:
                        physiques_par_source[s] += 1
        print("""
   Le taux de personnes physiques CHEZ LES RÉSOLUS d'une source est une
   base réelle, pas une intuition sur ce que la source capte.

   ⚠️ ET CE TAUX EST LUI-MÊME UN PLANCHER. Une personne physique n'apparaît
      chez les résolus que si elle a déclaré un nom; celles qui n'en ont
      déclaré aucun sont invisibles de cette colonne comme de partout
      ailleurs. La source qui en capte le plus est donc sous-estimée.
""")
        print(f"   {'source':<28} {'restants':>9} {'résolus lus':>12} "
              f"{'pers. phys.':>12} {'taux':>8}")
        for source, k in restants_par_source.most_common():
            lus = resolus_par_source.get(source, 0)
            phys = physiques_par_source.get(source, 0)
            taux = _part(phys, lus) if lus else "ZÉRO MES."
            print(f"   {source:<28} {milliers(k):>9} {milliers(lus):>12} "
                  f"{milliers(phys):>12} {taux:>8}")
        print("\n   ⚠️ Un dossier CUMULE ses signaux : il compte dans CHAQUE source qui")
        print("      l'a vu. Les colonnes ne s'additionnent pas au total.")
        print("   ⚠️ « ZÉRO MES. » est une source dont aucun résolu n'a de forme")
        print("      juridique lisible. Ce n'est pas un taux de 0 %.")

        return _verdict(precisions, taux_pont, n, retenus,
                        faux_positifs_miroir, n_miroir)
    finally:
        session.close()


#: La largeur du libellé dans le tableau du produit. ⚠️ **Un libellé plus long
#: que sa colonne POUSSE le nombre** : la ligne cesse d'être alignée sans qu'aucun
#: chiffre ait changé, et un tableau désaligné se relit de travers.
LARGEUR_DU_PRODUIT = 46

#: L'étiquette de la règle qui, seule, peut porter un plancher. *Lue dans
#: `REGLES` plutôt que recopiée* — une étiquette recopiée survit au
#: renommage de ce qu'elle désigne.
ETIQUETTE_STRICTE = REGLES[0][0]


def _verdict(precisions: dict[str, tuple[int, int]] | None,
             taux_pont: float | None,
             n_restants: int,
             retenus: dict[str, list],
             faux_positifs_miroir: dict[str, int],
             n_miroir: int) -> int:
    """Ce que la mesure rend, **et ce qu'elle ne rend pas.**

    ⚠️ *Le verdict lit la section 5 — la précision sur les résolus — et rien
    d'autre.* **La spécificité du miroir est une AUTRE grandeur**, et la
    substituer pour avoir un verdict serait exactement la confusion que cet outil
    existe pour éviter. *Quand la section 5 manque, le verdict n'est pas rendu.*
    """
    print("\n" + "-" * 78)
    print("8. CE QUI A ÉTÉ ÉCARTÉ, ET POURQUOI — pour que l'absence se discute")
    print("-" * 78)
    print("""
   LA JOINTURE PAR LE NEQ. Sans clé : un restant n'a pas de NEQ, et les NEQ
      qu'on cherche n'ont pas de nom. Les deux côtés manquent le même champ.

   LA JOINTURE PAR L'ADRESSE. Écartée, et pas faute de données : une adresse
      porte plusieurs entreprises, et un appariement par l'adresse seule
      fabriquerait des faux positifs en masse. Ce serait déborder, donc
      l'inverse de l'erreur qu'on préfère.

   NOM_ETAB. Déjà mesuré, et clos : 5 récupérations, toutes de forme `IND`.
      Rien à remesurer, et ce chemin ne rendra pas davantage.

   UNE LISTE DE PRÉNOMS. Écartée : nous n'en avons aucune, et en inventer une
      remplacerait une heuristique nommée par une heuristique cachée.
""")

    print("-" * 78)
    print("9. LE VERDICT")
    print("-" * 78)

    plancher_brut = len(retenus.get(ETIQUETTE_STRICTE, []))
    if n_miroir:
        k = faux_positifs_miroir.get(ETIQUETTE_STRICTE, 0)
        print(f"\n   SPÉCIFICITÉ (section 4, mesure) : la règle stricte accuserait")
        print(f"   {milliers(k)} des {milliers(n_miroir)} entités NOMMÉES du miroir, "
              f"soit {_part(k, n_miroir)}.")

    if precisions is None or ETIQUETTE_STRICTE not in precisions:
        print("""
   ⛔ LE VERDICT N'EST PAS RENDU. La section 5 n'a pas eu lieu, et c'est elle
      seule qui le décide. La spécificité ci-dessus est une AUTRE grandeur :
      la substituer pour obtenir un verdict serait la confusion que cet outil
      existe pour éviter.

      Relancer avec --chemin pour que la règle du verdict s'applique.
""")
        return 0

    faux, lisibles = precisions[ETIQUETTE_STRICTE]
    if not lisibles:
        print("""
   ⛔ LE VERDICT N'EST PAS RENDU. Aucun résolu retenu par la règle stricte
      n'a de forme juridique lisible : la section 5 est ZÉRO MESURE, pas un
      taux de 0 %. La règle n'est ni confirmée ni réfutée.
""")
        return 0

    taux_faux = 100 * faux / lisibles
    tient = taux_faux < FAUX_POSITIFS_MAX_POUR_UN_PLANCHER
    print(f"\n   PRÉCISION (section 5, mesure) : {milliers(faux)} faux positif(s) sur "
          f"{milliers(lisibles)} résolu(s) retenu(s), soit {taux_faux:.1f} %.")
    print(f"   La règle posée d'avance : tient sous "
          f"{FAUX_POSITIFS_MAX_POUR_UN_PLANCHER:.0f} %.")

    if not tient:
        print(f"""
   ⛔ LA MÉTHODE A NE TIENT PAS. {taux_faux:.1f} % dépasse le seuil posé avant
      la mesure. Un plancher qui compte une entreprise sur cinq à tort n'est
      plus un plancher, et le desserrer parce qu'il a échoué n'en ferait plus
      un critère.

      AUCUN CHIFFRE DE PLANCHER N'EST POSÉ. C'est un résultat : avec ce que
      nous avons, la part des restants hors de portée par nature n'est pas
      connaissable par la forme du nom.
""")
        return 0

    print(f"""
   ✅ LA RÈGLE STRICTE TIENT comme plancher, à ses réserves près.

   ⚠️ MAIS LA PRÉCISION EST MESURÉE SUR LES RÉSOLUS, qui ne sont pas les
      restants. Les résolus sont sélectionnés pour être nommés par le
      registre; les restants pour ne pas l'être. Le taux ci-dessus est donc
      une INDICATION portée d'une population à l'autre, jamais un transfert.
""")

    print(f"   {'restants retenus par la règle stricte':<{LARGEUR_DU_PRODUIT}} "
          f"{milliers(plancher_brut):>10}   ⚠️ HEURISTIQUE")
    if taux_pont is None:
        print("""
   ⛔ ET LE PONT T1 → T2 MANQUE. Sans lui, ce compte reste « des restants dont
      le nom a la forme d'un patronyme » — pas « des restants hors de portée ».
      Les deux ne sont pas le même chiffre, et le second n'est pas posé.
""")
        return 0
    plancher = plancher_brut * taux_pont / 100
    print(f"   {'× part des personnes physiques SANS nom publié':<{LARGEUR_DU_PRODUIT}} "
          f"{taux_pont:>9.1f} %   ✅ MESURE")
    print(f"   {'= plancher des restants HORS DE PORTÉE':<{LARGEUR_DU_PRODUIT}} "
          f"{milliers(round(plancher)):>10} {_part(round(plancher), n_restants):>8}")
    print(f"""
   ⚠️ CE CHIFFRE EST UN PRODUIT, ET SES DEUX FACTEURS NE SONT PAS DE MÊME
      NATURE. Le premier est une HEURISTIQUE sur la forme d'un nom; le second
      une MESURE sur l'archive. Le produit hérite de la faiblesse du premier,
      jamais de la solidité du second.

   ⚠️ ET LE TAUX DU PONT EST MESURÉ SUR TOUTES les personnes physiques du
      registre, alors que les restants sont celles qu'UNE SOURCE A DÉTECTÉES —
      donc qui portent une activité réelle. Rien ne dit que les deux
      populations déclarent un nom au même rythme. C'est une extrapolation,
      et elle est nommée plutôt que fondue dans le produit.

   CE QUE CE CHIFFRE N'EST PAS : une mesure. Ce qu'il est : un PLANCHER
   ESTIMÉ, dont les deux faiblesses sont écrites au-dessus de lui pour qu'il
   ne se relise pas comme un plancher mesuré dans trois semaines.
""")
    print("=" * 78)
    print("   RIEN N'A ÉTÉ ÉCRIT. Les échelles n'ont pas bougé.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
