"""Connecteur SEAO (Système électronique d'appel d'offres du Québec) — spec section
7, Signal 5.

Données ouvertes CKAN (donneesquebec.ca), fichiers JSON hebdomadaires/mensuels
(hebdo_YYYYMMDD_YYYYMMDD.json / mensuel_YYYYMMDD_YYYYMMDD.json) au format inspiré de
l'Open Contracting Data Standard (OCDS) depuis mars 2021 — releases contenant des
"awards" (contrats attribués), chacun avec un ou plusieurs fournisseurs (adjudicataires).

**STRUCTURE RÉELLE CONFIRMÉE le 2026-09-13**, sur `hebdo_20260831_20260906.json`
(4 750 releases, 4 127 attributions) téléchargé depuis Données Québec. Ce qui suit
est mesuré sur ce fichier, pas déduit du standard :

    items[].classification            93,6 %   schéma UNSPSC, 1 242 codes distincts
    items[].additionalClassifications 29,3 %
    items[].description               93,6 %
    buyer.id                         100,0 %
    tender.description                 0,0 %   <-- jamais présent
    fournisseur retrouvé dans parties  100,0 % (4 127/4 127)
      … avec une adresse                99,9 %
      … avec une VILLE (locality)       87,7 %
    award.status                      4 125 `active`, 2 `cancelled`

**Deux corrections que cette mesure impose.** *(a)* La classification est portée par
**l'ITEM**, jamais par le tender — `tender.classification` n'existe pas dans le vrai
fichier. *(b)* `tender.description` est TOUJOURS vide : la description sommaire des
besoins est `items[].description`. Le champ capté jusqu'ici sous le nom
`description_tender` ne contenait donc rien, dans 100 % des cas.

**Et le registre demandait déjà ce qui manquait.** `registry/sources.yaml:seao`
déclare `adresse_entreprise_adjudicataire` et `secteur_nature_contrat` parmi les
champs pertinents — le connecteur n'en livrait aucun des deux. *Ce n'est pas une
exigence neuve : c'est une exigence non tenue.*

Si un fichier futur diverge, `_extraire_awards` lève une erreur explicite plutôt que
de produire des signaux silencieusement incorrects.
"""
from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterator
from datetime import datetime, timezone

from dateutil import parser as dateutil_parser

from falkye.sources.base import RawSignal, SourceConnector
from falkye.sources.ckan_client import DONNEES_QUEBEC_BASE, CKANClient

logger = logging.getLogger(__name__)

SEAO_PACKAGE_ID = "systeme-electronique-dappel-doffres-seao"

_FILENAME_DATE_RANGE = re.compile(r"(\d{8})_(\d{8})")


def _parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = dateutil_parser.parse(raw)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError):
        return None


def _resource_covers(resource: dict, since: datetime | None) -> bool:
    if since is None:
        return True
    match = _FILENAME_DATE_RANGE.search(resource.get("name", "") or resource.get("url", ""))
    if not match:
        return True  # nom non daté : on ne peut pas filtrer, on l'inclut par prudence
    _start, end = match.groups()
    end_dt = datetime.strptime(end, "%Y%m%d").replace(tzinfo=timezone.utc)
    return end_dt >= since


def _buyer_name(release: dict) -> str | None:
    buyer = release.get("buyer") or {}
    if buyer.get("name"):
        return buyer["name"]
    for party in release.get("parties", []):
        if "buyer" in (party.get("roles") or []):
            return party.get("name")
    return None


def source_ref_pour(release: dict, award: dict) -> str:
    """La clé de déduplication d'une attribution — **séparée pour être empruntée**.

    `outils/reprise_champs_seao.py` doit retrouver en base le signal qui correspond
    à une attribution du fichier. **S'il recalculait la clé de son côté, il
    apparierait sa propre copie** : une divergence d'un caractère ne raterait pas
    quelques signaux, elle les raterait TOUS, et le rapport dirait « aucun signal
    trouvé » au lieu de « la clé a changé ». *Même règle que `requete_nom_exact` et
    `neq_retenu` : une fonction du moteur s'emprunte, jamais ne se recopie.*
    """
    return f"seao:{release.get('ocid', release.get('id', ''))}:{award.get('id', '')}"


def _classifications(release: dict) -> list[dict]:
    """Les classifications normalisées de l'avis — TOUTES, sans en élire une.

    **Portées par `items[].classification`, jamais par le tender** *(mesuré le
    2026-09-13 : `tender.classification` n'existe pas dans le vrai fichier)*. Une
    release peut porter plusieurs items, donc plusieurs codes.

    **Aucun « code principal » n'est désigné ici, et c'est délibéré.** Élire un code
    parmi plusieurs serait déjà une interprétation, et la correspondance
    code → sphère est une décision de produit qui n'est pas prise *(charte, règle 5)*.
    Le connecteur livre ce que la source dit; la règle viendra au chantier 22.
    """
    vues: list[dict] = []
    for item in (release.get("tender") or {}).get("items") or []:
        for classification in [item.get("classification")] + list(
            item.get("additionalClassifications") or []
        ):
            if not classification or not classification.get("id"):
                continue
            entree = {
                "scheme": classification.get("scheme"),
                "code": classification.get("id"),
                "libelle": classification.get("description"),
            }
            if entree not in vues:
                vues.append(entree)
    return vues


