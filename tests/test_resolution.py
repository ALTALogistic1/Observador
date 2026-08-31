"""Tests de la résolution NEQ (observador/resolution.py) contre un miroir REQ local
minimal inséré directement en base de test — pas d'appel réseau, pas de données
fabriquées présentées comme des détections réelles : juste des entrées REQ
plausibles utilisées pour vérifier l'algorithme de correspondance."""
from datetime import datetime, timezone

from observador.models.req_entry import REQEntry
from observador.resolution import resolve_company
from observador.sources.base import RawSignal


def _raw(nom, source_ref="ref-1", ville=None):
    return RawSignal(
        signal_type_id="appel_offres",
        nom_entreprise=nom,
        detected_at=datetime.now(timezone.utc),
        source_ref=source_ref,
        ville=ville,
    )


def test_resolution_directe_par_neq(db_session):
    raw = RawSignal(
        signal_type_id="registre_corporatif",
        nom_entreprise="Entreprise Alpha inc.",
        detected_at=datetime.now(timezone.utc),
        source_ref="req:1",
        neq="1234567890",
    )
    company = resolve_company(db_session, raw)
    assert company.neq == "1234567890"
    assert company.statut_resolution.value == "resolu"


def test_resolution_par_nom_avec_correspondance_unique(db_session):
    db_session.add(
        REQEntry(
            neq="1111111111",
            nom="Transport Beaulieu inc.",
            nom_normalise="transport beaulieu inc",
            statut="immatriculee",
        )
    )
    db_session.flush()

    company = resolve_company(db_session, _raw("Transport Beaulieu inc."))
    assert company.neq == "1111111111"
    assert company.statut_resolution.value == "resolu"


def test_resolution_ambigue_si_deux_noms_trop_proches(db_session):
    db_session.add_all(
        [
            REQEntry(neq="2222222222", nom="9345-1122 Québec inc.", nom_normalise="9345 1122 quebec inc", statut="immatriculee"),
            REQEntry(neq="3333333333", nom="9345-1123 Québec inc.", nom_normalise="9345 1123 quebec inc", statut="immatriculee"),
        ]
    )
    db_session.flush()

    company = resolve_company(db_session, _raw("9345-1122 Québec inc."))
    # Selon le seuil d'écart, ce cas limite reste soit résolu au bon NEQ, soit marqué
    # ambigu — jamais silencieusement résolu au MAUVAIS NEQ.
    if company.statut_resolution.value == "resolu":
        assert company.neq == "2222222222"
    else:
        assert company.statut_resolution.value == "ambigu"


def test_resolution_non_trouvee_sans_candidat(db_session):
    company = resolve_company(db_session, _raw("Entreprise Totalement Inconnue Du Registre XYZ"))
    assert company.neq is None
    assert company.statut_resolution.value == "non_trouve"


def test_meme_entreprise_non_resolue_deux_fois_reste_un_seul_dossier(db_session):
    c1 = resolve_company(db_session, _raw("Entreprise Fantome inc.", source_ref="a"))
    c2 = resolve_company(db_session, _raw("Entreprise Fantome inc.", source_ref="b"))
    assert c1.id == c2.id  # dossier cumulatif : pas de doublon pour le même nom non résolu


def test_statut_radie_propage_depuis_req(db_session):
    db_session.add(
        REQEntry(
            neq="4444444444",
            nom="Entreprise Fermee inc.",
            nom_normalise="entreprise fermee inc",
            statut="radiee",
        )
    )
    db_session.flush()

    company = resolve_company(db_session, _raw("Entreprise Fermee inc."))
    assert company.statut_legal.value == "radiee"
