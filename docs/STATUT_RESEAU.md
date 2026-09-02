# FALKYE — Statut réseau et découvertes

Document de suivi demandé par le README de démarrage ("Si tu découvres le
contraire en creusant, dis-le") et par la décision produit du 2026-08-31 de valider
le pipeline avec de vraies données, sans compromis. Mis à jour au fil des tests.

## Domaines requis pour les 3 sources actives + REQ

L'environnement cloud (`Default`, accès réseau `Custom`) doit autoriser :

| Domaine | Pourquoi | État (2026-08-31) |
|---|---|---|
| `www.donneesquebec.ca` | Portail CKAN — SEAO + REQ (métadonnées et fichiers SEAO) | ✅ Accessible, validé avec de vraies données (voir plus bas) |
| `open.canada.ca` | Portail CKAN — Guichet-Emplois (métadonnées) | ✅ Accessible |
| `www.registreentreprises.gouv.qc.ca` | Fichier de données réel du REQ (le CKAN de donneesquebec.ca n'héberge que les métadonnées, le fichier est servi par ce domaine) | ✅ Accès réseau autorisé, mais **le serveur d'origine renvoie une erreur "utilisation excessive"** — voir section REQ ci-dessous, ce n'est pas un problème d'allowlist |
| `opencanada.blob.core.windows.net` | Le téléchargement CSV du Guichet-Emplois redirige (302) vers ce compte de stockage Azure — découvert seulement à l'exécution, pas visible dans les métadonnées CKAN de premier niveau | ✅ Accessible (confirmé le 2026-08-31) — sert aussi EIMT, les subventions fédérales, et les contrats fédéraux (même infrastructure), sans ajout supplémentaire |
| `d4bf66bykfyaf.cloudfront.net` | Fichiers CSV réels de Corporations Canada (AWS CloudFront) — le CKAN de open.canada.ca n'héberge que les métadonnées | ✅ Accessible (autorisé et validé avec de vraies données le 2026-08-31 — voir plus bas) |
| `www.investquebec.com` | PDF de la liste de divulgation Investissement Québec | ✅ Accessible (autorisé et validé avec de vraies données le 2026-08-31 — voir plus bas) |

**Note technique** : contrairement à l'accès `Trusted` par défaut, l'accès `Custom`
s'est appliqué **sans redémarrage de session** — les domaines ajoutés ont
fonctionné immédiatement après leur ajout par l'utilisateur, dans la même session.

## SEAO — validé de bout en bout avec de vraies données

Testé le 2026-08-31 : découverte des ressources via CKAN (`package_show` sur
`systeme-electronique-dappel-doffres-seao`), téléchargement du fichier hebdomadaire
le plus récent (`hebdo_20260817_20260823.json`, ~16.7 Mo), parsing OCDS réel réussi.
Exemple de signal réel extrait :

```
Entreprise : SOCIÉTÉ DE MISE EN VALEUR DE LA MAISON O'NEILL ET DE SON SITE
Donneur d'ordre : Ville de Québec
Valeur : 45 990 $ CAD
Description : Programmation de concerts estivaux sur la scène extérieure...
```

800 signaux ingérés en ~3 secondes après correction d'un problème de performance
(résolution NEQ non indexée — voir plus bas).

## REQ — connecteur validé pour la découverte, bloqué pour le téléchargement (rate-limit d'origine)

`package_show` fonctionne (jeu de données "Registre des entreprises", 2 ressources :
le fichier ZIP de données et le guide d'utilisation PDF). Mais le fichier lui-même
est servi par `www.registreentreprises.gouv.qc.ca` via un endpoint dynamique
(`FichierDonneesOuvertes.aspx`), protégé par Cloudflare, qui renvoie
systématiquement (essayé à plusieurs reprises, à des heures et des jours
différents) :

> "L'accès à nos services vous est temporairement interdit en raison d'une
> utilisation excessive."

**Vérifié le 2026-08-31 (suite à une question directe) : ce n'est PAS une requête
par entreprise qui cause ce blocage.** Audit du code (`grep` sur tous les appels
réseau du projet) : `falkye/sources/req.py::ingest_snapshot` fait **une seule
requête HTTP par exécution**, vers la ressource ZIP en vrac découverte
dynamiquement via `package_show` (jamais une URL codée en dur) — exactement la
méthode prévue par la spec section 7 ("fichier en vrac de Données Québec, mis à
jour deux fois par mois"). `resolve_neq_by_name` et `get_by_neq`, utilisées par
TOUTES les autres sources pour la résolution NEQ, n'interrogent QUE le miroir
local (`REQEntry`, une table SQLite) — zéro appel réseau par entreprise, nulle
part dans le pipeline. `registreentreprises.gouv.qc.ca` n'est en fait sollicité
qu'à un seul endroit dans tout le code : ce téléchargement unique du fichier en
vrac.

Un bug distinct (corrigé au passage, sans lien avec le blocage) : le filtre
`format_filter="CSV"` ne correspondait jamais au format réel de la ressource
(`ZIP`), donc le code retombait sur "toutes les ressources" — ce qui aurait
tenté de traiter le PDF du guide comme un CSV. Corrigé pour cibler `ZIP`
explicitement.

**CORRIGÉ le 2026-08-31 (suite à une question précise d'Alexandre)** — l'analyse
précédente ("mes propres appels curl répétés") ne résiste pas à l'examen des
preuves brutes. Cinq tentatives réelles capturées sur ~13 heures :

| Heure (UTC) | IP sortante (rapportée par le serveur) | Résultat |
|---|---|---|
| 02:50:10 | 160.79.106.**129** | 403, message identique |
| 02:50:43 | 160.79.106.**128** | 403, message identique |
| 02:58:29 | 160.79.106.**137** | 403, message identique |
| 03:03:06 | 160.79.106.**129** | 403, message identique |
| 15:48:45 | 160.79.106.**136** | 403, message identique |

Deux faits qui pointent vers une **cause d'infrastructure partagée, pas notre
volume de requêtes** :
1. **L'IP de sortie change à chaque tentative** (128/129/136/137, même plage
   /28 environ) — signature d'un pool d'adresses partagé entre plusieurs
   sessions/tenants cloud, pas une IP dédiée à cette session.
2. **La toute première tentative (02:50:10, avant tout essai répété)** a déjà
   échoué avec ce même message — le blocage était présent dès le premier
   contact, pas apparu après une accumulation de requêtes de notre part
   (5 tentatives en tout sur 13h, un volume trivial).

**Cause la plus probable** : une règle Cloudflare ciblant la plage/l'ASN
d'adresses infonuagiques partagées (ou un pool visé par le trafic d'autres
sessions/tenants), pas un rate-limit déclenché par ce projet. Décision : ne
pas insister par des tests répétés (déjà appliqué) ; une seule tentative
espacée par le connecteur réel reste sûre. À réessayer plus tard, à faible
fréquence ; si le blocage persiste au-delà de la Phase 1, envisager de
contacter le Registraire des entreprises pour un accès non bloqué (ou signaler
la plage IP infonuagique bloquée), ou de générer le fichier depuis un réseau
différent (hors du pool cloud) puis de l'importer dans l'environnement.

**Impact sur la Phase 1** : le connecteur REQ (`falkye/sources/req.py`) est
codé et couvre le format attendu (voir la mise en garde sur le schéma CSV non
confirmé dans le fichier lui-même), mais n'a pas pu être validé avec le fichier réel
avant la remise de cette phase. Sans REQ chargé, toute entreprise détectée par une
autre source reste `non_trouve` et est donc **exclue silencieusement**, comme
prévu par les vérifications de base (spec section 6) — comportement vérifié : 646
entreprises détectées par SEAO, 0 notification produite, exactement le
comportement attendu en l'absence de résolution NEQ. Le pipeline est donc sûr même
sans REQ ; il n'est simplement pas encore démontré avec une notification positive
réelle.

## Guichet-Emplois — téléchargement validé, DÉCOUVERTE BLOQUANTE : pas de nom d'employeur dans le fichier

`package_show` fonctionne (jeu de données `ea639e28-c0fc-48bf-b5dd-b8899bd43072`,
86 ressources — un CSV FR + EN par mois). `opencanada.blob.core.windows.net`
maintenant autorisé (voir tableau plus haut) : téléchargement réel réussi le
2026-08-31 (fichier de juillet 2026, ~53 Mo, `job-bank-open-data-all-job-postings-fr-juillet2026.csv`).

Deux problèmes trouvés en inspectant le vrai fichier :

1. **Bug de parsing (mineur, à corriger)** : le fichier est encodé en **UTF-16**
   avec des colonnes séparées par **tabulation**, pas UTF-8/virgule comme
   `guichet_emplois.py` le supposait — `resolve_columns` échoue proprement avec un
   message garbled plutôt que de mal interpréter les données (le garde-fou a
   fonctionné comme prévu), mais le connecteur doit être ajusté pour lire le vrai
   format.
2. **DÉCOUVERTE BLOQUANTE, contredit l'hypothèse de la spec (section 7)** : les
   65 vraies colonnes du fichier ne contiennent **aucun nom d'employeur**. Confirmé
   à la fois en inspectant l'en-tête réelle (`ID WIC Lieu emploi`, `Appellation
   d'emploi`, codes CNP, `Ville`, `Provinces/Territoires`, salaire, conditions
   d'emploi, etc. — aucune colonne "employeur"/"entreprise") et dans la description
   officielle du jeu de données sur open.canada.ca, qui énumère explicitement les
   champs inclus sans jamais mentionner l'identité de l'employeur : "job title,
   codes from the National Occupational Classification (NOC) and the North
   American Industry Classification System (NAICS), work location, number of
   vacancies, salary and benefits, hours of work, job requirements, and employment
   terms." Aucune colonne URL/permalien vers l'offre non plus, donc pas de moyen
   évident de récupérer le nom de l'employeur pour une offre donnée sans requêtes
   individuelles sur le site public du Guichet-Emplois (le même anti-pattern que la
   question posée sur le REQ).

**Impact** : sans nom d'employeur, `resolve_company` n'a rien à résoudre — ce
fichier en vrac ne peut PAS alimenter le dossier cumulatif par entreprise tel que
conçu. Utiliser "Agence de placement" (la colonne la plus proche) serait trompeur :
c'est l'agence de recrutement, pas l'employeur réel, et présenterait un mauvais
nom d'entreprise à l'utilisateur — contraire à la promesse de fiabilité du produit
(spec section 6). Aucun contournement appliqué : ni donnée fabriquée, ni
substitution incorrecte. Décision à prendre par Alexandre — voir la question
posée dans la conversation.

## RDPRM — confirmé sans accès gratuit en vrac (contredit l'hypothèse du README)

Voir `falkye/registry/sources.yaml` (entrée `rdprm`) pour le détail complet :
consultation payante à l'unité (11 $/nom, 4 $/NIV), aucune API publique, aucun flux
en vrac. Décision produit (Alexandre, 2026-08-31) : statut `a_developper`,
activation Phase 2 avec déclenchement ciblé par entreprise déjà détectée — jamais
un balayage en vrac.

## Bug de performance corrigé pendant la validation

`falkye/resolution.py::_find_unresolved_company` comparait en Python, à
CHAQUE signal ingéré, le nom normalisé contre TOUTES les entreprises non résolues
déjà en base — quadratique sur le volume. Corrigé en ajoutant une colonne indexée
`Company.nom_detecte_normalise` et en interrogeant directement la base. Validé :
800 signaux SEAO traités en ~3 secondes après correction (contre un blocage
> 3 minutes avant).

## Politique d'ajout de domaines pour la Phase 2

Précisé dans la mise à jour de la spec du 2026-08-31 : ne pas ajouter par
anticipation les domaines des sources de Phase 2 à la liste réseau Custom —
ajouter chaque domaine seulement quand la source correspondante est activée.
`opencanada.blob.core.windows.net` couvre déjà probablement l'EIMT et les
subventions fédérales (même infrastructure Azure que le Guichet-Emplois) sans
ajout supplémentaire ; Investissement Québec est un PDF sur `www.investquebec.com`,
un domaine distinct, à ajouter seulement à son activation.

## EIMT positive — validée avec de vraies données, remplace Guichet-Emplois

Testé le 2026-08-31 : téléchargement et parsing réels réussis (fichier XLSX du
jeu de données `90fed587-1364-4f33-a9ee-208181dc0b97`, trimestre 2026Q1, ~8800
lignes). Exemple réel : "Barry Group Inc", Terre-Neuve-et-Labrador, 106 postes
approuvés, profession "94142-Ouvriers... transformation du poisson". Deux
découvertes techniques : (1) format réel = XLSX pour les trimestres récents
(CSV seulement pour les plus anciens, ~2021 et avant) ; (2) le fichier a une
ligne de titre fusionnée qui contient elle-même le mot "employeurs" — piège
pour un détecteur d'en-tête par sous-chaîne, corrigé en exigeant une
correspondance EXACTE de cellule. Voir `registry/sources.yaml` (entrée `eimt`)
pour le détail complet.

## Subventions fédérales et contrats fédéraux — validés via l'API Datastore CKAN

Les deux jeux de données réels (432527ab-7aac-45b5-81d6-7597107a7013 pour les
subventions, d8f85d91-7dec-4fd1-8055-483b77225d8b pour les contrats) ont un
fichier CSV brut trop volumineux pour être téléchargé en entier dans une
session (2,3 Go et 640 Mo respectivement — tout l'historique fédéral depuis
~2017). Découverte : les deux ressources ont `datastore_active=True`, donc
interrogeables via l'API Datastore CKAN (`datastore_search`, avec filtres, tri
et pagination) plutôt que le fichier brut — toujours des données ouvertes
gratuites au sens de la spec, juste un accès ciblé. Testé avec de vraies
données le 2026-08-31 :
- Subventions (filtré Québec, triées par date) : "Le Festival International de
  Jazz de Montréal inc.", 249 999 $, Développement économique Canada pour les
  régions du Québec, 2026-07-28.
- Contrats (triés par date) : "Real Time Networks Inc", 120 518,57 $,
  2026-12-01.

Aucun nouveau domaine réseau requis pour ces deux sources — même
infrastructure `open.canada.ca`/`opencanada.blob.core.windows.net` déjà
autorisée.

## Corporations Canada et Investissement Québec — validées avec de vraies données

Les deux domaines requis (`d4bf66bykfyaf.cloudfront.net`,
`www.investquebec.com`) ont été autorisés le 2026-08-31 ; les deux connecteurs
ont ensuite été validés contre de vraies données le même jour.

**Corporations Canada** — deux bugs trouvés et corrigés à l'inspection du
fichier réel :
1. Les colonnes réelles diffèrent de l'estimation initiale : pas de champ
   "date d'incorporation" direct (seulement "Date d'anniversaire"/"Année du
   dernier dépôt annuel", aucun fiable — donc non extrait plutôt que deviné) ;
   l'adresse est composée à partir de 4 colonnes (Rue, Municipalité/ville,
   Province/territoire, Code postal), pas une seule colonne "adresse".
2. `name_contains="active"` attrapait aussi les ressources "**in**active"
   (la sous-chaîne "active" y est contenue) — le premier essai a ingéré des
   corporations "Dissoute". Corrigé par une exclusion explicite
   (`_filtrer_ressources_actives`, avec test de régression dans
   `tests/test_corporations_canada.py`).

Résultat après corrections : "The Huntsman Marine Science Centre", 1 Lower
Campus Road, St. Andrews, NB — une vraie corporation fédérale active.

**Investissement Québec** — téléchargement et extraction de tableaux PDF
réels réussis (pdfplumber). Un problème d'environnement distinct rencontré et
résolu en cours de route : le module `cffi` (dépendance de `cryptography`,
utilisée par `pdfminer`/`pdfplumber`) était cassé dans l'image de base,
réinstallé avec `pip install --ignore-installed cffi cryptography`. Exemples
réels extraits : "13548082 Canada Inc", 3 000 000 $ ; "11888935 Canada Inc.
(Workstaff)", 289 058 $.

## Import manuel (RDPRM) — mécanisme testé, source activée

Le mécanisme générique d'import manuel (spec section 9, voir
`docs/ARCHITECTURE.md`) a été testé de bout en bout le 2026-08-31 avec la CLI
(`falkye import-manuel ajouter`) : création du signal, résolution NEQ
tentée via le miroir local (REQ), et déclenchement immédiat du reste du
pipeline pour les profils existants — comportement conforme (0 notification
en l'absence d'un vrai REQ chargé, exactement le même garde-fou que pour SEAO).
Aucun appel réseau impliqué dans ce mécanisme — c'est entièrement local une
fois que l'utilisateur a lui-même obtenu le document RDPRM.

## REQ basculé en import manuel (décision du 2026-08-31)

Suite à l'analyse détaillée ci-dessus (IP de sortie changeante à chaque
tentative, blocage dès la toute première requête, message Cloudflare
identique sur ~13h) : Alexandre a tranché que ce n'est pas quelque chose à
contourner par du code — c'est vraisemblablement une règle Cloudflare visant
les plages IP infonuagiques partagées. Plutôt que de chercher un
contournement technique, le REQ est passé en `methode_acces: import_manuel`
(le même mécanisme générique déjà construit pour le RDPRM, étendu pour couvrir
le cas "fichier complet" — voir `docs/ARCHITECTURE.md`). Alexandre télécharge
lui-même le fichier depuis son navigateur (tâche récurrente légère, deux fois
par mois — le fichier n'est pas mis à jour plus souvent) puis l'importe via
`falkye import-manuel fichier --source-id req --chemin <fichier>`.

Le lien exact (identique à celui découvert dynamiquement par le code, jamais
codé en dur différemment) :
`https://www.registreentreprises.gouv.qc.ca/RQAnonymeGR/GR/GR03/GR03A2_22A_PIU_RecupDonnPub_PC/FichierDonneesOuvertes.aspx`

Mécanique testée de bout en bout (CLI + tests automatisés,
`tests/test_req_manual_import.py`) avec un fichier local minimal — mais le
VRAI schéma de colonnes du fichier REQ reste non confirmé (le blocage empêche
aussi bien Alexandre que cette session d'inspecter un vrai fichier depuis
l'environnement). `resolve_columns()` échouera explicitement avec le détail
des en-têtes réelles si `COLUMN_ALIASES` (falkye/sources/req.py) ne
correspond pas au premier vrai import — pas une mauvaise interprétation
silencieuse.

## Structure réelle du ZIP REQ découverte (2026-08-31) — six CSV liés, pas un fichier plat

Alexandre a inspecté le vrai ZIP téléchargé depuis son navigateur : il contient
**six CSV distincts et liés entre eux**, pas un seul fichier plat comme le code
initial le supposait :

| Fichier | Taille | Rôle probable |
|---|---|---|
| `Entreprise.csv` | ~630 Mo | Table de base : NEQ, nom, statut |
| `Nom.csv` | ~281 Mo | Noms alternatifs/historiques par NEQ |
| `Etablissements.csv` | ~34,5 Mo | Adresse(s) par NEQ — probablement plusieurs lignes par entreprise (siège + établissements secondaires), pertinent pour le signal "nouvel établissement" (spec section 7) |
| `DomaineValeur.csv` | — | Table de décodage (code → libellé) pour des colonnes codées ailleurs (ex. secteur, type de statut) |
| `FusionScissions.csv` | — | Événements corporatifs (fusions/scissions) — hors des 5 champs requis par la spec (NEQ, nom, secteur, adresse, statut), pas utilisé pour l'instant |
| `ContinuationsTransformations.csv` | — | Idem, hors périmètre pour l'instant |

**Ce que ça change dans le code, corrigé le même jour :**
- `_iter_csv_rows` (falkye/sources/req.py) concaténait auparavant tous les
  CSV trouvés dans un `.zip` comme s'ils avaient le même schéma — avec un vrai
  fichier à 6 CSV différents, ça aurait produit des lignes mal interprétées en
  silence (violation directe du principe "données réelles non négociables,
  jamais d'interprétation silencieuse erronée"). **Corrigé immédiatement** :
  un `.zip` à plusieurs CSV lève maintenant une `RuntimeError` explicite plutôt
  que de fusionner à l'aveugle — testé (`test_ingest_snapshot_refuse_un_zip_a_
  plusieurs_csv_plutot_que_de_les_fusionner`).
- Nouvelle méthode optionnelle `SourceConnector.inspect_file()` (falkye/
  sources/base.py) + `REQConnector.inspect_file`/`inspect_zip` (falkye/
  sources/req.py) : lit en flux (sans tout décompresser) l'en-tête + une ligne
  d'exemple de chaque CSV interne — pour confirmer les vraies colonnes avant
  d'écrire la jointure, plutôt que de deviner sur une structure relationnelle à
  trois fichiers (risque de jonction NEQ→adresse silencieusement erronée, pire
  qu'une simple colonne manquante). Nouvelle commande CLI :
  `falkye import-manuel inspecter --source-id req --chemin <zip>`.
- La vraie jointure multi-fichiers (Entreprise.csv comme table de base,
  Etablissements.csv pour l'adresse/le signal "nouvel établissement",
  DomaineValeur.csv pour décoder les codes) a été écrite contre les vraies
  colonnes confirmées ci-dessous, une fois inspectées — voir section suivante.

## Vraies colonnes confirmées et jointure implémentée (2026-08-31)

Alexandre a mis le fichier réel (267 Mo, SHA-256 vérifié) en release GitHub
(`ALTALogistic1/Observador`, tag `req-data-2026-08-31` — nom du dépôt GitHub
inchangé par le renommage du produit/package en FALKYE, voir plus bas) ;
téléchargé et
inspecté dans cette session via `import-manuel inspecter`. Vraies colonnes
retenues (`falkye/sources/req.py`) :

- **`Entreprise.csv`** (37 colonnes réelles) : `NEQ`, `COD_STAT_IMMAT`,
  `DAT_MAJ_INDEX_NOM`, `COD_ACT_ECON_CAE`/`DESC_ACT_ECON_ASSUJ` (repli secteur),
  `ADR_DOMCL_ADR_DISP`/`ADR_DOMCL_LIGN1-4_ADR` (repli adresse — souvent
  `ADR_DOMCL_ADR_DISP='N'`, adresse alors absente même si les lignes sont
  remplies). **Ne contient PAS le nom** de l'entreprise.
- **`Nom.csv`** : `NEQ`, `NOM_ASSUJ`, `STAT_NOM`, `TYP_NOM_ASSUJ`,
  `DAT_INIT_NOM_ASSUJ`, `DAT_FIN_NOM_ASSUJ` — historique de noms, plusieurs
  lignes possibles par NEQ. Codes `STAT_IMMAT`/`STAT_NOM`/`TYP_NOM` décodés via
  `DomaineValeur.csv` (`IM`=Immatriculée, `RD`/`RO`/`RX`=Radiée [sur
  demande/d'office/d'office art. 59] → statut "radiee" ; `V`=nom en vigueur,
  `A`=antérieur, `M`=dénomination sociale, `N`=nom).
- **`Etablissements.csv`** : `NEQ`, `NO_SUF_ETAB`, `IND_ETAB_PRINC` (`O`=siège),
  `LIGN1-4_ADR`, `COD_ACT_ECON`/`DESC_ACT_ECON_ETAB`, `NOM_ETAB`. Plusieurs
  lignes possibles par NEQ — source du signal "nouvel établissement secondaire".

**Découverte de calibration en cours de route** : une NOUVELLE IMMATRICULATION
seule (sans changement d'adresse ni nouvel établissement secondaire) ne
produit PLUS de signal — une entreprise qui vient de naître n'est pas une
entreprise EN croissance (principe #3). Le code initial (avant confirmation du
vrai schéma) traitait à tort toute nouvelle ligne NEQ comme un signal
"nouvelle immatriculation" ; corrigé en même temps que la jointure réelle.
`REQEtablissementEntry` (nouveau modèle, miroir par établissement) permet de
distinguer un nouvel établissement SECONDAIRE d'une entreprise déjà connue
(fort) d'un changement d'adresse du siège (moyen) — deux signaux désormais
détectés séparément et correctement, alors que le code précédent ne pouvait
détecter qu'un changement d'adresse (miroir à une seule ligne par NEQ).

**Validé avec de vraies données** (session, `--limit 3000` sur le vrai fichier
après correction du bogue de bornage ci-dessous) :
- Résolution nom + statut + adresse/secteur confirmée correcte contre des
  entrées réelles (ex. NEQ 1140030355 → "LIGN'ELLE PLUS INC.", statut
  "radiee", cohérent avec une vérification manuelle indépendante du fichier).
- Décodage des 6 codes `COD_STAT_IMMAT` réels validé.
- Priorité de sélection du nom (en vigueur > antérieur le plus récent) validée
  sur un vrai NEQ radié n'ayant plus aucun nom "en vigueur".
- **Complétude d'adresse partielle, confirmée sur de vraies données — limite
  réelle, pas un bogue** : sur un échantillon de 3000 entreprises actives (NEQ
  très anciens, immatriculés en 1994), seulement 17 % avaient une adresse
  résolue (via `Etablissements.csv` ou repli domicile) ; sur un échantillon
  plus tardif dans le fichier (immatriculations ~1995), ce taux monte à 52 %
  pour les entreprises actives. Hypothèse la plus probable : la déclaration
  d'établissement est une exigence plus récente que l'immatriculation de base,
  donc les plus vieux dossiers actifs n'ont souvent jamais déposé cette
  information. Le code laisse `adresse`/`ville`/`code_postal` à `None` plutôt
  que d'inventer une valeur — cohérent avec le reste du pipeline (une
  entreprise sans adresse résolue via le REQ peut encore l'être via
  l'enrichissement web, section 10, ou une autre source qui la fournit
  directement).

**Bogue de bornage trouvé et corrigé en cours de validation** :
`REQConnector.detect_from_file` appelait `ingest_snapshot(limit=None)` sans
égard au `--limit` demandé — le paramètre `limite_lignes` de
`importer_fichier_source` ne bornait que le nombre de SIGNAUX produits après
coup, pas le volume réellement lu/inséré en amont (le vrai fichier REQ ne
produit ses signaux qu'après avoir traité tout `Entreprise.csv`, contrairement
à un connecteur simple ligne-par-ligne). Un premier essai `--limit 2000` a
donc en réalité traité le fichier ENTIER (~16 minutes dans cet environnement,
interrompu manuellement avant le commit final → 0 ligne persistée, aucune
perte de données réelles puisque rien n'avait encore été validé). Corrigé :
`SourceConnector.detect_from_file` accepte maintenant `limit` et le transmet
jusqu'à `ingest_snapshot` ; un deuxième essai `--limit 3000` a pris 27
secondes et produit exactement 3000 entrées, confirmant le correctif.

## Prochaine étape

Toutes les sources actives de la Phase 1 sont validées avec de vraies
données, y compris le REQ (mécanique ET schéma désormais confirmés). Reste
pour Alexandre : lancer le premier import RÉEL et COMPLET (sans `--limit`)
depuis son propre poste, probablement plus rapide que dans cet environnement
(voir note de performance ci-dessous) :

```
falkye import-manuel fichier --source-id req --chemin <fichier réel>
```

**Note de performance** : le fichier complet (`Entreprise.csv` seul fait
~630 Mo, plusieurs millions de lignes) est traité ligne par ligne via l'ORM —
dans CET environnement, l'extrapolation à partir du test borné à 3000 lignes
suggère un import complet de l'ordre de l'heure ou plus. Un poste personnel
non contraint sera vraisemblablement plus rapide, mais un import complet
restera une opération de plusieurs minutes, pas quelques secondes — normal
pour une tâche bi-mensuelle, mais à lancer en arrière-plan plutôt qu'en
attendant activement. Une optimisation par insertion en lot (bulk insert)
resterait possible plus tard si la durée réelle s'avère un irritant récurrent.

Une fois l'import complet réussi : lancer une recherche ponctuelle
(`falkye scan ponctuel`) pour obtenir la première notification consolidée
de bout en bout avec de vraies données sur les 8 sources actives.

## Import complet réel exécuté, et deux bugs réels trouvés en le validant (2026-08-31)

Le premier import complet du REQ (fichier fourni par Alexandre en release
GitHub, SHA-256 vérifié) a tourné avec succès : **2 726 312** entrées REQ
créées (1 006 208 immatriculées, 1 713 476 radiées, 6 581 non immatriculées,
47 avis d'intention), **236 311** établissements — en ~40 minutes dans cet
environnement (commit intermédiaire tous les 5000 lignes, ajouté après un
premier essai interrompu avant son commit final). `0 signal(aux)` produit,
comme attendu pour un premier import (aucun état antérieur à comparer).

En lançant le premier `scan` réel qui suit, DEUX bugs de performance/calibration
réels ont été trouvés et corrigés, tous deux invisibles tant que le REQ n'avait
pas encore de vraies données à cette échelle :

1. **`resolve_neq_by_name` 150x plus lent que nécessaire.** `EXPLAIN QUERY
   PLAN` a montré un `SCAN` complet de la table (2,7M lignes, ~0,5s par appel)
   au lieu d'un `SEARCH` indexé — `LIKE 'prefix%'` avec un paramètre lié est
   insensible à la casse par défaut, et l'index n'a pas de collation NOCASE,
   donc SQLite ne peut pas garantir que l'index couvre correctement la
   comparaison. Corrigé en remplaçant `LIKE` par `GLOB` (nativement sensible à
   la casse, éligible à l'optimisation d'index) — sans perte de correspondance
   puisque les deux côtés sont déjà normalisés en minuscules. Résultat mesuré :
   ~500ms → ~30ms par résolution.
2. **`corporations_canada` : même erreur de calibration que l'ancien code du
   REQ.** Le connecteur traitait toute NOUVELLE corporation active détectée
   par le diff comme un signal — sur le premier import réel (~695 000
   corporations actives dans le fichier fédéral, 111 Mo), ça aurait produit
   ~695 000 signaux, chacun nécessitant une résolution NEQ (des heures de
   calcul en pure perte, et un flot de "signaux" qui ne sont pas de vrais
   signaux de croissance). Corrigé de la même façon que le REQ : seul un
   changement d'ADRESSE pour une corporation DÉJÀ connue produit un signal —
   une toute nouvelle incorporation n'en produit plus.

## Fenêtre par défaut de `scan ponctuel` corrigée (2026-08-31)

`scan ponctuel` (`recherche_ponctuelle`) téléchargeait et traitait à SEAO
l'intégralité de ses 372 fichiers hebdomadaires/mensuels historiques (depuis
2021) plutôt qu'une fenêtre récente, parce que `since=None` était interprété
littéralement comme "aucune borne" — extrapolé à ~12h dans cet environnement.
Décision d'Alexandre : plafonner par défaut, comme `scan veille`, avec une
option pour forcer une fenêtre plus large.

Corrigé : `run_recherche_ponctuelle` accepte maintenant `lookback_days`
(défaut **60 jours** — le double des 30 jours de `scan veille`, cohérent avec
la lecture spec "plus large" de la recherche ponctuelle sans retomber dans
"tout l'historique"). CLI : `scan ponctuel --profile-id N [--lookback-days N]
[--historique-complet]` — ce dernier retrouve l'ancien comportement
(`since=None`) pour qui a vraiment besoin d'une recherche exhaustive et est
prêt à en payer le temps.

## Enrichissement web (section 10) — bloqué par les moteurs de recherche eux-mêmes, pas par le réseau (2026-09-01)

Vérification demandée par Alexandre sur les 311 notifications réelles produites
le 2026-08-31 : les 311 entreprises avaient bien un `site_web_vérifié_le` réglé
(l'étape a tourné) mais aucune n'avait de `site_web` trouvé — toutes les
recherches DuckDuckGo avaient échoué. Cause initiale identifiée :
`html.duckduckgo.com` n'était pas dans la liste réseau Custom. Alexandre l'a
ajouté.

**Après ajout, le domaine est bien accessible (confirmé : réponse HTTP réelle
du vrai serveur DuckDuckGo), mais DuckDuckGo répond par un CAPTCHA anti-bot**
("Unfortunately, bots use DuckDuckGo too... Select all squares containing a
duck", paramètre `cc=botnet` explicite dans sa propre réponse) plutôt que par
de vrais résultats de recherche. Ce n'est pas un blocage réseau — c'est
DuckDuckGo qui traite le trafic comme automatisé, très probablement à cause de
l'adresse IP de sortie infonuagique/partagée de cet environnement (même
catégorie de cause que le blocage Cloudflare du REQ, un mécanisme de défense
différent — CAPTCHA plutôt que 403 — mais la même origine : IP de centre de
données, pas notre volume de requêtes).

**Trois alternatives testées à la demande d'Alexandre, dans l'ordre demandé
(Brave et Mojeek en premier, Startpage en dernier recours), toutes les trois
également bloquées de façon distincte :**

| Moteur | Résultat HTTP | Nature du blocage |
|---|---|---|
| DuckDuckGo | 202 | CAPTCHA anti-bot (`cc=botnet`) |
| Brave Search | 429 | Rate-limited / refusé |
| Mojeek | 403 | Refusé |
| Startpage | 200 (mais pas de vrais résultats) | Challenge "Anubis" (preuve de travail JavaScript), IP de sortie visible dans le challenge : `160.79.106.129` |

**Conclusion, décision d'Alexandre** : aucun changement de code ni de liste
réseau ne peut contourner ça — les quatre moteurs gratuits sans clé API
bloquent le même type de trafic pour la même raison de fond (IP infonuagique
partagée). Enrichissement web laissé de côté pour l'instant — le pipeline
reste pleinement fonctionnel sans (l'absence de site web n'est jamais un
motif d'exclusion, spec section 6). Une clé API de recherche payante (Bing Web
Search, Google Custom Search, SerpAPI, etc.) est notée comme item budgétaire à
trancher en Phase 2, aux côtés de Crunchbase et de l'agrégateur de recrutement
(spec section 8) — ce budget contournerait le blocage anti-bot proprement,
contrairement au scraping HTML gratuit.

## Phase 1 déclarée atteinte — audit EIMT/subventions fédérales à 0 signal (2026-09-01)

Alexandre a demandé de vérifier, avant de passer à la Phase 2, si les `0
nouveaux` d'EIMT et de subventions fédérales lors du dernier scan reflétaient
un vrai manque de données ou un bogue silencieux. Les deux causes sont
différentes :

**EIMT — vrai bogue de calibration, corrigé.** `detect()` filtrait chaque
ligne avec `if since and trimestre_date < since: continue`, où
`trimestre_date` est la date de DÉBUT du trimestre PUBLIÉ (ex. `2026-01-01`
pour le fichier "2026Q1"), pas la date de l'événement. Confirmé contre les
vraies ressources CKAN le 2026-09-01 : le trimestre le plus récemment publié
est 2026Q1 (démarre le 2026-01-01), alors que `now` était le 2026-09-01 — un
décalage de publication structurel d'environ 8 mois, bien au-delà de
n'importe quelle fenêtre glissante de 30 ou 60 jours. Ce filtre excluait donc
TOUJOURS l'intégralité des données, même le trimestre le plus frais
réellement disponible — pas "pas de données pour cette période", un vrai
bogue. Corrigé en retirant ce filtre par ligne : le sélecteur de ressources
(`cibles = resources[:1 ou :4]`, déjà calibré pour la granularité trimestrielle
réelle de cette source) et le dédoublonnage par `source_ref` dans
`falkye.engine.ingest_source` suffisent déjà à borner le volume et éviter
les doublons d'un scan à l'autre — le filtre par date supplémentaire était
redondant et, en pratique, silencieusement destructeur. **Validé contre de
vraies données après correction** : plus de 200 signaux réels obtenus
immédiatement (Terre-Neuve-et-Labrador, professions agricoles/transformation
alimentaire — cohérent avec les données réelles EIMT/TET).

**Subventions fédérales — pas un bogue, une vraie coïncidence de fenêtre.**
Le filtrage par date ici compare `agreement_start_date` (une vraie date par
enregistrement, pas un repère grossier) à `since`, trié décroissant avec
sortie anticipée — logique correcte. Vérifié contre l'API Datastore réelle le
2026-09-01 : le don le plus récent pour le Québec (`recipient_province=QC`)
est daté du 2026-08-01, à peine EN DEHORS de la fenêtre de 30 jours de
`scan veille` (qui remontait au 2026-08-02 — raté d'une seule journée). Avec
une fenêtre de 60 jours (le nouveau défaut de `scan ponctuel`), au moins 5
subventions québécoises réelles de fin juillet/début août 2026 seraient
détectées (festivals de Montréal, corporation portuaire, etc.). Rien à
corriger dans le code — juste une coïncidence de calendrier entre le moment du
scan et la fenêtre glissante utilisée ce jour-là.

## Guichet-Emplois — RÉACTIVÉE via une nouvelle piste (nom d'employeur par page de détail) (2026-09-01)

Après le début de la Phase 2 (Deloitte Fast 50 activé pour Signal 1),
Alexandre a proposé une nouvelle piste pour Guichet-Emplois, retirée le
2026-08-31 faute de nom d'employeur dans le fichier en vrac (voir section
plus haut) : les pages de détail d'offre individuelle sur
guichetemplois.gc.ca affichent le nom de l'employeur, même si le fichier en
vrac ne le donne pas. Demande explicite : tester avant d'abandonner la
source, et ne poursuivre que si ça fonctionne sans blocage réseau.

**Piste confirmée avec de vraies données :**
- `ID WIC Lieu emploi` (une vraie colonne du fichier) correspond exactement à
  l'identifiant utilisé dans
  `https://www.guichetemplois.gc.ca/jobsearch/jobposting/{id}` — confirmé par
  WebSearch puis par une requête directe.
- Sur une offre encore active (exemple réel utilisé pour la validation : ID
  `50196187`), le nom de l'employeur est dans un `<h2>` à l'intérieur d'un
  conteneur `class="job-posting-details-employer-wrapper"`, avec le secteur
  d'activité juste à côté (`<li><span class="details">`) — valeur réelle
  capturée : `KAVURU'S INDIAN BISTRO`, secteur `Hébergement et services de
  restauration`.
- `robots.txt` du site : `Crawl-delay: 5`, aucun chemin interdit — la
  consultation individuelle est donc permise, mais coûte au moins 5 secondes
  par offre.

**Limite réelle confirmée (pas un bogue), qui borne la couverture plutôt que
de bloquer la source :** le fichier en vrac a un décalage de publication
d'environ un mois (le plus récent disponible début septembre 2026 est celui
de juillet 2026), et les offres individuelles expirent plus vite que ce
décalage. Deux échantillons réels tirés de ce fichier confirment ça : un
premier échantillon de 5 identifiants, puis un second de 4 identifiants
(après le correctif d'alias ci-dessous) — tous retournent HTTP 410 Gone, avec
redirection vers `jobsearch/jobpostingexpired` (une page sans bloc employeur,
pas une erreur d'identifiant mal formé). Validation de bout en bout du
connecteur complet : 15 offres québécoises tentées, 0 signal produit —
cohérent avec cette contrainte, pas un connecteur cassé.

**Décision d'Alexandre** : garder l'architecture fichier-en-vrac (cohérente
avec toutes les autres sources du registre) et accepter une couverture
PARTIELLE, plutôt que de basculer vers un scraping des résultats de
recherche en direct — un tel scraping introduirait un risque de blocage
anti-bot (comme démontré avec les 4 moteurs de recherche testés pour
l'enrichissement web, voir section précédente) et casserait la cohérence
architecturale du registre pour un gain incertain. Une offre expirée ne
produit simplement aucun signal — même principe qu'un `non_trouve` ailleurs
dans le pipeline.

**Deux bogues trouvés en construisant/validant cette version (aucun lié à la
piste elle-même) :**
1. `COLUMN_ALIASES` était écrit avec des alias à ESPACES (ex. `"id wic"`,
   `"appellation d emploi"`) alors que `resolve_columns` normalise les
   en-têtes du CSV avec des UNDERSCORES (voir
   `falkye/sources/column_mapping.py`, même convention déjà utilisée
   dans `eimt.py`) — un alias multi-mots à espaces ne correspondait donc
   jamais à un en-tête réel. Trouvé en validant contre les vraies en-têtes
   (`ID WIC Lieu emploi`, `Provinces/Territoires`, etc.), corrigé en
   réécrivant tous les alias avec des underscores.
2. Flakiness réseau distincte de l'expiration des offres : le tunnel TLS vers
   `guichetemplois.gc.ca` se réinitialise occasionnellement en cours de scan
   (`SSL_ERROR_SYSCALL` / `RemoteDisconnected`), y compris deux fois de suite
   sur un même identifiant — confirmé transitoire par un ré-essai qui finit
   par réussir (curl direct, même identifiant, 3 tentatives : deux échecs de
   connexion puis un succès). Sans ré-essai, cette flakiness se serait
   confondue silencieusement avec une vraie offre expirée. `recuperer_employeur`
   réessaie donc jusqu'à 3 fois sur une erreur RÉSEAU uniquement (jamais sur
   un statut HTTP non-200, pour ne jamais confondre flakiness et expiration
   réelle).

**Statut du registre** : `guichet_emplois` passe de `a_developper` à `actif`
— 9e source active du prototype, la 2e de la Phase 2 après Deloitte Fast 50
(Signal 1). Couverture volontairement partielle et documentée, pas une
promesse d'exhaustivité — cohérent avec le principe déjà établi ailleurs dans
le projet (couverture honnête plutôt que source retenue).

## Classements de croissance (Signal 1) : Growth 500 bloqué (Cloudflare), Globe and Mail activé (2026-09-01)

Suite de la Phase 2 (Signal 1, `classement_croissance`) : les deux sources
restantes du registre après Deloitte Fast 50, `growth500` et
`rob_top_growing`, investiguées comme demandé.

**Growth 500 (canadianbusiness.com) — laissé de côté, deux raisons
indépendantes :**
1. **Blocage anti-bot réel, pas un problème de liste réseau.**
   `canadianbusiness.com` et `www.canadianbusiness.com` sont bien accessibles
   (domaines déjà autorisés) et répondent par une vraie page Cloudflare —
   confirmé par inspection du corps de la réponse (`<title>Attention
   Required! | Cloudflare</title>`, cookie `__cf_bm` de gestion de bots,
   en-tête `server: cloudflare`). Même mécanisme, même cause de fond (IP
   infonuagique/partagée de sortie de cet environnement) que le blocage
   Cloudflare du REQ et les 4 moteurs de recherche testés pour
   l'enrichissement web (voir sections plus haut) — aucun changement de code
   ni de liste réseau ne le contournerait. `growth500.ca` et l'URL d'archive
   (`archiveprod.canadianbusiness.com`) ne sont eux-mêmes pas atteignables
   (bloqués au niveau du proxy — domaines non autorisés, distinct du blocage
   Cloudflare ci-dessus).
2. **Le classement lui-même semble ne plus être activement republié.** Une
   recherche web n'a trouvé aucune preuve d'une édition 2025/2026 en cours —
   seulement une page d'archive (`archiveprod.canadianbusiness.com`) et des
   mentions tierces d'entreprises citant un classement passé, contrairement à
   Deloitte Fast 50 et au Globe and Mail Top Growing Companies, tous deux
   confirmés actifs pour 2025 avec une méthodologie et un calendrier de
   publication courants.

Registre : `growth500` reste `a_developper`, `blocage_type` mis à
`anti_bot` avec le détail ci-dessus — décision de laisser tomber
complètement (plutôt que budgétaire, comme l'enrichissement web) à confirmer
avec Alexandre, puisque même une clé API payante ne contournerait pas
Cloudflare pour un classement qui n'existe peut-être plus.

**Globe and Mail Top Growing Companies — ACTIVÉ, aucun blocage rencontré.**
Découverte réelle en construisant le connecteur (`falkye/sources/
rob_top_growing.py`) :
- La page-hub stable
  (`theglobeandmail.com/business/rob-magazine/top-growing-companies/`) liste
  les classements annuels ; le lien de l'année courante ("...-of-2025/", pas
  la variante "...-of-2025-provincial/") est découvert dynamiquement — même
  discipline que le PDF de Deloitte (jamais une URL annuelle codée en dur).
- L'article annuel est une page JS (CMS Fusion/Arc XP, `theglobeandmail.com`
  appartient au même groupe que le Washington Post et utilise son CMS Arc
  XP) dont le corps visible est vide en HTML brut (`articleWordCount: 0`),
  mais le CMS embarque tout l'article dans un bloc
  `Fusion.globalContent={...};` inline — extrait par appariement d'accolades
  (un simple regex non-gourmand casse dès qu'une valeur contient elle-même
  des accolades, ex. un blob CSS imbriqué, ce qui arrive réellement dans
  cette page).
- Ce bloc contient `content_restrictions.content_code`, l'indicateur
  officiel de paywall du Globe and Mail — confirmé `"green"` (accès libre)
  pour ce classement, malgré la réputation générale du site d'être payant.
  Le connecteur logue un avertissement (sans échouer) si jamais un autre
  code est rencontré une année future.
- Le bloc révèle aussi le vrai mécanisme de données : un identifiant Google
  Sheet (`const sheetID = "..."`) chargé depuis un fichier JSON **public**
  hébergé sur S3 (`google-sheets-prod-....s3.ca-central-1.amazonaws.com`) —
  aucune authentification, aucun anti-bot rencontré, à l'opposé total de
  Growth 500. `sheetID` change chaque année (nouvelle feuille Google
  Sheets) — découvert dynamiquement depuis l'article de l'année courante,
  jamais codé en dur.
- **Validation de bout en bout contre le vrai fichier 2025** : 400
  entreprises (le nombre annoncé dans la description de l'article,
  "The 400 companies on this year's list"), avec des entreprises québécoises
  réelles identifiées (Boreas Technologies, NUAGE Logistics, Evnia
  Environmental Compliance Group, LOC medical, Ubiweb, entre autres).
- Champ région irrégulier dans les données sources : les grandes villes sont
  données seules ("Montreal", "Toronto", "Calgary"), les autres avec un
  suffixe de province ("Longueuil, Que.", "Bromont, Que.") —
  `_parse_ville_region` sépare les deux quand le suffixe est présent, laisse
  la région à `None` sinon plutôt que de deviner (résolue via le REQ comme
  n'importe quel champ absent).

**Statut du registre** : `rob_top_growing` passe de `a_developper` à
`actif` — 10e source active du prototype, la 3e de la Phase 2. `growth500`
reste `a_developper` (`blocage_type: anti_bot`) — **décision confirmée par
Alexandre le 2026-09-01** : classement figé/archivé (vérifié de son côté,
pas seulement le blocage Cloudflare), abandonné définitivement.

## Permis de construction municipaux (Signal 4) : Laval activé, Montréal/Québec bloqués par absence de nom (2026-09-01)

Suite de la Phase 2 (Signal 4, `registre_corporatif`) : les 3 sources de
permis municipaux du registre (Montréal, Québec, Laval), investiguées comme
prévu.

**Découverte structurante commune aux trois** : le portail Données Québec
(`www.donneesquebec.ca`, déjà autorisé pour REQ/SEAO) fédère en fait les
jeux de données des trois villes — aucun nouveau domaine n'a été nécessaire,
y compris pour Montréal dont le fichier brut est hébergé sur
`donnees.montreal.ca` (non autorisé, testé 403 au niveau du proxy) : la même
donnée est exposée via l'API Datastore CKAN directement sur
`www.donneesquebec.ca` (`datastore_active: true` sur la ressource), exactement
le même mécanisme déjà utilisé pour subventions_federales/contrats_federaux.

**Montréal et Québec — laissés à `a_developper`, aucune des deux ne contient
de nom d'entreprise/demandeur.** Vérifié par inspection directe des vraies
colonnes (pas une supposition) :
- Montréal (558 874 lignes, très à jour au 2026-08-24) : 17 colonnes —
  identifiants, dates, emplacement, arrondissement, type/catégorie de
  bâtiment, `nature_travaux` en texte libre (ex. "REMPLACEMENT DES FERMES DE
  TOIT..."), nombre de logements, coordonnées. Aucune ne porte un nom
  d'entité.
- Québec (69 197 lignes, très à jour au 2026-08-28) : 10 colonnes —
  numéro/date/adresse de permis, domaine, type, arrondissement, `RAISON` (motif
  administratif textuel, ex. "Installation d'un branchement d'aqueduc ou
  d'égout", "Abattage d'arbre"), coordonnées. Même constat.

Pour Québec, la même piste que Guichet-Emplois (page de détail publique par
numéro de permis) a été cherchée — infructueuse : l'"Assistant-permis" du
site de la ville est un outil d'aide au dépôt de demande, pas un annuaire des
permis émis avec identité du demandeur. Les deux sources restent donc
`a_developper` (`blocage_type: donnee_manquante`) — même principe que
Guichet-Emplois avant sa piste des pages individuelles : pas de nom à
inventer quand la donnée source n'en contient tout simplement pas.

**Laval — ACTIVÉE**, seule des trois à exposer une identité d'entreprise :
le champ `ENTREPRENEUR` (172 168 lignes, 1991 au 2026-03-31). Nuance
importante documentée dans le connecteur
(`falkye/sources/permis_construction_laval.py`) : ce champ identifie
l'entreprise de CONSTRUCTION qui exécute les travaux, pas le propriétaire du
bâtiment qui s'agrandit — la spec visait plutôt ce dernier ("nouveaux
locaux, agrandissement"), mais aucun champ demandeur/propriétaire n'existe
dans ce jeu de données non plus. Retenu quand même, documenté honnêtement
plutôt que présenté comme autre chose — un entrepreneur en construction actif
est lui-même un prospect plausible pour un fournisseur B2B au secteur de la
construction. Couverture partielle : `ENTREPRENEUR` vide sur ~69% des lignes
(chantiers résidentiels mineurs, souvent exécutés par le propriétaire
lui-même) — aucun signal produit dans ces cas, pas de nom deviné.

Deux découvertes supplémentaires en validant avec de vraies données :
- `COUT_PERMIS` est le coût DU PERMIS (souvent un tarif administratif
  forfaitaire — ex. plusieurs lignes à 270,00$ pour des travaux visiblement
  très différents), PAS le coût des travaux — pas fiable comme proxy de
  l'ampleur du chantier, donc volontairement PAS utilisé par le score
  (`falkye/scoring.py:_score_permis_construction`, calé sur les 4
  catégories réelles de `TYPE_PERMIS_DESCR` à la place).
- Le fichier est republié occasionnellement (dernière publication confirmée
  le 2026-03-31 via les métadonnées CKAN), pas en continu — un scan à
  fenêtre courte (30-60 jours) peut donc légitimement retourner 0 nouveau
  signal entre deux republications, même catégorie de constat que
  subventions_federales, pas un bogue.

**Validation de bout en bout contre le vrai fichier** : 53 953 lignes avec
`ENTREPRENEUR` non vide (entreprises réelles confirmées — ex. "CONSTRUCTION
LUC MIRON INC.", "LES ENT. V. BRISEBOIS ET FILS INC."), 49 694 permis
distincts après dédoublonnage (un même `NO_PERMIS` peut couvrir plusieurs
adresses contiguës — ex. un projet de 5 unités attenantes — collapsé en un
seul signal par permis via `source_ref`, pas 5 notifications répétées pour le
même projet).

**Statut du registre** : `permis_construction_laval` passe de `a_developper`
à `actif` — 11e source active du prototype, la 4e de la Phase 2.
`permis_construction_montreal` et `permis_construction_quebec` restent
`a_developper` (`blocage_type: donnee_manquante`).

## Expansion pancanadienne (2026-09-01) : vérification croisée Corporations Canada, équivalents SEAO/REQ évalués, Nouvelle-Écosse activée

Alexandre a confirmé l'objectif de couverture pancanadienne (pas seulement
Québec) et demandé de prioriser les sources qui l'élargissent. Trois volets
traités dans l'ordre : le mécanisme requis pour `licences_affaires_municipales`,
l'évaluation des équivalents provinciaux à SEAO/REQ, et l'activation de la
Nouvelle-Écosse (le seul candidat SEAO confirmé viable).

**Vérification croisée Corporations Canada** (préalable "NON NÉGOCIABLE"
avant d'activer `licences_affaires_municipales`, imposé par le registre) :
`CorporationFederaleEntry` gagne `nom_normalise` (indexé, même discipline
GLOB — pas LIKE — que `REQEntry`, voir la section REQ plus haut) et
`province`. Nouvelle fonction `resolve_corp_federale_by_name` dans
`corporations_canada.py`, mécanique identique à `resolve_neq_by_name` du REQ.
Distinction documentée dans les deux fichiers : ceci n'est PAS le pivot de
résolution de `Company` (qui reste le NEQ, décision inchangée — voir
"Généralisation du pivot d'identité" dans ARCHITECTURE.md) mais une porte de
calibration plus étroite, utilisée uniquement pour confirmer qu'un nom
détecté correspond à une corporation fédérale EXISTANTE avant de produire un
signal. Validé contre les 694 844 corporations réelles : "Shopify Inc"
résout à 100.0 (SHOPIFY INC., vraie corporation fédérale) ; un nom inventé
ne produit aucune correspondance confiante. `EXPLAIN QUERY PLAN` confirme un
SEARCH via l'index, pas un SCAN complet. Migration ponctuelle appliquée à la
base de développement existante (ALTER TABLE + backfill des 694 844 lignes).
Limite documentée : ne détecte que les entreprises incorporées au FÉDÉRAL —
une entreprise provinciale-seulement ne matchera pas même si elle existe
réellement (connu, accepté).

**Équivalents SEAO (appels d'offres attribués) évalués** — 7 candidats
provinciaux, un seul automatisable :

| Source | Verdict |
|---|---|
| Nouvelle-Écosse — "Awarded Public Tenders" | ✅ Portail Socrata (data.novascotia.ca), API JSON, aucune authentification |
| BC Bid, Alberta Purchasing Connection, Ontario Tenders Portal, SaskTenders | ❌ Confirmé : "portails séparés, aucun flux de données public" |
| NBON (Nouveau-Brunswick) | ❌ Système d'avis web seulement |
| MERX | ❌ Payant (dès ~15$/mois), aucune API publique documentée |

CanadaBuys (fédéral) exclu de la liste : déjà la même infrastructure que
`contrats_federaux` (actif), fédéral seulement, aucun apport provincial.

**Équivalents REQ (registre d'entreprises) évalués** — conclusion plus dure
que la recherche initiale d'Alexandre ne le laissait supposer : **aucune
province n'offre un équivalent REQ automatisable et gratuit**, une fois
vérifié :

| Source | Verdict |
|---|---|
| Ontario | ❌ Recherche gratuite mais pas de vrac/API — "aucune API publique pour les registres provinciaux majeurs" (confirmé) |
| Nouvelle-Écosse (registre des sociétés, distinct du portail de contrats ci-dessus) | ❌ Vrac explicitement interdit depuis 2015 (changement des conditions d'utilisation) |
| Colombie-Britannique, Nouveau-Brunswick | ❌ Payant par recherche |
| Alberta | ❌ Fermé, agents autorisés seulement |
| Fédéral (Canada's Business Registries) | ❌ Interdit explicitement l'automatisation dans ses conditions ("I am not allowed to use automated tools to copy data from this service"), 8/13 provinces/territoires seulement |

Corporations Canada (déjà actif) reste donc le seul registre pancanadien en
vrac, avec sa limite fédérale-seulement déjà connue. Décision confirmée par
Alexandre : laisser tomber les autres candidats provinciaux. Piste secondaire
notée, pas prioritaire : StatCan "Open Database of Businesses" (~450 000
entreprises, licence ouverte) — un agrégat compilé, pas un registre primaire,
fréquence de mise à jour non confirmée ; à réévaluer comme enrichissement
futur, pas comme source de détection de signal.

**Nouvelle-Écosse — ACTIVÉE** (`contrats_nouvelle_ecosse`), première source
hors Québec pour le signal `appel_offres`. Portail Socrata, jeu de données
"Awarded Public Tenders" (id `m6ps-8j6u`) : 33 290 lignes réelles (avril 2010
à 2026-08-17, très à jour), couverture d'identité quasi totale (99,9% des
lignes ont un vendeur ET une date d'attribution). Deux bogues trouvés en
validant :
1. `tender_id` seul n'identifie pas une ligne de façon unique — un même
   appel d'offres peut être attribué à PLUSIEURS entreprises distinctes
   (contrats à commandes) : confirmé sur de vraies données (tender_id
   "MET24-04" attribué à la fois à "Miller Waste Systems Inc" et "Royal
   Environmental Inc"). `source_ref` inclut donc le vendeur — sans ça, le
   dédoublonnage du moteur aurait silencieusement écrasé le signal d'une
   vraie entreprise distincte.
2. `awarded_amount` vaut parfois `"0"` (867/33 290 lignes, ~2,6%) — traité
   comme valeur INCONNUE (`None`), pas un contrat réellement gratuit.

Validation de bout en bout : 33 267 signaux sur l'historique complet (33 030
distincts après dédoublonnage — quelques cas réels où la même entreprise
apparaît plusieurs fois sous le même tender_id avec des montants différents,
collapsés en un seul signal, même principe que les permis de Laval).

**Statut du registre** : `contrats_nouvelle_ecosse` ajouté et `actif` — 13e
source active du prototype, la 5e de la Phase 2.

## Licences d'affaires municipales : Vancouver activée, Toronto bloquée (2e domaine requis) (2026-09-01)

Alexandre a autorisé les 3 domaines demandés (`opendata.vancouver.ca`,
`open.toronto.ca`, `data.novascotia.ca`) et confirmé de construire
`licences_affaires_municipales` — signal `registre_corporatif`, priorité
pancanadienne.

**Vancouver — ACTIVÉE**, portail Opendatasoft (`opendata.vancouver.ca`, PAS
du CKAN) — jeu de données "business-licences", 205 329 lignes réelles
(167 962 au statut "Issued", très à jour, `extractdate` du jour même).

**Découverte structurante, qui a nécessité une nouvelle pièce d'architecture** :
la règle "NON NÉGOCIABLE" du registre exige qu'une licence ne soit un signal
que si elle représente un vrai nouvel établissement, pas un simple
renouvellement. Or Vancouver attribue un NOUVEAU numéro de licence CHAQUE
ANNÉE (le folderyear est encodé dans le numéro lui-même, ex. "26-258507"
pour 2026), et le jeu de données ne couvre qu'une fenêtre glissante de 3 ans
(24/25/26 au 2026-09-01) — impossible de distinguer "nouveau" de
"renouvellement" à partir d'un seul instantané, contrairement à REQ/
Corporations Canada qui remontent sur des décennies. Nouveau miroir local
persistant `LicenceMunicipaleEntry` (partagé entre villes, clé =
municipalité+nom normalisé+adresse normalisée) et helper commun
`falkye/sources/licences_municipales_communes.py:detecter_nouvelles_licences`
— accumule les entreprises+adresses déjà vues d'un scan à l'autre, avec la
MÊME précaution "premier scan ne produit aucun signal" que REQ/Corporations
Canada avant leurs propres corrections de calibration (sinon ~168 000
licences déjà anciennes seraient traitées comme "nouvelles" au premier
scan).

Combiné à la vérification croisée Corporations Canada déjà construite
(`resolve_corp_federale_by_name`, voir plus haut) : DEUX filtres en
cascade, aucun optionnel — (1) jamais vue avant (miroir municipal), (2)
correspond avec confiance à une corporation fédérale existante (pas un
nouveau démarrage, pas une entreprise individuelle).

**Validation de bout en bout, en plusieurs étapes** :
- Premier scan (2 625 licences réelles, fenêtre 90 jours) : 0 signal —
  confirme que le mécanisme "premier scan" fonctionne.
- Mécanisme de diff testé isolément : entreprises retirées puis
  réintroduites correctement redétectées comme nouvelles ; entreprise déjà
  connue correctement exclue.
- Vérification croisée testée dans les deux sens sur un échantillon réel de
  59 grands employeurs vancouvérois : 6 correspondances confiantes (ex.
  "Acme Import & Export Ltd", "KPMG Inc", "Parking Corporation of
  Vancouver") ; la plupart des grandes marques testées (Lululemon, Telus)
  sont incorporées PROVINCIALEMENT en Colombie-Britannique et ne matchent
  donc pas Corporations Canada — limite connue et attendue, pas un bogue.
- **Scan complet de bout en bout (fenêtre 700 jours)** : 294 signaux réels
  produits, dont plusieurs correspondances évidentes de compagnies à
  numéro fédérales (ex. "14690605 CANADA INC." et "14560639 Canada Inc" —
  le nom de l'entreprise contient littéralement son propre numéro de
  corporation fédérale, correspondance à 100.0) et des entreprises nommées
  réelles ("NOVAGEN AI CORP.", "MEWAR INFOTECH LIMITED", "Mira Geoscience
  Limited", etc.).

**Limite de pagination réelle de la plateforme** (Opendatasoft, pas propre à
ce connecteur) : `offset + limit <= 10000` par requête, confirmé — sans
effet sur un scan à fenêtre courte (30-90 jours, défaut du moteur, ~2 900
lignes/90 jours observées), mais borne un appel `--historique-complet`
(avertissement explicite loggé plutôt qu'échec silencieux ou boucle
infinie).

**Toronto — BLOQUÉE, un 2e domaine est requis.** `open.toronto.ca` (déjà
autorisé) n'est que la façade web du portail — confirmé par un appel direct
à `/api/3/action/site_read` (HTTP 404 : ce n'est pas la racine de l'API
CKAN). Le vrai backend CKAN semble hébergé sur un domaine distinct
(probablement `ckan0.cf.opendata.inter.prod-toronto.ca`, à confirmer une
fois autorisé) — même schéma de séparation portail/fichier que Montréal
pour les permis de construction. Le mécanisme commun
(`licences_municipales_communes.py`) est déjà prêt à être réutilisé sans
modification une fois ce domaine confirmé.

**Statut du registre** : `licences_vancouver` ajoutée et `actif` — 14e
source active du prototype, la 6e de la Phase 2. `licences_toronto` ajoutée,
`a_developper` (`blocage_type: reseau`) en attendant le 2e domaine.

## Licences d'affaires — Toronto activée (2e domaine confirmé) (2026-09-01)

Alexandre a autorisé `ckan0.cf.opendata.inter.prod-toronto.ca` — confirmé
être le vrai backend CKAN de Toronto (`open.toronto.ca`, déjà autorisé,
n'est que la façade web : son `/api/3/action/*` retourne 404, pas la racine
de l'API). Même schéma de séparation portail/fichier que Montréal pour les
permis de construction.

Jeu de données "Municipal Licensing and Standards - Business Licences and
Permits", ressource datastore-active `169e90ba-3ae0-43dd-8b2f-919e87002f50` :
159 647 lignes réelles, historique complet depuis 1946 (bien plus profond
que la fenêtre glissante de 3 ans de Vancouver) — interrogée via l'API
Datastore CKAN, même principe que subventions_federales/contrats_federaux.

**Différence structurante avec Vancouver, découverte en validant** : le
numéro de licence de Toronto est un identifiant PERSISTANT (confirmé : 500
lignes échantillonnées, 0 doublon de `Licence No.`) — pas réattribué chaque
année comme à Vancouver. Mais le calibrage "pas un simple renouvellement"
reste nécessaire quand même : une même entreprise obtient parfois plusieurs
numéros de licence successifs au fil des décennies (confirmé sur un exemple
réel — une entreprise avec 4 licences distinctes entre 2002 et 2019, chacune
annulée puis remplacée). Le mécanisme commun
(`licences_municipales_communes.py:detecter_nouvelles_licences`, même
miroir `LicenceMunicipaleEntry`) a donc été réutilisé SANS modification,
avec la même précaution "premier scan ne produit rien" (sinon 159 647
licences historiques seraient toutes traitées comme "nouvelles").

Autres découvertes réelles en construisant le connecteur :
- Champ `Client Name` (nom légal) utilisé comme `nom_entreprise` plutôt que
  `Operating Name` (nom commercial) — plus fiable pour la vérification
  croisée Corporations Canada.
- Licences annulées (`Cancel Date` non vide) exclues, même principe que le
  filtre `status="Issued"` de Vancouver.
- Quirk de qualité de données réel : un champ texte vide est parfois encodé
  par la chaîne littérale `"None"` plutôt qu'un JSON `null` — touche aussi
  de vraies lignes "junk" du jeu de données (catégorie "** Class record not
  on file"), filtrées explicitement plutôt que de produire un signal avec un
  nom/une adresse inventés.

**Validation de bout en bout** : premier scan (1 452 licences réelles,
fenêtre 90 jours) → 0 signal, confirmant le mécanisme "premier scan" ;
deuxième scan simulé → signaux réels produits, dont des compagnies à numéro
fédérales évidentes ("18093504 CANADA INC", correspondance 100.0) et une
entreprise ("9003088 CANADA CORP") avec plusieurs adresses réellement
distinctes confirmées (panneaux mobiles temporaires à des emplacements
différents) — chacune un nouvel établissement légitime, pas un doublon.

**Statut du registre** : `licences_toronto` passe de `a_developper` à
`actif` — 15e source active du prototype, la 7e de la Phase 2.

## Mise à jour de spec : sphère financement, score de pertinence A/AA/AAA (2026-09-01)

Alexandre a communiqué trois décisions produit déjà intégrées au document de
specs général (`docs/spec/repereur-entreprises-croissance-specs.md`, sections
4, 6 et 9bis). Deux des trois sont maintenant construites, testées et
commitées (la troisième, la structure tarifaire à trois plans de la section
9bis, reste une question de portée ouverte — voir plus bas, pas dans ce
fichier de statut réseau puisqu'elle ne touche aucune source).

**Nouvelle sphère de besoin — Financement / accès au capital** (section 4) :
ajoutée à `registry/spheres.yaml`, découverte en croisant des personas
(courtiers en cautionnement, prêteurs alternatifs, investisseurs
providentiels, banquiers d'investissement) qui ne correspondaient à aucune
sphère existante. Aucune nouvelle source ni aucun nouveau type de signal
requis — la sphère utilise `financement_expansion` (déjà actif via
Investissement Québec et les subventions fédérales) comme signal
d'appartenance directe, et déclare ce même type comme
`signal_absence_pertinent` pour le mécanisme de pertinence ci-dessous.

**Score de pertinence, deuxième axe indépendant** (section 6, restructurée) :
voir `docs/ARCHITECTURE.md` pour le détail complet de la conception
(`falkye/pertinence.py`). En résumé pour ce journal : trois paliers A/AA/AAA
calculés à partir du `MatchResult` déjà produit par `matching.py` (aucune
nouvelle donnée collectée, une nouvelle couche de calcul, comme demandé),
deux bonus additifs (signal par absence, vélocité/trajectoire), un curseur de
sensibilité dédié (`Profile.sensibilite_pertinence`, indépendant de
`sensibilite_confiance`), et une décision de notification en MATRICE (les
deux seuils doivent être franchis, jamais une moyenne des deux axes).

Migration de la base de développement réelle (1 profil, 311 notifications
réelles générées avant cette restructuration) : `profiles.sensibilite`
renommée `sensibilite_confiance` + nouvelle colonne `sensibilite_pertinence`
(défaut `moyen`) ; `notifications.niveau` renommée `niveau_confiance` +
nouvelles colonnes `score_pertinence`/`niveau_pertinence`, laissées `NULL`
pour les 311 notifications historiques — jamais de valeur de pertinence
inventée pour combler l'historique (principe directeur #1). Affichées comme
"non disponible" plutôt qu'un palier fabriqué, dans le courriel de
notification comme dans le résumé périodique et la CLI.

**Non construit, en attente d'une clarification de portée avant de
commencer** : la structure tarifaire à trois plans (Écho/Radar/Radar+,
section 9bis) implique un portail de sources payantes avec paiement intégré
(Radar) et gestion de clés API utilisateur (Radar+) — aucun backend de
paiement ni aucune source payante n'est encore branché au produit pour
servir de premier cas concret à construire contre. Question à poser à
Alexandre avant tout travail d'architecture sur ce point (voir le message de
suivi de cette session).

## Portail Radar/Radar+ construit contre un premier cas concret (2026-09-02)

Réponse d'Alexandre à la question de portée ci-dessus : priorité à l'option 1
(construire contre un cas réel plutôt que dans l'abstrait). Décisions :
première source payante = agrégateur de recrutement tiers (TheirStack ou
Apify, choix précis en attente d'un comparatif de prix — non bloquant) ;
solution de paiement pour Radar = Stripe, tranchée directement sans
comparatif ; Radar+ (gestion de clés API utilisateur) explicitement différé
à une session future, une fois Radar validé avec ce premier cas.

**Architecture livrée** (voir `docs/ARCHITECTURE.md` pour le détail) :

- `SourceDef.plan_minimum` (registre) + `Profile.plan` (`PlanTarifaire` :
  ECHO/RADAR/RADAR_PLUS, `falkye/models/profile.py`) — troisième porte dans
  `falkye/engine.py`, indépendante des deux axes confiance/pertinence,
  appliquée à la SÉLECTION des signaux par profil, jamais à l'ingestion
  (qui reste globale au dossier cumulatif, comme toute source).
- `falkye/sources/agregateur_recrutement.py` — connecteur générique par
  fournisseur (interface `FournisseurAgregateur`, `TheirStackProvider` et
  `ApifyActeurGeneriqueProvider`, sélection par variable d'environnement).
  L'entrée `agregateur_recrutement_tiers` du registre (déjà présente comme
  placeholder budgétaire, spec section 8) est mise à jour : `plan_minimum:
  radar`, `connecteur` pointé vers le nouveau module, `blocage_type` passé
  de `budgetaire` à `reseau` (le financement n'est plus le blocage — un vrai
  blocage réseau/fournisseur demeure, voir plus bas).
- `falkye/billing/stripe_client.py` — paiement intégré Stripe : session
  Checkout (`creer_session_paiement_radar`), traitement d'événement webhook
  déjà décodé (`traiter_evenement_webhook`, séparé de la vérification de
  signature pour rester testable et utilisable sans point de terminaison
  HTTP public), synchronisation `Subscription` (nouveau modèle, état Stripe
  brut) → `Profile.plan` (état effectif). Commandes CLI : `billing
  radar-checkout`, `billing statut`, `billing traiter-webhook --fichier`
  (chemin manuel, même principe que l'import manuel appliqué à un webhook),
  `billing definir-plan` (bascule manuelle pour tester sans Stripe réel).

**NON VALIDÉ contre du réel, sur les deux fronts, et documenté comme tel** :

- Agrégateur de recrutement : `theirstack.com` et `apify.com` sont bloqués
  par le proxy de sortie réseau de cet environnement de développement (même
  classe de blocage que `registreentreprises.gouv.qc.ca` pour le REQ — voir
  plus haut dans ce fichier), et aucune clé API réelle n'existe de toute
  façon tant que le choix précis du fournisseur n'est pas tranché. La forme
  exacte de la réponse (`_normaliser_theirstack`, `_normaliser_apify`) est
  construite d'après des résumés de documentation publique, avec tolérance à
  plusieurs noms de champs plausibles plutôt qu'une seule hypothèse figée —
  jamais confirmée par un vrai appel. Source laissée `a_developper` dans le
  registre, jamais `actif`, jusqu'à validation réelle.
- Paiement Stripe : aucun compte Stripe réel disponible dans cet
  environnement — `falkye/billing/stripe_client.py` est construit et testé
  unitairement contre le SDK Stripe mocké (`tests/test_billing.py`), jamais
  exécuté contre une vraie session de paiement ni un vrai webhook livré à un
  point de terminaison public (qui n'existe pas non plus encore).

**Bogue réel trouvé et corrigé en migrant la base de développement** :
`falkye/models/profile.py::Sensibilite` (`Enum(..., native_enum=False)` sans
`values_callable`) stocke le NOM du membre Python (`"MOYEN"`, majuscules),
pas sa valeur (`"moyen"`) — confirmé en confrontant les colonnes déjà
peuplées par l'ORM (`sensibilite_confiance`, `niveau_confiance` : bien
`"MOYEN"`/`"ELEVE"` en majuscules dans la vraie base). La migration de
pertinence du 2026-09-01 avait inséré `sensibilite_pertinence='moyen'` en
minuscule par script SQL brut — valide en lecture SQL directe (vérifié à
l'époque), mais silencieusement CASSÉ pour toute lecture via l'ORM
(`LookupError`), jamais remarqué faute d'avoir rechargé ce profil via
`Profile`/SQLAlchemy après cette migration. Trouvé en migrant la base pour
cette mise à jour (`plan` aurait reproduit exactement la même erreur si non
corrigé avant commit) ; corrigé directement dans `data/falkye.sqlite3`
(`sensibilite_pertinence` et `plan` remis en majuscules) et vérifié par une
relecture ORM complète du profil réel et de ses 311 notifications.

**Migration de la base de développement réelle** (1 profil, 311
notifications) : `profiles.plan` ajoutée (`'ECHO'`, valeur réelle — aucun
profil n'était Radar/Radar+ avant cette structure, pas une valeur inventée) ;
table `subscriptions` créée via `create_all()` (vide, aucun abonnement réel).

**Hors de cette construction, signalé explicitement** : le document de specs
mis à jour (section "Tableau de bord et statut de suivi — Radar et Radar+
seulement") introduit, en plus de la structure de plans ci-dessus, un
tableau de bord complet (cartes de dossiers, statut de suivi extensible),
un mécanisme de rétroaction utilisateur maintenant résolu via ce statut de
suivi (contredit le report explicite précédent, voir plus haut dans ce
fichier), et trois fonctionnalités transversales (modèles de premier
contact, carte géographique, filtre par taille d'entreprise). Aucune de ces
fonctionnalités n'est construite dans cette mise à jour — la demande
d'Alexandre portait explicitement sur le portail/paiement/connecteur, pas
sur le tableau de bord. À confirmer avant d'entamer ce chantier, nettement
plus large (interface, pas seulement moteur).
