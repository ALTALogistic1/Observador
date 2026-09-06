"""Tests de l'ordonnanceur et du journal d'exploitation.

Ce que ces tests protègent : **une exécution laisse toujours une trace**. Sans
battements de cœur, trois pannes produisent le même silence — l'hôte n'a pas
démarré, le cycle s'est interrompu, ou il n'y avait rien à signaler — et
l'absence de journal devient indiscernable d'une semaine calme.
"""
import json

import pytest
from sqlalchemy import select

import falkye.db
import falkye.engine
import falkye.summary
from falkye.cycle import executer_cycle, profils_abonnes
from falkye.exploitation import journaliser
from falkye.models.journal_exploitation import EvenementExploitation, JournalExploitation
from falkye.models.profile import Profile


class _Scan:
    nb_notifications_creees = 3


class _Resume:
    def __init__(self, envoye=True, ids=(1, 2)):
        self.envoye_le = "2026-09-05" if envoye else None
        self.notification_ids = list(ids)


@pytest.fixture()
def branche(monkeypatch, db_session, tmp_path):
    """Branche le cycle sur la session de test et un fichier de repli isolé."""
    monkeypatch.setattr(falkye.db, "get_session", lambda: db_session)
    monkeypatch.setattr(falkye.engine, "run_veille_continue", lambda **kw: _Scan())
    monkeypatch.setenv("FALKYE_JOURNAL_REPLI", str(tmp_path / "repli.jsonl"))
    # La session partagée ne doit pas être refermée par le cycle : les
    # assertions qui suivent l'utilisent encore.
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def _profile(db_session, courriel):
    p = Profile(courriel=courriel, nom="Test")
    db_session.add(p)
    db_session.flush()
    return p


def _evenements(db_session):
    return [
        e.evenement
        for e in db_session.execute(
            select(JournalExploitation).order_by(JournalExploitation.id)
        ).scalars()
    ]


# --- Les battements de cœur ------------------------------------------------


def test_un_cycle_reussi_ecrit_le_debut_et_la_fin(branche, monkeypatch):
    _profile(branche, "a@exemple.com")
    monkeypatch.setattr(falkye.summary, "generer_et_envoyer_resume", lambda s, p: _Resume())

    rapport = executer_cycle()

    assert _evenements(branche) == [
        EvenementExploitation.CYCLE_DEBUT,
        EvenementExploitation.CYCLE_FIN,
    ]
    assert rapport.resumes_envoyes == 1
    assert rapport.opportunites_livrees == 2


def test_un_cycle_qui_echoue_ecrit_son_echec_avant_de_relever(branche, monkeypatch):
    """La ligne d'échec doit exister même si plus rien ne tourne ensuite, et
    l'exception doit remonter pour que le gestionnaire de services voie l'unité
    en échec."""

    def _explose(**kw):
        raise RuntimeError("source injoignable")

    monkeypatch.setattr(falkye.engine, "run_veille_continue", _explose)

    with pytest.raises(RuntimeError, match="source injoignable"):
        executer_cycle()

    assert _evenements(branche) == [
        EvenementExploitation.CYCLE_DEBUT,
        EvenementExploitation.CYCLE_ECHEC,
    ]


def test_la_ligne_de_fin_porte_des_faits_pas_une_trace_de_debogage(branche, monkeypatch):
    """La base distante facture les lignes écrites : un journal bavard pèserait
    plus lourd que la donnée du produit."""
    _profile(branche, "a@exemple.com")
    monkeypatch.setattr(falkye.summary, "generer_et_envoyer_resume", lambda s, p: _Resume())

    executer_cycle()

    fin = branche.execute(
        select(JournalExploitation).where(
            JournalExploitation.evenement == EvenementExploitation.CYCLE_FIN
        )
    ).scalar_one()
    assert "1 profil(s)" in fin.detail
    assert "1 résumé(s) envoyé(s)" in fin.detail
    assert "Traceback" not in fin.detail


# --- L'isolement entre profils --------------------------------------------


