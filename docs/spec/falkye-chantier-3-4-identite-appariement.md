# FALKYE — Chantiers 3 et 4 : identité d'entreprise et confiance d'appariement

> Ouvert le 16 septembre 2026. Document créé le 17 septembre, à mi-chantier — le chantier travaillait depuis deux jours sans document, contrairement à l'usage du corpus. **Ce qui suit est daté et sourcé : chaque fait porte la mesure qui l'a produit.**
>
> Arbitrage : `charte-falkye.md` tranche, puis `falkye-audit-et-mandat.md`, puis ce document.
>
> ⚠️ **Le chantier est EN COURS.** Aucun livrable des chantiers 3 et 4 n'est construit. Ce document porte le **constat de phase 0** — la campagne de mesure du 14 au 17 septembre — et le mandat qu'elle doit servir. *Les mesures encore en vol sont nommées à la section 17, pas anticipées ailleurs.*

---

## 1. Le mandat, et ce qu'il commande

Le mandat vit dans `falkye-audit-et-mandat.md`, section « Chantiers 3 et 4 ». Les deux sont inséparables : **séparer l'identité de la confiance ferait migrer deux fois la même clé.**

**Chantier 3 — l'identité.** Une identité interne distincte de tout identifiant externe. Une table d'identifiants externes rattachés, chacun avec son territoire, sa source et sa date — zéro, un ou plusieurs. **Une identité sans identifiant externe est valide de plein droit, pas un cas dégradé.** Un niveau de vérification par couple identité × territoire.

**Chantier 4 — la confiance d'appariement.** Un score hérité du maillon le plus faible de l'historique de fusion, qui **plafonne** au lieu de s'additionner. **L'adresse comme axe principal, le nom en corroborateur** — pas l'inverse. Une table d'apprentissage raison sociale ↔ nom d'enseigne ↔ adresse. Une règle de non-promotion sous un seuil.

**La seconde dimension, à prévoir dès la conception.** La famille d'entité (publique / privée) s'ajoute **à côté du territoire**, pas à sa place. Le motif est chiffré au mandat : sur le SEAO, l'identifiant de l'organisme acheteur est présent à 100 %, celui du fournisseur n'est jamais un NEQ — 56 % d'ambiguïté sur les entreprises, zéro sur les organismes publics. *Le faire maintenant coûte presque rien; le faire après, c'est migrer deux fois la même clé.*

**Deux questions de désaccord, non répondues.** Deux identifiants contradictoires : l'exclusion porte-t-elle sur toute l'identité ou seulement le territoire? Deux appariements concurrents à score comparable : **le défaut ne doit jamais être « prendre le meilleur score ».**

**Critère d'acceptation.** Ajouter un identifiant d'un territoire fictif ne doit toucher aucune ligne du moteur de croisement. Test de non-régression sur les entreprises québécoises.

### Décisions ouvertes qui bloquent la conception de la clé

| | | état |
|---|---|---|
| **D27** | trouver un registre officiel des entités publiques québécoises | ⬜ |
| **D28** | la règle de classement public / privé, avec sa réponse par défaut | ⬜ |
| **D29** | lequel des deux identifiants fait foi quand une entité porte les deux | ⬜ |
| **D43** | les donneurs d'ouvrage du SEAO n'existent comme entité nulle part | ⬜ |

**Aucune n'est tranchée.** La mesure et le chiffrage tiennent sans elles; la structure définitive, non.

---

## 2. Portée — ce qui est dans le chantier et ce qui n'y est pas

**Dans le chantier :** l'identité interne et sa clé, la table d'identifiants externes avec territoire et famille, le niveau de vérification par couple identité × territoire, le score d'appariement plafonnant, la table d'apprentissage raison sociale ↔ enseigne ↔ adresse, la règle de non-promotion, et la **passe de reprise** — seul mécanisme qui répare un dossier existant *(section 6)*.

**Hors du chantier, à ne pas commencer :** le dédoublonnage existant `falkye/dedup_entreprises.py`, qui reste un rattrapage manuel en mode opérateur *(décision du 16 septembre, section 4)*; le tableau de bord de santé de source *(chantier 2)*; la cadence de notification *(chantier 8)*; la vérification elle-même — statut légal, signe d'activité, cohérence — qui est le mur d'après *(section 18)*.

**Hors du chantier et souvent confondu avec lui :** les deux échelles du moteur — seuil de confiance **92**, écart minimal **8**. Elles ne sont pas des livrables du chantier. *Elles se changent avec Alexandre, jamais dans une demande de mesure.*

**Ce qui borne le chantier par le haut.** *Le chantier récupère des identités; il ne dit pas ce qu'elles valent.* Si une frontière devient gênante en cours de route, **la signaler plutôt que la franchir**.

---

## 3. Préalables — ce qui doit exister avant de concevoir

**Bloquants pour la clé.** **D27**, **D28**, **D29** *(section 1)*. *Concevoir la clé avant elles, c'est la concevoir deux fois.*

**Bloquant pour tout gain mesuré.** La **passe de reprise**. Une résolution réussie n'écrit jamais dans le dossier qui a échoué *(section 6)* — **donc un gain simulé ne devient pas un dossier résolu en production sans elle.** *Elle existe en lecture seule (`outils/reresolution_neq.py`); son application sur les 705 posables n'est pas décidée.*

**Bloquant pour la piste de la ville.** La promotion de la ville depuis `Signal.champs` vers le dossier *(section 9)*. **Du code, pas une échelle.** Non décidée au 17 septembre.

**Préalable de méthode, appris dans ce chantier.** *Avant de demander pourquoi une comparaison échoue, vérifier que les deux termes existent.* **Sept hypothèses sont tombées faute de ce préalable** *(section 11)*, et le préalable de l'adresse a évité la huitième *(section 9)*.

---

## 4. Les décisions d'Alexandre

**16 septembre — un dossier peut porter plusieurs noms.**
Conservation toujours, **aucune fusion**. Le dossier le plus ancien porte le NEQ. Aucun nom ne se perd.

*Portée précisée le 16 :* la décision dit que la solution retenue pour les dossiers sans NEQ n'est pas la fusion. **Elle ne touche pas au dédoublonnage existant** (`falkye/dedup_entreprises.py`), rattrapage manuel en mode opérateur, jamais greffé sur le cycle.

⚠️ *Cette décision, seule, ne récupère aucun NEQ.* Conserver un nom et l'utiliser pour chercher sont deux gestes différents — l'élargissement des points de recherche a été retiré au titre du cas 34, il demande sa propre démonstration chiffrée.

**16 septembre — mesurer avant de construire.**
Rien ne se construit tant que la mesure n'a pas dit ce qui est récupérable. Motif : *8 931 entreprises sans identité, ce n'est pas un produit imparfait — c'est un produit qui ne peut pas performer, seulement fonctionner à titre d'anecdote.*

**16 septembre — le rang des mesures.** NOM_ETAB premier; l'adresse seconde **pour son préalable, pas pour son rang** — elle reste l'axe principal du mandat.

**17 septembre — la garde des prétendants multiples.**
Formulation retenue : **le nombre de prétendants est une preuve contre l'appariement, et d'une autre nature que le score.** Monter le seuil n'y ferait rien, ces scores sont à 100. Refus posé au-delà de deux prétendants.

**19 septembre — n'écrire que le CODE POSTAL COMPLET.**
*Le départageur d'adresse mesure ses trois niveaux; seul le plus fin ÉCRIT.* **268 départages laissés EN SUSPENS — 188 par région de tri, 80 par ville.** ⚠️ *La restriction porte sur l'ÉCRITURE, pas sur le départageur.*

> **Un départage non écrit se reprend; un départage écrit à tort coûte une identité.**

**19 septembre — les noms génériques attendent le chantier 22.** *La route par code d'activité demande la table `(code, rôle) → sphère`, qui sert deux usages et se fait une fois pour deux.*

**20 et 21 septembre — le BASSIN DE PRATIQUE, et c'est le principe qui gouverne tout le reste.**

> *« Notre bassin actuel est un bassin de pratique. Chaque façon d'ajouter des NEQ qu'on valide ici devra servir sur les prochains fichiers zip du REQ, par la résolution qui roule à chaque import. »*

**Ce que ça change dans le jugement d'une hypothèse** : la question n'est plus *« écrit-on ces dossiers aujourd'hui »*, mais **« la règle peut-elle tourner seule, à chaque import, sans que personne relise les paires »**. ⚠️ *Un outil ponctuel se relit; une règle permanente, non.*

**Et deux conséquences d'ordre** : **aucun import tant que le bloc n'est pas complet** *(section 17bis)*, et **le test ultime est l'import d'un autre zip** — pour voir comment les règles se comportent sur des données que personne n'a lues.

**21 septembre — ne pas élargir le statut tout de suite.** *D'abord mesurer ce que valent les 81 contradictions de l'adresse, et vérifier d'où vient le statut.* **Les deux ont été faits** *(section « Le statut comme départageur »)*.

**21 septembre — la justesse des NEQ posés doit se mesurer.** *« Il faut évidemment s'assurer que les NEQ soient associés à leurs bonnes entreprises. »* **Un NEQ posé sur la mauvaise entreprise est PIRE qu'un dossier sans NEQ** : il produit un faux prospect, et rien ne le signale *(section 13, et registre)*.

**23 septembre — les noms retirés, consultés en dernier.** *Registre **D52**, et construit dans `resolve_neq_by_name`.*

**Les deux échelles ne bougent pas** : seuil de confiance **92**, écart minimal au second **8**. Elles se changent avec Alexandre, jamais dans une demande de mesure.

---

## 5. Phase 0 — l'état mesuré AU 16-17 SEPTEMBRE

> ⚠️ **Cette section est datée, et la population a bougé depuis.** *Les 8 931 sans NEQ de la phase 0 sont devenus **4 673** le 19 septembre, puis **3 608** le 20* — voir « Ce qui est posé en base » et « Le portrait des restants ». **Les chiffres ci-dessous restent le point de départ; ils ne sont plus l'état courant.**

**La population, inchangée depuis le 16 et confirmée par rejeu complet le 16 septembre :**

| famille | dossiers | part |
|---|---|---|
| RETENU | 805 | 9,0 % |
| ambigu | 3 244 | 36,3 % |
| trop faible | 4 733 | 53,0 % |
| aucun candidat | 149 | 1,7 % |
| **total sans NEQ** | **8 931** | |

*Le rejeu du 16 a établi que redemander aujourd'hui ne change pas un seul dossier : la ventilation est identique, chiffre pour chiffre.*

**Sur les 805 retenus** : 773 NEQ distincts visés, 32 dossiers en trop. 705 posables par la passe, 69 NEQ déjà portés, 31 contestés dans le lot.

---

## 5bis. Ce qui est POSÉ EN BASE — les trois écritures

> **Mesuré et écrit du 19 au 20 septembre 2026.** *Chaque écriture porte son instantané et sa commande pour défaire.*

**8 931 → 3 608 dossiers sans NEQ. 5 323 identifiés, soit 59,6 %.**

