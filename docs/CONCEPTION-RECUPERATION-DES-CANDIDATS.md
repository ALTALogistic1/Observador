# Présenter au scoreur un lot qui contient le bon candidat

> **Conception, pas construction.** Quatre directions départagées sur cinq axes, aucune retenue.
> **Alexandre tranche la direction avant qu'une ligne soit écrite.**
>
> Hors corpus — `docs/`, pas `docs/spec/`. Ce qui en sortira ira au chantier 3+4 par demande de fusion.

---

## Ce que C a établi, et la réserve qui voyage avec

```
FRANCHISSENT LE SEUIL DE 92 une fois la borne levée : 114 sur 152  (75,0 %)
par famille d'origine : trop faible — 114
```

**Les 4 733 « trop faibles » ne sont pas des dossiers sans correspondance** — ce sont des dossiers **dont la correspondance n'a jamais été présentée au scoreur.** Le plancher à 85,50, qui pèse 89,2 % du pic, était le score d'un candidat pris par défaut dans une mauvaise tranche.

⚠️ **75 % est un PLANCHER.** 48 dossiers sur 200 ont été refusés faute de gisement sous 120 000 lignes — `l` (309 788), `s` (221 412), `le` (205 071). **Ce sont exactement les cas où la borne fait le plus mal**, donc le chiffre porte sur les cas les moins sévères.

⚠️ **Et un franchissement n'est pas un appariement juste.** C établit que **le lot borné ne contenait pas ce candidat**, rien de plus. *La validation des paires reste un geste distinct, et aucune des quatre directions ne la remplace.*

---

## Le fait qui oriente tout : la clé de récupération est un MOT VIDE

**Les préfixes refusés par C ne sont pas des noms rares. Ce sont des articles et des initiales**, produits par `normaliser` qui remplace l'apostrophe et le point par une espace :

| nom publié | forme normalisée | préfixe de récupération |
|---|---|---|
| `L'INDUSTRIE MONDIALE DU NORD INC.` | `l industrie mondiale du nord inc` | **`l`** |
| `Les Habitations KTP` | `les habitations ktp` | **`les`** |
| `S.E.N.C. Beaulieu et Fils` | `s e n c beaulieu et fils` | **`s`** |

> **La récupération s'ancre sur le premier mot, et le premier mot est celui qui ne dit rien.** *`industrie`, `mondiale`, `nord`, `habitations`, `beaulieu` sont dans la chaîne et ne servent à rien.*

**C'est l'axe de départage des quatre directions** : celle qui utilise les autres mots règle les cas que C a dû refuser; celle qui ne les utilise pas règle `ferme` et laisse `le`.

### Et le coût dominant n'est pas le SQL

Par résolution, aujourd'hui *(`falkye/sources/req.py`)* : deux `GLOB` indexés bornés à 2 000, deux replis par sous-chaîne possibles *(balayage complet)*, une jointure par NEQ, **puis `process.extractOne` sur ~2 000 groupes avec toutes leurs formes.**

**Le coût est dans le SCORAGE FLOU, proportionnel au nombre de formes présentées.** *Lever la borne sur `l` ne multiplie pas une requête : il multiplie par 155 le nombre de formes à scorer.* **Toute direction qui RÉDUIT le nombre de formes présentées est moins chère qu'aujourd'hui, pas plus.**

---

## Direction 1 — un index par MOTS

**Ce qu'elle change dans la récupération.** Au lieu de `nom_normalise GLOB 'l*'`, on récupère les formes qui **partagent un mot** avec le nom détecté — et on choisit **le mot le plus rare**, celui dont la fréquence documentaire est la plus basse. *`ferme leger parent` se récupère par `parent`, pas par `ferme`.*

Deux mises en œuvre, et elles ne se valent pas sur l'axe des éditions.

### 1a — FTS5

`CREATE VIRTUAL TABLE … USING fts5(forme)` sur `nom_normalise`, requête par mots, `ORDER BY rank` (BM25) `LIMIT 2000`.

⚠️ **1a absorbe la direction 2** : `ORDER BY rank` **est** un tri par proximité, fourni par l'index.

### 1b — une table de mots, modélisée

`req_mots(mot, neq)` avec index sur `mot`, et `req_mots_frequence(mot, n)` pour choisir le plus rare. *Pas d'extension, entièrement dans SQLAlchemy, testable comme le reste.*

