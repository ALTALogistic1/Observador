"""Interface en ligne de commande — gestion de profils, lancement de scans (veille
continue / recherche ponctuelle, spec section 5), consultation des notifications et
génération du résumé périodique."""
from __future__ import annotations

import click

from observador.db import get_session, init_db, seed_spheres_from_registry
from observador.models.profile import Profile, ProfileNeed, Sensibilite, TypeProfil
from observador.registry.loader import get_registry


@click.group()
def cli():
    """Repéreur d'entreprises en croissance — Phase 1 (SEAO, RDPRM, REQ, Guichet-Emplois)."""


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
        click.echo(f"{marqueur} {s.id:35s} statut={s.statut:15s} signal={','.join(s.signal_associe)}")


@registry.command("canaux")
def registry_canaux():
    reg = get_registry()
    for c in sorted(reg.notification_channels.values(), key=lambda c: c.priorite):
        marqueur = "✅" if c.est_actif else "💤"
        click.echo(f"{marqueur} #{c.priorite} {c.id:20s} statut={c.statut}")


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
@click.option("--sensibilite", type=click.Choice([s.value for s in Sensibilite]), default="moyen")
def profile_create(courriel, nom, type_profil, ville, region, etat_province, pays, rayon_km, sensibilite):
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
            sensibilite=Sensibilite(sensibilite),
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
            click.echo(f"#{p.id} {p.nom} <{p.courriel}> type={p.type_profil.value} sensibilite={p.sensibilite.value}")
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
    from observador.engine import run_veille_continue

    report = run_veille_continue(profile_ids=list(profile_id) or None, lookback_days=lookback_days)
    _afficher_rapport(report)


@scan.command("ponctuel")
@click.option("--profile-id", required=True, type=int)
def scan_ponctuel(profile_id):
    from observador.engine import run_recherche_ponctuelle

    report = run_recherche_ponctuelle(profile_id=profile_id)
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
    from observador.models.notification import Notification

    session = get_session()
    try:
        query = session.query(Notification)
        if profile_id:
            query = query.filter(Notification.profile_id == profile_id)
        for n in query.order_by(Notification.created_at.desc()).all():
            nom = n.company.nom_officiel_req or n.company.nom_detecte
            click.echo(
                f"#{n.id} [{n.created_at:%Y-%m-%d %H:%M}] {nom} — {n.niveau.value} ({n.score_confiance}/100)"
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
    from observador.summary import generer_et_envoyer_resume

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
