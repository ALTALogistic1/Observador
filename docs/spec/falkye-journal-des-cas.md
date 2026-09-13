# FALKYE — Journal des cas

*Créé le 7 septembre 2026, en séparant les règles de leurs preuves. La charte garde les règles; ce document garde les incidents qui les ont produites, avec leur détail complet.*

**À quoi ça sert.** Une règle se lit et s'applique; un cas se cherche. Quand un motif semble se répéter, c'est ici qu'on vérifie s'il s'est déjà produit et sous quelle forme.

**Chaque cas nomme ce qui le prouve.** *Exigence posée le 11 septembre 2026.* Un commit, une ligne en base, une sortie d'exécution, une capture — **l'artefact qui existerait encore si personne ne se souvenait du cas**. Un cas qui n'en a aucun **porte la mention qu'il n'en a pas** : c'est une information sur sa solidité, pas un défaut à cacher.

**Ce qui l'a produite.** Le cas 16 racontait un incident qui n'a jamais eu lieu, et il a tenu lieu de précédent à quatre écrits pendant quatre jours. **Rien ne le distinguait des autres à la lecture** — un exemple pédagogique et un incident se racontent avec la même grammaire. *Un artefact nommé l'aurait rendu visible sans qu'on le cherche : il n'y en avait aucun à nommer.*

**L'exigence ne vaut que pour les cas à venir, et ce paragraphe est la mention des autres.** Les cas antérieurs au 11 septembre 2026 ont été écrits sans elle et **aucun ne porte d'artefact**. On ne reconstitue pas ce que personne n'a noté, et les réécrire de mémoire fabriquerait exactement le genre de preuve que cette exigence sert à empêcher. **Et rien ici ne dit que ces cas-là sont sains** : la vérification a été tentée le 11 septembre, **elle ne discrimine pas** — le test repère les cas sans chiffre vérifiable, et il remonte le cas 1 et le cas 17, qui sont parfaitement réels. *Mieux vaut le savoir que de croire qu'une passe l'a vérifié.*

**Chaque cas porte entre parenthèses la règle qu'il justifie et l'endroit où elle vit** — une section de la charte, le guide d'ingénierie, ou le cadre légal. *Les règles de vérification ont quitté la section 11 de la charte pour le guide le 7 septembre 2026, et les renvois ont suivi le 8.*

---

## Cas 1 — Cinq sources placées au mauvais palier *(charte, section 0)*

Cinq sources gratuites nouvellement vérifiées ont été placées dans les paliers supérieurs en appliquant une règle mécanique — « une source nouvelle est un enrichissement, donc au minimum Radar » — alors que la section 13 disait exactement le contraire pour ce cas précis.

Le raisonnement implicite était : « le palier d'entrée a déjà quatorze sources, c'est sûrement assez ». **Le nombre de sources a servi de substitut à la qualité des résultats.** Aucune donnée ne soutenait cette conclusion; elle avait simplement l'air d'un choix de produit.

**Ce que ça a révélé.** Un principe correctement écrit peut être contredit en pratique sans que personne ne s'en aperçoive. Un principe formulé comme une conviction ne se déclenche pas au moment de décider; formulé comme un test, il ne se déclenche pas davantage s'il n'a pas de valeur par défaut.

**C'est le cas fondateur de la section 0**, et la raison pour laquelle chaque test de la charte porte désormais sa réponse par défaut.

## Cas 2 — La mesure qui n'aurait rien mesuré *(charte, section 0, règle 3)*

Un premier envoi de courriel était sur le point de partir avant que l'authentification du domaine soit posée. Il aurait « mesuré » la délivrabilité — sauf que les deux issues induisaient en erreur.

Arrivé en boîte de réception, il aurait fait conclure que tout va bien alors que rien n'était éprouvé. Tombé dans les indésirables, il aurait fait accuser le contenu plutôt que l'authentification manquante.

**Une mesure prise dans de mauvaises conditions est pire que pas de mesure** : elle produit une conclusion fausse portée par la confiance d'un fait observé.

## Cas 3 — La vérification légale qui ne tenait qu'au Québec *(charte, section 7, test 5)*

La vérification obligatoire du statut légal avant présentation d'un prospect passe par le NEQ, qui n'existe pas hors Québec. La règle était donc soit inapplicable, soit silencieusement sautée — **deux façons de ne pas tenir la promesse.**

## Cas 4 — Trois solutions comparées sur le mauvais axe *(charte, section 8)*

Trois solutions de persistance ont été comparées sur leur coût de migration pendant qu'une contrainte non mesurée en éliminait une d'office : l'égress du conteneur était limité au port 443, donc aucune base PostgreSQL n'était joignable, quel que soit son coût.

La comparaison portait sur le mauvais axe, et le raisonnement invoqué contre l'option écartée — « plus lourd » — était inexact en plus d'être inutile. **Une option écartée pour la mauvaise raison sera un jour retenue pour la mauvaise raison aussi.**

## Cas 5 — Le signal qui n'existait pas *(charte, section 9)*

Un logiciel de gestion de recharge de flotte électrique n'avait a priori aucun signal direct. La recherche a révélé le Fonds pour le transport en commun à zéro émission, qui publie le nom de ses bénéficiaires.

**Démonstration en direct sur un cas jamais vu** : la méthode de diagnostic est un service humain autant qu'un outil, et un concurrent qui vend seulement l'accès aux données ne peut pas la reproduire.

## Cas 6 — L'assurance sans source *(charte, section 9, cinquième étape)*

La sphère assurance avait été déclarée sans source. Au niveau du champ, son besoin est déclenché par un changement d'exposition assurable — et **six champs déjà captés le portent** : capacité d'accueil, valeur de travaux, nouvel établissement, nature du bien mis en garantie, volume d'embauche, valeur de contrat.

Ce n'était pas « aucune source », c'était **« aucune source seule »** — la thèse même du produit. C'est ce cas qui a fait ajouter le diagnostic à rebours.

## Cas 7 — Ce que la vérification macro a trouvé *(guide d'ingénierie)*

La vérification contre les vraies sources a trouvé deux bogues qu'aucun test synthétique ne pouvait révéler, parce que les deux ne se manifestent qu'au volume réel et sur la vraie donnée.

