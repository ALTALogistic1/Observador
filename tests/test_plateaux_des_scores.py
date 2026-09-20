"""Les paliers du scoreur, sur les ambigus.

⚠️ **Ce que ces tests verrouillent : qu'une mesure ne confirme pas sa propre
hypothèse.** *Quatre paliers ont été relevés sur 102 lignes. Une mesure qui ne
chercherait QUE ces quatre-là les retrouverait forcément* — donc elle doit
TROUVER les paliers dans la population, dire lesquels des quatre tiennent, et
surtout **lesquels elle ajoute.**
"""
from __future__ import annotations

import datetime as _dt
from collections import Counter

import pytest

from falkye.models.company import Company
from falkye.models.req_entry import REQEntry
from falkye.models.signal import Signal
from falkye.sources.column_mapping import normaliser
from outils import plateaux_des_scores as outil
from tests.conftest import compte_de_la_ligne as _compte


# ---------------------------------------------------------------------------
# LA DÉTECTION DES PALIERS — trouvés, jamais fournis
# ---------------------------------------------------------------------------

def test_un_palier_se_TROUVE_dans_la_population_il_ne_se_fournit_pas():
    compteur = Counter({100.0: 200, 95.0: 60, 90.0: 50, 87.3: 49, 84.1: 1})
    # ⚠️ 49 ne passe pas le plancher de 50 : la borne est stricte et posée d'avance.
    assert outil.paliers_observes(compteur) == [100.0, 95.0, 90.0]


def test_les_paliers_sont_rendus_du_plus_haut_au_plus_bas():
    compteur = Counter({85.5: 99, 100.0: 99, 92.0: 99})
    assert outil.paliers_observes(compteur) == [100.0, 92.0, 85.5]


def test_un_plancher_plus_bas_rend_PLUS_de_paliers_et_ça_se_demande():
    """*La borne est un paramètre, pas une constante enfouie* — et elle se
    demande jusque dans la ligne de commande, `--plancher`."""
    compteur = Counter({100.0: 10, 95.0: 5, 90.0: 2})
    assert outil.paliers_observes(compteur, plancher=5) == [100.0, 95.0]
    assert outil.paliers_observes(compteur, plancher=2) == [100.0, 95.0, 90.0]


@pytest.mark.parametrize("meilleur, second, attendu", [
    (100.0, 95.0, outil.LES_DEUX),
    (100.0, 93.7, outil.UN_SEUL),
    (97.2, 95.0, outil.UN_SEUL),
    (97.2, 93.7, outil.AUCUN),
])
def test_le_cas_d_un_couple_compte_les_DEUX_cotes(meilleur, second, attendu):
    assert outil._cas_du_couple(meilleur, second, [100.0, 95.0]) == attendu


class _Entry:
    def __init__(self, ville): self.ville = ville


class _Match:
    def __init__(self, ville): self.entry = _Entry(ville)


class _Dossier:
    def __init__(self, ville): self.ville = ville


@pytest.mark.parametrize("ville_dossier, ville_candidat, attendu", [
    ("Québec", "QUÉBEC", True),
    ("Québec", "Montréal", False),
    # ⚠️ *Sans ville d'un côté, `_scorer` n'applique rien* — et « inconnu »
    # n'est pas « ne concorde pas », c'est « la question ne se pose pas ».
    (None, "Québec", False),
    ("Québec", None, False),
])
def test_le_bonus_de_ville_se_reconnait_comme_le_moteur_le_pose(
        ville_dossier, ville_candidat, attendu):
    assert outil.porte_le_bonus_de_ville(
        _Dossier(ville_dossier), _Match(ville_candidat)) is attendu


def test_les_quatre_paliers_de_la_lecture_sont_une_HYPOTHESE_nommee():
    """*Ils sont dans le code pour être confrontés, pas pour être cherchés.*"""
    assert outil.PALIERS_DE_LA_LECTURE == (100.0, 95.0, 90.0, 85.5)


# ---------------------------------------------------------------------------
# LA MESURE, DE BOUT EN BOUT
# ---------------------------------------------------------------------------

