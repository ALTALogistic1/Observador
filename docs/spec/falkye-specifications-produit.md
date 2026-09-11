# FALKYE — Spécifications du produit

**Version officielle du 4 septembre 2026**, tenue à jour depuis. Organisée selon le parcours réel de la
donnée plutôt que selon l'ordre historique d'accumulation.

> **⚠️ Deux sens de « état » cohabitent dans ce document.** L'**état d'une source** — l'instantané qui
> permet de calculer un diff — est en **section 5.2**. L'**état du produit**, ce qui est construit,
> déployé ou vérifié, est en **section 15**. Ce ne sont pas la même chose, et la contradiction du
> 7 septembre s'était logée exactement là. **Lire le glossaire en tête de `falkye-audit-et-mandat.md`
> avant ce document** — il fixe aussi le sens de « journal », de numéro contre rang, de statut
> d'exécution contre état de santé.

## Hiérarchie documentaire

Quatre documents, aux rôles distincts, à ne pas confondre :

- **`charte-falkye.md`** — les principes. Tranche en cas de contradiction, y compris contre un document
  plus récent. C'est là que vivent les décisions de fond et la mémoire des erreurs.
- **Ce document** — les spécifications. Ce que le produit fait et comment, à jour.
- **`falkye-audit-et-mandat.md`** — les chantiers de construction, avec leur ordre et leurs critères
  d'acceptation : **vingt-neuf numéros stables, vingt-six fiches, vingt-trois blocs de travail
  restants**. Il porte aussi **le glossaire des cinq mots qui portent deux sens** — à lire avant tout le
  reste — et **le registre des décisions ouvertes**, leur emplacement unique.
- **`strategie-et-personas.md`** — le marché, les personas, le positionnement concurrentiel.
- **`falkye-guide-ingenierie.md`** — les règles de vérification : ce qu'un test vert ne prouve pas, le
  glissement du décidé au fait, les critères de clôture.
- **`falkye-journal-des-cas.md`** — les incidents réels qui ont produit les règles. Les renvois
  « journal, cas N » y pointent, et nulle part ailleurs.

Ce que ce document décrit n'est pas entièrement construit. La section 15 dit précisément ce qui est
livré, ce qui est en cours, et ce qui reste à faire.

---

## 0. Principes directeurs

À vérifier avant toute proposition, pas seulement contre la logique du moment.

1. **Aucune donnée fictive ou simulée, jamais, même temporairement**, y compris en développement et en
   test.
2. **Toute source gratuite et de bonne qualité fait partie du produit.** Une source n'est écartée que
   pour deux raisons : elle est légalement inaccessible, ou elle exige un abonnement payant — décision
   budgétaire qui revient à Alexandre, jamais prise à sa place.
3. **Calibration obligatoire : aucune source n'est activée sans une règle concrète et vérifiable qui
   distingue un vrai signal du bruit administratif.** Une source non calibrable reste en réserve. Le
   nombre de sources actives n'est jamais l'objectif — la précision des résultats l'est.
4. **Vérifications de base obligatoires avant toute présentation d'un prospect**, dans tous les modes
   d'usage, avec le niveau atteignable déclaré par territoire (section 6).
5. **Un seul indice de confiance par notification** — jamais une jauge par signal détecté, jamais une
   jauge d'urgence parallèle. Ce principe porte sur l'affichage, pas sur le calcul : les trois axes
   internes (confiance, pertinence, appariement) restent séparés dans le moteur et se résolvent en une
   présentation unifiée.
6. **Polyvalence : rien n'est codé en dur pour le cas d'usage d'Alexandre.** Le produit doit servir
   d'autres types d'utilisateurs — fournisseurs de services, chambres de commerce, développement
   économique, institutions financières — avec la même architecture, sans modification de code.
7. **Architecture modulaire pour tout ce qui évolue** — sources, types de signaux, sphères, types de
   profil, statuts, cadences — chacun avec son registre extensible.
8. **L'identité d'entreprise est interne; les identifiants externes l'ancrent à un territoire.** Le NEQ
   est l'identifiant Piste du Québec et le meilleur ancrage disponible sur ce territoire. Il n'est pas
   la clé du moteur. Voir section 6.
9. **Ne pas complexifier en anticipation de cas non confirmés.** Deux cas restent explicitement hors
   portée : la détection du déclin plutôt que de la croissance, et toute logique de scoring à polarité
   inversée.
10. **Le dossier cumulatif se corrige, il ne s'efface pas.** Un fait invalidé reste visible comme
    invalidé. Aucune suppression silencieuse, à aucun stade.
11. **Proposer, jamais appliquer.** Seuils, liens champ↔sphère, pondérations : un mécanisme peut
    proposer, l'activation reste une décision humaine.

---

## 1. Le produit

### 1.1 Ce que FALKYE fait

FALKYE détecte les entreprises en croissance à partir de signaux publics, et met en correspondance ces
signaux avec le besoin qu'ils annoncent, pour prévenir l'utilisateur avant que l'entreprise publie un
appel d'offres — souvent avant qu'elle réalise elle-même qu'elle a un besoin.

L'utilisateur configure une fois son profil : localisation, rayon d'action, et une ou plusieurs sphères
de besoin qu'il sert. Le système surveille en continu et le prévient quand une entreprise correspond,
avec le motif précis du repérage, la sphère de besoin concernée, et un niveau de confiance.

**L'avantage défendable n'est pas la donnée brute** — d'autres y ont accès. Il tient à trois choses : le moteur de
croisement de signaux par sphère, la veille continue avec notification automatique, et la mise en
correspondance service↔besoin. Un signal isolé, aussi bien détecté soit-il, n'est pas le produit.

**L'avantage vient de ce que FALKYE conserve, pas de ce à quoi il accède.** Quatre actifs qui ne
s'achètent pas et ne peuvent que s'accumuler : le dossier cumulatif, le registre de correspondances
sphère↔signal, la table d'apprentissage d'appariement, et le journal de diagnostic. Corollaire
opérationnel : **l'horloge du produit tourne sur l'accumulation, pas sur le développement.**

### 1.2 Portée géographique

**Priorité : un produit pleinement fonctionnel au Québec d'abord.** Les autres provinces viendront
ensuite — **tout ce qui vient de l'extérieur du Québec est en veilleuse et sort du développement**. Ces
sources restent au registre avec leur code, leurs tests et leur état conservé; elles ne sont simplement
plus ordonnancées ni maintenues.

**La distinction qui décide n'est pas le territoire d'origine de la source, c'est qui elle couvre.** Une
source fédérale n'est pas « hors Québec » si les entreprises québécoises y figurent.

| Reste au développement | En veilleuse |
|---|---|
| Registre, appels d'offres, financement, permis d'alcool, établissements et permis municipaux, francisation | Licences de Toronto et de Vancouver |
| Subventions, contrats et autorisations fédérales — les entreprises québécoises y figurent | Contrats de la Nouvelle-Écosse |
| Marques et lobbyistes — dépôts d'entreprises québécoises | Registre fédéral des sociétés — n'ajoute rien au Québec |
| Palmarès canadiens incluant le Québec | |

**Ce que « en veilleuse » veut dire :** le connecteur n'est plus ordonnancé, son état cesse d'être
rafraîchi, aucun correctif ne lui est apporté, **et il ne figure plus dans l'argumentaire de vente**. Il
n'est ni supprimé ni retiré du registre — **c'est une décision de séquencement, pas un abandon**.

**⚠️ Conséquence sur la validation.** Au moment de la décision, une source en veilleuse était **la seule
à avoir produit un diff réel non nul**. Le moteur reste donc sans validation contre un vrai changement
observé sur une source active — **compléter celle du registre contre un fichier frais est la seule voie
pour combler ce trou**.

**Trois raisons rendent ce choix plus fort qu'une gestion de charge.** Un produit qui fonctionne bien sur
un territoire est vendable; **un produit à moitié fonctionnel sur dix ne l'est pas**. Le Québec est le
seul territoire où tout existe — identifiant obligatoire, source Piste solide, contrats publics,
financement, permis, mesure de taille. **Et c'est donc le seul endroit où la thèse du produit peut être
vérifiée : si le croisement ne produit pas assez de bons résultats là, il n'en produira pas ailleurs avec
moins de données.**

**L'extensibilité territoriale reste une exigence d'architecture, pas de fonctionnalité.** Ajouter un
territoire doit rester un ajout de sources et d'identifiants externes, jamais une réécriture — **et son
coût augmente avec le volume de dossiers accumulés**.

---

## 2. Vocabulaire

Ces définitions sont contraignantes. Les confondre a déjà produit des erreurs de conception.

**Source** — alimente le moteur de croisement. Point d'**entrée**.

**Intégration** — reçoit les résultats déjà détectés (CRM). Point de **sortie**. Jamais une source,
jamais dans un tableau de sources.

**Cadence d'ingestion** et **cadence de livraison** — deux rythmes distincts, à ne jamais fusionner. La
première est la fréquence à laquelle on interroge une source : hebdomadaire pour le RACJ, deux fois par
mois pour le REQ, annuelle pour les palmarès. Elle est propre à chaque source et suit sa publication. La
seconde est la fréquence à laquelle un abonné reçoit son lot, configurable par palier et par profil, avec
son jour et sa fenêtre.

**Rien n'oblige les deux à coïncider, et il est souhaitable qu'elles diffèrent.** Un signal détecté le
mercredi entre au dossier cumulatif immédiatement et n'est livré que le mardi suivant — ce délai permet
à la corroboration de s'accumuler avant l'envoi, ce qui améliore le résultat au lieu de le retarder.

Le raccourci « le produit tourne une fois par semaine » fusionne les deux et figerait une décision que
personne n'a prise.

**Portail** — mécanisme de **paiement et de gestion d'accès pour les sources payantes**, donc pour des
**entrées**. Rien d'autre. La connexion d'une intégration ne passe jamais par le portail : elle ne coûte
rien à FALKYE, ne demande aucun paiement, et se règle dans la configuration du compte de l'utilisateur.
Les deux mécaniques sont distinctes et ne partagent aucun composant.

**Piste** — source qui ancre le dossier cumulatif d'une entité par un identifiant stable.
Classification **propre à chaque territoire et à chaque famille d'entités, jamais universelle**. *Le SEAO
l'a montré dans une seule source : Piste pour les organismes publics, Réflexion pour les entreprises.
Direction retenue pour lever cette double nature — un registre officiel des entités publiques qui ferait
pour le public ce que le REQ fait pour le privé; décisions D27 à D29 au registre de
`falkye-audit-et-mandat.md`.*

**Piste partiel** — fournit un identifiant stable mais ne couvre pas toutes les entreprises d'un
territoire. Nuance, pas troisième catégorie.

**Réflexion** — enrichit un dossier déjà ancré, ne peut jamais l'ancrer seule.

**Usage du moteur** — ce à quoi le moteur de croisement est appliqué. FALKYE est **un moteur de
croisement appliqué à la prospection d'opportunités d'affaires**. Produit unique, pas catalogue : l'usage
n'est pas une option, c'est ce que le produit est. Le terme sert à nommer la frontière entre le moteur et
sa configuration — voir la charte, section 4, et la contrainte de non-fermeture qui l'accompagne :
**l'entité observée est une variable d'usage, et le moteur ne présume jamais sa nature.**

