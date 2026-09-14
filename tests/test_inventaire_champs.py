"""L'inventaire des champs — le préalable du chantier 12, généré et mesuré.

**Deux colonnes, et la seconde sauve le chantier de lui-même.** Ce que le code
déclare capter, et ce que les données portent vraiment. *`description_tender` était
déclaré par le connecteur SEAO depuis toujours et vide dans 100 % des cas : un
inventaire tiré du code seul l'aurait offert à une règle d'assurance.*
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

from outils.inventaire_champs import champs_declares, remplissage

RACINE = Path(__file__).resolve().parents[1]


def test_seao_declare_ce_que_le_registre_demandait():
    declare = champs_declares("falkye.sources.seao")

    assert "secteur_nature_contrat" in declare["champs"]
    assert "adresse_entreprise_adjudicataire" in declare["champs"]
    assert "description_tender" not in declare["champs"]  # retiré le 2026-09-13


def test_un_dictionnaire_VOISIN_nest_pas_pris_pour_un_champ():
    """Le test qui porte le choix de l'arbre syntaxique contre l'expression
    régulière. `falkye/sources/req.py` contient d'autres dictionnaires — ceux de
    l'inspection de zip, avec des clés comme `colonnes` et `exemple`. Une regex sur
    `"clé":` les aurait pris pour des champs captés, et le chantier 12 aurait cru
    disposer d'une matière qui n'existe pas."""
    declare = champs_declares("falkye.sources.req")

    assert "colonnes" not in declare["champs"]
    assert "exemple" not in declare["champs"]
    assert "taille_decompressee_octets" not in declare["champs"]


def test_une_expansion_est_SIGNALEE_plutot_que_tue():
    """`champs={"type_changement": ..., **etab}` : seul le run révèle les autres
    clés. Rendre la liste sans le dire la ferait croire complète."""
    declare = champs_declares("falkye.sources.req")

    assert declare["dynamiques"] is True
    assert "type_changement" in declare["champs"]


def test_les_identifiants_du_produit_ne_sont_pas_de_la_matiere():
    """`source_ref` et `signal_type_id` sont de la mécanique. Les inventorier ferait
    croire au 12 qu'il a sous la main une matière qu'il n'a pas."""
    for module in ("falkye.sources.seao", "falkye.sources.eimt"):
        declare = champs_declares(module)
        assert "source_ref" not in declare["attributs"]
        assert "signal_type_id" not in declare["attributs"]


def test_un_module_introuvable_le_dit_au_lieu_de_rendre_du_vide():
    assert "introuvable" in champs_declares("falkye.sources.inexistante")["erreur"]


def test_le_remplissage_compte_les_valeurs_distinctes(db_session):
    """Le nombre de valeurs distinctes sert le livrable 4 — un champ à presque
    autant de valeurs que de signaux est du texte libre, et l'inventaire le montre
    sans avoir à le déclarer."""
    from falkye.models.company import Company
    from falkye.models.signal import Signal

    c = Company(nom_detecte="X", nom_detecte_normalise="x")
    db_session.add(c)
    db_session.flush()
    for titre in ("Pavage", "Toiture", "Pavage"):
        db_session.add(
            Signal(
                company_id=c.id, source_id="seao", signal_type_id="appel_offres",
                detected_at=datetime.now(), titre_ou_description=titre,
                champs={"donneur_ordre": "Ville de Laval", "devise": None},
            )
        )
    db_session.commit()

    mesure = remplissage(db_session, "seao")

    assert mesure["signaux"] == 3
    assert mesure["par_cle"]["donneur_ordre"] == {"remplis": 3, "distinctes": 1}
    assert mesure["par_cle"]["titre_ou_description"] == {"remplis": 3, "distinctes": 2}
    assert "devise" not in mesure["par_cle"]  # None n'est pas une valeur


def test_une_source_sans_signal_rend_une_ABSENCE_pas_un_zero(db_session):
    mesure = remplissage(db_session, "eimt")

    assert mesure["signaux"] == 0
    assert mesure["par_cle"] == {}


def test_il_refuse_une_cible_que_personne_na_choisie(tmp_path):
    """Un taux de remplissage de 0 % sur une base vide se lit comme un champ mort."""
    fait = subprocess.run(
        [sys.executable, str(RACINE / "outils" / "inventaire_champs.py")],
        cwd=tmp_path,
        env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(RACINE), "HOME": str(tmp_path)},
        capture_output=True, text=True, check=False,
    )

    assert fait.returncode == 2, fait.stdout + fait.stderr
    assert "REFUS" in fait.stdout + fait.stderr
    assert "--sans-base" in fait.stdout + fait.stderr  # le repli est nommé


def test_sans_base_il_DIT_quil_ne_rend_quune_colonne(tmp_path):
    fait = subprocess.run(
        [sys.executable, str(RACINE / "outils" / "inventaire_champs.py"), "--sans-base"],
        cwd=tmp_path,
        env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(RACINE), "HOME": str(tmp_path)},
        capture_output=True, text=True, check=False,
    )

    assert fait.returncode == 0, fait.stdout + fait.stderr
    assert "COLONNE DU CODE SEULE" in fait.stdout
    assert "AUCUNE SPHÈRE N'EST ATTRIBUÉE" in fait.stdout