Une insertion ligne par ligne qui faisait exploser la mémoire à l'échelle du miroir REQ — 2,7 millions de lignes, environ 9,6 Go, processus tué avant d'aboutir. Et environ 0,5 % des lignes réelles d'une source municipale portant une clé naturelle strictement dupliquée : un défaut du jeu de données lui-même, sur lequel le moteur plantait.

**Une suite verte ne dit rien du comportement au volume réel ni de la qualité de la donnée d'entrée.**

## Cas 8 — Trois défauts dans un module sans test *(guide d'ingénierie)*

Trois défauts réels vivaient dans le module du résumé périodique, dont un qui perdait définitivement une opportunité au premier échec d'envoi. Ils ont survécu à **483 tests verts** pour une raison simple : aucun de ces tests ne portait sur ce module.

**Le compte global rassurait sur une couverture qui n'existait pas là.**

## Cas 9 — Le même angle mort, au même endroit, le lendemain *(guide d'ingénierie)*

Après avoir ajouté des tests au module du résumé, une modification complète de l'objet du courriel et l'ajout d'une partie HTML sont passés sans qu'aucun des **586 tests** ne bronche : ni l'objet ni le rendu n'en avaient.

Le module avait été couvert sur ce qu'on venait d'y corriger, pas sur ce qu'il produit. **Ajouter des tests à un module ne le rend pas couvert.**

## Cas 10 — Les trois glissements du décidé au fait *(guide d'ingénierie)*

Trois écarts découverts le même jour, tous du même motif — quelque chose de décidé, mesuré ou écrit avait été pris pour quelque chose de fait.

**Le miroir REQ absent de la base de production.** Mesuré, pas supposé : 953 signaux réels ingérés sur 768 entreprises, zéro notification. Sans miroir, tout est « non trouvé », donc exclu avant le rapprochement. La chaîne déployée telle quelle aurait produit un silence hebdomadaire parfait, et rien ne l'aurait dit.

**Le découpage entre base du produit et base des miroirs.** Décidé, mesuré, jamais codé — constaté en tentant de charger le miroir. Aucune notion de base séparée n'existait dans le code.

**La préparation du serveur, jamais exécutée**, alors que le chantier qui la portait était marqué livré. L'utilisateur de service n'existait pas sur la machine, donc ni les répertoires ni les unités. **L'application n'avait jamais tourné sur cet hôte.**

**Aucun des trois ne se voyait dans le code ni dans les documents.** Les tests passaient, les mandats étaient clairs, les décisions consignées. Il a fallu taper une commande pour les découvrir.

## Cas 11 — Le geste d'installation fait trop tôt *(guide d'ingénierie)*

Des fichiers de configuration système ont été recopiés **avant** que le déploiement n'ait déposé leurs nouvelles versions. Le rechargement a réussi, l'unité a démarré, le cycle a tourné et s'est terminé en succès.

Il a simplement perdu les cinq sources que la correction devait sauver, et **rien ne l'a dit**. Le geste fait trop tôt ne rate pas : il réussit à vide.

## Cas 12 — Le commentaire qui justifiait une erreur *(guide d'ingénierie)*

Le repli sur l'adresse du domicile du registre avait sa condition **inversée**, et le commentaire qui l'expliquait affirmait le contraire de la documentation officielle du diffuseur. L'indicateur signifiait « dispensée de fournir l'adresse » — donc adresse absente — et c'était le seul cas où le code acceptait de lire.

**Résultat mesuré : 1 943 990 lignes portaient une adresse utilisable et n'étaient jamais lues.** Le miroir affichait 6,6 % de villes remplies au lieu de 73,2 %. Plus de neuf entreprises sur dix étaient invisibles à tout filtre territorial — **donc le rayon d'action, une des trois choses que l'utilisateur configure, ne servait à rien.**

**Deux protections ont manqué ensemble.** Aucun test ne parcourait cette branche, tous les décors passant par un autre fichier. Et un relecteur y aurait vu **une intention plutôt qu'une inversion**, puisque le commentaire lui donnait une raison.

## Cas 13 — Le remède qui coûtait plus que le mal *(guide d'ingénierie)*

Une erreur permanente au démarrage du serveur d'application venait d'une fonction inutilisée qui tentait d'écrire dans un répertoire volontairement protégé.

Le correctif évident — ouvrir ce répertoire en écriture — aurait rendu le répertoire du code modifiable par le service, **pour supprimer une ligne de journal**. La fonction a été retirée à la place : on ne s'en servait pas, et elle exposait une interface capable d'arrêter le service sur le seul chemin par lequel un désabonnement peut passer.

## Cas 14 — Le conteneur recyclé *(charte, section 14bis)*

Quelques heures après la rédaction du principe « l'accumulation ne vaut que si ce qui s'accumule survit », le conteneur de développement a été recyclé. **2,7 Go de base et l'archive de diff ont disparu** — état REQ importé, état du moteur pour toutes les sources rebranchées, historique de diff servant de base aux seuils, et la matière première que le chantier suivant devait apprendre.

Le code était intact, poussé, sans divergence. **Seules les données non versionnées ont été perdues.**

**Trois leçons, plus utiles que le principe seul.**

*Le risque avait été identifié et non traité.* La documentation technique du projet le décrivait mot pour mot, avec le chemin exact des fichiers concernés, avant qu'il se réalise. **Un risque documenté et non traité n'est pas un risque géré.**

*La sauvegarde manuelle n'était pas une solution.* L'export de secours a échoué à la livraison — trop volumineux, découpé en trente et un fragments, bloqué par un garde-fou. **Un filet qui demande une manœuvre à chaque session ne tient pas au-delà de la deuxième.**

*C'est arrivé au meilleur moment possible.* Quelques semaines d'accumulation perdues, sur des sources dont la plupart étaient en veilleuse, et une donnée pivot reconstituable depuis un fichier conservé hors de l'environnement. Le même incident six mois plus tard aurait coûté l'historique sur lequel reposent la densité, les normes et les taux de rejet. **Un incident qui valide un risque à faible coût est une information achetée bon marché — la gaspiller serait de ne rien changer.**

## Cas 15 — La décision budgétaire disparue *(charte, section 15)*

