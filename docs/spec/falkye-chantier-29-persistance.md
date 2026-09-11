# FALKYE — Chantier 29 : persistance de la base et hôte de production

*Mandat détaillé. La fiche courte est dans `falkye-audit-et-mandat.md`, qui tranche en cas de
contradiction. Le récit de l'incident fondateur est au journal des cas, n° 14.*


> **⚠️ Lire le glossaire en tête de `falkye-audit-et-mandat.md` avant ce document.** Cinq mots du corpus
> portent chacun deux sens ou plus — **état** (celui d'une source, chantier 1, contre celui du produit,
> chantier 29), **journal** (d'exécution, de diagnostic, de repli, d'exploitation, ou le journal des
> cas), **numéro contre rang**, **statut d'exécution contre état de santé**, et **chantier contre travail
> contre point**. *La contradiction du 7 septembre s'était logée dans le premier.*

> **Trois décisions ouvertes de ce chantier sont au registre unique**, en tête de
> `falkye-audit-et-mandat.md` : **D1** la résidence des données; **D10** où vivent l'historique et les
> quarantaines de diff; **D13** le comportement réel de la fenêtre de restauration.

**🟡 En cours. Trois gestes restent, et une question ouverte.** *L'infrastructure est vérifiée avec ses
preuves; l'activation du minuteur, le test de la fenêtre de restauration et la liste blanche de
l'hébergeur ne le sont pas — voir « Ce qui reste ». Ne pas résumer ce chantier par « tout est vérifié
sauf le minuteur » : c'est faux depuis le 8 septembre, et c'est le motif que ce document documente.*

### La contrainte qui a décidé de tout

**L'égress du conteneur est limité au port 443** — mesuré par connexion directe : 443 ouvert, les ports
d'une base classique, du courrier et de l'administration en délai d'attente. **Aucune base PostgreSQL
gérée n'est joignable**, et ce n'est pas une question de liste blanche : celle-ci s'applique aux requêtes
sur 443 et n'ouvre pas un port brut.

*Correction à conserver, sans quoi la bonne option serait rejetée pour un motif inexact à la prochaine
revue : ce n'est pas le dialecte SQL qui disqualifiait PostgreSQL — le projet ne contient qu'une seule
construction propre à SQLite. **C'est le port.***

**Décision : base gérée compatible SQLite, accédée en HTTPS.** Turso, organisation `altalogistic`, base
`falkye`, région `us-east-1`. **Palier Scaler depuis le 8 septembre 2026. Deux changements successifs :
Developer le 7 septembre, puis Scaler le 8** — les besoins étaient plus grands qu'estimé. Le second était
forcé par l'épuisement du quota de lectures ce matin-là. **Quotas et fenêtre de restauration : à lire sur
la fiche du palier Scaler, pas recopiés ici** — *un chiffre recopié est une promesse que personne ne
tient.*

**⚠️ Le passage au palier Scaler n'était pas planifié, et il est temporaire.** *Deux paliers franchis en
deux jours, ce qui est en soi l'information : l'estimation initiale était fausse d'un cran, puis de
deux.* Il a été forcé le
8 septembre au matin par **l'épuisement du quota de lectures** — un index unique sur le NEQ acceptant
8 395 NULL, chaque résolution d'entreprise non identifiée lisait 8 395 lignes deux fois. L'index
composite `ix_companies_neq_nom_normalise` a réduit la fuite sans la fermer : le repli par sous-chaîne
balaie toujours 8 396 lignes **sur la base durable, donc facturées**. **Le quota de lectures est le
chiffre qui manque à ce document**, et la décision de redescendre attend la ventilation du coût livrée au
chantier 2. **Elle mène au Developer, pas au palier gratuit** *(registre, D14)*.

### Le découpage produit / miroirs

**Au distant, ce qui ne se reconstitue pas** : entreprises, signaux, notifications, profils, journaux
d'exécution, historique et quarantaines de diff, journal de diagnostic, rétroaction, abonnements,
connexions CRM.

**En local, les miroirs reconstituables** : REQ, établissements, corporations fédérales, licences
municipales.