**Sphère de besoin** — catégorie générique de besoin. Une sphère est **directe** (au moins une source
produit son signal), **dérivée** (alimentée par une règle sur des signaux d'autres sphères), ou **sans
couverture**. Une sphère sans couverture se montre comme telle à la configuration du profil, jamais
offerte comme si elle fonctionnait.

**Signal** — un type d'événement détecté. Registre extensible.

**Identité d'entreprise** — la clé interne du moteur. Dossier cumulatif, corroboration et déduplication
s'y accrochent.

**Identifiant externe** — NEQ, numéro de société fédéral, identifiants provinciaux futurs. Ancre une
identité à un territoire et lui apporte son niveau de vérification. Une identité peut en porter zéro,
un ou plusieurs; une identité sans identifiant externe est valide de plein droit.

**Source de couverture** contre **source d'enrichissement** — voir section 12.2. Le classement se fait
par couple source × sphère, jamais par source seule.

---

## 3. Profil utilisateur et sphères de besoin

### 3.1 Structure du profil

Localisation (ville, région, province, pays), rayon d'action, une ou plusieurs sphères de besoin
offertes, mots-clés optionnels précisant le service, et le « qui » — le type de client visé.

Le champ **type de profil** (fournisseur / client / les deux) existe dès maintenant dans le schéma,
même si seule la mécanique fournisseur est implémentée. Ne pas coder en dur l'hypothèse qu'un
utilisateur est nécessairement un fournisseur.

**Profils multiples simultanés** — plusieurs combinaisons sphère × territoire × « qui » dans un même
compte. Disponible en Radar+.

### 3.2 Lien sphère↔service — plusieurs-à-plusieurs, pondéré

Livré et validé. Un service peut appartenir à plusieurs sphères avec un poids différent pour chacune,
plutôt qu'à une seule. Le score de pertinence tient compte du poids.

### 3.3 La dimension « qui » — client cible

Un même service change de nature selon la clientèle desservie. Le « qui » est déclaré au profil et
détecté, quand c'est possible, sur l'entreprise repérée.

Règle de traitement, à ne pas contourner : **un désaccord confirmé entre le « qui » déclaré et le
« qui » détecté ne devient jamais un malus silencieux.** Il redirige vers le canal « hors profil
déclaré ».

**Décision du 4 septembre 2026 : la redirection a lieu dans l'ensemble de la solution, tous paliers
confondus.** La règle s'applique à tous les profils, puisque tous déclarent un « qui » — une redirection
sans destination fait disparaître le signal, ce qui est précisément le malus silencieux que la règle
interdit.

**Forme du canal.** Tous les paliers disposant désormais d'un tableau de bord (section 9.6), le canal y
est partout une **vue distincte**, jamais mêlée aux opportunités du profil et jamais poussée par
courriel ou webhook par défaut.

**Ce que Radar+ conserve comme différenciation** porte sur ce qu'on peut faire du canal, pas sur son
existence : les alertes composites préconfigurées, la conversion d'un signal hors profil en nouveau
profil de recherche, et le poussage par webhook.

### 3.4 Registre des sphères

Extensible. Chaque sphère porte son type (directe / dérivée / sans couverture), sa règle de dérivation
le cas échéant, sa durée de pertinence par type de signal (section 8.3), et son statut **offert / non
offert**, distinct du fait d'exister au registre.

L'ajout d'une sphère est un engagement à la servir. La question à poser n'est pas « est-ce que ça rentre
dans l'architecture » — la réponse est toujours oui — mais « est-ce qu'on peut la servir la majorité du
temps, et qui va le vérifier ».

**Retirer une sphère de l'offre est une opération normale et documentée**, pas un aveu d'échec.
Précédents : « Gestion d'inventaire », retirée parce que c'était un service précis et non une catégorie
générique; plusieurs personas retirés pour avantage faible ou chevauchement.

---

## 4. Sources

### 4.1 Gabarit du registre

Chaque source, active ou non, existe comme entrée structurée avec le même gabarit :

| Attribut | Contenu |
|---|---|
| Identifiant | Nom court, stable |
| Signal associé | Type de signal produit |
| Type | Piste / Piste partiel / Réflexion |
| Territoire | Territoire d'origine |
| Statut | `actif` / `à développer` / `en pause` / `en quarantaine` / `bloquée` / `en attente d'une action externe` |
| Méthode d'accès | API, données ouvertes, scraping, import manuel |
| Champs pertinents | Liste des champs extraits et conservés |
| Clé naturelle | Déclarée, jamais devinée — varie par source |
| Cadence attendue | Hebdomadaire, mensuelle, trimestrielle, annuelle |
| Saisonnalité | Période creuse déclarée, le cas échéant |
| Règles de calibration | Motif, champ, seuil, tier produit, bruit exclu (section 5.4) |
| Couverture par sphère | Couverture ou enrichissement, **par couple source × sphère** |
| Coût et payeur | Gratuit / payant, et qui paie |
| **Canal légal** | Jeu sous licence ouverte / page web / API / export par accès à l'information |
| **Variante de licence** | Lue sur la fiche du jeu précis, jamais déduite du portail |
| **Clause contractuelle** | Indexation, automatisation, redistribution |
| **robots.txt** | Statut du domaine hôte |
| **Attribution** | Obligation, et lien vers la page de crédits |
| **Vérification légale** | Date, et échéance de revalidation |

Activer ou désactiver une source est une action de configuration, sans toucher au moteur. Le moteur
boucle sur les sources actives, quel qu'en soit le nombre.

### 4.2 Cadre légal

*Le raisonnement complet est dans `falkye-cadre-legal.md`. Ce qui suit est ce qui s'applique aux sources
du produit.*

**Trois règles à ne jamais oublier.** Le statut légal dépend du **canal de diffusion, pas de
l'organisme** — le même fait peut être exploitable via un portail de données ouvertes et interdit via une
page ministérielle. **Le régime par défaut est la réservation totale**, avec autorisation préalable et
redevance possible. Et **une licence ouverte se vérifie sur la fiche du jeu précis** : la licence commune
se décline en six variantes, dont des non commerciales inutilisables.

**« On n'affiche rien » est une défense contre une réclamation en droit d'auteur, jamais contre une
clause contractuelle** — les conditions d'utilisation visent l'**ingestion**, pas l'affichage.

**Cas bloquant vérifié.** Un régulateur interdit nommément d'« indexer dans une base de données » son
contenu. Son bulletin hebdomadaire publie pourtant les placements avec dispense, **complément naturel du
signal financement**. Non ingérable sans entente écrite. *Voie à explorer avant d'abandonner : la même
déclaration est déposée ailleurs, possiblement sous des conditions moins restrictives.*

**L'attribution est une obligation réelle**, y compris quand les données sont intégrées à une base qu'on
possède. D'où une **page de crédits distincte, hors du produit** — jamais dans un tableau de bord, un
libellé, un export ou un message d'erreur. *Conséquence assumée : la liste des sources ouvertes finit
publiée. Ça n'expose pas le moteur de croisement, qui est l'avantage défendable.*

### 4.2bis ⚠️ La source pivot est diffusée sous licence non commerciale

**Vérifié le 4 septembre 2026, lu sur la fiche officielle du jeu.** Le registre des entreprises porte une
licence **non commerciale et à partage identique** — deux clauses distinctes, la seconde souvent
oubliée : *NC* interdit l'exploitation commerciale, *SA* demande que toute œuvre dérivée soit rediffusée
sous la même licence.

**Pourquoi ça compte plus que pour n'importe quelle autre source.** C'est la source Piste du Québec et le
pivot du produit — identification, résolution de nom, vérification du statut légal, enrichissement
d'adresse et de secteur. **Ce n'est pas une source parmi d'autres qu'on pourrait mettre en veilleuse.**

*C'est exactement le cas que la charte prévoyait : la règle avait été écrite en pensant à une source
périphérique, et le cas réel était le pivot (journal, cas 17).*

**Ce que ça ne remet pas en cause :** le développement, la construction et les tests se poursuivent —
l'usage actuel est personnel et non commercial, ce que la licence autorise explicitement.

**Ce que ça bloque :** toute promesse commerciale reposant sur cette source.

**Décision : la demande d'autorisation est reportée, avec un déclencheur plutôt qu'une date.** Le
déclencheur est le **premier engagement commercial, quel qu'il soit** — un abonné payant, une
démonstration à un client potentiel, ou une mise en ligne publique. **Les trois font basculer l'usage, et
c'est plus tôt que « quand le produit sera prêt ».**

**⚠️ Marge à prévoir :** les autorisations gouvernementales annoncent une quinzaine de jours ouvrables.
**La demande doit donc partir avant le déclencheur, pas au moment où il survient** — sinon la réponse
arrive après le premier client.

**Accès au fichier, pour mémoire.** Le fichier n'est pas hébergé sur le portail : le téléchargement
redirige vers le site du registraire, dont le domaine bloque les plages d'adresses infonuagiques — d'où
l'import manuel. Archive de 225 Mo, six fichiers joints par le NEQ, mise à jour bimensuelle. **Les
versions antérieures ne sont pas archivées par le diffuseur** : conserver chaque édition téléchargée est
la seule façon de pouvoir rejouer un diff plus tard.

### 4.3 Sources actives

| Source | Territoire | Signal | Type | Notes |
|---|---|---|---|---|
| REQ | Québec | Identification, nouvel établissement, changement d'adresse | **Piste** | Import manuel; ⚠️ licence CC-BY-NC-SA — voir 4.2bis |
| SEAO | Québec | Contrats publics décrochés | Réflexion | Données ouvertes, JSON/XML |
| Investissement Québec | Québec | Subventions et financement public | Réflexion | PDF annuel, extraction requise |
| EIMT positive | Fédéral | Recrutement, avec nom d'employeur | Réflexion | CSV trimestriel |
| Subventions fédérales | Fédéral | Subventions et contributions | Réflexion | Absorbe DEC, PARI, CanExport, agences régionales |
| Contrats fédéraux | Fédéral | Contrats publics décrochés | Réflexion | Contrats de plus de 10 000 $ |
| Deloitte Fast 50 | Canada | Classement de croissance | Réflexion | Annuel, scraping léger |
| ROB Top Growing | Canada | Classement de croissance | Réflexion | Annuel, scraping léger |
| Permis de construction Laval | Québec | Nouvel établissement, travaux | Réflexion | Données ouvertes municipales |
| Corporations Canada | Fédéral | Changement d'adresse | Piste partiel | **En veilleuse** — n'ajoute rien au Québec |
| Licences Toronto | Ontario | Nouvel établissement | Réflexion | **En veilleuse** — 159 647 lignes, état conservé |
| Licences Vancouver | C.-B. | Nouvel établissement | Réflexion | **En veilleuse** — état conservé |
| Contrats Nouvelle-Écosse | N.-É. | Contrats publics décrochés | Réflexion | **En veilleuse** |

Les quatre sources en veilleuse ont été rebranchées sur le moteur de diff et leur état est conservé —
elles reprennent sans run de référence le jour où la portée s'élargit.

### 4.4 Sources vérifiées, prêtes à construire — priorité québécoise

**1. RACJ — permis de détaillant d'alcool (Québec). Priorité 1, aucun obstacle.** Bars, restaurants,
centres de vinification et de brassage, épiceries, cidreries. Bulk CSV/JSON/XLSX plus API Données
Québec, hebdomadaire, **CC-BY 4.0 confirmé, usage commercial permis, aucune autorisation requise**.
**Livre le NEQ directement.** Champ `Capacite` = proxy de taille d'établissement, rare dans les sources
gratuites. Sphères : restauration (couverture), commerce de détail, agroalimentaire, construction,
immobilier, entretien ménager, SST, sécurité physique, assurance. Tier fort pour une nouvelle
inscription, moyen pour un changement de titulaire. **Calibration** — aucune date de délivrance, diff
hebdomadaire requis : nouveau `NoPermis`/`Neq` = ouverture; `Neq` inchangé et `Titulaire` différent =
changement de propriétaire; **`Capacite` en hausse = agrandissement**.

**`Capacite` est un signal à part entière, pas un attribut de taille — promotion du 5 septembre 2026.**
C'est **la seule mesure directe d'expansion physique de tout le portefeuille** : une capacité qui
augmente est un agrandissement, sans interprétation nécessaire. Toutes les autres sources détectent des
événements qu'il faut interpréter; celle-ci mesure une grandeur. À calibrer comme signal fort, et à
traiter comme tel dans la structure de faits — pas comme une donnée de contexte.

**2. CIPO / IP Horizons (fédéral). Priorité 2, licence commerciale explicite.** Marques, dessins
industriels, brevets. XML ST.96 hebdomadaire, jeux CSV/TXT trimestriels, **SFTP d'automatisation
officiellement documenté**, gratuit. Licence mondiale, libre de redevance, révocable, avec droit de
sous-licence, attribution obligatoire, régie par le droit de l'Ontario. Réflexion — aucun identifiant
d'entreprise, rapprochement par nom et adresse. Sphères : franchisage (une marque est l'actif central
d'un réseau), ingénierie et design industriel, automatisation et robotique, juridique; en second rang
marketing, commerce de détail, agroalimentaire, import/export. Tier fort pour un dépôt de marque ou un
dessin industriel, moyen pour un brevet seul (18 mois de délai de publication). **Calibration** :
exclure les désignations Madrid de titulaires étrangers, exclure les dépôts au nom de cabinets d'agents,
filtrer sur l'adresse du requérant, distinguer un premier dépôt d'un renouvellement.

**3. Registre fédéral des lobbyistes. Priorité 3, licence ouverte sans ambiguïté.** ZIP de CSV plus
dictionnaire de données, licence gouvernementale ouverte du Canada, usage commercial permis. Réflexion.
Sphères : relations publiques (couverture, seul signal trouvé), juridique, planification stratégique,
financement. Chaque enregistrement déclare des **sujets** qui se mappent directement sur les sphères.
Tier moyen — un **nouvel** enregistrement, pas une mise à jour. **Point de conformité obligatoire :** ce
jeu contient des noms de personnes physiques, à exclure **à l'ingestion** comme exclusion universelle,
jamais seulement filtrés au calcul. **Calibration** : ne garder que les nouveaux déclarants et les
nouveaux sujets; exclure les grandes sociétés et associations enregistrées en permanence.

**4. Établissements alimentaires — Ville de Montréal. Priorité 4, complément du RACJ.** CSV/GeoJSON/SHP,
mis à jour aux quelques jours, CC-BY 4.0, commercial explicitement autorisé. Clause à surveiller sans
être bloquante : la Ville proscrit « toute tentative d'identifier une personne, une entreprise » —
vraisemblablement dirigée contre la ré-identification depuis des données anonymisées, mais l'ambiguïté
est réelle. Champ `Statut` : `En traitement` = ouverture récente avec `date_statut`; `Fermé changement
d'exploitant` = changement de propriétaire. Complémentaire au RACJ, pas redondant — couvre les
établissements sans permis d'alcool et fournit une date que le RACJ n'a pas. Portée : agglomération de
Montréal.

**5. OQLF — entreprises certifiées. Autorisation à demander, pas un chantier technique.** Livre le NEQ
directement. Bulk par date de certification, nouveau lot aux deux semaines. **Page ministérielle sans
licence ouverte → autorisation requise avant activation.** Sphères : traduction (couverture, seul signal
direct trouvé), juridique, gestion documentaire (signal le plus proche pour une sphère autrement sans
solution), formation, TI. **Valeur unique : marqueur de seuil d'effectif daté** — 25+ employés confirmés
par un organisme public, ce qu'aucune source active ne fournit. Tier moyen : la certification marque la
**fin** du processus, pas le franchissement du seuil. **Deux listes sœurs** : les entreprises **non
conformes** (besoin aigu, daté, non servi — tier fort comme signal de besoin, faible comme signal de
croissance, probablement la plus actionnable pour cette sphère) et les ententes particulières.

### 4.5 Sources écartées après vérification

**BDC et prêts bancaires privés** — assujettis à la confidentialité, aucune divulgation de prêts
individuels. Porte fermée, pas repoussée.

**Agences de revenu (ARC, Revenu Québec, provinciales)** — principe structurel plutôt que technique :
une agence de revenu existe pour percevoir l'impôt confidentiellement, pas pour publier un registre. Le
registre TPS/TVH exige déjà de connaître le nom et une date, et ses conditions interdisent explicitement
la reproduction commerciale. À ne pas revérifier au cas par cas.

**RPEVL / Commission des transports du Québec** — consultation uniquement par nom d'entreprise. Un
outil de recherche par nom ne peut jamais être une source de découverte. Réserve : utilisable en
**enrichissement** sur une entreprise déjà détectée, comme le mécanisme 2 du RDPRM.

**Registre des licences alimentaires de l'ACIA** — la donnée serait bonne (pancanadienne, liste complète
listable), mais le domaine hôte interdit l'accès automatisé par robots.txt. Deux voies non explorées :
export manuel ponctuel, ou demande de données directe.

