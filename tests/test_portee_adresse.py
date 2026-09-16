"""Le préalable de l'adresse établit-il ce qu'il annonce?

**Il n'apparie rien**, et c'est son objet : *mesurer un appariement contre un
champ vide rendrait zéro, et ce zéro se lirait comme « l'adresse ne sert à
rien ».*

La population de ces tests a une réponse connue : **aucun dossier ne porte
d'adresse, un signal en porte une dans `champs`** — c'est exactement la forme du
défaut de l'EIMT, capturée puis jamais promue.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from falkye.models.company import Company
from falkye.models.req_entry import REQEntry
from falkye.models.signal import Signal
from falkye.sources.column_mapping import normaliser
from outils import portee_adresse


@pytest.fixture()
def population(db_session, monkeypatch):
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")

    orphelin = Company(neq=None, nom_detecte="Ferme Dallaire",
                       nom_detecte_normalise=normaliser("Ferme Dallaire"))
    db_session.add(orphelin)
    db_session.add(REQEntry(neq="7777777777", nom="ferme dallaire freres",
                            nom_normalise="ferme dallaire freres",
                            statut="IMMATRICULÉE",
                            adresse="123 RANG SAINT-JOSEPH", ville="Saint-Anselme"))
    db_session.flush()
    db_session.add(Signal(
        company_id=orphelin.id, source_id="eimt", signal_type_id="recrutement_massif",
        source_ref="eimt:essai:1", detected_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        champs={"adresse": "123, Rang Saint-Joseph, bureau 2", "profession": "x"},
    ))
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def test_il_dit_quaucune_entreprise_a_apparier_ne_porte_dadresse(population, capsys):
    """⛔ **Le constat qui doit arriver AVANT toute mesure d'appariement.**"""
    assert portee_adresse.main([]) == 0
    sortie = capsys.readouterr().out
    assert "AUCUNE des entreprises à apparier ne porte d'adresse" in sortie
    assert "ce" in sortie and "zéro ne dirait rien de l'adresse" in sortie


def test_le_gisement_cache_est_trouve_par_source(population, capsys):
    """*C'est là que vit celle de l'EIMT : capturée dans `champs`, jamais promue
    en `RawSignal.adresse`.*"""
    assert portee_adresse.main([]) == 0
    sortie = capsys.readouterr().out
    assert "eimt" in sortie
    assert "avec adresse" in sortie


def test_la_FORME_est_montree_des_deux_cotes(population, capsys):
    """**Deux taux de remplissage élevés ne disent pas que les deux chaînes se
    comparent** — et c'est la seule chose qu'un taux ne montre jamais."""
    assert portee_adresse.main([]) == 0
    sortie = capsys.readouterr().out
    assert "123, Rang Saint-Joseph, bureau 2" in sortie, "la forme côté produit manque"
    assert "123 RANG SAINT-JOSEPH" in sortie, "la forme côté miroir manque"


def test_il_dit_ce_quil_ne_dit_PAS(population, capsys):
    assert portee_adresse.main([]) == 0
    assert "CE QUE CET OUTIL NE DIT PAS" in capsys.readouterr().out


def test_il_NECRIT_RIEN(population):
    from sqlalchemy import select

    avant = {c.id: c.adresse for c in population.execute(select(Company)).scalars().all()}
    assert portee_adresse.main([]) == 0
    population.expire_all()
    apres = {c.id: c.adresse for c in population.execute(select(Company)).scalars().all()}
    assert avant == apres, "le préalable a modifié la base"
