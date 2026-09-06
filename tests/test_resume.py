"""Tests du résumé groupé — falkye/summary.py.

Ce module n'avait AUCUN test avant le 2026-09-05, et c'est exactement pourquoi
trois défauts y ont survécu jusqu'à la phase 0 du chantier 28 : le lot perdu en
silence, la divergence avec l'autre chemin de livraison, et l'inclusion des
signaux hors profil. Chacun a son test ci-dessous, écrit pour échouer sur la
version d'avant.
"""
from datetime import datetime, timedelta, timezone

import pytest

from falkye.models.company import Company, StatutLegal, StatutResolution, StatutVerification
from falkye.models.notification import (
    ModeUsage,
    NiveauConfiance,
    NiveauPertinence,
    Notification,
    NotificationSignal,
)
from falkye.models.profile import Profile
from falkye.models.signal import Signal
from falkye.notifications.base import DeliveryResult, NotificationChannel
from falkye.registry.loader import NotificationChannelDef
from falkye.summary import generer_et_envoyer_resume, generer_resume, notifications_en_attente


class _CanalEspion(NotificationChannel):
    """Canal qui note ce qu'on lui demande d'envoyer, sans rien envoyer."""

    journal: list = []
    succes: bool = True

    def envoyer(self, destinataire, contenu):
        type(self).journal.append((self.channel_def.id, destinataire, contenu))
        if type(self).succes:
            return DeliveryResult(succes=True)
        return DeliveryResult(succes=False, erreur="panne simulée du fournisseur")


@pytest.fixture()
def espion(monkeypatch):
    _CanalEspion.journal = []
    _CanalEspion.succes = True
    monkeypatch.setattr(
        NotificationChannelDef, "charger_canal", lambda self: _CanalEspion(channel_def=self)
    )
    return _CanalEspion


def _profile(db_session, courriel="alexandre@exemple.com"):
    p = Profile(courriel=courriel, nom="Profil Test")
    db_session.add(p)
    db_session.flush()
    return p


def _company(db_session, nom="Transport Bourassa"):
    c = Company(
        nom_detecte=nom,
        nom_detecte_normalise=nom.lower(),
        ville="Laval",
        statut_legal=StatutLegal.IMMATRICULEE,
        statut_resolution=StatutResolution.RESOLU,
        statut_verification=list(StatutVerification)[0],
    )
    db_session.add(c)
    db_session.flush()
    return c


def _notification(db_session, profile, company, *, hors_profil=False, avec_signal=True):
    n = Notification(
        company_id=company.id,
        profile_id=profile.id,
        mode=ModeUsage.VEILLE_CONTINUE,
        score_confiance=72.0,
        niveau_confiance=NiveauConfiance.ELEVE,
        score_pertinence=80.0,
        niveau_pertinence=NiveauPertinence.AA,
        justification_resumee="résumé de test",
        hors_profil=hors_profil,
    )
    db_session.add(n)
    db_session.flush()
    if avec_signal:
        s = Signal(
            company_id=company.id,
            source_id="seao",
            signal_type_id="appel_offres",
            detected_at=datetime.now(timezone.utc),
        )
        db_session.add(s)
        db_session.flush()
        db_session.add(
            NotificationSignal(
                notification_id=n.id,
                signal_id=s.id,
                justification="contrat public de 45 990 $ obtenu ce mois-ci",
            )
        )
        db_session.flush()
    return n


# --- Défaut 1 : le lot perdu en silence ------------------------------------


def test_envoi_reussi_marque_les_opportunites_comme_livrees(db_session, espion):
    profile = _profile(db_session)
    _notification(db_session, profile, _company(db_session))

    summary = generer_et_envoyer_resume(db_session, profile)

    assert summary.envoye_le is not None
    assert notifications_en_attente(db_session, profile, avant=datetime.now(timezone.utc)) == []


def test_envoi_echoue_ne_marque_rien_et_le_lot_repart_au_cycle_suivant(db_session, espion):
    """Le test central du défaut 1.

    Sur la version d'avant, les notifications étaient marquées AVANT l'envoi et
    sélectionnées par fenêtre de dates : un échec les perdait définitivement.
    """
    profile = _profile(db_session)
    _notification(db_session, profile, _company(db_session))

    espion.succes = False
    premier = generer_et_envoyer_resume(db_session, profile)

    assert premier.envoye_le is None
    en_attente = notifications_en_attente(db_session, profile, avant=datetime.now(timezone.utc))
    assert len(en_attente) == 1, "une opportunité non livrée doit rester en attente"

    # Le cycle suivant, le fournisseur répond de nouveau : le lot sort.
    espion.succes = True
    second = generer_et_envoyer_resume(db_session, profile)

    assert second.envoye_le is not None
    assert len(second.notification_ids) == 1
    assert notifications_en_attente(db_session, profile, avant=datetime.now(timezone.utc)) == []


