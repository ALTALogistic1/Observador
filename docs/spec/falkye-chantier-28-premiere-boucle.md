# FALKYE — Chantier 28 : la première boucle complète

Mandat destiné à Claude Code.

> **⚠️ Lire le glossaire en tête de `falkye-audit-et-mandat.md` avant ce document.** Cinq mots du corpus
> portent chacun deux sens ou plus — **état** (celui d'une source, chantier 1, contre celui du produit,
> chantier 29), **journal** (d'exécution, de diagnostic, de repli, d'exploitation, ou le journal des
> cas), **numéro contre rang**, **statut d'exécution contre état de santé**, et **chantier contre travail
> contre point**. *La contradiction du 7 septembre s'était logée dans le premier.*


---

## Pourquoi ce chantier existe, et pourquoi il passe avant le reste du socle

FALKYE détecte, score, accumule un dossier cumulatif et sait ce qu'il ferait d'une opportunité. Mais
**la chaîne complète n'existe nulle part de bout en bout** : rien ne va de « je m'inscris, je décris mon
service, je donne mon courriel » à « je reçois quelque chose ».

Le morceau manquant est petit. L'authentification est construite et validée, l'assistance de
configuration existe à deux niveaux, le lien sphère↔service pondéré est livré. Ce qui manque est le
**fil** entre les deux.

**Ce qu'il débloque, et qui vaut plus que le code qu'il demande.** La veille continue par notification
est nommée comme l'un des trois avantages défendables du produit. Un avantage qui n'a pas de canal pour
exister est une intention. Et surtout : tant qu'une boucle ne tourne pas, chaque décision produit est
de la conception d'avance plutôt qu'une correction observée. Une trentaine de décisions ont été prises
ces derniers jours sans qu'aucune mesure n'existe pour les départager.

---

## ⚠️ Préalable bloquant — un hôte, avant tout code

**Constat du 4 septembre 2026 : il n'existe aucun serveur HTTP dans le produit.** FALKYE est un outil en
ligne de commande de bout en bout. Trois éléments de ce chantier en exigent un, publiquement joignable
en HTTPS :

- **le désabonnement en un clic** (RFC 8058), qui demande une URI `https://` interrogée en POST par le
  fournisseur de courriel — sans point d'entrée, pas de un-clic, et le mandat exige qu'il soit
  fonctionnel et non décoratif;
- **la rétroaction depuis le courriel**, dont le lien doit atterrir quelque part;
- **l'ordonnanceur**, moins strictement — une tâche planifiée suffit, mais il lui faut un hôte qui
  tourne quand personne ne le demande.

**Ce chantier ne démarre pas avant que l'hôte soit tranché** (chantier 29, qui porte maintenant les trois
besoins : tâche planifiée, point d'entrée HTTPS, base distante).

**Repli sur le désabonnement, à connaître sans s'en contenter.** La forme ancienne
`List-Unsubscribe: <mailto:...>` ne demande aucun point d'entrée et reste largement honorée — mais ce
n'est pas le un-clic du RFC 8058, elle ne satisfait donc pas l'exigence de Gmail et Yahoo, et la traiter
suppose de **recevoir** du courriel, sur des ports eux aussi bloqués. Ce serait manuel. Repli à échéance,
jamais solution.

## La règle de portée, à respecter strictement

**Construire la version brute, pas la version décrite dans les documents.** Les spécifications
décrivent le raffinement de plusieurs mécanismes — cadence configurable, fenêtre de 10 h, groupement
avec exception, narratif par gabarit, archivage, plafond d'antériorité, trois dimensions de statut.
**Rien de tout ça n'entre dans ce chantier.** Ces décisions restent au registre comme intentions datées
et attendent qu'il y ait quelque chose à raffiner.

Si une décision documentée simplifierait le travail, l'appliquer. Si elle l'alourdit, la laisser.

---

## Phase 0 — Constat avant de coder

À rapporter avant d'écrire autre chose.

1. Ce qui existe déjà du profil utilisateur : quels champs, jusqu'où va la configuration, ce qui manque
   pour qu'un humain crée le sien de bout en bout.
2. S'il existe déjà un moyen quelconque d'envoyer un courriel dans le produit, même partiel.
3. S'il existe un ordonnanceur, ou si les exécutions sont uniquement déclenchées à la main.
4. **Où le produit tournerait quand personne ne le demande.** La veille continue exige quelque chose qui
   s'exécute chaque semaine, tout seul. Si rien n'existe pour ça aujourd'hui, le dire — c'est la même
   question que la persistance, vue sous un autre angle, et il vaut mieux ne pas la payer deux fois.
5. **L'état du canal d'envoi**, sachant que SMTP est inutilisable ici : ce qui existe dans
   `email_channel.py`, ce qui se réutilise tel quel, et ce que la bascule vers une API HTTPS demande
   réellement.

---

## Ce qu'il faut construire

**1. Un profil complet, créé par un humain pour lui-même.** Description du service, sphère et
territoire, adresse courriel. Une seule sphère suffit. Le point d'entrée conversationnel existant
(`profile configurer-besoin` ou équivalent) est réutilisé tel quel — ne pas en construire un second.

**2. Un envoi réel.** Un courriel qui part vers une vraie adresse, avec les opportunités détectées et,
pour chacune, le motif du repérage tiré de la structure de faits. Groupé en un seul envoi. Pas de
gabarit élaboré, pas de mise en forme travaillée : du texte lisible.

**⚠️ Contrainte mesurée le 4 septembre 2026 : l'envoi SMTP est impossible dans cet environnement.**
L'égress est limité au port 443 — le port 587 est en délai d'attente, comme 5432 et 22, et **aucune
liste blanche de domaines ne l'ouvre**. Le canal `email_channel.py` qui utilise `smtplib` ne peut pas
fonctionner ici.

**L'envoi passe donc par une API d'envoi en HTTPS** — Postmark, Resend, SendGrid ou équivalent. Ça ajoute
un domaine à autoriser, un compte à créer, et une réécriture modeste du canal d'envoi.

**Ce n'est pas un détail de plomberie.** La valeur entière de FALKYE est livrée par courriel : un lot qui
atterrit dans les indésirables est un produit qui ne fonctionne pas, quelle que soit la qualité de la
détection. Le choix du fournisseur se fait sur la délivrabilité, pas sur le prix.

**Fournisseur retenu : Postmark** (`api.postmarkapp.com`), Resend en second si Postmark bloque.
Raisonnement : un petit expéditeur n'a pas de réputation propre, il hérite de celle du parc partagé — une
IP dédiée sous-utilisée serait jugée plus sévèrement qu'une bonne IP partagée. Le critère qui départage
devient donc la sévérité avec laquelle chaque fournisseur surveille son propre parc, et Postmark est le
plus regardant.

**Piège à éviter dès l'inscription :** un résumé hebdomadaire est une **diffusion**, pas du transactionnel.
Postmark sépare les deux en flux distincts sur des IP distinctes et prend la distinction au sérieux. Le
déclarer en flux de diffusion dès le départ — une suspension au lancement coûterait infiniment plus que
l'écart entre les deux flux.

### ✅ État au 5 septembre 2026 — deux livrables déjà réglés hors développement

**Compte Postmark créé**, en mode test, approbation à demander avant tout envoi réel vers des
destinataires externes. C'est aussi le moment où la distinction entre flux transactionnel et flux de
diffusion sera examinée.

