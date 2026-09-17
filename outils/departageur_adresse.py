#!/usr/bin/env python3
"""L'ADRESSE, en UN départageur à DEUX niveaux — le code postal, puis la ville.

**Le fait qui l'écrit** *(2026-09-17, mesure des trois départageurs sur l'hôte)*.
Sur les **5 002 ambigus**, le code postal en sépare **1 805 (36,1 %)**, dont
**725 que rien d'autre ne sépare**; la ville en sépare **1 235 (24,7 %)**, dont
**187 seule**; l'activité **166 (3,3 %)**, dont **97**. *Le recouvrement des
trois est de 1 114 dossiers.* **Le code postal est le départageur; la ville est
son repli; l'activité attend le chantier 22.**

> ⚠️ **Deux niveaux d'un MÊME départageur, pas deux mécanismes.** *La ville ne
> se demande que là où le code postal n'a pas tranché* — et elle ne se demande
> **jamais** là où le code postal a tranché *contre tout le monde*.

## Le repli, et la seule porte qu'il ne franchit pas

| issue du CODE POSTAL | la ville parle? | pourquoi |
|---|---|---|
| `DÉPARTAGÉ` | non | *c'est fini : un second avis ne s'ajoute pas à une décision* |
| le dossier ne porte pas le fait | **oui** | *le dossier n'a pas de code postal; il peut avoir une ville* |
| un concurrent ne porte pas le fait | **oui** | *« inconnu ≠ non » a bloqué 837 dossiers; la ville peut être connue de tous* |
| plusieurs concurrents compatibles | **oui** | *le code postal a réduit sans trancher; la ville réduit encore* |
| **aucun concurrent compatible** | ⚠️ **NON** | ⚠️ **voir ci-dessous** |

⚠️ **« Le fait les exclut tous » interdit le repli, et c'est la règle la plus
importante de ce module.** *Le code postal du dossier ne concorde avec AUCUN
candidat : soit le bon candidat n'est pas dans le lot, soit le fait est sale.*
**Dans les deux cas, laisser la ville désigner un gagnant serait construire un
départage PAR-DESSUS une contradiction établie** — et rendre 443 départages dont
on sait déjà qu'un fait plus précis les dément.

## Ce qui ne bouge pas

⚠️ **Un départageur AJOUTE un fait; il n'ABAISSE pas une garde.** Le seuil de
**92** et l'écart de **8** ne sont pas lus ici pour être changés, seulement pour
savoir *qui sont les concurrents*.

⚠️ **Et un départage ÉCARTE un candidat; il n'en CONFIRME aucun.** *Deux
entreprises distinctes peuvent partager une région de tri.* **Les paires se
regardent une à une avant toute écriture, et ce module n'écrit rien.**

## La non-régression sur les retenus — structurelle, pas espérée

`departager_le_dossier` **REFUSE** tout dossier qui n'est pas `ambigu`
*(`PasUnAmbigu`)*. **Un dossier RETENU ne peut donc pas être re-décidé par
l'adresse** — non parce qu'on n'appellera pas, mais parce que l'appel échoue.
*« Critère, pas effet secondaire acceptable. »*
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from outils.departageurs import (
    AUCUN_COMPATIBLE,
    DEPARTAGE,
    ISSUES,
    PLUSIEURS_COMPATIBLES,
    SANS_FAIT_AU_DOSSIER,
    SANS_FAIT_CHEZ_UN_CONCURRENT,
    Fait,
    codes_postaux,
    departager,
    fait_de_la_ville,
)

#: Les deux niveaux, **dans l'ordre où ils se demandent**. *L'ordre est la
#: décision : le code postal d'abord, parce qu'il est plus précis et qu'il sépare
#: deux fois plus.*
NIVEAU_CODE_POSTAL = "code postal"
NIVEAU_VILLE = "ville"
NIVEAUX = (NIVEAU_CODE_POSTAL, NIVEAU_VILLE)

#: Les issues d'un niveau qui **laissent parler le suivant**. *Chacune veut dire
#: « ce niveau n'a pas tranché », et aucune ne veut dire « ce niveau a tranché
#: contre ».*
ISSUES_QUI_APPELLENT_LE_REPLI = (
    SANS_FAIT_AU_DOSSIER,
    SANS_FAIT_CHEZ_UN_CONCURRENT,
    PLUSIEURS_COMPATIBLES,
)

#: ⚠️ **L'issue qui FERME le départageur sans départager.** *Le fait du dossier
#: dément tous les candidats; un fait moins précis n'a pas à le contredire.*
ISSUES_QUI_FERMENT = (AUCUN_COMPATIBLE,)


class IssueNonClassee(RuntimeError):
    """Une issue de `departageurs.ISSUES` que la règle de repli ne classe pas.

    ⚠️ *Sans cette garde, ajouter une issue à `departageurs.py` la ferait
    silencieusement tomber du côté « ne replie pas » — et un changement de
    vocabulaire deviendrait un changement de comportement que personne n'a
    demandé.* **Elle se lève à l'import, pas à l'exécution.**
    """


def _refuser_si_une_issue_nest_pas_classee() -> None:
    classees = {DEPARTAGE, *ISSUES_QUI_APPELLENT_LE_REPLI, *ISSUES_QUI_FERMENT}
    orphelines = set(ISSUES) - classees
    if orphelines:
        raise IssueNonClassee(
            "la règle de repli ne dit rien de : " + ", ".join(sorted(orphelines))
            + " — la classer explicitement dans ISSUES_QUI_APPELLENT_LE_REPLI ou "
              "ISSUES_QUI_FERMENT, jamais par défaut."
        )


_refuser_si_une_issue_nest_pas_classee()


#: Les clés de `Signal.champs` où une adresse peut vivre — **y compris imbriquée**.
#: *Le SEAO range la sienne sous `adresse_entreprise_adjudicataire`; l'EIMT la met
#: à plat.* Une liste, parce que c'est une observation et non une norme.
CLES_ADRESSE = ("adresse", "code_postal", "adresse_entreprise_adjudicataire")


def texte_des_champs(champs: dict | None, cles) -> str:
    """Tout le texte des clés demandées, imbrication comprise — *aplati, parce
    qu'un code postal rangé un niveau plus bas est un code postal quand même.*"""
    morceaux: list[str] = []

    def _plonger(valeur):
        if isinstance(valeur, dict):
            for v in valeur.values():
                _plonger(v)
        elif isinstance(valeur, (list, tuple)):
            for v in valeur:
                _plonger(v)
        elif valeur is not None:
            morceaux.append(str(valeur))

    for cle in cles:
        if cle in (champs or {}):
            _plonger(champs[cle])
    return " ".join(morceaux)


