"""La promotion de la ville — deux fois, journalisée, et défaisable.

⚠️ **Les trois questions d'Alexandre, une par groupe de tests** : *ce qui se
passe si on l'applique deux fois, ce qui est journalisé, et comment on revient
en arrière.*
"""
from __future__ import annotations

import datetime as _dt
import json

import pytest
from sqlalchemy import select

from falkye.models.company import Company
from falkye.models.signal import Signal
from falkye.sources.column_mapping import normaliser
from outils import promotion_ville
from outils.villes_des_signaux import ville_depuis_adresse, villes_des_signaux


def test_la_ville_se_lit_en_TETE_de_ladresse():
    assert ville_depuis_adresse("St-Isidore, QC J0L  2A") == "St-Isidore"
    assert ville_depuis_adresse("200 rue des Commandeurs") is None
    assert ville_depuis_adresse(None) is None


def _cible(monkeypatch):
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")


def _signal(company_id, champs, source="eimt"):
    return Signal(company_id=company_id, source_id=source,
                  signal_type_id="recrutement_massif",
                  detected_at=_dt.datetime(2026, 1, 1), champs=champs)


@pytest.fixture()
def population(db_session, monkeypatch, tmp_path):
    _cible(monkeypatch)
    a = Company(neq=None, nom_detecte="Transport Boreal",
                nom_detecte_normalise=normaliser("Transport Boreal"))
    b = Company(neq=None, nom_detecte="Ferme Bellevue",
                nom_detecte_normalise=normaliser("Ferme Bellevue"))
    c = Company(neq=None, nom_detecte="Deja Remplie", ville="Laval",
                nom_detecte_normalise=normaliser("Deja Remplie"))
    db_session.add_all([a, b, c])
    db_session.flush()
    db_session.add_all([
        _signal(a.id, {"adresse": "Saint-Isidore, QC J0L 2A"}),
        # ⚠️ Deux signaux, deux villes — le dossier B doit être REFUSÉ.
        _signal(b.id, {"adresse": "Levis, QC G6V 1A1"}),
        _signal(b.id, {"ville": "Sherbrooke"}, source="seao"),
        _signal(c.id, {"adresse": "Laval, QC H7N 1A1"}),
    ])
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    monkeypatch.setattr(promotion_ville, "DOSSIER_INSTANTANE", tmp_path)
    return db_session


def _instantane(tmp_path):
    fichiers = sorted(tmp_path.glob("promotion-ville-*.json"))
    assert fichiers, "aucun instantané écrit"
    return fichiers[-1]


# --- ce qui est promu, et ce qui est refusé --------------------------------


def test_le_dossier_a_villes_CONTRADICTOIRES_est_refuse(population, capsys):
    """*Deux signaux qui nomment deux villes ne se tranchent pas par un ordre de
    tri* — même discipline que le refus au-delà de deux prétendants."""
    assert promotion_ville.main(["--sans-familles"]) == 0
    sortie = capsys.readouterr().out
    assert "À PROMOUVOIR                  : 1" in sortie, sortie
    assert "REFUSÉS — signaux contradictoires : 1" in sortie, sortie


def test_une_ville_DEJA_POSEE_nest_jamais_ecrasee(population, tmp_path):
    assert promotion_ville.main(["--sans-familles", "--appliquer",
                                 "--instantane", str(tmp_path)]) == 0
    population.expire_all()
    deja = population.execute(
        select(Company).where(Company.nom_detecte == "Deja Remplie")
    ).scalar_one()
    assert deja.ville == "Laval", "une ville existante a été touchée"


def test_la_ville_du_signal_est_promue(population, tmp_path):
    assert promotion_ville.main(["--sans-familles", "--appliquer",
                                 "--instantane", str(tmp_path)]) == 0
    population.expire_all()
    a = population.execute(
        select(Company).where(Company.nom_detecte == "Transport Boreal")
    ).scalar_one()
    assert a.ville == "Saint-Isidore"


# --- 1. deux fois ----------------------------------------------------------


def test_appliquer_DEUX_FOIS_ne_change_rien_la_seconde(population, tmp_path, capsys):
    """⚠️ **L'idempotence est structurelle** : on ne remplit que ce qui est vide,
    donc la seconde exécution ne trouve plus personne."""
    assert promotion_ville.main(["--sans-familles", "--appliquer",
                                 "--instantane", str(tmp_path)]) == 0
    capsys.readouterr()
    population.expire_all()
    avant = {c.id: c.ville for c in population.execute(select(Company)).scalars().all()}

    assert promotion_ville.main(["--sans-familles", "--appliquer",
                                 "--instantane", str(tmp_path)]) == 0
    sortie = capsys.readouterr().out
    population.expire_all()
    apres = {c.id: c.ville for c in population.execute(select(Company)).scalars().all()}
    assert avant == apres, "la seconde exécution a modifié la base"
    assert "À PROMOUVOIR                  : 0" in sortie, sortie


