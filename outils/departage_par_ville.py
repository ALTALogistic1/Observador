#!/usr/bin/env python3
"""L'adresse ne peut pas APPARIER. Peut-elle DÉPARTAGER? Et combien de fois?

**Ce qui a rendu cette question possible** *(2026-09-17)*. Le préalable a établi
que **zéro des 8 931 dossiers à apparier ne porte d'adresse** — la mesure
d'appariement qu'on s'apprêtait à demander aurait rendu zéro, et *ce zéro se
serait lu comme « l'adresse ne sert à rien »*.

Et la FORME est un second mur, distinct du premier :

    produit  : 'St-Isidore, QC J0L  2A'
    registre : '200 rue des Commandeurs'   ville='Lévis'

**L'EIMT donne une municipalité, une province, un code postal. Le REQ donne un
numéro civique et une rue.** *Ce ne sont pas deux écritures de la même chose —
ce sont deux niveaux de précision différents, et aucune normalisation ne les fera
se rejoindre.* **Ce qui se recouvre, c'est la VILLE.**

## Pourquoi départager, et pas apparier

Le chiffrage de l'écart a établi que **le gain et la colonne « 2e NEQ à moins
de » sont le même chiffre à chaque ligne** — 138 et 138, 2 097 et 2 097. *Tout ce
qu'un abaissement de l'écart récupère, il le récupère en tranchant entre deux
entités.*

> **Les ambigus ne manquent pas de TOLÉRANCE. Il leur manque un signal qui ne
> dépend pas du nom.**

**Apparier depuis rien avec une ville est impossible** — « Lévis » ne désigne pas
une entreprise. **Départager deux candidats DÉJÀ TROUVÉS avec une ville est autre
chose** : si l'un est à St-Isidore et l'autre à Laval, la question est réglée
*sans toucher à aucune échelle*.

⚠️ **AUCUNE ÉCRITURE, AUCUNE PROMOTION DE CHAMP, AUCUNE RÈGLE MODIFIÉE.** *La
promotion de l'adresse EIMT vers `RawSignal.adresse` est un correctif connu de
l'audit — il attend ce chiffre, il ne le précède pas.* **Et les deux échelles ne
bougent pas : seuil 92, écart 8.**

Usage, SUR L'HÔTE :
    sudo -u falkye bash -c 'set -a; . /etc/falkye/falkye.env; set +a; \
        cd /opt/falkye/code && \
        /opt/falkye/venv/bin/python -m outils.departage_par_ville'
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict

from outils.nombres import milliers
from outils.villes_des_signaux import (
    CLE_ADRESSE,  # noqa: F401 -- gardé pour les tests qui vérifient la convention
    CLES_VILLE,  # noqa: F401
    ville_depuis_adresse as _ville_depuis_adresse,
    villes_des_signaux,
)


def _part(k: int, n: int) -> str:
    return f"{100 * k / n:.1f} %" if n else "—"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--limite", type=int, default=None, help="borner (mise au point)")
    parser.add_argument("--exemples", type=int, default=6)
    args = parser.parse_args(argv)

    from sqlalchemy import select

    from falkye.db import refuser_si_cible_non_choisie

    code = refuser_si_cible_non_choisie()
    if code:
        return code

    from falkye.db import get_session
    from falkye.models.company import Company
    from falkye.models.signal import Signal
    from falkye.resolution import SEUIL_AMBIGUITE_ECART_MIN, famille_de
    from falkye.sources import req as req_source
    from falkye.sources.column_mapping import normaliser

    print("=" * 78)
    print("L'ADRESSE NE PEUT PAS APPARIER — PEUT-ELLE DÉPARTAGER?")
    print("=" * 78)

    # ---- CE QUE LA MESURE NE DIRA PAS, AVANT LES CHIFFRES --------------------
    print(f"""
