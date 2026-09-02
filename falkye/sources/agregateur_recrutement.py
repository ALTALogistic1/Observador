"""Connecteur générique — agrégateur tiers de recrutement (LinkedIn/Indeed via un
fournisseur payant, ex. TheirStack ou Apify) — spec section 7 Signal 3, et section
9bis (premier cas concret construit contre le plan Radar, décision d'Alexandre du
2026-09-02). Réactive pleinement le signal recrutement au-delà de Guichet-Emplois
(couverture partielle, offres expirées avant consultation — voir
falkye/sources/guichet_emplois.py) et EIMT positive (ne couvre que le recours à des
travailleurs étrangers temporaires) : LinkedIn et Indeed n'ont aucune API publique
de recherche en lecture (registry/sources.yaml:agregateur_recrutement_tiers), d'où
le passage par un agrégateur tiers payant plutôt qu'un accès direct.

STATUT DE VALIDATION — IMPORTANT : ce connecteur est écrit d'après la documentation
PUBLIQUE des deux fournisseurs (résumés de recherche, le 2026-09-02), jamais contre
un vrai appel réseau : les domaines theirstack.com et apify.com sont bloqués par le
proxy de sortie de cet environnement de développement (même classe de limitation que
registreentreprises.gouv.qc.ca pour le REQ — voir docs/STATUT_RESEAU.md), et aucune
clé API réelle n'est de toute façon disponible tant qu'Alexandre n'a pas tranché
entre les deux fournisseurs (comparatif de prix en cours, communiqué comme non
bloquant pour cette construction). La source reste donc `a_developper` dans le
registre (registry/sources.yaml) — jamais `actif` — tant qu'un vrai appel n'aura
pas confirmé la forme réelle de la réponse, exactement comme RDPRM et le REQ
avant leur validation. `_normaliser_theirstack` tolère plusieurs noms de champs
plausibles par valeur (même principe que falkye/sources/column_mapping.py pour les
en-têtes CSV) précisément parce que cette incertitude est assumée, pas cachée.

Deux fournisseurs, une seule interface (FournisseurAgregateur) — spec section 9bis :
"gestion de connecteurs génériques par fournisseur" est un composant du portail
partagé entre Radar et Radar+, pas propre à cette source. Le fournisseur actif est
choisi par variable d'environnement (FALKYE_AGREGATEUR_RECRUTEMENT_FOURNISSEUR),
jamais codé en dur — same principe que le reste du registre : ajouter/changer de
fournisseur ne doit pas demander de modifier falkye/engine.py.
"""
from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone

import requests
from dateutil import parser as dateutil_parser

from falkye.matching import MOTS_CLES_TRANSFORMATION
from falkye.sources.base import RawSignal, SourceConnector

logger = logging.getLogger(__name__)


def _parse_date(raw) -> datetime | None:
    if not raw:
        return None
    try:
        dt = dateutil_parser.parse(str(raw))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError, TypeError):
        return None


@dataclass
class OffreAgregateur:
    """Forme normalisée d'une offre d'emploi, commune aux deux fournisseurs —
    AgregateurRecrutementConnector ne connaît QUE cette forme, jamais le format
    brut propre à TheirStack ou à un acteur Apify précis."""

    entreprise: str
    titre: str
    source_ref: str
    date_publication: datetime | None = None
    ville: str | None = None
    region: str | None = None
    description: str | None = None
    url: str | None = None


class FournisseurAgregateur(ABC):
    """Un fournisseur = un mécanisme d'accès précis (API HTTP TheirStack, run
    d'acteur Apify, ou un futur troisième fournisseur). Le connecteur ne dépend
    que de cette interface — voir docstring du module."""

    @abstractmethod
    def rechercher(self, mots_cles: list[str], since: datetime | None, limit: int) -> Iterator[OffreAgregateur]:
        raise NotImplementedError


# --- TheirStack ------------------------------------------------------------

THEIRSTACK_URL = "https://api.theirstack.com/v1/jobs/search"


def _premier(item: dict, *cles: str):
    """Retourne la première valeur non vide trouvée parmi plusieurs noms de champs
    plausibles (`a.b` pour un champ imbriqué) — la forme exacte de la réponse
    TheirStack n'a pas pu être confirmée contre un vrai appel, voir docstring du
    module ; tolérer plusieurs hypothèses plutôt que d'en figer une seule."""
    for cle in cles:
        valeur = item
        for part in cle.split("."):
            if not isinstance(valeur, dict):
                valeur = None
                break
            valeur = valeur.get(part)
        if valeur:
            return valeur
    return None


