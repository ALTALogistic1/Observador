#!/usr/bin/env python3
"""Le portrait des restants — **ce qu'ils SONT, pas pourquoi ils échouent.**

## ⚠️ LE MOTIF, ET IL DÉCIDE DE LA FORME DE CETTE MESURE

**Cinq théories ont été examinées, et aucune n'explique le gros des 4 673** :

| théorie | ce qu'elle rend |
|---|---|
| origine pancanadienne | 8 % |
| consortiums *(deux formes juridiques)* | 1,1 % |
| doublons exacts du produit | 0,4 % |
| absence d'adresse | **+0** des deux côtés |
| personnes physiques | **non connaissable** — 57,1 % de faux positifs |

**La règle du corpus pour cette série : quand plusieurs hypothèses bien mesurées
tombent, la question est mal posée.** *Alors on part des dossiers, pas d'une
idée.*

## ⚠️ CE QUE CETTE MESURE NE FERA PAS — et ça se lit avant les chiffres

**Elle ne dira pas POURQUOI ils échouent. Elle dit ce qu'ils sont.** *C'est un
portrait de population, pas une explication* — et c'est précisément ce qui manque
après cinq hypothèses.

⚠️ **AUCUN CLASSEMENT PAR JUGEMENT.** Pas de catégorie *« probablement
récupérable »* ni *« probablement pas »* : **ce serait remplacer la mesure par une
sixième théorie.** *Les axes sont des faits que le produit porte; leur lecture
vient après, et elle est d'Alexandre.*

## Les axes, et d'où chacun vient — aucune heuristique, aucun champ inventé

| axe | porté par |
|---|---|
| famille de décision | `falkye.resolution.famille_de` — **la fonction du produit** |
| candidats, meilleur score | `req.resolve_neq_by_name` — **le chemin de production** |
| signaux, sources distinctes | `Signal` — ⚠️ *personne ne l'avait regardé* |
| finesse d'adresse | `departageur_adresse.faits_des_dossiers` |
| forme du nom | `Company.nom_detecte`, et `est_numero` du diagnostic |
| âge du signal le plus récent | `Signal.detected_at` — ⚠️ *jamais regardé non plus* |

⚠️ **`detected_at` est la date de l'ÉVÈNEMENT SOURCE, `ingested_at` celle de notre
collecte.** *Lire la seconde mesurerait nos cycles, pas l'activité des dossiers.*

## ⚠️ Et une ventilation des restants SEULE ne dit rien

*« 38 % des restants n'ont qu'un signal »* **ne se compare à rien.** Les quatre
axes que les résolus portent aussi — signaux, adresse, forme du nom, âge — sont
donc rendus **sur les deux populations, avec le rapport**. *Les deux premiers axes
n'existent que pour les restants : un résolu porte déjà son NEQ.*

⚠️ **AUCUNE ÉCRITURE. Les échelles ne bougent pas : seuil 92, écart 8.**

Usage, SUR L'HÔTE :
    python3 -m outils.portrait_des_restants
    python3 -m outils.portrait_des_restants --limite 500
"""
from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

from outils.nombres import milliers

# ⚠️ **Empruntées, jamais recopiées.** *Une règle de décision recopiée mesurerait
# sa propre copie* — et `est_numero` porte déjà la réserve sur les dénominations
# numériques, qu'une seconde écriture perdrait.
from outils.diagnostic_appariement import est_numero

#: Les tranches de candidats. ⚠️ **Elles sont un GRAIN D'AFFICHAGE, pas une
#: frontière du produit** — la seule frontière qui décide est le seuil, et elle
#: vit dans `falkye/resolution.py`. *Dire lesquelles sont arbitraires évite
#: qu'on leur prête un sens dans trois semaines.*
#: ⚠️ **CORRIGÉ le 22 septembre.** *Les tranches allaient jusqu'à « plus de 100 »,
#: et TROIS D'ENTRE ELLES NE POUVAIENT JAMAIS SE REMPLIR* — `resolve_neq_by_name`
#: coupe le lot à cinq. **La sortie annonçait donc « 94,9 %, aucun n'en a plus de
#: 5 » comme un fait de population, alors que c'est le plafond de l'instrument.**
#: *Relevé par Alexandre en lisant le plan de travail : la ligne allait entrer au
#: corpus.* **Les tranches s'arrêtent maintenant à la coupe, et la coupe est LUE.**
TRANCHES_DE_CANDIDATS = ((0, "aucun"), (1, "1"), (2, "2"), (None, "3 à la coupe"))

