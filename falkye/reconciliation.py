"""Ce qui arrive APRÈS l'appel — et que rien n'écoutait.

**Le défaut que ce module ferme.** Le premier envoi réel, le 2026-09-06, a été
accepté par Postmark puis refusé une seconde plus tard par la messagerie du
destinataire (`554 5.7.1 detected as Spam`, rebond dur, jamais remis en file).
FALKYE avait déjà inscrit `envoye_le` et marqué les 306 opportunités comme
incluses : elles ne seraient jamais reparties. Capturées, crues livrées, perdues,
sans aucune trace interne.

Le correctif de la réunification des chemins de livraison traitait l'échec **au
moment de l'appel** : un canal qui refuse laisse les opportunités en attente.
Celui-ci traite l'échec **après** l'appel, où la même règle doit valoir : une
remise qui échoue remet l'opportunité en attente, exactement comme un envoi
refusé.

**Consultation, pas webhook.** Le fournisseur sait pousser le verdict, mais un
webhook exige que le point d'entrée public réponde à l'instant précis où il
pousse, et une indisponibilité perdrait l'information sans que rien ne le dise —
la forme même du défaut qu'on corrige. La consultation se rejoue sans effet de
bord, n'ouvre aucune surface entrante, et son délai n'a pas de conséquence :
ce qu'elle déclenche ne sert qu'au cycle suivant, qui est justement l'endroit où
elle tourne.

**Le moteur ne connaît aucun fournisseur.** Il demande au canal ce qu'il sait
(`NotificationChannel.etat_des_livraisons`), et un canal qui ne sait rien dire
retourne un dictionnaire vide. Même discipline que le registre des sources.

**Le garde-fou, tranché par Alexandre le 2026-09-06.** Un rebond dû au filtre
antipourriel du destinataire se reproduirait à l'identique chaque semaine : les
opportunités repartent, le résumé rebondit, sans fin. Trois rebonds consécutifs
sur le même profil suspendent donc l'envoi et déclenchent une alerte — une
SUSPENSION, jamais un désabonnement, la distinction restant visible au journal
parce qu'un profil suspendu par le produit n'est pas un abonné qui a demandé à
partir. La suspension ne perd rien : les opportunités restent en attente et
repartiront à sa levée (`falkye profile reprendre-envoi`).

**Et ce n'est pas la solution.** Le vrai remède est de ne plus produire un
message que les filtres refusent. La suspension empêche seulement d'abîmer la
réputation du domaine en insistant.

**Ne rien savoir n'est pas savoir que c'est perdu.** Une remise sans verdict
reste `acceptee` et repasse au cycle suivant. La déclarer rebondie sur une
ignorance renverrait un résumé déjà lu — un défaut symétrique de celui qu'on
corrige, et plus difficile à voir.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from falkye.models.base import en_utc
from falkye.models.livraison_resume import LivraisonResume, StatutLivraison
from falkye.models.notification import Notification, PeriodicSummary
from falkye.models.profile import Profile
from falkye.notifications.base import EtatLivraison
from falkye.registry.loader import Registry, get_registry

logger = logging.getLogger(__name__)

# Postmark conserve le détail d'un message 45 jours. Au-delà, la consultation ne
# renverra plus jamais de verdict : insister ferait rejouer chaque semaine, pour
# toujours, une question dont la réponse n'existe plus. La remise passe alors en
# `indeterminee` — un aveu daté, pas un succès par défaut.
DELAI_ABANDON_JOURS = 45

# Trois rebonds consécutifs sur le même profil suspendent l'envoi (décision
# d'Alexandre du 2026-09-06). Trois plutôt que deux : un rebond isolé peut venir
# d'une indisponibilité passagère chez le destinataire; au troisième, c'est le
# message ou l'adresse.
SEUIL_SUSPENSION = 3


@dataclass
class RapportReconciliation:
    verifiees: int = 0
    confirmees: int = 0
    rebondies: int = 0
    indeterminees: int = 0
    opportunites_remises_en_attente: int = 0
    resumes_rebondis: list[str] = field(default_factory=list)
    profils_suspendus: list[str] = field(default_factory=list)

    def resume_lisible(self) -> str:
        texte = (
            f"{self.verifiees} remise(s) vérifiée(s), "
            f"{self.confirmees} confirmée(s), {self.rebondies} rebondie(s)"
        )
        if self.indeterminees:
            texte += f", {self.indeterminees} indéterminée(s)"
        if self.opportunites_remises_en_attente:
            texte += (
                f", {self.opportunites_remises_en_attente} opportunité(s) "
                "remise(s) en attente"
            )
        if self.profils_suspendus:
            texte += f", {len(self.profils_suspendus)} profil(s) suspendu(s)"
        return texte


def livraisons_a_verifier(db_session: Session) -> list[LivraisonResume]:
    """Les remises acceptées dont on ignore encore le sort, et qui portent une
    référence — sans référence, il n'y a rien à demander au fournisseur."""
    return list(
        db_session.execute(
            select(LivraisonResume).where(
                LivraisonResume.statut == StatutLivraison.ACCEPTEE,
                LivraisonResume.reference.is_not(None),
            )
        )
        .scalars()
        .all()
    )


