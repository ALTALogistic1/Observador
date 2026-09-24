"""La passe de reprise pose-t-elle les NEQ libres, et CONSERVE-t-elle le reste?

**La décision que ces tests verrouillent** *(Alexandre, 2026-09-16)* :
**conservation plutôt que fusion, parce qu'elle est réversible.** *Deux dossiers
séparés se fusionnent plus tard; deux dossiers fusionnés ne se séparent pas.*

`Company.neq` est `unique=True`. Quand la reprise trouve un NEQ **déjà porté par
un autre dossier**, le chemin « naturel » serait de fusionner les deux. ⚠️ **La
passe ne le fait pas, et ces tests existent pour que personne ne le fasse plus
tard sans le décider** — un rapprochement est *journalisé*, à examiner par un
humain, et **les deux dossiers sortent intacts**.

Le reste tient en trois exigences, chacune avec son test :

1. **Le rapport est le mode par défaut** — `--appliquer` est le seul chemin qui
   écrit. *Un outil qui écrit par défaut est un outil qu'on lance une fois de
   trop.*
2. **L'instantané d'avant précède le commit.** *Sans lui, « réversible » est une
   intention* — et si l'instantané ne peut pas s'écrire, **rien n'est modifié**.
3. **La décision passe par `neq_retenu`**, la fonction du produit. *Une règle
   recopiée mesurerait sa propre copie.*
"""
from __future__ import annotations

import json

import pytest

from falkye.models.company import Company, StatutResolution
from falkye.models.diagnostic_journal import DiagnosticJournal, TypeDiagnostic
from falkye.models.req_entry import REQEntry
from falkye.models.req_nom import REQNom
from falkye.sources.column_mapping import normaliser
from outils import reresolution_neq


@pytest.fixture()
def decor(db_session, tmp_path, monkeypatch):
    """Trois dossiers sans NEQ : un que le registre résout vers un NEQ libre, un
    vers un NEQ DÉJÀ PRIS, un que rien ne résout. Plus le détenteur."""
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")
    monkeypatch.setattr(reresolution_neq, "DOSSIER_INSTANTANE", tmp_path)

    for neq, nom in (
        ("1111111111", "boulangerie saint-viateur inc"),
        ("2222222222", "plomberie rousseau et fils ltee"),
    ):
        db_session.add(
            REQEntry(neq=neq, nom=nom, nom_normalise=normaliser(nom),
                     statut="IMMATRICULÉE")
        )

    # ⚠️ **Le cas `#16` du 19 septembre** : la dénomination ÉLUE n'a pas un
    # caractère commun avec le nom détecté, et le score vient d'une TROISIÈME
    # forme que `req_noms` porte. *Sans ce dossier au décor, les deux lignes de
    # lecture ne seraient jamais exercées.*
    db_session.add(REQEntry(neq="3333333333",
                            nom="LES ENTREPRISES DOUGLAS POWERTECH INC.",
                            nom_normalise=normaliser("LES ENTREPRISES DOUGLAS POWERTECH INC."),
                            statut="IMMATRICULÉE"))
    db_session.add(REQNom(neq="3333333333", nom="16790224 Canada Inc.",
                          nom_normalise=normaliser("16790224 Canada Inc."),
                          gisement="NOM_ASSUJ", statut="A", type_nom="NOM"))
    autre_forme = Company(neq=None, nom_detecte="16790224 Canada Inc.",
                          nom_detecte_normalise=normaliser("16790224 Canada Inc."))

    libre = Company(neq=None, nom_detecte="Boulangerie Saint-Viateur Inc",
                    nom_detecte_normalise=normaliser("Boulangerie Saint-Viateur Inc"))
    a_conserver = Company(neq=None, nom_detecte="Plomberie Rousseau et Fils Ltee",
                          nom_detecte_normalise=normaliser("Plomberie Rousseau et Fils Ltee"))
    detenteur = Company(neq="2222222222", nom_detecte="Plomberie Rousseau",
                        nom_detecte_normalise=normaliser("Plomberie Rousseau"))
    introuvable = Company(neq=None, nom_detecte="Zzyzx Quelque Chose Qui Nexiste Pas",
                          nom_detecte_normalise=normaliser("Zzyzx Quelque Chose Qui Nexiste Pas"))
    db_session.add_all([libre, a_conserver, detenteur, introuvable, autre_forme])
    db_session.commit()

    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return {"libre": libre.id, "a_conserver": a_conserver.id,
            "detenteur": detenteur.id, "introuvable": introuvable.id,
            "autre_forme": autre_forme.id,
            "session": db_session, "tmp": tmp_path}


