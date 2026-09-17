#!/usr/bin/env python3
"""La borne de récupération COUPE-T-ELLE le lot? Et combien de fois?

**L'hypothèse d'Alexandre, déclarée le 2026-09-17 et jamais mesurée.** *Nettoyer
le registre du bruit et rendre la liste des candidats ORDONNÉE — éventuellement à
l'import plutôt qu'à chaque comparaison.* **C'est une hypothèse, pas une demande
de construction**, et cet outil existe pour la départager.

## ⚠️ Une correction à l'énoncé, et elle ne l'affaiblit pas

*« `candidats_par_nom` fait `LIMIT 2000` sans `ORDER BY`. »* — **l'`ORDER BY` a
été posé le 2026-09-16**, après ton propre relevé. Mais **il ne règle pas ce que
tu vises** :

> ⚠️ **Trier par `nom_normalise` rend le tirage REPRODUCTIBLE, pas MEILLEUR.** Sur
> 50 000 « gestion… », les 2 000 retenus restent **une tranche alphabétique
> arbitraire**. *Le lot est stable d'une exécution à l'autre; rien ne dit qu'il
> contient la bonne ligne.*

**Donc l'inquiétude tient entièrement**, et elle porte sur tout ce qui a été
mesuré depuis deux jours : seuil, écart, parenthèses, ville — *tout opère sur un
lot dont personne n'a vérifié qu'il contient le bon candidat.*

## Ce que cet outil mesure, et le seul chiffre qui départage

**Combien de fois la borne COUPE.** Si elle sature souvent, l'ordonnancement
attaque le mur. **Si elle ne sature jamais, le lot est complet et l'hypothèse ne
récupère rien** — et le chantier se ferme sans avoir été construit.

Ventilé **par famille** et **par forme du préfixe** — *un préfixe numérique
(`11888935`) est quasi unique, un préfixe parlant (`gestion`, `construction`) ne
l'est pas du tout, et mélanger les deux ferait une moyenne qui ne décrit
personne.*

Et, sur les dossiers saturés seulement, **la taille du gisement** : combien de
lignes le préfixe rendrait SANS borne. *C'est la différence entre « on en regarde
2 000 sur 2 100 » et « on en regarde 2 000 sur 51 000 ».*

⚠️ **RIEN N'EST CONSTRUIT.** *Ni tri, ni filtrage, ni transformation à l'import.*
**Aucune écriture, aucune règle modifiée** — seuil 92, écart 8.

Usage, SUR L'HÔTE :
    sudo -u falkye bash -c 'set -a; . /etc/falkye/falkye.env; set +a; \
        cd /opt/falkye/code && \
        /opt/falkye/venv/bin/python -m outils.saturation_de_la_borne'
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict

from outils.nombres import milliers


def _forme_du_prefixe(prefixe: str) -> str:
    """Numérique, parlant, ou vide. *Trois populations, trois comportements de
    récupération — et une moyenne des trois ne décrirait aucune des trois.*"""
    if not prefixe:
        return "(vide)"
    if any(c.isdigit() for c in prefixe):
        return "numérique"
    return "parlant"


def _part(k: int, n: int) -> str:
    return f"{100 * k / n:.1f} %" if n else "—"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--limite", type=int, default=None, help="borner (mise au point)")
    parser.add_argument("--gisements", type=int, default=12,
                        help="combien de préfixes saturés détailler")
    args = parser.parse_args(argv)

    from sqlalchemy import func, select

    from falkye.db import refuser_si_cible_non_choisie

    code = refuser_si_cible_non_choisie()
    if code:
        return code

    from falkye.db import get_session
    from falkye.models.company import Company
    from falkye.models.req_entry import REQEntry
    from falkye.resolution import FAMILLES, famille_de
    from falkye.sources import req as req_source
    from falkye.sources.column_mapping import normaliser

    borne = req_source.LIMITE_CANDIDATS_PAR_NOM

    print("=" * 78)
    print("LA BORNE DE RÉCUPÉRATION COUPE-T-ELLE LE LOT?")
    print("=" * 78)
    print(f"""