Une décision budgétaire réelle, portant sur un angle mort documenté depuis longtemps, a disparu du suivi pendant des mois avant d'être retrouvée par hasard en revue.

Elle n'avait été ni rejetée ni reportée — **elle était simplement restée sans réponse, et rien ne la faisait revenir.**

## Cas 16 — L'exemple donné en conversation, consigné comme un fait *(charte, section 16; guide d'ingénierie)*

**⚠️ Ce cas portait autre chose jusqu'au 11 septembre 2026, et ce qu'il portait n'a jamais eu lieu.** Il décrivait un passage de l'échelle de pertinence de `A/B/C` à `A/AA/AAA`. **Le produit n'a jamais eu de gradation `A/B/C`** — ni en service, ni implémentée, ni retenue puis écartée. C'était **un exemple donné en conversation** pour expliquer un principe : il faut des termes positifs pour tout ce que le client voit. **La règle existait avant l'exemple; elle n'en découle pas.**

**Ce que la consignation a produit.** La charte y a appuyé sa section 16 comme **cas d'origine**; les spécifications 8.1 y ont rattaché la justification des trois libellés; le relevé des objets gradués en a fait **le fait réel** qui avait forcé le grade de pertinence; et la section 16 elle-même s'en servait pour illustrer qu'une échelle emprunte le jugement de sa convention. **Quatre écrits ont pris appui sur un précédent qui n'existait pas**, et le plus ancien le faisait depuis la création de ce journal, le 7 septembre.

**Le mécanisme.** Ce journal ne consigne que des incidents réels — son en-tête le dit : *« la charte garde les règles; ce document garde les incidents qui les ont produites »*. Or **un exemple pédagogique et un incident se racontent avec la même grammaire** : un avant, un après, une leçon. Une fois écrits, rien ne les sépare à la lecture. **Et un exemple consigné comme un fait est plus solide qu'un fait** : il a été construit pour illustrer, donc il illustre parfaitement, donc rien ne vient jamais le mettre en défaut. *Un vrai incident laisse des traces ailleurs — du code, une base, un journal d'exécution. Celui-ci n'en avait aucune, et personne ne les a cherchées.*

**Ce que ça ajoute au cas 31, écrit le même jour.** Là, un **document** montré avait été traité comme versé. Ici, un **exemple** montré a été traité comme survenu. *Un document montré n'est pas un document versé; un exemple montré n'est pas un fait survenu.* **Même famille, deux objets** — et dans les deux cas le geste fautif n'est pas une lecture présumée, c'est **une écriture fondée dessus**.

**Pourquoi le numéro reste occupé.** Retirer le cas renumérote tout ce qui suit et casse chaque renvoi du corpus; le laisser vide fait aboutir les renvois existants sur rien. **Il porte donc désormais sa propre falsification**, et les cinq renvois qui pointaient vers lui apprennent en y arrivant pourquoi ils ne tiennent plus.

**Artefact.** `git log -S"A/B/C" --all -- '*.py'` **ne rend aucun commit** : aucune échelle de ce nom n'est jamais entrée dans le code, ni pour y être retirée ensuite. *C'est la vérification d'une seconde qui n'a pas été faite pendant quatre jours — et c'est elle qui a fait poser l'exigence d'artefact en tête de ce journal.*

**Ce qui a été corrigé avec.** La section 16 de la charte **assume d'être un principe sans cas d'origine** — la règle 4 appliquée à elle-même. Les spécifications 8.1 attribuent les trois libellés à la règle plutôt qu'à un changement d'échelle. Et au relevé des objets gradués, le grade de pertinence passe de « forcé par une décision » à **« forcé par rien »** : c'est la correction qui a le plus changé la lecture du relevé.

## Cas 17 — Le REQ non commercial *(cadre légal)*

Le jeu de données du Registraire des entreprises porte une licence **non commerciale et à partage identique**. C'est la source Piste du Québec, le pivot du produit — et celle dont personne n'avait vérifié la licence **parce qu'elle était là depuis le début**.

La règle sur la vérification légale avait été écrite en pensant à une source périphérique; le cas réel était au centre.

**Corollaire : vérifier en priorité les sources qu'on croit acquises.** Une source ajoutée récemment passe par le gabarit d'activation. Une source présente depuis l'origine n'y est jamais passée — c'est précisément là que se cache ce que personne ne pense à regarder.

## Cas 18 — L'avantage défendable qui était faux *(charte, section 19)*

L'affirmation initiale — « aucun concurrent n'a de raison de construire ça pour le Canada » — **était fausse**, et il a fallu la corriger après recherche : Deep Data et BidOps existent.

C'est le type d'erreur que la charte documente ailleurs, sauf que la section sur l'avantage défendable n'avait jamais reçu ce traitement. **Un avantage affirmé il y a un an et jamais revérifié est une présomption, pas un avantage.**

## Cas 19 — Le déversoir de trois cent six lignes *(charte, section 16)*

Le premier envoi réel a été refusé par le serveur du destinataire — détecté comme pourriel, rebond dur, jamais remis en file.

**Le message contenait 306 lignes toutes notées à l'identique, sans motif de repérage** — un déversoir plutôt qu'un résumé. Aucun filtre ne laisse passer ça d'un domaine neuf.

**Mais le plus grave n'était pas le refus : le produit croyait avoir livré.** Les 306 notifications étaient marquées incluses, zéro en attente, et elles ne repartaient jamais. Le rebond n'existait nulle part dans le produit.

**Et en posant le plafond, un second défaut est apparu.** Cent quatre-vingt-deux des 306 opportunités partageaient exactement le même score : l'ordre entre elles était donc celui du fichier source. Un plafond de dix posé là-dessus aurait livré **les dix premières lignes du fichier, chaque semaine** — un tri arbitraire promu en sélection, sans que rien ne le signale.

## Cas 20 — Le délai qui n'était pas une mesure *(guide d'ingénierie)*

Le délai d'exécution du cycle hebdomadaire était fixé à une heure. Le cycle mesuré prend **92,5 minutes**.

Le minuteur aurait donc tué le cycle à mi-parcours, chaque mardi. **Ce n'était pas une mesure, c'était une heure ronde.**

## Cas 21 — La source active qui ne pouvait rien produire *(charte, section 18)*

