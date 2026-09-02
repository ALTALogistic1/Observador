"""Interface générique des fournisseurs CRM (HubSpot, Pipedrive — voir
registry/crm_providers.yaml). Même principe que NotificationChannel
(falkye/notifications/base.py) : le déclencheur (falkye/crm_sync.py) ne connaît
que cette interface, jamais un fournisseur précis.

DIFFÉRENT d'un NotificationChannel malgré la ressemblance de façade : un canal de
notification pousse un message une fois (fire-and-forget) ; un fournisseur CRM
pousse un UPSERT (créer ou mettre à jour la MÊME fiche à chaque nouvelle
notification pour la même entreprise — voir falkye/models/crm_sync_record.py)
et, dans l'autre sens, PEUT être sondé pour lire un changement fait côté CRM
(spec : synchronisation "dans les deux sens si possible", implémentée par
sondage périodique — falkye/crm_sync.py::sonder_statuts_crm — pas un webhook
entrant, voir docs/ARCHITECTURE.md pour la décision)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from falkye.models.crm_connection import CrmConnection
    from falkye.models.profile import Profile
    from falkye.notifications.base import NotificationContent
    from falkye.registry.loader import CrmProviderDef


@dataclass
class CrmPushResult:
    succes: bool
    crm_object_id: str | None = None
    erreur: str | None = None


@dataclass
class CrmStatutDistant:
    """Résultat d'un sondage retour (falkye/crm_sync.py::sonder_statuts_crm).
    `succes=True, stage_brut=None` veut dire "sondage réussi, rien à
    signaler" — différent d'un échec de sondage (`succes=False`), qui ne doit
    jamais être traité comme "aucun changement"."""

    succes: bool
    stage_brut: str | None = None
    erreur: str | None = None


def mappage_effectif(provider_def: "CrmProviderDef", connection: "CrmConnection") -> dict[str, str]:
    """Mappage {champ_falkye: propriété/champ CRM} pour CETTE connexion — le
    défaut du fournisseur (registry/crm_providers.yaml::champs_mappage),
    ajusté par les overrides propres à ce client
    (CrmConnection.champs_mappage_override, nécessaire en pratique pour
    Pipedrive — voir la note dans le YAML). Les overrides gagnent sur le
    défaut, jamais l'inverse."""
    return {**provider_def.champs_mappage, **(connection.champs_mappage_override or {})}


def valeurs_a_pousser(contenu: "NotificationContent", connection: "CrmConnection") -> dict[str, object | None]:
    """Valeurs FALKYE candidates à pousser vers un CRM, indépendantes du
    fournisseur — la correspondance vers un nom de propriété/champ CRM précis
    se fait via `mappage_effectif` + `proprietes_pour_mappage`, dans chaque
    client concret (hubspot_channel.py / pipedrive_channel.py)."""
    d = contenu.donnees_structurees or {}
    entreprise = d.get("entreprise") or {}
    statut_id = d.get("statut_suivi_id")
    mapping_statuts = connection.mapping_statuts or {}
    return {
        "nom": entreprise.get("nom"),
        "neq": entreprise.get("neq"),
        "adresse": entreprise.get("adresse"),
        "ville": entreprise.get("ville"),
        "site_web": entreprise.get("site_web"),
        "sphere_probable_id": d.get("sphere_probable_id"),
        "score_pertinence": d.get("score_pertinence"),
        "niveau_pertinence": d.get("niveau_pertinence"),
        "score_confiance": d.get("score_confiance"),
        "niveau_confiance": d.get("niveau_confiance"),
        # Traduit via CrmConnection.mapping_statuts si le client a défini une
        # correspondance pour CE statut ; sinon la valeur BRUTE FALKYE (l'id du
        # statut, ex. "a_joindre") est poussée telle quelle — jamais bloqué par
        # l'absence de mapping, voir falkye/models/crm_connection.py.
        "statut_suivi": mapping_statuts.get(statut_id, statut_id) if statut_id else None,
    }


def proprietes_pour_mappage(valeurs: dict[str, object | None], champs_mappage: dict[str, str]) -> dict[str, object]:
    """Filtre/renomme `valeurs` (clés FALKYE) vers des clés CRM selon
    `champs_mappage` — ne pousse que les champs déclarés dans le mappage ET
    dont la valeur FALKYE n'est pas None (jamais fabriquer/pousser une valeur
    vide, principe directeur #1)."""
    return {
        prop_crm: valeurs[champ_falkye]
        for champ_falkye, prop_crm in champs_mappage.items()
        if champ_falkye in valeurs and valeurs[champ_falkye] is not None
    }


class CrmProvider(ABC):
    def __init__(self, provider_def: "CrmProviderDef"):
        self.provider_def = provider_def

    def resoudre_connexion(self, profile: "Profile") -> "CrmConnection | None":
        """Connexion active pour CE profil, vers CE fournisseur — ou None si le
        profil n'a pas de connexion configurée pour ce fournisseur, si elle est
        désactivée, ou si le plan est insuffisant. Disponible pour Radar ET
        Radar+ (contrairement au webhook générique, réservé Radar+ seul) — gate
        au moment de l'USAGE, jamais au stockage (même principe que partout
        ailleurs dans le projet, voir falkye/notifications/webhook_channel.py)."""
        from falkye.models.profile import PlanTarifaire

        if profile.plan not in (PlanTarifaire.RADAR, PlanTarifaire.RADAR_PLUS):
            return None
        return next(
            (c for c in profile.connexions_crm if c.fournisseur == self.provider_def.id and c.actif),
            None,
        )

    @abstractmethod
    def pousser(
        self, connection: "CrmConnection", contenu: "NotificationContent", crm_object_id: str | None
    ) -> CrmPushResult:
        """Crée l'objet CRM si `crm_object_id` est None, sinon le met à jour
        (upsert) — jamais un doublon pour la même entreprise. L'appelant
        (falkye/crm_sync.py) est responsable de fournir le bon `crm_object_id`
        connu (via CrmSyncRecord) ou None à la première synchronisation."""
        raise NotImplementedError

    @abstractmethod
    def tirer_statut(self, connection: "CrmConnection", crm_object_id: str) -> CrmStatutDistant:
        """Lit l'étape/stage courant de l'objet CRM — utilisé par le sondage
        retour (falkye/crm_sync.py::sonder_statuts_crm), jamais appelé
        directement par le moteur (falkye/engine.py)."""
        raise NotImplementedError
