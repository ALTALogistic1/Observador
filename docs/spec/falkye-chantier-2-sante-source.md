# FALKYE — Chantier 2 : santé de source

Mandat de développement destiné à Claude Code. À exécuter **seul**, après confirmation que le
chantier 1 est terminé — connecteurs rebranchés inclus. `falkye-audit-et-mandat.md` et
`charte-falkye.md` servent de contexte, pas de liste de travail.

---

## Pourquoi ce chantier suit immédiatement le premier

Le chantier 1 traite le cas où une source produit trop de changements. Celui-ci traite le cas inverse,
plus fréquent : une source qui ne produit rien.

Trois sources sont aujourd'hui à zéro signal pour trois raisons complètement différentes. Corporations
Canada est « actif, 0 signal à ce jour (attendu) ». Le RDPRM mécanisme 1 est un stub **et** attend une
décision de mécanisme et de budget qui n'a pas été prise. TheirStack est marqué actif, mais attend une
manœuvre non technique d'Alexandre — création de compte et clé API — sans laquelle le connecteur ne
produit rien. Le chantier 1 en ajoute une quatrième : une source en quarantaine ne produit rien non
plus.

**Au moins cinq causes distinctes pour un même symptôme observable**, dont deux qui ne sont pas
techniques. La distinction tient aujourd'hui dans la tête d'Alexandre, ce qui fonctionne à cette
échelle. Avec vingt sources et quelques mois d'écart, un connecteur qui cesse de fonctionner
ressemblera à un territoire calme, à une source qui attend une clé, ou à une autorisation jamais
demandée — et rien ne le signalera, puisque l'absence de résultat ne déclenche aucune alerte.

**Le chantier 1 a produit la matière première de celui-ci.** La journalisation de l'amplitude de chaque
diff, demandée pour permettre la calibration future des seuils, est exactement la donnée dont la norme
de volume a besoin. Ce chantier la consomme plutôt que d'en créer une nouvelle.

---

## Portée

**Dans le chantier :** historique d'exécution par source, norme de volume apprise, taxonomie des états
de santé, alertes de dérive dans les deux sens, tableau de bord d'exploitation interne, traitement des
signaux publiés par une source ensuite déclarée défaillante.

**Hors du chantier, à ne pas commencer :** l'identité d'entreprise et le niveau de vérification par
territoire (chantier 3), la confiance d'appariement (chantier 4), le registre légal et l'état `bloquée`
(chantier 6), et surtout **tout ce qui touche la perception du silence par l'utilisateur final**
(chantier 14). Ce chantier-ci est un outil d'exploitation interne. Ce que l'abonné voit quand il ne
reçoit rien est un autre chantier et une autre décision.

---

## Phase 0 — Constat avant de coder

À rapporter avant d'écrire autre chose.

1. Ce qui est conservé aujourd'hui d'une exécution de source : y a-t-il un historique de runs, ou
   seulement le dernier état?
2. Comment une exécution en échec se distingue actuellement d'une exécution réussie sans résultat —
   s'il y a une distinction.
3. Ce que le chantier 1 a laissé comme métadonnées de run exploitables ici, pour les réutiliser plutôt
   que de créer une structure parallèle.
4. Pour chacune des sources actives : sa cadence de publication réelle attendue (hebdomadaire,
   mensuelle, trimestrielle, annuelle) et sa saisonnalité connue, si elle en a une.
5. **Le relevé des sources bloquées par une action externe d'Alexandre**, avec l'action précise
   attendue pour chacune — clé API, compte à créer, jeton, autorisation gouvernementale, décision
   budgétaire ou de mécanisme. La liste des tâches restantes en contient déjà l'essentiel; il s'agit
   de la faire entrer dans le registre plutôt que de la laisser dans un document séparé. Ne pas présumer
   qu'une source marquée `actif` est opérationnelle : TheirStack l'est au registre et ne produit rien
   sans sa clé.

---

## Ce qu'il faut construire

### 1. Historique d'exécution par source

Chaque exécution laisse une trace, y compris — surtout — celles qui n'aboutissent pas.

