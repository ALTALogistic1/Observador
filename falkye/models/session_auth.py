"""Session d'authentification réelle — falkye/auth.py, ajoutée le 2026-09-02
(prérequis avant de vendre les rôles/sous-comptes Radar+ comme une vraie
séparation, voir falkye/models/sous_compte.py pour le contexte complet).

Créée par `falkye auth login`, résolue à chaque commande "portail" (dashboard,
crm, souscompte, billing, ponderation, profile set-webhook — voir falkye/
cli.py::_identite_courante). Le jeton BRUT ne vit QUE dans le fichier local du
principal (~/.falkye/session, mode 0600) — seul son HASH est stocké ici, même
principe qu'un mot de passe (falkye/auth.py::hacher_jeton) : une fuite de la
base ne permet pas de rejouer une session active."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from falkye.models.base import Base, utcnow


class SessionAuth(Base):
    __tablename__ = "sessions_auth"

    id: Mapped[int] = mapped_column(primary_key=True)

    # "profile" (propriétaire du profil) | "sous_compte" — voir
    # falkye/auth.py::Principal. Pas une ForeignKey unique vers une seule
    # table : le principal peut être l'un ou l'autre, résolu par type +
    # principal_id (même principe que Notification.signal_type_id, qui
    # référence le registre plutôt qu'une FK stricte).
    type_principal: Mapped[str] = mapped_column(String(20), nullable=False)
    principal_id: Mapped[int] = mapped_column(nullable=False)

    jeton_hash: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)

    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    # NULL = jamais révoquée explicitement (peut quand même être expirée,
    # voir expires_at) — falkye auth logout la renseigne plutôt que de
    # supprimer la ligne, pour garder une trace (falkye auth login/logout).
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)
