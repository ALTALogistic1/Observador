"""L'adresse, de la source au dossier — quatre états, trois écarts.

⚠️ *Un champ absent des quatre colonnes veut dire « personne ici ne le
connaît » — jamais « la source ne l'a pas ».*
"""
from __future__ import annotations

import datetime as _dt

import pytest
from sqlalchemy import select

from falkye.models.company import Company
from falkye.models.signal import Signal
from falkye.sources.column_mapping import normaliser
from outils import adresse_par_connecteur as outil


# ---------------------------------------------------------------------------
# L'EXTRACTION PAR AST — lue dans le code, jamais recopiée
# ---------------------------------------------------------------------------

def test_les_cles_lues_sortent_du_CODE_et_non_dune_liste(tmp_path):
    """⚠️ *Une liste recopiée se désynchronise à la première clé ajoutée, et le
    garde-fou vérifierait alors sa propre copie.*"""
    module = tmp_path / "faux.py"
    module.write_text(
        "def lire(row):\n"
        "    a = row.get('adresse_complete')\n"
        "    b = row['ville_du_siege']\n"
        "    c = row.get(variable)\n"          # non littéral : invisible, à dessein
        "    return a, b, c\n",
        encoding="utf-8")
    assert outil.cles_lues_par_le_module(module) == {"adresse_complete", "ville_du_siege"}


def test_un_module_ILLISIBLE_rend_un_ensemble_vide_sans_lever(tmp_path):
    """*Un connecteur absent ou cassé ne doit pas faire tomber la mesure des
    autres.*"""
    assert outil.cles_lues_par_le_module(tmp_path / "absent.py") == set()
    casse = tmp_path / "casse.py"
    casse.write_text("def (", encoding="utf-8")
    assert outil.cles_lues_par_le_module(casse) == set()


def test_seul_un_RawSignal_compte_comme_PROMOTION(tmp_path):
    """⚠️ *Un `adresse=` dans un appel à autre chose ferait croire à une
    promotion qui n'a pas lieu* — `_CorporationResolue(adresse=…)` est interne."""
    module = tmp_path / "faux.py"
    module.write_text(
        "def f():\n"
        "    _Interne(adresse=x, ville=y)\n"
        "    return RawSignal(nom_entreprise=n, ville=v)\n",
        encoding="utf-8")
    assert outil.champs_promus_par_le_module(module) == {"ville"}


def test_un_champ_promu_a_None_nest_PAS_une_promotion(tmp_path):
    """*`adresse=None` remplit la signature, pas le champ.*"""
    module = tmp_path / "faux.py"
    module.write_text("def f():\n    return RawSignal(adresse=None, ville=v)\n",
                      encoding="utf-8")
    assert outil.champs_promus_par_le_module(module) == {"ville"}


@pytest.mark.parametrize("cle, attendu", [
    ("adresse_entreprise_adjudicataire", True),
    ("code_postal", True),
    ("municipalite", True),
    ("province", True),
    ("montant_octroye", False),
    ("nom_entreprise", False),
])
def test_lindice_dadresse_est_LARGE_a_dessein(cle, attendu):
    """*Mieux vaut lister un champ qui n'en est pas que taire celui qui l'est.*"""
    assert bool(outil.INDICE_DADRESSE.search(cle)) is attendu


# ---------------------------------------------------------------------------
# LA MESURE
# ---------------------------------------------------------------------------

@pytest.fixture()
def decor(db_session, monkeypatch):
    """Une source qui RANGE sans promouvoir, et une qui ne porte rien."""
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")

    a = Company(neq=None, nom_detecte="Sans NEQ inc.",
                nom_detecte_normalise=normaliser("Sans NEQ inc."))
    b = Company(neq=None, nom_detecte="Autre inc.",
                nom_detecte_normalise=normaliser("Autre inc."))
    db_session.add_all([a, b])
    db_session.flush()
    db_session.add_all([
        # Une source qui range un CODE POSTAL, pour lequel `RawSignal` n'a
        # aucun emplacement.
        Signal(company_id=b.id, source_id="seao_factice",
               signal_type_id="contrat",
               detected_at=_dt.datetime(2026, 1, 1),
               champs={"code_postal": "G6V 1A1"}),
        # ⚠️ Le motif EIMT : l'adresse est RANGÉE dans `champs`, avec un code
        # postal dedans.
        Signal(company_id=a.id, source_id="eimt",
               signal_type_id="recrutement_massif",
               detected_at=_dt.datetime(2026, 1, 1),
               champs={"adresse": "St-Isidore, QC J0L 2A1", "profession": "soudeur"}),
        # Une source dont AUCUN champ d'adresse n'est connu ici — ni déclaré,
        # ni lu, ni arrivé. ⚠️ Ça ne dit pas que la source n'en publie pas.
        Signal(company_id=b.id, source_id="source_sans_module",
               signal_type_id="subvention",
               detected_at=_dt.datetime(2026, 1, 1),
               champs={"montant_octroye": 50000, "programme": "X"}),
    ])
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def _sortie(capsys):
    return capsys.readouterr().out


