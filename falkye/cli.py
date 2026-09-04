"""Interface en ligne de commande — gestion de profils, lancement de scans (veille
continue / recherche ponctuelle, spec section 5), consultation des notifications et
génération du résumé périodique."""
from __future__ import annotations

import os
from pathlib import Path

import click

from falkye.db import (
    get_session,
    init_db,
    seed_client_cible_synonymes_from_registry,
    seed_clients_cibles_from_registry,
    seed_sphere_synonymes_from_registry,
    seed_spheres_from_registry,
)
from falkye.models.diagnostic_journal import DiagnosticJournal, TypeDiagnostic
from falkye.models.profile import PlanTarifaire, Profile, ProfileNeed, Sensibilite, TypeProfil
from falkye.models.profile_need_client_cible import ProfileNeedClientCible
from falkye.models.profile_need_sphere import ProfileNeedSphere
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
    seed_sphere_synonymes_from_registry()
    seed_clients_cibles_from_registry()
    seed_client_cible_synonymes_from_registry()
    click.echo("Base de données initialisée.")


# --- Authentification réelle par utilisateur (falkye/auth.py, ajoutée le
# 2026-09-02) — voir falkye/models/sous_compte.py pour le contexte complet.
# Le jeton de session BRUT vit UNIQUEMENT dans ce fichier local (jamais en
# base — voir falkye/models/session_auth.py) ; FALKYE_SESSION_FILE permet de
# le déplacer (tests, plusieurs identités sur une même machine).


def _chemin_jeton_local() -> Path:
    override = os.environ.get("FALKYE_SESSION_FILE")
    if override:
        return Path(override)
    return Path.home() / ".falkye" / "session"


def _ecrire_jeton_local(jeton: str) -> None:
    chemin = _chemin_jeton_local()
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(jeton, encoding="utf-8")
    chemin.chmod(0o600)


def _lire_jeton_local() -> str | None:
    chemin = _chemin_jeton_local()
    if not chemin.exists():
        return None
    contenu = chemin.read_text(encoding="utf-8").strip()
    return contenu or None


def _supprimer_jeton_local() -> None:
    chemin = _chemin_jeton_local()
    if chemin.exists():
        chemin.unlink()


def _mode_operateur() -> bool:
    """FALKYE_OPERATOR=1 — bypass intentionnel et documenté pour Alexandre,
    qui doit pouvoir dépanner/administrer n'importe quel profil sans se
    connecter comme chacun de ses clients. Voir falkye/models/sous_compte.py
    pour la limite honnête que ce mode représente : la frontière réelle
    protège les principaux les uns des autres, jamais contre l'opérateur, qui
    a de toute façon accès à la base sous-jacente."""
    return os.environ.get("FALKYE_OPERATOR") == "1"


def _identite_courante(db_session, profile_id: int | None = None, sous_compte_id: int | None = None):
    """Résout l'identité pour une commande "portail" (dashboard, crm,
    souscompte, billing, ponderation, profile set-webhook, notifications,
    resume) — via une session authentifiée (falkye/auth.py), sauf en mode
    opérateur (comportement déclaratif historique préservé pour Alexandre).

    Hors mode opérateur, `profile_id`/`sous_compte_id` — s'ils sont fournis —
    doivent correspondre EXACTEMENT à l'identité de la session active :
    jamais ignorés silencieusement (l'appelant serait alors surpris que sa
    commande agisse sur un autre profil que celui demandé), jamais acceptés
    comme une preuve d'identité alternative (ce serait rouvrir exactement le
    trou que cette fonctionnalité corrige)."""
    from falkye.auth import Principal, resoudre_session

    if _mode_operateur():
        if profile_id is None:
            raise click.ClickException("--profile-id requis en mode opérateur (FALKYE_OPERATOR=1).")
        p = db_session.get(Profile, profile_id)
        if p is None:
            raise click.ClickException(f"Profil {profile_id} introuvable")
        sous_compte = None
        if sous_compte_id is not None:
            from falkye.models.sous_compte import SousCompte

            sous_compte = db_session.get(SousCompte, sous_compte_id)
            if sous_compte is None or sous_compte.profile_id != profile_id:
                raise click.ClickException(f"Sous-compte {sous_compte_id} introuvable pour le profil {profile_id}.")
        return Principal(type="sous_compte" if sous_compte else "profile", profile=p, sous_compte=sous_compte)

    jeton = _lire_jeton_local()
    if jeton is None:
        raise click.ClickException("Non connecté — voir `falkye auth login`.")
    principal = resoudre_session(db_session, jeton)
    if principal is None:
        raise click.ClickException("Session invalide ou expirée — voir `falkye auth login`.")

    if profile_id is not None and profile_id != principal.profile.id:
        raise click.ClickException("Vous ne pouvez agir qu'en votre propre nom (profil de la session active).")
    if sous_compte_id is not None:
        if principal.sous_compte is None or sous_compte_id != principal.sous_compte.id:
            raise click.ClickException(
                "Vous ne pouvez agir qu'en votre propre nom (sous-compte de la session active)."
            )

    return principal


_AIDE_PROFILE_ID_PORTAIL = (
    "Requis en mode opérateur (FALKYE_OPERATOR=1) ; sinon dérivé de la session active "
    "(`falkye auth login`) — doit correspondre à la session s'il est fourni."
)


@cli.group()
def auth():
    """Authentification réelle par utilisateur (mot de passe + session) —
    ajoutée le 2026-09-02, prérequis avant de vendre les rôles/sous-comptes
    Radar+ comme une vraie séparation. Voir falkye/auth.py et falkye/models/
    sous_compte.py pour le contexte complet (ce que ça corrige, et la limite
    honnête qui reste — le mode opérateur, FALKYE_OPERATOR=1)."""


@auth.command("definir-mot-de-passe")
@click.option("--profile-id", type=int, default=None, help="Définit le mot de passe du PROPRIÉTAIRE de ce profil.")
@click.option("--sous-compte-id", type=int, default=None, help="Définit le mot de passe de CE sous-compte.")
@click.option("--mot-de-passe", "mot_de_passe", prompt=True, hide_input=True, confirmation_prompt=True)
def auth_definir_mot_de_passe(profile_id, sous_compte_id, mot_de_passe):
    """Bootstrap OPÉRATEUR (Alexandre uniquement — exige FALKYE_OPERATOR=1) :
    un principal ne peut pas prouver son identité avant d'avoir un mot de
    passe, quelqu'un doit le définir la première fois. Un principal déjà
    connecté change son PROPRE mot de passe avec `auth
    changer-mot-de-passe` plutôt que celle-ci. Choisir exactement un des
    deux : --profile-id (le propriétaire) ou --sous-compte-id."""
    from falkye.auth import definir_mot_de_passe
    from falkye.models.sous_compte import SousCompte

    if not _mode_operateur():
        raise click.ClickException(
            "Réservé au mode opérateur (FALKYE_OPERATOR=1) — un principal déjà connecté utilise "
            "`auth changer-mot-de-passe` pour changer SON PROPRE mot de passe."
        )
    if (profile_id is None) == (sous_compte_id is None):
        raise click.ClickException("Fournir exactement un de --profile-id ou --sous-compte-id.")

    session = get_session()
    try:
        if profile_id is not None:
            principal_obj = session.get(Profile, profile_id)
            if principal_obj is None:
                raise click.ClickException(f"Profil {profile_id} introuvable")
            libelle = f"profil #{profile_id} (propriétaire)"
        else:
            principal_obj = session.get(SousCompte, sous_compte_id)
            if principal_obj is None:
                raise click.ClickException(f"Sous-compte {sous_compte_id} introuvable")
            libelle = f"sous-compte #{sous_compte_id}"

        definir_mot_de_passe(principal_obj, mot_de_passe)
        session.commit()
        click.echo(f"Mot de passe défini pour {libelle}.")
    finally:
        session.close()


@auth.command("login")
@click.option("--courriel", required=True)
@click.option("--mot-de-passe", "mot_de_passe", prompt=True, hide_input=True)
def auth_login(courriel, mot_de_passe):
    """Ouvre une session (30 jours) — jeton écrit dans ~/.falkye/session
    (0600), résolu automatiquement par les commandes "portail" ensuite."""
    from falkye.auth import AuthentificationError, authentifier, creer_session

    session = get_session()
    try:
        try:
            principal = authentifier(session, courriel, mot_de_passe)
        except AuthentificationError as exc:
            raise click.ClickException(str(exc)) from exc
        jeton = creer_session(session, principal)
        _ecrire_jeton_local(jeton)
        click.echo(f"Connecté en tant que {principal.nom_affichage}.")
    finally:
        session.close()


@auth.command("logout")
def auth_logout():
    from falkye.auth import revoquer_session

    jeton = _lire_jeton_local()
    if jeton is None:
        click.echo("Non connecté.")
        return
    session = get_session()
    try:
        revoquer_session(session, jeton)
    finally:
        session.close()
    _supprimer_jeton_local()
    click.echo("Déconnecté.")


@auth.command("whoami")
def auth_whoami():
    from falkye.auth import resoudre_session

    jeton = _lire_jeton_local()
    if jeton is None:
        click.echo("Non connecté.")
        return
    session = get_session()
    try:
        principal = resoudre_session(session, jeton)
        if principal is None:
            click.echo("Session invalide ou expirée — voir `falkye auth login`.")
            return
        click.echo(f"Connecté en tant que {principal.nom_affichage}.")
    finally:
        session.close()


