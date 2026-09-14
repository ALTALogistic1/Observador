"""La troisième colonne : ce que la source porte et que personne ne demande.

*La classification du SEAO était là depuis toujours — 93,6 % des avis — et personne ne
la lisait.* La sonde interroge les SOURCES, pas la base.

**Et ce qu'elle ne peut pas faire doit être dans sa sortie, pas dans une réponse** :
une source grattée n'a pas de liste de champs, et la troisième colonne y est vide PAR
NATURE. *Une absence de mesure n'est pas une mesure nulle.*
"""
from __future__ import annotations

from outils.sonde_source import PAS_DE_SCHEMA, SONDES, cles_lues, sonder_source


def test_les_cles_lues_viennent_des_get_du_connecteur():
    lues = cles_lues("falkye.sources.subventions_federales")

    assert "recipient_legal_name" in lues
    assert "agreement_value" in lues
    assert "recipient_type" not in lues  # jamais demandé — c'est tout l'objet


def test_un_module_absent_ne_pretend_pas_lire():
    assert cles_lues("falkye.sources.inexistante") == set()


def test_une_source_grattee_dit_POURQUOI_elle_nest_pas_sondable():
    releve = sonder_source("rob_top_growing", "falkye.sources.rob_top_growing")

    assert "impossible" in releve
    assert "PAR NATURE" in releve["impossible"]
    assert releve["impossible"] == PAS_DE_SCHEMA


def test_une_source_sans_sonde_le_dit_au_lieu_de_rendre_du_vide():
    releve = sonder_source("source_inventee", "falkye.sources.inexistante")

    assert releve["impossible"] == "aucune sonde déclarée pour cette source"


def test_une_sonde_qui_tombe_ne_tue_pas_le_releve(monkeypatch):
    """Un portail injoignable coûte une source, jamais le relevé entier — même
    règle que l'ingestion depuis le 2026-09-07."""
    def _casse():
        raise RuntimeError("portail injoignable")

    monkeypatch.setitem(SONDES, "seao", _casse)

    releve = sonder_source("seao", "falkye.sources.seao")

    assert "sonde en échec" in releve["impossible"]
    assert "portail injoignable" in releve["impossible"]


def test_toutes_les_sources_actives_ont_une_sonde_ou_une_raison(registry):
    """Une source active absente de la table passerait sous silence. Ce test
    force à écrire soit une sonde, soit la raison de son absence."""
    actives = {s.id for s in registry.sources_actives() if s.connecteur}

    assert actives <= set(SONDES), actives - set(SONDES)


def test_le_releve_compte_le_remplissage_et_le_distinct(monkeypatch):
    monkeypatch.setitem(
        SONDES, "seao",
        lambda: ([{"a": 1, "b": None}, {"a": 1, "b": "x"}], "essai"),
    )

    releve = sonder_source("seao", "falkye.sources.seao")

    assert releve["champs"]["a"] == {"taux": 100.0, "distinctes": 1, "lu": False}
    assert releve["champs"]["b"]["taux"] == 50.0