**Base de données sur les importateurs canadiens (ISED)** — instantané annuel limité aux entreprises
totalisant 80 % des importations d'un produit, donc biaisé vers les grandes. Exploitable seulement par
diff annuel. Tier faible, à garder en réserve.

**MAPAQ, liste provinciale des permis alimentaires** — trois obstacles : robots.txt bloquant, couverture
incomplète et officiellement volontaire hors restauration et vente au détail, régime de droit d'auteur
par défaut. **Voie de contournement documentée** : la liste complète des titulaires du secteur
transformation a déjà été publiée en XLSX via une demande d'accès à l'information. Socle de référence
ponctuel, jamais un flux de veille.

**Nouveau-Brunswick, Corporate Registry** — interdit explicitement les outils automatisés dans ses
conditions. Blocage légal, pas seulement un coût.

**Guichet-Emplois — en pause depuis le 7 septembre 2026, pour une raison qui n'est plus celle
d'origine.** *État, pas verdict.* Le fichier en vrac ne porte aucun nom d'employeur — vrai, et
**dépassé** : le connecteur va le chercher sur la page de détail de l'offre, et **cette piste
fonctionne** (nom capturé sur une offre réelle, `robots.txt` permissif, `Crawl-delay: 5`). Ce qui bloque
est le **décalage de publication** : le fichier paraît avec environ un mois de retard, les offres
expirent plus vite, donc les identifiants qu'il porte sont déjà morts (HTTP 410) quand on les suit —
15 offres Québec pour 0 signal. **Ni écartée, ni active : en attente d'un réessai qui tranchera**
*(registre, D32)*. Le signal recrutement reste couvert par l'EIMT positive, qui donne le nom.

### 4.5bis Accès réseau — relevé du 4 septembre 2026

L'environnement de développement applique une liste blanche de domaines. Le relevé ci-dessous a été fait
domaine par domaine, en recoupant le code de réponse avec le journal de refus de la passerelle.

**Autorisés et fonctionnels :** Données Québec, le portail fédéral (CKAN), les portails ouverts de
Toronto et Vancouver, la Nouvelle-Écosse, Investissement Québec, Deloitte, le Globe and Mail.

**Autorisé mais instable :** le Guichet-Emplois, dont une requête sur trois expire côté site sans refus
de la passerelle. Problème de robustesse du connecteur — une reprise sur échec —, pas de politique
réseau.

**Autorisé mais refusé par la source :** le registre des entreprises. Le tunnel s'établit, et le refus
vient du pare-feu applicatif du REQ lui-même, cohérent avec le blocage des plages infonuagiques déjà
documenté. **L'import manuel reste donc la seule voie, y compris pour reconstituer l'état après une
perte.**

**Bloqués par la politique de l'organisation**, et c'est le point à traiter :

| Domaine | Ce qu'il bloque |
|---|---|
| `rdprm.gouv.qc.ca` | Le RDPRM en accès direct — le mécanisme 1 par import manuel n'en dépend pas |
| `nominatim.openstreetmap.org` | Le géocodage, donc la validation de la carte géographique |
| `api.theirstack.com` | Le connecteur recrutement, **même une fois la clé fournie** |
| `api.hubapi.com`, `api.pipedrive.com` | La validation des intégrations CRM contre les vrais services |
| `checkout.stripe.com` | La validation du flux de paiement |

**Correction importante à une conclusion antérieure :** plusieurs sources et intégrations étaient
décrites comme « en attente d'une action externe d'Alexandre », en supposant qu'une clé suffirait à les
débloquer. **Ce n'est pas le cas** — le domaine doit d'abord être autorisé. Fournir la clé TheirStack
sans élargir la liste ne débloquerait rien. L'ordre est : autoriser le domaine, puis fournir l'accès,
puis valider.

### 4.6 Sources en attente d'une action externe

Ces sources ne sont ni défaillantes ni non implémentées. Elles attendent une manœuvre non technique que
le code ne peut pas déclencher. **Le registre nomme l'action attendue**, pas seulement l'état — « en
attente d'une clé API » et « en attente d'une autorisation gouvernementale » ne se résolvent ni de la
même façon ni dans les mêmes délais. Chacune porte une échéance de décision, faute de quoi elle sort du
suivi comme ce fut le cas pour Crunchbase.

| Source | Action attendue | Effet |
|---|---|---|
| TheirStack | Créer un compte, fournir la clé API | Statut réel `a_developper`; blocage réseau **et** absence de clé |
| RDPRM mécanisme 1 | ~~Trancher le mécanisme~~ — **fait, actif depuis le 2026-08-31** | Import manuel, 11 $/recherche. N'est plus un stub |
| RDPRM mécanisme 2 | Examiner le format réel d'un document | Configuration `champs_pertinents` impossible à écrire |
| OQLF | Demander l'autorisation gouvernementale | Sphère traduction sans couverture |
| Crunchbase | Trancher la décision budgétaire (49-99 $ US/mois) | Angle mort du capital de risque privé |
| HubSpot / Pipedrive | Fournir des jetons réels | Intégration validée contre des mocks seulement |
| Stripe | Configurer un compte, fournir les clés | Flux de paiement non validé |
| Clé API Anthropic | Fournir `FALKYE_ANTHROPIC_API_KEY` | Assistance IA niveau 2 vendue mais inopérante |
| Géocodage Nominatim | Validation réseau en conditions réelles | Carte géographique non validée |

---

## 5. Ingestion — de la donnée brute au signal

### 5.1 Deux familles de sources

**Sources de type événement** — chaque enregistrement porte sa propre date. Le signal est dans la
donnée.

**Sources de type instantané** — aucune date d'événement. Le signal **naît de la comparaison entre deux
états successifs**. Le RACJ, les établissements de Montréal, les licences municipales et la plupart des
registres de permis sont de ce type.

Conséquence à ne pas sous-estimer : **une source de type instantané qui tourne sans conserver son état
complet ne perd pas du temps de développement, elle perd des événements définitivement.** Ce qui s'est
produit entre deux exécutions non conservées n'existera jamais nulle part.

### 5.2 Conservation de l'état d'une source et moteur de diff

État courant par source, mis à jour à chaque exécution réussie — pas un historique de copies complètes.
Par ligne : clé naturelle, empreinte des champs pertinents, données normalisées, première apparition,
dernière observation. Le fichier brut des dernières exécutions est archivé pour inspection.

**La clé naturelle est déclarée par source, jamais devinée.** Elle varie franchement : `NoPermis` et
`Neq` au RACJ, `business_id` à Montréal, aucune en Nouvelle-Écosse — où une clé composite nom + adresse
+ ville est fragile par nature, un établissement renommé ressemblant à une fermeture suivie d'une
ouverture. Limite à documenter, pas à masquer.

**L'empreinte porte uniquement les champs pertinents**, jamais la ligne entière, sans quoi un changement
cosmétique produit une fausse modification.

**Dédoublonnage déterministe.** Certaines sources violent leur propre clé naturelle — environ 0,5 % des
lignes de Toronto. La règle de sélection est une fonction pure du contenu, jamais de la position dans le
fichier, sans quoi le résultat dépend de l'ordre d'arrivée et produit de fausses modifications d'une
semaine à l'autre. Doublons identiques et divergents sont comptés séparément, et le taux est journalisé
à chaque exécution comme indicateur de santé de la donnée d'entrée.

**Run de référence.** La première exécution réussie n'a rien à quoi se comparer : toutes ses lignes sont
des apparitions. Elle **amorce l'état et n'émet aucun signal**, et ne déclenche pas la quarantaine.

**La règle est portée par le moteur, jamais par la discipline de chaque connecteur — précision du
4 septembre 2026.** Un cas réel l'a montré : le moteur générique a bien émis zéro écart au premier run de
Toronto, mais le filtre propre à ce connecteur portait **sa propre notion de premier scan**, fondée sur un
miroir qui contenait déjà de l'historique, et il a émis des milliers de signaux réels. Ce n'étaient pas
de faux signaux — mais rien n'empêchait qu'ils partent.

**Aucun connecteur ne doit avoir à vérifier lui-même qu'il est en run de référence.** Le moteur refuse
l'émission, quelle que soit la source du signal. Deux connecteurs respectaient la règle uniquement parce
que leurs compteurs y étaient câblés par hasard — une conformité accidentelle n'est pas une garantie.

**Corollaire pour toute migration :** quand un connecteur possède déjà un état accumulé, migrer cet état
vers le magasin générique fait partie du rebranchement. Laisser le moteur amorcer à vide pendant qu'un
miroir porte de l'historique crée deux couches désynchronisées au premier appel.

**Sortie du diff : trois ensembles jamais fusionnés** — apparitions, disparitions, modifications, ces
dernières avec la liste des champs changés. Une hausse de `Capacite` et un code postal reformaté n'ont
pas la même valeur.

### 5.3 Quarantaine

Quand un diff dépasse le plausible, **rien n'est publié, l'état précédent reste intact**, l'exécution
attend une révision humaine.

- **Deux seuils à franchir ensemble**, un pourcentage et un nombre absolu de lignes. Le pourcentage seul
  mettrait en quarantaine les petites sources sur du bruit; l'absolu seul ne verrait rien sur les
  grosses.
- **Seuils distincts par type d'écart.** Une disparition massive est plus suspecte qu'une apparition
  massive dans un registre de licences : elle signale généralement un extrait tronqué.
- **Seuils resserrés de moitié** tant qu'une source a moins de cinq exécutions non-référence
  d'historique — jamais relâchés. Sans norme, la prudence est de bloquer plus facilement.
- **Détection de changement de schéma** : colonne pertinente retirée ou type modifié → quarantaine
  immédiate, quel que soit le volume. Colonne ajoutée → avertissement seulement. Échec de lecture
  au-delà d'un seuil → quarantaine, sans interrompre les autres sources.
- **Amplitude journalisée à chaque exécution**, même très en dessous du seuil. C'est la base de la
  calibration future et de la norme de volume; sans elle, le seuil restera incalculable indéfiniment.
- **Proposition de seuil par source** une fois assez de recul, **jamais d'application automatique** — un
  seuil qui s'ajuste seul s'élargit jusqu'à ne plus rien attraper. Les exécutions mises en quarantaine
  et **rejetées** sont exclues du calcul; celles **acceptées** y entrent, l'amplitude ayant été réelle.
- **Levée explicite et journalisée**, réservée au mode opérateur : accepter le diff (l'état se met à
  jour) ou rejeter l'exécution (l'état précédent est conservé).

**Un run en quarantaine n'entre nulle part** — aucune donnée ne rejoint le dossier cumulatif, même
partiellement, même pour une entreprise dont un autre signal sain existe. Il est traité comme s'il
n'avait pas eu lieu. Ce qui a été publié avant reste publié, et **aucun recalcul rétroactif de
corroboration** n'inclut ses données.

**Deux quarantaines dans la même exécution** sont deux incidents indépendants, mais le cumul déclenche
une alerte distincte : deux diffuseurs qui changent de format le même jour est improbable, une cause
commune de notre côté l'est beaucoup moins.

### 5.4 Calibration — forme commune

Aucune source ne s'active sans une règle qui distingue le vrai signal du bruit administratif. Cette
règle est **déclarée au registre selon un catalogue de motifs**, pas codée à la main dans le
connecteur — sans quoi les règles ne sont ni comparables, ni auditables, ni testables côte à côte, et
chaque nouvelle source réinvente sa calibration.

Motifs : **apparition** d'un enregistrement absent de l'état précédent; **changement de valeur** au-delà
d'un seuil; **franchissement de palier**; **répétition** sur une fenêtre; **absence attendue**.

Chaque règle déclare son motif, le champ visé, son seuil, le tier de confiance produit, et ce qu'elle
exclut explicitement comme bruit.

**Le tier de confiance est porté par le couple type de signal × sphère** *(8.1)*, jamais par le signal
seul : une même règle peut produire un signal fort pour une sphère et faible pour une autre, et une
valeur unique mentirait à l'une des deux. **Ses critères n'existent pas encore, et c'est délibéré** —
décider si un signal est réel et fort est l'acte de lecture que ce chantier construit, pas une
définition à rédiger d'avance *(registre, D34)*.

Exemples déjà établis : au RDPRM, distinguer une garantie d'expansion d'un refinancement de routine; au
REQ, distinguer un nouvel établissement d'une mise à jour administrative — la toute première
immatriculation n'est jamais un signal, une entreprise qui vient de naître n'est pas une entreprise
**en** croissance; aux licences municipales, distinguer un nouvel établissement d'une entreprise
existante d'un démarrage ou d'un renouvellement, par vérification croisée.

### 5.5 Santé de source

**Trois issues d'exécution distinctes, jamais un booléen** : échec technique (donnée jamais obtenue),
mise en quarantaine (obtenue, lue, volontairement non publiée), réussite publiée. « Dernière exécution
réussie » désigne la troisième.

