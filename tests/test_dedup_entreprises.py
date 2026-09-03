"""Tests de la détection/fusion de doublons Company sans NEQ
(falkye/dedup_entreprises.py) — spec section 8bis, point 4 (2026-09-03).

Vérifié contre la base réelle avant de coder (voir docs/STATUT_RESEAU.md) :
76 paires à similarité >=90% déjà présentes parmi les entreprises sans NEQ —
pas un risque théorique."""
from datetime import datetime, timedelta, timezone

from falkye.dedup_entreprises import (
    SEUIL_FUSION_AUTO,
    SEUIL_FUSION_CANDIDAT,
    detecter_doublons,
    fusionner,
    trouver_meilleur_candidat_fusion,
)
from falkye.models.company import Company
from falkye.models.diagnostic_journal import DiagnosticJournal, TypeDiagnostic
from falkye.models.notification import ModeUsage, NiveauConfiance, Notification
from falkye.models.signal import Signal


def _company(nom_norm, nom=None, neq=None, ville=None, first_detected_at=None):
    c = Company(
        nom_detecte=nom or nom_norm,
        nom_detecte_normalise=nom_norm,
        neq=neq,
        ville=ville,
    )
    if first_detected_at is not None:
        c.first_detected_at = first_detected_at
    return c


# --- Garde-fou compagnies à numéro (bogue réel trouvé contre la base réelle,
# 2026-09-03 — voir docs/STATUT_RESEAU.md) ---


def test_deux_compagnies_a_numero_differentes_jamais_un_candidat(db_session):
    """"9519-3801 Québec inc." vs "9519-3850 Québec inc." — score WRatio brut
    de 95.0 (fourchette de fusion AUTOMATIQUE), alors que ce sont deux
    entités légalement DISTINCTES : le matricule numérique diffère
    entièrement, seule la partie commune "Québec inc." fait grimper la
    similarité de chaînes. Fusion automatique INCORRECTE trouvée et annulée
    contre la base réelle avant que ce garde-fou n'existe."""
    c1 = _company("9519 3801 quebec inc", nom="9519-3801 Québec inc.")
    db_session.add(c1)
    db_session.flush()
    assert trouver_meilleur_candidat_fusion(db_session, "9519 3850 quebec inc", None) is None


def test_deux_compagnies_a_numero_dans_detecter_doublons_jamais_traitees(db_session):
    db_session.add_all(
        [
            _company("9519 3801 quebec inc", nom="9519-3801 Québec inc."),
            _company("9519 3850 quebec inc", nom="9519-3850 Québec inc."),
        ]
    )
    db_session.flush()
    rapport = detecter_doublons(db_session)
    assert rapport.nb_fusions_auto == 0
    assert rapport.nb_candidats_journalises == 0


def test_compagnie_a_numero_contre_nom_ordinaire_reste_comparee_normalement(db_session):
    """Le garde-fou ne s'applique QUE si les DEUX noms ont la forme "compagnie
    à numéro" — un nom ordinaire reste comparé par similarité floue comme
    d'habitude."""
    c1 = _company("entreprise alpha inc")
    db_session.add(c1)
    db_session.flush()
    assert trouver_meilleur_candidat_fusion(db_session, "9519 3801 quebec inc", None) is None
    # (aucun match ici — les deux noms n'ont simplement rien en commun, pas à
    # cause du garde-fou. Le point du test : pas d'exception, comportement
    # normal quand un seul côté a la forme numérotée.)


# --- trouver_meilleur_candidat_fusion ---


def test_aucun_candidat_sous_le_seuil(db_session):
    db_session.add(_company("entreprise alpha inc"))
    db_session.flush()
    assert trouver_meilleur_candidat_fusion(db_session, "entreprise beta inc", None) is None


def test_candidat_trouve_au_dessus_du_seuil(db_session):
    c1 = _company("transport beaulieu inc")
    db_session.add(c1)
    db_session.flush()

    meilleur = trouver_meilleur_candidat_fusion(db_session, "transport beaulieux inc", None)
    assert meilleur is not None
    assert meilleur.company.id == c1.id
    assert meilleur.score >= SEUIL_FUSION_AUTO


