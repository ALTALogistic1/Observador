# README pour Claude Code — Repéreur d'entreprises en croissance

Ce fichier accompagne `repereur-entreprises-croissance-specs.md`, le document de spécifications complet du projet. Lis d'abord la spec au complet, puis reviens à ce README pour les consignes de démarrage.

## Point de départ : Phase 1 seulement

Ne construis pas les 10 sources d'un coup. Commence par un chemin complet de bout en bout avec **4 sources seulement** (voir section 8 de la spec, "Séquencement de développement recommandé") :

- **SEAO** (appels d'offres)
- **RDPRM** (financement)
- **REQ** (registre corporatif — sert aussi de base de résolution NEQ/adresse/secteur pour les autres sources)
- **Guichet-Emplois** (recrutement)

L'objectif de cette phase est de valider **tout le pipeline** — détection → résolution NEQ/REQ → score de confiance → vérifications de base obligatoires → enrichissement web → notification — avec ces 4 sources, pas d'avoir une couverture complète. Les 6 autres sources gratuites (EIMT, subventions fédérales, Investissement Québec, classements de croissance, permis de construction, Québec emploi) s'ajoutent une à une après coup, dans le registre déjà conçu pour ça.

## Respecte l'architecture modulaire dès la Phase 1

Le piège à éviter : coder la première source (ex. SEAO) en dur plutôt que de construire directement le **registre de sources modulaire** décrit en section 9. Même avec seulement 4 sources actives, la structure doit déjà être : un gabarit générique (identifiant, signal associé, statut, méthode d'accès, champs pertinents, coût, région), un moteur qui boucle sur les sources actives, et l'ajout d'une source qui ne touche jamais au moteur central. Si la Phase 2 demande de modifier le moteur pour ajouter une source, c'est que l'architecture de la Phase 1 n'a pas été construite correctement.

Même logique pour le registre de types de signaux (section 7, "Extensibilité des types de signaux") et le champ `type de profil` (fournisseur/client/les deux, section 4/9) — prévoir la structure dès le départ, même si seule la mécanique fournisseur est utilisée en Phase 1.

## Aucun compte ou accès à préparer pour la Phase 1

SEAO, RDPRM, REQ et Guichet-Emplois sont tous des données ouvertes gratuites, sans clé d'API requise, à notre connaissance. Si tu découvres le contraire en creusant, dis-le.

## En cas d'ambiguïté

Pose la question plutôt que de deviner. La spec couvre le *quoi* (sources, signaux, champs, logique de scoring, vérifications) mais pas le *comment* technique (stack, base de données, hébergement) — ces choix technique t'appartiennent, mais toute ambiguïté sur l'intention produit doit être clarifiée avant de coder, pas résolue par une supposition.

## Hors scope pour toi

Un document séparé de stratégie commerciale existe (`repereur-strategie-commerciale.md`) mais n'est pas pertinent pour la construction technique — ignore-le sauf si on te dit explicitement de l'utiliser.