**Norme de volume apprise par source, sur sa propre cadence déclarée**, jamais sur une moyenne globale —
le RACJ bouge chaque semaine, un palmarès annuel publie une fois par an et onze mois de silence y sont
normaux. Alerte **dans les deux sens** : un volume anormalement bas indique souvent un connecteur qui se
dégrade sans cesser de fonctionner, le cas le moins visible.

**États distinguables — cette liste est la référence du corpus**, et aucun autre document n'en recopie
le compte. Plusieurs causes produisent le même symptôme observable, rien :
saine et territoire calme; saine en période creuse déclarée; non implémentée; **en attente d'une action
externe** (section 4.6); en quarantaine; défaillante. À quoi s'ajoutent `bloquée` (légalement) et
« jamais validée en réel ».

**⚠️ La quarantaine est déclarée deux fois, dans deux catégories différentes** — comme l'une des trois
issues d'exécution ci-dessus, et comme l'un des états distinguables. **Un *run* mis en quarantaine et une
*source* en état de quarantaine ne sont pas la même chose.** Décision ouverte D11 au registre de l'audit,
à trancher avant d'écrire la taxonomie; le mandat du chantier 2 porte la même mention. **Trois documents
donnent aujourd'hui trois comptes de ces états** — un registre extensible ne dispense pas de savoir
combien il en contient à une date donnée.

**Un statut d'exécution ne se propage pas automatiquement en état de santé.** Le statut `interrompue`,
retenu le 8 septembre — *on ne sait pas pourquoi l'exécution n'a pas fini, seulement qu'elle n'a pas pu
continuer*, distinct de `erreur` où l'échec a été vu et écrit — **ne compte ni dans la norme de volume,
ni dans l'escalade de quarantaine, ni dans « dernière exécution réussie »**. Un quota épuisé interrompt
le cycle sans qu'aucune source ne soit malade. *C'est la même règle qu'à la section 9.7 : le taux de
rejet se calcule sur la dimension 1 seule, et toute contamination fausse la seule boucle de correction
disponible.*

**Ce qu'une exécution a coûté fait partie de sa santé.** On mesurait la durée, la mémoire et les
écritures, jamais les lectures — **un cycle peut être rapide, léger, huit sources sur huit en succès, et
avoir consommé le quota du mois.** Deux grandeurs distinctes, jamais sous un même nom :
`nb_lignes_source` (les lignes lues du fichier source) et `nb_lignes_lues_base` (les lignes facturées par
la base), ventilées par cycle, par source et par chemin de résolution.

**Rétraction.** Une source muette ne pose pas de problème rétroactif. Une source ayant produit des
données partiellement erronées restées sous le seuil de quarantaine, oui : les faits issus de
l'exécution invalidée sont **marqués**, le score est recalculé sans eux, et **rien n'est supprimé** — un
prospect déjà livré peut avoir été contacté, et le retirer ferait perdre à l'utilisateur la trace d'une
action qu'il a posée. Ce qui n'a pas encore été livré ne part pas.

**Corroboration.** Celle déjà calculée tient. Aucun nouveau bonus ne se calcule à partir d'une source en
état dégradé — la corroboration suppose deux observations indépendantes fiables.

**Fenêtre de rattrapage.** `since` se dérive de la dernière exécution réussie, avec la fenêtre fixe
comme plancher et non comme valeur, plus un plafond par source pour qu'une reprise après interruption
ne demande pas un historique que la source ne conserve pas. Là où l'historique reste interrogeable, ce
qui a été manqué se rattrape; là où la source n'expose qu'une fenêtre récente, seule la correction
empêche que ça se reproduise. Une reprise longue ne s'évalue pas avec les mêmes seuils de quarantaine
qu'une exécution normale.

---

## 6. Identité d'entreprise et appariement

### 6.1 Identité interne, identifiants externes

**La clé du moteur est l'identité interne.** Dossier cumulatif, corroboration et déduplication s'y
accrochent. Les identifiants externes — NEQ, numéro de société fédéral, identifiant d'entité publique, identifiants
provinciaux futurs — sont rattachés à cette identité, chacun avec **son territoire, sa famille
d'entités**, sa source et sa date de résolution. *La famille est la seconde dimension qui désigne le
pivot : le territoire seul ne suffit pas — voir §7.2 et les décisions D27 à D29.*

**Le NEQ garde tout son rôle au Québec.** Le REQ y est obligatoire pour toute entreprise, il mérite
d'être la source Piste du territoire, et une identité qui en porte un est mieux ancrée qu'une identité
qui n'en porte pas. Ce qui change, c'est qu'une identité **sans** identifiant externe devient valide de
plein droit plutôt qu'un cas dégradé.

**Critère de non-régression** : une entreprise québécoise avec NEQ doit produire exactement les mêmes
résultats qu'avant la séparation. Ce n'est pas un effet secondaire acceptable, c'est une condition.

Pourquoi maintenant : le coût de cette séparation est proportionnel au volume de dossiers déjà
accumulés sur la mauvaise clé, et il augmente chaque semaine. Tant qu'un seul territoire est ancré, la
confusion ne se voit pas.

### 6.2 Vérifications de base — par territoire

Trois vérifications avant toute présentation : statut légal, signe d'activité, cohérence d'identité.

**Le niveau atteignable est déclaré par territoire**, parce qu'une vérification passant par un
identifiant qui n'existe pas ailleurs est inapplicable. Trois niveaux : vérifié contre un registre
d'État, vérifié partiellement, non vérifiable sur ce territoire. Le registre déclare, par territoire,
quelle vérification tient lieu de contrôle d'existence légale.

Un prospect non vérifiable est présenté avec une **confiance plafonnée** plutôt qu'exclu — décision
assumée, reflétée dans le score et non dans un avertissement affiché. Dans la portée québécoise
actuelle, ce cas est marginal : le NEQ existe pour toute entreprise opérant au Québec.

### 6.3 Confiance d'appariement — troisième axe

Le problème n'est pas théorique. La base réelle contenait 76 paires de doublons non reconnues; une
fusion erronée a eu lieu entre deux compagnies à numéro légalement distinctes, restaurée depuis une
sauvegarde; 20 candidats de fusion restent en attente d'examen.

Correction livrée : appariement flou restreint aux entreprises sans NEQ, jamais contre une entreprise
déjà résolue au REQ; fusion automatique au-dessus de 95, bonifiée si la ville concorde; journalisation
comme candidat entre 90 et 95, jamais de fusion silencieuse dans cette zone; **comparaison floue entre
deux compagnies à numéro interdite structurellement**, ces noms étant génériques par nature.

Ce qui manque : l'incertitude est résolue **au moment de la fusion**, puis oubliée. Le dossier ne porte
plus trace du caractère probabiliste du lien, les signaux s'y accumulent, la corroboration additionne,
et la confiance monte sans justification.

**Le troisième axe corrige ça.** L'identité porte un score, hérité du maillon le plus faible de son
historique d'appariement, **jamais fusionné en moyenne** avec les deux autres. Il **plafonne** la
confiance du signal au lieu de s'y additionner. Sous un seuil, le signal reste une réflexion non
promue, n'entre pas au dossier comme fait établi, et ne déclenche aucune notification.

**L'adresse devient l'axe d'appariement principal** — code postal plus numéro civique est nettement plus
discriminant qu'une raison sociale, et presque toutes les sources en fournissent une. Le nom devient
corroborateur.

**Le RACJ et l'OQLF servent de ponts d'apprentissage.** Ce sont les deux seules sources à livrer
simultanément un NEQ, un nom d'enseigne et une adresse. Chaque ligne est une paire réutilisable pour
apparier les sources sans NEQ. C'est ce qui règle un problème autrement insoluble : le REQ porte la
raison sociale (« 9138-3471 Québec inc. ») pendant que les permis portent le nom d'enseigne (« Maison
La joie d'y vivre »), deux univers de chaînes qui ne se rejoignent jamais par similarité textuelle.

### 6.4 Complétude — localisation et secteur

Plusieurs sources ne fournissent ni adresse complète ni secteur — Investissement Québec, les
subventions fédérales et le SEAO donnent souvent un nom et un montant. Chaque source capture ces champs
quand ils existent, et à défaut le système les résout via le REQ après identification par nom. Sans
cette étape, une bonne partie des entreprises détectées ne pourraient être ni localisées ni classées,
ce qui viderait la notification de sa valeur.

**Limite d'agrégation documentée** : le secteur du REQ est un champ à faible granularité — 211 valeurs
distinctes sur 311 notifications réelles. Un regroupement grossier en 11 catégories par mots-clés
couvre environ 75 % des cas, distinct de « non précisé », le libellé brut restant toujours accessible.
La normalisation de ce champ reste un chantier ouvert et conditionne les tableaux de bord agrégés.

---

## 7. Signaux

### 7.1 Registre extensible

Les cinq signaux ci-dessous sont les catégories identifiées à ce jour, pas une limite structurelle — le
signal 4 a été ajouté après les trois premiers. Un nouveau type s'ajoute avec son gabarit — nom, sources
associées, critères de confiance, sphères probables, icône — sans renuméroter les existants.

### 7.2 Les cinq signaux

**Signal 1 — Classements de croissance. Source de corroboration, pas de détection** — reclassement du
5 septembre 2026. Une entreprise qui figure à un palmarès est déjà connue, déjà sollicitée, et sa
croissance date de l'année précédente : c'est du signal public et tardif, exactement ce que l'avantage
défendable prétend éviter. Sa valeur réelle est de **confirmer** une croissance détectée ailleurs, jamais
de la découvrir. À ne pas présenter comme un détecteur dans l'argumentaire.

Deloitte Fast 50, Growth 500, ROB Top Growing. Pages web publiques, scraping léger. Champs : nom, secteur, taux de croissance, rang, année, région, site web,
effectif si mentionné.

**Signal 2 — Financement et expansion.** RDPRM (deux mécanismes distincts, section 12.4), Investissement
Québec (PDF annuel), subventions fédérales (absorbe DEC, PARI, CanExport et les agences régionales —
des filtres sur une même source, pas des sources séparées). Le RDPRM demande un filtrage serré :
uniquement les garanties sur biens d'entreprise à valeur significative, jamais les biens personnels.

**Signal 3 — Recrutement.** Deux mécanismes distincts. Le **volume** (plusieurs postes simultanés) et le
**signal qualitatif par titre de poste**, qui peut à lui seul justifier une notification avec un seul
poste — un titre orienté transformation ou implantation annonce une intention de changement précise,
pas seulement un besoin de main-d'œuvre. Les mots-clés du profil utilisateur servent à analyser ces
titres, ce qui donne une correspondance plus fine que la table générique signal → sphère.

**⚠️ Ce signal n'a pas de source générale aujourd'hui.** La seule source active est l'EIMT positive, dont
la portée est sectorielle — voir ci-dessous. **Ne jamais présenter le recrutement comme un signal couvert
tant que TheirStack n'est pas branché.**

**Signal 3bis — Recrutement en secteurs à main-d'œuvre étrangère temporaire.** C'est le libellé exact de
ce que l'EIMT positive couvre : les employeurs ayant obtenu une évaluation d'impact favorable pour
embaucher des travailleurs étrangers temporaires. Concentration marquée en **restauration,
agriculture et agroalimentaire, transformation manufacturière**.

**Ce n'est pas un signal de recrutement dégradé, c'est un signal sectoriel précis** — et pour les
utilisateurs qui servent ces secteurs, il est excellent : le nom de l'employeur est fourni, la démarche
est coûteuse pour l'entreprise donc elle traduit un besoin réel, et elle annonce une croissance
d'effectifs planifiée plutôt que supposée. À présenter comme tel dans les sphères restauration,
agroalimentaire, production et SST, jamais comme couverture générale du recrutement.

**Signal 4 — Registre et changements corporatifs.** REQ (nouvel établissement secondaire, changement
d'adresse, **franchissement de bande d'effectifs**), permis de construction municipaux, licences
d'affaires municipales.

**Le franchissement de bande d'effectifs est le seul signal du portefeuille qui atteigne les entreprises
sans empreinte administrative** — une firme de services qui passe de 10-24 à 25-49 employés le déclare,
qu'elle ait ou non un permis. Il est déjà dans le fichier ingéré et ne demande aucun connecteur nouveau.
Calibration : le motif est un **franchissement de palier** vers le haut, jamais une simple mise à jour
déclarative. Tier moyen — la déclaration est annuelle et déclarative, donc le signal est tardif et
imprécis, mais tardif vaut mieux qu'absent, et le croisement avec un signal frais lui rend sa valeur. Ni le REQ ni Corporations
Canada ne font de découverte instantanée : les deux exigent qu'une entreprise soit déjà connue d'un
import précédent pour qu'un changement soit détecté par différence. Une correction de calibration a
d'ailleurs dû retirer un traitement erroné qui comptait toute nouvelle incorporation comme un signal —
environ 695 000 faux signaux au premier import.

**Signal 5 — Contrats publics décrochés.** SEAO, contrats fédéraux de plus de 10 000 $. Le but n'est pas
d'éviter les appels d'offres comme canal, mais de couvrir aussi les entreprises en croissance qui n'y
apparaissent jamais — surtout les PME.

### Arrêt à la première donnée réelle — 6 septembre 2026

*Application de la sixième étape du diagnostic (charte, section 9), sur 4 704 avis.*

**La source décrit deux familles d'entités, et le produit n'en voyait qu'une.** L'identifiant de
l'organisme acheteur est présent à **100 %** — 641 organismes distincts sur une semaine, ancrage direct
sans appariement par nom. Celui du fournisseur est présent aussi, mais interne à la source, **jamais un
NEQ**. D'où le contraste : 56 % d'ambiguïté sur les fournisseurs, zéro sur les acheteurs.

