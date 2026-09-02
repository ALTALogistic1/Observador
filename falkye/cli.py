"""Interface en ligne de commande — gestion de profils, lancement de scans (veille
continue / recherche ponctuelle, spec section 5), consultation des notifications et
génération du résumé périodique."""
from __future__ import annotations

import click

from falkye.db import get_session, init_db, seed_spheres_from_registry
from falkye.models.profile import PlanTarifaire, Profile, ProfileNeed, Sensibilite, TypeProfil
from falkye.models.sous_compte import RoleSousCompte
from falkye.registry.loader import get_registry


@click.group()
def cli():
    """FALKYE — Repéreur d'entreprises en croissance (15 sources actives, voir `registry sources`)."""


@cli.command("init-db")
def init_db_cmd():
    """Crée les tables et synchronise les sphères de besoin depuis le registre."""
    init_db()
    seed_spheres_from_registry()
    click.echo("Base de données initialisée.")


@cli.group()
def registry():
    """Consulter les registres (sources, signaux, canaux) — spec section 9."""


@registry.command("sources")
def registry_sources():
    reg = get_registry()
    for s in reg.sources.values():
        marqueur = "✅" if s.est_actif else ("💤" if s.statut == "a_developper" else "⛔")
        extra = f" — recherche: {s.lien_recherche}" if s.est_import_manuel and s.lien_recherche else ""
        click.echo(
            f"{marqueur} {s.id:35s} statut={s.statut:15s} signal={','.join(s.signal_associe)}{extra}"
        )


@registry.command("canaux")
def registry_canaux():
    reg = get_registry()
    for c in sorted(reg.notification_channels.values(), key=lambda c: c.priorite):
        marqueur = "✅" if c.est_actif else "💤"
        click.echo(f"{marqueur} #{c.priorite} {c.id:20s} statut={c.statut}")


@cli.group("import-manuel")
def import_manuel_group():
    """Importer un document/résultat obtenu hors ligne (spec section 9, "Import
    manuel de documents sources") — générique pour toute source du registre en
    `methode_acces: import_manuel` (ex. RDPRM)."""


@import_manuel_group.command("lien")
@click.option("--source-id", required=True)
def import_manuel_lien(source_id):
    """Affiche le lien direct de recherche pour cette source, avant d'y aller
    faire la recherche à importer ensuite."""
    reg = get_registry()
    source = reg.sources.get(source_id)
    if source is None:
        raise click.ClickException(f"Source inconnue: {source_id}")
    if not source.est_import_manuel:
        raise click.ClickException(f"{source_id} n'est pas en import manuel (methode_acces={source.methode_acces}).")
    click.echo(source.lien_recherche)


@import_manuel_group.command("inspecter")
@click.option("--source-id", required=True, help="Ex. req")
@click.option(
    "--chemin",
    "chemin_fichier",
    required=True,
    type=click.Path(exists=True),
    help="Fichier téléchargé par vous-même, à inspecter avant un premier import réel",
)
def import_manuel_inspecter(source_id, chemin_fichier):
    """Inspecte la structure réelle d'un fichier importé manuellement (en-têtes
    de chaque CSV s'il y en a plusieurs dans un .zip, plus une ligne
    d'exemple) sans tenter de le parser/importer. À utiliser AVANT un premier
    'import-manuel fichier' sur une source dont la structure interne n'a pas
    encore été confirmée contre de vraies données (ex. REQ, dont le vrai
    fichier contient 6 CSV liés entre eux plutôt qu'un seul plat)."""
    reg = get_registry()
    source_def = reg.sources.get(source_id)
    if source_def is None:
        raise click.ClickException(f"Source inconnue: {source_id!r}")

    connector = source_def.charger_connecteur()
    if connector is None:
        raise click.ClickException(f"Aucun connecteur codé pour {source_id!r}.")

    try:
        infos = connector.inspect_file(chemin_fichier)
    except NotImplementedError as exc:
        raise click.ClickException(str(exc)) from exc

    if not infos:
        click.echo("Aucun fichier CSV trouvé à inspecter.")
        return

    for nom, info in infos.items():
        click.echo(f"\n=== {nom} ({info['taille_decompressee_octets']:,} octets décompressés) ===")
        click.echo(f"Colonnes ({len(info['colonnes'])}): {info['colonnes']}")
        if info["exemple"]:
            click.echo(f"Exemple: {info['exemple']}")