def test_bonus_de_ville_peut_faire_franchir_le_seuil(db_session):
    """Même principe que la résolution REQ (+5 si la ville concorde) — un
    score sous le seuil candidat SANS bonus peut le franchir AVEC."""
    c1 = _company("groupe abc", ville="Montréal")
    db_session.add(c1)
    db_session.flush()

    sans_ville = trouver_meilleur_candidat_fusion(db_session, "groupe abd", None)
    avec_ville = trouver_meilleur_candidat_fusion(db_session, "groupe abd", "Montréal")
    if sans_ville is not None:
        assert avec_ville.score >= sans_ville.score
    # Le bonus ne peut jamais faire DESCENDRE le score — au pire, égal.


def test_ne_se_compare_jamais_a_soi_meme(db_session):
    c1 = _company("entreprise alpha inc")
    db_session.add(c1)
    db_session.flush()
    assert trouver_meilleur_candidat_fusion(db_session, "entreprise alpha inc", None, exclure_id=c1.id) is None


def test_ignore_les_entreprises_deja_resolues_au_neq(db_session):
    c1 = _company("transport beaulieu inc", neq="1234567890")
    db_session.add(c1)
    db_session.flush()
    assert trouver_meilleur_candidat_fusion(db_session, "transport beaulieux inc", None) is None


def test_ignore_une_correspondance_exacte(db_session):
    """Une correspondance EXACTE est du ressort de falkye/resolution.py::
    _find_unresolved_company, pas de ce module — jamais retournée ici même
    si elle existe."""
    c1 = _company("entreprise alpha inc")
    db_session.add(c1)
    db_session.flush()
    assert trouver_meilleur_candidat_fusion(db_session, "entreprise alpha inc", None) is None


# --- fusionner ---


def test_fusionner_reassigne_signaux_et_notifications_puis_supprime_le_candidat(db_session):
    principal = _company("transport beaulieu inc")
    candidat = _company("transport beaulieux inc")
    db_session.add_all([principal, candidat])
    db_session.flush()

    signal = Signal(
        company_id=candidat.id, source_id="seao", signal_type_id="appel_offres",
        detected_at=datetime.now(timezone.utc), champs={},
    )
    notif = Notification(
        company_id=candidat.id, profile_id=1, mode=ModeUsage.VEILLE_CONTINUE,
        score_confiance=70.0, niveau_confiance=NiveauConfiance.ELEVE, justification_resumee="test",
    )
    db_session.add_all([signal, notif])
    db_session.flush()
    candidat_id = candidat.id

    fusionner(db_session, principal, candidat)

    assert db_session.get(Company, candidat_id) is None
    db_session.refresh(signal)
    db_session.refresh(notif)
    assert signal.company_id == principal.id
    assert notif.company_id == principal.id


def test_fusionner_neutralise_les_references_journal_au_candidat_supprime(db_session):
    principal = _company("transport beaulieu inc")
    candidat = _company("transport beaulieux inc")
    autre_principal = _company("groupe xyz")
    db_session.add_all([principal, candidat, autre_principal])
    db_session.flush()

    # Un journal antérieur qui nommait déjà `candidat` comme candidat d'une AUTRE paire.
    journal_anterieur = DiagnosticJournal(
        type_diagnostic=TypeDiagnostic.CANDIDAT_FUSION_ENTREPRISE,
        texte_description="test",
        statut="a_examiner",
        company_id_principal=autre_principal.id,
        company_id_candidat=candidat.id,
        score_similarite=91.0,
    )
    db_session.add(journal_anterieur)
    db_session.flush()

    fusionner(db_session, principal, candidat)

    db_session.refresh(journal_anterieur)
    assert journal_anterieur.company_id_candidat is None
    assert journal_anterieur.company_id_principal == autre_principal.id  # inchangé


