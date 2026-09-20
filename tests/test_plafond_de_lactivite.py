"""Le plafond de la piste de l'activité économique.

⚠️ **Ce que ces tests verrouillent est une SÉPARATION.** *Trois faits se
ressemblent et ne valent pas la même chose :* un **code** se relie par une table
qui n'existe pas, un **libellé** se compare mot à mot, une **profession** décrit
un poste et pas une entreprise. **Les fondre donnerait un plafond trop haut, et
personne ne verrait lequel des trois l'a gonflé.**
"""
from __future__ import annotations

import datetime as _dt
import re

import pytest

from falkye.models.company import Company
from falkye.models.req_entry import REQEntry
from falkye.models.signal import Signal
from falkye.sources.column_mapping import normaliser
from outils import plafond_de_lactivite as outil
# ⚠️ **Cinquième occurrence de `split()[-2]` sur une ligne qui finit par un
# pourcentage.** *Le helper existe dans `conftest.py` depuis N172, et je l'ai
# quand même refait à la main.* **Il est importé, cette fois.**
from tests.conftest import compte_de_la_ligne as _compte


# ---------------------------------------------------------------------------
# LA LECTURE DU CODE — c'est elle qui a corrigé l'affirmation de départ
# ---------------------------------------------------------------------------

def test_l_EIMT_ne_promeut_AUCUNE_activite_d_entreprise():
    """⚠️ *La moitié vraie de « l'EIMT n'a aucune classification ».* **Lue par
    arbre syntaxique, jamais supposée.**"""
    from outils.adresse_par_connecteur import (
        DOSSIER_CONNECTEURS,
        champs_promus_par_le_module,
    )

    eimt = DOSSIER_CONNECTEURS / "eimt.py"
    assert eimt.exists()
    assert champs_promus_par_le_module(eimt, champs=(outil.CHAMP_PROMU,)) == set()


def test_mais_l_EIMT_porte_bien_une_PROFESSION_et_elle_est_comptee_a_part():
    """⚠️ **La moitié fausse, et c'est elle qui change le compte.** *`Occupation`
    est lue et posée dans `champs["profession"]`.* **Une profession décrit un
    POSTE** — elle ne rejoint donc jamais le plafond."""
    from outils.adresse_par_connecteur import DOSSIER_CONNECTEURS, cles_lues_par_le_module

    cles = cles_lues_par_le_module(DOSSIER_CONNECTEURS / "eimt.py")
    assert "profession" in cles or "occupation" in {c.lower() for c in cles}
    cle, nature, _note = outil.CLES_DACTIVITE["eimt"]
    assert nature == outil.PROFESSION
    # ⚠️ La garde qui compte : la profession n'est PAS une des deux natures
    # que l'intersection additionne.
    assert nature not in (outil.CODE, outil.LIBELLE)


def test_chaque_cle_declaree_est_bien_DEPOSEE_par_son_connecteur():
    """*Une table de clés recopiée à côté se désynchronise en silence.*

    ⚠️ **Et le recoupement doit lire ce que le connecteur ÉCRIT dans `champs=`,
    pas ce qu'il LIT de son fichier.** *Écrit d'abord contre les clés lues, ce
    test tombait sur `secteur_nature_contrat` — qui n'est lue nulle part, elle
    est déposée.* **Une garde branchée sur la mauvaise source passe pour verte
    ou pour rouge, jamais pour juste.**
    """
    from outils.adresse_par_connecteur import DOSSIER_CONNECTEURS, cles_du_sac_par_le_module

    for source, (cle, _nature, _note) in outil.CLES_DACTIVITE.items():
        chemin = DOSSIER_CONNECTEURS / f"{source}.py"
        assert chemin.exists(), source
        assert cle in cles_du_sac_par_le_module(chemin), (source, cle)


def test_le_lecteur_d_arbre_est_EMPRUNTE_jamais_recopie():
    from outils import adresse_par_connecteur

    assert outil.cles_lues_par_le_module is adresse_par_connecteur.cles_lues_par_le_module
    assert (outil.champs_promus_par_le_module
            is adresse_par_connecteur.champs_promus_par_le_module)
    assert (outil.cles_du_sac_par_le_module
            is adresse_par_connecteur.cles_du_sac_par_le_module)


