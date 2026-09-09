"""Refermer par déclaration — le geste humain, et ce qui l'empêche d'être une
inférence déguisée.

Trois conditions, et un test pour chacune : un auteur nommé, un motif qui se
relit, et un statut DISTINCT de la bascule automatique. Plus l'idempotence, qui
vaut ici comme pour la bascule.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from falkye.execution import Lancement
from falkye.models.run_log import (
    STATUTS_DE_SOURCE,
    STATUTS_DINFRASTRUCTURE,
    SourceRunLog,
    StatutExecution,
    decrit_la_source,
)
from falkye.sante_source import (
    DeclarationRefusee,
    derniere_execution_reussie,
    executions_non_decidables,
    fermer_par_declaration,
)

MAINTENANT = datetime(2026, 9, 8, 17, 0, 0)
MOTIF = "Cycle lancé à la main le 7 septembre, tué par SIGTERM pendant l'ingestion."


def _ouverte(session, source_id="eimt", lance_par=None, debut=None):
    ligne = SourceRunLog(
        source_id=source_id,
        mode="veille_continue",
        statut=StatutExecution.EN_COURS.value,
        started_at=debut or MAINTENANT - timedelta(days=1),
        lance_par=lance_par,
    )
    session.add(ligne)
    session.commit()
    return ligne


# --- Les trois conditions --------------------------------------------------


def test_une_declaration_sans_auteur_est_refusee(db_session):
    ligne = _ouverte(db_session)

    with pytest.raises(DeclarationRefusee, match="sans auteur"):
        fermer_par_declaration(db_session, [ligne.id], par="  ", motif=MOTIF)

    assert ligne.statut == StatutExecution.EN_COURS.value


def test_un_motif_trop_court_est_refuse(db_session):
    """« ok » n'est pas une raison, c'est une case cochée — et une case cochée
    ne se relit pas dans six mois."""
    ligne = _ouverte(db_session)

    with pytest.raises(DeclarationRefusee, match="Motif trop court"):
        fermer_par_declaration(db_session, [ligne.id], par="Alexandre", motif="ok")

    assert ligne.statut == StatutExecution.EN_COURS.value
    assert ligne.decision_motif is None


def test_le_statut_dit_quil_vient_dune_decision_humaine(db_session):
    """**LE test de la réserve.** Si la déclaration posait `interrompue`, on
    aurait reproduit un cran plus loin le défaut qu'on vient de retirer : deux
    origines de force de preuve différente sous un même mot."""
    ligne = _ouverte(db_session)

    fermer_par_declaration(
        db_session, [ligne.id], par="Alexandre Quevillon", motif=MOTIF, maintenant=MAINTENANT
    )

    assert ligne.statut == StatutExecution.INTERROMPUE_DECLAREE.value
    assert ligne.statut != StatutExecution.INTERROMPUE.value
    assert ligne.decision_par == "Alexandre Quevillon"
    assert ligne.decision_motif == MOTIF
    assert ligne.decision_le == MAINTENANT
    assert ligne.finished_at == MAINTENANT


def test_le_motif_apparait_au_rapport(db_session):
    ligne = _ouverte(db_session)

    rapport = fermer_par_declaration(
        db_session, [ligne.id], par="Alexandre Quevillon", motif=MOTIF
    )

    resume = rapport.resume_lisible()
    assert MOTIF in resume
    assert "Alexandre Quevillon" in resume
    assert "déclaration" in resume


def test_le_motif_nest_pas_range_dans_le_champ_erreur(db_session):
    """`erreur` porte une cause technique OBSERVÉE. Y ranger le raisonnement de
    quelqu'un ferait lire un jugement comme une observation."""
    ligne = _ouverte(db_session)

    fermer_par_declaration(db_session, [ligne.id], par="Alexandre", motif=MOTIF)

    assert ligne.erreur is None
    assert ligne.decision_motif == MOTIF


# --- Idempotence -----------------------------------------------------------


