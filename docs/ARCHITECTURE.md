# FALKYE — Architecture (Phase 2)

Ce document explique comment le code répond à chaque exigence structurelle du
README de démarrage et de `repereur-entreprises-croissance-specs.md`.

## Import manuel de documents sources (spec section 9, ajouté le 2026-08-31)

`falkye/manual_import.py` implémente le mécanisme générique demandé :
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

### Deuxième forme : import par fichier complet (REQ, ajouté le 2026-08-31)

RDPRM (un document = une entreprise) et REQ (un fichier = potentiellement des
milliers d'entreprises) sont deux SITUATIONS différentes sous le même
mécanisme générique — pas deux mécanismes séparés :

- `SourceConnector.detect_from_file(path, db_session)` (nouvelle méthode
  optionnelle sur l'interface de base, `falkye/sources/base.py`) : un
  connecteur qui sait ingérer un fichier local l'implémente. `REQConnector`
  le fait en appelant `req.ingest_snapshot(fichier_local=path)` — EXACTEMENT
  la même logique de parsing/diff/upsert que le chemin réseau automatisé
  (`REQConnector.detect`), factorisée dans `_stats_vers_signaux` pour ne
  jamais dupliquer cette mécanique entre les deux chemins.
- `manual_import.importer_fichier_source(db_session, source_id, chemin, ...)` :
  le pendant "fichier" de `importer_document_manuel` — délègue à
  `detect_from_file`, déduplique par `source_ref` (comme `engine.ingest_source`
  le ferait pour une source automatisée), puis persiste via le même
  `persist_raw_signal` factorisé (utilisé aussi par `importer_document_manuel`
  — un seul endroit qui sait transformer un `RawSignal` en `Signal`).
- **Pourquoi le REQ est passé par ce mécanisme** : le téléchargement automatisé
  échoue systématiquement (HTTP 403 Cloudflare, "utilisation excessive")
  depuis cette session — l'IP de sortie change à chaque tentative (pool
  partagé entre sessions cloud) et le blocage était déjà présent dès la toute
  première tentative, avant tout essai répété — signature d'une règle visant
  une plage IP infonuagique, pas notre volume de requêtes (une seule requête
  par exécution, jamais par entreprise). Voir `docs/STATUT_RESEAU.md` pour le
  détail complet avec preuves (horodatage + IP de sortie par tentative).
- **`Registry.sources_actives_automatisees()`** (nouveau) exclut les sources
  en `import_manuel` de la boucle que `engine.ingest_all_active_sources`
  parcourt à chaque `scan veille`/`scan ponctuel` — sans ça, le REQ tenterait
  quand même le téléchargement réseau bloqué à chaque scan malgré
  `methode_acces: import_manuel`. `registry.sources_actives()` (sans suffixe)
  continue de tout lister (utile pour `falkye registry sources`).
- Après un import REQ, `falkye import-manuel fichier --source-id req`
  retraite par défaut TOUTES les entreprises connues (pas seulement celles
  touchées par ce fichier) — un rafraîchissement du REQ peut débloquer la
  résolution NEQ d'entreprises déjà détectées par SEAO/EIMT/etc. qui étaient
  jusque-là `non_trouve`. Désactivable (`--pas-de-reprocess`) pour un gros
  import si on préfère lancer `scan veille` séparément.
- Le chemin réseau automatisé (`REQConnector.detect`) reste codé et
  fonctionnel — gardé au cas où l'accès redeviendrait praticable — mais n'est
  plus dans la boucle du moteur tant que `methode_acces: import_manuel`.

### Troisième extension : inspection d'un fichier à structure complexe (REQ, 2026-08-31)

Alexandre a inspecté le vrai ZIP téléchargé et découvert qu'il contient **six
CSV liés entre eux** (`Entreprise.csv`, `Etablissements.csv`, `Nom.csv`,
`DomaineValeur.csv`, `FusionScissions.csv`, `ContinuationsTransformations.csv`),
pas un fichier plat comme le code le supposait au départ. Plutôt que de traiter
ça comme un problème spécifique au REQ, le mécanisme générique a été étendu une
troisième fois :

- **`SourceConnector.inspect_file(path) -> dict`** (nouvelle méthode optionnelle,
  `falkye/sources/base.py`) : pour une source dont le fichier importé a une
  structure interne pas encore confirmée. Retourne, par fichier interne,
  colonnes + une ligne d'exemple — jamais tenter d'importer. Un connecteur qui
  n'en a pas besoin (structure déjà simple/confirmée) lève `NotImplementedError`.
- **`REQConnector.inspect_file`/`req.inspect_zip`** : lit en flux (sans tout
  décompresser — coûte quelques Ko même sur `Entreprise.csv`, ~630 Mo) l'en-tête
  et un exemple de chaque CSV membre du zip.
- **CLI `falkye import-manuel inspecter --source-id <id> --chemin <fichier>`**
  : appelle `inspect_file` et affiche le résultat, sans toucher à la base.
- **Garde-fou dans `_iter_csv_rows`** : un `.zip` à plusieurs CSV NON reconnu
  comme le vrai fichier REQ (`FICHIERS_REQ_REELS`) lève une `RuntimeError`
  explicite au lieu d'être traité comme un fichier plat unique — sans cette
  garde, le code initial aurait concaténé des fichiers au schéma différent,
  produisant des données mal interprétées en silence (violation directe du
  principe "aucune donnée fictive/mal interprétée, jamais").
- Généralisable : n'importe quelle source `import_manuel` future dont le fichier
  a une structure relationnelle similaire peut implémenter `inspect_file` de la
  même façon, sans toucher au moteur ni à `manual_import.py`.

### Quatrième extension : jointure multi-fichiers réelle + bornage propagé (REQ, 2026-08-31)

Une fois les vraies colonnes confirmées via l'inspecteur ci-dessus (fichier
mis en release GitHub par Alexandre, SHA-256 vérifié avant utilisation), la
vraie jointure a été écrite et validée avec de vraies données :

- **`_ingest_zip_req_reel`** (`falkye/sources/req.py`) : charge d'abord
  `Nom.csv` et `Etablissements.csv` en index mémoire NEQ→(nom|établissements)
  — bornés au nombre d'entités distinctes, pas au nombre de lignes brutes —
  puis balaie `Entreprise.csv` en flux, une seule fois, en joignant chaque
  ligne aux deux index. `ingest_snapshot` route automatiquement vers ce chemin
  quand le fichier importé contient les 3 CSV requis (`FICHIERS_REQ_REELS`).
- **`REQEtablissementEntry`** (nouveau modèle, miroir par établissement,
  clé composite NEQ + NO_SUF_ETAB) : nécessaire pour distinguer un NOUVEL
  établissement SECONDAIRE d'une entreprise déjà connue (signal fort, spec
  Signal 4) d'un simple changement d'adresse du siège (signal moyen, déjà géré
  par `REQEntry` seul) — un miroir à une seule ligne par NEQ ne peut pas faire
  cette distinction. Le signal fort ne se déclenche QUE pour un établissement
  secondaire apparu chez une entreprise DÉJÀ connue à un import précédent —
  jamais pour le tout premier établissement d'une toute nouvelle
  immatriculation (voir la correction de calibration ci-dessous).
- **Correction de calibration découverte en cours de route** : le code écrit
  avant confirmation du schéma traitait à tort toute NOUVELLE immatriculation
  comme un signal ("nouvelle immatriculation au REQ") — une entreprise qui
  vient de naître n'est pas une entreprise EN croissance (principe #3). Cette
  génération de signal a été retirée du chemin réel ; seuls "nouvel
  établissement secondaire" et "changement d'adresse du siège" restent des
  signaux, conformément à la table Signal 4 de la spec.
- **Bogue de bornage trouvé et corrigé pendant la validation** :
  `SourceConnector.detect_from_file` accepte maintenant `limit: int | None`,
  transmis jusqu'à `ingest_snapshot` — auparavant `REQConnector.
  detect_from_file` appelait `ingest_snapshot(limit=None)` sans égard au
  `--limit` demandé, puisque le chemin réel ne produit ses signaux qu'APRÈS
  avoir traité tout `Entreprise.csv` (contrairement à un générateur
  ligne-par-ligne) ; borner seulement les signaux produits (ce que fait
  `manual_import.importer_fichier_source` en filet de sécurité) ne réduisait
  donc pas le volume réellement lu. Voir `docs/STATUT_RESEAU.md` pour le
  déroulé complet de la découverte et les résultats de validation contre de
  vraies données (résolution nom/statut/adresse confirmée correcte, limite
  réelle de complétude d'adresse selon l'ancienneté du dossier).

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
| 5 | Score unifié, pas de jauges parallèles | ✅ `scoring.py` — toujours un seul score composite PAR AXE ; le score de pertinence ajouté le 2026-09-01 (`pertinence.py`) est un second axe voulu par la spec (section 6, restructurée), pas une régression du principe : chaque axe reste unifié en interne, les deux ne sont simplement jamais fusionnés entre eux (voir section dédiée plus bas) |
| 6 | Polyvalence, rien codé en dur pour Alexandre | ✅ Audité et corrigé le 2026-08-31 (voir section dédiée plus bas) |
| 7 | Architecture modulaire (sources/signaux/type de profil) | ✅ Trois registres + `Profile.type_profil` |
| 8 | NEQ (ou équivalent) comme pivot | ✅ Voir "Généralisation du pivot d'identité" ci-dessous (nuance introduite par cette mise à jour) |
| 9 | Ne pas complexifier pour du non confirmé | ✅ Aucune trace de logique de déclin ou d'agrégation régionale |

### Principe de calibration (nouveau, non négociable)

Chaque `SourceDef` a maintenant un champ `regle_calibration` (`falkye/registry/
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

