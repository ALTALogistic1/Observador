# FALKYE — Audit transversal et mandat de consolidation

Destiné à Claude Code. À lire avec `charte-falkye.md`, `falkye-guide-ingenierie.md` et les
spécifications produit.

**Nature de l'exercice.** Ce n'est pas une liste de fonctionnalités manquantes. Ce sont des endroits où
**le produit contredit ses propres documents de référence**, ou bien où une décision a été prise
correctement puis n'a jamais reçu de mécanisme. **La plupart sont invisibles en test unitaire parce que
chaque pièce fonctionne : c'est leur combinaison qui casse.**

---

# Glossaire — les cinq mots qui portent deux sens

**À lire avant le reste.** Ces cinq mots désignent chacun plusieurs choses dans le corpus. Ce n'est pas
une coquetterie de vocabulaire : **la contradiction du 7 septembre s'était logée dans le premier
d'entre eux**, et personne ne la voyait parce que le même mot couvrait les deux réalités.

**« État » — deux choses sans rapport.**

- **L'état d'une source** *(chantier 1)* — l'instantané complet de la dernière exécution réussie d'un
  connecteur, sans lequel un diff ne peut pas se calculer. **Le perdre, c'est perdre des événements
  définitivement.**
- **L'état du produit** *(chantier 29)* — ce qui vit dans la base durable et survit au recyclage d'un
  conteneur.

**⚠️ Le piège exact.** Le premier peut être rangé hors du second sans que rien ne le signale, **et il
l'est peut-être** : l'historique et les quarantaines de diff sont l'état du chantier 1, présumés couverts
par la garantie du chantier 29. *Question ouverte, à la fiche du 29.* **La garantie du 29 ne couvre pas
automatiquement l'état du 1 : elle ne le couvre que si les tables sont au bon endroit.**

**« Journal » — cinq choses. Toujours qualifier, jamais dire « le journal ».**

| Terme | Ce que c'est |
|---|---|
| **Journaux d'exécution** | Les trois tables qui décrivent une exécution — `SourceRunLog`, `DiffRunHistorique`, `DiffQuarantaine`. *Point 27.4, chantier 2.* |
| **Journal de diagnostic** | Fonctionnalité produit : ce que des utilisateurs ont demandé et que le produit n'a pas su servir. **Force structurelle, pas correctif.** *Chantiers 11 et 19.* |
| **Journal de repli** | `/var/lib/falkye/journal-repli.jsonl` — filet d'écriture quand la base est injoignable. **Devenu source de vérité de la réconciliation.** *Chantier 2, décision B.* |
| **Journaux d'exploitation** | Traces de service de l'hôte. *Chantier 28.* |
| **Journal des cas** | `falkye-journal-des-cas.md`, document du corpus. Les renvois « journal, cas N » y pointent, **et nulle part ailleurs.** |

**Numéro contre rang.** Le **numéro** est un identifiant stable — tout le corpus y renvoie, il ne change
jamais. Le **rang** donne l'ordre de travail et se réajuste. **Le 29 porte le plus haut numéro et il est
presque clos; le 22 porte le rang 3.** Aucune information ne se lit dans un numéro.

**Statut d'exécution contre état de santé.** Le **statut d'exécution** décrit *un run* — `en_cours`,
`erreur`, `interrompue`, quarantaine, réussite publiée. L'**état de santé** décrit *une source* — sept
valeurs, dont « en attente d'une action externe ». **Un statut d'exécution ne se propage pas
automatiquement en état de santé** : un quota épuisé interrompt le cycle sans qu'aucune source ne soit
malade. Les confondre recréerait exactement la confusion que le chantier 2 existe pour lever.

**Chantier, travail, point — trois échelles.** Un **chantier** est un bloc numéroté de cette Partie 2. Un
**travail** est une étape à l'intérieur d'un chantier *(chantier 2, travail 1bis)*. Un **point** est une
subdivision numérotée du chantier 27 *(27.1, 27.4, 27.9)*. **La taille ne suit pas l'échelle** : le point
27.1 représente plus de travail que plusieurs chantiers entiers.

---

# Registre des décisions ouvertes

**Ce registre existe parce que la charte l'exige et que rien ne l'appliquait.** Section 15 : *toute
entrée à l'état « décision jamais tranchée » porte une échéance et réapparaît à cette date. L'échéance
est obligatoire au moment où l'état est posé, jamais ajoutée après coup.* **Quatorze décisions ouvertes
étaient dispersées dans trois documents, aucune datée.** *(journal, cas 15 — une décision réelle a
disparu du suivi pendant des mois, ni rejetée ni reportée.)*

**Elles vivent ici et nulle part ailleurs.** Les documents d'origine y renvoient au lieu de les
redécrire. **Trancher inclut « non, et voici pourquoi ».**

| # | Décision | Origine | Déclencheur ou échéance |
|---|---|---|---|
| D1 | Résidence des données de la base distante | Spéc. §15, chantier 29 | **Déclencheur : décision d'ouvrir les inscriptions** — migrer à vide |
| D2 | Autorisation commerciale du REQ | Spéc. §15, cadre légal | **Déclencheur : premier engagement commercial**, moins quinze jours ouvrables |
| D3 | Crunchbase | Spéc. §15, stratégie §8 | ⬜ *à dater* — **vivante : sert le Québec.** Seule voie restante pour l'angle mort du financement privé québécois, que SEDAR+ n'a refermé que partiellement *(le jeu ouvert ontarien ne couvre que les levées avec acquéreurs ontariens)* |
| D4 | Prix du palier supérieur | Spéc. §15, charte §5 | ⬜ *à dater* |
| D5 | Autorisation OQLF | Spéc. §15, §4.6 | ⬜ *à dater* |
| D6 | Clarification légale du RDPRM | Spéc. §15, §12.4 | ⬜ *à dater* |
| D7 | La méthode de diagnostic est-elle le produit? | Charte §20, spéc. §15 | ⬜ *à dater* — **trancher inclut « non, le logiciel reste le produit »** |
| D8 | Revalidation de l'avantage défendable | Charte §19 | ⬜ *à dater* + trois déclencheurs immédiats déjà définis |
| D9 | Enrichissement web — le déplacer après le seuil? | Spéc. annexe pt 10, point 27.1 | ⬜ **avant d'optimiser le 27.1** — il sert aussi de filtre d'exclusion |
| D10 | Où vivent l'historique et les quarantaines de diff | Chantier 29, chantier 2 | ✅ **Tranchée le 9 septembre** — mesurée dans le fichier miroir local, pas sur la base durable. Les copies vides distantes n'ont pas reçu la colonne. *Reste la confirmation positive par la sortie sur l'hôte.* |
| D11 | La quarantaine : issue d'exécution ou état de santé? | Chantier 2, spéc. §5.5 | ⬜ **avant la taxonomie des états** |
| D20 | Vérification de fusion : mesurer la dérive en production | Flux `schema`, chantier 27 | ✅ **Écartée le 9 septembre** — exigerait les identifiants de base dans les secrets du dépôt, ce qui défait la propriété de l'architecture des secrets : une chaîne compromise peut redémarrer le service, jamais lire la base. *Raisonnement complet et chemins écartés à `docs/DEPLOIEMENT.md`.* |
| D21 | Colonnes présentes en base et absentes du modèle | `migration_colonnes.py`, point 27.9 | ⬜ **après la sortie sur l'hôte** — la chaîne n'ajoute que, donc l'écart se creuse en silence dans ce sens-là |
| D22 | Seuil de publication — à partir de quelle case un dossier devient une opportunité présentée | Mandat chantier 21, §1 | ⬜ *à dater* — **distinct du curseur de sensibilité de l'utilisateur**, les fusionner lui retirerait la possibilité d'être plus sélectif |
| D23 | Inventaire des libellés visibles par l'utilisateur | Mandat chantier 21, §7 | ⬜ *à dater* — six révisions et deux propositions à trancher explicitement. **Du texte destiné aux clients, pas une décision technique** |
| D24 | Fraîcheur : signal ancien fort contre signal récent faible | Mandat chantier 21, §2 | ⬜ **avant de construire la modulation du grade** — la fraîcheur porte-t-elle sur le plus récent, le plus fort, ou l'ensemble? |
| D25 | ProcureData | Stratégie §8 | ⬜ *à dater* — **vivante si sa couverture inclut le Québec.** ⚠️ *Le corpus n'en dit rien d'autre : ni ce qu'elle vend, ni son coût, ni la sphère servie. À décrire avant de pouvoir la trancher.* |
| D26 | Registre de Colombie-Britannique | Stratégie §8 | 💤 **En veilleuse, pas à dater** — il couvre des entreprises de C.-B., donc sans objet tant que la portée est québécoise |
| D27 | Trouver un registre officiel des entités publiques québécoises | Chantiers 3+4, 20; spéc. §7.2 | ⬜ **avant la conception de la clé du chantier 3** — il ferait pour le public ce que le REQ fait pour le privé, et retirerait au SEAO sa double nature |
| D28 | Règle de classement d'une entité en publique ou privée | Chantiers 3+4 | ⬜ **avec D27** — société d'État, organisme paramunicipal, coopérative subventionnée : la règle doit avoir une **réponse par défaut** quand elle ne tranche pas, sinon on remplace une ambiguïté de source par une ambiguïté d'entité |
| D29 | Entité portant les deux identifiants — lequel fait foi | Chantiers 3+4 | ⬜ **avec D27** — une identité peut en porter plusieurs *(spéc. §6.1)*, mais **la vérification du statut légal doit en désigner un** |
| D12 | Seuils d'alerte de dérive | Mandat chantier 2, livrable 6 | ⬜ **avant clôture du chantier 2** |
| D17 | Seuils de quarantaine par défaut | Mandat chantier 1, livrable 6 | ⬜ *à dater* — **même forme que D12, jamais une constante enfouie** |
| D18 | Exception canadienne pour la fouille de textes et de données | Cadre légal | ⬜ *à revalider* — si elle entre en vigueur, elle change l'analyse des sources |
| D19 | Licence et fréquence du jeu ouvert de la CVMO | Recommandations sources, priorité 3 | ⬜ *à vérifier manuellement* — le site bloque l'accès automatisé |
| D13 | Fenêtre de restauration — comportement réel | Chantier 29, point 27.9 | ⬜ **avant toute migration destructive** |
| D14 | Le repli par sous-chaîne : borner ou retirer? | Chantier 2, instrument de coût | ⬜ **après le premier rapport de coût en régime** |
| D15 | Le vide du 8 septembre — miroir absent ou appariement? | Journal cas 10, faille D | ⬜ **avant de s'en servir comme prémisse** — une commande tranche |

**Vingt-neuf entrées : deux tranchées, douze portant un déclencheur ou une condition de levée, quinze
attendant encore une date.**

**⚠️ Portée : tout ce qui touche un territoire hors Québec est en veilleuse.** *Décision du 4 septembre
2026, stratégie §3 — le produit se rend pleinement fonctionnel au Québec d'abord.* **Ce n'est pas
l'origine d'une source qui décide, c'est qui elle couvre.** Une source fédérale ou un fournisseur de
données où figurent des entreprises québécoises reste vivant; un registre provincial d'ailleurs est sans
objet. *Les décisions marquées 💤 ne se datent pas tant que cette portée tient.* *Le compte se relit dans le tableau, il ne se recopie nulle part.* Une
décision reconduite doit dire **ce qui manque pour la trancher**, sans quoi elle sera reconduite
indéfiniment par le même réflexe.

**Le même mécanisme couvre les vérifications qui se périment** — la table de prix de l'instrument de
coût, les licences de sources, la section 3 de la charte. *Sans échéance de revalidation, la diligence
d'aujourd'hui devient la présomption de dans deux ans.*

---

# Partie 0 — Quelles failles coûtent cher si on attend

**Le critère : est-ce que le coût de la réparation augmente avec le temps qui passe?** La plupart des
failles sont **additives** — un attribut, une règle de configuration, un tableau de bord par-dessus
l'existant, réparable dans six mois au même prix. **Trois ne le sont pas.**

## Les trois failles à coût croissant

**Faille C — l'identité d'entreprise.** Coût proportionnel au **volume de dossiers déjà accumulés sur une
clé de territoire**. C'est la seule qui menace une refonte au sens strict : au deuxième territoire ancré,
il faudra soit dupliquer la logique de corroboration et de déduplication, soit migrer l'historique.

**Faille E — la conservation d'état.** Coût **irrécupérable**, pas seulement croissant. Une source de
type instantané qui tourne sans conserver son état complet ne perd pas du temps de développement : **elle
perd des événements définitivement.** Ce qui survient entre deux exécutions non conservées n'existera
jamais nulle part.

**Faille D — la confiance d'appariement.** Croissant à double titre. Les fusions déjà faites perdent
leur trace probabiliste au fur et à mesure. Et **la table d'apprentissage s'enrichit avec le temps** :
la construire tard, c'est repartir d'une table vide alors que les mauvais appariements, eux, se sont
accumulés.

## Les autres — additives, mais trois portent une urgence commerciale

**Failles A et H** — palier d'entrée vide, fonctionnalités jamais validées en réel. Elles ne coûtent
rien de plus à réparer plus tard, mais elles coûtent **des clients** si elles franchissent la mise en
marché. **Un abonné qui ne reçoit rien pendant un mois ne revient pas.**