@import_manuel_group.command("ajouter")
@click.option("--source-id", required=True, help="Ex. rdprm")
@click.option("--entreprise", "nom_entreprise", required=True)
@click.option("--valeur", "valeur_associee", type=float, default=None)
@click.option("--description", "titre_ou_description", default=None)
@click.option("--nature-bien", default=None, help="Ex. 'équipement de production' (RDPRM)")
@click.option("--date-evenement", default=None, help="AAAA-MM-JJ — date de l'inscription/du document")
@click.option("--adresse", default=None)
@click.option("--ville", default=None)
@click.option("--region", default=None)
@click.option("--institution", default=None, help="Ex. institution créancière (RDPRM)")
@click.option("--importe-par", default=None, help="Courriel de la personne qui fait l'import")
@click.option("--profile-id", "profile_ids", multiple=True, type=int, help="Traiter immédiatement pour ces profils (défaut: tous)")
def import_manuel_ajouter(
    source_id,
    nom_entreprise,
    valeur_associee,
    titre_ou_description,
    nature_bien,
    date_evenement,
    adresse,
    ville,
    region,
    institution,
    importe_par,
    profile_ids,
):
    from dateutil import parser as dateutil_parser

    from falkye.manual_import import importer_document_manuel, traiter_apres_import

    session = get_session()
    try:
        champs = {}
        if nature_bien:
            champs["nature_bien"] = nature_bien
        if institution:
            champs["institution_creanciere"] = institution

        signal = importer_document_manuel(
            session,
            source_id,
            nom_entreprise,
            valeur_associee=valeur_associee,
            titre_ou_description=titre_ou_description,
            date_evenement=dateutil_parser.parse(date_evenement) if date_evenement else None,
            adresse=adresse,
            ville=ville,
            region=region,
            champs=champs,
            importe_par=importe_par,
        )
        click.echo(f"Signal #{signal.id} importé pour {nom_entreprise} (company_id={signal.company_id}).")

        query = session.query(Profile)
        if profile_ids:
            query = query.filter(Profile.id.in_(profile_ids))
        profiles = query.all()

        notifications = traiter_apres_import(session, signal, profiles)
        click.echo(f"Notifications déclenchées immédiatement : {len(notifications)}")
    finally:
        session.close()


@import_manuel_group.command("fichier")
@click.option("--source-id", required=True, help="Ex. req — doit avoir un connecteur supportant detect_from_file")
@click.option("--chemin", "chemin_fichier", required=True, type=click.Path(exists=True), help="Fichier téléchargé par vous-même (voir 'import-manuel lien')")
@click.option("--limit", "limite_lignes", type=int, default=None, help="Borner le nombre de lignes traitées (test)")
@click.option("--importe-par", default=None, help="Courriel de la personne qui fait l'import")
@click.option("--profile-id", "profile_ids", multiple=True, type=int, help="Retraiter les notifications pour ces profils (défaut: tous)")
@click.option(
    "--reprocess-tout/--pas-de-reprocess",
    default=True,
    help="Après l'import, retraiter TOUTES les entreprises connues (pas seulement celles touchées par ce fichier) — "
    "utile pour un registre comme le REQ dont l'import débloque la résolution NEQ d'entreprises déjà détectées "
    "par d'autres sources. Désactiver pour un import volumineux si vous préférez lancer 'scan veille' séparément.",
)
def import_manuel_fichier(source_id, chemin_fichier, limite_lignes, importe_par, profile_ids, reprocess_tout):
    """Importer un FICHIER COMPLET obtenu hors ligne (ex. le fichier en vrac du
    REQ, téléchargé manuellement — voir 'import-manuel lien --source-id req')
    — spec section 9. Contrairement à 'ajouter' (un document = une
    entreprise), cette commande délègue à
    SourceConnector.detect_from_file du connecteur de la source, qui peut
    produire des signaux pour des milliers d'entreprises en une seule
    importation."""
    from falkye.engine import generer_notifications
    from falkye.manual_import import ImportManuelError, importer_fichier_source
    from falkye.models.notification import ModeUsage

    session = get_session()
    try:
        try:
            signaux = importer_fichier_source(
                session,
                source_id,
                chemin_fichier,
                importe_par=importe_par,
                limite_lignes=limite_lignes,
            )
        except ImportManuelError as exc:
            raise click.ClickException(str(exc)) from exc
        except RuntimeError as exc:
            # Couvre notamment le refus explicite d'un .zip à plusieurs CSV liés
            # (ex. le vrai fichier REQ) tant que la jointure multi-fichiers n'est
            # pas implémentée — voir falkye/sources/req.py:_iter_csv_rows.
            raise click.ClickException(str(exc)) from exc

        click.echo(f"{len(signaux)} signal(aux) importé(s) depuis {chemin_fichier}.")

        query = session.query(Profile)
        if profile_ids:
            query = query.filter(Profile.id.in_(profile_ids))
        profiles = query.all()

        if reprocess_tout:
            notifications = generer_notifications(session, profiles, ModeUsage.VEILLE_CONTINUE)
            click.echo(
                f"Notifications déclenchées (retraitement complet, toutes entreprises) : {len(notifications)}"
            )
    finally:
        session.close()


