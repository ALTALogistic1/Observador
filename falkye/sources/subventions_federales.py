"""Connecteur Subventions et contributions gouvernementales — divulgation
proactive fédérale (spec section 7, Signal 2). Couvre tous les ministères
fédéraux (absorbe DEC, PARI-CNRC, CanExport, FedDev Ontario, FedNor, APECA,
PrairiesCan, PacifiCan comme des filtres sur cette même source, pas des sources
séparées).

ACCÈS RÉEL CONFIRMÉ le 2026-08-31 : jeu de données CKAN
432527ab-7aac-45b5-81d6-7597107a7013 sur open.canada.ca, ressource "Proactive
Disclosure - Grants and Contributions". Le fichier CSV brut pèse ~2,3 Go (tout
l'historique fédéral depuis ~2017) — ingérable en entier dans une session.
`datastore_active=True` sur cette ressource : on interroge donc l'API Datastore
CKAN (`datastore_search`, triée par date décroissante, avec pagination) plutôt
que de télécharger le fichier — toujours des "données ouvertes gratuites" au
sens de la spec, juste un accès ciblé plutôt qu'un fichier brut complet.
"""
from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import datetime, timezone

from dateutil import parser as dateutil_parser

from falkye.sources.base import RawSignal, SourceConnector
from falkye.sources.ckan_client import OPEN_CANADA_BASE, CKANClient
from falkye.sources.fraicheur_datastore import parcourir_par_publication

logger = logging.getLogger(__name__)

SUBVENTIONS_PACKAGE_ID = "432527ab-7aac-45b5-81d6-7597107a7013"
_RESOURCE_NAME = "Proactive Disclosure - Grants and Contributions"


def _parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = dateutil_parser.parse(raw)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError):
        return None


def _parse_float(raw) -> float | None:
    if raw is None or raw == "":
        return None
    try:
        return float(str(raw).replace(",", "").strip())
    except ValueError:
        return None


def source_ref_pour(rec: dict) -> str:
    """La clé de déduplication d'une entente — **un seul endroit**.

    Elle sert désormais à deux choses : identifier le signal à l'ingestion, et dire au
    parcours par publication ce qu'on a DÉJÀ vu *(falkye/sources/fraicheur_datastore.py)*.
    **Écrite deux fois, une divergence d'un caractère ferait tout reparcourir à chaque
    cycle sans jamais rien reconnaître** — et le connecteur paraîtrait simplement lent.
    """
    return f"subventions_federales:{rec.get('ref_number')}:{rec.get('amendment_number')}"


def _find_resource_id(client: CKANClient) -> str:
    resources = client.resources(SUBVENTIONS_PACKAGE_ID, format_filter="CSV")
    for r in resources:
        if r.get("name") == _RESOURCE_NAME and r.get("datastore_active"):
            return r["id"]
    raise RuntimeError(
        f"Ressource {_RESOURCE_NAME!r} introuvable ou pas indexée dans le Datastore "
        f"(package {SUBVENTIONS_PACKAGE_ID!r}) — le jeu de données a peut-être changé."
    )


class SubventionsFederalesConnector(SourceConnector):
    """`region` sur cette source est "Canada" (spec) ; `province` restreint la
    requête pour la Phase 1 (foyer Québec) sans que ce soit une limite de
    l'architecture — passer province=None couvre tout le Canada."""

    def __init__(self, source_def, limit: int | None = 500, province: str | None = "QC"):
        super().__init__(source_def)
        self.limit = limit
        self.province = province

    def detect(self, since: datetime | None, db_session) -> Iterator[RawSignal]:
        client = CKANClient(OPEN_CANADA_BASE)
        try:
            resource_id = _find_resource_id(client)
        except RuntimeError as exc:
            logger.warning("Subventions fédérales: %s", exc)
            return

        filters = {"recipient_province": self.province} if self.province else None

        # **L'axe de fraîcheur n'est PAS la date d'entente** — bascule du 2026-09-14.
        # La divulgation proactive publie des ententes commencées des mois plus tôt :
        # la plus récente date de début québécoise était le 2026-08-01, et une fenêtre
        # de 30 jours faisait sortir le connecteur au PREMIER enregistrement. Zéro
        # signal, trois secondes, un succès. Voir falkye/sources/fraicheur_datastore.py
        # pour l'axe retenu et sa réserve.
        #
        # `since` n'est donc plus un filtre d'ingestion. Il reste le paramètre du
        # cycle, et c'est la DÉDUPLICATION qui borne le travail.
        for rec in parcourir_par_publication(
            client,
            resource_id,
            source_id="subventions_federales",
            db_session=db_session,
            construire_ref=source_ref_pour,
            filters=filters,
            limite=self.limit,
        ):
            nom = (rec.get("recipient_legal_name") or "").strip()
            if not nom:
                continue

            date_signature = _parse_date(rec.get("agreement_start_date"))
            # Une date d'entente POSTÉRIEURE à aujourd'hui contredit la source
            # elle-même — deux cas réels ont été démontés champ par champ chez les
            # contrats fédéraux le 2026-09-14, `reporting_period` et
            # `contract_period_start` contredisant tous deux la date annoncée. On ne
            # corrige pas la source : on refuse d'en faire un signal, et l'entente
            # entrera le jour où elle se corrigera.
            if date_signature and date_signature > datetime.now(timezone.utc):
                logger.info(
                    "Subventions fédérales : entente datée du futur (%s) — écartée.",
                    rec.get("agreement_start_date"),
                )
                continue

            montant = _parse_float(rec.get("agreement_value"))
            titre = rec.get("agreement_title_fr") or rec.get("agreement_title_en")
            programme = rec.get("prog_name_fr") or rec.get("prog_name_en")

            yield RawSignal(
                signal_type_id="financement_expansion",
                nom_entreprise=nom,
                detected_at=date_signature or datetime.now(timezone.utc),
                source_ref=source_ref_pour(rec),
                ville=rec.get("recipient_city"),
                region=rec.get("recipient_province"),
                valeur_associee=montant,
                titre_ou_description=titre or programme,
                champs={
                    "nature_bien": programme,  # réutilisé par le scoring (nature du programme)
                    "programme": programme,
                    "ministere": rec.get("owner_org_title"),
                    "description": rec.get("description_fr") or rec.get("description_en"),
                    "type_entente": rec.get("agreement_type"),  # G=subvention, C=contribution, O=autre
                    "date_signature": rec.get("agreement_start_date"),
                },
            )

CONNECTOR_CLASS = SubventionsFederalesConnector
