"""Un profil qu'on ne peut pas servir ne passe plus en silence.

Le 2026-09-14 : `generer_notifications` sautait un profil sans besoin par un
`continue` NU — sans erreur, sans trace. **Un abonné pouvait ne jamais rien
recevoir sans que rien ne l'explique**, dans le chemin même qui sert les profils.
C'est le silence que la charte §17 nomme comme mode de défaillance principal.

La correction suit la règle d'exploitation du corpus, et elle a deux moitiés :
**un mécanisme automatique ne doit pas interrompre le travail** — le cycle saute
et continue — **mais un geste humain mal formé, si** — la création le crie.
"""
from __future__ import annotations

from falkye.models.journal_exploitation import EvenementExploitation, JournalExploitation
from falkye.models.profile import PlanTarifaire, Profile, TypeProfil


def _profil(db_session, **kw):
    p = Profile(courriel=kw.pop("courriel", "a@b.c"), nom="Test",
                type_profil=TypeProfil.FOURNISSEUR, plan=PlanTarifaire.RADAR, **kw)
    db_session.add(p)
    db_session.commit()
    return p


def test_un_profil_sans_besoin_dit_ce_qui_lui_manque(db_session):
    raison = _profil(db_session).raison_incomplet()

    assert raison is not None
    assert "offre" in raison
    assert "add-need" in raison  # le geste qui le répare est nommé


def test_la_regle_vit_a_un_seul_endroit(db_session):
    """Trois appelants la lisent — création, inventaire, cycle. Qu'ils en aient
    chacun leur version ferait diverger ce que « incomplet » veut dire."""
    import inspect

    from falkye import cli, engine

    for source in (inspect.getsource(engine.generer_notifications), inspect.getsource(cli)):
        assert "raison_incomplet" in source


def test_le_cycle_laisse_une_TRACE_au_lieu_de_se_taire(db_session, registry):
    from falkye.engine import generer_notifications
    from falkye.models.notification import ModeUsage

    profil = _profil(db_session)

    notifications = generer_notifications(db_session, [profil], ModeUsage.VEILLE_CONTINUE, registry)
    db_session.commit()

    assert notifications == []
    lignes = (
        db_session.query(JournalExploitation)
        .filter(JournalExploitation.evenement == EvenementExploitation.PROFIL_INCOMPLET)
        .all()
    )
    assert len(lignes) == 1
    assert f"#{profil.id}" in lignes[0].detail


def test_le_cycle_ne_sarrete_PAS_sur_un_profil_incomplet(db_session, registry):
    """L'autre moitié de la règle : le profil suivant doit être servi. Faire
    lever ici punirait les abonnés valides pour un profil mal formé."""
    from falkye.engine import generer_notifications
    from falkye.models.notification import ModeUsage

    incomplet = _profil(db_session, courriel="vide@b.c")

    generer_notifications(db_session, [incomplet, incomplet], ModeUsage.VEILLE_CONTINUE, registry)
    db_session.commit()

    assert (
        db_session.query(JournalExploitation)
        .filter(JournalExploitation.evenement == EvenementExploitation.PROFIL_INCOMPLET)
        .count()
        == 2
    )
