"""Interface générique des connecteurs de sources (spec section 9).

Le moteur (observador/engine.py) ne connaît QUE cette interface — jamais une source
précise. Ajouter une source = écrire une classe qui hérite de SourceConnector,
l'exposer comme CONNECTOR_CLASS dans son module, et pointer `connecteur:` vers ce
module dans registry/sources.yaml. Rien d'autre à toucher.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from observador.registry.loader import SourceDef


@dataclass
class RawSignal:
    """Ce qu'un connecteur produit pour une détection brute, avant résolution NEQ,
    vérification et scoring (qui sont des étapes génériques du moteur, pas du
    connecteur — spec section 7 : "chaque source doit capturer ces champs
    directement quand ils sont disponibles, et sinon le système doit les résoudre
    via le REQ")."""

    signal_type_id: str
    nom_entreprise: str
    detected_at: datetime
    source_ref: str  # identifiant/URL unique dans la source, pour déduplication

    neq: str | None = None                 # rare : seul REQ le fournit directement
    adresse: str | None = None
    ville: str | None = None
    region: str | None = None
    secteur_activite: str | None = None
    site_web: str | None = None

    valeur_associee: float | None = None
    titre_ou_description: str | None = None

    # Tous les champs pertinents définis dans sources.yaml pour cette source,
    # conservés intégralement (spec section 7, "principe transversal").
    champs: dict = field(default_factory=dict)


class SourceConnector(ABC):
    """Base commune. `source_def` donne accès au gabarit du registre (champs
    pertinents attendus, statut, etc.) sans que le connecteur ait à le redéfinir."""

    def __init__(self, source_def: "SourceDef"):
        self.source_def = source_def

    @property
    def source_id(self) -> str:
        return self.source_def.id

    @abstractmethod
    def detect(self, since: datetime | None, db_session: "Session") -> Iterator[RawSignal]:
        """Produit les signaux détectés depuis `since` (None = tout ce que la source
        expose raisonnablement, ex. le fichier le plus récent). Un connecteur peut
        ne rien produire (source temporairement indisponible) sans que ce soit une
        erreur — logguer plutôt que planter le moteur pour les autres sources.

        `db_session` est fourni à TOUS les connecteurs pour rester cohérent, mais
        seul REQ s'en sert réellement (il maintient un miroir local pour la
        résolution NEQ et la détection de changement par diff — voir
        observador/sources/req.py). Les autres connecteurs l'ignorent : ils restent
        de simples générateurs sans effet de bord sur la base."""
        raise NotImplementedError

    def disponible(self) -> bool:
        """Vérification légère (pas de coût réseau significatif) que la source est
        actuellement joignable. Le moteur peut s'en servir pour un diagnostic rapide
        avant de lancer un scan complet."""
        return True

    def inspect_file(self, path) -> dict:
        """Optionnel — pour une source en `methode_acces: import_manuel` dont le
        fichier importé a une structure interne pas encore confirmée contre de
        vraies données (ex. REQ : le fichier en vrac réel contient six CSV liés
        entre eux, pas un seul fichier plat, découvert le 2026-08-31 — voir
        docs/STATUT_RESEAU.md). Doit lire uniquement l'en-tête (+ éventuellement
        une ligne d'exemple) de chaque fichier interne, SANS tout charger en
        mémoire ni tenter d'importer quoi que ce soit — sert à confirmer les
        vrais noms de colonnes avant d'écrire une logique de jointure/mapping à
        l'aveugle, ce que ce projet interdit (données réelles non négociables,
        échec explicite plutôt qu'interprétation silencieuse erronée). Retourne
        `{nom_de_fichier: {"colonnes": [...], "exemple": {...}, ...}}`. Un
        connecteur qui ne supporte pas ce mode (structure déjà simple et
        confirmée) lève NotImplementedError explicitement."""
        raise NotImplementedError(
            f"{type(self).__name__} ne supporte pas l'inspection de fichier "
            "(inspect_file non implémenté) — sa structure est déjà simple/confirmée, "
            "utilisez directement 'import-manuel fichier'."
        )

    def detect_from_file(self, path, db_session: "Session") -> Iterator[RawSignal]:
        """Optionnel — pour une source en `methode_acces: import_manuel` dont
        l'import se fait par FICHIER COMPLET plutôt que par résultat individuel
        (ex. REQ : Alexandre télécharge lui-même le fichier en vrac, bloqué en
        téléchargement automatisé pour cette session — voir docs/STATUT_RESEAU.md
        — puis l'importe). Complète observador/manual_import.py, qui couvre le cas
        "un document = une entreprise" (ex. RDPRM) ; ce chemin-ci couvre "un
        fichier = potentiellement des milliers d'entreprises", en réutilisant la
        même logique de parsing/diff qu'un connecteur automatisé (ex.
        req.py:ingest_snapshot) sans dupliquer de mécanique. Un connecteur qui ne
        supporte pas ce mode lève NotImplementedError explicitement."""
        raise NotImplementedError(
            f"{type(self).__name__} ne supporte pas l'import manuel par fichier "
            "(detect_from_file non implémenté)."
        )


class StubConnector(SourceConnector):
    """Connecteur pour une source au statut `a_developper` : ne renvoie jamais de
    résultat, mais existe dans le registre (spec section 9 : "Une source 'à
    développer' ne retourne simplement aucun résultat tant qu'elle n'est pas
    activée — mais elle est visible et prête à être complétée.")."""

    def detect(self, since: datetime | None, db_session: "Session") -> Iterator[RawSignal]:
        return iter(())

    def disponible(self) -> bool:
        return False