⚠️ CE QUE CETTE MESURE NE DIRA PAS — à lire avant tout chiffre

   ELLE COMPTE CE QUI SERAIT DÉPARTAGEABLE EN PRINCIPE. Elle ne valide AUCUN
   départage, et n'en applique aucun.

   La ville du registre est SALE : `ville='LOCAL RC27'`, `ville='BEAUCEVILLE,
   BEAUCE'`. Un départage par ville hérite de cette saleté, et le compte
   ci-dessous la porte sans la corriger.

   UNE VILLE QUI CONCORDE NE PROUVE PAS L'IDENTITÉ. Deux entreprises distinctes
   peuvent être dans la même ville — c'est même le cas courant à Montréal.
   *Un départage écarte un candidat; il n'en confirme aucun.*

   ⚠️ ET LE MOTEUR UTILISE DÉJÀ `Company.ville` : +5 quand elle concorde
   (`falkye/sources/req.py::resolve_neq_by_name`). Là où la ville est DÉJÀ
   promue, le signal est en partie consommé et l'ambiguïté a survécu au bonus.
   *Le gisement est là où la ville N'EST PAS promue* — et le tableau 1 sépare
   les deux pour cette raison.

   AUCUNE ÉCRITURE, AUCUNE PROMOTION, AUCUNE RÈGLE MODIFIÉE.
   Les deux échelles ne bougent pas : seuil 92, écart minimal
   {SEUIL_AMBIGUITE_ECART_MIN:.0f}.
""")

    session = get_session()
    try:
        requete = select(Company).where(Company.neq.is_(None)).order_by(Company.id)
        if args.limite:
            requete = requete.limit(args.limite)
        orphelins = list(session.execute(requete).scalars().all())

        # --- Les villes disponibles par dossier, et d'où elles viennent ------
        # ⚠️ **Empruntée, pas recopiée.** *La mesure et le correctif de promotion
        # doivent lire la MÊME ville — sinon la mesure compte une chose pendant
        # que l'écriture en pose une autre.*
        trouvees = villes_des_signaux(session, {c.id for c in orphelins})
        villes_signal: dict[int, tuple[str, str, str]] = {
            cid: (v.ville, v.provenance, v.source_id) for cid, v in trouvees.items()
        }
        contradictoires = sum(1 for v in trouvees.values() if v.contradictoire)

        # --- La population : les AMBIGUS ------------------------------------
        print("-" * 78)
        print("0. LA POPULATION — les ambigus, recomptés par la règle du moteur")
        print("-" * 78)
        ambigus: list[tuple[Company, list]] = []
        for i, company in enumerate(orphelins):
            if i and i % 1000 == 0:
                print(f"   … {milliers(i)} examinés", flush=True)
            matches = req_source.resolve_neq_by_name(
                session, company.nom_detecte, ville=company.ville
            )
            if famille_de(matches) == "ambigu":
                ambigus.append((company, matches))
        print(f"\n   dossiers sans NEQ : {milliers(len(orphelins))}")
        print(f"   dont AMBIGUS      : {milliers(len(ambigus))}   ← la population de cette mesure")

        # --- 1. LE PLAFOND ---------------------------------------------------
        print("\n" + "-" * 78)
        print("1. LE PLAFOND — combien d'ambigus ont une ville DISPONIBLE")
        print("-" * 78)
        print("\n   ⚠️ « Disponible » veut dire : présente quelque part dans le produit.")
        print("      Deux provenances, et elles ne valent pas la même chose.\n")
        deja_promue = [c for c, _ in ambigus if c.ville]
        seulement_signal = [
            c for c, _ in ambigus if not c.ville and c.id in villes_signal
        ]
        aucune = [
            c for c, _ in ambigus if not c.ville and c.id not in villes_signal
        ]
        n = len(ambigus)
        print(f"   {'provenance de la ville':<46} {'dossiers':>9} {'part':>8}")
        print(f"   {'`Company.ville` — DÉJÀ connue du moteur (+5 déjà appliqué)':<46}"
              f" {milliers(len(deja_promue)):>9} {_part(len(deja_promue), n):>8}")
        print(f"   {'`Signal.champs` SEULEMENT — jamais promue':<46}"
              f" {milliers(len(seulement_signal)):>9} {_part(len(seulement_signal), n):>8}")
        print(f"   {'aucune ville nulle part':<46}"
              f" {milliers(len(aucune)):>9} {_part(len(aucune), n):>8}")
        print(f"\n   PLAFOND de tout ce qui suit : "
              f"{milliers(len(deja_promue) + len(seulement_signal))} dossier(s)")
        if contradictoires:
            print(f"\n   ⚠️ {milliers(contradictoires)} dossier(s) portent DES VILLES QUI SE")
            print("      CONTREDISENT d'un signal à l'autre. *Un dossier cumule les")
            print("      signaux; rien ne garantit qu'ils parlent du même établissement.*")
            print("      Ils sont comptés ici avec leur ville EXPLICITE quand il y en a")
            print("      une — mais un départage sur eux serait à décider, pas à déduire.")
        print("\n   ⚠️ La seconde ligne est le GISEMENT : là, la ville existe dans la")
        print("      base et le moteur ne l'a jamais vue. La première ligne a déjà")
        print("      reçu le bonus, et est restée ambiguë quand même.")

        par_source: Counter = Counter(
            villes_signal[c.id][2] for c in seulement_signal
        )
        if par_source:
            print("\n   le gisement, par source :\n")
            for sid, k in par_source.most_common(10):
                print(f"      {sid:<30} {milliers(k):>9}")

        # --- 2. DÉPARTAGEABLES OU NON ---------------------------------------
        print("\n" + "-" * 78)
        print("2. DÉPARTAGEABLES — les concurrents ont-ils des villes DIFFÉRENTES?")
        print("-" * 78)
        print(f"""
   Les « concurrents » sont les candidats que la règle ne sait pas séparer :
   ceux à moins de {SEUIL_AMBIGUITE_ECART_MIN:.0f} points du meilleur. *C'est exactement
   l'ensemble sur lequel un abaissement de l'écart trancherait à l'aveugle.*