@cli.group()
def profile():
    """Gestion des profils utilisateur (spec section 4)."""


@profile.command("create")
@click.option("--courriel", required=True)
@click.option("--nom", required=True)
@click.option("--type-profil", type=click.Choice([t.value for t in TypeProfil]), default="fournisseur")
@click.option("--ville", default=None)
@click.option("--region", default=None)
@click.option("--etat-province", default=None)
@click.option("--pays", default="Canada")
@click.option("--rayon-km", type=float, default=None)
@click.option(
    "--sensibilite-confiance",
    type=click.Choice([s.value for s in Sensibilite]),
    default="moyen",
    help="Seuil de notification sur l'axe CONFIANCE (le signal est-il réel et fort)",
)
@click.option(
    "--sensibilite-pertinence",
    type=click.Choice([s.value for s in Sensibilite]),
    default="moyen",
    help="Seuil de notification sur l'axe PERTINENCE (le signal correspond-il à votre profil) — "
    "indépendant du seuil de confiance (spec section 6)",
)
def profile_create(
    courriel, nom, type_profil, ville, region, etat_province, pays, rayon_km,
    sensibilite_confiance, sensibilite_pertinence,
):
    session = get_session()
    try:
        p = Profile(
            courriel=courriel,
            nom=nom,
            type_profil=TypeProfil(type_profil),
            ville=ville,
            region=region,
            etat_province=etat_province,
            pays=pays,
            rayon_km=rayon_km,
            sensibilite_confiance=Sensibilite(sensibilite_confiance),
            sensibilite_pertinence=Sensibilite(sensibilite_pertinence),
        )
        session.add(p)
        session.commit()
        click.echo(f"Profil créé : id={p.id}")
    finally:
        session.close()


@profile.command("add-need")
@click.option("--profile-id", required=True, type=int)
@click.option("--sphere-id", required=True)
@click.option(
    "--service",
    "service_precis",
    required=True,
    help="Texte libre décrivant votre service (ex. 'courtage d'assurance commerciale', 'implantation de systèmes d'inventaire')",
)
@click.option("--mots-cles", default=None, help="Séparés par des virgules")
@click.option("--type-besoin", type=click.Choice(["offre", "besoin"]), default="offre")
def profile_add_need(profile_id, sphere_id, service_precis, mots_cles, type_besoin):
    session = get_session()
    try:
        need = ProfileNeed(
            profile_id=profile_id,
            sphere_id=sphere_id,
            service_precis=service_precis,
            mots_cles=mots_cles,
            type_besoin=type_besoin,
        )
        session.add(need)
        session.commit()
        click.echo(f"Besoin ajouté au profil {profile_id} : id={need.id}")
    finally:
        session.close()


@profile.command("list")
def profile_list():
    session = get_session()
    try:
        for p in session.query(Profile).all():
            click.echo(
                f"#{p.id} {p.nom} <{p.courriel}> type={p.type_profil.value} plan={p.plan.value} "
                f"sensibilite_confiance={p.sensibilite_confiance.value} "
                f"sensibilite_pertinence={p.sensibilite_pertinence.value}"
            )
            for n in p.besoins:
                click.echo(f"    - [{n.type_besoin}] {n.sphere_id}: {n.service_precis} (mots-clés: {n.mots_cles})")
    finally:
        session.close()


@profile.command("set-webhook")
@click.option("--profile-id", required=True, type=int)
@click.option("--url", "webhook_url", required=True)
def profile_set_webhook(profile_id, webhook_url):
    """Configure l'URL de webhook du profil — spec section 4bis, Radar+ "accès
    API/webhook complet". N'a d'effet que pour un profil au plan Radar+
    (falkye/notifications/webhook_channel.py) ; se configure indépendamment du
    plan pour être prêt avant/après une bascule de plan."""
    session = get_session()
    try:
        p = session.get(Profile, profile_id)
        if p is None:
            raise click.ClickException(f"Profil {profile_id} introuvable")
        p.webhook_url = webhook_url
        session.commit()
        click.echo(f"Profil #{p.id} — webhook_url défini (actif seulement si plan=radar_plus).")
    finally:
        session.close()