**Faille K** — la page de crédits ne coûte rien à construire mais elle est **bloquante à l'activation**
des sources gratuites : les brancher sans elle met le produit en défaut de licence dès le premier jour.

**Faille B** — additive dans son mécanisme, mais elle dépend de la faille C : **le niveau de vérification
par territoire n'a nulle part où vivre tant que l'identité interne n'existe pas.** Les deux se livrent
ensemble.

## Ce que ça donne concrètement

**Le chantier 1 a réglé la faille E.** Des trois failles à coût croissant, il reste **les chantiers 3 et
4, à livrer ensemble** — ce sont les seuls à ne jamais reporter. Tout le reste peut attendre sans que le
coût change, **à condition de ne pas lancer commercialement avant d'avoir réglé A, H et K.**

---

# Partie 1 — Failles constatées

*Classées par ce que ça coûterait si personne ne le voyait avant les premiers clients payants.*

---

## Faille A — Le palier d'entrée est structurellement vide

**Constat.** Les cinq sources gratuites vérifiées le 3 septembre 2026 ont toutes été placées dans les
paliers supérieurs. **Chacune est la seule source existante pour sa sphère cible** — le corpus le dit
lui-même. Conséquence mécanique : **un abonné du palier d'entrée qui déclare l'une de ces cinq sphères ne
recevra jamais rien.** Pas peu de résultats : aucun.

**⚠️ Mesuré le 6 septembre 2026, plus grave que le diagnostic initial.** Le premier cycle sur données
réelles a livré un résumé **vide, correctement** : les 1 672 signaux du SEAO portent **tous la même
sphère unique**, et le profil d'essai en visait une autre. **Une source qui ne peut servir qu'une sphère
sur trente-quatre** — il a fallu relier cette sphère au profil pour obtenir un envoi non vide, parce que
c'est la seule que la source peut servir. **Le choix était forcé, et c'est ça le constat.**

**La faille ne porte donc pas sur cinq sources mal placées : le portefeuille branché ne couvre presque
rien.**

**Pourquoi c'est arrivé.** Deux règles se contredisaient : la grille disait qu'une source améliorant un
résultat existant va au palier supérieur, la charte disait le contraire pour ce cas — **la question n'est
ni le coût ni l'enrichissement, mais si le palier d'entrée produit des opportunités crédibles pour cette
sphère**. La règle mécanique a été appliquée, celle de la charte perdue *(journal, cas 1)*.

**Remède : chantier 5** — une distinction couverture / enrichissement, calculable plutôt que laissée au
jugement.

---

## Faille B — La vérification de base est impossible hors Québec

**Constat.** Les spécifications imposent trois vérifications avant toute présentation d'un prospect, en
insistant que ce n'est pas optionnel. **Les deux premières passent par le NEQ.**

**Le problème.** Six sources actives ou vérifiées **ne fournissent aucun NEQ**, et les entreprises
qu'elles détectent n'en ont souvent aucun. La vérification obligatoire est donc **structurellement
inapplicable à toute une moitié du produit**.

**Deux comportements possibles, tous deux mauvais** : exclure les prospects hors Québec, et le produit
n'y fonctionne pas; ou sauter silencieusement la vérification, et **la promesse « aucun prospect présenté
sans vérification » n'est pas tenue** — ce que la charte interdit nommément.

**Remède : chantiers 3 et 4** — une vérification relative au territoire plutôt qu'absolue. **Elle n'a
nulle part où vivre tant que l'identité interne n'existe pas**, d'où la livraison conjointe.

---

## Faille C — Le pivot québécois est correct; ce qui est structurel, c'est qu'il est aussi le pivot de l'architecture

**Nuance d'entrée, parce qu'elle change la nature du problème.** Que le NEQ soit la colonne vertébrale
**du Québec** n'est pas une faille. **Ce qui est en cause, c'est qu'il est simultanément la clé de
déduplication, de corroboration, du dossier cumulatif et le véhicule de la vérification des radiées** —
**quatre fonctions qui appartiennent au moteur, pas au territoire**, et qui s'appliquent identiquement à
une entreprise qui n'aura jamais de NEQ.

Autrement dit : **la charte dit qu'un territoire a sa source Piste, et le code dit que le produit a une
clé primaire.** Les deux ne sont compatibles que si la clé est **interne**, le NEQ étant ce qui l'ancre au
Québec plutôt que ce qu'elle est.

**Pourquoi c'est le point le plus coûteux du document.** Tant qu'il n'y a qu'un territoire ancré, la
confusion ne se voit pas. Elle coûte quand un deuxième identifiant Piste arrive — deux registres
provinciaux sont déjà identifiés — et **il n'y a alors que deux issues** : un deuxième pivot en
parallèle, qui double la logique de corroboration et de déduplication partout, ou une migration de tout
l'historique. **Le coût augmente chaque semaine**, proportionnellement au volume accumulé.

**Remède : chantiers 3 et 4 — un déplacement, pas un affaiblissement.** Le NEQ reste l'identifiant Piste
du Québec; **ce qui change, c'est qu'une identité sans NEQ devient valide de plein droit plutôt qu'un cas
dégradé.**

---

## Faille D — L'appariement par nom, et l'incertitude qui n'est suivie nulle part

**⚠️ Mesurée trois fois, chaque fois plus durement.**

| Mesure | Résultat |
|---|---|
| 1 248 entreprises du SEAO résolues contre le miroir, 6 septembre | **42 % résolues, 56 % ambiguës** |
| Base de production complète, 8 septembre | **65 % ambiguës** |
| Entreprises passant la vérification | **0,8 %** |

**⚠️ Le même chiffre porte deux explications dans le corpus, à vérifier avant de s'en servir comme
prémisse.** Le journal des cas, cas 10, attribue « 953 signaux réels ingérés sur 768 entreprises, zéro
notification » à **l'absence du miroir REQ dans la base de production** — tout était « non trouvé ». La
mesure ci-dessous attribue le même vide au **taux de vérification de 0,8 %**. *Lecture la plus probable,
non établie : c'est le même lot de 953 signaux, qui a heurté deux murs successifs — d'abord le miroir
absent, puis, une fois le miroir chargé, l'appariement.* **Si c'est exact, le dire; si le vide du
8 septembre a été mesuré avant le chargement du miroir, la mesure a été prise dans de mauvaises
conditions** *(charte, section 0, règle 3)* **et l'argument qui fait des chantiers 22 puis 3+4 les
suivants repose dessus.**

**Conséquence directe, constatée le 8 septembre : 953 signaux correspondent au profil, aucun ne porte sur
une entreprise vérifiée.** Le premier envoi réel est parti vide. Le produit détecte correctement et
refuse de présenter, faute de savoir qui il présenterait. **Ce n'est plus une amélioration, c'est ce qui
décide du volume.**

**Le corpus documentait déjà les dégâts** : 76 paires de doublons non reconnues, une fusion erronée entre
deux compagnies à numéro qu'il a fallu restaurer depuis une sauvegarde, et 20 candidats en attente avec
des faux positifs identifiés d'avance.

**Ce qui manque.** L'incertitude est résolue **au moment de la fusion**, puis oubliée. Une fois deux
enregistrements fusionnés, le dossier ne porte plus aucune trace du caractère probabiliste du lien. Les
signaux s'y accumulent, la corroboration les additionne, la confiance monte — **et un signal fort finit
rattaché à une entreprise avec une assurance que rien ne justifie**.

**Un signal fort rattaché à la mauvaise entreprise est pire qu'un signal faible bien rattaché** : il
produit une notification confiante et fausse, le seul type d'erreur que l'utilisateur ne peut pas
détecter lui-même.

**Remède : chantiers 3 et 4** — un troisième axe indépendant, qui **plafonne** la confiance du signal au
lieu de s'y additionner.

*Le problème structurel qu'il faut garder en tête : le registre porte la **raison sociale** pendant que
les permis portent le **nom d'enseigne**. **Deux univers de chaînes qui ne se rejoignent jamais par
similarité textuelle**, quel que soit l'algorithme.*

---

## Faille E — Un moteur de diff d'instantanés, sans protection contre un diff aberrant

**Constat.** Plusieurs sources actives **ne fournissent aucune date d'événement** — la détection vient
donc de la comparaison de deux états successifs. C'est le cas de la source de priorité 1.

**Le risque.** Qu'un diffuseur renomme une colonne ou réassigne ses identifiants, et **le diff produit
des milliers de fausses ouvertures : une vague de notifications absurdes part chez tous les clients le
même matin.** **Le seul scénario du document qui coûte la crédibilité d'un coup** plutôt que
graduellement — et il coûte une journée à prévenir.

**Solution :** la règle de quarantaine du chantier 1. ✅ **Livrée.**

---

## Faille F — Trois sources à zéro signal pour trois raisons différentes, et rien ne les distingue

**Constat.** Une source est à zéro parce que c'est normal, une autre parce qu'elle n'est pas implémentée,
une troisième parce qu'elle n'est pas validée : **trois états radicalement différents, un seul symptôme
observable.** La distinction tient aujourd'hui dans une tête — **avec vingt sources et six mois d'écart,
un connecteur cassé silencieusement sera indiscernable d'un territoire calme.**

**Solution :** l'état de santé par source, chantier 2.

---

## Faille G — Le canal « hors profil » n'existe pas là où le désaccord se produit

**Constat.** La règle est générale et s'applique à tous : quand le « qui » de l'entreprise ne correspond
pas au « qui » déclaré, le signal **ne devient jamais un malus silencieux** et se redirige vers un canal
séparé. **Mais le canal était réservé au palier supérieur.**

**Le problème.** Ailleurs, la redirection n'a pas de destination : le signal n'est ni montré ni dirigé
ailleurs — **il disparaît.** **Exactement le malus silencieux que la règle voulait empêcher, obtenu par
un autre chemin.**

**Tranché : la redirection a lieu dans tous les paliers.** Le canal n'est plus un différenciateur. Ce que
le palier supérieur conserve porte sur **ce qu'on peut faire du canal** — alertes composites,
conversion en nouveau profil, poussage par webhook.

---

## Faille H — Des fonctionnalités vendables qui n'ont jamais tourné contre du réel

**Constat.** La grille marque d'un ✓ des capacités jamais validées hors mock : intégrations CRM,
paiement, assistance de niveau 2, source d'offres d'emploi payante, géocodage.

**Le problème.** **La grille est le document qui dit ce que le client reçoit**, et elle ne distingue pas
« construit » de « éprouvé contre le vrai service ». Le risque n'est pas technique, il est commercial :
vendre un plan dont une fonctionnalité annoncée casse au premier usage.

**Remède : chantiers 10 et 16** — un troisième état à côté du ✓ et du tiret.

---

## Faille I — Les décisions ouvertes disparaissent du suivi

**Constat.** Une décision budgétaire réelle, sur un angle mort documenté, a disparu du suivi pendant des
mois *(journal, cas 15)*. **Le problème n'est pas cette décision** — c'est qu'une décision non tranchée
n'a aucun mécanisme qui la fasse revenir. Le prix du palier supérieur, « à réviser », est dans le même
état.

**Remède : chantiers 10 et 16** — une échéance qui fait revenir la décision.

---

## Faille J — Deux sphères déclarées résolues par une méthode qui n'existe pas dans le produit

**Constat.** La recherche conclut correctement que l'une se traite par une règle de mots-clés et l'autre
par dérivation d'autres signaux. **Les deux conclusions sont justes.**

**Le problème.** Le registre ne connaît qu'un seul type de sphère. Rien ne distingue une sphère directe
d'une dérivée, et rien ne porte la règle de dérivation. **Résultat : deux sphères qu'un utilisateur peut
sélectionner, pour lesquelles la documentation dit qu'une solution existe, et dont le moteur ne sait
rien.**

**Remède : chantiers 7 et 15** — un attribut de type sur la sphère, et la règle de dérivation au
registre plutôt que dans un document.

---

## Faille K — L'obligation d'attribution n'a pas de destination

**Constat.** Quatre sources vérifiées portent une obligation d'attribution — l'une précise même qu'elle
s'applique lorsque les données sont intégrées à une base qu'on possède. **Rien ne construit la page de
crédits que la charte prévoit.**

**Activer ces sources sans elle place le produit en défaut de licence dès le premier jour.**

**Solution :** chantier 6.

---

# Partie 2 — Chantiers

## Index — les vingt-trois blocs de travail restants, par ordre

**Ce document décrit tous les chantiers. La fiche est le mandat par défaut** — un chantier sans document
séparé se construit à partir d'elle. **Un mandat détaillé s'écrit quand le chantier passe en tête de
file**, il est tenu à jour, et **conservé après la clôture** : il porte le raisonnement qui a produit le
code. **Quand les deux se contredisent, l'audit tranche.**

**Convention des sections « État ».** ✅ fait avec sa preuve · 🟡 en cours · ⚠️ **présumé fait, non
vérifié** · ⬜ à faire. **Une case cochée porte ce qui l'a établie — sinon elle peut mentir.** Le
troisième état est celui qui manquait partout, **et c'est exactement là que se trouvaient les trois
écarts du 7 septembre**.

**Les numéros sont des identifiants stables** — tout le corpus y renvoie, et ils ne changent jamais.
**C'est le rang qui donne l'ordre de travail.** Le coût d'attente reprend le test de la Partie 0 :
*irrécupérable* — reporter détruit de la donnée; *croissant* — le prix monte avec le volume accumulé;
*constant* — même prix dans six mois.