#: Les tranches de score. ⚠️ **Seule la borne du seuil a un sens** : au-dessus,
#: le dossier est assez sûr et n'échoue que par l'écart au second. Les autres
#: bornes sont du grain d'affichage.
TRANCHES_DE_SCORE = ((0.0, "aucun candidat"), (50.0, "moins de 50"),
                     (70.0, "50 à 69"), (85.0, "70 à 84"), (90.0, "85 à 89"),
                     (92.0, "90 à 91,9 ← sous le seuil"),
                     (None, "92 et plus ← FRANCHIT le seuil"))

#: La largeur de la colonne des étiquettes. ⚠️ **Une étiquette plus longue POUSSE
#: le nombre** : la ligne cesse d'être alignée sans qu'aucun chiffre ait changé.
#: *C'est arrivé trois fois; un test le vérifie désormais au lieu d'un relecteur.*
LARGEUR_DES_AXES = 30

TRANCHES_DE_SIGNAUX = ((1, "1 seul"), (2, "2"), (5, "3 à 5"), (None, "6 et plus"))
TRANCHES_DE_SOURCES = ((1, "1 seule"), (2, "2"), (None, "3 et plus"))

#: ⚠️ **La borne d'un an est celle qu'Alexandre a soulevée**, les autres sont du
#: grain. *Un dossier dont l'activité date de plus d'un an n'a peut-être pas à
#: être récupéré — mais cette mesure ne le dit pas, elle le compte.*
TRANCHES_DAGE = ((30, "30 jours ou moins"), (90, "31 à 90 jours"),
                 (180, "91 à 180 jours"), (365, "181 à 365 jours"),
                 (None, "PLUS D'UN AN"))

#: L'échelle d'adresse, **EXCLUSIVE et du plus fin au plus grossier**. ⚠️ *Un code
#: complet porte toujours sa région de tri — `codes_postaux` pose `jeton[:3]` à
#: côté de chaque code complet.* **Les compter tous les deux ferait un total qui
#: dépasse la population**, et c'est l'erreur que l'échelle interdit.
NIVEAU_CODE_COMPLET = "code postal complet"
NIVEAU_REGION_DE_TRI = "région de tri SEULE"
NIVEAU_VILLE = "ville SEULE"
NIVEAU_RIEN = "rien"
ECHELLE_DADRESSE = (NIVEAU_CODE_COMPLET, NIVEAU_REGION_DE_TRI, NIVEAU_VILLE,
                    NIVEAU_RIEN)

#: Ce qui sépare deux entités dans un champ, **au sens du CARACTÈRE**. ⚠️ *Ce
#: n'est PAS la règle stricte de `nature_des_restants`*, qui exige deux formes
#: juridiques et rendait 1,1 %. **Les deux chiffres ne sont pas comparables**, et
#: celui-ci est le fait brut : « ce nom porte une conjonction ».
CONJONCTION = re.compile(r"\s+et\s+|\s*&\s*", re.IGNORECASE)

FORME_TETE_NUMERIQUE = "tête numérique (9xxx…)"
FORME_TOUTES_LETTRES = "nom en toutes lettres"
FORME_PARENTHESE = "porte une parenthèse"
FORME_CONJONCTION = "porte une conjonction"

#: ⚠️ **Ces formes NE SONT PAS exclusives** — un nom peut en porter trois. *Les
#: additionner donnerait un total supérieur à la population*, et la sortie le dit
#: à l'endroit où le total pourrait être lu comme une partition.
FORMES_DU_NOM = (FORME_TETE_NUMERIQUE, FORME_TOUTES_LETTRES, FORME_PARENTHESE,
                 FORME_CONJONCTION)

