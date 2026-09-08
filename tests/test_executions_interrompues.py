"""Refermer une exécution restée ouverte — et refuser de la refermer.

Les quatre réserves posées avec la décision, une par bloc :

1. le seuil se LIT depuis l'unité; la valeur de repli porte sa provenance et se
   déclare périmée quand elle diverge;
2. la déduction ne tient que sous l'unité — hors d'elle, la ligne reste ouverte
   et se signale comme non décidable;
3. `interrompue` ne dégrade pas la santé d'une source : c'est l'infrastructure
   qui a lâché, pas le connecteur;
4. idempotence — ne referme que ce qui est encore ouvert.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from falkye.delai_unite import DELAI_REPLI_SECONDES, DelaiUnite, analyser_duree
from falkye.execution import Lancement
from falkye.models.run_log import (
    STATUTS_DE_SOURCE,
    SourceRunLog,
    StatutExecution,
    decrit_la_source,
)
from falkye.sante_source import derniere_execution_reussie, refermer_executions_interrompues

MAINTENANT = datetime(2026, 9, 8, 16, 0, 0)


def _ouverte(session, source_id, debut, lance_par):
    ligne = SourceRunLog(
        source_id=source_id,
        mode="veille_continue",
        statut=StatutExecution.EN_COURS.value,
        started_at=debut,
        lance_par=lance_par,
    )
    session.add(ligne)
    session.commit()
    return ligne


@pytest.fixture()
def delai_lu(monkeypatch):
    """L'unité déclare 5 400 s — le cas nominal sur l'hôte."""
    monkeypatch.setattr(
        "falkye.sante_source.delai_maximal",
        lambda: DelaiUnite(secondes=5400.0, lu=True, provenance="unité (test)"),
    )


# --- Réserve 1 : le seuil se lit ------------------------------------------


def test_les_durees_de_systemd_sont_analysees():
    assert analyser_duree("1h 30min") == 5400.0
    assert analyser_duree("5400s") == 5400.0
    assert analyser_duree("1min 30s") == 90.0


def test_infinity_ne_donne_aucun_seuil():
    """Un délai infini veut dire qu'AUCUNE durée ne permet de conclure. Rendre
    un très grand nombre ferait passer cette impossibilité pour un seuil haut."""
    assert analyser_duree("infinity") is None


def test_un_delai_illisible_ne_referme_rien(db_session, monkeypatch):
    monkeypatch.setattr(
        "falkye.sante_source.delai_maximal",
        lambda: DelaiUnite(secondes=None, lu=True, provenance="infinity"),
    )
    _ouverte(db_session, "seao", MAINTENANT - timedelta(days=3), Lancement.UNITE.value)

    rapport = refermer_executions_interrompues(db_session, MAINTENANT)

    assert rapport.refermees == []
    assert "indécidable" in rapport.resume_lisible()


def test_le_repli_se_declare_perime_quand_il_diverge_de_lunite():
    """Même mécanisme que la table de prix : une valeur recopiée qui ne
    correspond plus doit le DIRE, pas être corrigée en douce."""
    aligne = DelaiUnite(secondes=float(DELAI_REPLI_SECONDES), lu=True, provenance="unité")
    diverge = DelaiUnite(secondes=9999.0, lu=True, provenance="unité")
    jamais_lu = DelaiUnite(secondes=9999.0, lu=False, provenance="repli")

    assert aligne.perime is False
    assert diverge.perime is True
    # Non lu : rien à comparer, donc rien à déclarer périmé.
    assert jamais_lu.perime is False


# --- Réserve 2 : la déduction ne tient que sous l'unité --------------------


def test_une_execution_de_lunite_trop_vieille_est_refermee(db_session, delai_lu):
    ligne = _ouverte(db_session, "seao", MAINTENANT - timedelta(hours=3), Lancement.UNITE.value)

    rapport = refermer_executions_interrompues(db_session, MAINTENANT)

    assert rapport.refermees == [ligne.id]
    assert ligne.statut == StatutExecution.INTERROMPUE.value
    assert ligne.finished_at == MAINTENANT
    assert "Cause inconnue" in ligne.erreur


def test_une_execution_manuelle_reste_ouverte_et_se_signale(db_session, delai_lu):
    """**LE test de la réserve.** Un cycle lancé à la main n'est gouverné par
    aucun délai. La conclure interrompue serait vrai sous une condition qu'on
    n'a pas vérifiée — et il y a eu beaucoup de cycles manuels cette semaine."""
    ligne = _ouverte(db_session, "eimt", MAINTENANT - timedelta(hours=3), Lancement.MANUEL.value)

    rapport = refermer_executions_interrompues(db_session, MAINTENANT)

    assert rapport.refermees == []
    assert rapport.non_decidables == [ligne.id]
    assert ligne.statut == StatutExecution.EN_COURS.value
    assert "NON DÉCIDABLE" in rapport.resume_lisible()


