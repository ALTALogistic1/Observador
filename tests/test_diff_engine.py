"""Tests du moteur de diff générique et de la quarantaine (Chantier 1, spec
section 8bis — audit du 2026-09-03, faille E). Les 14 tests exigés par le
mandat (docs/spec/falkye-chantier-1-quarantaine.md, section "Tests exigés"),
plus des tests unitaires supplémentaires sur les briques internes."""
import os

import pytest

import falkye.diff_engine as diff_engine_module
from falkye.diff_engine import (
    SEUIL_ERREUR_LECTURE_DEFAUT,
    SeuilsQuarantaine,
    SeuilType,
    LigneSnapshot,
    calculer_empreinte,
    executer_diff,
    lever_quarantaine,
    lister_quarantaines,
    seuils_depuis_registre,
    suspicion_incident_local,
)
from falkye.models.diff_quarantaine import DiffQuarantaine, MotifQuarantaine, StatutQuarantaine
from falkye.models.etat_diff_source import EtatLigneSource

CHAMPS_PERTINENTS = {"nom", "capacite"}
COLONNES = {"nom": "str", "capacite": "int", "adresse": "str"}


@pytest.fixture(autouse=True)
def _archive_dans_tmp(tmp_path, monkeypatch):
    """L'archivage du diff (falkye/diff_engine.py::_archiver_snapshot) écrit
    de vrais fichiers sur disque — redirigé vers un répertoire temporaire
    pour chaque test plutôt que de polluer ./cache réel."""
    monkeypatch.setattr(diff_engine_module, "ARCHIVE_DIR", tmp_path / "diff_archive")


def _ligne(cle, nom, capacite, adresse="123 rue Test"):
    return LigneSnapshot(cle=cle, champs={"nom": nom, "capacite": capacite})


# --- 1. Run de référence ---


def test_run_reference_amorce_etat_sans_notification_ni_quarantaine(db_session):
    lignes = [_ligne(f"c{i}", f"Entreprise {i}", 50) for i in range(20)]
    rapport = executer_diff(db_session, "racj", lignes, COLONNES, CHAMPS_PERTINENTS)

    assert rapport.run_reference is True
    assert rapport.quarantaine is False
    assert rapport.resultat is None  # aucun candidat émis
    assert db_session.query(EtatLigneSource).filter_by(source_id="racj").count() == 20
    assert db_session.query(DiffQuarantaine).count() == 0


def test_run_reference_avec_cles_dupliquees_dedoublonne_sans_lever_d_erreur(db_session):
    """Régression réelle (macro-vérification chantier 1, licences Toronto) :
    ~0,5% des lignes brutes du vrai jeu de données portaient une clé
    naturelle STRICTEMENT dupliquée (lignes identiques) — un INSERT en lot
    (falkye/diff_engine.py::_inserer_lignes_en_lot) rejetait le lot ENTIER
    (contrainte UNIQUE source_id+cle_naturelle), contrairement à un ORM
    add() par ligne qui aurait simplement produit deux lignes distinctes en
    conflit au flush. Le run de référence doit dédoublonner AVANT
    l'insertion (garder la dernière occurrence) et le signaler en
    avertissement, jamais planter."""
    lignes = [_ligne("c1", "Entreprise A", 50), _ligne("c1", "Entreprise A", 50), _ligne("c2", "Entreprise B", 10)]
    rapport = executer_diff(db_session, "racj", lignes, COLONNES, CHAMPS_PERTINENTS)

    assert rapport.run_reference is True
    assert db_session.query(EtatLigneSource).filter_by(source_id="racj").count() == 2  # dédoublonné, pas 3
    assert any("clé naturelle en double" in a for a in rapport.avertissements)


# --- 2. Run normal ---


def test_run_normal_trois_apparitions_produisent_trois_candidats(db_session):
    executer_diff(db_session, "racj", [_ligne("c1", "A", 10)], COLONNES, CHAMPS_PERTINENTS)  # référence

    lignes = [_ligne("c1", "A", 10), _ligne("c2", "B", 20), _ligne("c3", "C", 30), _ligne("c4", "D", 40)]
    rapport = executer_diff(db_session, "racj", lignes, COLONNES, CHAMPS_PERTINENTS)

    assert rapport.run_reference is False
    assert rapport.quarantaine is False
    assert len(rapport.resultat.apparitions) == 3
    assert {a.cle for a in rapport.resultat.apparitions} == {"c2", "c3", "c4"}
    assert db_session.query(EtatLigneSource).filter_by(source_id="racj").count() == 4