TRANCHES_DE_LONGUEUR = ((1, "1 mot"), (2, "2 mots"), (3, "3 mots"), (4, "4 mots"),
                        (None, "5 mots et plus"))


def _tranche(valeur, tranches):
    """La première tranche dont la borne HAUTE n'est pas dépassée. *La dernière a
    une borne `None` et prend tout le reste* — un `None` n'est pas zéro, c'est
    « sans borne »."""
    for borne, etiquette in tranches:
        if borne is None or valeur <= borne:
            return etiquette
    return tranches[-1][1]


def tranche_de_candidats(k: int) -> str:
    return _tranche(k, TRANCHES_DE_CANDIDATS)


def tranche_de_score(meilleur: float | None) -> str:
    """`None` quand il n'y a **aucun candidat** — et ce n'est pas un score de 0."""
    if meilleur is None:
        return TRANCHES_DE_SCORE[0][1]
    for borne, etiquette in TRANCHES_DE_SCORE[1:]:
        if borne is None or meilleur < borne:
            return etiquette
    return TRANCHES_DE_SCORE[-1][1]


def tranche_de_signaux(k: int) -> str:
    return _tranche(k, TRANCHES_DE_SIGNAUX)


def tranche_de_sources(k: int) -> str:
    return _tranche(k, TRANCHES_DE_SOURCES)


def tranche_dage(jours: int | None) -> str:
    """`None` quand le dossier n'a **aucun signal daté**. *Une absence de date et
    une date ancienne ne sont pas le même fait.*"""
    return "aucun signal daté" if jours is None else _tranche(jours, TRANCHES_DAGE)


def finesse_de(faits) -> str:
    """Le niveau le plus FIN que le dossier porte. **Exclusif.**"""
    if faits is None:
        return NIVEAU_RIEN
    if faits.code_complet is not None:
        return NIVEAU_CODE_COMPLET
    if faits.region_de_tri is not None:
        return NIVEAU_REGION_DE_TRI
    if faits.ville is not None:
        return NIVEAU_VILLE
    return NIVEAU_RIEN


def formes_du_nom(nom: str | None, nom_normalise: str | None) -> set[str]:
    """Les formes que porte ce nom. ⚠️ **Non exclusives**, sauf la tête."""
    trouvees: set[str] = set()
    trouvees.add(FORME_TETE_NUMERIQUE if est_numero(nom_normalise or "")
                 else FORME_TOUTES_LETTRES)
    if nom and ("(" in nom or ")" in nom):
        trouvees.add(FORME_PARENTHESE)
    if nom and CONJONCTION.search(nom):
        trouvees.add(FORME_CONJONCTION)
    return trouvees


def tranche_de_longueur(nom_normalise: str | None) -> str:
    """En MOTS de la forme normalisée. *Compter les caractères mêlerait la
    ponctuation au propos.*"""
    return _tranche(len((nom_normalise or "").split()), TRANCHES_DE_LONGUEUR)


def _part(k: int, n: int) -> str:
    return f"{100 * k / n:.1f} %" if n else "—"


def ventiler_les_deux(ordre, chez_les_restants: Counter, chez_les_resolus: Counter,
                      n_restants: int, n_resolus: int,
                      largeur: int = LARGEUR_DES_AXES) -> None:
    """Le même axe sur les DEUX populations, et le rapport des deux.

    ⚠️ *Une ventilation des restants seule ne dit pas « surreprésenté ».* **C'est
    le rapport qui le dit** — et une valeur que les résolus ne portent PAS est le
    cas le plus fort, pas un cas manquant : `AUCUN` plutôt qu'un tiret.
    """
    print(f"   {'':<{largeur}} {'restants':>9} {'part':>8} "
          f"{'résolus':>9} {'part':>8} {'rapport':>8}")
    for valeur in ordre:
        k = chez_les_restants.get(valeur, 0)
        r = chez_les_resolus.get(valeur, 0)
        part_rest = 100 * k / n_restants if n_restants else 0.0
        part_res = 100 * r / n_resolus if n_resolus else 0.0
        if part_res:
            rapport = f"×{part_rest / part_res:.1f}"
        else:
            rapport = "AUCUN" if k else "—"
        print(f"   {valeur:<{largeur}} {milliers(k):>9} {part_rest:>7.1f} % "
              f"{milliers(r):>9} {part_res:>7.1f} % {rapport:>8}")