**Domaine d'envoi `avis.falkye.com` vérifié** — DKIM et Return-Path posés dans la zone DNS de
`falkye.com` chez le registraire, et validés par Postmark. Le domaine racine n'est pas utilisé, et
`falkye.ca` reste hors de tout envoi.

**Deux constats à retenir de cette étape.**

*SPF n'est plus requis.* Postmark le gère lui-même et ne demande plus d'enregistrement dédié. Un
livrable de moins.

*Un enregistrement DMARC existe déjà*, posé automatiquement par le registraire — **en `p=quarantine`**,
pas en `p=none` comme la recommandation initiale le prévoyait. C'est plus strict : les serveurs
destinataires sont invités à mettre en quarantaine ce qui échoue à l'authentification. Sans conséquence
maintenant que DKIM est vérifié, mais **ça renforce l'interdiction d'envoyer avant que l'authentification
soit en place** — un envoi non authentifié n'aurait pas seulement été non mesurable, il aurait été
activement filtré.

**Ce qui décide vraiment de la délivrabilité n'est pas chez le fournisseur.** Quatre livrables, à traiter
dans ce chantier :

1. **Un sous-domaine d'envoi dédié sous `falkye.com`** — `avis.falkye.com` ou l'équivalent, jamais la
   racine, et jamais le domaine de l'entreprise qui porte la correspondance d'affaires. Un incident de
   délivrabilité empoisonne alors le sous-domaine seulement.
   **Domaines détenus :** `falkye.com` porte le produit, le site, les envois et la réputation. `falkye.ca`
   est une réserve défensive de marque et ne sert à rien d'autre — ne pas y répartir d'envois, ce qui
   diviserait la réputation en deux et doublerait le travail d'authentification sans bénéfice.
2. **SPF, DKIM et DMARC.** DMARC en `p=none` avec rapports d'abord, resserré en `p=quarantine` une fois le
   flux propre. Enregistrements DNS chez le registraire, aucune liste blanche nécessaire.
3. **`List-Unsubscribe` avec désabonnement en un clic (RFC 8058).** **N'existe nulle part dans le code ni
   dans les documents à ce jour.** Gmail et Yahoo l'exigent des expéditeurs en volume depuis février 2024,
   avec un taux de plainte sous 0,3 %. FALKYE est sous leur seuil aujourd'hui, mais l'en-tête coûte
   presque rien à poser maintenant et très cher à rattraper en pleine crise de délivrabilité.
4. **Un rodage.** D'abord les adresses d'Alexandre, puis une montée lente. Jamais de zéro au lot complet.

**Point de vigilance à transmettre au chantier 21 :** un résumé de prospects d'entreprises ressemble, en
surface, à une liste d'adresses achetée — précisément la forme de contenu que les filtres scrutent le
plus. La formulation et la structure comptent ici davantage que pour un courriel transactionnel ordinaire.

**Ce que le code demande, et ce qu'il ne demande pas.** Le registre `notification_channels.yaml` permet
d'ajouter un canal sans toucher au moteur de notification. Le remplacement est donc un nouveau module,
une entrée de registre et trois variables d'environnement — rien dans le socle. C'est l'extensibilité qui
paie.

**3. Un ordonnanceur minimal.** Une exécution périodique qui ne dépend pas d'une commande tapée à la
main. Fréquence fixe, non configurable.

**Ce qui avance sans DNS, et ce qui n'avance pas.** Le profil, le module d'envoi, l'ordonnanceur et le
fil de bout en bout se construisent et se valident au complet — Postmark fournit un jeton de test qui
accepte les appels et retourne un succès sans livrer. Seuls le sous-domaine, les enregistrements DNS et
**la livraison réelle** attendent.

**Ne pas faire le premier envoi réel sans authentification, même si c'est techniquement possible.** Un
envoi non authentifié est une mesure qui ne mesure rien, et ses deux issues induisent en erreur : s'il
tombe dans les indésirables, on accusera le contenu alors que c'est DKIM qui manque; s'il arrive parce
qu'il va vers une adresse qui connaît déjà l'expéditeur, on conclura que la délivrabilité est bonne alors
que rien n'a été éprouvé.

**4. Le fil complet, testé de bout en bout.** Création du profil → exécution → détection → score →
envoi. Un test qui parcourt la chaîne entière compte plus que dix tests unitaires sur ses morceaux.

**5. La rétroaction minimale.** Un moyen de marquer un prospect « pas pertinent » depuis le courriel.
Sans motif, sans tableau de bord — juste la donnée. C'est ce qui alimente la seule boucle de correction
du produit, et l'omettre maintenant, c'est perdre les premières observations, qui sont les plus
instructives.

---

## Constats de la phase 0 — 5 septembre 2026

**Le profil est prêt.** Rien de bloquant : un humain peut créer aujourd'hui un profil complet et
utilisable. Deux frictions seulement, sans code neuf — la création ne demande pas de mot de passe, il
faut une seconde commande en mode opérateur; et le plan par défaut est Écho, ce qui a une conséquence
sur la rétroaction (voir plus bas).

**Le canal d'envoi existe et est plus complet que prévu** — authentification, multipart texte et HTML,
erreurs proprement retournées. Il ne peut simplement pas fonctionner, le port sortant étant bloqué.
**Rien à réécrire :** le registre de canaux fait exactement ce pour quoi il a été construit. Ajouter le
nouveau fournisseur est un module, une entrée au registre, des variables d'environnement — et rien dans
le moteur. Ce qu'il faut écrire se limite à la traduction du contenu vers le format du fournisseur et à
l'en-tête de désabonnement, qui n'a aucun point d'accroche aujourd'hui.

**Aucun ordonnanceur n'existe.** Toutes les exécutions passent par une commande tapée.

**Le résumé groupé existe déjà à environ 80 %** — il rassemble les notifications d'une fenêtre, les
formate en un seul corps et les envoie. **Ce qui lui manque est le motif du repérage**, que le
formateur individuel produit pourtant déjà. C'est un rapprochement, pas une construction.

### ⚠️ Trois défauts trouvés, dont un que le chantier hériterait

**1. Le lot perdu en silence — le plus grave, et c'est la troisième fois que ce motif apparaît.** Quand
un envoi échoue, la trace est enregistrée, mais rien ne réessaie **et la notification reste en base** —
donc ses signaux comptent comme déjà couverts. Au cycle suivant, l'entreprise ne produit plus rien.
**Une opportunité dont l'envoi a échoué n'est jamais renvoyée.** C'est exactement le motif du
chantier 1 : un filet qui capture sans livrer. **À corriger dans ce chantier**, c'est la réponse à sa
question de la section 11.

**2. Deux chemins de livraison ont divergé.** Le résumé appelle le canal directement, sans passer par
la résolution de destinataire que la livraison individuelle utilise correctement. Deux conséquences
réelles : un canal de type webhook, actif au registre, reçoit une adresse courriel comme si c'était une
URL — chaque résumé produit donc une livraison en échec parasite, et la réserve de palier du webhook est
contournée. Et la date d'envoi n'est renseignée que si l'identifiant du canal vaut exactement `email`,
codé en dur — le nouveau canal cesserait silencieusement de la remplir. **Les deux chemins doivent être
réunifiés.**

**3. ~~La rétroaction est inaccessible au palier qui en a le plus besoin.~~ — surévalué, corrigé le
5 septembre 2026.** Vérification faite : **le marquage n'a aucune porte de palier** et fonctionne sur
Écho aujourd'hui. La mention « réservé à Radar » ne vivait que dans une chaîne de documentation, sans
être appliquée. **Ce livrable disparaît.**

