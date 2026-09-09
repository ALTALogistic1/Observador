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


LIVRAISON = "falkye-cycle.service"
OBSERVATION = "falkye-cycle-sans-livraison.service"


def _ouverte(session, source_id, debut, lance_par, unite=LIVRAISON):
    ligne = SourceRunLog(
        source_id=source_id,
        mode="veille_continue",
        statut=StatutExecution.EN_COURS.value,
        started_at=debut,
        lance_par=lance_par,
        # `unite` seulement si `lance_par` dit qu'il y en avait une : une ligne
        # manuelle qui porterait un nom d'unité serait un état impossible.
        unite=unite if lance_par == Lancement.UNITE.value else None,
    )
    session.add(ligne)
    session.commit()
    return ligne


#: Les deux délais RÉELS des deux unités, au 2026-09-09. L'écart est le défaut.
DELAIS = {LIVRAISON: 5400.0, OBSERVATION: 43200.0}


@pytest.fixture()
def delai_lu(monkeypatch):
    """Chaque unité déclare LE SIEN — le cas nominal sur l'hôte.

    La simulation prend l'unité en argument, comme le vrai appel : une simulation
    qui l'ignorerait ne pourrait pas faire tomber le défaut qu'on corrige ici.
    """
    monkeypatch.setattr(
        "falkye.sante_source.delai_maximal",
        lambda unite: DelaiUnite(
            secondes=DELAIS.get(unite),
            lu=True,
            provenance=f"{unite} (test)",
        ),
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
        lambda unite: DelaiUnite(secondes=None, lu=True, provenance="infinity"),
    )
    ligne = _ouverte(db_session, "seao", MAINTENANT - timedelta(days=3), Lancement.UNITE.value)

    rapport = refermer_executions_interrompues(db_session, MAINTENANT)

    assert rapport.refermees == []
    assert rapport.non_decidables == [ligne.id]
    assert "aucun délai exploitable" in rapport.resume_lisible()


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


# --- Réserve 5 : le seuil se lit sur L'UNITÉ QUI A PRODUIT LA LIGNE ---------
#
# Ajoutée le 2026-09-09. Les quatre réserves d'origine disaient « limite la
# bascule aux cycles lancés par l'unité » — le mot qui manquait était LAQUELLE.
# Deux unités lancent le même cycle et écrivent dans la même table :
#
#     falkye-cycle.service                 TimeoutStartSec=5400   (1 h 30)
#     falkye-cycle-sans-livraison.service  TimeoutStartSec=43200  (12 h)
#
# Aucun test ci-dessus ne pouvait faire tomber le défaut : ils ne construisaient
# qu'une seule unité, et la simulation du délai ignorait son argument.


def test_une_ligne_du_cycle_dobservation_encore_vivante_nest_pas_refermee(
    db_session, delai_lu
):
    """**LE test du défaut.** Deux heures sous une unité qui en autorise douze :
    la ligne tourne encore. L'ancien code lisait 5 400 s pour tout le monde et
    la refermait en `interrompue` avec un motif chiffré — une ligne vivante
    déclarée morte, avec une raison qui se lit comme vérifiée."""
    ligne = _ouverte(
        db_session,
        "req",
        MAINTENANT - timedelta(hours=2),
        Lancement.UNITE.value,
        unite=OBSERVATION,
    )

    rapport = refermer_executions_interrompues(db_session, MAINTENANT)

    assert rapport.refermees == []
    assert rapport.encore_possibles == [ligne.id]
    assert ligne.statut == StatutExecution.EN_COURS.value


def test_les_deux_unites_sont_jugees_chacune_sur_son_delai(db_session, delai_lu):
    """Dans le MÊME passage : deux heures est mort sous 1 h 30, vivant sous 12 h.
    C'est la seule forme qui distingue un seuil par unité d'un seuil unique."""
    livraison = _ouverte(
        db_session, "seao", MAINTENANT - timedelta(hours=2), Lancement.UNITE.value
    )
    observation = _ouverte(
        db_session,
        "req",
        MAINTENANT - timedelta(hours=2),
        Lancement.UNITE.value,
        unite=OBSERVATION,
    )

    rapport = refermer_executions_interrompues(db_session, MAINTENANT)

    assert rapport.refermees == [livraison.id]
    assert rapport.encore_possibles == [observation.id]