def ventiler_seul(ordre, compteur: Counter, total: int,
                  largeur: int = LARGEUR_DES_AXES) -> None:
    """Un axe que **seuls les restants portent**. *Un résolu porte déjà son NEQ :
    lui rejouer une famille de décision ne dirait rien de son état.*"""
    for valeur in ordre:
        k = compteur.get(valeur, 0)
        print(f"   {valeur:<{largeur}} {milliers(k):>9} {_part(k, total):>8}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--limite", type=int, default=None,
                        help="borner le nombre de dossiers (mise au point)")
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
    from falkye.models.signal import Signal
    from falkye.resolution import (
        FAMILLES,
        SEUIL_AMBIGUITE_ECART_MIN,
        SEUIL_RESOLUTION_CONFIANTE,
        famille_de,
    )
    from falkye.sources.req import LIMITE_CANDIDATS_PAR_NOM
    from outils.departageur_adresse import champs_des_dossiers, faits_des_dossiers
    # ⚠️ **La résolution est REJOUÉE par le chemin de la passe**, pas par un
    # équivalent écrit ici. *`_resoudre_une` porte l'argument `ville=` que le
    # produit passe; le réécrire à côté ferait diverger les deux comptes sans
    # que rien ne le dise.*
    from outils.reresolution_neq import _resoudre_une
    from outils.valeur_des_contradictions import coupe_de_production

    coupe = coupe_de_production()

    print("=" * 78)
    print("LE PORTRAIT DES RESTANTS — ce qu'ils SONT, pas pourquoi ils échouent")
    print("=" * 78)
    print(f"""
⚠️ CE QUE CETTE MESURE NE FERA PAS — et ça se lit avant les chiffres

   ELLE NE DIRA PAS POURQUOI ILS ÉCHOUENT. Elle dit ce qu'ils SONT. C'est un
   portrait de population, pas une explication — et c'est précisément ce qui
   manque après cinq hypothèses bien mesurées qui sont toutes tombées.

   ⚠️ AUCUN CLASSEMENT PAR JUGEMENT. Pas de « probablement récupérable » ni
   de « probablement pas » : ce serait remplacer la mesure par une sixième
   théorie. Les axes sont des FAITS que le produit porte déjà; leur lecture
   vient après, et elle n'est pas de cet outil.

   ⚠️ ET UNE VENTILATION DES RESTANTS SEULE NE DIT RIEN. Les quatre axes que
   les résolus portent aussi sont rendus sur LES DEUX populations, avec le
   rapport. Les deux premiers n'existent que pour les restants : un résolu
   porte déjà son NEQ.

   LES BORNES DES TRANCHES SONT DU GRAIN D'AFFICHAGE. Les seules qui
   décident quelque chose sont les échelles du produit — seuil
   {SEUIL_RESOLUTION_CONFIANTE:.0f}, écart {SEUIL_AMBIGUITE_ECART_MIN:.0f} — et la borne d'un an, qu'Alexandre a
   soulevée. AUCUNE ÉCRITURE; les échelles ne bougent pas.
""")

    session = get_session()
    try:
        requete = select(Company).order_by(Company.id)
        if args.limite:
            requete = requete.limit(args.limite)
        tous = list(session.execute(requete).scalars().all())
        restants = [c for c in tous if c.neq is None]
        resolus = [c for c in tous if c.neq is not None]
        n, n_res = len(restants), len(resolus)
        print(f"   dossiers au total : {milliers(len(tous))}")
        print(f"   RESTANTS (sans NEQ) : {milliers(n)}"
              f"   ·   résolus : {milliers(n_res)}\n")
        if not restants:
            print("   Aucun restant à portraiturer.")
            return 0

        # ---- les faits que le produit porte, en une passe -------------------
        signaux: dict[int, int] = Counter()
        sources: dict[int, set[str]] = defaultdict(set)
        dernier: dict[int, datetime] = {}
        for company_id, source_id, quand in session.execute(
            select(Signal.company_id, Signal.source_id, Signal.detected_at)
            .execution_options(yield_per=2000)
        ):
            signaux[company_id] += 1
            sources[company_id].add(source_id)
            if quand is not None and (company_id not in dernier
                                      or quand > dernier[company_id]):
                dernier[company_id] = quand

        champs = champs_des_dossiers(session, {c.id for c in tous})
        faits = faits_des_dossiers(session, tous, champs=champs)

        maintenant = datetime.now(timezone.utc)

        def _age(company) -> int | None:
            quand = dernier.get(company.id)
            if quand is None:
                return None
            # *Une date sans fuseau vient de SQLite, qui n'en stocke pas.* La
            # lire comme UTC est ce que le reste du produit fait.
            if quand.tzinfo is None:
                quand = quand.replace(tzinfo=timezone.utc)
            return (maintenant - quand).days

        # ---- LE REJEU, restants seulement -----------------------------------
        print(f"… rejeu de la résolution sur {milliers(n)} restants, "
              f"par le chemin de production", flush=True)
        par_famille: Counter = Counter()
        par_candidats: Counter = Counter()
        par_score: Counter = Counter()
        famille_du_dossier: dict[int, str] = {}
        au_plafond = 0
        for i, company in enumerate(restants, 1):
            if args.pas and i % args.pas == 0:
                print(f"   … {milliers(i)} / {milliers(n)}", flush=True)
            _neq, matches = _resoudre_une(session, company)
            famille = famille_de(matches)
            famille_du_dossier[company.id] = famille
            par_famille[famille] += 1
            par_candidats[tranche_de_candidats(len(matches))] += 1
            if len(matches) >= coupe:
                au_plafond += 1
            par_score[tranche_de_score(matches[0].score if matches else None)] += 1

        # ---- 1. LA FAMILLE DE DÉCISION --------------------------------------
        print("\n" + "-" * 78)
        print("1. LA FAMILLE DE DÉCISION — la taxonomie du produit, rejouée")
        print("-" * 78)
        print(f"\n   {'':<{LARGEUR_DES_AXES}} {'dossiers':>9} {'part':>8}")
        ventiler_seul(FAMILLES, par_famille, n)
        print("""
   ⚠️ `RETENU` ici n'est pas une contradiction : c'est un dossier que le
      rejeu résoudrait AUJOURD'HUI et qui ne l'a pas été à l'ingestion — le
      miroir a grossi depuis. Ce compte ne dit pas qu'on doit l'écrire.
   ⚠️ `ambigu` et `trop faible` n'appellent pas le même correctif : l'un
      échoue sur l'ÉCART au second, l'autre sur le SEUIL. Les confondre fait
      attribuer au seuil une masse que l'écart retient.
""")

        # ---- 2. CANDIDATS ET MEILLEUR SCORE ---------------------------------
        print("-" * 78)
        print("2. CANDIDATS TROUVÉS, ET MEILLEUR SCORE OBTENU")
        print("-" * 78)
        print(f"\n   candidats rendus par le SCORAGE, coupés à {coupe}")
        print(f"   {'':<{LARGEUR_DES_AXES}} {'dossiers':>9} {'part':>8}")
        ventiler_seul([e for _b, e in TRANCHES_DE_CANDIDATS], par_candidats, n)
        print(f"""
   ⚠️ CET AXE NE MESURE PAS LA RÉCUPÉRATION. `resolve_neq_by_name` rend au
      plus {coupe} candidats ({milliers(au_plafond)} dossiers y sont). La récupération, elle,
      en ramène jusqu'à {milliers(LIMITE_CANDIDATS_PAR_NOM)} avant le scorage, et CE compte n'est
      pas lu ici. « Aucun dossier n'a plus de {coupe} candidats » serait donc une
      propriété de l'OUTIL, jamais des dossiers.""")
        print(f"\n   meilleur score obtenu")
        print(f"   {'':<{LARGEUR_DES_AXES}} {'dossiers':>9} {'part':>8}")
        ventiler_seul([e for _b, e in TRANCHES_DE_SCORE], par_score, n)
        print("""
   ⚠️ « aucun candidat » N'EST PAS un score de zéro. Un dossier à zéro
      candidat et un dossier à 91 ne sont pas le même problème — le premier
      n'a rien à départager, le second a tout sauf deux points.
""")

        # ---- 3. SIGNAUX ET SOURCES ------------------------------------------
        print("-" * 78)
        print("3. SIGNAUX ET SOURCES DISTINCTES   ⚠️ jamais regardé jusqu'ici")
        print("-" * 78)
        sig_r = Counter(tranche_de_signaux(signaux.get(c.id, 0)) for c in restants)
        sig_s = Counter(tranche_de_signaux(signaux.get(c.id, 0)) for c in resolus)
        src_r = Counter(tranche_de_sources(len(sources.get(c.id, ()))) for c in restants)
        src_s = Counter(tranche_de_sources(len(sources.get(c.id, ()))) for c in resolus)
        print("\n   nombre de SIGNAUX du dossier")
        ventiler_les_deux([e for _b, e in TRANCHES_DE_SIGNAUX], sig_r, sig_s, n, n_res)
        print("\n   nombre de SOURCES DISTINCTES")
        ventiler_les_deux([e for _b, e in TRANCHES_DE_SOURCES], src_r, src_s, n, n_res)
        print("""
   ⚠️ Ce que ce compte dit, et ce qu'il ne dit pas. Un dossier vu une seule
      fois par une seule source n'a pas la même nature qu'un dossier vu par
      trois — mais le rapport ne dit pas LAQUELLE des deux lectures est la
      bonne : un appariement plus faible, ou une entreprise moins réelle.
""")

        # ---- 4. LA FINESSE D'ADRESSE ----------------------------------------
        print("-" * 78)
        print("4. LA FINESSE D'ADRESSE — échelle EXCLUSIVE, du plus fin au plus large")
        print("-" * 78)
        adr_r = Counter(finesse_de(faits.get(c.id)) for c in restants)
        adr_s = Counter(finesse_de(faits.get(c.id)) for c in resolus)
        print()
        ventiler_les_deux(ECHELLE_DADRESSE, adr_r, adr_s, n, n_res)
        print("""
   ⚠️ L'ÉCHELLE EST EXCLUSIVE, et c'est ce qui la rend lisible. Un code
      complet porte TOUJOURS sa région de tri — `codes_postaux` pose
      `jeton[:3]` à côté de chaque code complet. Les compter tous les deux
      ferait un total supérieur à la population.
""")

        # ---- 5. LA FORME DU NOM ---------------------------------------------
        print("-" * 78)
        print("5. LA FORME DU NOM — des faits sur la chaîne, aucun jugement")
        print("-" * 78)
        formes_r: Counter = Counter()
        formes_s: Counter = Counter()
        formes_par_dossier: dict[int, set[str]] = {}
        for lot, cible in ((restants, formes_r), (resolus, formes_s)):
            for c in lot:
                trouvees = formes_du_nom(c.nom_detecte, c.nom_detecte_normalise)
                formes_par_dossier[c.id] = trouvees
                for forme in trouvees:
                    cible[forme] += 1
        print()
        ventiler_les_deux(FORMES_DU_NOM, formes_r, formes_s, n, n_res)
        print("\n   longueur du nom, en MOTS de la forme normalisée")
        lon_r = Counter(tranche_de_longueur(c.nom_detecte_normalise) for c in restants)
        lon_s = Counter(tranche_de_longueur(c.nom_detecte_normalise) for c in resolus)
        ventiler_les_deux([e for _b, e in TRANCHES_DE_LONGUEUR], lon_r, lon_s, n, n_res)
        print("""
   ⚠️ LES FORMES NE SONT PAS EXCLUSIVES — sauf la tête, qui est numérique ou
      ne l'est pas. Un nom peut porter une parenthèse ET une conjonction :
      les additionner dépasserait la population.
   ⚠️ « porte une conjonction » est le fait BRUT du caractère. Ce n'est pas
      la règle stricte des consortiums, qui exige DEUX formes juridiques et
      rendait 1,1 %. Les deux chiffres ne sont pas comparables.
""")

        # ---- 6. L'ÂGE DU SIGNAL LE PLUS RÉCENT ------------------------------
        print("-" * 78)
        print("6. L'ÂGE DU SIGNAL LE PLUS RÉCENT   ⚠️ jamais regardé jusqu'ici")
        print("-" * 78)
        age_r = Counter(tranche_dage(_age(c)) for c in restants)
        age_s = Counter(tranche_dage(_age(c)) for c in resolus)
        ordre_age = [e for _b, e in TRANCHES_DAGE] + ["aucun signal daté"]
        print()
        ventiler_les_deux(ordre_age, age_r, age_s, n, n_res)
        print("""
   ⚠️ `detected_at` EST LA DATE DE L'ÉVÈNEMENT SOURCE, pas celle de notre
      collecte — `ingested_at` est l'autre, et la lire mesurerait nos cycles.
   ⚠️ ET UNE DATE ANCIENNE NE VEUT PAS DIRE UNE ENTREPRISE DORMANTE. Une
      source qui publie un jeu de données daté rend des `detected_at` anciens
      sans que le dossier ait cessé d'exister. Ce compte dit l'âge du signal,
      jamais l'état de l'entreprise.
""")

        return _croisements(restants, famille_du_dossier, signaux, sources,
                            faits, formes_par_dossier, FAMILLES, n)
    finally:
        session.close()


