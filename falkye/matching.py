"""Correspondance signal → sphère de besoin, et correspondance qualitative aux
mots-clés du profil (spec section 7, table signal → sphères ; section 4, mots-clés
optionnels ; section 7, Signal 3 "lien avec les mots-clés du profil utilisateur").
"""
from __future__ import annotations

from dataclasses import dataclass, field

from falkye.models.profile import Profile, ProfileNeed
from falkye.registry.loader import Registry
from falkye.sources.base import RawSignal
from falkye.sources.column_mapping import normaliser

# Titres de poste orientés transformation/implantation (spec section 7, Signal 3) —
# signal qualitatif fort même pour un seul poste, indépendant des mots-clés propres
# à un profil en particulier. Base de départ, affinable avec l'usage.
#
# Polyvalence (spec section 9, "Polyvalence d'utilisation") : cette liste est un
# indicateur générique d'INTENTION de transformation organisationnelle, pas une
# liste de systèmes ou de secteurs particuliers — un agent immobilier commercial,
# un courtier d'assurance ou une agence de recrutement doivent y trouver un signal
# aussi pertinent qu'un consultant en implantation de systèmes. Ne jamais y ajouter
# un terme qui ne fait sens que pour un secteur ou un service précis (ex. un nom de
# logiciel ou de catégorie de système) — ça revient à coder en dur un cas d'usage.
MOTS_CLES_TRANSFORMATION = [
    "implantation",
    "transformation",
    "amelioration continue",
    "transition numerique",
    "modernisation",
    "deploiement",
    "reorganisation",
    "restructuration",
    "mise en place",
    "directeur de la transformation",
    "gestionnaire amelioration continue",
    "responsable de la transition",
    "conduite du changement",
    "optimisation des processus",
    "chef de projet",
]


@dataclass
class MatchResult:
    profile_need: ProfileNeed
    sphere_generique: bool  # correspondance via la table signal -> sphères (générique)
    correspondance_qualitative: bool  # correspondance via mots-clés/titre (précise, Signal 3)
    mots_cles_trouves: list[str] = field(default_factory=list)


def spheres_probables(signal_type_id: str, registry: Registry) -> list[str]:
    """Table de correspondance signal -> sphères probables (spec section 7)."""
    signal_type = registry.signal_types.get(signal_type_id)
    return list(signal_type.spheres_probables) if signal_type else []


def _titre_contient(titre_normalise: str, mot_cle: str) -> bool:
    mc = normaliser(mot_cle)
    return bool(mc) and mc in titre_normalise


def correspondance_qualitative_titre(titre_poste: str | None, mots_cles_profil: list[str]) -> list[str]:
    """Retourne la liste des mots-clés (du profil ou de la base transformation)
    trouvés dans le titre de poste. Une liste non vide = signal qualitatif fort
    (spec Signal 3), indépendant du volume de postes."""
    if not titre_poste:
        return []
    titre_norm = normaliser(titre_poste)
    trouves = [mc for mc in mots_cles_profil if _titre_contient(titre_norm, mc)]
    trouves += [mc for mc in MOTS_CLES_TRANSFORMATION if _titre_contient(titre_norm, mc)]
    # dédoublonnage en conservant l'ordre
    seen = set()
    result = []
    for mc in trouves:
        if mc not in seen:
            seen.add(mc)
            result.append(mc)
    return result


def match_profile(raw: RawSignal, profile: Profile, registry: Registry) -> list[MatchResult]:
    """Pour chaque paire sphère+service du profil (mécanique fournisseur — voir
    Profile.besoins_fournisseur), détermine si ce signal la concerne, via la table
    générique signal->sphères et/ou via la correspondance qualitative précise."""
    spheres_generiques = set(spheres_probables(raw.signal_type_id, registry))
    resultats: list[MatchResult] = []

    for need in profile.besoins_fournisseur():
        sphere_ok = need.sphere_id in spheres_generiques
        mots_cles_trouves: list[str] = []
        if raw.signal_type_id == "recrutement_massif":
            mots_cles_trouves = correspondance_qualitative_titre(
                raw.titre_ou_description, need.liste_mots_cles()
            )

        if sphere_ok or mots_cles_trouves:
            resultats.append(
                MatchResult(
                    profile_need=need,
                    sphere_generique=sphere_ok,
                    correspondance_qualitative=bool(mots_cles_trouves),
                    mots_cles_trouves=mots_cles_trouves,
                )
            )

    return resultats
