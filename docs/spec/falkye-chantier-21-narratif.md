# FALKYE — Chantier 21 : présentation de l'opportunité et narratif

Mandat de développement destiné à Claude Code. À exécuter après le chantier 13 (précision perçue), qui
fournit la boucle de correction dont celui-ci a besoin.

> **⚠️ Lire le glossaire en tête de `falkye-audit-et-mandat.md` avant ce document.** Cinq mots du corpus
> portent chacun deux sens ou plus — **état** (celui d'une source, chantier 1, contre celui du produit,
> chantier 29), **journal** (d'exécution, de diagnostic, de repli, d'exploitation, ou le journal des
> cas), **numéro contre rang**, **statut d'exécution contre état de santé**, et **chantier contre travail
> contre point**. *La contradiction du 7 septembre s'était logée dans le premier.*


---

## Pourquoi ce chantier existe

Le corpus décrit en détail comment un signal entre et comment il est scoré. Il dit peu sur ce qui sort.
La promesse faite est « le motif précis du repérage » et des « amorces de premier contact
contextuelles », mais le mécanisme qui produit cette phrase n'est décrit nulle part.

C'est pourtant ce que l'utilisateur voit. Le moteur de croisement est l'avantage défendable; le narratif est la
seule forme sous laquelle cet avantage défendable lui parvient.

---

## Portée

**Dans le chantier :** seuil de publication, fraîcheur et trajectoire dans le grade, structure de faits,
gabarits de narratif, formulation optionnelle par LLM, amorce de premier contact, expression de
l'incertitude.

**Hors du chantier :** les trois scores eux-mêmes (déjà en place), la cadence de notification
(chantier 8), le comportement en l'absence de signal (chantier 14).

---

## 1. Seuil de publication — une décision produit, pas un algorithme

La matrice confiance × pertinence produit un classement. Ce que le corpus ne fixe pas, c'est **à partir
de quelle case un dossier devient une opportunité présentée** plutôt qu'un dossier qui continue de
mûrir.

À construire : un seuil explicite, configurable, et **distinct du curseur de sensibilité utilisateur**.
Le seuil de publication dit ce qui est présentable; la sensibilité dit ce que cet utilisateur-ci veut
voir parmi le présentable. Les fusionner enlèverait à l'utilisateur la possibilité d'être plus
sélectif que le défaut.

**À valider avec Alexandre**, pas à choisir dans le code.

---

## 2. Fraîcheur et trajectoire dans le grade

Le A/AA/AAA mesure l'alignement au profil. Rien ne mesure le **moment**. Un nouvel établissement
détecté il y a trois jours et le même détecté il y a huit mois produisent aujourd'hui le même grade,
alors que la valeur commerciale diffère nettement.

À construire :
- La **fraîcheur** — âge du signal le plus récent du dossier — comme composante du grade.
- La **trajectoire** — densité de signaux sur une fenêtre glissante — comme seconde composante,
  reprise du chantier 17 si celui-ci est déjà livré, sinon construite ici sous une forme minimale et
  remplacée ensuite.
- Ces deux composantes **modulent le grade, elles ne le remplacent pas**. Un signal frais mais mal
  aligné ne devient pas AAA.

**Question de la section 11.** Que se passe-t-il quand un dossier contient un signal ancien très fort
et un signal récent faible? La fraîcheur porte-t-elle sur le plus récent, sur le plus fort, ou sur
l'ensemble? Trancher, écrire, tester.

---

## 2bis. Contrainte de non-fermeture — l'interprétation reste ouverte

**Question ouverte, consignée aux spécifications, section 9.2bis :** le produit sait rattacher des
signaux à une entreprise et à une sphère, mais rien ne produit encore d'**interprétation** — ce que les
signaux, ensemble, veulent dire. La structure de faits est une liste, et un gabarit qui rend une liste
produit une énumération, pas un récit.

**Rien n'est à construire ici.** Ce qui manque a besoin de vrais dossiers pour être calibré, et inventer
des motifs d'avance reproduirait l'erreur d'inventer des sphères.

