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
    SpecificationDiff,
    calculer_empreinte,
    executer_diff,
    executer_diff_groupe,
    lever_quarantaine,
    lister_quarantaines,
    seuils_depuis_registre,
    suspicion_incident_local,
)
from falkye.diff_engine import proposer_seuils
from falkye.models.diff_quarantaine import DiffQuarantaine, MotifQuarantaine, StatutQuarantaine
from falkye.models.diff_run_historique import DiffRunHistorique
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


def _epuiser_periode_prudence(db_session, source_id, lignes):
    """Accumule NB_RUNS_MINIMUM_AVANT_SEUILS_NORMAUX runs non-référence sans
    écart (mêmes lignes à chaque fois) pour sortir la source de la période de
    prudence (seuils resserrés — voir diff_engine.py) avant le run réellement
    testé, quand un test veut isoler le comportement des seuils "normaux"."""
    for _ in range(diff_engine_module.NB_RUNS_MINIMUM_AVANT_SEUILS_NORMAUX):
        executer_diff(db_session, source_id, lignes, COLONNES, CHAMPS_PERTINENTS)


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
    # Seuils "normaux" (non resserrés) isolés du mécanisme de prudence de
    # début de vie — voir _epuiser_periode_prudence.
    _epuiser_periode_prudence(db_session, "racj_a", lignes_ref)
    _epuiser_periode_prudence(db_session, "racj_b", lignes_ref)

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


# --- Suivi d'Alexandre au premier livrable (2026-09-04) : dédoublonnage
# déterministe, journalisation systématique, prudence de début de vie,
# proposition de seuils jamais auto-appliquée ---


def test_dedoublonnage_deterministe_independant_de_l_ordre():
    a = _ligne("c1", "A", 10)
    b = _ligne("c1", "B", 20)  # même clé naturelle, contenu DIVERGENT
    resultat_ordre_1 = diff_engine_module._dedoublonner_lignes([a, b])
    resultat_ordre_2 = diff_engine_module._dedoublonner_lignes([b, a])  # ordre inversé

    assert resultat_ordre_1.lignes_par_cle["c1"] == resultat_ordre_2.lignes_par_cle["c1"]
    assert resultat_ordre_1.nb_doublons_divergents == 1
    assert resultat_ordre_1.nb_doublons_identiques == 0


def test_dedoublonnage_distingue_doublons_identiques_et_divergents(db_session):
    lignes = [
        _ligne("c1", "A", 10),
        _ligne("c1", "A", 10),  # doublon identique — inoffensif
        _ligne("c2", "B", 20),
        _ligne("c2", "C", 30),  # doublon DIVERGENT — ambiguïté réelle de clé
    ]
    rapport = executer_diff(db_session, "racj", lignes, COLONNES, CHAMPS_PERTINENTS)

    assert any("identique" in a for a in rapport.avertissements)
    assert any("DIVERGENT" in a for a in rapport.avertissements)

    historique = db_session.query(DiffRunHistorique).filter_by(source_id="racj").one()
    assert historique.nb_doublons_identiques == 1
    assert historique.nb_doublons_divergents == 1
    assert historique.taux_doublons == pytest.approx(2 / 4)


def test_historique_journalise_chaque_type_de_run(db_session):
    # Run de référence.
    executer_diff(db_session, "racj", [_ligne("c1", "A", 10)], COLONNES, CHAMPS_PERTINENTS)
    # Diff normal, accepté.
    executer_diff(db_session, "racj", [_ligne("c1", "A", 10), _ligne("c2", "B", 20)], COLONNES, CHAMPS_PERTINENTS)
    # Quarantaine de schéma.
    executer_diff(db_session, "racj", [_ligne("c1", "A", 10)], {"nom": "str"}, CHAMPS_PERTINENTS)
    # Quarantaine de lecture.
    executer_diff(db_session, "autre_source", [], COLONNES, CHAMPS_PERTINENTS, taux_erreur_lecture=1.0)

    lignes_hist = db_session.query(DiffRunHistorique).filter_by(source_id="racj").order_by(DiffRunHistorique.id).all()
    assert [h.run_reference for h in lignes_hist] == [True, False, False]
    assert [h.quarantaine for h in lignes_hist] == [False, False, True]
    assert lignes_hist[2].motif_quarantaine == MotifQuarantaine.SCHEMA_COLONNE_RETIREE.value

    hist_lecture = db_session.query(DiffRunHistorique).filter_by(source_id="autre_source").one()
    assert hist_lecture.quarantaine is True
    assert hist_lecture.motif_quarantaine == MotifQuarantaine.LECTURE_ECHOUEE.value
    assert hist_lecture.nb_apparitions is None  # jamais calculé — quarantaine avant tout diff


