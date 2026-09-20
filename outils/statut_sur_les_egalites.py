#!/usr/bin/env python3
"""Ce que le STATUT DE L'ENTREPRISE laisserait debout — sur les égalités, et
sur tous les ambigus.

## Le motif

**Les paliers sont confirmés** : sur les 3 267 ambigus, **2 889 ont leurs deux
scores sur un palier**, et **1 629 sont à ÉGALITÉ STRICTE**.

⚠️ **Pour une égalité stricte, aucune valeur d'écart ne change rien** : *zéro
reste sous n'importe quel seuil.* **Ce n'est pas une échelle mal calibrée — c'est
que le nom a fini son travail.** *Il faut un autre fait, et le statut en est un
qui est déjà à côté de chaque candidat.*

## ⚠️ CE QUE CETTE MESURE NE DIRA PAS — à lire avant tout chiffre

**Qu'un départage par le statut serait JUSTE.** *Une entreprise radiée peut être
la bonne* : un signal ancien peut désigner une entreprise fermée depuis.

⚠️ **Et le produit ne peut pas distinguer ces deux cas** : `REQEntry` **ne porte
aucune date de radiation** — seulement `date_maj_req`. *Comparer la date du
signal à celle de la radiation est impossible avec ce que le miroir garde.*

⚠️ **Aucune règle n'est proposée.** *Préférer un statut est une échelle, et elle
se pose avec Alexandre.*

## ⚠️ Ce n'est PAS un départageur au sens de `outils/departageurs.py`

*Là-bas, `departager` compare **un fait que le dossier porte** aux faits des
candidats* — une ville, un code postal, une activité. **Le statut n'est porté que
d'un côté : le registre.** *Le dossier n'a pas de statut à opposer.*

**C'est donc une EXCLUSION, pas une comparaison** — et une exclusion a un mode de
panne que la comparaison n'a pas : **elle peut vider le lot.** *C'est le
`AUCUN_COMPATIBLE` du départageur, et il est compté ici comme un résultat, jamais
comme un cas manquant.*

## ⚠️ `ni` n'est pas « immatriculée », et deux exclusions ne se valent pas

**Lu dans le code, pas supposé** — `falkye/sources/req.py`, lignes 114-119,
*« codes confirmés par inspection réelle de `DomaineValeur.csv`
(`TYP_DOM_VAL='STAT_IMMAT'`) le 2026-08-31 »* :

| code | libellé lu à la source | ce que le miroir stocke |
|---|---|---|
| `IM` | Immatriculée | `immatriculee` |
| `RD` · `RO` · `RX` | Radiée sur demande · d'office · art. 59 | `radiee` |
| **`NI`** | **Non immatriculée** | **`ni`** — brut |
| **`AI`** | **Avis d'intention de constitution** | **`ai`** — brut |

**Donc DEUX exclusions différentes, et l'écart entre elles est exactement le
poids de `ni` et `ai` :**

1. **ne garder que les IMMATRICULÉES** — la plus stricte;
2. **n'écarter que les RADIÉES** — `ni` et `ai` restent en lice.

⚠️ **La mesure rend les deux côte à côte et n'en recommande aucune.** *Une seule
colonne ferait passer un choix pour un fait.*

⚠️ **AUCUNE ÉCRITURE. Les échelles ne bougent pas : seuil 92, écart 8.**

Usage, SUR L'HÔTE :
    python3 -m outils.statut_sur_les_egalites
    python3 -m outils.statut_sur_les_egalites --chemin /opt/falkye/import
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter

from outils.nombres import milliers

#: Les libellés **relevés dans le code**, avec leur provenance. ⚠️ *Ce sont des
#: codes déjà lus le 2026-08-31 dans `DomaineValeur.csv`, pas devinés* — et
#: `--chemin` les reconfronte à l'archive du jour plutôt que de les croire.
LIBELLES_RELEVES = {
    "IM": "Immatriculée",
    "AI": "Avis d'intention de constitution",
    "NI": "Non immatriculée",
    "RD": "Radiée sur demande",
    "RO": "Radiée d'office",
    "RX": "Radiée d'office (article 59)",
}
PROVENANCE_DES_LIBELLES = (
    "falkye/sources/req.py, lignes 114-119 — « codes confirmés par inspection "
    "réelle de DomaineValeur.csv (TYP_DOM_VAL='STAT_IMMAT') le 2026-08-31 »"
)
DOMAINE_DU_STATUT = "STAT_IMMAT"

#: Ce que le miroir stocke, après `_decoder_statut_reel`.
IMMATRICULEE = "immatriculee"
RADIEE = "radiee"

#: Les deux exclusions, **nommées et rendues côte à côte**. ⚠️ *Une seule
#: colonne ferait passer un choix pour un fait.*
GARDER_IMMATRICULEES = "ne garder que les IMMATRICULÉES"
ECARTER_RADIEES = "n'écarter que les RADIÉES"
LES_DEUX_EXCLUSIONS = (GARDER_IMMATRICULEES, ECARTER_RADIEES)

#: Ce qu'il reste après une exclusion. ⚠️ **`AUCUN` est un RÉSULTAT** — c'est le
#: `AUCUN_COMPATIBLE` de `outils/departageurs.py`, et une exclusion qui vide le
#: lot ne se range pas avec « rien à dire ».
AUCUN = "il n'en reste AUCUN — l'exclusion les vide"
UN_SEUL = "il n'en reste qu'UN"
PLUSIEURS = "il en reste PLUSIEURS"
CE_QUI_RESTE = (UN_SEUL, PLUSIEURS, AUCUN)

#: La largeur de la colonne des cas, et celle d'une colonne d'exclusion.
#: ⚠️ **Une étiquette plus longue que sa colonne POUSSE le nombre**, et la ligne
#: cesse d'être alignée sans qu'aucun chiffre ait bougé. *Quatrième occurrence
#: en quatre outils; un test les vérifie désormais au lieu d'un relecteur.*
LARGEUR_DU_CAS = 44
LARGEUR_DUNE_EXCLUSION = 32


def _part(k: int, n: int) -> str:
    return f"{100 * k / n:.1f} %" if n else "—"


def ex_aequo(matches) -> list:
    """Les candidats dont le score ÉGALE le meilleur — **égalité stricte.**

    ⚠️ *Ils peuvent être plus de deux.* **Et pour eux, aucune valeur d'écart ne
    change rien : zéro reste sous n'importe quel seuil.**
    """
    if not matches:
        return []
    haut = matches[0].score
    return [m for m in matches if m.score == haut]


def ce_qui_reste(groupe, exclusion: str) -> str:
    """Ce que l'exclusion laisse debout dans ce groupe de candidats."""
    if exclusion == GARDER_IMMATRICULEES:
        restants = [m for m in groupe if m.entry.statut == IMMATRICULEE]
    else:
        restants = [m for m in groupe if m.entry.statut != RADIEE]
    if not restants:
        return AUCUN
    return UN_SEUL if len(restants) == 1 else PLUSIEURS


