# FALKYE — Stratégie commerciale, positionnement et personas

**Mise à jour du 4 septembre 2026.** Ce document reste séparé des spécifications techniques
(`falkye-specifications-produit.md`) et de la charte (`charte-falkye.md`), auxquelles il renvoie plutôt
que de dupliquer leur contenu. La grille des fonctionnalités et le tableau des sources par plan, qui
existaient en PDF distincts, sont maintenant intégrés aux sections 4 et 12 des spécifications — c'est là
que vit l'état à jour.

---

## 1. Positionnement

FALKYE est une solution de détection de la croissance d'entreprise. La vente de services B2B n'est qu'un
des usages possibles, pas une limite du produit — chambres de commerce, conseillers en immigration,
développement économique régional et institutions financières s'y ajoutent, et d'autres usages restent à
découvrir.

Le premier public visé reste les travailleurs autonomes et micro-PME de services qui ne peuvent pas se
payer les outils existants — Owler, ZoomInfo, Apollo, Lead411, Crunchbase, à 75 $ US et plus par mois,
pensés pour des équipes de vente. Un outil de repérage simple, pour une personne qui gère seule sa
prospection, qui s'étend ensuite aux PME et aux institutions avec Radar et Radar+.

---

## 2. Le avantage défendable — 

**Correction déjà consignée : l'affirmation initiale « aucun concurrent n'a de raison de construire ça
pour le Canada » était fausse.** Deux concurrents canadiens réels existent — **Deep Data** (29 M
d'enregistrements, subventions fédérales, contrats gouvernementaux, profils d'entreprises, Québec
inclus, 149-499 $ CAD/mois) et **BidOps** (veille d'appels d'offres canadiens incluant le SEAO,
9,99 $ CAD/mois). L'accès brut aux données gouvernementales n'est donc pas un avantage défendable.

**Ce qui reste vrai et vérifié :** aucun des concurrents identifiés — Pharow, Corporama, Kompass,
Manageo, Sparklane du côté français; Deep Data et BidOps du côté canadien — n'offre de veille continue
par profil avec notification automatique combinée à un score de pertinence croisé par sphère de besoin.
Deep Data et BidOps sont des outils de recherche : l'utilisateur cherche activement, encore et encore.
Aucun ne fait de mise en correspondance service↔besoin ni de croisement de signaux en A/AA/AAA. Et leurs
clientèles diffèrent — Deep Data et BidOps s'adressent à des entreprises qui cherchent elles-mêmes des
contrats et des subventions, pas à des fournisseurs qui cherchent des clients en croissance.

### Ce qui rend l'avantage défendable difficile à rattraper — l'accumulation, pas l'accès

**L'avantage ne vient pas de ce à quoi FALKYE accède, mais de ce qu'il conserve.** Un concurrent qui vend
de la recherche active interroge une base et oublie la question. FALKYE garde quatre actifs qui ne
s'achètent pas et ne peuvent que s'accumuler : le dossier cumulatif par entreprise, le registre de
correspondances sphère↔signal, la table d'apprentissage d'appariement, et le journal de ce qu'on lui a
demandé et qu'il ne savait pas faire.

Deux capacités en découlent directement, et **elles sont structurellement impossibles pour un outil de
recherche** :

- **Le signal par absence** — croissance d'effectifs et nouvel établissement, *sans* financement public
  ni classement encore visible, signale une traction précoce avant qu'elle soit publique. Exprimer une
  absence exige de connaître l'ensemble de ce qui aurait dû apparaître, et de l'avoir gardé.
- **La trajectoire** — trois signaux en deux mois valent mieux que trois signaux en deux ans.
  L'accélération ne se déduit pas d'un instantané.

**Conséquence commerciale directe : l'horloge du produit tourne sur l'accumulation, pas sur le
développement.** Un concurrent qui déciderait aujourd'hui de copier l'approche repartirait d'une mémoire
vide, même en achetant les mêmes sources demain.

### Revalidation obligatoire

**Notre avantage a été vérifié à une date précise. Il doit être revérifié, parce qu'il a déjà changé une
fois.** C'est tout ce que cette section demande de retenir : ce n'est pas un acquis, c'est un constat qui
se périme.

**Trois situations obligent à revérifier tout de suite, sans attendre l'échéance** : un concurrent
identifié annonce de la veille continue ou de la notification automatique; un concurrent adopte la mise
en correspondance service↔besoin; un fournisseur de données lance un produit destiné aux fournisseurs de
services plutôt qu'aux chercheurs de contrats.

**Si un avantage défendable tombe, il sort du matériel de vente le jour même**, sans attendre de savoir par quoi le
remplacer.

---

## 3. Marché adressable et portée