def test_seuils_resserres_tant_que_historique_insuffisant(db_session):
    """Le tout premier diff non-référence d'une source est jugé sous des
    seuils PLUS SERRÉS que SEUILS_DEFAUT — une amplitude qui ne
    déclencherait PAS la quarantaine une fois l'historique suffisant la
    déclenche ici, par prudence."""
    lignes_ref = [_ligne(f"c{i}", f"E{i}", 10) for i in range(100)]
    executer_diff(db_session, "racj", lignes_ref, COLONNES, CHAMPS_PERTINENTS)

    # 300 apparitions (300% des 100 lignes précédentes) : sous le seuil ABSOLU
    # de SEUILS_DEFAUT (500 — donc pas de quarantaine sous seuils normaux, où
    # les DEUX doivent être franchis), mais au-dessus du seuil absolu resserré
    # (250, x0.5) — le pourcentage (300%) franchit les deux seuils dans les
    # deux cas, c'est l'ABSOLU resserré qui fait toute la différence ici.
    rapport = executer_diff(
        db_session, "racj", lignes_ref + [_ligne(f"n{i}", f"N{i}", 10) for i in range(300)],
        COLONNES, CHAMPS_PERTINENTS,
    )
    assert rapport.quarantaine is True
    assert rapport.motif_quarantaine == MotifQuarantaine.VOLUME_APPARITIONS
    assert any("resserr" in a.lower() for a in rapport.avertissements)

    historique = (
        db_session.query(DiffRunHistorique)
        .filter_by(source_id="racj", run_reference=False)
        .order_by(DiffRunHistorique.id.desc())
        .first()
    )
    assert historique.seuils_prudence_debut is True
    assert historique.seuils_apparitions_pct == pytest.approx(diff_engine_module.SEUILS_DEFAUT.apparitions.pct * 0.5)


def test_seuils_normaux_une_fois_historique_suffisant(db_session):
    """La MÊME amplitude (300 apparitions) que le test précédent ne déclenche
    PLUS rien une fois l'historique suffisant accumulé — seuls les seuils
    resserrés du DÉBUT étaient en cause, jamais un seuil devenu plus
    permissif que SEUILS_DEFAUT."""
    lignes_ref = [_ligne(f"c{i}", f"E{i}", 10) for i in range(100)]
    executer_diff(db_session, "racj", lignes_ref, COLONNES, CHAMPS_PERTINENTS)
    _epuiser_periode_prudence(db_session, "racj", lignes_ref)

    rapport = executer_diff(
        db_session, "racj", lignes_ref + [_ligne(f"n{i}", f"N{i}", 10) for i in range(300)],
        COLONNES, CHAMPS_PERTINENTS,
    )
    assert rapport.quarantaine is False


def test_proposer_seuils_none_si_historique_insuffisant(db_session):
    lignes_ref = [_ligne(f"c{i}", f"E{i}", 10) for i in range(100)]
    executer_diff(db_session, "racj", lignes_ref, COLONNES, CHAMPS_PERTINENTS)
    executer_diff(db_session, "racj", lignes_ref, COLONNES, CHAMPS_PERTINENTS)  # 1 seul run non-référence

    assert proposer_seuils(db_session, "racj") is None


