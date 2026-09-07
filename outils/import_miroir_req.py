"""Charger le miroir REQ — avec les garde-fous que l'hôte exige.

**Pourquoi ce script plutôt que `falkye import-manuel fichier` directement.**
L'import lui-même est déjà écrit. Ce qui manque quand il tourne sur le serveur,
sans personne devant l'écran, ce sont trois choses :

1. *Un refus explicite plutôt qu'un défaut silencieux.* Sans
   `FALKYE_MIROIR_DB_URL`, la valeur par défaut est le chemin RELATIF
   `./data/miroirs.sqlite3` — qui, sous systemd, se résout dans le répertoire de
   travail de l'unité, hors des chemins que `ProtectSystem=strict` autorise en
   écriture. L'erreur qui en sortirait parlerait de permissions, pas de la
   variable manquante, et on chercherait au mauvais endroit.

2. *Un refus de viser la base distante.* C'est LE garde-fou de ce script. Y
   pointer le miroir ferait un import de ~168 heures au lieu de 33 minutes et
   consommerait 2,7 millions d'écritures facturées — sans aucune erreur, juste
   de la lenteur, découverte des heures plus tard.

3. *Les deux chiffres qu'on n'a mesurés qu'en développement* : la durée réelle
   et le pic mémoire. Le pic mesuré était de 3 535 Mo pour 8 Go de serveur; c'est
   la première fois que l'import s'exécute là, et c'est la marge qu'il faut voir.

Le rapport part sur la sortie standard, donc dans le journal du service.

    python outils/import_miroir_req.py --chemin /opt/falkye/import/JeuDonnees.zip \\
                                       [--empreinte-attendue <sha256>]
"""
from __future__ import annotations

import argparse
import hashlib
import os
import resource
import sys
import time
from pathlib import Path


class ImportImpossible(SystemExit):
    """Sortie en erreur AVANT d'avoir touché quoi que ce soit."""

    def __init__(self, message: str):
        super().__init__(f"REFUS — {message}")


def verifier_cible() -> str:
    """La cible des miroirs doit être un fichier local, et l'être explicitement."""
    url = os.environ.get("FALKYE_MIROIR_DB_URL", "").strip()
    if not url:
        raise ImportImpossible(
            "FALKYE_MIROIR_DB_URL n'est pas définie. Sans elle, le miroir "
            "s'écrirait dans le chemin relatif ./data/miroirs.sqlite3, hors des "
            "répertoires que l'unité systemd peut écrire. Poser dans "
            "/etc/falkye/falkye.env :\n"
            "    FALKYE_MIROIR_DB_URL=sqlite:////var/lib/falkye/miroirs.sqlite3"
        )
    if not url.startswith("sqlite:"):
        raise ImportImpossible(
            f"FALKYE_MIROIR_DB_URL vaut {url!r}, qui n'est pas un fichier local. "
            "Le miroir ne va JAMAIS dans la base distante : l'import y prendrait "
            "environ 168 heures au lieu de 33 minutes (2 allers-retours par "
            "ligne à 111 ms, mesuré le 2026-09-06) et consommerait 2,7 millions "
            "d'écritures facturées. Voir docs/MIROIRS.md."
        )
    return url


def verifier_archive(chemin: Path, empreinte_attendue: str | None) -> str:
    """Retourne l'empreinte SHA-256 de l'archive.

    L'empreinte protège d'un transfert tronqué ou corrompu, PAS d'une archive
    hostile : sur ce chemin, la chaîne de déploiement fournit à la fois le
    fichier et l'empreinte attendue. Le dire plutôt que de laisser croire à une
    garantie qu'elle n'apporte pas.
    """
    if not chemin.is_file():
        raise ImportImpossible(f"archive introuvable : {chemin}")

    condensat = hashlib.sha256()
    with chemin.open("rb") as fichier:
        for bloc in iter(lambda: fichier.read(1024 * 1024), b""):
            condensat.update(bloc)
    empreinte = condensat.hexdigest()

    if empreinte_attendue and empreinte != empreinte_attendue.strip().lower():
        raise ImportImpossible(
            f"empreinte de l'archive {empreinte} ≠ attendue {empreinte_attendue} "
            "— transfert tronqué ou fichier remplacé, rien n'a été importé."
        )
    return empreinte


def pic_memoire_mo() -> float:
    """Pic de mémoire résidente du processus. `ru_maxrss` est en kilo-octets
    sous Linux — la même mesure que celle du 2026-09-06 en développement, pour
    que les deux chiffres se comparent."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def etat_du_miroir() -> tuple[int, int]:
    """(entrées, entrées avec ville) — le contrôle de sortie de docs/MIROIRS.md.

    Un taux autour de 7 % au lieu de ~66 % signale que le correctif du
    2026-09-06 sur l'indicateur de dispense d'adresse n'est pas dans le code
    déployé. C'est le seul contrôle qui distingue « importé » de
    « importé correctement ».
    """
    from sqlalchemy import func, select

    from falkye.db import get_session
    from falkye.models.req_entry import REQEntry

    session = get_session()
    try:
        total = session.execute(select(func.count()).select_from(REQEntry)).scalar() or 0
        avec_ville = (
            session.execute(
                select(func.count()).select_from(REQEntry).where(REQEntry.ville.is_not(None))
            ).scalar()
            or 0
        )
        return total, avec_ville
    finally:
        session.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chemin", required=True, help="archive JeuDonnees.zip déposée sur l'hôte")
    parser.add_argument("--empreinte-attendue", default=os.environ.get("FALKYE_REQ_SHA256"))
    parser.add_argument("--importe-par", default="chaine-de-deploiement")
    args = parser.parse_args(argv)

    url = verifier_cible()
    chemin = Path(args.chemin)
    empreinte = verifier_archive(chemin, args.empreinte_attendue)

    taille_mo = chemin.stat().st_size / (1024 * 1024)
    print(f"cible    : {url}", flush=True)
    print(f"archive  : {chemin} ({taille_mo:.0f} Mo)", flush=True)
    print(f"empreinte: {empreinte}", flush=True)

    from falkye.db import get_session, init_db
    from falkye.manual_import import importer_fichier_source

    init_db()  # crée les tables manquantes des DEUX bases

    debut = time.monotonic()
    session = get_session()
    try:
        signaux = importer_fichier_source(
            session, "req", str(chemin), importe_par=args.importe_par
        )
    finally:
        session.close()
    duree = time.monotonic() - debut

    total, avec_ville = etat_du_miroir()
    part_ville = 100 * avec_ville / total if total else 0.0

    print("--- RAPPORT D'IMPORT ---", flush=True)
    print(f"durée        : {duree / 60:.1f} min", flush=True)
    print(f"pic mémoire  : {pic_memoire_mo():.0f} Mo", flush=True)
    print(f"entrées      : {total:,}".replace(",", " "), flush=True)
    print(f"avec ville   : {avec_ville:,} ({part_ville:.1f} %)".replace(",", " "), flush=True)
    print(f"signaux      : {len(signaux)}", flush=True)

    if total and part_ville < 40:
        # Pas une erreur de sortie : le miroir EST chargé et utilisable. Mais le
        # dire fort, parce qu'un miroir sans ville rend invisible tout profil qui
        # filtre par territoire, et que rien d'autre ne le signalerait.
        print(
            f"ATTENTION : seulement {part_ville:.1f} % des entrées portent une ville, "
            "attendu ~66 %. Le correctif du 2026-09-06 sur l'indicateur de dispense "
            "d'adresse n'est probablement pas dans le code déployé "
            "(falkye/sources/req.py::_resoudre_entreprise).",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
