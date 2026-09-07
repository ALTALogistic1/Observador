"""Tests du point d'entrée HTTPS — falkye/web/app.py.

Ce que ces tests protègent avant tout : **consulter ne doit rien modifier**. Les
analyseurs de liens des messageries et des antivirus suivent les liens d'un
courriel avant l'humain; si une simple visite désabonnait, ou marquait un
prospect non pertinent, le produit fabriquerait de la donnée que personne n'a
voulue — dans son seul mécanisme de correction.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import falkye.models  # noqa: F401
from falkye.liens import url_desabonnement, url_pas_pertinent
from falkye.models.base import Base
from falkye.models.company import Company, StatutLegal, StatutResolution, StatutVerification
from falkye.models.notification import ModeUsage, NiveauConfiance, NiveauPertinence, Notification
from falkye.models.profile import Profile
from falkye.models.sphere import Sphere
from falkye.web.app import creer_app


@pytest.fixture()
def fabrique():
    """Une base en mémoire PARTAGÉE entre toutes les sessions.

    StaticPool plutôt que le pool par défaut : l'application ouvre et ferme une
    session par requête, et sans lui chaque requête verrait une base vide.
    """
    moteur = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(moteur)
    return sessionmaker(bind=moteur)


@pytest.fixture()
def client(fabrique):
    app = creer_app(fabrique_session=fabrique)
    app.config.update(TESTING=True)
    return app.test_client()


def _donnees(fabrique, nom_entreprise="Transport Bourassa"):
    """Retourne (chemin_desabonnement, chemin_pas_pertinent, profile_id, notification_id)."""
    session = fabrique()
    try:
        session.add(Sphere(id="gestion_projet", nom="Gestion de projet"))
        p = Profile(courriel="alexandre@exemple.com", nom="Alexandre")
        session.add(p)
        session.flush()
        c = Company(
            nom_detecte=nom_entreprise,
            nom_detecte_normalise=nom_entreprise.lower(),
            statut_legal=StatutLegal.IMMATRICULEE,
            statut_resolution=StatutResolution.RESOLU,
            statut_verification=list(StatutVerification)[0],
        )
        session.add(c)
        session.flush()
        n = Notification(
            company_id=c.id,
            profile_id=p.id,
            mode=ModeUsage.VEILLE_CONTINUE,
            score_confiance=70.0,
            niveau_confiance=NiveauConfiance.ELEVE,
            niveau_pertinence=NiveauPertinence.AA,
            sphere_probable_id="gestion_projet",
            justification_resumee="test",
        )
        session.add(n)
        session.flush()
        chemin_d = "/" + url_desabonnement(session, p).split("/", 3)[3]
        chemin_r = "/" + url_pas_pertinent(session, n).split("/", 3)[3]
        session.commit()
        return chemin_d, chemin_r, p.id, n.id
    finally:
        session.close()


def _profil(fabrique, profile_id):
    session = fabrique()
    try:
        return session.get(Profile, profile_id)
    finally:
        session.close()


def _notification(fabrique, notification_id):
    session = fabrique()
    try:
        return session.get(Notification, notification_id)
    finally:
        session.close()


# --- Consulter ne modifie rien : le test central ---------------------------


def test_visiter_le_lien_de_desabonnement_ne_desabonne_pas(client, fabrique):
    chemin_d, _, profile_id, _ = _donnees(fabrique)

    reponse = client.get(chemin_d)

    assert reponse.status_code == 200
    assert _profil(fabrique, profile_id).desabonne_le is None
    assert b"<form method=\"post\">" in reponse.data


def test_visiter_le_lien_de_retroaction_ne_marque_rien(client, fabrique):
    _, chemin_r, _, notification_id = _donnees(fabrique)

    reponse = client.get(chemin_r)

    assert reponse.status_code == 200
    assert _notification(fabrique, notification_id).statut_suivi_id is None


# --- Agir ------------------------------------------------------------------


def test_poster_desabonne(client, fabrique):
    chemin_d, _, profile_id, _ = _donnees(fabrique)

    reponse = client.post(chemin_d)

    assert reponse.status_code == 200
    assert _profil(fabrique, profile_id).desabonne_le is not None


def test_le_un_clic_des_messageries_fonctionne_tel_quel(client, fabrique):
    """Gmail et Yahoo postent `List-Unsubscribe=One-Click` en corps de
    formulaire, sans témoin ni jeton anti-CSRF. Le corps n'est pas lu — exiger
    un contenu précis ferait échouer le bouton natif d'un fournisseur qui
    formaterait autrement."""
    chemin_d, _, profile_id, _ = _donnees(fabrique)

    reponse = client.post(chemin_d, data={"List-Unsubscribe": "One-Click"})

    assert reponse.status_code == 200
    assert _profil(fabrique, profile_id).desabonne_le is not None


def test_poster_marque_pas_pertinent(client, fabrique):
    _, chemin_r, _, notification_id = _donnees(fabrique)

    reponse = client.post(chemin_r)

    assert reponse.status_code == 200
    assert _notification(fabrique, notification_id).statut_suivi_id == "pas_pertinent"


def test_un_second_envoi_confirme_au_lieu_dechouer(client, fabrique):
    """Une erreur affichée à qui se désabonne deux fois le pousse vers le bouton
    « pourriel », qui coûte à la réputation du domaine entier."""
    chemin_d, _, _, _ = _donnees(fabrique)

    client.post(chemin_d)
    reponse = client.post(chemin_d)

    assert reponse.status_code == 200


# --- Les liens qui ne valent rien -----------------------------------------


def test_un_jeton_inconnu_donne_la_meme_page_quun_jeton_de_mauvaise_action(client, fabrique):
    """Ne pas distinguer les cas : la différence ne renseignerait que quelqu'un
    qui sonde des jetons."""
    chemin_d, _, profile_id, _ = _donnees(fabrique)
    jeton_desabo = chemin_d.rsplit("/", 1)[-1]

    inconnu = client.get("/d/jeton-qui-nexiste-pas")
    mauvaise_action = client.get(f"/r/{jeton_desabo}")

    assert inconnu.status_code == 404
    assert mauvaise_action.status_code == 404
    assert inconnu.data == mauvaise_action.data


def test_un_jeton_de_desabonnement_poste_sur_la_retroaction_ne_fait_rien(client, fabrique):
    chemin_d, _, profile_id, notification_id = _donnees(fabrique)
    jeton_desabo = chemin_d.rsplit("/", 1)[-1]

    reponse = client.post(f"/r/{jeton_desabo}")

    assert reponse.status_code == 404
    assert _profil(fabrique, profile_id).desabonne_le is None
    assert _notification(fabrique, notification_id).statut_suivi_id is None


# --- Divers ---------------------------------------------------------------


def test_le_nom_dentreprise_est_echappe(client, fabrique):
    """Un nom d'entreprise vient d'une source externe : il ne doit jamais
    atteindre la page tel quel."""
    _, chemin_r, _, _ = _donnees(fabrique, nom_entreprise="<script>alert(1)</script>")

    reponse = client.get(chemin_r)

    assert b"<script>alert(1)</script>" not in reponse.data
    assert b"&lt;script&gt;" in reponse.data


def test_la_sonde_de_sante_ne_touche_pas_la_base(client):
    """Une sonde qui interroge la base transforme une lenteur de base en
    application « morte », et le mandataire retire alors le seul chemin par
    lequel un désabonnement pourrait encore passer."""
    reponse = client.get("/sante")

    assert reponse.status_code == 200
    assert reponse.data == b"ok\n"