Ce sont trois autres commandes du tableau de bord — la vue, la synthèse et la carte — qui rejettent
Écho. Le diagnostic sur l'écart entre le code et la décision du 4 septembre était juste, mais il porte
sur elles, et elles relèvent de leur propre chantier.

**Le seul obstacle réel pour la rétroaction depuis le courriel demeure :** le marquage exige une session
authentifiée en ligne de commande, ce qu'un lien cliqué ne peut pas fournir. **Le jeton dans l'URL reste
la réponse**, comme pour le désabonnement.

### ✅ Réunification des chemins de livraison — livrée le 5 septembre 2026

Les trois défauts sont corrigés, chacun reproduit avant de l'être. **491 tests**, dont huit neufs.

**Le lot ne se perd plus.** La sélection porte sur l'état d'attente et non sur une fenêtre de dates, et
le marquage n'a lieu qu'**après un envoi réussi**. Une opportunité attend autant de cycles qu'il le faut
et sort au premier envoi qui aboutit. C'est la réponse implémentée à la question de la section 11.

**La forme de livraison se déclare au registre, pas dans le moteur** — résumé pour le courriel, unitaire
pour le webhook, validé au chargement. Le moteur ne nomme aucun canal : il demande au registre qui sert
la forme qu'il livre. C'est l'extensibilité appliquée au bon endroit.

**Le motif du repérage entre au résumé**, repris tel quel de la structure de faits, avec la catégorie de
signal et **jamais le nom de la source**. La place de la ligne d'interprétation du chantier 21 est
réservée par un paramètre qui n'émet rien tant que rien ne lui est passé — pas de texte de remplissage,
qui serait l'encouragement non mérité que la charte interdit.

**Une troisième divergence trouvée en réunifiant :** le résumé incluait les notifications hors profil,
que la livraison unitaire excluait déjà. Corrigé.

**⚠️ La cause profonde, plus importante que les trois défauts.** Le module du résumé **n'avait aucun
test** — 483 dans le dépôt, zéro sur celui-là. C'est précisément pourquoi trois défauts y ont survécu.
Il en a huit maintenant. Voir le guide d'ingénierie.

### ✅ Module d'envoi livré le 5 septembre 2026

**Le contrat a été éprouvé avant d'être codé.** Une sonde rejoue les quatre réponses contre la vraie
API et sert de preuve rejouable, sur le modèle de celle de la persistance : envoi accepté, jeton
invalide refusé, adresse malformée refusée, en-têtes et flux acceptés. Elle n'a aucune issue où un
courriel parte. **Les réponses simulées dans les tests sont ces réponses réelles, recopiées** — des
formes inventées n'auraient prouvé que la cohérence du code avec lui-même.

**Le fil partiel est parcouru en réel** : profil, notification, résumé groupé, appel au service,
opportunité marquée livrée. Ce n'est pas encore le premier envoi vers une vraie adresse, mais toute la
mécanique en amont est éprouvée contre le vrai service.

**Le piège du flux est traité par le défaut, pas par la configuration.** Le flux de diffusion est le
comportement par défaut, surclassable seulement si le nom du flux diffère. Se tromper de flux par oubli
de configuration était le risque le plus cher de ce module, et l'oubli en est le mode de panne le plus
probable.

**⚠️ Un faux succès aurait fait revenir le défaut de l'étape 1 par une autre porte.** Une réponse
techniquement acceptée mais porteuse d'un code d'erreur, ou une réponse illisible — page d'erreur de
mandataire, HTML — sont traitées comme des échecs. Sans ça, un lot aurait été marqué livré sans l'être.
**C'est la quatrième fois que ce motif apparaît dans le projet** : capturer sans livrer, sous une forme
nouvelle chaque fois.

**Le canal SMTP passe inactif** — deux canaux actifs de même forme enverraient le résumé en double. Il
reste au registre, prêt pour un hôte qui autoriserait ce transport.

**Vocabulaire manquant au registre, signalé et non traité.** Ce canal n'est pas « à développer » : il est
écrit, correct et testé, et son transport est simplement inatteignable. Le registre ne connaît que
`actif` et `a_developper`; un troisième état — `indisponible` — dirait la chose exactement. **Non ajouté
délibérément**, faute d'un second cas qui le justifierait. À trancher quand il apparaîtra.

### ✅ Désabonnement et rétroaction par lien — livrés le 5 septembre 2026

**L'autorisation voyage dans le lien**, ce qui règle d'un coup l'obstacle réel : un lien cliqué depuis un
courriel ne peut fournir ni session ouverte ni identification en ligne de commande.

**Trois propriétés de sécurité, dont la troisième est la vraie protection.** Le jeton en clair n'est
jamais conservé — seule son empreinte, donc une copie de la base ne rend aucun lien utilisable. Un jeton
n'autorise **qu'un geste, sur une cible** : celui de la rétroaction ne désabonne pas, et inversement.
**C'est la portée qui protège, pas le secret seul.**

**Consulter montre, agir modifie.** Les analyseurs de liens des messageries et des antivirus suivent
automatiquement les liens d'un courriel avant l'humain. Un désabonnement déclenché par une simple visite
partirait tout seul; une rétroaction déclenchée ainsi fabriquerait de la donnée que personne n'a voulue —
**dans le seul mécanisme de correction du produit**. C'est aussi pourquoi la norme du désabonnement en un
clic l'impose.

**Le lien vit à deux endroits :** dans le corps pour la personne qui lit, et dans les en-têtes pour le
bouton natif des grandes messageries.

**⚠️ Un défaut introduit puis trouvé, dont la leçon dépasse le cas.** La première version révoquait
l'ancien jeton à chaque envoi, cassant le lien de désabonnement de tous les courriels encore en boîte de
réception. La cause était réelle — on ne peut pas reconstruire un jeton dont on ne garde que
l'empreinte — mais **la conclusion était fausse : un lien de désabonnement mort ne retient pas l'abonné,
il le pousse vers le bouton « pourriel », qui coûte à la réputation du domaine entier.** Tous les jetons
d'un profil restent donc valables, au prix d'une ligne par envoi.

**Trois décisions de portée.**

*Le désabonnement coupe le courriel, pas le service.* Appliqué à la résolution de destination, donc tout
canal humain ajouté demain en hérite sans qu'on y pense. Le webhook n'est pas touché : se désabonner d'un
envoi n'est pas résilier une intégration qu'on paie.

*Deux clics ne pèsent pas double.* La rétroaction est cumulative; un lien prérécupéré par un analyseur
puis cliqué compterait deux marquages pour une seule opinion.

*Un profil désabonné ne génère plus rien.* **Sans cette garde, le résumé aurait été construit, n'aurait
eu aucun canal où aller, n'aurait jamais été marqué envoyé — et les opportunités se seraient accumulées
en attente pour toujours.** Un résumé mort par cycle, indéfiniment. **Cinquième variante du motif
« capturer sans livrer ».**

**Et la règle sur les tests, appliquée le jour même.** Sept tests passaient uniquement parce que la
machine portait une variable d'environnement : ils vérifiaient une configuration, pas un comportement.
Isolés. Deuxième occurrence : un faux profil de test ne portait que les champs dont l'auteur s'était
souvenu, et il a cassé à l'arrivée du désabonnement — remplacé par un vrai objet.

### ✅ Point d'entrée HTTPS — livré le 5 septembre 2026