| écriture | NEQ posés | instantané |
|---|---|---|
| passe de reprise *(`reresolution_neq --appliquer`)* | **2 523** | `/var/lib/falkye/reresolution-20260919T162941.json` |
| départage par l'adresse, **code postal complet seulement** *(`ecriture_des_departages --appliquer`)* | **1 735** | `/var/lib/falkye/departages-20260919T185650.json` |
| exclusion des radiées sur les **égalités strictes** *(`ecriture_du_statut --appliquer`)* | **1 065** | `/var/lib/falkye/statut-20260921T040739.json` |

**La règle de conservation a tenu jusqu'au bout.** *108 + 28 rapprochements journalisés, **aucune fusion**. 111 puis 29 NEQ « déjà pris » conservés sans être posés.* ⚠️ **Un NEQ refusé en bloc — `8879690699`, 17 prétendants, les organisations publiques** : *le nombre de prétendants est une preuve contre l'appariement, et d'une autre nature que le score* **(§4, 17 septembre)**.

⚠️ **Les restants SOUS le sommet restent en suspens** — 78 le 20 septembre. *Deux instruments s'y contredisent, et rien ne dit lequel a raison.*

⚠️ **Ce sont trois OUTILS PONCTUELS, pas des étapes de la résolution.** *Aucun ne s'appliquerait au prochain zip* — c'est l'étape 10 du bloc de l'import *(section 17bis)*.

### ⚠️ Ce que ces 5 323 doivent à une porte ouverte le 17 septembre

**Les trois écritures sont postérieures au retrait du filtre `STAT_NOM='V'`** *(17 septembre, commit `a362d35`)*. **Mesuré le 22 septembre** *(`outils/noms_perimes_en_production.py`)* :

| | dossiers | part |
|---|---|---|
| trouvés par un **nom retiré** | **208** | **2,4 %** |
| … dont **leur PROPRE ancien nom** *(aucun autre NEQ ne le porte)* | 157 | 75,5 % |
| … dont ⚠️ **un nom qu'une AUTRE entreprise porte aujourd'hui** | **51** | 24,5 % |

⚠️ **« Plus en vigueur » n'est pas « faux ».** *Un nom abandonné mène souvent à la bonne entreprise — un signal antérieur au changement de nom, une source qui recopie l'inscription d'origine.* **Le compte dit l'EXPOSITION, jamais l'erreur.**

**Ce qui a été fait de ce chiffre** : la règle du **troisième temps**, tranchée le 23 septembre *(registre **D52**)* — les noms retirés ne sont consultés que si aucun nom en vigueur n'a trouvé l'entreprise. ⚠️ *Elle ne réécrit rien toute seule : les 5 323 gardent leur NEQ tant qu'une reprise ne les rouvre pas (étape 14).*

⚠️ **Et 14 dossiers posés ne sont plus retrouvés par le rejeu d'aujourd'hui.** *Deux causes, qui n'appellent pas la même suite* : **le lot a grandi et le NEQ est passé sous la coupe à cinq**, ou **la porte a disparu**. *La première est la dérive annoncée de l'étape 7 — `req_noms` n'oublie rien.*

---

## 5ter. Le portrait des restants — le mur a changé de nature

> **Mesuré le 19 septembre 2026** *(`outils/portrait_des_restants.py`)*, sur les **4 673** restants d'alors.

**Le mur n'est plus un problème d'appariement : c'est un problème de DÉPARTAGE.**

| famille | dossiers | part | ce qui échoue |
|---|---|---|---|
| **ambigu** | **3 267** | 69,9 % | **l'ÉCART** au second |
| trop faible | 1 257 | 26,9 % | le SEUIL |
| RETENU | 111 | 2,4 % | *voir §13bis — une impasse* |
| aucun candidat | 38 | 0,8 % | — |

**72,3 % des restants ont un candidat au-dessus du seuil et restent bloqués par l'écart.** *Ils ont trouvé leur entreprise; ils ne savent pas laquelle des trois c'est.*

⚠️ **`ambigu` et `trop faible` n'appellent pas le même correctif.** *Les confondre fait attribuer au seuil une masse que l'écart retient.*

⚠️ **« Aucun candidat » n'est pas un score de zéro.** *Un dossier à zéro candidat et un dossier à 91 ne sont pas le même problème — le premier n'a rien à départager, le second a tout sauf deux points.*

⚠️ **Les 810 dossiers entre 90 et 91,9 sont un fait, pas une invitation.** *Le seuil de 92 et l'écart de 8 ne se rouvrent qu'en dernier recours.*

### L'adresse ne MANQUE pas : elle ne SÉPARE pas

| finesse d'adresse | restants | résolus | rapport |
|---|---|---|---|
| code postal complet | 70,5 % | 99,6 % | ×0,7 |
| région de tri seule | 5,6 % | 0,1 % | ×86 |
| ville seule | 9,6 % | 0,3 % | ×32 |
| rien | 14,3 % | 0,0 % | ×548 |

**70,5 % des restants portent un code complet et sont ambigus quand même.** *L'EIMT en porte à 100 % et ne départage qu'un ambigu sur dix — les concurrents sont au même endroit.* **Il faut un fait d'une AUTRE NATURE, pas une adresse plus fine.**

### Deux familles d'échec, pas une

| source | restants | ambigu | trop faible |
|---|---|---|---|
| eimt | 3 053 | 79,9 % | 18,4 % |
| investissement_quebec | 438 | 77,6 % | 13,7 % |
| seao | 637 | 68,3 % | 28,6 % |
| rob_top_growing | 329 | 14,9 % | **76,9 %** |
| contrats_federaux | 191 | 19,4 % | **79,6 %** |
| deloitte_fast50 | 64 | 15,6 % | **70,3 %** |

**Les classements et les contrats fédéraux échouent sur le NOM; les sources québécoises sur l'ÉCART.** *584 dossiers dans le premier cas.* ⚠️ **Un dossier cumule ses signaux** : il compte dans chaque source qui l'a vu, et **les lignes ne s'additionnent pas**.

### Le nom court, second discriminant — et personne ne l'avait regardé

| longueur du nom | restants | résolus | rapport |
|---|---|---|---|
| **1 mot** | 5,1 % | 1,5 % | **×3,4** |
| 2 mots | 14,8 % | 10,0 % | ×1,5 |
| 3 mots et plus | 80,1 % | 88,6 % | ×0,9 |

**C'est la théorie des noms génériques, mesurée pour la première fois.** *Les autres formes ne distinguent rien — tête numérique ×1,0, parenthèse ×1,2, conjonction ×1,1.* ⚠️ **Et la CAUSE du ×3,4 est dans notre code** : `candidats_par_mot_rare` exige un deuxième mot, qu'un nom d'un mot n'a pas *(section « Défauts du code de résolution »)*.

⚠️ *« Porte une conjonction » (7,8 %) est le fait brut du caractère, pas la règle stricte des consortiums (1,1 %) : **les deux chiffres ne sont pas comparables**.*

### Un croisement isole une famille distincte

| forme et adresse | dossiers | ambigu | trop faible |
|---|---|---|---|
| **lettres · sans code postal** | **974** | 34,7 % | **57,3 %** |
| lettres · avec code postal | 3 035 | 79,7 % | 18,1 % |
| tête numérique · avec code postal | 522 | 74,3 % | 25,5 % |
| tête numérique · sans code postal | 142 | 86,6 % | 12,7 % |

**C'est le seul groupe qui échoue majoritairement sur le NOM, et il se repère par l'ABSENCE d'adresse.**

### Deux axes jamais regardés, et ils distinguent peu

*Le nombre de signaux et de sources est le même chez les restants et les résolus (×1,0)* — **sauf les dossiers à six signaux et plus (×1,5) et ceux vus par deux sources (×1,4), sur de petits effectifs.** *34 % des restants ont un signal de plus d'un an — les résolus aussi (34,9 %) : **l'âge ne distingue pas**.* ⚠️ **Mais les signaux de 30 jours ou moins sont ×1,6 chez les restants** : *un dossier récent se résout MOINS bien, et c'est l'inverse de ce qu'on aurait supposé.*

⚠️ **Trois réserves de lecture, portées par l'outil lui-même.** *`detected_at` est la date de l'ÉVÉNEMENT source, `ingested_at` celle de notre collecte — lire la seconde mesurerait nos cycles.* **Une date ancienne ne dit pas une entreprise dormante** — une source qui publie un jeu de données daté rend des dates anciennes. *Et un compte arrêté à la borne de 2 000 est **tronqué, pas mesuré**.*

---

## 6. Le défaut de fond — la résolution ne répare pas

**Établi le 16 septembre par lecture du code** (`falkye/resolution.py::resolve_company`) :

```
company = SELECT Company WHERE neq = <retenu>
if company is None: company = Company(neq=…)   # ← un NOUVEAU dossier
```

**Une résolution réussie n'écrit jamais dans le dossier qui a échoué.** Elle cherche un dossier clé par NEQ et en crée un si aucun n'existe.

**Deux conséquences.** Un dossier non résolu ne guérit jamais, puisque rien ne le réexamine. Et **même en réexaminant, la réponse s'écrirait ailleurs** — c'est pourquoi la passe de reprise doit exister séparément, et pourquoi elle est le seul mécanisme qui répare un dossier existant.

**C'est ce défaut qui explique la série d'hypothèses tombées.** Toutes demandaient *pourquoi la comparaison échoue*. Aucune ne pouvait aboutir : la comparaison réussie n'écrit pas là où l'échec est inscrit.

**Corollaire pour toute mesure simulée** : un gain simulé ne devient pas un dossier résolu en production sans la passe de reprise.

---

## 7. Le second défaut — la borne de récupération

**Mesuré le 17 septembre** (`outils/saturation_de_la_borne.py`).

La récupération extrait un préfixe — `prefix = nom_norm.split(" ")[0]`, **le premier mot, rien d'autre** — et rend au plus `LIMITE_CANDIDATS_PAR_NOM` candidats, **2 000** au 17 septembre *(`falkye/sources/req.py`)*.

| | lots coupés | part |
|---|---|---|
| RETENU (805) | 209 | 26,0 % |
| ambigu (3 244) | 490 | 15,1 % |
| **trop faible (4 733)** | **3 518** | **74,3 %** |
| aucun candidat (149) | 0 | 0,0 % |
| **total (8 931)** | **4 217** | **47,2 %** |

| forme du préfixe | dossiers | coupés | part |
|---|---|---|---|
| numérique | 1 552 | 3 | 0,2 % |
| parlant | 7 379 | 4 214 | 57,1 % |

**La taille du gisement, sur les préfixes qui saturent :**

| préfixe | dossiers | lignes au registre | part vue |
|---|---|---|---|
| `ferme` | 1 244 | 23 061 | 8,7 % |
| `les` | 768 | 163 296 | 1,2 % |
| `le` | 143 | 205 071 | 1,0 % |
| `l` | 47 | 309 788 | 0,6 % |
| `gestion` | 115 | 105 845 | 1,9 % |

**Et l'ordre du tri décide de ce qu'on voit.** L'`ORDER BY` posé le 16 septembre a rendu le tirage **reproductible, pas meilleur**. L'ordre des caractères est :

```
" "  <  "0" … "9"  <  "a" … "z"
```

`normaliser` ayant déjà transformé `LES " 100 " AILE` en `les 100 aile`, **ces noms-là occupent bien la tête de la tranche.** *Le correctif de la reproductibilité a figé le tirage : il n'a rien cassé, il a rendu constant ce qui était aléatoire.*