| Rang | Nº | Nom | Ce qu'il règle | Coût d'attente |
|---|---|---|---|---|
| 🟡 | 29 | **Persistance de la base et hôte** | Trois gestes restent, et une question ouverte sur le placement des tables de diff | — |
| ✅ | 1 | **Quarantaine de diff** | Conserver l'état d'une source, quarantaine, écriture groupée | — |
| ✅ | 28 | **Première boucle complète** | Courriel réel livré et authentifié | — |
| 🟡 2 | 2 | **Santé de source** | Distinguer une source silencieuse d'une source brisée — **et mesurer ce qu'un cycle coûte** | Constant |
| 3 | 22 | **Calibration et durée de pertinence** | La lecture du signal — **précède 4 et 6** | Constant |
| 4 | 3+4 | **Identité et confiance d'appariement** | La clé du moteur, et le score qui la qualifie | **Croissant** |
| 5 | 27 | **Consolidation** | Point 27.1 d'abord — l'enrichissement est la moitié d'un cycle | Constant |
| 6 | 5 | **Placement des sources et fonctionnalités** | Couverture contre enrichissement, par couple | Constant |
| 7 | 6 | **Registre légal et page de crédits** | Bloquant pour l'activation des sources gratuites | Constant |
| 8 | 7 | **Canal hors profil et sphères dérivées** | Un signal redirigé qui ne disparaît plus | Constant |
| 9 | 26 | **Passerelle du non déterministe** | Deux composants — avant 12, 18 et 21 | Constant |
| 10 | 13 | **Précision perçue** | Instrumenter le faux positif à partir des rejets collectés | Constant |
| 11 | 14 | **Comportement en l'absence de signal** | Le silence, mode de défaillance principal | Constant |
| 12 | 21 | **Narratif et présentation** | Structure de faits, gabarits, seuil de publication | Constant |
| 13 | 23 | **Cycle de vie d'une opportunité** | Ce qui arrive quand un dossier livré reçoit un signal | Constant |
| 14 | 24 | **Péremption et archivage** | Archiver sans effacer, et exiger une réponse au retrait | Constant |
| 15 | 25 | **Le premier jour d'un abonné** | L'antériorité, plafonnée et présentée comme telle | Constant |
| 16 | 8 | **Cadence et livraison** | Groupement, mardi, fenêtre de 10 h, cadence par profil | Constant |
| 17 | 9 | **Densité de signal** | L'instrument qui rend le placement calculable | Constant |
| 18 | 12 | **Inventaire champ ↔ sphère** | Diagnostic à rebours sur les sources déjà actives | Constant |
| 19 | 15 | **Retenue** | Séparer le registre interne de l'offre | Constant |
| 20 | 18 | **Normalisation par la base** | Un signal ne veut rien dire sans base de comparaison | Constant |
| 21 | 10+16 | **Validation réelle et échéances** | Un troisième état, et des décisions qui reviennent | Constant |
| 22 | 17 | **Absence et trajectoire** | Les deux capacités qu'un outil de recherche ne peut avoir | Constant |
| 23 | 11+19 | **Le journal de diagnostic** | Ce qu'on y écrit, et ce qu'on en lit comme demande | Constant |
| 24 | 20 | **Public institutionnel** | Surtout du déblocage — il utilise moins du produit | Constant |

**Trois regroupements, parce qu'ils partagent le même mécanisme.** *3 et 4* — le score est porté par
l'identité, il n'a nulle part où vivre sans elle, et **les séparer voudrait dire migrer deux fois la même
clé**. *10 et 16* — les deux reposent sur **l'ordonnanceur unique d'échéances** du point 27.2. *11 et
19* — **même table**, écriture puis lecture.

**Les chantiers 22 à 25 partagent un mandat, pas un mécanisme.** Ils suivent la même chaîne — du signal
calibré à l'opportunité archivée — et **le 25 dépend du 22**, qui fixe la durée de pertinence. Mais
**c'est une dépendance, pas une fusion** : chacun se livre séparément, et seul le 22 est urgent.

**Deux regroupements écartés, et c'est utile de savoir pourquoi.** *9 et 13* sont deux instruments
calculés sur l'historique, mais leurs consommateurs diffèrent : la densité valide le placement, le taux
de rejet réfute les liens champ↔sphère. *14 et 17* parlent tous deux d'absence, mais ce sont **deux
absences opposées** — l'une est un silence subi côté utilisateur, l'autre un signal détecté parce que
quelque chose n'est pas arrivé. **Ne jamais les confondre.**

**Sur le chantier 3, après la mise en veilleuse du hors-Québec.** La plupart des identités porteront un
NEQ, donc le cas de l'identité sans identifiant externe devient plus rare — **mais il ne disparaît pas**,
deux sources vérifiées n'en livrant aucun. Le chantier garde son rang **pour une raison de coût, pas de
fonctionnalité** : son prix monte avec le volume accumulé, et différer l'expansion est précisément ce qui
le renchérit.

**Pourquoi le chantier 22 précède les chantiers 4 et 6.** Le moteur de notation n'est pas en cause : il
calcule fidèlement ce qu'on lui donne. **Tous les signaux d'une source portent aujourd'hui la même sphère
avec la même confiance, donc le score n'a rien à départager.** Le raffiner avant d'avoir appris à lire un
signal produirait une notation plus fine nourrie de la même uniformité.

**Ce que les deux chantiers clos ont apporté à l'ordre.** Le chantier 28 a fait exister la chaîne
complète, et **c'est lui qui a transformé trois hypothèses en mesures** — la faille A chiffrée, la faille
D chiffrée deux fois, et un estimé de mémoire qui aurait tué le serveur. **Chaque décision produit prise
avant lui était de la conception d'avance.**

**Les premiers rangs ne se réordonnent pas** : ils protègent ce qui ne se rachète pas ou ce qui renchérit
chaque semaine. Le reste s'ajuste selon les besoins, **avec deux contraintes** : le chantier 26 précède
12, 18 et 21; le chantier 9 conditionne la validation de 5 et de 12.

## Règles applicables à tous les chantiers

1. **Registre extensible, jamais d'énumération codée en dur.** Cadences, états de santé, niveaux de
   vérification, types de sphère : tout s'ajoute sans migration structurelle.
2. **La question de désaccord est une condition de fin.** Chaque chantier touche une dimension déjà
   pluralisée ailleurs. **Répondre par écrit, dans le code ou la doc, à la question posée sous chaque
   chantier** — aucune ne doit rester sans réponse implémentée et testée.
3. **Vérification macro.** Tout mécanisme se teste contre **toutes** les sources actives, pas seulement
   celle qui a motivé sa conception.
4. **Aucun nom de source visible par l'utilisateur**, sauf les deux exceptions délibérées : le portail de
   sources payantes et la page de crédits. **Les tableaux de bord d'exploitation ne sont pas l'interface
   utilisateur** — les séparer nettement dans le code.
5. **Étendre la suite de tests existante**, ne pas en créer une parallèle.

---

## Chantier 1 — Quarantaine de diff : conserver l'état d'une source *(faille E)*

**✅ Livré.**

**Ce qui a été construit.** Un moteur de diff générique partagé par les sources de type instantané,
conservant **l'état complet** de la dernière exécution réussie et pas seulement les écarts — sans quoi
une exécution manquée serait une période d'événements perdue définitivement. Une **règle de quarantaine**
paramétrable : au-delà d'un seuil d'écart, **rien n'est publié**, l'état précédent reste intact et le
diff suspect est archivé. Une **détection de changement de schéma** qui déclenche la quarantaine quel que
soit le volume. Et une levée explicite et journalisée.

**Question de désaccord, à vérifier si elle ne l'a pas été.** Deux sources en quarantaine dans la même
exécution; et une source en quarantaine alimentant un signal déjà partiellement corroboré par une source
saine — **le dossier reflète-t-il la corroboration partielle, ou attend-il?**

### État

- ✅ **Conservation d'état, diff, quarantaine, journalisation d'amplitude** — 456 tests, deux bogues de volume trouvés en vérification macro.
- ✅ **Rebranchement des quatre connecteurs** — migration réelle depuis les miroirs accumulés.
- ✅ **Le moteur refuse l'émission en run de référence** — rappel invoqué par le moteur, jamais par le connecteur.
- ✅ **Écriture groupée sur les trois chemins** — 12 → 5 049 lignes/s en apparition; les disparitions ne plantent plus au-delà de 32 766 clés.
- ⚠️ **Chemin d'import du miroir non traité** — deux allers-retours par ligne, mesuré. Renvoyé au chantier 27.

---

## Chantier 2 — Santé de source *(faille F)*

**🟡 Ouvert le 8 septembre 2026.** *Mandat détaillé : `falkye-chantier-2-sante-source.md`.*

**⚠️ Deux décisions prises avant l'écriture du code, qui modifient le mandat.** Elles priment sur la
version antérieure du mandat détaillé tant qu'il ne les a pas absorbées.

**Constat.** Le chantier 1 traite le cas où une source produit **trop** de changements; celui-ci traite
l'inverse, plus fréquent : **une source qui ne produit rien** — et **plusieurs causes distinctes
produisent ce symptôme unique, dont deux qui ne sont pas techniques** : une source qui attend une clé ou
un compte, et une décision jamais prise. *La liste des causes est celle des états de santé, et elle vit
à un seul endroit — spécifications, section 5.5. Ne pas en recopier le compte ailleurs : il a divergé
entre trois documents avant le 8 septembre.*

**Les grandes lignes.**

- **Un historique d'exécution à trois issues jamais confondues en booléen** — échec technique,
  quarantaine, réussite publiée. **« Dernière exécution réussie » désigne la troisième, jamais la
  deuxième.**
- **Unifier les trois journaux d'exécution.** C'est le premier critère d'acceptation, **et il échoue déjà**
  : un connecteur en quarantaine s'enregistre comme un succès à zéro signal, indiscernable d'un
  territoire calme.
- **Une norme de volume apprise par source, sur sa propre cadence**, avec alerte **dans les deux sens** —
  un volume anormalement bas trahit un connecteur qui se dégrade sans cesser de fonctionner, **le cas le
  moins visible**.
- **Sept états de santé**, dont « en attente d'une action externe » — le plus courant en ce moment — et
  **le champ nomme l'action attendue**, pas seulement l'état.
- **La fenêtre de rattrapage.** Le cycle calcule ses trente jours **sans consulter la dernière exécution
  réussie** : ce qui dépasse la fenêtre n'est jamais repris.
- **Un tableau de bord d'exploitation interne**, dont aucun état ne peut fuir vers l'interface.
- **Refermer les lignes d'exécution orphelines.** Quand la base tombe, la trace de sa panne ne peut pas
  s'y écrire — **la ligne reste ouverte et elle ment.** Deux subsistent.

**Deux questions de désaccord, réponses retenues au mandat :** une source défaillante après avoir publié
— **recalculer plutôt que supprimer, le dossier cumulatif se corrige et ne s'efface pas**; deux sources
qui se corroborent et tombent ensemble — la corroboration antérieure tient, **aucun nouveau bonus depuis
une source dégradée**, et le cumul est lui-même l'indice d'un incident local.

### Décision A — le coût d'exécution passe devant la norme de volume

**Le mandat rangeait la norme de volume en travail 2 et le coût comme un champ parmi d'autres du travail
1. L'ordre s'inverse.** Trois faits du 8 septembre l'imposent.

**Le quota est le seul mode de panne qui arrête tout d'un coup.** Une source qui tombe coûte une source;
un cache inaccessible coûte les sources qui téléchargent; **un quota épuisé coûte le cycle entier** — et
il l'a fait : le déclenchement de 14 h 17 UTC n'a même pas pu écrire son propre échec. **Une exécution
peut être rapide, légère, huit sources sur huit en succès, et avoir consommé le mois.**

**La norme de volume ne peut rien dire avant des mois**, le mandat le pose lui-même. C'est une raison de
commencer à accumuler, pas d'en faire le premier livrable. **La ventilation du coût est utilisable au
premier cycle**, et une décision l'attend : ne pas redescendre du palier de quota supérieur avant qu'un
cycle complet en régime ait été mesuré.

**Ventilation exigée : lignes lues par cycle, par source, et par chemin de résolution** — exact, préfixe,
sous-chaîne. C'est elle qui dira si le repli par sous-chaîne se borne ou se retire, **décision de
conception inscrite ici plutôt que prise dans le correctif d'index.**

**⚠️ Nommage tranché, parce que le piège est le motif du projet en miniature.** Le mandat demande de
conserver par exécution « le volume de lignes lues » — dans son contexte, **les lignes lues du fichier
source**, c'est-à-dire l'entrée. La mesure de coût porte le même nom et désigne **les lignes facturées
par la base**. Deux grandeurs sans rapport sous un seul nom, dans la même table. **`nb_lignes_source` et
`nb_lignes_lues_base`, jamais un `nb_lignes_lues` nu.**

**Réserve retenue : reporter la *lecture* de la norme de volume, pas son *accumulation*.** Le volume par
exécution s'écrit dès le premier cycle. La Partie 3 le dit des instruments dont le résultat n'est lisible
qu'après des mois : **c'est la raison de ne pas les repousser, pas de les repousser** — ce qu'ils
accumulent ne se rattrape pas en accélérant plus tard.

### Décision B — la réconciliation des lignes orphelines lit le journal de repli, pas la base

