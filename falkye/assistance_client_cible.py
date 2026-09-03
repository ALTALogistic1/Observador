"""Assistance à la configuration du profil par IA — Niveau 1, dimension "qui"
(client cible) — spec section 8bis, ajoutée le 2026-09-03.

Miroir structurel exact de falkye/assistance_sphere.py (même mécanisme,
registre différent) : correspondance LOCALE mot-à-mot (falkye/
texte_matching.py::motif_present), gratuite, tous plans, contre le
dictionnaire de synonymes de chaque client cible (registry/
clients_cibles.yaml::ClientCibleDef.synonymes, resynchronisé en base via
falkye.db.seed_client_cible_synonymes_from_registry, enrichi par le Niveau 2
— falkye/assistance_client_cible_ia.py — sans jamais changer ce module).

Le catalogue inclut la sentinelle `aucune_restriction`
(falkye/models/client_cible.py::ID_AUCUNE_RESTRICTION) comme un membre
NORMAL du dictionnaire de synonymes — un texte contenant "tous types
d'entreprises" matche cette entrée exactement comme n'importe quelle autre
catégorie matcherait la sienne. Pas de traitement spécial ici : la
distinction "réponse positive vs correspondance non trouvée" n'a de sens
qu'au Niveau 2 (falkye/assistance_client_cible_ia.py), qui doit décider quoi
faire d'une liste VRAIMENT vide — ce module se contente de rapporter ce qu'il
trouve, comme pour la sphère."""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from falkye.models.client_cible import ClientCible
from falkye.models.client_cible_synonyme import ClientCibleSynonyme
from falkye.models.company import Company
from falkye.texte_matching import motif_present


@dataclass(frozen=True)
class SuggestionClientCible:
    """Miroir de falkye/assistance_sphere.py::SuggestionSphere."""

    client_cible_id: str
    client_cible_nom: str
    score: int  # nombre de synonymes DISTINCTS trouvés
    mots_cles_matches: list[str] = field(default_factory=list)
    niveau: int = 1


def suggerer_clients_cibles_niveau1(
    db_session: Session, texte_description: str, limite: int = 3
) -> list[SuggestionClientCible]:
    """Catégories candidates pour `texte_description`, triées par score
    décroissant. Liste VIDE = échec du Niveau 1 (aucune correspondance, PAS
    MÊME "aucune_restriction") — le signal utilisé par
    falkye/assistance_client_cible_ia.py pour décider de déclencher le
    Niveau 2."""
    if not texte_description or not texte_description.strip():
        return []

    texte_lower = texte_description.lower()

    synonymes = (
        db_session.query(ClientCibleSynonyme, ClientCible)
        .join(ClientCible, ClientCible.id == ClientCibleSynonyme.client_cible_id)
        .all()
    )

    par_categorie: dict[str, dict] = {}
    for synonyme, client_cible in synonymes:
        motif = synonyme.texte.lower().strip()
        if not motif_present(texte_lower, motif):
            continue
        entree = par_categorie.setdefault(
            client_cible.id, {"nom": client_cible.nom, "mots_cles": set()}
        )
        entree["mots_cles"].add(synonyme.texte)

    suggestions = [
        SuggestionClientCible(
            client_cible_id=cle,
            client_cible_nom=donnees["nom"],
            score=len(donnees["mots_cles"]),
            mots_cles_matches=sorted(donnees["mots_cles"]),
        )
        for cle, donnees in par_categorie.items()
    ]
    suggestions.sort(key=lambda s: (-s.score, s.client_cible_nom))
    return suggestions[:limite]


def suggerer_clients_cibles_niveau1_pour_company(
    db_session: Session, company: Company, limite: int = 3
) -> list[SuggestionClientCible]:
    """Classification "qui" d'une entreprise DÉTECTÉE (falkye/engine.py, jamais
    dépendant d'une seule source — vérifié explicitement, 2026-09-03, contre les
    champs réellement disponibles de chaque source active).

    `company.secteur_activite_libelle` EST DÉJÀ la fusion cross-source pour les
    deux sources qui peuvent légitimement le renseigner :
      - REQ (`falkye/resolution.py::_enrich_from_req`, secteur_libelle officiel) ;
      - `licences_toronto`/`licences_vancouver` (`raw.secteur_activite=brute.
        type_entreprise`, propagé par `resolve_company` — même champ, même
        rôle que le secteur REQ pour une entreprise hors Québec).
    Aucun changement de mécanisme nécessaire ici pour ces deux-là : le simple
    fait d'appeler ce matcher contre `company.secteur_activite_libelle` couvre
    déjà les deux.

    Les autres champs disponibles à travers les signaux de cette entreprise
    (`donneur_ordre`/`ministere` de SEAO/contrats fédéraux/Nouvelle-Écosse/
    subventions, `titre_poste`/`profession` du recrutement, `description_
    tender`) sont DÉLIBÉRÉMENT exclus, pas oubliés : ces champs décrivent le
    DONNEUR D'ORDRE, le POSTE affiché, ou le CONTRAT — jamais la clientèle
    propre de l'entreprise détectée elle-même. Les inclure classerait à tort,
    par exemple, une firme d'ingénierie privée comme "organismes publics et
    institutionnels" simplement parce qu'elle a décroché un contrat d'un
    ministère — le donneur d'ordre n'est pas le client-type de l'entreprise,
    c'est SON client à elle pour CE contrat précis, une notion différente.

    Sans signal classifiable (secteur vide ou sans correspondance), liste
    vide — jamais une catégorie forcée, jamais d'escalade Niveau 2 pour une
    entreprise détectée (coût IA par entreprise scannée jamais introduit sans
    demande explicite — voir docs/ARCHITECTURE.md)."""
    return suggerer_clients_cibles_niveau1(db_session, company.secteur_activite_libelle or "", limite=limite)
