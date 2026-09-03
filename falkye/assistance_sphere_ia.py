"""Assistance à la configuration du profil par IA — Niveau 2, dimension sphère
("quoi") — spec section 8bis (2026-09-03), enveloppe mince autour du moteur
généralisé falkye/assistance_ia.py (voir sa docstring pour le mécanisme
complet : les deux modes classifier_niveau2/departager_niveau2, le garde-fou
structurel, le gating par plan).

Ce module ne fait que : construire le catalogue (toutes les Sphere en base),
le contexte du prompt, et PERSISTER le résultat côté sphère spécifiquement —
enrichissement silencieux de SphereSynonyme (jamais registry/spheres.yaml) ou
journalisation dans falkye/models/diagnostic_journal.py
(type_diagnostic=CANDIDAT_SPHERE, remplace l'ancien CandidatSphere).

Comme partout ailleurs dans le produit, ce module ne fait que PROPOSER : il
n'écrit jamais `profile_needs`/`profile_need_spheres` — voir
falkye/cli.py::profile_configurer_besoin_cmd, qui affiche la proposition et
laisse l'utilisateur confirmer."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from falkye.assistance_ia import (
    AssistanceIANonConfiguree,  # noqa: F401 -- réexporté pour les appelants (cli.py)
    PlanInsuffisantPourAssistanceIA,  # noqa: F401 -- réexporté pour les appelants (cli.py)
    ResultatNiveau2,
    classifier_niveau2,
    departager_niveau2,
)
from falkye.assistance_sphere import SuggestionSphere
from falkye.models.diagnostic_journal import DiagnosticJournal, TypeDiagnostic
from falkye.models.profile import Profile
from falkye.models.sphere import Sphere
from falkye.models.sphere_synonyme import SphereSynonyme

_SENTINELLE_AUCUNE_CORRESPONDANCE = "aucune_correspondance"

_CONTEXTE = (
    "Tu aides à classer la description libre d'un service professionnel dans une ou "
    "PLUSIEURS sphères de besoin existantes (\"quoi\" un utilisateur offre) — un service "
    "peut légitimement appartenir à plusieurs sphères à la fois (ex. l'implantation d'un "
    "système logiciel de gestion d'inventaire touche à la fois la technologie/systèmes et "
    "les opérations qu'il sert)."
)


@dataclass(frozen=True)
class LienSpherePropose:
    sphere_id: str
    sphere_nom: str
    poids: float


@dataclass(frozen=True)
class SuggestionSphereNiveau2:
    liens: list[LienSpherePropose]
    confiance: str
    raisonnement: str
    candidat_diagnostic_id: int | None = None  # rempli si journalisé (aucune correspondance)
    synonyme_retenu: str | None = None
    niveau: int = 2


def _catalogue(db_session: Session) -> list[tuple[str, str]]:
    return [(s.id, s.nom) for s in db_session.query(Sphere).order_by(Sphere.id).all()]


def _persister(
    db_session: Session, resultat: ResultatNiveau2, profile: Profile, texte_description: str
) -> SuggestionSphereNiveau2:
    if not resultat.liens:
        candidat = DiagnosticJournal(
            type_diagnostic=TypeDiagnostic.CANDIDAT_SPHERE,
            profile_id=profile.id,
            texte_description=texte_description,
            resume_niveau2=resultat.raisonnement,
            statut="a_examiner",
        )
        db_session.add(candidat)
        db_session.commit()
        return SuggestionSphereNiveau2(
            liens=[], confiance=resultat.confiance, raisonnement=resultat.raisonnement,
            candidat_diagnostic_id=candidat.id,
        )

    synonyme_retenu = None
    if resultat.synonyme_a_retenir and resultat.synonyme_a_retenir.strip():
        sphere_id_principal = max(resultat.liens, key=lambda l: l.poids).id
        texte_syn = resultat.synonyme_a_retenir.strip()
        existe_deja = (
            db_session.query(SphereSynonyme)
            .filter(SphereSynonyme.sphere_id == sphere_id_principal, SphereSynonyme.texte.ilike(texte_syn))
            .first()
        )
        if existe_deja is None:
            db_session.add(SphereSynonyme(sphere_id=sphere_id_principal, texte=texte_syn, origine="ia_niveau2"))
            db_session.commit()
            synonyme_retenu = texte_syn

    return SuggestionSphereNiveau2(
        liens=[LienSpherePropose(sphere_id=l.id, sphere_nom=l.nom, poids=l.poids) for l in resultat.liens],
        confiance=resultat.confiance,
        raisonnement=resultat.raisonnement,
        synonyme_retenu=synonyme_retenu,
    )


def suggerer_spheres_niveau2(
    db_session: Session, profile: Profile, texte_description: str
) -> SuggestionSphereNiveau2:
    """Classification complète (le Niveau 1 a échoué)."""
    resultat = classifier_niveau2(
        profile,
        texte_description,
        catalogue=_catalogue(db_session),
        sentinelles=[_SENTINELLE_AUCUNE_CORRESPONDANCE],
        contexte=_CONTEXTE,
    )
    return _persister(db_session, resultat, profile, texte_description)


def departager_spheres_niveau2(
    db_session: Session, profile: Profile, texte_description: str, candidats: list[SuggestionSphere]
) -> SuggestionSphereNiveau2:
    """Départage à portée réduite (le Niveau 1 a produit un tie exact entre
    `candidats`, déjà des correspondances réelles — pas un échec)."""
    resultat = departager_niveau2(
        profile,
        texte_description,
        candidats=[(c.sphere_id, c.sphere_nom) for c in candidats],
        contexte=_CONTEXTE,
    )
    return _persister(db_session, resultat, profile, texte_description)
