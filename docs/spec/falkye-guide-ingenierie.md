# FALKYE — Guide d'ingénierie

*Extrait de la charte le 7 septembre 2026. La charte tranche des arbitrages de produit; ce document
porte les règles de vérification — ce qu'il faut faire pour qu'un chantier soit réellement terminé.*

**À lire avant d'ouvrir un chantier, et à relire avant de le déclarer clos.** Chaque règle ici vient d'un
défaut réel; le détail des incidents est dans `falkye-journal-des-cas.md`. *Les cas 7 à 13, 20, 22 et 23
renvoient à ce document — leurs règles vivaient à la section 11 de la charte avant l'extraction.*

> **⚠️ Lire le glossaire en tête de `falkye-audit-et-mandat.md` avant ce document.** Cinq mots du corpus
> portent chacun deux sens ou plus — **état** (celui d'une source, chantier 1, contre celui du produit,
> chantier 29), **journal** (d'exécution, de diagnostic, de repli, d'exploitation, ou le journal des
> cas), **numéro contre rang**, **statut d'exécution contre état de santé**, et **chantier contre travail
> contre point**. *La contradiction du 7 septembre s'était logée dans le premier.*


---

## Vue d'ensemble et détail à la fois

**Deux réflexes simultanés.** *Micro* — chaque mécanisme configuré pour le cas qui l'a motivé. *Macro* — chaque mécanisme revérifié contre l'ensemble déjà construit : toutes les sources actives, toutes les combinaisons entre dimensions existantes.

**Question obligatoire quand un mécanisme touche une dimension pluralisée ailleurs :** que se passe-t-il quand deux éléments de cette dimension sont en désaccord? **C'est une condition de fin, pas un réflexe** — la question se pose par écrit, avec sa réponse implémentée et testée. **Un chantier dont la question de désaccord n'a pas de test n'est pas terminé, même si tout le reste est vert.**

**Une règle portée par la discipline de chaque appelant n'est pas portée.** *(journal, cas 27)* Elle doit
vivre à l'endroit qui ne peut pas être contourné. **Et une conformité accidentelle n'est pas une
garantie** : deux composants respectaient une règle uniquement parce que leurs compteurs y étaient câblés
par hasard — rien dans leur code n'exprimait l'intention, et ça disparaît au premier changement sans que
rien ne le signale.

**La vérification macro s'exécute, elle ne s'espère pas** — faire tourner le mécanisme contre toutes les sources concernées et rapporter chaque résultat. *(journal, cas 7)* **Une suite verte ne dit rien du comportement au volume réel ni de la qualité de la donnée d'entrée.**

## Ce qu'un test vert ne prouve pas

**Un module sans test n'est pas testé faiblement, c'est un angle mort complet** — indiscernable du reste quand on ne regarde que le total. *(journal, cas 8)*

**Ajouter des tests à un module ne le rend pas couvert.** La question est « ce changement précis est-il regardé », pas « ce fichier a-t-il des tests ». *(journal, cas 9)*

**Question après chaque modification : quel test tomberait si je défaisais ce que je viens de faire?** Si la réponse est aucun, le changement n'est pas couvert.

**Quatre formes du test qui passe pour la mauvaise raison**, toutes attrapées par cette question. Un test qui **fige une configuration** plutôt qu'un comportement — il casse sans défaut et rassure sans couverture. Une **variable d'environnement** présente sur la machine. Un **état que l'opération fautive produit aussi** — la mutation passe sans rien casser. Les **privilèges du compte** qui lance la suite : un répertoire non inscriptible ne bloque pas un administrateur.

**La deuxième forme a une variante qui ne se voit pas même en regardant : le mode d'installation d'un paquet.** *(journal, cas 26)* Une installation en mode éditable fait résoudre un import depuis les paquets installés quel que soit le répertoire courant — **elle ne s'écrit ni dans le code ni dans la commande**, donc rien ne signale que l'essai testait un état de la machine plutôt que le chemin d'exécution.