@cli.group()
def souscompte():
    """Sous-comptes et territoires assignés, avec rôles (spec section 4bis,
    Radar+). Voir falkye/models/sous_compte.py — structure de données
    seulement, ce produit CLI n'a aucun système d'authentification réel."""


@souscompte.command("create")
@click.option("--profile-id", required=True, type=int, help="Compte Radar+ parent.")
@click.option("--courriel", required=True)
@click.option("--nom", required=True)
@click.option("--role", "role_value", type=click.Choice([r.value for r in RoleSousCompte]), default="analyste")
@click.option("--territoire", default=None, help="Ex. une région ou une ville — voir `dashboard voir --sous-compte-id`.")
def souscompte_create(profile_id, courriel, nom, role_value, territoire):
    from falkye.models.sous_compte import SousCompte

    session = get_session()
    try:
        p = session.get(Profile, profile_id)
        if p is None:
            raise click.ClickException(f"Profil {profile_id} introuvable")
        sc = SousCompte(
            profile_id=profile_id, courriel=courriel, nom=nom, role=RoleSousCompte(role_value), territoire=territoire
        )
        session.add(sc)
        session.commit()
        click.echo(f"Sous-compte créé : id={sc.id} (profil parent #{profile_id}, rôle={sc.role.value})")
    finally:
        session.close()


@souscompte.command("list")
@click.option("--profile-id", required=True, type=int)
def souscompte_list(profile_id):
    from falkye.models.sous_compte import SousCompte

    session = get_session()
    try:
        for sc in session.query(SousCompte).filter_by(profile_id=profile_id).all():
            click.echo(
                f"#{sc.id} {sc.nom} <{sc.courriel}> rôle={sc.role.value} "
                f"territoire={sc.territoire or 'n/d'}"
            )
    finally:
        session.close()


@cli.group()
def scan():
    """Lancer un scan (spec section 5)."""


@scan.command("veille")
@click.option("--profile-id", multiple=True, type=int, help="Limiter à ces profils (défaut : tous)")
@click.option("--lookback-days", default=30, help="Fenêtre de détection depuis le dernier scan")
def scan_veille(profile_id, lookback_days):
    from falkye.engine import run_veille_continue

    report = run_veille_continue(profile_ids=list(profile_id) or None, lookback_days=lookback_days)
    _afficher_rapport(report)


@scan.command("ponctuel")
@click.option("--profile-id", required=True, type=int)
@click.option(
    "--lookback-days",
    default=60,
    show_default=True,
    help="Fenêtre de recherche par source. \"Plus large\" (spec section 5) que la veille "
    "continue par défaut (60 jours vs 30), mais pas illimité — un historique complet "
    "peut représenter des centaines de fichiers pour une source comme le SEAO. "
    "Utiliser --historique-complet pour lever cette borne.",
)
@click.option(
    "--historique-complet",
    "historique_complet",
    is_flag=True,
    default=False,
    help="Ignore --lookback-days et remonte tout l'historique disponible de chaque source "
    "(peut représenter plusieurs heures pour une source à large archive, ex. SEAO).",
)
def scan_ponctuel(profile_id, lookback_days, historique_complet):
    from falkye.engine import run_recherche_ponctuelle

    report = run_recherche_ponctuelle(
        profile_id=profile_id, lookback_days=None if historique_complet else lookback_days
    )
    _afficher_rapport(report)


def _afficher_rapport(report):
    click.echo(f"Mode : {report.mode.value}")
    for r in report.ingestion:
        if r.erreur:
            click.echo(f"  ⚠ {r.source_id}: {r.erreur}")
        else:
            click.echo(f"  ✓ {r.source_id}: {r.nb_signaux_nouveaux} nouveaux, {r.nb_signaux_dupliques} déjà connus")
    click.echo(f"Notifications créées : {report.nb_notifications_creees}")


@cli.group()
def notifications():
    """Consulter les notifications générées."""


@notifications.command("list")
@click.option("--profile-id", type=int, default=None)
def notifications_list(profile_id):
    from falkye.models.notification import Notification

    session = get_session()
    try:
        query = session.query(Notification)
        if profile_id:
            query = query.filter(Notification.profile_id == profile_id)
        for n in query.order_by(Notification.created_at.desc()).all():
            nom = n.company.nom_officiel_req or n.company.nom_detecte
            pertinence_txt = n.niveau_pertinence.value if n.niveau_pertinence else "n/d"
            click.echo(
                f"#{n.id} [{n.created_at:%Y-%m-%d %H:%M}] {nom} — "
                f"confiance {n.niveau_confiance.value} ({n.score_confiance}/100), pertinence {pertinence_txt}"
            )
    finally:
        session.close()