def _remettre_en_attente(db_session: Session, summary: PeriodicSummary) -> int:
    """Défait les deux marquages posés à l'acceptation. Retourne le nombre
    d'opportunités qui repartiront au prochain résumé.

    Le `PeriodicSummary` lui-même n'est pas supprimé : il reste la trace datée
    d'une tentative qui a échoué, ce qui distingue « rien à envoyer » de
    « l'envoi n'est jamais arrivé »."""
    summary.envoye_le = None
    ids = list(summary.notification_ids or [])
    if not ids:
        return 0
    notifications = (
        db_session.execute(select(Notification).where(Notification.id.in_(ids))).scalars().all()
    )
    for notification in notifications:
        notification.inclus_dans_resume = False
    return len(notifications)


def _autre_canal_a_livre(db_session: Session, livraison: LivraisonResume) -> bool:
    """Vrai si le MÊME résumé a été livré ou est encore en vol sur un autre canal.

    Un résumé peut partir sur plusieurs canaux. Un rebond sur l'un d'eux ne veut
    pas dire que la personne n'a rien reçu : remettre les opportunités en attente
    lui vaudrait un doublon. On ne défait les marquages que si AUCUN autre canal
    ne tient encore la livraison.
    """
    autres = (
        db_session.execute(
            select(LivraisonResume).where(
                LivraisonResume.summary_id == livraison.summary_id,
                LivraisonResume.id != livraison.id,
            )
        )
        .scalars()
        .all()
    )
    return any(
        a.statut in (StatutLivraison.CONFIRMEE, StatutLivraison.ACCEPTEE) for a in autres
    )


def _suspendre_si_necessaire(profile: Profile, maintenant: datetime) -> bool:
    """Compte le rebond et suspend au seuil. Vrai si CE rebond a suspendu.

    Suspendre, pas désabonner : `desabonne_le` reste intact, parce que c'est le
    champ de l'abonné et qu'un profil suspendu par le produit n'est pas quelqu'un
    qui a demandé à partir. Un profil déjà suspendu n'est pas re-signalé — une
    alerte répétée chaque semaine cesse d'être une alerte.
    """
    profile.rebonds_consecutifs = (profile.rebonds_consecutifs or 0) + 1
    if profile.rebonds_consecutifs < SEUIL_SUSPENSION or profile.envoi_suspendu_le is not None:
        return False
    profile.envoi_suspendu_le = maintenant
    return True


def reconcilier_livraisons(
    db_session: Session, registry: Registry | None = None
) -> RapportReconciliation:
    """Demande à chaque canal ce qu'il est advenu de ses remises acceptées.

    Ne lève jamais : une panne du fournisseur pendant cette étape est une panne
    d'observation. Si elle interrompait le cycle, on perdrait les envois de la
    semaine EN PLUS de l'information sur ceux de la précédente.
    """
    registry = registry or get_registry()
    rapport = RapportReconciliation()

    par_canal: dict[str, list[LivraisonResume]] = defaultdict(list)
    for livraison in livraisons_a_verifier(db_session):
        par_canal[livraison.channel_id].append(livraison)

    maintenant = datetime.now(timezone.utc)

    for channel_id, livraisons in par_canal.items():
        channel_def = registry.notification_channels.get(channel_id)
        channel = channel_def.charger_canal() if channel_def is not None else None
        verdicts = {}
        if channel is not None:
            try:
                verdicts = channel.etat_des_livraisons([l.reference for l in livraisons])
            except Exception as exc:  # noqa: BLE001 — l'observation n'interrompt rien
                logger.warning("Vérification impossible sur le canal %s : %s", channel_id, exc)

        for livraison in livraisons:
            verdict = verdicts.get(livraison.reference)
            if verdict is None or verdict.etat == EtatLivraison.INCONNUE:
                age = maintenant - (en_utc(livraison.tentee_le) or maintenant)
                if age > timedelta(days=DELAI_ABANDON_JOURS):
                    livraison.statut = StatutLivraison.INDETERMINEE
                    livraison.verifiee_le = maintenant
                    livraison.detail = (
                        f"Aucun verdict après {DELAI_ABANDON_JOURS} jours — "
                        "hors de la fenêtre de rétention du fournisseur."
                    )
                    rapport.indeterminees += 1
                continue

            rapport.verifiees += 1
            livraison.verifiee_le = maintenant
            livraison.detail = verdict.detail

            summary = db_session.get(PeriodicSummary, livraison.summary_id)
            profile = (
                db_session.get(Profile, summary.profile_id) if summary is not None else None
            )

            if verdict.etat == EtatLivraison.CONFIRMEE:
                livraison.statut = StatutLivraison.CONFIRMEE
                rapport.confirmees += 1
                if profile is not None:
                    # « Consécutifs » : une remise qui aboutit efface l'ardoise.
                    profile.rebonds_consecutifs = 0
                continue

            livraison.statut = StatutLivraison.REBONDIE
            rapport.rebondies += 1
            if summary is None or _autre_canal_a_livre(db_session, livraison):
                continue
            rapport.opportunites_remises_en_attente += _remettre_en_attente(db_session, summary)
            rapport.resumes_rebondis.append(
                f"résumé #{summary.id} (profil #{summary.profile_id}) : "
                f"{verdict.detail or 'rebond sans détail'}"
            )
            if profile is not None and _suspendre_si_necessaire(profile, maintenant):
                rapport.profils_suspendus.append(
                    f"profil #{profile.id} suspendu après {profile.rebonds_consecutifs} "
                    f"rebond(s) consécutif(s) : {verdict.detail or 'rebond sans détail'}"
                )

    db_session.flush()
    return rapport
