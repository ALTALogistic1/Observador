"""L'écriture du départage par le statut — **élargie aux confirmations.**

⚠️ **Ce que ces tests verrouillent : la PORTÉE et sa limite.** *Le 21 septembre,
« pas une égalité » cesse d'être un blocage et devient une portée.* **Ce qui ne
bouge pas est la condition du sommet** : un survivant moins bien scoré reste en
suspens, dans les DEUX portées — c'est elle qui porte les 78 du 20 septembre et
le témoin nommé par Alexandre.

⚠️ *Et l'adresse est vérifiée COLONNE, jamais condition* : un dossier qu'elle
contredit est tout de même à poser, et le verdict se lit dans la sortie.
"""
from __future__ import annotations

import datetime as _dt
import json

import pytest

from falkye.models.company import Company, StatutResolution
from falkye.models.req_entry import REQEntry
from falkye.models.signal import Signal
from falkye.sources.column_mapping import normaliser
from outils import ecriture_du_statut as outil


class _Match:
    def __init__(self, statut, score, neq=None):
        self.entry = type("E", (), {"statut": statut, "neq": neq or f"1{int(score)}",
                                    "nom": "x", "ville": None})()
        self.score = score


# ---------------------------------------------------------------------------
# LA CONDITION DU SOMMET — c'est elle qui porte la décision, dans les DEUX portées
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("statuts_scores, portee_attendue", [
    # une égalité entre DEUX RADIÉES : le nom ne désignait personne…
    ([("radiee", 100.0), ("radiee", 100.0), ("immatriculee", 95.0)], outil.EGALITE),
    # …un sommet UNIQUE radié : le nom désignait un gagnant, et le statut le tue
    ([("radiee", 100.0), ("immatriculee", 95.0)], outil.CONFIRMATION),
])
def test_un_restant_SOUS_le_sommet_reste_en_suspens_dans_LES_DEUX_portees(
        statuts_scores, portee_attendue):
    """⚠️ **La réserve, vérifiée des deux côtés.** *L'élargissement change ce
    que le nom avait fait; il ne change pas qu'un survivant sous le sommet est
    une contradiction entre deux instruments.*"""
    groupe = [_Match(s, sc) for s, sc in statuts_scores]
    raison, seul, portee = outil.ce_qui_bloque(groupe, groupe)
    assert raison == outil.SOUS_LE_SOMMET
    assert portee == portee_attendue
    assert seul.score == 95.0, "le restant est nommé, pour qu'on le lise"


@pytest.mark.parametrize("statuts_scores, attendu, portee", [
    # ✅ L'ÉLARGISSEMENT : sommet unique, tous les concurrents radiés
    ([("immatriculee", 100.0), ("radiee", 95.0)], None, outil.CONFIRMATION),
    # ✅ l'égalité stricte du 20 septembre — inchangée
    ([("immatriculee", 100.0), ("radiee", 100.0)], None, outil.EGALITE),
    ([("radiee", 100.0), ("radiee", 100.0)], outil.LOT_VIDE, None),
    ([("immatriculee", 100.0), ("ni", 100.0)], outil.PAS_UN_SEUL, None),
    # ⚠️ Un `ni` seul survivant AU sommet : la forme retenue le garde.
    ([("ni", 100.0), ("radiee", 100.0)], None, outil.EGALITE),
])
def test_les_conditions_dans_l_ordre(statuts_scores, attendu, portee):
    groupe = [_Match(s, sc) for s, sc in statuts_scores]
    raison, _seul, rendue = outil.ce_qui_bloque(groupe, groupe)
    assert raison == attendu
    assert rendue == portee


def test_PAS_UNE_EGALITE_n_est_plus_un_blocage():
    """⚠️ *Ce qui bloquait hier et ne bloque plus aujourd'hui se dit* — sinon
    l'écart se lit comme un oubli."""
    assert not hasattr(outil, "PAS_UNE_EGALITE")
    assert outil.CONFIRMATION not in outil.RAISONS


def test_les_deux_portees_sont_DISJOINTES_et_exhaustives():
    """*Un lot a des ex æquo au sommet, ou il n'en a pas.*"""
    for groupe in ([_Match("immatriculee", 100.0), _Match("radiee", 100.0)],
                   [_Match("immatriculee", 100.0), _Match("radiee", 95.0)],
                   [_Match("immatriculee", 100.0)]):
        assert outil.portee_de(groupe) in outil.PORTEES


