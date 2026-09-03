"""Assistance à la configuration du profil par IA — Niveau 2 (spec Radar+, point 8,
ajoutée le 2026-09-03, confirmée le 2026-09-03).

Déclenché SEULEMENT quand le Niveau 1 échoue (falkye/assistance_sphere.py::
suggerer_spheres_niveau1 retourne une liste vide) — jamais en remplacement, jamais
en parallèle systématique du Niveau 1, pour limiter le coût par appel.

Gating BINAIRE Radar/Radar+ (confirmé par Alexandre le 2026-09-03 : "pas de
système de quota pour le Niveau 2") — même principe que partout ailleurs dans le
produit (falkye/notifications/webhook_channel.py, falkye/ponderation.py) : le
plan gate l'USAGE, jamais un compteur d'appels séparé.

GARDE-FOU STRUCTUREL NON NÉGOCIABLE (spec, confirmé explicitement par Alexandre
comme "exactement ce qu'on voulait, pas juste une instruction") : le modèle ne
peut PHYSIQUEMENT pas inventer une nouvelle sphère. La sortie est contrainte par
schéma JSON (output_config, voir _construire_schema_sortie) à un `sphere_id` pris
dans une énumération FERMÉE = les sphères EXISTANTES en base au moment de l'appel,
plus la valeur sentinelle "aucune_correspondance" — aucune chaîne libre n'est un
choix valide pour ce champ, donc aucune sortie valide du modèle ne peut nommer une
sphère qui n'existe pas déjà. C'est le schéma qui rend le cas impossible, pas
seulement le prompt qui le déconseille. Un cas "aucune_correspondance" est
journalisé comme CandidatSphere (falkye/models/candidat_sphere.py) pour examen
par Alexandre — jamais auto-résolu, exactement comme "Financement" a été ajoutée
par décision humaine (falkye/registry/spheres.yaml). Un cas rattaché à une sphère
existante peut silencieusement enrichir SON dictionnaire de synonymes
(SphereSynonyme, origine="ia_niveau2") mais ne touche jamais
falkye/registry/spheres.yaml ni la table Sphere elle-même.

Comme partout ailleurs dans le produit, ce module ne fait que PROPOSER : il
n'écrit jamais `profile_needs` — voir falkye/cli.py::profile_suggerer_sphere_cmd,
qui affiche la suggestion et laisse l'utilisateur confirmer ou corriger.

STATUT DE VALIDATION : construit et testé contre le SDK Anthropic mocké (voir
tests/test_assistance_sphere_ia.py) — aucune clé API réelle disponible dans cet
environnement de développement (même situation que Stripe/HubSpot/Pipedrive, voir
docs/STATUT_RESEAU.md). Validation en direct à faire une fois qu'Alexandre fournit
une vraie ANTHROPIC_API_KEY.

CHOIX DE MODÈLE : claude-haiku-4-5 par défaut (FALKYE_ANTHROPIC_MODEL_NIVEAU2,
voir .env.example) plutôt que le modèle le plus capable — décision assumée, pas
un oubli : cette tâche est une classification fermée à choix contraint (le schéma
de sortie fait déjà tout le travail de robustesse structurelle), pas une tâche
ouverte ou créative, et Radar/Radar+ restent des paliers sensibles au coût par
appel (même Écho, le palier le plus bas, n'est lui-même jamais gratuit — spec
section 9bis). Ajustable via variable d'environnement si l'usage réel montre que
Haiku ne suffit pas pour ce catalogue de sphères.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

from sqlalchemy.orm import Session

from falkye.models.candidat_sphere import CandidatSphere
from falkye.models.profile import PlanTarifaire, Profile
from falkye.models.sphere import Sphere
from falkye.models.sphere_synonyme import SphereSynonyme

_SENTINELLE_AUCUNE_CORRESPONDANCE = "aucune_correspondance"
_MODELE_PAR_DEFAUT = "claude-haiku-4-5"


class PlanInsuffisantPourAssistanceIA(RuntimeError):
    """Levée quand un profil Écho tente d'utiliser le Niveau 2 (Radar/Radar+ seulement)."""


class AssistanceIANonConfiguree(RuntimeError):
    """Levée quand ANTHROPIC_API_KEY n'est pas configurée."""


@dataclass(frozen=True)
class SuggestionNiveau2:
    sphere_id: str | None  # None si aucune sphère existante ne correspond
    sphere_nom: str | None
    confiance: str  # "faible" | "moyenne" | "elevee"
    raisonnement: str
    candidat_sphere_id: int | None = None  # rempli si journalisé comme candidat
    synonyme_retenu: str | None = None  # rempli si le dictionnaire a été enrichi
    niveau: int = 2


def _verifier_plan(profile: Profile) -> None:
    if profile.plan == PlanTarifaire.ECHO:
        raise PlanInsuffisantPourAssistanceIA(
            f"Le Niveau 2 de l'assistance IA est réservé aux plans Radar et Radar+ "
            f"(profil #{profile.id} est au plan Écho)."
        )