**Décision du 4 septembre 2026 : un produit pleinement fonctionnel au Québec d'abord, et tout ce qui
vient de l'extérieur du Québec est mis en veilleuse.**

La distinction qui décide n'est pas le territoire d'origine d'une source mais **qui elle couvre** : les
sources fédérales où figurent les entreprises québécoises — subventions, contrats, EIMT, CIPO, registre
des lobbyistes — restent au développement. Quatre sources passent en veilleuse : licences de Toronto et
de Vancouver, contrats de la Nouvelle-Écosse, Corporations Canada. Leur code, leurs tests et leur état
sont conservés; elles ne sont simplement plus ordonnancées ni maintenues.

**Effet sur les personas :** ceux qui reposaient sur un ancrage hors Québec — développement économique
régional pour ses territoires hors province, et tout persona s'appuyant sur les licences municipales de
l'Ouest ou les contrats néo-écossais — ne sont plus servis pour ces territoires. Ils restent au tableau,
puisque la mise en veilleuse est une décision de séquencement, mais ils ne se vendent pas d'ici là. Les autres
provinces viendront ensuite. Une source pancanadienne reste retenue si elle améliore les résultats
obtenus au Québec — c'est le seul critère.

Le marché est modeste en v1, et c'est acceptable. Trois raisons rendent ce choix plus fort qu'une simple
gestion de charge.

Un produit qui fonctionne bien sur un territoire est vendable; un produit à moitié fonctionnel sur dix ne
l'est pas — et à l'échelle d'une personne seule, la deuxième version ne se rattrape pas, chaque
territoire ajouté diluant l'attention au lieu de l'élargir.

**Le Québec est le seul territoire où tout existe** : un identifiant obligatoire pour toute entreprise,
deux sources qui le livrent directement, une source Piste solide, des contrats publics, du financement,
des permis, une mesure de taille. Ailleurs, il n'y a que des fragments. C'est donc le seul endroit où la
thèse du produit peut réellement être vérifiée — si le croisement ne produit pas assez de bons résultats
là, il n'en produira pas ailleurs avec moins de données.

**L'expansion reste la vraie manette de croissance**, et elle reste possible sans reconstruire le moteur —
à une condition : que la séparation entre identité interne et identifiants externes soit faite avant que
le volume de dossiers accumulés en renchérisse le coût.

---

## 4. Tarification

**Les prix des trois paliers vivent à un seul endroit : `falkye-specifications-produit.md`, section 12.1.**
*Ce document en a longtemps porté une copie; elle a été retirée le 11 septembre 2026 (registre, D35). Un
prix se périme, et il ne peut pas se périmer à trois endroits à des vitesses différentes.*

| Plan | Public visé |
|---|---|
| **Écho** | Travailleurs autonomes, petites entreprises |
| **Radar** | PME en croissance — le choix qu'on veut voir dominer |
| **Radar+** | Entreprises, institutions, cabinets multi-services ou multi-territoires |

**Coût d'infrastructure, mesuré le 4 septembre 2026 : environ 40 à 60 $ CA par mois** — serveur, base
distante et service d'envoi de courriel réunis. **Soit environ deux abonnés Écho pour couvrir
l'infrastructure complète.**

C'est un fait d'affaires utile à garder en tête. Il dit que le seuil de viabilité est bas, que le coût
marginal d'un abonné supplémentaire est proche de zéro à cette échelle, et que la pression sur les prix
ne viendra pas de l'infrastructure. Les deux vrais coûts variables du produit sont ailleurs : les sources
payantes et les appels aux modèles de langage.

Le prix de Radar+ reste **une décision ouverte portant une échéance**, à revoir contre un tableau
comparatif de Deep Data, Pharow et BidOps une fois le produit complet.

### Ce qui décide du palier d'une source

**Le classement se fait par couple source × sphère, jamais par source seule.** Une source est **de
couverture** quand, sans elle, la sphère produit zéro résultat ou seulement des résultats non
discriminants — elle appartient alors au palier où la sphère est offerte, peu importe son coût. Elle est
**d'enrichissement** quand elle améliore un résultat qui existerait de toute façon — elle va au minimum
dans Radar.

**En l'absence de mesure, le défaut est inversé par rapport à l'intuition : une source nouvelle va dans
Écho**, sauf démonstration chiffrée que sa sphère y fonctionne déjà. Se tromper vers Écho coûte un
argument de vente; se tromper vers Radar coûte un abonné qui ne reçoit rien et ne revient pas.

