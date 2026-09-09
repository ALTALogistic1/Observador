# FALKYE — Sources par sphère de besoin : candidats vérifiés

Recherche du 3 septembre 2026. Chaque candidat ci-dessous a été vérifié en consultant directement
la page réelle de la source (page de licence, page de téléchargement, ou registre lui-même), pas
seulement un résumé de recherche. Les candidats écartés et les sphères sans signal sont rapportés
aussi explicitement que les trouvailles.

---

## ⚠️ Volet légal — vérifié en détail, à traiter avant tout le reste

La règle qui ressort de la vérification : **au Québec, le statut légal d'une donnée dépend du canal
de diffusion, pas de l'organisme ni du fait qu'elle soit publique.** Le même fait — un permis, une
certification — peut être librement exploitable commercialement s'il sort par Données Québec, et
interdit s'il sort par une page web ministérielle. Le réflexe à installer : **chercher
systématiquement s'il existe une version « données ouvertes » d'une source avant de scraper sa page
web.** Dans le cas des permis alimentaires, ça a fait exactement la différence (voir section 5).

### Le régime par défaut : tout est réservé

`quebec.ca/droit-auteur` (mis à jour le 10 février 2025) : le gouvernement « détient les droits
exclusifs de propriété intellectuelle sur tous les documents, **données, compilations** et autres
œuvres qu'il produit, publie ou diffuse », et il est « interdit de reproduire, télécharger, stocker,
traduire, adapter, publier ou représenter en public » ces contenus sans autorisation préalable.
Autorisation demandée en ligne, réponse en ~15 jours ouvrables, formulaire qui demande les
coordonnées de la personne **à facturer** — donc une redevance est possible, ce n'est pas
automatiquement gratuit.

