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
