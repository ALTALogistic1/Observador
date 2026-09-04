# FALKYE — Audit transversal et mandat de consolidation

Destiné à Claude Code. À lire avec `charte-falkye.md`, `repereur-entreprises-croissance-specs.md`,
`strategie-et-personas.md`, la grille des fonctionnalités, le tableau des sources par plan et la liste
des tâches restantes.

**Ce document remplace le mandat de consolidation précédent** (sept chantiers) : il en reprend
l'intégralité et y ajoute ce qu'un audit croisé de l'ensemble du corpus a révélé. Les failles A, B, C
et H ci-dessous n'apparaissaient pas dans la version précédente et sont plus graves que celles qui y
figuraient.

**Nature de l'exercice.** Ce n'est pas une liste de fonctionnalités manquantes. Ce sont des endroits
où **le produit construit contredit ses propres documents de référence**, ou bien où une décision a
été prise correctement puis n'a jamais reçu de mécanisme. La plupart de ces failles sont invisibles
en test unitaire parce que chaque pièce fonctionne : c'est leur combinaison qui casse.

---

# Partie 0 — Test de refonte : lesquelles de ces failles coûtent cher si on attend

**C'est la question à trancher en premier**, avant de décider quoi envoyer en développement. Les onze
failles ne se valent pas du tout sur ce plan. La plupart sont **additives** — on peut les réparer dans
six mois exactement au même prix qu'aujourd'hui, parce qu'il s'agit d'ajouter un attribut, une règle
de configuration ou un tableau de bord par-dessus l'existant. Trois ne le sont pas.

Le critère : **est-ce que le coût de la réparation augmente avec le temps qui passe?**

## Les trois failles à coût croissant — à traiter maintenant

**Faille C — l'identité d'entreprise.** Coût proportionnel au **volume de dossiers cumulatifs déjà
accumulés** sur une clé NEQ. Chaque semaine d'exploitation ajoute des dossiers à migrer. C'est la seule
faille du document qui menace vraiment une refonte au sens strict : au deuxième territoire ancré, il
faudra soit dupliquer la logique de corroboration et de déduplication, soit migrer l'historique.

**Faille E — la conservation d'état des sources instantanées.** Coût **irrécupérable**, pas seulement
croissant. Une source de type instantané qui tourne sans conserver son état complet ne perd pas du
temps de développement : elle perd des événements **définitivement**. Les ouvertures d'établissement
survenues entre deux exécutions non conservées n'existeront jamais nulle part. Le RACJ est la source de
priorité 1 et n'a aucune date de délivrance — chaque semaine où il tourne sans conservation d'état est
une semaine de signaux perdue, et aucun développement ultérieur ne la récupérera.

**Faille D — la confiance d'appariement.** Coût croissant à double titre. D'abord parce que les fusions
déjà effectuées perdent leur trace probabiliste au fur et à mesure. Ensuite parce que la table
d'apprentissage raison sociale ↔ nom d'enseigne ↔ adresse, alimentée par le RACJ et l'OQLF,
**s'enrichit avec le temps** : la construire tôt donne une base d'appariement qui vaut de plus en plus,
la construire tard, c'est repartir d'une table vide alors que les mauvais appariements, eux, se sont
accumulés.

## Les huit autres — additives, réparables à coût constant

Les failles A, B, F, G, H, I, J et K se réparent à l'identique dans six mois. Ce sont des attributs à
ajouter au registre, des règles de configuration, des états supplémentaires, ou des décisions à
trancher. Aucune ne demande de toucher au schéma central.

Deux nuances toutefois, qui portent sur l'urgence **commerciale** plutôt que technique :

- **Faille A** (Écho vide pour cinq sphères) et **faille H** (fonctionnalités jamais validées en réel)
  ne coûtent rien de plus à réparer plus tard, mais elles coûtent **des clients** si elles franchissent
  la mise en marché. Un abonné qui ne reçoit rien pendant un mois ne revient pas.
- **Faille K** (page de crédits) ne coûte rien à construire, mais elle est **bloquante à l'activation**
  des quatre nouvelles sources gratuites : les brancher sans elle met le produit en défaut de licence
  dès le premier jour.
- **Faille B** est additive dans son mécanisme, mais elle dépend directement de la faille C : le niveau
  de vérification par territoire n'a nulle part où vivre tant que l'identité interne n'existe pas. Les
  deux se livrent ensemble.

## Ce que ça donne concrètement

