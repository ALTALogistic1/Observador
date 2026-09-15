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
[Données Québec](https://www.donneesquebec.ca/recherche/dataset/registre-des-entreprises/resource/eac1b5f1-d8c0-4690-9c51-316d44ed9d94)
— environ 267 Mo, six fichiers CSV. Le téléchargement automatisé depuis un
hébergeur infonuagique est refusé par le pare-feu de l'origine (règle
Cloudflare), d'où la copie déposée en *release* du dépôt, dont l'empreinte
SHA-256 est publiée avec l'actif.

**L'archive est CONSERVÉE sur l'hôte, et sa date est dans son nom**
*(décision d'Alexandre, 2026-09-16)* :

    /opt/falkye/import/JeuDonnees-2026-09-02.zip

**Ce que ça change.** *Chaque mesure qui demandait l'archive obligeait à la
retélécharger — trois fois en deux jours, et on a changé de méthode chaque fois
pour l'éviter.* Le blocage Cloudflare ne touche que le **téléchargement**, pas la
lecture : **une archive déposée est relisible indéfiniment.** *L'import reste
manuel; les mesures cessent de l'être.*

⚠️ **Le revers, pris en connaissance de cause.** *Une archive conservée vieillit,
et dans trois semaines quelqu'un la relira en croyant mesurer l'état courant.*
C'est le motif du 16 septembre — Laval figé, l'adresse de l'EIMT, la table de
prix sans date : **un fichier figé qui ressemble à un fichier vivant.** La date
dans le nom est ce qui le neutralise : `outils/archives_req.py` la lit, calcule
l'âge, et **tout outil qui ouvre une archive imprime sa provenance avant son
premier chiffre.** Au-delà de 21 jours — une édition manquée — l'avertissement
dit combien d'éditions ont paru depuis.

⚠️ **La date vient du NOM, jamais de `mtime`** : un `scp` ou une restauration
réécrit la date de modification, et l'archive paraîtrait fraîche de jours qu'elle
n'a pas.

⚠️ **Une archive SANS date n'est pas traitée comme récente** — elle est utilisable
et **toujours signalée** : *son âge n'est pas nul, il est inconnu.*

**Rien n'est purgé automatiquement**, et c'est délibéré : une rotation silencieuse
recréerait le même défaut à l'envers — *un fichier qui disparaît sans que personne
l'ait décidé.* Le flux de déploiement rend un **inventaire** (`ls -lh`, `du -sh`,
`df -h`) à chaque passage; purger reste un geste. *~7 Go par an au rythme de deux
semaines, pour 66 Go libres.*

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

**Et le contrôle qui manquait** *(ajouté le 2026-09-16)*. Le nombre d'entrées et
le taux de ville ne disent **rien** de la colonne dont dépend toute la
résolution. Le 15 septembre, un miroir de 2 730 146 lignes à 66 % de villes —
donc « importé correctement » selon les deux contrôles ci-dessus — portait
**1 371 730 `nom_normalise` vides (50,2 %)**, et rien ne l'avait signalé :

    python3 outils/etat_champ_normalise.py

**Attendu : 0 ligne vide, 0 ligne absente, et « toutes les lignes examinées sont
CONFORMES ».** *Tout le reste veut dire que le miroir est chargé et inutilisable
— l'état le plus coûteux, parce qu'il a l'air du bon.*

## Le réimport du 16 septembre 2026 (soir) — tous les noms

**Ce qu'il apporte, mesuré avant de le lancer** *(`outils/impact_tous_les_noms.py`)* :

    entreprises sans NEQ                  8 931
      ├─ gains FRANCS                     2 218
      ├─ gagnés mais AMBIGUS                 12
      └─ sans effet                       6 701
    déjà résolues MENACÉES                   43
    rapport gains francs / menacées         52.0
    volume        1 705 806 lignes          ~+260 Mo      7 à 35 min

### ⛔ Ce que le réimport NE FERA PAS, et qu'il faut savoir avant

**Le réimport seul ne résoudra AUCUNE des 2 218.** `resolve_company` n'a que deux
points d'appel — l'ingestion d'un signal brut et l'import manuel — et **aucune
passe de re-résolution n'existe** *(registre D15)*. *Une entreprise déjà en base
n'est réessayée que si un NOUVEAU signal la concerne.*

**Conséquence pratique : mesuré le lendemain du réimport, le gain sera proche de
zéro**, et il serait facile d'en conclure que le correctif a échoué. *Ce ne serait
pas vrai — le miroir portera bien les noms; c'est le produit qui ne repasse
jamais.* **Les 2 218 se résoudront au fil des cycles, à mesure que leurs sources
les renomment** — ou d'un coup, le jour où une passe de re-résolution existe.
**Elle n'existe pas, et elle n'est pas dans ce réimport.**

