"""Le chemin de production peut-il fabriquer, puis rencontrer, un doublon de nom?

**La question d'Alexandre** *(2026-09-16)*. J'ai qualifié `scalar_one_or_none()`
de « défaut VIVANT sur le chemin de production » — **sans en donner la preuve**,
et le corpus veut que la preuve voyage avec le fait. Deux lectures possibles :

1. le chemin a déjà levé, et il y a une trace au journal;
2. « vivant » est déduit de la lecture du code — *ce serait alors la conformité
   accidentelle du cas 27.*

**Ces tests tranchent la partie qui se tranche ici : le MÉCANISME.** Ils ne
disent rien de l'OCCURRENCE — *« est-ce arrivé » se lit dans les journaux et
dans `doublons_entreprises`, pas dans un test.*

## Ce qui protégeait le chemin, et pourquoi c'est un accident

`resolve_company` ne crée un second dossier que si `_find_unresolved_company`
rend `None` **et** que le rapprochement flou échoue. Or **un nom normalisé
IDENTIQUE score 100**, donc au-dessus de `SEUIL_FUSION_AUTO = 95` : le doublon
est absorbé et jamais créé.

⚠️ **Mais cette protection n'est pas une garde — c'est un effet de bord d'un
autre mécanisme.** *C'est exactement la forme du cas 27 : la conformité
accidentelle prise pour une garantie.*

**Et la fissure est nommable** : `requete_candidats_prefixe` est bornée par
`LIMITE_CANDIDATS = 500` **sans `ORDER BY`** — la même forme que la borne
corrigée ce matin dans `candidats_par_nom`. *Si le préfixe sature la borne et
que le vrai jumeau n'est pas dans la tranche rendue, le score n'a jamais lieu,
et le second dossier est créé.*
"""
from __future__ import annotations

import pytest
from sqlalchemy.exc import MultipleResultsFound

from falkye.dedup_entreprises import LIMITE_CANDIDATS
from falkye.models.company import Company
from falkye.resolution import _find_unresolved_company
from falkye.sources.column_mapping import normaliser

NOM = "gestion pierre tremblay"


def test_la_borne_du_dedoublonnage_na_pas_dordre():
    """**Le constat, lu dans le code.** Une borne sans ordre ne rend pas « les
    500 plus proches » : elle rend 500 lignes au hasard de l'index."""
    from falkye.dedup_entreprises import requete_candidats_prefixe

    sql = str(requete_candidats_prefixe("gestion"))
    assert "LIMIT" in sql.upper(), "la requête n'est plus bornée — ce test a vieilli"
    assert "ORDER BY" not in sql.upper(), (
        "un ORDER BY est apparu : la fissure décrite ici est refermée, "
        "et ce test doit être réécrit plutôt que supprimé"
    )


def test_le_jumeau_echappe_a_la_borne_saturee(db_session):
    """⚠️ **Le mécanisme, démontré.** Le vrai jumeau existe, et la recherche
    bornée ne le rend pas — donc `resolve_company` ne peut pas le fusionner.

    *C'est l'étape qui manque pour que le doublon naisse.*
    """
    from falkye.dedup_entreprises import trouver_meilleur_candidat_fusion

    for i in range(LIMITE_CANDIDATS + 50):
        nom = f"gestion {i:05d} autre chose"
        db_session.add(
            Company(neq=None, nom_detecte=nom, nom_detecte_normalise=normaliser(nom))
        )
    jumeau = Company(neq=None, nom_detecte="Gestion Pierre Tremblay",
                     nom_detecte_normalise=normaliser(NOM))
    db_session.add(jumeau)
    db_session.commit()

    meilleur = trouver_meilleur_candidat_fusion(db_session, NOM, ville=None,
                                                exclure_id=None)
    assert meilleur is None or meilleur.company.id != jumeau.id, (
        "le jumeau a été retrouvé malgré la borne — le décor ne reproduit pas la "
        "saturation, et la démonstration suivante ne dirait rien"
    )


def test_deux_dossiers_de_meme_nom_font_LEVER_le_chemin_de_production(db_session):
    """**La conséquence, démontrée sur la fonction que le produit appelle.**

    `_find_unresolved_company` est traversée à CHAQUE signal non résolu. Deux
    dossiers de même nom normalisé, et elle lève — *l'exception n'arrive donc pas
    dans un outil, elle arrive dans le cycle.*
    """
    for nom in ("Gestion Pierre Tremblay", "GESTION PIERRE TREMBLAY inc"[:23]):
        db_session.add(
            Company(neq=None, nom_detecte=nom, nom_detecte_normalise=normaliser(NOM))
        )
    db_session.commit()

    with pytest.raises(MultipleResultsFound):
        _find_unresolved_company(db_session, "Gestion Pierre Tremblay")


def test_un_seul_dossier_ne_leve_pas(db_session):
    """La garde de la garde : sans doublon, le chemin rend la ligne. *Sinon le
    test précédent pourrait passer pour une raison qui n'est pas la sienne.*"""
    db_session.add(
        Company(neq=None, nom_detecte="Gestion Pierre Tremblay",
                nom_detecte_normalise=normaliser(NOM))
    )
    db_session.commit()
    assert _find_unresolved_company(db_session, "Gestion Pierre Tremblay") is not None