def test_sans_appliquer_rien_nest_ecrit(decor, capsys):
    """**Le mode par défaut est le rapport.** Un outil qui écrit par défaut est
    un outil qu'on lance une fois de trop."""
    assert reresolution_neq.main([]) == 0

    session = decor["session"]
    session.expire_all()
    assert session.get(Company, decor["libre"]).neq is None, "un NEQ a été posé sans --appliquer"
    assert not list(session.execute(
        __import__("sqlalchemy").select(DiagnosticJournal)).scalars().all()
    ), "un rapprochement a été journalisé sans --appliquer"
    assert "rien n'a été écrit" in capsys.readouterr().out.lower()


def test_le_neq_libre_est_pose(decor):
    assert reresolution_neq.main(["--appliquer"]) == 0
    session = decor["session"]
    session.expire_all()
    repris = session.get(Company, decor["libre"])
    assert repris.neq == "1111111111"
    assert repris.statut_resolution == StatutResolution.RESOLU


def test_un_neq_deja_pris_ne_fusionne_RIEN(decor):
    """⚠️ **Le test qui porte la décision.** Les deux dossiers sortent intacts,
    et le rapprochement n'est qu'une proposition.

    *Deux dossiers séparés se fusionnent plus tard; deux dossiers fusionnés ne se
    séparent pas.*
    """
    from sqlalchemy import select

    assert reresolution_neq.main(["--appliquer"]) == 0
    session = decor["session"]
    session.expire_all()

    conserve = session.get(Company, decor["a_conserver"])
    detenteur = session.get(Company, decor["detenteur"])
    assert conserve is not None, "le dossier a été SUPPRIMÉ — c'est une fusion"
    assert conserve.neq is None, "un NEQ déjà pris a été posé sur un second dossier"
    assert detenteur is not None and detenteur.neq == "2222222222", "le détenteur a bougé"

    entrees = list(session.execute(select(DiagnosticJournal)).scalars().all())
    rapprochements = [
        e for e in entrees if e.type_diagnostic == TypeDiagnostic.CANDIDAT_FUSION_ENTREPRISE
    ]
    assert len(rapprochements) == 1, "le rapprochement n'a pas été journalisé pour examen"
    assert rapprochements[0].statut == "a_examiner"
    assert rapprochements[0].company_id_principal == decor["detenteur"]
    assert rapprochements[0].company_id_candidat == decor["a_conserver"]


def test_linstantane_porte_letat_davant(decor):
    """*Sans instantané, « réversible » est une intention.*"""
    assert reresolution_neq.main(["--appliquer"]) == 0
    fichiers = list(decor["tmp"].glob("reresolution-*.json"))
    assert len(fichiers) == 1, f"aucun instantané écrit ({fichiers})"

    contenu = json.loads(fichiers[0].read_text(encoding="utf-8"))
    a_poser = {p["company_id"]: p for p in contenu["a_poser"]}
    assert decor["libre"] in a_poser
    assert a_poser[decor["libre"]]["neq_avant"] is None, (
        "l'état d'AVANT manque — l'instantané ne permet pas de défaire"
    )
    conserves = {p["company_id"] for p in contenu["conserves"]}
    assert decor["a_conserver"] in conserves


def test_un_instantane_impossible_ANNULE_tout(decor, monkeypatch):
    """⚠️ **Si la trace ne peut pas s'écrire, le geste n'a pas lieu.**

    Le même défaut que le chemin d'archive du diff, une table plus loin : un
    geste irréversible sans trace de l'état d'avant n'est pas réversible.
    """
    barrage = decor["tmp"] / "barrage"
    barrage.write_text("un fichier, pas un répertoire")
    monkeypatch.setattr(reresolution_neq, "DOSSIER_INSTANTANE", barrage / "dedans")

    assert reresolution_neq.main(["--appliquer"]) == 3
    session = decor["session"]
    session.expire_all()
    assert session.get(Company, decor["libre"]).neq is None, (
        "un NEQ a été posé alors que l'instantané n'a pas pu être écrit"
    )


def test_ce_que_rien_ne_resout_reste_intact(decor):
    assert reresolution_neq.main(["--appliquer"]) == 0
    session = decor["session"]
    session.expire_all()
    assert session.get(Company, decor["introuvable"]).neq is None