**Le SEAO est donc Piste pour les organismes publics, Réflexion pour les entreprises** — dans la même
source. *Nuance : l'identifiant d'organisme est un **ancrage de source, pas de territoire**. Suffisant
pour un dossier cumulatif; insuffisant pour recouper avec une autre source.*

**⚠️ Direction retenue le 9 septembre 2026 — lever la double nature plutôt que la gérer.** Plutôt que de
laisser une source porter deux types, **s'appuyer sur un registre officiel des entités publiques** qui
fournirait l'identifiant unique comme le REQ fournit le NEQ. Le SEAO redeviendrait alors **Réflexion pour
les deux familles**, et la règle deviendrait une propriété du type d'entité, pas de la source : *entité
publique → registre des organismes publics; entité privée → REQ.*

**Ce que ça consolide.** La séparation public / privé décidée plus bas reposait sur les seuils, le délai,
le cycle de vente et l'identifiant. **L'identifiant en devient le premier argument** : ce ne sont pas
deux vues d'une même population, ce sont deux populations avec chacune son pivot — donc classables et
dédoublonnables séparément. *Le déversoir redouté pour le tableau public venait en partie d'un ancrage
bancal.*

**Trois décisions au registre de `falkye-audit-et-mandat.md` avant la conception de la clé du
chantier 3 : D27** trouver le registre, **D28** la règle de classement d'une entité — avec sa réponse par
défaut pour les cas mixtes comme une société d'État ou un organisme paramunicipal —, **D29** lequel des
deux identifiants fait foi pour la vérification du statut légal quand une entité porte les deux.

**Trois champs présents depuis le début et non exploités.** *L'objet du contrat*, à 100 %, en français
clair. *Une classification normalisée*, sur 93 % des avis — **c'est l'antidote direct au résumé vide** :
les signaux portaient tous la même sphère parce que rien ne permettait de les distinguer, et cette
nomenclature les distingue déjà. **Elle est la condition mesurable qui manquait** : un code n'est pas un
autre, et cette différence est vérifiable plutôt qu'interprétée. *La méthode d'attribution*, qui sépare
le gré à gré — 45 % des avis — de l'appel d'offres public, et *le nombre de soumissionnaires*, mesure de
concurrence.

**Ce que le donneur d'ouvrage est, et ce qu'il n'est pas.** La contrainte ne vient pas de son statut
public mais **des seuils d'appel d'offres** : au-delà d'un montant il doit passer par un processus
public, en dessous le gré à gré est permis. Trois lectures, dans l'ordre de ce qu'elles valent.

*Indicateur d'activité, et c'est probablement le rôle principal.* Un organisme qui octroie un contrat de
construction annonce un chantier — et c'est **l'entrepreneur retenu** qui achètera la signalisation,
l'équipement, la surveillance. Le donneur enrichit alors la lecture du signal sur le fournisseur plutôt
que de devenir une cible.

*Cible directe, mais seulement sous les seuils*, et pour ce qui n'y est pas déjà soumis.

*Entité à trajectoire propre.* Répéter des contrats d'une même nature, c'est mener un programme; un
premier contrat d'une nature nouvelle amorce quelque chose.

**Deux tableaux séparés, public et privé — décision du 6 septembre 2026.** Pas un filtre d'affichage :
**deux jeux de règles**. Les seuils, le délai avant d'agir, le cycle de vente et l'identifiant diffèrent.
*Pas de tableau unifié* — deux lignes côte à côte dans une liste triée sous-entendent qu'elles sont
comparables, et un AAA public ne veut pas dire la même chose qu'un AAA privé; une distinction visuelle
masquerait le problème sans le régler. *Ce que ça règle :* un utilisateur qui ne sert pas le public
écarte tout un pan de bruit sans rien configurer, et **un utilisateur qui ne sert que le public existe**.
*Réserve :* le tableau public serait un déversoir tant que la règle des seuils n'est pas écrite.

**Rien n'est construit là-dessus : c'est le chantier 22.**

**Calibration resserrée le 5 septembre 2026.** Décrocher un contrat public signale une **capacité**, pas
une croissance : une entreprise peut en décrocher chaque année sans grandir d'un employé. Le signal n'est
donc réel que dans deux cas — un **premier** contrat, ou un contrat **disproportionné par rapport à la
taille déclarée**, ce second cas devenant calculable dès que la bande d'effectifs est exploitée. Sans
cette règle, la source produit du bruit régulier sur les mêmes entreprises.

### 7.3 Correspondance signal → sphères

Table plusieurs-à-plusieurs, point de départ à affiner avec l'usage, jamais figée. Le croisement des
sphères multiples d'un même signal est explicitement recherché : une même source sert souvent plusieurs
sphères, et une source à large portée cross-sphère vaut mieux qu'une source hyper-spécifique.

### 7.4 Diagnostic — de la sphère vers le signal

La méthode à quatre étapes — quoi, qui, territoire, source — se lit toujours du service vers la source.
Elle a un angle mort : elle ne repose jamais la question sur les sources **déjà actives**, et jamais au
niveau du **champ**.

**Cinquième étape, avant de conclure qu'une sphère n'a pas de source :** parcourir l'inventaire des
champs de toutes les sources actives et chercher ce qui, au niveau du champ, sert déjà cette sphère.

Cas qui a révélé le manque : la sphère assurance, déclarée sans source, alors que six champs déjà
captés portent le besoin — capacité d'accueil, valeur de travaux, nouvel établissement, nature du bien
en garantie, volume d'embauche, valeur de contrat. Ce n'était pas « aucune source », c'était « aucune
source **seule** », c'est-à-dire la thèse même du produit.

**Garde-fou obligatoire :** un lien champ → sphère proposé n'est jamais activé sur la seule foi de la
proposition, qu'elle vienne d'une personne ou d'un modèle. Il doit être **réfuté ou confirmé par
l'historique réel** — sans volume, ou avec tant de volume qu'il ne distingue rien, il est rejeté. Sans
cette règle, la cinquième étape devient une machine à fabriquer des liens plausibles.

**Journaliser les diagnostics négatifs** autant que les positifs : « cherché, rien trouvé, à telle date,
voici où » évite de refaire la même recherche infructueuse et fait décroître le coût du diagnostic.

### 7.5 Signal par absence et trajectoire

Deux capacités que seule la mémoire dans le temps rend possibles, et que personne ne peut reproduire en
achetant les mêmes données.

**Le signal par absence** — l'absence d'un signal normalement attendu à un stade plus avancé est
elle-même un indicateur. Croissance d'effectifs et nouvel établissement, **sans** financement public ni
classement encore visible, signale une traction précoce avant qu'elle soit publique. Un outil de
recherche ne peut pas exprimer une absence : il faut connaître l'ensemble de ce qui aurait dû
apparaître, et l'avoir gardé.

**La trajectoire** — trois signaux en deux mois valent mieux que trois signaux en deux ans, à confiance
égale. L'accélération ne se déduit pas d'un instantané.

**Risque propre au signal par absence, qui n'existe pour aucun autre :** une absence causée par une
source en quarantaine ou défaillante produirait un faux positif. Ce mécanisme dépend directement de la
conservation d'état et de la santé de source.

---

## 7bis. Angles morts du portefeuille de sources

*Critique du 5 septembre 2026. **Les correctifs qui en découlent sont appliqués aux signaux ci-dessus** — bande d'effectifs promue en signal, capacité du RACJ promue en signal, calibration resserrée des contrats publics, palmarès reclassés en corroboration, EIMT relibellée. Le détail et les pistes de sources sont dans `falkye-recommandations-sources.md`. Ne restent ici que les trois constats qui n'ont pas de correctif.*

**Le biais de sélection, et c'est le plus structurant.** Presque toutes les sources actives détectent des événements qu'une entreprise **doit** déclarer — permis, contrats, subventions, registres. Les entreprises réglementées et subventionnées sont donc surreprésentées, et **une PME de services professionnels qui double son chiffre d'affaires sans permis ni contrat public est presque invisible.**

Ce n'est pas un défaut à corriger mais un fait qui détermine **quel type d'entreprise le produit trouve**, donc à quel fournisseur il est réellement utile. **À dire honnêtement au moment de vendre, plutôt qu'à laisser découvrir.**

**Le NEQ porte quatre fonctions, deux seulement en ont besoin.** La vérification du statut légal et l'exclusion des radiées exigent un identifiant officiel. La déduplication et la corroboration ont seulement besoin qu'un identifiant existe. **Question ouverte : la vérification du statut légal vaut-elle ce qu'elle coûte?** Mesurable une fois la boucle en marche, en comptant les prospects qu'elle écarte. Si le taux est négligeable, la contrainte pourrait être assouplie hors Québec.

**La prémisse centrale n'a jamais été testée : un signal de croissance annonce-t-il vraiment un besoin de service?** Un nouvel établissement annonce-t-il un besoin d'entretien dans les mois qui suivent, ou l'entreprise avait-elle réglé ça avant d'ouvrir? **La réponse décide de la valeur du produit** et ne se trouve que chez de vrais utilisateurs — c'est ce que le taux de rejet du chantier 13 mesurera.

---

## 8. Scores, seuil et durée de pertinence

### 8.1 Trois axes indépendants

**Confiance** — le signal est-il réel et fort? Faible / Moyen / Élevé.
**Pertinence** — correspond-il à CE profil? A Repéré / AA Aligné / AAA Sur mesure.
**Confiance d'appariement** — est-il rattaché à la bonne entreprise? Plafonne les deux autres.

Combinés en matrice, **jamais fusionnés en une moyenne**. La règle vaut pour N axes : si un quatrième
s'impose, il s'ajoute sans que la séparation devienne négociable.

**⚠️ Trois axes ne veut pas dire trois objets de même nature.** La Confiance et la Confiance
d'appariement sont des **instruments internes** — le moteur les calcule pour décider, leur valeur n'est
jamais affichée. La Pertinence est une **finalité présentée** — c'est le dernier mot du produit au
client. **Les règles qui s'y appliquent ne sont pas les mêmes**, et cette section a longtemps laissé
croire le contraire. *Découpe des trois natures : charte, section 16.*

**La Confiance est portée par le couple type de signal × sphère, jamais par le signal seul.**
*Tranché le 11 septembre 2026.* Une non-conformité au processus de francisation est un signal **fort de
besoin** et **faible de croissance** : ce n'est pas une ambiguïté à lever, **c'est ce que le fait dit
vraiment**, et forcer une valeur unique reviendrait à mentir à l'une des deux sphères. *Le corpus
penchait déjà dans ce sens — la durée de pertinence obéit à la même règle (8.3) avec le même
raisonnement, et deux propriétés du même objet ne peuvent pas obéir à des règles opposées.*

**Ce que ça ne change pas.** La séparation d'avec la Pertinence reste entière. **Ce n'est pas la
Pertinence qui déborde sur la Confiance : c'est que lire un signal, c'est déjà le lire pour
quelqu'un.** La Confiance n'est pas une propriété du signal, c'est une propriété de **sa lecture dans
une sphère**; la Pertinence mesure l'alignement au profil de l'utilisateur. Deux questions distinctes,
qui ont seulement en commun de n'avoir aucune réponse hors d'une sphère.

### 8.2 Corroboration et normalisation

La corroboration multi-signaux monte la confiance. Elle suppose deux observations **indépendantes** et
**fiables** — un même champ servant deux sphères ne peut pas se corroborer lui-même.

**Un signal ne veut rien dire sans sa base de comparaison.** Cinq embauches chez une entreprise de dix
personnes et chez une entreprise de cinq cents n'ont pas le même sens. Sans normalisation par la taille
et par le secteur, tout signal de volume favorise mécaniquement les grandes entreprises — celles qui ne
sont pas la clientèle visée. Le miroir REQ complet sert de dénominateur pour établir ce qu'est un
rythme normal.

**Taille à trois niveaux de fiabilité, jamais fusionnés en un chiffre** : mesurée (capacité RACJ, seuil
25+ de l'OQLF, à leur date), déclarée (bande d'effectifs du registre), estimée (signaux d'embauche
cumulés). Chaque niveau porte sa provenance et sa date.

### 8.3 Durée de pertinence — par couple type de signal × sphère

La fenêtre de pertinence varie fortement. Un nouvel établissement intéresse un entrepreneur en
entretien ménager deux ou trois mois; un dépôt de marque intéresse un conseiller en franchisage près
d'un an; une vague d'embauche se refroidit en quelques semaines.

**Déclarée au registre, par couple, avec une valeur par défaut.** Elle module la fraîcheur dans le grade
et détermine la profondeur d'antériorité à l'inscription.

**Active dès Écho, identique dans tous les plans, non configurable par l'utilisateur.** Ce n'est pas une
fonctionnalité mais une correction de justesse — un fait sur le signal, pas une préférence. Livrer des
résultats délibérément moins exacts au palier d'entrée contredirait la règle de placement. Et un
utilisateur n'a aucun moyen de savoir combien de temps un signal reste pertinent dans sa sphère : c'est
une connaissance du produit, pas la sienne.

Un même signal servant deux sphères aux durées différentes peut être frais pour un utilisateur et
périmé pour un autre au même instant. La durée est portée par le couple, jamais par le signal seul.

### 8.4 Fraîcheur et trajectoire dans le grade

Le A/AA/AAA mesure l'alignement. Rien ne mesurait le **moment** : un nouvel établissement détecté il y a
trois jours et le même détecté il y a huit mois produisaient le même grade.

La **fraîcheur** (âge du signal le plus récent, relative à la durée de pertinence du couple) et la
**trajectoire** (densité sur une fenêtre glissante) modulent le grade sans le remplacer. Un signal frais
mais mal aligné ne devient pas AAA.

### 8.5 Seuil de publication