#: Les familles, raccourcies pour tenir en colonne. ⚠️ **Les clés restent celles
#: du produit** — seul l'affichage est coupé, et un libellé recopié entier
#: divergerait le jour où `FAMILLES` change. **Une abréviation sans sa légende
#: se devine**, donc `_legende_des_familles` est imprimée au-dessus des tableaux.
ABREGE = {"RETENU": "RETENU", "ambigu": "ambigu", "trop faible": "faible",
          "aucun candidat": "aucun"}

#: La largeur d'une colonne de famille. *Une de plus que la plus longue
#: abréviation, pour que deux colonnes ne se touchent jamais* — elles se
#: touchaient, et deux nombres collés se lisent comme un seul.
LARGEUR_DUNE_FAMILLE = 11

#: Les largeurs d'étiquette, par croisement. ⚠️ *L'identifiant de source le plus
#: long du registre fait 34 caractères* — une colonne plus étroite le tronquerait,
#: et une source tronquée ne se reconnaît plus.
LARGEUR_DES_SIGNAUX = 18
LARGEUR_DES_SOURCES = 34
LARGEUR_DES_PROFILS = 30

#: « Adresse fine » veut dire **un code postal, à l'une ou l'autre résolution**.
#: *La ville seule n'en est pas une* — c'est ce que le départageur a établi le
#: 18 septembre, et le croisement emploie la même frontière.
AVEC_CODE = "avec code postal"
SANS_CODE = "sans code postal"
TETE_ABREGEE = {True: "tête num.", False: "lettres"}

