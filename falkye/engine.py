"""Moteur central — spec section 9 : boucle sur les sources actives du registre,
jamais une source codée en dur ici. Orchestre le pipeline complet (spec section 1) :
détection → résolution NEQ/REQ → dossier cumulatif → vérifications de base →
plan tarifaire du profil (spec section 9bis) → score de confiance ET score de
pertinence (deux axes indépendants, spec section 6 restructurée) →
enrichissement web → notification.

Ajouter une source, un type de signal ou un canal de notification ne demande AUCUNE
modification de ce fichier — seulement une nouvelle entrée dans le registre
approprié (falkye/registry/*.yaml) et, pour une source/canal, un module qui
implémente l'interface générique (SourceConnector / NotificationChannel)."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from falkye import pertinence
from falkye.db import get_session
from falkye.enrichment import enrichir_entreprise
from falkye.matching import MatchResult, match_profile, spheres_probables
from falkye.models.company import Company, StatutVerification
from falkye.models.notification import (
    ModeUsage,
    Notification,
    NotificationDelivery,
    NotificationSignal,
)
from falkye.models.profile import Profile
from falkye.models.run_log import SourceRunLog
from falkye.models.signal import Signal
from falkye.notifications.formatter import formatter_notification
from falkye.registry.loader import Registry, get_registry
from falkye.resolution import resolve_company
from falkye.scoring import calculer_score, franchit_seuil_sensibilite
from falkye.sources.base import RawSignal
from falkye.verification import appliquer_verification, verifier_avant_enrichissement

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
                methode_acces=source_def.methode_acces,
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
    """Boucle sur les sources actives AUTOMATISÉES du registre — spec section 9 :
    le moteur ne connaît aucune source par son nom, seulement via ce registre.
    Exclut les sources en `methode_acces: import_manuel` (ex. RDPRM, REQ) :
    celles-ci ne produisent des signaux que via une action explicite de
    l'utilisateur (falkye/manual_import.py), jamais dans cette boucle."""
    registry = registry or get_registry()
    registry.valider_calibration()  # principe directeur non négociable #3
    return [
        ingest_source(db_session, s.id, since, registry, mode)
        for s in registry.sources_actives_automatisees()
    ]


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
    matches_par_signal: dict[int, list[MatchResult]] = {}
    meilleur_global: tuple[float, MatchResult] | None = None  # (base_pertinence, match) — voir plus bas

    for signal in company.signals:
        # Troisième porte, indépendante des deux axes confiance/pertinence
        # ci-dessous (spec section 9bis) : un signal d'une source payante ne
        # compte pour CE profil que si son plan tarifaire le couvre — filtré ICI,
        # avant même le matching, plutôt qu'à l'ingestion (qui reste globale au
        # dossier cumulatif, spec section 5 : un signal Radar ingéré profite à
        # TOUS les profils Radar/Radar+, pas seulement celui qui l'a "payé").
        source_def = registry.sources.get(signal.source_id)
        if source_def is not None and not source_def.disponible_pour_plan(profile.plan.value):
            continue

        raw = _signal_vers_rawsignal(signal)
        matches = match_profile(raw, profile, registry)
        if not matches:
            continue
        signaux_pertinents.append(signal)
        matches_par_signal[signal.id] = matches

        meilleur_signal = max(matches, key=lambda m: m.correspondance_qualitative)
        if meilleur_signal.correspondance_qualitative:
            justifications[signal.id] = (
                f"{signal.titre_ou_description or ''} — correspond aux mots-clés : "
                f"{', '.join(meilleur_signal.mots_cles_trouves)}"
            )
        else:
            justifications[signal.id] = signal.titre_ou_description or "Signal détecté"

        # Sphère retenue pour LA notification (une seule, même simplification déjà
        # en place) : le MEILLEUR tier de pertinence toutes correspondances
        # confondues (AAA > AA > A) plutôt que "le premier signal rencontré" — la
        # spec introduit maintenant un vrai classement entre ces tiers (section 6),
        # donc le choix de sphère doit en tenir compte plutôt que d'être arbitraire.
        for m in matches:
            base = pertinence.base_match(m, signal.signal_type_id, registry)
            if meilleur_global is None or base > meilleur_global[0]:
                meilleur_global = (base, m)

    if not signaux_pertinents:
        return None

    sphere_choisie = meilleur_global[1].profile_need.sphere_id

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

    # Deux axes indépendants, combinés en MATRICE — pas en moyenne (spec section 6,
    # restructurée) : un signal peu pertinent n'est jamais montré même si sa
    # confiance est élevée, et vice-versa. Chaque axe a son propre curseur de
    # sensibilité (Profile.sensibilite_confiance / sensibilite_pertinence) ; les
    # DEUX portes doivent s'ouvrir, sans compensation possible de l'une par l'autre.
    score_result = calculer_score(signaux_pertinents)
    pertinence_result = pertinence.calculer_pertinence(
        company, signaux_pertinents, matches_par_signal, sphere_choisie, registry
    )
    if not franchit_seuil_sensibilite(score_result.niveau, profile.sensibilite_confiance.value):
        return None
    if not pertinence.franchit_seuil_sensibilite(pertinence_result.niveau, profile.sensibilite_pertinence.value):
        return None

    notification = Notification(
        company_id=company.id,
        profile_id=profile.id,
        mode=mode,
        score_confiance=score_result.score_confiance,
        niveau_confiance=score_result.niveau,
        score_pertinence=pertinence_result.score_pertinence,
        niveau_pertinence=pertinence_result.niveau,
        sphere_probable_id=sphere_choisie,
        justification_resumee=(
            f"{len(signaux_pertinents)} signal(aux) détecté(s), "
            f"bonus de corroboration {score_result.bonus_corroboration:.0f} pts "
            f"(confiance), pertinence {pertinence_result.niveau.value}"
            + (f" (+{pertinence_result.bonus_absence:.0f} absence)" if pertinence_result.bonus_absence else "")
            + (f" (+{pertinence_result.bonus_velocite:.0f} vélocité)" if pertinence_result.bonus_velocite else "")
            + "."
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


DEFAULT_LOOKBACK_RECHERCHE_PONCTUELLE_DAYS = 60


def run_recherche_ponctuelle(
    profile_id: int, lookback_days: int | None = DEFAULT_LOOKBACK_RECHERCHE_PONCTUELLE_DAYS
) -> ScanReport:
    """Mode 2 (spec section 5) : plus large, sans lien strict au profil, sans
    notion de nouveau/déjà-vu — mais passe par le MÊME moteur de scan et les
    MÊMES vérifications de base obligatoires (spec section 6).

    "Plus large" (spec) veut dire : pas restreint au profil, pas de notion de
    nouveau/déjà-vu au niveau des NOTIFICATIONS — pas "toute la profondeur
    historique de chaque source", ce que le code faisait à tort avant cette
    correction (2026-08-31, découvert en lançant le tout premier scan ponctuel
    réel après le premier import complet du REQ : SEAO seul a 372 fichiers
    hebdomadaires/mensuels historiques depuis 2021, `since=None` les
    téléchargeait et traitait TOUS — extrapolé à ~12h). `lookback_days` borne
    maintenant la fenêtre par défaut comme pour la veille continue (60 jours,
    plus large que les 30 jours de veille, cohérent avec "plus large" sans
    être littéralement tout l'historique) ; `lookback_days=None` explicite
    retrouve l'ancien comportement (aucune borne, tout l'historique
    disponible) pour qui a vraiment besoin d'une recherche exhaustive et est
    prêt à en payer le temps."""
    registry = get_registry()
    db_session = get_session()
    try:
        since = (
            None
            if lookback_days is None
            else datetime.now(timezone.utc) - timedelta(days=lookback_days)
        )
        ingestion = ingest_all_active_sources(db_session, since=since, registry=registry, mode="recherche_ponctuelle")
        profile = db_session.get(Profile, profile_id)
        if profile is None:
            raise ValueError(f"Profil {profile_id} introuvable")
        notifications = generer_notifications(db_session, [profile], ModeUsage.RECHERCHE_PONCTUELLE, registry)
        return ScanReport(
            mode=ModeUsage.RECHERCHE_PONCTUELLE, ingestion=ingestion, nb_notifications_creees=len(notifications)
        )
    finally:
        db_session.close()
