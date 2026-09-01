"""Connecteur Contrats publics attribués — Nouvelle-Écosse (spec section 7,
Signal "appel_offres" — équivalent SEAO hors Québec).

Découverte réelle (2026-09-01), en réponse à la recherche d'équivalents
provinciaux à SEAO demandée par Alexandre : contrairement aux portails de
soumission de la plupart des autres provinces (BC Bid, Alberta Purchasing
Connection, Ontario Tenders Portal, SaskTenders — tous confirmés sans flux de
données public), la Nouvelle-Écosse publie ses contrats attribués via son
portail de données ouvertes Socrata (data.novascotia.ca), jeu de données
"Awarded Public Tenders" (id `m6ps-8j6u`) — API JSON standard (SoQL), aucune
authentification requise.

Champs réels confirmés (33 290 lignes au 2026-09-01, avril 2010 à aujourd'hui,
très à jour — dernière attribution le 2026-08-17) : `tender_id`, `entity`
(organisme acheteur), `goods`/`service`/`construction` (indicateurs Y/N, pas
mutuellement exclusifs), `tender_start_date`, `tender_close_date`,
`tender_description`, `awarded_date`, `awarded_amount`, `vendor` (nom de
l'entreprise adjudicataire — TOUJOURS un contrat déjà attribué : 0 ligne avec
`awarded_date` nul dans l'échantillon complet). Couverture d'identité quasi
totale : 33 267/33 290 lignes (99,9%) ont un vendeur ET une date
d'attribution non vides.

`awarded_amount` vaut parfois "0" (867/33 290 lignes, ~2,6%) — traité comme
valeur INCONNUE (`None`), pas un contrat réellement gratuit, pour ne pas
fausser le palier de score vers le bas avec une fausse certitude.

Aucun filtrage de bruit nécessaire au niveau du connecteur — même principe
que SEAO/contrats_federaux (spec, `regle_calibration` du registre) : chaque
ligne est déjà un contrat RÉELLEMENT attribué, pas une intention ou une
soumission en cours.

DÉDOUBLONNAGE — deux découvertes réelles en validant (voir `detect`) :
`tender_id` seul n'identifie PAS une ligne de façon unique (un même appel
d'offres attribue parfois à plusieurs fournisseurs distincts, ex. un
contrat à commandes), donc `source_ref` inclut le vendeur. Mais même
(tender_id, vendor) n'est pas toujours unique : une même entreprise peut
apparaître plusieurs fois sous le même tender_id avec des montants
différents (plusieurs éléments de portée) — dans ce cas, collapser en un
seul signal via le dédoublonnage par `source_ref` du moteur est le
comportement voulu (même entreprise, même attribution, pas une raison de
notifier deux fois).

`robots.txt` du portail : `Crawl-delay: 1`, aucun chemin `/resource/`
(l'API SoQL) interdit — seuls des chemins de navigation web (`/browse`,
`/catalog`, etc.) le sont, non utilisés ici.
"""
from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import datetime, timezone

import requests
from dateutil import parser as dateutil_parser

from falkye.sources.base import RawSignal, SourceConnector
from falkye.sources.ckan_client import DEFAULT_USER_AGENT

logger = logging.getLogger(__name__)

SOCRATA_BASE = "https://data.novascotia.ca"
RESOURCE_ID = "m6ps-8j6u"
TAILLE_PAGE = 1000


def _parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = dateutil_parser.parse(raw)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError):
        return None


def _parse_float(raw: str | None) -> float | None:
    if not raw:
        return None
    try:
        valeur = float(str(raw).replace(",", "").strip())
    except ValueError:
        return None
    return valeur if valeur > 0 else None  # "0" = valeur inconnue, pas un contrat gratuit — voir docstring


def _nature_contrat(row: dict) -> str:
    natures = [
        nom
        for flag, nom in (("goods", "biens"), ("service", "services"), ("construction", "construction"))
        if (row.get(flag) or "").strip().upper() == "Y"
    ]
    return "/".join(natures) if natures else "non précisé"