**Éprouvé sous le vrai serveur, pas seulement avec le client de test.** Le client de test court-circuite
le réseau et l'analyse des requêtes; la chaîne a donc été suivie contre le serveur réel, avec de vrais
liens en base. Résultat conforme : une simple visite ne déclenche rien, ni pour le désabonnement ni pour
la rétroaction, et seule l'action explicite modifie l'état. Un lien inconnu répond « introuvable ».

**Trois décisions qui méritent d'être dites.**

*Le corps de la requête n'est pas lu.* Les grandes messageries envoient un contenu de formulaire sans
jeton anti-contrefaçon — c'est une requête inter-origine par conception. Le jeton du chemin porte déjà
toute l'autorisation; exiger un contenu précis ferait échouer le bouton natif d'un fournisseur qui
formaterait autrement.

*Un lien invalide rend toujours la même page*, qu'il soit inconnu, remplacé, ou employé pour l'autre
action — vérifié octet pour octet. Distinguer les cas ne renseignerait que quelqu'un qui sonde des
jetons, et n'aiderait pas la personne qui a simplement un vieux lien dans sa boîte.

*La sonde de santé ne touche pas la base, délibérément.* **Une sonde qui l'interrogerait transformerait
une lenteur de base en application « morte »** aux yeux du serveur placé devant, qui retirerait alors le
seul chemin par lequel un désabonnement pourrait encore passer. **Sixième variante du motif : garantir le
chemin de sortie, y compris quand le reste va mal.**

**Deux dépendances entrent, vérifiées avant d'être choisies** — arbre complet résolu en roues
précompilées avant de les retenir, même contrainte que le reste du projet.

**Le chiffrement n'est pas dans l'application** : elle sert en clair sur la boucle locale, derrière un
serveur intermédiaire qui porte le certificat. Le renouvellement, les rechargements et les permissions
sur les clés y sont mieux traités, et un redémarrage de l'application ne doit pas les interrompre.

**Laissé de côté volontairement, et c'est le bon geste :** le point d'accroche du service de paiement,
dont le secret attend depuis longtemps sans destination. Ce serait une cinquième route et peu de code,
mais il ne figure pas aux livrables — et l'ajouter de soi-même serait exactement ce que la règle de
portée interdit. **Consigné comme laissé de côté, avec la note que le coût est désormais faible.**

### ✅ Ordonnanceur et battements de cœur — livrés le 5 septembre 2026

**Les deux sont la même pièce**, et c'est la bonne lecture : une exécution qui ne laisse pas de trace est
indiscernable d'une semaine sans rien à signaler.

**Un minuteur du système, pas un processus qui dort.** Aucune dépendance neuve, redémarrage au démarrage
de l'hôte, et un échec visible dans les unités en défaut. Un processus qui dormirait en boucle a le
défaut inverse : il peut mourir en silence, et rien ne le relève.

**Un créneau manqué se rattrape** plutôt que d'attendre une semaine de plus — même règle que le lot
conservé : ne pas perdre une livraison parce que le moment est passé. Et le créneau vit dans la
configuration, pas dans le code, pour qu'en changer ne demande pas un déploiement.

**Les trois silences que les battements distinguent**, et c'était le vrai sujet du livrable :

| Ce qu'on voit | Ce que ça veut dire |
|---|---|
| Aucune ligne | Le cycle n'a pas démarré — **l'absence est le signal** |
| Début sans fin | Le cycle s'est interrompu, daté à la minute |
| Début et fin, comptes à zéro | Il a tourné et n'avait rien à signaler |

**Le repli a été éprouvé contre une vraie base injoignable**, pas seulement simulé. Une ligne ajoutée en
fin de fichier, donc une écriture interrompue ne perd que la sienne. Et **journaliser ne lève jamais
d'erreur**, y compris quand le fichier de repli est lui-même impossible à créer — une panne d'observation
ne doit pas emporter la production, sans quoi on perdrait le cycle en plus de sa trace.

**Deux décisions d'exploitation.**

*Un profil en échec n'emporte pas les autres.* Une adresse refusée chez l'un ne prive personne d'autre;
ses opportunités restent en attente et repartiront au cycle suivant.

***Un résumé que personne n'a livré est un échec, pas un succès.*** Aucune erreur n'est levée dans ce cas
— aucun canal n'a simplement répondu — mais le compter comme réussi masquerait le silence. Même
raisonnement que le code d'erreur sur une réponse acceptée, appliqué au niveau au-dessus.

*Le point d'entrée public se relance toujours* : c'est le seul chemin par lequel un désabonnement peut
passer, et le laisser mort transformerait une panne en plainte pour pourriel.

**⚠️ Limite constatée puis corrigée le 5 septembre 2026.** Il avait été affirmé que « les portails de
données ouvertes ne sont pas joignables depuis l'environnement de développement ». **Vérification faite :
c'est faux.** Un seul portail est réellement bloqué — le REQ, et par le pare-feu de son origine, pas par
la liste blanche. Données Québec, le portail fédéral et les ressources associées répondent tous.

Et l'archive REQ est téléchargeable depuis la release du dépôt — vérifié, vrai fichier de 267 Mo, dans un
conteneur qui dispose de 16 Go de mémoire, largement au-dessus du plancher mesuré de 0,91 Go.

**Conséquence : la moitié détection ne demande rien d'Alexandre.** Ce qui avait été présenté comme un
trou à combler de son côté n'en était pas un.

**Dette consignée, à traiter à l'étape suivante : le fichier de repli capture sans pouvoir livrer** —
septième variante du motif. Il vit sur un hôte injoignable depuis l'environnement de développement, donc
dans les deux cas exacts où il se déclenche, la base est muette et le fichier hors de portée. Le
correctif est déjà prévu au mandat : un flux déclenché à la demande qui récupère le fichier depuis le
coureur et le publie.

### ✅ Chaîne de déploiement — livrée le 5 septembre 2026

**Ce que la chaîne ne peut pas faire est aussi construit que ce qu'elle fait.** L'utilisateur de
déploiement écrit le code et peut redémarrer trois unités nommées — pas davantage, et aucun accès au
fichier d'environnement. La création du schéma passe par une unité distincte qui, elle, tourne avec les
identifiants. **Une chaîne compromise peut interrompre le service; elle ne peut ni lire la base ni les
clés d'envoi.**

**Trois décisions.** L'empreinte du serveur vient du secret, jamais d'une lecture par le réseau — la
récupérer depuis le réseau qu'on cherche à ne pas croire ne vérifie rien. **Le déploiement vérifie plutôt
que de supposer** : il interroge la sonde de santé jusqu'à ce qu'elle réponde et échoue en affichant
l'état de l'unité, parce qu'un redémarrage accepté n'est pas un service qui répond. Et le contrôle des
roues précompilées tourne à chaque exécution des tests — c'est lui qui avait décidé du choix de l'hôte;
si une roue disparaissait, on l'apprendrait là plutôt qu'au déploiement.

**Le filet peut enfin livrer — septième variante close.** Un troisième flux, déclenché à la demande,
rapatrie le fichier de repli par le coureur, qui atteint le serveur, et le publie. Deux détails qui
comptent : un fichier vide est annoncé comme le cas **normal**, pour qu'on ne cherche pas une panne là où
il n'y en a pas; et le vidage n'a lieu qu'**après** que le contenu soit sorti de l'hôte — l'inverse
perdrait exactement ce qu'on venait chercher.

**Vérification faite parce qu'elle ne coûtait rien :** les blocs de script des trois flux ont été passés
au vérificateur de syntaxe. Une faute de frappe dans un script de déploiement ne se serait vue qu'au
premier déploiement réel, c'est-à-dire au pire moment.

