"""Le point d'entrée HTTPS — quatre routes, aucune décision.

Toute la logique vit dans `falkye/liens.py`, qui se teste sans serveur. Ce
module est l'enveloppe : il traduit une requête en appel, et un résultat en
page. S'il commençait à décider quoi que ce soit, il faudrait un serveur pour
tester une règle métier — et c'est exactement ce qu'on évite.

**Consulter montre, agir modifie.** `GET` affiche une confirmation et ne change
rien; `POST` fait le geste. Les analyseurs de liens des messageries et des
antivirus suivent les GET d'un courriel avant l'humain : sur GET, un
désabonnement partirait tout seul et une rétroaction fabriquerait de la donnée
que personne n'a voulue. Le RFC 8058 impose POST pour cette raison exacte.

**Le TLS n'est pas ici.** Cette application sert du HTTP en clair sur la boucle
locale, derrière un mandataire inverse qui porte le certificat. Terminer le TLS
dans le processus applicatif obligerait à y gérer le renouvellement, les
rechargements et les permissions sur les clés — trois choses qu'un mandataire
fait mieux, et qu'un redémarrage d'application ne doit pas interrompre.

**Aucune authentification, et c'est le sujet.** Le jeton de l'URL EST
l'autorisation, parce qu'un lien cliqué depuis un courriel ne peut rien fournir
d'autre. Ce que ça n'ouvre pas : un jeton ne vaut que pour un geste sur une
cible, ne lit aucune donnée et n'ouvre aucune session. Voir falkye/liens.py.
"""
from __future__ import annotations

from flask import Flask, Response
from markupsafe import escape

from falkye.liens import (
    LienInvalide,
    CHEMIN_DESABONNEMENT,
    CHEMIN_PAS_PERTINENT,
    consommer_desabonnement,
    consommer_pas_pertinent,
    decrire,
)
from falkye.models.jeton_lien import ActionJeton

