"""Le cycle hebdomadaire — ce qui s'exécute quand personne ne le demande.

Fréquence fixe et non configurable, comme le mandat le demande : la cadence par
profil est une décision du chantier 8, elle n'entre pas ici. Le déclenchement
lui-même n'est pas dans ce module — c'est un minuteur systemd (voir
`deploiement/`), qui redémarre au démarrage de l'hôte, survit aux redémarrages
et n'ajoute aucune dépendance. Un processus Python qui dormirait en boucle
aurait le défaut inverse : il peut mourir en silence, et rien ne le relève.

**Deux battements de cœur, systématiquement.** Une ligne au début, une à la fin.
Sans elles, trois pannes se ressemblent — voir
falkye/models/journal_exploitation.py, qui les distingue.

**Ce que le cycle précédent a cru livrer, vérifié avant de générer.** Une
acceptation par le fournisseur n'est pas une livraison; le refus du destinataire
arrive après, quand plus rien n'écoute. La réconciliation
(falkye/reconciliation.py) ouvre le cycle pour que les opportunités d'un résumé
rebondi repartent immédiatement, et non la semaine d'après.

**Un profil qui échoue n'emporte pas les autres.** Chaque résumé est isolé :
une adresse invalide chez l'un ne doit pas priver les autres de leur envoi. Les
opportunités du profil en échec restent en attente et repartiront au cycle
suivant, ce que la réunification des chemins de livraison garantit déjà.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select

from falkye.exploitation import journaliser
from falkye.models.journal_exploitation import EvenementExploitation
from falkye.models.profile import Profile

logger = logging.getLogger(__name__)


@dataclass
class RapportCycle:
    profils_traites: int = 0
    remises_rebondies: int = 0
    opportunites_remises_en_attente: int = 0
    profils_suspendus: int = 0
    resumes_envoyes: int = 0
    resumes_en_echec: int = 0
    opportunites_livrees: int = 0
    notifications_creees: int = 0
    sources_en_erreur: int = 0
    sources_ingerees: int = 0
    livraison_omise: bool = False
    echecs: list[str] = field(default_factory=list)

    @property
    def toutes_les_sources_sont_tombees(self) -> bool:
        """Le seuil où « une source en panne » devient « le cycle n'a rien fait ».

        Une source sur neuf qui tombe est une panne partielle : le cycle a
        quand même observé le reste, et faire échouer l'unité pour ça ferait
        passer huit sources saines pour un cycle mort. Mais quand elles tombent
        TOUTES, il n'y a plus de cycle du tout — seulement une exécution qui
        s'est terminée. L'unité doit alors sortir en échec, sans quoi
        `systemctl list-units --failed` reste vide au moment précis où il
        devrait crier.

        Arbitrage tranché le 2026-09-07, sur exception explicite à la règle
        « une source en panne ne fait pas échouer le cycle ».
        """
        return self.sources_ingerees > 0 and self.sources_en_erreur == self.sources_ingerees

    def resume_lisible(self) -> str:
        """Une phrase pour le journal — des faits, jamais une trace de débogage."""
        if self.livraison_omise:
            # « 0 résumé envoyé » se lirait comme une panne. La ligne doit dire
            # que personne n'a essayé, sans quoi le journal d'un cycle mesuré
            # serait indiscernable de celui d'un cycle qui n'a rien pu livrer.
            texte = (
                f"{self.profils_traites} profil(s), "
                f"{self.notifications_creees} notification(s) créée(s), "
                "LIVRAISON OMISE (--sans-livraison) : aucun résumé généré ni envoyé"
            )
        else:
            texte = (
                f"{self.profils_traites} profil(s), "
                f"{self.notifications_creees} notification(s) créée(s), "
                f"{self.resumes_envoyes} résumé(s) envoyé(s), "
                f"{self.opportunites_livrees} opportunité(s) livrée(s)"
            )
        if self.toutes_les_sources_sont_tombees:
            # Pas une nuance de la ligne précédente : c'est un cycle qui n'a
            # rien observé du tout, et il doit se lire comme tel du premier
            # coup d'œil.
            texte += (
                f", AUCUNE OBSERVATION — les {self.sources_ingerees} source(s) "
                "tentée(s) ont toutes échoué"
            )
        elif self.sources_en_erreur:
            # Comptées, jamais nommées : la ligne part dans la base et le nom
            # d'une source est révélateur (charte, neutralité des libellés). Le
            # détail par source vit déjà dans SourceRunLog.
            texte += (
                f", {self.sources_en_erreur} source(s) en erreur "
                f"sur {self.sources_ingerees}"
            )
        if self.resumes_en_echec:
            texte += f", {self.resumes_en_echec} en échec"
        if self.profils_suspendus:
            texte += f", {self.profils_suspendus} profil(s) suspendu(s) après rebonds répétés"
        if self.remises_rebondies:
            texte += (
                f", {self.remises_rebondies} remise(s) rebondie(s) du cycle précédent "
                f"({self.opportunites_remises_en_attente} opportunité(s) reprise(s))"
            )
        return texte


def profils_abonnes(db_session) -> list[Profile]:
    """Les profils à qui un résumé peut partir.

    Deux exclusions, de natures différentes. `desabonne_le` est le geste de
    l'abonné : définitif jusqu'à ce qu'il revienne. `envoi_suspendu_le` est une
    décision du produit après trois rebonds : réparable, et levée par
    `falkye profile reprendre-envoi`. Les opportunités d'un profil suspendu
    restent en attente et repartiront — la suspension ne perd rien, c'est ce qui
    la distingue d'un désabonnement.
    """
    return list(
        db_session.execute(
            select(Profile).where(
                Profile.desabonne_le.is_(None), Profile.envoi_suspendu_le.is_(None)
            )
        )
        .scalars()
        .all()
    )


class CacheInaccessible(RuntimeError):
    """Le répertoire de cache des téléchargements n'est pas accessible en écriture."""


