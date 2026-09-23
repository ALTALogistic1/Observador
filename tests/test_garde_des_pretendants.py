"""⛔ **La garde des prétendants, là où la règle vit** *(2026-09-23)*.

**Le défaut qu'elle corrige.** `falkye/resolution.py::resolve_company` cherchait
un `Company` **par NEQ** avant d'en créer un : plusieurs noms détectés résolus
vers le même NEQ étaient rattachés au MÊME dossier — **fusionnés de fait**,
silencieusement. *La garde du 17 septembre ne vivait que dans
`outils/pose_du_neq.py`, donc elle ne protégeait que les passes par LOT.*

⚠️ **Décision du 16 septembre : conservation toujours, aucune fusion.** *« Six
dossiers réunis sur un seul NEQ, c'est une fusion de fait »* (Alexandre,
2026-09-23).

**Le fait qui a écrit la règle** : le NEQ 8879690699 attirait **26 dossiers** —
CISSS, CIUSSS, CHUM, McGill, Institut de Cardiologie — 26 organisations
RÉELLEMENT distinctes, scores de 95 à 100. *Le test `test_les_vingt_six_…`
rejoue cette forme-là : il CASSE volontairement la garde en poussant plusieurs
dossiers sur un seul NEQ, et vérifie qu'elle refuse.*
"""
from datetime import datetime, timedelta, timezone

import pytest

from falkye import resolution
from falkye.models.company import Company, StatutResolution
from falkye.models.diagnostic_journal import DiagnosticJournal, TypeDiagnostic
from falkye.models.req_entry import REQEntry
from falkye.models.req_nom import REQNom
from falkye.resolution import (
    PRETENDANTS_MAX_POUR_TRANCHER,
    STATUT_PRETENDANT_REFUSE,
    compter_pretendants,
    resolve_company,
)
from falkye.sources.base import RawSignal
from falkye.sources.column_mapping import normaliser

#: Le NEQ que tous les prétendants visent — celui du fait de 2026-09-17.
NEQ_ATTIRANT = "8879690699"

#: Des noms qui désignent des organisations RÉELLEMENT DISTINCTES et que le
#: registre porte toutes sous un seul NEQ. ⚠️ *Ce n'est pas une donnée fabriquée
#: présentée comme une détection : c'est la FORME du cas réel, réduite au
#: minimum qui l'expose.*
NOMS_DE_LA_FAMILLE = (
    "CISSS de la Monteregie-Centre",
    "CISSS de la Gaspesie",
    "CIUSSS de l'Outaouais",
    "Centre hospitalier de l'Universite de Montreal",
    "Centre universitaire de sante McGill",
    "Institut de Cardiologie de Montreal",
)


def _raw(nom, *, ref="ref", neq=None, ville=None):
    return RawSignal(
        signal_type_id="appel_offres",
        nom_entreprise=nom,
        detected_at=datetime.now(timezone.utc),
        source_ref=ref,
        neq=neq,
        ville=ville,
    )


@pytest.fixture
def famille(db_session):
    """Un seul NEQ au registre, portant TOUTES les formes de la famille.

    *C'est ainsi que `resolve_neq_by_name` rend le même NEQ pour des noms
    détectés différents* — il regroupe par NEQ et prend le MEILLEUR de ses noms.
    """
    db_session.add(
        REQEntry(
            neq=NEQ_ATTIRANT,
            nom=NOMS_DE_LA_FAMILLE[0],
            nom_normalise=normaliser(NOMS_DE_LA_FAMILLE[0]),
            statut="immatriculee",
        )
    )
    for nom in NOMS_DE_LA_FAMILLE:
        db_session.add(
            REQNom(neq=NEQ_ATTIRANT, nom=nom, nom_normalise=normaliser(nom),
                   statut="V", type_nom="AUTRE NOM UTILISE AU QUEBEC")
        )
    db_session.flush()
    return db_session


def _refus(db_session):
    return (
        db_session.query(DiagnosticJournal)
        .filter(DiagnosticJournal.statut == STATUT_PRETENDANT_REFUSE)
        .all()
    )


# --------------------------------------------------------------------------
# 1. LE TEST QUI LA CASSE VOLONTAIREMENT
# --------------------------------------------------------------------------


