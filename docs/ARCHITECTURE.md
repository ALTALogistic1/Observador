# Architecture — Phase 1

Ce document explique comment le code répond à chaque exigence structurelle du
README de démarrage et de `repereur-entreprises-croissance-specs.md`.

## Import manuel de documents sources (spec section 9, ajouté le 2026-08-31)

`observador/manual_import.py` implémente le mécanisme générique demandé :
activer une source dont l'automatisation impliquerait un coût récurrent (ex.
RDPRM, payant à l'unité) sans engagement — l'utilisateur fait lui-même la
recherche ponctuelle sur le site de la source, puis l'importe.

- **Généralisé, pas codé en dur pour le RDPRM** : `importer_document_manuel(db_session,
  source_id, nom_entreprise, ...)` fonctionne pour N'IMPORTE QUELLE source du
  registre dont `methode_acces == "import_manuel"`. RDPRM en est la première
  instance, pas la seule prévue.
- **Même pipeline qu'une source automatisée** : le document importé passe par
  `resolve_company` (résolution NEQ, section 9) exactement comme un `RawSignal`
  produit par un connecteur, puis `traiter_apres_import` appelle la MÊME
  fonction que le moteur (`engine._traiter_entreprise_pour_profil`) pour les
  vérifications de base, le score et la notification — "sans distinction de
  traitement une fois à l'intérieur du pipeline" (spec).
- **Lien direct de recherche obligatoire** : `SourceDef.lien_recherche` doit
  être renseigné pour toute source active en `import_manuel` —
  `Registry.valider_calibration()` lève une erreur sinon (même mécanisme de
  garde-fou que la règle de calibration). RDPRM :
  `https://www.rdprm.gouv.qc.ca/Consultation/`.
