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

*(Mise à jour 2026-09-03 : `need.sphere_id` — colonne unique — n'existe plus.
`match_profile` compare désormais CHACUNE des sphères de `need.spheres_liees`
(lien plusieurs-à-plusieurs pondéré) à `spheres_probables(...)` ; voir la
section "Sphère ↔ besoin plusieurs-à-plusieurs pondérée" plus bas. Le
principe décrit ici — le lien reste au niveau du `signal_type_id` en entier —
est inchangé, seule la cardinalité sphère↔besoin a changé.)*

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

**Cette section décrit l'état INITIAL du mécanisme (une sphère unique par
besoin). Il a été généralisé le 2026-09-03 même — voir la section "Sphère ↔
besoin plusieurs-à-plusieurs pondérée, dimension 'qui', journal de diagnostic
généralisé" plus bas pour l'architecture ACTUELLE (l'essentiel du
raisonnement Niveau 1/Niveau 2 ci-dessous reste vrai, seul le SCHÉMA de
sortie et le nombre de résultats possibles ont changé).**

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
d'inventaire") — ce matcher à bornes de mot est maintenant partagé
(`falkye/texte_matching.py::motif_present`) entre la dimension sphère et la
dimension "qui".

Liste VIDE de suggestions = échec du Niveau 1 — c'est CE signal, et rien
d'autre, qui déclenche le Niveau 2.

**Niveau 2 — réservé Radar/Radar+, gating BINAIRE (pas de système de quota —
confirmé par Alexandre le 2026-09-03).** Un appel Claude (`anthropic` SDK,
`claude-haiku-4-5` par défaut — voir docstring du module pour la
justification du choix de modèle) avec une sortie JSON CONTRAINTE PAR SCHÉMA
(`output_config`, `additionalProperties: false`) : l'id retourné est une
`enum` fermée = les entrées EXISTANTES du catalogue au moment de l'appel,
plus une valeur sentinelle `aucune_correspondance`.

**C'est ce garde-fou-là — confirmé par Alexandre comme "exactement ce qu'on
voulait, pas juste une instruction" — qui rend structurellement IMPOSSIBLE au
Niveau 2 d'inventer une nouvelle catégorie : aucune sortie valide du modèle ne
peut nommer un id qui n'existe pas déjà.** Un cas `aucune_correspondance` est
journalisé (`DiagnosticJournal`, `statut="a_examiner"`) — jamais auto-résolu,
exactement comme la sphère "Financement / accès au capital" a été ajoutée par
décision humaine après avoir croisé plusieurs personas (voir section
précédente), jamais par un mécanisme automatique. `falkye diagnostic lister`
(réservé au mode opérateur — ce journal traverse tous les profils) liste ces
cas pour révision.

Un cas rattaché à une entrée EXISTANTE du catalogue peut silencieusement
enrichir SON dictionnaire de synonymes (`SphereSynonyme`/`ClientCibleSynonyme`,
`origine="ia_niveau2"`) — jamais le YAML source, jamais la table catalogue
elle-même.

