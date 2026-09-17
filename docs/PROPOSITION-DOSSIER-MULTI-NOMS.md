# Un dossier qui porte plusieurs noms — état après les trois contraintes

*Rédigé le 2026-09-16, **révisé le même jour** après réception de trois
contraintes arrivées APRÈS l'ouverture de la demande #71. **Rien n'est
construit.** Ce document dit ce qui tient, ce qui tient moyennant un ajout, et
ce qui tombe.*

---

## ⚠️ Avant tout : ce que je tiens de la décision du 16, et ce que je n'ai pas

**La décision n'est écrite nulle part dans `docs/spec/`.** Vérifié : aucun
fichier du corpus ne porte « un dossier peut porter plusieurs noms » ni « aucun
nom ne se perd ».

**Ce que j'ai réellement sous les yeux :**

- `NOTES-A-CONSIGNER.md`, **N61 et N63** — *conservation plutôt que fusion*, et
  *le dossier le plus ancien porte le NEQ*. Écrites à partir des messages
  d'Alexandre des 15 et 16 septembre, **dans mon tampon, pas au corpus.**
- `NOTES-A-CONSIGNER.md`, **N65** — la direction multi-noms, transcrite de son
  message de ce soir.
- ⚠️ **N40, et elle mérite d'être rappelée** : le 15 septembre, **je
  recommandais la FUSION**, au motif que « la conservation n'existe pas, le
  schéma l'interdit ». *Alexandre a tranché contre ma recommandation.* La
  décision est donc la sienne de bout en bout, et je ne peux pas la recopier de
  mémoire comme si elle était mienne.

**Je travaille donc sur ce qu'en rapportent ses messages et mes notes, pas sur un
texte du dépôt.** *Si le plan de travail dit autre chose, c'est lui qui a
raison.*

---

## Les trois issues, déclarées

### ✅ CE QUI TIENT TEL QUEL

**1. Le recensement du coût — 55 lectures, ≈47 / ≈6 / 2.**
Il compte des lectures de `Company.nom_detecte` dans le code. *Quelle que soit
la forme que prend le pivot d'identité, ces 47 sites afficheront un nom et ces 6
en chercheront un.* **Aucune des trois contraintes ne le touche.**

**2. ⚠️ `scalar_one_or_none()` dans `_find_unresolved_company`.**
*C'est le plus urgent des trois, et il ne dépend d'aucune décision ouverte.* La
ligne lève si deux dossiers non résolus portent le même nom normalisé, et le
chemin de production y passe à chaque signal non résolu. **`doublons_entreprises`
famille 1 dit s'il est déjà violé.** À traiter indépendamment de tout le reste.

**3. La correction des collisions dans `reresolution_neq` et les deux mesures.**
Elles opèrent sur la structure d'aujourd'hui, et leur validité n'en dépend pas.

### ⚠️ CE QUI TIENT MOYENNANT UN AJOUT — et l'ajout est fait

**Les deux mesures — leur périmètre est la moitié privée d'une population qui en
compte deux.**

*Cas 33 : « un instrument mesure ce qu'il a été construit pour mesurer; son zéro
ne dit rien de ce qu'il ne regarde pas », et « sa portée s'écrit à côté de sa
sortie, pas dans sa documentation ».*

**Ce que `rejeu_resolution` et `doublons_entreprises` mesurent
EXACTEMENT :** les `Company` du produit, résolues contre **le REQ**, qui est le
registre des entités **privées**. *Sur ce périmètre, la mesure est entière et
valable.*

**Ce qu'elles NE couvraient pas, et ne pouvaient pas couvrir :**

- **les entités publiques** — aucun registre pivot n'est choisi (**D27 ⬜**),
  aucune règle de classement n'existe (**D28 ⬜**);
- **les donneurs d'ouvrage du SEAO** — ils n'existent **comme entité nulle
  part** dans le produit (**D43 ⬜**), donc aucune ligne les concernant n'entre
  dans le compte;
- **la famille d'entité** — la structure actuelle ne la porte pas.

*Et le mandat chiffre précisément ce que ça écarte : sur le SEAO, l'identifiant
de l'organisme acheteur est présent à **100 %**, celui du fournisseur n'est
jamais un NEQ — **56 % d'ambiguïté sur les entreprises, zéro sur les organismes
publics**.* **La population où l'appariement est difficile est exactement celle
que ces deux outils mesurent; celle où il est trivial en est absente.**

**L'ajout :** les deux outils **impriment ce périmètre en tête de leur sortie**,
et deux tests l'exigent. *La prescription du cas 33 est « à côté de la sortie » —
pas dans ce document.*

### ⛔ CE QUI TOMBE

**`company_noms` comme structure DÉFINITIVE.**

Ma proposition accroche les noms à `company_id` et **suppose que `Company.neq`
reste le pivot de l'identité**. Le mandat dit l'inverse, noir sur blanc
*(chantiers 3+4)* :

> « **la clé du moteur cesse d'être un identifiant de territoire** »
> « Une **identité interne**, distincte de tout identifiant externe […] Une table
> d'**identifiants externes** rattachés, chacun avec son territoire, sa source et
> sa date — zéro, un ou plusieurs »

