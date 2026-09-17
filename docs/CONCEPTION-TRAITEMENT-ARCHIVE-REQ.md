# Traiter l'archive REQ en entier — une direction, et le chiffre qui la borne

> **Conception.** Hors corpus — `docs/`, pas `docs/spec/`.
> ⚠️ **Le chiffre est en tête, et il ferme une piste.**

---

## LE CHIFFRE, ET IL SE TRANCHE SANS L'HÔTE

**Le traitement de l'archive récupérerait `0` dossier de plus par les noms EN VIGUEUR. Les 6 009 sont déjà en base, à la ligne près. Cette piste est CLOSE.**

**Ce n'est pas une lecture, c'est une identité.** `req_noms` est chargé depuis **le même fichier**, avec **le même filtre**, **le même nom de colonne** et **la même normalisation** que `impact_tous_les_noms` — vérifié au code :

| | `_charger_tous_les_noms` *(le pont)* | `impact_tous_les_noms` *(la mesure)* |
|---|---|---|
| fichier | `Nom.csv` du zip | `Nom.csv` du zip |
| clés lues | `NEQ`, `NOM_ASSUJ`, `STAT_NOM` | `NEQ`, `NOM_ASSUJ`, `STAT_NOM` |
| filtre | `STAT_NOM.upper() != "V"` → ignoré | `STAT_NOM.upper() != "V"` → ignoré |
| normalisation | `column_mapping.normaliser` | `column_mapping.normaliser` |
| forme vide | ignorée | ignorée |
| **déduplication `(NEQ, forme)`** | **oui** — clé composite + `OR IGNORE` | **non** — compte les lignes |

**Et l'arithmétique se referme sur l'écart de ~16 000 qui restait à expliquer :**

```
noms EN VIGUEUR annoncés par l'outil   1 521 816
paires (NEQ, nom normalisé) en double     15 937     ← entonnoir du 16 septembre
                                       ─────────
distinctes attendues                   1 505 879
req_noms en base, count(*)             1 505 879     ← IDENTIQUE
```

> ⚠️ **L'écart n'était pas des noms manquants. C'étaient les mêmes noms comptés deux fois** — deux `TYP_NOM_ASSUJ` portant la même graphie. **Le pont les déduplique; la mesure les additionne.**

**Donc le 6 009 ne représente aucun gain disponible.** *C'est un plafond d'appariement exact que le moteur ne produit pas* — et **on sait pourquoi, c'est mesuré** : la borne de récupération coupe 4 217 lots *(74,3 % des trop faibles)*, et la mesure C a montré que **114 des 152 dossiers testés franchissent le seuil dès que la borne est levée.**

**La clé de récupération reste donc le chantier.**

### La seule ligne qui renverserait ce verdict

**La ligne de provenance, en tête de la sortie d'`impact_tous_les_noms`.** *L'archive du 16 septembre est sortie hier; l'hôte porte encore celle du 2.* **Si l'outil a lu l'archive du 16 alors que le miroir porte celle du 2, les deux ensembles ne sont plus les mêmes et l'identité ci-dessus ne tient plus.** *Une ligne à lire, pas une mesure à relancer.*

---

## CE QUI RESTE VRAIMENT DE L'ARCHIVE, ET CE QUE ÇA VAUT

**L'inventaire réel du zip — six CSV, établi par inspection le 2026-08-31** *(`falkye/sources/req.py`, `docs/STATUT_RESEAU.md`, `inspect_zip`)* :

| fichier | lu aujourd'hui? | ce qu'il porte | ce qui reste dessus |
|---|---|---|---|
| `Entreprise.csv` *(~630 Mo)* | ✅ | NEQ, statut, adresse du domicile, secteur | rien d'identifiant |
| `Nom.csv` *(4 651 088 lignes)* | ⚠️ **un tiers** | tous les noms, en vigueur ou non | **3 129 272 lignes de noms PLUS EN VIGUEUR** |
| `Etablissements.csv` | ✅ | adresses, `NOM_ETAB` | **clos** — 5 récupérations sur 2 517 |
| `DomaineValeur.csv` *(~90 Ko)* | ⛔ | table code → libellé | qualité des libellés, **pas d'identité** |
| `FusionScissions.csv` | ⛔ | **relations NEQ → NEQ** | jamais regardé |
| `ContinuationsTransformations.csv` | ⛔ | **relations NEQ → NEQ** | jamais regardé |

**Deux natures, et il faut les séparer :**

**(a) Les noms PLUS EN VIGUEUR — 3 129 272 lignes.** *Même mécanisme que le pont* — un nom mène à un NEQ. **C'est la seule part de l'archive qui puisse rattacher des dossiers par le nom et qui ne soit pas déjà en base.**

**(b) Les deux fichiers de relations — NEQ → NEQ.** *Nature différente* : ils ne rattachent pas un nom à une entreprise, ils rattachent **une entreprise à celle qui lui a succédé**. ⚠️ **Ils ne servent que lorsqu'un NEQ MORT est déjà trouvé** — or notre échec est « aucun NEQ trouvé », pas « un NEQ périmé trouvé ». *Ils sont donc en aval de (a), pas à côté.*