**Déclencheur retenu :** la branche par défaut du dépôt, `claude/phase-1-docs-setup-b8em5g`.

### Fil de bout en bout — mesures du 6 septembre 2026

**Le miroir REQ est chargé pour de vrai.** 2 726 312 lignes, le chiffre exact du chantier 29, en
36,7 minutes. Zéro signal au premier import, ce qui est attendu — tout est neuf, donc la prudence de
début de vie supprime tout.

**⚠️ La mesure qui aurait changé une décision d'infrastructure.** Le pic mémoire réel de l'import est de
**3 535 Mo**, presque quatre fois le plancher de 0,91 Go annoncé au mandat. **Sur le serveur à 4 Go
écarté au moment de la commande, cet import se serait très probablement fait tuer par le système.** La
décision de doubler la mémoire pour cinq dollars n'était pas une marge de confort, c'était la condition
de fonctionnement. Sur 8 Go, 3,5 Go de pic laisse de la place — mais pas énormément, une fois le
système, le serveur d'application et le cache comptés.

*À noter : le code portait déjà la bonne estimation en commentaire. C'est le chiffre du mandat qui était
périmé, pas le code.*

**⚠️ Un cul-de-sac dans le point d'entrée conversationnel — défaut réel, à corriger.** Sur six
formulations éprouvées, cinq passent au premier niveau. Quand il échoue, **le second niveau — qui existe
précisément pour ce cas — est fermé au plan Écho**, et le premier profil réel est au plan Écho par
défaut. L'utilisateur dont le vocabulaire sort des synonymes n'a alors aucune issue par ce chemin.

**C'est la correction du 4 septembre que le code n'a pas rattrapée** — l'assistance de niveau 2 est
disponible dans tous les paliers depuis cette décision, parce que c'est une escalade qui rend la
configuration juste, pas un enrichissement. La phase 0 disait « le profil est prêt, rien de bloquant » :
c'était vrai à condition que le lexique morde, et ça n'avait pas été éprouvé.

**Première mesure vraie de l'appariement par nom.** Sur 1 248 entreprises détectées au SEAO, résolues
contre le miroir réel : **42 % résolues, 56 % ambiguës, 1 % introuvables.** Plus de la moitié ne se
résolvent pas sans ambiguïté. C'est la faille D chiffrée pour la première fois, et elle relève du
chantier 4.

**Une alarme corrigée par la mesure.** Le repli de résolution parcourt toute la table là où le chemin
principal utilise l'index — facteur six mesuré, pas un blocage. Les quarante minutes s'expliquent par le
volume, environ 1,9 seconde par entreprise, pas par un défaut. **Coût mesuré, pas défaut.** Un premier
cycle complet sur quinze sources se compte en heures; un cycle hebdomadaire incrémental ne traitera que
les entreprises neuves.

**Le battement de cœur s'est prouvé sur une interruption réelle.** Cycle tué en cours : un début sans
fin, daté à la seconde. Exactement la signature prévue.

**Décision : le fil se termine avec le SEAO seul.** 1 248 entreprises et 526 résolutions suffisent à
prouver profil, détection, score et envoi. Les quatorze autres sources ne prouveraient rien de plus sur
la chaîne — elles mesureraient leur propre débit, ce qui n'est pas ce livrable.

### ✅ Fil de bout en bout — livré le 6 septembre 2026

**Le cul-de-sac est corrigé, et la porte disparaît entièrement** plutôt que d'être élargie — le contrôle
de palier, son exception et les gestionnaires qui l'attrapaient. Un gestionnaire qui ne peut plus rien
attraper trompe le prochain lecteur. Les deux tests qui vérifiaient la porte **encodaient l'ancienne
décision** : inversés plutôt que supprimés, ils verrouillent désormais la nouvelle.

Sur la formulation qui butait, le message a changé de nature — il ne dit plus « réservé aux plans
supérieurs » mais « clé d'API non configurée ». Ce n'est plus une restriction du code, c'est une
configuration manquante.

**Le fil complet a tourné sur de vraies données** : douze notifications, un résumé envoyé, douze
opportunités livrées. De vraies entreprises québécoises, de vrais contrats, le motif du repérage tiré de
la structure de faits, la catégorie de signal et **jamais le nom de la source**.

**La boucle entière éprouvée sur le vrai serveur**, sur une opportunité réelle : une simple visite du
lien ne change rien, l'action explicite marque le prospect, le désabonnement en un clic fonctionne. **Et
la rétroaction a nourri le moteur** — le poids d'une sphère a bougé après un seul marquage. La seule
boucle de correction du produit fonctionne depuis un lien cliqué dans un courriel.

### ⚠️ Le résultat le plus important n'est pas le douze

**Le premier cycle a livré un résumé vide, et zéro était correct.** Les 1 672 signaux du SEAO portent
**tous la même sphère unique** — gestion de projet. Le profil était en chaîne d'approvisionnement et
logistique. Aucun recouvrement, donc rien à livrer.

**C'est la faille A mesurée pour la première fois : une source qui ne peut servir qu'une seule sphère sur
trente-quatre.** Il a fallu relier cette sphère au profil pour obtenir un envoi non vide — non pour
truquer le résultat, mais parce que c'est la seule que la source active peut servir aujourd'hui. **Le
choix était forcé, et c'est ça le constat.**

Autrement dit : la chaîne fonctionne, et elle vient de démontrer qu'elle n'a presque rien à dire pour
trente-trois sphères sur trente-quatre avec les sources actuellement branchées.

**Les trois silences se distinguent dans une trace réelle** — un début sans fin sur le cycle interrompu,
un cycle vide, un cycle plein. Le mécanisme du livrable 8 s'est prouvé sur des interruptions réelles et
non simulées.

**Deux réserves dites honnêtement.** L'enrichissement web échoue dans l'environnement de développement,
le moteur de recherche employé n'y étant pas joignable — le cycle continue et se termine proprement, ce
qui est le bon comportement, mais aucun site n'a été enrichi. **Ça confirme le point 27.1 : l'enrichissement
tourne pour chaque entreprise détectée, avant tout seuil.** Et la mise en pause temporaire des autres
sources a été faite par le registre, exactement comme prévu, puis restaurée.

**Il ne reste que le premier envoi réel.**

### ⚠️ Premier envoi réel — refusé, et c'est le résultat le plus utile du chantier

**6 septembre 2026.** Le fournisseur a accepté, le serveur du destinataire a refusé à la porte —
détecté comme pourriel, rebond dur, jamais remis en file. Rien n'est arrivé dans la boîte.

**Quatre constats, dont un seul explique le refus.** Trois cent six lignes, toutes notées à l'identique,
sans motif de repérage — un déversoir plutôt qu'un résumé. Aucun filtre ne laisse passer ça d'un domaine
neuf.

**Mais le plus grave n'est pas le refus, c'est ce qui l'a suivi : FALKYE croyait avoir livré.** Les 306
notifications marquées incluses, zéro en attente, elles ne repartaient jamais. **Le rebond n'existait
nulle part dans le produit.** Huitième variante du motif, et la plus aboutie : capturé, cru livré, perdu,
sans qu'aucune trace interne ne le dise.

### ✅ Réconciliation des livraisons — livrée le 6 septembre 2026

**Une acceptation n'est plus une livraison.** Une table distincte porte la référence du message chez le
fournisseur et son statut réel : acceptée, puis confirmée, rebondie ou indéterminée.

**La réconciliation ouvre le cycle, avant toute génération** — et c'est l'ordre qui compte : une
opportunité reprise repart dans ce cycle-ci, pas la semaine d'après. Sinon un refus coûterait deux
semaines au lieu d'une.

