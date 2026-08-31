"""Vérifications de base obligatoires — spec section 6.

"Aucun prospect ne doit être présenté à l'utilisateur — notification individuelle,
résumé périodique, ou recherche ponctuelle — sans qu'un ensemble minimal de
vérifications ait été effectué." Un prospect qui échoue est exclu SILENCIEUSEMENT,
jamais présenté avec un avertissement — donc les fonctions ici ne retournent qu'un
statut interne (StatutVerification), jamais un texte destiné à l'utilisateur.

Deux passes, parce que la vérification #2 dépend de l'enrichissement web (spec
section 10, qui se déroule après le calcul du score mais avant la notification) :
  - verifier_avant_enrichissement : vérifications #1 (statut REQ) et #3 (résolution
    NEQ) — pas besoin d'enrichir le web une entreprise déjà exclue.
  - verifier_apres_enrichissement : vérification #2 (signe d'inactivité du site).
"""
from __future__ import annotations

from observador.enrichment import EnrichmentResult
from observador.models.company import Company, StatutLegal, StatutResolution, StatutVerification


def verifier_avant_enrichissement(company: Company) -> StatutVerification:
    """Vérification #1 (statut légal REQ) et #3 (cohérence de la résolution NEQ)."""
    if company.statut_legal == StatutLegal.RADIEE:
        return StatutVerification.EXCLU_RADIEE

    if company.statut_resolution in (StatutResolution.AMBIGU, StatutResolution.NON_TROUVE):
        return StatutVerification.EXCLU_RESOLUTION_AMBIGUE

    return StatutVerification.NON_VERIFIE  # en attente de la passe post-enrichissement


def verifier_apres_enrichissement(
    company: Company, enrichment: EnrichmentResult | None
) -> StatutVerification:
    """Vérification #2 (signe d'activité via le site web). L'ABSENCE de site n'est
    PAS un motif d'exclusion (spec section 6) — seul un site trouvé qui contredit
    le signal détecté (fermeture, vente, inactivité) l'est."""
    statut_avant = verifier_avant_enrichissement(company)
    if statut_avant != StatutVerification.NON_VERIFIE:
        return statut_avant  # déjà exclu avant même l'enrichissement

    if enrichment is not None and enrichment.indique_inactivite:
        return StatutVerification.EXCLU_SITE_INACTIF

    return StatutVerification.VERIFIE


def appliquer_verification(
    company: Company, enrichment: EnrichmentResult | None = None
) -> StatutVerification:
    """Point d'entrée unique pour le moteur : applique toutes les vérifications et
    met à jour company.statut_verification en conséquence."""
    statut = verifier_apres_enrichissement(company, enrichment)
    company.statut_verification = statut
    return statut
