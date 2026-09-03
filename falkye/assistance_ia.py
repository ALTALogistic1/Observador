"""Moteur Niveau 2 généralisé de l'assistance à la configuration du profil par
IA — spec section 8bis (2026-09-03), généralisation de l'ancien
falkye/assistance_sphere_ia.py (créé le 2026-09-03 pour la seule sphère).

Née de deux besoins qui appellent EXACTEMENT le même changement de schéma
(confirmé par Alexandre, "un seul schéma généralisé, pas deux formats
séparés") :
  1. Un service peut légitimement appartenir à PLUSIEURS sphères à la fois —
     un cas réel (implantation ERP/WMS) a produit un partage à ÉGALITÉ EXACTE
     entre deux sphères au Niveau 1 ; forcer un seul gagnant aurait perdu du
     signal. La sortie doit donc être un ENSEMBLE pondéré, pas un seul id.
  2. La dimension "qui" (client cible, falkye/assistance_client_cible_ia.py)
     a besoin du même mécanisme contre un registre différent.

GARDE-FOU STRUCTUREL NON NÉGOCIABLE, inchangé depuis la première version : le
modèle ne peut PHYSIQUEMENT pas inventer un id hors catalogue. Chaque `id`
dans `liens` est contraint par schéma JSON (`output_config`) à une énumération
FERMÉE = le catalogue passé en argument — jamais une chaîne libre. C'est le
schéma qui rend le cas impossible, pas seulement le prompt qui le déconseille.

DEUX MODES, appelés par les modules spécifiques à un registre
(falkye/assistance_sphere_ia.py, falkye/assistance_client_cible_ia.py) :

  - `classifier_niveau2` — classification complète depuis rien (le Niveau 1 a
    échoué, liste vide) : le catalogue est TOUT le registre, une `sentinelle`
    ("aucune_correspondance") est possible si vraiment rien ne convient — ce
    cas doit être journalisé pour examen humain (falkye/models/
    diagnostic_journal.py), jamais auto-résolu.

  - `departager_niveau2` — départage à PORTÉE RÉDUITE : le Niveau 1 a déjà
    trouvé plusieurs candidats à ÉGALITÉ EXACTE (pas un échec) ; le catalogue
    passé est restreint à CES candidats-là, pas tout le registre, et il n'y a
    PAS de sentinelle "aucune_correspondance" (ces candidats existent déjà,
    prouvés par une correspondance réelle du Niveau 1 — rien à signaler comme
    non résolu). Le modèle retourne ses poids relatifs avec son propre
    raisonnement contextuel — AUCUNE règle mécanique de départage (ordre
    alphabétique, premier trouvé) n'est codée nulle part : le poids EST déjà
    le classement (dérivé, jamais une colonne séparée sur le lien), donc
    "principal" tombe naturellement du côté le plus élevé une fois ce poids
    appliqué.

Gating BINAIRE Radar/Radar+ (jamais Écho, pas de système de quota) —
inchangé, même principe que partout ailleurs dans le produit.

CHOIX DE MODÈLE inchangé : claude-haiku-4-5 par défaut
(FALKYE_ANTHROPIC_MODEL_NIVEAU2) — classification fermée à choix contraint,
pas une tâche ouverte ou créative.

STATUT DE VALIDATION : construit et testé contre le SDK Anthropic mocké —
aucune clé API réelle disponible dans cet environnement de développement."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from falkye.models.profile import PlanTarifaire, Profile

_MODELE_PAR_DEFAUT = "claude-haiku-4-5"


class PlanInsuffisantPourAssistanceIA(RuntimeError):
    """Levée quand un profil Écho tente d'utiliser le Niveau 2 (Radar/Radar+ seulement)."""


class AssistanceIANonConfiguree(RuntimeError):
    """Levée quand ANTHROPIC_API_KEY n'est pas configurée."""


@dataclass(frozen=True)
class LienPondere:
    """Un id du catalogue (sphère ou client cible) retenu, avec son poids
    relatif (0-100) — voir docstring du module."""

    id: str
    nom: str
    poids: float


@dataclass(frozen=True)
class ResultatNiveau2:
    liens: list[LienPondere] = field(default_factory=list)
    sentinelle: str | None = None  # None sauf en mode classifier_niveau2
    confiance: str = "moyenne"
    raisonnement: str = ""
    synonyme_a_retenir: str | None = None


def _verifier_plan(profile: Profile) -> None:
    if profile.plan == PlanTarifaire.ECHO:
        raise PlanInsuffisantPourAssistanceIA(
            f"Le Niveau 2 de l'assistance IA est réservé aux plans Radar et Radar+ "
            f"(profil #{profile.id} est au plan Écho)."
        )


def _client_et_modele(profile: Profile):
    _verifier_plan(profile)
    import anthropic

    cle = os.environ.get("ANTHROPIC_API_KEY")
    if not cle:
        raise AssistanceIANonConfiguree(
            "ANTHROPIC_API_KEY non configurée (voir .env.example) — impossible d'appeler le Niveau 2."
        )
    modele = os.environ.get("FALKYE_ANTHROPIC_MODEL_NIVEAU2", _MODELE_PAR_DEFAUT)
    return anthropic.Anthropic(api_key=cle), modele


