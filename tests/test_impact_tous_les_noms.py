"""L'impact de « garder tous les noms » — fonctions pures."""
from outils.impact_tous_les_noms import (
    LIGNES_DE_REFERENCE,
    MINUTES_DE_REFERENCE,
    OCTETS_PAR_LIGNE,
    estimer_duree,
)


def test_la_duree_est_une_FOURCHETTE_jamais_un_nombre():
    """L'écriture en masse est plus rapide que l'upsert de référence, et de
    combien n'a pas été mesuré. Un nombre serait une promesse."""
    basse, haute = estimer_duree(LIGNES_DE_REFERENCE)
    assert basse < haute
    assert haute == MINUTES_DE_REFERENCE


def test_la_borne_haute_suppose_le_meme_prix_par_ligne():
    _basse, haute = estimer_duree(LIGNES_DE_REFERENCE * 2)
    assert haute == MINUTES_DE_REFERENCE * 2


def test_zero_ligne_ne_coute_rien():
    assert estimer_duree(0) == (0.0, 0.0)


def test_lestimation_doctets_est_un_ordre_de_grandeur_declare():
    """Un chiffre recopié est une promesse que personne ne tient — celui-ci est
    annoncé comme un ordre de grandeur dans la sortie."""
    assert 50 < OCTETS_PAR_LIGNE < 500


# ---------------------------------------------------------------------------
# LES DÉCORS — une archive minimale, et une base branchée sur le test
# ---------------------------------------------------------------------------


def _archive(tmp_path, lignes_nom):
    """Un zip portant les trois CSV réels, dont un `Nom.csv` aux lignes données.

    *Daté dans son nom* — `archives_req` refuse de mesurer sans provenance, et
    un décor non daté ferait passer l'avertissement plutôt que la mesure.
    """
    import csv
    import io
    import zipfile

    chemin = tmp_path / "JeuDonnees-2026-09-02.zip"
    with zipfile.ZipFile(chemin, "w") as zf:
        tampon = io.StringIO()
        champs = ["NEQ", "NOM_ASSUJ", "STAT_NOM", "TYP_NOM_ASSUJ"]
        redacteur = csv.DictWriter(tampon, fieldnames=champs)
        redacteur.writeheader()
        for ligne in lignes_nom:
            redacteur.writerow(ligne)
        zf.writestr("Nom.csv", tampon.getvalue())
        zf.writestr("Entreprise.csv", "NEQ,COD_STAT_IMMAT\n")
        zf.writestr("Etablissements.csv", "NEQ,NO_SUF_ETAB\n")
    return chemin


def _brancher(db_session, monkeypatch, companies):
    """La base du test, et la cible déclarée — sans quoi l'outil REFUSE."""
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")
    if companies:
        db_session.add_all(companies)
        db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


# ---------------------------------------------------------------------------
# LE GAIN NEUF — ce que le pont N'ATTEINT PAS  (2026-09-17)
# ---------------------------------------------------------------------------
#
# ⚠️ **Le fait qui écrit ces tests.** `req_noms` est chargé depuis le MÊME
# fichier, avec le MÊME filtre `STAT_NOM = 'V'`, la MÊME colonne et la MÊME
# normalisation que cet outil. *Donc tout gain mesuré sur les noms en vigueur
# est DÉJÀ EN BASE, et ne représente aucune récupération disponible.*


def test_le_pont_ne_filtre_PLUS_par_statut_et_la_conclusion_du_0_est_DATEE():
    """⚠️ **Une conclusion vraie d'un état du code, et le code a changé.**

    Le 2026-09-17 au matin, l'arithmétique fermait la piste des noms en vigueur :
    `1 521 816 − 15 937 = 1 505 879`, exactement `count(*)` de `req_noms`. **Elle
    tenait parce que le pont filtrait `STAT_NOM = 'V'`, comme l'outil.**

    **Le même jour, Alexandre a décidé que tout entre.** *Donc l'identité ne vaut
    QUE pour le miroir chargé avant ce changement* — celui du 16 septembre, avec
    l'archive du 2. **Après le prochain import, `req_noms` portera bien plus que
    le compte en vigueur de l'outil, et comparer les deux n'aura plus de sens.**

    Ce test verrouille les deux moitiés : *le pont ne filtre plus*, et *la
    conclusion du 0 est datée*.
    """
    import inspect
    import pathlib

    from falkye.sources import req

    pont = inspect.getsource(req._charger_tous_les_noms)
    outil = pathlib.Path("outils/impact_tous_les_noms.py").read_text(encoding="utf-8")
    for cle in ("NEQ", "NOM_ASSUJ"):
        assert f'"{cle}"' in pont or cle in str(req.GISEMENTS_DE_NOMS), (
            f"le pont ne lit plus {cle}"
        )
        assert f'"{cle}"' in outil, f"l'outil ne lit plus {cle}"
    assert "statuts_retenus" in pont, (
        "le pont ne porte plus de filtre par statut, même optionnel — la décision "
        "cesserait d'être révisable sans réimport"
    )
    assert "STAT_NOM" in str(req.GISEMENTS_DE_NOMS), (
        "les gisements ne déclarent plus la colonne de statut"
    )
    assert "normaliser" in pont and "normaliser" in outil