# --- 3. Diff aberrant ---


def test_diff_aberrant_60_pourcent_met_en_quarantaine(db_session):
    lignes_ref = [_ligne(f"c{i}", f"Entreprise {i}", 50) for i in range(100)]
    executer_diff(db_session, "racj", lignes_ref, COLONNES, CHAMPS_PERTINENTS)

    # 60 clés changent (40 conservées, 60 nouvelles) — dépasse largement les
    # seuils par défaut (apparitions 50%/500... mais ABS=500 non atteint avec
    # ce volume : utiliser des seuils explicites pour ce test, réalistes pour
    # une source de cette taille).
    seuils = SeuilsQuarantaine(
        apparitions=SeuilType(pct=50.0, abs=50),
        disparitions=SeuilType(pct=30.0, abs=30),
        modifications=SeuilType(pct=50.0, abs=50),
    )
    lignes_suivantes = [_ligne(f"c{i}", f"Entreprise {i}", 50) for i in range(40, 160)]
    rapport = executer_diff(db_session, "racj", lignes_suivantes, COLONNES, CHAMPS_PERTINENTS, seuils=seuils)

    assert rapport.quarantaine is True
    assert rapport.resultat is None  # zéro notification
    # État précédent intact — toujours les 100 lignes d'origine.
    assert db_session.query(EtatLigneSource).filter_by(source_id="racj").count() == 100
    q = db_session.query(DiffQuarantaine).filter_by(source_id="racj").one()
    assert q.statut == StatutQuarantaine.EN_ATTENTE
    assert q.chemin_archive is not None
    assert os.path.exists(q.chemin_archive)  # diff archivé et consultable


# --- 4. Petite source : seuil absolu non atteint ---


def test_petite_source_60_pourcent_sur_20_lignes_pas_de_quarantaine(db_session):
    lignes_ref = [_ligne(f"c{i}", f"E{i}", 10) for i in range(20)]
    executer_diff(db_session, "petite_source", lignes_ref, COLONNES, CHAMPS_PERTINENTS)

    # 12 nouvelles clés sur 20 (60%) — sous le seuil ABSOLU par défaut (500).
    lignes_suivantes = [_ligne(f"c{i}", f"E{i}", 10) for i in range(8, 20)]
    rapport = executer_diff(db_session, "petite_source", lignes_suivantes, COLONNES, CHAMPS_PERTINENTS)

    assert rapport.quarantaine is False
    assert db_session.query(DiffQuarantaine).count() == 0


# --- 5. Colonne pertinente retirée ---


def test_colonne_pertinente_retiree_quarantaine_immediate_peu_importe_volume(db_session):
    lignes_ref = [_ligne("c1", "A", 10)]
    executer_diff(db_session, "racj", lignes_ref, COLONNES, CHAMPS_PERTINENTS)

    colonnes_sans_capacite = {"nom": "str", "adresse": "str"}  # "capacite" retirée, PERTINENTE
    # champs_pertinents reste la même constante déclarée au registre à chaque
    # appel (JAMAIS réduite pour "suivre" ce qui a disparu) — c'est la
    # comparaison entre colonnes_vues et l'état de schéma précédent qui
    # révèle la disparition, pas ce paramètre. Un seul enregistrement
    # identique par ailleurs — volume minimal, jamais assez pour déclencher
    # la quarantaine par le seuil de volume seul.
    rapport = executer_diff(
        db_session, "racj", [LigneSnapshot(cle="c1", champs={"nom": "A"})],
        colonnes_sans_capacite, CHAMPS_PERTINENTS,
    )

    assert rapport.quarantaine is True
    assert rapport.motif_quarantaine == MotifQuarantaine.SCHEMA_COLONNE_RETIREE


# --- 6. Colonne non pertinente ajoutée ---


