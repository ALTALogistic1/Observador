"""La reprise du journal de repli — les quatre règles, une par bloc.

Le fichier est le SEUL témoin des pannes où la base était injoignable. Le
2026-09-08 en donne la preuve : le déclenchement de 14 h 17 UTC n'a laissé
aucune trace en base, seulement deux lignes dans ce fichier.

D'où quatre exigences, et un test pour chacune :

1. le format est un contrat — une ligne illisible est sautée, comptée,
   signalée, jamais fatale;
2. la reprise est relançable sans perte;
3. le fichier n'est jamais consommé ni déplacé;
4. absent et vide ne disent pas la même chose.
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import select

from falkye.exploitation import FORMAT_REPLI
from falkye.models.journal_exploitation import JournalExploitation
from falkye.reconciliation_repli import (
    EtatJournal,
    identifiant_de,
    reconcilier_journal_repli,
)


def _ligne(evenement="cycle_debut", **extra):
    base = {
        "id": extra.pop("id", "a" * 32),
        "format": FORMAT_REPLI,
        "moment": "2026-09-08T14:17:57.123456+00:00",
        "evenement": evenement,
        "detail": None,
        "version": "e6308aa",
        "cause_du_repli": "OperationalError: quota de lectures atteint",
    }
    base.update(extra)
    return base


@pytest.fixture()
def journal(tmp_path):
    return tmp_path / "journal-repli.jsonl"


def _ecrire(chemin, lignes):
    chemin.write_text(
        "".join(json.dumps(l, ensure_ascii=False) + "\n" for l in lignes), encoding="utf-8"
    )


# --- Règle 4 : absent ≠ vide ------------------------------------------------


def test_un_fichier_absent_dit_je_ne_sais_pas(db_session, journal):
    """Disque plein, chemin changé, permissions. Sans cette distinction, la
    réconciliation devient un cycle qui réussit à vide."""
    rapport = reconcilier_journal_repli(db_session, journal)

    assert rapport.etat is EtatJournal.INTROUVABLE
    assert rapport.raison
    assert "INTROUVABLE" in rapport.resume_lisible()


def test_un_fichier_vide_dit_rien_a_reconcilier(db_session, journal):
    journal.write_text("", encoding="utf-8")

    rapport = reconcilier_journal_repli(db_session, journal)

    assert rapport.etat is EtatJournal.VIDE
    assert rapport.etat is not EtatJournal.INTROUVABLE
    assert "rien à reprendre" in rapport.resume_lisible()


def test_un_chemin_illisible_dit_je_ne_sais_pas_pas_vide(db_session, tmp_path):
    """Un répertoire à la place du fichier : `exists()` répond oui, la lecture
    échoue. C'est « je ne sais pas », jamais « rien à réconcilier »."""
    repertoire = tmp_path / "journal-repli.jsonl"
    repertoire.mkdir()

    rapport = reconcilier_journal_repli(db_session, repertoire)

    assert rapport.etat is EtatJournal.INTROUVABLE
    assert rapport.raison


# --- Règle 1 : une ligne cassée n'emporte pas les autres --------------------


def test_une_ligne_illisible_est_sautee_comptee_et_situee(db_session, journal):
    """Le cas nominal : une écriture interrompue tronque la DERNIÈRE ligne. Une
    réconciliation que son propre fichier peut tuer ne sert à rien le jour où on
    en a besoin."""
    journal.write_text(
        json.dumps(_ligne(id="b" * 32)) + "\n"
        + '{"moment": "2026-09-08T14:1\n'  # tronquée
        + json.dumps(_ligne(id="c" * 32, evenement="cycle_echec")) + "\n",
        encoding="utf-8",
    )

    rapport = reconcilier_journal_repli(db_session, journal)

    assert rapport.lignes_illisibles == 1
    assert rapport.numeros_illisibles == [2]
    assert rapport.lignes_reprises == 2  # les deux saines sont passées
    assert "ILLISIBLE" in rapport.resume_lisible()


def test_un_format_plus_recent_est_laisse_au_lecteur_qui_le_comprend(db_session, journal):
    """Ne pas deviner : la ligne est comptée et reste dans le fichier."""
    _ecrire(journal, [_ligne(format=999)])

    rapport = reconcilier_journal_repli(db_session, journal)

    assert rapport.lignes_format_inconnu == 1
    assert rapport.lignes_reprises == 0
    assert journal.exists()