Trois registres YAML (`falkye/registry/*.yaml`), chargés par
`falkye/registry/loader.py` :

| Registre | Fichier | Gabarit (spec) |
|---|---|---|
| Sources | `sources.yaml` | section 9 |
| Types de signaux | `signal_types.yaml` | section 7 |
| Sphères de besoin | `spheres.yaml` | section 4 |
| Canaux de notification | `notification_channels.yaml` | (décision produit, même principe) |

`falkye/engine.py` (le moteur) ne contient **aucune mention d'une source, d'un
type de signal ou d'un canal précis**. Il boucle sur `registry.sources_actives()`
et `registry.canaux_actifs()`, et instancie les classes concrètes via les
conventions `CONNECTOR_CLASS` / `CHANNEL_CLASS` déclarées dans chaque module de
`falkye/sources/` et `falkye/notifications/`. Conséquence directe : la
Phase 2 (ajouter EIMT, subventions fédérales, Investissement Québec, classements de
croissance, permis de construction, Québec emploi) consiste à :

1. Écrire un connecteur (`falkye/sources/<nouvelle_source>.py`) qui implémente
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
→ score de confiance (scoring.py) ET score de pertinence (pertinence.py), deux axes
indépendants → filtrage par les DEUX seuils de sensibilité (matrice, pas moyenne) →
notification consolidée (engine._traiter_entreprise_pour_profil) → livraison
(notifications/*)
```

Implémenté dans `falkye/engine.py::_traiter_entreprise_pour_profil`, appelée
pour chaque (Company, Profile) par `generer_notifications`, elle-même appelée par
`run_veille_continue` (mode 1) et `run_recherche_ponctuelle` (mode 2) — **même
moteur pour les deux modes**, comme l'exige la spec section 5.

## Le NEQ comme pivot (spec section 9)

`falkye/models/req_entry.py` (`REQEntry`) est un miroir local du REQ,
rafraîchi par `falkye/sources/req.py::ingest_snapshot`. Il sert à deux choses
indépendantes :

1. **Résolution nom → NEQ** pour SEAO, RDPRM et Guichet-Emplois (aucune des trois
   ne fournit le NEQ directement) — `resolve_neq_by_name` dans `req.py`, appelée par
   `falkye/resolution.py::resolve_company` pour chaque signal brut.
2. **Signal en soi** (nouvel établissement, changement d'adresse) — en comparant
   deux rafraîchissements successifs (`_upsert_row` dans `req.py`).

Chaque `Company` (le "dossier cumulatif par entreprise", spec section 5) est
identifié par son NEQ une fois résolu ; `Company.statut_resolution` distingue
`resolu` / `ambigu` / `non_trouve` / `en_attente`, et seul `resolu` avec un statut
légal non-`radiee` peut atteindre `est_presentable() == True` (voir
`verification.py`).

## Vérifications de base obligatoires (spec section 6)

`falkye/verification.py` implémente les 3 vérifications de la spec comme deux
passes (avant/après enrichissement, puisque la vérification #2 dépend du site web) :

1. Statut REQ `radiee` → `EXCLU_RADIEE`
2. Site web contredisant le signal → `EXCLU_SITE_INACTIF` (l'absence de site n'exclut
   PAS, seul un site actif contredisant le signal le fait)
3. Résolution NEQ ambiguë/non trouvée → `EXCLU_RESOLUTION_AMBIGUE`

Un `Company` qui échoue une vérification n'atteint jamais `generer_notifications`
au-delà de ce point — exclusion silencieuse, jamais un avertissement affiché
(spec section 6).

## Score de confiance unifié (spec section 6)

`falkye/scoring.py::calculer_score` retourne UN SEUL score composite :

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
`Profile.sensibilite_confiance` : sensibilité "élevée" = tout est notifié (filtrage
faible), "faible" = seuls les signaux Élevé passent (filtrage agressif).

## Score de pertinence (spec section 6, restructurée le 2026-09-01)

Deuxième axe, INDÉPENDANT du score de confiance ci-dessus — la confiance répond à
"ce signal est-il réel et fort", la pertinence répond à "correspond-il au profil
précis de CET utilisateur". Implémenté dans `falkye/pertinence.py`, en miroir
architectural de `scoring.py` (même principe : score numérique interne 0-100,
quantifié en palier, jamais affiché tel quel) mais avec ses propres paliers et son
propre curseur de sensibilité :

- **Paliers A / AA / AAA** ("Repéré" / "Aligné" / "Sur mesure"), pas de "non
  pertinent" — un `MatchResult` existe déjà pour qu'une notification soit
  envisagée, donc A est un plancher. `base_match` détermine le tier de base à
  partir du `MatchResult` déjà produit par `matching.py` (aucun nouveau mécanisme
  de correspondance) :
  - **AAA** si `correspondance_qualitative` (mot-clé précis du profil trouvé).
  - **AA** si la sphère du besoin utilisateur est la sphère PRINCIPALE du type de
    signal — interprétée comme la PREMIÈRE sphère listée dans `spheres_probables`
    (`registry/signal_types.yaml`), un ordre déjà cohérent avec la table de la
    spec section 7 ; voir le commentaire de `_sphere_principale` pour le détail
    de cette décision d'interprétation, la spec ne précisant pas le mécanisme.
  - **A** sinon (sphère seulement probable/secondaire pour ce type de signal).
- **Bonus signal-par-absence** (`bonus_signal_absence`, +15 pts fixe) :
  l'absence d'un signal normalement attendu plus tard peut elle-même être
  pertinente (persona investisseur providentiel : croissance visible mais
  aucun financement encore visible = traction précoce). Généralisé via un champ
  de registre plutôt que codé en dur pour ce seul persona :
  `SphereDef.signal_absence_pertinent` (`registry/spheres.yaml`) déclare, pour
  une sphère donnée, l'id du type de signal dont l'absence compte — appliqué
  seulement si l'entreprise a au moins un autre signal (sinon rien à comparer).
- **Bonus de vélocité/trajectoire** (`bonus_velocite`, jusqu'à +24 pts, +8/signal
  rapproché supplémentaire) : plusieurs signaux dans une fenêtre glissante de 60
  jours pèsent plus lourd qu'un signal isolé, même à confiance égale par signal —
  cherche la fenêtre la plus dense parmi les dates de détection, pas seulement
  l'écart min/max, pour ne pas être faussé par un signal isolé loin des autres.

`pertinence.franchit_seuil_sensibilite` filtre selon
`Profile.sensibilite_pertinence` — curseur INDÉPENDANT de
`sensibilite_confiance` (deux curseurs, spec section 6), même mécanique de
traduction niveau→seuil que côté confiance mais sur l'échelle A/AA/AAA.

**Décision matricielle, pas moyenne** (`engine.py::_traiter_entreprise_pour_profil`) :
les deux seuils de sensibilité doivent être franchis INDÉPENDAMMENT pour qu'une
notification soit envoyée — un signal peu pertinent n'est jamais montré même si sa
confiance est élevée, et vice-versa. `Notification` porte donc les deux axes en
parallèle (`score_confiance`/`niveau_confiance` et `score_pertinence`/
`niveau_pertinence`), jamais fusionnés en un seul chiffre. Les 311 notifications
historiques (antérieures à cette restructuration) ont `score_pertinence`/
`niveau_pertinence` = `NULL` — jamais de valeur inventée pour combler l'historique
(principe directeur #1) ; affiché comme "non disponible" plutôt qu'un palier.

## Détection d'expansion inter-provinciale (spec Radar+, point 7, ajoutée le 2026-09-03)

"Nouvelle capacité générale, pas liée à une seule sphère" (spec) : repère quand
une même entreprise apparaît dans les signaux de croissance de plusieurs
provinces (ex. REQ au Québec ET licences Toronto/Vancouver ET contrats
Nouvelle-Écosse), peu importe la sphère de besoin du profil qui la reçoit.

**Limite honnête, non négociable (exigence explicite d'Alexandre avant tout
code)** : aucun identifiant unique n'est partagé entre le REQ et les
registres/licences des autres provinces — le seul rapprochement possible est
PAR NOM, une heuristique imparfaite (faux positifs : deux entreprises
différentes, nom similaire ; faux négatifs : même entreprise, raison sociale
différente d'une province à l'autre). Jamais présenté comme garanti — deux
garde-fous, jamais un seul :
1. **Structurel** — le bonus de confiance qui en découle est plafonné à
   `BONUS_EXPANSION_INTERPROVINCIALE_MAX = 15` points sur 100
   (`falkye/scoring.py`), jamais assez à lui seul pour faire basculer un
   signal faible en confiance élevée.
2. **Textuel** — `justification_resumee` porte toujours un libellé
   explicitement hedgé ("présence possible en Ontario — nom similaire à 87% —
   à valider"), jamais présenté comme un fait acquis.

**D'où vient "quelle province" pour une source** : `SourceDef.province_code`
(`registry/sources.yaml`), un champ délibérément DISTINCT de `SourceDef.
region` (texte libre à granularité incohérente — "Vancouver" vs "Québec" vs
"Canada", impropre à une comparaison programmatique). Seules 4 sources le
portent aujourd'hui : `req` → `qc`, `licences_vancouver` → `bc`,
`licences_toronto` → `on`, `contrats_nouvelle_ecosse` → `ns`. Tout le reste
(fédéral, national, classements pancanadiens) reste `None` — jamais deviné,
simplement exclu du mécanisme.

**Bogue réel trouvé et corrigé en construisant cette grille** : `province_code:
on` NU (non quoté) dans le YAML était lu comme le booléen `True` par PyYAML
(YAML 1.1 traite `on`/`off`/`yes`/`no` comme des mots-clés booléens) —
`SourceDef("licences_toronto").province_code` valait `True`, pas la chaîne
`"on"`. Corrigé en quotant explicitement (`province_code: "on"`), test de
régression ajouté (`tests/test_registry.py::
test_registre_reel_a_les_quatre_sources_provinciales_attendues`).

**Le rapprochement lui-même** (`falkye/expansion_interprovinciale.py::
detecter_expansions`) : `rapidfuzz.fuzz.WRatio`, même scorer déjà utilisé dans
`falkye/resolution.py` et `falkye/sources/req.py` (un seul algorithme de
correspondance floue dans tout le projet). Seuil plancher `SEUIL_
RAPPROCHEMENT = 80` pour même enregistrer un lien candidat — plus bas que les
92 de `resolution.py::SEUIL_RESOLUTION_CONFIANTE` (ici le rapprochement se
fait par nom SEUL, entre deux registres différents, jamais confirmé par un
identifiant commun comme le NEQ, donc structurellement plus faible), mais
reste une vraie barre. Nouvelle table `LienInterprovincial`
(`falkye/models/expansion_interprovinciale.py`) — un LIEN, JAMAIS une
fusion : les deux `Company` (dossiers cumulatifs) restent distincts et
traçables, seul le rapprochement est stocké, avec son score.

Tourne en **passe par lot**, greffée sur `run_veille_continue` — APRÈS
l'ingestion mais AVANT `generer_notifications` (le bonus doit déjà exister en
base au moment où le score de chaque notification est calculé, sinon les
liens détectés pendant CE cycle n'auraient d'effet qu'au cycle suivant).
Rattrapage manuel via `falkye scan detecter-expansions` (balaye tout le
dossier cumulatif — utile après l'activation initiale ou l'ajout d'une
nouvelle source provinciale). Idempotent : ne recrée jamais un lien déjà
enregistré pour la même paire.

**Axe choisi : confiance, pas pertinence** — la pertinence répond à "est-ce
que ÇA correspond à MON profil", l'expansion inter-provinciale ne dit rien
sur le profil de l'utilisateur, elle dit "est-ce que cette entreprise est
VRAIMENT en croissance" — une preuve corroborante de plus, dans l'esprit du
bonus de corroboration multi-signaux déjà présent (`falkye/scoring.py::
BONUS_CORROBORATION_*`) mais séparé et plafonné plus bas (structurellement
plus faible, voir ci-dessus). `calculer_score` reste PUR (aucune requête DB) :
le bonus est résolu une fois par `engine.py` (`expansion_interprovinciale.py::
evaluer_pour_company`) et passé en paramètre, jamais calculé à l'intérieur de
`scoring.py`.

**Gating : RADAR minimum, jamais Écho** — décision produit d'Alexandre
(2026-09-03), PAS une contrainte de coût technique (le calcul est local,
aucun appel externe) : "un bonus qui améliore réellement la qualité d'un
résultat déjà présent est un enrichissement, et notre principe est qu'aucun
enrichissement de résultat ne reste dans Écho, peu importe son coût de
calcul." Principe potentiellement réutilisable pour de futurs enrichissements
similaires — noté ici pour référence, pas encore formalisé comme principe
directeur global tant qu'un deuxième cas réel ne le confirme pas. Le gating
vit dans `engine.py` (`if profile.plan != PlanTarifaire.ECHO`), jamais dans
`expansion_interprovinciale.py` lui-même — même principe que
`falkye/ponderation.py`/`falkye/pertinence.py`, où le module reste agnostique
du plan et l'appelant gate au moment de l'usage.

## Structure de plans tarifaires et portail de sources payantes (spec section 9bis)

Trois plans (`falkye/models/profile.py::PlanTarifaire`) — ÉCHO / RADAR / RADAR_PLUS,
strictement ordonnés (`falkye/registry/loader.py::PLANS_TARIFAIRES`) — mais **un seul
mécanisme sous-jacent**, pas trois architectures distinctes :

- Chaque `SourceDef` porte un `plan_minimum` (`registry/sources.yaml`, défaut
  `echo`) — le plan requis pour qu'un PROFIL reçoive une notification bâtie (en
  tout ou en partie) sur un signal de cette source.
- `falkye/engine.py::_traiter_entreprise_pour_profil` applique une TROISIÈME porte,
  indépendante des deux axes confiance/pertinence (spec section 6) : un signal dont
  la source exige un plan supérieur à celui du profil est ignoré pour CE profil,
  avant même le matching. Filtré à la SÉLECTION, pas à l'INGESTION : un signal
  Radar reste ingéré une seule fois dans le dossier cumulatif global (spec section
  5) et profite à TOUS les profils Radar/Radar+, pas seulement à celui qui a
  "payé" pour le déclencher — même principe que toute autre source.

**Premier cas concret construit contre cette architecture** (décision d'Alexandre,
2026-09-02, plutôt que de bâtir le portail dans l'abstrait) :
`falkye/sources/agregateur_recrutement.py` — connecteur générique par fournisseur
(interface `FournisseurAgregateur`, implémentations `TheirStackProvider` et
`ApifyActeurGeneriqueProvider`, le fournisseur actif choisi par variable
d'environnement, jamais codé en dur) pour un agrégateur tiers de recrutement
(LinkedIn/Indeed n'ont aucune API publique de recherche). Réactive le signal
recrutement au-delà de Guichet-Emplois/EIMT (spec section 7, Signal 3), au bénéfice
du persona agences de recrutement. **NON VALIDÉ contre un vrai appel** — voir
docs/STATUT_RESEAU.md pour le détail (domaines bloqués par le proxy réseau de cet
environnement, choix de fournisseur non encore tranché) ; `plan_minimum: radar`
dans le registre, statut resté `a_developper`.

**Paiement intégré (couche propre à Radar) — `falkye/billing/stripe_client.py`** :
isole tout le SDK Stripe dans un seul module, jamais importé ailleurs, pour que la
logique d'attribution de plan (`traiter_evenement_webhook`) reste testable sans
réseau. `creer_session_paiement_radar` crée une session Stripe Checkout ;
`traiter_evenement_webhook` synchronise `Subscription` (`falkye/models/
subscription.py`, l'état Stripe brut) vers `Profile.plan` (l'état effectif utilisé
par le moteur) à chaque événement. `verifier_signature_webhook` est séparée de
`traiter_evenement_webhook` pour que ce dernier reste appelable sur un événement
obtenu autrement qu'un vrai point de terminaison HTTP public (aucun des deux —
compte Stripe réel, point de terminaison déployé — n'existe encore dans cet
environnement) : `falkye billing traiter-webhook --fichier` applique un événement
JSON déjà obtenu (ex. depuis le tableau de bord Stripe) SANS vérification de
signature, en confiance explicite plutôt qu'implicite — même principe que l'import
manuel (spec section 9) appliqué à un webhook plutôt qu'à un document source.

**Radar+ (gestion de clés API utilisateur) — délibérément DIFFÉRÉ** (décision
d'Alexandre, 2026-09-02 : "peut suivre la même architecture de portail une fois la
version Radar validée... pas besoin de construire les deux en parallèle") : la
valeur `PlanTarifaire.RADAR_PLUS` et `plan_minimum: radar_plus` existent déjà au
niveau du modèle/registre (même porte ouverte que `TypeProfil` dès la Phase 1),
mais AUCUN mécanisme de stockage/gestion de clés API par profil n'est construit.
Poserait une question architecturale non triviale (sources ajoutées PAR
L'UTILISATEUR, donc potentiellement propres à un seul profil plutôt que globales au
dossier cumulatif comme toute source interne aujourd'hui) volontairement non
tranchée tant que Radar n'a pas un premier cas validé. Les trois fonctionnalités
Radar+ additionnelles introduites par la même mise à jour de spec (accès API/
webhook complet, pondération du moteur de score personnalisable par l'utilisateur,
sous-comptes/territoires avec rôles) ne sont pas non plus construites — même
report.

## Tableau de bord et statut de suivi (spec section 4bis, ajoutée le 2026-09-02)

Réservé aux plans Radar/Radar+ (`falkye/cli.py::_verifier_plan_dashboard` — même
porte que le reste du système de plans, section 9bis ci-dessus, pas un mécanisme
séparé). Une carte par notification (`falkye dashboard voir`) : pertinence,
confiance, site web, coordonnées d'enrichissement, statut de suivi.

**Coordonnées d'enrichissement, complétées plutôt qu'ajoutées** :
`falkye/enrichment.py::EnrichmentResult.coordonnees` extrayait déjà téléphone et
courriel depuis 2026-08 (utilisé pour la vérification #2, spec section 6), mais
n'étaient jamais persistés au-delà de cette vérification ponctuelle. Le tableau de
bord en avait besoin comme donnée durable — `Company.telephone` /
`Company.courriel_contact` (nouveaux champs, nullables) les capturent maintenant au
même endroit que `Company.site_web` (`engine.py::_traiter_entreprise_pour_profil`),
sans nouvelle source ni nouveau mécanisme d'extraction.

**Statuts de suivi — registre extensible, même principe que les sphères de
besoin** : `falkye/registry/statuts_suivi.yaml` (noyau curé : à_joindre [défaut],
joint, premier_appel_prometteur, pas_pertinent) chargé par `StatutSuiviDef`
(`registry/loader.py`), synchronisé vers la table `StatutSuivi`
(`db.seed_statuts_suivi_from_registry`, même mécanique que `Sphere`/
`seed_spheres_from_registry`) — un statut personnalisé (`est_personnalise=True`)
peut s'ajouter sans migration. `Notification.statut_suivi_id` porte le statut
courant ; `engine.py` attribue le statut par défaut du registre
(`registry.statut_suivi_par_defaut()`) à toute NOUVELLE notification, sans jamais
retoucher l'historique.

**Rétroaction de pertinence — "un statut 'Pas pertinent' sert une double
fonction"** (spec section 4bis, résout la question laissée en suspens le
2026-09-01) : `StatutSuiviDef.declenche_retroaction` marque, au registre plutôt
qu'en dur dans le moteur, le(s) statut(s) qui déclenchent
`falkye/retroaction.py::enregistrer_pas_pertinent`. Décision d'implémentation
documentée dans `falkye/models/retroaction_pertinence.py` : granularité SPHÈRE,
pas mot-clé — la spec dit "mots-clés/sphères" sans préciser le mécanisme, et le
mot-clé qualitatif exact qui a produit une correspondance AAA n'est aujourd'hui
capturé que dans un texte libre (`NotificationSignal.justification`), pas un champ
structuré ; l'ajouter serait une nouvelle capture de donnée, pas seulement une
couche de calcul (contrairement au score de pertinence lui-même). `poids_pour_sphere`
(0.4 à 1.0, jamais 0 — "légèrement réduire", jamais supprimer) est appliqué dans
`falkye/pertinence.py::calculer_pertinence` à la SEULE base de correspondance,
jamais aux bonus signal-par-absence/vélocité, deux mécanismes indépendants du
choix de sphère. Isolé par `(profile_id, sphere_id)` (`RetroactionPertinence`,
contrainte d'unicité) — la rétroaction d'un profil n'affecte jamais un autre.

## Trois fonctionnalités transversales additionnelles (spec section 4bis, construites le 2026-09-02)

Aucune nouvelle source, uniquement des couches de calcul/présentation par-dessus
des données déjà captées — même principe que le score de pertinence lui-même.

**Modèles de premier contact contextuels** (`falkye/premier_contact.py`,
`falkye dashboard modele`) : amorce de message générée à partir du SIGNAL
DOMINANT d'une notification (`_signal_dominant`, le plus fort selon
`falkye/scoring.py::score_signal_individuel` — même principe que le score de
confiance : le signal qui porte le message, pas une fusion de tous à la fois).
Dispatch par `signal_type_id` (`_MODELES`, même structure que
`scoring.py::_SCORERS`), chaque fonction dégradant gracieusement vers une
phrase plus générale si un champ précis manque (jamais de détail inventé,
principe directeur #1) ; un type de signal sans modèle dédié retombe sur une
phrase générique référençant seulement le nom de l'entreprise.

**Filtre par taille d'entreprise estimée** (`falkye/taille_entreprise.py`,
`dashboard voir --employes-min/--employes-max`) : proxy assumé et documenté
(la spec ne donne pas de formule) — le volume cumulé de postes ouverts/
approuvés (`Signal.valeur_associee` pour `recrutement_massif`, déjà rempli par
Guichet-Emplois et EIMT) sert d'estimation, bucketée en quatre tranches
alignées sur la classification Statistique Canada (1-4 / 5-19 / 20-99 / 100+).
Une entreprise sans AUCUN signal de recrutement n'a pas d'estimation (`None`),
jamais une tranche par défaut inventée — et ne correspond à aucun filtre borné
(un filtre n'a de sens que sur une donnée qui existe).

**Carte géographique interactive** (`falkye/geocoding.py` + `falkye/carte.py`,
`dashboard carte --sortie fichier.html`) : produit un fichier HTML AUTONOME
(Leaflet.js chargé depuis un CDN public dans le navigateur de l'UTILISATEUR
final, pas cet environnement de développement) — même philosophie que les
notifications courriel, aucun serveur web côté FALKYE. `generer_carte_html`
(`falkye/carte.py`) est de la logique PURE, testable sans réseau ni DB ; le
géocodage est fait séparément en amont par `geocoder_entreprise`, avec un cache
(`Company.latitude`/`longitude`/`geocode_tente_le`, même principe que
`site_web_vérifié_le`) pour ne jamais refaire un appel réseau inutile.

**NON VALIDÉ contre un vrai appel** : `NominatimGeocoder` (OpenStreetMap,
gratuit, sans clé — principe directeur #2 appliqué à un service de géocodage)
est construit d'après la documentation publique de l'API, jamais confirmé —
`nominatim.openstreetmap.org` est bloqué par le proxy de sortie réseau de cet
environnement (403 confirmé à la tentative de connexion), même classe de
limitation que theirstack.com/apify.com (voir docs/STATUT_RESEAU.md). Une
entreprise non géocodée est simplement absente de la carte, pas un échec de la
commande — vérifié en conditions réelles (0/311 dossiers géocodés contre la
base réelle, carte générée correctement quand même).

## Fonctionnalités Radar+ professionnelles (spec section 4bis, révisées le 2026-09-02)

"Le portail ouvert seul ne suffit pas à distinguer Radar+ comme palier
professionnel." Chacune gate son propre usage en vérifiant
`profile.plan == PlanTarifaire.RADAR_PLUS` au moment où elle sert, jamais en
empêchant le STOCKAGE de sa configuration (un profil peut préparer son
webhook/ses combinaisons de recherche avant une bascule de plan).

**Accès API/webhook complet** — `Profile.webhook_url` + `falkye/notifications/
webhook_channel.py::WebhookChannel`. Nécessitait de généraliser la résolution
de destinataire (`NotificationChannel.resoudre_destinataire`, voir section
"Canaux de notification" ci-dessus) puisque `engine.deliver_notification`
codait en dur `profile.courriel` depuis la Phase 1. `NotificationContent.
donnees_structurees` (nouveau champ, rempli par `formatter_notification` pour
TOUTE notification) porte un payload JSON structuré — entreprise, scores,
sphère, signaux contributifs — pour qu'un CRM/ERP externe n'ait pas à reparser
un texte formaté pour affichage humain.

**Alertes composites préconfigurées par cas d'usage** (`falkye/
alertes_composites.py`) — remplace, le 2026-09-02, la "pondération du moteur
de score personnalisable" d'origine (jugée trop abstraite pour un usage réel,
décision d'Alexandre). Le mécanisme sous-jacent est INCHANGÉ : `falkye/
pertinence.py::PonderationValeurs` (dataclass miroir des constantes du
module, `PONDERATION_DEFAUT` = les valeurs historiques) enfilée à travers
`base_match`/`bonus_signal_absence`/`bonus_velocite`/`calculer_pertinence`,
résolue par profil via `falkye/ponderation.py::ponderation_pour_profil` et
calculée UNE FOIS par `engine.py::_traiter_entreprise_pour_profil`.
`PonderationPersonnalisee` (une ligne par profil au plus, tous les champs
nullables) permet toujours d'ajuster un seul facteur. Seule l'EXPOSITION
change : trois presets nommés (`AlerteCompositeDef`, `ponderation appliquer
--preset`) plutôt que six leviers numériques bruts — `alerte_cautionnement`
(favorise la vélocité), `alerte_financement_precoce` (favorise le bonus
d'absence), `alerte_acquisition` (favorise la précision de sphère et la
vélocité). LIMITE HONNÊTE documentée en tête du module : les trois cas
d'usage nommés mentionnent tous "entreprise jeune", mais aucune donnée
d'âge/date de fondation n'est captée nulle part dans le pipeline (`Company.
first_detected_at` est la date où FALKYE a REPÉRÉ l'entreprise, pas sa date
de fondation réelle) — les presets approximent chaque cas d'usage avec les
seuls leviers que `pertinence.py` modélise (poids par palier, bonus
absence/vélocité), pas un vrai filtre sur l'âge.

**Profils de recherche multiples simultanés (multi-usage × multi-territoire)**
— nouveauté du 2026-09-02, spec section 4bis : "un compte Radar+ peut définir
plusieurs combinaisons sphère de besoin/usage précis × territoire... sous un
seul compte plutôt que quatre profils séparés." `ProfileNeed.territoire`
(nouveau champ, texte libre, nullable) restreint UN besoin précis à une
ville/région — NULL (défaut) préserve exactement le comportement historique
(`Profile.ville`/`region`/`rayon_km` existaient depuis la Phase 1 mais ne
filtraient déjà rien, voir plus haut ; ce champ n'introduit un vrai filtrage
géographique QUE pour un besoin qui le définit explicitement, donc aucun
changement de comportement pour un profil existant à un seul besoin).
Implémenté dans `falkye/matching.py::_territoire_ok` — comparaison simple
(insensible à la casse) à la ville OU la région de l'entreprise, PAS une
hiérarchie territoriale formelle, même principe que `SousCompte.territoire`.
`Notification.profile_need_id` (nouveau champ FK, nullable pour l'historique)
trace quelle combinaison précise a produit chaque notification, capturé à
partir du `meilleur_global` déjà calculé pour choisir la sphère
(`engine.py::_traiter_entreprise_pour_profil`) — cohérence garantie entre
`sphere_probable_id` et `profile_need_id` puisque les deux viennent du même
match. `dashboard voir --usage`/`--territoire` filtrent par cette
combinaison — distinct de `--sous-compte-id`, qui scope plutôt par le
territoire assigné AU VIEWER (deux dimensions indépendantes : quelle
combinaison a détecté le prospect, et qui a le droit de le voir).

**Tableaux de bord agrégés par territoire** (`falkye/synthese.py`,
`dashboard synthese`) — "au-delà des prospects un à un, une vue agrégée ('X
entreprises... réparties par secteur')." Compte les entreprises DISTINCTES
(pas les notifications) sur une fenêtre de temps, réparties par secteur
d'activité, niveau de pertinence, et territoire. LIMITE RÉELLE trouvée en
validant contre la base réelle (311 notifications) : `Company.
secteur_activite_libelle` est un champ TEXTE LIBRE du REQ, extrêmement
granulaire en pratique (ex. "Fabrication de charpentes en bois en usine" vs
"Fabrication de meuble de maison" comme deux secteurs distincts) — sur 311
entreprises réelles, la répartition produisait ~211 "secteurs" différents, la
plupart avec une seule entreprise chacun, rendant l'agrégation par secteur
LITTÉRAL peu utile telle quelle pour un usage de reddition de comptes réel.

**Regroupement grossier — solution intermédiaire (2026-09-02, demande
d'Alexandre).** Avant de construire, vérifié contre la base réelle si un
regroupement par les libellés les PLUS FRÉQUENTS littéralement suffirait :
NON — le top 20 des libellés exacts (sur 200 notifications avec un secteur
renseigné) ne couvre que 10,5%, presque aucun libellé ne se répétant mot pour
mot (199 valeurs distinctes sur 200). Construit à la place :
`registry/secteurs_grossiers.yaml` + `Registry.classer_secteur` — un
regroupement par MOTS-CLÉS récurrents À TRAVERS les libellés (11 catégories
larges — Fabrication/manufacture, Logiciel/TI, Construction/bâtiment,
Commerce de détail, Distribution, Alimentation, Transport/logistique,
Immobilier, Gestion/holding/conseil, R&D/sciences, Services professionnels —
première catégorie qui matche gagne, l'ordre du fichier est significatif).
Validé contre la base réelle : ~75% des 200 notifications avec secteur
renseigné trouvent une catégorie ; le reste (~25%) reste honnêtement
`SECTEUR_NON_CLASSE` ("(non classé)") plutôt que forcé dans une catégorie
approximative — DISTINCT de `SECTEUR_NON_PRECISE` ("(non précisé)", aucun
secteur capté du tout), les deux ne sont jamais confondus.
`SyntheseAgregee.par_secteur_detail` garde le libellé REQ brut (granularité
d'origine jamais perdue) pour qui veut inspecter ce qui tombe dans
"(non classé)" (`dashboard synthese --secteur-detail`).

PAS UN REMPLACEMENT DU SCIAN/NAICS — un vrai regroupement par code SCIAN
(quelques chiffres plutôt que la description texte intégrale) demanderait
une couche de normalisation contre un vrai référentiel externe, plus lourde
à construire et à valider ; noté comme amélioration future si le volume de
notifications justifie l'investissement plus tard. Le regroupement par
mots-clés est un pis-aller pragmatique construit sur les données réelles
déjà en main, pas une classification officielle.

**Sous-comptes et territoires assignés, avec rôles** — `falkye/models/
sous_compte.py::SousCompte` (profil Radar+ parent, courriel, nom, rôle
admin/analyste/lecture_seule, territoire texte libre). `dashboard voir`
scope les dossiers au territoire assigné (comparaison simple à `Company.
region`/`ville`) ; `dashboard statut` refuse un changement de statut si le
rôle est `lecture_seule`. **CORRIGÉ le 2026-09-02** (falkye/auth.py, section
suivante) : l'identité derrière ces vérifications est désormais VÉRIFIÉE
(session authentifiée), plus un `--sous-compte-id` déclaratif — voir la
section "Authentification réelle par utilisateur" ci-dessous pour le détail
complet, et falkye/models/sous_compte.py pour la limite honnête qui reste
(le mode opérateur).

## Authentification réelle par utilisateur — mot de passe + session (ajoutée le 2026-09-02)

Prérequis explicitement posé avant de vendre les rôles/sous-comptes Radar+
comme une vraie séparation (voir paragraphe précédent) : "un système
d'identité vérifiable et réel... suffisant pour que la mise en garde
documentée cesse d'être vraie." Plan discuté et validé avant le code, aux
quatre décisions suivantes.

**Portée : Profile ET SousCompte, pas seulement les sous-comptes.** Avant
cette fonctionnalité, ni l'un ni l'autre n'était vérifié — un `--profile-id`
brut dans `falkye/cli.py` suffisait à agir sur N'IMPORTE QUEL profil, pas
seulement à usurper un sous-compte. Corriger seulement les sous-comptes
aurait laissé un trou plus large grand ouvert juste à côté. `Profile.
mot_de_passe_hash` et `SousCompte.mot_de_passe_hash` (tous deux nullables —
NULL tant que personne n'a défini de mot de passe, jamais fabriqué) sont
vérifiés par le même mécanisme (`falkye/auth.py::authentifier`).

**Hachage : `hashlib.scrypt` (stdlib), pas une nouvelle dépendance.** KDF
délibérément lent (comme bcrypt/argon2), pour rendre une attaque par force
brute coûteuse même si la base fuit. Comparaison en temps constant
(`hmac.compare_digest`). Le jeton de SESSION, lui, est généré par `secrets.
token_urlsafe` (déjà à haute entropie, pas besoin d'un KDF lent) — seul son
hash SHA-256 est stocké côté serveur (`falkye/models/session_auth.py::
SessionAuth`), le jeton BRUT ne vit que dans le fichier local du principal
(`~/.falkye/session`, mode 0600, `FALKYE_SESSION_FILE` pour le déplacer).

**Mode opérateur, distinct de l'identité client.** `FALKYE_OPERATOR=1`
préserve le comportement déclaratif historique (`--profile-id`/
`--sous-compte-id` bruts, sans session) — Alexandre reste l'opérateur
technique de FALKYE, qui doit pouvoir dépanner/administrer n'importe quel
profil sans se connecter comme chacun de ses clients. Documenté comme un
choix architectural explicite dans `falkye/models/sous_compte.py`, pas une
faille oubliée : la frontière réelle protège les principaux les uns des
autres, jamais contre l'opérateur, qui a de toute façon accès à la base de
données sous-jacente par construction.

**Session obligatoire, sans repli déclaratif — hors mode opérateur.** Les
commandes "portail" (dashboard, crm, souscompte, billing sauf
`traiter-webhook`, ponderation, profile set-webhook, notifications list,
resume envoyer) exigent désormais une session active
(`falkye/cli.py::_identite_courante`) ; `--profile-id`/`--sous-compte-id`,
s'ils sont fournis hors mode opérateur, doivent correspondre EXACTEMENT à
l'identité de la session — jamais ignorés silencieusement, jamais acceptés
comme preuve d'identité alternative. C'est ce qui rend la mise en garde
documentée réellement fausse, pas seulement en théorie. `billing
definir-plan` (contourne délibérément Stripe) va plus loin : réservé au mode
opérateur SANS exception, jamais en libre-service — sinon un client pourrait
simplement se donner Radar+ gratuitement.

**`dashboard voir --sous-compte-id` reste un cas particulier, volontaire.**
Distinct des autres options : ce n'est pas une vérification d'IDENTITÉ mais
un filtre de LECTURE (`falkye/cli.py::_resoudre_scope_territoire`) — le
propriétaire ou un sous-compte admin peut prévisualiser le territoire d'un
collègue (ex. pour du support), alors qu'un sous-compte non admin reste
TOUJOURS auto-scopé à son propre territoire, sans pouvoir en demander un
autre (empêcherait sinon un sous-compte à territoire restreint d'élargir sa
propre vue en passant simplement un autre id).

**`dashboard statut` perd `--sous-compte-id`.** L'attribution du changement
(et la vérification `lecture_seule`) vient maintenant automatiquement de la
session — plus un paramètre à fournir, l'identité EST la preuve.

**CLI** : `auth login`/`logout`/`whoami`, `auth definir-mot-de-passe`
(bootstrap, mode opérateur uniquement — un principal ne peut pas prouver son
identité avant d'avoir un premier mot de passe), `auth
changer-mot-de-passe` (self-service, exige l'ancien mot de passe, agit
TOUJOURS sur sa propre identité même en mode opérateur).

**Deux limites honnêtes qui restent, documentées dans falkye/models/
sous_compte.py plutôt que glissées sous silence** : (1) le mode opérateur
lui-même, ci-dessus — la frontière ne protège jamais contre Alexandre ; (2)
l'authentification prouve QUI a exécuté une commande, pas QUI l'a
physiquement tapée — un sous-compte qui partage son mot de passe reste
indétectable, comme pour tout système par mot de passe, pas une faiblesse
propre à FALKYE.

## Intégration CRM — HubSpot, Pipedrive (Radar et Radar+, ajoutée le 2026-09-02)

Fonctionnalité retenue depuis un moment dans la liste, formellement transmise
le 2026-09-02. DISPONIBLE POUR RADAR ET RADAR+, à la différence du webhook
générique (réservé Radar+ seul, section ci-dessus) — gate au moment de
l'USAGE (`CrmProvider.resoudre_connexion`), jamais au stockage, même principe
que partout ailleurs.

**Pourquoi pas juste un nouveau NotificationChannel.** Un canal de
notification pousse un message une fois (fire-and-forget) ; un CRM exige un
UPSERT — mettre à jour la MÊME fiche à chaque nouvelle notification pour la
même entreprise, jamais un doublon à chaque cycle de veille — plus, dans
l'autre sens, la possibilité d'être sondé pour lire un changement fait côté
CRM. `falkye/notifications/crm/base.py::CrmProvider` est donc une interface
distincte de `NotificationChannel`, avec deux méthodes (`pousser`,
`tirer_statut`) plutôt qu'une (`envoyer`). Ce qui EST réutilisé tel quel :
`NotificationContent.donnees_structurees` (même payload déjà construit pour
le webhook, avec une clé `statut_suivi_id` ajoutée à cette occasion) comme
source de données, et `NotificationDelivery` (`channel_id=f"crm_{fournisseur}"`)
comme journal de tentatives — pas une table de journalisation parallèle.

**Authentification par JETON STATIQUE**, pas OAuth2 — décision d'Alexandre
(2026-09-02) : un jeton d'application privée HubSpot ou un jeton API
personnel Pipedrive, généré par le client dans SON compte et collé dans son
profil FALKYE (`falkye crm connecter`, `CrmConnection.jeton_api`), même
mécanique que `Profile.webhook_url`. Un flux OAuth2 complet exigerait une
page de callback web et un enregistrement d'application chez chaque
fournisseur — infrastructure que FALKYE n'a pas et qui n'était pas
nécessaire pour un push depuis le compte du client lui-même plutôt qu'une
appli listée sur un marketplace.

**Sens retour : sondage périodique, pas un webhook entrant.** La spec
demande une synchronisation "dans les deux sens si possible" — décision
d'Alexandre (2026-09-02) : `falkye/crm_sync.py::sonder_statuts_crm`, greffé
sur `run_veille_continue` (chaque cycle de veille sonde l'étape courante des
fiches déjà synchronisées), plutôt qu'un webhook entrant depuis le CRM.
FALKYE n'a jamais eu de composant serveur HTTP exposé publiquement en
permanence (CLI/traitement par lot uniquement, comme documenté ailleurs dans
ce fichier pour les sous-comptes) — un webhook entrant aurait été un premier
changement d'architecture disproportionné pour cette seule fonctionnalité.
Reste une amélioration possible plus tard si la latence d'un cycle de veille
s'avère insuffisante en usage réel.

**Deux tables neuves** : `falkye/models/crm_connection.py::CrmConnection`
(jeton, `identifiant_compte` optionnel, `mapping_statuts` — correspondance
statut de suivi FALKYE ↔ étape CRM, dans les deux sens — et
`champs_mappage_override`) ; `falkye/models/crm_sync_record.py::
CrmSyncRecord` (profile × company × fournisseur → `crm_object_id` connu,
condition de l'upsert, plus `dernier_statut_pousse_id`/
`dernier_stage_crm_connu` pour que le sondage ne retraite qu'un CHANGEMENT).

**JAMAIS fabriquer une correspondance** (principe directeur #1). Les étapes
de pipeline HubSpot/Pipedrive sont propres au compte de CHAQUE client — donc
`CrmConnection.mapping_statuts` est vide par défaut, rempli statut par statut
via `falkye crm mapper-statut`. Sans correspondance pour un statut donné : il
est poussé BRUT côté CRM (`falkye/notifications/crm/base.py::
valeurs_a_pousser`) plutôt que d'échouer, et une valeur lue côté CRM sans
correspondance connue est ignorée proprement par le sondage plutôt que
devinée. Même logique pour `champs_mappage` : le registre
(`registry/crm_providers.yaml`) porte un mappage par défaut {champ FALKYE →
propriété/champ CRM}, RÉALISTE pour HubSpot (propriétés personnalisées
nommées explicitement par le client, ex. `falkye_neq`) mais un simple
PLACEHOLDER pour Pipedrive : ses clés de champ personnalisé sont des
hachages opaques attribués par Pipedrive à la création du champ, impossibles
à deviner au niveau du registre — `CrmConnection.champs_mappage_override`
existe précisément pour que chaque client Pipedrive fournisse ses vraies
clés (`falkye crm connecter --mappage-override-json`).

**Rétroaction partagée, peu importe l'origine du changement de statut** —
`falkye/statut_suivi.py::appliquer_statut`, factorisé à cette occasion à
partir de la logique jusqu'ici seulement en ligne dans
`falkye/cli.py::dashboard_statut` : la même règle de rétroaction de
pertinence (spec section 4bis, `falkye/retroaction.py`) s'applique qu'un
statut "Pas pertinent" vienne d'un clic au tableau de bord ou d'un
changement lu côté CRM par `sonder_statuts_crm`.

**Cartes de source à l'étape de connexion, portail Radar/Radar+** (spec
section 9bis, ajoutée le 2026-09-02) : chaque option de source présentée au
client doit afficher DEUX éléments, jamais un nom de marque seul — le
domaine/type de la source et l'avantage concret qu'elle apporte, pour que le
client choisisse en connaissance de cause plutôt que sur la notoriété (ex.
HubSpot vs Pipedrive : la vraie distinction est la structure d'équipe et le
besoin marketing, pas le secteur d'activité). `CrmProviderDef.domaine_type`/
`avantage_concret` (`registry/crm_providers.yaml`), exposés via `falkye crm
fournisseurs` — texte exact du tableau de référence de la spec, pas une
paraphrase. Même gabarit prévu pour TheirStack et Houski une fois leurs
cartes de sélection construites dans le portail — pas ajouté à leurs
registres dans cette passe, portée limitée au travail CRM déjà en cours
(demande explicite d'Alexandre : "si ça s'insère facilement à ce stade").

**CLI** : `crm fournisseurs` (cartes de source ci-dessus), `crm connecter`
(jeton + `identifiant_compte` + mappage override optionnel), `crm
mapper-statut` (une correspondance statut ↔ étape CRM à la fois), `crm
statut` (état de synchronisation par profil). `scan veille` affiche
désormais le nombre de statuts synchronisés depuis un CRM (`ScanReport.
nb_statuts_crm_synchronises`).

**Même limite de validation que TheirStack/Stripe/géocodage** : aucun accès
réseau vers les vraies API HubSpot/Pipedrive dans cet environnement —
construit et testé contre des mocks HTTP réalistes (`tests/
test_hubspot_channel.py`, `test_pipedrive_channel.py`, via `responses`),
validation en conditions réelles à faire par Alexandre une fois qu'un jeton
réel de chaque fournisseur est disponible.

## Porte ouverte fournisseur/client (spec section 4/9)

`Profile.type_profil` existe dès la Phase 1 (`fournisseur` / `client` / `les_deux`),
tout comme `ProfileNeed.type_besoin` (`offre` / `besoin`). Le moteur
(`generer_notifications`) ne traite que `profile.besoins_fournisseur()` — un profil
`client` peut être créé et stocké sans erreur, mais aucune mise en correspondance
bidirectionnelle n'est implémentée (spec : "décision d'architecture, pas une
fonctionnalité à livrer maintenant").

## Extensibilité des sphères de besoin

`falkye/models/sphere.py::Sphere` est une table DB (pas seulement le YAML),
synchronisée au démarrage (`db.seed_spheres_from_registry`). Un utilisateur qui
propose une sphère hors liste s'ajoute avec `est_personnalisee=True` sans migration.

### Granularité du lien sphère ↔ signal (question d'Alexandre, 2026-09-02)

Le lien entre une sphère et un type de signal (`SignalTypeDef.spheres_probables`,
`registry/signal_types.yaml`) se fait au niveau du **`signal_type_id` en
entier**, jamais d'un champ précis à l'intérieur d'un signal — `financement_
acces_capital` est reliée à `financement_expansion` comme TYPE de signal, pas
à un champ comme `nature_bien` ou `programme` en particulier. C'est le même
mécanisme pour toutes les sphères, pas une exception : `matching.py::
match_profile` compare `need.sphere_id` à l'ensemble `spheres_probables(raw.
signal_type_id, registry)`, sans jamais inspecter `raw.champs`.

**Le principe "jamais une source activée en bloc, toujours champ par champ
pour réduire le bruit" existe bel et bien dans le code réel — mais à une
AUTRE couche, celle de la CALIBRATION à l'ingestion (`SourceDef.
regle_calibration`), pas celle du matching sphère.** Exemples concrets déjà en
place : `req.py::_upsert_row` ne retient QUE les changements `nouvel_
etablissement_secondaire`/`changement_adresse` parmi tous les types de mise à
jour du REQ (une déclaration annuelle ou une correction administrative
n'entre jamais dans le pipeline comme signal) ; `rdprm`'s règle de
calibration exclut les garanties sur biens personnels/véhicules isolés par le
champ `nature_bien` avant même qu'un `Signal` soit créé. C'est CETTE couche,
en amont, qui filtre champ par champ — une fois qu'un `Signal` existe, son
association aux sphères reste au niveau du type, par design (le principe
d'extensibilité, spec section 9 : un type de signal a UNE table de
correspondance, pas une par combinaison de champs).

**Bogue réel trouvé en répondant à cette question** : `financement_acces_
capital` existait dans `spheres.yaml` (avec `signal_absence_pertinent:
financement_expansion`) depuis son ajout le 2026-09-01, mais n'avait JAMAIS
été ajoutée à `spheres_probables` de `financement_expansion` dans `signal_
types.yaml` — un oubli, pas une décision. Conséquence réelle : un profil
configuré sur cette sphère ne pouvait recevoir AUCUNE notification par le
chemin générique de `match_profile` (`sphere_ok` toujours `False`), seulement
le bonus de pertinence par absence (`falkye/pertinence.py::
bonus_signal_absence`), qui suppose déjà qu'un AUTRE match a fait entrer
l'entreprise dans le pipeline — la sphère était donc, en pratique,
INATTEIGNABLE. Corrigé le 2026-09-02 : ajoutée en DERNIÈRE position de la
liste (décision conservatrice documentée dans `signal_types.yaml` — ne
déplace pas la "sphère principale" des personas déjà supportés). Testé bout
en bout (`tests/test_matching.py::
test_match_profile_financement_acces_capital_matche_un_signal_financement`).

### Filtrage par champ, contextuel au profil (spec section 6, ajouté le 2026-09-02)

Suite directe de la section précédente : le lien sphère ↔ signal reste au
niveau du `signal_type_id` en entier — mais un TROISIÈME mécanisme de
filtrage, distinct des deux premiers, s'ajoute maintenant au-dessus.

Récapitulatif des trois couches de filtrage, désormais complètes :

1. **Calibration à l'ingestion** (`SourceDef.regle_calibration`) — répond à
   une question UNIVERSELLE ("cette donnée est-elle du bruit administratif,
   point final?"), la même pour tous les profils. Ex. REQ ne retient que
   certains types de mise à jour, RDPRM exclut par `nature_bien`. Inchangée.
2. **Matching sphère ↔ signal** (`SignalTypeDef.spheres_probables`) — au
   niveau du `signal_type_id` en entier (voir section précédente). Inchangé.
3. **Filtrage par champ, contextuel au profil** (`falkye/pertinence.py::
   filtrer_champs_pertinents`, NOUVEAU) — répond à une question dont la
   réponse dépend de QUI regarde : au sein d'un même `Signal.champs`, un
   champ peut être pertinent pour un profil et du bruit pour un autre. Ex.
   d'origine de la spec : le secteur/NAICS du REQ compte pour un courtier en
   efficacité énergétique, pas pour un fournisseur de mobilier de bureau.

**Pourquoi cette couche ne peut pas vivre à l'ingestion** : la couche 1
répond à une question universelle, valable pour tout profil. La couche 3
répond à une question qui change selon le profil qui regarde — un champ
retiré à l'ingestion serait perdu pour TOUJOURS, y compris pour une sphère
future qui en aurait besoin. C'est exactement le risque déjà vécu avec la
sphère "Financement / accès au capital" (voir bogue de la section
précédente) : mieux vaut capter largement une seule fois, puis appliquer
plusieurs lentilles différentes selon qui consulte, que refiltrer après
coup une donnée jamais captée.

**Mécanisme** : `registry/champs_pertinents.yaml` — une grille (sphère_id,
source_id) → liste blanche de clés de `Signal.champs`, chargée dans
`Registry.champs_pertinents` (dict à clé composite) et exposée via
`Registry.champs_pertinents_pour(sphere_id, source_id) -> list[str] | None`.
Absence d'entrée = `None` = AUCUN filtrage, TOUS les champs comptent —
défaut sûr qui ne perd jamais une donnée par simple omission de registre
(le même principe que `champs_pertinents_pour` sur `SourceDef`, appliqué
cette fois par paire sphère/source plutôt que par source seule).

`falkye/pertinence.py::filtrer_champs_pertinents(champs, sphere_id,
source_id, registry)` applique cette liste blanche à un dict `Signal.champs`
et retourne une VUE filtrée — elle ne retire jamais rien de `Signal.champs`
en base ("un seul entrepôt, plusieurs lentilles"). `sphere_id=None`
(notifications antérieures à la restructuration en deux axes, sans
`sphere_probable_id`) est géré sans erreur : aucune entrée ne peut matcher
une clé `(None, source_id)`, donc aucun filtrage.

**Point d'intégration** : `falkye/notifications/formatter.py::
formatter_notification` — chaque signal contributif du payload webhook
structuré (`donnees_structurees["signaux"][i]`) porte désormais une clé
`"champs_pertinents"`, calculée pour LA sphère retenue pour cette
notification (`notification.sphere_probable_id`). Le corps texte de la
notification (courriel) n'utilise pas cette vue filtrée — seul le payload
structuré, consommé par un système externe (CRM/ERP via webhook Radar+),
en bénéficie.

**Gap réel trouvé et corrigé en construisant cette grille** :
`falkye/sources/req.py::_diff_etablissements_secondaires` captait déjà
`secteur_code`/`secteur_libelle` sur le dataclass interne `_EtabLeger` et
les écrivait même dans `REQEtablissementEntry` (le miroir DB), mais ne les
incluait JAMAIS dans le dict ajouté à `stats.nouveaux_etablissements_
secondaires` — ils n'atteignaient donc jamais `Signal.champs` pour un
signal `registre_corporatif` "nouvel établissement". Corrigé le 2026-09-02 :
les deux champs sont maintenant propagés jusqu'au signal, condition
nécessaire pour que la grille sphère `efficacite_energetique` × source
`req` ait quelque chose à filtrer.

Grille initiale (`registry/champs_pertinents.yaml`) : deux entrées de
départ — `efficacite_energetique` × `req` (garde `secteur_code`/
`secteur_libelle`, exemple d'origine de la spec) et `logistique_transport_
flotte` × `req` (garde `adresse`/`type_changement`, illustratif — non
encore validé contre un usage réel, à ajuster si l'usage le contredit,
principe directeur #9). Extensible sans migration de code : ajouter une
entrée au YAML suffit, suivant le même principe que le reste du registre.

### Retrait de "Gestion d'inventaire et d'actifs" (correction d'architecture, 2026-09-03)

Cette sphère était présente depuis la Phase 1 (reprise directement de la
liste de départ de la spec, section 4) — mais Alexandre l'a identifiée
après coup comme une erreur de catégorisation : ce n'était pas une
catégorie de besoin GÉNÉRIQUE comme les autres sphères, c'était un
**service précis** — le cas d'usage d'origine du projet lui-même
(implantation Hector). Elle a été retirée au profit d'un rattachement par
l'assistance IA à deux paliers (section précédente) plutôt que d'avoir sa
propre sphère dédiée — cohérent avec le principe que le registre curé doit
rester un ensemble de catégories vraiment génériques, pas une collection
de services individuels.

**Vérification avant suppression** (exigée explicitement par Alexandre,
"pour ne rien casser silencieusement") — trois références réelles trouvées
et traitées, aucune laissée en suspens :
1. `registry/signal_types.yaml::financement_expansion.spheres_probables`
   la listait — retirée de la liste ; les sphères restantes
   (`logistique_transport_flotte`, `production_operations_manufacturieres`,
   etc.) couvrent déjà le cas équipement/inventaire de production, aucun
   remplacement n'était nécessaire.
2. `README.md` l'utilisait comme exemple de `profile add-need` — remplacée
   par `technologie_systemes_ti` (voir point 3).
3. **La base de développement réelle** portait une référence bien réelle :
   le `ProfileNeed` d'Alexandre lui-même (`profile #1`, "Implantation de
   systèmes de gestion d'inventaire et d'actifs (Hector)"). Réassigné à
   `technologie_systemes_ti` — décision informée par le Niveau 1 lui-même,
   exécuté contre le texte réel de ce besoin (`implantation, gestion
   d'inventaire, ERP, WMS, amélioration continue`) : deux candidats à
   score égal (`technologie_systemes_ti` via "ERP",
   `production_operations_manufacturieres` via "amélioration continue"),
   `technologie_systemes_ti` retenu comme le plus spécifique des deux
   (ERP/WMS nomment précisément le type de logiciel implanté, "amélioration
   continue" est un terme générique qui ne décrit pas ce que fait
   spécifiquement Hector) — **décision assumée, pas arbitraire, mais
   ajustable par Alexandre en un mot s'il préfère l'autre candidat.**
   Les 8 lignes `SphereSynonyme` propres à cette sphère (origine="registre")
   ont aussi été supprimées de la base réelle (orphelines une fois la
   sphère retirée du registre) avant la suppression de la ligne `Sphere`
   elle-même, pour respecter la contrainte de clé étrangère sans jamais
   avoir à la contourner.

**Synonymes retirés, pas redistribués** : les mots-clés propres à cette
sphère ("gestion d'inventaire", "RFID", "codes-barres", etc., voir
`registry/spheres.yaml`) ont été supprimés purement et simplement, jamais
rattachés en bloc à une autre sphère existante — les y rattacher aurait
recréé exactement le raccourci que cette correction retire (un texte comme
"gestion d'inventaire" doit désormais rester ambigu au Niveau 1 et
escalader au Niveau 2, pas être pré-tranché par un mot-clé statique).

**Cas de test réel retenu par Alexandre** : "spécialiste de gestion
d'inventaire et en implantation de solutions logistiques" — volontairement
ambigu entre `logistique_transport_flotte` et `technologie_systemes_ti`,
sans réponse évidente d'avance. Confirmé contre le VRAI registre
(`tests/test_assistance_sphere.py::
test_cas_reel_ambigu_gestion_inventaire_logistique_vs_ti_echoue_au_niveau1`) :
liste vide au Niveau 1 — le pluriel "logistiques" ne matche pas le synonyme
"logistique" (bornes de mot strictes, comportement attendu, pas un bogue),
confirmant que ce cas escalade correctement au Niveau 2. Testé côté Niveau 2
avec le SDK Anthropic mocké
(`tests/test_assistance_sphere_ia.py::
test_cas_reel_ambigu_gestion_inventaire_logistique_vs_ti`) : le résultat
retenu par le modèle doit être L'UNE des deux sphères plausibles du
catalogue, jamais une troisième inventée — le garde-fou structurel
(enum fermée, voir section précédente) validé sur ce cas réel précis, pas
seulement sur un exemple synthétique. Validation en direct (vrai appel
API) toujours en attente d'une clé `ANTHROPIC_API_KEY` réelle.

## Assistance à la configuration du profil par IA (spec Radar+, point 8, ajoutée le 2026-09-03)

Le seul usage de ML retenu dans tout le produit — deux niveaux, jamais un seul
mécanisme unique, pour que le coût par appel reste proportionnel à la
difficulté réelle du cas.

**Niveau 1 — `falkye/assistance_sphere.py`, gratuit, tous les plans (Écho
compris).** Correspondance MOT-À-MOT (bornée par des limites de mot, jamais une
sous-chaîne brute) entre la description libre de l'utilisateur et le
dictionnaire de synonymes/mots-clés de chaque sphère (`SphereSynonyme`, table
DB alimentée depuis `registry/spheres.yaml::SphereDef.synonymes` par
`falkye.db.seed_sphere_synonymes_from_registry`). "Texte simple" confirmé
explicitement par Alexandre le 2026-09-03 — aucun embeddings, aucun modèle de
langage à ce niveau. Un bogue réel de sous-chaîne brute a été trouvé et corrigé
pendant la validation avec de vraies données (voir docs/STATUT_RESEAU.md) :
l'acronyme "TI" matchait à l'intérieur du mot "implan**ta-ti**on" avant
l'ajout des bornes de mot (regex `(?<!\w)…(?!\w)`, insensible aux lettres
accentuées et aux apostrophes des synonymes composés comme "gestion
d'inventaire").

Liste VIDE de suggestions = échec du Niveau 1 — c'est CE signal, et rien
d'autre, qui déclenche le Niveau 2.

**Niveau 2 — `falkye/assistance_sphere_ia.py`, réservé Radar/Radar+, gating
BINAIRE (pas de système de quota — confirmé par Alexandre le 2026-09-03).**
Un appel Claude (`anthropic` SDK, `claude-haiku-4-5` par défaut — voir
docstring du module pour la justification du choix de modèle) avec une sortie
JSON CONTRAINTE PAR SCHÉMA (`output_config`, `additionalProperties: false`) :
le champ `sphere_id` est une `enum` fermée = les sphères EXISTANTES en base au
moment de l'appel, plus une valeur sentinelle `aucune_correspondance`.

**C'est ce garde-fou-là — confirmé par Alexandre comme "exactement ce qu'on
voulait, pas juste une instruction" — qui rend structurellement IMPOSSIBLE au
Niveau 2 d'inventer une nouvelle sphère : aucune sortie valide du modèle ne
peut nommer un id qui n'existe pas déjà.** Un cas `aucune_correspondance` est
journalisé dans `CandidatSphere` (`falkye/models/candidat_sphere.py`,
`statut="a_examiner"`) — jamais auto-résolu, exactement comme la sphère
"Financement / accès au capital" a été ajoutée par décision humaine après
avoir croisé plusieurs personas (voir section précédente), jamais par un
mécanisme automatique. `falkye sphere candidats` (réservé au mode opérateur —
ce journal traverse tous les profils) liste ces cas pour révision.

Un cas rattaché à une sphère EXISTANTE peut silencieusement enrichir SON
dictionnaire de synonymes (`SphereSynonyme(origine="ia_niveau2")`) — jamais
`registry/spheres.yaml`, jamais la table `Sphere` elle-même.

**Toujours une proposition, jamais une classification silencieuse** : ni le
Niveau 1 ni le Niveau 2 n'écrivent `profile_needs` — `falkye profile
suggerer-sphere` (lecture seule) affiche la ou les suggestions, l'utilisateur
confirme via `falkye profile add-need` s'il est d'accord.

STATUT DE VALIDATION : construit et testé contre le SDK Anthropic mocké
(`tests/test_assistance_sphere_ia.py`) — aucune clé `ANTHROPIC_API_KEY` réelle
disponible dans cet environnement de développement, même situation que
Stripe/HubSpot/Pipedrive (voir docs/STATUT_RESEAU.md).

## Polyvalence d'utilisation (spec section 9, ajoutée le 2026-08-31)

Exigence originale (2026-08-31) : le produit doit rester utilisable par
n'importe quel fournisseur de service B2B, pas seulement un consultant en
implantation de systèmes d'inventaire. Révisée le 2026-09-02 (principe
directeur #6) : "une multitude de types d'utilisateurs — pas seulement des
fournisseurs de services B2B" (chambres de commerce, développement économique
régional, etc. — un usage hors vente, pas seulement un service vendu). Suit un
renommage de vocabulaire dans le code : `ProfileNeed.service_precis` →
`usage_precis`, `cli.py --service` → `--usage` (voir docs/STATUT_RESEAU.md
pour la migration). Audit original fait le 2026-08-31 sur le code déjà
construit, toujours valide sur le fond (seul le nom du champ a changé) :

- **Rien dans le moteur, le scoring, la vérification ou le schéma de données** ne
  fait référence à un secteur ou un usage particulier — `sphere_id` et
  `usage_precis` (`service_precis` avant le 2026-09-02) sont traités comme des
  valeurs opaques partout (voir `matching.py`, `engine.py`, `models/profile.py`).
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
  priorisation du code. (Note historique : cette sphère a depuis été RETIRÉE du
  registre le 2026-09-03 — voir section "Extensibilité des sphères de besoin"
  plus bas — ce constat d'audit reste exact pour la date où il a été écrit.)
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
courriel actif (SMTP, `falkye/notifications/email_channel.py`), SMS/WhatsApp au
statut `a_developper` (`StubChannel` — échoue explicitement plutôt que de simuler
un envoi). Webhook générique passé `actif` le 2026-09-02 pour la fonctionnalité
Radar+ "accès API/webhook complet" (spec section 4bis) — voir
`falkye/notifications/webhook_channel.py` et la section "Tableau de bord..."
ci-dessus pour le détail (destination résolue par profil, pas une variable
d'environnement globale). Activer un canal Phase 2 = configurer les variables
d'env listées dans le registre + changer son statut, sans toucher `engine.py`.

`NotificationChannel.resoudre_destinataire(profile)` (`falkye/notifications/
base.py`, ajoutée le 2026-09-02) généralise la résolution de destination —
avant cette date, `engine.deliver_notification` codait en dur
`notification.profile.courriel` comme seule destination possible (limitation
documentée dès la Phase 1). Chaque canal résout maintenant SA propre
destination à partir du profil (`EmailChannel` hérite du comportement par
défaut — `profile.courriel` — sans le redéfinir ; `WebhookChannel` retourne
`profile.webhook_url`, ou `None` si le profil n'est pas Radar+) — le moteur ne
sait toujours pas qu'un canal précis existe, seulement qu'il faut lui demander
sa destination avant de tenter une livraison.