@pytest.fixture()
def decor(db_session, monkeypatch):
    """Des ambigus fabriqués pour tomber sur des paliers réels.

    ⚠️ *Les scores ne sont pas posés à la main : ils sortent de `rapidfuzz`*,
    comme en production. Un décor qui écrirait `score=95.0` mesurerait sa
    propre invention.
    """
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")

    #: (nom détecté, [noms du registre]) — les scores SORTENT de rapidfuzz.
    #: Deux dossiers tombent sur le couple (100,0 · 95,0), un troisième sur
    #: (97,4 · 95,0) : le premier est un couple de DEUX paliers, le second n'en
    #: a qu'un. C'est exactement la distinction que la mesure doit rendre.
    #: ⚠️ Les noms du registre partagent le préfixe du nom détecté — sinon la
    #: récupération ne les rend pas, et le décor mesurerait un lot vide.
    dossiers = [
        ("Pecheries Alpha inc", ["Pecheries Alpha inc", "Pecheries Alpha"]),
        ("Pecheries Beta inc", ["Pecheries Beta inc", "Pecheries Beta"]),
        ("Pecheries Gamma inc", ["Pecheries Gammar inc", "Pecheries Gamma"]),
    ]
    for i, (nom, au_registre) in enumerate(dossiers):
        company = Company(neq=None, nom_detecte=nom,
                          nom_detecte_normalise=normaliser(nom))
        db_session.add(company)
        db_session.flush()
        db_session.add(Signal(
            company_id=company.id, source_id="seao",
            signal_type_id="recrutement_massif",
            detected_at=_dt.datetime(2026, 1, 1), champs={},
        ))
        for j, nom_req in enumerate(au_registre):
            db_session.add(REQEntry(
                neq=f"11{i}000000{j}", nom=nom_req,
                nom_normalise=normaliser(nom_req),
                # ⚠️ Une ville au registre, AUCUNE au dossier : `_scorer`
                # n'applique alors aucun bonus, et la vue propre couvre tout.
                statut="immatriculee", ville="Québec"))
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def _sortie(capsys):
    return capsys.readouterr().out


def test_ce_que_la_mesure_ne_dira_pas_vient_AVANT_les_chiffres(decor, capsys):
    assert outil.main(["--pas", "0", "--plancher", "2"]) == 0
    sortie = _sortie(capsys)
    assert sortie.index("BIEN APPARIÉ SI L'ÉCART CHANGEAIT") < sortie.index(
        "AMBIGUS MESURÉS")
    assert "DISTANCES, jamais des IDENTITÉS" in sortie


def test_les_echelles_sont_dites_NON_rouvertes_par_cette_mesure(decor, capsys):
    from falkye.resolution import SEUIL_AMBIGUITE_ECART_MIN, SEUIL_RESOLUTION_CONFIANTE

    assert outil.main(["--pas", "0", "--plancher", "2"]) == 0
    sortie = _sortie(capsys)
    assert (f"seuil de {SEUIL_RESOLUTION_CONFIANTE:.0f} et l'écart de "
            f"{SEUIL_AMBIGUITE_ECART_MIN:.0f}") in sortie
    assert "pas pour l'autoriser" in sortie


def test_la_correction_du_couple_90_85_est_dite_avant_de_compter(decor, capsys):
    """⚠️ *Un ambigu exige meilleur ≥ 92 : « 90 → 85,5 » est un trop faible.*"""
    assert outil.main(["--pas", "0", "--plancher", "2"]) == 0
    sortie = _sortie(capsys)
    assert "C'EST FAUX" in sortie
    assert "n'est PAS mesuré ici" in sortie
    assert sortie.index("C'EST FAUX") < sortie.index("AMBIGUS MESURÉS")