**Toujours une proposition, jamais une classification silencieuse** : ni le
Niveau 1 ni le Niveau 2 n'écrivent `profile_needs` — `falkye profile
configurer-besoin` (aperçu par défaut) affiche la proposition, l'utilisateur
confirme avec `--confirmer` s'il est d'accord.

STATUT DE VALIDATION : construit et testé contre le SDK Anthropic mocké
(`tests/test_assistance_sphere_ia.py`, `tests/test_assistance_client_cible_ia.py`)
— aucune clé `ANTHROPIC_API_KEY` réelle disponible dans cet environnement de
développement, même situation que Stripe/HubSpot/Pipedrive (voir
docs/STATUT_RESEAU.md).

## Sphère ↔ besoin plusieurs-à-plusieurs pondérée, dimension "qui", journal de diagnostic généralisé (spec section 8bis, 2026-09-03)

**Déclencheur réel** : le cas Hector lui-même (voir "Retrait de 'Gestion
d'inventaire et d'actifs'" plus haut) a exposé qu'un besoin peut légitimement
appartenir à PLUSIEURS sphères à la fois — l'ancienne colonne unique
`ProfileNeed.sphere_id` forçait un choix arbitraire entre deux candidats
également valides (`technologie_systemes_ti` vs `production_operations_
manufacturieres`) plutôt que de représenter les deux. Alexandre a demandé une
architecture avant tout code, avec trois questions explicites à répondre :

1. **Le regroupement grossier des secteurs REQ (`falkye/registry/
   secteurs_grossiers.yaml`) peut-il servir de base à un registre "clientèle
   cible" ?** Vérifié contre le vrai miroir REQ (2,7M lignes) avant de
   concevoir quoi que ce soit : **invalide**. Le regroupement REQ classe des
   ENTREPRISES par secteur d'activité économique — les organismes publics et
   institutionnels (commissions scolaires, sociétés de transport,
   municipalités, CISSS/CIUSSS) qui sont des clientèles cibles B2B tout à
   fait réelles n'y apparaissent PAS comme catégorie distincte utile, parce
   que le REQ ne couvre que les entités inscrites au registre des entreprises
   — pas les organismes publics. D'où un registre `ClientCible` **totalement
   indépendant** (`registry/clients_cibles.yaml`), avec une entrée
   `organismes_publics_institutionnels` ajoutée SPÉCIFIQUEMENT pour combler
   ce vide, jamais dérivée de `secteurs_grossiers`.
2. **Comment les deux axes (confiance, pertinence) combinent-ils avec cette
   nouvelle dimension "qui" ?** "Qui" ne devient JAMAIS un troisième axe
   visible — il s'intègre au score de pertinence existant (bonus plafonné,
   voir plus bas), jamais une indicateur d'en-tête séparé.
3. **Traitement concret du "hors profil"** (désaccord confiant entre la
   clientèle déclarée et la clientèle détectée de l'entreprise) : jamais un
   malus silencieux sur le score — une REDIRECTION (canal séparé), réservée
   Radar+.

Alexandre a confirmé le design SANS réserve, puis ajouté deux exigences non
négociables avant le code :

- **Simplicité d'usage, pour le "quoi" ET le "qui"** : jamais un écran de
  pourcentages à manipuler. Un seul point d'entrée conversationnel en texte
  libre (`profile configurer-besoin`) — les poids sont CALCULÉS, une donnée
  de transparence secondaire affichée après coup, pas l'interface
  elle-même. Le raffinement manuel (`profile lier-sphere`, `profile
  lier-client-cible`, `profile definir-sphere-principale`) reste disponible,
  jamais une étape obligatoire.
- **Départage d'égalité SANS règle mécanique** : quand le Niveau 1 trouve
  plusieurs sphères à SCORE EXACTEMENT ÉGAL, ce n'est PAS une règle arbitraire
  (ex. ordre alphabétique) qui tranche laquelle devient "la sphère
  principale" — c'est le Niveau 2, avec son propre raisonnement contextuel
  sur la description complète, exactement comme n'importe quel autre appel
  Niveau 2. **"Le poids EST déjà le classement — aucune règle mécanique n'est
  nécessaire"** (design confirmé par Alexandre) : la sphère avec le plus haut
  poids retourné par le modèle EST la sphère principale, par construction,
  sans champ ni règle séparée. L'utilisateur peut ensuite inverser ce choix
  aussi simplement que possible (`profile definir-sphere-principale`).

### Modèles

`ProfileNeedSphere` (`profile_need_spheres`) et `ProfileNeedClientCible`
(`profile_need_clients_cibles`) — deux tables de jonction pondérées
(`poids: float`, défaut 100.0), miroir l'une de l'autre. **Aucune colonne
`est_primaire` séparée** — la sphère/clientèle "principale" d'un besoin est
TOUJOURS dérivée comme `max(poids)` au moment de la lecture
(`ProfileNeed.sphere_principale()` / `.client_cible_principal()`), jamais
une seconde source de vérité stockée qui pourrait diverger du poids réel.
`ProfileNeed.sphere_id` est retiré ENTIÈREMENT (colonne supprimée, pas
seulement dépréciée).

`ClientCible` (`clients_cibles`) + `ClientCibleSynonyme`
(`client_cible_synonymes`) — registre extensible, exact miroir de
`Sphere`/`SphereSynonyme` (`est_personnalisee`/`proposee_par`, synchronisé
depuis `registry/clients_cibles.yaml` par `db.seed_clients_cibles_from_
registry`/`seed_client_cible_synonymes_from_registry`, jamais aucune
entrée `origine="ia_niveau2"` touchée par le seed). Neuf entrées de
départ, dont la sentinelle `aucune_restriction` (`ID_AUCUNE_RESTRICTION`,
`falkye/models/client_cible.py`) — **une ligne RÉELLE du catalogue, PAS un
second sentinel Niveau 2** : le modèle la sélectionne via le tableau normal
`liens`, exactement comme n'importe quelle autre catégorie. Seul
`aucune_correspondance` (le "je ne sais pas") reste un sentinel véritable
pour la dimension "qui" — simplification retenue une fois réalisé que
"aucune restriction" est naturellement sélectionnable depuis le catalogue
normal, sans logique de schéma spéciale.

`DiagnosticJournal` (`journal_diagnostic`, `TypeDiagnostic` enum :
`candidat_sphere` / `candidat_client_cible` / `source_manquante`) remplace
l'ancien `CandidatSphere`, à usage unique — `profile_id` désormais nullable
(une source manquante journalisée manuellement peut ne se rattacher à AUCUN
profil précis).

`Notification.hors_profil: bool` (défaut `False`) — la marque de redirection
pour un désaccord "qui" confiant.

### Assistance IA généralisée (`falkye/assistance_ia.py`)

Le moteur Niveau 1/Niveau 2 est désormais PARTAGÉ entre les deux dimensions
plutôt que dupliqué : `falkye/assistance_sphere.py`/`assistance_client_
cible.py` (Niveau 1, mots-clés) et `assistance_sphere_ia.py`/`assistance_
client_cible_ia.py` (Niveau 2, enveloppes minces autour du moteur commun
`assistance_ia.py`).

**Schéma de sortie unifié — le changement central qui sert DEUX besoins à la
fois** (design salué par Alexandre : "exactement le niveau d'élégance qu'on
voulait") : au lieu de retourner UN id, le Niveau 2 retourne toujours un
ENSEMBLE `liens: [{id, poids}]`. Ce même changement sert :
1. le cas général plusieurs-sphères (un besoin peut légitimement toucher
   plusieurs sphères à la fois, chacune avec son poids) ;
2. le départage d'égalité (les poids retournés SONT le classement — pas de
   champ ni de règle séparée pour désigner "la sphère principale").

Deux modes d'appel distincts :
- `classifier_niveau2(catalogue, sentinelles, ...)` — catalogue COMPLET +
  sentinelle(s), utilisé quand le Niveau 1 échoue totalement (liste vide).
- `departager_niveau2(candidats, ...)` — catalogue RESTREINT aux seuls
  candidats retournés par le Niveau 1 (pas encore réduit aux seuls candidats
  À ÉGALITÉ — simplification d'implémentation, le modèle pondère
  naturellement), AUCUNE sentinelle (le Niveau 1 a déjà trouvé au moins une
  correspondance, il ne s'agit plus de savoir SI ça correspond mais LEQUEL
  domine), utilisé quand le Niveau 1 trouve un tie exact au score maximal.

Les deux fonctions publiques ne prennent AUCUNE session DB — appels API purs,
la persistance (journalisation, enrichissement de synonymes) reste la
responsabilité des enveloppes minces (`assistance_sphere_ia.py`/
`assistance_client_cible_ia.py`), qui appellent le moteur commun puis
persistent le résultat.

### Classification "qui" de l'entreprise détectée

Réutilise TEL QUEL le matcher Niveau 1 existant (`suggerer_clients_cibles_
niveau1`) contre `company.secteur_activite_libelle` — aucun nouveau
mécanisme, gratuit, local. Décision délibérée compte tenu du gap de
couverture institutionnelle du REQ déjà identifié (question 1 ci-dessus) :
un effort raisonnable, pas une garantie, cohérent avec le principe de ne
jamais construire un nouveau mécanisme de classification coûteux sans qu'il
ait été demandé.

### `matching.py` / `pertinence.py`

`MatchResult.spheres_liees: list[SphereMatch]` — TOUTES les sphères liées au
besoin (pas seulement la "sphère probable" du signal). `spheres_generiques_
ids` — le SOUS-ENSEMBLE probable pour CE signal précis (résultat de
l'intersection avec `spheres_probables(...)`).

`pertinence.py::base_match_pour_sphere(match, sphere_id, ...)` remplace
l'ancien `base_match()` à sphère unique — calcule la base A/AA/AAA pour UNE
sphère précise du lien, mise à l'échelle par son poids
(`base_x * (poids_lien / 100.0)`). `meilleure_sphere_pour_match(...)` choisit,
parmi toutes les sphères liées d'un match, celle qui produit la meilleure
base — c'est CETTE sphère qui devient `Notification.sphere_probable_id`,
jamais un choix arbitraire.

**Bonus "qui" (`BONUS_QUI_MAX = 12.0`) et redirection**
(`bonus_et_redirection_qui`) :
- Aucune clientèle cible configurée pour le besoin, OU le besoin porte
  `aucune_restriction` parmi ses liens → bonus nul, jamais de redirection
  (comportement par défaut sûr, cohérent avec "qui omis = non configuré,
  aucun impact").
- Intersection non vide entre la clientèle détectée de l'entreprise et la
  clientèle liée au besoin → bonus proportionnel au poids du lien qui a
  matché (jamais une redirection).
- Clientèle du besoin connue, clientèle de l'entreprise connue, AUCUNE
  intersection → **bonus nul, `hors_profil=True`** — jamais un malus. Un
  désaccord confiant est un signal de ROUTAGE, pas une pénalité sur le
  score : l'information peut rester pertinente pour un autre besoin/segment,
  elle ne doit simplement pas se mêler au flux normal.
- Clientèle de l'entreprise inconnue (best-effort du Niveau 1 échoué) →
  bonus nul, PAS de redirection (absence de signal ≠ désaccord confiant).

`calculer_pertinence(...)` prend maintenant `client_cible_ids_entreprise`/
`clients_cibles_lies_besoin` (défauts `None` → liste vide, jamais fabriqués),
`score = min(100.0, base + b_absence + b_velocite + b_qui)`.

### `engine.py` — intégration et gating

`_traiter_entreprise_pour_profil` choisit désormais la MEILLEURE sphère
parmi toutes celles liées au besoin (`meilleure_sphere_pour_match`), plutôt
que de comparer contre une seule sphère fixe. La classification "qui" de
l'entreprise (et donc le bonus/la redirection) n'est calculée QUE pour un
profil Radar+ — **gating étendu à TOUT l'axe "qui" (bonus ET redirection),
pas seulement au canal hors-profil explicitement demandé** : extension
assumée de ma part, cohérente avec les précédents de gating à un seul palier
déjà en place ailleurs (`ponderation.py`, `webhook_channel.py`), présentée
dans le plan et non contestée par Alexandre avant le codage.

`deliver_notification()` : garde en tout début — une notification
`hors_profil=True` n'emprunte AUCUN canal (email/webhook) ni push CRM. La
ligne `Notification` elle-même reste écrite en base (créée par les mêmes
portes confiance/pertinence qu'avant, JAMAIS un nouveau seuil de création) —
seule la LIVRAISON est court-circuitée, pour que `dashboard voir` puisse
l'afficher dans sa section séparée.

### CLI

`profile configurer-besoin` — point d'entrée conversationnel unique
(`--usage`, `--client-cible` optionnel, aperçu par défaut, `--confirmer`
pour créer). Logique d'escalade partagée (`_proposer_liens_spheres`/
`_proposer_liens_client_cible`) : Niveau 1 → égalité exacte au score max ⇒
`departager_..._niveau2` (repli sur poids égaux à 100 si le plan/la clé API
manque — jamais un blocage dur) → non vide sans égalité ⇒ scores Niveau 1
normalisés directement en poids 0-100 → vide ⇒ escalade au Niveau 2 complet
ou échec proprement journalisé.

`profile lier-sphere` / `profile lier-client-cible` (raffinement manuel,
`--poids`) ; `profile definir-sphere-principale` (promeut une sphère au-delà
du poids max actuel, `+1.0`, aucun plafond — accepté comme inoffensif).
`diagnostic lister` / `diagnostic ajouter-source-manquante` remplacent
`sphere candidats` (réservés au mode opérateur, journal généralisé). `profile
add-need` ne prend plus `--sphere-id` — crée un besoin SANS sphère liée, à
rattacher ensuite via `configurer-besoin` ou `lier-sphere`. `dashboard voir`
scinde désormais ses cartes en deux sections : dossiers normaux, puis dossiers
hors profil déclaré (Radar+), jamais mélangés.

### Migration de la base de développement réelle

Colonne `profile_needs.sphere_id` retirée (recréation de table SQLite —
`DROP COLUMN` refusé tant qu'une contrainte de clé étrangère porte sur la
colonne) ; table `candidats_spheres` (vide) supprimée au profit de
`journal_diagnostic`. Cinq nouvelles tables créées (`profile_need_spheres`,
`clients_cibles`, `client_cible_synonymes`, `profile_need_clients_cibles`,
`journal_diagnostic`), registre `clients_cibles.yaml` semé (9 entrées).
`notifications.hors_profil` ajoutée par `ALTER TABLE ... ADD COLUMN` (table
préexistante, hors de portée de `init_db()`/`create_all`).

**Le besoin réel d'Alexandre lui-même** (`profile #1`, "implantation
Hector") a été réétabli comme lien pondéré :
`ProfileNeedSphere(profile_need_id=1, sphere_id="technologie_systemes_ti",
poids=100.0)` — exactement la même sphère que la réassignation précédente
(voir "Retrait de 'Gestion d'inventaire et d'actifs'"), maintenant
représentée sous la nouvelle forme N:N plutôt que perdue dans la migration.
Vérifié après coup (`profile list`, mode opérateur) : le besoin affiche
correctement `sphères : technologie_systemes_ti(100)`,
`clientèle cible : non configuré` (jamais fabriqué — Alexandre n'a pas
encore configuré cette dimension pour ce besoin, et son profil est au plan
Écho, hors de portée du canal hors-profil de toute façon).