@auth.command("changer-mot-de-passe")
@click.option("--ancien-mot-de-passe", "ancien_mot_de_passe", prompt=True, hide_input=True)
@click.option("--nouveau-mot-de-passe", "nouveau_mot_de_passe", prompt=True, hide_input=True, confirmation_prompt=True)
def auth_changer_mot_de_passe(ancien_mot_de_passe, nouveau_mot_de_passe):
    """Change SON PROPRE mot de passe — exige une session active et l'ancien
    mot de passe (même en mode opérateur : agit toujours sur SA PROPRE
    identité, jamais sur celle d'un tiers — voir `auth
    definir-mot-de-passe` pour ça)."""
    from falkye.auth import definir_mot_de_passe, resoudre_session, verifier_mot_de_passe

    jeton = _lire_jeton_local()
    if jeton is None:
        raise click.ClickException("Non connecté — voir `falkye auth login`.")

    session = get_session()
    try:
        principal = resoudre_session(session, jeton)
        if principal is None:
            raise click.ClickException("Session invalide ou expirée — voir `falkye auth login`.")

        principal_obj = principal.sous_compte or principal.profile
        if not principal_obj.mot_de_passe_hash or not verifier_mot_de_passe(
            principal_obj.mot_de_passe_hash, ancien_mot_de_passe
        ):
            raise click.ClickException("Ancien mot de passe incorrect.")

        definir_mot_de_passe(principal_obj, nouveau_mot_de_passe)
        session.commit()
        click.echo("Mot de passe modifié.")
    finally:
        session.close()


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
@click.option(
    "--usage",
    "usage_precis",
    required=True,
    help="Texte libre décrivant votre usage (ex. 'courtage d'assurance commerciale', "
    "'implantation de systèmes d'inventaire', ou un usage hors vente comme 'suivi de la "
    "croissance manufacturière régionale')",
)
@click.option("--mots-cles", default=None, help="Séparés par des virgules")
@click.option("--type-besoin", type=click.Choice(["offre", "besoin"]), default="offre")
@click.option(
    "--territoire",
    default=None,
    help="Restreint CE besoin à une ville/région précise (spec section 4bis, "
    "'Profils de recherche multiples simultanés') — permet plusieurs combinaisons "
    "usage × territoire sous un seul profil (ex. recrutement-QC et recrutement-ON). "
    "Omis = aucun filtrage géographique pour ce besoin (comportement historique).",
)
def profile_add_need(profile_id, usage_precis, mots_cles, type_besoin, territoire):
    """Crée un besoin SANS sphère liée — utiliser ensuite `falkye profile
    configurer-besoin` (recommandé, assistance IA) ou `falkye profile
    lier-sphere` (manuel) pour le rattacher à une ou plusieurs sphères. Le
    lien sphère↔besoin est désormais plusieurs-à-plusieurs et pondéré (spec
    section 8bis, 2026-09-03) — plus une colonne unique sur ce besoin."""
    session = get_session()
    try:
        need = ProfileNeed(
            profile_id=profile_id,
            usage_precis=usage_precis,
            mots_cles=mots_cles,
            type_besoin=type_besoin,
            territoire=territoire,
        )
        session.add(need)
        session.commit()
        click.echo(
            f"Besoin ajouté au profil {profile_id} : id={need.id} (sans sphère liée pour l'instant — "
            f"voir `falkye profile configurer-besoin` ou `falkye profile lier-sphere`)."
        )
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
                spheres_txt = ", ".join(
                    f"{l.sphere_id}({l.poids:.0f})" for l in sorted(n.spheres_liees, key=lambda l: -l.poids)
                ) or "aucune"
                qui_txt = ", ".join(
                    f"{l.client_cible_id}({l.poids:.0f})"
                    for l in sorted(n.clients_cibles_lies, key=lambda l: -l.poids)
                ) or "non configuré"
                click.echo(
                    f"    - [id={n.id}, {n.type_besoin}] {n.usage_precis} "
                    f"(mots-clés: {n.mots_cles}, territoire: {n.territoire or 'aucun'})\n"
                    f"        sphères : {spheres_txt}\n"
                    f"        clientèle cible : {qui_txt}"
                )
    finally:
        session.close()


def _est_tie_niveau1(suggestions) -> bool:
    """Au moins deux candidats à ÉGALITÉ EXACTE au score maximal (spec section
    8bis) — le déclencheur du départage Niveau 2, distinct d'un échec total."""
    if len(suggestions) < 2:
        return False
    top = suggestions[0].score
    return sum(1 for s in suggestions if s.score == top) >= 2


def _normaliser_poids_niveau1(scores: dict[str, float]) -> dict[str, float]:
    """Met à l'échelle un dict {id: score brut Niveau 1} sur 0-100, le plus
    fort = 100, les autres proportionnels — confirmé par Alexandre :
    "le résultat du Niveau 1... devient directement les poids proposés"."""
    maximum = max(scores.values()) if scores else 0
    if maximum <= 0:
        return {k: 0.0 for k in scores}
    return {k: round(100.0 * v / maximum, 1) for k, v in scores.items()}


def _proposer_liens_spheres(session, profile_obj, texte, niveau2_autorise):
    """Retourne (liens [(sphere_id, poids)], rapport texte) — jamais d'écriture,
    voir docstring de `profile configurer-besoin`."""
    from falkye.assistance_sphere import suggerer_spheres_niveau1
    from falkye.assistance_sphere_ia import (
        AssistanceIANonConfiguree,
        PlanInsuffisantPourAssistanceIA,
        departager_spheres_niveau2,
        suggerer_spheres_niveau2,
    )

    suggestions = suggerer_spheres_niveau1(session, texte)

    if suggestions and _est_tie_niveau1(suggestions):
        if niveau2_autorise:
            try:
                resultat = departager_spheres_niveau2(session, profile_obj, texte, suggestions)
                liens = [(l.sphere_id, l.poids) for l in resultat.liens]
                rapport = "\n".join(
                    f"  - {l.sphere_id} ({l.sphere_nom}) — poids {l.poids:.0f}" for l in resultat.liens
                )
                rapport += f"\n  Niveau 2 (départage d'égalité) — raisonnement : {resultat.raisonnement}"
                return liens, rapport
            except (PlanInsuffisantPourAssistanceIA, AssistanceIANonConfiguree):
                pass  # repli silencieux : poids égaux ci-dessous, pas d'erreur bloquante
        candidats_egalite = [s for s in suggestions if s.score == suggestions[0].score]
        liens = [(s.sphere_id, 100.0) for s in candidats_egalite]
        rapport = "\n".join(
            f"  - {s.sphere_id} ({s.sphere_nom}) — poids 100 (égalité exacte au Niveau 1, "
            f"départage Niveau 2 indisponible pour ce plan)"
            for s in candidats_egalite
        )
        return liens, rapport

    if suggestions:
        bruts = {s.sphere_id: float(s.score) for s in suggestions}
        poids = _normaliser_poids_niveau1(bruts)
        liens = [(s.sphere_id, poids[s.sphere_id]) for s in suggestions]
        rapport = "\n".join(
            f"  - {s.sphere_id} ({s.sphere_nom}) — poids {poids[s.sphere_id]:.0f} "
            f"(mots-clés : {', '.join(s.mots_cles_matches)})"
            for s in suggestions
        )
        return liens, rapport

    if not niveau2_autorise:
        return [], "  Aucune correspondance locale (Niveau 1). Niveau 2 non demandé (--no-niveau2)."
    try:
        resultat = suggerer_spheres_niveau2(session, profile_obj, texte)
    except (PlanInsuffisantPourAssistanceIA, AssistanceIANonConfiguree) as exc:
        return [], f"  Aucune correspondance locale (Niveau 1). Niveau 2 indisponible : {exc}"
    if not resultat.liens:
        return [], (
            f"  Aucune sphère existante ne correspond (Niveau 1 et Niveau 2, confiance="
            f"{resultat.confiance}). Journalisé pour examen (#{resultat.candidat_diagnostic_id}, "
            f"voir `falkye diagnostic lister`).\n  Raisonnement : {resultat.raisonnement}"
        )
    liens = [(l.sphere_id, l.poids) for l in resultat.liens]
    rapport = "\n".join(f"  - {l.sphere_id} ({l.sphere_nom}) — poids {l.poids:.0f} (Niveau 2)" for l in resultat.liens)
    rapport += f"\n  Raisonnement : {resultat.raisonnement}"
    return liens, rapport


