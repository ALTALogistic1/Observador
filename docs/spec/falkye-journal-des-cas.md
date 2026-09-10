# FALKYE — Journal des cas

*Créé le 7 septembre 2026, en séparant les règles de leurs preuves. La charte garde les règles; ce document garde les incidents qui les ont produites, avec leur détail complet.*

**À quoi ça sert.** Une règle se lit et s'applique; un cas se cherche. Quand un motif semble se répéter, c'est ici qu'on vérifie s'il s'est déjà produit et sous quelle forme.

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

## Cas 16 — De A/B/C à A/AA/AAA *(charte, section 16)*

L'échelle de pertinence était A/B/C; elle est devenue A/AA/AAA. Le classement, l'ordre et les écarts sont identiques, et aucune information n'a été perdue.

Ce qui a été retiré, c'est **un jugement que le produit n'était pas en position de porter**. Dire « C » revient à dire à l'utilisateur que son opportunité est médiocre, alors que le moteur sait seulement qu'elle est **moins bien alignée que d'autres**. Le C ajoutait une information fausse; le A la retire sans rien inventer.

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