**Aucune clé étrangère ne pointe vers une table miroir**, ni aucune jointure SQL — vérifié. Le découpage
n'a donc demandé aucune réécriture de requête, seulement une seconde fabrique de session routée par
métadonnée.

**Les chiffres qui rendent la décision indiscutable.** Les miroirs représentent **99,95 % du volume et
zéro pour cent de ce qui se perdrait** : 5,7 millions de lignes reconstituables contre moins de 3 000
qui ne le sont pas. Et l'import du miroir prend **33 minutes en local contre environ 168 heures au
distant** — un rapport de 300, dû à deux allers-retours par ligne sur un chemin jamais optimisé.

*Ce chemin d'import reste à traiter, au chantier 27 : sans conséquence en local, mais la même forme
reviendra dès qu'un miroir devra vivre ailleurs.*

### L'hôte

**VPS-2 à Beauharnois, Debian 13, Python 3.13.5.** 4 cœurs, 8 Go de mémoire, 75 Go de disque, sans
engagement. Adresse `15.235.81.43`, point d'entrée public `lien.falkye.com`.

**Le dimensionnement à 8 Go était la condition de fonctionnement, pas une marge.** L'import du miroir
atteint **5,4 Go au groupe de contrôle** — le processus consomme 3 753 Mo, le noyau garde en plus les
pages des fichiers lus. Sur un modèle à 4 Go, l'import se serait fait tuer.

**Architecture des secrets, deux emplacements jamais mélangés.** *Dans le dépôt*, pour la chaîne de
déploiement seule : adresse de l'hôte, utilisateur dédié, clé privée, et **l'empreinte de la clé publique
du serveur** — celle qu'on saute d'habitude, sans laquelle le déploiement accepte n'importe quel serveur
répondant à cette adresse. *Sur le serveur*, dans un fichier en droits restreints : accès à la base, clés
d'envoi, clés de paiement et d'assistance IA.

**Deux raisons, dont une découverte en cours de route.** Une chaîne compromise peut redémarrer
l'application sans pouvoir lire la base. Et **une restauration de la base change son adresse et son
jeton** — les avoir sur le serveur permet de basculer sans commit ni redéploiement, au pire moment
possible.

**Règle permanente : cette machine n'envoie jamais de courriel directement.** L'envoi reste chez le
fournisseur dédié, sous son propre sous-domaine.

### Ce qui a été vérifié, avec sa preuve

| Élément | Preuve |
|---|---|
| Persistance de la base distante | Conteneur recyclé volontairement, 275 lignes durables retrouvées sans intervention |
| Découpage produit / miroirs | Codé et testé; un test verrouille la cible de chaque table dans les deux sens |
| Préparation de l'hôte | Utilisateur de service, répertoires, unités, permissions — validées commande par commande |
| Application en production | Service actif, sonde de santé positive, point d'entrée joignable en HTTPS depuis l'extérieur |
| Chaîne de déploiement | Passée au vert après la préparation |
| Miroir REQ chargé | 2 730 146 entrées, 40,7 min, **73,2 % d'entrées localisées** contre 6,6 % avant correctif |
| Cycle en régime | **29 min 10 s, huit sources sur huit en succès** |

### ⚠️ Le même code a trois régimes — l'erreur a été commise deux fois avant de le comprendre

| | Développement | Hôte, amorçage | Hôte, régime |
|---|---|---|---|
| Durée | 92,5 min | 1 h 26 | **29 min 10 s** |
| Processeur | 100 % | 22 % | **6 %** |
| Facteur dominant | le repli de résolution | la latence de la base | **l'enrichissement qui échoue** |

**Avant de conclure quoi que ce soit sur la lenteur d'un cycle, établir lequel des trois on observe.**

**Le chiffre qui compte n'est pas la durée totale.** Treize minutes d'ingestion, **seize minutes
d'enrichissement web qui échoue sur des refus** — la moitié d'un cycle est du temps passé à échouer. En
régime, le cycle ne calcule presque rien : il vérifie que rien n'a changé. **Le point 27.1 change donc de
nature et remonte dans l'ordre du chantier 27.**

### Le délai d'exécution du cycle

