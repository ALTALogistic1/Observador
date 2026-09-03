# FALKYE — Repéreur d'entreprises en croissance (Phase 2)

Système qui surveille en continu des signaux publics de croissance d'entreprises
(appels d'offres décrochés, financement, recrutement, changements corporatifs) et
notifie l'utilisateur des prospects probables — voir
`docs/spec/repereur-entreprises-croissance-specs.md` pour les spécifications
complètes et `docs/spec/README-demarrage.md` pour les consignes de démarrage.

**Phase 1 atteinte** (2026-09-01) : pipeline validé de bout en bout avec de
vraies notifications (311, dont l'exemple Sigma-RH) sur 8 sources actives —
voir `docs/STATUT_RESEAU.md` pour le détail complet de la validation.

**Phase 2 en cours** : ajout des sources gratuites restantes du registre, une
à la fois (spec section 8), avec priorité aux sources qui élargissent la
couverture pancanadienne (objectif produit : tout le Canada, pas seulement le
Québec). 15 sources actives à ce jour (état au 2026-09-01, voir `falkye
registry sources`) — les 8 de la Phase 1 (**SEAO** et **contrats fédéraux**
pour les appels d'offres, **Corporations Canada** [registre corporatif
pancanadien], **EIMT positive** [recrutement, avec nom d'employeur],
**subventions fédérales** et **Investissement Québec** [financement], **REQ**
+ **RDPRM** [registre corporatif/financement, activées via import manuel —
voir plus bas ; le téléchargement automatisé du REQ est bloqué par une règle
Cloudflare visant les IP infonuagiques partagées, pas un problème de méthode
d'accès — voir `docs/STATUT_RESEAU.md`]) plus sept sources de Phase 2 :
**Deloitte Technology Fast 50** et **Globe and Mail Top Growing Companies**
(classements de croissance), **Guichet-Emplois**, réactivée via le nom
d'employeur des pages de détail d'offre individuelle (couverture
volontairement partielle), **permis de construction — Ville de Laval**
(couverture volontairement partielle : le champ disponible identifie
l'entrepreneur qui exécute les travaux, pas le propriétaire qui s'agrandit),
**contrats publics attribués — Nouvelle-Écosse**, première source hors
Québec pour les appels d'offres, et **licences d'affaires — Vancouver et
Toronto**, premières sources hors Québec pour le registre corporatif : une
licence n'est un signal que si elle représente un vrai nouvel établissement
(pas un renouvellement, détecté par un miroir local persistant partagé entre
les deux villes) ET correspond avec confiance à une corporation fédérale
déjà existante (vérification croisée avec Corporations Canada) — voir
`docs/STATUT_RESEAU.md`. **Growth 500** (canadianbusiness.com) est
abandonné : bloqué par un vrai anti-bot Cloudflare, et le classement
lui-même n'est plus activement republié (confirmé). Équivalents provinciaux
à SEAO/REQ évalués (7 candidats appels d'offres, 5 candidats registres
d'entreprises) : la Nouvelle-Écosse est le seul équivalent SEAO automatisable
trouvé ; **aucune province n'offre d'équivalent REQ automatisable et
gratuit** — Corporations Canada reste le seul registre pancanadien en vrac
(limite connue : fédéral seulement) — voir `docs/STATUT_RESEAU.md` pour le
détail de chaque investigation. **Permis de construction — Montréal et
Québec** restent `à développer` : aucune des deux villes n'inclut de nom
d'entreprise/demandeur dans ses données ouvertes — voir
`docs/STATUT_RESEAU.md` pour le détail complet de chaque investigation. Voir
`docs/ARCHITECTURE.md` pour le détail.

### Import manuel (RDPRM, REQ)

Deux formes du même mécanisme générique (spec section 9) : vous obtenez le
document/fichier vous-même sur le site de la source, puis l'importez — il
entre alors dans le même pipeline qu'une source automatisée (résolution NEQ,
vérifications, score, corroboration).

**Un document = une entreprise** (ex. RDPRM, payant à l'unité — 11 $/nom) :

```bash
python -m falkye.cli import-manuel lien --source-id rdprm   # lien direct vers la recherche RDPRM

python -m falkye.cli import-manuel ajouter \
  --source-id rdprm --entreprise "Nom légal exact (REQ)" \
  --valeur 75000 --nature-bien "équipement de production" \
  --date-evenement 2026-08-15 --institution "Nom de l'institution créancière"
```

**Un fichier complet = potentiellement des milliers d'entreprises** (ex. REQ,
mis à jour deux fois par mois — tâche récurrente légère) :

```bash
python -m falkye.cli import-manuel lien --source-id req   # lien direct vers le fichier en vrac

python -m falkye.cli import-manuel fichier \
  --source-id req --chemin ~/Téléchargements/registre-entreprises.zip
```

Le vrai fichier REQ est un `.zip` de 6 CSV liés entre eux (`Entreprise.csv`,
`Nom.csv`, `Etablissements.csv` + 3 non utilisés pour l'instant), pas un
fichier plat — schéma confirmé et jointure implémentée et validée avec de
vraies données le 2026-08-31 (voir `docs/STATUT_RESEAU.md`). Pour inspecter
la structure d'un fichier avant import (utile pour une future source à
structure similaire) : `import-manuel inspecter --source-id req --chemin <fichier>`.

## Installation

```bash
python3 -m venv .venv && source .venv/bin/activate   # optionnel mais recommandé
pip install -e ".[dev]"
cp .env.example .env   # puis remplir SMTP_* pour le canal courriel
```

## Démarrage

Le produit est générique — n'importe quel type d'utilisateur configure un profil
de la même façon (spec section 9, "Polyvalence d'utilisation" — pas seulement un
fournisseur de service B2B : chambres de commerce, développement économique
régional, etc., voir plus bas). Deux exemples pour l'illustrer :

```bash
python -m falkye.cli init-db                     # crée les tables + sphères de base

# Exemple 1 : consultant en implantation de systèmes de gestion d'inventaire
python -m falkye.cli profile create \
  --courriel vous@exemple.com --nom "Profil A" \
  --ville Montréal --region Montréal --etat-province Québec \
  --rayon-km 100 --sensibilite-confiance eleve --sensibilite-pertinence moyen
python -m falkye.cli profile add-need \
  --profile-id 1 --sphere-id gestion_inventaire_actifs \
  --usage "Implantation de systèmes de gestion d'inventaire et d'actifs" \
  --mots-cles "implantation,gestion d'inventaire,ERP,WMS"

# Exemple 2 : courtier en assurance commerciale — même mécanique, autre sphère
python -m falkye.cli profile create \
  --courriel autre@exemple.com --nom "Profil B" \
  --ville Québec --region "Capitale-Nationale" --etat-province Québec \
  --rayon-km 75 --sensibilite-confiance moyen --sensibilite-pertinence moyen
python -m falkye.cli profile add-need \
  --profile-id 2 --sphere-id assurance_gestion_risques \
  --usage "Courtage en assurance commerciale PME" \
  --mots-cles "assurance responsabilité,gestion des risques"

python -m falkye.cli registry sources             # état du registre de sources
python -m falkye.cli registry canaux               # état du registre de canaux

python -m falkye.cli scan ponctuel --profile-id 1  # recherche ponctuelle (spec section 5), fenêtre 60 jours par défaut
python -m falkye.cli scan ponctuel --profile-id 1 --historique-complet  # fenêtre illimitée (peut être long, ex. SEAO)
python -m falkye.cli scan veille                    # veille continue, tous les profils
python -m falkye.cli notifications list
python -m falkye.cli resume envoyer --profile-id 1 --jours 7
```

## Plans tarifaires et paiement (spec section 9bis)

Trois plans — **Écho** (gratuit, sources ouvertes uniquement), **Radar** (Écho +
sources payantes choisies par nous, paiement intégré Stripe), **Radar+** (Radar +
clés API de l'utilisateur — mécanisme de gestion de clés délibérément différé,
voir `docs/ARCHITECTURE.md`). Un seul portail sous-jacent : chaque source porte un
`plan_minimum` dans le registre (`falkye registry sources`), appliqué par le
moteur au moment de générer les notifications, pas à l'ingestion.

```bash
python -m falkye.cli billing radar-checkout --profile-id 1   # URL de la session Stripe Checkout
python -m falkye.cli billing statut --profile-id 1           # plan effectif + état de l'abonnement Stripe
python -m falkye.cli billing traiter-webhook --fichier evenement.json  # applique un événement Stripe obtenu hors ligne
python -m falkye.cli billing definir-plan --profile-id 1 --plan radar  # bascule manuelle (tests, sans Stripe réel)
```

Première source construite contre le plan Radar : l'agrégateur de recrutement
tiers (`agregateur_recrutement_tiers` dans le registre — fournisseur TheirStack
confirmé). **Non validé contre un vrai appel ni un vrai compte Stripe** dans cet
environnement de développement — voir `docs/STATUT_RESEAU.md`.

## Tableau de bord et statut de suivi (spec section 4bis, Radar/Radar+ seulement)

```bash
python -m falkye.cli dashboard voir --profile-id 1     # cartes de dossiers (refuse un profil Écho)
python -m falkye.cli dashboard statuts                  # statuts de suivi disponibles
python -m falkye.cli dashboard statut --notification-id 42 --statut pas_pertinent
```

Marquer une notification "Pas pertinent" déclenche automatiquement la rétroaction
de pertinence (spec section 6) — réduit légèrement le poids de la sphère
correspondante pour les prochaines notifications de ce profil, jamais en dessous
d'un plancher. Voir `docs/ARCHITECTURE.md` pour le détail.

### Trois fonctionnalités transversales additionnelles

```bash
python -m falkye.cli dashboard modele --notification-id 42       # amorce de message de premier contact
python -m falkye.cli dashboard voir --profile-id 1 --employes-min 20 --employes-max 99  # filtre par taille estimée
python -m falkye.cli dashboard carte --profile-id 1 --sortie carte.html  # carte HTML autonome (Leaflet)
```

La carte géographique géocode les entreprises pas encore résolues (Nominatim/
OpenStreetMap, gratuit) — **non validé contre un vrai appel** dans cet
environnement de développement, voir `docs/STATUT_RESEAU.md`.

### Profils de recherche multiples simultanés (multi-usage × multi-territoire)

```bash
# Un compte Radar+ gère plusieurs combinaisons sphère/usage × territoire sous UN
# SEUL profil, plutôt qu'un profil par combinaison :
python -m falkye.cli profile add-need --profile-id 1 --sphere-id rh_recrutement_dotation \
  --usage "Recrutement spécialisé" --territoire Québec
python -m falkye.cli profile add-need --profile-id 1 --sphere-id rh_recrutement_dotation \
  --usage "Recrutement spécialisé" --territoire Ontario

python -m falkye.cli dashboard voir --profile-id 1 --usage "Recrutement" --territoire Québec
python -m falkye.cli dashboard synthese --profile-id 1 --jours 90       # vue agrégée par secteur/territoire
python -m falkye.cli dashboard synthese --profile-id 1 --secteur-detail # + libellés REQ bruts derrière le regroupement
```

### Authentification réelle par utilisateur (mot de passe + session)

```bash
# Bootstrap (mode opérateur — un principal ne peut pas prouver son identité
# avant d'avoir un premier mot de passe) :
FALKYE_OPERATOR=1 python -m falkye.cli auth definir-mot-de-passe --profile-id 1

# Ensuite, en libre-service — jeton écrit dans ~/.falkye/session :
python -m falkye.cli auth login --courriel alex@exemple.com
python -m falkye.cli auth whoami
python -m falkye.cli auth changer-mot-de-passe
python -m falkye.cli auth logout
```

Les commandes "portail" ci-dessous dérivent désormais leur identité de la
session active plutôt que d'un `--profile-id`/`--sous-compte-id` brut — voir
`docs/ARCHITECTURE.md`, section "Authentification réelle par utilisateur",
pour le détail complet (portée, mode opérateur `FALKYE_OPERATOR=1`, limites
honnêtes qui restent).

### Fonctionnalités Radar+ professionnelles

```bash
python -m falkye.cli profile set-webhook --url https://exemple.com/hook        # accès API/webhook complet
python -m falkye.cli ponderation presets                                       # alertes composites disponibles
python -m falkye.cli ponderation appliquer --preset alerte_financement_precoce
python -m falkye.cli souscompte create --courriel analyste@exemple.com \
  --nom "Analyste régional" --role analyste --territoire "Capitale-Nationale"  # sous-comptes et territoires
python -m falkye.cli dashboard voir                                            # dossiers de la session active
```

### Intégration CRM (HubSpot, Pipedrive — Radar ET Radar+)

```bash
python -m falkye.cli crm fournisseurs                 # cartes de source (domaine/type + avantage concret)
python -m falkye.cli crm connecter --profile-id 1 --provider hubspot --jeton pat-xxxxx
python -m falkye.cli crm mapper-statut --profile-id 1 --provider hubspot \
  --statut pas_pertinent --valeur-crm "Fermé perdu"   # correspondance statut ↔ étape CRM, une à la fois
python -m falkye.cli crm statut --profile-id 1        # état de synchronisation (fiches poussées, étape connue)
```

Les fonctionnalités Radar+ ci-dessus sont réservées au plan Radar+
(`PlanTarifaire.RADAR_PLUS`) — l'intégration CRM fait exception (disponible
dès Radar). Dans tous les cas, un profil sous le plan requis peut préparer sa
configuration à l'avance, elle prend simplement effet une fois le plan
basculé. Voir `docs/ARCHITECTURE.md` pour le détail complet.

**Sur les sous-comptes/rôles** : structure de répartition de volume entre
collègues d'une même organisation (ex. distribuer les bonnes notifications
selon le territoire assigné). **CORRIGÉ le 2026-09-02** : l'identité derrière
ces rôles est désormais VÉRIFIÉE par mot de passe + session
(`falkye/auth.py`), plus un `--sous-compte-id` déclaratif — voir
`docs/ARCHITECTURE.md` pour le détail complet, y compris les deux limites
honnêtes qui restent (le mode opérateur, et le fait qu'un mot de passe
partagé reste indétectable, comme pour tout système par mot de passe).

## Tests

```bash
pytest -q
```

Les tests couvrent la logique pure (scoring, vérifications, correspondance,
résolution) sans appel réseau. La validation de bout en bout avec les vraies
sources se fait manuellement via la CLI, une fois l'accès réseau aux portails
de données ouvertes confirmé pour l'environnement d'exécution — voir
`docs/STATUT_RESEAU.md` pour le détail de chaque source validée.

## Structure du projet

```
falkye/
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

## Choix techniques

Ces choix appartiennent à l'implémentation (pas à la spec produit) et peuvent
évoluer sans redemander d'arbitrage produit :

- **Python 3.11+**, SQLAlchemy 2.0, SQLite par défaut (`FALKYE_DB_URL` pour
  passer à PostgreSQL plus tard — le code ORM ne présume pas du moteur).
- Pas d'outil de migration de schéma pour l'instant (`init_db()` fait un
  `create_all` simple) — à introduire (Alembic) avant tout usage multi-utilisateur.
- CLI (`click`) comme interface pour l'instant ; une API REST pourra être ajoutée
  au-dessus des mêmes fonctions (`falkye.engine`, `falkye.summary`) sans
  toucher au moteur, pour une future interface web/mobile (spec section 6,
  "ergonomie web puis mobile").
