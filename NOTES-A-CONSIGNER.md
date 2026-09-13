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

## Tâche en cours — le relevé qui prépare le chantier 22

### N1 — Le SEAO porte DEUX prospects par avis, et le corpus n'en décrit qu'un
- **Notée le** : 2026-09-13
- **Destination** : corpus — spéc. section 7 (fiche du signal `appel_offres`) et mandat du
  chantier 22. **Dicté par Alexandre.**
- **Le donneur d'ouvrage est le prospect DIRECT** : il entreprend quelque chose, la
  classification dit quoi, son identifiant est présent à 100 %. **Le fournisseur retenu est un
  prospect CONDITIONNEL** : un contrat décroché crée des besoins — embauche, équipement,
  assurance, cautionnement, fonds de roulement — **mais seulement quand il sort de l'ordinaire
  pour lui**. *C'est déjà la calibration du corpus : premier contrat, ou disproportion par
  rapport à la bande d'effectifs.* Et l'avis porte ce que peu de signaux ont : **un montant et
  une date**.
- **Ce qui décide de l'ORDRE entre les deux, et c'est mesuré** : le fournisseur exige la
  mémoire *(premier contrat)* et la bande d'effectifs *(disproportion)* — donc qu'il soit
  résolu, ce que la majorité n'est pas. **Le donneur d'ouvrage est exploitable maintenant, le
  fournisseur attend l'appariement.**
- ⚠️ **État du code au 13 septembre** : le connecteur ne crée une entreprise **que pour le
  fournisseur** *(`award.suppliers[].name` → `RawSignal.nom_entreprise`)*. **Le donneur
  d'ouvrage n'existe comme entité nulle part** — son nom vit dans `Signal.champs`, lu
  seulement par le message de premier contact.

### N2 — Relevé champ par champ du SEAO, et trois champs qui expliquent l'uniformité
- **Notée le** : 2026-09-13
- **Destination** : corpus — le relevé du second rôle des sources (audit), à côté de celui du
  11 septembre.
- **Jamais LUS, alors qu'ils sont dans l'avis** : *(a)* **la classification normalisée** —
  aucune lecture de `tender.classification` ni de `items[].classification`; *(b)* **l'identifiant
  du donneur d'ouvrage** — seul son NOM est pris, jamais `buyer.id` / `parties[].identifier`.
- **Conservé sans usage** : la description sommaire des besoins *(`champs["description_tender"]`)*,
  la devise, le statut d'attribution.
- **Utilisé sans être promu** : le nom du donneur *(message de premier contact)*, le titre de
  l'avis *(mots-clés du profil — `matching.py`; motif de la notification)*, le montant
  *(`valeur_associee`, paliers absolus du score)*.
- **Promu au dossier : RIEN.**
- ⚠️ **C'est la cause directe de l'uniformité des signaux.** *Le mandat du chantier 22 nomme la
  classification normalisée comme l'antidote au fait que tous les signaux portent la même
  sphère — le SEAO la porte, et on ne s'en sert pas.* **La sphère vient du `signal_type_id`,
  donc elle est la même pour tout avis, quel que soit l'objet du contrat.**

### N3 — Le statut d'attribution est capté et jamais filtré
- **Notée le** : 2026-09-13
- **Destination** : à trancher — défaut à corriger, pas décision de conception.
- **Constat** : `champs["statut_attribution"]` est conservé et aucun code ne le lit. *Un avis
  annulé ou infructueux produirait donc un signal comme un autre.* **Non mesuré** : on ne sait
  pas combien d'avis portent un statut autre qu'attribué.