**Et une garantie qui dépend d'un objet de schéma — index unique, contrainte, clé étrangère — ne s'affirme qu'après avoir vérifié que la base de PRODUCTION le porte.** *(journal, cas 25)* Des tests qui bâtissent leur propre schéma vérifient réellement la contrainte, et prouvent la cohérence du code avec lui-même. **Le modèle dit ce qu'on veut; seule la base dit ce qui est.**

**Un seuil calibré sur la vraisemblance ne protège pas d'un plafond technique — les deux se vérifient séparément.** *(mandat du chantier 1, découvert le 4 septembre 2026)* Les seuils de quarantaine laissaient passer jusqu'à 30 % de disparitions, soit 818 000 clés pour le registre, alors que le traitement plantait au-delà de 32 766. **Le seuil bornait le bruit et ne bornait rien à cette échelle.**

**Une simulation ne prouve que la cohérence du code avec lui-même.** Les réponses simulées d'un service externe se recopient depuis des réponses **réelles**, obtenues une fois contre le vrai service.

## Le glissement du décidé au fait

Un fait vérifié se fait citer sous une forme raccourcie, puis sert de prémisse à autre chose. Chaque étape est raisonnable, et un peu de précision se perd à chaque reprise. *(journal, cas 10)*

**Trois cas le même jour, invisibles dans le code comme dans les documents — il a fallu taper une commande pour les découvrir** *(journal, cas 10)*.

**Trois marqueurs le trahissent.** *Le particulier devient général* — un terme collectif remplace une liste de choses précises. *L'agent disparaît* — « j'ai vérifié que » devient « la base répond », et **un fait sans témoin vieillit sans qu'on s'en aperçoive**. *Le verbe se déplace* — décidé devient fait, mesuré devient en place, construit devient déployé.

**Deux règles mécaniques. La preuve voyage avec le fait** — pas « le serveur est actif » mais « le serveur répond, vérifié le 5 septembre par connexion », de sorte qu'une reprise qui la perd se voit. Et **un fait sans preuve attachée ne peut pas servir de prémisse à autre chose**.

**Une valeur tronquée à l'affichage ne se complète jamais de mémoire — elle se relit à la source.** *(journal, cas 29)* C'est le glissement appliqué à une VALEUR plutôt qu'à un état : une forme abrégée est visible — empreinte courte, identifiant tronqué, numéro de version, chemin abrégé — le reste est complété par déduction, et **rien ne distingue à la lecture ce qui a été vu de ce qui a été reconstruit**. Et quand une opération offre de vérifier la valeur attendue, on la lui passe : c'est le seul moment où la reconstitution se voit.

**Un outil qui juge ou modifie un schéma annonce sa cible en tête de sortie, et refuse de juger une cible que personne n'a choisie.** *(journal, cas 30)* Troisième forme, après la preuve absente et la preuve périmée : **la preuve fabriquée par l'instrument qui devait la recueillir**. Un repli silencieux vers une base vide fait rendre le verdict le plus RASSURANT — rien ne manque, parce que rien n'existe. Le vert est sincère et l'outil est structurellement incapable de dire non. **Un outil de migration qui crée sa propre cible ne migre rien, il fabrique.**

**Un état sans date se lit comme courant.** *(constaté le 2026-09-09 sur Guichet-Emplois)* C'est le VOISIN de « la preuve voyage avec le fait », pas la même : là il manquait une preuve, ici la preuve existait et l'état a simplement changé depuis. Quatre documents portaient quatre états de la même source — « à développer faute de nom d'employeur » (31 août), « réactivée par les pages de détail » (1er septembre), « 9e source active » (1er septembre), et `en_pause` pour une TROISIÈME raison découverte le 7. **Chacun était vrai à sa date, aucun ne le disait**, et le plus récent était le seul introuvable dans les documents.

