"""La TROISIÈME colonne de l'inventaire : ce que la source porte et que personne ne demande.

**Ce qui manquait.** `outils/inventaire_champs.py` dit ce que le code CAPTE et ce qui
est REMPLI en base. **Il ne dit pas ce que la source PORTE.** Or c'est là que se cache
ce qu'on laisse sur la table : *la classification du SEAO était présente depuis
toujours, portée par l'item, et personne ne la lisait — 93,6 % des avis.*

**Ce que la sonde a déjà trouvé, sur une seule source** *(2026-09-14,
`subventions_federales`, 500 enregistrements québécois réels)* : **39 champs portés,
13 lus**. Parmi les non lus — `recipient_type` **rempli à 100 %, sept valeurs
normalisées**, qui est la matière de **D28**; un identifiant fédéral *(D29)*; un code
postal à 96,8 % alors que **l'adresse est une exigence de sortie**; et le nom d'USAGE
à côté du nom légal, *donc un second nom à apparier*.

**Et une honnêteté qui justifie la colonne à elle seule** : `naics_identifier`, le code
sectoriel normalisé qu'on espérerait, **n'est rempli qu'à 10 %**. *Une colonne
« déclaré » sans « rempli » l'aurait fait passer pour disponible.*

**⚠️ Ce que la sonde ne peut PAS faire, et qui doit apparaître dans la SORTIE.** Une
source GRATTÉE ne rend pas une liste de champs : une page web n'a pas de schéma, et ce
qu'on en tire est ce que le connecteur a su extraire. **Pour celles-là la troisième
colonne est vide PAR NATURE, et la sortie le dit** — plutôt que de laisser croire qu'on
a regardé et qu'il n'y avait rien. *Même forme que « déclaré, non ingéré » contre un
0 % : une absence de mesure n'est pas une mesure nulle.*

**Ce que « lu par le connecteur » veut dire ici** : les clés littérales qui apparaissent
dans un `.get("…")` du module, lues dans l'arbre syntaxique. *C'est une approximation
mécanique — un connecteur qui construirait un nom de champ dynamiquement passerait pour
ne pas le lire.* **Dit ici plutôt que supposé juste.**

    python outils/sonde_source.py                      # toutes les sources sondables
    python outils/sonde_source.py --source seao

Aucune écriture, aucune lecture de la base du produit : la sonde interroge les SOURCES.
"""
from __future__ import annotations

import argparse
import ast
import pathlib
import sys
from collections import Counter

RACINE = pathlib.Path(__file__).resolve().parents[1]
TAILLE_ECHANTILLON = 500

#: Pourquoi une source n'est pas sondable — écrit une fois, affiché tel quel.
PAS_DE_SCHEMA = (
    "source GRATTÉE : une page web n'a pas de liste de champs à interroger. "
    "La troisième colonne est vide PAR NATURE, pas par manque de mesure."
)
PDF = (
    "source PDF : les champs sont des colonnes d'un tableau mis en page, pas un "
    "schéma. Une sonde rendrait la lecture du connecteur, pas celle de la source."
)


def cles_lues(module: str) -> set[str]:
    """Les clés littérales que le connecteur demande — `.get("…")`, lu dans l'arbre.

    Approximation mécanique assumée : un nom de champ construit dynamiquement
    passerait pour non lu. L'inverse — inventer qu'un champ est lu — serait pire.
    """
    chemin = RACINE / (module.replace(".", "/") + ".py")
    if not chemin.exists():
        return set()
    arbre = ast.parse(chemin.read_text(encoding="utf-8"))
    lues = set()
    for noeud in ast.walk(arbre):
        if (
            isinstance(noeud, ast.Call)
            and isinstance(noeud.func, ast.Attribute)
            and noeud.func.attr == "get"
            and noeud.args
            and isinstance(noeud.args[0], ast.Constant)
            and isinstance(noeud.args[0].value, str)
        ):
            lues.add(noeud.args[0].value)
    return lues


# --- Les sondes, une par mode d'accès ---------------------------------------


