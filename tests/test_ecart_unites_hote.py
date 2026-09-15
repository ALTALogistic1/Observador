"""L'écart entre les unités du dépôt et celles de l'hôte — fonctions pures."""
from outils.ecart_unites_hote import comparer, directives

UNITE = """\
# un commentaire qui ne change rien à ce que la machine fait
[Service]
Type=oneshot
WorkingDirectory=/opt/falkye/code
ExecStart=/opt/falkye/venv/bin/python -m outils.import_miroir_req \\
          --chemin /opt/falkye/import \\
          --importe-par chaine-de-deploiement
ReadWritePaths=/var/lib/falkye
"""


def test_les_continuations_sont_recollees():
    """Un ExecStart sur trois lignes échapperait à toute comparaison, et la
    garde se tairait sur la directive qui compte le plus."""
    d = directives(UNITE)
    assert d["ExecStart"] == [
        "/opt/falkye/venv/bin/python -m outils.import_miroir_req "
        "--chemin /opt/falkye/import --importe-par chaine-de-deploiement"
    ]


def test_les_commentaires_et_les_sections_sont_ecartes():
    d = directives(UNITE)
    assert "#" not in " ".join(d)
    assert "[Service]" not in d


def test_deux_unites_identiques_nont_aucun_ecart():
    assert comparer(directives(UNITE), directives(UNITE)) == []


def test_un_commentaire_different_ne_fait_PAS_rougir():
    """Une garde qui crie pour une reformulation finit par être ignorée."""
    autre = UNITE.replace("# un commentaire qui ne change rien", "# tout autre texte")
    assert comparer(directives(UNITE), directives(autre)) == []


def test_LE_CAS_DU_SOIR_est_attrape():
    """Le dépôt en `-m`, l'hôte par le chemin : c'est l'écart qui a coûté la
    soirée, et il doit sortir nommément."""
    hote = UNITE.replace("-m outils.import_miroir_req", "outils/import_miroir_req.py")
    ecarts = comparer(directives(UNITE), directives(hote))
    assert len(ecarts) == 1
    cle, au_depot, sur_hote = ecarts[0]
    assert cle == "ExecStart"
    assert "-m outils.import_miroir_req" in au_depot[0]
    assert "outils/import_miroir_req.py" in sur_hote[0]


def test_une_directive_absente_dun_cote_est_un_ecart():
    """Un WorkingDirectory retiré sur l'hôte casserait `-m` en silence."""
    hote = UNITE.replace("WorkingDirectory=/opt/falkye/code\n", "")
    ecarts = dict((c, (a, b)) for c, a, b in comparer(directives(UNITE), directives(hote)))
    assert ecarts["WorkingDirectory"] == (["/opt/falkye/code"], [])


def test_une_directive_hors_liste_ne_fait_pas_rougir():
    """`Description` ne change pas ce que la machine exécute."""
    a = UNITE + "Description=avant\n"
    b = UNITE + "Description=après\n"
    assert comparer(directives(a), directives(b)) == []
