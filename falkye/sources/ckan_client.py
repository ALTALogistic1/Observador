"""Client générique pour les portails de données ouvertes basés sur CKAN.

SEAO et REQ (donneesquebec.ca) et Guichet-Emplois (open.canada.ca) sont tous les
trois publiés via CKAN — ce client est partagé entre les trois connecteurs plutôt
que dupliqué, et découvre les ressources dynamiquement (API `package_show`) plutôt
que de coder en dur une URL de fichier qui deviendrait vite périmée.

Nécessite un accès réseau sortant vers le domaine du portail. Si le domaine n'est
pas dans la liste d'accès de l'environnement, les appels échouent avec une erreur
réseau explicite plutôt qu'un contenu simulé — voir docs/STATUT_RESEAU.md.
"""
from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

DONNEES_QUEBEC_BASE = "https://www.donneesquebec.ca"
OPEN_CANADA_BASE = "https://open.canada.ca/data"

CACHE_DIR = Path(os.environ.get("FALKYE_CACHE_DIR", "./cache"))

DEFAULT_USER_AGENT = os.environ.get(
    "FALKYE_USER_AGENT",
    "Falkye/0.1 (repereur d'entreprises en croissance; usage a but non lucratif)",
)


class CKANError(RuntimeError):
    """Erreur lors d'un appel au portail CKAN (réseau, format inattendu, etc.)."""


class CKANClient:
    def __init__(self, base_url: str, timeout: int = 60, session: requests.Session | None = None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", DEFAULT_USER_AGENT)

    def package_show(self, package_id: str) -> dict:
        """Retourne la fiche complète du jeu de données, incluant la liste des
        ressources (fichiers) disponibles, via l'API d'action CKAN."""
        url = f"{self.base_url}/api/3/action/package_show"
        try:
            resp = self.session.get(url, params={"id": package_id}, timeout=self.timeout)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise CKANError(f"Échec de l'appel CKAN package_show({package_id!r}) sur {url}: {exc}") from exc

        data = resp.json()
        if not data.get("success"):
            raise CKANError(f"CKAN a refusé package_show({package_id!r}): {data.get('error')}")
        return data["result"]

    def resources(
        self,
        package_id: str,
        format_filter: str | None = None,
        name_contains: str | None = None,
    ) -> list[dict]:
        """Liste les ressources d'un jeu de données, triées par date de dernière
        modification décroissante (les plus récentes en premier). `format_filter`
        (ex. "JSON", "CSV") et `name_contains` (sous-chaîne insensible à la casse
        dans le nom de la ressource) permettent de cibler les bons fichiers sans
        les coder en dur par nom exact."""
        pkg = self.package_show(package_id)
        resources = pkg.get("resources", [])

        if format_filter:
            resources = [r for r in resources if (r.get("format") or "").upper() == format_filter.upper()]
        if name_contains:
            needle = name_contains.lower()
            resources = [r for r in resources if needle in (r.get("name") or "").lower()]

        resources.sort(key=lambda r: r.get("last_modified") or r.get("created") or "", reverse=True)
        return resources

    def datastore_search(
        self,
        resource_id: str,
        filters: dict | None = None,
        q: str | None = None,
        sort: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """Interroge l'API Datastore CKAN (`datastore_search`) pour une ressource
        avec `datastore_active=True`, plutôt que de télécharger le fichier brut —
        indispensable pour les jeux de données pancanadiens dont le CSV complet
        pèse plusieurs centaines de mégaoctets à plusieurs gigaoctets (ex.
        subventions fédérales, contrats fédéraux : tout l'historique depuis
        ~2017). `filters` est un dict de correspondance exacte (ex.
        {"recipient_province": "QC"}), sérialisé en JSON comme l'exige l'API."""
        import json as _json

        url = f"{self.base_url}/api/3/action/datastore_search"
        params = {"resource_id": resource_id, "limit": limit, "offset": offset}
        if filters:
            params["filters"] = _json.dumps(filters)
        if q:
            params["q"] = q
        if sort:
            params["sort"] = sort

        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise CKANError(f"Échec de l'appel datastore_search sur {resource_id!r}: {exc}") from exc

        data = resp.json()
        if not data.get("success"):
            raise CKANError(f"CKAN a refusé datastore_search({resource_id!r}): {data.get('error')}")
        return data["result"]

    def download(self, resource: dict, force: bool = False) -> Path:
        """Télécharge une ressource en flux (pas tout en mémoire — certains fichiers
        REQ/SEAO peuvent être volumineux) vers le cache local, et retourne le chemin.
        Ne re-télécharge pas si déjà présent, sauf `force=True`."""
        url = resource["url"]
        digest = hashlib.sha256(url.encode()).hexdigest()[:16]
        suffix = Path(url.split("?")[0]).suffix or ".bin"
        dest = CACHE_DIR / f"{digest}{suffix}"

        if dest.exists() and not force:
            logger.info("Ressource déjà en cache: %s -> %s", url, dest)
            return dest

        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp_dest = dest.with_suffix(dest.suffix + ".part")
        try:
            with self.session.get(url, timeout=self.timeout, stream=True) as resp:
                resp.raise_for_status()
                with tmp_dest.open("wb") as f:
                    for chunk in resp.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            f.write(chunk)
        except requests.RequestException as exc:
            tmp_dest.unlink(missing_ok=True)
            raise CKANError(f"Échec du téléchargement de {url}: {exc}") from exc

        tmp_dest.rename(dest)
        logger.info("Téléchargé %s -> %s", url, dest)
        return dest