**⚠️ Il y a deux unités, pas une — et ce document l'ignorait jusqu'au 9 septembre 2026.**

| Unité | Délai | Ce qu'elle lance |
|---|---|---|
| `falkye-cycle.service` | **5 400 s** — 1 h 30 | Le cycle avec livraison |
| `falkye-cycle-sans-livraison.service` | **43 200 s** — 12 h | Le même cycle en observation |

**Les deux écrivent dans `SourceRunLog`.** *Correction du 9 septembre : ce document annonçait « quatre
valeurs » d'historique en additionnant les deux unités comme s'il n'y en avait qu'une. Il y en a trois
pour l'unité de livraison, et les douze heures appartiennent à l'autre — où elles sont toujours en
vigueur.*

**5 400 secondes pour l'unité de livraison** — facteur 3,1 sur la mesure réelle. La marge absorbe une
source lente, un portail en erreur, un trimestre neuf, ou un enrichissement redevenu fonctionnel donc
plus lent qu'un échec immédiat. Elle ne doit pas laisser un cycle bloqué mobiliser l'hôte une demi-journée
sans que rien ne le signale — **c'est le point où les deux erreurs coûtent à peu près pareil**.

*Historique des trois valeurs de cette unité, parce qu'il explique la méthode mieux que le résultat : une
heure ronde qui n'était pas une mesure (journal, cas 20), puis trois heures réglées sur l'amorçage —
l'erreur symétrique — puis le régime.*

**⚠️ Cette valeur a un deuxième consommateur depuis le 8 septembre**, et il lit aujourd'hui la mauvaise
unité pour la moitié des cycles. Le seuil de bascule d'une ligne d'exécution vers `interrompue` s'en
déduit : une ligne `en_cours` dont le `started_at` remonte à plus de `TimeoutStartSec` ne peut plus
tourner sous l'unité. **Mais `lance_par` enregistre « sous unité » ou « à la main » — jamais laquelle.**
Un cycle d'observation qui tourne depuis deux heures, ce qui est normal sous 43 200 s, serait donc
refermé en `interrompue` avec le motif « au-delà du délai de l'unité (5 400 s) » : **une ligne vivante
déclarée morte, avec une raison chiffrée qui se lit comme vérifiée.**

**Corrigé le 9 septembre au chantier 2** *(registre, D30)* : `lance_par` porte le
nom de l'unité, et le seuil se lit sur cette unité-là. *Ni le seuil maximal — ça rendrait la bascule
inutile sous l'unité de livraison — ni deux tables séparées : les deux cycles ont raison de partager
`SourceRunLog`, ce qui manquait c'est qu'ils s'y distinguent.* **Les lignes existantes restent non
décidables et ne se basculent pas rétroactivement.**

**Règle qui en sort :** un seuil déduit d'un réglage se lit sur **l'instance** qui a produit la ligne,
jamais sur une constante nommée d'après une seule d'entre elles. *`UNITE_CYCLE` avait l'air d'un
identifiant de catégorie et désignait une unité précise.*

**Changer l'un ou l'autre délai déplace donc aussi la frontière entre une exécution en cours et une
exécution interrompue** — la modifier sans le savoir rendrait la réconciliation fausse en silence.

### Ce qui reste

