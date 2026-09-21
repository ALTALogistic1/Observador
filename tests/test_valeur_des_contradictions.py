"""Ce que valent les contradictions de l'adresse — **une mesure, elle n'écrit rien.**

⚠️ **Ce que ces tests verrouillent :** que l'ordre des causes soit celui qui a
été raisonné *(l'établissement DISSOUT, les autres DÉPLACENT)*, que la coupe de
production soit **lue** et non recopiée, et que la provenance des adresses
d'établissement soit **rendue** — `req_etablissements` est gelée depuis le
2026-09-04, et deux millésimes ne se mélangent pas en silence.
"""
from __future__ import annotations

import datetime as _dt

import pytest

from falkye.models.company import Company, StatutResolution
from falkye.models.etat_diff_source import EtatLigneSource
from falkye.models.req_entry import REQEntry
from falkye.models.req_etablissement_entry import REQEtablissementEntry
from falkye.models.signal import Signal
from falkye.sources.column_mapping import normaliser
from outils import valeur_des_contradictions as outil
from outils.departageur_adresse import FaitsDAdresse
from outils.departageurs import codes_postaux, fait_de_la_ville

DOSSIER = "G9A2G9"
AILLEURS = "G8Z0A3"


def _faits(code_postal):
    return FaitsDAdresse(codes_postaux(code_postal), fait_de_la_ville(None))


class _Match:
    def __init__(self, neq, score, code_postal, statut="radiee"):
        self.entry = type("E", (), {
            "neq": neq, "score": score, "code_postal": code_postal,
            "adresse": None, "ville": None, "nom": f"n{neq}", "statut": statut})()
        self.score = score
        self.forme_normalisee = None


# ---------------------------------------------------------------------------
# LA COUPE — lue, jamais recopiée
# ---------------------------------------------------------------------------

def test_la_coupe_est_CELLE_QUE_LE_PRODUIT_APPLIQUE(db_session):
    """⚠️ *Un outil qui écrirait `5` en dur annoncerait « sous la coupe » sur
    une coupe qui aurait changé.* **Vérifié par le comportement, pas par la
    signature relue une seconde fois.**"""
    from falkye.sources.req import resolve_neq_by_name

    for i in range(8):
        db_session.add(REQEntry(neq=f"110000000{i}", nom="Savonnerie Omega inc",
                                nom_normalise=normaliser("Savonnerie Omega inc"),
                                statut="radiee"))
    db_session.commit()
    matches = resolve_neq_by_name(db_session, "Savonnerie Omega inc")
    assert len(matches) == outil.coupe_de_production()


# ---------------------------------------------------------------------------
# L'ORDRE DES CAUSES — c'est lui qui porte le raisonnement
# ---------------------------------------------------------------------------

def _paire(concurrents, neq_retenu):
    return {"neq": neq_retenu, "_concurrents": concurrents,
            "_faits_du_dossier": _faits(DOSSIER)}


def test_l_ETABLISSEMENT_passe_AVANT_un_concurrent_compatible():
    """⚠️ **① dissout la contradiction; ② ne fait que la déplacer.** *Chercher ②
    d'abord ferait accuser un concurrent là où le registre portait simplement le
    domicile.*"""
    retenu = _Match("A", 100.0, AILLEURS, "immatriculee")
    rival = _Match("B", 100.0, DOSSIER)
    cause, piece = outil.cause_de_la_contradiction(
        _paire([retenu, rival], "A"), {"A": [_faits(DOSSIER)]}, [], 5)
    assert cause == outil.ETABLISSEMENT_DU_RETENU
    assert piece is None


def test_un_concurrent_DU_LOT_qui_porte_l_adresse_est_nomme():
    retenu = _Match("A", 100.0, AILLEURS, "immatriculee")
    rival = _Match("B", 100.0, DOSSIER)
    cause, piece = outil.cause_de_la_contradiction(
        _paire([retenu, rival], "A"), {}, [], 5)
    assert cause == outil.COMPATIBLE_DANS_LE_LOT
    assert piece is rival, "la pièce à conviction est RENDUE, pas seulement comptée"