**Consultation plutôt que rappel entrant, et c'est la décision de conception du module.** Un rappel
entrant exigerait que le point d'entrée réponde à l'instant précis où le fournisseur pousse — une
indisponibilité perdrait le verdict sans que rien ne le dise, **soit la forme exacte du défaut qu'on
corrige**. La consultation se rejoue sans effet de bord, n'ouvre aucune surface entrante, et son délai
est sans conséquence puisque ce qu'elle déclenche ne sert qu'au cycle suivant.

**Le moteur ne nomme aucun fournisseur** : il interroge le canal, et un canal qui ne sait pas répondre
retourne vide.

**Le piège symétrique, traité avec autant de soin.** Remettre en attente sur une **ignorance**
renverrait un résumé déjà lu — défaut jumeau du premier, et plus difficile à voir. Sans verdict, la
remise reste à vérifier et repasse au cycle suivant; au-delà de la fenêtre de rétention du fournisseur
elle devient indéterminée — **un aveu daté qui ne défait rien et ne marque rien comme livré**.

**Vérifié sur les vraies données**, pas sur un décor : les 306 opportunités sont revenues en attente, et
deux mutations éprouvées font tomber exactement les tests attendus de chaque côté.

**Décision laissée ouverte par le module, tranchée le 6 septembre 2026.** Un rebond pour pourriel se
reproduirait à l'identique chaque semaine — les opportunités repartent, le résumé rebondit, sans fin.

**Règle retenue : trois rebonds consécutifs sur le même profil suspendent l'envoi et déclenchent une
alerte.** Une **suspension**, pas un désabonnement — la distinction reste visible dans le journal, parce
qu'un profil suspendu par le produit n'est pas un abonné qui a demandé à partir.

*Trois plutôt que deux :* un rebond isolé peut venir d'une indisponibilité passagère chez le
destinataire; au troisième, c'est le message ou l'adresse.

**Le vrai remède reste de ne plus produire un message que les filtres refusent.** La suspension est un
garde-fou, pas une solution.

**Limite nommée :** la réconciliation ne couvre que le résumé. La livraison unitaire n'a pas de
référence — sans conséquence aujourd'hui, le canal qui l'utilise répondant dans l'appel. À revoir si un
canal unitaire différé apparaît.

### ✅ Désabonnement et suspension — livrés le 6 septembre 2026

**⚠️ Une découverte qui rend la règle des trois rebonds indispensable plutôt que prudente.** Le
fournisseur ne suppprime automatiquement que les **rebonds durs** et les **plaintes de destinataires**.
Un verdict antipourriel du serveur receveur n'est ni l'un ni l'autre : l'adresse n'a jamais été mise sur
la liste de suppression et ne le sera pas.

**Rien chez le fournisseur n'aurait donc empêché de réenvoyer à cette adresse, indéfiniment.** La règle
des trois rebonds n'est pas une précaution théorique — **c'est le seul garde-fou qui existe.**

Sans conséquence sur la réconciliation, qui lit les événements du message et non la liste de
suppressions.

**La suspension ne perd rien**, et c'est l'autre moitié de la distinction : les opportunités restent en
attente et repartent à la levée, là où un désabonnement arrête la génération pour de bon. Et
« consécutifs » veut dire ce qu'il dit — **une remise confirmée remet le compteur à zéro**, sans quoi
trois rebonds étalés sur un an finiraient par suspendre quelqu'un qui reçoit normalement.

**Une commande de reprise existe, parce qu'une suspension qu'on ne peut pas lever serait un cul-de-sac**
— le défaut exact déjà rencontré au point d'entrée conversationnel. Elle ne réabonne jamais un
désabonné, et l'état comme le geste pour en sortir sont visibles.

**✅ Dépendance levée le 6 septembre 2026.** Le réglage du désabonnement était verrouillé au niveau du
compte — ni l'interface ni l'API ne l'ouvraient, d'où l'échec des recherches. **Le support du
fournisseur l'a activé sur demande**, et l'option « gérer les désabonnements soi-même » est désormais
sélectionnée sur le flux de diffusion.

Leurs deux exigences étaient déjà remplies par ce qui avait été construit : un lien de désabonnement
visible dans le corps, et les en-têtes correspondants.

**À vérifier au prochain envoi, puisque c'est le seul moment où c'est observable :** que l'en-tête
survive et pointe vers `lien.falkye.com` plutôt que vers le domaine du fournisseur. C'est le test qui
prouve que le réglage a pris effet.

**Article de mise à l'échelle consigné, non fait :** le chemin d'envoi fait un appel par message, en
séquence, une connexion à la fois. La recommandation du fournisseur sur le point d'entrée par lot ne mord
pas aujourd'hui; elle deviendra le bon chemin quand le nombre d'abonnés rendra la latence sensible.

**Trou trouvé dans l'outil de migration :** la première colonne obligatoire du projet était refusée alors
qu'une valeur par défaut côté base suffit à remplir les lignes existantes. Corrigé, avec le refus maintenu
pour une valeur par défaut côté applicatif seul — celle-là ne touche jamais l'existant.

### Le miroir REQ vit en local — mesuré le 6 septembre 2026

**Le découpage du chantier 29 se justifie mieux que prévu, chiffres en main.** Les miroirs et l'état de
diff représentent **99,95 % du volume et zéro pour cent de ce qui se perdrait** : 5,7 millions de lignes
reconstituables contre moins de 3 000 qui ne le sont pas.

**Deux chemins d'import existent, un seul a été optimisé.** L'import du miroir fait **deux allers-retours
par ligne** — une vérification d'existence, puis une insertion, avec un objet par ligne. C'est exactement
le défaut que le chantier 29 a corrigé pour le moteur de diff, et il n'a pas été porté ici.

| | Local | Distant |
|---|---|---|
| Durée de l'import du miroir | **33 minutes** | **≈ 168 heures, soit 7 jours** |
| Allers-retours | négligeables | 5,46 M à 111 ms, séquentiels |

**Le rapport n'est pas de 23, il est de l'ordre de 300.**

**Décision : miroir REQ et état de diff sur le disque du serveur, base distante pour les ~3 000 lignes du
produit.** Prévoir environ 2 Go de disque sur les 75 disponibles, et 3,5 Go de mémoire au pic pendant
l'import.

**Le chemin d'import reste à traiter, consigné au chantier 27** — non pour la production, où il tournera
en local et où le coût est nul, mais parce que la même forme reviendra dès qu'un miroir devra vivre
ailleurs.

### ⚠️ Le plafond a révélé un tri arbitraire promu en sélection

**Cent quatre-vingt-deux des 306 opportunités partagent exactement le même score.** L'ordre entre elles
était donc celui de leur identifiant, c'est-à-dire **celui du fichier source**.

**Un plafond de dix posé là-dessus aurait livré chaque semaine les dix premières lignes du fichier.** Le
produit aurait paru fonctionner, en livrant toujours la même chose pour une raison sans rapport avec la
pertinence — et rien ne l'aurait signalé.

Le départage se fait désormais par **le montant du signal, un fait déjà présent**, jamais par le score,
qui reste l'affaire du module de notation.

**Le motif vient maintenant de la structure de faits.** Les 306 lignes disaient « Signal détecté » alors
que chaque signal portait un montant distinct, déjà en base. **Deux abstentions y sont aussi testées que
le motif lui-même** : ne jamais rendre les champs libres — l'un d'eux contient le nom de la source, que
la neutralité des libellés interdit d'afficher — et ne jamais dater, la seule date disponible étant celle
de l'ingestion.

