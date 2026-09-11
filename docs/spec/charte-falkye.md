# Charte FALKYE

Document de référence à consulter avant toute recherche, proposition de fonctionnalité ou décision de positionnement. Test à appliquer systématiquement : **est-ce que ceci découle de ce que FALKYE fait, ou est-ce une case cochée générique copiée d'ailleurs?**

**Trois documents l'accompagnent, chacun avec son moment de consultation.**

| Document | Quand le lire |
|---|---|
| `falkye-guide-ingenierie.md` | Avant d'ouvrir un chantier, et avant de le déclarer clos |
| `falkye-cadre-legal.md` | Avant d'activer une source |
| `falkye-journal-des-cas.md` | Quand un motif semble se répéter — les renvois « journal, cas N » y pointent |

*La charte tranche les arbitrages; les trois autres portent ce qui s'exécute, se vérifie ou se cherche.*

## 0. Comment cette charte fonctionne

**Le cas fondateur** *(journal, cas 1)* — cinq sources placées au mauvais palier par application mécanique d'une règle, alors qu'une autre section disait le contraire. **Le nombre de sources avait servi de substitut à la qualité des résultats**, ce que cette charte interdit ailleurs en toutes lettres.

**Ce que ça révèle.** Un principe formulé comme une conviction ne se déclenche pas au moment de décider. Formulé comme un test, il ne se déclenche pas davantage s'il n'a pas de **valeur par défaut** — un test sans mesure se résout par l'intuition de la personne pressée, et l'intuition penche toujours du même côté.

**Cinq règles de lecture applicables à toute la charte.**

1. **Un principe qui ne dit pas quoi faire en l'absence de mesure n'est pas utilisable.** Chaque test porte sa réponse par défaut, choisie du côté où se tromper coûte le moins cher — **et choisie délibérément, jamais posée en passant (règle 5)**.
2. **Quand deux règles du corpus se contredisent, la charte tranche** — y compris contre un document opérationnel plus récent. La contradiction se corrige dans les deux documents, jamais dans un seul.
3. **Une mesure prise dans de mauvaises conditions est pire que pas de mesure.** Elle produit une conclusion fausse portée par la confiance d'un fait observé. *(journal, cas 2)* **Avant de mesurer, vérifier que les conditions rendent le résultat interprétable** — sinon attendre, et le dire.
4. **Un principe violé une fois se documente ici, avec le cas réel.** Cette charte n'est pas une déclaration d'intention, c'est la mémoire des erreurs qu'on refuse de refaire.

   **Ce que vaut un incident par rapport à un principe, mesuré sur le corpus lui-même.** Des **sept objets gradués** du produit *(registre, D34)*, **un seul est complet** — critères écrits, seuils chiffrés, et un geste attaché à chaque seuil — **et c'est le seul qu'une erreur réelle a forcé** : la confiance d'appariement, née de 76 paires de doublons non reconnues et d'**une fusion erronée entre deux compagnies légalement distinctes, restaurée depuis une sauvegarde**. **Les six autres ont été posés par raisonnement, ou par rien, et aucun n'est complet.** La corrélation ne dit pas qu'un principe soit sans valeur — elle dit **ce qu'un principe ne produit jamais tout seul** : le chiffre exact, et ce qui se passe quand on le franchit. *Un raisonnement donne l'axe; seul un incident donne le seuil.* **Corollaire de méthode : un objet qu'aucun incident n'a forcé se relit comme incomplet par défaut, même quand il a l'air fini.**
5. **Une échelle ou une règle de calibration absente se signale, elle ne s'invente pas.** Dès qu'un travail bute sur une échelle qui n'existe pas, un seuil non fixé ou une règle manquante, **s'arrêter et le dire**. *Une échelle dit ce que le produit s'autorise à affirmer — c'est une décision de produit, pas une définition technique, et elle ne se prend pas en passant.*

   **Ce que la règle 1 n'autorise pas.** Un défaut au sens de la règle 1 est un défaut **décidé**. **Un défaut décidé est choisi en pesant de quel côté se tromper coûte le moins cher; un défaut posé en passant tire son autorité de sa seule existence.** Ce n'est pas la même chose, et rien ne les distinguait. Une valeur posée pour débloquer devient **la décision que personne n'a prise**, et elle sera défendue plus tard comme si elle en était une. *C'est la règle 3 appliquée aux échelles plutôt qu'aux mesures : sinon attendre, et le dire.*

   **Ce qui se fait sans consultation, et qui doit se faire.** Rapporter **ce que le corpus porte déjà de comparable, et ce qui l'a produit** — l'échelle voisine, le seuil analogue, la décision qui a fixé un cas semblable. Ça donne de quoi trancher plutôt qu'une page blanche. **Un signalement sans ce relevé fait porter le travail deux fois.** L'entrée va au registre des décisions ouvertes *(section 15)*, avec son échéance.

   **Nommer la faculté qui remplira la place, plutôt que d'écrire « à documenter ».** Une échelle sans critères n'est pas toujours un champ mal tenu. Entre la correspondance signal↔besoin et le grade présenté vit **le cerveau du produit et ses cinq facettes** *(`FALKYE-000-PAR-OU-COMMENCER.md`, § Le cœur et le cerveau)*. Une échelle vide est souvent **une place qui attend la faculté qui la remplira** — décider si un signal est réel et fort **est** un acte de lecture, pas une définition à rédiger. **Ce qui n'est pas encore conçu ne se comble pas : il se nomme.** Écrire « **attend la facette X, chantier Y** », et le dire même quand la facette n'a pas de chantier — c'est alors l'information la plus utile du signalement. *Premier cas réel : D34, qui attend la lecture (chantier 22), et le seuil de publication, qui attend le jugement (aucun chantier, D33).*

## 1. Mission

