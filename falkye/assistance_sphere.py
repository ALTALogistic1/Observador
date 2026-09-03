"""Assistance à la configuration du profil par IA — Niveau 1 (spec Radar+, point 8,
ajoutée le 2026-09-03, confirmée le 2026-09-03).

Classification LOCALE, texte simple : recherche de correspondance MOT-À-MOT
(bornée par des limites de mot, jamais une sous-chaîne brute — un acronyme court
comme "TI" ne doit pas matcher à l'intérieur de "implan-TA-TI-on") entre la
description libre saisie par l'utilisateur et le dictionnaire de synonymes/
mots-clés de chaque sphère (registry/spheres.yaml::SphereDef.synonymes,
resynchronisé en base via falkye.db.seed_sphere_synonymes_from_registry, ENRICHI
en continu par le Niveau 2 — falkye/assistance_sphere_ia.py — sans jamais changer
ce module). Aucun appel API, aucun coût, disponible pour TOUS les plans (Écho
compris) — confirmé par Alexandre le 2026-09-03 : "texte simple pour le Niveau 1",
pas d'embeddings ni de modèle de langage à ce niveau.

Garde-fou non négociable de la spec, préservé ici comme partout dans le produit :
une suggestion est TOUJOURS une proposition affichée à l'utilisateur, jamais une
classification silencieuse qui modifierait `profile_needs` sans confirmation —
voir falkye/cli.py::profile_suggerer_sphere_cmd, qui n'écrit jamais automatiquement
le résultat de ce module.

"Échoue" (déclenche le Niveau 2, spec) = aucune sphère n'obtient de correspondance
du tout (résultat vide) — le seuil volontairement simple, cohérent avec le principe
directeur #1 ("jamais fabriquer une valeur") : proposer une sphère sur la seule
base d'une correspondance ambiguë ou faible serait pire que de reconnaître
franchement l'échec et d'escalader.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from falkye.models.sphere import Sphere
from falkye.models.sphere_synonyme import SphereSynonyme
from falkye.texte_matching import motif_present


@dataclass(frozen=True)
class SuggestionSphere:
    """Une sphère candidate pour une description donnée, avec le détail des
    mots-clés qui ont matché — la transparence du détail permet à l'utilisateur
    de juger lui-même la pertinence plutôt que de faire confiance à un score
    opaque (même esprit que falkye/scoring.py, qui liste toujours ses éléments
    constitutifs)."""

    sphere_id: str
    sphere_nom: str
    score: int  # nombre de synonymes DISTINCTS trouvés comme sous-chaîne
    mots_cles_matches: list[str] = field(default_factory=list)
    niveau: int = 1


def suggerer_spheres_niveau1(
    db_session: Session, texte_description: str, limite: int = 3
) -> list[SuggestionSphere]:
    """Sphères candidates pour `texte_description`, triées par score décroissant.

    Liste VIDE = échec du Niveau 1 (aucune correspondance) — c'est le signal
    utilisé par falkye/assistance_sphere_ia.py pour décider de déclencher le
    Niveau 2, jamais fabriqué autrement qu'en constatant une liste vide."""
    if not texte_description or not texte_description.strip():
        return []

    texte_lower = texte_description.lower()

    synonymes = (
        db_session.query(SphereSynonyme, Sphere)
        .join(Sphere, Sphere.id == SphereSynonyme.sphere_id)
        .all()
    )

    par_sphere: dict[str, dict] = {}
    for synonyme, sphere in synonymes:
        motif = synonyme.texte.lower().strip()
        if not motif_present(texte_lower, motif):
            continue
        entree = par_sphere.setdefault(
            sphere.id, {"nom": sphere.nom, "mots_cles": set()}
        )
        entree["mots_cles"].add(synonyme.texte)

    suggestions = [
        SuggestionSphere(
            sphere_id=sphere_id,
            sphere_nom=donnees["nom"],
            score=len(donnees["mots_cles"]),
            mots_cles_matches=sorted(donnees["mots_cles"]),
        )
        for sphere_id, donnees in par_sphere.items()
    ]
    suggestions.sort(key=lambda s: (-s.score, s.sphere_nom))
    return suggestions[:limite]
