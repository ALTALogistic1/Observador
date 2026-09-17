"""Le chiffrage rend-il les deux natures de correction, et ce qu'il ne dit pas?

⚠️ **Le piège que ces tests gardent** : un chiffrage qui ne compterait que le
GAIN d'un abaissement de seuil ferait paraître l'abaissement gratuit. *On sait à
quoi ressemble le faux — 26 organisations publiques distinctes à 95-100 sur un
même NEQ.*
"""
from __future__ import annotations

import pytest

from falkye.models.company import Company
from falkye.models.req_entry import REQEntry
from falkye.sources.column_mapping import normaliser
from outils import chiffrage_corrections
from outils.chiffrage_corrections import _sans_parentheses


def test_le_retrait_des_parentheses_ne_touche_que_les_parentheses():
    assert _sans_parentheses("11888935 Canada inc. (Workstaff)") == "11888935 Canada inc."
    assert _sans_parentheses("Acme (A) et (B) inc.") == "Acme et inc.", (
        "deux groupes sur la même ligne doivent être DEUX retraits — un motif "
        "gourmand avalerait « et » entre les deux"
    )
    assert _sans_parentheses("Sans parenthèse") == "Sans parenthèse"
    assert _sans_parentheses(None) == ""


def _cible_declaree(monkeypatch):
    """Les DEUX cibles nommées. *`refuser_si_cible_non_choisie` refuse l'outil
    quand l'une manque — et ce refus est la raison d'être de la garde : sans
    lui, l'outil créerait une base vide et rendrait son verdict dessus.*"""
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")


@pytest.fixture()
def population(db_session, monkeypatch):
    _cible_declaree(monkeypatch)
    registre = "11888935 canada inc"
    db_session.add(REQEntry(neq="1188893500", nom=registre,
                            nom_normalise=normaliser(registre), statut="IMMATRICULÉE"))
    # Le cas réel : deux points sous le seuil, à cause de la parenthèse.
    db_session.add(Company(
        neq=None, nom_detecte="11888935 Canada inc. (Workstaff)",
        nom_detecte_normalise=normaliser("11888935 Canada inc. (Workstaff)"),
    ))
    db_session.add(Company(
        neq=None, nom_detecte="Zzyzx Rien Du Tout",
        nom_detecte_normalise=normaliser("Zzyzx Rien Du Tout"),
    ))
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def test_ce_que_la_mesure_ne_dira_pas_vient_AVANT_les_chiffres(population, capsys):
    """*Une correction simulée dit ce que la règle rendrait sur la population
    d'aujourd'hui, jamais ce qu'elle rendrait en production* — où un appariement
    réussi crée un dossier neuf au lieu de réparer celui qui échoue."""
    assert chiffrage_corrections.main([]) == 0
    sortie = capsys.readouterr().out
    avant = sortie.index("CE QUE CETTE MESURE NE DIRA PAS")
    chiffres = sortie.index("dossiers sans NEQ")
    assert avant < chiffres, "l'avertissement est APRÈS les chiffres"
    assert "CRÉE UN DOSSIER NEUF" in sortie
    assert "les DEUX échelles ne bougent pas" in sortie


def test_les_parentheses_sont_ventilees_par_famille(population, capsys):
    assert chiffrage_corrections.main([]) == 0
    sortie = capsys.readouterr().out
    assert "LES DOSSIERS PORTANT UNE PARENTHÈSE, PAR FAMILLE" in sortie
    assert "avec une parenthèse : 1 dossier(s) sur 2" in sortie


def test_labaissement_rend_LES_DEUX_chiffres(population, capsys):
    """⚠️ **Le test qui porte la distinction.** Un abaissement de seuil est un
    changement d'échelle : il récupère du vrai ET du faux."""
    assert chiffrage_corrections.main([]) == 0
    sortie = capsys.readouterr().out
    assert "CE QU'IL RÉCUPÈRE" in sortie
    assert "CE QU'IL LAISSE PASSER" in sortie
    assert "PLUS DE 2 dossiers" in sortie, (
        "le faux n'est pas mesuré — le chiffrage ferait paraître l'abaissement "
        "gratuit"
    )


