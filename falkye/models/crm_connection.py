"""Connexion CRM (HubSpot/Pipedrive) par profil — intégration CRM, retenue depuis
un moment dans la liste de fonctionnalités mais formellement transmise le
2026-09-02. Disponible pour Radar ET Radar+ (contrairement au webhook générique,
réservé Radar+ seul, falkye/notifications/webhook_channel.py) — gate au moment de
l'USAGE (falkye/notifications/crm/base.py::CrmProvider.resoudre_connexion),
jamais au stockage : même principe que Profile.webhook_url ailleurs dans le
projet.

Authentification par JETON STATIQUE fourni par le client (jeton d'application
privée HubSpot, jeton API personnel Pipedrive) — collé dans son profil FALKYE,
pas un flux OAuth2 complet. Décision d'Alexandre (2026-09-02) : OAuth2 exigerait
une page de callback web et un enregistrement d'application chez chaque
fournisseur — infrastructure que FALKYE n'a pas et qui n'est pas nécessaire pour
un push depuis le compte du client lui-même, plutôt qu'une appli listée sur un
marketplace."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from falkye.models.base import Base, utcnow


class CrmConnection(Base):
    """Une connexion CRM active pour UN profil, vers UN fournisseur (hubspot |
    pipedrive — voir registry/crm_providers.yaml). Un profil peut avoir une
    connexion par fournisseur (ex. HubSpot ET Pipedrive en parallèle, cas réel
    d'une organisation en transition d'un CRM à l'autre)."""

    __tablename__ = "crm_connections"
    __table_args__ = (
        UniqueConstraint("profile_id", "fournisseur", name="uq_crm_connection_profile_fournisseur"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), nullable=False)
    fournisseur: Mapped[str] = mapped_column(String(64), nullable=False)  # voir registry/crm_providers.yaml

    jeton_api: Mapped[str] = mapped_column(String(500), nullable=False)
    # Optionnel selon fournisseur — ex. l'id de pipeline Pipedrive à utiliser (un
    # compte Pipedrive peut avoir plusieurs pipelines) ; HubSpot n'en a pas besoin
    # (portail unique par jeton).
    identifiant_compte: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Correspondance statut de suivi FALKYE -> valeur d'étape CRM, DANS LES DEUX
    # SENS (spec : "synchroniser... dans les deux sens si possible") —
    # {statut_suivi_id: valeur_stage_crm}. JAMAIS fabriquée par défaut : les
    # étapes de pipeline HubSpot/Pipedrive sont propres au compte de CHAQUE
    # client (configurées par lui dans SON CRM), donc aucune correspondance
    # n'existe tant qu'il ne l'a pas explicitement définie (`falkye crm
    # mapper-statut`) — principe directeur #1, "jamais fabriquer une valeur".
    # Sans entrée pour un statut donné : poussé tel quel côté CRM (voir
    # falkye/notifications/crm/base.py::valeurs_a_pousser), et un changement lu
    # côté CRM sans correspondance connue est ignoré proprement plutôt que
    # deviné (falkye/crm_sync.py::sonder_statuts_crm).
    mapping_statuts: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Ajustement des noms de propriété/champ CRM ciblés par push, PAR-DESSUS le
    # mappage par défaut du fournisseur (registry/crm_providers.yaml::
    # champs_mappage). Nécessaire en pratique pour Pipedrive : contrairement à
    # HubSpot (propriétés personnalisées nommées explicitement par le client),
    # les clés de champ personnalisé Pipedrive sont des hachages opaques
    # attribués par Pipedrive à la création du champ — impossibles à deviner au
    # niveau du registre, donc ajustables ici par connexion.
    champs_mappage_override: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    actif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    profile = relationship("Profile", back_populates="connexions_crm")