Une source d'offres d'emploi est restée **active** au registre pendant des semaines alors que sa limite était documentée : le fichier paraît avec environ un mois de retard, et les offres expirent plus vite que ce décalage — les identifiants qu'il porte sont déjà morts quand on les suit.

Elle tournait à chaque cycle, retournait zéro signal, et **gonflait le dénominateur du compte de sources en erreur**. Une source active qui retourne toujours zéro est indiscernable d'une source qui n'a rien trouvé cette semaine.

**L'information existait, écrite, dans le corpus.** Elle ne s'est pas rencontrée avec la ligne du tableau qui déclarait la source active — c'est le motif qui a motivé le ménage des documents.

## Cas 22 — Le minuteur qu'on croyait éteint *(guide d'ingénierie)*

Le minuteur du cycle hebdomadaire était armé depuis l'installation de l'hôte. L'unité était `disabled`
— ce qui gouverne le prochain amorçage de la machine — **et `active`**, ce qui gouverne maintenant.
Personne n'avait posé la question à `is-active`, la seule commande qui y répond.

Le mardi 8 septembre à 8 h **UTC**, soit **4 h 31 heure de Montréal** puisque le fuseau de l'hôte n'avait
jamais été changé, il a lancé un vrai cycle avec livraison. **Un second résumé, vide, est arrivé chez le
destinataire — même dossier que le premier, aucun rebond.**

**Ce que l'incident a vérifié gratuitement :** un résumé vide franchit les filtres, et la réputation du
domaine tient sur deux envois.

**Ce qu'il a révélé :** un cinquième état qu'on croyait éteint depuis le début du projet. Le fuseau a été
corrigé vers `America/Toronto` — sans quoi les envois seraient partis à 4 h du matin — et le minuteur
arrêté, **vérifié `inactive`**.

**La règle existait déjà.** Le cas 11 dit qu'un geste d'installation fait trop tôt ne rate pas : il
réussit à vide. C'en est la sixième forme. **Ce n'est pas une règle qui manquait, c'est une règle qui ne
s'est pas déclenchée** — le motif du cas 21.

**La commande qui tranche coûte dix secondes; la supposition coûte une journée.**

## Cas 23 — L'index unique qui trompait le planificateur *(guide d'ingénierie)*

La base a été bloquée le 8 septembre au matin, **quota de lignes lues épuisé**, après environ six cents
signaux neufs.

L'index sur le NEQ était **unique**, donc le planificateur croyait qu'il rendait une ligne. Mais **un
index unique accepte tous les NULL qu'on veut, et il y en avait 8 395** : chaque résolution d'une
entreprise non identifiée lisait 8 395 lignes, deux fois.

**Un index partiel, essayé d'abord, corrigeait l'égalité et pas le balayage par préfixe — et il se créait
sans erreur.** Un outil qui se serait contenté de « la commande a réussi » aurait déclaré la migration
faite. C'est pourquoi l'outil relit le plan d'exécution après coup et **sort en échec si les requêtes
retombent sur l'ancien index**.

**Correction à conserver, parce que l'erreur inverse a été commise en séance.** Le repli qui balaie
2,7 millions de lignes du **miroir** est lent et **jamais facturé** — le miroir vit dans un fichier
local. Le repli par sous-chaîne, lui, est rapide et **facturé** : il touche la base durable. **Les deux
se distinguent par ce qu'ils lisent, jamais par leur allure**, et associer « attente réseau » à « lecture
facturée » est faux dans les deux sens.

**Et un instrument manquait.** On mesurait la durée, la mémoire, les écritures — jamais les lectures.
**Un cycle peut être rapide, léger, huit sources sur huit en succès, et avoir consommé le mois.**

> **⚠️ Ce cas est vrai et il a été DÉPASSÉ le 11 septembre 2026 — voir le cas 33.** Tout ce qui est
> au-dessus tient : l'index unique, les 8 395 NULL, les deux lectures par résolution, la mesure. **Ce qui
> ne tient pas est la fermeture de la question** : cette cause était suffisante, elle n'était pas unique.
> Un second consommateur du même ordre — le chargement des signaux par entreprise, sur une colonne sans
> index — tournait le même jour et n'a été mesuré que trois jours plus tard, au compteur de l'hébergeur.
> *L'instrument qui manquait a bien été construit; il ne regarde que les trois chemins de résolution, ce
> que sa sortie ne disait pas.*

## Cas 24 — Le déclenchement dont la base ne pouvait pas garder la trace *(charte, section 17)*

Le même jour, un déclenchement de cycle à 14 h 17 UTC est tombé **pendant le blocage du quota**. Il n'a
donc pas pu écrire son propre échec : la base était injoignable au moment précis où il fallait consigner
qu'elle l'était.

**Ses deux lignes — début, puis échec avec sa cause — n'existent que dans le journal de repli**, un
fichier de l'hôte. En base, la ligne d'exécution est restée ouverte, **et elle ment** : un mécanisme qui
reconstruirait la vérité depuis la base conclurait que le run tourne encore.

**Premier cas où un mécanisme de secours gagne son existence par les faits**, et la raison pour laquelle
la réconciliation des lignes orphelines lit le journal de repli plutôt que la base. **Un compte qui
décrit une exécution ne se calcule jamais depuis la base que cette exécution écrit.**

**Conséquence de conception :** le journal de repli devient lu, donc **son format devient un contrat** —
et il reste le seul témoin des pannes où la base était muette. Une réconciliation qui le consommerait en
le détruisant supprimerait la preuve au moment où elle s'en sert.

## Cas 25 — Une garantie du modèle décrite comme une garantie de la base *(guide d'ingénierie)*

Le 8 septembre 2026, la réconciliation du journal de repli a été livrée avec cette affirmation : « le
marquage est `repli_id`, en index UNIQUE — deux reprises concurrentes se heurtent à la base plutôt que de
se fier chacune à une lecture faite juste avant. »

**L'unicité était bien déclarée au modèle**, et les tests, qui bâtissent leur base avec `create_all`, la
vérifiaient réellement. **En production, l'index n'existait pas.** La chaîne de déploiement posait les
colonnes et jamais les index d'une table déjà créée.