def test_proposer_seuils_propose_une_fois_assez_de_runs(db_session):
    lignes_ref = [_ligne(f"c{i}", f"E{i}", 10) for i in range(100)]
    executer_diff(db_session, "racj", lignes_ref, COLONNES, CHAMPS_PERTINENTS)
    _epuiser_periode_prudence(db_session, "racj", lignes_ref)  # 5 runs non-référence, amplitude 0%

    proposition = proposer_seuils(db_session, "racj")
    assert proposition is not None
    assert proposition.nb_runs_observes == diff_engine_module.NB_RUNS_MINIMUM_AVANT_SEUILS_NORMAUX
    # Amplitude normale observée = 0% partout -> seuil proposé au plancher (abs=1), jamais 0
    # (un seuil à 0 se déclencherait sur le moindre écart, y compris du bruit inoffensif).
    assert proposition.seuils_proposes.apparitions.abs >= 1
    assert proposition.seuils_proposes.apparitions.pct == pytest.approx(0.0)


def test_proposer_seuils_exclut_les_runs_en_quarantaine(db_session):
    """Un run mis en quarantaine ne doit JAMAIS élargir la proposition
    future — suivi d'Alexandre : « un seuil qui s'ajuste seul finit par
    s'élargir jusqu'à ne plus rien attraper »."""
    lignes_ref = [_ligne(f"c{i}", f"E{i}", 10) for i in range(100)]
    executer_diff(db_session, "racj", lignes_ref, COLONNES, CHAMPS_PERTINENTS)
    _epuiser_periode_prudence(db_session, "racj", lignes_ref)

    proposition_avant = proposer_seuils(db_session, "racj")

    # Un run massivement aberrant, mis en quarantaine — 600 apparitions
    # franchit même le seuil ABSOLU normal (500, la période de prudence est
    # déjà épuisée à ce stade par _epuiser_periode_prudence ci-dessus).
    lignes_aberrantes = lignes_ref + [_ligne(f"n{i}", f"N{i}", 10) for i in range(600)]
    rapport_aberrant = executer_diff(db_session, "racj", lignes_aberrantes, COLONNES, CHAMPS_PERTINENTS)
    assert rapport_aberrant.quarantaine is True

    proposition_apres = proposer_seuils(db_session, "racj")
    assert proposition_apres.seuils_proposes.apparitions.pct == proposition_avant.seuils_proposes.apparitions.pct
    assert proposition_apres.nb_runs_observes == proposition_avant.nb_runs_observes  # le run aberrant n'est PAS compté


# --- `apres_diff_accepte` : le moteur refuse l'émission en run de référence
# ou en quarantaine, sans dépendre de la discipline du connecteur (chantier
# 1, suivi 2026-09-04 — correction demandée par Alexandre après le constat
# réel sur licences_toronto/licences_vancouver, voir la docstring de module) ---


def test_executer_diff_verrouille_le_callback_absent_au_run_de_reference(db_session):
    appels = []
    lignes = [_ligne(f"c{i}", f"E{i}", 10) for i in range(20)]
    rapport = executer_diff(
        db_session, "racj", lignes, COLONNES, CHAMPS_PERTINENTS, apres_diff_accepte=appels.append
    )
    assert rapport.run_reference is True
    assert appels == []  # jamais invoqué — même si le connecteur ne vérifie rien lui-même


def test_executer_diff_verrouille_le_callback_absent_en_quarantaine_volume(db_session):
    appels = []
    lignes_ref = [_ligne(f"c{i}", f"E{i}", 10) for i in range(100)]
    executer_diff(db_session, "racj", lignes_ref, COLONNES, CHAMPS_PERTINENTS)
    _epuiser_periode_prudence(db_session, "racj", lignes_ref)

    lignes_aberrantes = [_ligne(f"n{i}", f"N{i}", 10) for i in range(600)]  # 100% de disparitions
    rapport = executer_diff(
        db_session, "racj", lignes_aberrantes, COLONNES, CHAMPS_PERTINENTS, apres_diff_accepte=appels.append
    )
    assert rapport.quarantaine is True
    assert appels == []


def test_executer_diff_verrouille_le_callback_absent_en_quarantaine_schema(db_session):
    appels = []
    executer_diff(db_session, "racj", [_ligne("c1", "A", 10)], COLONNES, CHAMPS_PERTINENTS)

    colonnes_sans_capacite = {"nom": "str", "adresse": "str"}
    rapport = executer_diff(
        db_session,
        "racj",
        [LigneSnapshot(cle="c1", champs={"nom": "A"})],
        colonnes_sans_capacite,
        CHAMPS_PERTINENTS,
        apres_diff_accepte=appels.append,
    )
    assert rapport.quarantaine is True
    assert appels == []


