"""Résolution NEQ/REQ — le pivot de tout le pipeline (spec section 9, "Le NEQ comme
identifiant pivot pour la déduplication" ; section 7, "principe de complétude").

Chaque RawSignal produit par un connecteur passe par ici AVANT de devenir un Signal
persisté : on trouve ou crée le Company (dossier cumulatif) correspondant, on tente
de résoudre son NEQ via le REQ s'il n'est pas déjà connu, et on complète
adresse/secteur/statut légal quand la source ne les fournissait pas directement.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from falkye.dedup_entreprises import (
    SEUIL_FUSION_AUTO,
    journaliser_candidat_fusion,
    trouver_meilleur_candidat_fusion,
)
from falkye.models.company import Company, StatutLegal, StatutResolution
from falkye.sources import req as req_source
from falkye.sources.base import RawSignal
from falkye.sources.column_mapping import normaliser

logger = logging.getLogger(__name__)

# Seuils de confiance sur le score de correspondance floue du nom (0-100, rapidfuzz).
# Choisis pour respecter la vérification obligatoire section 6, point 3 : "si le nom
# d'entreprise détecté par une source ne peut pas être résolu avec confiance à un NEQ
# unique au REQ, le prospect doit être marqué comme non vérifié plutôt que présenté
# avec un NEQ potentiellement erroné" — on préfère donc être conservateur.
SEUIL_RESOLUTION_CONFIANTE = 92.0
SEUIL_AMBIGUITE_ECART_MIN = 8.0  # écart minimal avec le 2e candidat pour ne pas être "ambigu"


def _find_unresolved_company(db_session: Session, nom_detecte: str) -> Company | None:
    """Recherche indexée (Company.nom_detecte_normalise), pas un balayage Python de
    toutes les entreprises non résolues — voir le commentaire sur cette colonne dans
    falkye/models/company.py (sinon quadratique sur de gros volumes, ex. SEAO)."""
    nom_norm = normaliser(nom_detecte)
    return db_session.execute(
        select(Company).where(Company.neq.is_(None), Company.nom_detecte_normalise == nom_norm)
    ).scalar_one_or_none()


def resolve_company(db_session: Session, raw: RawSignal) -> Company:
    """Trouve ou crée le Company (dossier cumulatif) correspondant à ce signal brut,
    et tente sa résolution NEQ si elle n'est pas déjà acquise."""

    neq = raw.neq
    matches: list[req_source.REQMatch] = []

    if neq is None:
        matches = req_source.resolve_neq_by_name(db_session, raw.nom_entreprise, ville=raw.ville)
        if matches:
            top = matches[0]
            second_score = matches[1].score if len(matches) > 1 else 0.0
            if top.score >= SEUIL_RESOLUTION_CONFIANTE and (
                top.score - second_score >= SEUIL_AMBIGUITE_ECART_MIN or len(matches) == 1
            ):
                neq = top.entry.neq
            else:
                logger.info(
                    "Résolution NEQ ambiguë pour %r : top=%.1f, 2e=%.1f",
                    raw.nom_entreprise,
                    top.score,
                    second_score,
                )

    if neq is not None:
        company = db_session.execute(select(Company).where(Company.neq == neq)).scalar_one_or_none()
        if company is None:
            company = Company(
                neq=neq, nom_detecte=raw.nom_entreprise, nom_detecte_normalise=normaliser(raw.nom_entreprise)
            )
            db_session.add(company)
        company.statut_resolution = StatutResolution.RESOLU
        _enrich_from_req(db_session, company, neq)
    else:
        company = _find_unresolved_company(db_session, raw.nom_entreprise)
        if company is None:
            # Correspondance EXACTE absente — avant de créer une NOUVELLE fiche,
            # tente un rapprochement FLOU parmi les Company déjà sans NEQ (spec
            # section 8bis, point 4, 2026-09-03 — voir falkye/dedup_entreprises.py
            # pour le détail des deux seuils). L'entreprise existante trouvée est
            # TOUJOURS le "principal" ici : elle existait déjà avant ce signal, donc
            # forcément plus ancienne (`first_detected_at`) que la fiche qu'on
            # s'apprête à créer.
            nom_norm = normaliser(raw.nom_entreprise)
            meilleur = trouver_meilleur_candidat_fusion(db_session, nom_norm, raw.ville)
            if meilleur is not None and meilleur.score >= SEUIL_FUSION_AUTO:
                company = meilleur.company  # ancrage fort — jamais une nouvelle fiche créée
            else:
                company = Company(
                    neq=None, nom_detecte=raw.nom_entreprise, nom_detecte_normalise=nom_norm
                )
                db_session.add(company)
                db_session.flush()  # company.id requis avant de journaliser un candidat
                if meilleur is not None:  # 90 <= score < 95 — jamais fusionné seul
                    journaliser_candidat_fusion(
                        db_session, meilleur.company, company, meilleur.score, statut="a_examiner"
                    )
        company.statut_resolution = (
            StatutResolution.AMBIGU if matches else StatutResolution.NON_TROUVE
        )

    # Champs capturés directement par la source : toujours prioritaires sur le REQ
    # (spec section 7 : "capturer ces champs directement quand ils sont disponibles").
    if raw.adresse:
        company.adresse = raw.adresse
    if raw.ville:
        company.ville = raw.ville
    if raw.region:
        company.region = raw.region
    if raw.secteur_activite:
        company.secteur_activite_libelle = raw.secteur_activite
    if raw.site_web and not company.site_web:
        company.site_web = raw.site_web

    db_session.flush()
    return company


def _enrich_from_req(db_session: Session, company: Company, neq: str) -> None:
    entry = req_source.get_by_neq(db_session, neq)
    if entry is None:
        return
    company.nom_officiel_req = entry.nom
    company.statut_legal = (
        StatutLegal.RADIEE if entry.statut == "radiee" else StatutLegal.IMMATRICULEE
    )
    if not company.adresse and entry.adresse:
        company.adresse = entry.adresse
    if not company.ville and entry.ville:
        company.ville = entry.ville
    if not company.region and entry.region:
        company.region = entry.region
    if entry.code_postal:
        company.code_postal = entry.code_postal
    if not company.secteur_activite_libelle and entry.secteur_libelle:
        company.secteur_activite_code = entry.secteur_code
        company.secteur_activite_libelle = entry.secteur_libelle
