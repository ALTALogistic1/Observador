"""Ce que le statut laisserait debout, sur les égalités et sur tous les ambigus.

⚠️ **Ce que ces tests verrouillent : que DEUX exclusions restent deux.** *« Ne
garder que les immatriculées » et « n'écarter que les radiées » ne sont pas la
même règle, et `ni` est exactement ce qui les sépare.* **Les fondre en une
colonne ferait passer un choix pour un fait.**
"""
from __future__ import annotations

import datetime as _dt

import pytest

from falkye.models.company import Company
from falkye.models.req_entry import REQEntry
from falkye.models.signal import Signal
from falkye.sources.column_mapping import normaliser
from outils import statut_sur_les_egalites as outil
from tests.conftest import comptes_de_la_ligne as _comptes


class _Match:
    def __init__(self, statut, score=100.0):
        self.entry = type("E", (), {"statut": statut})()
        self.score = score


# ---------------------------------------------------------------------------
# L'ÉGALITÉ STRICTE, ET LES DEUX EXCLUSIONS
# ---------------------------------------------------------------------------

def test_l_egalite_stricte_peut_compter_PLUS_de_deux_candidats():
    groupe = outil.ex_aequo([_Match("immatriculee", 100.0), _Match("radiee", 100.0),
                             _Match("ni", 100.0), _Match("immatriculee", 95.0)])
    assert len(groupe) == 3


def test_sans_candidat_l_egalite_est_vide_et_ne_leve_pas():
    assert outil.ex_aequo([]) == []


@pytest.mark.parametrize("statuts, exclusion, attendu", [
    # ⚠️ **Le cas qui sépare les deux règles** : un immatriculé et un `ni`.
    (["immatriculee", "ni"], outil.GARDER_IMMATRICULEES, outil.UN_SEUL),
    (["immatriculee", "ni"], outil.ECARTER_RADIEES, outil.PLUSIEURS),
    # Un immatriculé et un radié : les deux règles s'accordent.
    (["immatriculee", "radiee"], outil.GARDER_IMMATRICULEES, outil.UN_SEUL),
    (["immatriculee", "radiee"], outil.ECARTER_RADIEES, outil.UN_SEUL),
    # ⚠️ L'exclusion VIDE le lot — un résultat, jamais un cas manquant.
    (["radiee", "radiee"], outil.GARDER_IMMATRICULEES, outil.AUCUN),
    (["radiee", "radiee"], outil.ECARTER_RADIEES, outil.AUCUN),
    # `ni` seul : écarté par la stricte, gardé par l'autre.
    (["ni", "radiee"], outil.GARDER_IMMATRICULEES, outil.AUCUN),
    (["ni", "radiee"], outil.ECARTER_RADIEES, outil.UN_SEUL),
    (["immatriculee", "immatriculee"], outil.GARDER_IMMATRICULEES, outil.PLUSIEURS),
])
def test_les_deux_exclusions_ne_sont_PAS_la_meme_regle(statuts, exclusion, attendu):
    assert outil.ce_qui_reste([_Match(s) for s in statuts], exclusion) == attendu


def test_ni_et_ai_ne_sont_JAMAIS_comptes_avec_les_immatriculees():
    """⚠️ *`falkye/resolution.py` transforme tout ce qui n'est pas `radiee` en
    `IMMATRICULEE` sur le dossier. Ici, non.*"""
    for autre in ("ni", "ai", "zz"):
        assert outil.ce_qui_reste(
            [_Match(autre)], outil.GARDER_IMMATRICULEES) == outil.AUCUN


def test_aucune_etiquette_ne_DEPASSE_sa_colonne():
    """⚠️ *Quatrième occurrence du même défaut, en quatre outils.* **Une
    étiquette plus longue que sa colonne pousse le nombre, et la ligne cesse
    d'être alignée sans qu'aucun chiffre ait bougé.**"""
    trop_longs = [c for c in outil.CE_QUI_RESTE if len(c) > outil.LARGEUR_DU_CAS]
    assert not trop_longs, trop_longs
    trop_larges = [e for e in outil.LES_DEUX_EXCLUSIONS
                   if len(e) > outil.LARGEUR_DUNE_EXCLUSION]
    assert not trop_larges, trop_larges


def test_les_libelles_sont_ceux_RELEVES_dans_le_code_avec_leur_provenance():
    assert outil.LIBELLES_RELEVES["NI"] == "Non immatriculée"
    assert outil.LIBELLES_RELEVES["AI"] == "Avis d'intention de constitution"
    assert "2026-08-31" in outil.PROVENANCE_DES_LIBELLES
    assert "DomaineValeur.csv" in outil.PROVENANCE_DES_LIBELLES


def test_les_codes_radies_du_releve_sont_CEUX_du_moteur():
    """*Un relevé qui diverge du moteur ferait lire la mauvaise frontière.*"""
    from falkye.sources.req import STATUTS_RADIES_CODES_REELS

    radies_du_releve = {c for c, v in outil.LIBELLES_RELEVES.items()
                        if v.startswith("Radiée")}
    assert radies_du_releve == STATUTS_RADIES_CODES_REELS


# ---------------------------------------------------------------------------
# LA MESURE, DE BOUT EN BOUT
# ---------------------------------------------------------------------------