Si le temps de développement est contraint, l'ordre de sacrifice est clair : **ne jamais reporter les
chantiers 1, 3 et 4** (conservation d'état et quarantaine, identité multi-territoire, confiance
d'appariement). Tout le reste peut attendre sans que le coût change — à condition de ne pas lancer
commercialement avant d'avoir réglé A, H et K.

---

# Partie 1 — Failles constatées

Classées par gravité, où la gravité se mesure à ce que ça coûterait si personne ne le voyait avant
les premiers clients payants.

---

## Faille A — Écho est structurellement vide pour cinq sphères de besoin

**Constat.** Les cinq sources gratuites vérifiées le 3 septembre 2026 ont toutes été placées dans
Radar ou Radar+ : RACJ, établissements alimentaires Montréal et CIPO dans Radar; registre des
lobbyistes et OQLF dans Radar+. Aucune n'est dans Écho.

**Preuve du problème.** Chacune est la **seule source existante** pour sa sphère cible. Le tableau
des sources et le document de personas le disent eux-mêmes : le RACJ est la source de la restauration,
CIPO est « le signal le plus direct qui existe » pour le franchisage et le seul pour l'ingénierie/design
industriel, le registre des lobbyistes est le seul pour les relations publiques, l'OQLF est « le seul
signal direct trouvé » pour la traduction. Conséquence mécanique : **un abonné Écho qui déclare l'une
de ces cinq sphères ne recevra jamais rien.** Pas peu de résultats — aucun.

**Pourquoi c'est arrivé.** Deux règles de placement coexistent dans le corpus et se contredisent.

La grille des fonctionnalités dit : « une fonctionnalité qui améliore la qualité d'un résultat déjà
présent dans un plan inférieur va au minimum dans Radar. L'entrée en matière (Écho) reste
volontairement sans enrichissement. »

La charte, section 13, dit le contraire pour ce cas précis : « le critère qui détermine si une source
appartient à Écho n'est **ni** "est-ce gratuit" **ni** "est-ce que ça enrichit un résultat déjà
présent" — ces deux questions passent à côté de l'essentiel. La vraie question : est-ce qu'Écho, avec
ses sources actuelles, produit des opportunités crédibles pour cette sphère, la majorité du temps? »
et conclut qu'une source nécessaire à la qualité de base « peut être nécessaire dans Écho pour que le
produit fonctionne réellement à son palier d'entrée, **peu importe qui la paie** ».

La règle de la grille a été appliquée mécaniquement, la règle de la charte a été perdue. Or c'est
exactement le cas que la charte anticipait : « un Écho qui ne trouve jamais rien de bon n'est pas un
palier d'entrée légitime, c'est un produit qui ne fonctionne pas. »

**Solution.** Introduire une distinction explicite et **calculable**, pas laissée au jugement :

- **Source d'enrichissement** — améliore un résultat qui existerait de toute façon dans le plan
  inférieur. Va au minimum dans Radar. La règle actuelle de la grille s'applique.
- **Source de couverture** — sans elle, une sphère produit zéro ou quasi zéro résultat dans le plan.
  Doit être dans Écho, quel que soit son coût.

Le test est mesurable une fois le chantier 9 (densité) livré : une source est de couverture pour une
sphère si son retrait fait tomber le volume de cette sphère sous un seuil défini. En attendant, le
classement se fait à la main, mais **le champ doit exister dès maintenant dans le registre de
sources** pour que la question soit posée à chaque activation.

Reclassement attendu à valider : RACJ et Montréal en Écho (restauration, agroalimentaire), CIPO en
Écho (franchisage, ingénierie), lobbyistes en Écho (relations publiques), OQLF en Écho si autorisé
(traduction). Toutes sont gratuites — le coût n'est pas l'enjeu, la cohérence de la promesse l'est.

---

## Faille B — La vérification de base obligatoire est impossible hors Québec

**Constat.** Les specs, section 6, imposent trois vérifications avant toute présentation d'un
prospect, en insistant : « ce n'est pas optionnel ». La première est le statut légal au REQ via le
NEQ. La troisième exige que le nom soit résolu « avec confiance à un NEQ unique », sans quoi le
prospect est « marqué comme non vérifié plutôt que présenté ».

**Le problème.** Les licences de Vancouver, les licences de Toronto, les contrats de la
Nouvelle-Écosse, Corporations Canada hors Québec, CIPO et le registre des lobbyistes **ne fournissent
aucun NEQ**, et les entreprises qu'ils détectent n'en ont souvent aucun. La vérification obligatoire
est donc structurellement inapplicable à toute une moitié du produit.

Il n'y a que deux comportements possibles, et les deux sont mauvais : soit tous les prospects hors
Québec sont exclus, et le produit ne fonctionne pas hors Québec — ce qui contredit l'objectif
pancanadien affirmé; soit la vérification est silencieusement sautée, et la promesse « aucun prospect
n'est présenté sans vérification » n'est pas tenue, ce que la charte interdit nommément (section 6,
ne jamais vendre une promesse qu'on ne peut pas tenir).

**Solution.** Rendre la vérification **relative au territoire** plutôt qu'absolue. Pour chaque
territoire couvert, définir dans le registre quelle vérification tient lieu de contrôle d'existence
légale, et **quel est le niveau de vérification maximal atteignable**. Trois niveaux suffisent :
vérifié contre un registre d'État, vérifié partiellement, non vérifiable sur ce territoire.

Ensuite, un choix de produit à trancher explicitement plutôt qu'implicitement : un prospect « non
vérifiable » est-il exclu, ou présenté avec un niveau de confiance plafonné? La deuxième option est
probablement la bonne — elle permet au produit d'exister hors Québec — mais elle doit être une
décision assumée, écrite dans les specs, et refléter le plafond dans le score plutôt que dans un
avertissement affiché.

---

## Faille C — Le pivot québécois est correct; ce qui est structurel, c'est qu'il est aussi le pivot de l'architecture

**Nuance à poser d'entrée, parce qu'elle change la nature du problème.** Que le NEQ soit la colonne
vertébrale **du Québec** n'est pas une faille — c'est exactement ce que la charte prévoit. Section 10 :
« cette classification est propre à chaque territoire, jamais universelle. Le Québec a aujourd'hui une
seule source piste (le REQ, via le NEQ) ». Le REQ mérite ce rôle au Québec, il est obligatoire pour
toute entreprise y opérant, et rien ne justifierait de le diluer. Ce chapitre ne demande pas de
réduire la place du NEQ au Québec.

**Ce qui est réellement en cause.** Le NEQ ne joue pas seulement le rôle de pivot **de son territoire**
— il joue le rôle de clé **de l'architecture**. Dans les specs, section 9, c'est simultanément la clé de
déduplication, la clé de corroboration multi-signaux, la clé du dossier cumulatif et le véhicule de la
vérification des entreprises radiées. Ces quatre fonctions sont des fonctions du **moteur**, pas du
territoire québécois. Elles s'appliquent identiquement à une entreprise ontarienne ou néo-écossaise,
qui n'a pas de NEQ et n'en aura jamais.

Autrement dit : la charte dit qu'un territoire a sa source Piste, et le code dit que le produit a une
clé primaire. Les deux affirmations sont compatibles seulement si la clé primaire est **interne**, et
que le NEQ est ce qui l'ancre au Québec — pas ce qu'elle est.

**Pourquoi c'est le point de refonte le plus coûteux du document.** Tant qu'il n'y a qu'un territoire
ancré, la confusion ne se voit pas et ne coûte rien. Elle coûte au moment où un deuxième identifiant
Piste arrive — l'Ontario Business Registry est déjà identifié comme « la piste la plus prometteuse » au
tableau des provinces, et le registre de la C.-B. figure au tableau des sources. À ce moment-là, avec
une base de dossiers cumulatifs déjà accumulés sur une clé NEQ, il n'y a que deux issues : un deuxième
pivot en parallèle — qui double la logique de corroboration et de déduplication à chaque endroit où
elle existe — ou une migration de toutes les données historiques vers un nouveau schéma d'identité.

Et le coût augmente chaque semaine, parce qu'il est proportionnel au volume de dossiers déjà accumulés.

**Solution — un déplacement, pas un affaiblissement.** Une **identité d'entreprise interne**, propre à
FALKYE, comme clé du dossier cumulatif, de la corroboration et de la déduplication. Une table
d'identifiants externes rattachés à cette identité : NEQ, numéro de société fédéral, identifiants
provinciaux futurs — chacun avec son territoire, sa source et sa date de résolution.

Le NEQ ne perd rien de son rôle : il reste l'identifiant Piste du Québec, celui qui donne le meilleur
niveau de vérification disponible sur ce territoire, et une identité qui en porte un est mieux ancrée
qu'une identité qui n'en porte pas. La différence est qu'une identité **sans** NEQ devient une identité
valide et de plein droit plutôt qu'un cas dégradé, ce qui est la condition pour que le produit
fonctionne hors Québec sans réécriture.

C'est aussi ce qui rend la faille B réparable : le niveau de vérification devient un attribut du couple
identité × territoire, au lieu d'être une propriété binaire de la présence d'un NEQ.

---

## Faille D — L'appariement par nom a déjà produit des dégâts réels, et rien ne suit son incertitude jusqu'au bout

**Constat, avec preuve dans les documents.** Ce n'est pas un risque théorique. Le corpus documente
déjà : 76 paires de doublons non reconnues dans la vraie base; une fusion erronée réelle entre deux
compagnies à numéro légalement distinctes, qu'il a fallu restaurer depuis une sauvegarde; et 20
candidats de fusion en attente d'examen manuel, avec des faux positifs identifiés d'avance (« Groupe
TVA inc. » contre « Groupe A. inc. »).

La correction livrée est bonne — appariement flou restreint aux entreprises sans NEQ, seuils à 90 et
95, interdiction structurelle de comparer deux compagnies à numéro. Mais elle s'arrête à la fusion.

**Ce qui manque.** L'incertitude d'appariement est résolue **au moment de la fusion**, puis oubliée.
Une fois deux enregistrements fusionnés à un score de 95, le dossier cumulatif ne porte plus aucune
trace du fait que ce lien est probabiliste. Les signaux suivants s'y accumulent, la corroboration
multi-signaux les additionne, le score de confiance monte — et un signal fort finit rattaché à une
entreprise avec une assurance que rien ne justifie.

**Un signal fort rattaché à la mauvaise entreprise est pire qu'un signal faible bien rattaché** : il
produit une notification confiante et fausse, et c'est le seul type d'erreur que l'utilisateur ne peut
pas détecter lui-même.

**Solution.** Un **troisième axe indépendant** : la confiance dans le lien d'identité. Jamais fusionné
en moyenne avec la confiance du signal ni avec la pertinence — même principe de séparation que les
deux axes existants.

- L'identité porte un score, hérité du plus faible maillon de son historique d'appariement.
- Ce score **plafonne** le score de confiance du signal plutôt que de s'y additionner. Une identité à
  90 ne peut pas produire une notification à confiance élevée, quelle que soit la force du signal.
- **L'adresse devient l'axe d'appariement principal, pas le nom.** Code postal plus numéro civique est
  nettement plus discriminant qu'une raison sociale, et presque toutes les sources en fournissent une.
  Le nom devient corroborateur.
- **Le RACJ et l'OQLF servent de ponts d'apprentissage.** Ce sont les deux seules sources à livrer
  simultanément le NEQ, un nom d'enseigne et une adresse. Chaque ligne qu'elles produisent est une
  paire (raison sociale ↔ nom d'enseigne ↔ adresse) réutilisable pour apparier toutes les autres
  sources. C'est probablement leur plus grande valeur et elle n'apparaît nulle part dans le tableau
  des sources.

Ce dernier point règle un problème structurel : le REQ porte la **raison sociale** (« 9138-3471
Québec inc. ») pendant que les permis et licences portent le **nom d'enseigne** (« Maison La joie d'y
vivre »). Ce sont deux univers de chaînes qui ne se rejoignent jamais par similarité textuelle, quel
que soit l'algorithme.

---

## Faille E — Le pipeline est un moteur de diff d'instantanés, sans protection contre un diff aberrant

**Constat.** Le RACJ, les établissements de Montréal, la Nouvelle-Écosse, l'ACIA et les registres de
licences en général **ne fournissent aucune date d'événement**. Les specs le reconnaissent pour le
RACJ : « aucune date de délivrance dans le registre, diff hebdomadaire nécessaire ». La détection
vient donc de la comparaison de deux états successifs — et le RACJ est la source de priorité 1.

**Le risque.** Le jour où un diffuseur renomme une colonne, change son encodage ou réassigne ses
identifiants internes, le diff produit des milliers de fausses ouvertures, et une vague de
notifications absurdes part chez tous les clients le même matin. C'est le seul scénario du présent
document qui coûte la crédibilité **d'un coup** plutôt que graduellement, et il coûte une journée à
prévenir.

**Solution.** Une règle de quarantaine, détaillée au chantier 1.

---

## Faille F — Trois sources sont à zéro signal pour trois raisons différentes, et rien ne les distingue

**Constat.** Corporations Canada est « actif, 0 signal à ce jour (attendu) ». Le RDPRM mécanisme 1 est
« stub — aucun signal réel produit à ce jour ». TheirStack est « actif, validation réelle en attente ».
Trois états radicalement différents — normal, non implémenté, non validé — qui produisent tous le même
symptôme observable : rien.

Aujourd'hui la distinction tient dans la tête d'Alexandre. Avec vingt sources et six mois d'écart, un
connecteur cassé silencieusement sera indiscernable d'un territoire calme.

**Solution.** Un état de santé par source, distinct du signal, détaillé au chantier 2.

---

## Faille G — Le canal « hors profil déclaré » n'existe pas là où le désaccord se produit

**Constat.** La section 8bis des specs établit une règle générale : quand le « qui » de l'entreprise
est connu et ne correspond pas au « qui » déclaré par l'utilisateur, le signal « ne devient jamais un
malus silencieux, redirige plutôt vers le canal séparé ». Cette règle s'applique à **tous** les
utilisateurs, puisque tous ont un « qui » déclaré.

Mais le canal « hors profil déclaré » est réservé à Radar+, dans les specs comme dans la grille.

**Le problème.** Pour un utilisateur Écho ou Radar, la redirection n'a pas de destination. Le signal
n'est pas montré, il n'est pas non plus dirigé ailleurs — il disparaît. C'est exactement le « malus
silencieux » que la règle voulait empêcher, obtenu par un autre chemin.

**Solution.** Trancher explicitement, l'une ou l'autre : soit le canal existe pour tous les plans et
la différenciation Radar+ porte sur autre chose (le volume, le filtrage fin, la présentation), soit le
comportement de repli pour Écho et Radar est écrit noir sur blanc dans les specs. Ne pas laisser la
règle générale et son exception de plan se contredire en silence.

---

## Faille H — Plusieurs fonctionnalités sont vendables mais n'ont jamais tourné contre du réel

**Constat.** La grille des fonctionnalités marque d'un ✓ des capacités dont la liste des tâches
restantes révèle qu'elles n'ont jamais été validées hors mock : l'intégration CRM (« construite,
testée, documentée » — contre des mocks, les jetons HubSpot et Pipedrive restent à fournir), le
paiement Stripe (non validé, ce qui a laissé `billing definir-plan` contourner la facturation jusqu'à
sa fermeture récente), l'assistance IA de niveau 2 (vendue dans Radar et Radar+, aucune clé API
fournie), TheirStack (source Radar annoncée, connecteur « à développer » tant que non validé), la
carte géographique (dépend d'un géocodage jamais validé en conditions réelles).

**Le problème.** La grille est le document qui dit ce que le client reçoit. Il ne distingue pas
« construit » de « éprouvé contre le vrai service ». Le risque n'est pas technique, il est commercial :
vendre un plan dont une fonctionnalité annoncée casse au premier usage réel.

**Solution.** Un troisième état dans la grille, à côté du ✓ et du — : **construit mais non validé en
réel**. Et une règle simple : rien ne passe au ✓ plein avant d'avoir tourné contre le vrai service, pas
contre un mock. Ça ne bloque pas le développement, ça bloque la promesse.

---

## Faille I — Les décisions ouvertes disparaissent du suivi

**Constat.** La liste des tâches restantes le dit elle-même à propos de Crunchbase : « décision
budgétaire jamais tranchée, pas juste différée […] disparu du suivi jusqu'à aujourd'hui ». C'est un
angle mort documenté depuis longtemps sur un vrai trou de couverture — toute entreprise qui finance sa
croissance par du capital privé, sans RDPRM ni subvention ni contrat public, reste invisible.

**Le problème n'est pas Crunchbase**, c'est qu'une décision non tranchée n'a aucun mécanisme qui la
fasse revenir. Le prix de Radar+ à 349 $ « à réviser » est dans le même état, et il est écrit dans
l'en-tête d'une colonne du document de référence interne.

**Solution.** Toute entrée de registre à l'état « décision jamais tranchée » porte une date d'échéance
de décision et réapparaît automatiquement à cette date. Trancher peut vouloir dire « non, et voici
pourquoi » — ce qui est un résultat, contrairement au silence.

---

## Faille J — Deux sphères ont été déclarées résolues par une méthode qui n'existe pas dans le produit

**Constat.** La recherche du 3 septembre conclut correctement que « service à la clientèle » se traite
par une règle de mots-clés sur Guichet-Emplois plutôt que par une nouvelle source, et que
« assurance/gestion des risques » est « alimentée uniquement par dérivation d'autres signaux ». Ces
deux conclusions sont justes.

**Le problème.** Le registre des sphères ne connaît qu'un seul type de sphère. Rien ne distingue une
sphère à source directe d'une sphère dérivée, et rien ne porte la règle de dérivation. Le résultat :
deux sphères qu'un utilisateur peut sélectionner, pour lesquelles la documentation dit qu'une solution
existe, mais dont le moteur ne sait rien.

**Solution.** Un attribut de type sur la sphère — directe, dérivée, ou sans couverture — et, pour les
dérivées, la règle de dérivation dans le registre plutôt que dans un document. Une sphère « sans
couverture » doit être visible comme telle au moment de la configuration du profil, jamais offerte
comme si elle fonctionnait.

---

## Faille K — L'obligation d'attribution des licences ouvertes n'a pas encore de destination

**Constat.** La charte a été mise à jour pour prévoir une page de crédits hors du produit, seconde
exception délibérée à la règle de non-divulgation des sources. Le RACJ, Montréal, CIPO et le registre
des lobbyistes portent tous une obligation d'attribution — Montréal précise même qu'elle s'applique
lorsque les données sont intégrées à une base qu'on possède.

Rien dans les specs ni dans le code ne construit cette page. Activer ces quatre sources sans elle
place le produit en défaut de licence dès le premier jour.

**Solution.** Chantier 6.

---

# Partie 2 — Chantiers

## Règles applicables à tous les chantiers

1. **Registre extensible, jamais d'énumération codée en dur** (charte, section 4). Cadences, états de
   santé, niveaux de vérification, types de sphère : tout s'ajoute sans migration structurelle.
2. **Le test de la section 11 est obligatoire.** Chaque chantier touche une dimension déjà pluralisée
   ailleurs. Avant de le considérer terminé, répondre par écrit, dans le code ou la doc, à la question
   posée sous chaque chantier : **« que se passe-t-il quand deux éléments de la même dimension sont en
   désaccord? »** Aucune ne doit rester sans réponse implémentée et testée.
3. **Vérification macro.** Tout mécanisme se teste contre **toutes** les sources actives, pas seulement
   celle qui a motivé sa conception. C'est l'erreur commise sur `champs_pertinents.yaml`, à ne pas
   refaire.
4. **Aucun nom de source visible par l'utilisateur** (charte, section 6), sauf les deux exceptions
   délibérées : le portail de sources payantes et la page de crédits du chantier 6. Les tableaux de
   bord d'exploitation internes ne sont pas l'interface utilisateur; les séparer nettement dans le code.
5. **Étendre la suite de tests existante**, ne pas en créer une parallèle.

---

## Chantier 1 — Quarantaine de diff *(faille E)*

**À construire.**
- Un moteur de diff générique partagé par toutes les sources de type instantané, conservant **l'état
  complet** de la dernière exécution réussie et pas seulement les écarts : une exécution manquée est
  sinon une période d'événements perdue définitivement.
- Une **règle de quarantaine** paramétrable par source : si les ajouts, retraits ou modifications
  dépassent un seuil (en pourcentage et en valeur absolue), **rien n'est publié**. L'exécution passe
  en attente de révision, l'état précédent reste intact, le diff suspect est archivé.
- Une **détection de changement de schéma** en amont : colonne disparue, apparue, renommée, type
  modifié. Un schéma modifié déclenche la quarantaine quel que soit le volume.
- Une levée de quarantaine explicite et journalisée : qui, quand, pourquoi.

**Question de la section 11.** Que se passe-t-il quand deux sources entrent en quarantaine dans la
même exécution, et quand une source en quarantaine alimente un signal déjà partiellement corroboré par
une source saine? Le dossier cumulatif reflète-t-il la corroboration partielle, ou attend-il?

**Acceptation.** Un test simulant un fichier dont 60 % des identifiants ont changé ne produit **aucune**
notification. Un test simulant le retrait d'une colonne met la source en quarantaine sans interrompre
le pipeline des autres sources.

---

## Chantier 2 — Santé de source *(faille F)*

**À construire.**
- Un état de santé par source, distinct du signal : dernière exécution tentée, dernière exécution
  **réussie**, volume observé, volume attendu, dérive.
- Une **norme de volume apprise** sur l'historique réel, avec alerte quand l'observé s'écarte **dans un
  sens comme dans l'autre**.
- Une distinction explicite entre quatre états qui produisent tous « rien » : source saine et
  territoire calme; source saine en période creuse connue (saisonnalité — permis saisonniers du RACJ,
  palmarès annuels); source non implémentée (stub); source défaillante.
- Un tableau de bord d'exploitation **interne**, séparé du tableau de bord client.

**Question de la section 11.** Quand une source est déclarée défaillante après avoir contribué à des
signaux déjà publiés, que deviennent ces signaux? Et si deux sources qui se corroborent mutuellement
tombent ensemble, la corroboration compte-t-elle encore?

---

## Chantier 3 — Identité d'entreprise multi-territoire *(failles B et C)*

**Cadrage, à ne pas perdre en implémentant.** Ce chantier ne réduit pas le rôle du NEQ au Québec. Le
REQ reste la source Piste du Québec et le NEQ reste l'identifiant qui donne le meilleur niveau de
vérification sur ce territoire. Ce qui change, c'est que la **clé du moteur** cesse d'être un
identifiant de territoire. Une identité qui porte un NEQ doit rester strictement aussi bien servie
qu'aujourd'hui — c'est un critère de non-régression, pas un effet secondaire acceptable.

**À construire.**
- Une **identité d'entreprise interne**, distincte de tout identifiant externe, comme clé unique du
  dossier cumulatif, de la corroboration et de la déduplication.
- Une table d'**identifiants externes** rattachés : NEQ, numéro de société fédéral, futurs
  identifiants provinciaux — chacun avec territoire, source et date de résolution. Zéro, un ou
  plusieurs par identité. Une identité sans identifiant externe est **valide de plein droit**, pas un
  cas dégradé.
- Un **niveau de vérification par couple identité × territoire** : vérifié contre un registre d'État,
  vérifié partiellement, non vérifiable ici. Le registre porte, par territoire, quelle vérification
  tient lieu de contrôle d'existence légale.
- Le traitement des prospects non vérifiables : trancher entre exclusion et présentation à confiance
  plafonnée, écrire la décision dans les specs, et l'implémenter dans le score plutôt que dans un
  avertissement affiché.

**Question de la section 11.** Que se passe-t-il quand deux identifiants externes de la même identité
se contredisent — le REQ dit `radiée`, le registre d'une autre province dit active? L'exclusion
s'applique-t-elle à toute l'identité ou seulement au territoire concerné?

**Acceptation, deux tests.** Un test qui ajoute un identifiant externe d'un territoire fictif à une
identité existante ne touche à aucune ligne du moteur de croisement — c'est la démonstration que
l'extensibilité territoriale est réelle et pas seulement affirmée. Et un test de non-régression qui
confirme qu'une entreprise québécoise avec NEQ produit exactement les mêmes résultats qu'avant la
migration.

---

## Chantier 4 — Confiance d'appariement, troisième axe *(faille D)*

**À construire.**
- Un score de confiance d'appariement porté par l'identité, hérité du maillon le plus faible de son
  historique de fusion, **jamais fusionné en moyenne** avec la confiance du signal ni avec la
  pertinence.
- Un **plafonnement** : l'identité plafonne la confiance du signal au lieu de s'y additionner. Une
  identité faible ne peut pas produire une notification à confiance élevée.
- **L'adresse comme axe d'appariement principal** (code postal plus numéro civique), le nom en
  corroborateur.
- Une **table d'apprentissage raison sociale ↔ nom d'enseigne ↔ adresse**, alimentée par le RACJ et
  l'OQLF, réutilisée pour apparier les sources sans NEQ.
- Une **règle de non-promotion** : sous un seuil, le signal reste une réflexion, n'entre pas au dossier
  cumulatif comme fait établi et ne déclenche aucune notification, quelle que soit sa force.

**Question de la section 11.** Que se passe-t-il quand **deux appariements concurrents** atteignent un
score comparable pour un même signal — deux entreprises à la même adresse, cas très courant en centre
commercial et en édifice à bureaux? Le comportement par défaut ne doit jamais être « prendre le
meilleur score ».

**Note.** Les 20 candidats de fusion en attente sont le jeu de test naturel de ce chantier. Les
examiner après l'avoir construit plutôt qu'avant.

---

## Chantier 5 — Placement des sources : couverture contre enrichissement *(faille A)*

**À construire.**
- Un attribut sur chaque source du registre : **source de couverture** (sans elle une sphère produit
  zéro) ou **source d'enrichissement** (améliore un résultat qui existerait quand même).
- La règle de placement par plan découle de cet attribut, elle n'est plus appliquée à la main : une
  source de couverture appartient au plan où sa sphère est offerte, une source d'enrichissement suit
  la règle actuelle de la grille.
- Le reclassement des cinq sources gratuites vérifiées, à valider avec Alexandre avant application.
- Une **vérification automatique de cohérence** : pour chaque combinaison plan × sphère offerte,
  au moins une source de couverture est présente. Une combinaison qui échoue est un défaut, pas une
  particularité.

**Question de la section 11.** Que se passe-t-il quand une source est de couverture pour une sphère et
d'enrichissement pour une autre — le cas du RACJ, couverture pour la restauration et enrichissement
pour l'assurance? L'attribut est donc **par couple source × sphère**, jamais par source seule.

---

## Chantier 6 — Registre légal et page de crédits *(faille K)*

**À construire.** Étendre le registre de sources avec la case obligatoire d'activation (charte,
section 12ter) :
- Canal exact : jeu sous licence ouverte, page web, API, export par accès à l'information.
- Variante de licence, lue sur la fiche du jeu précis, jamais déduite du portail. Les variantes **NC**
  sont bloquantes.
