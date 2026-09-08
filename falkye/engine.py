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
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from falkye import expansion_interprovinciale, pertinence, ponderation, retroaction
from falkye.assistance_client_cible import suggerer_clients_cibles_niveau1_pour_company
from falkye.crm_sync import pousser_notification_vers_crm, sonder_statuts_crm
from falkye.db import get_session
from falkye.enrichment import enrichir_entreprise
from falkye.matching import MatchResult, match_profile, spheres_probables
from falkye.motif import motif_avec_mots_cles
from falkye.models.base import en_utc
from falkye.models.company import Company, StatutVerification
from falkye.models.notification import (
    ModeUsage,
    Notification,
    NotificationDelivery,
    NotificationSignal,
)
from falkye.models.profile import PlanTarifaire, Profile
from falkye.cout_lectures import CHEMIN_EXACT, CHEMIN_PREFIXE, CHEMIN_SOUS_CHAINE, ouvrir_comptes
from falkye.execution import execution, mode_de_lancement
from falkye.models.run_log import SourceRunLog, StatutExecution
from falkye.models.signal import Signal
from falkye.notifications.base import FORME_UNITAIRE
from falkye.notifications.formatter import formatter_notification
from falkye.notifications.livraison import livrer
from falkye.registry.loader import Registry, get_registry
from falkye.resolution import resolve_company
from falkye.scoring import calculer_score, franchit_seuil_sensibilite
from falkye.sources.base import RawSignal
from falkye.territoire import appartient
from falkye.verification import appliquer_verification, verifier_avant_enrichissement

logger = logging.getLogger(__name__)

ENRICHISSEMENT_VALIDITE_JOURS = 30


@dataclass
class IngestReport:
    source_id: str
    nb_signaux_nouveaux: int = 0
    nb_signaux_dupliques: int = 0
    erreur: str | None = None
    # « Pas encore construite » n'est pas « en panne ». Les deux posent `erreur`,
    # et sans ce drapeau une source au statut `a_developper` compterait comme une
    # défaillance à chaque cycle — le bruit permanent qui finit par faire ignorer
    # le signal quand il devient vrai.
    ignoree: bool = False


@dataclass
class ScanReport:
    mode: ModeUsage
    ingestion: list[IngestReport] = field(default_factory=list)
    nb_notifications_creees: int = 0
    # Sondage retour CRM (falkye/crm_sync.py::sonder_statuts_crm, intégration
    # CRM ajoutée le 2026-09-02) — 0 par défaut pour run_recherche_ponctuelle,
    # qui ne sonde pas (voir run_veille_continue, seul mode où le sondage a lieu).
    nb_statuts_crm_synchronises: int = 0
    # Détection d'expansion inter-provinciale (falkye/expansion_
    # interprovinciale.py, spec Radar+ point 7, ajoutée le 2026-09-03) — 0 par
    # défaut pour run_recherche_ponctuelle, même raison que ci-dessus (passe
    # par lot greffée sur le cycle de veille continue seulement).
    nb_liens_interprovinciaux_detectes: int = 0


class CalibrationTerritoriale(RuntimeError):
    """Un filtre territorial déclaré qui n'a RIEN retenu sur une passe complète.

    **Pourquoi c'est une erreur et non une semaine calme.** Un filtre porte sur
    une valeur qu'on croit connaître — et le 2026-09-07 on a découvert que la
    valeur réelle du fichier des travailleurs étrangers temporaires était
    ``'Qu bec'`` et non « Québec ». Un filtre bâti sur la graphie attendue aurait
    tout rejeté, sans un mot, et la source aurait paru simplement vide. C'est le
    défaut de l'indicateur de dispense d'adresse, qui a rendu le rayon d'action
    inopérant pendant des semaines en supprimant silencieusement.

    **Le seuil est ZÉRO, jamais « peu ».** Un filtre qui retient 3 % là où il
    devrait en retenir 34 % est tout aussi cassé — mais on ne peut pas le savoir
    sans norme de volume, et cette norme n'existe pas encore (chantier 2, santé
    de source). Zéro est le seul cas qui se tranche sans connaître la bonne
    valeur : une source a produit des lignes, le filtre n'en a gardé aucune, donc
    le filtre ne parle pas la même langue que la donnée.
    """


