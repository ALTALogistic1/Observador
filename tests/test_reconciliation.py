"""Ce que ces tests protègent : **une acceptation n'est pas une livraison**.

Le premier envoi réel (2026-09-06) a été accepté par Postmark puis refusé par la
messagerie du destinataire une seconde plus tard. FALKYE avait déjà posé
`envoye_le` et marqué 306 opportunités comme incluses — elles ne seraient jamais
reparties, et rien dans le produit n'en portait la trace.

Le piège symétrique, moins visible, a aussi ses tests ici : remettre en attente
sur une IGNORANCE renverrait un résumé déjà lu. Ne rien savoir n'est pas savoir
que c'est perdu.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from falkye.models.company import Company, StatutLegal, StatutResolution, StatutVerification
from falkye.models.journal_exploitation import EvenementExploitation
from falkye.models.livraison_resume import LivraisonResume, StatutLivraison
from falkye.models.notification import (
    ModeUsage,
    NiveauConfiance,
    NiveauPertinence,
    Notification,
    PeriodicSummary,
)
from falkye.models.profile import Profile
from falkye.notifications.base import (
    DeliveryResult,
    EtatLivraison,
    NotificationChannel,
    VerdictLivraison,
)
from falkye.reconciliation import DELAI_ABANDON_JOURS, reconcilier_livraisons
from falkye.registry.loader import NotificationChannelDef


# --- Décors ----------------------------------------------------------------


class _CanalQuiSaitDire(NotificationChannel):
    """Canal dont le fournisseur répond — le verdict est posé par le test."""

    verdicts: dict = {}
    leve: bool = False

    def envoyer(self, destinataire, contenu):
        return DeliveryResult(succes=True, reference="ref-1")

    def etat_des_livraisons(self, references):
        if type(self).leve:
            raise RuntimeError("fournisseur injoignable")
        return {r: v for r, v in type(self).verdicts.items() if r in references}


@pytest.fixture()
def canal(monkeypatch):
    _CanalQuiSaitDire.verdicts = {}
    _CanalQuiSaitDire.leve = False
    monkeypatch.setattr(
        NotificationChannelDef, "charger_canal", lambda self: _CanalQuiSaitDire(channel_def=self)
    )
    return _CanalQuiSaitDire


def _profile(db_session):
    p = Profile(courriel="alexandre@exemple.com", nom="Profil Test")
    db_session.add(p)
    db_session.flush()
    return p


def _company(db_session):
    c = Company(
        nom_detecte="Transport Bourassa",
        nom_detecte_normalise="transport bourassa",
        statut_legal=StatutLegal.IMMATRICULEE,
        statut_resolution=StatutResolution.RESOLU,
        statut_verification=StatutVerification.VERIFIE,
    )
    db_session.add(c)
    db_session.flush()
    return c


def _resume_accepte(db_session, *, channel_id="postmark", reference="ref-1", tentee_le=None):
    """L'état exact laissé par un envoi que le fournisseur a accepté :
    `envoye_le` posé, opportunités marquées incluses, remise en attente de
    verdict."""
    profile = _profile(db_session)
    notification = Notification(
        company_id=_company(db_session).id,
        profile_id=profile.id,
        mode=ModeUsage.VEILLE_CONTINUE,
        score_confiance=72.0,
        niveau_confiance=NiveauConfiance.ELEVE,
        score_pertinence=80.0,
        niveau_pertinence=NiveauPertinence.AA,
        justification_resumee="résumé de test",
        inclus_dans_resume=True,
    )
    db_session.add(notification)
    db_session.flush()

    maintenant = datetime.now(timezone.utc)
    summary = PeriodicSummary(
        profile_id=profile.id,
        periode_debut=maintenant - timedelta(days=7),
        periode_fin=maintenant,
        notification_ids=[notification.id],
        envoye_le=maintenant,
    )
    db_session.add(summary)
    db_session.flush()

    livraison = LivraisonResume(
        summary_id=summary.id,
        channel_id=channel_id,
        statut=StatutLivraison.ACCEPTEE,
        reference=reference,
    )
    if tentee_le is not None:
        livraison.tentee_le = tentee_le
    db_session.add(livraison)
    db_session.flush()
    return summary, notification, livraison


def _canal_actif(registry):
    return registry.canaux_actifs()[0].id


# --- Le défaut : cru livré, perdu ------------------------------------------


def test_un_rebond_remet_les_opportunites_en_attente(db_session, canal, registry):
    """Le test central. Sur la version d'avant, `envoye_le` restait posé et
    l'opportunité restait marquée incluse — donc perdue pour toujours."""
    summary, notification, livraison = _resume_accepte(
        db_session, channel_id=_canal_actif(registry)
    )
    canal.verdicts = {
        "ref-1": VerdictLivraison(
            etat=EtatLivraison.REBONDIE, detail="detected as Spam by spam filters"
        )
    }

    rapport = reconcilier_livraisons(db_session, registry)

    assert livraison.statut == StatutLivraison.REBONDIE
    assert summary.envoye_le is None
    assert notification.inclus_dans_resume is False
    assert rapport.rebondies == 1
    assert rapport.opportunites_remises_en_attente == 1
    assert "detected as Spam" in rapport.resumes_rebondis[0]