def test_colonne_non_pertinente_ajoutee_pas_de_quarantaine_avertissement_journalise(db_session):
    lignes_ref = [_ligne("c1", "A", 10)]
    executer_diff(db_session, "racj", lignes_ref, COLONNES, CHAMPS_PERTINENTS)

    colonnes_plus_une = dict(COLONNES, nouvelle_colonne="str")
    rapport = executer_diff(db_session, "racj", [_ligne("c1", "A", 10)], colonnes_plus_une, CHAMPS_PERTINENTS)

    assert rapport.quarantaine is False
    assert any("nouvelle_colonne" in a for a in rapport.avertissements)


# --- 7. Changement cosmétique hors champs_pertinents ---


def test_changement_cosmetique_hors_champs_pertinents_zero_modification(db_session):
    executer_diff(db_session, "racj", [_ligne("c1", "A", 10, adresse="1 rue X")], COLONNES, CHAMPS_PERTINENTS)

    # L'adresse change, mais "adresse" n'est PAS dans champs_pertinents —
    # LigneSnapshot.champs ne la porte donc jamais, l'empreinte ne bouge pas.
    rapport = executer_diff(db_session, "racj", [_ligne("c1", "A", 10, adresse="2 rue Y")], COLONNES, CHAMPS_PERTINENTS)

    assert rapport.quarantaine is False
    assert len(rapport.resultat.modifications) == 0


# --- 8. Asymétrie apparitions/disparitions ---


def test_meme_pourcentage_asymetrique_selon_seuils_distincts(db_session):
    lignes_ref = [_ligne(f"c{i}", f"E{i}", 10) for i in range(100)]
    executer_diff(db_session, "racj_a", lignes_ref, COLONNES, CHAMPS_PERTINENTS)
    executer_diff(db_session, "racj_b", lignes_ref, COLONNES, CHAMPS_PERTINENTS)

    seuils = SeuilsQuarantaine(
        apparitions=SeuilType(pct=80.0, abs=50),   # apparitions : seuil ÉLEVÉ, ne se déclenche pas à 40%
        disparitions=SeuilType(pct=30.0, abs=30),  # disparitions : seuil BAS, se déclenche à 40%
        modifications=SeuilType(pct=80.0, abs=50),
    )

    # 40% d'apparitions (40 nouvelles sur 100 précédentes) — sous le seuil apparitions.
    rapport_apparitions = executer_diff(
        db_session, "racj_a", lignes_ref + [_ligne(f"n{i}", f"N{i}", 10) for i in range(40)],
        COLONNES, CHAMPS_PERTINENTS, seuils=seuils,
    )
    # 40% de disparitions (40 clés absentes sur 100 précédentes) — au-dessus du seuil disparitions.
    rapport_disparitions = executer_diff(
        db_session, "racj_b", lignes_ref[:60], COLONNES, CHAMPS_PERTINENTS, seuils=seuils
    )

    assert rapport_apparitions.quarantaine is False
    assert rapport_disparitions.quarantaine is True
    assert rapport_disparitions.motif_quarantaine == MotifQuarantaine.VOLUME_DISPARITIONS


# --- 9. Fichier illisible ---


def test_echec_lecture_au_dela_du_seuil_met_en_quarantaine_sans_exception(db_session):
    rapport = executer_diff(
        db_session, "racj", [], COLONNES, CHAMPS_PERTINENTS, taux_erreur_lecture=0.30,
    )
    assert rapport.quarantaine is True
    assert rapport.motif_quarantaine == MotifQuarantaine.LECTURE_ECHOUEE
    assert 0.30 > SEUIL_ERREUR_LECTURE_DEFAUT  # confirme que le taux dépasse bien le seuil par défaut utilisé


# --- 10. Isolation entre sources ---


def test_source_en_quarantaine_n_empeche_pas_une_autre_source_de_publier(db_session):
    executer_diff(db_session, "source_saine", [_ligne("c1", "A", 10)], COLONNES, CHAMPS_PERTINENTS)
    executer_diff(db_session, "source_malade", [_ligne("c1", "A", 10)], COLONNES, CHAMPS_PERTINENTS)

    rapport_malade = executer_diff(
        db_session, "source_malade", [], COLONNES, CHAMPS_PERTINENTS, taux_erreur_lecture=1.0
    )
    rapport_saine = executer_diff(
        db_session, "source_saine", [_ligne("c1", "A", 10), _ligne("c2", "B", 20)], COLONNES, CHAMPS_PERTINENTS
    )

    assert rapport_malade.quarantaine is True
    assert rapport_saine.quarantaine is False
    assert len(rapport_saine.resultat.apparitions) == 1


