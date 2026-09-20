"""Des dossiers entiers à lire — pas des comptes.

⚠️ **Ce que ces tests verrouillent est une RETENUE d'instrument.** *Un outil de
lecture qui imprime un pourcentage transforme vingt dossiers en population; un
outil qui filtre le sac de champs décide d'avance où regarder.* **Les deux
défauts sont silencieux, et c'est pour ça qu'ils sont testés plutôt que relus.**
"""
from __future__ import annotations

import datetime as _dt

import pytest

from falkye.models.company import Company
from falkye.models.req_entry import REQEntry
from falkye.models.req_nom import REQNom
from falkye.models.signal import Signal
from falkye.sources.column_mapping import normaliser
from outils import lecture_des_dossiers as outil


# ---------------------------------------------------------------------------
# LE BALAYAGE — c'est lui qui porte le cas 19
# ---------------------------------------------------------------------------

def test_le_balayage_parcourt_TOUTE_la_longueur_jamais_la_tete():
    """⚠️ **C'est le cas 19.** *`lot[:8]` rendrait les huit plus anciens
    identifiants, et une tête triée n'est pas un échantillon.*"""
    lot = list(range(1000))
    choisis = outil.a_pas_constant(lot, 8)
    assert choisis != lot[:8]
    assert choisis[0] < 100 and choisis[-1] > 800, choisis
    assert len(set(choisis)) == 8


def test_le_decalage_rend_une_SECONDE_lecture_et_pas_la_meme():
    lot = list(range(1000))
    assert not set(outil.a_pas_constant(lot, 6)) & set(outil.a_pas_constant(lot, 6, 7))


@pytest.mark.parametrize("taille, combien, attendu", [
    (3, 8, 3),    # *Un lot plus court que la demande se rend en entier.*
    (0, 8, 0),
    (100, 0, 0),
])
def test_le_balayage_ne_deborde_ni_ne_repete(taille, combien, attendu):
    choisis = outil.a_pas_constant(list(range(taille)), combien)
    assert len(choisis) == attendu
    assert len(set(choisis)) == attendu


def test_une_valeur_du_sac_est_rendue_SANS_etre_interpretee():
    """*Une liste de classifications, un nombre, une chaîne* — **tout passe, rien
    n'est traduit.** Tronquer est le seul geste permis."""
    assert outil._valeur_lisible([{"code": "72101"}]) == "[{'code': '72101'}]"
    assert outil._valeur_lisible(42) == "42"
    long = outil._valeur_lisible("x" * 200)
    assert len(long) == 96 and long.endswith("…")


# ---------------------------------------------------------------------------
# LA LECTURE, DE BOUT EN BOUT
# ---------------------------------------------------------------------------

@pytest.fixture()
def decor(db_session, monkeypatch):
    """Des dossiers de trois familles, dont un dont la forme qui a matché
    N'EST PAS la dénomination élue — le cas 33."""
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")
    recent = _dt.datetime.now() - _dt.timedelta(days=3)

    dossiers = [
        # Un ambigu : deux entrées du registre portent le même nom.
        ("Beton Bolduc", "seao",
         {"secteur_nature_contrat": [{"code": "72101"}], "valeur_contrat": 125000}),
        # Un nom d'un seul mot.
        ("Kone", "eimt", {"profession": "Mécanicien", "adresse": "Laval, QC H7N 1A1"}),
        # Un nom qui ne ressemble à rien du registre.
        ("Zzyzx Innovations Numeriques", "seao", {}),
    ]
    for nom, source, champs in dossiers:
        company = Company(neq=None, nom_detecte=nom, nom_detecte_normalise=normaliser(nom))
        db_session.add(company)
        db_session.flush()
        db_session.add(Signal(
            company_id=company.id, source_id=source,
            signal_type_id="recrutement_massif", detected_at=recent, champs=champs,
        ))
    miroir = [
        ("1111111111", "Béton Bolduc inc.", "Québec", "G1V 2M2", "5511"),
        ("1111111112", "Béton Bolduc et Frères", "Québec", "G1V 2M3", "6622"),
        # ⚠️ Sa dénomination ÉLUE ne ressemble pas au nom détecté; c'est un
        # AUTRE de ses noms qui remportera le score. Le cas 33.
        ("2222222222", "9312-4455 Québec inc.", "Laval", "H7N 1A1", "7733"),
    ]
    for neq, nom, ville, cp, secteur in miroir:
        db_session.add(REQEntry(neq=neq, nom=nom, nom_normalise=normaliser(nom),
                                statut="immatriculee", ville=ville,
                                code_postal=cp, secteur_code=secteur))
    for neq, nom in (("1111111111", "Béton Bolduc inc."),
                     ("1111111112", "Béton Bolduc et Frères"),
                     ("2222222222", "9312-4455 Québec inc."),
                     ("2222222222", "KONE")):
        db_session.add(REQNom(neq=neq, nom=nom, nom_normalise=normaliser(nom),
                              statut="V", type_nom="DENOMINATION", gisement="NOM_ASSUJ"))
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def _sortie(capsys):
    return capsys.readouterr().out


def _dossiers(sortie: str) -> str:
    """⚠️ **Les sections de DOSSIERS, jamais l'en-tête.** *L'en-tête cite les
    pourcentages du 19 septembre pour qu'on ne les refasse pas — une garde
    écrite sur toute la sortie tomberait dessus.* **La bonne portée est plus
    étroite que « tout », et c'est la leçon de N180 appliquée d'avance.**"""
    marque = "FAMILLE «"
    assert marque in sortie, "aucune section de dossier rendue"
    return sortie[sortie.index(marque):]