- ⬜ **Activer le minuteur — délibérément cette fois.** *Le premier déclenchement automatique a déjà eu
  lieu, sans témoin : le minuteur était armé depuis l'installation de l'hôte — `disabled` mais `active` —
  et il a lancé un vrai cycle avec livraison le mardi 8 septembre à 8 h **UTC**, soit 4 h 31 à Montréal.
  Le fuseau de l'hôte a été corrigé d'UTC vers `America/Toronto`; le minuteur est arrêté, **vérifié
  `inactive`**. Les cinq lectures à faire avant d'activer un minuteur sont à `docs/DEPLOIEMENT.md`,
  avec le point qui manquait : `disabled` ne veut pas dire arrêté, `enable` ne gouverne que le prochain
  amorçage, **seul `is-active` répond à la question qu'on posait**.*
  **Condition retenue : après le premier rapport de coût sur l'hôte**, pour ne pas laisser des cycles
  automatiques consommer un quota qu'on ne mesure pas encore. *Le rapport du 10 septembre a tourné mais
  n'a RIEN mesuré — zéro résolution, donc zéro coût de résolution. La condition n'est pas remplie.*

  ✅ **Le réarmement est fermé.** La ligne `systemctl restart falkye-cycle.timer` est retirée de la
  chaîne le 9 septembre, et le correctif est **vérifié sur la trace du déploiement 19** — le journal du
  travail montre le commentaire à la place de la commande. Le minuteur est arrêté, **revérifié
  `inactive` le 10 septembre**. *L'activation délibérée reste à faire, et sa condition ne change pas.*

  ⚠️ **Le 9 septembre, il était `active` de nouveau — et le mécanisme est identifié.** La chaîne de
  déploiement portait `systemctl restart falkye-cycle.timer`. **`restart` sur une unité arrêtée la
  démarre** : chaque fusion réarmait le minuteur, y compris après un arrêt délibéré et vérifié. La ligne
  est retirée le 9 septembre; l'activation redevient un geste, jamais un effet de bord. *La permission
  `sudo` correspondante subsiste sur l'hôte, inutilisée — à retirer au prochain passage en root.*

  ⚠️ **`Persistent=true` est le danger réel, et il n'est PAS testé.** Il rattrape un créneau manqué
  **immédiatement au démarrage du minuteur**. Tant que la ligne existait, un déploiement survenant après
  un mardi 8 h passé sans que le minuteur ait tourné ne réarmait pas seulement : **il déclenchait un
  cycle AVEC LIVRAISON sur-le-champ** — un courriel à un vrai destinataire, déclenché par une fusion,
  sans que rien ne l'annonce. Le 9 septembre rien n'est parti parce que le fichier d'horodatage couvrait
  le dernier créneau : **c'est le calendrier qui a protégé, pas le mécanisme.** Ce comportement ne sera
  pas vérifié — le tester consiste à laisser passer un mardi puis à déployer, c'est-à-dire à provoquer
  l'envoi qu'on cherche à empêcher. **Risque documenté et non traité, ce qui n'est pas un risque géré;
  un risque non documenté serait pire.** Le chemin est fermé tant qu'aucune commande ne démarre ce
  minuteur sans qu'on ait lu son fichier d'horodatage.
- ✅ **Fenêtre de restauration — testée le 10 septembre 2026, et la question s'est révélée mal posée.**
  Elle ne se mesure pas encore : **il n'y a rien à restaurer avant le 8 septembre**, date où commencent
  les données réelles du produit — le premier passage de données, tenté le 7, n'a pas abouti. La fenêtre
  couvre donc l'intégralité de ce qui existe, et **c'est ce qui a débloqué le point 27.9** : la
  suppression des huit copies vides avait son filet. **✅ Faite le 11 septembre 2026** — passage à blanc
  d'abord, puis les huit supprimées, aucune ne subsiste.
  *Trois essais : 5 septembre refusé (« pitr … is not available for the group »), 7 septembre refusé sur
  une **erreur interne du service — non concluant, ce n'est pas un verdict de fenêtre** —, 8 septembre
  accepté, base créée puis détruite.*
  ⚠️ **Ce qui reste inconnu, et doit le rester visible : on ne sait pas si la fenêtre fait trente jours en
  pratique.** Le refus du 5 ne mesure aucune durée — il dit qu'il n'y avait rien là. **On le saura quand
  le 8 septembre commencera à en sortir.**
  **Deux faits pour qui refait le test.** Il se fait **entièrement depuis l'interface web** — onglet
  `Branches`, `Create From Point-in-Time` — et le client de l'hébergeur n'est pas nécessaire. Et **le
  service refuse AVANT de créer** quand l'instant est hors fenêtre : les essais ne coûtent rien tant
  qu'ils échouent.
  ⚠️ **La fenêtre est portée par le GROUPE, pas par la base.** Le message de refus dit « not available
  for **the group** ». Le groupe s'appelle `default`. **Tout ce qui rejoint ce groupe hérite de la même
  fenêtre, et un changement de groupe la change pour toutes les bases qu'il porte.** *C'est le genre de
  fait qu'on découvre au mauvais moment.*
