"""Le pic est-il un plancher technique, et qui remplit la tranche alphabétique?

⚠️ **Ce que ces tests gardent.** *La tranche de 2 000 est remplie par le DÉBUT
de l'ordre alphabétique de `nom_normalise`* — où l'espace trie avant les
chiffres, qui trient avant les lettres. **`LES " 100 " AILE` y est
`les 100 aile`**, et c'est pour ça qu'il occupe la place.
"""
from __future__ import annotations

import pytest

from falkye.models.company import Company
from falkye.models.req_entry import REQEntry
from falkye.sources.column_mapping import normaliser
from outils import recomptage_du_plancher
from outils.recomptage_du_plancher import (
    ALPHABETIQUES,
    CLASSES,
    NON_ALPHABETIQUES,
    apres_le_prefixe,
    echantillon_reparti,
)


def test_ce_qui_suit_le_prefixe_est_classe_sur_la_forme_NORMALISEE():
    """*`normaliser` a déjà remplacé la ponctuation par des espaces* — donc ce
    qu'on voit après le préfixe est un espace, un chiffre ou une lettre."""
    assert apres_le_prefixe("les 100 aile", "les") == "espace puis CHIFFRE"
    assert apres_le_prefixe("ferme 100 miles", "ferme") == "espace puis CHIFFRE"
    assert apres_le_prefixe("les habitations ktp", "les") == "espace puis lettre"
    assert apres_le_prefixe("lesage construction", "les") == "lettre collée (mot plus long)"
    assert apres_le_prefixe("les2go", "les") == "CHIFFRE collé"
    assert apres_le_prefixe("les", "les") == "rien — le nom EST le préfixe"
    assert apres_le_prefixe("les   ", "les") == "rien — le nom EST le préfixe"
    assert apres_le_prefixe("autre chose", "les") == "hors préfixe"


def test_les_classes_couvrent_TOUT_ce_que_la_fonction_rend():
    """⚠️ *Une classe rendue par la fonction et absente du tableau disparaîtrait
    du compte sans qu'aucun total ne bouge.*"""
    rendues = {
        apres_le_prefixe(forme, "les")
        for forme in ("les 1", "les a", "les1", "lesa", "les", "autre")
    }
    assert rendues <= set(CLASSES), rendues - set(CLASSES)
    assert set(NON_ALPHABETIQUES) | set(ALPHABETIQUES) | {"hors préfixe"} == set(CLASSES)


def test_lordre_de_sqlite_met_bien_les_chiffres_AVANT_les_lettres():
    """**Le fait qui explique tout le motif.** *L'espace trie avant les chiffres,
    les chiffres avant les lettres* — donc la tranche commence par
    `les 100 aile` et n'atteint jamais `les habitations`."""
    assert " " < "0" < "9" < "a" < "z"
    assert sorted(["les habitations ktp", "les 100 aile", "lesage"]) == [
        "les 100 aile", "les habitations ktp", "lesage",
    ]


def test_lechantillon_est_reparti_sur_le_GISEMENT_pas_sur_lid():
    """⚠️ *Trier par `id` donnerait l'ordre des fichiers sources (cas 19).* Ici le
    tri est le gisement, pour que les GROS préfixes — ceux où la borne fait mal —
    soient représentés au lieu d'être noyés."""
    faux = [type("D", (), {"id": i, "g": i})() for i in range(100)]
    tire = echantillon_reparti(faux, 10, cle=lambda d: (d.g, d.id))
    assert len(tire) == 10
    assert max(d.g for d in tire) >= 90, "le haut du gisement n'est pas représenté"
    assert min(d.g for d in tire) <= 10, "le bas du gisement n'est pas représenté"
    assert [d.id for d in tire] != list(range(10))


def test_lechantillon_rend_tout_quand_il_est_plus_grand_que_la_population():
    faux = [type("D", (), {"id": i, "g": i})() for i in range(3)]
    assert len(echantillon_reparti(faux, 10, cle=lambda d: d.g)) == 3
    assert echantillon_reparti([], 10, cle=lambda d: 0) == []


def _cible_declaree(monkeypatch):
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")


