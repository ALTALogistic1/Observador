"""Connecteur Divulgation proactive des contrats fédéraux (spec section 7,
Signal 5) — équivalent pancanadien du SEAO, contrats de plus de 10 000$ accordés
par les ministères fédéraux.

ACCÈS RÉEL CONFIRMÉ le 2026-08-31 : jeu de données CKAN
d8f85d91-7dec-4fd1-8055-483b77225d8b sur open.canada.ca, ressource "Contracts
over $10,000". Fichier CSV brut ~640 Mo (tout l'historique fédéral) —
`datastore_active=True`, donc interrogé via l'API Datastore CKAN comme pour les
subventions fédérales (falkye/sources/subventions_federales.py), pas
téléchargé en entier.
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

CONTRATS_PACKAGE_ID = "d8f85d91-7dec-4fd1-8055-483b77225d8b"
_RESOURCE_NAME = "Contracts over $10,000"


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
    """La clé de déduplication d'un contrat — **un seul endroit**.

    Elle identifie le signal à l'ingestion ET dit au parcours par publication ce qu'on
    a déjà vu. Écrite deux fois, une divergence d'un caractère ferait tout reparcourir
    à chaque cycle sans jamais rien reconnaître.
    """
    return f"contrats_federaux:{rec.get('reference_number')}"


def _find_resource_id(client: CKANClient) -> str:
    resources = client.resources(CONTRATS_PACKAGE_ID, format_filter="CSV")
    for r in resources:
        if r.get("name") == _RESOURCE_NAME and r.get("datastore_active"):
            return r["id"]
    raise RuntimeError(
        f"Ressource {_RESOURCE_NAME!r} introuvable ou pas indexée dans le Datastore "
        f"(package {CONTRATS_PACKAGE_ID!r}) — le jeu de données a peut-être changé."
    )


class ContratsFederauxConnector(SourceConnector):
    def __init__(self, source_def, limit: int | None = 500):
        super().__init__(source_def)
        self.limit = limit

    def detect(self, since: datetime | None, db_session) -> Iterator[RawSignal]:
        client = CKANClient(OPEN_CANADA_BASE)
        try:
            resource_id = _find_resource_id(client)
        except RuntimeError as exc:
            logger.warning("Contrats fédéraux: %s", exc)
            return

        # **L'axe de fraîcheur n'est PAS la date du contrat** — bascule du 2026-09-14,
        # et cette source-ci est le cas qui l'a démontré le plus nettement.
        #
        # Le tri par `contract_date desc` mettait en tête DEUX dates FUTURES —
        # 2026-12-01 et 2026-09-26 — qui passaient la fenêtre et produisaient les deux
        # SEULS signaux de la source; la troisième ligne, datée du 2026-07-23,
        # déclenchait le `return`. Sur les soixante premiers enregistrements du tri :
        # deux futurs, ZÉRO dans la fenêtre de trente jours, cinquante-huit plus
        # anciens. Les deux signaux en base étaient exactement les deux valeurs
        # aberrantes de la source.
        #
        # Voir falkye/sources/fraicheur_datastore.py pour l'axe retenu et sa réserve.
        for rec in parcourir_par_publication(
            client,
            resource_id,
            source_id="contrats_federaux",
            db_session=db_session,
            construire_ref=source_ref_pour,
            limite=self.limit,
        ):
            nom = (rec.get("vendor_name") or "").strip()
            if not nom:
                continue

            date_contrat = _parse_date(rec.get("contract_date"))
            # **Une date de contrat postérieure à aujourd'hui est une erreur de
            # saisie, et la source le prouve elle-même.** Vérifié le 2026-09-14 sur
            # les deux cas réels : celui daté du 2026-12-01 porte
            # `contract_period_start = 2026-01-12` (le jour et le mois transposés) et
            # `reporting_period = 2025-2026-Q3`; celui du 2026-09-26 porte
            # `contract_period_start = 2026-02-01` et un rapport de Q4 2025-2026. **Un
            # rapport trimestriel ne peut pas décrire un contrat attribué après la fin
            # du trimestre.**
            #
            # On ne corrige pas la date — on refuse d'en faire un signal. *Un contrat
            # réellement à venir entrerait le jour où la source le date correctement;
            # une aberration, jamais.*
            if date_contrat and date_contrat > datetime.now(timezone.utc):
                logger.info(
                    "Contrats fédéraux : contrat daté du futur (%s, période débutant "
                    "le %s) — écarté comme erreur de saisie.",
                    rec.get("contract_date"), rec.get("contract_period_start"),
                )
                continue

            # Valeur finale = valeur d'origine + modifications (si connues),
            # sinon la valeur de contrat rapportée directement.
            valeur = _parse_float(rec.get("contract_value")) or _parse_float(
                rec.get("original_value")
            )

            yield RawSignal(
                signal_type_id="appel_offres",
                nom_entreprise=nom,
                detected_at=date_contrat or datetime.now(timezone.utc),
                source_ref=source_ref_pour(rec),
                valeur_associee=valeur,
                titre_ou_description=rec.get("description_fr") or rec.get("description_en"),
                champs={
                    "donneur_ordre": rec.get("buyer_name") or rec.get("owner_org_title"),
                    "ministere": rec.get("owner_org_title"),
                    "valeur_contrat": valeur,
                    "valeur_originale": _parse_float(rec.get("original_value")),
                    "date_attribution": rec.get("contract_date"),
                    "code_bien_service": rec.get("commodity_code"),
                    # Le code d'objet économique — 100 % de remplissage, 47 valeurs
                    # distinctes (mesuré le 2026-09-14) : l'équivalent fédéral de la
                    # classification normalisée du SEAO, capté ici pour que la
                    # correspondance code → sphère ait sa matière (registre).
                    "objet_economique": rec.get("economic_object_code"),
                },
            )


CONNECTOR_CLASS = ContratsFederauxConnector
