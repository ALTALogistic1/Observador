"""La trace d'une remise de résumé — et la seule chose qui distingue
« accepté » de « livré ».

**Ce que ce modèle existe pour empêcher.** Le 2026-09-06, le premier envoi réel
a été accepté par le fournisseur (HTTP 200, `ErrorCode 0`), puis refusé une
seconde plus tard par la messagerie du destinataire :

    554 5.7.1 Email cannot be delivered. Reason: Email detected as Spam
    Type: SpamNotification — no further attempts will be made

FALKYE a inscrit `PeriodicSummary.envoye_le` et marqué les 306 opportunités
comme incluses. Elles ne seraient jamais reparties. Capturées, crues livrées,
perdues — sans aucune trace interne. Le seul endroit où la vérité existait était
l'API du fournisseur, que rien n'interrogeait.

**La distinction que porte `statut`.** Une acceptation n'est pas une livraison.
Le fournisseur dit « je prends la charge »; la messagerie du destinataire dit,
plus tard, si elle l'a prise. Entre les deux il y a un délai que rien ne borne,
et c'est pour ça qu'il faut une ligne persistée plutôt qu'une valeur en mémoire :
le processus qui a envoyé est terminé depuis longtemps quand la réponse arrive.

**Pourquoi une table plutôt qu'une colonne sur `PeriodicSummary`.** Un résumé
peut partir sur plusieurs canaux, et chacun a sa propre réponse. Une colonne
obligerait à choisir laquelle compte; une ligne par canal ne le demande pas.
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from falkye.models.base import Base, utcnow


class StatutLivraison(str, enum.Enum):
    # Le fournisseur a pris la charge. Ce n'est PAS une livraison — c'est
    # l'état de départ de toute remise, et celui qu'il faut réconcilier.
    ACCEPTEE = "acceptee"
    # Le fournisseur a confirmé la remise au destinataire.
    CONFIRMEE = "confirmee"
    # Refusée par le destinataire APRÈS acceptation. Les opportunités du résumé
    # repartent en attente (falkye/reconciliation.py).
    REBONDIE = "rebondie"
    # Le fournisseur ne sait plus dire — au-delà de sa fenêtre de rétention.
    # Distinct de REBONDIE : ne rien savoir n'est pas savoir que c'est perdu, et
    # remettre en attente sur une ignorance renverrait des résumés déjà lus.
    INDETERMINEE = "indeterminee"


class LivraisonResume(Base):
    __tablename__ = "livraisons_resume"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    summary_id: Mapped[int] = mapped_column(ForeignKey("periodic_summaries.id"), nullable=False)
    channel_id: Mapped[str] = mapped_column(String(64), nullable=False)
    statut: Mapped[StatutLivraison] = mapped_column(
        Enum(StatutLivraison, native_enum=False), nullable=False, default=StatutLivraison.ACCEPTEE
    )
    # L'identifiant du message CHEZ le fournisseur — la seule clé qui permet de
    # lui redemander plus tard ce qu'il est advenu de cet envoi précis. Sans
    # elle, la réconciliation n'a rien à interroger.
    reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tentee_le: Mapped[datetime] = mapped_column(default=utcnow)
    verifiee_le: Mapped[datetime | None] = mapped_column(nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    summary = relationship("PeriodicSummary")
