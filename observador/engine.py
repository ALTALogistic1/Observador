"""Moteur central — spec section 9 : boucle sur les sources actives du registre,
jamais une source codée en dur ici. Orchestre le pipeline complet (spec section 1) :
détection → résolution NEQ/REQ → dossier cumulatif → vérifications de base →
score de confiance → enrichissement web → notification.

Ajouter une source, un type de signal ou un canal de notification ne demande AUCUNE
modification de ce fichier — seulement une nouvelle entrée dans le registre
approprié (observador/registry/*.yaml) et, pour une source/canal, un module qui
implémente l'interface générique (SourceConnector / NotificationChannel)."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from observador.db import get_session
from observador.enrichment import enrichir_entreprise
from observador.matching import match_profile, spheres_probables
from observador.models.company import Company, StatutVerification
from observador.models.notification import (
    ModeUsage,
    Notification,
    NotificationDelivery,
    NotificationSignal,
)
from observador.models.profile import Profile
from observador.models.run_log import SourceRunLog
from observador.models.signal import Signal
from observador.notifications.formatter import formatter_notification
from observador.registry.loader import Registry, get_registry
from observador.resolution import resolve_company
from observador.scoring import calculer_score, franchit_seuil_sensibilite
from observador.sources.base import RawSignal
from observador.verification import appliquer_verification, verifier_avant_enrichissement

logger = logging.getLogger(__name__)

ENRICHISSEMENT_VALIDITE_JOURS = 30


@dataclass
class IngestReport:
    source_id: str
    nb_signaux_nouveaux: int = 0
    nb_signaux_dupliques: int = 0
    erreur: str | None = None


@dataclass
class ScanReport:
    mode: ModeUsage
    ingestion: list[IngestReport] = field(default_factory=list)
    nb_notifications_creees: int = 0


def ingest_source(
    db_session: Session, source_id: str, since: datetime | None, registry: Registry, mode: str
) -> IngestReport:
    """Étape 1-3 du pipeline pour UNE source : détection, résolution NEQ,
    persistance dans le dossier cumulatif (Company + Signal)."""
    source_def = registry.source(source_id)
    report = IngestReport(source_id=source_id)

    run_log = SourceRunLog(source_id=source_id, mode=mode, statut="en_cours")
    db_session.add(run_log)
    db_session.flush()

    try:
        connector = source_def.charger_connecteur()
        if connector is None:
            report.erreur = "Aucun connecteur codé pour cette source (statut probablement a_developper)."
            run_log.statut = "ignoree"
            return report

        for raw in connector.detect(since, db_session):
            existing = db_session.execute(
                select(Signal).where(Signal.source_id == source_id, Signal.source_ref == raw.source_ref)
            ).scalar_one_or_none()
            if existing is not None:
                report.nb_signaux_dupliques += 1
                continue

            company = resolve_company(db_session, raw)

            signal = Signal(
                company_id=company.id,
                source_id=source_id,
                signal_type_id=raw.signal_type_id,
                source_ref=raw.source_ref,
                detected_at=raw.detected_at,
                valeur_associee=raw.valeur_associee,
                titre_ou_description=raw.titre_ou_description,
                champs=raw.champs,
                spheres_probables=spheres_probables(raw.signal_type_id, registry),
            )
            db_session.add(signal)
            db_session.flush()
            report.nb_signaux_nouveaux += 1

        db_session.commit()
        run_log.statut = "succes"
        run_log.nb_signaux_detectes = report.nb_signaux_nouveaux
    except Exception as exc:  # noqa: BLE001 -- une source en échec ne doit pas bloquer les autres
        db_session.rollback()
        logger.exception("Échec de l'ingestion pour la source %s", source_id)
        report.erreur = str(exc)
        run_log.statut = "erreur"
        run_log.erreur = str(exc)
    finally:
        run_log.finished_at = datetime.now(timezone.utc)
        db_session.commit()

    return report


def ingest_all_active_sources(
    db_session: Session, since: datetime | None, registry: Registry | None = None, mode: str = "veille_continue"
) -> list[IngestReport]:
    """Boucle sur TOUTES les sources actives du registre — spec section 9 :
    le moteur ne connaît aucune source par son nom, seulement via ce registre."""
    registry = registry or get_registry()
    return [ingest_source(db_session, s.id, since, registry, mode) for s in registry.sources_actives()]


def _signaux_deja_couverts(db_session: Session, company_id: int, profile_id: int) -> set[int]:
    rows = (
        db_session.execute(
            select(NotificationSignal.signal_id)
            .join(Notification)
            .where(Notification.company_id == company_id, Notification.profile_id == profile_id)
        )
        .scalars()
        .all()
    )
    return set(rows)


def _besoin_enrichissement(company: Company) -> bool:
    if company.site_web_vérifié_le is None:
        return True
    age = datetime.now(timezone.utc) - company.site_web_vérifié_le
    return age > timedelta(days=ENRICHISSEMENT_VALIDITE_JOURS)


def _signal_vers_rawsignal(signal: Signal) -> RawSignal:
    return RawSignal(
        signal_type_id=signal.signal_type_id,
        nom_entreprise=signal.company.nom_detecte,
        detected_at=signal.detected_at,
        source_ref=signal.source_ref or "",
        titre_ou_description=signal.titre_ou_description,
        valeur_associee=signal.valeur_associee,
        champs=signal.champs,
    )


def _traiter_entreprise_pour_profil(
    db_session: Session,
    company: Company,
    profile: Profile,
    mode: ModeUsage,
    registry: Registry,
) -> Notification | None:
    # Sélectionne les signaux de ce dossier pertinents pour ce profil (correspondance
    # sphère générique ou qualitative — spec section 7).
    signaux_pertinents: list[Signal] = []
    justifications: dict[int, str] = {}
    sphere_choisie: str | None = None

    for signal in company.signals:
        raw = _signal_vers_rawsignal(signal)
        matches = match_profile(raw, profile, registry)
        if not matches:
            continue
        signaux_pertinents.append(signal)
        meilleur = max(matches, key=lambda m: m.correspondance_qualitative)
        if meilleur.correspondance_qualitative:
            justifications[signal.id] = (
                f"{signal.titre_ou_description or ''} — correspond aux mots-clés : "
                f"{', '.join(meilleur.mots_cles_trouves)}"
            )
        else:
            justifications[signal.id] = signal.titre_ou_description or "Signal détecté"
        sphere_choisie = sphere_choisie or meilleur.profile_need.sphere_id

    if not signaux_pertinents:
        return None

    if mode == ModeUsage.VEILLE_CONTINUE:
        deja_couverts = _signaux_deja_couverts(db_session, company.id, profile.id)
        nouveaux = {s.id for s in signaux_pertinents} - deja_couverts
        if not nouveaux:
            return None  # rien de neuf à raconter (spec section 5 : dossier cumulatif, pas de répétition)

    # Vérifications de base AVANT enrichissement (spec section 6) — inutile
    # d'enrichir une entreprise déjà exclue (radiée, résolution ambiguë).
    statut_precoce = verifier_avant_enrichissement(company)
    if statut_precoce != StatutVerification.NON_VERIFIE:
        company.statut_verification = statut_precoce
        db_session.flush()
        return None  # exclusion silencieuse

    enrichment = None
    if _besoin_enrichissement(company):
        try:
            enrichment = enrichir_entreprise(
                company.nom_officiel_req or company.nom_detecte,
                ville=company.ville,
                site_web_connu=company.site_web,
            )
            company.site_web = enrichment.site_web or company.site_web
            company.site_web_vérifié_le = datetime.now(timezone.utc)
        except Exception:  # noqa: BLE001 -- l'enrichissement ne doit jamais faire planter le scan
            logger.exception("Échec de l'enrichissement web pour %s", company.nom_detecte)

    appliquer_verification(company, enrichment)
    db_session.flush()
    if not company.est_presentable():
        return None  # exclusion silencieuse (spec section 6)

    score_result = calculer_score(signaux_pertinents)
    if not franchit_seuil_sensibilite(score_result.niveau, profile.sensibilite.value):
        return None

    notification = Notification(
        company_id=company.id,
        profile_id=profile.id,
        mode=mode,
        score_confiance=score_result.score_confiance,
        niveau=score_result.niveau,
        sphere_probable_id=sphere_choisie,
        justification_resumee=(
            f"{len(signaux_pertinents)} signal(aux) détecté(s), "
            f"bonus de corroboration {score_result.bonus_corroboration:.0f} pts."
        ),
    )
    db_session.add(notification)
    db_session.flush()

    for signal in signaux_pertinents:
        db_session.add(
            NotificationSignal(
                notification_id=notification.id,
                signal_id=signal.id,
                justification=justifications.get(signal.id, ""),
            )
        )

    db_session.flush()
    return notification


def deliver_notification(db_session: Session, notification: Notification, registry: Registry) -> None:
    contenu = formatter_notification(notification, registry)
    for channel_def in registry.canaux_actifs():
        channel = channel_def.charger_canal()
        if channel is None:
            continue
        destinataire = notification.profile.courriel  # seul le courriel a un destinataire connu en Phase 1
        result = channel.envoyer(destinataire, contenu)
        db_session.add(
            NotificationDelivery(
                notification_id=notification.id,
                channel_id=channel_def.id,
                statut="envoyee" if result.succes else "echec",
                erreur=result.erreur,
            )
        )
    db_session.commit()


def generer_notifications(
    db_session: Session, profiles: list[Profile], mode: ModeUsage, registry: Registry | None = None
) -> list[Notification]:
    registry = registry or get_registry()
    notifications = []
    for profile in profiles:
        if not profile.besoins_fournisseur():
            continue  # mécanique fournisseur uniquement en Phase 1 (spec section 4/9)
        companies = db_session.execute(select(Company)).scalars().all()
        for company in companies:
            notif = _traiter_entreprise_pour_profil(db_session, company, profile, mode, registry)
            if notif:
                deliver_notification(db_session, notif, registry)
                notifications.append(notif)
    return notifications


def run_veille_continue(profile_ids: list[int] | None = None, lookback_days: int = 30) -> ScanReport:
    """Mode 1 (spec section 5) : basé strictement sur les profils configurés, avec
    suivi d'état pour éviter les doublons."""
    registry = get_registry()
    db_session = get_session()
    try:
        since = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        ingestion = ingest_all_active_sources(db_session, since, registry, mode="veille_continue")

        query = select(Profile)
        if profile_ids:
            query = query.where(Profile.id.in_(profile_ids))
        profiles = db_session.execute(query).scalars().all()

        notifications = generer_notifications(db_session, profiles, ModeUsage.VEILLE_CONTINUE, registry)
        return ScanReport(
            mode=ModeUsage.VEILLE_CONTINUE, ingestion=ingestion, nb_notifications_creees=len(notifications)
        )
    finally:
        db_session.close()


def run_recherche_ponctuelle(profile_id: int) -> ScanReport:
    """Mode 2 (spec section 5) : plus large, sans lien strict au profil, sans
    notion de nouveau/déjà-vu — mais passe par le MÊME moteur de scan et les
    MÊMES vérifications de base obligatoires (spec section 6)."""
    registry = get_registry()
    db_session = get_session()
    try:
        ingestion = ingest_all_active_sources(db_session, since=None, registry=registry, mode="recherche_ponctuelle")
        profile = db_session.get(Profile, profile_id)
        if profile is None:
            raise ValueError(f"Profil {profile_id} introuvable")
        notifications = generer_notifications(db_session, [profile], ModeUsage.RECHERCHE_PONCTUELLE, registry)
        return ScanReport(
            mode=ModeUsage.RECHERCHE_PONCTUELLE, ingestion=ingestion, nb_notifications_creees=len(notifications)
        )
    finally:
        db_session.close()
