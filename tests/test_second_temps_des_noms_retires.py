"""Ce que le troisième temps change — **une mesure, elle n'écrit rien.**

⚠️ **Ce que ces tests verrouillent :** que « perdre son NEQ » et « le rejeu ne
le retrouvait déjà plus » ne se confondent jamais — *le premier accuserait la
règle nouvelle d'une perte qui lui préexiste* — et que les deux causes d'un NEQ
introuvable restent distinctes.
"""
from __future__ import annotations

import datetime as _dt

import pytest

from falkye.models.company import Company, StatutResolution
from falkye.models.req_entry import REQEntry
from falkye.models.req_mot import REQMot, REQMotFrequence
from falkye.models.req_nom import REQNom
from falkye.sources.column_mapping import normaliser
from outils import second_temps_des_noms_retires as outil


def test_la_colonne_tient_toutes_ses_etiquettes():
    for t in (outil.ISSUES_DES_POSES + outil.ISSUES_DES_RESTANTS
              + outil.CAUSES_DE_LA_PERTE):
        assert len(t) < outil.LARGEUR, t


def test_les_deux_regles_passent_par_DEUX_APPELS_de_la_production():
    """*Une règle recopiée mesurerait sa propre copie.* **Le drapeau
    `retires_en_dernier` existe pour que la comparaison soit un APPEL.**"""
    import inspect

    from falkye.sources.req import resolve_neq_by_name

    assert "retires_en_dernier" in inspect.signature(resolve_neq_by_name).parameters
    source = inspect.getsource(outil.les_deux_regles)
    assert source.count("resolve_neq_by_name") == 2
    assert "retires_en_dernier=False" in source


@pytest.fixture()
def decor(db_session, monkeypatch):
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")

    def entreprise(neq, elue, autres=()):
        db_session.add(REQEntry(neq=neq, nom=elue, nom_normalise=normaliser(elue),
                                statut="immatriculee"))
        for nom, statut in autres:
            db_session.add(REQNom(neq=neq, nom=nom, nom_normalise=normaliser(nom),
                                  statut=statut, type_nom="NOM", gisement="NOM_ASSUJ"))

    def dossier(nom, neq=None):
        db_session.add(Company(
            neq=neq, nom_detecte=nom, nom_detecte_normalise=normaliser(nom),
            statut_resolution=(StatutResolution.RESOLU if neq
                               else StatutResolution.AMBIGU),
            first_detected_at=_dt.datetime(2026, 1, 1)))

    # ⚠️ CHANGE DE NEQ : le nom retiré de l'un, en vigueur chez l'autre.
    entreprise("1800000001", "Carbotech Innovation Inc.",
               [("Zibeline Robotique inc", "A")])
    entreprise("1800000002", "Zibeline Robotique inc",
               [("Zibeline Robotique inc", "V")])
    dossier("Zibeline Robotique inc", "1800000001")

    # INCHANGÉ : son propre ancien nom, personne d'autre ne le porte.
    entreprise("1800000003", "Les Entreprises Douglas Powertech inc.",
               [("Tannerie Orfevre Canada inc", "A")])
    dossier("Tannerie Orfevre Canada inc", "1800000003")

    # ⚠️ INTROUVABLE, PORTE DISPARUE : le NEQ posé n'est récupérable par aucun nom.
    entreprise("1800000004", "Papeterie Lointaine Sans Rapport inc")
    dossier("Chapellerie Introuvable Ailleurs inc", "1800000004")

    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def test_la_mesure_N_ECRIT_RIEN(decor, capsys):
    avant = {c.id: c.neq for c in decor.query(Company).all()}
    assert outil.main(["--pas", "0"]) == 0
    assert {c.id: c.neq for c in decor.query(Company).all()} == avant
    assert "RIEN N'A ÉTÉ ÉCRIT" in capsys.readouterr().out


def test_un_NEQ_deja_introuvable_n_est_PAS_compte_comme_PERDU(decor, capsys):
    """⚠️ **La distinction qui décide.** *Un dossier dont le rejeu ne retrouvait
    DÉJÀ plus le NEQ avant la règle ne se perd pas à cause d'elle.* **Les
    confondre accuserait la règle nouvelle d'une perte qui lui préexiste.**"""
    assert outil.main(["--pas", "0"]) == 0
    sortie = capsys.readouterr().out
    from tests.conftest import compte_de_la_ligne

    perdu = next(l for l in sortie.splitlines() if l.strip().startswith(outil.PERDU))
    deja = next(l for l in sortie.splitlines()
                if "le rejeu ne retrouvait DÉJÀ plus" in l)
    assert compte_de_la_ligne(perdu) == "0", perdu
    assert compte_de_la_ligne(deja) == "1", deja
    assert "Aucun dossier ne perd son NEQ" in sortie


