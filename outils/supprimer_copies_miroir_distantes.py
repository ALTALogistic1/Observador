"""Supprimer de la base de PRODUIT les copies vides des tables miroir — point 27.9.

**Le reliquat.** Le découpage du 6 septembre 2026 a déplacé les tables miroir
vers un fichier local. Leurs copies sont restées sur la base de produit, vides,
avec le schéma d'AVANT le chantier 2.

**Pourquoi ce n'est pas inoffensif.** Une session mal liée qui écrirait le
miroir sur le moteur du produit trouverait une table du bon nom et
**réussirait** — sur la mauvaise base, dans un schéma périmé. Un échec aurait
dit quelque chose; une réussite ne dit rien. C'est la forme exacte du motif du
cas 30 : *le verdict le plus rassurant est celui qu'une base vide produit.*

**Le piège propre à cet outil, et la raison de tous ses garde-fous.**

    Ces huit noms désignent des reliquats sur une base et le schéma réel sur
    l'autre. Un outil qui supprime par nom, sans vérifier où il est, supprime
    les deux.

`req_entries` sur la base de produit est un déchet; `req_entries` dans le
fichier miroir est le miroir REQ complet. **Le même `DROP TABLE` est une
réparation ici et une perte irréversible là.** L'outil ne touche donc JAMAIS au
moteur miroir — il ne l'ouvre même pas — et refuse toute cible qu'il n'a pas
reconnue comme la base du produit.

**Ce qu'il ne fait pas.** Il ne calcule pas « ce qui est en trop » pour le
supprimer. Il travaille sur la liste **déclarée par `BaseMiroir`**, et chaque
table doit être vérifiée vide **à l'instant de la suppression**. Un outil qui
déduirait sa propre liste de cibles destructrices se tromperait un jour tout
seul, et il aurait l'air d'avoir raison.

    python outils/supprimer_copies_miroir_distantes.py              # passage à blanc
    python outils/supprimer_copies_miroir_distantes.py --appliquer  # supprime
"""
from __future__ import annotations

import argparse
import sys

from sqlalchemy import inspect, text

import falkye.models  # noqa: F401 -- enregistre tous les modèles
from falkye.db import bases_sur_repli, cible_annoncee, est_base_distante, get_engine
from falkye.models.base import BaseMiroir

#: La table la plus ancienne du produit. Si elle manque, ce n'est pas que le
#: point 27.9 est déjà fait — c'est qu'on ne parle pas à la base du produit, et
#: « rien à supprimer » y serait exact et trompeur. Même témoin que
#: `migration_colonnes.py`, volontairement : deux outils qui se contredisent sur
#: l'état d'un schéma ont coûté une demi-journée le 9 septembre 2026.
TABLE_TEMOIN = "companies"


def tables_miroir() -> list[str]:
    """Les tables déclarées par `BaseMiroir`, dans l'ordre où on peut les DROP.

    `sorted_tables` rend l'ordre de CRÉATION (une table avant celles qui la
    référencent); on le renverse pour supprimer les dépendantes d'abord.

    La liste vient des modèles plutôt que d'une constante : une constante se
    serait désynchronisée au premier modèle miroir ajouté, et personne ne
    l'aurait vu — l'outil aurait continué à rendre « rien à supprimer ».
    """
    return [t.name for t in reversed(BaseMiroir.metadata.sorted_tables)]


