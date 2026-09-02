"""Tests du filtre par taille d'entreprise estimée (falkye/taille_entreprise.py)
— spec section 4bis. Fixtures minimales, aucune donnée de prospect réelle."""
from falkye.models.company import Company
from falkye.models.signal import Signal
from falkye.taille_entreprise import (
    BORNES_TRANCHE,
    TrancheTaille,
    correspond_au_filtre,
    estimer_taille,
)


def _company():
    return Company(nom_detecte="Entreprise Test", nom_detecte_normalise="entreprise test")


def _ajouter_signal_recrutement(company, valeur_associee, sig_id=1):
    s = Signal(
        id=sig_id, company_id=1, source_id="eimt", signal_type_id="recrutement_massif",
        source_ref=f"ref-{sig_id}", valeur_associee=valeur_associee, champs={},
    )
    company.signals.append(s)
    return s


def test_estimer_taille_retourne_none_sans_signal_de_recrutement():
    company = _company()
    assert estimer_taille(company) is None


def test_estimer_taille_micro_pour_un_seul_poste_qualitatif():
    company = _company()
    _ajouter_signal_recrutement(company, valeur_associee=None)  # signal qualitatif, pas de volume compté
    estimation = estimer_taille(company)
    assert estimation.tranche == TrancheTaille.MICRO


def test_estimer_taille_petite_pour_un_volume_moyen():
    company = _company()
    _ajouter_signal_recrutement(company, valeur_associee=8.0)
    estimation = estimer_taille(company)
    assert estimation.tranche == TrancheTaille.PETITE


def test_estimer_taille_grande_pour_un_gros_volume_cumule():
    company = _company()
    _ajouter_signal_recrutement(company, valeur_associee=60.0, sig_id=1)
    _ajouter_signal_recrutement(company, valeur_associee=45.0, sig_id=2)
    estimation = estimer_taille(company)
    assert estimation.tranche == TrancheTaille.GRANDE
    assert estimation.volume_postes_estime == 105.0


def test_estimer_taille_ignore_les_signaux_non_recrutement():
    company = _company()
    _ajouter_signal_recrutement(company, valeur_associee=2.0)
    autre = Signal(
        id=2, company_id=1, source_id="seao", signal_type_id="appel_offres",
        source_ref="ref-2", valeur_associee=500000.0, champs={},
    )
    company.signals.append(autre)
    estimation = estimer_taille(company)
    assert estimation.volume_postes_estime == 2.0  # le contrat n'entre pas dans le calcul


def test_correspond_au_filtre_sans_filtre_accepte_tout():
    company = _company()
    assert correspond_au_filtre(company, None, None) is True


def test_correspond_au_filtre_rejette_entreprise_sans_estimation_si_filtre_actif():
    company = _company()
    assert correspond_au_filtre(company, 5, 19) is False


def test_correspond_au_filtre_accepte_chevauchement():
    company = _company()
    _ajouter_signal_recrutement(company, valeur_associee=8.0)  # PETITE (5-19)
    assert correspond_au_filtre(company, 0, 10) is True
    assert correspond_au_filtre(company, 20, 99) is False


def test_bornes_tranche_couvrent_les_quatre_paliers():
    assert set(BORNES_TRANCHE.keys()) == {
        TrancheTaille.MICRO, TrancheTaille.PETITE, TrancheTaille.MOYENNE, TrancheTaille.GRANDE,
    }
    assert BORNES_TRANCHE[TrancheTaille.GRANDE][1] is None  # "et plus", pas de borne haute