def test_ce_que_loutil_ne_peut_pas_etablir_vient_AVANT_les_chiffres(decor, capsys):
    assert outil.main([]) == 0
    sortie = _sortie(capsys)
    assert sortie.index("QU'UNE SOURCE NE PUBLIE PAS D'ADRESSE") < sortie.index("eimt")
    assert "DÉCLARATION N'EST PAS UNE OBSERVATION" in sortie
    assert "description_tender" in sortie


def test_le_motif_EIMT_se_juge_EMPLACEMENT_PAR_EMPLACEMENT(decor, capsys):
    """⚠️ **Le défaut que le décor a révélé.**

    *`eimt` promeut bien `region` — donc « promeut quelque chose » est vrai, et
    masquerait que `adresse` reste dans le sac.* **C'est exactement le motif
    EIMT, et il se juge emplacement par emplacement.**
    """
    assert outil.main(["--source", "eimt"]) == 0
    sortie = _sortie(capsys)
    assert "PROMU en RawSignal         region" in sortie, sortie
    ligne = next(l for l in sortie.splitlines() if "MOTIF EIMT" in l)
    assert "adresse" in ligne, ligne
    assert "l'emplacement existe" in sortie


def test_un_champ_SANS_EMPLACEMENT_est_distingue_dun_champ_non_promu(decor, capsys):
    """⚠️ **`RawSignal` n'a AUCUN emplacement pour un code postal.**

    *Vérifié dans `falkye/sources/base.py` : `adresse`, `ville`, `region`, et
    rien d'autre.* **Donc aucun connecteur ne PEUT en promouvoir un** — et c'est
    le niveau le plus FORT du départageur.
    """
    from falkye.sources.base import RawSignal

    assert not hasattr(RawSignal("t", "n", None, "r"), "code_postal")
    assert outil.main(["--source", "seao_factice"]) == 0


def test_lemplacement_manquant_est_NOMME_dans_la_sortie(decor, capsys):
    assert outil.main(["--source", "seao_factice"]) == 0
    sortie = _sortie(capsys)
    assert "AUCUN EMPLACEMENT POUR CE CHAMP" in sortie
    assert "code_postal" in sortie
    assert "Aucun connecteur ne PEUT" in sortie


def test_une_source_SANS_champ_dadresse_ne_conclut_PAS_a_son_absence(decor, capsys):
    """⚠️ **La règle qui empêche de classer un fichier sur son nom.**"""
    assert outil.main(["--source", "source_sans_module"]) == 0
    sortie = _sortie(capsys)
    assert "AUCUN CHAMP D'ADRESSE NULLE PART" in sortie
    assert "Ça ne veut PAS dire que la source n'en publie pas" in sortie
    assert "personne ici ne le sait" in sortie
    assert "en ouvrant la source" in sortie


def test_PRESENT_et_REMPLI_sont_deux_colonnes(decor, capsys):
    """*Un champ présent à 100 % et rempli à 0 % est une promesse vide* —
    `description_tender`."""
    assert outil.main(["--source", "eimt"]) == 0
    sortie = _sortie(capsys)
    entete = next(l for l in sortie.splitlines() if "champ arrivé" in l)
    assert "présent" in entete and "rempli" in entete, entete
    assert "une promesse vide" in sortie


def test_le_CODE_POSTAL_ailleurs_dans_les_champs_est_compte(decor, capsys):
    """*Savoir si un code postal existe ailleurs change ce que la source vaut* —
    la ville est le niveau le plus faible du départageur."""
    assert outil.main(["--source", "eimt"]) == 0
    sortie = _sortie(capsys)
    ligne = next(l for l in sortie.splitlines() if "code postal existe QUELQUE PART" in l)
    assert ligne.strip().endswith("1 signal(aux)"), ligne
    assert "niveau le plus FAIBLE du départageur" in sortie


def test_les_exemples_montrent_des_VALEURS_reelles(decor, capsys):
    assert outil.main(["--source", "eimt", "--exemples", "3"]) == 0
    assert "· St-Isidore, QC J0L 2A1" in _sortie(capsys)


def test_il_NECRIT_RIEN(decor):
    avant = {c.id: c.neq for c in decor.execute(select(Company)).scalars()}
    assert outil.main([]) == 0
    decor.expire_all()
    assert {c.id: c.neq for c in decor.execute(select(Company)).scalars()} == avant