def test_la_mesure_rend_les_paliers_AJOUTES_pas_seulement_les_attendus(decor, capsys):
    """⚠️ **La garde principale.** *Une mesure qui n'aurait cherché que les
    quatre attendus aurait confirmé sa propre liste.*"""
    assert outil.main(["--pas", "0", "--plancher", "2"]) == 0
    sortie = _sortie(capsys)
    assert "AJOUTÉS par la population" in sortie
    assert "NON confirmés" in sortie
    assert "aurait confirmé sa propre liste" in sortie


def test_les_deux_distributions_sont_rendues_SEPAREMENT(decor, capsys):
    assert outil.main(["--pas", "0", "--plancher", "2"]) == 0
    sortie = _sortie(capsys)
    assert "LE MEILLEUR CANDIDAT" in sortie and "LE SECOND" in sortie
    assert "valeurs distinctes" in sortie


def test_un_ecart_sous_8_est_dit_DEFINITION_et_pas_resultat(decor, capsys):
    """*Ce que la colonne « écart » sert à lire, c'est sur QUELLES valeurs il
    tombe — pas qu'il soit petit.*"""
    assert outil.main(["--pas", "0", "--plancher", "2"]) == 0
    assert "c'est la\n      DÉFINITION d'un ambigu" in _sortie(capsys)


def test_les_DEUX_sur_un_palier_se_distinguent_d_UN_SEUL(decor, capsys):
    """*Deux dossiers tombent sur (100,0 · 95,0), un sur (97,3 · 95,0).* **Le
    premier couple est fait de deux constantes, le second d'une seule.**"""
    assert outil.main(["--pas", "0", "--plancher", "2"]) == 0
    bloc = _sortie(capsys).split("3. LA PART DÉCISIVE")[1].split("⚠️")[0]
    deux = next(l for l in bloc.splitlines() if l.strip().startswith(outil.LES_DEUX))
    un = next(l for l in bloc.splitlines() if l.strip().startswith(outil.UN_SEUL))
    assert _compte(deux) == "2", deux
    assert _compte(un) == "1", un


def test_les_trois_cas_du_couple_sont_rendus_et_totalisent_la_population(decor, capsys):
    assert outil.main(["--pas", "0", "--plancher", "2"]) == 0
    bloc = _sortie(capsys).split("3. LA PART DÉCISIVE")[1].split("⚠️")[0]
    total = 0
    for cas in outil.ORDRE_DES_CAS:
        ligne = next(l for l in bloc.splitlines() if l.strip().startswith(cas))
        total += int(_compte(ligne).replace(" ", ""))
    assert total == 3, bloc


def test_la_derniere_ligne_est_dite_L_AUTRE_MOITIE_du_resultat(decor, capsys):
    """*Si les couples sans palier sont nombreux, le motif ne porte qu'une
    partie de la population — et le dire est un résultat.*"""
    assert outil.main(["--pas", "0", "--plancher", "2"]) == 0
    assert "L'AUTRE MOITIÉ DU RÉSULTAT" in _sortie(capsys)


def test_le_bonus_de_ville_est_compte_et_dit_INDICATEUR(decor, capsys):
    assert outil.main(["--pas", "0", "--plancher", "2"]) == 0
    sortie = _sortie(capsys)
    assert "LE BONUS DE VILLE" in sortie
    assert "un INDICATEUR, pas une" in sortie
    assert "divergerait en silence" in sortie


def test_les_paliers_de_la_vue_propre_sont_RECALCULES(decor, capsys):
    """⚠️ *Un palier de la population entière peut n'en plus être un ici.*"""
    assert outil.main(["--pas", "0", "--plancher", "2"]) == 0
    sortie = _sortie(capsys)
    if "5. LA VUE PROPRE" in sortie:
        assert "RECALCULÉS SUR CETTE SOUS-POPULATION" in sortie
    else:
        assert "la vue propre n'existe pas" in sortie


def test_aucune_ecriture(decor, capsys):
    avant = {c.id: c.neq for c in decor.query(Company).all()}
    assert outil.main(["--pas", "0", "--plancher", "2"]) == 0
    assert "RIEN N'A ÉTÉ ÉCRIT" in _sortie(capsys)
    assert {c.id: c.neq for c in decor.query(Company).all()} == avant
