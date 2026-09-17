"""L'index par MOTS, et le SECOND TEMPS — la clé de récupération qui ne dépend
plus du premier mot.

⚠️ **Le fait qui les fait exister.** `normaliser` remplace l'apostrophe et le
point par une espace, donc le « premier mot » d'un nom est souvent un mot vide :

    "L'INDUSTRIE MONDIALE DU NORD INC."  →  'l industrie mondiale du nord inc'

**Les trois gisements que le plafond de la mesure C a dû refuser — `l`, `s`,
`le` — sont exactement ceux-là.**
"""
from __future__ import annotations

import pytest

from falkye.models.req_entry import REQEntry
from falkye.models.req_mot import REQMot, REQMotFrequence
from falkye.models.req_nom import REQNom
from falkye.sources.column_mapping import normaliser
from falkye.sources.req import (
    DecoupeurDivergent,
    candidats_par_mot_rare,
    construire_index_par_mots,
    mots_du_nom,
    refuser_si_le_decoupeur_diverge,
    resolve_neq_by_name,
)


def test_le_decoupage_est_une_FONCTION_NOMMEE():
    """*Le même des deux côtés, ou le rappel baisse sans qu'une erreur ne se
    produise.*"""
    assert mots_du_nom("l industrie mondiale du nord inc") == [
        "l", "industrie", "mondiale", "du", "nord", "inc",
    ]
    assert mots_du_nom("") == []
    assert mots_du_nom("  ferme   parent  ") == ["ferme", "parent"]


def _entree(db_session, neq, nom, ville=None):
    db_session.add(REQEntry(neq=neq, nom=nom, nom_normalise=normaliser(nom),
                            ville=ville, statut="IMMATRICULÉE"))
    db_session.add(REQNom(neq=neq, nom=nom, nom_normalise=normaliser(nom),
                          statut="V", type_nom="M", gisement="NOM_ASSUJ"))


@pytest.fixture()
def miroir(db_session):
    """Le cas de `l` : le vrai candidat porte un préfixe VIDE, et la tranche
    alphabétique est remplie par d'autres « l … »."""
    _entree(db_session, "1000000001", "L'Industrie Mondiale du Nord inc.")
    for i in range(6):
        _entree(db_session, f"200000000{i}", f"L'Atelier {i} inc.")
    db_session.commit()
    construire_index_par_mots(db_session)
    return db_session


# --- l'index ---------------------------------------------------------------


def test_lindex_porte_un_couple_par_mot_et_par_NEQ(miroir):
    couples = {(m.mot, m.neq) for m in miroir.query(REQMot).all()}
    assert ("industrie", "1000000001") in couples
    assert ("mondiale", "1000000001") in couples
    assert ("l", "1000000001") in couples


def test_la_frequence_dit_le_pouvoir_discriminant(miroir):
    par_mot = {f.mot: f.neqs for f in miroir.query(REQMotFrequence).all()}
    assert par_mot["l"] == 7, par_mot          # tous les NEQ le portent
    assert par_mot["mondiale"] == 1            # un seul
    assert par_mot["atelier"] == 6


def test_un_NEQ_a_trois_noms_portant_le_meme_mot_ne_compte_QUUNE_fois(db_session):
    """*La récupération veut des NEQ candidats, pas des occurrences.*"""
    _entree(db_session, "3000000001", "Construction Alpha inc.")
    for nom in ("Construction Beta inc.", "Construction Gamma inc."):
        db_session.add(REQNom(neq="3000000001", nom=nom,
                              nom_normalise=normaliser(nom), statut="V",
                              type_nom="N", gisement="NOM_ASSUJ"))
    db_session.commit()
    construire_index_par_mots(db_session)
    par_mot = {f.mot: f.neqs for f in db_session.query(REQMotFrequence).all()}
    assert par_mot["construction"] == 1


def test_la_reconstruction_est_TOTALE_jamais_incrementale(miroir):
    """⚠️ *Une reconstruction partielle laisserait une moitié périmée, et c'est
    invisible.*"""
    avant = miroir.query(REQMot).count()
    miroir.query(REQNom).delete()
    miroir.commit()
    construire_index_par_mots(miroir)
    assert avant > 0
    assert miroir.query(REQMot).count() == 0
    assert miroir.query(REQMotFrequence).count() == 0


# --- la récupération par le mot le plus rare -------------------------------


def test_a_frequence_egale_le_mot_le_plus_LONG_gagne(miroir):
    """⚠️ *Départager par ordre alphabétique choisirait « du » plutôt que
    « mondiale » — un tirage promu en critère.* **La longueur est une règle
    énoncée, contestable et reproductible.**"""
    journal: dict = {}
    candidats_par_mot_rare(
        miroir, normaliser("L'Industrie Mondiale du Nord inc."), journal=journal
    )
    assert journal["mot_retenu"] == "industrie", journal


def test_la_recuperation_choisit_le_mot_le_plus_RARE(miroir):
    journal: dict = {}
    candidats = candidats_par_mot_rare(
        miroir, normaliser("L'Industrie Mondiale du Nord inc."), journal=journal
    )
    assert journal["mot_retenu"] in {"industrie", "mondiale", "nord"}
    assert journal["frequence_du_plus_rare"] == 1
    assert [c.neq for c in candidats] == ["1000000001"]