Ce qui a été livré n'était donc pas ce qui avait été annoncé, **et l'écart portait sur le chemin qui sert
quand la base est injoignable — au pire moment.**

**Le glissement :** *déclaré au modèle* est devenu *garanti par la base*, sans que rien ne se vérifie
entre les deux. Les tests ne pouvaient pas l'attraper, puisqu'ils construisent le schéma qu'ils testent :
**ils prouvaient la cohérence du code avec lui-même.**

**La règle.** Une garantie qui dépend d'un objet de schéma — index unique, contrainte, clé étrangère —
**ne s'affirme qu'après avoir vérifié que la base de PRODUCTION le porte**. Le modèle dit ce qu'on veut;
seule la base dit ce qui est. Et la commande qui tranche coûte dix secondes.

## Cas 26 — Le mode d'installation qui rendait l'essai incapable d'échouer *(guide d'ingénierie)*

**Le fait.** Le 9 septembre 2026, le flux de vérification de fusion a échoué à son tout premier passage
réel, sur `ModuleNotFoundError: No module named 'falkye'`. Le relevé de la révision de la demande ne
pouvait pas importer le paquet : lancer un script depuis `outils/` met ce répertoire sur le chemin de
recherche, jamais la racine du dépôt, et le paquet n'est pas installé dans le conteneur du flux.

**Ce qui rendait l'essai incapable d'échouer.** Le même outil avait été passé à blanc en développement,
où il donnait la bonne sortie. L'environnement de développement porte une **installation en mode
éditable** : l'import se résout depuis les paquets installés, quel que soit le répertoire courant, quel
que soit le chemin de recherche. **L'essai ne testait pas le chemin d'import — il testait un état de la
machine qui ne voyage pas.**

**Ce n'est pas un trou de l'outil, c'est un trou de la preuve.** L'outil faisait ce qu'on lui demandait.
Ce qui était faux, c'est ce que l'essai prouvait : *« ça marche »* voulait dire *« ça marche ici »*, et
rien de plus, sans que rien ne le signale.

**C'est la deuxième forme du test qui passe pour la mauvaise raison** — un état présent sur la machine —
**sauf que l'état était un mode d'installation, ce qui le rend invisible : il ne s'écrit nulle part**, ni
dans le code, ni dans la commande. Les trois autres formes se voient si on regarde; celle-là ne se voit
pas même en regardant.

**La règle.** Un mécanisme éprouvé dans l'environnement de développement n'est pas éprouvé, **parce que
cet environnement porte des états que rien d'autre ne porte.** Un essai n'y prouve un chemin d'exécution
que si l'environnement réel a été reproduit **sur le point précis en cause**. Sinon l'essai vaut comme
dégrossissage, pas comme preuve : le mécanisme reste **construit mais non validé en réel**, le troisième
des quatre états.

**Corollaire, et c'est ce que l'incident laisse de réutilisable.** Que le flux soit tombé à son propre
premier passage est ce qui pouvait lui arriver de mieux : **il s'est vérifié sur le seul cas dont la
réponse était connue d'avance** — lui-même, qui n'ajoutait rien au schéma — avant qu'on lui fasse
confiance sur une fusion qui, elle, aurait compté. **Faire tourner un nouveau mécanisme en conditions
réelles sur un cas dont on connaît déjà la réponse, avant celui dont on ne la connaît pas.**

## Cas 27 — La conformité accidentelle prise pour une garantie *(guide d'ingénierie)*

Le run de référence — première exécution d'une source, où toutes les lignes sont des apparitions —
**n'émet aucun signal**. Le moteur générique respectait la règle : zéro écart émis au premier run de
Toronto.

**Mais le filtre propre à ce connecteur portait sa propre notion de premier scan**, fondée sur un miroir
qui contenait déjà de l'historique. Il a émis des milliers de signaux réels. *Ce n'étaient pas de faux
signaux — mais rien n'empêchait qu'ils partent.*

**Le constat qui a suivi est le plus utile.** Deux autres connecteurs respectaient la règle **uniquement
parce que leurs compteurs y étaient câblés par hasard**. Ils passaient la vérification sans que rien dans
leur code n'exprime l'intention. **Une conformité accidentelle n'est pas une garantie** : elle disparaît
au premier changement, sans que rien ne le signale.

**La règle.** *Aucun connecteur ne doit avoir à vérifier lui-même qu'il est en run de référence — le
moteur refuse l'émission, quelle que soit la source du signal.* Plus généralement : **une règle portée
par la discipline de chaque appelant n'est pas portée.** Elle doit vivre à l'endroit qui ne peut pas être
contourné.

**Corollaire pour toute migration.** Quand un composant possède déjà un état accumulé, **migrer cet état
fait partie du rebranchement**. Laisser le mécanisme générique amorcer à vide pendant qu'un ancien
magasin porte de l'historique crée deux couches désynchronisées au premier appel.

## Cas 28 — Six cent quatre-vingt-quinze mille faux signaux au premier import *(charte, section 9)*

La calibration du registre des entreprises comptait **toute nouvelle immatriculation comme un signal**.
Au premier import, ça a produit environ **695 000 faux signaux**.

**La règle qui manquait tient en une phrase :** la toute première immatriculation n'est jamais un
signal — *une entreprise qui vient de naître n'est pas une entreprise **en** croissance.*

**Ce que ce cas ajoute aux autres.** Il ne s'agit ni d'un test qui passe pour la mauvaise raison, ni d'un
état présumé : la calibration faisait exactement ce qu'on lui avait demandé. **Ce qui manquait, c'est la
règle qui distingue le vrai signal du bruit administratif** — et c'est pourquoi la charte pose qu'aucune
source ne s'active sans elle. Un volume de cet ordre se remarque; **le même défaut sur une source à
faible volume serait passé inaperçu.**

## Cas 29 — L'empreinte complétée de mémoire au lieu d'être lue *(guide d'ingénierie)*

Le 9 septembre 2026, une fusion a été refusée en `409 Head branch was modified`. La branche n'avait pas
bougé : l'empreinte attendue avait été **complétée à partir des sept caractères courts affichés**, au lieu
d'être lue. Une valeur qu'on croyait connaître tenant lieu de la valeur qu'on n'avait pas lue — dix
minutes après que le même motif ait été écrit dans une demande de fusion.

