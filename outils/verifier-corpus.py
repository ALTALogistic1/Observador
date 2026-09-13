#!/usr/bin/env python3
"""Vérificateur de cohérence du corpus FALKYE.

À lancer depuis le répertoire qui contient les .md du corpus :
    cd docs/spec && python3 ../../outils/verifier-corpus.py

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
import re, glob, sys, pathlib

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

textes = {f: open(f, encoding="utf-8").read() for f in sorted(glob.glob("*.md"))}
if not textes:
    sys.exit("Aucun .md dans ce répertoire.")

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
    titres = re.findall(r"^### (N\d+) — (.+)$", texte_tampon, re.M)
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
        print("   (elles s'écrivent d'un coup à la fin de la tâche; ce fichier se vide alors)")

sys.exit(1 if vus else 0)