def test_le_changement_de_NEQ_est_compte_et_rendu(decor, capsys):
    assert outil.main(["--pas", "0", "--paires", "5"]) == 0
    sortie = capsys.readouterr().out
    from tests.conftest import compte_de_la_ligne

    change = next(l for l in sortie.splitlines() if l.strip().startswith(outil.CHANGE))
    assert compte_de_la_ligne(change) == "1", change
    bloc = sortie.split("QUI CHANGERAIENT DE NEQ")[1]
    assert "1800000001" in bloc and "1800000002" in bloc
    assert "l'ancienne règle rendait" in bloc


def test_la_cause_est_la_FAMILLE_et_jamais_la_coupe(decor, capsys):
    """⚠️ **La correction du 23 septembre.** *L'outil nommait « le NEQ est passé
    sous la coupe » la cause d'un dossier qu'il ne résout plus.* **C'était faux :
    `neq_retenu` ne lit que `matches[0]` et `matches[1]`, donc relever le plafond
    du lot ne change aucune décision.**"""
    assert outil.main(["--pas", "0", "--paires", "5"]) == 0
    sortie = capsys.readouterr().out
    # ⚠️ La fausse cause n'est plus une ÉTIQUETTE — elle n'apparaît que dans sa
    # propre rétractation. *Un outil qui se corrige doit pouvoir NOMMER ce qu'il
    # disait; l'interdire l'obligerait à se corriger en silence.*
    assert not any("coupe" in c for c in outil.CAUSES_DE_LA_PERTE)
    assert "C'ÉTAIT FAUX" in sortie
    assert "NE CHANGE AUCUNE DÉCISION" in sortie
    assert "LA VRAIE CAUSE est la FAMILLE" in sortie
    # ⚠️ Et « ne résout plus » ne se confond pas avec « le NEQ a disparu ».
    assert any(l.strip().startswith(outil.ABSENT_DU_LOT)
               for l in sortie.splitlines())


def test_une_reprise_NE_RETIRE_RIEN_et_la_sortie_le_dit(decor, capsys):
    """*`reresolution_neq` POSE un NEQ là où la famille est RETENU; il n'efface
    jamais.* **Un dossier devenu ambigu garde le NEQ qu'il porte.**"""
    assert outil.main(["--pas", "0"]) == 0
    sortie = capsys.readouterr().out
    assert "UNE REPRISE NE RETIRE RIEN" in sortie
    assert "RIEN NE CHANGE TOUT SEUL" in sortie


def test_la_FAUSSE_GARANTIE_est_retractee_LA_OU_elle_etait(decor, capsys):
    """⚠️ **Un outil qui s'est trompé doit le dire à l'endroit où il se
    trompait.** *La garantie « perdre son NEQ est impossible » était imprimée en
    tête; la rétractation l'est aussi.*"""
    assert outil.main(["--pas", "0"]) == 0
    sortie = capsys.readouterr().out
    avant = sortie.index("LES DOSSIERS DÉJÀ POSÉS")
    assert sortie.index("UNE GARANTIE QUI ÉTAIT FAUSSE") < avant
    assert sortie.index("valait pour les FORMES, jamais pour le LOT") < avant
    assert "NE PEUT RIEN FAIRE PERDRE" not in sortie


def test_la_garde_des_pretendants_est_dite_DESCENDUE_dans_la_resolution(decor, capsys):
    """⚠️ **Le point le plus grave du 23 septembre, et il est corrigé.** *La
    garde n'a vécu que dans `outils/` du 17 au 23; la sortie dit maintenant
    qu'elle est descendue, ET que la FORME du refus a changé en descendant.*

    ⛔ *Ce test affirmait l'inverse jusqu'au 2026-09-23* — il est retourné, pas
    supprimé : la trace de ce que la sortie disait avant vaut autant que ce
    qu'elle dit maintenant."""
    assert outil.main(["--pas", "0"]) == 0
    sortie = capsys.readouterr().out
    assert "CETTE GARDE EST DESCENDUE DANS LA RÉSOLUTION" in sortie
    assert "LA FORME DU REFUS A CHANGÉ EN DESCENDANT" in sortie
    assert "CE QUI N'EST PAS DESCENDU" in sortie
    assert "D27" in sortie and "D28" in sortie


def test_la_garde_des_pretendants_vit_MAINTENANT_dans_falkye():
    """*Vérifié sur le code, pas sur la sortie* — contre-épreuve du test qui
    affirmait son absence jusqu'au 2026-09-23."""
    import pathlib

    resolution = pathlib.Path("falkye/resolution.py").read_text(encoding="utf-8")
    assert "PRETENDANTS_MAX_POUR_TRANCHER = 2" in resolution
    # ⚠️ EMPRUNTÉE, jamais recopiée — le geste est un geste d'ÉCRITURE.
    pose = pathlib.Path("outils/pose_du_neq.py").read_text(encoding="utf-8")
    assert "from falkye.resolution import PRETENDANTS_MAX_POUR_TRANCHER" in pose
    assert "PRETENDANTS_MAX_POUR_TRANCHER = 2" not in pose