# ---------------------------------------------------------------------------
# LES TROIS PROVENANCES — séparées, jamais fondues
# ---------------------------------------------------------------------------

class _Dossier:
    def __init__(self, libelle=None):
        self.secteur_activite_libelle = libelle


@pytest.mark.parametrize("libelle, champs, attendu", [
    (None, {"secteur_nature_contrat": [{"code": "72101"}]}, {outil.CODE}),
    ("Plomberie", None, {outil.LIBELLE}),
    (None, {"profession": "Cuisinier"}, {outil.PROFESSION}),
    ("Plomberie", {"objet_economique": "1234"}, {outil.LIBELLE, outil.CODE}),
    (None, None, set()),
])
def test_les_trois_provenances_sont_rendues_SEPAREMENT(libelle, champs, attendu):
    assert set(outil.activites_du_dossier(_Dossier(libelle), champs)) == attendu


class _Match:
    def __init__(self, code):
        self.entry = type("E", (), {"secteur_code": code})()


def test_les_candidats_SANS_code_sont_gardes_car_inconnu_n_est_pas_non():
    """⚠️ *Un départage exige le fait chez TOUS les concurrents.* **Jeter les
    `None` ferait passer un dossier incomplet pour un dossier complet.**"""
    assert outil.codes_des_candidats([_Match("111"), _Match(None)]) == ["111", None]


# ---------------------------------------------------------------------------
# LA MESURE, DE BOUT EN BOUT
# ---------------------------------------------------------------------------

@pytest.fixture()
def decor(db_session, monkeypatch):
    """Un ambigu dont les deux candidats portent des codes DIFFÉRENTS, un dont
    ils portent le MÊME, et un dont un candidat n'en porte aucun."""
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")

    dossiers = [
        ("Beton Bolduc", "seao", {"secteur_nature_contrat": [{"code": "72101"}]}),
        ("Plomberie Roy", "eimt", {"profession": "Plombier"}),
        ("Transport Gagne", "seao", {}),
    ]
    for nom, source, champs in dossiers:
        company = Company(neq=None, nom_detecte=nom, nom_detecte_normalise=normaliser(nom))
        db_session.add(company)
        db_session.flush()
        db_session.add(Signal(
            company_id=company.id, source_id=source,
            signal_type_id="recrutement_massif",
            detected_at=_dt.datetime(2026, 1, 1), champs=champs,
        ))
    # Deux entrées proches par nom pour chaque dossier → des ambigus.
    miroir = [
        ("1111111111", "Beton Bolduc", "5511"), ("1111111112", "Beton Bolduc", "6622"),
        ("2222222221", "Plomberie Roy", "7733"), ("2222222222", "Plomberie Roy", "7733"),
        ("3333333331", "Transport Gagne", "8844"), ("3333333332", "Transport Gagne", None),
    ]
    for neq, nom, secteur in miroir:
        db_session.add(REQEntry(neq=neq, nom=nom, nom_normalise=normaliser(nom),
                                statut="immatriculee", secteur_code=secteur))
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def _sortie(capsys):
    return capsys.readouterr().out


def test_ce_que_la_mesure_ne_dira_pas_vient_AVANT_tout_chiffre(decor, capsys):
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    assert sortie.index("SERAIT JUSTE") < sortie.index("RESTANTS (sans NEQ)")
    assert sortie.index("CETTE TABLE N'EXISTE") < sortie.index("RESTANTS (sans NEQ)")


def test_la_table_du_chantier_22_n_est_ni_construite_ni_ESQUISSEE(decor, capsys):
    """⚠️ **Remplir la place d'un chantier fermé est ce que le cas 39 a coûté.**
    *Aucune famille ne se nomme, aucune correspondance ne s'écrit.*"""
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    assert "chantier 22" in sortie and "n'est pas ouvert" in sortie
    assert "53 familles" not in sortie
    # ⚠️ **La garde vise une CORRESPONDANCE, pas le nom de la table.** *Écrite
    # contre « → CAE », elle tombait sur la phrase qui DIT que la table n'existe
    # pas* — même défaut qu'en N180, et la bonne portée est plus étroite.
    # Ce qui est interdit est un code mis en face d'un autre.
    assert not re.search(r"\b\d{3,}\s*(?:→|->|=)\s*\d{3,}", sortie), sortie


