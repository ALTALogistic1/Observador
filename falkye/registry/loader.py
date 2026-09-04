"""Chargeur générique des registres (sources, types de signaux, sphères, canaux).

Principe central de l'architecture (spec section 9) : ces registres sont la SEULE
source de vérité sur "quelles sources/signaux/canaux existent et sont actifs". Rien
dans le moteur (falkye/engine.py) ne doit connaître le nom d'une source précise
en dur — tout passe par ces gabarits chargés dynamiquement.
"""
from __future__ import annotations

import importlib
import re
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
    # Détection d'expansion inter-provinciale (spec Radar+, point 7, ajoutée le
    # 2026-09-03) — code de PROVINCE précis (qc/on/bc/ns/...), délibérément
    # DISTINCT de `region` ci-dessus (texte libre à granularité incohérente —
    # "Vancouver" vs "Québec" vs "Canada", impropre à une comparaison
    # programmatique). None = territoire non provincial (fédéral, national,
    # pancanadien) ou pas encore cartographié — jamais deviné, la source est
    # simplement exclue du mécanisme (falkye/expansion_interprovinciale.py).
    province_code: str | None = None

    # Chantier 1 (audit du 2026-09-03, faille E — voir docs/ARCHITECTURE.md) :
    # "evenement" (défaut) = chaque enregistrement porte sa propre date fiable,
    # aucune conservation d'état nécessaire pour savoir si c'est nouveau.
    # "instantane" = aucune date d'événement fiable par ligne (RACJ, licences
    # municipales, Nouvelle-Écosse...) — le signal naît de la comparaison entre
    # deux instantanés successifs, voir falkye/diff_engine.py. Détermine si
    # cette source passe par le moteur de diff/quarantaine générique.
    type_ingestion: str = "evenement"
    # Clé naturelle DÉCLARÉE, jamais devinée par le moteur (mandat du chantier :
    # "elle varie franchement"). Liste de noms LOGIQUES de champs (même
    # convention que champs_pertinents) composés en une seule chaîne par
    # l'appelant (falkye/diff_engine.py) — obligatoire quand type_ingestion ==
    # "instantane", ignoré sinon.
    cle_naturelle: list[str] | None = None
    # Seuils de quarantaine par type d'écart (apparitions/disparitions/
    # modifications), chacun {"pct": float, "abs": int} — LES DEUX doivent être
    # franchis pour déclencher la quarantaine sur ce type (voir falkye/
    # diff_engine.py:SEUILS_DEFAUT pour le repli si absent ici). Valeurs
    # spécifiques à CETTE source, à calibrer contre son vrai volume observé —
    # jamais une seule constante globale (une source à 200 lignes et une à
    # 160 000 n'ont pas le même bruit normal).
    seuils_quarantaine: dict | None = None
    # Variante EXACTE de licence ouverte lue sur la fiche du jeu de données
    # précis (charte section 12ter — jamais présumée depuis le portail en
    # bloc ; une licence ouverte se décline en plusieurs variantes, dont des
    # variantes NC qui interdisent l'usage commercial). None = source non
    # publiée sous licence ouverte (donnée propriétaire, API commerciale,
    # accès contractuel...), pas encore vérifiée, ou statut légal couvert
    # autrement (blocage_type). Un usage commercial sous licence NC exige une
    # autorisation préalable de l'organisme — voir `notes` pour l'échéance de
    # revalidation propre à chaque source concernée (charte section 15 : une
    # vérification se périme, elle a besoin d'une échéance, pas d'une bonne
    # intention).
    licence_ouverte: str | None = None

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
class ChampsPertinentsDef:
    """Une entrée de la grille de pertinence par champ (spec section 6,
    "Filtrage par champ, contextuel au profil", ajoutée le 2026-09-02) — voir
    registry/champs_pertinents.yaml pour la distinction avec la calibration à
    l'ingestion (SourceDef.regle_calibration, différente, inchangée)."""

    sphere_id: str
    source_id: str
    champs_pertinents: list[str]
    notes: str | None = None


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
    # Assistance à la configuration du profil par IA (spec Radar+, point 8,
    # ajoutée le 2026-09-03) — Niveau 1 : mots-clés/synonymes servant à faire
    # correspondre localement une description libre de l'utilisateur à cette
    # sphère, SANS appel API (gratuit, tous plans — falkye/assistance_sphere.py).
    # Premier jet volontairement large plutôt qu'exhaustif : ce noyau vit dans
    # le registre (le YAML fait foi), mais le Niveau 2 (Claude, Radar/Radar+
    # seulement) peut ENRICHIR silencieusement le dictionnaire d'une sphère
    # EXISTANTE en base (falkye/models/sphere_synonyme.py::SphereSynonyme,
    # origine="ia_niveau2") sans jamais toucher à ce fichier — même principe
    # que Sphere.est_personnalisee : le noyau curé reste ici, les enrichissements
    # vivent en base.
    synonymes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ClientCibleDef:
    """Une catégorie de client cible ("qui", spec section 8bis, 2026-09-03) —
    voir registry/clients_cibles.yaml pour le contexte complet (pourquoi ce
    registre est indépendant du regroupement de secteurs REQ). Même structure
    que SphereDef (id, nom, synonymes pour le Niveau 1), même principe
    d'extensibilité (noyau curé ici, enrichissements en base via
    falkye/models/client_cible_synonyme.py, origine="ia_niveau2")."""

    id: str
    nom: str
    est_personnalisee: bool = False
    proposee_par: str | None = None
    synonymes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class StatutSuiviDef:
    """Statut de suivi du tableau de bord (spec section 4bis, ajoutée le
    2026-09-02, "Radar et Radar+ seulement") — même principe d'extensibilité que
    SphereDef : le noyau curé vit ici, les statuts proposés par les utilisateurs
    vivent en base (falkye/models/statut_suivi.py::StatutSuivi,
    est_personnalise=True)."""

    id: str
    nom: str
    est_defaut: bool = False
    # Spec : "un statut 'Pas pertinent' sert... de signal de rétroaction pour le
    # moteur de pertinence" — champ de registre plutôt qu'un id figé en dur dans
    # le moteur (falkye/retroaction.py), pour qu'un futur deuxième statut de
    # rétroaction n'exige aucune modification de code.
    declenche_retroaction: bool = False


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


