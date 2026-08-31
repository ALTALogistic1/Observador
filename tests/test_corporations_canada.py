"""Tests de régression pour des bugs réels trouvés en validant le connecteur
Corporations Canada avec de vraies données (2026-08-31) :
1. "inactive" contient la sous-chaîne "active", donc un filtre
   name_contains="active" naïf attrapait aussi les ressources de corporations
   dissoutes.
2. Calibration : le code d'origine traitait toute NOUVELLE corporation
   détectée par le diff comme un signal — au premier import réel (~695 000
   corporations actives), ça aurait produit ~695 000 signaux. Corrigé : seul
   un changement d'adresse pour une corporation DÉJÀ connue produit un
   signal (même correction que pour le REQ le même jour)."""
from observador.sources.corporations_canada import (
    IngestStats,
    _filtrer_ressources_actives,
    _upsert_row,
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


def test_nouvelle_corporation_ne_produit_pas_de_signal(db_session):
    """Une toute nouvelle corporation active ne doit produire AUCUN signal —
    ce n'est pas une entreprise en croissance. Mise en miroir quand même
    (utile pour la résolution future)."""
    stats = IngestStats()
    _upsert_row(db_session, _row("1234567"), _COLUMNS, {}, stats)

    assert stats.changements_adresse == []
    assert len(stats.nouvelles_corporations_actives) == 1  # comptage/audit seulement, pas un signal


def test_changement_adresse_pour_corporation_deja_connue_produit_un_signal(db_session):
    stats1 = IngestStats()
    _upsert_row(db_session, _row("7654321", rue="1 rue A", ville="Québec"), _COLUMNS, {}, stats1)

    stats2 = IngestStats()
    _upsert_row(db_session, _row("7654321", rue="2 rue B", ville="Québec"), _COLUMNS, {}, stats2)

    assert len(stats2.changements_adresse) == 1
    assert stats2.changements_adresse[0]["nouvelle_adresse"] == "2 rue B, Québec, QC, H1H1H1"


def test_corporation_devenue_inactive_ne_declenche_pas_de_signal_meme_avec_changement_adresse(db_session):
    stats1 = IngestStats()
    _upsert_row(db_session, _row("1112223", rue="1 rue A", statut="Active"), _COLUMNS, {}, stats1)

    stats2 = IngestStats()
    _upsert_row(db_session, _row("1112223", rue="2 rue B", statut="Dissolved"), _COLUMNS, {}, stats2)

    assert stats2.changements_adresse == []
