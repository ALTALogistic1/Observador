"""Les archives du REQ conservées — la date se lit dans le nom, jamais dans mtime."""
from datetime import date
from pathlib import Path

from outils.archives_req import (
    SEUIL_VIEILLISSEMENT_JOURS,
    age_en_jours,
    archives_du_dossier,
    avertissement,
    date_de_larchive,
    la_plus_recente,
    ligne_de_provenance,
    resoudre,
)

LE_16 = date(2026, 9, 16)


def test_la_date_se_lit_dans_le_nom():
    assert date_de_larchive("JeuDonnees-2026-09-02.zip") == date(2026, 9, 2)
    assert date_de_larchive(Path("/opt/falkye/import/JeuDonnees-2026-09-02.zip")) \
        == date(2026, 9, 2)


def test_le_nom_herite_na_pas_de_date():
    assert date_de_larchive("JeuDonnees.zip") is None


def test_un_nom_qui_RESSEMBLE_a_une_date_nen_est_pas_une():
    """`2026-13-45` n'existe pas. Rendre None plutôt que lever : l'archive reste
    utilisable, elle est simplement non datée."""
    assert date_de_larchive("JeuDonnees-2026-13-45.zip") is None


def test_une_date_au_milieu_du_nom_nest_pas_retenue():
    """Elle se confondrait avec un numéro d'édition."""
    assert date_de_larchive("JeuDonnees-2026-09-02-final.zip") is None


def test_lage_dune_archive_sans_date_nest_pas_ZERO():
    """L'absence de mesure n'est pas une mesure nulle."""
    assert age_en_jours(None) is None
    assert age_en_jours(date(2026, 9, 2), LE_16) == 14


def test_les_datees_passent_devant_les_non_datees(tmp_path):
    """Une archive non datée ne doit jamais passer devant une datée : son âge est
    inconnu, pas nul."""
    for nom in ("JeuDonnees.zip", "JeuDonnees-2026-08-19.zip", "JeuDonnees-2026-09-02.zip"):
        (tmp_path / nom).write_bytes(b"")
    ordre = [c.name for _d, c in archives_du_dossier(tmp_path)]
    assert ordre == ["JeuDonnees-2026-09-02.zip", "JeuDonnees-2026-08-19.zip", "JeuDonnees.zip"]
    assert la_plus_recente(tmp_path).name == "JeuDonnees-2026-09-02.zip"


def test_un_dossier_vide_ne_rend_rien():
    assert archives_du_dossier("/n/existe/pas") == []
    assert la_plus_recente("/n/existe/pas") is None


def test_resoudre_accepte_un_fichier_ou_un_repertoire(tmp_path):
    """Un seul point d'entrée : sinon deux mesures prises le même jour
    porteraient sur deux fichiers différents sans que personne ne le voie."""
    archive = tmp_path / "JeuDonnees-2026-09-02.zip"
    archive.write_bytes(b"")
    assert resoudre(archive) == archive
    assert resoudre(tmp_path) == archive
    assert resoudre(tmp_path / "absente.zip") is None


def test_une_archive_fraiche_ne_declenche_aucun_avertissement():
    assert avertissement("JeuDonnees-2026-09-02.zip", date(2026, 9, 10)) is None


def test_une_archive_vieillie_dit_son_age_et_les_editions_manquees():
    message = avertissement("JeuDonnees-2026-08-01.zip", LE_16)
    assert "46 jour(s)" in message
    assert "3 édition(s)" in message
    assert "n'est PAS l'état courant" in message


def test_une_archive_non_datee_dit_INCONNU_et_non_vieille():
    """Fondre les deux ferait lire « vieille » là où il faut lire « on ne sait
    pas »."""
    message = avertissement("JeuDonnees.zip", LE_16)
    assert "INCONNU" in message
    assert "vieill" not in message.lower()


def test_le_seuil_laisse_passer_une_veille_de_publication():
    """Un seuil à 14 jours crierait à chaque veille, et une garde qui crie à tort
    finit par être ignorée."""
    assert SEUIL_VIEILLISSEMENT_JOURS > 14
    assert avertissement("JeuDonnees-2026-09-02.zip", date(2026, 9, 16)) is None
    assert avertissement("JeuDonnees-2026-09-02.zip", date(2026, 9, 23)) is not None


def test_la_provenance_tient_en_une_ligne_et_porte_la_date():
    ligne = ligne_de_provenance("JeuDonnees-2026-09-02.zip", LE_16)
    assert "2026-09-02" in ligne and "14 jour(s)" in ligne
    assert "INCONNUE" in ligne_de_provenance("JeuDonnees.zip", LE_16)