Sauvegarde du fichier DB prise avant toute modification de schéma.

### Chemin "hors profil déclaré" — validé de bout en bout (2026-09-03)

Demande explicite d'Alexandre, après la livraison ci-dessus : combler la
limite honnête notée alors (le chemin bonus/redirection "qui" n'était
validé que par des tests unitaires) par un scénario contre une base
TEMPORAIRE — même méthode que le scénario d'authentification déjà validé
ainsi (voir docs/STATUT_RESEAU.md), plutôt que d'attendre un vrai client
Radar+ ou de fabriquer des données dans la base réelle.

Trois entreprises, un seul besoin Radar+ (clientèle cible déclarée
`pme_privees_generales`), traitées via un appel direct à
`falkye.engine._traiter_entreprise_pour_profil`/`deliver_notification`
(fabriquer un `Company`/`Signal` n'a pas de commande CLI dédiée — les
signaux réels ne viennent que des connecteurs) :

- **Désaccord confiant** (entreprise classée `organismes_publics_
  institutionnels`) → `hors_profil=True`, score IDENTIQUE au cas sans
  aucune donnée "qui" (60/100 dans les deux cas — preuve concrète qu'il n'y
  a AUCUN malus), zéro tentative de livraison, section "Hors profil
  déclaré" du tableau de bord.
- **Accord** (même catégorie que le besoin) → `hors_profil=False`, bonus
  +12 (plafond `BONUS_QUI_MAX`), livraison RÉELLEMENT tentée.
- **Absence de signal "qui"** → `hors_profil=False`, ni bonus ni malus,
  livraison tentée normalement — confirme que l'absence de signal n'est
  jamais traitée comme un désaccord.

Voir docs/STATUT_RESEAU.md, section "Chemin 'hors profil déclaré' — validé
de bout en bout", pour le détail complet du scénario et les résultats
observés. Fichier DB temporaire supprimé après coup.

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

## Sept points de suivi post-livraison — sphère N:N/qui/hors-profil (2026-09-03)

Alexandre a demandé une vérification en sept points après la livraison des
trois chantiers précédents et de leur validation bout en bout. Le point 1
était une question de données (réponse ci-dessous) ; les points 2-7 ont fait
l'objet d'un plan avant tout code, confirmé sans réserve, puis codés.

### Point 1 — portée réelle de `champs_pertinents.yaml`

Compilé contre le code des 15 connecteurs actifs (pas seulement l'observé,
qui ne couvrait que 3 sources dans la base réelle au moment de vérifier) :
`req` (10 clés), `licences_vancouver` (9), `licences_toronto` (8), `eimt`
(7), `contrats_federaux`/`contrats_nouvelle_ecosse`/`guichet_emplois`/
`permis_construction_laval`/`rob_top_growing`/`seao`/`subventions_federales`
(6 chacune), `corporations_canada` (5), `deloitte_fast50` (4),
`investissement_quebec` (2), `rdprm` (0 — stub, aucune production de signal
avant la Phase 2). Sert de base à toute extension future de
`registry/champs_pertinents.yaml` (règle déjà tranchée par Alexandre : garder
un champ si au moins une sphère liée du profil le juge pertinent).

### Point 2 — classification "qui" cross-source (`falkye/assistance_client_cible.py::suggerer_clients_cibles_niveau1_pour_company`)

`company.secteur_activite_libelle` EST DÉJÀ la fusion cross-source pour REQ
et les licences municipales hors Québec — vérifié dans le code plutôt que
supposé (`falkye/resolution.py::resolve_company` propage `raw.secteur_
activite=brute.type_entreprise` pour `licences_toronto`/`licences_
vancouver`, même champ, même rôle que le secteur REQ). Aucun changement de
mécanisme nécessaire pour ces deux-là.

Les autres champs disponibles à travers les signaux d'une entreprise
(`donneur_ordre`/`ministere` de SEAO/contrats fédéraux/Nouvelle-Écosse/
subventions, `titre_poste`/`profession` du recrutement, `description_
tender`) sont DÉLIBÉRÉMENT exclus, documentés comme tels dans la docstring
de la fonction : ces champs décrivent le DONNEUR D'ORDRE, le POSTE affiché,
ou le CONTRAT — jamais la clientèle propre de l'entreprise détectée
elle-même. Les inclure classerait à tort une firme d'ingénierie privée
comme "organismes publics et institutionnels" simplement parce qu'elle a
décroché un contrat d'un ministère. Aucune escalade Niveau 2 pour une
entreprise détectée (coût IA par entreprise scannée jamais introduit sans
demande explicite) — sans signal classifiable, liste vide, jamais une
catégorie forcée.

### Point 3 — tableaux agrégés par clientèle cible + neutralité des libellés

`falkye/synthese.py::SyntheseAgregee.par_client_cible` — nouvelle dimension
d'agrégation, COMPLÉMENTAIRE à `par_secteur` (regroupement grossier SCIAN),
jamais un remplacement. Réponse au gap trouvé en construisant `par_secteur` :
une entreprise détectée uniquement via une source hors Québec pouvait avoir
un secteur classifiable (point 2 le confirme) mais tomber quand même en
"(non classé)" parce que `secteurs_grossiers.yaml` est construit contre le
vocabulaire français du REQ, pas contre les catégories de licences
municipales anglaises. `clients_cibles.yaml`, registre INDÉPENDANT de toute
source, sert de repli. `classifications_qui` (le dict `{company_id: nom}`)
est calculé par l'APPELANT (`falkye/cli.py::dashboard_synthese`, accès DB
requis pour `ClientCibleSynonyme`) — `falkye/synthese.py` reste pur, aucun
accès DB, comme avant.

**Charte de neutralité des libellés, élargie** : "aucun libellé visible par
l'utilisateur ne doit jamais nommer une source précise", avec pour seule
exception délibérée le portail de sources payantes (`falkye registry
sources`, `falkye crm fournisseurs`) et les outils d'exploitation qui
opèrent DIRECTEMENT sur une source par construction (`import-manuel`, jamais
accessible via une identité de profil/session — traité dans la même
catégorie que le portail, confirmé par Alexandre). Deux fuites réelles
trouvées et corrigées :
1. `falkye/notifications/formatter.py` — le corps du courriel nommait la
   source en clair (`"[SEAO (Système électronique d'appel d'offres du
   Québec)] ..."`). Remplacé par la CATÉGORIE de signal (`registry/
   signal_types.yaml::nom`, déjà neutre, déjà en place) — donnée existante,
   aucun nouveau registre. Le payload structuré du webhook Radar+, lui,
   garde `source_id` : c'est une donnée TECHNIQUE consommée par le système
   du client (CRM/ERP), pas un libellé lu par un humain — confirmé par
   Alexandre comme hors du principe.