@cli.group()
def dashboard():
    """Tableau de bord — cartes de dossiers cumulatifs + statut de suivi (spec
    section 4bis, ajoutée le 2026-09-02). Réservé aux plans Radar et Radar+
    (absent d'Écho)."""


def _verifier_plan_dashboard(profile) -> None:
    from falkye.models.profile import PlanTarifaire

    if profile.plan == PlanTarifaire.ECHO:
        raise click.ClickException(
            f"Tableau de bord réservé aux plans Radar et Radar+ (profil #{profile.id} est au plan Écho) — "
            "voir `falkye billing radar-checkout`."
        )


def _resoudre_sous_compte(session, profile_id, sous_compte_id):
    """Valide qu'un sous-compte appartient bien au profil parent donné — voir
    falkye/models/sous_compte.py pour la limite honnête sur ce que cette
    vérification garantit réellement (pas une authentification)."""
    from falkye.models.sous_compte import SousCompte

    if sous_compte_id is None:
        return None
    sc = session.get(SousCompte, sous_compte_id)
    if sc is None or sc.profile_id != profile_id:
        raise click.ClickException(f"Sous-compte {sous_compte_id} introuvable pour le profil {profile_id}.")
    return sc


@dashboard.command("voir")
@click.option("--profile-id", required=True, type=int)
@click.option(
    "--employes-min", type=int, default=None, help="Filtre par taille d'entreprise estimée (spec section 4bis)."
)
@click.option("--employes-max", type=int, default=None)
@click.option(
    "--sous-compte-id",
    type=int,
    default=None,
    help="Scope les dossiers au territoire assigné à ce sous-compte (spec section 4bis, Radar+).",
)
def dashboard_voir(profile_id, employes_min, employes_max, sous_compte_id):
    """Liste les cartes de dossiers (une par notification) pour ce profil —
    pertinence/confiance, site web et coordonnées, statut de suivi, taille
    d'entreprise estimée."""
    from falkye.models.notification import Notification
    from falkye.models.profile import Profile
    from falkye.taille_entreprise import correspond_au_filtre, estimer_taille

    session = get_session()
    try:
        p = session.get(Profile, profile_id)
        if p is None:
            raise click.ClickException(f"Profil {profile_id} introuvable")
        _verifier_plan_dashboard(p)
        sous_compte = _resoudre_sous_compte(session, profile_id, sous_compte_id)

        notifications_qs = (
            session.query(Notification)
            .filter(Notification.profile_id == profile_id)
            .order_by(Notification.created_at.desc())
            .all()
        )
        notifications_qs = [
            n for n in notifications_qs if correspond_au_filtre(n.company, employes_min, employes_max)
        ]
        if sous_compte is not None and sous_compte.territoire:
            territoire_norm = sous_compte.territoire.strip().lower()
            notifications_qs = [
                n
                for n in notifications_qs
                if (n.company.region or "").strip().lower() == territoire_norm
                or (n.company.ville or "").strip().lower() == territoire_norm
            ]
        if not notifications_qs:
            click.echo("Aucun dossier pour ce profil (avec ce(s) filtre(s), le cas échéant).")
            return

        for n in notifications_qs:
            company = n.company
            nom = company.nom_officiel_req or company.nom_detecte
            pertinence_txt = n.niveau_pertinence.value if n.niveau_pertinence else "n/d"
            statut = n.statut_suivi.nom if n.statut_suivi else "n/d"
            estimation = estimer_taille(company)
            taille_txt = f"{estimation.tranche.value} (~{estimation.volume_postes_estime:.0f} poste(s))" if estimation else "n/d"
            click.echo(f"┌─ #{n.id} {nom}")
            click.echo(f"│  Pertinence {pertinence_txt} · Confiance {n.niveau_confiance.value} ({n.score_confiance}/100)")
            click.echo(f"│  Site web : {company.site_web or 'non disponible'}")
            coordonnees = ", ".join(
                filter(None, [company.telephone, company.courriel_contact])
            ) or "non disponibles"
            click.echo(f"│  Coordonnées : {coordonnees}")
            click.echo(f"│  Taille estimée : {taille_txt}")
            click.echo(f"└─ Statut de suivi : {statut}")
    finally:
        session.close()