def iter_contrats(session: requests.Session, since: datetime | None) -> Iterator[dict]:
    """Pagine sur l'API SoQL — filtrage par date fait CÔTÉ SERVEUR (`$where`)
    plutôt que téléchargé puis filtré en Python, même principe que
    datastore_search côté CKAN ailleurs dans ce projet."""
    url = f"{SOCRATA_BASE}/resource/{RESOURCE_ID}.json"
    where = None
    if since:
        where = f"awarded_date >= '{since.strftime('%Y-%m-%dT%H:%M:%S')}'"

    offset = 0
    while True:
        params = {
            "$order": "awarded_date ASC, tender_id ASC",  # ordre stable, requis pour une pagination fiable
            "$limit": TAILLE_PAGE,
            "$offset": offset,
        }
        if where:
            params["$where"] = where

        resp = session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        page = resp.json()
        if not page:
            break

        yield from page
        offset += len(page)
        if len(page) < TAILLE_PAGE:
            break


class ContratsNouvelleEcosseConnector(SourceConnector):
    def detect(self, since: datetime | None, db_session) -> Iterator[RawSignal]:
        session = requests.Session()
        session.headers.setdefault("User-Agent", DEFAULT_USER_AGENT)

        try:
            lignes = list(iter_contrats(session, since))
        except requests.RequestException as exc:
            logger.warning("Contrats Nouvelle-Écosse: échec de la récupération: %s", exc)
            return

        for row in lignes:
            vendor = (row.get("vendor") or "").strip()
            tender_id = (row.get("tender_id") or "").strip()
            if not vendor or not tender_id:
                continue  # pas d'identité ou pas d'identifiant — rien à notifier, pas de nom deviné

            date_attribution = _parse_date(row.get("awarded_date"))

            yield RawSignal(
                signal_type_id="appel_offres",
                nom_entreprise=vendor,
                detected_at=date_attribution or datetime.now(timezone.utc),
                # tender_id SEUL n'est PAS unique par ligne : un même appel d'offres
                # attribue parfois à PLUSIEURS fournisseurs distincts (contrats à
                # commandes, lots multiples) — confirmé sur de vraies données (ex.
                # tender_id "MET24-04" attribué à la fois à "Miller Waste Systems
                # Inc" et "Royal Environmental Inc"). source_ref inclut donc le
                # vendeur, sinon le dédoublonnage par source_ref du moteur
                # (falkye.engine.ingest_source) écraserait silencieusement le
                # signal d'une VRAIE entreprise distincte.
                #
                # (tender_id, vendor) N'EST PAS NON PLUS TOUJOURS unique — une même
                # entreprise peut apparaître plusieurs fois sous le même tender_id
                # avec des montants différents (plusieurs éléments de portée dans
                # un même contrat) : confirmé sur de vraies données (ex.
                # "Brilun Construction Limited" deux fois sous "Doc1458897982",
                # 3 337 913$ puis 4 543 873$). Dans CE cas, collapser en UN SEUL
                # signal est le comportement voulu — même principe que les permis
                # de Laval (même entreprise, même tender, pas 2 notifications pour
                # ce qui est le même événement d'attribution).
                source_ref=f"contrats_nouvelle_ecosse:{tender_id}:{vendor}",
                region="Nouvelle-Écosse",
                valeur_associee=_parse_float(row.get("awarded_amount")),
                titre_ou_description=row.get("tender_description"),
                champs={
                    "donneur_ordre": row.get("entity"),
                    "valeur_contrat": row.get("awarded_amount"),
                    "date_attribution": row.get("awarded_date"),
                    "nature_contrat": _nature_contrat(row),
                    "date_ouverture_soumission": row.get("tender_start_date"),
                    "date_fermeture_soumission": row.get("tender_close_date"),
                },
            )


CONNECTOR_CLASS = ContratsNouvelleEcosseConnector
