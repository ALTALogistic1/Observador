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
    # Le vrai ScanReport porte toujours cette liste, une entrée par source. La
    # doublure doit la porter aussi, sinon elle fige une forme que la production
    # n'a jamais eue.
    ingestion = []


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


# --- Le cycle mesuré, sans livraison ---------------------------------------
#
# Pourquoi ces tests existent : le 2026-09-07, il fallait voir tourner un cycle
# réel sur l'hôte pendant qu'un envoi ne devait PAS partir (réglage de
# désabonnement bloqué chez le fournisseur). La seule chose qui garantit qu'un
# courriel ne part pas, c'est que la génération ne soit jamais appelée — pas une
# intention dans un commentaire.


def test_sans_livraison_aucun_resume_nest_genere(branche, monkeypatch):
    """Le test central : `generer_et_envoyer_resume` ne doit pas être appelé.

    Retirer la garde de falkye/cycle.py fait tomber celui-ci — c'est ce qu'on
    veut, parce que l'appel est l'unique chemin vers un envoi réel.
    """
    _profile(branche, "a@exemple.com")
    _profile(branche, "b@exemple.com")
    appels = []
    monkeypatch.setattr(
        falkye.summary,
        "generer_et_envoyer_resume",
        lambda s, p: appels.append(p.id) or _Resume(),
    )

    rapport = executer_cycle(livrer_les_resumes=False)

    assert appels == []
    assert rapport.resumes_envoyes == 0
    assert rapport.opportunites_livrees == 0
    assert rapport.resumes_en_echec == 0


def test_sans_livraison_les_profils_sont_comptes_pas_servis(branche, monkeypatch):
    """Le chiffre qu'on veut du cycle mesuré : combien d'envois il aurait faits."""
    _profile(branche, "a@exemple.com")
    _profile(branche, "b@exemple.com")
    monkeypatch.setattr(falkye.summary, "generer_et_envoyer_resume", lambda s, p: _Resume())

    rapport = executer_cycle(livrer_les_resumes=False)

    assert rapport.profils_traites == 2
    assert rapport.livraison_omise is True


def test_sans_livraison_la_detection_tourne_quand_meme(branche, monkeypatch):
    """C'est la détection qu'on mesure : la couper viderait l'exercice de son
    sens, et le miroir REQ ne serait jamais sollicité."""
    passages = []
    monkeypatch.setattr(
        falkye.engine, "run_veille_continue", lambda **kw: passages.append(kw) or _Scan()
    )

    rapport = executer_cycle(livrer_les_resumes=False)

    assert len(passages) == 1
    assert rapport.notifications_creees == 3


def test_sans_livraison_le_journal_dit_que_personne_na_essaye(branche, monkeypatch):
    """« 0 résumé envoyé » se lirait comme une panne. Six mois plus tard, la
    ligne doit distinguer « rien n'a pu partir » de « rien ne devait partir »."""
    _profile(branche, "a@exemple.com")

    executer_cycle(livrer_les_resumes=False)

    fin = branche.execute(
        select(JournalExploitation).where(
            JournalExploitation.evenement == EvenementExploitation.CYCLE_FIN
        )
    ).scalar_one()
    assert "LIVRAISON OMISE" in fin.detail
    assert "résumé(s) envoyé(s)" not in fin.detail


def test_sans_livraison_la_reconciliation_tourne_pour_de_vrai(branche, monkeypatch):
    """La réconciliation est une lecture de l'état des livraisons passées : elle
    n'envoie rien, et c'est elle qui rattrape le rebond du cycle précédent. La
    couper ferait perdre la moitié de ce qu'on cherche à observer."""
    import falkye.reconciliation

    passages = []

    class _Reconciliation:
        rebondies = 1
        opportunites_remises_en_attente = 4
        resumes_rebondis = []
        profils_suspendus = []

    # Sur `falkye.reconciliation` et non sur `falkye.cycle` : l'import est fait
    # DANS la fonction, donc le module d'origine est le seul point d'ancrage.
    # Et sans `raising=False`, pour qu'un mauvais nom échoue au lieu de créer
    # un attribut que personne ne lit.
    monkeypatch.setattr(
        falkye.reconciliation,
        "reconcilier_livraisons",
        lambda s, r: passages.append(1) or _Reconciliation(),
    )

    rapport = executer_cycle(livrer_les_resumes=False)

    assert passages == [1]
    assert rapport.remises_rebondies == 1
    assert rapport.opportunites_remises_en_attente == 4


def test_par_defaut_la_livraison_a_lieu(branche, monkeypatch):
    """La garde ne doit pas déteindre sur le chemin normal : le minuteur, lui,
    livre."""
    _profile(branche, "a@exemple.com")
    appels = []
    monkeypatch.setattr(
        falkye.summary,
        "generer_et_envoyer_resume",
        lambda s, p: appels.append(p.id) or _Resume(),
    )

    rapport = executer_cycle()

    assert appels == [1]
    assert rapport.livraison_omise is False


# --- Une source en panne ne doit pas se lire comme une semaine calme --------
#
# Constaté le 2026-09-07 : une source dont l'ingestion lève écrit bien son échec
# dans SourceRunLog, mais le cycle journalise « 0 notification créée » et sort en
# succès. C'est mot pour mot ce que journalise un cycle où il n'y avait rien à
# signaler — et docs/DEPLOIEMENT.md promet justement à l'opérateur qu'« un début
# et une fin à zéro » veut dire « rien à signaler ».


class _ScanAvecPannes:
    """Un rapport de scan comme en produit `run_veille_continue`."""

    nb_notifications_creees = 0

    def __init__(self, *etats):
        from falkye.engine import IngestReport

        self.ingestion = [
            IngestReport(source_id=f"s{i}", erreur=err, ignoree=ign)
            for i, (err, ign) in enumerate(etats)
        ]