@pytest.fixture()
def tranche_coupee(db_session, monkeypatch):
    """Le motif des dix, en miniature : la tranche est remplie de `les <chiffre>`
    et le VRAI candidat, `les habitations ktp`, tombe hors borne.

    ⚠️ **La borne est abaissée à 3 par le décor** *(via `--limite` non : par
    `LIMITE_CANDIDATS_PAR_NOM`)* — pour que le mécanisme se reproduise sans
    charger 2 000 lignes dans un test.
    """
    _cible_declaree(monkeypatch)
    monkeypatch.setattr("falkye.sources.req.LIMITE_CANDIDATS_PAR_NOM", 3)
    for i, nom in enumerate([
        'LES " 100 " AILE', "LES 200 BOIS", "LES 300 CEDRES", "LES 400 DUNES",
        "Les Habitations KTP",
    ]):
        db_session.add(REQEntry(neq=f"60000000{i}", nom=nom,
                                nom_normalise=normaliser(nom), statut="IMMATRICULÉE"))
    detecte = "Les Habitations KTP"
    db_session.add(Company(neq=None, nom_detecte=detecte,
                           nom_detecte_normalise=normaliser(detecte)))
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def test_le_decor_reproduit_bien_la_COUPE(tranche_coupee):
    """*Un test qui « passe » sur un lot non coupé ne verrouille rien.*"""
    from falkye.sources import req as req_source

    journal: dict = {}
    lot = req_source.candidats_par_nom(
        tranche_coupee, normaliser("Les Habitations KTP"), limite=3, journal=journal
    )
    assert journal["sature"] is True
    assert all("habitations" not in (c.nom_normalise or "") for c in lot), (
        "le vrai candidat est DANS le lot — le décor ne reproduit pas la coupe"
    )


def test_ce_que_les_mesures_ne_diront_pas_vient_AVANT_les_chiffres(tranche_coupee, capsys):
    assert recomptage_du_plancher.main([]) == 0
    sortie = capsys.readouterr().out
    assert sortie.index("NE DIRONT PAS") < sortie.index("dossiers sans NEQ")
    assert "NE DIRONT PAS QU'UN CANDIDAT TROUVÉ HORS BORNE SOIT LE BON" in sortie
    assert "RIEN N'EST CONSTRUIT" in sortie


def test_la_mesure_A_compte_ce_qui_remplit_la_tranche(tranche_coupee, capsys):
    assert recomptage_du_plancher.main(["--mesures", "A"]) == 0
    sortie = capsys.readouterr().out
    assert "QUI REMPLIT LA TRANCHE?" in sortie
    ligne = next(l for l in sortie.splitlines() if l.strip().startswith("espace puis CHIFFRE"))
    assert ligne.split()[3] == "3", ligne  # les trois `les <chiffre>` du décor
    assert "NON ALPHABÉTIQUE après le préfixe : 3" in sortie


def test_la_mesure_A_dit_les_lots_coupes_AVANT_la_premiere_lettre(tranche_coupee, capsys):
    """⚠️ **Le chiffre qui tue le réglage d'échelle.** *Là, le score n'a jamais vu
    un seul nom commençant par une lettre après le préfixe.*"""
    assert recomptage_du_plancher.main(["--mesures", "A"]) == 0
    sortie = capsys.readouterr().out
    assert "lots coupés AVANT LA PREMIÈRE LETTRE : 1" in sortie, sortie


def test_la_mesure_C_annonce_son_BUDGET_avant_de_le_depenser(tranche_coupee, capsys):
    """*« Dire ce que coûte l'échantillon avant de le lancer, et sur combien de
    dossiers il porte. »*"""
    assert recomptage_du_plancher.main(["--mesures", "C", "--echantillon", "5"]) == 0
    sortie = capsys.readouterr().out
    budget = sortie.index("LE BUDGET, AVANT DE LE DÉPENSER")
    assert budget < sortie.index("FRANCHISSENT LE SEUIL")
    assert "lignes à charger au total" in sortie
    assert "UNE ESTIMATION" in sortie
    assert "règle de tirage" in sortie


def test_la_mesure_C_trouve_le_candidat_QUE_LA_BORNE_CACHAIT(tranche_coupee, capsys):
    """**La mesure qui décide.** *Le vrai candidat est hors borne; borne levée,
    il franchit le seuil.*"""
    assert recomptage_du_plancher.main(["--mesures", "C", "--echantillon", "5"]) == 0
    sortie = capsys.readouterr().out
    assert "FRANCHISSENT LE SEUIL DE 92 une fois la borne levée : 1 sur 1" in sortie, sortie
    assert "Les Habitations KTP" in sortie
    assert "Un franchissement n'est PAS un appariement juste" in sortie