# --- 11. Question 1 : deux quarantaines simultanées ---


def test_deux_quarantaines_meme_execution_declenche_alerte_incident_local(db_session):
    executer_diff(db_session, "src_a", [_ligne("c1", "A", 10)], COLONNES, CHAMPS_PERTINENTS)
    executer_diff(db_session, "src_b", [_ligne("c1", "A", 10)], COLONNES, CHAMPS_PERTINENTS)

    r1 = executer_diff(db_session, "src_a", [], COLONNES, CHAMPS_PERTINENTS, taux_erreur_lecture=1.0)
    r2 = executer_diff(db_session, "src_b", [], COLONNES, CHAMPS_PERTINENTS, taux_erreur_lecture=1.0)
    r3 = executer_diff(db_session, "src_c_jamais_vue", [_ligne("c1", "A", 10)], COLONNES, CHAMPS_PERTINENTS)

    assert r1.quarantaine and r2.quarantaine  # deux incidents indépendants
    assert not r3.quarantaine  # troisième source, saine, pas affectée
    assert suspicion_incident_local([r1, r2, r3]) is True
    assert suspicion_incident_local([r1, r3]) is False  # une seule quarantaine — pas de suspicion


# --- 12. Question 2 : rien d'un run en quarantaine n'entre au dossier cumulatif ---


def test_run_en_quarantaine_ne_produit_aucun_candidat_ni_etat(db_session):
    executer_diff(db_session, "racj", [_ligne("c1", "Entreprise A", 10)], COLONNES, CHAMPS_PERTINENTS)
    etat_avant = {
        (e.cle_naturelle, e.empreinte)
        for e in db_session.query(EtatLigneSource).filter_by(source_id="racj").all()
    }

    seuils = SeuilsQuarantaine(
        apparitions=SeuilType(pct=10.0, abs=1), disparitions=SeuilType(pct=10.0, abs=1),
        modifications=SeuilType(pct=10.0, abs=1),
    )
    rapport = executer_diff(
        db_session, "racj", [_ligne("c1", "Entreprise A", 10), _ligne("c2", "Entreprise B", 99)],
        COLONNES, CHAMPS_PERTINENTS, seuils=seuils,
    )
    assert rapport.quarantaine is True
    assert rapport.resultat is None  # aucun candidat exposé à l'appelant — rien à corroborer

    etat_apres = {
        (e.cle_naturelle, e.empreinte)
        for e in db_session.query(EtatLigneSource).filter_by(source_id="racj").all()
    }
    assert etat_apres == etat_avant  # identique à si le run n'avait pas eu lieu
    assert "c2" not in {e.cle_naturelle for e in db_session.query(EtatLigneSource).filter_by(source_id="racj").all()}


# --- 13. Levée acceptée ---


def test_levee_acceptee_applique_le_diff_et_journalise(db_session):
    executer_diff(db_session, "racj", [_ligne("c1", "A", 10)], COLONNES, CHAMPS_PERTINENTS)
    rapport = executer_diff(
        db_session, "racj", [], COLONNES, CHAMPS_PERTINENTS, taux_erreur_lecture=1.0
    )
    q_id = rapport.quarantaine_id

    resultat = lever_quarantaine(
        db_session, q_id, decision="acceptee", qui="alexandre@exemple.com", motif="Vérifié manuellement, faux positif"
    )
    q = db_session.get(DiffQuarantaine, q_id)
    assert q.statut == StatutQuarantaine.ACCEPTEE
    assert q.levee_par == "alexandre@exemple.com"
    assert q.levee_le is not None
    assert q.levee_motif == "Vérifié manuellement, faux positif"
    assert resultat is not None


# --- 14. Levée rejetée ---


