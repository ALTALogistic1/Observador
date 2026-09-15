"""Les archives du REQ conservées sur l'hôte — **leur date se lit dans leur nom**.

**La décision qui fait exister ce module** *(Alexandre, 2026-09-16)*. Chaque mesure
qui demande l'archive obligeait à la retélécharger : *trois fois en deux jours, et
on a changé de méthode chaque fois pour l'éviter.* **On conserve désormais
l'archive.** Le serveur a 66 Go libres, l'archive fait 267 Mo, le répertoire
existe. *Le blocage Cloudflare ne touche que le téléchargement, pas la lecture —
une archive déposée est relisible indéfiniment.* **L'import reste manuel; les
mesures cessent de l'être.**

**Le revers, pris en connaissance de cause, et ce qui le neutralise.** *Une archive
conservée vieillit.* Dans trois semaines, quelqu'un la relira en croyant mesurer
l'état courant, **et rien ne le signalerait** — c'est le motif qui est revenu tout
le 16 septembre : Laval figé, l'adresse de l'EIMT, la table de prix sans date.
**Un fichier figé qui ressemble à un fichier vivant.**

**D'où la règle, et elle tient en un nom de fichier** :

    JeuDonnees-2026-09-02.zip        ✅  sa date se lit sans l'ouvrir
    JeuDonnees.zip                   ⚠️  son âge est INCONNU, pas récent

*Même forme que la table de prix datée et que la portée imprimée sous le chiffre :
**le vieillissement devient lisible sans qu'on ait à s'en souvenir.***

⚠️ **La date vient du NOM, jamais de `mtime`.** *Un `scp`, une copie, une
restauration réécrivent la date de modification* — un fichier publié le 2 septembre
et transféré le 16 porterait le 16, et paraîtrait frais de quatorze jours qu'il n'a
pas. **Le nom, lui, ne change pas tout seul.**

⚠️ **Une archive SANS date n'est pas traitée comme récente.** Elle est utilisable,
et **toujours signalée** : *son âge n'est pas nul, il est inconnu* — l'absence de
mesure n'est pas une mesure nulle.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

#: `JeuDonnees-2026-09-02.zip`. Le préfixe est libre pour qu'une archive
#: renommée à la main reste reconnue, mais la date est au format ISO et en fin
#: de nom — *une date au milieu se confondrait avec un numéro d'édition*.
MOTIF_ARCHIVE_DATEE = re.compile(r"^(?P<prefixe>.+)-(?P<date>\d{4}-\d{2}-\d{2})\.zip$")

#: Le nom hérité, sans date. Reconnu pour qu'une archive déjà déposée ne devienne
#: pas invisible du jour au lendemain — **mais jamais traité comme daté**.
NOM_HERITE = "JeuDonnees.zip"

#: Le Registraire publie **aux deux semaines**. Au-delà de 21 jours, une édition a
#: été manquée : ce n'est plus « la dernière », c'est « l'avant-dernière ».
#: *Trois semaines et non deux : un seuil à 14 jours crierait à chaque veille de
#: publication, et une garde qui crie à tort finit par être ignorée.*
SEUIL_VIEILLISSEMENT_JOURS = 21


def date_de_larchive(chemin: Path | str) -> date | None:
    """La date lue **dans le nom**, ou `None` si le nom n'en porte pas.

    *Jamais `mtime`* : une copie ou une restauration le réécrit, et l'archive
    paraîtrait fraîche de jours qu'elle n'a pas.
    """
    correspondance = MOTIF_ARCHIVE_DATEE.match(Path(chemin).name)
    if not correspondance:
        return None
    try:
        return date.fromisoformat(correspondance.group("date"))
    except ValueError:
        # `JeuDonnees-2026-13-45.zip` : un nom qui RESSEMBLE à une date n'en est
        # pas une. Rendre None plutôt que lever — l'archive reste utilisable,
        # elle est simplement non datée.
        return None


def archives_du_dossier(dossier: Path | str) -> list[tuple[date | None, Path]]:
    """Toutes les archives du répertoire, **les datées d'abord, plus récente en
    tête**, les non datées ensuite.

    *L'ordre est le résultat* : `la_plus_recente` en dépend, et une archive non
    datée ne doit jamais passer devant une datée — son âge est inconnu, pas nul.
    """
    dossier = Path(dossier)
    if not dossier.is_dir():
        return []
    trouvees = [(date_de_larchive(c), c) for c in dossier.glob("*.zip")]
    datees = sorted(
        ((d, c) for d, c in trouvees if d is not None), key=lambda t: t[0], reverse=True
    )
    non_datees = sorted(((d, c) for d, c in trouvees if d is None), key=lambda t: t[1].name)
    return datees + non_datees


def la_plus_recente(dossier: Path | str) -> Path | None:
    """L'archive à lire, ou `None` si le répertoire est vide."""
    archives = archives_du_dossier(dossier)
    return archives[0][1] if archives else None


