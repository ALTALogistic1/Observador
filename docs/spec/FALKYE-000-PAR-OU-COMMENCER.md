# FALKYE — Par où commencer

*Point d'entrée du corpus. **Le seul document à joindre en premier**, quelle que soit la conversation.
Il n'explique rien lui-même : il dit où aller. Tout ce qu'il contient vit ailleurs.*

---

## Ce qu'est FALKYE, en trois phrases

**Le produit construit un portrait de la situation d'une entreprise à un moment donné**, en croisant tout
ce qu'il sait d'elle, puis il évalue si ce portrait révèle un besoin qu'un fournisseur de services peut
remplir. **C'est à ce moment que ce fournisseur est notifié.**

**La promesse n'est pas de détecter des événements** — c'est de connecter les données des sources entre
elles pour donner un portrait exact d'une situation. *Un signal n'est qu'un élément du portrait; l'appel
d'offres n'est qu'un cas parmi d'autres, jamais la finalité.*

**L'avantage défendable n'est pas la donnée**, à laquelle d'autres ont accès. Il tient au moteur de
croisement et à **ce que le produit conserve** : dossier cumulatif, registre de correspondances, table
d'apprentissage d'appariement, journal de diagnostic. Aucun des quatre ne s'achète.

*Développé dans `charte-falkye.md` — sections 9 et 14bis.*

---

## Le cœur et le cerveau

**Le cœur est construit** : le moteur qui s'alimente aux sources, calcule les changements, met en
quarantaine, résout les entreprises, livre. *Chantiers 1, 28, 29.*

**Le cerveau se construit en cinq facettes.** Un système qui lit, associe et parle sans mémoire ni
jugement produit du bruit crédible — pire que le silence.

*⚠️ **Lecture du produit en cours d'élaboration, pas un cadre arrêté.** Les facettes nomment ce que le
cerveau doit savoir faire; elles se travaillent dans les chantiers indiqués, et le découpage lui-même
peut encore bouger. **Le jugement est la moins aboutie des cinq** — il n'a pas de chantier, et ce n'est
pas un oubli. Ne pas y ranger des chantiers comme si le cadre était tranché.*

*La condition d'ouverture de cette discussion est au registre des décisions ouvertes, **D33** — trois
faits à réunir plutôt qu'une date, parce qu'une place vide sans déclencheur devient un oubli (cas 15).*

| Facette | Ce qu'elle fait | Chantier |
|---|---|---|
| **Mémoire** | Avoir gardé, avant de lire. Trois signaux en deux mois ne valent pas trois en deux ans | 17 |
| **Lecture** | Extraire d'un signal ce qu'il dit vraiment | 22 |
| **Association** | Partir d'un besoin et chercher, dans ce qu'on possède déjà, ce qui pourrait le servir | 12 |
| **Jugement** | Décider de **ne pas dire** — seuil, confiance plafonnée, sphère non offerte | *aucun* |
| **Langage** | Mettre en mots ce qui a été compris | 21 |

**Le chantier 13 les corrige toutes** : le taux de rejet est la seule boucle qui confronte le moteur au
réel plutôt qu'à des hypothèses.

**⚠️ Une place a été laissée vide, et c'est un choix documenté.** Entre *associer* et *mettre en mots*,
il y a **comprendre** — la synthèse. Elle n'a pas de chantier : elle attend d'avoir de quoi se
construire, parce qu'**inventer des motifs d'avance reproduirait l'erreur d'inventer des sphères**. *Ce
n'est pas un trou : la question est traitée aux **spécifications, section 9.2bis** et au **mandat du
chantier 21, point 2bis**, avec cinq contraintes de non-fermeture à respecter. Ne pas la combler sans
décision explicite, et ne pas la croire absente du corpus.*

---

## Quelle question, quel document

