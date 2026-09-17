#!/usr/bin/env python3
"""Le pic 85-88 est-il un PLANCHER TECHNIQUE, et la tranche est-elle occupée par
des entrées que personne ne cherche? — trois recomptages, aucune construction.

**Ce que les dix paires ont montré** *(2026-09-17)*. Aucune des dix n'était
l'entreprise cherchée :

    'Les Habitations KTP'                  →  'LES " 100 " AILE'
    'Ferme Léger Parent inc.'              →  'FERME 100 MILES CENTRE ÉDUCATIONNEL'
    'La Perade Ford inc.'                  →  'La 115e'

*Ce ne sont pas des appariements qui manquent de peu — ce sont des noms qui
partagent le PREMIER MOT et rien d'autre.* **Et sept des dix sont en tête
alphabétique de leur préfixe** : chiffres et ponctuation trient avant les
lettres.

> ⚠️ **L'`ORDER BY` du 16 septembre rend le tirage reproductible et
> systématiquement mauvais.** *Le lot de 2 000 est rempli par le début de
> l'ordre alphabétique, et on regarde toujours ce même début.*

**Dix cas ne sont pas une proportion.** Cet outil est le recomptage.

## Les trois mesures

**A — le motif des dix, recompté.** Sur les lots COUPÉS : dans la tranche
alphabétique rendue, que trouve-t-on après le préfixe? *Et surtout : jusqu'où la
tranche va-t-elle avant d'être coupée?*

**B — le score plancher.** Sur le pic : la distribution des valeurs EXACTES de
score, et le partage de mots avec le candidat. *Si une seule valeur domine, le
pic n'est pas une population d'appariements proches — c'est le plancher de
`WRatio` sur un mot partagé, et aucun réglage d'échelle ne le franchira.*

**C — ce qu'un lot différent changerait.** Sur un ÉCHANTILLON des coupés,
récupération rejouée **sans borne**, et combien franchissent alors le seuil
actuel. ⚠️ **C'est la mesure qui décide, et elle coûte** — son budget est annoncé
avant d'être dépensé.

⚠️ **RIEN N'EST CONSTRUIT.** Ni tri par pertinence, ni nettoyage du registre, ni
transformation à l'import — **et surtout pas de borne relevée en production, qui
coûterait sur CHAQUE résolution ce que la mesure C coûte une fois.** Les échelles
ne bougent pas : seuil 92, écart 8.

Usage, SUR L'HÔTE :
    sudo -u falkye bash -c 'set -a; . /etc/falkye/falkye.env; set +a; \
        cd /opt/falkye/code && \
        /opt/falkye/venv/bin/python -m outils.recomptage_du_plancher'
    …  --mesures ABC --echantillon 200      (C incluse)
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from outils.formes_registre import formes_publiees
from outils.nombres import milliers

#: La fenêtre du pic, et la sous-fenêtre où le plancher se lit.
FENETRE_DU_PIC = (85.0, 88.0)
SOUS_FENETRE_PLANCHER = (85.0, 86.0)

#: ⚠️ **Le plafond de gisement au-delà duquel la mesure C REFUSE un dossier.**
#: Lever la borne charge tout le gisement en mémoire — `l` rend 309 788 lignes.
#: *Le plafond protège l'hôte, et il BIAISE l'échantillon en écartant exactement
#: les cas où la borne fait le plus mal.* **Donc il se déclare, et les refus se
#: comptent** — un garde silencieux transformerait le biais en résultat.
GISEMENT_MAX_PAR_DEFAUT = 120_000

#: Estimation du poids d'une ligne `REQEntry` chargée en objet. *Une ESTIMATION,
#: annoncée comme telle : elle sert à dire un ordre de grandeur avant de dépenser,
#: pas à promettre un chiffre.*
OCTETS_PAR_LIGNE_ESTIMES = 1_500


@dataclass
class Dossier:
    id: int
    nom: str
    nom_norm: str
    prefixe: str
    famille: str
    score: float
    neq: str | None
    ville: str | None
    sature: bool
    total: int
    pont_ajoutes: int
    mots: set = field(default_factory=set)


def apres_le_prefixe(nom_normalise: str, prefixe: str) -> str:
    """Ce qui suit le préfixe dans une forme normalisée, classé.

    ⚠️ **L'ordre qui remplit la tranche est celui de `nom_normalise`**, où la
    ponctuation est déjà devenue des espaces. *`LES " 100 " AILE` y est
    `les 100 aile`* — et l'espace trie avant les chiffres, qui trient avant les
    lettres. **C'est ce classement-là qui décide de ce qu'on voit.**
    """
    if not nom_normalise.startswith(prefixe):
        return "hors préfixe"
    reste = nom_normalise[len(prefixe):]
    if not reste:
        return "rien — le nom EST le préfixe"
    if reste[0] == " ":
        suite = reste.lstrip(" ")
        if not suite:
            return "rien — le nom EST le préfixe"
        return "espace puis CHIFFRE" if suite[0].isdigit() else "espace puis lettre"
    return "CHIFFRE collé" if reste[0].isdigit() else "lettre collée (mot plus long)"


#: Les classes rendues par `apres_le_prefixe`, dans l'ordre d'affichage, et
#: celles qui comptent comme « non alphabétique » — la question d'Alexandre.
CLASSES = (
    "rien — le nom EST le préfixe",
    "espace puis CHIFFRE",
    "CHIFFRE collé",
    "espace puis lettre",
    "lettre collée (mot plus long)",
    "hors préfixe",
)
NON_ALPHABETIQUES = (
    "rien — le nom EST le préfixe",
    "espace puis CHIFFRE",
    "CHIFFRE collé",
)
#: Les deux classes où une LETTRE suit le préfixe. *Énumérées plutôt que
#: déduites d'un `endswith` : un libellé retouché ferait basculer le compte sans
#: qu'aucun test ne tombe.*
ALPHABETIQUES = ("espace puis lettre", "lettre collée (mot plus long)")


def echantillon_reparti(dossiers: list, combien: int, cle) -> list:
    """Des rangs régulièrement espacés sur la liste triée par `cle`.

    **Même règle que `outils/paires_du_pic.py`, et pour la même raison** : *un
    échantillon pris par `id` croissant serait l'ordre des fichiers sources.*
    Ici le tri est le GISEMENT, pour que les gros préfixes — ceux où la borne
    fait mal — soient représentés au lieu d'être noyés.
    """
    if not dossiers or combien <= 0:
        return []
    ordonnes = sorted(dossiers, key=cle)
    if combien >= len(ordonnes):
        return ordonnes
    pas = len(ordonnes) / combien
    return [ordonnes[int(i * pas)] for i in range(combien)]


def _part(k: int, n: int) -> str:
    return f"{100 * k / n:.1f} %" if n else "—"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--mesures", default="AB",
                        help="quelles mesures lancer : A, B, C ou une combinaison (défaut AB)")
    parser.add_argument("--echantillon", type=int, default=200,
                        help="taille de l'échantillon de la mesure C")
    parser.add_argument("--gisement-max", type=int, default=GISEMENT_MAX_PAR_DEFAUT,
                        help="au-delà, la mesure C REFUSE le dossier et le compte")
    parser.add_argument("--limite", type=int, default=None, help="borner (mise au point)")
    args = parser.parse_args(argv)
    mesures = set(args.mesures.upper())

    from sqlalchemy import func, select

    from falkye.db import refuser_si_cible_non_choisie

    code = refuser_si_cible_non_choisie()
    if code:
        return code

    from falkye.db import get_session
    from falkye.models.company import Company
    from falkye.models.req_entry import REQEntry
    from falkye.resolution import FAMILLES, SEUIL_RESOLUTION_CONFIANTE, famille_de
    from falkye.sources import req as req_source
    from falkye.sources.column_mapping import normaliser

    borne = req_source.LIMITE_CANDIDATS_PAR_NOM
    bas_pic, haut_pic = FENETRE_DU_PIC
    bas_pl, haut_pl = SOUS_FENETRE_PLANCHER

    print("=" * 78)
    print("LE PLANCHER, RECOMPTÉ — mesures " + ", ".join(sorted(mesures)))
    print("=" * 78)
    print(f"""
