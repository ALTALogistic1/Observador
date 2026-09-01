"""Tests de la correspondance signal -> sphère et mots-clés (falkye/matching.py)."""
from falkye.matching import correspondance_qualitative_titre, spheres_probables


def test_spheres_probables_appel_offres(registry):
    spheres = spheres_probables("appel_offres", registry)
    assert "gestion_projet" in spheres


def test_spheres_probables_type_inconnu_retourne_liste_vide(registry):
    assert spheres_probables("signal_qui_n_existe_pas", registry) == []


def test_correspondance_qualitative_detecte_mot_cle_profil():
    trouves = correspondance_qualitative_titre(
        "Chef de projet — implantation ERP/WMS", mots_cles_profil=["implantation erp"]
    )
    assert any("implantation" in m for m in trouves)


def test_correspondance_qualitative_detecte_base_transformation_sans_mots_cles_profil():
    trouves = correspondance_qualitative_titre("Directeur de la transformation", mots_cles_profil=[])
    assert trouves  # doit matcher la base MOTS_CLES_TRANSFORMATION même sans mot-clé utilisateur


def test_correspondance_qualitative_titre_neutre_ne_matche_rien():
    trouves = correspondance_qualitative_titre("Commis aux ventes", mots_cles_profil=["implantation erp"])
    assert trouves == []


def test_correspondance_qualitative_titre_absent():
    assert correspondance_qualitative_titre(None, mots_cles_profil=["implantation"]) == []