def test_les_vingt_six_ne_sont_pas_FUSIONNES_par_la_resolution(famille):
    """⛔ **La garde cassée volontairement** — on pousse toute la famille sur un
    seul NEQ, et on vérifie qu'elle REFUSE.

    *Avant le 2026-09-23, ce test rendait UN dossier pour les six.*
    """
    db_session = famille
    dossiers = [
        resolve_company(db_session, _raw(nom, ref=f"ref-{i}"))
        for i, nom in enumerate(NOMS_DE_LA_FAMILLE)
    ]

    # ⛔ SIX DOSSIERS, PAS UN. La conservation, mot pour mot.
    assert len({d.id for d in dossiers}) == len(NOMS_DE_LA_FAMILLE)

    # ⛔ UN SEUL porte le NEQ — `Company.neq` est UNIQUE, et le premier arrivé
    # le garde. *Le lui retirer serait une écriture qui efface une identité.*
    porteurs = [d for d in dossiers if d.neq == NEQ_ATTIRANT]
    assert len(porteurs) == 1
    assert porteurs[0].id == dossiers[0].id

    # Les autres sont des dossiers séparés, SANS NEQ, et marqués indécis.
    for refuse in dossiers[1:]:
        assert refuse.neq is None
        assert refuse.statut_resolution == StatutResolution.AMBIGU

    # Chaque refus est consigné, et le RANG monte — c'est le seul décompte que
    # la résolution puisse produire, puisqu'elle voit un dossier à la fois.
    assert len(_refus(db_session)) == len(NOMS_DE_LA_FAMILLE) - 1
    assert compter_pretendants(db_session, dossiers[0].id) == len(NOMS_DE_LA_FAMILLE)


def test_le_refus_dit_AU_DELA_DE_DEUX_a_partir_du_troisieme(famille):
    """⚠️ *Le seuil du 17 septembre ne DÉCIDE plus rien ici — il NOMME.* Le
    détenteur garde son NEQ quel que soit le nombre de prétendants; ce que la
    résolution peut faire, c'est rendre ces NEQ-là VISIBLES."""
    db_session = famille
    for i, nom in enumerate(NOMS_DE_LA_FAMILLE[:3]):
        resolve_company(db_session, _raw(nom, ref=f"ref-{i}"))

    textes = [e.texte_description for e in _refus(db_session)]
    assert len(textes) == 2
    assert "AU-DELÀ DE" not in textes[0]  # 2e prétendant — dans la limite
    assert f"AU-DELÀ DE {PRETENDANTS_MAX_POUR_TRANCHER}" in textes[1]  # 3e


# --------------------------------------------------------------------------
# 2. CE QUE LA GARDE NE DOIT PAS CASSER
# --------------------------------------------------------------------------


def test_la_re_detection_du_MEME_nom_reste_UN_SEUL_dossier(famille):
    """**Le dossier cumulatif fait son travail.** *Une re-détection sous la même
    graphie n'est pas un prétendant* — et si la garde la refusait, chaque signal
    créerait un dossier."""
    db_session = famille
    a = resolve_company(db_session, _raw(NOMS_DE_LA_FAMILLE[0], ref="r1"))
    b = resolve_company(db_session, _raw(NOMS_DE_LA_FAMILLE[0], ref="r2"))
    assert a.id == b.id
    assert b.neq == NEQ_ATTIRANT
    assert _refus(db_session) == []


def test_le_NEQ_AFFIRME_par_la_source_ne_passe_pas_par_la_garde(db_session):
    """⚠️ **La frontière, posée pour être vue.** *Un NEQ qu'une source AFFIRME
    n'est pas un appariement* — et la garde du 17 septembre est née d'un
    appariement par le nom. Deux graphies sous le même NEQ affirmé désignent la
    même personne morale."""
    a = resolve_company(db_session, _raw("Les Services EXP inc.", ref="r1", neq="1112223334"))
    b = resolve_company(db_session, _raw("Services EXP inc. (Les)", ref="r2", neq="1112223334"))
    assert a.id == b.id
    assert b.neq == "1112223334"
    assert b.statut_resolution == StatutResolution.RESOLU
    assert _refus(db_session) == []


def test_un_NEQ_libre_est_pose_comme_avant(famille):
    """*La garde ne peut que RÉDUIRE les écritures, jamais en produire une* — et
    quand personne ne détient le NEQ, elle ne fait rien du tout."""
    db_session = famille
    company = resolve_company(db_session, _raw(NOMS_DE_LA_FAMILLE[0]))
    assert company.neq == NEQ_ATTIRANT
    assert company.statut_resolution == StatutResolution.RESOLU
    assert _refus(db_session) == []


# --------------------------------------------------------------------------
# 3. CE QUE LE REFUS LAISSE DERRIÈRE LUI
# --------------------------------------------------------------------------