### Le chiffrage de (a) — et il se fait sur l'instrument qui existe

⚠️ **Dans la même demande, pas dans une suivante.** `outils/impact_tous_les_noms.py` accepte maintenant `--tous-les-statuts`, et il rend **le gain NEUF** — *ce que le pont d'aujourd'hui n'atteint pas* :

```bash
sudo -u falkye bash -c 'set -a; . /etc/falkye/falkye.env; set +a; \
    cd /opt/falkye/code && /opt/falkye/venv/bin/python -m outils.impact_tous_les_noms \
    --chemin /opt/falkye/import --tous-les-statuts'
```

```
2bis. ⚠️ LE CHIFFRE QUI DÉCIDE — le gain NEUF du traitement

   « Neuf » veut dire : que le pont d'aujourd'hui N'ATTEINT PAS.

          …  déjà atteignable par un nom EN VIGUEUR — dans le pont
          …  ⇒ NEUF : atteignable SEULEMENT par un nom PLUS EN VIGUEUR   ←
          …  plusieurs NEQ anciens — ambigu par construction

   ⇒ GAIN NEUF DU TRAITEMENT DE L'ARCHIVE : … dossier(s)
```

**Et il rend le coût dans la même sortie**, comme le 16 septembre : les résolues qui verraient apparaître un concurrent. ⚠️ *Avec une forme de faux que le pont actuel n'a pas : **un nom plus en vigueur peut appartenir à une AUTRE entreprise aujourd'hui.***

---

## LA DIRECTION

**Indexer les noms PLUS EN VIGUEUR, dans `req_noms`, avec leur statut — et rien d'autre de l'archive.**

**Ce que ça change concrètement.** `_charger_tous_les_noms` cesse de jeter les lignes `STAT_NOM ≠ V` et les écrit avec leur statut réel. *La colonne `statut` existe déjà sur `REQNom` et porte déjà `"V"` — elle a été prévue pour ça.* **Aucun modèle à changer, aucune table à créer.**

⚠️ **Et le moteur doit pouvoir les distinguer.** *Un nom plus en vigueur n'a pas la même valeur qu'un nom en vigueur* — le traiter à l'identique ferait entrer du faux au même rang que du vrai. **C'est une règle, donc une décision d'Alexandre**, et la conception s'arrête à la poser : *soit `resolve_neq_by_name` ne les consulte qu'en second temps, soit leur score est plafonné.* **Ni l'un ni l'autre n'est écrit ici.**

### Le coût à l'import, et le pic mémoire