def _sortir_de_la_transaction(db_session: Session) -> None:
    """Annule la transaction en cours — et si l'annulation elle-même échoue,
    jette la connexion plutôt que de laisser l'erreur remonter.

    **Pourquoi ce garde-fou existe.** Mesuré en production le 2026-09-07 : une
    source est tombée, le gestionnaire d'erreur a appelé `rollback()`, et le
    rollback a levé `Hrana: stream not found` — la connexion vers la base
    distante était morte. L'exception a traversé `ingest_source`,
    `ingest_all_active_sources` et `run_veille_continue`, et a emporté le cycle
    entier. Huit sources saines n'ont jamais été essayées.

    Le chemin de secours doit être plus robuste que ce qu'il rattrape, sans quoi
    il ne rattrape rien. `invalidate()` jette la connexion sans tenter de
    l'annuler : la suivante en obtiendra une neuve.
    """
    try:
        db_session.rollback()
    except Exception:  # noqa: BLE001
        logger.exception("Annulation impossible — la connexion est jetée")
        try:
            db_session.invalidate()
        except Exception:  # noqa: BLE001
            logger.exception("Invalidation impossible — la session est peut-être perdue")


def _consigner_lechec(
    db_session: Session, run_log_id: int | None, source_id: str, message: str
) -> None:
    """Marque la ligne d'exécution comme `erreur`, dans SA PROPRE transaction.

    **Une mise à jour, pas une insertion.** La ligne a été validée avant le
    travail réseau : elle survit donc au rollback. En ajouter une seconde
    laisserait la première à `en_cours` pour toujours — et une ligne `en_cours`
    qui survit à l'exécution se lit comme un cycle interrompu, c'est-à-dire le
    mauvais diagnostic posé par la trace elle-même.

    **Par identifiant plutôt que par l'objet.** Après un rollback — a fortiori
    après une connexion jetée — l'objet Python n'est plus fiable. L'identifiant,
    lui, l'est.

    Le défaut d'origine, trouvé le 2026-09-07 : la ligne n'était que *flushée*,
    donc le rollback de l'échec l'effaçait, et `run_log.statut = "erreur"`
    portait sur un objet que la session ne suivait plus. **Une source tombée
    n'écrivait rien** — indiscernable d'une source saine sans résultat.

    Et si même cette mise à jour échoue, on le dit au journal du système et on
    continue. Perdre la trace d'un échec est mauvais; perdre les huit sources
    suivantes pour cette raison serait pire.

    **LIMITE OBSERVÉE le 2026-09-07, et elle est structurelle.** Quand c'est LA
    BASE qui tombe — `eimt` est morte sur un `Hrana: SQLite error: disk I/O
    error` renvoyé par le serveur pendant un `commit()` — cette mise à jour
    échoue pour la même raison que ce qu'elle essaie de consigner. La ligne reste
    donc `en_cours` **et elle ment** : elle se lit comme une source qui travaille
    encore, alors que le cycle est fini depuis longtemps.

    Aucun garde-fou local ne referme ça : le journal ne peut pas se décrire
    lui-même quand son support tombe. Ce qui a sauvé la lecture ce jour-là, c'est
    que le compte de sources en erreur vient du rapport EN MÉMOIRE
    (`IngestReport.erreur`, agrégé par falkye/cycle.py) et non de cette table :
    la ligne de fin du journal d'exploitation annonçait « 1 source(s) en erreur
    sur 8 » — juste — là où `SourceRunLog` disait « en cours » — faux.

    **D'où la règle, qui dépasse ce cas : un compte qui décrit une exécution ne
    se calcule jamais depuis la base que cette exécution écrit.** Il se tient en
    mémoire pendant l'exécution et n'est consigné qu'à la fin. Une lecture a
    posteriori de la table donnerait le décompte de ce qui a pu s'écrire, pas de
    ce qui s'est passé — et les deux diffèrent précisément quand ça compte.

    Refermer les lignes restées ouvertes relève d'un autre mécanisme, et d'un
    autre chantier (chantier 2) : un cycle qui démarre peut clore celles plus
    anciennes qu'un seuil raisonnable. Ce module-ci n'a pas les moyens de le
    faire, puisque le moment où il faudrait écrire est celui où il ne peut pas.
    """
    if run_log_id is None:
        return
    try:
        db_session.execute(
            update(SourceRunLog)
            .where(SourceRunLog.id == run_log_id)
            .values(
                statut="erreur",
                erreur=message,
                finished_at=datetime.now(timezone.utc),
            )
        )
        db_session.commit()
    except Exception:  # noqa: BLE001
        logger.exception("Trace de l'échec de la source %s non écrite en base", source_id)
        _sortir_de_la_transaction(db_session)


