"""Tous les noms d'une entreprise au registre — **pas seulement celui que le
chargeur élit**.

**Le fait qui fait exister cette table** *(mesuré le 2026-09-16)*. `Nom.csv` porte
**1 138 322 NEQ avec plusieurs noms en vigueur — 41,7 % du registre** — et
`_charger_index_noms` en élit **un seul**, jetant **1 705 806 noms** à chaque
chargement. *Le pont que les chantiers 3 et 4 cherchaient dehors était dans le
fichier depuis le premier import.*

**Ce que ça coûtait, mesuré** : sur 8 395 entreprises non résolues, **2 217
(26,4 %) s'apparient exactement à un nom que le chargeur jetait**, et **98,8 %
d'entre elles sont des sociétés par actions** — pas des travailleurs autonomes.
*Exemple : `9224-5842 Quebec inc` s'apparie à `Ferme M.G. Bellavance`. Le nom
numérique est la dénomination sociale élue; le nom parlant est celui qu'on
jetait.*

**Pourquoi une table SÉPARÉE plutôt qu'une colonne de plus sur `REQEntry`.**
`REQEntry` est **une ligne par entreprise** — c'est ce qui en fait le pivot de
résolution, et ce qui permet à `get_by_neq` d'être un accès par clé primaire.
*Un nom supplémentaire par ligne casserait ça; une colonne multivaluée
reproduirait le défaut d'`AUTRES_NOMS` de l'OPC, qu'on a dû éclater à la main.*
**Une ligne par (NEQ, nom) garde les deux propriétés : `REQEntry` reste unique
par entreprise, et la recherche par nom devient un index normal.**

⚠️ **`REQEntry.nom` ne change pas de sens.** Il reste **la dénomination sociale
élue** — celle qu'on affiche, celle qui identifie l'entreprise auprès d'un
humain. *Cette table sert à TROUVER, jamais à NOMMER.* **Ne jamais afficher un
`REQNom` comme le nom de l'entreprise** : `Ferme M.G. Bellavance` trouve
`9224-5842 Québec inc.`, elle ne la remplace pas.

⚠️ **Ce qu'elle apporte en portée, elle le coûte en ambiguïté.** *Plus de noms
récupérés veut dire plus de candidats comparés, donc plus d'écarts serrés entre
le premier et le second.* **Le moteur refuse un candidat dont le second est à
moins de 8 points** — un gain de rappel se paie en résolutions qui basculent
vers l'ambigu, et les deux se mesurent ensemble *(`outils/impact_tous_les_noms.py`)*.
"""
from __future__ import annotations

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from falkye.models.base import BaseMiroir, utcnow
from datetime import datetime


class REQNom(BaseMiroir):
    """Un nom sous lequel une entreprise fait affaire au Québec."""

    __tablename__ = "req_noms"

    # Clé composite (NEQ, nom normalisé) plutôt qu'un identifiant technique : la
    # même entreprise peut déclarer deux fois la même graphie sous deux types de
    # nom différents, et un import répété ne doit pas empiler des doublons.
    neq: Mapped[str] = mapped_column(String(20), primary_key=True)
    nom_normalise: Mapped[str] = mapped_column(String(300), primary_key=True)

    #: Le nom TEL QUE PUBLIÉ. Gardé à côté du normalisé pour qu'un diagnostic
    #: puisse montrer ce que la source écrit, et non seulement ce qu'on compare —
    #: c'est ce qui manquait à `comparaison()` le 15 septembre.
    nom: Mapped[str] = mapped_column(String(500), nullable=False)

    #: ⚠️ **DE QUEL GISEMENT LA FORME VIENT** *(ajoutée le 2026-09-17)*.
    #:
    #: **Le fait qui l'ajoute** : l'archive porte QUATRE gisements de noms, et le
    #: produit n'en indexait qu'un, filtré. *L'inventaire du 17 septembre, sur
    #: l'archive du 2 :*
    #:
    #: | gisement | fichier | formes |
    #: |---|---|---|
    #: | `NOM_ASSUJ` | `Nom.csv` | 4 651 087 |
    #: | `NOM_ETRNG` | `Nom.csv`, colonne `NOM_ASSUJ_LANG_ETRNG` | 412 459 |
    #: | `NOM_ETAB` | `Etablissements.csv` | 257 531 |
    #: | `DENOMN_SOC` | `FusionScissions.csv` | 132 448 |
    #:
    #: ⚠️ **`DENOMN_SOC` n'est pas une relation NEQ→NEQ.** *Classée comme telle le
    #: 17 septembre par lecture trop rapide du fichier, et le gisement est resté
    #: ignoré une journée de plus.* La relation, c'est `NEQ_ASSUJ_REL` (78,5 %);
    #: la dénomination est **un nom rattaché à un NEQ vivant**, rempli à 99,9 %.
    #:
    #: **Nullable** : les lignes écrites avant cette colonne n'en portent pas, et
    #: `None` se lit « gisement inconnu, écrit avant le 17 septembre » — jamais
    #: « aucun gisement ».
    gisement: Mapped[str | None] = mapped_column(String(20), nullable=True)

    #: `STAT_NOM` et `TYP_NOM_ASSUJ` tels quels, jamais interprétés ici. Un nom
    #: « en vigueur, dénomination sociale » et un nom « en vigueur, autre nom »
    #: ne valent pas la même chose pour un humain qui arbitre, et ranger les deux
    #: sous un booléen perdrait la distinction sans rien simplifier.
    statut: Mapped[str] = mapped_column(String(15), nullable=False)
    type_nom: Mapped[str] = mapped_column(String(15), nullable=False)

    first_seen_at: Mapped[datetime] = mapped_column(default=utcnow)

    __table_args__ = (
        # GLOB par préfixe, comme `REQEntry.nom_normalise` — même discipline, même
        # raison : LIKE force un SCAN complet parce que sa comparaison par défaut
        # est insensible à la casse et que l'index n'a pas de collation NOCASE.
        Index("ix_req_noms_nom_normalise", "nom_normalise"),
    )
