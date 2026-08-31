"""Regroupe l'import de tous les modèles pour que Base.metadata les connaisse
(voir observador/db.py:init_db)."""
from observador.models.base import Base  # noqa: F401
from observador.models.company import Company  # noqa: F401
from observador.models.corp_federale_entry import CorporationFederaleEntry  # noqa: F401
from observador.models.notification import (  # noqa: F401
    Notification,
    NotificationDelivery,
    NotificationSignal,
    PeriodicSummary,
)
from observador.models.profile import Profile, ProfileNeed  # noqa: F401
from observador.models.req_entry import REQEntry  # noqa: F401
from observador.models.run_log import SourceRunLog  # noqa: F401
from observador.models.signal import Signal  # noqa: F401
from observador.models.sphere import Sphere  # noqa: F401

__all__ = [
    "Base",
    "Company",
    "CorporationFederaleEntry",
    "Notification",
    "NotificationDelivery",
    "NotificationSignal",
    "PeriodicSummary",
    "Profile",
    "ProfileNeed",
    "REQEntry",
    "SourceRunLog",
    "Signal",
    "Sphere",
]