def test_un_evenement_inconnu_ne_fait_pas_lever(db_session, journal):
    _ecrire(journal, [_ligne(evenement="evenement_qui_nexiste_pas")])

    rapport = reconcilier_journal_repli(db_session, journal)

    assert rapport.lignes_illisibles == 1
    assert rapport.lignes_reprises == 0


# --- Règle 2 : relançable sans perte ---------------------------------------


def test_une_seconde_reprise_ne_duplique_rien(db_session, journal):
    _ecrire(journal, [_ligne(id="d" * 32)])

    premier = reconcilier_journal_repli(db_session, journal)
    second = reconcilier_journal_repli(db_session, journal)

    assert premier.lignes_reprises == 1
    assert second.lignes_reprises == 0
    assert second.lignes_deja_reprises == 1
    lignes = db_session.execute(
        select(JournalExploitation).where(JournalExploitation.repli_id == "d" * 32)
    ).scalars().all()
    assert len(lignes) == 1


def test_deux_lignes_identiques_du_meme_fichier_ne_cassent_pas_le_lot(db_session, journal):
    """Même empreinte, donc la seconde doit être vue comme déjà reprise. Sinon
    l'insertion viole l'unicité et emporte tout le lot."""
    sans_id = {k: v for k, v in _ligne().items() if k not in {"id", "format"}}
    _ecrire(journal, [sans_id, dict(sans_id)])

    rapport = reconcilier_journal_repli(db_session, journal)

    assert rapport.lignes_reprises == 1
    assert rapport.lignes_deja_reprises == 1


# --- Règle 3 : marquer, jamais consommer -----------------------------------


def test_le_fichier_nest_ni_efface_ni_vide_ni_deplace(db_session, journal):
    """Il est le seul témoin des pannes où la base était muette. Le consommer en
    le détruisant supprimerait la preuve au moment où l'on s'en sert."""
    _ecrire(journal, [_ligne(id="e" * 32)])
    avant = journal.read_bytes()

    reconcilier_journal_repli(db_session, journal)

    assert journal.exists()
    assert journal.read_bytes() == avant


# --- Le format 1, celui des deux lignes qui existent sur l'hôte -------------


def test_une_ligne_de_format_1_est_reprise_par_empreinte(db_session, journal):
    """Les deux lignes du 2026-09-08 à 14 h 17 UTC n'ont pas d'identifiant : le
    format ne l'avait pas prévu. Les sauter perdrait la seule trace de ce
    déclenchement; les reprendre sans identité créerait un doublon par cycle."""
    sans_id = {k: v for k, v in _ligne().items() if k not in {"id", "format"}}
    _ecrire(journal, [sans_id])

    premier = reconcilier_journal_repli(db_session, journal)
    second = reconcilier_journal_repli(db_session, journal)

    assert premier.lignes_reprises == 1
    assert premier.lignes_identifiees_par_empreinte == 1
    assert second.lignes_deja_reprises == 1


def test_lempreinte_est_stable_et_lidentifiant_ecrit_a_priorite():
    sans_id = {"moment": "m", "evenement": "cycle_debut", "detail": None}
    assert identifiant_de(sans_id) == identifiant_de(dict(sans_id))
    assert identifiant_de(sans_id)[1] is True
    assert identifiant_de({**sans_id, "id": "f" * 32}) == ("f" * 32, False)


def test_la_cause_du_repli_voyage_avec_la_ligne(db_session, journal):
    """Sans elle, une ligne rapatriée serait indiscernable d'une ligne écrite
    normalement — et « la base était muette à ce moment-là » se perdrait."""
    _ecrire(journal, [_ligne(id="0" * 32, detail="cycle interrompu")])

    reconcilier_journal_repli(db_session, journal)

    ligne = db_session.execute(
        select(JournalExploitation).where(JournalExploitation.repli_id == "0" * 32)
    ).scalar_one()
    assert "cycle interrompu" in ligne.detail
    assert "[repli :" in ligne.detail
    assert "quota de lectures" in ligne.detail