⚠️ CE QUE CES TROIS MESURES NE DIRONT PAS — à lire avant tout chiffre

   ELLES NE DIRONT PAS QU'UN CANDIDAT TROUVÉ HORS BORNE SOIT LE BON. Elles
   établissent que le lot ACTUEL ne contient pas de meilleur candidat; elles
   ne valident AUCUN appariement. *Un candidat à 94 hors borne peut être une
   autre entreprise — et le seul faux qu'on sache compter reste la
   convergence de plusieurs dossiers sur un même NEQ.*

   La mesure C porte sur un ÉCHANTILLON, pas sur les 8 931 : lever la borne
   coûte le gisement entier du préfixe, et `l` rend 309 788 lignes. Ce qu'elle
   rend devra être relu comme une proportion d'échantillon.

   ⚠️ Et son plafond de gisement ({milliers(args.gisement_max)} lignes) ÉCARTE exactement
   les cas où la borne fait le plus mal. Les refus sont COMPTÉS et affichés —
   un garde silencieux transformerait ce biais en résultat.

   RIEN N'EST CONSTRUIT. Ni tri par pertinence, ni nettoyage du registre, ni
   transformation à l'import, et surtout pas de borne relevée en production —
   elle coûterait sur CHAQUE résolution ce que C coûte une fois.
   Les échelles ne bougent pas : seuil {SEUIL_RESOLUTION_CONFIANTE:.0f}, écart 8.

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

        dossiers: list[Dossier] = []
        # Mesure A se remplit pendant la passe, pour ne pas récupérer deux fois.
        classes_candidats: Counter = Counter()
        classe_de_la_borne: Counter = Counter()
        lots_sans_lettre = 0
        for i, company in enumerate(orphelins):
            if i and i % 1000 == 0:
                print(f"   … {milliers(i)} examinés", flush=True)
            journal: dict = {}
            matches = req_source.resolve_neq_by_name(
                session, company.nom_detecte, ville=company.ville, journal=journal
            )
            nom_norm = normaliser(company.nom_detecte or "")
            d = Dossier(
                id=company.id, nom=company.nom_detecte or "", nom_norm=nom_norm,
                prefixe=journal.get("prefixe", ""), famille=famille_de(matches),
                score=matches[0].score if matches else 0.0,
                neq=matches[0].entry.neq if matches else None,
                ville=company.ville,
                sature=bool(journal.get("sature")),
                total=journal.get("total", 0),
                pont_ajoutes=journal.get("pont_ajoutes", 0),
                mots=set(nom_norm.split()),
            )
            dossiers.append(d)

            if "A" in mesures and d.sature:
                # ⚠️ La TRANCHE ALPHABÉTIQUE seule : les candidats venus du pont
                # sont récupérés par NEQ, pas par l'ordre — les mêler ici
                # diluerait le motif qu'on cherche.
                lot = req_source.candidats_par_nom(session, nom_norm)
                tranche = lot[: len(lot) - d.pont_ajoutes] if d.pont_ajoutes else lot
                vu_une_lettre = False
                for c in tranche:
                    classe = apres_le_prefixe(c.nom_normalise or "", d.prefixe)
                    classes_candidats[classe] += 1
                    if classe in ALPHABETIQUES:
                        vu_une_lettre = True
                if tranche:
                    classe_de_la_borne[
                        apres_le_prefixe(tranche[-1].nom_normalise or "", d.prefixe)
                    ] += 1
                if not vu_une_lettre:
                    lots_sans_lettre += 1

        satures = [d for d in dossiers if d.sature]
        print(f"   lots coupés par la borne : {milliers(len(satures))}"
              f"  ({_part(len(satures), total)})")

        # ================= MESURE A =========================================
        if "A" in mesures:
            print("\n" + "-" * 78)
            print("A. QUI REMPLIT LA TRANCHE? — ce qui suit le préfixe, dans les lots coupés")
            print("-" * 78)
            n_c = sum(classes_candidats.values())
            print(f"\n   candidats examinés (tranche alphabétique seule) : {milliers(n_c)}\n")
            print(f"   {'après le préfixe':<34} {'candidats':>11} {'part':>8}")
            for classe in CLASSES:
                k = classes_candidats.get(classe, 0)
                marque = "  ⚠️" if classe in NON_ALPHABETIQUES and k else ""
                print(f"   {classe:<34} {milliers(k):>11} {_part(k, n_c):>8}{marque}")
            non_alpha = sum(classes_candidats.get(c, 0) for c in NON_ALPHABETIQUES)
            print(f"\n   NON ALPHABÉTIQUE après le préfixe : {milliers(non_alpha)}"
                  f"  ({_part(non_alpha, n_c)})")

            print("\n   ⚠️ LE CHIFFRE QUI DIT JUSQU'OÙ LA TRANCHE VA")
            print("      Ce qui suit le préfixe chez le DERNIER candidat rendu — donc")
            print("      l'endroit où la coupe tombe dans l'ordre alphabétique.\n")
            n_b = sum(classe_de_la_borne.values())
            print(f"   {'au point de coupe':<34} {'lots':>11} {'part':>8}")
            for classe in CLASSES:
                k = classe_de_la_borne.get(classe, 0)
                print(f"   {classe:<34} {milliers(k):>11} {_part(k, n_b):>8}")
            print(f"\n   lots coupés AVANT LA PREMIÈRE LETTRE : {milliers(lots_sans_lettre)}"
                  f"  ({_part(lots_sans_lettre, len(satures))})")
            print("      *Là, le score n'a jamais vu un seul nom commençant par une")
            print("      lettre après le préfixe. Aucun réglage d'échelle ne rattrape ça.*")

        # ================= MESURE B =========================================
        if "B" in mesures:
            print("\n" + "-" * 78)
            print(f"B. LE SCORE PLANCHER — le pic [{bas_pic:.0f} – {haut_pic:.0f}[ "
                  f"est-il une population ou une valeur?")
            print("-" * 78)
            pic = [d for d in dossiers if bas_pic <= d.score < haut_pic]
            print(f"\n   dossiers dans le pic : {milliers(len(pic))}\n")
            valeurs: Counter = Counter(round(d.score, 2) for d in pic)
            print(f"   {'valeur EXACTE':>14} {'dossiers':>10} {'part':>8}")
            for valeur, k in valeurs.most_common(8):
                barre = "█" * max(1, round(30 * k / max(1, len(pic))))
                print(f"   {valeur:>14.2f} {milliers(k):>10} {_part(k, len(pic)):>8}  {barre}")
            if valeurs:
                dominante, k = valeurs.most_common(1)[0]
                print(f"\n   ⚠️ La valeur la plus fréquente pèse {_part(k, len(pic))} du pic.")
                print("      *Une distribution de RESSEMBLANCE ne se concentre pas sur une")
                print("      valeur. Un PLANCHER de calcul, si.*")

            plancher = [d for d in pic if bas_pl <= d.score < haut_pl]
            print(f"\n   dont [{bas_pl:.0f} – {haut_pl:.0f}[ : {milliers(len(plancher))}"
                  f"  ({_part(len(plancher), len(pic))} du pic)")

            print("\n   COMBIEN DE MOTS EN COMMUN avec leur candidat?\n")
            print("   ⚠️ Comparé à TOUTES les formes publiées du NEQ, en gardant le")
            print("      MEILLEUR recouvrement. *Aucun score n'est recalculé : si même")
            print("      la meilleure forme ne partage que le premier mot, la lecture")
            print("      tient a fortiori.*\n")
            partages: Counter = Counter()
            for d in plancher:
                if not d.neq:
                    partages["aucun candidat"] += 1
                    continue
                meilleur = 0
                premier_seul = False
                for _, nom, _ in formes_publiees(session, [d.neq]):
                    communs = d.mots & set(normaliser(nom).split())
                    if len(communs) > meilleur:
                        meilleur = len(communs)
                        premier_seul = communs == {d.prefixe}
                if meilleur == 0:
                    partages["AUCUN mot en commun"] += 1
                elif meilleur == 1 and premier_seul:
                    partages["le PREMIER MOT seulement"] += 1
                elif meilleur == 1:
                    partages["un seul mot, pas le premier"] += 1
                elif meilleur == 2:
                    partages["deux mots"] += 1
                else:
                    partages["trois mots ou plus"] += 1
            for cle, k in partages.most_common():
                marque = "  ⚠️" if "PREMIER MOT seulement" in cle else ""
                print(f"   {cle:<34} {milliers(k):>10} {_part(k, len(plancher)):>8}{marque}")
            seul = partages.get("le PREMIER MOT seulement", 0)
            print(f"\n   ⇒ {_part(seul, len(plancher))} des dossiers du plancher ne partagent")
            print("     QUE le premier mot avec leur meilleur candidat.")

        # ================= MESURE C =========================================
        if "C" in mesures:
            print("\n" + "-" * 78)
            print("C. CE QU'UN LOT DIFFÉRENT CHANGERAIT — borne levée, sur échantillon")
            print("-" * 78)
            gisements: dict[str, int] = {}
            for d in satures:
                if d.prefixe not in gisements:
                    gisements[d.prefixe] = session.execute(
                        select(func.count()).select_from(REQEntry)
                        .where(REQEntry.nom_normalise.op("GLOB")(f"{d.prefixe}*"))
                    ).scalar() or 0
            tire = echantillon_reparti(
                satures, args.echantillon, cle=lambda d: (gisements[d.prefixe], d.id)
            )
            retenus = [d for d in tire if gisements[d.prefixe] <= args.gisement_max]
            refuses = [d for d in tire if gisements[d.prefixe] > args.gisement_max]
            lignes = sum(gisements[d.prefixe] for d in retenus)

            # ---- LE BUDGET, ANNONCÉ AVANT D'ÊTRE DÉPENSÉ --------------------
            print(f"""
   ⚠️ LE BUDGET, AVANT DE LE DÉPENSER

      échantillon tiré          : {milliers(len(tire))} dossier(s) sur {milliers(len(satures))} coupés
      règle de tirage           : rangs régulièrement espacés sur les coupés
                                  TRIÉS PAR GISEMENT — pour que les gros
                                  préfixes soient représentés, pas noyés
      dossiers RETENUS          : {milliers(len(retenus))}
      dossiers REFUSÉS (gisement > {milliers(args.gisement_max)}) : {milliers(len(refuses))}  ({_part(len(refuses), len(tire))})
      lignes à charger au total : {milliers(lignes)}
      plus gros gisement retenu : {milliers(max((gisements[d.prefixe] for d in retenus), default=0))}
      mémoire, ORDRE DE GRANDEUR: ≈ {milliers(max((gisements[d.prefixe] for d in retenus), default=0) * OCTETS_PAR_LIGNE_ESTIMES // 1_000_000)} Mo au pic
                                  (~{OCTETS_PAR_LIGNE_ESTIMES} octets/ligne — UNE ESTIMATION,
                                  pas une mesure)
""")
            if refuses:
                print("      ⚠️ LES REFUSÉS SONT EXACTEMENT LES CAS OÙ LA BORNE FAIT LE")
                print("         PLUS MAL. Leurs gisements, pour dire ce qu'un plafond")
                print("         relevé coûterait :")
                for d in sorted(refuses, key=lambda d: -gisements[d.prefixe])[:5]:
                    print(f"            {d.prefixe[:20]:<22} {milliers(gisements[d.prefixe]):>10} lignes")
                print()

            franchissent = 0
            gagnes_par_famille: Counter = Counter()
            exemples: list[tuple[Dossier, float, str, str]] = []
            for n, d in enumerate(retenus):
                if n and n % 25 == 0:
                    print(f"   … {milliers(n)} / {milliers(len(retenus))} rejoués", flush=True)
                gisement = gisements[d.prefixe]
                matches = req_source.resolve_neq_by_name(
                    # ⚠️ LA MÊME VILLE DES DEUX CÔTÉS. *Sans elle, la borne
                    # levée perdrait le bonus de +5 et paraîtrait pire qu'elle
                    # n'est — c'est le défaut des -338, en miroir.*
                    session, d.nom, ville=d.ville, limite_candidats=gisement + 10_000
                )
                if not matches:
                    continue
                nouveau = matches[0]
                if nouveau.score >= SEUIL_RESOLUTION_CONFIANTE > d.score:
                    franchissent += 1
                    gagnes_par_famille[d.famille] += 1
                    if len(exemples) < 8:
                        exemples.append(
                            (d, nouveau.score, nouveau.entry.neq, nouveau.entry.nom or "")
                        )
            print(f"\n   FRANCHISSENT LE SEUIL DE {SEUIL_RESOLUTION_CONFIANTE:.0f} "
                  f"une fois la borne levée : {milliers(franchissent)}"
                  f" sur {milliers(len(retenus))}  ({_part(franchissent, len(retenus))})")
            if gagnes_par_famille:
                print("\n   par famille d'origine :")
                for f in FAMILLES:
                    k = gagnes_par_famille.get(f, 0)
                    if k:
                        print(f"      {f:<18} {milliers(k):>8}")
            for d, score, neq, nom in exemples:
                print(f"\n      {d.nom[:56]}")
                print(f"         borné  : {d.score:>6.2f}  ({d.famille})")
                print(f"         levé   : {score:>6.2f}  [{neq}] {nom[:44]!r}")
            print("\n   ⚠️ Un franchissement n'est PAS un appariement juste. Ce chiffre dit")
            print("      que le lot borné ne contenait pas ce candidat — rien de plus.")

        print("\n" + "=" * 78)
        print("   RIEN N'EST CONSTRUIT. Le tri, le nettoyage et la borne se décident")
        print("   avec Alexandre, et sur ces chiffres.")
        print("=" * 78)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
