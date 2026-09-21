#!/usr/bin/env python3
"""CE QUE VALENT LES CONTRADICTIONS DE L'ADRESSE — **une mesure, elle n'écrit rien.**

## La question d'Alexandre, du 21 septembre

Sur les **494** dossiers que la règle du statut poserait, l'adresse **peut
juger 125 fois** : elle **confirme 44 fois** et **contredit 81 fois** *(8 «
désigne un AUTRE candidat », 73 « les exclut tous »)*. **Que valent ces 81?**

⚠️ *« Une adresse différente n'est pas forcément un mauvais candidat : le
registre porte souvent le siège social, et le dossier peut porter l'adresse d'un
établissement. »*

## ⚠️ LES 81 NE SONT PAS UNE POPULATION, MAIS DEUX

| verdict | ce qu'il dit du RETENU | combien |
|---|---|---|
| « désigne un AUTRE candidat » | ⚠️ **il est contredit, nommément** | 8 |
| « les exclut TOUS » | *rien de lui en particulier* — **le lot entier est démenti** | 73 |

**Le second ne juge pas le retenu : il juge le LOT.** *C'est la trace la plus
directe de la réserve n° 3* — le bon candidat peut être absent.

## ⚠️ CORRECTION DU 21 SEPTEMBRE — « LES EXCLUT TOUS » N'EST PAS TOUJOURS LE CODE POSTAL

**La première version de cet outil affirmait que seuls les codes postaux avaient
parlé. C'est FAUX**, et Alexandre l'a mis au jour en relevant sept paires où le
retenu et son « suspect » portaient **le même code postal**.

*Trouvé en énumérant les configurations :* quand le code postal **ne tranche
pas** — plusieurs candidats compatibles, ou un candidat qui ne porte pas le
fait — **le repli descend jusqu'à la VILLE**, et c'est elle qui peut exclure tout
le monde. ⚠️ **Or `fait_de_la_ville` compare des GRAPHIES** : `Saint-Zéphirin` et
`St-Zéphirin` ne sont pas la même forme *(vérifié)*. **Une graphie de
municipalité renverse alors un code postal qui était d'accord.**

⚠️ **Et plus profond : le départageur est bâti pour REFUSER sûrement, pas pour
ACCUSER.** *En production, `AUCUN_COMPATIBLE` n'écrit rien — un refus ne coûte
qu'un dossier non posé.* **Lire ses refus comme une charge contre le retenu lui
fait dire ce pour quoi il n'a jamais été calibré.**

**La sortie rend donc le NIVEAU qui a prononcé l'exclusion, et le détail de
chaque niveau**, pour que la paire se vérifie au lieu de se croire.

## Les causes, dans l'ordre où elles se cherchent

**1. L'ÉTABLISSEMENT.** *Le registre porte le domicile; le dossier peut porter
un établissement.* **Les adresses d'établissement existent** — pas dans
`req_etablissements`, **gelée depuis le 2026-09-04**, mais dans l'état du moteur
de diff *(`etat_ligne_source`, partition `req_etablissements`,
`donnees_normalisees` = adresse, ville, code postal)*. ⚠️ **La sortie dit
LAQUELLE des deux a répondu** — deux millésimes ne se mélangent pas en silence.

**2. UN AUTRE CANDIDAT DU LOT.** *C'est exactement le verdict « désigne un
AUTRE ».* La sortie le nomme, avec son score et son statut.

**3. UN CANDIDAT ÉCARTÉ PAR L'ÉCART.** *Dans les cinq, mais à plus de 8 du
sommet : le nom l'a mis hors concours, l'adresse le désigne.*

**4. UN CANDIDAT SOUS LA COUPE À CINQ.** ⚠️ *La réserve n° 3, établie ou
réfutée.* `resolve_neq_by_name` plafonne le lot à cinq; l'outil rejoue le même
appel avec un plafond plus haut et **ne change rien d'autre**.

**5. AUCUNE.** *Ni établissement, ni candidat compatible nulle part.* **Le
produit ne peut pas décider — la paire se lit.**

## ⚠️ CE QUE CETTE MESURE NE PEUT PAS DIRE

**« Le candidat retenu est vraiment le mauvais » n'est pas une case que le
produit sait remplir.** *Un code postal partagé n'est pas une identité* — deux
entreprises distinctes habitent la même région de tri. **Les causes 2 à 4
désignent un SUSPECT, jamais une vérité**, et la paire est rendue entière pour
qu'elle se lise.

⚠️ **Le plafond relevé n'est pas la production.** *Le bonus de ville s'applique
aux candidats retenus APRÈS la coupe* (`falkye/sources/req.py::_scorer`) : en
relevant le plafond, un candidat profond reçoit un bonus qu'il n'aurait pas eu.
**Le score affiché d'un candidat profond n'est donc pas son score de
production** — sa COMPATIBILITÉ d'adresse, elle, ne dépend pas du plafond.

⚠️ **RIEN N'EST ÉCRIT. Les échelles ne bougent pas : seuil 92, écart 8.**

Usage, SUR L'HÔTE :
    python3 -m outils.valeur_des_contradictions
    python3 -m outils.valeur_des_contradictions --paires 20
    python3 -m outils.valeur_des_contradictions --profondeur 50
"""
from __future__ import annotations

