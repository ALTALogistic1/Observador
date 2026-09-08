# Les miroirs — ce qui vit hors de la base durable, et comment le rebâtir

## Pourquoi deux bases

FALKYE écrit dans **deux** bases depuis le 6 septembre 2026.

| | Base du produit | Base des miroirs |
|---|---|---|
| Variable | `FALKYE_DB_URL` | `FALKYE_MIROIR_DB_URL` |
| Cible en production | base distante (Turso, HTTPS) | fichier local du serveur |
| Volume mesuré | moins de 3 000 lignes | 5,7 millions de lignes, ~2 Go |
| Se reconstruit ? | **non** | **oui**, procédure ci-dessous |

Le découpage n'est pas une préférence de rangement, c'est une mesure. L'import
du miroir REQ prend **33 minutes** sur un disque local et **environ 168 heures**
sur la base distante — le chemin d'import fait deux allers-retours par ligne
(mesuré : 2,00 énoncés SQL par ligne), à 111 ms l'aller-retour. Il consommerait
en plus 2,7 millions d'écritures facturées sur un quota mensuel de 10 millions.

Le rapport est de l'ordre de 300, et il porte sur 99,95 % du volume qui
représente **zéro pour cent de ce qui se perdrait**.

## Ce que chaque base contient

**Base des miroirs** — copies de sources externes et état de diff :
`req_entries`, `req_etablissements`, `corporations_federales_entries`,
`licences_municipales_entries`, `etat_ligne_source`, `etat_schema_source`,
`diff_run_historique`, `diff_quarantaines`.

**Base du produit** — tout le reste : profils, besoins, entreprises repérées,
signaux, notifications, jetons, résumés, journal d'exploitation.

L'appartenance est portée par la classe parente du modèle (`Base` ou
`BaseMiroir`, voir `falkye/models/base.py`), pas par une liste de noms qu'il
faudrait tenir à jour. `tests/test_deux_bases.py` verrouille la cible de chaque
table : déplacer une table fait échouer un test, dans les deux sens.

## Rebâtir la base des miroirs

**Quand.** Disque perdu, fichier corrompu, migration vers un autre serveur, ou
simplement pour repartir propre. Perdre ce fichier ne perd aucune décision ni
aucune observation du produit — seulement le temps de le refaire.

**Ce qu'on perd pendant ce temps, et qu'il faut savoir.** Sans miroir REQ, la
résolution NEQ échoue, donc chaque entreprise détectée reste `ambigu` ou
`non_trouve`, donc la vérification l'exclut et **aucune notification n'est
produite**. Le produit tourne, les cycles se terminent proprement, et le résumé
est vide. Rebâtir n'est donc pas facultatif : c'est ce qui décide si le produit
a quelque chose à dire.

### 1. Le fichier source

L'archive du Registraire des entreprises se télécharge chez
[Données Québec](https://www.donneesquebec.ca/recherche/dataset/registre-des-entreprises)
— environ 267 Mo, six fichiers CSV. Le téléchargement automatisé depuis un
hébergeur infonuagique est refusé par le pare-feu de l'origine (règle
Cloudflare), d'où la copie déposée en *release* du dépôt, dont l'empreinte
SHA-256 est publiée avec l'actif.

```bash
sha256sum JeuDonnees.zip     # doit correspondre au digest de la release
```

### 2. Le schéma

```bash
export FALKYE_MIROIR_DB_URL="sqlite:////var/lib/falkye/miroirs.sqlite3"
falkye init-db                              # crée les tables des DEUX bases
python outils/migration_colonnes.py         # rapporte la dérive des DEUX bases
```

### 3. L'import

```bash
falkye import-manuel fichier \
    --source-id req \
    --chemin /chemin/vers/JeuDonnees.zip \
    --importe-par votre@courriel \
    --pas-de-reprocess
```

`--pas-de-reprocess` évite de retraiter toutes les entreprises connues dans la
foulée : sur un rebâtissage, on veut d'abord le miroir, et le retraitement se
fait ensuite par un `falkye scan veille` ordinaire.

**Attendus, mesurés le 6 septembre 2026 sur l'édition du 1er septembre :**

| | |
|---|---|
| Durée | ~33 minutes |
| Lignes écrites | ~2,73 M |
| Pic mémoire | **3 535 Mo** |
| Disque occupé | ~2 Go |
| Signaux produits | **0**, et c'est normal — voir ci-dessous |

**Zéro signal au premier import est le comportement attendu**, pas une panne.
Tout est neuf, donc le moteur de diff n'a rien à quoi comparer et la prudence de
début de vie supprime tout. Les signaux apparaissent à partir de la DEUXIÈME
édition importée.

**Le pic mémoire est la contrainte à surveiller.** 3 535 Mo sur un serveur de
8 Go laisse de la marge, mais pas énormément une fois le système, le serveur
d'application et le cache comptés. C'est ce chiffre qui a rendu insuffisant le
serveur à 4 Go envisagé au moment de la commande.

### 4. Vérifier

```bash
python - <<'PY'
from sqlalchemy import func, select
from falkye.db import get_session
from falkye.models.req_entry import REQEntry
s = get_session()
total = s.execute(select(func.count()).select_from(REQEntry)).scalar()
avec_ville = s.execute(
    select(func.count()).select_from(REQEntry).where(REQEntry.ville.is_not(None))
).scalar()
print(f"{total:,} entrées, dont {avec_ville:,} avec ville ({100*avec_ville/total:.1f} %)")
PY
```

