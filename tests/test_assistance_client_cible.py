"""Tests du Niveau 1 de l'assistance à la configuration du profil par IA,
dimension "qui" (falkye/assistance_client_cible.py) — spec section 8bis
(2026-09-03). Miroir de tests/test_assistance_sphere.py."""
from falkye.assistance_client_cible import (
    suggerer_clients_cibles_niveau1,
    suggerer_clients_cibles_niveau1_pour_company,
)
from falkye.models.client_cible import ClientCible
from falkye.models.client_cible_synonyme import ClientCibleSynonyme
from falkye.models.company import Company


def _semer_categories(db_session):
    db_session.add_all(
        [
            ClientCible(id="aucune_restriction", nom="Aucune restriction — s'applique largement"),
            ClientCible(id="organismes_publics_institutionnels", nom="Organismes publics et institutionnels"),
            ClientCible(id="pme_privees_generales", nom="PME privées, tous secteurs"),
        ]
    )
    db_session.add_all(
        [
            ClientCibleSynonyme(client_cible_id="aucune_restriction", texte="aucune restriction", origine="registre"),
            ClientCibleSynonyme(
                client_cible_id="organismes_publics_institutionnels", texte="commission scolaire", origine="registre"
            ),
            ClientCibleSynonyme(
                client_cible_id="organismes_publics_institutionnels", texte="société de transport", origine="registre"
            ),
            ClientCibleSynonyme(client_cible_id="pme_privees_generales", texte="PME", origine="registre"),
        ]
    )
    db_session.flush()


def test_trouve_la_categorie_avec_le_plus_de_mots_cles_matches(db_session):
    _semer_categories(db_session)
    suggestions = suggerer_clients_cibles_niveau1(
        db_session, "Nous travaillons avec une commission scolaire et une société de transport"
    )
    assert suggestions
    assert suggestions[0].client_cible_id == "organismes_publics_institutionnels"
    assert suggestions[0].score == 2


def test_aucune_restriction_matche_normalement(db_session):
    """"aucune_restriction" matche comme n'importe quelle autre catégorie —
    pas de traitement spécial au Niveau 1 (voir docstring du module)."""
    _semer_categories(db_session)
    suggestions = suggerer_clients_cibles_niveau1(db_session, "Aucune restriction, tous types de clients")
    assert suggestions
    assert suggestions[0].client_cible_id == "aucune_restriction"


def test_aucune_correspondance_retourne_liste_vide(db_session):
    _semer_categories(db_session)
    suggestions = suggerer_clients_cibles_niveau1(db_session, "Vente de meubles artisanaux faits main")
    assert suggestions == []


def test_description_vide_retourne_liste_vide(db_session):
    _semer_categories(db_session)
    assert suggerer_clients_cibles_niveau1(db_session, "") == []


# --- Classification cross-source d'une entreprise détectée (spec section 8bis,
# point 2, 2026-09-03) — voir la docstring du module testé pour la liste des
# champs délibérément exclus (donneur d'ordre, poste affiché, etc.). ---


def test_niveau1_pour_company_utilise_le_secteur_activite(db_session):
    """company.secteur_activite_libelle EST DÉJÀ la fusion cross-source pour
    REQ et les licences municipales hors Québec (voir falkye/resolution.py) —
    aucun mécanisme séparé nécessaire, juste appeler le matcher contre CE
    champ précis."""
    _semer_categories(db_session)
    company = Company(
        nom_detecte="Commission scolaire Test",
        nom_detecte_normalise="commission scolaire test",
        secteur_activite_libelle="Commission scolaire",
    )
    suggestions = suggerer_clients_cibles_niveau1_pour_company(db_session, company)
    assert suggestions
    assert suggestions[0].client_cible_id == "organismes_publics_institutionnels"


def test_niveau1_pour_company_secteur_vide_retourne_liste_vide(db_session):
    """Sans secteur classifiable, "qui inconnu" — jamais une catégorie forcée,
    jamais une escalade Niveau 2 pour une entreprise détectée (coût IA par
    entreprise scannée jamais introduit sans demande explicite)."""
    _semer_categories(db_session)
    company = Company(nom_detecte="Entreprise Sans Secteur", nom_detecte_normalise="entreprise sans secteur")
    assert suggerer_clients_cibles_niveau1_pour_company(db_session, company) == []
