"""Le départageur d'adresse sur les ambigus — et les trois choses qu'il doit rendre.

⚠️ *La non-régression sur les retenus est un CRITÈRE* : elle passe AVANT tout
chiffre, et l'outil sort en erreur si elle tombe.

⚠️ *La ville ne parle jamais là où le code postal exclut tout le monde* — et le
décor le vérifie sur un dossier où la ville aurait tranché sans hésiter.
"""
from __future__ import annotations

import datetime as _dt
import re

import pytest
from sqlalchemy import select

from falkye.models.company import Company
from falkye.models.req_entry import REQEntry
from falkye.models.signal import Signal
from falkye.sources.column_mapping import normaliser
from outils import departage_par_ladresse as outil
from tests.conftest import compte_de_la_ligne as _compte


def _entree(db_session, neq, nom, **kw):
    db_session.add(REQEntry(neq=neq, nom=nom, nom_normalise=normaliser(nom),
                            statut="IMMATRICULÉE", **kw))


@pytest.fixture()
def decor(db_session, monkeypatch):
    """Un retenu et CINQ ambigus, **un par comportement du départageur**.

    *Un décor où l'adresse sépare tout ne verrouillerait ni le repli ni son
    interdit.*
    """
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")

    # (0) RETENU — le nom tranche seul; l'adresse ne doit jamais le revoir.
    _entree(db_session, "9000000001", "Fisher Scientific Canada inc",
            ville="Ottawa", code_postal="K1B 5N1")
    retenu = Company(neq=None, nom_detecte="Fisher Scientific Canada inc",
                     ville="Laval", code_postal="H7A 1B1",
                     nom_detecte_normalise=normaliser("Fisher Scientific Canada inc"))

    # (a) séparé par le CODE POSTAL COMPLET — MÊME région de tri des deux côtés :
    #     seule la résolution fine tranche, et c'est le cas `TRIGONIX`.
    _entree(db_session, "1000000001", "Gagnon Freres inc", ville="Levis",
            code_postal="G6V 1A1")
    _entree(db_session, "1000000002", "Gagnon Freres ltee", ville="Levis",
            code_postal="G6V 5X9")
    par_code = Company(neq=None, nom_detecte="Gagnon Freres", ville="Levis",
                       nom_detecte_normalise=normaliser("Gagnon Freres"))

    # (a2) séparé par la RÉGION DE TRI — les codes COMPLETS s'excluent tous.
    #      C'est `Wazoom`, et c'est la porte à ne pas fermer.
    _entree(db_session, "4000000001", "Wazoom Studio inc", ville="CP 235",
            code_postal="G5R 3Y8")
    _entree(db_session, "4000000002", "Wazoom Studio ltee", ville="Montreal",
            code_postal="H2N 1A1")
    par_region = Company(neq=None, nom_detecte="Wazoom Studio",
                         code_postal="G5R 3A7",
                         nom_detecte_normalise=normaliser("Wazoom Studio"))

    # (a3) GAGNANT DÉPLACÉ, et c'est la route unique : les deux candidats
    #      partagent la région de tri, donc la forme d'avant tombait sur la
    #      VILLE et désignait `inc`. Le code complet désigne `ltee`.
    _entree(db_session, "5000000001", "Boyer Jardins inc", ville="Laval",
            code_postal="H7A 1B1")
    _entree(db_session, "5000000002", "Boyer Jardins ltee", ville="Quebec",
            code_postal="H7A 5X9")
    deplace = Company(neq=None, nom_detecte="Boyer Jardins", ville="Laval",
                      code_postal="H7A 5X9",
                      nom_detecte_normalise=normaliser("Boyer Jardins"))

    # (b) séparé par la VILLE EN REPLI — aucun code postal nulle part
    _entree(db_session, "2000000001", "Artelia Canada inc", ville="Quebec")
    _entree(db_session, "2000000002", "Artelia Canada ltee", ville="Laval")
    par_ville = Company(neq=None, nom_detecte="Artelia Canada", ville="Laval",
                        nom_detecte_normalise=normaliser("Artelia Canada"))

    # (c) LE FAIT LES EXCLUT TOUS — et la ville aurait tranché sans hésiter
    _entree(db_session, "3000000001", "Zebulon Metaux inc", ville="Laval",
            code_postal="H7A 1B1")
    _entree(db_session, "3000000002", "Zebulon Metaux ltee", ville="Levis",
            code_postal="G6V 1A1")
    exclut = Company(neq=None, nom_detecte="Zebulon Metaux", ville="Levis",
                     code_postal="J0L 2A1",
                     nom_detecte_normalise=normaliser("Zebulon Metaux"))

    db_session.add_all([retenu, par_code, par_region, deplace, par_ville, exclut])
    db_session.flush()
    db_session.add(Signal(
        company_id=par_code.id, source_id="eimt", signal_type_id="recrutement_massif",
        detected_at=_dt.datetime(2026, 1, 1),
        champs={"adresse": "Levis, QC G6V 5X9"},
    ))
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def _sortie(capsys):
    return capsys.readouterr().out