### ✅ Contenu corrigé — 6 septembre 2026

**2 534 caractères contre environ 40 000**, sur les mêmes données. Et ce ne sont plus les mêmes
entreprises : la version d'avant ouvrait sur dix sociétés à numéro indiscernables, celle-ci sur des
entreprises reconnaissables avec leur montant.

**Le plafond borne le message, jamais le lot.** Seules les retenues sont marquées livrées, le reste
attend — et le résumé dit combien restent en attente. **Taire l'arriéré ferait croire que la semaine n'a
produit que dix opportunités.**

**Le motif suit trois règles :** les mots de la source d'abord, le montant ensuite, rien en dernier
recours. Un bloc qui n'affiche que sa catégorie dit exactement ce qu'on sait; « Signal détecté »
prétendait dire davantage — et se répétait 306 fois.

### ⚠️ Trois réserves signalées et non corrigées

**Les scores ne discriminent presque pas** — trois valeurs pour 306 opportunités, dont 182 au même
palier. **Mais le moteur de notation n'est pas en cause : il calcule fidèlement ce qu'on lui donne.**

Tous les signaux d'une même source portent aujourd'hui la même sphère avec la même confiance. Le score
n'a donc rien à départager, et l'uniformité qu'on observe est le reflet exact d'une entrée uniforme. Le
tri par montant masque le symptôme sans le soigner.

**Ce n'est donc pas un défaut de notation, c'est l'absence de lecture.** Le score ne pourra discriminer
que lorsque ce qu'il reçoit sera distinct — classification normalisée, objet du contrat, bande
d'effectifs, premier contrat contre contrat de routine. **Le chantier 22 précède donc les chantiers 4 et
6** : l'ordre inverse produirait une notation plus fine nourrie de la même uniformité.

**Le sujet ne dit rien de son contenu** — un préfixe entre crochets et une plage de dates. Hors portée du
chantier, mais ça compte pour les filtres autant que pour la lecture.

**Le message est en texte seul, sans version HTML.** Un envoi de diffusion sans partie HTML est
inhabituel et les filtres le notent. Non ajouté délibérément : le mandat demande du texte lisible, pas un
gabarit élaboré.

**Ces trois réserves ont probablement contribué au rebond autant que le déversoir**, et deux d'entre
elles sont hors du chantier. À traiter avant de conclure que le contenu est réglé.

### ⚠️ Le filtre territorial ne fonctionnait pour aucun profil — trouvé le 6 septembre 2026

**Plus de neuf entreprises sur dix étaient sans localisation dans le miroir.** Ce n'était pas un défaut
d'affichage du résumé : **le rayon d'action, une des trois choses que l'utilisateur configure, ne servait
à rien.**

**La cause.** Le repli sur l'adresse du domicile avait sa condition **inversée**, et le commentaire qui la
justifiait affirmait le contraire de la documentation officielle. Le drapeau signifie « dispensée de
fournir l'adresse » — donc adresse absente — et c'était le seul cas où le code acceptait de lire. **Le
repli ne se déclenchait jamais utilement.**

Mesuré sur les 2 955 114 lignes du fichier réel : 1 943 990 lignes portent une adresse et n'étaient
jamais lues. Les seules villes venaient du fichier des établissements, qui ne couvre que **6,8 %** des
entreprises — et le miroir chargé affichait 6,6 % de villes remplies. Le compte y était exactement.

**Comment le défaut a survécu, et c'est le plus instructif.** Aucun test ne parcourait cette branche :
tous les décors passaient par le fichier des établissements, avec des lignes de domicile vides. Le défaut
était invisible **aux tests et au code** — le commentaire justifiait l'erreur, donc un relecteur y aurait
vu une intention plutôt qu'une inversion.

**Correction vérifiée contre le guide d'utilisation officiel du diffuseur**, avec quatre tests utilisant
les valeurs réelles du fichier. La mutation qui réinverse la condition en fait tomber trois.

**Le miroir déjà chargé n'est pas corrigé pour autant :** le code est juste, la donnée en base ne l'est
pas. Un réimport est nécessaire — 33 minutes.

### Le score retiré du corps du message

**Retrait élargi aux libellés en même temps qu'au chiffre.** L'argument — un score qui ne discrimine pas
suggère une évaluation qui n'a pas eu lieu — vaut identiquement pour « confiance Élevé, pertinence AA »
répété dix fois. **Garder les libellés en enlevant le nombre aurait conservé le défaut sous une forme
moins visible.**

Le score reste au tableau de bord et décide toujours l'ordre, avec un test qui tombe si l'ordre cesse de
l'utiliser — pour que le retrait ne glisse pas vers un abandon.

### Décision tranchée : le résumé groupé seul

Le produit envoie aujourd'hui un courriel par notification, immédiatement, **plus** un résumé. Un scan
repérant trente entreprises produirait trente courriels puis un résumé.

**Pour la première boucle : le résumé groupé seul.** La livraison individuelle par courriel se tait.

Trois raisons, la dernière étant décisive. Une veille dont la promesse est un rendez-vous hebdomadaire
n'envoie pas trente messages. Le domaine d'envoi est neuf, sans réputation, sous une politique stricte —
une rafale est le pire profil de départ, et c'est précisément ce que le rodage interdit. Et surtout :
**la charte, section 16, a déjà tranché** — le groupement est la forme par défaut, l'envoi unitaire est
une exception qui demande un seuil explicite. Ce n'est pas une préférence de démarrage, c'est une règle.

Ça ne supprime rien : la livraison individuelle reste en place pour les canaux CRM et webhook, qui sont
des poussées vers des systèmes et non des messages à lire.

## Question de la section 11

Que se passe-t-il quand l'envoi échoue — adresse invalide, service de courriel indisponible? Le lot
est-il perdu, réessayé, ou conservé pour le prochain envoi? Un lot perdu en silence reproduirait
exactement le problème que le chantier 1 a réglé côté ingestion.

---

## Ce qui doit être livré

1. Le rapport de la phase 0, **avant le code**, avec la réponse au point 4 sur l'exécution en
   production.
2. Le code, dans la portée ci-dessus et pas au-delà.
3. Un test de bout en bout, plus les tests unitaires nécessaires.
4. **Un premier envoi réel effectué**, vers une adresse fournie par Alexandre — pas un envoi simulé.
5. La liste de ce qui a été volontairement laissé de côté, pour que le raffinement sache où reprendre.
6. **L'en-tête `List-Unsubscribe` fonctionnel dès le premier envoi**, avec le désabonnement qui fonctionne
   réellement — pas un en-tête décoratif.
7. **Une chaîne de déploiement par intégration continue.** Il n'existe aucune CI dans le dépôt, et c'est
   devenu obligatoire : le port 22 est bloqué et les API des hébergeurs sont refusées au CONNECT, donc
   l'hôte ne peut pas être administré depuis l'environnement de développement. Le déploiement passe par
   GitHub Actions, avec le secret de déploiement créé par Alexandre dans le dépôt — jamais visible
   ailleurs.