def verifier_cache_telechargement() -> None:
    """Refuser tôt et fort plutôt que de perdre les sources une par une.

    **Ce qui est arrivé le 2026-09-07.** Le cache visait un chemin RELATIF,
    résolu sous le répertoire de travail de l'unité — en lecture seule sous
    `ProtectSystem=strict`. **Cinq sources sur neuf sont mortes**, à vingt-cinq
    secondes d'intervalle, chacune au fond d'une trace de pile, sur le même
    `OSError: [Errno 30]`. Le cycle s'est terminé en succès, 0 notification
    créée, et il a fallu lire le journal ligne à ligne pour comprendre que ce
    n'était pas une semaine calme mais une variable d'environnement manquante.

    Une erreur de CONFIGURATION n'est pas une source qui tombe. Une source qui
    tombe coûte une source — c'est la règle, et elle tient. Un cache
    inaccessible coûte toutes les sources qui téléchargent, et rien dans le
    déroulement ne le dit d'un coup. C'est le même arbitrage que
    `outils/import_miroir_req.py` : nommer ce qu'il faut corriger, avant
    d'avoir rien touché.
    """
    from falkye.sources.ckan_client import CACHE_DIR

    chemin = Path(CACHE_DIR)
    try:
        chemin.mkdir(parents=True, exist_ok=True)
        temoin = chemin / ".falkye-ecriture"
        temoin.write_bytes(b"")
        temoin.unlink()
    except OSError as exc:
        raise CacheInaccessible(
            f"Le cache de téléchargement ({chemin}) n'est pas accessible en "
            f"écriture : {exc}. Toutes les sources qui téléchargent un fichier "
            "échoueraient, une par une, sans que le cycle le dise. "
            "Sous systemd, poser dans l'unité :\n"
            "    CacheDirectory=falkye\n"
            "    Environment=FALKYE_CACHE_DIR=/var/cache/falkye\n"
            "Hors systemd, définir FALKYE_CACHE_DIR sur un répertoire "
            "accessible en écriture."
        ) from exc


