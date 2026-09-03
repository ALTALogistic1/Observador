"""Client cible ("qui") — spec section 8bis (2026-09-03), nouvelle dimension
distincte de la sphère de besoin ("quoi").

Même principe d'extensibilité que `falkye/models/sphere.py::Sphere` : table
alimentée au démarrage depuis `registry/clients_cibles.yaml`
(`falkye.db.seed_clients_cibles_from_registry`), extensible en base
(`est_personnalisee=True`) sans migration.

JAMAIS dérivé du regroupement grossier de secteurs REQ
(`registry/secteurs_grossiers.yaml`) — vérifié contre le vrai miroir REQ
(2,7M lignes réelles, 2026-09-03) que les grands organismes publics/
institutionnels (commissions scolaires, sociétés de transport) n'y
apparaissent presque jamais comme entités elles-mêmes (seuls leurs syndicats/
fondations satellites y figurent), et que le peu qui y apparaît produit soit
un faux ami (ex. "transport" matche autant le transport routier privé que le
transport en commun public), soit rien dans les 11 catégories existantes,
toutes bâties sur une taxonomie commerciale privée. Un registre curé
indépendant est donc nécessaire, avec sa propre catégorie institutionnelle/
publique — voir registry/clients_cibles.yaml.

`aucune_restriction` (id réservé) est un membre RÉEL du catalogue, pas un
NULL ni une absence de lien — une déclaration POSITIVE et distincte de
"correspondance non trouvée" (voir falkye/assistance_client_cible_ia.py :
deux sentinelles différentes, jamais confondues). "Aucun lien
ProfileNeedClientCible" = besoin pas encore configuré pour le "qui" ; "un
lien pointant vers aucune_restriction" = déclaré explicitement horizontal."""
from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from falkye.models.base import Base

ID_AUCUNE_RESTRICTION = "aucune_restriction"


class ClientCible(Base):
    __tablename__ = "clients_cibles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    nom: Mapped[str] = mapped_column(String(200), nullable=False)
    est_personnalisee: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    proposee_par: Mapped[str | None] = mapped_column(String(200), nullable=True)