import argparse
from collections import Counter

from outils.departageurs import DEPARTAGE
from outils.ecriture_du_statut import (
    ADRESSE_CONTRE,
    ADRESSE_EXCLUT_TOUS,
    parcourir,
)
from outils.nombres import milliers

#: La partition du moteur de diff qui porte les établissements.
#: *`falkye/sources/req.py:1224` la nomme; elle n'est pas dans le registre.*
PARTITION_DES_ETABLISSEMENTS = "req_etablissements"

#: ⚠️ **Les deux millésimes possibles, et la sortie dit lequel a répondu.**
#: *`req_etablissements` est GELÉE depuis le 2026-09-04* — « plus aucune ligne
#: n'est ajoutée ni mise à jour » (`falkye/models/req_etablissement_entry.py`).
#: **Un fait daté qu'on présente sans sa date est un fait faux à retardement.**
ETAT_DU_MOTEUR = "l'état du moteur de diff (courant)"
MIROIR_GELE = "⚠️ le miroir req_etablissements (GELÉ depuis le 2026-09-04)"
AUCUNE_SOURCE = "⚠️ AUCUNE — les deux sont vides"

#: Les causes, **dans l'ordre où elles se cherchent**. *L'ordre est la décision :
#: l'établissement DISSOUT la contradiction, les trois suivantes la déplacent sur
#: un autre candidat, la dernière ne l'explique pas.*
ETABLISSEMENT_DU_RETENU = "① l'adresse du dossier est celle d'un ÉTABLISSEMENT du retenu"
COMPATIBLE_DANS_LE_LOT = "② un AUTRE concurrent du lot porte l'adresse du dossier"
COMPATIBLE_SOUS_LE_LOT = "③ un candidat écarté par l'ÉCART porte l'adresse du dossier"
COMPATIBLE_SOUS_LA_COUPE = "④ un candidat SOUS la coupe à cinq porte l'adresse"
SANS_EXPLICATION = "⑤ aucune — ni établissement, ni candidat compatible nulle part"
CAUSES = (ETABLISSEMENT_DU_RETENU, COMPATIBLE_DANS_LE_LOT, COMPATIBLE_SOUS_LE_LOT,
          COMPATIBLE_SOUS_LA_COUPE, SANS_EXPLICATION)

