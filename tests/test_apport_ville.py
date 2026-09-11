"""Ce que la ville apporte se mesure en la retirant — et la règle rejouée est celle du moteur.

Compter les entreprises qu'une source crée dit ce qu'elle COÛTE. Seul le rejeu
— résolution avec la ville, puis sans — dit ce qu'elle APPORTE.
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from falkye.resolution import SEUIL_AMBIGUITE_ECART_MIN, SEUIL_RESOLUTION_CONFIANTE, neq_retenu
from outils.apport_ville import entreprises_exclusives

RACINE = Path(__file__).resolve().parents[1]


@dataclass
class _Entree:
    neq: str


@dataclass
class _Match:
    entry: _Entree
    score: float


def test_un_candidat_sur_mais_pas_detache_reste_ambigu():
    """Les DEUX conditions, pas une moyenne : c'est la règle que le moteur
    applique, et un outil qui la recopierait mesurerait sa propre copie."""
    matches = [
        _Match(_Entree("1"), SEUIL_RESOLUTION_CONFIANTE + 1),
        _Match(_Entree("2"), SEUIL_RESOLUTION_CONFIANTE + 1 - (SEUIL_AMBIGUITE_ECART_MIN - 1)),
    ]

    assert neq_retenu(matches) is None


def test_un_candidat_unique_et_sur_est_retenu():
    assert neq_retenu([_Match(_Entree("1"), SEUIL_RESOLUTION_CONFIANTE)]) == "1"


def test_un_candidat_detache_mais_pas_assez_sur_reste_ambigu():
    assert neq_retenu([_Match(_Entree("1"), SEUIL_RESOLUTION_CONFIANTE - 1)]) is None


def test_aucun_candidat_nest_pas_une_resolution():
    assert neq_retenu([]) is None


def test_une_entreprise_vue_ailleurs_nest_pas_exclusive(db_session):
    """L'exclusivité est ce qui rend la ville attribuable : une entreprise vue
    par une autre source a pu recevoir sa ville de celle-là."""
    from falkye.models.company import Company
    from falkye.models.signal import Signal

    def _entreprise(nom, sources):
        c = Company(nom_detecte=nom, nom_detecte_normalise=nom)
        db_session.add(c)
        db_session.flush()
        for source_id in sources:
            db_session.add(
                Signal(
                    company_id=c.id, source_id=source_id, signal_type_id="classement_croissance",
                    detected_at=datetime.now(), champs={},
                )
            )
        return c

    seule = _entreprise("seule", ["rob_top_growing"])
    partagee = _entreprise("partagee", ["rob_top_growing", "seao"])
    db_session.commit()

    ids = entreprises_exclusives(db_session, ["rob_top_growing"])

    assert seule.id in ids
    assert partagee.id not in ids


def test_les_deux_palmares_ensemble_comptent_comme_un_ensemble(db_session):
    """Une entreprise vue par les DEUX et par aucune autre est exclusive à
    l'ensemble — c'est le cas que la somme par source manque."""
    from falkye.models.company import Company
    from falkye.models.signal import Signal

    c = Company(nom_detecte="deux", nom_detecte_normalise="deux")
    db_session.add(c)
    db_session.flush()
    for source_id in ("rob_top_growing", "deloitte_fast50"):
        db_session.add(
            Signal(
                company_id=c.id, source_id=source_id, signal_type_id="classement_croissance",
                detected_at=datetime.now(), champs={},
            )
        )
    db_session.commit()

    assert c.id not in entreprises_exclusives(db_session, ["rob_top_growing"])
    assert c.id in entreprises_exclusives(db_session, ["rob_top_growing", "deloitte_fast50"])


def test_loutil_refuse_une_cible_que_personne_na_choisie(tmp_path):
    fait = subprocess.run(
        [sys.executable, str(RACINE / "outils" / "apport_ville.py")],
        cwd=tmp_path,
        env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(RACINE), "HOME": str(tmp_path)},
        capture_output=True, text=True, check=False,
    )

    assert fait.returncode == 2, fait.stdout + fait.stderr
    assert "REFUS" in fait.stdout + fait.stderr


def test_le_verificateur_affiche_letat_du_tampon():
    """Affichage, jamais blocage : l'oubli devient visible à chaque demande de
    fusion, sans qu'une sortie nommée puisse être prise par réflexe."""
    fait = subprocess.run(
        [sys.executable, str(RACINE / "outils" / "verifier-corpus.py")],
        cwd=RACINE / "docs" / "spec", capture_output=True, text=True, check=False,
    )

    assert "Notes à consigner" in fait.stdout
