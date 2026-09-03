"""Détection et fusion de doublons `Company` sans NEQ — spec section 8bis,
point 4 (2026-09-03).

CONTEXTE : `falkye/resolution.py::_find_unresolved_company` ne faisait
correspondre une entreprise SANS NEQ (ni résolue au REQ, ni détectée via une
source hors Québec dotée d'un identifiant équivalent) que par nom normalisé
EXACT — jamais flou, contrairement à la résolution NEQ elle-même
(`falkye.sources.req.resolve_neq_by_name`, déjà floue) et au rapprochement
inter-provincial (`falkye/expansion_interprovinciale.py`, floue aussi). Deux
noms différents pour la MÊME entreprise (ex. "Les Services EXP inc." vs
"Services EXP inc. (Les)" vs "Les Services EXP inc. — compte principal")
créaient donc systématiquement DEUX dossiers Company distincts — vérifié
contre la base réelle avant de coder (voir docs/STATUT_RESEAU.md) : 76
paires à similarité >=90% déjà présentes, pas un risque théorique.

DEUX SEUILS, jamais un seul — décision explicite d'Alexandre (2026-09-03) :
"jamais de fusion automatique silencieuse... une fusion incorrecte est trop
coûteuse à défaire pour la laisser à un seuil unique."
  - score >= SEUIL_FUSION_AUTO (95) : fusion APPLIQUÉE immédiatement,
    journalisée dans DiagnosticJournal à titre PUREMENT INFORMATIONNEL
    (`statut="fusionne_auto"`) — rien à confirmer, juste une trace.
  - SEUIL_FUSION_CANDIDAT (90) <= score < 95 : JAMAIS fusionné seul —
    journalisé (`statut="a_examiner"`), à trancher manuellement via
    `falkye diagnostic confirmer-fusion` / `diagnostic rejeter-fusion`.
  - score < 90 : ignoré, pas même journalisé (bruit, voir le seuil choisi
    contre la base réelle — c'est le plancher qui a produit les 76 paires
    ci-dessus, déjà à trier).

Même scorer unique du projet (`rapidfuzz.fuzz.WRatio`, cohérent avec
`falkye/resolution.py`/`falkye/sources/req.py`/`falkye/
expansion_interprovinciale.py`), avec le même bonus de ville que la
résolution REQ (+5, `Company.ville` normalisée insensible à la casse).
Recherche BORNÉE par préfixe (GLOB sur l'index `nom_detecte_normalise`,
même technique que `falkye.sources.req.resolve_neq_by_name` — jamais un
balayage complet, qui deviendrait quadratique sur un gros volume).

JAMAIS contre une entreprise déjà résolue au REQ (`neq IS NOT NULL`) — un
faux positif fusionnerait un dossier à forte valeur (identité confirmée)
avec un dossier incertain, perte disproportionnée pour un gain marginal.

`fusionner()` réassigne Signal/Notification du dossier candidat vers le
dossier principal puis SUPPRIME le candidat — jamais l'inverse : le
PRINCIPAL est toujours le dossier le plus ANCIEN (`first_detected_at`),
cohérent avec le principe du dossier cumulatif (spec section 5) : la
première détection reste la référence, jamais supplantée par une
ré-détection plus récente sous un nom légèrement différent."""
from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session

from falkye.models.company import Company
from falkye.models.diagnostic_journal import DiagnosticJournal, TypeDiagnostic
from falkye.models.notification import Notification
from falkye.models.signal import Signal

# GARDE-FOU trouvé en testant CONTRE LA BASE RÉELLE (2026-09-03), avant
# d'appliquer quoi que ce soit — deux compagnies à numéro québécoises DIFFÉRENTES
# (ex. "9519-3801 Québec inc." et "9519-3850 Québec inc.") produisaient un score
# WRatio de 95.0, DANS la fourchette de fusion AUTOMATIQUE, alors que ce sont
# deux entités légalement DISTINCTES — le matricule numérique EST l'identifiant
# réel, la similarité floue de chaînes de caractères est structurellement
# trompeuse ici (la partie commune "Québec inc." domine le score, masquant que
# les chiffres eux-mêmes ne se ressemblent pas du tout au sens du registre).
# Repéré avant toute conséquence réelle (fusion annulée, base restaurée depuis
# la sauvegarde) — voir docs/STATUT_RESEAU.md pour le récit complet. Deux noms
# de cette forme ne sont JAMAIS comparés par similarité floue : seule une
# correspondance EXACTE du matricule compte (et une correspondance exacte est de
# toute façon déjà gérée par falkye/resolution.py, jamais par ce module).
_MOTIF_NUMERO_ENTREPRISE = re.compile(r"^(\d{4}\s\d{4})\b")


def _numero_entreprise(nom_normalise: str) -> str | None:
    """Le matricule d'une compagnie à numéro québécoise (forme normalisée de
    "9519-3801 Québec inc." -> "9519 3801 quebec inc"), ou None si le nom n'a
    pas cette forme."""
    m = _MOTIF_NUMERO_ENTREPRISE.match(nom_normalise)
    return m.group(1) if m else None