**Trois issues distinctes, jamais confondues en un booléen :**
- **Échec technique** — la source n'a pas pu être lue : réseau, authentification, fichier absent,
  format illisible. La donnée n'a jamais été obtenue.
- **Mise en quarantaine** — la donnée a été obtenue et lue, mais le diff a été jugé aberrant
  (chantier 1). Techniquement réussie, volontairement non publiée.
- **Réussite publiée** — la donnée a été obtenue, lue, comparée, et ses résultats sont entrés dans le
  pipeline.

« Dernière exécution réussie » doit désigner sans ambiguïté la troisième, jamais la deuxième.

Conserver aussi, par exécution : le volume de lignes lues, l'amplitude du diff (déjà journalisée au
chantier 1), la durée, et le taux d'anomalies de la donnée d'entrée — dont le taux de clés dupliquées
mis en place pour Toronto, qui devient ici un indicateur de santé et pas seulement une correction.

### 2. Norme de volume apprise, sensible à la cadence

Un écart ne veut rien dire sans norme, et une norme plate ne fonctionne pas ici : les sources n'ont
pas du tout le même rythme. Le RACJ bouge chaque semaine; un palmarès annuel ne publie qu'une fois par
an, et onze mois de silence y sont parfaitement normaux.

**La norme se calcule par source, sur sa propre cadence déclarée**, jamais sur une moyenne globale.
Les sources à saisonnalité connue — permis saisonniers, palmarès — doivent pouvoir déclarer leur
période creuse plutôt que de déclencher une alerte chaque année à la même date.

**Alerter dans les deux sens.** Un volume anormalement bas indique souvent un connecteur qui se
dégrade sans cesser de fonctionner — le cas le moins visible. Un volume anormalement haut resté sous
le seuil de quarantaine mérite aussi d'être signalé : ça peut précéder ce que le chantier 1
attraperait la semaine suivante.

### 3. Taxonomie des états de santé

Un registre extensible, pas une énumération figée — d'autres états s'ajouteront, dont l'état `bloquée`
du chantier 6. Concevoir le champ pour l'accueillir sans restructuration, sans le construire ici.

Au minimum, distinguer :
- **Saine, territoire calme** — la source fonctionne, il ne se passe rien. État normal.
- **Saine, période creuse déclarée** — silence attendu et documenté, pas une anomalie.
- **Non implémentée** — le stub. N'a jamais produit et n'était pas censé produire.
- **En attente d'une action externe d'Alexandre** — l'état le plus courant en ce moment. La source
  est prête ou presque, mais attend une manœuvre non technique que le code ne peut pas déclencher :
  créer un compte et fournir une clé API (TheirStack), trancher un mécanisme et une décision
  budgétaire (RDPRM), obtenir une autorisation gouvernementale (OQLF), fournir un jeton (intégrations
  CRM), configurer un moyen de paiement.
  **Le champ nomme l'action attendue**, pas seulement l'état — « en attente d'une clé API » et « en
  attente d'une autorisation gouvernementale » ne se résolvent ni de la même façon ni dans les mêmes
  délais. C'est aussi le point de raccord avec l'échéance de décision de la charte, section 15 : une
  source en attente sans échéance finit par sortir du suivi, comme ce fut le cas pour Crunchbase.
- **Jamais validée en réel** — construite, testée contre des mocks, jamais confrontée au vrai service.
  Rejoint le troisième état de la grille des fonctionnalités (chantier 10, faille H). **Distinct de
  l'état précédent** : ici l'action externe a été faite, la confrontation au réel non.
- **En quarantaine** — chantier 1.
- **Défaillante** — a produit par le passé, ne produit plus, sans cause déclarée.

**Séparer les deux premiers états du dernier est l'objet du chantier.** Quand le code ne peut pas
faire la distinction automatiquement, il demande une déclaration explicite plutôt que de laisser
l'ambiguïté.

### 4. Fenêtre de rattrapage de la veille continue

