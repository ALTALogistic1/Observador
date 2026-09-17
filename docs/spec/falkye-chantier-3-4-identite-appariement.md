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

**Les deux échelles ne bougent pas** : seuil de confiance **92**, écart minimal au second **8**. Elles se changent avec Alexandre, jamais dans une demande de mesure.

---

## 5. Phase 0 — l'état mesuré

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

## 10. Faits acquis, avec leur preuve

**La contrainte d'unicité est portée par la base de production.** Prouvé par l'échec du 16 septembre — `UNIQUE constraint failed: companies.neq`. *C'est l'inverse exact du cas 25, où une garantie déclarée au modèle était absente en base.*

**`scalar_one_or_none()` ne peut pas lever.** Mesuré le 17 septembre sur la colonne que la production interroge (`companies.nom_detecte_normalise`) : **0 forme partagée, 0 forme vide** sur 8 931 dossiers sans NEQ. *Ce zéro dit que le défaut n'est pas survenu, pas qu'il est impossible — la borne sans ordre du dédoublonnage peut créer cette condition demain. Le correctif reste pertinent; il cesse d'être urgent.*

*Ce qui protégeait le chemin n'était pas une garde : un nom normalisé identique score 100, au-dessus du seuil de fusion à 95, donc le doublon était absorbé par le rapprochement flou. **Conformité accidentelle — cas 27.***

**L'échec de la passe de re-résolution n'était pas dû aux 69 NEQ déjà pris.** Le code les écartait déjà, journalisés, jamais posés. La cause était **les collisions internes au lot** — deux dossiers visant le même NEQ libre — corrigée par la demande #71. *Nuance : les 69 étaient traités correctement en logique, mais leur journalisation est partie avec le retour arrière. L'effet net était tout-ou-rien; la cause ne l'était pas.*

**La passe n'est pas un acompte** : 705 posables recalculés, contre 736 à l'instantané du 16. Plus petit. *Et la passe recalcule sa propre liste — le risque n'est pas qu'elle applique une vieille liste, c'est qu'on décide sur un vieux chiffre.*

**Toute société exerçant au Québec doit avoir un NEQ.** Vérifié à la source le 16 septembre (gouvernement du Québec et trois cabinets) : une société constituée au fédéral ou à l'étranger qui exerce une activité ou possède un établissement au Québec **doit s'immatriculer au REQ dans les 60 jours** et y déclare les mêmes renseignements qu'une société québécoise.

⚠️ **Conséquence, et elle retourne la question de départ.** Il n'y a pas d'impossibilité structurelle : **ces entreprises devraient presque toutes être au registre.** Le mur n'est pas qu'il n'y ait rien à trouver — c'est qu'on ne trouve pas ce qui est là. *Corporations Canada est écarté comme pont d'identification : une entreprise qui exerce au Québec a déjà un NEQ.*

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

9. **La passe de reprise**, seul mécanisme qui répare un dossier existant *(section 6)*. Elle existe en lecture seule; son application n'est pas décidée.

⚠️ **Ordre imposé.** **D27, D28 et D29 se tranchent avant les points 1 et 2.** *La structure du dossier à plusieurs noms attend le même moment* — sa forme survit, son point d'accrochage tombe *(section 17, et `docs/PROPOSITION-DOSSIER-MULTI-NOMS.md`)*.

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
- Le code postal : le second terme qui se recouvre entre l'EIMT et le REQ, **jamais regardé**.
- La trace sur un nom ordinaire — la réserve sur le préfixe parlant, encore non testée sur un cas réel.
- La normalisation des municipalités sur les 612 sans concordance. *Observation non mesurée : une part semble relever de l'écriture — « St-Apollinaire » contre « Saint-Apollinaire ».*
- L'alias de la RBQ, jamais mesuré.

**En décision d'Alexandre**
- La promotion de la ville vers le dossier (1 111 dossiers).
- L'application de la passe de reprise sur les 705.
- L'écart minimal : 2 097 dossiers à écart 4, au prix de 2 097 décisions machine entre deux entités.
- **D27, D28, D29** — préalables à la conception de la clé.
- L'ordonnancement et le filtrage du registre : hypothèse d'Alexandre du 16 septembre, appuyée par la saturation mesurée. *Conception à deux, non commencée.*

**En conception, non commencé**
- **Tout le chantier 3.** L'identité interne, la table d'identifiants externes, la famille d'entité, le niveau de vérification par couple identité × territoire.
- La structure du dossier à plusieurs noms. `company_noms` est tombée **comme structure définitive** — elle accrochait les noms à `company_id` et supposait `Company.neq` comme pivot, alors que le mandat dit que la clé du moteur cesse d'être un identifiant de territoire. **La forme survit** — `(identité, nom_normalisé)` avec `nom`, `source_id`, `first_seen_at` — son point d'accrochage et son moment tombent. *Détail dans `docs/PROPOSITION-DOSSIER-MULTI-NOMS.md`.*

⚠️ **Où vivent les noms — à trancher.** Trois structures peuvent porter la même correspondance : `req_noms` (miroir, 1 505 879 paires), la table d'apprentissage du chantier 4, et le dossier lui-même. *Charte : un point vit à un seul endroit.*

---

## 18. Le mur d'après

Le chantier 3+4 récupère des identités. **Il ne dit pas ce qu'elles valent.**

Sur les entreprises qui ont **déjà** un NEQ, une centaine seulement passe la vérification complète — statut légal, signe d'activité, cohérence d'identité. **Personne n'a mesuré laquelle des trois bloque, ni dans quelle proportion.**

*Le mandat chiffre le même mur par l'autre bout* : **65 % d'ambiguïté sur la base complète, 0,8 % d'entreprises vérifiées au bout**, et un premier envoi réel parti vide — **953 signaux correspondaient au profil, aucun ne portait sur une entreprise que le produit accepte de nommer.**

*C'est cette mesure qui dira si récupérer des NEQ rapporte vraiment.* Sans elle, on ne sait pas si 1 800 dossiers identifiés produisent 1 800 prospects ou une vingtaine.
