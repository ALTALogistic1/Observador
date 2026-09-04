# FALKYE — Chantier 1 : moteur de diff d'instantanés et quarantaine

Mandat de développement destiné à Claude Code. À exécuter **seul**, sans entamer aucun autre chantier
du document `falkye-audit-et-mandat.md`, qui sert de contexte et non de liste de travail.

---

## Pourquoi ce chantier passe avant tout le reste

Une partie des sources de FALKYE ne fournit **aucune date d'événement**. Le RACJ le dit
explicitement — « aucune date de délivrance dans le registre, diff hebdomadaire nécessaire » — et c'est
aussi le cas des établissements alimentaires de Montréal, des licences municipales, de la
Nouvelle-Écosse. Pour ces sources, un signal n'existe pas dans la donnée : il **naît de la comparaison
entre deux états successifs**.

Deux conséquences, et c'est ce qui rend ce chantier urgent plutôt qu'important.

**Le coût de l'inaction est irrécupérable, pas seulement croissant.** Une source instantanée qui tourne
sans conserver son état complet ne perd pas du temps de développement : elle perd des événements
définitivement. Les ouvertures survenues entre deux exécutions non conservées n'existeront jamais nulle
part. Aucun développement ultérieur ne les récupérera.

**Un diff aberrant est le seul scénario du projet qui coûte la crédibilité d'un coup.** Le jour où un
diffuseur renomme une colonne, change son encodage ou réassigne ses identifiants internes, le diff
produit des milliers de fausses ouvertures et une vague de notifications absurdes part chez tous les
clients le même matin. Ça se prévient en une journée de code.

---

## Portée — ce qui est dans le chantier et ce qui n'y est pas

**Dans le chantier :** conservation d'état, moteur de diff générique, détection de changement de
schéma, règle de quarantaine, levée de quarantaine journalisée, surface CLI minimale, tests.

**Hors du chantier, à ne pas commencer :** le tableau de bord de santé de source (chantier 2), toute
modification de l'identité d'entreprise ou du pivot NEQ (chantier 3), la confiance d'appariement
(chantier 4), la cadence de notification (chantier 8). Si une de ces frontières devient gênante en
cours de route, **le signaler plutôt que de la franchir**.

**Ne pas construire le connecteur RACJ dans ce chantier.** Le moteur doit être conçu pour l'accueillir,
et validé contre des sources **déjà actives avec du vrai volume** — les licences de Toronto (159 647
lignes réelles confirmées) et de Vancouver sont les cibles naturelles.

---

## Phase 0 — Constat avant de coder

**À faire en premier, et à rapporter avant d'écrire quoi que ce soit d'autre.** Ne présumer aucun des
points ci-dessous.

1. Inventorier les sources actives et classer chacune : **type instantané** (pas de date d'événement,
   la détection vient du diff) ou **type événement** (chaque enregistrement porte sa propre date).
2. Pour chaque source de type instantané, déterminer ce qui est conservé aujourd'hui entre deux
   exécutions : l'état complet, seulement les écarts, ou rien.
3. Vérifier si un mécanisme de diff existe déjà quelque part, même partiel ou spécifique à une source.
   S'il existe, ce chantier le généralise plutôt que de le remplacer.
4. Rapporter le résultat. **Si une source de type instantané tourne actuellement sans conservation
   d'état, c'est la première chose à corriger**, avant même la quarantaine.

---

## Ce qu'il faut construire

### 1. Conservation d'état

Un état courant par source, mis à jour à chaque exécution réussie. Pas un historique de copies
complètes — l'état courant suffit, puisque le diff se fait toujours contre la dernière exécution
réussie.

Par ligne conservée, au minimum : la **clé naturelle**, une **empreinte** des champs pertinents, les
données normalisées, la date de première apparition et la date de dernière observation.

**La clé naturelle est déclarée par source dans le registre, jamais devinée.** Elle varie franchement :
le RACJ a `NoPermis` et `Neq`, Montréal a `business_id`, la Nouvelle-Écosse n'en a aucune et exige une
clé composite (nom + adresse + ville). Le cas néo-écossais est fragile par nature — un établissement
renommé ressemble à une fermeture suivie d'une ouverture — et c'est une limite à documenter, pas à
masquer.

**L'empreinte porte uniquement les champs pertinents**, jamais la ligne entière. Sinon un changement
cosmétique sans intérêt — espace en trop, colonne que FALKYE n'utilise pas, réordonnancement — produit
une fausse modification. Si la grille `champs_pertinents.yaml` n'est pas encore livrée pour une source,
utiliser la liste de champs déclarée au registre et le noter comme dette.

Conserver aussi le fichier brut des dernières exécutions, en archive, pour pouvoir inspecter un diff
suspect. Un petit nombre de générations suffit.