**Trois remèdes, du plus fort au plus faible.** *Ne pas recopier* — un état qui a une source de vérité ailleurs s'y lit, il ne se duplique pas. *Dater en tête* quand il faut le garder comme repère : « Au 1er septembre — » plutôt qu'une parenthèse au milieu de la phrase. *Et signaler le dépassement là où l'ancien état est écrit*, plutôt que de le corriger : un récit d'investigation garde sa valeur, à condition de dire qu'il a été dépassé et par quoi.

**Test de relecture :** cette affirmation porte-t-elle la trace de ce qui l'a établie? Sinon, c'est une décision — et il faut le dire — ou une supposition déguisée en fait.

## Un chantier n'est clos que sur l'état observable

**Le critère d'acceptation porte sur ce qui s'observe depuis l'extérieur du code** — pas « les tests passent » ni « le code est poussé », mais « l'application répond sur l'hôte », « la base contient le miroir », « l'unité est active ». Chacun se vérifie en une commande. **Et le critère doit couvrir tout ce que le chantier prétend livrer**, pas la partie la plus facile à vérifier.

**Un geste d'installation fait trop tôt ne rate pas.** *(journal, cas 11)* **Un geste manuel qui dépend d'un artefact produit ailleurs se fait après vérification que l'artefact est arrivé.**

**Le premier passage réel d'un mécanisme se fait sur un cas dont on connaît déjà la réponse.** *(journal, cas 26)* En conditions réelles, avant le cas dont on ne la connaît pas. **Un mécanisme neuf porte deux inconnues à la fois** — ce qu'il répond, et s'il tourne — et un premier passage sur un cas ouvert ne permet pas de les séparer : une bonne réponse peut venir d'un mécanisme à moitié cassé, et une panne peut se lire comme une trouvaille. **Le cas connu n'est pas un essai de plus, c'est ce qui rend le suivant lisible.** Quand le mécanisme s'applique à lui-même, ce cas est gratuit.

## Trois pièges de relecture et de correction

**Un commentaire qui justifie une erreur la rend invisible.** *Un relecteur y voit une intention plutôt qu'une inversion (journal, cas 12).* **Quand un champ de source porte un drapeau, la condition se vérifie contre la documentation du diffuseur, jamais contre le commentaire du code.**

**Vérifier que le remède ne coûte pas plus que le mal.** *(journal, cas 13)* **La surface qu'on n'ouvre pas est celle qu'on n'a pas à surveiller.** Et **une erreur bénigne mais permanente n'est pas cosmétique** — elle apprend à ignorer une ligne rouge, ce qui défait un journal construit pour distinguer une panne d'un silence.

**Deux formes d'un même contenu ne s'écrivent jamais séparément.** Version texte et version HTML, résumé et notification unitaire : écrites en parallèle, elles divergent. **Une divergence entre deux formes du même contenu est un mensonge** — celui qui lit l'une n'a pas la même information que l'autre, sans que rien ne le signale. Une source unique, deux rendus, un test sur l'invariant.


## Une phrase qui a une source de vérité ailleurs n'a rien à faire là

**Elle a une date d'expiration que personne ne surveille.** *(constaté le 2026-09-09)* Le README du
dépôt recopiait l'inventaire des sources, dont la vérité vit au registre. Deux jours après un
changement de statut, il annonçait encore l'ancien — sans que rien ne soit tombé, puisque rien ne
comparait les deux.

**Un document d'accueil dit OÙ REGARDER et COMMENT DÉMARRER, jamais ce qui est vrai.** Trois choses
lui appartiennent en propre : ce que le projet est, comment on le lance, et la carte de ce qui répond
à quelle question. Tout le reste se renvoie.

**Une exception, et une seule : la carte doit dire comment lire ce vers quoi elle renvoie.** Si
l'inventaire vers lequel on pointe se lit de deux façons — ici `actif` ne veut pas dire « tourne dans
un cycle » —, le renvoi sans cette clé produit un lecteur qui compte faux en suivant le bon conseil.

