"""Moteur de diff générique et quarantaine (Chantier 1, spec section 8bis —
audit du 2026-09-03, faille E).

CONTEXTE — pourquoi ce module existe. Une source de type `instantane`
(`SourceDef.type_ingestion`, registry/sources.yaml) ne fournit AUCUNE date
d'événement fiable par ligne — RACJ et les établissements alimentaires de
Montréal (pas encore construits, ce module doit les accueillir sans
modification) en sont l'exemple ; REQ, Corporations Canada et les licences
municipales (Toronto/Vancouver) en sont des exemples DÉJÀ actifs, chacun avec
son propre mécanisme de diff BESPOKE et PARTIEL (miroir local + "clé jamais
vue = signal", jamais de détection de disparition, jamais de suivi de
modification) — ce module les généralise plutôt que de les remplacer (Phase 0
du chantier). Le remplacement effectif de ces 4 connecteurs par ce moteur
reste HORS de ce chantier (touche à la résolution NEQ/identité pour REQ —
territoire du chantier 3, signalé plutôt que franchi) ; voir docs/STATUT_
RESEAU.md pour la validation macro contre Toronto/Vancouver.

GARDE-FOUS NON NÉGOCIABLES DU MANDAT :
  - Le premier run d'une source (aucun EtatSchemaSource enregistré) est un
    RUN DE RÉFÉRENCE : il amorce l'état, n'émet AUCUN candidat, et ne peut
    JAMAIS déclencher la quarantaine (100% d'apparitions y est normal).
  - Un changement de schéma sur une colonne PERTINENTE (retirée ou dont le
    type déclaré change) déclenche la quarantaine IMMÉDIATEMENT, quel que
    soit le volume du diff. Une colonne AJOUTÉE ne déclenche jamais rien
    (avertissement seul) — les diffuseurs ajoutent des colonnes couramment.
  - La quarantaine exige DEUX seuils franchis ENSEMBLE (pourcentage ET
    absolu), avec des seuils DISTINCTS par type d'écart (apparitions,
    disparitions, modifications) — jamais un seuil unique.
  - Un run mis en quarantaine ne touche à AUCUN état : `EtatLigneSource`/
    `EtatSchemaSource` restent inchangés, `lignes` de ce run ne rejoignent
    JAMAIS le dossier cumulatif, même partiellement.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from falkye.models.diff_quarantaine import DiffQuarantaine, MotifQuarantaine, StatutQuarantaine
from falkye.models.etat_diff_source import EtatLigneSource, EtatSchemaSource

logger = logging.getLogger(__name__)

# Même convention que falkye/sources/ckan_client.py::CACHE_DIR — surchargeable
# par variable d'environnement pour les tests/déploiements.
ARCHIVE_DIR = Path(os.environ.get("FALKYE_DIFF_ARCHIVE_DIR", "./cache/diff_archive"))
GENERATIONS_CONSERVEES = 5  # "un petit nombre de générations suffit" (mandat)

# Insertion en LOT (SQLAlchemy Core, jamais un ORM par ligne) pour le run de
# référence et les apparitions — seul chemin qui touche potentiellement la
# POPULATION COMPLÈTE d'une source (ex. REQ réel : 2,7M lignes). Découverte
# réelle lors de la macro-vérification du chantier 1 : `db_session.add(...)`
# par ligne (ORM, unit-of-work) fait exploser la mémoire bien avant la fin de
# l'insertion à cette échelle (~9,6 Go observés, tué avant complétion) — un
# INSERT en lot (dicts bruts, jamais d'objet ORM par ligne, jamais tenu en
# mémoire par le identity map) reste stable quel que soit le volume. Les
# disparitions/modifications restent en ORM (update/delete par ligne) : leur
# volume est celui du DIFF, pas de la population, donc sans commune mesure.
TAILLE_LOT_INSERTION = 5000


def _inserer_lignes_en_lot(db_session: Session, source_id: str, lignes: list[LigneSnapshot]) -> None:
    lot: list[dict] = []
    for l in lignes:
        lot.append(
            {
                "source_id": source_id,
                "cle_naturelle": l.cle,
                "empreinte": calculer_empreinte(l.champs),
                "donnees_normalisees": l.champs,
            }
        )
        if len(lot) >= TAILLE_LOT_INSERTION:
            db_session.execute(insert(EtatLigneSource), lot)
            lot = []
    if lot:
        db_session.execute(insert(EtatLigneSource), lot)


@dataclass(frozen=True)
class LigneSnapshot:
    """Une ligne source normalisée, RÉDUITE aux champs pertinents
    (SourceDef.champs_pertinents) — jamais la ligne brute entière, pour que
    l'empreinte ne réagisse pas à un changement cosmétique hors de cette
    liste (espace, colonne inutilisée, réordonnancement)."""

    cle: str
    champs: dict = field(default_factory=dict)


@dataclass(frozen=True)
class SeuilType:
    pct: float
    abs: int


@dataclass(frozen=True)
class SeuilsQuarantaine:
    apparitions: SeuilType
    disparitions: SeuilType
    modifications: SeuilType


# Repli GLOBAL, conservateur — surchargé par SourceDef.seuils_quarantaine dès
# qu'une source a un vrai volume observé pour calibrer un seuil qui lui soit
# propre (voir docs/STATUT_RESEAU.md pour les valeurs retenues par source
# après validation macro, ex. licences_toronto). Disparitions volontairement
# PLUS BAS qu'apparitions/modifications — mandat : "une disparition massive
# est plus suspecte... signale généralement un extrait tronqué".
SEUILS_DEFAUT = SeuilsQuarantaine(
    apparitions=SeuilType(pct=50.0, abs=500),
    disparitions=SeuilType(pct=30.0, abs=300),
    modifications=SeuilType(pct=50.0, abs=500),
)


def seuils_depuis_registre(seuils_registre: dict | None) -> SeuilsQuarantaine:
    """Construit des SeuilsQuarantaine à partir de SourceDef.seuils_quarantaine
    (dict brut du YAML) — repli sur SEUILS_DEFAUT type par type, jamais tout ou
    rien (une source peut surcharger seulement "disparitions" par exemple)."""
    if not seuils_registre:
        return SEUILS_DEFAUT

    def _type(nom: str, defaut: SeuilType) -> SeuilType:
        brut = seuils_registre.get(nom)
        if not brut:
            return defaut
        return SeuilType(pct=float(brut.get("pct", defaut.pct)), abs=int(brut.get("abs", defaut.abs)))

    return SeuilsQuarantaine(
        apparitions=_type("apparitions", SEUILS_DEFAUT.apparitions),
        disparitions=_type("disparitions", SEUILS_DEFAUT.disparitions),
        modifications=_type("modifications", SEUILS_DEFAUT.modifications),
    )


@dataclass(frozen=True)
class Modification:
    cle: str
    champs_avant: dict
    champs_apres: dict
    champs_changes: list[str]


@dataclass(frozen=True)
class ResultatDiff:
    """Trois ensembles en sortie, JAMAIS fusionnés (mandat) — des CANDIDATS de
    signal, pas des notifications : le reste du pipeline (résolution
    d'identité, score, pertinence, routage) reste inchangé, hors de ce
    chantier."""

    apparitions: list[LigneSnapshot]
    disparitions: list[str]
    modifications: list[Modification]


@dataclass
class RapportExecution:
    source_id: str
    run_reference: bool = False
    quarantaine: bool = False
    motif_quarantaine: MotifQuarantaine | None = None
    quarantaine_id: int | None = None
    resultat: ResultatDiff | None = None
    nb_lignes_actuelles: int = 0
    nb_lignes_precedentes: int = 0
    avertissements: list[str] = field(default_factory=list)


def calculer_empreinte(champs: dict) -> str:
    """Empreinte stable des champs pertinents — sha256 sur une sérialisation
    JSON triée, insensible à l'ordre des clés du dict d'entrée."""
    brut = json.dumps(champs, sort_keys=True, default=str, ensure_ascii=True)
    return hashlib.sha256(brut.encode("utf-8")).hexdigest()


def _archiver_snapshot(source_id: str, lignes: list[LigneSnapshot]) -> str:
    """Conserve le fichier brut de CETTE exécution — pour pouvoir inspecter un
    diff suspect après coup (mandat). Rotation : ne garde que les
    GENERATIONS_CONSERVEES dernières par source."""
    dossier = ARCHIVE_DIR / source_id
    dossier.mkdir(parents=True, exist_ok=True)
    horodatage = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    chemin = dossier / f"{horodatage}.json"
    chemin.write_text(
        json.dumps([{"cle": l.cle, "champs": l.champs} for l in lignes], ensure_ascii=False), encoding="utf-8"
    )

    generations = sorted(dossier.glob("*.json"))
    for vieux in generations[:-GENERATIONS_CONSERVEES]:
        vieux.unlink(missing_ok=True)

    return str(chemin)


def _pct(count: int, total_precedent: int) -> float:
    if total_precedent == 0:
        return 100.0 if count > 0 else 0.0
    return 100.0 * count / total_precedent


def _seuil_franchi(count: int, total_precedent: int, seuil: SeuilType) -> bool:
    """Les DEUX seuils doivent être franchis ENSEMBLE (mandat) — le
    pourcentage seul mettrait en quarantaine les petites sources sur du bruit
    normal, l'absolu seul ne verrait rien venir sur les grosses."""
    return count >= seuil.abs and _pct(count, total_precedent) >= seuil.pct


SEUIL_ERREUR_LECTURE_DEFAUT = 0.05  # 5% de lignes illisibles — au-delà, quarantaine


def executer_diff(
    db_session: Session,
    source_id: str,
    lignes: list[LigneSnapshot],
    colonnes_vues: dict[str, str],
    champs_pertinents: set[str],
    seuils: SeuilsQuarantaine | None = None,
    taux_erreur_lecture: float = 0.0,
    seuil_erreur_lecture: float = SEUIL_ERREUR_LECTURE_DEFAUT,
) -> RapportExecution:
    """Point d'entrée unique du moteur — voir les docstrings de module et de
    dataclasses ci-dessus pour les garde-fous. `colonnes_vues` : TOUTES les
    colonnes brutes rencontrées dans cette exécution, mappées à un type
    déclaré par l'appelant (chaîne libre, "" si inconnu/non tracké — le suivi
    de type reste alors best-effort, jamais une erreur). `champs_pertinents` :
    sous-ensemble de `colonnes_vues` qui compte pour la détection de
    changement de schéma ET qui doit correspondre aux clés de `LigneSnapshot.
    champs` (SourceDef.champs_pertinents, registry/sources.yaml).

    `taux_erreur_lecture` : fraction (0-1) des lignes brutes que L'APPELANT
    n'a PAS réussi à parser (encodage, format, séparateur) — calculée par le
    connecteur, jamais ici (ce module ne lit aucun fichier). Au-delà de
    `seuil_erreur_lecture`, quarantaine immédiate (LECTURE_ECHOUEE), avant
    même la comparaison de schéma ou de contenu — l'échec de lecture rend
    `lignes` non fiable pour juger quoi que ce soit d'autre."""
    seuils = seuils or SEUILS_DEFAUT
    rapport = RapportExecution(source_id=source_id, nb_lignes_actuelles=len(lignes))

    if taux_erreur_lecture > seuil_erreur_lecture:
        chemin_archive = _archiver_snapshot(source_id, lignes)
        q = DiffQuarantaine(
            source_id=source_id,
            motif=MotifQuarantaine.LECTURE_ECHOUEE,
            detail={"taux_erreur_lecture": taux_erreur_lecture, "seuil": seuil_erreur_lecture},
            chemin_archive=chemin_archive,
        )
        db_session.add(q)
        db_session.flush()
        rapport.quarantaine = True
        rapport.motif_quarantaine = MotifQuarantaine.LECTURE_ECHOUEE
        rapport.quarantaine_id = q.id
        logger.warning(
            "Source %s en quarantaine (lecture_echouee) : taux d'erreur %.1f%% > seuil %.1f%%",
            source_id, taux_erreur_lecture * 100, seuil_erreur_lecture * 100,
        )
        return rapport

    etat_schema = db_session.get(EtatSchemaSource, source_id)
    run_reference = etat_schema is None
    rapport.run_reference = run_reference

    lignes_par_cle = {l.cle: l for l in lignes}
    if len(lignes_par_cle) != len(lignes):
        # Découverte réelle en macro-vérifiant contre les vraies données Toronto
        # (chantier 1) : ~0,5% de lignes brutes STRICTEMENT identiques (même
        # clé ET mêmes champs) pour la même clé naturelle, un défaut de qualité
        # RÉEL du jeu de données source, pas une erreur du connecteur. Jamais
        # une erreur bloquante ici — `lignes_par_cle` dédoublonne déjà (dernière
        # occurrence gagne, contenu identique en pratique) — mais consigné
        # explicitement : une DIVERGENCE de contenu entre deux lignes de même
        # clé serait, elle, un signe d'ambiguïté réelle sur la clé naturelle
        # déclarée, pas seulement un doublon inoffensif.
        rapport.avertissements.append(
            f"{len(lignes) - len(lignes_par_cle)} ligne(s) brute(s) avec une clé naturelle en double "
            f"(sur {len(lignes)} lignes) — dédoublonnées (dernière occurrence conservée)."
        )
    # Lecture en colonnes (Core), jamais des instances ORM complètes — même
    # motivation que TAILLE_LOT_INSERTION ci-dessus : cette lecture porte sur
    # la POPULATION COMPLÈTE de l'état précédent (ex. REQ réel : 2,7M lignes),
    # et n'est utilisée qu'en LECTURE seule ici (jamais mutée directement —
    # les mutations passent par _appliquer_diff, qui recharge ses propres
    # objets ORM ciblés uniquement sur les clés du diff, pas la population).
    etats_precedents = {
        row.cle_naturelle: row
        for row in db_session.execute(
            select(
                EtatLigneSource.cle_naturelle, EtatLigneSource.empreinte, EtatLigneSource.donnees_normalisees
            ).where(EtatLigneSource.source_id == source_id)
        ).all()
    }
    rapport.nb_lignes_precedentes = len(etats_precedents)

    # --- Détection de changement de schéma (jamais sur un run de référence —
    # rien à comparer) ---
    if not run_reference:
        colonnes_precedentes: dict = etat_schema.colonnes or {}
        retirees = set(colonnes_precedentes) - set(colonnes_vues)
        ajoutees = set(colonnes_vues) - set(colonnes_precedentes)
        retirees_pertinentes = retirees & champs_pertinents
        types_modifies = {
            c
            for c in (set(colonnes_vues) & set(colonnes_precedentes)) & champs_pertinents
            if colonnes_vues.get(c) and colonnes_precedentes.get(c) and colonnes_vues[c] != colonnes_precedentes[c]
        }
        if ajoutees:
            rapport.avertissements.append(f"Colonne(s) ajoutée(s), sans conséquence : {sorted(ajoutees)}")

        if retirees_pertinentes or types_modifies:
            motif = MotifQuarantaine.SCHEMA_COLONNE_RETIREE if retirees_pertinentes else MotifQuarantaine.SCHEMA_TYPE_MODIFIE
            chemin_archive = _archiver_snapshot(source_id, lignes)
            q = DiffQuarantaine(
                source_id=source_id,
                motif=motif,
                detail={
                    "colonnes_pertinentes_retirees": sorted(retirees_pertinentes),
                    "colonnes_type_modifie": sorted(types_modifies),
                    "colonnes_vues": colonnes_vues,
                    "colonnes_precedentes": colonnes_precedentes,
                },
                chemin_archive=chemin_archive,
            )
            db_session.add(q)
            db_session.flush()
            rapport.quarantaine = True
            rapport.motif_quarantaine = motif
            rapport.quarantaine_id = q.id
            logger.warning(
                "Source %s en quarantaine (%s) : colonnes retirées=%s, type modifié=%s",
                source_id, motif.value, sorted(retirees_pertinentes), sorted(types_modifies),
            )
            return rapport

    # --- Diff de contenu ---
    apparitions = [l for cle, l in lignes_par_cle.items() if cle not in etats_precedents]
    disparitions = [cle for cle in etats_precedents if cle not in lignes_par_cle]
    modifications: list[Modification] = []
    for cle, l in lignes_par_cle.items():
        etat = etats_precedents.get(cle)
        if etat is None:
            continue
        empreinte_actuelle = calculer_empreinte(l.champs)
        if empreinte_actuelle == etat.empreinte:
            continue
        champs_avant = etat.donnees_normalisees or {}
        champs_changes = sorted(
            k for k in set(champs_avant) | set(l.champs) if champs_avant.get(k) != l.champs.get(k)
        )
        modifications.append(
            Modification(cle=cle, champs_avant=champs_avant, champs_apres=l.champs, champs_changes=champs_changes)
        )

    # --- Run de référence : amorce l'état, aucun candidat, jamais de quarantaine ---
    if run_reference:
        # `lignes_par_cle.values()`, JAMAIS `lignes` brut : `lignes` peut
        # contenir des doublons de clé naturelle (voir avertissement plus
        # haut, découverte réelle sur les données Toronto) — un INSERT en
        # lot (contrairement à un ORM `add()` par ligne) ne les tolère pas,
        # la contrainte UNIQUE (source_id, cle_naturelle) rejette le lot
        # entier au moindre doublon.
        _inserer_lignes_en_lot(db_session, source_id, list(lignes_par_cle.values()))
        db_session.add(EtatSchemaSource(source_id=source_id, colonnes=colonnes_vues))
        db_session.flush()
        rapport.resultat = None
        return rapport

    # --- Règle de quarantaine sur le volume ---
    if (
        _seuil_franchi(len(apparitions), len(etats_precedents), seuils.apparitions)
        or _seuil_franchi(len(disparitions), len(etats_precedents), seuils.disparitions)
        or _seuil_franchi(len(modifications), len(etats_precedents), seuils.modifications)
    ):
        motif = (
            MotifQuarantaine.VOLUME_DISPARITIONS
            if _seuil_franchi(len(disparitions), len(etats_precedents), seuils.disparitions)
            else MotifQuarantaine.VOLUME_APPARITIONS
            if _seuil_franchi(len(apparitions), len(etats_precedents), seuils.apparitions)
            else MotifQuarantaine.VOLUME_MODIFICATIONS
        )
        chemin_archive = _archiver_snapshot(source_id, lignes)
        q = DiffQuarantaine(
            source_id=source_id,
            motif=motif,
            detail={
                "nb_apparitions": len(apparitions),
                "nb_disparitions": len(disparitions),
                "nb_modifications": len(modifications),
                "nb_lignes_precedentes": len(etats_precedents),
                "seuils": {
                    "apparitions": {"pct": seuils.apparitions.pct, "abs": seuils.apparitions.abs},
                    "disparitions": {"pct": seuils.disparitions.pct, "abs": seuils.disparitions.abs},
                    "modifications": {"pct": seuils.modifications.pct, "abs": seuils.modifications.abs},
                },
                "apparitions": [{"cle": l.cle, "champs": l.champs} for l in apparitions],
                "disparitions": disparitions,
                "modifications": [
                    {"cle": m.cle, "champs_avant": m.champs_avant, "champs_apres": m.champs_apres,
                     "champs_changes": m.champs_changes}
                    for m in modifications
                ],
                "colonnes_vues": colonnes_vues,
            },
            chemin_archive=chemin_archive,
        )
        db_session.add(q)
        db_session.flush()
        rapport.quarantaine = True
        rapport.motif_quarantaine = motif
        rapport.quarantaine_id = q.id
        logger.warning(
            "Source %s en quarantaine (%s) : %d apparitions, %d disparitions, %d modifications sur %d lignes précédentes",
            source_id, motif.value, len(apparitions), len(disparitions), len(modifications), len(etats_precedents),
        )
        return rapport

    # --- Diff accepté normalement : applique l'état ---
    _archiver_snapshot(source_id, lignes)
    _appliquer_diff(db_session, source_id, apparitions, disparitions, modifications, colonnes_vues)
    rapport.resultat = ResultatDiff(apparitions=apparitions, disparitions=disparitions, modifications=modifications)
    return rapport


def _appliquer_diff(
    db_session: Session,
    source_id: str,
    apparitions: list[LigneSnapshot],
    disparitions: list[str],
    modifications: list[Modification],
    colonnes_vues: dict[str, str],
) -> None:
    _inserer_lignes_en_lot(db_session, source_id, apparitions)
    for m in modifications:
        etat = db_session.execute(
            select(EtatLigneSource).where(
                EtatLigneSource.source_id == source_id, EtatLigneSource.cle_naturelle == m.cle
            )
        ).scalar_one()
        etat.empreinte = calculer_empreinte(m.champs_apres)
        etat.donnees_normalisees = m.champs_apres
    if disparitions:
        for etat in (
            db_session.execute(
                select(EtatLigneSource).where(
                    EtatLigneSource.source_id == source_id, EtatLigneSource.cle_naturelle.in_(disparitions)
                )
            )
            .scalars()
            .all()
        ):
            db_session.delete(etat)

    etat_schema = db_session.get(EtatSchemaSource, source_id)
    if etat_schema is None:
        db_session.add(EtatSchemaSource(source_id=source_id, colonnes=colonnes_vues))
    else:
        etat_schema.colonnes = colonnes_vues
    db_session.flush()


SEUIL_QUARANTAINES_SIMULTANEES_SUSPECT = 2


def suspicion_incident_local(rapports: list[RapportExecution]) -> bool:
    """Réponse à la question de la section 11 : « deux sources en quarantaine
    dans la même exécution ? ». La quarantaine reste STRICTEMENT par source
    (deux incidents indépendants, aucun des deux ne bloque le pipeline des
    autres) — mais le CUMUL est lui-même un signal : deux diffuseurs
    indépendants qui changent leur format le même jour est improbable, deux
    quarantaines simultanées pointent bien plus vraisemblablement vers un
    problème DE NOTRE CÔTÉ (réseau, disque, déploiement récent, dépendance
    mise à jour). L'appelant (falkye/cli.py ou un futur wrapper de veille)
    émet alors une alerte d'exploitation DISTINCTE, formulée comme une
    suspicion d'incident local et non comme un problème de source."""
    return sum(1 for r in rapports if r.quarantaine) >= SEUIL_QUARANTAINES_SIMULTANEES_SUSPECT


def lister_quarantaines(db_session: Session, statut: StatutQuarantaine | None = StatutQuarantaine.EN_ATTENTE):
    query = select(DiffQuarantaine)
    if statut is not None:
        query = query.where(DiffQuarantaine.statut == statut)
    return db_session.execute(query.order_by(DiffQuarantaine.created_at.desc())).scalars().all()


def lever_quarantaine(
    db_session: Session, quarantaine_id: int, *, decision: str, qui: str, motif: str
) -> RapportExecution | None:
    """Action explicite et journalisée (qui, quand, motif) — réservée au mode
    opérateur (falkye/cli.py). `decision` : "acceptee" (le diff calculé au
    moment de la quarantaine est appliqué TEL QUEL, jamais une nouvelle
    collecte) ou "rejetee" (état précédent conservé, rien n'est appliqué)."""
    if decision not in ("acceptee", "rejetee"):
        raise ValueError(f"decision invalide : {decision!r} (acceptee|rejetee attendu)")

    q = db_session.get(DiffQuarantaine, quarantaine_id)
    if q is None:
        raise ValueError(f"Quarantaine #{quarantaine_id} introuvable.")
    if q.statut != StatutQuarantaine.EN_ATTENTE:
        raise ValueError(f"Quarantaine #{quarantaine_id} déjà traitée (statut={q.statut.value}).")

    q.levee_par = qui
    q.levee_le = datetime.now(timezone.utc)
    q.levee_motif = motif

    if decision == "rejetee":
        q.statut = StatutQuarantaine.REJETEE
        db_session.flush()
        return None

    q.statut = StatutQuarantaine.ACCEPTEE

    detail = q.detail or {}
    # Une quarantaine de type SCHEMA n'a pas de diff de contenu calculé (elle
    # s'est déclenchée avant même la comparaison) — accepter un tel cas
    # signifie "le nouveau schéma est légitime", on amorce simplement le
    # nouvel état comme un run de référence PARTIEL (schéma seulement),
    # laissant le PROCHAIN run recalculer le vrai diff de contenu contre ce
    # nouveau schéma — jamais une fusion aveugle avec l'ancien état, qui
    # pourrait comparer des colonnes qui ne veulent plus dire la même chose.
    if q.motif in (MotifQuarantaine.SCHEMA_COLONNE_RETIREE, MotifQuarantaine.SCHEMA_TYPE_MODIFIE):
        colonnes_vues = detail.get("colonnes_vues", {})
        etat_schema = db_session.get(EtatSchemaSource, q.source_id)
        if etat_schema is None:
            db_session.add(EtatSchemaSource(source_id=q.source_id, colonnes=colonnes_vues))
        else:
            etat_schema.colonnes = colonnes_vues
        db_session.flush()
        return RapportExecution(source_id=q.source_id, quarantaine=False, resultat=None)

    apparitions = [LigneSnapshot(cle=a["cle"], champs=a["champs"]) for a in detail.get("apparitions", [])]
    disparitions = list(detail.get("disparitions", []))
    modifications = [
        Modification(
            cle=m["cle"], champs_avant=m["champs_avant"], champs_apres=m["champs_apres"],
            champs_changes=m["champs_changes"],
        )
        for m in detail.get("modifications", [])
    ]
    colonnes_vues = detail.get("colonnes_vues", {})

    _appliquer_diff(db_session, q.source_id, apparitions, disparitions, modifications, colonnes_vues)
    return RapportExecution(
        source_id=q.source_id,
        quarantaine=False,
        resultat=ResultatDiff(apparitions=apparitions, disparitions=disparitions, modifications=modifications),
        nb_lignes_actuelles=len(apparitions) + len(modifications),
    )
