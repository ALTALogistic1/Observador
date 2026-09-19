"""D'où viennent les restants, et de quelle nature ils sont.

⚠️ *Une ventilation des restants SEULE ne peut pas dire « surreprésentée »* — il
faut la même ventilation sur les résolus et le rapport des deux.
"""
from __future__ import annotations

import datetime as _dt
import re

import pytest
from sqlalchemy import select

from falkye.models.company import Company
from falkye.models.signal import Signal
from falkye.sources.column_mapping import normaliser
from outils import nature_des_restants as outil


def _compte(ligne: str) -> str:
    """Le nombre d'une ligne, **lu par motif** *(N144, N158)*."""
    trouve = re.search(r"\s(\d[\d ]*)\s+\d+\.\d %", ligne)
    assert trouve, ligne
    return trouve.group(1).strip()


# ---------------------------------------------------------------------------
# LES RÈGLES DE LECTURE — avant la mesure qui les emploie
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("nom, attendu", [
    ("9528-9393 Québec inc., Fabrication A.S. inc. & Maurice Milette", True),
    ("9281-7600 Québec inc. & Action SST inc.", True),
    # ⚠️ **Une conjonction ne suffit pas** : il faut DEUX formes juridiques.
    ("Gagnon et Fils inc.", False),
    ("Béton Bolduc inc.", False),
    ("Plomberie, chauffage et ventilation ltée", False),
    (None, False),
])
def test_un_champ_MULTI_ENTITES_demande_DEUX_formes_juridiques(nom, attendu):
    """⚠️ *La règle du chiffrage de la parenthèse comptait toute conjonction —
    17 sur 148. Les deux chiffres ne sont pas comparables.*"""
    assert outil.nomme_plusieurs_entites(nom) is attendu


@pytest.mark.parametrize("texte, attendu", [
    ("6775 Financial Dr, Suite 100, ON L5N0A4", {"ON"}),
    ("St-Isidore, QC J0L 2A", {"QC"}),
    # *On lit ce qui est ÉCRIT, pas ce qu'on devine.*
    ("Toronto, Ontario", set()),
    ("", set()),
    (None, set()),
])
def test_la_province_se_lit_par_JETON_jamais_par_sous_chaine(texte, attendu):
    assert outil.provinces_du_texte(texte) == attendu


# ---------------------------------------------------------------------------
# LA MESURE
# ---------------------------------------------------------------------------

@pytest.fixture()
def decor(db_session, monkeypatch):
    """Deux restants d'une source pancanadienne, un résolu d'une source
    québécoise, un consortium, et un doublon de graphie."""
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")

    restant_a = Company(neq=None, nom_detecte="Altis Human Resources (Ottawa) Inc.",
                        nom_detecte_normalise=normaliser("Altis Human Resources (Ottawa) Inc."))
    consortium = Company(neq=None, nom_detecte="9281-7600 Québec inc. & Action SST inc.",
                         nom_detecte_normalise=normaliser("9281-7600 Quebec inc"))
    # ⚠️ Deux dossiers, une seule entreprise : la casse seule les sépare.
    doublon_a = Company(neq=None, nom_detecte="AYE3D inc.",
                        nom_detecte_normalise=normaliser("AYE3D inc."))
    doublon_b = Company(neq="7777777777", nom_detecte="AYE3D Inc.",
                        nom_detecte_normalise=normaliser("AYE3D Inc."))
    resolu = Company(neq="8888888888", nom_detecte="Beton Bolduc inc.",
                     nom_detecte_normalise=normaliser("Beton Bolduc inc."))
    db_session.add_all([restant_a, consortium, doublon_a, doublon_b, resolu])
    db_session.flush()
    for company, source, champs in (
        (restant_a, "rob_top_growing", {"adresse": "150 Isabella St, Ottawa, ON K1S 1V7"}),
        (consortium, "rob_top_growing", {}),
        (doublon_a, "seao", {}),
        (doublon_b, "seao", {}),
        (resolu, "seao", {}),
    ):
        db_session.add(Signal(
            company_id=company.id, source_id=source,
            signal_type_id="recrutement_massif",
            detected_at=_dt.datetime(2026, 1, 1), champs=champs,
        ))
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def _sortie(capsys):
    return capsys.readouterr().out


