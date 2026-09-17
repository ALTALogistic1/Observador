#!/usr/bin/env python3
"""UN appariement, montré en entier — la requête, les candidats, et ce qui est
passé au scoreur.

**La question qu'il tranche** *(Alexandre, 2026-09-16)* : *« Pour
`9309-3927 Quebec inc`, est-ce que `9309-3927 QUÉBEC INC.` est dans les candidats
récupérés? S'il y est et score 66, le score ment. S'il n'y est pas, la requête ne
le trouve pas — et c'est là qu'est le mur. »*

**Pourquoi un cas entier plutôt qu'une distribution de plus.** Trois hypothèses
ont été mesurées et sont tombées : *le seuil* (la masse est trop basse), *la
normalisation* (rejeu à zéro gain), *le champ `nom_normalise`*. **Il
reste la récupération des candidats, et rien d'autre** — et une distribution ne
dira pas si une ligne précise est dans une liste précise. **Un compte agrégé
répond « combien »; il ne répond jamais « où ».**

**Ce que l'outil montre, étape par étape, sans en sauter une.**

1. La normalisation de la requête, avec `repr` et longueur — *pas une
   description : la valeur.*
2. Le préfixe extrait, et **le SQL RÉELLEMENT ÉMIS**, valeurs liées comprises.
3. Le plan d'exécution SQLite (`EXPLAIN QUERY PLAN`) — *un SEARCH et un SCAN ne
   récupèrent pas le même lot.*
4. Les candidats rendus : `neq`, `nom`, `nom_normalise`, sa longueur et son
   `typeof` SQLite.
5. **La ligne ATTENDUE est-elle dedans?** Si non, quatre recherches directes la
   cherchent par d'autres chemins — *pour distinguer « absente du miroir » de
   « présente mais non récupérée », qui appellent des correctifs opposés.*
6. Le dictionnaire `choices` **tel qu'il est passé** à `process.extract`, et son
   classement complet.
7. Le score recalculé sur les deux formes affichées, à côté du score rendu.

⚠️ **Il emprunte les fonctions du moteur** — `candidats_par_nom`,
`resolve_neq_by_name`, `normaliser`. *Une requête recopiée à côté mesurerait sa
propre copie*, et c'est exactement l'écart qu'on cherche.

⚠️ **PORTÉE.** Lecture seule, sur le miroir local. Un seul nom. *Ce qu'il montre
vaut pour CE cas* — **une cause établie sur une ligne n'est pas une cause
établie sur la population**, et l'étape 8 dit ce que le moteur DÉCIDE.

Usage :
    python3 outils/trace_un_appariement.py --nom "9309-3927 Quebec inc" \\
        --attendu "9309-3927 QUÉBEC INC."
    python3 outils/trace_un_appariement.py --nom "Ferme Dallaire Frères SENC"
"""
from __future__ import annotations

import argparse
import sys

#: Combien de candidats sont détaillés ligne à ligne. Au-delà, seul le compte est
#: rendu — **et le fait qu'il y ait eu troncature est dit**, jamais tu.
#: La borne de `candidats_par_nom` contre le MIROIR — **pas**
#: `LIMITE_CANDIDATS = 500`, qui borne le dédoublonnage entre `Company`.
#: *Deux bornes, deux tables, deux chemins, et les confondre fait chercher
#: le mur du mauvais côté.*
BORNE_MOTEUR = 2000

DETAIL_MAX = 40


def apercu(valeur, largeur: int = 58) -> str:
    """`repr` tronqué. **`repr` et pas `str`** : une chaîne vide, une chaîne d'un
    espace et `None` se ressemblent à l'affichage et n'ont pas la même cause."""
    texte = repr(valeur)
    return texte if len(texte) <= largeur else texte[: largeur - 1] + "…"


def sql_emis(requete) -> str:
    """Le SQL avec ses valeurs liées substituées — *ce que SQLite reçoit, pas ce
    que SQLAlchemy annonce.*"""
    try:
        return str(requete.compile(compile_kwargs={"literal_binds": True}))
    except Exception as exc:  # noqa: BLE001 - un type non littéralisable n'est pas un échec
        return f"(non littéralisable : {type(exc).__name__}) {requete}"


#: Les familles de la ventilation, telles que le MOTEUR les décide.
#: *Une famille nommée ici et calculée autrement ailleurs ne serait pas la même
#: famille* — c'est `neq_retenu` qui tranche, jamais une règle recopiée.
FAMILLES = ("resoluble", "ambigu", "trop_faible", "aucun_candidat")