def test_une_source_en_panne_apparait_dans_la_ligne_de_journal(branche, monkeypatch):
    monkeypatch.setattr(
        falkye.engine,
        "run_veille_continue",
        lambda **kw: _ScanAvecPannes((None, False), ("base verrouillée", False), (None, False)),
    )

    rapport = executer_cycle(livrer_les_resumes=False)

    assert rapport.sources_en_erreur == 1
    assert rapport.sources_ingerees == 3
    fin = branche.execute(
        select(JournalExploitation).where(
            JournalExploitation.evenement == EvenementExploitation.CYCLE_FIN
        )
    ).scalar_one()
    assert "1 source(s) en erreur sur 3" in fin.detail


def test_une_source_pas_encore_construite_nest_pas_une_panne(branche, monkeypatch):
    """`a_developper` pose aussi `erreur`. La compter ferait crier le journal à
    chaque cycle, et le cri finirait par ne plus rien vouloir dire le jour où il
    est vrai."""
    monkeypatch.setattr(
        falkye.engine,
        "run_veille_continue",
        lambda **kw: _ScanAvecPannes((None, False), ("Aucun connecteur codé", True)),
    )

    rapport = executer_cycle(livrer_les_resumes=False)

    assert rapport.sources_en_erreur == 0
    fin = branche.execute(
        select(JournalExploitation).where(
            JournalExploitation.evenement == EvenementExploitation.CYCLE_FIN
        )
    ).scalar_one()
    assert "en erreur" not in fin.detail


def test_la_ligne_de_journal_ne_nomme_aucune_source(branche, monkeypatch):
    """Elle part dans la base et le nom d'une source est révélateur (charte,
    neutralité des libellés). Le détail par source vit dans SourceRunLog."""
    monkeypatch.setattr(
        falkye.engine,
        "run_veille_continue",
        lambda **kw: _ScanAvecPannes((None, False), ("base verrouillée", False)),
    )

    executer_cycle(livrer_les_resumes=False)

    fin = branche.execute(
        select(JournalExploitation).where(
            JournalExploitation.evenement == EvenementExploitation.CYCLE_FIN
        )
    ).scalar_one()
    assert "s1" not in fin.detail
    assert "verrouillée" not in fin.detail


# --- Quand toutes les sources tombent, c'est le cycle qui n'a rien fait -----
#
# Exception tranchée le 2026-09-07 à la règle « une source en panne ne fait pas
# échouer le cycle ». Une sur neuf est une panne partielle; neuf sur neuf n'est
# plus un cycle, et `systemctl list-units --failed` doit le dire.


def test_toutes_les_sources_tombees_fait_sortir_lunite_en_echec(branche, monkeypatch):
    monkeypatch.setattr(
        falkye.engine,
        "run_veille_continue",
        lambda **kw: _ScanAvecPannes(("tombée", False), ("tombée", False)),
    )
    rapport = executer_cycle(livrer_les_resumes=False)

    assert rapport.toutes_les_sources_sont_tombees is True

    from click.testing import CliRunner

    from falkye.cli import cli

    resultat = CliRunner().invoke(cli, ["cycle", "--sans-livraison"])
    assert resultat.exit_code == 1


def test_une_panne_partielle_ne_fait_pas_echouer_lunite(branche, monkeypatch):
    """Huit sources saines ne doivent pas passer pour un cycle mort."""
    monkeypatch.setattr(
        falkye.engine,
        "run_veille_continue",
        lambda **kw: _ScanAvecPannes(("tombée", False), (None, False)),
    )
    rapport = executer_cycle(livrer_les_resumes=False)

    assert rapport.toutes_les_sources_sont_tombees is False

    from click.testing import CliRunner

    from falkye.cli import cli

    assert CliRunner().invoke(cli, ["cycle", "--sans-livraison"]).exit_code == 0


def test_les_sources_pas_encore_construites_ne_comptent_pas_au_denominateur(
    branche, monkeypatch
):
    """Le piège du dénominateur : deux sources tentées, toutes deux tombées, et
    une troisième jamais construite. C'est un effondrement complet — le compter
    « 2 sur 3 » le ferait passer pour une panne partielle."""
    monkeypatch.setattr(
        falkye.engine,
        "run_veille_continue",
        lambda **kw: _ScanAvecPannes(
            ("tombée", False), ("tombée", False), ("Aucun connecteur codé", True)
        ),
    )

    rapport = executer_cycle(livrer_les_resumes=False)

    assert rapport.sources_ingerees == 2
    assert rapport.toutes_les_sources_sont_tombees is True


def test_un_effondrement_complet_se_lit_dun_coup_doeil_au_journal(branche, monkeypatch):
    monkeypatch.setattr(
        falkye.engine,
        "run_veille_continue",
        lambda **kw: _ScanAvecPannes(("tombée", False), ("tombée", False)),
    )

    executer_cycle(livrer_les_resumes=False)

    fin = branche.execute(
        select(JournalExploitation).where(
            JournalExploitation.evenement == EvenementExploitation.CYCLE_FIN
        )
    ).scalar_one()
    assert "AUCUNE OBSERVATION" in fin.detail


def test_un_cycle_sans_aucune_source_ne_compte_pas_comme_un_effondrement(
    branche, monkeypatch
):
    """Zéro source tentée sur zéro : `0 == 0` serait vrai. Un registre où
    aucune source n'est active est une configuration, pas une panne."""
    monkeypatch.setattr(falkye.engine, "run_veille_continue", lambda **kw: _ScanAvecPannes())

    assert executer_cycle(livrer_les_resumes=False).toutes_les_sources_sont_tombees is False