def test_la_population_du_17_septembre_est_citee_comme_NON_comparable(decor, capsys):
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    assert str(outil.AMBIGUS_DU_17) in sortie.replace(" ", "")
    assert "NE SONT PAS LES MÊMES" in sortie
    assert "AMBIGUS AUJOURD'HUI" in sortie


def test_l_affirmation_sur_l_EIMT_est_corrigee_DANS_la_sortie(decor, capsys):
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    assert "À MOITIÉ FAUX" in sortie
    assert "profession d'un POSTE" in sortie


def test_le_code_au_dossier_est_VERIFIE_et_pas_deduit(decor, capsys):
    """*Une garde qui se déduit n'est pas une garde.*"""
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    assert "Company.secteur_activite_code rempli : 0" in sortie
    assert "Vérifié, pas déduit" in sortie


def test_certains_seulement_n_est_PAS_compté_comme_registre_complet(decor, capsys):
    """⚠️ *Inconnu n'est pas non.* **Le dossier dont un candidat n'a pas de code
    tombe dans « certains seulement », jamais dans le plafond.**"""
    assert outil.main(["--pas", "0"]) == 0
    bloc = _sortie(capsys).split("3. CÔTÉ REGISTRE")[1]
    tous = next(l for l in bloc.splitlines() if "TOUS les candidats" in l)
    certains = next(l for l in bloc.splitlines() if "certains seulement" in l)
    assert _compte(tous) == "2", tous
    assert _compte(certains) == "1", certains
    assert "inconnu n'est pas non" in bloc


def test_la_BORNE_ne_retient_que_les_codes_qui_DIFFERENT(decor, capsys):
    """*Porter une activité des deux côtés ne départage rien si tous les
    candidats portent la MÊME.* **Ici : un seul dossier sur deux.**"""
    assert outil.main(["--pas", "0"]) == 0
    bloc = _sortie(capsys).split("5. LA BORNE")[1]
    ligne = next(l for l in bloc.splitlines() if "codes différents entre eux" in l)
    assert _compte(ligne) == "1", ligne
    assert "pas une traduction" in bloc


def test_la_profession_ne_monte_JAMAIS_dans_le_plafond(decor, capsys):
    """*`Plomberie Roy` ne porte qu'une profession, et ses deux candidats ont le
    même code.* **Il ne peut apparaître dans aucune des deux bornes.**"""
    assert outil.main(["--pas", "0"]) == 0
    bloc = _sortie(capsys).split("4. L'INTERSECTION")[1].split("5. LA BORNE")[0]
    ligne_a = next(l for l in bloc.splitlines() if "(a) détecté porte un CODE" in l)
    assert _compte(ligne_a) == "1", ligne_a
    assert "LA PROFESSION N'EST DANS NI L'UN NI L'AUTRE" in bloc


def test_les_deux_provenances_du_code_du_registre_sont_NOMMEES(decor, capsys):
    """⚠️ *Le 99,6 % de `COD_ACT_ECON_CAE` ne se transporte pas au miroir.*"""
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    assert "COD_ACT_ECON_CAE` n'est\n      JAMAIS lu" in sortie
    assert "DEUX PROVENANCES" in sortie


def test_aucune_ecriture_et_les_echelles_ne_bougent_pas(decor, capsys):
    from falkye.resolution import SEUIL_AMBIGUITE_ECART_MIN, SEUIL_RESOLUTION_CONFIANTE

    avant = {c.id: c.neq for c in decor.query(Company).all()}
    assert outil.main(["--pas", "0"]) == 0
    sortie = _sortie(capsys)
    assert (f"seuil {SEUIL_RESOLUTION_CONFIANTE:.0f}, "
            f"écart {SEUIL_AMBIGUITE_ECART_MIN:.0f}.") in sortie
    assert "RIEN N'A ÉTÉ ÉCRIT" in sortie
    assert {c.id: c.neq for c in decor.query(Company).all()} == avant
