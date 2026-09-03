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


def filtrer_champs_pertinents(champs: dict, sphere_id: str, source_id: str, registry: Registry) -> dict:
    """Filtrage par champ, contextuel au profil — spec section 6 (ajoutée le
    2026-09-02) : "au sein d'un même signal, un champ peut être pertinent pour
    un profil et du bruit pour un autre" (ex. le secteur/NAICS du REQ compte
    pour un courtier en énergie, pas pour un fournisseur de mobilier de
    bureau). Répond à une question dont la réponse dépend de QUI regarde — donc
    s'applique ICI, au moment du calcul de pertinence, PAR PROFIL (via la
    sphère retenue pour la notification), JAMAIS à l'ingestion.

    Différent de la calibration à l'ingestion (`SourceDef.regle_calibration` —
    ex. REQ ne retient que certains types de mise à jour, RDPRM exclut par
    `nature_bien`), qui répond à une question UNIVERSELLE ("cette donnée
    est-elle du bruit administratif, point final?") et reste inchangée, à sa
    propre couche : cette fonction-ci ne retire jamais rien de `Signal.champs`
    en base, elle ne fait que construire une VUE filtrée pour un usage précis
    (ex. le payload structuré du webhook Radar+, falkye/notifications/
    formatter.py) — "un seul entrepôt, plusieurs lentilles."

    Retourne `champs` INCHANGÉ si aucune entrée n'est déclarée pour (sphere_id,
    source_id) dans `registry/champs_pertinents.yaml` — défaut sûr, ne perd
    jamais une donnée par simple omission de registre (le risque déjà vécu
    avec la sphère "Financement / accès au capital", ajoutée après coup)."""
    autorises = registry.champs_pertinents_pour(sphere_id, source_id)
    if autorises is None:
        return champs
    return {cle: valeur for cle, valeur in champs.items() if cle in autorises}


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


def base_match_pour_sphere(
    match: MatchResult,
    sphere_id: str,
    signal_type_id: str,
    registry: Registry,
    ponderation: PonderationValeurs = PONDERATION_DEFAUT,
) -> float | None:
    """Score de base d'UN match, POUR une sphère précise parmi celles liées au
    besoin (spec section 8bis, lien sphère↔besoin plusieurs-à-plusieurs
    pondéré) — `None` si `sphere_id` n'est même pas liée à ce besoin (rien à
    calculer).

    - Correspondance qualitative (mot-clé précis, Signal 3) : `base_aaa`
      INCHANGÉ pour n'importe quelle sphère liée — preuve indépendante du
      poids de la sphère, jamais mise à l'échelle (confirmé par Alexandre :
      "correspondance qualitative... inchangée, jamais mise à l'échelle par
      un poids de sphère — preuve indépendante").
    - Sphère générique = sphère PRINCIPALE du type de signal → `base_aa ×
      (poids/100)`.
    - Sphère générique = sphère secondaire → `base_a × (poids/100)`. Un lien
      à poids 100 se comporte exactement comme avant cette évolution ; un
      lien à poids 50 (partage exact, ex. le cas Hector) atterrit à
      mi-chemin.
    - Sphère liée mais ni qualitative ni générique pour CE signal précis →
      `None` (rien à en tirer, comme avant)."""
    poids_lien = next((sm.poids for sm in match.spheres_liees if sm.sphere_id == sphere_id), None)
    if poids_lien is None:
        return None
    if match.correspondance_qualitative:
        return ponderation.base_aaa
    if sphere_id not in match.spheres_generiques_ids:
        return None
    fraction = poids_lien / 100.0
    if sphere_id == _sphere_principale(signal_type_id, registry):
        return ponderation.base_aa * fraction
    return ponderation.base_a * fraction


def meilleure_sphere_pour_match(
    match: MatchResult,
    signal_type_id: str,
    registry: Registry,
    ponderation: PonderationValeurs = PONDERATION_DEFAUT,
) -> tuple[float, str | None]:
    """Parmi TOUTES les sphères liées au besoin de ce match, la meilleure
    (score, sphere_id) — utilisé par falkye/engine.py pour choisir, parmi
    plusieurs signaux et besoins matchés, la sphère la plus pertinente à
    retenir pour la notification (comparaison par tier, pas seulement "le
    premier match rencontré"). `(0.0, None)` si le besoin n'a aucune sphère
    liée (pas encore configuré côté "quoi")."""
    if not match.spheres_liees:
        return (0.0, None)
    candidats = [
        (base_match_pour_sphere(match, sm.sphere_id, signal_type_id, registry, ponderation) or 0.0, sm.sphere_id)
        for sm in match.spheres_liees
    ]
    return max(candidats, key=lambda c: c[0])


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


BONUS_QUI_MAX = 12.0
# Fourchette confirmée par Alexandre le 2026-09-03 : "+10 à +15" — même ordre
# de grandeur que les autres bonus circonstanciels (bonus_absence, bonus
# d'expansion inter-provinciale) plutôt qu'une nouvelle échelle. Un
# désaccord CONFIRMÉ (le "qui" de l'entreprise est connu et ne correspond
# PAS au "qui" déclaré du besoin) ne devient JAMAIS un malus silencieux ici
# — voir hors_profil ci-dessous et falkye/engine.py pour le routage vers le
# canal séparé, réservé Radar+.


@dataclass
class PertinenceResult:
    score_pertinence: float  # 0-100, interne — jamais affiché tel quel (voir niveau)
    niveau: NiveauPertinence
    bonus_absence: float
    bonus_velocite: float
    bonus_qui: float = 0.0
    # True = le "qui" de l'entreprise est CONNU et ne correspond à AUCUN
    # client cible déclaré pour ce besoin — jamais reflété comme un malus
    # dans score_pertinence (bonus_qui reste 0.0 dans ce cas), seulement ce
    # drapeau, que falkye/engine.py utilise pour router la notification vers
    # le canal "hors profil déclaré" plutôt que le flux normal.
    hors_profil: bool = False