def _sonde_datastore(package_id: str, nom_ressource: str, filtres: dict | None = None):
    """Sources interrogées par l'API Datastore CKAN (subventions, contrats)."""

    def sonder():
        from falkye.sources.ckan_client import OPEN_CANADA_BASE, CKANClient

        client = CKANClient(OPEN_CANADA_BASE)
        for resource in client.resources(package_id, format_filter="CSV"):
            if resource.get("name") == nom_ressource and resource.get("datastore_active"):
                # **`_id desc` — les plus RÉCEMMENT PUBLIÉS, pas les premiers venus.**
                # Sans tri, le datastore rend les plus anciens (`_id` croissant) :
                # mesuré le 2026-09-14, l'échantillon par défaut des subventions
                # fédérales portait **29 champs remplis, contre 39 sur les récents**
                # — `recipient_type`, `naics_identifier` et le numéro d'entreprise
                # n'existaient pas dans les vieilles lignes. *Une sonde qui échantillonne
                # le passé sous-estime ce que la source porte AUJOURD'HUI, et rien dans
                # sa sortie ne le dirait.*
                resultat = client.datastore_search(
                    resource["id"], filters=filtres, limit=TAILLE_ECHANTILLON, sort="_id desc"
                )
                return (
                    resultat.get("records", []),
                    f"datastore CKAN · {nom_ressource} · les plus récemment publiés",
                )
        return None, f"ressource {nom_ressource!r} introuvable ou non indexée"

    return sonder


def _sonde_json_ckan(package_id: str, base: str):
    """Sources lues comme fichier JSON sur un portail CKAN (SEAO)."""

    def sonder():
        import json

        from falkye.sources.ckan_client import CKANClient

        client = CKANClient(base)
        resources = client.resources(package_id, format_filter="JSON")
        if not resources:
            return None, "aucune ressource JSON au paquet"
        resource = sorted(
            resources, key=lambda r: r.get("last_modified") or "", reverse=True
        )[0]
        with open(client.download(resource), encoding="utf-8") as f:
            data = json.load(f)
        releases = data["releases"] if isinstance(data, dict) and "releases" in data else data
        # Un avis OCDS est imbriqué : on aplatit d'un cran pour que les champs de
        # `tender`, d'un `award` et d'une `partie` soient visibles comme des champs.
        plats = []
        for release in releases[:TAILLE_ECHANTILLON]:
            plat = {c: v for c, v in release.items() if not isinstance(v, (dict, list))}
            for prefixe, sous in (("tender", release.get("tender") or {}),):
                plat.update({f"{prefixe}.{c}": v for c, v in sous.items()})
            for award in (release.get("awards") or [])[:1]:
                plat.update({f"awards.{c}": v for c, v in award.items()})
            for partie in (release.get("parties") or [])[:1]:
                plat.update({f"parties.{c}": v for c, v in partie.items()})
            plats.append(plat)
        return plats, f"fichier JSON · {resource.get('name')}"

    return sonder


def _sonde_tableur_ckan(package_id: str, base: str, formats=("CSV",)):
    """Sources lues comme tableur sur un portail CKAN (Laval, EIMT)."""

    def sonder():
        import csv
        import io

        from falkye.sources.ckan_client import CKANClient

        client = CKANClient(base)
        resources = []
        for fmt in formats:
            resources = client.resources(package_id, format_filter=fmt)
            if resources:
                break
        if not resources:
            return None, f"aucune ressource {'/'.join(formats)} au paquet"
        resource = resources[0]
        chemin = client.download(resource)
        if not str(chemin).lower().endswith(".csv"):
            return None, f"ressource non CSV ({chemin.suffix}) — sonde tableur non branchée"
        with open(chemin, encoding="utf-8-sig", errors="replace") as f:
            lecteur = csv.DictReader(f)
            lignes = [l for _, l in zip(range(TAILLE_ECHANTILLON), lecteur)]
        return lignes, f"fichier CSV · {resource.get('name')}"

    return sonder