À partir de quelle case de la matrice un dossier devient une opportunité présentée plutôt qu'un dossier
qui continue de mûrir. **Décision produit, à valider explicitement, pas une constante enfouie.**

**Distinct du curseur de sensibilité utilisateur.** Le seuil dit ce qui est présentable; la sensibilité
dit ce que cet utilisateur veut voir parmi le présentable. Les fusionner enlèverait à l'utilisateur la
possibilité d'être plus sélectif que le défaut.

### 8.6 Sensibilité

Deux curseurs indépendants, à ne pas confondre entre eux ni avec la cadence : un pour la confiance
minimale, un pour la pertinence minimale. La cadence, elle, ne dit pas ce qui mérite d'être signalé mais
quand le lot part.

---

## 9. Présentation et livraison

### 9.1 Structure de faits — le narratif se calcule d'abord, se rédige ensuite

Le moteur produit une structure explicite avant qu'aucun texte n'existe : les signaux retenus avec leur
date, leur source interne et leur poids; leur ordre chronologique et les écarts; la sphère retenue et la
raison du lien avec le service; le grade et ce qui l'a déterminé; la confiance d'appariement et son
effet de plafonnement.

**Cette structure est la vérité, le texte n'en est qu'un rendu.** Elle est conservée avec l'opportunité,
ce qui permet de la re-rendre sans recalculer, et de répondre à un utilisateur qui conteste.

### 9.2 Gabarits et narratif — décidé, non construit

*Détail au chantier 21.* **Le principe qui contraint l'architecture : le narratif se calcule d'abord et
se rédige ensuite** — la structure de faits est la vérité, le texte n'en est qu'un rendu. Trois
contraintes valent dès le premier gabarit : **aucun nom de source**, une amorce qui aide à rédiger et
**n'est jamais un message prêt à envoyer**, et une incertitude visible dans la formulation.

### 9.2bis ⚠️ Question ouverte — du rattachement à l'interprétation

**Ce qui est résolu.** Le produit sait **rattacher** : l'identité relie les signaux d'un dossier, la
corroboration monte la confiance quand deux sources concordent, la table signal↔sphère dit quel besoin un
événement annonce.

**Ce qui ne l'est pas.** Rien ne produit encore d'**interprétation** — ce que les signaux, ensemble,
veulent dire. **La structure de faits est une liste, et un gabarit qui rend une liste produit une
énumération, pas un récit.** *« A ouvert un établissement, embauche depuis deux mois, a déposé une
marque » n'est pas « cette entreprise lance une nouvelle ligne d'affaires ».*

**Piste identifiée, ni retenue ni écartée :** un registre de **combinaisons reconnues** — des motifs à
plusieurs signaux portant chacun leur signification et leur formulation. *Nouvel établissement + embauche
+ permis = expansion physique. Dépôt de marque + établissements multiples = mise en réseau. Financement +
embauche de direction = changement d'échelle.* Deux mécanismes déjà prévus y touchent sans le nommer : la
**trajectoire** donne le rythme, et le **signal par absence** donne ce qui ne se produit pas — **souvent
ce qui départage deux interprétations concurrentes des mêmes signaux**.

**Pourquoi rien n'est construit.** On ne saura quelles combinaisons se produisent réellement qu'après que
la boucle ait tourné sur de vrais dossiers. **Inventer douze motifs d'avance reproduirait l'erreur
d'inventer douze sphères.**

**⚠️ La seule chose à faire maintenant : ne fermer aucune porte. Cinq contraintes.**

- **La structure reste extensible** — elle doit pouvoir porter un motif reconnu à côté de ses signaux,
  sans refonte.
- **Les gabarits restent liés au couple signal × sphère**, jamais figés en un texte par signal isolé — *un
  gabarit écrit comme « voici ce signal » ne pourra jamais devenir « voici ce que ces signaux signifient
  ensemble »*.
- **Le lien entre signaux d'un même dossier reste explicite et conservé**, avec ses dates et son ordre.
  **C'est la matière première de toute interprétation future — la perdre fermerait la porte sans qu'on
  s'en aperçoive.**
- **Ne pas fusionner l'interprétation dans le score.** Un motif pourra moduler la pertinence, mais il
  reste distinct des trois axes — sinon il devient impossible de le changer sans toucher au moteur.
- **Une place est réservée dans la présentation** : les faits d'abord, puis **une ligne distincte,
  séparée d'eux**, qui dirait ce que l'ensemble pourrait représenter, **au conditionnel**. *Le
  conditionnel n'est pas une précaution de style — il assume l'incertitude au lieu de la masquer, et il
  reste juste même quand l'interprétation est bonne.* **Deux propriétés à préserver :** les faits restent
  vérifiables indépendamment, donc une interprétation fausse se corrige sans les toucher; et
  l'utilisateur voit sur quoi elle repose.

*Une seconde ligne pourra un jour relier l'interprétation au besoin de l'utilisateur — c'est là que la
correspondance service↔besoin devient visible. **Limite dès maintenant : elle dirait un besoin probable,
jamais une action à poser.** Dire quoi faire glisserait vers le conseil de vente, que la section 6
exclut.*

**Ce qui est demandé se résume à ceci : ne rien construire, ne rien configurer, et ne rien décider qui
empêcherait de l'ajouter plus tard. La place existe; elle reste vide.**

**Ce qui débloquera la décision :** assez de dossiers réels pour voir quelles combinaisons se présentent,
et le taux de rejet pour savoir lesquelles les utilisateurs trouvent justes.

### 9.4 Cadence et livraison — décidé, non construit

Même statut. Détail au chantier 8 et à son amendement.

**Le principe qui contraint l'architecture :** la forme de livraison modifie la valeur perçue à contenu
identique, et **la cadence reste un axe distinct des curseurs de sensibilité** — l'une dit quand le lot
part, les autres ce qui mérite d'être signalé.

**La délivrabilité est une préoccupation de produit, pas de plomberie.** Toute la valeur transite par un
seul canal : **un lot qui atterrit dans les indésirables est un produit qui ne fonctionne pas, quelle que
soit la qualité de la détection.** Trois conséquences durables — le fournisseur d'envoi se choisit sur la
sévérité avec laquelle il surveille son parc partagé plutôt que sur son prix; l'envoi se fait depuis un
**sous-domaine dédié authentifié**, jamais depuis la racine ni depuis le domaine de correspondance
d'affaires; et **le désabonnement en un clic fait partie du premier envoi, pas d'un raffinement
ultérieur**. ✅ *Vérifié en réel le 8 septembre 2026.*


### 9.5 Le silence

*Détail au chantier 14.* **Le mode de défaillance principal n'est pas la mauvaise notification, c'est de
n'envoyer rien pendant trois semaines à quelqu'un qui paie** — l'utilisateur ne peut pas distinguer un
territoire calme, un profil mal configuré et un produit brisé.

**Les principes qui contraignent le produit.**

**Contenu d'un message de silence : l'agrégat, jamais la liste.** Le décompte et les motifs prouvent que
le produit a travaillé; **la liste des écartés ne prouve rien et coûte cher**. Ne jamais nommer un
dossier écarté — l'utilisateur essaiera de l'évaluer, et **s'il en contacte un, le produit vient de lui
enseigner que son filtrage vaut moins que son jugement**.

**L'agrégat est actionnable** : le motif dominant indique quoi proposer. *Hors sphère* → alignement à
revoir. *Identité incertaine* → problème de notre côté.

**Interdiction implémentée, pas seulement documentée : aucun mécanisme ne peut abaisser un seuil de
sensibilité pour rompre un silence.**

**Un lot vide** envoie un message court disant ce qui a été surveillé, puis cesse après quelques lots
consécutifs — **un message hebdomadaire qui ne dit jamais rien devient lui-même l'irritant qu'on
cherchait à éviter.**

### 9.6 Tableau de bord — dans tous les paliers

**Décision du 4 septembre 2026 : Écho dispose d'un tableau de bord.** Un produit qui livre des
opportunités sans aucun endroit pour les colliger oblige l'utilisateur à gérer sa prospection dans sa
boîte de réception. Trois décisions de palier avaient déjà buté sur cette absence — le canal hors
profil, la rétroaction, la profondeur d'exploration — et chaque fois la réponse avait été de
contourner. La cause est réglée plutôt que contournée une quatrième fois.

**La frontière entre les paliers porte sur consulter et agir, pas sur voir.**

**Écho — colliger et réviser ce qui a été reçu :** la liste des opportunités, y compris celles qui
dépassent le plafond de vingt notifications; la vue du canal hors profil; le tri par grade puis
fraîcheur; le filtre par taille; et la rétroaction « Pas pertinent », qui alimente la seule boucle de
correction du moteur.

**Radar et Radar+ — l'outillage pour agir :** statuts de suivi complets formant un pipeline, amorces de
premier contact, carte géographique, export et intégration CRM. Radar+ ajoute les profils multiples
simultanés, les alertes composites, les tableaux de bord agrégés par territoire et l'accès API.

**Conséquence assumée sur le positionnement :** deux des différenciateurs listés jusqu'ici pour Radar
disparaissent — l'existence même du tableau de bord, et la profondeur d'exploration au-delà du plafond
de vingt. Ce qui reste tient debout, mais l'argumentaire de Radar repose désormais entièrement sur
l'outillage d'action et les sources payantes, plus sur aucune restriction de visibilité ni de justesse
de configuration.

### 9.7 Statuts — trois dimensions distinctes, jamais fusionnées en une liste

Un même prospect porte simultanément trois informations de nature différente. Les mettre dans une seule
liste déroulante est la façon classique de casser les trois à la fois : on ne peut plus être « contacté
et archivé », ni « qualifié pertinent mais sans suite ».

**Dimension 1 — Qualification. Dans tous les paliers.** Ce que le système a besoin d'apprendre : le
prospect aurait-il dû être montré?

- `Nouveau` — état par défaut, rien à faire.
- `Retenu` — le prospect est bon. Posé explicitement, ou déduit dès qu'une action de pipeline est prise.
- `Pas pertinent` — le prospect n'aurait pas dû être montré.

**Le motif du rejet est ce qui fait la valeur de la dimension.** Un « pas pertinent » nu dit qu'il y a
eu erreur; un motif dit **quel axe** a échoué, et chaque axe a une correction différente :

| Motif | Ce qu'il corrige |
|---|---|
| Mauvaise sphère de besoin | Le lien signal↔sphère, ou le poids du service dans la sphère |
| Hors de mon territoire | Le rayon du profil, ou la résolution d'adresse |
| Mauvaise taille d'entreprise | Le filtre de taille, ou la mesure de taille elle-même |
| Pas mon type de client | La dimension « qui » (section 3.3) |
| Déjà client / déjà connu | Rien — le moteur a bien travaillé, l'utilisateur avait l'information |
| Signal trop faible ou trop vieux | Les curseurs de sensibilité, ou la durée de pertinence |
| Autre | À lire dans le journal de diagnostic |

Deux règles sur ce sélecteur : **le motif est facultatif et se donne en un geste**, jamais obligatoire —
un motif exigé fait chuter le taux de rétroaction, c'est-à-dire exactement la donnée qu'on cherche à
obtenir. Et **`Déjà client / déjà connu` ne compte jamais comme une erreur du moteur** dans le taux de
rejet : le prospect était bon, l'utilisateur le connaissait déjà.

**Dimension 2 — Pipeline. Radar et Radar+.** Ce que l'utilisateur fait du prospect :
`À contacter` → `Contacté` → `En discussion` → `Gagné`, plus `Joint, sans suite`.

**`Joint, sans suite` n'est jamais un rejet.** Le prospect était bon et la vente n'a pas eu lieu — c'est
de la non-conversion, elle ne compte pas dans le taux de rejet du moteur. Confondre les deux ferait
baisser artificiellement la précision mesurée à chaque vente perdue, et le moteur se corrigerait sur du
bruit commercial.

Aucun libellé ne juge le travail de l'utilisateur *(charte, section 16)* : `Joint, sans suite` décrit un fait,
`Perdu` ou `Échec` porterait un jugement que le produit n'est pas en position de porter.

**Dimension 3 — Cycle de vie. Système, dans tous les paliers.** `Actif` ou `Archivé` *(section 10)*.
Indépendant des deux autres : un prospect peut être archivé en étant `Contacté` et `Retenu`.

**Pourquoi cette séparation compte au-delà de l'ergonomie :** le taux de rejet du moteur se calcule sur
la dimension 1 seule. Toute contamination par la dimension 2 — traiter une vente perdue comme une erreur
de détection — fausse la seule boucle de correction disponible.

**Ordre d'affichage par défaut : grade puis fraîcheur.** Un tri par date place les vieux dossiers non
traités en tête et donne l'impression d'un retard accumulé; un tri par grade place en tête ce sur quoi
il vaut la peine d'agir. Le tri par date reste disponible, non par défaut.

---

## 10. Cycle de vie d'une opportunité — décidé, non construit

**Retiré du corps des spécifications le 4 septembre 2026.** Ces règles décrivent le raffinement d'une
livraison qui n'a jamais eu lieu une seule fois. Elles restent des décisions prises, datées, et vivent
dans `falkye-audit-et-mandat.md` (chantiers 23, 24 et 25) jusqu'à ce qu'il y ait quelque chose à
raffiner.

**Les décisions, en une ligne chacune, pour ne pas les reperdre :** mise à jour silencieuse par défaut,
renotification uniquement au franchissement d'un palier vers le haut et une seule fois par palier;
prospect rejeté qui ne remonte que sur un passage à AAA, avec mention; archivage après une période
configurable d'un mois par défaut, alerte groupée dix jours avant, **aucun effacement jamais**; remontée
d'une archive qui reçoit un signal fort; antériorité à l'inscription selon la durée de pertinence de
chaque sphère, plafonnée à vingt notifications, présentée distinctement de la détection en direct.

