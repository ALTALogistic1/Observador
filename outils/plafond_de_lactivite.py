#!/usr/bin/env python3
"""Le PLAFOND de la piste de l'activité économique — **et rien d'autre.**

## ⚠️ CE QUE CETTE MESURE NE DIRA PAS — et ça se lit avant tout chiffre

**Qu'un départage par l'activité serait JUSTE.** *Elle dit où le fait existe des
deux côtés, jamais s'il tranche bien.*

**Ni combien seraient effectivement départagés.** *Il faudrait pour ça relier
l'UNSPSC du contrat public au CAE du registre, et **cette table n'existe pas**.*
⚠️ **Elle appartient au chantier 22, qui n'est pas ouvert.** *Cet outil ne la
construit pas, ne l'esquisse pas, et ne nomme aucune famille* — remplir sa place
d'avance produirait ce que le cas 39 a coûté.

## ⚠️ ET LA POPULATION N'EST PAS CELLE DU 17 SEPTEMBRE

`outils/mesure_des_departageurs.py` a rendu **166 départagés, 97 en propre** —
mais **sur 5 002 ambigus, avant les deux écritures du 19**. *Le compte d'ambigus
d'aujourd'hui est imprimé ci-dessous.* **Deux chiffres pris sur deux populations
ne se comparent pas**, et la sortie le redit à l'endroit où la tentation serait
de les soustraire.

## Ce que la lecture du code a corrigé, avant de compter

⚠️ **« L'EIMT n'a aucune classification » est à moitié faux, et la moitié qui
reste change le compte.** *Lu dans `falkye/sources/eimt.py` :*

- **Elle ne promeut AUCUNE activité d'entreprise.** *Aucun `secteur_activite=`
  sur son `RawSignal`* — sur ce point l'affirmation tenait.
- **Mais elle porte `champs["profession"]`**, la colonne `Occupation` du fichier,
  aussi posée en `titre_ou_description`. ⚠️ **C'est la profession d'un POSTE, pas
  l'activité d'une ENTREPRISE.** *`« Cuisinier »` suggère un restaurant sans le
  dire*, et la traduire en CAE demanderait **une autre table encore**, distincte
  de celle de l'UNSPSC. **Elle est donc comptée à part, et jamais versée au
  plafond.**

⚠️ **Et `Company.secteur_activite_code` ne peut PAS être rempli sur un restant.**
*Son seul écrivain est `_enrich_from_req`, qui exige un NEQ résolu*
(`falkye/resolution.py`). **Le code confirme ce que la mesure comptera; la mesure
le vérifie quand même**, parce qu'une garde qui se déduit n'est pas une garde.

## ⚠️ Ce que le registre porte VRAIMENT, et le 99,6 % ne s'y transporte pas

**`COD_ACT_ECON_CAE` est rempli à 99,6 % dans l'archive. `REQEntry.secteur_code`
n'est pas cette colonne.** *Lu dans `falkye/sources/req.py::_resoudre_entreprise` :*
**quand un établissement principal existe, le code vient de
`Etablissements.csv::COD_ACT_ECON`, et `COD_ACT_ECON_CAE` n'est jamais lu.**
Sinon seulement, il vient de `COD_ACT_ECON_CAE`.

⚠️ **Donc le code stocké a DEUX provenances, et son origine n'est pas
conservée.** *Rien dans le miroir ne dit laquelle a servi pour une entrée
donnée.* **Le quatrième compte en hérite** : deux codes qui diffèrent pourraient
différer parce qu'ils ne viennent pas de la même colonne. *C'est une réserve qui
se nomme et ne se mesure pas — l'information n'est plus là.*

## Les quatre comptes

1. **Côté détecté** — combien des restants portent une activité, **par source, avec
   le champ exact qui la porte**.
2. **Côté registre** — combien de leurs candidats portent une activité. ⚠️ *Ce qui
   compte est le remplissage **chez ces candidats-là**, pas dans la population
   générale.*
3. **L'INTERSECTION** — les dossiers où **les deux côtés** portent une activité.
   **C'est le plafond.**
4. **Au moins deux candidats dont les codes du registre DIFFÈRENT entre eux.**
   ⚠️ *Porter une activité des deux côtés ne départage rien si tous les candidats
   portent la MÊME.* **Aucune correspondance entre nomenclatures n'est employée :
   c'est une comparaison de codes du registre entre eux.**

⚠️ **AUCUNE ÉCRITURE. Les échelles ne bougent pas : seuil 92, écart 8.**

Usage, SUR L'HÔTE :
    python3 -m outils.plafond_de_lactivite
    python3 -m outils.plafond_de_lactivite --comparer 20
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path

from outils.nombres import milliers

# ⚠️ **Le lecteur d'arbre syntaxique est EMPRUNTÉ, jamais recopié.** *Un second
# lecteur diverge du premier sans que rien ne le dise.*
from outils.adresse_par_connecteur import (
    DOSSIER_CONNECTEURS,
    champs_promus_par_le_module,
    cles_du_sac_par_le_module,
    cles_lues_par_le_module,
)

#: L'emplacement de `RawSignal` qui porte une activité PROMUE. *Le seul que
#: `falkye/resolution.py` lit ensuite pour écrire `Company`.*
CHAMP_PROMU = "secteur_activite"

#: Les clés de `Signal.champs` qui portent une activité, **par source**, avec ce
#: qu'elles sont. ⚠️ **Relevées en lisant chaque connecteur, et RECOUPÉES par
#: l'arbre syntaxique** en section 1 — une clé qui apparaîtrait sans entrer ici
#: se voit, au lieu de disparaître.
#:
#: ⚠️ **Le recoupement lit ce que le connecteur ÉCRIT dans `champs=`, pas ce
#: qu'il LIT de son fichier.** *Recoupée contre les clés lues, cette table
#: passerait pour vérifiée sans l'être* — `secteur_nature_contrat` n'est lue
#: nulle part, elle est déposée.
CODE = "code"
LIBELLE = "libellé"
PROFESSION = "profession d'un poste"

CLES_DACTIVITE = {
    "seao": ("secteur_nature_contrat", CODE, "UNSPSC, porté par items[].classification"),
    "contrats_federaux": ("objet_economique", CODE, "economic_object_code"),
    # ⚠️ **Comptée à part, jamais versée au plafond.**
    "eimt": ("profession", PROFESSION, "colonne Occupation du fichier"),
}

#: Ce qui, dans un nom de champ, annonce une activité. *Une observation des clés
#: rencontrées, pas une norme* — et volontairement large : **mieux vaut lister un
#: champ qui n'en est pas que taire celui qui l'est.**
import re  # noqa: E402 -- placé près du motif qu'il sert

INDICE_DACTIVITE = re.compile(
    r"secteur|activit|classification|unspsc|cae|naics|scian|objet_econom|"
    r"profession|occupation|type_entreprise|industri|bien_service",
    re.IGNORECASE,
)

#: Les provenances du fait détecté, **séparées parce qu'elles ne valent pas la
#: même chose**. *Un code se relie par une table; un libellé se compare mot à
#: mot; une profession ne dit pas l'activité d'une entreprise.*
PROVENANCES = (
    ("un CODE dans Signal.champs", CODE),
    ("un LIBELLÉ promu au dossier", LIBELLE),
    ("une PROFESSION (comptée à part)", PROFESSION),
)


def _part(k: int, n: int) -> str:
    return f"{100 * k / n:.1f} %" if n else "—"


def activites_du_dossier(company, champs: dict | None) -> dict[str, list[str]]:
    """Ce que ce dossier porte comme activité, **par provenance.**

    *Rend les valeurs plutôt qu'un booléen* : la sortie doit pouvoir montrer le
    champ exact, et un booléen ne le permettrait pas.
    """
    trouve: dict[str, list[str]] = defaultdict(list)
    if company.secteur_activite_libelle:
        trouve[LIBELLE].append(company.secteur_activite_libelle)
    for _source, (cle, nature, _note) in CLES_DACTIVITE.items():
        valeur = (champs or {}).get(cle)
        if valeur:
            trouve[nature].append(str(valeur)[:80])
    return dict(trouve)


def codes_des_candidats(concurrents) -> list[str | None]:
    """Le `secteur_code` de chaque concurrent, **`None` compris.**

    ⚠️ *Garder les `None` est ce qui rend le compte honnête* : un départage
    demande le fait chez TOUS les concurrents — inconnu n'est pas non.
    """
    return [m.entry.secteur_code for m in concurrents]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--comparer", type=int, default=0, metavar="N",
                        help="montrer N dossiers de l'intersection")
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
    from falkye.models.signal import Signal
    from falkye.resolution import (
        SEUIL_AMBIGUITE_ECART_MIN,
        SEUIL_RESOLUTION_CONFIANTE,
        famille_de,
    )
    from outils.departageur_adresse import champs_des_dossiers, concurrents_de
    # ⚠️ **La résolution est REJOUÉE par le chemin de la passe**, jamais par un
    # équivalent écrit ici.
    from outils.reresolution_neq import _resoudre_une

    print("=" * 78)
    print("LE PLAFOND DE LA PISTE DE L'ACTIVITÉ ÉCONOMIQUE")
    print("=" * 78)
    print(f"""
