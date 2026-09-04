"""Connecteur Licences d'affaires — Ville de Vancouver (spec section 7, Signal
registre_corporatif — première source hors Québec pour ce signal après
Corporations Canada, priorité pancanadienne demandée par Alexandre).

Portail réel : opendata.vancouver.ca, plateforme Opendatasoft (PAS du CKAN,
contrairement à la plupart des autres sources de ce projet) — API v2.1
JSON standard, aucune authentification requise. Jeu de données
"business-licences", 205 329 lignes réelles au 2026-09-01, très à jour
(`extractdate` du jour même).

Champs réels confirmés : `businessname`, `businesstradename`, `status`
("Issued"/"Pending"/"Gone Out of Business"/"Inactive"/...), `issueddate`,
`expireddate`, `businesstype`, `unit`/`house`/`street`/`city`/`province`/
`postalcode`, `localarea`, `numberofemployees`, `licencenumber`,
`licencersn`. Filtré sur `status="Issued"` (167 962/205 329 lignes) — les
licences en attente, inactives ou d'entreprises fermées ne sont pas des
signaux de croissance.

CALIBRATION "NON NÉGOCIABLE" (voir sources.yaml:licences_affaires_municipales) —
DEUX filtres appliqués en cascade, aucun optionnel :
1. **Pas un simple renouvellement.** Découverte réelle : un NOUVEAU numéro de
   licence est attribué CHAQUE ANNÉE (le "folderyear" est encodé dans le
   numéro, ex. "26-258507" pour l'année 2026) et le jeu de données ne
   couvre qu'une fenêtre glissante de 3 ans (24/25/26 au 2026-09-01) — la
   simple présence/absence dans le fichier ne suffit PAS à distinguer un
   nouvel établissement d'un renouvellement d'une entreprise en place
   depuis des années. Un miroir local persistant
   (`LicenceMunicipaleEntry`, voir falkye/sources/
   licences_municipales_communes.py) accumule donc les entreprises+adresses
   déjà vues d'un scan à l'autre ; seule une combinaison JAMAIS vue produit
   une candidate. Même précaution "premier scan" que Corporations Canada :
   le tout premier scan peuple le miroir SANS produire de signal (sinon
   ~168 000 licences déjà anciennes seraient traitées comme "nouvelles").
2. **Pas un nouveau démarrage.** Vérification croisée avec Corporations
   Canada (`resolve_corp_federale_by_name`) — ne produit un signal que si le
   nom correspond avec confiance à une corporation fédérale déjà EXISTANTE.
   Exclut naturellement au passage les propriétaires individuels/entreprises
   individuelles (ex. licences affichées "(Prénom Nom)" dans le jeu de
   données réel — fréquent pour les praticiens de santé, thérapeutes, etc.)
   puisqu'un nom de personne ne correspond à aucune corporation.

LIMITE DE PAGINATION RÉELLE (Opendatasoft, pas propre à ce connecteur) :
`offset + limit <= 10000` par requête — au-delà, l'API refuse (confirmé).

REBRANCHÉ sur le moteur de diff générique (Chantier 1, suivi 2026-09-04).
`detect()` appelle désormais TOUJOURS `iter_licences(session, since=None)` —
`since` ignoré pour la collecte, même changement délibéré que pour
licences_toronto.py (voir sa docstring pour le raisonnement complet : une
fenêtre incrémentale comparée à l'état cumulatif ferait apparaître, à tort,
l'essentiel de l'historique comme "disparu" à chaque exécution). Limite
honnête PROPRE à Vancouver, contrairement à Toronto : le plafond de
pagination Opendatasoft (10 000) est BIEN EN DEÇÀ de la population réelle
(~168 000 licences actives) — l'instantané soumis au moteur n'est donc
JAMAIS complet ici, seulement les 10 000 licences les PLUS RÉCENTES
(`order_by` inversé en DESCENDANT pour ce cas — auparavant ascendant,
pertinent seulement pour un vrai scan fenêtré). La détection de disparition
reste donc structurellement AFFAIBLIE pour Vancouver (une vraie disparition
au-delà des 10 000 plus récentes ne sera jamais vue) — limite documentée,
pas corrigée ici (lever le plafond appartient au fournisseur de données, pas
à ce chantier).
"""
from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import datetime, timezone