def test_un_profil_en_echec_nemporte_pas_les_autres(branche, monkeypatch):
    """Une adresse invalide chez l'un ne doit pas priver les autres de leur envoi."""
    _profile(branche, "premier@exemple.com")
    _profile(branche, "second@exemple.com")

    appels = []

    def _resume(session, profile):
        appels.append(profile.courriel)
        if profile.courriel == "premier@exemple.com":
            raise RuntimeError("adresse refusée")
        return _Resume()

    monkeypatch.setattr(falkye.summary, "generer_et_envoyer_resume", _resume)

    rapport = executer_cycle()

    assert appels == ["premier@exemple.com", "second@exemple.com"]
    assert rapport.resumes_envoyes == 1
    assert rapport.resumes_en_echec == 1
    assert EvenementExploitation.CYCLE_FIN in _evenements(branche)


def test_un_resume_non_livre_est_compte_comme_echec(branche, monkeypatch):
    """Aucun canal n'a livré : ce n'est pas une exception, mais ce n'est pas un
    succès non plus — et le compter comme tel masquerait le silence."""
    _profile(branche, "a@exemple.com")
    monkeypatch.setattr(
        falkye.summary, "generer_et_envoyer_resume", lambda s, p: _Resume(envoye=False)
    )

    rapport = executer_cycle()

    assert rapport.resumes_envoyes == 0
    assert rapport.resumes_en_echec == 1


def test_les_profils_desabonnes_ne_sont_pas_traites(branche, monkeypatch):
    from datetime import datetime, timezone

    abonne = _profile(branche, "abonne@exemple.com")
    desabonne = _profile(branche, "parti@exemple.com")
    desabonne.desabonne_le = datetime.now(timezone.utc)
    branche.flush()

    assert [p.id for p in profils_abonnes(branche)] == [abonne.id]

    appels = []
    monkeypatch.setattr(
        falkye.summary,
        "generer_et_envoyer_resume",
        lambda s, p: appels.append(p.courriel) or _Resume(),
    )
    executer_cycle()

    assert appels == ["abonne@exemple.com"]


# --- Le repli local --------------------------------------------------------


def test_le_repli_recoit_la_ligne_quand_la_base_est_muette(monkeypatch, tmp_path):
    """Les deux cas exacts qui justifient le fichier : démarrage impossible et
    base injoignable."""
    chemin = tmp_path / "repli.jsonl"
    monkeypatch.setenv("FALKYE_JOURNAL_REPLI", str(chemin))

    def _base_muette():
        raise ConnectionError("base injoignable")

    monkeypatch.setattr(falkye.db, "get_session", _base_muette)

    journaliser(EvenementExploitation.CYCLE_DEBUT, "démarrage")

    lignes = [json.loads(l) for l in chemin.read_text(encoding="utf-8").splitlines()]
    assert len(lignes) == 1
    assert lignes[0]["evenement"] == "cycle_debut"
    assert "ConnectionError" in lignes[0]["cause_du_repli"]


def test_journaliser_ne_leve_jamais_meme_sans_fichier_possible(monkeypatch, tmp_path):
    """Une panne du journal est une panne d'observation, pas de production : si
    écrire la ligne échouait bruyamment, on perdrait le cycle EN PLUS de sa
    trace.

    Le chemin de repli est ici sous un FICHIER ordinaire : créer le dossier
    parent échoue. C'est la panne réaliste — un disque plein, un montage
    disparu, un chemin devenu invalide après un déploiement.
    """
    obstacle = tmp_path / "pas-un-dossier"
    obstacle.write_text("x")
    monkeypatch.setenv("FALKYE_JOURNAL_REPLI", str(obstacle / "sous" / "repli.jsonl"))
    monkeypatch.setattr(
        falkye.db, "get_session", lambda: (_ for _ in ()).throw(ConnectionError("muette"))
    )

    journaliser(EvenementExploitation.CYCLE_ECHEC, "tout est cassé")  # ne doit pas lever


def test_le_repli_ajoute_sans_ecraser(monkeypatch, tmp_path):
    """Une ligne par événement, ajoutée à la fin : une écriture interrompue ne
    perd que sa propre ligne."""
    chemin = tmp_path / "repli.jsonl"
    monkeypatch.setenv("FALKYE_JOURNAL_REPLI", str(chemin))
    monkeypatch.setattr(
        falkye.db, "get_session", lambda: (_ for _ in ()).throw(ConnectionError("muette"))
    )

    journaliser(EvenementExploitation.CYCLE_DEBUT)
    journaliser(EvenementExploitation.CYCLE_ECHEC)

    assert len(chemin.read_text(encoding="utf-8").strip().splitlines()) == 2