def test_une_opportunite_plus_vieille_que_la_fenetre_reste_livrable(db_session, espion):
    """La sélection porte sur l'état d'attente, jamais sur une fenêtre basse."""
    profile = _profile(db_session)
    n = _notification(db_session, profile, _company(db_session))
    n.created_at = datetime.now(timezone.utc) - timedelta(days=90)
    db_session.flush()

    summary = generer_et_envoyer_resume(db_session, profile, jours=7)

    assert n.id in summary.notification_ids


# --- Défaut 2 : les deux chemins de livraison ------------------------------


def test_le_resume_ne_sollicite_que_les_canaux_de_forme_resume(db_session, espion):
    """Le canal webhook est actif au registre mais déclaré `unitaire`.

    Sur la version d'avant, il recevait l'adresse courriel du profil comme si
    c'était une URL — une livraison en échec parasite à chaque résumé, et la
    réserve de palier Radar+ contournée.
    """
    profile = _profile(db_session)
    _notification(db_session, profile, _company(db_session))

    generer_et_envoyer_resume(db_session, profile)

    canaux_sollicites = {ligne[0] for ligne in espion.journal}
    assert "webhook_generique" not in canaux_sollicites
    assert canaux_sollicites, "au moins un canal de forme `resume` doit avoir été sollicité"


def test_la_date_denvoi_ne_depend_daucun_identifiant_de_canal_code_en_dur(db_session, espion, registry):
    """Sur la version d'avant, `envoye_le` n'était posée que si l'identifiant du
    canal valait exactement "email" — le nouveau canal aurait cessé de la
    remplir en silence."""
    profile = _profile(db_session)
    _notification(db_session, profile, _company(db_session))

    summary = generer_et_envoyer_resume(db_session, profile)

    identifiants = {c.id for c in registry.canaux_actifs() if c.sert_forme("resume")}
    sollicites = {ligne[0] for ligne in espion.journal}

    assert summary.envoye_le is not None
    assert sollicites, "un canal de forme `resume` doit exister au registre"
    # La garantie qui compte : la date vient du SUCCÈS, pas d'un identifiant.
    # Aucun nom de canal n'est nommé ici — c'était justement le défaut.
    assert sollicites <= identifiants


# --- Défaut 3 (troisième divergence trouvée en réunifiant) -----------------


def test_les_signaux_hors_profil_sont_exclus_du_resume(db_session, espion):
    """Un signal redirigé hors du profil déclaré n'est jamais mélangé aux
    notifications normales (spec section 8bis) — la livraison unitaire l'excluait
    déjà, le résumé non."""
    profile = _profile(db_session)
    company = _company(db_session)
    normale = _notification(db_session, profile, company)
    hors = _notification(db_session, profile, company, hors_profil=True)

    summary = generer_et_envoyer_resume(db_session, profile)

    assert normale.id in summary.notification_ids
    assert hors.id not in summary.notification_ids
    assert hors.inclus_dans_resume is False


# --- Le motif du repérage --------------------------------------------------


def test_le_resume_porte_le_motif_du_reperage_et_jamais_le_nom_de_la_source(db_session, espion, registry):
    """Charte section 16 : un nom d'entreprise sans le motif précis du repérage
    ne vaut pas mieux qu'une liste achetée ailleurs. Et charte section 6 : jamais
    le nom d'une source dans un libellé visible."""
    profile = _profile(db_session)
    _notification(db_session, profile, _company(db_session))

    generer_et_envoyer_resume(db_session, profile)

    corps = espion.journal[0][2].corps_texte
    assert "Transport Bourassa" in corps
    assert "contrat public de 45 990 $ obtenu ce mois-ci" in corps, "le motif doit être livré"
    categorie = registry.signal_types["appel_offres"].nom
    assert categorie in corps
    assert "seao" not in corps.lower(), "aucun libellé ne doit nommer une source"


def test_generer_resume_ne_marque_rien_par_lui_meme(db_session):
    """La génération et la livraison sont deux gestes distincts — c'est ce qui
    permet à un échec de ne rien perdre."""
    profile = _profile(db_session)
    n = _notification(db_session, profile, _company(db_session))
    maintenant = datetime.now(timezone.utc)

    generer_resume(db_session, profile, maintenant - timedelta(days=7), maintenant)

    assert n.inclus_dans_resume is False


# --- L'objet et la partie HTML — 2026-09-06 --------------------------------
#
# ⚠️ Ces deux aspects n'avaient AUCUN test. Changer l'objet du courriel n'a fait
# tomber aucun des 586 tests du dépôt : la suite passait pour la même raison
# qu'elle passait avant le premier envoi réel — parce qu'elle ne regardait pas.
# C'est la règle de la charte (section 11) appliquée à ce qu'on vient de
# toucher, pas seulement à ce qu'on vient d'écrire.

import re
from html import unescape

from falkye.summary import formatter_resume, sujet_du_resume


def _resume_rendu(db_session, nb=1, **kw):
    profile = _profile(db_session)
    for i in range(nb):
        _notification(db_session, profile, _company(db_session, nom=f"Entreprise {i}"))
    maintenant = datetime.now(timezone.utc)
    summary, notifications, total = generer_resume(
        db_session, profile, maintenant - timedelta(days=7), maintenant
    )
    return formatter_resume(summary, notifications, nb_en_attente=total, **kw)