#: Les quatre profils du croisement (c), **nommés ici plutôt que fabriqués dans
#: la boucle** — le test de largeur doit pouvoir les lire sans rejouer la mesure.
PROFILS = tuple(f"{t} · {c}" for t in TETE_ABREGEE.values()
                for c in (AVEC_CODE, SANS_CODE))


def _legende_des_familles(familles) -> None:
    """*Une abréviation sans sa légende se devine, et on devine mal.*"""
    # *Seules les abréviations qui CHANGENT le nom ont besoin d'être traduites.*
    paires = "  ·  ".join(f"{ABREGE[f]} = {f}" for f in familles
                          if ABREGE.get(f, f) != f)
    print(f"      colonnes abrégées : {paires}\n" if paires else "")


def _croiser(lignes, familles, largeur: int) -> None:
    """Un tableau `ligne × famille`, **en parts de la ligne**.

    ⚠️ *Le compte de la ligne est rendu à côté du pourcentage.* **Une part sans
    sa base se lit de travers** — `100 %` sur trois dossiers et `100 %` sur
    trois mille ne disent pas la même chose.
    """
    entete = "".join(f"{ABREGE.get(f, f):>{LARGEUR_DUNE_FAMILLE}}" for f in familles)
    print(f"   {'':<{largeur}} {'dossiers':>8}{entete}")
    for etiquette, compteur in lignes:
        total = sum(compteur.values())
        cellules = "".join(
            f"{(100 * compteur.get(f, 0) / total):>{LARGEUR_DUNE_FAMILLE - 1}.1f}%"
            if total else f"{'—':>{LARGEUR_DUNE_FAMILLE}}"
            for f in familles
        )
        print(f"   {etiquette:<{largeur}} {milliers(total):>8}{cellules}")


