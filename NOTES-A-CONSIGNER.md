# Notes à consigner — tampon de travail

**Ce fichier n'est pas un document du corpus.** C'est un tampon : ce qui doit finir
dans le corpus atterrit ici **au moment où c'est trouvé**, et n'y reste que jusqu'à
la mise à jour de fin de tâche.

**La règle qu'il sert** *(méthode arrêtée le 11 septembre 2026)*. Le corpus s'écrit
**à la fin d'une tâche du plan**, en une seule demande de fusion — une entrée écrite
avec le résultat en main est plus juste qu'une entrée écrite avant, et une demande au
lieu de cinq allège le transport, qui se porte à la main.

**La condition, non négociable.** La mise à jour de fin de tâche porte **l'ensemble**
des points, pas ce dont on se souvient. *Une note différée qui se perd est pire qu'une
entrée écrite trop tôt — c'est le cas 15, et c'est exactement ce que cette méthode
risque de produire si elle est mal tenue.* D'où ce fichier : **rien ne dépend d'un
souvenir, et une note oubliée se voit parce que le fichier n'est pas vide.** Même
principe que le journal de repli — un endroit où ce qui risque de se perdre atterrit
avant d'être traité.

**Trois gestes qui vont ensemble.** *(1)* Chaque note s'annonce en une ligne dans le
tour où elle est prise. *(2)* Elle s'inscrit ici dans le même tour. *(3)* Le fichier se
vide en écrivant la mise à jour, jamais avant.

**L'exception.** Ce qui risque d'abîmer le produit s'écrit **tout de suite**, sans
attendre la fin de la tâche. Même test que pour un écart hors plan.

**Le format est un contrat.** Chaque note est un `### N<numéro> — <titre>` suivi d'une
ligne `- **Notée le** : AAAA-MM-JJ`. `outils/verifier-corpus.py` les compte et affiche la
plus ancienne sous chaque passage — *une note sans date est signalée comme telle, jamais
sautée en silence* **(l'absence de mesure n'est pas une mesure nulle)**.

**Comment lire ce fichier.** Aucun compte n'est tenu en tête : il se relit dans les
entrées *(un compte recopié est une promesse que personne ne tient)*. **Vide = rien en
attente**, et c'est le cas normal entre deux tâches.

---

## Tâche en cours — le premier cycle automatique avec livraison

### N1 — La borne de 500 rend le rattrapage du silence IMPOSSIBLE au-delà de 500
- **Notée le** : 2026-09-14
- **Destination** : `falkye/sources/fraicheur_datastore.py` *(la réserve, à côté de celle sur `_id`)*,
  fiches de source, et registre si la borne devient une décision.
- ✏️ **Ceci CORRIGE un avertissement que j'ai donné à Alexandre le 14 septembre au soir**, et qu'il a
  dit retenir pour lire le cycle du 15 : *« les deux connecteurs fédéraux vont marcher jusqu'à leur
  borne, `PAGES_MAX` × `TAILLE_PAGE` = 20 000 ; ni la durée ni le coût ne se comparent au régime ».*
  **C'est faux.** Les deux connecteurs passent `limite=self.limit`, et `limit` vaut **500** par défaut.
  *Le parcours `return` dès 500 enregistrements rendus* — **donc une seule page, et un cycle proche du
  régime.**
- ⚠️ **Et l'interaction des deux bornes produit un effet que je n'avais pas vu en les posant.**
  `ARRET_APRES_CONNUS = 200` s'évalue sur des références **consécutives** déjà connues. Donc :
  *cycle 1* — la base ne connaît presque rien, **500 rendus, arrêt sur la limite**. *Cycle 2* — le
  parcours repart du plus récent, croise les 500 d'hier, **s'arrête après 200 connues consécutives**,
  et **n'atteint jamais le 501ᵉ**.
- **Conséquence, à écrire telle quelle : le connecteur suit correctement ce qui est PUBLIÉ à partir de
  maintenant, et n'ira jamais chercher l'arriéré au-delà des 500 premiers.** *Le silence des semaines
  passées n'est pas rattrapé — il est abandonné en silence.*
- **Ce n'est pas forcément un défaut** — *un contrat de six mois n'est plus un signal de croissance,
  c'est le même raisonnement que la fenêtre de 30 jours du SEAO.* **Mais ce n'est pas une décision non
  plus : c'est un effet de bord de deux bornes posées séparément.** *À trancher, pas à corriger d'ici.*

### N2 — `contrats_federaux` n'est restreint au Québec à AUCUN étage
- **Notée le** : 2026-09-14
- **Destination** : fiche de source des contrats fédéraux, et registre *(à côté de D41)*.
- **Vérifié dans le code, trois étages, trois fois rien** : *(a)* le connecteur n'envoie **aucun
  `filters`** au datastore — il interroge les **1 313 621** contrats de tout le Canada; *(b)* il ne pose
  **jamais `region`** sur le `RawSignal`, et `appartient(None, …)` **retient** par principe; *(c)* le
  registre ne déclare **aucun `territoire`** pour cette source.
- **Comparer avec `subventions_federales`, qui fait l'inverse au même étage** : `province="QC"` par
  défaut, filtre envoyé à l'API *(`recipient_province`)*, et `region=rec.get("recipient_province")` posé
  sur le signal. *Deux connecteurs fédéraux écrits pour le même portefeuille, deux comportements
  territoriaux opposés, et rien ne le dit.*
- ⚠️ **Conséquence immédiate** : le profil n'ayant aucun territoire déclaré, **rien n'écarte une
  entreprise hors Québec** sur cette source. *Le produit est déclaré « foyer Québec » en Phase 1.*
- **Et le champ pour le faire existe et n'est pas capté** : `vendor_postal_code`, relevé par la sonde
  le 14 septembre. *La troisième colonne l'avait déjà trouvé.*
- ⛔ **NE PAS CORRIGER avant le cycle du 15 septembre — décision d'Alexandre, 14 septembre au soir, et
  le motif fait partie de la note.** *« Je veux voir ce que le cycle rend tel quel — si des entreprises
  hors Québec apparaissent, ça me dira combien, et c'est une mesure qu'on n'aura pas deux fois. »*
  **Le premier cycle non filtré est un instrument à usage unique** : une fois la restriction posée, la
  proportion hors Québec de cette source devient inobservable sans la retirer à nouveau. *Corriger tout
  de suite aurait effacé la mesure en même temps que le défaut.*

### N3 — Ce que le donneur d'ouvrage absent coûte à un utilisateur précis
- **Notée le** : 2026-09-14
- **Destination** : registre, **D43** — *l'entrée disait que le donneur n'existe pas; elle n'avait aucun
  exemple de ce que ça coûte.* Et chantier 21 pour la conséquence sur le portrait.
- **Deux cas d'usage d'Alexandre, sur le MÊME fait — un mandat d'architecture attribué par une
  municipalité.**
  - **Un fournisseur de mobilier de bureau.** *Le prospect est la firme d'architectes — l'entité que le
    produit sait créer.* **Trois faits convergent : le volume, la nature du mandat, l'embauche.** *Un
    contrat seul ne dirait rien; une embauche seule non plus.* **Ça marche de bout en bout aujourd'hui.**
  - **Un entrepreneur général.** *Le même mandat lui apprend qu'une municipalité prépare un chantier,
    des mois avant l'appel d'offres — la promesse du produit prise à la lettre.* **Mais son prospect est
    la MUNICIPALITÉ, et elle n'existe pas comme entité.**
- ⚠️ **Et ce n'est pas une dégradation gracieuse — c'est un portrait qui pointe la mauvaise porte.**
  *Alexandre estimait que « le grade le refléterait, A plutôt que AA ». La spéc. 8.x dit que le grade
  répond à « **correspond-il à CE profil?** » — A = « un signal pertinent pour votre secteur ».* **C'est
  exact, et ça ne dit rien du fait que l'entreprise NOMMÉE dans le portrait n'est pas le prospect.**
  **Le grade note la force d'un signal sur un prospect; il n'a aucun moyen d'exprimer « bon fait,
  mauvaise entité ».** *L'utilisateur fait la transposition lui-même, et rien dans le produit ne lui dit
  qu'il doit la faire.*
- **Ce que les deux cas ajoutent à la forme de la table** *(D48)* : **le code dit aussi LEQUEL des deux
  prospects le signal concerne.** *Mobilier → le fournisseur qui vient de gagner. Entrepreneur → le
  donneur qui prépare.* **Même signal, même code, deux prospects selon la sphère du lecteur.** *Donc la
  table n'est pas code → sphère : elle est **(code, rôle) → sphère**.*
- **Et le premier cas valide 7quater sur un usage réel** : *un code de services professionnels et un code
  de construction ne disent pas les mêmes besoins **parce qu'ils disent où le travail se fait** — dans des
  bureaux, ou sur un chantier.*

### N4 — Le mandat d'architecture comme signal précoce : le délai est MESURABLE, pas à affirmer
- **Notée le** : 2026-09-14
- **Destination** : mandat du chantier 22 *(un motif, avec sa calibration)*, et registre D48.
- **La lecture, et c'est peut-être la première réellement neuve que le code apporte** : *un mandat
  d'architecture annonce un chantier. Avant la classification, on ne pouvait pas le distinguer d'un
  contrat quelconque.*
- ⚠️ **« Six à dix-huit mois » est une estimation, pas une mesure** *(un chiffre recopié est une promesse
  que personne ne tient)*. **Et le délai est mesurable sur des données qu'on a déjà** : le SEAO porte les
  deux avis — le mandat de services professionnels, puis le contrat de construction — **et `buyer.id` est
  rempli à 100 %.** *Apparier par donneur d'ouvrage, comparer les dates d'attribution, rendre la
  distribution des délais.*
- **Ce que ça vaut** : *un motif « signal précoce » sans délai mesuré serait exactement la lecture
  disponible et inutilisable du motif « absence attendue » — il aurait l'air d'un outil.* **La mesure EST
  la calibration.**
- ⚠️ **Portée à déclarer d'avance** : nos 2 280 signaux ne suffiront pas — ils couvrent une fenêtre de
  30 jours. *La mesure se prend sur les fichiers source, sur plusieurs années, et elle est gratuite.*
- **Ne pas construire.** *Noté comme mesure possible, pas comme travail engagé.*

### N5 — L'EIMT fait 74,5 % du mur, et ses noms sont des RAISONS SOCIALES
- **Notée le** : 2026-09-14
- **Destination** : registre (D15), fiche de source de l'EIMT, mandat des chantiers 3 et 4.
- **Mesuré sur l'hôte** : des 8 395 entreprises sans NEQ, **6 258 sont EXCLUSIVES à l'EIMT (74,5 %)**.
  *Les deux palmarès en veilleuse, soupçonnés, pèsent 4,8 % à eux deux.* **La source qui fabrique 75 %
  de la base fabrique 75 % du mur.**
- ⚠️ **Et l'hypothèse de l'enseigne est FAUSSE.** *Mesuré sur le fichier réel `2026Q1`, 3 054 employeurs
  québécois, en empruntant les fonctions du connecteur :* **75,2 % portent une forme juridique en fin de
  nom** *(inc., ltée…)*, et les premiers de la liste sont des **sociétés à dénomination numérique**
  — `9164-4187 Quebec Inc`. **Ce sont des raisons sociales, pas des noms d'usage.**
- **Donc le second nom du REQ ne réglera PAS les trois quarts du problème.** *Il reste utile ailleurs;
  il ne s'applique pas ici.*
