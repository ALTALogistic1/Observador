"""L'archive du diff refuse-t-elle la cible que personne n'a choisie?

**Le fait qui a écrit ces tests** *(2026-09-16)*. L'import du REQ a lu 2 730 146
lignes, chargé l'état précédent, calculé le diff — **puis est mort sur le
`mkdir` de l'archivage** :

    OSError: [Errno 30] Read-only file system: 'cache'

`FALKYE_DIFF_ARCHIVE_DIR` n'était posée nulle part, et le repli
`./cache/diff_archive` est **relatif au répertoire courant** — sous l'unité,
`/opt/falkye/code/cache`, que `ProtectSystem=strict` rend en lecture seule.

⚠️ **C'est le repli silencieux de la base, une porte plus loin.** *Et sur une
machine où le répertoire courant est inscriptible, il n'aurait rien dit du
tout* : il aurait déposé 679 Mo à côté du code, perdus au déploiement suivant.
**C'est ce que la suite de tests faisait** — `cache/diff_archive/` existait dans
l'arbre de travail, invisible parce que `/cache/` est ignoré par git.

**Deux exigences, et la seconde compte autant que la première.**

1. **Refuser** quand personne n'a choisi.
2. **Refuser EN TÊTE**, avant le travail. *Une garde qui parle après trente
   minutes de lecture coûte trente minutes* — et c'est exactement ce que
   l'`Errno 30` a coûté.
"""
from __future__ import annotations

import pytest

from falkye import diff_engine
from falkye.diff_engine import (
    DOSSIER_ARCHIVE_PAR_DEFAUT,
    ArchiveSansCible,
    LigneSnapshot,
    executer_diff,
    verifier_cible_archive,
)


@pytest.fixture()
def sans_cible(monkeypatch):
    """Remet le repli — le décor autouse de `conftest` en pose un vrai."""
    monkeypatch.setattr(diff_engine, "ARCHIVE_DIR", DOSSIER_ARCHIVE_PAR_DEFAUT)


def test_la_cible_par_defaut_est_refusee(sans_cible):
    with pytest.raises(ArchiveSansCible) as capture:
        verifier_cible_archive()
    message = str(capture.value)
    assert "FALKYE_DIFF_ARCHIVE_DIR" in message, "la variable doit être NOMMÉE"
    assert "/var/lib/falkye/diff_archive" in message, "le remède doit être donné"
    assert "falkye.env" in message, "où poser la ligne doit être dit"


def test_une_cible_choisie_passe(tmp_path, monkeypatch):
    monkeypatch.setattr(diff_engine, "ARCHIVE_DIR", tmp_path / "archives")
    verifier_cible_archive()
    assert (tmp_path / "archives").is_dir(), "le répertoire doit être créé"


def test_une_cible_non_inscriptible_est_nommee_comme_telle(tmp_path, monkeypatch):
    """⚠️ Un FICHIER en guise de parent, jamais `chmod 0500`.

    La suite tourne en root dans le conteneur, et **root passe outre les bits de
    permission** — un test qui s'appuierait dessus passerait ici et ne dirait
    rien de l'hôte. Voir l'en-tête de `tests/conftest.py`, troisième forme.
    """
    barrage = tmp_path / "barrage"
    barrage.write_text("je suis un fichier, pas un répertoire")
    monkeypatch.setattr(diff_engine, "ARCHIVE_DIR", barrage / "archives")

    with pytest.raises(ArchiveSansCible) as capture:
        verifier_cible_archive()
    message = str(capture.value)
    assert "ReadWritePaths" in message, (
        "sous une unité, c'est la directive de confinement qui interdit l'écriture — "
        "un Errno 30 nu ne la nomme pas"
    )


def test_larchivage_direct_refuse_aussi(sans_cible):
    """Défense en profondeur : un appelant direct (rejeu d'une quarantaine) ne
    passe pas par `executer_diff`, donc pas par la garde de tête."""
    with pytest.raises(ArchiveSansCible):
        diff_engine._archiver_snapshot("req", [LigneSnapshot(cle="1", champs={"a": "b"})])


def test_le_refus_tombe_AVANT_le_travail(db_session, tmp_path, monkeypatch):
    """**Le point de ces tests.** Le refus doit précéder le travail, pas le
    suivre : c'est la différence entre perdre une seconde et perdre trente
    minutes.

    ⚠️ **Il faut un VRAI diff, pas un run de référence.** Un premier passage
    amorce l'état et rend la main *sans jamais archiver* — le piège ne se
    déclencherait pas, et le test passerait pour la mauvaise raison. *Une
    assertion qui ne peut pas échouer ment sur ce qu'elle vérifie.* On amorce
    donc avec une cible valide, puis on la retire pour le second passage, qui
    est celui qui archive.
    """
    monkeypatch.setattr(diff_engine, "ARCHIVE_DIR", tmp_path / "archives")
    executer_diff(
        db_session, source_id="req",
        lignes=[LigneSnapshot(cle="1", champs={"a": "b"})],
        colonnes_vues={"a": ""}, champs_pertinents={"a"},
    )

    atteint = []
    vrai = diff_engine._champs_precedents
    monkeypatch.setattr(
        diff_engine, "_champs_precedents",
        lambda *a, **k: (atteint.append(1), vrai(*a, **k))[1],
    )
    monkeypatch.setattr(diff_engine, "ARCHIVE_DIR", DOSSIER_ARCHIVE_PAR_DEFAUT)

    with pytest.raises(ArchiveSansCible):
        executer_diff(
            db_session, source_id="req",
            lignes=[LigneSnapshot(cle="1", champs={"a": "MODIFIÉ"})],
            colonnes_vues={"a": ""}, champs_pertinents={"a"},
        )

    assert not atteint, (
        "le diff a lu l'état précédent avant de refuser — la garde est trop bas "
        "dans executer_diff, et sur le REQ ça coûte trente minutes"
    )