#: Les étiquettes qui partagent la colonne des causes. *La largeur se calcule sur
#: leur union — cinquième et sixième occurrences du défaut déjà payées.*
ETIQUETTES = (
    "dossiers où l'adresse CONTREDIT",
    "   dont « désigne un AUTRE candidat »",
    "   dont « les exclut TOUS » (le lot, pas le retenu)",
    "dossiers où l'adresse CONFIRME",
    "dossiers où l'adresse est MUETTE",
    "NEQ retenus portant au moins un établissement connu",
    "le dossier ne porte pas le fait",
    "un concurrent ne porte pas le fait — inconnu ≠ non",
    "plusieurs concurrents compatibles",
)
LARGEUR = max(len(t) for t in CAUSES + ETIQUETTES) + 1


#: ⚠️ **D'où vient le fait d'adresse que le VERDICT a utilisé.** *La première
#: version affichait `Company.adresse · Company.ville · Company.code_postal`,
#: alors que `faits_du_dossier` lit AUSSI `Signal.champs` et la ville vue dans un
#: signal* — **presque toutes les paires montraient donc `— · — · —` sous un
#: verdict qui, lui, avait lu quelque chose.** *Cas 33, relevé par Alexandre le
#: 2026-09-21 : troisième fois en trois jours, dans la même famille d'outils.*
PROV_ADRESSE = "Company.adresse"
PROV_CODE_POSTAL = "Company.code_postal"
PROV_SIGNAL = "Signal.champs"
PROV_VILLE = "Company.ville"
PROV_VILLE_VUE = "ville vue dans un signal"
PROV_AUCUNE = "—"


def provenance_du_fait(company, champs, ville_vue) -> tuple[str, str]:
    """`(provenance du code postal, provenance de la ville)`.

    ⚠️ **Reconstruite en appelant les MÊMES lecteurs, source par source** — et
    non en devinant laquelle a parlé. *`faits_du_dossier` concatène trois textes
    pour le code postal et prend `company.ville or ville_vue` pour la ville.*
    """
    from outils.departageur_adresse import CLES_ADRESSE, texte_des_champs
    from outils.departageurs import codes_postaux

    sources = ((PROV_ADRESSE, company.adresse),
               (PROV_CODE_POSTAL, company.code_postal),
               (PROV_SIGNAL, texte_des_champs(champs, CLES_ADRESSE)))
    portantes = [nom for nom, texte in sources if codes_postaux(texte) is not None]
    ville = (PROV_VILLE if company.ville
             else PROV_VILLE_VUE if ville_vue else PROV_AUCUNE)
    return (" + ".join(portantes) if portantes else PROV_AUCUNE), ville


def coupe_de_production() -> int:
    """Le plafond du lot, **LU dans la signature du produit, jamais recopié.**

    *Un outil qui écrirait `5` en dur continuerait à annoncer « sous la coupe »
    sur une coupe qui aurait changé.*
    """
    import inspect

    from falkye.sources.req import resolve_neq_by_name

    return inspect.signature(resolve_neq_by_name).parameters["limit"].default


def faits_des_etablissements(session, neqs) -> tuple[dict, str, int]:
    """`(neq -> [FaitsDAdresse], provenance, NEQ pourvus)`.

    ⚠️ **L'état du moteur d'abord, le miroir gelé seulement s'il est vide** — et
    la provenance est RENDUE, pour qu'aucun lecteur n'ait à deviner de quel
    millésime vient le fait qui l'a convaincu.
    """
    from falkye.models.etat_diff_source import EtatLigneSource
    from falkye.models.req_etablissement_entry import REQEtablissementEntry
    from outils.departageur_adresse import FaitsDAdresse
    from outils.departageurs import codes_postaux, fait_de_la_ville

    def _fait(adresse, ville, code_postal) -> FaitsDAdresse:
        return FaitsDAdresse(
            codes_postaux(" ".join(filter(None, [adresse, code_postal]))),
            fait_de_la_ville(ville),
        )

    from sqlalchemy import select

    par_neq: dict[str, list] = {}
    for neq in neqs:
        # ⚠️ **GLOB, pas LIKE** — un `LIKE` paramétré force un SCAN complet;
        # c'est la leçon du 2026-08-31, déjà payée dans `candidats_par_nom`.
        # Un NEQ ne contient que des chiffres : aucun métacaractère à échapper.
        lignes = session.execute(
            select(EtatLigneSource.donnees_normalisees).where(
                EtatLigneSource.source_id == PARTITION_DES_ETABLISSEMENTS,
                EtatLigneSource.cle_naturelle.op("GLOB")(f"{neq}|*"),
            )
        ).scalars().all()
        faits = [_fait(d.get("adresse"), d.get("ville"), d.get("code_postal"))
                 for d in lignes if d]
        if faits:
            par_neq[neq] = faits
    if par_neq:
        return par_neq, ETAT_DU_MOTEUR, len(par_neq)

    for neq in neqs:
        lignes = session.execute(
            select(REQEtablissementEntry).where(REQEtablissementEntry.neq == neq)
        ).scalars().all()
        faits = [_fait(e.adresse, e.ville, e.code_postal) for e in lignes]
        if faits:
            par_neq[neq] = faits
    if par_neq:
        return par_neq, MIROIR_GELE, len(par_neq)
    return {}, AUCUNE_SOURCE, 0