def _proposer_liens_client_cible(session, profile_obj, texte, niveau2_autorise):
    """Miroir exact de _proposer_liens_spheres, registre ClientCible."""
    from falkye.assistance_client_cible import suggerer_clients_cibles_niveau1
    from falkye.assistance_client_cible_ia import (
        AssistanceIANonConfiguree,
        PlanInsuffisantPourAssistanceIA,
        departager_clients_cibles_niveau2,
        suggerer_clients_cibles_niveau2,
    )

    suggestions = suggerer_clients_cibles_niveau1(session, texte)

    if suggestions and _est_tie_niveau1(suggestions):
        if niveau2_autorise:
            try:
                resultat = departager_clients_cibles_niveau2(session, profile_obj, texte, suggestions)
                liens = [(l.client_cible_id, l.poids) for l in resultat.liens]
                rapport = "\n".join(
                    f"  - {l.client_cible_id} ({l.client_cible_nom}) — poids {l.poids:.0f}"
                    for l in resultat.liens
                )
                rapport += f"\n  Niveau 2 (départage d'égalité) — raisonnement : {resultat.raisonnement}"
                return liens, rapport
            except (PlanInsuffisantPourAssistanceIA, AssistanceIANonConfiguree):
                pass
        candidats_egalite = [s for s in suggestions if s.score == suggestions[0].score]
        liens = [(s.client_cible_id, 100.0) for s in candidats_egalite]
        rapport = "\n".join(
            f"  - {s.client_cible_id} ({s.client_cible_nom}) — poids 100 (égalité exacte au Niveau 1, "
            f"départage Niveau 2 indisponible pour ce plan)"
            for s in candidats_egalite
        )
        return liens, rapport

    if suggestions:
        bruts = {s.client_cible_id: float(s.score) for s in suggestions}
        poids = _normaliser_poids_niveau1(bruts)
        liens = [(s.client_cible_id, poids[s.client_cible_id]) for s in suggestions]
        rapport = "\n".join(
            f"  - {s.client_cible_id} ({s.client_cible_nom}) — poids {poids[s.client_cible_id]:.0f} "
            f"(mots-clés : {', '.join(s.mots_cles_matches)})"
            for s in suggestions
        )
        return liens, rapport

    if not niveau2_autorise:
        return [], "  Aucune correspondance locale (Niveau 1). Niveau 2 non demandé (--no-niveau2)."
    try:
        resultat = suggerer_clients_cibles_niveau2(session, profile_obj, texte)
    except (PlanInsuffisantPourAssistanceIA, AssistanceIANonConfiguree) as exc:
        return [], f"  Aucune correspondance locale (Niveau 1). Niveau 2 indisponible : {exc}"
    if not resultat.liens:
        return [], (
            f"  Aucune catégorie existante ne correspond, même pas 'aucune restriction' "
            f"(Niveau 1 et Niveau 2, confiance={resultat.confiance}). Journalisé pour examen "
            f"(#{resultat.candidat_diagnostic_id}, voir `falkye diagnostic lister`).\n"
            f"  Raisonnement : {resultat.raisonnement}"
        )
    liens = [(l.client_cible_id, l.poids) for l in resultat.liens]
    rapport = "\n".join(
        f"  - {l.client_cible_id} ({l.client_cible_nom}) — poids {l.poids:.0f} (Niveau 2)"
        for l in resultat.liens
    )
    rapport += f"\n  Raisonnement : {resultat.raisonnement}"
    return liens, rapport


@profile.command("configurer-besoin")
@click.option("--profile-id", type=int, default=None, help=_AIDE_PROFILE_ID_PORTAIL)
@click.option("--usage", "usage_precis", required=True, help="Texte libre décrivant votre service (\"quoi\").")
@click.option(
    "--client-cible",
    "client_cible_texte",
    default=None,
    help="Texte libre décrivant votre clientèle cible (\"qui\") — omis = 'qui' non configuré "
    "pour ce besoin (comportement par défaut sûr : aucun bonus/redirection tant qu'il n'est "
    "pas configuré).",
)
@click.option("--mots-cles", default=None, help="Séparés par des virgules.")
@click.option("--type-besoin", type=click.Choice(["offre", "besoin"]), default="offre")
@click.option("--territoire", default=None, help="Voir `profile add-need --help`.")
@click.option(
    "--confirmer",
    is_flag=True,
    default=False,
    help="Crée le besoin avec la proposition affichée. Sans ce flag : aperçu seulement, "
    "rien n'est écrit.",
)
@click.option(
    "--niveau2/--no-niveau2",
    default=True,
    help="Autoriser l'escalade au Niveau 2 (Claude, Radar/Radar+ seulement) si le Niveau 1 "
    "échoue ou produit une égalité exacte — défaut : autorisé.",
)
def profile_configurer_besoin(
    profile_id, usage_precis, client_cible_texte, mots_cles, type_besoin, territoire, confirmer, niveau2
):
    """Point d'entrée conversationnel UNIQUE pour configurer un besoin (spec
    section 8bis, 2026-09-03) : décrivez votre service et, si vous le
    souhaitez, votre clientèle cible, EN TEXTE LIBRE — l'assistance IA à deux
    paliers propose une configuration complète (sphère(s) pondérée(s), et
    clientèle cible le cas échéant), prête à confirmer en un clic
    (--confirmer). Jamais un écran de pourcentages à manipuler : les poids
    sont calculés pour vous, une donnée de transparence secondaire, pas
    l'interface elle-même. Le raffinement manuel (`profile lier-sphere`,
    `profile lier-client-cible`, `profile definir-sphere-principale`) reste
    disponible après coup, jamais une étape obligatoire.

    Aperçu par défaut (sans --confirmer) : la proposition est recalculée à
    chaque appel, y compris un éventuel appel Niveau 2 — relancer avec
    --confirmer une fois satisfait plutôt que d'itérer, pour éviter un second
    appel IA inutile."""
    session = get_session()
    try:
        profile_obj = _identite_courante(session, profile_id=profile_id).profile

        liens_spheres, rapport_spheres = _proposer_liens_spheres(session, profile_obj, usage_precis, niveau2)
        click.echo('Proposition — sphère(s) ("quoi") :')
        click.echo(rapport_spheres)

        liens_qui: list[tuple[str, float]] = []
        if client_cible_texte:
            liens_qui, rapport_qui = _proposer_liens_client_cible(
                session, profile_obj, client_cible_texte, niveau2
            )
            click.echo('\nProposition — clientèle cible ("qui") :')
            click.echo(rapport_qui)

        if not confirmer:
            click.echo("\nAperçu seulement — ajoutez --confirmer pour créer ce besoin avec cette configuration.")
            return

        if not liens_spheres:
            raise click.ClickException("Aucune sphère retenue — impossible de confirmer sans au moins une sphère.")

        need = ProfileNeed(
            profile_id=profile_obj.id,
            usage_precis=usage_precis,
            mots_cles=mots_cles,
            type_besoin=type_besoin,
            territoire=territoire,
        )
        session.add(need)
        session.flush()
        for sphere_id, poids in liens_spheres:
            session.add(ProfileNeedSphere(profile_need_id=need.id, sphere_id=sphere_id, poids=poids))
        for client_cible_id, poids in liens_qui:
            session.add(ProfileNeedClientCible(profile_need_id=need.id, client_cible_id=client_cible_id, poids=poids))
        session.commit()
        click.echo(
            f"\nBesoin créé : id={need.id}, {len(liens_spheres)} sphère(s) liée(s), "
            f"{len(liens_qui)} client(s) cible(s) lié(s)."
        )
    finally:
        session.close()


@profile.command("lier-sphere")
@click.option("--need-id", required=True, type=int)
@click.option("--sphere-id", required=True)
@click.option("--poids", type=float, default=100.0, show_default=True)
def profile_lier_sphere(need_id, sphere_id, poids):
    """Raffinement manuel — ajoute ou met à jour un lien sphère↔besoin (spec
    section 8bis). Jamais une étape obligatoire : `profile configurer-besoin`
    couvre le parcours normal."""
    session = get_session()
    try:
        need = session.get(ProfileNeed, need_id)
        if need is None:
            raise click.ClickException(f"Besoin {need_id} introuvable.")
        lien = (
            session.query(ProfileNeedSphere)
            .filter_by(profile_need_id=need_id, sphere_id=sphere_id)
            .one_or_none()
        )
        if lien is None:
            lien = ProfileNeedSphere(profile_need_id=need_id, sphere_id=sphere_id, poids=poids)
            session.add(lien)
        else:
            lien.poids = poids
        session.commit()
        click.echo(f"Lien sphère mis à jour : besoin #{need_id} -> {sphere_id} (poids {poids:.0f}).")
    finally:
        session.close()


@profile.command("lier-client-cible")
@click.option("--need-id", required=True, type=int)
@click.option("--client-cible-id", required=True)
@click.option("--poids", type=float, default=100.0, show_default=True)
def profile_lier_client_cible(need_id, client_cible_id, poids):
    """Miroir exact de `profile lier-sphere`, registre ClientCible."""
    session = get_session()
    try:
        need = session.get(ProfileNeed, need_id)
        if need is None:
            raise click.ClickException(f"Besoin {need_id} introuvable.")
        lien = (
            session.query(ProfileNeedClientCible)
            .filter_by(profile_need_id=need_id, client_cible_id=client_cible_id)
            .one_or_none()
        )
        if lien is None:
            lien = ProfileNeedClientCible(profile_need_id=need_id, client_cible_id=client_cible_id, poids=poids)
            session.add(lien)
        else:
            lien.poids = poids
        session.commit()
        click.echo(f"Lien clientèle cible mis à jour : besoin #{need_id} -> {client_cible_id} (poids {poids:.0f}).")
    finally:
        session.close()


@profile.command("definir-sphere-principale")
@click.option("--need-id", required=True, type=int)
@click.option("--sphere-id", required=True, help="La sphère (déjà liée) à promouvoir comme principale.")
def profile_definir_sphere_principale(need_id, sphere_id):
    """Inversion simple d'un départage — jamais besoin de manipuler un
    pourcentage : nomme la sphère voulue, le système ajuste les poids en
    arrière-plan pour qu'elle devienne la plus élevée (spec section 8bis,
    "aussi simplement que possible"). Fonctionne avec deux sphères liées ou
    plus."""
    session = get_session()
    try:
        need = session.get(ProfileNeed, need_id)
        if need is None:
            raise click.ClickException(f"Besoin {need_id} introuvable.")
        lien_vise = next((l for l in need.spheres_liees if l.sphere_id == sphere_id), None)
        if lien_vise is None:
            raise click.ClickException(
                f"{sphere_id} n'est pas liée au besoin #{need_id} — voir `profile lier-sphere` d'abord."
            )
        poids_max_actuel = max(l.poids for l in need.spheres_liees)
        if lien_vise.poids < poids_max_actuel:
            lien_vise.poids = poids_max_actuel + 1.0
        session.commit()
        click.echo(f"{sphere_id} est maintenant la sphère principale du besoin #{need_id} (poids {lien_vise.poids:.0f}).")
    finally:
        session.close()


