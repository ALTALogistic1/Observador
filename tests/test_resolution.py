"""Tests de la résolution NEQ (falkye/resolution.py) contre un miroir REQ local
minimal inséré directement en base de test — pas d'appel réseau, pas de données
fabriquées présentées comme des détections réelles : juste des entrées REQ
plausibles utilisées pour vérifier l'algorithme de correspondance."""
from datetime import datetime, timezone

from falkye.models.req_entry import REQEntry
from falkye.resolution import resolve_company
from falkye.sources.base import RawSignal


def _raw(nom, source_ref="ref-1", ville=None):
    return RawSignal(
        signal_type_id="appel_offres",
        nom_entreprise=nom,
        detected_at=datetime.now(timezone.utc),
        source_ref=source_ref,
        ville=ville,
    )


def test_resolution_directe_par_neq(db_session):
    raw = RawSignal(
        signal_type_id="registre_corporatif",
        nom_entreprise="Entreprise Alpha inc.",
        detected_at=datetime.now(timezone.utc),
        source_ref="req:1",
        neq="1234567890",
    )
    company = resolve_company(db_session, raw)
    assert company.neq == "1234567890"
    assert company.statut_resolution.value == "resolu"


def test_resolution_par_nom_avec_correspondance_unique(db_session):
    db_session.add(
        REQEntry(
            neq="1111111111",
            nom="Transport Beaulieu inc.",
            nom_normalise="transport beaulieu inc",
            statut="immatriculee",
        )
    )
    db_session.flush()

    company = resolve_company(db_session, _raw("Transport Beaulieu inc."))
    assert company.neq == "1111111111"
    assert company.statut_resolution.value == "resolu"


def test_resolution_ambigue_si_deux_noms_trop_proches(db_session):
    db_session.add_all(
        [
            REQEntry(neq="2222222222", nom="9345-1122 Québec inc.", nom_normalise="9345 1122 quebec inc", statut="immatriculee"),
            REQEntry(neq="3333333333", nom="9345-1123 Québec inc.", nom_normalise="9345 1123 quebec inc", statut="immatriculee"),
        ]
    )
    db_session.flush()

    company = resolve_company(db_session, _raw("9345-1122 Québec inc."))
    # Selon le seuil d'écart, ce cas limite reste soit résolu au bon NEQ, soit marqué
    # ambigu — jamais silencieusement résolu au MAUVAIS NEQ.
    if company.statut_resolution.value == "resolu":
        assert company.neq == "2222222222"
    else:
        assert company.statut_resolution.value == "ambigu"


def test_resolution_non_trouvee_sans_candidat(db_session):
    company = resolve_company(db_session, _raw("Entreprise Totalement Inconnue Du Registre XYZ"))
    assert company.neq is None
    assert company.statut_resolution.value == "non_trouve"


def test_meme_entreprise_non_resolue_deux_fois_reste_un_seul_dossier(db_session):
    c1 = resolve_company(db_session, _raw("Entreprise Fantome inc.", source_ref="a"))
    c2 = resolve_company(db_session, _raw("Entreprise Fantome inc.", source_ref="b"))
    assert c1.id == c2.id  # dossier cumulatif : pas de doublon pour le même nom non résolu


# --- Rapprochement flou entre entreprises SANS NEQ (spec section 8bis, point
# 4, 2026-09-03) — voir falkye/dedup_entreprises.py pour les deux seuils. ---


def test_rapprochement_floue_score_eleve_ancre_sur_le_meme_dossier(db_session):
    """"transport beaulieu inc" vs "transport beaulieux inc" (score ~97.8,
    au-dessus de SEUIL_FUSION_AUTO=95) — jamais une nouvelle fiche créée,
    ancrage direct sur le dossier existant, silencieux (aucun candidat créé
    à ancrer, rien à journaliser)."""
    c1 = resolve_company(db_session, _raw("Transport Beaulieu inc.", source_ref="a"))
    c2 = resolve_company(db_session, _raw("Transport Beaulieux inc.", source_ref="b"))
    assert c1.id == c2.id


