# Observador — Repéreur d'entreprises en croissance (Phase 1)

Système qui surveille en continu des signaux publics de croissance d'entreprises
(appels d'offres décrochés, financement, recrutement, changements corporatifs) et
notifie l'utilisateur des prospects probables — voir
`docs/spec/repereur-entreprises-croissance-specs.md` pour les spécifications
complètes et `docs/spec/README-demarrage.md` pour les consignes de démarrage.

**Phase 1** (en cours) : chemin complet de bout en bout avec 4 sources — **SEAO**
(appels d'offres), **RDPRM** (financement, en attente — voir plus bas), **REQ**
(registre corporatif + pivot de résolution NEQ), **Guichet-Emplois** (recrutement).
Objectif : valider tout le pipeline, pas la couverture complète. Voir
`docs/ARCHITECTURE.md` pour le détail et `docs/STATUT_RESEAU.md` pour l'état des
accès réseau et les découvertes faites en construisant cette phase.

## Installation

```bash
python3 -m venv .venv && source .venv/bin/activate   # optionnel mais recommandé
pip install -e ".[dev]"
cp .env.example .env   # puis remplir SMTP_* pour le canal courriel
```

## Démarrage

Le produit est générique — n'importe quel fournisseur de service B2B configure un
profil de la même façon (spec section 9, "Polyvalence d'utilisation"). Deux
exemples pour l'illustrer :

```bash
python -m observador.cli init-db                     # crée les tables + sphères de base

# Exemple 1 : consultant en implantation de systèmes de gestion d'inventaire
python -m observador.cli profile create \
  --courriel vous@exemple.com --nom "Profil A" \
  --ville Montréal --region Montréal --etat-province Québec \
  --rayon-km 100 --sensibilite eleve
python -m observador.cli profile add-need \
  --profile-id 1 --sphere-id gestion_inventaire_actifs \
  --service "Implantation de systèmes de gestion d'inventaire et d'actifs" \
  --mots-cles "implantation,gestion d'inventaire,ERP,WMS"

# Exemple 2 : courtier en assurance commerciale — même mécanique, autre sphère
python -m observador.cli profile create \
  --courriel autre@exemple.com --nom "Profil B" \
  --ville Québec --region "Capitale-Nationale" --etat-province Québec \
  --rayon-km 75 --sensibilite moyen
python -m observador.cli profile add-need \
  --profile-id 2 --sphere-id assurance_gestion_risques \
  --service "Courtage en assurance commerciale PME" \
  --mots-cles "assurance responsabilité,gestion des risques"

python -m observador.cli registry sources             # état du registre de sources
python -m observador.cli registry canaux               # état du registre de canaux

python -m observador.cli scan ponctuel --profile-id 1  # recherche ponctuelle (spec section 5)
python -m observador.cli scan veille                    # veille continue, tous les profils
python -m observador.cli notifications list
python -m observador.cli resume envoyer --profile-id 1 --jours 7
```

## Tests

```bash
pytest -q
```

Les tests couvrent la logique pure (scoring, vérifications, correspondance,
résolution) sans appel réseau. La validation de bout en bout avec les vraies
sources (SEAO validé ; REQ et Guichet-Emplois en cours — voir
`docs/STATUT_RESEAU.md`) se fait manuellement via la CLI, une fois l'accès réseau
aux portails de données ouvertes confirmé pour l'environnement d'exécution.

## Structure du projet

```
observador/
  registry/          Registres YAML (sources, types de signaux, sphères, canaux)
                      + loader.py générique — voir docs/ARCHITECTURE.md
  models/             Schéma SQLAlchemy (Profile, Company, Signal, Notification, ...)
  sources/            Connecteurs (un module par source, interface commune base.py)
  notifications/      Canaux de notification (email actif, sms/whatsapp/webhook stubs)
  db.py               Connexion DB, init, seed
  resolution.py        Résolution NEQ (pivot, spec section 9)
  verification.py       Vérifications de base obligatoires (spec section 6)
  scoring.py             Score de confiance unifié (spec section 6)
  matching.py             Correspondance signal -> sphère + mots-clés profil
  enrichment.py            Enrichissement web (spec section 10)
  engine.py                 Orchestrateur du pipeline complet
  summary.py                 Résumé périodique (spec section 5)
  cli.py                      Interface en ligne de commande
tests/                Tests unitaires (logique pure)
docs/                 ARCHITECTURE.md, STATUT_RESEAU.md
```

## Choix techniques (Phase 1)

Ces choix appartiennent à l'implémentation (pas à la spec produit) et peuvent
évoluer sans redemander d'arbitrage produit :

- **Python 3.11+**, SQLAlchemy 2.0, SQLite par défaut (`OBSERVADOR_DB_URL` pour
  passer à PostgreSQL plus tard — le code ORM ne présume pas du moteur).
- Pas d'outil de migration de schéma pour l'instant (`init_db()` fait un
  `create_all` simple) — à introduire (Alembic) avant tout usage multi-utilisateur.
- CLI (`click`) comme interface pour la Phase 1 ; une API REST pourra être ajoutée
  au-dessus des mêmes fonctions (`observador.engine`, `observador.summary`) sans
  toucher au moteur, pour une future interface web/mobile (spec section 6,
  "ergonomie web puis mobile").
