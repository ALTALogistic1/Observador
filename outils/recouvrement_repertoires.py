#!/usr/bin/env python3
"""Combien des entreprises NON RÉSOLUES trois répertoires publics apparient — et
**par quel champ**.

**La question qu'il tranche** *(Alexandre, 2026-09-15)* : *« Si `AUTRES_NOMS` en
apparie deux cents, la forme est validée — et c'est l'argument pour aller chercher
la même chose au REQ, à l'échelle du registre entier. »* **Le nombre apparié compte
moins que sa VENTILATION PAR CHAMP** : un appariement par `NOM_COMMERCANT` ne prouve
rien qu'on ne sache déjà *(c'est la raison sociale, celle que le miroir porte)*;
un appariement par `AUTRES_NOMS` ou `NOM_COMMERCIAL` prouve qu'un pont
**enseigne → raison sociale** répare ce que le score ne peut pas réparer.

**PORTÉE — ce que cet outil mesure, et ce qu'il ne mesure pas.**

- Il lit les `Company` **sans NEQ** de la base durable, et rien d'autre. *Il ne
  mesure pas la justesse d'une résolution : il mesure une occasion manquée.*
- Il apparie **par ÉGALITÉ de forme normalisée**, jamais par score flou. *C'est
  délibéré : un appariement exact ne se discute pas, et la question posée est
  « le pont existe-t-il », pas « jusqu'où peut-on l'étirer ».* **Un compte rendu
  ici est donc un PLANCHER, pas un plafond.**
- ⚠️ **Il n'écrit rien.** Aucun NEQ n'est posé, aucune `Company` n'est touchée.
  *Un appariement mesuré n'est pas un appariement décidé* — la promotion de ces
  ponts au moteur est une décision d'Alexandre, pas un effet de bord de la mesure.
- ⚠️ **Le NEQ rendu par un répertoire n'est pas vérifié contre le REQ.** Il est
  rapporté tel que la source le publie. *Un chiffre recopié d'une source n'est pas
  un chiffre vérifié* — l'outil dit combien de lignes en portent un, pas combien
  sont justes.

**Les trois répertoires, et pourquoi ceux-là** *(relevé du catalogue, 2026-09-15)*.

| répertoire | lignes | champs de nom | NEQ |
|---|---|---|---|
| OPC — permis et exemptions en vigueur | 10 065 | `NOM_COMMERCANT`, `AUTRES_NOMS` | `NEQ` |
| OPC — commerçants de Parle consommation | 783 | `NOM_COMMERCANT`, `AUTRES_NOMS`, `NOM_COMMERCIAL` | `NEQ` |
| OQLF — entreprises certifiées | 14 614 | `NOM_ENTREPRISE` | `MATRICULE` ⚠️ |

⚠️ **`MATRICULE` de l'OQLF a la FORME d'un NEQ** (dix chiffres, préfixe `11`), et
l'outil le rapporte comme tel — *mais l'OQLF ne le nomme jamais « NEQ »*. **C'est une
ressemblance de forme, pas une équivalence déclarée par la source.** L'outil compte
séparément les matricules de forme NEQ et les autres, pour que l'écart se voie.

**Ce qu'un recouvrement faible voudrait dire, et qu'il faut savoir d'avance.** Ces
trois répertoires couvrent des secteurs ÉTROITS — commerce de détail réglementé,
recouvrement, véhicules routiers, entreprises de 25 employés et plus soumises à la
francisation. **Les entreprises non résolues viennent majoritairement de l'EIMT**
*(74,5 % du mur)*, dont le profil sectoriel n'a aucune raison de coïncider. *Un
recouvrement de quelques dizaines n'infirme donc PAS la forme du pont : il dit que
ces trois répertoires-là ne sont pas le bon gisement.* **L'infirmation viendrait
d'un appariement par `NOM_COMMERCANT` massif et par `AUTRES_NOMS` nul** — là, le
pont ne servirait à rien.

Usage :
    python3 outils/recouvrement_repertoires.py
    python3 outils/recouvrement_repertoires.py --exemples 30
    python3 outils/recouvrement_repertoires.py --source opc-permis
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter

#: Les ressources CKAN, relevées le 2026-09-15 par `package_show`. **Les identifiants
#: sont figés ici, pas redécouverts à chaque appel** : une ressource remplacée doit se
#: voir comme un échec bruyant, pas se substituer en silence à celle qu'on a mesurée.
#: *(Même discipline que les fiches de source — une mesure doit pouvoir être refaite
#: sur le même objet.)*
REPERTOIRES: dict[str, dict] = {
    "opc-permis": {
        "titre": "OPC — permis et exemptions en vigueur",
        "paquet": "liste-des-permis-actifs",
        "ressource": "c40c7af7-4a27-4272-be91-208994c67b7b",
        "licence": "CC-BY 4.0",
        "champ_neq": "NEQ",
        # L'ORDRE compte : il est rendu tel quel dans la ventilation, et il dit
        # lequel des champs a fait l'appariement quand plusieurs le pourraient.
        "champs_nom": ["NOM_COMMERCANT", "AUTRES_NOMS"],
        "multivalue": {"AUTRES_NOMS": "//"},
    },
    "opc-parle": {
        "titre": "OPC — commerçants participant à Parle consommation",
        "paquet": "liste-des-commercants-participant-a-parle-consommation",
        "ressource": "9c769e6a-a30a-4ed4-9c29-ce3a1e3a59af",
        "licence": "CC-BY 4.0",
        "champ_neq": "NEQ",
        "champs_nom": ["NOM_COMMERCANT", "AUTRES_NOMS", "NOM_COMMERCIAL"],
        "multivalue": {"AUTRES_NOMS": "//"},
    },
    "oqlf": {
        "titre": "OQLF — entreprises certifiées",
        "paquet": "entreprises-certifiees-oqlf",
        "ressource": "da4c0cc2-7022-45c3-b5f5-a1e4ecf39e77",
        "licence": "CC-BY 4.0",
        # ⚠️ PAS nommé « NEQ » par la source. Voir la réserve en tête de module.
        "champ_neq": "MATRICULE",
        "champs_nom": ["NOM_ENTREPRISE"],
        "multivalue": {},
    },
}

#: Un NEQ québécois : dix chiffres. **Sert à qualifier `MATRICULE`, pas à le valider** —
#: la forme ne dit pas que le numéro désigne la bonne entreprise.
MOTIF_NEQ = re.compile(r"^\d{10}$")

#: Taille de page du parcours `datastore_search`. 1 000 est le plafond usuel de CKAN;
#: au-delà l'API tronque en silence, ce qui produirait un recouvrement sous-évalué
#: sans qu'aucune erreur ne s'affiche *(l'absence de mesure n'est pas une mesure nulle)*.
TAILLE_PAGE = 1000


def formes_du_nom(brut: str, normaliser) -> list[str]:
    """Toutes les formes normalisées non vides qu'une cellule porte.

    `AUTRES_NOMS` de l'OPC empile plusieurs enseignes séparées par `//` —
    *« Olivier Kia Baie-Comeau//Olivier Occasion Baie-Comeau »*. **Une cellule
    multivaluée comptée comme une seule chaîne n'apparie jamais rien**, et
    l'échec serait silencieux.
    """
    formes = []
    for morceau in re.split(r"//", brut or ""):
        n = normaliser(morceau)
        if n:
            formes.append(n)
    return formes


def charger_repertoire(client, cle: str, spec: dict, normaliser, journal=print) -> dict:
    """Parcourt une ressource entière et rend l'index `forme normalisée → entrées`.

    Rend aussi le compte de lignes lues, **pour qu'il puisse être comparé au `total`
    annoncé par CKAN** : un parcours qui s'arrête tôt doit se voir.
    """
    index: dict[str, list[dict]] = {}
    lignes = 0
    total_annonce = None
    offset = 0
    while True:
        res = client.datastore_search(spec["ressource"], limit=TAILLE_PAGE, offset=offset)
        if total_annonce is None:
            total_annonce = res.get("total")
        enregistrements = res.get("records", [])
        if not enregistrements:
            break
        for rec in enregistrements:
            lignes += 1
            neq = str(rec.get(spec["champ_neq"]) or "").strip()
            for champ in spec["champs_nom"]:
                for forme in formes_du_nom(str(rec.get(champ) or ""), normaliser):
                    index.setdefault(forme, []).append(
                        {"source": cle, "champ": champ, "neq": neq,
                         "brut": str(rec.get(champ) or "")[:80]}
                    )
        offset += len(enregistrements)
        if total_annonce is not None and offset >= total_annonce:
            break
    return {"index": index, "lignes": lignes, "total_annonce": total_annonce}


def ventilation(appariements: list[dict]) -> Counter:
    """`source · champ` → compte. **La ventilation est le résultat, pas le total.**"""
    return Counter(f"{a['source']} · {a['champ']}" for a in appariements)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--exemples", type=int, default=15,
                        help="nombre de paires montrées par champ apparieur (défaut 15)")
    parser.add_argument("--source", action="append", choices=sorted(REPERTOIRES),
                        help="limiter à un répertoire (répétable; défaut : les trois)")
    args = parser.parse_args(argv)

    try:
        from sqlalchemy import select

        from falkye.db import get_session
        from falkye.models.company import Company
        from falkye.sources.ckan_client import DONNEES_QUEBEC_BASE, CKANClient
        from falkye.sources.column_mapping import normaliser
    except ImportError as exc:  # pragma: no cover - dépend de l'environnement
        print(f"Import impossible ({exc}). Lancer depuis la racine du dépôt, "
              "dans l'environnement de FALKYE.", file=sys.stderr)
        return 2

    cles = args.source or sorted(REPERTOIRES)
    client = CKANClient(DONNEES_QUEBEC_BASE)

    print("=" * 78)
    print("RECOUVREMENT DES ENTREPRISES NON RÉSOLUES AVEC TROIS RÉPERTOIRES PUBLICS")
    print("=" * 78)
    print("\nPORTÉE : appariement par ÉGALITÉ de forme normalisée, jamais par score.")
    print("         Le compte rendu est un PLANCHER. Rien n'est écrit en base.")
    print("         Le NEQ des répertoires est rapporté tel que publié, non vérifié.")

    session = get_session()
    try:
        entreprises = session.execute(
            select(Company).where(Company.neq.is_(None))
        ).scalars().all()
        print(f"\nentreprises sans NEQ en base : {len(entreprises)}")
        if not entreprises:
            print("Rien à apparier.")
            return 0

        # Index des noms détectés — une forme peut être portée par plusieurs Company.
        par_forme: dict[str, list] = {}
        vides = 0
        for c in entreprises:
            n = normaliser(c.nom_detecte or "")
            if not n:
                vides += 1
                continue
            par_forme.setdefault(n, []).append(c)
        print(f"formes normalisées distinctes : {len(par_forme)}"
              + (f"   ({vides} nom(s) vide(s) après normalisation)" if vides else ""))

        catalogues = {}
        for cle in cles:
            spec = REPERTOIRES[cle]
            print(f"\n… lecture de {spec['titre']}", flush=True)
            cat = charger_repertoire(client, cle, spec, normaliser)
            catalogues[cle] = cat
            ecart = ""
            if cat["total_annonce"] is not None and cat["lignes"] != cat["total_annonce"]:
                ecart = f"   ⚠️ PARCOURS INCOMPLET (CKAN annonce {cat['total_annonce']})"
            print(f"   {cat['lignes']} ligne(s) lue(s), "
                  f"{len(cat['index'])} forme(s) de nom distincte(s){ecart}")

        # ---- l'appariement ------------------------------------------------
        appariements: list[dict] = []
        entreprises_appariees: dict[int, list[dict]] = {}
        for cle in cles:
            index = catalogues[cle]["index"]
            for forme, companies in par_forme.items():
                for entree in index.get(forme, []):
                    for c in companies:
                        a = dict(entree, forme=forme, company=c)
                        appariements.append(a)
                        entreprises_appariees.setdefault(c.id, []).append(a)

        print("\n" + "=" * 78)
        print("LE RÉSULTAT")
        print("=" * 78)
        print(f"\n   entreprises non résolues appariées : {len(entreprises_appariees)}"
              f"  sur {len(entreprises)}"
              f"   ({100 * len(entreprises_appariees) / len(entreprises):.1f} %)")
        print(f"   appariements (une entreprise peut en avoir plusieurs) : {len(appariements)}")

        print("\n   VENTILATION PAR CHAMP APPARIEUR — c'est ELLE qui tranche :")
        vent = ventilation(appariements)
        if not vent:
            print("      aucun")
        for label, n in vent.most_common():
            print(f"      {n:>6}  {label}")

        # Le NEQ : sans lui, l'appariement ne résout rien.
        print("\n   CE QUE L'APPARIEMENT REND — un NEQ, ou seulement un nom :")
        avec, forme_neq, sans = 0, 0, 0
        for aid, lst in entreprises_appariees.items():
            neqs = {a["neq"] for a in lst if a["neq"]}
            if not neqs:
                sans += 1
            else:
                avec += 1
                if any(MOTIF_NEQ.match(n) for n in neqs):
                    forme_neq += 1
        print(f"      {avec:>6}  entreprise(s) dont au moins un appariement porte un numéro")
        print(f"      {forme_neq:>6}  … dont le numéro a la FORME d'un NEQ (10 chiffres)")
        print(f"      {sans:>6}  entreprise(s) appariées SANS aucun numéro")
        print("      ⚠️ Un numéro de forme juste n'est pas un numéro vérifié.")

        # Désaccords : deux sources, deux NEQ pour le même nom.
        desaccords = [
            (aid, {a["neq"] for a in lst if a["neq"]})
            for aid, lst in entreprises_appariees.items()
            if len({a["neq"] for a in lst if a["neq"]}) > 1
        ]
        print(f"\n   {len(desaccords)} entreprise(s) reçoivent DEUX numéros différents.")
        if desaccords:
            print("      ⚠️ Un désaccord entre répertoires n'est pas départageable ici.")

        # ---- les paires, par champ apparieur -------------------------------
        for label, _ in vent.most_common():
            cle_src, champ = label.split(" · ")
            lot = [a for a in appariements if a["source"] == cle_src and a["champ"] == champ]
            print("\n" + "-" * 78)
            print(f"{label}  —  {len(lot)} appariement(s); {min(args.exemples, len(lot))} montré(s)")
            print("-" * 78)
            for a in lot[: args.exemples]:
                c = a["company"]
                print(f"   détecté  : {(c.nom_detecte or '')[:64]}")
                print(f"   {champ:<9}: {a['brut'][:64]}")
                print(f"   numéro   : {a['neq'] or '—'}")
                print()

        print("=" * 78)
        print("CE QUE CE COMPTE NE DIT PAS")
        print("=" * 78)
        print("   • Il ne dit pas que les appariements sont JUSTES — deux entreprises")
        print("     peuvent porter la même raison sociale normalisée.")
        print("   • Il ne dit pas que le pont vaut pour le REQ entier. Il dit que la")
        print("     FORME du pont apparie, sur un gisement de quelques milliers de lignes.")
        print("   • Un recouvrement faible n'infirme pas la forme : ces trois répertoires")
        print("     couvrent des secteurs étroits, et l'EIMT fait 74,5 % du mur.")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
