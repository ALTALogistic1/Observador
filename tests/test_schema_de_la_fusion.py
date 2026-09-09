"""Ce que la vérification de fusion dit — et ce qu'elle doit refuser de taire.

Deux conditions posées avec la décision, et un test pour chacune :

1. **La limite est dans la SORTIE**, pas dans la documentation. Une vérification
   qui ne nomme pas ce qu'elle ne couvre pas remplace une discipline par un
   mécanisme qui rassure au-delà de sa portée.
2. **Elle parle même quand elle ne trouve rien.** « Cette fusion n'ajoute rien
   au schéma » est une information; un silence ne distingue pas une
   vérification qui a tourné sans rien trouver d'une qui n'a pas tourné.
"""
from __future__ import annotations

from outils.schema_de_la_fusion import LIMITE, comparer, relever, rendre


def _releve(bases):
    return {"revision": "abc1234", "releve_le": "2026-09-09T03:00:00+00:00", "bases": bases}


TABLE = {"colonnes": {"id": "INTEGER", "nom": "VARCHAR(50)"}, "index": {}}


# --- Condition 1 : la limite voyage avec le rapport -------------------------


def test_la_limite_est_dans_la_sortie_quand_il_y_a_des_changements():
    avant = _releve({"produit": {"t": TABLE}})
    apres = _releve({"produit": {"t": {"colonnes": {**TABLE["colonnes"], "ville": "VARCHAR(80)"}, "index": {}}}})

    rapport = rendre(comparer(avant, apres), "aaa", "bbb")

    assert LIMITE in rapport
    assert "dérive déjà présente en production" in rapport


def test_la_limite_est_dans_la_sortie_meme_quand_il_ny_a_rien():
    """Surtout là : c'est le rapport vide qu'on serait tenté de raccourcir."""
    releve = _releve({"produit": {"t": TABLE}})

    rapport = rendre(comparer(releve, releve), "aaa", "aaa")

    assert LIMITE in rapport


# --- Condition 2 : elle parle quand elle ne trouve rien ---------------------


def test_aucun_changement_produit_une_phrase_pas_un_silence():
    releve = _releve({"produit": {"t": TABLE}})

    rapport = rendre(comparer(releve, releve), "aaa", "aaa")

    assert "n'ajoute rien au schéma" in rapport
    assert len(rapport.strip().splitlines()) > 3


# --- Ce que la comparaison voit --------------------------------------------


def test_une_colonne_ajoutee_est_vue():
    avant = _releve({"produit": {"t": TABLE}})
    apres = _releve({"produit": {"t": {"colonnes": {**TABLE["colonnes"], "ville": "VARCHAR(80)"}, "index": {}}}})

    changements = comparer(avant, apres)

    assert changements["produit"]["colonnes"] == ["t.ville  VARCHAR(80)"]


def test_un_index_unique_est_vu_avec_son_unicite():
    """L'unicité n'est pas un détail de performance : c'est une garantie, et
    c'est celle qui manquait en production le 2026-09-08."""
    avant = _releve({"produit": {"t": TABLE}})
    apres = _releve({"produit": {"t": {
        "colonnes": TABLE["colonnes"],
        "index": {"ix_t_nom": {"colonnes": ["nom"], "unique": True}},
    }}})

    (index,) = comparer(avant, apres)["produit"]["index"]

    assert index.startswith("UNIQUE ")
    assert "ix_t_nom" in index


def test_une_table_neuve_ne_reliste_pas_ses_colonnes():
    """Une table neuve arrive entière — détailler ses colonnes noierait les
    ajouts qui, eux, portent sur des tables déjà en production."""
    avant = _releve({"produit": {}})
    apres = _releve({"produit": {"t": TABLE}})

    changements = comparer(avant, apres)

    assert changements["produit"]["tables"] == ["t"]
    assert changements["produit"]["colonnes"] == []


def test_les_deux_bases_sont_comparees_separement():
    avant = _releve({"produit": {"t": TABLE}, "miroirs": {"m": TABLE}})
    apres = _releve({
        "produit": {"t": TABLE},
        "miroirs": {"m": {"colonnes": {**TABLE["colonnes"], "x": "INTEGER"}, "index": {}}},
    })

    changements = comparer(avant, apres)

    assert "produit" not in changements
    assert changements["miroirs"]["colonnes"] == ["m.x  INTEGER"]


# --- La troisième catégorie, celle qu'on oublie -----------------------------


def test_ce_qui_est_retire_du_modele_est_signale_comme_non_retire_de_la_base():
    """La chaîne n'AJOUTE que. Une colonne retirée du modèle reste en
    production indéfiniment, et c'est le seul endroit du flux où l'écart entre
    le modèle et la base se creuse en silence."""
    avant = _releve({"produit": {"t": {
        "colonnes": {**TABLE["colonnes"], "obsolete": "TEXT"},
        "index": {"ix_t_obsolete": {"colonnes": ["obsolete"], "unique": False}},
    }}})
    apres = _releve({"produit": {"t": TABLE}})

    retires = comparer(avant, apres)["produit"]["retires_du_modele"]

    assert "colonne t.obsolete" in retires
    assert "index ix_t_obsolete (sur t)" in retires

    rapport = rendre(comparer(avant, apres), "aaa", "bbb")
    assert "la chaîne ne les retirera pas de la base" in rapport
    assert "geste manuel et destructif" in rapport


def test_une_table_retiree_du_modele_est_signalee():
    avant = _releve({"produit": {"t": TABLE, "vieille": TABLE}})
    apres = _releve({"produit": {"t": TABLE}})

    assert "table vieille" in comparer(avant, apres)["produit"]["retires_du_modele"]


# --- Le relevé vient des vrais modèles -------------------------------------


def test_le_releve_couvre_les_deux_bases_du_projet():
    """Un relevé qui n'aurait qu'une base laisserait la moitié du schéma hors
    de la vérification, sans que rien ne le dise."""
    releve = relever()

    assert set(releve["bases"]) == {"produit", "miroirs"}
    assert "companies" in releve["bases"]["produit"]
    assert "req_entries" in releve["bases"]["miroirs"]
    assert releve["revision"]


def test_le_releve_nomme_les_index_uniques_du_vrai_modele():
    """Verrouille le lien avec le modèle réel : si `repli_id` perdait son
    unicité, ce test tomberait — et c'est la garantie qui manquait déjà une
    fois en production."""
    index = relever()["bases"]["produit"]["journal_exploitation"]["index"]

    assert index["ix_journal_exploitation_repli_id"]["unique"] is True
