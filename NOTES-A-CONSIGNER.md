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
- ⚠️⚠️ **CORRIGÉ LE 14 SEPTEMBRE, ET C'EST LA NOTE ELLE-MÊME QUI ÉTAIT FAUSSE.** *Lu dans
  l'archive REQ réelle (`req-data-2026-09-02`), en-tête d'`Entreprise.csv` :* **`COD_INTVAL_EMPLO_QUE`
  — le code d'intervalle d'employés au Québec — EXISTE**, décodé par `DomaineValeur.csv` en quinze
  valeurs : *A = 1 à 5, B = 6 à 10, C = 11 à 25, D = 26 à 49, E = 50 à 99, F = 100 à 249, G = 250 à
  499, H, I, J, K, L = plus de 5 000, **N/P = non déclaré, O = aucun***.
- **Mesuré sur les 60 000 premières lignes** *(échantillon NON aléatoire — le fichier est ordonné
  par NEQ, donc les vieilles entreprises sont sur-représentées)* : **le champ est rempli à 100 %**,
  et **~47 % portent une bande exploitable** (A à L); ~47 % disent « Aucun », ~7 % « Non déclaré ».
- **Donc « aucune source ne fournit la bande d'effectifs » est FAUX.** Le REQ la fournit, pour
  toute entreprise immatriculée, **gratuitement, dans un fichier déjà téléchargé et déjà importé**.
  *Ce qui manque est une colonne au miroir et une lecture, pas une source ni une autorisation.*
- **✏️ L'écart change donc de nature, et de nom.** Le corpus disait *« déclarée = bande d'effectifs
  du registre »* : **il avait raison sur la source et tort sur le produit.** Ce n'est pas une règle
  qui nomme une donnée que personne ne possède — **c'est une règle juste dont personne n'a vérifié
  qu'elle était branchée.**
- ⚠️ **Et l'aveu du code, que cette note citait hier comme le témoin fiable, est lui-même faux** :
  `_score_appel_offres` justifie ses paliers absolus *« tant qu'aucune source ne donne un effectif
  de façon systématique »* — **la source en donne un depuis toujours.** *La confession du code
  n'était pas un savoir : c'était une croyance non vérifiée, écrite avec l'autorité d'un constat.*
  **C'est ça, la forme neuve à écrire au journal** — pas « le code savait et le corpus non », mais
  **un commentaire de code qui affirme une absence que personne n'est allé vérifier, et que tout le
  monde lit ensuite comme une mesure.**

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