def resoudre(chemin: Path | str) -> Path | None:
    """Accepte **un fichier ou un répertoire**, et rend l'archive à lire.

    *Un seul point d'entrée pour tous les outils* — sinon chacun choisirait son
    archive à sa façon, et deux mesures prises le même jour porteraient sur deux
    fichiers différents sans que personne ne le voie.
    """
    chemin = Path(chemin)
    if chemin.is_dir():
        return la_plus_recente(chemin)
    return chemin if chemin.is_file() else None


def age_en_jours(quand: date | None, aujourdhui: date | None = None) -> int | None:
    """L'âge de l'archive, ou `None` si sa date est inconnue. **`None` n'est pas
    zéro** — c'est l'absence de mesure, et elle se propage jusqu'à l'affichage."""
    if quand is None:
        return None
    return ((aujourdhui or date.today()) - quand).days


def avertissement(chemin: Path | str, aujourdhui: date | None = None) -> str | None:
    """La phrase à imprimer au-dessus de toute mesure tirée de cette archive, ou
    `None` quand il n'y a rien à signaler.

    **Trois états, jamais deux** : datée et fraîche (rien), datée et vieillie
    (l'âge et l'édition manquée), **non datée (l'âge est inconnu)**. *Fondre les
    deux derniers ferait lire « vieille » là où il faut lire « on ne sait pas ».*
    """
    quand = date_de_larchive(chemin)
    if quand is None:
        return (
            f"⚠️ ARCHIVE NON DATÉE ({Path(chemin).name}) — son âge est INCONNU, pas récent. "
            "La renommer `JeuDonnees-AAAA-MM-JJ.zip` avec la date de publication "
            "lue sur la fiche du jeu (`metadata_modified`), pas celle du transfert."
        )
    jours = age_en_jours(quand, aujourdhui)
    if jours is not None and jours >= SEUIL_VIEILLISSEMENT_JOURS:
        editions = jours // 14
        return (
            f"⚠️ ARCHIVE DU {quand:%Y-%m-%d}, soit {jours} jour(s). Le Registraire "
            f"publie aux deux semaines : environ {editions} édition(s) ont paru depuis. "
            "Ce qui sera mesuré ici n'est PAS l'état courant du registre."
        )
    return None


def ligne_de_provenance(chemin: Path | str, aujourdhui: date | None = None) -> str:
    """La provenance, en une ligne, **à imprimer par tout outil qui lit une
    archive** — *un chiffre sans sa provenance est une promesse que personne ne
    tient.*"""
    chemin = Path(chemin)
    quand = date_de_larchive(chemin)
    jours = age_en_jours(quand, aujourdhui)
    if quand is None:
        return f"archive : {chemin.name}   (date INCONNUE — voir l'avertissement)"
    return f"archive : {chemin.name}   publiée le {quand:%Y-%m-%d}, {jours} jour(s)"