def _normaliser_theirstack(item: dict) -> OffreAgregateur | None:
    entreprise = _premier(item, "company_name", "company.name", "company")
    titre = _premier(item, "job_title", "title")
    ref = _premier(item, "id", "url", "job_url")
    if not entreprise or not titre or not ref:
        return None  # champ essentiel manquant — pas de signal deviné (principe directeur #1)

    return OffreAgregateur(
        entreprise=str(entreprise),
        titre=str(titre),
        source_ref=f"theirstack:{ref}",
        date_publication=_parse_date(_premier(item, "date_posted", "posted_at", "discovered_at")),
        ville=_premier(item, "location", "city"),
        region=_premier(item, "region", "country"),
        description=_premier(item, "description", "job_description"),
        url=_premier(item, "url", "job_url"),
    )


class TheirStackProvider(FournisseurAgregateur):
    """D'après theirstack.com/en/docs/api-reference/jobs/search_jobs_v1 (domaine
    bloqué par le proxy réseau de cet environnement — voir docstring du module) :
    authentification par jeton Bearer, requête POST avec un corps de filtres JSON
    (`job_title_or`, `posted_at_max_age_days`, `limit`, `page`), réponse attendue
    `{"data": [...], "metadata": {...}}`. NON VALIDÉ contre un vrai appel."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def rechercher(self, mots_cles: list[str], since: datetime | None, limit: int) -> Iterator[OffreAgregateur]:
        session = requests.Session()
        session.headers["Authorization"] = f"Bearer {self.api_key}"
        session.headers["Content-Type"] = "application/json"

        corps: dict = {"limit": limit, "page": 0}
        if mots_cles:
            corps["job_title_or"] = mots_cles
        if since:
            corps["posted_at_max_age_days"] = max(1, (datetime.now(timezone.utc) - since).days)

        resp = session.post(THEIRSTACK_URL, json=corps, timeout=30)
        resp.raise_for_status()
        payload = resp.json()

        for item in payload.get("data", []):
            offre = _normaliser_theirstack(item)
            if offre is not None:
                yield offre


# --- Apify -------------------------------------------------------------------

# Apify est un MARCHÉ d'acteurs (Workday/Greenhouse/Lever/etc. — plusieurs
# candidats identifiés en recherche publique, ex. company-career-page-scraper,
# ats-jobs-scraper), pas un fournisseur unique avec un seul schéma de sortie :
# quel acteur précis utiliser reste ouvert (comparatif de prix d'Alexandre en
# cours). Mapping de noms de champs par défaut, PROVISOIRE — à ajuster une fois
# l'acteur réel choisi et sa vraie structure de sortie confirmée, sans toucher
# au code (voir ApifyActeurGeneriqueProvider).
APIFY_MAPPING_CHAMPS_DEFAUT: dict[str, str] = {
    "entreprise": "company",
    "titre": "title",
    "ref": "url",
    "date_publication": "datePosted",
    "ville": "location",
    "description": "description",
    "url": "url",
}


def _normaliser_apify(item: dict, mapping: dict[str, str]) -> OffreAgregateur | None:
    entreprise = item.get(mapping["entreprise"])
    titre = item.get(mapping["titre"])
    ref = item.get(mapping["ref"])
    if not entreprise or not titre or not ref:
        return None

    return OffreAgregateur(
        entreprise=str(entreprise),
        titre=str(titre),
        source_ref=f"apify:{ref}",
        date_publication=_parse_date(item.get(mapping.get("date_publication", ""))),
        ville=item.get(mapping.get("ville", "")),
        description=item.get(mapping.get("description", "")),
        url=item.get(mapping.get("url", "")),
    )


class ApifyActeurGeneriqueProvider(FournisseurAgregateur):
    """Lance N'IMPORTE QUEL acteur Apify de type "offres d'emploi" par son
    identifiant (`actor_id`), via l'endpoint standard `run-sync-get-dataset-items`
    (api.apify.com/v2/acts/{id}/run-sync-get-dataset-items?token=...) — même
    principe de connecteur générique par fournisseur (spec section 9bis) que
    TheirStackProvider, mais un niveau d'indirection de plus puisque l'acteur
    lui-même reste à choisir. Le mapping de noms de champs (`mapping_champs`) est
    injecté plutôt que codé en dur, pour ajuster à l'acteur réel choisi sans
    modification de code — voir APIFY_MAPPING_CHAMPS_DEFAUT."""

    def __init__(self, api_token: str, actor_id: str, mapping_champs: dict[str, str] | None = None):
        self.api_token = api_token
        self.actor_id = actor_id
        self.mapping = mapping_champs or APIFY_MAPPING_CHAMPS_DEFAUT

    def rechercher(self, mots_cles: list[str], since: datetime | None, limit: int) -> Iterator[OffreAgregateur]:
        url = f"https://api.apify.com/v2/acts/{self.actor_id}/run-sync-get-dataset-items"
        corps: dict = {"maxItems": limit}
        if mots_cles:
            corps["searchTerms"] = mots_cles  # nom de champ propre à l'acteur — à ajuster une fois choisi

        resp = requests.post(url, params={"token": self.api_token}, json=corps, timeout=120)
        resp.raise_for_status()

        for item in resp.json():
            offre = _normaliser_apify(item, self.mapping)
            if offre is not None:
                yield offre


# --- Sélection du fournisseur --------------------------------------------------


def fournisseur_depuis_env() -> FournisseurAgregateur | None:
    """Aucun fournisseur codé en dur ici (spec section 9bis) — choisi par variable
    d'environnement, absente tant qu'Alexandre n'a pas tranché entre TheirStack et
    Apify (voir docstring du module). Retourne None si non configuré : le
    connecteur reste silencieux plutôt que d'échouer (même principe que StubConnector
    — falkye/sources/base.py)."""
    nom = (os.environ.get("FALKYE_AGREGATEUR_RECRUTEMENT_FOURNISSEUR") or "").strip().lower()

    if nom == "theirstack":
        cle = os.environ.get("FALKYE_THEIRSTACK_API_KEY")
        if not cle:
            logger.warning("FALKYE_AGREGATEUR_RECRUTEMENT_FOURNISSEUR=theirstack sans FALKYE_THEIRSTACK_API_KEY.")
            return None
        return TheirStackProvider(api_key=cle)

    if nom == "apify":
        token = os.environ.get("FALKYE_APIFY_API_TOKEN")
        actor_id = os.environ.get("FALKYE_APIFY_ACTOR_ID")
        if not token or not actor_id:
            logger.warning(
                "FALKYE_AGREGATEUR_RECRUTEMENT_FOURNISSEUR=apify sans FALKYE_APIFY_API_TOKEN/FALKYE_APIFY_ACTOR_ID."
            )
            return None
        return ApifyActeurGeneriqueProvider(api_token=token, actor_id=actor_id)

    if nom:
        logger.warning("Fournisseur agrégateur recrutement inconnu : %s", nom)
    return None


class AgregateurRecrutementConnector(SourceConnector):
    """Connecteur générique — ne connaît QUE FournisseurAgregateur, jamais
    TheirStack ou Apify directement (même principe que
    falkye/sources/licences_municipales_communes.py pour Vancouver/Toronto)."""

    def __init__(self, source_def, fournisseur: FournisseurAgregateur | None = None, limit: int = 200):
        super().__init__(source_def)
        self._fournisseur_injecte = fournisseur
        self.limit = limit

    @property
    def fournisseur(self) -> FournisseurAgregateur | None:
        # Résolu paresseusement (pas dans __init__) pour que la configuration
        # d'environnement au moment du scan fasse foi, pas celle au chargement du
        # registre (utile pour les tests, qui injectent directement `fournisseur`).
        if self._fournisseur_injecte is not None:
            return self._fournisseur_injecte
        return fournisseur_depuis_env()

    def disponible(self) -> bool:
        return self.fournisseur is not None

    def detect(self, since: datetime | None, db_session) -> Iterator[RawSignal]:
        fournisseur = self.fournisseur
        if fournisseur is None:
            logger.info(
                "Agrégateur recrutement : aucun fournisseur configuré "
                "(FALKYE_AGREGATEUR_RECRUTEMENT_FOURNISSEUR) — aucun signal produit."
            )
            return

        # Recherche par mots-clés de transformation/implantation (même liste que
        # falkye/matching.py, le signal qualitatif Signal 3) plutôt qu'un
        # rapatriement complet du marché — un fournisseur payant facture au
        # volume, et c'est déjà la correspondance qualitative qui porte la plus
        # forte valeur de ce signal (spec section 7).
        for offre in fournisseur.rechercher(list(MOTS_CLES_TRANSFORMATION), since, self.limit):
            yield RawSignal(
                signal_type_id="recrutement_massif",
                nom_entreprise=offre.entreprise,
                detected_at=offre.date_publication or datetime.now(timezone.utc),
                source_ref=offre.source_ref,
                ville=offre.ville,
                region=offre.region,
                titre_ou_description=offre.titre,
                champs={
                    "titre_poste": offre.titre,
                    "description_offre": offre.description,
                    "url_offre": offre.url,
                },
            )


CONNECTOR_CLASS = AgregateurRecrutementConnector
