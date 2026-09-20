#!/usr/bin/env python3
"""La ville qu'un dossier porte dans ses signaux, et d'où elle vient.

**Extraite pour être empruntée** *(2026-09-17)*. `outils/departage_par_ville.py`
la MESURE, `outils/promotion_ville.py` l'APPLIQUE — et *une mesure qui compte une
chose pendant qu'un correctif en écrit une autre est un rapport sur une
population imaginaire.* **Même règle que `requete_nom_exact`, `neq_retenu` et
`famille_de` : ce qui décide se nomme une fois et s'emprunte.**

⚠️ **Rien ici n'écrit.** La fonction rend ce qu'elle a trouvé et **ce qu'elle
refuse** — à l'appelant de décider quoi en faire.

⚠️ **`cles_ville` et `cles_adresse` sont des PARAMÈTRES depuis le 20 septembre**,
et leurs valeurs par défaut sont celles de la production. *Ils existent pour
qu'un chiffrage puisse demander « et si on lisait une clé de plus? » par un
APPEL de cette fonction, jamais par une copie* — le même motif que `niveaux=`
sur `departager_ladresse`. **Les passer depuis le pipeline serait un changement
de règle sans Alexandre.**
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

#: Les clés de `Signal.champs` qui portent une ville TELLE QUELLE, selon les
#: connecteurs. *Une clé par graphie rencontrée — la liste est une observation,
#: pas une norme.*
CLES_VILLE = ("ville", "city", "municipalite", "locality")

#: La clé qui porte une adresse COMBINÉE, dont la ville doit être extraite.
CLE_ADRESSE = "adresse"


@dataclass
class VilleVue:
    """Une ville trouvée pour un dossier, avec sa traçabilité."""

    ville: str
    provenance: str
    source_id: str
    #: Toutes les graphies distinctes trouvées dans les signaux de ce dossier.
    #: *Une seule = concordance; plusieurs = contradiction.*
    variantes: tuple[str, ...]

    @property
    def contradictoire(self) -> bool:
        return len(self.variantes) > 1


def ville_depuis_adresse(adresse: str | None) -> str | None:
    """La municipalité d'une adresse EIMT — `'St-Isidore, QC J0L 2A'` → `'St-Isidore'`.

    ⚠️ **UNE CONVENTION DE LECTURE, PAS UN CHAMP.** La forme observée est
    « municipalité, PROVINCE code postal ». On prend ce qui précède la première
    virgule — *et une adresse qui n'en porte pas ne rend rien, plutôt qu'une rue
    entière prise pour une municipalité.*
    """
    if not adresse or "," not in adresse:
        return None
    tete = adresse.split(",")[0].strip()
    return tete or None


def villes_des_signaux(db_session, ids: set[int], cles_ville=CLES_VILLE,
                       cles_adresse=(CLE_ADRESSE,)) -> dict[int, VilleVue]:
    """Pour chaque dossier de `ids`, la ville que ses signaux portent.

    ⚠️ **Pas « la première rencontrée ».** *Un dossier peut porter plusieurs
    signaux, et retenir celui que la base rend en premier promeut l'ordre du
    fichier au rang de critère (cas 19).* **On récolte TOUT**, on préfère une clé
    EXPLICITE à une tête d'adresse dérivée, et on garde les variantes pour que
    l'appelant sache si les signaux se contredisent.
    """
    from sqlalchemy import select

    from falkye.models.signal import Signal
    from falkye.sources.column_mapping import normaliser

    vues: dict[int, list[tuple[int, str, str, str]]] = defaultdict(list)
    for company_id, champs, source_id in db_session.execute(
        select(Signal.company_id, Signal.champs, Signal.source_id)
        .execution_options(yield_per=2000)
    ):
        if company_id not in ids:
            continue
        champs = champs or {}
        for cle in cles_ville:
            valeur = champs.get(cle)
            if valeur:
                vues[company_id].append(
                    (0, str(valeur), f"champs[{cle!r}]", source_id or "?")
                )
                break
        else:
            for cle in cles_adresse:
                depuis = ville_depuis_adresse(champs.get(cle))
                if depuis:
                    vues[company_id].append(
                        (1, depuis, f"champs[{cle!r}] (tête)", source_id or "?")
                    )
                    break

    trouvees: dict[int, VilleVue] = {}
    for company_id, lot in vues.items():
        variantes = tuple(sorted({normaliser(v) for _, v, _, _ in lot}))
        rang, ville, provenance, source = sorted(lot)[0]
        trouvees[company_id] = VilleVue(
            ville=ville, provenance=provenance, source_id=source, variantes=variantes
        )
    return trouvees