@profile.command("set-webhook")
@click.option("--profile-id", type=int, default=None, help=_AIDE_PROFILE_ID_PORTAIL)
@click.option("--url", "webhook_url", required=True)
def profile_set_webhook(profile_id, webhook_url):
    """Configure l'URL de webhook du profil — spec section 4bis, Radar+ "accès
    API/webhook complet". N'a d'effet que pour un profil au plan Radar+
    (falkye/notifications/webhook_channel.py) ; se configure indépendamment du
    plan pour être prêt avant/après une bascule de plan."""
    session = get_session()
    try:
        p = _identite_courante(session, profile_id=profile_id).profile
        p.webhook_url = webhook_url
        session.commit()
        click.echo(f"Profil #{p.id} — webhook_url défini (actif seulement si plan=radar_plus).")
    finally:
        session.close()


@cli.group()
def crm():
    """Intégration CRM (HubSpot, Pipedrive) — synchronise les entreprises
    repérées vers le CRM du client (Radar ET Radar+, contrairement au webhook
    générique réservé Radar+ seul — intégration retenue depuis un moment dans
    la liste de fonctionnalités, formellement transmise le 2026-09-02). Jeton
    statique par profil × fournisseur (même mécanique que `profile
    set-webhook`), pas de flux OAuth2 — voir falkye/notifications/crm/base.py."""


@crm.command("fournisseurs")
def crm_fournisseurs():
    """Liste les fournisseurs CRM disponibles — étape de connexion d'une
    source, portail Radar/Radar+ (spec section 9bis, ajoutée le 2026-09-02) :
    jamais un nom de marque seul, toujours le domaine/type ET l'avantage
    concret affichés ensemble, pour que le client choisisse en connaissance
    de cause avant d'appeler `crm connecter`."""
    from falkye.registry.loader import get_registry

    for p in get_registry().fournisseurs_crm_actifs():
        click.echo(f"{p.nom} — {p.domaine_type or 'non documenté'}")
        click.echo(f"  {p.avantage_concret or 'non documenté'}")


@crm.command("connecter")
@click.option("--profile-id", type=int, default=None, help=_AIDE_PROFILE_ID_PORTAIL)
@click.option("--provider", "fournisseur", required=True, type=click.Choice(["hubspot", "pipedrive"]))
@click.option(
    "--jeton", "jeton_api", required=True,
    help="Jeton d'application privée (HubSpot) ou jeton API personnel (Pipedrive).",
)
@click.option(
    "--identifiant-compte", default=None,
    help="Optionnel selon fournisseur (ex. id de pipeline Pipedrive à cibler).",
)
@click.option(
    "--mappage-override-json", "mappage_override_json", default=None,
    help='JSON {champ_falkye: propriété/champ CRM}, par-dessus le mappage par défaut du '
    "fournisseur (registry/crm_providers.yaml) — nécessaire en pratique pour Pipedrive, "
    "dont les clés de champ personnalisé sont propres à chaque compte client (voir notes "
    "du registre). Ex. : '{\"neq\": \"07a1b2c3d4e5\"}'",
)
def crm_connecter(profile_id, fournisseur, jeton_api, identifiant_compte, mappage_override_json):
    """Configure (ou remplace) la connexion CRM d'un profil vers un fournisseur.
    N'a d'effet que pour un profil Radar/Radar+ (gate à l'usage, pas au
    stockage — même principe que `profile set-webhook`)."""
    import json

    from falkye.models.crm_connection import CrmConnection

    mappage_override = None
    if mappage_override_json:
        try:
            mappage_override = json.loads(mappage_override_json)
        except json.JSONDecodeError as exc:
            raise click.ClickException(f"--mappage-override-json invalide : {exc}") from exc

    session = get_session()
    try:
        p = _identite_courante(session, profile_id=profile_id).profile

        connexion = (
            session.query(CrmConnection)
            .filter_by(profile_id=p.id, fournisseur=fournisseur)
            .one_or_none()
        )
        if connexion is None:
            connexion = CrmConnection(profile_id=p.id, fournisseur=fournisseur, jeton_api=jeton_api)
            session.add(connexion)
        else:
            connexion.jeton_api = jeton_api
            connexion.actif = True
        connexion.identifiant_compte = identifiant_compte
        if mappage_override is not None:
            connexion.champs_mappage_override = mappage_override

        session.commit()
        click.echo(f"Connexion {fournisseur} configurée pour le profil {p.id} (id={connexion.id})")
    finally:
        session.close()


@crm.command("mapper-statut")
@click.option("--profile-id", type=int, default=None, help=_AIDE_PROFILE_ID_PORTAIL)
@click.option("--provider", "fournisseur", required=True, type=click.Choice(["hubspot", "pipedrive"]))
@click.option("--statut", "statut_id", required=True, help="Voir `dashboard statuts` pour les valeurs possibles.")
@click.option(
    "--valeur-crm", required=True,
    help="Valeur exacte de l'étape/stage côté CRM (texte propre au compte du client).",
)
def crm_mapper_statut(profile_id, fournisseur, statut_id, valeur_crm):
    """Ajoute (ou remplace) UNE correspondance statut de suivi FALKYE <-> étape
    CRM, pour la connexion déjà configurée (`crm connecter`). Un appel par
    statut à synchroniser — les étapes de pipeline HubSpot/Pipedrive sont
    propres au compte de CHAQUE client, jamais devinées (principe directeur
    #1, "jamais fabriquer une valeur") : sans correspondance explicite pour un
    statut, il est poussé tel quel et un changement lu côté CRM sans
    correspondance connue est ignoré proprement (falkye/crm_sync.py)."""
    from falkye.models.crm_connection import CrmConnection
    from falkye.models.statut_suivi import StatutSuivi

    session = get_session()
    try:
        p = _identite_courante(session, profile_id=profile_id).profile
        connexion = (
            session.query(CrmConnection)
            .filter_by(profile_id=p.id, fournisseur=fournisseur)
            .one_or_none()
        )
        if connexion is None:
            raise click.ClickException(
                f"Aucune connexion {fournisseur} pour le profil {p.id} — voir `crm connecter`."
            )
        if session.get(StatutSuivi, statut_id) is None:
            raise click.ClickException(f"Statut de suivi inconnu : {statut_id} (voir `dashboard statuts`)")

        mapping = dict(connexion.mapping_statuts or {})
        mapping[statut_id] = valeur_crm
        connexion.mapping_statuts = mapping
        session.commit()
        click.echo(f'Correspondance ajoutée : {statut_id} <-> "{valeur_crm}" ({fournisseur}, profil {p.id})')
    finally:
        session.close()


@crm.command("statut")
@click.option(
    "--profile-id", type=int, default=None,
    help="Mode opérateur : limite l'affichage à un profil (tous sinon). Hors mode "
    "opérateur : toujours dérivé de la session active, jamais 'tous les profils'.",
)
def crm_statut(profile_id):
    """Liste l'état de synchronisation CRM — fiches déjà poussées, dernier
    statut de suivi poussé, dernière étape connue côté CRM."""
    from falkye.models.company import Company
    from falkye.models.crm_sync_record import CrmSyncRecord

    session = get_session()
    try:
        if _mode_operateur() and profile_id is None:
            query = session.query(CrmSyncRecord)  # vue globale, réservée au mode opérateur
        else:
            p = _identite_courante(session, profile_id=profile_id).profile
            query = session.query(CrmSyncRecord).filter_by(profile_id=p.id)
        lignes = query.all()
        if not lignes:
            click.echo("Aucune fiche synchronisée.")
            return
        for sr in lignes:
            company = session.get(Company, sr.company_id)
            nom = (company.nom_officiel_req or company.nom_detecte) if company else "?"
            synchronise_le = sr.derniere_synchro_le.isoformat() if sr.derniere_synchro_le else "jamais"
            click.echo(
                f"[{sr.fournisseur}] {nom} — id CRM={sr.crm_object_id}, "
                f"dernier statut poussé={sr.dernier_statut_pousse_id or 'aucun'}, "
                f"dernière étape CRM connue={sr.dernier_stage_crm_connu or 'aucune'}, "
                f"synchronisé le={synchronise_le}"
            )
    finally:
        session.close()


@cli.group()
def souscompte():
    """Sous-comptes et territoires assignés, avec rôles (spec section 4bis,
    Radar+). Voir falkye/models/sous_compte.py — structure de données
    seulement, ce produit CLI n'a aucun système d'authentification réel."""


