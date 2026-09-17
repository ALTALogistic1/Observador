"""La ville peut-elle DÉPARTAGER deux candidats déjà trouvés — et combien de fois?

⚠️ **Ce que ces tests gardent.** *Apparier depuis rien avec une ville est
impossible; départager deux candidats déjà trouvés est autre chose.* La mesure
doit rendre les trois chiffres d'Alexandre — le plafond, le départageable, et
**qui gagne** — sans rien écrire et sans promouvoir aucun champ.
"""
from __future__ import annotations

import pytest

from falkye.models.company import Company
from falkye.models.req_entry import REQEntry
from falkye.models.signal import Signal
from falkye.sources.column_mapping import normaliser
from outils import departage_par_ville
from outils.departage_par_ville import _ville_depuis_adresse


def test_la_ville_se_lit_en_TETE_de_ladresse_eimt():
    """`'St-Isidore, QC J0L 2A'` → `'St-Isidore'`. *La forme observée est
    « municipalité, PROVINCE code postal ».*"""
    assert _ville_depuis_adresse("St-Isidore, QC J0L  2A") == "St-Isidore"
    assert _ville_depuis_adresse("Lévis, QC G6V 1A1") == "Lévis"


def test_une_adresse_SANS_virgule_ne_rend_RIEN():
    """⚠️ *Prendre la chaîne entière pour une ville inventerait des villes.*
    `'200 rue des Commandeurs'` n'est pas une municipalité."""
    assert _ville_depuis_adresse("200 rue des Commandeurs") is None
    assert _ville_depuis_adresse("") is None
    assert _ville_depuis_adresse(None) is None


def _cible_declaree(monkeypatch):
    monkeypatch.setenv("FALKYE_DB_URL", "sqlite:////tmp/essai-produit.sqlite3")
    monkeypatch.setenv("FALKYE_MIROIR_DB_URL", "sqlite:////tmp/essai-miroirs.sqlite3")


def _ambigu(db_session, nom_detecte, villes_registre, prefixe="Transport Boreal"):
    """Deux candidats à moins de 8 points l'un de l'autre — donc AMBIGU — dont
    les villes au registre sont celles demandées."""
    for i, ville in enumerate(villes_registre):
        nom = f"{prefixe} {'inc' if i == 0 else 'ltee'}"
        db_session.add(REQEntry(neq=f"400000000{i}", nom=nom,
                                nom_normalise=normaliser(nom), ville=ville,
                                statut="IMMATRICULÉE"))
    company = Company(neq=None, nom_detecte=nom_detecte,
                      nom_detecte_normalise=normaliser(nom_detecte))
    db_session.add(company)
    db_session.flush()
    return company


@pytest.fixture()
def deux_villes(db_session, monkeypatch):
    """Un ambigu dont les deux candidats sont dans DEUX villes différentes, et
    dont la ville n'existe que dans `Signal.champs` — **le gisement**."""
    _cible_declaree(monkeypatch)
    company = _ambigu(db_session, "Transport Boreal", ["Saint-Isidore", "Laval"])
    db_session.add(Signal(
        company_id=company.id, source_id="eimt", signal_type_id="recrutement_massif",
        detected_at=__import__("datetime").datetime(2026, 1, 1),
        champs={"adresse": "Saint-Isidore, QC J0L 2A"},
    ))
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def test_ce_que_la_mesure_ne_dira_pas_vient_AVANT_les_chiffres(deux_villes, capsys):
    assert departage_par_ville.main([]) == 0
    sortie = capsys.readouterr().out
    assert sortie.index("CE QUE CETTE MESURE NE DIRA PAS") < sortie.index("dossiers sans NEQ")
    assert "LOCAL RC27" in sortie, "la saleté de la ville au registre n'est pas dite"
    assert "NE PROUVE PAS L'IDENTITÉ" in sortie
    assert "AUCUNE ÉCRITURE, AUCUNE PROMOTION" in sortie


