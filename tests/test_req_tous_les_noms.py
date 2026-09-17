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


def test_TOUS_les_statuts_entrent_et_le_statut_est_porte_en_colonne(db_session, tmp_path):
    """⚠️ **La décision a changé le 2026-09-17** *(Alexandre)*.

    Avant : seuls les noms `STAT_NOM='V'` entraient. *Le motif était bon — un
    nom retiré ferait apparier une entreprise sous un nom qu'elle n'utilise
    plus.* **Mais le filtre jetait 3 129 272 lignes, et le produit n'avait aucun
    moyen de réviser la décision sans réimport.**

    Maintenant : **tout entre, et le statut est écrit en colonne.** *La règle qui
    dit quoi faire d'un nom retiré se pose dans le moteur, pas dans le
    chargeur* — et elle se change sans relire 630 Mo.
    """
    zf = _zip_nom([
        ["1111111111", "Nom Actuel inc.", "V", "M", "2020-01-01", ""],
        ["1111111111", "Ancien Nom inc.", "A", "M", "1998-01-01", "2020-01-01"],
    ], tmp_path)
    assert _charger_tous_les_noms(zf, db_session) == 2
    par_statut = {n.statut: n.nom for n in db_session.query(REQNom).all()}
    assert par_statut == {"V": "Nom Actuel inc.", "A": "Ancien Nom inc."}


def test_le_filtre_par_statut_reste_DISPONIBLE(db_session, tmp_path):
    """*La décision est révisable dans les deux sens* — `statuts_retenus` rend
    l'ancien comportement sans toucher au chargeur."""
    zf = _zip_nom([
        ["1111111111", "Nom Actuel inc.", "V", "M", "2020-01-01", ""],
        ["1111111111", "Ancien Nom inc.", "A", "M", "1998-01-01", "2020-01-01"],
    ], tmp_path)
    assert _charger_tous_les_noms(
        zf, db_session, statuts_retenus=frozenset({"V"})
    ) == 1
    assert db_session.query(REQNom).one().nom == "Nom Actuel inc."


def test_le_gisement_est_porte_en_colonne(db_session, tmp_path):
    """*Quatre gisements dans une table : savoir d'où vient une forme est ce qui
    permet de peser sa valeur plus tard.*"""
    zf = _zip_nom([["1111111111", "Nom Actuel inc.", "V", "M", "2020-01-01", ""]],
                  tmp_path)
    assert _charger_tous_les_noms(zf, db_session) == 1
    assert db_session.query(REQNom).one().gisement == "NOM_ASSUJ"


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


# ---------------------------------------------------------------------------
# UN NEQ, UNE ENTITÉ — le score et l'ambiguïté se comptent sur le NEQ
# ---------------------------------------------------------------------------


def test_le_score_dun_NEQ_est_le_MEILLEUR_de_ses_noms(db_session):
    """Sans ça, la porte serait ouverte et le seuil infranchissable : la
    récupération trouverait l'entreprise par son nom commercial, puis la
    comparerait à sa dénomination sociale numérique."""
    from falkye.sources.req import resolve_neq_by_name

    db_session.add(REQEntry(
        neq="1111111111", nom="9224-5842 QUÉBEC INC.",
        nom_normalise="9224 5842 quebec inc", statut="immatriculee",
    ))
    db_session.add(REQNom(
        neq="1111111111", nom_normalise="ferme m g bellavance",
        nom="Ferme M.G. Bellavance", statut="V", type_nom="N",
    ))
    db_session.commit()
    matches = resolve_neq_by_name(db_session, "Ferme M.G. Bellavance")
    assert len(matches) == 1
    assert matches[0].entry.neq == "1111111111"
    assert matches[0].score == 100.0


def test_deux_noms_du_MEME_NEQ_ne_font_pas_une_ambiguite(db_session):
    """« Une entreprise n'a pas plusieurs identités parce qu'elle a plusieurs
    noms. » Deux noms qui se disputent la première place, c'est la même
    entreprise deux fois."""
    from falkye.resolution import neq_retenu
    from falkye.sources.req import resolve_neq_by_name

    db_session.add(REQEntry(
        neq="1111111111", nom="Construction Pierre Robert inc.",
        nom_normalise="construction pierre robert inc", statut="immatriculee",
    ))
    db_session.add(REQNom(
        neq="1111111111", nom_normalise="construction pierre robert",
        nom="Construction Pierre Robert", statut="V", type_nom="N",
    ))
    db_session.commit()
    matches = resolve_neq_by_name(db_session, "Construction Pierre Robert inc.")
    assert len(matches) == 1          # UN candidat, pas deux
    assert neq_retenu(matches) == "1111111111"


def test_deux_NEQ_DIFFERENTS_restent_une_ambiguite(db_session):
    """Le regroupement ne doit pas absorber une vraie ambiguïté."""
    from falkye.resolution import neq_retenu
    from falkye.sources.req import resolve_neq_by_name

    for neq in ("1111111111", "2222222222"):
        db_session.add(REQEntry(
            neq=neq, nom="Transport Gagnon inc.",
            nom_normalise="transport gagnon inc", statut="immatriculee",
        ))
    db_session.commit()
    matches = resolve_neq_by_name(db_session, "Transport Gagnon inc.")
    assert len(matches) == 2
    assert neq_retenu(matches) is None


def test_le_meilleur_nom_lemporte_meme_sil_nest_pas_lelu(db_session):
    """Le nom élu peut scorer mal et un nom alternatif très bien : c'est le
    meilleur des deux qui représente l'entité."""
    from falkye.sources.req import resolve_neq_by_name

    db_session.add(REQEntry(
        neq="1111111111", nom="9169-9587 QUÉBEC INC.",
        nom_normalise="9169 9587 quebec inc", statut="immatriculee",
    ))
    db_session.add(REQNom(
        neq="1111111111", nom_normalise="ferme a lapierre fils",
        nom="Ferme A. Lapierre & Fils", statut="V", type_nom="N",
    ))
    db_session.add(REQNom(
        neq="1111111111", nom_normalise="9169 9587 quebec inc",
        nom="9169-9587 QUÉBEC INC.", statut="V", type_nom="M",
    ))
    db_session.commit()
    matches = resolve_neq_by_name(db_session, "Ferme A. Lapierre & Fils")
    assert matches[0].score == 100.0
    # Et le portrait affiche la DÉNOMINATION LÉGALE, jamais le nom apparié.
    assert matches[0].entry.nom == "9169-9587 QUÉBEC INC."
