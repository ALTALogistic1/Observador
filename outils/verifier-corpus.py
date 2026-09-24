#!/usr/bin/env python3
"""Vérificateur de cohérence du corpus FALKYE.

À lancer de n'importe où :
    python3 outils/verifier-corpus.py

⚠️ **Il trouvait le corpus par le RÉPERTOIRE COURANT jusqu'au 2026-09-24**, et
lancé d'ailleurs il rendait un vert **vide** : « 2 documents · 0 section de
charte · 0 cas », plus tous les renvois du tampon déclarés cassés. *La chaîne
d'intégration faisait `cd docs/spec` et voyait juste; une relecture à la main
depuis la racine voyait faux, et le chiffre faux a été rapporté plusieurs fois
comme un état du dépôt.* **Il trouve maintenant le corpus lui-même, et il
REFUSE plutôt que de rendre un vert quand il ne le trouve pas.**

Il ne juge pas le contenu. Il vérifie ce qui se vérifie mécaniquement :
les renvois qui pointent vers une cible inexistante, les fichiers cités
mais absents, et **deux cas du journal qui porteraient le même numéro**.
Sortie non nulle si quelque chose casse — la vérification s'exécute,
elle ne s'espère pas.

**Le contrôle des numéros de cas** a été ajouté le 2026-09-09 : la
collision s'est produite deux fois dans la même semaine, et un numéro
dupliqué ne casse pas le journal — il casse tous les renvois qui le
citent, en les rendant ambigus plutôt qu'absents. Un renvoi ambigu est
pire qu'un renvoi mort : il continue de mener quelque part.

**Ce que ce script NE VÉRIFIE PAS, et qui doit rester écrit dans sa
sortie.** Il vérifie qu'une cible EXISTE, jamais qu'elle contient encore
ce qu'on va y chercher. Le 7 septembre 2026, le contenu de la section 11
de la charte est parti au guide d'ingénierie : la section existait
toujours, vide de ce que trois renvois y cherchaient, et ce script ne les
aurait pas vus. Un déplacement de contenu passe donc sous son radar —
c'est une relecture humaine qui l'attrape, pas lui.
"""
import re, subprocess, sys, pathlib

RACINE = pathlib.Path(__file__).resolve().parents[1]

#: Rappelée sous CHAQUE passage, y compris celui qui ne trouve rien. Une
#: vérification qui ne nomme pas sa limite finit par être lue comme couvrant
#: plus qu'elle ne couvre — et celle-ci a une limite qui a déjà mordu.
LIMITE = (
    "Ce script vérifie qu'une cible EXISTE, jamais qu'elle contient encore ce\n"
    "  qu'on y cherche. Une section vidée de son contenu passe pour valide : le\n"
    "  7 septembre, trois renvois pointaient vers la section 11 de la charte,\n"
    "  partie au guide d'ingénierie, et rien ici ne les aurait vus."
)

def trouver_le_corpus() -> pathlib.Path:
    """Le répertoire du corpus — **cherché, jamais présumé.**

    ⚠️ *Un vérificateur dont la couverture dépend du répertoire d'où on
    l'appelle rend deux verdicts différents sur le même dépôt*, et le plus
    rassurant des deux est celui qui ne regarde rien.
    """
    # ⚠️ **Le répertoire courant passe EN PREMIER, et c'est délibéré.** *Un
    # appel explicite depuis une copie du corpus doit porter sur cette copie* —
    # c'est ainsi que les tests cassent le vérificateur pour vérifier qu'il
    # attrape. **Ce qui change le 2026-09-24, c'est le REPLI** : sans corpus
    # sous le pied, il va le chercher au lieu de rendre un vert vide.
    for candidat in (pathlib.Path.cwd(), RACINE / "docs" / "spec", RACINE):
        if (candidat / "charte-falkye.md").exists():
            return candidat
    return RACINE / "docs" / "spec"


CORPUS = trouver_le_corpus()
textes = {f.name: f.read_text(encoding="utf-8") for f in sorted(CORPUS.glob("*.md"))}

# ⛔ **LE REFUS.** *Un rapport vert sur un corpus introuvable est pire qu'une
# erreur : il se lit comme une vérification réussie.* **Les deux documents
# nommés ici sont ceux dont tout le reste dépend** — la charte porte les
# sections citées, le journal porte les cas cités.
MANQUANTS = [nom for nom in ("charte-falkye.md", "falkye-journal-des-cas.md")
             if nom not in textes]
