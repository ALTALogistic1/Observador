"""Combien des restants sont hors de portée par nature.

⚠️ **Ce que ces tests verrouillent n'est pas un chiffre, c'est une DISCIPLINE :
qu'aucune heuristique ne sorte sans son étiquette, et qu'« aucune méthode ne
tient » reste un résultat que l'outil sait rendre.** *Un plancher estimé qui se
relit comme un plancher mesuré est le défaut que cet outil existe pour éviter —
donc c'est ce défaut-là qui est testé.*
"""
from __future__ import annotations

import datetime as _dt
import io
import zipfile

import pytest

from falkye.models.company import Company
from falkye.models.req_entry import REQEntry
from falkye.models.signal import Signal
from falkye.sources.column_mapping import normaliser
from outils import hors_de_portee_par_nature as outil


# ---------------------------------------------------------------------------
# LES RÈGLES DE LECTURE — avant la mesure qui les emploie
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("nom, attendu", [
    ("Lessard, Martin", outil.RETENU),
    ("DUBÉ, RICHARD", outil.RETENU),
    ("Saint-Jean, Marie-Claude", outil.RETENU),
    ("O'Brien, Patrick", outil.RETENU),
    # ⚠️ Les exclusions vont TOUTES dans le sens de l'erreur préférée :
    # elles font manquer, jamais déborder.
    ("Bolduc, Division inc.", outil.REJET_FORME_JURIDIQUE),
    ("Construction, Tremblay", outil.REJET_MOT_DENTREPRISE),
    ("Gagnon et Fils inc.", outil.REJET_PAS_LA_FORME),
    # ⚠️ *Une société à numéro tombe sur le JETON, avant toute exclusion* — et
    # c'est pour ça qu'une vérification `porte_un_chiffre` séparée ne pouvait
    # jamais se déclencher. **Elle a été écrite, puis retirée.**
    ("9528-9393, Québec", outil.REJET_PAS_LA_FORME),
    ("Martin Lessard", outil.REJET_PAS_LA_FORME),
    ("Tremblay, Jean, Marie", outil.REJET_PAS_LA_FORME),
    (None, outil.REJET_PAS_LA_FORME),
])
def test_la_regle_STRICTE_rend_la_RAISON_du_rejet_et_pas_un_booleen(nom, attendu):
    """*Une exclusion qui ne se voit pas ne se discute pas* — c'est pour ça que
    l'examen rend la raison et non un `True`/`False`."""
    assert outil.examiner_stricte(nom) == attendu


@pytest.mark.parametrize("nom, attendu", [
    ("Martin Lessard", outil.RETENU),
    # ⚠️ *C'est CE nom-là qui justifie de ne pas employer la règle lâche.*
    ("Bell Canada", outil.REJET_MOT_DENTREPRISE),
    ("Lessard, Martin", outil.REJET_PAS_LA_FORME),
    ("Bolduc inc.", outil.REJET_FORME_JURIDIQUE),
])
def test_la_regle_LACHE_existe_pour_que_le_DESSERRAGE_se_voie(nom, attendu):
    assert outil.examiner_lache(nom) == attendu


@pytest.mark.parametrize("nom", [
    "Lessard, Martin", "Martin Lessard", "Béton Bolduc inc.", "Bell Canada",
])
def test_les_deux_regles_sont_DISJOINTES_par_construction(nom):
    """*La stricte exige une virgule, la lâche l'interdit.* **Les additionner
    resterait faux pour une autre raison** — la lâche n'a pas la précision qui
    ferait un plancher — mais elles ne se chevauchent jamais."""
    retenus = [r for _e, r in outil.REGLES if r(nom) == outil.RETENU]
    assert len(retenus) <= 1, nom


def test_aucune_regle_de_rejet_n_est_INATTEIGNABLE():
    """⚠️ **Une garde qui ne se déclenche jamais se lit comme une protection sans
    en être une.** *`porte_un_chiffre` était dans ce cas : le jeton de patronyme
    exclut déjà les chiffres.* **Chaque raison affichable doit être atteignable
    par au moins un nom.**"""
    temoins = ("Gagnon et Fils inc.", "Bolduc, Division inc.", "Construction, Tremblay",
               "Bolduc inc.", "Bell Canada", "Martin Lessard", "Lessard, Martin")
    atteintes = {r(nom) for _e, r in outil.REGLES for nom in temoins}
    assert set(outil.ORDRE_DES_REJETS) <= atteintes, (
        set(outil.ORDRE_DES_REJETS) - atteintes)


def test_la_forme_juridique_est_IMPORTEE_jamais_recopiee():
    """⚠️ **Une règle recopiée à la main diverge de son original sans que rien ne
    le dise.** *C'est le défaut déjà payé quatre fois sur les gardes.*"""
    from outils import nature_des_restants

    assert outil.FORME_JURIDIQUE is nature_des_restants.FORME_JURIDIQUE


def test_les_codes_de_personne_physique_sont_LUS_a_la_source():
    libelles = {
        ("FORM_JURI", "IND"): "Personne physique exploitant une entreprise individuelle",
        ("FORM_JURI", "SPA"): "Société par actions",
        ("FORM_JURI", "XYZ"): "Entreprise individuelle sans raison sociale",
    }
    trouves = outil.codes_de_personne_physique(libelles)
    assert set(trouves) == {"IND", "XYZ"}, trouves


def test_la_graine_IND_survit_a_l_ABSENCE_des_libelles():
    """*`IND` est le code des 5 récupérations de `NOM_ETAB`, établi le 16
    septembre.* **Sans `DomaineValeur.csv`, il reste la seule graine** — et
    l'outil doit le DIRE, ce que verrouille le test de la sortie."""
    assert set(outil.codes_de_personne_physique({})) == {"IND"}


# ---------------------------------------------------------------------------
# LE VERDICT — c'est lui qui porte la discipline
# ---------------------------------------------------------------------------

STRICTE = outil.ETIQUETTE_STRICTE
LACHE = outil.REGLES[1][0]


def _verdict(capsys, precisions, taux_pont, retenus_stricte=100):
    code = outil._verdict(
        precisions, taux_pont, 4673,
        {STRICTE: [object()] * retenus_stricte, LACHE: []},
        {STRICTE: 12, LACHE: 900}, 2_700_000,
    )
    assert code == 0
    return capsys.readouterr().out


def test_un_taux_de_faux_positifs_TROP_HAUT_ne_pose_AUCUN_chiffre(capsys):
    """⚠️ **« Si aucune méthode ne tient, le dire est un résultat. »** *Et un
    critère qu'on desserre parce qu'il a échoué n'en est plus un.*"""
    sortie = _verdict(capsys, {STRICTE: (30, 100)}, 96.6)
    assert "LA MÉTHODE A NE TIENT PAS" in sortie
    assert "AUCUN CHIFFRE DE PLANCHER N'EST POSÉ" in sortie
    assert "plancher des restants HORS DE PORTÉE" not in sortie


def test_sans_ARCHIVE_le_verdict_n_est_PAS_rendu_et_le_miroir_ne_le_remplace_pas(capsys):
    """⚠️ *La spécificité du miroir est une AUTRE grandeur* — la substituer pour
    obtenir un verdict serait la confusion que l'outil existe pour éviter."""
    sortie = _verdict(capsys, None, None)
    assert "LE VERDICT N'EST PAS RENDU" in sortie
    assert "une AUTRE grandeur" in sortie
    assert "plancher des restants HORS DE PORTÉE" not in sortie


def test_zero_resolu_lisible_est_ZERO_MESURE_et_non_un_taux_de_zero(capsys):
    sortie = _verdict(capsys, {STRICTE: (0, 0)}, 96.6)
    assert "ZÉRO MESURE, pas un" in sortie
    assert "ni confirmée ni réfutée" in sortie
    assert "plancher des restants HORS DE PORTÉE" not in sortie


def test_sans_le_PONT_le_compte_reste_une_FORME_de_nom_et_pas_une_PORTEE(capsys):
    """*« Des restants dont le nom a la forme d'un patronyme » et « des restants
    hors de portée » ne sont pas le même chiffre.*"""
    sortie = _verdict(capsys, {STRICTE: (5, 100)}, None)
    assert "LE PONT T1 → T2 MANQUE" in sortie
    assert "plancher des restants HORS DE PORTÉE" not in sortie


def test_le_plancher_est_un_PRODUIT_dont_les_deux_facteurs_sont_ETIQUETES(capsys):
    """⚠️ **Poser un chiffre sur une heuristique sans dire qu'elle en est une est
    exactement ce qui est interdit.** *Donc chaque facteur porte, SUR SA LIGNE,
    ce qu'il est.*"""
    sortie = _verdict(capsys, {STRICTE: (5, 100)}, 96.6, retenus_stricte=100)
    heuristique = next(l for l in sortie.splitlines() if "règle stricte" in l
                       and "restants retenus" in l)
    assert "⚠️ HEURISTIQUE" in heuristique, heuristique
    mesure = next(l for l in sortie.splitlines() if "SANS nom publié" in l)
    assert "✅ MESURE" in mesure, mesure
    plancher = next(l for l in sortie.splitlines()
                    if "plancher des restants HORS DE PORTÉE" in l)
    # 100 × 96,6 % = 96,6 → 97.
    assert "97" in plancher, plancher
    assert "CE CHIFFRE EST UN PRODUIT" in sortie
    assert "PLANCHER\n   ESTIMÉ" in sortie or "PLANCHER ESTIMÉ" in sortie.replace(
        "PLANCHER\n   ESTIMÉ", "PLANCHER ESTIMÉ")
    assert "hérite de la faiblesse du premier" in sortie


def test_la_precision_mesuree_sur_les_RESOLUS_porte_sa_reserve_de_TRANSPORT(capsys):
    """*Les résolus sont sélectionnés pour être nommés; les restants pour ne pas
    l'être.* **Une indication portée d'une population à l'autre, jamais un
    transfert.**"""
    sortie = _verdict(capsys, {STRICTE: (5, 100)}, 96.6)
    assert "qui ne sont pas les" in sortie and "restants" in sortie
    assert "jamais un transfert" in sortie


def test_ce_qui_a_ete_ECARTE_est_nomme_pour_que_l_absence_se_discute(capsys):
    sortie = _verdict(capsys, {STRICTE: (5, 100)}, 96.6)
    for ecarte in ("LA JOINTURE PAR LE NEQ", "LA JOINTURE PAR L'ADRESSE",
                   "NOM_ETAB", "UNE LISTE DE PRÉNOMS"):
        assert ecarte in sortie, ecarte
    assert "5 récupérations, toutes de forme `IND`" in sortie


# ---------------------------------------------------------------------------
# LA MESURE, DE BOUT EN BOUT
# ---------------------------------------------------------------------------

def _archive(tmp_path):
    """Une archive minuscule, mais **complète** : sans `Nom.csv` le pont n'a pas
    de dénominateur, et sans `DomaineValeur.csv` la classification se replie."""
    chemin = tmp_path / "JeuDonnees-2026-09-15.zip"
    entreprises = [
        # NEQ, forme. Deux personnes physiques, une seule nommée → pont 50 %.
        ("1111111111", "IND"), ("1111111112", "IND"),
        ("8888888888", "SPA"), ("7777777777", "SPA"),
    ]
    noms = [("1111111111", "Lessard, Martin"), ("8888888888", "Béton Bolduc inc."),
            ("7777777777", "Hydro Solutions inc.")]
    def _csv(entetes, lignes):
        tampon = io.StringIO()
        graveur = csv.writer(tampon)
        graveur.writerow(entetes)
        graveur.writerows(lignes)
        return tampon.getvalue()
    with zipfile.ZipFile(chemin, "w") as zf:
        zf.writestr("Entreprise.csv", _csv(["NEQ", "COD_FORME_JURI"], entreprises))
        zf.writestr("Nom.csv", _csv(["NEQ", "NOM_ASSUJ"], noms))
        zf.writestr("DomaineValeur.csv", _csv(
            ["TYP_DOM_VAL", "COD_DOM_VAL", "VAL_DOM_FRAN"],
            [["FORM_JURI", "IND", "Personne physique exploitant une entreprise"],
             ["FORM_JURI", "SPA", "Société par actions"]]))
    return chemin


import csv  # noqa: E402  — utilisé par _archive, placé près de son emploi.


@pytest.fixture()
def decor(db_session, monkeypatch):
    """Trois restants dont deux patronymes, et deux résolus dont un patronyme
    qui EST une personne physique."""
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")

    dossiers = [
        (None, "Dubé, Richard", "rdprm"),
        (None, "Tremblay, Josée", "rdprm"),
        (None, "Excavation Bergeron inc.", "seao"),
        # ⚠️ Un résolu à forme de patronyme, ET personne physique : un VRAI
        # positif pour T1 — et un dossier que le registre A NOMMÉ, donc pas
        # hors de portée. C'est ce que la section 4 ne doit pas confondre.
        ("1111111111", "Lessard, Martin", "rdprm"),
        ("8888888888", "Béton Bolduc inc.", "seao"),
    ]
    for neq, nom, source in dossiers:
        company = Company(neq=neq, nom_detecte=nom, nom_detecte_normalise=normaliser(nom))
        db_session.add(company)
        db_session.flush()
        db_session.add(Signal(
            company_id=company.id, source_id=source,
            signal_type_id="recrutement_massif",
            detected_at=_dt.datetime(2026, 1, 1), champs={},
        ))
    # Le miroir : une entité NOMMÉE à forme de patronyme est un faux positif.
    for neq, nom in (("1111111111", "Lessard, Martin"),
                     ("8888888888", "Béton Bolduc inc.")):
        db_session.add(REQEntry(neq=neq, nom=nom, nom_normalise=normaliser(nom),
                                statut="immatriculee"))
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def test_la_DIFFICULTE_et_l_absence_de_cle_viennent_AVANT_tout_chiffre(decor, capsys):
    """⚠️ *« Il faut la nommer avant de chercher une méthode. »*"""
    assert outil.main([]) == 0
    sortie = capsys.readouterr().out
    assert sortie.index("IL EST SANS CLÉ") < sortie.index("dossiers au total")
    assert sortie.index("DÉJÀ IDENTIFIÉE") < sortie.index("dossiers au total")
    assert "96,6 %" in sortie and "n'est pas remesuré" in sortie.replace(
        "N'EST PAS REMESURÉ", "n'est pas remesuré")


def test_la_regle_du_verdict_est_POSEE_avant_de_voir_les_chiffres(decor, capsys):
    """*Un seuil choisi après coup n'est pas un seuil, c'est une
    justification.*"""
    assert outil.main([]) == 0
    sortie = capsys.readouterr().out
    assert sortie.index("POSÉE AVANT DE VOIR LE MOINDRE CHIFFRE") < sortie.index(
        "dossiers au total")


def test_les_deux_CIBLES_sont_distinguees_des_l_entete(decor, capsys):
    """⚠️ *Une précision calculée sur les résolus mesure T1, jamais T2.*"""
    assert outil.main([]) == 0
    sortie = capsys.readouterr().out
    assert "LES DEUX CIBLES, ET LES CONFONDRE RUINERAIT TOUT" in sortie
    assert "ils sont résolus, donc nommés" in sortie


