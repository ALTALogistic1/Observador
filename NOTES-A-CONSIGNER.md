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
- **✏️ CORRIGÉ le 13 septembre, avant écriture** *(Alexandre)* : **« le donneur d'ouvrage est
  exploitable maintenant » est FAUX**, et la phrase a été écrite en croyant qu'il existait dans
  le produit. **Le faire exister est un changement de modèle, pas un réglage.** *Les deux
  prospects attendent donc chacun quelque chose : le fournisseur attend l'appariement, le
  donneur attend d'exister.* **C'est la méthode qui a rattrapé ça** — la note n'était pas
  encore au corpus.

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
- ⚠️ **ET LE CORPUS L'INVOQUE COMME SI ELLE L'ÉTAIT** *(relevé des objets gradués, « Fiabilité de
  la taille », spéc. 8.2)* : *« déclarée = bande d'effectifs du registre »*. **La provenance est
  écrite comme un critère disponible; aucune source ne la fournit, et le miroir ne la stocke
  pas.**
- **Destination relevée le 13 septembre** *(Alexandre)* : **journal des cas, comme forme
  neuve** — pas seulement une ligne de registre.
- **Le nom de l'écart, à inscrire tel quel : une règle qui nomme une donnée que personne ne
  possède se lit comme une règle appliquée.** *Rien ne la distingue, à la lecture, d'une règle
  qui tourne — elle a une valeur, une provenance, une place dans une taxonomie.*
- **Et le mécanisme qui l'a cachée est l'inverse de l'habituel** : **le code SAVAIT et le corpus
  non.** `scoring.py::_score_appel_offres` porte l'aveu depuis toujours — *« faute d'estimation
  fiable… tant qu'aucune source ne donne un effectif de façon systématique »* — mais un aveu dans
  un commentaire ne voyage pas. **Les cas précédents allaient du corpus vers le code qui
  dérivait; celui-ci va du code vers le corpus qui ne l'a jamais su.**

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

### N10 — La stratégie du portrait : la direction retenue pour le cerveau
- **Notée le** : 2026-09-13
- **Destination — CONFIRMÉE par Alexandre le 13 septembre** : **découpée par nature,
  comme D35 l'a fait pour les prix — pas un document neuf.**
  - **Charte, section 9** *(la frontière du non déterministe)* : le principe, les trois couches,
    la frontière entre lecture et portrait, le découpage déterministe/non déterministe. **Parce
    que la règle y est DÉJÀ** — la charte porte le test mot pour mot : *« si la sortie ne peut
    pas être reconstruite à partir de la structure de faits qui l'a produite, elle est fausse »*.
    *La stratégie ne pose pas un principe neuf : elle donne sa structure à celui-là. L'écrire
    ailleurs créerait une seconde source de vérité pour la même règle.*
  - **Spécification 8.x** : la correction de ce que le grade mesure — *la distance entre ce que
    les faits établissent et ce que CET utilisateur peut servir*, et la règle A / AA / AAA.
    **Parce que le grade y vit déjà**, et que c'est un état de mécanisme, pas un principe :
    le chantier 22 le raffinera.
  - **Registre** : la question ouverte — *une association peut-elle à elle seule faire monter le
    grade?* **Inclinaison d'Alexandre : non.** *Inscrite comme inclinaison, pas comme décision.*
  - **Registre, D33** *(le cerveau)* : les trois choses que la stratégie révèle — le jugement est
    la facette qui travaille le plus et n'a aucun chantier; la mémoire produit le grade *(sans
    elle le portrait dit qu'il s'est passé quelque chose, avec elle il dit pourquoi c'est
    maintenant)*; l'association est **le seul endroit où le produit affirme ce que les sources ne
    disent pas**.
- **Et le mandat du chantier 22 y RENVOIE plutôt que de la redécrire.**