SEUIL_FUSION_AUTO = 95.0
SEUIL_FUSION_CANDIDAT = 90.0
BONUS_VILLE = 5.0

# Nombre max de candidats ramenés par la recherche bornée par préfixe — même
# ordre de grandeur que falkye.sources.req.resolve_neq_by_name (2000), réduit
# ici puisque le pool de comparaison (Company sans NEQ) est structurellement
# plus petit que le miroir REQ complet.
LIMITE_CANDIDATS = 500


@dataclass
class MeilleurCandidat:
    company: Company
    score: float


def _score(nom_normalise: str, ville: str | None, autre: Company) -> float:
    numero_a = _numero_entreprise(nom_normalise)
    numero_b = _numero_entreprise(autre.nom_detecte_normalise)
    if numero_a is not None and numero_b is not None and numero_a != numero_b:
        return 0.0  # deux compagnies à numéro DIFFÉRENTES — jamais un candidat (voir _numero_entreprise)

    score = fuzz.WRatio(nom_normalise, autre.nom_detecte_normalise)
    if ville and autre.ville and ville.strip().lower() == autre.ville.strip().lower():
        score = min(100.0, score + BONUS_VILLE)
    return score


def trouver_meilleur_candidat_fusion(
    db_session: Session,
    nom_normalise: str,
    ville: str | None,
    *,
    exclure_id: int | None = None,
) -> MeilleurCandidat | None:
    """Meilleur candidat de fusion pour `nom_normalise`, parmi les Company
    SANS NEQ existants — None si aucun n'atteint SEUIL_FUSION_CANDIDAT.
    `exclure_id` : à passer quand `nom_normalise` provient déjà d'un Company
    existant (recherche depuis la passe par lot), pour ne jamais se comparer
    à soi-même."""
    if not nom_normalise:
        return None

    prefix = nom_normalise.split(" ")[0]
    candidats = (
        db_session.execute(
            select(Company)
            .where(Company.neq.is_(None), Company.nom_detecte_normalise.op("GLOB")(f"{prefix}*"))
            .limit(LIMITE_CANDIDATS)
        )
        .scalars()
        .all()
    )
    if not candidats:
        candidats = (
            db_session.execute(
                select(Company)
                .where(Company.neq.is_(None), Company.nom_detecte_normalise.contains(nom_normalise[:6]))
                .limit(LIMITE_CANDIDATS)
            )
            .scalars()
            .all()
        )

    meilleur: MeilleurCandidat | None = None
    for autre in candidats:
        if exclure_id is not None and autre.id == exclure_id:
            continue
        if autre.nom_detecte_normalise == nom_normalise:
            continue  # correspondance EXACTE — gérée séparément par resolution.py, pas ici
        score = _score(nom_normalise, ville, autre)
        if meilleur is None or score > meilleur.score:
            meilleur = MeilleurCandidat(company=autre, score=score)

    if meilleur is None or meilleur.score < SEUIL_FUSION_CANDIDAT:
        return None
    return meilleur


def fusionner(db_session: Session, principal: Company, candidat: Company) -> None:
    """Réassigne tout le contenu de `candidat` vers `principal`, puis
    supprime `candidat`. `principal` doit déjà être le dossier retenu par
    l'appelant (voir docstring du module — le plus ancien) ; cette fonction
    ne fait aucun choix, elle exécute."""
    db_session.query(Signal).filter(Signal.company_id == candidat.id).update({"company_id": principal.id})
    db_session.query(Notification).filter(Notification.company_id == candidat.id).update(
        {"company_id": principal.id}
    )
    # Une référence de journal antérieure à CE candidat (ex. un fusionne_auto
    # d'une passe précédente qui l'aurait déjà nommé "candidat" pour une AUTRE
    # paire — chaîne rare mais possible) : neutralisée plutôt que laissée
    # pointer vers une ligne qui va disparaître. company_id_principal n'est
    # jamais touché ici — un principal n'est jamais fusionné comme candidat
    # d'une autre paire au sein de la même passe (voir detecter_doublons).
    db_session.query(DiagnosticJournal).filter(DiagnosticJournal.company_id_candidat == candidat.id).update(
        {"company_id_candidat": None}
    )
    db_session.delete(candidat)
    db_session.flush()


def journaliser_candidat_fusion(
    db_session: Session, principal: Company, candidat: Company, score: float, *, statut: str
) -> DiagnosticJournal:
    """ATTENTION D'ORDRE (piège trouvé en testant) : `fusionner()` neutralise
    toute référence `company_id_candidat` pointant vers la ligne qu'elle
    supprime, y COMPRIS une entrée créée par CET appel-ci si elle a lieu
    AVANT `fusionner()` pour la même paire. Pour le cas auto (score >=95),
    appeler `fusionner()` D'ABORD, puis journaliser via
    `journaliser_fusion_auto` (id/nom déjà capturés, pas un objet ORM
    potentiellement périmé après suppression) — jamais cette fonction-ci pour
    ce cas précis. Réservée au cas candidat (90-95, jamais fusionné), où
    `candidat` existe encore et le restera tant que personne ne confirme."""
    entree = DiagnosticJournal(
        type_diagnostic=TypeDiagnostic.CANDIDAT_FUSION_ENTREPRISE,
        profile_id=None,  # jamais rattaché à un profil précis — touche le dossier cumulatif entier
        texte_description=(
            f"Candidat de fusion (score {score:.1f}) : "
            f"#{principal.id} « {principal.nom_detecte} » <-> #{candidat.id} « {candidat.nom_detecte} »"
        ),
        statut=statut,
        company_id_principal=principal.id,
        company_id_candidat=candidat.id,
        score_similarite=score,
    )
    db_session.add(entree)
    db_session.flush()
    return entree