def test_rapprochement_floue_score_intermediaire_cree_un_candidat_journalise(db_session):
    """"les services exp inc" vs "...compte principal" (score 90, dans la
    fourchette [90, 95[) — JAMAIS fusionné seul : une nouvelle fiche est
    quand même créée, mais un candidat est journalisé pour examen manuel."""
    from falkye.models.diagnostic_journal import DiagnosticJournal, TypeDiagnostic

    c1 = resolve_company(db_session, _raw("Les Services EXP inc.", source_ref="a"))
    c2 = resolve_company(db_session, _raw("Les Services EXP inc. — compte principal", source_ref="b"))
    assert c1.id != c2.id  # deux fiches distinctes, jamais fusionnées automatiquement

    candidats = (
        db_session.query(DiagnosticJournal)
        .filter(DiagnosticJournal.type_diagnostic == TypeDiagnostic.CANDIDAT_FUSION_ENTREPRISE)
        .all()
    )
    assert len(candidats) == 1
    assert candidats[0].statut == "a_examiner"
    assert candidats[0].company_id_principal == c1.id
    assert candidats[0].company_id_candidat == c2.id
    assert 90.0 <= candidats[0].score_similarite < 95.0


def test_rapprochement_floue_score_faible_ne_journalise_rien(db_session):
    """"entreprise alpha inc" vs "entreprise beta inc" (score ~82, sous
    SEUIL_FUSION_CANDIDAT=90) — deux fiches distinctes, aucun candidat
    journalisé (bruit, pas un doublon plausible)."""
    from falkye.models.diagnostic_journal import DiagnosticJournal

    c1 = resolve_company(db_session, _raw("Entreprise Alpha inc.", source_ref="a"))
    c2 = resolve_company(db_session, _raw("Entreprise Beta inc.", source_ref="b"))
    assert c1.id != c2.id
    assert db_session.query(DiagnosticJournal).count() == 0


def test_rapprochement_floue_jamais_contre_une_entreprise_resolue_au_neq(db_session):
    """Un Company déjà résolu (neq NOT NULL, ici via un NEQ directement fourni
    par le signal — découplé de la correspondance floue REQ, qui aurait sinon
    elle-même résolu le 2e nom via son propre mécanisme et masqué le test) —
    jamais un candidat de fusion, même à très forte ressemblance : un faux
    positif fusionnerait un dossier à forte valeur avec un dossier incertain.
    Aucun REQEntry en base ici, donc `resolve_neq_by_name` ne peut résoudre
    ni l'un ni l'autre nom par lui-même — seul le rapprochement floue DE CE
    MODULE est sous test."""
    c1 = resolve_company(
        db_session,
        RawSignal(
            signal_type_id="appel_offres", nom_entreprise="Transport Beaulieu inc.",
            detected_at=datetime.now(timezone.utc), source_ref="a", neq="5555555555",
        ),
    )
    assert c1.neq == "5555555555"

    c2 = resolve_company(db_session, _raw("Transport Beaulieux inc.", source_ref="b"))
    assert c2.id != c1.id  # jamais ancré sur c1 malgré la ressemblance — c1 a un NEQ


def test_statut_radie_propage_depuis_req(db_session):
    db_session.add(
        REQEntry(
            neq="4444444444",
            nom="Entreprise Fermee inc.",
            nom_normalise="entreprise fermee inc",
            statut="radiee",
        )
    )
    db_session.flush()

    company = resolve_company(db_session, _raw("Entreprise Fermee inc."))
    assert company.statut_legal.value == "radiee"


# ---------------------------------------------------------------------------
# LES DEUX ÉCHELLES, SIMULABLES SANS ÊTRE DÉPLAÇABLES  (2026-09-17)
# ---------------------------------------------------------------------------
#
# `neq_retenu` et `resolve_neq_by_name` acceptent désormais des paramètres de
# SIMULATION. **Le risque que ces tests gardent** : qu'un de ces paramètres
# change la règle en production au lieu de servir une mesure.


class _FauxEntree:
    def __init__(self, neq):
        self.neq = neq


class _FauxMatch:
    def __init__(self, neq, score):
        self.entry = _FauxEntree(neq)
        self.score = score


