# Un dossier qui porte plusieurs noms — proposition, non appliquée

*Rédigé le 2026-09-16, à la demande d'Alexandre. **Rien n'est construit.**
Ce document répond à trois questions dans son ordre : ce que ça rapporte, ce que
la forme coûte, et quelle structure.*

---

## 1. Ce que ça rapporte — à mesurer, pas à annoncer

`outils/apport_noms_multiples.py` le chiffre. **Aucun nombre n'est écrit ici** :
celui d'hier a été mesuré contre un pont que personne n'empruntait, et celui
d'avant-hier contre une colonne cassée.

```bash
python3 -m outils.apport_noms_multiples --exemples 20
```

Il sépare trois choses que la forme actuelle confond :

- **ce que la résolution TROUVE** — inchangé par la forme;
- **ce que la forme actuelle peut en FAIRE** — un NEQ libre, un dossier;
- **ce qu'un dossier à plusieurs noms en ferait** — tout NEQ retenu devient un
  rattachement, qu'il soit libre ou déjà porté.

⚠️ **Et un chiffre qui recadre la question.** L'outil rapporte les **NEQ
DISTINCTS** visés par les 8 931. *Si les 8 931 dossiers désignent beaucoup moins
d'entreprises réelles, « 8 931 entreprises sans identité » n'est pas la bonne
phrase.* **Un compte de dossiers répond « combien de lignes », jamais « combien
d'entreprises ».**

---

## 2. Ce que la forme coûte — 55 lectures, et seulement 8 qui comptent

`grep nom_detecte falkye/` rend **55 points de lecture**. *Le chiffre brut fait
peur et il est trompeur* : ils se rangent en trois familles, et deux d'entre
elles ne bougent pas.

### Famille A — AFFICHER (≈ 47 points) : **rien à changer**

`premier_contact.py` (18), `cli.py` (5), `engine.py`, `summary.py`,
`notifications/formatter.py`, `liens.py`, `web/app.py`…

**Et l'idiome est déjà le bon partout où le dossier est résolu :**

```python
nom = company.nom_officiel_req or company.nom_detecte
```

*Le portrait affiche déjà le nom légal du registre en priorité* — c'est la règle
posée le 15 septembre, et **elle est renforcée, pas défaite**. Un dossier qui
gagne des noms n'affiche pas plus de noms : il affiche toujours celui du
registre.

⚠️ **UNE exception, et elle mérite d'être nommée.** `premier_contact.py` écrit
`company.nom_detecte` **sans** passer par `nom_officiel_req` — 18 fois, dans le
texte d'un courriel adressé à un humain. *C'est le seul endroit où un mauvais
nom coûte la crédibilité plutôt qu'une ligne de journal.* **Cette incohérence
existe déjà aujourd'hui** : elle n'est pas créée par la proposition, elle est
révélée par elle.

### Famille B — CHERCHER (≈ 6 points) : **c'est là qu'est le gain**

`dedup_entreprises.py` (requêtes préfixe/sous-chaîne, score),
`resolution.py::requete_nom_exact`.

**Ce sont les seuls points à élargir, et les élargir EST le gain.** Six endroits,
tous concentrés, tous déjà extraits en fonctions nommées pour être empruntés.

### Famille C — ÉCRIRE (2 points) : `resolution.py` lignes 106 et 127

Où le nom est posé à la création du dossier.

### ⚠️ Le vrai coût n'est aucun des trois : c'est une ligne

```python
# falkye/resolution.py::_find_unresolved_company
trouve = db_session.execute(requete_nom_exact(nom_norm)).scalar_one_or_none()
```

**`scalar_one_or_none()` LÈVE si deux dossiers non résolus portent le même nom
normalisé.** C'est l'invariant que la forme neuve casse — *un dossier qui gagne
un nom peut se mettre à porter le nom d'un autre dossier*, et le chemin de
production passe ici à chaque signal non résolu.

**Cet invariant n'est écrit nulle part.** Ni dans le corpus, ni dans une
docstring : il vit dans le choix d'un appel SQLAlchemy. *C'est la réponse à
« quelle règle dois-je défaire » — ce n'est pas une règle du corpus, c'est une
hypothèse tacite du code.*