def test_les_deux_natures_sont_nommees(population, capsys):
    assert chiffrage_corrections.main([]) == 0
    sortie = capsys.readouterr().out
    assert "CHANGEMENT D'ÉCHELLE" in sortie
    assert "CORRECTION DE DONNÉES" in sortie


def test_il_NECRIT_RIEN(population):
    from sqlalchemy import select

    avant = {c.id: c.neq for c in population.execute(select(Company)).scalars().all()}
    assert chiffrage_corrections.main([]) == 0
    population.expire_all()
    apres = {c.id: c.neq for c in population.execute(select(Company)).scalars().all()}
    assert avant == apres, "un chiffrage a modifié la base"


def test_le_seuil_du_produit_nest_pas_modifie(population):
    """**Aucune règle n'est changée.** *Le seuil se change avec Alexandre, jamais
    dans une demande de mesure.*"""
    from falkye import resolution

    avant = resolution.SEUIL_RESOLUTION_CONFIANTE
    chiffrage_corrections.main(["--seuil-simule", "80"])
    assert resolution.SEUIL_RESOLUTION_CONFIANTE == avant == 92.0


# ---------------------------------------------------------------------------
# LE DÉFAUT DU 2026-09-17 : l'instrument recopiait le scoreur du moteur
# ---------------------------------------------------------------------------
#
# La première version rescorait à la main — `fuzz.WRatio` contre la SEULE
# dénomination sociale élue, sans les autres noms du NEQ et sans le bonus de
# ville. Elle annonçait **-338 RETENUS** là où la correction n'y était pour
# rien. *Les deux décors ci-dessous sont les deux moitiés de ce défaut.*


@pytest.fixture()
def population_pont(db_session, monkeypatch):
    """Un dossier RETENU **par le pont `req_noms`**, pas par la dénomination élue.

    `Ferme M.G. Bellavance` s'apparie à `9224-5842 Québec inc.` — le nom parlant
    est dans `req_noms`, le nom numérique est la dénomination élue. *Rescorer
    contre la seule dénomination élue rendrait un score au plancher.*
    """
    from falkye.models.req_nom import REQNom

    _cible_declaree(monkeypatch)
    elu = "9224-5842 Quebec inc"
    db_session.add(REQEntry(neq="9224584200", nom=elu,
                            nom_normalise=normaliser(elu), statut="IMMATRICULÉE"))
    parlant = "Ferme M.G. Bellavance"
    db_session.add(REQNom(neq="9224584200", nom=parlant, statut="V",
                          type_nom="AUTRE NOM UTILISE AU QUEBEC",
                          nom_normalise=normaliser(parlant)))
    db_session.add(Company(neq=None, nom_detecte=parlant,
                           nom_detecte_normalise=normaliser(parlant)))
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def test_la_simulation_ne_perd_PAS_un_dossier_tenu_par_le_pont(population_pont, capsys):
    """⚠️ **Le test qui aurait attrapé les -338.**

    Aucune parenthèse nulle part : la correction (a) ne peut RIEN changer ici.
    *Si le dossier passe de RETENU à autre chose, c'est l'instrument qui a
    bougé, pas la population.*
    """
    assert chiffrage_corrections.main([]) == 0
    sortie = capsys.readouterr().out
    # ⚠️ Le test doit d'abord ÊTRE dans le cas qu'il prétend garder : un
    # dossier RETENU par le pont. *Sans cette ligne, « 0 perdu » passerait
    # aussi sur une population où rien n'a jamais été retenu.*
    assert "RETENU                     1" in sortie, sortie
    assert "RETENUS perdus : 0" in sortie, (
        "un dossier sans la moindre parenthèse a changé de famille — la seconde "
        "passe ne rejoue pas le scoreur du moteur"
    )