@pytest.fixture()
def decor_collision(db_session, tmp_path, monkeypatch):
    """**La panne du 2026-09-16, 19 h 03, reproduite.** Deux dossiers du LOT
    visent le même NEQ libre — des doublons de graphie, exactement comme les 69
    que le rapport montrait sans qu'on les lise ainsi.

    *Le premier prend le NEQ, le second viole `UNIQUE(companies.neq)`, et la
    transaction entière est annulée : rien n'est posé.*
    """
    from datetime import datetime, timezone

    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")
    monkeypatch.setattr(reresolution_neq, "DOSSIER_INSTANTANE", tmp_path)

    nom = "annexair inc"
    db_session.add(
        REQEntry(neq="3333333333", nom=nom, nom_normalise=normaliser(nom),
                 statut="IMMATRICULÉE")
    )
    # Le PLUS ANCIEN est créé en SECOND, et porte l'id le PLUS GRAND : si la
    # règle était « le premier rencontré », le test passerait pour la mauvaise
    # raison. Ici les deux critères pointent en sens opposés.
    recent = Company(
        neq=None, nom_detecte="Annexair Inc", nom_detecte_normalise=normaliser("Annexair Inc"),
        first_detected_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    db_session.add(recent)
    db_session.flush()
    ancien = Company(
        neq=None, nom_detecte="Annexair inc.", nom_detecte_normalise=normaliser("Annexair inc."),
        first_detected_at=datetime(2025, 3, 14, tzinfo=timezone.utc),
    )
    db_session.add(ancien)
    db_session.commit()

    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return {"ancien": ancien.id, "recent": recent.id, "session": db_session, "tmp": tmp_path}


def test_deux_dossiers_visant_le_meme_neq_nannulent_pas_la_passe(decor_collision):
    """**Le test de la panne.** Avant le correctif, ces deux dossiers faisaient
    échouer la transaction ENTIÈRE sur `UNIQUE constraint failed: companies.neq`
    — donc les 736 autres n'étaient pas posés non plus."""
    assert reresolution_neq.main(["--appliquer"]) == 0

    session = decor_collision["session"]
    session.expire_all()
    porteurs = [
        c for c in (session.get(Company, decor_collision["ancien"]),
                    session.get(Company, decor_collision["recent"]))
        if c.neq == "3333333333"
    ]
    assert len(porteurs) == 1, (
        f"{len(porteurs)} dossier(s) portent le NEQ — la collision interne au lot "
        "n'est pas résolue"
    )


def test_le_plus_ANCIEN_garde_le_neq(decor_collision):
    """⚠️ **L'échelle est celle du produit, pas une neuve.**
    `falkye/dedup_entreprises.py` : « le PRINCIPAL est toujours le dossier le
    plus ANCIEN (`first_detected_at`) ».

    Le décor met l'ancienneté et l'ordre d'insertion en SENS OPPOSÉS : un
    correctif « le premier rencontré gagne » échouerait ici.
    """
    assert reresolution_neq.main(["--appliquer"]) == 0
    session = decor_collision["session"]
    session.expire_all()
    assert session.get(Company, decor_collision["ancien"]).neq == "3333333333"
    assert session.get(Company, decor_collision["recent"]).neq is None


def test_le_perdant_dune_collision_est_conserve_et_journalise(decor_collision):
    """*Le perdant n'est pas perdu.* C'est ce qui rend le choix d'échelle bon
    marché : un humain tranche la paire plus tard, et les deux dossiers sont là."""
    from sqlalchemy import select

    assert reresolution_neq.main(["--appliquer"]) == 0
    session = decor_collision["session"]
    session.expire_all()

    perdant = session.get(Company, decor_collision["recent"])
    assert perdant is not None, "le dossier perdant a été SUPPRIMÉ — c'est une fusion"

    entrees = list(session.execute(select(DiagnosticJournal)).scalars().all())
    rapprochements = [
        e for e in entrees
        if e.type_diagnostic == TypeDiagnostic.CANDIDAT_FUSION_ENTREPRISE
        and e.company_id_candidat == decor_collision["recent"]
    ]
    assert len(rapprochements) == 1, "la collision n'a pas été journalisée pour examen"
    assert rapprochements[0].company_id_principal == decor_collision["ancien"]


def test_la_collision_est_annoncee_AVANT_decrire(decor_collision, capsys):
    """*La dernière vérification avant un geste irréversible se fait sur ce que
    le rapport montre.* Une collision réglée en silence à l'écriture serait une
    décision prise sans témoin."""
    assert reresolution_neq.main([]) == 0
    sortie = capsys.readouterr().out
    assert "COLLISIONS dans le lot" in sortie, (
        "le rapport ne dit pas que deux dossiers visent le même NEQ"
    )


@pytest.fixture()
def decor_famille_dentites(db_session, tmp_path, monkeypatch):
    """**Le groupe des 26, réduit à trois.** Trois organisations RÉELLEMENT
    DISTINCTES dont les noms convergent vers un même NEQ libre.

    *C'est le cas du NEQ 8879690699 : CISSS, CIUSSS, CHUM, centres
    hospitaliers — 26 dossiers, scores de 95 à 100, et aucun n'est le bon.*
    """
    from datetime import datetime, timezone

    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")
    monkeypatch.setattr(reresolution_neq, "DOSSIER_INSTANTANE", tmp_path)

    registre = "centre integre de sante et de services sociaux"
    db_session.add(
        REQEntry(neq="8888888888", nom=registre, nom_normalise=normaliser(registre),
                 statut="IMMATRICULÉE")
    )
    ids = []
    for i, nom in enumerate((
        "Centre integre de sante et de services sociaux A",
        "Centre integre de sante et de services sociaux B",
        "Centre integre de sante et de services sociaux C",
    )):
        c = Company(neq=None, nom_detecte=nom, nom_detecte_normalise=normaliser(nom),
                    first_detected_at=datetime(2025, 1, i + 1, tzinfo=timezone.utc))
        db_session.add(c)
        db_session.flush()
        ids.append(c.id)
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return {"ids": ids, "session": db_session}


def test_au_dela_de_deux_pretendants_AUCUN_ne_recoit_le_neq(decor_famille_dentites):
    """⛔ **Le refus qui gate l'écriture.**

    *Le nombre de prétendants est une preuve CONTRE l'appariement.* Deux
    dossiers qui convergent, c'est un doublon plausible. Au-delà, c'est un nom
    qui désigne une FAMILLE d'entités — et l'ancienneté désignerait un gagnant
    dans un groupe dont aucun membre n'est probablement le bon.

    ⚠️ **Sans ce refus, le plus ancien des 26 CISSS aurait reçu le NEQ.**
    """
    assert reresolution_neq.main(["--appliquer"]) == 0
    session = decor_famille_dentites["session"]
    session.expire_all()
    porteurs = [i for i in decor_famille_dentites["ids"]
                if session.get(Company, i).neq is not None]
    assert not porteurs, (
        f"le(s) dossier(s) {porteurs} ont reçu le NEQ alors que trois dossiers le "
        "visaient — le refus en bloc n'a pas joué"
    )


def test_le_refus_est_annonce_AVANT_decrire(decor_famille_dentites, capsys):
    """*Une écriture refusée en silence se lit comme une écriture qui n'avait
    pas lieu d'être* — et personne ne saurait qu'un groupe attend un humain."""
    assert reresolution_neq.main([]) == 0
    sortie = capsys.readouterr().out
    assert "REFUSÉS EN BLOC" in sortie
    assert "preuve CONTRE l'appariement" in sortie


def test_deux_pretendants_restent_departages(decor_famille_dentites, db_session):
    """**La garde ne doit pas être trop large** — le cas à DEUX est celui pour
    lequel la conservation et l'ancienneté ont été décidées, et il reste traité.
    *Une garde qui refuse aussi le cas qu'elle devait laisser passer coûte le
    gain qu'on venait de gagner.*"""
    from sqlalchemy import select

    troisieme = db_session.get(Company, decor_famille_dentites["ids"][2])
    db_session.delete(troisieme)
    db_session.commit()

    assert reresolution_neq.main(["--appliquer"]) == 0
    db_session.expire_all()
    porteurs = [i for i in decor_famille_dentites["ids"][:2]
                if db_session.get(Company, i).neq == "8888888888"]
    assert len(porteurs) == 1, "à deux prétendants, le plus ancien doit encore l'obtenir"
    assert porteurs[0] == decor_famille_dentites["ids"][0], "ce n'est pas le plus ancien"


def test_les_refuses_sont_JOURNALISES_sans_principal(decor_famille_dentites):
    """⚠️ **Sans ce test, les 26 disparaissaient du journal.**

    Le `continue` d'origine les écartait en silence, et *« refusé » se serait lu
    comme « jamais rencontré »*.

    Et ils ne peuvent PAS être journalisés comme candidats de fusion : cette
    entrée-là affirme que l'un des deux est le bon — **exactement ce que le refus
    vient de refuser d'affirmer.**
    """
    from sqlalchemy import select

    from falkye.models.diagnostic_journal import DiagnosticJournal, TypeDiagnostic

    assert reresolution_neq.main(["--appliquer"]) == 0
    session = decor_famille_dentites["session"]
    entrees = list(session.execute(select(DiagnosticJournal)).scalars().all())
    assert len(entrees) == 3, f"{len(entrees)} entrées pour 3 dossiers refusés"
    for e in entrees:
        assert e.type_diagnostic == TypeDiagnostic.PROBLEME_AUTRE_CHANTIER
        assert e.company_id_candidat is None, (
            "un candidat de fusion a été affirmé sur un groupe dont le refus dit "
            "précisément qu'on ne sait pas lequel est le bon"
        )
        assert "refusée" in e.texte_description


# ---------------------------------------------------------------------------
# LES TROIS QUESTIONS D'ALEXANDRE, AVANT D'APPLIQUER  (2026-09-17)
# ---------------------------------------------------------------------------
#
# *Ce qui se passe si on l'applique deux fois, ce qui est journalisé, et comment
# on revient en arrière.* **Deux des trois avaient un défaut.**


def test_linstantane_couvre_EXACTEMENT_ce_que_lenrichissement_reecrit():
    """⚠️ **Le défaut trouvé le 2026-09-17, avant d'appliquer.**

    L'instantané ne portait que `neq` et `statut_resolution`. *Or
    `_enrich_from_req` réécrit huit autres champs* — défaire rendait le NEQ et
    laissait l'adresse, la ville, le secteur et le statut légal du registre :
    **un dossier ni dans son état d'avant, ni dans celui d'après.**

    Ce test compare la liste de l'instantané au CODE de l'enrichissement. *Un
    champ ajouté là-bas et oublié ici rendrait le retour arrière partiel, en
    silence.*
    """
    import ast
    import inspect

    from falkye import resolution
    from outils.reresolution_neq import CHAMPS_ENRICHIS

    source = inspect.getsource(resolution._enrich_from_req)
    arbre = ast.parse(source.strip())
    ecrits = {
        cible.attr
        for noeud in ast.walk(arbre)
        if isinstance(noeud, ast.Assign)
        for cible in noeud.targets
        if isinstance(cible, ast.Attribute)
        and isinstance(cible.value, ast.Name)
        and cible.value.id == "company"
    }
    manquants = ecrits - set(CHAMPS_ENRICHIS)
    assert not manquants, (
        f"`_enrich_from_req` réécrit {sorted(manquants)}, que l'instantané ne "
        "porte pas — le retour arrière serait partiel, et en silence"
    )


def test_defaire_remet_le_dossier_dans_son_etat_davant(decor, db_session, tmp_path, capsys):
    """*Sans commande pour défaire, « réversible » reste une intention.*"""
    from sqlalchemy import select

    from falkye.models.company import Company
    from outils import reresolution_neq

    assert reresolution_neq.main(["--appliquer", "--instantane", str(tmp_path)]) == 0
    capsys.readouterr()
    fichiers = sorted(tmp_path.glob("reresolution-*.json"))
    assert fichiers, "aucun instantané écrit"

    db_session.expire_all()
    poses = db_session.execute(
        select(Company).where(Company.neq.is_not(None))
    ).scalars().all()
    assert poses, "le décor n'a rien posé — ce test ne verrouille rien"

    assert reresolution_neq.main(["--defaire", str(fichiers[-1])]) == 0
    sortie = capsys.readouterr().out
    assert "défaits      :" in sortie
    # ⚠️ Seuls les dossiers de l'instantané sont concernés. *Le DÉTENTEUR
    # portait déjà son NEQ avant la passe : le défaire serait défaire ce que la
    # passe n'a jamais fait.*
    import json as _json

    db_session.expire_all()
    instantane = _json.loads(fichiers[-1].read_text(encoding="utf-8"))
    touches = [x["company_id"] for x in instantane["a_poser"]]
    assert touches, "l'instantané ne liste aucun dossier posé"
    for company_id in touches:
        company = db_session.get(Company, company_id)
        assert company.neq is None, f"#{company_id} porte encore un NEQ"
        assert company.nom_officiel_req is None, (
            "l'enrichissement n'a pas été défait — l'instantané est partiel"
        )


def test_defaire_NE_TOUCHE_PAS_un_dossier_dont_le_NEQ_a_change(decor, db_session, tmp_path):
    """⚠️ *Un dossier dont le NEQ n'est plus celui qu'on avait posé n'est plus le
    nôtre, et le défaire écraserait quelqu'un d'autre.*"""
    from sqlalchemy import select

    from falkye.models.company import Company
    from outils import reresolution_neq

    assert reresolution_neq.main(["--appliquer", "--instantane", str(tmp_path)]) == 0
    fichiers = sorted(tmp_path.glob("reresolution-*.json"))
    db_session.expire_all()
    pose = db_session.execute(
        select(Company).where(Company.neq.is_not(None))
    ).scalars().first()
    pose.neq = "9999999999"      # un tiers est passé par là
    db_session.commit()

    assert reresolution_neq.main(["--defaire", str(fichiers[-1])]) == 0
    db_session.expire_all()
    assert db_session.get(Company, pose.id).neq == "9999999999", (
        "le NEQ d'un tiers a été écrasé"
    )


def test_comparer_pagine_avec_depuis(decor, capsys):
    """*« Si `--comparer` peut le faire par lot »* — il le peut maintenant."""
    from outils import reresolution_neq

    assert reresolution_neq.main(["--comparer", "1"]) == 0
    assert "LES PAIRES — 1 à 1" in capsys.readouterr().out
    assert reresolution_neq.main(["--comparer", "1", "--depuis", "1"]) == 0
    assert "LES PAIRES — 2 à" in capsys.readouterr().out


def test_appliquer_DEUX_FOIS_ne_redouble_pas_le_JOURNAL(decor, db_session, tmp_path, capsys):
    """⚠️ **Le défaut trouvé le 2026-09-17, avant d'appliquer.**

    La passe était idempotente sur les DOSSIERS — un dossier posé sort de
    `Company.neq IS NULL` — **et pas sur le JOURNAL** : un dossier CONSERVÉ y
    reste, donc il était re-journalisé à chaque exécution. *Et c'est la file
    qu'un humain doit dépiler.*
    """
    from sqlalchemy import func, select as _select

    from falkye.models.diagnostic_journal import DiagnosticJournal
    from outils import reresolution_neq

    def compter():
        return db_session.execute(
            _select(func.count()).select_from(DiagnosticJournal)
        ).scalar()

    assert reresolution_neq.main(["--appliquer", "--instantane", str(tmp_path)]) == 0
    apres_un = compter()
    assert apres_un > 0, "le décor n'a rien journalisé — ce test ne verrouille rien"
    capsys.readouterr()

    assert reresolution_neq.main(["--appliquer", "--instantane", str(tmp_path)]) == 0
    sortie = capsys.readouterr().out
    assert compter() == apres_un, "le journal a été redoublé par la seconde passe"
    assert "déjà au journal" in sortie, sortie


# ---------------------------------------------------------------------------
# SUR QUOI LA DÉCISION S'EST PRISE — cas 33, dans la passe
# ---------------------------------------------------------------------------

def test_la_paire_dit_LA_FORME_QUI_A_MATCHE_et_pas_seulement_la_denomination(decor, capsys):
    """⚠️ **Le cas `#16`.**

    *`16790224 Canada Inc.` contre `LES ENTREPRISES DOUGLAS POWERTECH INC.` à
    100, sans un caractère commun.* **La décision s'est prise sur une troisième
    chaîne, et la sortie doit la nommer** — sinon on relit une fausse résolution
    là où il y a un appariement juste.
    """
    assert reresolution_neq.main(["--comparer", "20"]) == 0
    sortie = capsys.readouterr().out
    bloc = sortie.split("registre : LES ENTREPRISES DOUGLAS POWERTECH INC.")[-1]
    assert "a matché : 16790224 Canada Inc." in bloc, bloc
    assert "gisement NOM_ASSUJ" in bloc, bloc
    assert "statut en vigueur" in bloc, bloc


def test_la_paire_dont_la_DENOMINATION_a_decide_nest_pas_marquee(decor, capsys):
    """*Marquer toutes les paires ferait de l'avertissement un décor.*"""
    assert reresolution_neq.main(["--comparer", "20"]) == 0
    # ⚠️ Le nom paraît DEUX fois dans le bloc — en « registre » et en « a matché ».
    # *`split(...)[1]` rendrait le vide entre les deux*; on prend la queue.
    bloc = capsys.readouterr().out.split("registre : boulangerie saint-viateur inc")[-1]
    ligne = next(l for l in bloc.splitlines() if "a matché" in l)
    assert "⚠️" not in ligne, ligne
    gisement = next(l for l in bloc.splitlines() if "gisement" in l)
    assert "(dénomination élue)" in gisement, gisement
    # ⚠️ *`req_entries` ne porte pas de statut DE NOM* : ne rien dire plutôt que
    # d'écrire « inconnu », qui ferait chercher une lecture manquée.
    assert "statut" not in gisement, gisement


def test_le_rapport_COMPTE_les_paires_decidees_autrement(decor, capsys):
    """⚠️ *Cinquante paires lues ne disent pas combien sont dans ce cas.*"""
    assert reresolution_neq.main([]) == 0
    sortie = capsys.readouterr().out
    assert "SUR QUOI LA DÉCISION S'EST PRISE" in sortie
    ligne = next(l for l in sortie.splitlines()
                 if "AUTRE que la dénomination sociale élue" in l)
    assert ": 1 sur 2" in ligne, ligne
    bloc = sortie.split("gisement de la forme qui a décidé")[1]
    assert "NOM_ASSUJ" in bloc and bloc.split("NOM_ASSUJ")[1].split()[0] == "1", bloc


def test_un_statut_absent_se_dit_INCONNU_et_ne_se_devine_pas():
    """*Un statut absent n'est pas « en vigueur ».*"""
    assert reresolution_neq._statut_lisible(None) == "inconnu"
    assert reresolution_neq._statut_lisible("A") == "en vigueur"
    assert reresolution_neq._statut_lisible("I") == "PLUS EN VIGUEUR"
    assert reresolution_neq._statut_lisible("?") == "non qualifié"


def test_linstantane_ne_porte_PAS_les_champs_de_lecture(decor):
    """⚠️ *L'instantané porte ce qu'il faut pour DÉFAIRE, et rien d'autre.*"""
    paire = {"neq": "1", "_forme_normalisee": "x", "champs_avant": {}}
    assert reresolution_neq._sans_champs_de_travail(paire) == {
        "neq": "1", "champs_avant": {}}


def test_une_forme_comptee_comme_AUTRE_nest_JAMAIS_la_denomination_elue(decor, capsys):
    """⚠️ **Ce qui décide comment se lit un gisement `(inconnu)`.**

    Le compte « forme AUTRE que la dénomination sociale élue » exclut par
    construction les formes élues — `est_la_denomination_elue` est exactement le
    filtre. **Donc un `(inconnu)` dans cette ventilation ne peut PAS s'expliquer
    par « c'est la dénomination élue, absente de `req_noms` »** : c'est une
    ligne de `req_noms` dont la colonne `gisement` est vide.

    *Et le chargeur en pose toujours une* (`_charger_tous_les_noms`) — **donc un
    `(inconnu)` désigne des lignes ANTÉRIEURES à la colonne, pas une propriété
    du mécanisme.** La distinction n'est pas cosmétique : la première lecture
    referme la question, la seconde ouvre un rechargement.
    """
    from falkye.sources import req as req_source

    assert reresolution_neq.main([]) == 0
    sortie = capsys.readouterr().out
    bloc = sortie.split("gisement de la forme qui a décidé")[1].split("⚠️")[0]
    assert req_source.GISEMENT_DENOMINATION_ELUE not in bloc, bloc


def test_la_denomination_elue_porte_TOUJOURS_son_gisement_propre(decor):
    """*Elle vient de `req_entries`, pas d'un des quatre gisements de noms.*"""
    from falkye.models.company import Company
    from falkye.sources import req as req_source

    session = decor["session"]
    company = session.get(Company, decor["libre"])
    matches = req_source.resolve_neq_by_name(session, company.nom_detecte)
    formes = req_source.formes_retenues(session, matches[:1])
    (forme,) = formes.values()
    assert forme.est_la_denomination_elue
    assert forme.gisement == req_source.GISEMENT_DENOMINATION_ELUE
    assert forme.statut is None


def test_une_forme_de_req_noms_porte_le_gisement_du_chargeur(decor):
    from falkye.models.company import Company
    from falkye.sources import req as req_source

    session = decor["session"]
    company = session.get(Company, decor["autre_forme"])
    matches = req_source.resolve_neq_by_name(session, company.nom_detecte)
    formes = req_source.formes_retenues(session, matches[:1])
    (forme,) = formes.values()
    assert not forme.est_la_denomination_elue
    assert (forme.gisement, forme.statut) == ("NOM_ASSUJ", "A")
    assert forme.nom_publie == "16790224 Canada Inc."


def test_la_reprise_ne_peut_PAS_remplacer_un_NEQ_deja_pose():
    """⏸️ **La garde des 35 CHANGEMENTS** *(décision d'Alexandre, 2026-09-23 —
    registre D63)*.

    *« Poser une identité et en REMPLACER une ne sont pas le même geste. »* Le
    troisième temps déplacerait le NEQ de **35 dossiers déjà posés**, dont
    plusieurs vers une entreprise **radiée** (`#594`, `#1728`, `#4949`). **Ils
    sont en suspens jusqu'à l'étape de réouverture, avec la règle du statut
    par-dessus.**

    ⚠️ **Et la garde est STRUCTURELLE, pas une consigne** : la passe ne balaie
    que `Company.neq IS NULL`, et chaque paire porte `neq_avant = None`. *Une
    consigne se contourne en changeant un argument; une population ne se
    contourne qu'en réécrivant la requête — ce que ce test rend visible.*
    """
    import inspect

    source = inspect.getsource(reresolution_neq.main)
    assert "select(Company).where(Company.neq.is_(None))" in source
    assert '"neq_avant": None' in source
    # ⛔ Aucun chemin d'écriture ne lit un NEQ d'avant NON nul.
    assert "neq_avant\": company.neq" not in source


# --------------------------------------------------------------------------
# L'ÉCART À LA MAIN, et les deux règles candidates — 2026-09-24
# --------------------------------------------------------------------------


def test_la_graphie_de_personne_tient_le_cas_qui_la_pose():
    """⚠️ **UNE HYPOTHÈSE, pas un fait du registre.** *Elle vient d'UN cas* —
    `« BOUCHARD, MARTIN »`, la forme qui a rattaché `#3705 Ferme Martin
    Bouchard` à `« Éditions Melançon »`.

    ⛔ **Et elle a été resserrée le jour même, sur un faux positif trouvé en
    l'essayant** : `« Boulangerie, Patisserie du Coin »` passait.
    """
    from outils.reresolution_neq import forme_de_personne

    # Le cas qui la pose, et ses voisins de même forme.
    assert forme_de_personne("BOUCHARD, MARTIN")
    assert forme_de_personne("TREMBLAY, MARIE-JOSEE")
    assert forme_de_personne("SMITH, JOHN ROBERT")
    assert forme_de_personne("ST-PIERRE, JEAN-GUY")
    # ⛔ Le faux positif qui l'a resserrée.
    assert not forme_de_personne("Boulangerie, Patisserie du Coin")
    # Une personne MORALE n'en est pas une, quelle que soit sa ponctuation.
    assert not forme_de_personne("Gestion Tremblay, Inc.")
    assert not forme_de_personne("Ferme Martin Bouchard")
    assert not forme_de_personne("9412-0001 Québec inc.")
    assert not forme_de_personne(None)


def test_la_graphie_ne_gouverne_RIEN_dans_le_chemin_d_ecriture():
    """⛔ **Elle sert à un COMPTE, pas à une décision.** *Une règle posée sur un
    seul exemple retire des appariements justes en silence* — et celle-ci
    attend le nombre qu'`--comparer` rendra sur la population entière."""
    import pathlib

    for chemin in pathlib.Path("falkye").rglob("*.py"):
        texte = chemin.read_text(encoding="utf-8")
        assert "forme_de_personne" not in texte, chemin
        assert "GRAPHIE_DE_PERSONNE" not in texte, chemin
    # Et dans l'outil, elle n'entre pas dans ce qui décide de poser.
    source = pathlib.Path("outils/pose_du_neq.py").read_text(encoding="utf-8")
    assert "forme_de_personne" not in source


def test_l_ecart_a_la_main_retire_le_dossier_SANS_en_faire_gagner_un_autre():
    """⚠️ **Écarté APRÈS la résolution des collisions, et c'est délibéré.**
    *L'écarter avant libérerait son NEQ pour un autre dossier du lot* —
    « écarter ce dossier » deviendrait « en faire gagner un autre »."""
    import inspect

    source = inspect.getsource(reresolution_neq.main)
    pose = source.index("resoudre_les_collisions(")
    ecart = source.index('if args.ecarter:')
    assert pose < ecart, "l'écart doit venir APRÈS la résolution des collisions"
    # L'écarté est CONSERVÉ dans `pris`, avec son motif — jamais effacé du rapport.
    assert 'p["motif"] = "ÉCARTÉ À LA MAIN' in source
    assert "pris.append(p)" in source


def test_un_ecart_SANS_EFFET_se_dit():
    """*Un écart silencieux qui ne portait sur rien laisse croire qu'il a
    porté* — et la prochaine passe reposera le dossier."""
    import inspect

    source = inspect.getsource(reresolution_neq.main)
    assert "SANS EFFET" in source
    assert "n'était pas dans les NEQ à poser" in source