@pytest.fixture()
def decor(db_session, monkeypatch):
    """Trois ambigus à ÉGALITÉ STRICTE, un par cas de figure.

    ⚠️ *Les scores sortent de `rapidfuzz`* : deux entrées du registre portant le
    MÊME nom que le dossier rendent toutes deux 100,0.
    """
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")

    #: (nom, statuts des deux entrées homonymes)
    dossiers = [
        ("Pecheries Alpha inc", ["immatriculee", "radiee"]),   # → UN SEUL, des deux
        ("Pecheries Beta inc", ["immatriculee", "ni"]),        # → UN SEUL / PLUSIEURS
        ("Pecheries Gamma inc", ["radiee", "radiee"]),         # → AUCUN, des deux
    ]
    for i, (nom, statuts) in enumerate(dossiers):
        company = Company(neq=None, nom_detecte=nom,
                          nom_detecte_normalise=normaliser(nom))
        db_session.add(company)
        db_session.flush()
        db_session.add(Signal(
            company_id=company.id, source_id="seao",
            signal_type_id="recrutement_massif",
            detected_at=_dt.datetime(2026, 1, 1), champs={},
        ))
        for j, statut in enumerate(statuts):
            db_session.add(REQEntry(
                neq=f"11{i}000000{j}", nom=nom, nom_normalise=normaliser(nom),
                statut=statut, ville=None))
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def _sortie(capsys):
    return capsys.readouterr().out


def test_ce_que_la_mesure_ne_dira_pas_vient_AVANT_les_chiffres(decor, capsys):
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    assert sortie.index("SERAIT JUSTE") < sortie.index("AMBIGUS :")
    assert "AUCUNE date de radiation" in sortie
    assert "AUCUNE RÈGLE N'EST PROPOSÉE" in sortie


def test_ce_n_est_pas_un_departageur_mais_une_EXCLUSION(decor, capsys):
    """*Le statut n'est porté que d'un côté : le registre.*"""
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    assert "PAS UN DÉPARTAGEUR AU SENS" in sortie
    assert "elle peut VIDER le lot" in sortie


def test_les_deux_exclusions_sont_rendues_COTE_A_COTE(decor, capsys):
    assert outil.main(["--pas", "0"]) == 0
    bloc = _sortie(capsys).split("3. LES ÉGALITÉS STRICTES")[1]
    entete = next(l for l in bloc.splitlines()
                  if outil.GARDER_IMMATRICULEES in l and outil.ECARTER_RADIEES in l)
    assert entete, "les deux exclusions doivent tenir sur la MÊME ligne d'en-tête"


def test_l_ecart_entre_les_deux_colonnes_est_le_poids_de_ni(decor, capsys):
    """⚠️ **Le cœur du test.** *Le dossier à `ni` compte « un seul » sous la
    règle stricte et « plusieurs » sous l'autre — et c'est le seul.*"""
    assert outil.main(["--pas", "0"]) == 0
    bloc = _sortie(capsys).split("SUR LES ÉGALITÉS STRICTES")[1]
    un_seul = next(l for l in bloc.splitlines() if l.strip().startswith(outil.UN_SEUL))
    plusieurs = next(l for l in bloc.splitlines()
                     if l.strip().startswith(outil.PLUSIEURS))
    aucun = next(l for l in bloc.splitlines() if l.strip().startswith(outil.AUCUN))
    # ⚠️ Les comptes se lisent PAR COLONNE, jamais par indice de mot :
    # l'étiquette n'a pas toujours le même nombre de mots.
    # colonne 1 = garder les immatriculées · colonne 2 = n'écarter que les radiées
    assert _comptes(un_seul) == ["2", "1"], un_seul
    assert _comptes(plusieurs) == ["0", "1"], plusieurs
    assert _comptes(aucun) == ["1", "1"], aucun


def test_ni_est_compte_a_part_dans_la_surface_des_statuts(decor, capsys):
    assert outil.main(["--pas", "0"]) == 0
    bloc = _sortie(capsys).split("2. LES STATUTS DES CANDIDATS")[1]
    ligne = next(l for l in bloc.splitlines() if l.strip().startswith("ni "))
    assert "NI l'un NI l'autre" in ligne, ligne
    assert "Non immatriculée" in ligne, ligne


def test_sans_chemin_les_libelles_sont_dits_NON_reconfrontes(decor, capsys):
    """*« Non reconfrontés » n'est pas « conformes ».*"""
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    assert "NON reconfrontés à l'archive" in sortie
    assert "un code a pu être ajouté depuis" in sortie


def test_une_archive_introuvable_ne_se_lit_pas_comme_une_conformite(decor, capsys, tmp_path):
    assert outil.main(["--pas", "0", "--chemin", str(tmp_path / "absente")]) == 0
    sortie = _sortie(capsys)
    assert "ne sont PAS" in sortie and "Ce n'est pas « conformes »" in sortie


def test_AUCUN_est_rendu_comme_un_resultat(decor, capsys):
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    assert "EST UN RÉSULTAT, pas un cas manquant" in sortie
    assert "AUCUN_COMPATIBLE" in sortie


def test_le_groupe_de_tous_les_ambigus_est_celui_du_PRODUIT(decor, capsys):
    """*`concurrents_de` est la fonction du produit, pas une copie.*"""
    assert outil.main(["--pas", "0"]) == 0
    assert "`concurrents_de`" in _sortie(capsys)


def test_aucune_ecriture(decor, capsys):
    from falkye.resolution import SEUIL_AMBIGUITE_ECART_MIN, SEUIL_RESOLUTION_CONFIANTE

    avant = {c.id: c.neq for c in decor.query(Company).all()}
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    assert (f"seuil {SEUIL_RESOLUTION_CONFIANTE:.0f}, "
            f"écart {SEUIL_AMBIGUITE_ECART_MIN:.0f}") in sortie
    assert "RIEN N'A ÉTÉ ÉCRIT" in sortie
    assert {c.id: c.neq for c in decor.query(Company).all()} == avant
