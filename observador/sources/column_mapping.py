"""Utilitaires partagés de normalisation et de résolution de colonnes CSV, utilisés
par les connecteurs dont le schéma exact n'a pas pu être confirmé avant déblocage
réseau (REQ, Guichet-Emplois) — voir docs/STATUT_RESEAU.md. Centralisé ici plutôt
que dupliqué pour que l'ajustement des alias, une fois les vrais en-têtes connus,
se fasse au même endroit pour toutes les sources CSV."""
from __future__ import annotations

import re
import unicodedata


def normaliser(texte: str) -> str:
    """Minuscule, sans accents, ponctuation réduite à des espaces, espaces
    compressés — comparaison tolérante aux variantes de graphie."""
    texte = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    texte = re.sub(r"[^a-z0-9 ]", " ", texte.lower())
    return re.sub(r"\s+", " ", texte).strip()


def resolve_columns(fieldnames: list[str], aliases: dict[str, list[str]]) -> dict[str, str]:
    """Fait correspondre chaque champ logique (clé de `aliases`) à son en-tête réelle
    dans `fieldnames`, par sous-chaîne normalisée. Lève ValueError avec le détail des
    champs manquants et des en-têtes disponibles plutôt que de deviner silencieusement."""
    normalized = {normaliser(f).replace(" ", "_"): f for f in fieldnames}
    resolved: dict[str, str] = {}
    missing: list[str] = []
    for logical, candidate_aliases in aliases.items():
        found = None
        for alias in candidate_aliases:
            for norm_name, original_name in normalized.items():
                if alias in norm_name:
                    found = original_name
                    break
            if found:
                break
        if found:
            resolved[logical] = found
        else:
            missing.append(logical)
    if missing:
        raise ValueError(
            f"Colonnes introuvables: {missing}. En-têtes disponibles: {fieldnames}. "
            "Ajuster la table d'alias correspondante dans observador/sources/."
        )
    return resolved