**Ce qui existe dans la version brute :** un état actif ou archivé, rien de plus.


## 11. Enrichissement web

Dès qu'une entreprise est détectée, le système cherche son site officiel et en extrait un contexte
léger. Dernière étape avant la notification.

Recherche de l'URL à partir du nom et de la ville. Ratissage ciblé — accueil, à propos, services,
carrières, actualités, contact — jamais un crawl complet. Extraction : description des activités et
domaine d'expertise, coordonnées publiques, indices de taille, mentions d'expansion, offres d'emploi
affichées.

Sert aussi de **filtre d'exclusion** : si le contenu révèle que l'entreprise ne correspond manifestement
pas, le prospect est écarté plutôt que notifié.

**Respect du robots.txt et des limites de fréquence.** Contexte complémentaire à la justification, jamais
un remplacement — le contenu d'un site peut être désuet.

**Point à revoir, signalé en inspection :** cette étape est aujourd'hui systématique pour **chaque**
entreprise détectée, y compris celles qui ne franchiront jamais le seuil de publication. Avec
l'introduction d'un seuil explicite (section 8.5), il devient possible de l'exécuter après le seuil
plutôt qu'avant, ce qui réduirait fortement le volume de requêtes. La contrepartie est que
l'enrichissement sert aussi de filtre d'exclusion, donc le déplacer changerait ce qui est exclu. À
trancher, pas à laisser tel quel par défaut.

---

## 12. Plans, sources payantes et portail

### 12.1 Les trois paliers

| Palier | Prix | Public | Sources |
|---|---|---|---|
| **Écho** | 29,99 $/mois, jamais gratuit | Travailleur autonome | Sources gratuites, plus toute source de couverture |
| **Radar** | 89 $/mois | PME en croissance | Écho + sources payantes choisies par nous, portail à paiement intégré |
| **Radar+** | Dès 349 $/mois — à réviser | Entreprises et institutions | Radar + portail ouvert, clés API du client |

Un seul portail à construire, avec deux couches par-dessus. Commun : connecteurs génériques,
normalisation vers le même pipeline. Propre à Radar : paiement intégré (Stripe). Propre à Radar+ :
gestion de clés API utilisateur, sans transaction de notre part sur la source.

Toute source ajoutée par un utilisateur Radar+ suit le même gabarit de registre, et peut révéler une
sphère non répertoriée — c'est ainsi qu'est née la sphère « Financement / accès au capital ».

**Format des cartes de source dans le portail :** domaine ou type de la source, **et** avantage concret,
jamais une ligne générique. Ne jamais présumer qu'un client sait choisir entre deux options similaires —
la vraie distinction entre HubSpot et Pipedrive est la structure d'équipe et le besoin marketing, pas le
secteur d'activité comme on l'avait d'abord supposé.

### 12.2 Placement d'une source — couverture contre enrichissement

*Détail au chantier 5.*

**Le classement se fait par couple source × sphère, jamais par source seule.** Une **source de
couverture** — sans elle la sphère produit zéro, ou des résultats non discriminants — appartient au
palier où la sphère est offerte, **peu importe son coût**. Une **source d'enrichissement** améliore un
résultat qui existerait de toute façon au palier inférieur.

**Défaut en l'absence de mesure : une source nouvelle est réputée de couverture et va au palier
d'entrée.** *Les deux erreurs ne coûtent pas la même chose : se tromper vers le bas coûte un argument de
vente, vers le haut un abonné qui ne reçoit rien et ne revient pas.*

**« Il y a déjà N sources dans ce palier » n'est jamais une réponse** — c'est le raisonnement qui a
produit l'erreur fondatrice. **Le nombre de sources n'est pas l'objectif, la précision l'est.**

### 12.3 La même règle s'applique aux fonctionnalités

Une fonctionnalité qui corrige l'**exactitude** de ce qui est montré est de la couverture; une qui ajoute
de la **profondeur** à un résultat déjà juste suit la règle de palier. **Un fait sur l'entreprise — la
fraîcheur d'un signal, sa durée de pertinence — n'est pas une préférence d'utilisateur : le retirer d'un
palier ne l'allège pas, ça le rend moins juste.**

**Quatre corrections appliquées sur cette base.** Le **filtre par taille** passe au palier d'entrée —
même classe d'outil que les curseurs de sensibilité, déjà présents partout : *le retirer, ce n'est pas
alléger le palier, c'est le laisser recevoir des prospects qu'il ne peut pas prendre*. La **rétroaction**
existe dans tous les paliers — **c'est ce qui alimente le taux de rejet, seule boucle de correction du
moteur, et la retirer reviendrait à n'apprendre que des utilisateurs les moins nombreux**. Le **bonus de
corroboration inter-provinciale** passe en veilleuse, sans quitter le registre. Et **l'assistance de
niveau 2 est disponible partout** — c'est une escalade automatique qui rend la configuration juste, pas
un enrichissement du résultat.

**Ce que le palier intermédiaire conserve pour justifier le saut de prix :** pipeline de statuts, amorces
de premier contact, carte, intégration CRM, sources payantes, temps réel. **La différence porte sur
l'outillage d'action, jamais sur l'exactitude ni sur la visibilité de ce qui est montré.**

**Reclassement des cinq sources vérifiées : à faire**, avec des mesures plutôt qu'une hypothèse. En
attendant l'instrument de densité, le défaut ci-dessus s'applique.

### 12.4 RDPRM — deux mécanismes à ne jamais confondre

**Mécanisme 1, opérateur.** FALKYE achète la donnée pour son propre usage produit, comme n'importe quelle
source payante. Le résultat entre dans le pipeline standard, visible par tout profil dont la sphère
correspond. Placement conditionnel à la clarification légale déjà notée (personne physique contre entité
juridique dans les garanties) : si l'usage commercial est confirmé sans restriction, **Écho** — une
source nécessaire à la qualité de base n'est pas reléguée à un palier supérieur parce qu'elle est
payante. Si un doute persiste, **Radar**, pour contenir l'exposition en attendant.

**Mécanisme 2, portail client (Radar minimum).** Le client paie sa propre recherche. **Le résultat reste
strictement scopé à son instance — jamais partagé, réutilisé ou redistribué.** Vérification légale
faite : aucune clause explicite trouvée sur la réutilisation d'un résultat, et le risque est jugé
minimal puisque rien ne sort de l'instance du client — contrairement à une mise en commun, qui resterait
à proscrire. **Blocage avant construction :** le format réel d'un document RDPRM n'a jamais été examiné.

### 12.5 Import manuel

Pour toute source dont l'automatisation implique un coût récurrent non engagé, ou qu'un blocage d'accès
empêche d'atteindre depuis l'environnement infonuagique. Deux formes — résultat unitaire (RDPRM) et
fichier complet (REQ) — suivant le même principe générique.

Une fois importée, la donnée entre dans la même boucle que toute source automatisée, sans traitement
spécial.

**Vrai pour le TRAITEMENT, faux pour le comptage — et c'est la confusion qui en découle qui compte.**
Une source active en import manuel **ne tourne pas dans un cycle** : elle n'entre dans le pipeline que
par une action explicite. Le moteur ne boucle que sur les sources actives **automatisées**. Un cycle
rapporte donc moins de sources que le registre n'en déclare actives, et **les deux comptes sont
justes** — ils ne comptent pas la même chose. Le 9 septembre 2026, un cycle en a traité huit là où le
registre en donnait dix, et rien n'expliquait l'écart.

**Même rigueur de calibration** : l'import manuel contourne l'automatisation de la collecte,
jamais la calibration. Chaque entrée en import manuel porte un **lien direct vers la bonne page de
consultation**, pas seulement vers l'accueil du site. Le registre garde trace de la méthode d'accès,
utile pour savoir plus tard si l'automatisation en vaudrait la peine.

### 12.6 Intégrations

Point de **sortie**, jamais une source, jamais dans un tableau de sources. HubSpot et Pipedrive, dès
Radar, le client paie son propre compte. Construites et testées contre des mocks; **jamais validées
contre les vrais services**.

**Décision du 4 septembre 2026 : la connexion d'un CRM se fait par OAuth, pas par jeton collé.** Le
modèle par jeton d'application privée est écarté.

**Où ça se passe, et où ça ne se passe pas.** La connexion d'un CRM est un réglage de **sortie**, dans
la configuration du compte de l'utilisateur. **Elle ne passe pas par le portail** : le portail est un
mécanisme de paiement et de gestion d'accès pour des **sources** payantes — des points d'entrée qui
alimentent le moteur. Une intégration ne coûte rien à FALKYE, ne demande aucun paiement, et n'entre nulle
part dans le pipeline. Les deux mécaniques sont distinctes et ne partagent rien.

**Le modèle de production, inchangé sur le fond :** le client Radar connecte **son propre compte CRM**,
paie son compte, apporte son accès. FALKYE ne paie ni ne gère rien. Ce qui change, c'est la façon dont
l'accès est accordé.

**Comment ça se présente au client :** il clique « Connecter HubSpot », voit un écran d'autorisation qui
liste ce que FALKYE pourra lire et écrire, et approuve. Aucune navigation dans des réglages de
développeur, aucune portée à cocher lui-même, rien à copier.

**Les trois raisons de la décision.**

*L'expérience d'accueil.* Un abonné Radar n'est pas nécessairement technique. Lui demander de générer un
jeton dans les réglages développeur de son CRM est une friction réelle, et une source d'abandon au
moment précis où il essaie de tirer valeur de son abonnement.

*La responsabilité de sécurité.* Les jetons OAuth sont courts et se rafraîchissent, et le client révoque
l'accès depuis son propre compte sans passer par FALKYE. Un jeton collé est une clé de longue durée
donnant accès au CRM d'un client, conservée par FALKYE — une responsabilité portée seul.

*Ce que ça ouvre.* Les webhooks exigent une application publique : sans eux, le lien ne peut que pousser
en sortie, jamais réagir à un événement côté CRM. Et le listage sur l'App Marketplace, condition du
programme Technology Partner, n'est pas accessible autrement.

**Pourquoi maintenant plutôt que plus tard.** Tant que la connexion n'est pas construite, c'est une
décision de conception. Une fois qu'elle existe avec des clients branchés par jeton, migrer veut dire
redemander à chacun de se reconnecter — coût croissant au sens de la charte, section 14.

**Ce que ça change au travail.** Le connecteur lui-même — appel à l'API, format des données poussées,
gestion des erreurs — est inchangé et se valide de la même façon. Ce qui s'ajoute est une couche
d'autorisation dans la configuration du compte : inscription au portail développeur de chaque CRM, flux
d'autorisation standard, gestion du rafraîchissement des jetons. Travail réel mais borné, et fait une
fois pour les deux CRM.

**Ce que ça change à la tâche en attente.** Les jetons de test restent utiles pour valider le connecteur
contre les vrais services plutôt que contre des mocks. Ils ne sont simplement plus le modèle de
production.

**Pipedrive — vérifié le 4 septembre 2026, même conclusion mais deux différences à connaître.**

Le flux d'autorisation OAuth 2.0 est **requis pour toute application listée au marketplace**. Le jeton
d'API personnel est prévu pour des scripts internes et des intégrations privées où les identifiants
d'un seul utilisateur suffisent. Même partage que HubSpot.

**Différence 1 — un processus de révision par Pipedrive, à prévoir au calendrier.** Pipedrive distingue
trois types d'applications : *publique* (au marketplace, révision requise), *non listée* (accessible par
lien direct, **révision requise aussi**), et *privée* (utilisable uniquement par les comptes de la même
entreprise). Autrement dit, dès qu'un client extérieur doit pouvoir brancher son propre compte, il faut
passer la révision — même sans vouloir figurer au marketplace. C'est une étape que HubSpot n'impose pas
de la même façon, et elle prend du temps. **À entamer tôt plutôt qu'au moment où un client le demande.**

**Différence 2 — un avantage opérationnel réel d'OAuth, qui n'était pas dans les raisons de la
décision.** Chez Pipedrive, le budget d'appels quotidien est alloué par compte client. Pour une
application au marketplace en OAuth, **les appels sont tirés du budget du compte de l'utilisateur
final** : un client qui dépasse son budget n'affecte aucun autre client. Avec un jeton statique, les
limites s'appliquent par jeton, ce qui concentre le risque. OAuth isole donc les clients les uns des
autres sur les quotas, en plus des raisons déjà retenues.

**Un point d'écart à vérifier au moment de construire :** certains intégrateurs classent Pipedrive parmi
les plateformes exigeant que **le client** enregistre lui-même une application et fournisse ses propres
identifiants OAuth, alors que HubSpot permet à l'éditeur de fournir les siens. Si c'était le cas, une
partie de la friction qu'on cherchait à retirer reviendrait côté Pipedrive. À confirmer directement dans
la documentation développeur avant de construire — pas à présumer dans un sens ou dans l'autre.

**Principe qui en découle, applicable au-delà du CRM :** pour toute intégration à un compte tiers
appartenant au client, retenir le mécanisme d'autorisation que la plateforme cible recommande pour les
intégrations multi-clients. Ne pas choisir le mécanisme le plus simple à construire quand il est celui
que la plateforme réserve à un usage interne.

## 13. Frontière du non déterministe

La règle n'écarte pas le ML, elle écarte **l'opacité**. La raison est dans l'utilisateur : il doit
pouvoir comprendre pourquoi ce prospect lui a été montré, et un score qu'on ne peut pas expliquer ne se
défend pas devant un client qui le conteste.

- **Aucun composant non déterministe ne produit un score, un seuil ou une décision de publication.**
- **Un composant non déterministe peut normaliser une entrée** dans un catalogue fermé — secteur en
  texte libre, titre de poste, sujet déclaré. C'est une traduction, vérifiable par échantillonnage.