⚠️ CE QUE CETTE MESURE NE DIRA PAS — avant tout chiffre

   QU'UN DÉPARTAGE PAR L'ACTIVITÉ SERAIT JUSTE. Elle dit où le fait existe
   des deux côtés, jamais s'il tranche bien.

   NI COMBIEN SERAIENT EFFECTIVEMENT DÉPARTAGÉS. Il faudrait relier
   l'UNSPSC du contrat public au CAE du registre, et CETTE TABLE N'EXISTE
   PAS. Elle appartient au chantier 22, qui n'est pas ouvert. Cet outil ne
   la construit pas, ne l'esquisse pas, et ne nomme aucune famille.

⚠️ ET LA POPULATION N'EST PAS CELLE DU 17 SEPTEMBRE

   outils/mesure_des_departageurs.py a rendu 166 départagés, 97 en propre —
   SUR 5 002 AMBIGUS, avant les deux écritures du 19. Le compte d'ambigus
   d'aujourd'hui est imprimé plus bas. Les deux chiffres ne se comparent
   pas, et les soustraire donnerait un gain ou une perte qui n'existe pas.

   AUCUNE ÉCRITURE. Les échelles ne bougent pas : seuil {SEUIL_RESOLUTION_CONFIANTE:.0f}, écart {SEUIL_AMBIGUITE_ECART_MIN:.0f}.
