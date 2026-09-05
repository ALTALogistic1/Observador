"""Sonde de persistance — chantier 29.

Deux rôles, choisis SEULS selon l'état de la cible :

  **Batterie complète** (cible vide) — éprouve `sqlalchemy-libsql` sur les
  usages réels du projet, contre le schéma réel complet (33 tables). Détruit et
  recrée le schéma : c'est le prix d'un test de DDL honnête.

  **Vérification en lecture seule** (cible peuplée) — joint la base, compte
  l'état durable, ne touche à rien. C'est le test d'acceptation du chantier 29 :
  conteneur recyclé, puis reprise qui retrouve l'état sans intervention.

⚠️ **La batterie complète ne peut PAS tourner sur une base distante peuplée.**
Elle commence par un `drop_all`. Le verrou est absolu et sans échappatoire :
l'état de diff perdu perd des signaux DÉFINITIVEMENT (voir
falkye/models/etat_diff_source.py), et un « je sais ce que je fais » tapé à
23 h n'est pas un mécanisme de sécurité. Pour repartir de zéro au distant, il
faut vider la base délibérément, ailleurs qu'ici.

Cible choisie par `FALKYE_DB_URL`, résolue par `falkye.db` — la sonde ne
duplique PAS la logique de connexion, elle éprouve celle du produit :

  Sans FALKYE_DB_URL  : fichier libSQL LOCAL — valide la couche dialecte seule.
  `libsql://…` + FALKYE_DB_AUTH_TOKEN : base DISTANTE — valide en plus le
                        transport HTTPS, l'authentification et le débit.

Usage (dépendances hors du projet, volontairement — la sonde précède la
décision d'ajouter sqlalchemy-libsql aux dépendances) :

    python -m venv /tmp/sonde && /tmp/sonde/bin/pip install "SQLAlchemy>=2.0" sqlalchemy-libsql
    PYTHONPATH=. /tmp/sonde/bin/python outils/sonde_persistance.py

`SONDE_N` règle le nombre de lignes du test d'insertion en lot (défaut 5000).

Résultat du 2026-09-04, mode LOCAL : 6/6.
Résultat du 2026-09-04, mode DISTANT (us-east-1) : 6/6 sur la correction.

  Trois mesures qui comptent plus que le 6/6 :
  - latence d'un aller-retour HTTPS : 86 ms;
  - `executemany` = UN aller-retour PAR LIGNE -> 12 lignes/s, soit 60 h pour
    les 2,7 M lignes du REQ;
  - un seul INSERT multi-VALUES par lot de 5 000 -> 5 174 lignes/s, soit
    8,7 min. Lots de 500/1000/2000/5000 : 1 051/2 377/3 877/5 174 lignes/s.
  Le transport n'est pas le goulot, le regroupement l'est. Corrigé dans
  falkye/diff_engine.py::_inserer_lignes_en_lot, verrouillé par ses tests.

  Et un mur : SQLITE_MAX_VARIABLE_NUMBER = 32 766 côté distant. 5 000 lignes ×
  6 colonnes = 30 000, à 9 % du mur. D'où un budget de VARIABLES et non de
  lignes dans diff_engine.
"""
import os, time, json
from datetime import datetime, timezone

from sqlalchemy import create_engine, select, insert, func, inspect, text
from sqlalchemy.orm import Session

from falkye.db import est_base_distante, get_db_url, resoudre_cible
from falkye.models.base import Base
import falkye.models  # noqa
from falkye.models.req_entry import REQEntry
from falkye.models.etat_diff_source import EtatLigneSource
from falkye.models.company import Company, StatutLegal, StatutResolution, StatutVerification


def cible():
    """(url, connect_args, mode) — la résolution distante vient de falkye.db,
    pour que la sonde éprouve le chemin du produit et pas une copie."""
    if est_base_distante():
        url, connect_args = resoudre_cible(get_db_url())
        return url, connect_args, "DISTANT"
    return "sqlite+libsql:///" + os.path.abspath("sonde_locale.db"), {}, "LOCAL"