def test_le_refus_est_IDEMPOTENT(famille):
    """*Sans idempotence, un dossier refusé re-détecté cinquante fois écrirait
    cinquante entrées, et le décompte compterait des SIGNAUX au lieu de
    dossiers.*"""
    db_session = famille
    resolve_company(db_session, _raw(NOMS_DE_LA_FAMILLE[0], ref="r1"))
    for i in range(4):
        resolve_company(db_session, _raw(NOMS_DE_LA_FAMILLE[1], ref=f"r-{i}"))
    assert len(_refus(db_session)) == 1


def test_le_refus_ne_se_defait_PAS_par_confirmer_fusion(famille):
    """⚠️ **Délibérément pas `a_examiner`.** *`falkye diagnostic
    confirmer-fusion` n'agit que sur `a_examiner`* — sans quoi un coup de CLI
    fusionnerait les deux dossiers que la garde vient de séparer. **Défaire un
    refus est une décision d'Alexandre, pas une commande qui existe déjà.**"""
    db_session = famille
    resolve_company(db_session, _raw(NOMS_DE_LA_FAMILLE[0], ref="r1"))
    resolve_company(db_session, _raw(NOMS_DE_LA_FAMILLE[1], ref="r2"))
    (entree,) = _refus(db_session)
    assert entree.statut != "a_examiner"
    assert entree.type_diagnostic == TypeDiagnostic.CANDIDAT_FUSION_ENTREPRISE
    assert entree.company_id_principal is not None
    assert entree.company_id_candidat is not None
    assert entree.score_similarite is not None


def test_le_refus_ne_RETIRE_rien_au_detenteur(famille):
    """**La garde ne peut que réduire les écritures.** *Rien n'est retiré, rien
    n'est écrasé — le détenteur ne sait même pas qu'un prétendant est passé.*"""
    db_session = famille
    detenteur = resolve_company(db_session, _raw(NOMS_DE_LA_FAMILLE[0], ref="r1"))
    avant = (detenteur.id, detenteur.neq, detenteur.nom_detecte, detenteur.statut_resolution)
    resolve_company(db_session, _raw(NOMS_DE_LA_FAMILLE[1], ref="r2"))
    db_session.refresh(detenteur)
    assert (detenteur.id, detenteur.neq, detenteur.nom_detecte,
            detenteur.statut_resolution) == avant


def test_un_dossier_refuse_reste_rapprochable_des_autres_sans_NEQ(famille):
    """*Un refus qui recopierait le chemin sans-NEQ en divergerait*, et un
    dossier refusé cesserait de profiter du rapprochement flou qui protège les
    autres. **`_dossier_sans_neq` est le MÊME geste pour les deux issues.**"""
    db_session = famille
    resolve_company(db_session, _raw(NOMS_DE_LA_FAMILLE[0], ref="r1"))
    a = resolve_company(db_session, _raw(NOMS_DE_LA_FAMILLE[1], ref="r2"))
    b = resolve_company(db_session, _raw(NOMS_DE_LA_FAMILLE[1] + " ", ref="r3"))
    assert a.id == b.id  # le nom normalisé est le même — chemin EXACT


# --------------------------------------------------------------------------
# 4. LA GARDE VIT DANS `falkye/`, ET `outils/` L'EMPRUNTE
# --------------------------------------------------------------------------


def test_la_constante_vit_dans_falkye_et_pose_du_neq_l_EMPRUNTE():
    """⚠️ **C'était le défaut du 23 septembre** : la garde ne vivait que dans
    `outils/`. *Deux copies d'une règle de conservation divergent sans que rien
    ne le dise, et le geste est un geste d'ÉCRITURE.*"""
    import pathlib

    from outils import pose_du_neq

    assert pose_du_neq.PRETENDANTS_MAX_POUR_TRANCHER is PRETENDANTS_MAX_POUR_TRANCHER
    source = pathlib.Path("outils/pose_du_neq.py").read_text(encoding="utf-8")
    assert "from falkye.resolution import PRETENDANTS_MAX_POUR_TRANCHER" in source
    assert "PRETENDANTS_MAX_POUR_TRANCHER = 2" not in source


def test_la_resolution_compte_les_pretendants_DANS_falkye():
    """*Vérifié sur le code, pas sur une sortie* — contre-épreuve du test qui
    affirmait l'inverse jusqu'au 2026-09-23."""
    import pathlib

    source = pathlib.Path("falkye/resolution.py").read_text(encoding="utf-8")
    assert "PRETENDANTS_MAX_POUR_TRANCHER = 2" in source
    assert "def garde_des_pretendants(" in source
