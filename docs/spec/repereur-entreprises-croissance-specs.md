# Repéreur d'entreprises en croissance — Spécifications du projet

## Principes directeurs — à respecter dans toute proposition future

Ces principes gouvernent l'ensemble du projet. Toute nouvelle source, fonctionnalité, ou modification proposée doit être vérifiée contre cette liste avant d'être ajoutée — pas seulement contre la logique du moment.

1. **Aucune donnée fictive ou simulée, jamais, même temporairement.** Les vraies données réelles sont non négociables, y compris pendant le développement et les tests.
2. **Toute source gratuite et de bonne qualité fait partie du produit, sans exception de priorisation.** Une source n'est écartée que pour deux raisons précises : elle est légalement inaccessible, ou elle exige un abonnement payant (décision budgétaire qui revient à Alexandre, jamais un choix fait à sa place).
3. **Principe de calibration, non négociable : aucune source n'est activée sans une règle concrète et vérifiable qui distingue un vrai signal de croissance du bruit.** Une source qui ne peut pas être calibrée reste en réserve, non activée — le nombre de sources actives n'est jamais l'objectif, la précision des résultats l'est.
4. **Vérifications de base obligatoires avant toute présentation d'un prospect** (statut légal, signe d'activité, cohérence d'identité) — dans tous les modes d'usage, sans exception.
5. **Un seul indice de confiance unifié par notification** — jamais de jauges parallèles (urgence, gradation séparée par signal, etc.).
6. **Polyvalence d'utilisation : rien n'est codé en dur pour le cas d'usage d'Alexandre.** Le produit doit rester utilisable par n'importe quel type de fournisseur de service B2B avec la même architecture, sans modification de code.
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

## 6. Score de confiance et sensibilité

**Principe d'unification, essentiel pour l'ergonomie web puis mobile :** il n'existe qu'**un seul indice de confiance par notification** — pas de jauges parallèles (urgence, gradation par signal, etc.). Tout facteur pertinent, y compris la notion d'urgence, est plié dans ce score unique plutôt que présenté comme une mesure séparée. L'utilisateur ne voit et n'interprète qu'une seule chose par notification : Faible/Moyen/Élevé.

Ce score unifié est calculé à partir de trois éléments qui s'additionnent ou se soustraient sur la même échelle :
1. **Critères propres au signal** (table ci-dessous)
2. **Bonus de corroboration multi-signaux** (voir plus bas) — plusieurs signaux indépendants sur la même entreprise renforcent le score
3. **Facteur de fraîcheur** : le score diminue avec le temps écoulé depuis la détection du signal. Ce facteur remplace ce qui aurait pu être une "jauge d'urgence" séparée — un signal ancien devient moins pertinent avec le temps, sans qu'on ait besoin d'un deuxième indicateur pour l'exprimer.

Le seuil global de sensibilité de l'utilisateur (Faible/Moyen/Élevé) filtre les notifications selon ce score unique. Pas de ML requis pour la v1.

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

### Corroboration multi-signaux

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
  - **Champs pertinents :** nom de l'employeur, **titre du poste (texte intégral, pour l'analyse qualitative des mots-clés)**, profession/CNP (Classification nationale des professions), nombre de postes, salaire offert, ville/région, date de publication
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
2. RDPRM — gratuit, public, signal précoce (Signal 2 : financement)
3. Guichet-Emplois (Job Bank Canada) — gratuit, structuré, données ouvertes, couverture pancanadienne (Signal 3 : recrutement)
4. **Liste des employeurs avec EIMT positive (EDSC)** — gratuit, trimestriel, signal de pénurie de main-d'œuvre confirmé officiellement (Signal 3 : recrutement) — **nouvelle découverte, signal de très haute qualité**
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

- **Phase 1 — chemin complet de bout en bout, avec 4 sources seulement :** SEAO, RDPRM, REQ, Guichet-Emplois — une source par grande catégorie de signal (appels d'offres, financement, registre corporatif, recrutement). L'objectif de cette phase est de valider l'ensemble du pipeline (détection → résolution NEQ/REQ → score de confiance → vérifications de base → enrichissement web → notification) de bout en bout, pas d'avoir une couverture complète.
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
| Méthode d'accès | API, données ouvertes, scraping, agrégateur tiers |
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

### Polyvalence d'utilisation — ne pas coder en dur le cas d'usage d'Alexandre

Le produit doit rester utilisable par n'importe quel type de fournisseur de service B2B, pas seulement un consultant en implantation de systèmes d'inventaire. Ça implique :

- **Aucune logique ne doit assumer un secteur, un service, ou une sphère de besoin particulière.** La correspondance entre signaux, sphères, et mots-clés (sections 4 et 7) doit rester généralisée — un agent immobilier commercial, un courtier d'assurance, une agence de recrutement, ou même un chercheur d'emploi individuel doivent pouvoir configurer un profil et obtenir des résultats pertinents, sans qu'aucun code ne soit écrit en fonction du profil d'Alexandre spécifiquement.
- **Le dossier cumulatif par entreprise (identifié par NEQ, section 5/9) doit être conçu pour pouvoir éventuellement supporter une liste de surveillance par entreprise nommée**, en plus de la détection par profil/sphère — même si ce mode d'usage n'est pas construit pour le prototype 1. Ne pas fermer cette porte par une hypothèse de conception qui suppose que toute entreprise suivie provient nécessairement d'une correspondance de profil.
- **Hors scope explicite pour le prototype 1**, à ne pas construire maintenant : une logique inversée qui détecterait le déclin plutôt que la croissance (ex. repérer des entreprises en difficulté pour des courtiers en fusions-acquisitions), et une couche d'agrégation produisant des statistiques ou tendances régionales plutôt que des résultats par entreprise. Ces deux cas demanderaient une polarité de scoring et un type de résultat fondamentalement différents de ce que documente ce projet — ne pas complexifier l'architecture actuelle en anticipation de ces cas non confirmés.

## 10. Enrichissement contextuel via le site web du prospect

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