def test_le_bonus_de_ville_deja_applique_est_dit(deux_villes, capsys):
    """⚠️ *Le moteur utilise DÉJÀ `Company.ville` (+5).* Là où elle est promue,
    le signal est en partie consommé — et le gisement est ailleurs."""
    assert departage_par_ville.main([]) == 0
    sortie = capsys.readouterr().out
    assert "le signal est en partie consommé" in sortie
    assert "jamais promue" in sortie


def test_un_ambigu_a_deux_villes_est_DEPARTAGEABLE(deux_villes, capsys):
    assert departage_par_ville.main([]) == 0
    sortie = capsys.readouterr().out
    assert "dont AMBIGUS      : 1" in sortie, sortie
    assert "DÉPARTAGEABLES : 1 sur 1" in sortie, sortie
    # Et la ville vient du gisement, pas d'un champ promu.
    assert "`Signal.champs` SEULEMENT" in sortie


@pytest.fixture()
def meme_ville(db_session, monkeypatch):
    """Les deux candidats sont dans LA MÊME ville. *La ville ne départage pas —
    et c'est un résultat, pas une absence de mesure.*"""
    _cible_declaree(monkeypatch)
    company = _ambigu(db_session, "Transport Boreal", ["Laval", "Laval"])
    db_session.add(Signal(
        company_id=company.id, source_id="eimt", signal_type_id="recrutement_massif",
        detected_at=__import__("datetime").datetime(2026, 1, 1),
        champs={"adresse": "Laval, QC H7N 1A1"},
    ))
    db_session.commit()
    monkeypatch.setattr("falkye.db.get_session", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)
    return db_session


def test_deux_candidats_de_MEME_ville_ne_sont_pas_departageables(meme_ville, capsys):
    assert departage_par_ville.main([]) == 0
    sortie = capsys.readouterr().out
    assert "MÊME ville — la ville ne départage pas" in sortie
    assert "DÉPARTAGEABLES : 0 sur 1" in sortie, sortie


def test_le_gagnant_par_la_ville_est_compare_au_mieux_score(deux_villes, capsys):
    """⚠️ **La question qui décide si le correctif vaut la peine.** *Si la ville
    retient presque toujours celui qui avait déjà le meilleur score, elle
    confirme sans apporter.*"""
    assert departage_par_ville.main([]) == 0
    sortie = capsys.readouterr().out
    assert "était DÉJÀ le seul mieux scoré" in sortie
    assert "est UN AUTRE candidat" in sortie
    # ⚠️ Le décor donne DEUX candidats au même score : la question « était-ce
    # déjà le mieux scoré » n'a pas de réponse, et l'outil doit le dire au lieu
    # de trancher. *Les compter comme « confirmé » ferait paraître la ville
    # inutile là où elle est la seule à départager.*
    assert "EX ÆQUO au meilleur score" in sortie
    ligne = next(l for l in sortie.splitlines() if "EX ÆQUO" in l and "%" in l)
    assert ligne.split()[-3] == "1", ligne


def test_il_NECRIT_RIEN(deux_villes):
    from sqlalchemy import select

    avant = {c.id: (c.neq, c.ville, c.adresse)
             for c in deux_villes.execute(select(Company)).scalars().all()}
    assert departage_par_ville.main([]) == 0
    deux_villes.expire_all()
    apres = {c.id: (c.neq, c.ville, c.adresse)
             for c in deux_villes.execute(select(Company)).scalars().all()}
    assert avant == apres, "la mesure a promu un champ ou écrit dans la base"


def test_les_echelles_ne_bougent_pas(deux_villes):
    from falkye import resolution

    assert departage_par_ville.main([]) == 0
    assert resolution.SEUIL_RESOLUTION_CONFIANTE == 92.0
    assert resolution.SEUIL_AMBIGUITE_ECART_MIN == 8.0
