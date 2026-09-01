"""Connecteur Permis de construction — Ville de Laval (spec section 7, Signal 4).

Découverte réelle (2026-09-01) : jeu de données CKAN publié sur le portail
Données Québec (`www.donneesquebec.ca`, package `permis-de-construction`) —
le MÊME domaine déjà autorisé pour REQ et SEAO, aucun nouveau domaine à
demander. 172 168 lignes couvrant 1991 à 2026-03-31.

IMPORTANT — identité captée : le seul champ qui identifie une entreprise est
`ENTREPRENEUR`, l'entreprise de CONSTRUCTION qui EXÉCUTE les travaux — pas le
propriétaire du bâtiment qui s'agrandit. Aucun champ demandeur/propriétaire
n'existe dans ce jeu de données (confirmé par inspection des 19 colonnes
réelles). C'est un signal légitime mais différent de l'intention initiale de
la spec ("nouveaux locaux, agrandissement" pour le propriétaire qui grandit) :
un entrepreneur en construction avec un permis de valeur/nature significative
est lui-même un prospect plausible pour un fournisseur B2B au secteur de la
construction, mais ce N'EST PAS un signal que le propriétaire du bâtiment est
en croissance. Retenu quand même (couverture honnête plutôt que source
abandonnée, même principe que Guichet-Emplois), documenté clairement plutôt
que présenté comme autre chose. Couverture partielle : `ENTREPRENEUR` est vide
sur environ 69% des lignes (69,3 % dans l'échantillon complet du 2026-09-01 —
chantiers résidentiels mineurs surtout, souvent exécutés par le propriétaire
lui-même) — aucun signal produit dans ces cas, pas de nom deviné.

`COUT_PERMIS` est le coût DU PERMIS (souvent un tarif administratif
forfaitaire, ex. plusieurs lignes à 270,00$ pour des travaux visiblement très
différents), PAS le coût estimé des travaux — pas fiable comme proxy direct
de l'ampleur du chantier, donc conservé dans `champs` pour référence mais
volontairement PAS utilisé par le score (voir
observador/scoring.py:_score_permis_construction, qui se base sur la nature
des travaux — les 4 catégories réelles confirmées : "Permis de construction -
nouvelle"/"- amélioration", "Certificat d'autorisation"/"d'occupation").

FRAÎCHEUR : fichier republié occasionnellement (confirmé via les métadonnées
CKAN), pas en continu — dernière publication confirmée le 2026-03-31. Un scan
avec fenêtre glissante courte (30-60 jours) peut donc légitimement retourner 0
nouveau signal entre deux republications — pas un bogue, même catégorie de
constat que pour subventions_federales (voir docs/STATUT_RESEAU.md).

DÉDOUBLONNAGE : un même NO_PERMIS peut apparaître sur plusieurs lignes (un
permis couvrant plusieurs adresses contiguës, ex. un projet de 5 unités
attenantes) — `source_ref` utilise volontairement NO_PERMIS seul (pas
l'adresse), donc `observador.engine.ingest_source` collapse naturellement ces
lignes en UN SEUL signal par permis (le même projet, pas 5 notifications
répétées pour la même entreprise). Confirmé avec de vraies données le
2026-09-01 : 53 953 lignes avec ENTREPRENEUR non vide, 49 694 permis
distincts après dédoublonnage.
"""
from __future__ import annotations

import csv
import logging
from collections.abc import Iterator
from datetime import datetime, timezone

from dateutil import parser as dateutil_parser

from observador.sources.base import RawSignal, SourceConnector
from observador.sources.ckan_client import DONNEES_QUEBEC_BASE, CKANClient

logger = logging.getLogger(__name__)

PACKAGE_ID = "permis-de-construction"


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
        return float(str(raw).replace(",", "").replace("$", "").strip())
    except ValueError:
        return None


class PermisConstructionLavalConnector(SourceConnector):
    def detect(self, since: datetime | None, db_session) -> Iterator[RawSignal]:
        client = CKANClient(DONNEES_QUEBEC_BASE)
        resources = client.resources(PACKAGE_ID, format_filter="CSV")
        if not resources:
            logger.warning("Permis de construction (Laval): aucune ressource CSV trouvée sur CKAN")
            return

        path = client.download(resources[0])

        with open(path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                entrepreneur = (row.get("ENTREPRENEUR") or "").strip()
                if not entrepreneur:
                    continue  # pas de nom -> pas de signal, voir docstring du module

                date_emission = _parse_date(row.get("DATE_EMISSION"))
                if since and date_emission and date_emission < since:
                    continue

                no_permis = (row.get("NO_PERMIS") or "").strip()
                if not no_permis:
                    continue

                nature = (row.get("TYPE_PERMIS_DESCR") or "").strip()
                adresse = (row.get("ADRESSE") or "").strip() or None
                ville = (row.get("EXVILLE_DESCR") or "").strip() or None

                yield RawSignal(
                    signal_type_id="registre_corporatif",
                    nom_entreprise=entrepreneur,
                    detected_at=date_emission or datetime.now(timezone.utc),
                    source_ref=f"permis_construction_laval:{no_permis}",
                    adresse=adresse,
                    ville=ville,
                    region="Laval",
                    titre_ou_description=f"{nature} — {adresse}" if adresse else nature,
                    champs={
                        "type_changement": "permis_construction",
                        "nom_demandeur": entrepreneur,  # voir docstring : entrepreneur, pas propriétaire
                        "adresse_travaux": adresse,
                        "nature_travaux": nature,
                        "valeur_permis": _parse_float(row.get("COUT_PERMIS")),  # coût du PERMIS, pas des travaux
                        "date_emission": row.get("DATE_EMISSION"),
                    },
                )


CONNECTOR_CLASS = PermisConstructionLavalConnector