### N26 — Ce que l'archive REQ porte et que le produit ne lit pas
- **Notée le** : 2026-09-14
- **Destination** : fiche de source du REQ, mandat du chantier 22, et registre.
- **Lu par plages HTTP sur l'archive réelle, sans la télécharger** — en-têtes des six CSV.
  `Entreprise.csv` porte, **tous remplis à 100 % sur l'échantillon de 60 000 lignes** :
  **`DAT_IMMAT`** *(date d'immatriculation — « établie depuis 1998 » devient disponible)*,
  **`DAT_CONSTI`**, **`COD_INTVAL_EMPLO_QUE`** *(voir N5)*. Et **`DESC_ACT_ECON_ASSUJ2`** — un
  **second** secteur d'activité, présent sur 15,2 %. `IND_FAIL` *(faillite)* et `DAT_CESS_PREVU`
  *(cessation prévue)* existent aussi.
- **Le connecteur n'en lit AUCUN** : il ne prend que `DAT_MAJ_INDEX_NOM`, le statut, le nom,
  l'adresse et un secteur.
- ⚠️ **Ce que ça change pour la mémoire** *(question d'Alexandre)* : oui, la date
  d'immatriculation existe. **Mais « même adresse depuis 2011 » reste indérivable** — c'est
  l'ancienneté de l'ENTREPRISE qui devient disponible, pas celle de son adresse.

### N27 — Le profil n'accueille aucun des trois publics non commerciaux
- **Notée le** : 2026-09-14
- **Destination** : registre *(avec N22)* et spéc. section 4.
- **Vérifié dans le code** : `TypeProfil` ne connaît que **`fournisseur`, `client`, `les_deux`** —
  *et « client » reste commercial : quelqu'un qui achète.* Un besoin est une paire **sphère +
  usage**; **un chercheur d'emploi n'a pas de sphère à servir, il a un métier.**
- ⚠️ **Et le mode de défaillance est le pire possible** : `generer_notifications` fait
  `if not profile.besoins_fournisseur(): continue` — **un profil sans besoin de type « offre » ne
  produit rien, en silence**, sans erreur ni trace. *C'est le silence que la charte §17 nomme comme
  le mode de défaillance principal, dans le chemin même qui sert les profils.*
- `ProfileNeed.type_besoin` admet déjà une autre valeur que « offre » — **l'axe existe, le moteur
  ne l'implémente pas.**

### N28 — Le portrait de tendance — décision prise
- **Notée le** : 2026-09-14
- **Destination** : spéc. *(un troisième mode, à côté de la veille et de la recherche ponctuelle)*,
  et charte section 9 avec la stratégie du portrait pour la contrainte de forme.
- **Décision d'Alexandre** : consulter un prospect déjà connu et **engendrer un portrait sur les
  douze derniers mois**. **Un objet distinct, pas une variante** — *le portrait d'opportunité décrit
  une situation au présent, le portrait de tendance décrit un mouvement sur un an.*
- **Aucun grade.** *Le grade mesure la distance entre les faits et ce que l'utilisateur peut servir
  MAINTENANT; A/AA/AAA ne s'applique qu'au présent.*
- **Même structure, même contrainte de forme, et le second bloc reste** — *« pour un [profil], cette
  évolution peut représenter… »*.
- **Douze mois, une seule fenêtre, non paramétrable. Paliers Radar et Radar+** — *c'est une
  fonctionnalité, pas une source, donc le seuil ne reproduit pas la faille du portefeuille.*
- ⚠️ **Et la limite « depuis qu'on regarde » est une contrainte de ce mode, pas un détail** : *un
  portrait sur douze mois d'un produit qui observe depuis six est TRONQUÉ, et il doit le dire.*
  **À formuler partout où l'affirmation apparaîtra : « inchangée depuis qu'on regarde » n'est pas
  « inchangée depuis 2011 ».**

### N29 — Le produit ne sait dire aucun NIVEAU — question ouverte
- **Notée le** : 2026-09-14
- **Destination** : registre, entrée neuve, **rattachée au portrait de tendance (N28)**.
- **La question, non tranchée** : *le produit peut-il dire qu'une entreprise est en élan, stable, ou
  moribonde avec un sursaut récent?* **C'est ce qu'Alexandre voudrait, et le produit n'a pas de quoi
  le faire.**
- **Ce qui manque, nommé** : **un indicateur de NIVEAU.** *Les signaux disent des ÉVÉNEMENTS, jamais
  un niveau.* **Deux exceptions** : le montant des contrats, et le champ capacité du RACJ.
- **C'est le même vide que la bande d'effectifs** — *et la bande d'effectifs vient d'en sortir
  (N5) : le REQ en porte une, ce qui donne au moins un niveau de TAILLE, à défaut d'un niveau
  d'activité.*

### N30 — « Absence attendue » : une lecture disponible et inutilisable
- **Notée le** : 2026-09-14
- **Destination** : mandat du chantier 22, **à l'endroit où le 22 rencontrera le motif** — pas dans
  une note de dépendance en fin de document.
- **Il a servi dans quatre simulations sur sept, et le jugement l'a écarté chaque fois qu'il a été
  honnête** : *aucun signal de recrutement depuis cinquante-cinq jours ne dit rien de fiable sans
  seuil.*
- **Le motif existe au 22.1, sa calibration appartient au 17, et le 17 est parmi les derniers du
  plan.** *Une lecture disponible et inutilisable est pire qu'une lecture absente : elle a l'air
  d'un outil.*

### N31 — Le jugement pose TROIS questions, et trois natures de refus
- **Notée le** : 2026-09-14
- **Destination** : charte section 9 *(avec la stratégie du portrait)* et **D33** *(le cerveau —
  le jugement est la facette qui travaille le plus et n'a aucun chantier)*.
- **Les trois** : *(1)* **Est-ce que je peux soutenir ça?** — une lecture porte les faits qu'elle
  consomme; **une absence ne porte rien.** *(2)* **Est-ce que ça enrichit le portrait pour CET
  utilisateur?** — filtre ce qui est soutenu mais hors sujet. *(3)* **Est-ce que ce qui reste
  suffit à déranger quelqu'un?** — le seuil de publication, **déjà en 8.5**.
- **Trois natures de refus** : *ce que je ne peux pas dire, ce qui ne sert pas, ce qui ne vaut pas
  un dérangement.*
- **Le principe qui les gouverne** : **le produit affirme des faits; pour tout le reste, il parle
  au conditionnel.** *Ce n'est pas une précaution de style — c'est une frontière VISIBLE dans le
  portrait : le premier bloc affirme, le second est au conditionnel.* **C'est ce qui rend la forme
  à deux blocs meilleure qu'un texte unique nuancé.**
- ⚠️ **Conséquence pour les réserves, et elle est contre-intuitive** : une réserve **échoue à la
  première question** *(elle ne porte aucun fait)* **mais réussit à la deuxième** — *« rien
  n'indique si elle est déjà couverte » est très pertinent pour un courtier.* **Donc elle n'est
  pas supprimée, elle est REFORMULÉE EN ACTION.** *La charte porte déjà la forme : une réserve se
  formule par l'action qu'elle appelle.* Pas *« on ignore si elle est couverte »* — **« à valider
  avant l'appel »**. *Même information, conditionnel préservé, action nommée.* **C'est du langage,
  donc le 21.**

### N32 — Le sixième motif du 22.1 : la concentration de sources DIFFÉRENTES
- **Notée le** : 2026-09-14
- **Destination** : mandat du chantier 22 *(22.1)*. **Le premier des deux motifs SE FAIT.**
- **Condition** : *N signaux d'au moins M sources distinctes dans une fenêtre de P jours.* **Les
  trois valeurs reviennent à Alexandre.**
- ⚠️ **Et la condition doit exiger que les signaux CONVERGENT vers une même sphère** — *sinon on
  signale l'agitation, pas le besoin.*
- ⚠️ **Le revers, pris en connaissance de cause et à écrire AVEC le motif** : *une entreprise bien
  couverte paraîtra plus active qu'une entreprise mal couverte.* **Exiger des sources DISTINCTES
  neutralise en partie le biais** — en partie seulement.

### N33 — Le silence après un pic : on n'y touche pas, et le motif de l'abstention
- **Notée le** : 2026-09-14
- **Destination** : mandat du chantier 22, avec le motif écrit.
- **Le calibrer maintenant confondrait une entreprise qui se tait et une source qui a cessé de
  livrer.**
- **C'est le motif le plus dangereux du catalogue : il affirme quelque chose de faux SANS JAMAIS SE
  CONTREDIRE.** *Une lecture qui ne peut pas être démentie par les faits n'a pas de garde-fou.*
- **Sa condition de levée** : que **la santé de source soit branchée sur les lectures**.

### N34 — Le même dossier revient — conséquence jamais tirée
- **Notée le** : 2026-09-14
- **Destination** : registre *(à trancher)*, et **touche le chantier 23**.
- **Conséquence de la durée de pertinence PAR COUPLE** : *si un signal est frais pour une sphère et
  périmé pour une autre au même instant, **le dossier est déjà destiné à revenir**.*
- **À trancher** : seconde notification, ou mise à jour du dossier existant?
- **Une exigence qui lève le revers, quelle que soit l'issue** : **une seconde notification doit
  dire qu'elle est la suite.**

### N35 — L'amorce de premier contact : un brouillon, jamais un message prêt
- **Notée le** : 2026-09-14
- **Destination** : spéc. *(palier Radar)* et mandat du chantier 21.
- **Décision d'Alexandre** : présentée comme **un brouillon à modifier**, jamais comme un message
  prêt à envoyer.
- **La raison, et elle est du côté du risque** : *un message rédigé par le produit **engage
  l'utilisateur en son nom**, et une amorce maladroite lui coûte le prospect — **sans que le
  produit le sache jamais**.* **Le brouillon déplace la responsabilité là où elle doit être.**
- **Ce n'est pas une section du portrait** — *c'est un geste, pas une lecture.*
- ⚠️ **Et elle est DÉJÀ promise au palier Radar** : c'est donc une contrainte à poser sur quelque
  chose de vendu, pas sur une idée.

### N36 — Le portrait visuel — pour le 21
- **Notée le** : 2026-09-14
- **Destination** : mandat du chantier 21.
- **Rendre le PREMIER bloc visuel** : des pictogrammes avec leur chiffre — *effectif,
  établissements, capacité, montant.*
- **La règle qui le gouverne est celle du produit : on affirme des faits.** Un visuel **n'affiche
  qu'un champ que le produit POSSÈDE, avec sa source et sa date**.
- **Une fourchette est un fait quand elle vient d'une source** — *« 26 à 49 » du REQ, un seuil
  OQLF, une capacité RACJ, un montant.* **Elle n'en est pas un quand le produit la calcule.**
- **Quand la donnée manque, l'icône ne s'affiche pas.** *Pas de point d'interrogation, pas de « non
  disponible » — rien.* **Remplir l'espace avec du vide affirme qu'on a cherché.**
- ⚠️ **Un visuel ne peut pas être au conditionnel** — *c'est ce qui en fait la bonne forme pour le
  premier bloc, et ce qui l'EXCLUT du second.*
- **Et la vérification du 14 septembre change ce paragraphe** : avec la bande d'effectifs du REQ,
  **le visuel ne serait plus pauvre**. *Première fois qu'une vérification AJOUTE au produit au lieu
  d'en retirer.*

### N37 — Les profils : le défaut est corrigé, la décision reste ouverte
- **Notée le** : 2026-09-14
- **Destination** : registre *(la décision)*, et journal des cas si la forme mérite un cas.
- **Corrigé dans le code le 14 septembre** *(demande de fusion nº 39)* : un profil sans besoin
  déclaré **se signale** — bruyamment à la création et à l'inventaire *(le geste humain)*, et **par
  une ligne d'exploitation `PROFIL_INCOMPLET` au cycle** *(le mécanisme automatique, qui saute sans
  s'arrêter mais ne se tait plus)*. **La règle vit au modèle, lue par les trois appelants.**
- ✏️ **Précision d'Alexandre le 14 septembre — le correctif couvre le chemin ADMINISTRATIF, et
  ce n'était pas de lui qu'il parlait.** *`profile create` puis `add-need` : là, le profil vide est
  nécessaire, le correctif tient, et le silence devait y être nommé de toute façon.* **Mais le jour
  où un utilisateur s'inscrit LUI-MÊME, il remplit un formulaire, pas deux commandes** — et là, les
  **champs obligatoires empêchent l'enregistrement** : *pas de sauvegarde sans au moins un besoin
  déclaré.* **Le profil incomplet n'existe jamais.**
- ⚠️ **Destination de cette moitié-là : le chantier 25, le premier jour d'un abonné.** *C'est là que
  le formulaire se conçoit, et **la contrainte doit être écrite avant que quelqu'un construise
  l'interface** — après, elle coûterait une migration de profils déjà entrés.*
- **Ce qui reste ouvert, et c'est la vraie question** : **ce qu'un profil peut DÉCLARER.**
  `TypeProfil` ne connaît que `fournisseur`, `client`, `les_deux` — *et « client » reste
  commercial.* **Une MRC, une chambre de commerce, un chercheur d'emploi n'y entrent pas.**
  *`ProfileNeed.type_besoin` admet déjà autre chose qu'« offre » : l'axe existe, le moteur ne
  l'implémente pas.*

### N38 — Une suite doit être consultable avec ce qu'elle prolonge
- **Notée le** : 2026-09-14
- **Destination** : **mandat du chantier 23**, là où la livraison se conçoit — pas au 21.
- **Constat de simulation** : *le portrait de suite est **plus court** que le premier, et c'est
  normal — il ne redit pas ce qui est connu.* **Mais ça veut dire qu'il n'est lisible qu'AVEC le
  premier.**
- **Un utilisateur qui aurait supprimé la notification de septembre recevrait un texte incomplet.**
  *Ce n'est pas un défaut du portrait : c'est une exigence sur la LIVRAISON.*
- **Et elle rejoint l'exigence déjà notée en N34** : une seconde notification doit dire qu'elle est
  la suite — **et maintenant, la rendre atteignable.**

### N39 — La mémoire est une section à part, et elle porte une contrainte que les autres n'ont pas
- **Notée le** : 2026-09-14
- **Destination** : **charte section 9, DANS la stratégie du portrait** — *jugement rendu le
  14 septembre : ça mérite d'être écrit, et à l'intérieur de la couche « lectures », pas à côté.*
- **La structure qui est apparue en simulation** : *ce qu'un fait dit seul · ce que le dossier dit ·
  ce que le croisement dit.*
- **La distinction est réelle, pas cosmétique, et voici ce qui la rend structurelle : une lecture
  qui consomme l'HISTORIQUE est bornée par « depuis quand on regarde ». Une lecture qui consomme un
  FAIT ne l'est pas.** *Donc les deux ne sont pas soumises aux mêmes conditions de véracité — ce
  n'est pas une question de présentation, c'est une question de ce qu'une lecture a le droit
  d'affirmer.*
- **Pourquoi dans la couche « lectures » et non comme une quatrième couche** : les trois couches
  disent *d'où vient* ce qui est dit — fait, lecture, assemblage. Celle-ci dit **ce qu'une lecture
  consomme**, donc elle découpe la deuxième couche plutôt que de s'ajouter aux trois. *Y ajouter un
  étage ferait croire que la mémoire vient après l'assemblage, alors qu'elle le précède.*
- **Elle porte la même borne que le portrait de tendance** *(N28)* : **« inchangée depuis qu'on
  regarde » n'est pas « inchangée depuis 2011 ».** *Une seule contrainte, deux endroits où elle
  s'applique — à écrire une fois, citée deux fois.*

### N40 — Ce que les huitième et neuvième simulations confirment
- **Notée le** : 2026-09-14
- **Destination** : registre *(la bande d'effectifs, N5)* et mandat du chantier 22 *(les motifs)*.
- **La DISPROPORTION est calculable pour la première fois** — *un contrat de 1,8 M$ pour une
  entreprise déclarée à 26-49 employés.* **Cette lecture n'existait dans aucune simulation
  antérieure : c'est la bande du REQ qui l'ouvre.** *Confirmation par l'usage de ce que la
  vérification du 14 septembre a trouvé.*
- **Le motif de concentration porte une lecture que rien d'autre ne porte** — *quatre signaux,
  trois sources distinctes, quarante-cinq jours, convergents vers la capacité opérationnelle.*
  ⚠️ **Et la condition de convergence A SERVI : sans elle, c'était de l'agitation.** *La garde
  posée avec le motif n'était donc pas une précaution théorique.*
- **Le retour du dossier fonctionne, et sa forme tient** : *suite du 4 septembre, puis ce qui a
  changé depuis.* **Le franchissement de bande D → E affiché avec ses deux valeurs** — *un
  franchissement est un fait, pas une interprétation, parce que les deux bornes viennent de la
  source.*
- **Et le motif d'absence a été écarté par le jugement, comme décidé** — *aucun nouveau contrat
  depuis septembre peut être un ralentissement ou rien.* **La première question du jugement a fait
  son travail sur un cas réel.**

### N41 — Le relevé du matin est le préalable du 12, et il n'est pas assez PROFOND
- **Notée le** : 2026-09-14
- **Destination** : mandat du chantier 12 *(livrable 1 — « l'inventaire de champs par source active,
  approuvé mais jamais livré »)*, et audit.
- ⚠️ **Le manque n'est pas six sources, c'est une profondeur.** *Le relevé du 13 septembre a
  inventorié ce que chaque source **PROMEUT AU DOSSIER** — le second rôle. Le 12 a besoin de ce que
  chaque source **CAPTE**, `champs` compris.* **Sur le SEAO, les deux ensembles ne se recoupent
  presque pas** : promu au dossier = **rien**; capté = **quinze clés**.
- **Et c'est précisément là que vit la démonstration de l'audit** : *l'assurance est déclarée sans
  source alors que **six champs déjà captés portent son déclencheur**.* **Ces six-là sont dans
  `champs`, pas dans ce qui atteint le dossier** — donc invisibles au relevé du 13.
- **Il faut donc refaire les huit en profondeur, pas compléter six en surface.**

### N42 — L'inventaire du 12 doit être GÉNÉRÉ, et porter deux colonnes
- **Notée le** : 2026-09-14
- **Destination** : mandat du chantier 12, livrable 1 — **la forme du livrable, pas seulement son
  contenu**.
- **Généré depuis le code, jamais écrit à la main** : *un connecteur a changé aujourd'hui même; une
  liste de champs recopiée serait fausse au premier commit suivant.* **C'est la règle du corpus
  contre les copies, appliquée à un inventaire.**
- ⚠️ **Deux colonnes, et la seconde est celle que la journée a payée pour apprendre** : *(a)* **ce
  que le code DÉCLARE capter**, *(b)* **le taux de remplissage RÉEL**. **Un inventaire tiré du code
  seul aurait listé `description_tender` comme un champ disponible pour la règle d'assurance — et
  il était vide dans 100 % des cas.** *Un champ déclaré n'est pas un champ rempli, et le 12
  construirait ses liens sur du vide sans s'en apercevoir.*
- **Et ça rend le livrable 4 du 12 possible** *(normaliser le texte libre déjà capté)* : la
  normalisation a besoin de savoir **quels champs sont du texte libre et combien de valeurs
  distinctes ils portent** — deux choses que seule la mesure donne.

### N43 — Le 12 remonte, mais c'est son PRÉALABLE qui remonte, pas le chantier
- **Notée le** : 2026-09-14
- **Destination** : audit, Partie 0 *(l'ordre par coût d'attente)* — **avis rendu, décision
  d'Alexandre**.
- **Pour le préalable, tout de suite** : *(1)* l'audit dit que le 12 **« peut se mener en parallèle
  du socle — le seul chantier qui peut avancer pendant que le reste se répare »**; *(2)* son
  préalable est **à moitié fait**; *(3)* il **sert déjà un autre point du plan** — la correspondance
  code → sphère du SEAO, qui attend la même matière; *(4)* il **ne dépend pas de l'appariement**,
  donc il n'est pas derrière le verrou.
- ⚠️ **Contre, pour le RESTE du 12, et c'est le corpus qui le dit** : le livrable 5 — *la règle de
  réfutation, « la partie non négociable »* — exige que **chaque lien se teste contre l'historique
  réel**, et l'audit précise que c'est le **chantier 13** qui rend ce garde-fou *« opérationnel
  plutôt que théorique »*, par le taux de rejet. **Or le taux de rejet demande des utilisateurs qui
  rejettent**, et les cycles récents produisent zéro notification. *Sans lui, le 12 propose des liens
  et n'a rien pour les réfuter — exactement ce que sa propre règle interdit.*
- **Donc : remonter le livrable 1, laisser les livrables 2, 3 et 5 où ils sont.** *Ce qui remonte est
  ce qui ne dépend de rien; ce qui attend est ce qui a besoin d'usage réel.*
- **Et la réserve du mandat vaut d'être reprise au moment de trancher** : *le 12 ne créera pas de
  signal là où il n'y en a pas — il révèle des signaux captés mais mal attribués.*

### N44 — Le générateur d'inventaire est livré, et ce qu'il apprend déjà
- **Notée le** : 2026-09-14
- **Destination** : mandat du chantier 12 *(livrable 1 — le marquer LIVRÉ, avec sa forme)*.
- **`outils/inventaire_champs.py`** : les sources actives sont lues **au registre**, les champs
  **dans l'arbre syntaxique** du connecteur, le remplissage **en base**. *Sept connecteurs, une
  quarantaine de champs déclarés.*
- **Ce que l'arbre évite, et ce n'est pas théorique** : une expression régulière sur `"clé":`
  attrapait les dictionnaires VOISINS — `colonnes`, `exemple`, `taille_decompressee_octets` de
  l'inspection de zip du REQ — **et le 12 aurait cru disposer d'une matière qui n'existe pas.**
  *Elle manquait aussi un champ réel d'`investissement_quebec`.* **Un test le verrouille.**
- **Trois écarts nommés par la sortie**, et chacun veut dire autre chose : *déclaré jamais rempli*
  **(le connecteur écrit une clé que la source ne porte pas)**, *rempli non déclaré* **(une
  expansion `**` ou un chemin oublié)**, *déclaré non ingéré* **(absence de mesure, pas champ
  mort)*.
- ⚠️ **Le REQ porte des clés DYNAMIQUES** *(`**etab`, `**chgt`)* : **sa liste déclarée est
  incomplète par nature**, l'outil le signale plutôt que de rendre une liste qu'on croirait
  complète. *C'est la source la plus riche, et c'est celle dont le code dit le moins.*
- **Et l'outil n'attribue AUCUNE sphère** — le diagnostic à rebours est le livrable 2, il exige la
  réfutation du livrable 5, opérationnelle seulement avec le 13. *Proposer un lien ici produirait
  exactement ce que la règle de réfutation existe pour empêcher.*