def _schema_liens_ponderes(ids_valides: list[str], *, avec_sentinelle: list[str] | None) -> dict:
    """`liens` : ensemble {id, poids} — chaque id contraint à `ids_valides`
    (le garde-fou structurel). `sentinelle` optionnelle, seulement pour
    classifier_niveau2 (voir docstring du module)."""
    proprietes: dict = {
        "liens": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "enum": ids_valides},
                    "poids": {"type": "number", "minimum": 0, "maximum": 100},
                },
                "required": ["id", "poids"],
                "additionalProperties": False,
            },
        },
        "confiance": {"type": "string", "enum": ["faible", "moyenne", "elevee"]},
        "raisonnement": {"type": "string"},
        "synonyme_a_retenir": {"type": ["string", "null"]},
    }
    requis = ["liens", "confiance", "raisonnement", "synonyme_a_retenir"]
    if avec_sentinelle is not None:
        proprietes["sentinelle"] = {"type": ["string", "null"], "enum": [*avec_sentinelle, None]}
        requis.append("sentinelle")
    return {
        "type": "json_schema",
        "schema": {
            "type": "object",
            "properties": proprietes,
            "required": requis,
            "additionalProperties": False,
        },
    }


def _prompt_classification(
    texte_description: str, catalogue: list[tuple[str, str]], sentinelles: list[str], contexte: str
) -> str:
    lignes_catalogue = "\n".join(f"- {id_} : {nom}" for id_, nom in catalogue)
    lignes_sentinelles = "\n".join(f'- "{s}"' for s in sentinelles)
    return (
        f"{contexte}\n\n"
        f"Catalogue FERMÉ des catégories existantes (id : nom) :\n{lignes_catalogue}\n\n"
        f'Description fournie par l\'utilisateur :\n"{texte_description}"\n\n'
        "Retourne dans `liens` UNE OU PLUSIEURS catégories du catalogue qui s'appliquent, "
        "chacune avec un poids de 0 à 100 reflétant sa pertinence RELATIVE (100 = la plus "
        "pertinente ; si plusieurs catégories s'appliquent à la fois, distribue les poids selon "
        "ton propre jugement contextuel, jamais une règle mécanique comme l'ordre alphabétique). "
        f"Si AUCUNE catégorie ne convient, laisse `liens` vide et retourne dans `sentinelle` "
        f"l'une de :\n{lignes_sentinelles}\n"
        "N'invente JAMAIS un id hors de ce catalogue, même si tu penses qu'une catégorie "
        "manque : signale ce cas via la sentinelle appropriée pour examen humain, ne le résous "
        "jamais toi-même. Propose aussi dans synonyme_a_retenir un court mot-clé/expression tiré "
        "de la description qui aiderait à reconnaître des cas similaires sans appel IA la "
        "prochaine fois, pour la catégorie au poids le plus élevé (ou null si rien d'utile)."
    )


def _prompt_departage(texte_description: str, candidats: list[tuple[str, str]], contexte: str) -> str:
    lignes = "\n".join(f"- {id_} : {nom}" for id_, nom in candidats)
    return (
        f"{contexte}\n\n"
        "Le mécanisme local a déjà trouvé PLUSIEURS catégories également probables pour cette "
        f"description, à ÉGALITÉ EXACTE :\n{lignes}\n\n"
        f'Description :\n"{texte_description}"\n\n'
        "Retourne dans `liens` CES catégories, et seulement celles-là, chacune avec un poids de "
        "0 à 100 reflétant TON PROPRE raisonnement contextuel sur laquelle est la plus pertinente "
        "pour cette description précise — jamais une règle mécanique (ordre alphabétique, premier "
        "trouvé). Si elles sont vraiment équivalentes après réflexion, retourne-les au même poids "
        "plutôt que d'inventer une distinction arbitraire — explique ton choix dans `raisonnement`."
    )


def _parser_reponse(response) -> dict:
    texte_json = next(b.text for b in response.content if b.type == "text")
    return json.loads(texte_json)


def _liens_depuis_data(data: dict, catalogue: list[tuple[str, str]]) -> list[LienPondere]:
    noms = dict(catalogue)
    return [
        LienPondere(id=l["id"], nom=noms.get(l["id"], l["id"]), poids=float(l["poids"]))
        for l in data["liens"]
    ]


def classifier_niveau2(
    profile: Profile,
    texte_description: str,
    *,
    catalogue: list[tuple[str, str]],
    sentinelles: list[str],
    contexte: str,
) -> ResultatNiveau2:
    """Classification complète — le Niveau 1 a échoué (liste vide)."""
    client, modele = _client_et_modele(profile)
    response = client.messages.create(
        model=modele,
        max_tokens=1024,
        messages=[
            {"role": "user", "content": _prompt_classification(texte_description, catalogue, sentinelles, contexte)}
        ],
        output_config={
            "format": _schema_liens_ponderes([id_ for id_, _ in catalogue], avec_sentinelle=sentinelles)
        },
    )
    data = _parser_reponse(response)
    return ResultatNiveau2(
        liens=_liens_depuis_data(data, catalogue),
        sentinelle=data.get("sentinelle"),
        confiance=data["confiance"],
        raisonnement=data["raisonnement"],
        synonyme_a_retenir=data.get("synonyme_a_retenir"),
    )


def departager_niveau2(
    profile: Profile,
    texte_description: str,
    *,
    candidats: list[tuple[str, str]],
    contexte: str,
) -> ResultatNiveau2:
    """Départage à portée réduite — le Niveau 1 a produit un tie exact entre
    `candidats`. Pas de sentinelle : ces candidats existent déjà, prouvés par
    une correspondance locale réelle."""
    client, modele = _client_et_modele(profile)
    response = client.messages.create(
        model=modele,
        max_tokens=1024,
        messages=[{"role": "user", "content": _prompt_departage(texte_description, candidats, contexte)}],
        output_config={
            "format": _schema_liens_ponderes([id_ for id_, _ in candidats], avec_sentinelle=None)
        },
    )
    data = _parser_reponse(response)
    return ResultatNiveau2(
        liens=_liens_depuis_data(data, candidats),
        confiance=data["confiance"],
        raisonnement=data["raisonnement"],
    )