def test_la_portee_demandee_ECARTE_sans_refuser():
    """`--portee egalites` laisse les confirmations en suspens, et le dit."""
    groupe = [_Match("immatriculee", 100.0), _Match("radiee", 95.0)]
    raison, _seul, portee = outil.ce_qui_bloque(
        groupe, groupe, portees=(outil.EGALITE,))
    assert raison == outil.HORS_PORTEE
    assert portee == outil.CONFIRMATION


def test_la_forme_retenue_est_celle_qu_ALEXANDRE_a_tranchee():
    from outils.statut_sur_les_egalites import ECARTER_RADIEES

    assert outil.FORME_QUI_SECRIT is ECARTER_RADIEES


def test_la_colonne_des_raisons_tient_TOUTES_les_etiquettes():
    """⚠️ *Une étiquette plus longue que sa colonne pousse le nombre* — le
    défaut a été corrigé cinq fois avant d'être gardé."""
    for texte in outil.RAISONS + outil.ETIQUETTES_DU_RAPPORT + outil.VERDICTS_DADRESSE:
        assert len(texte) < outil.LARGEUR_DUNE_RAISON, texte


def test_le_chemin_de_l_instantane_est_EMPRUNTE_et_plus_recopie():
    """⚠️ *Il était recopié dans trois outils. Une constante recopiée diverge
    sans que rien ne le dise.*"""
    from outils import (
        ecriture_des_departages,
        pose_du_neq,
        promotion_ville,
        reresolution_neq,
    )

    for module in (outil, ecriture_des_departages, promotion_ville, reresolution_neq):
        assert module.DOSSIER_INSTANTANE is pose_du_neq.DOSSIER_INSTANTANE


# ---------------------------------------------------------------------------
# L'ÉCRITURE, DE BOUT EN BOUT
# ---------------------------------------------------------------------------

@pytest.fixture()
def decor(db_session, monkeypatch):
    """Un dossier par cas de figure, le témoin nommé compris."""
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")

    #: (nom, code postal du dossier, [(nom au registre, statut, neq, code postal)])
    dossiers = [
        # ✅ égalité stricte, le survivant EST au sommet → à poser
        ("Boulangerie Alpha inc", None,
         [("Boulangerie Alpha inc", "immatriculee", "1100000001", None),
          ("Boulangerie Alpha inc", "radiee", "1100000002", None)]),
        # ⛔ égalité entre deux radiées → le restant est SOUS le sommet
        ("Quincaillerie Beta inc", None,
         [("Quincaillerie Beta inc", "radiee", "1100000003", None),
          ("Quincaillerie Beta inc", "radiee", "1100000004", None),
          ("Quincaillerie Beta", "immatriculee", "1100000005", None)]),
        # ✅ L'ÉLARGISSEMENT : sommet unique immatriculé, concurrent radié
        ("Imprimerie Gamma inc", None,
         [("Imprimerie Gamma inc", "immatriculee", "1100000006", None),
          ("Imprimerie Gamma", "radiee", "1100000007", None)]),
        # ⛔ lot vidé
        ("Serrurerie Delta inc", None,
         [("Serrurerie Delta inc", "radiee", "1100000008", None),
          ("Serrurerie Delta inc", "radiee", "1100000009", None)]),
        # ⚠️ LE TÉMOIN NOMMÉ : sommet unique RADIÉ, le survivant est dessous
        (outil.TEMOIN_DE_LA_CONTRADICTION + " inc", None,
         [(outil.TEMOIN_DE_LA_CONTRADICTION + " inc", "radiee", "1100000010", None),
          (outil.TEMOIN_DE_LA_CONTRADICTION, "immatriculee", "1100000011", None)]),
        # ✳️ à poser, ET l'adresse du dossier les exclut tous
        ("Fromagerie Zeta inc", "G9A2G9",
         [("Fromagerie Zeta inc", "immatriculee", "1100000012", "G8Z0A3"),
          ("Fromagerie Zeta inc", "radiee", "1100000013", "G8Z0A3")]),
    ]
    for nom, code_postal, au_registre in dossiers:
        company = Company(neq=None, nom_detecte=nom,
                          nom_detecte_normalise=normaliser(nom),
                          code_postal=code_postal,
                          statut_resolution=StatutResolution.AMBIGU,
                          first_detected_at=_dt.datetime(2026, 1, 1))
        db_session.add(company)
        db_session.flush()
        db_session.add(Signal(
            company_id=company.id, source_id="seao",
            signal_type_id="recrutement_massif",
            detected_at=_dt.datetime(2026, 1, 1), champs={}))
        for nom_req, statut, neq, cp in au_registre:
            db_session.add(REQEntry(neq=neq, nom=nom_req,
                                    nom_normalise=normaliser(nom_req),
                                    statut=statut, ville=None, code_postal=cp))
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def _sortie(capsys):
    return capsys.readouterr().out


