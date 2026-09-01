"""Connecteur Licences d'affaires — Ville de Toronto (spec section 7, Signal
registre_corporatif — priorité pancanadienne, 2e ville après Vancouver).

Découverte réelle (2026-09-01) : `open.toronto.ca` (autorisé) n'est que la
façade web du portail — son `/api/3/action/*` retourne 404, ce n'est pas la
racine de l'API CKAN. Le vrai backend est un domaine CKAN distinct
(`ckan0.cf.opendata.inter.prod-toronto.ca`, confirmé fonctionnel une fois
autorisé) — même schéma de séparation portail/fichier que Montréal pour les
permis de construction.

Jeu de données "Municipal Licensing and Standards - Business Licences and
Permits", ressource `169e90ba-3ae0-43dd-8b2f-919e87002f50` (`datastore_active:
true` — interrogée via l'API Datastore CKAN, pas un téléchargement de fichier
brut, même principe que subventions_federales/contrats_federaux). 159 647
lignes réelles, historique complet depuis 1946 — schéma documenté dans le
jeu de données lui-même (chaque champ CKAN porte une description officielle).

DIFFÉRENCE STRUCTURANTE avec Vancouver : le numéro de licence de Toronto est
un identifiant PERSISTANT (confirmé : 500 lignes échantillonnées, 0 doublon
de `Licence No.`), pas réattribué chaque année — contrairement à Vancouver.
MAIS le calibrage "pas un simple renouvellement" reste nécessaire quand même :
une même entreprise peut obtenir plusieurs numéros de licence successifs au
fil des décennies (confirmé sur un exemple réel : une entreprise avec 4
licences distinctes entre 2002 et 2019, chacune annulée puis remplacée) —
sans le miroir local, chaque nouveau numéro de licence pour une entreprise
DÉJÀ connue serait à tort traité comme "un nouvel établissement". Réutilise
donc le même mécanisme commun que Vancouver
(falkye/sources/licences_municipales_communes.py:detecter_nouvelles_licences,
même miroir `LicenceMunicipaleEntry`, aucune modification nécessaire) — avec
la même précaution "premier scan ne produit aucun signal" (sinon 159 647
licences historiques seraient toutes traitées comme "nouvelles").

Champs réels confirmés : `Licence No.`, `Category` (type de licence),
`Operating Name` (nom commercial), `Client Name` (nom légal — utilisé comme
`nom_entreprise`, plus fiable que `Operating Name` pour la vérification
croisée Corporations Canada), `Issued`, `Cancel Date` (licences annulées
exclues — équivalent du filtre `status="Issued"` de Vancouver), `Licence
Address Line 1/2/3`, `Ward`, `Endorsements`. Quirk de qualité de données :
les champs texte vides sont parfois la CHAÎNE littérale `"None"` (pas un
JSON `null`) — voir `_nettoyer`.

Même règle de calibration NON NÉGOCIABLE que Vancouver (deux filtres en
cascade) — voir sources.yaml:licences_vancouver pour le détail complet,
applicable ici sans changement.
"""
from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import datetime, timezone

import requests
from dateutil import parser as dateutil_parser

from falkye.resolution import SEUIL_AMBIGUITE_ECART_MIN, SEUIL_RESOLUTION_CONFIANTE
from falkye.sources.base import RawSignal, SourceConnector
from falkye.sources.ckan_client import DEFAULT_USER_AGENT
from falkye.sources.corporations_canada import resolve_corp_federale_by_name
from falkye.sources.licences_municipales_communes import LicenceBrute, detecter_nouvelles_licences

logger = logging.getLogger(__name__)

MUNICIPALITE = "Toronto"
CKAN_BASE = "https://ckan0.cf.opendata.inter.prod-toronto.ca"
RESOURCE_ID = "169e90ba-3ae0-43dd-8b2f-919e87002f50"
TAILLE_PAGE = 1000


def _nettoyer(val) -> str | None:
    """Le portail encode parfois un champ texte vide par la chaîne littérale
    "None" plutôt qu'un JSON null — voir docstring du module."""
    if val is None:
        return None
    val = str(val).strip()
    return val if val and val != "None" else None


def _parse_date(raw) -> datetime | None:
    raw = _nettoyer(raw)
    if not raw:
        return None
    try:
        dt = dateutil_parser.parse(raw)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError):
        return None


def _composer_adresse(row: dict) -> str | None:
    parties = [_nettoyer(row.get(f"Licence Address Line {i}")) for i in (1, 2, 3)]
    return ", ".join(p for p in parties if p) or None


