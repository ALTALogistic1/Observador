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
    score_des_noms_detectes,
    trouver_meilleur_candidat_fusion,
)
from falkye.cout_lectures import CHEMIN_EXACT, compter, compter_abouti
from falkye.models.company import Company, StatutLegal, StatutResolution
from falkye.models.diagnostic_journal import DiagnosticJournal, TypeDiagnostic
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

#: ⛔ **Au-delà de ce nombre de prétendants, personne n'obtient le NEQ.**
#:
#: *Le fait qui a écrit ce refus* (2026-09-17, relevé par Alexandre) : **le NEQ
#: 8879690699 attirait 26 dossiers** — CISSS de la Montérégie-Centre, CISSS
#: Gaspésie, CIUSSS de l'Outaouais, CHUM, Centre universitaire de santé McGill,
#: Institut de Cardiologie… **26 organisations RÉELLEMENT DISTINCTES, scores de
#: 95 à 100.** *Le nombre de prétendants est lui-même une preuve CONTRE
#: l'appariement* : deux dossiers qui convergent, c'est un doublon plausible;
#: vingt-six, c'est un nom qui désigne une FAMILLE d'entités.
#:
#: ⚠️ **Il vivait dans `outils/pose_du_neq.py` jusqu'au 2026-09-23**, et rien
#: dans `falkye/` ne comptait les prétendants : la garde ne protégeait donc que
#: les passes par LOT, jamais la production. *Il vit ici parce que la règle vit
#: ici*, et `pose_du_neq` l'emprunte désormais plutôt que de le redéfinir.
PRETENDANTS_MAX_POUR_TRANCHER = 2

#: Le statut que porte au journal un prétendant REFUSÉ.
#:
#: ⚠️ **Délibérément pas `"a_examiner"`.** *`falkye diagnostic confirmer-fusion`
#: n'agit que sur `a_examiner`* — une entrée écrite ici ne peut donc pas être
#: « confirmée » d'un coup de CLI en fusionnant les deux dossiers que la garde
#: vient de séparer. **Défaire un refus est une décision d'Alexandre, pas une
#: commande qui existe déjà.**
STATUT_PRETENDANT_REFUSE = "pretendant_refuse"


def requete_nom_exact(nom_norm: str):
    """La requête, séparée de son exécution — pour que l'outil qui VÉRIFIE son plan
    vérifie la vraie. Un plan mesuré sur une requête réécrite à côté ne prouve rien
    de celle que le moteur envoie (même règle que pour les outils qui agissent sur
    les données : emprunter la fonction du moteur, jamais son équivalent recopié)."""
    return select(Company).where(
        Company.neq.is_(None), Company.nom_detecte_normalise == nom_norm
    )


def _find_unresolved_company(db_session: Session, nom_detecte: str) -> Company | None:
    """Recherche indexée (Company.nom_detecte_normalise), pas un balayage Python de
    toutes les entreprises non résolues — voir le commentaire sur cette colonne dans
    falkye/models/company.py (sinon quadratique sur de gros volumes, ex. SEAO)."""
    nom_norm = normaliser(nom_detecte)
    compter(CHEMIN_EXACT)
    trouve = db_session.execute(requete_nom_exact(nom_norm)).scalar_one_or_none()
    if trouve is not None:
        # Le chemin exact aboutit quand il rend UNE ligne — il n'a pas de seuil
        # à franchir, la correspondance est l'aboutissement. Le dire ici plutôt
        # que de le supposer ailleurs : les trois chemins doivent être comptés
        # à la même définition, sinon leurs rendements ne se comparent pas.
        compter_abouti(CHEMIN_EXACT)
    return trouve


def neq_retenu(
    matches: list, seuil: float | None = None, ecart_min: float | None = None
) -> str | None:
    """Le NEQ qu'on retient parmi des candidats, ou None si c'est ambigu.

    ⚠️ `seuil` et `ecart_min` valent `None` en production, et la règle est alors
    strictement celle des constantes du module. **Ils existent pour les outils
    qui SIMULENT une autre échelle, et pour rien d'autre** : un appelant du
    pipeline qui les renseignerait changerait la règle sans passer par Alexandre.
    *Les deux échelles se changent avec lui, jamais dans une mesure.*

    **Séparée de son appel à dessein.** La règle — assez sûr ET assez détaché du
    second — est ce qui décide qu'une entreprise est identifiée ou pas. Un outil
    qui la rejouerait en la recopiant mesurerait sa propre copie : même raison
    que `requete_nom_exact` ci-dessus, appliquée à une décision plutôt qu'à une
    requête. *(Extraite le 2026-09-11 pour `outils/apport_ville.py`.)*
    """
    if not matches:
        return None
    top = matches[0]
    second_score = matches[1].score if len(matches) > 1 else 0.0
    seuil = SEUIL_RESOLUTION_CONFIANTE if seuil is None else seuil
    ecart_min = SEUIL_AMBIGUITE_ECART_MIN if ecart_min is None else ecart_min
    assez_sur = top.score >= seuil
    assez_detache = top.score - second_score >= ecart_min or len(matches) == 1
    return top.entry.neq if (assez_sur and assez_detache) else None


