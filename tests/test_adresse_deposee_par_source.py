"""Quelle adresse chaque source dépose — **une mesure, elle n'écrit rien.**

⚠️ **Ce que ces tests verrouillent :** l'asymétrie du constat. *La VARIATION
réfute « adresse d'entreprise »; la CONSTANCE ne la confirme pas* — et « une
seule observation » se compte à part, sinon elle gonfle la constance.
"""
from __future__ import annotations

import datetime as _dt

import pytest

from falkye.models.company import Company, StatutResolution
from falkye.models.req_entry import REQEntry
from falkye.models.signal import Signal
from falkye.sources.column_mapping import normaliser
from outils import adresse_deposee_par_source as outil


def test_un_signal_sans_adresse_ne_rend_AUCUN_fait():
    """*« Rien » et « une adresse vide » sont deux choses.*"""
    assert outil.fait_du_signal(None) is None
    assert outil.fait_du_signal({}) is None
    assert outil.fait_du_signal({"valeur_contrat": 1000}) is None


def test_le_fait_se_lit_par_les_CLES_DE_LA_PRODUCTION():
    """⚠️ *Les clés sont celles du départageur et de `villes_des_signaux`* —
    empruntées, jamais recopiées."""
    faits = outil.fait_du_signal({"adresse": "200 rue des Commandeurs G1A1A1"})
    assert faits is not None and faits.code_complet is not None
    imbrique = outil.fait_du_signal(
        {"adresse_entreprise_adjudicataire": {"code_postal": "H2X1Y1"}})
    assert imbrique is not None and imbrique.code_complet is not None


def test_l_empreinte_va_du_PLUS_FIN_au_plus_grossier():
    """*Une variation de graphie de rue ne doit pas compter comme un
    déplacement.*"""
    from outils.departageur_adresse import FaitsDAdresse
    from outils.departageurs import codes_postaux, fait_de_la_ville

    complet = FaitsDAdresse(codes_postaux("G1A1A1"), fait_de_la_ville("Quebec"))
    tri = FaitsDAdresse(codes_postaux("G1A"), fait_de_la_ville("Quebec"))
    ville = FaitsDAdresse(None, fait_de_la_ville("Quebec"))
    assert outil._empreinte(complet).startswith("code complet:")
    assert outil._empreinte(tri).startswith("region:")
    assert outil._empreinte(ville).startswith("ville:")
    assert outil._empreinte(complet) != outil._empreinte(tri)


@pytest.mark.parametrize("empreintes, attendu", [
    ({"a", "b"}, outil.VARIABLE),
    ({"a"}, outil.CONSTANTE),
    (set(), outil.UNE_SEULE),
])
def test_une_seule_observation_ne_compte_PAS_comme_constante(empreintes, attendu):
    """⚠️ **L'asymétrie.** *Un dossier dont aucun signal ne porte d'adresse n'est
    pas « constant » : il est muet, et le ranger avec les constants gonflerait
    exactement la conclusion qu'on cherche à éprouver.*"""
    assert outil.regime_de(empreintes) == attendu


@pytest.fixture()
def decor(db_session, monkeypatch):
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")

    #: (nom, neq posé, [code postal de chaque signal])
    dossiers = [
        # deux lieux différents pour la même entreprise → VARIABLE
        ("Plomberie Alpha inc", "1500000001", ["G1A1A1", "H2X1Y1"]),
        # même lieu deux fois → CONSTANTE
        ("Plomberie Beta inc", "1500000002", ["G1A1A1", "G1A1A1"]),
        # deux signaux, aucune adresse → UNE SEULE (muette)
        ("Plomberie Gamma inc", "1500000003", [None, None]),
    ]
    for nom, neq, codes in dossiers:
        company = Company(neq=neq, nom_detecte=nom,
                          nom_detecte_normalise=normaliser(nom),
                          statut_resolution=StatutResolution.RESOLU,
                          first_detected_at=_dt.datetime(2026, 1, 1))
        db_session.add(company)
        db_session.flush()
        for code in codes:
            db_session.add(Signal(
                company_id=company.id, source_id="eimt",
                signal_type_id="recrutement_massif",
                detected_at=_dt.datetime(2026, 1, 1),
                champs={"adresse": code} if code else {}))
        # ⚠️ Le registre porte le DOMICILE — ici G1A1A1 pour les trois.
        db_session.add(REQEntry(neq=neq, nom=nom, nom_normalise=normaliser(nom),
                                statut="immatriculee", code_postal="G1A1A1"))
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def test_la_dispersion_separe_les_TROIS_regimes(decor, capsys):
    assert outil.main(["--exemples", "3"]) == 0
    sortie = capsys.readouterr().out
    bloc = sortie.split("L'ADRESSE VARIE-T-ELLE")[1]
    ligne = next(l for l in bloc.splitlines() if l.strip().startswith("eimt"))
    #  source  dossiers  constante  VARIABLE  muette  part
    assert ligne.split()[1:5] == ["3", "1", "1", "1"], ligne
    assert "#1" in sortie.split("adresse variable")[1][:200]


def test_la_concordance_avec_le_NEQ_du_dossier_est_rendue(decor, capsys):
    """*Sur les dossiers posés, plus aucune ambiguïté de candidat.*"""
    assert outil.main([]) == 0
    sortie = capsys.readouterr().out
    bloc = sortie.split("CONCORDE-T-ELLE AVEC LE NEQ DU DOSSIER")[1]
    from tests.conftest import compte_de_la_ligne

    concorde = next(l for l in bloc.splitlines()
                    if l.strip().startswith("code postal complet"))
    contre = next(l for l in bloc.splitlines()
                  if l.strip().startswith(outil.AUCUN_NIVEAU))
    assert compte_de_la_ligne(concorde) == "3", concorde   # 2 × Beta + 1 × Alpha
    assert compte_de_la_ligne(contre) == "1", contre       # le second lieu d'Alpha


def test_les_deux_lectures_d_un_desaccord_sont_DITES(decor, capsys):
    """⚠️ *Un désaccord est soit une adresse qui n'est pas celle de
    l'entreprise, soit un NEQ posé à tort.* **Même compte, deux suites.**"""
    assert outil.main([]) == 0
    sortie = capsys.readouterr().out
    assert "UN DÉSACCORD A DEUX LECTURES" in sortie
    assert "point 25" in sortie
    assert "LE REGISTRE PORTE LE DOMICILE" in sortie
    assert "RIEN N'A ÉTÉ ÉCRIT" in sortie


def test_ce_que_le_code_depose_est_lu_par_ARBRE_SYNTAXIQUE(decor, capsys):
    assert outil.main([]) == 0
    sortie = capsys.readouterr().out
    assert "lu par arbre syntaxique" in sortie
    assert "adresse_entreprise_adjudicataire" in sortie, "la clé du sac du SEAO"
    assert "DIT OÙ L'ADRESSE ATTERRIT, JAMAIS CE QU'ELLE EST" in sortie