Rattaché à ce chantier après avoir été trouvé et consigné pendant le chantier 1
(`DiagnosticJournal`, entrée #23).

`run_veille_continue` calcule aujourd'hui `since = maintenant - 30 jours` à chaque exécution, sans
consulter la date de la dernière exécution réussie. Si l'intervalle réel entre deux exécutions dépasse
la fenêtre, les événements plus anciens ne sont pas repris — pour toute source filtrable par `since`,
pas seulement celles de type instantané.

Le correctif appartient ici plutôt qu'ailleurs parce qu'il a besoin de ce que ce chantier construit :
la date de la **dernière exécution réussie** au sens strict, celle qui a publié, pas celle qui a été
mise en quarantaine.

**À construire.**
- `since` dérivé de la dernière exécution réussie, avec la fenêtre fixe comme plancher plutôt que
  comme valeur.
- Un **plafond de fenêtre par source**, pour qu'une reprise après une longue interruption ne demande
  pas un historique que la source refuse de servir, ou qui dépasse ce qu'elle conserve.
- **Un relevé préalable, avant de coder :** pour chaque source filtrable par `since`, déterminer si
  son historique reste interrogeable au-delà de 30 jours. La réponse décide de la nature du problème.
  Là où l'historique est disponible, ce qui a été manqué se rattrape par une reprise ponctuelle à
  fenêtre élargie — c'est du travail, pas une perte. Là où la source n'expose qu'une fenêtre récente,
  ce qui est passé ne revient pas, et seule la correction empêche que ça se reproduise.

**Question de la section 11.** Que se passe-t-il quand la dernière exécution réussie est très
ancienne — l'exécution suivante demande-t-elle tout l'intervalle d'un coup, au risque d'un volume qui
déclencherait la quarantaine du chantier 1? Une reprise longue et une exécution normale ne doivent pas
être évaluées avec les mêmes seuils.

### 5. Tableau de bord d'exploitation

Interne, séparé du tableau de bord client, dans le code comme dans les libellés. Aucun état de santé ne
doit pouvoir fuir vers l'interface utilisateur sous une forme qui nomme une source (charte,
section 6) — c'est une frontière à vérifier, pas à supposer.

---

## Les deux questions de la section 11 — réponses proposées, à implémenter et tester

### Question 1 — Une source est déclarée défaillante après avoir contribué à des signaux déjà publiés

Cette question avait été explicitement reportée du chantier 1 vers celui-ci. Il faut y répondre ici.

**Distinguer deux cas, parce qu'ils n'appellent pas la même réponse.**

Une source **muette** — connecteur cassé, rien produit — ne pose pas de problème rétroactif : il n'y a
rien à rétracter, seulement des signaux futurs qui n'arriveront pas.

Le cas à traiter est celui d'une source ayant produit des données partiellement erronées restées sous
le seuil de quarantaine. Règle retenue :

**Pas de suppression silencieuse.** Un prospect déjà livré peut avoir été contacté. Le retirer ferait
perdre à l'utilisateur la trace d'une action qu'il a posée, sans explication.

**Recalculer plutôt que supprimer.** Les faits issus d'une exécution rétroactivement invalidée sont
marqués comme tels dans le dossier cumulatif, et le score est recalculé sans eux. Si le prospect tombe
alors sous le seuil, il est **marqué dans le tableau de bord**, pas retiré.

**Ce qui n'a pas encore été livré ne part pas.** La distinction entre « déjà vu par l'utilisateur » et
« en attente de livraison » commande le traitement.

**Principe général qui en découle, à respecter partout : le dossier cumulatif se corrige, il ne
s'efface pas.** Un fait invalidé reste visible comme invalidé.

### Question 2 — Deux sources qui se corroborent mutuellement tombent ensemble

**La corroboration déjà calculée tient.** Elle a été établie à un moment où les deux sources étaient
saines, avec des données valides à ce moment-là.

**Aucun nouveau bonus de corroboration ne se calcule à partir d'une source en état dégradé** —
quarantaine, défaillante, ou jamais validée. La corroboration suppose deux observations indépendantes
fiables; une source dégradée n'en fournit pas une.