@pytest.mark.parametrize("rang_du_compatible, attendu", [
    (2, outil.COMPATIBLE_SOUS_LE_LOT),      # dans les cinq, écarté par l'écart
    (5, outil.COMPATIBLE_SOUS_LA_COUPE),    # ⚠️ la réserve n° 3
])
def test_l_ECART_et_la_COUPE_sont_DEUX_causes_distinctes(rang_du_compatible, attendu):
    """⚠️ *« Le nom l'a mis hors concours » et « le lot l'a coupé » appellent
    deux correctifs différents* — l'écart de 8 d'un côté, le plafond de cinq de
    l'autre."""
    retenu = _Match("A", 100.0, AILLEURS, "immatriculee")
    profonds = [_Match(f"P{i}", 100.0 - i, AILLEURS) for i in range(8)]
    profonds[rang_du_compatible] = _Match(
        f"P{rang_du_compatible}", 100.0 - rang_du_compatible, DOSSIER)
    cause, piece = outil.cause_de_la_contradiction(
        _paire([retenu], "A"), {}, profonds, 5)
    assert cause == attendu
    assert piece.entry.neq == f"P{rang_du_compatible}"


def test_sans_etablissement_ni_candidat_compatible_la_cause_est_AUCUNE():
    retenu = _Match("A", 100.0, AILLEURS, "immatriculee")
    cause, piece = outil.cause_de_la_contradiction(
        _paire([retenu], "A"), {}, [_Match("P", 90.0, AILLEURS)], 5)
    assert cause == outil.SANS_EXPLICATION
    assert piece is None


def test_un_candidat_SANS_code_postal_ne_porte_PAS_l_adresse():
    """⚠️ **« Je ne sais pas » n'est pas « oui ».** *Sans cette garde, tout
    candidat au registre incomplet deviendrait un suspect.*"""
    assert not outil.porte_ladresse(_faits(DOSSIER), _faits(None))
    assert outil.porte_ladresse(_faits(DOSSIER), _faits(DOSSIER))


def test_la_colonne_tient_TOUTES_ses_etiquettes():
    for texte in outil.CAUSES + outil.ETIQUETTES:
        assert len(texte) < outil.LARGEUR, texte


# ---------------------------------------------------------------------------
# LA PROVENANCE DES ÉTABLISSEMENTS — rendue, jamais devinée
# ---------------------------------------------------------------------------

def test_l_etat_du_moteur_REPOND_EN_PREMIER(db_session):
    db_session.add(EtatLigneSource(
        source_id=outil.PARTITION_DES_ETABLISSEMENTS, cle_naturelle="1100000001|01",
        empreinte="x", donnees_normalisees={"adresse": None, "ville": "Trois-Rivieres",
                                            "code_postal": DOSSIER}))
    db_session.add(REQEtablissementEntry(neq="1100000001", no_suf_etab="01",
                                         code_postal=AILLEURS))
    db_session.commit()
    par_neq, provenance, pourvus = outil.faits_des_etablissements(
        db_session, {"1100000001"})
    assert provenance == outil.ETAT_DU_MOTEUR
    assert pourvus == 1
    assert outil.porte_ladresse(_faits(DOSSIER), par_neq["1100000001"][0]), \
        "c'est bien l'état COURANT qui a répondu, pas le miroir gelé"


def test_le_miroir_GELE_ne_repond_QUE_si_l_etat_est_vide(db_session):
    db_session.add(REQEtablissementEntry(neq="1100000002", no_suf_etab="01",
                                         code_postal=DOSSIER))
    db_session.commit()
    _par_neq, provenance, pourvus = outil.faits_des_etablissements(
        db_session, {"1100000002"})
    assert provenance == outil.MIROIR_GELE
    assert "GELÉ" in provenance, "le millésime est DIT, pas deviné"
    assert pourvus == 1


def test_aucune_source_se_DIT(db_session):
    par_neq, provenance, pourvus = outil.faits_des_etablissements(
        db_session, {"1100000003"})
    assert (par_neq, provenance, pourvus) == ({}, outil.AUCUNE_SOURCE, 0)


# ---------------------------------------------------------------------------
# LA MESURE, DE BOUT EN BOUT
# ---------------------------------------------------------------------------

