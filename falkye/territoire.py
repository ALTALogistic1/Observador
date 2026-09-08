"""Comparer un territoire déclaré à ce qu'une source en écrit vraiment.

**Pourquoi ce module existe.** La portée territoriale est une décision de
PRODUIT : elle vit au registre (`SourceDef.territoire`), sous sa graphie juste et
lisible — « Québec ». Ce que les sources écrivent, lui, ne l'est pas toujours.

Mesuré le 2026-09-07 sur le fichier réel du programme des travailleurs étrangers
temporaires : la colonne des provinces y vaut littéralement ``'Qu bec'``, octets
``b'Qu bec'``. Le diffuseur n'a pas REPLIÉ l'accent, il a SUPPRIMÉ la lettre — un
espace à la place du ``é``. Dans la même colonne, ses notes de bas de page
gardent pourtant tous leurs accents, et dans la même ligne la profession aussi :
c'est bien la valeur de province qui est abîmée chez lui, pas notre décodage.

**Conséquence, et c'est le piège.** Replier les accents des deux côtés ne suffit
pas : « Québec » donne ``quebec``, ``'Qu bec'`` donne ``qubec``. Jamais égaux.
Un filtre bâti là-dessus ne retiendrait RIEN, silencieusement — exactement le
défaut de l'indicateur de dispense d'adresse, une condition portant sur une
valeur qu'on croit connaître.

**La règle retenue : deux graphies de référence, une seule côté source.**

    « Québec »  →  {quebec, qubec}      accent replié, ET lettre accentuée retirée
    'Qu bec'    →   qubec               ✓
    'Québec'    →   quebec              ✓
    'Quebec'    →   quebec              ✓

Les trois formes possibles se reconnaissent, y compris celle d'un diffuseur qui
corrigerait son export un jour. Le registre ne porte jamais la faute d'un autre.
"""
from __future__ import annotations

import re
import unicodedata

_NON_ALPHANUM = re.compile(r"[^a-z0-9]")


def _cle(valeur: str) -> str:
    """Minuscule, sans rien d'autre que des lettres ASCII et des chiffres.

    Les espaces et la ponctuation disparaissent : c'est ce qui rend
    « Nouvelle-Écosse » et ``'Nouvelle- cosse'`` comparables.
    """
    return _NON_ALPHANUM.sub("", valeur.lower())


def _replie(valeur: str) -> str:
    """« Québec » → « Quebec ». Le repli d'accent ordinaire."""
    return unicodedata.normalize("NFKD", valeur).encode("ascii", "ignore").decode()


def _sans_lettres_accentuees(valeur: str) -> str:
    """« Québec » → « Qubec ». La lettre accentuée RETIRÉE, pas repliée —
    la transformation qu'un diffuseur applique quand son export perd le non-ASCII."""
    return "".join(c for c in valeur if c.isascii())


def cles_de_reference(territoire: str) -> set[str]:
    """Les graphies sous lesquelles un territoire déclaré peut apparaître."""
    return {_cle(_replie(territoire)), _cle(_sans_lettres_accentuees(territoire))}


def appartient(valeur: str | None, territoires: list[str]) -> bool:
    """La valeur écrite par la source désigne-t-elle un des territoires déclarés?

    Une valeur ABSENTE est retenue, jamais rejetée. Une source qui ne renseigne
    pas la région ne doit pas voir tout son contenu disparaître à cause d'un
    filtre qu'elle ne sait pas alimenter : le territoire se vérifiera plus tard,
    à la résolution. Rejeter ici serait exactement le défaut de l'indicateur de
    dispense — supprimer sur une ABSENCE d'information.
    """
    if not territoires:
        return True
    if valeur is None or not valeur.strip():
        return True
    attendu: set[str] = set()
    for t in territoires:
        attendu |= cles_de_reference(t)
    return _cle(_replie(valeur)) in attendu
