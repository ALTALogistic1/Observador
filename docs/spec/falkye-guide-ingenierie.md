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

**Le premier des quatre se pose aussi dans ce qu'on vient d'écrire.** *(constaté le 2026-09-10)* Une assertion qui repérait une ligne de sortie **par son indice** a cassé dix minutes après avoir été écrite, parce qu'un en-tête était passé d'une ligne à deux — sans défaut, sans rien à corriger que le test. On relit un test neuf avec la même question qu'un ancien : **qu'est-ce qui le ferait tomber sans qu'un défaut existe?** L'avoir écrit soi-même il y a un instant ne le protège de rien; ça rend seulement moins probable qu'on le relise.

**La deuxième forme a une variante qui ne se voit pas même en regardant : le mode d'installation d'un paquet.** *(journal, cas 26)* Une installation en mode éditable fait résoudre un import depuis les paquets installés quel que soit le répertoire courant — **elle ne s'écrit ni dans le code ni dans la commande**, donc rien ne signale que l'essai testait un état de la machine plutôt que le chemin d'exécution.

**Et une garantie qui dépend d'un objet de schéma — index unique, contrainte, clé étrangère — ne s'affirme qu'après avoir vérifié que la base de PRODUCTION le porte.** *(journal, cas 25)* Des tests qui bâtissent leur propre schéma vérifient réellement la contrainte, et prouvent la cohérence du code avec lui-même. **Le modèle dit ce qu'on veut; seule la base dit ce qui est.**

**Un seuil calibré sur la vraisemblance ne protège pas d'un plafond technique — les deux se vérifient séparément.** *(mandat du chantier 1, découvert le 4 septembre 2026)* Les seuils de quarantaine laissaient passer jusqu'à 30 % de disparitions, soit 818 000 clés pour le registre, alors que le traitement plantait au-delà de 32 766. **Le seuil bornait le bruit et ne bornait rien à cette échelle.**

**Une simulation ne prouve que la cohérence du code avec lui-même.** Les réponses simulées d'un service externe se recopient depuis des réponses **réelles**, obtenues une fois contre le vrai service.

## Le glissement du décidé au fait

Un fait vérifié se fait citer sous une forme raccourcie, puis sert de prémisse à autre chose. Chaque étape est raisonnable, et un peu de précision se perd à chaque reprise. *(journal, cas 10)*

**Trois cas le même jour, invisibles dans le code comme dans les documents — il a fallu taper une commande pour les découvrir** *(journal, cas 10)*.

**Trois marqueurs le trahissent.** *Le particulier devient général* — un terme collectif remplace une liste de choses précises. *L'agent disparaît* — « j'ai vérifié que » devient « la base répond », et **un fait sans témoin vieillit sans qu'on s'en aperçoive**. *Le verbe se déplace* — décidé devient fait, mesuré devient en place, construit devient déployé.

**Deux règles mécaniques. La preuve voyage avec le fait** — pas « le serveur est actif » mais « le serveur répond, vérifié le 5 septembre par connexion », de sorte qu'une reprise qui la perd se voit. Et **un fait sans preuve attachée ne peut pas servir de prémisse à autre chose**.

**Une branche réinitialisée sur la base fusionnée décroche la tête d'une demande encore OUVERTE.** *(deux fois les 9 et 10 septembre 2026)* Reprendre le travail par `git checkout -B <branche> origin/<base>` est juste quand la demande précédente est fusionnée, et destructeur quand elle ne l'est pas : le distant garde la tête, le local ne l'a plus, et le prochain envoi l'efface. **Ce qui a arrêté les deux fois est le REFUS DE `git` sur un envoi non-rapide** — le même garde-fou que l'empreinte attendue d'une fusion, et `--force` le désactive. *D'où la règle : sur un refus non-rapide, on lit ce que porte le distant avant tout autre geste, et on rejoue son travail par-dessus. `--force` ne se pose qu'après avoir nommé ce qu'il détruit.* Le remède qui n'en est pas un serait de mieux s'en souvenir : reprendre depuis la tête de la BRANCHE plutôt que depuis la base retire l'occasion.