#: Une sonde par source, ou la RAISON de son absence. *Le dictionnaire est la seule
#: liste écrite à la main de cet outil, et elle est vérifiée contre le registre : une
#: source active qui n'y figure pas est signalée plutôt que passée sous silence.*
SONDES = {
    "seao": _sonde_json_ckan(
        "systeme-electronique-dappel-doffres-seao", "https://www.donneesquebec.ca/recherche"
    ),
    "subventions_federales": _sonde_datastore(
        "432527ab-7aac-45b5-81d6-7597107a7013",
        "Proactive Disclosure - Grants and Contributions",
        {"recipient_province": "QC"},
    ),
    "contrats_federaux": _sonde_datastore(
        "d8f85d91-7dec-4fd1-8055-483b77225d8b", "Contracts over $10,000"
    ),
    "permis_construction_laval": _sonde_tableur_ckan(
        "permis-de-construction", "https://www.donneesquebec.ca/recherche"
    ),
    "eimt": _sonde_tableur_ckan(
        "90fed587-1364-4f33-a9ee-208181dc0b97",
        "https://open.canada.ca/data",
        formats=("CSV", "XLSX"),
    ),
    "investissement_quebec": PDF,
    "req": (
        "archive de six CSV liés : la sonde par plages HTTP existe (elle a lu les "
        "en-têtes le 2026-09-14) mais n'est pas branchée ici — voir la réponse du jour."
    ),
    "deloitte_fast50": PAS_DE_SCHEMA,
    "rob_top_growing": PAS_DE_SCHEMA,
}


def sonder_source(source_id: str, module: str) -> dict:
    sonde = SONDES.get(source_id)
    if sonde is None:
        return {"impossible": "aucune sonde déclarée pour cette source"}
    if isinstance(sonde, str):
        return {"impossible": sonde}
    try:
        records, provenance = sonde()
    except Exception as exc:  # noqa: BLE001 -- une sonde qui tombe ne tue pas le relevé
        return {"impossible": f"sonde en échec : {exc}"}
    if not records:
        return {"impossible": provenance}

    remplis: Counter = Counter()
    distinctes: dict[str, set] = {}
    for rec in records:
        for cle, valeur in rec.items():
            if valeur in (None, "", [], {}) or str(cle).startswith("_"):
                continue
            remplis[cle] += 1
            distinctes.setdefault(cle, set()).add(str(valeur)[:80])

    lues = cles_lues(module)
    return {
        "provenance": provenance,
        "echantillon": len(records),
        "champs": {
            cle: {
                "taux": 100 * n / len(records),
                "distinctes": len(distinctes[cle]),
                "lu": cle in lues or cle.split(".")[-1] in lues,
            }
            for cle, n in remplis.most_common()
        },
    }


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--source", action="append", default=[], help="limiter à ces sources")
    parseur.add_argument(
        "--seuil", type=float, default=0.0,
        help="ne montrer les champs NON LUS qu'au-dessus de ce taux de remplissage",
    )
    args = parseur.parse_args(argv)

    from falkye.registry.loader import get_registry

    registry = get_registry()
    sources = [s for s in registry.sources_actives() if s.connecteur]
    if args.source:
        sources = [s for s in sources if s.id in args.source]

    sans_sonde = [s.id for s in sources if s.id not in SONDES]
    if sans_sonde:
        print(f"⚠ sources actives sans sonde déclarée : {', '.join(sans_sonde)}\n")

    for source in sources:
        print(f"\n── {source.id} " + "─" * max(0, 58 - len(source.id)))
        releve = sonder_source(source.id, source.connecteur)
        if "impossible" in releve:
            print(f"   ⊘ {releve['impossible']}")
            continue
        champs = releve["champs"]
        non_lus = [c for c, i in champs.items() if not i["lu"] and i["taux"] >= args.seuil]
        print(
            f"   {releve['provenance']} · échantillon de {releve['echantillon']}\n"
            f"   {len(champs)} champ(s) rempli(s) à la source, "
            f"{sum(1 for i in champs.values() if i['lu'])} lu(s) par le connecteur"
        )
        if not non_lus:
            print("   tout ce que la source remplit est lu.")
            continue
        print(f"\n   {'NON LU':<34}{'rempli':>8}{'distinct':>10}")
        for cle in non_lus:
            info = champs[cle]
            print(f"   {cle:<34}{info['taux']:7.1f}%{info['distinctes']:10}")

    print(
        "\n" + "─" * 64 + "\n"
        "⚠ « ⊘ » n'est pas « rien à prendre » : c'est une source qu'on ne PEUT pas\n"
        "  interroger — grattée, en PDF, ou sans sonde branchée. La troisième colonne y\n"
        "  est vide par nature, et une absence de mesure n'est pas une mesure nulle.\n\n"
        "  Et « lu » signifie : la clé apparaît littéralement dans un `.get()` du\n"
        "  connecteur. Un champ construit dynamiquement passerait pour non lu."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