def test_une_livraison_confirmee_ne_defait_rien(db_session, canal, registry):
    summary, notification, livraison = _resume_accepte(
        db_session, channel_id=_canal_actif(registry)
    )
    canal.verdicts = {"ref-1": VerdictLivraison(etat=EtatLivraison.CONFIRMEE)}

    rapport = reconcilier_livraisons(db_session, registry)

    assert livraison.statut == StatutLivraison.CONFIRMEE
    assert summary.envoye_le is not None
    assert notification.inclus_dans_resume is True
    assert rapport.confirmees == 1


def test_une_livraison_confirmee_nest_pas_reexaminee_au_cycle_suivant(
    db_session, canal, registry
):
    """Sinon chaque cycle rappellerait le fournisseur sur tout l'historique — la
    facture et la lenteur croîtraient sans borne."""
    _resume_accepte(db_session, channel_id=_canal_actif(registry))
    canal.verdicts = {"ref-1": VerdictLivraison(etat=EtatLivraison.CONFIRMEE)}
    reconcilier_livraisons(db_session, registry)

    canal.verdicts = {}
    assert reconcilier_livraisons(db_session, registry).verifiees == 0


# --- Le piège symétrique : ne rien savoir ----------------------------------


def test_sans_verdict_rien_nest_defait_et_la_remise_repasse(db_session, canal, registry):
    """Le message est peut-être encore en vol. Le déclarer perdu renverrait un
    résumé que la personne a déjà lu."""
    summary, notification, livraison = _resume_accepte(
        db_session, channel_id=_canal_actif(registry)
    )
    canal.verdicts = {}

    rapport = reconcilier_livraisons(db_session, registry)

    assert livraison.statut == StatutLivraison.ACCEPTEE
    assert summary.envoye_le is not None
    assert notification.inclus_dans_resume is True
    assert rapport.rebondies == 0


def test_un_verdict_inconnu_explicite_ne_defait_rien(db_session, canal, registry):
    summary, _, livraison = _resume_accepte(db_session, channel_id=_canal_actif(registry))
    canal.verdicts = {"ref-1": VerdictLivraison(etat=EtatLivraison.INCONNUE)}

    reconcilier_livraisons(db_session, registry)

    assert livraison.statut == StatutLivraison.ACCEPTEE
    assert summary.envoye_le is not None


def test_au_dela_de_la_retention_la_remise_est_indeterminee_pas_rebondie(
    db_session, canal, registry
):
    """L'abandon est un aveu daté, jamais une conclusion : il ne remet rien en
    attente et ne marque rien comme livré."""
    vieux = datetime.now(timezone.utc) - timedelta(days=DELAI_ABANDON_JOURS + 1)
    summary, notification, livraison = _resume_accepte(
        db_session, channel_id=_canal_actif(registry), tentee_le=vieux
    )
    canal.verdicts = {}

    rapport = reconcilier_livraisons(db_session, registry)

    assert livraison.statut == StatutLivraison.INDETERMINEE
    assert summary.envoye_le is not None
    assert notification.inclus_dans_resume is True
    assert rapport.indeterminees == 1
    assert rapport.rebondies == 0