**Le cumul est lui-même un indice**, comme au chantier 1 : deux sources indépendantes qui cessent de
fonctionner en même temps s'expliquent plus souvent par une cause commune de notre côté — réseau,
disque, déploiement, dépendance mise à jour — que par deux incidents distincts chez deux diffuseurs.
Émettre une alerte d'exploitation distincte, formulée comme une hypothèse d'incident local.

---

## Tests exigés

À intégrer à la suite existante.

1. **Trois issues distinctes** — échec technique, quarantaine et réussite publiée produisent trois
   traces différentes, et « dernière exécution réussie » ne désigne que la troisième.
2. **Territoire calme** — une source qui tourne correctement et ne retourne aucun changement n'est pas
   marquée défaillante.
3. **Période creuse déclarée** — une source annuelle silencieuse onze mois ne déclenche aucune alerte.
4. **Dégradation lente** — une source dont le volume décroît progressivement sur plusieurs exécutions
   déclenche une alerte de volume bas avant d'être complètement muette.
5. **Volume anormalement haut sous le seuil de quarantaine** — alerte émise, publication normale.
6. **Stub** — une source non implémentée n'est jamais classée défaillante.
7. **En attente d'une action externe** — une source dont la clé API ou l'autorisation manque n'est
   jamais classée défaillante, et l'action attendue est nommée dans son état. Vérifier nommément
   contre TheirStack et le RDPRM.
8. **Jamais validée en réel** — l'état est distinct de « saine », de « défaillante » et de « en
   attente d'une action externe ».
9. **Question 1, cas muet** — aucune rétraction, aucun dossier touché.
10. **Question 1, cas corrompu** — les faits issus du run invalidé sont marqués, le score est recalculé
   sans eux, **rien n'est supprimé**, et un prospect déjà livré reste visible avec sa marque.
11. **Question 1, non livré** — un prospect en attente de livraison qui tombe sous le seuil après
    recalcul ne part pas.
12. **Question 2** — aucun nouveau bonus de corroboration n'est calculé à partir d'une source dégradée,
    et la corroboration antérieure est inchangée.
13. **Question 2, cumul** — deux sources défaillantes dans la même exécution produisent une alerte
    d'exploitation distincte, en plus des deux incidents.
14. **Étanchéité** — aucun état de santé ni nom de source ne franchit la frontière vers l'interface
    utilisateur.

---

## Vérification macro — obligatoire

Faire tourner le mécanisme contre **toutes** les sources actives et rapporter pour chacune : cadence
déclarée, saisonnalité, norme de volume calculée sur l'historique disponible, état de santé courant, et
la justification de cet état.

Rappel de ce que la dernière vérification macro a trouvé : deux bogues réels invisibles en test
synthétique, l'un se manifestant au vrai volume, l'autre sur la vraie qualité de donnée d'entrée. Une
suite verte ne dit rien sur ces deux dimensions; les vérifier séparément.

**Attente à poser d'avance :** l'historique disponible est court, donc les normes de volume seront peu
fiables à ce stade. C'est attendu, et ce n'est pas une raison de reporter. Comme pour les seuils de
quarantaine, ce qui compte est que la donnée commence à s'accumuler — sans quoi la norme restera
incalculable dans six mois.

---

## Ce qui doit être livré

1. Le rapport de la phase 0, **avant le code**.
2. Le code : historique d'exécution, norme de volume, taxonomie d'état, alertes, tableau de bord
   interne.
3. Les quatorze tests ci-dessus, verts, dans la suite existante.
4. Le rapport de vérification macro par source.
5. La mise à jour de la documentation d'architecture, même format que les scénarios déjà documentés.
6. Les seuils d'alerte de dérive retenus, avec justification — **décision à valider avec Alexandre**,
   comme les seuils de quarantaine, et non une constante enfouie.

**Ne rien commencer d'autre.** Un problème appartenant à un autre chantier se consigne au
`DiagnosticJournal` et se rapporte, sans être attaqué.
