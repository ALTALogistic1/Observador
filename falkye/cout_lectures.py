"""Ce qu'une exécution a COÛTÉ en lectures, ventilé par chemin de résolution.

**Pourquoi ce module existe.** Le 2026-09-08, le quota de lectures de la base
distante a été épuisé. Le cycle qui l'a vidé était rapide, léger, huit sources
sur huit en succès. On mesurait la durée, la mémoire, les écritures — jamais les
lectures. La santé d'une exécution inclut ce qu'elle a coûté, pas seulement ce
qu'elle a produit.

**Deux grandeurs, jamais confondues, et c'est toute la conception.**

*Un COMPTE exact* — combien de fois chaque chemin de résolution a été emprunté.
Mesuré par incrément, au point d'appel. Rien à estimer, rien qui vieillit.

*Une DÉRIVATION* — combien de lignes ça a fait lire à la base. Elle n'est pas
mesurable ici : le pilote libSQL qu'utilise SQLAlchemy n'expose pas `rows_read`,
seul le protocole Hrana le rend. Elle se calcule donc à la LECTURE du rapport, à
partir du compte exact et de la population du moment — jamais écrite en base
comme si elle avait été mesurée.

C'est la règle du 2026-09-07 appliquée au coût : *un compte qui décrit une
exécution ne se calcule jamais depuis la base que cette exécution écrit.* Ici,
c'est plus fort encore — le prix d'un chemin DÉPEND de la population, donc une
constante gravée aujourd'hui mentirait dans six mois sans que rien ne le dise.

**Ce que le module ne fait pas.** Il ne compte pas les requêtes du reste du
cycle (déduplication, chargement des profils, écritures). Ces chemins-là sont
indexés et lisent 0 ou 2 lignes; les trois chemins de résolution sont ceux qui
lisent par milliers. Élargir la couverture est un travail à part, et prétendre
compter « tout » alors qu'on compte trois chemins serait pire que de le dire.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

CHEMIN_EXACT = "exact"
CHEMIN_PREFIXE = "prefixe"
CHEMIN_SOUS_CHAINE = "sous_chaine"

CHEMINS = (CHEMIN_EXACT, CHEMIN_PREFIXE, CHEMIN_SOUS_CHAINE)


@dataclass
class ComptesResolution:
    """Les appels d'une exécution, par chemin. Des entiers, rien d'autre."""

    appels: dict[str, int] = field(default_factory=lambda: {c: 0 for c in CHEMINS})

    def compter(self, chemin: str) -> None:
        self.appels[chemin] = self.appels.get(chemin, 0) + 1

    @property
    def total(self) -> int:
        return sum(self.appels.values())


_comptes: ContextVar[ComptesResolution | None] = ContextVar("falkye_comptes", default=None)


def compter(chemin: str) -> None:
    """Incrémente le compteur du chemin emprunté, s'il y a une exécution ouverte.

    Silencieux hors exécution : un appel depuis un outil ou la ligne de commande
    ne doit ni lever ni s'inventer un compteur. Le prix de ce silence est qu'un
    chemin emprunté hors exécution n'est compté nulle part — assumé, parce que
    l'alternative (un compteur global) mélangerait des exécutions distinctes.
    """
    comptes = _comptes.get()
    if comptes is not None:
        comptes.compter(chemin)


@contextmanager
def ouvrir_comptes():
    """Pose un compteur neuf le temps du bloc, puis restaure le précédent.

    Restaurer, et pas seulement effacer : sans ça, une source imbriquée ou une
    exception laisserait le compteur d'une exécution ouvert, et la suivante
    additionnerait ses appels à ceux de la précédente. C'est la même raison qui
    fait empiler les identifiants d'exécution (falkye/execution.py).
    """
    comptes = ComptesResolution()
    jeton = _comptes.set(comptes)
    try:
        yield comptes
    finally:
        _comptes.reset(jeton)


def comptes_courants() -> ComptesResolution | None:
    return _comptes.get()


# --- La dérivation, faite à la lecture, jamais écrite en base ---------------


@dataclass(frozen=True)
class PrixChemin:
    """Ce qu'un chemin fait lire, exprimé en fonction de la population.

    **Une formule, pas une constante.** Le repli par sous-chaîne lit toute la
    population sans NEQ : son prix suit cette population. Une constante mesurée
    aujourd'hui (8 396) serait fausse dès la semaine prochaine, et fausse en
    silence — la forme exacte du défaut que ce module existe pour éviter.
    """

    nom: str
    #: lignes lues = `part_population` × population_sans_neq + `fixe`
    part_population: float
    fixe: int
    note: str


@dataclass(frozen=True)
class Provenance:
    """Les conditions dans lesquelles les prix ont été pris.

    **Une table de prix mesurée une fois et jamais redatée est une vérification
    qui se périme sans le dire.** Le 2026-09-08 en donne la preuve dans la même
    journée : le chemin exact valait 8 396 lignes le matin et 2 l'après-midi. Rien
    dans le code n'avait changé — un index avait été posé.

    D'où `index_companies` : ce ne sont pas des métadonnées décoratives, c'est la
    condition de validité. Toute création ou tout retrait d'index sur `companies`
    invalide les trois prix, et `peremption()` le dit avant qu'on s'appuie dessus.
    """

    mesure_le: str
    methode: str
    population_sans_neq: int
    #: L'état d'index de `companies` au moment de la mesure. Le comparer à
    #: l'état courant est ce qui rend la péremption détectable.
    index_companies: tuple[str, ...]


PROVENANCE = Provenance(
    mesure_le="2026-09-08",
    methode="`rows_read` du protocole Hrana (/v2/pipeline), contre la base réelle",
    population_sans_neq=8_395,
    index_companies=(
        "ix_companies_neq",
        "ix_companies_neq_nom_normalise",
        "ix_companies_nom_detecte_normalise",
    ),
)


PRIX: dict[str, PrixChemin] = {
    CHEMIN_EXACT: PrixChemin(
        nom="exact",
        part_population=0.0,
        fixe=2,
        note="0 ligne sur un nom absent, 2 sur un nom présent (index puis table). "
        "Le majorant est retenu : sous-estimer un coût est le sens dangereux.",
    ),
    CHEMIN_PREFIXE: PrixChemin(
        nom="préfixe GLOB",
        part_population=0.0,
        fixe=84,
        note="recherche par plage dans un index couvrant — le coût suit le nombre "
        "d'homonymes de préfixe, pas la population. 84 mesuré sur « construction ».",
    ),
    CHEMIN_SOUS_CHAINE: PrixChemin(
        nom="sous-chaîne",
        part_population=1.0,
        fixe=1,
        note="`LIKE '%…%'` : aucun index ne rattrape une sous-chaîne non ancrée. "
        "Lit TOUTE la population sans NEQ, à chaque appel.",
    ),
}


#: Ce que la dérivation N'EST PAS, à répéter partout où elle s'affiche.
#:
#: Charte, Force 3 : mesure, estimation et absence coexistent avec leur
#: fiabilité assumée, jamais fusionnées en un chiffre dont on ne sait plus d'où
#: il vient. Le compte d'appels est une MESURE. Les lignes qui en sortent sont
#: une ESTIMATION. Le compteur de consommation de l'hébergeur est la seule
#: mesure du coût réel — c'est contre lui que cette estimation se valide, sur un
#: cycle complet en régime. Si les deux divergent de plus d'un ordre de
#: grandeur, c'est l'estimation qui a tort.
AVERTISSEMENT_DERIVATION = (
    "Les colonnes « lignes ~ » sont une ESTIMATION dérivée d'un compte exact, "
    "jamais un `rows_read`. Elles ne suffisent pas à décider d'un palier de "
    "quota : cette décision se prend contre le compteur de l'hébergeur, après "
    "validation sur un cycle complet en régime."
)


def index_companies(db_session) -> tuple[str, ...]:
    """Les index actuellement posés sur `companies`, triés."""
    from sqlalchemy import text

    from falkye.models.company import Company

    connexion = db_session.connection(bind_arguments={"mapper": Company.__mapper__})
    lignes = connexion.execute(
        text("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='companies'")
    ).all()
    return tuple(sorted(nom for (nom,) in lignes if nom))


def peremption(db_session) -> str | None:
    """Pourquoi la table de prix n'est plus valable, ou None si elle l'est.

    Ne compare QUE les index : c'est le plan d'exécution qui fixe le prix d'un
    chemin, et c'est l'index qui fixe le plan. La population, elle, entre déjà
    dans la formule — elle ne périme rien, elle se relit.
    """
    actuels = index_companies(db_session)
    attendus = tuple(sorted(PROVENANCE.index_companies))
    if actuels == attendus:
        return None
    ajoutes = sorted(set(actuels) - set(attendus))
    retires = sorted(set(attendus) - set(actuels))
    details = []
    if ajoutes:
        details.append("posé(s) depuis : " + ", ".join(ajoutes))
    if retires:
        details.append("retiré(s) depuis : " + ", ".join(retires))
    return (
        f"Prix mesurés le {PROVENANCE.mesure_le} sur un autre état d'index — "
        + " ; ".join(details)
        + ". Les reprendre avant de s'en servir : un index change le plan, "
        "et le plan fixe le prix (le chemin exact est passé de 8 396 lignes à 2 "
        "en une journée, sans qu'une ligne de code change)."
    )


def population_sans_neq(db_session) -> int:
    """Le nombre d'entreprises sans NEQ — le multiplicateur du repli.

    Se lit au moment du RAPPORT, jamais au moment de l'exécution : c'est une
    grandeur de la base, pas de l'exécution, et la figer dans la ligne de journal
    ferait vieillir une dérivation sans que rien ne le signale.
    """
    from sqlalchemy import func, select

    from falkye.models.company import Company

    return db_session.execute(
        select(func.count()).select_from(Company).where(Company.neq.is_(None))
    ).scalar_one()


def lignes_lues_derivees(appels: dict[str, int], population: int) -> dict[str, int]:
    """La dérivation, par chemin. **Un ordre de grandeur, pas une mesure.**

    Le nom de la fonction porte le mot `derivees` à dessein : partout où ce
    résultat voyage, il doit rester distinguable d'un `rows_read` réel.
    """
    return {
        chemin: int(nb * (PRIX[chemin].part_population * population + PRIX[chemin].fixe))
        for chemin, nb in appels.items()
        if chemin in PRIX
    }
