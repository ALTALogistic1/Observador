#!/usr/bin/env python3
"""Poser un NEQ sur un dossier — **la machinerie d'écriture, nommée UNE fois.**

**Le fait qui l'extrait** *(2026-09-19)*. Deux passes posent des NEQ : la
**reprise** *(`outils/reresolution_neq.py`)*, qui pose ce que le NOM a tranché,
et l'**écriture des départages** *(`outils/ecriture_des_departages.py`)*, qui
pose ce que l'ADRESSE a tranché. **Elles ne diffèrent que par la façon dont la
paire `(dossier, NEQ)` est produite.** *Tout ce qui vient après — l'instantané,
les collisions, le refus au-delà de deux prétendants, la re-vérification au
moment de poser, l'enrichissement, la journalisation, le retour arrière — est le
même geste.*

> ⚠️ **Recopier ce geste serait cas 41 sur un chemin d'ÉCRITURE.** *Un scoreur
> recopié rend un chiffre faux et se rattrape; une règle de conservation
> recopiée qui diverge perd une identité, et l'instantané de l'autre copie ne la
> rend pas.*

## Le contrat d'une PAIRE

Un `dict`, et les passes le remplissent toutes les deux de la même façon :

| clé | |
|---|---|
| `company_id`, `nom_detecte` | le dossier |
| `neq`, `nom_registre`, `score` | ce qu'on veut poser, et sur quoi |
| `neq_avant`, `statut_avant`, `champs_avant` | **l'état d'AVANT** — ce qui rend le geste réversible |
| `_anciennete` | ⚠️ départage une collision. Préfixé `_` : **retiré de l'instantané** |
| `detenteur_id`, `detenteur_nom`, `motif` | posés par la machinerie quand la paire est CONSERVÉE plutôt que posée |

⚠️ **Les clés préfixées `_` sont des intermédiaires de calcul et ne vont PAS à
l'instantané** — *il porte l'état d'avant, pas la façon dont la passe a raisonné
ce jour-là.*

## Ce que cette machinerie ne décide JAMAIS

**Quel NEQ va sur quel dossier.** *C'est l'appelant qui le dit, et c'est là que
les deux passes diffèrent.* **Ici on ne décide que ce qui arrive quand deux
dossiers veulent le même NEQ, et ce qu'on garde pour pouvoir revenir.**
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

#: ⛔ **Au-delà de ce nombre de prétendants, personne n'obtient le NEQ.**
#: *Le nombre de prétendants est lui-même une preuve CONTRE l'appariement* — voir
#: `resoudre_les_collisions`.
PRETENDANTS_MAX_POUR_TRANCHER = 2

#: Le statut d'un nom au registre, tel que `Nom.csv` l'écrit. *Traduit pour la
#: lecture, et **jamais deviné** : un statut absent se dit « inconnu », pas
#: « en vigueur ».*
STATUTS_LISIBLES = {"A": "en vigueur", "I": "PLUS EN VIGUEUR", "?": "non qualifié"}


#: Où l'instantané d'avant est déposé. ⚠️ **Recopié dans TROIS outils jusqu'au
#: 2026-09-20** — `reresolution_neq`, `ecriture_des_departages`,
#: `promotion_ville`. *Une constante recopiée diverge sans que rien ne le dise,
#: et celle-ci désigne le seul répertoire que les unités peuvent écrire
#: (`ReadWritePaths`).* **Elle vit ici, près du geste qu'elle gouverne** — même
#: raison que `PRETENDANTS_MAX_POUR_TRANCHER`.
DOSSIER_INSTANTANE = Path("/var/lib/falkye")


def statut_lisible(statut: str | None) -> str:
    """⚠️ *Un nom PLUS EN VIGUEUR apparie quand même* — le registre le porte, et
    l'entreprise l'a porté. **Mais ça se lit avant d'écrire**, parce qu'un
    appariement sur un nom retiré depuis dix ans ne vaut pas un appariement sur
    le nom courant."""
    if statut is None:
        return "inconnu"
    return STATUTS_LISIBLES.get(statut, statut)


def sans_champs_de_travail(paire: dict) -> dict:
    """La paire sans ses champs de calcul (préfixés `_`).

    *L'instantané porte l'état d'AVANT, ce qui suffit à défaire le geste* — y
    mêler les intermédiaires de décision rendrait son format dépendant de la
    façon dont la passe raisonne ce jour-là.
    """
    return {k: v for k, v in paire.items() if not k.startswith("_")}


#: Les champs que `falkye/resolution.py::_enrich_from_req` réécrit après avoir
#: posé un NEQ. **La liste est ici parce que l'instantané doit couvrir EXACTEMENT
#: ce que le geste touche** — un champ ajouté là-bas et oublié ici rendrait le
#: retour arrière partiel, en silence. *Un test compare les deux.*
CHAMPS_ENRICHIS = (
    "nom_officiel_req", "statut_legal", "adresse", "ville", "region",
    "code_postal", "secteur_activite_code", "secteur_activite_libelle",
)


def champs_enrichis(company) -> dict:
    """L'état d'avant des champs que l'enrichissement va réécrire."""
    return {
        champ: getattr(getattr(company, champ), "value", getattr(company, champ))
        for champ in CHAMPS_ENRICHIS
    }