""")

    # ---- 1. CE QUE CHAQUE CONNECTEUR PORTE, LU DANS LE CODE -----------------
    print("-" * 78)
    print("1. CE QUE CHAQUE CONNECTEUR PORTE — lu dans le code, pas supposé")
    print("-" * 78)
    print(f"""
   ⚠️ « L'EIMT n'a aucune classification » EST À MOITIÉ FAUX, et la moitié
      qui reste change le compte. Elle ne promeut aucune activité
      d'entreprise — aucun `{CHAMP_PROMU}=` sur son RawSignal, et sur ce
      point l'affirmation tenait. MAIS elle porte `champs["profession"]`,
      la colonne Occupation. C'est la profession d'un POSTE, pas l'activité
      d'une ENTREPRISE, et la traduire demanderait une AUTRE table encore.
      Elle est comptée à part, et jamais versée au plafond.
""")
    # *L'apostrophe vit dans une variable* : une f-string à guillemets simples
    # la coupe, et un libellé mutilé pour une raison de syntaxe se relit mal.
    entete_cles = "clés d'activité, lues ou déposées"
    print(f"   {'connecteur':<28} {'promeut ' + CHAMP_PROMU:<22} {entete_cles}")
    connecteurs = sorted(p for p in DOSSIER_CONNECTEURS.glob("*.py")
                         if p.name not in ("__init__.py", "base.py"))
    promoteurs: set[str] = set()
    cles_vues: dict[str, set[str]] = {}
    for chemin in connecteurs:
        promus = champs_promus_par_le_module(chemin, champs=(CHAMP_PROMU,))
        # ⚠️ **Les deux lecteurs, réunis** : une activité peut être LUE du
        # fichier source ou DÉPOSÉE dans le sac, et les deux comptent ici.
        du_sac = cles_du_sac_par_le_module(chemin)
        cles = {c for c in cles_lues_par_le_module(chemin) | du_sac
                if INDICE_DACTIVITE.search(c)}
        cles_vues[chemin.stem] = du_sac
        if promus:
            promoteurs.add(chemin.stem)
        if promus or cles:
            marque = "OUI" if promus else "—"
            print(f"   {chemin.stem:<28} {marque:<22} "
                  # ⚠️ **Pas de troncature** : une clé coupée ne se reconnaît
                  # plus, et c'est elle qu'on vient vérifier.
                  f"{', '.join(sorted(cles)) if cles else '—'}")
    print(f"""
   ⚠️ LA COLONNE DE DROITE EST LARGE À DESSEIN — elle réunit ce que le
      connecteur LIT de son fichier et ce qu'il DÉPOSE dans le sac, et retient
      toute clé dont le NOM évoque une activité. Mieux vaut en lister une qui
      n'en est pas que taire celle qui l'est. Les lignes « déclarée » en
      dessous disent lesquelles la mesure COMPTE.