# --- 2. ce qui est journalisé ----------------------------------------------


def test_linstantane_porte_letat_davant_ET_la_valeur_posee(population, tmp_path):
    assert promotion_ville.main(["--sans-familles", "--appliquer",
                                 "--instantane", str(tmp_path)]) == 0
    contenu = json.loads(_instantane(tmp_path).read_text(encoding="utf-8"))
    (promue,) = contenu["promues"]
    assert promue["ville_avant"] is None
    assert promue["ville_posee"] == "Saint-Isidore"
    assert promue["source_id"] == "eimt"
    assert "adresse" in promue["provenance"]
    assert contenu["refuses_contradictoires"], "les refusés ne sont pas tracés"


def test_il_REFUSE_decrire_si_linstantane_est_impossible(population, tmp_path):
    """*Un geste sans trace de l'état d'avant n'est pas réversible.* Un FICHIER
    en guise de parent rend `mkdir` impossible pour tout le monde, root compris."""
    barrage = tmp_path / "barrage"
    barrage.write_text("x")
    assert promotion_ville.main(
        ["--sans-familles", "--appliquer", "--instantane", str(barrage / "dedans")]
    ) == 3
    population.expire_all()
    a = population.execute(
        select(Company).where(Company.nom_detecte == "Transport Boreal")
    ).scalar_one()
    assert a.ville is None, "une ville a été posée malgré le refus"


# --- 3. comment on revient en arrière --------------------------------------


def test_defaire_remet_la_ville_a_None(population, tmp_path, capsys):
    assert promotion_ville.main(["--sans-familles", "--appliquer",
                                 "--instantane", str(tmp_path)]) == 0
    chemin = _instantane(tmp_path)
    assert promotion_ville.main(["--defaire", str(chemin)]) == 0
    population.expire_all()
    a = population.execute(
        select(Company).where(Company.nom_detecte == "Transport Boreal")
    ).scalar_one()
    assert a.ville is None
    assert "défaites     : 1" in capsys.readouterr().out


def test_defaire_NE_TOUCHE_PAS_une_ville_changee_depuis(population, tmp_path, capsys):
    """⚠️ *Une ville différente de celle qu'on avait posée appartient à quelqu'un
    d'autre, et la défaire serait écraser un tiers.*"""
    assert promotion_ville.main(["--sans-familles", "--appliquer",
                                 "--instantane", str(tmp_path)]) == 0
    chemin = _instantane(tmp_path)
    a = population.execute(
        select(Company).where(Company.nom_detecte == "Transport Boreal")
    ).scalar_one()
    a.ville = "Quebec"       # un tiers est passé par là
    population.commit()

    assert promotion_ville.main(["--defaire", str(chemin)]) == 0
    population.expire_all()
    a = population.execute(
        select(Company).where(Company.nom_detecte == "Transport Boreal")
    ).scalar_one()
    assert a.ville == "Quebec", "la ville d'un tiers a été écrasée"
    assert "ignorées     : 1" in capsys.readouterr().out


# --- les paires, par lot ---------------------------------------------------


def test_comparer_pagine_avec_depuis(population, capsys):
    """*« Dire combien de paires il y a à regarder, et si `--comparer` peut le
    faire par lot. »* — il le peut maintenant."""
    assert promotion_ville.main(["--sans-familles", "--comparer", "1"]) == 0
    premier = capsys.readouterr().out
    assert "paires 1 à 1 sur 1" in premier
    assert promotion_ville.main(["--sans-familles", "--comparer", "1", "--depuis", "1"]) == 0
    second = capsys.readouterr().out
    assert "paires 2 à 1 sur 1" in second, second


def test_il_NECRIT_RIEN_en_mode_rapport(population):
    avant = {c.id: c.ville for c in population.execute(select(Company)).scalars().all()}
    assert promotion_ville.main(["--sans-familles", "--comparer", "5"]) == 0
    population.expire_all()
    apres = {c.id: c.ville for c in population.execute(select(Company)).scalars().all()}
    assert avant == apres


def test_le_geste_dit_quil_ne_resout_RIEN(population, capsys):
    """⚠️ *Les 1 111 départages ne se matérialisent que si la passe de reprise
    tourne APRÈS.*"""
    assert promotion_ville.main(["--sans-familles"]) == 0
    sortie = capsys.readouterr().out
    assert "IL NE RÉSOUT AUCUN DOSSIER" in sortie
    assert "PASSE DE REPRISE tourne APRÈS" in sortie


def test_la_recolte_est_EMPRUNTEE_pas_recopiee(population):
    """*La mesure et le correctif doivent lire la MÊME ville* — sinon la mesure
    compte une chose pendant que l'écriture en pose une autre."""
    from outils import departage_par_ville

    assert departage_par_ville.villes_des_signaux is villes_des_signaux
    assert promotion_ville.villes_des_signaux is villes_des_signaux