@souscompte.command("create")
@click.option("--profile-id", type=int, default=None, help=_AIDE_PROFILE_ID_PORTAIL + " Compte Radar+ parent.")
@click.option("--courriel", required=True)
@click.option("--nom", required=True)
@click.option("--role", "role_value", type=click.Choice([r.value for r in RoleSousCompte]), default="analyste")
@click.option("--territoire", default=None, help="Ex. une région ou une ville — voir `dashboard voir --sous-compte-id`.")
def souscompte_create(profile_id, courriel, nom, role_value, territoire):
    """Ajoute un sous-compte — réservé au propriétaire du profil ou à un
    sous-compte de rôle admin (falkye/auth.py::Principal.role)."""
    from falkye.models.sous_compte import SousCompte

    session = get_session()
    try:
        principal = _identite_courante(session, profile_id=profile_id)
        if principal.role != RoleSousCompte.ADMIN:
            raise click.ClickException("Seul le propriétaire du profil ou un sous-compte admin peut en créer un.")
        sc = SousCompte(
            profile_id=principal.profile.id, courriel=courriel, nom=nom,
            role=RoleSousCompte(role_value), territoire=territoire,
        )
        session.add(sc)
        session.commit()
        click.echo(f"Sous-compte créé : id={sc.id} (profil parent #{principal.profile.id}, rôle={sc.role.value})")
    finally:
        session.close()


@souscompte.command("list")
@click.option("--profile-id", type=int, default=None, help=_AIDE_PROFILE_ID_PORTAIL)
def souscompte_list(profile_id):
    from falkye.models.sous_compte import SousCompte

    session = get_session()
    try:
        p = _identite_courante(session, profile_id=profile_id).profile
        for sc in session.query(SousCompte).filter_by(profile_id=p.id).all():
            click.echo(
                f"#{sc.id} {sc.nom} <{sc.courriel}> rôle={sc.role.value} "
                f"territoire={sc.territoire or 'n/d'}"
            )
    finally:
        session.close()


@cli.group()
def diagnostic():
    """Journal de diagnostic généralisé (spec section 8bis, 2026-09-03) —
    remplace `sphere candidats` : candidats de sphère/clientèle cible non
    résolus par le Niveau 2, ET sources de données manquantes trouvées en
    cours de route (falkye/models/diagnostic_journal.py)."""


@diagnostic.command("lister")
@click.option(
    "--type",
    "type_diagnostic",
    type=click.Choice([t.value for t in TypeDiagnostic]),
    default=None,
    help="Filtrer par type (défaut : tous les types).",
)
@click.option(
    "--statut",
    default="a_examiner",
    help="Filtrer par statut (a_examiner par défaut) — passer une chaîne vide pour tous les statuts.",
)
def diagnostic_lister(type_diagnostic, statut):
    """Liste les entrées du journal de diagnostic — cas non résolus par le
    Niveau 2 (JAMAIS auto-résolus, garde-fou non négociable) et sources
    manquantes journalisées manuellement. RÉSERVÉ AU MODE OPÉRATEUR
    (FALKYE_OPERATOR=1) : ce journal traverse tous les profils."""
    if not _mode_operateur():
        raise click.ClickException(
            "Réservé au mode opérateur (FALKYE_OPERATOR=1) — ce journal traverse tous les profils."
        )
    session = get_session()
    try:
        query = session.query(DiagnosticJournal)
        if type_diagnostic:
            query = query.filter(DiagnosticJournal.type_diagnostic == type_diagnostic)
        if statut:
            query = query.filter(DiagnosticJournal.statut == statut)
        entrees = query.order_by(DiagnosticJournal.created_at.desc()).all()
        if not entrees:
            click.echo("Aucune entrée.")
            return
        for e in entrees:
            profil_txt = f"profil=#{e.profile_id}" if e.profile_id is not None else "profil=(aucun)"
            click.echo(
                f"#{e.id} [{e.created_at:%Y-%m-%d %H:%M}] type={e.type_diagnostic.value} "
                f"{profil_txt} statut={e.statut}\n"
                f"    description : {e.texte_description}\n"
                f"    raisonnement niveau 2 : {e.resume_niveau2 or '(aucun)'}"
            )
    finally:
        session.close()


@diagnostic.command("ajouter-source-manquante")
@click.option("--description", required=True, help="Note décrivant la source de données manquante.")
@click.option("--profile-id", type=int, default=None, help="Optionnel — rattache à un profil précis.")
def diagnostic_ajouter_source_manquante(description, profile_id):
    """Journalise manuellement une source de données qui devrait exister mais
    n'existe pas encore dans le registre (ex. un organisme public absent du
    REQ, un fonds de financement découvert en creusant un persona) — jamais
    un appel Niveau 2, une observation produit. RÉSERVÉ AU MODE OPÉRATEUR."""
    if not _mode_operateur():
        raise click.ClickException("Réservé au mode opérateur (FALKYE_OPERATOR=1).")
    session = get_session()
    try:
        entree = DiagnosticJournal(
            type_diagnostic=TypeDiagnostic.SOURCE_MANQUANTE,
            profile_id=profile_id,
            texte_description=description,
            statut="a_examiner",
        )
        session.add(entree)
        session.commit()
        click.echo(f"Source manquante journalisée : #{entree.id}")
    finally:
        session.close()


@diagnostic.command("confirmer-fusion")
@click.option("--id", "diagnostic_id", required=True, type=int)
def diagnostic_confirmer_fusion(diagnostic_id):
    """Confirme manuellement un candidat de fusion d'entreprises (score 90-95,
    spec section 8bis, point 4, 2026-09-03) — applique la fusion (réassigne
    Signal/Notification du candidat vers le principal, supprime le candidat).
    JAMAIS automatique à ce score — décision d'Alexandre : "une fusion
    incorrecte est trop coûteuse à défaire". RÉSERVÉ AU MODE OPÉRATEUR."""
    if not _mode_operateur():
        raise click.ClickException("Réservé au mode opérateur (FALKYE_OPERATOR=1).")
    from falkye.dedup_entreprises import fusionner
    from falkye.models.company import Company

    session = get_session()
    try:
        entree = session.get(DiagnosticJournal, diagnostic_id)
        if entree is None or entree.type_diagnostic != TypeDiagnostic.CANDIDAT_FUSION_ENTREPRISE:
            raise click.ClickException(f"#{diagnostic_id} n'est pas un candidat de fusion d'entreprises.")
        if entree.statut != "a_examiner":
            raise click.ClickException(f"#{diagnostic_id} a déjà été traité (statut={entree.statut}).")
        principal = session.get(Company, entree.company_id_principal)
        candidat = session.get(Company, entree.company_id_candidat)
        if principal is None or candidat is None:
            raise click.ClickException(
                f"#{diagnostic_id} : une des deux entreprises n'existe plus (déjà fusionnée ailleurs?)."
            )
        fusionner(session, principal, candidat)
        entree.statut = "fusionne_confirme"
        session.commit()
        click.echo(f"Fusion confirmée : #{candidat.id} réassigné vers #{principal.id}.")
    finally:
        session.close()


@diagnostic.command("rejeter-fusion")
@click.option("--id", "diagnostic_id", required=True, type=int)
def diagnostic_rejeter_fusion(diagnostic_id):
    """Rejette manuellement un candidat de fusion — les deux fiches restent
    distinctes, aucune donnée touchée. RÉSERVÉ AU MODE OPÉRATEUR."""
    if not _mode_operateur():
        raise click.ClickException("Réservé au mode opérateur (FALKYE_OPERATOR=1).")
    session = get_session()
    try:
        entree = session.get(DiagnosticJournal, diagnostic_id)
        if entree is None or entree.type_diagnostic != TypeDiagnostic.CANDIDAT_FUSION_ENTREPRISE:
            raise click.ClickException(f"#{diagnostic_id} n'est pas un candidat de fusion d'entreprises.")
        entree.statut = "ecarte"
        session.commit()
        click.echo(f"Candidat de fusion #{diagnostic_id} écarté.")
    finally:
        session.close()


@cli.group()
def quarantaine():
    """Quarantaine de diff (Chantier 1, spec section 8bis, 2026-09-03) —
    exécutions suspectes des sources de type `instantane` (falkye/
    diff_engine.py), jamais publiées automatiquement. RÉSERVÉ AU MODE
    OPÉRATEUR : ce journal traverse tout le dossier cumulatif."""


@quarantaine.command("lister")
@click.option(
    "--statut",
    type=click.Choice(["en_attente", "acceptee", "rejetee", "toutes"]),
    default="en_attente",
    help="Filtrer par statut (en_attente par défaut) — 'toutes' pour tout afficher.",
)
def quarantaine_lister(statut):
    if not _mode_operateur():
        raise click.ClickException("Réservé au mode opérateur (FALKYE_OPERATOR=1).")
    from falkye.diff_engine import lister_quarantaines
    from falkye.models.diff_quarantaine import StatutQuarantaine

    session = get_session()
    try:
        filtre = None if statut == "toutes" else StatutQuarantaine(statut)
        entrees = lister_quarantaines(session, filtre)
        if not entrees:
            click.echo("Aucune quarantaine.")
            return
        for q in entrees:
            click.echo(
                f"#{q.id} [{q.created_at:%Y-%m-%d %H:%M}] source={q.source_id} "
                f"motif={q.motif.value} statut={q.statut.value}"
            )
    finally:
        session.close()