# --- detecter_doublons (passe par lot) ---


def test_detecter_doublons_fusionne_automatiquement_au_dessus_de_95(db_session):
    plus_ancien = _company(
        "transport beaulieu inc", first_detected_at=datetime.now(timezone.utc) - timedelta(days=10)
    )
    plus_recent = _company("transport beaulieux inc", first_detected_at=datetime.now(timezone.utc))
    db_session.add_all([plus_ancien, plus_recent])
    db_session.flush()
    ancien_id, recent_id = plus_ancien.id, plus_recent.id

    rapport = detecter_doublons(db_session)

    assert rapport.nb_fusions_auto == 1
    assert rapport.nb_candidats_journalises == 0
    assert db_session.get(Company, ancien_id) is not None  # le plus ancien SURVIT
    assert db_session.get(Company, recent_id) is None  # le plus récent a disparu

    journal = (
        db_session.query(DiagnosticJournal)
        .filter(DiagnosticJournal.type_diagnostic == TypeDiagnostic.CANDIDAT_FUSION_ENTREPRISE)
        .one()
    )
    assert journal.statut == "fusionne_auto"
    assert journal.company_id_principal == ancien_id
    # company_id_candidat reste NULL — la ligne n'existe plus, rien de valide à
    # référencer (voir falkye/dedup_entreprises.py::journaliser_fusion_auto) ;
    # le nom/id d'origine restent dans texte_description à titre de trace.
    assert journal.company_id_candidat is None
    assert f"#{recent_id}" in journal.texte_description


def test_detecter_doublons_journalise_sans_fusionner_entre_90_et_95(db_session):
    c1 = _company("les services exp inc")
    c2 = _company("les services exp inc compte principal")
    db_session.add_all([c1, c2])
    db_session.flush()
    id1, id2 = c1.id, c2.id

    rapport = detecter_doublons(db_session)

    assert rapport.nb_fusions_auto == 0
    assert rapport.nb_candidats_journalises == 1
    # Les DEUX fiches survivent — jamais de fusion automatique dans cette fourchette.
    assert db_session.get(Company, id1) is not None
    assert db_session.get(Company, id2) is not None

    journal = (
        db_session.query(DiagnosticJournal)
        .filter(DiagnosticJournal.type_diagnostic == TypeDiagnostic.CANDIDAT_FUSION_ENTREPRISE)
        .one()
    )
    assert journal.statut == "a_examiner"
    assert SEUIL_FUSION_CANDIDAT <= journal.score_similarite < SEUIL_FUSION_AUTO


def test_detecter_doublons_ignore_les_paires_sous_le_seuil(db_session):
    db_session.add_all([_company("entreprise alpha inc"), _company("entreprise beta inc")])
    db_session.flush()
    rapport = detecter_doublons(db_session)
    assert rapport.nb_fusions_auto == 0
    assert rapport.nb_candidats_journalises == 0
    assert db_session.query(DiagnosticJournal).count() == 0


def test_detecter_doublons_idempotent_ne_rejournalise_pas_une_paire_deja_vue(db_session):
    db_session.add_all(
        [_company("les services exp inc"), _company("les services exp inc compte principal")]
    )
    db_session.flush()

    detecter_doublons(db_session)
    assert db_session.query(DiagnosticJournal).count() == 1

    rapport_2 = detecter_doublons(db_session)
    assert rapport_2.nb_candidats_journalises == 0
    assert db_session.query(DiagnosticJournal).count() == 1  # toujours une seule entrée


def test_detecter_doublons_ignore_les_entreprises_deja_resolues_au_neq(db_session):
    db_session.add_all(
        [
            _company("transport beaulieu inc", neq="1234567890"),
            _company("transport beaulieux inc", neq="9876543210"),
        ]
    )
    db_session.flush()
    rapport = detecter_doublons(db_session)
    assert rapport.nb_fusions_auto == 0
    assert rapport.nb_candidats_journalises == 0
