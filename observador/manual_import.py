"""Import manuel de documents sources — spec section 9, "Import manuel de
documents sources".

Permet d'activer une source dont l'automatisation complète impliquerait un coût
récurrent (ex. RDPRM, payant à l'unité par recherche) SANS engagement
récurrent : l'utilisateur fait lui-même la recherche ponctuelle sur le site de
la source (voir SourceDef.lien_recherche pour le lien direct), puis importe le
résultat ici. Une fois importé, ce résultat suit EXACTEMENT le même chemin
qu'un signal détecté automatiquement — résolution NEQ, dossier cumulatif,
vérifications de base, score de confiance, corroboration, notification (spec :
"sans distinction de traitement une fois à l'intérieur du pipeline").

GÉNÉRIQUE : fonctionne pour n'importe quelle source du registre configurée en
`methode_acces: import_manuel` (voir registry/sources.yaml), pas seulement le
RDPRM — la spec l'exige explicitement ("généralisable à toute source dans une
situation similaire").
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from observador.matching import spheres_probables
from observador.models.notification import ModeUsage, Notification
from observador.models.profile import Profile
from observador.models.signal import Signal
from observador.registry.loader import Registry, get_registry
from observador.resolution import resolve_company
from observador.sources.base import RawSignal


class ImportManuelError(ValueError):
    """L'import demandé ne respecte pas la configuration du registre (source
    inconnue, ou pas déclarée en `methode_acces: import_manuel`)."""


def importer_document_manuel(
    db_session: Session,
    source_id: str,
    nom_entreprise: str,
    *,
    valeur_associee: float | None = None,
    titre_ou_description: str | None = None,
    date_evenement: datetime | None = None,
    adresse: str | None = None,
    ville: str | None = None,
    region: str | None = None,
    champs: dict | None = None,
    importe_par: str | None = None,
    registry: Registry | None = None,
) -> Signal:
    """Crée un Signal à partir d'un document/résultat obtenu hors ligne par
    l'utilisateur, et le fait entrer dans le pipeline exactement comme un
    signal automatisé : même résolution NEQ (observador.resolution.
    resolve_company), même dossier cumulatif (Company), même schéma Signal.

    La rigueur de calibration (spec : "un document RDPRM importé manuellement
    doit passer par le même filtre que documenté en section 7") reste la
    responsabilité de l'utilisateur au moment de choisir QUOI importer — le
    code ne peut pas juger la pertinence d'un document arbitraire, mais
    `valeur_associee`/`champs` sont conservés intégralement pour que le
    scoring applique les mêmes critères qu'une source automatisée équivalente
    (ex. nature_bien pour RDPRM, voir observador/scoring.py)."""
    registry = registry or get_registry()
    source_def = registry.sources.get(source_id)
    if source_def is None:
        raise ImportManuelError(f"Source inconnue: {source_id!r}")
    if not source_def.est_import_manuel:
        raise ImportManuelError(
            f"La source {source_id!r} n'est pas configurée en `methode_acces: import_manuel` "
            f"(méthode actuelle: {source_def.methode_acces!r}) — l'import manuel n'est prévu "
            "que pour les sources déclarées ainsi dans registry/sources.yaml."
        )
    if not source_def.signal_associe:
        raise ImportManuelError(f"La source {source_id!r} n'a aucun type de signal associé.")

    signal_type_id = source_def.signal_associe[0]
    maintenant = datetime.now(timezone.utc)

    raw = RawSignal(
        signal_type_id=signal_type_id,
        nom_entreprise=nom_entreprise,
        detected_at=date_evenement or maintenant,
        source_ref=f"{source_id}:import_manuel:{maintenant.isoformat()}",
        adresse=adresse,
        ville=ville,
        region=region,
        valeur_associee=valeur_associee,
        titre_ou_description=titre_ou_description,
        champs=champs or {},
    )

    company = resolve_company(db_session, raw)

    signal = Signal(
        company_id=company.id,
        source_id=source_id,
        signal_type_id=signal_type_id,
        source_ref=raw.source_ref,
        detected_at=raw.detected_at,
        valeur_associee=raw.valeur_associee,
        titre_ou_description=raw.titre_ou_description,
        champs=raw.champs,
        spheres_probables=spheres_probables(signal_type_id, registry),
        methode_acces="import_manuel",
        importe_par=importe_par,
    )
    db_session.add(signal)
    db_session.commit()
    return signal


def traiter_apres_import(
    db_session: Session, signal: Signal, profiles: list[Profile], registry: Registry | None = None
) -> list[Notification]:
    """Lance immédiatement le reste du pipeline — vérifications de base, score
    de confiance, notification — pour l'entreprise concernée par ce signal
    importé, contre chaque profil fourni (spec : "entre immédiatement dans la
    même boucle de traitement que toute source automatisée"). Même fonction
    que le moteur utilise pour une source automatisée
    (engine._traiter_entreprise_pour_profil) — aucune mécanique séparée."""
    from observador.engine import _traiter_entreprise_pour_profil, deliver_notification

    registry = registry or get_registry()
    notifications = []
    for profile in profiles:
        if not profile.besoins_fournisseur():
            continue
        notif = _traiter_entreprise_pour_profil(
            db_session, signal.company, profile, ModeUsage.VEILLE_CONTINUE, registry
        )
        if notif:
            deliver_notification(db_session, notif, registry)
            notifications.append(notif)
    return notifications
