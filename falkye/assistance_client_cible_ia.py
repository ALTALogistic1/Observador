"""Assistance à la configuration du profil par IA — Niveau 2, dimension "qui"
(client cible) — spec section 8bis (2026-09-03), miroir exact de
falkye/assistance_sphere_ia.py contre le registre ClientCible plutôt que
Sphere. Voir falkye/assistance_ia.py pour le mécanisme partagé complet.

Une seule sentinelle, `aucune_correspondance` — PAS de sentinelle séparée
pour "aucune restriction" : `aucune_restriction`
(falkye/models/client_cible.py::ID_AUCUNE_RESTRICTION) est un membre RÉEL du
catalogue passé au modèle (comme n'importe quelle autre catégorie), pas un
cas hors catalogue à traiter à part — le modèle le sélectionne normalement
via `liens` quand la description indique une clientèle non restreinte.
`aucune_correspondance` reste le seul vrai signal d'échec (rien, même pas
"s'applique largement", ne convient) qui déclenche la journalisation."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from falkye.assistance_client_cible import SuggestionClientCible
from falkye.assistance_ia import (
    AssistanceIANonConfiguree,  # noqa: F401 -- réexporté pour les appelants (cli.py)
    PlanInsuffisantPourAssistanceIA,  # noqa: F401 -- réexporté pour les appelants (cli.py)
    ResultatNiveau2,
    classifier_niveau2,
    departager_niveau2,
)
from falkye.models.client_cible import ClientCible
from falkye.models.client_cible_synonyme import ClientCibleSynonyme
from falkye.models.diagnostic_journal import DiagnosticJournal, TypeDiagnostic
from falkye.models.profile import Profile

_SENTINELLE_AUCUNE_CORRESPONDANCE = "aucune_correspondance"

_CONTEXTE = (
    "Tu aides à classer la description libre de la clientèle cible d'un utilisateur "
    "(\"qui\" il vend/offre son service, PAS ce qu'il offre) dans une ou plusieurs "
    "catégories existantes. Une catégorie du catalogue, \"aucune_restriction\", "
    "représente une clientèle délibérément non restreinte (\"s'applique largement\", "
    "\"tous types d'entreprises\") — c'est une réponse VALIDE et positive au même titre "
    "qu'une catégorie précise, sélectionne-la normalement si le texte l'indique, ce "
    "n'est PAS un cas d'échec. Si le texte décrit une clientèle si large qu'elle "
    "correspondrait à une TRÈS large proportion des catégories du catalogue (pas "
    "seulement deux ou trois qui se recoupent, mais la quasi-totalité), retourne "
    "directement \"aucune_restriction\" seule plutôt qu'une longue liste de liens — "
    "c'est la même situation exprimée plus simplement, pas un cas différent."
)


@dataclass(frozen=True)
class LienClientCiblePropose:
    client_cible_id: str
    client_cible_nom: str
    poids: float


@dataclass(frozen=True)
class SuggestionClientCibleNiveau2:
    liens: list[LienClientCiblePropose]
    confiance: str
    raisonnement: str
    candidat_diagnostic_id: int | None = None
    synonyme_retenu: str | None = None
    niveau: int = 2


def _catalogue(db_session: Session) -> list[tuple[str, str]]:
    return [(c.id, c.nom) for c in db_session.query(ClientCible).order_by(ClientCible.id).all()]


def _persister(
    db_session: Session, resultat: ResultatNiveau2, profile: Profile, texte_description: str
) -> SuggestionClientCibleNiveau2:
    if not resultat.liens:
        candidat = DiagnosticJournal(
            type_diagnostic=TypeDiagnostic.CANDIDAT_CLIENT_CIBLE,
            profile_id=profile.id,
            texte_description=texte_description,
            resume_niveau2=resultat.raisonnement,
            statut="a_examiner",
        )
        db_session.add(candidat)
        db_session.commit()
        return SuggestionClientCibleNiveau2(
            liens=[], confiance=resultat.confiance, raisonnement=resultat.raisonnement,
            candidat_diagnostic_id=candidat.id,
        )

    synonyme_retenu = None
    if resultat.synonyme_a_retenir and resultat.synonyme_a_retenir.strip():
        client_cible_id_principal = max(resultat.liens, key=lambda l: l.poids).id
        texte_syn = resultat.synonyme_a_retenir.strip()
        existe_deja = (
            db_session.query(ClientCibleSynonyme)
            .filter(
                ClientCibleSynonyme.client_cible_id == client_cible_id_principal,
                ClientCibleSynonyme.texte.ilike(texte_syn),
            )
            .first()
        )
        if existe_deja is None:
            db_session.add(
                ClientCibleSynonyme(
                    client_cible_id=client_cible_id_principal, texte=texte_syn, origine="ia_niveau2"
                )
            )
            db_session.commit()
            synonyme_retenu = texte_syn

    return SuggestionClientCibleNiveau2(
        liens=[
            LienClientCiblePropose(client_cible_id=l.id, client_cible_nom=l.nom, poids=l.poids)
            for l in resultat.liens
        ],
        confiance=resultat.confiance,
        raisonnement=resultat.raisonnement,
        synonyme_retenu=synonyme_retenu,
    )


def suggerer_clients_cibles_niveau2(
    db_session: Session, profile: Profile, texte_description: str
) -> SuggestionClientCibleNiveau2:
    """Classification complète (le Niveau 1 a échoué)."""
    resultat = classifier_niveau2(
        profile,
        texte_description,
        catalogue=_catalogue(db_session),
        sentinelles=[_SENTINELLE_AUCUNE_CORRESPONDANCE],
        contexte=_CONTEXTE,
    )
    return _persister(db_session, resultat, profile, texte_description)


def departager_clients_cibles_niveau2(
    db_session: Session,
    profile: Profile,
    texte_description: str,
    candidats: list[SuggestionClientCible],
) -> SuggestionClientCibleNiveau2:
    """Départage à portée réduite (tie exact au Niveau 1)."""
    resultat = departager_niveau2(
        profile,
        texte_description,
        candidats=[(c.client_cible_id, c.client_cible_nom) for c in candidats],
        contexte=_CONTEXTE,
    )
    return _persister(db_session, resultat, profile, texte_description)