@dataclass(frozen=True)
class FaitsDAdresse:
    """Ce qu'un côté — dossier ou candidat — sait de son adresse, **par niveau**.

    *Les deux se lisent ensemble parce qu'ils viennent du même texte; ils se
    comparent séparément parce qu'ils n'ont pas la même précision.*
    """

    code_postal: Fait | None
    ville: Fait | None

    def de_niveau(self, niveau: str) -> Fait | None:
        if niveau == NIVEAU_CODE_POSTAL:
            return self.code_postal
        if niveau == NIVEAU_VILLE:
            return self.ville
        raise KeyError(niveau)


@dataclass(frozen=True)
class Departage:
    """Ce que le départageur d'adresse a conclu, **et par quel niveau**.

    `niveau` vaut `None` quand rien n'a été prononcé : *l'issue dit alors lequel
    des maillons a manqué, et au dernier niveau consulté.*
    """

    issue: str
    niveau: str | None
    gagnant: int | None
    #: L'issue de CHAQUE niveau consulté, dans l'ordre. *Sans elle, « la ville a
    #: séparé » ne dit pas si le code postal a été muet ou bloqué par « inconnu ≠
    #: non » — et ce sont deux correctifs différents.*
    par_niveau: tuple[tuple[str, str], ...]

    @property
    def prononce(self) -> bool:
        return self.niveau is not None

    def issue_du_niveau(self, niveau: str) -> str | None:
        for nom, issue in self.par_niveau:
            if nom == niveau:
                return issue
        return None


def departager_ladresse(
    du_dossier: FaitsDAdresse, des_concurrents: list[FaitsDAdresse]
) -> Departage:
    """Les deux niveaux, dans l'ordre, **avec le repli et son unique interdit**.

    ⚠️ *La ville ne parle pas quand le code postal a exclu tout le monde* — voir
    l'entête du module : ce serait bâtir un départage par-dessus une
    contradiction établie.
    """
    par_niveau: list[tuple[str, str]] = []
    for niveau in NIVEAUX:
        issue, gagnant = departager(
            du_dossier.de_niveau(niveau),
            [faits.de_niveau(niveau) for faits in des_concurrents],
        )
        par_niveau.append((niveau, issue))
        if issue == DEPARTAGE:
            return Departage(issue, niveau, gagnant, tuple(par_niveau))
        if issue not in ISSUES_QUI_APPELLENT_LE_REPLI:
            return Departage(issue, None, None, tuple(par_niveau))
    return Departage(par_niveau[-1][1], None, None, tuple(par_niveau))


# ---------------------------------------------------------------------------
# LIRE LES FAITS — une seule fois, empruntée par la mesure ET par la reprise
# ---------------------------------------------------------------------------
# ⚠️ *Une mesure qui lit une adresse pendant qu'une écriture en lit une autre est
# un rapport sur une population imaginaire* (même règle que `villes_des_signaux`,
# `neq_retenu` et `famille_de`). **Ce qui décide se nomme une fois et s'emprunte.**


