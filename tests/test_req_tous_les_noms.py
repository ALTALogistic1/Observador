"""Le chargeur garde TOUS les noms en vigueur — et la récupération les voit."""
import io
import zipfile

import pytest

from falkye.models.req_entry import REQEntry
from falkye.models.req_nom import REQNom
from falkye.sources.req import _charger_tous_les_noms, candidats_par_nom

_ENTETE = "NEQ,NOM_ASSUJ,STAT_NOM,TYP_NOM_ASSUJ,DAT_INIT_NOM_ASSUJ,DAT_FIN_NOM_ASSUJ"


def _zip_nom(lignes, tmp_path):
    chemin = tmp_path / "noms.zip"
    contenu = "\n".join([_ENTETE] + [",".join(l) for l in lignes])
    with zipfile.ZipFile(chemin, "w") as zf:
        zf.writestr("Nom.csv", contenu)
    return zipfile.ZipFile(chemin)


def test_tous_les_noms_en_vigueur_dun_neq_sont_gardes(db_session, tmp_path):
    """C'est LE correctif : le chargeur élisait un nom et jetait les autres."""
    zf = _zip_nom([
        ["1111111111", "9224-5842 QUÉBEC INC.", "V", "M", "2010-01-01", ""],
        ["1111111111", "Ferme M.G. Bellavance", "V", "N", "2010-01-01", ""],
    ], tmp_path)
    assert _charger_tous_les_noms(zf, db_session) == 2
    noms = db_session.query(REQNom).filter_by(neq="1111111111").all()
    assert {n.nom_normalise for n in noms} == {"9224 5842 quebec inc", "ferme m g bellavance"}


def test_seuls_les_noms_en_vigueur_entrent(db_session, tmp_path):
    zf = _zip_nom([
        ["1111111111", "Nom Actuel inc.", "V", "M", "2020-01-01", ""],
        ["1111111111", "Ancien Nom inc.", "A", "M", "1998-01-01", "2020-01-01"],
    ], tmp_path)
    assert _charger_tous_les_noms(zf, db_session) == 1
    assert db_session.query(REQNom).one().nom == "Nom Actuel inc."


def test_un_nom_qui_se_normalise_en_VIDE_est_refuse(db_session, tmp_path):
    """Il n'apparierait rien et apparierait TOUT — le défaut du 15 septembre."""
    zf = _zip_nom([
        ["1111111111", "...", "V", "M", "2020-01-01", ""],
        ["1111111111", "Vrai Nom inc.", "V", "N", "2020-01-01", ""],
    ], tmp_path)
    assert _charger_tous_les_noms(zf, db_session) == 1


def test_la_meme_graphie_sous_deux_types_nentre_quune_fois(db_session, tmp_path):
    """La clé est composite : un doublon ferait échouer l'insertion du lot."""
    zf = _zip_nom([
        ["1111111111", "Gagnon inc.", "V", "M", "2020-01-01", ""],
        ["1111111111", "GAGNON INC", "V", "N", "2020-01-01", ""],
    ], tmp_path)
    assert _charger_tous_les_noms(zf, db_session) == 1


def test_un_REIMPORT_ne_leve_pas(db_session, tmp_path):
    """Avec `add` ligne à ligne, la seconde passe levait IntegrityError et
    faisait tomber l'import entier."""
    zf = _zip_nom([["1111111111", "Gagnon inc.", "V", "M", "2020-01-01", ""]], tmp_path)
    assert _charger_tous_les_noms(zf, db_session) == 1
    zf2 = _zip_nom([["1111111111", "Gagnon inc.", "V", "M", "2020-01-01", ""]], tmp_path)
    _charger_tous_les_noms(zf2, db_session)      # ne lève pas
    assert db_session.query(REQNom).count() == 1


def test_un_nom_sans_neq_ou_sans_texte_est_saute(db_session, tmp_path):
    zf = _zip_nom([
        ["", "Sans NEQ inc.", "V", "M", "2020-01-01", ""],
        ["1111111111", "", "V", "M", "2020-01-01", ""],
    ], tmp_path)
    assert _charger_tous_les_noms(zf, db_session) == 0


def test_la_recuperation_trouve_par_un_nom_ALTERNATIF(db_session, tmp_path):
    """Le cœur du pont : `Ferme M.G. Bellavance` doit mener à `9224-5842`."""
    db_session.add(REQEntry(
        neq="1111111111", nom="9224-5842 QUÉBEC INC.",
        nom_normalise="9224 5842 quebec inc", statut="immatriculee",
    ))
    db_session.add(REQNom(
        neq="1111111111", nom_normalise="ferme m g bellavance",
        nom="Ferme M.G. Bellavance", statut="V", type_nom="N",
    ))
    db_session.commit()
    candidats = candidats_par_nom(db_session, "ferme m g bellavance")
    assert [c.neq for c in candidats] == ["1111111111"]
    # Et le nom AFFICHÉ reste la dénomination sociale : la table sert à TROUVER,
    # jamais à NOMMER.
    assert candidats[0].nom == "9224-5842 QUÉBEC INC."


def test_un_neq_deja_trouve_par_REQEntry_nest_pas_doublonne(db_session, tmp_path):
    db_session.add(REQEntry(
        neq="1111111111", nom="Gagnon inc.", nom_normalise="gagnon inc",
        statut="immatriculee",
    ))
    db_session.add(REQNom(
        neq="1111111111", nom_normalise="gagnon inc", nom="Gagnon inc.",
        statut="V", type_nom="M",
    ))
    db_session.commit()
    candidats = candidats_par_nom(db_session, "gagnon inc")
    assert len(candidats) == 1


def test_la_borne_sapplique_au_TOTAL_pas_a_chaque_source(db_session, tmp_path):
    """Sinon `limite` ne bornerait plus rien et le coût doublerait en silence."""
    for i in range(6):
        db_session.add(REQEntry(
            neq=f"11111111{i:02d}", nom=f"Gagnon {i} inc.",
            nom_normalise=f"gagnon {i} inc", statut="immatriculee",
        ))
    for i in range(6, 12):
        db_session.add(REQEntry(
            neq=f"11111111{i:02d}", nom=f"Autre {i}", nom_normalise=f"autre {i}",
            statut="immatriculee",
        ))
        db_session.add(REQNom(
            neq=f"11111111{i:02d}", nom_normalise=f"gagnon {i} inc",
            nom=f"Gagnon {i} inc.", statut="V", type_nom="N",
        ))
    db_session.commit()
    assert len(candidats_par_nom(db_session, "gagnon 0 inc", limite=4)) == 4