def test_executer_diff_verrouille_le_callback_absent_en_quarantaine_lecture(db_session):
    appels = []
    rapport = executer_diff(
        db_session,
        "racj",
        [_ligne("c1", "A", 10)],
        COLONNES,
        CHAMPS_PERTINENTS,
        taux_erreur_lecture=0.5,
        apres_diff_accepte=appels.append,
    )
    assert rapport.quarantaine is True
    assert appels == []


def test_executer_diff_invoque_le_callback_seulement_sur_diff_accepte(db_session):
    appels = []
    executer_diff(db_session, "racj", [_ligne("c1", "A", 10)], COLONNES, CHAMPS_PERTINENTS)  # référence

    lignes = [_ligne("c1", "A", 10), _ligne("c2", "B", 20)]
    rapport = executer_diff(
        db_session, "racj", lignes, COLONNES, CHAMPS_PERTINENTS, apres_diff_accepte=appels.append
    )
    assert rapport.quarantaine is False
    assert rapport.run_reference is False
    assert appels == [rapport]  # invoqué exactement une fois, avec CE rapport
    assert {a.cle for a in rapport.resultat.apparitions} == {"c2"}


def test_executer_diff_groupe_n_invoque_le_callback_que_si_tous_les_grains_sont_acceptes(db_session):
    """Régression directe du constat réel Toronto/Vancouver : un connecteur
    multi-grain (comme REQ : entreprise + établissements) ne doit jamais
    pouvoir publier sur la seule foi d'UN grain accepté si l'AUTRE est en
    quarantaine ou en référence — la décision conjointe est portée par
    `executer_diff_groupe`, jamais recomposée par l'appelant."""
    appels = []
    lignes_a = [_ligne("a1", "A", 10)]
    lignes_b = [_ligne("b1", "B", 10)]

    # Les deux grains à leur run de référence -> aucun appel.
    rapports = executer_diff_groupe(
        db_session,
        [
            SpecificationDiff("grain_a", lignes_a, COLONNES, CHAMPS_PERTINENTS),
            SpecificationDiff("grain_b", lignes_b, COLONNES, CHAMPS_PERTINENTS),
        ],
        apres_diff_accepte=appels.append,
    )
    assert all(r.run_reference for r in rapports)
    assert appels == []

    # Grain A accepté (une apparition), grain B en quarantaine (lecture) -> aucun appel,
    # même si le grain A pris isolément aurait publié.
    rapports = executer_diff_groupe(
        db_session,
        [
            SpecificationDiff("grain_a", lignes_a + [_ligne("a2", "A2", 10)], COLONNES, CHAMPS_PERTINENTS),
            SpecificationDiff("grain_b", lignes_b, COLONNES, CHAMPS_PERTINENTS, taux_erreur_lecture=1.0),
        ],
        apres_diff_accepte=appels.append,
    )
    assert rapports[0].quarantaine is False
    assert rapports[1].quarantaine is True
    assert appels == []

    # Les deux grains acceptés -> UN appel, avec la liste complète des deux rapports.
    rapports = executer_diff_groupe(
        db_session,
        [
            SpecificationDiff("grain_a", lignes_a + [_ligne("a3", "A3", 10)], COLONNES, CHAMPS_PERTINENTS),
            SpecificationDiff("grain_b", lignes_b + [_ligne("b2", "B2", 10)], COLONNES, CHAMPS_PERTINENTS),
        ],
        apres_diff_accepte=appels.append,
    )
    assert all(not r.quarantaine and not r.run_reference for r in rapports)
    assert appels == [rapports]


# --- 10. Forme de l'insertion en lot (chantier 29) ---
#
# Ces tests ne portent pas sur le RÉSULTAT de l'insertion — il est déjà couvert
# plus haut — mais sur la FORME des énoncés émis. Au distant, cette forme décide
# entre 8,7 minutes et 60 heures pour le même run de référence, et l'écart est
# rigoureusement invisible aux tests en mémoire : les deux formes passent, et
# aussi vite. D'où une vérification directe de ce qui part vers la base.