def test_neq_retenu_sans_parametres_est_la_regle_du_produit():
    """*Les défauts sont les constantes du module, et rien d'autre.*"""
    from falkye import resolution

    limite = [_FauxMatch("A", resolution.SEUIL_RESOLUTION_CONFIANTE), _FauxMatch("B", 0.0)]
    juste_dessous = [
        _FauxMatch("A", resolution.SEUIL_RESOLUTION_CONFIANTE - 0.01),
        _FauxMatch("B", 0.0),
    ]
    assert resolution.neq_retenu(limite) == "A"
    assert resolution.neq_retenu(juste_dessous) is None
    # Et le second trop proche reste un refus, aux défauts.
    serre = [_FauxMatch("A", 99.0), _FauxMatch("B", 99.0 - resolution.SEUIL_AMBIGUITE_ECART_MIN + 0.1)]
    assert resolution.neq_retenu(serre) is None


def test_les_parametres_de_simulation_ne_touchent_pas_les_constantes():
    """⚠️ **La garde qui compte.** *Un appelant peut simuler une autre échelle;
    il ne peut pas la poser.* Les deux échelles se changent avec Alexandre."""
    from falkye import resolution

    avant = (resolution.SEUIL_RESOLUTION_CONFIANTE, resolution.SEUIL_AMBIGUITE_ECART_MIN)
    matches = [_FauxMatch("A", 80.0), _FauxMatch("B", 79.0)]
    assert resolution.neq_retenu(matches, seuil=70.0, ecart_min=0.0) == "A"
    assert (resolution.SEUIL_RESOLUTION_CONFIANTE, resolution.SEUIL_AMBIGUITE_ECART_MIN) == avant
    assert avant == (92.0, 8.0)


def test_famille_de_separe_le_seuil_de_lecart():
    """⚠️ *Un dossier peut échouer parce que le score est bas OU parce que le
    second est trop proche* — et les deux n'appellent pas le même correctif."""
    from falkye.resolution import famille_de

    assert famille_de([]) == "aucun candidat"
    assert famille_de([_FauxMatch("A", 50.0)]) == "trop faible"
    assert famille_de([_FauxMatch("A", 99.0), _FauxMatch("B", 98.0)]) == "ambigu"
    assert famille_de([_FauxMatch("A", 99.0), _FauxMatch("B", 50.0)]) == "RETENU"
    # Le même dossier, deux échelles : le seuil ne le retient pas, l'écart si.
    bloque_par_lecart = [_FauxMatch("A", 91.0), _FauxMatch("B", 90.0)]
    assert famille_de(bloque_par_lecart) == "trop faible"
    assert famille_de(bloque_par_lecart, seuil=90.0) == "ambigu", (
        "le seuil abaissé le fait FRANCHIR sans le faire RETENIR — c'est la "
        "distinction que le chiffrage du 2026-09-17 avait manquée"
    )
    assert famille_de(bloque_par_lecart, seuil=90.0, ecart_min=0.5) == "RETENU"


def test_le_transformateur_de_formes_ne_touche_que_le_chemin_de_simulation(db_session):
    """`transformer_forme=None` — le chemin de production — doit rendre
    exactement ce qu'il rendait. *Et le transformateur doit voir le nom PUBLIÉ,
    pas la forme normalisée, sinon il n'y a plus de parenthèse à retirer.*"""
    from falkye.models.company import Company  # noqa: F401 -- enregistre le modèle
    from falkye.models.req_entry import REQEntry
    from falkye.sources import req as req_source
    from falkye.sources.column_mapping import normaliser

    publie = "Fabrications Meridien (Groupe Nordet) inc."
    db_session.add(REQEntry(neq="2222222222", nom=publie,
                            nom_normalise=normaliser(publie), statut="IMMATRICULÉE"))
    db_session.commit()

    vus: list[str] = []

    def retirer(nom: str) -> str:
        vus.append(nom)
        import re
        return re.sub(r"\s*\([^)]*\)", "", nom)

    sans = req_source.resolve_neq_by_name(db_session, "Fabrications Meridien inc.")
    avec = req_source.resolve_neq_by_name(
        db_session, "Fabrications Meridien inc.", transformer_forme=retirer
    )
    assert vus and any("(" in n for n in vus), (
        "le transformateur reçoit une forme NORMALISÉE — `normaliser` a déjà "
        "remplacé les parenthèses par des espaces, donc le retrait serait un "
        "no-op déguisé en mesure"
    )
    assert avec[0].score > sans[0].score, (
        "retirer le groupe entre parenthèses côté registre doit rapprocher les "
        "deux chaînes"
    )
