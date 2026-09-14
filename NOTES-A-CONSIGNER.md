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

---

*Vide — les soixante-quatre notes des 13 et 14 septembre 2026 ont été portées au corpus
le 14 septembre. C'est le cas normal entre deux tâches.*