def test_une_panne_du_fournisseur_ninterrompt_pas_le_cycle(db_session, canal, registry):
    """Une panne d'observation ne doit pas coûter les envois de la semaine EN
    PLUS de l'information sur ceux de la précédente."""
    summary, _, livraison = _resume_accepte(db_session, channel_id=_canal_actif(registry))
    canal.leve = True

    rapport = reconcilier_livraisons(db_session, registry)  # ne doit pas lever

    assert livraison.statut == StatutLivraison.ACCEPTEE
    assert summary.envoye_le is not None
    assert rapport.verifiees == 0


# --- Plusieurs canaux ------------------------------------------------------


def test_un_rebond_sur_un_canal_ne_defait_rien_si_un_autre_a_livre(
    db_session, canal, registry
):
    """Sinon la personne recevrait le même résumé deux fois."""
    canal_id = _canal_actif(registry)
    summary, notification, livraison = _resume_accepte(db_session, channel_id=canal_id)
    db_session.add(
        LivraisonResume(
            summary_id=summary.id,
            channel_id="autre_canal",
            statut=StatutLivraison.CONFIRMEE,
            reference="ref-2",
        )
    )
    db_session.flush()
    canal.verdicts = {"ref-1": VerdictLivraison(etat=EtatLivraison.REBONDIE, detail="refusé")}

    rapport = reconcilier_livraisons(db_session, registry)

    assert livraison.statut == StatutLivraison.REBONDIE
    assert summary.envoye_le is not None
    assert notification.inclus_dans_resume is True
    assert rapport.opportunites_remises_en_attente == 0


# --- Un canal qui ne sait pas dire -----------------------------------------


def test_un_canal_sans_verification_laisse_la_remise_en_attente(db_session, registry):
    """Le défaut de `NotificationChannel` : ajouter un canal ne doit pas obliger
    à écrire cette méthode pour que le reste fonctionne."""

    class _Muet(NotificationChannel):
        def envoyer(self, destinataire, contenu):
            return DeliveryResult(succes=True)

    assert _Muet(channel_def=None).etat_des_livraisons(["ref-1"]) == {}


# --- Le contrat réel de Postmark -------------------------------------------
#
# Charge COPIÉE de la réponse réelle observée le 2026-09-06 sur le message
# 2847f37f-b0e7-488f-97b5-a2661ff305e9, jamais inventée : un décor inventé
# vérifierait ce qu'on imagine du fournisseur, pas ce qu'il envoie.

EVENEMENT_REBOND_REEL = {
    "Type": "Bounced",
    "ReceivedAt": "2026-09-06T17:04:21.0000000-04:00",
    "Details": {
        "Summary": (
            "smtp; 554 5.7.1 Email cannot be delivered. "
            "Reason: Email detected as Spam by spam filters."
        ),
        "BounceID": "2817714665",
    },
}


def test_le_rebond_reel_de_postmark_est_lu_comme_un_rebond():
    from falkye.notifications.postmark_channel import _verdict_depuis_evenements

    verdict = _verdict_depuis_evenements([EVENEMENT_REBOND_REEL])

    assert verdict.etat == EtatLivraison.REBONDIE
    assert "detected as Spam" in verdict.detail


def test_une_remise_confirmee_est_lue_comme_telle():
    from falkye.notifications.postmark_channel import _verdict_depuis_evenements

    verdict = _verdict_depuis_evenements(
        [{"Type": "Delivered", "Details": {"DeliveryMessage": "smtp;250 2.0.0 OK"}}]
    )

    assert verdict.etat == EtatLivraison.CONFIRMEE


def test_une_ouverture_nest_pas_un_verdict_de_remise():
    """`Opened` décrit ce que la personne a fait, pas si le message est arrivé —
    et un message remis peut n'être jamais ouvert."""
    from falkye.notifications.postmark_channel import _verdict_depuis_evenements

    assert _verdict_depuis_evenements([{"Type": "Opened", "Details": {}}]) is None


def test_aucun_evenement_ne_conclut_rien():
    from falkye.notifications.postmark_channel import _verdict_depuis_evenements

    assert _verdict_depuis_evenements([]) is None


# --- La trace posée à l'envoi ----------------------------------------------