8. **Une destination pour les journaux d'exploitation, décidée avant le premier envoi.** Sans elle, la
   première défaillance réelle serait un débogage à l'aveugle, au moment précis où il faut voir.
   **Solution retenue : les événements d'exploitation s'écrivent dans la base distante**, déjà joignable
   en HTTPS. Aucun service tiers, aucun domaine de plus, et ça réutilise le journal d'exécution que le
   chantier 2 construit plutôt que d'ajouter un mécanisme parallèle — cohérent avec le chantier 27,
   point 27.4.

   **Réserve à traiter, posée avec la décision :** une défaillance de démarrage ou de connexion à la base
   ne pourrait pas s'y écrire. **Garder un fichier local en repli pour ces deux cas précis**, et seulement
   eux.

   **Trois précisions d'exploitation, qui complètent la décision sans la remettre en cause.**

   *Le repli local capture mais ne livre pas.* Le fichier de repli vivra sur un hôte inaccessible depuis
   l'environnement de développement, port 22 bloqué — donc dans les deux cas précis où il se déclenche,
   la base est muette et le fichier est hors de portée. **C'est la forme exacte de la panne de
   septembre : un filet qui capture sans pouvoir livrer.** Correctif à faible coût, réutilisant la CI du
   livrable 7 : un second flux déclenché à la demande, qui récupère le fichier depuis le coureur et le
   publie comme artefact. Aucune dépendance neuve.

   *Un troisième cas manquait : rien ne s'exécute du tout.* Hôte qui ne démarre pas, minuteur qui ne se
   déclenche pas — ni la base ni le fichier n'affichent quoi que ce soit, et l'absence de journal devient
   indiscernable d'une semaine sans rien à signaler. **Une ligne de battement de cœur à chaque exécution,
   début et fin, systématiquement**, rend la ligne manquante elle-même le signal. C'est la discipline du
   chantier 2 — distinguer une source silencieuse d'une source brisée — appliquée au coureur plutôt
   qu'aux sources.

   *L'écriture est facturée.* La base distante compte les lignes écrites. **Ce journal porte des
   événements d'exploitation, jamais des traces de débogage**, sinon il pèsera plus lourd que la donnée
   du produit dans la facture.

**Deux sous-domaines distincts, à ne pas confondre.** `avis.falkye.com` porte les envois et leurs
enregistrements d'authentification. Le point d'entrée HTTPS — désabonnement, rétroaction, webhook —
vit sur un sous-domaine séparé, `lien.falkye.com` ou l'équivalent. Un incident sur l'un ne touche alors
pas l'autre.

**Ne rien commencer d'autre.**


---

## État — liste dynamique

*Quatre états : ✅ fait avec sa preuve · 🟡 en cours · ⚠️ présumé fait, non vérifié · ⬜ à faire.*
*Une case cochée porte ce qui l'a établie — sinon elle peut mentir.*

> **⚠️ Deux lignes de cette liste ont menti pendant deux jours** — le désabonnement et la chaîne de
> déploiement — **en contredisant le corps du même document**, qui portait déjà la levée de la dépendance
> et la preuve de l'envoi réel. **Une liste d'état se met à jour dans le même geste que le fait qu'elle
> décrit**, sinon c'est elle qu'un lecteur pressé croira.

**Livrables du mandat**

- ✅ **1. Profil complet créé par un humain** — vérifié : profil réel créé avec les vraies commandes, cul-de-sac du niveau 2 corrigé le 6 septembre.
- ✅ **2. Envoi réel** — vérifié : contrat éprouvé contre la vraie API, fil parcouru, message accepté par le fournisseur.
- ✅ **3. Ordonnanceur minimal** — vérifié : minuteur système, créneau manqué rattrapé, battements de cœur éprouvés sur une interruption réelle.
- ✅ **4. Fil de bout en bout** — vérifié : profil → détection → score → envoi, sur données réelles, 12 opportunités livrées.
- ✅ **5. Rétroaction minimale** — vérifié : marquage depuis un lien cliqué, sur une opportunité réelle, le poids d'une sphère a bougé.
- ✅ **6. Désabonnement en un clic** — vérifié en code, en test **et en production**. *Cette ligne disait « contourné en production, réglage bloqué chez le fournisseur ». La dépendance a été levée le 6 septembre — le support a activé « gérer les désabonnements soi-même » — et l'envoi réel du 8 septembre l'a prouvé : **le lien pointe vers notre point d'entrée, pas vers celui du fournisseur**. Corrigée le 8 septembre.*
- ✅ **7. Chaîne de déploiement** — construite, **exécutée et passée au vert** après la préparation de l'hôte *(chantier 29)*. *Cette ligne disait « jamais exécutée, l'hôte n'est pas préparé » — vrai au 6 septembre, faux depuis le 7. Corrigée le 8 septembre.*
- ✅ **8. Journaux d'exploitation** — vérifié : repli éprouvé contre une base injoignable, rapatriement par la chaîne.

**Corrections trouvées en chemin**

- ✅ Réunification des deux chemins de livraison — vérifié, trois défauts reproduits puis corrigés.
- ✅ Réconciliation des livraisons — vérifié sur le rebond réel, 306 opportunités revenues en attente.
- ✅ Suspension après trois rebonds consécutifs — vérifié, compteur remis à zéro sur une remise confirmée.
- ✅ Filtre territorial — vérifié : condition inversée corrigée, 6,8 % → 65,8 % de villes attendues à la source.
- ✅ Score retiré du corps du message, objet et partie HTML — vérifié, 600 tests.

**Clos**

- ✅ **Premier envoi réel arrivé dans une boîte** — vérifié le 8 septembre 2026, 03 h 33 UTC. Courriel
  parti du serveur, arrivé chez le destinataire, **classé en infolettre et non en indésirables**.

**Les cinq vérifications d'en-tête, toutes positives.** Les trois verdicts d'authentification passent
sous une politique en quarantaine. La signature porte le domaine d'envoi avec le sélecteur posé le
5 septembre — **c'est notre domaine qui signe, pas celui du fournisseur**. Le chemin de retour est le
nôtre, donc un rebond resterait détectable. Aucune mention « via ». Et l'en-tête compagnon du un-clic est
présent.

**Et surtout : le lien de désabonnement pointe vers notre point d'entrée**, pas vers celui du
fournisseur. **C'est la preuve que le réglage obtenu du support a pris effet** — le seul moment où
c'était observable. Les deux versions du message portent le même lien, comme le test le verrouillait.

**Le résumé était vide, et la cause est en amont.** Zéro notification en attente : 953 signaux
correspondent au profil, aucun ne porte sur une entreprise vérifiée. **Seulement 0,8 % des entreprises
passent la vérification**, l'appariement par nom laissant 65 % d'ambiguïté. Le vide n'est ni une panne ni
une semaine calme — **c'est la règle de prudence appliquée correctement à des données qu'on ne sait pas
résoudre.** Chantier 4.

**⚠️ Deux variables d'envoi manquaient au fichier d'environnement du serveur**, découvertes par le refus
du garde-fou : l'adresse du point d'entrée public et les deux clés du fournisseur. Le fichier s'était
accumulé par ajouts successifs, chacun correspondant au travail du jour — **rien ne comparait ce qu'il
contenait à ce que le code demande.** Troisième cas du même motif; un contrôle est à construire.
**Rattaché au point 27.10 de l'audit le 9 septembre 2026** — il était consigné ici, dans un mandat clos,
donc invisible à qui cherche du travail à faire.

**Hors chantier, consigné**

- ⬜ Scores qui ne discriminent pas — **chantier 22 d'abord**, puis 4 et 6. Le moteur de notation n'est
  pas en cause : il reflète une entrée uniforme. Sans lecture fine du signal, une notation plus fine
  n'aurait rien de plus à départager.
- ⬜ Source repliée sur une sphère unique — chantier 22.
- ⬜ Enrichissement web avant le seuil — chantier 27.