def porte_ladresse(du_dossier, fait) -> str | None:
    """**Le NIVEAU auquel** le fait du dossier désigne ce candidat, ou `None`.

    *Un `DÉPARTAGÉ` sur un lot d'un candidat veut dire « le fait du dossier est
    compatible avec lui ».* ⚠️ **Un code postal partagé n'est pas une identité.**

    ⚠️ **Le niveau est rendu, et pas seulement un oui/non** : un suspect qui
    porte le CODE POSTAL n'a pas le même poids qu'un suspect qui porte la seule
    VILLE — laquelle est une comparaison de graphies. *C'est exactement la
    confusion qui a rendu sept paires illisibles le 21 septembre.*

    ⚠️ **Et cette question n'est PAS celle du lot.** *Le départage du lot entier
    peut s'arrêter à un niveau que celui-ci franchit* — un lot est démenti par la
    ville pendant qu'un de ses membres, seul, concorde au code postal.
    """
    from outils.departageur_adresse import departager_ladresse

    departage = departager_ladresse(du_dossier, [fait])
    return departage.niveau if departage.issue == DEPARTAGE else None


def cause_de_la_contradiction(paire, etablissements, profonds, coupe):
    """`(cause, pièce à conviction)` — **les cinq, dans l'ordre.**

    `pièce` est le `REQMatch` qui porte l'adresse, ou `None`.
    """
    from outils.departageur_adresse import faits_du_candidat

    du_dossier = paire["_faits_du_dossier"]
    for fait in etablissements.get(paire["neq"], []):
        niveau = porte_ladresse(du_dossier, fait)
        if niveau:
            paire["niveau_de_la_piece"] = niveau
            return ETABLISSEMENT_DU_RETENU, None

    dans_le_lot = {m.entry.neq for m in paire["_concurrents"]}
    for m in paire["_concurrents"]:
        niveau = (porte_ladresse(du_dossier, faits_du_candidat(m.entry))
                  if m.entry.neq != paire["neq"] else None)
        if niveau:
            paire["niveau_de_la_piece"] = niveau
            return COMPATIBLE_DANS_LE_LOT, m

    for rang, m in enumerate(profonds):
        if m.entry.neq in dans_le_lot:
            continue
        niveau = porte_ladresse(du_dossier, faits_du_candidat(m.entry))
        if not niveau:
            continue
        paire["niveau_de_la_piece"] = niveau
        return (COMPATIBLE_SOUS_LE_LOT if rang < coupe
                else COMPATIBLE_SOUS_LA_COUPE), m
    return SANS_EXPLICATION, None


#: *Une forme que ni `req_entries` ni `req_noms` ne portent* — n'arrive que sur
#: le chemin de simulation, mais se nomme plutôt que de compter pour « inconnu ».
FORME_INTROUVABLE = "(forme introuvable)"