def test_levee_rejetee_conserve_etat_precedent(db_session):
    executer_diff(db_session, "racj", [_ligne("c1", "A", 10)], COLONNES, CHAMPS_PERTINENTS)
    etat_avant = db_session.query(EtatLigneSource).filter_by(source_id="racj").count()

    seuils = SeuilsQuarantaine(
        apparitions=SeuilType(pct=10.0, abs=1), disparitions=SeuilType(pct=10.0, abs=1),
        modifications=SeuilType(pct=10.0, abs=1),
    )
    rapport = executer_diff(
        db_session, "racj", [_ligne("c1", "A", 10), _ligne("c2", "B", 20)], COLONNES, CHAMPS_PERTINENTS,
        seuils=seuils,
    )

    resultat = lever_quarantaine(
        db_session, rapport.quarantaine_id, decision="rejetee", qui="alexandre@exemple.com", motif="Faux positif écarté"
    )
    assert resultat is None
    q = db_session.get(DiffQuarantaine, rapport.quarantaine_id)
    assert q.statut == StatutQuarantaine.REJETEE
    assert db_session.query(EtatLigneSource).filter_by(source_id="racj").count() == etat_avant

    # La prochaine exécution repart bien de l'état précédent (pas de "c2" fantôme).
    rapport_suivant = executer_diff(db_session, "racj", [_ligne("c1", "A", 10)], COLONNES, CHAMPS_PERTINENTS)
    assert rapport_suivant.quarantaine is False
    assert len(rapport_suivant.resultat.apparitions) == 0


# --- Tests unitaires additionnels sur les briques internes ---


def test_calculer_empreinte_stable_insensible_a_l_ordre_des_cles():
    a = calculer_empreinte({"nom": "A", "capacite": 10})
    b = calculer_empreinte({"capacite": 10, "nom": "A"})
    assert a == b


def test_calculer_empreinte_differente_si_valeur_differente():
    assert calculer_empreinte({"capacite": 10}) != calculer_empreinte({"capacite": 11})


def test_seuils_depuis_registre_repli_type_par_type():
    seuils = seuils_depuis_registre({"disparitions": {"pct": 15.0, "abs": 40}})
    assert seuils.disparitions.pct == 15.0
    assert seuils.disparitions.abs == 40
    # apparitions/modifications non surchargées -> repli sur SEUILS_DEFAUT
    from falkye.diff_engine import SEUILS_DEFAUT
    assert seuils.apparitions == SEUILS_DEFAUT.apparitions
    assert seuils.modifications == SEUILS_DEFAUT.modifications


def test_seuils_depuis_registre_none_retourne_defauts():
    from falkye.diff_engine import SEUILS_DEFAUT
    assert seuils_depuis_registre(None) == SEUILS_DEFAUT


def test_type_colonne_modifie_declenche_quarantaine(db_session):
    executer_diff(db_session, "racj", [_ligne("c1", "A", 10)], COLONNES, CHAMPS_PERTINENTS)
    colonnes_type_change = dict(COLONNES, capacite="str")  # "int" -> "str"
    rapport = executer_diff(db_session, "racj", [_ligne("c1", "A", 10)], colonnes_type_change, CHAMPS_PERTINENTS)
    assert rapport.quarantaine is True
    assert rapport.motif_quarantaine == MotifQuarantaine.SCHEMA_TYPE_MODIFIE


def test_lister_quarantaines_filtre_par_statut(db_session):
    executer_diff(db_session, "racj", [_ligne("c1", "A", 10)], COLONNES, CHAMPS_PERTINENTS)
    r = executer_diff(db_session, "racj", [], COLONNES, CHAMPS_PERTINENTS, taux_erreur_lecture=1.0)

    en_attente = lister_quarantaines(db_session, StatutQuarantaine.EN_ATTENTE)
    assert len(en_attente) == 1

    lever_quarantaine(db_session, r.quarantaine_id, decision="rejetee", qui="op", motif="test")
    assert lister_quarantaines(db_session, StatutQuarantaine.EN_ATTENTE) == []
    assert len(lister_quarantaines(db_session, StatutQuarantaine.REJETEE)) == 1


def test_lever_quarantaine_deja_traitee_leve_une_erreur(db_session):
    executer_diff(db_session, "racj", [_ligne("c1", "A", 10)], COLONNES, CHAMPS_PERTINENTS)
    r = executer_diff(db_session, "racj", [], COLONNES, CHAMPS_PERTINENTS, taux_erreur_lecture=1.0)
    lever_quarantaine(db_session, r.quarantaine_id, decision="rejetee", qui="op", motif="test")

    with pytest.raises(ValueError):
        lever_quarantaine(db_session, r.quarantaine_id, decision="acceptee", qui="op", motif="deuxième essai")
