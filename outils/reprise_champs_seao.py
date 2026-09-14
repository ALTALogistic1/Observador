"""Compléter les `champs` des signaux SEAO déjà en base, depuis les fichiers source.

**Pourquoi cet outil existe.** Le connecteur SEAO a commencé le 2026-09-13 à capter
la classification normalisée, l'identifiant du donneur d'ouvrage, l'adresse du
fournisseur et la description des besoins. **Mais `champs` s'écrit à l'ingestion, et
la déduplication par `source_ref` fait qu'un avis déjà vu ne repasse jamais** — les
signaux antérieurs resteraient donc sans ces champs, pour toujours. *« Un produit qui
distingue les signaux futurs et pas les anciens serait à moitié calibré »* — décision
d'Alexandre, 2026-09-14, sur 2 280 signaux SEAO en base.

**Ce qu'il fait, exactement.** Il relit les fichiers SEAO **à la source** (Données
Québec), recalcule pour chaque attribution **la clé du moteur** — `source_ref_pour`,
empruntée et non recopiée — et complète les `champs` du signal correspondant.

**Ce qu'il ne fait jamais.**

*Il n'écrase aucune valeur existante.* Une clé déjà remplie est laissée telle quelle :
l'outil ne sait pas si elle vient du connecteur ou d'une correction à la main, et
**une reprise qui écrase n'est plus une reprise**.

*Il ne crée aucun signal.* Une attribution du fichier sans signal en base est
COMPTÉE et passée — elle veut dire que le cycle ne l'avait pas retenue *(hors
fenêtre, filtre territorial, nom vide)*, et en faire un signal ici contournerait la
détection au lieu de la compléter.

*Il ne devine aucune période.* La fenêtre de fichiers à relire est déduite des dates
des signaux EN BASE, puis élargie d'une marge, parce qu'un avis peut avoir été publié
dans un fichier voisin de sa date d'attribution.

**Les écritures sont BORNÉES EN TEMPS, pas seulement en nombre** : la base distante
annule une transaction portant une écriture non validée après moins de dix secondes
d'inactivité *(mesuré le 2026-09-07, docs/DEPLOIEMENT.md)*. D'où les lots.

    python outils/reprise_champs_seao.py                 # compte, n'écrit rien
    python outils/reprise_champs_seao.py --appliquer

Sur l'hôte, l'environnement d'abord :

    set -a; . /etc/falkye/falkye.env; set +a
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import timedelta

#: Même raison que `outils/purge_hors_territoire.py` : un lot de quelques centaines
#: tient largement dans la fenêtre de dix secondes; un `UPDATE` unique sur des
#: milliers de lignes ne la tiendrait pas.
TAILLE_LOT = 300

#: La marge autour de la période des signaux. Un avis attribué le 30 du mois peut
#: n'apparaître que dans le fichier de la semaine suivante — relire trop de fichiers
#: coûte du temps, en relire trop peu laisse des signaux incomplets en silence.
MARGE_JOURS = 21


def periode_des_signaux(db_session) -> tuple:
    """(plus ancienne, plus récente) date d'attribution des signaux SEAO en base."""
    from sqlalchemy import func, select

    from falkye.models.signal import Signal

    return db_session.execute(
        select(func.min(Signal.detected_at), func.max(Signal.detected_at)).where(
            Signal.source_id == "seao"
        )
    ).one()


def ressources_couvrantes(client, debut, fin) -> list[dict]:
    """Les fichiers SEAO dont la plage de dates croise la période demandée.

    Le nom porte la plage (`hebdo_YYYYMMDD_YYYYMMDD.json`). Un fichier au nom non
    daté est RETENU par prudence — l'écarter perdrait des signaux sans le dire.
    """
    from falkye.sources.seao import SEAO_PACKAGE_ID, _FILENAME_DATE_RANGE

    retenues = []
    for resource in client.resources(SEAO_PACKAGE_ID, format_filter="JSON"):
        match = _FILENAME_DATE_RANGE.search(resource.get("name", "") or resource.get("url", ""))
        if not match:
            retenues.append(resource)
            continue
        d, f = match.groups()
        if d <= fin.strftime("%Y%m%d") and f >= debut.strftime("%Y%m%d"):
            retenues.append(resource)
    return retenues