**Donc la table des noms ne se rattache pas au dossier tel qu'il est : elle se
rattache à l'identité interne du chantier 3, à côté de la table des
identifiants externes — et la famille d'entité s'ajoute au territoire.**

*La FORME reste bonne — `(identité, nom_normalisé)`, avec `nom`, `source_id`,
`first_seen_at`, symétrique de `req_noms`. Ce qui tombe, c'est son point
d'accrochage et le moment de la construire.* **Le mandat chiffre le report :
« le faire maintenant coûte presque rien; le faire après, c'est migrer deux fois
la même clé ».** La même phrase condamne de construire `company_noms` seule
maintenant : *ce serait une troisième migration de la même clé.*

---

## Les décisions ouvertes que ma proposition SUPPOSAIT

*Plutôt que de poser une valeur par défaut pour avancer, les voici nommées.*

| décision | ce que la proposition supposait |
|---|---|
| **D28** — règle de classement public/privé | ⚠️ **Mon étape 2 envoyait TOUT nom au REQ.** *C'est présumer que toute entité est privée* — exactement l'ambiguïté d'entité que D28 doit trancher avec une réponse par défaut. |
| **D29** — quel identifiant fait foi | Ma règle d'ancienneté décide quel dossier porte **le NEQ**. Dès qu'une entité peut porter deux identifiants, « qui porte quoi » est une question de D29, pas d'ancienneté. |
| **D27** — registre des entités publiques | Pas de présomption directe, **mais** : sans lui, une entité publique n'a aucun pivot, donc « lui apparier des noms » n'a pas de sens défini. |

**Aucune valeur par défaut n'est posée.** *La demande de mesure et de chiffrage
tient sans ces trois décisions; la structure définitive, non.*

---

## Les deux réserves du corpus, appliquées à la forme

### Cas 27 + cas 41 — ce qui l'exigerait mécaniquement

*Cas 27 : une règle portée par la discipline de chaque appelant n'est pas portée
— elle doit vivre à l'endroit qui ne peut pas être contourné. Cas 41 : le
correctif d'une convention n'est pas de la rappeler, c'est de la rendre
exigible.*

⚠️ **Ma proposition avait exactement ce défaut.** Elle décrivait deux points
d'écriture à étendre, et **rien n'obligeait un troisième, écrit le mois
prochain, à passer par la table des noms.** *C'est la garde recopiée à la main,
une table plus loin — et elle a coûté quinze outils sur vingt-huit il y a six
heures.*

**Ce qui l'exigerait mécaniquement, et l'ordre est celui de la préférence :**

1. **Un seul chemin d'écriture du nom** — une fonction qui est la *seule* façon
   de nommer une entité, et qui écrit les deux endroits en un geste. *L'endroit
   qui ne peut pas être contourné.*
2. **Un test d'AST qui refuse toute affectation de `nom_detecte` hors de cette
   fonction** — même forme que `tests/test_imports_des_outils.py` et
   `tests/test_garde_cible_des_outils.py`, **tous deux vérifiés en les cassant
   aujourd'hui.** *C'est l'idiome du dépôt, et il a prouvé deux fois qu'il
   mord.*

*Le point 2 sans le point 1 est une vigilance outillée; le point 1 sans le point
2 est une convention.* **Il faut les deux.**

### Cas 34 — ce que je ne dois PAS étendre par symétrie

*« Une garde ne couvre que ce que la mesure couvrait. »*

⚠️ **Et j'avais commis l'extension.** L'étape 2 de ma proposition — *« élargir
les 6 points de recherche »* — était présentée comme une conséquence de la
décision du 16. **Elle n'en est pas une.** La décision porte sur la
**conservation des noms** : qu'aucun nom ne se perde, et qu'aucun dossier ne
soit supprimé.

**Conserver un nom et l'utiliser pour chercher sont deux gestes différents, et
le second a ses propres risques** : élargir la récupération augmente le nombre
de candidats, donc le nombre d'appariements ambigus et de **faux** appariements.
*Rien dans la décision du 16 ne dit qu'on accepte ce coût-là.*

**L'élargissement de la lecture et l'élargissement du dédoublonnage demandent
chacun leur propre démonstration**, chiffrée séparément. *Ils ne sont pas
acquis, et je les retire de la proposition.*

---

## Ce que je recommande maintenant

**Dans cet ordre, et les deux premiers ne dépendent d'aucune décision ouverte.**

1. **`scalar_one_or_none()`** — défaut vivant sur le chemin de production,
   indépendant de tout le reste.
2. **Les deux mesures**, en lisant leur périmètre imprimé.
3. **D27, D28, D29** — et la table des noms **avec** le chantier 3, jamais
   avant. *Une migration de moins.*

**Et si la pression est de récupérer les noms maintenant** : la table peut
naître **dans le miroir** plutôt que dans la base durable, comme `req_noms` —
elle y serait un index de recherche reconstructible, **sans rien promettre sur
l'identité**, et sa disparition ne coûterait rien. *Ce n'est pas la structure
définitive, et il faudrait l'écrire comme telle dans sa propre docstring.*