**Lecture de dix paires du pic 85-88** (`outils/paires_du_pic.py`, 17 septembre) :

```
'Konstruct Digital'                    →  'Konstructo'
'Les Habitations KTP'                  →  'LES " 100 " AILE'
'Ferme Léger Parent inc.'              →  'FERME 100 MILES CENTRE ÉDUCATIONNEL'
'J.G. Rive-Sud Fruits & Légumes inc'   →  'J 2 B'
"L'INDUSTRIE MONDIALE DU NORD INC."    →  "L'0EIL A LA TOUCHE"
'La Perade Ford inc.'                  →  'La 115e'
```

**Aucun des dix n'est l'entreprise cherchée.** Sept sur dix sont en tête alphabétique de leur préfixe. Le score **85,50 revient huit fois sur dix** — c'est ce que `WRatio` rend quand seul le premier mot correspond, vérifié au banc.

**Des deux observations, une seule a survécu au recomptage.** *La valeur 85,50 est confirmée sur la population — section 7bis. La tête alphabétique, non — juste en dessous.*

### ⚠️ Et l'explication qu'on en avait tirée est DÉMENTIE — mesure A, 17 septembre

**Ce que ce document disait avant le recomptage** : *« la tranche commence par les chiffres et la ponctuation et n'atteint jamais les lettres. »* **C'est faux.**

```
lots coupés AVANT LA PREMIÈRE LETTRE : 17 sur 4 217   (0,4 %)

au point de coupe          lots     part
espace puis lettre        4 072    96,6 %
lettre collée               123     2,9 %
hors préfixe                 17     0,4 %
CHIFFRE collé                 5     0,1 %
espace puis CHIFFRE           0     0,0 %
```

**La coupe tombe au MILIEU de l'alphabet, pas avant les lettres.** Et dans la tranche entière, le non alphabétique après le préfixe pèse **776 568 candidats sur 6 342 752 — 12,2 %.** *Pas la majorité.*

> ⚠️ **La lecture des dix paires montrait un mécanisme RÉEL mais RARE.** *Sept sur dix en tête alphabétique était un artefact du tirage, pas une fréquence.* **Dix cas disent qu'une chose EXISTE; ils ne disent jamais COMBIEN DE FOIS.**

**Deux recoupements internes confirment que la mesure lit le bon objet.** Les 17 lots « avant la première lettre » sont **exactement** les 17 lots « hors préfixe » — les seuls où le préfixe n'a rien rendu et où le repli par sous-chaîne a servi. Et 6 342 752 candidats pour 4 217 lots font **1 504 par lot**, contre une tranche théorique de `2 000 − 2 000//4 = 1 500` : *la part réservée au pont est bien retirée de l'ordre alphabétique.*

**Ce qui reste vrai, et ne bouge pas** : la borne coupe **4 217** lots, **74,3 %** chez les trop faibles, `ferme` vu à **8,7 %**.

**Ce qui change, c'est la QUESTION.** Le bon candidat est-il **après** le point de coupe, ou **n'existe-t-il pas**? ⚠️ *C'est la mesure C, et elle n'a pas encore rendu.* **Rien n'est écrit ici sur la borne comme CAUSE avant qu'elle rende.**

⚠️ **Une coupe n'est pas une perte.** Un préfixe qui rend 51 000 lignes dont la bonne est douzième alphabétique sature **et** récupère. Le compte borne le risque; l'établir demande une vérité de terrain qui n'existe pas.

---

## 7bis. Le pic 85-88 est un PLANCHER DE CALCUL — mesuré sur la population

**Mesuré le 17 septembre** (`outils/recomptage_du_plancher.py`, mesure B), sur l'hôte, environnement chargé, cible distante, aucun repli.

```
valeur exacte    dossiers    part
85.50               2 419   89,2 %
85.71                  69    2,5 %
87.50                  41    1,5 %

dont [85 – 86[ : 2 505  (92,3 % du pic)
```

**La valeur dominante pèse 89,2 % du pic.** *Une distribution de RESSEMBLANCE ne se concentre pas sur une valeur; un PLANCHER de calcul, si.* **85,50 est ce que `WRatio` rend quand seul le premier mot correspond**, vérifié au banc.

```
mots en commun avec le meilleur candidat, sur les 2 505 du plancher
le PREMIER MOT seulement   2 107   84,1 %
deux mots                    302   12,1 %
AUCUN mot en commun            2    0,1 %
```

*Comparé à **toutes** les formes publiées du NEQ, en gardant le **meilleur** recouvrement — donc **84,1 %** est un plancher : même la forme la plus favorable du registre ne partage que le premier mot.*

> ⚠️ **Le pic de 2 713 est un plancher de calcul, et aucun réglage d'échelle ne le franchira.** *Ce sont des dossiers dont le candidat n'a rien à voir* — abaisser le seuil à 85 n'accepterait pas 2 713 appariements proches, il accepterait 2 713 noms qui partagent un mot et rien d'autre.

**Ce que 7bis ne dit pas** : *pourquoi* le bon candidat est absent du lot. Il peut être après le point de coupe, ou ne pas exister. **C'est la mesure C.**

---

## 8. Ce qui a été mesuré et fermé

| piste | rendement | date | état |
|---|---|---|---|
| NOM_ETAB (`Etablissements.csv`) | **5** sur 2 517 mesurées, toutes en forme `IND` | 16 sept | close |
| Parenthèses retirées des deux côtés | **+17 / −13**, plafond 205 dossiers | 17 sept | close |
| Seuil abaissé à 90 | **79** retenus de plus | 17 sept | close |
| Le pic 85-88 comme réserve d'appariements proches | **plancher de calcul** — 89,2 % à 85,50 *(section 7bis)* | 17 sept | close |
| Corporations Canada comme pont | **0** — sans objet | 16 sept | close |
| Rejeu complet de la résolution | **0** — ventilation identique | 16 sept | close |
| Index par mots + quatre gisements | **+1 854** retenus | 17 sept | ✅ déployé |
| Passe de reprise | **+2 523** posés | 19 sept | ✅ écrit |
| Départage par l'adresse, code complet | **+1 735** posés | 19 sept | ✅ écrit |
| Exclusion des radiées, égalités strictes | **+1 065** posés | 20 sept | ✅ écrit |
| Parenthèses, côté détecté seul | **16 gagnés, 1 perdu — 15 nets.** Non appliqué | 19 sept | close |
| Promotion de l'adresse *(seao, eimt)* | **+0** au départage | 19 sept | close |
| Le gisement de la forme gagnante comme garde-fou | **ne sépare pas** les bons des faux | 21 sept | close |

**NOM_ETAB.** Les 5 récupérations sont toutes des entreprises individuelles — des personnes physiques, que le Registraire ne publie pas. **Convergence** : `outils/profil_des_absents_req.py` avait établi que 96,6 % des 224 968 NEQ sans nom dans `Nom.csv` sont des personnes physiques. *Deux instruments indépendants, même mur.*

⚠️ **Réserve établie sur NOM_ETAB** : la ventilation par forme juridique porte sur les NEQ **retrouvés**, jamais sur les introuvables — on ne connaît la forme juridique que d'une entreprise déjà identifiée. **Il dit ce qui est réparable, jamais ce qui est hors de portée.** *La question « combien des 8 931 sont irrécupérables » reste sans instrument.*

**Le seuil n'est pas ce qui bloque.** 4 918 dossiers non retenus ont un meilleur score ≥ 90. À seuil 90 : **79 deviennent retenus (1,6 %), 4 839 basculent en ambigu (98,4 %)**. Ce n'est pas le seuil qui les retient — c'est l'écart.

**L'écart n'a aucun gain propre.**

| écart | NEQ visés par > 2 dossiers | dossiers dans ces groupes | 2e NEQ à moins de | gain |
|---|---|---|---|---|
| **8** (en vigueur) | 1 | 26 | 0 | **0** ← témoin |
| 6 | 1 | 26 | 138 | 138 |
| 4 | 2 | 29 | 2 097 | 2 097 |
| 2 | 3 | 32 | 2 207 | 2 207 |
| 0 | 5 | 38 | 3 244 | 3 244 |

**Le gain et la colonne « 2e NEQ à moins de » sont le même chiffre à chaque ligne.** Établi le 17 septembre que ce n'était **pas une mesure mais une identité** : tout dossier récupéré par un écart abaissé a par construction un second à moins de 8 points. Le contenu reste vrai, l'instrument ne valait rien (N95).

⚠️ **Conclusion qui tient** : chaque dossier qu'un écart abaissé récupère est un dossier où **la machine tranche entre deux entreprises différentes**. L'écart de 8 refuse exactement ce qu'il a été posé pour refuser.

---

## 9. La piste ouverte sans coût en faux — la ville

**Mesuré le 17 septembre** (`outils/departage_par_ville.py`).

**L'adresse ne peut pas apparier.** Sur les 8 931 dossiers à apparier, **0 porte une adresse** (`Company.adresse`). Le gisement existe pourtant : l'EIMT capte une adresse sur **14 105 signaux, soit 100 %**, jamais promue en `RawSignal.adresse`. Côté registre, 2 001 277 entrées sur 2 730 146 en portent une (73,3 %).

⚠️ **Et les deux formes ne se comparent pas** :

```
produit  : 'St-Isidore, QC J0L  2A'          → municipalité, province, code postal
registre : '200 rue des Commandeurs'          → numéro civique et rue
```

**Aucune normalisation ne les fera se rejoindre.** Ce qui se recouvre, c'est la **ville** — et le **code postal**, jamais regardé à ce jour.

**Mais l'adresse peut départager.**

| issue | dossiers |
|---|---|
| **DÉPARTAGÉ — un seul concurrent dans la ville du dossier** | **1 111** |
| aucune ville au dossier | 690 |
| villes différentes, aucune ne concorde | 612 |
| concurrents de même ville — la ville ne départage pas | 469 |
| villes différentes, plusieurs concordent | 354 |
| aucun concurrent n'a de ville au registre | 8 |

**1 111 sur 3 244 ambigus — 34,2 %.**

**Le gisement est bien celui qui n'a jamais été vu** : 2 484 dossiers ont une ville dans `Signal.champs` seulement, tous EIMT. Seuls 70 ont une `Company.ville` déjà connue du moteur — *et le moteur applique déjà +5 quand elle concorde, donc l'ambiguïté y a survécu au bonus.* **Mélanger les deux annoncerait comme gain ce qui est déjà appliqué.**

**La ville confirme, elle ne corrige presque jamais :**

| | dossiers | part |
|---|---|---|
| le gagnant par la ville était déjà seul mieux scoré | 963 | 86,7 % |
| le gagnant par la ville est **un autre** candidat | 45 | 4,1 % |
| **ex æquo au meilleur score — le score ne tranchait pas** | 103 | 9,3 % |

⚠️ **La troisième ligne n'est ni confirmation ni correction : là, la ville est la seule à avoir une opinion.** Exemples : deux `BÉTON BOLDUC INC.` à 100, l'un à Ste-Marie l'autre non; deux `CIMA+ S.E.N.C.` à 100, Sherbrooke et Laval.

**Lecture** : la ville ne corrige pas le score — **elle autorise à trancher ce que le score avait déjà tranché.** C'est un feu vert, pas une opinion nouvelle.