def _famille(matches, neq_decide) -> str:
    """Dans quelle famille le MOTEUR range ce dossier.

    ⚠️ **Le classement vient de `neq_retenu`**, la fonction que le produit
    appelle. *Recopier la règle ici ferait échantillonner des familles que le
    produit ne connaît pas.*
    """
    from falkye.resolution import SEUIL_RESOLUTION_CONFIANTE

    if not matches:
        return "aucun_candidat"
    if neq_decide is not None:
        return "resoluble"
    return "trop_faible" if matches[0].score < SEUIL_RESOLUTION_CONFIANTE else "ambigu"


def _jumeau_exact(forme: str | None) -> str | None:
    """Le NEQ dont le nom normalisé est EXACTEMENT celui du dossier, s'il existe.

    **Ce n'est pas une présélection du résultat** *(cas 42)* : on sélectionne sur
    l'ÉCHEC — la famille vient de `neq_retenu` — et on cherche ensuite si la
    bonne réponse existait. *Sélectionner des échecs dont on sait que la réponse
    existe est la seule façon de distinguer « absent du lot » de « présent et mal
    scoré ».*
    """
    if not forme:
        return None
    from sqlalchemy import select

    from falkye.db import get_session
    from falkye.models.req_entry import REQEntry
    from falkye.models.req_nom import REQNom

    session = get_session()
    try:
        trouve = session.execute(
            select(REQEntry.neq).where(REQEntry.nom_normalise == forme).limit(1)
        ).scalar_one_or_none()
        if trouve is None:
            trouve = session.execute(
                select(REQNom.neq).where(REQNom.nom_normalise == forme).limit(1)
            ).scalar_one_or_none()
        return trouve
    finally:
        session.close()