def test_le_decor_donne_UN_retenu_et_CINQ_ambigus(decor, capsys):
    assert outil.main(["--echantillon", "0"]) == 0
    sortie = _sortie(capsys)
    assert "dont RETENUS      : 1" in sortie, sortie
    assert "dont AMBIGUS      : 5" in sortie, sortie


def test_ce_que_loutil_ne_dira_pas_vient_AVANT_les_chiffres(decor, capsys):
    assert outil.main(["--echantillon", "0"]) == 0
    sortie = _sortie(capsys)
    assert sortie.index("NE DIRA PAS") < sortie.index("dont AMBIGUS")
    assert "IL N'EN CONFIRME AUCUN" in sortie
    assert "LA VILLE NE PARLE JAMAIS LÀ OÙ LE CODE POSTAL A EXCLU TOUT LE MONDE" in sortie
    assert "L'ACTIVITÉ N'EST PAS CONSTRUITE" in sortie


# ---------------------------------------------------------------------------
# 1. LA NON-RÉGRESSION — un critère, et il passe en PREMIER
# ---------------------------------------------------------------------------

def test_la_non_regression_est_rendue_AVANT_ce_que_ladresse_separe(decor, capsys):
    """*« Critère, pas effet secondaire acceptable » — donc avant les chiffres
    qu'elle conditionne.*"""
    assert outil.main(["--echantillon", "0"]) == 0
    sortie = _sortie(capsys)
    assert sortie.index("NON-RÉGRESSION SUR LES RETENUS") < sortie.index(
        "CE QUE L'ADRESSE SÉPARE")
    assert "REFUSÉS par la garde                 :         1" in sortie, sortie
    assert "départages prononcés sur un retenu :         0" in sortie, sortie
    assert "Aucun retenu n'est re-décidé par l'adresse" in sortie


def test_le_critere_ECHOUE_BRUYAMMENT_si_la_garde_tombe(decor, capsys, monkeypatch):
    """⚠️ **Un critère qu'on ne peut pas faire échouer n'en est pas un.**

    *On retire la garde et on vérifie que l'outil SORT EN ERREUR au lieu de
    continuer* — sinon « non-régression vérifiée » ne veut rien dire.
    """
    monkeypatch.setattr(outil, "departager_le_dossier",
                        lambda matches, faits, **kw: (None, []))
    assert outil.main(["--echantillon", "0"]) == 1
    sortie = _sortie(capsys)
    assert "CRITÈRE ÉCHOUÉ" in sortie
    assert "Rien de ce qui suit ne doit être lu" in sortie
    assert "CE QUE L'ADRESSE SÉPARE" not in sortie


# ---------------------------------------------------------------------------
# 2. LES DEUX NIVEAUX — et l'interdit du repli
# ---------------------------------------------------------------------------

def test_chaque_niveau_separe_SON_dossier(decor, capsys):
    """*Un décor où un seul niveau sépare tout ne verrouillerait pas la
    ventilation.*"""
    assert outil.main(["--echantillon", "0"]) == 0
    bloc = _sortie(capsys).split("2. CE QUE L'ADRESSE SÉPARE")[1]
    # ⚠️ Les titres COMPLETS : « RÉGION DE TRI » tout court apparaît aussi dans
    # le préambule en prose, et le test lirait alors le décor.
    attendus = {"CODE POSTAL COMPLET — un immeuble": "2",   # Gagnon + Boyer
                "RÉGION DE TRI — la finesse": "1",           # Wazoom
                "VILLE — en repli": "1"}                     # Artelia
    for titre, combien in attendus.items():
        assert _compte(next(l for l in bloc.splitlines() if titre in l)) == combien, titre
    total = next(l for l in bloc.splitlines() if "SÉPARÉS PAR L'ADRESSE" in l)
    assert _compte(total) == "4", total