- Présence d'une clause visant l'indexation, l'automatisation ou la redistribution.
- Statut du `robots.txt` du domaine hôte.
- Obligation d'attribution, et lien vers son inscription à la page de crédits.
- **Date de dernière vérification légale et échéance de revalidation**, avec alerte à l'échéance.
- Un état `bloquée` distinct de `inactive` : une source peut être techniquement prête et légalement
  interdite. L'AMF en est l'exemple courant.

Livrer la **page de crédits** : hors du produit, alimentée automatiquement par les sources dont le
registre indique une obligation d'attribution, et jamais par les autres.

**Question de la section 11.** Que se passe-t-il quand une source passe à `bloquée` alors que ses
données sont déjà intégrées à des dossiers cumulatifs? Purger, geler, ou conserver? La charte promet
qu'une source problématique se désactive « sans restructuration » — vérifier que c'est vrai en
pratique.

---

## Chantier 7 — Canal hors profil et sphères dérivées *(failles G et J)*

**À construire.**
- Trancher et implémenter le comportement du canal « hors profil déclaré » pour Écho et Radar : canal
  disponible partout avec une différenciation Radar+ portant sur autre chose, ou repli explicite écrit
  dans les specs. Le silence actuel n'est pas une option.
- Un **type de sphère** dans le registre : directe, dérivée, sans couverture.
- Pour les sphères dérivées, la **règle de dérivation dans le registre** plutôt que dans un document —
  « service à la clientèle » comme règle de mots-clés sur Guichet-Emplois, « assurance » comme
  dérivation de nouvel établissement, permis de construction et RDPRM.