def faits_du_dossier(company, champs: dict | None = None,
                     ville_vue: str | None = None) -> FaitsDAdresse:
    """Les deux faits d'un dossier — *`Company` d'abord, `Signal.champs` ensuite.*

    ⚠️ **La ville explicite du dossier prime sur celle vue dans un signal.** *Une
    ville promue a été décidée; une ville vue a été trouvée.*
    """
    texte = " ".join(filter(None, [
        company.adresse,
        company.code_postal,
        texte_des_champs(champs, CLES_ADRESSE),
    ]))
    return FaitsDAdresse(
        codes_postaux(texte),
        fait_de_la_ville(company.ville or ville_vue),
    )


def faits_du_candidat(entry) -> FaitsDAdresse:
    """Les deux faits d'une entrée du registre. *Le REQ donne un numéro civique
    et une rue là où l'EIMT donne une municipalité — le code postal est le seul
    fragment que les deux écrivent.*"""
    return FaitsDAdresse(
        codes_postaux(" ".join(filter(None, [entry.adresse, entry.code_postal]))),
        fait_de_la_ville(entry.ville),
    )


def champs_des_dossiers(db_session, ids: set[int]) -> dict[int, dict]:
    """Les `Signal.champs` cumulés de chaque dossier demandé."""
    from sqlalchemy import select

    from falkye.models.signal import Signal

    cumules: dict[int, dict] = defaultdict(dict)
    for company_id, champs in db_session.execute(
        select(Signal.company_id, Signal.champs).execution_options(yield_per=2000)
    ):
        if company_id in ids and champs:
            cumules[company_id].update(champs)
    return cumules


def faits_des_dossiers(db_session, companies, champs: dict | None = None
                       ) -> dict[int, FaitsDAdresse]:
    """`company_id -> FaitsDAdresse`, signaux et villes vues compris."""
    from outils.villes_des_signaux import villes_des_signaux

    ids = {c.id for c in companies}
    if champs is None:
        champs = champs_des_dossiers(db_session, ids)
    villes = villes_des_signaux(db_session, ids)
    return {
        c.id: faits_du_dossier(
            c,
            champs.get(c.id),
            villes[c.id].ville if c.id in villes else None,
        )
        for c in companies
    }


# ---------------------------------------------------------------------------
# L'ENTRÉE — et la garde qui rend la non-régression STRUCTURELLE
# ---------------------------------------------------------------------------

class PasUnAmbigu(RuntimeError):
    """Le départageur a été appelé sur un dossier que le NOM a déjà tranché.

    ⚠️ *La non-régression sur les retenus n'est pas un effet secondaire
    acceptable : c'est un critère.* **Donc l'appel échoue, au lieu de réussir
    discrètement.**
    """


def refuser_si_ce_nest_pas_un_ambigu(matches, seuil: float | None = None,
                                     ecart_min: float | None = None) -> None:
    from falkye.resolution import famille_de

    famille = famille_de(matches, seuil=seuil, ecart_min=ecart_min)
    if famille != "ambigu":
        raise PasUnAmbigu(
            f"dossier « {famille} » — le départageur d'adresse ne s'applique "
            "qu'aux ambigus. Un retenu a été tranché par le nom; un « trop "
            "faible » n'a pas de concurrent à écarter."
        )


def concurrents_de(matches, ecart_min: float | None = None) -> list:
    """Les candidats que le nom ne sépare pas — *ceux à moins de l'écart minimal
    du meilleur.* **C'est exactement l'ensemble sur lequel un abaissement de
    l'écart trancherait à l'aveugle.**"""
    from falkye.resolution import SEUIL_AMBIGUITE_ECART_MIN

    if ecart_min is None:
        ecart_min = SEUIL_AMBIGUITE_ECART_MIN
    if not matches:
        return []
    haut = matches[0].score
    return [m for m in matches if haut - m.score < ecart_min]


def departager_le_dossier(matches, du_dossier: FaitsDAdresse,
                          seuil: float | None = None,
                          ecart_min: float | None = None) -> tuple[Departage, list]:
    """`(départage, concurrents)` — **le seul point d'entrée, garde comprise.**

    *Un appelant ne peut pas sauter la garde en oubliant de l'appeler : elle est
    dedans.*
    """
    refuser_si_ce_nest_pas_un_ambigu(matches, seuil=seuil, ecart_min=ecart_min)
    concurrents = concurrents_de(matches, ecart_min=ecart_min)
    departage = departager_ladresse(
        du_dossier, [faits_du_candidat(m.entry) for m in concurrents]
    )
    return departage, concurrents