def _enonces_emis(db_session):
    """Enregistre chaque énoncé exécuté sur la connexion, avec son drapeau
    `executemany` — c'est CE drapeau qui distingue un aller-retour par ligne
    d'un énoncé multi-VALUES."""
    from sqlalchemy import event

    journal = []
    moteur = db_session.get_bind()

    def _ecouter(conn, cursor, enonce, parametres, contexte, executemany):
        journal.append((enonce, executemany, parametres))

    event.listen(moteur, "before_cursor_execute", _ecouter)
    return journal, lambda: event.remove(moteur, "before_cursor_execute", _ecouter)


def test_insertion_en_lot_emet_un_enonce_multi_values_jamais_un_par_ligne(db_session):
    """Régression du chantier 29, mesurée le 2026-09-04 contre la base distante
    réelle : `execute(insert(T), liste)` est un `executemany`, que le pilote
    libSQL exécute en UN ALLER-RETOUR HTTPS PAR LIGNE — 12 lignes/s, soit 60 h
    pour les 2,7 M lignes du REQ. `execute(insert(T).values(liste))` est un seul
    énoncé multi-VALUES : 5 174 lignes/s, 8,7 min. Même donnée, ×430.

    Le test interdit donc la première forme sur ce chemin."""
    journal, arreter = _enonces_emis(db_session)
    try:
        executer_diff(db_session, "racj", [_ligne(f"c{i}", f"E{i}", 1) for i in range(50)], COLONNES, CHAMPS_PERTINENTS)
    finally:
        arreter()

    insertions = [(e, many) for e, many, _ in journal if "INSERT INTO etat_ligne_source" in e]
    assert insertions, "aucune insertion observée — le test ne mesure plus rien"
    assert not any(many for _, many in insertions), (
        "l'insertion d'état passe par executemany : un aller-retour par ligne au distant"
    )
    assert len(insertions) == 1, f"50 lignes devraient tenir en UN énoncé, {len(insertions)} émis"
    # Un seul énoncé, mais bien 50 lignes dedans : autant de groupes de valeurs.
    assert insertions[0][0].count("(?") >= 50 or insertions[0][0].count("VALUES") == 1


