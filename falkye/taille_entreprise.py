"""Filtre par taille d'entreprise estimée — spec section 4bis (3 fonctionnalités
transversales additionnelles, ajoutée le 2026-09-02) : "dérivé des signaux
d'embauche cumulés déjà captés (Guichet-Emplois, EIMT, section 7) et du dossier
cumulatif par entreprise — nouvelle couche de calcul, pas une nouvelle source."

Proxy assumé et documenté (choix d'implémentation, la spec ne donne pas de
formule — même statut que les paliers de falkye/scoring.py) : le volume cumulé
de postes ouverts/approuvés (Signal.valeur_associee, déjà rempli par
falkye/sources/guichet_emplois.py et falkye/sources/eimt.py pour
recrutement_massif) est un proxy pour la TAILLE de l'entreprise, pas une mesure
directe — une entreprise de 500 employés qui recrute pour 3 postes n'est pas
"petite", elle recrute peu en ce moment. Approximation assumée, affinable avec
l'usage réel (principe directeur #9 : ne pas complexifier pour du non confirmé).

Tranches alignées sur la classification Statistique Canada par nombre
d'employés (1-4 / 5-19 / 20-99 / 100+), vocabulaire déjà familier pour un
utilisateur B2B canadien."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from falkye.models.company import Company


class TrancheTaille(str, Enum):
    MICRO = "micro"  # 1-4 employés estimés
    PETITE = "petite"  # 5-19
    MOYENNE = "moyenne"  # 20-99
    GRANDE = "grande"  # 100+


# (borne_min, borne_max) — borne_max=None signifie "et plus".
BORNES_TRANCHE: dict[TrancheTaille, tuple[int, int | None]] = {
    TrancheTaille.MICRO: (1, 4),
    TrancheTaille.PETITE: (5, 19),
    TrancheTaille.MOYENNE: (20, 99),
    TrancheTaille.GRANDE: (100, None),
}


@dataclass
class EstimationTaille:
    tranche: TrancheTaille
    volume_postes_estime: float  # somme cumulée des postes détectés — la donnée brute derrière le palier


def _tranche_pour_volume(volume: float) -> TrancheTaille:
    if volume >= 100:
        return TrancheTaille.GRANDE
    if volume >= 20:
        return TrancheTaille.MOYENNE
    if volume >= 5:
        return TrancheTaille.PETITE
    return TrancheTaille.MICRO


def estimer_taille(company: Company) -> EstimationTaille | None:
    """None si l'entreprise n'a AUCUN signal de recrutement — rien à estimer,
    jamais une tranche par défaut inventée (principe directeur #1)."""
    signaux_recrutement = [s for s in company.signals if s.signal_type_id == "recrutement_massif"]
    if not signaux_recrutement:
        return None

    # Un signal qualitatif (titre de poste) sans volume compté vaut 1 poste — il
    # existe (au moins ce poste précis), même sans dénombrement explicite.
    volume = sum((s.valeur_associee or 1.0) for s in signaux_recrutement)
    return EstimationTaille(tranche=_tranche_pour_volume(volume), volume_postes_estime=volume)


def correspond_au_filtre(company: Company, employes_min: int | None, employes_max: int | None) -> bool:
    """True si l'estimation de taille de `company` chevauche l'intervalle
    [employes_min, employes_max] demandé. Une entreprise SANS estimation
    (aucun signal de recrutement) ne correspond à aucun filtre borné — un
    filtre de taille n'a de sens que sur une donnée qui existe."""
    if employes_min is None and employes_max is None:
        return True

    estimation = estimer_taille(company)
    if estimation is None:
        return False

    borne_min, borne_max = BORNES_TRANCHE[estimation.tranche]
    if employes_min is not None and (borne_max is not None and borne_max < employes_min):
        return False
    if employes_max is not None and borne_min > employes_max:
        return False
    return True
