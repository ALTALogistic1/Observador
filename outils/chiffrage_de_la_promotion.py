#!/usr/bin/env python3
"""Ce que la promotion rendrait — **et la réponse n'est pas la même aux deux niveaux.**

⚠️ **LA QUESTION QUI DÉCIDE SE LIT DANS LE CODE, PAS DANS UNE MESURE.** *Le
départageur lit `Signal.champs` directement; la promotion sert `RawSignal`.* **Si
tout ce qui compte passe déjà par `faits_du_dossier`, la promotion est un travail
de propreté, pas un gain.**

## Deux lecteurs, et ils ne connaissent pas les mêmes clés

| niveau | qui lit | quelles clés |
|---|---|---|
| **code postal** | `faits_du_dossier` | `CLES_ADRESSE` — `adresse`, `code_postal`, **`adresse_entreprise_adjudicataire`** |
| **ville** | `villes_des_signaux` | `CLES_VILLE` — `ville`, `city`, `municipalite`, `locality` · repli sur **la seule clé `adresse`** |

> ⚠️ **C'est ce qui explique l'asymétrie du SEAO — 88,7 % de code postal contre
> 9,6 % de ville.** *Le champ agrégé `adresse_entreprise_adjudicataire` porte les
> deux; seul le lecteur de code postal le connaît.* **La ville du SEAO n'est pas
> absente : elle est invisible au lecteur qui la cherche.**

## Ce que ça change pour chaque source

- **`eimt`** — `champs['adresse']` est lu **par les DEUX** : le code postal par
  `CLES_ADRESSE`, la ville par le repli sur `'adresse'`. ⚠️ **Donc la promouvoir
  en `RawSignal.adresse` ne change RIEN au départage.** *Elle servirait le
  portrait, qui exige une adresse en sortie.*
- **`seao`** — le connecteur **lit `locality`** et ne le range pas. *`locality`
  est déjà dans `CLES_VILLE`* : **le ranger suffirait, sans rien changer
  d'autre.** ⚠️ *L'autre voie — apprendre la clé agrégée au repli d'adresse —
  risque de prendre une RUE pour une ville, et cette mesure le montre avant
  qu'on construise.*

## ⚠️ Ce que cette mesure ne dit pas

**Ce que les sources fermées publient.** *`contrats_federaux` et
`investissement_quebec` n'ont aucun champ d'adresse ici — 629 restants — et ça
veut dire que personne ici ne le sait.* **Fermer la piste demande d'ouvrir la
source.**

⚠️ **Et elle ne tranche pas `RawSignal`.** *Le code postal n'a aucun emplacement
à promouvoir : élargir `CLES_ADRESSE` ou donner un champ à `RawSignal` est une
décision de modèle.* **Rien ne se construit dessus avant Alexandre.**

⚠️ **AUCUNE ÉCRITURE. Les échelles ne bougent pas : seuil 92, écart 8.**

Usage, SUR L'HÔTE :
    python3 -m outils.chiffrage_de_la_promotion
    python3 -m outils.chiffrage_de_la_promotion --exemples 10
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict

from outils.nombres import milliers

#: Les clés agrégées qu'on SIMULE d'apprendre au repli d'adresse du lecteur de
#: ville. ⚠️ **Une simulation, pas un correctif** — et la mesure montre ce que la
#: tête de chaîne y trouve avant qu'on décide.
CLES_A_ESSAYER = ("adresse_entreprise_adjudicataire", "adresse_complete",
                  "lieu_affaires")

#: Les sources dont l'écart a été relevé, et le niveau où il se joue.
SOURCES_VISEES = ("seao", "eimt")


def _part(k: int, n: int) -> str:
    return f"{100 * k / n:.1f} %" if n else "—"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--source", action="append", default=None, metavar="ID")
    parser.add_argument("--exemples", type=int, default=6, metavar="N",
                        help="montrer N têtes de chaîne extraites (la QUALITÉ)")
    parser.add_argument("--limite", type=int, default=None)
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
    from falkye.sources import req as req_source
    from outils.departageur_adresse import (
        CLES_ADRESSE,
        NIVEAU_CODE_COMPLET,
        PasUnAmbigu,
        champs_des_dossiers,
        departager_le_dossier,
        faits_du_dossier,
        faits_du_candidat,
    )
    from outils.villes_des_signaux import (
        CLE_ADRESSE,
        CLES_VILLE,
        ville_depuis_adresse,
        villes_des_signaux,
    )

    sources_visees = tuple(args.source) if args.source else SOURCES_VISEES

    print("=" * 78)
    print("CE QUE LA PROMOTION RENDRAIT — AVANT DE LA FAIRE")
    print("=" * 78)
    print(f"""
