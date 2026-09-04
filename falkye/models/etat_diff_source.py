"""État persisté du moteur de diff générique (Chantier 1, spec section 8bis —
audit du 2026-09-03, faille E : « la conservation d'état des sources
instantanées »).

Pour une source de type `instantane` (aucune date d'événement fiable par
ligne — RACJ, établissements alimentaires Montréal, et — déjà en place sous
une forme partielle et bespoke à généraliser — REQ, Corporations Canada,
licences municipales), un signal N'EXISTE PAS dans la donnée : il naît de la
comparaison entre l'état actuel et le dernier état connu. Perdre cet état
entre deux exécutions perd des événements DÉFINITIVEMENT (faille E, coût
irrécupérable, pas seulement croissant) — d'où deux tables dédiées, séparées
du reste du schéma, pour que cette conservation ne dépende d'aucun mécanisme
bespoke par source.

`EtatLigneSource` — une ligne par (source, clé naturelle) : l'état COURANT
uniquement (pas un historique de copies complètes — le diff se fait toujours
contre la dernière exécution RÉUSSIE, voir falkye/diff_engine.py). Supprimée
quand la ligne source disparaît (une disparition puis une réapparition plus
tard redevient légitimement une nouvelle apparition, jamais un cas spécial).

`EtatSchemaSource` — une ligne par source : la liste de colonnes vue à la
dernière exécution réussie, pour détecter un changement de schéma (colonne
retirée/renommée/type modifié) avant même de comparer le contenu — spec du
chantier : « un schéma modifié déclenche la quarantaine quel que soit le
volume »."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from falkye.models.base import Base, utcnow


class EtatLigneSource(Base):
    __tablename__ = "etat_ligne_source"
    __table_args__ = (UniqueConstraint("source_id", "cle_naturelle", name="uq_etat_ligne_source"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Composite si plusieurs champs (ex. nom_normalise + "|" + adresse_normalisee
    # pour Nouvelle-Écosse, qui n'a aucune clé stable — voir SourceDef.cle_naturelle
    # dans registry/sources.yaml, JAMAIS devinée ici) — toujours une chaîne, la
    # composition reste la responsabilité du connecteur/appelant.
    cle_naturelle: Mapped[str] = mapped_column(String(600), nullable=False)

    # Empreinte des champs PERTINENTS uniquement (registry/champs_pertinents.yaml,
    # ou à défaut la liste déclarée au registre — voir falkye/diff_engine.py) —
    # jamais la ligne entière : un changement cosmétique hors de cette liste
    # (espace en trop, colonne inutilisée, réordonnancement) ne doit jamais
    # produire une fausse modification.
    empreinte: Mapped[str] = mapped_column(String(64), nullable=False)

    # Valeurs des champs pertinents au dernier état connu — nécessaire pour
    # rapporter QUELS champs ont changé lors d'une modification (spec : "la
    # hausse de Capacite du RACJ est un signal d'agrandissement; un changement
    # de code postal formaté différemment n'est rien" — la liste des champs
    # changés doit être disponible pour cette distinction en aval).
    donnees_normalisees: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    premiere_apparition: Mapped[datetime] = mapped_column(default=utcnow)
    derniere_observation: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class EtatSchemaSource(Base):
    __tablename__ = "etat_schema_source"

    source_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    colonnes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    mis_a_jour_le: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
