"""Sonde de persistance — chantier 29.

Éprouve `sqlalchemy-libsql` sur les QUATRE usages réels du projet, contre le
schéma réel complet (33 tables), avant tout engagement de migration.

  Sans FALKYE_DB_URL  : fichier libSQL LOCAL — valide la couche dialecte.
  Avec FALKYE_DB_URL
   + FALKYE_DB_AUTH_TOKEN : base Turso DISTANTE — valide en plus le transport
                            HTTPS, l'authentification et le débit d'écriture.

Résultat du 2026-09-04, mode LOCAL : 6/6.
Résultat du 2026-09-04, mode DISTANT (Turso, us-east-1) : 6/6 sur la correction.

  Trois mesures qui comptent plus que le 6/6 :
  - latence d'un aller-retour HTTPS : 86 ms;
  - `executemany` (ce que fait le test 1) = UN aller-retour PAR LIGNE
    -> 12 lignes/s, soit 60 h pour les 2,7 M lignes de REQ;
  - un seul INSERT multi-VALUES par lot de 5 000 -> 5 174 lignes/s,
    soit 8,7 min pour 2,7 M. Lots de 500/1000/2000/5000 mesurés :
    1 051 / 2 377 / 3 877 / 5 174 lignes/s — le débit monte encore à 5 000.

  Donc le transport n'est pas le goulot : le regroupement l'est. Toute
  écriture en masse vers le distant doit passer par `.values(liste)` et non
  par `execute(insert(T), liste)`.

Usage (dépendances hors du projet, volontairement — la sonde précède la
décision d'ajouter sqlalchemy-libsql aux dépendances) :

    python -m venv /tmp/sonde && /tmp/sonde/bin/pip install "SQLAlchemy>=2.0" sqlalchemy-libsql
    PYTHONPATH=. /tmp/sonde/bin/python outils/sonde_persistance.py

`SONDE_N` règle le nombre de lignes du test d'insertion en lot (défaut 5000).
Se réutilise tel quel pour vérifier la connexion après un recyclage de
conteneur — le test d'acceptation du chantier 29.
"""
import os, sys, time, json
from datetime import datetime, timezone
from sqlalchemy import create_engine, select, insert, func
from sqlalchemy.orm import Session

from falkye.models.base import Base
import falkye.models  # noqa
from falkye.models.req_entry import REQEntry
from falkye.models.etat_diff_source import EtatLigneSource
from falkye.models.company import Company, StatutLegal, StatutResolution, StatutVerification

def url_sqlalchemy():
    """Retourne (url, connect_args, mode).

    Le jeton NE PASSE PAS par l'URL. Mesuré le 2026-09-04 : le dialecte range
    `authToken` dans la chaîne de requête de l'URL qu'il donne à
    `libsql_experimental.connect()`, mais ce pilote ne la lit pas — sa
    signature porte `auth_token=''` en argument nommé, et le serveur répond
    401 « empty JWT token ». Le jeton doit donc voyager par `connect_args`.
    """
    brut, jeton = os.environ.get("FALKYE_DB_URL"), os.environ.get("FALKYE_DB_AUTH_TOKEN")
    if brut and brut.startswith("libsql://"):
        hote = brut.removeprefix("libsql://")
        return f"sqlite+libsql://{hote}?secure=true", {"auth_token": jeton or ""}, "DISTANT"
    return "sqlite+libsql:///" + os.path.abspath("sonde_locale.db"), {}, "LOCAL"

resultats = []
def verdict(nom, ok, detail=""):
    resultats.append((nom, ok, detail))
    print(f"  [{'OK ' if ok else 'ÉCHEC'}] {nom}" + (f" — {detail}" if detail else ""))

url, connect_args, mode = url_sqlalchemy()
print(f"=== SONDE — mode {mode} ===\n")
moteur = create_engine(url, connect_args=connect_args)

# 0. DDL : les 33 tables réelles
try:
    Base.metadata.drop_all(moteur); Base.metadata.create_all(moteur)
    verdict("DDL des 33 tables réelles", True, f"{len(Base.metadata.tables)} tables créées")
except Exception as e:
    verdict("DDL des 33 tables réelles", False, f"{type(e).__name__}: {e}"); raise SystemExit(1)

N = int(os.environ.get("SONDE_N", "5000"))
maintenant = datetime.now(timezone.utc)

# 1. Insertion Core en LOT — le chemin de diff_engine.py (REQ : 2,7 M lignes)
try:
    lignes = [{"source_id": "sonde", "cle_naturelle": f"cle-{i}", "empreinte": f"{i:064d}",
               "donnees_normalisees": {"nom": f"entreprise {i}", "ville": "Montréal"},
               "premiere_apparition": maintenant, "derniere_observation": maintenant} for i in range(N)]
    t0 = time.time()
    with moteur.begin() as cx:
        cx.execute(insert(EtatLigneSource), lignes)
    dt = time.time() - t0
    with Session(moteur) as s:
        n = s.execute(select(func.count(EtatLigneSource.id))).scalar_one()
    debit = N / dt if dt else 0
    verdict("Insertion Core en lot", n == N,
            f"{n:,} lignes en {dt:.2f}s — {debit:,.0f} lignes/s — extrapolé 2,7 M : {2_700_000/debit/60:.1f} min")
except Exception as e:
    verdict("Insertion Core en lot", False, f"{type(e).__name__}: {e}")

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

print("\n=== VERDICT ===")
echecs = [n for n, ok, _ in resultats if not ok]
print(("ROUGE — " + ", ".join(echecs)) if echecs else f"VERT — {len(resultats)}/{len(resultats)} usages passent en mode {mode}")
raise SystemExit(1 if echecs else 0)