def test_la_REGION_DE_TRI_tranche_la_ou_le_code_complet_EXCLUT_TOUT(decor, capsys):
    """⚠️ **La porte à ne pas fermer** — sans elle, `Wazoom` disparaîtrait."""
    assert outil.main(["--echantillon", "0"]) == 0
    sortie = _sortie(capsys)
    bloc = sortie.split("▸ CODE POSTAL COMPLET")[1].split("▸ RÉGION DE TRI")[0]
    ligne = next(l for l in bloc.splitlines() if "exclut tous" in l)
    assert "repli (même fait, dégradé)" in ligne, ligne
    assert _compte(ligne) == "2", ligne   # Wazoom + le dossier que la région exclut



def test_la_ville_NE_PARLE_PAS_quand_la_region_de_tri_exclut_tout(decor, capsys):
    """⚠️ *La ville aurait désigné `3000000002` sans hésiter. Elle ne parle pas.*"""
    assert outil.main(["--echantillon", "0"]) == 0
    sortie = _sortie(capsys)
    bloc = sortie.split("▸ RÉGION DE TRI")[1].split("▸ VILLE")[0]
    ligne = next(l for l in bloc.splitlines() if "exclut tous" in l)
    assert "la ville NE PARLE PAS" in ligne, ligne
    assert _compte(ligne) == "1", ligne


def test_le_CRITERE_interdit_une_PERTE_et_un_deplacement_INEXPLIQUE(decor, capsys):
    """⚠️ **Le critère du découpage, dans sa forme.**

    *« Aucun gagnant déplacé » interdirait à un niveau fin de corriger un niveau
    grossier — ce qu'on lui demande.* **Ce qui est interdit est un gagnant
    déplacé SANS qu'un niveau plus fin l'explique.**
    """
    assert outil.main(["--echantillon", "0"]) == 0
    sortie = _sortie(capsys)
    perdus = next(l for l in sortie.splitlines() if "PERDUS — séparés avant" in l)
    expliques = next(l for l in sortie.splitlines() if "expliqués par un niveau" in l)
    inexpliques = next(l for l in sortie.splitlines() if "INEXPLIQUÉS" in l)
    assert perdus.split()[-1] == "0", perdus
    assert expliques.split()[-1] == "1", expliques      # Boyer Jardins
    assert inexpliques.split()[-1] == "0", inexpliques
    assert "LE CRITÈRE N'EST PAS « aucun gagnant déplacé »" in sortie
    assert "Un départage PERDU reste interdit sans condition" in sortie


def test_la_paire_DEPLACEE_se_lit_en_entier(decor, capsys):
    """*« Le niveau qui a tranché dans chaque forme, les codes postaux du
    dossier, et ceux des deux gagnants — l'ancien et le nouveau. »*"""
    assert outil.main(["--echantillon", "0"]) == 0
    bloc = _sortie(capsys).split("DÉPLACEMENT(S)")[1]
    assert "Boyer Jardins" in bloc
    assert "forme D'AVANT        : tranché par ville" in bloc, bloc
    assert "forme À TROIS NIVEAUX: tranché par code postal complet" in bloc, bloc
    assert "ANCIEN gagnant" in bloc and "NOUVEAU gagnant" in bloc
    assert "5000000001" in bloc and "5000000002" in bloc
    assert "H7A1B1" in bloc and "H7A5X9" in bloc