@quarantaine.command("inspecter")
@click.option("--id", "quarantaine_id", required=True, type=int)
def quarantaine_inspecter(quarantaine_id):
    if not _mode_operateur():
        raise click.ClickException("Réservé au mode opérateur (FALKYE_OPERATOR=1).")
    from falkye.models.diff_quarantaine import DiffQuarantaine

    session = get_session()
    try:
        q = session.get(DiffQuarantaine, quarantaine_id)
        if q is None:
            raise click.ClickException(f"Quarantaine #{quarantaine_id} introuvable.")
        click.echo(f"#{q.id} source={q.source_id} motif={q.motif.value} statut={q.statut.value}")
        click.echo(f"créée : {q.created_at:%Y-%m-%d %H:%M}")
        click.echo(f"archive brute : {q.chemin_archive or '(aucune)'}")
        click.echo("détail :")
        for cle, valeur in q.detail.items():
            if isinstance(valeur, list) and len(valeur) > 10:
                click.echo(f"  {cle} : {len(valeur)} entrée(s) (tronqué, voir l'archive brute)")
            else:
                click.echo(f"  {cle} : {valeur}")
        if q.levee_par:
            click.echo(f"levée par {q.levee_par} le {q.levee_le:%Y-%m-%d %H:%M} — motif : {q.levee_motif}")
    finally:
        session.close()


@quarantaine.command("lever")
@click.option("--id", "quarantaine_id", required=True, type=int)
@click.option("--decision", type=click.Choice(["acceptee", "rejetee"]), required=True)
@click.option("--motif", required=True, help="Justification de la décision — journalisée.")
@click.option("--qui", required=True, help="Identité de la personne qui lève la quarantaine — journalisée.")
def quarantaine_lever(quarantaine_id, decision, motif, qui):
    """Lève une quarantaine — action explicite et journalisée (qui, quand,
    motif), RÉSERVÉE AU MODE OPÉRATEUR. 'acceptee' applique le diff calculé
    au moment de la quarantaine tel quel (jamais une nouvelle collecte
    contre la source) ; 'rejetee' conserve l'état précédent intact."""
    if not _mode_operateur():
        raise click.ClickException("Réservé au mode opérateur (FALKYE_OPERATOR=1).")
    from falkye.diff_engine import lever_quarantaine as lever_quarantaine_moteur

    identite = qui
    session = get_session()
    try:
        try:
            resultat = lever_quarantaine_moteur(session, quarantaine_id, decision=decision, qui=identite, motif=motif)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        session.commit()
        if decision == "rejetee":
            click.echo(f"Quarantaine #{quarantaine_id} rejetée — état précédent conservé.")
        else:
            click.echo(
                f"Quarantaine #{quarantaine_id} acceptée — "
                f"{len(resultat.resultat.apparitions)} apparition(s), "
                f"{len(resultat.resultat.disparitions)} disparition(s), "
                f"{len(resultat.resultat.modifications)} modification(s) appliquée(s)."
                if resultat.resultat
                else f"Quarantaine #{quarantaine_id} acceptée — nouveau schéma amorcé."
            )
    finally:
        session.close()


@quarantaine.command("proposer-seuils")
@click.option("--source-id", required=True)
def quarantaine_proposer_seuils(source_id):
    """Propose un seuil de quarantaine calibré pour cette source, à partir de
    son historique réel (falkye/diff_engine.py::proposer_seuils) — JAMAIS
    appliqué automatiquement, une simple proposition à examiner et,
    éventuellement, écrire soi-même dans registry/sources.yaml. RÉSERVÉ AU
    MODE OPÉRATEUR."""
    if not _mode_operateur():
        raise click.ClickException("Réservé au mode opérateur (FALKYE_OPERATOR=1).")
    from falkye.diff_engine import NB_RUNS_MINIMUM_AVANT_SEUILS_NORMAUX
    from falkye.diff_engine import proposer_seuils as proposer_seuils_moteur

    session = get_session()
    try:
        proposition = proposer_seuils_moteur(session, source_id)
        if proposition is None:
            click.echo(
                f"Historique insuffisant pour {source_id} — "
                f"attendu au moins {NB_RUNS_MINIMUM_AVANT_SEUILS_NORMAUX} run(s) non-référence."
            )
            return
        s = proposition.seuils_proposes
        click.echo(f"Proposition pour {source_id} (basée sur {proposition.nb_runs_observes} run(s)) :")
        click.echo(f"  apparitions   : pct={s.apparitions.pct}  abs={s.apparitions.abs}")
        click.echo(f"  disparitions  : pct={s.disparitions.pct}  abs={s.disparitions.abs}")
        click.echo(f"  modifications : pct={s.modifications.pct}  abs={s.modifications.abs}")
        click.echo(f"  {proposition.justification}")
        click.echo("  À valider et, si retenue, à écrire soi-même dans registry/sources.yaml — jamais automatique.")
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
    "peut représenter des centaines de fichiers pour une source à grand volume. "
    "Utiliser --historique-complet pour lever cette borne.",
)
@click.option(
    "--historique-complet",
    "historique_complet",
    is_flag=True,
    default=False,
    help="Ignore --lookback-days et remonte tout l'historique disponible de chaque source "
    "(peut représenter plusieurs heures pour une source à large archive).",
)
def scan_ponctuel(profile_id, lookback_days, historique_complet):
    from falkye.engine import run_recherche_ponctuelle

    report = run_recherche_ponctuelle(
        profile_id=profile_id, lookback_days=None if historique_complet else lookback_days
    )
    _afficher_rapport(report)


@scan.command("detecter-expansions")
def scan_detecter_expansions():
    """Rattrapage manuel de la détection d'expansion inter-provinciale (spec
    Radar+, point 7) — balaye TOUT le dossier cumulatif plutôt que la passe
    incrémentale déjà greffée sur `scan veille`. Utile après l'activation
    initiale du mécanisme ou l'ajout d'une nouvelle source à
    SourceDef.province_code. Idempotent : ne recrée jamais un lien déjà
    enregistré."""
    from falkye.db import get_session
    from falkye.expansion_interprovinciale import detecter_expansions
    from falkye.registry.loader import get_registry

    session = get_session()
    try:
        registry = get_registry()
        nouveaux = detecter_expansions(session, registry)
        session.commit()
        click.echo(f"Liens inter-provinciaux détectés : {len(nouveaux)}")
        for lien in nouveaux:
            click.echo(
                f"  #{lien.id} : company #{lien.company_id_a} ({lien.province_a}) "
                f"<-> company #{lien.company_id_b} ({lien.province_b}) — "
                f"score {lien.score_correspondance:.0f}"
            )
    finally:
        session.close()


@scan.command("detecter-doublons")
def scan_detecter_doublons():
    """Rattrapage manuel de détection/fusion de doublons d'entreprises sans
    NEQ (spec section 8bis, point 4, 2026-09-03) — balaye tout le dossier
    cumulatif. RÉSERVÉ AU MODE OPÉRATEUR : contrairement à `scan
    detecter-expansions` (jamais destructif, ne fait qu'ajouter un lien),
    cette commande peut FUSIONNER — et donc supprimer — de vraies fiches
    Company à score >=95 (voir falkye/dedup_entreprises.py). Jamais greffée
    automatiquement sur `scan veille`, contrairement à la détection
    d'expansion inter-provinciale — décision délibérée compte tenu du
    caractère irréversible d'une fusion, même à un seuil élevé. Idempotent :
    une paire déjà fusionnée ou déjà journalisée n'est jamais retraitée."""
    if not _mode_operateur():
        raise click.ClickException(
            "Réservé au mode opérateur (FALKYE_OPERATOR=1) — action potentiellement destructive."
        )
    from falkye.dedup_entreprises import detecter_doublons

    session = get_session()
    try:
        rapport = detecter_doublons(session)
        session.commit()
        click.echo(f"Fusions automatiques (score >=95) : {rapport.nb_fusions_auto}")
        click.echo(
            f"Candidats journalisés pour examen manuel (score 90-95) : {rapport.nb_candidats_journalises}"
        )
        if rapport.nb_candidats_journalises:
            click.echo("Voir `falkye diagnostic lister --type candidat_fusion_entreprise`.")
    finally:
        session.close()


def _categorie_pour_source(registry, source_id):
    """Catégorie de signal neutre pour une source — JAMAIS le nom de la source
    elle-même dans un rapport de scan (libre-service, `scan veille`/`scan
    ponctuel`) — principe de neutralité des libellés (charte, section 6,
    élargie le 2026-09-03). Chaque source active du registre n'est associée
    qu'à UNE seule catégorie (`SourceDef.signal_associe`, vérifié le
    2026-09-03) — pas d'ambiguïté à trancher ici."""
    source_def = registry.sources.get(source_id)
    if not source_def or not source_def.signal_associe:
        return source_id  # repli honnête si le registre ne sait pas classer — rarissime
    signal_type = registry.signal_types.get(source_def.signal_associe[0])
    return signal_type.nom if signal_type else source_def.signal_associe[0]


def _afficher_rapport(report):
    click.echo(f"Mode : {report.mode.value}")
    registry = get_registry()
    # Agrégé par CATÉGORIE de signal, jamais par source précise (voir
    # _categorie_pour_source) — le détail par source individuelle (y compris les
    # messages d'erreur, potentiellement révélateurs) reste consultable via
    # SourceRunLog, en mode opérateur seulement.
    par_categorie: dict[str, dict] = {}
    for r in report.ingestion:
        entree = par_categorie.setdefault(
            _categorie_pour_source(registry, r.source_id),
            {"nouveaux": 0, "dupliques": 0, "erreurs": 0},
        )
        if r.erreur:
            entree["erreurs"] += 1
        else:
            entree["nouveaux"] += r.nb_signaux_nouveaux
            entree["dupliques"] += r.nb_signaux_dupliques
    for categorie, compte in sorted(par_categorie.items()):
        marqueur = "⚠" if compte["erreurs"] else "✓"
        detail = f"{compte['nouveaux']} nouveaux, {compte['dupliques']} déjà connus"
        if compte["erreurs"]:
            detail += f" ({compte['erreurs']} source(s) en erreur — détail : mode opérateur)"
        click.echo(f"  {marqueur} {categorie}: {detail}")
    click.echo(f"Notifications créées : {report.nb_notifications_creees}")
    if report.nb_statuts_crm_synchronises:
        click.echo(f"Statuts synchronisés depuis un CRM : {report.nb_statuts_crm_synchronises}")
    if report.nb_liens_interprovinciaux_detectes:
        click.echo(f"Liens inter-provinciaux détectés : {report.nb_liens_interprovinciaux_detectes}")