if MANQUANTS:
    sys.exit(
        f"⛔ REFUS — corpus introuvable dans {CORPUS}.\n"
        f"   Manque : {', '.join(MANQUANTS)}.\n"
        "   Ce script ne rend pas un vert sur ce qu'il n'a pas lu."
    )

def cibles(nom, motif):
    return set(re.findall(motif, textes.get(nom, ""), re.M))

sections_charte = cibles("charte-falkye.md", r"^#{2,3} (\d+bis|\d+)\.")
cas_journal     = cibles("falkye-journal-des-cas.md", r"^## Cas (\d+)")
fichiers        = set(textes) | {"FALKYE-README-reprise.md"}

problemes = []

# Deux cas ne peuvent pas porter le même numéro. `cibles()` renvoie un ENSEMBLE,
# donc un doublon y est déjà écrasé — il faut relire la liste ordonnée pour le
# voir. C'est précisément pourquoi le défaut a pu passer deux fois.
numeros = re.findall(r"^## Cas (\d+)", textes.get("falkye-journal-des-cas.md", ""), re.M)
for numero in sorted({n for n in numeros if numeros.count(n) > 1}, key=int):
    problemes.append(
        f"falkye-journal-des-cas.md → cas {numero} apparaît {numeros.count(numero)} fois "
        f"(un numéro dupliqué rend AMBIGU chaque renvoi qui le cite)"
    )

for f, t in textes.items():
    for m in re.finditer(r"charte,?\s+section\s+(\d+bis|\d+)", t, re.I):
        if sections_charte and m.group(1) not in sections_charte:
            problemes.append(f"{f} → charte, section {m.group(1)} (inexistante)")
    for m in re.finditer(r"journal,?\s+cas\s+(\d+)", t, re.I):
        if cas_journal and m.group(1) not in cas_journal:
            problemes.append(f"{f} → journal, cas {m.group(1)} (inexistant)")
    for m in re.finditer(r"`([\w\-\.]+\.md)`", t):
        # Un renvoi HORS corpus est légitime — le corpus cite `README.md`,
        # `docs/DEPLOIEMENT.md`, le tampon `NOTES-A-CONSIGNER.md`. Ce qui serait
        # une faute est un renvoi vers un fichier qui n'existe NULLE PART :
        # d'où les trois emplacements connus, plutôt qu'un seul répertoire.
        # *Ajouté le 2026-09-11, sur un faux positif : le guide d'ingénierie
        # citait le tampon, qui vit à la racine et pas dans le corpus.*
        if m.group(1) not in fichiers and not any(
            (RACINE / dossier / m.group(1)).exists() for dossier in ("", "docs")
        ):
            problemes.append(f"{f} → `{m.group(1)}` (fichier introuvable, ici comme à la racine)")

vus = set()
for p in problemes:
    if p not in vus:
        print("  ✗", p)
        vus.add(p)

print(f"\n{len(textes)} documents · {len(sections_charte)} sections de charte · "
      f"{len(cas_journal)} cas · {len(vus)} renvoi(s) à corriger")
# La limite s'affiche même quand tout passe : un rapport vert qui ne dit pas ce
# qu'il ne couvre pas se lit comme une garantie qu'il n'est pas.
print(f"\n⚠️ {LIMITE}")