def famille_de(matches: list, seuil: float | None = None, ecart_min: float | None = None) -> str:
    """La FAMILLE d'un appariement — la taxonomie des mesures, en un seul endroit.

    Quatre issues, et **elles n'appellent pas le même correctif** : `RETENU` (la
    règle tranche), `ambigu` (assez sûr, pas assez détaché du second),
    `trop faible` (le meilleur ne franchit pas le seuil), `aucun candidat` (la
    récupération n'a rien rendu).

    ⚠️ **Deux échelles, deux familles.** *Un dossier peut échouer parce que le
    score est bas OU parce que le second est trop proche* — confondre les deux
    fait attribuer au seuil une masse que l'écart retient. C'est exactement la
    confusion qu'`outils/chiffrage_corrections.py` a produite le 2026-09-17, en
    annonçant 79 dossiers récupérés là où 1 623 franchissaient le seuil simulé.
    """
    if neq_retenu(matches, seuil=seuil, ecart_min=ecart_min) is not None:
        return "RETENU"
    if not matches:
        return "aucun candidat"
    seuil = SEUIL_RESOLUTION_CONFIANTE if seuil is None else seuil
    return "trop faible" if matches[0].score < seuil else "ambigu"


#: L'ordre d'affichage des familles, pour que deux tableaux se lisent l'un sous
#: l'autre. *Une taxonomie qui change d'ordre selon l'outil se compare mal.*
FAMILLES = ("RETENU", "ambigu", "trop faible", "aucun candidat")


def detenteur_du_neq(db_session: Session, neq: str) -> Company | None:
    """Le dossier qui PORTE déjà ce NEQ, ou `None`.

    ⚠️ **`Company.neq` est UNIQUE** (`falkye/models/company.py`). Il y a donc au
    plus UN détenteur, et c'est ce fait qui donne sa forme à la garde ci-dessous
    : *deux dossiers ne peuvent pas porter le même NEQ, donc « au-delà de deux
    prétendants, PERSONNE ne l'obtient » ne se transpose pas tel quel dans la
    résolution.* Voir `garde_des_pretendants`.
    """
    return db_session.execute(select(Company).where(Company.neq == neq)).scalar_one_or_none()


def est_le_meme_dossier(company: Company, nom_detecte: str) -> bool:
    """Ce signal vient-il du dossier qu'il a trouvé, ou d'un AUTRE nom détecté ?

    **Le nom détecté NORMALISÉ est le discriminant**, le même que partout
    ailleurs (`_find_unresolved_company`, `falkye/dedup_entreprises.py`). *Une
    re-détection de la même entreprise sous la même graphie n'est pas un
    prétendant : c'est le dossier cumulatif qui fait son travail* — et la garde
    ne doit jamais la casser.
    """
    return company.nom_detecte_normalise == normaliser(nom_detecte)


def _pretendant_deja_journalise(db_session: Session, detenteur_id: int, refuse_id: int) -> bool:
    """Idempotence — **la même paire ne se journalise qu'une fois.**

    *Sans elle, un dossier refusé re-détecté cinquante fois écrirait cinquante
    entrées et le décompte des prétendants compterait des signaux au lieu de
    dossiers.* Même principe que `_paire_deja_journalisee`, mais sur la paire
    ORIENTÉE (détenteur → refusé) : le refus n'est pas symétrique.
    """
    return db_session.query(DiagnosticJournal.id).filter(
        DiagnosticJournal.type_diagnostic == TypeDiagnostic.CANDIDAT_FUSION_ENTREPRISE,
        DiagnosticJournal.statut == STATUT_PRETENDANT_REFUSE,
        DiagnosticJournal.company_id_principal == detenteur_id,
        DiagnosticJournal.company_id_candidat == refuse_id,
    ).first() is not None


