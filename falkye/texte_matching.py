"""Correspondance mot-à-mot partagée — extrait de falkye/assistance_sphere.py
lors de la généralisation du mécanisme d'assistance IA à la dimension "qui"
(spec section 8bis, 2026-09-03), pour que le correctif de bornes de mot ne
vive qu'à UN seul endroit plutôt que d'être dupliqué entre
falkye/assistance_sphere.py et falkye/assistance_client_cible.py.

Historique du correctif (trouvé en validant contre de vraies données,
2026-09-03) : une correspondance de SOUS-CHAÎNE brute faisait matcher
l'acronyme "TI" à l'intérieur du mot "implan-TA-TI-on" — corrigé par des
bornes de mot en regex, jamais réintroduit ailleurs depuis."""
from __future__ import annotations

import re


def motif_present(texte_lower: str, motif: str) -> bool:
    """`motif` (déjà en minuscules, ex. un synonyme de registre) apparaît-il
    dans `texte_lower` comme un mot ou une expression complète — jamais comme
    sous-chaîne d'un mot plus long? Bornes ((?<!\\w)/(?!\\w) plutôt que \\b)
    pour rester correctes sur les lettres accentuées ET sur les motifs
    contenant une apostrophe (ex. "gestion d'inventaire")."""
    return bool(motif) and bool(re.search(rf"(?<!\w){re.escape(motif)}(?!\w)", texte_lower))
