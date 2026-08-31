"""Enrichissement contextuel via le site web du prospect — spec section 10.

Dernière étape du pipeline avant notification : trouve le site officiel, fait un
ratissage léger et ciblé (pas un crawl complet) des pages prioritaires, extrait un
contexte structuré, et sert de filtre d'exclusion si le site contredit le signal
détecté (fermeture, inactivité). Respecte robots.txt et une limite de fréquence —
jamais de sollicitation agressive d'un site.

Le fournisseur de recherche (pour trouver l'URL officielle quand elle n'est pas déjà
connue) est pluggable via OBSERVADOR_SEARCH_PROVIDER — par défaut une recherche
DuckDuckGo HTML sans clé d'API. Ce domaine (html.duckduckgo.com) n'est pas dans la
liste réseau demandée dans docs/STATUT_RESEAU.md pour la Phase 1 — à ajouter si ce
module est activé en environnement cloud restreint.
"""
from __future__ import annotations

import logging
import os
import re
import time
import urllib.robotparser
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from observador.sources.ckan_client import DEFAULT_USER_AGENT

logger = logging.getLogger(__name__)

TIMEOUT = 10
MAX_PAGES = 6
CRAWL_DELAY_SECONDS = 1.0

PAGES_PRIORITAIRES_MOTS = {
    "accueil": [""],
    "a_propos": ["about", "a-propos", "apropos", "qui-sommes-nous", "notre-entreprise"],
    "services": ["services", "produits", "products", "solutions"],
    "carrieres": ["carrieres", "careers", "emplois", "jobs", "recrutement"],
    "actualites": ["nouvelles", "actualites", "news", "blog"],
    "contact": ["contact", "coordonnees"],
}

MOTS_INACTIVITE = [
    "ferme definitivement",
    "fermeture definitive",
    "permanently closed",
    "cette entreprise a ferme",
    "domain for sale",
    "domaine a vendre",
    "site en construction",
    "coming soon",
    "cette entreprise est en liquidation",
    "avis de dissolution",
]

MOTS_EXPANSION = [
    "nouvelle usine",
    "nouveau bureau",
    "expansion",
    "agrandissement",
    "nouvelle succursale",
    "croissance rapide",
    "ouverture d une nouvelle",
    "nous recrutons",
    "grande nouvelle",
]

RE_TELEPHONE = re.compile(r"(\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")
RE_COURRIEL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
RE_EMPLOYES = re.compile(r"(\d{1,5})\s*(\+)?\s*(employ[ée]s|employees|employés)", re.IGNORECASE)


@dataclass
class EnrichmentResult:
    site_web: str | None = None
    trouve: bool = False
    indique_inactivite: bool = False
    description: str | None = None
    coordonnees: dict = field(default_factory=dict)
    indices_taille: dict = field(default_factory=dict)
    mentions_expansion: list[str] = field(default_factory=list)
    offres_emploi: list[str] = field(default_factory=list)
    erreurs: list[str] = field(default_factory=list)


class SearchProvider:
    def search(self, query: str, max_results: int = 5) -> list[dict]:
        raise NotImplementedError


class DuckDuckGoHTMLProvider(SearchProvider):
    """Recherche sans clé d'API, via l'endpoint HTML de DuckDuckGo (pas d'API
    officielle sans frais — accepté comme méthode légère et publique)."""

    URL = "https://html.duckduckgo.com/html/"

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", DEFAULT_USER_AGENT)

    def search(self, query: str, max_results: int = 5) -> list[dict]:
        try:
            resp = self.session.post(self.URL, data={"q": query}, timeout=TIMEOUT)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Recherche DuckDuckGo échouée pour %r: %s", query, exc)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for a in soup.select("a.result__a")[:max_results]:
            href = a.get("href")
            if href:
                results.append({"title": a.get_text(strip=True), "url": href})
        return results


def _get_search_provider() -> SearchProvider:
    provider = os.environ.get("OBSERVADOR_SEARCH_PROVIDER", "duckduckgo")
    if provider == "duckduckgo":
        return DuckDuckGoHTMLProvider()
    raise ValueError(f"Fournisseur de recherche inconnu: {provider!r}")


def _normaliser_ascii(texte: str) -> str:
    return re.sub(r"\s+", " ", texte.lower())


def _robots_autorise(url: str, session: requests.Session) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = urllib.robotparser.RobotFileParser()
    try:
        resp = session.get(robots_url, timeout=TIMEOUT)
        if resp.status_code >= 400:
            return True  # pas de robots.txt = pas de restriction connue
        rp.parse(resp.text.splitlines())
    except requests.RequestException:
        return True  # on ne bloque pas sur une erreur réseau de robots.txt lui-même
    return rp.can_fetch(DEFAULT_USER_AGENT, url)