### 2. Run de référence

La première exécution réussie d'une source n'a rien à quoi se comparer : **toutes ses lignes sont des
apparitions**. Ce cas doit être traité explicitement.

Un run de référence **amorce l'état et n'émet aucun signal**. Il ne déclenche pas la quarantaine — un
volume de 100 % d'apparitions y est normal, pas suspect. Ce comportement existe déjà en pratique dans
le projet : Corporations Canada est décrit comme « un seul run de référence effectué, attendu ». Il
s'agit de le formaliser plutôt que de l'inventer.

### 3. Moteur de diff

Trois ensembles en sortie, jamais fusionnés : **apparitions**, **disparitions**, **modifications** —
ces dernières accompagnées de la liste des champs qui ont changé, puisque toutes les modifications
n'ont pas la même valeur de signal. La hausse de `Capacite` du RACJ est un signal d'agrandissement; un
changement de code postal formaté différemment n'est rien.

Le diff produit des **candidats de signal**, pas des notifications. Le reste du pipeline —
résolution d'identité, score, pertinence, routage — reste inchangé et hors de ce chantier.

### 4. Détection de changement de schéma

Comparer, à chaque exécution, la liste des colonnes et leurs types à ceux de l'exécution précédente.

- Colonne **pertinente retirée**, ou dont le type change → quarantaine immédiate, quel que soit le
  volume du diff.
- Colonne **ajoutée** → avertissement journalisé, pas de quarantaine. Les diffuseurs ajoutent des
  colonnes régulièrement et ça ne casse rien.
- Colonne **renommée** → indétectable comme telle, se présente comme un retrait plus un ajout, et
  c'est le retrait qui commande. Comportement voulu.
- **Échec de lecture** au-delà d'un seuil de lignes (encodage, format, séparateur) → quarantaine, sans
  interrompre le pipeline des autres sources.

### 5. Règle de quarantaine

Le principe : quand un diff dépasse le plausible, **rien n'est publié, l'état précédent reste intact**,
et l'exécution attend une révision humaine.

Trois décisions de conception à respecter :

**Deux seuils qui doivent être franchis ensemble**, un pourcentage et un nombre absolu de lignes. Le
pourcentage seul mettrait en quarantaine les petites sources sur du bruit normal; l'absolu seul ne
verrait rien venir sur les grosses. Les deux ensemble, jamais l'un ou l'autre.

**Des seuils distincts par type d'écart.** Une disparition massive est plus suspecte qu'une apparition
massive dans un registre de licences : elle signale généralement un extrait tronqué, pas une vague de
fermetures. Apparitions, disparitions et modifications méritent donc leurs propres seuils.

**Seuils par source, avec des valeurs par défaut conservatrices**, surchargeables au registre. Les
sources n'ont ni la même volatilité ni la même taille — le RACJ bouge chaque semaine, un palmarès
annuel ne bouge qu'une fois par an.

### 6. Levée de quarantaine

Action explicite et journalisée : qui, quand, quel motif. Réservée au mode opérateur.

Deux issues possibles, toutes deux à supporter : **accepter le diff** (il était réel — une réforme
réglementaire, une fusion municipale) et l'état se met à jour normalement; ou **rejeter le run** et
l'état précédent est conservé en attendant la prochaine exécution.

### 7. Surface CLI minimale

De quoi lister les quarantaines en cours, inspecter le détail d'un diff mis en quarantaine, et le lever
avec un motif. Suivre les conventions de commande existantes du projet plutôt que d'en inventer.

---

## Les deux questions de la section 11 — réponses proposées, à implémenter et tester

La charte, section 11, exige qu'avant de considérer un mécanisme terminé, on réponde explicitement à
« que se passe-t-il quand deux éléments de la même dimension sont en désaccord? ». Voici les réponses
retenues. Les implémenter telles quelles, et les tester.

### Question 1 — Deux sources en quarantaine dans la même exécution

**La quarantaine est strictement par source.** Deux sources en quarantaine sont deux incidents
indépendants et aucune des deux ne bloque le pipeline des autres.

**Mais le cumul est lui-même un signal, et il mérite une alerte distincte.** Deux diffuseurs
indépendants qui changent leur format le même jour est improbable; deux quarantaines simultanées
pointent bien plus vraisemblablement vers un problème **de notre côté** — réseau, disque, déploiement
récent, dépendance mise à jour. Émettre une alerte d'exploitation distincte au-delà d'une quarantaine
par exécution, formulée comme une suspicion d'incident local et non comme un problème de source.

### Question 2 — Une source en quarantaine alimente un signal déjà partiellement corroboré