- Une sphère sans couverture doit être **visible comme telle au moment de la configuration du profil**,
  jamais offerte comme si elle fonctionnait.

**Question de la section 11.** Que se passe-t-il quand un profil combine une sphère directe et une
sphère sans couverture? Et quand une sphère dérivée et une sphère directe produisent le même signal
pour le même prospect — deux notifications, ou une consolidée?

---

## Chantier 8 — Cadence de notification configurable par palier

**À construire.**
- Un **registre de cadences** extensible, pas une énumération figée : temps réel, quotidien,
  hebdomadaire, aux dix jours, mensuel, désactivé.
- Une **matrice palier × cadences autorisées**, en configuration. Point de départ à valider : Écho
  accède aux cadences espacées (quotidien, hebdomadaire, dix jours); Radar et Radar+ accèdent à
  l'ensemble, y compris le temps réel et la désactivation, puisqu'ils disposent du tableau de bord
  comme canal de rechange.
- **Cadence et sensibilité restent deux axes indépendants**, jamais fusionnés en un réglage
  « fréquence ». La sensibilité détermine *ce qui mérite d'être signalé*, la cadence détermine *quand
  le lot part*. Les confondre reproduirait l'erreur que la charte interdit déjà sur les deux scores —
  d'autant que les specs prévoient déjà **deux** curseurs de sensibilité indépendants, ce qui ferait
  trois axes à ne pas mélanger.