def test_les_refus_du_plafond_sont_COMPTES_et_affiches(tranche_coupee, capsys):
    """⚠️ *Le plafond écarte exactement les cas où la borne fait le plus mal.*
    **Un garde silencieux transformerait ce biais en résultat.**"""
    assert recomptage_du_plancher.main(
        ["--mesures", "C", "--echantillon", "5", "--gisement-max", "1"]
    ) == 0
    sortie = capsys.readouterr().out
    assert "dossiers REFUSÉS" in sortie
    assert "LES REFUSÉS SONT EXACTEMENT LES CAS" in sortie
    assert "FRANCHISSENT LE SEUIL DE 92 une fois la borne levée : 0 sur 0" in sortie


def test_il_NECRIT_RIEN(tranche_coupee):
    from sqlalchemy import select

    avant = {c.id: c.neq for c in tranche_coupee.execute(select(Company)).scalars().all()}
    assert recomptage_du_plancher.main(["--mesures", "ABC"]) == 0
    tranche_coupee.expire_all()
    apres = {c.id: c.neq for c in tranche_coupee.execute(select(Company)).scalars().all()}
    assert avant == apres


def test_les_echelles_et_la_borne_de_PRODUCTION_ne_bougent_pas(tranche_coupee):
    """⚠️ *Une borne levée en production coûterait sur CHAQUE résolution ce que
    la mesure C coûte une fois.*"""
    from falkye import resolution
    from falkye.sources import req as req_source

    assert recomptage_du_plancher.main(["--mesures", "ABC"]) == 0
    assert resolution.SEUIL_RESOLUTION_CONFIANTE == 92.0
    assert resolution.SEUIL_AMBIGUITE_ECART_MIN == 8.0
    # Le décor l'a posée à 3; ce qui compte est qu'aucune MESURE ne l'ait bougée.
    assert req_source.LIMITE_CANDIDATS_PAR_NOM == 3


# ---------------------------------------------------------------------------
# MESURE B — le pic est-il une POPULATION ou une VALEUR?
# ---------------------------------------------------------------------------


def test_le_decor_rend_bien_85_50_le_score_du_premier_mot_seul(tranche_coupee):
    """**Le fait qui fonde la mesure B.** *`WRatio` rend 85.50 quand seul le
    premier mot correspond* — et c'est la valeur qu'Alexandre a vue huit fois
    sur dix."""
    from rapidfuzz import fuzz

    assert fuzz.WRatio(normaliser("Les Habitations KTP"),
                       normaliser('LES " 100 " AILE')) == 85.5
    assert fuzz.WRatio(normaliser("Les Habitations KTP"),
                       normaliser("LES 200 BOIS")) == 85.5


def test_la_mesure_B_rend_la_distribution_des_valeurs_EXACTES(tranche_coupee, capsys):
    """⚠️ *Une distribution de RESSEMBLANCE ne se concentre pas sur une valeur.
    Un PLANCHER de calcul, si.*"""
    assert recomptage_du_plancher.main(["--mesures", "B"]) == 0
    sortie = capsys.readouterr().out
    assert "valeur EXACTE" in sortie
    assert "85.50" in sortie
    assert "La valeur la plus fréquente pèse 100.0 % du pic" in sortie, sortie


def test_la_mesure_B_compte_le_PREMIER_MOT_SEULEMENT(tranche_coupee, capsys):
    """*Comparé à TOUTES les formes publiées du NEQ, en gardant le meilleur
    recouvrement* — si même la meilleure ne partage que le premier mot, la
    lecture tient a fortiori."""
    assert recomptage_du_plancher.main(["--mesures", "B"]) == 0
    sortie = capsys.readouterr().out
    assert "le PREMIER MOT seulement" in sortie
    assert "des dossiers du plancher ne partagent" in sortie
    ligne = next(l for l in sortie.splitlines()
                 if l.strip().startswith("le PREMIER MOT seulement"))
    assert ligne.split()[4] == "1", ligne
