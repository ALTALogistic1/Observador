"""Tests de falkye/crm_sync.py — push (upsert, jamais un doublon) et sondage
retour (`sonder_statuts_crm`) — intégration CRM (Radar et Radar+, ajoutée le
2026-09-02). Fournisseur CRM entièrement simulé ici (aucun appel HTTP) ; voir
tests/test_hubspot_channel.py et test_pipedrive_channel.py pour la couverture
HTTP réelle par fournisseur."""
from falkye.crm_sync import pousser_notification_vers_crm, sonder_statuts_crm
from falkye.models.company import Company
from falkye.models.crm_connection import CrmConnection
from falkye.models.crm_sync_record import CrmSyncRecord
from falkye.models.notification import (
    ModeUsage,
    NiveauConfiance,
    NiveauPertinence,
    Notification,
    NotificationDelivery,
)
from falkye.models.profile import PlanTarifaire, Profile
from falkye.notifications.crm.base import CrmProvider, CrmPushResult, CrmStatutDistant
from falkye.registry.loader import CrmProviderDef


class _FakeProvider(CrmProvider):
    """Fournisseur CRM entièrement simulé — appels tracés dans .pushes plutôt
    que de vrais appels HTTP."""

    def __init__(self, provider_def, push_result=None, statut_result=None):
        super().__init__(provider_def)
        self.pushes = []
        self._push_result = push_result or CrmPushResult(succes=True, crm_object_id="obj-1")
        self._statut_result = statut_result or CrmStatutDistant(succes=True, stage_brut=None)

    def pousser(self, connection, contenu, crm_object_id):
        self.pushes.append(crm_object_id)
        return self._push_result

    def tirer_statut(self, connection, crm_object_id):
        return self._statut_result


def _hubspot_def():
    return CrmProviderDef(id="hubspot", nom="H", statut="actif", module="x", objet_crm_cible="companies")


def _registry_avec_fake_provider(monkeypatch, fake_provider, provider_id="hubspot"):
    """Registre réel (deux fournisseurs, hubspot + pipedrive), avec
    `charger_fournisseur` remplacé pour TOUTE instance de CrmProviderDef —
    seul `provider_id` retourne le fournisseur simulé, l'autre est ignoré
    (retourne None, comme un fournisseur sans module implémenté) — évite tout
    appel HTTP réel."""
    from falkye.registry.loader import get_registry

    registry = get_registry()
    monkeypatch.setattr(
        CrmProviderDef, "charger_fournisseur",
        lambda self: fake_provider if self.id == provider_id else None,
    )
    return registry


def _profile(db_session, plan=PlanTarifaire.RADAR):
    p = Profile(courriel="t@t.com", nom="T", plan=plan)
    db_session.add(p)
    db_session.flush()
    return p


def _company(db_session, nom="Entreprise Test"):
    c = Company(nom_detecte=nom, nom_detecte_normalise=nom.lower())
    db_session.add(c)
    db_session.flush()
    return c


def _connexion(db_session, profile, fournisseur="hubspot", **kwargs):
    kwargs.setdefault("actif", True)
    connexion = CrmConnection(profile_id=profile.id, fournisseur=fournisseur, jeton_api="jeton-test", **kwargs)
    db_session.add(connexion)
    profile.connexions_crm.append(connexion)
    db_session.flush()
    return connexion


def _notification(db_session, profile, company, statut_suivi_id=None, sphere="gestion_projet"):
    n = Notification(
        company_id=company.id, profile_id=profile.id, mode=ModeUsage.VEILLE_CONTINUE,
        score_confiance=50.0, niveau_confiance=NiveauConfiance.MOYEN,
        score_pertinence=60.0, niveau_pertinence=NiveauPertinence.AA,
        sphere_probable_id=sphere, justification_resumee="test", statut_suivi_id=statut_suivi_id,
    )
    n.company = company
    n.profile = profile
    db_session.add(n)
    db_session.flush()
    return n


# --- pousser_notification_vers_crm ---


def test_pousser_ignore_si_aucune_connexion_configuree(db_session, monkeypatch):
    fake = _FakeProvider(_hubspot_def())
    registry = _registry_avec_fake_provider(monkeypatch, fake)
    profile = _profile(db_session)
    company = _company(db_session)
    n = _notification(db_session, profile, company)

    pousser_notification_vers_crm(db_session, n, registry)

    assert fake.pushes == []
    assert db_session.query(CrmSyncRecord).count() == 0
    assert db_session.query(NotificationDelivery).count() == 0