Détecter les entreprises en croissance et rendre ce signal utile à une multitude d'utilisateurs — pas seulement des fournisseurs B2B. Chambres de commerce, conseillers en immigration, développement économique, institutions financières, et d'autres à découvrir. **FALKYE est une solution de détection de la croissance d'entreprise, pas un outil de prospection restreint à un usage.** Ne jamais présumer que vendre un service à l'entreprise détectée est la seule utilisation d'un signal de croissance.

## 2. Le principe fondamental — le test de l'avantage réel

**Un signal isolé, consultable ailleurs dans le même temps de recherche, est un échec.** Avoir accès à une donnée n'est jamais un avantage en soi, même gouvernementale, même gratuite. L'avantage vient du **croisement de plusieurs signaux** pour produire un score propre au profil de l'utilisateur, qu'aucune source seule ne peut donner. Toute nouvelle fonctionnalité s'évalue contre ce test.

**Réponse par défaut en l'absence de mesure.** Ce test suppose qu'on sache ce que les sources produisent déjà — il n'est donc pas applicable tant que la densité de signal par sphère et par territoire n'est pas mesurée. D'ici là, **présumer que le croisement est insuffisant**. Se tromper dans ce sens coûte une source de plus au palier d'entrée; dans l'autre, un palier qui ne livre rien.

## 3. L'avantage défendable

Pas la donnée brute — d'autres y ont accès. L'avantage, c'est le moteur de croisement par sphère de besoin, la veille continue avec notification automatique (la majorité des concurrents n'ont que de la recherche active), et la mise en correspondance service↔besoin, que personne d'autre ne fait.

**Un avantage défendable ne s'érode pas seulement en le retirant — il s'érode en le rendant optionnel par défaut.** Une configuration qui désactive un avantage pour un palier, ou qui l'éteint par défaut, est une décision de charte et non un réglage. *Rendre les notifications désactivables est légitime; faire d'un palier supérieur un palier silencieux par défaut retirerait au client le différenciateur qu'il paie le plus cher, sans qu'il s'en aperçoive.*

## 4. Architecture centrale (vocabulaire de référence)