@dashboard.command("statuts")
def dashboard_statuts():
    """Liste les statuts de suivi disponibles (registre + statuts personnalisés)."""
    from falkye.models.statut_suivi import StatutSuivi

    session = get_session()
    try:
        for s in session.query(StatutSuivi).all():
            marque = " (personnalisé)" if s.est_personnalise else ""
            click.echo(f"{s.id} — {s.nom}{marque}")
    finally:
        session.close()


@dashboard.command("statut")
@click.option("--notification-id", required=True, type=int)
@click.option("--statut", "statut_id", required=True, help="Voir `dashboard statuts` pour les valeurs possibles.")
@click.option(
    "--sous-compte-id",
    type=int,
    default=None,
    help="Identifie le sous-compte à l'origine du changement (spec section 4bis) — "
    "refusé si son rôle est lecture_seule. Voir falkye/models/sous_compte.py pour "
    "la portée réelle (pas une authentification) de cette vérification.",
)
def dashboard_statut(notification_id, statut_id, sous_compte_id):
    """Change le statut de suivi d'une notification — déclenche automatiquement
    la rétroaction de pertinence si le statut choisi est marqué
    `declenche_retroaction` au registre (ex. "Pas pertinent", spec section 4bis)."""
    from falkye.models.notification import Notification
    from falkye.models.sous_compte import RoleSousCompte
    from falkye.models.statut_suivi import StatutSuivi
    from falkye.registry.loader import get_registry
    from falkye.retroaction import enregistrer_pas_pertinent

    session = get_session()
    try:
        n = session.get(Notification, notification_id)
        if n is None:
            raise click.ClickException(f"Notification {notification_id} introuvable")
        if session.get(StatutSuivi, statut_id) is None:
            raise click.ClickException(f"Statut de suivi inconnu : {statut_id} (voir `dashboard statuts`)")
        sous_compte = _resoudre_sous_compte(session, n.profile_id, sous_compte_id)
        if sous_compte is not None and sous_compte.role == RoleSousCompte.LECTURE_SEULE:
            raise click.ClickException(
                f"Sous-compte {sous_compte_id} en lecture seule — ne peut pas modifier un statut de suivi."
            )

        n.statut_suivi_id = statut_id

        registry = get_registry()
        statut_def = registry.statut_suivi(statut_id)
        if statut_def is not None and statut_def.declenche_retroaction:
            enregistrer_pas_pertinent(session, n)
            click.echo(f"Notification #{n.id} — statut défini à {statut_id} (rétroaction de pertinence appliquée)")
        else:
            click.echo(f"Notification #{n.id} — statut défini à {statut_id}")

        session.commit()
    finally:
        session.close()


@dashboard.command("carte")
@click.option("--profile-id", required=True, type=int)
@click.option("--sortie", "chemin_sortie", required=True, type=click.Path(dir_okay=False))
def dashboard_carte(profile_id, chemin_sortie):
    """Génère une carte géographique interactive (fichier HTML autonome, spec
    section 4bis) des dossiers de ce profil. Géocode les entreprises pas encore
    résolues (falkye/geocoding.py — NON VALIDÉ contre un vrai appel dans cet
    environnement de développement, voir docs/STATUT_RESEAU.md) ; les entreprises
    sans coordonnées disponibles sont simplement absentes de la carte, pas un
    échec de la commande."""
    from falkye.carte import PointCarte, generer_carte_html
    from falkye.geocoding import geocoder_entreprise
    from falkye.models.notification import Notification
    from falkye.models.profile import Profile

    session = get_session()
    try:
        p = session.get(Profile, profile_id)
        if p is None:
            raise click.ClickException(f"Profil {profile_id} introuvable")
        _verifier_plan_dashboard(p)

        notifications_qs = (
            session.query(Notification).filter(Notification.profile_id == profile_id).all()
        )

        points = []
        for n in notifications_qs:
            company = n.company
            if geocoder_entreprise(company):
                points.append(
                    PointCarte(
                        notification_id=n.id,
                        nom_entreprise=company.nom_officiel_req or company.nom_detecte,
                        latitude=company.latitude,
                        longitude=company.longitude,
                        niveau_pertinence=n.niveau_pertinence.value if n.niveau_pertinence else None,
                        niveau_confiance=n.niveau_confiance.value,
                        ville=company.ville,
                    )
                )
        session.commit()  # persiste le cache de géocodage même si la commande échoue plus loin

        html_carte = generer_carte_html(points, titre=f"FALKYE — Carte des prospects (profil #{p.id})")
        with open(chemin_sortie, "w", encoding="utf-8") as f:
            f.write(html_carte)

        click.echo(f"Carte générée : {chemin_sortie} ({len(points)}/{len(notifications_qs)} dossier(s) géocodé(s))")
    finally:
        session.close()


