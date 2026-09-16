"""Le croisement compte-t-il des dossiers, et lit-il le registre plutôt que de le déduire?

**Trois pièges, et chacun a son test.**

1. **Un dossier à deux sources compte dans les deux colonnes.** *Un total de
   colonnes n'est pas un total de dossiers*, et l'outil doit le dire plutôt que
   de laisser additionner.
2. **Un dossier SANS signal n'a aucune source** — il échappe entièrement au
   croisement, et son absence doit être comptée. *L'absence de mesure n'est pas
   une mesure nulle.*
3. ⚠️ **`territoire` et `region` sont deux champs différents.** `region` est du
   texte libre et ne filtre rien; `territoire: null` fait TOUT retenir. *Une
   sortie qui les confondrait ferait lire « Québec » là où rien n'est filtré.*
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from falkye.models.company import Company
from falkye.models.signal import Signal
from outils import sources_des_non_resolues


@pytest.fixture()
def population(db_session, monkeypatch):
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")

    def c(nom):
        return Company(neq=None, nom_detecte=nom, nom_detecte_normalise=nom.lower())

    deux_sources, une_source, orphelin = c("Deux Sources"), c("Une Source"), c("Sans Signal")
    resolu = Company(neq="9999999999", nom_detecte="Résolu", nom_detecte_normalise="resolu")
    db_session.add_all([deux_sources, une_source, orphelin, resolu])
    db_session.flush()

    def s(company, source, ref):
        return Signal(company_id=company.id, source_id=source,
                      signal_type_id="x", source_ref=ref,
                      detected_at=datetime(2026, 9, 1, tzinfo=timezone.utc), champs={})

    db_session.add_all([
        s(deux_sources, "eimt", "a"), s(deux_sources, "contrats_federaux", "b"),
        s(une_source, "eimt", "c"),
        s(resolu, "eimt", "d"),   # résolu : ne doit PAS entrer dans le compte
    ])
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def test_seuls_les_dossiers_SANS_NEQ_sont_comptes(population, capsys):
    assert sources_des_non_resolues.main([]) == 0
    sortie = capsys.readouterr().out
    assert "dossiers sans NEQ            : 3" in sortie, (
        "le dossier RÉSOLU a été compté — la population n'est pas la bonne"
    )


def test_un_dossier_sans_signal_est_compte_a_part(population, capsys):
    """*Il échappe entièrement au croisement, et son absence doit être dite.*"""
    assert sources_des_non_resolues.main([]) == 0
    sortie = capsys.readouterr().out
    assert "dont AUCUN signal rattaché   : 1" in sortie
    assert "échappe entièrement au croisement" in sortie


def test_le_double_comptage_est_annonce(population, capsys):
    """**Un total de colonnes n'est pas un total de dossiers.**"""
    assert sources_des_non_resolues.main([]) == 0
    sortie = capsys.readouterr().out
    assert "eimt" in sortie and "contrats_federaux" in sortie
    assert "LA SOMME DES COLONNES CI-DESSOUS DÉPASSE" in sortie, (
        "un dossier à deux sources est compté deux fois sans que la sortie le dise"
    )


def test_le_registre_est_LU_et_les_deux_champs_distingues(population, capsys):
    """⚠️ `eimt` déclare `territoire: ['Québec']` et `region: Canada`.
    `contrats_federaux` déclare `territoire: null`.

    *Si la sortie confondait les deux champs, on lirait « Canada » comme un
    filtre, ou « Québec » là où rien n'est filtré.*
    """
    assert sources_des_non_resolues.main([]) == 0
    sortie = capsys.readouterr().out
    assert "territoire (FILTRE)" in sortie and "region (TEXTE)" in sortie
    assert "AUCUN" in sortie, "une source sans territoire doit être marquée AUCUN"
    assert "Québec" in sortie


def test_ce_que_la_mesure_ne_peut_pas_dire_est_ecrit(population, capsys):
    """*Une source pancanadienne ne prouve pas qu'un dossier est hors Québec.*
    Et pour l'EIMT, le filtre porte sur la province de l'EMPLOI, pas sur le lieu
    d'immatriculation — la distinction même sur laquelle porte l'hypothèse."""
    assert sources_des_non_resolues.main([]) == 0
    sortie = capsys.readouterr().out
    assert "NE PROUVE PAS qu'un dossier est hors Québec" in sortie
    assert "PROVINCE DE L'EMPLOI" in sortie
    assert "DÉCISION DE PRODUIT" in sortie


def test_il_NECRIT_RIEN(population):
    from sqlalchemy import select

    avant = {c.id: c.neq for c in population.execute(select(Company)).scalars().all()}
    assert sources_des_non_resolues.main([]) == 0
    population.expire_all()
    apres = {c.id: c.neq for c in population.execute(select(Company)).scalars().all()}
    assert avant == apres