def test_un_deplacement_INEXPLIQUE_fait_sortir_en_erreur(decor, capsys, monkeypatch):
    """⚠️ *Un critère qu'on ne peut pas faire échouer n'en est pas un.*"""
    from outils import departageur_adresse as da

    monkeypatch.setattr(
        outil, "expliquer_le_deplacement",
        lambda *a: da.Deplacement("ville", "code postal complet", 0, 1,
                                  False, da.PAS_PLUS_FIN),
    )
    assert outil.main(["--echantillon", "0"]) == 1
    sortie = _sortie(capsys)
    assert "CRITÈRE ÉCHOUÉ" in sortie
    assert "CE QUE CHAQUE NIVEAU APPORTE SEUL" not in sortie
    # ⚠️ La paire reste LUE avant le refus : *un critère qui échoue sans montrer
    # sur quoi ne laisse rien à examiner.*
    assert "Boyer Jardins" in sortie


def test_le_code_complet_AJOUTE_ce_que_la_region_seule_ratait(decor, capsys):
    """*`Gagnon Freres` partage `G6V` avec les deux candidats : la forme d'avant
    ne tranchait pas. Le code complet, si.*"""
    assert outil.main(["--echantillon", "0"]) == 0
    sortie = _sortie(capsys)
    ligne = next(l for l in sortie.splitlines() if "AJOUTÉS par le code complet" in l)
    assert ligne.split()[-1] == "1", ligne
    avant = next(l for l in sortie.splitlines() if "forme D AVANT" in l)
    apres = next(l for l in sortie.splitlines() if "forme À TROIS NIVEAUX" in l)
    assert avant.split()[-1] == "3" and apres.split()[-1] == "4", (avant, apres)


def test_le_CRITERE_du_decoupage_echoue_bruyamment(decor, capsys, monkeypatch):
    """⚠️ *Un critère qu'on ne peut pas faire échouer n'en est pas un.*

    On casse la forme d'avant pour qu'elle prétende avoir tranché partout, et on
    vérifie que l'outil SORT EN ERREUR plutôt que d'imprimer la suite.
    """
    from outils import departageur_adresse as da

    vrai = outil.departager_ladresse

    def _ment(faits, concurrents, niveaux=da.NIVEAUX):
        if niveaux is da.NIVEAUX_DAVANT:
            return da.Departage(outil.DEPARTAGE, da.NIVEAU_CODE_POSTAL, 0, ())
        return vrai(faits, concurrents, niveaux=niveaux)

    monkeypatch.setattr(outil, "departager_ladresse", _ment)
    assert outil.main(["--echantillon", "0"]) == 1
    sortie = _sortie(capsys)
    assert "CRITÈRE ÉCHOUÉ" in sortie
    assert "CE QUE CHAQUE NIVEAU APPORTE SEUL" not in sortie


def test_ce_que_chaque_niveau_apporte_SEUL_est_rendu(decor, capsys):
    """*Un niveau dont la colonne « LUI SEUL » est vide ne mérite pas son rang.*"""
    assert outil.main(["--echantillon", "0"]) == 0
    sortie = _sortie(capsys)
    assert "3. CE QUE CHAQUE NIVEAU APPORTE SEUL" in sortie
    bloc = sortie.split("joué SEUL sur les")[1]
    # ⚠️ Joué SEUL, le code complet ne couvre QUE `Gagnon Freres` : `Wazoom` lui
    # échappe (ses codes complets s'excluent) faute de repli vers la région.
    ligne = next(l for l in bloc.splitlines() if l.strip().startswith("code postal complet"))
    assert ligne.split()[-2] == "2", ligne
    ville = next(l for l in bloc.splitlines() if l.strip().startswith("ville"))
    # ⚠️ La ville SEULE couvre 2 dossiers, dont celui que la cascade REFUSE de
    # trancher : *le tableau dit ce qu'elle saurait faire, pas ce qu'on la
    # laisse faire.*
    assert ville.split()[-2] == "3", ville
    assert "recouvrement :" in sortie
    assert "ne mérite pas son rang" in sortie


# ---------------------------------------------------------------------------
# 3. LES CORRECTIONS — le lot à regarder en premier, paginable À PART
# ---------------------------------------------------------------------------

def test_les_corrections_sont_comptees_par_NIVEAU(decor, capsys):
    assert outil.main(["--echantillon", "0"]) == 0
    sortie = _sortie(capsys)
    assert "LES CAS OÙ UN FAIT CORRIGE LE SCORE" in sortie
    assert "n'est PAS une erreur" in sortie or "CORRIGE le score" in sortie
    assert "TOTAL à relire une à une" in sortie


