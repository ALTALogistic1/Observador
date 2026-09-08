"""Le coût d'une exécution, ventilé par chemin de résolution.

Ce que ces tests verrouillent :

1. Le COMPTE est exact et vient du point d'appel réel — pas d'un faux qui
   compterait à la place du moteur.
2. La DÉRIVATION suit la population, elle n'est pas une constante gravée. Une
   constante mesurée le 2026-09-08 serait fausse dans six mois, en silence.
3. Le repli par sous-chaîne n'est compté QUE quand il est réellement emprunté —
   c'est sa fréquence, et elle seule, qui décide s'il se borne ou se retire.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from falkye.cout_lectures import (
    CHEMIN_EXACT,
    CHEMIN_PREFIXE,
    CHEMIN_SOUS_CHAINE,
    PRIX,
    comptes_courants,
    compter,
    lignes_lues_derivees,
    ouvrir_comptes,
    population_sans_neq,
)
from falkye.models.company import Company
from falkye.models.run_log import SourceRunLog


# --- le compteur ------------------------------------------------------------


def test_hors_execution_compter_ne_leve_pas_et_ne_compte_nulle_part():
    """Un outil ou la ligne de commande empruntent les mêmes chemins. Ils ne
    doivent ni faire lever le moteur, ni s'inventer un compteur global qui
    mélangerait des exécutions distinctes."""
    assert comptes_courants() is None
    compter(CHEMIN_EXACT)  # ne doit pas lever
    assert comptes_courants() is None


def test_un_compteur_imbrique_restaure_le_precedent():
    """Sans restauration, une exception laisserait le compteur d'une exécution
    ouvert et la suivante additionnerait ses appels à ceux de la précédente."""
    with ouvrir_comptes() as externe:
        compter(CHEMIN_EXACT)
        with ouvrir_comptes() as interne:
            compter(CHEMIN_SOUS_CHAINE)
            assert interne.appels[CHEMIN_SOUS_CHAINE] == 1
            assert interne.appels[CHEMIN_EXACT] == 0
        assert comptes_courants() is externe
        assert externe.appels[CHEMIN_EXACT] == 1
        assert externe.appels[CHEMIN_SOUS_CHAINE] == 0


def test_le_compteur_est_restaure_meme_si_le_bloc_leve():
    with ouvrir_comptes() as externe:
        try:
            with ouvrir_comptes():
                raise RuntimeError("la source tombe")
        except RuntimeError:
            pass
        assert comptes_courants() is externe


# --- la dérivation ----------------------------------------------------------


def test_le_prix_du_repli_suit_la_population_il_nest_pas_une_constante():
    """LE test de conception. Le repli lit toute la population sans NEQ : son
    prix DOIT doubler quand elle double. Une constante (8 396, mesurée le
    2026-09-08) passerait ce test aujourd'hui et mentirait dans six mois."""
    appels = {CHEMIN_EXACT: 10, CHEMIN_PREFIXE: 10, CHEMIN_SOUS_CHAINE: 10}

    petite = lignes_lues_derivees(appels, population=8_395)
    grande = lignes_lues_derivees(appels, population=16_790)

    assert grande[CHEMIN_SOUS_CHAINE] == 2 * petite[CHEMIN_SOUS_CHAINE] - 10 * PRIX[
        CHEMIN_SOUS_CHAINE
    ].fixe
    # Les deux chemins corrigés par l'index, eux, ne bougent pas avec elle.
    assert grande[CHEMIN_EXACT] == petite[CHEMIN_EXACT]
    assert grande[CHEMIN_PREFIXE] == petite[CHEMIN_PREFIXE]


def test_la_derivation_reste_nommee_comme_une_derivation():
    """Partout où ce résultat voyage, il doit rester distinguable d'un
    `rows_read` réel — le nom de la fonction est le premier garde-fou."""
    assert "derivees" in lignes_lues_derivees.__name__


def test_population_sans_neq_ne_compte_que_les_non_resolues(db_session):
    db_session.add_all(
        [
            Company(neq=None, nom_detecte="a", nom_detecte_normalise="a"),
            Company(neq=None, nom_detecte="b", nom_detecte_normalise="b"),
            Company(neq="1160000001", nom_detecte="c", nom_detecte_normalise="c"),
        ]
    )
    db_session.commit()

    assert population_sans_neq(db_session) == 2


# --- de bout en bout : c'est le MOTEUR qui compte, pas le test ---------------


def test_une_resolution_reelle_incremente_les_chemins_empruntes(db_session):
    """Le compteur est incrémenté dans `resolution.py` et `dedup_entreprises.py`,
    pas ici. Si quelqu'un déplaçait l'appel hors du chemin réel, ce test
    tomberait."""
    from falkye.resolution import resolve_company
    from falkye.sources.base import RawSignal

    with ouvrir_comptes() as comptes:
        resolve_company(
            db_session,
            RawSignal(
                signal_type_id="appel_offres",
                nom_entreprise="Entreprise Inconnue Sans NEQ",
                source_ref="test:1",
                detected_at=datetime(2026, 9, 8, tzinfo=timezone.utc),
            ),
        )

    # Nom absent du miroir REQ → pas de NEQ → recherche exacte, puis rapprochement
    # flou par préfixe. Le repli par sous-chaîne suit, le préfixe ne rendant rien.
    assert comptes.appels[CHEMIN_EXACT] == 1
    assert comptes.appels[CHEMIN_PREFIXE] == 1
    assert comptes.appels[CHEMIN_SOUS_CHAINE] == 1


