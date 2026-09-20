"""L'écriture du départage par le statut — égalités strictes seulement.

⚠️ **Ce que ces tests verrouillent : que la PORTÉE soit bien celle qui a été
décidée.** *« Égalité stricte » et « le statut ne contredit aucun gagnant » ne
sont pas la même population* — une égalité entre deux radiées laisse un restant
SOUS le sommet. **Sans la seconde condition, une partie de ce qu'Alexandre a mis
en suspens serait écrite.**
"""
from __future__ import annotations

import datetime as _dt
import json

import pytest

from falkye.models.company import Company, StatutResolution
from falkye.models.req_entry import REQEntry
from falkye.models.signal import Signal
from falkye.sources.column_mapping import normaliser
from outils import ecriture_du_statut as outil


class _Match:
    def __init__(self, statut, score, neq=None):
        self.entry = type("E", (), {"statut": statut, "neq": neq or f"1{int(score)}",
                                    "nom": "x", "ville": None})()
        self.score = score


# ---------------------------------------------------------------------------
# LA CONDITION DOUBLE — c'est elle qui porte la décision
# ---------------------------------------------------------------------------

def test_une_egalite_entre_DEUX_RADIEES_laisse_un_restant_SOUS_le_sommet():
    """⚠️ **La réserve, vérifiée.** *Le dossier EST une égalité stricte, et le
    statut y retient pourtant un candidat sous les premiers ex æquo.* **C'est
    exactement le cas laissé en suspens, et la première condition ne l'exclut
    pas.**"""
    groupe = [_Match("radiee", 100.0), _Match("radiee", 100.0),
              _Match("immatriculee", 95.0)]
    from outils.statut_sur_les_egalites import ex_aequo

    assert len(ex_aequo(groupe)) >= 2, "c'est bien une égalité stricte"
    raison, _seul = outil.ce_qui_bloque(groupe, groupe)
    assert raison == outil.SOUS_LE_SOMMET


@pytest.mark.parametrize("statuts_scores, attendu", [
    ([("immatriculee", 100.0), ("radiee", 100.0)], None),
    ([("immatriculee", 100.0), ("radiee", 95.0)], outil.PAS_UNE_EGALITE),
    ([("radiee", 100.0), ("radiee", 100.0)], outil.LOT_VIDE),
    ([("immatriculee", 100.0), ("ni", 100.0)], outil.PAS_UN_SEUL),
    # ⚠️ Un `ni` seul survivant AU sommet : la forme retenue le garde.
    ([("ni", 100.0), ("radiee", 100.0)], None),
])
def test_les_deux_conditions_dans_l_ordre(statuts_scores, attendu):
    groupe = [_Match(s, sc) for s, sc in statuts_scores]
    raison, _ = outil.ce_qui_bloque(groupe, groupe)
    assert raison == attendu


def test_la_forme_retenue_est_celle_qu_ALEXANDRE_a_tranchee():
    from outils.statut_sur_les_egalites import ECARTER_RADIEES

    assert outil.FORME_QUI_SECRIT is ECARTER_RADIEES


def test_le_chemin_de_l_instantane_est_EMPRUNTE_et_plus_recopie():
    """⚠️ *Il était recopié dans trois outils. Une constante recopiée diverge
    sans que rien ne le dise.*"""
    from outils import (
        ecriture_des_departages,
        pose_du_neq,
        promotion_ville,
        reresolution_neq,
    )

    for module in (outil, ecriture_des_departages, promotion_ville, reresolution_neq):
        assert module.DOSSIER_INSTANTANE is pose_du_neq.DOSSIER_INSTANTANE, module


# ---------------------------------------------------------------------------
# L'ÉCRITURE, DE BOUT EN BOUT
# ---------------------------------------------------------------------------

@pytest.fixture()
def decor(db_session, monkeypatch):
    """Un dossier par cas de figure, plus un NEQ déjà porté."""
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")

    #: (nom, [(nom au registre, statut, neq)])
    dossiers = [
        # ✅ égalité stricte, le survivant EST au sommet → à poser
        ("Pecheries Alpha inc", [("Pecheries Alpha inc", "immatriculee", "1100000001"),
                                 ("Pecheries Alpha inc", "radiee", "1100000002")]),
        # ⛔ égalité entre deux radiées → le restant est SOUS le sommet
        ("Pecheries Beta inc", [("Pecheries Beta inc", "radiee", "1100000003"),
                                ("Pecheries Beta inc", "radiee", "1100000004"),
                                ("Pecheries Beta", "immatriculee", "1100000005")]),
        # ⛔ pas une égalité
        ("Pecheries Gamma inc", [("Pecheries Gamma inc", "immatriculee", "1100000006"),
                                 ("Pecheries Gamma", "radiee", "1100000007")]),
        # ⛔ lot vidé
        ("Pecheries Delta inc", [("Pecheries Delta inc", "radiee", "1100000008"),
                                 ("Pecheries Delta inc", "radiee", "1100000009")]),
    ]
    for nom, au_registre in dossiers:
        company = Company(neq=None, nom_detecte=nom,
                          nom_detecte_normalise=normaliser(nom),
                          statut_resolution=StatutResolution.AMBIGU,
                          first_detected_at=_dt.datetime(2026, 1, 1))
        db_session.add(company)
        db_session.flush()
        db_session.add(Signal(
            company_id=company.id, source_id="seao",
            signal_type_id="recrutement_massif",
            detected_at=_dt.datetime(2026, 1, 1), champs={}))
        for nom_req, statut, neq in au_registre:
            db_session.add(REQEntry(neq=neq, nom=nom_req,
                                    nom_normalise=normaliser(nom_req),
                                    statut=statut, ville=None))
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def _sortie(capsys):
    return capsys.readouterr().out