def test_insertion_en_lot_decoupe_selon_le_budget_de_variables(db_session, monkeypatch):
    """Le lot se mesure en VARIABLES LIÉES, pas en lignes : SQLite refuse un
    énoncé au-delà de SQLITE_MAX_VARIABLE_NUMBER (32 766 mesuré côté distant).
    Avec un budget réduit à 12 variables et 6 variables par ligne, chaque
    énoncé doit porter exactement 2 lignes."""
    monkeypatch.setattr(diff_engine_module, "BUDGET_VARIABLES_INSERTION", 12)
    monkeypatch.setattr(diff_engine_module, "_variables_par_ligne", None)

    journal, arreter = _enonces_emis(db_session)
    try:
        executer_diff(db_session, "racj", [_ligne(f"c{i}", f"E{i}", 1) for i in range(7)], COLONNES, CHAMPS_PERTINENTS)
    finally:
        arreter()

    insertions = [p for e, _, p in journal if "INSERT INTO etat_ligne_source" in e]
    assert [len(p) // 6 for p in insertions] == [2, 2, 2, 1], "découpage attendu 2+2+2+1 pour 7 lignes"
    assert db_session.query(EtatLigneSource).filter_by(source_id="racj").count() == 7


def test_taille_de_lot_retrecit_si_le_modele_gagne_une_colonne(db_session):
    """Le garde-fou qui compte vraiment. Les 6 colonnes actuelles donnent
    30 000 variables pour 5 000 lignes — 9 % sous le mur du distant. Une
    colonne de plus ferait 35 000, donc « too many SQL variables », AU DISTANT
    SEULEMENT et jamais aux tests. La taille de lot doit donc se déduire du
    modèle plutôt que d'être un nombre de lignes figé."""
    par_ligne = diff_engine_module._variables_par_ligne_etat_ligne(db_session)
    assert par_ligne == 6, "le modèle a changé : vérifier que le lot rétrécit bien en conséquence"

    taille = diff_engine_module._taille_lot_insertion(db_session)
    assert taille * par_ligne <= 32_766, "le lot dépasserait SQLITE_MAX_VARIABLE_NUMBER au distant"

    # Une colonne de plus -> lot plus petit, produit toujours sous le mur.
    diff_engine_module._variables_par_ligne = par_ligne + 1
    try:
        taille_apres = diff_engine_module._taille_lot_insertion(db_session)
    finally:
        diff_engine_module._variables_par_ligne = None
    assert taille_apres < taille
    assert taille_apres * (par_ligne + 1) <= 32_766


def test_insertion_en_lot_ignore_une_liste_vide(db_session):
    """Une liste vide ne doit émettre aucun énoncé — `insert().values([])` est
    invalide, là où l'ancien `execute(insert(T), [])` ne faisait rien."""
    journal, arreter = _enonces_emis(db_session)
    try:
        diff_engine_module._inserer_lignes_en_lot(db_session, "racj", [])
    finally:
        arreter()
    assert not [e for e, _, _ in journal if "INSERT INTO etat_ligne_source" in e]


# --- 11. Modifications et disparitions : bornées elles aussi (chantier 29) ---
#
# La quarantaine n'arrête un run que si le seuil relatif ET le seuil absolu sont
# franchis ensemble (_depasse). Sur une source de 2,7 M lignes, jusqu'à 50 % de
# modifications et 30 % de disparitions passent donc SANS quarantaine. « Volume
# du diff, pas de la population » ne borne rien à cette échelle.


def test_modifications_un_enonce_par_lot_jamais_un_select_par_ligne(db_session):
    """Mesuré le 2026-09-04 au distant : un SELECT par ligne tient 11 lignes/s.
    Le code d'origine en émettait un par modification — 100 000 modifications
    auraient demandé 2 h 30."""
    executer_diff(db_session, "racj", [_ligne(f"c{i}", f"E{i}", 1) for i in range(60)], COLONNES, CHAMPS_PERTINENTS)

    journal, arreter = _enonces_emis(db_session)
    try:
        executer_diff(db_session, "racj", [_ligne(f"c{i}", f"E{i}", 2) for i in range(60)], COLONNES, CHAMPS_PERTINENTS)
    finally:
        arreter()

    selects = [e for e, _, _ in journal if e.lstrip().upper().startswith("SELECT") and "etat_ligne_source" in e]
    updates = [e for e, _, _ in journal if e.lstrip().upper().startswith("UPDATE") and "etat_ligne_source" in e]
    # 60 modifications, plafond de 50 termes d'union au distant -> 2 énoncés.
    assert len(updates) == 2, f"attendu 2 énoncés (plafond {diff_engine_module.TERMES_UNION_MAX}), {len(updates)} émis"
    assert len(selects) <= 2, f"un SELECT par modification est revenu ({len(selects)} émis)"
    assert db_session.query(EtatLigneSource).filter_by(source_id="racj").count() == 60


def test_modifications_ecrivent_le_meme_encodage_que_l_insertion(db_session):
    """Une modification passe par `UPDATE ... FROM (SELECT ...)`, une apparition
    par `INSERT ... VALUES`. Les deux doivent écrire le MÊME encodage pour un
    même dict — d'où des valeurs qui traversent les types SQLAlchemy plutôt
    qu'un `json.dumps` posé à la main dans le chemin de modification."""
    accents = {"nom": "Aciérie Côté & Frères — Montréal", "capacite": 1}
    executer_diff(db_session, "racj", [LigneSnapshot(cle="c1", champs=dict(accents))], COLONNES, CHAMPS_PERTINENTS)

    modifie = dict(accents, nom="Aciérie Côté & Frères — Québec")
    executer_diff(db_session, "racj", [LigneSnapshot(cle="c1", champs=modifie)], COLONNES, CHAMPS_PERTINENTS)

    etat = db_session.query(EtatLigneSource).filter_by(source_id="racj", cle_naturelle="c1").one()
    assert etat.donnees_normalisees == modifie
    assert etat.empreinte == calculer_empreinte(modifie)


def test_modification_sans_ligne_d_etat_reste_une_erreur(db_session):
    """Le code d'origine levait NoResultFound (scalar_one). L'invariant survit
    au passage en lot : une modification sans état correspondant est un défaut
    en amont, jamais quelque chose à absorber en silence."""
    from falkye.diff_engine import Modification

    with pytest.raises(RuntimeError, match="sans ligne d'état correspondante"):
        diff_engine_module._appliquer_modifications_en_lot(
            db_session, "racj", [Modification(cle="fantome", champs_avant={}, champs_apres={"nom": "X"}, champs_changes=["nom"])]
        )


def test_disparitions_decoupees_sous_le_plafond_de_variables(db_session, monkeypatch):
    """`IN (...)` lie UNE VARIABLE PAR CLÉ. Non découpé, il ne ralentit pas au
    distant : il plante (« too many SQL variables ») au-delà de 32 766 clés —
    et les seuils laissent passer jusqu'à 30 % de disparitions, soit 818 000
    clés pour une source de la taille du REQ."""
    monkeypatch.setattr(diff_engine_module, "BUDGET_VARIABLES_INSERTION", 6)

    executer_diff(db_session, "racj", [_ligne(f"c{i}", f"E{i}", 1) for i in range(12)], COLONNES, CHAMPS_PERTINENTS)

    journal, arreter = _enonces_emis(db_session)
    try:
        diff_engine_module._supprimer_lignes_en_lot(db_session, "racj", [f"c{i}" for i in range(12)])
        db_session.commit()
    finally:
        arreter()

    suppressions = [p for e, _, p in journal if e.lstrip().upper().startswith("DELETE")]
    assert [len(p) - 1 for p in suppressions] == [5, 5, 2], "découpage attendu 5+5+2 pour 12 clés"
    assert db_session.query(EtatLigneSource).filter_by(source_id="racj").count() == 0


def test_disparitions_un_enonce_par_lot_jamais_un_delete_par_ligne(db_session):
    executer_diff(db_session, "racj", [_ligne(f"c{i}", f"E{i}", 1) for i in range(40)], COLONNES, CHAMPS_PERTINENTS)

    journal, arreter = _enonces_emis(db_session)
    try:
        executer_diff(db_session, "racj", [_ligne(f"c{i}", f"E{i}", 1) for i in range(30)], COLONNES, CHAMPS_PERTINENTS)
    finally:
        arreter()

    suppressions = [e for e, _, _ in journal if e.lstrip().upper().startswith("DELETE") and "etat_ligne_source" in e]
    assert len(suppressions) == 1, f"10 disparitions devraient tenir en UN énoncé, {len(suppressions)} émis"
    assert db_session.query(EtatLigneSource).filter_by(source_id="racj").count() == 30


def test_modifications_et_disparitions_vides_n_emettent_rien(db_session):
    journal, arreter = _enonces_emis(db_session)
    try:
        diff_engine_module._appliquer_modifications_en_lot(db_session, "racj", [])
        diff_engine_module._supprimer_lignes_en_lot(db_session, "racj", [])
    finally:
        arreter()
    assert not [e for e, _, _ in journal if "etat_ligne_source" in e]


def test_modifications_respectent_le_plafond_de_termes_d_union(db_session):
    """Second plafond, indépendant de celui des variables et bien plus bas :
    le serveur distant refuse un SELECT composé de plus de 50 termes, là où le
    SQLite local en accepte 500. Un lot calibré sur le local passerait les
    tests et planterait au distant — la valeur du distant s'applique donc
    partout."""
    assert diff_engine_module.TERMES_UNION_MAX == 50
    assert diff_engine_module._taille_lot_insertion(db_session) > diff_engine_module.TERMES_UNION_MAX

    executer_diff(db_session, "racj", [_ligne(f"c{i}", f"E{i}", 1) for i in range(120)], COLONNES, CHAMPS_PERTINENTS)
    journal, arreter = _enonces_emis(db_session)
    try:
        executer_diff(db_session, "racj", [_ligne(f"c{i}", f"E{i}", 2) for i in range(120)], COLONNES, CHAMPS_PERTINENTS)
    finally:
        arreter()

    updates = [p for e, _, p in journal if e.lstrip().upper().startswith("UPDATE") and "etat_ligne_source" in e]
    assert len(updates) == 3, "120 modifications = 50+50+20 énoncés"
    # 4 variables par ligne + le source_id de la clause WHERE.
    assert [(len(p) - 1) // 4 for p in updates] == [50, 50, 20]
