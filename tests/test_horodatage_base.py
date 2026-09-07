"""Les dates relues depuis la base — une classe de défaut, pas un défaut isolé.

Ce que ces tests protègent : **une date écrite consciente du fuseau revient
naïve**. SQLite ne stocke pas le fuseau; toute soustraction ou comparaison
avec `datetime.now(timezone.utc)` lève alors `TypeError: can't subtract
offset-naive and offset-aware datetimes`.

Pourquoi la suite ne le voyait pas. Tant que l'objet reste dans la session qui
l'a écrit, il porte encore la valeur Python d'origine — consciente — et le
calcul passe. Le défaut n'apparaît qu'après un vrai aller-retour. Chaque test
ici force cet aller-retour avec `commit()` puis `expire_all()`, ce qui
reproduit dans un seul processus ce qui, en production, arrivait au DEUXIÈME
cycle hebdomadaire : le premier posait la date, celui de la semaine suivante
la relisait et tombait.
"""
from datetime import datetime, timedelta, timezone

import pytest

from falkye.models.base import en_utc


# --- Le helper lui-même ----------------------------------------------------


def test_en_utc_rend_conscient_un_datetime_naif():
    naif = datetime(2026, 9, 1, 12, 0, 0)
    assert en_utc(naif) == datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)


def test_en_utc_laisse_intact_un_datetime_deja_conscient():
    """Ne pas réécrire un fuseau déjà présent : `replace` sur un datetime
    conscient d'un AUTRE fuseau décalerait l'instant de plusieurs heures."""
    montreal = timezone(timedelta(hours=-4))
    conscient = datetime(2026, 9, 1, 12, 0, 0, tzinfo=montreal)
    assert en_utc(conscient) is conscient


def test_en_utc_laisse_passer_labsence():
    assert en_utc(None) is None


# --- Les trois sites qui font le calcul ------------------------------------


def _apres_aller_retour(db_session, objet):
    """Écrit, puis vide le cache d'identité : l'objet est relu depuis SQLite,
    comme le ferait le processus du cycle suivant."""
    db_session.commit()
    db_session.expire_all()
    return objet


def test_besoin_enrichissement_survit_a_une_date_relue(db_session):
    """C'est le défaut exact qui a bloqué le premier envoi réel : le cycle
    tombait au deuxième passage, jamais au premier."""
    from falkye.engine import _besoin_enrichissement
    from falkye.models.base import utcnow
    from falkye.models.company import Company

    company = Company(
        nom_detecte="Exemple inc.",
        nom_detecte_normalise="exemple",
        site_web="https://exemple.test",
        site_web_vérifié_le=utcnow(),
    )
    db_session.add(company)
    _apres_aller_retour(db_session, company)

    assert company.site_web_vérifié_le.tzinfo is None, (
        "si SQLite rendait un jour le fuseau, ce test ne prouverait plus rien"
    )
    assert _besoin_enrichissement(company) is False


def test_une_session_dauthentification_relue_reste_valide(db_session):
    """`SessionAuth.expires_at` est TOUJOURS relu depuis la base : le jeton
    arrive d'un fichier local, jamais d'un objet encore en mémoire."""
    from falkye.auth import Principal, creer_session, resoudre_session
    from falkye.models.profile import Profile

    profile = Profile(courriel="a@exemple.com", nom="Test")
    db_session.add(profile)
    db_session.flush()

    jeton = creer_session(
        db_session, Principal(type="profile", profile=profile), duree=timedelta(hours=1)
    )
    db_session.expire_all()

    assert resoudre_session(db_session, jeton) is not None


def test_la_fraicheur_se_calcule_sur_un_signal_relu(db_session):
    """`freshness_factor` reçoit `Signal.detected_at` directement depuis la
    base à chaque calcul de score."""
    from falkye.models.base import utcnow
    from falkye.scoring import freshness_factor

    naif = utcnow().replace(tzinfo=None)
    assert 0.0 < freshness_factor(naif) <= 1.0
