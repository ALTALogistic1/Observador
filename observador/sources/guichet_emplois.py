"""Connecteur Guichet-Emplois (Job Bank Canada) — spec section 7, Signal 3.

Historique : RETIRÉE de la Phase 1 active le 2026-08-31 (le fichier en vrac
ne contient aucun nom d'employeur — voir docs/STATUT_RESEAU.md). RÉACTIVÉE
le 2026-09-01 après une nouvelle piste d'Alexandre : les pages de détail
d'offre individuelle sur guichetemplois.gc.ca AFFICHENT le nom de
l'employeur, même si le fichier en vrac ne le donne pas. Confirmé avec de
vraies données :
  - `ID WIC Lieu emploi` (une vraie colonne du fichier) correspond exactement
    à l'identifiant utilisé dans
    `https://www.guichetemplois.gc.ca/jobsearch/jobposting/{id}`.
  - Sur une offre encore active, l'employeur est dans un `<h2>` à l'intérieur
    d'un conteneur `class="job-posting-details-employer-wrapper"`, avec le
    secteur d'activité juste à côté — voir `_extraire_employeur`.
  - LIMITE RÉELLE CONFIRMÉE (pas un bogue) : le fichier en vrac a un décalage
    de publication d'environ un mois, et les offres individuelles ont une
    durée de vie plus courte que ce décalage — validé deux fois sur des
    échantillons réels du fichier de juillet 2026 (le plus récent disponible
    début septembre) : 5/5 puis 4/4 identifiants retournent HTTP 410 Gone,
    avec redirection vers `jobsearch/jobpostingexpired` (page sans bloc
    employeur, pas une erreur d'identifiant). Décision d'Alexandre : garder
    l'architecture fichier-en-vrac (cohérente avec toutes les autres
    sources), accepter une couverture PARTIELLE plutôt que de basculer vers
    un scraping des résultats de recherche en direct (risque de blocage
    anti-bot, architecture différente de toutes les autres sources). Une
    offre expirée ne produit simplement aucun signal — comme un
    `non_trouve` ailleurs dans le pipeline, pas une erreur, pas une donnée
    inventée. Validation de bout en bout (15 offres Québec tentées, limite
    de test) : 0 signal, cohérent avec la contrainte ci-dessus, pas un
    connecteur cassé — voir docs/STATUT_RESEAU.md pour le détail.
  - FLAKINESS RÉSEAU DISTINCTE DE L'EXPIRATION (trouvée en validant) : le
    tunnel TLS vers ce site se réinitialise occasionnellement en cours de
    scan (`SSL_ERROR_SYSCALL` / `RemoteDisconnected`, y compris deux fois de
    suite sur un même identifiant), sans rapport avec l'état de l'offre —
    `recuperer_employeur` réessaie donc jusqu'à `_TENTATIVES_CONNEXION` fois
    sur une erreur RÉSEAU uniquement (jamais sur un vrai statut HTTP, pour ne
    pas confondre flakiness et expiration réelle).

COÛT RÉEL DE LA CONSULTATION INDIVIDUELLE : `Crawl-delay: 5` dans le
robots.txt du site (confirmé, aucun chemin interdit) — chaque offre coûte
donc au moins 5 secondes. Bornage obligatoire (`limit`, défaut 100 —
~8-9 minutes par exécution) et filtre géographique par défaut
(`province="Québec"`, ~10 000 offres/mois sur ~52 000 nationalement) pour
qu'un scan reste praticable — voir le même principe déjà appliqué à
subventions_federales.

Fichier en vrac : encodage UTF-16, colonnes séparées par TABULATION (pas
UTF-8/virgule comme la première version du connecteur le supposait — bogue
mineur corrigé le 2026-08-31 en même temps que la découverte bloquante).
Deuxième bogue trouvé en validant CETTE version (2026-09-01) : les alias de
`COLUMN_ALIASES` étaient écrits avec des ESPACES ("id wic") alors que
`resolve_columns` normalise les en-têtes avec des UNDERSCORES (voir
column_mapping.py et la même convention dans eimt.py) — un alias multi-mots
à espaces ne matchait donc jamais, corrigé en réécrivant tous les alias avec
des underscores.
"""
from __future__ import annotations

import csv
import logging
import time
from collections.abc import Iterator
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateutil_parser

from observador.sources.base import RawSignal, SourceConnector
from observador.sources.ckan_client import DEFAULT_USER_AGENT, OPEN_CANADA_BASE, CKANClient
from observador.sources.column_mapping import resolve_columns

logger = logging.getLogger(__name__)

GUICHET_EMPLOIS_PACKAGE_ID = "ea639e28-c0fc-48bf-b5dd-b8899bd43072"

CRAWL_DELAY_SECONDES = 5.0
URL_OFFRE_TEMPLATE = "https://www.guichetemplois.gc.ca/jobsearch/jobposting/{id}"

# Alias confirmés contre les vraies en-têtes du fichier réel (2026-09-01) — voir
# docstring du module. "employeur" n'est PAS une colonne du fichier (c'est tout
# le point de ce connecteur : le récupérer via la page de détail individuelle).
# IMPORTANT : `resolve_columns` normalise les en-têtes avec des UNDERSCORES
# (jamais des espaces) — voir observador/sources/column_mapping.py et la
# même convention dans eimt.py. Un alias à espaces ne matcherait jamais un
# en-tête multi-mots (bogue trouvé et corrigé avant la première validation).
COLUMN_ALIASES: dict[str, list[str]] = {
    "id_offre": ["id_wic", "job_id", "id_offre"],
    "titre_poste": ["appellation_d_emploi", "job_title", "titre_poste", "titre"],
    "cnp": ["code_cnp_2021", "code_cnp_2016", "noc_code", "noc", "cnp"],
    "nombre_postes": ["nombre_de_postes_vacants", "vacancies", "nb_postes"],
    "remuneration": ["detail_remuneration", "salary", "salaire"],
    "ville": ["ville", "city"],
    "province": ["provinces_territoires", "province", "region"],
    "date_publication": ["date_initiale_affichage_de_l_offre_d_emploi", "date_posted", "date_publication"],
}


def _parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = dateutil_parser.parse(raw)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError):
        return None


def _parse_int(raw: str | None) -> int | None:
    if not raw:
        return None
    try:
        return int(float(str(raw).replace(",", "").strip()))
    except ValueError:
        return None


def _extraire_employeur(html: str) -> dict | None:
    """Extrait le nom de l'employeur (et, en prime, le secteur d'activité) du
    bloc `job-posting-details-employer-wrapper` d'une page de détail d'offre
    — voir docstring du module pour la découverte réelle. Retourne None si le
    bloc est absent (page d'erreur, structure changée) plutôt que de deviner."""
    soup = BeautifulSoup(html, "html.parser")
    wrapper = soup.find(class_="job-posting-details-employer-wrapper")
    if wrapper is None:
        return None
    h2 = wrapper.find("h2")
    nom = h2.get_text(strip=True) if h2 else None
    if not nom:
        return None

    secteur = None
    premier_li = wrapper.find("li")
    if premier_li is not None:
        span = premier_li.find("span", class_="details")
        if span:
            secteur = span.get_text(strip=True) or None

    return {"nom": nom, "secteur": secteur}


_TENTATIVES_CONNEXION = 3  # voir docstring de recuperer_employeur


def recuperer_employeur(session: requests.Session, job_id: str) -> dict | None:
    """Récupère le nom de l'employeur pour UNE offre, via sa page de détail.
    Retourne None pour toute offre inaccessible (expirée = 410, retirée = 404) —
    silencieux, jamais une exception qui interromprait le scan pour les autres
    offres (même principe que enrichir_entreprise).

    Des tentatives de reconnexion (jusqu'à `_TENTATIVES_CONNEXION`) sur une
    erreur RÉSEAU (pas un statut HTTP) : découvert en validant contre de
    vraies données — le tunnel TLS vers ce site se réinitialise
    occasionnellement (`SSL_ERROR_SYSCALL` / `RemoteDisconnected`), y compris
    deux fois de suite sur le même identifiant lors de la validation. Sans ce
    ré-essai, cette flakiness réseau se confondrait silencieusement avec une
    vraie offre expirée (qui, elle, répond normalement par une redirection
    vers `jobpostingexpired`, jamais par une erreur de connexion)."""
    url = URL_OFFRE_TEMPLATE.format(id=job_id)
    for tentative in range(1, _TENTATIVES_CONNEXION + 1):
        try:
            resp = session.get(url, timeout=15)
            break
        except requests.RequestException as exc:
            if tentative >= _TENTATIVES_CONNEXION:
                logger.info("Guichet-Emplois: échec de requête pour l'offre %s: %s", job_id, exc)
                return None
            time.sleep(tentative)  # backoff court : laisse le temps au tunnel TLS de se rétablir
    if resp.status_code != 200:
        return None  # 410 Gone (offre expirée) le cas le plus fréquent, pas une erreur à logger
    return _extraire_employeur(resp.text)