- **Traçabilité** : chaque `Signal` porte `methode_acces` (la méthode
  RÉELLEMENT utilisée pour CE signal, capturée à l'ingestion — donnees_ouvertes,
  api, import_manuel...) et `importe_par` (courriel de la personne qui a fait
  l'import, pour un signal en import manuel) — spec : "le registre garde une
  trace de la méthode d'accès utilisée pour chaque entrée traitée de cette
  façon".
- **Calibration reste la responsabilité de l'utilisateur au moment de choisir
  quoi importer** (le code ne peut pas juger un document arbitraire) — voir
  `regle_calibration` de l'entrée `rdprm` dans `registry/sources.yaml`.

## Les "Principes directeurs" (bloc ajouté en tête de la spec le 2026-08-31)

La spec ouvre maintenant sur 9 principes directeurs, présentés comme la grille de
vérification pour toute décision future. Audit fait le jour même contre le code
déjà construit :

| # | Principe | Statut |
|---|---|---|
| 1 | Aucune donnée fictive, jamais | ✅ Aucune donnée de prospect fabriquée nulle part (voir docs/STATUT_RESEAU.md pour les limites d'exécution réelle rencontrées) |
| 2 | Toute source gratuite fait partie du produit | ✅ Les 24 sources identifiées à ce jour sont dans `sources.yaml`, y compris les 3 nouvelles de cette mise à jour |
| 3 | **Calibration non négociable** (nouveau) | ✅ Nouveau champ `regle_calibration` + `Registry.valider_calibration()` — voir section dédiée ci-dessous |
| 4 | Vérifications de base obligatoires | ✅ `verification.py` |
| 5 | Score unifié, pas de jauges parallèles | ✅ `scoring.py` |
| 6 | Polyvalence, rien codé en dur pour Alexandre | ✅ Audité et corrigé le 2026-08-31 (voir section dédiée plus bas) |
| 7 | Architecture modulaire (sources/signaux/type de profil) | ✅ Trois registres + `Profile.type_profil` |
| 8 | NEQ (ou équivalent) comme pivot | ✅ Voir "Généralisation du pivot d'identité" ci-dessous (nuance introduite par cette mise à jour) |
| 9 | Ne pas complexifier pour du non confirmé | ✅ Aucune trace de logique de déclin ou d'agrégation régionale |

### Principe de calibration (nouveau, non négociable)

Chaque `SourceDef` a maintenant un champ `regle_calibration` (`observador/registry/
loader.py`) qui documente la règle concrète distinguant un vrai signal de croissance
du bruit pour cette source précise. `Registry.valider_calibration()`, appelée par
`engine.ingest_all_active_sources` avant tout scan réel, **lève une exception** si
une source `actif` n'a pas cette règle documentée — le principe est donc appliqué
en code, pas seulement respecté par convention.

Les 3 sources actives de la Phase 1 avaient déjà leur règle implémentée avant cette
mise à jour (elle est maintenant simplement rendue visible et vérifiable dans le
registre) :
- **SEAO** : chaque "award" du fichier est déjà un contrat attribué, aucun filtrage
  de bruit nécessaire à ce niveau.
- **REQ** : seuls "nouvel établissement" et "changement d'adresse" génèrent un
  signal ; tout le reste (déclaration annuelle, correction) est exclu dans
  `req.py::_upsert_row`.
- **Guichet-Emplois** : le signal qualitatif (mots-clés dans le titre) et le signal
  volumétrique (paliers de nombre de postes) sont deux règles de calibration
  distinctes, implémentées dans `matching.py` et `scoring.py`.

Pour le RDPRM et les licences d'affaires municipales (nouvelle source), la spec
donne déjà la règle attendue mais elle n'est pas codée — ces sources restent donc
`a_developper` par construction, pas par choix : `valider_calibration()`
empêcherait de les passer à `actif` sans implémenter la règle d'abord.

### Généralisation du pivot d'identité (nuance introduite par cette mise à jour)

Le principe 8 dit maintenant "le NEQ (ou l'identifiant équivalent hors Québec)" —
avant, seul le NEQ était mentionné. Ça vient de l'ajout de Corporations Canada
(pivot : numéro de corporation fédérale, pas un NEQ) à la Phase 2.

**Décision (2026-08-31) : pas de changement de schéma maintenant.** `Company.neq`
reste tel quel pour la Phase 1 — toujours Québec (spec section 3), et toute
entreprise qui y opère, même incorporée fédéralement, doit s'immatriculer au REQ et
obtient donc un NEQ. La généralisation ne devient un besoin réel qu'à l'activation
de Corporations Canada ou d'une région hors Québec (Principe 9 : ne pas
complexifier pour un cas pas encore confirmé). Quand ce moment viendra, l'extension
prévue est additive, pas une restructuration : soit une colonne
`numero_corporation_federale` distincte sur `Company`, soit une petite table
d'identifiants externes (`CompanyExternalId(company_id, type, valeur)`) — dans les
deux cas, `resolve_company` garde le NEQ comme pivot principal pour le Québec et
n'a pas besoin d'être réécrit.

## Le principe central : tout passe par des registres, jamais par du code en dur

Trois registres YAML (`observador/registry/*.yaml`), chargés par
`observador/registry/loader.py` :

| Registre | Fichier | Gabarit (spec) |
|---|---|---|
| Sources | `sources.yaml` | section 9 |
| Types de signaux | `signal_types.yaml` | section 7 |
| Sphères de besoin | `spheres.yaml` | section 4 |
| Canaux de notification | `notification_channels.yaml` | (décision produit, même principe) |

`observador/engine.py` (le moteur) ne contient **aucune mention d'une source, d'un
type de signal ou d'un canal précis**. Il boucle sur `registry.sources_actives()`
et `registry.canaux_actifs()`, et instancie les classes concrètes via les
conventions `CONNECTOR_CLASS` / `CHANNEL_CLASS` déclarées dans chaque module de
`observador/sources/` et `observador/notifications/`. Conséquence directe : la
Phase 2 (ajouter EIMT, subventions fédérales, Investissement Québec, classements de
croissance, permis de construction, Québec emploi) consiste à :

1. Écrire un connecteur (`observador/sources/<nouvelle_source>.py`) qui implémente
   `SourceConnector.detect()`.
2. Changer `statut: a_developper` → `statut: actif` et pointer `connecteur:` vers ce
   module dans `sources.yaml`.

Rien d'autre à toucher — en particulier pas `engine.py`. C'est le test que le
README de démarrage demandait : "Si la Phase 2 demande de modifier le moteur pour
ajouter une source, c'est que l'architecture de la Phase 1 n'a pas été construite
correctement."

## Le pipeline (spec section 1 et section 10)

```
détection (connecteur) → résolution NEQ/REQ (resolution.py) →
dossier cumulatif (Company + Signal) → vérifications de base AVANT enrichissement
(verification.verifier_avant_enrichissement) → enrichissement web (enrichment.py) →
vérifications de base APRÈS enrichissement (verification.verifier_apres_enrichissement)
→ score de confiance unifié (scoring.py) → filtrage par sensibilité →
notification consolidée (engine._traiter_entreprise_pour_profil) → livraison
(notifications/*)
```

Implémenté dans `observador/engine.py::_traiter_entreprise_pour_profil`, appelée
pour chaque (Company, Profile) par `generer_notifications`, elle-même appelée par
`run_veille_continue` (mode 1) et `run_recherche_ponctuelle` (mode 2) — **même
moteur pour les deux modes**, comme l'exige la spec section 5.

## Le NEQ comme pivot (spec section 9)

`observador/models/req_entry.py` (`REQEntry`) est un miroir local du REQ,
rafraîchi par `observador/sources/req.py::ingest_snapshot`. Il sert à deux choses
indépendantes :

1. **Résolution nom → NEQ** pour SEAO, RDPRM et Guichet-Emplois (aucune des trois
   ne fournit le NEQ directement) — `resolve_neq_by_name` dans `req.py`, appelée par
   `observador/resolution.py::resolve_company` pour chaque signal brut.
2. **Signal en soi** (nouvel établissement, changement d'adresse) — en comparant
   deux rafraîchissements successifs (`_upsert_row` dans `req.py`).

Chaque `Company` (le "dossier cumulatif par entreprise", spec section 5) est
identifié par son NEQ une fois résolu ; `Company.statut_resolution` distingue
`resolu` / `ambigu` / `non_trouve` / `en_attente`, et seul `resolu` avec un statut
légal non-`radiee` peut atteindre `est_presentable() == True` (voir
`verification.py`).

## Vérifications de base obligatoires (spec section 6)

`observador/verification.py` implémente les 3 vérifications de la spec comme deux
passes (avant/après enrichissement, puisque la vérification #2 dépend du site web) :

1. Statut REQ `radiee` → `EXCLU_RADIEE`
2. Site web contredisant le signal → `EXCLU_SITE_INACTIF` (l'absence de site n'exclut
   PAS, seul un site actif contredisant le signal le fait)
3. Résolution NEQ ambiguë/non trouvée → `EXCLU_RESOLUTION_AMBIGUE`

Un `Company` qui échoue une vérification n'atteint jamais `generer_notifications`
au-delà de ce point — exclusion silencieuse, jamais un avertissement affiché
(spec section 6).

## Score de confiance unifié (spec section 6)

`observador/scoring.py::calculer_score` retourne UN SEUL score composite :

- **Base par signal** (le plus fort des signaux contributifs, pas une somme —
  évite qu'un grand nombre de signaux faibles gonfle artificiellement le score) :
  une fonction par `signal_type_id`, avec des paliers documentés et explicitement
  assumés comme choix d'implémentation (voir les commentaires dans `scoring.py` —
  la spec donne des critères qualitatifs, pas une formule).
- **Bonus de corroboration** : `+12` points par TYPE de signal indépendant
  supplémentaire (pas par signal brut), plafonné à `+30`.
- **Facteur de fraîcheur** : décroissance exponentielle (demi-vie 120 jours,
  plancher 0.15) appliquée à la contribution de chaque signal — remplace toute
  notion séparée d'urgence, comme l'exige la spec.

`franchit_seuil_sensibilite` traduit le niveau (Faible/Moyen/Élevé) en filtre selon
`Profile.sensibilite` : sensibilité "élevée" = tout est notifié (filtrage faible),
"faible" = seuls les signaux Élevé passent (filtrage agressif).

## Porte ouverte fournisseur/client (spec section 4/9)

`Profile.type_profil` existe dès la Phase 1 (`fournisseur` / `client` / `les_deux`),
tout comme `ProfileNeed.type_besoin` (`offre` / `besoin`). Le moteur
(`generer_notifications`) ne traite que `profile.besoins_fournisseur()` — un profil
`client` peut être créé et stocké sans erreur, mais aucune mise en correspondance
bidirectionnelle n'est implémentée (spec : "décision d'architecture, pas une
fonctionnalité à livrer maintenant").

## Extensibilité des sphères de besoin

`observador/models/sphere.py::Sphere` est une table DB (pas seulement le YAML),
synchronisée au démarrage (`db.seed_spheres_from_registry`). Un utilisateur qui
propose une sphère hors liste s'ajoute avec `est_personnalisee=True` sans migration.

## Polyvalence d'utilisation (spec section 9, ajoutée le 2026-08-31)

Exigence : le produit doit rester utilisable par n'importe quel fournisseur de
service B2B, pas seulement un consultant en implantation de systèmes d'inventaire.
Audit fait le 2026-08-31 sur le code déjà construit :

- **Rien dans le moteur, le scoring, la vérification ou le schéma de données** ne
  fait référence à un secteur ou un service particulier — `sphere_id` et
  `service_precis` sont traités comme des valeurs opaques partout (voir
  `matching.py`, `engine.py`, `models/profile.py`).
- **Corrigé** : `matching.MOTS_CLES_TRANSFORMATION` (la base de mots-clés
  "transformation/implantation" utilisée pour le signal qualitatif de
  recrutement, spec section 7 Signal 3) contenait deux termes propres aux
  systèmes de gestion d'inventaire ("chef de projet ERP", "chef de projet WMS" —
  WMS signifiant littéralement "Warehouse Management System"). Remplacés par des
  formulations sectoriellement neutres (modernisation, déploiement,
  réorganisation, restructuration, mise en place, "chef de projet" seul). Un
  titre de poste orienté transformation doit être un signal aussi fort pour un
  courtier d'assurance que pour un consultant en systèmes.
- **Corrigé** : les exemples dans la documentation (`README.md`) et le texte
  d'aide de la CLI (`cli.py --service`) utilisaient "implantation Hector"
  (l'exemple exact d'Alexandre en section 1 de la spec) comme SEUL exemple.
  Remplacés par des exemples neutres/multiples ; le README montre maintenant deux
  profils de nature différente (implantation de systèmes ET courtage
  d'assurance) pour rendre la polyvalence visible, pas seulement affirmée.
- **Non modifié, jugé conforme** : `scoring._score_financement_expansion` donne
  un bonus si la nature du bien mis en garantie (RDPRM) contient
  "équipement"/"inventaire"/"production". Ce n'est PAS une préférence pour la
  sphère "gestion d'inventaire" — c'est un critère de confiance sur le SIGNAL
  lui-même (équipement de production = expansion réelle plus probable qu'un
  véhicule isolé), explicitement demandé par la table de critères de la spec
  section 6, et indépendant de la sphère du profil qui reçoit la notification.
- **Non modifié, jugé conforme** : l'ordre des sphères dans `spheres.yaml` (avec
  "Gestion d'inventaire et d'actifs" en premier) suit fidèlement l'ordre de la
  liste donnée par la spec elle-même (section 4) — ce n'est pas un choix de
  priorisation du code.
- **Attribution de décisions produit** ("décision d'Alexandre" dans certains
  commentaires de `registry/*.yaml`) : conservée telle quelle — ça crédite qui a
  tranché une question budgétaire/produit (ex. statut du RDPRM), ça n'encode
  aucune hypothèse sur son secteur d'activité.

### Porte laissée ouverte : liste de surveillance par entreprise nommée

La spec (section 9) demande de ne pas fermer cette porte sans l'implémenter en
Phase 1. Vérifié : `Company`/`Signal` sont déjà créés pour TOUTE entreprise
détectée par une source active, indépendamment de toute correspondance à un
profil — le filtrage par sphère/mots-clés n'intervient qu'en aval, dans
`engine.generer_notifications`. Une future liste de surveillance nommée
(ex. table `CompanyWatch(profile_id, neq)`) pourrait déclencher une notification
pour toute nouvelle activité sur une entreprise ciblée, EN PLUS du filtrage par
profil/sphère existant, sans restructurer `Company`, `Signal`, ou le pipeline de
résolution NEQ. Non implémenté (hors scope Phase 1, comme demandé).

### Explicitement hors scope (spec section 9) — non construit

- Logique inversée de détection de déclin (repérer des entreprises en difficulté).
- Couche d'agrégation régionale (statistiques/tendances plutôt que par entreprise).

Aucune trace de ces deux cas dans le code — confirmé par l'audit du 2026-08-31.

## Canaux de notification (décision produit du 2026-08-31)

Même principe que le registre de sources. `registry/notification_channels.yaml` :
courriel actif (SMTP, `observador/notifications/email_channel.py`), SMS/WhatsApp/
webhook au statut `a_developper` (`StubChannel` — échoue explicitement plutôt que
de simuler un envoi). Activer un canal Phase 2 = configurer les variables d'env
listées dans le registre + changer son statut, sans toucher `engine.py`.
