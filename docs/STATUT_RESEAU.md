# Statut réseau et découvertes — Phase 1

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
| `d4bf66bykfyaf.cloudfront.net` | Fichiers CSV réels de Corporations Canada (AWS CloudFront) — le CKAN de open.canada.ca n'héberge que les métadonnées | ⛔ **Pas encore autorisé** — Corporations Canada activée au registre mais non validée avec de vraies données (voir plus bas) |
| `www.investquebec.com` | PDF de la liste de divulgation Investissement Québec | ⛔ **Pas encore autorisé** — Investissement Québec activée au registre mais non validée avec de vraies données (voir plus bas) |

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
réseau du projet) : `observador/sources/req.py::ingest_snapshot` fait **une seule
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

**Cause la plus probable du blocage** : mes propres appels `curl` de diagnostic
manuel, répétés à plusieurs reprises vers cette même URL en quelques minutes lors
du dépannage initial de l'accès réseau (avant même que le connecteur Python soit
exécuté une seule fois) — pas un comportement du pipeline applicatif, qui n'a
jamais atteint cette étape avec succès. Le blocage a persisté au-delà d'une heure
malgré l'absence de nouvelles requêtes de ma part dans l'intervalle, ce qui
suggère soit une fenêtre de blocage Cloudflare plus longue qu'anticipé, soit un
effet combiné avec d'autres sessions partageant la même IP sortante du pool cloud
— les deux causes restent plausibles, mais la responsabilité de mes requêtes de
diagnostic répétées est la plus directe et la plus certaine des deux. Décision :
ne plus insister par des tests manuels répétés (déjà appliqué) ; une seule
tentative espacée par le connecteur réel est sans risque d'aggraver la situation.
À réessayer plus tard, à faible fréquence ; si le blocage persiste au-delà de la
Phase 1, envisager de contacter le Registraire des entreprises pour un accès non
bloqué, ou de générer le fichier depuis un réseau différent puis de l'importer
dans l'environnement.

**Impact sur la Phase 1** : le connecteur REQ (`observador/sources/req.py`) est
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

Voir `observador/registry/sources.yaml` (entrée `rdprm`) pour le détail complet :
consultation payante à l'unité (11 $/nom, 4 $/NIV), aucune API publique, aucun flux
en vrac. Décision produit (Alexandre, 2026-08-31) : statut `a_developper`,
activation Phase 2 avec déclenchement ciblé par entreprise déjà détectée — jamais
un balayage en vrac.

## Bug de performance corrigé pendant la validation

`observador/resolution.py::_find_unresolved_company` comparait en Python, à
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

## Corporations Canada et Investissement Québec — connecteurs écrits, non encore validés

Les deux nouvelles sources (voir `registry/sources.yaml`) sont actives au
registre (demande d'Alexandre, 2026-08-31), mais leurs connecteurs n'ont **pas**
pu être exécutés contre de vraies données — chacun bloqué par un domaine réseau
distinct pas encore autorisé (voir tableau en haut de ce document) :
`d4bf66bykfyaf.cloudfront.net` (fichiers CSV de Corporations Canada) et
`www.investquebec.com` (PDF de la liste de divulgation). Les deux connecteurs
sont écrits contre la meilleure information publique disponible (structure de
colonnes estimée pour Corporations Canada, URL réelle confirmée par recherche
pour Investissement Québec), avec le même garde-fou que req.py : échec
explicite plutôt que mauvaise interprétation si la structure réelle diverge.
**Ajouter ces deux domaines pour compléter la validation.**

## Import manuel (RDPRM) — mécanisme testé, source activée

Le mécanisme générique d'import manuel (spec section 9, voir
`docs/ARCHITECTURE.md`) a été testé de bout en bout le 2026-08-31 avec la CLI
(`observador import-manuel ajouter`) : création du signal, résolution NEQ
tentée via le miroir local (REQ), et déclenchement immédiat du reste du
pipeline pour les profils existants — comportement conforme (0 notification
en l'absence d'un vrai REQ chargé, exactement le même garde-fou que pour SEAO).
Aucun appel réseau impliqué dans ce mécanisme — c'est entièrement local une
fois que l'utilisateur a lui-même obtenu le document RDPRM.

## Prochaine étape

Domaines réseau encore à ajouter pour compléter la validation Phase 1 :
`d4bf66bykfyaf.cloudfront.net` (Corporations Canada) et `www.investquebec.com`
(Investissement Québec). Dès que ces deux domaines sont autorisés et que le
rate-limit REQ se lève, relancer une recherche ponctuelle complète
(`observador scan ponctuel`) pour obtenir la première notification consolidée
de bout en bout avec de vraies données sur les 8 sources actives, incluant une
résolution NEQ réussie et un enrichissement web réel.
