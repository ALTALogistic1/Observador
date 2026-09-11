"""D'où viennent les entreprises — et ce que « retirer une source » ferait vraiment.

Deux nombres, jamais un seul : les entreprises qu'une source TOUCHE, et celles
qu'elle est seule à voir. Seul le second dit ce qui disparaîtrait.
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

from outils.provenance_entreprises import ventiler

RACINE = Path(__file__).resolve().parents[1]


def _paires():
    #  c1 : vue par deux sources      → exclusive à aucune
    #  c2 : vue par le palmarès seul  → exclusive au palmarès
    #  c3 : vue par le SEAO seul      → exclusive au SEAO
    return [(1, "seao"), (1, "rob_top_growing"), (2, "rob_top_growing"), (3, "seao")]


def test_une_entreprise_vue_par_deux_sources_nest_exclusive_a_aucune():
    v = ventiler(_paires())

    assert v["touchees"] == {"seao": 2, "rob_top_growing": 2}
    assert v["exclusives"] == {"rob_top_growing": 1, "seao": 1}


def test_les_touchees_ne_disent_pas_ce_qui_disparaitrait():
    """Le piège que cet outil existe pour éviter : `rob_top_growing` touche deux
    entreprises et n'en porte qu'une seule à elle seule. Lire la première comme
    un coût de retrait la doublerait."""
    v = ventiler(_paires())

    assert v["touchees"]["rob_top_growing"] == 2
    assert v["exclusives"]["rob_top_growing"] == 1


def test_le_compte_des_entreprises_avec_signal_ne_double_pas_les_doublons():
    v = ventiler(_paires())

    assert v["entreprises_avec_signal"] == 3
    assert v["signaux"] == 4


def test_il_lit_les_signaux_reels_de_la_base(db_session):
    from falkye.models.company import Company
    from falkye.models.signal import Signal
    from outils.provenance_entreprises import paires

    c = Company(nom_detecte="Test", nom_detecte_normalise="test")
    db_session.add(c)
    db_session.flush()
    db_session.add(
        Signal(
            company_id=c.id, source_id="deloitte_fast50", signal_type_id="classement_croissance",
            detected_at=datetime.now(), champs={},
        )
    )
    db_session.commit()

    assert paires(db_session) == [(c.id, "deloitte_fast50")]


def test_il_refuse_une_cible_que_personne_na_choisie(tmp_path):
    """Zéro entreprise sur une base vide se lit exactement comme zéro
    entreprise — le verdict le plus rassurant de tous *(journal, cas 30)*."""
    fait = subprocess.run(
        [sys.executable, str(RACINE / "outils" / "provenance_entreprises.py")],
        cwd=tmp_path,
        env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(RACINE), "HOME": str(tmp_path)},
        capture_output=True, text=True, check=False,
    )

    assert fait.returncode == 2, fait.stdout + fait.stderr
    assert "REFUS" in fait.stdout + fait.stderr
    assert not (tmp_path / "data").exists()
