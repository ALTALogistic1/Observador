"""Tests du formatter de notification (falkye/notifications/formatter.py) — le
payload structuré ajouté pour le canal webhook (spec section 4bis, Radar+)."""
from falkye.models.company import Company
from falkye.models.notification import ModeUsage, NiveauConfiance, NiveauPertinence, Notification, NotificationSignal
from falkye.models.signal import Signal
from falkye.notifications.formatter import formatter_notification


def test_formatter_notification_remplit_les_donnees_structurees(registry):
    company = Company(nom_detecte="Entreprise Test", nom_detecte_normalise="entreprise test", neq="1234567890")
    signal = Signal(
        id=1, company_id=1, source_id="seao", signal_type_id="appel_offres",
        source_ref="ref-1", valeur_associee=100000.0, titre_ou_description="Contrat test", champs={},
    )
    n = Notification(
        company_id=1, profile_id=1, mode=ModeUsage.VEILLE_CONTINUE,
        score_confiance=70.0, niveau_confiance=NiveauConfiance.ELEVE,
        score_pertinence=80.0, niveau_pertinence=NiveauPertinence.AA,
        sphere_probable_id="gestion_projet", justification_resumee="test résumé",
    )
    n.company = company
    n.signaux_contributifs = [NotificationSignal(signal=signal, justification="Contrat décroché")]

    contenu = formatter_notification(n, registry)

    assert contenu.donnees_structurees is not None
    d = contenu.donnees_structurees
    assert d["entreprise"]["nom"] == "Entreprise Test"
    assert d["entreprise"]["neq"] == "1234567890"
    assert d["score_confiance"] == 70.0
    assert d["niveau_pertinence"] == "AA"
    assert d["signaux"][0]["source_id"] == "seao"
    assert d["signaux"][0]["justification"] == "Contrat décroché"


def test_formatter_notification_niveau_pertinence_none_pour_historique(registry):
    """Notification antérieure au système de pertinence — NULL, pas une valeur
    inventée (principe directeur #1)."""
    company = Company(nom_detecte="Entreprise Test", nom_detecte_normalise="entreprise test")
    n = Notification(
        company_id=1, profile_id=1, mode=ModeUsage.VEILLE_CONTINUE,
        score_confiance=50.0, niveau_confiance=NiveauConfiance.MOYEN, justification_resumee="test",
    )
    n.company = company
    n.signaux_contributifs = []

    contenu = formatter_notification(n, registry)
    assert contenu.donnees_structurees["niveau_pertinence"] is None


# --- champs_pertinents par signal (spec section 6, "Filtrage par champ,
# contextuel au profil", ajouté le 2026-09-02) ---


def test_formatter_notification_filtre_les_champs_pour_une_sphere_avec_grille(registry):
    """efficacite_energetique × req est déclarée dans registry/champs_pertinents.yaml
    avec [secteur_code, secteur_libelle] — adresse doit être exclue de la vue
    filtrée du payload webhook, sans jamais toucher signal.champs lui-même."""
    company = Company(nom_detecte="Entreprise Test", nom_detecte_normalise="entreprise test")
    signal = Signal(
        id=1, company_id=1, source_id="req", signal_type_id="registre_corporatif",
        source_ref="ref-1", titre_ou_description="Nouvel établissement",
        champs={"secteur_code": "541330", "secteur_libelle": "Fabrication", "adresse": "123 rue Test"},
    )
    n = Notification(
        company_id=1, profile_id=1, mode=ModeUsage.VEILLE_CONTINUE,
        score_confiance=70.0, niveau_confiance=NiveauConfiance.ELEVE,
        score_pertinence=80.0, niveau_pertinence=NiveauPertinence.AA,
        sphere_probable_id="efficacite_energetique", justification_resumee="test résumé",
    )
    n.company = company
    n.signaux_contributifs = [NotificationSignal(signal=signal, justification="Nouvel établissement détecté")]

    contenu = formatter_notification(n, registry)

    champs_filtres = contenu.donnees_structurees["signaux"][0]["champs_pertinents"]
    assert champs_filtres == {"secteur_code": "541330", "secteur_libelle": "Fabrication"}
    # signal.champs lui-même reste intact — seule une vue est filtrée, jamais la donnée captée.
    assert signal.champs == {"secteur_code": "541330", "secteur_libelle": "Fabrication", "adresse": "123 rue Test"}


def test_formatter_notification_ne_filtre_rien_pour_une_sphere_sans_grille(registry):
    """gestion_projet n'a aucune entrée déclarée pour la source req — défaut
    sûr, tous les champs captés restent dans la vue."""
    company = Company(nom_detecte="Entreprise Test", nom_detecte_normalise="entreprise test")
    signal = Signal(
        id=1, company_id=1, source_id="req", signal_type_id="registre_corporatif",
        source_ref="ref-1", titre_ou_description="Nouvel établissement",
        champs={"secteur_code": "541330", "adresse": "123 rue Test"},
    )
    n = Notification(
        company_id=1, profile_id=1, mode=ModeUsage.VEILLE_CONTINUE,
        score_confiance=70.0, niveau_confiance=NiveauConfiance.ELEVE,
        score_pertinence=80.0, niveau_pertinence=NiveauPertinence.AA,
        sphere_probable_id="gestion_projet", justification_resumee="test résumé",
    )
    n.company = company
    n.signaux_contributifs = [NotificationSignal(signal=signal, justification="Nouvel établissement détecté")]

    contenu = formatter_notification(n, registry)

    champs_filtres = contenu.donnees_structurees["signaux"][0]["champs_pertinents"]
    assert champs_filtres == {"secteur_code": "541330", "adresse": "123 rue Test"}