def _refuser(message: str) -> int:
    print(f"\nREFUS — {message}", file=sys.stderr)
    return 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--appliquer",
        action="store_true",
        help="exécute les DROP TABLE (sans ce drapeau, l'outil ne fait que rapporter)",
    )
    parser.add_argument(
        "--repli-par-defaut",
        action="store_true",
        help="autorise le repli local par défaut — à ne passer qu'en développement, "
        "jamais sur l'hôte",
    )
    args = parser.parse_args()

    # ANNONCER LA CIBLE, TOUJOURS, ET AVANT TOUT LE RESTE — et le mode avec,
    # parce qu'un passage à blanc et une application commençaient pareil.
    print(cible_annoncee())
    print(f"mode    : {'SUPPRESSION' if args.appliquer else 'PASSAGE À BLANC (aucun DROP)'}")
    print(f"distante: {'oui' if est_base_distante() else 'non'}\n")

    # Un outil de migration qui crée sa propre cible ne migre rien, il fabrique.
    # Ici c'est pire qu'ailleurs : sur un repli vide, les huit tables sont
    # absentes, l'outil dirait « rien à supprimer » et on le croirait fait.
    if bases_sur_repli() and not args.repli_par_defaut:
        return _refuser(
            "une base n'a pas de cible choisie — "
            f"{', '.join(bases_sur_repli())} absente(s), donc repli relatif au "
            "répertoire courant.\n"
            "  Sur l'hôte : set -a; . /etc/falkye/falkye.env; set +a\n"
            "  En développement, si le repli est vraiment voulu : --repli-par-defaut"
        )

    moteur = get_engine()  # le moteur du PRODUIT, et lui seul
    presentes = set(inspect(moteur).get_table_names())

    if TABLE_TEMOIN not in presentes:
        return _refuser(
            f"la table témoin « {TABLE_TEMOIN} » est absente de cette base "
            f"({len(presentes)} table(s) en tout).\n"
            "  Ce n'est pas une base de produit. Rendre « rien à supprimer » ici "
            "serait exact et trompeur."
        )

    cibles = tables_miroir()
    print(f"{len(cibles)} table(s) miroir déclarée(s) par les modèles.\n")

    a_supprimer: list[str] = []
    absentes: list[str] = []
    peuplees: list[tuple[str, int]] = []

    with moteur.connect() as connexion:
        for nom in cibles:
            if nom not in presentes:
                absentes.append(nom)
                continue
            # Le compte est LU, jamais supposé. Le corpus dit ces copies vides
            # au 10 septembre; ce qui décide ici est ce que la base répond
            # maintenant.
            lignes = connexion.execute(text(f'SELECT COUNT(*) FROM "{nom}"')).scalar_one()
            if lignes:
                peuplees.append((nom, lignes))
            else:
                a_supprimer.append(nom)

    for nom in absentes:
        print(f"  absente      {nom}")
    for nom in a_supprimer:
        print(f"  vide         {nom}")
    for nom, lignes in peuplees:
        print(f"  ⚠️ PEUPLÉE   {nom} — {lignes} ligne(s)")

    # Une seule table peuplée arrête TOUT, et ne se contourne pas par un
    # drapeau. Sur la base du produit, une de ces tables qui contient des
    # lignes veut dire que quelque chose y écrit — donc que la prémisse du
    # point 27.9 est fausse. Supprimer les sept autres « en attendant »
    # détruirait la trace qui permet de comprendre laquelle.
    if peuplees:
        return _refuser(
            f"{len(peuplees)} table(s) miroir ne sont PAS vides sur la base du produit.\n"
            "  Le point 27.9 suppose des copies vides : la supposition est fausse ici.\n"
            "  Rien n'a été supprimé. Comprendre QUI écrit là avant tout geste."
        )

    if not a_supprimer:
        print("\nRien à supprimer — aucune copie miroir sur cette base.")
        return 0

    if not args.appliquer:
        print(f"\nPassage à blanc. {len(a_supprimer)} table(s) seraient supprimées :")
        for nom in a_supprimer:
            print(f"  DROP TABLE {nom}")
        print("\nRelancer avec --appliquer pour exécuter.")
        return 0

    for nom in a_supprimer:
        # Le compte est revérifié DANS la transaction qui supprime. Entre
        # l'inventaire ci-dessus et ce point, un cycle a pu écrire : le
        # relevé d'avant est une indication, la vérification d'ici est la
        # garantie.
        with moteur.begin() as connexion:
            lignes = connexion.execute(text(f'SELECT COUNT(*) FROM "{nom}"')).scalar_one()
            if lignes:
                return _refuser(
                    f"« {nom} » a reçu {lignes} ligne(s) depuis l'inventaire. "
                    "Suppression abandonnée."
                )
            connexion.execute(text(f'DROP TABLE "{nom}"'))
        print(f"supprimée : {nom}")

    restantes = set(inspect(moteur).get_table_names()) & set(cibles)
    if restantes:
        return _refuser(
            f"après suppression, {len(restantes)} copie(s) subsistent : "
            f"{', '.join(sorted(restantes))}"
        )
    print(f"\n{len(a_supprimer)} copie(s) supprimée(s), aucune ne subsiste.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