class GuichetEmploisConnector(SourceConnector):
    def __init__(self, source_def, limit: int | None = 100, province: str | None = "Québec"):
        super().__init__(source_def)
        # Bornage obligatoire : chaque offre coûte au moins CRAWL_DELAY_SECONDES
        # (voir docstring du module) — un fichier national sans borne prendrait
        # des heures. `province` restreint au foyer Québec de la Phase 1 (même
        # principe que subventions_federales) ; province=None couvre tout le
        # Canada pour qui est prêt à en payer le temps.
        self.limit = limit
        self.province = province

    def detect(self, since: datetime | None, db_session) -> Iterator[RawSignal]:
        client = CKANClient(OPEN_CANADA_BASE)
        resources = client.resources(GUICHET_EMPLOIS_PACKAGE_ID, format_filter="CSV")
        if not resources:
            logger.warning("Guichet-Emplois: aucune ressource CSV trouvée sur CKAN")
            return

        # Un seul fichier (le plus récent) : la contrainte réelle n'est pas le
        # nombre de mois couverts mais l'expiration des offres individuelles
        # (voir docstring du module) — remonter plus loin dans l'historique
        # n'aiderait pas, ces offres-là sont encore plus susceptibles d'avoir
        # déjà expiré.
        resource = resources[0]
        path = client.download(resource)

        session = requests.Session()
        session.headers.setdefault("User-Agent", DEFAULT_USER_AGENT)

        with open(path, encoding="utf-16", errors="replace", newline="") as f:
            reader = csv.DictReader(f, delimiter="\t")
            columns = resolve_columns(reader.fieldnames or [], COLUMN_ALIASES)

            n_tentees = 0
            for row in reader:
                if self.limit is not None and n_tentees >= self.limit:
                    break

                if self.province:
                    province_ligne = (row.get(columns["province"]) or "").strip()
                    if province_ligne != self.province:
                        continue

                job_id = (row.get(columns["id_offre"]) or "").strip()
                titre = (row.get(columns["titre_poste"]) or "").strip()
                if not job_id or not titre:
                    continue

                date_pub = _parse_date(row.get(columns["date_publication"]))
                if since and date_pub and date_pub < since:
                    continue

                n_tentees += 1  # compte chaque tentative réelle (chaque appel réseau coûte le crawl-delay)
                employeur = recuperer_employeur(session, job_id)
                time.sleep(CRAWL_DELAY_SECONDES)
                if employeur is None:
                    continue  # offre expirée/retirée — pas de signal, rien à deviner

                yield RawSignal(
                    signal_type_id="recrutement_massif",
                    nom_entreprise=employeur["nom"],
                    detected_at=date_pub or datetime.now(timezone.utc),
                    source_ref=f"guichet_emplois:{job_id}",
                    ville=(row.get(columns["ville"]) or "").strip() or None,
                    region=(row.get(columns["province"]) or "").strip() or None,
                    secteur_activite=employeur.get("secteur"),
                    titre_ou_description=titre,
                    valeur_associee=_parse_int(row.get(columns["nombre_postes"])),
                    champs={
                        "titre_poste": titre,
                        "cnp": row.get(columns["cnp"]),
                        "nombre_postes": _parse_int(row.get(columns["nombre_postes"])),
                        "remuneration": row.get(columns["remuneration"]),
                        "date_publication": row.get(columns["date_publication"]),
                        "url_offre": URL_OFFRE_TEMPLATE.format(id=job_id),
                    },
                )


CONNECTOR_CLASS = GuichetEmploisConnector