- ⬜ **Vérifier que les deux bases d'essai sont bien détruites** — `falkye-essai-restauration`, et
  `falkye-essai-2` si la seconde a été créée avant l'erreur. *À faire quand le site de l'hébergeur sera
  stable : deux essais ont donné des erreurs internes le matin du 10 septembre, et l'interface a perdu sa
  barre d'onglets. Une base d'essai oubliée compte dans le quota.*
- ⬜ **Un jeton d'API de plateforme, sur le poste d'Alexandre — et nulle part ailleurs.** *Remplace la
  ligne « ajouter le domaine d'API de l'hébergeur à la liste blanche », devenue fausse : le domaine passe
  déjà. Vérifié le 10 septembre 2026 depuis l'environnement de développement — `api.turso.tech` répond
  `401` avec les en-têtes du fournisseur, ce qui est un refus d'authentification et non un blocage
  réseau.*
  **Ce qui manque n'est pas un chemin, c'est un secret d'une autre nature.** `FALKYE_DB_AUTH_TOKEN` ouvre
  **la base** `falkye`; il ne dit rien du compte, des sauvegardes ni des autres bases — essayé, `401` lui
  aussi sur l'API de plateforme. Un jeton de plateforme, lui, peut **créer et détruire des bases**.
  **Il ne va donc ni dans le dépôt, ni sur l'hôte, ni dans l'environnement de développement.** L'hôte n'a
  besoin que de lire et écrire *sa* base : lui donner un jeton capable de la détruire élargit exactement
  la surface que l'architecture de ce chantier protège — *une chaîne compromise peut redémarrer le
  service, jamais lire la base*, et à plus forte raison jamais la supprimer. Vérifier l'état des
  sauvegardes est un **geste humain occasionnel** : il se fait en séance, depuis le poste, avec un jeton
  qui n'existe nulle part en permanence. *Et le test du 10 septembre montre que la vérification courante
  n'en a même pas besoin : l'interface web suffit.*

### ⚠️ Question ouverte — où vivent réellement l'historique et les quarantaines de diff

**Ce document les place au distant**, dans « ce qui ne se reconstitue pas ». **Le travail 1bis du
chantier 2 les a mesurés dans le fichier miroir local**, non facturés, aux côtés de `SourceRunLog` qui,
lui, est bien au distant. **Les deux ne peuvent pas être vrais ensemble.**

**Pourquoi ça compte.** Le chantier 1 existe parce que perdre l'état de diff, c'est perdre des événements
définitivement; le chantier 29 existe pour garantir que ce qui ne se reconstitue pas survit. **Si l'état
de diff vit hors de la base durable, cette garantie ne le couvre pas.** Et le point 27.9 s'explique alors
de lui-même : les copies vides de `diff_run_historique` et `diff_quarantaines` sur la base distante
étaient le résidu de l'intention décrite ici.

**⚠️ Ces copies ont été supprimées le 11 septembre 2026 (point 27.9), et la question reste entière.** Ce
qui change, c'est qu'**elle a perdu sa pièce à conviction** : on ne peut plus lire l'intention d'origine
dans le schéma de la base distante. *Elle reste tranchable autrement — le routage est déclaré par la
métadonnée des modèles, `falkye/db.py::get_sessionmaker` — mais le témoin matériel n'existe plus.*
**Noté parce qu'une décision destructrice prise pour une bonne raison a quand même retiré une preuve, et
que personne ne l'avait vu venir, moi le premier.**

**Ce qui tranche : le test qui verrouille la cible de chaque table dans les deux sens**, mentionné plus
haut. Soit il encode le placement local et ce mandat est périmé, soit il encode le distant et c'est la
mesure du chantier 2 qui est à revoir. **À vérifier avant de clore le chantier 29.**

### ⚠️ Écart de résidence des données

La base vit en Virginie, aucune région canadienne n'étant offerte. **Déclencheur de migration : la
décision d'ouvrir les inscriptions**, pour migrer à vide plutôt qu'avec des données de clients.

