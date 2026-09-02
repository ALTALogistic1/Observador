"""Tests des modèles de premier contact contextuels (falkye/premier_contact.py)
— spec section 4bis. Fixtures minimales, aucune donnée de prospect réelle
(principe directeur #1)."""
from datetime import datetime, timezone

from falkye.models.company import Company
from falkye.models.notification import ModeUsage, NiveauConfiance, Notification, NotificationSignal
from falkye.models.signal import Signal
from falkye.premier_contact import generer_amorce


def _company(nom="Entreprise Test Inc."):
    return Company(nom_detecte=nom, nom_detecte_normalise=nom.lower())


def _notification_avec_signal(company, signal_type_id, champs=None, valeur_associee=None, titre=None, sig_id=1):
    signal = Signal(
        id=sig_id,
        company_id=1,
        source_id="test_source",
        signal_type_id=signal_type_id,
        source_ref=f"ref-{sig_id}",
        detected_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
        valeur_associee=valeur_associee,
        titre_ou_description=titre,
        champs=champs or {},
    )
    n = Notification(
        company_id=1,
        profile_id=1,
        mode=ModeUsage.VEILLE_CONTINUE,
        score_confiance=70.0,
        niveau_confiance=NiveauConfiance.ELEVE,
        justification_resumee="test",
    )
    n.company = company
    n.signaux_contributifs = [NotificationSignal(signal=signal, justification="test")]
    return n


def test_amorce_appel_offres_mentionne_valeur_et_donneur_ordre():
    company = _company()
    n = _notification_avec_signal(
        company, "appel_offres", champs={"donneur_ordre": "Ville de Montréal"}, valeur_associee=250000.0
    )
    amorce = generer_amorce(n)
    assert "250 000" in amorce
    assert "Ville de Montréal" in amorce
    assert company.nom_detecte in amorce


def test_amorce_appel_offres_degrade_sans_donneur_ordre():
    company = _company()
    n = _notification_avec_signal(company, "appel_offres", champs={}, valeur_associee=50000.0)
    amorce = generer_amorce(n)
    assert company.nom_detecte in amorce
    assert "50 000" in amorce


def test_amorce_financement_mentionne_programme_et_montant():
    company = _company()
    n = _notification_avec_signal(
        company, "financement_expansion", champs={"programme": "Investissement Québec"}, valeur_associee=100000.0
    )
    amorce = generer_amorce(n)
    assert "Investissement Québec" in amorce
    assert "100 000" in amorce


def test_amorce_recrutement_mentionne_le_titre_du_poste():
    company = _company()
    n = _notification_avec_signal(company, "recrutement_massif", titre="Chef de projet — implantation ERP")
    amorce = generer_amorce(n)
    assert "Chef de projet" in amorce


def test_amorce_registre_corporatif_nouvel_etablissement_mentionne_ville_et_date():
    company = _company()
    company.ville = "Sherbrooke"
    n = _notification_avec_signal(
        company, "registre_corporatif", champs={"type_changement": "nouvel_etablissement_secondaire"}
    )
    amorce = generer_amorce(n)
    assert "Sherbrooke" in amorce
    assert "2026-08-15" in amorce


def test_amorce_classement_croissance_mentionne_le_rang():
    company = _company()
    n = _notification_avec_signal(
        company, "classement_croissance", champs={"rang": 42, "categorie": "Deloitte Technology Fast 50"}
    )
    amorce = generer_amorce(n)
    assert "42" in amorce
    assert "Deloitte Technology Fast 50" in amorce


def test_amorce_type_inconnu_degrade_vers_message_generique():
    company = _company()
    n = _notification_avec_signal(company, "type_futur_inconnu", champs={})
    amorce = generer_amorce(n)
    assert company.nom_detecte in amorce


def test_amorce_sans_signal_contributif_degrade_vers_message_generique():
    company = _company()
    n = Notification(
        company_id=1,
        profile_id=1,
        mode=ModeUsage.VEILLE_CONTINUE,
        score_confiance=70.0,
        niveau_confiance=NiveauConfiance.ELEVE,
        justification_resumee="test",
    )
    n.company = company
    n.signaux_contributifs = []
    amorce = generer_amorce(n)
    assert company.nom_detecte in amorce


def test_amorce_choisit_le_signal_le_plus_fort_parmi_plusieurs():
    """Un signal EIMT (fort par nature) doit dominer un signal de classement au
    rang faible — vérifié indirectement : l'amorce doit référencer le
    recrutement, pas le classement."""
    company = _company()
    signal_eimt = Signal(
        id=1, company_id=1, source_id="eimt", signal_type_id="recrutement_massif",
        source_ref="ref-1", detected_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
        valeur_associee=8.0, titre_ou_description="Postes EIMT", champs={},
    )
    signal_classement = Signal(
        id=2, company_id=1, source_id="deloitte_fast50", signal_type_id="classement_croissance",
        source_ref="ref-2", detected_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
        champs={"rang": 999},
    )
    n = Notification(
        company_id=1, profile_id=1, mode=ModeUsage.VEILLE_CONTINUE,
        score_confiance=70.0, niveau_confiance=NiveauConfiance.ELEVE, justification_resumee="test",
    )
    n.company = company
    n.signaux_contributifs = [
        NotificationSignal(signal=signal_eimt, justification="test"),
        NotificationSignal(signal=signal_classement, justification="test"),
    ]
    amorce = generer_amorce(n)
    assert "Postes EIMT" in amorce