- **Réutiliser le résumé périodique existant** (specs, section 5) comme mécanisme de regroupement des
  lots. Ne pas construire un second système d'agrégation à côté.
- **Défaut : notification active.** La désactivation est un choix explicite de l'utilisateur, jamais
  l'état par défaut d'un palier — la veille continue par notification est nommée comme l'un des trois
  fossés défendables (charte, section 3) et comme argument de vente direct contre des concurrents qui
  n'en ont pas. Un palier supérieur silencieux par défaut retirerait au client le différenciateur qu'il
  paie le plus cher.
- Cadence **par profil**, pas seulement par compte : les profils multiples de Radar+ existent déjà, un
  cabinet voudra du temps réel sur une sphère et de l'hebdomadaire sur une autre.

**Question de la section 11.** Que se passe-t-il quand un même prospect correspond à **deux profils du
même compte ayant des cadences différentes** — doublon, cadence la plus rapide, ou regroupement? Et
quand un compte est rétrogradé vers un palier n'autorisant pas la cadence configurée, quelle cadence de
repli s'applique et l'utilisateur en est-il informé?

---

## Chantier 9 — Densité de signal par sphère et par territoire

**À construire.**
- Une mesure de densité calculée sur **l'historique réel**, par sphère × territoire × plan : volume,
  répartition par niveau de pertinence, fraîcheur médiane.
- Une **exposition honnête au moment de la configuration du profil** : quand un utilisateur décrit un
  besoin tombant dans une combinaison à faible densité, le lui dire avant qu'il paie, en termes de
  résultats attendus et **sans nommer de source**.
- L'alimentation du test du chantier 5 : c'est cette mesure qui rend le classement
  couverture/enrichissement calculable plutôt que subjectif.
- Un usage interne comme **file de priorité de recherche de sources** : les combinaisons à faible
  densité et forte demande deviennent le prochain mandat, au lieu d'être découvertes par des
  annulations.

**Question de la section 11.** Comment se calcule la densité pour un profil couvrant **plusieurs
sphères**, dont une dense et une vide? La moyenne masquerait exactement le problème qu'on cherche à
exposer.

---

## Chantier 10 — État de validation réelle et décisions à échéance *(failles H et I)*

**À construire.**
- Un troisième état dans la grille des fonctionnalités et le registre de sources : **construit mais non
  validé en réel**, distinct du ✓ et du —.
- La règle associée : rien ne passe au ✓ plein avant d'avoir tourné contre le vrai service plutôt que
  contre un mock. Ça ne bloque pas le développement, ça bloque la promesse commerciale.