| Ta question | Va voir |
|---|---|
| Qu'est-ce qu'on bâtit, et pourquoi ce choix plutôt qu'un autre? | `charte-falkye.md` — **tranche en cas de contradiction** |
| Que fait le produit aujourd'hui, concrètement? | `falkye-specifications-produit.md` |
| Sur quoi travailler, dans quel ordre, et pourquoi cet ordre? | `falkye-audit-et-mandat.md` — **contient les 29 chantiers** |
| Que veut dire ce mot? | Le **glossaire**, en tête de l'audit — cinq mots portent deux sens |
| Qu'est-ce qui n'est pas tranché, et qui doit le trancher? | Le **registre des décisions ouvertes**, en tête de l'audit |
| Comment sait-on qu'un travail est vraiment fini? | `falkye-guide-ingenierie.md` |
| Cette erreur, est-ce qu'on l'a déjà faite? | `falkye-journal-des-cas.md` — 28 incidents réels |
| Peut-on utiliser cette source légalement? | `falkye-cadre-legal.md` — **avant d'activer, jamais après** |
| À qui vend-on, et contre qui? | `strategie-et-personas.md` |
| Ce territoire est-il servi? | **Le Québec seulement.** Tout ce qui est hors Québec est en veilleuse — *stratégie §3, décision du 4 septembre 2026*. Une source hors Québec n'est retenue que si elle améliore les résultats **au Québec** |
| Quelles sources existent, lesquelles ajouter? | `falkye-sources-spheres-verifiees.md` et `falkye-recommandations-sources.md` |
| Comment faire *ce* chantier précis? | `falkye-chantier-<n>-<nom>.md` — six existent |
| Où en étaient les travaux? | Le document de reprise du moment — **il ne se met pas à jour : il s'écrit à neuf à chaque passation, puis se jette.** Le reste du corpus, lui, se maintient |

**Règle d'arbitrage : charte, puis audit, puis mandat.** Une fiche de l'audit est le mandat par défaut;
quand un mandat contredit l'audit, l'audit tranche.

---

## Trois choses à savoir avant de toucher à quoi que ce soit

**Un point vit à un seul endroit.** Ce qui est écrit à deux endroits finit par diverger, et la divergence
ne se signale jamais. Les autres documents renvoient, ils ne recopient pas.

**La preuve voyage avec le fait.** Pas « le serveur est actif » mais « le serveur répond, vérifié le
5 septembre par connexion ». *Un fait sans preuve attachée ne peut pas servir de prémisse.*

**Le motif le plus coûteux du projet : quelque chose qui a l'air de fonctionner et qui ne fonctionne
pas.** Un cycle qui réussit à vide, un minuteur qu'on croyait éteint, une garantie d'unicité déclarée au
modèle et absente de la base. Il ne se signale jamais. **La commande qui tranche coûte dix secondes; la
supposition coûte une journée.**

---

## Comment travailler avec Alexandre

**Il communique en français**, préfère le direct et le concret, et n'aime pas la gradation excessive —
ne pas qualifier de « grave » ou « bloquant » ce qui est seulement à surveiller.

**Il veut être consulté.** Mettre en contexte, proposer des options, répondre à ses questions, l'épauler.
**Ne pas décider à sa place ni énoncer de règles en son nom** — c'est lui qui tranche.

**Les messages destinés à Claude Code se présentent en bloc de citation**, avec la mention des documents
à joindre.

**Chaque terme technique porte sa signification simplifiée entre parenthèses** — objectif d'apprentissage
sur le tas.

**Quand un geste technique est à poser**, donner la marche complète : où taper, la commande exacte, ce
qu'on doit voir en retour, et quoi faire sinon.

### Écrire dans le corpus — une seule main, et ce qu'elle doit dire

**Le texte vient d'Alexandre; Claude Code l'écrit dans le document qui convient; Alexandre fusionne.**
Ça vaut pour une ligne comme pour un bloc. *Hors corpus — le README du dépôt, `docs/ARCHITECTURE.md`,
`docs/DEPLOIEMENT.md`, `docs/STATUT_RESEAU.md` — Claude Code corrige et Alexandre relit en demande de
fusion. La frontière porte sur QUI RÉDIGE, jamais sur qui regarde.*

**À l'ouverture du cerveau *(registre, D33)*, ce ne seront plus des corrections ponctuelles** mais des
sections entières, possiblement plusieurs de suite. La méthode ne change pas; deux exigences s'y
ajoutent, et elles ne valent que parce que la structure aura grossi.

**Dire dans quel document chaque bloc doit aller** quand Alexandre ne le précise pas. Un texte rangé au
mauvais endroit y devient introuvable, et personne ne s'en aperçoit avant d'en avoir besoin.

**Signaler qu'un texte reçu contredit ce qui est déjà écrit ailleurs — AVANT de l'écrire, jamais
par-dessus.** Écrire par-dessus produit deux formes du même contenu qui divergent, ce que le guide
d'ingénierie interdit; et la contradiction se découvre alors au pire moment, quand quelqu'un s'appuie
sur celle des deux qui a tort.
