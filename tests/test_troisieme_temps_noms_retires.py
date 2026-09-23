"""Le TROISIÈME TEMPS — les noms retirés, consultés en dernier.

⚠️ **Décision d'Alexandre du 23 septembre 2026, registre D52.** *« `resolve_neq_
by_name` ne consulte les noms retirés que si aucun nom en vigueur n'a trouvé
l'entreprise. Je ne plafonne pas les scores : ça ferait perdre des changements
de nom qui sont justes. »*

**Ce que ces tests verrouillent :** que le troisième temps ne puisse RIEN faire
perdre, et qu'un code de statut INCONNU soit traité comme retiré — conservateur,
parce que le coût d'une erreur y est borné.
"""
from __future__ import annotations

import pytest

from falkye.models.req_entry import REQEntry
from falkye.models.req_nom import REQNom
from falkye.sources.column_mapping import normaliser
from falkye.sources.req import nom_retire, resolve_neq_by_name


@pytest.mark.parametrize("statut, attendu", [
    ("V", False), ("v", False), (" V ", False),
    ("A", True), ("F", True),
    (None, False), ("", False), ("?", False),
    # ⚠️ Un code INCONNU compte comme retiré — le coût est borné, puisqu'il
    # revient au troisième temps si rien d'autre ne trouve l'entreprise.
    ("Z", True), ("XX", True),
])
def test_un_code_inconnu_compte_comme_RETIRE(statut, attendu):
    assert nom_retire(statut) is attendu


def test_le_statut_non_qualifie_n_est_PAS_un_nom_retiré():
    """*`NOM_ETAB` et `DENOMN_SOC` n'ont aucune colonne de statut.* **« Pas
    qualifié » et « retiré » ne se confondent pas** — les confondre écarterait
    125 767 formes que personne n'a dites périmées."""
    from falkye.sources.req import STATUT_NON_QUALIFIE

    assert nom_retire(STATUT_NON_QUALIFIE) is False


def _registre(db_session, lignes):
    """`lignes` : (neq, dénomination élue, [(autre nom, statut)])."""
    for neq, elue, autres in lignes:
        db_session.add(REQEntry(neq=neq, nom=elue, nom_normalise=normaliser(elue),
                                statut="immatriculee"))
        for nom, statut in autres:
            db_session.add(REQNom(neq=neq, nom=nom, nom_normalise=normaliser(nom),
                                  statut=statut, type_nom="NOM", gisement="NOM_ASSUJ"))
    db_session.commit()


def test_un_nom_RETIRE_ne_trouve_plus_quand_un_nom_EN_VIGUEUR_trouve(db_session):
    """⚠️ **Le seul cas où la règle change l'issue.** *Deux NEQ portent la même
    forme : l'un l'a retirée, l'autre l'a en vigueur.* **Avant, le premier
    pouvait gagner; désormais il n'est même pas consulté.**"""
    _registre(db_session, [
        ("1700000001", "Carbotech Innovation Inc.", [("Zibeline Robotique inc", "A")]),
        ("1700000002", "Zibeline Robotique inc", [("Zibeline Robotique inc", "V")]),
    ])
    matches = resolve_neq_by_name(db_session, "Zibeline Robotique inc")
    assert matches[0].entry.neq == "1700000002", "le porteur EN VIGUEUR"
    assert "1700000001" not in [m.entry.neq for m in matches[:1]]


def test_le_troisieme_temps_REND_le_nom_retiré_quand_rien_d_autre_ne_trouve(db_session):
    """*157 des 208 dossiers du 22 septembre sont posés sur LEUR PROPRE ancien
    nom.* **Aucun ne doit se perdre.**"""
    _registre(db_session, [
        ("1700000003", "Les Entreprises Douglas Powertech inc.",
         [("Tannerie Orfevre Canada inc", "A")]),
    ])
    matches = resolve_neq_by_name(db_session, "Tannerie Orfevre Canada inc")
    assert matches and matches[0].entry.neq == "1700000003"
    assert matches[0].score >= 92.0, "⚠️ et SANS plafond — la forme écartée est le plafond"


def test_la_regle_ne_peut_RIEN_faire_perdre(db_session):
    """⚠️ **Structurel, pas mesuré.** *Pour un même dossier, ce que la nouvelle
    règle retient est ce que l'ancienne retenait, ou mieux* — écarter des formes
    ne peut qu'abaisser des scores, et le troisième temps rejoue l'ancien
    comportement quand rien n'est retenu."""
    from falkye.resolution import neq_retenu

    _registre(db_session, [
        ("1700000004", "Fromagerie Vercheres inc", [("Fromagerie Vercheres inc", "A")]),
        ("1700000005", "Chocolaterie Lointaine inc", [("Chocolaterie Lointaine", "V")]),
    ])
    for nom in ("Fromagerie Vercheres inc", "Chocolaterie Lointaine inc"):
        avant = neq_retenu(resolve_neq_by_name(db_session, nom,
                                               retires_en_dernier=False))
        apres = neq_retenu(resolve_neq_by_name(db_session, nom))
        assert not (avant is not None and apres is None), (
            f"« {nom} » perdrait son NEQ — impossible par construction")


def test_le_drapeau_rejoue_le_comportement_du_17_au_22_septembre(db_session):
    """*`retires_en_dernier=False` existe pour qu'une mesure compare les deux
    règles par un APPEL, jamais par une copie du scoreur.*"""
    _registre(db_session, [
        ("1700000006", "Carbotech Innovation Inc.", [("Zibeline Robotique inc", "A")]),
        ("1700000007", "Zibeline Robotique inc", [("Zibeline Robotique inc", "V")]),
    ])
    ancien = resolve_neq_by_name(db_session, "Zibeline Robotique inc",
                                 retires_en_dernier=False)
    assert {m.entry.neq for m in ancien[:2]} == {"1700000006", "1700000007"}, (
        "les deux se disputaient la tête avant la règle")


def test_le_journal_dit_QUAND_le_troisieme_temps_a_servi(db_session):
    """*Un temps qui ne s'exécute que parfois doit dire quand* — sinon on ne peut
    pas savoir ce qu'une mesure a réellement emprunté."""
    _registre(db_session, [
        ("1700000008", "Papeterie Lointaine inc", [("Serrurerie Orfevre inc", "A")]),
    ])
    journal: dict = {}
    resolve_neq_by_name(db_session, "Serrurerie Orfevre inc", journal=journal)
    assert journal.get("troisieme_temps") is True