def test_RAPPORT_SEUL_par_defaut_rien_n_est_ecrit(decor, capsys):
    avant = {c.id: c.neq for c in decor.query(Company).all()}
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    assert "RAPPORT SEUL — rien n'a été écrit" in sortie
    assert {c.id: c.neq for c in decor.query(Company).all()} == avant


def test_la_reserve_sur_l_elargissement_est_dite_AVANT_les_chiffres(decor, capsys):
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    assert sortie.index("LA RÉSERVE SUR L'ÉLARGISSEMENT") < sortie.index("ambigus rejoués")
    assert "jamais au\n      DOSSIER" in sortie
    assert "plafonne à CINQ" in sortie
    assert "UNE ENTREPRISE RADIÉE PEUT ÊTRE LA BONNE" in sortie
    assert "AUCUNE\n      date de radiation" in sortie


def test_les_deux_populations_sont_comptees_A_PART(decor, capsys):
    """⚠️ *La sortie sépare les égalités des confirmations* — sinon
    l'élargissement se lit comme un total qui a grossi."""
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    egalites = next(l for l in sortie.splitlines() if "dont ÉGALITÉS STRICTES" in l)
    confirmations = next(l for l in sortie.splitlines() if "dont CONFIRMATIONS" in l)
    from tests.conftest import compte_de_la_ligne

    assert compte_de_la_ligne(egalites) == "2", egalites      # Alpha, Zeta
    assert compte_de_la_ligne(confirmations) == "1", confirmations   # Gamma


def test_les_suspendus_sont_comptes_PAR_RAISON(decor, capsys):
    """⚠️ *Un outil qui écrit une partie doit dire lesquels il n'a pas
    touchés.*"""
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    for raison in outil.RAISONS:
        assert any(l.strip().startswith(raison) for l in sortie.splitlines()), raison
    assert "LAISSÉS EN SUSPENS, ET NON REFUSÉS : 3" in sortie
    assert "sinon la différence se lit comme une perte" in sortie


def test_les_SOUS_LE_SOMMET_sont_ventiles_par_portee(decor, capsys):
    """*Les 78 du 20 septembre ne se mêlent pas à ceux que l'élargissement fait
    apparaître.*"""
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    from tests.conftest import compte_de_la_ligne

    hier = next(l for l in sortie.splitlines() if "dont égalités strictes" in l)
    neufs = next(l for l in sortie.splitlines() if "dont sommet unique" in l)
    assert compte_de_la_ligne(hier) == "1", hier        # Beta
    assert compte_de_la_ligne(neufs) == "1", neufs      # le témoin


def test_l_ELARGISSEMENT_pose_le_dossier_a_sommet_unique(decor, capsys):
    assert outil.main(["--pas", "0", "--comparer", "5"]) == 0
    sortie = _sortie(capsys)
    bloc = sortie.split(f"CE QUI SERAIT ÉCRIT — {outil.CONFIRMATION}")[1]
    assert "Imprimerie Gamma inc" in bloc
    assert "1100000006" in bloc, "le survivant immatriculé, au sommet"


def test_le_TEMOIN_nomme_est_montre_et_laisse_en_suspens(decor, capsys):
    """⚠️ **Alexandre l'a nommé comme une contradiction.** *La sortie montre ce
    que l'outil en fait, plutôt que de l'affirmer dans un commentaire.*"""
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    bloc = sortie.split("LE TÉMOIN NOMMÉ")[1]
    assert outil.TEMOIN_DE_LA_CONTRADICTION in bloc
    assert "LAISSÉ EN SUSPENS" in bloc
    assert outil.SOUS_LE_SOMMET[2:] in bloc


def test_un_temoin_INTROUVABLE_se_dit_au_lieu_de_disparaitre(decor, capsys):
    assert outil.main(["--pas", "0", "--temoin", "Une Entreprise Absente"]) == 0
    bloc = _sortie(capsys).split("LE TÉMOIN NOMMÉ")[1]
    assert "INTROUVABLE" in bloc
    assert "La preuve manque" in bloc