def test_le_pont_garde_TOUS_les_statuts_par_defaut():
    """*La décision du 2026-09-17, vérifiée sur la signature et non sur une
    intention* — `statuts_retenus=None` veut dire « tout garder »."""
    import inspect

    from falkye.sources import req

    defaut = inspect.signature(
        req._charger_tous_les_noms
    ).parameters["statuts_retenus"].default
    assert defaut is None, "le pont filtre encore par défaut"


def test_larithmetique_de_lecart_de_16000():
    """*L'écart entre les 1 521 816 annoncés et les 1 505 879 en base n'était pas
    des noms manquants : c'étaient les mêmes noms comptés deux fois.*"""
    annonce, doublons, en_base = 1_521_816, 15_937, 1_505_879
    assert annonce - doublons == en_base


def test_tous_les_statuts_separe_le_DEJA_ATTEIGNABLE_du_NEUF(
    db_session, tmp_path, monkeypatch, capsys
):
    """⚠️ **Le chiffre qui décide.** Un dossier atteignable par un nom EN VIGUEUR
    est déjà dans le pont; seul celui qui ne l'est QUE par un nom plus en vigueur
    est un gain neuf."""
    from falkye.models.company import Company
    from falkye.sources.column_mapping import normaliser
    from outils import impact_tous_les_noms

    archive = _archive(tmp_path, [
        # en vigueur — donc DÉJÀ dans le pont
        {"NEQ": "1000000001", "NOM_ASSUJ": "Deja Dans Le Pont", "STAT_NOM": "V",
         "TYP_NOM_ASSUJ": "M"},
        # plus en vigueur — le gain NEUF
        {"NEQ": "1000000002", "NOM_ASSUJ": "Ancien Nom Abandonne", "STAT_NOM": "A",
         "TYP_NOM_ASSUJ": "M"},
    ])
    _brancher(db_session, monkeypatch, [
        Company(neq=None, nom_detecte="Deja Dans Le Pont",
                nom_detecte_normalise=normaliser("Deja Dans Le Pont")),
        Company(neq=None, nom_detecte="Ancien Nom Abandonne",
                nom_detecte_normalise=normaliser("Ancien Nom Abandonne")),
    ])

    assert impact_tous_les_noms.main(
        ["--chemin", str(archive), "--tous-les-statuts"]
    ) == 0
    sortie = capsys.readouterr().out
    assert "LE CHIFFRE QUI DÉCIDE" in sortie
    assert "GAIN NEUF DU TRAITEMENT DE L'ARCHIVE : 1 dossier(s)" in sortie, sortie
    ligne = next(l for l in sortie.splitlines() if "déjà atteignable" in l)
    assert ligne.split()[0] == "1", ligne


def test_sans_le_drapeau_les_anciens_noms_ne_sont_PAS_comptes(
    db_session, tmp_path, monkeypatch, capsys
):
    """*Le chemin par défaut ne change pas* — l'outil rendait déjà un chiffre, et
    il doit rendre le même."""
    from falkye.models.company import Company
    from falkye.sources.column_mapping import normaliser
    from outils import impact_tous_les_noms

    archive = _archive(tmp_path, [
        {"NEQ": "1000000002", "NOM_ASSUJ": "Ancien Nom Abandonne", "STAT_NOM": "A",
         "TYP_NOM_ASSUJ": "M"},
    ])
    _brancher(db_session, monkeypatch, [
        Company(neq=None, nom_detecte="Ancien Nom Abandonne",
                nom_detecte_normalise=normaliser("Ancien Nom Abandonne")),
    ])
    assert impact_tous_les_noms.main(["--chemin", str(archive)]) == 0
    sortie = capsys.readouterr().out
    assert "LE CHIFFRE QUI DÉCIDE" not in sortie
    assert "0 entreprise(s) se résoudraient franchement." in sortie, sortie


def test_le_deja_en_base_est_dit_AVANT_le_gain(
    db_session, tmp_path, monkeypatch, capsys
):
    """⚠️ *Lire « 6 009 résolutions franches » avant de lire « déjà en base »
    fait décider sur un gain qui n'existe pas.*"""
    from outils import impact_tous_les_noms

    archive = _archive(tmp_path, [
        {"NEQ": "1000000001", "NOM_ASSUJ": "Quelconque", "STAT_NOM": "V",
         "TYP_NOM_ASSUJ": "M"},
    ])
    _brancher(db_session, monkeypatch, [])
    assert impact_tous_les_noms.main(["--chemin", str(archive)]) == 0
    sortie = capsys.readouterr().out
    assert sortie.index("CE QUI EST DÉJÀ EN BASE") < sortie.index("2. LE GAIN")
    assert "DÉJÀ EN BASE, et ne" in sortie