- Application immédiate à l'intégration CRM, Stripe, l'assistance IA niveau 2, TheirStack et le
  géocodage.
- Une **échéance de décision** sur toute entrée à l'état « décision jamais tranchée », qui la fait
  réapparaître automatiquement. Trancher inclut « non, et voici pourquoi ». Application immédiate à
  Crunchbase, au prix de Radar+ et au palier gratuit de ProcureData.

---

## Chantier 11 — Capitalisation du diagnostic à quatre étapes

**À construire.**
- Chaque diagnostic effectué enrichit le **registre sphère↔signal de façon permanente** : la
  correspondance trouvée pour un client sert à tous les suivants, pour que le coût marginal décroisse
  au lieu de rester constant.
- Consigner aussi les **diagnostics négatifs** — cherché, rien trouvé, à telle date, voici où — pour ne
  pas refaire deux fois la même recherche infructueuse. Le `DiagnosticJournal` généralisé existe déjà
  (discriminant `source_manquante`) : l'étendre plutôt que de créer un mécanisme parallèle. Les quatre
  sphères sans solution de la recherche du 3 septembre sont les premières entrées.
- Réserve à maintenir dans le produit : la partie irréductible du coût — la vraie recherche pour une
  combinaison inédite — appartient à Radar+ **comme service**, pas comme fonctionnalité incluse. Ne
  jamais laisser l'interface promettre un diagnostic instantané sur une spécialité jamais vue.

**Question de la section 11.** Que se passe-t-il quand deux diagnostics successifs attribuent des
sphères différentes au même service? Le registre reflète-t-il les deux, arbitre-t-il, ou marque-t-il le
désaccord pour révision?

## Chantier 12 — Inventaire champ ↔ sphère à rebours *(chantier parallèle, ne touche pas au schéma)*

**Peut se mener en parallèle des chantiers 1 à 4** : il n'ajoute aucune table centrale et ne présente
donc aucun risque de refonte. C'est le seul chantier du document qui peut avancer pendant que le socle
se répare.

**Constat.** Toute la recherche de sources a été menée **source-d'abord** : on trouve une source, on
demande quelles sphères elle peut servir. Cette question n'a jamais été reposée à rebours sur les
quatorze sources déjà actives, et elle n'a jamais été posée **au niveau du champ** — seulement au
niveau de la source entière. Or les specs, section 6, ont établi le bon principe pour ça : capter
largement une fois, filtrer par lentille ensuite. Ce principe n'a été appliqué que dans un sens, et
plusieurs sphères sont arrivées au registre après la cartographie des sources actives.

**Preuve que le diagnostic « sans source » est probablement faux pour au moins trois des quatre.**

*Assurance / gestion des risques* — déclarée sans source. Au niveau du champ, le besoin est déclenché
par un changement d'exposition assurable, et six champs déjà captés le portent : `Capacite` du RACJ
(occupation, responsabilité civile), valeur des travaux des permis de construction, nouvel
établissement du REQ, `nature_bien` du RDPRM (véhicules et équipement à assurer), volume d'embauche de
Guichet-Emplois et de l'EIMT (masse salariale, classification CNESST), valeur de contrat du SEAO
(cautionnement et exigences de responsabilité). Ce n'est pas « aucune source », c'est « aucune source
**seule** » — c'est-à-dire exactement la thèse de la charte, section 2.

*Analytique d'affaires* — le signal existe déjà dans le titre de poste (Guichet-Emplois, TheirStack) :
une entreprise qui embauche son premier analyste de données a un besoin d'outillage et de conseil.
Problème de mots-clés, pas de source.

*Service à la clientèle* — la règle de mots-clés recommandée était déjà la bonne réponse; elle n'a
simplement jamais été traitée comme un mécanisme du produit.

*Gestion documentaire* — reste honnêtement mince, même à ce niveau d'analyse. Ne pas forcer.

**À construire.**

1. **Inventaire de champs par source active.** La grille `champs_pertinents.yaml` a déjà été approuvée
   avec sa portée complète (0 à 10 clés selon la source) mais n'a jamais été livrée. C'est le
   préalable : sans inventaire de champs, tout ce chantier reste au niveau de la source et ne trouve
   rien de nouveau.
2. **Diagnostic à rebours, au niveau du champ.** Pour chaque sphère orpheline ou faiblement couverte,
   parcourir l'inventaire complet des champs de **toutes** les sources actives et proposer des liens
   champ → sphère. C'est la méthode de diagnostic à quatre étapes de la charte, appliquée dans l'autre
   sens : au lieu de partir du service pour chercher la source, partir de la sphère pour parcourir les
   champs déjà en main.
3. **Assistance IA, en proposition seulement — mécanisme existant retourné.** Le niveau 2 fait
   aujourd'hui description utilisateur → sphères. Le même mécanisme, avec le même schéma de sortie
   contraint et le même catalogue fermé, fait inventaire de champs → sphères candidates. **Aucun
   nouveau mécanisme, aucun nouveau modèle.** Les garde-fous existants s'appliquent tels quels : une
   proposition, jamais une activation silencieuse; enrichissement d'une sphère existante permis;
   création d'une sphère, jamais sans confirmation humaine. Résultat journalisé dans le
   `DiagnosticJournal` généralisé, discriminant existant.
4. **Second usage de l'IA, sur des champs déjà captés : la normalisation de texte libre.** Les sujets
   déclarés du registre des lobbyistes, les titres de poste, et le secteur REQ — dont les specs
   documentent déjà l'échec d'agrégation (211 valeurs distinctes sur 311 notifications réelles).
   Normaliser ces champs en catégories exploitables sert à la fois ce chantier et le problème
   d'agrégation resté ouvert dans les tableaux de bord Radar+.
5. **Règle de réfutation obligatoire — la partie non négociable.** Une IA à qui on demande quel champ
   pourrait servir une sphère produira toujours quelque chose de plausible. C'est précisément ce que la
   charte, section 8, interdit : fabriquer un avantage plausible mais non vérifié. **Aucun lien
   champ → sphère n'est activé sur la seule foi d'une proposition.** Chaque lien doit être testé contre
   l'historique réel via la mesure de densité (chantier 9) : s'il ne discrimine pas — s'il ne produit
   pas de volume, ou s'il en produit tellement qu'il ne distingue rien — il est rejeté et journalisé
   comme réfuté, pas laissé en attente.
6. **Retombée attendue sur le chantier 7.** Les sphères qui survivent à l'étape 5 deviennent des
   sphères dérivées documentées, avec leur règle de dérivation dans le registre. Celles qui n'y
   survivent pas deviennent des sphères sans couverture, affichées comme telles à la configuration du
   profil. Dans les deux cas, on sort de l'état actuel où la documentation dit qu'une solution existe
   et où le moteur n'en sait rien.

**Question de la section 11.** Que se passe-t-il quand un même champ est proposé pour deux sphères dont
l'une est directe et l'autre dérivée — le champ compte-t-il deux fois dans la corroboration
multi-signaux? La réponse par défaut doit être non : un seul champ ne peut pas se corroborer lui-même,
quel que soit le nombre de sphères qu'il alimente.

**Réserve honnête à documenter.** Ce chantier ne créera pas de signal là où il n'y en a pas. Il révèle
des signaux déjà captés mais mal attribués — ce qui est probablement le cas pour trois des quatre
sphères orphelines, et probablement pas pour la quatrième. Ne jamais le présenter comme une méthode qui
garantit de couvrir toute nouvelle sphère.

---

## Chantier 13 — Précision perçue : instrumenter le faux positif *(charte, section 16)*