| | 1a — FTS5 | 1b — table de mots |
|---|---|---|
| **classement par pertinence** | fourni (BM25) | à faire soi-même, ou aucun |
| **dépendance** | ⚠️ FTS5 compilé dans le SQLite de l'hôte | aucune |
| **modélisation** | table virtuelle, SQL brut, hors `create_all` | un modèle ordinaire |
| **vérifié ici** | FTS5 **présent** en SQLite 3.45.1 *(venv de développement — **pas l'hôte**)* | sans objet |

**Coût par résolution.** *Une ou deux recherches indexées locales, puis le scorage flou sur un lot de taille `DF(mot le plus rare)`.* **Quand ce mot est discriminant, le lot est plus PETIT qu'aujourd'hui — donc moins cher qu'aujourd'hui.** ⚠️ *Quand le nom n'est fait que de mots courants — « les entreprises du québec » —, le lot reste gros et la borne mord encore.* **C'est le point aveugle de la direction 1, et il se mesure avant (mesure D).**

**Coût à l'import.** ~4,24 M de formes *(2 730 146 `req_entries` + 1 505 879 `req_noms`)* × le nombre de mots par nom. ⚠️ **Le nombre de mots par nom n'est pas mesuré** — c'est l'hypothèse qui décide du volume, et la mesure D le rend. *À 4 mots par nom : ~17 M de lignes de postings.* **L'écriture doit se faire en flux** : l'import a déjà connu un pic de 7,4 Go ramené à 3,9, et accumuler 17 M de tuples en mémoire le referait.

**Sur les cas refusés par C.** ⚠️ **C'est là qu'elle gagne tout.** `l industrie mondiale du nord` se récupère par `mondiale` ou `nord` au lieu de `l` : *le gisement de 309 788 lignes n'est jamais touché.* **La direction 1 est la seule des quatre qui règle `l`, `s` et `le` par construction plutôt que par volume.**

**Résistance au changement d'édition.** **Se reconstruit intégralement** à chaque import, à partir de `nom_normalise` — qui est une fonction pure du nom publié. *Aucune dépendance à un ordre de fichier, à une colonne facultative ou à un encodage.* Reconstruction **totale** (vider puis remplir), jamais incrémentale : *une reconstruction partielle laisserait une moitié périmée, et c'est invisible.*

> ⚠️ **La dégradation silencieuse qui la guette, et c'est la seule : deux découpeurs de mots.** *Si l'index découpe autrement que la requête — FTS5 `unicode61` d'un côté, `str.split()` de l'autre —, le rappel baisse sans qu'aucune erreur ne se produise.* **Remède : indexer `nom_normalise`, qui ne porte que `[a-z0-9 ]`, et découper des deux côtés avec la MÊME fonction empruntée** *(règle de `requete_nom_exact`, `neq_retenu`, `famille_de`)*. **Et un témoin à chaque import** : un jeu de noms connus doit se retrouver lui-même dans l'index; si un seul échoue, l'import refuse.

**Ce qu'elle casse.** *En REMPLACEMENT du préfixe, elle peut retirer des candidats que le préfixe trouvait* — donc les 805 retenus sont exposés. **En UNION avec le préfixe, elle ne peut qu'ajouter** — et ajouter des candidats resserre l'écart au second, donc **fait basculer des RETENU vers l'AMBIGU**. ⚠️ *C'est exactement la réserve d'Alexandre du 16 septembre sur le pont `req_noms`, et l'outil qui la mesure existe et n'a jamais été lancé : `outils/impact_tous_les_noms.py`.*

---

## Direction 2 — un tri par proximité au lieu de l'alphabet

**Ce qu'elle change.** Rien, si on la prend au mot — **et c'est le résultat.**

**Pour ordonner par proximité, il faut calculer la proximité.** Trois chemins, et deux sont fermés :

| chemin | état |
|---|---|
| une fonction de distance **en SQL** (`spellfix1`, `editdist3`) | ⛔ **absente** de ce SQLite *(3.45.1, vérifié)* — et une extension à compiler sur l'hôte est précisément la fragilité qu'Alexandre refuse |
| calculer en Python sur tout le gisement | ⛔ **c'est le coût de C**, par résolution |
| un ordre fourni par un INDEX | ✅ **c'est la direction 1a** |

> **La direction 2 n'est pas mauvaise : elle n'est pas séparable.** *Honnêtement mise en œuvre, elle est soit la direction 1a, soit la levée de borne qu'on veut éviter.*

**Un ordre indépendant de la requête ne peut pas être un ordre de proximité.** *Trier par longueur, par date, par NEQ rend le tirage reproductible — l'`ORDER BY` du 16 septembre le fait déjà — et jamais pertinent.*

---

## Direction 3 — retirer les entrées inutilisables du gisement

**Le « nettoyage » d'Alexandre. Chiffré plutôt que supposé, et l'arithmétique le range.**

| préfixe | gisement | vu aujourd'hui | après un retrait de 10 % | retrait nécessaire pour TOUT voir |
|---|---|---|---|---|
| `ferme` | 23 061 | 8,7 % | **9,6 %** | 91,3 % |
| `gestion` | 105 845 | 1,9 % | 2,1 % | 98,1 % |
| `les` | 163 296 | 1,2 % | 1,4 % | 98,8 % |
| `le` | 205 071 | 1,0 % | 1,1 % | 99,0 % |
| `s` | 221 412 | 0,9 % | 1,0 % | 99,1 % |
| `l` | 309 788 | 0,6 % | 0,7 % | 99,4 % |

> ⚠️ **Un nettoyage de 10 % fait passer `ferme` de 8,7 % à 9,6 %.** *Le retrait est un effet du SECOND ordre sur une borne multiplicative* — pour que la tranche couvre le gisement, il faudrait retirer 91 % à 99 % des lignes, ce qu'aucune règle de propreté ne justifie.

**Coût par résolution** : nul, voire légèrement meilleur *(moins de lignes à balayer)*. **Coût à l'import** : faible.

**Sur les cas refusés par C** : ⚠️ **elle ne les règle pas.** *Elle règle `ferme` un peu et laisse `le` — la moitié du problème, littéralement.*

**Résistance au changement d'édition.** ⚠️ **C'est la pire des quatre, et par une marge.** *Un filtre posé à l'import sur une colonne — `statut`, une forme juridique, un indicateur — supprime des lignes en silence le jour où cette colonne change de forme.* **Et son échec ressemble à une archive plus petite, pas à un défaut.**

> **Remède s'il fallait la retenir** : tout retrait passe par les seuils du moteur de diff et la quarantaine *(chantier 1)*, jamais par un filtre muet dans le chargeur. **Un retrait anormal doit mettre la source en quarantaine, pas réduire le miroir.**

**Ce qu'elle casse.** *Toute ligne retirée qui appariait aujourd'hui est un RETENU perdu.* Non-régression à mesurer, pas à supposer.

---

## Direction 4 — une récupération en DEUX TEMPS

**Ce qu'elle change.** Premier temps : le chemin d'aujourd'hui, inchangé. **Si `neq_retenu` rend un NEQ, on s'arrête.** Sinon, et seulement sinon, un second temps élargit.

> ⚠️ **C'est la seule des quatre qui garantit la non-régression PAR CONSTRUCTION.** *Les 805 retenus ne voient jamais le second temps — il ne s'exécute que là où le premier a échoué.* **Toutes les autres demandent une non-régression MESURÉE; celle-ci la rend impossible à violer.**

**Ce n'est pas une stratégie de récupération, c'est une structure de contrôle.** *Elle ne dit pas avec quoi on élargit* — elle dit **quand**, et **à quel prix**. Elle a donc besoin d'une des autres, et la direction 1 est celle qui tient le rôle.

**Coût par résolution.** **Zéro ajouté sur ce qui marche déjà.** ⚠️ *Et c'est là que la lecture facile se trompe.* **La résolution tourne par SIGNAL, pas par dossier** *(`resolve_company(db_session, raw)`)* — et comme **une résolution réussie n'écrit jamais dans le dossier qui a échoué**, *les mêmes échecs se represcrivent à chaque cycle.* **« Seuls les échecs paient » veut dire « les mêmes échecs paient, à chaque cycle, indéfiniment ».**

**Le correctif qui borne ce coût, et il est petit** : journaliser la tentative — `(forme normalisée, édition du miroir, verdict)`. *L'élargissement tourne alors une fois par NOM et par ÉDITION, pas une fois par signal.* ⚠️ **Préalable : « l'édition du miroir » n'existe pas aujourd'hui** — aucune marque de niveau instantané dans les modèles du miroir, seulement des dates par ligne. **Il faudrait la poser, et c'est elle qui rend l'invalidation automatique au réimport.**

**Coût à l'import** : nul en propre.

**Sur les cas refusés par C** : *dépend entièrement de l'élargissement.* Avec la direction 1 : réglés. Avec une borne levée : c'est le coût de C, acceptable **dans une passe de reprise en lot, jamais dans le cycle.**

**Résistance au changement d'édition** : ⚠️ **c'est du code, pas des données — rien ne se reconstruit, rien ne se dégrade en silence.** *Sauf le journal des tentatives, dont la clé porte l'édition et qui s'invalide donc tout seul.*

---

## Ce qui se combine, ce qui s'exclut

| | 1 index par mots | 2 tri par proximité | 3 nettoyage | 4 deux temps |
|---|---|---|---|---|
| **1** | — | **absorbée** par 1a | compatible, apport faible | ✅ **complémentaires** |
| **2** | absorbée par 1a | — | sans rapport | sans objet seule |
| **3** | compatible | sans rapport | — | compatible |
| **4** | ✅ **complémentaires** | sans objet seule | compatible | — |

**La seule paire qui fait un mécanisme complet est 4 ∘ 1** : *le deux-temps décide QUAND élargir et protège les 805; l'index par mots décide AVEC QUOI et règle `l`, `s`, `le`.*

**2 n'existe pas séparément** — elle est 1a ou elle est C. **3 est du second ordre** par arithmétique, et porte le pire mode d'échec silencieux des quatre.

---

## ⚠️ Ce qu'il faut mesurer avant d'écrire une ligne

**Mesure D — le pouvoir discriminant des mots.** *Pour chacun des 4 733 trop faibles* : les mots du nom détecté, la fréquence documentaire de chacun dans le miroir, celle du plus rare — **donc la taille du lot qu'un index par mots présenterait.**

Elle rend les trois chiffres qui départagent la direction 1 :

1. **la taille médiane du lot** — si elle est en centaines, la direction 1 est *moins chère* qu'aujourd'hui, pas plus;
2. **combien de dossiers n'ont AUCUN mot rare** — *c'est le point aveugle, et il est aujourd'hui inconnu*;
3. **le nombre de mots par nom** — l'hypothèse dont dépend tout le volume de l'index.

⚠️ **Et elle coûte ce que coûterait la construction de l'index, sans l'écrire** : *une passe de découpage sur les 4,24 M de formes.* **Donc elle mesure aussi le coût d'import de la direction 1, en le payant une fois.**

**Mesure E — le coût en ambiguïté, sur l'outil qui existe déjà.** `outils/impact_tous_les_noms.py`, écrit le 16 septembre pour la réserve d'Alexandre sur le pont, **n'a jamais été lancé.** *Il mesure exactement le seul risque des directions 1 et 3 : combien d'entreprises DÉJÀ RÉSOLUES verraient apparaître un concurrent.* **Un correctif qui gagne 114 et en perd 300 n'est pas un correctif.**

---

## Ce que je recommande, et ce n'est pas une décision

**4 ∘ 1b**, dans cet ordre : *le deux-temps d'abord, parce qu'il ne peut rien casser et qu'il est du code sans données; l'index par mots ensuite, parce qu'il est ce qui règle les cas refusés.* **1b plutôt que 1a** tant que FTS5 n'est pas vérifié sur l'hôte — *la table modélisée ne dépend de rien, et elle se teste comme le reste du produit.*

**3 se mesure, ne se construit pas** — l'arithmétique la range au second ordre, et sa version « filtre à l'import » est à refuser telle quelle.

⚠️ **Rien de tout cela ne se commence avant D et E.** *La direction 1 a un point aveugle non mesuré, et les directions 1 et 3 ont un coût en ambiguïté non mesuré. Les deux mesures existent ou tiennent en un outil.*

**Et les échelles ne bougent pas** : seuil **92**, écart **8**, borne de production **2 000**.
