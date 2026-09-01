"""Interface en ligne de commande — gestion de profils, lancement de scans (veille
continue / recherche ponctuelle, spec section 5), consultation des notifications et
génération du résumé périodique."""
from __future__ import annotations

import click

from falkye.db import get_session, init_db, seed_spheres_from_registry
from falkye.models.profile import Profile, ProfileNeed, Sensibilite, TypeProfil
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
                f"#{p.id} {p.nom} <{p.courriel}> type={p.type_profil.value} "
                f"sensibilite_confiance={p.sensibilite_confiance.value} "
                f"sensibilite_pertinence={p.sensibilite_pertinence.value}"
            )
            for n in p.besoins:
                click.echo(f"    - [{n.type_besoin}] {n.sphere_id}: {n.service_precis} (mots-clés: {n.mots_cles})")
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


if __name__ == "__main__":
    cli()