- **Un composant non déterministe peut formuler une sortie** à partir de faits déjà établis.
- **Test de sécurité automatisable :** si la sortie ne peut pas être reconstruite à partir de la
  structure de faits qui l'a produite, elle est fausse. Reproductible ne veut pas dire déterministe au
  caractère près — reconstituable.
- **Proposer, jamais appliquer.**
- **Le ML classique n'est pas synonyme d'opacité.** Une régression logistique ou un arbre peu profond
  entraînés sur les rejets « Pas pertinent » sont lisibles. Admissibles pour **proposer** un ajustement
  de pondération une fois assez de rejets accumulés, jamais pour l'appliquer.

### 13.1 Assistance IA de configuration — les deux niveaux, dans tous les paliers

**Correction du 4 septembre 2026.** Les versions antérieures réservaient le niveau 2 à Radar et Radar+.
C'était une incompréhension et non une décision : les deux niveaux forment un seul processus de
configuration, disponible partout.

Le raisonnement qui le confirme : **le niveau 2 n'est pas un mode que l'utilisateur choisit, c'est une
escalade automatique** qui ne se déclenche que si le niveau 1 échoue. Ce n'est donc pas un
enrichissement du résultat, c'est ce qui rend la configuration juste — même classe que la durée de
pertinence. Et c'est en Écho qu'une configuration bancale coûte le plus cher, l'abonné y ayant le moins
de moyens de s'en apercevoir.

**Niveau 1** — classification rapide et peu coûteuse (similarité de texte, embeddings ou modèle léger)
qui associe la description aux sphères déjà connues, et dont le résultat produit directement les poids
proposés sur l'échelle 0-100.

**Niveau 2** — un modèle plus capable, avec **deux déclencheurs d'escalade** :
- *Aucune correspondance confiante* — le niveau 2 analyse la description dans tout le catalogue pour
  comprendre pourquoi elle ne correspond à rien de connu.
- *Tie exact* — au moins deux candidates au score maximal. Portée réduite : laquelle de ces N
  candidates, et avec quel poids relatif. Ce cas est né d'un vrai partage à égalité exact, où forcer un
  gagnant unique aurait perdu du signal.

**Garde-fous, inchangés.** Schéma de sortie contraint, chaque identifiant tiré d'un catalogue fermé. Le
niveau 2 peut enrichir silencieusement le dictionnaire de synonymes d'une sphère existante, mais ne
crée jamais seul une nouvelle sphère au registre — un cas non rattachable se journalise comme candidat
à examiner.

**Trois précisions qui manquaient, ajoutées en même temps que la correction :**

- **La journalisation d'un cas non résolu se fait dès l'échec du niveau 1, dans tous les paliers**,
  indépendamment de l'escalade. Sans quoi les descriptions non résolues du palier le plus nombreux
  n'entreraient jamais au journal de diagnostic, et le signal de demande (section 14) perdrait sa
  principale source.
- **Repli quand le modèle est indisponible ou que l'escalade échoue : garder les candidates à égalité,
  à poids égal**, plutôt que de forcer un gagnant. Le modèle plusieurs-à-plusieurs le supporte
  nativement, et c'est le raisonnement qui avait fait abandonner le gagnant unique. L'utilisateur peut
  ensuite nommer sa sphère principale sans jamais toucher à un pourcentage.
- **Bornage du coût sans quota.** Les specs écartent explicitement un système de quota. Le bornage se
  fait autrement : une description déjà résolue ne redéclenche pas d'escalade — mise en cache par
  empreinte du texte. Un utilisateur qui reconfigure son profil sans changer sa description ne coûte
  rien de plus.

**Rappel d'une distinction facile à mal coder :** sur la dimension « qui », la réponse « aucune
restriction, s'applique largement » est une **réponse positive**, jamais une absence. Elle n'escalade
pas au niveau 2 et ne se journalise pas comme cas non résolu, contrairement à « aucune correspondance
trouvée ».

**Le diagnostic à rebours (section 7.4) réutilise le mécanisme du niveau 2, retourné** — inventaire de
champs vers sphères candidates. C'est une **opération interne, sans utilisateur**, donc conditionnée par
aucun palier.

### 13.2 Deux composants seulement, et une passerelle unique

*Le mécanisme est au chantier 26. Ce qui suit est la contrainte d'architecture qu'il doit respecter.*

Cinq usages du non déterministe existent dans le produit. **Ils se ramènent à deux formes, et il ne doit
exister que deux composants** — pas cinq implémentations parallèles avec cinq jeux de garde-fous.

**Forme A — classer un texte libre dans un catalogue fermé.** Sortie contrainte, chaque identifiant tiré
du catalogue. Trois appelants, une seule implémentation : la suggestion à la configuration, la
normalisation de texte libre, et le diagnostic à rebours — **la même opération lue dans l'autre sens**.

**Forme B — rédiger à partir d'une structure de faits.** Un seul appelant, le narratif.

**Ne pas fusionner A et B.** Leur garde-fou n'est pas le même — catalogue fermé d'un côté, test de
non-invention de l'autre — **et c'est précisément ce que la frontière protège**.

**Ce qui réduit réellement le coût : normaliser les vocabulaires, pas les enregistrements.** Le volume
dominant est la normalisation de texte libre, qui s'appliquerait à chaque enregistrement ingéré — des
millions de lignes. **Or ces champs ont un vocabulaire borné** : 211 valeurs distinctes de secteur pour
311 notifications. **Une valeur déjà vue se résout par consultation, sans appel** — le coût devient
proportionnel aux **nouvelles** valeurs, ce qui tend vers zéro à mesure que le vocabulaire se remplit.
*C'est la seule optimisation qui change l'ordre de grandeur.*

**Une passerelle unique**, point de passage obligé des deux formes. Ce n'est pas une élégance
d'architecture : **c'est le seul endroit où quatre choses peuvent être garanties plutôt qu'espérées** —
le cache, la validation du garde-fou, le repli, et le comptage par usage. *Sans ce point unique, il
existe plusieurs flux de coût et aucun endroit qui les additionne.*

---

## 14. Instruments de mesure

*Détail aux chantiers 9, 13 et 11-19.* **Trois instruments dont la valeur dépend entièrement de
l'historique accumulé.** Les livrer tôt ne donne pas de résultat immédiat — **ça démarre l'accumulation,
qui ne se rattrape pas en accélérant plus tard.**

**Densité de signal** par sphère × territoire × palier. Sert à trois choses : **exposer honnêtement une
combinaison mince avant que la personne paie**, rendre le classement couverture/enrichissement
calculable, et prioriser la recherche de sources. *Pour un profil couvrant une sphère dense et une vide,
la moyenne masquerait exactement ce qu'on cherche à exposer.*

**Taux de rejet** par profil, sphère, source et gabarit, calculé sur les statuts déjà collectés.
**Distinguer le rejet — n'aurait pas dû être montré — de la non-conversion — bon prospect, vente non
faite** : le second n'est jamais une erreur du moteur. **Un rejet est un signal sur le profil, pas sur la
sphère** — le moteur n'apprend jamais d'un utilisateur pour les autres sans confirmation.

**Journal de diagnostic**, à lire aussi comme **signal de demande** : ce que de vrais utilisateurs ont
demandé et que le produit n'a pas su servir **vaut mieux que n'importe quelle étude de marché**. Agrégé
par motif et croisé avec la densité — **forte demande et faible densité est la définition du prochain
mandat de recherche.**

---

## 15. État de construction du produit

**⚠️ Construit, déployé et vérifié sont trois états différents.** Trois écarts ont été trouvés le même jour parce que l'un avait été pris pour un autre. **L'état détaillé, chantier par chantier, vit désormais dans `falkye-audit-et-mandat.md`** — chaque chantier y porte sa liste dynamique, avec quatre états et la preuve attachée à chaque case cochée. Ce qui suit n'est qu'un résumé.

**Vérifié sur l'état réel du système** — persistance de la base distante, éprouvée par recyclage volontaire du conteneur; écriture groupée du moteur de diff, mesurée sur les trois chemins; **application déployée et active sur l'hôte** au 7 septembre 2026, point d'entrée public joignable en HTTPS, miroir REQ chargé avec 73,2 % d'entrées localisées.

**Le canal d'envoi est désormais validé en réel** — courriel parti du serveur le 8 septembre 2026,
arrivé chez le destinataire, classé en infolettre, avec authentification complète et lien de
désabonnement pointant vers notre propre point d'entrée.

**Deux faits du 8 septembre qui changent l'exploitation.** Le **cycle en régime** prend 29 min 10 s,
huit sources sur huit en succès, **dont seize minutes d'enrichissement web qui échoue**. Et un **index
composite sur `(neq, nom_detecte_normalise)`** a réduit le coût d'une résolution d'entreprise non
identifiée de ~16 800 à 84 lignes lues — **la fuite est réduite, pas fermée** : le repli par sous-chaîne
balaie toujours la base durable *(journal, cas 23)*.

**Et un mécanisme du 9 septembre qui change la façon de décider.** La chaîne de déploiement **applique
les migrations de schéma sur les deux bases à chaque passage**, et le déclencheur ne regarde pas ce que
le commit contient : **une fusion qui ne change qu'un document déploie exactement comme les autres.** Le
raisonnement complet est à `docs/DEPLOIEMENT.md`. *Découvert en cherchant l'auteur de colonnes apparues
sans qu'on les demande — troisième forme cette semaine d'un mécanisme actif qu'on croyait au repos
(journal, cas 22).*

**Construit, jamais validé contre le vrai service** — intégrations CRM, paiement, assistance IA de
niveau 2, TheirStack, géocodage. **Ces éléments ne passent pas au statut plein avant d'avoir tourné
contre le vrai service.** Ça ne bloque pas le développement, ça bloque la promesse commerciale.

**Les trois chantiers à coût croissant ou irrécupérable** — conservation d'état (1), identité multi-territoire (3), confiance d'appariement (4).

**Décisions ouvertes — leur emplacement unique est le registre en tête de `falkye-audit-et-mandat.md`.**
*Elles n'étaient nulle part rassemblées et aucune ne portait de date, alors que la charte §15 exige que
l'échéance soit posée au moment où l'état est posé. **Ni leur liste ni leur compte ne se recopient ici**
— ils se lisent au registre, qui bouge à chaque décision prise ou ouverte.*

**Vérification légale à faire sur les sources héritées.** Le REQ n'est jamais passé par le gabarit d'activation — c'est ce qui a laissé sa licence non vérifiée. **SEAO, Investissement Québec et permis de construction de Laval sont dans la même situation.** À vérifier maintenant, non pour demander quoi que ce soit, mais pour savoir combien d'autorisations seront nécessaires au jour du déclencheur plutôt que de les découvrir une à une.

---

## Annexe — points relevés en inspection

Contradictions et incohérences trouvées en croisant les documents, corrigées dans cette version. Listées
parce que chacune a une origine, et que l'origine est plus utile que la correction.

**1. La section 10 avait disparu.** L'ancien document passait de 9bis à 11; le contenu de la section 10
— l'enrichissement web — subsistait sans titre, rattaché visuellement à 9bis. Corrigé : section 11 ici.

**2. Le principe directeur sur le NEQ pivot contredisait la décision d'identité interne.** L'ancien
principe 8 faisait du NEQ la clé de déduplication, de corroboration et du dossier cumulatif. Reformulé.

**3. Le principe « un seul indice de confiance, jamais de jauges parallèles » semblait interdire le
troisième axe.** En réalité il porte sur l'affichage — une jauge par notification, pas une par signal.
Précisé, sans quoi il aurait servi d'argument contre la confiance d'appariement.

**4. L'interdiction d'anticiper « l'agrégation régionale » contredisait une fonctionnalité vendue.** Les
tableaux de bord agrégés par territoire sont au catalogue Radar+. Le principe 9 ne mentionne plus ce cas.

**5. Le contexte d'origine était périmé.** Il décrivait Alexandre en recherche de mandats en implantation
de systèmes d'inventaire, alors que la sphère « Gestion d'inventaire » a été retirée du registre et que
le principe de polyvalence interdit précisément de coder le produit autour de son cas. Remplacé par une
description du produit.

**6. Guichet-Emplois figurait comme source active** dans le tableau des sources par plan, alors que les
sections 7 et 8 le donnaient à `à développer` faute de nom d'employeur. Corrigé.

**7. Le signal 1 contenait des lignes dupliquées** — artefact de copier-coller.

**8. Le placement des cinq sources vérifiées contredisait la charte.** Traité en 12.2 et 12.3.

**9. Les vérifications de base étaient inapplicables hors Québec** et devenaient soit une exclusion
totale, soit une promesse non tenue. Traité en 6.2, et largement neutralisé par la priorité québécoise.

**10. Point non résolu, signalé : l'enrichissement web tourne pour chaque entreprise détectée**, avant
tout seuil. *Décision ouverte D9 au registre de l'audit. **À trancher avant d'optimiser le point 27.1**,
qui traite le même mécanisme comme un coût — seize des vingt-neuf minutes d'un cycle en régime — sans
savoir qu'il sert aussi de filtre.* Avec un seuil de publication explicite, la question de le déplacer se pose — mais il sert
aussi de filtre d'exclusion, donc le déplacer change ce qui est exclu. À trancher.

**11. Résolu — le canal « hors profil déclaré » n'existait qu'en Radar+**, alors que la règle de
redirection s'applique à tous les profils. Pour Écho et Radar, la redirection n'avait pas de destination
et le signal disparaissait — précisément le malus silencieux que la règle voulait empêcher. **Décision
prise : la redirection a lieu dans l'ensemble de la solution.** Voir section 3.3 pour la forme du canal
par palier et pour ce que Radar+ conserve comme différenciation.
