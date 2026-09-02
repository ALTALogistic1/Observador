"""Tests du géocodage (falkye/geocoding.py) — spec section 4bis. IMPORTANT (voir
docstring du module testé) : la forme de la réponse Nominatim ci-dessous est une
hypothèse plausible d'après la documentation publique, jamais confirmée par un
vrai appel (nominatim.openstreetmap.org est bloqué par le proxy réseau de cet
environnement). Ces tests valident donc la logique de cache et de normalisation,
pas une réponse réelle capturée."""
from datetime import datetime, timezone

import responses

from falkye.geocoding import NOMINATIM_URL, NominatimGeocoder, geocoder_entreprise
from falkye.models.company import Company


def _company():
    return Company(nom_detecte="Entreprise Test", nom_detecte_normalise="entreprise test", ville="Montréal")


@responses.activate
def test_nominatim_geocoder_retourne_lat_lon():
    responses.add(responses.GET, NOMINATIM_URL, json=[{"lat": "45.5017", "lon": "-73.5673"}], status=200)
    geocoder = NominatimGeocoder()
    resultat = geocoder.geocoder(None, "Montréal", "Québec")
    assert resultat == (45.5017, -73.5673)


@responses.activate
def test_nominatim_geocoder_retourne_none_si_aucun_resultat():
    responses.add(responses.GET, NOMINATIM_URL, json=[], status=200)
    geocoder = NominatimGeocoder()
    assert geocoder.geocoder(None, "Ville Inconnue Improbable", None) is None


def test_nominatim_geocoder_retourne_none_sans_donnee_de_localisation():
    geocoder = NominatimGeocoder()
    assert geocoder.geocoder(None, None, None) is None


class _GeocoderFactice:
    def __init__(self, resultat):
        self.resultat = resultat
        self.nb_appels = 0

    def geocoder(self, adresse, ville, region):
        self.nb_appels += 1
        return self.resultat


def test_geocoder_entreprise_persiste_les_coordonnees():
    company = _company()
    geocoder = _GeocoderFactice((45.5, -73.6))
    assert geocoder_entreprise(company, geocoder) is True
    assert company.latitude == 45.5
    assert company.longitude == -73.6
    assert company.geocode_tente_le is not None


def test_geocoder_entreprise_ne_refait_pas_l_appel_si_deja_geocodee():
    company = _company()
    company.latitude = 1.0
    company.longitude = 2.0
    geocoder = _GeocoderFactice((99.0, 99.0))
    assert geocoder_entreprise(company, geocoder) is True
    assert geocoder.nb_appels == 0
    assert company.latitude == 1.0  # inchangé


def test_geocoder_entreprise_ne_reessaie_pas_apres_un_echec_deja_tente():
    company = _company()
    company.geocode_tente_le = datetime.now(timezone.utc)
    geocoder = _GeocoderFactice((45.5, -73.6))
    assert geocoder_entreprise(company, geocoder) is False
    assert geocoder.nb_appels == 0  # déjà tenté (échoué) — pas de nouvel appel


def test_geocoder_entreprise_retourne_false_si_aucune_correspondance():
    company = _company()
    geocoder = _GeocoderFactice(None)
    assert geocoder_entreprise(company, geocoder) is False
    assert company.latitude is None
    assert company.geocode_tente_le is not None  # marqué comme tenté malgré l'échec