def defaire(db_session, chemin: Path) -> int:
    """Rejoue l'instantané à l'envers. **Et refuse de toucher ce qui a bougé
    depuis** : un dossier dont le NEQ n'est plus celui qu'on avait posé n'est
    plus le nôtre, et le défaire écraserait quelqu'un d'autre."""
    import json as _json

    from falkye.models.company import Company, StatutLegal, StatutResolution

    contenu = _json.loads(chemin.read_text(encoding="utf-8"))
    a_defaire = contenu.get("a_poser", [])
    print(f"   instantané : {chemin}")
    print(f"   NEQ posés à défaire : {len(a_defaire)}\n")
    defaits = ignores = introuvables = 0
    for p in a_defaire:
        company = db_session.get(Company, p["company_id"])
        if company is None:
            introuvables += 1
            continue
        if company.neq != p["neq"]:
            ignores += 1
            continue
        company.neq = p["neq_avant"]
        if p.get("statut_avant"):
            company.statut_resolution = StatutResolution(p["statut_avant"])
        for champ, valeur in (p.get("champs_avant") or {}).items():
            if champ == "statut_legal":
                setattr(company, champ, StatutLegal(valeur) if valeur else None)
            else:
                setattr(company, champ, valeur)
        defaits += 1
    db_session.commit()
    print(f"   défaits      : {defaits}")
    print(f"   ignorés      : {ignores}   (le NEQ a changé depuis — plus le nôtre)")
    if introuvables:
        print(f"   introuvables : {introuvables}")
    print("\n   ⚠️ Les rapprochements JOURNALISÉS ne sont pas retirés : ce sont des")
    print("      observations, pas des écritures sur les dossiers.")
    return 0




def ecrire_instantane(dossier: str, prefixe: str, contenu: dict) -> Path | None:
    """L'état d'AVANT, **écrit avant le commit**. `None` si l'écriture échoue.

    ⚠️ *Sans lui, « réversible » est une intention.* **Un refus d'écrire est un
    refus d'agir** — le même défaut que le chemin d'archive du diff, une table
    plus loin.
    """
    horodatage = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    try:
        chemin = Path(dossier)
        chemin.mkdir(parents=True, exist_ok=True)
        chemin = chemin / f"{prefixe}-{horodatage}.json"
        chemin.write_text(
            json.dumps(contenu, ensure_ascii=False, indent=1), encoding="utf-8"
        )
    except OSError as exc:
        print(f"\n⛔ REFUS : l'instantané ne peut pas être écrit ({exc}).\n"
              "   Rien n'a été modifié. Un geste irréversible sans trace de l'état\n"
              "   d'avant n'est pas un geste réversible.", file=sys.stderr)
        return None
    return chemin