def bonus_et_redirection_qui(
    client_cible_ids_entreprise: list[str],
    clients_cibles_lies_besoin: list[tuple[str, float]],
) -> tuple[float, bool]:
    """Bonus circonstanciel (spec section 8bis) si le "qui" de l'entreprise
    recoupe le "qui" déclaré du besoin — JAMAIS un gate (des services
    horizontaux existent, un "qui" étroit ne doit jamais créer de faux
    négatif). Les deux listes sont déjà résolues par l'appelant
    (falkye/engine.py) : ce module reste pur, sans requête DB — même principe
    que falkye/scoring.py::calculer_score et bonus_expansion_interprovinciale.

    - Besoin sans restriction déclarée (aucun lien "qui", OU un lien vers
      `aucune_restriction`) → (0.0, False) : rien à comparer, comportement
      historique inchangé.
    - "Qui" de l'entreprise INCONNU (liste vide — souvent le cas, voir le gap
      institutionnel réel trouvé contre le miroir REQ) → (0.0, False) :
      absence d'info n'est JAMAIS un malus.
    - Recoupement → bonus proportionnel au poids du lien "qui" le plus fort
      concerné, jamais au-delà de BONUS_QUI_MAX.
    - Désaccord CONFIRMÉ (les deux listes sont non vides, aucun recoupement)
      → (0.0, True) : jamais un malus silencieux, une redirection."""
    from falkye.models.client_cible import ID_AUCUNE_RESTRICTION

    ids_besoin = {cc_id for cc_id, _ in clients_cibles_lies_besoin}
    if not ids_besoin or ID_AUCUNE_RESTRICTION in ids_besoin:
        return 0.0, False
    if not client_cible_ids_entreprise:
        return 0.0, False

    intersection = ids_besoin & set(client_cible_ids_entreprise)
    if intersection:
        poids_max = max(poids for cc_id, poids in clients_cibles_lies_besoin if cc_id in intersection)
        return BONUS_QUI_MAX * (poids_max / 100.0), False

    return 0.0, True


def calculer_pertinence(
    company: Company,
    signaux_pertinents: list[Signal],
    matches_par_signal: dict[int, list[MatchResult]],
    sphere_choisie: str,
    registry: Registry,
    poids_sphere: float = 1.0,
    ponderation: PonderationValeurs = PONDERATION_DEFAUT,
    client_cible_ids_entreprise: list[str] | None = None,
    clients_cibles_lies_besoin: list[tuple[str, float]] | None = None,
) -> PertinenceResult:
    """Calcule la pertinence pour LA sphère retenue pour cette notification
    (falkye/engine.py choisit une seule sphère représentative par notification,
    même simplification déjà en place avant cette mise à jour). Prend le MEILLEUR
    tier atteint parmi tous les signaux contribuant à cette sphère précise (même
    principe que le score de confiance : le signal dominant, pas une moyenne),
    puis ajoute les bonus signal-par-absence, vélocité, et "qui" (spec section
    8bis — voir bonus_et_redirection_qui ci-dessus).

    `poids_sphere` (spec section 4bis, "Lien avec la rétroaction utilisateur") :
    multiplicateur 0.4-1.0 appliqué à la SEULE base de correspondance, jamais aux
    autres bonus — la rétroaction dit "cette sphère correspond moins bien à ce
    que je cherche", un mécanisme indépendant du choix de sphère. Voir
    falkye/retroaction.py:poids_pour_sphere.

    `ponderation` (spec section 4bis, fonctionnalité Radar+ "pondération du
    moteur de score personnalisable") : remplace PONDERATION_DEFAUT pour un
    profil Radar+ qui a défini sa propre pondération — voir
    falkye/ponderation.py:ponderation_pour_profil, appelé par falkye/engine.py.

    `client_cible_ids_entreprise`/`clients_cibles_lies_besoin` : listes DÉJÀ
    RÉSOLUES par l'appelant (falkye/engine.py) — ce module reste pur, aucune
    requête DB. `None` (comportement par défaut) = comme si aucune des deux
    listes n'était renseignée, bonus_qui=0.0, hors_profil=False (compatible
    avec tout appelant antérieur à cette fonctionnalité)."""
    bases = [
        base_match_pour_sphere(m, sphere_choisie, signal.signal_type_id, registry, ponderation)
        for signal in signaux_pertinents
        for m in matches_par_signal.get(signal.id, [])
    ]
    bases = [b for b in bases if b is not None]
    base = (max(bases) if bases else ponderation.base_a) * poids_sphere

    b_absence = bonus_signal_absence(company, sphere_choisie, registry, ponderation)
    b_velocite = bonus_velocite(signaux_pertinents, ponderation)
    b_qui, hors_profil = bonus_et_redirection_qui(
        client_cible_ids_entreprise or [], clients_cibles_lies_besoin or []
    )

    score = min(100.0, base + b_absence + b_velocite + b_qui)

    if score >= SEUIL_AAA:
        niveau = NiveauPertinence.AAA
    elif score >= SEUIL_AA:
        niveau = NiveauPertinence.AA
    else:
        niveau = NiveauPertinence.A

    return PertinenceResult(
        score_pertinence=round(score, 1),
        niveau=niveau,
        bonus_absence=b_absence,
        bonus_velocite=b_velocite,
        bonus_qui=b_qui,
        hors_profil=hors_profil,
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