| | |
|---|---|
| **lignes ajoutées** | **3 129 272** *(pire cas : aucune n'est un doublon)* |
| **taille de `req_noms`** | ~1,5 M → ~4,6 M lignes, **~740 Mo** *(à 160 o/ligne, l'estimation que l'outil annonce déjà)* |
| **durée ajoutée** | la fourchette qu'`estimer_duree` rend, **×2** environ |
| **pic mémoire** | ⚠️ **INCHANGÉ** |

**Pourquoi le pic ne bouge pas, et c'est vérifiable au code.** `_charger_tous_les_noms` lit `Nom.csv` **en flux**, écrit par lots de `_INTERVALLE_COMMIT_NOMS`, et **vide son ensemble `vus` à chaque lot**. *Trois fois plus de lignes traversent le même tuyau, sans que rien ne s'accumule.*

⚠️ **Ce qui porte le pic de 3 535 Mo est ailleurs, et ne change pas** : `_charger_index_etablissements` construit **un index NEQ → établissements entièrement en mémoire**. *C'est le poste à surveiller, il est déjà là, et cette conception n'y touche pas.*

### Ce qui échouerait BRUYAMMENT — et un défaut actuel à corriger avec

**Le garde-fou des colonnes existe déjà et il est bon** : `_LECTEURS_PAR_CSV` associe chaque CSV à sa fonction, et `colonnes_brutes_lues` extrait **par lecture de l'arbre syntaxique** les en-têtes que cette fonction lit réellement — *jamais une liste recopiée à côté, qui se désynchroniserait à la première colonne ajoutée.* **Un nouveau lecteur non déclaré dans cette table sort de la vérification, et le commentaire le dit.**

⚠️ **Mais deux modes de panne restent, et ce sont exactement ceux qu'Alexandre veut éliminer.**

**1. Le filtre échoue FERMÉ, en silence.** *Aujourd'hui* :

```python
if (row.get("STAT_NOM") or "").strip().upper() != "V":
    continue
```

**Si `STAT_NOM` est renommée, `.get` rend `None`, la comparaison est vraie pour TOUTE ligne, et `req_noms` se vide.** *L'import rend `0 noms indexés` et se déclare réussi.* ⚠️ **Un pont vide ressemble à une archive plus petite, pas à un défaut** — et c'est le motif le plus coûteux du projet.

> **Remède par conception : un PLANCHER par fichier.** *La part retenue sur les lignes lues est bornée* — `Nom.csv` rend aujourd'hui ~32,7 % de lignes en vigueur, et le traitement porterait cette part à ~100 %. **Une part qui s'effondre est un refus bruyant, pas un compte plus petit.** *Et le seuil ne s'invente pas : il se pose au registre des sources, avec les seuils de quarantaine que le chantier 1 a déjà construits — un retrait anormal met la source en quarantaine, il ne réduit pas le miroir.*

**2. Un fichier qui APPARAÎT n'est pas vu.** *Le garde couvre les colonnes des fichiers qu'on lit; il ne dit rien d'un septième CSV.* `FICHIERS_REQ_REELS` vérifie une **présence**, jamais une **absence d'inattendu**.

> **Remède : l'inventaire du zip est comparé à un inventaire DÉCLARÉ**, et tout membre inconnu est **journalisé comme un changement de schéma** — donc traité par la quarantaine, pas ignoré. *`inspect_zip` fait déjà le travail coûteux : en-tête et une ligne d'exemple par membre, quelques kilo-octets, sans décompresser.*

### Les trois éditions nommées, et ce qui les traverse

**Ce qui est conçu ici ne dépend d'aucune particularité d'édition** : *pas d'ordre de fichier* — chaque membre est ouvert par son nom; *pas de colonne facultative* — les quatre clés lues sont vérifiées par en-tête avant lecture; *pas d'encodage observé une fois* — `utf-8-sig` avec `errors="replace"`, déjà en place.

**Ce qui se reconstruit à chaque import** : la totalité de `req_noms`, par `OR IGNORE` sur la clé composite. **Rien ne se recalcule à la lecture.** *Une édition qui ne porterait plus un nom laisse la ligne en place — c'est un défaut existant du mode upsert, et il n'empire pas ici; il devient visible le jour où l'édition du miroir existe.*

---

## L'ÉDITION DU MIROIR — ce qui manque au modèle, et qui se pose ici

⚠️ **Elle n'existe nulle part.** *Deux archives par mois, le 2 et le 16 — et rien ne peut dire qu'une tentative a échoué contre celle du 2 septembre.* **Donc rien ne sait qu'il faut réessayer après un import**, et c'est la moitié manquante du cercle : la résolution ne répare pas, et personne ne sait quand il faudrait la relancer.

**La forme proposée — une table du miroir, une ligne par import :**

```
req_editions
   id               … clé technique
   empreinte        … l'IDENTITÉ de l'édition  ⚠️ voir ci-dessous
   importee_le      … horodatage
   lignes_par_fichier … le compte retenu et le compte lu, par CSV
   part_retenue     … ce qui alimente le PLANCHER ci-dessus
```

⚠️ **L'empreinte ne doit PAS être le nom du fichier.** *Un humain renomme, télécharge deux fois, garde une copie.* **Elle se calcule sur le contenu, et sans décompresser** : les `file_size` et les `CRC` des membres CSV, lus dans le répertoire du zip. *`zipfile` les expose déjà, `inspect_zip` les lit déjà.* **Deux archives identiques rendent la même empreinte; deux éditions différentes ne peuvent pas la partager.**

**Ce que ça débloque, et rien de plus** : le journal des tentatives `(forme normalisée, empreinte d'édition, verdict)` de la conception du deux-temps. *Une tentative vaut pour une édition; un import neuf l'invalide tout seul, par la clé.* **Pas de purge, pas de tâche d'entretien.**

---

## LA NON-RÉGRESSION SUR LES 805 — un critère, pas un effet secondaire

**Le risque est identifié et il est d'une seule sorte** : *ajouter des noms ajoute des candidats, et des candidats resserrent l'écart au second.* **Un dossier retenu aujourd'hui dont un concurrent apparaît bascule vers l'ambigu et SE DÉRÉSOUT.**

**Ce qui le mesure existe et sort dans la même commande** : la section 3 d'`impact_tous_les_noms`, *« entreprises DÉJÀ RÉSOLUES qui verraient un concurrent »*. **Le 16 septembre, sur les noms en vigueur : 65 menacées pour 6 009 gains — 92 pour 1.** ⚠️ *Ce rapport n'est PAS transposable aux noms plus en vigueur*, parce qu'un ancien nom peut aujourd'hui appartenir à quelqu'un d'autre : **le rapport se relit dans la même sortie, avec le gain neuf, ou la construction ne part pas.**

**Et le critère de fermeture se formule en une phrase** : *le traitement est acceptable si le rapport gain neuf / résolues menacées reste du même ordre que 92 pour 1, et il est refusé s'il approche de 1 pour 1* — **le chiffre exact du refus est une décision d'Alexandre, pas une constante à enfouir.**

---

## CE QUE CETTE CONCEPTION NE DIT PAS

**Qu'un appariement par un nom plus en vigueur soit JUSTE.** *Un nom abandonné peut avoir été repris.* **C'est une forme de faux que le pont actuel n'a pas, et aucune mesure ne la couvre.**

**Et elle ne touche pas aux échelles** : seuil **92**, écart **8**, borne **2 000**.
