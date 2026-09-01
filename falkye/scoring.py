"""Score de confiance unifié — spec section 6.

"Il n'existe qu'UN SEUL indice de confiance par notification — pas de jauges
parallèles." Trois composantes s'additionnent/se combinent sur la même échelle :
  1. Critères propres au signal (le plus fort des signaux contributifs)
  2. Bonus de corroboration multi-signaux
  3. Facteur de fraîcheur (remplace toute notion séparée d'urgence)

Les critères qualitatifs de la table section 6 (ex. "valeur relative à la taille
estimée de l'entreprise") sont traduits ici en paliers explicites et documentés —
c'est un choix d'implémentation assumé (la spec dit "pas de ML requis pour la v1",
pas de formule exacte) : ajuster les paliers avec l'usage réel, pas une vérité figée.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from falkye.models.notification import NiveauConfiance
from falkye.models.signal import Signal

DEMI_VIE_FRAICHEUR_JOURS = 120
FRAICHEUR_PLANCHER = 0.15

# Bonus de corroboration : +12 points par TYPE de signal distinct supplémentaire
# (pas par signal brut — dix offres d'emploi ne "corroborent" pas plus qu'une seule
# vis-à-vis d'un autre type de signal indépendant), plafonné.
BONUS_CORROBORATION_PAR_TYPE_SUPPLEMENTAIRE = 12.0
BONUS_CORROBORATION_MAX = 30.0

SEUIL_ELEVE = 70.0
SEUIL_MOYEN = 40.0

# Sensibilité -> niveau minimal à notifier. Une sensibilité "élevée" laisse passer
# même les signaux faibles (l'utilisateur veut tout voir) ; une sensibilité "faible"
# ne laisse passer que les signaux les plus forts (filtrage agressif).
SEUIL_NOTIFICATION_PAR_SENSIBILITE = {
    "faible": NiveauConfiance.ELEVE,
    "moyen": NiveauConfiance.MOYEN,
    "eleve": NiveauConfiance.FAIBLE,
}

_ORDRE_NIVEAUX = {NiveauConfiance.FAIBLE: 0, NiveauConfiance.MOYEN: 1, NiveauConfiance.ELEVE: 2}


def freshness_factor(detected_at: datetime, now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    if detected_at.tzinfo is None:
        detected_at = detected_at.replace(tzinfo=timezone.utc)
    jours = max(0.0, (now - detected_at).total_seconds() / 86400)
    facteur = 0.5 ** (jours / DEMI_VIE_FRAICHEUR_JOURS)
    return max(FRAICHEUR_PLANCHER, facteur)


def _palier(valeur: float, paliers: list[tuple[float, float]]) -> float:
    """paliers = [(seuil_min, score)], triés décroissant par seuil ; retourne le
    score du premier seuil atteint."""
    for seuil, score in paliers:
        if valeur >= seuil:
            return score
    return paliers[-1][1] if paliers else 0.0


def _score_appel_offres(signal: Signal) -> float:
    valeur = signal.valeur_associee or 0.0
    # Paliers absolus faute d'estimation fiable de la taille de l'entreprise dans
    # la plupart des sources Phase 1 (spec : "valeur relative à la taille estimée" —
    # approximation assumée tant qu'aucune source ne donne un effectif/chiffre
    # d'affaires de façon systématique).
    base = _palier(valeur, [(1_000_000, 85), (250_000, 65), (50_000, 45), (0, 25)])
    return base


def _score_financement_expansion(signal: Signal) -> float:
    valeur = signal.valeur_associee or 0.0
    base = _palier(valeur, [(500_000, 80), (100_000, 60), (25_000, 40), (0, 20)])

    nature = (signal.champs.get("nature_bien") or "").lower()
    if any(m in nature for m in ["equipement", "équipement", "inventaire", "production"]):
        base += 15
    elif any(m in nature for m in ["vehicule", "véhicule"]):
        base += 0
    else:
        base += 5  # nature inconnue/autre : bonus neutre modeste

    return min(100.0, base)


def _score_recrutement_massif(signal: Signal, nb_postes_recents_entreprise: int = 1) -> float:
    if signal.champs.get("correspondance_qualitative"):
        # Signal fort même à un seul poste (spec section 7, Signal 3).
        nb_mots_cles = len(signal.champs.get("mots_cles_trouves") or [])
        return min(100.0, 75.0 + min(15.0, nb_mots_cles * 5.0))

    if signal.source_id == "eimt":
        # EIMT positive : "signal déjà fort par nature puisque confirmé
        # officiellement par le gouvernement" (spec section 6, table des
        # critères) — paliers plus généreux qu'un simple affichage de poste.
        nb = signal.valeur_associee or nb_postes_recents_entreprise
        return _palier(float(nb), [(5, 90), (2, 75), (1, 65)])

    base = _palier(float(nb_postes_recents_entreprise), [(10, 75), (5, 60), (2, 45), (1, 30)])
    return base


def _score_registre_corporatif(signal: Signal) -> float:
    type_changement = signal.champs.get("type_changement")
    if type_changement == "nouvel_etablissement":
        return 70.0
    if type_changement == "changement_adresse":
        return 50.0
    if type_changement == "permis_construction":
        return _score_permis_construction(signal)
    return 20.0  # mise à jour non catégorisée — ne devrait normalement pas être émise


def _score_permis_construction(signal: Signal) -> float:
    """Paliers calés sur les 4 catégories réelles confirmées dans le jeu de
    données Permis de construction — Ville de Laval (voir falkye/sources/
    permis_construction_laval.py) : une nouvelle construction est un signal
    d'expansion bien plus fort qu'une simple amélioration, elle-même plus
    forte qu'un certificat administratif (autorisation/occupation). Ne se
    base PAS sur `valeur_permis` (coût du PERMIS, pas du chantier — un tarif
    administratif souvent forfaitaire, pas fiable comme proxy de l'ampleur
    des travaux, voir la même source pour le détail)."""
    nature = (signal.champs.get("nature_travaux") or "").lower()
    if "nouvelle" in nature:
        return 75.0
    if "amélioration" in nature or "amelioration" in nature:
        return 50.0
    if "autorisation" in nature:
        return 30.0
    if "occupation" in nature:
        return 25.0
    return 35.0  # catégorie non reconnue (jeu de données futur/étendu) — score prudent


def _score_classement_croissance(signal: Signal) -> float:
    rang = signal.champs.get("rang")
    taux = signal.champs.get("taux_croissance")
    base = 50.0
    if isinstance(rang, (int, float)):
        base = max(base, _palier(1000 - rang, [(950, 90), (800, 75), (500, 60), (0, 45)]))
    if isinstance(taux, (int, float)):
        base = max(base, _palier(taux, [(200, 90), (100, 75), (50, 60), (0, 45)]))
    return base


_SCORERS = {
    "appel_offres": _score_appel_offres,
    "financement_expansion": _score_financement_expansion,
    "recrutement_massif": _score_recrutement_massif,
    "registre_corporatif": _score_registre_corporatif,
    "classement_croissance": _score_classement_croissance,
}


def score_signal_individuel(signal: Signal, nb_postes_recents_entreprise: int = 1) -> float:
    if signal.signal_type_id == "recrutement_massif":
        return _score_recrutement_massif(signal, nb_postes_recents_entreprise)
    scorer = _SCORERS.get(signal.signal_type_id)
    if scorer is None:
        return 30.0  # type de signal inconnu du barème (futur signal Phase 2+) : score prudent
    return scorer(signal)


@dataclass
class ScoreResult:
    score_confiance: float  # 0-100
    niveau: NiveauConfiance
    detail_par_signal: dict[int, float]  # signal.id -> contribution (base * fraîcheur)
    bonus_corroboration: float


def calculer_score(signaux: list[Signal], now: datetime | None = None) -> ScoreResult:
    """Calcule le score unifié pour un groupe de signaux contribuant à une même
    notification consolidée (même Company, spec section 6 "corroboration
    multi-signaux")."""
    if not signaux:
        raise ValueError("calculer_score nécessite au moins un signal")

    now = now or datetime.now(timezone.utc)
    contributions: dict[int, float] = {}

    nb_recrutement = sum(1 for s in signaux if s.signal_type_id == "recrutement_massif")

    for s in signaux:
        base = score_signal_individuel(s, nb_postes_recents_entreprise=nb_recrutement)
        fraicheur = freshness_factor(s.detected_at, now)
        contributions[s.id] = base * fraicheur

    score_dominant = max(contributions.values())

    types_distincts = {s.signal_type_id for s in signaux}
    bonus = min(
        BONUS_CORROBORATION_MAX,
        (len(types_distincts) - 1) * BONUS_CORROBORATION_PAR_TYPE_SUPPLEMENTAIRE,
    )

    score_final = max(0.0, min(100.0, score_dominant + bonus))

    if score_final >= SEUIL_ELEVE:
        niveau = NiveauConfiance.ELEVE
    elif score_final >= SEUIL_MOYEN:
        niveau = NiveauConfiance.MOYEN
    else:
        niveau = NiveauConfiance.FAIBLE

    return ScoreResult(
        score_confiance=round(score_final, 1),
        niveau=niveau,
        detail_par_signal=contributions,
        bonus_corroboration=bonus,
    )


def franchit_seuil_sensibilite(niveau: NiveauConfiance, sensibilite: str) -> bool:
    """Filtre le score consolidé selon la sensibilité du profil (spec section 4/6)."""
    seuil = SEUIL_NOTIFICATION_PAR_SENSIBILITE[sensibilite]
    return _ORDRE_NIVEAUX[niveau] >= _ORDRE_NIVEAUX[seuil]