@dataclass(frozen=True)
class CrmProviderDef:
    """Un fournisseur CRM (HubSpot, Pipedrive — voir registry/crm_providers.yaml)
    — intégration CRM, ajoutée le 2026-09-02. Même principe que
    NotificationChannelDef (charger_canal), avec une distinction : `champs_
    mappage` porte le mappage PAR DÉFAUT des champs FALKYE vers des noms de
    propriété/champ CRM, ajustable par connexion (falkye/models/
    crm_connection.py::CrmConnection.champs_mappage_override) — voir la note
    Pipedrive dans le YAML pour pourquoi ce n'est qu'un défaut, pas une vérité
    universelle.

    `domaine_type`/`avantage_concret` : format standard des cartes de source à
    l'étape de connexion, portail Radar/Radar+ (spec section 9bis, ajouté le
    2026-09-02) — jamais un nom de marque seul, toujours ces deux éléments
    affichés ensemble pour que le client choisisse en connaissance de cause.
    Voir `falkye crm fournisseurs`."""

    id: str
    nom: str
    statut: str  # actif | a_developper
    module: str | None
    objet_crm_cible: str | None
    champs_mappage: dict[str, str] = field(default_factory=dict)
    domaine_type: str | None = None
    avantage_concret: str | None = None
    notes: str | None = None

    @property
    def est_actif(self) -> bool:
        return self.statut == "actif"

    def charger_fournisseur(self):
        if not self.module:
            return None
        module = importlib.import_module(self.module)
        provider_cls = getattr(module, "PROVIDER_CLASS", None)
        if provider_cls is None:
            raise AttributeError(
                f"Le module {self.module} ne définit pas PROVIDER_CLASS "
                f"(voir falkye/notifications/crm/base.py)."
            )
        return provider_cls(provider_def=self)


@dataclass(frozen=True)
class SecteurGrossierDef:
    """Une catégorie du regroupement grossier de secteurs REQ (spec section
    4bis, tableaux de bord agrégés) — voir registry/secteurs_grossiers.yaml
    pour le contexte complet (pourquoi un regroupement par mots-clés, pas par
    libellé exact ni par fréquence littérale) et le principe "première
    catégorie qui matche gagne, l'ordre du fichier est significatif"."""

    id: str
    nom: str
    mots_cles: list[str]