def resoudre_les_collisions(a_poser: list[dict], pris: list[dict]):
    """`(a_poser, collisions, refuses_en_bloc)` — **qui garde le NEQ quand
    plusieurs dossiers le visent.**

    *Les perdants ne sont pas perdus : ils passent dans `pris`, donc conservés
    et journalisés.*
    """
    libres = a_poser
    par_neq: dict[str, list[dict]] = {}
    for paire in libres:
        par_neq.setdefault(paire["neq"], []).append(paire)

    collisions = {neq: v for neq, v in par_neq.items() if len(v) > 1}
    refuses_en_bloc: dict[str, int] = {}
    libres = []
    for neq, pretendants in par_neq.items():
        if len(pretendants) == 1:
            libres.append(pretendants[0])
            continue
        # LE PLUS ANCIEN GAGNE — `first_detected_at`, départagé par `id`.
        #
        # **Ce n'est pas une échelle neuve : c'est celle du produit.**
        # `falkye/dedup_entreprises.py` la pose déjà pour le cas analogue —
        # *« le PRINCIPAL est toujours le dossier le plus ANCIEN
        # (first_detected_at) »*. Inventer un second critère ici ferait
        # dépendre l'identité d'une entreprise de la table par laquelle on
        # arrive.
        #
        # ⚠️ **Et l'ancienneté n'est pas la vérité.** Le dossier le plus vieux
        # peut être le plus mal saisi. Mais ce choix ne décide pas quel nom
        # est juste : il décide seulement qui PORTE le NEQ pendant qu'un
        # humain regarde la paire. **C'est la conservation qui rend ce choix
        # bon marché** — le perdant n'est pas perdu, il est journalisé.
        # ⛔ **AU-DELÀ DE DEUX PRÉTENDANTS, PERSONNE NE L'OBTIENT.**
        #
        # *Le fait qui a écrit ce refus* (2026-09-17, relevé par Alexandre) :
        # **le NEQ 8879690699 attirait 26 dossiers** — CISSS de la
        # Montérégie-Centre, CISSS Gaspésie, CIUSSS de l'Outaouais, CHUM,
        # Centre universitaire de santé McGill, Institut de Cardiologie…
        # **26 organisations RÉELLEMENT DISTINCTES, scores de 95 à 100.**
        #
        # ⚠️ **Le nombre de prétendants est lui-même une preuve CONTRE
        # l'appariement.** Deux dossiers qui convergent, c'est un doublon
        # plausible — la situation pour laquelle la conservation a été
        # pensée. *Vingt-six, c'est un nom qui désigne une FAMILLE d'entités,
        # et l'ancienneté n'y a plus aucun sens* : elle désignerait un
        # gagnant dans un groupe dont probablement AUCUN membre n'est le bon.
        #
        # **Ce n'est pas un réglage de seuil.** Les noms se ressemblent
        # réellement; le scoreur ne se trompe pas, il répond à une autre
        # question que celle qu'on lui pose. *Monter le seuil n'y ferait
        # rien — ces scores sont à 100.*
        #
        # **Le refus ne peut que RÉDUIRE les écritures**, jamais en produire
        # une. Les 26 restent des dossiers séparés, tous journalisés.
        if len(pretendants) > PRETENDANTS_MAX_POUR_TRANCHER:
            for pretendant in pretendants:
                pretendant["detenteur_id"] = None
                pretendant["detenteur_nom"] = None
                pretendant["motif"] = (
                    f"REFUS — {len(pretendants)} dossiers visent ce NEQ; "
                    "le nombre de prétendants est une preuve contre "
                    "l'appariement, et aucun ne l'obtient"
                )
                pris.append(pretendant)
            refuses_en_bloc[neq] = len(pretendants)
            continue

        pretendants.sort(key=lambda x: (x["_anciennete"] is None,
                                        x["_anciennete"], x["company_id"]))
        gagnant, *perdants = pretendants
        libres.append(gagnant)
        for perdant in perdants:
            perdant["detenteur_id"] = gagnant["company_id"]
            perdant["detenteur_nom"] = gagnant["nom_detecte"]
            perdant["motif"] = "collision dans le lot — le plus ancien garde le NEQ"
            pris.append(perdant)

    return libres, collisions, refuses_en_bloc


def poser_les_neq(db_session, a_poser: list[dict], pris: list[dict]):
    """`(posés, tardifs)` — **l'écriture elle-même**, disponibilité re-vérifiée
    au moment de poser."""
    from falkye.models.company import Company, StatutResolution
    from falkye.resolution import _enrich_from_req

    session = db_session
    libres = a_poser
    poses = 0
    tardifs = 0
    for p in libres:
        company = session.get(Company, p["company_id"])
        # ⚠️ **LA DISPONIBILITÉ RE-VÉRIFIÉE AU MOMENT DE POSER**, et pas
        # seulement au moment de décider. Les collisions internes au lot
        # sont déjà résolues plus haut; celle-ci attrape l'autre cas — **un
        # cycle de production qui aurait pris ce NEQ entre le rapport et
        # l'écriture.** *Une vérification faite d'avance répond à l'état
        # d'avant, jamais à celui du moment où l'on écrit.*
        occupant = session.execute(
            select(Company).where(Company.neq == p["neq"])
        ).scalar_one_or_none()
        if occupant is not None:
            p["detenteur_id"] = occupant.id
            p["detenteur_nom"] = occupant.nom_detecte
            p["motif"] = "NEQ pris entre le rapport et l'écriture"
            pris.append(p)
            tardifs += 1
            continue
        company.neq = p["neq"]
        company.statut_resolution = StatutResolution.RESOLU
        _enrich_from_req(session, company, p["neq"])
        session.flush()  # la contrainte parle ICI, sur UNE ligne nommée
        poses += 1

    return poses, tardifs