### N11 — L'appariement n'est plus un chantier parmi d'autres
- **Notée le** : 2026-09-13
- **Destination** : registre *(près de D15)* et Partie 0 de l'audit — l'ordre par coût d'attente.
- **Constat, dicté par Alexandre et appuyé par le relevé** : sans NEQ — **pas de secteur**, donc
  pas de raison d'être dans le portrait; **pas de dossier stable**, donc pas de mémoire; **pas de
  croisement**, donc pas d'association. *Les trois facettes du cerveau dépendent d'un même
  verrou.*

### N12 — Un signal que personne ne produit, et que le NEQ débloquerait
- **Notée le** : 2026-09-13
- **Destination** : spéc. section 7 *(types de signaux)* ou mandat du chantier 22.
- **Constat** : *un entrepreneur en construction qui décroche un contrat de construction fait son
  métier; le même qui décroche un contrat d'une autre nature élargit son activité.* **Ça demande
  le secteur du fournisseur ET l'objet du contrat.** *On a les deux dans les données — le secteur
  par le REQ, l'objet par la classification du SEAO — et ni l'un ni l'autre dans le produit.*

### N13 — La classification du SEAO : ce qu'il faut mesurer avant tout code
- **Notée le** : 2026-09-13
- **Destination** : registre *(la correspondance code → sphère est une décision de produit,
  à prendre avec Alexandre)* et mandat du chantier 22.
- ⚠️ **La mesure préalable NE PEUT PAS se prendre sur notre base** : le champ n'ayant jamais été
  lu, il n'est nulle part en base. *Il faut relire un fichier SEAO à la source (CKAN) pour savoir
  quels codes existent et à quelle fréquence — donc zéro lecture facturée, mais un accès réseau.*
  **Et le 93 % ne peut pas être confirmé par nos données, seulement par la source.**
- ⚠️ **Le passé ne l'aura pas** : `champs` est écrit à l'ingestion et la déduplication par
  `source_ref` fait qu'un avis déjà vu ne repasse pas. **La classification n'existerait que pour
  les signaux ingérés APRÈS le changement**, sauf migration qui relit les fichiers source et
  complète par `source_ref`.
- **Le garde-fou, à reprendre mot pour mot** : un contrat de construction ne doit pas ouvrir d'un
  coup la construction, l'assurance, le cautionnement, l'équipement et l'entretien. *Un signal qui
  sert cinq sphères sans discriminer n'en sert aucune.* **La classification DISTINGUE les signaux
  entre eux; elle ne multiplie pas les correspondances d'un même signal.**

### N14 — Le donneur d'ouvrage comme entité — décision ouverte
- **Notée le** : 2026-09-13
- **Destination** : registre, entrée neuve, **rattachée à D27/D28/D29 et à la faille C**.
- **Ce qu'il faudrait pour la trancher** : un registre officiel des entités publiques *(D27)*, une
  règle de classement avec réponse par défaut *(D28)*, l'identifiant qui fait foi *(D29)* — et
  **une identité interne distincte du NEQ**, qui est exactement ce que le chantier 3+4 construit.
  *C'est le même changement de modèle : le produit n'a qu'une sorte d'entité, pivotée sur le NEQ.*

### N15 — La bande d'effectifs : le blocage est une autorisation
- **Notée le** : 2026-09-13
- **Destination** : `falkye-recommandations-sources.md`, et registre *(D5 — autorisation OQLF)*.
- **Constat** : aucune source active ne fournit d'effectif. **L'OQLF confirmerait un seuil de
  25+ employés, daté, par un organisme public** — la spéc. 8.2 le classe déjà en taille
  *mesurée*. **Son blocage n'est ni technique ni budgétaire : c'est une demande d'autorisation au
  gouvernement du Québec** *(D5)*.

### N16 — La description des besoins du SEAO — à noter, pas à faire
- **Notée le** : 2026-09-13
- **Destination** : mandat du chantier 22, en matière disponible.
- **Constat** : captée, jamais ouverte. **Elle ne se traite pas comme la classification** : texte
  libre, donc **matière pour le langage et l'association**, pas pour une règle. *Et l'association
  est le seul endroit où le produit affirme ce que les sources ne disent pas — donc elle attend
  que le lien champ ↔ sphère soit écrit et vérifiable.*

