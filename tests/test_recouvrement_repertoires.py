"""Le recouvrement avec les répertoires publics — fonctions pures et parcours,
sans réseau ni base."""
from falkye.sources.column_mapping import normaliser
from outils.recouvrement_repertoires import (
    MOTIF_NEQ,
    REPERTOIRES,
    charger_repertoire,
    formes_du_nom,
    ventilation,
)


def test_une_cellule_multivaluee_rend_chaque_enseigne():
    """`AUTRES_NOMS` empile les enseignes avec `//`. Comptée d'un bloc, la cellule
    n'apparierait jamais rien — et l'échec serait silencieux."""
    formes = formes_du_nom("Olivier Kia Baie-Comeau//Olivier Occasion Baie-Comeau", normaliser)
    assert formes == ["olivier kia baie comeau", "olivier occasion baie comeau"]


def test_une_cellule_vide_ne_rend_aucune_forme():
    assert formes_du_nom("", normaliser) == []
    assert formes_du_nom("//", normaliser) == []
    assert formes_du_nom("...", normaliser) == []


def test_une_cellule_simple_rend_une_forme():
    assert formes_du_nom("Cliche Auto Ford inc.", normaliser) == ["cliche auto ford inc"]


def test_la_forme_dun_neq_est_dix_chiffres():
    assert MOTIF_NEQ.match("1166991746")
    assert not MOTIF_NEQ.match("116699174")      # neuf
    assert not MOTIF_NEQ.match("11669917460")    # onze
    assert not MOTIF_NEQ.match("1166991746 ")    # espace résiduel


class FauxClient:
    """Rend deux pages puis s'arrête — le parcours doit lire les deux."""

    def __init__(self, records, total=None):
        self.records = records
        self.total = len(records) if total is None else total
        self.appels = []

    def datastore_search(self, resource_id, limit=1000, offset=0, **kw):
        self.appels.append((resource_id, limit, offset))
        return {"total": self.total, "records": self.records[offset : offset + limit]}


def test_le_parcours_lit_toutes_les_pages():
    recs = [{"NEQ": f"11000000{i:02d}", "NOM_COMMERCANT": f"Entreprise {i}",
             "AUTRES_NOMS": ""} for i in range(2500)]
    client = FauxClient(recs)
    cat = charger_repertoire(client, "opc-permis", REPERTOIRES["opc-permis"], normaliser)
    assert cat["lignes"] == 2500
    assert cat["total_annonce"] == 2500
    assert len(client.appels) == 3  # 1000 + 1000 + 500


def test_le_parcours_indexe_chaque_champ_separement():
    """Le champ qui a apparié est le résultat — il ne doit pas se perdre."""
    recs = [{"NEQ": "1166991746", "NOM_COMMERCANT": "10355364 CANADA INC.",
             "AUTRES_NOMS": "Olivier Kia Baie-Comeau//Olivier Occasion"}]
    cat = charger_repertoire(FauxClient(recs), "opc-permis",
                             REPERTOIRES["opc-permis"], normaliser)
    index = cat["index"]
    assert index["10355364 canada inc"][0]["champ"] == "NOM_COMMERCANT"
    assert index["olivier kia baie comeau"][0]["champ"] == "AUTRES_NOMS"
    assert index["olivier occasion"][0]["champ"] == "AUTRES_NOMS"
    assert all(e[0]["neq"] == "1166991746" for e in index.values())


def test_un_parcours_tronque_se_voit_dans_le_compte():
    """CKAN annonce plus que ce qu'il rend : le compte lu doit rester le compte lu,
    jamais le total annoncé (l'absence de mesure n'est pas une mesure nulle)."""
    recs = [{"NEQ": "1100000000", "NOM_COMMERCANT": "A", "AUTRES_NOMS": ""}]
    cat = charger_repertoire(FauxClient(recs, total=9999), "opc-permis",
                             REPERTOIRES["opc-permis"], normaliser)
    assert cat["lignes"] == 1
    assert cat["total_annonce"] == 9999


def test_la_ventilation_separe_source_et_champ():
    app = [
        {"source": "opc-permis", "champ": "AUTRES_NOMS"},
        {"source": "opc-permis", "champ": "AUTRES_NOMS"},
        {"source": "opc-permis", "champ": "NOM_COMMERCANT"},
        {"source": "oqlf", "champ": "NOM_ENTREPRISE"},
    ]
    v = ventilation(app)
    assert v["opc-permis · AUTRES_NOMS"] == 2
    assert v["opc-permis · NOM_COMMERCANT"] == 1
    assert v["oqlf · NOM_ENTREPRISE"] == 1


def test_le_matricule_de_loqlf_est_declare_comme_tel():
    """La source ne le nomme jamais « NEQ ». La fiche du répertoire doit porter
    le nom RÉEL du champ, pas celui qu'on aimerait qu'il ait."""
    assert REPERTOIRES["oqlf"]["champ_neq"] == "MATRICULE"
    assert REPERTOIRES["opc-permis"]["champ_neq"] == "NEQ"
