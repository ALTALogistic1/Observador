"""L'index par MOTS du miroir — la clé de récupération qui ne dépend plus du
premier mot.

**Le fait qui fait exister ces deux tables** *(mesuré du 16 au 17 septembre)*.
La récupération s'ancre sur `nom_norm.split(" ")[0]`, et `normaliser` remplace
l'apostrophe et le point par une espace :

    "L'INDUSTRIE MONDIALE DU NORD INC."  →  'l industrie mondiale du nord inc'
                                             ↑ le préfixe est « l »

⚠️ **La clé de récupération est un MOT VIDE**, et `industrie`, `mondiale`, `nord`
sont dans la chaîne sans jamais servir. *Les trois gisements que le plafond de la
mesure C a dû refuser — `l` (309 788 lignes), `s` (221 412), `le` (205 071) —
sont exactement ceux-là.*

**Mesuré** : la borne de 2 000 coupe **4 217 lots sur 8 931 (47,2 %)**, dont
**74,3 % des « trop faibles »**. Et borne levée, **114 des 152 dossiers testés
franchissent le seuil** — des correspondances exactes que le lot n'avait jamais
présentées au scoreur.

## Pourquoi un index par mots plutôt qu'une borne plus grande

**Le coût dominant d'une résolution n'est pas le SQL, c'est le scorage flou** —
`process.extractOne` sur ~2 000 groupes. *Lever la borne sur `l` ne multiplie pas
une requête : il multiplie par 155 le nombre de formes à scorer.*

> **Une récupération qui présente 300 formes PERTINENTES au lieu de 2 000
> arbitraires coûte MOINS qu'aujourd'hui, pas plus.**

## Pourquoi DEUX tables

`req_mots` porte les couples `(mot, NEQ)`. `req_mots_frequence` porte, par mot,
le nombre de NEQ qui le portent — **c'est elle qui permet de choisir le mot LE
PLUS RARE du nom cherché**, donc de borner le lot par le pouvoir discriminant
plutôt que par un `LIMIT` arbitraire.

*Sans la fréquence, il faudrait la calculer à chaque résolution — un `COUNT` par
mot du nom, à chaque signal.* **Avec elle, c'est une lecture par clé primaire.**

⚠️ **Les deux se reconstruisent ENTIÈREMENT à chaque import**, depuis
`req_noms` — donc depuis `nom_normalise`, qui est une fonction pure du nom
publié. *Aucune dépendance à un ordre de fichier, à une colonne facultative ou à
un encodage observé une fois.*
"""
from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from falkye.models.base import BaseMiroir


class REQMot(BaseMiroir):
    """Un mot, et un NEQ dont au moins une forme le porte.

    **Clé composite `(mot, neq)`** — elle donne l'index sur `mot` gratuitement et
    déduplique à l'écriture. *Un NEQ dont trois noms portent « construction »
    n'apparaît qu'une fois : la récupération veut des NEQ candidats, pas des
    occurrences.*
    """

    __tablename__ = "req_mots"

    mot: Mapped[str] = mapped_column(String(100), primary_key=True)
    neq: Mapped[str] = mapped_column(String(20), primary_key=True)


class REQMotFrequence(BaseMiroir):
    """Combien de NEQ portent ce mot — **le pouvoir discriminant, précalculé**.

    *« ferme » en porte des dizaines de milliers, « bellavance » quelques
    dizaines.* **C'est ce qui permet de chercher par le mot le plus rare** au lieu
    du premier, et de rendre un lot petit ET pertinent.

    ⚠️ **Calculée par une seule requête après l'écriture des couples** —
    `INSERT … SELECT mot, COUNT(*) FROM req_mots GROUP BY mot`. *Rien ne passe par
    la mémoire de Python : c'est SQLite qui agrège.*
    """

    __tablename__ = "req_mots_frequence"

    mot: Mapped[str] = mapped_column(String(100), primary_key=True)
    neqs: Mapped[int] = mapped_column(Integer, nullable=False)
