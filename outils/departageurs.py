#!/usr/bin/env python3
"""Trois FAITS qui séparent deux candidats — et aucun ne touche à une échelle.

**Le fait qui les fait exister** *(2026-09-17, après le second temps)*. Les
« trop faibles » ont chuté de 73 % et **les ambigus sont montés à 5 002**. *Un
ambigu n'est pas un dossier sans candidat : c'est un dossier avec DEUX candidats
que le nom ne sépare pas.*

> ⚠️ **Un départageur AJOUTE un fait. Il n'ABAISSE pas une garde.** *Le seuil de
> 92 et l'écart de 8 ne bougent pas, et ces outils n'existent pas pour les
> rouvrir.*

## La règle de séparation, et elle est plus stricte qu'il n'y paraît

**Un fait ABSENT chez un concurrent ne l'exclut pas.** *« Je ne sais pas » n'est
pas « non ».* Un départage n'est donc prononcé que si :

1. le **dossier** porte le fait;
2. **exactement un** concurrent est compatible;
3. ⚠️ **tous les autres concurrents PORTENT le fait** et sont incompatibles.

*Sans la troisième condition, un candidat sans code postal serait écarté pour
n'avoir pas de code postal* — et le départageur deviendrait un filtre sur le
remplissage du registre, pas sur l'identité.

⚠️ **Et un départage ÉCARTE un candidat; il n'en CONFIRME aucun.** *Deux
entreprises distinctes peuvent partager une ville, un code postal et un secteur.*

## Ce que chacun sait, et ce qu'il ignore

| départageur | côté dossier | côté registre | sa limite |
|---|---|---|---|
| **ville** | `Company.ville`, `Signal.champs` | `REQEntry.ville` | Montréal ne sépare rien |
| **code postal** | l'adresse EIMT, `Signal.champs` | `REQEntry.code_postal` | ⚠️ l'EIMT en donne souvent un TRONQUÉ |
| **activité** | `Company.secteur_activite_libelle`, SEAO | `REQEntry.secteur_libelle` | ⚠️ **UNSPSC et CAE ne se joignent pas par code** |

⚠️ **L'activité se compare par LIBELLÉ, pas par code, et c'est une faiblesse
assumée.** *Le SEAO classe en UNSPSC, le REQ en CAE; aucune table ne les relie,
et en inventer une serait décider à la place d'Alexandre.* **La comparaison
textuelle est donc un PLANCHER de ce que l'activité rendrait avec la vraie
table** — celle que le chantier 22 construira pour son propre usage.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

#: Un code postal canadien complet, sous sa forme compacte.
CODE_POSTAL = re.compile(r"^[A-Z]\d[A-Z]\d[A-Z]\d$")
#: La région de tri d'acheminement — les trois premiers caractères. *C'est ce
#: qui reste comparable quand la source donne un code TRONQUÉ, et l'EIMT le fait
#: souvent : `'St-Isidore, QC J0L  2A'` n'a que cinq caractères sur six.*
DEBUT_CODE_POSTAL = re.compile(r"^[A-Z]\d[A-Z]$")

#: Les mots qu'un libellé d'activité porte sans rien distinguer. *Les garder
#: ferait « concorder » une boulangerie et une plomberie sur « autres services ».*
MOTS_VIDES_ACTIVITE = frozenset({
    "de", "du", "des", "la", "le", "les", "et", "en", "au", "aux", "a", "d", "l",
    "autres", "autre", "divers", "diverses", "services", "service", "generaux",
    "general", "generale", "activites", "activite", "entreprises", "entreprise",
    "non", "classes", "ailleurs", "nda", "sans", "objet",
})


@dataclass(frozen=True)
class Fait:
    """Ce qu'un départageur sait — **les formes COMPARABLES, et le brut à côté**.

    *Le brut sert à regarder une paire; les formes servent à comparer.* Confondre
    les deux fait afficher ce qu'on n'a pas comparé.
    """

    formes: frozenset[str]
    brut: str

    def compatible_avec(self, autre: "Fait") -> bool:
        return bool(self.formes & autre.formes)


def fait_de_la_ville(valeur: str | None) -> Fait | None:
    """La ville, normalisée. *`St-Isidore` et `SAINT-ISIDORE` ne sont PAS la même
    forme ici* — la normalisation des municipalités est un chantier à part, et
    l'inventer ferait passer pour un départage ce qui est une graphie."""
    from falkye.sources.column_mapping import normaliser

    if not valeur:
        return None
    forme = normaliser(valeur)
    return Fait(frozenset({forme}), valeur) if forme else None