def _descriptions_besoins(release: dict) -> list[str]:
    """La description sommaire des besoins — `items[].description`.

    *Le champ `tender.description` capté jusqu'au 2026-09-13 était vide dans 100 %
    des releases mesurées : ce n'est pas là qu'elle vit.*
    """
    return [
        item["description"]
        for item in ((release.get("tender") or {}).get("items") or [])
        if item.get("description")
    ]


def _partie_du_fournisseur(release: dict, supplier: dict) -> dict:
    """La fiche `parties` du fournisseur, retrouvée par son `id`.

    **C'est là que vit son adresse** — le bloc `suppliers[]` ne porte qu'un nom et un
    identifiant. Mesuré le 2026-09-13 : les 4 127 fournisseurs de la semaine sont tous
    retrouvés, 99,9 % portent une adresse et **87,7 % une ville**.

    *Le registre déclare `adresse_entreprise_adjudicataire` depuis toujours; le
    connecteur ne la livrait pas.*
    """
    identifiant = supplier.get("id")
    if not identifiant:
        return {}
    for partie in release.get("parties") or []:
        if partie.get("id") == identifiant:
            return partie
    return {}


def _extraire_awards(data) -> Iterator[tuple[dict, dict]]:
    """Retourne des paires (release, award) pour chaque contrat attribué trouvé."""
    if isinstance(data, dict) and "releases" in data:
        releases = data["releases"]
    elif isinstance(data, list):
        releases = data
    else:
        raise ValueError(
            "Structure JSON SEAO inattendue (ni {'releases': [...]}, ni liste de "
            f"releases). Clés de premier niveau reçues: "
            f"{list(data.keys()) if isinstance(data, dict) else type(data)}"
        )

    for release in releases:
        for award in release.get("awards", []) or []:
            yield release, award


class SEAOConnector(SourceConnector):
    def detect(self, since: datetime | None, db_session) -> Iterator[RawSignal]:
        client = CKANClient(DONNEES_QUEBEC_BASE)
        resources = client.resources(SEAO_PACKAGE_ID, format_filter="JSON")
        if not resources:
            logger.warning("SEAO: aucune ressource JSON trouvée sur CKAN")
            return

        cibles = [r for r in resources if _resource_covers(r, since)]
        if not cibles:
            cibles = resources[:1]  # au minimum le plus récent

        for resource in cibles:
            path = client.download(resource)
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            for release, award in _extraire_awards(data):
                for supplier in award.get("suppliers", []) or []:
                    nom = (supplier.get("name") or "").strip()
                    if not nom:
                        continue

                    date_attribution = _parse_date(award.get("date")) or _parse_date(
                        release.get("date")
                    )
                    if since and date_attribution and date_attribution < since:
                        continue

                    value = award.get("value") or {}
                    montant = value.get("amount")
                    adresse_fournisseur = (
                        _partie_du_fournisseur(release, supplier).get("address") or {}
                    )

                    yield RawSignal(
                        signal_type_id="appel_offres",
                        nom_entreprise=nom,
                        detected_at=date_attribution or datetime.now(timezone.utc),
                        source_ref=source_ref_pour(release, award),
                        valeur_associee=float(montant) if montant is not None else None,
                        titre_ou_description=(release.get("tender") or {}).get("title"),
                        # ⚠️ `ville`/`adresse` NE SONT PAS encore promues au RawSignal,
                        # et c'est une décision d'ordre, pas un oubli : promouvoir la
                        # ville change le chemin de RÉSOLUTION (+5 au score, départage
                        # entre deux entrées du REQ), et cette bascule attend la mesure
                        # de `outils/apport_ville.py` — décision d'Alexandre du
                        # 2026-09-13, « lance-le avant de toucher à quoi que ce soit ».
                        # Le champ est capté ici pour que la mesure porte sur du réel;
                        # la promotion tient en deux lignes le jour où elle est décidée.
                        champs={
                            "donneur_ordre": _buyer_name(release),
                            # 100 % des releases mesurées en portent un. Le donneur
                            # d'ouvrage n'est pas une entité du produit (registre) —
                            # son identifiant est capté pour le jour où il le sera.
                            "donneur_ordre_id": (release.get("buyer") or {}).get("id"),
                            "valeur_contrat": montant,
                            "devise": value.get("currency"),
                            "date_attribution": award.get("date"),
                            "statut_attribution": award.get("status"),
                            # `secteur_nature_contrat` et `adresse_entreprise_
                            # adjudicataire` sont les noms DÉCLARÉS au registre
                            # (sources.yaml:seao.champs_pertinents) — repris tels
                            # quels plutôt que renommés ici, pour qu'un champ déclaré
                            # et un champ livré portent le même nom.
                            "secteur_nature_contrat": _classifications(release),
                            "adresse_entreprise_adjudicataire": {
                                "adresse": adresse_fournisseur.get("streetAddress"),
                                "ville": adresse_fournisseur.get("locality"),
                                "region": adresse_fournisseur.get("region"),
                                "code_postal": adresse_fournisseur.get("postalCode"),
                            }
                            if adresse_fournisseur
                            else None,
                            # Remplace `description_tender`, vide dans 100 % des
                            # releases mesurées : la description des besoins est
                            # portée par les items.
                            "description_besoins": _descriptions_besoins(release),
                        },
                    )


CONNECTOR_CLASS = SEAOConnector