def rechercher_site_officiel(nom_entreprise: str, ville: str | None = None) -> str | None:
    provider = _get_search_provider()
    query = f"{nom_entreprise} {ville or ''} site officiel entreprise".strip()
    results = provider.search(query, max_results=5)
    for r in results:
        url = r.get("url") or ""
        domaine = urlparse(url).netloc.lower()
        # Écarte les résultats évidemment non pertinents (réseaux sociaux, annuaires
        # génériques) plutôt que de retenir le premier lien venu.
        if any(bloque in domaine for bloque in ["linkedin.", "facebook.", "yellowpages.", "google."]):
            continue
        return url
    return None


def _pages_a_visiter(page_accueil_url: str, liens_internes: list[str]) -> list[str]:
    base_netloc = urlparse(page_accueil_url).netloc
    retenues = [page_accueil_url]
    for categorie, mots in PAGES_PRIORITAIRES_MOTS.items():
        if categorie == "accueil":
            continue
        for lien in liens_internes:
            if urlparse(lien).netloc != base_netloc:
                continue
            chemin = urlparse(lien).path.lower()
            if any(mot in chemin for mot in mots):
                retenues.append(lien)
                break
        if len(retenues) >= MAX_PAGES:
            break
    seen = set()
    result = []
    for r in retenues:
        if r not in seen:
            seen.add(r)
            result.append(r)
    return result[:MAX_PAGES]


def enrichir_entreprise(
    nom_entreprise: str, ville: str | None = None, site_web_connu: str | None = None
) -> EnrichmentResult:
    result = EnrichmentResult()
    session = requests.Session()
    session.headers.setdefault("User-Agent", DEFAULT_USER_AGENT)

    site = site_web_connu or rechercher_site_officiel(nom_entreprise, ville)
    if not site:
        # Absence de site : PAS un motif d'exclusion (spec section 6).
        return result

    result.site_web = site

    if not _robots_autorise(site, session):
        result.erreurs.append("robots.txt interdit le ratissage de ce site")
        result.trouve = True
        return result

    try:
        resp = session.get(site, timeout=TIMEOUT)
    except requests.RequestException as exc:
        result.erreurs.append(f"Site injoignable: {exc}")
        return result  # domaine possiblement expiré : pas assez pour conclure à l'inactivité

    if resp.status_code >= 400:
        result.erreurs.append(f"HTTP {resp.status_code} sur la page d'accueil")
        return result

    result.trouve = True
    soup = BeautifulSoup(resp.text, "html.parser")
    liens_internes = [urljoin(site, a.get("href")) for a in soup.select("a[href]")]
    pages = _pages_a_visiter(site, liens_internes)

    texte_complet = []
    for i, page_url in enumerate(pages):
        if i > 0:
            time.sleep(CRAWL_DELAY_SECONDS)
            try:
                page_resp = session.get(page_url, timeout=TIMEOUT)
                page_soup = BeautifulSoup(page_resp.text, "html.parser")
            except requests.RequestException:
                continue
        else:
            page_resp, page_soup = resp, soup

        texte = page_soup.get_text(" ", strip=True)
        texte_complet.append(texte)

        if "carrieres" in page_url.lower() or "emplois" in page_url.lower() or "jobs" in page_url.lower():
            offres = [a.get_text(strip=True) for a in page_soup.select("a") if a.get_text(strip=True)]
            result.offres_emploi.extend(offres[:20])

    texte_norm = _normaliser_ascii(" ".join(texte_complet))
    texte_norm = re.sub(r"[éèêë]", "e", texte_norm)
    texte_norm = re.sub(r"[àâ]", "a", texte_norm)

    result.indique_inactivite = any(mot in texte_norm for mot in MOTS_INACTIVITE)
    result.mentions_expansion = [mot for mot in MOTS_EXPANSION if mot in texte_norm]

    tel_match = RE_TELEPHONE.search(" ".join(texte_complet))
    mail_match = RE_COURRIEL.search(" ".join(texte_complet))
    result.coordonnees = {
        "telephone": tel_match.group(0) if tel_match else None,
        "courriel": mail_match.group(0) if mail_match else None,
    }

    emp_match = RE_EMPLOYES.search(" ".join(texte_complet))
    if emp_match:
        result.indices_taille["nombre_employes_mentionne"] = emp_match.group(1)

    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        result.description = meta_desc["content"].strip()[:500]

    return result