2. `falkye/cli.py::_afficher_rapport` (`scan veille`/`scan ponctuel`,
   commandes libre-service) — affichait le `source_id` brut. Agrégé
   maintenant par catégorie de signal (`_categorie_pour_source`, chaque
   source active n'étant associée qu'à une seule catégorie — vérifié, pas
   d'ambiguïté à trancher) ; le détail par source individuelle (y compris
   les messages d'erreur, potentiellement révélateurs) reste consultable
   via `SourceRunLog`, en mode opérateur seulement.

### Point 4 — dédoublonnage des entreprises sans NEQ (`falkye/dedup_entreprises.py`)

**Confirmé, avec preuve plutôt qu'une supposition** : `falkye/resolution.py::
_find_unresolved_company` ne faisait qu'une correspondance EXACTE par nom
normalisé pour toute entreprise sans NEQ — jamais floue, contrairement à la
résolution REQ et au rapprochement inter-provincial. Vérifié contre les
1337 entreprises réellement sans NEQ dans la base réelle avant de coder : 76
paires à similarité >=90% déjà présentes (majoritairement des entités
Québec dont la résolution REQ elle-même avait échoué, pas seulement les
sources hors Québec — même mécanisme sous-jacent, portée plus large que ce
qui avait été demandé).

**Deux seuils, jamais un seul** — décision explicite d'Alexandre : "jamais
de fusion automatique silencieuse... une fusion incorrecte est trop
coûteuse à défaire pour la laisser à un seuil unique." Score >= 95 (`SEUIL_
FUSION_AUTO`) : fusion APPLIQUÉE immédiatement (`falkye/dedup_
entreprises.py::fusionner` réassigne Signal/Notification puis supprime le
doublon), journalisée à titre purement informationnel
(`DiagnosticJournal`, `statut="fusionne_auto"`). Score 90-95 (`SEUIL_
FUSION_CANDIDAT`) : jamais fusionné seul, journalisé
(`statut="a_examiner"`) pour confirmation manuelle
(`falkye diagnostic confirmer-fusion`/`rejeter-fusion`). Même scorer unique
du projet (`rapidfuzz.fuzz.WRatio`), même bonus de ville (+5) que la
résolution REQ, recherche BORNÉE par préfixe (GLOB, même technique que
`falkye.sources.req.resolve_neq_by_name` — jamais un balayage complet).
Jamais contre une entreprise déjà résolue au REQ (`neq IS NOT NULL`).

**BOGUE RÉEL TROUVÉ ET CORRIGÉ en validant contre la base réelle, avant
toute conséquence durable** : les compagnies à numéro québécoises (ex.
"9519-3801 Québec inc." vs "9519-3850 Québec inc.") produisent un score
WRatio élevé (95.0, dans la fourchette de fusion AUTOMATIQUE) alors que ce
sont des entités légalement DISTINCTES — le matricule numérique est
l'identifiant réel, la similarité de chaînes de caractères est
structurellement trompeuse ici (la partie commune "Québec inc." domine le
score). Repéré immédiatement après un premier passage contre la base réelle
(une fusion incorrecte avait déjà été appliquée) — base restaurée depuis la
sauvegarde AVANT toute autre conséquence, garde-fou ajouté
(`falkye/dedup_entreprises.py::_numero_entreprise` — deux noms de compagnie
à numéro ne sont jamais comparés par similarité floue, seule une
correspondance EXACTE du matricule compte), testé (3 tests dédiés), puis
seulement ensuite réappliqué contre la base réelle. Voir docs/STATUT_
RESEAU.md pour le récit complet et les résultats réels après correction.

Ingestion (`falkye/resolution.py::resolve_company`) : après un échec de
correspondance exacte, tente le rapprochement flou AVANT de créer une
nouvelle fiche — >=95 ancre directement sur l'existant (aucune nouvelle
fiche, aucun journal — rien à fusionner, juste un routage correct dès le
départ) ; 90-95 crée quand même la nouvelle fiche MAIS journalise un
candidat. Passe par lot rétroactive (`falkye scan detecter-doublons`,
RÉSERVÉE AU MODE OPÉRATEUR — contrairement à `scan detecter-expansions`,
jamais destructif, cette commande peut supprimer de vraies fiches, jamais
greffée automatiquement sur `scan veille`) pour rattraper les doublons déjà
présents. Idempotent des deux côtés.

### Point 5 — rétroaction ciblée sur la sphère précise

**Déjà correct, confirmé par lecture de code — aucun changement requis.**
`falkye/retroaction.py::enregistrer_pas_pertinent` réduisait déjà
uniquement le poids de `notification.sphere_probable_id`, qui EST déjà la
sphère précise choisie par `meilleure_sphere_pour_match` (chantier
précédent) parmi toutes celles liées au besoin — jamais toutes les sphères
liées. `falkye/pertinence.py::calculer_pertinence` applique ce poids
uniquement à la base de correspondance de CETTE sphère (`base_match_pour_
sphere(m, sphere_choisie, ...)`), jamais aux autres bonus.

### Point 6 — plusieurs "qui" par besoin

**Premier volet déjà construit et déjà correct** (chantier précédent) :
`ProfileNeedClientCible` (N:N), `profile lier-client-cible` (plusieurs
liens possibles), et `bonus_et_redirection_qui` (bonus dès qu'AU MOINS un
"qui" lié matche ; désaccord confiant seulement si l'INTERSECTION avec
TOUS les "qui" liés est vide) satisfont déjà exactement ce qui était
demandé. Rien à coder.

**Deuxième volet, nouveau** : `_CONTEXTE` dans `falkye/assistance_client_
cible_ia.py` (déjà un paramètre distinct de celui de la sphère) reçoit une
instruction additionnelle — si la description correspond à une très large
proportion des catégories du catalogue, le Niveau 2 retourne directement
`aucune_restriction` seule plutôt qu'une longue liste de liens. Portée
volontairement limitée au Niveau 2 (formulation d'Alexandre : "si l'IA
détecte...") — le Niveau 1 (mots-clés, aucun raisonnement) garde son
comportement actuel.

### Point 7 — vérification globale ponctuelle

Sweep ciblé (grep sur les ids/noms de sources connus à travers `cli.py`,
`formatter.py`, `synthese.py`, `carte.py`, `premier_contact.py`,
`notifications/*.py`) — au-delà des deux cas du point 3, rien d'autre
trouvé. `signal.champs.get("donneur_ordre")` dans `premier_contact.py`
n'est PAS une fuite : c'est une DONNÉE du signal (le nom du donneur d'ordre
réel, partie du contenu détecté), pas un nom de source.

## Quarantaine de diff — état/schéma/volume (Chantier 1, audit et mandat du 2026-09-03/04, faille E)

**Le problème que ce chantier corrige.** Une source de type `instantane`
(aucune date d'événement fiable par ligne — le signal naît de la
comparaison de deux instantanés successifs) n'avait, avant ce chantier,
AUCUN état conservé de façon générique : chacun des 4 connecteurs actifs de
ce type (REQ, Corporations Canada, licences Toronto/Vancouver) réinvente
son propre miroir BESPOKE et PARTIEL (`REQEntry`/`CorporationFederaleEntry`/
`LicenceMunicipaleEntry`) qui ne fait qu'une chose : décider si une clé
"a déjà été vue" — jamais de détection de disparition, jamais de suivi de
modification, et surtout aucune protection si le fichier source arrive
tronqué ou déformé un jour (perte réseau, changement de schéma du
diffuseur) : une déformation silencieuse se traduirait directement par une
tempête de fausses notifications, avec un risque de crédibilité que le
mandat qualifie explicitement de "à coût croissant" — plus on attend, plus
la probabilité cumulée d'un tel incident augmente sans qu'aucun garde-fou
n'existe pour l'intercepter.

**Ce que ce chantier construit, et ce qu'il ne touche PAS.** Un moteur de
diff générique (`falkye/diff_engine.py`) qui GÉNÉRALISE le mécanisme
bespoke des 4 connecteurs existants sans les remplacer — remplacer
effectivement REQ/Corporations Canada dans ce chantier toucherait à la
résolution NEQ/identité (territoire du chantier 3, signalé plutôt que
franchi) ; remplacer licences_toronto/vancouver perdrait leur fetch
incrémental (`since`-filtrable, efficace) au profit d'un instantané complet
à chaque exécution, un changement de comportement de production hors de la
portée "construire et valider le moteur" de ce chantier. Les 4 connecteurs
restent donc inchangés en production ; le moteur est validé de façon
EXTERNE, contre de vraies données réelles (voir "Macro-vérification"
ci-dessous), et `registry/sources.yaml` porte déjà les 3 nouveaux champs
(`type_ingestion`, `cle_naturelle`, `seuils_quarantaine`) pour ces 4
sources, prêt pour le branchement futur.

### Modèle de données

- **`EtatLigneSource`** (`falkye/models/etat_diff_source.py`) : l'état
  COURANT d'une source de type `instantane`, une ligne par clé naturelle —
  PAS un historique de copies complètes (l'état courant suffit pour un
  diff au prochain run). Empreinte (`empreinte`, sha256) calculée
  UNIQUEMENT sur les champs pertinents (`SourceDef.champs_pertinents`),
  jamais la ligne brute entière — un changement cosmétique hors de cette
  liste (espace, colonne inutilisée, réordonnancement) ne doit jamais
  produire un faux "modification". Une disparition SUPPRIME la ligne
  (pas un statut "disparu") — une réapparition plus tard est légitimement
  une NOUVELLE apparition, jamais un cas spécial.
- **`EtatSchemaSource`** : les colonnes vues au dernier run réussi (nom →
  type déclaré, best-effort) — seule source de vérité pour "cette source
  a-t-elle déjà tourné" (`run_reference = (EtatSchemaSource absent)`) ET
  pour la détection de changement de schéma.
- **`DiffQuarantaine`** (`falkye/models/diff_quarantaine.py`) : un
  incident. `detail` (JSON) conserve le DIFF CALCULÉ EN ENTIER au moment
  de la mise en quarantaine (pas seulement des statistiques) — décision
  délibérée : "lever" une quarantaine applique ce diff TEL QUEL, jamais une
  nouvelle collecte contre la source (qui pourrait avoir changé entre
  temps). Une archive JSON brute du run (`chemin_archive`, rotation sur
  `GENERATIONS_CONSERVEES = 5`) permet l'inspection post-mortem même au-delà
  de ce qui est gardé en base.

### `falkye/diff_engine.py` — le moteur

Point d'entrée unique : `executer_diff(db_session, source_id, lignes,
colonnes_vues, champs_pertinents, seuils=None, taux_erreur_lecture=0.0,
seuil_erreur_lecture=0.05) -> RapportExecution`. Ordre des vérifications,
chacune un garde-fou non négociable du mandat :

1. **Échec de lecture** (`taux_erreur_lecture` — calculé par l'APPELANT,
   ce module ne lit aucun fichier) au-delà du seuil → quarantaine
   immédiate (`LECTURE_ECHOUEE`), avant même la comparaison de schéma ou de
   contenu.
2. **Run de référence** (`EtatSchemaSource` absent pour cette source) →
   amorce l'état intégralement, **n'émet aucun candidat, ne peut jamais
   déclencher la quarantaine** (100% d'apparitions y est normal, pas une
   aberration).
3. **Changement de schéma** — colonne PERTINENTE retirée ou dont le type
   déclaré change (comparé contre `EtatSchemaSource.colonnes` du run
   précédent) → quarantaine **immédiate, quel que soit le volume du diff**.
   Colonne AJOUTÉE → avertissement seul, jamais de quarantaine (les
   diffuseurs ajoutent des colonnes couramment). Une colonne RENOMMÉE est,
   par construction, indistinguable d'un retrait + ajout — le retrait
   l'emporte, décision assumée du mandat plutôt qu'une heuristique de
   renommage fragile.
4. **Diff de contenu** — trois ensembles TOUJOURS séparés (`apparitions`,
   `disparitions`, `modifications` — cette dernière portant la liste des
   champs qui ont changé), jamais fusionnés. Ce sont des CANDIDATS, pas des
   notifications : le reste du pipeline (résolution d'identité, score,
   pertinence, routage) reste entièrement hors de ce chantier.
5. **Règle de quarantaine sur le volume** — DEUX seuils (pourcentage ET
   absolu) doivent être franchis ENSEMBLE pour CHAQUE type d'écart,
   jamais un seuil unique global : le pourcentage seul mettrait en
   quarantaine les petites sources sur du bruit normal, l'absolu seul ne
   verrait rien venir sur les grosses. Seuils par défaut
   (`SEUILS_DEFAUT`), surchageables par source dans `registry/sources.yaml`
   (`SourceDef.seuils_quarantaine`) : apparitions 50%/500, **disparitions
   30%/300 (volontairement plus bas)** — une disparition massive est plus
   suspecte qu'une explosion d'apparitions (signale généralement un
   extrait tronqué, la panne la plus probable), modifications 50%/500.
6. **Diff accepté** → archive le snapshot, applique l'état
   (`_appliquer_diff`), retourne le `ResultatDiff`.

**Insertion en LOT, pas un `db_session.add()` ORM par ligne.** Découverte
réelle en macro-vérifiant ce moteur contre le vrai volume REQ (2,7M
lignes, voir plus bas) : la première implémentation (un objet ORM par
ligne, ajouté au unit-of-work de la session) faisait exploser la mémoire
bien avant la fin de l'insertion à cette échelle (~9,6 Go observés, tué
avant complétion). Corrigé par `_inserer_lignes_en_lot` (SQLAlchemy Core,
`insert()` par lots de `TAILLE_LOT_INSERTION = 5000` dicts bruts, jamais
d'objet ORM par ligne) pour le run de référence ET les apparitions — seuls
chemins qui touchent potentiellement la POPULATION COMPLÈTE d'une source.
La lecture de l'état précédent (`etats_precedents`, comparé pour calculer
le diff) suit le même principe : colonnes Core plutôt que des instances
ORM complètes, cette lecture aussi portant sur la population complète à
CHAQUE run non-référence. Les mutations ciblées (modifications,
disparitions) restent en ORM ligne par ligne — leur volume est celui du
DIFF, pas de la population, sans commune mesure. Limite honnête qui reste,
documentée ici plutôt que glissée sous silence : `etats_precedents` est
tout de même chargé intégralement en mémoire (comme dict Python) à chaque
run non-référence — un choix qui tient jusqu'à plusieurs millions de
lignes par source (validé contre REQ, la plus grosse source réelle du
projet) mais qui redeviendrait un problème avec un ordre de grandeur
supplémentaire ; une diffusion côté base de données serait le prochain
palier si jamais nécessaire, hors de la portée de ce chantier.

### Section 11 du mandat — les deux réponses implémentées telles quelles

1. **Deux sources en quarantaine dans la même exécution.** La quarantaine
   reste STRICTEMENT par source (deux incidents indépendants — aucun des
   deux ne bloque le pipeline de l'autre, testé explicitement :
   `test_source_en_quarantaine_n_empeche_pas_une_autre_source_de_publier`).
   Mais le CUMUL est lui-même un signal :
   `suspicion_incident_local(rapports) -> bool` (seuil
   `SEUIL_QUARANTAINES_SIMULTANEES_SUSPECT = 2`) — deux diffuseurs
   indépendants qui changent leur format le même jour est improbable, deux
   quarantaines simultanées pointent bien plus vraisemblablement vers un
   problème DE NOTRE CÔTÉ (réseau, disque, déploiement récent, dépendance
   mise à jour). Fonction pure, prête à être branchée par un futur
   orchestrateur de veille multi-sources (hors de ce chantier — les 4
   connecteurs réels ne sont pas encore rebranchés sur ce moteur).
2. **Source en quarantaine touchant une entité déjà corroborée par une
   source saine.** Résolu STRUCTURELLEMENT, pas par une règle
   supplémentaire à respecter : un run en quarantaine a toujours
   `RapportExecution.resultat = None`, et `EtatLigneSource`/
   `EtatSchemaSource` ne sont JAMAIS touchés — les données de ce run ne
   peuvent donc, par construction, atteindre AUCUNE étape de candidat, de
   score ou de corroboration en aval, puisqu'aucun candidat n'est jamais
   produit (testé :
   `test_run_en_quarantaine_ne_produit_aucun_candidat_ni_etat`, état
   byte-identique avant/après). Rétracter un signal déjà publié par une
   source ensuite jugée mauvaise est le territoire du chantier 2, jamais
   attaqué ici.

### Clé naturelle par source — jamais devinée, déclarée dans le registre

Décision structurante par source, chacune justifiée par une propriété
RÉELLE du jeu de données (`registry/sources.yaml`,
`SourceDef.cle_naturelle`) :

- **REQ** : `neq` — identifiant stable et unique par entreprise.
- **Corporations Canada** : `numero_corporation_federale` — idem.
- **Licences Toronto** : `identifiant_licence` (le "Licence No.") —
  confirmé PERSISTANT (0 doublon sur échantillon réel). Une même
  entreprise peut obtenir plusieurs numéros successifs au fil des
  décennies ; chacun est, pour CE moteur générique, un nouvel identifiant
  de plein droit — le filtrage "pas un simple renouvellement" reste la
  responsabilité du miroir bespoke `LicenceMunicipaleEntry`
  (`falkye/sources/licences_municipales_communes.py`), une préoccupation
  distincte (identité d'établissement) de celle de ce moteur (intégrité de
  la source).
- **Licences Vancouver** : **composite (`nom_entreprise`, `adresse`)**,
  **PAS le numéro de licence** — découverte réelle documentée dans
  `sources.yaml` : Vancouver RÉATTRIBUE un nouveau numéro de licence CHAQUE
  ANNÉE (`folderyear` encodé dedans, ex. "26-258507"). Utiliser ce numéro
  comme clé naturelle ferait apparaître 100% de disparitions + 100%
  d'apparitions à CHAQUE réémission annuelle normale — un comportement
  attendu et bénin de la source, mais qui déclencherait la quarantaine à
  tort à chaque cycle. `nom_entreprise` + `adresse` est l'identifiant
  stable de l'ÉTABLISSEMENT à travers les réémissions — même clé que
  celle déjà utilisée par le mécanisme bespoke
  (`LicenceBrute`/`detecter_nouvelles_licences`, clé `"nom|adresse"`).

### CLI — `falkye quarantaine` (RÉSERVÉ AU MODE OPÉRATEUR)

`quarantaine lister [--statut en_attente|acceptee|rejetee|toutes]`,
`quarantaine inspecter --id N` (détail complet, listes de plus de 10
entrées tronquées à l'écran — l'archive brute reste consultable en
entier), `quarantaine lever --id N --decision acceptee|rejetee --motif
"..." --qui "..."` — action explicite et JOURNALISÉE (qui, quand, motif),
jamais anonyme. `acceptee` applique le diff calculé au moment de la
quarantaine tel quel (jamais une nouvelle collecte) ; `rejetee` conserve
l'état précédent intact. Une quarantaine SCHEMA acceptée amorce le nouveau
schéma comme une référence PARTIELLE — le PROCHAIN run recalcule le vrai
diff de contenu contre ce nouveau schéma, jamais une fusion aveugle avec
l'ancien état.

### Macro-vérification (2026-09-04) — contre les 4 sources actives réelles, pas seulement l'exemple

Exécutée par un script externe jetable (jamais committé), contre une base
SQLite JETABLE (jamais la base réelle) — les 4 connecteurs de production
restent inchangés, comme décidé plus haut. Pour REQ et Corporations
Canada, les données proviennent des miroirs déjà réels dans
`data/falkye.sqlite3` (issus d'imports réels antérieurs) ; pour les
licences Toronto/Vancouver, tirées EN DIRECT des vrais portails via les
mêmes fonctions `iter_licences()` que les connecteurs réels de production
(aucune modification de ces connecteurs).

| Source | Clé naturelle | Lignes réelles amorcées | Run 1 (référence) | Run 2 (vrai diff réel) |
|---|---|---|---|---|
| REQ | `neq` | 2 726 312 (miroir réel, import manuel) | amorce l'état, 0 candidat, 59,8s | 2e run sur les MÊMES données (aucun 2e fichier disponible) : 0/0/0, idempotent, 90,8s |
| Corporations Canada | `numero_corporation_federale` | 694 844 (miroir réel) | amorce l'état, 0 candidat, 18,1s | idem : 0/0/0, idempotent, 21,4s |
| Licences Toronto | `identifiant_licence` | 37 501 lignes brutes tirées EN DIRECT (licences actives seulement, `Cancel Date` vide — sur ~159 700 lignes historiques totales depuis 1946), 3 clés dupliquées dédoublonnées (37 498 amorcées) — voir "bogue réel trouvé" ci-dessous | amorce l'état, 0 candidat, 13,9s de collecte | 2e tirage EN DIRECT ~15s plus tard (37 501 lignes) : 0/0/0, idempotent — cohérent, aucune nouvelle licence émise dans cette fenêtre |
| Licences Vancouver | `(nom_entreprise, adresse)` | 10 000 lignes brutes (plafond de pagination Opendatasoft réel, voir sources.yaml) | amorce l'état, 0 candidat | 2e tirage EN DIRECT : 0/0/0, idempotent |

**Bogue réel trouvé et corrigé en macro-vérifiant contre Toronto** : ~0,5%
des lignes brutes du jeu de données portent une clé naturelle
(`Licence No.`) STRICTEMENT dupliquée (lignes identiques en tout point —
un défaut de qualité réel du jeu de données CKAN, pas une erreur du
connecteur ni un signe que `identifiant_licence` est un mauvais choix de
clé). Le run de référence insérait alors la liste `lignes` BRUTE (non
dédoublonnée) dans l'INSERT en lot, qui — contrairement à un ORM `add()`
par ligne — rejette le lot ENTIER dès la première violation de la
contrainte UNIQUE (`source_id`, `cle_naturelle`) : **premier run réel
contre Toronto, plantage immédiat.** Corrigé (`executer_diff` insère
désormais `lignes_par_cle.values()`, jamais `lignes` brut — dédoublonné
AVANT l'INSERT, avec un avertissement journalisé sur le nombre de doublons
rencontrés) ; régression ajoutée
(`test_run_reference_avec_cles_dupliquees_dedoublonne_sans_lever_d_erreur`).
Exactement le type de découverte que la macro-vérification contre de
vraies données existe pour attraper avant "considérer le mécanisme
terminé" — un jeu de test synthétique n'aurait jamais pensé à ce cas.

**Seuils de quarantaine — proposition, à valider avec Alexandre, pas une
constante enfouie.** Les 4 sources gardent `SEUILS_DEFAUT` (aucune
surcharge dans `sources.yaml` à ce jour) : les deux runs réels de chaque
source étant rapprochés dans le temps (REQ/Corporations Canada : même
fichier comparé à lui-même — aucun deuxième import réel disponible ;
Toronto/Vancouver : ~15-20 secondes d'écart entre deux tirages), le diff
observé est 0/0/0 partout — un run réel ESPACÉ dans le temps (jours ou
semaines) serait nécessaire pour observer un vrai volume d'écart et
calibrer un seuil PROPRE à chaque source. Observation utile en attendant :
à l'échelle réelle des 4 sources (37 498 à 2 726 312 lignes), le seuil
ABSOLU (300) ne devient jamais le facteur limitant — il faudrait un écart
de 30% ou plus pour l'atteindre, largement au-dessus de 300 lignes à ces
volumes ; l'absolu protège surtout les PETITES sources hypothétiques
futures (RACJ, établissements alimentaires Montréal — pas encore
construites), pas les 4 sources actuelles. Recommandation : garder
`SEUILS_DEFAUT` tel quel pour l'instant, recalibrer par source une fois un
vrai historique de runs espacés accumulé (chantier futur, pas celui-ci).

Les 3 nouvelles tables (`etat_ligne_source`, `etat_schema_source`,
`diff_quarantaines`) ont été créées dans la base réelle
(`falkye/db.py::init_db()`, additif — aucune autre table touchée) ; elles
restent VIDES en production tant que les 4 connecteurs ne sont pas
effectivement rebranchés sur ce moteur (hors de ce chantier).

### Suivi d'Alexandre au premier livrable (2026-09-04) — dédoublonnage déterministe, historique de diff, prudence de début de vie, propositions de seuils

Quatre demandes, toutes tranchées et implémentées avant tout rebranchement
de connecteur (voir plus bas pour la réponse à la question de conservation
d'état, posée en préalable explicite).

**1. Dédoublonnage déterministe.** L'implémentation d'origine
(`{l.cle: l for l in lignes}`) retenait la DERNIÈRE ligne rencontrée en cas
de clé naturelle dupliquée — un choix qui dépend de l'ORDRE du fichier
source, susceptible de changer d'une semaine à l'autre (pagination, tri
interne du diffuseur) et de produire une fausse "modification" au diff
suivant sans qu'aucune donnée n'ait réellement bougé. Corrigé
(`falkye/diff_engine.py::_dedoublonner_lignes`) : la ligne retenue par
groupe de clé est celle dont l'EMPREINTE (sha256 des champs pertinents) est
lexicographiquement la plus grande — une fonction PURE DU CONTENU, jamais
de la position dans `lignes`, donc strictement le même résultat quel que
soit l'ordre d'arrivée. Distingue au passage deux cas, comptés séparément
et journalisés : doublons IDENTIQUES (contenu strictement identique — cas
réel observé chez Toronto, sans conséquence) et doublons DIVERGENTS
(contenu différent pour la même clé — jamais observé à ce jour, mais
signe d'une ambiguïté réelle sur la clé naturelle déclarée pour cette
source si ça arrivait).

**2. `DiffRunHistorique`** (`falkye/models/diff_run_historique.py`) — une
ligne PAR APPEL à `executer_diff`, quel que soit le chemin de sortie, pas
seulement les incidents (`DiffQuarantaine` continue d'exister pour ça,
inchangée). Objectif direct : « journaliser l'amplitude de chaque diff à
chaque run, même très en dessous du seuil... sans ça, la calibration reste
impossible indéfiniment. » Porte, par run : le nombre et le pourcentage
d'apparitions/disparitions/modifications (même quand aucun seuil n'est
franchi), le taux de doublons de clé naturelle (identiques et divergents
distingués), et les seuils EFFECTIVEMENT appliqués (voir point 3). Nuls
uniquement pour les deux quarantaines qui se déclenchent AVANT tout calcul
de diff (lecture_echouee, schéma) — partout ailleurs, y compris sur un run
de référence (où apparitions = 100% par construction, non signifiant pour
la calibration mais journalisé quand même, pour que l'historique reste
lisible) et sur une quarantaine de VOLUME (le diff est calculé avant
d'être refusé — l'amplitude est connue et journalisée même là).

**3. Prudence de début de vie.** « Tant qu'aucune norme n'existe, la
prudence est de bloquer plus facilement. » Tant qu'une source a moins de
`NB_RUNS_MINIMUM_AVANT_SEUILS_NORMAUX` (5) runs NON-référence journalisés,
les seuils autrement applicables (registre ou `SEUILS_DEFAUT`) sont
RESSERRÉS par `FACTEUR_PRUDENCE_DEBUT` (0.5, soit deux fois plus stricts)
— jamais relâchés, uniquement resserrés, et jamais sur le run de référence
lui-même (qui ne vérifie de toute façon aucun seuil). Le raisonnement de
fond, à conserver pour tout arbitrage futur sur ces valeurs (Alexandre,
2026-09-04) : « une quarantaine injustifiée coûte une levée manuelle, une
quarantaine manquée coûte la confiance de tous les clients le même matin »
— l'asymétrie des coûts justifie de pécher par excès de prudence tant que
le comportement normal d'une source n'a pas encore été observé. Les 5/0.5
sont des valeurs de départ raisonnables, pas calibrées empiriquement (rien
à calibrer contre — même limite que `SEUILS_DEFAUT` lui-même) : à ajuster
si l'usage réel le justifie.

**4. `proposer_seuils`** (`falkye/diff_engine.py`, CLI `falkye quarantaine
proposer-seuils --source-id X`) — une PROPOSITION, jamais une
auto-application : « un seuil qui s'ajuste seul finit par s'élargir
jusqu'à ne plus rien attraper. » Retourne `None` tant que l'historique
non-référence et NON mis en quarantaine d'une source est sous le minimum ;
au-delà, propose pour chaque type d'écart le maximum PCT et ABS observé
parmi les runs NORMAUX (jamais en quarantaine — même ceux ensuite
"acceptés" par un opérateur : une amplitude déjà flaguée comme suspecte ne
doit jamais élargir mécaniquement le seuil futur), multiplié par
`MARGE_SECURITE_PROPOSITION` (1.5) — jamais pile sur le pire cas déjà vu
comme "normal". Écrire la proposition retenue dans `registry/sources.yaml`
reste un geste humain, délibéré, séparé — ce module n'écrit jamais le
registre lui-même.

**Réponse à la question posée en préalable — conservation d'état des 4
sources instantané, avant tout rebranchement.** Les 4 (REQ, Corporations
Canada, licences Toronto, licences Vancouver) conservent bien un état
PERSISTANT aujourd'hui, chacune via son propre miroir bespoke
(`REQEntry`/`CorporationFederaleEntry`/`LicenceMunicipaleEntry`),
`commit()`/`rollback()` TOUT-OU-RIEN par exécution (`falkye/sources/
req.py:_ingest_zip_req_reel`, `falkye/sources/corporations_canada.py:
ingest_snapshot`, `falkye/sources/licences_municipales_communes.py:
detecter_nouvelles_licences` + le `db_session.commit()` final de `falkye/
engine.py::ingest_source`) — un run interrompu perd SA propre progression,
jamais l'état déjà acquis par un run antérieur réussi. Aucune des 4 ne
tourne aujourd'hui sans conservation d'état ; la condition d'urgence
qu'Alexandre avait posée ("si l'une tourne sans conservation d'état,
rebrancher celle-là en priorité") ne s'applique donc à aucune des 4.

En vérifiant ce point, une AUTRE fuite réelle est apparue — orthogonale à
la conservation d'état par source, hors du périmètre de ce chantier,
consignée (`DiagnosticJournal`, `type_diagnostic=probleme_autre_chantier`,
entrée #23) et rapportée plutôt qu'attaquée : `falkye/engine.py::
run_veille_continue` calcule `since = now - lookback_days` (30 jours par
défaut) à CHAQUE exécution, sans jamais consulter le dernier run RÉUSSI —
si l'intervalle réel entre deux exécutions dépasse `lookback_days`, les
événements plus anciens que la fenêtre glissante ne sont jamais rattrapés,
pour TOUTE source filtrable par `since` (pas seulement les 4 instantané).
Une perte irrécupérable au sens de la charte section 14, mais par une voie
différente de celle de ce chantier (fenêtre de fetch jamais élargie pour
rattraper un retard, pas un problème de conservation d'état une fois la
donnée reçue) — territoire d'un futur chantier sur l'ordonnancement des
exécutions, pas celui-ci.

### Rebranchement des 4 connecteurs — la fin réelle du chantier 1 (2026-09-04)

Tant que REQ, Corporations Canada, licences Toronto et licences Vancouver
tournaient encore sur leur ancien chemin bespoke, la quarantaine ne
protégeait rien de réel — le moteur existait, validé, mais hors du chemin
de production. Ce rebranchement ferme cet écart. Priorité posée par
Alexandre : la portée du produit devient prioritairement québécoise —
REQ rebranché en premier (la seule des 4 sources servant directement cette
priorité), puis Toronto/Vancouver/Corporations Canada dans un ordre libre.

**Principe commun aux 4 : deux phases, jamais mélangées.** Phase 1 construit
l'instantané complet (aucune écriture) et le soumet au moteur générique.
Si le run est mis en quarantaine, la phase 2 n'a JAMAIS lieu — le miroir de
résolution (REQEntry/CorporationFederaleEntry, utilisé par TOUTES les
autres sources) reste intact, pas seulement l'absence de signal. Phase 2
(upsert du miroir + dérivation des signaux à partir du `ResultatDiff` déjà
calculé par le moteur) ne s'exécute que si la phase 1 est passée sans
incident.

**REQ — deux grains de diff, jamais fusionnés.** Le REQ produit deux
signaux distincts (changement d'adresse du siège / nouvel établissement
secondaire) à partir de DEUX fichiers CSV joints (Entreprise.csv,
Etablissements.csv) — un schéma cassé dans l'un des deux ne doit jamais
passer inaperçu simplement parce que l'autre est intact. Deux partitions
indépendantes du moteur : `"req"` (grain entreprise, cle_naturelle=neq) et
`"req_etablissements"` (grain établissement, cle_naturelle=neq+no_suf_etab).
`REQEtablissementEntry` — l'ancien miroir bespoke de ce second grain — est
GELÉ (table conservée, plus aucune écriture) : entièrement remplacé par
`EtatLigneSource("req_etablissements")`, qui protège en plus contre un
schéma cassé et un volume aberrant, ce que l'ancien miroir n'a jamais su
faire (voir falkye/models/req_etablissement_entry.py pour le détail).
"secteur_code" est délibérément EXCLU de l'empreinte diffée à ce grain :
l'ancien miroir ne l'a jamais capté, l'inclure aurait fait apparaître une
"modification" sur la quasi-totalité des établissements dès le premier
diff suivant la migration — un faux positif de masse causé par un trou de
données historique, pas un vrai changement (reste capté dans le SIGNAL,
juste hors de l'empreinte comparée).

**Toronto et Vancouver — changement de comportement DÉLIBÉRÉ et ACCEPTÉ.**
`detect()` récupère désormais un INSTANTANÉ COMPLET à chaque exécution
(`since` reçu mais ignoré pour la collecte) plutôt que la fenêtre
incrémentale d'avant — une fenêtre glissante comparée à l'état cumulatif
aurait fait apparaître, à tort, l'essentiel de l'historique comme "disparu"
à chaque exécution (le moteur générique a besoin d'un vrai instantané pour
que ses disparitions/son volume veuillent dire quelque chose). Coût réel
accepté : Toronto passe de quelques milliers de lignes à ~160 000 par
exécution (~14s de collecte, c'est d'ailleurs la source contre laquelle le
moteur a été validé) ; Vancouver reste plafonné à 10 000 lignes (limite
réelle de la plateforme Opendatasoft, inchangée) — mais désormais les 10 000
les PLUS RÉCENTES (`order_by` inversé en descendant pour ce cas précis),
pas les plus anciennes comme l'aurait donné un tri ascendant sans fenêtre.
**Limite honnête qui reste, propre à Vancouver** : le plafond de pagination
(10 000) est bien en deçà de la population réelle (~168 000 licences
actives) — l'instantané soumis au moteur n'est donc jamais complet, la
détection de disparition y reste structurellement affaiblie (une vraie
disparition au-delà des 10 000 plus récentes ne sera jamais vue). Documenté,
pas corrigé ici — lever le plafond appartient au fournisseur de données.

Le filtre bespoke existant (`detecter_nouvelles_licences` — "pas un simple
renouvellement" / "pas un nouveau démarrage" via Corporations Canada) reste
INCHANGÉ, une préoccupation distincte (identité d'établissement) de celle
du moteur générique (intégrité de la source) — appelé désormais APRÈS que
le moteur ait confirmé que le run n'est pas en quarantaine, jamais avant.
Clé du moteur générique, PAR VILLE (voir "clé naturelle par source"
ci-dessus) : Toronto = identifiant_licence (persistant) ; Vancouver =
composite nom+adresse (le numéro y est réattribué chaque année) — les deux
restent distinctes de la clé du filtre bespoke, qui est TOUJOURS nom+adresse
pour les deux villes (une préoccupation d'identité d'établissement, pas
d'intégrité de source).

**Migration de l'état existant, jamais un run de référence gaspillé** — les
mandats explicites : REQEntry (2 726 312 lignes réelles), REQ
Etablissements (236 311), CorporationFederaleEntry (694 844) migrés vers
`EtatLigneSource` via le mécanisme de run de référence du moteur, mais
nourri de données RÉELLES déjà accumulées plutôt que de repartir de zéro.
Toronto/Vancouver n'avaient rien à migrer (aucun miroir générique
antérieur) — leur premier appel réel EST le run de référence.

**Validation macro réelle (2026-09-04, `falkye.engine.ingest_source` — le
vrai point d'entrée de production, pas un appel isolé au connecteur) :**

| Source | 1er appel réel | 2e appel réel (diff observé) |
|---|---|---|
| REQ (`req` + `req_etablissements`) | *(déjà migré — voir ci-dessus)* | `run_reference=False quarantaine=False` apparitions=0 disparitions=0 modifications=0 (re-soumission des mêmes données réelles migrées — aucun fichier neuf disponible dans cet environnement, voir plus bas) |
| Toronto | run de référence : erreur=None, 4117 signaux (filtre bespoke, ~160k lignes), 2395s | `run_reference=False` : erreur=None, **17 signaux**, 87s |
| Vancouver | run de référence : erreur=None, 253 signaux (10 000 lignes, plafond atteint), 208s | `run_reference=False` : erreur=None, **0 signal**, 37s |
| Corporations Canada | *(déjà migré — voir ci-dessus)* | `run_reference=False` : erreur=None, **0 signal**, 292s (~695k corporations comparées) |

Toronto et Vancouver n'avaient aucun état préalable : leur 1er appel réel EST
nécessairement leur run de référence (comportement du moteur, pas un choix)
— le 2e appel, quelques minutes plus tard sur les mêmes populations réelles,
est le premier vrai diff. REQ et Corporations Canada étaient déjà migrés
(voir plus haut) : leur unique appel réel de cette validation est donc
directement un diff réel, pas un amorçage.

**Deux bugs réels trouvés — et corrigés — PENDANT cette validation (pas
avant) :**

1. **Corporations Canada — doublon linguistique CKAN.** Le jeu de données
   publie chaque ressource "active" en français ET en anglais, mêmes
   corporations, MÊME nom de ressource dans les deux langues (le filtre par
   nom ne peut pas les distinguer). Le premier appel réel a planté
   (`ValueError: Colonnes introuvables`) sur les en-têtes anglaises, que
   `COLUMN_ALIASES` (délibérément français-only) ne reconnaît pas. Corrigé
   par `_filtrer_langue_francaise` (`falkye/sources/corporations_canada.py`),
   basé sur le champ `language` fourni par CKAN (`['fr']`/`['en']`, vérifié
   en direct) — sans ce correctif, une extension naïve de `COLUMN_ALIASES`
   à l'anglais aurait plutôt doublé chaque corporation. 2 nouveaux tests.
2. **Corporations Canada — colonnes_vues erronées dans le script de
   migration.** Le script de migration ponctuel (`migrer_corp.py`, non
   committé) a construit `colonnes_vues` à partir de `CHAMPS_PERTINENTS_CORP`
   au complet, incluant à tort `date_incorporation` — un champ que le
   connecteur réel n'a JAMAIS extrait du vrai fichier (aucune colonne
   fiable de date de constitution n'existe dans les en-têtes réelles,
   documenté depuis le 2026-08-31). Le premier appel réel post-migration a
   donc vu `date_incorporation` comme une colonne "retirée" et mis la
   source en quarantaine à tort (`schema_colonne_retiree`). Corrigé en
   alignant directement l'`EtatSchemaSource` stocké sur les 5 colonnes que
   le connecteur réel produit effectivement (pas de nouveau run de
   référence nécessaire — seul le schéma enregistré était faux, pas les
   2 726 312+ lignes migrées).

Aucun des deux bugs ne vient d'un changement de comportement du moteur de
diff générique lui-même — les deux sont des erreurs d'intégration propres
à Corporations Canada, trouvées précisément PARCE QUE cette validation
exigeait un vrai appel réseau réel plutôt qu'une exécution simulée.

**Limite d'environnement, pas de conception :** aucun fichier REQ neuf
n'est disponible dans ce conteneur pour un deuxième import réellement
distinct (le fichier original a été téléchargé et consommé dans une
session antérieure, absent de l'environnement actuel — confirmé par
recherche exhaustive sur le système de fichiers). La validation REQ
ci-dessus re-soumet donc les données réelles déjà migrées une seconde
fois — un diff authentique et non trivial (le moteur compare réellement
2 726 312 + 236 311 lignes à leur état stocké), mais idempotent par
construction plutôt que reflétant un changement réel du registre depuis la
migration. À corriger dès qu'un fichier REQ neuf redevient disponible.

### Le moteur refuse l'émission en run de référence — correction portée dans `executer_diff` (2026-09-04, suite du chantier 1)

En clarifiant avec Alexandre le comportement du "run de référence" observé
sur Toronto/Vancouver (voir `docs/STATUT_RESEAU.md`, "Suite du chantier 1"),
un principe de conception s'est révélé absent du contrat du moteur
générique : **`executer_diff` garantissait que SON PROPRE calcul
(apparitions/disparitions/modifications) était vide au premier run d'une
source — mais ne garantissait RIEN sur ce qu'un connecteur faisait AVEC ce
résultat.** REQ et Corporations Canada respectaient quand même le critère
"aucun signal au run de référence" (mandat chantier 1, premier critère
d'acceptation), mais seulement parce que leurs statistiques étaient
explicitement dérivées de `rapport.run_reference`/`rapport.resultat`.
Toronto/Vancouver ne le faisaient pas : leur filtre bespoke
(`detecter_nouvelles_licences`) s'exécutait inconditionnellement dès que le
moteur confirmait l'absence de quarantaine, avec sa PROPRE notion
indépendante de "premier scan" (état d'un mirror bespoke, pas de
`EtatSchemaSource`) — ce qui a produit de vrais signaux lors du premier
appel du moteur générique, parce que ce mirror bespoke portait déjà un
historique réel antérieur à ce chantier.

**Un premier correctif documentaire (exiger que chaque connecteur vérifie
`rapport.run_reference` lui-même) a été jugé insuffisant par Alexandre :**
« Aucun connecteur ne devrait avoir à vérifier `rapport.run_reference`
lui-même. » Corrigé pour de vrai dans le moteur plutôt que dans la
discipline des connecteurs :

- `executer_diff(..., apres_diff_accepte=callback)` : `callback` EST la
  logique de publication du connecteur (filtre bespoke inclus), et le
  moteur ne l'invoque QUE sur le chemin de diff réellement accepté — jamais
  sur un run de référence, jamais sur une quarantaine, quel qu'en soit le
  motif. Un connecteur qui passe sa logique de publication par ce paramètre
  ne peut structurellement plus émettre de signal en dehors de ce chemin,
  peu importe ce que son propre code vérifie ou ne vérifie pas.
- `executer_diff_groupe(db_session, specs: list[SpecificationDiff],
  apres_diff_accepte=callback)` : pour un connecteur multi-grain (REQ :
  "req" + "req_etablissements"), soumet plusieurs grains liés sous UNE SEULE
  décision conjointe — le callback n'est invoqué que si TOUS les grains
  sont simultanément acceptés. Sans ça, un connecteur qui recomposerait
  lui-même "quarantaine_a OU quarantaine_b" pourrait s'y tromper — REQ le
  faisait déjà correctement à la main, mais rien ne le garantissait pour un
  futur troisième grain.
- **Verrouillé par test** (`tests/test_diff_engine.py`) : le callback n'est
  jamais invoqué sur les quatre chemins de sortie sans publication
  (référence, quarantaine lecture/schéma/volume), et invoqué exactement une
  fois sur le chemin accepté — au niveau du moteur lui-même, indépendamment
  de tout connecteur particulier.

**REQ migré vers cette API** (`falkye/sources/req.py::_ingest_zip_req_reel`,
via `executer_diff_groupe` — la dérivation de signaux vit maintenant dans
`_deriver_signaux_req`, appelée uniquement par le callback). Corrige au
passage un bogue latent jamais manifesté en pratique : avant cette
migration, le grain établissement dérivait ses signaux dès que LUI-MÊME
n'était pas un run de référence, indépendamment du grain entreprise — si le
grain entreprise avait été en référence (ou en quarantaine) pendant que le
grain établissement ne l'était pas, `neq_nouvelles_entreprises` serait
retombé sur un ensemble vide (faute de `rapport_entreprise.resultat`), et
TOUS les établissements auraient été pris à tort pour "secondaires d'une
entreprise déjà connue". La décision conjointe de `executer_diff_groupe`
empêche structurellement ce cas.

**Toronto/Vancouver/Corporations Canada NON migrés** — cohérent avec leur
mise en veilleuse (`docs/STATUT_RESEAU.md`) : "aucun correctif prévu" tant
que la portée reste québécoise. Leur ancien code (vérification manuelle de
`rapport.quarantaine` uniquement, jamais `run_reference`) reste en place tel
quel — non exécuté puisque ces sources ne sont plus ordonnancées, mais non
retouché non plus.

**Règle à appliquer dès la construction de tout futur connecteur instantané
(RACJ, établissements alimentaires Montréal — les deux prochaines sources
de ce type) :** passer la logique de publication (bespoke ou non) par
`apres_diff_accepte`/`executer_diff_groupe`, jamais par une vérification
manuelle de `rapport.run_reference` dans le connecteur.
