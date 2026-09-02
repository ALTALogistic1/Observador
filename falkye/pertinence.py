"""Score de pertinence — spec section 6 (restructurée, 2026-09-01).

Distinct du score de confiance (falkye/scoring.py, inchangé) : la confiance répond
à "ce signal est-il réel et fort, indépendamment de qui le reçoit", la pertinence
répond à "ce signal correspond-il au profil précis de CET utilisateur". Les deux
axes se combinent en MATRICE, jamais en moyenne (voir falkye/engine.py) — un signal
peu pertinent n'est jamais montré même si sa confiance est élevée.

Trois paliers en registre positif, pas de "non pertinent" (un MatchResult doit déjà
exister pour qu'une notification soit envisagée, donc A est le plancher) :
  A   — Repéré  : correspondance à une sphère seulement probable/secondaire
  AA  — Aligné  : correspondance directe à la sphère PRINCIPALE du signal
  AAA — Sur mesure : correspondance à un mot-clé précis du profil (Signal 3)

Comme falkye/scoring.py, un score numérique interne (0-100) est calculé puis
quantifié en palier — permet d'accumuler des bonus (signal par absence, vélocité)
sur la même échelle avant de trancher le palier final, plutôt que de traiter
A/AA/AAA comme trois cases indépendantes sans granularité entre elles. Ce score
numérique est un détail d'implémentation interne, jamais affiché tel quel à
l'utilisateur (spec : "un seul indice... Faible/Moyen/Élevé" pour la confiance,
même principe de simplicité d'affichage pour la pertinence — seul le palier
A/AA/AAA est montré).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from falkye.matching import MatchResult, spheres_probables
from falkye.models.company import Company
from falkye.models.notification import NiveauPertinence
from falkye.models.signal import Signal
from falkye.registry.loader import Registry

# Paliers de base par tier de correspondance — ancrés aux mêmes seuils de
# quantification ci-dessous pour qu'un match "propre" (sans bonus) atterrisse
# directement dans son palier attendu.
BASE_A = 30.0
BASE_AA = 60.0
BASE_AAA = 90.0

SEUIL_AAA = 80.0
SEUIL_AA = 50.0
# en dessous de SEUIL_AA => A (un MatchResult existe déjà pour qu'on soit ici, donc
# A est un plancher, pas une absence de correspondance — voir docstring du module)

# "Signal par absence" (spec section 6) : bonus fixe, pas proportionnel — soit le
# signal attendu est absent alors que d'autres existent (le cas décrit par la
# spec), soit non ; pas de granularité supplémentaire tant qu'aucun usage réel ne
# justifie d'en ajouter une (principe directeur #9).
BONUS_ABSENCE_SIGNAL_ATTENDU = 15.0

# Vélocité/trajectoire (spec section 6) : plusieurs signaux dans une fenêtre de 60
# jours (même ordre de grandeur que la demi-vie de fraîcheur du score de
# confiance, falkye/scoring.py:DEMI_VIE_FRAICHEUR_JOURS=120 — mais plus courte,
# puisqu'il s'agit ici de détecter une ACCÉLÉRATION récente, pas juste une
# fraîcheur générale) pèsent plus lourd qu'un signal isolé.
FENETRE_VELOCITE_JOURS = 60
BONUS_VELOCITE_PAR_SIGNAL_SUPPLEMENTAIRE = 8.0
BONUS_VELOCITE_MAX = 24.0


@dataclass(frozen=True)
class PonderationValeurs:
    """Pondération du moteur de score de pertinence (spec section 4bis,
    fonctionnalité Radar+ "pondération du moteur de score personnalisable") :
    "l'utilisateur Radar+ ajuste lui-même les poids relatifs des facteurs de
    pertinence (sphère, vélocité, mots-clés) selon sa propre méthodologie
    interne, plutôt que de subir la pondération par défaut définie par FALKYE."

    Les constantes du module ci-dessus (BASE_A/AA/AAA, BONUS_ABSENCE_SIGNAL_
    ATTENDU, BONUS_VELOCITE_*) restent la valeur PAR DÉFAUT (`PONDERATION_
    DEFAUT` ci-dessous, utilisée pour Écho et Radar) — cette dataclass est
    l'interface par laquelle un profil Radar+ peut les remplacer, une à une,
    sans toucher au reste du moteur (falkye/ponderation.py résout la bonne
    instance par profil ; falkye/engine.py ne connaît que cette interface,
    jamais le mécanisme de stockage par-derrière — même principe que le
    registre pour les sources/sphères)."""

    base_a: float = BASE_A
    base_aa: float = BASE_AA
    base_aaa: float = BASE_AAA
    bonus_absence: float = BONUS_ABSENCE_SIGNAL_ATTENDU
    bonus_velocite_max: float = BONUS_VELOCITE_MAX
    bonus_velocite_par_signal: float = BONUS_VELOCITE_PAR_SIGNAL_SUPPLEMENTAIRE


PONDERATION_DEFAUT = PonderationValeurs()


def _sphere_principale(signal_type_id: str, registry: Registry) -> str | None:
    """Sphère PRINCIPALE d'un type de signal, au sens de la spec section 6 (A vs
    AA) : la PREMIÈRE sphère listée dans spheres_probables (falkye/registry/
    signal_types.yaml). Interprétation assumée, documentée ici plutôt que laissée
    implicite : la spec dit "la sphère de l'utilisateur n'est qu'une des sphères
    probables, pas la principale" pour A, ce qui suppose un ordre de préséance
    dans cette liste — déjà cohérent avec l'ordre de la table de correspondance de
    la section 7 (ex. "Gestion de projet" listée en premier pour les classements
    de croissance), pas un ordre arbitraire ou alphabétique à réinterpréter."""
    spheres = spheres_probables(signal_type_id, registry)
    return spheres[0] if spheres else None


def base_match(
    match: MatchResult, signal_type_id: str, registry: Registry, ponderation: PonderationValeurs = PONDERATION_DEFAUT
) -> float:
    """Score de base d'UN match, avant bonus — exposé (pas préfixé `_`) car
    falkye/engine.py s'en sert aussi pour choisir, parmi plusieurs signaux et
    besoins matchés, la sphère la plus pertinente à retenir pour la notification
    (comparaison par tier, pas seulement "le premier match rencontré")."""
    if match.correspondance_qualitative:
        return ponderation.base_aaa
    if match.profile_need.sphere_id == _sphere_principale(signal_type_id, registry):
        return ponderation.base_aa
    return ponderation.base_a


def bonus_signal_absence(
    company: Company, sphere_id: str, registry: Registry, ponderation: PonderationValeurs = PONDERATION_DEFAUT
) -> float:
    """Principe du "signal par absence" (spec section 6) : l'absence d'un signal
    normalement attendu à un stade plus avancé peut être un indicateur de
    pertinence POSITIF, pas seulement la présence d'un signal — découvert avec le
    persona investisseur providentiel (croissance visible mais AUCUN financement
    gouvernemental ni classement encore visible = traction précoce, avant qu'elle
    soit publique).

    Généralisé plutôt que codé en dur pour cette seule sphère (spec : "ce principe
    est généralisable à d'autres sphères... à garder en tête... plutôt que de le
    coder comme un cas spécial au VC") : n'importe quelle sphère peut déclarer, via
    `SphereDef.signal_absence_pertinent` (falkye/registry/spheres.yaml), l'id d'un
    type de signal dont l'absence est pertinente. Le bonus ne s'applique que si
    l'entreprise a AU MOINS UN autre signal (sinon "absence" ne veut rien dire —
    il n'y a simplement rien à comparer) ET que le type de signal déclaré n'est
    justement PAS parmi eux."""
    sphere_def = registry.spheres.get(sphere_id)
    if sphere_def is None or not sphere_def.signal_absence_pertinent:
        return 0.0
    types_presents = {s.signal_type_id for s in company.signals}
    if not types_presents:
        return 0.0
    if sphere_def.signal_absence_pertinent in types_presents:
        return 0.0  # le signal "attendu" est justement présent — pas un cas d'absence
    return ponderation.bonus_absence


def bonus_velocite(signaux: list[Signal], ponderation: PonderationValeurs = PONDERATION_DEFAUT) -> float:
    """Facteur de trajectoire (spec section 6) : "une entreprise avec 3 signaux en
    2 mois est un meilleur prospect qu'une entreprise avec 3 signaux étalés sur 2
    ans, même à confiance égale par signal" — contributeur à la PERTINENCE,
    distinct de la fraîcheur individuelle déjà gérée côté confiance
    (falkye/scoring.py:freshness_factor, qui pénalise l'ÂGE d'un signal, pas leur
    RAPPROCHEMENT entre eux).

    Cherche la fenêtre de FENETRE_VELOCITE_JOURS la plus dense parmi les dates de
    détection (pas seulement l'écart min/max) pour ne pas être faussé par un seul
    signal isolé loin des autres."""
    if len(signaux) < 2:
        return 0.0
    dates = sorted(s.detected_at for s in signaux)
    fenetre = timedelta(days=FENETRE_VELOCITE_JOURS)
    meilleur_compte = 1
    for i, debut in enumerate(dates):
        compte = sum(1 for d in dates[i:] if d - debut <= fenetre)
        meilleur_compte = max(meilleur_compte, compte)
    signaux_rapproches_supplementaires = meilleur_compte - 1
    return min(
        ponderation.bonus_velocite_max,
        signaux_rapproches_supplementaires * ponderation.bonus_velocite_par_signal,
    )


@dataclass
class PertinenceResult:
    score_pertinence: float  # 0-100, interne — jamais affiché tel quel (voir niveau)
    niveau: NiveauPertinence
    bonus_absence: float
    bonus_velocite: float


def calculer_pertinence(
    company: Company,
    signaux_pertinents: list[Signal],
    matches_par_signal: dict[int, list[MatchResult]],
    sphere_choisie: str,
    registry: Registry,
    poids_sphere: float = 1.0,
    ponderation: PonderationValeurs = PONDERATION_DEFAUT,
) -> PertinenceResult:
    """Calcule la pertinence pour LA sphère retenue pour cette notification
    (falkye/engine.py choisit une seule sphère représentative par notification,
    même simplification déjà en place avant cette mise à jour). Prend le MEILLEUR
    tier atteint parmi tous les signaux contribuant à cette sphère précise (même
    principe que le score de confiance : le signal dominant, pas une moyenne),
    puis ajoute les bonus signal-par-absence et vélocité.

    `poids_sphere` (spec section 4bis, "Lien avec la rétroaction utilisateur") :
    multiplicateur 0.4-1.0 appliqué à la SEULE base de correspondance, jamais aux
    bonus signal-par-absence/vélocité — la rétroaction dit "cette sphère
    correspond moins bien à ce que je cherche", pas "je fais moins confiance à la
    vélocité ou à l'absence d'un signal", deux mécanismes indépendants du choix
    de sphère. Voir falkye/retroaction.py:poids_pour_sphere.

    `ponderation` (spec section 4bis, fonctionnalité Radar+ "pondération du
    moteur de score personnalisable") : remplace PONDERATION_DEFAUT pour un
    profil Radar+ qui a défini sa propre pondération — voir
    falkye/ponderation.py:ponderation_pour_profil, appelé par falkye/engine.py."""
    bases = [
        base_match(m, signal.signal_type_id, registry, ponderation)
        for signal in signaux_pertinents
        for m in matches_par_signal.get(signal.id, [])
        if m.profile_need.sphere_id == sphere_choisie
    ]
    base = (max(bases) if bases else ponderation.base_a) * poids_sphere

    b_absence = bonus_signal_absence(company, sphere_choisie, registry, ponderation)
    b_velocite = bonus_velocite(signaux_pertinents, ponderation)

    score = min(100.0, base + b_absence + b_velocite)

    if score >= SEUIL_AAA:
        niveau = NiveauPertinence.AAA
    elif score >= SEUIL_AA:
        niveau = NiveauPertinence.AA
    else:
        niveau = NiveauPertinence.A

    return PertinenceResult(
        score_pertinence=round(score, 1), niveau=niveau, bonus_absence=b_absence, bonus_velocite=b_velocite
    )


_ORDRE_NIVEAUX_PERTINENCE = {NiveauPertinence.A: 0, NiveauPertinence.AA: 1, NiveauPertinence.AAA: 2}

SEUIL_NOTIFICATION_PAR_SENSIBILITE = {
    "faible": NiveauPertinence.AAA,
    "moyen": NiveauPertinence.AA,
    "eleve": NiveauPertinence.A,
}


def franchit_seuil_sensibilite(niveau: NiveauPertinence, sensibilite: str) -> bool:
    """Filtre le niveau de pertinence selon le curseur de sensibilité PERTINENCE
    du profil — indépendant du curseur de sensibilité CONFIANCE
    (falkye/scoring.py:franchit_seuil_sensibilite), spec section 6 : "deux
    curseurs de sensibilité indépendants"."""
    seuil = SEUIL_NOTIFICATION_PAR_SENSIBILITE[sensibilite]
    return _ORDRE_NIVEAUX_PERTINENCE[niveau] >= _ORDRE_NIVEAUX_PERTINENCE[seuil]