def test_un_envoi_accepte_ouvre_une_remise_a_verifier(db_session, canal, registry, monkeypatch):
    """Sans cette ligne, la réconciliation n'aurait rien à interroger."""
    from falkye.notifications.base import FORME_RESUME
    from falkye.notifications.livraison import livrer

    profile = _profile(db_session)
    maintenant = datetime.now(timezone.utc)
    summary = PeriodicSummary(
        profile_id=profile.id,
        periode_debut=maintenant - timedelta(days=7),
        periode_fin=maintenant,
        notification_ids=[],
    )
    db_session.add(summary)
    db_session.flush()

    from falkye.notifications.base import NotificationContent

    livrer(
        db_session,
        profile,
        NotificationContent(sujet="s", corps_texte="c"),
        registry,
        FORME_RESUME,
        summary=summary,
    )

    lignes = (
        db_session.execute(
            select(LivraisonResume).where(LivraisonResume.summary_id == summary.id)
        )
        .scalars()
        .all()
    )
    assert [l.reference for l in lignes] == ["ref-1"]
    assert lignes[0].statut == StatutLivraison.ACCEPTEE


def test_un_envoi_refuse_nouvre_aucune_remise_a_verifier(db_session, registry, monkeypatch):
    """Un refus au moment de l'appel est déjà tranché — le revérifier chaque
    semaine interrogerait le fournisseur sur un message qu'il n'a jamais eu."""
    from falkye.notifications.base import FORME_RESUME, NotificationContent
    from falkye.notifications.livraison import livrer

    class _Refuse(NotificationChannel):
        def envoyer(self, destinataire, contenu):
            return DeliveryResult(succes=False, erreur="jeton invalide")

    monkeypatch.setattr(
        NotificationChannelDef, "charger_canal", lambda self: _Refuse(channel_def=self)
    )

    profile = _profile(db_session)
    maintenant = datetime.now(timezone.utc)
    summary = PeriodicSummary(
        profile_id=profile.id,
        periode_debut=maintenant - timedelta(days=7),
        periode_fin=maintenant,
        notification_ids=[],
    )
    db_session.add(summary)
    db_session.flush()

    livrer(
        db_session,
        profile,
        NotificationContent(sujet="s", corps_texte="c"),
        registry,
        FORME_RESUME,
        summary=summary,
    )

    assert (
        db_session.execute(
            select(LivraisonResume).where(LivraisonResume.summary_id == summary.id)
        )
        .scalars()
        .all()
        == []
    )


# --- Le branchement dans le cycle ------------------------------------------


def test_le_cycle_reconcilie_avant_de_generer(db_session, monkeypatch, tmp_path):
    """L'ordre est le sujet : une opportunité reprise doit repartir DANS ce
    cycle-ci. Si la réconciliation venait après, un refus coûterait deux
    semaines au lieu d'une."""
    import falkye.cycle
    import falkye.db
    import falkye.engine
    import falkye.summary

    ordre = []

    monkeypatch.setattr(falkye.db, "get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    monkeypatch.setenv("FALKYE_JOURNAL_REPLI", str(tmp_path / "repli.jsonl"))
    monkeypatch.setattr(
        falkye.engine, "run_veille_continue", lambda **kw: type("S", (), {"nb_notifications_creees": 0})()
    )

    from falkye.reconciliation import RapportReconciliation

    def _reconcilier(session, reg=None):
        ordre.append("reconciliation")
        return RapportReconciliation(
            rebondies=1,
            opportunites_remises_en_attente=3,
            resumes_rebondis=["résumé #1 (profil #1) : refusé"],
        )

    monkeypatch.setattr(falkye.reconciliation, "reconcilier_livraisons", _reconcilier)

    def _resume(session, profile):
        ordre.append("resume")
        return type("R", (), {"envoye_le": "2026-09-06", "notification_ids": []})()

    monkeypatch.setattr(falkye.summary, "generer_et_envoyer_resume", _resume)
    _profile(db_session)

    rapport = falkye.cycle.executer_cycle()

    assert ordre == ["reconciliation", "resume"]
    assert rapport.remises_rebondies == 1
    assert rapport.opportunites_remises_en_attente == 3
    assert "1 remise(s) rebondie(s)" in rapport.resume_lisible()

    from falkye.models.journal_exploitation import JournalExploitation

    evenements = [
        e.evenement
        for e in db_session.execute(select(JournalExploitation)).scalars()
    ]
    assert EvenementExploitation.LIVRAISON_REBONDIE in evenements