**Ce que ça ajoute aux occurrences précédentes.** Les autres portaient sur un **état du système** présumé
plutôt que vérifié — un minuteur, un index, un schéma. Celle-ci porte sur une **valeur reconstituée** :
une forme abrégée est visible, le reste est complété par déduction, et **rien ne distingue à la lecture ce
qui a été vu de ce qui a été reconstruit**. Un identifiant tronqué, un numéro de version, un chemin abrégé
se prêtent au même geste.

**Ce qui l'a attrapée n'est pas la vigilance.** Le serveur vérifie l'empreinte attendue avant de
fusionner. Sans ce paramètre, la fusion passait sur une tête non confirmée. **Un garde-fou qui coûte un
paramètre a rendu inoffensif un défaut qui n'aurait laissé aucune trace.**

**La règle.** Une valeur tronquée à l'affichage **ne se complète jamais de mémoire — elle se relit à la
source**. Et quand une opération offre de vérifier la valeur attendue, on la lui passe : c'est le seul
moment où la reconstitution se voit.

## Cas 30 — La preuve fabriquée par l'instrument qui devait la recueillir *(guide d'ingénierie)*

Le 9 septembre 2026, deux outils lancés dans la même session root, sur le même hôte, ont rendu des
verdicts opposés sur le schéma de la base. `migration_colonnes.py` : **« Schéma à jour des deux côtés :
aucune colonne ni index manquant »**, code de sortie 0. `rapport_cout_cycle.py`, deux heures plus tard :
**quatorze colonnes manquantes**, dont `journal_exploitation.repli_id` — qu'un cycle venait pourtant
d'écrire, et **une colonne absente ne peut pas recevoir d'écriture**.

**Ni l'un ni l'autre ne disait à quelle base il parlait.** Le repli de `falkye/db.py` est silencieux et
**relatif au répertoire courant** : sur l'hôte, `/etc/falkye/falkye.env` n'est chargé que par les unités
systemd, jamais par un shell interactif. Une commande tapée à la main crée donc un fichier SQLite vide et
rend son verdict dessus, sans que rien ne le signale.

**Le vert était le pire des deux verdicts, et c'est ça le cas.** La comparaison saute les tables absentes
— *« create_all s'en charge »*, juste sur une base réelle qu'on étend. Sur une base vide, **zéro table
présente donne zéro colonne manquante** : l'outil bâti pour détecter ce qui manque annonce que rien ne
manque, précisément quand tout manque. Reproduit sur un fichier vide avant d'être refermé.

**Ce que ce cas ajoute aux précédents.** Les autres portaient sur une preuve **absente** — un état qu'on
n'avait pas lu — ou **périmée** — un fait vrai qui avait vieilli. Celui-ci porte sur une preuve
**fabriquée par l'instrument qui devait la recueillir**. Le vert était sincère : l'outil faisait
exactement ce qu'on lui demandait, sur la base qu'on lui avait donnée sans le savoir, et **il était
structurellement incapable de dire non**. Rien à corriger dans son raisonnement; tout à corriger dans ce
qu'il acceptait de juger.

**Et l'essai depuis l'environnement de développement ne pouvait pas le révéler** — `FALKYE_DB_URL` y est
toujours définie, donc le repli n'y existe pas. Cas 26, mot pour mot, sur une variable différente.

**Suite du 10 septembre — le même défaut, dans le mécanisme construit pour l'empêcher.** Le garde-fou
posé la veille ne lisait qu'une base sur deux : `FALKYE_DB_URL`, jamais `FALKYE_MIROIR_DB_URL`. Les
miroirs ont leur propre variable et leur propre repli relatif, tout aussi silencieux — un outil touchant
`diff_run_historique` ou `diff_quarantaines` rendait donc son verdict sur un fichier local vide **pendant
que l'en-tête affichait « cible choisie »**. La forme est celle du cas ci-dessus; ce qui manquait était
la **portée**.

**La règle qui en sort, et elle vaut bien au-delà d'ici :** *un garde-fou posé sur une ressource doit
couvrir TOUTES celles de sa catégorie, sinon il déplace le défaut au lieu de le fermer.* Deux bases dont
une seule contrôlée — et ça vaut pareil pour deux fichiers, deux chemins, deux comptes. **Un contrôle
partiel est pire qu'aucun** : il fait cesser de regarder ce qu'il ne couvre pas.

**Les deux règles, et la seconde est celle qui empêche.** Un outil qui juge ou modifie un schéma
**annonce sa cible en tête de sortie** — la cible lue, pas déduite; sans quoi deux verdicts opposés ne se
distinguent pas d'un désaccord de fond. Et **un outil de migration qui crée sa propre cible ne migre
rien, il fabrique** : il refuse de tourner sur un repli que personne n'a choisi, et refuse de rendre un
verdict vert sur une base où sa table témoin est absente. *Un verdict rendu sur une base vide est le plus
rassurant de tous.*

## Cas 31 — Le document montré pris pour un document versé *(guide d'ingénierie)*

Le 11 septembre 2026, un document commercial a été mentionné en conversation — existant, décrit, trois de
ses affirmations citées. **Il n'a jamais été versé au dépôt, et il ne devait pas l'être** : il n'était pas
une source, il portait des états périmés, et il avait été évoqué pour une raison sans rapport avec le
corpus.

**Ce qui a été fait sur la seule foi de cette mention.** Sa place dans l'arborescence tranchée, son chemin
écrit, trois règles rédigées pour lui, et **une clause de portée ajoutée à la charte qui le nommait** — la
charte, le document qui tranche en cas de contradiction. Le corpus a donc affirmé l'existence d'un
document que personne n'avait lu.

**Ce qui a rendu le glissement invisible.** Rien ne distingue, à la lecture d'une conversation, un
document **mentionné** d'un document **promis** d'un document **versé**. Les trois se nomment pareil. Et
le raisonnement sur sa place était juste — c'est ce qui l'a rendu convaincant : *un document hors du dépôt
n'est repéré par personne quand il vieillit* reste vrai, et ne dit rien sur l'existence de celui-là.