def test_lobjet_dit_le_contenu_et_le_nombre(db_session):
    """L'ancien objet — « [FALKYE] Résumé du 2026-08-30 au 2026-09-06 » — ne
    disait rien de ce qu'il contenait, et son préfixe entre crochets est la
    forme des envois automatisés en masse."""
    contenu = _resume_rendu(db_session, nb=3)

    assert contenu.sujet.startswith("3 entreprises repérées — semaine du ")
    assert "[" not in contenu.sujet
    assert "FALKYE" not in contenu.sujet  # l'adresse d'envoi le porte déjà


def test_lobjet_saccorde_au_singulier(db_session):
    assert _resume_rendu(db_session, nb=1).sujet.startswith("1 entreprise repérée — ")


def test_lobjet_dune_semaine_vide_le_dit(db_session):
    contenu = _resume_rendu(db_session, nb=0)
    assert contenu.sujet.startswith("Aucune entreprise repérée — ")


def test_le_mois_est_en_francais_sans_dependre_de_la_machine(db_session):
    """`locale.setlocale(LC_TIME, "fr_CA")` échoue sur une image sans paquet de
    langue : l'objet basculerait en anglais sur l'hôte de production seulement,
    une différence qu'aucun test ne verrait."""

    class _S:
        periode_debut = datetime(2026, 8, 30, tzinfo=timezone.utc)

    assert sujet_du_resume(_S(), 3) == "3 entreprises repérées — semaine du 30 août 2026"


def test_la_partie_html_existe_et_reste_minimale(db_session):
    """Elle existe parce qu'un envoi de diffusion en texte seul est un signal
    négatif de plus pour les filtres. Elle reste nue parce que le mandat demande
    du texte lisible, pas un gabarit."""
    contenu = _resume_rendu(db_session, nb=2)

    assert contenu.corps_html.startswith("<!doctype html>")
    for interdit in ("<style", "<img", "<table", "style=", "<script"):
        assert interdit not in contenu.corps_html


def _visible(texte: str, *, html: bool = False) -> str:
    """Le texte qu'un lecteur VOIT, réduit à sa substance.

    Comparaison sur le texte CONTINU plutôt que ligne par ligne : `<a>` et
    `<strong>` sont des balises en ligne, et couper à chaque balise scinderait
    une phrase que le lecteur voit d'un seul tenant. Ce serait un faux écart —
    et un test qui échoue sans défaut est aussi nuisible qu'un test qui passe
    sans couverture.

    Deux marques sont retirées des deux côtés : la puce du texte et le tiret de
    séparation, dont l'équivalent HTML (`<hr>`) est un trait sans texte.
    """
    if html:
        # Les attributs (dont `href`) ne sont pas visibles — seul le contenu l'est.
        texte = unescape(re.sub(r"<[^>]+>", " ", texte))
    texte = texte.replace("•", " ").replace("---", " ")
    return " ".join(texte.split())


def test_les_deux_formes_portent_exactement_le_meme_texte(db_session, monkeypatch):
    """L'invariant qui justifie la structure intermédiaire.

    Deux rendus écrits séparément divergent — et une divergence entre deux formes
    du MÊME message est un mensonge : celui qui lit l'une n'a pas la même
    information que celui qui lit l'autre, sans que rien ne le signale.
    """
    monkeypatch.setenv("FALKYE_LIEN_BASE_URL", "https://lien.exemple.test")
    profile = _profile(db_session)
    for i in range(3):
        _notification(db_session, profile, _company(db_session, nom=f"Ex & Co {i}"))
    maintenant = datetime.now(timezone.utc)
    summary, notifications, total = generer_resume(
        db_session, profile, maintenant - timedelta(days=7), maintenant
    )
    contenu = formatter_resume(
        summary,
        notifications,
        liens_pas_pertinent={n.id: f"https://lien.exemple.test/r/j{n.id}" for n in notifications},
        lien_desabonnement="https://lien.exemple.test/d/jeton",
        nb_en_attente=total,
    )

    assert _visible(contenu.corps_texte) == _visible(contenu.corps_html, html=True)


def test_le_html_echappe_les_noms_dentreprise(db_session):
    """« BONNEVILLE & FILS INC. » existe pour de vrai dans les données réelles :
    un `&` non échappé casse le rendu chez certains clients."""
    profile = _profile(db_session)
    _notification(db_session, profile, _company(db_session, nom="Bonneville & Fils <inc.>"))
    maintenant = datetime.now(timezone.utc)
    summary, notifications, total = generer_resume(
        db_session, profile, maintenant - timedelta(days=7), maintenant
    )
    contenu = formatter_resume(summary, notifications, nb_en_attente=total)

    assert "Bonneville &amp; Fils &lt;inc.&gt;" in contenu.corps_html
    assert "<inc.>" not in contenu.corps_html