@pytest.fixture()
def decor(db_session, monkeypatch):
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")

    dossiers = [
        # ① l'adresse exclut tous, MAIS le retenu a un établissement au dossier
        ("Fromagerie Zeta inc", DOSSIER,
         [("Fromagerie Zeta inc", "immatriculee", "1200000001", AILLEURS),
          ("Fromagerie Zeta inc", "radiee", "1200000002", AILLEURS)]),
        # ② l'adresse désigne un AUTRE candidat du lot
        ("Brasserie Kappa inc", DOSSIER,
         [("Brasserie Kappa inc", "immatriculee", "1200000003", AILLEURS),
          ("Brasserie Kappa inc", "radiee", "1200000004", DOSSIER)]),
        # ⑤ rien n'explique
        ("Menuiserie Sigma inc", DOSSIER,
         [("Menuiserie Sigma inc", "immatriculee", "1200000005", AILLEURS),
          ("Menuiserie Sigma inc", "radiee", "1200000006", AILLEURS)]),
    ]
    for nom, code_postal, au_registre in dossiers:
        company = Company(neq=None, nom_detecte=nom,
                          nom_detecte_normalise=normaliser(nom),
                          code_postal=code_postal,
                          statut_resolution=StatutResolution.AMBIGU,
                          first_detected_at=_dt.datetime(2026, 1, 1))
        db_session.add(company)
        db_session.flush()
        db_session.add(Signal(company_id=company.id, source_id="seao",
                              signal_type_id="recrutement_massif",
                              detected_at=_dt.datetime(2026, 1, 1), champs={}))
        for nom_req, statut, neq, cp in au_registre:
            db_session.add(REQEntry(neq=neq, nom=nom_req,
                                    nom_normalise=normaliser(nom_req),
                                    statut=statut, ville=None, code_postal=cp))
    db_session.add(EtatLigneSource(
        source_id=outil.PARTITION_DES_ETABLISSEMENTS,
        cle_naturelle="1200000001|02", empreinte="x",
        donnees_normalisees={"adresse": None, "ville": None, "code_postal": DOSSIER}))
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def test_la_mesure_N_ECRIT_RIEN_et_rend_les_trois_causes(decor, capsys):
    avant = {c.id: c.neq for c in decor.query(Company).all()}
    assert outil.main(["--pas", "0", "--paires", "3"]) == 0
    sortie = capsys.readouterr().out
    assert {c.id: c.neq for c in decor.query(Company).all()} == avant
    assert "RIEN N'A ÉTÉ ÉCRIT" in sortie
    from tests.conftest import compte_de_la_ligne

    for cause, attendu in ((outil.ETABLISSEMENT_DU_RETENU, "1"),
                           (outil.COMPATIBLE_DANS_LE_LOT, "1"),
                           (outil.SANS_EXPLICATION, "1")):
        ligne = next(l for l in sortie.splitlines() if l.strip().startswith(cause))
        assert compte_de_la_ligne(ligne) == attendu, ligne


def test_les_DEUX_familles_de_contradiction_sont_comptees_A_PART(decor, capsys):
    """⚠️ *« Désigne un autre » juge le RETENU; « les exclut tous » juge le
    LOT.* **Les additionner surdit ce qu'on sait.**"""
    assert outil.main(["--pas", "0"]) == 0
    sortie = capsys.readouterr().out
    from tests.conftest import compte_de_la_ligne

    autre = next(l for l in sortie.splitlines()
                 if l.strip().startswith(outil.ETIQUETTES[1].strip()))
    tous = next(l for l in sortie.splitlines()
                if l.strip().startswith(outil.ETIQUETTES[2].strip()))
    assert compte_de_la_ligne(autre) == "1", autre
    assert compte_de_la_ligne(tous) == "2", tous


def test_le_cout_d_un_garde_fou_permanent_est_DIT(decor, capsys):
    assert outil.main(["--pas", "0"]) == 0
    sortie = capsys.readouterr().out
    assert "CE QUE COÛTERAIT UN GARDE-FOU PERMANENT" in sortie
    assert "n'est pas un garde-fou" in sortie


def test_la_ville_JAMAIS_consultee_est_dite_avant_les_chiffres(decor, capsys):
    """⚠️ *« Le fait les exclut tous » ferme le repli par conception* — un
    lecteur qui l'ignore croit que la ville a été prise en compte."""
    assert outil.main(["--pas", "0"]) == 0
    sortie = capsys.readouterr().out
    assert sortie.index("la VILLE n'a jamais été consultée") < sortie.index(
        "dossiers que la règle poserait")
