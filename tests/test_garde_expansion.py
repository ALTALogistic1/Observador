"""La passe d'expansion ne s'exécute pas quand aucun lien ne peut exister.

**Un non-geste démontré, pas une optimisation.** Un candidat n'est retenu que
s'il porte une province QUI DIFFÈRE. Avec une seule province au registre actif,
l'ensemble des candidats est vide pour toute entreprise — la passe rendait zéro
lien après avoir balayé `companies` en entier et chargé les signaux de chaque
entreprise, soit une des deux passes du coût mesuré le 2026-09-11.

Mesuré avant de poser la garde : `req` (qc) est la seule source active à porter
un `province_code`, et **0 entreprise sur 11 556** vient des trois sources
provinciales en veilleuse.
"""
from __future__ import annotations

from datetime import datetime

import pytest

from falkye.expansion_interprovinciale import (
    detecter_expansions,
    evaluer_pour_company,
    expansion_possible,
    provinces_au_registre_actif,
)


def _registre_a(registry, provinces: dict[str, str]):
    """Un registre où les sources nommées portent ces provinces-là.

    `SourceDef` est gelée — on remplace les fiches plutôt que de les muter, ce
    qui évite aussi qu'un test en salisse un autre.
    """
    from dataclasses import replace

    registry.sources = {
        sid: replace(source, province_code=provinces.get(sid))
        for sid, source in registry.sources.items()
    }
    return registry


def test_le_registre_reel_ne_permet_aucune_expansion(registry):
    """L'état du 2026-09-11 : une seule province active. Ce test tombera le jour
    où une source d'une autre province repassera `actif` — et c'est exactement
    ce qu'on veut, la garde se lève d'elle-même."""
    assert provinces_au_registre_actif(registry) == {"qc"}
    assert expansion_possible(registry) is False


def test_deux_provinces_rallument_la_passe(registry):
    actives = [s.id for s in registry.sources_actives()][:2]
    if len(actives) < 2:
        pytest.skip("registre sans deux sources actives")
    _registre_a(registry, {actives[0]: "qc", actives[1]: "on"})

    assert expansion_possible(registry) is True


def test_la_passe_ignoree_ne_lit_rien_du_tout(db_session, registry):
    """Pas seulement « rend zéro lien » : elle ne doit émettre AUCUNE requête.
    C'est le balayage complet de `companies` et le chargement des signaux par
    entreprise qu'on retire, pas le résultat."""
    from falkye.models.company import Company

    db_session.add(Company(nom_detecte="Test", nom_detecte_normalise="test"))
    db_session.commit()

    emises: list[str] = []
    from sqlalchemy import event

    moteur = db_session.get_bind(mapper=Company.__mapper__)

    @event.listens_for(moteur, "before_cursor_execute")
    def _noter(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        emises.append(statement)

    try:
        liens = detecter_expansions(db_session, registry)
    finally:
        event.remove(moteur, "before_cursor_execute", _noter)

    assert liens == []
    assert emises == [], emises


def test_un_lien_deja_en_base_donne_TOUJOURS_son_bonus(db_session, registry):
    """La garde porte sur la PASSE, pas sur la lecture — et c'est une décision.

    Posée aux deux endroits le 2026-09-11, elle a été resserrée le jour même :
    trois tests existants ont montré qu'un lien **déjà en base** cessait de
    donner son bonus dès que le registre ne pouvait plus en créer de nouveau.
    *Ne plus créer et cesser de lire sont deux gestes différents* : le premier
    est un non-geste démontré, le second retirerait en silence une observation
    légitime déjà acquise. Le motif du coût est tombé de lui-même — depuis
    `ix_liens_interprovinciaux_company_id_b`, cette lecture coûte deux lignes.
    """
    from falkye.models.company import Company
    from falkye.models.expansion_interprovinciale import LienInterprovincial

    a = Company(nom_detecte="Alpha", nom_detecte_normalise="alpha")
    b = Company(nom_detecte="Alpha", nom_detecte_normalise="alpha")
    db_session.add_all([a, b])
    db_session.flush()
    db_session.add(
        LienInterprovincial(
            company_id_a=min(a.id, b.id), company_id_b=max(a.id, b.id),
            province_a="qc", province_b="on", score_correspondance=100.0,
        )
    )
    db_session.commit()

    assert expansion_possible(registry) is False  # la passe, elle, reste éteinte
    assert evaluer_pour_company(db_session, a).bonus > 0.0