def test_ce_que_la_sortie_n_est_pas_vient_avant_les_dossiers(decor, capsys):
    assert outil.main(["--pas", "0", "--par-famille", "3"]) == 0
    sortie = _sortie(capsys)
    assert sortie.index("CE N'EST PAS UNE MESURE") < sortie.index("FAMILLE «")
    assert sortie.index("JAMAIS PRIS EN TÊTE DE TABLE") < sortie.index("FAMILLE «")


def test_AUCUN_pourcentage_n_est_imprime_dans_les_dossiers(decor, capsys):
    """⚠️ **La garde principale du fichier.** *Un pourcentage tiré de vingt
    dossiers se relit comme une population dans trois semaines.*"""
    assert outil.main(["--pas", "0", "--par-famille", "3"]) == 0
    assert "%" not in _dossiers(_sortie(capsys))


def test_aucune_categorie_de_JUGEMENT_dans_les_dossiers(decor, capsys):
    assert outil.main(["--pas", "0", "--par-famille", "3"]) == 0
    bloc = _dossiers(_sortie(capsys)).lower()
    for juge in ("probablement récupérable", "probablement pas", "récupérable",
                 "irrécupérable", "sans espoir"):
        assert juge not in bloc, juge


def test_le_sac_de_champs_est_rendu_ENTIER_jamais_filtre(decor, capsys):
    """⚠️ *Choisir les champs à montrer, c'est déjà avoir décidé où regarder* —
    et la piste de l'activité est sortie d'un champ que personne n'avait
    demandé."""
    assert outil.main(["--pas", "0", "--par-famille", "3"]) == 0
    bloc = _dossiers(_sortie(capsys))
    # Les deux clés du même signal, dont une que nulle mesure n'a jamais lue.
    assert "secteur_nature_contrat" in bloc
    assert "valeur_contrat" in bloc, "un champ a été filtré"
    assert "entier, jamais filtré" in bloc


def test_la_forme_qui_a_MATCHE_est_rendue_et_marquee_quand_elle_differe(decor, capsys):
    """⚠️ **Cas 33** : la dénomination élue n'est presque jamais celle qui a
    remporté le score. *`Kone` matche `9312-4455 Québec inc.` par son AUTRE
    nom.*"""
    assert outil.main(["--pas", "0", "--par-famille", "3"]) == 0
    bloc = _dossiers(_sortie(capsys))
    assert "forme qui a MATCHÉ" in bloc
    assert "AUTRE que l'élue" in bloc, bloc[:2000]
    assert "gisement" in bloc and "statut" in bloc


def test_les_candidats_portent_leur_lieu_et_leur_secteur(decor, capsys):
    assert outil.main(["--pas", "0", "--par-famille", "3"]) == 0
    bloc = _dossiers(_sortie(capsys))
    assert "G1V 2M2" in bloc and "secteur 5511" in bloc


def test_les_quatre_lectures_deja_faites_sont_citees_comme_NON_mesurees(decor, capsys):
    """*Ce sont des lectures, pas des prémisses.*"""
    assert outil.main(["--pas", "0", "--par-famille", "3"]) == 0
    sortie = _sortie(capsys)
    assert "AUCUNE n'est mesurée" in sortie
    assert "les contredire est un résultat" in sortie
    for lecture in ("plus récente que l'archive", "un seul mot",
                    "ne serait pas dans le lot", "974"):
        assert lecture in sortie, lecture


def test_une_lentille_dit_qu_elle_sert_a_VERIFIER_et_pas_a_chercher(decor, capsys):
    assert outil.main(["--pas", "0", "--par-famille", "3",
                       "--lentille", "un-seul-mot"]) == 0
    sortie = _sortie(capsys)
    assert "LENTILLE ACTIVE" in sortie
    assert "VÉRIFIER UN MOTIF DÉJÀ VU, jamais à en chercher un" in sortie
    # `Kone` est le seul nom d'un seul mot du décor.
    assert "Kone" in sortie and "Zzyzx" not in _dossiers(sortie)


def test_chaque_lentille_est_APPLICABLE_et_aucune_ne_leve(decor, capsys):
    """*Une lentille qui lève au premier dossier n'est pas une lentille.*"""
    for nom in outil.LENTILLES:
        assert outil.main(["--pas", "0", "--par-famille", "1", "--lentille", nom]) == 0
        capsys.readouterr()


def test_un_motif_vu_trois_fois_se_dit_vu_trois_fois(decor, capsys):
    assert outil.main(["--pas", "0", "--par-famille", "3"]) == 0
    assert "jamais « fréquent »" in _sortie(capsys)


def test_aucune_ecriture(decor, capsys):
    from falkye.resolution import SEUIL_AMBIGUITE_ECART_MIN, SEUIL_RESOLUTION_CONFIANTE

    avant = {c.id: c.neq for c in decor.query(Company).all()}
    assert outil.main(["--pas", "0", "--par-famille", "3"]) == 0
    sortie = _sortie(capsys)
    assert (f"seuil {SEUIL_RESOLUTION_CONFIANTE:.0f}, "
            f"écart {SEUIL_AMBIGUITE_ECART_MIN:.0f}.") in sortie
    assert "RIEN N'A ÉTÉ ÉCRIT" in sortie
    assert {c.id: c.neq for c in decor.query(Company).all()} == avant