**Ce que ça ajoute aux occurrences précédentes.** Le motif portait sur un **état du système** présumé
*(cas 25)*, puis sur une **valeur reconstituée** *(cas 29)*. Ici l'objet non lu est **un document**, et le
geste fautif n'est pas une lecture présumée : **c'est une écriture fondée dessus**. Un état présumé produit
une conclusion fausse; une règle écrite pour un objet absent **produit une autorité sans objet**, et elle
survit plus longtemps parce que rien ne la contredit.

**Artefact.** Le commit **`c633c1e`** ajoute à `docs/spec/charte-falkye.md` la clause qui nommait le chemin du document; le commit **`d4cda09`** la retire. *`git log -S"presentation-commerciale" -- docs/spec/charte-falkye.md` rend les deux, et rien d'autre : le fichier n'a jamais existé.*

**La règle 5 s'applique aux documents autant qu'aux échelles, et elle a été enfreinte quatre tours après
avoir été écrite.** *Une source absente se signale, elle ne se légifère pas.*

**Ce qui a limité les dégâts, et ce n'est pas la vigilance.** Aucun fichier n'a été créé : le chemin n'a
été qu'écrit, jamais ouvert. **Et l'écart a été rapporté par la personne qui avait mentionné le document,
pas repérée par le corpus** — aucun mécanisme du dépôt ne peut voir qu'une règle parle d'un objet qui
n'existe pas. *Le vérificateur ne contrôle que les renvois internes; un chemin hors `docs/spec/` lui est
invisible.*

**La règle.** **Rien ne s'écrit au corpus sur la foi d'un document qu'on n'a pas lu** — pas une clause, pas
un chemin, pas une place dans l'arborescence. Ce qui se fait à la place : dire ce qui **s'appliquerait**,
sans nommer d'objet ni créer de fichier, et attendre que le document soit dans le dépôt. *Une règle
formulée d'avance garde sa valeur; une règle qui nomme un objet absent affirme son existence.*

## Cas 32 — La marche donnée sur un état jamais vérifié *(guide d'ingénierie)*

Le 11 septembre 2026, une procédure d'exploitation en trois étapes a été remise pour exécution sur
l'hôte. **Elle commençait par `cd /opt/falkye`, et le fichier qu'elle appelait n'existait pas sur
l'hôte.**

**Deux erreurs dans le même geste, et la seconde est la grave.** Le chemin réel est `/opt/falkye/code` —
approximation, rattrapable. Mais surtout : **l'outil était sur une demande de fusion ouverte, non
fusionnée**, et la chaîne ne déploie qu'au `push` sur la branche par défaut. **La marche a été écrite
dans le même tour que la demande de fusion qui la rendait possible.**

**Ce qui l'a rendue invisible.** Une procédure se relit comme un mode d'emploi, pas comme une
affirmation. Or **elle en contient une à chaque ligne** : que le fichier est là, que le chemin est
celui-là, que l'interpréteur existe. *Rien dans sa forme ne dit qu'elle suppose quoi que ce soit.* La
question qui l'a démasquée n'est pas venue d'une relecture — elle est venue de quelqu'un qui avait
regardé l'hôte.

**Ce que ça ajoute au motif.** *« Une valeur qu'on croit connaître tient lieu de la valeur qu'on n'a pas
lue »* portait sur un état du système *(cas 25)*, une valeur reconstituée *(cas 29)*, un document
*(cas 31)*, un exemple *(cas 16)*. **Ici l'objet présumé est l'état de la cible d'une procédure**, et le
livrable fautif n'est ni une conclusion ni une écriture : **c'est une instruction que quelqu'un
exécutera**. Les précédents produisaient une croyance fausse; celui-ci produit **un geste**.

**Artefact.** `deploiement/falkye-cycle.service` porte `WorkingDirectory=/opt/falkye/code` et
`.github/workflows/deploiement.yml` envoie vers `:/opt/falkye/code/` — la marche disait `/opt/falkye`.
Et la demande de fusion nº 31, qui portait l'outil, a été créée dans le même tour que la marche et
fusionnée seulement après.

**La règle. Une procédure est une affirmation sur un état, et elle se vérifie comme telle avant d'être
remise.** *Vérifier d'abord ce qui doit déjà exister — le déploiement fait, le chemin lu dans la
configuration plutôt que de mémoire — puis l'écrire.*

## Cas 33 — L'instrument juste dont la portée était plus étroite qu'on croyait *(guide d'ingénierie)*

Le 11 septembre 2026, un cycle `--sans-livraison` a tourné 28 min 23 s sur l'hôte, huit sources en
succès. **Le rapport de coût a rendu zéro sur les trois chemins de résolution, `~0` ligne dérivée, « le
repli par sous-chaîne n'a pas été emprunté ».** Le compteur de l'hébergeur, relevé avant et après le même
cycle, a rendu **411 963 777 lectures**.

**L'instrument ne mentait pas.** Il compte les trois chemins de résolution d'identité, il les compte
exactement, et aucun n'a été emprunté — il n'y avait rien de neuf à résoudre. **Le consommateur était
hors de sa portée**, et rien dans sa sortie ne le disait.

**La cause, relevée dans les requêtes les plus coûteuses de l'hébergeur :** un chargement des signaux
d'une entreprise, **une requête par entreprise**, sur `signals.company_id` **qui ne porte aucun index** —
donc un balayage complet de la table à chaque appel. Appelé une fois par entreprise dans **deux**
balayages complets de `companies` : la détection d'expansion inter-provinciale, puis la génération des
notifications.

**Artefact — compteur de l'hébergeur, encadrant le cycle :**

```
avant : 2 142 022 521 lectures — 2 237 266 écritures
après : 2 553 986 298 lectures — 2 237 294 écritures
```

**Artefact — requêtes les plus coûteuses, même intervalle :**

```
SELECT signals.id, signals.company_id, … FROM signals WHERE ? = signals.company_id
    Average Rows Read : 17 800   Count : 23 100   Avg time : 2,78 ms
SELECT … FROM companies (sans filtre)               11 600 lignes  ×2
```

23 100 × 17 800 ≈ 411 millions — **l'écart mesuré au compteur, à moins d'un pour cent.** Et
23 100 ≈ 2 × 11 550 : une lecture des signaux par entreprise, dans chacun des deux balayages.