def _a_ete_mise_en_quarantaine(db_session: Session, execution_id: str) -> bool:
    """Cette exécution a-t-elle mis un diff en quarantaine?

    **La réponse vit dans l'AUTRE base.** `DiffRunHistorique` est une table des
    miroirs, un fichier local; `SourceRunLog` est dans la base du produit. Aucune
    jointure SQL ne les relie — le rapprochement se fait ici, sur
    `execution_id`, et la session route la requête vers le bon moteur par la
    métadonnée du modèle (falkye/db.py::get_sessionmaker).

    Ne lève jamais : si la base des miroirs est muette, on ne peut pas savoir, et
    ne pas savoir ne doit pas transformer une ingestion réussie en échec. Le
    statut retombe alors sur « succes », ce qui est le comportement d'avant — un
    défaut connu vaut mieux qu'un nouveau.
    """
    from falkye.models.diff_run_historique import DiffRunHistorique

    try:
        return (
            db_session.execute(
                select(DiffRunHistorique.id)
                .where(
                    DiffRunHistorique.execution_id == execution_id,
                    DiffRunHistorique.quarantaine.is_(True),
                )
                .limit(1)
            ).first()
            is not None
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "Quarantaine indéterminable pour l'exécution %s — statut laissé à succès",
            execution_id,
        )
        return False


def ingest_source(
    db_session: Session, source_id: str, since: datetime | None, registry: Registry, mode: str
) -> IngestReport:
    """Étape 1-3 du pipeline pour UNE source : détection, résolution NEQ,
    persistance dans le dossier cumulatif (Company + Signal).

    **Ne lève jamais.** C'est le contrat de cette fonction, et c'est ce qui donne
    son sens à « une source en échec ne bloque pas les autres ». Il tenait sur le
    chemin nominal et pas sur le chemin de secours — voir
    `_sortir_de_la_transaction`.
    """
    with execution() as execution_id, ouvrir_comptes() as comptes:
        return _ingerer_source(db_session, source_id, since, registry, mode, execution_id, comptes)


