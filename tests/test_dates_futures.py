"""Une date postérieure à aujourd'hui n'est pas un signal — la source se contredit.

Vérifié le 2026-09-14 sur les deux cas réels des contrats fédéraux : celui daté du
`2026-12-01` porte `contract_period_start = 2026-01-12` — le jour et le mois transposés
— et `reporting_period = 2025-2026-Q3`; celui du `2026-09-26` porte
`contract_period_start = 2026-02-01` et un rapport de Q4 2025-2026. **Un rapport
trimestriel ne peut pas décrire un contrat attribué après la fin du trimestre.**

Ces deux-là étaient **les deux seuls signaux** de la source en base.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from falkye.sources.contrats_federaux import ContratsFederauxConnector
from falkye.sources.fraicheur_datastore import TAILLE_PAGE


class _Client:
    def __init__(self, records):
        self.records = records

    def resources(self, package_id, format_filter=None):
        return [{"id": "res", "name": "Contracts over $10,000", "datastore_active": True}]

    def datastore_search(self, resource_id, filters=None, sort=None, limit=None, offset=0):
        return {"records": self.records[offset : offset + (limit or TAILLE_PAGE)]}


def _contrat(ref, date, nom="Untel inc."):
    return {
        "reference_number": ref, "vendor_name": nom, "contract_date": date,
        "contract_value": "50000", "description_fr": "Services",
        "owner_org_title": "Ministère", "economic_object_code": "1245",
    }


def _detecter(monkeypatch, db_session, records):
    from falkye.sources import contrats_federaux

    monkeypatch.setattr(contrats_federaux, "CKANClient", lambda *a, **k: _Client(records))
    connecteur = ContratsFederauxConnector.__new__(ContratsFederauxConnector)
    connecteur.limit = 50
    return list(connecteur.detect(None, db_session))


def test_un_contrat_date_du_FUTUR_ne_produit_pas_de_signal(monkeypatch, db_session):
    demain = (datetime.now(timezone.utc) + timedelta(days=80)).strftime("%Y-%m-%d")

    signaux = _detecter(monkeypatch, db_session, [_contrat("r1", demain)])

    assert signaux == []


def test_un_contrat_passe_produit_un_signal(monkeypatch, db_session):
    hier = (datetime.now(timezone.utc) - timedelta(days=53)).strftime("%Y-%m-%d")

    signaux = _detecter(monkeypatch, db_session, [_contrat("r1", hier)])

    assert len(signaux) == 1
    assert signaux[0].source_ref == "contrats_federaux:r1"


def test_une_aberration_NARRETE_PLUS_le_parcours(monkeypatch, db_session):
    """Le défaut exact du 2026-09-14 : deux dates futures en tête du tri passaient la
    fenêtre, et la troisième ligne — plus ancienne — déclenchait le `return`. Deux
    signaux sur 1 313 621 contrats."""
    futur = (datetime.now(timezone.utc) + timedelta(days=80)).strftime("%Y-%m-%d")
    vieux = (datetime.now(timezone.utc) - timedelta(days=53)).strftime("%Y-%m-%d")

    signaux = _detecter(
        monkeypatch, db_session,
        [_contrat("r1", futur), _contrat("r2", futur), _contrat("r3", vieux),
         _contrat("r4", vieux), _contrat("r5", vieux)],
    )

    assert [s.source_ref for s in signaux] == [
        "contrats_federaux:r3", "contrats_federaux:r4", "contrats_federaux:r5"
    ]


def test_une_date_ancienne_nest_plus_un_motif_darret(monkeypatch, db_session):
    """La fenêtre `since` ne filtre plus l'ingestion : la divulgation proactive
    publie des contrats vieux de plusieurs mois, et c'est la déduplication qui borne."""
    tres_vieux = (datetime.now(timezone.utc) - timedelta(days=400)).strftime("%Y-%m-%d")

    from falkye.sources import contrats_federaux

    monkeypatch.setattr(
        contrats_federaux, "CKANClient", lambda *a, **k: _Client([_contrat("r1", tres_vieux)])
    )
    connecteur = ContratsFederauxConnector.__new__(ContratsFederauxConnector)
    connecteur.limit = 50

    signaux = list(connecteur.detect(datetime.now(timezone.utc) - timedelta(days=30), db_session))

    assert len(signaux) == 1


def test_le_code_dobjet_economique_est_capte(monkeypatch, db_session):
    """100 % de remplissage, 47 valeurs distinctes — l'équivalent fédéral de la
    classification du SEAO, présent depuis toujours et lu par personne."""
    hier = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%d")

    signaux = _detecter(monkeypatch, db_session, [_contrat("r1", hier)])

    assert signaux[0].champs["objet_economique"] == "1245"