#: ⚠️ **29,7 % de `req_noms` a été chargée avant que la colonne `gisement`
#: existe** *(pont du 15 septembre)*. `formes_retenues` rend alors une étiquette;
#: cette constante ne sert qu'au cas où la colonne est vide sans même ça.
GISEMENT_SANS_COLONNE = "(gisement non renseigné)"


def _montrer_les_paires(session, passe, lot, depuis, combien, titre,
                        champs, villes) -> None:
    """Des paires ENTIÈRES — ⚠️ **avec le FAIT qui a décidé et sa provenance.**

    *La première version affichait `Company.adresse · ville · code_postal`, donc
    `— · — · —` sous un verdict qui avait lu `Signal.champs`.* **Un verdict dont
    on ne voit pas l'entrée ne se vérifie pas.**
    """
    from falkye.sources.req import formes_retenues

    tranche = lot[depuis: depuis + combien]
    print("\n" + "=" * 78)
    print(f"{titre} — {len(tranche)} sur {milliers(len(lot))}")
    print("=" * 78)
    if not tranche:
        print("\n   (aucun dossier)")
        return
    formes = formes_retenues(
        session, [m for x in tranche for m in x["_concurrents"]])
    for paire in tranche:
        company = passe.retenus[paire["company_id"]]
        ville_vue = villes.get(paire["company_id"])
        prov_cp, prov_ville = provenance_du_fait(
            company, champs.get(paire["company_id"]),
            ville_vue.ville if ville_vue is not None else None)
        faits = paire["_faits_du_dossier"]
        cp = faits.code_complet or faits.region_de_tri
        print(f"\n   #{paire['company_id']}   {(paire['nom_detecte'] or '')[:54]}")
        print(f"      fait du dossier : code postal « {cp.brut if cp else '—'} »"
              f" ({prov_cp})   ·   ville « {faits.ville.brut if faits.ville else '—'} »"
              f" ({prov_ville})")
        niveau = paire.get("niveau_qui_exclut")
        print(f"      ✳️ {paire['adresse']}"
              + (f"   →  PRONONCÉ PAR : {niveau}" if niveau else ""))
        for nom, issue in paire["_departage"].par_niveau:
            print(f"           {nom:<22} : {issue}")
        if paire.get("gisement"):
            print(f"      ⌂ le retenu est entré par « {paire['gisement']} »")
        for m in paire["_concurrents"]:
            marque = "→" if m.entry.neq == paire["neq"] else "×"
            print(f"      {marque} {m.entry.neq}  {m.score:>6.1f}  "
                  f"{(m.entry.nom or '—')[:30]:<32} "
                  f"[{m.entry.statut}]  {(m.entry.ville or '—')[:14]} "
                  f"{m.entry.code_postal or '—'}")
            forme = formes.get((m.entry.neq, m.forme_normalisee))
            if forme is not None and not forme.est_la_denomination_elue:
                print("         ↳ a scoré sur "
                      f"« {(forme.nom_publie or forme.nom_normalise)[:40] } »"
                      f"   ({forme.gisement})")
        piece = paire.get("_piece")
        if piece is not None:
            print(f"      ⚠️ porte l'adresse AU NIVEAU "
                  f"« {paire.get('niveau_de_la_piece') or '—'} » : "
                  f"{piece.entry.neq}  {piece.score:>6.1f}  "
                  f"{(piece.entry.nom or '—')[:30]} [{piece.entry.statut}]  "
                  f"{piece.entry.code_postal or '—'}")


def _part(k: int, n: int) -> str:
    return f"{100 * k / n:.1f} %" if n else "—"