def executer_cycle(lookback_days: int = 30, livrer_les_resumes: bool = True) -> RapportCycle:
    """Un cycle complet : détecter, puis livrer. Lève si le cycle a échoué.

    Lever est voulu : le gestionnaire de services doit voir l'unité en échec.
    La ligne d'échec est écrite AVANT de relever, pour qu'elle existe même si
    plus rien ne tourne ensuite.

    **`livrer_les_resumes=False` — pourquoi ça existe.** Pour mesurer un cycle
    réel sur l'hôte pendant qu'un envoi ne doit PAS partir : c'est la situation
    du 2026-09-07, où le réglage de désabonnement du flux de diffusion n'est pas
    encore débloqué chez le fournisseur. Sans ce mode, voir tourner le cycle et
    respecter l'interdiction d'envoi s'excluaient.

    La coupure est posée AVANT `generer_et_envoyer_resume`, jamais à l'intérieur
    du canal. Générer un résumé puis retenir l'envoi laisserait un
    `PeriodicSummary` avec `envoye_le` à NULL — indiscernable d'une tentative qui
    a échoué, et la réconciliation du cycle suivant travaillerait sur une trace
    inventée. La réconciliation et la détection, elles, tournent pour de vrai :
    ce sont elles qu'on veut mesurer, et elles n'envoient rien.
    """
    from falkye.db import get_session
    from falkye.engine import run_veille_continue
    from falkye.reconciliation import reconcilier_livraisons
    from falkye.registry.loader import get_registry
    from falkye.summary import generer_et_envoyer_resume

    journaliser(EvenementExploitation.CYCLE_DEBUT)
    rapport = RapportCycle()

    try:
        # AVANT tout travail : un cache inaccessible fait échouer toutes les
        # sources qui téléchargent, et le dire ici coûte une seconde au lieu de
        # sept minutes. Dans le `try`, pour que l'échec soit journalisé comme
        # tel — un début sans fin serait le mauvais diagnostic.
        verifier_cache_telechargement()

        scan = run_veille_continue(lookback_days=lookback_days)
        rapport.notifications_creees = scan.nb_notifications_creees
        # Sans ce compte, un cycle où TOUTES les sources ont échoué journalise
        # « 0 notification créée » et sort en succès — mot pour mot ce que
        # journalise une semaine calme. Constaté le 2026-09-07 en répétition :
        # une source tombée sur une base verrouillée, cycle vert, rien dit.
        # Le dénominateur est le nombre de sources TENTÉES. Une source sans
        # connecteur n'a pas échoué, elle n'a pas été essayée — la compter
        # gonflerait le dénominateur et ferait passer un effondrement complet
        # pour une panne partielle.
        rapport.sources_ingerees = sum(1 for r in scan.ingestion if not r.ignoree)
        rapport.sources_en_erreur = sum(
            1 for r in scan.ingestion if r.erreur and not r.ignoree
        )

        db_session = get_session()
        try:
            # AVANT de générer quoi que ce soit : ce que le cycle précédent a cru
            # livrer l'a-t-il été? Un rebond remet ses opportunités en attente, et
            # elles doivent repartir DANS CE CYCLE-CI, pas au suivant — sinon un
            # refus coûterait deux semaines au lieu d'une.
            reconciliation = reconcilier_livraisons(db_session, get_registry())
            rapport.remises_rebondies = reconciliation.rebondies
            rapport.opportunites_remises_en_attente = (
                reconciliation.opportunites_remises_en_attente
            )
            rapport.profils_suspendus = len(reconciliation.profils_suspendus)
            for ligne in reconciliation.resumes_rebondis:
                journaliser(
                    EvenementExploitation.LIVRAISON_REBONDIE, ligne, db_session=db_session
                )
            for ligne in reconciliation.profils_suspendus:
                journaliser(
                    EvenementExploitation.ENVOI_SUSPENDU, ligne, db_session=db_session
                )

            profils = profils_abonnes(db_session)
            if not livrer_les_resumes:
                # Comptés, pas servis. Le nombre est ce qu'on veut savoir : il
                # dit combien d'envois ce cycle aurait produits.
                rapport.profils_traites = len(profils)
                rapport.livraison_omise = True
                profils = []

            for profile in profils:
                rapport.profils_traites += 1
                try:
                    summary = generer_et_envoyer_resume(db_session, profile)
                except Exception as exc:  # noqa: BLE001
                    # Un profil isolé ne fait pas tomber le cycle. Ses
                    # opportunités restent en attente et repartiront.
                    db_session.rollback()
                    rapport.resumes_en_echec += 1
                    rapport.echecs.append(f"profil #{profile.id} : {type(exc).__name__}")
                    logger.warning("Résumé en échec pour le profil %s : %s", profile.id, exc)
                    continue

                if summary is None:
                    continue  # désabonné entre-temps
                if summary.envoye_le is not None:
                    rapport.resumes_envoyes += 1
                    rapport.opportunites_livrees += len(summary.notification_ids)
                else:
                    rapport.resumes_en_echec += 1
                    rapport.echecs.append(f"profil #{profile.id} : aucun canal n'a livré")

            journaliser(
                EvenementExploitation.CYCLE_FIN, rapport.resume_lisible(), db_session=db_session
            )
            db_session.commit()
        finally:
            db_session.close()

    except Exception as exc:  # noqa: BLE001
        journaliser(EvenementExploitation.CYCLE_ECHEC, f"{type(exc).__name__}: {exc}")
        raise

    return rapport