**Et un chiffre repris d'un message n'est pas plus vérifié qu'une valeur complétée de mémoire.** *(constaté le 2026-09-10)* « Deux lignes orphelines » venait d'un échange, a été recopié dans un texte, accepté, puis écrit — il en fallait trois, et il a fallu relire la base pour le voir. **Ce n'est pas une forme nouvelle : c'est celle-ci appliquée à un texte déjà accepté.** Un accord sur un texte porte sur sa rédaction, jamais sur l'interdiction de vérifier ce qu'il affirme — et un chiffre qui a une source de vérité se relit à sa source, même quand il vient de la personne qui décide.

**Une valeur tronquée à l'affichage ne se complète jamais de mémoire — elle se relit à la source.** *(journal, cas 29)* C'est le glissement appliqué à une VALEUR plutôt qu'à un état : une forme abrégée est visible — empreinte courte, identifiant tronqué, numéro de version, chemin abrégé — le reste est complété par déduction, et **rien ne distingue à la lecture ce qui a été vu de ce qui a été reconstruit**. Et quand une opération offre de vérifier la valeur attendue, on la lui passe : c'est le seul moment où la reconstitution se voit.

**Un outil qui juge ou modifie un schéma annonce sa cible en tête de sortie, et refuse de juger une cible que personne n'a choisie.** *(journal, cas 30)* Troisième forme, après la preuve absente et la preuve périmée : **la preuve fabriquée par l'instrument qui devait la recueillir**. Un repli silencieux vers une base vide fait rendre le verdict le plus RASSURANT — rien ne manque, parce que rien n'existe. Le vert est sincère et l'outil est structurellement incapable de dire non. **Un outil de migration qui crée sa propre cible ne migre rien, il fabrique.**

**Un état sans date se lit comme courant.** *(constaté le 2026-09-09 sur Guichet-Emplois)* C'est le VOISIN de « la preuve voyage avec le fait », pas la même : là il manquait une preuve, ici la preuve existait et l'état a simplement changé depuis. Quatre documents portaient quatre états de la même source — « à développer faute de nom d'employeur » (31 août), « réactivée par les pages de détail » (1er septembre), « 9e source active » (1er septembre), et `en_pause` pour une TROISIÈME raison découverte le 7. **Chacun était vrai à sa date, aucun ne le disait**, et le plus récent était le seul introuvable dans les documents.

**Trois remèdes, du plus fort au plus faible.** *Ne pas recopier* — un état qui a une source de vérité ailleurs s'y lit, il ne se duplique pas. *Dater en tête* quand il faut le garder comme repère : « Au 1er septembre — » plutôt qu'une parenthèse au milieu de la phrase. *Et signaler le dépassement là où l'ancien état est écrit*, plutôt que de le corriger : un récit d'investigation garde sa valeur, à condition de dire qu'il a été dépassé et par quoi.

**Test de relecture :** cette affirmation porte-t-elle la trace de ce qui l'a établie? Sinon, c'est une décision — et il faut le dire — ou une supposition déguisée en fait.

## Quand un projet porte deux bases, une requête doit nommer son moteur

**Contrainte permanente depuis le découpage du 6 septembre 2026**, et elle n'était écrite nulle part —
elle a été trouvée en tombant dedans. Le produit vit au distant, les miroirs dans un fichier local, et
la fabrique de sessions route **par métadonnée**. Aucun des deux moteurs n'est le défaut : une session
qui porte deux bases ne sait pas viser.

**Un `session.execute(text(...))` nu ÉCHOUE**, et voici la phrase qu'on obtient — c'est elle qu'on
reconnaîtra, pas le principe :

    sqlalchemy.exc.UnboundExecutionError:
    Could not locate a bind configured on SQL expression or this Session

**Tout outil, script ou commande qui interroge une table par du SQL brut nomme son moteur.** Par le
mappeur du modèle, qui est la seule source de vérité sur la base à laquelle une table appartient :

    connexion = session.connection(bind_arguments={"mapper": SourceRunLog.__mapper__})
    connexion.execute(text("SELECT ... FROM source_run_logs ..."))

*L'ORM n'a pas ce problème — `select(SourceRunLog)` porte son mappeur avec lui. Le SQL brut, non : c'est
une chaîne de caractères, et une chaîne ne dit pas d'où elle vient.* Voir
`outils/migration_chantier2_execution.py::connexion` pour l'aide déjà écrite.

**Ce que l'échec a d'heureux : il est bruyant.** Le défaut symétrique — une requête qui atteindrait la
MAUVAISE base et réussirait sur une table vide — ne dirait rien. C'est le motif du point 27.9, et c'est
pourquoi cette erreur-ci ne mérite pas d'être contournée par un moteur par défaut.

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