""")
        issues: Counter = Counter()
        departages: list[tuple[Company, list, int]] = []  # (company, concurrents, rang_gagnant)
        exemples: dict[str, list[str]] = defaultdict(list)
        for company, matches in ambigus:
            ville = company.ville or (villes_signal.get(company.id) or (None,))[0]
            if not ville:
                issues["aucune ville au dossier"] += 1
                continue
            haut = matches[0].score
            concurrents = [m for m in matches if haut - m.score < SEUIL_AMBIGUITE_ECART_MIN]
            villes_reg = [
                normaliser(m.entry.ville) if m.entry.ville else "" for m in concurrents
            ]
            if not any(villes_reg):
                issues["aucun concurrent n'a de ville au registre"] += 1
                continue
            if len(set(villes_reg)) == 1:
                issues["concurrents de MÊME ville — la ville ne départage pas"] += 1
                if len(exemples["meme"]) < args.exemples:
                    exemples["meme"].append(
                        f"{company.nom_detecte[:40]:<40} tous à {concurrents[0].entry.ville!r}"
                    )
                continue
            cible = normaliser(ville)
            gagnants = [i for i, v in enumerate(villes_reg) if v and v == cible]
            if len(gagnants) == 1:
                issues["DÉPARTAGÉ — un seul concurrent dans la ville du dossier"] += 1
                departages.append((company, concurrents, gagnants[0]))
            elif not gagnants:
                issues["villes différentes, mais AUCUNE ne concorde"] += 1
                if len(exemples["aucune"]) < args.exemples:
                    exemples["aucune"].append(
                        f"{company.nom_detecte[:34]:<34} dossier={ville!r} "
                        f"registre={[m.entry.ville for m in concurrents][:3]}"
                    )
            else:
                issues["villes différentes, PLUSIEURS concordent"] += 1
        print(f"   {'issue':<56} {'dossiers':>9}")
        for cle, k in issues.most_common():
            print(f"   {cle:<56} {milliers(k):>9}")
        print(f"\n   DÉPARTAGEABLES : {milliers(len(departages))} sur {milliers(n)} ambigus "
              f"({_part(len(departages), n)})")

        for titre, cle in (("concurrents de même ville", "meme"),
                           ("aucune ville ne concorde", "aucune")):
            if exemples[cle]:
                print(f"\n   quelques cas — {titre} :")
                for ligne in exemples[cle]:
                    print(f"      {ligne}")

        # --- 3. CONFIRME OU CORRIGE? -----------------------------------------
        print("\n" + "-" * 78)
        print("3. LA VILLE CONFIRME-T-ELLE, OU CORRIGE-T-ELLE?")
        print("-" * 78)
        print("""
   ⚠️ C'est la question qui décide si le correctif vaut la peine.

      Si le candidat retenu par la ville est PRESQUE TOUJOURS celui qui avait
      déjà le meilleur score, la ville CONFIRME — elle débloque l'ambiguïté
      sans rien apprendre.

      Si c'est SOUVENT L'AUTRE, elle CORRIGE — et le score se trompait de
      gagnant, ce qui est un fait beaucoup plus lourd.