def _construire_schema_sortie(sphere_ids: list[str]) -> dict:
    """Schéma JSON contraint — voir docstring du module pour pourquoi `sphere_id`
    en `enum` fermé est LE garde-fou structurel, pas une simple instruction."""
    return {
        "type": "json_schema",
        "schema": {
            "type": "object",
            "properties": {
                "sphere_id": {
                    "type": "string",
                    "enum": [*sphere_ids, _SENTINELLE_AUCUNE_CORRESPONDANCE],
                },
                "confiance": {"type": "string", "enum": ["faible", "moyenne", "elevee"]},
                "raisonnement": {"type": "string"},
                "synonyme_a_retenir": {"type": ["string", "null"]},
            },
            "required": ["sphere_id", "confiance", "raisonnement", "synonyme_a_retenir"],
            "additionalProperties": False,
        },
    }


def _construire_prompt(texte_description: str, spheres: list[Sphere]) -> str:
    catalogue = "\n".join(f"- {s.id} : {s.nom}" for s in spheres)
    return (
        "Tu aides à classer la description libre d'un usage professionnel dans une "
        "sphère de besoin existante. Voici le catalogue FERMÉ de sphères existantes "
        "(id : nom) :\n"
        f"{catalogue}\n\n"
        "Description fournie par l'utilisateur :\n"
        f'"{texte_description}"\n\n'
        "Si une sphère du catalogue correspond clairement, retourne son id exact. "
        "Si AUCUNE sphère du catalogue ne convient raisonnablement, retourne "
        f'"{_SENTINELLE_AUCUNE_CORRESPONDANCE}" — n\'invente JAMAIS un nouvel id, '
        "même si tu penses qu'une catégorie manque : ce cas doit être signalé pour "
        "examen humain, pas résolu par toi. Si tu identifies une sphère existante, "
        "propose aussi dans synonyme_a_retenir un court mot-clé ou expression tiré "
        "de la description qui aiderait à reconnaître des cas similaires sans appel "
        "IA la prochaine fois (ou null si rien d'utile à en tirer)."
    )


def suggerer_sphere_niveau2(
    db_session: Session, profile: Profile, texte_description: str
) -> SuggestionNiveau2:
    """Appelle Claude (Niveau 2) pour `texte_description`, déjà refusée par le
    Niveau 1. Gate le plan, puis enrichit silencieusement un dictionnaire de
    synonymes existant OU journalise un CandidatSphere — jamais les deux, jamais
    la création d'une sphère. Ne modifie JAMAIS `profile_needs` : la suggestion
    reste à confirmer par l'utilisateur (voir falkye/cli.py)."""
    _verifier_plan(profile)

    import anthropic

    cle = os.environ.get("ANTHROPIC_API_KEY")
    if not cle:
        raise AssistanceIANonConfiguree(
            "ANTHROPIC_API_KEY non configurée (voir .env.example) — impossible d'appeler le Niveau 2."
        )

    spheres = db_session.query(Sphere).order_by(Sphere.id).all()
    sphere_ids = [s.id for s in spheres]
    noms_par_id = {s.id: s.nom for s in spheres}

    modele = os.environ.get("FALKYE_ANTHROPIC_MODEL_NIVEAU2", _MODELE_PAR_DEFAUT)
    client = anthropic.Anthropic(api_key=cle)
    response = client.messages.create(
        model=modele,
        max_tokens=1024,
        messages=[{"role": "user", "content": _construire_prompt(texte_description, spheres)}],
        output_config={"format": _construire_schema_sortie(sphere_ids)},
    )
    texte_json = next(b.text for b in response.content if b.type == "text")
    data = json.loads(texte_json)

    sphere_id = data["sphere_id"]
    raisonnement = data["raisonnement"]
    confiance = data["confiance"]
    synonyme_a_retenir = data.get("synonyme_a_retenir")

    if sphere_id == _SENTINELLE_AUCUNE_CORRESPONDANCE:
        candidat = CandidatSphere(
            profile_id=profile.id,
            texte_description=texte_description,
            resume_niveau2=raisonnement,
            statut="a_examiner",
        )
        db_session.add(candidat)
        db_session.commit()
        return SuggestionNiveau2(
            sphere_id=None,
            sphere_nom=None,
            confiance=confiance,
            raisonnement=raisonnement,
            candidat_sphere_id=candidat.id,
        )

    synonyme_retenu = None
    if synonyme_a_retenir and synonyme_a_retenir.strip():
        texte_syn = synonyme_a_retenir.strip()
        existe_deja = (
            db_session.query(SphereSynonyme)
            .filter(
                SphereSynonyme.sphere_id == sphere_id,
                SphereSynonyme.texte.ilike(texte_syn),
            )
            .first()
        )
        if existe_deja is None:
            db_session.add(
                SphereSynonyme(sphere_id=sphere_id, texte=texte_syn, origine="ia_niveau2")
            )
            db_session.commit()
            synonyme_retenu = texte_syn

    return SuggestionNiveau2(
        sphere_id=sphere_id,
        sphere_nom=noms_par_id.get(sphere_id),
        confiance=confiance,
        raisonnement=raisonnement,
        synonyme_retenu=synonyme_retenu,
    )