**Constat.** La charte pose maintenant que le faux positif coûte structurellement plus cher que le faux
négatif pour ce produit et ce prix. Aucun instrument ne mesure ce ratio aujourd'hui.

**Le mécanisme existe déjà à moitié.** Le statut de suivi « Pas pertinent » est décrit dans les specs
comme ayant une double fonction : suivi de pipeline **et** rétroaction au moteur de pertinence. Ce qui
manque, c'est de l'agréger.

**À construire.**
- Un **taux de rejet par profil, par sphère et par source**, calculé sur les statuts « Pas pertinent »
  déjà collectés.
- Un **seuil d'alerte interne** : au-delà d'un certain taux de rejet, la combinaison est signalée comme
  suspecte — sphère mal câblée, source bruitée, ou seuil de sensibilité trop bas.
- Une **distinction entre rejet et non-conversion.** « Pas pertinent » signifie que le prospect
  n'aurait pas dû être montré; « Joint, sans suite » signifie qu'il était bon et que la vente n'a pas
  eu lieu. Le second ne doit jamais compter comme une erreur du moteur.
- Un usage direct dans le chantier 12 : un lien champ → sphère dont le taux de rejet est élevé est
  réfuté par les données, ce qui rend le garde-fou de réfutation opérationnel plutôt que théorique.

**Question de la section 11.** Que se passe-t-il quand un même prospect est rejeté par un utilisateur
et retenu par un autre, sur la même sphère? Le rejet est-il un signal sur le prospect, sur le profil,
ou sur la sphère? La réponse par défaut doit être « sur le profil » — le moteur n'apprend jamais d'un
utilisateur pour les autres sans confirmation.

---

## Chantier 14 — Comportement en l'absence de signal *(charte, section 17)*

**Constat.** Le mode de défaillance principal du produit est le silence, et rien ne le traite. Un
abonné qui ne reçoit rien pendant trois semaines ne peut pas distinguer un territoire calme, un profil
mal configuré et un produit brisé.

**À construire.**
- Un **rythme normal par profil**, appris sur son propre historique — pas une moyenne globale : un
  profil de niche a un rythme lent qui est normal pour lui.
- Une distinction explicite entre **silence attendu** et **silence anormal**, avec des causes
  distinguables : combinaison sphère × territoire structurellement mince (chantier 9), profil trop
  restrictif, source en quarantaine ou défaillante (chantiers 1 et 2), aucune des trois.
- Une **annonce à la configuration** quand la combinaison choisie est mince, en termes de résultats
  attendus et **sans jamais nommer de source**.
- Une **intervention au-delà d'un seuil de silence** : proposer un ajustement de profil, un
  élargissement de territoire, ou dire que la sphère est mince en ce moment. Un message honnête vaut
  mieux que rien, et infiniment mieux qu'un faux prospect.
- **Interdiction implémentée, pas seulement documentée :** aucun mécanisme ne doit pouvoir abaisser un
  seuil de sensibilité automatiquement pour rompre un silence. Si un tel comportement existe quelque
  part, le retirer.

**Question de la section 11.** Que se passe-t-il pour un compte à **profils multiples** dont un seul
est silencieux — l'alerte porte-t-elle sur le profil ou sur le compte? Et un silence causé par une
source en quarantaine doit-il être présenté comme un silence anormal, sachant qu'on ne peut pas nommer
la source en cause?

---

## Chantier 15 — Retenue : séparer le registre interne de l'offre commerciale *(charte, section 18)*

**Constat.** Rien ne distingue aujourd'hui ce que le registre contient de ce que le produit offre. Une
sphère sans couverture est sélectionnable comme les autres.

**À construire.**
- Un attribut **offert / non offert** sur les sphères, territoires et combinaisons, distinct du fait
  d'exister au registre. Le registre garde la trace, l'offre ne présente que ce qui est servi.
- Une **opération de retrait** propre et journalisée : retirer une sphère du catalogue offert sans la
  supprimer du registre, avec motif et date. Les précédents existent — la sphère « Gestion
  d'inventaire », plusieurs personas — mais ont été traités à la main.
- Le traitement des **utilisateurs déjà abonnés** à une combinaison retirée de l'offre : ils ne perdent
  pas leur configuration, ils sont informés. Décision à trancher explicitement, pas à découvrir.

**Question de la section 11.** Que se passe-t-il quand un profil combine une sphère offerte et une
sphère retirée de l'offre? Le profil reste-t-il valide en mode partiel, ou demande-t-il une
reconfiguration?

---

## Chantier 16 — Réévaluation datée du fossé *(charte, section 19)*

Chantier léger, sans code lourd, mais qui doit exister quelque part pour ne pas se reperdre.

**À construire.**
- Une **échéance de revalidation** sur les trois fossés de la section 3, au même mécanisme que les
  échéances de décision et de vérification légale (chantiers 6 et 10) — un seul mécanisme d'échéance,
  pas trois.
- Les **trois déclencheurs de revue immédiate** de la charte, consignés comme critères de veille :
  veille continue ou notification annoncée par un concurrent identifié, mise en correspondance
  service-besoin adoptée par un concurrent, produit dérivé lancé par un fournisseur de données vers
  les fournisseurs de services.
- Un lien avec le chantier 10 : si un fossé tombe, l'élément correspondant du matériel de vente passe
  au même état que les fonctionnalités non validées — retiré de la promesse, pas du produit.

---

# Partie 2bis — Chantiers offensifs

Les seize chantiers précédents réparent. Les quatre suivants exploitent des forces déjà présentes dans
le produit mais laissées à l'état de note. Tous sont additifs et à coût constant — mais **leur valeur
dépend de l'historique accumulé**, donc les commencer tôt fait mûrir l'actif plus vite, même si le
résultat n'est lisible que plus tard.

---

## Chantier 17 — Signal par absence et trajectoire, en première classe *(charte, section 21, force 1)*

**Constat.** Les deux capacités que personne ne peut reproduire sans mémoire sont mentionnées une fois
chacune dans les specs, avec la note qu'elles sont généralisables, et n'ont aucun mécanisme. Le signal
par absence est décrit comme un cas découvert avec un persona; la trajectoire, comme « un contributeur
additionnel au score ».

**À construire.**
- **Le signal par absence comme règle exprimable**, pas comme cas particulier codé pour les
  investisseurs. Il faut pouvoir déclarer, par sphère : « présence de A et B, **absence** de C et D
  sur une fenêtre donnée ». La généralisation est déjà demandée dans les specs — c'est le mécanisme
  qui manque.
- **La trajectoire comme dimension calculée du dossier cumulatif** : nombre de signaux sur une
  fenêtre glissante, force croissante ou décroissante, écart depuis le signal précédent. Trois signaux
  en deux mois et trois signaux en deux ans doivent produire deux résultats différents.
- **La conservation nécessaire à l'expression d'une absence.** Une absence ne se déduit que d'un
  ensemble connu de ce qui aurait dû apparaître : ce chantier dépend directement de la conservation
  d'état du chantier 1, et échouera silencieusement sans elle.

**Question de la section 11.** Que se passe-t-il quand une absence est due à une **source en
quarantaine ou défaillante** plutôt qu'à un fait réel? Une absence causée par une panne ne doit jamais
produire un signal positif — c'est le risque propre à cette capacité, et il n'existe pas pour les
signaux de présence.

**Réserve honnête.** Ce chantier a besoin de plusieurs mois d'historique pour dire quelque chose. Le
construire tôt sert à commencer à accumuler, pas à obtenir un résultat immédiat.