**Ce que ce cas ajoute aux précédents, et c'est une forme neuve.** Le cas 30 portait sur **une preuve
fabriquée par l'instrument qui devait la recueillir** — l'outil jugeait une base vide et son vert était
structurellement incapable de dire non. Ici **l'instrument est juste, sa sortie est exacte, et il n'a
aucun défaut à corriger** : *sa portée est simplement plus étroite que ce que sa sortie laissait croire.*
Un zéro exact sur le mauvais périmètre.

**Et ce n'est pas « l'absence de mesure n'est pas une mesure nulle » non plus** *(guide d'ingénierie)*.
Ce zéro-là n'est ni un `NULL` ni une exécution manquante : **c'est une vraie mesure, de quelque chose
d'autre.** La règle voisine ne l'attrapait pas.

**Ce que ça a coûté de plus, et qui est le vrai prix.** Le diagnostic du 8 septembre avait attribué
l'épuisement du quota à l'index unique sur le NEQ — **mesuré, réel, suffisant à lui seul**, et la question
s'est refermée là-dessus. Ce second consommateur tournait le même jour, du même ordre de grandeur, et
**n'a jamais été mesuré** : le code est antérieur au 8 septembre. *Ce qui a rendu l'écart invisible n'est
pas une erreur de raisonnement — c'est que `rows_read` avait été relevé requête par requête, sur les
trois chemins qu'on soupçonnait, jamais sur le TOTAL du cycle.* **Une cause suffisante n'est pas une
cause unique.** Un total l'aurait dit tout de suite; trois mesures partielles, jamais.

**Ce qui a fini par le voir :** le compteur de l'hébergeur, relevé **avant et après** — le seul chiffre
de la journée qui ne dépendait d'aucune hypothèse sur l'endroit où regarder.

**Épilogue mesuré — le soir du 11 septembre 2026.** Un index posé sur `signals.company_id`, un cycle
comparable, le compteur relevé des deux côtés : **411 963 777 → 120 311 lectures. Divisé par 3 424.** La
requête qui dominait les requêtes les plus coûteuses n'y figure plus, et celle qui la remplace lit
**2 lignes par appel au lieu de 17 800**. *Le correctif a coûté ~17 824 écritures facturées, une fois — la
construction de l'index, lisible dans l'écart des compteurs d'écriture.* **Le plus gros poste de la
journée est devenu la commande de mesure elle-même**, pas le cycle.

**Et une arithmétique qui soutient le « vraie et incomplète », sans le prouver.** Sur la fiche du palier
Developer **lue le 11 septembre 2026**, le quota mensuel de lectures se compte en **milliards**. Si ce
chiffre valait déjà le 8 septembre — *ce qu'une fiche d'aujourd'hui n'établit pas d'hier* — alors les
~1,2 milliard de lectures des trois passages de l'EIMT ne l'épuisaient pas à eux seuls, et **il fallait
bien un second consommateur du même ordre**. *Cohérent avec le constat, pas une preuve : c'est une lecture
d'aujourd'hui appliquée à hier, et elle est marquée comme telle.*

**La règle. Un instrument mesure ce qu'il a été construit pour mesurer; son zéro ne dit rien de ce qu'il
ne regarde pas.** *Sa portée s'écrit à côté de sa sortie, pas dans sa documentation* — sans quoi un zéro
se lit comme une absence de coût. **Et une mesure partielle ne ferme jamais une question de total.**
*Précédent à imiter : `outils/schema_de_la_fusion.py`, qui annonce dans sa sortie qu'il ne sait rien de
la dérive déjà présente en production.*


## Cas 34 — La garde trop large, arrêtée par les tests qui existaient déjà *(guide d'ingénierie)*

Le 11 septembre 2026, après la mesure, une garde a été posée sur la détection d'expansion
inter-provinciale : **moins de deux provinces au registre actif ⇒ la passe ne s'exécute pas.** Elle était
justifiée et mesurée — une seule source active porte une province, aucun lien ne peut exister, et
`provenance_entreprises.py` avait confirmé **0 entreprise sur 11 556** venant des trois sources
provinciales en veilleuse.

**Elle a été posée aux DEUX points d'appel.** Le second — `evaluer_pour_company` — lit les liens d'une
entreprise pour lui accorder un bonus de confiance. **Trois tests existants sont tombés immédiatement** :
un lien **déjà en base** cessait de donner son bonus dès que le registre ne pouvait plus en créer de
nouveau.

**Ce que la garde confondait.** *Ne plus CRÉER et cesser de LIRE sont deux gestes différents.* Le premier
est un non-geste démontré : rien ne peut naître, donc ne rien tenter ne retire rien. Le second retirerait
**en silence une observation légitime déjà acquise** — et le silence est exactement la forme que ce projet
passe son temps à fermer.

**Le motif qui l'avait rendue tentante était déjà tombé.** La lecture coûtait cher parce que
`liens_interprovinciaux.company_id_b` n'était pas indexé; l'index posé une heure plus tôt la fait lire
deux lignes. *Ce qui restait à retirer était la PASSE, pas la lecture* — et une garde posée « tant qu'à y
être » élargissait son emprise au-delà de ce qu'elle avait mesuré.

**Pourquoi ce cas vaut d'être écrit alors que rien n'a cassé en production.** Le correctif a tenu
**quarante minutes**, dans une seule session, et la base réelle ne porte aucun lien — l'effet aurait été
nul. **C'est la forme qui compte** : une mesure justifie un geste précis, et le geste s'étend d'un cran
par cohérence apparente. *La mesure couvrait un des deux points d'appel; la garde a couvert les deux.*

**Ce qui l'a arrêtée n'est ni une relecture ni un raisonnement** — c'est une suite de tests écrite avant,
pour une autre raison, qui affirmait qu'un lien en base donne un bonus. **Un test qui tombe sur un
changement qu'on croit inoffensif est le seul mécanisme qui parle plus fort que la conviction de celui qui
l'écrit.**

**La règle. Une garde ne couvre que ce que la mesure couvrait.** *Étendre « par symétrie » à un geste
voisin — écrire et lire, créer et consulter, calculer et afficher — demande sa propre démonstration, parce
que le voisin a ses propres raisons d'exister.*
