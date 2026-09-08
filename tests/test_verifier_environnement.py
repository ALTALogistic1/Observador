"""Ce que ces tests protègent : **le document qui a l'air complet et ne l'est pas.**

Trois fois en deux jours, une configuration s'est révélée incomplète au pire
moment — le groupe de journalisation, la ligne `stop`, puis `FALKYE_LIEN_BASE_URL`
découverte par le refus du premier envoi réel. Le point commun n'est aucune des
trois : c'est que rien ne comparait ce qui est déclaré à ce qui existe.
"""
import pytest

from outils.verifier_environnement import (
    ROLES,
    variables_declarees,
    variables_lues_par_le_code,
    verifier,
)


# --- Le test qui empêche la liste des rôles de pourrir ----------------------


def test_chaque_variable_de_role_est_reellement_lue_par_le_code():
    """ROLES est la seule partie tenue à la main. Sans ce test, elle
    dériverait en silence — un rôle exigeant une variable que plus personne ne
    lit ferait échouer un déploiement pour rien, et l'outil bâti contre la
    dérive en produirait une."""
    lues = set(variables_lues_par_le_code())
    for role, variables in ROLES.items():
        for nom in variables:
            assert nom in lues, f"{nom} exigée par le rôle « {role} » n'est lue nulle part"


def test_chaque_variable_de_role_est_declaree_dans_lexemple(tmp_path):
    """Exiger d'un opérateur une variable que le document ne mentionne pas
    serait lui demander de deviner."""
    from pathlib import Path

    declarees = variables_declarees(Path(__file__).resolve().parent.parent / ".env.example")
    for role, variables in ROLES.items():
        for nom in variables:
            assert nom in declarees, f"{nom} ({role}) manque à .env.example"


# --- Le dépôt lui-même doit être conforme -----------------------------------


def test_le_depot_ne_porte_aucune_derive():
    """Le contrôle tourne sur le dépôt réel. S'il échoue, c'est que quelqu'un a
    ajouté une lecture d'environnement sans la déclarer — exactement la dérive
    qui a laissé partir un serveur sans FALKYE_LIEN_BASE_URL."""
    anomalies = verifier(environnement={}, roles=[])
    assert anomalies == [], "\n".join(anomalies)


# --- Les trois comparaisons -------------------------------------------------


def _faux_depot(tmp_path, code: str, exemple: str):
    (tmp_path / "falkye").mkdir()
    (tmp_path / "outils").mkdir()
    (tmp_path / "falkye" / "m.py").write_text(code)
    (tmp_path / ".env.example").write_text(exemple)
    return tmp_path


def test_une_variable_lue_mais_non_declaree_est_signalee(tmp_path):
    racine = _faux_depot(tmp_path, 'import os\nos.environ.get("FALKYE_OUBLIEE")\n', "AUTRE=\n")

    anomalies = verifier({}, roles=[], racine=racine)

    assert any("NON DÉCLARÉE" in a and "FALKYE_OUBLIEE" in a for a in anomalies)


def test_une_declaration_morte_est_signalee(tmp_path):
    racine = _faux_depot(tmp_path, "x = 1\n", "FALKYE_FANTOME=\n")

    anomalies = verifier({}, roles=[], racine=racine)

    assert any("DÉCLARATION MORTE" in a and "FALKYE_FANTOME" in a for a in anomalies)


def test_une_variable_de_role_absente_est_signalee_avec_sa_raison(tmp_path):
    """Le message doit suffire à réparer sans aller lire le code."""
    anomalies = verifier({}, roles=["envoi"])

    ligne = next(a for a in anomalies if "FALKYE_LIEN_BASE_URL" in a)
    assert "MANQUANTE" in ligne
    assert "aucun résumé ne part" in ligne.lower() or "AUCUN résumé ne part" in ligne


def test_une_valeur_vide_compte_comme_absente(tmp_path):
    """`FALKYE_LIEN_BASE_URL=` dans un fichier d'environnement définit la
    variable à la chaîne vide — l'oubli le plus probable."""
    anomalies = verifier({"FALKYE_LIEN_BASE_URL": "   "}, roles=["envoi"])

    assert any("FALKYE_LIEN_BASE_URL" in a for a in anomalies)


# --- Le silence par défaut, qui est ce qui rend l'outil utilisable ----------


def test_sans_role_demande_aucun_controle_denvironnement(tmp_path):
    """En développement, l'absence des clés Postmark est NORMALE. Les signaler
    à chaque exécution ferait de cet outil un avertissement permanent, donc
    ignoré — le défaut qu'on cherche justement à éviter."""
    anomalies = verifier(environnement={}, roles=None)

    assert not any("MANQUANTE" in a for a in anomalies)


def test_les_commentaires_de_lexemple_ne_comptent_pas_comme_declarations(tmp_path):
    """`# TWILIO_ACCOUNT_SID=` est une note, pas une déclaration — la compter
    produirait une fausse « déclaration morte » à chaque exécution."""
    racine = _faux_depot(tmp_path, "x = 1\n", "# COMMENTEE=\nVRAIE=\n")

    anomalies = verifier({}, roles=[], racine=racine)

    assert not any("COMMENTEE" in a for a in anomalies)
    assert any("VRAIE" in a for a in anomalies)
