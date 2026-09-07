"""Ce que ces tests protègent : **`ingest_source` ne lève jamais, et une source
tombée laisse une trace.**

Les trois défauts qu'ils verrouillent ont été trouvés le 7 septembre 2026, sur
l'hôte, au premier cycle réel — et aucun n'était visible en développement, parce
qu'ils dépendent tous d'une base DISTANTE.

  1. Le gestionnaire d'erreur appelait `db_session.rollback()`, qui a levé
     `Hrana: stream not found` sur une connexion morte. L'exception a traversé
     `ingest_source`, `ingest_all_active_sources` et `run_veille_continue` : le
     cycle entier est mort sur la panne d'UNE source, et huit sources saines
     n'ont jamais été essayées. Le chemin de secours doit être plus robuste que
     ce qu'il rattrape.

  2. Ce même rollback effaçait la ligne `en_cours` de `SourceRunLog` posée au
     début. Les lignes qui suivaient (`run_log.statut = "erreur"`) portaient sur
     un objet que la session ne suivait plus. **Une source tombée n'écrivait
     donc rien** — indiscernable d'une source saine sans résultat, exactement la
     confusion que ce journal existe pour lever.

  3. Le `flush()` initial laissait une écriture non validée ouverte pendant le
     téléchargement réseau. Mesuré : une transaction en lecture survit à 180 s
     d'inactivité sur la base distante, une transaction portant une écriture
     meurt en 75 s. C'est ce qui tuait le flux.
"""
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from falkye.engine import ingest_source
from falkye.models.run_log import SourceRunLog
from falkye.registry.loader import get_registry


@pytest.fixture()
def source_id():
    return get_registry().sources_actives_automatisees()[0].id


def _brancher_connecteur(monkeypatch, source_id, connecteur):
    registry = get_registry()
    monkeypatch.setattr(
        type(registry.source(source_id)), "charger_connecteur", lambda self: connecteur
    )
    return registry


class _ConnecteurQuiTombe:
    def detect(self, since, db_session):
        raise RuntimeError("portail injoignable")
        yield  # pragma: no cover


# --- La trace ---------------------------------------------------------------


def test_une_source_tombee_laisse_une_ligne_derreur(db_session, monkeypatch, source_id):
    """Le test central du défaut 2. Sur la version d'avant, la requête ne
    ramenait RIEN : la seule trace d'un échec vivait dans le journal du système,
    hors de la base, sur un hôte injoignable."""
    registry = _brancher_connecteur(monkeypatch, source_id, _ConnecteurQuiTombe())

    rapport = ingest_source(db_session, source_id, None, registry, "veille_continue")

    assert rapport.erreur is not None
    lignes = (
        db_session.execute(select(SourceRunLog).where(SourceRunLog.source_id == source_id))
        .scalars()
        .all()
    )
    erreurs = [l for l in lignes if l.statut == "erreur"]
    assert len(erreurs) == 1
    assert "portail injoignable" in erreurs[0].erreur
    assert erreurs[0].finished_at is not None


def test_aucune_ligne_ne_reste_en_cours_apres_un_echec(db_session, monkeypatch, source_id):
    """Une ligne `en_cours` qui survit à l'exécution se lit comme un cycle
    interrompu — le mauvais diagnostic, posé par la trace elle-même."""
    registry = _brancher_connecteur(monkeypatch, source_id, _ConnecteurQuiTombe())

    ingest_source(db_session, source_id, None, registry, "veille_continue")

    restantes = (
        db_session.execute(select(SourceRunLog).where(SourceRunLog.statut == "en_cours"))
        .scalars()
        .all()
    )
    assert restantes == []


# --- Le chemin de secours ---------------------------------------------------


def test_un_rollback_qui_leve_nemporte_pas_le_cycle(db_session, monkeypatch, source_id):
    """Le test central du défaut 1, reproduit tel qu'il s'est produit : la
    source tombe, PUIS l'annulation elle-même échoue parce que la connexion est
    morte. `ingest_source` doit quand même rendre son rapport."""
    registry = _brancher_connecteur(monkeypatch, source_id, _ConnecteurQuiTombe())

    appels = {"rollback": 0, "invalidate": 0}
    vrai_rollback = db_session.rollback

    def _rollback_mort():
        appels["rollback"] += 1
        if appels["rollback"] == 1:
            # Le message exact renvoyé par la base distante le 2026-09-07.
            raise ValueError(
                'Hrana: `api error: `status=404 Not Found, '
                'body={"error":"stream not found: e0b782e6:200fc74"}``'
            )
        return vrai_rollback()

    def _invalidate():
        appels["invalidate"] += 1
        vrai_rollback()

    monkeypatch.setattr(db_session, "rollback", _rollback_mort)
    monkeypatch.setattr(db_session, "invalidate", _invalidate, raising=False)

    rapport = ingest_source(db_session, source_id, None, registry, "veille_continue")

    assert rapport.erreur is not None
    assert appels["invalidate"] == 1, "la connexion morte doit être jetée, pas réutilisée"