---

## Chantier 18 — Normalisation par la base et mesures de taille réelles *(charte, section 21, force 3)*

**Constat.** Sans base de comparaison, tout signal de volume favorise mécaniquement les grandes
entreprises — c'est-à-dire exactement celles qui ne sont pas la clientèle visée. Les specs appliquent
déjà ce principe ponctuellement (« valeur relative à la taille estimée » pour le RDPRM et le SEAO)
mais jamais systématiquement.

**À construire.**
- Une **taille d'entreprise à trois niveaux de fiabilité, jamais fusionnés en un seul chiffre** :
  mesurée (capacité RACJ, seuil 25+ de l'OQLF, à leur date), déclarée (bande d'effectifs du registre),
  estimée (signaux d'embauche cumulés). Chaque niveau porte sa provenance et sa date.
- Une **normalisation systématique des signaux de volume** par la taille et par le secteur, plutôt
  qu'au cas par cas. Cinq embauches chez une entreprise de dix personnes est un événement; chez une
  entreprise de cinq cents, c'est du bruit.
- L'usage du **miroir REQ complet** comme dénominateur : il permet de calculer ce qu'est un rythme
  normal pour un secteur et une taille donnés, au lieu de le supposer.

**Question de la section 11.** Que se passe-t-il quand la taille mesurée et la taille estimée se
contredisent — l'OQLF confirme 25+ employés il y a deux ans, les signaux d'embauche suggèrent une
entreprise plus petite aujourd'hui? La plus récente l'emporte-t-elle, ou la mieux mesurée?

---

## Chantier 19 — Le journal de diagnostic lu comme signal de demande *(charte, section 21, force 2)*

**Constat.** Le registre de diagnostic collecte déjà les descriptions mal classées, les « qui » non
résolus et les sources manquantes. Il est traité comme une file de correctifs. C'est aussi la
meilleure feuille de route produit disponible — ce que de vrais utilisateurs ont demandé et que le
produit n'a pas su servir.

**À construire.**
- Une **agrégation par motif** plutôt qu'une liste chronologique : quels types de service reviennent,
  quelles sphères manquent, quels territoires sont demandés.
- Un **croisement avec la densité** (chantier 9) : forte demande et faible densité est la définition
  exacte du prochain mandat de recherche de sources. C'est ce qui remplace la découverte par
  annulation d'abonnement.
- Une **lecture à intervalle régulier**, avec échéance (charte, section 15), plutôt qu'une consultation
  quand on y pense.

---

## Chantier 20 — Servir le public institutionnel qui est déjà à moitié construit *(charte, section 1 et section 21)*

**Constat.** La charte nomme depuis le début les chambres de commerce, le développement économique
régional et les institutions financières. Un persona existe. Les tableaux de bord agrégés par
territoire sont **déjà construits**. Mais le produit entier est conçu autour du vendeur B2B, et ce
public reste traité comme un débouché secondaire.

**Ce qui le rend structurellement intéressant, à documenter pour que la décision soit consciente :** un
organisme de développement économique n'a rien à vendre au prospect détecté — il veut savoir quelles
entreprises de son territoire grandissent, pour intervenir et pour justifier son impact. La fragilité
assumée du modèle, à savoir que rien n'empêche un utilisateur de contourner la plateforme une fois le
prospect connu, **ne s'applique pas à lui**. Son budget est institutionnel. Et un organisme de ce type
est aussi un canal vers ses propres membres.

**À construire — surtout du déblocage, peu de neuf.**
- Lever la limite documentée des tableaux de bord agrégés : l'agrégation par secteur est cassée par la
  granularité du champ en texte libre (211 valeurs distinctes sur 311 notifications). Le chantier 12
  règle ce problème de normalisation; ce chantier en récolte le bénéfice.
- Corriger le trou déjà documenté : les entreprises détectées hors Québec tombent systématiquement en
  « non classé », quel que soit leur domaine réel.
- Vérifier que le mode d'usage institutionnel — suivre un territoire entier plutôt qu'un profil de
  vente — est réellement exprimable dans l'architecture de profil actuelle, ou ce qui manque pour
  l'exprimer.

**Question de la section 11.** Que se passe-t-il quand un même compte porte à la fois un profil de
vente et un profil de veille territoriale? Les seuils de sensibilité, la cadence et le canal hors
profil ont-ils le même sens pour les deux? La réponse est probablement non, et il vaut mieux le
constater maintenant qu'après avoir vendu le premier abonnement institutionnel.

---

# Partie 3 — Ordre d'exécution

1. **Chantiers 1 et 2** — protègent la crédibilité, seule chose qui ne se rachète pas. Peu de code,
   effet immédiat, à faire avant de brancher le RACJ.
2. **Chantiers 3 et 4** — sans eux, tout ce qui est bâti ensuite s'appuie sur des liens d'identité dont
   personne ne connaît la solidité, et le produit reste structurellement québécois malgré son objectif
   pancanadien.
3. **Chantiers 5 et 7** — corrigent des contradictions entre les documents de référence et le produit.
   Aucun code lourd, mais ils changent ce qu'on vend, donc à trancher avant de vendre.
4. **Chantier 6** — bloquant pour l'activation des quatre nouvelles sources gratuites. À faire avant
   elles, pas après.
5. **Chantier 8** — fonctionnalité client, sûre à livrer une fois le socle sain.
6. **Chantiers 9, 10 et 11** — outils de pilotage, utiles dès qu'il existe assez d'historique pour
   qu'ils disent quelque chose de vrai.
7. **Chantier 12 — en parallèle, dès maintenant.** Ne touche à aucune table centrale, donc aucun
   risque de refonte et aucune raison d'attendre le socle. Son seul préalable est la grille
   `champs_pertinents.yaml`, déjà approuvée et jamais livrée. Sa validation finale dépend du
   chantier 9 : les liens proposés restent en attente de réfutation jusqu'à ce que la densité existe
   pour les juger.
8. **Chantiers 13, 14, 15 et 16 — additifs, à coût constant.** Ils ne touchent à aucune clé de données
   et se réparent au même prix dans six mois. Deux nuances : le chantier 14 (silence) est celui qui
   pèse le plus sur la rétention et mériterait de passer **avant** le chantier 8, puisqu'un abonné qui
   ne reçoit rien part bien avant de se plaindre d'une cadence; et le chantier 13 rend opérationnel le
   garde-fou de réfutation du chantier 12, donc les deux avancent naturellement ensemble.
9. **Chantiers 17 à 20 — offensifs, à démarrer plus tôt qu'il n'y paraît.** Leur résultat n'est
   lisible qu'après des mois d'historique, mais c'est exactement pour ça qu'il ne faut pas les
   repousser : ce qu'ils accumulent ne se rattrape pas en accélérant plus tard. Le chantier 17 dépend
   de la conservation d'état du chantier 1 et échouera silencieusement sans elle. Le chantier 18 est
   le plus indépendant des quatre et peut avancer n'importe quand. Le chantier 20 est surtout du
   déblocage : il récolte le bénéfice du chantier 12 plutôt que de construire du neuf.

**Une remarque sur le séquencement global.** Les chantiers 1 à 7 ne sont pas des ajouts : ce sont des
réparations d'écarts entre ce que les documents promettent et ce que le code fait. Les livrer avant les
premiers clients payants coûte quelques semaines. Les livrer après coûte des clients, et pour au moins
trois d'entre eux — la faille A, la faille B et la faille H — le client s'en apercevrait avant nous.