⚠️ LA QUESTION QUI DÉCIDE SE LIT DANS LE CODE, PAS DANS UNE MESURE

   Le départageur lit `Signal.champs` DIRECTEMENT; la promotion sert
   `RawSignal`. Si tout ce qui compte passe déjà par `faits_du_dossier`, la
   promotion est un travail de PROPRETÉ, pas un gain.

   DEUX LECTEURS, ET ILS NE CONNAISSENT PAS LES MÊMES CLÉS :
      code postal  ·  faits_du_dossier   ·  {', '.join(CLES_ADRESSE)}
      ville        ·  villes_des_signaux ·  {', '.join(CLES_VILLE)}
                                          ·  repli sur la SEULE clé {CLE_ADRESSE!r}

   AUCUNE ÉCRITURE. Seuil {SEUIL_RESOLUTION_CONFIANTE:.0f}, écart
   {SEUIL_AMBIGUITE_ECART_MIN:.0f} — inchangés. Et rien ne se construit sur
   `RawSignal` avant qu'Alexandre tranche.
""")

    session = get_session()
    try:
        requete = select(Company).where(Company.neq.is_(None)).order_by(Company.id)
        if args.limite:
            requete = requete.limit(args.limite)
        restants = list(session.execute(requete).scalars().all())
        ids = {c.id for c in restants}
        par_id = {c.id: c for c in restants}

        # --- à quelle source appartient chaque restant ----------------------
        sources: dict[int, set[str]] = defaultdict(set)
        champs_bruts: dict[int, dict] = defaultdict(dict)
        for company_id, champs, source_id in session.execute(
            select(Signal.company_id, Signal.champs, Signal.source_id)
            .execution_options(yield_per=2000)
        ):
            if company_id in ids:
                sources[company_id].add(source_id)
                if champs:
                    champs_bruts[company_id].update(champs)

        champs = champs_des_dossiers(session, ids)
        # ⚠️ **Deux lectures de la ville par un APPEL de la même fonction** — la
        # production, puis la production PLUS les clés simulées. *Une copie de
        # `villes_des_signaux` mesurerait sa copie.*
        villes_aujourdhui = villes_des_signaux(session, ids)
        villes_elargies = villes_des_signaux(
            session, ids, cles_adresse=(CLE_ADRESSE, *CLES_A_ESSAYER))

        for source_id in sources_visees:
            lot = [c for c in restants if source_id in sources.get(c.id, ())]
            n = len(lot)
            print("-" * 78)
            print(f"{source_id}   ({milliers(n)} restants)")
            print("-" * 78)
            if not n:
                print("   aucun restant de cette source.\n")
                continue

            # ---- 1. CE QUI EST DÉJÀ LU ---------------------------------------
            avec_code = avec_ville = 0
            for c in lot:
                faits = faits_du_dossier(
                    c, champs.get(c.id),
                    villes_aujourdhui[c.id].ville if c.id in villes_aujourdhui else None)
                avec_code += 1 if faits.code_postal is not None else 0
                avec_ville += 1 if faits.ville is not None else 0
            print(f"\n   {'ce que `faits_du_dossier` lit DÉJÀ':<44} {'dossiers':>9} {'part':>8}")
            print(f"   {'un code postal':<44} {milliers(avec_code):>9} "
                  f"{_part(avec_code, n):>8}")
            print(f"   {'une ville':<44} {milliers(avec_ville):>9} "
                  f"{_part(avec_ville, n):>8}")

            # ---- 2. CE QU'UNE CLÉ DE PLUS AJOUTERAIT -------------------------
            gagnent = [
                c for c in lot
                if c.id not in villes_aujourdhui and c.id in villes_elargies
            ]
            print(f"\n   {'⇒ une VILLE de plus, si le repli apprenait la clé agrégée':<44} "
                  f"{milliers(len(gagnent)):>9} {_part(len(gagnent), n):>8}")
            if not gagnent:
                print("      ✔ AUCUN. *La clé agrégée est déjà lue, ou ne rend rien.*")
                print("      ⚠️ Donc la promouvoir ne changerait RIEN au départage —")
                print("         elle servirait le PORTRAIT, qui exige une adresse en")
                print("         sortie. C'est un travail de propreté, pas un gain.")

            # ---- 3. LA QUALITÉ DE CE QUE ÇA AJOUTERAIT -----------------------
            if gagnent:
                print("""
   ⚠️ ET CE N'EST PAS ENCORE UN GAIN : il faut voir CE QUE la tête de chaîne
      extrait. `ville_depuis_adresse` prend ce qui précède la première virgule.
      Sur « St-Isidore, QC J0L 2A » c'est une municipalité; sur
      « 123 rue Principale, Montréal, QC » c'est une RUE.
