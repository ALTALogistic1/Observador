"""Le pont `req_noms` survit-il à une première requête qui sature la borne?

**Le fait qui a écrit ces tests** *(2026-09-16)*. Après un réimport qui a mis
**1 505 879 noms** dans `req_noms`, le diagnostic n'a pas bougé d'une unité :
3 061 ambigus et 313 résolubles **exactement comme avant**. *Pas « peu de
gain » — zéro effet.* Un pont qui ajoute un million et demi de portes et ne
change aucune des trois catégories n'a pas été emprunté.

**La borne est appliquée au TOTAL**, et c'était volontaire :

    reste = max(0, limite - len(candidates))
    if reste:
        candidates += …req_noms…

⚠️ **Mais si la première requête rend déjà `limite` lignes, `reste` vaut zéro
et PAS UN SEUL nom de `req_noms` n'entre.** *Le préfixe de récupération est le
PREMIER MOT du nom* — « gestion », « les », « construction », « 9 » — donc la
saturation n'est pas un cas limite : **c'est le cas courant, et c'est exactement
là que le pont servirait.**

*Une borne qui protège du coût en supprimant l'apport protège du gain.*
"""
from __future__ import annotations

import pytest

from falkye.models.req_entry import REQEntry
from falkye.models.req_nom import REQNom
from falkye.sources.column_mapping import normaliser
from falkye.sources.req import candidats_par_nom

#: La borne réelle du moteur. Le test la sature délibérément.
BORNE = 2000


@pytest.fixture()
def miroir_sature(db_session):
    """Un miroir où le préfixe « gestion » rend déjà la borne entière, plus UNE
    entreprise que seul `req_noms` peut désigner.

    *C'est la forme du REQ réel* : 2,7 millions d'entrées, et des préfixes que
    des milliers de raisons sociales partagent.
    """
    for i in range(BORNE + 50):
        nom = f"gestion {i:05d} ltee"
        db_session.add(
            REQEntry(neq=f"11{i:08d}", nom=nom, nom_normalise=normaliser(nom), statut="IMMATRICULÉE")
        )
    # La cible : son nom ÉLU ne commence pas par « gestion », mais elle porte
    # « gestion … » comme AUTRE nom en vigueur. C'est précisément le cas des
    # 2 217 entreprises mesurées le 16 septembre.
    cible_nom = "9187 5678 quebec inc"
    db_session.add(
        REQEntry(neq="2299999999", nom=cible_nom, nom_normalise=normaliser(cible_nom), statut="IMMATRICULÉE")
    )
    pont = "gestion pierre tremblay"
    db_session.add(
        REQNom(
            neq="2299999999",
            nom=pont,
            nom_normalise=normaliser(pont),
            statut="V",
            type_nom="A",
        )
    )
    db_session.commit()
    return db_session


def test_la_premiere_requete_sature_bien_la_borne(miroir_sature):
    """Sans cette vérification, le test suivant pourrait passer pour la mauvaise
    raison — une borne non atteinte ne prouve rien du cas réel."""
    candidats = candidats_par_nom(miroir_sature, normaliser("gestion pierre tremblay"))
    assert len(candidats) >= BORNE, (
        f"la borne n'est pas saturée ({len(candidats)}), le décor ne reproduit pas "
        "le REQ réel et le test d'après ne dirait rien"
    )


def test_le_pont_req_noms_survit_a_la_saturation(miroir_sature):
    """**Le test qui décide.** La cible n'est atteignable QUE par `req_noms`.

    Si elle n'est pas dans les candidats, le pont bâti le 16 septembre — un
    million et demi de noms, trente-cinq minutes de réimport — **ne sert à rien
    dès que le préfixe est commun**, c'est-à-dire la plupart du temps.
    """
    candidats = candidats_par_nom(miroir_sature, normaliser("gestion pierre tremblay"))
    neqs = {c.neq for c in candidats}
    assert "2299999999" in neqs, (
        "l'entreprise atteignable uniquement par req_noms est ABSENTE des candidats : "
        "la première requête a saturé la borne, `reste` vaut zéro, et le pont n'a "
        "ajouté personne. C'est le cas courant, pas un cas limite — le préfixe de "
        "récupération est le premier mot du nom."
    )


def test_la_borne_totale_tient_toujours(miroir_sature, db_session):
    """**La part réservée ne doit pas devenir une borne doublée.** C'était la
    raison d'être de « ce qui reste » — le coût ne doit pas augmenter en silence
    pendant qu'on répare l'apport."""
    for i in range(BORNE):
        pont = f"gestion pont {i:05d}"
        db_session.add(
            REQEntry(
                neq=f"33{i:08d}", nom=pont, nom_normalise=normaliser(pont),
                statut="IMMATRICULÉE",
            )
        )
        db_session.add(
            REQNom(
                neq=f"33{i:08d}", nom=pont, nom_normalise=normaliser(pont),
                statut="V", type_nom="A",
            )
        )
    db_session.commit()

    candidats = candidats_par_nom(miroir_sature, normaliser("gestion pierre tremblay"))
    assert len(candidats) <= BORNE, (
        f"{len(candidats)} candidats pour une borne de {BORNE} : la part réservée "
        "a doublé le coût au lieu de partager le budget"
    )


def test_la_recuperation_est_reproductible(miroir_sature):
    """**Deux exécutions identiques doivent rendre la même chose.**

    Un `LIMIT` sans `ORDER BY` rend 2 000 lignes *au hasard de l'index* — et
    « au hasard » veut dire susceptible de changer après un réimport, un
    `VACUUM`, une insertion. *Le rejeu devenait non reproductible, et une passe
    qui ÉCRIT dans la base ne peut pas s'appuyer sur un tirage au sort.*

    ⚠️ Ce test verrouille la REPRODUCTIBILITÉ, pas la pertinence : la tranche
    retenue reste alphabétique et arbitraire.
    """
    nom = normaliser("gestion pierre tremblay")
    premier = [c.neq for c in candidats_par_nom(miroir_sature, nom)]
    second = [c.neq for c in candidats_par_nom(miroir_sature, nom)]
    assert premier == second, "deux appels identiques rendent deux listes différentes"
    assert len(set(premier)) == len(premier), "un NEQ apparaît deux fois dans les candidats"