@cli.group()
def notifications():
    """Consulter les notifications générées."""


@notifications.command("list")
@click.option(
    "--profile-id", type=int, default=None,
    help="Mode opérateur : limite l'affichage à un profil (tous sinon). Hors mode "
    "opérateur : toujours dérivé de la session active, jamais 'tous les profils'.",
)
def notifications_list(profile_id):
    from falkye.models.notification import Notification

    session = get_session()
    try:
        if _mode_operateur() and profile_id is None:
            query = session.query(Notification)  # vue globale, réservée au mode opérateur
        else:
            p = _identite_courante(session, profile_id=profile_id).profile
            query = session.query(Notification).filter(Notification.profile_id == p.id)
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


def _resoudre_scope_territoire(session, principal, sous_compte_id_demande):
    """Détermine le sous-compte dont le territoire doit scoper `dashboard
    voir` — PAS une vérification d'identité (voir `_identite_courante`, déjà
    passée à ce stade), un filtre de LECTURE. Le propriétaire ou un
    sous-compte admin peut prévisualiser le territoire d'un collègue
    (`--sous-compte-id` explicite, ex. pour du support) ; un sous-compte non
    admin reste TOUJOURS scopé à son propre territoire, sans pouvoir en
    demander un autre — sinon un sous-compte à territoire restreint pourrait
    simplement élargir sa propre vue en passant un autre id."""
    from falkye.models.sous_compte import SousCompte

    if sous_compte_id_demande is not None:
        if principal.role != RoleSousCompte.ADMIN:
            raise click.ClickException(
                "Seul le propriétaire du profil ou un sous-compte admin peut prévisualiser "
                "le territoire d'un autre sous-compte."
            )
        sc = session.get(SousCompte, sous_compte_id_demande)
        if sc is None or sc.profile_id != principal.profile.id:
            raise click.ClickException(f"Sous-compte {sous_compte_id_demande} introuvable pour ce profil.")
        return sc

    # Pas de demande explicite : un sous-compte non admin est auto-scopé à
    # son propre territoire ; le propriétaire/un admin voit tout par défaut.
    if principal.sous_compte is not None and principal.role != RoleSousCompte.ADMIN:
        return principal.sous_compte
    return None