""")
    # ⚠️ **Le recoupement qui rend la table fiable** : une clé déclarée dans
    # `CLES_DACTIVITE` doit être lue par le connecteur qu'on lui attribue.
    for source, (cle, _nature, _note) in sorted(CLES_DACTIVITE.items()):
        vues = cles_vues.get(source, set())
        etat = "✅ déposée" if cle in vues else "⚠️ NON DÉPOSÉE par ce connecteur"
        print(f"   déclarée · {source:<20} champs[{cle!r}]   {etat}")

    session = get_session()
    try:
        requete = select(Company).where(Company.neq.is_(None)).order_by(Company.id)
        if args.limite:
            requete = requete.limit(args.limite)
        restants = list(session.execute(requete).scalars().all())
        n = len(restants)
        print(f"\n   RESTANTS (sans NEQ) : {milliers(n)}")
        if not restants:
            print("   Aucun restant à mesurer.")
            return 0

        sources: dict[int, set[str]] = defaultdict(set)
        for company_id, source_id in session.execute(
            select(Signal.company_id, Signal.source_id).execution_options(yield_per=2000)
        ):
            sources[company_id].add(source_id)
        champs = champs_des_dossiers(session, {c.id for c in restants})

        # ---- 2. CÔTÉ DÉTECTÉ ------------------------------------------------
        print("\n" + "-" * 78)
        print("2. CÔTÉ DÉTECTÉ — combien des restants portent une activité")
        print("-" * 78)
        activites: dict[int, dict[str, list[str]]] = {}
        par_provenance: Counter = Counter()
        avec_code_par_source: dict[str, Counter] = defaultdict(Counter)
        for c in restants:
            trouve = activites_du_dossier(c, champs.get(c.id))
            activites[c.id] = trouve
            for nature in trouve:
                par_provenance[nature] += 1
            for s in sources.get(c.id, {"(aucun signal)"}):
                avec_code_par_source[s]["dossiers"] += 1
                for nature in trouve:
                    avec_code_par_source[s][nature] += 1

        print(f"\n   {'provenance':<34} {'dossiers':>9} {'part':>8}")
        for etiquette, nature in PROVENANCES:
            k = par_provenance.get(nature, 0)
            print(f"   {etiquette:<34} {milliers(k):>9} {_part(k, n):>8}")
        # ⚠️ Vérifié plutôt que déduit : le code dit que c'est impossible.
        avec_code_dossier = sum(1 for c in restants if c.secteur_activite_code)
        print(f"\n   Company.secteur_activite_code rempli : {milliers(avec_code_dossier)}")
        if avec_code_dossier == 0:
            print("   ✅ Conforme au code : son seul écrivain est `_enrich_from_req`,")
            print("      qui exige un NEQ résolu. Vérifié, pas déduit.")
        else:
            print("   ⚠️ INATTENDU — le code dit que c'est impossible sur un restant.")
            print("      Lire `falkye/resolution.py` avant d'employer ce chiffre.")

        print(f"\n   PAR SOURCE — avec le champ exact qui porte le fait\n")
        print(f"   {'source':<26} {'dossiers':>9} {'code':>8} {'libellé':>9} "
              f"{'profess.':>9}   champ")
        for source, compteur in sorted(avec_code_par_source.items(),
                                       key=lambda kv: -kv[1]["dossiers"]):
            total = compteur["dossiers"]
            declare = CLES_DACTIVITE.get(source)
            champ = f"champs[{declare[0]!r}]" if declare else (
                f"{CHAMP_PROMU} → Company" if source in promoteurs else "—")
            print(f"   {source:<26} {milliers(total):>9} "
                  f"{_part(compteur[CODE], total):>8} "
                  f"{_part(compteur[LIBELLE], total):>9} "
                  f"{_part(compteur[PROFESSION], total):>9}   {champ}")
        print("\n   ⚠️ Un dossier CUMULE ses signaux : il compte dans CHAQUE source qui")
        print("      l'a vu. Les lignes ne s'additionnent pas au total.")
        print("   ⚠️ Et la PROFESSION est une colonne à part, jamais additionnée aux")
        print("      deux autres : elle décrit un poste, pas une entreprise.")

        # ---- LE REJEU, pour atteindre les candidats -------------------------
        print(f"\n… rejeu de la résolution sur {milliers(n)} restants, "
              f"par le chemin de production", flush=True)
        concurrents_du_dossier: dict[int, list] = {}
        par_famille: Counter = Counter()
        for i, company in enumerate(restants, 1):
            if args.pas and i % args.pas == 0:
                print(f"   … {milliers(i)} / {milliers(n)}", flush=True)
            _neq, matches = _resoudre_une(session, company)
            famille = famille_de(matches)
            par_famille[famille] += 1
            if famille == "ambigu":
                concurrents_du_dossier[company.id] = concurrents_de(matches)

        ambigus = [c for c in restants if c.id in concurrents_du_dossier]
        n_amb = len(ambigus)
        return _cotes_registre(ambigus, n, n_amb, concurrents_du_dossier, activites,
                               par_famille, args.comparer)
    finally:
        session.close()


#: Les chiffres du 17 septembre, **cités pour ne pas être soustraits.**
DEPARTAGES_DU_17 = 166
EN_PROPRE_DU_17 = 97
AMBIGUS_DU_17 = 5002


def _cotes_registre(ambigus, n_restants: int, n_amb: int, concurrents_du_dossier,
                    activites, par_famille: Counter, comparer: int) -> int:
    """Les comptes 2, 3 et 4 — **le côté registre, l'intersection, et la borne.**"""
    print("\n" + "-" * 78)
    print("3. CÔTÉ REGISTRE — combien de LEURS candidats portent une activité")
    print("-" * 78)
    print(f"""
   familles du rejeu : """ + "  ·  ".join(
        f"{f} {milliers(k)}" for f, k in par_famille.most_common()) + f"""

   AMBIGUS AUJOURD'HUI : {milliers(n_amb)}
   ⚠️ Le 17 septembre, la mesure par LIBELLÉ portait sur {milliers(AMBIGUS_DU_17)} ambigus et
      rendait {DEPARTAGES_DU_17} départagés, {EN_PROPRE_DU_17} en propre — AVANT les deux écritures du
      19. LES DEUX POPULATIONS NE SONT PAS LES MÊMES. Soustraire ces chiffres
      donnerait un gain ou une perte qui n'existe pas.

   ⚠️ ET CE QUI COMPTE EST LE REMPLISSAGE CHEZ CES CANDIDATS-LÀ. Le 99,6 % de
      `COD_ACT_ECON_CAE` est un fait de l'ARCHIVE, et il ne s'y transporte pas :
      `REQEntry.secteur_code` vient d'`Etablissements.csv::COD_ACT_ECON` dès
      qu'un établissement principal existe, auquel cas `COD_ACT_ECON_CAE` n'est
      JAMAIS lu (`falkye/sources/req.py::_resoudre_entreprise`).
""")
    reg_tous: list = []
    reg_partiel = 0
    reg_aucun = 0
    codes_differents: set[int] = set()
    concurrents_comptes: Counter = Counter()
    for c in ambigus:
        concurrents = concurrents_du_dossier[c.id]
        codes = codes_des_candidats(concurrents)
        concurrents_comptes[min(len(codes), 5)] += 1
        portes = [x for x in codes if x]
        if codes and len(portes) == len(codes):
            reg_tous.append(c)
        elif portes:
            reg_partiel += 1
        else:
            reg_aucun += 1
        if len(set(portes)) >= 2:
            codes_differents.add(c.id)

    print(f"   {'':<44} {'dossiers':>9} {'part':>8}")
    print(f"   {'TOUS les candidats portent un code':<44} "
          f"{milliers(len(reg_tous)):>9} {_part(len(reg_tous), n_amb):>8}")
    print(f"   {'certains seulement':<44} "
          f"{milliers(reg_partiel):>9} {_part(reg_partiel, n_amb):>8}")
    print(f"   {'aucun':<44} "
          f"{milliers(reg_aucun):>9} {_part(reg_aucun, n_amb):>8}")
    print("""
   ⚠️ « CERTAINS SEULEMENT » N'EST PAS UNE DEMI-VICTOIRE. Un départage exige
      le fait chez TOUS les concurrents : inconnu n'est pas non. C'est la
      règle que `outils/departageurs.py::departager` applique déjà, et elle
      n'est pas assouplie ici.
""")

    # ---- 4. L'INTERSECTION ------------------------------------------------
    print("-" * 78)
    print("4. L'INTERSECTION — les deux côtés portent une activité. LE PLAFOND.")
    print("-" * 78)
    avec_code = [c for c in reg_tous if CODE in activites.get(c.id, {})]
    avec_libelle = [c for c in reg_tous
                    if activites.get(c.id, {}).keys() & {CODE, LIBELLE}]
    print(f"\n   {'':<52} {'dossiers':>9} {'part':>8}")
    print(f"   {'(a) détecté porte un CODE, registre complet':<52} "
          f"{milliers(len(avec_code)):>9} {_part(len(avec_code), n_amb):>8}")
    print(f"   {'(b) détecté porte un code OU un libellé, idem':<52} "
          f"{milliers(len(avec_libelle)):>9} {_part(len(avec_libelle), n_amb):>8}")
    print(f"""
   ⚠️ (a) EST LE SEUL PLAFOND DE LA ROUTE CODE À CODE — celle qui demanderait
      la table qui n'existe pas. (b) ajoute les dossiers où seul un LIBELLÉ
      existe : c'est la route que `fait_de_lactivite` emprunte déjà, mot à
      mot, et elle n'a pas besoin de table.
   ⚠️ LA PROFESSION N'EST DANS NI L'UN NI L'AUTRE. Elle décrit un poste.
   ⚠️ Les parts sont sur les {milliers(n_amb)} ambigus, jamais sur les {milliers(n_restants)} restants :
      un départageur ne s'applique qu'à un ambigu.
""")

    # ---- 5. LA BORNE — les codes diffèrent-ils entre eux? -----------------
    print("-" * 78)
    print("5. LA BORNE — au moins deux candidats dont les CODES DIFFÈRENT")
    print("-" * 78)
    borne_a = [c for c in avec_code if c.id in codes_differents]
    borne_b = [c for c in avec_libelle if c.id in codes_differents]
    tous_differents = [c for c in reg_tous if c.id in codes_differents]
    print(f"\n   {'':<52} {'dossiers':>9} {'part':>8}")
    print(f"   {'registre complet ET codes différents entre eux':<52} "
          f"{milliers(len(tous_differents)):>9} "
          f"{_part(len(tous_differents), len(reg_tous)):>8}")
    print(f"   {'(a) + codes différents  ← LA BORNE, route code':<52} "
          f"{milliers(len(borne_a)):>9} {_part(len(borne_a), n_amb):>8}")
    print(f"   {'(b) + codes différents  ← LA BORNE, route libellé':<52} "
          f"{milliers(len(borne_b)):>9} {_part(len(borne_b), n_amb):>8}")
    print("""
   ⚠️ AUCUNE CORRESPONDANCE ENTRE NOMENCLATURES N'EST EMPLOYÉE ICI. C'est une
      comparaison des codes du registre ENTRE EUX — pas une traduction.
   ⚠️ ET LE CODE STOCKÉ A DEUX PROVENANCES, dont l'origine n'est pas
      conservée : `Etablissements.csv::COD_ACT_ECON` quand un établissement
      principal existe, `COD_ACT_ECON_CAE` sinon. Deux codes qui diffèrent
      POURRAIENT différer parce qu'ils ne viennent pas de la même colonne.
      L'information n'est plus dans le miroir : la réserve se nomme et ne se
      mesure pas.
""")
    print(f"   nombre de concurrents par ambigu — "
          + "  ".join(f"{k if k < 5 else '5+'} : {milliers(v)}"
                      for k, v in sorted(concurrents_comptes.items())))

    if comparer and borne_b:
        montres = borne_b[:comparer]
        print(f"\n   {len(montres)} dossier(s) de la borne (b), sur "
              f"{milliers(len(borne_b))} :\n")
        for c in montres:
            print(f"      #{c.id:<7} {(c.nom_detecte or '')[:52]}")
            for nature, valeurs in sorted(activites.get(c.id, {}).items()):
                print(f"         détecté · {nature:<22} {valeurs[0][:44]}")
            codes = [x for x in codes_des_candidats(concurrents_du_dossier[c.id]) if x]
            print(f"         registre · codes des candidats  {sorted(set(codes))}")

    print("=" * 78)
    print("   RIEN N'A ÉTÉ ÉCRIT. Les échelles n'ont pas bougé.")
    print("   ⚠️ CE PLAFOND NE DIT PAS QU'UN DÉPARTAGE PAR L'ACTIVITÉ SERAIT JUSTE,")
    print("   ni combien seraient départagés. La table UNSPSC → CAE n'existe pas,")
    print("   elle appartient au chantier 22, et cet outil ne l'a pas esquissée.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
