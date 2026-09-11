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

## Tâche en cours — D37, le chargement des signaux par entreprise

### N1 — D37 : mettre à jour avec ce que l'index a réglé
- **Notée le** : 2026-09-11
- **Destination** : registre, D37.
- **Constat** : l'index est posé et vérifié au plan *(demande de fusion nº 36)* —
  `SCAN signals` → `SEARCH … USING INDEX ix_signals_company_id`. **Ce qui manque à
  l'entrée est le résultat** : le compteur de l'hébergeur avant/après le premier cycle
  qui suit, et ce que Top Queries montre à sa place. Restent ouverts après ça : le
  chargement par lot et la double passe.
- **À écrire après** : la mesure.

### N2 — Une entrée neuve : le tri qui suit le chargement, au lieu de le précéder
- **Notée le** : 2026-09-11
- **Destination** : registre, entrée neuve, **rattachée au chantier 22 (la lecture)**.
- **Constat, dicté par Alexandre le 11 septembre 2026** : *le moteur charge les signaux
  de toutes les entreprises, puis trie. Le départage des entreprises pertinentes se fait
  APRÈS le chargement — c'est ce qui rend le coût proportionnel à la base entière plutôt
  qu'à ce qui compte.* **Ce n'est pas un défaut à réparer, c'est une conception à
  revoir.** Avec le corollaire, qui est la moitié qui décide : **enrichir le départage ne
  réduira le coût que si le tri précède le chargement.**
- **Ne pas confondre avec D37** : D37 est le prix d'un appel, celle-ci est le nombre.

### N3 — Un troisième index de la même forme, trouvé et NON posé
- **Notée le** : 2026-09-11
- **Destination** : registre (D37, ou une ligne à elle).
- **Constat** : `notifications.company_id` et `notification_signals.notification_id` sont
  des clés étrangères **sans aucun index** — `_signaux_deja_couverts` les interroge une
  fois par entreprise CANDIDATE. **Écarté de la demande nº 36 délibérément** : ce chemin
  ne s'exécute que pour une entreprise dont un signal a déjà matché un profil, donc zéro
  fois dans le régime actuel. *Non mesuré ⇒ non posé.* **La décision appartient à
  Alexandre**, et le coût du report est un déploiement.

### N4 — Le filtre territorial n'est déclaré que par UNE source sur huit
- **Notée le** : 2026-09-11
- **Destination** : à trancher — registre, ou fiche de source.
- **Constat, lu le 11 septembre 2026** : dans `falkye/registry/sources.yaml`, **seule
  `eimt` déclare un `territoire`**. Les sept autres sources actives automatisées ont
  `territoire: None`, et `falkye/territoire.py::appartient` **retient tout** quand la
  liste est vide — à dessein *(« une valeur absente est retenue, jamais rejetée »)*.
  **Donc le « filtre territorial actif » filtre exactement une source.** Quatre des sept
  autres sont pancanadiennes (`subventions_federales`, `contrats_federaux`,
  `deloitte_fast50`, `rob_top_growing`) et écrivent dans `companies` sans borne de
  territoire, **alors que tout ce qui touche un territoire hors Québec est en veilleuse
  depuis le 4 septembre**.
- **Pourquoi ça compte ici** : la population de `companies` est le multiplicateur du coût
  qu'on vient de mesurer.

### N5 — EIMT porte une adresse que rien ne reçoit
- **Notée le** : 2026-09-11
- **Destination** : fiche de source, ou l'audit des huit sources (N6).
- **Constat** : `falkye/sources/eimt.py` met l'adresse de l'employeur dans `champs`
  (`"adresse": row.get(columns["adresse"])`) mais **ne la promeut pas en
  `RawSignal.adresse`**. `resolve_company` ne recopie que les champs nommés du
  `RawSignal` : `company.adresse` reste donc vide, et le géocodage, le formateur et le
  premier contact ne la voient jamais. *De l'enrichissement capturé, conservé, et
  inutilisé.*

### N6 — L'audit des huit sources : ce que chacune ajoute au dossier
- **Notée le** : 2026-09-11
- **Destination** : **confirmée par Alexandre le 11 septembre** — ça va au corpus, *« c'est
  un état du produit que rien ne dit aujourd'hui »*. Reste à placer : une ligne par fiche
  dans `falkye-sources-spheres-verifiees.md`, ou un relevé à l'audit.