**Ce qui est exigé de ce chantier : ne fermer aucune porte.** Quatre contraintes, à respecter dans la
conception :

- la structure de faits reste extensible et pourra porter un motif reconnu à côté de ses signaux, sans
  refonte;
- les gabarits restent liés au couple **signal × sphère**, jamais figés en un texte par signal isolé — un
  gabarit écrit comme « voici ce signal » ne pourra jamais devenir « voici ce que ces signaux signifient
  ensemble »;
- le lien entre signaux d'un même dossier reste explicite et conservé, avec ses dates et son ordre;
- l'interprétation ne se fusionne jamais dans le score : un motif reconnu pourra moduler la pertinence,
  mais il reste une notion distincte des trois axes;
- **la présentation réserve une place vide** pour une ligne d'interprétation distincte des faits, au
  conditionnel, et pour une seconde ligne reliant cette interprétation au besoin de l'utilisateur. La
  place existe dans la structure et dans la mise en forme; **elle n'est pas remplie, et aucun motif n'est
  écrit**. Voir les spécifications, section 9.2bis.

**À dire sans ambiguïté à qui exécute ce chantier : rien de tout ceci ne se construit ni ne se configure
maintenant.** La seule exigence est qu'aucune décision prise ici n'empêche de l'ajouter plus tard.

## 3. Structure de faits — la pièce centrale

**Le narratif se calcule d'abord, se rédige ensuite.** Le moteur produit une structure explicite avant
qu'aucun texte n'existe :

- les signaux retenus, avec leur date, leur source interne et leur poids;
- leur ordre chronologique et les écarts entre eux;
- la sphère retenue et la raison du lien avec le service de l'utilisateur;
- le grade et ce qui l'a déterminé;
- la confiance d'appariement et son effet de plafonnement.

**Cette structure est la vérité. Le texte n'en est qu'un rendu.** Elle est conservée avec
l'opportunité, ce qui permet de reconstruire ou de re-rendre un narratif sans recalculer quoi que ce
soit — et de répondre à un utilisateur qui conteste.

---

## 4. Gabarits par croisement

Chaque combinaison signal × sphère porte une phrase à trous, écrite d'avance, dont les variables
viennent de la structure de faits.

**Trois contraintes que le corpus impose déjà, à intégrer dès l'écriture du premier gabarit** — les
ajouter après coup obligerait à tout réécrire.

**Aucun nom de source.** « Selon le RACJ » est interdit (charte, section 6). Le gabarit dit « un permis
d'alcool a été délivré », jamais d'où l'information vient. Chaque gabarit se relit contre cette
contrainte.

**L'amorce de premier contact est une aide à la rédaction, jamais un message prêt à envoyer.** Ce qui
est fourni est un angle et un contexte, pas un courriel à copier. La frontière est explicite dans la
section 6 : FALKYE n'est pas un outil de prospection automatisée.

**Un contrainte de délivrabilité, transmise par le chantier 28.** Un résumé de prospects d'entreprises
ressemble, en surface, à une liste d'adresses achetée — précisément la forme de contenu que les filtres
anti-pourriel scrutent le plus. La formulation et la structure des gabarits comptent donc davantage ici
que pour un courriel transactionnel ordinaire, et un gabarit qui accumule des noms d'entreprises sans
contexte est le pire cas. C'est une contrainte de conception, pas un raffinement esthétique.

**L'incertitude se voit dans la formulation, pas seulement dans un chiffre.** Quand la confiance
d'appariement est basse, le gabarit employé doit être plus prudent — « une entreprise portant ce nom
à cette adresse » plutôt qu'une affirmation directe.

Commencer par les croisements les plus denses, ceux qui produiront le plus de volume, plutôt que de
viser la couverture complète du catalogue.

---

## 5. Formulation par LLM — optionnelle, encadrée

Admissible sous la frontière posée à la charte, section 6 : un composant non déterministe **formule**
ce que les règles ont **décidé**.

- Le modèle reçoit **uniquement la structure de faits**. Aucun accès aux données brutes, aucune
  latitude pour ajouter un fait.
