# Repéreur d'entreprises en croissance — Spécifications du projet

## Principes directeurs — à respecter dans toute proposition future

Ces principes gouvernent l'ensemble du projet. Toute nouvelle source, fonctionnalité, ou modification proposée doit être vérifiée contre cette liste avant d'être ajoutée — pas seulement contre la logique du moment.

1. **Aucune donnée fictive ou simulée, jamais, même temporairement.** Les vraies données réelles sont non négociables, y compris pendant le développement et les tests.
2. **Toute source gratuite et de bonne qualité fait partie du produit, sans exception de priorisation.** Une source n'est écartée que pour deux raisons précises : elle est légalement inaccessible, ou elle exige un abonnement payant (décision budgétaire qui revient à Alexandre, jamais un choix fait à sa place).
3. **Principe de calibration, non négociable : aucune source n'est activée sans une règle concrète et vérifiable qui distingue un vrai signal de croissance du bruit.** Une source qui ne peut pas être calibrée reste en réserve, non activée — le nombre de sources actives n'est jamais l'objectif, la précision des résultats l'est.
4. **Vérifications de base obligatoires avant toute présentation d'un prospect** (statut légal, signe d'activité, cohérence d'identité) — dans tous les modes d'usage, sans exception.
5. **Un seul indice de confiance unifié par notification** — jamais de jauges parallèles (urgence, gradation séparée par signal, etc.).
6. **Polyvalence d'utilisation : rien n'est codé en dur pour le cas d'usage d'Alexandre.** Le produit doit rester utilisable par une multitude de types d'utilisateurs — pas seulement des fournisseurs de services B2B — avec la même architecture, sans modification de code.
7. **Architecture modulaire pour tout ce qui est amené à évoluer** — sources, types de signaux, type de profil (fournisseur/client/les deux) — chacun avec son propre registre extensible, sans jamais nécessiter une restructuration pour ajouter un nouvel élément.
8. **Le NEQ (ou l'identifiant équivalent hors Québec) sert de pivot** pour dédupliquer, corroborer, et maintenir un dossier cumulatif par entreprise dans le temps — jamais des événements isolés et déconnectés.
9. **Ne pas complexifier l'architecture en anticipation de cas non confirmés** (ex. logique inversée pour le déclin, agrégation régionale) — rester concentré sur ce qui est demandé, pas sur ce qui pourrait éventuellement l'être.

## 1. Contexte et origine

Alexandre est en transition vers un positionnement de consultant indépendant en implantation de systèmes de gestion d'inventaire et d'actifs (plateforme Hector). Plutôt que de chercher des offres d'emploi classiques, il cherche à identifier des entreprises en forte croissance — celles qui, en grossissant, perdent le contrôle de leur inventaire ou de leurs actifs — avant même qu'elles publient un appel d'offres ou réalisent elles-mêmes qu'elles ont un problème.

Les outils existants (Owler, ZoomInfo, Apollo, Lead411, Crunchbase) sont trop chers (75$ US+/mois) et pensés pour des équipes de vente, pas pour des travailleurs autonomes ou micro-entreprises.

## 2. Promesse produit

L'utilisateur configure une seule fois son profil : localisation (ville, région, état/province, pays), rayon d'action, et un ou plusieurs services/sphères de besoin offerts. Le système surveille ensuite en continu des signaux publics de croissance et notifie l'utilisateur dès qu'une entreprise correspond, avec :

- la **raison précise** du repérage (quel signal, quelle source),
- la **sphère de besoin probable** concernée chez cette entreprise,
- un **niveau de confiance** du signal.

L'utilisateur peut aussi ajuster sa **sensibilité de notification** (Faible/Moyen/Élevé), et lancer en tout temps une **recherche ponctuelle** plus large, indépendante de son profil configuré.

Promesse centrale : remplacer des heures de veille manuelle par une liste courte et justifiée d'entreprises ayant probablement besoin du service, avant même qu'elles publient un appel d'offres.

## 3. Zone géographique

- **Démarrage : Québec**, parce que les sources y sont connues et en bonne partie gratuites.
- Le système doit être **conçu dès le départ pour être adaptable/configurable par région** (pas codé en dur pour le Québec) — une fois la mécanique validée, on réplique la même logique pour d'autres régions en changeant les sources locales derrière le même moteur.

## 4. Structure du profil utilisateur

| Champ | Description |
|---|---|
| **Type de profil** | **Fournisseur / Client / Les deux** — voir sous-section ci-dessous |
| Ville / région / état-province / pays | Localisation de l'utilisateur |
| Rayon de déplacement acceptable | Distance/zone dans laquelle l'utilisateur est prêt à travailler |
| Sphère(s) de besoin | Catégorie générique réutilisable — voir liste complète ci-dessous |
| Service(s) précis | Spécifique à l'utilisateur (ex. Alexandre : implantation Hector) — **plusieurs paires sphère+service possibles en parallèle** |
| Sensibilité de notification | Seuil Faible/Moyen/Élevé filtrant les signaux selon leur score de confiance |

Chaque paire sphère+service est scannée en parallèle ; la notification précise laquelle a matché.

### Porte ouverte : profils fournisseur et client

Le produit tel que conçu pour le prototype 1 sert exclusivement le point de vue du **fournisseur** — quelqu'un qui offre un service et cherche des entreprises en croissance ayant potentiellement besoin de ce service. Mais la structure de données doit dès maintenant prévoir un champ **type de profil**, avec trois valeurs possibles :
- **Fournisseur** : le profil actuel, tel que documenté dans ce document — offre un service, cherche des clients en croissance.
- **Client** : une entreprise qui a elle-même un besoin (une sphère de besoin, sans service à offrir) et qui pourrait éventuellement être mise en correspondance avec des fournisseurs pertinents.
- **Les deux** : un utilisateur qui agit dans les deux rôles à la fois.

**Ce que ça implique pour la v1, et ce que ça n'implique pas :**
- Le champ `type de profil` doit exister dans la structure de données dès le départ, pour éviter une restructuration plus tard.
- **La mécanique de correspondance client-fournisseur (bidirectionnelle) n'est pas construite pour le prototype 1.** Le moteur de scan et de notification du prototype 1 reste entièrement basé sur la détection de signaux externes pour des profils fournisseurs, comme documenté dans ce document.
- Cette porte ouverte est une décision d'architecture, pas une fonctionnalité à livrer maintenant — elle prépare seulement un futur où des profils clients pourraient exister dans le même système sans tout reconstruire.

### Mode de saisie

- **Sphère de besoin :** liste prédéfinie (sélection dans la liste ci-dessus), pour que le système puisse faire correspondre automatiquement les signaux détectés à une catégorie cohérente. Extensible au besoin (voir ci-dessus).
- **Service précis :** **texte libre**, saisi par l'utilisateur, car chaque utilisateur décrit sa spécialité avec ses propres mots (ex. "implantation Hector" pour Alexandre). Une liste fermée serait trop limitante ici.
- Suggestion : ajouter en parallèle un ou deux **mots-clés/tags optionnels**, choisis ou extraits par l'utilisateur, pour enrichir le texte libre sans le remplacer et faciliter la correspondance future.

### Liste des sphères de besoin

La liste doit être **la plus large possible** pour permettre au produit de s'adresser à un maximum de types d'entrepreneurs et de PME, pas seulement à des profils comme celui d'Alexandre. Cette liste, comme les sources, doit être **extensible** : un entrepreneur qui ne se reconnaît dans aucune sphère existante doit pouvoir en proposer une nouvelle sans que ça brise la structure du système.

- Gestion d'inventaire et d'actifs
- Ressources humaines / recrutement / dotation
- Comptabilité / finance / fiscalité
- Juridique / conformité réglementaire
- Technologie / systèmes / TI
- Cybersécurité
- Logistique / transport / gestion de flotte
- Chaîne d'approvisionnement / achats / approvisionnement
- Marketing / vente / développement des affaires
- Sécurité (physique, surveillance, contrôle d'accès)
- Immobilier / gestion d'espaces / aménagement
- Construction / rénovation / entretien de bâtiments
- Santé et sécurité au travail (SST)
- Environnement / développement durable / ESG
- Gestion de projet
- Production / opérations manufacturières
- Ingénierie / design industriel
- Service à la clientèle / support technique
- Formation / développement des compétences
- Traduction / communications multilingues
- Relations publiques / communication corporative
- Gestion documentaire / archivage
- Assurance / gestion des risques
- Import / export / douanes
- Automatisation / robotique
- Analytique d'affaires / gestion de données
- Efficacité énergétique / gestion de l'énergie
- Franchisage / développement de réseaux
- Commerce de détail / e-commerce
- Restauration / gestion alimentaire
- Agriculture / agroalimentaire
- Entretien ménager / conciergerie commerciale
- Gestion de la paie / avantages sociaux
- Planification stratégique / conseil en gestion
- Financement / accès au capital

## 5. Modes d'usage

1. **Recherche ponctuelle à la demande** : plus large, sans lien strict au profil, sans notion de nouveau/déjà-vu.
2. **Veille continue par notifications** : basée strictement sur le profil configuré, avec suivi d'état pour éviter les doublons.

Même moteur de scan sous-jacent pour les deux modes.

### Résumé périodique, en complément des notifications individuelles

En plus des notifications au cas par cas, le système doit offrir un **résumé périodique** (ex. hebdomadaire) regroupant toutes les entreprises repérées durant la période — pour donner une vue d'ensemble et réduire la fatigue de notification en mode veille continue. Les deux formats coexistent, l'un ne remplace pas l'autre.

### Dossier cumulatif par entreprise

Le système doit maintenir un **dossier cumulatif par entreprise** (identifiée par son NEQ, voir section 9) plutôt que de traiter chaque détection comme un événement isolé et déconnecté des précédents. Concrètement :
- si une entreprise déjà repérée par le passé (ex. un palmarès en janvier) déclenche un nouveau signal plus tard (ex. le RDPRM en juin), le système doit le reconnaître comme faisant partie du même dossier, pas comme une nouvelle entreprise détectée du néant,
- la corroboration multi-signaux (section 6) s'applique donc aussi bien à des signaux rapprochés dans le temps qu'à des signaux étalés sur plusieurs mois, tant qu'ils concernent la même entreprise,
- ça permet de présenter à l'utilisateur une histoire qui se construit dans le temps plutôt que des mentions isolées et sans lien apparent entre elles.

### Tableau de bord et statut de suivi — Radar et Radar+ seulement

Vue tableau de bord listant les dossiers cumulatifs sous forme de pastilles/cartes, réservée aux plans Radar et Radar+ (absente d'Écho). Chaque carte affiche :
- le code de pertinence (A/AA/AAA, section 6) et le score de confiance,
- le lien vers le site web du prospect et les coordonnées trouvées via l'enrichissement contextuel (section 10),
- un **statut de suivi**, propre à l'utilisateur, distinct du score de pertinence/confiance : ex. "À joindre" (défaut), "Joint", "Premier appel prometteur", et d'autres valeurs. **Liste de statuts extensible**, suivant le même principe que les sphères de besoin, les sources et les types de signaux (section 9/9bis) — un statut n'existant pas doit pouvoir être ajouté sans restructuration.

**Lien avec la rétroaction utilisateur (anciennement en attente, résolu ici) :** un statut "Pas pertinent" sert une double fonction — suivi de pipeline pour l'utilisateur, et signal de rétroaction pour le moteur de pertinence (section 6) : quand un prospect est marqué ainsi, le système doit légèrement réduire le poids des mots-clés/sphères qui ont produit sa correspondance pour les prochaines notifications de cet utilisateur. Règle simple, pas de ML, cohérent avec le principe déjà établi.

### Trois fonctionnalités transversales additionnelles — pertinentes à la majorité des personas, aucune nouvelle source requise

1. **Modèles de premier contact contextuels** : génère une amorce de message adaptée au signal précis détecté (ex. valeur et donneur d'ordre d'un contrat décroché, ville et date d'un nouvel établissement). S'appuie sur les données déjà captées par signal (section 7) et l'enrichissement web (section 10). Se connecte directement au statut "Premier appel prometteur" du tableau de bord ci-dessus.
2. **Carte géographique interactive des prospects** : vue carte, pastilles de pertinence positionnées par territoire, alternative à la vue liste du tableau de bord — même donnée, présentation différente. Pertinent pour les personas dont le service est livré localement.
3. **Filtre par taille d'entreprise estimée (nombre d'employés)** : dérivé des signaux d'embauche cumulés déjà captés (Guichet-Emplois, EIMT, section 7) et du dossier cumulatif par entreprise — nouvelle couche de calcul, pas une nouvelle source.

### Fonctionnalités Radar+ — au-delà du portail ouvert, pour un vrai positionnement professionnel/institutionnel

Reprises depuis la charte FALKYE (section 7, grille de décision) : chaque fonctionnalité ci-dessous a été validée contre un besoin réel de personas Radar+ identifiés, pas copiée d'un générique "plan professionnel".

1. **Profils de recherche multiples simultanés (multi-usage × multi-territoire)** — nouveauté centrale de cette révision. Un compte Radar+ peut définir **plusieurs combinaisons sphère de besoin/usage précis × territoire**, chacune fonctionnant comme une veille indépendante mais gérée sous un seul compte, en parallèle. **Meilleur exemple concret, ancré dans un vrai persona (sphère gestion de projet) :** une firme de gestion de projet externalisée (PMO-as-a-service) gère par nature plusieurs mandats simultanés, souvent dans des secteurs et territoires différents — un mandat implantation de systèmes au Québec, un mandat expansion physique en Ontario, chacun avec ses propres notifications sous un seul compte. Autres exemples : une entreprise offrant à la fois du recrutement et de la formation, active au Québec et en Ontario, gère ses quatre combinaisons sous un seul compte plutôt que quatre profils séparés; une chambre de commerce régionale pourrait suivre simultanément la croissance générale de son territoire ET un sous-segment (ex. entreprises manufacturières) pour deux types de rapports différents — même mécanique, usage entièrement différent (voir charte, section 1). Chaque combinaison produit ses propres notifications, filtrables dans le tableau de bord par usage ou par territoire. S'appuie directement sur l'architecture de profil déjà établie (sphères de besoin multiples, mots-clés d'usage précis, territoire) — l'ajout, c'est de permettre plusieurs instances de cette combinaison par compte plutôt qu'une seule.
2. **Alertes composites préconfigurées par cas d'usage** (remplace l'ancienne "pondération du moteur de score personnalisable", jugée trop abstraite pour un usage réel) : plutôt qu'un curseur générique de pondération, des modèles concrets ancrés dans des croisements de signaux déjà identifiés — ex. "alerte cautionnement" (contrat public + jeune entreprise), "alerte financement précoce" (croissance sans subvention ni classement encore visible), "alerte acquisition" (classement de croissance + subvention + entreprise jeune). Personnalisation réelle, ancrée dans des cas d'usage vérifiés plutôt que dans une abstraction.
3. **Tableaux de bord agrégés par territoire** : au-delà des prospects un à un, une vue agrégée ("X entreprises en croissance détectées dans votre région ce trimestre, réparties par secteur") — sert un besoin concret de reddition de comptes pour des personas comme le développement économique régional, qui doivent justifier leur propre impact à un conseil ou à un palier gouvernemental. **Construit, mais limite réelle découverte en testant, non résolue :** le secteur d'activité du REQ est un texte libre si granulaire (~211 valeurs distinctes sur 311 notifications réelles) que l'agrégation par secteur reste peu utile telle quelle — deux entreprises du même secteur peuvent avoir un libellé différent, ce qui casse le regroupement. **Décision ouverte, pas encore tranchée :** investir dans un vrai regroupement (SCIAN/NAICS) pour rendre l'agrégation utile, ou lancer tel quel avec une agrégation plus grossière en attendant (ex. regroupement manuel des libellés les plus fréquents plutôt qu'une classification complète).
4. **Accès prioritaire aux nouvelles sphères/sources** : un client Radar+ qui identifie un besoin non couvert (comme vécu avec la sphère "Financement / accès au capital") obtient une priorité réelle sur les décisions de développement futures.
5. **Accès API/webhook complet** : pousser chaque nouveau signal (filtré par seuils de confiance/pertinence du profil) vers un système externe de l'institution plutôt que d'exiger la consultation d'un dashboard — transforme FALKYE d'un outil consulté en infrastructure intégrée aux systèmes internes du client (CRM propriétaire, ERP, système de gestion des risques).
6. **Sous-comptes et territoires assignés, avec rôles — reclassé comme répartition de volume, pas comme sécurité.** Le vrai besoin identifié chez les personas Radar+ réels (développement économique régional, cabinets multi-agents) est de distribuer automatiquement les bonnes notifications à la bonne personne selon son secteur/territoire assigné, pour réduire le bruit — pas d'empêcher un collègue de la même organisation de voir les données d'un autre territoire. **Mise à jour : l'authentification réelle est maintenant construite et validée (336/336 tests, scénario complet en direct).** `Profile` et `SousCompte` sont authentifiés par le même mécanisme (mots de passe hachés via `hashlib.scrypt`, session obligatoire, `_identite_courante` sur 19 commandes CLI). La mise en garde documentée précédemment ("ce n'est pas une frontière de sécurité") ne s'applique plus — c'en est une, réellement. Deux limites honnêtes restent documentées, pas des failles : le mode opérateur (`FALKYE_OPERATOR=1`, réservé à Alexandre) ne protège jamais contre lui-même par conception; l'authentification prouve qui a exécuté une commande, pas qui l'a physiquement tapée (limite normale de tout système par session). Gap fermé en prime pendant ce chantier : `billing definir-plan` (contourne Stripe) était accessible sans restriction — réservé au mode opérateur maintenant, un client ne peut plus se donner Radar+ gratuitement.
7. **Détection d'expansion inter-provinciale** — nouvelle capacité générale, pas liée à une seule sphère. Repère quand une même entreprise apparaît dans les signaux de croissance de plusieurs provinces (ex. REQ au Québec ET licences Vancouver/Toronto ET contrats Nouvelle-Écosse), peu importe la sphère de besoin de l'utilisateur qui la reçoit — bénéficie directement aux profils Radar+ qui gèrent déjà plusieurs territoires (voir fonctionnalité 1, profils multiples). Particulièrement pertinent pour les personas traduction/communications multilingues et franchisage/développement de réseaux, sans leur être exclusif. **Limite honnête à documenter avant de construire quoi que ce soit :** aucun identifiant unique n'est partagé entre le REQ et les registres/licences des autres provinces — le rapprochement doit se faire par nom d'entreprise, une heuristique imparfaite avec un vrai risque de faux positifs (deux entreprises différentes, nom similaire) et de faux négatifs (même entreprise, raison sociale différente d'une province à l'autre). Ne jamais présenter ce rapprochement comme garanti.

Notées pour une feuille de route plus lointaine : rapports exportables automatisés en marque blanche, authentification SSO/SAML complète.

## 6. Score de confiance, score de pertinence, et sensibilité

**Deux axes indépendants, pas un seul score fusionné :**
- **Score de confiance** (ci-dessous, inchangé) : le signal est-il réel et fort, indépendamment de qui le reçoit.
- **Score de pertinence** (nouveau, voir sous-section dédiée) : ce signal correspond-il au profil précis de CET utilisateur — c'est le moteur de croisement par sphère de besoin qui distingue FALKYE d'une simple consultation des sources publiques une à une.

Ces deux axes se combinent en **matrice**, pas en moyenne, pour la décision finale de notification : un signal peu pertinent n'est jamais montré même si sa confiance est élevée; un signal moyennement pertinent mais très fiable peut valoir la peine. Le seuil de sensibilité de l'utilisateur (section suivante) s'applique sur cette combinaison, pas sur un seul des deux axes isolément.

**Principe d'unification, essentiel pour l'ergonomie web puis mobile :** il n'existe qu'**un seul indice de confiance par notification** — pas de jauges parallèles (urgence, gradation par signal, etc.). Tout facteur pertinent, y compris la notion d'urgence, est plié dans ce score unique plutôt que présenté comme une mesure séparée. L'utilisateur ne voit et n'interprète qu'une seule chose par notification : Faible/Moyen/Élevé.

Ce score unifié est calculé à partir de trois éléments qui s'additionnent ou se soustraient sur la même échelle :
1. **Critères propres au signal** (table ci-dessous)
2. **Bonus de corroboration multi-signaux** (voir plus bas) — plusieurs signaux indépendants sur la même entreprise renforcent le score
3. **Facteur de fraîcheur** : le score diminue avec le temps écoulé depuis la détection du signal. Ce facteur remplace ce qui aurait pu être une "jauge d'urgence" séparée — un signal ancien devient moins pertinent avec le temps, sans qu'on ait besoin d'un deuxième indicateur pour l'exprimer.

Le seuil global de sensibilité de l'utilisateur (Faible/Moyen/Élevé) filtre les notifications selon ce score unique. Pas de ML requis pour la v1.

**Deux curseurs de sensibilité indépendants** : puisque confiance et pertinence sont deux axes distincts, l'utilisateur doit pouvoir régler un seuil pour chacun séparément (ex. "montre-moi seulement AA et AAA, peu importe la confiance" ou l'inverse). Un seul curseur combiné forcerait un compromis que l'utilisateur n'a pas nécessairement demandé.

### Vérifications de base obligatoires — avant toute présentation d'un prospect

Puisque les sources ne se vérifient jamais entre elles, c'est à notre solution de le faire. **Aucun prospect ne doit être présenté à l'utilisateur — que ce soit en notification individuelle, en résumé périodique, ou en résultat de recherche ponctuelle — sans qu'un ensemble minimal de vérifications ait été effectué.** Ce n'est pas optionnel et ça s'applique aux deux modes d'usage (section 5), pas seulement à la veille continue.

Les vérifications de base :
1. **Statut légal au REQ** (via le NEQ, section 9) : si `radiée`, exclusion immédiate, peu importe le score de confiance calculé par ailleurs. C'est la vérification la plus fiable et la plus à jour de l'existence légale d'une entreprise.
2. **Signe d'activité via le site web** (enrichissement contextuel, section 10) : si un site est trouvé mais indique clairement une fermeture, une vente, ou une inactivité (ex. page "fermé définitivement", domaine expiré, contenu manifestement obsolète), exclusion. L'absence de site web n'est pas en soi un motif d'exclusion — plusieurs PME légitimes n'en ont pas — mais un site actif qui contredit le signal détecté l'est.
3. **Cohérence du nom résolu au NEQ** : si le nom d'entreprise détecté par une source ne peut pas être résolu avec confiance à un NEQ unique au REQ (ambiguïté entre plusieurs entreprises similaires), le prospect doit être marqué comme non vérifié plutôt que présenté avec un NEQ potentiellement erroné.

Un prospect qui échoue à l'une de ces vérifications est **exclu silencieusement**, pas présenté avec un avertissement — la promesse du produit repose sur la fiabilité de ce qui est montré, pas sur la quantité.

### Critères de confiance par signal

| Signal | Critères de confiance |
|---|---|
| Classements de croissance | Rang dans le palmarès (plus haut = plus fort), taux de croissance rapporté, fraîcheur de la publication (année en cours vs passée) |
| Financement — RDPRM | Valeur du bien mis en garantie relative à la taille estimée de l'entreprise, nature du bien (équipement/inventaire de production = plus fort qu'un véhicule isolé), récence de l'inscription |
| Financement — subventions/Investissement Québec | Montant relatif à la taille de l'entreprise, nature du programme (expansion/croissance explicite vs formation/maintien), confirmation directe (nom + montant précis) vs mention indirecte |
| Recrutement — Guichet-Emplois (volume) | Nombre de postes ouverts simultanément, vitesse de publication (plusieurs postes en peu de temps), récurrence sur plusieurs mois |
| Recrutement — Guichet-Emplois (titre qualitatif) | Présence de mots-clés de transformation/implantation/amélioration dans le titre du poste, correspondance avec les mots-clés du profil utilisateur — signal fort même avec un seul poste, indépendant du critère de volume |
| Recrutement — EIMT positive | Nombre de postes approuvés, récurrence sur plusieurs trimestres — signal déjà fort par nature puisque confirmé officiellement par le gouvernement |
| Registre corporatif — REQ | Type de changement (nouvel établissement secondaire = fort; changement d'adresse du siège social = moyen; mise à jour administrative de routine = à exclure, voir note ci-dessous) |
| Registre corporatif — permis de construction | Valeur du permis, nature des travaux (agrandissement/nouvelle construction = fort; rénovation mineure = faible) |
| Appels d'offres — SEAO | Valeur du contrat relative à la taille estimée de l'entreprise, récurrence de contrats décrochés sur une période courte |

### Score de pertinence — A / AA / AAA

Distinct du score de confiance ci-dessus. Répond à "ce signal correspond-il au profil précis de cet utilisateur", pas "ce signal est-il fiable". Trois paliers, en registre positif avec gradation :

| Code | Nom | Critère |
|---|---|---|
| **A — Repéré** | Correspondance à une sphère de besoin secondaire ou seulement probable (ex. un signal touche plusieurs sphères à la fois via la table de correspondance signal → sphères de la section 7, et la sphère de l'utilisateur n'est qu'une des sphères probables, pas la principale) | Prospect montré, attente la plus modeste |
| **AA — Aligné** | Correspondance directe à la sphère de besoin principale déclarée par l'utilisateur, sans mot-clé précis de son profil — correspondance générique mais directe | Prospect montré avec confiance de correspondance |
| **AAA — Sur mesure** | Correspondance à un mot-clé précis du profil utilisateur (ex. le signal qualitatif basé sur le titre du poste, section 7, Signal 3) — la correspondance la plus fine possible, au-delà de la sphère générique | Prospect prioritaire, correspondance la plus étroite possible |

**Implication pour le moteur** : le calcul de pertinence dépend directement de la table de correspondance signal → sphères (section 7) et des mots-clés optionnels du profil utilisateur (section 4) — ce ne sont pas de nouvelles données à collecter, c'est une nouvelle couche de calcul par-dessus ce qui existe déjà.

**Filtrage par champ, contextuel au profil — nouvelle couche, appliquée après la capture, jamais à l'ingestion**

Le matching sphère ↔ signal se fait aujourd'hui au niveau du `signal_type_id` en entier (confirmé dans le code réel). Nouvelle couche à ajouter par-dessus : au sein d'un même signal, certains champs sont pertinents pour un profil donné et du bruit pour un autre — ex. le champ secteur/NAICS du REQ compte pour un courtier en énergie (secteurs énergivores) mais est du bruit pour un fournisseur de mobilier de bureau; le champ type d'établissement (siège vs succursale) compte pour une compagnie de déménagement mais pas pour un courtier en énergie.

**Distinction critique avec le filtrage déjà existant à l'ingestion (REQ ne retient que certains types de mise à jour, RDPRM exclut par `nature_bien`) :** ce filtrage-là répond à une question universelle, la même pour tout le monde ("cette donnée est-elle du bruit administratif, point final?"), et reste tel quel à l'ingestion. Le filtrage par champ proposé ici répond à une question dont la réponse dépend de qui regarde — donc elle ne peut pas être tranchée une fois pour toutes à la capture. **Principe retenu : capter largement une seule fois à l'ingestion (comme c'est déjà fait), appliquer la grille de pertinence par champ au moment du calcul de pertinence, pour le profil précis qui reçoit la notification — jamais à l'ingestion.**

Deux raisons qui tranchent en faveur du "après" :
1. **Extensibilité** — si un champ était jeté à l'ingestion parce que jugé non pertinent au moment de la capture, il serait irrécupérable pour toute sphère de besoin identifiée plus tard. Exactement le risque qu'on vient d'éviter de justesse avec la sphère "Financement / accès au capital", ajoutée après coup.
2. **Un seul entrepôt, plusieurs lentilles** — un même événement capté une seule fois peut être vu différemment par deux utilisateurs de sphères différentes, sans re-capter quoi que ce soit.

À construire : une table de correspondance sphère → champs pertinents par source (ex. sphère "énergie" → champ NAICS du REQ pertinent, champ type d'établissement non pertinent), suivant le même principe d'extensibilité que le reste du registre — pas codée en dur, doit pouvoir s'étendre à mesure que de nouvelles sphères ou sources s'ajoutent.

**Principe du signal par absence** : un signal ne se limite pas à ce qui est détecté — l'**absence** d'un signal normalement attendu à un stade plus avancé peut elle-même constituer un indicateur de pertinence positif. Découvert avec le persona investisseurs providentiels (section personas) : une entreprise montrant croissance d'effectifs et nouvel établissement, mais **sans** financement gouvernemental ni classement de croissance encore visible, signale une traction précoce, avant qu'elle soit publique. Ce principe est généralisable à d'autres sphères au-delà du financement — à garder en tête lors de la conception du moteur de pertinence plutôt que de le coder comme un cas spécial au VC.

**Trajectoire, en complément du score statique** : le dossier cumulatif par entreprise (section 5) permet de détecter une **accélération** — plusieurs signaux de force croissante en peu de temps plutôt qu'un signal isolé ou des signaux espacés sur une longue période. Une entreprise avec 3 signaux en 2 mois est un meilleur prospect qu'une entreprise avec 3 signaux étalés sur 2 ans, même à confiance égale par signal — ce facteur de vélocité doit être considéré comme un contributeur additionnel au score de pertinence, pas seulement au score de confiance.



Lorsqu'une même entreprise est détectée par **plusieurs signaux distincts**, le système doit **consolider ces détections en une seule notification**, plutôt que d'envoyer une notification par signal. Cette notification consolidée :
- présente chaque signal ayant contribué à la détection, avec sa source et sa justification propre,
- reçoit un **bonus de confiance intégré au même score unifié** — la corroboration entre sources indépendantes est en soi une indication de fiabilité plus forte, pas un score séparé,
- respecte tout de même le seuil de sensibilité global de l'utilisateur, appliqué au score consolidé plutôt qu'à chaque signal pris isolément,
- s'applique aussi bien à des signaux détectés dans une période rapprochée qu'à des signaux étalés sur plusieurs mois — voir le dossier cumulatif par entreprise (section 5).

## 7. Signaux à détecter et sources

**Principe transversal (s'applique à toutes les sources, actuelles et futures) :** pour chaque source, définir à l'avance les champs précis à extraire et conserver, afin que l'information pertinente ne soit jamais noyée dans du bruit administratif ou des champs non pertinents.

**Principe de complétude, essentiel au résultat recherché :** l'objectif final est de trouver des prospects avec un besoin potentiel, ce qui exige de pouvoir (1) les localiser géographiquement pour les croiser avec le profil de l'utilisateur (ville/région/rayon), et (2) déterminer leur secteur d'activité pour les croiser avec la sphère de besoin. Plusieurs sources ne fournissent ni l'adresse complète ni le secteur d'activité directement (ex. Investissement Québec, les subventions fédérales, le SEAO ne donnent souvent que le nom et un montant). **Chaque source doit donc capturer ces champs directement quand ils sont disponibles, et sinon, le système doit les résoudre via le REQ** (en utilisant le NEQ comme pivot, section 9) après avoir identifié l'entreprise par son nom. Sans cette étape, une bonne partie des entreprises détectées ne pourraient être ni localisées ni classées par sphère de besoin, ce qui viderait la notification de sa valeur.

### Extensibilité des types de signaux

Les cinq signaux documentés dans ce chapitre (classements, financement, recrutement, registre corporatif, appels d'offres) ne sont **pas une liste figée** — ce sont les catégories identifiées à ce jour, pas une limite structurelle du système. Le Signal 4 (registre corporatif) a d'ailleurs été ajouté après les trois premiers, ce qui confirme que cette taxonomie va continuer d'évoluer. Le système doit donc traiter le **type de signal** comme un registre extensible, avec le même principe que le registre de sources (section 9) : un nouveau type de signal (ex. changements de dirigeants, si une source s'ouvre un jour; données de propriété intellectuelle; etc.) doit pouvoir être ajouté avec son propre gabarit — nom, sources associées, critères de confiance, sphères de besoin probables, **et une icône représentative pour l'identité visuelle future de l'interface** — sans renuméroter ou restructurer les signaux existants.

**Principe de calibration, non négociable :** aucune source n'est activée sans une règle concrète et vérifiable qui distingue un vrai signal de croissance du bruit administratif ou non pertinent — comme le filtrage déjà exigé pour le RDPRM (garantie de routine vs expansion), le REQ (mise à jour administrative vs nouvel établissement), et les licences d'affaires municipales (démarrage/renouvellement vs nouvel établissement d'une entreprise existante, vérifié par croisement). **Une source qui ne peut pas être calibrée de cette façon reste en réserve, non activée, plutôt que d'être ajoutée "quand même" parce qu'elle est gratuite.** Le nombre de sources actives n'est jamais l'objectif en soi — la précision des résultats l'est.

### Table de correspondance signal → sphères de besoin probables

Chaque signal détecté doit être associé à une ou plusieurs sphères de besoin probables (voir liste complète en section 4), pour que la notification puisse indiquer non seulement la raison du repérage mais aussi le type de besoin que l'entreprise est susceptible de développer. Cette table est un point de départ à affiner avec l'usage, pas une liste figée.

| Signal | Sphères de besoin probables |
|---|---|
| Classements de croissance (Signal 1) | Gestion de projet, planification stratégique/conseil en gestion, technologie/systèmes, RH/recrutement (la croissance rapide touche généralement plusieurs sphères à la fois) |
| Financement et expansion — RDPRM (Signal 2) | Gestion d'inventaire et d'actifs, logistique/transport, production/opérations manufacturières (le bien mis en garantie indique souvent la sphère concernée) |
| Financement et expansion — subventions/Investissement Québec (Signal 2) | Comptabilité/finance, juridique/conformité, technologie/systèmes (selon le programme ciblé — ex. PARI → technologie, CanExport → marketing/vente et juridique) |
| Recrutement massif — Guichet-Emplois/EIMT (Signal 3) | RH/recrutement/dotation, et la sphère associée à la profession recrutée (ex. postes en logistique → gestion d'inventaire/logistique; postes en TI → technologie). **Le signal qualitatif basé sur le titre du poste (voir Signal 3) offre une correspondance directe et souvent plus précise que ce mapping générique, via les mots-clés du profil utilisateur.** |
| Registre corporatif — REQ, nouvel établissement/changement d'adresse (Signal 4) | Immobilier/gestion d'espaces, logistique/transport, sécurité (physique), technologie/systèmes (déménagement implique souvent plusieurs besoins simultanés) |
| Registre corporatif — permis de construction (Signal 4) | Construction/rénovation, immobilier/gestion d'espaces, santé et sécurité au travail |
| Appels d'offres publics — SEAO (Signal 5) | Gestion de projet, et la sphère directement liée à la nature du contrat décroché |

### Signal 1 — Classements de croissance publiés
- **Inclus dans le prototype 1 (Québec/Canada) :** Deloitte Technology Fast 50 (Canada/Québec), Growth 500 (anciennement Croissance 500/PROFIT, Canadian Business), Globe and Mail Report on Business Top Growing Companies
- **Hors scope v1, réservé à l'extension géographique future :** Inc. 5000 (US) et tout palmarès équivalent d'une autre région, ajoutés au registre avec statut `à développer` dès qu'une nouvelle zone géographique est activée
- **Accès :** aucune API — pages web publiques standards, scraping léger nécessaire, sans restriction apparente (information publique destinée à large diffusion)
- **Champs pertinents à extraire :** nom d'entreprise, secteur, taux de croissance, rang, année de publication, région/ville si disponible, **site web (si mentionné directement par la source — évite l'étape de recherche en section 10)**, nombre d'employés (si mentionné)

### Signal 2 — Financement et expansion
- **RDPRM (registre des droits personnels et réels mobiliers, Québec)** — gratuit, public. Capte les inscriptions de garanties prises par des institutions financières sur des biens d'entreprise (équipement, inventaire, véhicules) lors d'un financement. Signal précoce, indirect mais public, de financement d'expansion.
  - **Activation possible dès maintenant via import manuel** (voir section 9) : plutôt que d'attendre une décision budgétaire pour une automatisation complète, Alexandre peut effectuer lui-même une recherche RDPRM ponctuelle (11$/nom d'entreprise) et l'importer dans le logiciel — le résultat entre alors dans le même pipeline que les sources automatisées. **Lien direct vers la page de recherche :** `https://www.rdprm.gouv.qc.ca/Consultation/` (consultation assistée par nom — la recherche doit utiliser le nom légal exact enregistré au Registre des entreprises du Québec).
  - **Champs pertinents :** uniquement les garanties sur biens d'entreprise à valeur significative (exclure garanties sur biens personnels), nom de l'entreprise débitrice, **adresse de l'entreprise débitrice (à défaut, résolue via REQ)**, nature du bien, **valeur/montant de la garantie**, date d'inscription, institution créancière
- **Investissement Québec** — liste de divulgation publique gratuite (nom d'entreprise + montant de financement), inclut des PME
  - **Champs pertinents :** nom d'entreprise, montant, date, programme/type de financement, **adresse/région (résolue via REQ si non fournie directement)**, **secteur d'activité (résolu via REQ si non fourni)**
  - **Découverte technique (accès réel vérifié) :** la liste est publiée en **PDF**, pas en CSV/API structuré — hébergée directement sur `www.investquebec.com` (ex. `investquebec.com/sites/default/files/.../interventions-financieres-2025.pdf`), mise à jour annuellement. Aucune redirection externe à prévoir pour l'accès réseau, mais l'extraction demande un traitement PDF plutôt qu'un simple parsing de fichier structuré.
- **BDC (Banque de développement du Canada)** — **vérifié : source réellement bloquée**, pas juste en réserve. La BDC est assujettie à la Loi sur l'accès à l'information et à la Loi sur la protection des renseignements personnels, exactement comme une banque privée, et ne divulgue pas ses prêts individuels.
- **Crunchbase** — payant (49-99$ US/mois), couvre les levées de fonds privées/institutionnelles — décision budgétaire à prendre, pas un choix de priorisation
- **CDPQ** — écarté comme source principale (cible des entreprises trop grandes), gardé en note comme signal secondaire possible (effet de ruissellement vers sous-traitants/fournisseurs d'une grande entreprise financée)
- **PME MTL, Futurpreneur, EVOL, Fonds Mosaïque** — aucune divulgation structurée des bénéficiaires trouvée à ce jour (contrairement à Investissement Québec) ; statut `à développer`, à réévaluer si une liste publique équivalente existe
- Note : une demande de prêt bancaire privé reste et restera inaccessible (secret bancaire) — le RDPRM est le meilleur proxy public disponible
- **Subventions et contributions gouvernementales — divulgation proactive fédérale** (Portail du gouvernement ouvert, open.canada.ca) — gratuit, public, couvre **tous les ministères fédéraux** : chaque subvention ou contribution versée à une entreprise est divulguée avec le nom du bénéficiaire, le montant, le programme et le ministère. Source large et gratuite, potentiellement une des plus riches pour ce signal.
  - **Champs pertinents :** nom du bénéficiaire, montant, ministère/programme, date, description sommaire du projet financé, **localisation du bénéficiaire (ville/province si fournie par le jeu de données, sinon résolue via REQ pour les entreprises québécoises)**
  - **Découverte technique (accès réseau, en prévision de la Phase 2) :** le fichier CSV est référencé sur `open.canada.ca`, mais comme le Guichet-Emplois utilise la même infrastructure et redirige vers `opencanada.blob.core.windows.net` (stockage Azure) au moment du téléchargement réel, il faut s'attendre à la même redirection ici et pour l'EIMT positive. Puisque ce domaine sera déjà ajouté à la liste réseau Custom depuis la Phase 1 (voir section 9), aucune interruption supplémentaire n'est attendue en Phase 2.
- **Programme d'aide à la recherche industrielle (PARI-CNRC)** — Conseil national de recherches Canada, finance jusqu'à 50 % des frais de développement technologique des PME
- **CanExport PME** — Affaires mondiales Canada, aide au développement de marchés d'exportation (20 000$ à 100 000$)
- **Agences régionales de développement économique** (au-delà de DEC pour le Québec) : FedDev Ontario, FedNor (Nord de l'Ontario), APECA (Canada atlantique), PrairiesCan, PacifiCan — pertinentes pour l'extension géographique future hors Québec
- **Futurpreneur Canada** — prêts et mentorat pour jeunes entrepreneurs (18-39 ans), jusqu'à 60 000$
- **EVOL (anciennement Femmessor)** et **Fonds Mosaïque (Filaction)** — financement ciblé pour entreprises dirigées par des groupes sous-représentés
- **Programme d'actions concertées pour le maintien en emploi (PACME)** — subventions de formation, signal indirect de croissance/adaptation de la main-d'œuvre

### Signal 3 — Recrutement massif

**Deux mécanismes distincts, pas un seul :** en plus du volume (plusieurs postes ouverts simultanément), un **signal qualitatif basé sur le titre du poste** doit être détecté indépendamment du volume. Un seul poste avec un titre orienté transformation ou implantation (ex. "Chef de projet — implantation ERP/WMS", "Directeur de la transformation", "Gestionnaire, amélioration continue", "Pilote d'implantation [système]", "Responsable de la transition numérique") est souvent un signal plus fort et plus directement actionnable qu'un lot de postes de production — il annonce une intention de changement précise, pas seulement un besoin de main-d'œuvre. **Ce signal qualitatif peut à lui seul justifier une notification, même avec un seul poste détecté**, contrairement au signal de volume qui a besoin de plusieurs postes pour être significatif.

**Lien avec les mots-clés du profil utilisateur (section 4) :** les mots-clés/tags optionnels que l'utilisateur associe à son service précis (ex. Alexandre pourrait ajouter "implantation ERP", "gestion d'inventaire", "amélioration des opérations") doivent être utilisés pour analyser le titre des postes détectés — un titre de poste qui contient ou se rapproche de ces mots-clés génère une correspondance directe et précise, bien au-delà de ce que la table de correspondance signal → sphère de besoin (générique) peut offrir.

- **Guichet-Emplois (Job Bank), gouvernement du Canada** — **excellente découverte** : les offres publiées sur le Guichet-Emplois national sont disponibles en **données ouvertes gratuites**, mises à jour mensuellement, en formats CSV/TSV/JSON/XML avec API de données, via le Portail du gouvernement ouvert (open.canada.ca). Couverture pancanadienne, structurée, gratuite — nettement plus simple que LinkedIn/Indeed pour ce signal.
  - **Limite critique confirmée (vraies données + documentation officielle) :** le fichier en vrac **ne contient pas le nom de l'employeur** — confirmé à la fois dans les données réelles et dans la documentation officielle du jeu de données. Sans nom d'employeur, impossible de résoudre une entreprise précise, donc **impossible de produire une notification par entreprise** — cette source échoue au principe de calibration (elle ne peut identifier une entreprise, pas seulement mal filtrer le bruit). **Statut repassé à `à développer`** pour la Phase 1 : le signal recrutement pour la Phase 1 est couvert par l'EIMT positive (voir ci-dessous), qui donne le nom de l'employeur. Le Guichet-Emplois reste au registre pour une réactivation future (ex. couplage avec un agrégateur tiers qui identifie l'employeur, ou si le jeu de données est enrichi), mais n'est plus une source active de la Phase 1.
  - **Champs pertinents (si réactivée) :** nom de l'employeur, **titre du poste (texte intégral, pour l'analyse qualitative des mots-clés)**, profession/CNP (Classification nationale des professions), nombre de postes, salaire offert, ville/région, date de publication
  - **Limite à valider :** délai de mise à jour mensuel (moins réactif qu'un flux en temps réel), et ne couvre que les offres publiées directement sur le Guichet-Emplois ou partagées par ses partenaires (Workopolis, Monster, etc.) — pas nécessairement 100 % du marché
- **Québec emploi (anciennement Placement en ligne, remplacé depuis mai 2021)** — correction importante : "Placement en ligne" n'existe plus, le site actuel du gouvernement du Québec s'appelle **Québec emploi**.
  - **Aucune API publique documentée** trouvée pour consulter les offres à des fins de tiers (contrairement au Guichet-Emplois fédéral). Il existe un sous-domaine `partenaires.api.quebecemploi.gouv.qc.ca`, ce qui indique qu'une API de partenaires existe bel et bien, mais elle semble réservée à des partenaires authentifiés (agences de placement, établissements scolaires, prestataires de services d'emploi) pour publier/gérer des offres, pas pour de la consultation en lecture par un tiers comme notre outil. **À valider directement avec l'équipe de Québec emploi** (Centre d'assistance au placement, 1 866 640-3059) si un accès en lecture est possible pour un usage comme le nôtre.
  - **Bonne nouvelle qui réduit l'urgence de cet accès** : le Québec et le gouvernement fédéral ont une entente établie (Entente Canada-Québec relative au marché du travail, avec un volet spécifique de partage des services informationnels entre l'ancien Placement en ligne et le Guichet-Emplois, en place depuis au moins 2015). Une bonne partie des offres publiées via les systèmes québécois se retrouvent donc déjà, en pratique, dans les données ouvertes du Guichet-Emplois — ce qui atténue en partie l'angle mort plutôt que de le combler à 100 %.
  - **Statut recommandé pour le registre :** `à développer` — avec le Guichet-Emplois comme source principale active pour ce signal en v1, et Québec emploi ajouté au registre en attente d'une confirmation d'accès (contact direct) ou, en dernier recours, d'un scraping léger du site public si l'entreprise juge la couverture du Guichet-Emplois insuffisante après un premier test
- **LinkedIn** : aucune API publique de recherche d'emploi, réservée aux partenaires approuvés — tout "API LinkedIn jobs" trouvée en ligne est un scraper tiers
- **Indeed** : Publisher API fermée depuis 2025/2026, plus d'accès développeur pour chercher des offres
- **Accès pour LinkedIn/Indeed :** nécessite un agrégateur tiers payant (ex. TheirStack, Apify) ou du scraping plus fragile/risqué — à garder en dernier recours maintenant que le Guichet-Emplois offre une alternative gratuite et structurée
- **Liste des employeurs avec EIMT positive (Étude d'impact sur le marché du travail), Emploi et Développement social Canada** — **excellente découverte, signal de très haute qualité** : publiée trimestriellement en données ouvertes gratuites (CSV) sur open.canada.ca. Une EIMT positive signifie que Service Canada a confirmé qu'aucun travailleur canadien ou résident permanent n'était disponible pour le poste — c'est donc un signal de pénurie de main-d'œuvre confirmé officiellement, souvent plus fort qu'un simple affichage de poste, et un signe clair qu'une entreprise est en expansion active.
  - **Champs pertinents :** nom de l'employeur, lieu d'affaires, profession (CNP), nombre de postes, volet du programme, trimestre
  - **Limite à noter :** exclut les employeurs utilisant un nom personnel (ex. gardiennage), et ne couvre que les employeurs recourant à des travailleurs étrangers temporaires — un sous-ensemble ciblé, pas l'ensemble du marché
  - **Découverte technique (accès réseau) :** même infrastructure open.canada.ca que le Guichet-Emplois — probable redirection vers `opencanada.blob.core.windows.net` au téléchargement réel (voir note sous les subventions fédérales ci-dessus)

### Signal 4 — Registre et changements corporatifs
- **Registre des entreprises du Québec (REQ)** — **excellente découverte** : données ouvertes gratuites, mises à jour deux fois par mois, via Données Québec. Couvre toutes les entreprises immatriculées ou constituées au Québec (NEQ, nom, secteur d'activité, adresse, statut). Utile de deux façons :
  1. **Base de vérification/enrichissement** pour toutes les entreprises repérées par les autres signaux (confirmer existence légale, secteur, adresse)
  2. **Signal d'expansion en soi** : une nouvelle immatriculation d'établissement secondaire ou un changement d'adresse pour une entreprise déjà active peut indiquer une expansion physique
  - **Découverte technique (accès réel vérifié) :** le fichier en vrac est hébergé sur `registreentreprises.gouv.qc.ca` (décision de Données Québec, pas un choix d'implémentation), à l'URL `RQAnonymeGR/GR/GR03/GR03A2_22A_PIU_RecupDonnPub_PC/FichierDonneesOuvertes.aspx`, découverte dynamiquement via les métadonnées officielles. Ce domaine **bloque les plages d'adresses IP infonuagiques** (confirmé : blocage Cloudflare identique dès le premier appel, IP de sortie différente à chaque tentative, aucun lien avec le volume de requêtes) — un environnement de développement cloud comme celui de Claude Code ne peut donc pas y accéder directement, peu importe la méthode. **Statut : `import_manuel`** — Alexandre télécharge le fichier ZIP lui-même depuis son navigateur personnel (aucun blocage, IP résidentielle) et l'importe dans le logiciel via le mécanisme générique d'import manuel (section 9). Comme le fichier n'est mis à jour que deux fois par mois, c'est une tâche récurrente légère plutôt qu'un irritant à chaque recherche (contrairement au RDPRM).
  - **Champs pertinents :** NEQ, nom d'entreprise, secteur d'activité (CAE/CTI), adresse(s), statut (immatriculée/radiée), date de la dernière mise à jour
  - **Limite à noter :** les actionnaires et administrateurs sont anonymisés dans les données ouvertes (contrairement à la consultation individuelle payante par NEQ)
  - **Filtrage requis, même logique que le RDPRM :** la grande majorité des mises à jour au REQ sont administratives et routinières (déclaration annuelle obligatoire, correction mineure, renouvellement) et n'indiquent aucune croissance. Seuls certains types de changements doivent être retenus comme signal — notamment l'ajout d'un nouvel établissement secondaire ou un changement d'adresse du siège social — et le filtre doit explicitement exclure les mises à jour de nature purement administrative pour éviter un signal bruyant plutôt que précis
- **Corporations Canada (ISED)** — **nouvelle découverte, équivalent fédéral du REQ, mais pancanadien** : couvre toutes les entreprises incorporées sous une loi fédérale (partout au Canada, anglais et français), publié en **téléchargement gratuit en vrac, mis à jour quotidiennement**, avec en plus une **vraie API en temps réel** (plus complet que le REQ à cet égard). Répond directement au besoin de couverture en anglais Canada.
  - **Champs pertinents :** numéro de corporation fédérale, nom, statut, adresse du bureau enregistré, date d'incorporation, loi constitutive
  - **Limite à noter :** ne couvre que les entreprises incorporées fédéralement — la majorité des PME sont incorporées provincialement, donc cette source complète le REQ (Québec) sans remplacer l'équivalent dans les autres provinces (accès inégal — gratuit en Ontario/Nouvelle-Écosse pour la recherche de base, payant en Colombie-Britannique, fermé en Alberta — à documenter au cas par cas si activé plus tard)
- **Licences d'affaires municipales** (ex. Vancouver, Toronto — données ouvertes confirmées, gratuites, mises à jour quotidiennement pour Vancouver) — nom d'entreprise, adresse, type d'entreprise, date d'émission.
  - **Condition de pertinence, non négociable :** une nouvelle licence d'affaires ne devient un signal utile qu'après **vérification croisée avec Corporations Canada ou le registre provincial concerné**, pour confirmer qu'il s'agit d'une entreprise **déjà existante qui ouvre un nouvel établissement** — pas un tout nouveau démarrage (hors cible du produit) ni un simple renouvellement annuel (bruit administratif). Sans cette vérification croisée, la source produit surtout du bruit. Cette vérification suit exactement le même principe que la résolution NEQ/REQ déjà bâtie dans l'architecture (section 9) — pas une nouvelle mécanique, une application de celle qui existe déjà.
  - **Champs pertinents :** nom d'entreprise, adresse, type d'entreprise, date d'émission de la licence
- **Registres municipaux de permis de construction** (Montréal, Québec, Laval, etc., disponibles en données ouvertes par ville) — signal potentiel d'expansion physique (nouveaux locaux, agrandissement). Fragmenté par municipalité, à activer progressivement selon la priorité géographique
  - **Champs pertinents :** nom du demandeur/propriétaire, adresse des travaux, nature des travaux (agrandissement/nouvelle construction/rénovation), valeur du permis, date d'émission

### Signal 5 — Appels d'offres publics décrochés
- **SEAO (Système électronique d'appel d'offres du Québec)** — la source la plus simple et gratuite : données ouvertes, formats JSON/XML, mise à jour hebdomadaire/mensuelle, aucune autorisation requise (portail Données Québec). Couvre contrats gouvernementaux, réseaux éducation/santé, municipalités.
- **Divulgation proactive des contrats fédéraux** (Portail du gouvernement ouvert, open.canada.ca) — **nouvelle découverte, équivalent pancanadien du SEAO** : contrats de plus de 10 000$ accordés par les ministères fédéraux, publiés en CSV gratuit, couverture partout au Canada. Répond directement au besoin de couverture en anglais Canada pour ce signal.
  - **Champs pertinents :** entreprise adjudicataire, valeur du contrat, ministère, date d'attribution, description sommaire
- Note : le but n'est pas d'éviter les appels d'offres comme canal, mais aussi de couvrir les entreprises en croissance qui n'y apparaissent jamais (surtout les PME) — le SEAO et les contrats fédéraux sont des sources additionnelles, pas la source principale.
- **Champs pertinents (SEAO) :** entreprise adjudicataire, **adresse de l'entreprise adjudicataire (résolue via REQ si non fournie directement)**, valeur du contrat, secteur/nature du contrat, date d'attribution, donneur d'ordre

## 8. Priorisation pour le prototype v1

**Principe directeur : toute source gratuite et de bonne qualité fait partie du prototype 1, sans exception.** Ce n'est pas une variable d'ajustement optionnelle — c'est au cœur de la promesse du produit. Une source n'est écartée du lancement que pour deux raisons précises, jamais par choix de priorisation :
1. **Elle est légalement inaccessible** (confidentialité bancaire/institutionnelle) — aucune quantité de développement ne peut la débloquer.
2. **Elle exige un abonnement payant** — dans ce cas, c'est une décision budgétaire qui te revient, pas un choix que je fais à ta place.

### Sources gratuites — toutes incluses dans le prototype 1

1. SEAO — gratuit, simple, structuré (Signal 5 : appels d'offres)
2. RDPRM — **actif via import manuel** (voir sections 7 et 9) : payant à l'unité (11$/nom, 4$/NIV), pas gratuit en vrac comme documenté à l'origine — activé sans engagement récurrent grâce au mécanisme d'import manuel plutôt que par une décision budgétaire d'automatisation complète (Signal 2 : financement)
3. Guichet-Emplois (Job Bank Canada) — **repassé à `à développer`** : le fichier en vrac ne contient pas le nom de l'employeur, confirmé dans les vraies données et la documentation officielle — impossible de produire une notification par entreprise sans réactivation future (ex. agrégateur tiers) (Signal 3 : recrutement)
4. **Liste des employeurs avec EIMT positive (EDSC)** — gratuit, trimestriel, signal de pénurie de main-d'œuvre confirmé officiellement, **donne le nom de l'employeur** — source active pour le signal recrutement en Phase 1 (Signal 3 : recrutement) — **nouvelle découverte, signal de très haute qualité**
5. **Subventions et contributions gouvernementales — divulgation proactive fédérale** — gratuit, couvre tous les ministères fédéraux (Signal 2 : financement). **Cette source unique absorbe DEC, PARI-CNRC, CanExport, FedDev Ontario, FedNor, APECA, PrairiesCan et PacifiCan** : ce sont tous des ministères/organismes fédéraux dont les subventions apparaissent dans cette même divulgation proactive. Il ne s'agit donc pas de sources séparées "en réserve" mais de filtres à configurer sur cette source dès la v1, sans développement additionnel.
6. Investissement Québec — gratuit, ciblé PME (Signal 2 : financement)
7. Classements de croissance (Deloitte Fast 50, Growth 500, Globe and Mail Top Growing Companies) — gratuit, scraping léger requis (Signal 1)
8. **Registre des entreprises du Québec (REQ)** — gratuit, mis à jour deux fois par mois, base de vérification/enrichissement et signal d'expansion via changements d'adresse/nouveaux établissements (Signal 4 : registre corporatif) — **nouvelle découverte**
9. Québec emploi — statut à confirmer directement avec leur équipe (voir section 7), à activer dès qu'un accès est clarifié
10. Registres municipaux de permis de construction (Montréal, Québec, Laval, etc.) — gratuit, fragmenté par ville, à activer progressivement (Signal 4)
11. **Corporations Canada (ISED)** — gratuit, bulk quotidien + API, équivalent fédéral pancanadien du REQ (Signal 4) — **nouvelle découverte, couverture Canada anglais**
12. **Divulgation proactive des contrats fédéraux** — gratuit, équivalent pancanadien du SEAO (Signal 5) — **nouvelle découverte, couverture Canada anglais**
13. **Licences d'affaires municipales** (Vancouver, Toronto) — gratuit, mais **activation conditionnelle à la vérification croisée avec Corporations Canada/registre provincial** (voir section 7) pour distinguer un nouvel établissement d'une entreprise existante d'un simple démarrage ou renouvellement (Signal 4)

### Sources réellement bloquées (non négociables, pas un choix de priorisation)

- **BDC (Banque de développement du Canada)** — vérifié : la BDC est assujettie à la Loi sur l'accès à l'information et à la Loi sur la protection des renseignements personnels, exactement comme une institution financière privée. Elle ne divulgue pas ses prêts individuels. Cette porte est fermée, pas repoussée.
- **Prêts bancaires privés** — même logique, secret bancaire, inaccessible par nature (voir section 7)
- **PME MTL, Futurpreneur, EVOL, Fonds Mosaïque** — organismes à but non lucratif ou paramunicipaux sans divulgation structurée de leurs bénéficiaires trouvée à ce jour. Gardés au registre avec statut `à développer`, à réévaluer si une liste publique existe (ex. rapports annuels) — mais rien d'équivalent à la liste d'Investissement Québec n'a été trouvé pour l'instant.

### Sources nécessitant une décision budgétaire de ta part

- **Crunchbase** — payant (49-99$ US/mois), couvre les levées de fonds privées/institutionnelles, angle mort réel du prototype 1 sans elle (voir l'analyse de couverture ci-dessous)
- **Agrégateur tiers pour LinkedIn/Indeed** (ex. TheirStack, Apify) — payant, comble une partie de l'angle mort du recrutement non couvert par le Guichet-Emplois

Je te laisse trancher sur ces deux-là selon le budget que tu veux allouer dès le départ — ce sont les deux seules sources du projet où l'obstacle est purement financier plutôt que technique ou légal.

### Séquencement de développement recommandé

Construire les 10 sources gratuites simultanément avant le premier envoi de notification utile représente une charge de démarrage importante. Recommandation pour Claude Code :

- **Phase 1 — chemin complet de bout en bout :** SEAO, REQ, et EIMT positive (recrutement, avec nom d'employeur) — RDPRM et Guichet-Emplois sont repassés à `à développer` en cours de construction réelle (RDPRM : payant à l'unité, pas gratuit en vrac comme documenté à l'origine ; Guichet-Emplois : le fichier en vrac ne contient pas le nom de l'employeur, rendant impossible une notification par entreprise). L'objectif de cette phase reste de valider l'ensemble du pipeline (détection → résolution NEQ/REQ → score de confiance → vérifications de base → enrichissement web → notification) de bout en bout, pas d'avoir une couverture complète.
- **Phase 2 — ajout progressif des sources restantes** (EIMT, subventions fédérales, Investissement Québec, classements de croissance, permis de construction, Québec emploi) une à une dans le registre déjà conçu pour ça, une fois la mécanique de la Phase 1 validée avec de vraies notifications.

**Note d'accès réseau pour la Phase 2 :** ne pas ajouter par anticipation les domaines des sources de Phase 2 à la liste réseau Custom — ajouter chaque domaine seulement quand la source correspondante est activée, comme ça a été fait pour `opencanada.blob.core.windows.net` en Phase 1. Ce domaine Azure couvre déjà probablement l'EIMT et les subventions fédérales (même infrastructure que le Guichet-Emplois) sans ajout supplémentaire ; Investissement Québec est un PDF sur `www.investquebec.com`, pas un fichier structuré (voir section 7).

Cette phase ne change rien à l'architecture ou à la portée du prototype 1 — c'est une recommandation d'ordre de construction, pas de contenu.

### Cette combinaison suffit-elle pour des résultats pertinents ?

Avec l'ajout de la divulgation proactive fédérale (qui couvre maintenant DEC, PARI, CanExport et les agences régionales gratuitement) et la confirmation que les palmarès sont bien dans la v1, la couverture gratuite du prototype 1 est maintenant complète pour tout ce qui est légalement accessible sans frais. Il reste deux types d'angles morts, et aucun des deux n'est dû à un manque de sources — ce sont des limites réelles, pas des choix :

- **Angle mort légal, non négociable :** les entreprises qui financent leur croissance uniquement par prêt bancaire privé ou BDC restent invisibles — ni l'un ni l'autre ne divulguent leurs prêts, par la loi. Le RDPRM reste le meilleur proxy public pour ce type de financement.
- **Angle mort budgétaire, à trancher par toi :** les entreprises qui financent leur croissance par capital de risque privé (sans passer par le RDPRM, une subvention publique ou un contrat public) resteront invisibles sans Crunchbase. De même, les entreprises qui recrutent uniquement via LinkedIn ou leur propre site échapperont au signal recrutement sans un agrégateur tiers payant.
- **Le RDPRM demandera un filtrage serré** pour distinguer une garantie liée à une réelle expansion d'une garantie de refinancement ou d'achat de routine — sinon le signal risque d'être bruyant plutôt que précis.

En résumé : la combinaison gratuite du prototype 1 est maintenant aussi large que possible sans dépense — rien n'y est omis par choix. Ce qui manque encore ne peut être comblé que par un budget (Crunchbase, agrégateur de recrutement) ou ne peut simplement pas l'être (secret bancaire). Je recommande de lancer avec la couverture gratuite complète, de mesurer la précision des premières notifications, puis de décider si l'angle mort budgétaire justifie la dépense une fois que la mécanique aura fait ses preuves.

## 9. Architecture des sources — modularité obligatoire

Le système doit être conçu comme un **registre de sources modulaire**, pas comme une série de scripts codés en dur pour chaque source. Chaque source, qu'elle soit déjà implémentée, en attente de développement, ou temporairement désactivée, doit exister comme une **entrée structurée dans le système**, avec le même gabarit :

| Attribut | Description |
|---|---|
| Identifiant / nom | Ex. "RDPRM", "SEAO", "Investissement Québec" |
| Signal associé | Financement, recrutement, classement, appel d'offres, etc. |
| Statut | `actif` / `inactif` / `à développer` / `en pause` |
| Méthode d'accès | API, données ouvertes, scraping, agrégateur tiers, **import manuel** (voir sous-section dédiée) |
| Champs pertinents | Liste des champs à extraire et conserver (voir section 7) |
| Coût | Gratuit / payant + montant si connu |
| Région couverte | Ex. Québec, Canada, international |

**Conséquences pour la conception technique :**

- **Toutes les sources identifiées à ce jour** (SEAO, RDPRM, Investissement Québec, BDC, PME MTL, DEC, Crunchbase, classements de croissance, LinkedIn, Indeed) doivent apparaître dans le registre dès la v1, **même celles non encore branchées** (ex. LinkedIn/Indeed, en attente d'un agrégateur tiers, ou Crunchbase, en attente d'un abonnement payant). Une source "à développer" ne retourne simplement aucun résultat tant qu'elle n'est pas activée — mais elle est visible et prête à être complétée.
- **Activer ou désactiver une source doit être une action simple** pour Alexandre (ex. changer un statut dans un fichier de configuration ou une interface), **sans toucher au code du moteur de scan central**. Le moteur doit boucler sur toutes les sources actives, peu importe combien il y en a.
- **Ajouter une nouvelle source plus tard** (ex. pour une nouvelle région, ou une source découverte après coup) doit suivre le même gabarit standard, sans modification du reste du système — seulement une nouvelle entrée dans le registre avec ses propres champs pertinents et sa méthode d'accès.
- Cette structure est ce qui permettra, plus tard, d'étendre le système à d'autres régions géographiques : on ajoute simplement les sources locales de la nouvelle région dans le même registre, sans retoucher la logique de croisement des signaux.

### Le NEQ comme identifiant pivot pour la déduplication

Le SEAO, le RDPRM, Investissement Québec et les subventions fédérales identifient tous les entreprises par leur nom en texte libre, qui varie facilement d'une source à l'autre (raisons sociales, abréviations, "inc." vs "Inc.", accents). Sans identifiant commun, deux mentions de la même entreprise dans des sources différentes risquent de ne jamais être reconnues comme la même entité — ce qui casserait la corroboration multi-signaux et le dossier cumulatif (section 5).

**Le NEQ (numéro d'entreprise du Québec, disponible via le REQ) doit servir d'identifiant pivot** : dès qu'une entreprise est détectée par nom dans n'importe quelle source, le système doit tenter de résoudre ce nom vers son NEQ via le REQ, puis utiliser ce NEQ comme clé pour tout regroupement, toute corroboration, et tout suivi dans le dossier cumulatif. C'est aussi via ce même NEQ que le statut `radiée` (filtre d'exclusion, section 6) est vérifié.

### Extensibilité du type de profil

De la même façon que le registre de sources est conçu pour absorber de nouvelles sources sans restructuration, la structure du profil utilisateur doit prévoir dès la v1 le champ `type de profil` (fournisseur/client/les deux, voir section 4), même si seule la mécanique fournisseur est implémentée pour le prototype 1. Le schéma de données ne doit pas coder en dur l'hypothèse qu'un utilisateur est nécessairement un fournisseur — pour permettre, plus tard, l'ajout de profils clients et d'une éventuelle mise en correspondance bidirectionnelle, sans reconstruire la structure existante.

### Import manuel de documents sources — activer une source payante sans engagement récurrent

Pour toute source où l'automatisation complète implique un coût récurrent qu'Alexandre ne veut pas engager d'emblée (ex. le RDPRM, payant à l'unité par recherche), **ou qu'un blocage d'accès empêche l'environnement infonuagique d'atteindre directement** (ex. le REQ, dont le domaine bloque les plages d'adresses IP infonuagiques — voir section 7), le système doit permettre un **mode d'import manuel**, sous deux formes :
- **Résultat unitaire** (ex. RDPRM) : Alexandre effectue lui-même une recherche/un achat ponctuel et importe le résultat obtenu.
- **Fichier complet** (ex. REQ) : Alexandre télécharge lui-même un fichier périodique depuis son propre navigateur (contournant un blocage d'accès plutôt qu'un coût) et l'importe dans le logiciel.

Les deux formes suivent le même principe générique — une donnée obtenue hors ligne par Alexandre entre dans le pipeline exactement comme une source automatisée, sans traitement spécial selon la source ou la forme.

Une fois importé, ce résultat entre **immédiatement dans la même boucle de traitement que toute source automatisée** — résolution NEQ/REQ, vérifications de base, score de confiance, corroboration avec d'autres signaux, et notification — sans distinction de traitement une fois à l'intérieur du pipeline.

**Principes de conception :**
- **Aucun engagement récurrent requis** : Alexandre paie uniquement les recherches qu'il choisit de faire, au moment où il les fait — pas un abonnement, pas un budget mensuel engagé d'avance. Ça répond directement au principe directeur #2 (décision budgétaire qui revient à Alexandre) sans le forcer à trancher pour ou contre une automatisation complète maintenant.
- **Lien direct vers la page de recherche de la source** : chaque entrée du registre configurée en import manuel doit inclure un lien direct vers la bonne page de consultation (ex. pour le RDPRM, directement vers la page de recherche par nom d'entreprise, pas seulement la page d'accueil du site). Quand Alexandre décide de faire une recherche pour une entreprise détectée par une autre source, le système lui présente ce lien directement plutôt que de le laisser chercher où aller.
- **Même rigueur de calibration que les sources automatisées** (principe #3) : un document RDPRM importé manuellement doit passer par le même filtre que documenté en section 7 (uniquement les garanties sur biens d'entreprise à valeur significative, pas les biens personnels) — l'import manuel ne contourne pas la calibration, il contourne seulement l'automatisation de la collecte.
- **Généralisable à toute source dans une situation similaire**, pas seulement le RDPRM — n'importe quelle source du registre avec un coût par recherche peut adopter ce même mode d'accès plutôt que de rester bloquée en statut `à développer` en attendant une décision budgétaire complète.
- **Le registre garde une trace de la méthode d'accès utilisée** (`import manuel` comme valeur possible du champ, section 9) pour chaque entrée traitée de cette façon, distincte d'une collecte automatisée — utile pour l'audit et pour savoir plus tard si l'automatisation complète en vaudrait la peine selon le volume réel utilisé manuellement.

### Polyvalence d'utilisation — ne pas coder en dur le cas d'usage d'Alexandre

Le produit doit rester utilisable par une multitude de types d'utilisateurs, pas seulement un fournisseur de service B2B ni un consultant en implantation de systèmes d'inventaire — voir la charte FALKYE, section 1 : chambres de commerce, conseillers en immigration, développement économique régional, institutions financières, et bien d'autres usages à découvrir. Ça implique :

- **Aucune logique ne doit assumer un secteur, un service, ou une sphère de besoin particulière.** La correspondance entre signaux, sphères, et mots-clés (sections 4 et 7) doit rester généralisée — un agent immobilier commercial, un courtier d'assurance, une agence de recrutement, ou même un chercheur d'emploi individuel doivent pouvoir configurer un profil et obtenir des résultats pertinents, sans qu'aucun code ne soit écrit en fonction du profil d'Alexandre spécifiquement.
- **Le dossier cumulatif par entreprise (identifié par NEQ, section 5/9) doit être conçu pour pouvoir éventuellement supporter une liste de surveillance par entreprise nommée**, en plus de la détection par profil/sphère — même si ce mode d'usage n'est pas construit pour le prototype 1. Ne pas fermer cette porte par une hypothèse de conception qui suppose que toute entreprise suivie provient nécessairement d'une correspondance de profil.
- **Hors scope explicite pour le prototype 1**, à ne pas construire maintenant : une logique inversée qui détecterait le déclin plutôt que la croissance (ex. repérer des entreprises en difficulté pour des courtiers en fusions-acquisitions), et une couche d'agrégation produisant des statistiques ou tendances régionales plutôt que des résultats par entreprise. Ces deux cas demanderaient une polarité de scoring et un type de résultat fondamentalement différents de ce que documente ce projet — ne pas complexifier l'architecture actuelle en anticipation de ces cas non confirmés.

## 9bis. Structure de plans tarifaires et portail de sources payantes

Décidée après la conception initiale de ce document — trois plans, avec un seul chantier de portail sous-jacent, pas deux.

| Plan | Sources | Portail |
|---|---|---|
| **Écho** | Sources gratuites uniquement (l'ensemble du registre actuel) | Aucun |
| **Radar** | Écho + sous-ensemble de sources payantes choisies par nous | Le même portail que Radar+, mais restreint aux sources qu'on propose, avec une couche de **paiement intégré** (l'utilisateur paie pour débloquer, nous gérons l'accès à la source) |
| **Radar+** | Radar + n'importe quelle source payante externe que l'utilisateur possède déjà | Le même portail, ouvert sans restriction, avec une couche de **gestion de clés API utilisateur** (l'utilisateur branche son propre accès, nous ne payons ni ne gérons la source) |

**Conséquence pour l'architecture : un seul portail à construire, avec deux couches différentes par-dessus, pas deux portails distincts.** Composants communs : gestion de connecteurs génériques par fournisseur, normalisation des données entrantes vers le même pipeline que les sources internes (résolution NEQ, score de confiance, sphères de besoin — sections 6/7/9). Composant propre à Radar : paiement intégré. Composant propre à Radar+ : gestion de clés API utilisateur, sans transaction financière de notre part sur la source elle-même.

Toute source ajoutée par un utilisateur Radar+ doit suivre le même gabarit de registre que les sources internes (section 9) — champs pertinents, méthode d'accès, sphère de besoin associée — et peut révéler une sphère de besoin non encore répertoriée dans la liste de la section 4 (ex. la sphère "Financement / accès au capital" ajoutée ci-dessus est née de ce constat, pas d'une anticipation).

**Décision de priorisation (premier cas concret à construire) :** plutôt que de bâtir le portail dans l'abstrait, on le construit contre un premier cas réel. Source payante prioritaire : **agrégateur de recrutement, fournisseur TheirStack confirmé** (choisi plutôt qu'Apify — API structurée et légale, conçue pour ce cas d'usage précis, vs une place de marché de scrapers avec risque de conformité aux conditions d'utilisation des plateformes sources), pour réactiver pleinement le signal recrutement au-delà de Guichet-Emplois/EIMT, au bénéfice du persona agences de recrutement (Radar) et de tous les personas qui utilisent la vitesse/le volume d'embauche comme signal croisé secondaire. Solution de paiement retenue pour la couche Radar : **Stripe**, choix standard pour ce type de produit au Canada.

**Deuxième source payante candidate, pour Radar+ : Houski (houski.ca)**, API canadienne de données de propriétés, pour le persona courtiers immobilier commercial. Couverture commerciale confirmée réelle dans la documentation technique (champ `commercial_use`, `area_commercial_list_price_per_sq_m`, `expand_listing_event` pour les transactions/annonces) — pas seulement une mention marketing, contrairement à ce qu'une première recherche superficielle laissait croire (voir charte, section 8 : ne jamais présumer une limite non testée). 99$ US/mois minimum, payé à l'usage au-delà. **Validation en conditions réelles requise avant d'engager le budget de façon continue** — profondeur de couverture canadienne spécifiquement non confirmée dans la documentation seule.

**Format standard des cartes de source dans le portail (Radar et Radar+) :** chaque option de source présentée au client doit afficher deux éléments, jamais une seule ligne générique — le **domaine/type de la source** et **l'avantage concret que cette source apporte**, pour que le client choisisse en connaissance de cause plutôt que sur un nom de marque seul. Gabarit à suivre pour toute source ajoutée au registre :

| Source | Domaine/type | Avantage concret affiché |
|---|---|---|
| TheirStack | Agrégateur de données de recrutement | Signal de croissance via l'embauche active, au-delà de Guichet-Emplois/EIMT |
| HubSpot | CRM marketing + vente unifiés | Pour unifier marketing et vente, ou si vous faites déjà du marketing entrant |
| Pipedrive | CRM vente pure | Simple et rapide à configurer, abordable, pour une équipe de vente sans marketing intégré |
| Houski | Données de propriétés commerciales/résidentielles (Canada/É.-U.) | Signal de transactions et d'évaluations immobilières commerciales, pour les courtiers |

**Principe qui en découle, cohérent avec la charte section 8 :** ne jamais présumer qu'un client sait déjà quoi choisir entre deux options similaires — toujours vérifier et afficher la vraie distinction (comme HubSpot/Pipedrive, où la distinction réelle est la structure d'équipe et le besoin marketing, pas le secteur d'activité comme on l'avait d'abord supposé) plutôt qu'une affirmation plausible mais non vérifiée.



Dès qu'une entreprise est détectée par une source, peu importe le signal, le système doit tenter de trouver son site web officiel et d'en extraire un contexte léger — ce processus se fait systématiquement, à chaque entreprise détectée, pas seulement pour celles qui franchissent le seuil de notification. C'est la **dernière étape du pipeline, juste avant l'avertissement de l'utilisateur** : elle bonifie le profil de l'entreprise repérée avant que la notification soit envoyée.

**Fonctionnement :**
1. **Recherche de l'URL officielle** : à partir du nom d'entreprise (et de la ville/adresse si disponible via le REQ ou une autre source), rechercher le site web officiel. Aucune des sources actuelles ne fournit l'URL directement — cette étape est nécessaire.
2. **Ratissage léger et ciblé**, pas un crawl complet : pages prioritaires — accueil, à propos, services/produits, carrières/emplois, actualités/nouvelles, coordonnées/contact.
3. **Extraction structurée**, pour bonifier le profil du prospect avant notification :
   - description sommaire des activités et **domaine d'expertise précis** de l'entreprise
   - **coordonnées complètes** si disponibles publiquement (adresse, téléphone, courriel général)
   - indices de taille (nombre d'employés mentionné, multiplicité de sites/succursales)
   - mentions explicites d'expansion ou de nouveaux projets
   - offres d'emploi affichées sur le site (utile pour recouper avec le signal recrutement)
4. **Vérification de pertinence et filtre d'exclusion** : cette étape sert aussi à confirmer que l'entreprise est réellement pertinente pour l'utilisateur avant l'envoi de la notification. Si le contenu du site révèle que l'entreprise ne correspond manifestement pas au profil (ex. secteur d'activité incompatible, entreprise inactive, site indiquant une fermeture), le système doit pouvoir **exclure ce prospect** plutôt que d'envoyer une notification non pertinente.

**Règles de conception :**
- **Systématique, pour chaque entreprise détectée** : ce processus tourne pour toute entreprise repérée par une source, dès sa détection — pas seulement celles qui auraient déjà franchi un autre filtre. Ce choix implique un volume de requêtes de recherche et de ratissage plus élevé, donc plus de temps et de ressources de traitement.
- **Position dans le pipeline :** cette étape se déroule après la détection du signal et le calcul du score de confiance, mais avant l'envoi de la notification — elle peut donc à la fois enrichir et, le cas échéant, annuler une notification qui s'avérerait non pertinente à la lumière du contenu du site.
- **Respect du robots.txt** et des limites de fréquence de requêtes, pas de sollicitation agressive d'un site.
- **Contexte complémentaire à la justification, pas un remplacement** : cette information enrichit le profil du prospect (coordonnées, expertise) et peut servir de filtre d'exclusion, mais ne remplace jamais la justification principale du signal détecté — le contenu d'un site peut être désuet ou incomplet, donc traité avec cette réserve dans la notification.
- Ce module suit le même principe de registre modulaire que les sources (section 9) : statut `actif`/`à développer`, activable/désactivable indépendamment du reste du système.

## 11. Prochaines étapes

Ce document sert de base à la conception technique, qui sera réalisée avec Claude Code plutôt que dans cette conversation.