def test_le_repli_nest_pas_compte_quand_le_prefixe_rend_quelque_chose(db_session):
    """Sa fréquence est la question ouverte : le compter à chaque fois, ou ne le
    compter que quand il est emprunté, ne donne pas la même réponse."""
    from falkye.dedup_entreprises import trouver_meilleur_candidat_fusion

    db_session.add(
        Company(
            neq=None,
            nom_detecte="Construction Beaulieu",
            nom_detecte_normalise="construction beaulieu",
        )
    )
    db_session.commit()

    with ouvrir_comptes() as comptes:
        trouver_meilleur_candidat_fusion(db_session, "construction tremblay", ville=None)

    assert comptes.appels[CHEMIN_PREFIXE] == 1
    assert comptes.appels[CHEMIN_SOUS_CHAINE] == 0


def test_les_comptes_atterrissent_sur_la_ligne_dexecution(db_session, monkeypatch):
    from falkye.engine import ingest_source
    from falkye.registry.loader import get_registry

    class _ConnecteurCalme:
        def detect(self, since, db_session):
            return iter(())

    registry = get_registry()
    source_id = registry.sources_actives_automatisees()[0].id
    monkeypatch.setattr(
        type(registry.source(source_id)), "charger_connecteur", lambda self: _ConnecteurCalme()
    )

    ingest_source(db_session, source_id, None, registry, "veille_continue")

    ligne = db_session.execute(
        select(SourceRunLog).where(SourceRunLog.source_id == source_id)
    ).scalar_one()
    assert ligne.nb_resolutions_exact == 0
    assert ligne.nb_resolutions_prefixe == 0
    assert ligne.nb_resolutions_sous_chaine == 0
    # Zéro APPEL est une mesure; zéro LIGNE LUE n'en serait pas une — d'où la
    # colonne du coût réel laissée à NULL.
    assert ligne.nb_lignes_lues_base is None


# --- la table de prix se périme, et elle doit le dire ------------------------


def test_les_prix_sont_valides_sur_letat_dindex_de_reference(db_session):
    """Sur une base bâtie depuis les modèles, l'état d'index est celui sur lequel
    les prix ont été pris — donc rien à signaler."""
    from falkye.cout_lectures import peremption

    assert peremption(db_session) is None


def test_un_index_pose_perime_la_table_de_prix(db_session):
    """**LE test de la réserve du 2026-09-08.** Le chemin exact valait 8 396
    lignes le matin et 2 l'après-midi : rien dans le code n'avait changé, un
    index avait été posé. Une table de prix qui ne le détecte pas est une
    vérification qui se périme sans le dire."""
    from sqlalchemy import text

    from falkye.cout_lectures import index_companies, peremption

    db_session.connection(bind_arguments={"mapper": Company.__mapper__}).execute(
        text("CREATE INDEX ix_companies_ville_essai ON companies (ville)")
    )
    db_session.commit()

    message = peremption(db_session)

    assert message is not None
    assert "ix_companies_ville_essai" in message
    assert "posé(s) depuis" in message
    assert "ix_companies_ville_essai" in index_companies(db_session)


def test_un_index_retire_perime_aussi_la_table(db_session):
    """La péremption est symétrique : retirer un index change le plan autant que
    d'en poser un."""
    from sqlalchemy import text

    from falkye.cout_lectures import peremption

    db_session.connection(bind_arguments={"mapper": Company.__mapper__}).execute(
        text("DROP INDEX ix_companies_nom_detecte_normalise")
    )
    db_session.commit()

    message = peremption(db_session)

    assert message is not None
    assert "retiré(s) depuis" in message


def test_la_provenance_nomme_ses_conditions_de_mesure():
    """Une table de prix sans provenance ne peut pas se périmer : rien à
    comparer. Ces champs sont la condition de validité, pas de la décoration."""
    from falkye.cout_lectures import PROVENANCE

    assert PROVENANCE.mesure_le
    assert PROVENANCE.methode
    assert PROVENANCE.population_sans_neq > 0
    assert PROVENANCE.index_companies


def test_lavertissement_dit_que_la_derivation_ne_decide_pas_du_palier():
    """Charte, Force 3 : mesure, estimation et absence ne se fusionnent jamais en
    un chiffre dont on ne sait plus d'où il vient."""
    from falkye.cout_lectures import AVERTISSEMENT_DERIVATION

    assert "ESTIMATION" in AVERTISSEMENT_DERIVATION
    assert "palier" in AVERTISSEMENT_DERIVATION
    assert "hébergeur" in AVERTISSEMENT_DERIVATION