def test_l_adresse_est_une_COLONNE_et_n_ecarte_RIEN(decor, capsys):
    """⚠️ *Le dossier que l'adresse contredit est tout de même à poser* — la
    décision reste à Alexandre, et le chiffre se lit avant d'appliquer."""
    assert outil.main(["--pas", "0", "--comparer", "5"]) == 0
    sortie = _sortie(capsys)
    from tests.conftest import compte_de_la_ligne

    ligne = next(l for l in sortie.splitlines()
                 if l.strip().startswith(outil.ADRESSE_EXCLUT_TOUS))
    assert compte_de_la_ligne(ligne) == "1", ligne
    bloc = sortie.split(f"CE QUI SERAIT ÉCRIT — {outil.EGALITE}")[1]
    assert "Fromagerie Zeta inc" in bloc, "contredit par l'adresse, et POURTANT à poser"
    assert outil.ADRESSE_EXCLUT_TOUS in bloc


def test_la_portee_egalites_LAISSE_les_confirmations(decor, capsys):
    assert outil.main(["--pas", "0", "--portee", "egalites"]) == 0
    sortie = _sortie(capsys)
    from tests.conftest import compte_de_la_ligne

    ligne = next(l for l in sortie.splitlines()
                 if l.strip().startswith(outil.HORS_PORTEE))
    assert compte_de_la_ligne(ligne) == "1", ligne      # Gamma
    assert "LAISSÉS EN SUSPENS, ET NON REFUSÉS : 4" in sortie


def test_appliquer_ECRIT_les_deux_populations(decor, capsys, tmp_path):
    assert outil.main(["--pas", "0", "--appliquer",
                       "--instantane", str(tmp_path)]) == 0
    sortie = _sortie(capsys)
    assert "NEQ posés                  : 3" in sortie
    par_nom = {c.nom_detecte: c.neq for c in decor.query(Company).all()}
    assert par_nom["Boulangerie Alpha inc"] == "1100000001", "l'égalité"
    assert par_nom["Imprimerie Gamma inc"] == "1100000006", "la confirmation"
    assert par_nom[outil.TEMOIN_DE_LA_CONTRADICTION + " inc"] is None
    assert par_nom["Quincaillerie Beta inc"] is None
    # ⚠️ L'instantané est écrit AVANT le commit, et porte l'état d'avant.
    instantanes = list(tmp_path.glob("statut-*.json"))
    assert len(instantanes) == 1, instantanes
    contenu = json.loads(instantanes[0].read_text(encoding="utf-8"))
    assert contenu["forme"] == outil.FORME_QUI_SECRIT
    assert contenu["portee"] == "les-deux"
    paire = contenu["a_poser"][0]
    assert paire["neq_avant"] is None
    assert paire["statut_avant"] == StatutResolution.AMBIGU.value
    assert paire["portee"] in outil.PORTEES, "la portée est TRACÉE dans l'instantané"
    assert "_concurrents" not in paire, "les champs de travail ne sont pas écrits"


def test_defaire_remet_l_etat_d_avant(decor, capsys, tmp_path):
    assert outil.main(["--pas", "0", "--appliquer",
                       "--instantane", str(tmp_path)]) == 0
    capsys.readouterr()
    chemin = next(iter(tmp_path.glob("statut-*.json")))
    assert outil.main(["--defaire", str(chemin)]) == 0
    assert all(c.neq is None for c in decor.query(Company).all())


def test_l_instantane_precedent_VERIFIE_que_rien_n_est_revenu(decor, capsys, tmp_path):
    """⚠️ **Les 1 065 du 20 septembre ne sont pas retouchés — vérifié, pas
    affirmé.** *La passe ne lit que `Company.neq IS NULL`.*"""
    pose = decor.query(Company).filter(
        Company.nom_detecte == "Boulangerie Alpha inc").one()
    pose.neq = "1100000001"
    revenu = decor.query(Company).filter(
        Company.nom_detecte == "Quincaillerie Beta inc").one()
    decor.commit()
    chemin = tmp_path / "statut-precedent.json"
    chemin.write_text(json.dumps({"a_poser": [
        {"company_id": pose.id}, {"company_id": revenu.id}]}), encoding="utf-8")

    assert outil.main(["--pas", "0", "--instantane-precedent", str(chemin)]) == 0
    bloc = _sortie(capsys).split("LES ÉGALITÉS DÉJÀ POSÉES")[1]
    assert "dossiers posés à cette passe" in bloc
    assert "n'ont PLUS de NEQ" in bloc
    assert str(revenu.id) in bloc


# ---------------------------------------------------------------------------
# ⚠️ D'OÙ L'EXCLUSION LIT LE STATUT — la question d'Alexandre du 21 septembre
# ---------------------------------------------------------------------------