def journaliser_les_conserves(db_session, pris: list[dict], etiquette: str):
    """`(journalisés, déjà)` — **les conservés entrent au journal, jamais en
    base.** `etiquette` nomme la passe dans le texte du diagnostic."""
    from falkye.dedup_entreprises import journaliser_candidat_fusion
    from falkye.models.company import Company
    from falkye.models.diagnostic_journal import DiagnosticJournal, TypeDiagnostic

    session = db_session
    journalises = 0
    deja_journalises = 0

    def _deja_au_journal(principal_id, candidat_id, type_diagnostic) -> bool:
        """⚠️ **Idempotent sur le JOURNAL, pas seulement sur les dossiers.**

        *Un dossier posé sort de la population; un dossier CONSERVÉ y reste,
        donc il était re-journalisé à chaque exécution* — et c'est précisément
        la file qu'un humain doit dépiler.
        """
        requete = select(DiagnosticJournal.id).where(
            DiagnosticJournal.type_diagnostic == type_diagnostic,
            DiagnosticJournal.company_id_principal == principal_id,
            DiagnosticJournal.statut == "a_examiner",
        )
        requete = requete.where(
            DiagnosticJournal.company_id_candidat.is_(None)
            if candidat_id is None
            else DiagnosticJournal.company_id_candidat == candidat_id
        )
        return session.execute(requete.limit(1)).scalar_one_or_none() is not None

    journalises = 0
    deja_journalises = 0
    from falkye.models.diagnostic_journal import DiagnosticJournal, TypeDiagnostic

    def _deja_au_journal(principal_id: int, candidat_id: int | None,
                         type_diagnostic) -> bool:
        """⚠️ **La passe était idempotente sur les DOSSIERS et ne l'était pas
        sur le JOURNAL** *(relevé le 2026-09-17, avant d'appliquer)*.

        Un dossier posé sort de la population — `Company.neq IS NULL` ne le
        rend plus. **Mais un dossier CONSERVÉ y reste, donc il était
        re-journalisé à chaque exécution.** *Et c'est précisément la file
        qu'un humain doit dépiler : la polluer de doublons rend le travail
        plus long à chaque relance.*
        """
        requete = select(DiagnosticJournal.id).where(
            DiagnosticJournal.type_diagnostic == type_diagnostic,
            DiagnosticJournal.company_id_principal == principal_id,
            DiagnosticJournal.statut == "a_examiner",
        )
        requete = requete.where(
            DiagnosticJournal.company_id_candidat.is_(None)
            if candidat_id is None
            else DiagnosticJournal.company_id_candidat == candidat_id
        )
        return session.execute(requete.limit(1)).scalar_one_or_none() is not None

    for p in pris:
        company = session.get(Company, p["company_id"])
        if company is None:
            continue
        attendu = (
            TypeDiagnostic.PROBLEME_AUTRE_CHANTIER
            if p.get("detenteur_id") is None
            else TypeDiagnostic.CANDIDAT_FUSION_ENTREPRISE
        )
        principal = (company.id if p.get("detenteur_id") is None
                     else p["detenteur_id"])
        candidat = None if p.get("detenteur_id") is None else company.id
        if _deja_au_journal(principal, candidat, attendu):
            deja_journalises += 1
            continue
        if p.get("detenteur_id") is None:
            # ⚠️ **UN GROUPE REFUSÉ N'A PAS DE PRINCIPAL, ET C'EST LE FOND.**
            # `journaliser_candidat_fusion` demande deux dossiers et affirme
            # que l'un est le bon — *exactement ce qu'on vient de refuser
            # d'affirmer.* Le journaliser ainsi contredirait le refus.
            #
            # Journalisé donc comme un PROBLÈME à examiner, rattaché au seul
            # dossier concerné. **Sans ça, les 26 disparaissaient du
            # journal** : le `continue` d'origine les écartait en silence, et
            # « refusé » se serait lu comme « jamais rencontré ».
            session.add(DiagnosticJournal(
                type_diagnostic=TypeDiagnostic.PROBLEME_AUTRE_CHANTIER,
                profile_id=None,
                texte_description=(
                    f"{etiquette} — #{company.id} « {company.nom_detecte} » "
                    f"vise {p['neq']} ({p.get('motif', '')}). Score {p['score']}, "
                    f"registre « {p['nom_registre']} »."
                ),
                statut="a_examiner",
                company_id_principal=company.id,
                company_id_candidat=None,
                score_similarite=p["score"],
            ))
            journalises += 1
            continue
        detenteur = session.get(Company, p["detenteur_id"])
        if detenteur is None:
            continue
        # Le DÉTENTEUR est le principal : il porte déjà le NEQ, donc il est
        # le dossier que le registre désigne. Le rapprochement est proposé,
        # jamais exécuté — `statut="a_examiner"`.
        journaliser_candidat_fusion(
            session, detenteur, company, p["score"], statut="a_examiner"
        )
        journalises += 1

    return journalises, deja_journalises
