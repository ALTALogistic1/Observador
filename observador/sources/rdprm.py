"""Connecteur RDPRM — statut `a_developper` (voir registry/sources.yaml).

DÉCOUVERTE (documentée aussi dans docs/STATUT_RESEAU.md) : le RDPRM n'a pas d'accès
gratuit en vrac ni d'API publique — seulement une consultation payante à l'unité
(11 $/nom d'entreprise, 4 $/NIV, carte de crédit, une recherche à la fois). Décision
produit (2026-08-31, Alexandre) : Phase 2, avec un déclenchement CIBLÉ par entreprise
déjà détectée par une autre source — jamais un balayage en vrac (le tarif à l'unité
rendrait un balayage en vrac prohibitif et n'a de toute façon aucun sens : le RDPRM
n'expose pas de liste des inscriptions récentes, seulement une recherche par nom).

Ce stub existe pour que le RDPRM soit visible et prêt dans le registre (spec section
9), pas pour être appelé par le moteur de découverte générique. Quand la Phase 2
l'active, ce connecteur devra être invoqué explicitement par entreprise (ex. depuis
observador/engine.py, après qu'un Company existe déjà), pas via la boucle
`detect(since)` standard qui suppose une découverte en vrac — d'où `disponible()`
qui retourne False et une classe qui hérite volontairement de StubConnector plutôt
que d'implémenter une vraie boucle for l'instant.
"""
from __future__ import annotations

from observador.sources.base import StubConnector


class RDPRMConnector(StubConnector):
    """Aucune détection en vrac. Voir docstring du module pour le plan d'activation
    Phase 2 (appel ciblé par entreprise, coût à l'unité assumé par Alexandre)."""


CONNECTOR_CLASS = RDPRMConnector