**La règle vaut aussi pour les fonctionnalités.** Celle qui corrige l'**exactitude** de ce qui est montré
appartient au palier où le résultat est offert; celle qui ajoute de la **profondeur** suit la règle de
palier normale. Trois corrections appliquées sur cette base : le **filtre par taille** passe à Écho (même
classe d'outil que les curseurs de sensibilité, déjà présents partout); la **rétroaction « Pas
pertinent »** existe dans tous les paliers, puisqu'elle alimente la seule boucle de correction du
moteur; et le **bonus de corroboration inter-provinciale passe en veilleuse**, sans quitter le produit,
tant que la portée reste québécoise.

**Écho dispose d'un tableau de bord** (décision du 4 septembre 2026). Un produit qui livre des
opportunités sans endroit pour les colliger oblige l'abonné à gérer sa prospection dans sa boîte de
réception. La frontière entre les paliers porte donc sur **consulter et agir**, jamais sur **voir** :
Écho collige, révise, trie et rétroagit; Radar outille l'action.

**Ce que Radar conserve pour justifier le saut d'Écho à Radar** *(prix en spéc. 12.1)* : statuts de suivi complets formant
un pipeline, amorces de premier contact, carte géographique, intégration CRM, TheirStack, RDPRM,
cadence en temps réel.

**Deux différenciateurs disparaissent avec cette décision** — l'existence du tableau de bord et la
profondeur d'exploration au-delà du plafond de vingt notifications. L'assistance IA de niveau 2, elle aussi, cesse d'être un
différenciateur : c'est une escalade qui rend la configuration juste, pas un enrichissement.
L'argumentaire de Radar repose désormais entièrement sur l'outillage d'action et les sources payantes,
plus sur aucune restriction de visibilité ni de justesse. C'est plus honnête à vendre, et plus étroit à défendre — à surveiller quand
viendra la révision du prix de Radar+.

---

## 5. Tableau des personas

**Principe rappelé pour chaque ligne : un signal isolé est souvent consultable ailleurs dans le même
temps de recherche — ce n'est pas un avantage. L'avantage vient du croisement.**

### ⚠️ Réserve majeure à lire avant le tableau — le signal recrutement

Une vingtaine des personas ci-dessous croisent un **signal de recrutement**. Or le Guichet-Emplois, qui
portait ce signal dans les versions antérieures de ce tableau, est repassé à `à développer` : **son
fichier en vrac ne contient pas le nom de l'employeur**, confirmé dans les données réelles et dans la
documentation officielle. Sans nom d'employeur, aucune notification par entreprise n'est possible.

Le remplaçant actif est **l'EIMT positive**, qui donne le nom — mais qui ne couvre que les employeurs
recourant à des travailleurs étrangers temporaires. **C'est un sous-ensemble ciblé, pas l'ensemble du
marché.** Le signal « vitesse d'embauche » sur lequel reposent ces personas est donc nettement plus mince
que le tableau ne le laisse croire, tant que TheirStack n'est pas validé avec une clé réelle.

Ce n'est pas une raison de retirer ces personas — c'est une raison de ne pas les vendre comme s'ils
étaient pleinement servis. La colonne « Réserve » ci-dessous le marque explicitement.

| Type d'utilisateur | Plan | Sources croisées | Ce que le croisement priorise | Réserve |
|---|---|---|---|---|
| Consultants et conseillers d'affaires indépendants | Écho | Tous signaux combinés | Plusieurs signaux de croissance simultanés | — |
| Chercheurs d'emploi individuels | Écho | REQ + signal recrutement | Entreprises qui embauchent ET viennent de s'établir | Recrutement |
| Travailleurs autonomes en services professionnels | Écho | Tous signaux combinés | Flux pondéré par intensité de croissance | — |
| Fournisseurs d'équipement et systèmes pour restaurants/bars | **Écho** | RACJ (nouveau permis, capacité en hausse) + établissements alimentaires Montréal | Ouverture ou agrandissement confirmé, avec NEQ direct | — |
| Consultants en développement de franchise | **Écho** | REQ (entreprise déjà établie) + CIPO (nouveau dépôt de marque) | La marque est l'actif central d'un réseau de franchise | — |
| Firmes d'ingénierie et de design de produit | **Écho** | CIPO (dessin industriel enregistré) + REQ | Nouveau produit physique concret mis en marché | — |
| Agences de relations publiques et affaires gouvernementales | **Écho** | Registre fédéral des lobbyistes (nouvel enregistrement) + REQ | Entreprise qui commence à défendre ses intérêts au fédéral | — |
| Agences de traduction et services de francisation | **Écho** | OQLF (certifiées ou non conformes) + REQ | Seuil de 25+ employés confirmé à une date | Autorisation |
| Agences de recrutement | Radar | REQ + TheirStack + Deloitte Fast 50 | Embauche en croissance rapide confirmée | Clé API |
| Fournisseurs 3PL | Radar | REQ + signal recrutement opérations | Croissance physique + embauche logistique | Recrutement |
| Fournisseurs de services gérés en TI (MSP) | Radar | REQ + signal recrutement général | Croissance d'effectifs sans équipe TI visible | Recrutement |
| Entrepreneurs en construction/rénovation commerciale | Radar | REQ + SEAO (déjà titulaire de contrats) | Capacité financière démontrée | — |
| Courtiers en énergie commerciale | Radar | REQ + secteur énergivore | Nouveaux établissements à forte consommation | Aucun signal de consommation |
| Sociétés de crédit-bail d'équipement et de flotte | Radar | REQ + RDPRM + signal recrutement | Expansion physique et d'effectifs | Recrutement, RDPRM |
| Fournisseurs de télécommunications d'affaires | Radar | REQ (succursale vs siège) | Vraie installation vs mise à jour administrative | — |
| Systèmes de sécurité et alarmes commerciales | Radar | REQ + SEAO + RACJ (capacité) | Établissements avec exigence contractuelle | — |
| Fournisseurs de mobilier de bureau commercial | Radar | REQ + signal recrutement bureau | Distingue expansion de bureau et d'entrepôt | Recrutement |
| Compagnies de déménagement commercial | Radar | REQ (siège vs établissement secondaire) | Vrais déménagements plutôt que nouvelle filiale | — |
| Fournisseurs d'enseignes et impression commerciale | Radar | REQ + secteur détail + RACJ | Établissements orientés client | — |
| Gestion des déchets et matières résiduelles | Radar | REQ + signal recrutement manufacturier | Croissance réelle de volume de production | Recrutement |
| Consultants et avocats en immigration d'affaires | Radar | EIMT positive + REQ | Recours récurrent plutôt qu'un cas ponctuel | — |
| Fournisseurs de systèmes POS et paiement | Radar | REQ + secteur détail + RACJ | Établissements de vente au détail | — |
| Nettoyage et entretien ménager commercial | Radar | REQ + taille d'établissement + RACJ (capacité) | Plus grands établissements, contrat plus rentable | — |
| Automatisation industrielle et robotique | Radar | REQ manufacturier + CIPO (brevets) + signal recrutement | Dépassement confirmé de la capacité manuelle | Recrutement |
| Consultants en SST | Radar | REQ + vitesse d'embauche | Vitesse de croissance comme facteur de risque | Recrutement |
| Formation et développement des compétences | Radar | Vitesse d'embauche + REQ | Vitesse plutôt que volume cumulé | Recrutement |
| Agences de marketing digital et de branding | Radar | REQ + **absence** de Fast 50/Investissement Québec | Croissance rapide encore peu visible publiquement | Signal par absence à construire |
| Télématique et gestion de flotte | Radar | REQ + RDPRM (véhicules) + signal recrutement | Expansion de flotte réelle | Recrutement, RDPRM |
| Gestion immobilière commerciale | Radar | REQ + délai depuis l'établissement (6-18 mois) | Établissements récents en stabilisation | — |
| Courtiers en cautionnement | Radar | SEAO (garantie exigée) + REQ (âge/taille) | Jeunes entreprises avec contrat disproportionné | — |
| Consultants en subventions et financement | Radar | Investissement Québec + REQ | Octroi isolé vs vraie traction | — |
| Firmes de cybersécurité pour PME | Radar+ | REQ + signal recrutement rapide | Croissance numérique sans renfort de sécurité | Recrutement |
| Consultants en durabilité et conformité ESG | Radar+ | Investissement Québec + REQ | Entreprises visant des subventions de conformité | — |
| Courtiers immobilier commercial | Radar+ | REQ + Houski + signal recrutement | Besoin probable d'un deuxième espace bientôt | Recrutement, clé Houski |
| Assureurs commerciaux | Radar+ | RACJ (capacité) + permis + RDPRM + REQ | Changement d'exposition assurable | Sphère dérivée |
| Prêteurs alternatifs | Radar+ | REQ + Investissement Québec | Solvabilité démontrée plutôt que supposée | — |
| Développement économique régional | Radar+ | REQ + Fast 50 + agrégation territoriale | Fort potentiel d'impact économique local | Agrégation par secteur cassée |
| Veille concurrentielle | Radar+ | Liste de surveillance nominative | Fonctionnalité produit distincte | Non construite |
| Banquiers d'investissement / repéreurs d'acquisitions | Radar+ | Fast 50 + Investissement Québec + REQ (âge) | Cibles en forte croissance encore jeunes | — |
| Processeurs de paiement / fintech | Radar+ | REQ (détail) + signal recrutement vente | Croissance de volume de vente | Recrutement |
| Courtiers en avantages sociaux | Radar+ | OQLF (seuil 25+) + REQ (âge) | Franchissement d'un seuil d'effectifs | Autorisation OQLF |
| Éditeurs de logiciels RH/paie | Radar+ | OQLF (seuil 25+) + signal recrutement | Dépassement de la capacité des outils actuels | Autorisation, recrutement |
| Investisseurs providentiels et capital de risque | Radar+ | REQ + recrutement + **absence** de Fast 50/IQ | Traction précoce avant qu'elle soit publique | Signal par absence à construire |
| Gestion de projet externalisée (PMO) | Radar+ | REQ (nouvel établissement) + croissance rapide | Transition plus grande que la capacité interne | Recrutement |
| Cabinets de propriété intellectuelle | Radar+ | CIPO (portefeuille en croissance) + REQ | Portefeuille qui grossit = besoin juridique récurrent | — |

**Retirés** (avantage faible ou peu démontrable) : cabinets comptables et fiscalistes, cabinets
d'avocats corporatifs, associations sectorielles, coachs et consultants en gestion. Ce n'était pas une
erreur d'analyse — c'est le produit qui indiquait ses limites. Les services horizontaux, achetables en
tout temps sans moment déclencheur, se prêtent mal à un signal de timing.

**Retirés par chevauchement** : équipement industriel (→ automatisation), génie-conseil et architecture
(→ construction), courtiers hypothécaires commerciaux (→ prêteurs alternatifs et immobilier commercial).
Note : les relations publiques, autrefois retirées vers le marketing, sont redevenues un persona
autonome depuis que le registre des lobbyistes leur donne un signal propre.

---

## 6. Constat clé — Radar demande un moteur, pas des sources

La majorité des personas Radar reposent sur des combinaisons de sources déjà actives. Le travail restant
n'est pas une segmentation par secteur, c'est le moteur de score de pertinence qui pondère plusieurs
signaux ensemble — et c'est lui qui porte l'avantage réel.

**Trois besoins de source distincts subsistent** :
- **Signal recrutement** — TheirStack est retenu, actif au registre, mais **attend une clé API**. Tant
  qu'il n'est pas validé, une vingtaine de personas reposent sur l'EIMT positive seule, dont la
  couverture est un sous-ensemble.
- **Courtiers en énergie commerciale** — aucun signal de consommation énergétique en source ouverte
  identifié à ce jour. Non résolu.
- **Financement par capital de risque privé** — Crunchbase, décision budgétaire jamais tranchée, angle
  mort documenté depuis longtemps.

---

## 7. Le public institutionnel — la force la moins exploitée

La charte nomme depuis le début les chambres de commerce, le développement économique régional et les
institutions financières. Un persona existe. Les tableaux de bord agrégés par territoire sont **déjà
construits**. Et pourtant le produit entier est conçu autour du vendeur B2B.

**Trois raisons structurelles de ne pas traiter ce public comme secondaire.**

Un organisme de développement économique **n'a rien à vendre au prospect détecté** — il veut savoir
quelles entreprises de son territoire grandissent, pour intervenir au bon moment et pour justifier son
impact. La fragilité assumée du modèle (section 11) **ne s'applique pas à lui** : il n'y a rien à
contourner.

Son budget est institutionnel plutôt que celui d'un travailleur autonome.

Et un organisme de ce type est aussi **un canal vers ses propres membres**.

**Ce qui bloque aujourd'hui, et qui est du déblocage plutôt que du neuf :** l'agrégation par secteur est
cassée par la granularité du champ en texte libre du REQ — 211 valeurs distinctes sur 311 notifications
réelles. Et les entreprises détectées hors Québec tombent systématiquement en « non classé ». Il reste
aussi à vérifier que le mode d'usage institutionnel — suivre un territoire entier plutôt qu'un profil de
vente — est réellement exprimable dans l'architecture de profil actuelle.

---

## 7bis. Deux façons d'utiliser le même produit — réflexion du 5 septembre 2026

**Note de portée : rien ici n'affecte le développement en cours.** C'est une observation sur la manière
dont différents types d'utilisateurs se serviraient du produit tel qu'il existe. Aucun chantier n'en
découle, aucune décision n'est prise.

### Le sens de la question n'est pas le même

**Le fournisseur de services demande « qui a besoin de ce que je vends ».** Il filtre par sphère de
besoin, veut peu de résultats mais bien ciblés, et agit sur chacun individuellement.

**L'organisme institutionnel demande « qu'est-ce qui bouge chez moi ».** Il ne filtre pas par
correspondance — il veut voir l'ensemble de son territoire, agrégé, et comparer dans le temps.

Même moteur, mêmes sources, même entité observée. Ce qui change est la correspondance finale : le
premier l'utilise, le second la met de côté.

### L'organisme utilise moins du produit, pas plus

C'est le constat qui change l'estimation du chantier 20, aujourd'hui rédigé comme du déblocage
technique. Ce public **n'a besoin ni des amorces de premier contact, ni de l'intégration CRM, ni du
pipeline de statuts** — il n'a personne à contacter.

Ce qu'il lui faut : l'agrégation par territoire et par secteur, la comparaison dans le temps, et
l'export pour un rapport. Autrement dit une **soustraction plus une vue**, pas une seconde moitié de
produit à construire.

### La distance technique est mince, la distance commerciale est grande

*Le prix ne se justifie pas de la même façon.* Le fournisseur calcule une rentabilité — combien de
contrats contre combien ça coûte. L'organisme paie sur un budget de fonctionnement, pour un outil de
mission. Deux plafonds différents, deux cycles différents.

*La fragilité assumée du modèle ne s'applique pas à lui.* Rien n'empêche un fournisseur de contourner
la plateforme une fois le prospect connu; l'organisme, lui, n'a personne à contacter. Ce qu'il achète
est la vue elle-même.

*Le cycle de vente diffère du tout au tout* — long, parfois par appel d'offres, avec décision
collective et vocabulaire distinct. C'est le seul endroit où l'écart coûte réellement quelque chose.

*Et probablement le nom.* « Radar d'opportunités d'affaires » ne dit rien à quelqu'un qui ne cherche
pas d'opportunités, alors que le moteur qu'il utiliserait est exactement le même.

### Ce qui reste ouvert

Est-ce un second public du même produit, ou un produit distinct partageant le même moteur? La réponse
tient moins à la technique qu'à la mise en marché, et elle ne presse pas. À reprendre quand une boucle
aura tourné et que le premier public sera servi.

## 7ter. Souplesse de mise en marché — porte à garder ouverte, 7 septembre 2026

**Note de portée : rien à construire, rien à configurer.** Ce qui suit ne change aucune décision en
cours. C'est une porte à ne pas fermer par inadvertance.

### Pourquoi cette porte compte plus que les autres

**Le portefeuille de sources est un risque, pas une hypothèse.** Le registre des entreprises porte une
licence non commerciale, et il est le pivot du produit — sans lui, aucune résolution, aucun dossier
cumulatif. Trois autres sources portent des licences jamais vérifiées.

Si une autorisation est refusée ou assortie de conditions inacceptables, **ce n'est pas une source qui
tombe, c'est le socle**. La souplesse de mise en marché n'est donc pas une extension : c'est **ce qui
reste du produit** si le portefeuille devient inexploitable commercialement.

### L'inversion — le moteur va aux données

Une organisation qui possède déjà ses données branche le moteur dessus. **Trois contraintes tombent
d'un coup :** aucune licence à négocier, le client étant propriétaire; aucune question de résidence,
les données ne bougeant pas; aucun portail à moissonner, le client ayant ses données à la source —
souvent plus complètes et plus fraîches que ce qui est publié.

**Le mécanisme existe déjà en germe.** Le palier supérieur prévoit que le client apporte ses propres
clés d'accès, avec son instance cloisonnée. La différence d'échelle est réelle — il apporterait alors
**toutes** les sources plutôt qu'une de plus — mais c'est le même geste.

**Contrainte à respecter d'ici là, et c'est la seule chose demandée : le moteur ne doit jamais présumer
qu'il est propriétaire de ses sources.** Concrètement, l'ingestion reste séparable de la façon dont la
donnée arrive — le registre porte déjà cette idée avec l'import manuel, il s'agit de ne pas la perdre.
Et le client apportant ses sources ne doit pas être conçu comme un cas particulier réservé à un palier,
mais comme la forme générale dont le nôtre est une variante.

### Trois angles, aucun recommandé

*Le moteur chez le client.* Aucune licence à obtenir, mais un cycle de vente institutionnel et un
produit qui n'est plus le même.

*La méthode plutôt que le logiciel.* Question déjà ouverte à la charte, section 20. Le diagnostic se
vend même si aucune source ne peut être exploitée commercialement.

*Le chemin actuel, assumé.* Obtenir les autorisations une à une. Il n'est pas fermé — la demande au
registraire n'a même pas encore été faite.

**Ce qui décide entre les trois est une information qu'on n'a pas :** ce que le registraire répond quand
on demande. Tout le reste est de la spéculation autour de cette réponse. **La vraie action, le moment
venu, n'est pas d'explorer davantage — c'est d'écrire.**

## 8. Sourcing — état des décisions

TheirStack est retenu et attend sa clé. Houski est un candidat pour l'immobilier commercial, avec une
validation canadienne requise avant d'engager le budget — et en production, chaque client Radar+ apporte
sa propre clé, jamais un accès partagé. Crunchbase, ProcureData et le registre de C.-B. restent des
décisions ouvertes. **Elles vivent au registre des décisions ouvertes**, en tête de
`falkye-audit-et-mandat.md`, qui porte leur état à jour — *ni leur liste ni leur compte ne se recopient
ici*. **Aucune ne portait de date avant le 9 septembre 2026**, ce qui est exactement ce qui avait fait
sortir Crunchbase du suivi pendant des mois *(journal, cas 15)*.

*Rappel de portée : le registre de C.-B. porte sur un territoire en veilleuse. Il ne se rouvre que si la
règle de la section 3 le justifie — une source hors Québec n'est retenue que si elle améliore les
résultats obtenus au Québec.*

**Cinq sources gratuites ont été vérifiées le 3 septembre 2026** et sont prêtes à construire : RACJ,
CIPO, registre fédéral des lobbyistes, établissements alimentaires de Montréal, et OQLF sous réserve
d'autorisation. Le détail légal et technique est dans `falkye-sources-spheres-verifiees.md`.

**Trois découvertes de cette recherche ont une portée commerciale directe.** Le RACJ et l'OQLF livrent le
NEQ, ce qui élimine l'appariement approximatif pour les entreprises qu'ils touchent. Le champ `Capacite`
du RACJ et le seuil de 25 employés de l'OQLF donnent une **mesure** de taille là où le produit ne faisait
qu'estimer. Et le bulletin de l'AMF, qui aurait été le complément naturel du RDPRM pour le financement,
est **contractuellement bloqué** — ses conditions interdisent nommément d'indexer son contenu dans une
base de données.

---

## 9. Personas et sphères de besoin

Les personas ne sont pas la structure du produit — ce sont des exemples de qui pourrait s'abonner à une
sphère.

**Sphères couvertes par au moins un persona et au moins une source :** RH/recrutement, technologie/TI,
cybersécurité, logistique/flotte, sécurité physique, immobilier/aménagement, construction/rénovation,
SST, environnement/ESG, production/manufacturier, formation, entretien ménager, paie/avantages sociaux,
efficacité énergétique, commerce de détail, marketing/vente, planification stratégique, gestion de
projet, financement/accès au capital, franchisage, restauration, traduction, juridique, ingénierie,
relations publiques.

**Quatre sphères déclarées sans solution après la recherche du 3 septembre** — mais le diagnostic a
depuis été rouvert, et pour trois d'entre elles il était probablement trop pessimiste. La recherche avait
été menée **source-d'abord**, jamais au niveau du champ ni à rebours sur les sources déjà actives :

- **Assurance / gestion des risques** — six champs déjà captés portent le besoin : capacité d'accueil,
  valeur de travaux, nouvel établissement, nature du bien en garantie, volume d'embauche, valeur de
  contrat. Ce n'était pas « aucune source », c'était « aucune source **seule** » — la thèse même du
  produit. Devient une sphère **dérivée** documentée.
- **Analytique d'affaires** — le signal est le titre de poste (analyste de données, BI). Problème de
  mots-clés, pas de source.
- **Service à la clientèle** — même chose : une règle de mots-clés sur le signal recrutement, pas une
  nouvelle source.
- **Gestion documentaire** — reste honnêtement mince, même au niveau du champ. Seul l'angle OQLF, et il
  est indirect. À documenter comme **sans couverture** plutôt qu'à forcer.

**Une sphère sans couverture se montre comme telle au moment de la configuration du profil**, jamais
offerte comme si elle fonctionnait. C'est le corollaire commercial d'un principe de la charte : un
abonné qui s'inscrit pour une sphère vide ne recevra rien et conclura que le produit ne fonctionne pas —
alors que c'est la sphère qui est vide.

**Retirée du registre : « Gestion d'inventaire et d'actifs »** — c'était un service précis, pas une
catégorie générique. Un utilisateur décrivant ce service est rattaché par l'assistance IA à une sphère
existante.

**Le droit de refuser est un principe, pas une exception.** Trente-quatre sphères multipliées par les
territoires et les types d'utilisateurs, c'est une surface qu'une personne seule ne peut pas valider.
Ajouter une sphère, c'est s'engager à la servir.

---

## 10. Portes ouvertes pour l'évolution

Sphères, sources, types de signaux, cadences, types de profil : tout est extensible sans restructuration.
Implication tarifaire directe — une source ajoutée par un utilisateur Radar+ peut alimenter une sphère
existante ou en révéler une nouvelle, comme la sphère financement, née de ce constat. La segmentation par
plan doit rester assez souple pour absorber ces découvertes.

---

## 11. Fragilité de la mise en correspondance — décision assumée

Une fois qu'un prospect est présenté, rien n'empêche l'utilisateur de le contacter en dehors de la
plateforme. Aucune mesure technique ou contractuelle fiable n'existe à coût raisonnable. Décision : ne
pas construire de mécanisme pour l'empêcher — la valeur repose sur l'abonnement donnant accès continu aux
signaux et à leur précision, pas sur une transaction à protéger.

**Cette fragilité ne s'applique pas au public institutionnel** (section 7), qui n'a rien à vendre au
prospect détecté. C'est un argument de plus pour ne pas le traiter comme secondaire.

---

## 12. Flux de revenu potentiels, portes ouvertes

**Profils client et fournisseur.** Le champ `type de profil` existe déjà dans l'architecture, sans
mécanique de correspondance bidirectionnelle construite. Si développée, elle ouvrirait un modèle de
commission sur mise en relation — plus difficile à contourner que l'abonnement, puisqu'il s'agirait
d'une vraie mise en relation facilitée par la plateforme.

**Programmes partenaires des sources du portail.** S'inscrire aux programmes **Solution Provider /
Technology Partner** plutôt qu'aux programmes d'affiliation grand public : ces derniers interdisent
explicitement de référer des clients qu'on sert déjà directement, alors que les programmes partenaires
sont conçus pour ça. Commissions confirmées : HubSpot 30 % récurrent jusqu'à 12 mois, Pipedrive 20-33 %
selon le programme. TheirStack et Houski n'ont pas de programme confirmé.

**Les deux programmes n'ont pas les mêmes prérequis.** Le programme **Solution Provider** vise les
consultants et agences qui gèrent le CRM pour leurs clients et ne demande aucune application technique.
Le programme **Technology Partner** et le listage sur l'App Marketplace exigent une application publique
OAuth.

**Décision du 4 septembre 2026 : la connexion d'un CRM se fait par OAuth**, ce qui garde les deux
programmes accessibles. Le modèle par jeton collé, qui aurait fermé la moitié la plus large de ce flux
de revenu, est écarté — voir les spécifications, section 12.6.

**Chaque source du portail affiche son domaine et son avantage concret**, jamais un nom de marque seul.
La vraie distinction vérifiée entre HubSpot et Pipedrive est la structure d'équipe et le besoin
marketing — pas le secteur d'activité, hypothèse de départ qui ne s'est pas confirmée.

---

## 13. Mise en marché

- Communautés de consultants et de travailleurs autonomes, ordres professionnels sectoriels.
- Bouche-à-oreille organique plutôt qu'acquisition payante, au moins au démarrage.
- Écho comme mécanisme d'entrée à faible friction.
- **Les organismes institutionnels comme canal vers leurs membres** — un débouché et une distribution à
  la fois.

**Ce qui décide de la rétention n'est pas seulement la qualité du signal.** À contenu identique, la
formulation et le rythme de livraison décident souvent seuls entre un abonné qui reste et un abonné qui
part. Quinze notifications séparées transforment une bonne nouvelle en irritant; les mêmes quinze livrées
ensemble donnent l'impression d'un produit qui travaille. Et le mode de défaillance principal n'est pas
la mauvaise notification, c'est le **silence** — quelqu'un qui paie et ne reçoit rien pendant trois
semaines, sans pouvoir distinguer un territoire calme d'un produit brisé. Ces décisions sont traitées
comme des décisions produit, pas comme de la cosmétique.

---

## 14. Question ouverte — la méthode est-elle le produit?

La méthode de diagnostic — partir du service, remonter jusqu'au signal, et trouver la source qui
l'expose — est probablement la chose la plus difficile à copier dans tout le projet. Un concurrent qui
achète les mêmes données ne l'a pas, et chaque diagnostic effectué enrichit le registre de façon
permanente : le coût marginal décroît pendant que l'actif croît. C'est l'inverse d'un accès à des
données, qui coûte le même prix à tout le monde et n'appartient à personne.

Or la tarification traite cette méthode comme un avantage accessoire de Radar+ — un engagement de
priorité sur les développements futurs. Si l'affirmation ci-dessus est exacte, c'est peut-être la méthode
qui est le produit, et le logiciel qui en est le véhicule. Ça changerait le positionnement, le prix, et
probablement le premier public visé.

**Les deux lectures sont défendables et aucune n'est retenue aujourd'hui.** La question porte une
échéance de décision, et la trancher inclut « non, le logiciel reste le produit, et voici pourquoi ».

---

## 15. Décisions de fond issues de la recherche concurrentielle initiale

**Enrichissement de contacts individuels volontairement écarté**, au-delà des coordonnées déjà publiques
sur le site du prospect. C'est la fonctionnalité la plus demandée dans la catégorie chez les
concurrents, mais le risque de conformité est disproportionné par rapport à la valeur pour ce
positionnement — usage secondaire d'une donnée personnelle à des fins de prospection, au sens de la
LPRPDE. FALKYE est centré sur le signal de timing, pas sur le contact individuel.

**Pas de prospection automatisée.** L'amorce de premier contact est une aide à la rédaction, jamais un
message prêt à envoyer.