@dashboard.command("voir")
@click.option("--profile-id", type=int, default=None, help=_AIDE_PROFILE_ID_PORTAIL)
@click.option(
    "--employes-min", type=int, default=None, help="Filtre par taille d'entreprise estimée (spec section 4bis)."
)
@click.option("--employes-max", type=int, default=None)
@click.option(
    "--sous-compte-id",
    type=int,
    default=None,
    help="Prévisualise le territoire assigné à CE sous-compte (spec section 4bis, Radar+) — "
    "réservé au propriétaire/un admin ; un sous-compte non admin est de toute façon "
    "auto-scopé à son propre territoire sans avoir besoin de cette option.",
)
@click.option(
    "--usage",
    "usage_filtre",
    default=None,
    help="Filtre par usage précis (spec section 4bis, 'Profils de recherche multiples "
    "simultanés') — sous-chaîne insensible à la casse de ProfileNeed.usage_precis.",
)
@click.option(
    "--territoire",
    "territoire_filtre",
    default=None,
    help="Filtre par territoire de la combinaison sphère/usage × territoire à l'origine "
    "de la notification (ProfileNeed.territoire) — distinct de --sous-compte-id, qui "
    "scope plutôt par le territoire assigné AU VIEWER.",
)
def dashboard_voir(profile_id, employes_min, employes_max, sous_compte_id, usage_filtre, territoire_filtre):
    """Liste les cartes de dossiers (une par notification) pour ce profil —
    pertinence/confiance, site web et coordonnées, statut de suivi, taille
    d'entreprise estimée."""
    from falkye.models.notification import Notification
    from falkye.taille_entreprise import correspond_au_filtre, estimer_taille

    session = get_session()
    try:
        principal = _identite_courante(session, profile_id=profile_id)
        p = principal.profile
        _verifier_plan_dashboard(p)
        sous_compte = _resoudre_scope_territoire(session, principal, sous_compte_id)

        notifications_qs = (
            session.query(Notification)
            .filter(Notification.profile_id == p.id)
            .order_by(Notification.created_at.desc())
            .all()
        )
        notifications_qs = [
            n for n in notifications_qs if correspond_au_filtre(n.company, employes_min, employes_max)
        ]
        if usage_filtre:
            u = usage_filtre.strip().lower()
            notifications_qs = [
                n for n in notifications_qs if n.profile_need and u in (n.profile_need.usage_precis or "").lower()
            ]
        if territoire_filtre:
            t = territoire_filtre.strip().lower()
            notifications_qs = [
                n
                for n in notifications_qs
                if n.profile_need and (n.profile_need.territoire or "").strip().lower() == t
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

        # Canal "hors profil déclaré" (spec section 8bis, 2026-09-03, réservé
        # Radar+) — JAMAIS mélangé aux notifications normales : section
        # séparée, affichée après, explicitement étiquetée. Ces lignes
        # n'existent de toute façon que pour un profil Radar+ (gating fait
        # dans falkye/engine.py), le filtrage ci-dessous est donc purement
        # un tri d'affichage, pas un gate additionnel.
        notifications_normales = [n for n in notifications_qs if not n.hors_profil]
        notifications_hors_profil = [n for n in notifications_qs if n.hors_profil]

        for n in notifications_normales:
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
            if n.profile_need is not None:
                click.echo(
                    f"│  Combinaison : {n.profile_need.usage_precis or 'n/d'} "
                    f"(territoire: {n.profile_need.territoire or 'aucun'})"
                )
            click.echo(f"└─ Statut de suivi : {statut}")

        if notifications_hors_profil:
            click.echo("")
            click.echo(
                "── Hors profil déclaré — correspond à votre sphère mais pas à la "
                "clientèle cible que vous avez déclarée, à valider ──"
            )
            for n in notifications_hors_profil:
                company = n.company
                nom = company.nom_officiel_req or company.nom_detecte
                click.echo(f"┌─ #{n.id} {nom}")
                click.echo(
                    f"│  Pertinence {n.niveau_pertinence.value if n.niveau_pertinence else 'n/d'} · "
                    f"Confiance {n.niveau_confiance.value} ({n.score_confiance}/100)"
                )
                click.echo(f"└─ {n.justification_resumee}")
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
def dashboard_statut(notification_id, statut_id):
    """Change le statut de suivi d'une notification — déclenche automatiquement
    la rétroaction de pertinence si le statut choisi est marqué
    `declenche_retroaction` au registre (ex. "Pas pertinent", spec section 4bis).

    L'auteur du changement est désormais l'identité VÉRIFIÉE de la session
    active (falkye/auth.py), refusé si son rôle est lecture_seule — plus de
    `--sous-compte-id` déclaratif (voir falkye/models/sous_compte.py pour ce
    que ça corrige)."""
    from falkye.models.notification import Notification
    from falkye.models.statut_suivi import StatutSuivi
    from falkye.registry.loader import get_registry
    from falkye.statut_suivi import appliquer_statut

    session = get_session()
    try:
        n = session.get(Notification, notification_id)
        if n is None:
            raise click.ClickException(f"Notification {notification_id} introuvable")
        if session.get(StatutSuivi, statut_id) is None:
            raise click.ClickException(f"Statut de suivi inconnu : {statut_id} (voir `dashboard statuts`)")

        principal = _identite_courante(session, profile_id=n.profile_id)
        if principal.role == RoleSousCompte.LECTURE_SEULE:
            raise click.ClickException("Votre rôle (lecture_seule) ne peut pas modifier un statut de suivi.")

        retroaction_appliquee = appliquer_statut(session, n, statut_id, get_registry())
        if retroaction_appliquee:
            click.echo(f"Notification #{n.id} — statut défini à {statut_id} (rétroaction de pertinence appliquée)")
        else:
            click.echo(f"Notification #{n.id} — statut défini à {statut_id}")

        session.commit()
    finally:
        session.close()


@dashboard.command("synthese")
@click.option("--profile-id", type=int, default=None, help=_AIDE_PROFILE_ID_PORTAIL)
@click.option("--jours", type=int, default=90, help="Fenêtre de temps (défaut 90 jours, environ un trimestre).")
@click.option(
    "--territoire",
    "territoire_filtre",
    default=None,
    help="Limite la synthèse aux notifications dont la combinaison sphère/usage × "
    "territoire (ProfileNeed.territoire) correspond exactement.",
)
@click.option(
    "--secteur-detail",
    "secteur_detail",
    is_flag=True,
    default=False,
    help="Affiche aussi les libellés bruts (granularité d'origine) derrière le "
    "regroupement grossier — utile pour inspecter ce qui tombe dans « (non classé) ».",
)
def dashboard_synthese(profile_id, jours, territoire_filtre, secteur_detail):
    """Vue de synthèse agrégée (spec section 4bis) — "X entreprises détectées,
    réparties par secteur" plutôt que les prospects un à un. Utile pour la
    reddition de comptes (ex. développement économique régional).

    La répartition par secteur est un REGROUPEMENT GROSSIER par mots-clés
    (falkye/synthese.py, `registry/secteurs_grossiers.yaml`) — solution
    intermédiaire, PAS un vrai SCIAN/NAICS ; voir docs/ARCHITECTURE.md."""
    from datetime import datetime, timedelta, timezone

    from falkye.assistance_client_cible import suggerer_clients_cibles_niveau1_pour_company
    from falkye.models.notification import Notification
    from falkye.registry.loader import get_registry
    from falkye.synthese import generer_synthese

    session = get_session()
    try:
        p = _identite_courante(session, profile_id=profile_id).profile
        _verifier_plan_dashboard(p)

        depuis = datetime.now(timezone.utc) - timedelta(days=jours)
        notifications_qs = (
            session.query(Notification)
            .filter(Notification.profile_id == p.id, Notification.created_at >= depuis)
            .all()
        )
        if territoire_filtre:
            t = territoire_filtre.strip().lower()
            notifications_qs = [
                n
                for n in notifications_qs
                if n.profile_need and (n.profile_need.territoire or "").strip().lower() == t
            ]

        # Classification "qui" (spec section 8bis, point 3, 2026-09-03) — résolue
        # ICI (accès DB requis pour ClientCibleSynonyme), jamais dans
        # falkye/synthese.py qui reste pur. Une seule classification par
        # entreprise distincte, pas par notification.
        classifications_qui: dict[int, str | None] = {}
        for n in notifications_qs:
            if n.company_id in classifications_qui:
                continue
            suggestions = suggerer_clients_cibles_niveau1_pour_company(session, n.company)
            classifications_qui[n.company_id] = suggestions[0].client_cible_nom if suggestions else None

        synthese = generer_synthese(notifications_qs, get_registry(), classifications_qui)

        sous_titre = f", territoire « {territoire_filtre} »" if territoire_filtre else ""
        click.echo(f"Synthèse — profil #{p.id}, {jours} derniers jours{sous_titre}")
        click.echo(f"{synthese.nb_entreprises} entreprise(s) en croissance détectée(s)\n")

        click.echo("Répartition par secteur d'activité (regroupement grossier) :")
        for secteur, n in synthese.par_secteur.most_common():
            click.echo(f"  {secteur} : {n}")
        if secteur_detail:
            click.echo("\nDétail par libellé brut :")
            for secteur, n in synthese.par_secteur_detail.most_common():
                click.echo(f"  {secteur} : {n}")

        click.echo("\nRépartition par clientèle cible (dimension complémentaire) :")
        for categorie, n in synthese.par_client_cible.most_common():
            click.echo(f"  {categorie} : {n}")

        click.echo("\nRépartition par niveau de pertinence :")
        for niveau, n in synthese.par_niveau_pertinence.most_common():
            click.echo(f"  {niveau} : {n}")

        if not territoire_filtre:
            click.echo("\nRépartition par territoire :")
            for territoire, n in synthese.par_territoire.most_common():
                click.echo(f"  {territoire} : {n}")
    finally:
        session.close()


@dashboard.command("carte")
@click.option("--profile-id", type=int, default=None, help=_AIDE_PROFILE_ID_PORTAIL)
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

    session = get_session()
    try:
        p = _identite_courante(session, profile_id=profile_id).profile
        _verifier_plan_dashboard(p)

        notifications_qs = (
            session.query(Notification).filter(Notification.profile_id == p.id).all()
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
        _identite_courante(session, profile_id=n.profile_id)
        click.echo(generer_amorce(n))
    finally:
        session.close()


@cli.group()
def resume():
    """Résumé périodique (spec section 5)."""


@resume.command("envoyer")
@click.option("--profile-id", type=int, default=None, help=_AIDE_PROFILE_ID_PORTAIL)
@click.option("--jours", default=7)
def resume_envoyer(profile_id, jours):
    from falkye.summary import generer_et_envoyer_resume

    session = get_session()
    try:
        p = _identite_courante(session, profile_id=profile_id).profile
        summary = generer_et_envoyer_resume(session, p, jours=jours)
        click.echo(f"Résumé #{summary.id} généré : {len(summary.notification_ids)} notification(s) incluse(s)")
    finally:
        session.close()


@cli.group()
def ponderation():
    """Alertes composites préconfigurées par cas d'usage (spec section 4bis,
    Radar+) — remplace l'ancienne exposition par curseur générique, jugée trop
    abstraite (décision d'Alexandre du 2026-09-02). Le mécanisme sous-jacent
    (falkye/pertinence.py::PonderationValeurs) est inchangé, seule
    l'interface change : trois presets nommés (voir `ponderation presets`)
    plutôt que des leviers numériques bruts. N'a d'effet que pour un profil au
    plan Radar+ (falkye/ponderation.py)."""


@ponderation.command("presets")
def ponderation_presets():
    """Liste les alertes composites disponibles et leur description."""
    from falkye.alertes_composites import ALERTES_COMPOSITES

    for a in ALERTES_COMPOSITES.values():
        click.echo(f"{a.id} — {a.nom}")
        click.echo(f"  {a.description}")


@ponderation.command("voir")
@click.option("--profile-id", type=int, default=None, help=_AIDE_PROFILE_ID_PORTAIL)
def ponderation_voir(profile_id):
    from falkye.ponderation import ponderation_pour_profil

    session = get_session()
    try:
        p = _identite_courante(session, profile_id=profile_id).profile
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


@ponderation.command("appliquer")
@click.option("--profile-id", type=int, default=None, help=_AIDE_PROFILE_ID_PORTAIL)
@click.option("--preset", "preset_id", required=True, help="Voir `ponderation presets` pour les valeurs possibles.")
def ponderation_appliquer(profile_id, preset_id):
    """Applique une alerte composite préconfigurée à ce profil (remplace toute
    pondération précédemment appliquée). N'a d'effet que pour un profil Radar+ ;
    se configure indépendamment du plan, même principe que `profile set-webhook`."""
    from falkye.alertes_composites import alerte_composite
    from falkye.models.ponderation_personnalisee import PonderationPersonnalisee

    session = get_session()
    try:
        p = _identite_courante(session, profile_id=profile_id).profile

        alerte = alerte_composite(preset_id)
        if alerte is None:
            raise click.ClickException(f"Alerte composite inconnue : {preset_id} (voir `ponderation presets`)")

        ligne = session.query(PonderationPersonnalisee).filter_by(profile_id=p.id).one_or_none()
        if ligne is None:
            ligne = PonderationPersonnalisee(profile_id=p.id)
            session.add(ligne)

        pond = alerte.ponderation
        ligne.base_a = pond.base_a
        ligne.base_aa = pond.base_aa
        ligne.base_aaa = pond.base_aaa
        ligne.bonus_absence = pond.bonus_absence
        ligne.bonus_velocite_max = pond.bonus_velocite_max
        ligne.bonus_velocite_par_signal = pond.bonus_velocite_par_signal

        session.commit()
        click.echo(
            f"Profil #{p.id} — alerte composite '{alerte.nom}' appliquée "
            f"(effective seulement si plan=radar_plus)."
        )
    finally:
        session.close()


@ponderation.command("reinitialiser")
@click.option("--profile-id", type=int, default=None, help=_AIDE_PROFILE_ID_PORTAIL)
def ponderation_reinitialiser(profile_id):
    from falkye.models.ponderation_personnalisee import PonderationPersonnalisee

    session = get_session()
    try:
        p = _identite_courante(session, profile_id=profile_id).profile
        ligne = session.query(PonderationPersonnalisee).filter_by(profile_id=p.id).one_or_none()
        if ligne is None:
            click.echo(f"Profil #{p.id} — aucune pondération personnalisée à réinitialiser.")
            return
        session.delete(ligne)
        session.commit()
        click.echo(f"Profil #{p.id} — pondération réinitialisée aux valeurs par défaut de FALKYE.")
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
@click.option("--profile-id", type=int, default=None, help=_AIDE_PROFILE_ID_PORTAIL)
def billing_radar_checkout(profile_id):
    """Crée une session Stripe Checkout pour débloquer le plan Radar et affiche son URL."""
    from falkye.billing.stripe_client import creer_session_paiement_radar

    session = get_session()
    try:
        p = _identite_courante(session, profile_id=profile_id).profile
        url = creer_session_paiement_radar(p)
        click.echo(url)
    finally:
        session.close()


@billing.command("statut")
@click.option("--profile-id", type=int, default=None, help=_AIDE_PROFILE_ID_PORTAIL)
def billing_statut(profile_id):
    """Affiche le plan effectif du profil et l'état de son abonnement Stripe, s'il existe."""
    from falkye.models.subscription import Subscription

    session = get_session()
    try:
        p = _identite_courante(session, profile_id=profile_id).profile
        click.echo(f"Profil #{p.id} — plan={p.plan.value}")
        abo = session.query(Subscription).filter_by(profile_id=p.id).one_or_none()
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
    HTTP une fois déployé) ; ceci contourne délibérément la facturation, donc
    RÉSERVÉ AU MODE OPÉRATEUR (FALKYE_OPERATOR=1) — jamais une action en
    libre-service, un client ne doit pas pouvoir se donner Radar+ gratuitement."""
    if not _mode_operateur():
        raise click.ClickException(
            "Réservé au mode opérateur (FALKYE_OPERATOR=1) — contourne la facturation, jamais en libre-service."
        )
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