# --- Les notes en attente de consignation ---------------------------------
#
# **Affichage, jamais blocage — et c'est une décision, pas une facilité.**
# *(Arrêté le 2026-09-11 avec Alexandre.)* Une règle bloquante aurait eu besoin
# de reconnaître une « fin de tâche », ce qui n'est pas lisible dans l'arbre :
# il aurait fallu une déclaration, donc une sortie nommée — et toute sortie
# nommée s'utilise, jusqu'à devenir un réflexe. On aurait alors un garde-fou
# qui rassure sans couvrir, c'est-à-dire pire que rien.
#
# Ce que ça fait à la place : rendre l'oubli VISIBLE à chaque demande de
# fusion. Le tampon reste le garde-fou; ceci n'en est que le rappel.
TAMPON = RACINE / "NOTES-A-CONSIGNER.md"
if TAMPON.exists():
    texte_tampon = TAMPON.read_text(encoding="utf-8")
    # ⚠️ **DEUX ou TROIS dièses, et il faut les deux.** *Le tampon a changé de
    # niveau de titre en cours de route — N1 à N87 en `###`, N88 et suivantes en
    # `##` — et ce rappel a compté 87 notes sur 136 pendant ce temps.* **Un
    # rappel qui ne bloque jamais et qui compte faux ne rappelle rien** : il
    # affiche un chiffre plausible, ce qui est pire qu'un chiffre absent.
    titres = re.findall(r"^#{2,3} (N\d+) — (.+)$", texte_tampon, re.M)
    dates = re.findall(r"^- \*\*Notée le\*\* : (\d{4}-\d{2}-\d{2})", texte_tampon, re.M)
    if not titres:
        print("\n📝 Notes à consigner : aucune — le tampon est vide.")
    else:
        # Une note sans date se COMPTE et se SIGNALE : la sauter ferait
        # disparaître exactement ce que ce tampon existe pour retenir.
        sans_date = len(titres) - len(dates)
        plus_ancienne = min(dates) if dates else None
        ligne = f"\n📝 Notes à consigner : {len(titres)} en attente"
        if plus_ancienne:
            ligne += f", la plus ancienne du {plus_ancienne}"
        if sans_date:
            ligne += f" — ⚠️ {sans_date} sans date"
        print(ligne)
        for numero, titre in titres:
            print(f"     {numero} — {titre}")
        print("   (elles s'écrivent à la fin du POINT qu'elles concernent, dans la")
        print("    MÊME demande de fusion — voir le guide, « La clôture d'un point »)")

        # --- L'ÂGE DES DOCUMENTS DE CHANTIER ------------------------------
        #
        # ⚠️ **Le témoin que la règle du 2026-09-24 réclamait.** *Le chantier
        # 3+4 s'est arrêté au 17 septembre pendant qu'on travaillait dessus six
        # jours de plus, et rien ne le disait* — le tampon enflait d'un côté,
        # le document vieillissait de l'autre, et les deux faits ne se
        # rencontraient nulle part.
        #
        # ⛔ **PREMIÈRE FORME, ÉCARTÉE LE JOUR MÊME** : dater un document par
        # la date la plus récente qu'il ÉCRIT. *Elle rendait le 2026-10-02 sur
        # le chantier 3+4* — **l'archive du 2 octobre, une date À VENIR.** Un
        # document parle aussi du futur; ce qu'il mentionne ne le date pas.
        #
        # **La forme retenue : la dernière ÉCRITURE du fichier, par `git`.**
        # ⚠️ *Sa limite, et elle se dit* : une retouche d'une virgule compte
        # comme une mise à jour. **Le témoin dit qu'un document N'A PAS été
        # touché; il ne dit jamais qu'il a été mis à jour pour de bon.**
        plus_recente = max(dates) if dates else None
        chantiers = sorted(f for f in textes if f.startswith("falkye-chantier-"))
        if plus_recente and chantiers:
            print(f"\n📅 Dernière écriture des documents de chantier, contre la "
                  f"note la plus récente du tampon ({plus_recente}) :")
            inconnues = 0
            for nom in chantiers:
                try:
                    vue = subprocess.run(
                        ["git", "log", "-1", "--format=%cs", "--", str(CORPUS / nom)],
                        capture_output=True, text=True, cwd=RACINE, timeout=10,
                    ).stdout.strip()
                except Exception:
                    vue = ""
                if not vue:
                    inconnues += 1
                    print(f"     {'? inconnue':<14} {'—':<12} {nom}")
                    continue
                retard = "⚠️ en retard" if vue < plus_recente else "✅"
                print(f"     {retard:<14} {vue:<12} {nom}")
            if inconnues:
                print(f"     ⚠️ {inconnues} document(s) sans date : `git` n'a pas")
                print("        répondu — clone superficiel, ou pas de dépôt ici.")
                print("        UNE DATE ABSENTE N'EST PAS UNE DATE RÉCENTE.")
            print("   ⚠️ CE QUE CE TÉMOIN NE DIT PAS. « En retard » ne veut pas")
            print("      dire « faux » : un chantier à l'arrêt vieillit")
            print("      normalement. Et une retouche d'une virgule suffit à le")
            print("      rendre ✅ — il dit qu'un document n'a PAS été touché,")
            print("      jamais qu'il a été mis à jour pour de bon.")

sys.exit(1 if vus else 0)