⚠️ **Réserves.** La ville du registre est sale (`ville='LOCAL RC27'`, `ville='BEAUCEVILLE, BEAUCE'`). Une ville qui concorde ne prouve pas l'identité — deux entreprises distinctes peuvent être dans la même ville. **Un départage écarte un candidat; il n'en confirme aucun.** Et 25 dossiers portent des villes qui se contredisent d'un signal à l'autre : *un dossier cumule les signaux, rien ne garantit qu'ils parlent du même établissement.*

**Le geste que ça demande** : promouvoir la ville de `Signal.champs` vers le dossier. **Du code, pas une échelle.** Non décidé au 17 septembre.

---

## 9bis. Le STATUT comme départageur — et ce que l'adresse en dit

> **Construit et écrit du 20 au 21 septembre 2026.** *`outils/statut_sur_les_egalites.py`, `outils/ecriture_du_statut.py`, `outils/valeur_des_contradictions.py`.*

**La forme retenue : n'écarter que les RADIÉES** *(codes `RD`, `RO`, `RX`)*. ⚠️ *Elle garde les 39 dossiers à candidat `ni` — les entités publiques — et l'autre forme ne rendait que 16 dossiers de plus.*

⚠️ **`ni` n'est pas « immatriculée ».** *`NI = Non immatriculée`, `AI = Avis d'intention de constitution`, confirmés dans `DomaineValeur.csv`.* **`falkye/resolution.py` les transforme pourtant en `IMMATRICULEE`** *(section « Défauts du code de résolution »)*.

### La portée, et les DEUX conditions qui la définissent

**Le 20 septembre — les égalités strictes.** *Au moins deux candidats au score du sommet; l'exclusion en laisse un seul; il est AU sommet.* **1 065 NEQ posés.**

⚠️ **La seconde condition n'est pas redondante avec la première, et c'est une correction de Claude Code, vérifiée en exécutant le code.** *Une égalité stricte entre deux RADIÉES laisse un restant **sous** le sommet* :

```
candidats : radiée 100,0 · radiée 100,0 · immatriculée 95,0
→ égalité stricte au sommet : OUI
→ le restant après exclusion : 95,0 — SOUS le sommet
```

**Sans la seconde condition, une partie de ce qui devait rester en suspens serait écrite.**

**Le 21 septembre — l'élargissement aux CONFIRMATIONS, mesuré, non appliqué.** *La même exclusion là où le score désignait déjà un gagnant et où le statut désigne LE MÊME.* **494 dossiers sur 2 202 ambigus rejoués** — 70 sous le sommet *(en suspens)*, 1 526 où l'exclusion laisse plusieurs candidats, 47 où elle vide le lot, 65 NEQ déjà portés.

⚠️ **La réserve, et elle ne se lève pas.** *Le statut et le score comparent les candidats ENTRE EUX; aucun des deux ne compare le gagnant au DOSSIER.* Élargie, la règle se lit : **« poser le mieux scoré quand tous ses concurrents sont radiés ».** *Et le bon candidat peut être absent du lot — `resolve_neq_by_name` le plafonne à cinq.* **Une entreprise radiée peut être la bonne : `REQEntry` ne porte aucune date de radiation.**

### Ce que l'adresse en dit — une COLONNE, jamais une condition

| verdict de l'adresse | dossiers | part |
|---|---|---|
| désigne le même | 44 | 8,9 % |
| ⚠️ désigne un AUTRE candidat | 8 | 1,6 % |
| ⚠️ les exclut TOUS | 73 | 14,8 % |
| **ne dit rien** | **369** | **74,7 %** |

⚠️ **« Les exclut tous » n'est PAS toujours un verdict du code postal.** *Quand le code postal ne tranche pas, le repli descend jusqu'à la VILLE — et `fait_de_la_ville` compare des **graphies** : `Saint-Zéphirin` et `St-Zéphirin` ne sont pas la même forme.* **Une graphie de municipalité peut donc renverser un code postal qui était d'accord** *(relevé le 21 septembre sur sept paires où le retenu et son « suspect » portaient le même code postal)*.

⚠️ **Et le départageur d'adresse est bâti pour REFUSER sûrement, pas pour ACCUSER.** *En production, « aucun compatible » n'écrit rien : un refus ne coûte qu'un dossier non posé, ce qui autorise un niveau aussi grossier que la ville.* **Réemployé en garde-fou, le même refus devient une charge, et son niveau le plus faible devient accusateur.**

> **Un garde-fou muet trois fois sur quatre n'en est pas un** : en faire une condition bloquerait 81 écritures et en laisserait passer 369 sans rien en dire. ⚠️ *Et la cause dominante de son silence — « un concurrent ne porte pas le fait » — mesure le **remplissage du registre**, pas la qualité des dossiers.*

### Les causes des contradictions, quand on va les chercher

*Cinq causes, dans l'ordre où elles se cherchent* **(`outils/valeur_des_contradictions.py`)** : l'adresse du dossier est celle d'un **établissement** du retenu *(la contradiction se dissout)*; un **autre concurrent du lot** la porte; un candidat **écarté par l'écart** la porte; un candidat **sous la coupe à cinq** la porte; **aucune**.

⚠️ **Les adresses d'établissement EXISTENT.** *`req_etablissements` est gelée depuis le 2026-09-04, mais le fait a déménagé dans `etat_ligne_source`, partition `req_etablissements`.* **L'hypothèse siège/établissement est donc testable.**

⚠️ **« Le candidat retenu est vraiment le mauvais » n'est pas une case que le produit sait remplir.** *Un code postal partagé n'est pas une identité.* **Les causes ② ③ ④ désignent un SUSPECT, jamais une vérité.**

### ⚠️ Ce que l'adresse du dossier est, selon la source

*Lu dans le code, pas supposé* **(`outils/adresse_deposee_par_source.py`)** :

| source | ce qu'elle dépose |
|---|---|
| **seao** | `parties[].address` du **fournisseur** — l'adresse de l'ORGANISATION, pas le lieu du contrat |
| **eimt** | la colonne `Address` d'une liste dont chaque ligne est un *(employeur × profession × trimestre)* |
| investissement_quebec · contrats_federaux | **aucune** |

⚠️ **Si une source dépose le LIEU D'UN ÉVÉNEMENT plutôt que l'adresse d'une entreprise, l'axe principal du mandat compare deux choses qui n'ont aucune raison de concorder.** *L'instrument qui tranche ne demande ni NEQ ni registre : **pour un même dossier vu plusieurs fois par la même source, l'adresse varie-t-elle?*** **La VARIATION réfute « adresse d'entreprise »; la CONSTANCE ne la confirme pas.**

---

## 9ter. L'ACTIVITÉ ÉCONOMIQUE — le dernier départageur, et son plafond

> **Mesuré le 20 septembre 2026** *(`outils/plafond_de_lactivite.py`)*, **à la demande d'Alexandre : s'assurer que la possibilité est réelle avant de la construire.**

**C'est le seul fait restant qui ne dépend ni du nom ni du lieu.** *Il sépare un `Gérard et Fils` en pavage d'un `Gérard et Fils` en plomberie, quel que soit le code postal.*

**Elle est réelle, et elle est MODESTE.**

| | dossiers | part | |
|---|---|---|---|
| ambigus au 20 septembre | **3 267** | | |
| registre complet **ET** codes différents entre eux | 2 381 | 73,4 % | ← *le registre suit* |
| **(a) route CODE + codes différents — LA BORNE** | **332** | 10,2 % | ← *demande la table du chantier 22* |
| **(b) route LIBELLÉ + codes différents — LA BORNE** | **374** | 11,4 % | ← *n'en demande aucune* |

**Ce n'est pas le registre qui borne, c'est NOTRE côté.** *99,2 % des dossiers ont un code chez tous leurs candidats. Mais du côté DÉTECTÉ, sur les restants : **17,7 % portent un code, 7 % un libellé**.*

⚠️ **Et il ne suffit pas que l'activité existe des deux côtés : il faut que les CANDIDATS DIFFÈRENT ENTRE EUX.** *C'est cette condition qui coupe de 518 à 374* — **un code identique chez tous les candidats ne départage rien.**

⚠️ **Une BORNE n'est pas un GAIN.** *Elle dit où le fait existe et diffère, jamais s'il tranche bien.* **Et un départage écarte un candidat, il n'en confirme aucun.**

**La route par LIBELLÉ ne demande aucune table** — `fait_de_lactivite` la parcourt déjà, mot à mot. **La route CODE attend le chantier 22** *(`falkye-chantier-22-calibration.md`, « Le besoin mesuré »)*, qui se fait à deux : nommer les 53 familles, poser la condition de chacune. *Elle sert deux usages — l'identité et la sphère — donc le travail se fait une fois pour deux, et **332 dossiers ne la justifient pas à eux seuls**.*

⚠️ **Décision d'Alexandre du 19 septembre : les noms génériques attendent le chantier 22.**

---

## 10. Faits acquis, avec leur preuve

**La contrainte d'unicité est portée par la base de production.** Prouvé par l'échec du 16 septembre — `UNIQUE constraint failed: companies.neq`. *C'est l'inverse exact du cas 25, où une garantie déclarée au modèle était absente en base.*

**`scalar_one_or_none()` ne peut pas lever.** Mesuré le 17 septembre sur la colonne que la production interroge (`companies.nom_detecte_normalise`) : **0 forme partagée, 0 forme vide** sur 8 931 dossiers sans NEQ. *Ce zéro dit que le défaut n'est pas survenu, pas qu'il est impossible — la borne sans ordre du dédoublonnage peut créer cette condition demain. Le correctif reste pertinent; il cesse d'être urgent.*

*Ce qui protégeait le chemin n'était pas une garde : un nom normalisé identique score 100, au-dessus du seuil de fusion à 95, donc le doublon était absorbé par le rapprochement flou. **Conformité accidentelle — cas 27.***

**L'échec de la passe de re-résolution n'était pas dû aux 69 NEQ déjà pris.** Le code les écartait déjà, journalisés, jamais posés. La cause était **les collisions internes au lot** — deux dossiers visant le même NEQ libre — corrigée par la demande #71. *Nuance : les 69 étaient traités correctement en logique, mais leur journalisation est partie avec le retour arrière. L'effet net était tout-ou-rien; la cause ne l'était pas.*

**La passe n'est pas un acompte** : 705 posables recalculés, contre 736 à l'instantané du 16. Plus petit. *Et la passe recalcule sa propre liste — le risque n'est pas qu'elle applique une vieille liste, c'est qu'on décide sur un vieux chiffre.*

**Toute société exerçant au Québec doit avoir un NEQ.** Vérifié à la source le 16 septembre (gouvernement du Québec et trois cabinets) : une société constituée au fédéral ou à l'étranger qui exerce une activité ou possède un établissement au Québec **doit s'immatriculer au REQ dans les 60 jours** et y déclare les mêmes renseignements qu'une société québécoise.

⚠️ **Conséquence, et elle retourne la question de départ.** Il n'y a pas d'impossibilité structurelle : **ces entreprises devraient presque toutes être au registre.** Le mur n'est pas qu'il n'y ait rien à trouver — c'est qu'on ne trouve pas ce qui est là. *Corporations Canada est écarté comme pont d'identification : une entreprise qui exerce au Québec a déjà un NEQ.*

---

### Les vérifications closes, avec leur preuve

✅ **L'écriture du 19 a PRIS.** *Le départageur relancé après la passe a lu **6 408** dossiers sans NEQ au lieu de 8 931* — la base a bien changé entre les deux.

✅ **Le seuil de 92 n'est pas ce qui bloque; l'écart n'a aucun gain propre** *(section 8)*. ⚠️ *Ils ne se rouvrent qu'en DERNIER RECOURS, après épuisement des signaux disponibles.*

✅ **Le statut qui écarte vient de `req_entries`, en UPSERT VRAI — jamais de `req_noms`** *(vérifié le 21 septembre)*. `candidats_par_nom` rend des `REQEntry`; `req_noms` n'apporte qu'un **nom**, jamais une entité. **La porte est gelée, le jugement est frais** : une radiée garde ses vieux noms, ils la font entrer dans le lot, et son statut à jour l'en chasse. *C'est ce qui fait tenir la règle du statut.*

---

## 11. Les hypothèses tombées

Toutes mesurées correctement, toutes réfutées. **Les douze premières demandaient pourquoi la comparaison échoue.**

| # | hypothèse | comment elle tombe |
|---|---|---|
| 1-7 | seuil, normalisation, ponts, troncature, champ vide, registre incomplet (14-16 sept) | le second terme n'existait pas |
| 8 | NOM_ETAB comme troisième gisement de noms | 5 sur 2 517 |
| 9 | la colonne `nom_detecte_normalise` périmée | le chemin de résolution recalcule, ne lit pas la colonne |
| 10 | le croisement territorial du registre des sources | une seule source déclare un territoire, et il porte sur la province de l'emploi |
| 11 | les 8 931 seraient majoritairement hors registre | l'immatriculation est obligatoire |
| 12 | `LIMITE_CANDIDATS = 500` du dédoublonnage | mauvais mécanisme — la borne qui décide est `candidats_par_nom` |
| 13 | le préfixe sur les trois premiers cas tracés | leurs préfixes étaient numériques, donc muets |
| 14 | le pic 85-88 serait une réserve d'appariements qui manquent de peu | 89,2 % du pic sur une seule valeur, 84,1 % ne partagent que le premier mot *(7bis)* |
| 15 | la tranche serait remplie par la tête alphabétique, chiffres et ponctuation | la coupe tombe au milieu de l'alphabet — 96,6 % sur « espace puis lettre » *(section 7)* |

⚠️ **Les deux dernières ne sont pas de la même famille que les treize premières.** *Elles ne demandaient pas pourquoi la comparaison échoue : elles proposaient une EXPLICATION de ce qu'on venait de voir.* **Et elles sont tombées de la même manière — par recomptage sur la population, jamais par un cas de plus.**

### Les cinq théories d'Alexandre — examinées le 19 septembre

| théorie | verdict | chiffre |
|---|---|---|
| origine pancanadienne | réelle, **marginale** | 393 sur 4 673 — 8 % |
| consortiums | marginale | 50 — 1,1 %, règle stricte |
| doublons du produit | marginale, **plancher** | 44 exacts — 0,4 % |
| absence d'adresse sur certaines sources | **close** | +0 |
| personnes physiques | ⛔ **non connaissable** | méthode à 57,1 % de faux positifs, seuil de 20 % posé d'avance |
| **noms génériques** | **vivante — c'est le gros du reste** | attend le chantier 22 |

**Sur l'origine** : `rob_top_growing` ×7,6 et `deloitte_fast50` ×5,8 surreprésentées. ⚠️ **Et `province_code` est `null` sur TOUTES les sources** — *le mécanisme prévu pour raisonner par province existe et n'a aucune donnée.* `contrats_federaux` et `investissement_quebec` ne portent aucune adresse **(629 restants)** : fermer la piste demanderait d'ouvrir la source.

**Sur les personnes physiques** : ⛔ *le croisement est SANS CLÉ* — **un restant n'a pas de NEQ, un absent de `Nom.csv` n'a pas de nom.** ✅ *Mesuré au passage : sur 1 010 580 entreprises individuelles, **224 967 sans aucun nom publié — 22,3 %**.* **« Personne physique » ne veut pas dire « introuvable ».**

⚠️ **Et un effet du mécanisme que personne n'a nommé comme règle** *(Alexandre, 19 septembre)*. *Un portrait qui dirait « NEQ 3456433562 a reçu un contrat » ne veut rien dire pour un utilisateur et atteint la réputation du produit.* **Aujourd'hui, l'exigence d'un NEQ fait déjà ce travail** — une personne physique sans nom publié reste dans les restants et ne sort jamais. ⚠️ **C'est un EFFET, pas une règle nommée** : *si l'exigence du NEQ se desserre un jour — pour les entités publiques, par exemple — **le filtre tombe sans que personne y pense**.*

**La règle que cette série a produite** (code de conduite, 16 sept) : *quand plusieurs hypothèses bien mesurées tombent, la question est mal posée. Le remède n'est pas une dixième de la même famille — c'est un cas entier tracé de bout en bout.* **Et : avant de demander pourquoi une comparaison échoue, vérifier que les deux termes existent.**

---

## 12. Les défauts d'instrument rencontrés — et ce qu'ils ont coûté

*Cette section existe parce que quatre mesures de ce chantier ont produit des chiffres cohérents et faux. **Un instrument est aussi exposé que ce qu'il mesure.***

**Un compte figé dans un nom de fichier.** `profil_des_6176.py` portait une mesure périmée dans son nom pendant que l'outil recalculait autre chose. *Un nom de fichier donne l'autorité d'une mesure à une étiquette, et c'est l'endroit où personne ne va la vérifier.* Renommé; un test refuse désormais tout nom d'outil portant un compte.

**Un découpage par forme normalisée, lu comme un compte de dossiers.** *Un compte qui ne dit pas son unité se lit dans l'unité que le lecteur a en tête.*

**Un critère de sélection qui présélectionnait le résultat.** La première trace choisissait des dossiers dont elle avait déjà établi que le NEQ était trouvable par nom exact. *Un critère qui présélectionne le résultat n'échantillonne pas une population : il illustre une conclusion.* **Et il est d'autant plus dur à voir qu'il produit des sorties parfaitement cohérentes** — les trois cas étaient justes, reproductibles, et sans intérêt. *(cas 42)*

**Un scoreur recopié à la main plutôt qu'emprunté.** La simulation des parenthèses rescorait sans le pont des noms multiples ni le bonus de ville : « Ferme M.G. Bellavance » scorait 30 dans la recopie contre 100 dans le moteur. **338 dossiers perdus imaginaires.** *Cas 41 dans l'instrument même.*

**Une constante décorative.** `limite: int = LIMITE_CANDIDATS_PAR_NOM` — Python l'évalue une fois à l'import. La constante existait, le code la nommait, **et la changer n'avait aucun effet.**

**Une règle de lecture à laquelle il manquait une branche.** Un perdu *sans* parenthèse au nom détecté pouvait quand même relever du mécanisme, si un **candidat** en portait une. Trois lectures, pas deux — et la troisième seule accuse l'instrument.

**Ce qui a fonctionné** : les gardes qui refusent. Le 17 septembre, `doublons_forme_stockee` a refusé sur `REPLI PAR DÉFAUT` faute d'environnement chargé. **Sans ce refus, la sortie aurait été `✅ AUCUNE LIGNE RENDUE` sur une base vide, et une vérification aurait été fermée sur rien.** *Une panne se voit; un vert sur une base vide ne se voit pas.*

---

## 12bis. Les défauts du CODE DE RÉSOLUTION — identifiés, UN SEUL corrigé

> ⚠️ **À ne pas confondre avec la section 12**, qui porte les défauts des INSTRUMENTS DE MESURE. *Ceux-ci sont dans le produit, ils tournent en production, et leur correction est l'étape 13 du bloc de l'import.*

**Relevés le 20 septembre, en lisant onze motifs sur des dossiers entiers.**

| défaut | ce qu'il fait | où |
|---|---|---|
| **les paliers du scoreur** | `WRatio` rend 100, 95, 90 — *un nom du registre entièrement contenu dans le nom détecté rend **exactement 90,0*** | `rapidfuzz` |
| **la coupe à cinq** | le lot soumis au score est plafonné à 5, après une récupération qui en ramène jusqu'à 2 000 | `resolve_neq_by_name(limit=5)` |
| **le bonus de ville APRÈS la coupe** | +5 si la ville concorde, **plafonné à 100** — *donc un 95 avec bonus atteint 100, et le pré-bonus n'est conservé nulle part* | `_scorer` |
| **le garde-fou des noms d'un mot** | `candidats_par_mot_rare` exige un **deuxième mot**, qu'un nom d'un mot n'a pas — **c'est la cause du ×3,4 du portrait** | `candidats_par_mot_rare` |
| **`ni` → `IMMATRICULEE`** | tout ce qui n'est pas `radiee` devient `IMMATRICULEE` | `falkye/resolution.py` |
| **la radiation silencieuse** | `verification.py` exclut les `RADIEE` **après** résolution, sans le dire — *le dossier disparaît* | `falkye/verification.py` |
| ~~**la fusion de fait par le NEQ**~~ ✅ | `resolve_company` cherchait un `Company` **par NEQ** avant d'en créer un : *tous les dossiers résolus vers le même NEQ étaient rattachés au MÊME dossier* — **corrigé le 23 septembre**, voir ci-dessous | `falkye/resolution.py` |

✅ **LE SEUL CORRIGÉ — la fusion de fait par le NEQ** *(23 septembre, demandé par Alexandre avant tout le reste : « c'est le seul point qui peut abîmer la base »)*.

**Ce qu'il faisait.** `resolve_company` cherchait un `Company` **par NEQ** avant d'en créer un. *Plusieurs noms détectés résolus vers le même NEQ étaient donc rattachés au MÊME dossier* — **fusionnés de fait, silencieusement, sans qu'aucune ligne ne le dise.** ⚠️ *Décision du 16 septembre : conservation toujours, aucune fusion.* **Six dossiers CISSS réunis sur `8879690699` sont une fusion de fait.**

**Pourquoi la garde du 17 septembre ne le couvrait pas** : `PRETENDANTS_MAX_POUR_TRANCHER` vivait dans `outils/pose_du_neq.py`, donc elle ne protégeait que les passes par LOT — **jamais la production.** *Elle vit maintenant dans `falkye/resolution.py`, et `outils/` l'emprunte.*

⚠️ **La FORME du refus a changé en descendant, et elle ne pouvait pas ne pas changer** :

| | la passe par LOT | la RÉSOLUTION |
|---|---|---|
| ce qu'elle voit | tous les prétendants ensemble | UN dossier à la fois |
| qui détient le NEQ au moment de décider | **personne** | **quelqu'un, déjà** |
| le refus | personne ne l'obtient | le **nouveau venu** ne l'obtient pas |

*C'est une contrainte de schéma qui l'impose* : **`Company.neq` est UNIQUE.** Le partage n'est pas une issue, et retirer le NEQ au détenteur serait **une écriture qui EFFACE une identité**, pas une garde. **La garde ne peut que RÉDUIRE les écritures.**

⛔ **CE QUI N'EST PAS DESCENDU, et qui reste à trancher avec Alexandre : le SEUIL.** *Au-delà de deux prétendants, la passe par lot retire le NEQ à tout le monde; ici le premier arrivé le garde*, et le rang n'est qu'**écrit au journal** (`statut="pretendant_refuse"`, délibérément pas `a_examiner` — *`diagnostic confirmer-fusion` n'agit que sur `a_examiner` et appliquerait la fusion que la garde vient d'empêcher*).

⚠️ **La frontière, posée pour être vue** : la garde ne s'applique qu'au NEQ **inféré par le scoreur**, jamais à celui qu'une source **affirme** (`RawSignal.neq`). *La garde est née d'un appariement par le nom; un NEQ affirmé n'est pas un appariement.*

⚠️ **Deux d'entre eux portent une échelle, et une échelle se pose avec Alexandre** : la **coupe à cinq** *(une valeur, donc une échelle)* et le **bonus de ville**.

**Encore à tester** *(section 17)* : les 1 049 couples à 100/95; la coupe à cinq; le bonus de ville après la coupe; le garde-fou des noms d'un mot; les 1 526 où l'exclusion laisse plusieurs candidats; les 70 contradictions en suspens.

**Plancher non corrigeable** — *ce qui restera quoi qu'on corrige* : hors Québec; **entités publiques** *(D27, D28)*; personnes physiques; bannières *(`SUBWAY`, `IGA`, `LA BELLE PROVINCE`)*.

⚠️ **Et un défaut d'affichage qui a coûté deux jours de lecture fausse** : *`_scorer` prend le meilleur des noms d'un NEQ, `req_noms` compris, et les outils affichaient la **dénomination élue**.* **`Elevage des reines Le Roi Bourdon` rendait 61,5 contre le nom détecté, sur une ligne qui annonçait 95,0.** *`formes_retenues` existe depuis le 17 septembre pour ça; il a fallu la brancher.*

---

## 13. Ce qu'il faut construire

*Rien de ce qui suit n'est commencé. La liste vient du mandat; elle n'ajoute rien.*

**Chantier 3 — l'identité**

1. **L'identité interne**, clé du dossier cumulatif, de la corroboration et de la déduplication, distincte de tout identifiant externe.
2. **La table d'identifiants externes**, chacun avec son **territoire**, sa **famille d'entité**, sa source et sa date. Zéro, un ou plusieurs. ⚠️ *Une identité sans identifiant externe est valide de plein droit.*
3. **Le niveau de vérification par couple identité × territoire.**
4. **Le traitement des prospects non vérifiables** — exclusion ou confiance plafonnée, **implémenté dans le score et non dans un avertissement affiché.**

**Chantier 4 — la confiance d'appariement**

5. **Le score hérité du maillon le plus faible** de l'historique de fusion, qui **plafonne** au lieu de s'additionner.
6. **L'adresse comme axe principal, le nom en corroborateur.** ⚠️ *Le préalable du 17 septembre a établi que l'adresse n'existe sur aucun des 8 931 dossiers à apparier* — l'axe principal du mandat est aujourd'hui vide, et c'est un fait à porter dans la conception, pas une raison de l'inverser.
7. **La table d'apprentissage raison sociale ↔ nom d'enseigne ↔ adresse.** *Elle s'enrichit avec le temps : la construire tard, c'est repartir d'une table vide alors que les mauvais appariements se sont accumulés.*
8. **La règle de non-promotion** : sous un seuil, le signal reste une réflexion et ne déclenche rien, quelle que soit sa force.

**Commun aux deux**

9. ~~**La passe de reprise**, seul mécanisme qui répare un dossier existant *(section 6)*.~~ ✅ **Construite et APPLIQUÉE le 19 septembre — 2 523 NEQ posés** *(section 5bis)*. *Il lui manque son déclencheur : c'est l'étape 8 du bloc de l'import.*

10. ⚠️ **LA MESURE DE JUSTESSE** *(ajoutée par Alexandre le 21 septembre — chantier 4)*. **On a compté combien de NEQ on posait, jamais combien sont BONS.** *Les paires lues servaient à décider d'une règle, pas à vérifier l'ensemble des 5 323.*

   > **Un NEQ posé sur la mauvaise entreprise est PIRE qu'un dossier sans NEQ : il produit un faux prospect, et rien ne le signale.**

   **La forme proposée** : un échantillon **tiré au hasard** parmi les NEQ posés, **par règle** *(passe de reprise, départage par l'adresse, exclusion des radiées)*, vérifié à la main.

   ⚠️ **Une échelle qui n'existe pas, et qui se pose avec Alexandre : le TAUX D'ERREUR ACCEPTABLE pour qu'une règle tourne seule.** *C'est aussi le critère qui manque à l'étape 10 du bloc de l'import pour faire passer une règle d'outil ponctuel à règle permanente* — **les deux se posent probablement ensemble.**

⚠️ **Ordre imposé.** **D27, D28 et D29 se tranchent avant les points 1 et 2.** *La structure du dossier à plusieurs noms attend le même moment* — sa forme survit, son point d'accrochage tombe *(section 17, et `docs/PROPOSITION-DOSSIER-MULTI-NOMS.md`)*.

---

---

## 13bis. Deux cas d'usage de la table d'identifiants externes

> **Des théories d'Alexandre sur ce qui restera APRÈS les écritures, chacune avec ce qui l'appuie.** *Aucune n'est un mandat — elles disent pourquoi la structure du point 2 est nécessaire, et à quoi elle servira le jour où elle existera.*

### Les consortiums — un champ qui nomme plusieurs entreprises n'est pas une entreprise

```
« 9281-7600 Québec inc. & Action SST inc. »
« 9528-9393 Québec inc., Fabrication A.S. inc. & Maurice Milette »
```

**Le nom détecté désigne un groupement, pas une entité.** *Aucun score de ressemblance ne peut faire mieux que de l'apparier à l'un de ses membres, et il le fera au hasard de la graphie.*

**Les scinder et résoudre chaque membre demanderait qu'un dossier porte PLUSIEURS NEQ.** ⚠️ **Le modèle n'en permet qu'un** — `Company.neq` est unique, et la contrainte est portée par la base de production *(section 10)*. *C'est exactement la forme que la table d'identifiants externes rend possible : zéro, un ou plusieurs identifiants par identité.*

~~⚠️ **Jamais compté.**~~ ✅ **Compté le 19 septembre, en compte EXACT : 50 dossiers — 1,1 %, par la règle stricte.** ⚠️ *À ne pas confondre avec « porte une conjonction » (7,8 %), qui est le fait brut du caractère* — **les deux chiffres ne sont pas comparables.**

### Les doublons du produit — deux sources nomment la même entreprise différemment

**Le second dossier ne trouve rien**, parce que le premier porte déjà le NEQ. *C'est le défaut de fond vu d'un autre côté : la résolution ne répare pas, et elle ne rapproche pas non plus deux dossiers qui visent la même entité.*

**Les 111 NEQ déjà pris de la passe le montrent en clair** *(mesuré le 19 septembre)*. Deux familles, et elles n'appellent pas le même geste :

| | exemples | ce que c'est |
|---|---|---|
| **variantes de graphie** | `AYE3D inc.` / `AYE3D Inc.` · `Acti-Sol inc.` / `Acti-Sol inc.` | **deux dossiers pour une entreprise** — la casse seule les sépare |
| **noms d'enseigne** *(une douzaine)* | `PHILIPS CANADA` → `PHILIPS ÉLECTRONIQUE LTÉE` · `Casa Grecque Drummondville` → `3038947 Canada Inc.` · `Kanatrac - Joliette` → `Kanatrac inc.` | **la raison sociale et l'enseigne**, ce que la table d'apprentissage du point 7 existe pour retenir |

⚠️ **Les joindre ne veut PAS dire les fusionner.** *Décision du 16 septembre, section 4 : conservation toujours, aucune fusion.* **La table d'identifiants externes permet de dire « ces deux identités portent le même NEQ » sans en supprimer une.**

**Seul indice chiffré, et il est indirect** : sur les 805 retenus de la phase 0, **773 NEQ distincts visés, 32 dossiers en trop — 4 %** *(section 5)*. ⚠️ *C'est une borne basse sur les seuls dossiers que le nom résout; elle ne dit rien des doublons que le nom ne résout pas.*

✅ **Compté le 19 septembre : 44 doublons EXACTS — 0,4 %**, et c'est un **plancher**.

---

### ✅ Les 111 RETENU — tranché le 20 septembre : une IMPASSE

**0 NEQ libre.** *Ce sont les NEQ « déjà pris » que la règle de conservation interdit de poser* — donc **aucun gain n'attend derrière eux**.

⚠️ **Mais ils sont le premier argument CHIFFRÉ pour le chantier 3.** *111 + 50 consortiums + 44 doublons ≈ **205 dossiers*** que la structure « un dossier, plusieurs identifiants » débloquerait — **et rien d'autre.**

> **Une impasse et un argument sont la même mesure, lue deux fois.** *Le compte qui ferme la piste du gain est celui qui ouvre la justification de la structure.*

---

## 14. Tests exigés

1. **Territoire fictif.** Ajouter un identifiant d'un territoire qui n'existe pas ne touche **aucune ligne** du moteur de croisement.
2. **Non-régression québécoise.** Une entreprise portant un NEQ produit **exactement** les mêmes résultats qu'avant le chantier. *C'est un critère, pas un effet secondaire acceptable.*
3. **Identité nue.** Une identité sans aucun identifiant externe traverse la corroboration, la déduplication et le score **sans être traitée comme dégradée**.
4. **Le score plafonne.** Une identité faible dans l'historique de fusion **empêche** une confiance élevée en sortie, et deux maillons moyens ne s'additionnent jamais en un fort.
5. **La non-promotion mord.** Sous le seuil, aucun déclenchement, **quelle que soit la force du signal**.
6. **Deux appariements à score comparable.** Le défaut n'est jamais « prendre le meilleur score » — le test vérifie ce que le moteur fait à la place.
7. **Les échelles sont lues, jamais recopiées.** Seuil, écart et borne de récupération sont empruntés au moteur par tout outil qui les diagnostique. *Trois défauts de ce chantier venaient d'une recopie (section 12); la suite les garde déjà.*
8. **Une mesure n'écrit rien.** Tout outil de ce chantier laisse la base inchangée, et un test le vérifie dossier par dossier.

---

## 15. Vérification macro — obligatoire avant de déclarer le chantier fini

**Le chantier n'est pas fini quand le code passe ses tests.** *Le chantier 1 était réputé clos et ne s'était jamais exécuté en production (cas 39).* Donc :

1. **Rejouer la ventilation des 8 931** après construction, et la comparer **chiffre pour chiffre** à celle du 16-17 septembre *(section 5)*. Une ventilation qui n'a pas bougé est un résultat, pas une panne — c'est ce que le rejeu du 16 a établi.
2. **La passe de reprise a tourné au moins une fois sur la base réelle.** *Sans elle, un gain mesuré n'est jamais devenu un dossier résolu* — et le chantier aurait livré une amélioration que personne ne peut voir.
3. **Les vingt candidats de fusion en attente sont examinés APRÈS le chantier, jamais avant** *(mandat)*. Ils sont le jeu de test naturel de la confiance d'appariement.
4. **Le test du territoire fictif tourne contre le moteur réel**, pas contre un décor.
5. **Le registre des décisions est à jour** : D27, D28, D29 tranchées et datées; D43 rouverte avec elles.
6. ⚠️ **La justesse des NEQ posés est MESURÉE** *(section 13, point 10)*, sur un échantillon tiré au hasard, par règle. **Sans elle, le chantier peut livrer 5 323 identités dont personne ne sait ce qu'elles valent** — et la fermeture affirmerait un gain qu'elle n'a pas établi.

**Critère de fermeture, en une phrase.** *Le chantier est fini quand une identité sans NEQ traverse tout le moteur aussi bien qu'une identité qui en porte un, quand une identité faible ne peut plus produire une notification forte, et quand la ventilation rejouée le montre sur la base réelle.*

⚠️ **Ce que la fermeture ne dira PAS** : que les identités récupérées valent quelque chose. **C'est le mur d'après** *(section 18)*, et il a son propre instrument, qui n'existe pas.

---

## 16. Ce qui doit être livré

1. **Le constat de phase 0** — c'est ce document, sections 5 à 12.
2. **D27, D28, D29 tranchées**, avec leur réponse par défaut, **avant la conception de la clé**.
3. **Le code des points 1 à 9** *(section 13)*.
4. **Les huit tests** *(section 14)*, verts, dans la suite existante.
5. **Le rapport de vérification macro** *(section 15)*, avec la ventilation rejouée à côté de celle du 17 septembre.
6. **La mise à jour du registre des décisions ouvertes** et de `falkye-specifications-produit.md` — ce que le produit fait, une fois qu'il le fait.
7. **Les notes de ce chantier versées au journal des cas**, les défauts d'instrument compris.

**Ne rien commencer d'autre.** Si le chantier révèle un problème appartenant à un autre chantier, le consigner dans le `DiagnosticJournal` et le rapporter, sans l'attaquer.

---

## 17. Ce qui reste ouvert

**En mesure, au 17 septembre**
- Le recomptage du plancher, **mesure C seule** — ce qu'une borne levée récupérerait. *Les mesures **A** et **B** ont tourné le 17 septembre sur l'hôte et sont versées aux sections 7 et 7bis; **C est en cours**.* ⚠️ **Elle portera sur un échantillon de 200 dossiers, avec un plafond de gisement qui écarte précisément les plus gros cas** — *le chiffre qu'elle rendra sera un PLANCHER du gain, jamais une estimation.*
- ~~Le code postal : le second terme qui se recouvre entre l'EIMT et le REQ, **jamais regardé**.~~ ✅ **Regardé, construit et ÉCRIT le 19 septembre** — `outils/ecriture_des_departages.py`, **1 735 NEQ posés** au code postal complet. *Décision d'Alexandre du 19 : n'écrire que ce niveau; 268 départages laissés EN SUSPENS — 188 par région de tri, 80 par ville.*
- La trace sur un nom ordinaire — la réserve sur le préfixe parlant, encore non testée sur un cas réel.
- La normalisation des municipalités sur les 612 sans concordance. *Observation non mesurée : une part semble relever de l'écriture — « St-Apollinaire » contre « Saint-Apollinaire ».*
- L'alias de la RBQ, jamais mesuré.

**En décision d'Alexandre**
- ~~La promotion de la ville vers le dossier (1 111 dossiers).~~ ⛔ **Mesurée le 19 septembre : +0 au départage.** *Le gisement existait; il ne séparait rien de plus que ce qui l'était déjà.* **Piste close, et son chiffre reste** — voir section 8.
- ~~L'application de la passe de reprise sur les 705.~~ ✅ **Appliquée le 19 septembre** — `outils/reresolution_neq.py --appliquer`, **2 523 NEQ posés** *(et non 705 : la passe recalcule sa propre liste, et la population avait changé)*. *Instantané et `--defaire` à `/var/lib/falkye/`.*
- L'écart minimal : 2 097 dossiers à écart 4, au prix de 2 097 décisions machine entre deux entités.
- ⚠️ **`RawSignal` n'a aucun emplacement pour un CODE POSTAL** — il porte `adresse`, `ville`, `region`. *Le niveau le plus fort du départageur — 1 764 départages, dont 1 735 écrits — **ne fonctionne que parce que `faits_du_dossier` va le chercher lui-même dans `Signal.champs`**.* **Deux directions : élargir `CLES_ADRESSE`, ou donner un emplacement à `RawSignal`.** *Décision de modèle, aucun dossier en jeu — **registre D59**, et rien ne se construit dessus avant.* ⚠️ *Et un usage de plus, relevé le 19 septembre : le code postal servira au **rayon d'action de l'utilisateur**.*
- ⚠️ **Le critère qui fait passer une règle d'outil ponctuel à règle PERMANENTE** — *une échelle qui n'existe pas* **(registre D54)**, probablement la même décision que le **taux d'erreur acceptable** de la mesure de justesse **(D55)**.
- ⚠️ **La coupe à cinq candidats : son échelle** *(registre D57)*. **Une valeur, donc une échelle, donc Alexandre.**
- **D27, D28, D29** — préalables à la conception de la clé.
- L'ordonnancement et le filtrage du registre : hypothèse d'Alexandre du 16 septembre, appuyée par la saturation mesurée. *Conception à deux, non commencée.*
- ⚠️ **Vérifier que la fusion ≥95 tourne encore** dans `falkye/dedup_entreprises.py`. *C'est une vérification, pas une décision : l'échelle **95 / 90** est celle de la confiance d'appariement, donc de ce chantier.* **À trancher avec elle : quelle branche fait foi.** *Un README est de la documentation, pas le code — cas 38.*

**Les pistes NEUVES — relevées après la chute des cinq théories, aucune mesurée**

> *Ordre posé par Alexandre le 19 septembre : **d'abord les hypothèses qu'on a**, ensuite plonger dans celles-ci.*

- **Les noms PÉRIMÉS.** ⚠️ *La piste a changé de nature le 23 septembre* : elle n'est plus « 3 129 272 lignes non indexées » — **elles sont en base depuis le 17 septembre**, et le moteur ne les consulte plus qu'en **troisième temps** *(registre D52)*. *Ce qui reste ouvert est ce qu'elles RAPPORTENT, et le compte est fait : 208 dossiers, dont 157 sur leur propre ancien nom.*
- **Les filiales et les noms après acquisition.** *`SDI CANADA` → `BIOMEDSHIELD`, `KONE` → `DROLET KONE ELEVATORS`.* ⚠️ **`FusionScissions.csv` porte `NEQ_ASSUJ_REL` à 78,5 % — une relation NEQ→NEQ que le produit n'a jamais lue.** *Et si le signal vise la filiale mais que le prospect utile est la mère, le portrait ne dit pas lequel.* ⚠️ **Question ouverte sur le même fichier** : `DENOMN_SOC` est attaché au `NEQ` de la rangée — *mais qui est le SUJET d'une rangée de fusion, l'absorbante ou l'absorbée?* **Le dépôt ne le dit pas, et ce gisement n'a aucune colonne de statut.**
- **Les entités publiques.** *Municipalités, CISSS, centres de services scolaires — pas de NEQ au REQ.* **Vues avec `8879690699`. Jamais comptées.** *Touche **D27** et **D28**.*
- **Le nom détecté n'est pas un nom d'entreprise** — nom de projet, acronyme, département, marque.
- **L'entreprise a cessé d'exister** — radiée, fusionnée, dissoute.
- **Le nom est TRONQUÉ à la capture** — *« et 9254-61 », « ABtech » coupés net.*

**En conception, non commencé**
- **Tout le chantier 3.** L'identité interne, la table d'identifiants externes, la famille d'entité, le niveau de vérification par couple identité × territoire.
- La structure du dossier à plusieurs noms. `company_noms` est tombée **comme structure définitive** — elle accrochait les noms à `company_id` et supposait `Company.neq` comme pivot, alors que le mandat dit que la clé du moteur cesse d'être un identifiant de territoire. **La forme survit** — `(identité, nom_normalisé)` avec `nom`, `source_id`, `first_seen_at` — son point d'accrochage et son moment tombent. *Détail dans `docs/PROPOSITION-DOSSIER-MULTI-NOMS.md`.*

⚠️ **Où vivent les noms — à trancher.** Trois structures peuvent porter la même correspondance : `req_noms` *(miroir, **5 071 984 formes** depuis le 17 septembre — 1 505 879 avant)*, la table d'apprentissage du chantier 4, et le dossier lui-même. *Charte : un point vit à un seul endroit.*

⚠️ **Et `req_noms` ne porte plus seulement des noms EN VIGUEUR.** *Le 17 septembre, le chargeur a cessé de filtrer `STAT_NOM='V'`* — **ce que le moteur doit faire d'un nom retiré est ouvert au registre, D51**, et se tranche avant toute nouvelle écriture de NEQ.

---

## 17bis. Le bloc de l'import — les quatorze étapes, dans l'ordre

> ⚠️ **DÉCISION D'ALEXANDRE, 20 septembre 2026 : aucun import tant que ce bloc n'est pas complet.**
>
> *Le 2 octobre cesse d'être une échéance à respecter et devient une édition qu'on choisit de sauter.* **Le travail garde sa valeur, il perd son urgence de calendrier.**
>
> **Décision du 21 septembre, qui ajoute les étapes 10 à 14** : *le bassin actuel est un **bassin de pratique**. Chaque façon d'ajouter des NEQ qu'on valide ici devra tourner seule, à chaque import, sans que personne relise les paires.* **Un outil ponctuel se relit; une règle permanente, non.**

**Le prix d'attendre, et il est faible sans clients** : le miroir vieillit, les entreprises immatriculées depuis le 2 septembre restent introuvables, le diff suivant sera d'autant plus gros.

⚠️ **Une question, pas une construction : le prochain import serait-il le PREMIER VRAI DIFF du REQ?** *`docs/MIROIRS.md` pose que les signaux n'apparaissent qu'à partir de la deuxième édition importée, et les imports du 16 et du 17 ont tous deux porté sur l'archive du 2 septembre.* **À vérifier sur l'hôte, jamais à supposer** — c'est l'étape 1.

⚠️ **Et ce bloc ROUVRE D14.** *Le registre écrit sa condition de réouverture en toutes lettres : « un cycle qui résout réellement des entreprises — **un premier import REQ d'un trimestre neuf**, une source réactivée, une population qui grandit ».* **Le repli par sous-chaîne a été fermé le 11 septembre parce qu'il n'était emprunté aucune fois; un import qui résout le rend à nouveau mesurable.**

### Ce que le dépôt en porte déjà — et où

**Presque tout est conçu, et hors corpus** : `docs/CONCEPTION-TRAITEMENT-ARCHIVE-REQ.md`. ⚠️ *Ce document date d'avant le 17 septembre* — il parle encore de 1,5 million de noms et range `FusionScissions.csv` parmi les fichiers jamais regardés. **Des parties en sont périmées, et il ne fait pas foi.**

### Avant tout import — les neuf étapes qui PROTÈGENT

*Aucune de ces neuf ne récupère une entreprise : elles protègent ce qui a été gagné.*

| # | étape | où vit le mécanisme |
|---|---|---|
| **1** | **Vérifier ce que l'état de diff porte sur l'hôte** — savoir si le prochain import serait le premier vrai diff. *Une question, pas une construction.* | `falkye-chantier-1-quarantaine.md`, *Conservation de l'état d'une source* |
| **2** | ⚠️ **Poser les seuils de quarantaine du REQ, avec Alexandre.** Deux seuils franchis ensemble, distincts par type d'écart, propres à la source. | **D17** *(à enrichir, pas à doubler)*; `falkye-chantier-1-quarantaine.md`, *Règle de quarantaine*; **le chiffrage vit dans D36** et ne se recopie pas ici |
| **3** | ⚠️ **Poser le plancher de remplissage PAR FICHIER, avec Alexandre.** *Une part retenue qui s'effondre doit refuser bruyamment.* **C'est une seconde échelle, pas celle de l'étape 2.** ⚠️ **Et la valeur de référence a DÉJÀ bougé** : le `~32,7 %` cité par la conception était la part des lignes de `Nom.csv` en vigueur — *une propriété du FICHIER* — **mais le chargeur les garde toutes depuis le 17 septembre, donc la part RETENUE est aujourd'hui ~100 %.** *Poser un plancher sur l'ancienne valeur refuserait chaque import.* | `falkye-chantier-1-quarantaine.md`, *Détection de changement de schéma* — et le registre des sources |
| **4** | **La revue d'archive** — le plancher ci-dessus, et l'inventaire déclaré du zip. *Le garde des colonnes existe et il est bon (`colonnes_brutes_lues`, par arbre syntaxique); `FICHIERS_REQ_REELS` vérifie une PRÉSENCE, jamais une absence d'inattendu.* ⚠️ **Si `STAT_NOM` est renommée, `req_noms` se vide en se déclarant réussi.** | même chantier, même section |
| **5** | **L'édition du miroir** — la table `req_editions`, empreinte calculée sur le CONTENU du zip *(`file_size` et CRC des membres, jamais le nom du fichier)*. ⚠️ **À nommer distinctement du SHA256 qui existe déjà** pour détecter un transfert tronqué : deux empreintes qui se confondraient. | à construire; le SHA256 existant vit dans `docs/MIROIRS.md` |
| **9** | ⚠️ **D36 — l'import interrompu.** *Ne bloque la construction de rien.* | **D36**, qui porte les trois options — voir ci-dessous |

⚠️ **Les étapes 6 et 7 s'écrivent ICI EN ENTIER, et c'est une décision du 21 septembre.** *Le renvoi vers `docs/MIROIRS.md` avait été supposé, pas lu : ce document ne porte ni `INSERT OR IGNORE`, ni `first_seen_at`, ni `req_editions` — il ne nomme `req_noms` que pour l'espace disque.* **Renvoyer vers un document qui ne porte pas le fait envoie le lecteur nulle part.**

**6. Trancher `first_seen_at`, et le régime des deux tables.** *Les autres tables du miroir portent une date de première apparition ET une de dernière observation; `REQNom` n'a pas la seconde.* **Sans elle, on ne peut pas dire depuis quand une forme n'a plus été vue dans l'archive** — donc pas distinguer un nom que le registre a retiré d'un nom que notre import n'a pas relu.

**7. Le rechargement en UPSERT — après la 6.** `req_noms` s'écrit en `INSERT OR IGNORE` et **rien ne la vide** : une ligne existante est **sautée, jamais mise à jour**. Trois conséquences mesurées :

- **`gisement` est vide sur 1 505 879 lignes sur 5 071 984 — 29,7 %** *(les lignes du pont d'avant le 17 septembre)*;
- **`statut` est figé à la PREMIÈRE insertion de chaque paire `(neq, nom_normalisé)`** — un nom passé de `V` à `A` dans une archive suivante reste `V` en base. **La table porte deux millésimes, et rien ne les distingue sauf `gisement IS NULL`**;
- ⚠️ **le lot des candidats ne peut que GRANDIR** : `_scorer` prend le MEILLEUR des noms d'un NEQ, donc un score de NEQ ne peut que monter d'un import à l'autre. *Conséquence pour toute règle qui écrit sur une égalité ou une exclusion : **plus de dossiers à « plusieurs candidats », donc moins d'écritures, import après import.*** **Dérive dans le sens sûr — mais elle doit être ATTENDUE, sinon une baisse de rendement se lira comme une panne.**

⚠️ **Ça vaut pour TROIS tables — `req_noms`, `req_mots`, `req_mots_frequence` — et PAS pour `req_entries`, qui est en upsert vrai** *(`_upsert_entreprise_reelle`)*. **Un correctif qui les traiterait ensemble se tromperait sur l'une.** *C'est ce qui fait tenir la règle du statut aujourd'hui : **la porte est gelée, le jugement est frais** — une radiée garde ses vieux noms, ils la font entrer dans le lot, et son statut à jour l'en chasse.*

**Forme retenue par Alexandre le 19 septembre : passage en UPSERT + réimport** — la seule qui corrige la cause.

⚠️ **Et l'étape 7 ne suffit pas sans D51.** *Passer en UPSERT rafraîchira le `statut` des formes; **rien ne lira ce statut pour autant**.* **Ce que le moteur fait d'un nom retiré est ouvert au registre et se tranche avant toute nouvelle écriture de NEQ.**

**8. La reprise déclenchée par l'import.** *La passe existe et sait écrire (`outils/reresolution_neq.py`, 2 523 NEQ posés le 19 septembre); **seul manque le déclencheur**.* ⚠️ **Un dossier resté sans NEQ ne se réexamine jamais** — c'est le défaut de fond de la section 6, vu du côté du calendrier.

**Sur l'étape 9 — D36 porte TROIS options, et la troisième est celle qu'elle retient** : *(a)* valider l'état de diff après le dernier signal de la source — *échange une classe de perte contre une autre*; *(b)* journaliser le point d'avancement; *(c)* **appliquer l'état ET émettre les signaux PAR LOTS ALIGNÉS**, de sorte que l'état n'avance jamais au-delà de ce qui est durable — *aucun journal, aucune liste, moins d'écritures*. **Le prix de (c) est nommé : `apres_diff_accepte` est invoqué exactement UNE fois, et c'est une garantie du chantier 1 — la découper est un changement de contrat.**

### Faire œuvre des règles validées — les cinq étapes qui REGAGNENT

*Ajoutées le 21 septembre. **Ce que le bassin de pratique a gagné doit se regagner à chaque import.***

**10. Intégrer à la résolution chaque règle validée et déjà appliquée.** *Aujourd'hui : l'exclusion des radiées sur les égalités strictes — **1 065 NEQ posés le 20 septembre**, par un outil de `outils/`, qui ne s'appliquerait pas au prochain zip.*

✅ **Vérifié le 21 septembre** : le statut qui écarte vient de `req_entries`, en upsert vrai — donc à jour à chaque import. ⚠️ **Mais deux dérives quand la règle tournera seule, à trancher AVANT l'intégration :**

- ⚠️ **une radiation entre deux zip fait écrire un NEQ sans décision.** *Un dossier passe de « plusieurs candidats » à « écriture » parce qu'un concurrent a été radié* — et `REQEntry` ne porte **aucune date de radiation**. **La règle convertirait « radiation observée » en « NEQ posé », en silence.**
- **Le lot ne peut que grandir** *(étape 7)* — la règle écrira moins, import après import.

**11. Intégrer les règles EN DÉCISION, si Alexandre les valide** — l'élargissement aux confirmations, avec sa condition; et le verdict de l'adresse comme module de la résolution, **s'il devient une condition**. ⚠️ *Il ne l'est pas : l'adresse ne juge que 25,3 % des dossiers, et un garde-fou muet trois fois sur quatre n'en est pas un.*

**12. Ce qu'il faut pour qu'une règle tourne SANS RELECTURE.** *Chacun de ces quatre points existe déjà dans les outils ponctuels, et aucun n'existe dans la résolution :*

1. **un rapport d'import** qui compte ce qui a été posé **et ce qui est resté en suspens** — *un outil qui écrit une partie doit dire lesquels il n'a pas touchés, sinon la différence se lit comme une perte*;
2. **un instantané et une annulation à chaque passe** — l'équivalent de `--defaire`;
3. **la protection des NEQ déjà portés** — jamais écrasés, journalisés, les deux dossiers conservés;
4. **des témoins vérifiés à chaque import**, pour détecter une régression. ⚠️ *Et un témoin s'AFFICHE, il ne s'affirme pas* — `Les Ruchers du Roi Bourdon` a été lu pendant deux jours sur une ligne qui montrait un nom n'ayant pas scoré.

**13. Corriger les défauts trouvés dans le code**, une fois chaque correction validée : *les paliers du scoreur; la **coupe à cinq** et le bonus de ville appliqué APRÈS elle; le garde-fou des noms d'un mot (`candidats_par_mot_rare` exige un deuxième mot — c'est la cause du ×3,4 des noms d'un mot); `ni` transformé en `IMMATRICULEE`; la radiation qui fait disparaître un dossier sans le dire.* **`req_noms` en `INSERT OR IGNORE` est déjà l'étape 7, et le traitement des noms retirés est D51.**

**14. La réouverture des dossiers posés** — *ajoutée par Alexandre le 21 septembre.* **Un NEQ posé est aujourd'hui définitif, alors que le fait qui l'a justifié est volatil.** À chaque import, revoir un dossier dont le NEQ a changé de statut *(radié depuis)* ou pour lequel un meilleur candidat est apparu. ⚠️ **Revoir n'est pas écraser : la règle de conservation s'applique.**

⚠️ **Jamais discuté, et c'est ce qui manque pour franchir l'étape 10 : le critère qui fait passer une règle d'outil ponctuel à règle permanente.** *Une échelle — par exemple la part de contradictions sous laquelle une règle est acceptée.* **Elle se pose avec Alexandre, probablement en même temps que le taux d'erreur acceptable de la mesure de justesse.**

**Puis l'import, quand les étapes 1 à 8 et 10 à 14 sont faites.** *C'est le test ultime : un autre fichier zip du REQ, pour voir comment les règles se comportent sur des données que personne n'a lues.*

---

## 18. Le mur d'après

Le chantier 3+4 récupère des identités. **Il ne dit pas ce qu'elles valent.**

Sur les entreprises qui ont **déjà** un NEQ, une centaine seulement passe la vérification complète — statut légal, signe d'activité, cohérence d'identité. **Personne n'a mesuré laquelle des trois bloque, ni dans quelle proportion.**

*Le mandat chiffre le même mur par l'autre bout* : **65 % d'ambiguïté sur la base complète, 0,8 % d'entreprises vérifiées au bout**, et un premier envoi réel parti vide — **953 signaux correspondaient au profil, aucun ne portait sur une entreprise que le produit accepte de nommer.**

*C'est cette mesure qui dira si récupérer des NEQ rapporte vraiment.* Sans elle, on ne sait pas si 1 800 dossiers identifiés produisent 1 800 prospects ou une vingtaine.

⚠️ **ORDRE — décision d'Alexandre : APRÈS le bloc de l'import** *(section 17bis)*. *Le mur d'après se mesure une fois que ce qui a été gagné se regagne à chaque import, pas avant.* **Et le chiffre a changé d'échelle** : ce ne sont plus 1 800 dossiers identifiés mais **5 323** *(section 5bis)*, donc la question « produisent-ils des prospects ou une vingtaine » porte sur trois fois plus.