def test_les_corrections_se_paginent_A_PART(decor, capsys):
    """*« Paginables à part, parce que ce sont eux à regarder en premier. »*"""
    assert outil.main(["--echantillon", "0", "--departages", "1"]) == 0
    sortie = _sortie(capsys)
    assert "DÉPARTAGES 1 à 1 sur 4" in sortie, sortie
    assert "tranché par :" in sortie
    assert "→ = retenu par l'adresse" in sortie


def test_la_pagination_montre_le_fait_BRUT_et_la_forme_COMPAREE(decor, capsys):
    """*On ne relit pas une paire sur la seule forme qu'on a calculée.*"""
    assert outil.main(["--echantillon", "0", "--departages", "5"]) == 0
    sortie = _sortie(capsys)
    assert "au dossier  :" in sortie and "comparé sur :" in sortie
    assert "'Levis, QC G6V 5X9'" in sortie, sortie
    assert "complet=" in sortie and "tri=" in sortie


def test_les_deux_paginations_ne_se_demandent_PAS_ENSEMBLE(decor):
    """⚠️ *`--depuis` désigne un rang dans UN lot* — deux lots sous le même
    numéro afficheraient deux pages différentes."""
    with pytest.raises(SystemExit):
        outil.main(["--corrections", "5", "--departages", "5"])


def test_depuis_decale_le_lot(decor, capsys):
    assert outil.main(["--echantillon", "0", "--departages", "1", "--depuis", "1"]) == 0
    assert "DÉPARTAGES 2 à 2 sur 4" in _sortie(capsys)


# ---------------------------------------------------------------------------
# 4. « LES EXCLUT TOUS » — l'échantillon, et son coût
# ---------------------------------------------------------------------------

def test_lechantillon_dit_lequel_des_deux_et_ce_quil_a_COUTE(decor, capsys):
    assert outil.main([]) == 0
    sortie = _sortie(capsys)
    assert "LE FAIT LES EXCLUT TOUS" in sortie
    assert outil.HORS_DU_LOT in sortie and outil.FAIT_SUSPECT in sortie
    assert "CE QUE ÇA A COÛTÉ" in sortie
    assert "CE QUE COÛTERAIT DE LE SAVOIR SUR TOUS" in sortie
    assert "la relecture humaine des paires" in sortie


def test_lechantillon_est_tire_A_PAS_CONSTANT_pas_en_tete():
    """⚠️ *Prendre la tête promeut l'ordre de la base au rang de critère
    (cas 19).*"""
    population = list(range(100))
    assert outil._echantillon(population, 4) == [0, 25, 50, 75]
    assert outil._echantillon(population, 200) == population
    assert outil._echantillon(population, 0) == []


def test_lechantillon_se_saute(decor, capsys):
    assert outil.main(["--echantillon", "0"]) == 0
    assert "échantillon sauté" in _sortie(capsys)


def test_la_borne_elargie_est_LUE_dans_le_moteur(decor, capsys):
    """⚠️ *Une constante décorative vaut la valeur qu'elle avait à l'import.*"""
    from falkye.sources import req as req_source

    assert outil.main([]) == 0
    attendu = outil.FACTEUR_BORNE_ELARGIE * req_source.LIMITE_CANDIDATS_PAR_NOM
    from outils.nombres import milliers

    assert f"Borne élargie : {milliers(attendu)}" in _sortie(capsys)


# ---------------------------------------------------------------------------
# CE QUI NE BOUGE PAS
# ---------------------------------------------------------------------------

def test_il_NECRIT_RIEN(decor):
    avant = {c.id: (c.neq, c.ville, c.code_postal)
             for c in decor.execute(select(Company)).scalars()}
    assert outil.main([]) == 0
    decor.expire_all()
    apres = {c.id: (c.neq, c.ville, c.code_postal)
             for c in decor.execute(select(Company)).scalars()}
    assert avant == apres


def test_les_echelles_ne_bougent_pas(decor):
    from falkye import resolution

    assert outil.main([]) == 0
    assert resolution.SEUIL_RESOLUTION_CONFIANTE == 92.0
    assert resolution.SEUIL_AMBIGUITE_ECART_MIN == 8.0
