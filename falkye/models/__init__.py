"""Regroupe l'import de tous les modèles pour que Base.metadata les connaisse
(voir falkye/db.py:init_db)."""
from falkye.models.base import Base  # noqa: F401
from falkye.models.client_cible import ClientCible  # noqa: F401
from falkye.models.client_cible_synonyme import ClientCibleSynonyme  # noqa: F401
from falkye.models.company import Company  # noqa: F401
from falkye.models.corp_federale_entry import CorporationFederaleEntry  # noqa: F401
from falkye.models.crm_connection import CrmConnection  # noqa: F401
from falkye.models.crm_sync_record import CrmSyncRecord  # noqa: F401
from falkye.models.diagnostic_journal import DiagnosticJournal, TypeDiagnostic  # noqa: F401
from falkye.models.expansion_interprovinciale import LienInterprovincial  # noqa: F401
from falkye.models.licence_municipale_entry import LicenceMunicipaleEntry  # noqa: F401
from falkye.models.notification import (  # noqa: F401
    Notification,
    NotificationDelivery,
    NotificationSignal,
    PeriodicSummary,
)
from falkye.models.ponderation_personnalisee import PonderationPersonnalisee  # noqa: F401
from falkye.models.profile import Profile, ProfileNeed  # noqa: F401
from falkye.models.profile_need_client_cible import ProfileNeedClientCible  # noqa: F401
from falkye.models.profile_need_sphere import ProfileNeedSphere  # noqa: F401
from falkye.models.req_entry import REQEntry  # noqa: F401
from falkye.models.req_etablissement_entry import REQEtablissementEntry  # noqa: F401
from falkye.models.retroaction_pertinence import RetroactionPertinence  # noqa: F401
from falkye.models.run_log import SourceRunLog  # noqa: F401
from falkye.models.session_auth import SessionAuth  # noqa: F401
from falkye.models.signal import Signal  # noqa: F401
from falkye.models.sous_compte import SousCompte  # noqa: F401
from falkye.models.sphere import Sphere  # noqa: F401
from falkye.models.sphere_synonyme import SphereSynonyme  # noqa: F401
from falkye.models.statut_suivi import StatutSuivi  # noqa: F401
from falkye.models.subscription import Subscription  # noqa: F401

__all__ = [
    "Base",
    "ClientCible",
    "ClientCibleSynonyme",
    "Company",
    "CorporationFederaleEntry",
    "CrmConnection",
    "CrmSyncRecord",
    "DiagnosticJournal",
    "TypeDiagnostic",
    "LicenceMunicipaleEntry",
    "LienInterprovincial",
    "Notification",
    "NotificationDelivery",
    "NotificationSignal",
    "PeriodicSummary",
    "PonderationPersonnalisee",
    "Profile",
    "ProfileNeed",
    "ProfileNeedClientCible",
    "ProfileNeedSphere",
    "REQEntry",
    "REQEtablissementEntry",
    "RetroactionPertinence",
    "SessionAuth",
    "SourceRunLog",
    "Signal",
    "SousCompte",
    "Sphere",
    "SphereSynonyme",
    "StatutSuivi",
    "Subscription",
]