**Un run mis en quarantaine n'entre nulle part.** Aucune de ses données ne rejoint le dossier cumulatif,
même partiellement, même pour une entreprise dont un autre signal sain est déjà présent. Le run est
traité comme s'il n'avait pas eu lieu.

**Ce qui a déjà été publié reste publié.** Les corroborations établies avant la quarantaine l'ont été
avec des données valides au moment où elles l'étaient. On ne les rétracte pas.

**Aucun recalcul rétroactif du bonus de corroboration** ne doit inclure les données d'un run en
quarantaine. C'est le point qui compte : accepter une ingestion partielle créerait un état où plus
personne ne peut dire quels faits d'un dossier sont provisoires et lesquels sont confirmés — exactement
le genre d'ambiguïté qui rend un score inexplicable.

**Frontière avec le chantier 2, à ne pas franchir ici.** La question « que faire des signaux déjà
publiés par un run qu'on découvre mauvais **après coup** » est une question de rétraction, elle
appartient à la santé de source. Ce chantier empêche seulement les mauvais runs d'entrer.

---

## Tests exigés

À intégrer à la suite existante, jamais dans une suite parallèle. Aucun chantier n'est terminé sans
ces tests verts.

1. **Run de référence** — première exécution : l'état est amorcé, zéro notification émise, aucune
   quarantaine déclenchée malgré 100 % d'apparitions.
2. **Run normal** — trois apparitions produisent trois candidats de signal, l'état est mis à jour.
3. **Diff aberrant** — 60 % des clés changent : **zéro notification**, état précédent intact, diff
   archivé et consultable, source en quarantaine.
4. **Petite source** — 60 % de variation sur 20 lignes : pas de quarantaine, le seuil absolu n'étant
   pas atteint. Vérifie que les deux seuils fonctionnent bien ensemble et non l'un ou l'autre.
5. **Colonne pertinente retirée** — quarantaine immédiate, indépendamment du volume du diff.
6. **Colonne non pertinente ajoutée** — pas de quarantaine, avertissement journalisé, traitement normal.
7. **Changement cosmétique** — modification d'un champ hors `champs_pertinents` : zéro modification
   détectée. Vérifie que l'empreinte ne porte que les champs pertinents.
8. **Disparition massive contre apparition massive** — le même pourcentage déclenche la quarantaine
   dans un cas et pas dans l'autre, si les seuils diffèrent. Vérifie l'asymétrie.
9. **Fichier illisible** — échec de lecture au-delà du seuil : quarantaine, aucune exception non
   rattrapée, pipeline des autres sources intact.
10. **Isolation** — une source en quarantaine n'empêche aucune autre source de publier ses signaux
    dans la même exécution.
11. **Question 1** — deux quarantaines dans la même exécution : deux incidents indépendants **plus**
    une alerte d'exploitation distincte.
12. **Question 2** — une source en quarantaine et une source saine touchent la même entreprise : aucun
    fait du run en quarantaine n'apparaît au dossier cumulatif, et le score de corroboration est
    identique à ce qu'il serait si la source en quarantaine n'avait pas tourné du tout.
13. **Levée acceptée** — l'état se met à jour, la levée est journalisée avec identité, horodatage et
    motif.
14. **Levée rejetée** — l'état précédent est conservé et l'exécution suivante repart de cet état.

---

## Vérification macro — obligatoire avant de déclarer le chantier fini

La charte, section 11, documente une erreur déjà commise : `champs_pertinents.yaml` avait été vérifié
contre le REQ seulement, jamais contre les autres sources actives. **Ne pas refaire ça ici.**

Avant de considérer le chantier terminé, faire tourner le moteur contre **toutes** les sources actives
de type instantané, pas seulement celle qui a servi d'exemple, et rapporter pour chacune : la clé
naturelle retenue, le nombre de lignes de l'état amorcé, le résultat du premier diff réel, et les
seuils de quarantaine choisis avec leur justification.

Les licences de Toronto sont la meilleure cible de validation — source active, 159 647 lignes réelles
déjà confirmées, volume suffisant pour que les seuils veuillent dire quelque chose.

---

## Ce qui doit être livré

1. Le rapport de la phase 0, **avant le code**.
2. Le code du moteur, la conservation d'état, la détection de schéma et la quarantaine.
3. Les quatorze tests ci-dessus, verts, dans la suite existante.
4. Le rapport de vérification macro par source.
5. La mise à jour de la documentation d'architecture, dans le même format que les scénarios
   d'authentification et de lien sphère↔service déjà documentés.
6. La liste des seuils par défaut retenus, avec leur justification — c'est une décision à valider avec
   Alexandre, pas une constante à enfouir dans le code.

**Ne rien commencer d'autre.** Si le chantier révèle un problème appartenant à un autre chantier, le
consigner dans le `DiagnosticJournal` et le rapporter, sans l'attaquer.