def test_un_vocabulaire_INCONNU_se_dit_autrement_que_AUCUN_CANDIDAT(miroir):
    """*« L'index ne connaît pas ce vocabulaire » et « pas de candidat » sont
    deux échecs différents, et ils appellent deux correctifs différents.*"""
    journal: dict = {}
    assert candidats_par_mot_rare(miroir, "zzyzx quelconque", journal=journal) == []
    assert journal["aucun_mot_a_lindex"] is True


def test_un_mot_trop_courant_est_INTERSECTE_avec_le_deuxieme(db_session, monkeypatch):
    """⚠️ **Le point aveugle, traité plutôt que laissé ouvert** : « les
    entreprises du québec » n'a aucun mot rare."""
    monkeypatch.setattr("falkye.sources.req.MOT_TROP_COURANT", 1)
    _entree(db_session, "4000000001", "Les Entreprises Boreal")
    _entree(db_session, "4000000002", "Les Entreprises Solaris")
    _entree(db_session, "4000000003", "Les Ateliers Boreal")
    db_session.commit()
    construire_index_par_mots(db_session)

    journal: dict = {}
    candidats = candidats_par_mot_rare(
        db_session, normaliser("Les Entreprises Boreal"), journal=journal
    )
    assert journal.get("mot_intersecte"), journal
    assert [c.neq for c in candidats] == ["4000000001"], journal


# --- LE SECOND TEMPS ------------------------------------------------------


def test_le_second_temps_TROUVE_ce_que_le_prefixe_cachait(db_session):
    """⚠️ **Le cœur du correctif.** La borne coupe la tranche des « l … » avant
    d'atteindre le vrai candidat; le mot `mondiale` le retrouve."""
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr("falkye.sources.req.LIMITE_CANDIDATS_PAR_NOM", 3)
    try:
        # La tranche alphabétique : « l atelier … » trie avant « l industrie … »
        for i in range(5):
            _entree(db_session, f"500000000{i}", f"L'Atelier {i} inc.")
        _entree(db_session, "5100000000", "L'Industrie Mondiale du Nord inc.")
        db_session.commit()
        construire_index_par_mots(db_session)

        borne = resolve_neq_by_name(
            db_session, "L'Industrie Mondiale du Nord inc.", elargir=False
        )
        assert "5100000000" not in {m.entry.neq for m in borne}, (
            "le décor ne reproduit pas la coupe — ce test ne verrouille rien"
        )

        elargi = resolve_neq_by_name(db_session, "L'Industrie Mondiale du Nord inc.")
        assert elargi[0].entry.neq == "5100000000"
        assert elargi[0].score == 100.0
    finally:
        monkeypatch.undo()


def test_le_second_temps_NE_SEXECUTE_PAS_quand_le_premier_reussit(miroir):
    """⚠️ **La non-régression est STRUCTURELLE** : les 805 dossiers retenus ne
    voient jamais cette branche."""
    journal: dict = {}
    matches = resolve_neq_by_name(
        miroir, "L'Industrie Mondiale du Nord inc.", journal=journal
    )
    assert matches[0].score == 100.0
    assert "second_temps" not in journal, journal


def test_le_second_temps_AJOUTE_sans_remplacer(db_session):
    """*Un candidat que le préfixe trouvait et que les mots ne trouvent pas ne
    doit pas disparaître.*"""
    _entree(db_session, "6000000001", "Boreal Transport")
    _entree(db_session, "6000000002", "Boreal Logistique")
    db_session.commit()
    construire_index_par_mots(db_session)
    matches = resolve_neq_by_name(db_session, "Boreal")
    assert {m.entry.neq for m in matches} == {"6000000001", "6000000002"}


def test_elargir_False_rend_letat_DAVANT(miroir):
    """*Pour mesurer ce que le correctif change, il faut pouvoir le couper.*"""
    journal: dict = {}
    resolve_neq_by_name(miroir, "zzyzx introuvable", elargir=False, journal=journal)
    assert "second_temps" not in journal


# --- LE TÉMOIN DU DÉCOUPEUR ----------------------------------------------


def test_le_temoin_passe_sur_un_index_sain(miroir):
    refuser_si_le_decoupeur_diverge(miroir)  # ne lève pas


def test_le_temoin_REFUSE_si_les_deux_decoupeurs_divergent(miroir, monkeypatch):
    """⚠️ **La seule dégradation silencieuse que l'index puisse subir.** *Une
    divergence ne lève nulle part ailleurs — elle fait seulement baisser le
    rappel, et le chiffre sera attribué à autre chose.*"""
    monkeypatch.setattr("falkye.sources.req.mots_du_nom",
                        lambda nom_norm: ["zzyzx-inexistant"])
    with pytest.raises(DecoupeurDivergent) as exc:
        refuser_si_le_decoupeur_diverge(miroir)
    assert "ne découpent pas pareil" in str(exc.value)