def test_le_statut_qui_EXCLUT_vient_de_la_table_UPSERTEE(db_session):
    """⚠️ **`req_noms` sert à TROUVER, jamais à JUGER.**

    *La porte est GELÉE* — `req_noms` est écrite en `INSERT OR IGNORE` et rien
    ne la vide, donc un nom entré une fois y reste pour toujours. **Le jugement,
    lui, est FRAIS** : `_upsert_entreprise_reelle` réécrit `REQEntry.statut` à
    chaque import.

    Ce test met les deux en désaccord et vérifie laquelle décide : le nom gelé
    ouvre le lot, le statut frais le ferme. ⚠️ *Si un jour le scoreur rendait
    autre chose qu'une ligne de `req_entries`, la règle lirait un statut figé au
    premier import sans que rien ne le dise.*
    """
    from falkye.models.req_nom import REQNom
    from falkye.sources.req import resolve_neq_by_name
    from outils.paires_du_statut import restants_apres

    db_session.add(REQEntry(neq="1300000001", nom="Alpha Holdings",
                            nom_normalise=normaliser("Alpha Holdings"),
                            statut="radiee"))
    db_session.add(REQNom(neq="1300000001", nom="Zibeline Boulangerie",
                          nom_normalise=normaliser("Zibeline Boulangerie"),
                          statut="V", type_nom="NOM", gisement="NOM_ASSUJ"))
    db_session.commit()

    matches = resolve_neq_by_name(db_session, "Zibeline Boulangerie")
    assert [m.entry.neq for m in matches] == ["1300000001"], \
        "le nom de `req_noms` a bien ouvert la porte"
    assert isinstance(matches[0].entry, REQEntry), \
        "⚠️ l'entité rendue est la ligne UPSERTÉE, jamais la ligne gelée"
    assert matches[0].entry.statut == "radiee", \
        "le statut lu est celui de l'entreprise, pas le « V » du NOM"
    assert restants_apres(matches, outil.FORME_QUI_SECRIT) == [], \
        "le statut frais ferme le lot que le nom gelé avait ouvert"


# ---------------------------------------------------------------------------
# ⚠️ « LES EXCLUT TOUS » N'EST PAS TOUJOURS UN VERDICT DU CODE POSTAL
# ---------------------------------------------------------------------------

def test_une_GRAPHIE_de_ville_peut_renverser_un_code_postal_D_ACCORD():
    """⚠️ **Le mécanisme qu'Alexandre a mis au jour le 21 septembre**, trouvé en
    énumérant les configurations.

    *Le code postal du dossier est celui des DEUX candidats : il ne tranche pas,
    donc le repli descend jusqu'à la ville — et là, une graphie de municipalité
    exclut tout le monde.* **La sortie disait « l'adresse les exclut tous » alors
    que le code postal était d'accord avec le retenu.**
    """
    from outils.departageur_adresse import (
        NIVEAU_VILLE,
        FaitsDAdresse,
        departager_ladresse,
    )
    from outils.departageurs import AUCUN_COMPATIBLE, codes_postaux, fait_de_la_ville

    def faits(cp, ville):
        return FaitsDAdresse(codes_postaux(cp), fait_de_la_ville(ville))

    du_dossier = faits("G1A1A1", "Saint-Zephirin")
    lot = [faits("G1A1A1", "St-Zephirin"), faits("G1A1A1", "St-Zephirin")]
    departage = departager_ladresse(du_dossier, lot)

    assert departage.issue == AUCUN_COMPATIBLE, "la sortie disait « les exclut tous »"
    assert outil.niveau_qui_exclut(departage) == NIVEAU_VILLE, \
        "⚠️ et c'est la VILLE qui l'a prononcé, pas le code postal"
    assert departage.issue_du_niveau("code postal complet") != AUCUN_COMPATIBLE, \
        "le code postal, lui, n'excluait personne"


def test_niveau_qui_exclut_rend_None_quand_rien_n_exclut():
    """*Chaque valeur est un résultat* — `None` dit « aucune exclusion », et ne
    se confond pas avec « je ne sais pas par quel niveau »."""
    from outils.departageur_adresse import FaitsDAdresse, departager_ladresse
    from outils.departageurs import codes_postaux, fait_de_la_ville

    departage = departager_ladresse(
        FaitsDAdresse(codes_postaux("G1A1A1"), fait_de_la_ville(None)),
        [FaitsDAdresse(codes_postaux("G1A1A1"), None)])
    assert outil.niveau_qui_exclut(departage) is None
