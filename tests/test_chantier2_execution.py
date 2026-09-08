"""Chantier 2, travail 1bis — l'identité d'exécution et les trois issues.

Ce que ces tests verrouillent :

1. Une quarantaine ne s'enregistre PLUS comme un succès. C'est le premier
   critère d'acceptation du chantier, et il échouait avant d'avoir commencé.
2. « Dernière exécution réussie » ne désigne que la réussite PUBLIÉE.
3. L'identifiant d'exécution relie les traces des DEUX bases — et vaut None hors
   de toute exécution, jamais un identifiant fabriqué.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

# SQLite ne conserve pas le fuseau : ce qui ressort de la base est naïf. Comparer
# une valeur relue à un `datetime.now(timezone.utc)` échouerait sur la seule
# différence de tzinfo — un test rouge sans défaut.
MAINTENANT = datetime(2026, 9, 8, 15, 0, 0)

from sqlalchemy import select

from falkye.execution import execution, execution_courante, nouvel_identifiant
from falkye.models.diff_run_historique import DiffRunHistorique
from falkye.models.run_log import SourceRunLog, StatutExecution
from falkye.sante_source import date_derniere_reussite, derniere_execution_reussie


def _ligne(session, source_id, statut, quand, execution_id=None):
    ligne = SourceRunLog(
        source_id=source_id,
        mode="veille_continue",
        statut=statut.value,
        finished_at=quand,
        execution_id=execution_id,
    )
    session.add(ligne)
    session.commit()
    return ligne


# --- l'identité ------------------------------------------------------------


def test_hors_execution_lidentifiant_est_none_jamais_fabrique():
    """Une trace écrite hors exécution ne doit pas s'inventer un rattachement :
    un lien faux est pire qu'un lien absent — il se lit comme vérifié."""
    assert execution_courante() is None


def test_une_execution_imbriquee_restaure_la_precedente():
    """Sans restauration, une source qui échoue laisserait son identifiant en
    place et la source SUIVANTE écrirait ses traces sous le nom de celle qui est
    tombée."""
    with execution() as externe:
        with execution() as interne:
            assert interne != externe
            assert execution_courante() == interne
        assert execution_courante() == externe
    assert execution_courante() is None


def test_lidentifiant_survit_a_une_exception():
    with execution() as externe:
        try:
            with execution():
                raise RuntimeError("la source tombe")
        except RuntimeError:
            pass
        assert execution_courante() == externe


def test_lidentifiant_relie_les_traces_des_deux_bases(db_session):
    """`SourceRunLog` est dans la base du produit, `DiffRunHistorique` dans celle
    des miroirs. Aucune jointure SQL ne les relie — le rapprochement se fait sur
    la valeur, dans le code."""
    ident = nouvel_identifiant()
    _ligne(db_session, "seao", StatutExecution.SUCCES, MAINTENANT, ident)
    db_session.add(DiffRunHistorique(source_id="seao", execution_id=ident))
    db_session.commit()

    run = db_session.execute(
        select(SourceRunLog).where(SourceRunLog.execution_id == ident)
    ).scalar_one()
    diff = db_session.execute(
        select(DiffRunHistorique).where(DiffRunHistorique.execution_id == ident)
    ).scalar_one()

    assert run.execution_id == diff.execution_id


# --- les trois issues ------------------------------------------------------


def test_une_quarantaine_nest_pas_une_reussite(db_session):
    """LE critère d'acceptation. Une source en quarantaine rend zéro signal sans
    lever — indiscernable d'un territoire calme tant que le statut ne les sépare
    pas."""
    maintenant = MAINTENANT
    _ligne(db_session, "seao", StatutExecution.SUCCES, maintenant - timedelta(days=7))
    _ligne(db_session, "seao", StatutExecution.QUARANTAINE, maintenant)

    derniere = derniere_execution_reussie(db_session, "seao")

    assert derniere is not None
    assert derniere.statut == StatutExecution.SUCCES.value
    assert derniere.finished_at == maintenant - timedelta(days=7)


def test_ni_une_erreur_ni_une_ignoree_ne_sont_des_reussites(db_session):
    maintenant = MAINTENANT
    _ligne(db_session, "seao", StatutExecution.SUCCES, maintenant - timedelta(days=7))
    _ligne(db_session, "seao", StatutExecution.ERREUR, maintenant - timedelta(days=2))
    _ligne(db_session, "seao", StatutExecution.IGNOREE, maintenant - timedelta(days=1))

    assert date_derniere_reussite(db_session, "seao") == maintenant - timedelta(days=7)