def journaliser_fusion_auto(
    db_session: Session, principal: Company, candidat_id: int, candidat_nom: str, score: float
) -> DiagnosticJournal:
    """Trace PUREMENT INFORMATIONNELLE d'une fusion déjà appliquée
    (score >=95) — appelée APRÈS `fusionner()`, jamais avant (voir
    `journaliser_candidat_fusion`). `company_id_candidat` reste NULL : la
    ligne n'existe plus, rien de valide à référencer — `candidat_id`/
    `candidat_nom` (capturés par l'appelant AVANT la suppression) suffisent
    à documenter QUI a été fusionné, dans le texte."""
    entree = DiagnosticJournal(
        type_diagnostic=TypeDiagnostic.CANDIDAT_FUSION_ENTREPRISE,
        profile_id=None,
        texte_description=(
            f"Fusion automatique (score {score:.1f}) : "
            f"#{principal.id} « {principal.nom_detecte} » <-> #{candidat_id} « {candidat_nom} »"
        ),
        statut="fusionne_auto",
        company_id_principal=principal.id,
        company_id_candidat=None,
        score_similarite=score,
    )
    db_session.add(entree)
    db_session.flush()
    return entree


def _paire_deja_journalisee(db_session: Session, id_a: int, id_b: int) -> bool:
    """Idempotence — même principe que falkye/expansion_interprovinciale.py :
    une paire déjà journalisée (peu importe le statut, y compris "ecarte")
    n'est jamais rejournalisée par une passe ultérieure."""
    existe = (
        db_session.query(DiagnosticJournal.id)
        .filter(
            DiagnosticJournal.type_diagnostic == TypeDiagnostic.CANDIDAT_FUSION_ENTREPRISE,
            DiagnosticJournal.company_id_principal.in_([id_a, id_b]),
            DiagnosticJournal.company_id_candidat.in_([id_a, id_b]),
        )
        .first()
    )
    return existe is not None


@dataclass
class RapportDedup:
    nb_fusions_auto: int = 0
    nb_candidats_journalises: int = 0


def detecter_doublons(db_session: Session) -> RapportDedup:
    """Passe par lot — rattrapage manuel (`falkye scan detecter-doublons`,
    réservé au mode opérateur : action potentiellement DESTRUCTIVE — voir
    falkye/cli.py). Balaie toutes les Company sans NEQ, du plus ancien
    dossier au plus récent (le plus ancien devient naturellement le
    "principal" de toute paire qu'il produit). Idempotent : une paire déjà
    fusionnée ne peut plus être retrouvée (la ligne candidate a disparu) ;
    une paire déjà journalisée n'est jamais rejournalisée."""
    rapport = RapportDedup()
    ids = (
        db_session.execute(
            select(Company.id).where(Company.neq.is_(None)).order_by(Company.first_detected_at)
        )
        .scalars()
        .all()
    )

    for company_id in ids:
        company = db_session.get(Company, company_id)
        if company is None:
            continue  # fusionné comme candidat d'une paire précédente, plus tôt dans CETTE passe

        meilleur = trouver_meilleur_candidat_fusion(
            db_session, company.nom_detecte_normalise, company.ville, exclure_id=company.id
        )
        if meilleur is None:
            continue

        autre = meilleur.company
        # `company` est déjà le plus ancien des deux par construction (ids triés par
        # first_detected_at, et `autre` n'a pas encore été visité par cette boucle —
        # sauf s'il a un first_detected_at ANTÉRIEUR mais un nom qui commence par un
        # préfixe différent, jamais rencontré avant lui dans `ids` — cas rare, corrigé
        # explicitement ci-dessous plutôt que supposé).
        principal, candidat = (
            (company, autre) if company.first_detected_at <= autre.first_detected_at else (autre, company)
        )

        if meilleur.score >= SEUIL_FUSION_AUTO:
            candidat_id, candidat_nom = candidat.id, candidat.nom_detecte
            fusionner(db_session, principal, candidat)  # AVANT de journaliser — voir docstrings
            journaliser_fusion_auto(db_session, principal, candidat_id, candidat_nom, meilleur.score)
            rapport.nb_fusions_auto += 1
        elif not _paire_deja_journalisee(db_session, principal.id, candidat.id):
            journaliser_candidat_fusion(db_session, principal, candidat, meilleur.score, statut="a_examiner")
            rapport.nb_candidats_journalises += 1

    return rapport
