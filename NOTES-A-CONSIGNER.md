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
