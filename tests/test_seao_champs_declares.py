"""Le SEAO livre ce que le registre déclare — mesuré sur un vrai fichier.

Le 2026-09-13, sur `hebdo_20260831_20260906.json` (4 750 releases, 4 127
attributions) : **classification présente sur 93,6 %**, schéma UNSPSC, 1 242 codes
distincts en une seule semaine; **`buyer.id` à 100 %**; **ville du fournisseur à
87,7 %**; et **`tender.description` à 0,0 %** — le champ que le connecteur captait
sous le nom `description_tender` ne contenait rien, jamais.

`registry/sources.yaml:seao` déclarait déjà `adresse_entreprise_adjudicataire` et
`secteur_nature_contrat`. **Ce n'était pas une exigence neuve, c'était une exigence
non tenue.**
"""
from __future__ import annotations

from datetime import datetime, timezone

from falkye.sources.seao import (
    SEAOConnector,
    _classifications,
    _descriptions_besoins,
    _partie_du_fournisseur,
)

#: La forme RÉELLE, réduite — clés vérifiées sur le fichier du 2026-09-13.
RELEASE = {
    "ocid": "ocds-abc-1", "id": "r-1", "date": "2026-09-02T12:00:00Z",
    "buyer": {"id": "QC-OBNL-1", "name": "Ville de Laval"},
    "parties": [
        {"id": "QC-OBNL-1", "name": "Ville de Laval", "roles": ["buyer"]},
        {
            "id": "QC-NEQ-2", "name": "Constructions Untel", "roles": ["supplier"],
            "address": {
                "streetAddress": "12 rue Principale", "locality": "Laval",
                "region": "QC", "postalCode": "H7A 1A1",
            },
        },
    ],
    "tender": {
        "title": "Réfection de la rue Principale",
        "items": [
            {
                "id": "1", "description": "Pavage et bordures",
                "classification": {"scheme": "UNSPSC", "id": "72141100", "description": "Pavage"},
                "additionalClassifications": [
                    {"scheme": "UNSPSC", "id": "72103300", "description": "Entretien d'infrastructures"}
                ],
            }
        ],
    },
    "awards": [
        {
            "id": "a-1", "date": "2026-09-02T12:00:00Z", "status": "active",
            "value": {"amount": 250000, "currency": "CAD"},
            "suppliers": [{"id": "QC-NEQ-2", "name": "Constructions Untel"}],
        }
    ],
}


def _signal():
    connecteur = SEAOConnector.__new__(SEAOConnector)  # pas de registre requis ici
    # On n'exerce que la mise en forme : le téléchargement CKAN est hors test.
    from falkye.sources.seao import _buyer_name, _parse_date

    release, award = RELEASE, RELEASE["awards"][0]
    supplier = award["suppliers"][0]
    adresse = _partie_du_fournisseur(release, supplier).get("address") or {}
    return {
        "donneur_ordre": _buyer_name(release),
        "donneur_ordre_id": (release.get("buyer") or {}).get("id"),
        "secteur_nature_contrat": _classifications(release),
        "adresse_entreprise_adjudicataire": {
            "adresse": adresse.get("streetAddress"), "ville": adresse.get("locality"),
            "region": adresse.get("region"), "code_postal": adresse.get("postalCode"),
        },
        "description_besoins": _descriptions_besoins(release),
        "date": _parse_date(award["date"]),
        "connecteur": connecteur,
    }


def test_la_classification_est_portee_par_litem_pas_par_le_tender():
    """`tender.classification` n'existe pas dans le vrai fichier — chercher là
    rendait zéro classification sur 4 750 releases."""
    assert "classification" not in RELEASE["tender"]

    classifications = _classifications(RELEASE)

    assert {c["code"] for c in classifications} == {"72141100", "72103300"}
    assert all(c["scheme"] == "UNSPSC" for c in classifications)


def test_aucun_code_principal_nest_elu():
    """Élire un code parmi plusieurs serait déjà une interprétation, et la
    correspondance code → sphère est une décision de produit non prise."""
    classifications = _classifications(RELEASE)

    assert isinstance(classifications, list)
    assert len(classifications) == 2  # les deux, sans hiérarchie posée ici


def test_ladresse_du_fournisseur_vient_de_parties_pas_de_suppliers():
    """Le bloc `suppliers[]` ne porte qu'un nom et un identifiant : l'adresse vit
    dans `parties`, retrouvée par l'id. C'est 87,7 % de villes."""
    supplier = RELEASE["awards"][0]["suppliers"][0]
    assert set(supplier) == {"id", "name"}

    adresse = _partie_du_fournisseur(RELEASE, supplier)["address"]

    assert adresse["locality"] == "Laval"


def test_un_fournisseur_introuvable_dans_parties_ne_leve_pas():
    """Une release incomplète coûte une adresse, jamais le signal."""
    assert _partie_du_fournisseur(RELEASE, {"id": "inconnu"}) == {}
    assert _partie_du_fournisseur(RELEASE, {}) == {}


def test_la_description_des_besoins_vient_des_items():
    assert _descriptions_besoins(RELEASE) == ["Pavage et bordures"]


def test_les_champs_declares_au_registre_sont_livres(registry):
    """Le registre déclare ce qu'une source doit extraire et conserver *(spéc.
    section 7)*. Deux de ces champs n'étaient pas livrés — ce test les tient."""
    declares = set(registry.sources["seao"].champs_pertinents)
    livres = set(_signal())

    assert "adresse_entreprise_adjudicataire" in declares & livres
    assert "secteur_nature_contrat" in declares & livres
    assert "donneur_ordre" in declares & livres
    assert "valeur_contrat" in declares  # déjà livré avant le 2026-09-13


def test_la_ville_nest_pas_encore_promue_a_la_resolution():
    """Décision d'ordre du 2026-09-13 : la promotion de la ville change le chemin
    de résolution (+5 au score, départage entre deux entrées du REQ) et attend la
    mesure d'`apport_ville.py`. Ce test tombera le jour où on la promeut — c'est
    voulu : il force à relire la décision plutôt qu'à la contourner."""
    import inspect

    from falkye.sources import seao

    source = inspect.getsource(seao.SEAOConnector.detect)

    assert "ville=" not in source