def _ligne(etiquette: str, k: int, n: int = 0) -> str:
    part = f" {_part(k, n):>8}" if n else ""
    return f"   {etiquette:<{LARGEUR}} {milliers(k):>9}{part}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--paires", type=int, default=0, metavar="N",
                        help="montrer N dossiers PAR CAUSE, en entier")
    parser.add_argument("--par-gisement", type=int, default=0, metavar="N",
                        help="montrer N dossiers PAR FORME D'ENTRÉE du retenu")
    parser.add_argument("--depuis", type=int, default=0, metavar="K")
    parser.add_argument("--profondeur", type=int, default=25, metavar="N",
                        help="plafond du lot rejoué (production : lu dans le code)")
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
    from falkye.sources import req as req_source
    from outils.departageurs import (
        PLUSIEURS_COMPATIBLES,
        SANS_FAIT_AU_DOSSIER,
        SANS_FAIT_CHEZ_UN_CONCURRENT,
    )
    from falkye.sources.req import formes_retenues
    from outils.departageur_adresse import champs_des_dossiers
    from outils.ecriture_du_statut import ADRESSE_ACCORD, ADRESSE_MUETTE
    from outils.villes_des_signaux import villes_des_signaux

    coupe = coupe_de_production()
    session = get_session()
    try:
        print("=" * 78)
        print("CE QUE VALENT LES CONTRADICTIONS DE L'ADRESSE — une MESURE")
        print("=" * 78)
        print(f"""
⚠️ LES CONTRADICTIONS NE SONT PAS UNE POPULATION, MAIS DEUX

   « désigne un AUTRE candidat » contredit le RETENU, nommément.
   « les exclut TOUS » ne dit rien du retenu : il dément le LOT ENTIER.
   C'est la trace la plus directe de la réserve n° 3 — le bon candidat
   peut être absent du lot.

   ⚠️ ET « LES EXCLUT TOUS » N'EST PAS TOUJOURS UN VERDICT DU CODE POSTAL.
      Quand le code postal ne tranche pas, le repli descend jusqu'à la
      VILLE, qui compare des GRAPHIES : « Saint-Zéphirin » et
      « St-Zéphirin » ne sont pas la même forme. Une graphie peut donc
      renverser un code postal qui était d'accord. Le niveau qui a
      prononcé l'exclusion est rendu dans chaque paire.

   ⚠️ Le départageur est bâti pour REFUSER sûrement, pas pour ACCUSER. En
      production, « aucun compatible » n'écrit rien. Lire ses refus comme
      une charge contre le retenu lui fait dire ce pour quoi il n'a jamais
      été calibré.

⚠️ CE QUE CETTE MESURE NE PEUT PAS DIRE

   « Le candidat retenu est vraiment le mauvais » n'est pas une case que le
   produit sait remplir. Un code postal partagé n'est pas une identité. Les
   causes ② ③ ④ désignent un SUSPECT, jamais une vérité, et la paire est
   rendue entière pour qu'elle se lise.

   Le plafond relevé ({args.profondeur}) n'est pas la production ({coupe}) : le bonus de
   ville s'applique APRÈS la coupe, donc le score d'un candidat profond
   n'est pas son score de production. Sa compatibilité d'adresse, elle, ne
   dépend pas du plafond.

⚠️ RIEN N'EST ÉCRIT.
""")

        requete = select(Company).where(Company.neq.is_(None)).order_by(Company.id)
        if args.limite:
            requete = requete.limit(args.limite)
        restants = list(session.execute(requete).scalars().all())
        if not restants:
            print("   Aucun restant.")
            return 0

        # ⚠️ **La MÊME passe que l'écriture**, empruntée et non refaite.
        passe = parcourir(session, restants, pas=args.pas)
        a_poser = passe.a_poser
        contredits = [x for x in a_poser
                      if x["adresse"] in (ADRESSE_CONTRE, ADRESSE_EXCLUT_TOUS)]

        print("\n" + "-" * 78)
        print("1. LA POPULATION, ET CE QUE L'ADRESSE EN FAIT")
        print("-" * 78 + "\n")
        n = len(a_poser)
        print(_ligne("dossiers que la règle poserait", n))
        print(_ligne(ETIQUETTES[3], passe.par_adresse.get(ADRESSE_ACCORD, 0), n))
        print(_ligne(ETIQUETTES[0], len(contredits), n))
        print(_ligne(ETIQUETTES[1], passe.par_adresse.get(ADRESSE_CONTRE, 0), n))
        print(_ligne(ETIQUETTES[2], passe.par_adresse.get(ADRESSE_EXCLUT_TOUS, 0), n))
        print(_ligne(ETIQUETTES[4], passe.par_adresse.get(ADRESSE_MUETTE, 0), n))

        # ⚠️ **Pourquoi elle est muette** — trois causes, trois suites. *« Elle ne
        # dit rien » se lit comme une absence de fait; c'est presque toujours un
        # fait manquant CHEZ UN CONCURRENT, et ce n'est pas la même chose.*
        muettes: Counter = Counter()
        for paire in a_poser:
            if paire["adresse"] == ADRESSE_MUETTE:
                muettes[paire["_departage"].issue] += 1
        print()
        for issue, etiquette in ((SANS_FAIT_AU_DOSSIER, ETIQUETTES[6]),
                                 (SANS_FAIT_CHEZ_UN_CONCURRENT, ETIQUETTES[7]),
                                 (PLUSIEURS_COMPATIBLES, ETIQUETTES[8])):
            print(_ligne("   " + etiquette, muettes.get(issue, 0), n))
        print(f"""
   ⚠️ CE QUE COÛTERAIT UN GARDE-FOU PERMANENT

      L'adresse ne juge que {milliers(len(contredits) + passe.par_adresse.get(ADRESSE_ACCORD, 0))} des {milliers(n)} dossiers. En faire une
      CONDITION bloquerait {milliers(len(contredits))} écritures et en laisserait passer
      {milliers(passe.par_adresse.get(ADRESSE_MUETTE, 0))} sans rien en dire. Un garde-fou muet trois fois sur
      quatre n'est pas un garde-fou : c'est un filtre partiel qu'on lira
      comme une garantie.
""")
        # ---- PAR QUELLE FORME LE RETENU EST ENTRÉ -------------------------
        # ⚠️ **La piste ouverte par Alexandre le 21 septembre.** *Sur 34 paires
        # lues, les trois faux probables étaient entrés par une forme SECONDAIRE
        # — `NOM_ETRNG « CROSSROADS »`, `NOM_ETAB « BOUCHARD, MARTIN »` — ou par
        # un candidat sous la coupe.* **Contrairement à l'adresse, ce signal
        # existe pour CHAQUE dossier : aucune forme gagnante n'est absente.**
        formes = formes_retenues(session, [x["_retenu"] for x in a_poser])
        par_gisement: dict[str, list] = {}
        for paire in a_poser:
            forme = formes.get((paire["neq"], paire["_retenu"].forme_normalisee))
            etiquette = FORME_INTROUVABLE if forme is None else (
                forme.gisement or GISEMENT_SANS_COLONNE)
            paire["gisement"] = etiquette
            par_gisement.setdefault(etiquette, []).append(paire)

        print("\n" + "-" * 78)
        print("2. PAR QUELLE FORME LE RETENU EST ENTRÉ")
        print("-" * 78)
        print("""
   ⚠️ CE SIGNAL EXISTE POUR CHAQUE DOSSIER. L'adresse se tait trois fois
      sur quatre; une forme gagnante, jamais — tout candidat scoré a
      scoré sur quelque chose. C'est ce qui en fait un garde-fou
      candidat, là où l'adresse n'en est pas un.

   ⚠️ CE N'EST PAS ENCORE UNE RÈGLE. Le tableau dit d'où les dossiers
      entrent; il ne dit pas lesquels sont justes. Les paires se lisent.
""")
        print(f"   {'':<{LARGEUR}} {'total':>9} {'score 100':>10} "
              f"{'adr. ✅':>8} {'adr. ⚠️':>8}")
        for etiquette, lot in sorted(par_gisement.items(),
                                     key=lambda kv: -len(kv[1])):
            cent = sum(1 for x in lot if x["score_du_sommet"] >= 100.0)
            oui = sum(1 for x in lot if x["adresse"] == ADRESSE_ACCORD)
            non = sum(1 for x in lot if x["adresse"] in
                      (ADRESSE_CONTRE, ADRESSE_EXCLUT_TOUS))
            print(f"   {etiquette:<{LARGEUR}} {milliers(len(lot)):>9} "
                  f"{milliers(cent):>10} {milliers(oui):>8} {milliers(non):>8}")

        if args.par_gisement:
            champs_tous = champs_des_dossiers(
                session, {x["company_id"] for x in a_poser})
            villes_tous = villes_des_signaux(
                session, {x["company_id"] for x in a_poser})
            for etiquette, lot in sorted(par_gisement.items(),
                                         key=lambda kv: -len(kv[1])):
                _montrer_les_paires(
                    session, passe, lot, args.depuis, args.par_gisement,
                    f"ENTRÉS PAR « {etiquette} »", champs_tous, villes_tous)

        if not contredits:
            print("   Aucune contradiction à expliquer.")
            return 0

        # ---- LES CAUSES ---------------------------------------------------
        neqs = {x["neq"] for x in contredits}
        print(f"… lecture des établissements de {milliers(len(neqs))} NEQ", flush=True)
        etablissements, provenance, pourvus = faits_des_etablissements(session, neqs)
        print(f"… rejeu du lot à {args.profondeur} sur {milliers(len(contredits))} dossiers",
              flush=True)

        par_cause: Counter = Counter()
        for i, paire in enumerate(contredits, 1):
            if args.pas and i % args.pas == 0:
                print(f"   … {milliers(i)} / {milliers(len(contredits))}", flush=True)
            company = passe.retenus[paire["company_id"]]
            profonds = req_source.resolve_neq_by_name(
                session, company.nom_detecte, ville=company.ville,
                limit=args.profondeur)
            cause, piece = cause_de_la_contradiction(
                paire, etablissements, profonds, coupe)
            paire["cause"] = cause
            paire["_piece"] = piece
            par_cause[cause] += 1

        print("\n" + "-" * 78)
        print("3. CE QUI EXPLIQUE LA CONTRADICTION")
        print("-" * 78 + "\n")
        print(f"   provenance des établissements : {provenance}")
        print(_ligne(ETIQUETTES[5], pourvus, len(neqs)))
        print()
        for cause in CAUSES:
            print(_ligne(cause, par_cause.get(cause, 0), len(contredits)))
        print(f"""
   ⚠️ ① DISSOUT la contradiction — le registre portait le domicile, le
      dossier portait un établissement. Rien ne s'oppose plus à l'écriture.

   ⚠️ ② ③ ④ DÉPLACENT le soupçon sur un autre candidat. Elles ne prouvent
      pas que le retenu est faux : elles nomment qui lui dispute l'adresse.
      ④ est la réserve n° 3 — la coupe à cinq — établie ou réfutée.

   ⚠️ ⑤ N'EXPLIQUE RIEN. Ni établissement, ni candidat compatible nulle
      part : soit l'adresse du dossier n'est pas celle de l'entreprise,
      soit l'entreprise n'est pas récupérée du tout (la récupération est
      ancrée sur la TÊTE du nom). Le produit ne peut pas trancher.
""")

        if args.paires:
            champs = champs_des_dossiers(session, {x["company_id"] for x in contredits})
            villes = villes_des_signaux(session, {x["company_id"] for x in contredits})
            for cause in CAUSES:
                _montrer_les_paires(
                    session, passe,
                    [x for x in contredits if x.get("cause") == cause],
                    args.depuis, args.paires, cause, champs, villes)

        print("\n" + "=" * 78)
        print("   RIEN N'A ÉTÉ ÉCRIT. Les échelles n'ont pas bougé.")
        print("   ⚠️ Les causes ② ③ ④ nomment un SUSPECT, jamais une vérité.")
        print("=" * 78)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