def test_une_ligne_du_cycle_dobservation_vraiment_trop_vieille_est_refermee(
    db_session, delai_lu
):
    """Le seuil n'est pas désactivé pour l'unité d'observation, il est déplacé.
    Sans ce test, rendre `non_decidable` tout ce qui vient d'elle passerait."""
    ligne = _ouverte(
        db_session,
        "req",
        MAINTENANT - timedelta(hours=13),
        Lancement.UNITE.value,
        unite=OBSERVATION,
    )

    rapport = refermer_executions_interrompues(db_session, MAINTENANT)

    assert rapport.refermees == [ligne.id]
    assert OBSERVATION in ligne.erreur
    assert "43200" in ligne.erreur


def test_une_ligne_sous_unite_sans_nom_dunite_reste_non_decidable(db_session, delai_lu):
    """Les lignes écrites avant le champ `unite`. On sait que systemd les
    surveillait, pas avec quel délai. Leur attribuer l'unité de livraison parce
    que c'est la plus courante serait refaire le même geste une deuxième fois,
    en croyant le corriger — et elles sont TRÈS au-delà des deux seuils."""
    ligne = _ouverte(
        db_session, "seao", MAINTENANT - timedelta(days=2), Lancement.UNITE.value
    )
    ligne.unite = None
    db_session.commit()

    rapport = refermer_executions_interrompues(db_session, MAINTENANT)

    assert rapport.refermees == []
    assert rapport.non_decidables == [ligne.id]
    assert ligne.statut == StatutExecution.EN_COURS.value


def test_le_motif_ecrit_nomme_lunite_pas_seulement_le_chiffre(db_session, delai_lu):
    """Un chiffre seul ne dit pas à quoi il se rapportait. C'est ainsi qu'un
    mauvais seuil reste invisible dans la ligne qu'il a produite."""
    ligne = _ouverte(
        db_session, "seao", MAINTENANT - timedelta(hours=3), Lancement.UNITE.value
    )

    refermer_executions_interrompues(db_session, MAINTENANT)

    assert LIVRAISON in ligne.erreur


def test_le_resume_nomme_chaque_unite_rencontree(db_session, delai_lu):
    """Un résumé qui ne montre qu'un délai laisse croire qu'un seul s'applique —
    la lecture même qui a produit le défaut."""
    _ouverte(db_session, "seao", MAINTENANT - timedelta(hours=2), Lancement.UNITE.value)
    _ouverte(
        db_session,
        "req",
        MAINTENANT - timedelta(hours=2),
        Lancement.UNITE.value,
        unite=OBSERVATION,
    )

    rapport = refermer_executions_interrompues(db_session, MAINTENANT)

    assert set(rapport.delais) == {LIVRAISON, OBSERVATION}


def test_chaque_unite_nest_interrogee_quune_fois(db_session, delai_lu, monkeypatch):
    """`systemctl show` est un sous-processus. Une base peut porter des centaines
    de lignes ouvertes; une lecture par ligne serait une régression silencieuse,
    lente sans rien casser."""
    appels = []
    vrai = __import__("falkye.sante_source", fromlist=["delai_maximal"]).delai_maximal

    def compte(unite):
        appels.append(unite)
        return vrai(unite)

    monkeypatch.setattr("falkye.sante_source.delai_maximal", compte)
    for i in range(5):
        _ouverte(
            db_session, f"s{i}", MAINTENANT - timedelta(hours=2), Lancement.UNITE.value
        )

    refermer_executions_interrompues(db_session, MAINTENANT)

    assert appels == [LIVRAISON]