# --------------------------------------------------------------------------
# LA TROISIÈME FORME — rejouer le pipeline entier depuis le préfixe
# --------------------------------------------------------------------------


def test_la_troisieme_forme_passe_par_UN_APPEL_de_la_production():
    """*Elle ne recopie pas le scoreur* : `elargir=False` est un paramètre de la
    production, et il rend la troisième forme EXACTEMENT — le troisième temps ne
    tire que là où les deux premiers n'ont rien retenu, et `elargir` ne coupe
    pas le troisième."""
    import inspect

    from falkye.sources.req import resolve_neq_by_name

    assert "elargir" in inspect.signature(resolve_neq_by_name).parameters
    source = inspect.getsource(outil.la_troisieme_forme)
    assert source.count("resolve_neq_by_name") == 1
    assert "elargir=False" in source


def test_cause_dune_perte_EMPRUNTE_la_troisieme_forme():
    """⚠️ *La cause d'une perte et le remède de la troisième forme sont la même
    question.* **Deux appels séparés divergeraient le jour où l'un des deux
    changerait de paramètre.**"""
    import inspect

    assert "la_troisieme_forme" in inspect.getsource(outil.cause_dune_perte)
    assert "resolve_neq_by_name" not in inspect.getsource(outil.cause_dune_perte)


def test_la_section_5_dit_OU_les_deux_formes_different(decor, capsys):
    """⚠️ **Mesurée là où elle s'applique, et nulle part ailleurs.** *Compter
    comme « inchangés » les dossiers que le troisième temps ne touche pas
    gonflerait le dénominateur d'une population que la question ne touche
    pas.*"""
    assert outil.main(["--pas", "0"]) == 0
    sortie = capsys.readouterr().out
    assert "5. CE QUE LA TROISIÈME FORME COÛTERAIT" in sortie
    assert "CE N'EST PAS UNE APPROXIMATION" in sortie
    assert "dossiers où le TROISIÈME TEMPS tire" in sortie
    # ⚠️ Ni « perd » ni « récupère » ne prétendent à la JUSTESSE.
    assert "RIEN ICI NE DIT LEQUEL DES DEUX EST JUSTE" in sortie
    assert "ET « RÉCUPÈRE » NON PLUS" in sortie


def test_la_section_5_precede_les_paires(decor, capsys):
    """*Le compte avant les exemples* — une paire lue avant son dénombrement se
    fait prendre pour la règle."""
    assert outil.main(["--pas", "0", "--paires", "2"]) == 0
    sortie = capsys.readouterr().out
    assert sortie.index("5. CE QUE LA TROISIÈME FORME COÛTERAIT") < sortie.index(
        "LES DOSSIERS QUI CHANGERAIENT DE NEQ")


@pytest.fixture()
def une_perte(db_session, monkeypatch):
    """⛔ **Une PERTE construite exprès** — la forme exacte des 9 du 23 septembre.

    *Le NEQ posé a matché sur un nom RETIRÉ, seul dans le lot du PRÉFIXE.*
    **L'ancienne règle le retenait à 100.** La nouvelle l'écarte du premier
    temps, n'a plus rien, ouvre le SECOND — qui ramène par le mot rare deux
    concurrents que le préfixe ne voyait pas — puis rejoue les formes sur ce lot
    ÉLARGI : le nom retiré revient à 100, mais un concurrent est à moins de 8
    points. **Ambigu. Le NEQ est perdu par le LOT, pas par les FORMES.**
    """
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")
    detecte = "Zeta Chromoplastie Industrielle"

    def entreprise(neq, elue, autres=()):
        db_session.add(REQEntry(neq=neq, nom=elue, nom_normalise=normaliser(elue),
                                statut="immatriculee"))
        for nom, statut in autres:
            db_session.add(REQNom(neq=neq, nom=nom, nom_normalise=normaliser(nom),
                                  statut=statut, type_nom="NOM", gisement="NOM_ASSUJ"))

    # Le détenteur : sa dénomination élue ne ressemble à rien, son nom RETIRÉ
    # est exactement le nom détecté — et il est le seul du lot du PRÉFIXE.
    entreprise("1900000001", "Groupe 9412-0001 Québec inc.",
               [("Groupe 9412-0001 Québec inc.", "V"), (detecte, "A")])
    # Deux concurrents que SEUL le mot rare ramène — aucun ne commence par
    # « Zeta », donc le lot du préfixe ne les a jamais vus.
    entreprise("1900000002", "Chromoplastie Industrielle Zeta",
               [("Chromoplastie Industrielle Zeta", "V")])
    entreprise("1900000003", "Chromoplastie Industrielle Zeta enr.",
               [("Chromoplastie Industrielle Zeta enr.", "V")])
    # ⚠️ L'INDEX DES MOTS, sans lequel le second temps ne ramène RIEN — le
    # décor du haut n'en a pas, et c'est pour ça qu'il n'y perdait aucun NEQ.
    for neq in ("1900000002", "1900000003"):
        db_session.add(REQMot(mot="chromoplastie", neq=neq))
    db_session.add(REQMotFrequence(mot="chromoplastie", neqs=2))
    db_session.add(REQMotFrequence(mot="industrielle", neqs=3))
    db_session.add(REQMotFrequence(mot="zeta", neqs=5))
    db_session.add(Company(
        neq="1900000001", nom_detecte=detecte,
        nom_detecte_normalise=normaliser(detecte),
        statut_resolution=StatutResolution.RESOLU,
        first_detected_at=_dt.datetime(2026, 1, 1)))
    db_session.flush()
    return db_session