@pytest.fixture()
def population_ville(db_session, monkeypatch):
    """Un dossier RETENU **grâce au bonus de ville** (+5), et par lui seul.

    ⚠️ **Le score du NOM est 90.00 — sous le seuil.** *C'est le bonus de ville
    qui le porte à 95.* Un décor où le nom seul passerait déjà ne verrouillerait
    rien : il resterait RETENU des deux côtés, avec ou sans le défaut.

    **Et aucune parenthèse nulle part** : la correction (a) ne peut rien y
    changer, donc toute perte est imputable à l'instrument.
    """
    _cible_declaree(monkeypatch)
    registre = "11888935 canada inc"
    db_session.add(REQEntry(neq="1111111111", nom=registre,
                            nom_normalise=normaliser(registre),
                            ville="Longueuil", statut="IMMATRICULÉE"))
    detecte = "11888935 Canada inc Workstaff"
    db_session.add(Company(neq=None, nom_detecte=detecte, ville="Longueuil",
                           nom_detecte_normalise=normaliser(detecte)))
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def test_la_simulation_garde_le_bonus_de_ville(population_ville, capsys):
    from rapidfuzz import fuzz

    # Le décor tient-il sa promesse? *Le nom seul doit échouer.*
    assert fuzz.WRatio(normaliser("11888935 Canada inc Workstaff"),
                       normaliser("11888935 canada inc")) == 90.0
    assert chiffrage_corrections.main([]) == 0
    sortie = capsys.readouterr().out
    assert "RETENU                     1" in sortie, sortie
    assert "RETENUS perdus : 0" in sortie, (
        "le bonus de ville a disparu entre les deux passes — le scoreur est "
        "recopié au lieu d'être emprunté"
    )


def test_le_temoin_de_lecart_en_vigueur_rend_zero(population, capsys):
    """À l'écart en vigueur, la simulation rejoue la règle actuelle : **le gain
    doit être nul**. *Un gain non nul dirait que la simulation et le moteur ne
    classent pas pareil, et tout le tableau serait à jeter.*"""
    assert chiffrage_corrections.main([]) == 0
    sortie = capsys.readouterr().out
    ligne = next(l for l in sortie.splitlines() if "TÉMOIN" in l)
    assert ligne.split("│")[-1].split("←")[0].strip() == "0", (
        f"le témoin ne rend pas 0 : {ligne!r}"
    )


# ---------------------------------------------------------------------------
# LA DESTINATION, ET NON LE SEUL GAIN
# ---------------------------------------------------------------------------


def test_le_seuil_abaisse_rend_la_DESTINATION_de_ce_qui_franchit(population, capsys):
    """⚠️ **Le second refus du 2026-09-17.** 1 623 dossiers franchissaient le
    seuil simulé, 79 étaient annoncés « récupérés », et les 1 544 autres
    n'apparaissaient nulle part. *Franchir le seuil et devenir RETENU ne sont
    pas le même événement — l'écart minimal sépare les deux.*"""
    assert chiffrage_corrections.main([]) == 0
    sortie = capsys.readouterr().out
    assert "où va la masse qui le franchit" in sortie
    assert "destination au seuil simulé" in sortie
    assert "franchissent" in sortie and "SANS devenir RETENUS" in sortie
    # Les quatre familles sont nommées dans le tableau de destination.
    bloc = sortie[sortie.index("destination au seuil simulé"):]
    for famille in ("RETENU", "ambigu", "trop faible", "aucun candidat"):
        assert famille in bloc


def test_lecart_est_chiffre_et_son_FAUX_vient_en_premier(population, capsys):
    """⚠️ *L'écart est plus dangereux que le seuil, pas moins* — il fait trancher
    entre deux candidats proches. **Le faux se lit avant le gain.**"""
    assert chiffrage_corrections.main([]) == 0
    sortie = capsys.readouterr().out
    assert "ÉCART MINIMAL ABAISSÉ" in sortie
    entete = next(l for l in sortie.splitlines() if "│" in l and "gain" in l)
    assert entete.index("FAUX") < entete.index("gain"), (
        "le gain se lit avant le faux — un chiffrage qui ferait paraître "
        "l'abaissement de l'écart gratuit"
    )
    assert "CETTE ÉCHELLE EST PLUS DANGEREUSE QUE LE SEUIL" in sortie
    assert "8879690699" in sortie, "la forme de faux connue n'est pas nommée"


def test_les_DEUX_echelles_sont_declarees_immobiles(population, capsys):
    assert chiffrage_corrections.main([]) == 0
    sortie = capsys.readouterr().out
    assert "les DEUX échelles ne bougent pas" in sortie
    assert "écart minimal 8" in sortie