def _croisements(restants, famille_du_dossier, signaux, sources, faits,
                 formes_par_dossier, familles, n: int) -> int:
    """Les croisements — **l'objet réel de la demande.**

    *Les six axes disent ce que la population est; les croisements disent si deux
    faits vont ensemble.* ⚠️ **Aller ensemble n'est pas expliquer**, et la sortie
    le redit sous chaque tableau plutôt qu'une fois en tête.
    """
    print("-" * 78)
    print("7. LES CROISEMENTS — deux faits ensemble, jamais une cause")
    print("-" * 78)
    print()
    _legende_des_familles(familles)

    # --- a. les dossiers à un seul signal se résolvent-ils moins bien? ------
    print("   a. LA FAMILLE SELON LE NOMBRE DE SIGNAUX\n")
    par_signaux: dict[str, Counter] = defaultdict(Counter)
    for c in restants:
        par_signaux[tranche_de_signaux(signaux.get(c.id, 0))][
            famille_du_dossier[c.id]] += 1
    _croiser([(e, par_signaux[e]) for _b, e in TRANCHES_DE_SIGNAUX], familles,
             LARGEUR_DES_SIGNAUX)

    # --- b. les trop faibles sont-ils concentrés sur une source? ------------
    print("\n   b. LA FAMILLE SELON LA SOURCE\n")
    par_source: dict[str, Counter] = defaultdict(Counter)
    for c in restants:
        for source in sources.get(c.id, {"(aucun signal)"}):
            par_source[source][famille_du_dossier[c.id]] += 1
    ordonnees = sorted(par_source.items(), key=lambda kv: -sum(kv[1].values()))
    _croiser([(s, compteur) for s, compteur in ordonnees], familles,
             LARGEUR_DES_SOURCES)
    print("\n      ⚠️ Un dossier CUMULE ses signaux : il compte dans CHAQUE source")
    print("         qui l'a vu. Les lignes ne s'additionnent pas au total.")

    # --- c. la forme du nom croisée à la finesse d'adresse ------------------
    print("\n   c. LA FAMILLE SELON LA FORME DU NOM ET L'ADRESSE\n")
    par_profil: dict[str, Counter] = defaultdict(Counter)
    for c in restants:
        tete = (FORME_TETE_NUMERIQUE
                if FORME_TETE_NUMERIQUE in formes_par_dossier[c.id]
                else FORME_TOUTES_LETTRES)
        finesse = finesse_de(faits.get(c.id))
        code = (AVEC_CODE if finesse in (NIVEAU_CODE_COMPLET, NIVEAU_REGION_DE_TRI)
                else SANS_CODE)
        abrege = TETE_ABREGEE[tete == FORME_TETE_NUMERIQUE]
        par_profil[f"{abrege} · {code}"][famille_du_dossier[c.id]] += 1
    _croiser([(p, par_profil[p]) for p in PROFILS], familles,
             LARGEUR_DES_PROFILS)
    print("""
      ⚠️ « Avec code postal » veut dire un code, à l'une OU l'autre
         résolution. La ville seule n'en est pas un — même frontière que
         celle que le départageur a établie le 18 septembre.
""")

    print("=" * 78)
    print("   RIEN N'A ÉTÉ ÉCRIT. Les échelles n'ont pas bougé.")
    print(f"   {milliers(n)} restants décrits sur six axes et trois croisements.")
    print("   ⚠️ CE PORTRAIT NE DIT PAS POURQUOI ILS ÉCHOUENT. Deux faits qui vont")
    print("   ensemble n'en expliquent aucun — la lecture vient après, et elle")
    print("   n'est pas de cet outil.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