def compter_pretendants(db_session: Session, detenteur_id: int) -> int:
    """Combien de dossiers ont visé le NEQ de ce détenteur — **lui compris.**

    ⚠️ **C'est tout ce que la résolution PEUT compter.** *La passe par lot voit
    ses prétendants ensemble et peut les dénombrer avant d'écrire; la résolution
    les voit un par un, étalés dans le temps.* **Le seul nombre qu'elle puisse
    produire est celui des refus déjà consignés** — d'où la journalisation
    ci-dessous, qui n'est pas une trace de confort mais l'organe de comptage.
    """
    refuses = db_session.query(DiagnosticJournal.id).filter(
        DiagnosticJournal.type_diagnostic == TypeDiagnostic.CANDIDAT_FUSION_ENTREPRISE,
        DiagnosticJournal.statut == STATUT_PRETENDANT_REFUSE,
        DiagnosticJournal.company_id_principal == detenteur_id,
    ).count()
    return refuses + 1  # le détenteur est le premier prétendant


def journaliser_pretendant_refuse(
    db_session: Session, detenteur: Company, refuse: Company, score: float, rang: int
) -> DiagnosticJournal | None:
    """Consigne un refus — `None` si la paire était déjà consignée.

    *Le perdant n'est pas perdu, il est journalisé* — la phrase est celle de
    `outils/pose_du_neq.py`, et elle vaut ici mot pour mot : **c'est la
    conservation qui rend le refus bon marché.**
    """
    if _pretendant_deja_journalise(db_session, detenteur.id, refuse.id):
        return None
    au_dela = (
        f" — AU-DELÀ DE {PRETENDANTS_MAX_POUR_TRANCHER}, le nombre de prétendants "
        "est lui-même une preuve contre l'appariement"
        if rang > PRETENDANTS_MAX_POUR_TRANCHER
        else ""
    )
    entree = DiagnosticJournal(
        type_diagnostic=TypeDiagnostic.CANDIDAT_FUSION_ENTREPRISE,
        profile_id=None,
        texte_description=(
            f"Prétendant refusé sur le NEQ {detenteur.neq} "
            f"(score des noms détectés {score:.1f}, {rang}e prétendant{au_dela}) : "
            f"#{detenteur.id} « {detenteur.nom_detecte} » le détient; "
            f"#{refuse.id} « {refuse.nom_detecte} » reste un dossier SÉPARÉ, sans NEQ"
        ),
        statut=STATUT_PRETENDANT_REFUSE,
        company_id_principal=detenteur.id,
        company_id_candidat=refuse.id,
        score_similarite=score,
    )
    db_session.add(entree)
    db_session.flush()
    return entree


def garde_des_pretendants(db_session: Session, neq: str, raw: RawSignal) -> Company | None:
    """Le détenteur du NEQ quand ce signal doit lui être REFUSÉ, `None` sinon.

    ## ⛔ Ce que la garde empêche

    `resolve_company` cherchait un `Company` **par NEQ** avant d'en créer un :
    plusieurs noms détectés résolus vers le même NEQ étaient donc rattachés au
    MÊME dossier — **fusionnés de fait**, silencieusement, sans qu'aucune ligne
    ne le dise. *⚠️ Décision du 16 septembre : conservation toujours, aucune
    fusion.* **Six dossiers réunis sur un seul NEQ sont une fusion de fait**
    (Alexandre, 2026-09-23), et c'est le seul point de ce chantier qui pouvait
    abîmer la base.

    ## ⚠️ La forme du refus CHANGE en descendant du lot vers la résolution

    | | la passe par lot (17 sept.) | la résolution (ici) |
    |---|---|---|
    | ce qu'elle voit | tous les prétendants ensemble | UN dossier à la fois |
    | qui détient le NEQ | personne encore | quelqu'un, déjà |
    | le refus | **personne ne l'obtient** | **le nouveau venu ne l'obtient pas** |

    *La passe peut refuser à tout le monde parce qu'elle décide AVANT que
    quiconque ait le NEQ.* **Ici le détenteur l'a déjà, et le lui retirer serait
    une écriture qui EFFACE une identité** — pas une garde. La garde ne fait donc
    que ce qu'une garde peut faire : **elle ne peut que RÉDUIRE les écritures,
    jamais en produire une.**

    ⚠️ **Ce qui n'est donc PAS descendu, et qui reste à trancher** : le seuil
    lui-même. Au-delà de `PRETENDANTS_MAX_POUR_TRANCHER`, la passe par lot retire
    le NEQ à tout le monde; ici le premier arrivé le garde. *Le rang est écrit au
    journal à chaque refus pour que ces NEQ-là soient visibles* — mais **révoquer
    le NEQ d'un détenteur est une décision d'Alexandre, pas un effet de bord de
    la garde.**

    ## ⚠️ La frontière : le NEQ DONNÉ par la source ne passe pas par ici

    La garde du 17 septembre est née d'un **appariement par le NOM** — *« le
    nombre de prétendants est une preuve contre l'appariement »*. Un NEQ qu'une
    source AFFIRME (`raw.neq`) n'est pas un appariement : deux graphies sous le
    même NEQ affirmé désignent la même personne morale, et les séparer perdrait
    l'identité que la source donnait. **Seul le NEQ INFÉRÉ par le scoreur est
    gardé.** *Cette frontière est un choix, pas une évidence — elle est posée ici
    pour être vue, pas pour être supposée.*
    """
    if raw.neq is not None:
        return None  # NEQ affirmé par la source — voir la frontière ci-dessus
    detenteur = detenteur_du_neq(db_session, neq)
    if detenteur is None or est_le_meme_dossier(detenteur, raw.nom_entreprise):
        return None
    return detenteur