def test_RAPPORT_SEUL_par_defaut_rien_n_est_ecrit(decor, capsys):
    avant = {c.id: c.neq for c in decor.query(Company).all()}
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    assert "RAPPORT SEUL — rien n'a été écrit" in sortie
    assert {c.id: c.neq for c in decor.query(Company).all()} == avant


def test_la_seconde_condition_est_dite_AVANT_les_chiffres(decor, capsys):
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    assert sortie.index("QUI N'EST PAS REDONDANTE") < sortie.index("ambigus rejoués")
    assert "vérifié en exécutant le code" in sortie


def test_la_reserve_sur_la_radiation_reste_dans_la_sortie(decor, capsys):
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    assert "UNE ENTREPRISE RADIÉE PEUT ÊTRE LA BONNE" in sortie
    assert "AUCUNE\n   date de radiation" in sortie


def test_les_suspendus_sont_comptes_PAR_RAISON(decor, capsys):
    """⚠️ *Un outil qui écrit une partie doit dire lesquels il n'a pas
    touchés.*"""
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    for raison in outil.RAISONS:
        ligne = next(l for l in sortie.splitlines() if l.strip().startswith(raison))
        assert ligne, raison
    assert "LAISSÉS EN SUSPENS, ET NON REFUSÉS : 3" in sortie
    assert "sinon la différence se lit comme une perte" in sortie


def test_seul_le_dossier_aux_DEUX_conditions_est_a_poser(decor, capsys):
    assert outil.main(["--pas", "0", "--comparer", "5"]) == 0
    sortie = _sortie(capsys)
    bloc = sortie.split("CE QUI SERAIT ÉCRIT")[1]
    assert "Pecheries Alpha inc" in bloc
    for autre in ("Pecheries Beta", "Pecheries Gamma", "Pecheries Delta"):
        assert autre not in bloc, autre


def test_appliquer_ECRIT_et_l_instantane_porte_l_etat_d_avant(decor, capsys, tmp_path):
    assert outil.main(["--pas", "0", "--appliquer",
                       "--instantane", str(tmp_path)]) == 0
    sortie = _sortie(capsys)
    assert "NEQ posés                  : 1" in sortie
    pose = next(c for c in decor.query(Company).all()
                if c.nom_detecte == "Pecheries Alpha inc")
    assert pose.neq == "1100000001", "le survivant immatriculé"
    # ⚠️ L'instantané est écrit AVANT le commit, et porte l'état d'avant.
    instantanes = list(tmp_path.glob("statut-*.json"))
    assert len(instantanes) == 1, instantanes
    contenu = json.loads(instantanes[0].read_text(encoding="utf-8"))
    assert contenu["forme"] == outil.FORME_QUI_SECRIT
    paire = contenu["a_poser"][0]
    assert paire["neq_avant"] is None
    assert paire["statut_avant"] == StatutResolution.AMBIGU.value
    assert "_concurrents" not in paire, "les champs de travail ne sont pas écrits"


def test_defaire_remet_l_etat_d_avant(decor, capsys, tmp_path):
    assert outil.main(["--pas", "0", "--appliquer",
                       "--instantane", str(tmp_path)]) == 0
    capsys.readouterr()
    chemin = next(iter(tmp_path.glob("statut-*.json")))
    assert outil.main(["--defaire", str(chemin)]) == 0
    assert "défaits      : 1" in _sortie(capsys)
    pose = next(c for c in decor.query(Company).all()
                if c.nom_detecte == "Pecheries Alpha inc")
    assert pose.neq is None


def test_un_NEQ_deja_porte_n_est_PAS_pose_et_les_deux_dossiers_restent(
        decor, capsys, tmp_path):
    """*Le rapprochement est journalisé; aucun dossier ne disparaît.*"""
    detenteur = Company(neq="1100000001", nom_detecte="Déjà résolu inc.",
                        nom_detecte_normalise=normaliser("Déjà résolu inc."))
    decor.add(detenteur)
    decor.commit()
    combien_avant = decor.query(Company).count()

    assert outil.main(["--pas", "0", "--appliquer",
                       "--instantane", str(tmp_path)]) == 0
    sortie = _sortie(capsys)
    assert "NEQ posés                  : 0" in sortie
    assert "rapprochements journalisés : 1" in sortie
    assert decor.query(Company).count() == combien_avant, "aucun dossier perdu"
    reste = next(c for c in decor.query(Company).all()
                 if c.nom_detecte == "Pecheries Alpha inc")
    assert reste.neq is None, "le dossier garde son absence de NEQ"


def test_les_suspendus_se_lisent_un_par_un(decor, capsys):
    assert outil.main(["--pas", "0", "--suspendus", "10"]) == 0
    bloc = _sortie(capsys).split("LES DOSSIERS EN SUSPENS")[1]
    assert outil.SOUS_LE_SOMMET in bloc
    assert "Pecheries Beta inc" in bloc


def test_aucune_etiquette_de_raison_ne_depasse_sa_colonne():
    """*Cinquième occurrence du défaut, évitée plutôt que corrigée.*"""
    trop = [r for r in outil.RAISONS if len(r) > outil.LARGEUR_DUNE_RAISON]
    assert not trop, trop
