"""Synchronisation CRM (HubSpot/Pipedrive) — intégration CRM (Radar et Radar+,
retenue depuis un moment dans la liste de fonctionnalités, formellement
transmise le 2026-09-02). Deux directions :

  - `pousser_notification_vers_crm` : appelée au même point que
    falkye/engine.py::deliver_notification (une notification nouvellement
    créée) — pousse vers chaque fournisseur CRM connecté et actif du profil,
    en UPSERT (falkye/models/crm_sync_record.py) plutôt qu'un doublon à chaque
    cycle de veille.
  - `sonder_statuts_crm` : greffée sur falkye/engine.py::run_veille_continue —
    sondage PÉRIODIQUE (pas un webhook entrant, décision d'Alexandre
    2026-09-02 documentée dans docs/ARCHITECTURE.md : FALKYE n'a jamais eu de
    composant serveur HTTP exposé publiquement, et ce n'était pas le moment
    d'introduire ce changement d'architecture pour cette seule fonctionnalité)
    des fiches déjà synchronisées, pour un changement de statut fait côté CRM.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from falkye.models.crm_sync_record import CrmSyncRecord
from falkye.models.notification import Notification, NotificationDelivery
from falkye.notifications.formatter import formatter_notification
from falkye.registry.loader import Registry
from falkye.statut_suivi import appliquer_statut

logger = logging.getLogger(__name__)


def pousser_notification_vers_crm(db_session: Session, notification: Notification, registry: Registry) -> None:
    """Pousse UNE notification vers chaque fournisseur CRM connecté et actif du
    profil. Chaque tentative est tracée dans NotificationDelivery
    (channel_id=f"crm_{fournisseur}") — même mécanisme que les canaux de
    notification classiques (réutilisation délibérée plutôt qu'une table de
    journalisation parallèle, voir falkye/engine.py::deliver_notification)."""
    contenu = None  # construit paresseusement — jamais si aucun fournisseur n'est connecté
    for provider_def in registry.fournisseurs_crm_actifs():
        provider = provider_def.charger_fournisseur()
        if provider is None:
            continue
        connection = provider.resoudre_connexion(notification.profile)
        if connection is None:
            continue  # pas de connexion configurée, désactivée, ou plan insuffisant (Écho)

        if contenu is None:
            contenu = formatter_notification(notification, registry)

        sync_record = db_session.execute(
            select(CrmSyncRecord).where(
                CrmSyncRecord.profile_id == notification.profile_id,
                CrmSyncRecord.company_id == notification.company_id,
                CrmSyncRecord.fournisseur == provider_def.id,
            )
        ).scalar_one_or_none()

        result = provider.pousser(connection, contenu, sync_record.crm_object_id if sync_record else None)

        db_session.add(
            NotificationDelivery(
                notification_id=notification.id,
                channel_id=f"crm_{provider_def.id}",
                statut="envoyee" if result.succes else "echec",
                erreur=result.erreur,
            )
        )
        if not result.succes:
            continue

        if sync_record is None:
            sync_record = CrmSyncRecord(
                profile_id=notification.profile_id,
                company_id=notification.company_id,
                fournisseur=provider_def.id,
                crm_object_id=result.crm_object_id,
            )
            db_session.add(sync_record)
        elif result.crm_object_id:
            sync_record.crm_object_id = result.crm_object_id
        sync_record.dernier_statut_pousse_id = notification.statut_suivi_id
        sync_record.derniere_synchro_le = datetime.now(timezone.utc)


def sonder_statuts_crm(db_session: Session, registry: Registry) -> int:
    """Sondage retour (spec : "dans les deux sens si possible") — greffé sur le
    cycle de veille (falkye/engine.py::run_veille_continue). Pour chaque fiche
    déjà synchronisée, lit l'étape courante côté CRM ; si elle a changé depuis
    le dernier sondage ET qu'une correspondance existe dans
    CrmConnection.mapping_statuts pour cette valeur, applique le nouveau statut
    de suivi via falkye/statut_suivi.py::appliquer_statut (même règle de
    rétroaction qu'un changement fait depuis le tableau de bord). Une valeur
    d'étape CRM sans correspondance connue est ignorée proprement plutôt que
    devinée (principe directeur #1, "jamais fabriquer une valeur").

    Retourne le nombre de statuts effectivement changés (pour le rapport de scan,
    falkye/engine.py::ScanReport)."""
    nb_changements = 0
    sync_records = db_session.execute(select(CrmSyncRecord)).scalars().all()
    for sr in sync_records:
        provider_def = registry.fournisseur_crm(sr.fournisseur)
        if provider_def is None or not provider_def.est_actif:
            continue
        provider = provider_def.charger_fournisseur()
        if provider is None:
            continue
        connection = provider.resoudre_connexion(sr.profile)
        if connection is None:
            continue  # connexion retirée/désactivée ou profil rétrogradé sous Radar depuis le dernier push

        resultat = provider.tirer_statut(connection, sr.crm_object_id)
        if not resultat.succes or resultat.stage_brut is None:
            continue
        if resultat.stage_brut == sr.dernier_stage_crm_connu:
            continue  # pas de changement depuis le dernier sondage

        sr.dernier_stage_crm_connu = resultat.stage_brut
        sr.derniere_synchro_le = datetime.now(timezone.utc)

        mapping_inverse = {valeur: statut_id for statut_id, valeur in (connection.mapping_statuts or {}).items()}
        nouveau_statut_id = mapping_inverse.get(resultat.stage_brut)
        if nouveau_statut_id is None:
            continue  # valeur CRM sans correspondance connue dans mapping_statuts — ignoré, pas deviné

        notification = db_session.execute(
            select(Notification)
            .where(Notification.profile_id == sr.profile_id, Notification.company_id == sr.company_id)
            .order_by(Notification.created_at.desc())
        ).scalars().first()
        if notification is None:
            continue  # aucune notification à mettre à jour (ne devrait pas arriver en usage normal)

        appliquer_statut(db_session, notification, nouveau_statut_id, registry)
        sr.dernier_statut_pousse_id = nouveau_statut_id
        nb_changements += 1

    return nb_changements