def test_ce_que_la_mesure_ne_dira_pas_vient_AVANT_les_chiffres(decor, capsys):
    assert outil.main([]) == 0
    sortie = _sortie(capsys)
    assert sortie.index("QU'UNE ENTREPRISE SANS NEQ SOIT RÉCUPÉRABLE") < sortie.index(
        "dossiers au total")
    assert "L'ORIGINE NE DIT PAS LA PERTINENCE" in sortie
    assert "NE DIT PAS « SURREPRÉSENTÉE »" in sortie


def test_la_ventilation_rend_les_DEUX_populations_et_leur_rapport(decor, capsys):
    """⚠️ *« 12 % des restants viennent de X » ne se compare à rien.*"""
    assert outil.main([]) == 0
    bloc = _sortie(capsys).split("1. PAR SOURCE")[1]
    # ⚠️ Le TITRE de section contient déjà ces mots : on vise la ligne d'en-tête
    # du tableau, celle qui commence par « source ».
    entete = next(l for l in bloc.splitlines() if l.strip().startswith("source"))
    for colonne in ("restants", "résolus", "rapport"):
        assert colonne in entete, (colonne, entete)
    ligne = next(l for l in bloc.splitlines() if l.strip().startswith("rob_top_growing"))
    # ⚠️ 2 restants, 0 résolu : c'est le cas le PLUS fort, pas un cas manquant.
    # *Écrire `—` y masquerait ce que la mesure cherche.*
    assert ligne.split()[1] == "2", ligne
    assert "AUCUN" in ligne and "JAMAIS résolue" in ligne, ligne
    autre = next(l for l in bloc.splitlines() if l.strip().startswith("seao"))
    assert "×0.3" in autre, autre


def test_les_colonnes_ne_se_presentent_PAS_comme_une_partition(decor, capsys):
    """*Un dossier cumule les signaux, donc il compte dans chaque source.*"""
    assert outil.main([]) == 0
    assert "Les colonnes ne s'additionnent pas au total" in _sortie(capsys)


def test_ladresse_est_rendue_PAR_SOURCE_avec_la_province(decor, capsys):
    assert outil.main([]) == 0
    sortie = _sortie(capsys)
    bloc = sortie.split("code post.")[1]
    assert "ON 1" in bloc, bloc
    assert "immatriculée au Québec" in sortie


def test_les_MULTI_ENTITES_sont_comptes_avec_la_regle_stricte(decor, capsys):
    assert outil.main([]) == 0
    sortie = _sortie(capsys)
    ligne = next(l for l in sortie.splitlines() if "PLUSIEURS entités" in l)
    assert _compte(ligne) == "1", ligne
    assert "17 sur 148" in sortie and "NE sont PAS comparables" in sortie.replace(
        "ne sont PAS comparables", "NE sont PAS comparables")
    assert "le modèle n'en permet qu'un" in sortie


def test_les_DOUBLONS_exacts_sont_comptes_et_le_PLANCHER_est_dit(decor, capsys):
    assert outil.main([]) == 0
    sortie = _sortie(capsys)
    groupes = next(l for l in sortie.splitlines() if "forme normalisée IDENTIQUE" in l)
    assert groupes.split()[-1] == "1", groupes
    resolu = next(l for l in sortie.splitlines() if "porte DÉJÀ un NEQ" in l)
    assert resolu.split()[-1] == "1", resolu
    assert "PHILIPS ÉLECTRONIQUE LTÉE" in sortie
    assert "Ce compte est donc un PLANCHER" in sortie


def test_les_groupes_de_doublons_se_lisent(decor, capsys):
    assert outil.main(["--comparer", "5"]) == 0
    bloc = _sortie(capsys).split("quelques groupes")[1]
    assert "AYE3D inc." in bloc and "AYE3D Inc." in bloc
    assert "7777777777" in bloc


def test_il_NECRIT_RIEN(decor):
    avant = {c.id: c.neq for c in decor.execute(select(Company)).scalars()}
    assert outil.main([]) == 0
    decor.expire_all()
    assert {c.id: c.neq for c in decor.execute(select(Company)).scalars()} == avant


def test_les_echelles_ne_bougent_pas(decor):
    from falkye import resolution

    assert outil.main([]) == 0
    assert resolution.SEUIL_RESOLUTION_CONFIANTE == 92.0
    assert resolution.SEUIL_AMBIGUITE_ECART_MIN == 8.0
