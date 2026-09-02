"""Regroupe l'import de tous les modèles pour que Base.metadata les connaisse
(voir falkye/db.py:init_db)."""
from falkye.models.base import Base  # noqa: F401
from falkye.models.company import Company  # noqa: F401
from falkye.models.corp_federale_entry import CorporationFederaleEntry  # noqa: F401
from falkye.models.licence_municipale_entry import LicenceMunicipaleEntry  # noqa: F401
from falkye.models.notification import (  # noqa: F401
    Notification,
    NotificationDelivery,
    NotificationSignal,
    PeriodicSummary,
)
from falkye.models.ponderation_personnalisee import PonderationPersonnalisee  # noqa: F401
from falkye.models.profile import Profile, ProfileNeed  # noqa: F401
from falkye.models.req_entry import REQEntry  # noqa: F401
from falkye.models.req_etablissement_entry import REQEtablissementEntry  # noqa: F401
from falkye.models.retroaction_pertinence import RetroactionPertinence  # noqa: F401
from falkye.models.run_log import SourceRunLog  # noqa: F401
from falkye.models.signal import Signal  # noqa: F401
from falkye.models.sous_compte import SousCompte  # noqa: F401
from falkye.models.sphere import Sphere  # noqa: F401
from falkye.models.statut_suivi import StatutSuivi  # noqa: F401
from falkye.models.subscription import Subscription  # noqa: F401

__all__ = [
    "Base",
    "Company",
    "CorporationFederaleEntry",
    "LicenceMunicipaleEntry",
    "Notification",
    "NotificationDelivery",
    "NotificationSignal",
    "PeriodicSummary",
    "PonderationPersonnalisee",
    "Profile",
    "ProfileNeed",
    "REQEntry",
    "REQEtablissementEntry",
    "RetroactionPertinence",
    "SourceRunLog",
    "Signal",
    "SousCompte",
    "Sphere",
    "StatutSuivi",
    "Subscription",
]