_GABARIT = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FALKYE</title>
<style>
 body {{ font-family: system-ui, sans-serif; max-width: 34rem; margin: 4rem auto;
        padding: 0 1.5rem; line-height: 1.6; color: #1a1a1a; }}
 button {{ font: inherit; padding: .6rem 1.2rem; cursor: pointer; }}
 .discret {{ color: #666; font-size: .9rem; }}
</style></head>
<body>{corps}</body></html>
"""


def _page(corps: str, statut: int = 200) -> Response:
    return Response(_GABARIT.format(corps=corps), status=statut, mimetype="text/html; charset=utf-8")


def _page_lien_invalide() -> Response:
    """Même page pour un jeton inconnu, expiré ou employé pour une autre action.

    Ne pas distinguer les cas : la différence ne renseignerait que quelqu'un qui
    sonde des jetons, et n'aiderait pas la personne qui a simplement un vieux
    lien.
    """
    return _page(
        "<h1>Ce lien n'est plus valide</h1>"
        "<p>Il a peut-être été remplacé par un lien plus récent. "
        "Le lien du dernier résumé reçu fonctionnera.</p>",
        statut=404,
    )


def creer_app(fabrique_session=None) -> Flask:
    """`fabrique_session` : appelable sans argument retournant une session.

    Injectée plutôt qu'importée pour que les tests branchent une base en
    mémoire sans monter de serveur ni toucher à la configuration.
    """
    if fabrique_session is None:
        from falkye.db import get_session

        fabrique_session = get_session

    app = Flask(__name__)

    def _avec_session(travail):
        session = fabrique_session()
        try:
            reponse = travail(session)
            session.commit()
            return reponse
        except LienInvalide:
            session.rollback()
            return _page_lien_invalide()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _formulaire(titre: str, explication: str, libelle_bouton: str) -> str:
        # L'action du formulaire est l'URL courante : le jeton reste dans le
        # chemin, jamais recopié dans un champ caché où un journal de mandataire
        # ou un en-tête Referer le ramasserait.
        return (
            f"<h1>{titre}</h1><p>{explication}</p>"
            f'<form method="post"><button type="submit">{libelle_bouton}</button></form>'
        )

    # --- Désabonnement (RFC 8058) -----------------------------------------

    @app.get(f"/{CHEMIN_DESABONNEMENT}/<jeton>")
    def desabonnement_confirmer(jeton):
        def travail(session):
            infos = decrire(session, jeton, ActionJeton.DESABONNEMENT)
            if infos["deja_fait"]:
                return _page(
                    "<h1>C'est déjà fait</h1>"
                    f"<p>{escape(infos['courriel'])} ne reçoit plus de résumés.</p>"
                )
            return _page(
                _formulaire(
                    "Ne plus recevoir les résumés",
                    f"Confirmez et {escape(infos['courriel'])} cessera de recevoir les résumés FALKYE.",
                    "Confirmer le désabonnement",
                )
            )

        return _avec_session(travail)

    @app.post(f"/{CHEMIN_DESABONNEMENT}/<jeton>")
    def desabonnement_appliquer(jeton):
        # Gmail et Yahoo envoient ici `List-Unsubscribe=One-Click` en corps de
        # formulaire. Le corps n'est pas lu : le jeton du chemin porte déjà tout
        # ce qu'il faut, et exiger un contenu précis ferait échouer le bouton
        # natif d'un fournisseur qui formaterait autrement.
        def travail(session):
            profile = consommer_desabonnement(session, jeton)
            return _page(
                "<h1>C'est fait</h1>"
                f"<p>{escape(profile.courriel)} ne recevra plus de résumés.</p>"
                "<p class=\"discret\">Vous pouvez revenir en écrivant à cette même adresse.</p>"
            )

        return _avec_session(travail)

    # --- Rétroaction « pas pertinent » ------------------------------------

    @app.get(f"/{CHEMIN_PAS_PERTINENT}/<jeton>")
    def pas_pertinent_confirmer(jeton):
        def travail(session):
            infos = decrire(session, jeton, ActionJeton.PAS_PERTINENT)
            entreprise = escape(infos.get("entreprise") or "cette entreprise")
            if infos["deja_fait"]:
                return _page(
                    "<h1>C'est déjà noté</h1>"
                    f"<p>{entreprise} a été marquée comme non pertinente.</p>"
                )
            return _page(
                _formulaire(
                    "Marquer comme non pertinent",
                    f"{entreprise} ne correspondait pas à ce que vous cherchez. "
                    "Cette réponse ajuste les prochains repérages pour votre profil.",
                    "Confirmer",
                )
            )

        return _avec_session(travail)

    @app.post(f"/{CHEMIN_PAS_PERTINENT}/<jeton>")
    def pas_pertinent_appliquer(jeton):
        def travail(session):
            notification = consommer_pas_pertinent(session, jeton)
            nom = notification.company.nom_officiel_req or notification.company.nom_detecte
            return _page(
                "<h1>C'est noté</h1>"
                f"<p>{escape(nom)} est marquée comme non pertinente, et les prochains "
                "repérages en tiendront compte.</p>"
            )

        return _avec_session(travail)

    # --- Santé -------------------------------------------------------------

    @app.get("/sante")
    def sante():
        """Le mandataire inverse a besoin de savoir si le processus répond.

        Volontairement muette sur l'état de la base : une sonde de santé qui
        interroge la base transforme une lenteur de base en application
        « morte », et le mandataire retire alors le seul chemin par lequel un
        désabonnement pourrait encore passer.
        """
        return Response("ok\n", mimetype="text/plain")

    @app.errorhandler(404)
    def non_trouve(_):
        return _page_lien_invalide()

    return app


def create_app():
    """Fabrique reconnue par les serveurs WSGI.

    Servi en production par `gunicorn 'falkye.web.app:create_app()'`, derrière
    le mandataire inverse qui porte le certificat.
    """
    return creer_app()
