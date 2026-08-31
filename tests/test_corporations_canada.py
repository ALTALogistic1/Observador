"""Test de régression pour un bug réel trouvé en validant le connecteur
Corporations Canada avec de vraies données (2026-08-31) : "inactive" contient
la sous-chaîne "active", donc un filtre name_contains="active" naïf attrapait
aussi les ressources de corporations dissoutes."""
from observador.sources.corporations_canada import _filtrer_ressources_actives


def test_filtre_exclut_les_ressources_inactive():
    resources = [
        {"name": "Active business corporations"},
        {"name": "Inactive business corporations"},
        {"name": "Other active corporations"},
        {"name": "Other inactive corporations"},
    ]
    filtres = _filtrer_ressources_actives(resources)
    noms = {r["name"] for r in filtres}
    assert noms == {"Active business corporations", "Other active corporations"}


def test_filtre_insensible_a_la_casse():
    resources = [{"name": "INACTIVE Corporations"}, {"name": "Active Corporations"}]
    filtres = _filtrer_ressources_actives(resources)
    assert len(filtres) == 1
    assert filtres[0]["name"] == "Active Corporations"