### Avant de lancer — six vérifications

**1. Le minuteur est arrêté.** *Un cycle qui démarre pendant l'import lirait un
miroir à moitié écrit.*

    systemctl is-active falkye-cycle.timer     # attendu : inactive
    sudo systemctl stop falkye-cycle.timer

**2. Aucun cycle n'est en cours.**

    systemctl is-active falkye-cycle.service   # attendu : inactive

**3. L'espace disque.** *~260 Mo pour `req_noms`, et SQLite a besoin de place pour
écrire son journal en plus du fichier.* Compter **le double**, soit ~520 Mo libres.

    df -h /var/lib/falkye

**4. Le code de la #56 est sur l'hôte.** ⚠️ **Pas celui de la #55** : avec la #55
seule, `req_noms` se remplit et le score continue de comparer la dénomination
sociale — *la porte s'ouvre et le seuil reste infranchissable.*

    /opt/falkye/venv/bin/python -c \
      "from falkye.models.req_nom import REQNom; \
       from falkye.sources.req import resolve_neq_by_name; print('#56 présente')"

**5. L'archive, vérifiée sur ses en-têtes.** Deux secondes contre trente minutes.

    python3 outils/verifier_archive_req.py --chemin /opt/falkye/import

**6. Les témoins, capturés.** ⚠️ **AVANT, et il faut que ce soit avant** — faite
après, la capture relèverait l'état d'arrivée et ne comparerait rien.

    python3 outils/temoins_resolution.py --capturer \
        --vers /var/lib/falkye/temoins-2026-09-16.json

### Lancer

    sudo systemctl start falkye-miroir-req.service
    journalctl -u falkye-miroir-req.service -f

*Chercher dans le journal la ligne `noms en vigueur indexés dans req_noms`* —
c'est elle qui dit que la passe neuve a tourné. **Une absence de cette ligne veut
dire que le code déployé n'est pas celui de la #56.**

### Après — quatre contrôles, dans cet ordre

    python3 outils/temoins_resolution.py --verifier \
        --depuis /var/lib/falkye/temoins-2026-09-16.json
    python3 outils/etat_champ_normalise.py
    python3 outils/entonnoir_verification.py
    python3 outils/diagnostic_appariement.py --toutes --histogramme

**Le premier passe en tête, et pas par habitude.** *Il distingue une entreprise
qui s'est **dérésolue** — visible, réversible — d'une qui a **mal résolu**, dont
le dossier a changé d'identité en silence.* **Une mauvaise réponse est pire qu'une
absence de réponse**, et aucun des trois autres contrôles ne la verrait.

### Remettre le minuteur

    sudo systemctl start falkye-cycle.timer
    systemctl list-timers falkye-cycle.timer

⚠️ **Ne pas l'oublier.** *Un minuteur arrêté ne signale rien — la panne est un
mardi matin sans courriel, une semaine plus tard.*

## La reprise du 16 septembre 2026 — la marche, dans l'ordre

**Pourquoi ce réimport.** La moitié du miroir portait un `nom_normalise` vide, et
une partie du reste une valeur tronquée. *Conséquence : les 4 873 « candidats
trop faibles » — 58 % du mur d'appariement — sont pour l'essentiel des
entreprises que le produit trouve, qu'il a sous les yeux, et qu'il compare à des
chaînes mutilées ou vides.*

⚠️ **Aucun gain n'est annoncé ici, et c'est délibéré.** Une entreprise dont le bon
candidat scorait 66 va scorer 100; une entreprise que le miroir ne porte pas
reste bloquée. **Il n'y a pas un chiffre à promettre, il y a une mesure à
refaire** — celle du 15 septembre a été prise contre une colonne cassée et ne
vaut rien.

### 1. Le code d'abord, l'archive ensuite

Le garde-fou doit être **sur l'hôte** avant l'import, sinon il ne protège rien.

    sudo systemctl start falkye-deploiement.service   # ou docs/DEPLOIEMENT.md
    /opt/falkye/venv/bin/python -c \
      "from falkye.sources.req import refuser_si_colonnes_absentes; print('garde-fou présent')"