def compter_etat_durable(moteur):
    """{table: nb_lignes} pour les tables du schéma réellement présentes.

    UN SEUL aller-retour (UNION ALL) plutôt qu'un par table : à 86 ms l'unité,
    33 tables coûteraient trois secondes pour une question qui en vaut une."""
    presentes = sorted(set(inspect(moteur).get_table_names()) & set(Base.metadata.tables))
    if not presentes:
        return {}
    requete = " UNION ALL ".join(f"SELECT '{t}' AS t, COUNT(*) AS n FROM {t}" for t in presentes)
    with moteur.connect() as cx:
        return {t: n for t, n in cx.execute(text(requete)).all()}


resultats = []


def verdict(nom, ok, detail=""):
    resultats.append((nom, ok, detail))
    print(f"  [{'OK ' if ok else 'ÉCHEC'}] {nom}" + (f" — {detail}" if detail else ""))


def conclure(mode):
    print("\n=== VERDICT ===")
    echecs = [n for n, ok, _ in resultats if not ok]
    print(("ROUGE — " + ", ".join(echecs)) if echecs
          else f"VERT — {len(resultats)}/{len(resultats)} usages passent en mode {mode}")
    raise SystemExit(1 if echecs else 0)


url, connect_args, mode = cible()
print(f"=== SONDE — mode {mode} ===\n")
moteur = create_engine(url, connect_args=connect_args)

# --- Verrou : jamais de drop_all sur une base distante qui porte de l'état ---
if mode == "DISTANT":
    try:
        etat = compter_etat_durable(moteur)
    except Exception as e:
        print(f"  [ÉCHEC] Connexion à la base distante — {type(e).__name__}: {e}")
        raise SystemExit(1)

    peuplees = {t: n for t, n in etat.items() if n}
    if peuplees:
        print("VÉRIFICATION EN LECTURE SEULE — la base distante porte de l'état.")
        print("La batterie complète est verrouillée : elle commencerait par un drop_all.\n")
        verdict("Connexion à la base distante", True, f"{len(etat)} tables du schéma présentes")
        verdict("État durable retrouvé", True,
                ", ".join(f"{t}={n:,}" for t, n in sorted(peuplees.items(), key=lambda x: -x[1])[:8]))
        total = sum(peuplees.values())
        verdict("Reprise sans intervention", True, f"{total:,} lignes durables au total")
        conclure(mode)
    print("Base distante VIDE — la batterie complète est autorisée.\n")

# --- Batterie complète (cible vide, ou fichier local) ---

# 0. DDL : les 33 tables réelles
try:
    Base.metadata.drop_all(moteur); Base.metadata.create_all(moteur)
    verdict("DDL des 33 tables réelles", True, f"{len(Base.metadata.tables)} tables créées")
except Exception as e:
    verdict("DDL des 33 tables réelles", False, f"{type(e).__name__}: {e}"); raise SystemExit(1)

N = int(os.environ.get("SONDE_N", "5000"))
maintenant = datetime.now(timezone.utc)