def _ville_province(row: dict) -> tuple[str | None, str | None]:
    """"Licence Address Line 2" est au format "TORONTO, ON" dans les vraies
    données — séparé en (ville, province) quand le format est reconnu."""
    ligne2 = _nettoyer(row.get("Licence Address Line 2"))
    if not ligne2 or "," not in ligne2:
        return ligne2, None
    ville, province = ligne2.rsplit(",", 1)
    return ville.strip() or None, province.strip() or None


def iter_licences(session: requests.Session, since: datetime | None) -> Iterator[dict]:
    """Pagine sur l'API Datastore CKAN, triée par date d'émission décroissante
    (nulls en dernier) — permet un arrêt anticipé dès qu'on dépasse `since`,
    même principe que le tri stable utilisé ailleurs dans ce projet pour la
    pagination. Filtre les licences annulées et les lignes vides
    (`"** Class record not on file"`, un artefact réel du jeu de données)."""
    url = f"{CKAN_BASE}/api/3/action/datastore_search"
    offset = 0
    while True:
        params = {
            "resource_id": RESOURCE_ID,
            "sort": "Issued desc nulls last",
            "limit": TAILLE_PAGE,
            "offset": offset,
        }
        resp = session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            raise RuntimeError(f"CKAN Toronto a refusé datastore_search: {data.get('error')}")

        records = data["result"].get("records") or []
        if not records:
            return

        for row in records:
            issued = _parse_date(row.get("Issued"))
            if since and issued and issued < since:
                return  # trié par date décroissante — tout le reste est plus vieux
            if _nettoyer(row.get("Cancel Date")):
                continue  # licence annulée — pas un établissement actif
            yield row

        offset += len(records)
        if len(records) < TAILLE_PAGE:
            return


class LicencesTorontoConnector(SourceConnector):
    def detect(self, since: datetime | None, db_session) -> Iterator[RawSignal]:
        session = requests.Session()
        session.headers.setdefault("User-Agent", DEFAULT_USER_AGENT)

        try:
            lignes = list(iter_licences(session, since))
        except (requests.RequestException, RuntimeError) as exc:
            logger.warning("Licences Toronto: échec de la récupération: %s", exc)
            return

        candidats: dict[str, dict] = {}
        for row in lignes:
            nom = _nettoyer(row.get("Client Name"))
            numero = _nettoyer(row.get("Licence No."))
            if not nom or not numero:
                continue
            adresse = _composer_adresse(row)
            brute = LicenceBrute(
                nom=nom,
                adresse=adresse,
                type_entreprise=_nettoyer(row.get("Category")),
                identifiant_source=numero,
            )
            candidats[f"{nom}|{adresse or ''}"] = {"brute": brute, "row": row}

        entries = list(candidats.values())
        nouvelles = detecter_nouvelles_licences(db_session, MUNICIPALITE, [c["brute"] for c in entries])
        nouvelles_ids = {id(n) for n in nouvelles}

        for c in entries:
            if id(c["brute"]) not in nouvelles_ids:
                continue
            brute, row = c["brute"], c["row"]

            ville, province = _ville_province(row)
            matches = resolve_corp_federale_by_name(db_session, brute.nom, province=province)
            if not matches:
                continue
            top = matches[0]
            second = matches[1].score if len(matches) > 1 else 0.0
            if not (
                top.score >= SEUIL_RESOLUTION_CONFIANTE
                and (top.score - second >= SEUIL_AMBIGUITE_ECART_MIN or len(matches) == 1)
            ):
                continue

            date_emission = _parse_date(row.get("Issued"))
            yield RawSignal(
                signal_type_id="registre_corporatif",
                nom_entreprise=brute.nom,
                detected_at=date_emission or datetime.now(timezone.utc),
                source_ref=f"licences_toronto:{brute.identifiant_source}",
                adresse=brute.adresse,
                ville=ville,
                region=province,
                secteur_activite=brute.type_entreprise,
                titre_ou_description=f"Nouvelle licence d'affaires — {brute.type_entreprise or 'type non précisé'}",
                champs={
                    "type_changement": "nouvel_etablissement",
                    "nom_demandeur": brute.nom,
                    "nom_commercial": _nettoyer(row.get("Operating Name")),
                    "adresse_travaux": brute.adresse,
                    "type_entreprise": brute.type_entreprise,
                    "date_emission": row.get("Issued"),
                    "corporation_federale_correspondante": top.entry.numero_corporation,
                    "score_correspondance": round(top.score, 1),
                },
            )


CONNECTOR_CLASS = LicencesTorontoConnector