def test_pousser_ignore_pour_un_profil_echo(db_session, monkeypatch):
    """Disponible pour Radar ET Radar+ seulement (contrairement au webhook
    générique, réservé Radar+ seul) — gate déjà testé en isolation dans
    tests/test_crm_base.py::test_resoudre_connexion_none_pour_echo ; ce test
    confirme que crm_sync le respecte bien en pratique, jusqu'au bout."""
    fake = _FakeProvider(_hubspot_def())
    registry = _registry_avec_fake_provider(monkeypatch, fake)
    profile = _profile(db_session, plan=PlanTarifaire.ECHO)
    company = _company(db_session)
    _connexion(db_session, profile)
    n = _notification(db_session, profile, company)

    pousser_notification_vers_crm(db_session, n, registry)

    assert fake.pushes == []
    assert db_session.query(CrmSyncRecord).count() == 0


def test_pousser_cree_un_nouvel_enregistrement_de_synchro(db_session, monkeypatch):
    fake = _FakeProvider(_hubspot_def(), push_result=CrmPushResult(succes=True, crm_object_id="obj-1"))
    registry = _registry_avec_fake_provider(monkeypatch, fake)
    profile = _profile(db_session)
    company = _company(db_session)
    _connexion(db_session, profile)
    n = _notification(db_session, profile, company, statut_suivi_id="a_joindre")

    pousser_notification_vers_crm(db_session, n, registry)
    db_session.commit()

    assert fake.pushes == [None]  # premier push, aucun id CRM connu encore
    sr = db_session.query(CrmSyncRecord).one()
    assert sr.crm_object_id == "obj-1"
    assert sr.fournisseur == "hubspot"
    assert sr.dernier_statut_pousse_id == "a_joindre"

    livraison = db_session.query(NotificationDelivery).one()
    assert livraison.channel_id == "crm_hubspot"
    assert livraison.statut == "envoyee"
    assert livraison.notification_id == n.id


def test_pousser_reutilise_le_meme_enregistrement_sans_creer_de_doublon(db_session, monkeypatch):
    fake = _FakeProvider(_hubspot_def())
    registry = _registry_avec_fake_provider(monkeypatch, fake)
    profile = _profile(db_session)
    company = _company(db_session)
    _connexion(db_session, profile)

    n1 = _notification(db_session, profile, company, statut_suivi_id="a_joindre")
    pousser_notification_vers_crm(db_session, n1, registry)
    db_session.commit()

    n2 = _notification(db_session, profile, company, statut_suivi_id="joint")
    pousser_notification_vers_crm(db_session, n2, registry)
    db_session.commit()

    assert db_session.query(CrmSyncRecord).count() == 1  # jamais un doublon pour la même entreprise
    sr = db_session.query(CrmSyncRecord).one()
    assert sr.dernier_statut_pousse_id == "joint"
    assert fake.pushes == [None, "obj-1"]  # le 2e push connaît déjà l'id CRM (upsert)
    assert db_session.query(NotificationDelivery).count() == 2


def test_pousser_trace_un_echec_sans_creer_d_enregistrement_de_synchro(db_session, monkeypatch):
    fake = _FakeProvider(_hubspot_def(), push_result=CrmPushResult(succes=False, erreur="401 unauthorized"))
    registry = _registry_avec_fake_provider(monkeypatch, fake)
    profile = _profile(db_session)
    company = _company(db_session)
    _connexion(db_session, profile)
    n = _notification(db_session, profile, company)

    pousser_notification_vers_crm(db_session, n, registry)
    db_session.commit()

    assert db_session.query(CrmSyncRecord).count() == 0
    livraison = db_session.query(NotificationDelivery).one()
    assert livraison.statut == "echec"
    assert livraison.erreur == "401 unauthorized"


# --- sonder_statuts_crm ---