def codes_postaux(texte: str | None) -> Fait | None:
    """Les codes postaux d'un texte, **complets ET tronqués**.

    ⚠️ **Deux niveaux, et il faut les deux.** *L'EIMT écrit
    `'St-Isidore, QC J0L  2A'` — cinq caractères au lieu de six.* **Un code
    complet rend `{'J0L2A1', 'J0L'}`, un code tronqué rend `{'J0L'}`** : la
    comparaison réussit alors sur la région de tri, qui est ce qui reste de
    comparable.

    *Comparer un tronqué à un complet sur six caractères rendrait toujours faux,
    et le départageur paraîtrait inutile alors qu'il est mal lu.*
    """
    if not texte:
        return None
    # ⚠️ **On lit des JETONS, jamais une fenêtre glissante.** *Balayer la chaîne
    # caractère par caractère invente des codes : `'…QC J0L 2A'` compacté en
    # `STISIDOREQCJ0L2A` contient `L2A`, qui a la forme d'une région de tri et
    # n'en est pas une.* **Un faux code rend un mauvais candidat « compatible »,
    # donc produit un faux départage** — le seul coût que ce départageur puisse
    # avoir, et il s'élimine par conception.
    jetons = re.findall(r"[A-Za-z0-9]+", texte.upper())
    formes: set[str] = set()
    for i, jeton in enumerate(jetons):
        if CODE_POSTAL.match(jeton):
            formes.add(jeton)
            formes.add(jeton[:3])
            continue
        if DEBUT_CODE_POSTAL.match(jeton):
            formes.add(jeton)
            # `J0L 2A1` est écrit en DEUX jetons : on recolle avec le suivant.
            colle = jeton + (jetons[i + 1] if i + 1 < len(jetons) else "")
            if CODE_POSTAL.match(colle):
                formes.add(colle)
    return Fait(frozenset(formes), texte) if formes else None


def fait_de_lactivite(libelle: str | None) -> Fait | None:
    """Les mots PORTEURS d'un libellé d'activité.

    ⚠️ **Comparaison par LIBELLÉ, jamais par code.** *Le SEAO classe en UNSPSC,
    le REQ en CAE, et aucune table ne les relie* — en inventer une serait décider
    à la place d'Alexandre. **Donc ce que rend ce départageur est un PLANCHER de
    ce que l'activité donnerait avec la vraie table.**

    Les mots vides sont retirés : *les garder ferait « concorder » une
    boulangerie et une plomberie sur « autres services ».*
    """
    from falkye.sources.column_mapping import normaliser

    if not libelle:
        return None
    mots = {
        mot for mot in normaliser(libelle).split(" ")
        if len(mot) > 2 and mot not in MOTS_VIDES_ACTIVITE
    }
    return Fait(frozenset(mots), libelle) if mots else None


#: Les issues d'un départage. **Chacune est un RÉSULTAT, y compris les refus** —
#: *« indépartageable » dit lequel des trois maillons manque, et les trois
#: appellent trois correctifs différents.*
DEPARTAGE = "DÉPARTAGÉ"
SANS_FAIT_AU_DOSSIER = "le dossier ne porte pas le fait"
SANS_FAIT_CHEZ_UN_CONCURRENT = "un concurrent ne porte pas le fait — inconnu ≠ non"
PLUSIEURS_COMPATIBLES = "plusieurs concurrents compatibles"
AUCUN_COMPATIBLE = "aucun concurrent compatible — le fait les exclut tous"

ISSUES = (
    DEPARTAGE,
    SANS_FAIT_AU_DOSSIER,
    SANS_FAIT_CHEZ_UN_CONCURRENT,
    PLUSIEURS_COMPATIBLES,
    AUCUN_COMPATIBLE,
)


def departager(du_dossier: Fait | None, des_concurrents: list) -> tuple[str, int | None]:
    """`(issue, index du gagnant ou None)` — **la règle, en un seul endroit.**

    `des_concurrents` est la liste des faits des concurrents, dans l'ordre des
    scores décroissants; `None` veut dire *« ce concurrent ne porte pas le
    fait »*.
    """
    if du_dossier is None:
        return SANS_FAIT_AU_DOSSIER, None
    if any(fait is None for fait in des_concurrents):
        # ⚠️ **« Je ne sais pas » n'est pas « non ».** *Sans cette branche, un
        # candidat sans code postal serait écarté pour n'avoir pas de code
        # postal — et le départageur deviendrait un filtre sur le remplissage du
        # registre.*
        return SANS_FAIT_CHEZ_UN_CONCURRENT, None
    compatibles = [
        i for i, fait in enumerate(des_concurrents)
        if du_dossier.compatible_avec(fait)
    ]
    if not compatibles:
        return AUCUN_COMPATIBLE, None
    if len(compatibles) > 1:
        return PLUSIEURS_COMPATIBLES, None
    return DEPARTAGE, compatibles[0]