## Un document montré n'est pas un document versé

**Le corpus ne légifère que sur ce qu'il contient.** *(constaté le 2026-09-11)* Un document a été
mentionné en conversation — existant, décrit, avec trois de ses affirmations citées. Il a suffi de cette
mention pour qu'il soit traité comme une source à venir : sa place dans l'arborescence tranchée, son
chemin écrit, et **une clause de portée ajoutée à la charte qui le nommait**. Il n'a jamais été versé, et
il ne devait pas l'être.

**Trois états qu'on confond parce que rien ne les sépare à la lecture :** un document **mentionné**, un
document **promis**, un document **versé**. Seul le troisième se lit, se vérifie et se corrige. **Les deux
premiers n'existent pas pour le dépôt** — et une règle écrite pour eux prend l'autorité du document qui
la porte tout en n'ayant aucun objet.

**La règle. Rien ne s'écrit au corpus sur la foi d'un document qu'on n'a pas lu** — pas une clause, pas un
chemin, pas une place dans l'arborescence. Ce qui se fait à la place : **dire ce qui s'appliquerait, sans
nommer d'objet et sans créer de fichier**, et attendre que le document soit dans le dépôt. *Une règle
formulée d'avance garde sa valeur; une règle qui nomme un objet absent affirme son existence.*

**Ce que ça ajoute au motif connu.** *« Une valeur qu'on croit connaître tient lieu de la valeur qu'on n'a
pas lue »* portait sur des états du système, puis sur des valeurs reconstituées *(cas 25, 29, 30)*. Ici
l'objet non lu est **un document**, et le geste fautif n'est pas une lecture présumée mais **une écriture
fondée dessus**. C'est la règle 5 de la charte appliquée aux documents : **une source absente se signale,
elle ne se légifère pas.**

## Un exemple montré n'est pas un fait survenu

**Un exemple consigné comme un fait est plus solide qu'un fait.** *(constaté le 2026-09-11, journal, cas 16)* Il a été **construit pour illustrer**, donc il illustre parfaitement, donc **rien ne vient jamais le mettre en défaut**. Un vrai incident est encombrant : il a des détails qui ne servent à rien, des circonstances qui compliquent la leçon, parfois une cause qu'on n'a jamais élucidée. **Un exemple n'a que ce qu'il faut.** C'est exactement ce qui le rend impossible à repérer une fois écrit au passé.

**Le cas réel.** Un exemple donné en conversation pour expliquer un principe a été consigné au journal des cas comme un incident survenu. **Quatre écrits s'y sont appuyés — dont la charte, qui tranche en cas de contradiction — pendant quatre jours**, et il a fallu que la personne qui avait donné l'exemple s'en souvienne pour que ça se voie.

**Ce qui le sépare du motif voisin.** *Un document montré n'est pas un document versé* porte sur un objet **qu'on n'a pas lu**; ici l'objet a été lu, parfaitement compris, et **rangé dans la mauvaise catégorie**. Un exemple pédagogique et un incident **se racontent avec la même grammaire** — un avant, un après, une leçon — et rien ne les distingue une fois qu'ils sont écrits.

**La règle. Ce qui prouve un fait n'est pas qu'il se raconte bien, c'est qu'il ait laissé une trace ailleurs** — un commit, une ligne en base, une sortie d'exécution. **Avant de consigner un incident, nommer cet artefact; si on n'en trouve aucun, c'est peut-être qu'il n'y a pas eu d'incident.** *C'est devenu une exigence du journal des cas.*

## Une procédure est une affirmation sur un état

**Une marche à suivre se relit comme un mode d'emploi, et c'est ce qui la rend dangereuse.** *(constaté
le 2026-09-11, journal, cas 32)* Elle contient pourtant une affirmation à chaque ligne : que le fichier
est déployé, que le chemin est celui-là, que l'interpréteur existe. **Rien dans sa forme ne signale
qu'elle suppose quoi que ce soit**, et son lecteur ne la relit pas — il l'exécute.

**Le cas réel.** Une procédure en trois étapes a été remise pour l'hôte, **commençant par un chemin
approximatif et appelant un outil qui n'y était pas** : il vivait sur une demande de fusion ouverte,
**écrite dans le même tour que la marche**. La chaîne ne déploie qu'au `push` sur la branche par défaut.

