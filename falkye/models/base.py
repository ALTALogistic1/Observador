from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Les tables du PRODUIT — ce qui ne se reconstruit pas.

    Profils, besoins, entreprises repérées, signaux, notifications, jetons,
    journal d'exploitation. Perdre une de ces lignes, c'est perdre une décision
    ou une observation que rien ne peut refaire.
    """


class BaseMiroir(DeclarativeBase):
    """Les MIROIRS de sources et l'état de diff — ce qui se reconstruit.

    **Pourquoi une seconde base déclarative plutôt qu'une liste de noms de
    tables.** Le découpage du chantier 29 range les miroirs sur le disque local
    et le produit dans la base distante. Deux cibles, donc deux façons de se
    tromper : une table miroir créée au distant, ou une table produit dans le
    fichier local. Une liste à tenir à jour se serait désynchronisée en silence,
    et la table serait apparue au mauvais endroit sans que rien ne le dise.

    Ici, l'appartenance est STRUCTURELLE : une table est créée là où vit sa
    métadonnée, et un modèle ne peut hériter que d'une seule base. Se tromper
    demande de changer la classe parente, ce qui se voit à la relecture.

    **Ce que ce découpage suppose, et qui a été vérifié avant de le poser
    (2026-09-06).** Aucun modèle miroir ne porte de clé étrangère ni de relation
    vers un modèle produit, et aucune requête ne joint les deux en SQL — une
    jointure entre deux moteurs ne peut pas s'exécuter. Le miroir REQ n'est lu
    que par deux fonctions de falkye/sources/req.py, qui reçoivent déjà leur
    session en paramètre.

    **Ce qu'on perd, et qu'il faut savoir.** Une transaction ne couvre plus les
    deux bases : SQLAlchemy valide chaque moteur séparément, sans validation en
    deux phases. Une panne entre les deux laisse donc le miroir avancé et le
    produit non, ou l'inverse. C'est acceptable ICI précisément parce que le
    miroir se rebâtit (voir docs/MIROIRS.md) — ça ne le serait pas pour deux
    tables du produit.
    """


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def en_utc(moment: datetime | None) -> datetime | None:
    """Ramène un datetime lu depuis la base à un datetime conscient du fuseau.

    Pourquoi ce helper existe : SQLite ne stocke pas le fuseau. Une colonne
    écrite avec `utcnow()` (conscient) revient **naïve** à la relecture, et toute
    soustraction avec `datetime.now(timezone.utc)` lève alors
    `TypeError: can't subtract offset-naive and offset-aware datetimes`.

    Pourquoi cette classe de défaut échappe aux tests : tant que l'objet reste
    dans la session SQLAlchemy qui l'a écrit, il porte encore la valeur Python
    d'origine — consciente — et le calcul passe. Le défaut n'apparaît qu'après
    un vrai aller-retour : autre processus, ou `expire_all()` après commit.
    C'est pour ça qu'un test de régression doit forcer cet aller-retour.
    """
    if moment is None:
        return None
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment
