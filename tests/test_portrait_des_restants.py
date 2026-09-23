"""Le portrait des restants — ce qu'ils SONT, pas pourquoi ils échouent.

⚠️ **Ce que ces tests verrouillent est une RETENUE.** *Après cinq hypothèses
tombées, la tentation est de classer les dossiers par ce qu'on croit d'eux.*
**Un axe est un fait que le produit porte; « probablement récupérable » est une
sixième théorie déguisée en mesure** — et c'est ce déguisement qui est testé.
"""
from __future__ import annotations

import datetime as _dt

import pytest

from falkye.models.company import Company
from falkye.models.req_entry import REQEntry
from falkye.models.signal import Signal
from falkye.sources.column_mapping import normaliser
from outils import portrait_des_restants as outil


# ---------------------------------------------------------------------------
# LES AXES — des faits, avant la mesure qui les emploie
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("k, attendu", [
    (0, "aucun"), (1, "1"), (2, "2"), (3, "3 à la coupe"), (5, "3 à la coupe"),
])
def test_les_tranches_de_candidats_prennent_toute_la_droite(k, attendu):
    assert outil.tranche_de_candidats(k) == attendu


def test_aucune_tranche_ne_peut_rester_VIDE_par_construction():
    """⚠️ **Le défaut du 22 septembre.** *Les tranches allaient jusqu'à « plus de
    100 », et trois d'entre elles ne pouvaient JAMAIS se remplir* —
    `resolve_neq_by_name` coupe le lot à cinq. **La sortie annonçait « aucun n'en
    a plus de 5 » comme un fait de population, alors que c'est le plafond de
    l'instrument, et la ligne allait entrer au corpus.**

    *Une tranche d'affichage qui ne peut pas se remplir n'est pas une précaution :
    c'est une affirmation sur la population, faite par la forme du tableau.*
    """
    from outils.valeur_des_contradictions import coupe_de_production

    coupe = coupe_de_production()
    bornes = [b for b, _e in outil.TRANCHES_DE_CANDIDATS if b is not None]
    assert max(bornes) < coupe, (
        f"une borne d'affichage dépasse la coupe du produit ({coupe}) — "
        "la tranche au-delà ne pourra jamais se remplir")


@pytest.mark.parametrize("score, attendu", [
    # ⚠️ *« aucun candidat » N'EST PAS un score de zéro.*
    (None, "aucun candidat"),
    (0.0, "moins de 50"),
    (91.9, "90 à 91,9 ← sous le seuil"),
    (92.0, "92 et plus ← FRANCHIT le seuil"),
    (100.0, "92 et plus ← FRANCHIT le seuil"),
])
def test_aucun_candidat_et_un_score_de_zero_ne_sont_pas_la_meme_tranche(score, attendu):
    assert outil.tranche_de_score(score) == attendu


def test_la_borne_du_score_est_bien_CELLE_du_produit():
    """*Une borne d'affichage recopiée de travers déplacerait la seule frontière
    qui décide.*"""
    from falkye.resolution import SEUIL_RESOLUTION_CONFIANTE

    bornes = [b for b, _e in outil.TRANCHES_DE_SCORE]
    assert SEUIL_RESOLUTION_CONFIANTE in bornes, bornes


@pytest.mark.parametrize("jours, attendu", [
    # ⚠️ *Une ABSENCE de date et une date ancienne ne sont pas le même fait.*
    (None, "aucun signal daté"),
    (0, "30 jours ou moins"), (30, "30 jours ou moins"), (31, "31 à 90 jours"),
    (365, "181 à 365 jours"), (366, "PLUS D'UN AN"), (4000, "PLUS D'UN AN"),
])
def test_une_absence_de_date_n_est_pas_un_age(jours, attendu):
    assert outil.tranche_dage(jours) == attendu


class _Faits:
    def __init__(self, complet=None, region=None, ville=None):
        self.code_complet, self.region_de_tri, self.ville = complet, region, ville


@pytest.mark.parametrize("faits, attendu", [
    # ⚠️ *Un code complet porte TOUJOURS sa région de tri* — l'échelle le compte
    # une seule fois, au niveau le plus fin.
    (_Faits(complet="x", region="x", ville="v"), outil.NIVEAU_CODE_COMPLET),
    (_Faits(region="x", ville="v"), outil.NIVEAU_REGION_DE_TRI),
    (_Faits(ville="v"), outil.NIVEAU_VILLE),
    (_Faits(), outil.NIVEAU_RIEN),
    (None, outil.NIVEAU_RIEN),
])
def test_l_echelle_d_adresse_est_EXCLUSIVE_du_plus_fin_au_plus_large(faits, attendu):
    assert outil.finesse_de(faits) == attendu


@pytest.mark.parametrize("nom, norm, attendues", [
    ("9231-4567 Québec inc.", "9231 4567 quebec inc", {outil.FORME_TETE_NUMERIQUE}),
    ("Béton Bolduc inc.", "beton bolduc inc", {outil.FORME_TOUTES_LETTRES}),
    ("Altis (Ottawa) Inc.", "altis ottawa inc",
     {outil.FORME_TOUTES_LETTRES, outil.FORME_PARENTHESE}),
    ("X inc. & Y inc.", "x inc y inc",
     {outil.FORME_TOUTES_LETTRES, outil.FORME_CONJONCTION}),
])
def test_la_tete_est_exclusive_et_les_autres_formes_s_accumulent(nom, norm, attendues):
    assert outil.formes_du_nom(nom, norm) == attendues


def test_la_tete_est_numerique_OU_en_lettres_jamais_les_deux():
    for nom, norm in (("9231-4567 Québec", "9231 4567 quebec"), ("Bolduc", "bolduc")):
        trouvees = outil.formes_du_nom(nom, norm)
        exclusives = trouvees & {outil.FORME_TETE_NUMERIQUE, outil.FORME_TOUTES_LETTRES}
        assert len(exclusives) == 1, (nom, trouvees)


def test_la_conjonction_ici_est_le_fait_BRUT_et_pas_la_regle_des_consortiums():
    """⚠️ **Les deux chiffres ne sont pas comparables, et le test le dit.**
    *`« Gagnon et Fils inc. »` porte une conjonction — ce n'est PAS un
    consortium, qui exige DEUX formes juridiques.*"""
    from outils.nature_des_restants import nomme_plusieurs_entites

    nom = "Gagnon et Fils inc."
    assert outil.FORME_CONJONCTION in outil.formes_du_nom(nom, normaliser(nom))
    assert nomme_plusieurs_entites(nom) is False


def test_aucune_etiquette_ne_DEPASSE_sa_colonne():
    """⚠️ **Une étiquette plus longue que sa colonne POUSSE le nombre**, et la
    ligne cesse d'être alignée sans qu'aucun chiffre ait bougé. *C'est arrivé
    trois fois en trois outils* — donc c'est un test, plus un relecteur."""
    etiquettes = (
        [e for _b, e in outil.TRANCHES_DE_CANDIDATS]
        + [e for _b, e in outil.TRANCHES_DE_SCORE]
        + [e for _b, e in outil.TRANCHES_DE_SIGNAUX]
        + [e for _b, e in outil.TRANCHES_DE_SOURCES]
        + [e for _b, e in outil.TRANCHES_DAGE]
        + [e for _b, e in outil.TRANCHES_DE_LONGUEUR]
        + list(outil.ECHELLE_DADRESSE) + list(outil.FORMES_DU_NOM)
        + ["aucun signal daté"]
    )
    trop_longues = [e for e in etiquettes if len(e) > outil.LARGEUR_DES_AXES]
    assert not trop_longues, trop_longues


def test_aucune_etiquette_de_CROISEMENT_ne_depasse_sa_colonne():
    """⚠️ *Le même défaut vit dans les croisements, avec d'autres largeurs.* **Et
    l'identifiant de source le plus long du registre fait 34 caractères** — une
    colonne plus étroite le tronquerait, et une source tronquée ne se reconnaît
    plus."""
    import re as _re
    from pathlib import Path as _Path

    profils = [len(p) for p in outil.PROFILS]
    assert max(profils) <= outil.LARGEUR_DES_PROFILS, outil.PROFILS
    signaux = [len(e) for _b, e in outil.TRANCHES_DE_SIGNAUX]
    assert max(signaux) <= outil.LARGEUR_DES_SIGNAUX

    # ⚠️ Les sources sont lues DANS LE REGISTRE, pas devinées : le jour où l'on
    # en ajoute une plus longue, c'est ce test qui tombe, pas la mise en page.
    yaml = _Path(__file__).resolve().parent.parent / "falkye" / "registry" / "sources.yaml"
    ids = _re.findall(r"^\s+-?\s*id:\s*([A-Za-z0-9_]+)", yaml.read_text(encoding="utf-8"), _re.M)
    assert ids, "aucun identifiant de source lu — la garde ne garde rien"
    trop_longs = [i for i in ids if len(i) > outil.LARGEUR_DES_SOURCES]
    assert not trop_longs, trop_longs


def test_deux_colonnes_de_famille_ne_se_TOUCHENT_jamais():
    """*Deux nombres collés se lisent comme un seul* — et ils se touchaient."""
    plus_longue = max(len(a) for a in outil.ABREGE.values())
    assert plus_longue < outil.LARGEUR_DUNE_FAMILLE, outil.ABREGE


def test_chaque_famille_du_produit_a_son_ABREGE():
    """*Une famille sans abrégé s'afficherait en entier et casserait la
    colonne* — et `FAMILLES` peut changer sans que ce fichier bouge."""
    from falkye.resolution import FAMILLES

    assert set(FAMILLES) <= set(outil.ABREGE), set(FAMILLES) - set(outil.ABREGE)


def test_est_numero_est_EMPRUNTE_jamais_recopie():
    """*Une règle recopiée perd la réserve qui l'accompagne* — ici, que la source
    nomme presque toujours ces entreprises par leur enseigne."""
    from outils import diagnostic_appariement

    assert outil.est_numero is diagnostic_appariement.est_numero


# ---------------------------------------------------------------------------
# LA MESURE, DE BOUT EN BOUT
# ---------------------------------------------------------------------------

@pytest.fixture()
def decor(db_session, monkeypatch):
    """Quatre restants de profils distincts, et deux résolus pour le rapport."""
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")
    vieux = _dt.datetime(2020, 1, 1)
    recent = _dt.datetime.now() - _dt.timedelta(days=3)

    #: (neq, nom, ville, code postal, [(source, quand)])
    dossiers = [
        # Un restant à UN signal, nom en lettres, code postal complet, récent.
        (None, "Excavation Bergeron", "Laval", "H7N 1A1", [("seao", recent)]),
        # Un restant à tête numérique, sans adresse, et VIEUX de plus d'un an.
        (None, "9231-4567 Québec inc.", None, None, [("eimt", vieux)]),
        # Un restant vu par DEUX sources, avec parenthèse et conjonction.
        (None, "Altis (Ottawa) inc. & Fils", "Gatineau", None,
         [("seao", recent), ("eimt", recent)]),
        # Un restant dont le nom correspond EXACTEMENT à une entrée du miroir.
        (None, "Béton Bolduc inc.", "Québec", "G1V 2M2", [("seao", recent)]),
        ("7777777777", "Résolu Un inc.", "Laval", "H7N 1A1", [("seao", recent)]),
        ("8888888888", "Résolu Deux inc.", None, None, [("eimt", vieux)]),
    ]
    for neq, nom, ville, code, signaux in dossiers:
        company = Company(neq=neq, nom_detecte=nom, nom_detecte_normalise=normaliser(nom),
                          ville=ville, code_postal=code)
        db_session.add(company)
        db_session.flush()
        for source, quand in signaux:
            db_session.add(Signal(
                company_id=company.id, source_id=source,
                signal_type_id="recrutement_massif", detected_at=quand, champs={},
            ))
    for neq, nom in (("1212121212", "Béton Bolduc inc."),
                     ("1313131313", "Béton Bolduc et Frères inc.")):
        db_session.add(REQEntry(neq=neq, nom=nom, nom_normalise=normaliser(nom),
                                statut="immatriculee", ville="Québec"))
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def _sortie(capsys):
    return capsys.readouterr().out


def test_ce_que_la_mesure_ne_fera_PAS_vient_avant_tout_chiffre(decor, capsys):
    """⚠️ *« Elle dit ce qu'ils sont. C'est un portrait, pas une explication. »*"""
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    assert sortie.index("ELLE NE DIRA PAS POURQUOI ILS ÉCHOUENT") < sortie.index(
        "dossiers au total")
    assert sortie.index("AUCUN CLASSEMENT PAR JUGEMENT") < sortie.index(
        "dossiers au total")


def test_aucune_categorie_de_JUGEMENT_n_apparait_dans_les_TABLEAUX(decor, capsys):
    """⚠️ **La garde la plus importante du fichier.** *Une sixième théorie se
    reconnaît à ses mots* — et elle ne doit apparaître ni comme axe, ni comme
    ligne de tableau.

    ⚠️ **Elle est bornée aux SECTIONS, et l'en-tête en est exclu à dessein.**
    *Écrite sur toute la sortie, elle tombait sur la phrase qui INTERDIT ces
    mots* — une garde qui lit des lignes ne distingue pas un libellé de la
    phrase qui le proscrit. **Et c'est le tableau qu'elle doit surveiller, pas
    la prose : un jugement se glisse dans une étiquette, jamais dans un
    avertissement.**
    """
    assert outil.main(["--pas", "0"]) == 0
    sections = _sortie(capsys).split("1. LA FAMILLE DE DÉCISION")[1].lower()
    for juge in ("probablement récupérable", "probablement pas", "récupérable",
                 "irrécupérable", "perdu d'avance", "à abandonner"):
        assert juge not in sections, juge


def test_les_axes_que_les_RESOLUS_portent_aussi_rendent_les_deux_populations(decor, capsys):
    """*« 38 % des restants n'ont qu'un signal » ne se compare à rien.*"""
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    for titre in ("3. SIGNAUX ET SOURCES", "4. LA FINESSE D'ADRESSE",
                  "5. LA FORME DU NOM", "6. L'ÂGE DU SIGNAL"):
        bloc = sortie.split(titre)[1][:1400]
        entete = next(l for l in bloc.splitlines() if "restants" in l and "résolus" in l)
        assert "rapport" in entete, (titre, entete)


def test_les_deux_premiers_axes_n_existent_QUE_pour_les_restants(decor, capsys):
    """*Un résolu porte déjà son NEQ : lui rejouer une famille ne dirait rien.*"""
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    for titre in ("1. LA FAMILLE DE DÉCISION", "2. CANDIDATS TROUVÉS"):
        bloc = sortie.split(titre)[1].split("-" * 78)[0]
        assert "résolus" not in bloc, (titre, bloc[:300])


def test_l_echelle_d_adresse_TOTALISE_la_population(decor, capsys):
    """⚠️ *L'exclusivité est MESURÉE, pas affirmée* — si un dossier tombait dans
    deux niveaux, le total dépasserait la population."""
    assert outil.main(["--pas", "0"]) == 0
    bloc = _sortie(capsys).split("4. LA FINESSE D'ADRESSE")[1].split("⚠️")[0]
    total = 0
    for niveau in outil.ECHELLE_DADRESSE:
        ligne = next(l for l in bloc.splitlines() if l.strip().startswith(niveau))
        total += int(ligne.split()[len(niveau.split())])
    assert total == 4, bloc


def test_la_famille_est_celle_du_PRODUIT_et_le_rejeu_passe_par_la_passe(decor, capsys):
    """*`Béton Bolduc inc.` a un homonyme au miroir : le rejeu doit le VOIR.*"""
    from falkye.resolution import FAMILLES

    assert outil.main(["--pas", "0"]) == 0
    bloc = _sortie(capsys).split("1. LA FAMILLE DE DÉCISION")[1].split("⚠️")[0]
    for famille in FAMILLES:
        assert any(l.strip().startswith(famille) for l in bloc.splitlines()), famille
    # Deux entrées du miroir se ressemblent : le dossier n'est pas « aucun candidat ».
    aucun = next(l for l in bloc.splitlines() if l.strip().startswith("aucun candidat"))
    assert aucun.split()[2] == "3", aucun


def test_les_trois_croisements_demandes_sont_rendus(decor, capsys):
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    # ⚠️ *Une abréviation sans sa légende se devine, et on devine mal.*
    assert "faible = trop faible" in sortie and "aucun = aucun candidat" in sortie
    for croisement in ("a. LA FAMILLE SELON LE NOMBRE DE SIGNAUX",
                       "b. LA FAMILLE SELON LA SOURCE",
                       "c. LA FAMILLE SELON LA FORME DU NOM"):
        assert croisement in sortie, croisement
    assert "Les lignes ne s'additionnent pas au total" in sortie


def test_une_part_de_croisement_est_rendue_avec_SA_BASE(decor, capsys):
    """*`100 %` sur trois dossiers et `100 %` sur trois mille ne disent pas la
    même chose.*"""
    assert outil.main(["--pas", "0"]) == 0
    bloc = _sortie(capsys).split("a. LA FAMILLE SELON LE NOMBRE DE SIGNAUX")[1]
    entete = next(l for l in bloc.splitlines() if "dossiers" in l)
    assert "dossiers" in entete, entete
    ligne = next(l for l in bloc.splitlines() if l.strip().startswith("1 seul"))
    assert ligne.split()[2] == "3", ligne


def test_deux_faits_ensemble_n_expliquent_rien_et_la_sortie_le_redit(decor, capsys):
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    assert "deux faits ensemble, jamais une cause" in sortie
    assert "CE PORTRAIT NE DIT PAS POURQUOI ILS ÉCHOUENT" in sortie


def test_aucune_ecriture(decor, capsys):
    from falkye.resolution import SEUIL_AMBIGUITE_ECART_MIN, SEUIL_RESOLUTION_CONFIANTE

    avant = {c.id: c.neq for c in decor.query(Company).all()}
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    assert (f"seuil\n   {SEUIL_RESOLUTION_CONFIANTE:.0f}, "
            f"écart {SEUIL_AMBIGUITE_ECART_MIN:.0f}") in sortie
    assert "RIEN N'A ÉTÉ ÉCRIT" in sortie
    assert {c.id: c.neq for c in decor.query(Company).all()} == avant