def test_une_ligne_dorigine_inconnue_nest_pas_refermee(db_session, delai_lu):
    """Les deux lignes orphelines d'avant ce champ sont dans ce cas : `lance_par`
    est NULL, donc on ne sait pas, et on ne le devinera pas après coup."""
    ligne = _ouverte(db_session, "eimt", MAINTENANT - timedelta(days=1), None)

    rapport = refermer_executions_interrompues(db_session, MAINTENANT)

    assert rapport.non_decidables == [ligne.id]
    assert ligne.statut == StatutExecution.EN_COURS.value


def test_une_execution_encore_dans_le_delai_nest_pas_touchee(db_session, delai_lu):
    ligne = _ouverte(db_session, "seao", MAINTENANT - timedelta(minutes=10), Lancement.UNITE.value)

    rapport = refermer_executions_interrompues(db_session, MAINTENANT)

    assert rapport.encore_possibles == [ligne.id]
    assert ligne.statut == StatutExecution.EN_COURS.value


# --- Réserve 3 : interrompue ne dégrade pas la source ----------------------


def test_interrompue_ne_decrit_pas_la_source(db_session):
    """Un quota épuisé n'est pas huit connecteurs qui se dégradent, c'est
    l'infrastructure qui tombe. Le statut décrit l'exécution, pas le
    connecteur."""
    assert decrit_la_source(StatutExecution.INTERROMPUE.value) is False
    assert StatutExecution.INTERROMPUE.value not in STATUTS_DE_SOURCE
    assert decrit_la_source(StatutExecution.SUCCES.value) is True
    assert decrit_la_source(StatutExecution.QUARANTAINE.value) is True
    assert decrit_la_source(StatutExecution.ERREUR.value) is True


def test_ni_en_cours_ni_ignoree_ne_decrivent_la_source():
    assert decrit_la_source(StatutExecution.EN_COURS.value) is False
    assert decrit_la_source(StatutExecution.IGNOREE.value) is False


def test_une_interrompue_ne_devient_jamais_la_derniere_reussite(db_session, delai_lu):
    session_debut = MAINTENANT - timedelta(hours=3)
    reussite = SourceRunLog(
        source_id="seao",
        mode="veille_continue",
        statut=StatutExecution.SUCCES.value,
        finished_at=MAINTENANT - timedelta(days=7),
    )
    db_session.add(reussite)
    _ouverte(db_session, "seao", session_debut, Lancement.UNITE.value)
    db_session.commit()

    refermer_executions_interrompues(db_session, MAINTENANT)

    derniere = derniere_execution_reussie(db_session, "seao")
    assert derniere.statut == StatutExecution.SUCCES.value
    assert derniere.finished_at == MAINTENANT - timedelta(days=7)


def test_interrompue_reste_visible_pour_lexploitation(db_session, delai_lu):
    """Ne pas dégrader une source n'est pas se taire : la ligne existe, datée,
    avec sa raison — c'est ce que le tableau de bord d'exploitation lira."""
    ligne = _ouverte(db_session, "seao", MAINTENANT - timedelta(hours=3), Lancement.UNITE.value)

    refermer_executions_interrompues(db_session, MAINTENANT)

    assert ligne.statut == StatutExecution.INTERROMPUE.value
    assert ligne.finished_at is not None
    assert ligne.erreur


# --- Réserve 4 : idempotence ----------------------------------------------


def test_une_ligne_deja_refermee_nest_pas_reecrite(db_session, delai_lu):
    """Si quelqu'un — ou le cycle lui-même — a refermé la ligne proprement entre
    temps, la reprise ne l'écrase pas."""
    fin = MAINTENANT - timedelta(hours=2)
    ligne = SourceRunLog(
        source_id="seao",
        mode="veille_continue",
        statut=StatutExecution.ERREUR.value,
        started_at=MAINTENANT - timedelta(hours=3),
        finished_at=fin,
        erreur="portail injoignable",
        lance_par=Lancement.UNITE.value,
    )
    db_session.add(ligne)
    db_session.commit()

    rapport = refermer_executions_interrompues(db_session, MAINTENANT)

    assert rapport.refermees == []
    assert ligne.statut == StatutExecution.ERREUR.value
    assert ligne.finished_at == fin
    assert ligne.erreur == "portail injoignable"


def test_deux_passages_ne_changent_rien_au_second(db_session, delai_lu):
    ligne = _ouverte(db_session, "seao", MAINTENANT - timedelta(hours=3), Lancement.UNITE.value)

    premier = refermer_executions_interrompues(db_session, MAINTENANT)
    fin = ligne.finished_at
    second = refermer_executions_interrompues(db_session, MAINTENANT + timedelta(hours=1))

    assert premier.refermees == [ligne.id]
    assert second.refermees == []
    assert ligne.finished_at == fin