### N4 — Relevé du REQ : ce qui atteint le dossier, et ce que le REQ ne porte pas
- **Notée le** : 2026-09-13
- **Destination** : corpus — même relevé que N2.
- **Promus au dossier** *(par `_enrich_from_req`, seulement si le champ est vide **et** si
  l'entreprise est RÉSOLUE)* : nom officiel, statut légal, adresse, ville, code postal,
  **secteur d'activité — code ET libellé**.
- **Donc le produit PORTE le secteur d'activité.** *La réponse à « faut-il une source pour
  ça » est non : il faut l'appariement.* **Le secteur manque exactement pour les entreprises
  non résolues, c'est-à-dire le mur de D15, et pas pour une autre raison.**
- ⚠️ **La région, elle, n'arrive JAMAIS par le REQ** : `REQEntry.region` est écrit à `None`
  faute de région administrative dans le vrai schéma du REQ. *Seuls les connecteurs en
  donnent une — et c'est sur `raw.region` que porte le filtre territorial (D41).*

### N5 — La bande d'effectifs n'existe nulle part, et deux endroits du code le disent déjà
- **Notée le** : 2026-09-13
- **Destination** : corpus — elle conditionne la moitié « fournisseur » de N1.
- **Constat** : le miroir REQ ne stocke aucun effectif, et le dossier non plus.
  `taille_entreprise.py` **estime** une tranche à partir du volume cumulé de postes des
  signaux de recrutement — *proxy assumé et documenté, pas une mesure*. Et
  `scoring.py::_score_appel_offres` porte déjà l'aveu : paliers absolus *« faute d'estimation
  fiable de la taille de l'entreprise… tant qu'aucune source ne donne un effectif de façon
  systématique »*.
- **Conséquence directe** : la condition « disproportion par rapport à la bande d'effectifs »
  **n'est pas calculable aujourd'hui**, même pour une entreprise résolue.

### N6 — Les établissements du REQ n'atteignent pas le dossier
- **Notée le** : 2026-09-13
- **Destination** : corpus — même relevé que N2/N4.
- **Constat** : les établissements sont lus *(adresse, ville, code postal, secteur, nom,
  principal)* et servent un **grain de diff distinct** qui émet un signal
  `nouvel_etablissement_secondaire`. **Mais rien n'atteint le dossier** : *combien, où, depuis
  quand* ne se lisent nulle part par entreprise. *Le catalogue dit que plusieurs nouveaux
  établissements croisés avec un autre signal deviennent très forts — ce croisement n'a donc
  aujourd'hui aucune donnée à croiser, sinon les signaux eux-mêmes.*
- **Et « depuis quand » est borné par le premier import** : un établissement n'existe comme
  événement que s'il apparaît entre deux éditions du miroir.

### N7 — Les donneurs d'ouvrage : une population qui n'est pas homogène
- **Notée le** : 2026-09-13
- **Destination** : registre, **D27 à D29** *(clé du chantier 3, règle public/privé, identifiant
  qui fait foi)*.
- **Constat, vérifié à la source du gouvernement du Québec** : l'obligation de publier au SEAO
  ne pèse que sur les **organismes publics** — ministères, santé, éducation, municipalités —
  *mais d'autres peuvent l'utiliser volontairement* : sociétés d'État à vocation commerciale,
  OSBL, entreprises privées. **Donc un donneur d'ouvrage n'est pas « public » par construction**,
  et une règle de classement qui le présumerait se tromperait en silence.
- **Outil posé pour préparer la règle sans la prendre** : `outils/donneurs_douvrage.py` —
  il compte les donneurs distincts et **refuse d'en attribuer le type** *(ce serait D28,
  devinée)*.

### N8 — Les programmes d'immobilisations municipaux — INSTRUITE, pas construite
- **Notée le** : 2026-09-13
- **Destination** : `falkye-recommandations-sources.md`, comme piste instruite.
- **La base légale est solide et datée** : le conseil d'une municipalité **doit**, au plus tard
  le **31 décembre** de chaque année, adopter le programme des **trois** exercices suivants, en
  détaillant **l'objet, le montant et le mode de financement** de chaque dépense en
  immobilisations dont la période de financement excède 12 mois. *Loi sur les cités et villes,
  art. 473; Code municipal, art. 953.1 — délai porté au 31 janvier en année d'élection.*
- **C'est la promesse du produit prise à sa source** : ce qu'une municipalité **compte faire**,
  un à trois ans avant l'appel d'offres. *Là où le SEAO dit ce qui est déjà attribué.*
- **Montréal va plus loin que la loi** : un programme **décennal** (PDI), publié en données
  ouvertes sous **CC-BY 4.0**. ⚠️ **Et il est sur Données Québec (CKAN)** — donc joignable par
  le client CKAN que le produit utilise déjà, sans nouveau mécanisme d'accès.
- **La limite est le format, et elle décide de la portée** : Montréal publie du tableur; **la
  plupart des autres municipalités publient un PDF sur leur propre site**. *Une source « PTI
  municipal » générique n'existe pas — il y aurait Montréal, puis un long travail par
  municipalité.*

### N9 — Trois pistes que le corpus n'a jamais instruites — ni retenues, ni écartées
- **Notée le** : 2026-09-13
- **Destination** : `falkye-recommandations-sources.md`, à l'état « jamais instruite », ce qui
  n'est ni retenue ni écartée. *Ne pas y toucher avant instruction.*
- **Régie du bâtiment du Québec** — les catégories de licence disent **ce qu'un entrepreneur
  est autorisé à exécuter**. **Registre foncier.** **Gazette officielle du Québec.**