- **Test automatisé de non-invention** : chaque fait du texte produit doit être traçable à la
  structure. Un texte qui n'est pas reconstructible est rejeté et le gabarit prend le relais.
- **Le gabarit est la solution de repli, pas l'absence de notification.** Si l'API est indisponible ou
  si le test échoue, l'opportunité part avec son texte de gabarit.
- **Génération une seule fois, au moment de la publication, puis stockage du texte.** Jamais de
  régénération à l'affichage : c'est ce qui transforme un coût par consultation en coût par
  opportunité créée, et ça garantit qu'un utilisateur revoit exactement le texte qu'il a déjà lu.
- Clé API distincte de l'abonnement personnel d'Alexandre, comme pour l'assistance de configuration.

---

## 6. Boucle de correction

Le taux de rejet « Pas pertinent » du chantier 13 se ventile **par gabarit et par croisement**. Un
croisement dont le narratif est systématiquement rejeté indique soit un lien sphère↔signal faible,
soit une formulation qui promet plus que le signal ne porte. Les deux méritent d'être vus, et c'est la
meilleure boucle de correction disponible sur cette partie du produit.

---

## 7. Relecture de tous les libellés visibles par l'utilisateur

Chantier transversal, **à faire en une seule passe** plutôt qu'au fil de l'eau : un vocabulaire se
corrige une fois, puis se maintient. Fait après coup, il faudrait rouvrir chaque écran.

**Ce n'est pas une passe cosmétique de fin de chantier.** À contenu identique, la formulation et le
rythme de livraison décident souvent seuls entre un abonné qui reste et un abonné qui part.

### Le critère

Pour chaque libellé : **retire-t-il un découragement non mérité par la donnée, ou ajoute-t-il un
encouragement qui ne l'est pas non plus?** Le premier est à faire, le second est interdit. *Le cas
fondateur est la gradation A / AA / AAA, qui a remplacé A / B / C sans rien changer au classement —
seulement en retirant un jugement de médiocrité que le produit n'avait aucun moyen de porter.*

### Ce qui doit être relu

**Un inventaire est à produire avant les corrections** — l'exercice a autant de valeur que le résultat,
puisqu'il révélera des textes que personne n'a relus depuis leur écriture. La liste est indicative, pas
limitative : **tout texte que l'utilisateur peut lire y passe.**

- Les **grades et scores**, partout, y compris en abrégé et dans les info-bulles.
- Les **statuts de suivi**. Un statut décrit un fait, jamais une performance. « Joint, sans suite » est
  un fait; « Perdu » ou « Échec » juge son travail, ce que le produit ne connaît pas.
- Les **messages d'absence de résultat** — frontière partagée avec le chantier 14. Formuler par ce qui a
  été fait plutôt que par ce qui manque : le nombre d'entreprises suivies **rend visible un travail réel
  qui autrement ne se voit pas**.
- **L'expression de l'incertitude.** Une réserve se formule par l'action qu'elle appelle.
- Les messages d'**échéance et d'archivage** (chantier 24).
- Les messages d'**erreur, de quota, de limite de palier**, et de source indisponible.
- Les libellés de **configuration de profil**, dont l'avertissement de faible densité — **dire la réalité
  sans la présenter comme un défaut de l'utilisateur**.
- Les **libellés d'action** : ce que fait un bouton, comment se nomme un rejet, comment se nomme un
  archivage.
- Les **gabarits et les amorces** eux-mêmes.
- Les **courriels de notification, objet compris** — le texte le plus lu du produit et souvent le moins
  relu.

### Six révisions à examiner, avec leur raison

**Retenir ou écarter chacune, mais la trancher explicitement.**

- **Statuts de suivi.** « Joint, sans suite » convient; « Perdu » ou « Échec » porterait un jugement sur
  le travail de l'utilisateur.
- **Confiance d'appariement basse.** « Lien incertain » invite à ignorer; **« à confirmer avant l'appel »
  dit la même chose en indiquant l'action.**