import requests
from dateutil import parser as dateutil_parser

from falkye.diff_engine import LigneSnapshot, executer_diff, seuils_depuis_registre
from falkye.registry.loader import get_registry
from falkye.resolution import SEUIL_AMBIGUITE_ECART_MIN, SEUIL_RESOLUTION_CONFIANTE
from falkye.sources.base import RawSignal, SourceConnector
from falkye.sources.ckan_client import DEFAULT_USER_AGENT
from falkye.sources.corporations_canada import resolve_corp_federale_by_name
from falkye.sources.licences_municipales_communes import (
    CHAMPS_PERTINENTS_MUNIC,
    LicenceBrute,
    colonnes_vues_depuis_lignes,
    detecter_nouvelles_licences,
)

logger = logging.getLogger(__name__)

MUNICIPALITE = "Vancouver"
API_URL = "https://opendata.vancouver.ca/api/explore/v2.1/catalog/datasets/business-licences/records"
TAILLE_PAGE = 100
PLAFOND_OPENDATASOFT = 10_000  # offset + limit <= 10000, confirmé — voir docstring du module

_MAPPING_COLONNES_VANCOUVER = {
    "nom_entreprise": "businessname",
    "adresse": "street",  # colonne représentative — voir docstring du module
    "type_entreprise": "businesstype",
    "date_emission": "issueddate",
}


def _parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = dateutil_parser.parse(raw)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError):
        return None


def _composer_adresse(row: dict) -> str | None:
    parties = [
        str(row.get("unit") or "").strip(),
        str(row.get("house") or "").strip(),
        (row.get("street") or "").strip(),
        (row.get("city") or "").strip(),
        (row.get("province") or "").strip(),
    ]
    return ", ".join(p for p in parties if p) or None