⚠️ CE QUE CETTE MESURE NE DIRA PAS — à lire avant tout chiffre

   ELLE COMPTE DES COUPES, PAS DES PERTES. Une borne saturée dit que le lot a
   été tranché; elle ne dit PAS que le bon candidat est tombé du mauvais côté.
   *Un préfixe qui rend 51 000 lignes dont la bonne est la douzième
   alphabétique sature ET récupère.* Le compte BORNE le risque; il ne
   l'établit pas.

   Établir la perte demanderait de connaître le bon candidat — donc une vérité
   de terrain qui n'existe pas. C'est un autre chantier, et il se décide après
   celui-ci.

   L'ORDER BY posé le 2026-09-16 rend le tirage REPRODUCTIBLE, pas MEILLEUR :
   sur 50 000 « gestion… », les 2 000 retenus restent une tranche alphabétique.

   ⚠️ RIEN N'EST CONSTRUIT ICI. Ni tri, ni filtrage, ni transformation à
   l'import. Aucune écriture, aucune règle modifiée — seuil 92, écart 8.

   BORNE EN VIGUEUR : {borne} (lue dans le moteur, jamais recopiée).
""")

    session = get_session()
    try:
        requete = select(Company).where(Company.neq.is_(None)).order_by(Company.id)
        if args.limite:
            requete = requete.limit(args.limite)
        orphelins = list(session.execute(requete).scalars().all())
        total = len(orphelins)
        print(f"   dossiers sans NEQ : {milliers(total)}\n")

        satures_par_famille: Counter = Counter()
        par_famille: Counter = Counter()
        satures_par_forme: Counter = Counter()
        par_forme: Counter = Counter()
        replis_principal = replis_pont = rognages = 0
        prefixes_satures: Counter = Counter()
        exemples_non_satures: list[tuple[str, int]] = []

        for i, company in enumerate(orphelins):
            if i and i % 1000 == 0:
                print(f"   … {milliers(i)} examinés", flush=True)
            journal: dict = {}
            nom_norm = normaliser(company.nom_detecte or "")
            # ⚠️ La VRAIE récupération, instrumentée — pas une requête recopiée
            # à côté. *Une copie mesurerait sa propre borne.*
            req_source.candidats_par_nom(session, nom_norm, journal=journal)
            matches = req_source.resolve_neq_by_name(
                session, company.nom_detecte, ville=company.ville
            )
            famille = famille_de(matches)
            forme = _forme_du_prefixe(journal.get("prefixe", ""))
            par_famille[famille] += 1
            par_forme[forme] += 1
            if journal.get("sature"):
                satures_par_famille[famille] += 1
                satures_par_forme[forme] += 1
                prefixes_satures[journal.get("prefixe", "")] += 1
            elif len(exemples_non_satures) < 5:
                exemples_non_satures.append(
                    (journal.get("prefixe", ""), journal.get("total", 0))
                )
            replis_principal += 1 if journal.get("repli_principal") else 0
            replis_pont += 1 if journal.get("repli_pont") else 0
            rognages += 1 if journal.get("rognage") else 0

        satures = sum(satures_par_famille.values())

        # ---- LE CHIFFRE QUI DÉPARTAGE ---------------------------------------
        print("\n" + "=" * 78)
        print("LE CHIFFRE QUI DÉPARTAGE L'HYPOTHÈSE")
        print("=" * 78)
        print(f"\n   lots COUPÉS par la borne : {milliers(satures)} sur {milliers(total)}"
              f"  ({_part(satures, total)})\n")
        if not satures:
            print("   ⇒ LA BORNE NE COUPE JAMAIS. Le lot est complet à chaque fois,")
            print("      et l'ordonnancement ne récupérerait rien. *L'hypothèse se")
            print("      ferme ici, sans avoir été construite.*")
        elif satures == total:
            print("   ⇒ LA BORNE COUPE TOUJOURS. Aucun appariement mesuré depuis deux")
            print("      jours n'a vu la totalité de ses candidats.")
        else:
            print("   ⇒ La borne coupe une PART. Le tableau par famille dit si cette")
            print("      part se concentre là où les appariements échouent.")

        # ---- 1. PAR FAMILLE --------------------------------------------------
        print("\n" + "-" * 78)
        print("1. PAR FAMILLE — la coupe se concentre-t-elle là où ça échoue?")
        print("-" * 78)
        print(f"\n   {'famille':<18} {'dossiers':>9} {'coupés':>9} {'part':>8}")
        for f in FAMILLES:
            n, k = par_famille.get(f, 0), satures_par_famille.get(f, 0)
            print(f"   {f:<18} {milliers(n):>9} {milliers(k):>9} {_part(k, n):>8}")
        print("\n   ⚠️ Une part de coupe ÉGALE entre RETENU et les autres dirait que la")
        print("      borne n'explique rien : elle couperait autant là où ça marche.")

        # ---- 2. PAR FORME DU PRÉFIXE ----------------------------------------
        print("\n" + "-" * 78)
        print("2. PAR FORME DU PRÉFIXE — numérique contre parlant")
        print("-" * 78)
        print(f"\n   {'forme':<18} {'dossiers':>9} {'coupés':>9} {'part':>8}")
        for forme in ("numérique", "parlant", "(vide)"):
            n, k = par_forme.get(forme, 0), satures_par_forme.get(forme, 0)
            print(f"   {forme:<18} {milliers(n):>9} {milliers(k):>9} {_part(k, n):>8}")
        print("\n   ⚠️ Un préfixe numérique est quasi unique; un préfixe parlant ne")
        print("      l'est pas. *C'est la réserve d'Alexandre sur le cas du 2026-09-17,")
        print("      et elle se mesure ici sur la population entière.*")

        # ---- 3. LES AUTRES CHEMINS DE LA RÉCUPÉRATION -----------------------
        print("\n" + "-" * 78)
        print("3. LES AUTRES CHEMINS — repli par sous-chaîne, et rognage du pont")
        print("-" * 78)
        print(f"\n   repli par SOUS-CHAÎNE (préfixe sans réponse) : {milliers(replis_principal)}"
              f"  ({_part(replis_principal, total)})")
        print(f"   repli par SOUS-CHAÎNE côté pont               : {milliers(replis_pont)}"
              f"  ({_part(replis_pont, total)})")
        print(f"   liste principale ROGNÉE pour le pont          : {milliers(rognages)}"
              f"  ({_part(rognages, total)})")
        print("\n   ⚠️ Le rognage n'est PAS une perte : la place rendue va à des")
        print("      candidats ciblés par leur préfixe, là où les derniers de la liste")
        print("      principale sont une tranche alphabétique. *Il est compté parce")
        print("      qu'il change le lot, pas parce qu'il le dégrade.*")

        # ---- 4. LA TAILLE DU GISEMENT ---------------------------------------
        if satures:
            print("\n" + "-" * 78)
            print("4. LA TAILLE DU GISEMENT — 2 000 sur combien?")
            print("-" * 78)
            print("\n   Sur les préfixes qui SATURENT, ce que le registre rendrait sans")
            print("   borne. *« 2 000 sur 2 100 » et « 2 000 sur 51 000 » sont deux")
            print("   situations, et une seule est un mur.*\n")
            print(f"   {'préfixe':<22} {'dossiers':>9} {'lignes au registre':>20} "
                  f"{'vu':>8}")
            for prefixe, k in prefixes_satures.most_common(args.gisements):
                gisement = session.execute(
                    select(func.count()).select_from(REQEntry)
                    .where(REQEntry.nom_normalise.op("GLOB")(f"{prefixe}*"))
                ).scalar() or 0
                print(f"   {prefixe[:20]:<22} {milliers(k):>9} {milliers(gisement):>20} "
                      f"{_part(borne, gisement):>8}")
            print("\n   « vu » est la part du gisement que le score a pu regarder.")
        if exemples_non_satures:
            print("\n   quelques lots NON coupés, pour l'échelle :")
            for prefixe, n in exemples_non_satures:
                print(f"      {prefixe[:24]:<26} {milliers(n):>6} candidat(s)")

        print("\n" + "=" * 78)
        print("   RIEN N'EST CONSTRUIT. Le tri, le nettoyage et la transformation à")
        print("   l'import se décident avec Alexandre, et sur ce chiffre.")
        print("=" * 78)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
