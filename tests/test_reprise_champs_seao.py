"""La reprise du passé complète, n'écrase pas, et ne crée rien.

`champs` s'écrit à l'ingestion, et la déduplication par `source_ref` fait qu'un avis
déjà vu ne repasse jamais : sans reprise, les 2 280 signaux SEAO antérieurs au
2026-09-13 resteraient sans classification, pour toujours. *« Un produit qui distingue
les signaux futurs et pas les anciens serait à moitié calibré. »*
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from outils.reprise_champs_seao import champs_du_fichier, completer, periode_des_signaux

RACINE = Path(__file__).resolve().parents[1]

RELEASE = {
    "ocid": "ocds-1", "id": "r-1", "date": "2026-09-02T12:00:00Z",
    "buyer": {"id": "QC-1", "name": "Ville de Laval"},
    "parties": [
        {"id": "QC-2", "name": "Untel", "roles": ["supplier"],
         "address": {"streetAddress": "12 rue X", "locality": "Laval", "region": "QC"}},
    ],
    "tender": {"title": "Réfection", "items": [
        {"id": "1", "description": "Pavage",
         "classification": {"scheme": "UNSPSC", "id": "72141100", "description": "Pavage"}},
    ]},
    "awards": [{"id": "a-1", "date": "2026-09-02T12:00:00Z", "status": "active",
                "value": {"amount": 1000, "currency": "CAD"},
                "suppliers": [{"id": "QC-2", "name": "Untel"}]}],
}


class _Signal:
    def __init__(self, champs):
        self.champs = champs


def test_la_cle_est_celle_du_moteur_pas_une_copie(tmp_path):
    """Si l'outil recalculait la clé de son côté, une divergence d'un caractère ne
    raterait pas quelques signaux — elle les raterait TOUS, et le rapport dirait
    « aucun signal trouvé » au lieu de « la clé a changé »."""
    from falkye.sources.seao import source_ref_pour

    chemin = tmp_path / "f.json"
    chemin.write_text(json.dumps({"releases": [RELEASE]}), encoding="utf-8")

    par_ref = champs_du_fichier(chemin)

    assert list(par_ref) == [source_ref_pour(RELEASE, RELEASE["awards"][0])]


def test_les_champs_repris_sont_ceux_du_connecteur(tmp_path):
    chemin = tmp_path / "f.json"
    chemin.write_text(json.dumps({"releases": [RELEASE]}), encoding="utf-8")

    champs = next(iter(champs_du_fichier(chemin).values()))

    assert champs["donneur_ordre_id"] == "QC-1"
    assert champs["secteur_nature_contrat"][0]["code"] == "72141100"
    assert champs["adresse_entreprise_adjudicataire"]["ville"] == "Laval"
    assert champs["description_besoins"] == ["Pavage"]


def test_une_valeur_existante_nest_JAMAIS_ecrasee():
    """L'outil ne sait pas si une valeur vient du connecteur ou d'une correction à
    la main. Une reprise qui écrase n'est plus une reprise."""
    signal = _Signal({"donneur_ordre": "Corrigé à la main"})

    change = completer(signal, {"donneur_ordre": "Ville de Laval", "donneur_ordre_id": "QC-1"})

    assert change is True
    assert signal.champs["donneur_ordre"] == "Corrigé à la main"
    assert signal.champs["donneur_ordre_id"] == "QC-1"


def test_une_valeur_vide_dans_la_source_ne_remplace_rien():
    signal = _Signal({})

    change = completer(signal, {"secteur_nature_contrat": [], "description_besoins": None})

    assert change is False
    assert signal.champs == {}


def test_un_signal_deja_complet_ne_compte_pas_comme_ecriture():
    signal = _Signal({"donneur_ordre_id": "QC-1"})

    assert completer(signal, {"donneur_ordre_id": "QC-1"}) is False


def test_les_champs_sont_REASSIGNES_pour_que_sqlalchemy_les_voie(db_session):
    """Une mutation en place d'un dict JSON passe inaperçue : l'`UPDATE` ne partirait
    pas, et le rapport dirait « complété » sans que rien ne soit écrit."""
    from falkye.models.company import Company
    from falkye.models.signal import Signal

    c = Company(nom_detecte="X", nom_detecte_normalise="x")
    db_session.add(c)
    db_session.flush()
    signal = Signal(
        company_id=c.id, source_id="seao", signal_type_id="appel_offres",
        detected_at=datetime.now(), source_ref="seao:ocds-1:a-1", champs={"devise": "CAD"},
    )
    db_session.add(signal)
    db_session.commit()

    completer(signal, {"donneur_ordre_id": "QC-1"})
    db_session.commit()
    db_session.expire_all()

    relu = db_session.get(Signal, signal.id)
    assert relu.champs["donneur_ordre_id"] == "QC-1"
    assert relu.champs["devise"] == "CAD"


def test_la_periode_vient_des_signaux_pas_dune_supposition(db_session):
    from falkye.models.company import Company
    from falkye.models.signal import Signal

    c = Company(nom_detecte="X", nom_detecte_normalise="x")
    db_session.add(c)
    db_session.flush()
    vieux, recent = datetime(2026, 8, 1), datetime(2026, 9, 10)
    for quand in (vieux, recent):
        db_session.add(
            Signal(company_id=c.id, source_id="seao", signal_type_id="appel_offres",
                   detected_at=quand, source_ref=f"seao:{quand:%Y%m%d}", champs={})
        )
    db_session.commit()

    assert periode_des_signaux(db_session) == (vieux, recent)


def test_il_refuse_une_cible_que_personne_na_choisie(tmp_path):
    fait = subprocess.run(
        [sys.executable, str(RACINE / "outils" / "reprise_champs_seao.py"), "--appliquer"],
        cwd=tmp_path,
        env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(RACINE), "HOME": str(tmp_path)},
        capture_output=True, text=True, check=False,
    )

    assert fait.returncode == 2, fait.stdout + fait.stderr
    assert "REFUS" in fait.stdout + fait.stderr