""")
                montres = 0
                suspectes = 0
                for c in gagnent:
                    brut = next(
                        (champs_bruts[c.id][k] for k in CLES_A_ESSAYER
                         if champs_bruts[c.id].get(k)), None)
                    tete = villes_elargies[c.id].ville
                    # ⚠️ Une tête qui commence par un NUMÉRO est une rue, pas une
                    # ville. *Un indice, pas une preuve* — d'où l'affichage.
                    est_suspecte = bool(tete) and tete.strip()[:1].isdigit()
                    suspectes += 1 if est_suspecte else 0
                    if montres < args.exemples:
                        marque = "⚠️ RUE?" if est_suspecte else "       "
                        print(f"      {marque} {str(brut)[:48]!r}")
                        print(f"              → tête : {tete!r}")
                        montres += 1
                print(f"\n      têtes qui COMMENCENT PAR UN NUMÉRO : "
                      f"{milliers(suspectes)} sur {milliers(len(gagnent))} "
                      f"({_part(suspectes, len(gagnent))})")
                print("      ⚠️ *Une rue prise pour une ville ne manque pas un")
                print("       départage : elle en PRONONCE un faux.* **C'est pire**,")
                print("       et c'est ce que ce tableau existe pour montrer.")

            # ---- 4. CE QUE ÇA CHANGE AU DÉPARTAGE ---------------------------
            print("\n   ce que ça change au DÉPARTAGE des ambigus de cette source :")
            # Deux étiquettes nommées une fois : *une apostrophe contournée dans
            # une f-string produit du code illisible, et c'est arrivé ici.*
            AVANT, APRES = "aujourd'hui", "avec la clé"
            gagnes = Counter()
            examines = 0
            for c in lot:
                matches = req_source.resolve_neq_by_name(
                    session, c.nom_detecte, ville=c.ville)
                if famille_de(matches) != "ambigu":
                    continue
                examines += 1
                for etiquette, vues in ((AVANT, villes_aujourdhui),
                                        (APRES, villes_elargies)):
                    faits = faits_du_dossier(
                        c, champs.get(c.id),
                        vues[c.id].ville if c.id in vues else None)
                    try:
                        departage, _ = departager_le_dossier(matches, faits)
                    except PasUnAmbigu:
                        continue
                    if departage.prononce:
                        gagnes[etiquette] += 1
            print(f"      ambigus de cette source          : {milliers(examines)}")
            print(f"      départagés AUJOURD'HUI           : {milliers(gagnes[AVANT])}")
            print(f"      départagés AVEC la clé de plus   : {milliers(gagnes[APRES])}")
            delta = gagnes[APRES] - gagnes[AVANT]
            print(f"      ⇒ écart                          : {delta:+d}")
            if delta == 0:
                print("      ✔ *La clé n'ajoute aucun départage.* La promotion est")
                print("        un travail de propreté pour le portrait.")
            print()

        print("=" * 78)
        print("   RIEN N'A ÉTÉ ÉCRIT. Et `RawSignal` n'a toujours pas d'emplacement")
        print("   pour un code postal — c'est une décision de modèle, pas une")
        print("   conséquence de ces chiffres.")
        print("=" * 78)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
