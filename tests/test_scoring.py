"""Tests de la logique pure de scoring (observador/scoring.py) — spec section 6.
Aucune donnée de prospect ici : uniquement des valeurs numériques arbitraires pour
vérifier le comportement des fonctions de calcul."""
from datetime import datetime, timedelta, timezone

import pytest

from observador.models.notification import NiveauConfiance
from observador.models.signal import Signal
from observador.scoring import (
    calculer_score,
    franchit_seuil_sensibilite,
    freshness_factor,
)


def _signal(signal_type_id, detected_at=None, valeur=None, champs=None, sig_id=1):
    s = Signal(
        id=sig_id,
        company_id=1,
        source_id="test_source",
        signal_type_id=signal_type_id,
        source_ref=f"ref-{sig_id}",
        detected_at=detected_at or datetime.now(timezone.utc),
        valeur_associee=valeur,
        champs=champs or {},
    )
    return s


def test_freshness_factor_est_maximal_a_zero_jour():
    now = datetime.now(timezone.utc)
    assert freshness_factor(now, now) == pytest.approx(1.0)


def test_freshness_factor_decroit_avec_le_temps():
    now = datetime.now(timezone.utc)
    recent = freshness_factor(now - timedelta(days=10), now)
    vieux = freshness_factor(now - timedelta(days=300), now)
    assert recent > vieux


def test_freshness_factor_a_un_plancher():
    now = datetime.now(timezone.utc)
    tres_vieux = freshness_factor(now - timedelta(days=100_000), now)
    assert tres_vieux >= 0.15
    assert tres_vieux == pytest.approx(0.15, abs=1e-6)


def test_score_appel_offres_valeur_elevee_donne_niveau_eleve():
    now = datetime.now(timezone.utc)
    s = _signal("appel_offres", detected_at=now, valeur=2_000_000)
    result = calculer_score([s], now=now)
    assert result.niveau == NiveauConfiance.ELEVE
    assert 0 <= result.score_confiance <= 100


def test_score_appel_offres_valeur_faible_donne_niveau_faible():
    now = datetime.now(timezone.utc)
    s = _signal("appel_offres", detected_at=now, valeur=5_000)
    result = calculer_score([s], now=now)
    assert result.niveau == NiveauConfiance.FAIBLE


def test_corroboration_multi_signaux_augmente_le_score():
    now = datetime.now(timezone.utc)
    seul = calculer_score([_signal("appel_offres", detected_at=now, valeur=100_000, sig_id=1)], now=now)
    combine = calculer_score(
        [
            _signal("appel_offres", detected_at=now, valeur=100_000, sig_id=1),
            _signal("registre_corporatif", detected_at=now, champs={"type_changement": "nouvel_etablissement"}, sig_id=2),
        ],
        now=now,
    )
    assert combine.bonus_corroboration > 0
    assert combine.score_confiance > seul.score_confiance


def test_meme_type_de_signal_repete_ne_declenche_pas_de_bonus_corroboration():
    now = datetime.now(timezone.utc)
    result = calculer_score(
        [
            _signal("appel_offres", detected_at=now, valeur=100_000, sig_id=1),
            _signal("appel_offres", detected_at=now, valeur=120_000, sig_id=2),
        ],
        now=now,
    )
    assert result.bonus_corroboration == 0


def test_recrutement_qualitatif_fort_meme_a_un_seul_poste():
    now = datetime.now(timezone.utc)
    s = _signal(
        "recrutement_massif",
        detected_at=now,
        champs={"correspondance_qualitative": True, "mots_cles_trouves": ["implantation"]},
    )
    result = calculer_score([s], now=now)
    assert result.niveau in (NiveauConfiance.MOYEN, NiveauConfiance.ELEVE)


def test_calculer_score_leve_erreur_sans_signal():
    with pytest.raises(ValueError):
        calculer_score([])


@pytest.mark.parametrize(
    "niveau,sensibilite,attendu",
    [
        (NiveauConfiance.FAIBLE, "eleve", True),
        (NiveauConfiance.FAIBLE, "moyen", False),
        (NiveauConfiance.FAIBLE, "faible", False),
        (NiveauConfiance.MOYEN, "moyen", True),
        (NiveauConfiance.MOYEN, "faible", False),
        (NiveauConfiance.ELEVE, "faible", True),
    ],
)
def test_franchit_seuil_sensibilite(niveau, sensibilite, attendu):
    assert franchit_seuil_sensibilite(niveau, sensibilite) == attendu