def test_sonder_ignore_si_aucun_changement_de_stage(db_session, monkeypatch):
    fake = _FakeProvider(_hubspot_def(), statut_result=CrmStatutDistant(succes=True, stage_brut="Étape 1"))
    registry = _registry_avec_fake_provider(monkeypatch, fake)
    profile = _profile(db_session)
    company = _company(db_session)
    _connexion(db_session, profile, mapping_statuts={"a_joindre": "Étape 1"})
    db_session.add(
        CrmSyncRecord(
            profile_id=profile.id, company_id=company.id, fournisseur="hubspot",
            crm_object_id="obj-1", dernier_stage_crm_connu="Étape 1",
        )
    )
    db_session.flush()

    assert sonder_statuts_crm(db_session, registry) == 0


def test_sonder_applique_le_nouveau_statut_si_mapping_connu(db_session, monkeypatch):
    fake = _FakeProvider(_hubspot_def(), statut_result=CrmStatutDistant(succes=True, stage_brut="Étape 2"))
    registry = _registry_avec_fake_provider(monkeypatch, fake)
    profile = _profile(db_session)
    company = _company(db_session)
    _connexion(db_session, profile, mapping_statuts={"a_joindre": "Étape 1", "joint": "Étape 2"})
    db_session.add(
        CrmSyncRecord(
            profile_id=profile.id, company_id=company.id, fournisseur="hubspot",
            crm_object_id="obj-1", dernier_stage_crm_connu="Étape 1",
        )
    )
    n = _notification(db_session, profile, company, statut_suivi_id="a_joindre")
    db_session.flush()

    nb = sonder_statuts_crm(db_session, registry)

    assert nb == 1
    assert n.statut_suivi_id == "joint"
    sr = db_session.query(CrmSyncRecord).one()
    assert sr.dernier_stage_crm_connu == "Étape 2"
    assert sr.dernier_statut_pousse_id == "joint"


def test_sonder_ignore_une_valeur_crm_sans_correspondance_connue(db_session, monkeypatch):
    """Jamais deviné — principe directeur #1, "jamais fabriquer une valeur"."""
    fake = _FakeProvider(_hubspot_def(), statut_result=CrmStatutDistant(succes=True, stage_brut="Étape inconnue"))
    registry = _registry_avec_fake_provider(monkeypatch, fake)
    profile = _profile(db_session)
    company = _company(db_session)
    _connexion(db_session, profile, mapping_statuts={"a_joindre": "Étape 1"})
    db_session.add(
        CrmSyncRecord(
            profile_id=profile.id, company_id=company.id, fournisseur="hubspot",
            crm_object_id="obj-1", dernier_stage_crm_connu="Étape 1",
        )
    )
    n = _notification(db_session, profile, company, statut_suivi_id="a_joindre")
    db_session.flush()

    nb = sonder_statuts_crm(db_session, registry)

    assert nb == 0
    assert n.statut_suivi_id == "a_joindre"  # inchangé


def test_sonder_ignore_un_echec_de_sondage(db_session, monkeypatch):
    fake = _FakeProvider(_hubspot_def(), statut_result=CrmStatutDistant(succes=False, erreur="timeout"))
    registry = _registry_avec_fake_provider(monkeypatch, fake)
    profile = _profile(db_session)
    company = _company(db_session)
    _connexion(db_session, profile)
    db_session.add(
        CrmSyncRecord(profile_id=profile.id, company_id=company.id, fournisseur="hubspot", crm_object_id="obj-1")
    )
    db_session.flush()

    assert sonder_statuts_crm(db_session, registry) == 0


def test_sonder_ignore_une_connexion_retiree_depuis_le_dernier_push(db_session, monkeypatch):
    """Une connexion peut être désactivée/retirée entre deux cycles de veille —
    le sondage doit s'arrêter proprement, pas planter."""
    fake = _FakeProvider(_hubspot_def(), statut_result=CrmStatutDistant(succes=True, stage_brut="Étape 2"))
    registry = _registry_avec_fake_provider(monkeypatch, fake)
    profile = _profile(db_session)
    company = _company(db_session)
    # Aucune connexion créée pour ce profil (retirée) — seul le CrmSyncRecord subsiste.
    db_session.add(
        CrmSyncRecord(profile_id=profile.id, company_id=company.id, fournisseur="hubspot", crm_object_id="obj-1")
    )
    db_session.flush()

    assert sonder_statuts_crm(db_session, registry) == 0