Ce n'est pas une formule isolée : la même revendication, mot pour mot ou presque, se retrouve chez
Revenu Québec (qui vise explicitement le fait d'« **indexer dans une base de données** »), à la
Commission d'accès à l'information (qui nomme explicitement « les compilations de données » comme
œuvres protégées et exige une autorisation pour tout usage **commercial**), et chez plusieurs
ministères qui gèrent leur propre guichet d'autorisation.

### L'exception qui sauve la mise : Données Québec

Le gouvernement et une vingtaine de municipalités ont adopté une licence commune de données ouvertes
— Creative Commons 4.0, **variante CC-BY par défaut**, qui autorise nommément la distribution,
l'adaptation et l'usage **commercial** moyennant l'attribution. Quand un jeu est diffusé là, la
licence prime sur la revendication générale.

**Piège à ne pas manquer :** la licence CC 4.0 « se décline en six variantes », et toutes ne sont pas
équivalentes. Hydro-Québec, par exemple, diffuse sous **CC-BY-NC** — *utilisation non commerciale*,
donc inutilisable pour FALKYE. La règle n'est donc pas « Données Québec = permis », c'est
**« vérifier la variante de licence affichée sur la fiche de chaque jeu, un par un »**. À intégrer
comme case obligatoire dans le gabarit d'activation d'une source, au même titre que la règle de
calibration.

### Le cas bloquant : l'AMF

À vérifier les conditions de l'AMF directement, le résultat est plus dur que ce que j'annonçais dans
la première version de ce rapport. L'AMF n'est pas régie par `quebec.ca` — elle a ses propres
conditions générales, et elles interdisent nommément de « vendre, distribuer, publier, afficher,
modifier, **indexer dans une base de données**, copier, reproduire ou réutiliser de quelque façon que
ce soit le contenu du site Web de l'AMF […] sans avoir obtenu au préalable le consentement **écrit**
de l'AMF ». Seule exception prévue : télécharger ou imprimer une copie pour **usage personnel**.

« Indexer dans une base de données » décrit précisément ce que FALKYE ferait du bulletin. Ce n'est
donc pas une zone grise à clarifier : c'est une **interdiction explicite**, levable uniquement par un
consentement écrit obtenu à l'avance. La source reste excellente sur le fond (voir section 3), mais
elle passe de « autorisation à vérifier » à « **bloquée tant qu'il n'y a pas d'entente écrite** ».

Piste de contournement à explorer, non vérifiée à ce jour : la même déclaration 45-106F1 est déposée
dans SEDAR+ et publiée par les autres membres des ACVM. Un régulateur d'une autre province pourrait
diffuser la même information sous des conditions moins restrictives — à vérifier avant d'abandonner
le signal.

### Ce que ça implique pour l'existant

À reposer sur les sources québécoises **déjà actives** : sont-elles ingérées depuis un jeu sous
licence ouverte, ou depuis une page web? La distinction n'est pas cosmétique, et l'architecture en
registre extensible permet justement de désactiver proprement une source qui s'avérerait
problématique — mais encore faut-il avoir posé la question.

---

## 1. CIPO / IP Horizons — marques, dessins industriels, brevets

**La meilleure trouvaille cross-sphère de cette recherche.**

- **Sphères servies :**
  - *Franchisage / développement de réseaux (#8)* — la marque de commerce **est** l'actif central d'un
    réseau de franchise; un nouveau dépôt par une PME opérante est le signal le plus direct qui existe
    pour cette sphère. Croisé avec plusieurs nouveaux établissements au REQ, ça devient très fort.
  - *Ingénierie / design industriel (#12)* — un enregistrement de dessin industriel = un nouveau produit
    physique mis en marché.
  - *Automatisation / robotique (#15)* — brevets déposés dans les classes pertinentes.
  - *Analytique d'affaires / gestion de données (#7)* — brevets, mais couverture faible (peu de PME
    québécoises brevettent en analytique).
  - *Juridique / conformité réglementaire (#11)* — un portefeuille de PI qui grossit crée un besoin
    juridique récurrent.
  - Aussi, en second rang : marketing/vente, commerce de détail, agroalimentaire (nouvelles marques
    de produits), import/export.
- **Bulk ou lookup :** bulk, franchement. Fichiers XML ST.96 hebdomadaires pour les marques, les
  dessins industriels et les brevets; XLSX hebdomadaire des brevets octroyés (depuis le 20 août 2024);
  jeux « chercheurs » CSV/TXT trimestriels plus faciles à traiter. Un **SFTP d'automatisation est
  officiellement offert et documenté** — c'est rare et ça enlève toute ambiguïté sur le scraping.
- **Coût :** gratuit.
- **Conditions d'utilisation :** vérifiées ligne par ligne. CIPO accorde une licence « mondiale, libre
  de redevance, non exclusive, révocable » pour un usage **commercial** explicitement nommé, avec droit
  de sous-licence. Obligations réelles : mention d'attribution obligatoire, et obligation de cesser
  d'utiliser un enregistrement dès que CIPO publie un avis de modification le concernant. Régie par
  le droit de l'Ontario.
- **Fiabilité :** organisme fédéral, données primaires.
- **Piste ou Réflexion :** Réflexion. Aucun identifiant d'entreprise (ni NEQ ni numéro fédéral) — le
  rapprochement se fait par nom et adresse du requérant, avec la même imprécision que les licences
  Vancouver/Toronto.
- **Tier de confiance :** moyen à fort selon le filtrage. Dépôt de marque par une entreprise déjà
  ancrée avec adresse au territoire = **fort**. Enregistrement de dessin industriel = **fort** (produit
  concret). Brevet seul = **moyen** (délais de 18 mois+ entre dépôt et publication, le signal est vieux).
- **Calibration nécessaire (bruit à exclure) :** (a) exclure les désignations Madrid de titulaires
  étrangers, qui dominent le volume et ne représentent aucune croissance locale; (b) exclure les dépôts
  faits au nom de cabinets d'agents; (c) filtrer sur l'adresse du requérant dans le territoire ciblé;
  (d) distinguer un premier dépôt d'un renouvellement ou d'une cession administrative.

---

## 2. OQLF — liste des entreprises certifiées (et listes connexes)

**La seule source trouvée qui livre le NEQ directement.** C'est ce qui la rend précieuse : zéro
appariement approximatif, jointure directe sur le pivot du Québec.

- **Sphères servies :**
  - *Traduction / communications multilingues (#4)* — sphère cible, signal direct et le seul trouvé.
  - *Juridique / conformité réglementaire (#11)* — la francisation est un processus de conformité
    légale avec échéances et sanctions.
  - *Gestion documentaire / archivage (#5)* — la francisation touche les manuels, contrats, formulaires
    et interfaces logicielles; c'est le signal le plus proche trouvé pour cette sphère.
  - *Formation / développement des compétences* — cours de français en entreprise.
  - *Technologie / systèmes / TI* — obligation d'offrir les logiciels en français.
  - *RH, marketing, commerce de détail* en second rang (affichage, emballage, communications internes).
- **Ce qu'elle apporte en plus, et qui n'existe nulle part ailleurs dans FALKYE :** l'obligation vise
  les entreprises de **25 personnes ou plus** au Québec. Une entreprise qui apparaît sur cette liste est
  donc, à cette date, confirmée à 25+ employés par un organisme public. C'est un **marqueur de seuil
  d'effectif daté**, ce qu'aucune source active ne fournit aujourd'hui.
- **Bulk ou lookup :** bulk. La recherche se fait par **date de certification** dans une liste déroulante
  qui remonte à 1977; chaque date retourne le lot complet (plusieurs centaines d'entreprises) avec NEQ,
  nom, adresse complète et date. Nouveau lot environ **aux deux semaines**. La recherche par nom/NEQ
  existe en plus, mais n'est pas nécessaire pour la découverte.
- **Coût :** gratuit.
- **Conditions d'utilisation :** ⚠️ page web ministérielle sans licence ouverte → tombe sous la
  revendication de droit d'auteur du gouvernement du Québec décrite plus haut. **Autorisation à demander
  avant activation.** Ne pas présumer que c'est permis parce que c'est public.
- **Fiabilité :** organisme public, donnée primaire. Note mineure : le pied de page affiche « dernière
  mise à jour : 2026-01-20 » alors que le lot le plus récent est daté du 2026-09-01 — artefact de pied
  de page, pas un problème de fraîcheur des données.
- **Piste ou Réflexion :** Réflexion — mais une réflexion privilégiée, puisqu'elle porte le NEQ et
  s'ancre sans ambiguïté sur le dossier cumulatif.
- **Tier de confiance :** **moyen**, et il faut être honnête sur pourquoi. La certification marque la
  **fin** du processus de francisation, pas le moment où l'entreprise a franchi 25 employés — le délai
  entre les deux peut être de plusieurs années. La date confirme donc « 25+ employés à cette date », pas
  « vient de grandir ». Pour la sphère traduction précisément, ça veut aussi dire que le besoin a
  peut-être déjà été servi.
- **Les deux listes sœurs, à ne pas négliger :**
  - **Liste des entreprises non conformes au processus de francisation** — besoin **aigu, daté et non
    servi** en traduction/francisation, avec une conséquence concrète (l'entreprise ne peut pas obtenir
    de subvention ni de contrat public). Tier **fort** comme signal de besoin, **faible** comme signal
    de croissance. C'est probablement la plus actionnable des trois pour la sphère #4.
  - **Liste des ententes particulières en vigueur** — entreprises ayant négocié un régime adapté,
    souvent des entreprises à forte composante étrangère ou multilingue.

---

## 3. AMF — bulletin hebdomadaire, section 6.6 « Placements »

- **Sphères servies :**
  - *Comptabilité / finance / fiscalité (#1)* — sphère cible. Une entreprise qui vient de lever du
    capital privé a un besoin immédiat de structuration fiscale, d'audit, de rapport aux investisseurs,
    souvent de direction financière externe.
  - *Juridique / conformité réglementaire (#11)* — un placement avec dispense crée des obligations
    d'information continues.
  - *Planification stratégique / conseil en gestion*.
  - *Financement / accès au capital* (déjà couverte, mais avec un angle différent).
- **Ce qu'elle apporte :** l'AMF publie, dans son bulletin hebdomadaire, la liste des placements
  effectués sous les dispenses du Règlement 45-106 — **nom de l'émetteur, montant, date**. C'est le
  complément naturel du RDPRM : le RDPRM capte le financement **par dette garantie**, celui-ci capte
  le financement **par capitaux propres privés**. Ensemble, ils couvrent les deux moitiés du signal
  financement, et ça arrive plus vite qu'une nouvelle publiée.
- **Bulk ou lookup :** bulk. PDF hebdomadaire structuré en tableau (extraction PDF requise, pas une API).
- **Coût :** gratuit.
- **Conditions d'utilisation :** 🚫 **bloquante.** Les conditions générales de l'AMF interdisent
  nommément d'« indexer dans une base de données » son contenu sans consentement écrit préalable
  (détail au volet légal ci-dessus). Ne pas activer sans entente. Explorer d'abord la voie SEDAR+ /
  autre membre des ACVM pour le même signal.
- **Fiabilité :** régulateur, donnée déclarée par l'émetteur sous obligation légale et sanction en cas
  de retard.
- **Piste ou Réflexion :** Réflexion. Nom de l'émetteur seulement, pas de NEQ → résolution via le REQ.
- **Tier de confiance :** **fort** — confirmation directe avec nom et montant précis, exactement le
  critère déjà retenu pour Investissement Québec.
- **Calibration nécessaire (bruit à exclure) :** la liste est **massivement dominée par des fonds
  d'investissement et des fiducies de placement** qui déclarent des souscriptions de routine. Sans un
  filtre qui écarte les émetteurs de type fonds pour ne garder que les sociétés opérantes, cette source
  produirait presque uniquement du bruit. C'est exactement la même mécanique que la distinction
  garantie de routine / garantie d'expansion au RDPRM — la source ne s'active pas sans cette règle.

---

## 4. Registre fédéral des lobbyistes — enregistrements (Commissariat au lobbying)

- **Sphères servies :**
  - *Relations publiques / communication corporative (#13)* — sphère cible, signal direct et le seul trouvé.
  - *Juridique / conformité réglementaire (#11)* — un enregistrement implique un enjeu réglementaire actif.
  - *Planification stratégique / conseil en gestion*.
  - *Financement / accès au capital* — l'ensemble de données inclut un indicateur de financement public
    reçu par le déclarant.
  - **Bonus structurel :** chaque enregistrement déclare des **sujets** (environnement, fiscalité,
    industrie, transport, etc.). Ces sujets se mappent directement sur les sphères, ce qui en fait une
    des rares sources qui indique elle-même quelle sphère elle alimente.
- **Bulk ou lookup :** bulk. Fichier ZIP de CSV (fichier primaire + fichiers secondaires pour les
  relations un-à-plusieurs) + dictionnaire de données XLS. Dernière mise à jour de l'ensemble :
  10 août 2026.
- **Coût :** gratuit.
- **Conditions d'utilisation :** Licence du gouvernement ouvert – Canada, usage commercial permis.
  Pas de zone grise ici.
- **Fiabilité :** organisme fédéral, déclaration obligatoire sous peine de sanction.
- **Piste ou Réflexion :** Réflexion. Nom de la société/organisation, pas d'identifiant d'entreprise.
- **Tier de confiance :** **moyen**. Un **nouvel** enregistrement d'entreprise (pas une mise à jour)
  indique une entreprise qui commence à défendre ses intérêts auprès du fédéral — souvent lié à une
  expansion, un projet réglementé, ou une demande de financement public.
- **⚠️ Point de conformité FALKYE :** ce jeu contient **des noms de personnes physiques** (lobbyistes,
  titulaires de charge publique). La règle de la section 6 de la charte (aucun enrichissement de contact
  individuel) impose d'écarter ces champs à l'ingestion, pas au calcul de pertinence. À traiter comme
  une exclusion universelle, au même titre que le bruit administratif du REQ.
- **Calibration nécessaire :** ne garder que les nouveaux déclarants et les nouveaux sujets ajoutés;
  exclure les grandes sociétés et associations enregistrées en permanence, dont les mises à jour
  périodiques ne signalent rien.

---

## 5. RACJ — Registre des titulaires de permis de détaillant d'alcool en vigueur

**Trouvée en cherchant la version provinciale des permis alimentaires. C'est la meilleure source
québécoise de cette recherche, et elle règle du même coup le problème légal et le problème de
couverture.**

- **Sphères servies :** *restauration / gestion alimentaire (#9)* et *commerce de détail* en premier;
  puis *agroalimentaire (#10)*, *construction / rénovation*, *immobilier / aménagement*,
  *entretien ménager*, *SST*, *sécurité physique*, *assurance / gestion des risques (#14)* — un
  nouvel établissement licencié doit s'assurer, s'aménager, s'équiper et s'entretenir.
- **Contenu :** titulaires d'un permis de **bar, restaurant, centre de vinification et de brassage,
  épicerie, vendeur de cidre** et permis accessoires.
- **Bulk ou lookup :** bulk, en trois formats (CSV 7 Mo, JSON 8 Mo, XLSX 4 Mo), plus l'API de
  Données Québec. **Mise à jour hebdomadaire** — dernière au 1er septembre 2026 au moment de la
  vérification.
- **Couverture :** tout le Québec.
- **Coût :** gratuit.
- **Conditions d'utilisation :** ✅ **CC-BY 4.0** affichée sur la fiche du jeu — usage commercial
  permis, attribution obligatoire, citation recommandée fournie par le diffuseur. Aucun blocage,
  aucune demande d'autorisation à faire. C'est le contraste exact avec l'AMF et l'OQLF.
- **Fiabilité :** Régie des alcools, des courses et des jeux; jeu conforme à 100 % aux lignes
  directrices de diffusion; diffusé depuis juin 2022, donc historique de fiabilité établi.
- **Piste ou Réflexion :** Réflexion — **mais avec le `Neq` du titulaire dans le dictionnaire de
  données.** C'est la deuxième source seulement, avec l'OQLF, à livrer le pivot québécois
  directement. Aucun appariement approximatif requis.
- **Champs qui font le travail :** `Neq`, `RaisonSociale`, `Titulaire`, `Adresse`, `Ville`,
  `RegAdmin`, `Categorie`, `PeriodeExplt` (annuelle ou saisonnière), et surtout **`Capacite`**
  (nombre maximum de personnes par localisation) — un **proxy de taille d'établissement**, chose
  rare dans les sources gratuites.
- **Tier de confiance :** **fort** pour une nouvelle inscription; **moyen** pour un changement de
  titulaire sur un établissement existant (remise en jeu des fournisseurs, mais pas de croissance).
- **Calibration nécessaire :** le registre est un **instantané des permis en vigueur**, sans date de
  délivrance. La détection passe donc par un **diff hebdomadaire** : nouveau `NoPermis` ou nouveau
  `Neq` = ouverture; `Neq` inchangé mais `Titulaire` différent = changement de propriétaire;
  **`Capacite` en hausse sur un établissement existant = agrandissement**, qui est probablement le
  signal le plus intéressant du lot et le plus facile à rater. Exclure les renouvellements et les
  variations saisonnières des permis marqués saisonniers.

---

## 6. Établissements alimentaires — Ville de Montréal (données ouvertes)

- **Sphères servies :** un cas d'école de source large qui traverse les sphères.
  - *Restauration / gestion alimentaire (#9)* — sphère cible.
  - *Agriculture / agroalimentaire (#10)* — le jeu inclut les transformateurs et distributeurs, pas
    seulement les restaurants.
  - *Construction / rénovation*, *immobilier / aménagement* — une ouverture implique presque toujours
    des travaux et un bail.
  - *Entretien ménager / conciergerie commerciale*, *SST*, *sécurité physique*, *commerce de détail*.
  - *Assurance / gestion des risques (#14)* — indirect mais réel : un nouvel établissement doit
    s'assurer. C'est le meilleur proxy trouvé pour cette sphère.
- **Bulk ou lookup :** bulk. CSV de 9,1 Mo (aussi GeoJSON et SHP), mis à jour aux quelques jours.
- **Le champ qui fait tout le travail :** `Statut`, avec la valeur **`En traitement` = « ouverture
  récente et en attente d'inspection »**, accompagné de `date_statut`. C'est un signal d'ouverture
  daté, pas un annuaire. La valeur `Fermé changement d'exploitant` donne un second signal distinct :
  changement de propriétaire, donc remise en jeu de tous les fournisseurs.
- **Coût :** gratuit.
- **Conditions d'utilisation :** CC-BY 4.0, adaptation et usage **commercial explicitement autorisés**,
  attribution obligatoire (y compris quand les données sont intégrées à une base de données qu'on
  possède — ce qui est exactement le cas de FALKYE). ⚠️ Une clause à lire deux fois : la Ville
  « proscrit tout usage malveillant ou abusif […] notamment toute tentative d'identifier une personne,
  **une entreprise** ou une organisation ». Les entreprises sont nommées dans le jeu lui-même, donc la
  clause vise vraisemblablement la ré-identification à partir de données anonymisées — mais c'est une
  ambiguïté à ne pas balayer, vu que « identifier une entreprise » décrit littéralement la fonction
  du produit.
- **Fiabilité :** Ville de Montréal, mandataire du MAPAQ sur son territoire. Réserve documentée par la
  Ville elle-même : les changements de propriétaire peuvent accuser plusieurs semaines ou mois de retard.
- **Piste ou Réflexion :** Réflexion. Identifiant local (`business_id`) non transférable, pas de NEQ.
- **Tier de confiance :** `En traitement` = **fort** (analogue direct au « nouvel établissement » du
  REQ). `Fermé changement d'exploitant` = **moyen**.
- **Limite de portée :** agglomération de Montréal seulement. Utilité résiduelle une fois le RACJ en
  place : Montréal couvre les établissements **sans permis d'alcool** (traiteurs, boulangeries,
  cantines, dépanneurs), invisibles au RACJ, et fournit une **date** (`date_statut`) là où le RACJ
  n'en a pas. Les deux sont complémentaires, pas redondantes.

### Le MAPAQ lui-même : vérifié, et écarté sous sa forme actuelle

La liste provinciale du MAPAQ (« Liste d'établissements sous permis ») a été vérifiée directement.
Trois obstacles, dont deux rédhibitoires :

1. **Accès automatisé interdit.** Le sous-domaine qui héberge l'outil (`web.mapaq.gouv.qc.ca`)
   bloque les robots. Même situation que le registre des licences de l'ACIA.
2. **Couverture incomplète, et c'est officiel.** La page gouvernementale sur les permis alimentaires
   le dit noir sur blanc : hors restauration et vente au détail, « **l'affichage du nom se fait sur
   une base volontaire** ». Une liste partielle par consentement ne peut pas servir de base de
   détection — l'absence d'une entreprise n'y veut rien dire.
3. **Régime de droit d'auteur par défaut**, puisqu'il s'agit d'une page ministérielle sans licence
   ouverte.

**Voie de contournement identifiée et documentée :** le MAPAQ publie dans son registre de diffusion
les réponses aux demandes d'accès à l'information, et une demande de 2026 a produit publiquement la
**liste complète des titulaires de permis pour le secteur de la transformation alimentaire (XLSX,
5 Mo)**. C'est une piste réelle : une demande d'accès à l'information est gratuite, produit un
fichier structuré, et sa diffusion publique règle en partie la question du canal. Ça reste un
instantané ponctuel, pas un flux — donc utilisable comme **socle de référence** à rafraîchir
occasionnellement (le mécanisme d'import manuel prévu en section 9 des specs), pas comme veille.

### Nouvelle-Écosse — *List of Licensed Food Establishments*

Vérifiée en téléchargeant le fichier réel, pas seulement la fiche descriptive.

- **Bulk ou lookup :** bulk, via l'API Socrata, en CSV / TSV / XML / RDF / RSS. Le fichier répond et
  contient des milliers d'établissements actifs. (Attention : le miroir sur le portail fédéral affiche
  une date de dernière mise à jour de juillet 2024, alors que la ressource elle-même répond en direct
  — se fier au fichier, pas au miroir.)
- **Champs réels :** `Facility`, `Permit Type`, `Permit Status`, `Facility Address`, `Facility Town`.
- **Le champ utile :** `Permit Status` avec la valeur **`Awaiting Application`**, l'équivalent
  fonctionnel du `En traitement` montréalais — établissement nouveau ou en cours de régularisation.
  `Permit Type` distingue restaurant, commerce, mobile, marché public et saisonnier.
- **Limites, sérieuses :** aucune date, aucun identifiant d'entreprise, et le nom est souvent une
  enseigne plutôt qu'une raison sociale. Le fichier est aussi **très bruité** pour un usage B2B — il
  mêle écoles, églises, légions, hôpitaux, cafétérias municipales et vendeurs de marché aux vraies
  entreprises. Un filtre par `Permit Type` et une exclusion des entités institutionnelles sont
  indispensables, sinon la majorité des « détections » ne seront pas des prospects.
- **Conditions d'utilisation :** ⚠️ **non vérifiées.** La page de licence des données ouvertes de la
  Nouvelle-Écosse bloque l'accès automatisé; impossible de confirmer le texte exact à distance. À
  lire manuellement avant activation — ne pas présumer qu'une licence provinciale ouverte autorise
  le commercial simplement parce que c'est l'usage courant ailleurs.
- **Valeur stratégique :** complète la source « contrats Nouvelle-Écosse » déjà active dans une
  province sans ancrage Piste, où chaque signal supplémentaire compte. Le voisinage immédiat contient
  aussi un jeu **Permanent Liquor Licenses** (équivalent NS du RACJ) et, pour l'Ontario, des jeux
  ouverts sur les **établissements de traitement des viandes sous licence provinciale** — deux pistes
  non explorées ici.

---

## Vérifié et écarté

**Registre des propriétaires et exploitants de véhicules lourds (RPEVL / CTQ)** — écarté comme source
de découverte. La consultation passe uniquement par le service en ligne « Dossier d'une entreprise ou
d'un individu », donc **il faut déjà connaître le nom** de l'entreprise. Règle de vérification #1 : un
outil de recherche par nom ne peut jamais servir de source de découverte. Réserve utile quand même :
il pourrait servir de source d'**enrichissement** sur une entreprise déjà détectée (sphères assurance,
SST, logistique), sur le même modèle que le mécanisme 2 du RDPRM.

**Registre des licences d'entreprises alimentaires de l'ACIA** — la donnée serait excellente
(pancanadienne, un champ vide retourne la liste complète des titulaires, couvre importation,
transformation et commerce interprovincial → sphères #6, #9, #10, #2). Mais le domaine hôte
`apps.inspection.canada.ca` **interdit l'accès automatisé par robots.txt**. Non utilisable tel quel.
Deux voies possibles, non explorées ici : export manuel ponctuel (cadre de l'import manuel de documents
sources déjà prévu en section 9 des specs), ou demande de données directe à l'ACIA.

**Base de données sur les importateurs canadiens (BDIC / ISED)** — vérifiée, mais faible. Ce n'est pas
un flux d'événements : c'est un instantané annuel (données 2023 au moment de la vérification) limité
aux entreprises qui totalisent 80 % des importations d'un produit — donc biaisé vers les gros. Le seul
signal exploitable serait un **diff d'une année à l'autre** pour repérer un nouvel entrant dans une
catégorie de produit. Latence d'un à deux ans, tier **faible**. À garder en réserve, pas à prioriser.

---

## Sphères où rien de valable n'a été trouvé

Dit franchement plutôt que comblé par une suggestion faible :

- **Service à la clientèle / support technique (#3)** — aucun signal distinct. Rien de public ne
  déclare qu'une entreprise développe sa fonction support. Le meilleur signal reste le titre de poste
  dans le recrutement, **déjà couvert** par le signal qualitatif de Guichet-Emplois. Recommandation :
  traiter cette sphère par une règle de mots-clés sur une source existante plutôt que par une source
  nouvelle.
- **Gestion documentaire / archivage (#5)** — rien de direct. L'OQLF est le seul angle trouvé, et il
  est indirect. La Loi 25 crée une obligation universelle, donc non discriminante : elle ne distingue
  aucune entreprise d'une autre.
- **Analytique d'affaires / gestion de données (#7)** — seulement les brevets CIPO, avec une couverture
  très mince chez les PME. Sphère à considérer comme non résolue.
- **Assurance / gestion des risques (#14)** — aucun signal direct. Ce qui existe est indirect :
  nouvel établissement alimentaire, nouveau permis de construction, nouvelle flotte au RDPRM. Décision
  à prendre : accepter que cette sphère soit alimentée uniquement par dérivation d'autres signaux, et
  le documenter comme tel plutôt que de chercher une source qui n'existe probablement pas.
- **Chaîne d'approvisionnement / achats (#2)** et **Import / export / douanes (#6)** — partiellement
  couvertes seulement, et par des sources contraintes (ACIA bloquée, BDIC faible). À reprendre.

---

## Ordre d'attaque suggéré

1. **RACJ (permis d'alcool)** — passé en tête après vérification légale. CC-BY, hebdomadaire, tout le
   Québec, **avec le NEQ** et un proxy de taille. Aucun obstacle d'aucune sorte. Débloque #9 et #14.
2. **CIPO / IP Horizons** — licence commerciale explicite, SFTP officiel, débloque quatre sphères
   d'un coup (#8, #12, #15, #11).
3. **Registre fédéral des lobbyistes** — licence ouverte, CSV, débloque #13 et #11, et les sujets
   déclarés se mappent directement sur les sphères.
4. **Établissements alimentaires Montréal** — complément du RACJ pour les établissements sans permis
   d'alcool, avec une date de statut que le RACJ n'a pas.
5. **Demande d'autorisation au gouvernement du Québec pour l'OQLF** — du délai, possiblement une
   redevance, et ça débloque #4 (traduction), la sphère en tête de tes priorités.
6. **AMF : ne rien ingérer.** Explorer d'abord SEDAR+ ou un autre membre des ACVM pour le même signal
   de placement privé; à défaut, entamer une demande de consentement écrit.

**Règle à ajouter au gabarit d'activation d'une source, valable au-delà de cette recherche :** avant
de scraper la page web d'un organisme, chercher s'il existe une version « données ouvertes » du même
registre — et si oui, **lire la variante de licence sur la fiche du jeu**, pas seulement constater
qu'il y en a une. Les permis alimentaires sont le cas d'école : page ministérielle = bloquée et
incomplète, jeu ouvert équivalent = CC-BY, hebdomadaire, provincial, avec le NEQ en prime.


---

# Pistes de sources pour les angles morts — 5 septembre 2026

Réponses aux critiques consignées aux spécifications, section 7bis. **Rien de ce qui suit n'est vérifié**
au sens des règles de ce document — ce sont des pistes à instruire, classées par ce qu'elles règlent.

## Pour le biais de sélection — atteindre les entreprises qui ne déclarent rien

**1. La bande d'effectifs du REQ — aucune recherche nécessaire, c'est déjà là.** Détaillé aux
spécifications. Gratuit, dans une source ingérée, sans autorisation nouvelle. **À faire avant de chercher
quoi que ce soit d'autre :** c'est la seule piste dont le coût est nul et qui atteint précisément les
entreprises invisibles.

**2. Les offres d'emploi — la vraie réponse, et elle est bloquée par une décision, pas par l'absence de
source.** TheirStack est identifié, retenu, et attend une clé **plus** l'autorisation de son domaine. Une
entreprise qui embauche laisse une trace publique, qu'elle soit réglementée ou non. C'est le signal qui
corrige le mieux le biais, et il est à portée.

*Piste secondaire à instruire :* Claude Code a signalé « Québec emploi » comme angle à valider par un
appel au Centre d'assistance au placement. Non instruit.

**3. Les registres des ordres professionnels — piste neuve, à vérifier.** Plusieurs ordres publient un
tableau des membres, parfois avec l'employeur. Une firme qui grandit y ajoute des membres. Si le tableau
est consultable en bloc et porte l'employeur, **c'est un signal de croissance pour exactement le segment
que le portefeuille rate** : services professionnels, sans permis ni contrat public.

À vérifier selon les règles habituelles — bloc ou consultation à l'unité, conditions d'utilisation,
présence de l'employeur. Réserve prévisible : plusieurs de ces registres sont conçus pour vérifier un
professionnel, pas pour être moissonnés, et leurs conditions pourraient l'interdire.

**Instruit le 5 septembre 2026 — voie fermée, à écarter définitivement.**

*Les tableaux sont des outils de consultation à l'unité.* Le bottin de l'Ordre des ingénieurs — plus de
77 000 membres, donc le cas le plus favorable — exige d'entrer un **numéro ou un nom de membre** avant de
retourner quoi que ce soit. Règle de vérification n° 1 : un outil de recherche par nom ne peut jamais
servir de source de découverte. Le motif est structurel, pas technique.

*Ce qui est publié en bloc ne sert à rien ici.* L'Office des professions publie sur Données Québec un jeu
« Statistiques concernant le système professionnel » : nombre de membres par genre, par région et par
ordre, au 31 mars de chaque année. **Aucune dimension entreprise, aucun employeur, aucun individu** — de
l'agrégat statistique annuel, inutilisable pour détecter la croissance d'une firme.

*Un obstacle de fond, qui aurait bloqué même en cas de succès.* Compter les membres d'un ordre par
employeur revient à agréger des données personnelles de professionnels nommés. La section 6 de la charte
écarte tout enrichissement portant sur des personnes. **La voie était doublement fermée.**

*Porte fermée pour un motif structurel, comme les agences de revenu — à ne pas revérifier ordre par
ordre.*

*Observation trouvée au passage, sans lien avec cette piste :* l'Ordre des ingénieurs exploite son propre
babillard d'emplois, réservé aux postes exigeant un membre et validé avant publication — un gisement
d'offres **spécifique au génie**, avec l'employeur nommé. Ça relève du signal recrutement, donc du
territoire de TheirStack, mais ça suggère que **plusieurs ordres et associations sectorielles exploitent
des babillards de niche** qui échappent aux agrégateurs généraux. À garder en tête si le signal
recrutement devait un jour être complété par secteur.

**4. Le RDPRM, déjà en place et sous-estimé dans la critique.** Une entreprise qui finance de l'équipement
grandit sans avoir besoin d'un permis ni d'un contrat public. C'est l'une des rares sources actives qui
échappe au biais administratif. Sa limite est ailleurs — coût à l'unité et import manuel.

## Pour le signal recrutement, au-delà de l'EIMT

Rien de nouveau à chercher : **TheirStack est la réponse**, et le blocage est double — clé et domaine.
Tant qu'il n'est pas branché, il faut dire honnêtement que le signal recrutement ne couvre que les
secteurs recourant aux travailleurs étrangers temporaires, plutôt que de le présenter comme général.

## Pour les palmarès

Aucune source à ajouter. **Reclassement** : de source de détection à source de corroboration. Leur signal
est vrai mais public et vieux d'un an; sa valeur est de confirmer une croissance détectée ailleurs, pas
de la découvrir.

## Pour les contrats publics

Aucune source à ajouter. **Règle de calibration à écrire au chantier 22** : le signal n'est réel que sur
un **premier** contrat, ou sur un contrat **disproportionné par rapport à la taille déclarée** — ce
second cas devenant calculable une fois la bande d'effectifs exploitée.

## Pour le financement privé — l'angle mort le mieux documenté et le moins traité

Une entreprise qui finance sa croissance par du capital privé, sans garantie au RDPRM, sans subvention et
sans contrat public, reste invisible. Deux voies existent et aucune n'est ouverte : **Crunchbase**,
décision budgétaire jamais tranchée; et le **bulletin de l'AMF**, contractuellement bloqué.

### Voie SEDAR+ — instruite le 5 septembre 2026

**SEDAR+ lui-même est fermé.** Le site public est protégé par une détection de robots active — la requête
est interceptée et renvoie une page de blocage, pas un refus de liste blanche. Et ses conditions
d'utilisation précisent que **la commission albertaine est l'autorité habilitée à accorder des licences à
des tiers** pour l'accès au site public. Autrement dit, l'accès automatisé à SEDAR+ passe par une licence
négociée, jamais par du moissonnage. Voie payante et administrative, pas gratuite.

**Mais une porte latérale existe : la Commission des valeurs mobilières de l'Ontario publie ces données en
données ouvertes.** Sa page de données ouvertes annonce un jeu de « rapports de placement avec dispense »
comportant la date de dépôt, **le nom de l'émetteur**, la date du premier placement, le capital levé en
Ontario et le nombre d'acquéreurs. C'est exactement le signal recherché, sous forme structurée et
publiée.

**La limite, et elle est réelle :** le jeu ne couvre que les déclarations où des **acquéreurs ontariens**
ont été identifiés. Une entreprise québécoise qui lève du capital exclusivement auprès d'investisseurs
québécois n'y figurera pas. La couverture serait donc **partielle et biaisée vers les levées plus
importantes**, le capital institutionnel étant concentré à Toronto — ce qui n'est pas rien, mais ne
couvre pas les premières levées locales, souvent les plus intéressantes pour FALKYE.

**Reste à vérifier, et je n'ai pas pu :** la licence exacte du jeu et sa fréquence de mise à jour. Le site
de la Commission bloque lui aussi l'accès automatisé, et la fiche n'a pas pu être ouverte. **À vérifier
manuellement avant d'y compter.**

**Équivalent en Colombie-Britannique :** la commission de cette province reçoit ces déclarations par son
propre portail depuis 2019, donc un jeu comparable pourrait exister — même limite géographique, cette
fois vers les acquéreurs de la Colombie-Britannique. Non instruit.

**Verdict.** La voie gratuite existe mais elle est **partielle**, et elle ne remplace pas ce que le
bulletin de l'AMF aurait donné pour le Québec. Elle mérite d'être branchée si sa licence le permet — un
signal partiel vaut mieux qu'aucun — mais elle ne referme pas complètement l'angle mort du financement
privé québécois. **La question de Crunchbase reste donc ouverte, et non tranchée par cette recherche.**

## Une piste hors des sentiers habituels, à peser plutôt qu'à adopter

Les **registres de transparence des certificats** consignent publiquement et gratuitement chaque
certificat émis pour un nom de domaine. Une entreprise qui ouvre une boutique en ligne, un portail client
ou un site de recrutement y laisse une trace **le jour même**, bien avant tout événement administratif.

Attrait réel : c'est probablement la source la plus **fraîche** qui existe, et elle échappe entièrement au
biais administratif. Réserves tout aussi réelles : rien n'y relie un domaine à une entreprise
québécoise — le rapprochement serait à construire — et le volume est énorme par rapport au signal. À
considérer comme une piste de recherche, pas comme un candidat.

## Ce qu'aucune source ne réglera

La question de savoir si un signal de croissance annonce vraiment un besoin de service ne se répond pas
en ajoutant des sources. Elle se répond avec de vrais utilisateurs et le taux de rejet.