def champs_du_fichier(chemin) -> dict[str, dict]:
    """{source_ref : champs} pour toutes les attributions d'un fichier.

    Les champs sont produits par les fonctions du connecteur — jamais réécrits ici,
    sans quoi la reprise remplirait autre chose que ce que l'ingestion remplit.
    """
    from falkye.sources.seao import (
        _buyer_name,
        _classifications,
        _descriptions_besoins,
        _extraire_awards,
        _partie_du_fournisseur,
        source_ref_pour,
    )

    with open(chemin, encoding="utf-8") as f:
        data = json.load(f)

    par_ref: dict[str, dict] = {}
    for release, award in _extraire_awards(data):
        for supplier in award.get("suppliers", []) or []:
            adresse = _partie_du_fournisseur(release, supplier).get("address") or {}
            par_ref[source_ref_pour(release, award)] = {
                "donneur_ordre_id": (release.get("buyer") or {}).get("id"),
                "secteur_nature_contrat": _classifications(release),
                "adresse_entreprise_adjudicataire": {
                    "adresse": adresse.get("streetAddress"),
                    "ville": adresse.get("locality"),
                    "region": adresse.get("region"),
                    "code_postal": adresse.get("postalCode"),
                }
                if adresse
                else None,
                "description_besoins": _descriptions_besoins(release),
                "donneur_ordre": _buyer_name(release),
            }
    return par_ref


def completer(signal, neufs: dict) -> bool:
    """Ajoute les clés ABSENTES. Rend True si le signal a changé.

    Une clé déjà présente et non vide est laissée : l'outil ne sait pas d'où elle
    vient, et une reprise qui écrase n'est plus une reprise.
    """
    champs = dict(signal.champs or {})
    change = False
    for cle, valeur in neufs.items():
        if valeur in (None, [], {}):
            continue
        if champs.get(cle) in (None, "", [], {}):
            champs[cle] = valeur
            change = True
    if change:
        signal.champs = champs  # réassignation : SQLAlchemy ne voit pas une mutation en place
    return change


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--appliquer", action="store_true", help="écrire (défaut : compter)")
    args = parseur.parse_args(argv)

    from falkye.db import bases_sur_repli, cible_annoncee

    print(cible_annoncee())
    if bases_sur_repli():
        print(
            "\nREFUS — aucune cible n'a été choisie : "
            f"{', '.join(bases_sur_repli())} absente(s).\n"
            "  « Aucun signal à compléter » sur une base vide se lit comme un travail fait.\n"
            "  Sur l'hôte : set -a; . /etc/falkye/falkye.env; set +a",
            file=sys.stderr,
        )
        return 2

    from sqlalchemy import select

    from falkye.db import get_session
    from falkye.models.signal import Signal
    from falkye.sources.ckan_client import DONNEES_QUEBEC_BASE, CKANClient

    session = get_session()
    try:
        debut, fin = periode_des_signaux(session)
        if debut is None:
            print("\nAucun signal SEAO en base — rien à reprendre, et ce n'est pas un succès.")
            return 0
        debut, fin = debut - timedelta(days=MARGE_JOURS), fin + timedelta(days=MARGE_JOURS)
        print(f"\nsignaux SEAO datés du {debut:%Y-%m-%d} au {fin:%Y-%m-%d} (marge comprise)")

        client = CKANClient(DONNEES_QUEBEC_BASE)
        ressources = ressources_couvrantes(client, debut, fin)
        print(f"fichiers source à relire : {len(ressources)}")

        champs_par_ref: dict[str, dict] = {}
        for resource in ressources:
            chemin = client.download(resource)
            trouves = champs_du_fichier(chemin)
            champs_par_ref.update(trouves)
            print(f"   {str(resource.get('name'))[:44]:46} {len(trouves):>6} attribution(s)")

        compte = Counter()
        a_ecrire = []
        signaux = session.execute(
            select(Signal).where(Signal.source_id == "seao")
        ).scalars().all()
        print(f"\nsignaux SEAO en base : {len(signaux)}")

        refs_en_base = {s.source_ref for s in signaux}
        for signal in signaux:
            neufs = champs_par_ref.get(signal.source_ref)
            if neufs is None:
                compte["introuvable dans les fichiers relus"] += 1
                continue
            if completer(signal, neufs):
                compte["à compléter"] += 1
                a_ecrire.append(signal)
            else:
                compte["déjà complet"] += 1
        compte["attributions sans signal en base"] = len(
            set(champs_par_ref) - refs_en_base
        )

        print()
        for libelle, n in compte.most_common():
            print(f"   {libelle:44} {n:>6}")

        if not args.appliquer:
            session.rollback()  # les objets ont été modifiés en mémoire : rien ne part
            print("\n(lecture seule — relancer avec --appliquer pour écrire)")
            return 0

        for i in range(0, len(a_ecrire), TAILLE_LOT):
            session.commit() if i else None
            lot = a_ecrire[i : i + TAILLE_LOT]
            session.add_all(lot)
            session.commit()
            print(f"   lot de {len(lot)} écrit")
        print(f"\n{len(a_ecrire)} signal(aux) complété(s).")
        print(
            "  ⚠ Ce que ça ne fait PAS : créer un signal. Une attribution sans signal en\n"
            "    base veut dire que le cycle ne l'avait pas retenue — hors fenêtre, filtre\n"
            "    territorial, nom vide. En faire un signal ici contournerait la détection."
        )
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