**Et il est peut-être DÉJÀ violé.** `outils/doublons_entreprises.py` (famille 1)
compte exactement les groupes qui le violeraient. **La mesure qu'Alexandre lance
ce soir répond à cette question-là aussi.**

---

## 3. La structure proposée — `company_noms`, symétrique de `req_noms`

### La forme

Une table rattachée au dossier, **exactement comme `req_noms` l'est au miroir** :

| colonne | rôle |
|---|---|
| `company_id` | le dossier |
| `nom_normalise` | la clé de recherche |
| `nom` | la graphie d'origine, telle que reçue |
| `source_id` | **qui a nommé l'entreprise ainsi** |
| `first_seen_at` | quand ce nom est apparu |

Clé primaire `(company_id, nom_normalise)` — la même que `req_noms`.

### Pourquoi cette forme et pas une autre

**1. `nom_detecte` NE BOUGE PAS.** Il reste la colonne du dossier, donc
**aucune des 47 lectures d'affichage ne change**, et aucune migration de données
n'est nécessaire pour qu'elles continuent de marcher. *La table est ADDITIVE.*

**2. La règle de `req_noms` s'applique telle quelle :** *« la table sert à
TROUVER, jamais à NOMMER »*. Elle est déjà écrite, déjà acceptée, déjà testée
une fois. **La symétrie est l'argument** : le miroir et le dossier auraient la
même forme pour le même problème, et un lecteur qui comprend l'un comprend
l'autre.

**3. `source_id` est le champ qui n'existe pas côté miroir, et il faut l'avoir.**
Le registre publie des noms; le produit, lui, **les reçoit de sources qui se
trompent**. Savoir que « Annexair Inc » vient du SEAO et « Annexair inc. » de la
RBQ est ce qui permettra plus tard de dire *quelle source écrit mal les noms* —
et c'est une mesure qu'on ne pourra jamais refaire après coup si la colonne
n'existe pas.

### Ce que la structure ne fait PAS

- ⚠️ **Elle ne fusionne rien.** Un dossier qui porte plusieurs noms ne supprime
  aucun dossier. *La conservation est intacte* — c'est même elle qui rend la
  proposition sûre.
- **Elle ne change pas le NEQ.** `Company.neq` reste `unique=True` : une
  entreprise, un dossier porteur. La table ajoute des portes, pas des identités.
- **Elle ne décide pas quel nom afficher.** `nom_officiel_req or nom_detecte`
  continue de répondre.

### Les trois étapes, si la direction est retenue

1. **La table et son remplissage** — chaque `Company` reçoit son `nom_detecte`
   comme premier nom. *Migration sans perte, réversible : la table peut être
   vidée sans que rien du produit change.*
2. **Élargir les 6 points de recherche** — et **c'est ici que le gain arrive**,
   pas à l'étape 1.
3. ⚠️ **Traiter `scalar_one_or_none()` AVANT l'étape 2**, jamais après. *Sinon
   l'élargissement met une exception sur le chemin de production.*

**L'ordre n'est pas négociable, et l'étape 3 est la seule qui touche un chemin
qui tourne aujourd'hui.**

---

## 4. Quelle règle du corpus change?

**Aucune.** Et c'est la réponse honnête, pas une esquive.

| règle | sort |
|---|---|
| « le portrait affiche le nom légal du registre, jamais le nom apparié » | **renforcée** — c'est elle qui rend les 47 lectures immobiles |
| « la table sert à TROUVER, jamais à NOMMER » *(`req_noms`)* | **étendue** au dossier, mot pour mot |
| conservation plutôt que fusion | **intacte**, et c'est elle qui rend la proposition sûre |
| « le PRINCIPAL est toujours le dossier le plus ANCIEN » | **intacte** |

**Ce qui change est en dessous du corpus : une hypothèse que personne n'a
écrite** — *« un nom normalisé désigne au plus un dossier non résolu »* — et qui
n'existe que sous la forme d'un `scalar_one_or_none()`.

⚠️ **C'est la leçon à en tirer, et elle vaut plus que la structure.** *Les
hypothèses les plus coûteuses à défaire ne sont pas celles qu'on a écrites comme
règles : ce sont celles qu'on a écrites comme appels de fonction.* Une règle du
corpus, on la relit et on la discute. Un `scalar_one_or_none()`, on le découvre
en le cassant.