def iter_licences(session: requests.Session, since: datetime | None) -> Iterator[dict]:
    """Pagine sur l'API Opendatasoft — filtrage par date fait CÔTÉ SERVEUR
    (`where`), même principe que datastore_search côté CKAN ailleurs dans ce
    projet. S'arrête au plafond de pagination de la plateforme (voir
    docstring du module) plutôt que d'échouer.

    Ordre de tri conditionnel : ASCENDANT pour un vrai scan fenêtré (`since`
    fourni — pagination stable et exhaustive DANS la fenêtre), DESCENDANT
    pour un instantané non fenêtré (`since=None`, le seul cas appelé par
    `detect()` depuis le chantier 1) — le plafond de 10 000 doit alors capter
    les licences les PLUS RÉCENTES, pas les plus anciennes."""
    clause = 'status="Issued"'
    if since:
        clause += f" and issueddate>=date'{since.strftime('%Y-%m-%dT%H:%M:%S')}'"
    direction = "asc" if since else "desc"

    offset = 0
    while offset + TAILLE_PAGE <= PLAFOND_OPENDATASOFT:
        params = {
            "where": clause,
            "order_by": f"issueddate {direction}, licencersn {direction}",  # ordre stable pour une pagination fiable
            "limit": TAILLE_PAGE,
            "offset": offset,
        }
        resp = session.get(API_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results") or []
        if not results:
            return

        yield from results
        offset += len(results)
        if len(results) < TAILLE_PAGE:
            return

    logger.warning(
        "Licences Vancouver: plafond de pagination Opendatasoft (%s lignes) atteint — "
        "des licences plus anciennes n'ont pas été récupérées. Utiliser une fenêtre "
        "`since` plus courte pour un scan complet.",
        PLAFOND_OPENDATASOFT,
    )


class LicencesVancouverConnector(SourceConnector):
    def detect(self, since: datetime | None, db_session) -> Iterator[RawSignal]:
        # `since` REÇU MAIS IGNORÉ pour la collecte (voir docstring du
        # module, Chantier 1) — conservé pour l'interface SourceConnector.
        session = requests.Session()
        session.headers.setdefault("User-Agent", DEFAULT_USER_AGENT)

        try:
            lignes_brutes = list(iter_licences(session, None))
        except requests.RequestException as exc:
            logger.warning("Licences Vancouver: échec de la récupération: %s", exc)
            return

        brutes_par_cle: dict[str, dict] = {}
        for row in lignes_brutes:
            nom = (row.get("businessname") or "").strip()
            if not nom:
                continue
            adresse = _composer_adresse(row)
            brute = LicenceBrute(
                nom=nom,
                adresse=adresse,
                type_entreprise=(row.get("businesstype") or "").strip() or None,
                identifiant_source=(row.get("licencenumber") or row.get("licencersn") or ""),
            )
            # une même entreprise+adresse peut apparaître plusieurs fois dans une même
            # page (révisions de licence) — on ne garde que la ligne la plus récente
            # pour le diff, `row` original conservé à part pour construire le signal.
            # MÊME clé que le moteur générique (cle_naturelle = nom+adresse pour
            # Vancouver, voir registry/sources.yaml) — pas une coïncidence.
            brutes_par_cle[f"{nom}|{adresse or ''}"] = {"brute": brute, "row": row}

        lignes_snapshot = [
            LigneSnapshot(
                cle=cle,
                champs={
                    "nom_entreprise": c["brute"].nom,
                    "adresse": c["brute"].adresse,
                    "type_entreprise": c["brute"].type_entreprise,
                    "date_emission": c["row"].get("issueddate"),
                },
            )
            for cle, c in brutes_par_cle.items()
        ]
        colonnes_vues = colonnes_vues_depuis_lignes(lignes_brutes, _MAPPING_COLONNES_VANCOUVER)

        registry = get_registry()
        source_def = registry.sources.get("licences_vancouver")
        seuils = seuils_depuis_registre(source_def.seuils_quarantaine) if source_def else None
        rapport = executer_diff(
            db_session, "licences_vancouver", lignes_snapshot, colonnes_vues, CHAMPS_PERTINENTS_MUNIC, seuils=seuils
        )
        if rapport.quarantaine:
            logger.warning(
                "Licences Vancouver: import mis en quarantaine (%s) — aucun signal produit. "
                "Voir `falkye quarantaine lister`.",
                rapport.motif_quarantaine.value if rapport.motif_quarantaine else None,
            )
            return

        # --- Filtre bespoke (inchangé) — APPLIQUÉ SEULEMENT si le moteur
        # générique confirme que ce run n'est pas en quarantaine. ---
        candidates = list(brutes_par_cle.values())
        nouvelles = detecter_nouvelles_licences(db_session, MUNICIPALITE, [c["brute"] for c in candidates])
        nouvelles_ids = {id(n) for n in nouvelles}
        # detecter_nouvelles_licences retourne les MÊMES objets LicenceBrute passés en
        # entrée (jamais des copies) — comparer par identité est donc fiable ici.

        for c in candidates:
            if id(c["brute"]) not in nouvelles_ids:
                continue
            brute, row = c["brute"], c["row"]

            matches = resolve_corp_federale_by_name(db_session, brute.nom, province="BC")
            if not matches:
                continue
            top = matches[0]
            second = matches[1].score if len(matches) > 1 else 0.0
            if not (
                top.score >= SEUIL_RESOLUTION_CONFIANTE
                and (top.score - second >= SEUIL_AMBIGUITE_ECART_MIN or len(matches) == 1)
            ):
                continue  # pas de correspondance confiante à une corporation existante — pas de signal

            date_emission = _parse_date(row.get("issueddate"))
            yield RawSignal(
                signal_type_id="registre_corporatif",
                nom_entreprise=brute.nom,
                detected_at=date_emission or datetime.now(timezone.utc),
                source_ref=f"licences_vancouver:{brute.identifiant_source}",
                adresse=brute.adresse,
                ville=(row.get("city") or "").strip() or None,
                region=(row.get("province") or "").strip() or None,
                secteur_activite=brute.type_entreprise,
                titre_ou_description=f"Nouvelle licence d'affaires — {brute.type_entreprise or 'type non précisé'}",
                champs={
                    "type_changement": "nouvel_etablissement",
                    "nom_demandeur": brute.nom,
                    "nom_commercial": row.get("businesstradename"),
                    "adresse_travaux": brute.adresse,
                    "type_entreprise": brute.type_entreprise,
                    "date_emission": row.get("issueddate"),
                    "nombre_employes": row.get("numberofemployees"),
                    "corporation_federale_correspondante": top.entry.numero_corporation,
                    "score_correspondance": round(top.score, 1),
                },
            )


CONNECTOR_CLASS = LicencesVancouverConnector