def test_sans_chemin_les_sections_qui_lisent_une_FORME_disent_ZERO_MESURE(decor, capsys):
    assert outil.main([]) == 0
    sortie = capsys.readouterr().out
    assert "ZÉRO MESURE — pas « 0 % »" in sortie
    assert "LE VERDICT N'EST PAS RENDU" in sortie


def test_le_miroir_donne_une_SPECIFICITE_et_jamais_une_precision(decor, capsys):
    """*Toute entité du miroir EST nommée : tout nom que la règle y retient est
    un faux positif, sans supposition.*"""
    assert outil.main([]) == 0
    bloc = capsys.readouterr().out.split("4. CALIBRAGE")[1]
    assert "SPÉCIFICITÉ" in bloc and "Ce n'est PAS une précision" in bloc
    ligne = next(l for l in bloc.splitlines() if l.strip().startswith("STRICTE"))
    assert "1" in ligne and "faux positifs" in ligne, ligne


def test_avec_l_archive_la_precision_le_pont_et_la_source_sont_rendus(decor, capsys, tmp_path):
    assert outil.main(["--chemin", str(_archive(tmp_path))]) == 0
    sortie = capsys.readouterr().out
    # La section 4 : un résolu retenu par la stricte, personne physique → 0 faux.
    bloc = sortie.split("5. CALIBRAGE")[1].split("6. LE PONT")[0]
    assert "CIBLE T1, PAS T2" in sortie
    assert "IND" in bloc and "Personne physique" in bloc
    # Le pont : deux personnes physiques, une seule nommée → 50 %.
    pont = sortie.split("6. LE PONT")[1].split("7. MÉTHODE B")[0]
    ligne = next(l for l in pont.splitlines() if "AUCUN nom dans Nom.csv" in l)
    assert "50.0 %" in ligne, ligne
    # La méthode B : rdprm porte les deux restants à patronyme.
    source = sortie.split("7. MÉTHODE B")[1]
    rdprm = next(l for l in source.splitlines() if l.strip().startswith("rdprm"))
    assert rdprm.split()[1] == "2", rdprm
    assert "CE TAUX EST LUI-MÊME UN PLANCHER" in source


def test_le_taux_par_source_est_dit_PLANCHER_et_zero_mesure_n_est_pas_zero(decor, capsys, tmp_path):
    assert outil.main(["--chemin", str(_archive(tmp_path))]) == 0
    sortie = capsys.readouterr().out
    assert "n'apparaît\n      chez les résolus que si elle a déclaré un nom" in sortie
    assert "n'est pas un taux de 0 %" in sortie


def test_les_faux_NEGATIFS_sont_dits_NON_MESURABLES(decor, capsys, tmp_path):
    """⚠️ *On mesure ce qui déborde, jamais ce qui manque — et c'est pour ça que
    le chiffre est un plancher.*"""
    assert outil.main(["--chemin", str(_archive(tmp_path))]) == 0
    sortie = capsys.readouterr().out
    assert "TAUX DE FAUX NÉGATIFS N'EST MESURABLE NULLE PART" in sortie


def test_aucune_ecriture_et_les_echelles_ne_bougent_pas(decor, capsys, tmp_path):
    from falkye.resolution import SEUIL_AMBIGUITE_ECART_MIN, SEUIL_RESOLUTION_CONFIANTE

    assert outil.main(["--chemin", str(_archive(tmp_path))]) == 0
    sortie = capsys.readouterr().out
    assert (f"seuil {SEUIL_RESOLUTION_CONFIANTE:.0f}, "
            f"écart {SEUIL_AMBIGUITE_ECART_MIN:.0f}.") in sortie
    assert "RIEN N'A ÉTÉ ÉCRIT" in sortie
    assert all(c.neq in (None, "1111111111", "8888888888")
               for c in decor.query(Company).all())