def _dossier_sans_neq(db_session: Session, raw: RawSignal) -> Company:
    """Le dossier d'un signal qu'aucun NEQ ne porte — trouvé, rapproché, ou créé.

    **Extrait de `resolve_company` le 2026-09-23** pour que la garde des
    prétendants et l'échec de résolution aboutissent au MÊME geste. *Un refus qui
    recopierait ce chemin en divergerait, et un dossier refusé cesserait de
    profiter du rapprochement flou qui protège les autres.*
    """
    company = _find_unresolved_company(db_session, raw.nom_entreprise)
    if company is not None:
        return company
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
        return meilleur.company  # ancrage fort — jamais une nouvelle fiche créée
    company = Company(neq=None, nom_detecte=raw.nom_entreprise, nom_detecte_normalise=nom_norm)
    db_session.add(company)
    db_session.flush()  # company.id requis avant de journaliser un candidat
    if meilleur is not None:  # 90 <= score < 95 — jamais fusionné seul
        journaliser_candidat_fusion(
            db_session, meilleur.company, company, meilleur.score, statut="a_examiner"
        )
    return company


def resolve_company(db_session: Session, raw: RawSignal) -> Company:
    """Trouve ou crée le Company (dossier cumulatif) correspondant à ce signal brut,
    et tente sa résolution NEQ si elle n'est pas déjà acquise."""

    neq = raw.neq
    matches: list[req_source.REQMatch] = []

    if neq is None:
        matches = req_source.resolve_neq_by_name(db_session, raw.nom_entreprise, ville=raw.ville)
        if matches:
            neq = neq_retenu(matches)
            if neq is None:
                top = matches[0]
                logger.info(
                    "Résolution NEQ ambiguë pour %r : top=%.1f, 2e=%.1f",
                    raw.nom_entreprise,
                    top.score,
                    matches[1].score if len(matches) > 1 else 0.0,
                )

    detenteur = garde_des_pretendants(db_session, neq, raw) if neq is not None else None

    if detenteur is not None:
        # ⛔ LA GARDE A REFUSÉ — le NEQ est déjà porté par un AUTRE nom détecté.
        # Le prétendant reste un dossier SÉPARÉ, sans NEQ, et le refus est
        # consigné. **Rien n'est retiré au détenteur**, rien n'est fusionné :
        # voir `garde_des_pretendants` pour la forme du refus et sa frontière.
        company = _dossier_sans_neq(db_session, raw)
        rang = compter_pretendants(db_session, detenteur.id) + 1
        score = score_des_noms_detectes(company.nom_detecte_normalise, raw.ville, detenteur)
        journaliser_pretendant_refuse(db_session, detenteur, company, score, rang)
        logger.info(
            "Prétendant refusé sur le NEQ %s : #%s « %s » le détient, #%s « %s » "
            "reste séparé (%se prétendant, score des noms %.1f)",
            neq, detenteur.id, detenteur.nom_detecte, company.id, company.nom_detecte, rang, score,
        )
        # AMBIGU plutôt qu'un cinquième statut : *un NEQ a bien été trouvé, mais
        # l'identité reste indécise* — et inventer un statut ici toucherait tous
        # ses lecteurs alors que l'élargissement du statut (registre D53) est
        # encore en attente d'Alexandre.
        company.statut_resolution = StatutResolution.AMBIGU
    elif neq is not None:
        company = db_session.execute(select(Company).where(Company.neq == neq)).scalar_one_or_none()
        if company is None:
            company = Company(
                neq=neq, nom_detecte=raw.nom_entreprise, nom_detecte_normalise=normaliser(raw.nom_entreprise)
            )
            db_session.add(company)
        company.statut_resolution = StatutResolution.RESOLU
        _enrich_from_req(db_session, company, neq)
    else:
        company = _dossier_sans_neq(db_session, raw)
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
