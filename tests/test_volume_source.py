"""Le volume brut d'une exécution — écrit dès maintenant, lu plus tard.

La norme de volume ne devient calculable qu'avec de l'historique, et
l'historique ne se rattrape pas en accélérant après coup. Ces tests verrouillent
ce que le compte MESURE, parce que c'est là que la norme se trompera si on se
trompe ici : un compte qui ne retient que ce qui a survécu au filtre décrirait
notre tri, pas la santé de la source.
"""
from __future__ import annotations

import dataclasses
from datetime import datetime, timezone

from sqlalchemy import select

from falkye.engine import ingest_source
from falkye.models.run_log import SourceRunLog, StatutExecution
from falkye.registry.loader import get_registry


def _raw(ref, region="Québec"):
    from falkye.sources.base import RawSignal

    return RawSignal(
        signal_type_id="recrutement_massif",
        source_ref=ref,
        nom_entreprise=f"Entreprise {ref}",
        detected_at=datetime(2026, 9, 8, tzinfo=timezone.utc),
        region=region,
        champs={},
    )


def _brancher(monkeypatch, source_id, raws, territoire=("Québec",)):
    registry = get_registry()
    remplace = dataclasses.replace(registry.source(source_id), territoire=list(territoire))
    monkeypatch.setitem(registry.sources, source_id, remplace)

    class _Connecteur:
        def detect(self, since, db_session):
            return iter(raws)

    monkeypatch.setattr(type(remplace), "charger_connecteur", lambda self: _Connecteur())
    return registry


def _ligne(db_session, source_id):
    return db_session.execute(
        select(SourceRunLog).where(SourceRunLog.source_id == source_id)
    ).scalars().all()[-1]


def test_le_volume_compte_tout_ce_que_la_source_a_rendu(db_session, monkeypatch):
    """Y compris ce que le filtre territorial écarte. Une source nationale qui
    cesse de publier hors Québec s'effondre en volume sans qu'un seul signal
    retenu ne change — c'est exactement l'écart qu'une norme doit voir."""
    raws = [_raw("a"), _raw("b", "Ontario"), _raw("c"), _raw("d", "Alberta")]
    registry = _brancher(monkeypatch, "eimt", raws)

    ingest_source(db_session, "eimt", None, registry, "veille_continue")

    assert _ligne(db_session, "eimt").nb_lignes_source == 4


def test_le_volume_compte_aussi_les_doublons(db_session, monkeypatch):
    """Un signal déjà connu n'est pas un signal neuf, mais la source l'a bien
    produit. `nb_signaux_detectes` compte les NEUFS; celui-ci compte le RENDU,
    et les deux ensemble disent si une source ralentit ou si elle répète."""
    registry = _brancher(monkeypatch, "eimt", [_raw("a"), _raw("b")])
    ingest_source(db_session, "eimt", None, registry, "veille_continue")

    registry = _brancher(monkeypatch, "eimt", [_raw("a"), _raw("b"), _raw("c")])
    ingest_source(db_session, "eimt", None, registry, "veille_continue")

    ligne = _ligne(db_session, "eimt")
    assert ligne.nb_lignes_source == 3
    assert ligne.nb_signaux_detectes == 1  # seul « c » est neuf


def test_un_territoire_calme_ecrit_zero_pas_null(db_session, monkeypatch):
    """Zéro ligne rendue EST une mesure — la source a répondu, elle n'avait
    rien. NULL voudrait dire qu'on n'a pas pu mesurer, et les confondre ferait
    lire une semaine calme comme une absence de donnée."""
    registry = _brancher(monkeypatch, "eimt", [])

    ingest_source(db_session, "eimt", None, registry, "veille_continue")

    ligne = _ligne(db_session, "eimt")
    assert ligne.nb_lignes_source == 0
    assert ligne.nb_lignes_source is not None
    assert ligne.statut == StatutExecution.SUCCES.value


def test_une_source_tombee_ne_laisse_pas_un_volume_partiel(db_session, monkeypatch):
    """Un volume partiel comparé à une norme se lirait comme une chute. NULL dit
    « pas de mesure », ce qui est la vérité quand l'exécution n'a pas fini."""
    registry = get_registry()
    remplace = dataclasses.replace(registry.source("eimt"), territoire=["Québec"])
    monkeypatch.setitem(registry.sources, "eimt", remplace)

    class _ConnecteurQuiTombeEnRoute:
        def detect(self, since, db_session):
            yield _raw("a")
            yield _raw("b")
            raise RuntimeError("le portail coupe en plein téléchargement")

    monkeypatch.setattr(
        type(remplace), "charger_connecteur", lambda self: _ConnecteurQuiTombeEnRoute()
    )

    ingest_source(db_session, "eimt", None, registry, "veille_continue")

    ligne = _ligne(db_session, "eimt")
    assert ligne.statut == StatutExecution.ERREUR.value
    assert ligne.nb_lignes_source is None