# 1. Insertion Core en LOT — le chemin de diff_engine.py (REQ : 2,7 M lignes).
#    Forme multi-VALUES, celle que diff_engine emploie désormais : c'est elle
#    qu'il faut mesurer, pas l'executemany qu'on vient d'abandonner.
try:
    lignes = [{"source_id": "sonde", "cle_naturelle": f"cle-{i}", "empreinte": f"{i:064d}",
               "donnees_normalisees": {"nom": f"entreprise {i}", "ville": "Montréal"},
               "premiere_apparition": maintenant, "derniere_observation": maintenant} for i in range(N)]
    from falkye.diff_engine import BUDGET_VARIABLES_INSERTION
    par_lot = max(1, BUDGET_VARIABLES_INSERTION // 6)
    t0 = time.time()
    with moteur.begin() as cx:
        for d in range(0, N, par_lot):
            cx.execute(insert(EtatLigneSource).values(lignes[d:d + par_lot]))
    dt = time.time() - t0
    with Session(moteur) as s:
        n = s.execute(select(func.count(EtatLigneSource.id))).scalar_one()
    debit = N / dt if dt else 0
    verdict("Insertion Core en lot (multi-VALUES)", n == N,
            f"{n:,} lignes en {dt:.2f}s — {debit:,.0f} lignes/s — "
            f"extrapolé 2,7 M : {2_700_000/debit/60:.1f} min")
except Exception as e:
    verdict("Insertion Core en lot (multi-VALUES)", False, f"{type(e).__name__}: {e}")

# 2. GLOB — falkye/sources/req.py:928, le chemin critique de résolution NEQ
try:
    with Session(moteur) as s:
        s.add_all([REQEntry(neq=f"11{i:08d}", nom=f"Transport Bourassa {i}",
                            nom_normalise=f"transport bourassa {i}", statut="IMMATRICULEE",
                            first_seen_at=maintenant, last_seen_at=maintenant) for i in range(200)])
        s.add_all([REQEntry(neq=f"22{i:08d}", nom=f"Alimentation Nord {i}",
                            nom_normalise=f"alimentation nord {i}", statut="IMMATRICULEE",
                            first_seen_at=maintenant, last_seen_at=maintenant) for i in range(200)])
        s.commit()
        trouves = s.execute(
            select(REQEntry).where(REQEntry.nom_normalise.op("GLOB")("transport*")).limit(2000)
        ).scalars().all()
        # le repli par sous-chaîne du même bloc
        repli = s.execute(
            select(REQEntry).where(REQEntry.nom_normalise.contains("alimen")).limit(2000)
        ).scalars().all()
    verdict("GLOB (op) + repli .contains()", len(trouves) == 200 and len(repli) == 200,
            f"GLOB {len(trouves)}/200, contains {len(repli)}/200")
except Exception as e:
    verdict("GLOB (op) + repli .contains()", False, f"{type(e).__name__}: {e}")

# 3. Colonnes JSON — aller-retour, dict imbriqué et accents
try:
    with Session(moteur) as s:
        ligne = s.execute(select(EtatLigneSource).where(EtatLigneSource.cle_naturelle == "cle-42")).scalar_one()
        d = ligne.donnees_normalisees
        ok = isinstance(d, dict) and d.get("ville") == "Montréal" and d.get("nom") == "entreprise 42"
    verdict("Colonnes JSON (aller-retour)", ok, f"relu {json.dumps(d, ensure_ascii=False)}")
except Exception as e:
    verdict("Colonnes JSON (aller-retour)", False, f"{type(e).__name__}: {e}")

# 4. Colonnes Enum — écriture, relecture, ET filtre sur la valeur
try:
    with Session(moteur) as s:
        s.add(Company(nom_detecte="Sonde Inc", nom_detecte_normalise="sonde inc",
                      statut_legal=StatutLegal.IMMATRICULEE,
                      statut_resolution=StatutResolution.RESOLU,
                      statut_verification=list(StatutVerification)[0],
                      first_detected_at=maintenant, updated_at=maintenant))
        s.commit()
        c = s.execute(select(Company).where(Company.statut_legal == StatutLegal.IMMATRICULEE)).scalar_one()
        ok = c.statut_legal is StatutLegal.IMMATRICULEE and c.statut_resolution is StatutResolution.RESOLU
    verdict("Colonnes Enum (écriture + filtre)", ok, f"{c.statut_legal.name}/{c.statut_resolution.name}")
except Exception as e:
    verdict("Colonnes Enum (écriture + filtre)", False, f"{type(e).__name__}: {e}")

# 5. func.lower / ilike — auth.py:119 et assistance_client_cible_ia.py:97
try:
    with Session(moteur) as s:
        a = s.execute(select(func.count(REQEntry.neq)).where(
            func.lower(REQEntry.nom) == "transport bourassa 7")).scalar_one()
        b = s.execute(select(func.count(REQEntry.neq)).where(
            REQEntry.nom.ilike("Transport Bourassa 7"))).scalar_one()
    verdict("func.lower() + .ilike()", a == 1 and b == 1, f"lower={a}, ilike={b}")
except Exception as e:
    verdict("func.lower() + .ilike()", False, f"{type(e).__name__}: {e}")

conclure(mode)