def test_la_perte_est_bien_UNE_PERTE_par_le_LOT(une_perte):
    """*Le décor ne vaut que s'il produit vraiment la forme qu'il annonce.*"""
    from falkye.models.company import Company as C

    company = une_perte.query(C).one()
    avant, apres, _m, journal = outil.les_deux_regles(une_perte, company)
    assert avant == company.neq          # l'ancienne règle le retenait
    assert apres is None                 # la nouvelle ne retient plus rien
    assert journal.get("troisieme_temps")  # le troisième temps a bien tiré
    assert outil.cause_dune_perte(une_perte, company) == outil.PAR_LE_SECOND_TEMPS
    # ⚠️ Et la TROISIÈME FORME le récupérerait — c'est tout le sujet.
    assert outil.la_troisieme_forme(une_perte, company) == company.neq


def test_les_pertes_sont_rendues_DOSSIER_PAR_DOSSIER(une_perte, capsys):
    """⚠️ **Toutes, jamais un échantillon** — *neuf dossiers se lisent en
    entier, et `--paires` n'en montrerait qu'une poignée.*"""
    assert outil.main(["--pas", "0"]) == 0
    sortie = capsys.readouterr().out
    assert "1bis. LES 1 PERTES, DOSSIER PAR DOSSIER" in sortie
    assert "NEQ posé          : 1900000001" in sortie
    assert outil.PAR_LE_SECOND_TEMPS in sortie
    assert "la TROISIÈME FORME le récupérerait" in sortie
    assert "écart sommet/second" in sortie
    # La troisième forme récupère exactement cette perte-là.
    assert "✅ RÉCUPÈRE un NEQ que le lot élargi lui prenait" in sortie
    assert "retrouverait 1900000001" in sortie


def test_le_denominateur_de_la_section_5_est_la_POPULATION(decor, capsys):
    """⛔ **Le défaut du 2026-09-24, relevé par Alexandre en lisant la sortie.**

    *Une boucle de la section 4 s'appelait `dossiers` et écrasait la POPULATION
    du même nom.* La section 5 s'en servait comme dénominateur et imprimait
    **« 6 468   24 876,9 % »** — 6 468 sur les **26** dossiers du dernier NEQ
    de cette boucle.
    """
    assert outil.main(["--pas", "0"]) == 0
    sortie = capsys.readouterr().out
    from tests.conftest import compte_de_la_ligne

    ligne = next(ligne for ligne in sortie.splitlines()
                 if "dossiers où le TROISIÈME TEMPS tire" in ligne)
    part = ligne.rsplit("%", 1)[0].rsplit(None, 1)[-1].replace(",", ".")
    assert 0.0 <= float(part) <= 100.0, ligne
    # Le compte lui-même ne peut pas dépasser la population rejouée.
    tire = int(compte_de_la_ligne(ligne).replace(" ", "").replace(" ", ""))
    rejeu = next(ligne for ligne in sortie.splitlines() if "rejeu des DEUX règles" in ligne)
    assert tire <= int(rejeu.split("sur")[1].split()[0].replace(" ", ""))


def test_la_section_4_ne_peut_plus_ECRASER_la_population():
    """*Vérifié sur le code* — le nom de la boucle, et le dénominateur pris à
    une variable retenue d'avance plutôt qu'à une liste relue."""
    import inspect

    source = inspect.getsource(outil.main)
    assert "dossiers_du_neq = [" in source
    assert "population = len(dossiers)" in source
    assert "len(a_tire), population)" in source
