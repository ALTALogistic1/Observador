"""Modèles de premier contact contextuels — spec section 4bis (3 fonctionnalités
transversales additionnelles, ajoutée le 2026-09-02) : "génère une amorce de
message adaptée au signal précis détecté (ex. valeur et donneur d'ordre d'un
contrat décroché, ville et date d'un nouvel établissement). S'appuie sur les
données déjà captées par signal (section 7) et l'enrichissement web (section 10).
Se connecte directement au statut 'Premier appel prometteur' du tableau de bord."

Aucune nouvelle donnée collectée — une nouvelle couche de calcul par-dessus
`Signal.champs`, `Signal.valeur_associee` et `Company` (site web, ville), même
principe que falkye/pertinence.py pour le score de pertinence. Dispatch par
`signal_type_id`, même structure que falkye/scoring.py::_SCORERS (une fonction
par type, un texte franc plutôt qu'une formule)."""
from __future__ import annotations

from falkye.models.company import Company
from falkye.models.notification import Notification
from falkye.models.signal import Signal
from falkye.scoring import score_signal_individuel


def _signal_dominant(notification: Notification) -> Signal | None:
    """Le signal le plus fort parmi les contributeurs de cette notification (même
    principe que falkye/scoring.py::calculer_score : le signal dominant porte le
    message, pas une fusion de tous les signaux à la fois — un message de premier
    contact doit rester court et précis, pas une liste)."""
    signaux = [ns.signal for ns in notification.signaux_contributifs]
    if not signaux:
        return None
    return max(signaux, key=score_signal_individuel)


def _amorce_appel_offres(signal: Signal, company: Company) -> str:
    donneur = signal.champs.get("donneur_ordre")
    valeur = signal.valeur_associee
    valeur_txt = f"{valeur:,.0f} $".replace(",", " ") if valeur else "un contrat"
    if donneur:
        return (
            f"J'ai vu que {company.nom_detecte} a récemment décroché {valeur_txt} "
            f"auprès de {donneur} — félicitations pour ce contrat."
        )
    return f"J'ai vu que {company.nom_detecte} a récemment décroché {valeur_txt}."


def _amorce_financement_expansion(signal: Signal, company: Company) -> str:
    programme = signal.champs.get("programme")
    valeur = signal.valeur_associee
    valeur_txt = f"{valeur:,.0f} $".replace(",", " ") if valeur else None
    if programme and valeur_txt:
        return (
            f"J'ai remarqué que {company.nom_detecte} a obtenu {valeur_txt} via "
            f"{programme} — ça a l'air d'un beau projet d'expansion."
        )
    if programme:
        return f"J'ai remarqué que {company.nom_detecte} a bénéficié de {programme}."
    return f"J'ai remarqué un signal de financement récent pour {company.nom_detecte}."


def _amorce_recrutement_massif(signal: Signal, company: Company) -> str:
    titre = signal.titre_ou_description
    nb = signal.champs.get("nombre_postes") or signal.valeur_associee
    if titre:
        return f"J'ai vu que {company.nom_detecte} recrute activement — entre autres pour \"{titre}\"."
    if nb:
        nb_int = int(nb)
        return f"J'ai vu que {company.nom_detecte} a {nb_int} poste(s) ouvert(s) en ce moment."
    return f"J'ai vu que {company.nom_detecte} est en phase de recrutement."


def _amorce_registre_corporatif(signal: Signal, company: Company) -> str:
    type_changement = signal.champs.get("type_changement")
    date_txt = signal.detected_at.strftime("%Y-%m-%d") if signal.detected_at else None
    if type_changement in ("nouvel_etablissement_secondaire", "nouvel_etablissement"):
        ville = company.ville or "un nouveau secteur"
        if date_txt:
            return (
                f"J'ai vu que {company.nom_detecte} a ouvert un nouvel établissement "
                f"à {ville} (le {date_txt})."
            )
        return f"J'ai vu que {company.nom_detecte} a ouvert un nouvel établissement à {ville}."
    if type_changement == "permis_construction":
        nature = signal.champs.get("nature_travaux") or "des travaux"
        adresse = signal.champs.get("adresse_travaux") or company.adresse
        if adresse:
            return f"J'ai vu que {company.nom_detecte} a un permis pour {nature} à {adresse}."
        return f"J'ai vu que {company.nom_detecte} a un permis pour {nature}."
    return f"J'ai vu un changement récent au registre corporatif pour {company.nom_detecte}."


def _amorce_classement_croissance(signal: Signal, company: Company) -> str:
    rang = signal.champs.get("rang")
    taux = signal.champs.get("taux_croissance")
    categorie = signal.champs.get("categorie")
    if rang and categorie:
        return f"Félicitations pour le rang {rang} de {company.nom_detecte} au palmarès {categorie}."
    if taux:
        return f"J'ai vu le taux de croissance de {taux}% de {company.nom_detecte} — impressionnant."
    return f"J'ai vu que {company.nom_detecte} figure dans un classement de croissance récent."


_MODELES = {
    "appel_offres": _amorce_appel_offres,
    "financement_expansion": _amorce_financement_expansion,
    "recrutement_massif": _amorce_recrutement_massif,
    "registre_corporatif": _amorce_registre_corporatif,
    "classement_croissance": _amorce_classement_croissance,
}


def generer_amorce(notification: Notification) -> str:
    """Amorce de message pour LE signal dominant de cette notification. Dégrade
    gracieusement (jamais de valeur inventée pour combler un champ absent,
    principe directeur #1) : chaque fonction de _MODELES retombe sur une phrase
    plus générale si un champ précis manque, et un type de signal sans modèle
    dédié retombe sur une phrase générique référençant seulement le nom de
    l'entreprise et le type de signal."""
    signal = _signal_dominant(notification)
    company = notification.company

    if signal is None:
        return f"Je me permets de vous contacter au sujet de {company.nom_detecte}."

    fonction = _MODELES.get(signal.signal_type_id)
    if fonction is None:
        return f"J'ai remarqué un signal de croissance récent pour {company.nom_detecte}."

    return fonction(signal, company)