**Attendu : environ 2,7 millions d'entrées, dont ~66 % avec une ville.** Un taux
autour de 7 % signale que le correctif du 6 septembre sur l'indicateur de
dispense d'adresse n'est pas dans le code déployé — voir
`falkye/sources/req.py::_resoudre_entreprise`.

## Ce que le miroir coûte à chaque cycle

**⚠️ TROIS mesures, et chacune déplace le diagnostic de la précédente.** Elles
sont gardées toutes les trois : c'est l'écart entre elles qui porte
l'information, et le même code a trois régimes selon les conditions.

| | En développement | Hôte, amorçage | Hôte, **régime** |
|---|---|---|---|
| Durée | 92,5 min | 1 h 26 | **29 min 10 s** |
| Temps processeur | 41 min sur 41 — **100 %** | 19 min sur 86 — **22 %** | 1 min 43 s sur 29 — **6 %** |
| Pic mémoire | 428 Mo | 414 Mo | 396 Mo |
| Base du produit | fichier local | distante, ~111 ms | distante, ~111 ms |
| État de diff | amorcé | **à amorcer** | amorcé |
| Facteur dominant | le repli de résolution | la latence de la base | **l'enrichissement qui échoue** |

**Avant de conclure quoi que ce soit sur la lenteur d'un cycle, établir lequel
des trois régimes on observe.** Un profil mesuré dans l'un ne dit rien des deux
autres — c'est l'erreur commise deux fois ici.

**En développement, le cycle est limité par le processeur.** Douze prélèvements
sur quatorze tombent au même endroit : `falkye/sources/req.py`, le **repli par
sous-chaîne** de `resolve_neq_by_name`. Quand la recherche par préfixe ne rend
rien, le repli fait un `LIKE '%...%'` que SQLite ne peut pas indexer, donc un
SCAN des 2,7 millions de lignes :

| | |
|---|---|
| Préfixe indexé (`GLOB 'transport*'`) | 0,007 s — SEARCH via l'index |
| Repli par sous-chaîne (`LIKE '%boulan%'`) | 0,32 s — SCAN complet |

**Sur l'hôte à l'amorçage, il n'est plus le facteur dominant.** 78 % du temps est
de l'ATTENTE, pas du calcul. Le miroir y est local et rapide; ce qui coûte, c'est
la latence de la base du produit — un aller-retour par validation, et depuis le
7 septembre une validation par signal neuf.

**En régime, ce n'est plus la latence non plus.** Le cycle du 8 septembre :

    ingestion des 8 sources   13 min 07 s   ← le travail utile
    enrichissement web        16 min 03 s   ← des 403 en série

**Seize minutes sur vingt-neuf sont du temps passé à ÉCHOUER**, pas à travailler.
Et 6 % de processeur dit que le reste ne calcule presque rien : en régime, un
cycle vérifie surtout que rien n'a changé.

Ça change la nature du point 27.1 du mandat. Il n'était que « l'enrichissement
tourne pour chaque entreprise détectée, avant tout seuil » — du gaspillage
mesuré en appels. Il est devenu **la moitié de la durée d'un cycle, entièrement
dépensée en échecs**, depuis que le moteur de recherche répond 403 Forbidden
depuis l'hôte (et non plus des délais d'attente). À remonter dans l'ordre du
chantier 27.

**Ce que ça change au levier**, et c'est la raison de garder les deux mesures :
indexer autrement le repli optimiserait 22 % du temps. Le vrai gain serait de
réduire le NOMBRE d'allers-retours — valider par lots, vérifier les doublons en
une requête par lot plutôt qu'une par ligne.

**Mais ça entre en tension directe avec la validation par signal**, qui a déjà
sauvé de la donnée deux fois le même jour : un `SIGTERM` à 3 h, puis une erreur
d'entrée-sortie du serveur. Tout lot reste par ailleurs borné par les dix
secondes au-delà desquelles la base distante annule une transaction portant une
écriture (voir docs/DEPLOIEMENT.md), donc le lot se borne au TEMPS, pas au
nombre. **À mesurer avant de trancher. Rien n'est corrigé au 8 septembre 2026**,
et le prochain qui trouvera le cycle lent devra d'abord regarder lequel des deux
régimes il observe.

## L'état de diff

Il se rebâtit par un **run de référence** : le premier passage d'une source sur
une base d'état vide amorce l'état sans produire de signal. Aucune commande
dédiée — c'est le comportement normal du premier run, et c'est pour ça qu'un
état de diff perdu ne perd rien d'autre qu'un cycle de détection.

## Ce que ce découpage coûte, dit franchement

Une transaction ne couvre plus les deux bases. SQLAlchemy valide chaque moteur
l'un après l'autre, sans validation en deux phases : une panne entre les deux
laisse le miroir avancé et le produit non, ou l'inverse.

C'est acceptable **ici précisément parce que le miroir se rebâtit**. Ça ne le
serait pas entre deux tables du produit, et c'est la raison pour laquelle la
frontière passe exactement là.
