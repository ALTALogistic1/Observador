"""Résumé périodique — la forme de livraison PAR DÉFAUT depuis le 2026-09-05.

Charte section 16 : « le groupement est la forme par défaut; l'envoi unitaire est
l'exception justifiée, jamais l'inverse — l'exception a besoin d'un seuil
explicite, sinon elle redevient la norme par glissement ». Le courriel individuel
par notification ne part plus (voir falkye/engine.py::deliver_notification, qui ne
sert plus que les canaux poussant vers un système).

Deux corrections structurelles apportées le 2026-09-05, l'une et l'autre invisibles
en test parce que ce module n'en avait AUCUN :

**Le lot ne se perd plus.** L'ancienne version marquait les notifications
« incluses » AVANT d'envoyer, et les sélectionnait par fenêtre de dates. Un envoi
en échec laissait donc des opportunités marquées comme livrées, définitivement :
la fenêtre suivante ne les voyait plus. C'était le même motif que la quarantaine
du chantier 1 — un filet qui capture sans livrer. Désormais la sélection porte sur
l'ÉTAT (`inclus_dans_resume`), pas sur une fenêtre, et le marquage n'a lieu
qu'après un envoi réussi. Une opportunité attend donc autant de cycles qu'il le
faut, et sort au premier envoi qui aboutit.

**Un seul chemin de livraison.** L'envoi passe par
falkye/notifications/livraison.py, comme la livraison unitaire — voir ce module
pour ce que la divergence des deux chemins coûtait.

`periode_debut` reste enregistrée comme métadonnée du résumé (la fenêtre que
l'appelant avait en tête), mais ne filtre plus rien : c'est l'état d'attente qui
décide. Conséquence assumée, à connaître : un tout premier résumé sur une base qui
porte déjà des notifications les emporte toutes. Le plafond d'antériorité du
chantier 25 est ce qui bornera ça — il n'entre pas ici.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html import escape

from sqlalchemy import func, nullslast, select
from sqlalchemy.orm import Session

from falkye.liens import url_desabonnement, url_pas_pertinent
from falkye.models.notification import Notification, NotificationSignal, PeriodicSummary
from falkye.models.profile import Profile
from falkye.models.signal import Signal
from falkye.notifications.base import FORME_RESUME, NotificationContent
from falkye.notifications.livraison import au_moins_un_succes, livrer
from falkye.registry.loader import Registry, get_registry

_NIVEAU_AFFICHAGE = {"faible": "Faible", "moyen": "Moyen", "eleve": "Élevé"}

# Nombre maximal d'opportunités dans UN résumé (décision d'Alexandre du
# 2026-09-06 : « un résumé de trois cents entrées n'est pas un résumé, quelle que
# soit la qualité du reste »).
#
# Le premier envoi réel en portait 306. Ce n'était pas un rendez-vous
# hebdomadaire, c'était un déversoir — et c'est le profil de contenu que les
# filtres antipourriel scrutent le plus (mandat, point de vigilance du
# chantier 21).
#
# Dix : une personne agit sur une poignée d'opportunités dans sa semaine, pas sur
# trente. Le chiffre est un point de départ à corriger par l'observation
# (principe directeur #9), pas une valeur démontrée — d'où une constante nommée
# plutôt qu'un nombre semé dans le code.
#
# Ce que le plafond NE règle pas : le reste attend son tour et sortira aux cycles
# suivants, ce qui étale un arriéré de 306 sur une trentaine de semaines. Le
# plafond d'ANTÉRIORITÉ, qui bornerait l'arriéré lui-même, appartient au
# chantier 25 et n'entre pas ici.
PLAFOND_OPPORTUNITES = 10


def _valeur_du_signal():
    """La plus grande valeur monétaire portée par les signaux d'une notification.

    Sert UNIQUEMENT à départager les ex æquo, jamais à scorer — le score reste
    entièrement l'affaire de falkye/scoring.py.

    Pourquoi c'est nécessaire dès qu'il y a un plafond : sur les 306 opportunités
    du premier envoi, 182 partageaient exactement le même score de 85. L'ordre
    entre elles était donc celui de leur identifiant, c'est-à-dire celui du
    fichier source. Un plafond posé sur cet ordre-là aurait livré chaque semaine
    les dix premières lignes du fichier — un tri arbitraire promu en sélection.
    Départager par le montant utilise un fait que le signal porte déjà.
    """
    return (
        select(func.max(Signal.valeur_associee))
        .select_from(NotificationSignal)
        .join(Signal, Signal.id == NotificationSignal.signal_id)
        .where(NotificationSignal.notification_id == Notification.id)
        .scalar_subquery()
    )


def notifications_en_attente(db_session: Session, profile: Profile, avant: datetime) -> list[Notification]:
    """Les opportunités qui n'ont encore été livrées par aucun résumé.

    Deux filtres, et pas de fenêtre de dates basse — voir la docstring du module.

    `hors_profil` est exclu : un signal redirigé hors du profil déclaré n'est
    « jamais mélangé aux notifications normales » (spec section 8bis) et ne se
    consulte qu'au tableau de bord. L'ancienne version l'incluait au résumé alors
    que la livraison unitaire l'excluait déjà — troisième divergence entre les
    deux chemins, corrigée ici.
    """
    return list(
        db_session.execute(
            select(Notification)
            .where(
                Notification.profile_id == profile.id,
                Notification.inclus_dans_resume.is_(False),
                Notification.hors_profil.is_(False),
                Notification.created_at < avant,
            )
            .order_by(Notification.score_confiance.desc(), nullslast(_valeur_du_signal().desc()))
        )
        .scalars()
        .all()
    )


def generer_resume(
    db_session: Session, profile: Profile, periode_debut: datetime, periode_fin: datetime
) -> tuple[PeriodicSummary, list[Notification]]:
    """Construit le résumé SANS marquer quoi que ce soit comme livré.

    Le marquage appartient à `generer_et_envoyer_resume`, après un envoi réussi —
    c'est toute la correction du lot perdu.

    Retourne aussi le NOMBRE TOTAL en attente, plafond compris. Le résumé doit
    pouvoir dire combien il en reste : taire l'arriéré ferait croire que la
    semaine n'a produit que dix opportunités, et l'arriéré s'écoulerait sans que
    personne sache qu'il existe.

    Seules les opportunités RETENUES entrent dans `notification_ids` : ce sont
    elles, et elles seules, qui seront marquées livrées après un envoi réussi.
    Les autres restent en attente et repartiront — le plafond borne le message,
    jamais le lot.
    """
    en_attente = notifications_en_attente(db_session, profile, avant=periode_fin)
    notifications = en_attente[:PLAFOND_OPPORTUNITES]

    summary = PeriodicSummary(
        profile_id=profile.id,
        periode_debut=periode_debut,
        periode_fin=periode_fin,
        notification_ids=[n.id for n in notifications],
    )
    db_session.add(summary)
    db_session.flush()
    return summary, notifications, len(en_attente)


@dataclass
class BlocOpportunite:
    """Une opportunité, AVANT tout rendu.

    Pourquoi une structure plutôt qu'une chaîne. Le résumé part en deux formes,
    texte et HTML. Écrites séparément, elles divergeraient — et une divergence
    entre deux formes du MÊME message est un mensonge : la personne qui lit
    l'une n'aurait pas la même information que celle qui lit l'autre, sans que
    rien ne le signale. C'est la même leçon que la réunification des chemins de
    livraison, appliquée au rendu. Les deux formes se construisent donc ici, à
    partir d'une seule source, et un test vérifie qu'elles portent exactement le
    même texte visible.
    """

    titre: str
    details: list[str]
    lien_pas_pertinent: str | None = None


def _bloc_opportunite(
    notification: Notification,
    registry: Registry,
    lien_pas_pertinent: str | None = None,
    ligne_interpretation: str | None = None,
) -> BlocOpportunite:
    """Une opportunité : ce qu'elle est, pourquoi elle a été repérée.

    Le MOTIF DU REPÉRAGE est ce qui manquait au résumé. Charte section 16 : « un
    résultat n'est bon que s'il donne une raison d'agir maintenant, pas seulement
    un nom — un nom d'entreprise sans le motif précis du repérage ne vaut pas mieux
    qu'une liste achetée ailleurs ». Les motifs viennent de la structure de faits
    déjà produite par le moteur (`NotificationSignal.justification`), reprise ici
    telle quelle plutôt que reformulée.

    La CATÉGORIE de signal est affichée, jamais le nom de la source — neutralité
    des libellés (charte section 6), même règle que le formateur individuel.

    `ligne_interpretation` est la place RÉSERVÉE, et volontairement vide, pour la
    ligne d'interprétation du chantier 21 (gabarits liés au couple signal ×
    sphère). Elle ne se remplit pas ici : ce chantier livre la version brute. Le
    paramètre existe pour que la place ne soit pas à rouvrir, et le rendu n'émet
    rien tant que rien ne lui est passé — jamais un texte de remplissage, qui
    serait précisément l'encouragement non mérité que la section 16 interdit.
    """
    nom = notification.company.nom_officiel_req or notification.company.nom_detecte
    niveau = _NIVEAU_AFFICHAGE[notification.niveau_confiance.value]
    pertinence = notification.niveau_pertinence.value if notification.niveau_pertinence else "non disponible"

    details: list[str] = []
    if ligne_interpretation:
        details.append(ligne_interpretation)

    for ns in notification.signaux_contributifs:
        signal_type = registry.signal_types.get(ns.signal.signal_type_id)
        categorie = signal_type.nom if signal_type else ns.signal.signal_type_id
        # Un motif vide n'écrit rien après la catégorie. Le remplir d'une phrase
        # creuse (« Signal détecté », la version d'avant) prétendrait dire
        # quelque chose de plus que ce qu'on sait — voir falkye/motif.py.
        motif = (ns.justification or "").strip()
        details.append(f"[{categorie}] {motif}".rstrip())

    if notification.company.ville:
        details.append(notification.company.ville)

    return BlocOpportunite(
        titre=(
            f"{nom} — confiance {niveau} ({notification.score_confiance}/100), "
            f"pertinence {pertinence}"
        ),
        details=details,
        lien_pas_pertinent=lien_pas_pertinent,
    )


# La rétroaction minimale — la seule boucle de correction du produit. Formulée
# par l'action qu'elle appelle, jamais comme un jugement sur l'opportunité
# (charte section 16).
LIBELLE_PAS_PERTINENT = "Pas pertinent pour vous?"


def _bloc_en_texte(bloc: BlocOpportunite) -> str:
    lignes = [f"• {bloc.titre}"]
    lignes += [f"    {d}" for d in bloc.details]
    if bloc.lien_pas_pertinent:
        lignes.append(f"    {LIBELLE_PAS_PERTINENT} {bloc.lien_pas_pertinent}")
    return "\n".join(lignes)


def _bloc_en_html(bloc: BlocOpportunite) -> str:
    """Le MÊME contenu, balisé au minimum.

    Aucune feuille de style, aucune image, aucun tableau : le mandat demande du
    texte lisible, pas un gabarit. La partie HTML existe parce qu'un envoi de
    diffusion en texte seul est un signal négatif pour les filtres, pas pour
    mettre en forme.
    """
    lignes = [f"<strong>{escape(bloc.titre)}</strong>"]
    lignes += [escape(d) for d in bloc.details]
    if bloc.lien_pas_pertinent:
        cible = escape(bloc.lien_pas_pertinent)
        # Le texte du lien est l'URL elle-même : identique à la version texte,
        # et une URL visible se vérifie d'un coup d'œil là où un libellé
        # cliquable masque sa destination.
        lignes.append(f"{escape(LIBELLE_PAS_PERTINENT)} <a href=\"{cible}\">{cible}</a>")
    return "<p>" + "<br>\n".join(lignes) + "</p>"


_MOIS = (
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
)


def _date_en_francais(moment: datetime) -> str:
    """Sans dépendre d'une locale système : `locale.setlocale(LC_TIME, "fr_CA")`
    échoue sur une image qui n'a pas le paquet de langue, et l'objet du courriel
    basculerait alors en anglais sur l'hôte de production seulement — une
    différence que les tests ne verraient jamais."""
    return f"{moment.day} {_MOIS[moment.month - 1]} {moment.year}"


def sujet_du_resume(summary: PeriodicSummary, nb_opportunites: int) -> str:
    """Ce que le message contient, et combien.

    L'ancien objet — « [FALKYE] Résumé du 2026-08-30 au 2026-09-06 » — ne disait
    rien de son contenu. Trois défauts en une ligne : un préfixe entre crochets,
    forme associée aux envois automatisés en masse; le nom de l'expéditeur
    répété alors que l'adresse d'envoi le porte déjà, aux caractères les plus
    visibles d'une boîte de réception; et aucune indication de ce qu'on
    trouvera dedans.

    Le nombre vient en tête parce que c'est lui qui décide si on ouvre
    maintenant ou plus tard.
    """
    semaine = _date_en_francais(summary.periode_debut)
    if nb_opportunites == 0:
        return f"Aucune entreprise repérée — semaine du {semaine}"
    pluriel = "s" if nb_opportunites > 1 else ""
    return f"{nb_opportunites} entreprise{pluriel} repérée{pluriel} — semaine du {semaine}"


def formatter_resume(
    summary: PeriodicSummary,
    notifications: list[Notification],
    registry: Registry | None = None,
    liens_pas_pertinent: dict[int, str] | None = None,
    lien_desabonnement: str | None = None,
    nb_en_attente: int | None = None,
) -> NotificationContent:
    """Le résumé en DEUX formes, construites d'une seule source.

    `nb_en_attente` : le total en attente, plafond compris. Absent, on suppose
    qu'il n'y a pas d'arriéré — le cas des appels qui formatent une liste déjà
    close.

    **Pourquoi une partie HTML alors que le mandat demande « du texte lisible ».**
    Le mandat interdit un GABARIT élaboré, pas une partie HTML — et un envoi de
    diffusion en texte seul est inhabituel, donc un signal négatif de plus pour
    les filtres, sur un domaine qui vient d'encaisser un rebond pour pourriel. Le
    balisage ici est le strict minimum : aucune feuille de style, aucune image,
    aucun tableau, rien qui ne soit déjà dans le texte.

    **Les deux formes disent exactement la même chose**, parce qu'elles sortent
    des mêmes `BlocOpportunite`. Deux rendus écrits séparément divergeraient, et
    une divergence entre deux formes du même message est un mensonge : celui qui
    lit l'une n'aurait pas la même information que celui qui lit l'autre.
    """
    registry = registry or get_registry()
    liens_pas_pertinent = liens_pas_pertinent or {}
    nb_en_attente = len(notifications) if nb_en_attente is None else nb_en_attente

    paragraphes_texte: list[str] = []
    paragraphes_html: list[str] = []

    if not notifications:
        # Formulation à revoir au chantier 14 : la charte (section 16) demande de
        # dire une absence par le travail accompli — combien d'entreprises ont été
        # suivies et qu'aucune n'a franchi le seuil — plutôt que par le vide, qui
        # se lit comme une panne. Ce compte n'existe pas encore; le fabriquer ici
        # serait pire que la phrase neutre. Laissé tel quel, sciemment.
        vide = "Aucune nouvelle entreprise repérée durant cette période."
        paragraphes_texte.append(vide)
        paragraphes_html.append(f"<p>{escape(vide)}</p>")
    else:
        blocs = [
            _bloc_opportunite(n, registry, lien_pas_pertinent=liens_pas_pertinent.get(n.id))
            for n in notifications
        ]
        pluriel = "s" if len(notifications) > 1 else ""
        entete = f"{len(notifications)} entreprise{pluriel} repérée{pluriel} :"
        paragraphes_texte.append(entete)
        paragraphes_html.append(f"<p>{escape(entete)}</p>")

        paragraphes_texte += [_bloc_en_texte(b) for b in blocs]
        paragraphes_html += [_bloc_en_html(b) for b in blocs]

        reste = nb_en_attente - len(notifications)
        if reste > 0:
            # Taire l'arriéré ferait croire que la semaine n'a produit que ces
            # dix-là. Le dire par le FAIT — combien, et qu'elles suivront —
            # plutôt que par une invitation à cliquer quelque part : il n'y a
            # rien à cliquer, et promettre une page qui n'existe pas serait pire
            # que le silence.
            s_reste = "s" if reste > 1 else ""
            arriere = (
                f"{reste} autre{s_reste} opportunité{s_reste} en attente, "
                f"retenue{s_reste} pour les résumés suivants."
            )
            paragraphes_texte.append(arriere)
            paragraphes_html.append(f"<p>{escape(arriere)}</p>")

    entetes = None
    if lien_desabonnement:
        # Le lien visible dans le corps ET l'en-tête : l'un pour la personne qui
        # lit, l'autre pour le bouton natif de sa messagerie (RFC 8058). Les deux
        # mènent à la même URL, donc au même geste.
        libelle = "Ne plus recevoir ces résumés :"
        paragraphes_texte.append(f"---\n{libelle} {lien_desabonnement}")
        cible = escape(lien_desabonnement)
        paragraphes_html.append(
            f"<hr>\n<p>{escape(libelle)} <a href=\"{cible}\">{cible}</a></p>"
        )
        entetes = {
            "List-Unsubscribe": f"<{lien_desabonnement}>",
            # Sans cet en-tête, Gmail et Yahoo n'affichent pas le bouton natif :
            # c'est lui qui déclare que l'URL accepte le POST en un clic.
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        }

    corps_texte = "\n\n".join(paragraphes_texte) + "\n"
    corps_html = (
        "<!doctype html>\n"
        '<html lang="fr">\n<head><meta charset="utf-8"></head>\n<body>\n'
        + "\n".join(paragraphes_html)
        + "\n</body>\n</html>\n"
    )

    return NotificationContent(
        sujet=sujet_du_resume(summary, len(notifications)),
        corps_texte=corps_texte,
        corps_html=corps_html,
        entetes=entetes,
    )


def generer_et_envoyer_resume(
    db_session: Session, profile: Profile, jours: int = 7
) -> PeriodicSummary | None:
    """None si le profil est désabonné OU suspendu — rien n'est généré ni marqué.

    La garde est ICI et pas seulement à la résolution de destinataire : sans
    elle, un résumé serait bien construit, n'aurait aucun canal où aller, ne
    serait donc jamais marqué envoyé, et les opportunités s'accumuleraient
    indéfiniment en attente. Le désabonné coûterait un résumé mort par cycle,
    pour toujours.

    La suspension pour rebonds répétés passe par la même garde, pour la même
    raison — mais elle est réparable : les opportunités restent en attente et
    repartent à sa levée. Le filtre du cycle (falkye/cycle.py::profils_abonnes)
    n'y suffirait pas : `falkye resume envoyer` appelle directement ici, et une
    garde qui ne tient que sur un chemin ne tient pas.
    """
    if profile.desabonne_le is not None or profile.envoi_suspendu_le is not None:
        return None

    registry = get_registry()
    periode_fin = datetime.now(timezone.utc)
    periode_debut = periode_fin - timedelta(days=jours)

    summary, notifications, nb_en_attente = generer_resume(
        db_session, profile, periode_debut, periode_fin
    )

    # Les jetons sont créés AVANT le formatage : ce sont eux qui portent les
    # URL. `url_desabonnement` lève si le point d'entrée n'est pas configuré —
    # aucun résumé ne part alors, ce qui est voulu (voir falkye/liens.py).
    lien_desabo = url_desabonnement(db_session, profile)
    liens_retro = {n.id: url_pas_pertinent(db_session, n) for n in notifications}

    contenu = formatter_resume(
        summary,
        notifications,
        registry,
        liens_pas_pertinent=liens_retro,
        lien_desabonnement=lien_desabo,
        nb_en_attente=nb_en_attente,
    )

    resultats = livrer(db_session, profile, contenu, registry, FORME_RESUME, summary=summary)

    if au_moins_un_succes(resultats):
        summary.envoye_le = datetime.now(timezone.utc)
        for n in notifications:
            n.inclus_dans_resume = True
    # Sinon : `envoye_le` reste NULL et rien n'est marqué. Les opportunités
    # repartiront au prochain résumé. Le PeriodicSummary non envoyé subsiste comme
    # trace de la tentative — c'est ce qui distingue « rien à envoyer » de
    # « l'envoi a échoué ».
    #
    # `envoye_le` ne dit que « le fournisseur a accepté ». Le refus du
    # destinataire arrive plus tard et défait ces deux marquages —
    # falkye/reconciliation.py, appelé au début du cycle suivant.

    db_session.commit()
    return summary
