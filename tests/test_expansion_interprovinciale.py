"""Tests de la détection d'expansion inter-provinciale
(falkye/expansion_interprovinciale.py) — spec Radar+, point 7."""
from datetime import datetime, timezone

import pytest

from falkye.expansion_interprovinciale import (
    SEUIL_RAPPROCHEMENT,
    detecter_expansions,
    evaluer_pour_company,
)
from falkye.models.company import Company
from falkye.models.expansion_interprovinciale import LienInterprovincial
from falkye.models.signal import Signal
from falkye.registry.loader import Registry, SourceDef


def _registry_provinces():
    """Registre minimal avec des sources qc/on/bc, une source fédérale (sans
    province_code, jamais devinée) et une source qc SANS province_code
    (simule une source non encore cartographiée)."""
    return Registry(
        sources={
            "req": SourceDef(
                id="req", nom="REQ", signal_associe=[], statut="actif", blocage_type=None,
                methode_acces=None, champs_pertinents=[], cout="gratuit", region="Québec",
                connecteur=None, province_code="qc",
            ),
            "licences_toronto": SourceDef(
                id="licences_toronto", nom="Toronto", signal_associe=[], statut="actif",
                blocage_type=None, methode_acces=None, champs_pertinents=[], cout="gratuit",
                region="Toronto", connecteur=None, province_code="on",
            ),
            "licences_vancouver": SourceDef(
                id="licences_vancouver", nom="Vancouver", signal_associe=[], statut="actif",
                blocage_type=None, methode_acces=None, champs_pertinents=[], cout="gratuit",
                region="Vancouver", connecteur=None, province_code="bc",
            ),
            "contrats_federaux": SourceDef(
                id="contrats_federaux", nom="Fédéral", signal_associe=[], statut="actif",
                blocage_type=None, methode_acces=None, champs_pertinents=[], cout="gratuit",
                region="Canada", connecteur=None, province_code=None,
            ),
        }
    )


def _company(db_session, nom, source_id, neq=None):
    c = Company(neq=neq, nom_detecte=nom, nom_detecte_normalise=nom.lower())
    db_session.add(c)
    db_session.flush()
    db_session.add(
        Signal(
            company_id=c.id, source_id=source_id, signal_type_id="registre_corporatif",
            source_ref=f"{source_id}:{c.id}", detected_at=datetime.now(timezone.utc), champs={},
        )
    )
    db_session.flush()
    return c


# --- detecter_expansions ---


def test_detecte_un_rapprochement_entre_deux_provinces_differentes(db_session):
    registry = _registry_provinces()
    qc = _company(db_session, "9284712 quebec inc", "req")
    on = _company(db_session, "9284712 quebec inc", "licences_toronto")

    liens = detecter_expansions(db_session, registry)

    assert len(liens) == 1
    lien = liens[0]
    assert {lien.company_id_a, lien.company_id_b} == {qc.id, on.id}
    assert {lien.province_a, lien.province_b} == {"qc", "on"}
    assert lien.score_correspondance >= 95.0  # nom identique


def test_ne_rapproche_pas_deux_companies_de_la_meme_province(db_session):
    registry = _registry_provinces()
    _company(db_session, "acme inc", "req")
    _company(db_session, "acme inc", "req")

    liens = detecter_expansions(db_session, registry)
    assert liens == []


def test_ne_rapproche_pas_sous_le_seuil(db_session):
    registry = _registry_provinces()
    _company(db_session, "solutions logistiques du quebec", "req")
    _company(db_session, "entreprise totalement differente xyz", "licences_toronto")

    liens = detecter_expansions(db_session, registry)
    assert liens == []


def test_ignore_les_companies_sans_province_connue(db_session):
    """Une source sans province_code (ex. fédérale) ne participe jamais au
    mécanisme — jamais deviné."""
    registry = _registry_provinces()
    _company(db_session, "9284712 quebec inc", "req")
    _company(db_session, "9284712 quebec inc", "contrats_federaux")

    liens = detecter_expansions(db_session, registry)
    assert liens == []


def test_idempotent_ne_duplique_jamais_une_paire(db_session):
    registry = _registry_provinces()
    _company(db_session, "9284712 quebec inc", "req")
    _company(db_session, "9284712 quebec inc", "licences_toronto")

    premiere_passe = detecter_expansions(db_session, registry)
    db_session.commit()
    deuxieme_passe = detecter_expansions(db_session, registry)

    assert len(premiere_passe) == 1
    assert deuxieme_passe == []
    assert db_session.query(LienInterprovincial).count() == 1


def test_jamais_de_fusion_les_deux_company_restent_distincts(db_session):
    """Garde-fou structurel : le mécanisme ne modifie jamais Company.neq ni ne
    supprime aucune des deux lignes."""
    registry = _registry_provinces()
    qc = _company(db_session, "9284712 quebec inc", "req", neq="1234567890")
    on = _company(db_session, "9284712 quebec inc", "licences_toronto")

    detecter_expansions(db_session, registry)

    assert db_session.query(Company).count() == 2
    assert db_session.get(Company, qc.id).neq == "1234567890"
    assert db_session.get(Company, on.id).neq is None


# --- evaluer_pour_company ---


def test_evaluer_pour_company_sans_lien_retourne_zero(db_session):
    registry = _registry_provinces()
    qc = _company(db_session, "acme inc", "req")

    evaluation = evaluer_pour_company(db_session, qc)
    assert evaluation.bonus == 0.0
    assert evaluation.texte_hedge is None


def test_evaluer_pour_company_bonus_au_seuil_est_nul(db_session):
    qc = _company(db_session, "a", "req")
    on = _company(db_session, "b", "licences_toronto")
    db_session.add(
        LienInterprovincial(
            company_id_a=min(qc.id, on.id), company_id_b=max(qc.id, on.id),
            province_a="qc", province_b="on", score_correspondance=SEUIL_RAPPROCHEMENT,
        )
    )
    db_session.flush()

    evaluation = evaluer_pour_company(db_session, qc)
    assert evaluation.bonus == 0.0
    assert evaluation.texte_hedge is not None  # toujours hedgé, même à bonus nul


def test_evaluer_pour_company_bonus_maximal_a_score_100(db_session):
    qc = _company(db_session, "a", "req")
    on = _company(db_session, "b", "licences_toronto")
    db_session.add(
        LienInterprovincial(
            company_id_a=min(qc.id, on.id), company_id_b=max(qc.id, on.id),
            province_a="qc", province_b="on", score_correspondance=100.0,
        )
    )
    db_session.flush()

    evaluation = evaluer_pour_company(db_session, qc)
    assert evaluation.bonus == 15.0
    assert "on" not in evaluation.texte_hedge  # nom complet affiché, pas le code brut
    assert "Ontario" in evaluation.texte_hedge
    assert "à valider" in evaluation.texte_hedge


def test_evaluer_pour_company_jamais_presente_comme_un_fait(db_session):
    """Garde-fou textuel — le libellé doit toujours porter le score ET une
    réserve explicite, jamais une affirmation nue."""
    qc = _company(db_session, "a", "req")
    on = _company(db_session, "b", "licences_toronto")
    db_session.add(
        LienInterprovincial(
            company_id_a=min(qc.id, on.id), company_id_b=max(qc.id, on.id),
            province_a="qc", province_b="on", score_correspondance=88.0,
        )
    )
    db_session.flush()

    evaluation = evaluer_pour_company(db_session, qc)
    assert "88" in evaluation.texte_hedge
    assert "à valider" in evaluation.texte_hedge
    assert "possible" in evaluation.texte_hedge