**Ce n'est pas un arbitrage neuf : c'est l'application du point 27.4** — *un compte qui décrit une
exécution ne se calcule jamais depuis la base que cette exécution écrit.*

Les lignes restées `en_cours` le sont **parce que la base était injoignable au moment d'écrire l'échec**.
**La base est donc, par construction, le seul témoin qui ne sait rien.** Un mécanisme qui reconstruit la
vérité depuis `source_run_logs` conclurait que le run tourne encore. Le déclenchement de 14 h 17 UTC le
prouve : ses deux lignes n'existent que dans `/var/lib/falkye/journal-repli.jsonl`.

**Conséquence d'architecture : `falkye/exploitation.py` passe de filet de sécurité à source de vérité
pour la réconciliation.** À trancher **avant** d'écrire la taxonomie des états — la frontière entre « en
cours », « défaillante » et « échec technique » dépend de qui a le droit de la dire.

Quatre conséquences retenues :

1. **Le format du journal de repli devient un contrat**, pas un dépotoir de dernier recours : numéro de
   version dans chaque ligne, et une ligne illisible **se saute, se compte et se signale — jamais
   n'interrompt la réconciliation.** Une réconciliation que son propre fichier d'entrée peut tuer est
   inutile le jour où on en a besoin.
2. **Elle tourne au début du cycle suivant**, comme `reconcilier_livraisons` — même place, même raison :
   c'est le premier moment où la base répond à nouveau.
3. **Marquer les lignes traitées, jamais faire tourner le fichier.** Il est le seul témoin des pannes où
   la base était injoignable : **une réconciliation qui le consomme en le détruisant supprime la preuve au
   moment où elle s'en sert.** La rotation par âge ou par taille reste possible **comme geste
   d'exploitation séparé, jamais comme effet de bord de la lecture.** La réconciliation doit être
   relançable sans perte si elle échoue à mi-parcours.
4. **Un fichier vide et un fichier introuvable ne produisent pas le même résultat.** Le premier dit « rien
   à réconcilier », le second dit « je ne sais pas ». Sans cette distinction, la réconciliation devient
   elle-même un cycle qui réussit à vide.

### ⚠️ Ce que le travail 1bis a découvert — les trois journaux d'exécution sont dans deux bases

**La phase 0 avait un angle mort qu'elle ne pouvait pas voir : elle précède le découpage des bases du
6 septembre.** Les trois journaux d'exécution ne sont pas seulement sans lien entre eux.

| Journal | Base | Facturée |
|---|---|---|
| `SourceRunLog` | produit, distante | **oui** |
| `DiffRunHistorique` | miroirs, fichier local | non |
| `DiffQuarantaine` | miroirs, fichier local | non |

**Trois conséquences structurelles, pas des détails d'implémentation.**

1. **L'identifiant partagé ne peut pas être une clé étrangère.** Aucune contrainte ne traverse deux bases,
   aucune requête SQL ne joint les trois tables. **Le rapprochement se fait dans le code, sur une valeur
   opaque, et l'absence de correspondance est un état normal** — jamais une anomalie à signaler.
2. **Il est porté par une variable de contexte.** `executer_diff` est appelé depuis `detect()`; le faire
   descendre par la signature l'ajouterait à l'interface des treize sources qui ne font aucun diff. **Le
   prix est écrit dans le module au lieu d'être tu** — un état ambiant est invisible à la lecture d'une
   signature. **Hors exécution, l'identifiant vaut `None`, jamais une valeur fabriquée : un lien faux se
   lit comme vérifié.**
3. **La migration tourne sur l'hôte, jamais depuis un conteneur de développement.** Quatre colonnes visent
   la base distante, deux le fichier miroir — que le conteneur ne voit pas. **La lancer d'ailleurs les
   poserait dans un fichier vide.**

### État

- ✅ Phase 0 rapportée.
- ✅ **Décisions A et B prises avant le code**, 8 septembre — elles modifient l'ordre d'attaque et le
  nommage des champs.
- ✅ **Travail 1bis livré** — le critère d'acceptation passe : une source en quarantaine ne s'enregistre
  plus comme un succès. Testé de bout en bout **avec le vrai `executer_diff`**, parce qu'un faux qui
  écrirait la trace lui-même testerait le test. 686 tests.