def _tracer_depuis_la_base(par_famille: int, familles: tuple[str, ...]) -> int:
    """Trace N dossiers PAR FAMILLE d'échec, classés par la décision du moteur.

    ⚠️ **Le critère précédent était faux, et son défaut mérite d'être écrit**
    *(relevé par Alexandre, 2026-09-17)*. Il retenait les dossiers **dont le nom
    normalisé existait par correspondance EXACTE dans le miroir** — c'est-à-dire
    *ceux dont il avait déjà démontré qu'ils devaient réussir*. **Trois cas
    tracés, trois scores de 100, et aucun dossier qui échoue n'avait été
    regardé.**

    *Un critère de sélection qui présélectionne le résultat n'échantillonne pas
    une population : il illustre une conclusion.*

    **Ici, chaque dossier est classé par `neq_retenu` — la décision du moteur —
    et l'échantillon prend N de CHAQUE famille.** *Un cas par famille dit plus
    que trois cas de la même.*

    ⚠️ **Par `id` croissant à l'intérieur de chaque famille**, donc
    reproductible; et **non représentatif**, donc annoncé comme tel — un ordre
    de table promu en échantillon est le cas 19.
    """
    from sqlalchemy import select

    from falkye.db import get_session, refuser_si_cible_non_choisie

    code = refuser_si_cible_non_choisie()
    if code:
        return code

    from falkye.models.company import Company
    from falkye.resolution import neq_retenu
    from falkye.sources import req as req_source

    session = get_session()
    try:
        choisis: dict[str, list] = {f: [] for f in familles}
        vus = 0
        for company in session.execute(
            select(Company).where(Company.neq.is_(None)).order_by(Company.id)
            .execution_options(yield_per=200)
        ).scalars():
            if all(len(v) >= par_famille for v in choisis.values()):
                break
            vus += 1
            matches = req_source.resolve_neq_by_name(
                session, company.nom_detecte, ville=company.ville
            )
            decide = neq_retenu(matches)
            f = _famille(matches, decide)
            if f in choisis and len(choisis[f]) < par_famille:
                choisis[f].append((company, decide))
    finally:
        session.close()

    total = sum(len(v) for v in choisis.values())
    print("=" * 78)
    print("ÉCHANTILLON PAR FAMILLE D'ÉCHEC — classées par `neq_retenu`")
    print("=" * 78)
    print(f"\n   dossiers examinés pour remplir l'échantillon : {vus}")
    for f in familles:
        manque = "" if len(choisis[f]) >= par_famille else "   ⚠️ INCOMPLET"
        print(f"      {f:<16} {len(choisis[f])}/{par_famille}{manque}")
    print("\n   ⚠️ Par id croissant DANS chaque famille : reproductible, et NON")
    print("      représentatif. Un ordre de table promu en échantillon est le")
    print("      cas 19 — ces cas montrent un MÉCANISME, jamais une proportion.")
    for f in familles:
        if not choisis[f]:
            print(f"\n   ⚠️ Famille « {f} » : AUCUN dossier trouvé dans les {vus} examinés.")
            print("      Ce n'est pas zéro dans la population — c'est zéro dans ce")
            print("      qui a été parcouru. Relancer avec --par-famille plus bas,")
            print("      ou accepter que cette famille soit rare en tête de table.")
    if not total:
        return 1

    for f in familles:
        for i, (company, decide) in enumerate(choisis[f], start=1):
            print("\n" + "#" * 78)
            print(f"# FAMILLE « {f} » — cas {i}/{len(choisis[f])} — dossier #{company.id}")
            print("#" * 78)
            argv = ["--nom", company.nom_detecte,
                    "--forme-stockee", company.nom_detecte_normalise or ""]
            # ⚠️ **LE JUMEAU EXACT, CHERCHÉ MÊME QUAND LE MOTEUR ÉCHOUE.**
            #
            # *C'est la question qui compte* (Alexandre, 2026-09-17) : un dossier
            # classé « trop faible » dont le nom est LITTÉRALEMENT au registre —
            # le bon candidat était-il ABSENT du lot présenté au scoreur, ou
            # PRÉSENT et mal scoré? **Les deux verdicts s'appellent « trop
            # faible » et n'ont pas la même cause.**
            #
            # Sans ce `--neq`, l'étape 5 se saute et la question reste ouverte.
            argv += ["--famille-selection", f]
            attendu = decide or _jumeau_exact(company.nom_detecte_normalise)
            if attendu:
                argv += ["--neq", attendu]
            if company.ville:
                argv += ["--ville", company.ville]
            main(argv)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--nom", help="le nom détecté, tel que la source l'a livré")
    parser.add_argument(
        "--par-famille", type=int, default=0, metavar="N",
        help="tracer N dossiers de CHAQUE famille d'échec — résoluble, ambigu, "
             "trop faible, aucun candidat — classées par la décision du moteur",
    )
    parser.add_argument(
        "--familles", default=",".join(FAMILLES),
        help=f"les familles à échantillonner, séparées par des virgules ({', '.join(FAMILLES)})",
    )
    parser.add_argument("--attendu", default=None,
                        help="le nom du miroir qu'on s'attend à voir apparier")
    parser.add_argument("--neq", default=None, help="le NEQ attendu, si on le connaît")
    parser.add_argument("--ville", default=None, help="la ville du dossier (bonus de +5)")
    parser.add_argument(
        "--famille-selection", default=None, metavar="FAMILLE",
        help="la famille d'où ce cas vient (posée par --par-famille) — sert à dire "
             "POURQUOI un jumeau exact est introuvable plutôt que de se taire",
    )
    parser.add_argument(
        "--forme-stockee", default=None, metavar="FORME",
        help="la colonne `nom_detecte_normalise` du dossier, pour la comparer à la "
             "forme RECALCULÉE (posée automatiquement par --depuis-la-base)",
    )
    args = parser.parse_args(argv)
    if not args.nom and not args.par_famille:
        parser.error("donner --nom, ou --par-famille N")

    if args.par_famille:
        demandees = tuple(f.strip() for f in args.familles.split(",") if f.strip())
        inconnues = [f for f in demandees if f not in FAMILLES]
        if inconnues:
            parser.error(f"famille(s) inconnue(s) : {inconnues}. Connues : {list(FAMILLES)}")
        return _tracer_depuis_la_base(args.par_famille, demandees)

    try:
        from rapidfuzz import fuzz, process
        from sqlalchemy import func, select, text

        from falkye.db import get_session
        from falkye.models.req_entry import REQEntry
        from falkye.sources.column_mapping import normaliser
        from falkye.models.company import Company
        from falkye.resolution import (
            SEUIL_AMBIGUITE_ECART_MIN,
            SEUIL_RESOLUTION_CONFIANTE,
            neq_retenu,
        )
        from falkye.sources.req import candidats_par_nom, resolve_neq_by_name
    except ImportError as exc:  # pragma: no cover - dépend de l'environnement
        print(f"Import impossible ({exc}). Lancer depuis la racine du dépôt.", file=sys.stderr)
        return 2

    # LA CIBLE, ANNONCÉE ET EXIGÉE — juste avant d'ouvrir, jamais après
    # `parse_args` : un mode qui ne touche aucune base ne doit pas être
    # refusé. Sans ce refus, le repli CRÉE `./data/*.sqlite3` dans le
    # répertoire courant et le verdict porte sur une base vide.
    from falkye.db import refuser_si_cible_non_choisie

    code = refuser_si_cible_non_choisie()
    if code:
        return code

    session = get_session()
    # LE PIÈGE DES DEUX BASES, posé une fois pour tout l'outil. La session porte
    # deux moteurs et aucun n'est le défaut : une requête ORM trouve le sien par
    # métadonnée, un `text()` n'en a aucune et lève `UnboundExecutionError`. Le
    # demander explicitement plutôt que de compter sur une connexion déjà ouverte
    # par une requête précédente — ça marche par ACCIDENT D'ORDRE, et un
    # réarrangement innocent le casse.
    miroir = session.connection(bind_arguments={"mapper": REQEntry.__mapper__})
    try:
        print("=" * 78)
        print("UN APPARIEMENT, EN ENTIER")
        print("=" * 78)
        print("\nPORTÉE : lecture seule, miroir local, UN seul nom.")
        print("         Ce qui est montré vaut pour CE cas, et pour lui seul.")

        # --- 1. la normalisation -----------------------------------------
        print("\n" + "-" * 78)
        print("1. LA REQUÊTE, NORMALISÉE")
        print("-" * 78)
        nom_norm = normaliser(args.nom)
        print(f"\n   détecté brut   : {apercu(args.nom)}")

        # --- LES DEUX FORMES, CÔTE À CÔTE -----------------------------------
        # ⚠️ **« La forme normalisée » est ambiguë, et l'ambiguïté se lève ici.**
        # Il y en a DEUX, produites par la même fonction à des moments
        # différents :
        #
        #   RECALCULÉE — `normaliser(nom)`, maintenant. C'est ce que la
        #       résolution contre le REQ compare (`resolve_neq_by_name` reçoit
        #       le nom brut et le normalise à chaque appel).
        #   STOCKÉE — `Company.nom_detecte_normalise`, écrite le jour de la
        #       création du dossier, par le normaliseur de CE jour-là. C'est ce
        #       que `_find_unresolved_company` et le dédoublonnage comparent.
        #
        # *Une colonne dérivée est une photo, pas un miroir* — et `normaliser` a
        # changé le 15 septembre 2026.
        if args.forme_stockee is not None:
            print(f"\n   forme RECALCULÉE : {apercu(nom_norm)}")
            print(f"   forme STOCKÉE    : {apercu(args.forme_stockee)}")
            if args.forme_stockee != nom_norm:
                print("\n   ⛔ LES DEUX DIFFÈRENT.")
                print("      La colonne stockée est périmée pour ce dossier.")
                print("      Conséquence : `_find_unresolved_company` et le")
                print("      dédoublonnage cherchent une chaîne que la résolution")
                print("      ne produit plus. ⚠️ Mais ça n'explique PAS un échec de")
                print("      résolution contre le REQ : ce chemin-là ne lit jamais")
                print("      la colonne stockée, des deux côtés.")
            else:
                print("   ✅ identiques — la colonne stockée est à jour pour ce dossier.")
        print(f"   normalisé      : {apercu(nom_norm)}   ({len(nom_norm)} car.)")
        if args.attendu:
            attendu_norm = normaliser(args.attendu)
            print(f"\n   attendu brut   : {apercu(args.attendu)}")
            print(f"   normalisé      : {apercu(attendu_norm)}   ({len(attendu_norm)} car.)")
            print(f"   les deux formes normalisées sont ÉGALES : {nom_norm == attendu_norm}")
            print(f"   WRatio(norm, norm) = {fuzz.WRatio(nom_norm, attendu_norm):.1f}")
        else:
            attendu_norm = None

        # --- 2. la requête réellement émise -------------------------------
        print("\n" + "-" * 78)
        print("2. LE SQL RÉELLEMENT ÉMIS")
        print("-" * 78)
        prefixe = nom_norm.split(" ")[0]
        print(f"\n   préfixe extrait : {apercu(prefixe)}")
        requete_prefixe = (
            select(REQEntry).where(REQEntry.nom_normalise.op("GLOB")(f"{prefixe}*")).limit(2000)
        )
        requete_repli = (
            select(REQEntry).where(REQEntry.nom_normalise.contains(nom_norm[:6])).limit(2000)
        )
        print(f"\n   PRÉFIXE :\n      {sql_emis(requete_prefixe)}")
        print(f"\n   REPLI (si le préfixe ne rend rien) :\n      {sql_emis(requete_repli)}")

        # --- 3. le plan d'exécution ---------------------------------------
        print("\n" + "-" * 78)
        print("3. LE PLAN D'EXÉCUTION — un SEARCH et un SCAN ne rendent pas le même lot")
        print("-" * 78)
        try:
            plan = miroir.execute(
                text(f"EXPLAIN QUERY PLAN {sql_emis(requete_prefixe)}")
            ).all()
            for ligne in plan:
                print(f"   {ligne[-1]}")
        except Exception as exc:  # noqa: BLE001 - un moteur non SQLite n'a pas ce plan
            print(f"   (plan indisponible : {type(exc).__name__} — moteur non SQLite?)")

        # --- 4. les candidats, tels que le moteur les récupère -------------
        print("\n" + "-" * 78)
        print("4. LES CANDIDATS RÉCUPÉRÉS — par la fonction DU MOTEUR")
        print("-" * 78)
        candidats = candidats_par_nom(session, nom_norm)
        n_prefixe = len(session.execute(requete_prefixe).scalars().all())
        print(f"\n   le préfixe seul rend    : {n_prefixe} ligne(s)")
        print(f"   candidats_par_nom rend  : {len(candidats)} ligne(s)")

        # --- LA BORNE COUPE-T-ELLE, ET DE COMBIEN ? -------------------------
        # ⚠️ **C'est la borne DE 2000, celle de `candidats_par_nom` contre le
        # MIROIR** — à ne pas confondre avec `LIMITE_CANDIDATS = 500`, qui borne
        # le dédoublonnage entre `Company`. *Deux bornes, deux tables, deux
        # chemins* : celle-ci décide ce qui est comparé au registre, l'autre
        # décide ce qui est comparé aux autres dossiers.
        prefixe = nom_norm.split(" ")[0]
        sans_borne = session.execute(
            select(func.count()).select_from(REQEntry)
            .where(REQEntry.nom_normalise.op("GLOB")(f"{prefixe}*"))
        ).scalar() or 0
        print("\n   ⚠️ LA RÈGLE QUI EXTRAIT LE PRÉFIXE, ET CE QU'ELLE DONNE ICI")
        print("      `prefix = nom_norm.split(\" \")[0]` — LE PREMIER MOT, rien d'autre.")
        print(f"      nom normalisé  : {apercu(nom_norm, 52)}")
        print(f"      → préfixe      : {prefixe!r}   ({len(prefixe)} caractères)")
        if prefixe.isdigit():
            print("      Ce préfixe est NUMÉRIQUE : quasi unique, donc la récupération")
            print("      est presque parfaite. ⚠️ *Les trois premiers cas tracés étaient")
            print("      tous de cette forme, et ils ne disent rien des noms ordinaires.*")
        elif len(prefixe) <= 4:
            print("      ⚠️ Préfixe TRÈS COURT : il retiendra un très grand nombre de")
            print("         lignes, et la borne tranchera une tranche alphabétique.")
        print(f"\n   ⚠️ LA BORNE — préfixe {prefixe!r}")
        print(f"      lignes AVANT la borne   : {sans_borne}")
        print(f"      borne de candidats_par_nom : {BORNE_MOTEUR}")
        if sans_borne > BORNE_MOTEUR:
            print(f"      ⛔ LA BORNE COUPE : {sans_borne - BORNE_MOTEUR} ligne(s) écartées,")
            print("         et le LIMIT n'a d'ordre que depuis le 2026-09-16 —")
            print("         avant, la tranche changeait d'une exécution à l'autre.")
        else:
            print("      ✅ la borne ne coupe pas : tous les candidats du préfixe sont là.")
            print("         Si le bon candidat manque, ce n'est PAS la borne.")
        if n_prefixe == 0:
            print("\n   ⛔ LE PRÉFIXE N'A RIEN RENDU — le repli par SOUS-CHAÎNE a servi.")
            print("      *Documenté comme coûtant 98 % du budget de résolution pour")
            print("      14 % des appels* : ce chemin-ci est celui qui coûte cher, et")
            print("      il n'a aucun index — le balayage est dans la nature de la")
            print("      requête, pas dans le plan.")
        else:
            print(f"\n   ✅ Le préfixe a rendu {n_prefixe} ligne(s) : le repli n'a PAS servi.")
        print()
        for i, c in enumerate(candidats[:DETAIL_MAX], start=1):
            stocke = c.nom_normalise
            print(f"   {i:>3}. neq={c.neq}")
            print(f"        nom            = {apercu(c.nom)}")
            print(f"        nom_normalise  = {apercu(stocke)}   ({len(stocke or '')} car.)")
        if len(candidats) > DETAIL_MAX:
            print(f"\n   … {len(candidats) - DETAIL_MAX} candidat(s) de plus, non détaillés.")

        # Le type SQLite de la colonne, sur ces lignes : un BLOB n'est JAMAIS
        # apparié par GLOB, et se relit en octets côté Python.
        if candidats:
            neqs = [c.neq for c in candidats[:DETAIL_MAX]]
            marques = ",".join(f"'{n}'" for n in neqs)
            try:
                types = miroir.execute(text(
                    f"SELECT typeof(nom_normalise) AS t, count(*) FROM req_entries "
                    f"WHERE neq IN ({marques}) GROUP BY t"
                )).all()
                print("\n   typeof(nom_normalise) sur ces lignes :")
                for t_, n in types:
                    print(f"      {str(t_):<10} {n}")
            except Exception as exc:  # noqa: BLE001
                print(f"   (typeof indisponible : {type(exc).__name__})")

        # --- 5. LA LIGNE ATTENDUE EST-ELLE DEDANS ? ------------------------
        print("\n" + "-" * 78)
        print("5. LA LIGNE ATTENDUE — dans le lot, ou introuvable ?")
        print("-" * 78)
        if not (args.attendu or args.neq):
            # ⚠️ **TROIS SILENCES DIFFÉRENTS SOUS LE MÊME MESSAGE**, et le
            # distinguer a coûté un aller-retour le 2026-09-17. *« Aucun --neq
            # donné » se lisait comme « on ne l'a pas demandé »* alors que la
            # recherche avait bien eu lieu et n'avait rien trouvé.
            if args.famille_selection:
                print(f"\n   ⚠️ JUMEAU EXACT CHERCHÉ, ET INTROUVABLE.")
                print("      La forme normalisée du dossier n'existe à l'identique")
                print("      NI dans `req_entries` NI dans `req_noms`.")
                if args.famille_selection == "trop_faible":
                    print("\n      **Et c'est ATTENDU pour cette famille.** Un dossier")
                    print("      « trop faible » l'est parce que son nom DIFFÈRE de celui")
                    print("      du registre — s'il était identique, il scorerait 100.")
                    print("      *Le jumeau exact ne peut donc presque jamais servir ici :")
                    print("      c'est l'étape 7 qui répond, en montrant si le bon candidat")
                    print("      a été PRÉSENTÉ au scoreur et avec quel score.*")
            else:
                print("\n   (aucun --attendu ni --neq donné, et aucune famille : "
                      "étape sautée)")
        else:
            dans_le_lot = [
                c for c in candidats
                if (args.neq and c.neq == args.neq)
                or (args.attendu and (c.nom or "") == args.attendu)
                or (attendu_norm and (c.nom_normalise or "") == attendu_norm)
            ]
            if dans_le_lot:
                print(f"\n   ✅ ELLE EST DANS LE LOT ({len(dans_le_lot)} ligne(s)).")
                print("      → si son score est bas, le MUR EST DANS LE SCORE.")
                for c in dans_le_lot:
                    print(f"\n      neq={c.neq}")
                    print(f"      nom            = {apercu(c.nom)}")
                    print(f"      nom_normalise  = {apercu(c.nom_normalise)}")
                    print(f"      WRatio(requête_norm, nom_normalise) = "
                          f"{fuzz.WRatio(nom_norm, c.nom_normalise or ''):.1f}")
            else:
                print("\n   ⛔ ELLE N'EST PAS DANS LE LOT.")
                print("      → le mur est dans la RÉCUPÉRATION, pas dans le score.")
                print("\n   Quatre recherches directes, pour distinguer « absente du miroir »")
                print("   de « présente mais non récupérée » — deux correctifs opposés :")
                recherches = []
                if args.neq:
                    recherches.append(("par NEQ exact", select(REQEntry).where(REQEntry.neq == args.neq)))
                if args.attendu:
                    recherches.append(("par nom BRUT exact",
                                       select(REQEntry).where(REQEntry.nom == args.attendu)))
                    recherches.append(("par nom brut, sous-chaîne",
                                       select(REQEntry).where(
                                           REQEntry.nom.contains(args.attendu[:12])).limit(10)))
                if attendu_norm:
                    recherches.append(("par nom_normalise exact",
                                       select(REQEntry).where(
                                           REQEntry.nom_normalise == attendu_norm)))
                for libelle, requete in recherches:
                    lignes = session.execute(requete.limit(10)).scalars().all()
                    print(f"\n      {libelle} : {len(lignes)} ligne(s)")
                    for c in lignes[:5]:
                        print(f"         neq={c.neq}  nom={apercu(c.nom, 44)}")
                        print(f"         nom_normalise={apercu(c.nom_normalise, 44)}"
                              f"  ({len(c.nom_normalise or '')} car.)")
                        commence = (c.nom_normalise or "").startswith(prefixe)
                        print(f"         commence par {prefixe!r} : {commence}"
                              + ("" if commence else "   ⚠️ LE GLOB NE PEUT PAS LA TROUVER"))

                # Combien de lignes du miroir commencent par ce préfixe, en SQL pur.
                try:
                    n_glob = miroir.execute(text(
                        "SELECT count(*) FROM req_entries WHERE nom_normalise GLOB :m"
                    ), {"m": f"{prefixe}*"}).scalar()
                    n_like = miroir.execute(text(
                        "SELECT count(*) FROM req_entries WHERE nom LIKE :m"
                    ), {"m": f"{prefixe}%"}).scalar()
                    print(f"\n      lignes dont nom_normalise GLOB '{prefixe}*' : {n_glob}")
                    print(f"      lignes dont nom       LIKE '{prefixe}%'      : {n_like}")
                    if n_like and n_glob is not None and n_glob < n_like:
                        print(f"      ⚠️ ÉCART DE {n_like - n_glob} : le nom BRUT commence par")
                        print("         le préfixe, la colonne normalisée non. La récupération")
                        print("         ne voit pas des lignes qui sont pourtant là.")
                except Exception as exc:  # noqa: BLE001
                    print(f"      (comptes indisponibles : {type(exc).__name__})")

        # --- 6. ce qui est passé au scoreur --------------------------------
        print("\n" + "-" * 78)
        print("6. CE QUI EST PASSÉ AU SCOREUR — le dictionnaire tel quel")
        print("-" * 78)
        choix = {c.neq: c.nom_normalise for c in candidats}
        print(f"\n   process.extract(")
        print(f"       query   = {apercu(nom_norm)},")
        print(f"       choices = {{  # {len(choix)} entrée(s)")
        for neq, valeur in list(choix.items())[:DETAIL_MAX]:
            print(f"           {neq!r}: {apercu(valeur, 46)},")
        if len(choix) > DETAIL_MAX:
            print(f"           …  {len(choix) - DETAIL_MAX} de plus")
        print("       },")
        print("       scorer  = fuzz.WRatio, limit = 5)")
        classement = process.extract(nom_norm, choix, scorer=fuzz.WRatio, limit=5)
        print("\n   → rendu :")
        for valeur, score, cle in classement:
            print(f"        {score:>6.2f}   neq={cle}   valeur={apercu(valeur, 44)}")
        if not classement:
            print("        (aucun)")

        # --- 7. le score rendu par le moteur, à côté du recalculé ----------
        print("\n" + "-" * 78)
        print("7. LE SCORE DU MOTEUR, ET LE MÊME RECALCULÉ")
        print("-" * 78)
        matches = resolve_neq_by_name(session, args.nom, ville=args.ville)
        if not matches:
            print("\n   le moteur ne rend AUCUN candidat scoré.")
        else:
            for m in matches:
                recalcul = fuzz.WRatio(nom_norm, m.entry.nom_normalise or "")
                ecart = "   ← ÉCART" if abs(recalcul - m.score) > 0.05 else ""
                print(f"\n   score rendu {m.score:>6.2f}   neq={m.entry.neq}")
                print(f"      nom affiché    = {apercu(m.entry.nom, 46)}")
                print(f"      nom_normalise  = {apercu(m.entry.nom_normalise, 46)}")
                print(f"      recalcul WRatio(requête_norm, nom_normalise) = {recalcul:.2f}{ecart}")
            if args.ville:
                print(f"\n   ⚠️ --ville {args.ville!r} donné : un bonus de +5 a pu s'appliquer,")
                print("      ce qui explique un écart de exactement 5 points avec le recalcul.")

        # --- 8. LA DÉCISION, ET CE QUE LA PRODUCTION EN FAIT ----------------
        # ⚠️ **L'étape qui manquait, et son absence a produit une
        # contradiction** *(relevée par Alexandre, 2026-09-17)* : trois dossiers
        # scoraient 100 contre un seuil de 92 et restaient sans NEQ. *La trace
        # s'arrêtait au score et annonçait « la fonction DU MOTEUR » — ce qui
        # était vrai de la RÉCUPÉRATION et faux de la DÉCISION.*
        print("\n" + "-" * 78)
        print("8. LA DÉCISION DU MOTEUR — `neq_retenu`, la fonction du produit")
        print("-" * 78)
        neq_decide = neq_retenu(matches)
        top = matches[0].score if matches else 0.0
        second = matches[1].score if len(matches) > 1 else 0.0
        print(f"\n   seuil de confiance       : {SEUIL_RESOLUTION_CONFIANTE:.0f}")
        print(f"   écart minimal au second  : {SEUIL_AMBIGUITE_ECART_MIN:.0f}")
        print(f"   top {top:.2f}, second {second:.2f}, écart {top - second:.2f}")
        if neq_decide is None:
            if not matches:
                print("\n   ⛔ AUCUN CANDIDAT RÉCUPÉRÉ.")
            elif top < SEUIL_RESOLUTION_CONFIANTE:
                print("\n   ⛔ TROP FAIBLE — le meilleur candidat n'atteint pas le seuil.")
            else:
                print("\n   ⛔ AMBIGU — assez sûr, pas assez détaché du second.")
        else:
            print(f"\n   ✅ NEQ RETENU : {neq_decide}")
            occupant = session.execute(
                select(Company).where(Company.neq == neq_decide)
            ).scalar_one_or_none()
            print("\n" + "   " + "=" * 72)
            print("   ⚠️ ET POURTANT CE DOSSIER EST SANS NEQ. Les deux sont vrais.")
            print("   " + "=" * 72)
            print("""
   Ce que `resolve_company` fait d'un NEQ retenu :

       company = SELECT Company WHERE neq = <retenu>
       if company is None: company = Company(neq=…)   ← un NOUVEAU dossier
       company.statut_resolution = RESOLU

   ⚠️ **Il ne répare JAMAIS le dossier non résolu qu'on trace.** Il écrit
      dans un dossier CLÉ PAR NEQ — celui qui existe, ou un neuf. Le dossier
      sans NEQ reste sans NEQ, indéfiniment.

   Et rien ne le réessaie : `generer_notifications` n'appelle jamais
   `resolve_company` (N36). **Un dossier qui a échoué une fois n'est plus
   jamais interrogé, quoi qu'il arrive au miroir ensuite.**

   Donc un score de 100 aujourd'hui ne contredit pas l'absence de NEQ :
   il dit que la résolution ÉCHOUAIT le jour de la création du dossier,
   et que personne n'a redemandé depuis. **Ce n'est pas un mur
   d'appariement — c'est le cercle.**
""")
            if occupant is not None:
                print(f"   ⚠️ Et le NEQ {neq_decide} est DÉJÀ PORTÉ par #{occupant.id}")
                print(f"      « {occupant.nom_detecte} » — donc même une passe de reprise")
                print("      ne pourrait pas le poser ici : c'est le cas « conservation ».")
            else:
                print(f"   Le NEQ {neq_decide} n'est porté par aucun dossier :")
                print("      une passe de reprise le poserait sans conflit.")

        print("\n" + "=" * 78)
        print("   Rien n'a été écrit. Ce cas dit où est le mur POUR LUI, et rien")
        print("   de plus — l'étendre demande de le rejouer sur la population.")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