""")
        # ⚠️ TROIS issues, pas deux. *Quand plusieurs concurrents partagent le
        # MEILLEUR score, « était-ce déjà le mieux scoré » n'a pas de réponse —
        # et les compter comme « confirmé » ferait paraître la ville inutile
        # alors qu'elle tranche un cas que le score ne tranchait pas du tout.*
        confirme = corrige = ex_aequo = 0
        for _, concurrents, rang in departages:
            haut = concurrents[0].score
            partage = sum(1 for m in concurrents if m.score == haut) > 1
            if concurrents[rang].score < haut:
                corrige += 1
            elif partage:
                ex_aequo += 1
            else:
                confirme += 1
        d = len(departages)
        print(f"   {'le gagnant par la ville était DÉJÀ le seul mieux scoré':<52} "
              f"{milliers(confirme):>9} {_part(confirme, d):>8}")
        print(f"   {'le gagnant par la ville est UN AUTRE candidat':<52} "
              f"{milliers(corrige):>9} {_part(corrige, d):>8}")
        print(f"   {'EX ÆQUO au meilleur score — le score ne tranchait pas':<52} "
              f"{milliers(ex_aequo):>9} {_part(ex_aequo, d):>8}")
        print("\n   ⚠️ La troisième ligne n'est ni une confirmation ni une correction :")
        print("      le score ne désignait AUCUN gagnant. *Là, la ville n'ajoute pas")
        print("      une opinion à une autre — elle est la seule à en avoir une.*")
        montres = 0
        for company, concurrents, rang in departages:
            if rang == 0 or montres >= args.exemples:
                continue
            par_ville, par_score = concurrents[rang], concurrents[0]
            print(f"\n      {company.nom_detecte[:60]}")
            print(f"         ville au dossier : "
                  f"{(company.ville or villes_signal.get(company.id, ('?',))[0])!r}")
            print(f"         mieux scoré      : {par_score.entry.neq}  {par_score.score:>6.2f}  "
                  f"{par_score.entry.nom[:34]!r}  ville={par_score.entry.ville!r}")
            print(f"         choisi par ville : {par_ville.entry.neq}  {par_ville.score:>6.2f}  "
                  f"{par_ville.entry.nom[:34]!r}  ville={par_ville.entry.ville!r}")
            montres += 1

        print("\n" + "=" * 78)
        print("   CE QUE CE CHIFFRE NE DIT PAS : qu'un départage soit JUSTE.")
        print("   Il borne ce qui est départageable en principe. La promotion du")
        print("   champ, elle, se décide avec Alexandre — et sur ce chiffre.")
        print("=" * 78)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
