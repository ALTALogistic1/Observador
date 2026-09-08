"""Ce que ces tests protègent : **un filtre territorial qui ne parle pas la même
langue que la donnée doit crier, jamais se taire.**

Le 7 septembre 2026, le programme des travailleurs étrangers temporaires écrivait
26 175 employeurs dont 66 % hors Québec, faute de filtre. En allant en poser un,
on a découvert que la valeur réelle du fichier est ``'Qu bec'`` — le diffuseur a
SUPPRIMÉ la lettre accentuée, il ne l'a pas repliée. Un filtre comparant à
« Québec » aurait donc tout rejeté, silencieusement : le même défaut que
l'indicateur de dispense d'adresse, une condition portant sur une valeur qu'on
croit connaître.
"""
import pytest
from sqlalchemy import select

from falkye.engine import CalibrationTerritoriale, ingest_source
from falkye.models.run_log import SourceRunLog
from falkye.models.signal import Signal
from falkye.registry.loader import get_registry
from falkye.territoire import appartient, cles_de_reference

from datetime import datetime, timezone


# --- La comparaison ---------------------------------------------------------


def test_les_quatre_graphies_de_quebec_se_reconnaissent():
    """Dont ``'Qu bec'``, la seule que le fichier réel contient."""
    for valeur in ("Qu bec", "Québec", "Quebec", "QUÉBEC", "québec"):
        assert appartient(valeur, ["Québec"]), valeur


def test_replier_les_accents_ne_suffirait_pas():
    """Le test qui explique pourquoi ce module existe au lieu d'un simple
    `normaliser`. « Québec » replié donne `quebec`; le fichier donne `qubec`,
    une lettre en moins. Deux clés de référence, pas une."""
    assert cles_de_reference("Québec") == {"quebec", "qubec"}


def test_une_autre_province_est_ecartee():
    for valeur in ("Ontario", "Alberta", "Nouvelle- cosse", "Terre-Neuve-et-Labrador"):
        assert not appartient(valeur, ["Québec"]), valeur


def test_les_autres_provinces_accentuees_se_reconnaissent_aussi():
    """La règle n'est pas taillée pour le seul Québec — elle vaut pour toute
    valeur dont le diffuseur a mangé les accents."""
    assert appartient("Nouvelle- cosse", ["Nouvelle-Écosse"])
    assert appartient("le-du-Prince- douard", ["Île-du-Prince-Édouard"])


def test_une_region_absente_est_RETENUE_jamais_rejetee():
    """Supprimer sur une ABSENCE d'information est exactement le défaut de
    l'indicateur de dispense d'adresse. Une source qui ne renseigne pas la
    région ne doit pas voir tout son contenu disparaître."""
    assert appartient(None, ["Québec"])
    assert appartient("", ["Québec"])
    assert appartient("   ", ["Québec"])


def test_sans_territoire_declare_tout_passe():
    assert appartient("Ontario", [])


# --- L'application dans le moteur -------------------------------------------


def _raw(region, ref):
    from falkye.sources.base import RawSignal

    return RawSignal(
        signal_type_id="recrutement_massif",
        source_ref=ref,
        nom_entreprise=f"Entreprise {ref}",
        detected_at=datetime.now(timezone.utc),
        region=region,
        champs={},
    )


def _brancher(monkeypatch, source_id, raws, territoire):
    """Remplace l'entrée du registre par une copie portant le territoire voulu.

    `SourceDef` est figé et `territoire` a une fabrique par défaut : il n'existe
    donc ni comme attribut de classe ni comme champ modifiable. Copier l'objet
    est plus fidèle que de forcer l'attribut — c'est bien un registre différent
    qu'on veut simuler, pas une instance bricolée.
    """
    import dataclasses

    registry = get_registry()
    remplace = dataclasses.replace(registry.source(source_id), territoire=territoire)
    monkeypatch.setitem(registry.sources, source_id, remplace)

    class _Connecteur:
        def detect(self, since, db_session):
            return iter(raws)

    monkeypatch.setattr(type(remplace), "charger_connecteur", lambda self: _Connecteur())
    return registry


def test_le_moteur_ecarte_ce_qui_est_hors_territoire(db_session, monkeypatch):
    """Le connecteur ne sait pas qu'un filtre existe : il produit tout, le
    moteur trie."""
    raws = [_raw("Qu bec", "a"), _raw("Ontario", "b"), _raw("Québec", "c"), _raw("Alberta", "d")]
    registry = _brancher(monkeypatch, "eimt", raws, ["Québec"])

    rapport = ingest_source(db_session, "eimt", None, registry, "veille_continue")

    assert rapport.nb_signaux_nouveaux == 2
    refs = {s.source_ref for s in db_session.execute(select(Signal)).scalars()}
    assert refs == {"a", "c"}


def test_un_filtre_qui_ne_retient_rien_est_une_erreur(db_session, monkeypatch):
    """Le garde-fou central. Seuil ZÉRO, jamais « peu » : c'est le seul cas qui
    se tranche sans norme de volume."""
    raws = [_raw("Ontario", "a"), _raw("Alberta", "b")]
    registry = _brancher(monkeypatch, "eimt", raws, ["Québec"])

    rapport = ingest_source(db_session, "eimt", None, registry, "veille_continue")

    assert rapport.erreur is not None
    assert "AUCUNE" in rapport.erreur
    ligne = db_session.execute(
        select(SourceRunLog).where(SourceRunLog.source_id == "eimt")
    ).scalars().one()
    assert ligne.statut == "erreur"


def test_une_source_qui_ne_produit_rien_nest_PAS_une_erreur_de_filtre(
    db_session, monkeypatch
):
    """Zéro ligne produite est une semaine calme, pas un filtre cassé. Confondre
    les deux ferait crier le journal chaque fois qu'une source est tranquille."""
    registry = _brancher(monkeypatch, "eimt", [], ["Québec"])

    rapport = ingest_source(db_session, "eimt", None, registry, "veille_continue")

    assert rapport.erreur is None


def test_sans_territoire_declare_le_garde_fou_ne_se_declenche_jamais(
    db_session, monkeypatch
):
    registry = _brancher(monkeypatch, "eimt", [_raw("Ontario", "a")], [])

    rapport = ingest_source(db_session, "eimt", None, registry, "veille_continue")

    assert rapport.erreur is None
    assert rapport.nb_signaux_nouveaux == 1
