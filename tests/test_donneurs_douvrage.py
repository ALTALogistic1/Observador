"""Le relevé des donneurs d'ouvrage compte, et ne classe pas.

L'obligation de publier au SEAO ne pèse que sur les organismes publics, mais
d'autres l'utilisent volontairement : la population n'est pas homogène. Trier ces
noms est la décision D28 — un outil qui devinerait la règle rendrait une
classification avec l'apparence d'une mesure.
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

from outils.donneurs_douvrage import SOURCES_AVEC_DONNEUR, releve

RACINE = Path(__file__).resolve().parents[1]


def _signal(db_session, company_id, source_id, donneur, valeur=None):
    from falkye.models.signal import Signal

    db_session.add(
        Signal(
            company_id=company_id, source_id=source_id, signal_type_id="appel_offres",
            detected_at=datetime.now(), valeur_associee=valeur,
            champs={"donneur_ordre": donneur} if donneur is not None else {},
        )
    )


def test_les_donneurs_se_comptent_sans_doublon(db_session):
    from falkye.models.company import Company

    c = Company(nom_detecte="Fournisseur", nom_detecte_normalise="fournisseur")
    db_session.add(c)
    db_session.flush()
    _signal(db_session, c.id, "seao", "Ville de Laval", 100.0)
    _signal(db_session, c.id, "seao", "Ville de Laval")
    _signal(db_session, c.id, "seao", "CISSS de Laval", 200.0)
    db_session.commit()

    r = releve(db_session, ["seao"])

    assert r["par_source"]["seao"] == 3
    assert r["avec_donneur"]["seao"] == 3
    assert r["avec_montant"]["seao"] == 2
    assert dict(r["donneurs"]) == {"Ville de Laval": 2, "CISSS de Laval": 1}


def test_un_signal_sans_donneur_se_compte_a_part(db_session):
    """La couverture est une mesure en soi : un connecteur qui cesserait de
    renseigner le donneur se verrait là, et nulle part ailleurs."""
    from falkye.models.company import Company

    c = Company(nom_detecte="X", nom_detecte_normalise="x")
    db_session.add(c)
    db_session.flush()
    _signal(db_session, c.id, "seao", None)
    _signal(db_session, c.id, "seao", "   ")
    _signal(db_session, c.id, "seao", "Ministère des Transports")
    db_session.commit()

    r = releve(db_session, ["seao"])

    assert r["par_source"]["seao"] == 3
    assert r["avec_donneur"]["seao"] == 1


def test_les_trois_sources_qui_portent_un_donneur_sont_nommees():
    """Si un quatrième connecteur écrit un `donneur_ordre` sans être inscrit ici,
    le compte de couverture le fera voir — mais la liste doit rester juste."""
    import pathlib
    import re

    ecrivent = {
        chemin.stem
        for chemin in pathlib.Path(RACINE / "falkye" / "sources").glob("*.py")
        if re.search(r'"donneur_ordre":', chemin.read_text(encoding="utf-8"))
    }

    assert ecrivent == set(SOURCES_AVEC_DONNEUR)


def test_il_refuse_une_cible_que_personne_na_choisie(tmp_path):
    fait = subprocess.run(
        [sys.executable, str(RACINE / "outils" / "donneurs_douvrage.py")],
        cwd=tmp_path,
        env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(RACINE), "HOME": str(tmp_path)},
        capture_output=True, text=True, check=False,
    )

    assert fait.returncode == 2, fait.stdout + fait.stderr
    assert "REFUS" in fait.stdout + fait.stderr