@dashboard.command("modele")
@click.option("--notification-id", required=True, type=int)
def dashboard_modele(notification_id):
    """Génère une amorce de message de premier contact pour cette notification
    (spec section 4bis) — se connecte au statut "Premier appel prometteur"."""
    from falkye.models.notification import Notification
    from falkye.premier_contact import generer_amorce

    session = get_session()
    try:
        n = session.get(Notification, notification_id)
        if n is None:
            raise click.ClickException(f"Notification {notification_id} introuvable")
        click.echo(generer_amorce(n))
    finally:
        session.close()


@cli.group()
def resume():
    """Résumé périodique (spec section 5)."""


@resume.command("envoyer")
@click.option("--profile-id", required=True, type=int)
@click.option("--jours", default=7)
def resume_envoyer(profile_id, jours):
    from falkye.summary import generer_et_envoyer_resume

    session = get_session()
    try:
        p = session.get(Profile, profile_id)
        if p is None:
            raise click.ClickException(f"Profil {profile_id} introuvable")
        summary = generer_et_envoyer_resume(session, p, jours=jours)
        click.echo(f"Résumé #{summary.id} généré : {len(summary.notification_ids)} notification(s) incluse(s)")
    finally:
        session.close()


@cli.group()
def ponderation():
    """Pondération personnalisée du moteur de score de pertinence (spec section
    4bis, Radar+ "pondération du moteur de score personnalisable"). N'a d'effet
    que pour un profil au plan Radar+ (falkye/ponderation.py)."""


@ponderation.command("voir")
@click.option("--profile-id", required=True, type=int)
def ponderation_voir(profile_id):
    from falkye.ponderation import ponderation_pour_profil

    session = get_session()
    try:
        p = session.get(Profile, profile_id)
        if p is None:
            raise click.ClickException(f"Profil {profile_id} introuvable")
        pond = ponderation_pour_profil(session, p)
        click.echo(
            f"Profil #{p.id} (plan={p.plan.value}) — pondération effective "
            f"(personnalisée seulement si plan=radar_plus, sinon toujours la valeur par défaut) :"
        )
        click.echo(f"  base_a={pond.base_a} base_aa={pond.base_aa} base_aaa={pond.base_aaa}")
        click.echo(
            f"  bonus_absence={pond.bonus_absence} bonus_velocite_max={pond.bonus_velocite_max} "
            f"bonus_velocite_par_signal={pond.bonus_velocite_par_signal}"
        )
    finally:
        session.close()


@ponderation.command("definir")
@click.option("--profile-id", required=True, type=int)
@click.option("--base-a", type=float, default=None)
@click.option("--base-aa", type=float, default=None)
@click.option("--base-aaa", type=float, default=None)
@click.option("--bonus-absence", type=float, default=None)
@click.option("--bonus-velocite-max", type=float, default=None)
@click.option("--bonus-velocite-par-signal", type=float, default=None)
def ponderation_definir(
    profile_id, base_a, base_aa, base_aaa, bonus_absence, bonus_velocite_max, bonus_velocite_par_signal
):
    """Définit UN OU PLUSIEURS facteurs (les autres restent inchangés — NULL =
    valeur par défaut de FALKYE, voir falkye/models/ponderation_personnalisee.py).
    N'a d'effet que pour un profil Radar+ ; se configure indépendamment du plan,
    même principe que `profile set-webhook`."""
    from falkye.models.ponderation_personnalisee import PonderationPersonnalisee

    session = get_session()
    try:
        p = session.get(Profile, profile_id)
        if p is None:
            raise click.ClickException(f"Profil {profile_id} introuvable")

        ligne = session.query(PonderationPersonnalisee).filter_by(profile_id=profile_id).one_or_none()
        if ligne is None:
            ligne = PonderationPersonnalisee(profile_id=profile_id)
            session.add(ligne)

        for champ, valeur in [
            ("base_a", base_a), ("base_aa", base_aa), ("base_aaa", base_aaa),
            ("bonus_absence", bonus_absence), ("bonus_velocite_max", bonus_velocite_max),
            ("bonus_velocite_par_signal", bonus_velocite_par_signal),
        ]:
            if valeur is not None:
                setattr(ligne, champ, valeur)

        session.commit()
        click.echo(f"Profil #{p.id} — pondération personnalisée mise à jour (effective seulement si plan=radar_plus).")
    finally:
        session.close()


