"""L'écriture des départages — **restreinte au code postal complet**.

⚠️ *Un départage non écrit se reprend; un départage écrit à tort coûte une
identité.* **La restriction se trompe dans le bon sens, et l'outil doit DIRE
lesquels il n'a pas touchés** — sinon la différence se lit comme une perte.
"""
from __future__ import annotations

import re

import pytest
from sqlalchemy import select

from falkye.models.company import Company, StatutResolution
from falkye.models.diagnostic_journal import DiagnosticJournal
from falkye.models.req_entry import REQEntry
from falkye.sources.column_mapping import normaliser
from outils import ecriture_des_departages as outil


def _entree(db_session, neq, nom, **kw):
    db_session.add(REQEntry(neq=neq, nom=nom, nom_normalise=normaliser(nom),
                            statut="IMMATRICULÉE", **kw))


@pytest.fixture()
def decor(db_session, tmp_path, monkeypatch):
    """Un départage par CODE COMPLET, un par RÉGION DE TRI, un par VILLE.

    *Un décor où tout se pose ne verrouillerait pas la restriction.*
    """
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")
    monkeypatch.setattr(outil, "DOSSIER_INSTANTANE", tmp_path)

    # (a) CODE COMPLET — même région de tri des deux côtés. ⇒ à écrire
    _entree(db_session, "1000000001", "Gagnon Freres inc", ville="Levis",
            code_postal="G6V 1A1")
    _entree(db_session, "1000000002", "Gagnon Freres ltee", ville="Levis",
            code_postal="G6V 5X9")
    par_code = Company(neq=None, nom_detecte="Gagnon Freres", ville="Levis",
                       code_postal="G6V 5X9",
                       nom_detecte_normalise=normaliser("Gagnon Freres"))

    # (b) RÉGION DE TRI — c'est `KONE`. ⇒ EN SUSPENS
    _entree(db_session, "4000000001", "Wazoom Studio inc", ville="CP 235",
            code_postal="G5R 3Y8")
    _entree(db_session, "4000000002", "Wazoom Studio ltee", ville="Montreal",
            code_postal="H2N 1A1")
    par_region = Company(neq=None, nom_detecte="Wazoom Studio",
                         code_postal="G5R 3A7",
                         nom_detecte_normalise=normaliser("Wazoom Studio"))

    # (c) VILLE — aucun code postal nulle part. ⇒ EN SUSPENS
    _entree(db_session, "2000000001", "Artelia Canada inc", ville="Quebec")
    _entree(db_session, "2000000002", "Artelia Canada ltee", ville="Laval")
    par_ville = Company(neq=None, nom_detecte="Artelia Canada", ville="Laval",
                        nom_detecte_normalise=normaliser("Artelia Canada"))

    db_session.add_all([par_code, par_region, par_ville])
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return {"session": db_session, "tmp": tmp_path,
            "par_code": par_code.id, "par_region": par_region.id,
            "par_ville": par_ville.id}


def _sortie(capsys):
    return capsys.readouterr().out


def _compte(ligne: str) -> str:
    """Le nombre d'une ligne de tableau, **lu par motif**.

    ⚠️ *N144 dit exactement ça, et ce test l'a refait dans l'heure* :
    `« 2   66.7 % »` se découpe en TROIS jetons, donc `[-2]` rend le
    pourcentage. **Une note écrite ne protège pas le doigt qui tape.**
    """
    trouve = re.search(r"\s(\d[\d ]*)\s+\d+\.\d %", ligne)
    assert trouve, ligne
    return trouve.group(1).strip()


# ---------------------------------------------------------------------------
# LA RESTRICTION — et ce qu'elle laisse en suspens
# ---------------------------------------------------------------------------

def test_sans_appliquer_rien_nest_ecrit(decor, capsys):
    """**Le rapport est le mode par défaut.**"""
    assert outil.main([]) == 0
    decor["session"].expire_all()
    assert decor["session"].get(Company, decor["par_code"]).neq is None
    assert "rien n'a été écrit" in _sortie(capsys).lower()


def test_SEUL_le_code_complet_est_pose(decor, capsys):
    """⚠️ *`L5N` ne dit que « quelque part à Mississauga ».*"""
    assert outil.main(["--appliquer"]) == 0
    session = decor["session"]
    session.expire_all()
    assert session.get(Company, decor["par_code"]).neq == "1000000002"
    assert session.get(Company, decor["par_region"]).neq is None, "la région de tri a écrit"
    assert session.get(Company, decor["par_ville"]).neq is None, "la ville a écrit"


