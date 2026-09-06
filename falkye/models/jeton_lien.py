"""Jeton de lien — l'autorisation d'UN geste précis, depuis un courriel.

Le tableau de bord exige une session authentifiée en ligne de commande. Un lien
cliqué dans un courriel n'en a aucune : il faut donc porter l'autorisation dans
l'URL elle-même. C'est ce que fait ce jeton, et c'est le mécanisme commun au
désabonnement (RFC 8058) et à la rétroaction « pas pertinent ».

**Le jeton n'est PAS stocké.** Seule son empreinte SHA-256 l'est. Une copie de
la base ne rend donc aucun lien utilisable — la valeur en clair n'existe que
dans le courriel déjà parti. La vérification hache ce qui est présenté et
compare, ce qui ne coûte rien de plus qu'une recherche par clé.

**Un jeton n'autorise qu'un geste, sur une cible.** Pas de session, pas de
droits, aucune lecture de données : `desabonnement` coupe l'envoi pour un
profil, `pas_pertinent` marque UNE notification. Un jeton volé au passage ne
donne accès à rien d'autre — c'est la portée qui protège, pas le secret seul.

**Durée de vie.** Aucune expiration. Un lien de désabonnement doit rester
valable aussi longtemps que le courriel reste dans une boîte de réception —
un désabonnement qui échoue parce que le lien a expiré est une plainte pour
pourriel, ce qui coûte infiniment plus cher que la fenêtre laissée ouverte.
Le jeton de rétroaction suit la même règle, par cohérence : une opinion tardive
sur un prospect reste une opinion utile.
"""
from __future__ import annotations

import enum
import hashlib
import secrets
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from falkye.models.base import Base, utcnow


class ActionJeton(str, enum.Enum):
    DESABONNEMENT = "desabonnement"
    PAS_PERTINENT = "pas_pertinent"


def engendrer_jeton() -> str:
    """Valeur en clair, à mettre dans l'URL et nulle part ailleurs."""
    return secrets.token_urlsafe(32)


def empreinte(jeton: str) -> str:
    return hashlib.sha256(jeton.encode("utf-8")).hexdigest()


class JetonLien(Base):
    __tablename__ = "jetons_lien"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # L'empreinte, jamais le jeton. Indexée et unique : c'est la clé de
    # recherche au moment où un lien est suivi.
    jeton_empreinte: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    action: Mapped[ActionJeton] = mapped_column(Enum(ActionJeton, native_enum=False), nullable=False)

    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), nullable=False)
    # Renseigné pour `pas_pertinent` seulement — c'est la notification visée.
    notification_id: Mapped[int | None] = mapped_column(ForeignKey("notifications.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    # Date du PREMIER usage. Un second clic ne fait rien de plus, mais ne se
    # plaint pas non plus : un désabonnement redemandé confirme, il n'échoue
    # pas. Voir falkye/liens.py.
    utilise_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
