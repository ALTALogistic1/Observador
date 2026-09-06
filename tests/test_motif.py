"""Ce que ces tests protègent : **une ligne qui se répète à l'identique ne dit
rien**.

Le premier envoi réel (2026-09-06) portait 306 lignes toutes marquées « Signal
détecté », alors que chaque signal portait un montant distinct — de 112 500 $ à
5 000 000 $ — déjà en base et jamais regardé. Le mandat demande « le motif du
repérage tiré de la structure de faits »; le code ne lisait qu'un seul champ.

Les deux abstentions comptent autant que le motif lui-même : ne pas rendre les
champs libres (ils nomment la source, ce que la neutralité des libellés
interdit) et ne pas dater (la seule date disponible est celle de l'ingestion,
pas celle de l'événement).
"""
from datetime import datetime, timezone

from falkye.models.signal import Signal
from falkye.motif import (
    ESPACE_INSECABLE,
    montant_lisible,
    motif_avec_mots_cles,
    motif_du_reperage,
)


def _montant(texte):
    """Le rendu attendu d'un MONTANT, avec les espaces insécables que la
    typographie demande — écrits par la constante plutôt qu'à la main, où ils
    seraient indiscernables d'un espace ordinaire à la relecture.

    Ne s'applique qu'au montant lui-même : sur une phrase entière, remplacer
    tous les espaces souderait les mots.
    """
    return texte.replace(" ", ESPACE_INSECABLE)


def _motif_montant(texte):
    return f"Montant associé : {_montant(texte)}"


def _signal(**kw):
    defauts = dict(
        company_id=1,
        source_id="investissement_quebec",
        signal_type_id="financement_expansion",
        detected_at=datetime.now(timezone.utc),
    )
    return Signal(**{**defauts, **kw})


# --- L'ordre des trois règles ----------------------------------------------


def test_les_mots_de_la_source_priment_sur_les_faits_types():
    """Quand la source décrit l'événement, personne ne dit mieux qu'elle."""
    signal = _signal(
        titre_ou_description="Contrat de déneigement des voies publiques",
        valeur_associee=45990.0,
    )
    assert motif_du_reperage(signal) == "Contrat de déneigement des voies publiques"


def test_sans_libelle_le_montant_tient_lieu_de_motif():
    """Le défaut exact du premier envoi : ce montant était en base et le motif
    disait « Signal détecté »."""
    assert motif_du_reperage(_signal(valeur_associee=350000.0)) == _motif_montant("350 000 $")


def test_sans_libelle_ni_montant_le_motif_est_vide():
    """Pas de phrase de remplissage. Un bloc qui n'affiche que sa catégorie dit
    exactement ce qu'on sait; « Signal détecté » prétendait dire davantage."""
    assert motif_du_reperage(_signal()) == ""


def test_un_libelle_vide_ne_compte_pas_comme_un_libelle():
    """La source peut renvoyer une chaîne vide ou blanche plutôt que rien —
    s'arrêter là laisserait le montant inutilisé."""
    assert motif_du_reperage(_signal(titre_ou_description="   ", valeur_associee=1000.0)) == (
        _motif_montant("1 000 $")
    )


# --- Les deux abstentions, aussi importantes que le motif -------------------


def test_les_champs_libres_ne_sont_jamais_rendus():
    """`programme` vaut ici « Investissement Québec » : le nom de la SOURCE, que
    la neutralité des libellés (charte section 6) interdit d'afficher. Rendre
    `champs` en vrac le ferait fuir dans le courriel sans décision."""
    signal = _signal(
        champs={"programme": "Investissement Québec", "montant": 350000.0},
        valeur_associee=350000.0,
    )
    motif = motif_du_reperage(signal)

    assert "Investissement Québec" not in motif
    assert "programme" not in motif


def test_aucune_date_nest_affichee():
    """`detected_at` vaut l'heure d'INGESTION pour les sources qui ne datent pas
    leurs événements. En faire « financé le 6 septembre » énoncerait un fait
    faux."""
    signal = _signal(
        detected_at=datetime(2026, 9, 6, 20, 23, tzinfo=timezone.utc), valeur_associee=350000.0
    )
    motif = motif_du_reperage(signal)

    assert "2026" not in motif
    assert "septembre" not in motif


# --- Les mots-clés se rattachent au motif, ils ne le remplacent pas ---------


def test_les_mots_cles_suivent_le_motif():
    signal = _signal(titre_ou_description="Contrat de transport scolaire")
    assert motif_avec_mots_cles(signal, ["transport", "logistique"]) == (
        "Contrat de transport scolaire — correspond aux mots-clés : transport, logistique"
    )


def test_sans_motif_les_mots_cles_touvrent_pas_par_un_tiret_orphelin():
    """La version d'avant produisait « — correspond aux mots-clés : … » quand la
    source ne libellait rien."""
    resultat = motif_avec_mots_cles(_signal(), ["transport"])

    assert not resultat.startswith("—")
    assert resultat == "Correspond aux mots-clés : transport"


def test_sans_mots_cles_le_motif_tient_seul():
    signal = _signal(valeur_associee=500000.0)
    assert motif_avec_mots_cles(signal, []) == _motif_montant("500 000 $")


# --- Le rendu d'un montant --------------------------------------------------


def test_un_montant_entier_na_pas_de_cents():
    """« 350 000,00 $ » donnerait au chiffre une précision qu'il n'a pas."""
    assert montant_lisible(350000.0) == _montant("350 000 $")


def test_un_montant_a_cents_les_garde():
    assert montant_lisible(1234.56) == _montant("1 234,56 $")


def test_les_milliers_se_separent_pour_de_gros_montants():
    assert montant_lisible(5000000.0) == _montant("5 000 000 $")


def test_labsence_de_montant_nest_pas_zero():
    """Rendre None comme « 0 $ » affirmerait un montant nul — un fait faux."""
    assert montant_lisible(None) is None
    assert montant_lisible(0.0) == _montant("0 $")
