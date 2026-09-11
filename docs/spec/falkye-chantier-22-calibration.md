# FALKYE — Chantier 22 : calibration déclarée et durée de pertinence

*Mandat détaillé. La fiche courte est dans `falkye-audit-et-mandat.md`, qui tranche en cas de
contradiction.*

> **⚠️ Lire le glossaire en tête de `falkye-audit-et-mandat.md` avant ce document.** Cinq mots du corpus
> portent chacun deux sens ou plus — **état** (celui d'une source, chantier 1, contre celui du produit,
> chantier 29), **journal** (d'exécution, de diagnostic, de repli, d'exploitation, ou le journal des
> cas), **numéro contre rang**, **statut d'exécution contre état de santé**, et **chantier contre travail
> contre point**. *La contradiction du 7 septembre s'était logée dans le premier.*


**Deux mécanismes réunis parce qu'ils portent sur la même question : à quelles conditions un changement
dans les données devient un signal, et pendant combien de temps ce signal vaut quelque chose.**

**Ce chantier précède les chantiers 4 et 6.** Le moteur de notation reflète fidèlement une entrée
uniforme : tous les signaux d'une source portent aujourd'hui la même sphère avec la même confiance, donc
**le score n'a rien à départager**. Le raffiner avant produirait une notation plus fine nourrie de la
même uniformité.

**Additif, à coût constant : il ne touche aucune clé de données.**

---

## 22.1 — Une forme commune pour les règles de calibration

**Constat.** La charte pose qu'aucune source ne s'active sans une règle qui distingue le vrai signal du
bruit administratif. **Cette règle n'a aujourd'hui aucune forme commune** : chacune est codée à la main
dans son connecteur. On ne peut ni les comparer, ni les auditer, ni les tester côte à côte — **et la
calibration de chaque nouvelle source se réinvente à partir de rien.**

**À construire — un catalogue de motifs déclarés au registre**, plutôt que du code sur mesure.

- **Apparition** d'un enregistrement absent de l'état précédent.
- **Changement de valeur** d'un champ au-delà d'un seuil — hausse de capacité d'accueil, valeur de
  contrat.
- **Franchissement de palier** — seuil d'effectif confirmé, tranche de valeur.
- **Répétition** d'un même type d'événement sur une fenêtre donnée.
- **Absence attendue** — le motif du chantier 17, **à prévoir dans la forme même s'il est construit
  ailleurs**.

Chaque règle déclare **son motif, le champ visé, son seuil, le tier de confiance produit, et ce qu'elle
exclut explicitement comme bruit administratif**. **Ajouter une source devient une déclaration, pas une
réécriture.**


**Le tier de confiance est porté par le couple type de signal × sphère** *(spéc. 8.1, tranché le
11 septembre 2026)*, jamais par le signal seul. Une même règle produit un signal **fort** pour une sphère
et **faible** pour une autre — une non-conformité à la francisation est un besoin aigu et une croissance
douteuse — et **forcer une valeur unique mentirait à l'une des deux**. *Même règle que la durée de
pertinence du 22.2 : portée par le couple, jamais par le signal seul.*

**Les critères qui produisent un niveau plutôt qu'un autre n'existent pas, et ils ne se rédigent pas
d'avance.** Décider si un signal est réel et fort **est** l'acte de lecture que ce chantier construit :
c'est une place qui attend cette facette, pas un champ mal documenté *(registre, D34; charte, règle 5)*.
Le catalogue de motifs ci-dessus est ce qui les rendra formulables — **huit fiches de source portent déjà
un tier justifié au cas par cas**, à la granularité exacte d'une règle déclarée.

**Livrable de migration.** Reprendre les règles de calibration existantes des sources actives sous cette
forme, et **rapporter celles qui n'y entrent pas — un motif manquant au catalogue est une information
utile, pas un échec.**

**Ce que ce chantier débloque, mesuré.** Les 1 672 signaux d'une même source portaient **tous la même
sphère unique**, faute de règle capable de les distinguer. La classification normalisée que cette source
publie sur 93 % de ses avis est **l'antidote direct** : un code n'est pas un autre, et cette différence
est vérifiable plutôt qu'interprétée.

**Garde-fou.** Élargir la lecture d'un signal ne veut pas dire multiplier les correspondances pour
couvrir plus de sphères. **Un signal qui sert cinq sphères sans discriminer n'en sert aucune** — il
produit du bruit crédible, pire que le silence. **Ce qui transforme une correspondance en lecture, c'est
la condition** : « un contrat annonce un besoin en cautionnement » est du remplissage; « un premier
contrat, ou un contrat disproportionné par rapport aux effectifs déclarés » est une lecture, et elle est
mesurable.

---

## 22.2 — Durée de pertinence par couple type de signal × sphère

**Constat.** Le chantier 21 met la fraîcheur dans le grade, mais **uniformément**. Or la fenêtre de
pertinence varie fortement : *un nouvel établissement intéresse un entrepreneur en entretien deux ou
trois mois; un dépôt de marque intéresse un conseiller en franchisage près d'un an; une vague d'embauche
se refroidit en quelques semaines.*

**À construire.** Une **durée de pertinence déclarée au registre, par couple type de signal × sphère**,
avec une valeur par défaut quand le couple n'est pas renseigné. Elle **module la fraîcheur dans le grade**
(chantier 21) et **détermine la profondeur d'antériorité à l'inscription** (chantier 25).

**Décision à respecter sans exception : active dès le palier d'entrée, identique partout, non
configurable par l'utilisateur.**

Trois raisons. **Ce n'est pas une fonctionnalité, c'est une correction de justesse** — un fait sur le
signal, pas une préférence. Livrer des résultats délibérément moins exacts au palier d'entrée
contredirait la règle de placement de la charte : **c'est une source de couverture appliquée au temps,
pas un enrichissement.** Et **un utilisateur n'a aucun moyen de savoir combien de temps un signal reste
pertinent dans sa sphère** — c'est une connaissance du produit, pas la sienne, et la lui faire régler
serait lui confier un travail qu'il ferait mal.

**Question de désaccord.** Un signal servant **deux sphères aux durées différentes** — un nouvel
établissement, chaud trois mois pour l'entretien et douze pour l'assurance. **La durée est portée par le
couple, jamais par le signal seul**, et le même fait peut donc être frais pour un utilisateur et périmé
pour un autre.

---

## Tests exigés

1. Une règle de calibration déclarée sous forme de motif **produit le même résultat que la règle codée
   qu'elle remplace**, pour chaque source active migrée.
2. Un même signal servant deux sphères aux durées différentes est **frais pour l'une et périmé pour
   l'autre au même instant**.
3. La durée de pertinence **s'applique identiquement dans les trois paliers**.
4. Une source dont la règle déclarée ne discrimine pas — même sphère pour tous ses signaux — **est
   signalée comme telle au rapport de migration**, plutôt que d'être acceptée en silence.
