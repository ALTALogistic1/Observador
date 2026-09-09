"""LAQUELLE des unités a démarré ce processus — et le refus de le deviner.

`mode_de_lancement()` répondait « sous unité » sans dire laquelle. Deux unités
lancent le cycle, à 5 400 s et 43 200 s : la moitié de la réponse valait une
mauvaise réponse. Voir `falkye/delai_unite.py` pour la règle qui en sort.
"""
from __future__ import annotations

import pytest

from falkye.delai_unite import (
    UNITE_CYCLE_LIVRAISON,
    UNITE_CYCLE_OBSERVATION,
    delai_maximal,
)
from falkye.execution import unite_de_lancement


@pytest.fixture()
def sous_systemd(monkeypatch):
    monkeypatch.setenv("INVOCATION_ID", "5f2a1c")


def _cgroup(tmp_path, contenu):
    fichier = tmp_path / "cgroup"
    fichier.write_text(contenu, encoding="utf-8")
    return str(fichier)


def test_le_nom_de_lunite_se_lit_dans_le_groupe_de_controle(tmp_path, sous_systemd):
    """systemd pose le nom de l'unité dans le chemin du groupe de contrôle. Il
    dit ce que systemd A FAIT, là où une `Environment=` déclarée dans le fichier
    ne dirait que ce qu'on y a écrit."""
    chemin = _cgroup(tmp_path, "0::/system.slice/falkye-cycle-sans-livraison.service\n")

    assert unite_de_lancement(chemin) == UNITE_CYCLE_OBSERVATION


def test_lunite_de_livraison_se_distingue_de_celle_dobservation(tmp_path, sous_systemd):
    chemin = _cgroup(tmp_path, "0::/system.slice/falkye-cycle.service\n")

    assert unite_de_lancement(chemin) == UNITE_CYCLE_LIVRAISON


def test_hors_systemd_aucune_unite_nest_nommee(tmp_path, monkeypatch):
    """Sans `INVOCATION_ID`, personne ne surveille — et un groupe de contrôle
    résiduel ne doit pas faire croire le contraire."""
    monkeypatch.delenv("INVOCATION_ID", raising=False)
    chemin = _cgroup(tmp_path, "0::/system.slice/falkye-cycle.service\n")

    assert unite_de_lancement(chemin) is None


def test_un_cgroup_illisible_ne_nomme_rien(tmp_path, sous_systemd):
    """`None` n'est pas un échec, c'est l'absence d'un fait. Rendre l'unité la
    plus probable serait exactement le défaut qu'on retire."""
    assert unite_de_lancement(str(tmp_path / "absent")) is None


def test_un_cgroup_sans_nom_dunite_ne_nomme_rien(tmp_path, sous_systemd):
    assert unite_de_lancement(_cgroup(tmp_path, "0::/\n")) is None


def test_lunite_la_plus_imbriquee_gagne(tmp_path, sous_systemd):
    """Un `systemd-run` sous un service : c'est l'unité intérieure qui gouverne
    le délai de CE processus, pas celle qui l'englobe."""
    chemin = _cgroup(
        tmp_path, "0::/system.slice/falkye-cycle.service/run-r42.scope\n"
    )

    assert unite_de_lancement(chemin) == "run-r42.scope"


# --- Le repli ne vaut que pour l'unité qu'il décrit ------------------------


def test_le_repli_ne_sapplique_pas_a_une_autre_unite(monkeypatch):
    """`DELAI_REPLI_SECONDES` a été mesuré sur le cycle de livraison. L'appliquer
    au cycle d'observation reproduirait le défaut sous un autre nom : mieux vaut
    ne rien conclure que conclure avec le seuil du voisin."""
    monkeypatch.setattr("falkye.delai_unite._demander_a_systemd", lambda unite: None)

    delai = delai_maximal(UNITE_CYCLE_OBSERVATION)

    assert delai.secondes is None
    assert delai.lu is False
    assert UNITE_CYCLE_LIVRAISON in delai.provenance


def test_le_repli_sapplique_encore_a_lunite_quil_decrit(monkeypatch):
    monkeypatch.setattr("falkye.delai_unite._demander_a_systemd", lambda unite: None)

    delai = delai_maximal(UNITE_CYCLE_LIVRAISON)

    assert delai.secondes == 5400.0
    assert delai.lu is False


def test_delai_maximal_exige_de_nommer_lunite():
    """Le défaut d'hier rendait 5 400 s à qui ne demandait rien. Un appelant qui
    ne sait pas quelle unité a produit la ligne doit être OBLIGÉ de le dire."""
    with pytest.raises(TypeError):
        delai_maximal()