@dataclass
class Registry:
    sources: dict[str, SourceDef] = field(default_factory=dict)
    signal_types: dict[str, SignalTypeDef] = field(default_factory=dict)
    spheres: dict[str, SphereDef] = field(default_factory=dict)
    clients_cibles: dict[str, ClientCibleDef] = field(default_factory=dict)
    notification_channels: dict[str, NotificationChannelDef] = field(default_factory=dict)
    statuts_suivi: dict[str, StatutSuiviDef] = field(default_factory=dict)
    # Clé (sphere_id, source_id) — voir registry/champs_pertinents.yaml.
    champs_pertinents: dict[tuple[str, str], ChampsPertinentsDef] = field(default_factory=dict)
    crm_providers: dict[str, CrmProviderDef] = field(default_factory=dict)
    # Liste, PAS un dict — l'ordre est significatif (première catégorie qui
    # matche gagne, voir registry/secteurs_grossiers.yaml).
    secteurs_grossiers: list[SecteurGrossierDef] = field(default_factory=list)

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

    def client_cible(self, client_cible_id: str) -> ClientCibleDef | None:
        return self.clients_cibles.get(client_cible_id)

    def statut_suivi(self, statut_id: str) -> StatutSuiviDef | None:
        return self.statuts_suivi.get(statut_id)

    def statut_suivi_par_defaut(self) -> StatutSuiviDef:
        """Le statut attribué à toute notification nouvellement créée (spec
        section 4bis) — validé unique par valider_calibration ci-dessous."""
        for s in self.statuts_suivi.values():
            if s.est_defaut:
                return s
        raise ValueError(
            "Aucun statut de suivi par défaut (est_defaut: true) dans "
            "registry/statuts_suivi.yaml."
        )

    def statuts_suivi_declencheurs_retroaction(self) -> list[StatutSuiviDef]:
        return [s for s in self.statuts_suivi.values() if s.declenche_retroaction]

    def champs_pertinents_pour(self, sphere_id: str, source_id: str) -> list[str] | None:
        """Liste blanche des clés de `Signal.champs` pertinentes pour cette
        sphère, pour cette source — spec section 6, "Filtrage par champ,
        contextuel au profil". `None` = AUCUNE entrée déclarée = aucun
        filtrage, tous les champs comptent (défaut sûr, voir registry/
        champs_pertinents.yaml). Utilisé par falkye/pertinence.py::
        filtrer_champs_pertinents, jamais à l'ingestion."""
        entree = self.champs_pertinents.get((sphere_id, source_id))
        return entree.champs_pertinents if entree is not None else None

    def fournisseurs_crm_actifs(self) -> list[CrmProviderDef]:
        return [p for p in self.crm_providers.values() if p.est_actif]

    def fournisseur_crm(self, provider_id: str) -> CrmProviderDef | None:
        return self.crm_providers.get(provider_id)

    def classer_secteur(self, secteur_activite_libelle: str | None) -> str | None:
        """Catégorie grossière (id de registry/secteurs_grossiers.yaml) pour un
        libellé de secteur REQ — regroupement PAR MOTS-CLÉS, pas par
        correspondance exacte (la quasi-totalité des libellés réels sont
        uniques mot pour mot, voir le YAML). Retourne None dans DEUX cas
        distincts, jamais confondus par l'appelant (falkye/synthese.py) :
        `secteur_activite_libelle` vide/absent (rien à classer), OU aucune
        catégorie ne matche (~25% des cas réels — jamais forcé dans une
        catégorie approximative, principe directeur #1)."""
        if not secteur_activite_libelle:
            return None
        libelle = secteur_activite_libelle.lower()
        for categorie in self.secteurs_grossiers:
            if any(re.search(motif, libelle, re.IGNORECASE) for motif in categorie.mots_cles):
                return categorie.id
        return None

    def secteur_grossier(self, categorie_id: str) -> SecteurGrossierDef | None:
        return next((c for c in self.secteurs_grossiers if c.id == categorie_id), None)

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
    clients_cibles_raw = _load_yaml("clients_cibles.yaml")["clients_cibles"]
    channels_raw = _load_yaml("notification_channels.yaml")["channels"]
    statuts_suivi_raw = _load_yaml("statuts_suivi.yaml")["statuts_suivi"]
    champs_pertinents_raw = _load_yaml("champs_pertinents.yaml")["champs_pertinents"]
    crm_providers_raw = _load_yaml("crm_providers.yaml")["crm_providers"]
    secteurs_grossiers_raw = _load_yaml("secteurs_grossiers.yaml")["secteurs_grossiers"]

    sources = {s["id"]: SourceDef(**s) for s in sources_raw}
    signal_types = {s["id"]: SignalTypeDef(**s) for s in signals_raw}
    spheres = {s["id"]: SphereDef(**s) for s in spheres_raw}
    clients_cibles = {c["id"]: ClientCibleDef(**c) for c in clients_cibles_raw}
    notification_channels = {c["id"]: NotificationChannelDef(**c) for c in channels_raw}
    statuts_suivi = {s["id"]: StatutSuiviDef(**s) for s in statuts_suivi_raw}
    champs_pertinents = {
        (c["sphere_id"], c["source_id"]): ChampsPertinentsDef(**c) for c in champs_pertinents_raw
    }
    crm_providers = {p["id"]: CrmProviderDef(**p) for p in crm_providers_raw}
    secteurs_grossiers = [SecteurGrossierDef(**s) for s in secteurs_grossiers_raw]

    nb_defauts = sum(1 for s in statuts_suivi.values() if s.est_defaut)
    if nb_defauts != 1:
        raise ValueError(
            f"registry/statuts_suivi.yaml doit déclarer EXACTEMENT un statut "
            f"est_defaut: true (trouvé {nb_defauts})."
        )

    from falkye.models.client_cible import ID_AUCUNE_RESTRICTION

    if ID_AUCUNE_RESTRICTION not in clients_cibles:
        raise ValueError(
            f"registry/clients_cibles.yaml doit déclarer l'entrée sentinelle "
            f"'{ID_AUCUNE_RESTRICTION}' (falkye/models/client_cible.py::ID_AUCUNE_RESTRICTION)."
        )

    return Registry(
        sources=sources,
        signal_types=signal_types,
        spheres=spheres,
        clients_cibles=clients_cibles,
        notification_channels=notification_channels,
        statuts_suivi=statuts_suivi,
        champs_pertinents=champs_pertinents,
        crm_providers=crm_providers,
        secteurs_grossiers=secteurs_grossiers,
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
