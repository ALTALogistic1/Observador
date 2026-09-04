"""Tests de régression pour des bugs réels trouvés en validant le connecteur
Corporations Canada avec de vraies données (2026-08-31) :
1. "inactive" contient la sous-chaîne "active", donc un filtre
   name_contains="active" naïf attrapait aussi les ressources de corporations
   dissoutes.
2. Calibration : le code d'origine traitait toute NOUVELLE corporation
   détectée par le diff comme un signal — au premier import réel (~695 000
   corporations actives), ça aurait produit ~695 000 signaux. Corrigé : seul
   un changement d'adresse pour une corporation DÉJÀ connue produit un
   signal (même correction que pour le REQ le même jour).

Rebranché sur le moteur de diff générique (Chantier 1, suivi 2026-09-04) —
les tests exercent `_traiter_instantane` directement (aucune dépendance
réseau, `ingest_snapshot` lui-même appelle CKANClient)."""
from falkye.models.corp_federale_entry import CorporationFederaleEntry
from falkye.sources.corporations_canada import (
    CHAMPS_PERTINENTS_CORP,
    _filtrer_ressources_actives,
    _ligne_corporation,
    _resoudre_corporation,
    _traiter_instantane,
    resolve_corp_federale_by_name,
)

_COLUMNS = {
    "numero": "numero",
    "nom": "nom",
    "statut": "statut",
    "rue": "rue",
    "ville": "ville",
    "province": "province",
    "code_postal": "code_postal",
}
_COLONNES_VUES = {c: "str" for c in CHAMPS_PERTINENTS_CORP}


def test_filtre_exclut_les_ressources_inactive():
    resources = [
        {"name": "Active business corporations"},
        {"name": "Inactive business corporations"},
        {"name": "Other active corporations"},
        {"name": "Other inactive corporations"},
    ]
    filtres = _filtrer_ressources_actives(resources)
    noms = {r["name"] for r in filtres}
    assert noms == {"Active business corporations", "Other active corporations"}


def test_filtre_insensible_a_la_casse():
    resources = [{"name": "INACTIVE Corporations"}, {"name": "Active Corporations"}]
    filtres = _filtrer_ressources_actives(resources)
    assert len(filtres) == 1
    assert filtres[0]["name"] == "Active Corporations"


def _row(numero, nom="Entreprise Fictive Inc.", statut="Active", rue="1 rue Test", ville="Montréal"):
    return {
        "numero": numero,
        "nom": nom,
        "statut": statut,
        "rue": rue,
        "ville": ville,
        "province": "QC",
        "code_postal": "H1H1H1",
    }


def _ingest_une_ligne(db_session, row):
    """Reproduit le pipeline complet (résoudre -> diff -> upsert) pour UNE
    seule ligne, sans dépendance réseau — deux appels avec le MÊME numero
    accumulent l'état comme le feraient deux exécutions réelles
    successives."""
    r = _resoudre_corporation(row, _COLUMNS, {})
    ligne = _ligne_corporation(r)
    stats = _traiter_instantane(db_session, [ligne], [r], _COLONNES_VUES, lignes_lues=1)
    db_session.commit()
    return stats


def test_nouvelle_corporation_ne_produit_pas_de_signal(db_session):
    """Une toute nouvelle corporation active ne doit produire AUCUN signal —
    ce n'est pas une entreprise en croissance. Mise en miroir quand même
    (utile pour la résolution future)."""
    stats = _ingest_une_ligne(db_session, _row("1234567"))

    assert stats.changements_adresse == []
    entry = db_session.get(CorporationFederaleEntry, "1234567")
    assert entry is not None
    assert entry.nom == "Entreprise Fictive Inc."


def test_changement_adresse_pour_corporation_deja_connue_produit_un_signal(db_session):
    _ingest_une_ligne(db_session, _row("7654321", rue="1 rue A", ville="Québec"))
    stats2 = _ingest_une_ligne(db_session, _row("7654321", rue="2 rue B", ville="Québec"))

    assert len(stats2.changements_adresse) == 1
    assert stats2.changements_adresse[0]["nouvelle_adresse"] == "2 rue B, Québec, QC, H1H1H1"

    entry = db_session.get(CorporationFederaleEntry, "7654321")
    assert entry.adresse == "2 rue B, Québec, QC, H1H1H1"


def test_corporation_devenue_inactive_ne_declenche_pas_de_signal_meme_avec_changement_adresse(db_session):
    _ingest_une_ligne(db_session, _row("1112223", rue="1 rue A", statut="Active"))
    stats2 = _ingest_une_ligne(db_session, _row("1112223", rue="2 rue B", statut="Dissolved"))

    assert stats2.changements_adresse == []


def test_quarantaine_ne_touche_pas_corporationfederaleentry(db_session):
    """300 disparitions d'un coup (le run précédent avait 300 corporations,
    celui-ci n'en a plus aucune) — quarantaine, miroir intact."""
    lignes_ref = [
        _ligne_corporation(_resoudre_corporation(_row(f"999{i:04d}"), _COLUMNS, {})) for i in range(300)
    ]
    resolues_ref = [_resoudre_corporation(_row(f"999{i:04d}"), _COLUMNS, {}) for i in range(300)]
    stats1 = _traiter_instantane(db_session, lignes_ref, resolues_ref, _COLONNES_VUES, lignes_lues=300)
    db_session.commit()
    assert stats1.quarantaine is False
    assert db_session.get(CorporationFederaleEntry, "9990000") is not None

    ligne_nouvelle = _ligne_corporation(_resoudre_corporation(_row("8880000"), _COLUMNS, {}))
    resolue_nouvelle = _resoudre_corporation(_row("8880000"), _COLUMNS, {})
    stats2 = _traiter_instantane(
        db_session, [ligne_nouvelle], [resolue_nouvelle], _COLONNES_VUES, lignes_lues=1
    )
    db_session.commit()
    assert stats2.quarantaine is True
    assert stats2.quarantaine_motif == "volume_disparitions"
    assert db_session.get(CorporationFederaleEntry, "8880000") is None
    assert db_session.get(CorporationFederaleEntry, "9990000") is not None


# --- resolve_corp_federale_by_name : porte de calibration pour licences_affaires_municipales ---


def test_resolve_corp_federale_par_nom_trouve_une_correspondance_exacte(db_session):
    _ingest_une_ligne(db_session, _row("9990001", nom="Acme Fabrication Inc."))

    matches = resolve_corp_federale_by_name(db_session, "Acme Fabrication Inc.")
    assert matches
    assert matches[0].entry.numero_corporation == "9990001"
    assert matches[0].score == 100.0


def test_resolve_corp_federale_par_nom_retourne_vide_si_rien_ne_correspond(db_session):
    _ingest_une_ligne(db_session, _row("9990002", nom="Acme Fabrication Inc."))

    matches = resolve_corp_federale_by_name(db_session, "Un nom complètement différent xyz")
    assert matches == []


def test_resolve_corp_federale_par_nom_bonus_si_province_correspond(db_session):
    _ingest_une_ligne(db_session, _row("9990003", nom="Nordik Transport Ltée"))

    sans_province = resolve_corp_federale_by_name(db_session, "Nordik Transport")
    avec_province = resolve_corp_federale_by_name(db_session, "Nordik Transport", province="QC")

    assert avec_province[0].score >= sans_province[0].score