### N17 — Le portrait à deux blocs — décision prise
- **Notée le** : 2026-09-13
- **Destination** : charte section 9 *(avec la stratégie, N10)* pour la forme; **mandat du
  chantier 21** pour ce qu'elle impose au langage.
- **Décision d'Alexandre** : le portrait porte **deux blocs distincts, et la séparation est
  visible pour l'utilisateur**. Le premier **énumère la situation sans rien inventer** — nom,
  raison d'être, **adresse**, faits datés. Le second s'ouvre par *« Pour un [profil], cette
  situation peut représenter… »*.
- **Le « peut représenter » est la marque du non déterministe** : le produit n'affirme pas que
  l'entreprise a ce besoin, il dit ce que la situation **peut** signifier. **Chaque élément du
  second bloc remonte à un fait du premier.**
- **Seul le second change d'un utilisateur à l'autre : un portrait, plusieurs lectures.**
- ⚠️ **Conséquence pour le chantier 21** : le langage doit produire **deux registres, pas un** —
  *et le second est la partie que l'utilisateur lira en premier.*

### N18 — L'adresse est une exigence de SORTIE, pas une option
- **Notée le** : 2026-09-13
- **Destination** : spéc. *(ce qu'un portrait doit porter)* et mandat du chantier 21.
- **Un portrait sans adresse n'est pas actionnable**, pour tout type de prospect.
- **D'où elle vient, et ce qui arrive quand elle manque** : le REQ ne la donne **que si
  l'entreprise est résolue**; l'EIMT en capte une et **la jette**; le SEAO en porte une à 99,9 %
  **qu'il ne captait pas jusqu'au 13 septembre**. *Même cause que le gain partiel sur
  l'appariement, même correctif.*

### N19 — Un motif absent du 22 : la concentration de sources DIFFÉRENTES
- **Notée le** : 2026-09-13
- **Destination** : mandat du chantier 22 *(22.1)*.
- **Le 22.1 porte « répétition sur fenêtre », mais pour un MÊME type de signal.** Les simulations
  ont produit **six faits de cinq sources en quatre-vingts jours**, et **deux recours à l'EIMT en
  onze semaines**. **La concentration est le fait, pas chaque élément.**

### N20 — Le motif « absence attendue » existe sans aucun seuil
- **Notée le** : 2026-09-13
- **Destination** : mandat du chantier 22, avec sa dépendance.
- **Il a servi dans trois simulations sur cinq** — *aucun mandat touchant X à ce jour* — **et à
  chaque fois sans savoir combien de temps d'absence signifie quelque chose.**
- ⚠️ **Dépendance à inscrire** : le **22 peut DÉCLARER le motif, il ne peut pas le CALIBRER sans
  le 17**.

### N21 — Deux comparaisons que le produit capte et ne fait jamais
- **Notée le** : 2026-09-13
- **Destination** : mandat du chantier 22.
- **La ville du signal contre l'adresse de l'entreprise** — *dans la simulation de la MRC, toute
  la lecture repose là-dessus.* Les deux valeurs existent; aucune règle ne les compare.
- **L'ancienneté d'une adresse** — *« même adresse depuis 2011, établie depuis 1998 »*.
- ⚠️ **Réponse, vérifiée dans le code le 13 septembre : le produit ne porte NI l'une NI
  l'autre.** Le connecteur REQ ne lit que deux dates — `DAT_MAJ_INDEX_NOM` et
  `DAT_INIT_NOM_ASSUJ` *(qui sert à trier les noms)*. **Aucune date d'immatriculation, aucune
  date d'établissement.** *Si `Entreprise.csv` en porte une, elle est simplement non lue —
  `inspect_zip` le dirait sur l'hôte.* **Et « même adresse depuis 2011 » n'est pas dérivable** :
  l'état de diff ne connaît l'adresse que depuis le premier import — au mieux *« inchangée
  depuis qu'on regarde »*.

### N22 — Un cas d'usage que les cinq facettes n'ont jamais prévu : RETENIR
- **Notée le** : 2026-09-13
- **Destination** : registre, entrée neuve.
- **Un utilisateur peut chercher à retenir plutôt qu'à vendre.** *Une MRC veut savoir qu'une
  entreprise de son territoire grandit ailleurs.* **Le corpus prévoit ce public; les cinq
  facettes ont toutes été pensées pour un fournisseur.**
- ⚠️ **Et le grade aussi** : *« Sur mesure » ne veut pas dire la même chose quand on veut
  EMPÊCHER quelque chose.*

### N23 — Ce que cinq simulations de portrait confirment
- **Notée le** : 2026-09-13
- **Destination** : audit *(Partie 0 — l'ordre par coût d'attente)* et registre.
- **Aucune source nouvelle n'a manqué.** Les cinq portraits ont tenu avec l'existant plus l'OQLF,
  le RACJ, le CIPO et les permis de Montréal — **tous déjà au catalogue**. *Ce qui manquait :
  l'appariement, le secteur promu, et des lectures qui n'existent pas.*
- **Le secteur du REQ a porté une association dans CHAQUE simulation** — *la seule qui ne vient
  d'aucun signal : elle vient de ce que l'entreprise EST.*
- **Les établissements du REQ ont porté trois lectures**, et le relevé dit qu'ils n'atteignent
  jamais le dossier.
- ⚠️ **L'OQLF a porté deux simulations, pour deux raisons distinctes** — le NEQ sans appariement,
  et le seuil de 25+ daté. **Cinquième dans l'ordre du catalogue à cause de D5; les simulations
  suggèrent qu'elle devrait être première.** *À trancher, pas à faire.*

### N24 — L'erreur du RDPRM, et la règle qu'elle rend visible
- **Notée le** : 2026-09-13
- **Destination** : charte section 9 *(avec la stratégie)* ou mandat du chantier 21 — **là où on
  conçoit un portrait**, pas seulement là où on décrit une source.
- **Erreur d'Alexandre, notée comme telle** : le RDPRM a servi dans une simulation. *Il ne pouvait
  pas y être — import manuel, payant à l'unité : il n'apparaît que si quelqu'un cherche DÉJÀ
  cette entreprise. Or c'est le portrait qui devait la révéler.*
- **La règle : une source d'enrichissement à la demande ne peut jamais figurer dans le portrait
  qui la découvre.** *Le corpus la porte déjà avec son mécanisme 2 — ce qui a manqué n'est pas la
  règle, c'est sa présence là où le geste se fait.*

### N25 — La mesure du SEAO sur un fichier réel, 13 septembre 2026
- **Notée le** : 2026-09-13
- **Destination** : fiche de source du SEAO et mandat du chantier 22.
- **`hebdo_20260831_20260906.json`, 4 750 releases, 4 127 attributions** : classification
  **93,6 %** *(schéma **UNSPSC**, **1 242 codes distincts en une semaine**, 1 866 avec les
  additionnelles)*; `buyer.id` **100 %**; **ville du fournisseur 87,7 %**, adresse 99,9 %;
  `items[].description` 93,6 %; **`tender.description` 0,0 %**; statuts : 4 125 `active`,
  **2 `cancelled`**.
- **Deux corrections que la mesure impose** : la classification est portée par **l'ITEM**, jamais
  par le tender; et **le champ capté sous le nom `description_tender` ne contenait rien, dans
  100 % des cas**.
- **Et le registre demandait déjà ce qui manquait** : `sources.yaml:seao` déclare
  `adresse_entreprise_adjudicataire` et `secteur_nature_contrat`. **Ce n'était pas une exigence
  neuve, c'était une exigence non tenue.** *Forme voisine de N5 : le registre savait, le
  connecteur non.*
