"""Géocodage — support de la carte géographique interactive (spec section 4bis,
3 fonctionnalités transversales additionnelles, ajoutée le 2026-09-02) : "vue
carte, pastilles de pertinence positionnées par territoire, alternative à la vue
liste du tableau de bord — même donnée, présentation différente."

STATUT DE VALIDATION — IMPORTANT : `NominatimGeocoder` appelle l'API publique de
Nominatim (OpenStreetMap), gratuite et sans clé — choix naturel pour ce produit
(principe directeur #2, "toute source gratuite fait partie du produit", appliqué
ici à un service de géocodage plutôt qu'à un signal de croissance). NON VALIDÉ
contre un vrai appel dans cet environnement de développement : nominatim.
openstreetmap.org est bloqué par le proxy de sortie réseau (confirmé : 403 à la
tentative de connexion), même classe de limitation que theirstack.com/apify.com
(voir docs/STATUT_RESEAU.md) — la logique de requête/normalisation est donc
construite d'après la documentation publique de l'API, jamais confirmée par un
vrai appel.

`Geocoder` reste une interface (pas seulement une fonction) pour permettre un
futur remplacement (ex. un service payant plus précis pour un usage Radar+) sans
toucher à falkye/models/company.py ni au reste du pipeline — même principe que
falkye/sources/agregateur_recrutement.py::FournisseurAgregateur."""
from __future__ import annotations

import logging
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone

import requests

from falkye.models.company import Company

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
# Politique d'usage Nominatim (documentation publique) : maximum 1 requête par
# seconde — non négociable pour un service gratuit partagé, même principe que le
# Crawl-delay respecté pour Guichet-Emplois (falkye/sources/guichet_emplois.py).
DELAI_ENTRE_REQUETES_SECONDES = 1.0


class Geocoder(ABC):
    @abstractmethod
    def geocoder(self, adresse: str | None, ville: str | None, region: str | None) -> tuple[float, float] | None:
        """Retourne (latitude, longitude) ou None si aucune correspondance —
        jamais des coordonnées approximatives inventées (principe directeur #1)."""
        raise NotImplementedError


class NominatimGeocoder(Geocoder):
    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.session.headers.setdefault(
            "User-Agent", os.environ.get("FALKYE_USER_AGENT", "Falkye/0.1 (repereur d'entreprises en croissance)")
        )

    def geocoder(self, adresse: str | None, ville: str | None, region: str | None) -> tuple[float, float] | None:
        requete = ", ".join(filter(None, [adresse, ville, region, "Canada"]))
        if not requete or requete == "Canada":
            return None  # rien d'assez précis pour chercher — pas une requête sur "Canada" seul

        resp = self.session.get(
            NOMINATIM_URL, params={"q": requete, "format": "json", "limit": 1, "countrycodes": "ca"}, timeout=15
        )
        resp.raise_for_status()
        resultats = resp.json()
        time.sleep(DELAI_ENTRE_REQUETES_SECONDES)  # voir DELAI_ENTRE_REQUETES_SECONDES

        if not resultats:
            return None
        premier = resultats[0]
        try:
            return float(premier["lat"]), float(premier["lon"])
        except (KeyError, TypeError, ValueError):
            return None


def geocodeur_par_defaut() -> Geocoder:
    return NominatimGeocoder()


def geocoder_entreprise(company: Company, geocoder: Geocoder | None = None) -> bool:
    """Géocode UNE entreprise si pas déjà tentée (cache — `Company.
    geocode_tente_le`, même principe que `site_web_vérifié_le` pour
    l'enrichissement web : ne jamais refaire un appel réseau pour une donnée déjà
    résolue, ou déjà tentée sans résultat). Retourne True si des coordonnées sont
    maintenant disponibles (déjà en cache ou tout juste résolues)."""
    if company.latitude is not None and company.longitude is not None:
        return True
    if company.geocode_tente_le is not None:
        return False  # déjà tenté sans résultat — pas de nouvel appel réseau

    geocoder = geocoder or geocodeur_par_defaut()
    company.geocode_tente_le = datetime.now(timezone.utc)

    try:
        resultat = geocoder.geocoder(company.adresse, company.ville, company.region)
    except (requests.RequestException, ValueError):
        logger.info("Géocodage échoué pour %s (réseau ou réponse invalide).", company.nom_detecte)
        return False

    if resultat is None:
        return False

    company.latitude, company.longitude = resultat
    return True
