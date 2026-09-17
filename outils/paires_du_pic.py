#!/usr/bin/env python3
"""Dix paires du pic 85-88, lues CÔTE À CÔTE. Brut, pas un compte.

**Pourquoi celle-là** *(Alexandre, 2026-09-17)*. **2 713 dossiers sur 4 733 ont
leur meilleur score dans une fenêtre de TROIS POINTS.**

> *Une distribution naturelle ne fait pas ça — c'est une différence systématique
> qui se répète et coûte toujours à peu près les mêmes points.* **Et personne ne
> l'a jamais regardée.**

**Une distribution dit COMBIEN; elle ne dit jamais QUOI.** Trois jours de
ventilations n'ont rien ouvert; *un cas entier a nommé le mur en une commande.*

## ⚠️ L'ÉCHANTILLON, ET POURQUOI IL N'EST PAS LES DIX PREMIERS

**Dix dossiers pris par `id` croissant, c'est le cas 19** — *le tri du fichier
promu au rang d'échantillon.* L'ordre des `id` est l'ordre d'arrivée des signaux,
donc l'ordre des fichiers sources : dix premiers, c'est dix dossiers de la même
source, du même trimestre, souvent du même secteur.

**La règle de tirage ici, énoncée pour pouvoir être contestée :**

1. tous les dossiers de la fenêtre sont **triés par score croissant**;
2. on prend des rangs **régulièrement espacés** sur toute la fenêtre — donc le
   bas, le milieu et le haut du pic;
3. deux dossiers ne peuvent pas partager le **même préfixe de récupération**
   *(sinon dix variantes de « gestion… » rempliraient la page)*;
4. à score égal, l'ordre est celui de l'`id` — **la seule part arbitraire, et
   elle est bornée aux ex æquo.**

`--premiers` rend les dix premiers par `id` **et le dit en toutes lettres** :
*un échantillon qui ne représente rien reste utile si personne ne croit qu'il
représente quelque chose.*

⚠️ **Aucune écriture, aucune règle modifiée** — seuil 92, écart 8. *Et aucune
classification : c'est une LECTURE, et classer à ta place la remplacerait par un
compte de plus.*

Usage, SUR L'HÔTE :
    sudo -u falkye bash -c 'set -a; . /etc/falkye/falkye.env; set +a; \
        cd /opt/falkye/code && \
        /opt/falkye/venv/bin/python -m outils.paires_du_pic'
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass

from outils.formes_registre import formes_publiees
from outils.nombres import milliers


@dataclass
class Paire:
    id: int
    nom_detecte: str
    nom_norm: str
    prefixe: str
    score: float
    neq: str
    nom_registre: str
    nom_registre_norm: str
    ville_registre: str | None
    ville_dossier: str | None
    second: float


def tirage_reparti(paires: list[Paire], combien: int) -> list[Paire]:
    """Des rangs régulièrement espacés sur la fenêtre, un préfixe par dossier.

    **Séparée de son appel pour être testable** : *une règle de tirage qui ne se
    vérifie que dans une sortie ne se vérifie pas.*
    """
    if not paires:
        return []
    ordonnees = sorted(paires, key=lambda p: (p.score, p.id))
    if combien >= len(ordonnees):
        return ordonnees
    pris: list[Paire] = []
    prefixes_vus: set[str] = set()
    pas = len(ordonnees) / combien
    for i in range(combien):
        depart = int(i * pas)
        # ⚠️ On AVANCE jusqu'au prochain préfixe neuf plutôt que de sauter le
        # rang : sauter rendrait moins de dix paires, avancer garde le compte et
        # ne déplace le rang que du minimum nécessaire.
        for j in range(depart, len(ordonnees)):
            candidat = ordonnees[j]
            if candidat.prefixe not in prefixes_vus:
                prefixes_vus.add(candidat.prefixe)
                pris.append(candidat)
                break
    return pris


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--fenetre", type=float, nargs=2, default=(85.0, 88.0),
                        metavar=("BAS", "HAUT"), help="la fenêtre de score (défaut 85 88)")
    parser.add_argument("--combien", type=int, default=10)
    parser.add_argument("--premiers", action="store_true",
                        help="les dix premiers par id — ⚠️ cas 19, ne représente rien")
    parser.add_argument("--limite", type=int, default=None, help="borner (mise au point)")
    args = parser.parse_args(argv)

    from sqlalchemy import select

    from falkye.db import refuser_si_cible_non_choisie

    code = refuser_si_cible_non_choisie()
    if code:
        return code

    from falkye.db import get_session
    from falkye.models.company import Company
    from falkye.resolution import SEUIL_RESOLUTION_CONFIANTE
    from falkye.sources import req as req_source
    from falkye.sources.column_mapping import normaliser

    bas, haut = args.fenetre
    print("=" * 78)
    print(f"LE PIC {bas:.0f}-{haut:.0f}, REGARDÉ — {args.combien} paires côte à côte")
    print("=" * 78)
    print(f"""