- **Rejet d'une opportunité.** « Pas pertinent » est déjà neutre. Vérifier surtout que **rien ne suggère
  à l'utilisateur qu'il corrige une erreur du système** — c'est une préférence qu'il exprime, et **une
  formulation culpabilisante tarirait la boucle de correction du chantier 13**.
- **Fonctionnalité absente du palier.** Décrire ce que le palier supérieur permet, plutôt que ce que
  l'actuel ne permet pas. Même information, **sans faire porter le manque à l'abonné**.
- **Opportunité archivée.** « Archivée » plutôt qu'« expirée » : la première décrit un rangement, **la
  seconde suggère une occasion ratée, ce que le produit ne sait pas**.
- **Source indisponible.** Ne jamais la nommer, et **ne pas laisser croire à une panne générale quand une
  seule source est concernée**.

### Deux propositions supplémentaires, à valider

**Un lot vide ne devrait pas être un courriel vide.** Deux options : ne rien envoyer, ou envoyer un
message court disant ce qui a été surveillé. La seconde entretient la preuve que le produit travaille,
mais **un message hebdomadaire qui ne dit jamais rien devient lui-même un irritant**. *Proposition :
l'envoyer, et cesser après quelques lots vides consécutifs pour basculer vers le mécanisme
d'intervention du chantier 14, qui propose un ajustement plutôt que de répéter l'absence.*

**L'ordre d'affichage porte un message autant que les libellés.** Un tri par date place les vieux
dossiers non traités en tête et **donne l'impression d'un retard accumulé**. Un tri par grade puis
fraîcheur place en tête ce sur quoi il vaut la peine d'agir. *Proposition : grade puis fraîcheur par
défaut, tri par date disponible mais non par défaut.*

### La limite, à respecter dans toute la passe

Retirer un jugement que la donnée ne soutient pas est légitime; **ajouter une attente que rien ne
soutient ne l'est pas.** Aucun libellé ne doit laisser entendre qu'une sphère sans couverture est en
préparation, ni qu'un silence est temporaire quand rien ne permet de le dire.

### Livrable

**L'inventaire complet des libellés visibles**, chacun avec sa formulation actuelle, la formulation
proposée quand elle change, et le critère qui a motivé le changement. **À relire par Alexandre avant
application — c'est du texte destiné à ses clients, pas une décision technique.** Cet inventaire devient
la référence pour tout libellé futur.

---

## 8. Tests exigés

1. Structure de faits produite et conservée avant tout rendu de texte.
2. Un texte contenant un fait absent de la structure est rejeté par le test de non-invention.
3. Aucun nom de source ne franchit la frontière, dans aucun gabarit ni dans aucune sortie de LLM.
4. LLM indisponible : l'opportunité part quand même, avec son texte de gabarit.
5. Le texte est généré une seule fois et n'est pas régénéré aux consultations suivantes.
6. Confiance d'appariement basse : le gabarit prudent est employé, vérifié sur la formulation.
7. Deux dossiers identiques sauf la fraîcheur produisent deux grades différents.
8. Question de la section 11 : signal ancien fort contre signal récent faible, comportement conforme à
   la décision retenue.
9. L'amorce de premier contact ne constitue jamais un message complet prêt à l'envoi.
10. Seuil de publication et curseur de sensibilité restent deux réglages distincts et cumulables.
11. Aucun libellé visible par l'utilisateur ne porte de jugement sur sa performance plutôt que sur le
    dossier.
12. Aucun libellé ne laisse entendre qu'une sphère sans couverture est en préparation, ni qu'un silence
    est temporaire quand rien ne permet de le dire.

---

## Ce qui doit être livré

1. Le seuil de publication proposé, avec justification — **décision à valider avec Alexandre**.
2. Le code : structure de faits, grade modulé, gabarits, rendu, repli.
3. Les douze tests ci-dessus, verts, dans la suite existante.
4. La liste des croisements couverts par un gabarit, et de ceux qui ne le sont pas encore.
5. L'inventaire complet des libellés visibles, avec le texte retenu et la raison de chaque changement.
6. Vérification macro : un narratif produit pour au moins un dossier réel de chaque source active, avec
   le texte obtenu, à relire.

---