- ✅ **Instrument de coût livré** (PR #8). Le pilote libSQL n'expose pas `rows_read` : **les invocations
  par chemin sont comptées exactement, le coût en est dérivé** depuis une table de prix mesurée par le
  protocole Hrana. **Deux nombres jamais confondus — un compte exact et une dérivation.** La table porte
  sa provenance (date, méthode, population sans NEQ, liste d'index), et **toute pose ou tout retrait
  d'index la périme** : le rapport suspend alors la dérivation et n'affiche que les comptes, sortie 3.
  Un avertissement permanent rappelle que **le compteur de l'hébergeur est la mesure** et que la
  dérivation se valide contre lui avant tout changement de palier.
- ✅ **Réconciliation depuis le journal de repli livrée**, avec les quatre règles. *Cas relevé au passage :
  le format 1 n'avait pas prévu sa propre relecture — ses lignes n'ont pas d'identifiant, et les deux qui
  comptent sont de ce format. Identité dérivée de l'empreinte du contenu, stable parce que ces lignes
  sont ajoutées en fin de fichier et jamais réécrites. **Coût assumé et écrit dans le module** : deux
  lignes rigoureusement identiques seraient prises pour une seule. **Perdre le doublon d'une trace vaut
  mieux que la reprendre en boucle.*** La cause du repli voyage avec la ligne rapatriée — sans elle, une
  ligne rapatriée serait indiscernable d'une ligne écrite normalement, **or « la base était muette à ce
  moment-là » est précisément l'information.**
- ⬜ **Refermer les deux lignes orphelines** — le rapatriement est fait, la fermeture attend le statut
  `interrompue`.
- ⬜ **Migration à dix colonnes, sur l'hôte**, après déploiement.
- ⬜ Les autres travaux du mandat, **réordonnés : l'instrument de coût d'abord**.
- ⬜ **Le rapport de vérification macro par source** — cadence, saisonnalité, norme calculée, état de
  santé et sa justification. *Livrable 4 du mandat, non entamé.*
- ⚠️ **Décision qui attend Alexandre, et qui n'est listée nulle part ailleurs : les seuils d'alerte de
  dérive**, avec leur justification — *livrable 6 du mandat, « à valider avec Alexandre, et non une
  constante enfouie ».*
- ⚠️ **Ambiguïté à trancher dans la taxonomie, et elle traverse tout le corpus** : la quarantaine figure
  à la fois comme **issue d'exécution** et comme **état de santé** — dans le mandat du chantier 2, et
  dans le même paragraphe des spécifications, section 5.5. Le glossaire interdit désormais de les
  confondre. **Décider laquelle des deux elle est, et corriger les deux documents ensemble.**
- ⚠️ **Trois comptes différents pour les états de santé.** Les spécifications en listent six « au moins »
  puis en ajoutent deux; le mandat en détaille sept; cette fiche en annonce sept. **Un registre
  extensible ne dispense pas de savoir combien il en contient aujourd'hui.**

---

## Chantiers 3 et 4 — Identité d'entreprise et confiance d'appariement *(failles B, C, D)*

### ⚠️ Une seconde dimension à prévoir dès la conception : la famille d'entités

**Le territoire ne suffit pas à désigner le pivot d'une identité — la famille de l'entité entre aussi.**
Le SEAO le démontre dans une seule source : l'identifiant de l'organisme acheteur est présent à **100 %**,
celui du fournisseur n'est jamais un NEQ. **56 % d'ambiguïté sur les entreprises, zéro sur les
organismes publics** *(mesuré sur 4 704 avis, spéc. §7.2)*.

**Direction retenue, et elle simplifie plutôt qu'elle n'ajoute.** Plutôt que de laisser le SEAO porter
deux natures — Piste pour les organismes, Réflexion pour les entreprises —, **s'appuyer sur un registre
officiel des entités publiques** qui fournirait l'identifiant unique comme le REQ fournit le NEQ. Le SEAO
redevient alors une source ordinaire, Réflexion pour les deux familles, et **la règle devient une
propriété du type d'entité plutôt que de la source** : entité publique → registre des organismes
publics; entité privée → REQ.

**C'est l'application directe de la charte, section 4** — le moteur ne présume jamais la nature de
l'entité qu'il suit. L'entité déclare sa famille, la famille désigne son registre pivot.

**Ce que ça change ici, et presque rien.** Le chantier crée déjà la clé interne et des identifiants
externes rattachés **avec leur territoire**; il suffit que la **famille** s'ajoute à côté du territoire.
*Le faire maintenant coûte presque rien; le faire après, c'est migrer deux fois la même clé — exactement
la raison pour laquelle 3 et 4 sont inséparables.*

**Ça consolide aussi la séparation public / privé du 6 septembre** *(spéc. §7.2)*. Elle reposait sur les
seuils, le délai, le cycle de vente et l'identifiant; **l'identifiant y devient le premier argument**.
Ce ne sont plus deux vues d'une même population, ce sont **deux populations avec chacune son pivot** —
donc classables et dédoublonnables séparément. *Ça répond en partie à la réserve que les spécifications
posaient elles-mêmes : le tableau public serait un déversoir tant que la règle des seuils n'est pas
écrite. Une population mal ancrée l'est forcément.*

**Trois décisions au registre avant de concevoir la clé : D27** trouver le registre, **D28** la règle de
classement d'une entité avec sa réponse par défaut, **D29** lequel des deux identifiants fait foi pour la
vérification du statut légal quand une entité porte les deux.

**À livrer ensemble.** Le score du chantier 4 est **porté par l'identité** que crée le chantier 3, et
**les séparer voudrait dire migrer deux fois la même clé.**

**Cadrage, à ne pas perdre.** Le NEQ reste la source Piste du Québec et le meilleur niveau de
vérification. **Ce qui change, c'est que la clé du moteur cesse d'être un identifiant de territoire** —
et une identité qui porte un NEQ doit rester strictement aussi bien servie qu'aujourd'hui, **critère de
non-régression, pas effet secondaire acceptable**.

**L'identité *(chantier 3)*.** Une **identité interne**, distincte de tout identifiant externe, comme clé
du dossier cumulatif, de la corroboration et de la déduplication. Une table d'**identifiants externes**
rattachés, chacun avec son territoire, sa source et sa date — **zéro, un ou plusieurs, et une identité
sans identifiant externe est valide de plein droit, pas un cas dégradé**. Un **niveau de vérification par
couple identité × territoire**. Et le traitement des prospects non vérifiables : exclusion ou confiance
plafonnée, **implémenté dans le score plutôt que dans un avertissement affiché**.

**La confiance d'appariement *(chantier 4)*.** Un score **hérité du maillon le plus faible** de
l'historique de fusion, qui **plafonne** au lieu de s'additionner — une identité faible ne peut pas
produire une notification à confiance élevée. **L'adresse comme axe principal, le nom en
corroborateur.** Une **table d'apprentissage raison sociale ↔ nom d'enseigne ↔ adresse**, alimentée par
les deux sources qui livrent les trois — **elle s'enrichit avec le temps, donc la construire tard c'est
repartir d'une table vide alors que les mauvais appariements se sont accumulés**. Et une **règle de
non-promotion** : sous un seuil, le signal reste une réflexion et ne déclenche rien, quelle que soit sa
force.

**Pourquoi c'est urgent, chiffré.** 56 % d'ambiguïté sur une source, 65 % sur la base complète, **0,8 %
d'entreprises vérifiées au bout**. Le premier envoi réel est parti vide : **953 signaux correspondaient
au profil, aucun ne portait sur une entreprise que le produit accepte de nommer.**

**Deux questions de désaccord.** *Identité :* deux identifiants qui se contredisent — l'exclusion
porte-t-elle sur toute l'identité ou sur le seul territoire? *Appariement :* **deux appariements
concurrents à score comparable**, cas courant en centre commercial et en édifice à bureaux — **le défaut
ne doit jamais être « prendre le meilleur score »**.

**Acceptation.** Ajouter un identifiant d'un territoire fictif ne doit toucher **aucune ligne du moteur
de croisement**, et un test de non-régression confirme qu'une entreprise québécoise produit exactement
les mêmes résultats qu'avant. *Les vingt candidats de fusion en attente sont le jeu de test naturel — à
examiner après, pas avant.*

---

## Chantier 5 — Placement des sources et fonctionnalités *(faille A)*

**À construire.** Un attribut sur chaque source — **couverture** ou **enrichissement** — dont **la règle
de placement découle**, au lieu d'être appliquée à la main. Le reclassement des cinq sources vérifiées, à
valider avant application. Et une **vérification automatique** : pour chaque combinaison palier × sphère
offerte, au moins une source de couverture — **une combinaison qui échoue est un défaut, pas une
particularité**.

**Question de désaccord.** Une source de couverture pour une sphère et d'enrichissement pour une autre —
d'où la règle : **l'attribut est par couple source × sphère, jamais par source seule.**

**Le même attribut s'applique aux fonctionnalités** : ce qui corrige l'**exactitude** est de la
couverture, ce qui ajoute de la **profondeur** est de l'enrichissement.

**Quatre corrections décidées, à implémenter ici.** Le **filtre par taille** passe au palier d'entrée —
même classe que les curseurs de sensibilité, déjà présents partout. La **rétroaction** existe dans tous
les paliers : elle alimente le taux de rejet, **seule boucle de correction du moteur, et la retirer d'un
palier le dégrade pour tout le monde**. Le **bonus de corroboration inter-provinciale** passe en
veilleuse, sans quitter le registre. **Et le palier d'entrée dispose d'un tableau de bord : la frontière
porte sur consulter et agir, jamais sur voir.**

**Vérification à exécuter sur toute la grille** : passer chaque fonctionnalité au test exactitude /
profondeur, et **rapporter celles dont le placement ne s'explique que par l'habitude**.

---

## Chantier 6 — Registre légal et page de crédits *(faille K)*

**À construire.** Étendre le registre avec la case obligatoire d'activation *(voir `falkye-cadre-legal.md`)* :
canal exact de la donnée; variante de licence **lue sur la fiche du jeu précis, jamais déduite du
portail** — les variantes non commerciales sont bloquantes; clause visant l'indexation ou l'automatisation;
statut du fichier d'exclusion des robots; obligation d'attribution; **date de vérification et échéance de
revalidation**.

**Deux exigences au-delà de la case.**

**Une échéance événementielle en plus de l'échéance par date.** Certaines autorisations deviennent
requises à un événement précis — la licence du registre est **à autoriser dès le premier engagement
commercial**. **Sans ce type de déclencheur, la décision reportée se perd.**

**Passer au gabarit les sources héritées, pas seulement les nouvelles** — le registre n'y était jamais
passé, **c'est ce qui a laissé sa licence non vérifiée** *(journal, cas 17)*. Trois autres sources
québécoises actives sont dans le même cas.

**Un état `bloquée` distinct de `inactive`** : une source peut être techniquement prête et légalement
interdite. Et **la page de crédits**, hors du produit, alimentée automatiquement par les sources dont le
registre indique une obligation d'attribution.

**Question de désaccord.** Une source qui passe à `bloquée` alors que ses données sont déjà dans des
dossiers cumulatifs : purger, geler, ou conserver? **La charte promet qu'une source problématique se
désactive sans restructuration — vérifier que c'est vrai en pratique.**

---

## Chantier 7 — Canal hors profil et sphères dérivées *(failles G et J)*

**À construire.** Le canal « hors profil déclaré » **pour tous les paliers**, en vue distincte au tableau
de bord — **jamais mêlé aux opportunités du profil, jamais poussé par courriel ou webhook par défaut**.
Un **type de sphère** au registre : directe, dérivée, sans couverture. Et pour les dérivées, **la règle
de dérivation au registre plutôt que dans un document**.

*La visibilité des sphères sans couverture appartient au chantier 15, qui décide de ce qui est offert.*

**Question de désaccord.** Une sphère dérivée et une directe produisant le même signal pour le même
prospect — **deux notifications, ou une consolidée?**

---

## Chantier 8 — Cadence de notification configurable par palier

**À construire.** Un **registre de cadences extensible**, pas une énumération figée. Une **matrice
palier × cadences autorisées** — point de départ à valider : le palier d'entrée accède aux cadences
espacées, les supérieurs à l'ensemble **puisque leur tableau de bord sert de canal de rechange**. Et
**réutiliser le résumé périodique existant** comme mécanisme de regroupement, plutôt que d'ajouter un
second système d'agrégation.

**Trois règles à ne pas perdre.** **Cadence et sensibilité restent deux axes indépendants** — la
sensibilité dit *ce qui mérite d'être signalé*, la cadence *quand le lot part*, et les confondre
reproduirait l'erreur que la charte interdit sur les scores. **Défaut : notification active** — un palier
supérieur silencieux par défaut **retirerait au client le différenciateur qu'il paie le plus cher**. Et
**cadence par profil, pas seulement par compte** : un cabinet voudra du temps réel sur une sphère et de
l'hebdomadaire sur une autre.

**Question de désaccord.** Un prospect correspondant à **deux profils du même compte ayant des cadences
différentes** — doublon, cadence la plus rapide, ou regroupement? Et lors d'une rétrogradation vers un
palier n'autorisant pas la cadence configurée, quelle cadence de repli, et l'utilisateur en est-il
informé?

---

## Chantier 9 — Densité de signal par sphère et par territoire

**À construire.**

- Une mesure calculée sur **l'historique réel**, par sphère × territoire × palier : volume, répartition
  par niveau de pertinence, fraîcheur médiane.
- Une **exposition honnête à la configuration** : quand un besoin tombe dans une combinaison à faible
  densité, **le dire avant que la personne paie**, en termes de résultats attendus et sans nommer de
  source.
- **L'alimentation du test du chantier 5** : c'est cette mesure qui rend le classement
  couverture/enrichissement calculable plutôt que subjectif.
- Un usage interne comme **file de priorité de recherche de sources** — les combinaisons à faible densité
  et forte demande deviennent le prochain mandat, **au lieu d'être découvertes par des annulations**.

**Question de désaccord.** Comment se calcule la densité pour un profil couvrant **plusieurs sphères,
dont une dense et une vide**? **La moyenne masquerait exactement le problème qu'on cherche à exposer.**

---

## Chantiers 10 et 16 — Validation réelle, échéances et réévaluation *(failles H et I)*

**À livrer ensemble.** Les deux reposent sur le même mécanisme : **l'ordonnanceur unique d'échéances du
point 27.2**. Le chantier 16 dit lui-même « au même mécanisme que les échéances de décision et de
vérification légale » — le garder séparé produirait une minuterie de plus, ce que le 27.2 interdit.

### L'état de validation réelle *(chantier 10)*

- Un troisième état dans la grille et le registre : **construit mais non validé en réel**, distinct du ✓
  et du tiret.
- **Rien ne passe au ✓ plein avant d'avoir tourné contre le vrai service** plutôt que contre un mock.
  **Ça ne bloque pas le développement, ça bloque la promesse commerciale.**
- Application immédiate aux intégrations CRM, au paiement, à l'assistance de niveau 2, à la source
  d'offres d'emploi payante et au géocodage.

**Intégration CRM — décidé : connexion par autorisation déléguée**, le modèle par jeton collé est écarté.
**La connexion d'un CRM est un réglage de sortie dans la configuration du compte, jamais une opération du
portail** — celui-ci sert au paiement et à l'accès aux sources payantes, qui sont des entrées. Le
connecteur est inchangé; ce qui s'ajoute est une couche d'autorisation. **À traiter avant que la
connexion existe en production** — après, migrer voudrait dire redemander à chaque client de se
reconnecter. *Étape de calendrier à ne pas découvrir tard : l'un des deux CRM impose une révision de
l'application dès qu'un client extérieur doit brancher son compte, même hors marketplace.*

### Les échéances *(chantiers 10 et 16)*

- Toute entrée **« décision jamais tranchée »** porte une échéance et réapparaît à cette date.
  **Trancher inclut « non, et voici pourquoi ».**
- Une **échéance de revalidation sur les trois avantages défendables**, au même mécanisme.
- Les **trois déclencheurs de revue immédiate** de la charte, consignés comme critères de veille.
- **Si un avantage tombe, l'élément correspondant du matériel de vente passe au même état que les
  fonctionnalités non validées** — retiré de la promesse, pas du produit.

---

## Chantiers 11 et 19 — Le journal de diagnostic : ce qu'on y écrit, ce qu'on en lit

**À livrer ensemble.** Même table, écriture d'un côté et lecture de l'autre. Le journal de diagnostic existe déjà :
**l'étendre, jamais créer un mécanisme parallèle.**

### Ce qu'on y écrit *(chantier 11)*

- Chaque diagnostic enrichit le **registre sphère ↔ signal de façon permanente** : la correspondance
  trouvée pour un client sert à tous les suivants, **pour que le coût marginal décroisse au lieu de
  rester constant**.
- Consigner aussi les **diagnostics négatifs** — cherché, rien trouvé, à telle date, voici où — pour ne
  pas refaire deux fois la même recherche infructueuse.
- **Réserve à maintenir dans le produit :** la partie irréductible du coût — la vraie recherche pour une
  combinaison inédite — appartient au palier supérieur **comme service**, pas comme fonctionnalité
  incluse. **Ne jamais laisser l'interface promettre un diagnostic instantané sur une spécialité jamais
  vue.**

### Ce qu'on en lit *(chantier 19)*

Le journal de diagnostic collecte déjà les descriptions mal classées, les « qui » non résolus et les sources
manquantes. **Il est traité comme une file de correctifs alors que c'est la meilleure feuille de route
produit disponible** — ce que de vrais utilisateurs ont demandé et que le produit n'a pas su servir.

- Une **agrégation par motif** plutôt qu'une liste chronologique : quels types de service reviennent,
  quelles sphères manquent, quels territoires sont demandés.
- Un **croisement avec la densité** : **forte demande et faible densité est la définition exacte du
  prochain mandat de recherche de sources.** C'est ce qui remplace la découverte par annulation
  d'abonnement.
- Une **lecture à échéance**, sur l'ordonnanceur unique du point 27.2, plutôt qu'une consultation quand
  on y pense.

**Question de désaccord.** Deux diagnostics successifs attribuant des sphères différentes au même
service — le registre reflète-t-il les deux, arbitre-t-il, ou marque-t-il le désaccord pour révision?

---

## Chantier 12 — Inventaire champ ↔ sphère à rebours

**Facette du cerveau : l'association** — partir d'un besoin et chercher, dans ce qu'on possède déjà, ce qui pourrait le servir. *Voir `FALKYE-000-PAR-OU-COMMENCER.md`.*

**Peut se mener en parallèle du socle** : aucune table centrale, donc aucun risque de refonte. **Le seul
chantier qui peut avancer pendant que le reste se répare.**

**Constat.** Toute la recherche de sources a été menée **source-d'abord** — on trouve une source, on
demande quelles sphères elle sert. **La question n'a jamais été reposée à rebours sur les sources déjà
actives, ni au niveau du champ.** Les spécifications posent pourtant le bon principe — capter largement
une fois, filtrer par lentille ensuite — **mais il n'a été appliqué que dans un sens**.

**Preuve que le diagnostic « sans source » est probablement faux pour trois des quatre sphères
orphelines.** *L'assurance* est déclarée sans source alors que **six champs déjà captés portent son
déclencheur** : ce n'est pas « aucune source », c'est **« aucune source seule »**, la thèse même du
produit *(journal, cas 6)*. *L'analytique d'affaires* est portée par le titre de poste — problème de
mots-clés, pas de source. *Le service à la clientèle* attend une règle jamais traitée comme un mécanisme.
*La gestion documentaire* reste honnêtement mince : **ne pas forcer.**

**À construire.**

1. **L'inventaire de champs par source active** — approuvé mais jamais livré. **C'est le préalable** :
   sans lui, le chantier reste au niveau de la source et ne trouve rien.
2. **Le diagnostic à rebours, au niveau du champ** : partir de la sphère pour parcourir les champs déjà
   en main, plutôt que du service pour chercher une source.
3. **Assistance IA en proposition seulement, mécanisme existant retourné.** Le même composant qui fait
   description → sphères fait inventaire → sphères candidates. **Aucun nouveau mécanisme**, et les
   garde-fous s'appliquent tels quels.
4. **Normaliser le texte libre déjà capté** — sujets déclarés, titres de poste, secteur, dont l'échec
   d'agrégation est documenté : **211 valeurs distinctes sur 311 notifications réelles**.
5. **Règle de réfutation obligatoire — la partie non négociable.** Une IA à qui on demande quel champ
   pourrait servir une sphère produira toujours quelque chose de plausible, ce que la charte interdit.
   **Aucun lien n'est activé sur la seule foi d'une proposition** : chaque lien se teste contre
   l'historique réel. **S'il ne discrimine pas, il est rejeté et journalisé comme réfuté**, pas laissé en
   attente.
6. **Retombée sur le chantier 7.** Les sphères qui survivent deviennent dérivées, les autres sans
   couverture — **dans les deux cas on sort de l'état où la documentation dit qu'une solution existe et
   où le moteur n'en sait rien.**

**Question de désaccord.** Un même champ proposé pour deux sphères, l'une directe et l'autre dérivée —
compte-t-il deux fois dans la corroboration? **Non : un champ ne peut pas se corroborer lui-même.**

**Réserve à documenter.** Ce chantier **ne créera pas de signal là où il n'y en a pas** — il révèle des
signaux captés mais mal attribués. **Ne jamais le présenter comme une méthode qui garantit de couvrir
toute nouvelle sphère.**

---

## Chantier 13 — Précision perçue : instrumenter le faux positif *(charte, section 16)*

**Il corrige les cinq facettes du cerveau** : seule boucle qui confronte le moteur au réel plutôt qu'à des hypothèses. *Voir `FALKYE-000-PAR-OU-COMMENCER.md`.*

**Constat.** La charte pose que le faux positif coûte structurellement plus cher que le faux négatif pour
ce produit et ce prix. **Aucun instrument ne mesure ce ratio.** Le mécanisme existe à moitié — le statut
« Pas pertinent » sert déjà de rétroaction; **ce qui manque, c'est de l'agréger**.

**À construire.**

- Un **taux de rejet par profil, sphère et source**, calculé sur les statuts déjà collectés, avec un
  **seuil d'alerte interne** : au-delà, la combinaison est suspecte — sphère mal câblée, source bruitée,
  ou sensibilité trop basse.
- **Distinguer rejet et non-conversion.** *Pas pertinent* = n'aurait pas dû être montré; *joint, sans
  suite* = bon prospect, vente non faite. **Le second ne compte jamais comme une erreur du moteur.**
- **Trois dimensions de statut séparées, jamais fusionnées** — qualification, pipeline, cycle de vie.
  **Le taux se calcule sur la première seule** : toute contamination par la deuxième ferait baisser la
  précision mesurée à chaque vente perdue, et **le moteur se corrigerait sur du bruit commercial**.
- **Un motif de rejet facultatif, en un geste**, dans un catalogue fermé. **C'est le motif, pas le rejet,
  qui indique quoi corriger** — mais jamais obligatoire, **un motif exigé fait chuter le taux de
  rétroaction, donc la donnée qu'on cherche**. Et *« déjà client »* ne compte jamais comme une erreur.
- **Usage direct au chantier 12** : un lien champ → sphère à fort taux de rejet est **réfuté par les
  données**, ce qui rend le garde-fou opérationnel plutôt que théorique.

**Question de désaccord.** Un prospect rejeté par un utilisateur et retenu par un autre, sur la même
sphère — le rejet porte-t-il sur le prospect, le profil, ou la sphère? **Par défaut : le profil. Le
moteur n'apprend jamais d'un utilisateur pour les autres sans confirmation.**

---

## Chantier 14 — Comportement en l'absence de signal *(charte, section 17)*

**Constat.** Le mode de défaillance principal est le silence, et rien ne le traite. **Un abonné qui ne
reçoit rien pendant trois semaines ne peut pas distinguer un territoire calme, un profil mal configuré et
un produit brisé.**

**À construire.**

- Un **rythme normal par profil**, appris sur son propre historique — **un profil de niche a un rythme
  lent qui est normal pour lui**.
- Une distinction entre **silence attendu et silence anormal**, avec causes distinguables.
- Une **annonce à la configuration** quand la combinaison est mince, en termes de résultats attendus et
  **sans jamais nommer de source**.
- Une **intervention au-delà d'un seuil** : ajustement de profil, élargissement, ou dire que la sphère est
  mince. **Un message honnête vaut mieux que rien, et infiniment mieux qu'un faux prospect.**
- **Interdiction implémentée, pas seulement documentée :** aucun mécanisme ne peut abaisser un seuil pour
  rompre un silence.

**Ce que contient un message de silence — l'agrégat, jamais la liste.** Le décompte avec ses motifs —
« quarante-deux entreprises examinées, aucune n'a franchi le seuil » — a **le même effet rassurant que la
liste, sans aucun de ses risques**.

**Ne jamais nommer un dossier écarté**, pour trois raisons structurelles. L'utilisateur ne peut pas
évaluer un rejet mieux que le moteur, mais il essaiera. **S'il contacte un écarté, le produit vient de
lui enseigner que son filtrage vaut moins que son jugement.** Et montrer du volume rejeté pour rompre un
silence est ce que la charte interdit — **l'étiquette « rejeté » n'y change rien**.

**L'agrégat est actionnable, contrairement à la liste** : le motif dominant indique quoi proposer.
« Hors sphère » → profil à revoir. « Identité incertaine » → problème de notre côté. **Le silence cesse
d'être un mur et devient un diagnostic.**

**Restriction sur le motif « hors territoire ».** Il ne s'affiche que si l'utilisateur **n'a pas configuré
lui-même** son périmètre — sinon c'est contester une décision qu'il a prise délibérément, **et ça se lit
comme un reproche**.

**Exception encadrée — les dossiers « en observation ».** Un dossier écarté **de peu** et sans autre
réserve peut être nommé, sous quatre conditions : uniquement juste sous le seuil, **plafond de deux ou
trois**, **jamais sous l'étiquette « rejeté »**, et **exclusion absolue** pour tout dossier écarté sur
incertitude d'identité, échec de vérification ou territoire.

**Question de désaccord.** Pour un compte à **profils multiples** dont un seul est silencieux, l'alerte
porte-t-elle sur le profil ou le compte? Et un silence causé par une source en quarantaine doit-il être
présenté comme anormal, **sachant qu'on ne peut pas nommer la source en cause**?

---

## Chantier 15 — Retenue : séparer le registre interne de l'offre *(charte, section 18)*

**Constat.** Rien ne distingue ce que le registre contient de ce que le produit offre. **Une sphère sans
couverture est sélectionnable comme les autres.**

**À construire.**

- Un attribut **offert / non offert** sur les sphères, territoires et combinaisons, distinct du fait
  d'exister au registre. **Le registre garde la trace, l'offre ne présente que ce qui est servi.**
- Une **opération de retrait journalisée** — retirer du catalogue sans supprimer du registre, avec motif
  et date. *Les précédents existent, mais ont été traités à la main.*
- Le traitement des **utilisateurs déjà abonnés** à une combinaison retirée : ils gardent leur
  configuration et sont informés. **À trancher explicitement, pas à découvrir.**
- Une sphère **sans couverture** — type déclaré au chantier 7 — est **visible comme telle à la
  configuration**, jamais offerte comme si elle fonctionnait. **Même mécanisme : le registre garde,
  l'offre trie.**

**Question de désaccord.** Un profil combinant une sphère offerte et une sphère retirée — reste-t-il
valide en mode partiel, ou demande-t-il une reconfiguration?

---

# Partie 2bis — Chantiers offensifs

Les précédents réparent; les suivants exploitent des forces déjà présentes mais laissées à l'état de
note. Tous sont additifs et à coût constant — mais **leur valeur dépend de l'historique accumulé**, donc
les commencer tôt fait mûrir l'actif plus vite, même si le résultat n'est lisible que plus tard.

---

## Chantier 17 — Signal par absence et trajectoire, en première classe *(charte, section 21)*

**Facette du cerveau : la mémoire** — avoir gardé, avant de lire. *Voir `FALKYE-000-PAR-OU-COMMENCER.md`.*

**Constat.** Les deux capacités que personne ne peut reproduire sans mémoire sont mentionnées une fois
chacune, avec la note qu'elles sont généralisables, **et n'ont aucun mécanisme**.

**À construire.**

- **Le signal par absence comme règle exprimable**, pas comme cas particulier codé pour un persona. Il
  faut pouvoir déclarer, par sphère : « présence de A et B, **absence** de C et D sur une fenêtre
  donnée ». La généralisation est déjà demandée — c'est le mécanisme qui manque.
- **La trajectoire comme dimension calculée du dossier** : nombre de signaux sur une fenêtre glissante,
  force croissante ou décroissante, écart depuis le précédent. **Trois signaux en deux mois et trois en
  deux ans doivent produire deux résultats différents.**
- **La conservation nécessaire à l'expression d'une absence.** Une absence ne se déduit que d'un ensemble
  connu de ce qui aurait dû apparaître : ce chantier dépend de la conservation d'état, **et échouera
  silencieusement sans elle**.

**Question de désaccord.** Une absence due à une **source en quarantaine ou défaillante** plutôt qu'à un
fait réel. **Une absence causée par une panne ne doit jamais produire un signal positif** — c'est le
risque propre à cette capacité, et il n'existe pas pour les signaux de présence.

**Réserve honnête.** Ce chantier a besoin de plusieurs mois d'historique pour dire quelque chose. **Le
construire tôt sert à commencer à accumuler, pas à obtenir un résultat immédiat.**

---

## Chantier 18 — Normalisation par la base et mesures de taille réelles *(charte, section 21)*

**Constat.** Sans base de comparaison, **tout signal de volume favorise mécaniquement les grandes
entreprises** — exactement celles qui ne sont pas la clientèle visée. Le principe est appliqué
ponctuellement, jamais systématiquement.

**À construire.**

- Une **taille à trois niveaux de fiabilité, jamais fusionnés en un chiffre** : mesurée, déclarée,
  estimée. Chaque niveau porte sa provenance et sa date.
- Une **normalisation systématique des signaux de volume** par taille et secteur. **Cinq embauches chez
  une entreprise de dix personnes est un événement; chez une de cinq cents, c'est du bruit.**
- L'usage du **miroir complet comme dénominateur** : il permet de calculer ce qu'est un rythme normal
  pour un secteur et une taille, au lieu de le supposer.

**Question de désaccord.** Taille mesurée et taille estimée qui se contredisent — une confirmation
officielle d'il y a deux ans contre des signaux d'embauche récents suggérant plus petit. **La plus
récente l'emporte-t-elle, ou la mieux mesurée?**

---

## Chantier 20 — Servir le public institutionnel, déjà à moitié construit

**Constat.** La charte nomme ce public depuis le début, un persona existe, et **les tableaux de bord
agrégés par territoire sont déjà construits**. Mais le produit entier est conçu autour du vendeur B2B, et
ce public reste traité comme un débouché secondaire.

**Ce qui le rend structurellement intéressant, à documenter pour que la décision soit consciente.** Un
organisme de développement économique **n'a rien à vendre au prospect détecté** — il veut savoir quelles
entreprises de son territoire grandissent, pour intervenir et justifier son impact. **La fragilité
assumée du modèle — rien n'empêche un utilisateur de contourner la plateforme une fois le prospect
connu — ne s'applique donc pas à lui.** Son budget est institutionnel, et il est aussi un canal vers ses
propres membres.

**Il utilise moins du produit, pas davantage** : ni amorces de contact, ni intégration CRM, ni pipeline
de statuts. **Une soustraction plus une vue agrégée, pas une seconde moitié à construire.**

**À construire — surtout du déblocage.**

- Lever la limite des tableaux agrégés : l'agrégation par secteur est cassée par la granularité du texte
  libre — **211 valeurs distinctes sur 311 notifications**. Le chantier 12 règle la normalisation; celui-ci
  en récolte le bénéfice.
- Corriger le trou documenté : les entreprises hors Québec tombent systématiquement en « non classé ».
- Vérifier que **suivre un territoire entier plutôt qu'un profil de vente** est exprimable dans
  l'architecture de profil actuelle, ou ce qui manque pour l'exprimer.

**Question de désaccord.** Un même compte portant un profil de vente et un profil de veille territoriale
— seuils, cadence et canal hors profil ont-ils le même sens pour les deux? **La réponse est probablement
non, et il vaut mieux le constater maintenant qu'après avoir vendu le premier abonnement
institutionnel.**

---

## Chantier 21 — Présentation de l'opportunité et narratif

**Facette du cerveau : le langage** — mettre en mots ce qui a été compris. *Voir `FALKYE-000-PAR-OU-COMMENCER.md`.*

*Mandat détaillé : `falkye-chantier-21-narratif.md`. **À exécuter après le chantier 13**, qui fournit sa
boucle de correction.*

**Constat.** Le corpus décrit en détail comment un signal entre et comment il est scoré, et dit peu sur
ce qui sort. **Le moteur de croisement est l'avantage défendable; le narratif est la seule forme sous
laquelle il parvient à l'utilisateur.**

**Les grandes lignes.**

- **Un seuil de publication explicite, distinct du curseur de sensibilité.** Le seuil dit ce qui est
  présentable, la sensibilité ce que cet utilisateur veut voir parmi le présentable — **les fusionner lui
  enlèverait la possibilité d'être plus sélectif que le défaut**.
- **Fraîcheur et trajectoire modulent le grade**, elles ne le remplacent pas. Un signal frais mais mal
  aligné ne devient pas AAA.
- **La structure de faits, pièce centrale.** Le narratif se calcule d'abord, se rédige ensuite. **Cette
  structure est la vérité; le texte n'en est qu'un rendu** — elle est conservée, ce qui permet de
  re-rendre sans recalculer et **de répondre à un utilisateur qui conteste**.
- **Un gabarit par croisement signal × sphère**, avec quatre contraintes dès le premier : aucun nom de
  source; l'amorce est une aide à la rédaction, jamais un message prêt à envoyer; **un gabarit qui
  accumule des noms d'entreprises sans contexte ressemble à une liste achetée** — contrainte de
  délivrabilité, pas d'esthétique; et l'incertitude se voit dans la formulation.
- **Formulation par modèle, optionnelle.** Il reçoit **uniquement la structure de faits**, avec un test
  de non-invention, un repli sur le gabarit, et **génération une seule fois puis stockage**.
- **Une passe unique de relecture de tous les libellés visibles.** *Pas cosmétique* : à contenu
  identique, **la formulation décide souvent seule entre un abonné qui reste et un abonné qui part.**

**⚠️ Contrainte de non-fermeture — l'interprétation reste ouverte.** Le produit sait **rattacher** des
signaux; **rien ne produit encore d'interprétation** — ce qu'ils veulent dire ensemble. **Rien n'est à
construire** : ça demande de vrais dossiers, et inventer des motifs d'avance reproduirait l'erreur
d'inventer des sphères. **La seule exigence est de ne fermer aucune porte** — cinq contraintes détaillées
au mandat, dont **une place vide réservée dans la présentation, qui existe et n'est pas remplie**.

**Question de désaccord.** Un signal ancien très fort et un signal récent faible — la fraîcheur porte-t-
elle sur le plus récent, le plus fort, ou l'ensemble?

---

## Chantier 22 — Calibration déclarée et durée de pertinence

**Facette du cerveau : la lecture** — extraire d'un signal ce qu'il dit vraiment. *Voir `FALKYE-000-PAR-OU-COMMENCER.md`.*

*Mandat détaillé : `falkye-chantier-22-calibration.md`.* **Précède les chantiers 4 et 6** — le moteur de
notation reflète fidèlement une entrée uniforme, donc le raffiner avant d'avoir appris à lire un signal
ne lui donnerait rien de plus à départager.

**Constat.** Aucune source ne s'active sans une règle qui distingue le vrai signal du bruit
administratif — **mais cette règle n'a aucune forme commune**, chacune étant codée à la main dans son
connecteur. On ne peut ni les comparer, ni les auditer, ni les tester côte à côte, **et la calibration de
chaque nouvelle source se réinvente à partir de rien**.

**À construire — un catalogue de motifs déclarés au registre** plutôt que du code sur mesure : apparition,
changement de valeur au-delà d'un seuil, franchissement de palier, répétition sur une fenêtre, absence
attendue. Chaque règle déclare **son motif, le champ visé, son seuil, le tier de confiance produit, et ce
qu'elle exclut comme bruit**. **Ajouter une source devient une déclaration, pas une réécriture.**

*Livrable de migration : reprendre les règles existantes sous cette forme et **rapporter celles qui n'y
entrent pas — un motif manquant au catalogue est une information utile, pas un échec**.*

**Une durée de pertinence par couple type de signal × sphère**, avec valeur par défaut. *Un nouvel
établissement intéresse un entrepreneur en entretien deux ou trois mois; un dépôt de marque intéresse un
conseiller en franchisage près d'un an.* Elle module la fraîcheur du chantier 21 et détermine la
profondeur d'antériorité du chantier 25.

**Décision à respecter sans exception : active dès le palier d'entrée, identique partout, non
configurable.** Ce n'est pas une fonctionnalité, **c'est une correction de justesse** — un fait sur le
signal, pas une préférence. Et **un utilisateur n'a aucun moyen de savoir combien de temps un signal
reste pertinent dans sa sphère** : la lui faire régler serait lui confier un travail qu'il ferait mal.

**Question de désaccord.** Un signal servant **deux sphères aux durées différentes**. **La durée est
portée par le couple, jamais par le signal seul** — le même fait peut donc être frais pour un utilisateur
et périmé pour un autre.

---

## Chantier 23 — Cycle de vie d'une opportunité déjà livrée

**Constat.** Rien ne dit ce qui arrive quand un dossier déjà présenté reçoit un nouveau signal. **La
double notification sur la même entreprise est un des irritants les plus faciles à créer sans le
vouloir.**

**À construire.** **Mise à jour silencieuse par défaut** — le grade se met à jour, la structure
s'enrichit, rien ne part. **Renotification uniquement au franchissement d'un palier vers le haut, et une
seule fois par palier.** Le **narratif régénéré doit dire ce qui a changé**, pas répéter le narratif
initial. Et **un prospect marqué « pas pertinent » ne remonte pas**, sauf passage au palier le plus haut,
avec mention du rejet antérieur — **le rejet est un jugement de l'utilisateur, et le contredire trop
souvent érode la confiance plus que ça ne rend service.**

**Question de désaccord.** Un dossier franchissant deux paliers d'un coup, ou montant puis redescendant
puis remontant au même palier — **la règle « une seule fois par palier » doit tenir dans les deux cas**.

**Tests exigés.** Un nouveau signal sans franchissement ne produit **aucune** notification. Un
franchissement en produit **exactement une**, et le narratif régénéré dit ce qui a changé. Deux paliers
d'un coup, puis descente et remontée : **jamais de notification en double pour le même palier**. Un
prospect rejeté ne remonte pas, **sauf passage au palier le plus haut, et alors avec mention du rejet
antérieur**.

---

## Chantier 24 — Péremption et archivage

**À construire.** **Archivage après une période configurable, un mois par défaut** — l'opportunité sort
du tableau de bord principal et **reste consultable**. **Alerte dix jours avant, groupée** : une seule
pour toutes celles arrivant à échéance, jamais une par prospect. Et **remontée d'archive** — une
opportunité archivée qui reçoit un signal fort revient comme nouvelle, avec mention qu'un dossier
existait. *C'est une capacité qu'un outil de recherche ne peut pas offrir.*

**⚠️ Aucun effacement, à aucun moment.** Le dossier cumulatif se corrige, il ne s'efface pas. Et **ces
opportunités anciennes sont la matière première des instruments de mesure** — densité, taux de rejet,
réfutation des liens champ↔sphère. **Les effacer détruirait la base de mesure au moment où elle commence
à valoir quelque chose. L'archivage nettoie la vue, jamais la base.**

**Exiger une réponse pour retirer une opportunité du tableau** — oui, non, ou à revoir — et **relancer
les « à revoir » un mois plus tard**. *« À revoir » plutôt que « neutre » : l'utilisateur n'est pas
indifférent, **il ne sait pas encore**, le résultat n'étant souvent pas connu au moment du classement.*
**C'est la seule voie par laquelle la conversion réelle par type de signal peut s'accumuler — une donnée
que personne d'autre ne possède.**

**Question de désaccord.** Une opportunité arrivant à échéance **le jour où** un nouveau signal la fait
monter de palier. **La montée l'emporte, et l'alerte d'échéance ne part pas en même temps que la
renotification.**

**Tests exigés.** Dix opportunités arrivant à échéance produisent **une seule alerte**. **Aucune
opportunité n'est effacée, à aucun stade, quelle que soit son ancienneté.** Une opportunité archivée
recevant un signal fort revient comme nouvelle, avec mention. Échéance et montée le même jour : **une
seule communication part**.

---

## Chantier 25 — Le premier jour d'un nouvel abonné

*Dépend du chantier 22, qui fixe la durée de pertinence déterminant la profondeur d'antériorité.*

**Constat.** Le dossier contient des mois d'historique au moment où quelqu'un s'inscrit. **C'est le
miroir exact du problème du silence, et il est mal placé dans les deux sens** : noyer quelqu'un le
premier jour lui fait ignorer tout ce qui suit, mais lui cacher un historique qu'on possède le prive de
la valeur qu'il vient d'acheter.

**À construire.** **Antériorité remontant jusqu'à la durée de pertinence propre à chaque sphère**, un
mois en repli. **Plafond de vingt opportunités notifiées**, les mieux gradées — le reste reste
consultable sans notification, **ce qui fait de la profondeur d'exploration, et non de l'exactitude, le
différenciateur entre paliers**. Et une **présentation distincte** : c'est de l'historique, pas de la
détection en direct — **le dire évite qu'un utilisateur appelle en croyant que l'événement vient de se
produire.**

**Test exigé.** L'antériorité respecte la durée de pertinence par sphère, le plafond de vingt tient, et
**le reste est consultable sans notification**.

---

## Amendement au chantier 8 — cadence

**À appliquer au moment d'aborder le chantier 8.** Le **groupement est la forme normale**; l'envoi
unitaire est une exception qui demande un **seuil explicite**, sans quoi elle redevient la norme par
glissement. **Mardi par défaut** pour les cadences hebdomadaires et plus longues — *le vendredi est le
mauvais choix, une opportunité livrée alors attend le lundi et perd trois jours de fraîcheur.* **Fenêtre
à 10 h, dans le fuseau de l'utilisateur, jamais celui du serveur** — ce qui est détecté après attend la
fenêtre suivante, **et la fenêtre s'applique aussi à l'exception unitaire**, sans quoi un signal fort
peut partir à 23 h ou un dimanche. *Détail qui passe inaperçu jusqu'à ce qu'un client de l'Ouest reçoive
ses lots à 7 h du matin.*

**Tests exigés.** Une cadence hebdomadaire part **le mardi dans la fenêtre, au fuseau de l'utilisateur**.
Une opportunité détectée après la fenêtre **attend la suivante**, y compris quand elle est éligible à
l'exception unitaire.

---

## Mesurer une régularité — piste ouverte, rien à construire

**Mesurer qu'un événement en annonce un autre exige d'observer les deux bouts.** Le portefeuille est
entièrement du côté du déclencheur : un agrandissement se voit, l'achat qui suit ne se déclare nulle
part. **Aucune source ne comblera ça** — les ventes entre entreprises privées n'ont aucune obligation de
déclaration.

**Sauf sur le secteur public, où la boucle se ferme sans utilisateur.** Un permis de construction puis,
quelques mois plus tard, un contrat de systèmes de sécurité : **les deux apparaissent au même endroit.**
Trois choses en sortiraient — les **enchaînements** entre types de contrats sur un même organisme, les
**délais réels** mesurés plutôt que supposés, et les **absences**.

**Limite à nommer :** c'est un portrait du secteur public, déformé par les seuils. **Une régularité
mesurée là devient une hypothèse pour le privé, à réfuter par le taux de rejet — jamais un fait
établi.**

*La seconde voie passe par les utilisateurs, et elle est au chantier 24 : un prospect marqué « gagné »
est exactement l'information manquante.*

---

## Chantier 26 — Passerelle du non déterministe et normalisation par vocabulaire

**À faire avant les chantiers 12, 18 et 21**, ses trois appelants — **construit après eux, il faudrait
défaire trois implémentations.**

**Constat.** Cinq usages du non déterministe existent ou sont prévus. **Ils se ramènent à deux formes**,
et rien n'empêche aujourd'hui qu'ils soient implémentés cinq fois, **avec cinq jeux de garde-fous à
maintenir et aucun endroit qui compte le coût**.

**À construire.**

1. **Composant A — classer un texte libre dans un catalogue fermé.** Une implémentation, trois
   appelants : suggestion de sphère et de « qui », normalisation de texte libre, diagnostic à rebours.
2. **Composant B — rédiger à partir d'une structure de faits.** Un seul appelant, le narratif. **Ne pas
   fusionner avec A** : le garde-fou diffère, et c'est ce que la frontière de la charte protège.
3. **Normalisation par vocabulaire, jamais par enregistrement.** Une valeur déjà vue se résout par
   consultation, sans appel — **la seule optimisation qui change l'ordre de grandeur du coût**. Amorcer
   la table par un passage sur les valeurs distinctes existantes.
4. **Cache par empreinte** pour la configuration; **génération unique et stockage** pour le narratif,
   avec regroupement du lot en un seul appel.
5. **Modèle différencié** : A peut tourner sur un modèle nettement plus léger que B.
6. **La passerelle**, point de passage obligé des deux composants, portant cache, validation du
   garde-fou, repli et comptage par usage.

**Question de désaccord.** Une valeur du vocabulaire **reclassée** — catégorie qui change de sens, ou
erreur corrigée : les enregistrements déjà normalisés sont-ils recalculés, marqués, ou laissés tels
quels? *Le principe du dossier qui se corrige sans s'effacer s'applique, mais la mécanique reste à
définir.*

**Acceptation.** Un test qui ingère cent mille lignes portant dix valeurs distinctes produit **dix appels
au plus, pas cent mille**. Et **une indisponibilité du modèle ne produit jamais une absence de résultat,
seulement un repli.**

---

## Chantier 27 — Consolidation et allègement

**Réserve d'entrée :** déduit des documents, pas du code — **chaque point commence par une vérification**,
et un point déjà réglé se rapporte comme tel. Rien ici n'ajoute de fonctionnalité : **retirer des chemins
parallèles avant qu'ils divergent.**

**27.1 — L'enrichissement web, devenu la moitié d'un cycle.** Il tourne **pour chaque entreprise
détectée, avant tout seuil**, alors qu'avec un seuil de publication la majorité ne seront jamais
présentées. **Mesuré le 8 septembre : sur 29 min 10 s, treize minutes d'ingestion et seize minutes
d'enrichissement qui échoue.** Ce n'est plus du gaspillage en appels, **c'est la moitié d'un cycle
entièrement dépensée en échecs** — d'où sa place en tête. *L'objection connue — il sert aussi de filtre
d'exclusion — se traite en appliquant l'exclusion **après** le score et **avant** la livraison.* **À
faire :** le déplacer après le seuil, mesurer avant et après, rapporter l'écart. **Si l'écart est faible,
revenir en arrière — mais il faut le chiffre.**

**27.2 — Six échéanciers pour un seul besoin.** Décision non tranchée, revalidation légale, revalidation
de l'avantage, archivage, alerte avant archivage, seuil de silence. **Six fois la même mécanique — une
date, un porteur, une action.** Un seul ordonnanceur à entrées typées.

**27.3 — Quatre normes apprises de forme identique.** Volume par source, rythme par profil, base par
taille et secteur, amplitude de diff. Toutes accumulent, dérivent une référence, alertent sur l'écart.
**Un composant, quatre configurations** — sans quoi les quatre divergeront sur les valeurs aberrantes et
les périodes creuses.

**27.4 — Les journaux d'exécution, parallèles et sans clé commune.** **Trois tables décrivent la même exécution sans aucune clé
partagée.** Conséquence directe, traitée au chantier 2 : un connecteur en quarantaine s'enregistre comme
un succès à zéro signal, **indiscernable d'un territoire calme**. *Un cas de plus le 8 septembre : quand
la base tombe, la trace de sa panne ne peut pas s'y écrire — **la ligne reste ouverte et elle ment**. La
lecture n'a été sauvée que parce que le compte venait du rapport en mémoire, d'où la règle : **un compte
qui décrit une exécution ne se calcule jamais depuis la base que cette exécution écrit.*** **Consolider
avant que les prochains chantiers ajoutent trois journaux d'exécution de plus.**

**27.5 — Deux couches d'état, prémisse corrigée.** Pas deux vérités concurrentes mais **deux questions
différentes** : l'une répond « ce run est-il sain », l'autre « que sait-on de cette entité ». Retirer
l'une casserait la quarantaine, l'autre la résolution — **les deux survivent**. **Le risque est
d'entretien, pas d'exécution** : deux fonctions de correspondance à garder synchronisées, d'où une
vérification macro périodique **pour que la dérive se voie au lieu de s'installer**.

**27.6 — La taxonomie « qui » duplique celle des sphères.** Même échelle, même résolution de synonymes,
même suggestion. **Le miroir était le bon choix; reste à vérifier si c'est une mécanique générique
instanciée deux fois ou deux implémentations parallèles** — dans le second cas chaque amélioration se
ferait deux fois, et **un troisième axe rendrait le problème triple**.

**27.7 — Code dont l'expiration est connue.** Le *regroupement grossier des secteurs* — onze catégories
par mots-clés, 75 % de couverture — que la normalisation du chantier 26 remplace : **à marquer comme
transitoire avec la date de son retrait**, plutôt que de le laisser devenir permanent. Le *bonus de
corroboration inter-provinciale*, en veilleuse : vérifier qu'il ne s'exécute pas pour rien. ✅ Le
*connecteur d'offres d'emploi*, mis en veilleuse **avec une condition de réactivation vérifiable plutôt
qu'une intuition**.

**27.8 — Les réglages visibles.** Cinq mécanismes filtrent ce qui parvient à l'utilisateur; **il ne
devrait jamais en voir plus de deux** — sa sensibilité et sa fourchette de taille. Le reste relève du
produit, **comme les poids de sphères : ils existent dans les données, ils ne sont jamais l'interface**.

**27.9 — Les copies vides des tables miroir sur la base distante.** Huit tables — `diff_run_historique`,
`diff_quarantaines`, `req_entries` et cinq autres — existent à vide sur la base de produit, reliquat du
découpage du 6 septembre. **Ce n'est pas un reliquat inoffensif** : elles portent le schéma d'avant le
chantier 2, et **un routage qui se tromperait de moteur réussirait sur une table vide plutôt que
d'échouer.** C'est la forme exacte du motif. *Signalé le 8 septembre depuis le chantier 2, sans y toucher
— ce n'est pas son chantier.*

**Le remède retire plutôt qu'il ne garde** : les supprimer convertit un succès silencieux en échec
bruyant. **Mais c'est une migration destructive, pas additive** — celle-là a besoin de la fenêtre de
restauration, contrairement à un index qui se défait par `DROP INDEX`. **À ne pas lancer avant que la
fenêtre ait été testée.**

**27.10 — Rien ne compare le fichier d'environnement du serveur à ce que le code demande.** *Signalé au
chantier 28, où il était consigné dans un mandat clos — donc invisible. Rattaché ici le 9 septembre
2026.* Deux variables d'envoi manquaient au fichier de l'hôte, **découvertes par le refus du serveur
d'envoi**, pas par une vérification. Le fichier s'est accumulé par ajouts successifs, et **aucun
mécanisme ne confronte son contenu à ce que le code lit au démarrage.** Troisième occurrence de ce motif
au moment du signalement.

**Ce qu'il faut : un contrôle qui liste les variables attendues par le code et celles présentes sur
l'hôte, et qui nomme l'écart dans les deux sens.** Une variable attendue et absente casse au premier
usage; une variable présente et jamais lue est un reliquat qui donne l'illusion d'une configuration
complète. *Même forme que `migration_colonnes.py` pour le schéma — et **la section s'affiche même vide**,
« aucun écart » étant une information et non un silence.*

**Acceptation générale : aucun comportement observable ne change.** Les tests existants passent sans
modification. **Ce qui change, c'est le nombre de chemins qui font la même chose.**

### État

- ✅ 27.4 confirmé · 27.5 investigué · 27.7 partiellement.
- ⬜ **27.1 en tête** — la moitié d'un cycle, en échecs. **⚠️ Ce n'est pas qu'un problème de
  performance.** Les spécifications, annexe point 10, signalent que l'enrichissement web tourne pour
  chaque entreprise détectée **avant tout seuil**, et qu'il **sert aussi de filtre d'exclusion** : le
  déplacer change donc ce qui est exclu, pas seulement ce que ça coûte. *Décision à trancher avant
  d'optimiser, sans quoi l'optimisation modifiera les résultats en silence.*
- ⬜ Chemin d'import du miroir — deux allers-retours par ligne, mesuré.
- ⬜ 27.2, 27.3, 27.6, 27.8, 27.10 · **27.9 — bloqué sur le test de la fenêtre de restauration**.

---

## Chantier 28 — Première boucle complète ✅

**Clos le 8 septembre 2026.** *Mandat : `falkye-chantier-28-premiere-boucle.md`.*

**Ce qu'il a livré.** Profil créé par un humain, canal d'envoi réel, ordonnanceur et battements de cœur,
fil de bout en bout sur données réelles, rétroaction depuis un lien cliqué, désabonnement en un clic,
chaîne de déploiement, journaux d'exploitation. **Et un courriel réel parti du serveur, arrivé chez le
destinataire, authentifié de bout en bout, avec un lien de désabonnement pointant vers notre propre point
d'entrée.**

**Ce qu'il a surtout produit : trois hypothèses transformées en mesures.** La faille A chiffrée — une
source repliée sur une sphère unique. La faille D chiffrée deux fois. Et un estimé de mémoire qui aurait
tué le serveur si on l'avait suivi. **Chaque décision produit prise avant lui était de la conception
d'avance.**

**Huit défauts corrigés en chemin**, dont cinq du même motif — *capturer sans livrer*, sous une forme
nouvelle chaque fois. Le lot perdu au premier échec d'envoi. Le faux succès sur code d'erreur. Le
désabonnement mort. Le profil désabonné générant dans le vide. La réponse du service jamais écoutée.

**Ce qui en sort et vit ailleurs.** Les scores qui ne discriminent pas → chantier 22 puis 4. La source
repliée sur une sphère → chantier 22. L'enrichissement web → point 27.1. Les lignes d'exécution
orphelines → chantier 2.

**⚠️ Deux lignes de sa liste d'état ont menti pendant deux jours, corrigées le 8 septembre.** Le
désabonnement y restait « contourné en production » et la chaîne de déploiement « jamais exécutée »,
**alors que le corps du même mandat portait déjà la levée de la dépendance et la preuve de l'envoi
réel**. *Le défaut n'est pas dans le fait, il est dans la liste : une liste d'état se met à jour dans le
même geste que le fait qu'elle décrit, sinon c'est elle qu'un lecteur pressé croira — et c'est
exactement ce qu'un mandat sert à faire lire.*

---

## Chantier 29 — Persistance de la base et hôte de production

**🟡 En cours. Trois gestes restent, et une question ouverte.** *Mandat détaillé :
`falkye-chantier-29-persistance.md`.*

**Constat.** L'avantage défendable repose sur ce qui s'accumule. **Un actif qui s'accumule dans un
environnement dont la persistance n'est pas garantie n'est pas un actif, c'est un compte à rebours** —
démontré par les faits, 2,7 Go perdus au recyclage du conteneur *(journal, cas 14)*.

**Les décisions à ne pas rediscuter.** Une **base gérée compatible SQLite accédée en HTTPS** — l'égress
limité au port 443 rend toute base classique injoignable, **et c'est le port, pas le dialecte SQL**. Un
**découpage** produit au distant, miroirs en local : ceux-ci représentent 99,95 % du volume et **zéro
pour cent de ce qui se perdrait**. Un **hôte à 8 Go**, condition de fonctionnement et non marge —
l'import du miroir atteint 5,4 Go. Une **architecture des secrets à deux emplacements jamais mélangés**.

**⚠️ Le même code a trois régimes**, et l'erreur a été commise deux fois avant de le comprendre.

| | Développement | Hôte, amorçage | Hôte, régime |
|---|---|---|---|
| Durée | 92,5 min | 1 h 26 | **29 min 10 s** |
| Processeur | 100 % | 22 % | **6 %** |
| Facteur dominant | le repli de résolution | la latence de la base | **l'enrichissement qui échoue** |

**Avant de conclure sur la lenteur d'un cycle, établir lequel des trois on observe.**

**Délai retenu : 5 400 secondes**, facteur 3,1 — **le point où les deux erreurs coûtent à peu près
pareil** : trop court tue un cycle qui travaillait, trop long laisse un cycle bloqué mobiliser l'hôte
sans que rien ne le signale.

**⚠️ Écart de résidence des données.** La base vit hors du Canada. **Déclencheur de migration : la
décision d'ouvrir les inscriptions**, pour migrer à vide plutôt qu'avec des données de clients.

**⚠️ Deux incidents du 8 septembre, consignés ici parce qu'ils portent sur l'hôte et la base.**

**Le minuteur qu'on croyait éteint a livré.** Armé depuis l'installation de l'hôte — `disabled` mais
`active` — il a lancé un vrai cycle avec livraison à 8 h UTC, **4 h 31 heure de Montréal**, sans témoin.
Le fuseau de l'hôte a été corrigé d'UTC vers `America/Toronto`; le minuteur est arrêté, **vérifié
`inactive`**. `docs/DEPLOIEMENT.md` porte les cinq occurrences du motif et les quatre lectures à faire
avant d'en activer un — avec le point qui manquait : **`disabled` ne veut pas dire arrêté, `enable` ne
gouverne que le prochain amorçage, seul `is-active` répond à la question qu'on posait.**

**La base a été bloquée le matin, quota de lignes lues épuisé.** L'index unique sur le NEQ acceptait
8 395 NULL, donc chaque résolution d'entreprise non identifiée lisait 8 395 lignes deux fois. **Index
composite `ix_companies_neq_nom_normalise` posé et vérifié en après-midi** — chemin exact 8 396 → 0,
préfixe 8 396 → 84, **repli par sous-chaîne inchangé à 8 396, et il lit la base durable : facturé.** La
fuite est **réduite, pas fermée**, et son résiduel est gouverné par la fréquence de ce repli — d'où la
ventilation exigée au chantier 2. Palier de quota supérieur maintenu **temporairement**, jusqu'à mesure
d'un cycle complet en régime.

**Règle qui en sort.** Pour une migration **additive** — un index — le retour arrière est `DROP INDEX`,
pas la restauration : elle ne touche pas aux données et se défait à la seconde près. **La restauration
est le filet des migrations qui modifient des données.**

### État

- ✅ Persistance, découpage, hôte, application en production, déploiement, miroir, cycle en régime — **chaque case porte sa preuve au mandat**.
- ✅ Fuseau de l'hôte corrigé · minuteur vérifié `inactive` · index composite posé et vérifié.
- ⬜ Activer le minuteur · tester la fenêtre de restauration · liste blanche de l'hébergeur.
- ⚠️ **Question ouverte : où vivent l'historique et les quarantaines de diff.** Le mandat les place au
  distant; le travail 1bis du chantier 2 les a mesurés dans le fichier miroir local. **Les deux ne peuvent
  pas être vrais ensemble**, et si l'état de diff vit hors de la base durable, la garantie de persistance
  ne le couvre pas. Le test qui verrouille la cible de chaque table tranche. **À régler avant clôture.**

---

# Partie 3 — Le raisonnement derrière l'ordre

**L'ordre est dans l'index.** Cette section dit pourquoi, pour qu'il puisse être ajusté en connaissance
de cause plutôt que suivi mécaniquement.

*Les regroupements et les dépendances ne sont pas repris ici — ils sont expliqués une seule fois, sous
le tableau d'index de la Partie 2.*

**Rangs 2 à 4 — le socle, non réordonnable.** La santé de source protège la crédibilité, seule chose qui
ne se rachète pas — et **c'est un instrument de mesure, qu'on installe avant de mesurer**. La calibration
vient ensuite parce que **le moteur de notation reflète fidèlement une entrée uniforme** : le raffiner
avant d'avoir appris à lire un signal ne lui donnerait rien de plus à départager. Puis l'identité et la
confiance d'appariement, **seul groupe à coût croissant** — leur prix monte avec chaque semaine de
dossiers accumulés.

**Rangs 5 à 9 — la vérité du produit.** Consolidation, placement, registre légal, canal hors profil,
passerelle du non déterministe. Peu de code, mais **ils changent ce qu'on vend et ce qu'on a le droit
d'ingérer**. Le registre légal est bloquant pour l'activation des sources vérifiées, et la passerelle
précède ses trois appelants — sans quoi il faudra défaire trois implémentations.

**Rangs 10 à 13 — ce que l'utilisateur vit.** Précision perçue, silence, narratif, cadence. **Le silence
mérite d'être traité tôt** : un abonné qui ne reçoit rien part avant de se plaindre d'une cadence.

**Rangs 14 à 21 — les instruments et l'offensif.** Leur résultat n'est lisible qu'après des mois
d'historique, **et c'est exactement pourquoi il ne faut pas les repousser indéfiniment** : ce qu'ils
accumulent ne se rattrape pas en accélérant plus tard.

**Sur le séquencement global.** Les premiers rangs ne sont pas des ajouts — **ce sont des réparations
d'écarts entre ce que les documents promettent et ce que le code fait**. Les livrer avant les premiers
clients payants coûte quelques semaines; les livrer après coûte des clients. Et pour trois d'entre eux —
palier d'entrée vide, vérification hors Québec, fonctionnalités non validées — **le client s'en
apercevrait avant nous**.