- **Ce que les noms montrent à la lecture** : `AER RIANTA INTL.` *(abréviation)*, `agileDSS`
  *(concaténation)*, `ALTEN Canada Inc.` *(filiale d'un groupe étranger)*. **Des écarts de forme qui
  placent le score flou dans les années 80 — sous le seuil de 92.**
- ✏️ **Mesuré à l'échelle le 14 septembre, sur `2026Q1` entier — 2 707 employeurs québécois
  DISTINCTS**, et l'hypothèse de l'enseigne tombe définitivement :

      forme juridique en fin (inc., ltée…)   74,9 %
      abréviation pointée dans le nom        45,4 %
      accents                                26,2 %
      tout en MAJUSCULES                     12,0 %
      dénomination numérique (9xxx-xxxx)     10,4 %
      « o/a » ou « / »                        0,3 %

  *Fermes, PME, CIUSSS, filiales de groupes étrangers — des **raisons sociales**.* **0,3 % portent la
  marque d'un nom d'usage.**
- ✅ **Et le filtre territorial de l'EIMT FONCTIONNE — vérifié, contrairement aux contrats fédéraux.**
  *Le fichier est fédéral et **65,3 % de ses lignes sont hors Québec** (Ontario 30,0 %,
  Colombie-Britannique 16,8 %, Alberta 10,3 %…). Mais le connecteur promeut `region=province`, le
  registre déclare `territoire: ['Québec']`, et `appartient` reconnaît « Quebec ».* **Les 65,3 %
  n'entrent jamais.** *Le module `territoire.py` a été écrit pour ce fichier précis — il tient.*
- ⚠️ **Le mur change donc de nature : ce n'est pas un problème de PONT, c'est un problème de SEUIL.**
  *58 % des échecs ont des candidats récupérés qui n'atteignent pas 92.* **La mesure qui manque est la
  distribution des meilleurs scores entre 80 et 92** — elle dirait ce qu'un second critère récupérerait.

### N6 — Rien ne réessaie de résoudre une entreprise qui ne reçoit plus de signal
- **Notée le** : 2026-09-14
- **Destination** : registre, **D15** — *c'est un mécanisme manquant, pas une explication.*
- **Vérifié dans le code** : `resolve_company` n'a que **deux points d'appel** — `engine.py` à
  l'ingestion d'un signal brut, et `manual_import.py`. **Aucune passe de re-résolution n'existe.**
- **Conséquence** : *une entreprise non résolue n'est réessayée que si un NOUVEAU signal la concerne.*
  **Si la source se tait, elle reste non résolue pour toujours — même quand le miroir a changé depuis.**
- **Mesuré** : les **313 « résolubles maintenant »** ont toutes été détectées le **6 septembre entre
  19 h 21 et 19 h 31**; le miroir REQ a été importé le **8 septembre à 17 h 02**. *Elles précèdent
  l'import de deux jours, aucun signal ne les a revisitées depuis.* **Le rejeu ne contredit donc pas la
  production — il révèle que la production ne repasse jamais.**
- *Le correctif évident — une passe de re-résolution après chaque import de miroir — n'est ni construit
  ni décidé.*

### N7 — Le chemin CSV de l'EIMT ne saute pas la ligne de titre
- **Notée le** : 2026-09-14
- **Destination** : fiche de source de l'EIMT. **Défaut latent, non corrigé.**
- `_read_xlsx` appelle `_find_header_row`, qui saute la première ligne — *un TITRE fusionné qui contient
  le mot « employeurs »*. **`_read_csv` ne l'appelle pas** : il passe le fichier à `csv.DictReader`
  et prend la première ligne pour l'en-tête.
- **Vérifié sur un fichier CSV réel du même jeu : la première ligne EST le titre.** *Le chemin CSV
  lèverait donc sur `resolve_columns`, ou pire, résoudrait mal.*
- ⚠️ **Il n'est jamais emprunté aujourd'hui** — le connecteur demande le XLSX d'abord. **Il le serait le
  jour où le diffuseur cesse de publier en XLSX**, c'est-à-dire exactement quand personne ne regarde.

### N8 — `Directed Contract` : un contrat de gré à gré n'est pas un contrat remporté
- **Notée le** : 2026-09-14
- **Destination** : mandat du chantier 22, avec les motifs · registre D48.
- **Mesuré sur les avis d'attribution de CanadaBuys** : `Directed Contract` = **456** occurrences sur
  les 3 661 avis dont le champ est rempli.
- **Pour un utilisateur, ce n'est pas le même fait.** *Un contrat remporté en concurrence dit que
  l'entreprise a soumissionné et gagné; un contrat de gré à gré dit que l'acheteur l'a choisie sans
  mise en marché — souvent parce qu'elle est seule à pouvoir le faire.* **Le second est un signal de
  position, le premier un signal de conquête.**
- **Le corpus n'en parle nulle part.** *Non construit, non tranché.*

### N9 — Le connecteur EIMT lit les quatre derniers trimestres, sur un ordre que personne ne garantit
- **Notée le** : 2026-09-14
- **Destination** : fiche de source de l'EIMT. *Constat, pas défaut — mais la réserve est la même que
  celle de `fraicheur_datastore`.*
- **Vérifié** : `cibles = resources[:1] if since is None else resources[:4]`. **Et le portail rend bien
  les ressources du plus récent au plus ancien** — `2026Q1`, `2025Q4`, `2025Q3`, `2025Q2`. *Le
  connecteur lit donc un an de trimestres, ce qu'il annonce.*
- ⚠️ **Mais cet ordre est une propriété de la RÉPONSE du portail, pas une garantie que le connecteur
  demande.** *Il ne trie pas. Le jour où le catalogue rend ses ressources dans un autre ordre, le
  connecteur lirait des trimestres de 2015 **sans jamais échouer** — même forme que la réserve sur
  `_id desc`, et même forme que Laval.*
- *Un tri explicite par trimestre coûterait trois lignes. Non corrigé.*

### N10 — L'adresse du REQ inscrite au registre est morte, et la vraie est derrière Cloudflare
- **Notée le** : 2026-09-14
- **Destination** : `docs/STATUT_RESEAU.md`, à côté de l'analyse du 31 août.
- **L'adresse `donneesquebec.ca/.../download/jeudonneesouvertes.zip` rend 404.** *Elle est périmée.*
- **La vraie, lue sur la fiche du jeu par l'API CKAN, est
  `registreentreprises.gouv.qc.ca/.../FichierDonneesOuvertes.aspx`** — et elle rend **403** depuis
  l'environnement de développement. *Exactement ce que le corpus documente depuis le 31 août : une règle
  Cloudflare visant les plages infonuagiques partagées.*
- **Conséquence pratique : l'archive du REQ ne peut être obtenue que depuis un navigateur.** *C'est ce
  qui fait de `req` une source `import_manuel`, et ça ne change pas.*

### N11 — Une correction qui s'annule en vérifiant vaut autant qu'une correction qui tient
- **Notée le** : 2026-09-14. **Formulation d'Alexandre, reprise telle quelle.**
- **Destination** : guide d'ingénierie — *à côté de « un instrument déclare sa provenance ».*
- **Deux fois le même jour, une hypothèse défendable a été vérifiée avant d'être rapportée, et elle est
  tombée.** *(1)* Le filtre territorial de l'EIMT : **65,3 % du fichier est hors Québec**, et tout
  indiquait le même défaut que les contrats fédéraux — *vérifié aux trois étages, il tient.* *(2)*
  L'ordre des ressources de l'EIMT : `resources[:4]` sans tri, tout indiquait une lecture de vieux
  trimestres — *vérifié au portail, il rend bien du plus récent au plus ancien.*
- **Dans les deux cas, le défaut rapporté aurait été faux, et il aurait coûté du travail réel** : une
  garde territoriale de plus sur une source déjà filtrée, un tri de plus sur un ordre déjà bon.
- **La règle. Le travail de vérification ne se juge pas à ce qu'il trouve.** *Une hypothèse écartée par
  la mesure a exactement la même valeur qu'un défaut confirmé — elle retire une fausse piste du plan.*
  ⚠️ **Et le contraire est le vrai danger : rapporter l'hypothèse sans la vérifier, parce qu'elle
  ressemble à un motif déjà vu.** *Trois fois aujourd'hui le motif « un ordre qu'on n'a pas demandé » est
  apparu — `_id desc`, Laval, les ressources de l'EIMT. **Deux étaient réels, un ne l'était pas.***

---

*Vide — les soixante-quatre notes des 13 et 14 septembre 2026 ont été portées au corpus
le 14 septembre. C'est le cas normal entre deux tâches.*

### N12 — Le score de 66 ne sort PAS des deux chaînes affichées, et l'instrument le cachait
- **Notée le** : 2026-09-15
- **Destination** : `falkye-journal-des-cas.md` (cas neuf), et `falkye-guide-ingenierie.md`
  (famille des instruments).
- **Les valeurs, mesurées localement, sans base ni hôte** :
  `normaliser("9309-3927 Quebec inc")` → `'9309 3927 quebec inc'` (20 car.);
  `normaliser("9309-3927 QUÉBEC INC.")` → `'9309 3927 quebec inc'` (20 car.); **égales**.
  `WRatio(norm, norm) = 100,0`. `WRatio(brut, brut) = 58,97`. `WRatio(norm, brut) = 48,78`.
  `process.extract` sur le dict à une entrée rend `[('9309 3927 quebec inc', 100.0, '1170123456')]`.
- **Aucune des trois valeurs n'est 66.** Un balayage montre qu'un score dans la bande 60-68 contre une
  requête de 20 caractères vient d'une chaîne cible de **1 à 4 caractères** — pas d'un nom.
- **Et le zéro est du même ordre** : `WRatio('ferme dallaire freres senc', 'ferme') = 90,0`.
  Un candidat qui partage la tête ne peut pas descendre sous 90. **Un 0 exige une chaîne VIDE** —
  or `nom_normalise` vide n'est récupérable ni par `GLOB 'ferme*'` ni par le repli `contains`, les
  deux requêtes portant sur ce même champ. *Le fait et le mécanisme se contredisent : donc une
  prémisse est fausse, et ce n'est pas le code du score.*
- ⚠️ **Ce que l'instrument cachait.** `comparaison()` affichait `entry.nom` — le nom BRUT — et
  jamais `entry.nom_normalise`, la seule chaîne que le score voit. La valeur en cause **était
  collectée dans le dictionnaire de paire (`"meilleur"`) et jamais imprimée.**
- **La règle à écrire** : *un instrument qui montre l'entrée et la sortie sans montrer ce qui est
  réellement comparé ne mesure pas — il illustre.* **Corollaire pour la famille des instruments :
  quand un outil affiche un score, il affiche les deux opérandes de ce score, telles qu'elles sont
  passées au scoreur.** Le correctif ajoute `norm dét.`, `norm mir.` (avec leur longueur) et un
  `recalcul` qui refait `WRatio` sur les deux formes affichées, avec un marqueur `← ÉCART` quand le
  score rendu par le moteur diffère du score recalculé. **L'écart localise la panne sans l'expliquer.**

### N13 — Le champ `Capacite` de la RACJ : 76,8 % sur 32 195 lignes, un des deux seuls indicateurs de NIVEAU
- **Notée le** : 2026-09-15
- **Destination** : `falkye-audit-et-mandat.md`, **à côté de D45**.
- **Le fait** : le registre des permis d'alcool de la RACJ porte `Capacite` rempli sur **76,8 % de
  32 195 lignes**. *C'est un nombre de places — donc une mesure de TAILLE d'établissement, pas un
  compte d'événements.*
- **Pourquoi ça mérite d'être à côté de D45** : le produit lit presque exclusivement des signaux
  d'ÉVÉNEMENT (un contrat obtenu, un permis délivré, une offre publiée). *Un événement dit qu'il se
  passe quelque chose; il ne dit pas à quelle échelle.* **`Capacite` est l'un des deux seuls
  indicateurs de NIVEAU que le produit puisse lire d'une source publique** — et il est là, gratuit,
  sous licence ouverte, sur un secteur entier.
- ⚠️ **Il ne vaut que pour la restauration et les débits de boisson.** *Une garde ne couvre que ce que
  la mesure couvrait* : ce n'est pas un indicateur de taille d'entreprise, c'est un indicateur de
  taille de salle. À écrire tel quel, pour que le prochain à lire ne l'étende pas.

### N14 — Deux jeux municipaux écartés, avec le motif, pour que personne n'y revienne
- **Notée le** : 2026-09-15
- **Destination** : `falkye-recommandations-sources.md`, section des refus.
- **Sherbrooke — permis de construction : ÉCARTÉ, source FIGÉE.** La ressource n'a pas bougé depuis
  **689 jours**. *Un jeu qui ne bouge plus ne produit aucun signal précoce — il produit un arriéré, une
  fois, puis plus rien.* **Et le coût n'est pas nul** : un connecteur branché dessus consomme un tour
  de cycle, une fiche de santé de source et une ligne de surveillance, pour zéro détection.
- **Montréal — liste noire des fournisseurs : ÉCARTÉE, dix lignes.** *L'effectif ne soutient aucune
  mesure* : dix lignes ne permettent ni d'évaluer un taux d'appariement, ni de détecter une rupture de
  source, ni de justifier une fiche. **Et le motif est plus fort que l'effectif** : une liste noire est
  un signal NÉGATIF, hors de la stratégie du portrait *(§6bis)* — le produit détecte une entreprise qui
  se développe, pas une entreprise qu'on exclut.
- ⚠️ **Le refus s'écrit avec sa DATE et son motif mesuré**, pas seulement avec son verdict — *sinon le
  prochain balayage du catalogue les repropose, et le travail se refait.* **Ils redeviennent
  examinables si le motif tombe** : Sherbrooke si la ressource repart, Montréal jamais (le motif est
  de nature, pas d'effectif).

### N15 — Le `MATRICULE` de l'OQLF EST un NEQ : un quatrième pont, avec la clé
- **Notée le** : 2026-09-15
- **Destination** : `falkye-sources-spheres-verifiees.md` et `falkye-recommandations-sources.md`.
- **Mesuré** : **99,7 % des `MATRICULE` de l'OQLF ont un format de NEQ valide** (dix chiffres).
  *L'OQLF ne nomme jamais ce champ « NEQ » — la ressemblance est de forme, et elle se vérifie
  à 99,7 %, ce qui ne laisse guère de place à la coïncidence.*
- **Ce que ça vaut** : 14 614 entreprises certifiées, avec leur **nom ET leur clé**. Ce n'est pas un
  répertoire de noms de plus, c'est un pont nom ↔ NEQ. **Inutile pour le mur actuel** *(0 appariement
  sur 8 395 — la population ne recoupe pas)*, **réel pour ailleurs**.
- ⚠️ **Et il porte une information que le REQ n'a pas** : une entreprise certifiée par l'OQLF est une
  entreprise de **50 employés et plus** soumise au processus de francisation. *C'est un indicateur de
  TAILLE* — le second des deux que le produit puisse lire, avec `Capacite` de la RACJ (N13).

### N16 — Le recouvrement des trois répertoires : 5 sur 8 395, et la forme reste bonne
- **Notée le** : 2026-09-15
- **Destination** : `falkye-recommandations-sources.md`, avec le chiffre.
- **Mesuré** : OPC permis **5** appariements sur 8 395 (0,1 %); OPC Parle consommation **0**; OQLF **0**.
- **Ce que ça infirme, et ce que ça n'infirme pas.** *La FORME du pont enseigne → raison sociale n'est
  pas infirmée* — elle n'a simplement pas été éprouvée : **la population ne recoupe pas.** Quelques
  dizaines de milliers de lignes dans des secteurs étroits (recouvrement, véhicules routiers,
  francisation) contre un mur fait à 74,5 % de l'EIMT.
- **L'argument qui reste entier** : si la forme est bonne, il faut aller chercher `AUTRES_NOMS` **au
  REQ, à l'échelle du registre entier** — 10 065 lignes coûtent une commande, 2,7 millions coûtent un
  import. ⚠️ **Mais pas avant que `nom_normalise` soit réparé** *(N17)* : on mesurerait un pont contre
  une colonne vide, et le zéro qui en sortirait serait attribué au pont.

### N17 — `nom_normalise` : la moitié du miroir est vide, et le code du dépôt ne peut pas l'expliquer
- **Notée le** : 2026-09-15
- ⚠️ **EXCEPTION À LA RÈGLE DU TAMPON** — celle-ci abîme le produit **maintenant**, et elle est écrite
  comme telle : *les 4 873 « candidats trop faibles », 58 % du mur d'appariement, sont probablement
  presque tous là-dedans.* **Des entreprises que le produit trouve, qu'il a sous les yeux, et qu'il
  compare à des chaînes mutilées ou vides.**
- **Destination** : `falkye-journal-des-cas.md` (cas neuf), `falkye-audit-et-mandat.md`.
- **Les faits mesurés sur l'hôte** *(Alexandre, 2026-09-15)* : **1 371 730 / 2 730 146 lignes (50,2 %)**
  ont un `nom_normalise` vide ou absent. Et `nom = '9309-3927 QUÉBEC INC.'` porte
  `nom_normalise = '9309 3927 quebec'` — **la forme juridique retirée d'un seul côté**, score 66,
  recalcul concordant.
- **Ce que le dépôt dit, et qui contredit la donnée.** `nom` et `nom_normalise` sont écrits **ensemble,
  dans la même instruction, depuis la même chaîne**, aux quatre seuls endroits qui les écrivent
  (`req.py` 469, 477-478, 869, 899). `normaliser` n'a **pas changé depuis le 3 septembre**
  (`git log --follow`, deux commits, fonction identique). Et elle ne rend vide sur **aucun** des noms
  relevés — même en simulant un mauvais encodage lu avec `errors="replace"`.
- ⚠️ **La contradiction, mesurée et non résolue.** Un score de 0 exige que les candidats récupérés
  portent une chaîne **vide** (`process.extract` sur cent valeurs vides rend `('', 0.0)`; sur des
  `None`, il les ÉCARTE). Or ils ont été récupérés par `GLOB 'ferme*'`, **qui porte sur cette même
  colonne**. *Une chaîne vide ne peut satisfaire ni ce filtre ni son repli.* **Donc le filtre et la
  lecture ne rendent pas la même valeur pour la même ligne** — et le défaut n'est pas dans la donnée,
  il est sous elle. **Aucune lecture de code ne tranchera ça; il faut lire la base.**
- **La règle à écrire, et elle est plus large que ce cas** : *quand le code ne peut pas produire la
  donnée observée, ce n'est pas le code qu'on relit une quatrième fois — c'est la prémisse « le code
  déployé est le code du dépôt » qu'on vérifie.* **C'est la même forme que le cas 35** (la #40
  fusionnée dont l'outil n'était pas sur l'hôte) : *rien n'a échoué, et c'est pour ça que c'était
  invisible.*
- **Ce que trois jours ont coûté** : le mur a été cherché **dehors** — enseignes, ponts, sources,
  seuil, récupération — alors qu'il était **dedans**. *Aucune de ces pistes n'était absurde; aucune
  n'aurait pu aboutir.* **Ce qui a ouvert la porte, c'est une contradiction interne** — un score
  impossible sur deux chaînes identiques — **pas une hypothèse de plus.**

### N18 — Aucun connecteur ne normalise le nom : 16 sur 16 le passent tel quel
- **Notée le** : 2026-09-16
- **Destination** : `falkye-guide-ingenierie.md`, et `falkye-audit-et-mandat.md` à côté de l'asymétrie.
- **Mesuré par AST sur les 16 expressions qui alimentent `nom_entreprise=` d'un `RawSignal`** :
  `chgt['nom']`, `employeur`, `brute.nom`, `entree['nom']`, `offre.entreprise`… **Aucune n'appelle
  `normaliser`, aucune ne retire quoi que ce soit.** *Un `.strip()` retire des espaces; il ne retire
  pas une forme juridique.*
- **Ce que ça décide, et c'est structurel.** La graphie des noms **n'est pas une décision du produit** :
  c'est une propriété de chaque source. *Donc « aligner le connecteur de l'EIMT » n'a pas de sens —
  il n'y a rien à aligner dans un connecteur qui ne transforme rien.* **Si une asymétrie existe entre
  le détecté et le stocké, elle vient du MIROIR, qui est le seul des deux côtés à transformer.**
- ⚠️ **Et ça rouvre la contradiction du 15 septembre par l'autre bout.** `normaliser` **ne retire pas**
  les formes juridiques non plus. *Donc ni le connecteur ni la fonction de normalisation du dépôt ne
  peuvent produire un `nom_normalise` amputé de `inc`* — **ce qui ramène, une troisième fois, à la
  prémisse « le code déployé est le code du dépôt » (N17).**

### N19 — Trois sources sur vingt-six portent une adresse; vingt-trois n'en portent aucune
- **Notée le** : 2026-09-16
- **Destination** : `falkye-chantier-2-sante-source.md`, et le guide (famille des instruments).
- **Mesuré** : 26 sources au registre, **3 adresses en tout**, dont **2 sans témoin** *(`req`, `rdprm` —
  toutes deux en `import_manuel`)*. La troisième, celle du Guichet-Emplois, est citée dans
  `falkye/sources/guichet_emplois.py`, donc éprouvée à chaque cycle.
- **Contrôle de tête, 2026-09-16** : `req` **200** *(adresse neuve)*, `guichet_emplois` **200**,
  `rdprm` **403**. *Le repli HEAD → GET est nécessaire : beaucoup de serveurs refusent `HEAD` tout en
  servant `GET`, et sans lui on déclarerait mortes des adresses vivantes.*
- **La règle** *(formulation d'Alexandre, retenue)* : *une adresse qu'aucun mécanisme n'appelle n'est
  jamais éprouvée.* **Deux adresses du REQ sont mortes sans que personne le sache, pour exactement
  cette raison.**
- ⚠️ **Mais le fait le plus lourd n'est pas celui-là.** *23 des 26 sources ne portent AUCUNE adresse.*
  **Rien ne casse — sauf qu'un humain qui cherche par où l'on accède à une source ne trouve rien là où
  il regarde.** *Le registre ne peut rien éprouver pour elles : ce n'est pas un taux d'échec de 0 %,
  c'est zéro mesure.*

### N20 — Pousser n'est pas ouvrir, et ouvrir n'est pas fusionner
- **Notée le** : 2026-09-16
- **Destination** : `falkye-journal-des-cas.md` (cas neuf), et `falkye-guide-ingenierie.md` — *à côté du
  cas 35, dont c'est la suite exacte.*
- ⚠️ **EXCEPTION À LA RÈGLE DU TAMPON** : c'est une faute de procédure qui se répète, et elle coûte du
  temps à chaque fois.
- **Le fait** : **trois fois le 16 septembre**, du travail a été poussé sur la branche sans qu'aucune
  demande de fusion soit ouverte. *La #49 avait été fusionnée à 00 h 42 au commit `1704222`; les quatre
  commits suivants existaient sur la branche, complets et testés, et n'allaient nulle part.*
- **Pourquoi ça ne se voit pas.** Le geste `git push` réussit, le journal affiche `→ branche mise à
  jour`, et **rien ne signale l'absence de demande**. *Le seul symptôme atteint Alexandre à l'autre bout :
  un outil absent de l'hôte* — **ce qui ressemble à une panne de déploiement, pas à une demande
  manquante.** Il a diagnostiqué la cause en lisant `ls -la outils/` : tous les fichiers portaient la
  même date, celle du dernier déploiement.
- **La règle, formulation d'Alexandre, à reprendre telle quelle** : *« Pousser n'est pas ouvrir, et
  ouvrir n'est pas fusionner. Tant que la demande n'existe pas, rien ne part. »*
- ⚠️ **Et c'est la MÊME forme que le cas 35**, ce qui en fait une famille plutôt qu'un incident :
  *rien n'échoue, chaque geste réussit, et l'écart n'apparaît qu'à l'autre bout de la chaîne.*
  **Trois maillons — pousser, ouvrir, fusionner, déployer — dont chacun réussit isolément pendant que
  la chaîne est rompue.**
- **Le correctif de méthode, pas de code** : *une tâche ne se déclare pas finie sur un `push` réussi.*
  **Elle se déclare finie sur le NUMÉRO d'une demande ouverte**, vérifié, et donné à Alexandre.
  *Un état vérifié au bout de la chaîne, pas un geste réussi au début.*

### N21 — Une adresse joignable de l'hôte peut être injoignable d'ailleurs, et l'inverse
- **Notée le** : 2026-09-16
- **Destination** : `falkye-guide-ingenierie.md`, **à côté de « hors bac à sable »** — c'est le même
  motif, appliqué au réseau plutôt qu'aux données.
- **Le fait** : l'adresse du REQ rend **200 depuis l'hôte** et l'a toujours fait; depuis le conteneur de
  développement, la page du Registraire rendait **403**. *Ce n'est pas une adresse qui a changé d'état :
  c'est deux origines qui reçoivent deux réponses.*
- **La règle** : **un code de retour est une propriété du COUPLE (adresse, origine), jamais de
  l'adresse seule.** *Un 403 relevé depuis un conteneur infonuagique ne dit rien de ce qu'un navigateur
  obtient, et un 200 relevé depuis l'hôte ne garantit pas qu'un connecteur automatisé passera.*
- ⚠️ **Conséquence pour `outils/adresses_sans_temoin.py`** : sa sonde doit être lue **avec l'origine
  d'où elle a tourné.** *Le même outil, lancé des deux côtés, rend deux relevés également vrais.*
  **Et c'est l'hôte qui fait foi**, puisque c'est de là que le produit lit.
- **Écart relevé en passant, une ligne, non instruit** : la sonde de l'hôte a rendu **dix** adresses,
  celle du conteneur **trois**. *Le fichier `falkye/registry/sources.yaml` du dépôt n'en porte que
  trois — vérifié par balayage du YAML brut.* **Donc les deux registres ne sont pas le même fichier**,
  et c'est la quatrième fois aujourd'hui que le chemin ramène à l'écart entre le code déployé et le
  code du dépôt *(N17, N18, N20)*. **À vérifier avant de se servir du chiffre de 23 sources sans
  adresse, qui vient du dépôt.**

### N22 — Le mur n'était pas la comparaison : l'entreprise n'est pas au miroir
- **Notée le** : 2026-09-16
- ⚠️ **EXCEPTION À LA RÈGLE DU TAMPON** — c'est le résultat qui referme trois jours de travail, et il
  change ce qu'il faut chercher.
- **Destination** : `falkye-journal-des-cas.md` (cas neuf), `falkye-audit-et-mandat.md`.
- **La trace d'un cas entier** *(`outils/trace_un_appariement.py`, 16 septembre)* : `9309-3927 QUÉBEC
  INC.` est **introuvable au miroir par les quatre chemins** — NEQ, nom brut exact, sous-chaîne
  `9309-3927`, nom normalisé exact. Et `nom_normalise GLOB '9309*'` comme `nom LIKE '9309%'` rendent
  **une seule ligne** sur 2 730 146.
- **Le moteur a fait exactement ce qu'il devait** : il a récupéré la seule ligne disponible —
  `9309-1319 QUÉBEC INC.` — l'a comparée à `9309-3927`, obtenu 66, et refusé. *C'est le bon
  comportement sur une base amputée.*
- **Ce que ça explique d'un coup** : **six hypothèses tombaient toutes pour la même raison.** *Le seuil,
  la normalisation, les ponts d'enseigne, la troncature de récupération, le champ `nom_normalise`, la
  symétrie des formes juridiques* — **on cherchait pourquoi la comparaison échoue, alors que le candidat
  n'existe pas.** Et ça explique la **médiane à 63,5 des dénominations numériques** : elles sont
  massivement absentes, et le meilleur candidat est toujours un homonyme partiel de la même série.
- **La règle, et c'est la vraie prise** : *avant de demander pourquoi une comparaison échoue, vérifier
  que les deux termes existent.* **Une distribution de scores répond « combien »; elle ne dit jamais
  que l'un des deux côtés est vide.** *Trois jours de mesures justes sur une question mal posée.*
- ⚠️ **Et la cause de l'amputation n'est PAS établie.** Trois possibles, trois remèdes opposés : le
  fichier source est incomplet, l'import filtre, l'import s'arrête. *`outils/audit_import_req.py` les
  départage sur l'archive.* **Ne pas conclure avant.**

### N23 — L'écart des registres est tranché : le dépôt et le produit lisent le MÊME fichier ici
- **Notée le** : 2026-09-16
- **Destination** : `falkye-guide-ingenierie.md`, à côté de N21.
- **Mesuré** *(`outils/quel_registre_est_lu.py`)* : dans le conteneur, `loader.REGISTRY_DIR` résout vers
  `/home/user/Observador/falkye/registry/sources.yaml` — **le fichier du dépôt lui-même**, même
  empreinte, **3 adresses**. *Il n'y a donc aucune divergence de ce côté.*
- **Ce qui reste à mesurer, et l'outil est fait pour ça** : le même relevé **sur l'hôte**. Le chargeur
  résout `Path(__file__).parent` — **donc il lit le registre À CÔTÉ DU PAQUET INSTALLÉ.** *Si `falkye`
  y est installé en copie (`pip install .`) plutôt qu'en lien (`pip install -e .`), le YAML lu est un
  instantané figé à l'installation, qui diverge à chaque fusion touchant le registre, en silence.*
- ⚠️ **Le chiffre de dix adresses n'est pas expliqué**, et il ne faut pas l'attribuer trop vite. *Mon
  chiffre de « 23 sources sans adresse » vient du dépôt et vaut pour le dépôt.* **Tant que le relevé
  de l'hôte n'est pas fait, aucun des deux chiffres ne décrit l'autre côté.**
- **La règle** : *un chargeur qui résout son chemin depuis `__file__` lit le paquet, pas le dépôt.*
  **La question « quelle version le produit lit-il » a une réponse différente de « quelle version
  avons-nous décidée », et rien dans le code ne les rapproche.**

### N24 — L'archive du REQ était supprimée par la chaîne, `if: always()`, pour un motif que la mesure dément
- **Notée le** : 2026-09-16
- **Destination** : `falkye-chantier-29-persistance.md` *(écrit)*, `docs/MIROIRS.md` *(écrit)*, et
  `falkye-journal-des-cas.md` pour la forme du défaut.
- **Ce qui la faisait disparaître** : `.github/workflows/miroir-req.yml`, dernière étape,
  `rm -f /opt/falkye/import/JeuDonnees.zip`, **avec `if: always()` — donc même quand l'import
  échouait.** *Le motif écrit à côté : « 267 Mo qui n'ont plus de raison d'être sur un disque de
  75 Go ».*
- **La mesure dément le motif** : **66 Go libres**, archive de **267 Mo**, soit ~7 Go par an au rythme
  de deux semaines. ⚠️ **Et le coût réel était ailleurs, invisible depuis le flux** : chaque mesure
  demandant l'archive obligeait à la retélécharger — *trois fois en deux jours, et on a changé de
  méthode chaque fois pour l'éviter.* **Un coût déplacé n'est pas un coût supprimé.**
- **La décision** *(Alexandre)* : on conserve, **avec la date dans le nom** —
  `JeuDonnees-2026-09-02.zip`. *Le blocage Cloudflare ne touche que le téléchargement, pas la
  lecture : une archive déposée est relisible indéfiniment.* **L'import reste manuel; les mesures
  cessent de l'être.**
- **Le revers, pris en connaissance de cause, et ce qui le neutralise.** *Une archive conservée
  vieillit, et rien ne le signalerait* — **c'est le motif de la journée : Laval figé, l'adresse de
  l'EIMT, la table de prix sans date. Un fichier figé qui ressemble à un fichier vivant.** La date
  dans le nom le rend **lisible sans qu'on ait à s'en souvenir**, *même forme que la table de prix
  datée et que la portée imprimée sous le chiffre.*
- ⚠️ **Trois règles tombées de là, toutes écrites dans `outils/archives_req.py`** : *(1)* la date vient
  du **nom**, jamais de `mtime` — *un `scp` réécrit la date de modification et l'archive paraîtrait
  fraîche de jours qu'elle n'a pas*; *(2)* une archive **sans date** n'est pas récente, elle est
  **d'âge inconnu** — l'absence de mesure n'est pas une mesure nulle; *(3)* **rien n'est purgé
  automatiquement** — *une rotation silencieuse recréerait le même défaut à l'envers, un fichier qui
  disparaît sans que personne l'ait décidé.* **L'inventaire rend la croissance lisible; purger reste
  un geste.**
- **Et la chaîne REFUSE désormais de partir si l'étiquette de la release ne porte pas de date.**
  *Déposer une archive sans date serait déposer un fichier d'âge inconnu qui ressemble à un fichier
  frais* — le refus coûte une seconde, le silence coûterait trois semaines.

### N25 — Le guide officiel du Registraire existe, il est dans l'archive, et personne ne l'avait lu
- **Notée le** : 2026-09-16
- **Destination** : `falkye-sources-spheres-verifiees.md` (fiche REQ), `falkye-guide-ingenierie.md`.
- **Le fait** : le jeu de données du REQ porte une **seconde ressource**, `Guide d'utilisation`, un PDF
  de 21 pages, **servi par Données Québec** (200, contrairement à l'archive elle-même). *Il documente
  les 37 colonnes d'`Entreprise.csv`, les 7 de `Nom.csv`, le schéma relationnel, et un lexique.*
- **Ce qu'il tranche en une phrase** *(page 16)* : *« Numéro de 10 chiffres attribué à chaque
  entreprise au moment de son immatriculation. **Les deux premiers chiffres correspondent à la forme
  juridique de l'entreprise et sont 11, 22 ou 33.** »* **Le préfixe du NEQ n'est pas un rang, c'est une
  CATÉGORIE** — ce qui change entièrement la lecture de la plage des absents.
- ⚠️ **Et il ne couvre pas tout ce que le fichier porte** : la borne haute observée est `8881817611`,
  donc un préfixe `88`, **hors des trois valeurs documentées**. *À relever, pas à lisser.*
- **Trois choses que le produit ignore et qui sont dans l'archive** :
  *(1)* **`DomaineValeur.csv`** — la table code → libellé de tous les domaines. *Le produit lit des
  codes nus depuis le début.* *(2)* **`COD_INTVAL_EMPLO_QUE`**, décrit comme *« ordre de grandeur du
  nombre d'employés au Québec »* — **un TROISIÈME indicateur de niveau**, sur le registre entier, à
  côté de `Capacite` de la RACJ et de la certification OQLF *(N13, N15)*. **Et celui-là couvre toutes
  les entreprises, pas un secteur.** *(3)* `IND_FAIL`, indicateur de faillite.
- **La règle** : *une source de données ouvertes publie souvent sa propre documentation comme une
  ressource à côté du fichier.* **La lire coûte dix minutes; ne pas la lire a coûté trois jours** —
  la plage `11`–`22` s'interprétait en une phrase.

### N26 — Le piège des deux bases, troisième occurrence, et cette fois il marchait par accident
- **Notée le** : 2026-09-16
- **Destination** : `falkye-guide-ingenierie.md`, *à côté de la règle du 9 septembre.*
- **Le fait** : `UnboundExecutionError` à l'étape 6 de `audit_import_req.py` — un `text()` n'a aucune
  métadonnée à router, et la session porte deux moteurs dont aucun n'est le défaut.
- ⚠️ **Ce qui est neuf, et plus inquiétant que la panne** : `trace_un_appariement.py` fait **quatre**
  `text()` par la même session et **n'a jamais levé**. *Il marchait parce qu'une requête ORM sur
  `REQEntry` avait déjà ouvert la connexion juste avant.* **Le code était faux et passait, par
  ACCIDENT D'ORDRE** — un réarrangement innocent l'aurait cassé, et la panne aurait semblé venir du
  réarrangement.
- **La règle, plus large que le cas** : *un code qui dépend d'un effet de bord d'ordre n'est pas un
  code qui marche — c'est un code qui n'a pas encore échoué.* **Corrigé aux cinq endroits**, par
  `session.connection(bind_arguments={"mapper": …})`, comme `falkye/cout_lectures.py` le fait depuis
  le 9 septembre.

### N27 — `COD_INTVAL_EMPLO_QUE` : le seul indicateur de niveau qui couvre le registre entier
- **Notée le** : 2026-09-16
- **Destination** : `falkye-audit-et-mandat.md`, **à D45**, à côté de N13 (`Capacite` de la RACJ) et
  de N15 (la certification OQLF).
- **Le fait** : `Entreprise.csv` porte `COD_INTVAL_EMPLO_QUE`, décrit par le guide officiel du
  Registraire *(§ 4.1)* comme **« ordre de grandeur du nombre d'employés au Québec »**, avec un domaine
  de valeurs dans `DomaineValeur.csv`. *Il est dans l'archive depuis le premier import, et le produit
  ne le lit nulle part.*
- **Ce qui le distingue des deux autres, et c'est décisif.** *`Capacite` de la RACJ ne vaut que pour la
  restauration et les débits de boisson; la certification OQLF ne marque que les entreprises de 50
  employés et plus soumises à la francisation.* **Celui-ci couvre le registre entier — 2,7 millions
  d'entreprises, toutes formes juridiques, tous secteurs.**
- **Pourquoi ça compte pour D45.** Le produit lit presque exclusivement des signaux d'**événement** :
  *un événement dit qu'il se passe quelque chose, il ne dit pas à quelle échelle.* **Un ordre de
  grandeur d'effectif, disponible sur chaque entreprise du miroir, est le premier indicateur de niveau
  qui ne dépende ni d'un secteur ni d'un seuil réglementaire.**
- ⚠️ **Trois réserves à écrire avec, parce qu'elles limitent l'usage** : *(1)* c'est un **ordre de
  grandeur**, pas un compte — une tranche, jamais un nombre; *(2)* il vient de la **déclaration
  annuelle de l'entreprise**, donc il vieillit au rythme de ce dépôt et non de l'activité réelle;
  *(3)* **son taux de remplissage n'est pas mesuré** — *l'absence de mesure n'est pas une mesure
  nulle*, et il faut le compter avant de s'en servir. **Rien n'est instruit ici : c'est un relevé, et
  la décision reste entière.**

### N28 — Le mur du registre est FERMÉ : le miroir est complet pour ce que la source publie
- **Notée le** : 2026-09-16
- ⚠️ **EXCEPTION À LA RÈGLE DU TAMPON** — c'est le résultat qui referme quatre jours de travail.
- **Destination** : `falkye-journal-des-cas.md` (le cas ouvert par N22, refermé ici),
  `falkye-audit-et-mandat.md`.
- **La mesure** : **96,6 % des 224 968 NEQ sans nom élu sont des personnes physiques exploitant une
  entreprise individuelle**, contre **0 % chez les présents**. *Le Registraire ne publie pas leur nom,
  et c'est légitime.* **Le miroir n'est pas amputé : il est complet pour ce que la source publie.**
- **Ce que ça referme, et il faut l'écrire pour que personne ne rouvre** : *les quatre hypothèses
  écartées les 15 et 16 septembre — le seuil, la normalisation symétrique, la ville, les ponts
  d'enseigne — portaient sur la population RÉELLEMENT ATTEIGNABLE.* **Il n'y a rien à remesurer.**
- **Et ce qui a tranché n'était pas une mesure de plus** : c'était **21 pages de guide dans l'archive,
  que personne n'avait ouvertes** *(N25)*. La plage `11`–`22` s'interprétait en une phrase de lexique.

### N29 — Le pont était dans le fichier depuis le premier import, et il a fallu sept hypothèses pour le voir
- **Notée le** : 2026-09-16
- ⚠️ **EXCEPTION À LA RÈGLE DU TAMPON.** **Cas neuf au journal** — *et Alexandre le demande « pas pour
  le défaut, pour ce qu'il a fallu pour le voir ».*
- **Destination** : `falkye-journal-des-cas.md` (cas neuf), `falkye-guide-ingenierie.md`.
- **Le défaut, en une ligne** : `_charger_index_noms` élisait **un** nom par NEQ et jetait les autres.
  **1 705 806 noms jetés à chaque chargement**, sur **1 138 322 NEQ portant plusieurs noms en vigueur —
  41,7 % du registre.**
- **Ce que ça coûtait, mesuré** : **2 217 des 8 395 non résolues (26,4 %) s'apparient EXACTEMENT à un
  nom jeté**, dont **98,8 % de sociétés par actions** et 0,7 % de personnes physiques. *`9224-5842
  Quebec inc` s'apparie à `Ferme M.G. Bellavance`; `9169-9587 Quebec inc` à `Ferme A. Lapierre & Fils`.*
  **Le nom numérique est la dénomination sociale élue; le nom parlant est celui qu'on jetait.**
  Pour l'EIMT seule : **1 837 réparations sur 6 258, 29,4 %** — *la source qui fabrique 74,5 % du mur
  est aussi celle qui profite le plus du correctif.*
- **CE QU'IL A FALLU POUR LE VOIR, et c'est ça le cas.** *Sept hypothèses, trois jours, toutes mesurées
  correctement, toutes tombées* : le seuil de 92, la normalisation asymétrique, le champ
  `nom_normalise` vide, la troncature de récupération, les ponts d'enseigne externes, la ville, la
  clientèle hors cible. **Aucune n'était absurde. Aucune ne pouvait aboutir.**
- **Les trois choses qui ont réellement fait avancer, et aucune n'était une hypothèse de plus** :
  *(1)* **une contradiction interne** — un score de 66 sur deux chaînes identiques une fois
  normalisées, impossible, donc une prémisse fausse *(N12)*; *(2)* **un cas entier plutôt qu'une
  distribution** — *un compte agrégé répond « combien », jamais « où »*, et c'est la trace d'un seul
  appariement qui a montré que le candidat n'existait pas *(N22)*; *(3)* **vingt et une pages de
  documentation dans l'archive, que personne n'avait ouvertes** *(N25)*.
- **La règle, et elle vaut plus que le correctif** : **quand plusieurs hypothèses bien mesurées tombent
  d'affilée, ce n'est pas la prochaine hypothèse qui manque — c'est que la question est mal posée.**
  *Le signal n'est pas l'échec d'une mesure : c'est la SÉRIE d'échecs.* **Trois de suite doivent faire
  arrêter de chercher des réponses et faire relire la question.**
- ⚠️ **Et un corollaire désagréable** : *le défaut était dans le code du produit, à l'endroit le plus
  ancien et le moins suspecté — le chargeur, écrit une fois, jamais rouvert.* **On a cherché dehors
  pendant trois jours ce qui était dedans depuis le début, deux fois de suite** *(N17 pour
  `nom_normalise`, N29 pour les noms jetés)*. **Ce n'est plus une coïncidence, c'est un biais :
  le code ancien est présumé juste parce qu'il est ancien.**

### N30 — Le NEQ est l'entité; les noms ne sont que des portes vers elle
- **Notée le** : 2026-09-16. **Formulation d'Alexandre, reprise telle quelle.**
- **Destination** : `falkye-specifications-produit.md` (section 9, le pivot), `falkye-guide-ingenierie.md`.
- **Le principe** : *« Une entreprise n'a pas plusieurs identités parce qu'elle a plusieurs noms. »*
  **Conséquence opératoire : l'ambiguïté se mesure sur les NEQ DISTINCTS, jamais sur les noms.**
  *Regrouper les candidats par NEQ AVANT de compter les écarts — si un seul NEQ sort, c'est résolu,
  quel que soit le nombre de noms qui y mènent.*
- ⚠️ **Et ce principe a trouvé un défaut dans le correctif du matin même.** La récupération cherchait
  bien dans `req_noms`, mais le score comparait la requête à la **seule dénomination sociale élue** :
  *`Ferme M.G. Bellavance` retrouvait le NEQ, puis se faisait comparer à `9224-5842 QUÉBEC INC.`.*
  **La porte était ouverte et le seuil infranchissable.** Corrigé : le score d'un NEQ est **le
  meilleur de ses noms**, et le classement porte sur les NEQ.
- **La leçon de méthode** : *un test qui vérifie la récupération ne vérifie pas la résolution.*
  **Le test du matin passait — il s'arrêtait à `candidats_par_nom`.** Un correctif se teste **bout en
  bout, sur la fonction que le produit appelle vraiment**, pas sur l'étage qu'on vient d'écrire.

### N31 — Deux bornes posées avec le correctif, et une distinction à ne pas perdre
- **Notée le** : 2026-09-16 *(décisions d'Alexandre)*
- **Destination** : `falkye-specifications-produit.md`, `falkye-audit-et-mandat.md`.
- **Borne 1 — les noms ANCIENS ne servent pas à apparier.** *« Une entreprise qui a changé de nom a
  souvent changé d'autre chose, et on apparierait juste en présentant faux. »* **À inscrire comme
  chemin de DERNIER RECOURS, à confiance plafonnée — et à ne pas construire.** *Le champ `statut` de
  `req_noms` est conservé pour que la décision reste révisable sans réimport.*
- **Borne 2 — le portrait affiche le NOM LÉGAL du registre, jamais le nom apparié.** *Le nom commercial
  vient à côté, pas à la place.* **`Ferme M.G. Bellavance` TROUVE `9224-5842 Québec inc.`; elle ne la
  remplace pas.**
- ⚠️ **La distinction qui gouverne les deux** : **résoudre l'identité et présenter les faits sont deux
  choses.** *Alexandre a hésité sur deux contrats du SEAO attribués sous deux noms du même NEQ : les
  joindre aide parfois — deux contrats en six semaines, c'est une entreprise qui accélère — et nuit
  parfois, quand les deux noms servent des activités différentes.* **Mais le choix n'est pas entre
  joindre et séparer : c'est entre joindre et NE RIEN AVOIR.** *Sans le NEQ, l'entreprise nommée
  autrement reste sans secteur, sans taille, sans adresse.* **Le NEQ résout l'identité; le portrait
  décidera de la présentation — c'est une décision du cerveau, pour le 22. Rien ne se ferme.**

### N32 — L'entonnoir : 92 sur 11 556, et personne ne sait ce qui bloque
- **Notée le** : 2026-09-16
- **Destination** : `falkye-audit-et-mandat.md` *(registre — c'est une décision ouverte, pas un fait)*.
- **Les chiffres** : **11 556 détectées, 8 395 sans identité (73 %), 3 161 avec un NEQ, ~92 vérifiées.**
- **Le corpus exige trois conditions** *(spec section 6)* : statut légal, signe d'activité, cohérence
  d'identité. **Le correctif des noms règle la troisième. Personne n'a mesuré laquelle des deux autres
  bloque, ni dans quelle proportion.**
- ⚠️ **Et c'est ça qui décide si le correctif rapporte.** *2 217 entreprises de plus avec un NEQ ne
  servent à rien si elles échouent ensuite sur la même chose.* **`outils/entonnoir_verification.py`
  mesure, à lancer APRÈS le réimport** — lancé avant, il mesure l'état qu'on s'apprête à changer.
- **Une distinction que l'outil tient et qu'un total effacerait** : `NON_VERIFIE` **n'est pas un
  échec**, c'est une entreprise qui n'est jamais passée par la vérification. *Les fondre ferait lire un
  blocage là où il n'y a qu'une absence de passage* — et les deux n'ont pas le même remède.

### N33 — Le réimport seul ne résoudra aucune des 2 218, et ça ressemblera à un échec
- **Notée le** : 2026-09-16
- ⚠️ **EXCEPTION À LA RÈGLE DU TAMPON** : *dit après le réimport, ce fait ferait conclure que le
  correctif a raté.*
- **Destination** : `falkye-audit-et-mandat.md`, **à D15** *(c'est le même mécanisme manquant que N6)*.
- **Le fait, revérifié dans le code le 16 septembre** : `resolve_company` a **exactement deux points
  d'appel** — `engine.py:339` à l'ingestion d'un signal brut, `manual_import.py:55`. **Aucune passe de
  re-résolution n'existe.**
- **Conséquence : le miroir portera les 1,7 million de noms, et le compte d'entreprises résolues ne
  bougera pas.** *Les 2 218 ne seront réessayées que si une source les renomme.* **Mesuré le lendemain,
  le gain sera proche de zéro — et ce ne sera pas le correctif qui aura échoué.**
- ⚠️ **C'est exactement la forme du piège de la journée** : *un mécanisme qui réussit, un effet qui ne
  se voit pas, et une conclusion fausse qui s'impose d'elle-même.* **Écrit dans la marche, au-dessus
  des étapes, pour que personne ne lise le chiffre sans lire ça d'abord.**
- **Ce qui le débloquerait** : une passe de re-résolution des `Company` sans NEQ. *Elle n'existe pas,
  elle n'est pas dans ce réimport, et elle demande de trancher un cas que la déduplication rend
  délicat* — **une entreprise qui gagne un NEQ déjà porté par un autre dossier doit être FUSIONNÉE,
  pas dupliquée.** *À instruire, pas à improviser.*

### N34 — La population non résolue GRANDIT : +536 en un cycle
- **Notée le** : 2026-09-16
- **Destination** : `falkye-audit-et-mandat.md` *(le coût du chantier 3+4)*, `falkye-chantier-2-sante-source.md`.
- **Mesuré** : **8 395 entreprises sans NEQ le 15 septembre, 8 931 le 16.** *Le cycle du matin en a
  ajouté **536**.*
- **Ce que ça dit, et c'est structurel** : **le mur n'est pas un stock, c'est un débit.** *Chaque cycle
  hebdomadaire ajoute des entreprises que le produit détecte et ne sait pas identifier.* **Le coût du
  chantier 3+4 ne se mesure pas à ce qu'il reste à réparer, mais à ce qui s'ajoute pendant qu'on
  répare.**
- ⚠️ **Et ça change la lecture de tous les chiffres de la journée** : *2 218 gains sur 8 931, ce n'est
  pas « un quart du mur réglé »* — c'est un quart du mur **au 16 septembre**, sur une population qui
  croît d'environ 500 par semaine. **Un pourcentage mesuré sur un stock mobile est daté, et doit se
  lire avec sa date.**

### N35 — Les 43 menacées : à vérifier après, et la distinction est tout
- **Notée le** : 2026-09-16 *(consigne d'Alexandre)*
- **Destination** : `falkye-guide-ingenierie.md` (famille des instruments), journal des cas si un
  basculement grave se produit.
- **La consigne, reprise telle quelle** : *« Il faudra vérifier qu'elles se sont bien dérésolues, et
  non qu'elles ont mal résolu. Une entreprise qui bascule vers une mauvaise réponse est pire qu'une
  qui bascule vers l'ambigu. »*
- **Pourquoi** : *une dérésolution se VOIT — l'entreprise redevient candidate, rien de faux n'est
  présenté.* **Une mauvaise résolution se présente comme un fait**, et rien dans le produit ne la
  distingue d'une bonne.
- **L'instrument** : `outils/temoins_resolution.py`, `--capturer` avant / `--verifier` après.
  ⚠️ **Il capture TOUTES les résolues, pas les 43** — *les 43 sont une prédiction tirée d'un
  appariement exact, et le moteur compare par score.* **Une garde qui ne surveille que ce qu'elle a
  prévu ne surveille rien.**
- ⚠️ **Et la réserve qui va avec** : *il compare un avant à un après; ni l'un ni l'autre n'est une
  vérité terrain.* **Un changement d'identité est un signal d'alerte, pas une preuve d'erreur — et une
  résolution inchangée peut avoir toujours été fausse.**

### N36 — Le cercle EST au corpus, et il y est décrit comme résolu par un mécanisme qui ne le fait pas
- **Notée le** : 2026-09-16
- ⚠️ **EXCEPTION À LA RÈGLE DU TAMPON.** ⚠️ **ET CECI CORRIGE MA PROPRE NOTE N33**, qui affirmait
  qu'aucune passe de re-résolution n'existait.
- **Destination** : `docs/ARCHITECTURE.md` *(hors corpus — à corriger)*, `falkye-audit-et-mandat.md`
  *(registre, décision neuve)*, `falkye-journal-des-cas.md`.
- **Le corpus le porte**, à `docs/ARCHITECTURE.md` (lignes 107-112), et il le porte comme **acquis** :
  > *« Après un import REQ, `falkye import-manuel fichier --source-id req` retraite par défaut TOUTES
  > les entreprises connues (pas seulement celles touchées par ce fichier) — un rafraîchissement du REQ
  > peut débloquer la résolution NEQ d'entreprises déjà détectées par SEAO/EIMT/etc. qui étaient
  > jusque-là `non_trouve`. »*
- ⛔ **Et c'est faux, sur deux étages distincts.**
  *(1)* **Le drapeau existe et ne re-résout pas.** `--reprocess-tout` *(défaut `True`)* appelle
  `generer_notifications`, qui parcourt les `Company` et les passe à
  `_traiter_entreprise_pour_profil` — **score, pertinence, notification.** *`resolve_company` n'y est
  jamais appelée*, et `company.neq` reste `NULL`. **Le retraitement renotifie; il ne réidentifie pas.**
  *(2)* **Et le chemin de déploiement ne passe même pas par là.** `outils/import_miroir_req.py` appelle
  `importer_fichier_source` **directement**, sans la commande CLI — *donc même le drapeau qui ne fait
  pas ce qu'il dit n'est pas actionné.*
- **Pourquoi c'est pire qu'une absence.** *Une lacune non documentée se découvre en la cherchant. Une
  lacune documentée comme résolue ne se cherche pas* — **le corpus répond à la question avant qu'elle
  soit posée, et il répond faux.** C'est la première fois qu'on trouve le corpus en défaut de cette
  manière : non pas incomplet, mais **rassurant à tort**.
- **La règle** : *un document qui décrit un COMPORTEMENT doit nommer la fonction qui le produit.*
  **« Retraite toutes les entreprises » ne se vérifie pas; « appelle `resolve_company` sur toutes les
  entreprises » se vérifie en une seconde** — et se serait démenti tout seul à la première lecture.

### N37 — La ligne de base du mur est irrécupérable après le réimport
- **Notée le** : 2026-09-16
- **Destination** : `falkye-guide-ingenierie.md` (famille des instruments).
- **Le fait** : la capture des témoins ne portait que les **résolues**. *Les 8 931 SANS NEQ n'étaient
  capturées nulle part* — et après le réimport, « ce que l'appariement rendait avant » **ne se
  recalcule plus** : le miroir aura changé.
- **Sans cet avant, on pourra dire combien se résolvent après, jamais de combien on a bougé.** *Un
  score de 88 qui passe à 94 et un score de 41 qui passe à 94 ne sont pas le même correctif.*
- **Le correctif** : `--capturer --non-resolues` relève le **meilleur score, le second, et le nombre de
  candidats** de chaque non résolue. ⚠️ **Le score, pas seulement le statut** — *un statut dit qu'on a
  échoué, un score dit de combien.*
- **La règle, plus large** : *avant toute opération qui réécrit une source de vérité, se demander ce
  qui ne se recalculera plus après.* **Ce n'est pas la même question que « qu'est-ce qui sera
  perdu » : rien n'est perdu ici — c'est la MESURE D'AVANT qui devient impossible, et elle n'existe
  que si quelqu'un l'a prise.**

### N38 — Une affirmation fausse produit une fausse attente; le silence n'en produit aucune
- **Notée le** : 2026-09-16. ⚠️ **EXCEPTION À LA RÈGLE DU TAMPON.**
- **Destination** : `falkye-guide-ingenierie.md` **en règle de premier rang**, et
  `falkye-journal-des-cas.md`.
- **Le fait** : `docs/ARCHITECTURE.md` affirme qu'un rafraîchissement du REQ *« peut débloquer la
  résolution NEQ d'entreprises déjà détectées […] jusque-là `non_trouve` »*. **Le mécanisme nommé
  renotifie et ne réidentifie pas** *(N36)*. **Conséquence directe et vérifiable : la phrase
  « les 953 signaux orphelins deviendront résolubles au prochain cycle » est FAUSSE.**
- **La règle, formulation d'Alexandre reprise telle quelle** : *« Le silence ne produit pas de fausse
  attente; une affirmation fausse en produit une. »* **Un trou dans le corpus se découvre en le
  cherchant. Une affirmation contraire aux faits empêche de chercher** — *elle répond à la question
  avant qu'elle soit posée, et elle répond faux.*
- ⚠️ **Ce qui rend le cas exemplaire, et pas anecdotique** : *le défaut n'était pas dans le code ni
  dans une mesure — il était dans la PHRASE qui décrivait le code.* **Le corpus a été, ce jour-là, la
  source de l'erreur plutôt que la garde contre elle.**
- **Le garde-fou qui en sort** *(déjà énoncé à N36, repris ici parce qu'il est général)* : **un
  document qui décrit un COMPORTEMENT nomme la FONCTION qui le produit.** *« Retraite toutes les
  entreprises » ne se vérifie pas; « appelle `resolve_company` sur toutes les entreprises » se
  vérifie en une seconde — et se serait démentie à la première lecture.*

### N39 — Le coût du repli par sous-chaîne rend le réimport rentable, indépendamment du gain
- **Notée le** : 2026-09-16 *(argument d'Alexandre, retenu)*
- **Destination** : `falkye-audit-et-mandat.md`, **à D14**.
- **Le raisonnement** : *chaque entreprise sans NEQ coûte ~8 900 lignes lues au repli par sous-chaîne,
  à CHAQUE cycle.* **Le réimport ne résout rien du stock, mais il réduit ce coût pour les signaux
  futurs** — une entreprise résolue au premier passage n'emprunte jamais le repli.
- **Donc le réimport n'est pas seulement un préalable** : *il paie sur le débit* — ~500 nouvelles
  entreprises par semaine, dont environ un quart se résoudront au lieu d'échouer, et chacune de
  celles-là économise 8 900 lignes par cycle, indéfiniment.
- ⚠️ **À rapprocher de D14, sans la trancher** : *le rendement du repli n'est toujours pas mesuré*
  (les colonnes `nb_abouties_*` sont `NULL` avant le premier cycle qui les écrit). **Cet argument
  parle du COÛT ÉVITÉ, pas du rendement du chemin — les deux se ressemblent et ne répondent pas à la
  même question.**

### N40 — La conservation n'est pas une option de conception : le schéma l'interdit
- **Notée le** : 2026-09-16
- **Destination** : `falkye-specifications-produit.md` (section 9, le pivot), `falkye-audit-et-mandat.md`.
- **La question posée** *(Alexandre)* : une entreprise qui gagne un NEQ **déjà porté** par un autre
  dossier — **fusion ou conservation?**
- **La réponse est factuelle avant d'être un choix.** `Company.neq` porte
  `unique=True` *(`falkye/models/company.py`, index `ix_companies_neq`)*. **Deux dossiers ne peuvent
  pas porter le même NEQ** : l'écriture lèverait `IntegrityError`. Et `resolve_company` fait
  `select(Company).where(Company.neq == neq).scalar_one_or_none()` — *avec deux lignes, il lèverait
  `MultipleResultsFound` à chaque signal ultérieur de cette entreprise.*
- **Donc « conservation » n'est pas une voie à peser contre la fusion : c'est un changement de schéma
  PLUS une réécriture du pivot.** *Le corpus pose le NEQ comme identifiant unique du dossier cumulatif
  (spec section 9); conserver deux dossiers reviendrait à retirer au NEQ ce qui en fait un pivot.*
- **Ce que la fusion COÛTE, et il faut l'écrire** : *le `nom_detecte` du dossier absorbé — le nom que
  la SOURCE employait réellement — disparaît du dossier.* **Il survit au journal de diagnostic**
  *(`journaliser_fusion_auto` capture id et nom avant la suppression)*, **mais plus personne ne le lit
  au dossier.** ⚠️ *C'est une perte de PREUVE d'usage : la façon dont une entreprise est nommée dans la
  vraie vie est précisément ce qu'on a passé la journée à chercher.*
- **Recommandation, à trancher par Alexandre** : **fusion**, parce que la conservation n'existe pas —
  **mais avec le `nom_detecte` absorbé PRÉSERVÉ au dossier survivant**, pas seulement au journal.
  *Sinon on jette exactement le genre de nom qu'on vient de passer trois jours à récupérer.*

### N41 — Deux familles d'imports dans le même fichier, dont une seule survit à l'unité
- **Notée le** : 2026-09-16. ⚠️ **EXCEPTION À LA RÈGLE DU TAMPON** — *deuxième occurrence du cas 26
  dans la même journée.*
- **Destination** : `falkye-journal-des-cas.md` **(cas 26, suite)**, `falkye-guide-ingenierie.md`.
- **Le fait** : `outils/import_miroir_req.py` importait `outils.archives_req` pour lire la date de
  l'archive. **À la main il marchait; sous systemd il est mort à la première seconde** —
  `ModuleNotFoundError: No module named 'outils'`.
- **Le mécanisme, et il est plus fin que « le chemin manque »** : `python outils/x.py` met **`outils/`
  lui-même** en tête de `sys.path`, **jamais la racine**. *`import falkye.x` y survit — le paquet est
  INSTALLÉ dans le venv et ne dépend pas du répertoire courant. `import outils.y`, lui, meurt.*
  ⚠️ **Deux familles d'imports dans le même fichier, dont une seule survit à l'unité** — et c'est ce
  qui rend le défaut invisible : *le fichier est plein d'imports qui marchent.*
- **Le correctif est dans la FORME D'INVOCATION, pas dans un chemin à poser.** `python -m outils.x`
  met le **répertoire courant** en tête, et `WorkingDirectory` le rend juste. *Ni `sys.path.insert` à
  recopier en tête de chaque script, ni `PYTHONPATH` à tenir à jour dans chaque unité : une règle.*
- ⚠️ **Et un second défaut, dans le MÊME correctif** : l'import fautif était **dans `main()`, après
  `parse_args`** — donc `--help` sortait avant de l'atteindre, et tout contrôle par `--help` aurait
  été vert. **Un import qui peut échouer doit échouer AU CHARGEMENT**, là où un test l'atteint.
- **La garde, mécanique** : `tests/test_unites_systemd.py` — *(1)* aucune unité ne lance un script par
  son chemin; *(2)* chaque module d'unité **s'importe vraiment**, dans un sous-processus, depuis la
  racine, **avec `PYTHONPATH` RETIRÉ de l'environnement** *(sans ça, le test hériterait du chemin de
  la session et passerait ici en échouant sur l'hôte — l'écart même qu'il ferme)*; *(3)* toute unité
  qui lance `-m` déclare un `WorkingDirectory`. **Vérifiée en la cassant : elle rougit.**
- **Et `falkye-migration.service` a été converti alors qu'il n'importe rien de `outils` aujourd'hui.**
  *C'est exactement pourquoi : le jour où il le fera, la panne serait à l'exécution, sur l'hôte, en
  silence.*

### N42 — `journalctl -u … -f` montre l'historique avant de suivre, et rien ne distingue les deux
- **Notée le** : 2026-09-16
- **Destination** : `docs/DEPLOIEMENT.md` *(hors corpus)* et `falkye-guide-ingenierie.md`.
- **Le fait** : l'import est mort à la **première seconde**, et le journal a montré pendant **une
  heure** la progression de l'import précédent. *Rien ne distingue les deux — mêmes messages, même
  unité, même format.* **Le suivi a donné l'impression exacte du succès.**
- ⚠️ **Ce n'est pas une inattention** : `journalctl -f` affiche les dernières lignes **puis** suit, et
  une unité `oneshot` qui meurt tout de suite n'écrit presque rien après. *L'historique occupe tout
  l'écran, et il est authentique — c'est un vrai import, simplement pas celui-là.*
- **Le remède** : `systemctl show -p InvocationID --value <unité>` puis
  `journalctl _SYSTEMD_INVOCATION_ID=$ID -f`. **Ne montre que l'exécution en cours** — *la confusion
  devient impossible, pas seulement improbable.* À défaut, `-n 0` coupe l'historique sans identifier
  l'exécution.
- **La règle** : *un flux qui mêle le passé et le présent sans les distinguer est un instrument qui
  ment par omission.* **Même famille que la table de prix sans date et que l'archive sans date : ce
  qui est figé doit se distinguer de ce qui est vivant.**

### N43 — La chaîne n'a JAMAIS copié les unités, et c'est une propriété de sécurité
- **Notée le** : 2026-09-16. ⚠️ **EXCEPTION À LA RÈGLE DU TAMPON.**
- **Destination** : `docs/DEPLOIEMENT.md` *(hors corpus)*, `falkye-chantier-29-persistance.md`,
  `falkye-journal-des-cas.md` **(cas 35, troisième forme)**.
- **Le fait** : `.github/workflows/deploiement.yml` fait un `rsync` du dépôt vers
  `/opt/falkye/code/`. **Les unités y arrivent bien — et systemd lit
  `/etc/systemd/system/`.** *Rien ne fait le pont.* **Depuis le premier déploiement, les unités de
  l'hôte sont ce que quelqu'un y a installé à la main, un jour.**
- ⚠️ **Et ce n'est PAS un oubli à réparer en ajoutant une ligne.** Le fichier de permissions le dit :
  `deploy` a le droit de **sept actions nommées** sur cinq unités, *« une chaîne compromise peut
  interrompre le service, jamais lire la base ni les clés d'envoi »*. **Lui donner le droit d'écrire
  dans `/etc/systemd/system/` lui donnerait celui de faire exécuter n'importe quoi en root** — et les
  unités, elles, lisent `/etc/falkye/falkye.env`. *La séparation est délibérée; la combler serait un
  recul.*
- **Ce qui manquait n'est donc pas la copie, c'est la DÉTECTION.** *Lire ne demande aucun privilège* —
  `systemctl cat` est ouvert à tous. **La chaîne peut constater la dérive même sans le droit de la
  corriger**, et c'est le seul trou réel.
- **La règle, et elle est plus large que systemd** : *quand une chaîne automatique n'a
  délibérément PAS le droit de corriger quelque chose, elle doit avoir le devoir de le CONSTATER.*
  **Sinon l'interdiction de corriger devient une interdiction de savoir.**
- ⚠️ **Et ma garde `tests/test_unites_systemd.py` ne l'aurait pas vu** *(Alexandre l'a relevé)* :
  **elle lit les unités du DÉPÔT.** *Elle vérifie ce qu'on a décidé, pas ce que l'hôte fait.* **Les
  deux gardes sont nécessaires et ne se remplacent pas** — l'une empêche d'écrire une mauvaise unité,
  l'autre empêche de croire qu'une bonne unité est installée.
- **L'instrument** : `outils/ecart_unites_hote.py`, à lancer **sur l'hôte**. Trois écarts distincts,
  *qui ne se soignent pas pareil* : unité absente, directives divergentes, **drop-in que le dépôt
  ignore** *(le cas 36 — `systemctl cat` les montre, lire le fichier seul les rate)*. Il compare les
  **directives**, jamais les commentaires : *une garde qui crie pour une reformulation finit par être
  ignorée.*

### N44 — L'import meurt à 7,2 Go, et le chiffre que j'avais annoncé était recopié
- **Notée le** : 2026-09-16. ⚠️ **EXCEPTION À LA RÈGLE DU TAMPON.**
- **Destination** : `falkye-journal-des-cas.md` (cas neuf), `docs/MIROIRS.md`, `falkye-guide-ingenierie.md`.
- **Le fait** : `falkye-miroir-req.service` tué par le gestionnaire de mémoire, **7,2 Go de pic sur
  7,7 Go disponibles**, cinq minutes après le démarrage, `status=9/KILL`.
- ⛔ **MA FAUTE, et elle a un nom dans le corpus.** J'ai annoncé *« la mémoire ne bouge pas, le pic
  reste à 3 535 Mo »* — **un chiffre recopié d'une docstring, jamais re-dérivé.**
  *« Un chiffre recopié est une promesse que personne ne tient »* — ma propre maxime, appliquée à moi.
- ⚠️ **Et le chiffre n'était compatible avec RIEN.** Mesuré localement et extrapolé linéairement à
  2 730 146 lignes : **index des noms 543 Mo · `resolues` 1 078 Mo · `lignes_entreprise` 1 669 Mo =
  ~3 300 Mo**, *avant* l'index des établissements (déjà chargé) et *avant* `lignes_etab` (pas encore
  construite). **Les 3 535 Mo ne pouvaient pas couvrir ce que la phase 1 construit** — personne ne
  l'avait re-dérivé depuis que le chiffre avait été écrit.
- **Ce qui accumule, et c'est STRUCTUREL, antérieur à mes changements.** La phase 1 tient
  **simultanément** : l'index des noms élus, l'index des établissements, `resolues` (2,7 M dataclasses)
  et `lignes_entreprise` (2,7 M `LigneSnapshot` portant chacun un dict de six clés). *L'import est mort
  AVANT `lignes_etab`, donc avant son propre pire moment.*
- ⚠️ **La redondance la plus coûteuse, et elle est gratuite à retirer** : `lignes_entreprise`
  **(1 669 Mo)** est **entièrement dérivable de `resolues`** par `_ligne_entreprise()`. *Deux listes
  portent la même donnée, l'une reconstructible à partir de l'autre.*
- **Et un doublement transitoire d'une ligne** : `_charger_index_noms` finit par
  `return {neq: nom for neq, (_, _, nom) in meilleurs.items()}` — **les deux dictionnaires sont vivants
  pendant la compréhension**, soit ~708 Mo de plus au moment précis du retour.
- **Ma passe des noms, elle, est bien en flux** *(lots de 20 000, `INSERT OR IGNORE`)* — **et elle n'a
  jamais tourné** : la mort est en phase 1, qu'elle suit. *La prévision sur MA passe était juste; elle
  ne disait rien du total, et c'est le total qui tue.*
- **La règle** : *une prévision de ressource ne se cite pas, elle se dérive.* **Et quand on annonce
  qu'un ajout ne change rien, il faut dire par rapport à QUOI** — *« le delta est nul » et « ça tient
  dans la machine » sont deux affirmations différentes, et j'ai laissé lire la seconde en n'ayant
  vérifié que la première.*

### N45 — Le miroir est intact, et deux chemins indépendants le disent
- **Notée le** : 2026-09-16
- **Destination** : `falkye-guide-ingenierie.md`.
- **Par le code** : la mort est survenue **en phase 1**, dans la boucle de lecture d'`Entreprise.csv`
  *(les avertissements `absent de Nom.csv` viennent de `req.py:505`, appelé là)*. **Or rien n'est écrit
  avant `executer_diff_groupe`**, qui vient après — *ni `REQEntry`, ni `EtatLigneSource`, ni l'état de
  diff.* **L'import a lu sans jamais écrire.**
- **Par l'horodatage** *(Alexandre)* : `miroirs.sqlite3` n'a pas bougé depuis 14 h 37, **deux heures
  avant** l'import de 17 h 52.
- ⚠️ **Et c'est exactement ce qui rendait la vérification nécessaire** : *« un import tué en cours
  laisse une base que rien ne distingue d'une base complète »*, écrit deux heures plus tôt. **Ici la
  réponse est bonne — mais elle a été VÉRIFIÉE, pas supposée, et par deux chemins qui ne dépendent pas
  l'un de l'autre.** *Un raisonnement sur le code et une date de fichier peuvent être faux séparément;
  ils ne le sont pas ensemble.*

### N46 — « Le delta est nul » et « ça tient dans la machine » sont deux affirmations différentes
- **Notée le** : 2026-09-16. **Formulation retenue par Alexandre comme valant au-delà du cas.**
- **Destination** : `falkye-guide-ingenierie.md`, **règle de premier rang**.
- **Le cas** : j'ai vérifié que ma passe des noms ne consommait rien de plus *(flux, lots de 20 000)*,
  et j'en ai conclu que l'import tiendrait. **Les deux propositions n'ont aucun rapport.** *Un ajout
  nul sur une somme déjà au-dessus de la limite ne sauve rien.*
- **La règle** : *quand on annonce qu'un ajout ne change rien, il faut dire par rapport à QUOI.*
  **Un delta se mesure contre un total, et le total doit être mesuré aussi** — sinon on rassure sur la
  moitié de la question, et c'est l'autre moitié qui tue.
- ⚠️ **Le même motif vaut pour le coût, le temps et le quota** : *« ça n'ajoute que deux requêtes »
  n'est une bonne nouvelle que si le total en supporte deux de plus.*

### N47 — Ce qui accumule réellement à l'import, mesuré ligne par ligne
- **Notée le** : 2026-09-16
- **Destination** : `docs/MIROIRS.md` **(section « ce qui accumule »)**, `falkye-chantier-1-quarantaine.md`.
- **Mesuré localement, extrapolé linéairement à 2 730 146 lignes.** ⚠️ *Extrapolation déclarée : la
  mesure porte sur 100 000 à 200 000 objets, et suppose la linéarité.*

  | structure | coût | quand |
  |---|---|---|
  | index des noms élus | **543 Mo** | avant la phase 1, vivant jusqu'à la fin |
  | … son doublement au retour | **+165 Mo** | transitoire — **corrigé** |
  | `resolues` | **1 078 Mo** | construit en phase 1 |
  | `lignes_entreprise` | **1 669 Mo** | construit en phase 1 |
  | archivage du snapshot | **+1 179 Mo** | transitoire, à chaque diff — **corrigé** |
  | `etats_precedents` | *non mesuré* | chargé dans `executer_diff`, 2,7 M lignes de la base |
  | index des établissements, `lignes_etab` | *non mesurés* | l'import est mort avant |

- ⛔ **ET MA PREMIÈRE PISTE NE MARCHAIT PAS.** *J'avais proposé de ne pas garder `lignes_entreprise`
  et de la produire en flux.* **Le moteur de diff la matérialise de toute façon** :
  `_dedoublonner_lignes` construit `lignes_par_cle`, un dictionnaire de 2,7 M entrées. **Passer un
  générateur n'aurait économisé que l'enveloppe de la liste (~22 Mo), pas les objets.** *Trouvé en la
  construisant, dit avant de continuer.*
- **La piste qui marche à sa place** : **ne pas garder `resolues`** — la phase 2 peut relire
  `Entreprise.csv` et rappeler `_resoudre_entreprise`. *Une seconde lecture du fichier contre
  1 078 Mo.* **Non construite : elle demande que `noms` et `etablissements` restent vivants en
  phase 2, ce qui est le cas, mais c'est un changement d'ordre à instruire.**

### N48 — La forme où la phase 1 n'accumulerait PAS : la jointure de fusion triée
- **Notée le** : 2026-09-16 *(question d'Alexandre : « est-ce qu'il existe une forme où la phase 1
  n'accumule pas du tout? »)*
- **Destination** : `falkye-chantier-1-quarantaine.md` *(c'est le moteur de diff)*, registre.
- **Oui, et elle est praticable ici parce que les DEUX côtés sont triables sur la même clé.**
  *`Entreprise.csv` est ordonné par NEQ — le corpus le dit déjà, à propos de `--limite` : « le fichier
  est ordonné par NEQ, ce n'est PAS un échantillon aléatoire ».* Et `EtatLigneSource.cle_naturelle` est
  indexé, donc lisible `ORDER BY` **sans tri en mémoire**.
- **Le principe** : lire les deux flux **en parallèle, en ordre de clé**, et décider ligne par ligne —
  *clé à gauche seule → disparition; à droite seule → apparition; des deux côtés → comparer les
  empreintes.* **Rien n'est tenu en mémoire au-delà de la ligne courante et des compteurs.**
- **Ce que ça coûte, et ce n'est pas rien** : *(1)* le moteur de diff est **générique** — sept sources
  l'utilisent, et toutes ne sont pas triées; il faudrait un chemin trié **en plus**, pas à la place.
  *(2)* Les seuils de quarantaine se calculent sur des **totaux** *(apparitions/disparitions rapportées
  au précédent)*, donc une passe de comptage avant la passe de décision, ou une décision différée.
  *(3)* L'archivage en flux est déjà fait, mais `apparitions` et `modifications` sont aujourd'hui des
  **listes rendues au connecteur** — il faudrait les rendre en flux aussi.
- **Estimation honnête : une semaine, pas une soirée.** *Et ce n'est pas un refactor cosmétique : c'est
  le passage d'un diff « tout en mémoire » à un diff « en flux », qui change la forme du moteur.*
- ⚠️ **À ne pas entreprendre avant d'avoir mesuré `Etablissements.csv`** : *si `lignes_etab` est petite,
  les correctifs locaux suffisent et la réécriture attend.* **Un chantier d'une semaine ne se décide
  pas sur une structure qu'on n'a jamais mesurée.**

### N49 — Mon inventaire n'explique que la moitié du pic, et mon correctif principal ne touche pas la phase qui a tué
- **Notée le** : 2026-09-16. ⚠️ **EXCEPTION À LA RÈGLE DU TAMPON** — *elle empêche une relance qui
  échouerait.*
- **Destination** : `falkye-journal-des-cas.md` *(le cas de l'OOM)*, `docs/MIROIRS.md`.
- **Le compte, posé franchement** : l'import est mort à **7 372 Mo, EN PHASE 1**. Mon inventaire en
  explique **3 390** — index des noms 543, établissements ~100 *(257 563 lignes, mesurées)*,
  `resolues` 1 078, `lignes_entreprise` 1 669. **Il manque 3 982 Mo, soit plus que tout ce que j'ai
  proposé de retirer.**
- ⛔ **Et mon correctif le plus gros ne s'applique pas là.** *L'archivage en flux (1 179 Mo) vit dans
  le moteur de diff, APRÈS la phase 1.* **L'import est mort avant de l'atteindre.** Sur la phase 1,
  mes correctifs de la soirée ne retirent que **165 Mo** *(le doublement de l'index des noms)*.
- **Deux causes plausibles à l'écart, et elles se départagent par la mesure, pas par le raisonnement** :
  *(1)* **`tracemalloc` compte les objets vivants, le système compte la RSS** — *l'allocateur de Python
  ne rend pas volontiers ce qu'il a pris, et 2,7 millions de petits objets créés puis jetés
  fragmentent.* **La RSS peut dépasser du double la somme des objets vivants sans qu'aucun bogue
  n'existe.** *(2)* **Mon extrapolation est linéaire, faite sur 200 000 objets** — à 2,7 millions, les
  redimensionnements ne se comportent pas pareil.
- **La décision : ni relancer, ni construire — MESURER.** *Décider sur une extrapolation quand une
  mesure coûte cinq minutes est exactement ce qu'on s'est interdit ce matin.*
  `outils/profil_memoire_import.py` refait la phase 1 seule, **sans base, sans écriture, sans diff**,
  et relève la **RSS du système** à chaque étape. **Lancé à 100 000 puis 500 000 puis 1 000 000 lignes,
  il donne une COURBE** — *et une courbe mesurée vaut mieux qu'une droite supposée.*
- **La règle, et c'est la troisième fois aujourd'hui qu'elle se vérifie** : *quand un total mesuré
  dépasse de beaucoup la somme de ce qu'on sait expliquer, ce n'est pas le total qui est faux — c'est
  l'inventaire qui est incomplet.* **Ajouter des correctifs à un inventaire incomplet, c'est corriger
  ce qu'on voit en laissant intact ce qui coûte.**

### N50 — La mesure retourne le diagnostic : c'est le moteur de diff, pas la phase 1
- **Notée le** : 2026-09-16
- **Destination** : `falkye-journal-des-cas.md` *(le cas de l'OOM, sa résolution)*, `docs/MIROIRS.md`,
  `falkye-chantier-1-quarantaine.md`.
- **Mesuré sur l'hôte** *(`outils/profil_memoire_import.py`)*, et la pente est **parfaitement
  linéaire** — 195 Mo par tranche de 250 000 lignes, deux fois de suite :

      au démarrage                           57 Mo
      index des noms élus (2 730 147 NEQ)   818 Mo   (+761)
      index des établissements (257 563)    922 Mo   (+104)
        … 250 000 lignes lues             1 117 Mo   (+195)
        … 500 000 lignes lues             1 311 Mo   (+195)
      lignes_etab                         1 311 Mo     (+0)

- **Extrapolé correctement : ~3 050 Mo pour la phase 1 complète.** *L'import est mort à 7 372.*
  **Donc ~4 300 Mo viennent du MOTEUR DE DIFF**, pas de la phase 1.
- ⛔ **Et ça renverse ma propre conclusion de l'heure précédente.** J'avais écrit que mon archivage en
  flux *« ne touche pas la phase qui a tué l'import »* — **je croyais la mort en phase 1.** *La mesure
  dit l'inverse : la phase 1 tient dans 3 Go, c'est le diff qui écrase la machine.* **Mes 1 179 Mo
  d'archivage frappent exactement au bon endroit**, et la piste `resolues` devient la moins utile des
  trois.
- **Deux relevés qui valaient la mesure à eux seuls** : *(1)* l'index des noms élus pèse **761 Mo, pas
  les 543 estimés — 40 % de plus**, et il est chargé en entier avant la première ligne
  d'`Entreprise.csv`; *(2)* **`lignes_etab` ne coûte RIEN** — zéro mégaoctet sur 257 563 lignes.
  *La crainte des 900 Mo était sans objet, et c'est la mesure qui l'a dit.*
- **La règle** : *une hypothèse sur l'emplacement d'un coût vaut exactement ce que vaut la mesure qui
  la porte.* **J'ai eu tort deux fois de suite sur le MÊME pic** — d'abord en annonçant 3 535 Mo
  recopiés, puis en plaçant la mort en phase 1. **Les deux erreurs venaient du même geste : conclure
  sur un raisonnement là où cinq minutes de mesure tranchaient.**

### N51 — L'état précédent du diff chargeait 2,7 M de dictionnaires pour en lire quelques milliers
- **Notée le** : 2026-09-16
- **Destination** : `falkye-chantier-1-quarantaine.md` *(c'est le moteur de diff)*, `docs/MIROIRS.md`.
- **Le défaut** : `executer_diff` chargeait `cle -> LIGNE ENTIÈRE`, **`donnees_normalisees` comprise**,
  pour toute la population de la source. *Pour le REQ : 2,7 millions de dictionnaires de six clés,
  relus de la base.*
- ⚠️ **Or ce champ n'est lu QU'À UNE LIGNE** *(`diff_engine.py`, calcul des `champs_changes`)* — et
  **seulement pour les clés dont l'empreinte diffère**, soit quelques milliers. **On chargeait 2,7
  millions de dictionnaires pour en lire quelques milliers.**
- **Le correctif, et il tient au même endroit que l'archivage** *(pas de changement d'ordre des phases
  à improviser, ce qu'Alexandre espérait)* : le dictionnaire ne porte plus que **`clé -> empreinte`**,
  une chaîne courte; le détail des seules clés modifiées est **relu par lots** ensuite
  *(`_champs_precedents`, lots de 1 000 — `IN` sans borne dépasse la limite de variables liées de
  SQLite, et l'erreur ne ressemble en rien à sa cause)*.
- **Et `.all()` disparaît** : il matérialisait la liste ENTIÈRE des lignes avant de construire le
  dictionnaire — *les deux structures vivantes en même temps, exactement comme l'index des noms.*
  Remplacé par un parcours en flux *(`yield_per`)*.
- ⚠️ **Le gain n'est pas annoncé, il se mesure** : `profil_memoire_import.py --etat-precedent req`
  charge **les deux formes l'une après l'autre** et rend la RSS de chacune. *Lire les DELTAS, pas les
  totaux — l'allocateur ne rend pas au système ce qu'il a pris, donc un delta de libération proche de
  zéro est normal et n'est pas une fuite.*

### N52 — Une garde écrite pour l'environnement a habillé un défaut du dépôt

**Le fait** *(2026-09-16)*. `outils/profil_memoire_import.py --etat-precedent req` a rendu, sur
l'hôte :

```
Import impossible (No module named 'falkye.models.etat_ligne_source').
```

**Ce module n'a jamais existé.** Le vrai est `falkye/models/etat_diff_source.py`. J'avais **déduit
le nom du module de celui de la classe** (`EtatLigneSource`) au lieu de le lire — *un chemin
inventé par symétrie, jamais vérifié contre le disque.*

⚠️ **Mais le nom faux n'est pas le pire.** Trois choses se sont additionnées, et seule la
troisième est intéressante :

1. **L'import était DANS une fonction**, après `parse_args` — donc ni le chargement du module, ni
   `--help`, ni aucun test ne l'atteignait. *C'est le cas 26 pour la TROISIÈME fois.*
2. Aucun test n'exerçait `--etat-precedent` : les quatre tests du fichier portent sur `_etape` et
   la lecture de la RSS. **Le chemin neuf n'était couvert nulle part.**
3. ⚠️ **Un `except ImportError` l'enveloppait** — écrit pour une dépendance tierce absente. Il a
   donc rendu un message d'environnement pour un défaut de code, et **a envoyé son lecteur
   chercher une panne de déploiement qui n'existait pas.**

**LA RÈGLE.** *Une garde ne couvre que ce que la mesure couvrait* — et une garde qui couvre trop
large **ment sur la cause**. Un `except ImportError` écrit pour les dépendances tierces doit
**refuser** les modules du dépôt : un `falkye.*` introuvable est un défaut du code, il se dit comme
tel, et il ne porte pas le même numéro de sortie.

**Le correctif est mécanique, pas vigilant.** `tests/test_imports_des_outils.py` parcourt l'AST de
chaque outil **à toute profondeur** — dans les fonctions, sous les `try` — et vérifie par
`find_spec` que chaque module `falkye.*` visé existe, puis que chaque nom importé y est défini.
*`find_spec` et jamais un import réel : importer exécuterait le module, et un environnement sans
`sqlalchemy-libsql` ferait rougir la garde pour une raison qui n'est pas la sienne.*

**Vérifiée en la cassant, deux fois** : mauvais module → rouge en nommant fichier et ligne; bon
module et mauvais symbole → rouge aussi.

### N53 — La date d'un fichier déployé est celle de son commit, pas celle de la copie

**Le fait** *(2026-09-16, apporté par Alexandre)*. Devant l'échec ci-dessus, la première hypothèse
a été une panne de déploiement — **parce que les fichiers de l'hôte portaient une vieille date.**
Ils ne la portaient pas par accident : `rsync` **préserve `mtime`**. *La date d'un fichier déployé
est celle de son dernier commit, jamais celle de la copie.* Le déploiement était à jour :
`grep -c "etat-precedent"` rendait 3.

**C'est la règle du matin, dans l'autre sens.** `outils/archives_req.py` lit la date d'une archive
**dans son nom, jamais dans son `mtime`** — parce qu'une copie fraîche d'un fichier ancien se
présenterait comme récente. Ici, l'inverse : **un fichier récemment copié se présente comme
ancien.**

**LA RÈGLE, dans sa forme générale.** *Le `mtime` répond à « quand ce contenu a-t-il été écrit »,
jamais à « quand est-il arrivé ici ».* Ce sont deux questions différentes, et lire l'une pour
l'autre se trompe **dans les deux directions selon l'outil qui a fait la copie.** Pour vérifier
qu'un déploiement a eu lieu, **on interroge le CONTENU** — un `grep` sur ce que la version neuve
est seule à porter — jamais l'horodatage.

### N54 — Le pic recalculé : l'addition tient, et le poste manquant se mesure à 59 Mo

**La mesure d'Alexandre sur l'hôte** *(2026-09-16)* : état précédent à **4 502 Mo** en ancienne
forme contre **527 Mo** en neuve.

**Son addition est la bonne, et meilleure que la soustraction.** `3 050 + 527 = 3 577 Mo`.
*Soustraire des 7 372 donnerait 3 397 — mais **7 372 est l'endroit où le processus est MORT, pas
le pic qu'il aurait atteint***. Le modèle additif le montre : `3 050 + 4 502 = 7 552`, soit 180 Mo
au-dessus de la mort. **Une valeur de mort est un plancher du pic, jamais le pic.**

**Le poste que l'inventaire ne couvrait pas : `lignes_par_cle`.** Le dict de dédoublonnage
(`_dedoublonner_lignes`) vit dans le moteur de diff, donc **hors du rejeu de phase 1**. Mesuré
sur 2 730 146 entrées, clés et valeurs déjà vivantes : **59 Mo**. *J'aurais annoncé ~280 —
l'estimation était 4,7 fois trop haute, et la mesure a pris trente secondes.*

⚠️ **Le poste qui aurait pu tout annuler, et pourquoi il ne le fait pas.** `_champs_precedents()`
relit les `donnees_normalisees` des clés MODIFIÉES, et `modifications` porte `champs_avant` ET
`champs_apres` : *si le réimport modifiait la moitié du miroir, le coût reviendrait au-dessus de
l'ancien.* **Il ne le fait pas, et la raison est structurelle** : `nom_normalise` **n'est pas dans
`champs`** (`_ligne_entreprise` : `neq`, `nom_entreprise`, `secteur_activite`, `adresses`,
`statut`, `date_derniere_maj`). *La colonne que le réimport répare ne traverse pas le moteur de
diff.* **Si elle y était, le correctif s'évaporerait** — c'est une propriété à ne pas perdre de
vue si `champs` s'élargit un jour.

⚠️ **Et la falaise : la quarantaine de volume.** `VOLUME_MODIFICATIONS` matérialise dans `detail`
**toutes** les apparitions et modifications en dictionnaires, plus l'archive. *Ce n'est pas une
pente, c'est une falaise* — et c'est un réimport qui change beaucoup de lignes qui la déclenche.
**Le même raisonnement la neutralise ici**, pour la même raison.

### N55 — Le repli silencieux, une porte plus loin : l'archive du diff

**Le fait** *(2026-09-16)*. Le correctif mémoire tient — **3,9 Go de pic contre 7,37**, proche des
3 640 calculés. **Mais l'import est mort ailleurs :**

```
File "falkye/diff_engine.py", line 419, in _archiver_snapshot
OSError: [Errno 30] Read-only file system: 'cache'
```

`FALKYE_DIFF_ARCHIVE_DIR` n'était posée nulle part, et le repli `./cache/diff_archive` est
**relatif au répertoire courant** — `/opt/falkye/code/cache` sous l'unité, que
`ProtectSystem=strict` rend en lecture seule.

⚠️ **C'est exactement le repli de la base, une porte plus loin** *(cas 41)* : un chemin par défaut
qui a l'air de marcher. **Et sur une machine où le répertoire courant est inscriptible, il n'aurait
rien dit du tout** — 679 Mo déposés à côté du code, perdus au déploiement suivant. *C'est ce que la
suite de tests faisait* : `cache/diff_archive/` existait dans l'arbre de travail, invisible parce
que `/cache/` est ignoré par git.

**Ce qui avait été mal jugé le matin.** Le défaut avait été noté, puis écarté « parce que
l'archivage n'est jamais appelé ». **Faux** : `executer_diff` appelle `_archiver_snapshot` sur le
**chemin accepté normalement** *(ligne 920)*, pas seulement en quarantaine. *Trois des quatre
appels sont des quarantaines, et c'est le quatrième qui tourne tous les jours.* **Compter les
points d'appel n'est pas mesurer lequel s'exécute.**

**LA RÈGLE, et elle est la moitié manquante du cas 41.** *Un refus posé au moment d'écrire coûte
tout le travail qui précède.* L'import a lu 2,7 millions de lignes, chargé l'état précédent,
calculé le diff — **puis** a refusé. `verifier_cible_archive()` est donc appelée **en tête
d'`executer_diff`**, et vérifie aussi que le répertoire est *inscriptible* : un chemin choisi mais
confiné échoue comme un chemin non choisi, et l'`Errno 30` ne nomme ni la variable ni la directive.

**Le fichier d'environnement, pas les unités.** Les quatre unités chargent déjà
`/etc/falkye/falkye.env` et déclarent toutes `ReadWritePaths=/var/lib/falkye`. *Une ligne au
fichier couvre les quatre; recopiée dans chacune, elle manquerait à la cinquième* — le cas 41, mot
pour mot.

⚠️ **Et un coût que personne n'avait chiffré : 679 Mo par exécution × 5 générations = jusqu'à
3,4 Go** dans `/var/lib/falkye`, à côté du miroir. *Trois commentaires d'unité disaient que
`/var/lib/falkye` ne portait que « le fichier des miroirs » ou « les miroirs ET l'état de diff ».
Ils étaient faux, et corrigés.*

### N56 — Les deux « hausses » étaient une population, pas une dégradation

**Le fait** *(2026-09-16)*. Après réimport, deux catégories du diagnostic montent : candidats faibles
`4 873 → 5 211` (+338), aucun candidat `148 → 346` (+198). *Lu comme une régression.*

**L'arithmétique tranche seule :**

```
somme des catégories AVANT : 8 395
somme des catégories APRÈS : 8 931
population « sans NEQ »    : 8 931   (les DEUX colonnes)
ce qui manque à AVANT      :   536
somme des deux hausses     :   536   ← identiques
```

**La colonne « avant » portait une ventilation de 8 395 en face d'une population de 8 931.** Les
deux hausses sont, à l'unité près, les 536 entreprises que cette ventilation ne comptait pas.
*Aucune entreprise n'a reculé.*

**LA RÈGLE.** ⚠️ **Deux colonnes côte à côte affirment une comparaison.** *Quand leurs totaux
diffèrent, elles comparent deux populations et non deux états* — et la différence se lit comme un
mouvement. **Un tableau avant/après doit porter la somme de ses lignes**, sinon la première chose
qu'il communique est fausse.

### N57 — Le pont existait, était interrogé, et n'ajoutait jamais personne

**Le fait.** Le miroir porte 1 505 879 noms de plus. Le diagnostic est **identique à l'unité** sur
trois catégories : 3 061 ambigus, 313 résolubles. *Pas « peu de gain » — zéro effet.*

**La cause est une ligne que j'ai écrite exprès, en la croyant prudente :**

```python
reste = max(0, limite - len(candidates))   # la borne s'applique au TOTAL
if reste: … req_noms …
```

⚠️ **Si la première requête rend déjà `limite` lignes, `reste` vaut zéro et pas un seul nom du pont
n'entre.** Or le préfixe de récupération est le **PREMIER MOT** du nom — « gestion », « les »,
« construction ». **La saturation n'est pas un cas limite : c'est le cas courant, et c'est
exactement là que le pont servirait.**

*Démontré par un test avant de le dire* : 2 050 entrées partageant le préfixe, une cible atteignable
uniquement par `req_noms` — absente des candidats.

**LA RÈGLE. Une borne qui protège du coût en supprimant l'apport protège du gain.** Le correctif
donne au pont une **part réservée** (un quart) et rogne la liste principale pour lui faire place :
le total reste borné, le coût ne bouge pas. *Et les candidats du pont valent mieux que ceux qu'ils
remplacent* — ils sont ciblés par leur préfixe, là où les derniers de la liste principale sont une
tranche arbitraire : **le `LIMIT` n'a pas d'`ORDER BY`**, donc sur 50 000 « gestion… » SQLite en
rend 2 000 au hasard de l'index. *Cette absence d'ordre reste un défaut ouvert.*

### N58 — Une ligne de contrôle qui ne s'imprime pas ne contrôle rien

**Le fait.** `req.py` journalisait « %s noms en vigueur indexés dans req_noms » par `logger.info`.
**Aucun programme de l'import ne configure de journal** — l'outil rapporte par `print()`. Sans
gestionnaire, le logger racine est à WARNING : *la ligne partait dans le vide.* La table portait
1 505 879 noms et `grep req_noms` ne rendait rien — **et son absence se lisait comme « la passe n'a
pas tourné »**.

**Le correctif ne déplace pas la ligne, il change ce qu'elle compte.** Le rapport imprime désormais
un `count(*)` **lu dans la table**, et non le total rendu par la passe : *« j'ai envoyé » et
« c'est là » sont deux affirmations différentes*, et entre les deux il y a les `OR IGNORE`, les
contraintes et les transactions non validées. Une table vide alors que les entrées sont chargées
crie désormais.

### N59 — La garde de ce matin ne couvrait pas les imports `outils.*`

**Le fait**, quelques heures après avoir écrit `tests/test_imports_des_outils.py` : un outil neuf
importait `outils.archives_req.resoudre_archive`. **Ce nom n'existe pas** — le vrai est `resoudre`.
*Le même défaut que le matin, déduit au lieu d'être lu.* **La garde ne l'a pas vu : elle ne
regardait que les modules `falkye.*`.**

⚠️ **Une garde ne couvre que ce que la mesure couvrait — y compris quand c'est la garde elle-même
qui a fixé la mesure.** Elle avait été écrite sur un défaut `falkye.*`, et avait pris cette portée
pour la bonne. *La question à poser en écrivant une garde n'est pas « est-ce qu'elle attrape ce
défaut-ci », c'est « où est la frontière que je viens de tracer sans la nommer ».*

### N60 — Un `LIMIT` sans `ORDER BY` rend le rejeu non reproductible

**Le fait** *(2026-09-16, relevé par Alexandre)*. `candidats_par_nom` bornait quatre requêtes par
`LIMIT` **sans aucun ordre**. Un `LIMIT` sans ordre ne rend pas « les 2 000 meilleurs » : il rend
**2 000 lignes au hasard de l'index** — et « au hasard » veut dire *susceptible de changer entre
deux exécutions*, après un réimport, un `VACUUM`, une insertion.

⚠️ **Deux passages du même rejeu pouvaient donner deux chiffres différents.** *Les 804 « résolubles
maintenant » étaient un chiffre qu'on ne pouvait pas re-obtenir* — et c'est sur eux qu'une passe
allait écrire dans la base.

**LA RÈGLE. Une mesure non reproductible n'est pas une mesure, c'est un tirage.** Et un geste
irréversible ne s'appuie jamais sur un tirage.

*Le coût est nul sur le chemin GLOB* : l'ordre demandé est celui de l'index, donc SQLite le suit
sans trier. Le repli par sous-chaîne balaie déjà la table entière; un tri borné à `limite` lignes ne
change pas son ordre de grandeur.

⚠️ **Et ce n'est PAS un classement par pertinence.** Trier par `nom_normalise` rend le tirage
reproductible, pas meilleur : sur 50 000 « gestion… », les 2 000 retenus restent une tranche
alphabétique arbitraire. **Rendre la récupération pertinente est un autre chantier, et il reste
ouvert.**

### N61 — La passe de reprise : conservation, et trois gardes avant le premier octet

**La décision d'Alexandre** *(2026-09-16)* : **conservation plutôt que fusion, parce qu'elle est
réversible.** *Deux dossiers séparés se fusionnent plus tard; deux dossiers fusionnés ne se séparent
pas.* `Company.neq` étant `unique=True`, un NEQ déjà porté ne peut pas être posé sur un second
dossier — et le chemin « naturel » aurait été de fusionner. **La passe ne fusionne rien** : elle
journalise un candidat de fusion `a_examiner`, et **les deux dossiers sortent intacts**. *Un test
porte cette décision et rougit si quelqu'un fusionne plus tard.*

**Trois gardes avant la première écriture.**

1. **Le rapport est le mode par DÉFAUT** — `--appliquer` est le seul chemin qui écrit. *Un outil qui
   écrit par défaut est un outil qu'on lance une fois de trop.*
2. **`--comparer N` montre des PAIRES** — nom détecté contre nom du registre, score, écart au
   second. *La dernière vérification avant un geste irréversible se fait sur des paires, jamais sur
   un total : un score de 100 sur deux raisons sociales différentes est une fausse résolution, et
   c'est la seule chose qu'un total ne montre pas.*
3. ⚠️ **L'instantané d'avant précède le commit, et s'il ne peut pas s'écrire, RIEN n'est modifié.**
   *Sans lui, « réversible » est une intention.* C'est le défaut du chemin d'archive du diff, une
   table plus loin.

**La décision passe par `neq_retenu`**, la fonction que le produit appelle — *une règle recopiée
mesurerait sa propre copie.*

### N62 — La garde des imports a payé son écriture le jour même

En écrivant la passe, j'ai importé `falkye.sources.req._enrich_from_req`. **Il vit dans
`falkye/resolution.py`.** *Troisième déduction de nom en deux jours* — et cette fois
`tests/test_imports_des_outils.py` l'a nommée, fichier et ligne, **avant l'hôte**. C'est la
première fois qu'une garde de cette session attrape un défaut que j'étais en train de commettre
plutôt qu'un défaut déjà payé.

### N63 — La vérification faite d'avance répond à l'état d'avant

**Le fait** *(2026-09-16, 19 h 03)*. La passe de reprise est morte sur
`UNIQUE constraint failed: companies.neq`, transaction annulée en entier — **rien posé sur les 736**.

**La cause, nommée par Alexandre avant moi.** La disponibilité du NEQ était vérifiée contre les
dossiers **EXISTANTS**, jamais contre **ce que la passe elle-même allait poser**. *Deux dossiers du
lot visant le même NEQ libre : le premier le prend, le second viole la contrainte.*

⚠️ **Et le rapport le montrait déjà.** 69 NEQ déjà pris, **tous des doublons de graphie** —
« Annexair inc. » contre « Annexair Inc ». *Si la base porte ces doublons, le lot en porte aussi* —
personne ne l'avait lu ainsi, moi le premier. **Un rapport qui contient la réponse ne la donne pas
pour autant.**

**LA RÈGLE. Une vérification faite d'avance répond à l'état d'avant, jamais à celui du moment où
l'on écrit.** Deux correctifs distincts, et il en fallait deux :

1. **Les collisions internes au lot, résolues AVANT l'affichage** — pas au moment de poser. *« Le
   premier arrivé » serait un ordre d'itération, donc un tirage* — et `ORDER BY` a été posé le matin
   même pour qu'un geste irréversible n'en dépende pas. Ici la règle est nommée, **visible dans le
   rapport**, et rend la même chose à chaque exécution.
2. **La disponibilité re-vérifiée au moment de poser** — pour l'autre cas, celui qu'aucun calcul
   d'avance ne couvre : *un cycle de production qui prendrait ce NEQ entre le rapport et
   l'écriture.* Plus un `flush()` par ligne, pour que la contrainte, si elle parle, nomme **une**
   ligne au lieu d'annuler tout.

**L'échelle du gagnant n'est PAS neuve.** `falkye/dedup_entreprises.py` la pose déjà pour le cas
analogue : *« le PRINCIPAL est toujours le dossier le plus ANCIEN (`first_detected_at`) »*. En
inventer une seconde ferait dépendre l'identité d'une entreprise **de la table par laquelle on
arrive**.

⚠️ **Et l'ancienneté n'est pas la vérité** — le dossier le plus vieux peut être le plus mal saisi.
Mais ce choix ne décide pas quel nom est juste : il décide **qui porte le NEQ pendant qu'un humain
regarde la paire**. *C'est la conservation qui rend ce choix bon marché* : le perdant n'est pas
perdu, il est journalisé. **Le modèle choisi hier a payé aujourd'hui.**

### N64 — Les doublons de dossier, et la famille que la contrainte rend invisible

**Demandé par Alexandre** *(2026-09-16)* : *« Ne le corrige pas. Mesure-le. »* `outils/
doublons_entreprises.py` ne fait que mesurer — aucune écriture, aucune proposition.

**Trois familles, et la troisième est celle que personne ne pouvait voir.**

1. **Graphie identique** — même `nom_detecte_normalise`, après retrait de casse, accents et
   ponctuation.
2. **Graphie proche, les deux sans NEQ** — mesurée avec `trouver_meilleur_candidat_fusion` et **les
   seuils du produit** (90/95). *Une règle recopiée mesurerait sa propre copie.*
3. ⚠️ **Un dossier RÉSOLU et un NON RÉSOLU.** `Company.neq` est `unique=True`, donc **deux dossiers
   résolus ne peuvent pas être doublons — la contrainte l'interdit.** *Mais un résolu et un
   non-résolu cohabitent sans rien violer*, et c'est exactement ce que la passe a trouvé.

**LA RÈGLE. Une contrainte d'unicité empêche une classe de défaut ET la rend invisible.** Ce qu'elle
interdit n'arrive jamais; ce qu'elle laisse passer n'est plus surveillé par personne, *parce qu'on
croit la contrainte responsable du sujet entier.*

⚠️ **La famille 2 sous-compte, et c'est écrit dans l'outil** : la fonction rend le MEILLEUR
candidat, donc un groupe de trois est vu comme des paires. *Le chiffre est un plancher* — et c'est
celui que le produit voit lui-même, ce qui est la mesure honnête de ce qu'il rate.

### N65 — L'hypothèse la plus coûteuse était un appel de fonction, pas une règle

**La direction tranchée par Alexandre** *(2026-09-16)* : **un dossier peut porter plusieurs noms,
aucun nom ne se perd, et la fusion reste écartée.** Le miroir permet plusieurs noms par NEQ
(1 505 879 paires, 41,7 % du registre); le dossier n'en permet qu'un. *Le produit suppose qu'une
entreprise n'est nommée que d'une façon, et le registre dit le contraire.*

**Le recensement du coût dit l'inverse de ce que le chiffre brut annonce.** 55 lectures de
`nom_detecte` dans `falkye/`, mais :

- **≈ 47 sont de l'AFFICHAGE, et ne bougent pas** — l'idiome est déjà
  `company.nom_officiel_req or company.nom_detecte`. *La règle du 15 septembre (« le portrait
  affiche le nom légal du registre ») est ce qui les rend immobiles.*
- **≈ 6 sont de la RECHERCHE, et les élargir EST le gain.**
- **2 sont de l'ÉCRITURE.**

⚠️ **Le vrai coût n'est aucun des trois : c'est une ligne.**

```python
trouve = db_session.execute(requete_nom_exact(nom_norm)).scalar_one_or_none()
```

**`scalar_one_or_none()` LÈVE si deux dossiers non résolus portent le même nom normalisé.** Le
chemin de production y passe à chaque signal non résolu. *Un dossier qui gagne un nom peut se
mettre à porter le nom d'un autre dossier* — et l'exception arriverait en production, pas en test.

**LA RÈGLE, et elle vaut plus que la structure proposée.** *Les hypothèses les plus coûteuses à
défaire ne sont pas celles qu'on a écrites comme règles : ce sont celles qu'on a écrites comme
appels de fonction.* **Une règle du corpus se relit et se discute. Un `scalar_one_or_none()` se
découvre en le cassant.**

**Et la réponse à « quelle règle du corpus dois-je défaire » est : aucune.** Le portrait est
renforcé, la règle de `req_noms` (« la table sert à TROUVER, jamais à NOMMER ») est étendue mot pour
mot, la conservation et l'ancienneté sont intactes. *Ce qui change vit en dessous du corpus.*

### N66 — Une transformation destinée à une valeur s'appliquait à toute la ligne

**Le fait.** L'idiome répandu dans `outils/` était `f"… {n:,}".replace(",", " ")`. ⚠️ **`.replace`
porte sur la LIGNE, pas sur le nombre** : « PERDUS, NEQ déjà porté » sortait « PERDUS  NEQ déjà
porté ».

**Trouvé par un test qui cherchait un libellé et ne l'a pas trouvé** — dans un outil écrit le jour
même. *Et il traînait déjà dans `purge_hors_territoire.py` et `entonnoir_noms_req.py`, livrés
depuis des jours, où personne ne l'avait vu* — **parce qu'on lit les chiffres d'un rapport, jamais
sa ponctuation.**

**LA RÈGLE. Une transformation destinée à UNE valeur ne s'applique pas à la ligne qui la
contient.** *La ligne n'est pas la valeur* — et le jour où le libellé change, la sortie change sans
que le code ait bougé. `outils/nombres.py::milliers` formate la valeur seule; 12 outils corrigés,
et `tests/test_format_des_nombres.py` refuse le retour de l'idiome.

*Le séparateur est l'espace insécable étroite (U+202F) : une espace ordinaire laisserait un nombre
se couper en fin de ligne, et un nombre coupé se relit comme deux.*

### N67 — Trois contraintes reçues après l'ouverture : deux tiennent, une tombe

**Les renvois vérifiés au corpus, et ils disent bien ce que le message rapportait.** *Le vérifier était
la première chose à faire : un message cite de seconde main, le corpus fait foi.*

**CE QUI TIENT TEL QUEL.** Le recensement des 55 lectures (≈47 affichage / ≈6 recherche / 2 écriture) —
*quelle que soit la forme du pivot, ces sites afficheront ou chercheront un nom*. Le défaut
`scalar_one_or_none()` — **vivant sur le chemin de production, indépendant de toute décision ouverte, et
le plus urgent des trois.** Les correctifs de collision et les deux mesures.

**CE QUI TIENT MOYENNANT UN AJOUT — cas 33.** Les deux mesures portent sur les `Company` résolues contre
**le REQ, registre des entités PRIVÉES**. *Entière et valable sur ce périmètre.* Ce qu'elles ne
couvraient pas : les entités **publiques** (D27 ⬜, D28 ⬜), les **donneurs d'ouvrage** qui n'existent
comme entité nulle part (D43 ⬜), et la **famille d'entité** que la structure ne porte pas.

⚠️ **Et le mandat chiffre ce que ça écarte : 56 % d'ambiguïté sur les entreprises, ZÉRO sur les
organismes publics.** *La population où l'appariement est difficile est exactement celle que ces outils
mesurent; celle où il est trivial en est absente.* **L'ajout suit la prescription du cas 33 à la
lettre : le périmètre s'imprime À CÔTÉ DE LA SORTIE, pas dans la documentation** — et deux tests
l'exigent.

**CE QUI TOMBE.** `company_noms` comme structure définitive. Elle accrochait les noms à `company_id` et
**supposait que `Company.neq` reste le pivot**. Le mandat dit l'inverse : *« la clé du moteur cesse
d'être un identifiant de territoire »*, une identité interne, une table d'identifiants externes avec
territoire — et la famille s'ajoute à côté. **La forme survit, son point d'accrochage tombe.** *Et la
phrase qui condamne le report condamne aussi de la construire seule maintenant : « le faire après, c'est
migrer deux fois la même clé » — la construire à part en ferait trois.*

### N68 — J'avais étendu une décision par symétrie, et le cas 34 l'interdit

⚠️ **L'étape 2 de ma proposition — « élargir les 6 points de recherche » — était présentée comme une
conséquence de la décision du 16. Elle n'en est pas une.** La décision porte sur la **conservation des
noms** : qu'aucun ne se perde, qu'aucun dossier ne soit supprimé.

**Conserver un nom et l'utiliser pour chercher sont deux gestes différents, et le second a ses propres
risques** — élargir la récupération augmente les candidats, donc les ambiguïtés **et les faux
appariements**. *Rien dans la décision du 16 ne dit qu'on accepte ce coût-là.* **Retiré de la
proposition : la lecture et le dédoublonnage demandent chacun leur démonstration chiffrée.**

**Et le cas 27 + 41 appliqués à la même proposition.** Elle décrivait deux points d'écriture à étendre,
et **rien n'obligeait un troisième, écrit le mois prochain, à passer par la table.** *C'est la garde
recopiée à la main, une table plus loin — six heures après qu'elle ait coûté quinze outils sur
vingt-huit.* Ce qui l'exigerait : **un seul chemin d'écriture du nom** *(l'endroit qui ne peut pas être
contourné)* **ET un test d'AST qui refuse toute affectation hors de lui**. *Le test sans la fonction est
une vigilance outillée; la fonction sans le test est une convention.*

### N69 — Les décisions que ma proposition supposait, nommées plutôt que devinées

**D28** : mon élargissement envoyait **tout** nom au REQ — *c'est présumer que toute entité est privée*,
exactement l'ambiguïté d'entité que D28 doit trancher avec une réponse par défaut. **D29** : ma règle
d'ancienneté décide quel dossier porte **le NEQ**; dès qu'une entité peut porter deux identifiants,
« qui porte quoi » relève de D29. **D27** : sans registre public, « apparier des noms à une entité
publique » n'a pas de sens défini.

**LA RÈGLE. Poser une valeur par défaut pour avancer, c'est trancher une décision ouverte sans le
dire.** *La nommer coûte une ligne; la deviner coûte une migration.*

### N70 — « Vivant » n'était pas fondé : j'avais le mécanisme, pas l'occurrence

**La question d'Alexandre** *(2026-09-16)* : j'ai qualifié `scalar_one_or_none()` de « défaut VIVANT
sur le chemin de production » **sans en donner la preuve**, et le corpus veut que la preuve voyage
avec le fait.

**La réponse est la seconde des deux lectures : c'était DÉDUIT de la lecture du code.** *Je n'avais
aucune trace, et je n'en ai toujours pas — les journaux sont sur l'hôte.* **Le mot était trop fort
et je le retire.**

**Mais l'enquête a rendu mieux qu'une confession, et c'est bien la forme du cas 27.** Ce qui
protège le chemin aujourd'hui n'est **pas une garde** : `resolve_company` ne crée un second dossier
que si le rapprochement flou échoue, et *un nom normalisé identique score 100, donc au-dessus de
`SEUIL_FUSION_AUTO = 95`* — le doublon est absorbé. **C'est un effet de bord d'un autre mécanisme
pris pour une garantie.**

⚠️ **Et la fissure est nommable, mesurable, et c'est la même que ce matin.**
`requete_candidats_prefixe` est bornée par `LIMITE_CANDIDATS = 500` **sans `ORDER BY`**. *Si le
préfixe sature la borne et que le vrai jumeau n'est pas dans la tranche rendue, le score n'a jamais
lieu et le second dossier naît.* **La borne sans ordre, une table plus loin.**

**Démontré plutôt qu'affirmé** — `tests/test_doublon_nom_non_resolu.py` : le jumeau échappe à la
borne saturée, puis deux dossiers de même nom font lever `_find_unresolved_company`, **la fonction
que le cycle traverse à chaque signal non résolu.**

**LA RÈGLE. « Ce défaut peut arriver » et « ce défaut est arrivé » sont deux affirmations
différentes, et un test ne prouve que la première.** *L'occurrence se lit dans les journaux et dans
la population, jamais dans le code.* **Dire laquelle des deux on tient coûte trois mots.**

### N71 — L'adresse est capturée et jamais promue : le préalable avant toute mesure

**Vérifié au code, et l'audit avait raison.** `falkye/sources/eimt.py` construit son `RawSignal`
avec `champs={"adresse": …}` et **aucun argument `adresse=`** — alors que `RawSignal.adresse`
existe *(`falkye/sources/base.py`)*. **Le champ existe, la donnée existe, et le pont entre les deux
n'existe pas.**

⚠️ **Donc une mesure d'appariement par adresse rendrait ZÉRO, et ce zéro se lirait comme
« l'adresse ne sert à rien »** — alors qu'il ne dirait rien de l'adresse, seulement du champ. *C'est
la série d'hypothèses tombées du 14 au 16 septembre, où le second terme de la comparaison
n'existait pas.*

`outils/portee_adresse.py` **n'apparie rien** : il établit si les deux termes existent, des deux
côtés, **et il montre LA FORME** — un échantillon brut côte à côte. *Deux taux de remplissage élevés
ne disent pas que les deux chaînes se comparent : « 123, Rang Saint-Joseph, bureau 2 » et
« 123 RANG SAINT-JOSEPH » sont deux remplissages et un seul appariement.* **C'est ce que la
normalisation devra franchir, et personne ne l'avait regardé.**

**Rappel du mandat, à ne pas perdre** : le chantier 4 pose **l'adresse comme axe principal, le nom
en corroborateur.** *Elle passe seconde dans l'ordre des mesures pour son préalable, jamais pour son
rang.*

### N72 — Le chiffre du nom de fichier n'était produit par aucune requête du fichier

**La question d'Alexandre** *(2026-09-16)* : `profil_des_6176` porte-t-il un sous-ensemble des 8 931,
ou une population recomptée? **Il demandait les deux requêtes, pas une explication.** *Il avait
raison de les demander : elles répondent une troisième chose.*

**Les voici, et elles sont identiques au caractère près :**

```python
# outils/diagnostic_appariement.py:381   → « les 8 931 »
select(Company).where(Company.neq.is_(None))
# outils/profil_des_6176.py:136          → « les 6 176 »
select(Company).where(Company.neq.is_(None))
```

**Donc ni (a) ni (b).** L'outil **LIT la population entière** — la même requête — puis **découpe son
sous-ensemble lui-même, à l'exécution** : il écarte les formes présentes dans `Nom.csv`, déjà
réglées par le pont. ⚠️ **Le 6 176 n'est produit par aucune requête de ce fichier.** *C'est une
mesure passée, gelée dans un nom.*

**Et un second défaut que la question a fait apparaître : le découpage se fait par NOM NORMALISÉ,
pas par dossier.** Deux dossiers de graphie identique comptent pour une forme. *Un compte de formes
et un compte de dossiers ne sont pas le même nombre*, et le plan raisonne en dossiers. **Un compte
qui ne dit pas son unité se lit dans l'unité que le lecteur a en tête.**

**LA RÈGLE, et c'est celle du corpus sur les chiffres recopiés appliquée aux noms.** *Un chiffre
recopié est une promesse que personne ne tient* — **et un nom de fichier est l'endroit où personne
ne va la vérifier.** Deux défauts distincts, et le second est le pire :

1. un compte ne se met pas à jour quand la population bouge;
2. ⚠️ **il donne l'autorité d'une MESURE à ce qui n'est qu'une ÉTIQUETTE.**

**Renommé `noms_etablissement_non_resolues.py`** — *nommer ce que l'outil FAIT, pas ce qu'il a
trouvé un jour.* Le périmètre imprime désormais **la requête elle-même**, les deux comptes avec leur
unité, et la phrase qui manquait : *« ce qui suit ne porte que sur ces N dossiers; les M autres ne
sont couvertes par aucune mesure ici ».*

**Et la règle est rendue exigible** : `tests/test_noms_doutils_sans_compte.py` refuse tout nom de
fichier portant trois chiffres consécutifs, années exclues — *un fichier daté dit QUAND, ce qui ne
se périme jamais; un fichier compté dit COMBIEN, ce qui se périme.* Vérifié en remettant l'ancien
nom.

### N73 — La normalisation est la même, la SOURCE DE LA VALEUR ne l'est pas

**La question d'Alexandre** *(2026-09-16)* : `dossiers sans NEQ : 8931` et `formes distinctes : 8931`
étant égaux, aucun dossier ne partage sa forme — donc `scalar_one_or_none()` ne peut pas lever. *La
normalisation de l'outil est-elle celle du chemin de résolution?*

**Premier temps : OUI, même fonction.** Les deux importent `falkye.sources.column_mapping.
normaliser`. Vérifié.

⚠️ **Second temps, et il change la conclusion : ce n'est pas la même SOURCE DE VALEUR.**

```python
# l'outil RECALCULE
forme = normaliser(company.nom_detecte or "")
# la production LIT LA COLONNE STOCKÉE
Company.nom_detecte_normalise == nom_norm
```

*Une colonne stockée a été écrite un jour, par le normaliseur de ce jour-là.* **Si `normaliser` a
changé depuis — et il a changé le 15 septembre, c'est tout le sujet du réimport — la colonne porte
l'ancienne forme et le recalcul porte la neuve.** Deux dossiers peuvent donc être distincts à la
lecture de l'outil et identiques dans la colonne, ou l'inverse.

**Donc l'égalité 8931/8931 est une PRÉSOMPTION FORTE, pas une preuve.** Ce qui ferme la question est
une requête d'une ligne, sur la colonne que la production interroge :

```sql
SELECT nom_detecte_normalise, count(*) FROM companies
WHERE neq IS NULL GROUP BY nom_detecte_normalise HAVING count(*) > 1;
```

**LA RÈGLE. Deux valeurs produites par la même fonction ne sont pas la même valeur si l'une est
stockée et l'autre recalculée.** *Une colonne dérivée est une photo, pas un miroir* — et la question
« est-ce le même code » ne répond jamais à « est-ce la même valeur ».

### N74 — Deux bornes, deux tables, et les confondre fait chercher le mur du mauvais côté

**Relevé en préparant la trace des 6 414.** La demande visait `LIMITE_CANDIDATS = 500` — **mais ce
n'est pas la borne qui décide du sort de ces dossiers.**

| borne | où | ce qu'elle décide |
|---|---|---|
| `candidats_par_nom(limite=2000)` | contre le **MIROIR** | ce qui est comparé au registre |
| `LIMITE_CANDIDATS = 500` | entre les **`Company`** | ce qui est comparé aux autres dossiers |

*Les deux sont des « LIMIT sans ORDER BY » relevés le même jour*, ce qui rend la confusion facile —
et c'est précisément pour ça qu'il faut l'écrire. **Un dossier qui échoue à se résoudre contre le
REQ a buté sur la première; la seconde ne l'a jamais vu.**

**Un test refuse que le diagnostic annonce une borne différente de celle que le moteur applique** —
*sinon la trace mentirait sur la borne qu'elle diagnostique.*

### N75 — NOM_ETAB rend zéro, et c'est le périmètre imprimé qui l'a rendu lisible

**5 sur 2 517, toutes en forme `IND`** — des personnes physiques, la population que le Registraire ne
publie pas. *L'hypothèse tombe.*

**Mais la mesure rend en passant plus gros qu'elle ne cherchait : 6 414 dossiers sur 8 931 — 72 % —
portent un nom déjà présent dans `Nom.csv` et n'ont toujours pas de NEQ.** **Le second terme de la
comparaison existe pour presque trois quarts d'entre eux.** *Ce qui échoue n'est pas de TROUVER le
nom, c'est de DÉCIDER lequel.*

⚠️ **Et ce chiffre n'était visible que parce que le périmètre imprimé l'exigeait.** Le compte
« réglées par le pont » n'avait été ajouté que pour dire ce que l'outil ne mesurait PAS *(cas 33)*.
**La déclaration de portée a produit la trouvaille.**

*Deux motifs relevés dans les exemples — champs nommant plusieurs entreprises, noms commerciaux entre
parenthèses — attendent délibérément : les corriger ferait passer ces dossiers d'un mur vers l'autre,
et leur gain est nul tant que le second n'est pas compris.* **Et la réserve d'Alexandre sur ces
quinze est juste : ce sont les quinze premiers par ordre alphabétique, donc le tri du fichier promu
en échantillon — le cas 19.**

### N76 — La distinction stockée/recalculée, appliquée au critère plutôt qu'au compte

**La question d'Alexandre** *(2026-09-16)* : le sélecteur de `--depuis-la-base` choisit-il sur la
valeur recalculée ou sur la colonne stockée? *Il m'appliquait ma propre distinction au CRITÈRE DE
SÉLECTION plutôt qu'au compte.*

**Vérifié au code : la colonne STOCKÉE** — `trace_un_appariement.py:112`,
`forme = company.nom_detecte_normalise`. **Bonne population, on lance tel quel.**

⚠️ **Mais sa question en ouvre une meilleure, et sa propre hypothèse tombe par lecture.** Il
supposait que la colonne périmée pourrait expliquer les 6 414. **Elle ne peut pas**, et la raison
est structurelle :

```
resolve_neq_by_name(db_session, raw.nom_entreprise)  → normaliser(nom), RECALCULÉ
    comparé à
REQEntry.nom_normalise / REQNom.nom_normalise        → le miroir, réécrit le 16
```

**Aucun des deux côtés de cette comparaison ne lit `Company.nom_detecte_normalise`.** *La colonne
périmée ne peut pas expliquer un échec de résolution contre le REQ — elle n'y participe pas.*

**Là où elle reste vivante :** `_find_unresolved_company` et `dedup_entreprises`, qui comparent tous
deux la colonne stockée. **Ce sont deux chemins différents, et le même mot — « la forme
normalisée » — les désignait tous les deux.**

**LA RÈGLE. Quand un même mot désigne deux valeurs, la question « laquelle » doit être posée à
CHAQUE endroit, pas une fois.** *Je l'avais posée au compte; il l'a posée au critère de sélection;
elle se posait aussi aux deux côtés de la comparaison.* **La trace imprime désormais les deux formes
côte à côte, nommées**, et dit explicitement qu'un écart n'explique pas un échec contre le REQ.

### N77 — Le zéro qui ferme 4a doit dire ce qu'il ne ferme pas

`outils/doublons_forme_stockee.py` interroge **la colonne que la production compare**, jamais un
recalcul. *Un test met les deux valeurs en désaccord : deux dossiers de forme stockée identique dont
les noms bruts se normalisent différemment aujourd'hui — **un outil qui recalculerait ne les verrait
pas**, et rendrait un zéro exact sur le mauvais périmètre.*

⚠️ **Et la sortie borne son propre zéro** : *« ce zéro dit que le défaut n'est pas SURVENU, pas
qu'il est impossible »* — **la borne sans ordre du dédoublonnage peut créer cette condition
demain.**

⚠️ **Pourquoi un outil plutôt qu'une ligne de SQL.** La base est **distante** : une commande lancée
sans l'environnement retombe sur `./data/falkye.sqlite3`, **qu'elle crée puis interroge**. *Une base
vide rend zéro ligne, et ce zéro se lit exactement comme la bonne réponse* — cas 30 et cas 41 réunis
sur la même commande. `refuser_si_cible_non_choisie()` l'interdit.

*Et un cas que la requête brute aurait raté : la forme stockée VIDE. `nom_detecte_normalise == ''`
partagée par deux dossiers est un doublon comme un autre, et `scalar_one_or_none()` lève pareil.*

### N78 — 4a fermée par la mesure, et la garde a payé avant elle

**`doublons_forme_stockee` a tourné sur l'hôte, cible distante annoncée, aucun repli : 0 forme
partagée et 0 forme vide sur 8 931.** `scalar_one_or_none()` n'a jamais pu lever.

⚠️ **Et la garde de la cible a rendu son service AVANT la mesure** : elle a refusé sur
`REPLI PAR DÉFAUT` quand l'environnement n'était pas chargé. *Sans elle, la sortie aurait été
`✅ AUCUNE LIGNE RENDUE` sur une base vide, et 4a aurait été fermée sur rien.*

**C'est la première fois qu'une garde de cette session empêche une FAUSSE CONCLUSION plutôt qu'une
panne.** *Une panne se voit; un verdict vert sur une base vide ne se voit pas.*

**Le correctif reste pertinent et cesse d'être urgent.** *Ce zéro dit que le défaut n'est pas
survenu, pas qu'il est impossible* — la borne sans ordre du dédoublonnage peut créer cette condition
demain.

### N79 — Neuf hypothèses tombées demandaient toutes POURQUOI la comparaison échoue

**L'hypothèse d'Alexandre** *(2026-09-16, déclarée comme telle et non établie)* : **une part des
8 931 n'a pas de NEQ à trouver.** Le REQ ne contient que les entités immatriculées au Québec; un
employeur vu par l'EIMT peut être fédéral ou extraprovincial.

**Ce qui rend cette hypothèse différente des neuf autres n'est pas sa vraisemblance, c'est sa
FORME.** *Les neuf demandaient pourquoi la comparaison échoue; celle-ci demande s'il y a quelque
chose à comparer.* **Quand plusieurs hypothèses bien mesurées tombent, la question est mal posée** —
et le remède n'est pas une dixième hypothèse de la même famille.

**Ce que le registre déclare, LU et non déduit** — et il porte deux champs qu'on confond :

| | |
|---|---|
| **`territoire`** | le FILTRE réel. `null` ⇒ `appartient()` **RETIENT TOUT**, à dessein |
| **`region`** | du **TEXTE LIBRE**, « région couverte ». *Il ne filtre rien.* |

⚠️ **Une seule source sur vingt-six déclare un `territoire` : `eimt`.** Toutes les autres —
`seao`, `contrats_federaux`, `subventions_federales`, `rob_top_growing`, `investissement_quebec`,
`deloitte_fast50` — ont `territoire: null`. *Une source dont `region` dit « Québec » et dont
`territoire` est `null` n'est pas filtrée.*

⚠️ **Et le cas de l'EIMT retourne l'argument sans le trancher.** Son `territoire: ['Québec']` porte
sur la **PROVINCE DE L'EMPLOI**, pas sur le lieu d'immatriculation. *Un employeur qui embauche au
Québec peut être constitué au fédéral* — **c'est exactement la distinction sur laquelle porte
l'hypothèse, et le registre ne peut pas y répondre.**

**LA RÈGLE. Une source pancanadienne ne prouve pas qu'un dossier est hors Québec : elle dit qu'il
PEUT l'être.** *La ventilation borne ce qu'on peut espérer; elle ne classe aucun dossier.* **Et ce
qu'il faudrait faire d'une population hors registre est une décision de produit, pas un
correctif** — aucune valeur par défaut n'est posée.

*Deux pièges de comptage traités dans la sortie : un dossier à deux sources compte dans les deux
colonnes — **un total de colonnes n'est pas un total de dossiers** — et un dossier SANS signal n'a
aucune source, donc échappe entièrement au croisement.*

### N80 — La contradiction venait d'une étape manquante, et la trouvaille la dépasse

**Le relevé d'Alexandre** *(2026-09-17)* : trois dossiers tracés scorent **100 contre un seuil de
92**, huit points de marge, et sont pourtant sans NEQ. *« Les deux ne peuvent pas être vrais en même
temps. »*

**C'est sa version (a), vérifiée au code : la trace s'arrêtait au SCORE.** Elle appelait
`resolve_neq_by_name` et **jamais `neq_retenu`.** *Elle annonçait « la fonction DU MOTEUR » — vrai
de la RÉCUPÉRATION, faux de la DÉCISION.*

⚠️ **Mais l'étape ajoutée rend plus que la décision, et c'est le mécanisme qui agissait sans qu'on
le sache.** Voici ce que `resolve_company` fait d'un NEQ retenu :

```python
company = SELECT Company WHERE neq = <retenu>
if company is None: company = Company(neq=…)   ← un NOUVEAU dossier
company.statut_resolution = RESOLU
```

**Il ne répare JAMAIS le dossier non résolu.** Il écrit dans un dossier **clé par NEQ** — celui qui
existe, ou un neuf. *Le dossier sans NEQ reste sans NEQ, indéfiniment.* Et rien ne le réessaie
(N36).

**Donc les deux affirmations sont vraies, et la contradiction n'en était pas une** : un score de 100
aujourd'hui dit que la résolution **échouait le jour de la création du dossier**, et que personne
n'a redemandé depuis. ⚠️ **Ce n'est pas un mur d'appariement — c'est le cercle, et il a une seconde
moitié que N36 ne nommait pas : même si on redemandait, la réponse s'écrirait ailleurs.**

### N81 — Un critère de sélection qui présélectionne le résultat illustre une conclusion

**Le défaut, relevé par Alexandre.** Mon sélecteur retenait les dossiers **dont le nom normalisé
existait par correspondance EXACTE dans le miroir** — *c'est-à-dire ceux dont il avait déjà démontré
qu'ils devaient réussir.* **Trois cas tracés, trois scores de 100, et aucun dossier qui échoue
regardé.** *C'était l'objet de la mesure.*

**LA RÈGLE. Un critère de sélection qui présélectionne le résultat n'échantillonne pas une
population : il illustre une conclusion.** *Et il est d'autant plus difficile à voir qu'il produit
des sorties parfaitement cohérentes — les trois cas étaient justes, reproductibles, et sans
intérêt.*

**Remplacé** : chaque dossier est classé par `neq_retenu`, **la décision du moteur**, et
l'échantillon prend N de **chaque famille** — résoluble, ambigu, trop faible, aucun candidat. *Un cas
par famille dit plus que trois cas de la même.* Une famille vide dit « zéro dans ce qui a été
parcouru », jamais « zéro dans la population ».

### N82 — Un compte périmé dans le texte qui existe pour borner la mesure

**Troisième population non expliquée en deux jours**, après les 6 176 et le territoire du registre :
le bloc de portée de la trace citait **4 873** trois fois. *Un compte du 15 septembre, devenu 5 211
puis 4 733, et qui n'est plus dans aucune ventilation.*

⚠️ **Et cette fois le chiffre était dans le TEXTE DE PORTÉE** — celui qui existe précisément pour
dire ce que la mesure couvre. **Un périmètre qui annonce une population non définie ne borne rien**;
il donne l'apparence d'une portée déclarée à une phrase qui ne désigne plus personne.

**Rendu exigible** — et la garde a dû être resserrée après un premier jet trop large qui attrapait
les années et les fragments de NEQ. *Une garde qui crie pour un millésime finit par être ignorée :
le cas 34 dans la garde elle-même.* **Ce qui est refusé est la FORME d'un compte humain** — quatre
chiffres avec séparateur de milliers. *Une année ne s'écrit jamais avec un séparateur, un NEQ non
plus, et les seuils vivent dans des constantes nommées.*

### N83 — Le rejeu en lecture seule : étendu plutôt que dupliqué

**La mesure demandée** *(Alexandre, 2026-09-17)* : rejouer la résolution **en lecture seule** sur les
8 931 et compter ce qui se résoudrait aujourd'hui.

⚠️ **La machinerie existait déjà.** `apport_noms_multiples.py` parcourait la même population, avec
`resolve_neq_by_name` + `neq_retenu`, et séparait déjà NEQ libre / déjà porté. *Il lui manquait
seulement la ventilation en quatre familles.* **Une cinquième passe sur 8 931 aurait coûté une
seconde traversée complète du miroir pour recalculer ce qui était déjà calculé.**

**Étendu, puis renommé `rejeu_resolution.py`** — *nommer ce que l'outil FAIT.* L'apport des noms
multiples devient une section; le rejeu devient le titre.

**Trois ajouts au-delà de la ventilation :**

1. ⚠️ **Le caveat qui décide de la lecture** : *qu'un dossier se résolve au rejeu ne dit pas que le
   NEQ est le bon. Le score dit la RESSEMBLANCE, pas l'IDENTITÉ.* **Le compte borne ce qui est
   récupérable; il ne valide aucun appariement** — ce sont les paires, une à une, qui autorisent une
   écriture.
2. **Le rapport avec les 736 de l'instantané du 16.** *Si le rejeu en rend nettement plus,
   appliquer la passe sur un vieil instantané traiterait une fraction du problème en donnant
   l'impression de l'avoir traité.* **Le rapport des deux décide si la passe est l'outil ou
   seulement un acompte.**
3. **L'unité dans le périmètre** — des DOSSIERS, jamais des formes normalisées.

*Et la ventilation reprend les fonctions et les seuils du diagnostic, pour que les deux comptes se
comparent ligne à ligne : deux ventilations calculées autrement ne se comparent pas, et l'écart se
lirait comme un mouvement (N56).*

### N84 — Le nombre de prétendants est une preuve d'une autre nature que le score

**Le fait** *(2026-09-17, relevé par Alexandre)*. Le NEQ `8879690699` attirait **26 dossiers** —
CISSS de la Montérégie-Centre, CISSS Gaspésie, CIUSSS de l'Outaouais, CHUM, Centre universitaire de
santé McGill, Institut de Cardiologie, Centre régional de la Baie-James… **26 organisations
RÉELLEMENT DISTINCTES, scores de 95 à 100.**

**Sa question gate une écriture, et la réponse était « oui, elle écrirait ».** La passe départageait
par l'ancienneté : *le plus ancien des 26 aurait reçu le NEQ.*

**LA RÈGLE. Le nombre de prétendants est lui-même une preuve CONTRE l'appariement, et d'une autre
nature que le score.** *Deux dossiers qui convergent, c'est un doublon plausible — la situation pour
laquelle la conservation a été pensée. Vingt-six, c'est un nom qui désigne une FAMILLE d'entités*, et
l'ancienneté y désignerait un gagnant dans un groupe dont **aucun membre n'est probablement le
bon.**

⚠️ **Et ce n'est pas un réglage de seuil.** *Les noms se ressemblent réellement; le scoreur ne se
trompe pas, il répond à une autre question que celle qu'on lui pose.* **Monter le seuil n'y ferait
rien — ces scores sont à 100.**

**Refus posé** : au-delà de `PRETENDANTS_MAX_POUR_TRANCHER = 2`, personne ne l'obtient. *Le refus ne
peut que RÉDUIRE les écritures, jamais en produire une.* Un test vérifie aussi que **le cas à DEUX
reste départagé** — une garde qui refuserait aussi le cas qu'elle devait laisser passer coûterait le
gain qu'on venait de gagner.

⚠️ **Et un trou trouvé en l'écrivant : les refusés n'étaient pas journalisés.** Le `continue`
d'origine les écartait en silence, et **« refusé » se serait lu comme « jamais rencontré ».** *Ils ne
peuvent pas non plus être journalisés comme candidats de fusion : cette entrée-là affirme que l'un des
deux est le bon — exactement ce que le refus vient de refuser d'affirmer.* Journalisés comme
problème à examiner, rattachés au seul dossier concerné.

**Le constat au-delà du cas, et il est à nommer plutôt qu'à corriger** *(Alexandre)* : **si 26
organisations publiques distinctes convergent vers un même NEQ à 95-100, le rapprochement par nom
sur les entités publiques produit du faux avec une confiance élevée.** *Et ce sont précisément les
entités que le périmètre déclare ne pas couvrir — D27 et D28 ouvertes.*

### N85 — Deux chiffres qui ne tiennent pas ensemble désignent l'étape d'avant

**Le recoupement d'Alexandre** : 6 414 dossiers portent un nom présent au registre, 4 733 sont
classés « candidats trop faibles ». *Les deux ensembles se recouvrent forcément.* **Un dossier dont
le nom est littéralement dans le registre ne devrait pas avoir de candidats faibles.**

⚠️ **Et son argument sur le scoreur retourne le soupçon de la bonne façon** : *le bloc des 26 montre
un scoreur GÉNÉREUX — des noms différents obtiennent 95 à 100.* **S'il donne 100 à deux entités
distinctes, il ne peut pas rendre « trop faible » sur un nom exact.** Donc le défaut est **en amont
du score, dans la RÉCUPÉRATION** : si le bon candidat n'est jamais présenté au scoreur, le verdict
est « trop faible » sur des candidats sans rapport, **et rien dans le compte ne le dirait.**

**Ce qui n'a jamais été regardé, et il a raison** : `prefix = nom_norm.split(" ")[0]` — **le premier
mot, rien d'autre.** *Les trois cas tracés portaient tous un nom numérique* (`10320633 Canada inc.`
→ préfixe `10320633`, unique, une ligne rendue). **On ne sait rien de ce que ça donne sur « Bâtiments
d'acier Finar inc. »** — préfixe `batiments`, des milliers de lignes, et une borne qui tranche une
tranche alphabétique.

**La trace rend désormais** : la règle d'extraction et le préfixe obtenu, un avertissement quand il
est numérique *(« ces cas ne disent rien des noms ordinaires »)* ou très court, le nombre de lignes
avant la borne, **et si le repli par sous-chaîne a servi** — celui qui coûte 98 % du budget pour
14 % des appels.

⚠️ **Et le jumeau exact est désormais cherché MÊME QUAND LE MOTEUR ÉCHOUE**, pour que l'étape 5
réponde à la seule question qui compte : **le bon candidat était-il ABSENT du lot, ou PRÉSENT et mal
scoré?** *Les deux verdicts s'appellent « trop faible » et n'ont pas la même cause.*

*Ce n'est pas une présélection du résultat (cas 42) : la sélection porte sur l'ÉCHEC — la famille
vient de `neq_retenu` — et le jumeau n'est cherché qu'ensuite.*

### N86 — Trois silences différents sous le même message

**L'écart relevé par Alexandre** *(2026-09-17)* : la trace disait *« aucun --attendu ni --neq donné :
étape sautée »* alors que j'avais annoncé que le jumeau exact était désormais cherché.

**Vérifié : la fonction a tourné et n'a rien trouvé, correctement.**

```
détecté normalisé  : '11888935 canada inc workstaff'
registre normalisé : '11888935 canada inc'
égaux ? False
```

⚠️ **Et mon affirmation était trop forte d'une façon qui compte.** *Pour la famille « trop faible »,
un jumeau EXACT n'existe presque jamais — c'est précisément pourquoi ces dossiers sont trop
faibles.* **Le jumeau exact ne peut donc quasiment pas servir sur cette famille-là**, et c'est
l'étape 7 qui répond, en montrant si le bon candidat a été présenté au scoreur.

**LA RÈGLE. « On ne l'a pas demandé » et « on l'a cherché et il n'existe pas » sont deux silences
différents, et le second est un résultat.** *Les confondre dans un seul message transforme une
mesure en absence de mesure* — et c'est la forme du cas 33 appliquée à une seule ligne de sortie.

### N87 — Deux corrections qui ne sont pas de même nature, et le chiffrage doit le rendre visible

**Le cas qui ouvre la question** : un dossier échouant de **deux points** à cause de `(Workstaff)`,
avec une récupération parfaite — préfixe numérique, une ligne rendue, borne non atteinte, bon
candidat présenté. **Le mur était dans le score, pas dans la récupération.**

⚠️ **Et une hypothèse ne tombe pas, elle n'est pas encore testée** *(Alexandre)* : le préfixe de ce
cas était NUMÉRIQUE. *L'argument sur `split(" ")[0]` donnant `centre` ou `construction` n'est ni
confirmé ni réfuté* — il attend un nom ordinaire.

**LA DISTINCTION QUE LE CHIFFRAGE DOIT PORTER :**

| | |
|---|---|
| **retirer les parenthèses** | **correction de DONNÉES** — *elle ne peut que rapprocher des chaînes qui désignent la même entreprise* |
| **abaisser le seuil** | **changement d'ÉCHELLE** — *il récupère du VRAI **et** du FAUX* |

**Donc l'abaissement rend DEUX chiffres** : ce qu'il récupère, **et ce qu'il laisse passer** —
mesuré par les prétendants multiples, *la seule forme de faux qu'on ait vue de près : 26
organisations publiques distinctes à 95-100 sur un même NEQ*.

⚠️ **Un chiffrage qui ne compterait que le gain ferait paraître l'abaissement gratuit.** C'est la
règle, et un test la porte.

**Et le seuil de 92 ne bouge pas** *(Alexandre)* : *c'est une échelle existante, elle se change avec
lui, jamais dans une demande de mesure.* **Un raisonnement donne l'axe; seul un incident donne le
seuil — et un cas unique n'est pas encore un incident.**

*Le coût est de deux passes : retirer la parenthèse change aussi le PRÉFIXE, donc la RÉCUPÉRATION —
la simuler sans rejouer la récupération mesurerait autre chose.*

---

## N88 — Un instrument qui recopie la règle du moteur mesure sa propre copie, et l'attribue à la correction

*(2026-09-17, relevé par Alexandre sur la sortie du chiffrage.)*

Le chiffrage annonçait **-338 RETENUS** après retrait des parenthèses, et **l'annotation juste en
dessous disait que cette correction ne peut que RAPPROCHER des chaînes**. Les deux étaient dans la
même sortie.

⚠️ **Alexandre n'a pas choisi la plus plausible des deux versions.** *« Soit le retrait s'applique
aussi au miroir, soit la simulation a un défaut. Ce qui trancherait : sur les 338 perdus, combien
portaient une parenthèse dans le nom détecté? »* **Une contradiction se tranche par une mesure, pas
par la vraisemblance.**

**Ce que la lecture a rendu.** La seconde passe rescorait à la main :

```python
rescores.append((fuzz.WRatio(cible, normaliser(_sans_parentheses(m.entry.nom))), m))
```

*Le moteur, lui, fait deux choses que cette ligne ne fait pas* :

| | le moteur | la recopie |
|---|---|---|
| **les noms** | le MEILLEUR des noms du NEQ, `req_noms` compris | la seule dénomination sociale élue |
| **la ville** | `+5` quand elle concorde | rien |

Mesuré sur le cas type : `Ferme M.G. Bellavance` → **100 au moteur, 30 à la recopie**. Et un dossier
tenu par le bonus de ville : **95 au moteur, 90 à la recopie** — sous le seuil.

⚠️ **Les scores plus bas tombaient tous du même côté, et le tableau les imputait à la correction.**

**C'est le cas 41 — le garde recopié — dans mon propre outil, contre une règle écrite dans la
docstring que je recopiais** : *« Un outil qui la rejouerait en la recopiant mesurerait sa propre
copie. »* `neq_retenu` et `requete_nom_exact` avaient été extraites pour ça. **Le scoreur, lui, ne
l'était pas — et c'est là que l'outil a recopié.**

**Le correctif** : `resolve_neq_by_name` accepte `transformer_forme`, `None` en production. La
simulation emprunte donc le scoreur entier — regroupement par NEQ, `req_noms`, bonus de ville — au
lieu d'en écrire un à côté.

⚠️ **Et le transformateur reçoit le nom PUBLIÉ, jamais la forme normalisée.** *`normaliser` remplace
déjà la ponctuation par des espaces : « Canada inc. (Workstaff) » y est « canada inc workstaff ».*
**Les parenthèses ont disparu comme caractères, leur contenu est resté comme mot.** Simuler le
retrait sur la colonne normalisée aurait rendu **un no-op déguisé en mesure**.

**Le test qui l'aurait attrapé** : *un dossier sans la moindre parenthèse, RETENU par le pont — la
correction ne peut rien y changer, donc toute perte est imputable à l'instrument.*

---

## N89 — L'annotation qui promet qu'une correction « ne peut que rapprocher » est fausse dès qu'elle touche la RÉCUPÉRATION

*(2026-09-17, exigé par Alexandre.)*

*« Si les 338 perdus ne portaient pas de parenthèse, la perte vient du côté registre et c'est un
mécanisme, pas un bogue — mais alors l'avertissement est faux tel qu'il est écrit. »*

**Deux effets, et ils ne vont pas dans le même sens :**

- **côté DÉTECTÉ**, retirer la parenthèse change le premier mot, donc le **préfixe**, donc **quelles
  lignes le `GLOB` rend**. *Elle DÉPLACE la récupération autant qu'elle rapproche les chaînes* — et
  un déplacement peut **perdre** un appariement qui marchait;
- **côté REGISTRE**, elle ne change que les **scores** : la récupération cherche le préfixe du nom
  **détecté** dans la colonne stockée, et la simulation ne réécrit pas cette colonne.

⚠️ **Une correction appliquée À L'IMPORT, elle, réécrirait `nom_normalise` — et changerait alors la
récupération des DEUX côtés.** *Ce n'est pas la même correction, et elle ne se chiffre pas avec la
même passe.*

**Aucune correction de données n'est « gratuite » quand la récupération est ancrée sur la tête de la
chaîne.** L'annotation dit maintenant les deux effets, et la ventilation des perdus (avec
parenthèse / sans) permet de trancher mécanisme contre défaut.

---

## N90 — Compter ce qui FRANCHIT un seuil n'est pas compter ce qu'on RÉCUPÈRE : deux échelles, deux refus

*(2026-09-17, relevé par Alexandre — l'écart de 1 544.)*

```
[ 90 – 91[            1 623 dossiers
seuil abaissé à 90 :     79 récupérés
```

*« Environ 1 544 franchissent donc le seuil abaissé sans devenir RETENU. »* **Le chiffrage les avait
tous perdus en route**, et « 79 récupérés » se lisait comme si les 1 544 autres n'existaient pas.

**La cause** : le moteur porte **DEUX échelles**, et une seule était simulée.

| | ce qu'elle dit | ce qu'elle produit quand elle refuse |
|---|---|---|
| **seuil, 92** | *« le candidat ressemble assez »* | `trop faible` |
| **écart minimal, 8** | *« le second ne ressemble pas trop »* | `ambigu` |

⚠️ **Une masse retenue par la seconde échelle disparaît d'un chiffrage qui ne simule que la
première.** *Ce n'est pas le seuil qui retient les 1 544 — c'est l'écart.*

**La règle** : toute masse qui franchit un seuil simulé est **suivie jusqu'à sa destination**, par
famille et par palier. Un gain seul n'est pas un chiffrage.

**Et la taxonomie est passée dans le moteur** (`falkye/resolution.py::famille_de`) : quatre familles,
un seul endroit. *Trois outils la recalculaient chacun à sa façon.*

---

## N91 — L'écart minimal est plus dangereux que le seuil, et personne n'en avait parlé de la journée

*(2026-09-17, décision de méthode d'Alexandre.)*

*« L'écart de 8 est une seconde échelle, et elle n'a jamais été rouverte. »*

⚠️ **Le seuil dit « le candidat ressemble assez ». L'écart dit « le SECOND ne ressemble pas trop ».**
*L'abaisser, c'est accepter de trancher entre deux candidats proches* — **la situation exacte des 26
organisations publiques distinctes à 95-100 sur le NEQ `8879690699`.**

**Donc le chiffrage de l'écart rend le FAUX AVANT le gain** — l'ordre des colonnes est la mesure.
*Un tableau qui montre d'abord ce qu'on gagne fait lire le reste comme un détail.*

**Trois colonnes de faux, et la troisième est propre à l'écart** : les dossiers nouvellement retenus
dont **le second candidat est une AUTRE entité** à portée de l'écart abaissé. *Chacun est une
décision entre deux entreprises différentes, prise par la machine.*

⚠️ **Un TÉMOIN dans le tableau** : à l'écart en vigueur, le gain **doit être 0**. *Un gain non nul
dirait que la simulation et le moteur ne classent pas pareil, et tout le tableau serait à jeter.*

**Et deux changements d'échelle ensemble ne s'additionnent pas — ils se multiplient**, parce que
chacun retire une garde que l'autre ne remplace pas.

⚠️ **Ni 92 ni 8 ne bougent.** *Deux échelles existantes, et elles se changent avec Alexandre, jamais
dans une demande de mesure.*

---

## N92 — Ce que les chiffres établissent, et qui ne bouge plus

*(2026-09-17, Alexandre.)*

**Les parenthèses sont un petit motif** : **259 dossiers sur 8 931**, dont **205 chez les trop
faibles**. *Même corrigé parfaitement, le plafond est 205.* **Le cas `(Workstaff)` était réel; il
n'est pas le mur.**

**Et la distribution répond à la question de fond** : **2 713 dossiers à 85-88**, **1 623 à 90-91**,
**1 885 à moins de quatre points du seuil**.

> ⚠️ **Le mur n'est pas que le bon candidat soit absent. C'est qu'il est là et qu'il ne passe pas.**

*Ce ne sont pas des appariements sans rapport — ce sont des appariements qui manquent de peu.*

---

## N93 — Un préalable a évité une mesure qui aurait rendu zéro, et ce zéro aurait accusé la chose au lieu du champ

*(2026-09-17.)*

```
dossiers SANS NEQ     : 8 931
dont avec une adresse : 0  (0.0 %)      ⛔
```

**Zéro des dossiers à apparier ne porte d'adresse.** *La mesure d'appariement par
adresse qu'on s'apprêtait à demander aurait rendu zéro* — et **ce zéro se serait
lu comme « l'adresse ne sert à rien »**, alors qu'il n'aurait rien dit de
l'adresse, seulement du champ.

⚠️ **C'est la série d'hypothèses du 14 au 16 septembre, évitée pour la première
fois avant d'être tombée** : le second terme de la comparaison n'existait pas.

> **Un préalable n'est pas une étape de plus. C'est ce qui empêche un chiffre
> d'être vrai et de désigner la mauvaise cause.**

---

## N94 — Deux niveaux de précision ne sont pas deux graphies : aucune normalisation ne les rejoint

*(2026-09-17, Alexandre.)*

```
produit  : 'St-Isidore, QC J0L  2A'
registre : '200 rue des Commandeurs'   ville='Lévis'
```

**L'EIMT donne une municipalité, une province, un code postal. Le REQ donne un
numéro civique et une rue.**

⚠️ *Ce n'est pas un problème de normalisation, et aucune quantité de
normalisation ne le réglera.* **On ne fait pas descendre une municipalité au
numéro civique.** *Le mur de la forme est distinct du mur du remplissage, et il
survit à un remplissage parfait.*

**Ce qui se recouvre, c'est la VILLE** — et peut-être le code postal. *La mesure
se pose donc sur l'intersection, pas sur le champ.*

---

## N95 — Une colonne qui rend le même chiffre que sa voisine n'ajoute rien : elle la répète

*(2026-09-17, relevé par Alexandre.)*

Le chiffrage de l'écart rendait le gain **et** une colonne « 2e NEQ à moins de ».
*À chaque ligne, les deux étaient égaux* — **138 et 138, 2 097 et 2 097**.

**C'était une identité, pas une mesure** : tout dossier récupéré par un écart
abaissé avait, par construction, un second à moins de 8 points.

⚠️ **Le contenu utile restait vrai** — *tout ce qu'un abaissement de l'écart
récupère, il le récupère en tranchant entre deux entités* — **mais il était
énoncé par une colonne qui ne pouvait pas dire autre chose.**

> **Une colonne doit pouvoir CONTREDIRE celle d'à côté. Si elle ne le peut pas,
> elle n'est pas une seconde mesure, c'est la première réécrite.**

---

## N96 — Trois lectures d'une perte, pas deux : ma propre règle de lecture accusait l'instrument pour un mécanisme

*(2026-09-17, relevé par Alexandre.)*

*« 9 perdus sur 13 ne portent aucune parenthèse, alors que ta propre règle de
lecture dit que ce cas signale l'instrument. »*

**La règle que j'avais écrite n'avait que deux branches**, et la seconde était
fausse :

| | ce qui change | verdict |
|---|---|---|
| **parenthèse au nom DÉTECTÉ** | le préfixe, donc les lignes récupérées | mécanisme |
| **parenthèse chez un CANDIDAT** | le score du candidat, qui perd un discriminant | ⚠️ **mécanisme aussi** |
| **aucune parenthèse NULLE PART** | rien ne peut avoir changé | **instrument** |

*Mesuré sur un cas construit* : détecté `Solutions BCITI inc` → `100` contre
`85.5`, **RETENU**. Parenthèse retirée côté registre, `Solutions BCITI (Groupe
Nordet) inc` devient identique au premier → `100` contre `100`, **AMBIGU**.
**Une perte réelle, et le registre a perdu ce qui séparait deux entreprises.**

⚠️ **Le compteur qui accuse l'instrument ne compte plus que la troisième
branche**, et il la mesure sur le VRAI pool de récupération — *pas sur les cinq
candidats rendus, parce que le score d'un NEQ vient du meilleur de ses noms.*

---

## N97 — Un signal trop faible pour IDENTIFIER peut être assez fort pour EXCLURE

*(2026-09-17, raisonnement d'Alexandre.)*

**« Lévis » ne désigne aucune entreprise.** *Apparier depuis rien avec une ville
est impossible, et c'est pour ça que l'adresse paraissait sans usage.*

**Mais départager deux candidats DÉJÀ TROUVÉS est une autre opération** : si l'un
est à St-Isidore et l'autre à Laval, la question est réglée — **sans toucher à
aucune échelle**.

> **Les 3 244 ambigus ne manquent pas de TOLÉRANCE. Il leur manque un signal qui
> ne dépend pas du nom.**

⚠️ *Et un départage ÉCARTE un candidat; il n'en CONFIRME aucun.* **Une ville qui
concorde ne prouve pas l'identité** — deux entreprises distinctes peuvent partager
une ville, et c'est le cas courant à Montréal.

**La question qui décide si le correctif vaut la peine** : le candidat retenu par
la ville est-il celui qui avait **déjà** le meilleur score? *S'il l'est presque
toujours, la ville confirme sans apporter. Si c'est souvent l'autre, le score se
trompait de gagnant* — **et c'est un fait beaucoup plus lourd**.

⚠️ **Trois issues, pas deux.** *Quand plusieurs concurrents partagent le meilleur
score, la question n'a pas de réponse* — et les compter comme « confirmé » ferait
paraître la ville inutile là où **elle est la seule à avoir une opinion**.

---

## N98 — Mesurer l'apport d'un signal que le moteur consomme déjà le compterait deux fois

*(2026-09-17.)*

`resolve_neq_by_name` **ajoute déjà +5 quand `Company.ville` concorde**. *Là où la
ville est promue, le signal est en partie consommé — et l'ambiguïté a SURVÉCU au
bonus.*

⚠️ **Le gisement est donc là où la ville N'EST PAS promue** : présente dans
`Signal.champs`, jamais vue par le moteur. **Un plafond qui mélangerait les deux
provenances annoncerait comme gain ce qui est déjà appliqué.**

*Et le champ n'est pas promu pour rien* : `falkye/sources/eimt.py` capture
l'adresse dans `champs` sans jamais la passer à `RawSignal.adresse`. **Le champ
existe, la donnée existe, le pont entre les deux n'existe pas** — et **le
correctif attend ce chiffre, il ne le précède pas.**

---

## N99 — Un correctif qui ferme un défaut peut laisser l'inquiétude entière : dire LAQUELLE des deux moitiés il a fermée

*(2026-09-17.)*

Alexandre : *« `candidats_par_nom` fait `LIMIT 2000` sans `ORDER BY`. »*

**L'`ORDER BY` a été posé le 2026-09-16** — après son propre relevé. *Et il ne
règle pas ce qu'il vise.*

| | avant | après l'`ORDER BY` |
|---|---|---|
| **le lot change-t-il entre deux exécutions?** | oui | **non** — fermé |
| **le lot contient-il la bonne ligne?** | inconnu | ⚠️ **toujours inconnu** |

> **Trier par `nom_normalise` rend le tirage REPRODUCTIBLE, pas MEILLEUR.** Sur
> 50 000 « gestion… », les 2 000 retenus restent une tranche alphabétique.

⚠️ **Répondre « c'est corrigé » aurait fermé la bonne moitié et enterré
l'autre.** *Et l'autre porte sur tout ce qui a été mesuré depuis deux jours :
seuil, écart, parenthèses, ville — tout opère sur un lot dont personne n'a
vérifié qu'il contient le bon candidat.*

---

## N100 — Une borne qui COUPE n'est pas une PERTE, et le compte des coupes borne le risque sans l'établir

*(2026-09-17.)*

*Un préfixe qui rend 51 000 lignes dont la bonne est la douzième alphabétique
SATURE ET RÉCUPÈRE.* **La saturation est une condition nécessaire de la perte,
jamais sa preuve.**

⚠️ **Établir la perte demanderait de connaître le bon candidat** — donc une
vérité de terrain qui n'existe pas. *C'est un autre chantier, et il se décide
après celui-ci.*

**Ce qui rend le compte utile quand même, c'est sa forme négative** : *si la
borne ne sature JAMAIS, le lot est complet et l'hypothèse ne récupère rien.*
**Le chantier se ferme alors sans avoir été construit** — et c'est le meilleur
rendement qu'une mesure puisse avoir.

**Et « 2 000 sur 2 100 » n'est pas « 2 000 sur 51 000 »** : la taille du gisement
se mesure à côté de la coupe, sinon le mot « saturé » couvre les deux.

---

## N101 — Une règle de tirage doit être ÉNONCÉE pour pouvoir être contestée

*(2026-09-17, exigé par Alexandre.)*

*« Si les dix sont pris par `id` croissant, c'est le cas 19 — le tri du fichier
promu en échantillon. »*

**L'ordre des `id` est l'ordre d'arrivée des signaux, donc celui des fichiers
sources** : dix premiers, c'est dix dossiers de la même source, du même
trimestre, souvent du même secteur.

**La règle retenue, en quatre lignes, parce qu'une règle qu'on ne peut pas lire
ne peut pas être refusée :** tri par score croissant; rangs régulièrement espacés
sur toute la fenêtre; un seul dossier par préfixe de récupération; à score égal,
l'`id` — *la seule part arbitraire, et elle est bornée aux ex æquo.*

⚠️ **Et le mode « les dix premiers » existe, en l'annonçant** : *un échantillon
qui ne représente rien reste utile si personne ne croit qu'il représente quelque
chose.* **Ce qui nuit n'est pas le mauvais échantillon, c'est le mauvais
échantillon silencieux.**

---

## N102 — Une distribution dit COMBIEN; elle ne dit jamais QUOI

*(2026-09-17, Alexandre.)*

**2 713 dossiers sur 4 733 ont leur meilleur score dans une fenêtre de TROIS
POINTS.**

> *Une distribution naturelle ne fait pas ça — c'est une différence systématique
> qui se répète et coûte toujours à peu près les mêmes points.* **Et personne ne
> l'a jamais regardée.**

⚠️ **Trois jours de ventilations n'ont rien ouvert; un cas entier a nommé le mur
en une commande.** *Le pic est une preuve qu'il y a quelque chose, et une
incapacité à dire quoi.*

**La contrepartie, et elle est obligatoire** : ce qu'une lecture ouvre doit être
**RECOMPTÉ** avant de devenir un chantier. *Le cas `(Workstaff)` a nommé le mur;
le chiffrage a dit qu'il pesait 205 dossiers sur 8 931 — réel, et pas le mur.*

---

## N103 — Une borne recopiée en dur ment le jour où la borne change

*(2026-09-17.)*

`candidats_par_nom` portait `limite: int = 2000`. **Un outil qui mesure la
saturation en écrivant `2000` continuerait d'annoncer « saturé » sur une borne
devenue 5 000** — *ou l'inverse, plus silencieusement.*

**La borne est devenue `LIMITE_CANDIDATS_PAR_NOM`, et l'outil la LIT.** *Même
règle que `requete_nom_exact`, `neq_retenu` et `famille_de` : ce qui décide se
nomme une fois et s'emprunte.*

**Et la récupération elle-même s'instrumente par un `journal` optionnel**, `None`
en production : *combien chaque requête a rendu, quel repli a servi, si le pont a
rogné la liste.* **Un outil qui aurait recopié les requêtes pour les compter
aurait mesuré sa copie** — c'est déjà arrivé une fois cette semaine, et ça a coûté
338 dossiers imaginaires.

---

## N104 — Ce que les deux mesures du 17 ont rendu, et qui ne bouge plus

*(2026-09-17, Alexandre.)*

**Les parenthèses — piste CLOSE.** La correction rend **+17** et en casse **13**.
*« FERME BELLEVUE (1997) INC. » privée de sa parenthèse passe de 86 à 95 contre
« Ferme Bellevue et Fils inc. », et l'écart s'effondre.* **Négligeable, pas
fausse** — et le compteur d'instrument à **0** valide le tableau.

**Le départage par ville** : **1 111 sur 3 244 ambigus — 34,2 %**. Le gisement est
bien `Signal.champs` jamais promue : **2 484 dossiers, tous EIMT**.

| | |
|---|---|
| le gagnant était **déjà seul mieux scoré** | **963** |
| le gagnant est **un autre candidat** | **45** |
| **ex æquo** — le score ne tranchait pas | **103** |

⚠️ **Elle CONFIRME plus qu'elle ne CORRIGE.** *Le score se trompe rarement de
gagnant* — 45 fois sur 1 111. **Ce que la ville apporte, c'est le déblocage, pas
la correction** — et les 103 ex æquo sont les seuls cas où elle est la seule à
avoir une opinion.

**Reste environ 7 100 dossiers**, et l'hypothèse de la borne est ce qui décide
s'ils sont entamables.

---

## N105 — Un `ORDER BY` alphabétique rend le tirage reproductible ET systématiquement mauvais

*(2026-09-17, établi par Alexandre sur les dix paires.)*

**Sept des dix candidats retenus sont en TÊTE ALPHABÉTIQUE de leur préfixe** :
`LES " 100 " AILE`, `FERME 100 MILES`, `J 2 B`, `La 115e`, `L'0EIL A LA TOUCHE`.

**Le mécanisme, et il est entier dans l'ordre de trois caractères :**

```
" " < "0" … "9" < "a" … "z"
```

*`normaliser` remplace la ponctuation par des espaces* — `LES " 100 " AILE`
devient `les 100 aile` — **et l'espace trie avant les chiffres, qui trient avant
les lettres.** Le lot de 2 000 est donc rempli par le début de l'ordre
alphabétique, et **l'`ORDER BY` posé le 16 septembre garantit qu'on regarde
toujours ce même début.**

> ⚠️ **Le correctif de la reproductibilité a figé le mauvais tirage.** *Il n'a
> rien cassé — il a rendu constant ce qui était aléatoire, et le constant se
> trouve être mauvais.*

**Mesuré** : `ferme` → 23 061 lignes, **8,7 % vues**. `les` → 163 296 lignes,
**1,2 %**. `l` → 309 788 lignes, **0,6 %**.

**Et la coupe se concentre là où ça échoue** : 74,3 % des trop faibles ont un lot
coupé, contre 26,0 % des RETENU. *Préfixe parlant : 57,1 %. Préfixe numérique :
0,2 %.*

---

## N106 — Une distribution concentrée sur UNE valeur n'est pas une population, c'est un calcul

*(2026-09-17, Alexandre.)*

**Le score 85,50 revient huit fois sur dix.** *C'est ce que `WRatio` rend quand
seul le PREMIER MOT correspond.*

> **Le pic de 2 713 dossiers est un PLANCHER TECHNIQUE, pas une distribution de
> ressemblance.**

⚠️ **Conséquence, et elle ferme un chantier** : *un plancher de calcul ne se
franchit pas par un réglage d'échelle.* **Abaisser le seuil à 85 ne récupérerait
pas 2 713 appariements proches — il accepterait 2 713 noms qui partagent un mot
et rien d'autre.**

*« Ce ne sont pas des appariements qui manquent de peu — ce sont des noms qui
partagent le premier mot. »* **Aucune des dix paires n'était l'entreprise
cherchée.**

**La contre-épreuve à faire, et elle est dans la mesure** : la distribution des
valeurs EXACTES. *Si une seule valeur pèse l'essentiel du pic, la cause est le
calcul; si les valeurs sont étalées, c'est une population.*

---

## N107 — Une constante écrite en valeur par défaut est décorative : Python l'évalue une fois, à l'import

*(2026-09-17, découvert par un test qui passait sur un lot qu'il croyait coupé.)*

```python
def candidats_par_nom(…, limite: int = LIMITE_CANDIDATS_PAR_NOM):   # ⛔
```

**La constante existait, le code la nommait, et la changer n'avait aucun effet.**
*Ni dans un test, ni dans un outil, ni au déploiement.*

```python
def candidats_par_nom(…, limite: int | None = None):
    if limite is None:
        limite = LIMITE_CANDIDATS_PAR_NOM                            # ✓
```

> **Une constante qu'on ne peut pas faire varier n'est pas la source de vérité,
> c'est une copie de plus** — celle du jour de l'import.

**Et le même jour, une trace portait `BORNE_MOTEUR = 2000` en dur.** *Un
diagnostic qui annonce une borne que le moteur n'applique plus ment sur ce qu'il
diagnostique.* **Elle est empruntée maintenant**, et un test vérifie que c'est le
MÊME objet, pas la même valeur.

---

## N108 — Un garde qui écarte les pires cas doit COMPTER ce qu'il écarte, sinon le biais devient le résultat

*(2026-09-17.)*

La mesure C lève la borne, donc charge **tout le gisement du préfixe** : `l` rend
**309 788 lignes**. Un plafond mémoire est nécessaire.

⚠️ **Et ce plafond écarte exactement les cas où la borne fait le plus mal.**
*Mesurer « ce qu'une borne levée rapporterait » en excluant les gros gisements
mesurerait le contraire de la question.*

**Donc : le plafond se déclare, les refus se comptent, et leurs gisements
s'affichent** — pour dire ce qu'un plafond relevé coûterait. *C'est la même règle
que le cas 34 : un garde couvre ce que la mesure a couvert, et il doit dire où
il s'arrête.*

**Et le budget s'annonce AVANT d'être dépensé** : taille de l'échantillon, règle
de tirage, lignes à charger, plus gros gisement retenu, ordre de grandeur mémoire
*avec son hypothèse par ligne, annoncée comme une estimation et pas comme une
mesure.*

---

## N109 — Les deux côtés d'une simulation prennent les MÊMES entrées, y compris celles qu'on croit accessoires

*(2026-09-17, attrapé à l'écriture.)*

La mesure C rejouait la récupération **sans la ville**, alors que le score de
référence l'avait **avec** (`+5` quand elle concorde).

⚠️ *La borne levée aurait paru PIRE qu'elle n'est, et l'écart aurait été attribué
à la borne.* **C'est le défaut des -338, en miroir** — la fois précédente un côté
avait le bonus et l'autre non; cette fois-ci le côté privé était le nouveau.

> **Une comparaison ne compare que ce qui ne change pas à côté.** *La ville
> n'était pas le sujet, et c'est exactement ce qui la rendait facile à oublier.*

---

## N110 — Un tableau dont les lignes ont plus de colonnes que l'en-tête : la colonne muette était celle qui portait le sens

*(2026-09-17, trouvé en versant le chantier 3+4 au corpus.)*

Le tableau de l'écart arrivait ainsi :

```
| écart | NEQ > 2 dossiers | 2e NEQ à moins de | gain |     ← 4 colonnes
| 6     | 1 | 26 | 138 | 138 |                              ← 5 valeurs
| 8     | 1 | 26 | **0** ← témoin |                          ← 3 valeurs
```

**L'en-tête avait perdu « dossiers dans ces groupes »**, et la ligne du témoin avait perdu son `0`.
*La sortie de l'outil en rend cinq; la transcription à la main en a gardé quatre.*

⚠️ **Ce qui rend ce défaut coûteux, c'est qu'il se lit quand même.** Un rendu Markdown coupe
silencieusement les cellules en trop : le tableau s'affiche, aligné, **avec `26` sous « 2e NEQ à moins
de » et `138` sous « gain »** — deux chiffres exacts rangés sous les mauvais titres.

> **Une colonne de trop ne casse rien. Elle décale tout.**

**Le garde qui l'attrape est trivial** : compter les barres verticales de chaque ligne d'un bloc et les
comparer à l'en-tête. *Il tourne en une seconde sur tout le corpus.*

---

## N111 — Un compte dans un document d'aiguillage vieillit en silence, parce que personne ne relit l'aiguilleur

*(2026-09-17.)*

`FALKYE-000-PAR-OU-COMMENCER.md` annonçait **« six existent »** pour les documents de chantier et
**« 28 incidents réels »** pour le journal des cas. *Au 17 septembre : sept, et quarante-deux.*

**C'est le même défaut que `profil_des_6176.py`**, déplacé d'un nom de fichier vers une table de
renvois : *un chiffre écrit à côté de la chose qu'il compte, là où personne ne va le vérifier — parce
qu'on ouvre l'aiguilleur pour savoir OÙ aller, jamais pour le relire.*

⚠️ **Et l'aiguilleur est le document le plus lu du corpus**, donc celui dont un chiffre faux circule le
plus. **La liste des chantiers y est maintenant nommée** — `1, 2, 3+4, 21, 22, 28, 29` — *une liste se
périme aussi, mais elle se périme VISIBLEMENT : un document manquant se voit, un « six » ne se voit pas.*

---

## N112 — Dix cas disent qu'une chose EXISTE; ils ne disent jamais COMBIEN DE FOIS

*(2026-09-17, établi par le recomptage, mesure A.)*

Sur dix paires du pic, **sept candidats étaient en tête alphabétique de leur préfixe** — `LES " 100 " AILE`, `FERME 100 MILES`, `J 2 B`, `La 115e`. **On en a tiré une explication** : *la tranche commence par les chiffres et la ponctuation et n'atteint jamais les lettres.*

**Le recomptage la dément :**

```
lots coupés AVANT LA PREMIÈRE LETTRE : 17 sur 4 217   (0,4 %)
au point de coupe : « espace puis lettre » 4 072   96,6 %
dans la tranche entière : non alphabétique 776 568 / 6 342 752   12,2 %
```

⚠️ **Le mécanisme est RÉEL. Sa fréquence ne l'était pas.** *Sept sur dix était un artefact du tirage, pas une proportion* — et l'explication qu'on en a tirée était fausse **alors que chacun des dix cas était exact.**

> **Un cas entier ouvre une question; il ne la ferme pas.** La règle du 16 septembre disait de tracer un cas quand les ventilations ne rendent rien. **Elle ne disait pas de conclure dessus** — et c'est la moitié qui manquait.

**Ce qui survit, et ce n'est pas rien** : la borne coupe 4 217 lots, dont 74,3 % des trop faibles. *Ce qui tombe, c'est l'explication de POURQUOI la coupe fait mal.* **La question redevient ouverte, et c'est un progrès : elle était fermée sur une erreur.**

**Le contre-exemple utile, le même jour** : l'autre observation des dix paires — *85,50 huit fois sur dix* — a été **confirmée** par le même recomptage, à 89,2 % du pic. *Un échantillon n'est pas systématiquement trompeur; il est systématiquement muet sur les fréquences.*

---

## N113 — Le recoupement interne d'une mesure : ce qui dit qu'un instrument lit bien l'objet qu'il prétend lire

*(2026-09-17.)*

La mesure A a rendu deux chiffres qui n'étaient pas demandés et qui l'ont validée :

- **les 17 lots « coupés avant la première lettre » sont EXACTEMENT les 17 lots « hors préfixe »** — les seuls où le préfixe n'a rien rendu et où le repli par sous-chaîne a servi. *Deux comptes obtenus par deux chemins différents dans le même passage, et ils coïncident.*
- **6 342 752 candidats pour 4 217 lots font 1 504 par lot**, contre une tranche théorique de `limite − limite//4 = 1 500`. *La part réservée au pont est bien retirée de l'ordre alphabétique, et l'écart de 4 est la part des lots où le pont n'avait pas 500 candidats à offrir.*

⚠️ **Aucun des deux n'était le but de la mesure.** *Ils disent que l'instrument a lu la tranche alphabétique et pas autre chose* — et c'est précisément ce qu'un chiffre cohérent et faux ne peut pas offrir.

> **Une mesure qui ne rend qu'un chiffre ne peut pas être vérifiée; une mesure qui en rend deux liés se vérifie elle-même.** *Quatre instruments de ce chantier ont produit des chiffres cohérents et faux — le recoupement interne est le seul garde qui les aurait attrapés sans une seconde mesure.*

---

## N114 — La clé de récupération était un MOT VIDE, et c'est une apostrophe devenue une espace

*(2026-09-17, après la mesure C.)*

`normaliser` remplace la ponctuation par des espaces. **Donc le « premier mot » d'un nom n'est pas son premier mot :**

| nom publié | forme normalisée | préfixe de récupération |
|---|---|---|
| `L'INDUSTRIE MONDIALE DU NORD INC.` | `l industrie mondiale du nord inc` | **`l`** |
| `S.E.N.C. Beaulieu et Fils` | `s e n c beaulieu et fils` | **`s`** |

**La récupération s'ancre sur le mot qui ne dit rien**, et `industrie`, `mondiale`, `nord`, `beaulieu`
sont dans la chaîne sans jamais servir. ⚠️ **Les trois préfixes que le plafond de C a dû refuser — `l`
(309 788 lignes), `s` (221 412), `le` (205 071) — sont exactement ceux-là.**

> **Le gisement n'est pas gros parce que le nom est courant. Il est gros parce que la clé est vide.**

*C'est aussi ce qui range les quatre directions* : celle qui utilise les AUTRES mots règle ces cas par
construction; celle qui réduit le volume les laisse. **Régler `ferme` et pas `le`, c'est régler la
moitié du problème, littéralement.**

---

## N115 — Le coût dominant d'une résolution est le SCORAGE, pas la requête — donc un meilleur lot coûte MOINS

*(2026-09-17.)*

Par résolution : deux `GLOB` indexés bornés, deux replis possibles, une jointure — **puis
`process.extractOne` sur ~2 000 groupes avec toutes leurs formes.** *Le temps est là.*

⚠️ **Conséquence, et elle renverse l'intuition** : lever la borne sur `l` ne multiplie pas une requête,
**il multiplie par 155 le nombre de formes à scorer.** Et inversement, **une récupération qui présente
300 formes pertinentes au lieu de 2 000 arbitraires est MOINS chère qu'aujourd'hui, pas plus.**

> **« Plus de portée » et « plus cher » ne sont pas la même phrase.** *On les avait confondues depuis le
> début : la borne était traitée comme une protection de coût, alors qu'elle protège d'un coût qu'un
> meilleur index supprimerait.*

---

## N116 — Une structure qui rend la non-régression IMPOSSIBLE vaut mieux qu'une qui la mesure

*(2026-09-17, en départageant quatre directions.)*

Trois des quatre directions envisagées changent le lot présenté au scoreur — donc exposent les **805**
dossiers déjà retenus, *et demandent une non-régression mesurée.*

**La quatrième — récupérer en deux temps, n'élargir que si le premier temps a échoué — ne les expose
pas** : le second temps ne s'exécute jamais là où le premier a réussi.

> ⚠️ **Ce n'est pas une garantie plus forte, c'est une garantie d'une autre nature.** *Une non-régression
> mesurée vaut le jour où on l'a mesurée; une non-régression structurelle vaut tant que la structure
> tient.*

**Et le prix de cette garantie est ailleurs, il faut le dire** : la résolution tourne **par signal**, et
une résolution réussie n'écrit jamais dans le dossier qui a échoué. *Donc « seuls les échecs paient »
veut dire « les mêmes échecs paient, à chaque cycle, indéfiniment ».* **Le journal des tentatives —
`(forme, édition du miroir, verdict)` — borne ce coût, et sa clé le fait s'invalider tout seul au
réimport.**

⚠️ *Préalable non satisfait* : **« l'édition du miroir » n'existe pas** — aucune marque de niveau
instantané dans les modèles du miroir, seulement des dates par ligne.

---

## N117 — J'ai désigné un outil comme mesurant une chose qu'il ne mesure pas, et l'erreur est exactement celle qu'il dénonce

*(2026-09-17, relevé par Alexandre.)*

**Écrit dans la conception** : *« E, le coût en ambiguïté, sur
`outils/impact_tous_les_noms.py`, écrit le 16 septembre pour cette réserve exacte
et jamais lancé. »* **Faux.**

`impact_tous_les_noms` mesure ce que **garder tous les noms À L'IMPORT** change :
il compare `Nom.csv` **sur disque** aux dossiers du produit, **et ne consulte
jamais `req_noms`.** *Sa section « coût » porte sur l'ajout de noms au pont, pas
sur un changement de clé de récupération.*

| | mécanisme | coût propre |
|---|---|---|
| **garder tous les noms à l'import** | ce que le miroir CONTIENT | volume, durée d'import, concurrents qui apparaissent |
| **changer la clé de récupération** | ce que le lot PRÉSENTE | scorage par résolution, non-régression des 805 |

> ⚠️ **Chiffrer l'une en croyant chiffrer l'autre ferait décider sur le mauvais
> chiffre** *(Alexandre)*. **Et c'est ce que le nom « mesure E » a failli faire
> faire.**

**La leçon, et elle est sur moi** : *un outil ne mesure pas ce que son sujet
suggère, il mesure ce que son code lit.* **Vérifier quelle table il interroge
avant de lui donner un rôle** — `impact_tous_les_noms` n'ouvre jamais le miroir,
et ça se voit en dix lignes de lecture.

---

## N118 — Deux chiffres qui ne peuvent pas être vrais ensemble désignent une chaîne, pas une erreur

*(2026-09-17, relevé par Alexandre.)*

**6 009 résolutions franches** *(`impact_tous_les_noms`)* contre **805 retenus**
*(rejeu complet du 16, ventilation identique chiffre pour chiffre)*.

⚠️ **Aucun des deux n'est faux.** *Ils mesurent deux points différents d'une même
chaîne*, et l'écart entre eux est la somme de ce qui casse entre les deux :

```
1. le nom est-il AU MIROIR (req_entries ∪ req_noms)?      ← manque à l'import
2. combien de NEQ DISTINCTS portent cette forme?          ← ambiguïté du nom
3. le NEQ est-il DANS LE LOT que la récupération rend?     ← LA BORNE
4. que décide le moteur (seuil 92, écart 8)?               ← les échelles
```

**La bonne réaction n'était pas de choisir lequel croire, c'était de mesurer où
la chaîne casse** — et **chaque chute nomme son mécanisme**, donc son correctif.

⚠️ **Et le premier maillon renverse ou non l'ordre des priorités.** *Si les noms
sont déjà au miroir, le 6 009 est le même mur vu depuis l'import et il ne passe
pas devant l'index par mots. S'ils manquent vraiment, cette correction passe
devant tout le reste.* **La question ne se tranche pas par le raisonnement.**

---

## N119 — « Réversible » se vérifie champ par champ, pas geste par geste

*(2026-09-17, trouvé en répondant aux trois questions d'Alexandre avant d'appliquer.)*

L'instantané de la passe de reprise portait `neq` et `statut_resolution`. ⚠️ *Or
`_enrich_from_req` réécrit **huit autres champs*** — `nom_officiel_req`,
`statut_legal`, `adresse`, `ville`, `region`, `code_postal` et les deux du
secteur.

> **Défaire rendait le NEQ et laissait le reste : un dossier ni dans son état
> d'avant, ni dans celui d'après.** *L'outil affirmait pourtant porter « l'état
> d'avant de chaque dossier touché ».*

**Trois correctifs, et le troisième est celui qui tient :**

1. l'instantané capture les huit champs;
2. `--defaire` existe — *« pour défaire, l'instantané porte l'état d'avant »
   était une phrase, pas une commande*, et c'est le reproche que l'outil
   adressait lui-même au chemin d'archive du diff;
3. **un test compare la liste de l'instantané au CODE de l'enrichissement**, par
   lecture de l'arbre syntaxique. *Un champ ajouté là-bas et oublié ici rendrait
   le retour arrière partiel, en silence.*

**Et défaire REFUSE de toucher ce qui a bougé depuis** : un dossier dont le NEQ
n'est plus celui qu'on avait posé n'est plus le nôtre.

---

## N120 — Idempotent sur les dossiers ne veut pas dire idempotent sur le journal

*(2026-09-17.)*

La passe de reprise est idempotente sur les **écritures aux dossiers** : un
dossier posé sort de la population, puisqu'elle se définit par
`Company.neq IS NULL`.

⚠️ **Mais un dossier CONSERVÉ y reste** — donc il était **re-journalisé à chaque
exécution**, et `journaliser_candidat_fusion` n'a aucune garde de doublon.

> **Et c'est précisément la file qu'un humain doit dépiler.** *La polluer de
> doublons rend le travail plus long à chaque relance* — l'effet est invisible
> dans la base et visible seulement pour la personne qui trie.

**La question « que se passe-t-il si on l'applique deux fois » a donc DEUX
réponses**, une par famille d'écriture. *Poser la question une seule fois pour
tout le geste aurait rendu « idempotent » sans réserve.*

---

## N121 — Un écart de 16 000 qu'on avait noté sans l'expliquer portait la réponse à la question

*(2026-09-17.)*

**La question** : le 6 009 de `impact_tous_les_noms` est-il un gain disponible, ou déjà en base?

**La réponse était dans un écart relevé et laissé de côté** : l'outil annonce **1 521 816** noms en
vigueur, `req_noms` en porte **1 505 879**. *On avait noté « environ 16 000 » et on était passé à
autre chose.*

```
1 521 816  −  15 937  =  1 505 879
                ↑ paires (NEQ, nom normalisé) en double, mesurées le 16 septembre
```

⚠️ **L'écart n'était pas des noms manquants : c'étaient les mêmes noms comptés deux fois** — deux
`TYP_NOM_ASSUJ` portant la même graphie. **Le pont les déduplique par sa clé composite; la mesure
additionne des lignes.**

**Et la lecture du code ferme la boucle** : `_charger_tous_les_noms` et `impact_tous_les_noms` lisent
le même fichier, les mêmes colonnes (`NEQ`, `NOM_ASSUJ`, `STAT_NOM`), le même filtre et la même
normalisation. *Les deux ensembles sont identiques.*

> **Donc les 6 009 sont déjà en base à la ligne près, et ne représentent aucune récupération
> disponible. La piste des noms en vigueur est close — par arithmétique, sans relancer une mesure.**

**La leçon** : *un écart qu'on ne sait pas expliquer n'est pas un détail de comptage — c'est une
question ouverte, et elle peut porter la réponse d'une autre.* **« Environ 16 000 » aurait dû être
tranché le jour où il est apparu; il aurait épargné une mesure et une conception.**

---

## N122 — Un filtre échoue FERMÉ, et un pont vide ressemble à une archive plus petite

*(2026-09-17, trouvé en concevant le traitement de l'archive.)*

```python
if (row.get("STAT_NOM") or "").strip().upper() != "V":
    continue
```

⚠️ **Si `STAT_NOM` est renommée, `.get` rend `None`, la comparaison est vraie pour TOUTE ligne, et
`req_noms` se vide.** *L'import rend « 0 noms indexés » et se déclare réussi.*

> **Un filtre qui échoue fermé ne produit pas une erreur, il produit une population.** *Et une
> population vide est indistinguable d'une source qui a maigri.*

**Le remède n'est pas une vérification de colonne** — il y en a déjà une, par lecture de l'arbre
syntaxique, et elle est bonne. **C'est un PLANCHER sur la part retenue** : `Nom.csv` rend aujourd'hui
~32,7 % de lignes en vigueur, et une part qui s'effondre est **un refus bruyant, pas un compte plus
petit**. *Et le seuil se pose au registre des sources, avec ceux de la quarantaine — un retrait
anormal met la source en quarantaine, il ne réduit pas le miroir.*

⚠️ **Le garde des colonnes couvre les fichiers qu'on LIT.** Il ne dit rien d'un septième CSV qui
apparaîtrait : `FICHIERS_REQ_REELS` vérifie une présence, jamais une absence d'inattendu.

---

## N123 — L'identité d'une édition se calcule sur son contenu, jamais sur son nom

*(2026-09-17.)*

**Le REQ publie deux archives par mois, le 2 et le 16.** *Et rien, dans le miroir, ne dit de quelle
édition il vient* — donc rien ne peut dire qu'une tentative a échoué contre celle du 2 septembre, et
**rien ne sait qu'il faut réessayer après un import.**

⚠️ **L'empreinte ne peut pas être le nom du fichier.** *Un humain renomme, télécharge deux fois,
garde une copie.* **Elle se calcule sur le contenu, et sans décompresser** : les `file_size` et les
`CRC` des membres CSV, lus dans le répertoire du zip — *`zipfile` les expose déjà, et `inspect_zip`
les lit déjà.*

> **Deux archives identiques rendent la même empreinte; deux éditions différentes ne peuvent pas la
> partager.** *C'est ce qui rend l'invalidation automatique au réimport — par la clé, pas par une
> tâche d'entretien.*

---

## N124 — J'ai classé un fichier entier sur son NOM, et un gisement est resté ignoré une journée de plus

*(2026-09-17, relevé par Alexandre après ouverture complète de l'archive.)*

**Écrit dans ma conception** : *« deux fichiers de relations NEQ→NEQ qui sont en
aval. »* **`FusionScissions.csv` porte `DENOMN_SOC` — une dénomination sociale
remplie à 99,9 %, 132 448 formes rattachées à des NEQ vivants.** *La relation,
c'est `NEQ_ASSUJ_REL`; la dénomination est un nom, et je ne l'avais pas
regardée.*

**L'inventaire réel est de QUATRE gisements de noms, pas un :**

| gisement | fichier | formes | exploité avant le 17 |
|---|---|---|---|
| `NOM_ASSUJ` | `Nom.csv` | 4 651 087 | oui, filtré `STAT_NOM='V'` |
| `NOM_ASSUJ_LANG_ETRNG` | `Nom.csv` | 412 459 | **non — colonne jamais lue** |
| `NOM_ETAB` | `Etablissements.csv` | 257 531 | non, pour apparier |
| `DENOMN_SOC` | `FusionScissions.csv` | 132 448 | **non — classé « en aval »** |

⚠️ **Le nom du fichier décrivait son ÉVÉNEMENT, pas son CONTENU.** *Un fichier
qui s'appelle « fusions et scissions » contient aussi les noms des entreprises
qui fusionnent* — et `inspect_zip` existait depuis le 31 août pour le dire en
quelques kilo-octets.

> **Classer un fichier sur son nom est la même faute que compter une colonne sur
> son libellé.** *La commande qui tranche coûte dix secondes.*

---

## N125 — Un garde par lecture de l'arbre syntaxique ne voit pas ce qui vient d'une table

*(2026-09-17, trouvé à l'écriture.)*

`colonnes_brutes_lues` extrait les en-têtes lues en cherchant `row.get("…")` dans
l'AST — **et c'est un bon garde**, il attrape même la virgule oubliée entre deux
littéraux.

⚠️ **Mais la passe des quatre gisements fait `rangee.get(colonne)`, où `colonne`
vient de `GISEMENTS_DE_NOMS`.** *Aucun arbre syntaxique ne peut lire une valeur
qui n'est pas là.* **Les quatre gisements sortaient donc de la vérification
d'en-tête en silence** — exactement le défaut que le garde existe pour attraper.

**Le correctif : deux sources de vérité, et il faut les deux.** *L'AST pour les
lecteurs qui nomment leurs colonnes en littéral, une DÉCLARATION pour ceux qui
les prennent dans une table.* **Et un test qui retire chaque colonne de gisement
une à une et vérifie que le garde refuse.**

> **Un garde a une portée, et sa portée s'écrit à côté de sa sortie** *(cas 33)*.
> *Celui-ci couvrait « les colonnes nommées en dur », et le code avait cessé de
> les nommer en dur.*

---

## N126 — Un index et sa requête ont deux découpeurs, et leur divergence ne lève nulle part

*(2026-09-17, en construisant l'index par mots.)*

L'index est bâti **en SQL** — une CTE récursive qui coupe `nom_normalise` sur
l'espace. La requête découpe **en Python**, par `mots_du_nom`.

⚠️ **Si les deux divergeaient, aucune erreur ne se produirait.** *Le rappel
baisserait, et le chiffre serait attribué à autre chose* — au seuil, à l'écart,
à la population. **C'est la seule dégradation silencieuse que cet index puisse
subir, et elle est invisible par construction.**

**Le garde : un TÉMOIN à chaque import.** *Vingt formes prises dans l'ordre de la
clé — donc reproductibles, pas un tirage — doivent se retrouver ELLES-MÊMES par
l'index.* **Une seule qui échoue fait REFUSER l'import.**

> **Quand deux chemins doivent rendre la même chose et qu'aucun ne peut vérifier
> l'autre, la seule garde est un aller-retour.**

---

## N127 — À fréquence égale, l'alphabet n'est pas un critère

*(2026-09-17.)*

La récupération par mots choisit **le mot le plus rare**. *Sur un index réel
« du » est partout, donc jamais le plus rare* — **mais rien ne garantit qu'un mot
vide ne se retrouve pas à égalité**, et l'ordre naturel d'un tri Python aurait
alors choisi `du` plutôt que `mondiale`.

⚠️ **Un départage alphabétique est un tirage promu en critère** — *c'est le même
défaut que la tranche du `LIMIT`, un étage plus haut.*

**La règle retenue : à fréquence égale, le mot le plus LONG gagne.** *Elle est
énoncée, contestable et reproductible; l'alphabet n'est rien de tout ça.*

---

## N128 — Une conclusion vraie d'un état du code doit porter sa date

*(2026-09-17.)*

Le matin, l'arithmétique fermait la piste des noms en vigueur :
`1 521 816 − 15 937 = 1 505 879`, exactement `count(*)` de `req_noms`. **Elle
tenait parce que le pont filtrait `STAT_NOM='V'`, comme l'outil de mesure.**

**Le même jour, la décision a changé : tout entre.** ⚠️ *Donc l'identité ne vaut
QUE pour le miroir chargé avant ce changement.* **Après le prochain import,
comparer les deux comptes n'aura plus de sens** — et personne ne s'en
apercevrait, parce que les deux chiffres continueraient d'exister.

> **Un test qui verrouille une identité doit verrouiller aussi le jour où elle
> cesse d'être vraie.** *Celui-ci vérifie maintenant les deux moitiés : que le
> pont ne filtre plus, et que la conclusion est datée.*

---

## N129 — Le second temps a livré, et il a déplacé le problème plutôt que de le supprimer

*(2026-09-17, mesuré sur l'hôte.)*

```
RETENU          780  →  2 634   +1 854
ambigu        3 435  →  5 002   +1 567
trop faible   4 603  →  1 257   −3 346
✓ RETENUS perdus : 0            ← le témoin passe
```

**Les « trop faibles » ont chuté de 73 %, et la garantie structurelle tient** :
rien de ce qui marchait n'a bougé. *L'import a coûté 39,9 minutes et un pic de
3 976 Mo sur 7 758 — 51 %, contre 33 minutes et 3 535 Mo avant.* `req_noms` porte
**5 071 984 formes**, l'index par mots **14 989 589 couples**.

⚠️ **Mais 1 567 dossiers sont passés de « trop faible » à « ambigu ».** *Ce n'est
ni un gain ni une perte : c'est un déplacement.* **Le nom a donné tout ce qu'il
avait** — un ambigu n'est pas un dossier sans candidat, c'est un dossier avec
DEUX candidats que le nom ne sépare pas.

> **Un correctif qui réussit change la forme du problème restant.** *Mesurer
> seulement le gain aurait caché que la population suivante n'est plus la même,
> et que les outils d'hier ne s'y appliquent plus.*

---

## N130 — « Je ne sais pas » n'est pas « non » — la règle qui sépare un départageur d'un filtre

*(2026-09-17, à l'écriture des trois départageurs.)*

Un départage n'est prononcé que si **trois** conditions tiennent :

1. le **dossier** porte le fait;
2. **exactement un** concurrent est compatible;
3. ⚠️ **tous les autres concurrents PORTENT le fait** et sont incompatibles.

**Sans la troisième, un candidat sans code postal serait écarté pour n'avoir pas
de code postal** — *et le départageur deviendrait un filtre sur le REMPLISSAGE du
registre, pas sur l'identité.* **Le registre est rempli à 65,7 % côté domicile :
le filtre écarterait un tiers des candidats sans rien savoir d'eux.**

**Et les issues de refus sont nommées séparément**, parce qu'elles appellent
trois correctifs différents : *fait absent au dossier* (promouvoir un champ),
*fait absent chez un concurrent* (compléter le miroir), *plusieurs compatibles*
(il faut un autre fait).

⚠️ **Une quatrième issue n'est pas un départage : « le fait les exclut tous ».**
*Soit le bon candidat n'est pas dans le lot, soit le fait est sale.* **C'est un
signal, et il se compte à part.**

---

## N131 — Un code postal lu par fenêtre glissante invente des codes qui n'existent pas

*(2026-09-17, attrapé en écrivant le test.)*

`'St-Isidore, QC J0L  2A'` compacté donne `STISIDOREQCJ0L2A`. **Une lecture
caractère par caractère y trouve `J0L` — qui est le vrai — mais aussi `L2A`, qui
a exactement la forme d'une région de tri et n'en est pas une.** *De même
`G6V1A1` contient `V1A`.*

⚠️ **Un faux code rend un mauvais candidat « compatible », donc produit un FAUX
DÉPARTAGE** — le seul coût que ce départageur puisse avoir, et il naît de la
lecture, pas de la donnée.

**Le correctif : lire des JETONS, jamais une fenêtre.** *On découpe sur les
non-alphanumériques, on teste chaque jeton, et on recolle avec le suivant parce
que `J0L 2A1` s'écrit en deux jetons.*

**Et l'EIMT donne souvent un code TRONQUÉ** — cinq caractères sur six. *Comparer
un tronqué à un complet sur six rendrait toujours faux, et le départageur
paraîtrait inutile alors qu'il est mal lu.* **Deux niveaux : le code complet, et
la région de tri qui reste comparable.**

---

## N132 — Deux classifications qui ne se joignent pas par code : le dire plutôt que d'inventer la table

*(2026-09-17.)*

Le SEAO classe en **UNSPSC**, le REQ en **CAE**, et **aucune table ne les relie**.
*Inventer une correspondance serait décider à la place d'Alexandre, sur une
matière qui appartient au chantier 22.*

**Donc le départageur par activité compare les LIBELLÉS, et c'est une faiblesse
assumée.** ⚠️ **Ce qu'il rend est un PLANCHER** de ce que l'activité donnerait
avec la vraie table.

*Et les mots vides sont retirés — « autres », « services », « généraux », « non
classés ailleurs »* : **les garder ferait « concorder » une boulangerie et une
plomberie sur « autres services »**, ce qui est pire qu'aucun départage.

> **Un départageur qui se sait plancher est utilisable; un départageur qui se
> croit complet fait décider sur un chiffre qui n'est pas le sien.**

---

## N133 — Un repli n'est pas un second avis : il ne franchit pas une contradiction établie

*(2026-09-17, construction du départageur d'adresse.)*

La ville a été demandée **comme repli du code postal, dans le même départageur**.
Un repli se déclenche quand le niveau précédent **n'a pas tranché** — et il y a
**quatre façons de ne pas trancher, dont une seule n'en est pas une** :

| issue du code postal | la ville parle? |
|---|---|
| le dossier ne porte pas le fait | oui |
| un concurrent ne porte pas le fait | oui |
| plusieurs concurrents compatibles | oui |
| ⚠️ **aucun concurrent compatible** | ⚠️ **NON** |

⚠️ **« Le fait les exclut tous » n'est pas un silence : c'est un démenti.** *Le
code postal du dossier contredit tous les candidats. Laisser la ville — plus
grossière — en désigner un rendrait un départage dont on sait déjà qu'un fait
plus précis le dément.*

**Sur l'hôte, 443 dossiers sont dans ce cas.** *Ce sont ceux que la section 4 de
`outils/departage_par_ladresse.py` regarde au lieu de les trancher.*

> **Un repli répond à « je ne sais pas ». Il n'a rien à répondre à « non ».**

---

## N134 — Une non-régression se rend STRUCTURELLE, ou elle reste une intention

*(2026-09-17.)*

La non-régression sur les **2 634 retenus** a été demandée comme **critère, pas
comme effet secondaire acceptable**. Trois façons de la tenir, et elles ne valent
pas la même chose :

1. *« Le départageur ne s'applique qu'aux ambigus »* — **une intention.** Rien
   n'empêche un appelant futur de l'appeler ailleurs.
2. **La garde** : `departager_le_dossier` lève `PasUnAmbigu` sur tout dossier que
   le nom a déjà tranché. *L'appel ÉCHOUE au lieu de réussir discrètement.*
3. **La vérification sur les retenus RÉELS**, un par un, et **un code de sortie
   non nul si elle tombe** — *parce qu'une garde qu'on n'exécute jamais est une
   intention avec un nom de fonction.*

⚠️ **Et un critère qu'on ne peut pas faire échouer n'en est pas un** : un test
retire la garde et vérifie que l'outil sort en erreur au lieu de continuer.

> **Une garde protège quand elle refuse. Une garde qu'on décrit protège une
> phrase.**

---

## N135 — Un échantillon se tire à pas constant, jamais en tête

*(2026-09-17.)*

Pour dire lequel des deux — *le bon candidat n'est pas dans le lot*, ou *le fait
est sale* — il faut un échantillon des 443 exclusions. ⚠️ **Prendre les N
premiers promeut l'ordre de la base au rang de critère** *(cas 19)* — c'est
exactement ce qui avait fait lire « sept sur dix en tête d'alphabet » comme une
fréquence, alors que la mesure A a montré que la coupe tombe au milieu.

**Le tirage se fait donc à pas constant sur toute la population**, et le pas est
écrit dans la sortie.

Et la lecture se fait en **deux temps dont un seul coûte** :

1. **gratuit** — le bon candidat était-il déjà rendu, *hors de la fenêtre des
   concurrents*?
2. **coûteux** — sinon, était-il *hors du lot récupéré*? Il faut relancer la
   récupération à borne élargie, et **c'est ce temps-là que la section chiffre**.

⚠️ **Et la dernière ligne ne tranche pas.** *« Aucun candidat compatible même à
la borne élargie » se lit aussi bien comme « l'entreprise n'est pas au registre »
que comme « le code postal lu est celui d'un tiers ».* **Ce que l'échantillon
sépare, c'est ce qui est mécaniquement vérifiable; le reste demande une paire
lue — et c'est CETTE relecture-là qui décide du prix, pas la machine.**

---

## N136 — Une garde qui lit des LIGNES ne distingue pas le code du commentaire qui le cite

*(2026-09-17.)*

`tests/test_format_des_nombres.py` interdit la substitution posée sur la ligne
entière au lieu de la valeur *(N. voir `outils/nombres.py`)*. **Elle a refusé un
fichier où l'idiome n'était que dans un COMMENTAIRE qui l'expliquait.**

⚠️ *Le code était juste; c'est l'explication qui a fait tomber la garde.* Et
`nombres.py` est exempté **par son nom**, précisément parce qu'il cite l'idiome
dans sa docstring pour l'enseigner.

**Ce n'est pas un défaut de la garde** : une garde textuelle est bon marché et
sans faux négatif, et la payer en faux positifs sur les commentaires est le bon
échange. *Mais il faut le savoir, sinon on « corrige » du code déjà correct.*

> **Une garde qui coûte trois lignes et attrape tout vaut mieux qu'une garde
> exacte que personne n'écrit. L'écrire dans son message, c'est ce qui manque.**

---

## N137 — Un rappel qui ne bloque jamais et qui compte faux ne rappelle rien

*(2026-09-18, en versant `falkye-le-cerveau.md` au corpus.)*

`outils/verifier-corpus.py` affiche à chaque demande de fusion le nombre de notes
en attente au tampon. **C'est le seul garde-fou de la méthode du corpus** — arrêté
le 11 septembre comme **affichage, jamais blocage**, parce qu'une règle bloquante
aurait eu besoin de reconnaître une « fin de tâche », donc d'une sortie nommée,
donc d'un réflexe qui rassure sans couvrir.

⚠️ **Il comptait 87 notes sur 136.** Le tampon a changé de niveau de titre en cours
de route — **N1 à N87 en `###`, N88 et suivantes en `##`** — et le motif du rappel
ne reconnaissait que trois dièses. *Quarante-neuf notes étaient invisibles au seul
mécanisme qui existe pour les rendre visibles.*

⚠️ **Et ça ne s'est pas vu parce que le chiffre restait PLAUSIBLE.** Quatre-vingt-
sept notes en attente est un nombre crédible; rien dans la sortie ne détonnait.
*Un compteur en panne affiche zéro et se voit. Un compteur qui rate une moitié
affiche un chiffre qu'on lit sans y penser.*

**Le correctif est d'accepter les deux niveaux, pas de réécrire quarante-neuf
titres** : *un niveau de titre est une mise en forme, pas un sens — et une garde
qui exige une mise en forme exacte finit par mesurer la discipline typographique
plutôt que ce qu'elle surveille.*

*Divergence voisine, nommée et non corrigée* : le rappel lit les dates sous la
forme `- **Notée le** : AAAA-MM-JJ`, et **85 notes sur 136** portent leur date
autrement *(« la plus ancienne » est donc calculée sur 51 notes)*. **Le chiffre
qui compte — combien sont en attente — est juste depuis ce correctif; celui qui
dit leur ancienneté ne l'est pas.**

> **Un garde-fou qui ne bloque pas n'a qu'une chose à faire : dire vrai. Celui-là
> disait vraisemblable.**

---

## N138 — Ce qui fait d'un document un document de CHANTIER et non un relevé de mesures

*(2026-09-18, arbitré par Alexandre sur les deux versions du 3+4.)*

Deux versions du même document se sont présentées : douze sections et dix-huit.
**L'écart n'était pas du contenu en plus — c'était six sections de STRUCTURE** :
*Portée*, *Préalables*, *les points à construire*, *Tests exigés*, *Vérification
macro*, *Ce qui doit être livré*.

> **Ce sont elles qui font d'un document un document de chantier plutôt qu'un
> relevé de mesures.** *(formulation d'Alexandre)*

⚠️ **Un relevé de mesures dit ce qu'on a trouvé. Un document de chantier dit ce
qu'on va construire, ce qu'on ne construira pas, ce qui doit exister avant, et
comment on saura que c'est fini.** *Sans ces quatre, le document se lit — et ne
commande rien.*

**Et la section 7bis vaut mieux que ce qu'elle remplace, pour une raison
générale** : *le texte d'origine affirmait le plancher de calcul sur **dix
cas**; la version alignée le **recompte sur la population**.* **Dix cas disent
qu'une chose existe; ils ne disent jamais combien de fois** — c'est la même
règle qui a déjà mordu sur « sept sur dix en tête d'alphabet ».

> **Un envoi ne prime pas sur le dépôt du seul fait d'être plus récent à
> l'écran.** *Ce qui prime, c'est ce qui porte la structure et le recompte.*

---

## N139 — Une divergence nommée et LAISSÉE : quand le chiffre qui portait le risque est déjà juste

*(2026-09-18, décision d'Alexandre.)*

Le rappel du tampon lit les dates sous une forme que **85 notes sur 136** n'emploient
pas : « la plus ancienne » se calcule donc sur 51. **Décision : ne pas corriger
maintenant.**

**Le motif est le bon, et il est réutilisable** : *le compte — combien de notes sont
en attente — est juste depuis le correctif, et **c'est lui qui portait le
risque**.* L'ancienneté est une information de confort; l'oubli d'une note est la
perte que le tampon existe pour empêcher.

⚠️ **Deux défauts dans le même outil ne valent pas le même prix, et les corriger
ensemble parce qu'ils sont voisins est une erreur de priorité déguisée en
propreté.** *Ce qui les distingue n'est pas leur taille : c'est lequel des deux
laisse passer ce qu'on surveille.*

**Ce qui rend la décision tenable, c'est qu'elle est ÉCRITE.** *Une divergence
connue et notée est une dette; une divergence connue et tue est un piège pour le
prochain lecteur, qui lira « la plus ancienne du 14 septembre » sans savoir que
51 notes seulement ont voté.*

---

## N140 — Un renvoi vers un chantier non ouvert ne se comble pas d'avance

*(2026-09-18, décision d'Alexandre.)*

`falkye-le-cerveau.md` attribue la table `(code, rôle) → sphère` au **chantier 22**,
et le document du 22 ne la nomme pas. **Renvoi vers un chantier, pas vers une
section : rien n'est cassé, et le vérificateur du corpus ne le voit pas non plus.**

**Décision : à nommer dans le document du 22 quand ce chantier s'ouvrira, pas
avant.**

⚠️ *Écrire d'avance dans le document d'un chantier fermé produit exactement ce que
le cas 39 a coûté : un chantier réputé traité parce que son document en parle,
alors qu'il n'a jamais tourné.* **Un renvoi qui pointe vers un chantier à ouvrir
est honnête; une section écrite d'avance dans ce chantier est une promesse qui se
lira comme un état.**

> **Nommer où le travail ira n'est pas le commencer. Remplir sa place d'avance,
> si.**

---

## N141 — Le code postal ne tranchait rien : c'était la région de tri, sur 100 % des cas

*(2026-09-18, relecture des 50 premières corrections par Alexandre.)*

Le départageur d'adresse avait un niveau nommé « code postal ». **Il décidait
entièrement à la résolution de la RÉGION DE TRI, et le code complet n'a jamais
rien tranché.**

Le mécanisme est dans la lecture des faits : `codes_postaux` range `jeton[:3]`
**à côté** de chaque code complet. Deux faits s'intersectent donc *si et seulement
si* leurs régions de tri s'intersectent — *tout code complet partagé implique sa
région partagée, et l'inverse suffit déjà.*

⚠️ **Alexandre l'a trouvé sur un cas; la construction a montré que c'était tout le
niveau.**

```
Wazoom  au dossier : G5R3A7  →  9358-9570 Québec inc.  cp=['G5R', 'G5R3Y8']
```

> *Un seul candidat compatible sur une région de tri n'est pas une
> identification : c'est de la ville déguisée en code postal, qui hérite de la
> faiblesse de la ville **sans la déclarer**.* **`G5R` couvre Rivière-du-Loup en
> entier.**

**Ce qui rend le défaut coûteux n'est pas qu'il soit faux — c'est qu'il soit
INVISIBLE.** *Un départage sur `G5R` et un départage sur `G5R3Y8` sortaient sous
la même étiquette, et rien ne disait lequel on lisait.*

> **Un niveau qui mélange deux résolutions annonce la précision de la plus fine
> et rend la fiabilité de la plus grossière.**

---

## N142 — « Le fait les exclut tous » se franchit vers une DÉGRADATION du même fait, jamais vers un autre fait

*(2026-09-18, en scindant le code postal en deux niveaux.)*

N133 avait posé qu'*« un repli répond à “je ne sais pas”; il n'a rien à répondre
à “non” »*. **Scinder le code postal a montré que la règle était trop large.**

`G5R3A7` contre `G5R3Y8` : au code complet, **le fait les exclut tous**. Fermer
là ferait disparaître le départage par région de tri — *et Alexandre a
explicitement refusé de retirer la région de tri : elle tranche des cas justes,
et la retirer coûterait des vrais pour éviter des faux.*

**La distinction qui tient :**

| le niveau suivant lit… | « exclut tous » | pourquoi |
|---|---|---|
| **le MÊME fait, dégradé** | **on franchit** | *c'est exactement ce que la dégradation existe pour tolérer* |
| **un AUTRE fait** | ⚠️ **on ferme** | *bâtir un départage par-dessus une contradiction établie* |

⚠️ **Et c'est une propriété de la TRANSITION, pas du niveau.** *L'écrire dans une
condition (« si on est au code postal… ») ferait hériter un troisième niveau
d'une règle pensée pour deux.* **Elle est donc portée par l'objet `Niveau` :
`degradation_du_precedent`.**

> **Une règle vérifiée sur deux cas n'est pas une règle : c'est une observation
> qui n'a pas encore rencontré le troisième.**

---

## N143 — Un compte figé dans une étiquette, troisième occurrence — et cette fois dans un libellé de tableau

*(2026-09-18.)*

`profil_des_6176.py` portait une mesure périmée **dans son nom de fichier**; un
test refuse depuis tout nom d'outil portant un compte. ⚠️ **Le même défaut vient
de reparaître ailleurs** : un en-tête de colonne écrit
`« niveau, joué SEUL sur les 5 002 »` **pendant que le code comptait la
population réelle juste à côté**.

*Sur le décor de test, l'en-tête annonçait 5 002 au-dessus d'un tableau de
quatre lignes.* **Personne ne l'aurait vu sur l'hôte, où 5 002 se trouve être
juste — jusqu'au jour où la population bouge.**

**La garde existante ne pouvait pas l'attraper : elle lit les NOMS DE FICHIERS.**
*Un chiffre recopié dans une chaîne de format est hors de sa portée.*

> **Une étiquette qui porte un nombre est une mesure sans requête. Le nombre se
> lit, il ne s'écrit pas.**

---

## N144 — Un test qui compte les jetons d'une ligne lit le décor, pas la mesure

*(2026-09-18.)*

Les tests du départageur vérifiaient un compte par `ligne.split()[-3]`. ⚠️
**Ajouter une marque en fin de ligne — `→ repli`, `⛔ la ville NE PARLE PAS` — a
déplacé tous les index, et les tests se sont mis à comparer des morceaux
d'explication à des nombres.**

*Le premier symptôme a été `assert '33.3' == '1'` : le test lisait le pourcentage
en croyant lire le compte.* **Le second a été pire** : un titre en prose du
préambule contenait « RÉGION DE TRI », et le test l'a trouvé avant la ligne du
tableau.

**Le correctif est de lire par MOTIF** — `\s(\d[\d ]*)\s+\d+\.\d %` — *et de
citer les titres en entier plutôt que par fragment.*

> **Un test qui repère sa valeur par position mesure la mise en page. Il tombe
> quand on ajoute une explication, et il ment quand on en ajoute deux.**

---

## N145 — Un critère qui refuse le gain pour lequel il a été écrit change de FORME, il ne se desserre pas

*(2026-09-19, après l'échec du critère sur les 2 032.)*

Le critère du découpage disait : **« aucun départage perdu, aucun gagnant
déplacé »**. Il a refusé sur **4 gagnants déplacés**, et il a eu raison de
refuser — *sans lui on lisait 2 032 et on concluait à un gain de 111.*

⚠️ **Mais sa seconde moitié interdisait exactement ce qu'on avait construit** :
un niveau fin qui corrige un niveau grossier. *Le découpage existe pour que le
code complet tranche là où la région de tri tranchait mal; le critère comptait
cette correction comme une régression.*

**Les deux réponses possibles, et une seule est tenable :**

| | |
|---|---|
| *desserrer* — accepter N déplacements | ⛔ **un critère qu'on desserre parce qu'il a échoué n'en est plus un** |
| **changer de forme** | ✔ interdire *un gagnant déplacé **sans qu'un niveau plus fin l'explique*** |

**Et la nouvelle forme VÉRIFIE au lieu de supposer** — trois conditions : le
niveau qui tranche est strictement plus fin; il retient le nouveau gagnant;
⚠️ **il EXCLUT l'ancien**. *Un ancien gagnant qui ne porte pas le fait fin n'est
pas réfuté, il est inconnu — « je ne sais pas » n'est pas « non », ici aussi.*

⚠️ **La moitié qui tenait n'a pas bougé** : *un départage PERDU reste interdit
sans condition.* **Changer de forme n'est pas tout rouvrir.**

> **Un critère se juge sur ce qu'il interdit, pas sur le nombre de fois qu'il
> passe. Celui qui interdisait le gain était mal écrit; celui qui n'interdit
> plus rien serait pire.**

---

## N146 — Un balayage exhaustif dit ce qui est POSSIBLE; dix cas tirés disent ce qui est arrivé

*(2026-09-19.)*

Quatre gagnants déplacés, deux lectures : **un défaut de construction**, ou **le
gain lui-même**. *Alexandre a refusé de choisir la plus plausible, et demandé la
lecture des quatre paires.*

**Les quatre paires étaient la bonne demande. Elles n'étaient pas la meilleure
réponse disponible.** ⚠️ *Le domaine est assez petit pour être balayé en entier* —
cinq codes postaux × trois villes, pour le dossier et deux concurrents. Le
balayage rend :

```
DÉPLACÉ  avant=ville  →  après=code postal complet     (seule route)
PERDU    (aucune route)
```

**Une seule route existe, et aucune ne perd de départage.** *Donc un déplacement
ne peut pas être un artefact d'ordre d'évaluation : il ne peut venir que du code
complet tranchant là où la forme mêlée tombait sur la ville.* **C'est la lecture
(b), et elle est démontrée plutôt que plaidée.**

⚠️ **Et c'est le même mécanisme que les 111 ajoutés** — *si le code complet
tranche là où la région ne pouvait pas, il tranche aussi autrement là où la
région tranchait mal.* Les deux effets ont une seule cause; le critère d'avant en
acceptait un et refusait l'autre.

**La démonstration ne remplace pas les quatre paires, elle les rend
falsifiables** : *elle prédit que chacune montrera `ville → code postal complet`,
et une seule qui montrerait autre chose la renverserait.*

> **« Je n'en ai pas vu d'autre » et « il n'y en a pas d'autre » ne sont pas la
> même phrase. Quand le domaine est petit, la seconde se paie.**

---

## N147 — Une paire refusée se lit AVANT le refus, sinon il ne reste rien à examiner

*(2026-09-19.)*

Le critère échouait en imprimant `gagnant : Beauce Carnaval inc  1 → 2` — **deux
rangs, sans le niveau qui a tranché ni les codes postaux des deux gagnants.**
*Alexandre a dû redemander ce qu'il fallait pour trancher : quatre paires lues.*

**Un refus doit porter de quoi l'instruire.** La lecture d'une paire déplacée
donne maintenant, *que le déplacement soit accepté ou refusé* : le niveau qui a
tranché **dans chaque forme**, les codes postaux du dossier **aux deux
résolutions**, et ceux de **l'ancien et du nouveau gagnant**.

⚠️ **Y compris quand le déplacement est EXPLIQUÉ** : *le critère dit qu'il est
explicable, il ne dit pas qu'il est juste.* **Un départage écarte un candidat; il
n'en confirme aucun** — un déplacement légitime reste une paire à regarder.

> **Un refus qui ne montre pas sur quoi il porte oblige à redemander ce qu'on
> avait déjà calculé.**

---

## N148 — Le scoreur savait sur quoi il avait décidé, et il le jetait

*(2026-09-19, relecture des 50 paires de la passe par Alexandre.)*

```
#16   détecté  : 16790224 Canada Inc.
      registre : LES ENTREPRISES DOUGLAS POWERTECH INC.      score 100.0
```

**Deux chaînes sans un caractère commun, à score 100.** *Ça se lit comme une
fausse résolution, et c'en est une bonne* : le NEQ porte plusieurs formes, dont
`16790224 Canada Inc.`, et **la décision s'est prise sur celle-là**.

⚠️ **Le défaut n'est pas dans le score : il est dans ce que l'instrument
montre.** `_scorer` appelle `process.extractOne`, qui rend **le score ET la
forme gagnante** — *le code gardait le premier et jetait la seconde*, puis
l'appelant affichait `entry.nom`, la dénomination sociale ÉLUE.

> **L'information existait, à une ligne de là. Elle était perdue à la sortie de
> la fonction qui l'avait produite.**

**C'est le cas 33 pris au pire endroit** : *avant une écriture irréversible, sur
la seule vérification qui reste — la relecture des paires.* Et c'est aussi le
même motif que `SDI CANADA → BIOMEDSHIELD` : **une raison sociale contre un nom
qui la désigne autrement.**

`REQMatch` porte maintenant `forme_normalisee`, et `formes_retenues()` la traduit
en nom publié, gisement et statut — **en une seule requête**, parce qu'une
lecture par paire ferait N requêtes pour un rapport de cinquante lignes.

> **Quand un calcul produit deux choses et qu'on n'en garde qu'une, c'est
> toujours l'autre qu'on redemandera.**

---

## N149 — « Cinquante paires lues » ne dit pas combien sont dans ce cas

*(2026-09-19.)*

Deux paires sur cinquante décidées sur une autre forme que celle affichée. ⚠️
**Alexandre n'a pas demandé le correctif seul : il a demandé LE COMPTE sur les
2 523.** *« Si c'est deux, c'est anecdotique; si c'est trois cents, la relecture
de 50 paires ne disait pas ce qu'on croyait qu'elle disait. »*

**Et le compte est gratuit** : `forme_normalisee != entry.nom_normalise` est une
comparaison, pas une requête. *Ce qui coûtait, c'était de traduire la forme en
gisement — et ça ne se fait que sur les lignes affichées.*

> **Un échantillon relu dit ce qu'il contient. La part de la population qu'il
> représente est une autre question, et elle se pose AVANT d'agir sur
> l'échantillon.**

⚠️ **Le rapport ventile aussi par gisement** — `nom_assuj`, `nom_etranger`,
`nom_etab`, `denomn_soc`. *Savoir que 300 paires ont décidé sur une autre forme
ne dit pas la même chose selon qu'elles viennent d'un nom en vigueur ou d'un nom
retiré.*

---

## N150 — Un statut absent là où il n'y a rien à lire n'est pas « inconnu »

*(2026-09-19.)*

La forme gagnante affiche son gisement et son statut. **Quand c'est la
dénomination sociale élue, elle vient de `req_entries`, qui ne porte aucun statut
DE NOM** — `REQEntry.statut` est le statut de l'ENTREPRISE (immatriculée,
radiée), pas celui du nom.

Écrire « statut inconnu » sur ces lignes-là — *la majorité* — **ferait chercher
une lecture manquée là où il n'y a rien à lire**, et noierait le cas où le statut
manque vraiment : *une forme de `req_noms` sans statut est une lacune réelle.*

**Donc : rien pour la dénomination élue, « inconnu » pour une forme de
`req_noms` qui n'en porte pas.**

> **Deux silences qui n'ont pas la même cause ne s'écrivent pas du même mot. Un
> champ qui n'existe pas et un champ qu'on n'a pas lu appellent deux gestes
> différents.**

---

## N151 — Une théorie se verse au corpus avec ce qui l'appuie ET avec ce qui n'est pas compté

*(2026-09-19, trois constats versés aux chantiers 3+4 et 22.)*

Trois théories d'Alexandre sur ce qui restera **après** les écritures. **Aucune
n'est un mandat** : elles disent pourquoi une structure est nécessaire.

⚠️ **Et chacune porte, à côté de ce qui l'appuie, l'aveu de ce qui n'est pas
mesuré :**

| constat | ce qui l'appuie | ⚠️ ce qui manque |
|---|---|---|
| **les consortiums** | deux noms lus, forme reconnaissable | **jamais compté** — personne ne sait combien de dossiers |
| **les doublons du produit** | 111 NEQ déjà pris, deux familles lues | **32 sur 805, 4 %** — borne basse, et seulement sur ce que le nom résout |
| **les indépartageables** | 2 970 que l'adresse ne sépare pas | la mesure de l'activité **précède** le découpage : **à refaire** |

**Sans la seconde colonne, un constat devient un chiffre.** *« Les consortiums
existent » et « les consortiums sont 400 » se lisent pareil dans six mois, et un
seul des deux a été établi.*

> **Une théorie versée sans son trou de mesure se relit comme un fait. Le trou
> fait partie du constat.**

---

## N152 — Remplir la place d'avance : la règle tient quand c'est nous qui écrivons le document

*(2026-09-19.)*

N140 posait que *nommer où le travail ira n'est pas le commencer; remplir sa
place d'avance, si*. **Le versement au chantier 22 était l'occasion de l'enfreindre
de bonne foi** — la table `(code, rôle) → sphère` est nommée, les 53 familles
sont connues, et en écrire trois aurait « aidé ».

**Ce qui est versé est le BESOIN et sa mesure** : 2 970 indépartageables,
l'activité comme seul départageur restant, et **pourquoi son chiffre est un
plancher** — comparaison par libellé faute de table, et mesure antérieure au
découpage du départageur d'adresse.

⚠️ **Le plancher a deux causes, et les séparer est ce qui rend le constat
utilisable** : *l'une est le besoin que le chantier 22 porte; l'autre est une
mesure à refaire, qui ne lui appartient pas.* **Les confondre ferait attendre du
chantier 22 qu'il corrige un chiffre que le chantier 3+4 a déjà périmé.**

> **La règle qui coûte est celle qu'on s'applique quand on a la matière sous la
> main.**

---

## N153 — Un `(inconnu)` qui « s'explique de lui-même » referme une question ouverte

*(2026-09-19, sur la ventilation par gisement de la passe.)*

**332 des 577 paires décidées sur une autre forme affichent un gisement
`(inconnu)`.** *La lecture proposée* : « c'est la dénomination élue de
`req_entries`, absente de `req_noms`, donc sans gisement ».

⚠️ **Cette lecture ne peut pas être la bonne, et le code le dit.** *Le compte des
577 exclut les dénominations élues par construction* — `est_la_denomination_elue`
**est** le filtre, et une forme élue s'affiche `(dénomination élue)`, pas
`(inconnu)`. **Un test le verrouille.**

**Ce qu'il reste comme lecture** : ce sont des lignes de `req_noms` dont la
colonne `gisement` est vide. *Or le chargeur en pose toujours une* — donc **des
lignes antérieures à la colonne**, ajoutée le 17 septembre.

⚠️ **La différence n'est pas cosmétique.** *La première lecture referme la
question; la seconde ouvre un rechargement, et fait douter de toute ventilation
par gisement tant qu'elle tient.* **Vérification à une requête :**
`SELECT count(*) FROM req_noms WHERE gisement IS NULL`.

> **« Ça s'explique de soi-même » est la phrase qui clôt le plus d'enquêtes
> avant qu'elles commencent. Quand l'explication est vérifiable à une ligne,
> elle se vérifie.**

---

## N154 — `INSERT OR IGNORE` rend une table APPEND-ONLY, et personne ne l'avait écrit

*(2026-09-19, en répondant à « le prochain import remplira-t-il la colonne? ».)*

**Non. Et le mécanisme va bien au-delà de la colonne `gisement`.**

`_charger_tous_les_noms` écrit en **`INSERT OR IGNORE`** sur la clé
`(neq, nom_normalise)`, et **rien ne vide `req_noms`** — *seules `req_mots` et
`req_mots_frequence` sont reconstruites.* **Une ligne déjà présente est donc
SAUTÉE, jamais mise à jour.**

Le choix était délibéré et son motif est écrit dans le code : *avec `add` ligne à
ligne, la seconde insertion levait `IntegrityError` et faisait tomber l'import
entier.* ⚠️ **Ce qui n'était écrit nulle part, c'est le prix** : **les colonnes
non-clés d'une ligne sont figées à leur valeur du PREMIER import où le nom est
apparu.**

| colonne | ce que le miroir porte |
|---|---|
| `gisement` | vide sur les 1 505 879 lignes du pont du 15 septembre, **indéfiniment** |
| `statut` | ⚠️ **celui du premier import** — *un nom retiré du registre depuis garde « en vigueur »* |
| `type_nom` | idem |

⚠️ **Et toute colonne ajoutée à `req_noms` à l'avenir naîtra vide sur les lignes
existantes, sans que rien le signale.**

**Le test qui existait ne pouvait pas l'attraper** : `test_un_REIMPORT_ne_leve_pas`
vérifie que le réimport **ne casse pas**. *Il ne dit rien de ce qu'il FAIT.*

> **Un test qui vérifie qu'un geste ne lève pas ne vérifie pas qu'il agit. Les
> deux se ressemblent au vert.**

---

## N155 — Le rechargement d'une colonne n'est pas « relancer le chargeur »

*(2026-09-19, chiffrage demandé avant de faire.)*

⚠️ **Relancer `_charger_tous_les_noms` ne remplirait RIEN** *(N154)*. Le
rechargement demande donc un geste d'une autre nature, et il y en a trois :

| | coût | ce que ça corrige |
|---|---|---|
| **(a) `UPDATE … WHERE gisement IS NULL`** | **secondes**, aucune archive | ⚠️ **AFFIRME** l'inférence `NOM_ASSUJ` au lieu de la lire. `gisement` seul, cette fois seulement |
| **(b) supprimer les lignes vides, relire `Nom.csv`** | une lecture en flux de 4,65 M enregistrements + ~1,5 M écritures, **archive requise** | `gisement` **et** `statut`, cette fois seulement |
| **(c) passer en UPSERT, réimporter** | **l'import complet — 40 min mesurées** | ⚠️ **la CAUSE**, pour toute colonne présente et future |

⚠️ **Seule (c) empêche que ça recommence.** *(a) et (b) réparent l'instance;
la prochaine colonne ajoutée retombera dans le même trou.*

**Et (c) porte une décision de conception, pas seulement un coût** : *que devient
`first_seen_at` quand une ligne est réécrite?* **Une ligne rafraîchie n'a pas été
vue pour la première fois aujourd'hui** — et confondre les deux ferait mentir la
seule colonne qui date le miroir.

⚠️ **Aucun chiffre inventé pour (b).** *Le seul repère mesuré est l'import
complet à 40 minutes; la part de `Nom.csv` dedans n'a pas été chronométrée
séparément.* **L'outil qui fera le rechargement devra se chronométrer
lui-même** — *un coût annoncé sans mesure est une estimation qu'on relira comme
un fait.*

---

## N156 — Une ventilation porte sa COUVERTURE, ou elle se lit comme complète

*(2026-09-19.)*

`gisement` est vide sur **1 505 879 lignes sur 5 071 984 — 29,7 %**. *Toute
ventilation par gisement sous-estimait `NOM_ASSUJ` d'autant.* **Le chiffre n'était
pas faux : il était incomplet, et rien dans la sortie ne le disait.**

**Deux correctifs, et il faut les deux :**

1. **L'étiquette dit ce qu'elle sait ET d'où elle le tient** —
   `NOM_ASSUJ (antérieur à la colonne)` plutôt que `(inconnu)`. *La ventilation
   redevient juste, et personne ne lit une valeur inférée comme une valeur lue.*
2. **La couverture s'imprime À CÔTÉ de la ventilation** — combien de lignes de la
   table n'en portent pas, et **que le prochain import ne les remplira pas**.

⚠️ *Le premier seul suffirait à rendre les comptes justes. Il ne suffirait pas à
empêcher qu'on lise la ventilation comme complète* — et c'est la lecture, pas le
compte, qui a fait écrire « 103 `NOM_ASSUJ` » là où il fallait lire 435.

> **Un total juste sur une population partielle est un total juste. C'est la
> population qu'il faut écrire à côté.**

---

## N157 — Deux passes qui écrivent le même geste : extraire AVANT d'écrire la seconde

*(2026-09-19, avant de construire l'écriture des départages.)*

Deux passes posent un NEQ : la **reprise** pose ce que le NOM a tranché,
l'**écriture des départages** pose ce que l'ADRESSE a tranché. ⚠️ **Elles ne
diffèrent que par la façon dont la paire `(dossier, NEQ)` est produite.** *Tout
ce qui vient après est le même geste* — instantané, collisions, refus au-delà de
deux prétendants, re-vérification au moment de poser, enrichissement,
journalisation, retour arrière.

⚠️ **Recopier ce geste aurait été cas 41 sur un chemin d'ÉCRITURE.** *Un scoreur
recopié rend un chiffre faux et se rattrape. Une règle de conservation recopiée
qui diverge perd une identité — et l'instantané de l'autre copie ne la rend
pas.*

**`outils/pose_du_neq.py` a donc été extrait AVANT d'écrire la seconde passe**,
par déplacement verbatim des blocs — commentaires compris, parce qu'ils portent
le fait qui a écrit chaque règle *(le NEQ 8879690699 et ses 26 CISSS)*.

**Et l'extraction se prouve toute seule** : *les 27 tests de la passe de reprise
passent sans une modification.* **Une extraction qu'on doit accompagner d'un
ajustement de tests n'est pas une extraction, c'est une réécriture.**

> **Le moment d'extraire n'est pas quand la copie existe : c'est juste avant de
> la faire. Après, il faut prouver que les deux copies disaient la même
> chose.**

---

## N158 — Une note écrite ne protège pas le doigt qui tape

*(2026-09-19, une heure après avoir écrit N144.)*

N144 dit : *un test qui repère sa valeur par rang de jeton mesure la mise en
page.* **Le premier test écrit après cette note faisait exactement ça** —
`ligne.split()[-2]` sur une ligne `« 2   66.7 % »`, qui rend `66.7`.

⚠️ **La note n'a pas servi parce qu'elle n'était pas à portée du geste.** *Elle
est au tampon, pas dans le module de test.* **Le correctif qui tient est
l'helper `_compte()`, copié dans le fichier de test** — *non pas parce qu'un
helper est plus intelligent qu'une note, mais parce qu'il est là où la faute se
commet.*

**Ce que ça dit de la méthode du corpus** : *une règle se consigne pour être
relue; elle ne se consigne pas pour être appliquée.* **Ce qui applique, c'est du
code au bon endroit.**

> **On consigne pour comprendre. On garde pour empêcher. Les deux ne se
> remplacent pas.**

---

## N159 — Restreindre l'écriture par NIVEAU, pas le départageur

*(2026-09-19, décision d'Alexandre après relecture de 50 paires sur 292.)*

Le départageur d'adresse sépare **2 032** ambigus. **On n'en écrit que 1 764** —
ceux du **code postal complet**.

```
KONE INC.   au dossier 'L5N0A4'   comparé sur ['L5N']
 × 1172439623  KONE INC.              ville='Montréal'      complet=H4S1Y4
 → 1144414308  DROLET KONE ELEVATORS  ville='Mississauga'   complet=L5N7J6
```

> ⚠️ *`L5N` ne dit que « quelque part à Mississauga ».* **C'est de la ville, sous
> un nom qui ne le dit pas.**

**Ce qui est restreint est l'ÉCRITURE, pas le départageur.** *`departager_ladresse`
continue de dire ce qu'il sait, à ses trois niveaux; c'est l'outil qui écrit qui
filtre.* **Mêler les deux ferait disparaître 268 départages de toutes les
mesures, pas seulement des écritures** — et une mesure qui rétrécit sans le dire
est pire qu'une écriture qu'on suspend.

⚠️ **Et « en suspens » n'est pas « refusé ».** *Un départage non écrit se
reprend; un départage écrit à tort coûte une identité.* **La restriction se
trompe dans le bon sens**, et l'outil les compte, les ventile et les montre un
par un — *un outil qui écrit 1 764 sur 2 032 doit dire lesquels il n'a pas
touchés, sinon la différence se lit comme une perte.*

> **Une restriction qui s'applique à l'action et non à la connaissance se lève
> sans rien redécouvrir.**

---

## N160 — Deux corrections qui portent le même nom ne se mesurent pas sous le même nom

*(2026-09-19, chiffrage du retrait de parenthèse côté détecté.)*

**« Retirer les parenthèses » désigne DEUX corrections différentes**, et la
première a déjà été chiffrée :

| | côté | rendu |
|---|---|---|
| 17 septembre | **les deux côtés** | **+17 net** — 30 gagnés, **13 PERDUS** |
| 19 septembre | ⚠️ **le nom DÉTECTÉ seul** | *jamais mesuré* |

⚠️ **Les 13 perdus venaient du REGISTRE** : *`FERME BELLEVUE (1997) INC.` privée
de sa parenthèse passe de 86 à 95, et l'écart au second s'effondre.* **Retirer
la parenthèse du seul nom détecté ne peut pas produire cette perte** — le
registre garde tous ses discriminants.

**Ce qui protège de la confusion n'est pas une note, c'est la sortie** : *le nom
du fichier porte le côté, l'entête rappelle l'autre chiffrage avec ses chiffres,
et la dernière ligne redit que le registre n'a pas été touché.*

> **Une mesure qui ne nomme pas sa variante se relira comme la variante déjà
> connue. Le lecteur de janvier n'aura pas la conversation de septembre.**

---

## N161 — Transformer le nom détecté ne change pas que le score : ça change le LOT

*(2026-09-19.)*

`transformer_forme` s'applique au **registre**; le nom détecté, lui, est
l'argument `nom` de `resolve_neq_by_name`. ⚠️ **Et le moteur le dit dans sa
propre docstring** : *« Il ne touche PAS la récupération : `candidats_par_nom`
cherche sur le nom DÉTECTÉ. Transformer le nom détecté change donc les lignes
rendues. »*

**Le premier temps ne bouge pas** — *le préfixe est le PREMIER mot, et une
parenthèse n'est jamais première.* **Mais le second temps choisit le mot le plus
RARE du nom** : retirer des mots peut changer ce choix, donc le lot élargi.

**Donc un gain mesuré ici vient de DEUX causes mêlées** : un score qui remonte,
et parfois un lot différent. *La mesure compte les dossiers où le lot a changé,
au lieu de supposer l'effet nul.*

> **Quand une transformation touche deux étages, le compte des dossiers où le
> second a bougé est ce qui empêche d'attribuer tout le gain au premier.**

---

## N162 — Un libellé qui annonce le PARAMÈTRE au lieu du RÉSULTAT

*(2026-09-19.)*

`--tete 5` compare la tête de table à la population *(cas 19)*. ⚠️ **Sur un lot
de deux dossiers, la sortie écrivait « la TÊTE — les 5 premiers par id » au-dessus
d'un compte de 2.**

*C'est le défaut du compte figé (N143), en plus discret* : **le libellé donne
l'autorité d'une mesure à ce qu'on a DEMANDÉ, pas à ce qu'on a OBTENU.** Et il ne
se voit que là où les deux diffèrent — donc jamais sur l'hôte, où le lot est
grand.

**Corrigé en lisant `len(tete)`.** *Troisième forme du même défaut en trois
jours : un nom de fichier, un en-tête de colonne, un libellé paramétré.*

> **Un paramètre dit ce qu'on a voulu. Seul le résultat dit ce qu'on a eu. Un
> libellé qui cite le premier ment dès que le second diffère.**

---

## N163 — Une ventilation d'une seule population ne peut pas dire « surreprésentée »

*(2026-09-19, ventilation des restants par source.)*

La théorie : *`rob_top_growing` et `deloitte_fast50` sont des classements
canadiens; s'ils sont **surreprésentés** parmi les restants, une part n'a pas de
NEQ à trouver.*

⚠️ **« 12 % des restants viennent de X » ne se compare à rien.** *Il faut la
même ventilation sur les dossiers RÉSOLUS, et le rapport des deux.* **La sortie
rend donc les deux colonnes et leur rapport, jamais l'une sans l'autre.**

**Et le cas le plus fort n'est pas un grand rapport : c'est une source dont
AUCUN dossier n'est résolu.** *Écrire `—` là où le dénominateur est nul masquerait
exactement ce que la mesure cherche* — la sortie écrit **`AUCUN`** et **`← JAMAIS
résolue`**.

⚠️ **Ce que le rapport ne dit pas** : *pourquoi.* **Une source pancanadienne et
une source dont les noms sont sales donnent le même rapport.**

> **Un taux sur une population isolée décrit cette population. Il ne devient une
> comparaison que quand l'autre est là — et le cas indéfini est souvent le plus
> parlant.**

---

## N164 — La prémisse tenait, et le code la disait plus fort

*(2026-09-19, vérification avant mesure.)*

Théorie d'Alexandre : *le registre des sources porte les classements canadiens à
`territoire: null` — rien ne les filtre par province.* **Vérifié : exact.**

⚠️ **Et plus fort que l'énoncé.** *`province_code` est **null sur toutes les
sources**, `territoire` n'est rempli que pour l'EIMT, et `region` est du texte
libre (`'Québec/Canada'`) que rien ne lit.* **Or `province_code` est le seul champ
que `falkye/expansion_interprovinciale.py` interroge** :

```python
if source_def is not None and source_def.province_code:   # jamais vrai
```

**Le mécanisme prévu pour raisonner par province existe et n'a aucune donnée.**

**La leçon de méthode** : *vérifier une prémisse avant de la reprendre coûte deux
minutes, et rend parfois un fait plus grand que celui qu'on cherchait.* ⚠️ **La
reprendre telle quelle l'aurait figée dans la sortie d'une mesure**, où elle
aurait ensuite été citée comme mesurée.

> **Une prémisse qu'on transporte sans la relire devient un résultat au bout de
> deux documents.**

---

## N165 — Deux règles qui portent le même nom rendent deux chiffres, et l'un des deux est faux

*(2026-09-19.)*

Le chiffrage de la parenthèse comptait les « champs multi-entités » avec une
règle LÂCHE — *toute conjonction* — et rendait **17 sur 148, 11,5 %**. La mesure
demandée ensuite spécifie la bonne règle : **une conjonction entre DEUX FORMES
JURIDIQUES.**

| nom | ancienne règle | règle stricte |
|---|---|---|
| `X inc. & Y inc.` | consortium | **consortium** |
| ⚠️ `Gagnon et Fils inc.` | **consortium** | *pas un consortium* |

⚠️ **Les deux chiffres ne sont pas comparables, et le second remplace le
premier.** *Le dire dans la sortie est ce qui empêche de lire « 11,5 % → 6 % »
comme une évolution du parc alors que c'est un changement d'instrument.*

**Et la règle lâche était la MIENNE**, écrite pour signaler un confond dans une
autre mesure — *ce qui était honnête là où elle servait, et faux dès qu'on la
promeut en compte.*

> **Un signal approximatif posé pour écarter un confond devient un chiffre faux
> le jour où quelqu'un le lit comme une mesure. La règle d'un compte se pose
> quand on compte, pas quand on signale.**

---

## N166 — Un compte exact sur une clé exacte est un plancher, et il doit le dire

*(2026-09-19, doublons du produit.)*

**Ce qui se compte** : deux dossiers de même `nom_detecte_normalise` — donc les
variantes de casse et de ponctuation, `AYE3D inc.` contre `AYE3D Inc.`

⚠️ **Ce qui ne s'y compte pas** : `PHILIPS CANADA` contre `PHILIPS ÉLECTRONIQUE
LTÉE`, `Casa Grecque Drummondville` contre `3038947 Canada Inc.` **Aucune clé
exacte ne les réunit** — *il faudrait une passe floue, qui est une autre
mesure.*

**Donc le compte est un PLANCHER, et la sortie l'écrit avec ses exemples.**
*Sans cette ligne, un compte exact se lit comme un compte complet* — c'est la
même famille que la ventilation par gisement lue comme complète *(N156)*.

⚠️ **Et ce compte ne cherche pas un correctif.** *Il dit si le chantier 3 — une
identité, plusieurs identifiants, plusieurs noms — vaut ce qu'il coûte.* **Un
consortium demande DEUX NEQ sur un dossier; un doublon demande UN dossier qui
porte DEUX noms. Le modèle actuel ne permet ni l'un ni l'autre.**

> **Une clé exacte rend un chiffre exact sur ce qu'elle atteint. Ce qu'elle
> n'atteint pas ne se déduit pas de ce qu'elle rend.**

---

## N167 — `RawSignal` n'a AUCUN emplacement pour un code postal

*(2026-09-20, en traçant l'adresse de la source au dossier.)*

⚠️ **Vérifié dans `falkye/sources/base.py`** : `RawSignal` porte `adresse`,
`ville`, `region` — **et rien d'autre pour l'adresse.**

> **Donc aucun connecteur ne PEUT promouvoir un code postal, quelle que soit la
> source qui en publie un.**

**Et c'est le niveau le plus FORT du départageur d'adresse** *(1 764 écritures
sur 2 032 reposent dessus)*. **Il ne fonctionne aujourd'hui que parce que
`faits_du_dossier` va le chercher LUI-MÊME dans `Signal.champs`**, en fouillant
le sac par `CLES_ADRESSE`.

⚠️ **Ça change la lecture de « cette source porte-t-elle un code postal? ».** *La
réponse ne débloque rien par une promotion* — il n'y a pas de champ où
promouvoir. **Soit on élargit `CLES_ADRESSE`, soit `RawSignal` gagne un
emplacement.** *Les deux se décident avec Alexandre; aucun ne se déduit de la
mesure.*

> **Un champ qu'on cherche à promouvoir sans emplacement où le mettre n'est pas
> un défaut de connecteur : c'est un défaut de modèle.**

---

## N168 — Un écart se juge emplacement par emplacement, pas « promeut quelque chose »

*(2026-09-20, défaut révélé par le décor de test.)*

L'outil marquait « rangé et jamais promu » **quand le connecteur ne promouvait
RIEN**. ⚠️ **Or `eimt` promeut `region`** — donc la condition était fausse, et
elle masquait exactement le cas pour lequel l'outil existe :

```
   arrivé dans Signal.champs  adresse
   PROMU en RawSignal         region        ← quelque chose est promu
```

*`adresse` reste dans le sac, et c'est le motif EIMT dans sa forme pure.*

**Le défaut n'est pas sorti d'une relecture : il est sorti du DÉCOR.** *Un décor
où le connecteur ne promeut rien du tout aurait laissé la condition passer pour
juste.* **C'est ce que vaut un décor construit sur un cas réel plutôt que sur le
cas commode.**

> **Une condition agrégée — « promeut quelque chose » — répond à une question
> qu'on ne pose jamais. Ce qu'on veut savoir est toujours : CE champ-là, où
> va-t-il?**

---

## N169 — Le dépôt dit ce que le connecteur LIT, jamais ce que la source PUBLIE

*(2026-09-20.)*

**Trois issues possibles pour une adresse manquante, et elles n'appellent pas le
même geste** :

| | établi par | correctif |
|---|---|---|
| captée et jetée | ⚠️ **le dépôt** | une ligne — le motif EIMT |
| publiée et jamais captée | ⚠️ **le dépôt** | travail de connecteur |
| **n'existe pas dans la source** | ⛔ **pas le dépôt** | *la piste se ferme* |

⚠️ **La troisième ne peut PAS s'établir ici.** *Un champ absent des quatre
colonnes veut dire « personne ici ne le connaît » — jamais « la source ne l'a
pas ».* **Conclure l'absence depuis un connecteur muet, c'est classer un fichier
sur son nom** — ce qui a laissé `DENOMN_SOC` ignoré un jour de plus.

**Et la colonne « déclaré » n'est pas une observation** : *`description_tender`
était déclaré par le connecteur SEAO depuis toujours et vide dans 100 % des
cas.* **C'est une prétention qu'on confronte, pas une source de vérité** — d'où
les deux colonnes séparées, « présent » (la clé) et « rempli » (la valeur).

> **Le silence d'un instrument est un fait sur l'instrument. Il ne devient un
> fait sur le monde que quand on est allé voir.**

---

## N170 — L'asymétrie du SEAO n'était pas dans la source : elle était dans le lecteur

*(2026-09-20.)*

**SEAO : 88,7 % de code postal, 9,6 % de ville.** *On pouvait lire ça comme
« la source porte un code et pas de ville ».* ⚠️ **C'est faux, et le code le
dit :**

| niveau | qui lit | clés connues |
|---|---|---|
| code postal | `faits_du_dossier` | `CLES_ADRESSE` — dont **`adresse_entreprise_adjudicataire`** |
| ville | `villes_des_signaux` | `CLES_VILLE`, puis repli sur **la seule clé littérale `'adresse'`** |

**Le champ agrégé du SEAO porte les deux. Seul le lecteur de code postal le
connaît.** *La ville du SEAO n'est pas absente : elle est invisible au lecteur
qui la cherche.*

⚠️ **Deux lecteurs d'un même fait, avec deux listes de clés qui divergent, et
personne ne les avait comparées.** *Chacun est correct isolément; c'est l'écart
entre eux qui produit un chiffre qu'on lit comme une propriété de la source.*

> **Quand deux mesures du même objet divergent, regarder l'objet est le second
> réflexe. Le premier est de vérifier qu'elles le lisent au même endroit.**

---

## N171 — Une promotion ne vaut que ce que le lecteur en aval ne lit pas déjà

*(2026-09-20.)*

**La promotion sert `RawSignal`. Le départageur, lui, lit `Signal.champs`
DIRECTEMENT.** ⚠️ *Donc la question n'est pas « ce champ est-il promu? » mais
**« ce que la promotion apporterait est-il déjà lu ailleurs? »***

- **`eimt`** — `champs['adresse']` est lu **par les deux** lecteurs. *Le
  promouvoir ne change RIEN au départage* : **travail de propreté**, qui servirait
  le PORTRAIT — lequel exige une adresse en sortie.
- **`seao`** — le connecteur **lit `locality`** et ne le range pas. *Or `locality`
  est DÉJÀ dans `CLES_VILLE`* : **le ranger suffirait**, sans toucher au repli ni
  à `RawSignal`.

⚠️ **Et l'autre voie est dangereuse** : apprendre la clé agrégée au repli
d'adresse fait prendre la tête de chaîne pour une municipalité. *Sur
`« 123 rue Principale, Montréal, QC »`, c'est une RUE.* **Une rue prise pour une
ville ne manque pas un départage : elle en PRONONCE un faux** — et le chiffrage
compte les têtes qui commencent par un numéro avant qu'on construise.

> **Un correctif se chiffre contre ce que le système fait déjà, pas contre ce
> qu'il déclare faire. Deux chemins vers le même fait rendent le second
> gratuit — ou nuisible.**

---

## N172 — Le quatrième `split()[-2]`, et le helper qui aurait dû exister au premier

*(2026-09-20.)*

N144 a nommé le défaut. N158 a constaté qu'une note ne protège pas le doigt qui
tape et a posé un helper **dans un fichier de test**. ⚠️ **Il a été recopié dans
trois fichiers, et le quatrième l'a refait à la main.**

**Le helper vit maintenant dans `tests/conftest.py`** — *le seul endroit que le
PROCHAIN fichier de test trouvera sans y penser.* Les cinq fichiers l'importent.

**Ce que les quatre occurrences enseignent, et ce n'est pas « faire attention » :**

| tentative | portée | a tenu? |
|---|---|---|
| une note au tampon | le corpus | ⛔ non |
| un helper dans LE fichier | un fichier | ⛔ non — recopié, puis oublié |
| **un helper dans `conftest.py`** | **tous les fichiers à venir** | *on verra* |

> **Une règle ne s'applique qu'à la portée de l'endroit où on l'a mise. Trois
> copies d'un garde-fou protègent trois fichiers et annoncent le quatrième.**

---

## N173 — Un croisement sans clé n'est pas un croisement difficile

*(2026-09-20.)*

La demande était un croisement : **combien des 4 673 restants sont des entreprises
que le registre ne nommera jamais.** *On cherche une méthode, on en essaie trois,
on retient la moins mauvaise.*

⚠️ **Mais les deux côtés du croisement manquent le MÊME champ.** Un restant n'a
pas de NEQ — il ne porte qu'un nom. Les 224 968 NEQ qu'on cherche n'ont **aucun
nom publié** : c'est *par définition* ce qui en fait des absents de `Nom.csv`.

| ce qu'on voudrait joindre | par le NEQ | par le nom |
|---|---|---|
| un restant | ⛔ il n'en a pas | ✅ |
| un absent de `Nom.csv` | ✅ | ⛔ il n'en a pas |

**La diagonale est vide.** *Il n'existe aucune colonne que les deux populations
portent en même temps.*

**Ce que ça change dans l'ordre du travail :** on ne cherche pas « la méthode la
moins mauvaise » avant d'avoir établi qu'il n'y en a aucune de directe. **Le dire
est le premier résultat de la mesure, et il vient avant tout chiffre** — sinon
l'indirect se relit comme un pis-aller, alors qu'il est le seul régime possible.

> **Avant de chercher une méthode, regarder si la clé existe. Une jointure dont
> la clé est exactement ce qu'on cherche n'est pas difficile : elle est
> impossible, et ça se dit.**

---

## N174 — Deux cibles qui se ressemblent, et la population témoin n'en contient qu'une

*(2026-09-20.)*

**T1** — *« c'est une personne physique »*. Une forme juridique, **mesurable** sur
les dossiers résolus, puisqu'ils portent un NEQ.

**T2** — *« le registre ne la nommera jamais »*. **Ce qu'on cherche.**

⚠️ **Elles ne sont pas la même chose, et la population qui sert à calibrer ne
contient que la première.** *Un dossier résolu est résolu PARCE QUE le registre
l'a nommé* — donc **aucun résolu n'est hors de portée, par construction.** Une
précision calculée là-dessus mesure T1 et se relirait comme T2.

**Deux conséquences, et la seconde est la plus dure :**

1. **Le pont T1 → T2 se mesure à part** — la part des personnes physiques du
   registre **sans aucun nom publié**. *Celle-là est une vraie mesure, sans
   heuristique.*
2. ⚠️ **Le taux de faux NÉGATIFS n'est mesurable nulle part.** La population
   témoin est faite de dossiers nommés : *elle ne contient presque aucune
   personne physique sans nom, c'est-à-dire exactement celles qu'on cherche.*
   **On mesure ce qui déborde, jamais ce qui manque.**

**Et c'est ce qui DÉCIDE l'heuristique, au lieu d'être une réserve ajoutée après :**
puisque seule l'erreur par excès est mesurable, la règle doit préférer l'erreur
par défaut — **manquer plutôt que déborder**. *C'est la seule préférence sous
laquelle le chiffre se lit comme un plancher.*

> **Quand une seule des deux erreurs est mesurable, l'instrument doit préférer
> l'autre. Sinon il rend un chiffre dont personne ne peut dire le sens.**

---

## N175 — Une garde qui ne peut JAMAIS se déclencher

*(2026-09-20.)*

L'heuristique portait trois exclusions, chacune avec sa raison affichable : forme
juridique, mot d'activité, **et chiffre**. *Un nom de personne ne porte pas de
chiffre, et les sociétés à numéro sont légion.*

⚠️ **`porte_un_chiffre` ne pouvait jamais se déclencher.** Le jeton de patronyme
— `^[lettre][lettre'.-]*$` — **exclut déjà les chiffres**, et il est vérifié
avant. *Trouvé par un test qui attendait `REJET_CHIFFRE` sur
`« Pièces 2000, Laval »` et recevait `REJET_PAS_LA_FORME`.*

**Retirée, et remplacée par une ligne de commentaire sur le jeton.** ⚠️ *La
tentation était de garder la vérification « au cas où » : elle ne coûte rien et
elle rassure.* **C'est précisément le problème — elle rassure sans protéger, et
sa ligne de ventilation aurait affiché `0` à jamais**, ce qui se relit comme
« aucune société à numéro » plutôt que comme « cette garde est morte ».

**Le test qui la remplace ne vérifie pas un nom : il vérifie que CHAQUE raison
affichable est atteignable par au moins un témoin.** *Il tombera le jour où une
exclusion future sera masquée par une antérieure.*

> **Un zéro rendu par une garde morte et un zéro mesuré s'écrivent pareil. Toute
> raison de rejet affichable doit être atteignable, et c'est un test, pas une
> relecture.**

---

## N176 — Un plancher qui est un produit hérite de son facteur le plus faible

*(2026-09-20.)*

Le chiffre final est un **produit** : *(combien de restants ont un nom en forme de
patronyme)* × *(quelle part des personnes physiques du registre n'a aucun nom
publié)*.

⚠️ **Le premier facteur est une HEURISTIQUE, le second une MESURE.** *Et un
produit ne se lit pas comme sa moyenne :* il hérite de la faiblesse du premier,
**jamais de la solidité du second**.

**Ce que l'outil fait, et ce n'est pas une note en bas de page :** chaque facteur
porte son étiquette **sur sa propre ligne**, `⚠️ HEURISTIQUE` et `✅ MESURE`, dans
le tableau du produit lui-même.

    restants retenus par la règle stricte               N     ⚠️ HEURISTIQUE
    × part des personnes physiques SANS nom publié   xx,x %   ✅ MESURE
    = plancher des restants hors de portée par nature   M

⚠️ **Et le second facteur porte SA propre extrapolation** : il est mesuré sur
*toutes* les personnes physiques du registre, alors que les restants sont celles
**qu'une source a détectées** — donc qui portent une activité réelle. *Rien ne dit
que les deux populations déclarent un nom au même rythme.*

> **Un chiffre composé de deux natures doit les montrer côte à côte, à la ligne
> où il se calcule. Une réserve écrite en fin de rapport ne voyage pas avec le
> nombre; une étiquette sur la ligne, oui.**

---

## N177 — Le seuil du verdict se pose avant de voir le chiffre

*(2026-09-20.)*

*« Un critère qu'on desserre parce qu'il a échoué n'en est plus un »* — la phrase
est d'Alexandre, le 17 septembre, et elle portait sur un critère de
non-régression. **Elle vaut aussi pour un seuil de mesure**, et cette fois elle
est **mécanique** plutôt que tenue à la main.

**Le seuil est une constante nommée, et il est IMPRIMÉ dans l'en-tête**, avant la
première donnée lue :

> *La règle stricte ne tient comme plancher que si son taux de faux positifs
> mesuré reste sous 20 %. Au-dessus, la sortie dit que la méthode NE TIENT PAS —
> et « aucune méthode ne tient » est un résultat, pas un échec.*

⚠️ **Et le verdict négatif ne pose AUCUN chiffre.** *La tentation, quand une
mesure a coûté une journée, est de rendre quand même le nombre « à titre
indicatif ».* **Un nombre rendu à titre indicatif est un nombre rendu.**

**Trois cas rendent `LE VERDICT N'EST PAS RENDU`**, et aucun n'invente de repli :
l'archive absente, aucun résolu lisible *(zéro mesure, pas un taux de 0 %)*, le
pont manquant. ⚠️ **Y compris quand une AUTRE grandeur est disponible** : la
spécificité mesurée sur les 2,7 M de noms du miroir ne remplace pas la précision,
et la substituer pour obtenir un verdict serait exactement la confusion que
l'outil existe pour éviter.

> **Un seuil choisi après coup n'est pas un seuil, c'est une justification.
> L'imprimer avant la première donnée est ce qui l'empêche de bouger.**

---

## N178 — Quand plusieurs hypothèses bien mesurées tombent, la question est mal posée

*(2026-09-20.)*

Cinq théories sur les 4 673 restants, toutes mesurées proprement, **toutes
tombées** :

| théorie | ce qu'elle rend |
|---|---|
| origine pancanadienne | 8 % |
| consortiums | 1,1 % |
| doublons exacts | 0,4 % |
| absence d'adresse | **+0** des deux côtés |
| personnes physiques | **non connaissable** — 57,1 % de faux positifs |

⚠️ **La tentation, à ce point, est la sixième théorie.** *Elle se présente
toujours bien : celle-là tient compte de ce qu'on vient d'apprendre.* **Mais cinq
mesures qui tombent ne disent pas « cherche mieux », elles disent que la
question est mal posée.**

**Ce que ça change dans la méthode, et c'est mécanique plutôt que sage :** on
décrit la population sur des axes que **le produit porte déjà**, au lieu de tester
une idée de plus. ⚠️ *Le moment où l'on invente un axe est le moment où l'on a
refait une théorie* — `famille_de`, `resolve_neq_by_name`, `Signal.detected_at`,
`faits_des_dossiers`, `est_numero` existaient tous. **Rien n'a été écrit pour
cette mesure sauf de la mise en forme.**

**Et la garde qui tient la discipline est un test**, pas une intention : aucun mot
de jugement — *« probablement récupérable »*, *« probablement pas »* — ne peut
apparaître dans un tableau.

> **Cinq hypothèses qui tombent ne demandent pas une sixième. Elles demandent de
> regarder la population au lieu de l'interroger.**

---

## N179 — Deux axes que personne n'avait regardés, et ils étaient là depuis le début

*(2026-09-20.)*

**Le nombre de signaux d'un dossier** et **l'âge de son signal le plus récent**
n'avaient jamais été ventilés. *Ni l'un ni l'autre ne demandait une collecte :
`Signal.company_id` et `Signal.detected_at` sont là depuis l'origine.*

⚠️ **Un axe ne manque pas parce que la donnée manque. Il manque parce que
personne ne l'a demandé.** *Et pendant cinq mesures, on a cherché ce qui
distinguait les restants dans ce qu'on avait déjà décidé de regarder —
l'origine, le nom, l'adresse.*

⚠️ **Et `detected_at` n'est pas `ingested_at`.** *La première est la date de
l'évènement source, la seconde celle de notre collecte.* **Lire la seconde aurait
mesuré nos cycles d'exécution et rendu un portrait de notre calendrier.** Les deux
colonnes existent côte à côte depuis toujours, et rien ne dit laquelle on lit —
sauf le commentaire du modèle, qui le disait.

> **Avant de conclure qu'une donnée manque, lister ce que le modèle porte déjà.
> Un champ jamais ventilé est indiscernable d'un champ absent, et il ne coûte
> pas la même chose.**

---

## N180 — Une garde qui lit des lignes ne distingue pas un libellé de la phrase qui l'interdit

*(2026-09-20. Deuxième occurrence — voir N136.)*

Le test le plus important du portrait vérifie qu'**aucun mot de jugement**
n'apparaît en sortie. Il est tombé du premier coup, sur ceci :

    pas de « probablement récupérable » ni de « probablement pas » :
    ce serait remplacer la mesure par une sixième théorie.

**La phrase qui INTERDIT les mots contenait les mots.** *Exactement N136, où un
commentaire citant l'idiome proscrit faisait tomber la garde de mise en forme.*

⚠️ **Mais le correctif n'est pas le même, et c'est ça qui vaut d'être noté.**
N136 avait réécrit le commentaire — *on avait plié le code devant la garde.* Ici
la garde a été **bornée aux sections**, l'en-tête exclu.

**Et la garde bornée est MEILLEURE, pas seulement plus commode :** un jugement se
glisse dans une **étiquette de tableau**, jamais dans un avertissement. *La version
qui lisait toute la sortie surveillait surtout de la prose.*

| occurrence | ce qu'on a plié | ce qu'on aurait dû se demander |
|---|---|---|
| N136 | le commentaire | — |
| **N180** | **la portée de la garde** | **qu'est-ce que je surveille vraiment?** |

> **Quand une garde tombe sur la phrase qui la justifie, la question n'est pas
> comment la contourner : c'est ce qu'elle devait surveiller. La bonne portée est
> presque toujours plus étroite que « tout ».**

---

## N181 — Une étiquette plus longue que sa colonne pousse le nombre

*(2026-09-20. Troisième occurrence, et la première qui soit gardée.)*

`« 92 et plus  ← AU-DESSUS du seuil »` fait 32 caractères dans une colonne de 30.
**Le nombre part deux caractères plus loin, la ligne cesse d'être alignée, et
aucun chiffre n'a bougé.** *Trouvé à l'œil, pour la troisième fois en trois
outils.*

⚠️ **Et dans les croisements, deux colonnes se TOUCHAIENT** —
`« ambigutrop faibleaucun cand. »`. *Deux nombres collés se lisent comme un
seul.*

**Trois tests remplacent le relecteur :**

| ce qui est vérifié | contre quoi |
|---|---|
| chaque étiquette d'axe | `LARGEUR_DES_AXES` |
| chaque étiquette de croisement | sa largeur propre |
| chaque abréviation de famille | **une de moins que la colonne** |

⚠️ **Et celui des sources lit `falkye/registry/sources.yaml`**, pas une liste
recopiée : *l'identifiant le plus long y fait 34 caractères, et le jour où l'on
en ajoute un plus long, c'est le test qui tombe — pas la mise en page, en
silence.*

> **Un tableau désaligné se relit de travers sans qu'on sache pourquoi. La
> largeur d'une colonne est une contrainte du code, donc elle se teste — et le
> test lit la source des valeurs, jamais leur copie.**

---

## N182 — Une échelle exclusive se mesure, elle ne s'affirme pas

*(2026-09-20.)*

L'échelle d'adresse du portrait — *code complet, région de tri seule, ville
seule, rien* — **est exclusive par construction**. ⚠️ *Mais « par construction »
est exactement ce qu'on croyait du code postal complet le 18 septembre, et il
s'est avéré que 100 % des 1 805 reposaient sur la région de tri.*

**Le test ne relit donc pas la cascade : il additionne les quatre niveaux et
exige le total de la population.** *Si un dossier tombait dans deux niveaux, le
total déborderait — et c'est le seul symptôme qu'une exclusivité cassée produit.*

⚠️ **La même prudence vaut pour ce qui n'est PAS exclusif, et il faut le dire à
l'endroit où on pourrait l'additionner :** les formes du nom se cumulent — *un nom
porte une parenthèse ET une conjonction* — et leur total dépasse la population
exprès.

> **Une partition annoncée est une partition à vérifier. Le total est le seul
> endroit où une exclusivité cassée se voit, et il ne se voit que si on
> l'additionne.**

---

## N183 — Une affirmation qui vient de nous vaut une hypothèse, pas une mesure

*(2026-09-20.)*

*« L'EIMT n'a aucune classification »* était dit ici depuis plusieurs jours, et
servait de prémisse. **Alexandre a demandé de le lire dans le code avant d'en
tirer un plafond.** *Lecture faite* :

| l'affirmation | ce que dit `falkye/sources/eimt.py` |
|---|---|
| aucune classification | ✅ **vrai** — aucun `secteur_activite=` sur son `RawSignal` |
| donc rien à croiser | ⛔ **faux** — elle dépose `champs["profession"]`, la colonne `Occupation` |

⚠️ **Et la moitié fausse ne s'annule pas avec la moitié vraie : elle demande une
troisième colonne.** *Une profession décrit un **poste**, pas l'activité d'une
**entreprise**.* `« Cuisinier »` suggère un restaurant sans le dire, et la
traduire demanderait **une autre table encore**, distincte de celle qu'on
attendait déjà. **Fondue dans le compte, elle aurait gonflé le plafond; écartée
sans être nommée, elle aurait disparu.** *Elle est comptée à part.*

**Ce qui rend le défaut coûteux, et ce n'est pas l'erreur elle-même :** une
affirmation née dans une conversation n'a pas de preuve attachée, **et elle se
recite avec l'assurance d'une mesure**. *C'est le guide d'ingénierie, § « la
preuve voyage avec le fait », appliqué à ce qu'on a dit soi-même.*

> **Un fait qui vient de nous se relit à sa source avant de porter un chiffre.
> Et une affirmation à moitié vraie est plus dangereuse qu'une fausse : la
> moitié qui tient fait passer l'autre.**

---

## N184 — Une garde branchée sur la mauvaise source n'est jamais juste

*(2026-09-20.)*

La table des clés d'activité se recoupe contre le code, pour qu'une clé déclarée
qui n'existe plus se voie. ⚠️ **Le recoupement lisait `cles_lues_par_le_module`
— ce que le connecteur LIT de son fichier source.** *Or les clés déclarées sont
celles de `Signal.champs` : ce que le connecteur **dépose**.*

    row.get("Occupation")          ← ce qu'il LIT
    champs={"profession": …}       ← ce qu'il DÉPOSE

**`secteur_nature_contrat` n'est lue nulle part. Elle est écrite.** *Le test est
tombé rouge, et il aurait aussi bien pu tomber vert* — sur une clé qui se trouve
être lue ET déposée, la garde aurait validé sans rien vérifier.

**Corrigé par un SECOND lecteur d'arbre syntaxique**, `cles_du_sac_par_le_module`,
rangé **à côté du premier** plutôt qu'écrit dans l'outil qui en avait besoin.
⚠️ *Ce n'est pas une copie : les deux répondent à deux questions différentes, et
c'est précisément ce que la confusion avait effacé.*

> **Avant de croire une garde verte, se demander sur quoi elle lit. Une garde
> branchée sur la mauvaise source rend un verdict des deux couleurs, et aucun
> des deux ne veut dire ce qu'on croit.**

---

## N185 — Le remplissage d'une colonne d'archive n'est pas celui du miroir

*(2026-09-20.)*

*« `COD_ACT_ECON_CAE` est rempli à 99,6 % au registre »* — vrai, et **sans
rapport avec ce que `REQEntry.secteur_code` porte.** Lu dans
`falkye/sources/req.py::_resoudre_entreprise` :

| cas | d'où vient le code stocké |
|---|---|
| un établissement principal existe | `Etablissements.csv::COD_ACT_ECON` — ⚠️ **`COD_ACT_ECON_CAE` n'est JAMAIS lu** |
| sinon | `COD_ACT_ECON_CAE` |

⚠️ **Et l'origine n'est pas conservée.** *Rien dans le miroir ne dit laquelle a
servi pour une entrée donnée.* **Toute comparaison de deux codes entre eux
hérite de cette incertitude** : deux codes qui diffèrent pourraient différer
parce qu'ils ne viennent pas de la même colonne.

**C'est une réserve qui se nomme et ne se mesure pas** — *l'information n'est
plus là.* ⚠️ *La tentation était de la taire parce qu'elle n'a pas de chiffre :
une réserve sans chiffre reste une réserve.*

> **Le remplissage d'une source n'est pas celui de ce qu'on en a gardé. Entre
> les deux il y a un chargeur, et il choisit.**

---

## N186 — Le cinquième `split()[-2]`, et ce que le helper n'a pas empêché

*(2026-09-20. Cinquième occurrence — voir N144, N158, N172.)*

N172 a rangé `compte_de_la_ligne` dans `tests/conftest.py`, *« le seul endroit
que le PROCHAIN fichier de test trouvera sans y penser »*, et concluait
*« on verra »*. **On a vu : quatre occurrences dans un fichier neuf, le même
jour.**

⚠️ **Le helper était à portée, importable en une ligne, et je ne l'ai pas
cherché.** *Ce n'est pas un défaut de rangement : c'est qu'aucun rangement ne se
rappelle à qui ne le cherche pas.*

**Ce qui a attrapé le défaut est le test lui-même**, qui a rendu
`'50.0' == '1'` — *quatre fois d'affilée.*

| tentative | ce qu'elle protège | a tenu? |
|---|---|---|
| une note au tampon | le corpus | ⛔ |
| un helper dans le fichier | un fichier | ⛔ |
| un helper dans `conftest.py` | tous les fichiers **de qui le cherche** | ⛔ |
| *(non construit)* une garde qui lit les fichiers de test | tous | *inconnu* |

⚠️ **La quatrième ligne n'est PAS une proposition à exécuter** : elle est notée
parce que les trois premières ont la même forme — *elles dépendent toutes de la
mémoire de celui qui tape* — et que la quatrième est la première qui n'en
dépende pas. **Rien n'est construit.**

> **Un outil bien rangé protège ceux qui le cherchent. Pour les autres il faut
> une garde, et une garde n'est pas un rangement.**

---

## N187 — Porter le fait des deux côtés ne départage rien s'il est le même

*(2026-09-20.)*

Le plafond d'un départageur se calcule d'habitude comme une **intersection** :
les dossiers où le fait existe au dossier **et** chez tous les candidats.
⚠️ **Ce chiffre-là est trop haut, et d'une façon qui ne se voit pas.**

*Deux candidats qui portent tous les deux le code `5511` portent bien le fait —
et le fait ne les sépare pas.* **L'intersection compte un départage possible là
où il n'y en a aucun.**

**Le compte qui borne vraiment** : parmi ces dossiers, combien ont **au moins
deux candidats dont les codes DIFFÈRENT entre eux**.

⚠️ **Et il ne coûte rien**, ce qui est la raison de le rendre : *c'est une
comparaison des codes du registre entre eux, pas une traduction.* **Aucune
correspondance entre nomenclatures n'y entre**, donc il se calcule avant que la
table qui n'existe pas existe.

**La même question vaut pour tout départageur déjà construit** : la ville, le
code postal, la région de tri. *Un fait partagé par tous les concurrents est un
fait présent et inutile* — et `outils/departageurs.py` le sait déjà, il rend
`PLUSIEURS_COMPATIBLES`. **Ce qui manquait est de le compter AVANT de construire,
plutôt que de le découvrir dans les issues après.**

> **Un plafond qui compte la présence du fait compte trop haut. Ce qui borne est
> sa VARIANCE entre les candidats, et elle se mesure sans rien traduire.**

---

## N188 — Une lecture se fait là où sont les données, et il faut le vérifier AVANT

*(2026-09-20.)*

Demande : **lire des dossiers entiers et en tirer des motifs.** *Pas une mesure —
une lecture.* **La première chose à faire n'était pas d'écrire l'outil : c'était
de regarder si les dossiers étaient lisibles d'ici.**

    /tmp/claude-0/lecture_seule/data/miroirs.sqlite3     0 octet
    pilote libsql                                         absent

⚠️ **Et le détail qui tranche n'est pas que la base soit vide : c'est d'où
viennent les CANDIDATS.** *Un dossier vient de la base du produit; ses candidats
viennent du MIROIR.* **La moitié de ce qui était demandé — les candidats avec
leurs noms et leurs scores — n'existe pas dans cet environnement**, quelle que
soit la base qu'on atteindrait par ailleurs.

**Deux mauvaises réponses se présentaient, et la seconde était la plus
tentante :**

| ce qu'on aurait pu faire | pourquoi non |
|---|---|
| inventer une lecture plausible | **fabriquer des motifs qu'on n'a pas vus** — le contraire de tout le projet |
| lire la base distante par HTTP | rendrait les dossiers **sans les candidats**, en brûlant du quota pour une demi-réponse |

**La bonne réponse : le dire en deux phrases, et livrer l'instrument** — celui
qui rend la lecture possible là où les données sont.

> **Avant de promettre une lecture, regarder ce qui est atteignable. Une
> demi-lecture coûte le prix d'une lecture entière et ne répond à rien.**

---

## N189 — Le sac de champs se rend ENTIER, parce que le filtrer c'est déjà décider

*(2026-09-20.)*

L'outil de lecture rend `Signal.champs` **en totalité**, trié par clé, sans
sélection. *La tentation était de n'afficher que les champs « pertinents »* —
l'adresse, l'activité, la valeur — **parce qu'un sac entier est verbeux.**

⚠️ **Mais la piste qui a tenu — l'activité économique — est sortie d'un champ que
personne n'avait demandé.** *Quatorze hypothèses sont tombées, et celle qui a
survécu venait de regarder ce qui était là, pas ce qu'on cherchait.*

**Filtrer le sac aurait retiré d'avance ce qu'on ne savait pas encore vouloir.**
*Et le filtre ne se serait pas vu : une clé absente d'un affichage ressemble à
une clé absente du dossier.*

**La même règle a une seconde face, appliquée ici :** les valeurs sont rendues
**sans être interprétées** — une liste de classifications s'affiche comme une
liste, pas comme un libellé élu. *Élire une valeur dans une liste est une
décision, et elle n'appartient pas à un outil de lecture.*

> **Un instrument de lecture ne choisit pas ce qu'on regarde. Le jour où il
> filtre, il a déjà répondu à la question qu'on venait poser.**

---

## N190 — Une lentille employée d'abord confirme ce qu'on est allé chercher

*(2026-09-20. Le cas 19 sous une autre forme.)*

L'outil porte des **lentilles** — *un seul mot, sans code postal, tête numérique,
signal récent, signal vieux.* **Elles sont utiles et elles sont dangereuses, pour
la même raison.**

⚠️ **Employée AVANT d'avoir vu un motif, une lentille rend une lecture qui
confirme ce qu'on est allé chercher.** *On filtre sur « un seul mot », on lit
douze dossiers d'un seul mot, et on conclut que les noms d'un seul mot ont
quelque chose de particulier.* **Le cas 19 disait « un tri promu en échantillon »;
celui-ci est un filtre promu en découverte.**

**Donc : le balayage par défaut est à pas constant et sans lentille**, et quand
une lentille est active **la sortie le dit à l'endroit où on la lira**, avec le
compte avant et après.

⚠️ *La garde n'est pas technique — rien n'empêche de lancer l'outil avec une
lentille en premier.* **Elle est dans la sortie, parce que c'est là que le
lecteur de la semaine prochaine regardera.**

> **Un filtre sert à vérifier un motif, jamais à en trouver un. Et un instrument
> qui offre les deux doit dire, dans sa sortie, lequel des deux il est en train
> de faire.**

---

## N191 — La leçon de N180 a tenu au premier contact

*(2026-09-20.)*

N180 : *une garde qui lit des lignes ne distingue pas un libellé de la phrase qui
l'interdit*, et la bonne portée est presque toujours plus étroite que « tout ».

**L'outil de lecture a la même forme de garde** — *aucun pourcentage dans la
sortie* — **et son en-tête cite les pourcentages du 19 septembre** pour qu'on ne
les refasse pas. *Écrite sur toute la sortie, elle serait tombée.*

**Elle a été bornée aux sections de dossiers dès la première écriture**, par un
helper `_dossiers()` qui coupe l'en-tête, *avec la raison dans sa docstring.*

⚠️ **Ce n'est pas une réussite d'attention** : c'est que la note existait et
disait **où** regarder. *N180 ne dit pas « faire attention aux gardes » — elle
dit « la bonne portée est plus étroite que tout », ce qui est une instruction.*

> **Une note qui prescrit un geste se transfère; une note qui prescrit de la
> vigilance ne se transfère pas. La différence se voit au premier cas suivant.**