def test_une_trace_impossible_a_ecrire_nemporte_pas_le_cycle(
    db_session, monkeypatch, source_id
):
    """Perdre la trace d'un échec est mauvais; perdre les huit sources suivantes
    pour cette raison serait pire."""
    registry = _brancher_connecteur(monkeypatch, source_id, _ConnecteurQuiTombe())

    vrai_commit = db_session.commit

    def _commit_mort():
        raise ValueError("Hrana: `stream not found`")

    def _apres_lechec(*a, **kw):
        monkeypatch.setattr(db_session, "commit", _commit_mort)

    monkeypatch.setattr(db_session, "commit", vrai_commit)
    monkeypatch.setattr(db_session, "add", lambda obj: _apres_lechec() or None)

    rapport = ingest_source(db_session, source_id, None, registry, "veille_continue")

    assert rapport.erreur is not None


# --- La cause profonde ------------------------------------------------------


def test_aucune_ecriture_nest_ouverte_pendant_le_reseau(db_session, monkeypatch, source_id):
    """Défaut 3. Au moment où le connecteur part sur le réseau, la session ne
    doit tenir AUCUNE écriture non validée : c'est ce qui faisait expirer le flux
    distant en 75 secondes, là où une transaction en lecture tient 180 s."""
    etat = {}

    class _ConnecteurQuiRegarde:
        def detect(self, since, db_session):
            # Même raison que ci-dessous : c'est la transaction OUVERTE qui tue,
            # pas la présence d'objets dans `session.new`.
            etat["en_transaction"] = db_session.in_transaction()
            return iter(())

    registry = _brancher_connecteur(monkeypatch, source_id, _ConnecteurQuiRegarde())

    ingest_source(db_session, source_id, None, registry, "veille_continue")

    assert etat["en_transaction"] is False


def test_une_source_pas_encore_construite_est_quand_meme_consignee(
    db_session, monkeypatch, source_id
):
    """La refonte du chemin d'erreur a supprimé le `finally` qui validait cette
    ligne-là aussi. Sans la validation explicite, elle resterait `en_cours`."""
    registry = _brancher_connecteur(monkeypatch, source_id, None)

    rapport = ingest_source(db_session, source_id, None, registry, "veille_continue")

    assert rapport.ignoree is True
    ligne = (
        db_session.execute(select(SourceRunLog).where(SourceRunLog.source_id == source_id))
        .scalars()
        .one()
    )
    assert ligne.statut == "ignoree"
    assert ligne.finished_at is not None


# --- Aucune écriture ne traverse une itération -----------------------------
#
# Décision du 2026-09-07 : valider à chaque signal plutôt que flusher, et
# accepter le coût. La mesure qui la motive est dans docs/DEPLOIEMENT.md —
# moins de dix secondes avant que la base distante annule une transaction qui
# porte une écriture.


def test_aucune_ecriture_ne_survit_a_une_iteration(db_session, monkeypatch, source_id):
    """Le test central de la décision. Entre deux signaux se glisse la
    résolution NEQ du suivant, qui peut durer des secondes : si une écriture
    reste ouverte à ce moment-là, la source entière est perdue."""
    from falkye.sources.base import RawSignal

    etats = []

    class _ConnecteurQuiObserve:
        def detect(self, since, db_session):
            for i in range(3):
                # Vu par le connecteur AVANT de produire le signal suivant —
                # c'est exactement l'instant où la résolution longue a lieu.
                #
                # `in_transaction()` et NON `db_session.new` : un `flush()` vide
                # `new` lui aussi, en poussant l'écriture dans une transaction
                # qui reste OUVERTE. Le premier jet de ce test regardait `new`,
                # et la mutation qui remet un `flush()` passait sans rien casser
                # — un test qui ne verrouillait rien.
                etats.append(db_session.in_transaction())
                yield RawSignal(
                    signal_type_id="contrat_public",
                    source_ref=f"ref-{i}",
                    nom_entreprise=f"Entreprise Témoin {i}",
                    detected_at=datetime.now(timezone.utc),
                    titre_ou_description="Signal de test",
                    champs={},
                )

    registry = _brancher_connecteur(monkeypatch, source_id, _ConnecteurQuiObserve())

    rapport = ingest_source(db_session, source_id, None, registry, "veille_continue")

    assert rapport.nb_signaux_nouveaux == 3
    assert len(etats) == 3
    assert etats == [False, False, False], (
        "une transaction reste ouverte pendant que le connecteur travaille — "
        "la base distante l'annulerait en moins de dix secondes"
    )
