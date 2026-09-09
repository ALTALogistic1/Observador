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
`falkye`, région `us-east-1`. Palier Developer depuis le 8 septembre 2026 — vingt-cinq millions d'écritures par
mois, et **fenêtre de restauration annoncée à dix jours par le fournisseur, comportement non vérifié**
*(voir « Ce qui reste »)*.

**⚠️ Le passage au palier Developer n'était pas planifié, et il est temporaire.** Il a été forcé le
8 septembre au matin par **l'épuisement du quota de lectures** — un index unique sur le NEQ acceptant
8 395 NULL, chaque résolution d'entreprise non identifiée lisait 8 395 lignes deux fois. L'index
composite `ix_companies_neq_nom_normalise` a réduit la fuite sans la fermer : le repli par sous-chaîne
balaie toujours 8 396 lignes **sur la base durable, donc facturées**. **Le quota de lectures est le
chiffre qui manque à ce document**, et la décision de redescendre de palier attend la ventilation du
coût livrée au chantier 2.

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

**Décision retenue le 9 septembre, à construire au chantier 2** *(registre, D30)* : `lance_par` porte le
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
  `inactive`**. Les quatre lectures à faire avant d'activer un minuteur sont à `docs/DEPLOIEMENT.md`,
  avec le point qui manquait : `disabled` ne veut pas dire arrêté, `enable` ne gouverne que le prochain
  amorçage, **seul `is-active` répond à la question qu'on posait**.*
  **Condition retenue : après le premier rapport de coût sur l'hôte**, pour ne pas laisser des cycles
  automatiques consommer un quota qu'on ne mesure pas encore.
- ⬜ **Tester la fenêtre de restauration** — **débloque aussi le point 27.9**, la suppression des copies
  vides sur la base distante étant une migration destructive, qui a besoin de ce filet contrairement à un
  index. Demander une restauration antérieure au changement de palier.
  Deux minutes, et la base d'essai se détruit ensuite puisqu'elle compte dans le quota. Tranchera si la
  fenêtre est rétroactive ou si elle s'accumule vers l'avant, question que la documentation du
  fournisseur n'aborde nulle part.
- ⬜ **Ajouter le domaine d'API du fournisseur d'hébergement à la liste blanche**, pour que l'état des
  sauvegardes soit vérifiable depuis l'environnement de développement.

### ⚠️ Question ouverte — où vivent réellement l'historique et les quarantaines de diff

**Ce document les place au distant**, dans « ce qui ne se reconstitue pas ». **Le travail 1bis du
chantier 2 les a mesurés dans le fichier miroir local**, non facturés, aux côtés de `SourceRunLog` qui,
lui, est bien au distant. **Les deux ne peuvent pas être vrais ensemble.**

**Pourquoi ça compte.** Le chantier 1 existe parce que perdre l'état de diff, c'est perdre des événements
définitivement; le chantier 29 existe pour garantir que ce qui ne se reconstitue pas survit. **Si l'état
de diff vit hors de la base durable, cette garantie ne le couvre pas.** Et le point 27.9 s'explique alors
de lui-même : les copies vides de `diff_run_historique` et `diff_quarantaines` sur la base distante
seraient le résidu de l'intention décrite ici.

**Ce qui tranche : le test qui verrouille la cible de chaque table dans les deux sens**, mentionné plus
haut. Soit il encode le placement local et ce mandat est périmé, soit il encode le distant et c'est la
mesure du chantier 2 qui est à revoir. **À vérifier avant de clore le chantier 29.**

### ⚠️ Écart de résidence des données

La base vit en Virginie, aucune région canadienne n'étant offerte. **Déclencheur de migration : la
décision d'ouvrir les inscriptions**, pour migrer à vide plutôt qu'avec des données de clients.