**Ce qui la sépare des occurrences voisines.** Un état présumé produit une conclusion fausse; une règle
écrite pour un objet absent produit une autorité sans objet. **Une procédure fausse produit un geste** —
elle est le seul des trois livrables qu'une autre personne exécute sans pouvoir le contredire.

**La règle. Avant de remettre une marche, vérifier ce qu'elle suppose déjà fait, et lire les chemins dans
la configuration plutôt que de mémoire.** *Et ne jamais écrire la procédure dans le même tour que le
changement qui la rend possible : la fusion n'a pas eu lieu, donc l'état non plus.*

## Le code peut déjà porter la décision qu'on croit prendre

**Le motif habituel est qu'un document vieillit pendant que le code avance. Celui-ci est l'inverse, et il
se voit moins.** *(constaté le 2026-09-11.)* Trois décisions écrites au corpus les 10 et 11 septembre
**existaient déjà dans le code, dans les mêmes mots, depuis des jours** : les libellés *Repéré / Aligné /
Sur mesure*, et la distinction entre un score interne et le palier affiché — *« score numérique interne,
quantifié en palier, jamais affiché tel quel »*, écrit à `docs/ARCHITECTURE.md` bien avant que la
spéc. 8.6 la formule. **Le corpus a été le dernier informé.**

**Ce que ça a failli coûter.** Les libellés ont été versés au corpus **comme s'ils étaient neufs**. Ils
concordaient — par chance. **S'ils avaient différé d'un mot, le corpus et le code se seraient contredits
sans que personne ne le voie**, chacun ayant l'air d'avoir raison chez lui, et l'écart serait apparu bien
plus tard, sur un libellé montré à un client.

**La règle. Avant d'écrire une décision de produit au corpus, chercher si le code y répond déjà.** S'il
répond : le corpus **enregistre** cette réponse, ou il la **remplace explicitement** — jamais il ne
décide dans l'ignorance de ce qui tourne. *Une décision prise deux fois séparément n'est pas une décision
confirmée, c'est une divergence en attente.*

## Qui repère qu'un document est devenu faux

**Repérer est une obligation, pas une courtoisie.** Un écart constaté se dit dans le tour où il est
constaté, même sans rapport avec ce qu'on faisait. Convenir de qui ÉCRIT dans un document ne dit rien
de qui REGARDE — et laisser cette ambiguïté valoir « je ne touche pas » revient à ne pas regarder.

**Le constat voyage avec sa proposition de texte.** Un signalement sans proposition fait porter le
travail deux fois; une correction sans signalement est une main dans le texte de quelqu'un d'autre.

**Quand une modification rend un document faux, corriger ce document fait partie de la modification.**
Pas d'un suivi, pas d'une demande ultérieure — de celle-là. Un suivi est une intention; une intention
ne tient pas un document à jour.

## Un document DEVIENT faux; une trace est RENDUE fausse

**La section précédente porte sur le temps** : le monde bouge, le texte reste, quelqu'un doit le voir.
**Celle-ci porte sur un geste** — un texte exact au moment où il est écrit, réécrit ensuite pour coller au
travail réel, et faux par cet acte même. *L'intention est bonne : décrire ce qui a été fait. Le résultat
est un registre qui date le travail au mauvais moment.*

**Une demande de fusion fusionnée est close.** Elle ne peut plus porter de travail, et la modifier ne fait
que la faire mentir — **et elle ment sur le seul point pour lequel on vient la consulter** : ce qui est
entré dans la base, et quand. **Une branche qui reçoit des commits après sa fusion appelle une demande
neuve, pas une réécriture.** *(journal, cas 35)*

**La distinction qui tranche : un document décrit un état, une trace date un événement.** Un document se
corrige dès qu'il devient faux — c'est une obligation, et c'est la section précédente. **Une trace ne se
corrige pas : elle se poursuit.** Ce qui manque à un procès-verbal s'ajoute au suivant.

**Le corollaire d'exploitation : une chaîne en succès ne prouve pas que le travail est parti.** Un
déploiement vert dit que **ce qui a été fusionné** est arrivé sur l'hôte; il ne dit rien de ce qui a été
écrit et jamais fusionné. *Devant un fichier attendu et absent sur l'hôte, comparer les deux têtes —
`git log base..branche` — AVANT de chercher une panne.* **Chercher une panne dans une chaîne qui a
fonctionné coûte plus cher que la vérification qui l'aurait évitée**, et ne rend jamais rien.

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

