"""L'outil compte-t-il le gain, ou compte-t-il autre chose?

**Un outil de mesure qui se trompe est pire qu'une absence de mesure** : il rend
un chiffre qu'on croira. La population de ces tests a une réponse connue.

Trois dossiers sans NEQ résolvent vers deux NEQ :
  - un NEQ **libre**, visé par **un** dossier  → posable aujourd'hui;
  - un NEQ **déjà porté** par un dossier résolu → perdu aujourd'hui, **nom de
    plus** demain.

Donc : posables = 1, perdus = 1, gain = 1, **NEQ distincts = 2 pour 2 dossiers
résolus**.
"""
from __future__ import annotations

import pytest

from falkye.models.company import Company
from falkye.models.req_entry import REQEntry
from falkye.sources.column_mapping import normaliser
from outils import apport_noms_multiples


@pytest.fixture()
def population(db_session, monkeypatch):
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")

    for neq, nom in (
        ("5555555555", "boulangerie saint-viateur inc"),
        ("6666666666", "plomberie rousseau et fils ltee"),
    ):
        db_session.add(
            REQEntry(neq=neq, nom=nom, nom_normalise=normaliser(nom), statut="IMMATRICULÉE")
        )

    def c(nom, neq=None):
        return Company(neq=neq, nom_detecte=nom, nom_detecte_normalise=normaliser(nom))

    db_session.add_all([
        c("Boulangerie Saint-Viateur Inc"),                    # NEQ libre → posable
        c("Plomberie Rousseau et Fils Ltee"),                  # NEQ déjà porté → perdu
        c("Plomberie Rousseau", neq="6666666666"),             # le porteur
        c("Zzyzx Rien Du Tout"),                               # aucun NEQ retenu
    ])
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def test_le_posable_et_le_perdu_sont_distingues(population, capsys):
    assert apport_noms_multiples.main(["--exemples", "0"]) == 0
    sortie = capsys.readouterr().out
    assert "NEQ posés                   : 1" in sortie
    assert "PERDUS, NEQ déjà porté      : 1" in sortie, (
        "le dossier dont le NEQ est déjà porté n'est pas compté comme perdu"
    )


def test_le_gain_est_le_perdu(population, capsys):
    """*« Perdu » veut dire : le produit SAIT quelle entreprise c'est, et n'a
    nulle part où le mettre.* Le gain de la forme neuve, c'est exactement ça."""
    assert apport_noms_multiples.main(["--exemples", "0"]) == 0
    assert "GAIN sur la forme actuelle  : 1" in capsys.readouterr().out


def test_les_NEQ_distincts_sont_rapportes(population, capsys):
    """**Un compte de dossiers répond « combien de lignes », jamais « combien
    d'entreprises ».**"""
    assert apport_noms_multiples.main(["--exemples", "0"]) == 0
    sortie = capsys.readouterr().out
    assert "NEQ DISTINCTS visés         : 2" in sortie


def test_ce_que_rien_ne_resout_est_compte_a_part(population, capsys):
    assert apport_noms_multiples.main(["--exemples", "0"]) == 0
    assert "aucun NEQ retenu            : 1" in capsys.readouterr().out


def test_loutil_NECRIT_RIEN(population):
    from sqlalchemy import select

    avant = {c.id: c.neq for c in population.execute(select(Company)).scalars().all()}
    assert apport_noms_multiples.main(["--exemples", "0"]) == 0
    population.expire_all()
    apres = {c.id: c.neq for c in population.execute(select(Company)).scalars().all()}
    assert avant == apres, "l'outil de MESURE a modifié la base"
