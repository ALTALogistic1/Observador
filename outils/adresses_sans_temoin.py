#!/usr/bin/env python3
"""Les adresses du registre des sources **qu'aucun mécanisme n'appelle** — donc
qui vieillissent sans témoin.

**Le fait qui justifie cet outil** *(Alexandre, 2026-09-16)*. Le `lien_recherche`
du REQ pointait sur `donneesquebec.ca/.../download/jeudonneesouvertes.zip`, qui
rend **404**. *Personne ne l'a su parce que personne ne l'utilisait* : `req` est
une source `import_manuel`, donc son adresse n'est lue par aucun connecteur.

**La forme du défaut, et pourquoi elle est générale.** Une adresse appelée à
chaque cycle est éprouvée à chaque cycle : le jour où elle meurt, la source
tombe en erreur et `SourceRunLog` le dit. **Une adresse que seul un humain ouvre,
toutes les deux semaines, n'est éprouvée que ce jour-là** — et entre deux, rien
ne la distingue d'une adresse vivante. *Même forme que l'adresse de l'EIMT.*

⚠️ **Ce que « sans témoin » veut dire ICI, précisément** : l'adresse n'apparaît
**littéralement dans aucun fichier `.py` du paquet**. *Un connecteur qui
construit son adresse par morceaux — un domaine d'un côté, un chemin de l'autre —
compte comme sans témoin alors qu'il l'appelle peut-être.* **La mesure
sur-estime donc le nombre, et c'est le bon sens du biais** : elle signale des
adresses à vérifier, elle n'en absout aucune.

**Ce que l'outil ne fait pas.** Il ne corrige aucune adresse et n'en propose
aucune. *Une adresse morte remplacée automatiquement par une adresse devinée
serait pire que l'adresse morte* — celle-là au moins échoue franchement.

Usage :
    python3 outils/adresses_sans_temoin.py
    python3 outils/adresses_sans_temoin.py --sonder      # appelle chaque adresse
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

#: Une adresse HTTP dans n'importe quel champ du registre, y compris au milieu
#: d'une note en prose. La ponctuation française collée en fin de phrase est
#: retirée — sinon `…aspx.` serait sondée telle quelle et rendrait un faux 404.
MOTIF_URL = re.compile(r"https?://[^\s\"'<>)\]]+")
PONCTUATION_FINALE = ".,;:!?»"


def urls_dune_valeur(valeur) -> list[str]:
    """Toutes les adresses portées par une valeur du registre, quelle qu'en soit
    la forme — chaîne, liste, dictionnaire, prose. **Une adresse enterrée dans
    une note compte autant qu'un `lien_recherche`** : elle sera lue par un humain
    exactement pareil."""
    trouvees: list[str] = []
    if isinstance(valeur, str):
        for brute in MOTIF_URL.findall(valeur):
            trouvees.append(brute.rstrip(PONCTUATION_FINALE))
    elif isinstance(valeur, dict):
        for v in valeur.values():
            trouvees.extend(urls_dune_valeur(v))
    elif isinstance(valeur, (list, tuple, set)):
        for v in valeur:
            trouvees.extend(urls_dune_valeur(v))
    return trouvees


def est_citee_dans_le_code(url: str, sources_py: dict[str, str]) -> list[str]:
    """Les fichiers `.py` qui citent cette adresse LITTÉRALEMENT.

    *Une correspondance littérale, pas une heuristique de domaine* : deux sources
    du même portail partagent un domaine sans partager une adresse, et compter
    l'une pour l'autre rendrait la mesure fausse dans le sens rassurant.
    """
    return sorted(f for f, texte in sources_py.items() if url in texte)


def sonder(url: str, delai: float):
    """Une requête de TÊTE, avec repli sur GET.

    ⚠️ **Le repli n'est pas une commodité** : beaucoup de serveurs refusent
    `HEAD` par 405, 403 ou 501 tout en servant `GET` normalement. *Sans le repli,
    on déclarerait mortes des adresses vivantes* — et une garde qui crie à tort
    est retirée au premier agacement.
    """
    import urllib.error
    import urllib.request

    for methode in ("HEAD", "GET"):
        requete = urllib.request.Request(url, method=methode)
        try:
            with urllib.request.urlopen(requete, timeout=delai) as reponse:
                return reponse.status, f"{methode} · {reponse.headers.get('Content-Type', '')}"
        except urllib.error.HTTPError as exc:
            if methode == "HEAD" and exc.code in (403, 405, 501):
                continue  # le serveur refuse la MÉTHODE, pas l'adresse
            return exc.code, f"{methode} · {exc.reason}"
        except Exception as exc:  # noqa: BLE001 - un réseau qui tombe n'est pas un verdict
            return "ERR", f"{methode} · {type(exc).__name__}"
    return "ERR", "aucune méthode n'a abouti"


def classer(source, url: str, citations: list[str]) -> str:
    """Le verdict, et il tient à UNE question : quelque chose d'automatique
    appelle-t-il cette adresse?"""
    if citations:
        return "citée par le code"
    if getattr(source, "est_import_manuel", False):
        return "SANS TÉMOIN — source en import manuel"
    if not getattr(source, "est_actif", True):
        return "SANS TÉMOIN — source inactive"
    return "SANS TÉMOIN — connecteur actif, adresse non citée"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--sonder", action="store_true",
                        help="appeler chaque adresse et rapporter son code (sortant — le dire)")
    parser.add_argument("--delai", type=float, default=30.0, help="délai par appel, en secondes")
    args = parser.parse_args(argv)

    try:
        from falkye.registry.loader import get_registry
    except ImportError as exc:  # pragma: no cover - dépend de l'environnement
        print(f"Import impossible ({exc}). Lancer depuis la racine du dépôt.", file=sys.stderr)
        return 2

    sources_py = {
        str(f): f.read_text(encoding="utf-8", errors="replace")
        for f in sorted(Path("falkye").rglob("*.py"))
    }

    registre = get_registry().sources

    print("=" * 78)
    print("LES ADRESSES DU REGISTRE, ET CE QUI LES ÉPROUVE")
    print("=" * 78)
    print("\nPORTÉE : « sans témoin » = l'adresse n'apparaît LITTÉRALEMENT dans aucun")
    print("         .py du paquet. Une adresse construite par morceaux compte comme")
    print("         sans témoin à tort — la mesure sur-estime, et c'est le bon biais.")

    lignes: list[tuple] = []
    for source in registre.values():
        vues: set[str] = set()
        for champ in ("lien_recherche", "notes", "regle_calibration", "nom"):
            for url in urls_dune_valeur(getattr(source, champ, None)):
                if url in vues:
                    continue
                vues.add(url)
                citations = est_citee_dans_le_code(url, sources_py)
                lignes.append((source, champ, url, citations, classer(source, url, citations)))

    sans_temoin = [l for l in lignes if l[4].startswith("SANS TÉMOIN")]

    ids_avec_adresse = {l[0].id for l in lignes}
    sans_aucune_adresse = sorted(set(registre) - ids_avec_adresse)

    print(f"\n   sources au registre               : {len(registre)}")
    # Le fait le plus lourd n'est pas le nombre d'adresses mortes : c'est le
    # nombre de sources qui n'en portent AUCUNE. L'endroit où l'on cherche une
    # adresse d'accès est vide pour elles, et rien ne le signale.
    print(f"   sources SANS AUCUNE adresse       : {len(sans_aucune_adresse)}"
          "   ← le registre ne peut rien éprouver là")
    print(f"   adresses distinctes trouvées      : {len(lignes)}")
    print(f"   adresses SANS TÉMOIN              : {len(sans_temoin)}")
    if lignes:
        print(f"   adresses citées par le code       : {len(lignes) - len(sans_temoin)}")

    from collections import Counter

    print("\n   par motif :")
    for motif, n in Counter(l[4] for l in lignes).most_common():
        print(f"      {n:>4}  {motif}")

    print("\n" + "-" * 78)
    print("LE DÉTAIL — ce qu'un humain ouvre, et que rien ne vérifie entre deux fois")
    print("-" * 78)
    for source, champ, url, citations, motif in sorted(lignes, key=lambda l: (l[4], l[0].id)):
        marque = "⛔" if motif.startswith("SANS TÉMOIN") else "  "
        print(f"\n   {marque} {source.id}  ·  {champ}  ·  {motif}")
        print(f"      {url}")
        if citations:
            print(f"      citée par : {', '.join(citations)}")

    if args.sonder:
        import urllib.error
        import urllib.request

        print("\n" + "-" * 78)
        print("LA SONDE — chaque adresse appelée UNE fois")
        print("-" * 78)
        print("   ⚠️ Appel SORTANT vers des sites publics. Un 403 depuis cet")
        print("      environnement ne prouve pas qu'un navigateur serait refusé —")
        print("      c'est exactement le cas du REQ (règle Cloudflare sur les")
        print("      plages infonuagiques, documenté depuis le 2026-08-31).")
        morts = 0
        for source, champ, url, _citations, motif in sorted(lignes, key=lambda l: l[0].id):
            code, detail = sonder(url, args.delai)
            mort = code == 404
            morts += mort
            print(f"\n   {code}  {source.id} · {champ}{'   ⛔ MORTE' if mort else ''}")
            print(f"        {url}")
            print(f"        {detail}")
        print(f"\n   {morts} adresse(s) rendent 404.")
        print("   ⚠️ Un 404 est un verdict; un 403 ou une erreur réseau n'en est pas un.")

    if sans_aucune_adresse:
        print("\n" + "-" * 78)
        print("LES SOURCES QUI NE PORTENT AUCUNE ADRESSE")
        print("-" * 78)
        print("\n   " + ", ".join(sans_aucune_adresse))
        print("\n   ⚠️ Ce n'est pas un défaut de code : rien ne CASSE. C'est que le")
        print("      registre ne peut rien éprouver pour elles, et qu'un humain qui")
        print("      cherche par où l'on accède à ces sources ne trouve rien là où")
        print("      il regarde. Une absence de mesure, pas une mesure nulle.")

    print("\n" + "=" * 78)
    print("   Aucune adresse n'a été corrigée. Une adresse morte remplacée par une")
    print("   adresse devinée serait pire que l'adresse morte — celle-là échoue franchement.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
