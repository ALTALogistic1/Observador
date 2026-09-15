"""Le profilage mémoire de la phase 1 — fonctions pures."""
from outils.profil_memoire_import import _etape, rss_mo


def test_la_rss_est_lue_du_systeme_ou_declaree_illisible():
    """C'est la RSS qui décide de l'OOM, pas la somme des objets vivants.
    Et `None` doit rester `None`, jamais 0."""
    valeur = rss_mo()
    assert valeur is None or valeur > 0


def test_la_premiere_etape_na_pas_de_delta(capsys):
    _etape("au démarrage", None)
    sortie = capsys.readouterr().out
    assert "—" in sortie or "non lisible" in sortie


def test_une_etape_affiche_le_delta_signe(capsys):
    if rss_mo() is None:
        return  # machine sans /proc : l'autre test couvre ce cas
    _etape("après quelque chose", 0.0)
    sortie = capsys.readouterr().out
    assert "+" in sortie or "-" in sortie
    assert "Mo" in sortie


def test_une_machine_sans_proc_dit_quelle_ne_mesure_pas(capsys, monkeypatch):
    """Ce n'est pas « zéro mémoire » : c'est zéro mesure."""
    import outils.profil_memoire_import as mod

    monkeypatch.setattr(mod, "rss_mo", lambda: None)
    assert mod._etape("étape", 100.0) is None
    assert "non lisible" in capsys.readouterr().out