⚠️ CE QUE CETTE LECTURE NE DIRA PAS — à lire avant les paires

   {args.combien} dossiers ne sont pas une proportion. Ce qu'on y verra devra être
   RECOMPTÉ sur la population avant de valoir quoi que ce soit. *C'est la règle
   qui a suivi le cas (Workstaff) : un cas a nommé le mur, un chiffrage a dit
   qu'il pesait 205 dossiers sur 8 931.*

   Et l'outil ne CLASSE rien. Il n'invente pas de catégories de différence :
   c'est une lecture, et classer à ta place la remplacerait par un compte.

   ⚠️ Le lot de candidats est BORNÉ ({req_source.LIMITE_CANDIDATS_PAR_NOM}) et son
   ordre est alphabétique, pas pertinent. Un candidat meilleur peut exister hors
   du lot — c'est l'objet de `outils/saturation_de_la_borne.py`, pas d'ici.

   Aucune écriture, aucune règle modifiée — seuil {SEUIL_RESOLUTION_CONFIANTE:.0f}, écart 8.
""")

    session = get_session()
    try:
        requete = select(Company).where(Company.neq.is_(None)).order_by(Company.id)
        if args.limite:
            requete = requete.limit(args.limite)
        orphelins = list(session.execute(requete).scalars().all())

        paires: list[Paire] = []
        for i, company in enumerate(orphelins):
            if i and i % 1000 == 0:
                print(f"   … {milliers(i)} examinés", flush=True)
            matches = req_source.resolve_neq_by_name(
                session, company.nom_detecte, ville=company.ville
            )
            if not matches or not (bas <= matches[0].score < haut):
                continue
            nom_norm = normaliser(company.nom_detecte or "")
            top = matches[0]
            paires.append(Paire(
                id=company.id,
                nom_detecte=company.nom_detecte or "",
                nom_norm=nom_norm,
                prefixe=nom_norm.split(" ")[0] if nom_norm else "",
                score=top.score,
                neq=top.entry.neq,
                nom_registre=top.entry.nom or "",
                nom_registre_norm=top.entry.nom_normalise or "",
                ville_registre=top.entry.ville,
                ville_dossier=company.ville,
                second=matches[1].score if len(matches) > 1 else 0.0,
            ))

        print(f"\n   dossiers dans la fenêtre [{bas:.0f} – {haut:.0f}[ : "
              f"{milliers(len(paires))}\n")
        if args.premiers:
            choisies = sorted(paires, key=lambda p: p.id)[: args.combien]
            print("   ⚠️ TIRAGE : LES PREMIERS PAR `id`. **Cet échantillon ne représente")
            print("      RIEN** — l'ordre des `id` est l'ordre d'arrivée des signaux, donc")
            print("      celui des fichiers sources. C'est le cas 19, assumé et nommé.")
        else:
            choisies = tirage_reparti(paires, args.combien)
            print("   TIRAGE : rangs régulièrement espacés sur la fenêtre triée par")
            print("   score, un préfixe de récupération par dossier. *Le bas, le milieu")
            print("   et le haut du pic sont représentés; dix variantes du même préfixe")
            print("   ne peuvent pas remplir la page.*")

        for n, p in enumerate(choisies, 1):
            print("\n" + "─" * 78)
            print(f"{n:>2}. score {p.score:>6.2f}    (2e : {p.second:>6.2f})    "
                  f"il manque {SEUIL_RESOLUTION_CONFIANTE - p.score:>5.2f} point(s)")
            print(f"    détecté  : {p.nom_detecte!r}")
            print(f"    registre : {p.nom_registre!r}   [{p.neq}]")
            print(f"    ville    : dossier={p.ville_dossier!r}   registre={p.ville_registre!r}")
            print(f"    comparé  : {p.nom_norm!r}")
            print(f"               {p.nom_registre_norm!r}")
            autres = [
                (nom, table) for _, nom, table in formes_publiees(session, [p.neq])
                if nom != p.nom_registre
            ]
            if autres:
                print("    autres noms de ce NEQ :")
                for nom, table in autres[:4]:
                    print(f"       {nom[:52]!r:<56} {table}")

        print("\n" + "=" * 78)
        print("   Ce qui se répète ici doit être RECOMPTÉ sur la population avant")
        print("   de devenir un chantier. Une lecture ouvre; elle ne conclut pas.")
        print("=" * 78)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