*Un `ImportError` ici veut dire que le déploiement n'a pas passé* — **ne pas
lancer l'import** : c'est exactement le défaut du cas 35 (une fusion faite, un
hôte qui ne l'a pas).

### 2. Vérifier l'archive AVANT de l'importer

La vérification porte sur les **en-têtes**, pas sur les lignes : deux secondes,
contre 33 minutes d'import et un miroir à refaire.

    /opt/falkye/venv/bin/python outils/verifier_archive_req.py \
        --chemin /opt/falkye/import

**Attendu : `aucune colonne déclarée absente`.** *Si une colonne sort ici,
l'import refusera de démarrer et la nommera — vérifier d'abord une virgule
oubliée entre deux noms de colonne (deux littéraux collés n'en font qu'un, et
`dict.get` rend `None` sans rien signaler) avant de conclure que le schéma du REQ
a changé.*

### 3. L'import

    sudo systemctl start falkye-miroir-req.service
    journalctl -u falkye-miroir-req.service -f

*L'unité pointe sur le RÉPERTOIRE `/opt/falkye/import`, pas sur un fichier : la
plus récente des archives datées est prise, et la ligne `provenance:` du journal
dit laquelle et de quand.*

*L'unité est `oneshot`, `TimeoutStartSec=7200`, et n'écrit que
`/var/lib/falkye`.* **~33 minutes, pic mémoire ~3,5 Go, zéro écriture facturée**
— le miroir est un fichier local, il ne touche jamais la base distante.

### 4. Les trois contrôles, dans cet ordre

    python3 outils/etat_champ_normalise.py          # 0 vide, 0 absent, CONFORME
    python3 outils/diagnostic_appariement.py --toutes --histogramme
    python3 outils/rapport_cout_cycle.py

**Le premier décide si les deux autres valent la peine d'être lus.** *Un
histogramme mesuré sur une colonne encore cassée ne dit rien, et il aurait l'air
de dire quelque chose.*

### 5. Ce qui ne peut PAS être relevé après coup

⚠️ **Le rendement par chemin de résolution ne se rattrape pas sur les exécutions
passées** : les colonnes `nb_abouties_*` sont `NULL` pour tout ce qui précède
leur ajout, et `NULL` veut dire *personne n'a mesuré*, jamais *zéro*. **Il faut un
cycle complet après le réimport pour l'avoir** — et c'est ce cycle-là, pas celui
du 15, qui tranche D14.

## ⚠️ L'import du miroir ne coûte RIEN au quota — et ce n'est pas lui qui l'a vidé

*Écrit le 11 septembre 2026, parce que la croyance inverse avait cours et qu'elle a failli retarder un
cycle.* Le miroir REQ va dans le fichier **local** depuis le découpage du 6 septembre, et
`outils/import_miroir_req.py` **refuse toute cible qui ne commence pas par `sqlite:`**. Un import coûte
donc **zéro lecture et zéro écriture facturées**, quelles que soient ses 2,7 millions d'entrées.

**Ce qui a épuisé le quota le 8 septembre passe par la base durable, pas par le miroir** : un index
unique sur le NEQ acceptant 8 395 NULL, chaque résolution d'entreprise non identifiée lisant 8 395 lignes
deux fois. Mesuré, suffisant à lui seul — 23 142 signaux neufs à ~16 800 lignes. L'index composite a
réduit cette fuite-là sans la fermer : le repli par sous-chaîne balaie toujours **8 396 lignes facturées**
par résolution qui échoue en préfixe *(registre, D14)*.

> **⚠️ Ce diagnostic était vrai et INCOMPLET — dépassé le 11 septembre 2026.** Il nommait une cause
> suffisante et la question s'est refermée dessus. **Un second consommateur, du même ordre de grandeur,
> tournait le même jour et n'a jamais été mesuré** : le chargement des signaux d'une entreprise
> (`signals.company_id`, **sans index**), appelé une fois par entreprise dans deux balayages complets de
> `companies`. Mesuré au compteur de l'hébergeur le 11 septembre : **411 963 777 lectures pour un cycle
> qui n'a résolu AUCUNE entreprise** — donc zéro par le chemin ci-dessus. Le code en cause est antérieur
> au 8 septembre. *Ce qui a rendu l'écart invisible n'est pas une erreur de raisonnement : `rows_read`
> avait été relevé requête par requête sur les trois chemins instrumentés, jamais sur le TOTAL du cycle.*
> **Une cause suffisante n'est pas une cause unique, et seul un total permet d'en juger.** *(journal,
> cas 33; registre, D37)*
>
> **Refermé le soir même.** Un index sur `signals.company_id` — la clé étrangère n'en créait aucun — et le
> même cycle coûte **120 311 lectures**. *411 963 777 → 120 311, divisé par 3 424, mesuré au compteur des
> deux côtés.* **Ce que la lecture de la base durable coûte n'est donc plus la résolution d'identité, ni
> le repli par sous-chaîne : c'était un chargement de relation sans index.** *(registre, D37 et D14.)*

**La distinction vaut d'être gardée : l'import est gratuit, la LECTURE DE LA BASE DURABLE est ce qui
coûte.** Confondre les deux fait craindre le geste inoffensif et fait lancer l'autre sans compter. *Et ne
pas la rétrécir à la seule résolution d'identité : c'est l'erreur que le 11 septembre a corrigée.*

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