- **Constat** : **deux rôles distincts, et le corpus n'a que le premier** — le signal
  qu'une source produit, et **ce qu'elle ajoute au dossier cumulatif une fois le signal
  détecté**. Relevé du 11 septembre sur les huit sources ingérées : `permis_construction_laval`
  (adresse, ville, région), `rob_top_growing` (ville, région, secteur), `deloitte_fast50` et
  `subventions_federales` (ville, région), `eimt` (région seule), et **`seao`,
  `investissement_quebec`, `contrats_federaux` : rien**. **Aucune des huit ne renseigne
  jamais `site_web`** — seul l'enrichissement web le fait, celui qui échoue en 403.
- **Ce qui décide** : la ville vaut +5 au score de résolution NEQ et sert de départage —
  donc les deux palmarès, dont le signal vise la mauvaise population, remplissent le
  second rôle mieux que le SEAO. *Les deux rôles pointent en sens contraire.*
- **À écrire après** : la décision d'Alexandre sur les deux palmarès.

### N7 — La portée de `detecter_expansions`, et le fait qui la décide
- **Notée le** : 2026-09-11
- **Destination** : registre (décision de portée) + le mécanisme retenu.
- **Constat, lu le 11 septembre 2026** : **une seule source active porte un
  `province_code` — `req` (qc)**; les trois autres qui en portent (`ns`, `bc`, `on`)
  sont `en_pause`. Or `detecter_expansions` ne retient un candidat que s'il a *une
  province QUI DIFFÈRE*. **Avec une seule province au registre actif, la passe ne peut
  produire aucun lien — et elle paie quand même un balayage complet de `companies` plus
  un chargement de signaux par entreprise**, soit la moitié du coût mesuré.
- **La nuance qui décide du mécanisme** : `_provinces_pour_company` lit le
  `province_code` du registre **sans regarder le statut** de la source. Des signaux
  historiques venus des trois sources mises en veilleuse donneraient donc encore des
  provinces. *Savoir s'il en existe est une lecture, pas une hypothèse — et
  `provenance_entreprises.py` la rend dans le même passage.*
- **À écrire après** : la décision d'Alexandre.

### N8 — Globe and Mail Top Growing et Deloitte Fast 50
- **Notée le** : 2026-09-11
- **Destination** : registre, et fiches de source si retrait.
- **Constat** : compter ce qu'elles créent dit ce qu'elles COÛTENT, pas ce qu'elles
  APPORTENT — d'où `outils/apport_ville.py`, qui rejoue la résolution avec et sans la
  ville. **Une part de la question restera non décidable** : une entreprise déjà résolue
  a pu recevoir sa ville du REQ *après* coup (`_enrich_from_req`), et rien ne distingue
  alors les deux origines.
- **TRANCHÉ le 11 septembre 2026 — les deux passent en veilleuse** *(décision
  d'Alexandre, sans attendre la mesure : elle aurait dit ce qu'elles coûtent, pas ce
  qu'elles apportent, et le motif est la spéc. 8.2 — elles visent la mauvaise
  population)*. **Ce qui doit être inscrit au corpus, et pas seulement au registre des
  sources** : la réserve pesée — *le signal ne sert pas, l'enrichissement servait, et
  c'est le signal qui a décidé* — pour qu'une prochaine session ne rouvre pas la décision
  en invoquant l'enrichissement seul. *La réserve est déjà dans la note datée de
  `falkye/registry/sources.yaml`, là où on la lira en voyant `en_pause`; elle reste à
  porter au corpus.*
- **À écrire** : registre des décisions, avec la réserve. Et la fiche de chacune des deux
  sources si le relevé N6 leur donne une ligne.

### N9 — La méthode elle-même : le corpus s'écrit à la fin d'une tâche
- **Notée le** : 2026-09-11
- **Destination** : guide d'ingénierie *(la méthode d'écriture du corpus y vit déjà)*.
- **Constat** : la règle, sa condition — l'ensemble des points, jamais le souvenir — et
  **son garde-fou** : le tampon dans le dépôt plutôt que dans la tête. *Motif : le cas 33
  aurait été mieux écrit après la mesure qu'avant.* **À écrire avec le recul d'au moins
  une tâche tenue de bout en bout** — une règle de méthode écrite le jour où on l'adopte
  n'a encore rien mesuré d'elle-même.