def test_loutil_DIT_lesquels_il_na_pas_touches(decor, capsys):
    """⚠️ **Un outil qui écrit 1 sur 3 doit dire lesquels**, sinon la différence
    se lit comme une perte."""
    assert outil.main([]) == 0
    sortie = _sortie(capsys)
    ligne = next(l for l in sortie.splitlines() if "LAISSÉS EN SUSPENS" in l)
    assert _compte(ligne) == "2", ligne
    assert "Ils ne sont pas refusés" in sortie
    assert "chantier 22" in sortie
    for nom in ("région de tri", "ville"):
        l = next(x for x in sortie.splitlines()
                 if x.strip().startswith(nom) and "SUSPENS" in x)
        assert "→ EN SUSPENS" in l, l


def test_les_suspendus_se_lisent_un_par_un(decor, capsys):
    """*50 paires sur 292 ne disent pas où les douteux tombent dossier par
    dossier* — donc les suspendus se relisent."""
    assert outil.main(["--suspendus", "10"]) == 0
    bloc = _sortie(capsys).split("LES DÉPARTAGES EN SUSPENS")[1]
    assert "Wazoom Studio" in bloc and "Artelia Canada" in bloc
    assert "⛔ non écrit" in bloc
    assert "tranché par : région de tri" in bloc


def test_les_paires_a_poser_montrent_le_code_complet_des_deux_cotes(decor, capsys):
    assert outil.main(["--comparer", "10"]) == 0
    bloc = _sortie(capsys).split("LES PAIRES À POSER")[1]
    assert "Gagnon Freres" in bloc
    assert "complet=G6V1A1" in bloc and "complet=G6V5X9" in bloc
    assert "Wazoom" not in bloc, "un suspendu est passé dans le lot à poser"


# ---------------------------------------------------------------------------
# LA MACHINERIE EMPRUNTÉE — conservation, instantané, retour arrière
# ---------------------------------------------------------------------------

def test_un_NEQ_DEJA_PRIS_nest_pas_pose_et_se_journalise(decor, capsys):
    """⚠️ *Conservation toujours, aucune fusion* — décision du 16 septembre."""
    session = decor["session"]
    session.add(Company(neq="1000000002", nom_detecte="Gagnon Freres Detenteur",
                        nom_detecte_normalise=normaliser("Gagnon Freres Detenteur")))
    session.commit()

    assert outil.main(["--appliquer"]) == 0
    session.expire_all()
    assert session.get(Company, decor["par_code"]).neq is None, "le NEQ a été volé"
    assert session.execute(select(DiagnosticJournal)).scalars().all()


def test_linstantane_est_ecrit_et_DEFAIT_le_geste(decor):
    """⚠️ *Sans commande pour défaire, « réversible » reste une intention.*"""
    session = decor["session"]
    assert outil.main(["--appliquer"]) == 0
    session.expire_all()
    assert session.get(Company, decor["par_code"]).neq == "1000000002"

    (instantane,) = list(decor["tmp"].glob("departages-*.json"))
    assert outil.main(["--defaire", str(instantane)]) == 0
    session.expire_all()
    company = session.get(Company, decor["par_code"])
    assert company.neq is None
    assert company.statut_resolution != StatutResolution.RESOLU


def test_linstantane_ne_porte_PAS_les_champs_de_travail(decor):
    """*Il porte l'état d'avant, pas la façon dont la passe a raisonné.*"""
    import json

    assert outil.main(["--appliquer"]) == 0
    (instantane,) = list(decor["tmp"].glob("departages-*.json"))
    contenu = json.loads(instantane.read_text(encoding="utf-8"))
    for paire in contenu["a_poser"]:
        assert not [k for k in paire if k.startswith("_")], paire
        assert "champs_avant" in paire and "statut_avant" in paire


def test_la_machinerie_est_EMPRUNTEE_et_non_recopiee():
    """⚠️ **Cas 41 sur un chemin d'écriture.** *Une règle de conservation
    recopiée qui diverge perd une identité, et l'instantané de l'autre copie ne
    la rend pas.*"""
    from outils import pose_du_neq, reresolution_neq

    for nom in ("resoudre_les_collisions", "poser_les_neq",
                "journaliser_les_conserves", "ecrire_instantane", "defaire"):
        assert getattr(outil.pose_du_neq, nom) is getattr(pose_du_neq, nom)
    assert reresolution_neq._defaire is pose_du_neq.defaire
    assert reresolution_neq.PRETENDANTS_MAX_POUR_TRANCHER is (
        pose_du_neq.PRETENDANTS_MAX_POUR_TRANCHER)


def test_les_echelles_ne_bougent_pas(decor):
    from falkye import resolution

    assert outil.main([]) == 0
    assert resolution.SEUIL_RESOLUTION_CONFIANTE == 92.0
    assert resolution.SEUIL_AMBIGUITE_ECART_MIN == 8.0