## Ce qu'un instrument doit déclarer — trois choses, et aucune ne vit dans sa documentation

*Écrit le 14 septembre 2026, après trois défauts de la même famille en quatre jours.*

**Sa PORTÉE — ce qu'il ne regarde pas.** Un instrument mesure ce pour quoi il a été construit; son zéro
ne dit rien du reste. *(journal, cas 33 — un rapport de coût exact rendait zéro pendant que le compteur
de l'hébergeur voyait 412 millions de lectures.)* **La portée s'écrit à côté de la sortie, jamais dans
une docstring** : sans quoi un zéro se lit comme une absence de coût.

**Sa PROVENANCE — d'où il a regardé.** Une sonde du 14 septembre interrogeait un datastore sans tri : il
rend les enregistrements **les plus anciens**, donc **29 champs remplis au lieu de 35**, et un champ
absent des vieilles lignes paraissait ne pas exister. *Un chiffre faux en est sorti — `amendment_date`
donnée à 0,2 % au lieu de 27,8 %.* **Ce qui a attrapé le défaut n'est pas une relecture : c'est d'avoir
mesuré deux fois le même objet.** *Deux mesures qui divergent sont un fait, même quand la conclusion ne
bouge pas.*

**Et les CAUSES qu'il énumère — qu'elles puissent s'appliquer.** `outils/reprise_champs_seao.py`
annonçait qu'une attribution sans signal veut dire *« hors fenêtre, filtre territorial, nom vide »*.
**Deux des trois étaient impossibles pour cette source**, et la mesure les a mises à zéro : le SEAO ne
déclare aucun `territoire` au registre, son connecteur ne pose jamais `region`, et 23 977 attributions
sur 23 977 portent un fournisseur nommé. **Une énumération de causes se lit comme une répartition
plausible** — elle oriente vers une explication fausse. *Le coût n'est pas le mot de trop : c'est la
décision qu'il aurait pu emporter.*

**Le membre inattendu de la famille : le poste d'observation.** Le 14 septembre, un répertoire de
`/opt/falkye/code/` porte 283 Mo écrits depuis un shell root — **et le service, lui, ne peut pas y
écrire** : `ProtectSystem=strict` remonte l'arborescence en lecture seule dans son espace de montage,
avant que la permission du fichier n'entre en jeu. **Une lecture prise hors du bac à sable ne conclut
rien sur l'intérieur.** *Vérifier depuis l'identité ET les protections du service, ou ne pas conclure.*

## Un filet n'est posé que lorsque son effet est observé

**Le fait.** Le 14 septembre, une procédure d'essai commençait par poser un filet, puis démarrait le
mécanisme à éprouver. **La commande qui posait le filet a refusé** — l'unité visée est un fichier réel,
et `systemctl mask` ne peut pas écraser un fichier. **La commande suivante a réussi.** L'essai a tourné
sans protection, et seule une lecture attentive du refus a évité qu'on attende la suite.

**Ce qui l'a rendu invisible : rien n'a échoué bruyamment.** Un refus, puis un succès. *Deux commandes
indépendantes tapées à la suite ne forment pas une procédure — il n'existe aucun point où l'échec de la
première empêche la seconde.*

**La règle. La vérification lit l'ÉTAT EFFECTIF de la cible, jamais le code de retour de la commande qui
l'a posé.** Et **l'étape protégée doit être structurellement inaccessible tant que la vérification n'a
pas répondu** : un script qui s'arrête, pas une consigne de vigilance. *(journal, cas 36.)*

**Le corollaire, parce qu'il s'est vérifié le même jour : un moyen d'essai déclaré impossible mérite
d'être réexaminé.** Ce document portait depuis le 9 septembre qu'éprouver un rattrapage de minuteur
revenait à provoquer l'envoi qu'on cherchait à empêcher. **C'était une propriété du montage d'essai, pas
du mécanisme** — une surcharge d'unité rend le déclenchement observable sans destinataire.

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

## Quatre règles nées de l'exploitation

**Un mécanisme automatique ne doit pas interrompre le travail; un geste humain mal formé, si.** Une
réconciliation que son fichier d'entrée peut tuer est inutile le jour où on en a besoin — elle saute,
compte et signale. Une déclaration humaine incomplète, elle, doit lever : c'est le seul moment où
quelqu'un est là pour la corriger.

**L'absence de mesure n'est pas une mesure nulle.** Zéro et « rien » ne se rangent jamais dans la même
valeur : un territoire calme où la source a répondu vaut `0`, une exécution tombée en route vaut `NULL`.
Même règle qu'un fichier vide contre un fichier introuvable — « rien à reprendre » et « je ne sais pas »
sortent différemment — et que le troisième des quatre états ci-dessus. **Un partiel comparé à une norme
se lit comme une chute.**

**Un instrument mesure ce qu'il a été construit pour mesurer; son zéro ne dit rien de ce qu'il ne regarde
pas.** *(journal, cas 33)* **Sa portée s'écrit à côté de sa sortie** — en tête ou en pied, avec les
chiffres — *et pas seulement dans sa documentation, que personne ne relit au moment de lire un résultat.*
Sans elle, un zéro se lit comme une absence de coût.

**C'est le VOISIN de la règle ci-dessus, et il faut les tenir séparées.** Là, l'instrument n'avait rien à
dire — absence de mesure contre mesure nulle. **Ici il a mesuré, exactement, et ailleurs** : le rapport de
coût a rendu trois zéros justes pour un cycle qui avait lu 412 millions de lignes par un chemin qu'il ne
compte pas. *Ni faux, ni muet : exact sur un périmètre plus étroit que celui qu'on lui prêtait.* **Le
défaut n'est pas dans l'instrument, il est dans ce qu'on a laissé croire qu'il couvrait.**

**Et une mesure partielle ne ferme jamais une question de total.** Trois chemins relevés un par un ne
disent pas ce qu'un cycle a coûté; un seul chiffre global le dit — d'où *relever le compteur de
l'hébergeur AVANT et APRÈS*, le seul qui ne dépende d'aucune hypothèse sur l'endroit où regarder. **Une
cause suffisante n'est pas une cause unique** : c'est ce raccourci qui a laissé trois jours à un
consommateur du même ordre de grandeur que celui qu'on venait de corriger.

**Le corpus s'écrit à la FIN d'une tâche, pas pendant — et ce qui doit y finir se dépose au fur et à
mesure dans un tampon du dépôt.** *(Méthode arrêtée le 11 septembre 2026, tenue sur le point 1 du plan.)*
**Deux raisons, et la première est une question de justesse, pas d'économie** : une entrée écrite **avec
le résultat en main** est plus juste qu'une entrée écrite avant. *Le cas 33 en est la démonstration — il a
été écrit le matin, avant la mesure du soir; son épilogue porte le chiffre qui en change la portée, et
D14 comme D37 auraient été écrites autrement à midi.* La seconde : une demande de fusion au lieu de cinq
allège un transport qui se porte à la main.

**Sa condition est non négociable, et c'est elle qui décide si la méthode tient** : la mise à jour de fin
de tâche porte **l'ensemble** des points, jamais ce dont on se souvient. *Une note différée qui se perd
est pire qu'une entrée écrite trop tôt — c'est le cas 15.* **D'où le tampon** — `NOTES-A-CONSIGNER.md`, à
la racine, hors corpus : chaque note s'y inscrit **datée, au moment où elle est prise**, le fichier se vide
en écrivant la mise à jour, et **une note oubliée se voit parce que le fichier n'est pas vide**. Même
principe que le journal de repli : *un endroit où ce qui risque de se perdre atterrit avant d'être
traité.*

**Le rappel est un AFFICHAGE, jamais un blocage**, et ce choix mérite d'être gardé avec son motif.
`verifier-corpus.py` imprime sous chaque passage le nombre de notes en attente et la date de la plus
ancienne — *une note sans date est comptée et signalée, jamais sautée.* **La version bloquante a été
écartée parce qu'elle aurait dû reconnaître une « fin de tâche », ce qui n'est lisible nulle part dans
l'arbre** : il aurait fallu une déclaration, donc une sortie nommée — **et toute sortie nommée finit
utilisée par réflexe.** *Un garde-fou qu'on peut contourner d'un mot rassure sans couvrir, ce qui est pire
que pas de garde-fou du tout.*

**L'exception : ce qui risque d'abîmer le produit s'écrit tout de suite.** Même test que pour un écart
hors plan.

**Une garde ne couvre que ce que la mesure couvrait.** *(journal, cas 34)* Étendre un correctif « par
symétrie » à un geste voisin — écrire et lire, créer et consulter, calculer et afficher — **demande sa
propre démonstration**, parce que le voisin a ses propres raisons d'exister. *Une mesure justifie un geste
précis; la cohérence apparente le fait glisser d'un cran, et le cran de trop retire en silence quelque
chose de légitime.*

## La clôture d'un point — les documents se mettent à jour DANS la même demande de fusion

> **Règle d'Alexandre, 24 septembre 2026.** *« Quand un point se termine, les documents qu'il touche se mettent à jour dans la même demande de fusion. Pas plus tard, pas dans une passe séparée. »*

**Ce qui l'a produite** *(journal, cas 43)* : le corpus du chantier 3+4 s'est arrêté au 17 septembre pendant qu'on travaillait dessus **six jours de plus**, et le tampon a franchi **269 notes**. *Les deux faits étaient visibles séparément et ne se rencontraient nulle part.*

**À la fin de chaque point, cinq gestes, et aucun n'est optionnel :**

1. **Dire quels documents le point touche, AVANT d'écrire, et ce que chacun doit recevoir.** *Une liste faite après coup est une liste de ce qu'on a pensé à toucher.*
2. **Signaler ce qui devient périmé ailleurs** — une ligne qui disait le contraire, un chiffre dépassé, une question désormais répondue. ⚠️ *Le corpus est la dernière source à porter une erreur qu'on a corrigée ailleurs* **(journal, cas 49)**.
3. **Inscrire les décisions au registre, tranchées et datées**, et faire passer à ✅ celles qui viennent de se fermer. *Relire le compte du registre fait partie du geste* — la phrase qui existe pour empêcher un compte périmé en a été un.
4. **Vider les notes du tampon qui concernent ce point**, plutôt que de les reporter.
5. **Si un document manque pour accueillir le contenu, le DIRE** — au lieu de le ranger au plus proche.

⚠️ **« Aucun document touché » est une réponse valable, et elle se dit.** *Un point qui ne touche rien et un point dont on a oublié la mise à jour se ressemblent exactement, et rien ne les distingue six jours plus tard.*

**Le témoin, et ce qu'il ne dit pas.** `verifier-corpus.py` imprime à chaque passage le nombre de notes en attente **et la date de dernière écriture de chaque document de chantier**, comparée à la note la plus récente du tampon. ⛔ *Sa première forme — dater un document par la date la plus récente qu'il ÉCRIT — a été écartée le jour même : elle rendait le 2 octobre sur le chantier 3+4, **une date à venir**. Un document parle aussi du futur; ce qu'il mentionne ne le date pas.* ⚠️ **Et le témoin retenu dit qu'un document n'a PAS été touché, jamais qu'il a été mis à jour pour de bon** — une retouche d'une virgule suffit à le rendre vert.

## Une règle qui descend d'un niveau change de geste, pas de principe

**Descendre une règle d'une passe par LOT vers une règle qui voit UN cas à la fois ne déplace pas ses gardes** — certaines arrivent dans un monde où une partie de leur décision est **déjà prise**. *La garde des prétendants refusait à TOUS les prétendants dans la passe; dans la résolution, le détenteur porte déjà le NEQ, et le lui retirer serait une écriture qui EFFACE une identité.* **La bonne question n'est pas « la même règle descend-elle ? » mais « que reste-t-il à décider quand elle arrive ? »** *(journal, cas 44; registre D61)*

⚠️ **Une constante qui descend peut perdre son pouvoir de décider sans perdre son nom.** *Le plus dangereux n'est pas qu'elle disparaisse : c'est qu'elle reste écrite au même endroit, avec le même nom, en ne gouvernant plus rien.*

**Et quand une règle perd la population qu'elle lisait, sa TRACE devient son organe de mesure.** *La passe comptait ses prétendants en les regardant; la résolution ne peut compter que ses propres refus consignés.* **Une trace qui sert à compter n'a plus le droit d'être approximative** — sa duplication n'est plus du bruit, c'est un faux chiffre.

⚠️ **Réutiliser une table, c'est hériter de ses leviers.** Avant de ranger un fait nouveau dans une structure existante, regarder **quelles commandes savent déjà agir dessus** — et vérifier qu'aucune ne fait, gratuitement, le contraire de ce qu'on vient de construire. *Un refus journalisé sous le statut `a_examiner` aurait offert, d'un coup de CLI déjà écrit, le moyen exact de défaire la garde.*

**Une garde bâtie contre une INFÉRENCE ne se transpose pas à une AFFIRMATION.** *Les appliquer toutes les deux « par prudence » coûte exactement ce que la prudence devait protéger.*

## Une mesure se lit sur la population qu'elle touche

**Le dénominateur d'une mesure de règle est la population où la règle s'APPLIQUE**, pas celle sur laquelle on l'a lancée. *Un pourcentage calculé sur des dossiers que la règle ne touche pas dit toujours « c'est négligeable », quelle que soit la règle.*

⚠️ **Un dénominateur relu d'une variable à la fin d'un long rapport dépend de tout ce qui a touché ce nom entre-temps.** *Le retenir au moment où on le connaît coûte une ligne* — le relire a coûté un **24 876,9 %**, visible seulement parce qu'il était ridicule. **Un pourcentage plausible ne se serait pas vu** *(journal, cas 48)*.

**Toute règle qui retire de l'information en récupère ailleurs**, parce qu'elle change l'ÉCART autant que le SOMMET. *Une mesure qui ne compte qu'un des deux côtés n'est pas incomplète : elle est orientée.*

⛔ **Et « récupérer » demande toujours PAR QUOI.** *Retenir davantage en VOYANT MOINS n'est pas une amélioration : c'est le défaut qu'on vient de corriger, remis à l'endroit.* **Un gain obtenu par ignorance n'est pas un gain**, et le solde de deux colonnes ne le dira jamais — il faut regarder le mécanisme *(registre D62)*.

**Une mesure qui simule une règle doit chiffrer le cas où la règle ne fait RIEN, et le montrer à celui qui lit.** *Un instrument sans témoin ne se distingue d'un instrument faux que par la confiance qu'on lui porte.* ⚠️ *Le test protège le dépôt; la ligne protège le lecteur du rapport, qui n'a pas la suite sous les yeux.*

⚠️ **Un chemin de SIMULATION qui n'hérite pas d'une règle du produit mesure une règle qui n'existe nulle part** *(journal, cas 47)*. **Et la phrase qui justifie l'exception vieillit sans bruit** : elle était vraie quand elle a été écrite, et elle reste écrite quand elle cesse de l'être.

## Une unité se tranche avant une valeur — et une population vaut mieux qu'une consigne

**Une valeur posée sur une unité qu'on n'a pas nommée n'est pas une échelle : c'est une convention cachée**, et elle se découvre le jour où un cas la traverse. ⚠️ *Et l'unité ne se choisit pas au jugé : elle se choisit sur le **cas qui sépare les candidates*** — celui qui fait dire « ces deux-là doivent être traitées pareil ». *`« L.A. »` se normalise en `« l a »` : trois caractères, deux lettres, deux mots — et c'est la LETTRE qui en fait la même porte que `« LA »` (registre D60).*

**Quand une décision dit « pas ça », la bonne question est : qu'est-ce qui, dans la FORME du code, rend « ça » impossible plutôt qu'interdit ?** *Une consigne se contourne en changeant un argument; une POPULATION ne se contourne qu'en réécrivant une requête* — c'est ce qui rend tenable, sans surveillance, la décision de ne jamais remplacer un NEQ déjà posé *(registre D63)*.

⚠️ **Un décor qui ne peut pas PRODUIRE la forme qu'il teste ne teste rien** *(journal, cas 46)*. **Quand une mesure rend « zéro » sur un décor, la première question n'est pas « la règle est-elle bonne ? » mais « le décor peut-il seulement produire un non-zéro ? »** *Une branche qu'aucun décor n'atteint est du code non testé sous une suite verte.*

**Écarter un élément d'un lot n'est pas neutre pour les autres.** *Retirer un candidat AVANT la résolution des collisions libère ce qu'il visait* — « écarter ce dossier » devient « en faire gagner un autre », ce que personne n'a demandé. **L'écart se place après**, pour que la seule conséquence soit celle qu'on a décidée. ⚠️ *Et un écart demandé qui ne portait sur rien se DIT* : un écart silencieux laisse croire qu'il a porté, et la passe suivante repose le dossier.

**La règle qui vient à l'esprit devant un cas a souvent déjà été mesurée sous un autre nom.** *(journal, cas 51)* ⛔ **Avant de proposer un axe, relire ce qui est fermé.** Reproposer une piste close sur un seul exemple la fait passer pour neuve — et lui fait retirer des appariements justes pour empêcher un cas dont la faute est ailleurs. *Une piste fermée garde son chiffre; c'est ce chiffre qui empêche de la rouvrir par réflexe.*