def test_une_ligne_restee_ouverte_natteste_de_rien(db_session):
    """Les deux lignes `en_cours` orphelines du 2026-09-07 sont exactement ce
    cas : la base est tombée avant que l'échec puisse s'y écrire, et la ligne
    ment. Elle ne doit pas pouvoir passer pour une réussite."""
    ligne = SourceRunLog(
        source_id="eimt", mode="veille_continue", statut=StatutExecution.EN_COURS.value
    )
    db_session.add(ligne)
    db_session.commit()

    assert derniere_execution_reussie(db_session, "eimt") is None


def test_jamais_publie_rend_none_pas_une_date_par_defaut(db_session):
    """None est un état riche — neuve, en attente d'une clé, défaillante depuis
    toujours. Une date par défaut les aplatirait toutes."""
    assert date_derniere_reussite(db_session, "source-qui-na-jamais-tourne") is None


def test_les_sources_ne_se_melangent_pas(db_session):
    maintenant = MAINTENANT
    _ligne(db_session, "seao", StatutExecution.SUCCES, maintenant)

    assert date_derniere_reussite(db_session, "eimt") is None


# --- de bout en bout : la quarantaine remonte jusqu'au journal du produit ----


class _ConnecteurMisEnQuarantaine:
    """Appelle le VRAI moteur de diff, avec un taux d'erreur de lecture qui
    déclenche la quarantaine immédiate (`LECTURE_ECHOUEE`), puis ne rend aucun
    signal — exactement ce que fait une source réelle en quarantaine.

    Un faux qui écrirait lui-même la ligne `DiffRunHistorique` testerait le test.
    Ici c'est `executer_diff` qui l'écrit, donc c'est lui qui doit y avoir posé
    l'identifiant d'exécution.
    """

    def __init__(self, source_id):
        self.source_id = source_id

    def detect(self, since, db_session):
        from falkye.diff_engine import executer_diff

        executer_diff(
            db_session,
            self.source_id,
            lignes=[],
            colonnes_vues={},
            champs_pertinents=set(),
            taux_erreur_lecture=1.0,
        )
        return iter(())


def test_une_source_en_quarantaine_ne_senregistre_plus_comme_un_succes(
    db_session, monkeypatch
):
    """**LE critère d'acceptation du chantier 2**, de bout en bout.

    Avant : `statut = "succes"`, `nb_signaux_detectes = 0` — mot pour mot ce
    qu'écrit un territoire calme. Rien, nulle part, ne distinguait les deux.
    """
    from falkye.engine import ingest_source
    from falkye.registry.loader import get_registry

    registry = get_registry()
    source_id = registry.sources_actives_automatisees()[0].id
    monkeypatch.setattr(
        type(registry.source(source_id)),
        "charger_connecteur",
        lambda self: _ConnecteurMisEnQuarantaine(source_id),
    )

    ingest_source(db_session, source_id, None, registry, "veille_continue")

    ligne = db_session.execute(
        select(SourceRunLog).where(SourceRunLog.source_id == source_id)
    ).scalar_one()
    assert ligne.statut == StatutExecution.QUARANTAINE.value
    assert derniere_execution_reussie(db_session, source_id) is None

    # Et la trace de l'autre base porte le MÊME identifiant.
    diff = db_session.execute(
        select(DiffRunHistorique).where(DiffRunHistorique.source_id == source_id)
    ).scalar_one()
    assert diff.quarantaine is True
    assert diff.execution_id == ligne.execution_id
    assert ligne.execution_id is not None


def test_une_execution_ordinaire_porte_son_identifiant_et_sa_duree(
    db_session, monkeypatch
):
    from falkye.engine import ingest_source
    from falkye.registry.loader import get_registry

    class _ConnecteurCalme:
        def detect(self, since, db_session):
            return iter(())

    registry = get_registry()
    source_id = registry.sources_actives_automatisees()[0].id
    monkeypatch.setattr(
        type(registry.source(source_id)), "charger_connecteur", lambda self: _ConnecteurCalme()
    )

    ingest_source(db_session, source_id, None, registry, "veille_continue")

    ligne = db_session.execute(
        select(SourceRunLog).where(SourceRunLog.source_id == source_id)
    ).scalar_one()
    assert ligne.statut == StatutExecution.SUCCES.value
    assert ligne.execution_id is not None
    assert ligne.duree_ms is not None and ligne.duree_ms >= 0
    # Le coût reste NULL tant qu'il n'est pas mesuré : un zéro se lirait
    # « cette exécution n'a rien coûté ».
    assert ligne.nb_lignes_lues_base is None
