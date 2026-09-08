"""L'identité d'une exécution de source — partagée par des journaux qui ne
vivent pas dans la même base.

**Le fait qui commande toute la conception.** Les trois traces d'une même
exécution sont réparties sur DEUX bases :

    SourceRunLog        → Base       → base du PRODUIT, distante, facturée
    DiffRunHistorique   → BaseMiroir → fichier LOCAL
    DiffQuarantaine     → BaseMiroir → fichier LOCAL

Le mandat du chantier 2 demande « un identifiant d'exécution partagé permettant
de rattacher les trois traces à un même run ». Il ne pouvait pas savoir que le
découpage des bases (2026-09-06) est arrivé après sa phase 0. La conséquence est
structurelle : **cet identifiant ne peut pas être une clé étrangère.** Aucune
contrainte d'intégrité ne traverse deux bases, et aucune requête SQL ne peut
joindre les trois tables. Le rapprochement se fait dans le code, sur une valeur
opaque, et l'absence de correspondance est un état normal — pas une violation.

**Pourquoi une variable de contexte plutôt qu'un paramètre.** `executer_diff`
est appelé DEPUIS les connecteurs, à l'intérieur de `detect()`. Faire descendre
l'identifiant par la signature demanderait de l'ajouter à `detect()` — donc à
l'interface de TOUTES les sources, y compris les treize qui ne font aucun diff.
C'est exactement le prix que le découpage des bases a refusé de payer ailleurs
(voir falkye/db.py::get_sessionmaker).

**Ce que ça coûte, dit franchement.** Un état ambiant est invisible à la lecture
d'une signature. La contrepartie est posée ici : hors de toute exécution,
`execution_courante()` rend `None`, et une trace écrite là porte `None` — jamais
un identifiant fabriqué. Un journal qui invente un rattachement serait pire que
pas de rattachement du tout : il ferait croire à un lien vérifié.
"""
from __future__ import annotations

import enum
import os
import uuid
from contextlib import contextmanager
from contextvars import ContextVar

_execution: ContextVar[str | None] = ContextVar("falkye_execution", default=None)


def nouvel_identifiant() -> str:
    """Un identifiant opaque, sans signification et sans ordre.

    Pas un entier auto-incrémenté : il devrait être alloué par UNE base, et
    c'est précisément ce qu'on n'a pas. Pas un horodatage non plus — deux
    exécutions peuvent commencer dans la même milliseconde, et un identifiant
    qui se devine invite à le reconstruire au lieu de le lire.
    """
    return uuid.uuid4().hex


def execution_courante() -> str | None:
    """L'identifiant de l'exécution en cours, ou None hors de toute exécution."""
    return _execution.get()


@contextmanager
def execution(identifiant: str | None = None):
    """Ouvre une exécution. Rend son identifiant.

    Réentrant par empilement : une exécution imbriquée remplace la valeur le
    temps de son bloc et la restaure ensuite, y compris si le bloc lève. Sans
    ça, une source qui échoue laisserait son identifiant en place et la source
    SUIVANTE écrirait ses traces sous le nom de celle qui est tombée.
    """
    identifiant = identifiant or nouvel_identifiant()
    jeton = _execution.set(identifiant)
    try:
        yield identifiant
    finally:
        _execution.reset(jeton)


class Lancement(str, enum.Enum):
    """Qui a lancé cette exécution — et donc ce qu'on a le droit d'en déduire.

    **La distinction n'est pas cosmétique.** « systemd l'aurait tuée » suppose
    que systemd la surveillait. Un cycle lancé à la main n'est gouverné par aucun
    délai : il peut tourner trois heures sans que personne l'interrompe, et il y
    en a eu beaucoup cette semaine. Conclure `interrompue` sur une de ces
    exécutions serait une conclusion vraie sous une condition qu'on n'a pas
    vérifiée — la forme même du défaut que ce chantier existe pour retirer.
    """

    UNITE = "unite"
    MANUEL = "manuel"
    #: Les lignes écrites avant que ce champ existe. Ni l'un ni l'autre : on ne
    #: sait pas, et on ne le devinera pas après coup.
    INCONNU = "inconnu"


def mode_de_lancement() -> Lancement:
    """`UNITE` si systemd a démarré ce processus, `MANUEL` sinon.

    `INVOCATION_ID` est posé par systemd dans l'environnement de tout processus
    qu'il démarre, et par rien d'autre. Le lire est plus sûr que d'inspecter le
    parent : un cycle lancé à la main depuis un shell d'un service resterait
    manuel pour la question qui nous occupe — personne ne le tuera au délai.
    """
    return Lancement.UNITE if os.environ.get("INVOCATION_ID") else Lancement.MANUEL