**Ce qui se vérifie mécaniquement se verrouille par un test, mais après le retrait, pas à sa place.**
Un test qui ferait mentir un document moins vaut moins que le retrait de ce qu'il n'avait pas à dire.
Et il ne doit jamais exiger plus que la cohérence : **nommer une chose sans la déclarer active reste
légitime** — un test qui l'interdirait forcerait à retirer une information vraie pour passer au vert.

## Qui repère qu'un document est devenu faux

**Repérer est une obligation, pas une courtoisie.** Un écart constaté se dit dans le tour où il est
constaté, même sans rapport avec ce qu'on faisait. Convenir de qui ÉCRIT dans un document ne dit rien
de qui REGARDE — et laisser cette ambiguïté valoir « je ne touche pas » revient à ne pas regarder.

**Le constat voyage avec sa proposition de texte.** Un signalement sans proposition fait porter le
travail deux fois; une correction sans signalement est une main dans le texte de quelqu'un d'autre.

**Quand une modification rend un document faux, corriger ce document fait partie de la modification.**
Pas d'un suivi, pas d'une demande ultérieure — de celle-là. Un suivi est une intention; une intention
ne tient pas un document à jour.

## Ne jamais présumer une capacité non testée

**La règle est symétrique.** Ne jamais présumer une limite non testée — un fournisseur peut couvrir un
besoin réel même si son marketing met autre chose de l'avant. **Mais ne jamais présumer une capacité non
testée non plus** : un connecteur qui passe ses tests contre des mocks n'a rien prouvé sur le service
réel, et une couverture annoncée dans une documentation n'est pas vérifiée.

**La deuxième erreur est plus dangereuse : présumer une limite fait rater une occasion, présumer une
capacité fait vendre une promesse.**

**Avant de comparer des options, mesurer la contrainte qui les départage** *(journal, cas 4)*. **Une
option écartée pour la mauvaise raison sera un jour retenue pour la mauvaise raison aussi** — corriger le
motif, pas seulement la conclusion.

**Sur les intégrations à un compte tiers :** retenir le mécanisme d'autorisation que la plateforme
**recommande pour les intégrations multi-clients**, jamais le plus simple à construire quand celui-ci est
réservé à un usage interne. Le choix se prend avant que la connexion existe en production — après,
migrer veut dire redemander à chaque client de se reconnecter.

## Ce qu'un état « construit » ne prouve pas

**Une fonctionnalité construite et testée n'est pas éprouvée.** Tant qu'elle n'a pas tourné contre le
service réel, elle se documente comme **construite mais non validée en réel** — un état distinct, ni un
✓ ni un tiret. Ça ne bloque pas le développement, ça bloque la promesse commerciale.

**Quatre états, jamais trois.** Fait avec sa preuve · en cours · **présumé fait, non vérifié** · à faire.
Le troisième est celui qui manque partout, et c'est précisément l'état où se trouvaient les trois écarts
du cas 10.

**Un passage à blanc en développement ne fait pas passer de « construit » à « éprouvé ».** *(journal,
cas 26)* L'environnement de développement porte des états que rien d'autre ne porte; un essai n'y prouve
un chemin d'exécution que si l'environnement réel a été reproduit **sur le point précis en cause**.

## Deux règles nées de l'exploitation

**Un mécanisme automatique ne doit pas interrompre le travail; un geste humain mal formé, si.** Une
réconciliation que son fichier d'entrée peut tuer est inutile le jour où on en a besoin — elle saute,
compte et signale. Une déclaration humaine incomplète, elle, doit lever : c'est le seul moment où
quelqu'un est là pour la corriger.

**L'absence de mesure n'est pas une mesure nulle.** Zéro et « rien » ne se rangent jamais dans la même
valeur : un territoire calme où la source a répondu vaut `0`, une exécution tombée en route vaut `NULL`.
Même règle qu'un fichier vide contre un fichier introuvable — « rien à reprendre » et « je ne sais pas »
sortent différemment — et que le troisième des quatre états ci-dessus. **Un partiel comparé à une norme
se lit comme une chute.**