- **Sphère de besoin** — catégorie générique de besoin, registre extensible.
- **Signal** — un type d'événement détecté, alimenté par des **champs précis** de sources précises, jamais par une source entière d'un bloc.
- **Source, jamais confondue avec une intégration.** Une **source** est un point d'**entrée** qui alimente le moteur. Une **intégration** est un point de **sortie** qui pousse des résultats vers un système externe. Une intégration n'a ni type Piste/Réflexion ni sphère — ces catégories n'existent que pour les sources. **La distinction se floute précisément quand la charge de travail se diversifie.**
- **Score de confiance** — le signal est-il réel et fort? **Score de pertinence** — correspond-il à ce profil? **Confiance d'appariement** — est-il rattaché à la bonne entreprise?
- **La confiance d'appariement plafonne les deux autres au lieu de s'y additionner** : une identité incertaine ne peut pas produire une notification à confiance élevée, quelle que soit la force du signal. **Un signal fort rattaché à la mauvaise entreprise est pire qu'un signal faible bien rattaché** — c'est la seule erreur que l'utilisateur ne peut pas détecter lui-même.
- Ces scores sont des **axes indépendants combinés en matrice, jamais fusionnés en moyenne**. La règle vaut pour N axes : le jour où un quatrième s'impose, il s'ajoute sans que la séparation devienne négociable.
- **Identité et identifiant externe — jamais interchangeables.** L'**identité** est la clé interne du moteur; dossier cumulatif, corroboration et déduplication s'y accrochent. Un **identifiant externe** l'ancre à un territoire et lui apporte son niveau de vérification. Une identité peut en porter zéro, un ou plusieurs, et **une identité sans identifiant externe est valide de plein droit, pas un cas dégradé** — c'est la condition pour fonctionner hors Québec sans réécriture.
- **Type de sphère** — **directe** (une source produit son signal), **dérivée** (règle sur des signaux d'autres sphères), ou **sans couverture**. Une sphère sans couverture est visible comme telle à la configuration, jamais offerte comme si elle fonctionnait. Une règle de dérivation vit dans le registre, jamais seulement dans un document.
- **Usage du moteur** — ce à quoi le moteur est appliqué. FALKYE est **un moteur de croisement appliqué à la prospection d'opportunités d'affaires** : un produit unique, pas un catalogue. Le terme nomme la frontière entre le moteur et sa configuration. *Au moteur* : conservation d'état, quarantaine, santé de source, identité, confiance d'appariement, registre de sources et volet légal, matrice des axes, seuil, structure de faits, cadence, cycle de vie, persistance. *À l'usage* : sphères et synonymes, correspondance signal↔sphère, dimension « qui », gabarits de narratif, personas, sources.

  **Contrainte de non-fermeture, seule chose demandée : l'entité observée est une variable d'usage.** Aujourd'hui une entreprise; un autre usage observerait des immeubles ou des organismes. **Le moteur ne présume jamais la nature de l'entité qu'il suit** — préférer « entité » à « entreprise » là où le moteur n'a pas besoin de savoir, et traiter la vérification du statut légal comme une règle d'usage. **Rien à construire, aucun mécanisme de sélection** : la seule exigence est qu'aucune décision n'oblige à réécrire le moteur si un second usage existait.

- **Extensibilité transversale** — sphères, sources, types de signaux, types de profil, statuts : tout s'ajoute sans restructuration. Une limite découverte en route est normale, pas une erreur de conception.
- **Sources travaillées champ par champ, à deux couches.** *À l'ingestion* : exclusion universelle du bruit administratif, même réponse pour tous. *Au calcul de pertinence* : un champ pertinent pour un utilisateur peut être du bruit pour un autre — cette couche ne se tranche jamais à la capture. **Capter largement une fois, filtrer par lentille ensuite.**
- **Simplicité d'utilisation, quelle que soit la richesse du mécanisme interne.** Poids, sphères multiples, catégories de client : toute cette complexité reste derrière l'assistance de configuration. L'utilisateur décrit son besoin en texte libre; le raffinement manuel est une option, jamais une étape obligatoire.

## 5. Structure de plans

| Plan | Prix | Public réel |
|---|---|---|
| Écho | 29,99 $/mois | Travailleur autonome, petite entreprise — budget serré mais qui paie |
| Radar | 89 $/mois | PME en croissance — le choix qu'on veut voir dominer |
| Radar+ | Dès 349 $/mois — **à réviser** *(registre des décisions ouvertes, D4)* | Grandes entreprises, institutions, cabinets multi-services |

Chaque fonctionnalité se justifie par un besoin réel de ce public précis, jamais par « c'est ce qu'un plan professionnel a d'habitude ».

### Placement d'une source dans un palier

**Le classement se fait par couple source × sphère, jamais par source seule.** Une même source peut être indispensable à une sphère et accessoire à une autre; classer par source force une réponse fausse dans un des deux cas.

- **Source de couverture** — sans elle, la sphère produit zéro résultat ou des résultats non discriminants. Elle appartient au palier où la sphère est offerte, **peu importe son coût et sa nouveauté**.
- **Source d'enrichissement** — elle améliore un résultat qui existerait de toute façon au palier inférieur. Au minimum dans Radar.

**Réponse par défaut : une source nouvelle est réputée de couverture et va au palier d'entrée**, sauf démonstration chiffrée que sa sphère y fonctionne déjà. Le défaut est délibérément inversé par rapport à l'intuition — se tromper vers le bas coûte un argument de vente, vers le haut un abonné qui ne reçoit rien et ne revient pas.

**Vérification à exécuter, pas à espérer :** pour chaque combinaison palier × sphère offerte, au moins une source de couverture doit être présente.

**Piège qui a produit l'erreur d'origine :** « il y a déjà N sources dans ce palier » n'est jamais une réponse. Le nombre de sources n'est pas l'objectif — la précision des résultats l'est.

### La même règle s'applique aux fonctionnalités

Le motif se répète : **une règle écrite pour un palier, puis appliquée mécaniquement aux autres.**

- **Ça corrige l'exactitude de ce qui est montré?** C'est de la couverture. Un fait sur l'entreprise — fraîcheur, durée de pertinence — n'est pas une préférence : le retirer d'un palier ne l'allège pas, ça le rend moins juste.
- **Ça ajoute de la profondeur à un résultat déjà juste?** C'est de l'enrichissement, et la règle de palier s'applique.

**Ce qui alimente les instruments de mesure existe partout.** Retirer la rétroaction d'un palier dégrade le moteur pour tout le monde, en privant l'apprentissage des utilisateurs les plus nombreux.

**Quand une décision de palier bute plusieurs fois sur la même absence, régler la cause plutôt que contourner une fois de plus.** Trois décisions ont buté sur l'absence de tableau de bord au palier d'entrée; l'ajouter a réglé les trois et coûté moins que les trois contournements.

**La frontière entre paliers porte sur ce qu'on peut faire, jamais sur ce qu'on peut voir.** Retenir la visibilité d'un résultat déjà produit rend un palier inutilisable pour la tâche qu'il prétend servir; retenir l'outillage qui permet d'agir dessus est légitime.

## 6. Ce que FALKYE ne fait pas — limites assumées

- **Aucun enrichissement de contact individuel** au-delà des coordonnées déjà publiques sur le site du prospect. Risque de conformité disproportionné par rapport à la valeur — usage secondaire d'une donnée personnelle à des fins de prospection, pas seulement l'envoi du message.
- **Ne révèle jamais ses sources ni son mécanisme là où l'utilisateur peut le voir** — aucun nom de source dans un libellé, une catégorie, un export ou un message d'erreur. Même une intention inoffensive est interdite si ça finit par apparaître. Afficher par territoire ou catégorie neutre. **Deux exceptions délibérées :** la liste des sources payantes du portail, où l'utilisateur choisit explicitement à quel service se connecter; et **la page de crédits des licences ouvertes**, plusieurs exigeant l'attribution même quand les données sont intégrées à une base qu'on possède. Cette page vit **hors du produit** — jamais dans un tableau de bord ni un export. Conséquence à assumer : **la liste des sources ouvertes finit publiée**, ce qui n'expose pas le croisement mais expose une partie de la matière première.
- **Ne vend jamais une promesse de sécurité qu'on ne peut pas tenir.** Une permission est un filtre de confort tant qu'il n'y a pas de vraie authentification derrière.
- **Ne garantit jamais qu'un prospect devienne client.** FALKYE propose des opportunités et des raisons d'approcher, pas des conversions.
- **Frontière du non déterministe — décider contre formuler, proposer contre appliquer.** La raison n'est pas technique : l'utilisateur doit pouvoir comprendre pourquoi ce prospect lui a été montré, et un score qu'on ne peut pas expliquer ne se défend pas devant un client qui le conteste. **Ce n'est pas le ML qui est écarté, c'est l'opacité.**
  - **Aucun composant non déterministe ne produit un score, un seuil ou une décision de publication.** Ce sont les éléments à justifier ligne par ligne devant un client mécontent ou une plainte.
  - **Il peut normaliser une entrée** dans un catalogue fermé — une traduction, pas une décision, vérifiable par échantillonnage. **Il peut formuler une sortie** à partir de faits déjà établis, sans en ajouter aucun.
  - **Test de sécurité automatisable :** si la sortie ne peut pas être reconstruite à partir de la structure de faits qui l'a produite, elle est fausse. Reproductible ne veut pas dire déterministe au caractère près — ça veut dire reconstituable.
  - **Proposer, jamais appliquer.** Un mécanisme peut proposer un seuil ou une pondération; l'activation reste humaine. **Un paramètre qui s'ajuste seul dérive** — un seuil de quarantaine finit par ne plus rien attraper, un score par valider ses propres erreurs.
  - **Le ML classique n'est pas synonyme d'opacité.** Une régression logistique ou un arbre peu profond sont lisibles et restent admissibles pour **proposer** un ajustement une fois assez de rejets accumulés.

## 7. Grille de décision pour une nouvelle fonctionnalité

1. **Est-ce que ça découle du croisement de signaux**, ou est-ce un ajout générique qu'on trouverait identique ailleurs?
2. **Est-ce qu'un persona réel en a besoin concrètement**, pas hypothétiquement?
3. **Est-ce que ça s'appuie sur l'architecture en place**, ou demande une nouvelle source? Les deux sont acceptables, mais il faut le savoir avant de proposer.
4. **Est-ce qu'on risque de vendre une promesse qu'on ne peut pas tenir** — sécurité, conformité, précision?
5. **Est-ce que ça tient sur tous les territoires où on l'offre?** Une garantie honorable seulement au Québec est une promesse à moitié tenue. *(journal, cas 3)*
6. **Est-ce que ça a tourné contre le vrai service, ou seulement contre un mock?** Une fonctionnalité construite et testée n'est pas éprouvée. Elle se documente comme **construite mais non validée en réel** — ni un ✓ ni un tiret. Ça ne bloque pas le développement, ça bloque la promesse commerciale.

Échouer au test 1 ne rejette pas une fonctionnalité, mais elle doit être reconnue comme telle plutôt que présentée comme un différenciateur. **Les tests 4, 5 et 6 ne se contournent pas** : ils portent sur ce qu'on affirme au client.

## 8. Ne jamais présumer une limite — ni une capacité — non testée

**Le réflexe correct n'est jamais d'écarter un outil sur la base de ce qu'il semble avoir été conçu pour faire — c'est de tester contre le besoin réel avant de conclure**, dans un sens comme dans l'autre.

**La règle est symétrique, et c'est la moitié qui manquait. Ne jamais présumer une capacité non testée non plus.** Un connecteur qui passe ses tests contre des mocks n'a rien prouvé sur le service réel. **Présumer une limite fait rater une occasion; présumer une capacité fait vendre une promesse.**

*Les corollaires opérationnels — comparaison d'options, intégrations à un compte tiers, états de validation — sont au guide d'ingénierie.*

## 9. La méthode de diagnostic

Un processus répétable à appliquer à toute spécialité avant de conclure qu'aucun signal n'existe.

1. **Quoi** — quelles sphères couvrent le service, potentiellement plusieurs plutôt qu'une seule forcée.
2. **Qui** — quel type de client cible, qui doit pouvoir rester ouvert quand le service est horizontal.
3. **Territoire** — où.
4. **Source** — si aucun signal direct n'existe pour cette combinaison, chercher activement la source qui le donnerait avant de conclure à une limite du produit. **Jamais présumer l'absence sans avoir cherché.**

*(journal, cas 5)* **C'est un service humain autant qu'un outil**, qu'un concurrent vendant l'accès aux données ne peut pas reproduire. **Réserve à ne jamais escamoter :** ce diagnostic demande une recherche active à chaque nouvelle spécialité, un coût en temps que la documentation du processus ne fait pas disparaître.

### Cinquième étape — le diagnostic à rebours

Les quatre étapes partent toujours du service pour aboutir à une source. Cette direction ne repose jamais la question sur les sources **déjà actives**, et elle la pose au niveau de la source plutôt que du champ.

**Avant de conclure qu'une sphère n'a pas de source : parcourir l'inventaire des champs de toutes les sources actives et chercher ce qui, au niveau du champ, sert déjà cette sphère.** *(journal, cas 6)* Ce n'était pas « aucune source », c'était « aucune source **seule** » — la thèse même du produit.

**Garde-fou obligatoire, sans quoi cette étape fabrique des liens plausibles :** un lien champ → sphère n'est jamais activé sur la seule foi de la proposition. Il doit être **réfuté ou confirmé par l'historique réel** — s'il ne discrimine pas, il est rejeté.

**Journaliser les diagnostics négatifs autant que les positifs.** « Cherché, rien trouvé, à telle date, voici où » évite de refaire la même recherche infructueuse et fait décroître le coût du diagnostic. **Un diagnostic dont le résultat est une absence reste un résultat.**

### Sixième étape — l'arrêt à la première donnée réelle

**Chaque fois qu'une source livre ses données pour la première fois, s'arrêter et chercher les angles morts.** Pas après quelques semaines d'exploitation : au premier contact avec le contenu réel, seul moment où l'on voit ce que la source dit vraiment plutôt que ce qu'on supposait.

**Trois questions.** *Quelles entités décrit-elle réellement?* — le système d'appel d'offres en décrit **deux**, le fournisseur et l'organisme acheteur, et le produit n'en voyait qu'une. *Quels champs porte-t-elle qu'on n'exploite pas?* — l'objet du contrat était là depuis le début, d'où une source entière repliée sur une sphère unique. *À quel moment chaque besoin se manifeste-t-il?* — certains précèdent l'exécution, d'autres la suivent de plusieurs mois : **un signal peut être daté sans être encore pertinent.**

**Ce que cette étape protège.** La promesse n'est pas de détecter des événements, c'est de **connecter les données des sources entre elles pour donner un portrait exact d'une situation**. Une source lue trop grossièrement produit un portrait faux plutôt qu'incomplet — **et un portrait faux se remarque moins qu'un vide**.

**Garde-fou :** élargir la lecture ne veut pas dire multiplier les correspondances. **Un signal qui sert cinq sphères sans discriminer n'en sert aucune** — il produit du bruit crédible, pire que le silence. **Ce qui transforme une correspondance en lecture, c'est la condition** : « un contrat annonce un besoin en cautionnement » est du remplissage; « un premier contrat, ou un contrat disproportionné par rapport aux effectifs déclarés » est une lecture, et elle est mesurable.

## 10. Aucune source n'est une colonne vertébrale

Aucune source, pas même le REQ, n'est irremplaçable ou fondatrice — cette façon de penser crée une fragilité et contredit l'extensibilité. **Une source se classe par son rôle fonctionnel dans un territoire donné, jamais par son identité.**

- **Source Piste** — elle ancre le dossier cumulatif en fournissant un identifiant stable qui sert de pivot pour dédupliquer et corroborer dans le temps.
- **Source Réflexion** — elle enrichit le signal d'une entreprise déjà ancrée, mais n'établit jamais seule l'identité d'un dossier.

**La classification est propre à chaque territoire.** Le Québec n'a qu'une source Piste, non parce que le REQ a un statut spécial, mais parce que c'est la seule qui y fournit un identifiant fiable. Un autre territoire pourrait en exiger deux combinées.

**Elle est aussi propre à chaque type d'entité.** Une même source peut **ancrer** une famille et seulement **enrichir** une autre : le système d'appel d'offres fournit un identifiant aux **organismes publics** et aucun aux **entreprises**. Il est donc **Piste pour les uns, Réflexion pour les autres** — même source, même moment.

**Deux réserves.** Un identifiant stable ne suffit pas : il doit être **exhaustif pour sa famille**, sinon c'est un Piste partiel. Et un identifiant propre à une source n'est pas universel — si une autre source désigne la même entité autrement, le rapprochement reste à faire.

**Identifiant Piste et clé du moteur — les confondre est le piège le plus coûteux de cette section.** Que le NEQ soit la colonne vertébrale **du Québec** est correct. Qu'il serve de clé **du moteur** ne l'est pas : déduplication, corroboration, dossier cumulatif et vérification d'exclusion ne sont pas propres au territoire québécois — elles s'appliquent identiquement à une entreprise qui n'aura jamais de NEQ.

**La clé du moteur est l'identité interne, jamais un identifiant de territoire.** Un identifiant Piste ancre l'identité et lui apporte son niveau de vérification; il ne la remplace pas. **Une identité portant un NEQ doit rester strictement aussi bien servie qu'avant** — critère de non-régression, pas effet secondaire acceptable.

**Pourquoi ça se traite tôt :** le coût de la correction est proportionnel au volume déjà accumulé sur la mauvaise clé. Tant qu'un seul territoire est ancré, la confusion ne se voit pas et ne coûte rien.

**Piste partiel — une nuance, pas une troisième catégorie.** Une source peut fournir un identifiant fiable sans couvrir toutes les entreprises d'un territoire. Elle reste une vraie source Piste pour le sous-ensemble qui s'y qualifie : couverture incomplète, pas réflexion déguisée.

## 11. La vérification — renvoi

**Les règles de vérification vivent dans `falkye-guide-ingenierie.md`** : ce qu'un test vert ne prouve pas, le glissement du décidé au fait, les critères de clôture d'un chantier, et les pièges de relecture. Elles sont opérationnelles plutôt qu'arbitrales — à lire avant d'ouvrir un chantier, pas au moment de trancher une décision de produit.

**Deux règles y sont toutefois assez structurantes pour rester ici.**

**Un chantier n'est clos que sur l'état observable du système.** Pas « les tests passent » ni « le code est poussé », mais « l'application répond sur l'hôte », « la base contient le miroir ». Chacun se vérifie en une commande, et **le critère doit couvrir tout ce que le chantier prétend livrer**.

**La preuve voyage avec le fait.** Pas « le serveur est actif » mais « le serveur répond, vérifié le 5 septembre par connexion » — de sorte qu'une reprise qui la perd se voit. **Et un fait sans preuve attachée ne peut pas servir de prémisse à autre chose.**

## 12. Les sources — statut légal

Les sources ne sont pas l'avantage défendable — c'est le moteur de croisement. Mais **sans source active sur un territoire, aucun résultat, donc une perte de crédibilité et non une fonctionnalité manquante.** La recherche de sources se traite avec le même sérieux que n'importe quel chantier.

**Une donnée publique ne rend pas tout usage commercial légal.** La question se pose avant d'activer, pas après un signalement.

**Trois règles à ne jamais oublier, le raisonnement complet étant dans `falkye-cadre-legal.md`.**

- **« On n'affiche rien » est une défense contre une réclamation en droit d'auteur, jamais contre une clause contractuelle.** Les conditions d'utilisation visent l'ingestion, pas l'affichage.
- **Le canal de diffusion détermine le statut légal, pas l'organisme.** Le même fait peut être exploitable via un portail de données ouvertes et interdit via une page ministérielle — et une licence ouverte ne se présume jamais à partir du portail, seulement de la fiche du jeu précis.
- **Vérifier en priorité les sources qu'on croit acquises.** Une source récente passe par le gabarit d'activation; une source d'origine n'y est jamais passée. *(journal, cas 17)*

**Le volet légal est une case obligatoire du gabarit d'activation**, au même rang que la règle de calibration.

## 13. La qualité des résultats est le vrai cœur du produit

Le critère qui détermine si une source appartient au palier d'entrée n'est **ni** « est-ce gratuit » **ni** « est-ce que ça enrichit un résultat déjà présent ». La vraie question : **le palier d'entrée, avec ses sources actuelles, produit-il des opportunités crédibles pour cette sphère, la majorité du temps?**

Si oui, une source additionnelle est un vrai enrichissement, légitimement réservé à un palier supérieur. Si non — résultats ordinaires, caducs ou trop rares — cette source est nécessaire au palier d'entrée pour que le produit fonctionne, **peu importe qui la paie**. **Un palier d'entrée qui ne trouve jamais rien de bon n'est pas un palier d'entrée, c'est un produit qui ne fonctionne pas.**

**Corollaire à vérifier au cas par cas :** une source dont le coût reste borné et sous contrôle direct peut appartenir au palier d'entrée si elle est nécessaire à la qualité de base pour une sphère donnée. Ça ne s'applique pas automatiquement à un enrichissement systématique à coût nul — la question reste « ce palier fonctionne-t-il sans cette source pour cette sphère précise », jamais un raccourci sur le coût.

**L'instrument manquait, et c'est pour ça que la section a été contournée.** Cette question exige une mesure de densité de signal par sphère et par territoire, calculée sur l'historique réel. Tant qu'elle n'existe pas, appliquer la réponse par défaut de la section 5. **Un test sans instrument n'est pas un test, c'est une opinion à laquelle on a donné la forme d'une règle.**

## 14. Toutes les erreurs ne se rattrapent pas au même prix

**Trois catégories, à reconnaître avant d'arbitrer un ordre de priorité** — « on le fera plus tard » n'a pas le même sens dans chacune.

- **Coût constant** — règle de configuration, attribut de registre, tableau de bord. Se répare dans six mois au même prix. La grande majorité des décisions.
- **Coût croissant** — tout ce qui touche une clé sur laquelle de l'historique s'accumule. Chaque semaine d'attente renchérit. L'identité d'entreprise en est le cas type.
- **Coût irrécupérable** — la donnée non conservée n'existera jamais nulle part. *Cas type : une source dont le signal naît de la comparaison entre deux états, et qui tourne sans conserver le sien.*

**Avant de reporter, déterminer dans laquelle des trois la décision tombe.** Reporter du coût constant est une bonne gestion. **Reporter de l'irrécupérable n'est pas un report, c'est une perte prise sans être nommée.**

### 14bis. L'accumulation ne vaut que si ce qui s'accumule survit

**Tout ce qui fait l'avantage défendable est un actif qui s'accumule** : dossier cumulatif, table d'apprentissage d'appariement, historique d'amplitude, normes de volume, taux de rejet. Aucun ne se rachète ni ne se reconstitue en accélérant plus tard.

**Un actif qui s'accumule dans un environnement dont la persistance n'est pas garantie n'est pas un actif — c'est un compte à rebours.** Question à poser avant de compter sur une accumulation : où vit cette donnée, et qu'est-ce qui garantit qu'elle sera là dans six mois?

**La persistance se vérifie avant de démarrer une accumulation, pas quand on en a besoin.** Le moment où l'on découvre qu'un historique a disparu est précisément celui où il aurait servi.

**Vérifié par les faits le jour même de sa rédaction** — 2,7 Go de données non versionnées perdues au recyclage du conteneur *(journal, cas 14)*. **Trois leçons.** Un risque documenté et non traité n'est pas un risque géré. Un filet qui demande une manœuvre à chaque session ne tient pas au-delà de la deuxième. **Et un incident qui valide un risque à faible coût est une information achetée bon marché — la gaspiller serait de ne rien changer.**

## 15. Une décision non tranchée disparaît

*Une décision réelle a disparu du suivi pendant des mois : ni rejetée ni reportée, simplement sans réponse — et rien ne la faisait revenir (journal, cas 15).*

**Toute entrée à l'état « décision jamais tranchée » porte une échéance et réapparaît à cette date.** L'échéance est obligatoire au moment où l'état est posé, jamais ajoutée après coup.

**Où elles vivent.** *Un registre unique, en tête de `falkye-audit-et-mandat.md`* — créé le 8 septembre 2026 parce que quatorze décisions ouvertes étaient dispersées dans trois documents sans qu'aucune porte de date, cette section comprise. **Une décision ouverte qui n'est pas au registre n'existe pas.**

**Trancher inclut « non, et voici pourquoi ».** Un refus documenté libère l'attention; le silence n'est pas un résultat. Une décision reconduite doit dire ce qui manque pour la trancher, sans quoi elle sera reconduite indéfiniment par le même réflexe.

**Le même mécanisme s'applique à une vérification qui se périme.** Une condition d'utilisation vérifiée à une date ne l'est qu'à cette date : sans échéance de revalidation, **la diligence d'aujourd'hui devient la présomption de dans deux ans**.

## 16. Ce qu'un bon résultat est du point de vue de l'utilisateur

**Un résultat n'est bon que s'il donne une raison d'agir maintenant, pas seulement un nom.** Un nom sans le motif du repérage ne vaut pas mieux qu'une liste achetée ailleurs — c'est le test de la section 2, vu depuis la personne qui paie.

**La précision passe avant le volume, et ce n'est pas symétrique.** Trois mauvais prospects et l'utilisateur n'ouvre plus les suivants; deux bons par mois et il est satisfait. **Le faux positif coûte structurellement plus cher que le faux négatif**, et tout arbitrage se tranche dans ce sens par défaut.

**Corollaire non négociable : ne jamais gonfler le volume pour avoir l'air utile.** La tentation apparaît précisément quand un utilisateur reçoit peu — baisser le seuil, élargir la sphère, envoyer un « à surveiller ». **C'est le geste qui détruit la confiance le plus vite, et il se déguise en service rendu.**

**Ne jamais présenter comme opportunité ce qu'on présenterait soi-même avec réserve.** Si on n'appellerait pas ce prospect à sa place, il ne part pas.

### Trois natures d'objets, et la règle du jugement n'en vise qu'une

**Le corpus range côte à côte des objets de natures différentes, et rien ne les distinguait.** La spécification 8.1 rend l'erreur facile en présentant Confiance et Pertinence comme **trois axes d'une même famille**, alors que l'un est un instrument interne et l'autre est le dernier mot du produit au client. *L'erreur a été faite dans le corpus lui-même, en parlant de « cinq échelles » comme d'un seul ensemble (registre, D34).*

**1. Les instruments internes** — le tier de confiance du signal, la confiance d'appariement, la fiabilité de source. **Le moteur les calcule pour décider.** L'utilisateur n'en voit jamais la valeur, donc **leurs libellés n'ont pas à être ménagés** : les adoucir ferait perdre de la précision au moteur sans rien gagner à personne.

**2. Les données lues** — la taille d'entreprise, la bande d'effectifs, la capacité d'accueil. Ce sont **des faits sur l'entreprise, pas des jugements du produit**, et elles servent de filtre. **Les ménager serait mentir sur un fait.**

**3. Les finalités présentées** — le grade A/AA/AAA. **C'est le dernier mot du produit sur ce qu'il a lui-même décidé de montrer.**

**La règle ci-dessous ne vise que la troisième nature, et c'est ce qui l'empêche de dériver.** Le produit **ne porte jamais de jugement négatif sur ce qu'il a lui-même décidé de présenter** — non par délicatesse, mais **par cohérence** : il l'a choisi. **Mais il le gradue, et la gradation reste parfaitement lisible.** Ce qui est interdit n'est pas de distinguer, c'est de **dénigrer le bas de l'échelle** : *le plus court n'est pas mauvais, il est simplement moins.* Et **une échelle emprunte le jugement de la convention à laquelle elle ressemble** — A/B/C porte le bulletin scolaire que le moteur le veuille ou non, et c'est exactement ce qui a été retiré au cas 16.

**Ne pas étendre la règle aux deux premières natures.** C'est la pente : un libellé interne qu'on adoucit « au cas où », une donnée lue qu'on arrondit vers le haut. **Le test : est-ce que quelqu'un verra cette valeur? Si non, la seule exigence est qu'elle soit juste.**

### Le vocabulaire porte un jugement, et le produit ne juge que ce qu'il sait

**Retirer un découragement que la donnée ne justifie pas, ne jamais ajouter un encouragement qu'elle ne justifie pas davantage.** On ne noircit pas, on n'embellit pas.

*Cas d'origine : l'échelle A/B/C est devenue A/AA/AAA. Classement identique; ce qui a été retiré, c'est un jugement que le produit n'était pas en position de porter (journal, cas 16).*

**Trois applications.** Un **statut de suivi** décrit un fait, jamais une performance : « Joint, sans suite » porte sur le dossier, « Perdu » jugerait le travail de l'utilisateur. Une **réserve** se formule par l'action qu'elle appelle : « lien incertain » invite à ignorer, « à confirmer avant l'appel » dit la même chose en indiquant quoi faire. Une **absence** se formule par ce qui a été fait : « aucune opportunité cette semaine » se lit comme une panne, alors que dire combien d'entreprises ont été suivies rend visible un travail réel.

**La limite qui empêche la règle de dériver.** Retirer un découragement injustifié est légitime; maquiller une absence en promesse ne l'est pas. **Le test : est-ce que je retire un jugement que la donnée ne soutient pas, ou est-ce que j'ajoute une attente que rien ne soutient?**

### La forme de livraison modifie la valeur perçue, à contenu identique

Quinze notifications séparées transforment une bonne nouvelle en irritant; les mêmes quinze livrées ensemble donnent l'impression d'un produit qui travaille. **Un résultat n'existe pour l'utilisateur que sous la forme où il le reçoit.**

- **Le groupement est la forme par défaut; l'envoi unitaire est l'exception justifiée.** L'exception a besoin d'un seuil explicite, sinon elle redevient la norme par glissement.
- **Livrer au moment où la personne peut agir.** Une journée ne change rien à la pertinence d'un signal d'entreprise, et beaucoup à la probabilité que quelqu'un décroche le téléphone.
- **Ça ne justifie jamais de retenir un mauvais résultat mieux emballé.** La forme sert un contenu qui tient déjà.

**Un mécanisme de sortie cassé coûte plus cher que pas de mécanisme du tout.** Un lien de désabonnement mort ne retient pas l'abonné — il le pousse vers le bouton « pourriel », qui coûte à la réputation du domaine entier, donc à la livraison de tous les autres. **Chaque fois qu'on rend difficile un geste que l'utilisateur veut poser, il en pose un plus coûteux à sa place.**

**L'explicabilité est une exigence de produit, pas une préférence d'ingénierie.** Si le moteur de score reste en règles simples, c'est que l'utilisateur doit pouvoir comprendre pourquoi ce prospect lui a été montré — sans qu'on nomme une source. **Un score qu'on ne peut pas expliquer ne se défend pas devant un client qui le conteste.**

## 17. Le silence est le mode de défaillance principal — pas la mauvaise notification

Le pire scénario n'est pas d'envoyer un mauvais prospect, c'est de **n'envoyer rien pendant trois semaines à quelqu'un qui paie**. L'utilisateur ne peut alors pas distinguer trois causes au même symptôme : son territoire est calme, son profil est mal configuré, ou le produit est brisé. **C'est là que se joue la rétention.**

**Le produit doit toujours pouvoir dire pourquoi il est silencieux. Ne jamais laisser l'utilisateur interpréter une absence.**

- **Le silence attendu se dit à l'avance**, à la configuration du profil : quand une combinaison sphère × territoire est structurellement mince, l'annoncer en termes de résultats attendus, **avant que la personne paie**. C'est aussi la meilleure défense contre le reproche de vendre une promesse intenable.
- **Le silence anormal se signale**, et se distingue du silence attendu. Un profil qui ne reçoit rien au-delà de son propre rythme habituel est une anomalie à porter à l'attention de l'utilisateur, pas une donnée à laisser dormir.
- **Le silence prolongé déclenche une intervention utile, jamais un remplissage** : proposer un ajustement de profil, un élargissement de territoire, ou dire honnêtement que cette sphère est mince. **Un « votre secteur est calme ce mois-ci, voici pourquoi » vaut mieux qu'un faux prospect, et infiniment mieux que rien.**

**Interdiction explicite, parce que c'est la pente naturelle : ne jamais abaisser un seuil pour rompre le silence.** Le silence se traite par la transparence et la recherche de sources, jamais par la dégradation de la qualité.

**Trois silences se ressemblent côté exploitation** — la source n'a rien produit, le seuil n'a rien laissé passer, ou le mécanisme est en panne. **Un journal qui ne les distingue pas transforme une panne en semaine calme.** Chaque exécution laisse une trace de début et de fin : l'absence de trace est elle-même un signal.

## 18. Le droit de refuser — l'extensibilité autorise l'ajout, elle n'oblige pas à offrir

L'architecture rend tout extensible, et c'est juste. Mais **une charte qui n'autorise que l'ajout finit par produire un catalogue plus large que ce que le produit sert bien.** Trente-quatre sphères multipliées par les territoires et les types d'utilisateurs, c'est une surface qu'une personne seule ne peut pas valider — **la retenue est une contrainte de ressources assumée, pas un manque d'ambition.**

**Distinguer le registre interne de l'offre commerciale.** Le registre peut contenir une sphère sans couverture, un territoire non couvert, un persona non validé — c'est même souhaitable, ça garde la trace. **L'offre ne présente que ce que le produit sert la majorité du temps.**

**Refuser, retirer et marquer sans couverture sont des opérations normales et documentées, pas des aveux d'échec.** *Le corpus en contient des précédents réussis.* Ce qui manquait, c'était le principe qui rend le geste légitime plutôt qu'exceptionnel.

**Ajouter une sphère, un territoire ou un persona, c'est s'engager à le servir.** La question avant l'ajout n'est pas « est-ce que ça rentre dans l'architecture » — la réponse est toujours oui — mais **« est-ce qu'on peut le servir la majorité du temps, et qui va le vérifier »**.

## 19. Un avantage vérifié une fois n'est pas vérifié pour toujours

**L'affirmation initiale de l'avantage défendable était fausse**, et il a fallu la corriger après recherche *(journal, cas 18)*.

**La section 3 se relit et se revalide à échéance** *(registre, D8)*, comme toute vérification qui se périme. **Un avantage défendable affirmé il y a un an et jamais revérifié est une présomption, pas un avantage.**

**Trois déclencheurs obligent une revue immédiate, sans attendre l'échéance :** un concurrent annonce de la veille continue ou de la notification automatique; un concurrent se met à faire de la mise en correspondance service↔besoin; un fournisseur de données lance un produit dérivé destiné aux fournisseurs de services plutôt qu'aux chercheurs de contrats.

**Si un avantage défendable tombe, il sort du matériel de vente le jour même** — sans attendre de savoir par quoi le remplacer. Vendre un différenciateur qu'un concurrent offre aussi est une promesse qu'on ne peut pas tenir. **Constater qu'un avantage s'est refermé n'est pas une mauvaise nouvelle à retarder : c'est l'information la plus utile qu'on puisse obtenir sur son propre positionnement.**

## 20. Question ouverte, avec échéance — la méthode est-elle le produit?

La section 9 affirme que la méthode de diagnostic est un service humain autant qu'un outil, et que c'est ce qu'un concurrent vendant l'accès aux données ne peut pas reproduire. **Si c'est exact, ce serait la chose la plus difficile à copier de tout le projet** — les données, elles, sont accessibles à quiconque.

Or la tarification traite cette méthode comme un avantage accessoire du palier supérieur. **Si l'affirmation de la section 9 tient, c'est peut-être la méthode qui est le produit et le logiciel qui en est le véhicule** — ce qui changerait le positionnement, le prix et le premier public visé.

**Les deux lectures sont défendables et aucune n'est à retenir aujourd'hui.** Ce qui compte, c'est que la question ne se reperde pas : **elle est au registre des décisions ouvertes, D7**, et **la trancher inclut « non, le logiciel reste le produit, et voici pourquoi »**.

## 21. Les forces structurelles

**Une force qu'on n'exploite pas n'est pas une réserve gardée pour plus tard — c'est une décision de ne pas s'en servir, prise par défaut.**

**Le principe qui unifie les quatre : l'avantage ne vient pas de ce à quoi le produit a accès, il vient de ce qu'il conserve.** Un concurrent interroge une base et oublie la question; FALKYE garde un dossier qui se construit, un registre qui s'enrichit, une table d'appariement qui apprend, et un journal de ce qu'on lui a demandé sans qu'il sache le faire. **Aucun de ces quatre actifs ne s'achète** — ils ne peuvent que s'accumuler, et un nouvel entrant repart de zéro même en achetant les mêmes données le lendemain. **Corollaire qui change les priorités : l'horloge du produit tourne sur l'accumulation, pas sur le développement.**

**Force 1 — La mémoire rend expressible ce qu'une recherche ne peut pas formuler.** *Le signal par absence* : l'absence d'un signal normalement attendu est elle-même un indicateur — croissance d'effectifs et nouvel établissement **sans** financement ni classement visible signalent une traction précoce. **Un outil de recherche ne peut pas exprimer une absence** : il faut connaître l'ensemble de ce qui aurait dû apparaître, et l'avoir gardé. *La trajectoire* : trois signaux en deux mois valent mieux que trois en deux ans, à confiance égale. **Ce sont les seules choses qu'un concurrent ne peut pas reproduire en achetant les mêmes données** — donc à traiter en première classe, jamais comme des bonus.

**Force 2 — Le journal de diagnostic est un signal de demande.** Il collecte ce que des utilisateurs réels ont demandé et que le produit n'a pas su servir. **Aucune étude de marché ne vaut cette donnée, et elle s'accumule sans effort.** À lire comme une demande de marché à intervalle régulier, pas seulement comme une liste de correctifs.

**Force 3 — Mesurer plutôt qu'estimer, quand la mesure existe.** Certaines sources livrent une mesure de taille réelle. **Mesure, estimation et absence coexistent avec leur niveau de fiabilité assumé**, jamais fusionnées en un chiffre dont on ne sait plus d'où il vient. *Corollaire général : un signal ne veut rien dire sans sa base de comparaison.* Cinq offres d'emploi chez dix personnes et chez cinq cents n'ont pas le même sens — **sans normalisation par taille et secteur, tout signal de volume favorise mécaniquement les grandes entreprises**, c'est-à-dire celles qui ne sont pas la clientèle visée.

**Force 4 — La méthode s'accumule, contrairement à l'accès aux données.** Chaque diagnostic enrichit le registre de façon permanente et sert tous les suivants : **le coût marginal décroît, l'actif croît** — l'inverse d'un accès aux données, qui coûte le même prix à tout le monde et n'appartient à personne.