@ponderation.command("reinitialiser")
@click.option("--profile-id", required=True, type=int)
def ponderation_reinitialiser(profile_id):
    from falkye.models.ponderation_personnalisee import PonderationPersonnalisee

    session = get_session()
    try:
        ligne = session.query(PonderationPersonnalisee).filter_by(profile_id=profile_id).one_or_none()
        if ligne is None:
            click.echo(f"Profil #{profile_id} — aucune pondération personnalisée à réinitialiser.")
            return
        session.delete(ligne)
        session.commit()
        click.echo(f"Profil #{profile_id} — pondération réinitialisée aux valeurs par défaut de FALKYE.")
    finally:
        session.close()


@cli.group()
def billing():
    """Plan tarifaire et paiement intégré Stripe (spec section 9bis, plan Radar).

    NON VALIDÉ contre un vrai compte Stripe dans cet environnement de
    développement (voir falkye/billing/stripe_client.py) — ces commandes sont
    prêtes à l'usage une fois qu'Alexandre a un compte Stripe réel configuré
    (voir .env.example)."""


@billing.command("radar-checkout")
@click.option("--profile-id", required=True, type=int)
def billing_radar_checkout(profile_id):
    """Crée une session Stripe Checkout pour débloquer le plan Radar et affiche son URL."""
    from falkye.billing.stripe_client import creer_session_paiement_radar

    session = get_session()
    try:
        p = session.get(Profile, profile_id)
        if p is None:
            raise click.ClickException(f"Profil {profile_id} introuvable")
        url = creer_session_paiement_radar(p)
        click.echo(url)
    finally:
        session.close()


@billing.command("statut")
@click.option("--profile-id", required=True, type=int)
def billing_statut(profile_id):
    """Affiche le plan effectif du profil et l'état de son abonnement Stripe, s'il existe."""
    from falkye.models.subscription import Subscription

    session = get_session()
    try:
        p = session.get(Profile, profile_id)
        if p is None:
            raise click.ClickException(f"Profil {profile_id} introuvable")
        click.echo(f"Profil #{p.id} — plan={p.plan.value}")
        abo = session.query(Subscription).filter_by(profile_id=profile_id).one_or_none()
        if abo is None:
            click.echo("  Aucun abonnement Stripe enregistré.")
        else:
            click.echo(
                f"  Abonnement : statut={abo.statut} "
                f"stripe_subscription_id={abo.stripe_subscription_id} "
                f"periode_courante_fin={abo.periode_courante_fin}"
            )
    finally:
        session.close()


@billing.command("traiter-webhook")
@click.option(
    "--fichier",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Fichier JSON contenant UN événement Stripe déjà décodé (ex. exporté depuis le "
    "tableau de bord Stripe, section Développeurs > Événements) — même principe que "
    "l'import manuel (spec section 9) appliqué à un webhook plutôt qu'à un document "
    "source, en attendant un point de terminaison HTTP public capable de recevoir de "
    "vrais webhooks Stripe. AUCUNE vérification de signature ici (contrairement à un "
    "vrai webhook HTTP, voir falkye/billing/stripe_client.py:verifier_signature_webhook) "
    "— l'événement est supposé provenir d'une source déjà de confiance (le tableau de "
    "bord authentifié d'Alexandre), pas d'un réseau ouvert.",
)
def billing_traiter_webhook(fichier):
    import json

    from falkye.billing.stripe_client import traiter_evenement_webhook

    with open(fichier, encoding="utf-8") as f:
        event = json.load(f)

    session = get_session()
    try:
        traiter_evenement_webhook(event, session)
        click.echo(f"Événement traité : {event.get('type')}")
    finally:
        session.close()


@billing.command("definir-plan")
@click.option("--profile-id", required=True, type=int)
@click.option("--plan", "plan_value", required=True, type=click.Choice([p.value for p in PlanTarifaire]))
def billing_definir_plan(profile_id, plan_value):
    """Change le plan d'un profil manuellement — pour tester le moteur sans compte
    Stripe réel, ou pour un ajustement administratif ponctuel. Le chemin normal
    reste le webhook Stripe (billing traiter-webhook / un vrai point de terminaison
    HTTP une fois déployé) ; ceci contourne délibérément la facturation."""
    session = get_session()
    try:
        p = session.get(Profile, profile_id)
        if p is None:
            raise click.ClickException(f"Profil {profile_id} introuvable")
        p.plan = PlanTarifaire(plan_value)
        session.commit()
        click.echo(f"Profil #{p.id} — plan défini à {p.plan.value}")
    finally:
        session.close()


if __name__ == "__main__":
    cli()
