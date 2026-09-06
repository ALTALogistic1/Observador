from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


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
