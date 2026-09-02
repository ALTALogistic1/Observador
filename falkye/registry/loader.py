"""Chargeur générique des registres (sources, types de signaux, sphères, canaux).

Principe central de l'architecture (spec section 9) : ces registres sont la SEULE
source de vérité sur "quelles sources/signaux/canaux existent et sont actifs". Rien
dans le moteur (falkye/engine.py) ne doit connaître le nom d'une source précise
en dur — tout passe par ces gabarits chargés dynamiquement.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REGISTRY_DIR = Path(__file__).parent

# Structure de plans tarifaires (spec section 9bis) — un seul portail sous-jacent,
# deux couches par-dessus (Radar : paiement intégré ; Radar+ : clés API utilisateur),
# donc un seul ordre linéaire plutôt que des ensembles disjoints. Valeurs répétées
# dans falkye/models/profile.py::PlanTarifaire (SQLAlchemy) — celle-ci est la
# référence côté registre, indépendante du modèle de données.
PLANS_TARIFAIRES = ("echo", "radar", "radar_plus")


def _load_yaml(filename: str) -> dict[str, Any]:
    path = REGISTRY_DIR / filename
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@dataclass(frozen=True)
class SourceDef:
    id: str
    nom: str
    signal_associe: list[str]
    statut: str  # actif | inactif | a_developper | en_pause
    blocage_type: str | None
    methode_acces: str | None
    champs_pertinents: list[str]
    cout: str | None
    region: str | None
    connecteur: str | None
    notes: str | None = None
    # Principe directeur non négociable (spec, "Principes directeurs" #3) : aucune
    # source n'est activée sans une règle concrète et vérifiable qui distingue un
    # vrai signal de croissance du bruit. Ce champ documente CETTE règle — vide
    # tant qu'elle n'est pas définie, auquel cas la source doit rester `a_developper`
    # (voir Registry.valider_calibration ci-dessous, qui l'impose).
    regle_calibration: str | None = None
    # Lien direct vers la page de recherche/consultation de la source (spec section 9,
    # "Import manuel de documents sources") — obligatoire quand methode_acces ==
    # "import_manuel", pour que le système présente à l'utilisateur le bon endroit où
    # faire sa recherche ponctuelle plutôt que la page d'accueil générique du site.
    lien_recherche: str | None = None
    # Structure de plans tarifaires (spec section 9bis, 2026-09-02) : plan minimal
    # requis pour qu'un PROFIL reçoive une notification bâtie (en tout ou en partie)
    # sur un signal de cette source — "echo" (défaut, sources gratuites) / "radar"
    # (payant, géré par nous) / "radar_plus" (payant, clé API fournie par
    # l'utilisateur — mécanisme de gestion de clés non encore construit, voir
    # docs/STATUT_RESEAU.md). N'affecte QUE la sélection de signaux par profil
    # (falkye/engine.py) — jamais l'ingestion elle-même, qui reste globale au
    # dossier cumulatif (spec section 5) comme pour toute autre source.
    plan_minimum: str = "echo"

    @property
    def est_actif(self) -> bool:
        return self.statut == "actif"

    @property
    def est_import_manuel(self) -> bool:
        return self.methode_acces == "import_manuel"

    def disponible_pour_plan(self, plan: str) -> bool:
        """Est-ce qu'un profil sur `plan` peut recevoir un signal de cette source ?
        Plans strictement ordonnés (echo < radar < radar_plus, spec section 9bis) —
        un plan supérieur inclut toujours tout ce qu'offre un plan inférieur."""
        return PLANS_TARIFAIRES.index(plan) >= PLANS_TARIFAIRES.index(self.plan_minimum)

    def charger_connecteur(self):
        """Importe et instancie la classe SourceConnector associée.

        Retourne None si aucun connecteur n'est encore codé (statut a_developper
        sans module) — c'est un état normal du registre, pas une erreur.
        """
        if not self.connecteur:
            return None
        module = importlib.import_module(self.connecteur)
        connector_cls = getattr(module, "CONNECTOR_CLASS", None)
        if connector_cls is None:
            raise AttributeError(
                f"Le module {self.connecteur} ne définit pas CONNECTOR_CLASS "
                f"(voir falkye/sources/base.py)."
            )
        return connector_cls(source_def=self)


@dataclass(frozen=True)
class SignalTypeDef:
    id: str
    nom: str
    icone: str
    description: str
    sources_associees: list[str]
    criteres_confiance: list[str]
    spheres_probables: list[str]


@dataclass(frozen=True)
class SphereDef:
    id: str
    nom: str
    est_personnalisee: bool = False
    proposee_par: str | None = None
    # Principe du "signal par absence" (spec section 6, restructurée) : l'ABSENCE
    # d'un type de signal normalement attendu à un stade plus avancé peut être un
    # indicateur de pertinence positif, pas seulement la présence d'un signal —
    # découvert avec le persona investisseur providentiel (croissance visible mais
    # AUCUN financement encore visible = traction précoce). Généralisé ici plutôt
    # que codé en dur pour cette seule sphère : n'importe quelle sphère peut
    # déclarer l'id d'un type de signal (falkye/registry/signal_types.yaml) dont
    # l'absence, alors que d'autres signaux existent déjà pour l'entreprise, est
    # elle-même pertinente — voir falkye/pertinence.py:bonus_signal_absence.
    signal_absence_pertinent: str | None = None


@dataclass(frozen=True)
class NotificationChannelDef:
    id: str
    nom: str
    statut: str  # actif | a_developper
    priorite: int
    fournisseur_technique: str | None
    champs_config_requis: list[str]
    module: str | None
    notes: str | None = None

    @property
    def est_actif(self) -> bool:
        return self.statut == "actif"

    def charger_canal(self):
        if not self.module:
            return None
        module = importlib.import_module(self.module)
        channel_cls = getattr(module, "CHANNEL_CLASS", None)
        if channel_cls is None:
            raise AttributeError(
                f"Le module {self.module} ne définit pas CHANNEL_CLASS "
                f"(voir falkye/notifications/base.py)."
            )
        return channel_cls(channel_def=self)


@dataclass
class Registry:
    sources: dict[str, SourceDef] = field(default_factory=dict)
    signal_types: dict[str, SignalTypeDef] = field(default_factory=dict)
    spheres: dict[str, SphereDef] = field(default_factory=dict)
    notification_channels: dict[str, NotificationChannelDef] = field(default_factory=dict)

    def sources_actives(self) -> list[SourceDef]:
        """TOUTES les sources actives, y compris celles en import manuel (utile
        pour l'affichage/l'inventaire — ex. `falkye registry sources`)."""
        return [s for s in self.sources.values() if s.est_actif]

    def sources_actives_automatisees(self) -> list[SourceDef]:
        """Sources actives que le moteur doit boucler dessus AUTOMATIQUEMENT
        (spec section 9) — exclut celles en `methode_acces: import_manuel`,
        qui ne produisent des signaux que via une action explicite de
        l'utilisateur (falkye/manual_import.py), jamais dans la boucle de
        scan planifiée. Utilisée par engine.ingest_all_active_sources."""
        return [s for s in self.sources_actives() if not s.est_import_manuel]

    def canaux_actifs(self) -> list[NotificationChannelDef]:
        return sorted(
            (c for c in self.notification_channels.values() if c.est_actif),
            key=lambda c: c.priorite,
        )

    def canal(self, channel_id: str) -> NotificationChannelDef:
        return self.notification_channels[channel_id]

    def source(self, source_id: str) -> SourceDef:
        return self.sources[source_id]

    def signal_type(self, signal_type_id: str) -> SignalTypeDef:
        return self.signal_types[signal_type_id]

    def sphere(self, sphere_id: str) -> SphereDef | None:
        return self.spheres.get(sphere_id)

    def valider_calibration(self) -> None:
        """Applique le principe directeur non négociable : aucune source active
        sans règle de calibration documentée. Appelé avant tout scan réel
        (falkye/engine.py) plutôt qu'au chargement du registre, pour que
        consulter/éditer le registre reste toujours possible même en cours
        d'ajustement d'une règle."""
        sans_regle = [s.id for s in self.sources_actives() if not s.regle_calibration]
        if sans_regle:
            raise ValueError(
                "Principe directeur non négociable violé : source(s) active(s) sans "
                f"règle de calibration documentée (regle_calibration) : {sans_regle}. "
                "Documenter la règle dans registry/sources.yaml ou repasser le statut "
                "à `a_developper`."
            )

        # Spec section 9, "Import manuel de documents sources" : chaque source en
        # import manuel doit avoir un lien direct vers sa page de recherche.
        sans_lien = [
            s.id for s in self.sources_actives() if s.est_import_manuel and not s.lien_recherche
        ]
        if sans_lien:
            raise ValueError(
                f"Source(s) en import manuel sans lien_recherche documenté : {sans_lien}. "
                "Voir registry/sources.yaml."
            )


def load_registry() -> Registry:
    sources_raw = _load_yaml("sources.yaml")["sources"]
    signals_raw = _load_yaml("signal_types.yaml")["signal_types"]
    spheres_raw = _load_yaml("spheres.yaml")["spheres"]
    channels_raw = _load_yaml("notification_channels.yaml")["channels"]

    sources = {s["id"]: SourceDef(**s) for s in sources_raw}
    signal_types = {s["id"]: SignalTypeDef(**s) for s in signals_raw}
    spheres = {s["id"]: SphereDef(**s) for s in spheres_raw}
    notification_channels = {c["id"]: NotificationChannelDef(**c) for c in channels_raw}

    return Registry(
        sources=sources,
        signal_types=signal_types,
        spheres=spheres,
        notification_channels=notification_channels,
    )


_registry_singleton: Registry | None = None


def get_registry() -> Registry:
    """Retourne le registre chargé une seule fois par processus (rechargeable via reload)."""
    global _registry_singleton
    if _registry_singleton is None:
        _registry_singleton = load_registry()
    return _registry_singleton


def reload_registry() -> Registry:
    global _registry_singleton
    _registry_singleton = load_registry()
    return _registry_singleton