def test_les_perdus_sont_ventiles_par_presence_de_parenthese(population, capsys):
    """*Si les perdus se concentrent chez ceux qui portent une parenthèse, la
    perte est un mécanisme. Sinon, l'instrument est en cause.* **Le chiffrage
    doit permettre de trancher entre les deux.**"""
    assert chiffrage_corrections.main([]) == 0
    sortie = capsys.readouterr().out
    assert "parenthèse DANS LE NOM DÉTECTÉ" in sortie
    assert "AUCUNE parenthèse dans le nom détecté" in sortie
    assert "dossiers dont le PRÉFIXE change" in sortie


def test_lecart_du_produit_nest_pas_modifie(population):
    from falkye import resolution

    avant = resolution.SEUIL_AMBIGUITE_ECART_MIN
    chiffrage_corrections.main(["--seuil-simule", "80"])
    assert resolution.SEUIL_AMBIGUITE_ECART_MIN == avant == 8.0


# ---------------------------------------------------------------------------
# LES TROIS LECTURES D'UNE PERTE  (2026-09-17, second relevé d'Alexandre)
# ---------------------------------------------------------------------------
#
# La règle de lecture n'en donnait que DEUX, et faisait conclure « l'instrument
# est en cause » sur un cas qui est un mécanisme : **9 perdus sur 13 ne
# portaient aucune parenthèse au nom détecté.** *Un CANDIDAT peut en porter une,
# et la lui retirer lui fait perdre un discriminant.*


@pytest.fixture()
def population_discriminant(db_session, monkeypatch):
    """Le nom détecté n'a AUCUNE parenthèse; un candidat concurrent en a une.

    Avant : `100` contre `85.5` — écart 14.5, **RETENU**.
    Après : la parenthèse retirée côté registre rend les deux formes
    identiques — `100` contre `100`, écart 0, **AMBIGU**.

    ⚠️ *C'est une perte RÉELLE et un MÉCANISME* : le registre a perdu ce qui
    séparait les deux entreprises. **Rien à voir avec l'instrument.**
    """
    _cible_declaree(monkeypatch)
    for neq, nom in (("3000000001", "Solutions BCITI inc"),
                     ("3000000002", "Solutions BCITI (Groupe Nordet) inc")):
        db_session.add(REQEntry(neq=neq, nom=nom, nom_normalise=normaliser(nom),
                                statut="IMMATRICULÉE"))
    detecte = "Solutions BCITI inc"
    db_session.add(Company(neq=None, nom_detecte=detecte,
                           nom_detecte_normalise=normaliser(detecte)))
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def test_une_perte_sans_parenthese_detectee_nACCUSE_PAS_linstrument(
    population_discriminant, capsys
):
    """⚠️ **La règle de lecture corrigée.** *Le compteur qui accuse l'instrument
    ne compte que les pertes où AUCUNE parenthèse n'existe nulle part.*"""
    assert chiffrage_corrections.main([]) == 0
    sortie = capsys.readouterr().out
    assert "RETENUS perdus : 1" in sortie, sortie
    assert "perdus SANS aucune parenthèse, ni au nom ni chez leurs candidats : 0" in sortie, (
        "une perte causée par une parenthèse CÔTÉ REGISTRE est comptée comme un "
        "défaut d'instrument — c'est la lecture qu'Alexandre a refusée"
    )
    assert "TROIS LECTURES, PAS DEUX" in sortie


def test_le_perdu_est_trace_avec_la_provenance_de_ses_formes(
    population_discriminant, capsys
):
    """*« Quel second candidat apparaît après le retrait, et d'où il vient »* —
    la question du 2026-09-17, répondue par l'outil et non à la main."""
    assert chiffrage_corrections.main([]) == 0
    sortie = capsys.readouterr().out
    assert "quel second apparaît après le retrait" in sortie
    assert "ses formes au registre" in sortie
    assert "req_entries (dénomination élue)" in sortie
    assert "parenthèse au nom détecté : NON" in sortie
    # La forme fautive est montrée, marquée, telle que le registre l'écrit.
    assert "Solutions BCITI (Groupe Nordet) inc" in sortie