def libelles_de_larchive(chemin) -> dict[str, str] | None:
    """Les libellés `STAT_IMMAT` **relus dans l'archive du jour.**

    *Rend `None` si l'archive est introuvable* — et l'appelant doit alors dire
    « non reconfronté », jamais « conforme ».
    """
    import zipfile

    from outils.archives_req import resoudre
    from outils.profil_des_absents_req import charger_domaines

    archive = resoudre(chemin)
    if archive is None:
        return None
    with zipfile.ZipFile(archive) as zf:
        domaines = charger_domaines(zf)
    return {
        code: libelle for (domaine, code), libelle in domaines.items()
        if domaine == DOMAINE_DU_STATUT
    }


def _rendre_les_deux_exclusions(titre: str, resultats: dict[str, Counter],
                                n: int) -> None:
    """Les deux exclusions **côte à côte**, sur le même groupe."""
    print(f"\n   {titre} — {milliers(n)} dossier(s)\n")
    print(f"   {'':<{LARGEUR_DU_CAS}} "
          + "".join(f"{e:>{LARGEUR_DUNE_EXCLUSION}}" for e in LES_DEUX_EXCLUSIONS))
    for cas in CE_QUI_RESTE:
        cellules = ""
        for exclusion in LES_DEUX_EXCLUSIONS:
            k = resultats[exclusion].get(cas, 0)
            cellules += f"{milliers(k):>22} {_part(k, n):>9}"
        print(f"   {cas:<{LARGEUR_DU_CAS}}{cellules}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--chemin", default=None,
                        help="l'archive du REQ — pour RECONFRONTER les libellés "
                             "relevés dans le code à ceux du jour")
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
    from falkye.resolution import (
        SEUIL_AMBIGUITE_ECART_MIN,
        SEUIL_RESOLUTION_CONFIANTE,
        famille_de,
    )
    from outils.departageur_adresse import concurrents_de
    from outils.reresolution_neq import _resoudre_une

    print("=" * 78)
    print("CE QUE LE STATUT LAISSERAIT DEBOUT — sur les égalités, et sur tous")
    print("=" * 78)
    print(f"""
⚠️ CE QUE CETTE MESURE NE DIRA PAS — avant tout chiffre

   QU'UN DÉPARTAGE PAR LE STATUT SERAIT JUSTE. Une entreprise radiée peut
   être la bonne : un signal ancien peut désigner une entreprise fermée
   depuis. Et le produit ne peut PAS distinguer ces deux cas — `REQEntry`
   ne porte AUCUNE date de radiation, seulement `date_maj_req`.

   AUCUNE RÈGLE N'EST PROPOSÉE. Préférer un statut est une échelle, et elle
   se pose avec Alexandre.

⚠️ CE N'EST PAS UN DÉPARTAGEUR AU SENS DE `outils/departageurs.py`

   Là-bas, `departager` compare un fait QUE LE DOSSIER PORTE aux faits des
   candidats. Le statut n'est porté que d'un côté : le registre. C'est donc
   une EXCLUSION, et une exclusion a un mode de panne que la comparaison
   n'a pas — elle peut VIDER le lot. C'est compté ici comme un résultat.

   AUCUNE ÉCRITURE. Les échelles ne bougent pas : seuil {SEUIL_RESOLUTION_CONFIANTE:.0f}, écart {SEUIL_AMBIGUITE_ECART_MIN:.0f}.
""")

    # ---- 1. CE QUE LES CODES SIGNIFIENT ---------------------------------
    print("-" * 78)
    print("1. LES CODES DE STATUT — lus, pas supposés")
    print("-" * 78)
    print(f"\n   Relevés dans le code : {PROVENANCE_DES_LIBELLES}\n")
    for code_statut, libelle in sorted(LIBELLES_RELEVES.items()):
        stocke = {"IM": IMMATRICULEE}.get(code_statut)
        if code_statut in ("RD", "RO", "RX"):
            stocke = RADIEE
        print(f"      {code_statut:<4} {libelle:<40} → {stocke or code_statut.lower()}")
    print(f"""
   ⚠️ `ni` ET `ai` NE SONT NI L'UN NI L'AUTRE. Le miroir garde leur code
      brut, et `falkye/resolution.py` transforme ensuite TOUT ce qui n'est
      pas `radiee` en `IMMATRICULEE` sur le dossier. Ils sont comptés à part
      ici, jamais avec les immatriculées.
""")
    if args.chemin:
        relus = libelles_de_larchive(args.chemin)
        if relus is None:
            print(f"   ⚠️ Aucune archive à {args.chemin!r} — les libellés ne sont PAS")
            print("      reconfrontés. Ce n'est pas « conformes ».")
        else:
            ecarts = [
                (c, LIBELLES_RELEVES.get(c), relus.get(c))
                for c in sorted(set(LIBELLES_RELEVES) | set(relus))
                if (LIBELLES_RELEVES.get(c) or "").strip() != (relus.get(c) or "").strip()
            ]
            print(f"   Reconfrontés à l'archive : {milliers(len(relus))} code(s) lus.")
            if not ecarts:
                print("   ✅ Aucun écart avec le relevé du 2026-08-31.")
            for c, du_code, de_larchive in ecarts:
                print(f"   ⚠️ {c} : code={du_code or '(absent)'} · "
                      f"archive={de_larchive or '(absent)'}")
    else:
        print("   ⚠️ Libellés NON reconfrontés à l'archive (pas de --chemin).")
        print("      Le relevé date du 2026-08-31; un code a pu être ajouté depuis.")

    session = get_session()
    try:
        requete = select(Company).where(Company.neq.is_(None)).order_by(Company.id)
        if args.limite:
            requete = requete.limit(args.limite)
        restants = list(session.execute(requete).scalars().all())
        if not restants:
            print("\n   Aucun restant à mesurer.")
            print("   RIEN N'A ÉTÉ ÉCRIT. Les échelles n'ont pas bougé.")
            return 0

        print(f"\n… rejeu de la résolution sur {milliers(len(restants))} restants, "
              f"par le chemin de production", flush=True)
        statuts_vus: Counter = Counter()
        sur_egalites: dict[str, Counter] = {e: Counter() for e in LES_DEUX_EXCLUSIONS}
        sur_ambigus: dict[str, Counter] = {e: Counter() for e in LES_DEUX_EXCLUSIONS}
        tailles_egalite: Counter = Counter()
        n_amb = n_ega = 0
        ni_ou_ai_en_lice = 0
        for i, company in enumerate(restants, 1):
            if args.pas and i % args.pas == 0:
                print(f"   … {milliers(i)} / {milliers(len(restants))}", flush=True)
            _neq, matches = _resoudre_une(session, company)
            if famille_de(matches) != "ambigu":
                continue
            n_amb += 1
            concurrents = concurrents_de(matches)
            egaux = ex_aequo(matches)
            for m in concurrents:
                statuts_vus[m.entry.statut or "(vide)"] += 1
            if any(m.entry.statut not in (IMMATRICULEE, RADIEE) for m in concurrents):
                ni_ou_ai_en_lice += 1
            for exclusion in LES_DEUX_EXCLUSIONS:
                sur_ambigus[exclusion][ce_qui_reste(concurrents, exclusion)] += 1
            if len(egaux) >= 2:
                n_ega += 1
                tailles_egalite[min(len(egaux), 5)] += 1
                for exclusion in LES_DEUX_EXCLUSIONS:
                    sur_egalites[exclusion][ce_qui_reste(egaux, exclusion)] += 1

        print(f"\n   AMBIGUS : {milliers(n_amb)}"
              f"   ·   dont à ÉGALITÉ STRICTE : {milliers(n_ega)}")
        if not n_amb:
            print("   Aucun ambigu — rien à ventiler, et ce n'est pas « 0 ».")
            print("   RIEN N'A ÉTÉ ÉCRIT. Les échelles n'ont pas bougé.")
            return 0

        # ---- 2. LES STATUTS EN PRÉSENCE ---------------------------------
        print("\n" + "-" * 78)
        print("2. LES STATUTS DES CANDIDATS — toute la surface")
        print("-" * 78)
        total_c = sum(statuts_vus.values())
        print(f"\n   {'statut stocké':<20} {'candidats':>10} {'part':>8}   libellé")
        for statut, k in statuts_vus.most_common():
            libelle = next(
                (v for c, v in LIBELLES_RELEVES.items() if c.lower() == statut), "")
            if statut == IMMATRICULEE:
                libelle = LIBELLES_RELEVES["IM"]
            elif statut == RADIEE:
                libelle = "Radiée (RD · RO · RX confondus)"
            marque = "" if statut in (IMMATRICULEE, RADIEE) else "   ⚠️ NI l'un NI l'autre"
            print(f"   {statut:<20} {milliers(k):>10} {_part(k, total_c):>8}   "
                  f"{libelle[:34]}{marque}")
        print(f"\n   {milliers(ni_ou_ai_en_lice)} ambigu(s) ont au moins un concurrent "
              f"qui n'est NI immatriculé NI radié.")
        print("   ⚠️ C'est exactement l'écart entre les deux exclusions ci-dessous.")

        # ---- 3. LES ÉGALITÉS STRICTES ------------------------------------
        print("\n" + "-" * 78)
        print("3. LES ÉGALITÉS STRICTES — là où aucun écart ne change rien")
        print("-" * 78)
        print(f"""
   ⚠️ POUR CES DOSSIERS, LE NOM A FINI SON TRAVAIL. Zéro reste sous
      n'importe quel seuil : ce n'est pas une échelle mal calibrée.
""")
        if n_ega:
            print("   candidats à égalité — " + "  ".join(
                f"{k if k < 5 else '5+'} : {milliers(v)}"
                for k, v in sorted(tailles_egalite.items())))
            _rendre_les_deux_exclusions("SUR LES ÉGALITÉS STRICTES", sur_egalites, n_ega)
        else:
            print("   Aucune égalité stricte — et ce n'est pas « 0 exclusion ».")

        # ---- 4. TOUS LES AMBIGUS -----------------------------------------
        print("\n" + "-" * 78)
        print("4. TOUS LES AMBIGUS — le statut vaut aussi là où l'écart est de 5")
        print("-" * 78)
        _rendre_les_deux_exclusions("SUR TOUS LES AMBIGUS", sur_ambigus, n_amb)
        print("""
   ⚠️ LE GROUPE EST CELUI DES CONCURRENTS — `concurrents_de`, les candidats
      à moins de l'écart du meilleur. C'est l'ensemble sur lequel un
      départageur agit, et c'est la fonction du produit, pas une copie.

   ⚠️ « IL N'EN RESTE AUCUN » EST UN RÉSULTAT, pas un cas manquant. C'est le
      `AUCUN_COMPATIBLE` de `outils/departageurs.py` : une exclusion qui vide
      le lot n'a pas départagé, elle a tout écarté.

   ⚠️ ET L'ÉCART ENTRE LES DEUX COLONNES EST LE POIDS DE `ni` ET `ai`. Ce
      sont deux règles différentes, ni l'une ni l'autre n'est proposée, et
      les rendre ensemble est ce qui empêche de prendre un choix pour un
      fait.
""")
        print("=" * 78)
        print("   RIEN N'A ÉTÉ ÉCRIT. Les échelles n'ont pas bougé.")
        print("   ⚠️ UNE RADIÉE PEUT ÊTRE LA BONNE, et le miroir ne porte aucune date")
        print("   de radiation pour en juger. Ce qui précède compte ce qui resterait,")
        print("   jamais ce qui serait juste.")
        print("=" * 78)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