def _ingerer_source(
    db_session: Session,
    source_id: str,
    since: datetime | None,
    registry: Registry,
    mode: str,
    execution_id: str,
    comptes,
) -> IngestReport:
    """Le corps de `ingest_source`, à l'intérieur d'une exécution ouverte.

    La séparation existe pour que l'identifiant d'exécution soit posé AVANT la
    première ligne écrite : `SourceRunLog` le porte, et les traces que le moteur
    de diff écrit dans l'AUTRE base le liront depuis le contexte (voir
    falkye/execution.py). Une exécution ouverte plus tard laisserait des traces
    orphelines au début de son propre run.
    """
    source_def = registry.source(source_id)
    report = IngestReport(source_id=source_id)
    debut = time.monotonic()

    run_log = SourceRunLog(
        source_id=source_id,
        mode=mode,
        statut=StatutExecution.EN_COURS.value,
        execution_id=execution_id,
        # Posé au DÉBUT, avec la ligne — c'est la seule information qu'on ne
        # pourra pas retrouver après coup si l'exécution meurt sans rien écrire.
        lance_par=mode_de_lancement().value,
    )
    try:
        db_session.add(run_log)
        # VALIDÉ, pas seulement flushé — c'est la cause profonde de la panne du
        # 2026-09-07. Un `flush()` laisse une ÉCRITURE non validée ouverte sur la
        # base distante pendant tout ce qui suit, et ce qui suit est un
        # téléchargement réseau qui peut durer une minute. Mesuré ce jour-là :
        # une transaction en lecture seule survit à 180 s d'inactivité, une
        # transaction portant une écriture meurt en 75 s — le fournisseur expire
        # bien plus vite un flux qui tient un verrou d'écriture. Le flux mort
        # fait ensuite échouer la première opération suivante, rollback compris.
        # L'identifiant est pris APRÈS le flush et AVANT la validation. Le lire
        # après la validation forcerait un rafraîchissement — un aller-retour
        # distant de plus, et surtout une transaction rouverte au moment précis
        # où le connecteur part sur le réseau.
        db_session.flush()
        run_log_id = run_log.id
        db_session.commit()
    except Exception as exc:  # noqa: BLE001
        # Sous protection comme le reste : si la connexion est déjà morte ici,
        # lever ferait exactement ce qu'on vient de corriger — emporter les
        # sources suivantes. On perd la trace de celle-ci, pas le cycle.
        _sortir_de_la_transaction(db_session)
        logger.exception("Ouverture du journal d'exécution impossible pour %s", source_id)
        report.erreur = str(exc)
        return report

    try:
        connector = source_def.charger_connecteur()
        if connector is None:
            report.erreur = "Aucun connecteur codé pour cette source (statut probablement a_developper)."
            report.ignoree = True
            run_log.statut = StatutExecution.IGNOREE.value
            run_log.finished_at = datetime.now(timezone.utc)
            # Validé ICI : le `finally` qui s'en chargeait a disparu avec la
            # refonte du chemin d'erreur, et sans cette ligne une source pas
            # encore construite ne laisserait plus que sa ligne `en_cours`.
            db_session.commit()
            return report

        hors_territoire = 0
        dans_territoire = 0

        for raw in connector.detect(since, db_session):
            # Le filtre territorial s'applique ICI, pour TOUTES les sources, à
            # partir de ce que le registre déclare. Le connecteur l'ignore.
            if not appartient(raw.region, source_def.territoire):
                hors_territoire += 1
                continue
            dans_territoire += 1

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
            # VALIDÉ à chaque signal, pas flushé — décision du 2026-09-07, prise
            # sur la mesure : la base distante annule une transaction portant une
            # écriture non validée après moins de dix secondes d'inactivité. Un
            # `flush()` ici laisserait cette écriture ouverte pendant la
            # résolution NEQ du signal SUIVANT — 0,32 s par appel de repli, et
            # rien ne borne le nombre d'appels. La source entière serait alors
            # perdue, proprement mais perdue.
            #
            # Ce que ça coûte : un aller-retour facturé par signal neuf. Mis en
            # regard du quota — le run de référence en a consommé 3,47 M sur
            # 10 M, un cycle normal en écrit quelques centaines — c'est un bon
            # échange contre une classe de panne silencieuse.
            #
            # Ce que ça change aussi, et qui est voulu : une source qui tombe à
            # mi-chemin garde ce qu'elle a déjà trouvé. La déduplication par
            # `source_ref` fait que la reprise ramasse le reste sans doublon.
            db_session.commit()
            report.nb_signaux_nouveaux += 1

        if source_def.territoire and dans_territoire == 0 and hors_territoire > 0:
            raise CalibrationTerritoriale(
                f"le filtre territorial {source_def.territoire} n'a retenu AUCUNE "
                f"des {hors_territoire} ligne(s) produites par cette source. Le "
                "filtre ne parle probablement pas la même langue que la donnée — "
                "voir falkye/territoire.py, et vérifier la valeur RÉELLE écrite "
                "par la source avant de corriger la graphie attendue."
            )
        if hors_territoire:
            logger.info(
                "%s : %s ligne(s) retenue(s), %s écartée(s) hors du territoire %s",
                source_id, dans_territoire, hors_territoire, source_def.territoire,
            )

        db_session.commit()
        # **Le statut se lit sur ce que l'exécution a fait, pas sur l'absence
        # d'exception.** Une source mise en quarantaine retourne zéro signal
        # sans lever : jusqu'ici elle s'enregistrait « succes », mot pour mot ce
        # qu'enregistre un territoire calme. C'est le premier critère
        # d'acceptation du chantier 2, et il échouait avant d'avoir commencé.
        run_log.statut = (
            StatutExecution.QUARANTAINE.value
            if _a_ete_mise_en_quarantaine(db_session, execution_id)
            else StatutExecution.SUCCES.value
        )
        run_log.nb_signaux_detectes = report.nb_signaux_nouveaux
        run_log.finished_at = datetime.now(timezone.utc)
        run_log.duree_ms = int((time.monotonic() - debut) * 1000)
        # Des comptes, pas des lignes lues : la conversion se fait à la lecture,
        # depuis la population du moment (falkye/cout_lectures.py).
        run_log.nb_resolutions_exact = comptes.appels[CHEMIN_EXACT]
        run_log.nb_resolutions_prefixe = comptes.appels[CHEMIN_PREFIXE]
        run_log.nb_resolutions_sous_chaine = comptes.appels[CHEMIN_SOUS_CHAINE]
        db_session.commit()
    except Exception as exc:  # noqa: BLE001 -- une source en échec ne doit pas bloquer les autres
        # L'ordre compte : sortir de la transaction morte AVANT d'essayer
        # d'écrire quoi que ce soit, et écrire la trace dans une transaction
        # neuve. L'ancienne portait la ligne `en_cours`, que le rollback efface.
        _sortir_de_la_transaction(db_session)
        logger.exception("Échec de l'ingestion pour la source %s", source_id)
        report.erreur = str(exc)
        _consigner_lechec(db_session, run_log_id, source_id, str(exc))

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
    # `en_utc` : la date relue depuis SQLite revient naïve (le fuseau n'est pas
    # stocké), et la soustraction lèverait au deuxième cycle — le premier ayant
    # posé la valeur. Voir falkye/models/base.py.
    verifie_le = en_utc(company.site_web_vérifié_le)
    if verifie_le is None:
        return True
    age = datetime.now(timezone.utc) - verifie_le
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
        # Ville/région de l'entreprise associée — spec section 4bis "Profils de
        # recherche multiples simultanés" : nécessaire pour que match_profile
        # puisse filtrer par ProfileNeed.territoire (falkye/matching.py).
        # Jamais utilisées avant cette fonctionnalité (Profile.ville/region/
        # rayon_km existaient depuis la Phase 1 mais ne filtraient rien — voir
        # docs/ARCHITECTURE.md), donc aucun changement de comportement pour un
        # besoin qui ne définit pas de territoire.
        ville=signal.company.ville,
        region=signal.company.region,
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
    # (base_pertinence, match, sphere_id) — la sphère qui a atteint ce score
    # précis parmi TOUTES celles liées au besoin (spec section 8bis, lien
    # sphère↔besoin plusieurs-à-plusieurs), voir plus bas.
    meilleur_global: tuple[float, MatchResult, str] | None = None

    # Pondération de pertinence (spec section 4bis, Radar+ "pondération du moteur
    # de score personnalisable") — résolue une fois par profil, utilisée à la
    # fois pour le choix de sphère ci-dessous et pour calculer_pertinence plus
    # bas, cohérence garantie entre les deux.
    ponderation_profil = ponderation.ponderation_pour_profil(db_session, profile)

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
        # Le motif vient de la STRUCTURE DE FAITS, pas du seul libellé de la
        # source — voir falkye/motif.py. L'ancienne version retombait sur
        # « Signal détecté » dès qu'une source ne libellait pas ses événements,
        # et ouvrait la variante à mots-clés par un tiret orphelin.
        justifications[signal.id] = motif_avec_mots_cles(
            signal,
            meilleur_signal.mots_cles_trouves if meilleur_signal.correspondance_qualitative else [],
        )

        # Sphère retenue pour LA notification (une seule, même simplification déjà
        # en place) : le MEILLEUR tier de pertinence toutes correspondances
        # confondues (AAA > AA > A) plutôt que "le premier signal rencontré" — la
        # spec introduit maintenant un vrai classement entre ces tiers (section 6),
        # donc le choix de sphère doit en tenir compte plutôt que d'être arbitraire.
        for m in matches:
            base, sphere_du_match = pertinence.meilleure_sphere_pour_match(
                m, signal.signal_type_id, registry, ponderation_profil
            )
            if sphere_du_match is None:
                continue  # besoin sans aucune sphère liée — rien à retenir (spec section 8bis)
            if meilleur_global is None or base > meilleur_global[0]:
                meilleur_global = (base, m, sphere_du_match)

    if not signaux_pertinents or meilleur_global is None:
        return None

    sphere_choisie = meilleur_global[2]
    # Combinaison sphère/usage × territoire à l'origine de cette notification
    # (spec section 4bis, "Profils de recherche multiples simultanés") — le
    # ProfileNeed du MEILLEUR match global, cohérent avec sphere_choisie
    # ci-dessus (les deux viennent du même meilleur_global).
    profile_need_choisi_id = meilleur_global[1].profile_need.id

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
            # Coordonnées (spec section 4bis, tableau de bord) — déjà extraites par
            # enrichir_entreprise, simplement persistées maintenant (voir
            # falkye/models/company.py:telephone/courriel_contact).
            company.telephone = enrichment.coordonnees.get("telephone") or company.telephone
            company.courriel_contact = enrichment.coordonnees.get("courriel") or company.courriel_contact
        except Exception:  # noqa: BLE001 -- l'enrichissement ne doit jamais faire planter le scan
            logger.exception("Échec de l'enrichissement web pour %s", company.nom_detecte)

    appliquer_verification(company, enrichment)
    db_session.flush()
    if not company.est_presentable():
        return None  # exclusion silencieuse (spec section 6)

    # Détection d'expansion inter-provinciale (spec Radar+, point 7, ajoutée le
    # 2026-09-03) — bonus de confiance, RÉSERVÉ AU PLAN RADAR MINIMUM (jamais
    # Écho, même si le calcul lui-même est gratuit : décision produit
    # d'Alexandre, "aucun enrichissement de résultat ne reste dans Écho, peu
    # importe son coût de calcul" — voir falkye/expansion_interprovinciale.py).
    evaluation_expansion = expansion_interprovinciale.EvaluationExpansion(bonus=0.0, texte_hedge=None)
    if profile.plan != PlanTarifaire.ECHO:
        evaluation_expansion = expansion_interprovinciale.evaluer_pour_company(db_session, company)

    # Deux axes indépendants, combinés en MATRICE — pas en moyenne (spec section 6,
    # restructurée) : un signal peu pertinent n'est jamais montré même si sa
    # confiance est élevée, et vice-versa. Chaque axe a son propre curseur de
    # sensibilité (Profile.sensibilite_confiance / sensibilite_pertinence) ; les
    # DEUX portes doivent s'ouvrir, sans compensation possible de l'une par l'autre.
    score_result = calculer_score(
        signaux_pertinents, bonus_expansion_interprovinciale=evaluation_expansion.bonus
    )
    poids_sphere = retroaction.poids_pour_sphere(db_session, profile.id, sphere_choisie)

    # Dimension "qui" (client cible, spec section 8bis, 2026-09-03) — RÉSERVÉE
    # AU PLAN RADAR+ dans son ENSEMBLE (bonus ET redirection "hors profil"),
    # même principe que ponderation.py/webhook_channel.py : pas de gating
    # partiel entre les deux effets d'une même fonctionnalité. Pour tout
    # autre plan, les deux listes restent vides — bonus_et_redirection_qui
    # retombe alors sur son comportement par défaut sûr (0.0, False),
    # comportement historique inchangé.
    client_cible_ids_entreprise: list[str] = []
    clients_cibles_lies_besoin: list[tuple[str, float]] = []
    if profile.plan == PlanTarifaire.RADAR_PLUS:
        need_choisi = meilleur_global[1].profile_need
        clients_cibles_lies_besoin = [(l.client_cible_id, l.poids) for l in need_choisi.clients_cibles_lies]
        if clients_cibles_lies_besoin:
            # Classification cross-source (spec section 8bis, point 2, 2026-09-03) —
            # voir la docstring de suggerer_clients_cibles_niveau1_pour_company pour
            # le détail des champs volontairement exclus (donneur d'ordre, poste
            # affiché, etc.) et pourquoi company.secteur_activite_libelle EST déjà la
            # fusion cross-source pour REQ et les licences municipales hors Québec.
            suggestions_qui = suggerer_clients_cibles_niveau1_pour_company(db_session, company)
            client_cible_ids_entreprise = [s.client_cible_id for s in suggestions_qui]

    pertinence_result = pertinence.calculer_pertinence(
        company,
        signaux_pertinents,
        matches_par_signal,
        sphere_choisie,
        registry,
        poids_sphere=poids_sphere,
        ponderation=ponderation_profil,
        client_cible_ids_entreprise=client_cible_ids_entreprise,
        clients_cibles_lies_besoin=clients_cibles_lies_besoin,
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
        profile_need_id=profile_need_choisi_id,
        statut_suivi_id=registry.statut_suivi_par_defaut().id,
        hors_profil=pertinence_result.hors_profil,
        justification_resumee=(
            f"{len(signaux_pertinents)} signal(aux) détecté(s), "
            f"bonus de corroboration {score_result.bonus_corroboration:.0f} pts "
            f"(confiance), pertinence {pertinence_result.niveau.value}"
            + (f" (+{pertinence_result.bonus_absence:.0f} absence)" if pertinence_result.bonus_absence else "")
            + (f" (+{pertinence_result.bonus_velocite:.0f} vélocité)" if pertinence_result.bonus_velocite else "")
            + (f" (+{pertinence_result.bonus_qui:.0f} clientèle cible)" if pertinence_result.bonus_qui else "")
            + (
                f" (+{score_result.bonus_expansion_interprovinciale:.0f} pts, "
                f"{evaluation_expansion.texte_hedge})"
                if evaluation_expansion.texte_hedge
                else ""
            )
            + (
                " — HORS PROFIL DÉCLARÉ : correspond à la sphère mais pas à la "
                "clientèle cible déclarée pour ce besoin, à valider."
                if pertinence_result.hors_profil
                else ""
            )
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
    # Canal "hors profil déclaré" (spec section 8bis, 2026-09-03) : jamais
    # livré par courriel/webhook PAR DÉFAUT — visible uniquement dans le
    # tableau de bord (section séparée, falkye/cli.py::dashboard_voir),
    # cohérent avec "jamais mélangé aux notifications normales". La
    # notification existe bel et bien en base (jamais un signal perdu), seule
    # la livraison automatique est court-circuitée ici.
    if notification.hors_profil:
        return

    # Livraison UNITAIRE seulement — c'est-à-dire, depuis la décision du
    # 2026-09-05, les canaux qui poussent vers un SYSTÈME (webhook ici, CRM plus
    # bas), jamais un message lu par un humain. Le courriel part désormais GROUPÉ,
    # par le résumé (falkye/summary.py) : charte section 16, "le groupement est la
    # forme par défaut; l'envoi unitaire est l'exception justifiée, jamais
    # l'inverse". Quinze notifications séparées transforment une bonne nouvelle en
    # irritant et poussent vers le désabonnement.
    #
    # Quels canaux servent quelle forme est déclaré au REGISTRE
    # (registry/notification_channels.yaml::formes_livraison), et la résolution de
    # destination reste propre à chaque canal — le moteur ne nomme aucun canal.
    # Chemin commun avec le résumé : falkye/notifications/livraison.py.
    contenu = formatter_notification(notification, registry)
    livrer(db_session, notification.profile, contenu, registry, FORME_UNITAIRE, notification=notification)
    # Intégration CRM (Radar et Radar+, ajoutée le 2026-09-02) — même point de
    # déclenchement qu'un canal de notification classique (une notification
    # nouvellement créée), mais PAS un NotificationChannel : un push CRM est un
    # upsert avec état (falkye/models/crm_sync_record.py), pas un envoi
    # fire-and-forget. Voir falkye/crm_sync.py pour la distinction complète.
    pousser_notification_vers_crm(db_session, notification, registry)
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

        # Détection d'expansion inter-provinciale (falkye/expansion_
        # interprovinciale.py, spec Radar+ point 7) — greffée ICI, APRÈS
        # l'ingestion mais AVANT generer_notifications : le bonus de confiance
        # qu'elle alimente doit déjà exister en base au moment où
        # _traiter_entreprise_pour_profil calcule le score de chaque
        # notification, sans quoi les liens détectés PENDANT ce cycle
        # n'auraient d'effet qu'au cycle SUIVANT.
        nouveaux_liens = expansion_interprovinciale.detecter_expansions(db_session, registry)

        query = select(Profile)
        if profile_ids:
            query = query.where(Profile.id.in_(profile_ids))
        profiles = db_session.execute(query).scalars().all()

        notifications = generer_notifications(db_session, profiles, ModeUsage.VEILLE_CONTINUE, registry)

        # Sondage retour CRM (spec : "dans les deux sens si possible") — greffé
        # sur CE cycle précis (veille continue) plutôt qu'à chaque scan : la
        # recherche ponctuelle n'a pas de notion de "déjà connu" à mettre à
        # jour dans le même esprit (voir docstring run_recherche_ponctuelle).
        nb_statuts_crm = sonder_statuts_crm(db_session, registry)
        db_session.commit()

        return ScanReport(
            mode=ModeUsage.VEILLE_CONTINUE,
            ingestion=ingestion,
            nb_notifications_creees=len(notifications),
            nb_statuts_crm_synchronises=nb_statuts_crm,
            nb_liens_interprovinciaux_detectes=len(nouveaux_liens),
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
