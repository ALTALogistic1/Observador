"""Tests du mécanisme commun de détection "nouvel établissement, pas un
renouvellement" pour les licences d'affaires municipales (Vancouver, Toronto
— spec section 7, Signal registre_corporatif, règle de calibration "NON
NÉGOCIABLE" du registre).

Régression du même bogue de calibration que REQ/Corporations Canada avant
leurs corrections (voir docs/STATUT_RESEAU.md) : le tout premier scan d'une
municipalité ne doit produire AUCUNE candidate — sinon toutes les licences
déjà anciennes seraient traitées comme "nouvelles"."""
from falkye.models.licence_municipale_entry import LicenceMunicipaleEntry
from falkye.sources.licences_municipales_communes import (
    LicenceBrute,
    detecter_nouvelles_licences,
)


def _licence(nom="Acme Inc.", adresse="123 Rue Test", type_entreprise="Retail"):
    return LicenceBrute(nom=nom, adresse=adresse, type_entreprise=type_entreprise, identifiant_source="X-001")


def test_premier_scan_ne_produit_aucune_candidate_meme_avec_des_lignes(db_session):
    """Le miroir est vide pour cette municipalité : peupler ne doit produire
    AUCUNE candidate — même précaution que Corporations Canada au premier
    import réel (~695 000 lignes)."""
    lignes = [_licence("Acme Inc."), _licence("Beta Ltée", adresse="456 Rue B")]
    nouvelles = detecter_nouvelles_licences(db_session, "Vancouver", lignes)
    assert nouvelles == []

    # Le miroir est quand même peuplé (utile pour les scans suivants)
    total = db_session.query(LicenceMunicipaleEntry).count()
    assert total == 2


def test_deuxieme_scan_detecte_une_entreprise_genuinement_nouvelle(db_session):
    detecter_nouvelles_licences(db_session, "Vancouver", [_licence("Acme Inc.")])
    db_session.commit()

    nouvelles = detecter_nouvelles_licences(
        db_session, "Vancouver", [_licence("Acme Inc."), _licence("Gamma Corp", adresse="789 Rue C")]
    )
    noms = {n.nom for n in nouvelles}
    assert noms == {"Gamma Corp"}  # Acme déjà vue, pas candidate ; Gamma nouvelle


def test_meme_entreprise_nouvelle_adresse_est_une_nouvelle_candidate(db_session):
    """Une entreprise déjà connue qui ouvre une DEUXIÈME adresse est un
    nouvel établissement légitime — même logique que le REQ (nouvel
    établissement secondaire d'une entreprise déjà connue = signal)."""
    detecter_nouvelles_licences(db_session, "Vancouver", [_licence("Acme Inc.", adresse="123 Rue Test")])
    db_session.commit()

    nouvelles = detecter_nouvelles_licences(
        db_session, "Vancouver", [_licence("Acme Inc.", adresse="999 Autre Rue")]
    )
    assert len(nouvelles) == 1
    assert nouvelles[0].adresse == "999 Autre Rue"


def test_municipalites_distinctes_sont_independantes(db_session):
    """Une entreprise déjà vue à Vancouver reste candidate pour Toronto — les
    miroirs sont isolés par municipalité. (Chaque ville passe par son propre
    "premier scan" — voir test_premier_scan_ne_produit_aucune_candidate...
    — donc on simule ici le DEUXIÈME scan de chacune pour isoler ce qu'on
    teste réellement : l'indépendance entre municipalités, pas l'effet
    premier-scan déjà couvert ailleurs.)"""
    for ville in ("Vancouver", "Toronto"):
        # "premier scan" avec une ligne de remplissage (pas "Acme Inc.") pour que le
        # miroir de chaque ville soit non vide ensuite — un scan à lignes=[] ne
        # peuplerait rien et laisserait le prochain appel être traité comme un
        # premier scan lui aussi (voir la condition dans detecter_nouvelles_licences).
        detecter_nouvelles_licences(db_session, ville, [_licence("Placeholder Inc.", adresse="0 Rue Placeholder")])
        db_session.commit()

    detecter_nouvelles_licences(db_session, "Vancouver", [_licence("Acme Inc.")])
    db_session.commit()

    nouvelles = detecter_nouvelles_licences(db_session, "Toronto", [_licence("Acme Inc.")])
    assert len(nouvelles) == 1


def test_normalisation_evite_les_faux_nouveaux_pour_variantes_de_graphie(db_session):
    detecter_nouvelles_licences(db_session, "Vancouver", [_licence("ACME INC.", adresse="123 rue Test")])
    db_session.commit()

    nouvelles = detecter_nouvelles_licences(db_session, "Vancouver", [_licence("acme inc", adresse="123 Rue Test")])
    assert nouvelles == []