def test_une_ligne_deja_conclue_garde_sa_conclusion(db_session):
    """Une déclaration arrivée après coup n'écrase pas une conclusion mieux
    fondée que la sienne."""
    fin = MAINTENANT - timedelta(hours=1)
    ligne = SourceRunLog(
        source_id="seao",
        mode="veille_continue",
        statut=StatutExecution.ERREUR.value,
        started_at=MAINTENANT - timedelta(hours=2),
        finished_at=fin,
        erreur="portail injoignable",
    )
    db_session.add(ligne)
    db_session.commit()

    rapport = fermer_par_declaration(db_session, [ligne.id], par="Alexandre", motif=MOTIF)

    assert rapport.fermees == []
    assert rapport.deja_fermees == [ligne.id]
    assert ligne.statut == StatutExecution.ERREUR.value
    assert ligne.erreur == "portail injoignable"


def test_deux_declarations_de_suite_ne_changent_rien_a_la_seconde(db_session):
    ligne = _ouverte(db_session)

    premiere = fermer_par_declaration(db_session, [ligne.id], par="Alexandre", motif=MOTIF)
    decision = ligne.decision_le
    seconde = fermer_par_declaration(
        db_session, [ligne.id], par="Quelqu'un d'autre", motif=MOTIF + " Reprise."
    )

    assert premiere.fermees == [ligne.id]
    assert seconde.fermees == []
    assert ligne.decision_par == "Alexandre"
    assert ligne.decision_le == decision


def test_un_identifiant_inexistant_est_signale_pas_invente(db_session):
    rapport = fermer_par_declaration(db_session, [999_999], par="Alexandre", motif=MOTIF)

    assert rapport.fermees == []
    assert rapport.introuvables == [999_999]
    assert "INTROUVABLE" in rapport.resume_lisible()


# --- La déclarée ne dégrade pas plus que l'automatique ---------------------


def test_interrompue_declaree_ne_decrit_pas_la_source(db_session):
    assert decrit_la_source(StatutExecution.INTERROMPUE_DECLAREE.value) is False
    assert StatutExecution.INTERROMPUE_DECLAREE.value not in STATUTS_DE_SOURCE
    assert StatutExecution.INTERROMPUE_DECLAREE.value in STATUTS_DINFRASTRUCTURE


def test_une_declaree_ne_devient_jamais_la_derniere_reussite(db_session):
    reussite = SourceRunLog(
        source_id="eimt",
        mode="veille_continue",
        statut=StatutExecution.SUCCES.value,
        finished_at=MAINTENANT - timedelta(days=7),
    )
    db_session.add(reussite)
    ligne = _ouverte(db_session)

    fermer_par_declaration(db_session, [ligne.id], par="Alexandre", motif=MOTIF)

    derniere = derniere_execution_reussie(db_session, "eimt")
    assert derniere.id == reussite.id


# --- Ce que l'outil montre avant de toucher --------------------------------


def test_les_candidates_excluent_ce_que_la_bascule_sait_conclure(db_session):
    """L'outil ne propose que ce qu'aucune règle ne peut trancher : une
    exécution de l'unité appartient à la bascule automatique, pas à un humain."""
    manuelle = _ouverte(db_session, lance_par=Lancement.MANUEL.value)
    inconnue = _ouverte(db_session, lance_par=None)
    # Sous unité mais SANS nom d'unité : les lignes d'avant le champ. On sait que
    # systemd la surveillait, pas avec quel délai — donc rien à en conclure.
    sans_nom = _ouverte(db_session, source_id="req", lance_par=Lancement.UNITE.value)
    decidable = _ouverte(db_session, source_id="seao", lance_par=Lancement.UNITE.value)
    decidable.unite = "falkye-cycle.service"
    db_session.commit()

    candidates = executions_non_decidables(db_session)

    assert {ligne.id for ligne in candidates} == {manuelle.id, inconnue.id, sans_nom.id}


def test_une_ligne_deja_fermee_nest_plus_candidate(db_session):
    ligne = _ouverte(db_session)
    fermer_par_declaration(db_session, [ligne.id], par="Alexandre", motif=MOTIF)

    assert executions_non_decidables(db_session) == []
