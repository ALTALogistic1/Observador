"""La trace d'un appariement — fonctions pures, sans base."""
from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, mapped_column

from outils.trace_un_appariement import DETAIL_MAX, apercu, sql_emis


def test_apercu_distingue_le_vide_de_lespace_et_du_none():
    """`str` les rendrait indistinguables, et ils n'ont pas la même cause."""
    assert apercu("") == "''"
    assert apercu(" ") == "' '"
    assert apercu(None) == "None"


def test_apercu_tronque_sans_mentir_sur_la_troncature():
    long = "a" * 200
    rendu = apercu(long, largeur=20)
    assert len(rendu) == 20
    assert rendu.endswith("…")


def test_apercu_ne_tronque_pas_ce_qui_tient():
    assert apercu("court") == "'court'"


def test_le_sql_emis_porte_les_valeurs_LITTERALES():
    """Un SQL à paramètres liés ne dit pas ce que SQLite reçoit — et c'est
    exactement ce qu'on cherche à voir."""
    from falkye.models.req_entry import REQEntry

    requete = select(REQEntry.neq).where(REQEntry.nom_normalise.op("GLOB")("9309*"))
    rendu = sql_emis(requete)
    assert "'9309*'" in rendu
    assert ":nom_normalise" not in rendu


def test_le_sql_emis_ne_leve_pas_sur_un_type_non_litteralisable():
    """Un instrument qui tombe en décrivant sa propre requête ne mesure rien."""

    class Faux:
        def compile(self, **_kw):
            raise TypeError("pas de littéral pour ce type")

        def __str__(self):
            return "SELECT …"

    rendu = sql_emis(Faux())
    assert "non littéralisable" in rendu
    assert "TypeError" in rendu


def test_la_borne_de_detail_existe_et_est_franche():
    """Au-delà, seul le compte est rendu — et la troncature est DITE."""
    assert isinstance(DETAIL_MAX, int) and DETAIL_MAX > 0


def test_sans_nom_ni_selecteur_loutil_refuse(capsys):
    """`--nom` n'est plus obligatoire, donc quelque chose doit l'exiger. *Une
    option rendue facultative sans garde laisse passer un appel vide qui
    plantait avant.*"""
    import pytest as _pytest

    from outils import trace_un_appariement

    with _pytest.raises(SystemExit):
        trace_un_appariement.main([])


def test_la_borne_du_moteur_nest_pas_celle_du_dedoublonnage():
    """⚠️ **Deux bornes, deux tables, deux chemins.**

    `BORNE_MOTEUR = 2000` borne la récupération contre le MIROIR;
    `LIMITE_CANDIDATS = 500` borne le dédoublonnage entre `Company`. *Les
    confondre fait chercher le mur du mauvais côté* — et c'est une confusion
    facile, puisque les deux sont des « LIMIT sans ORDER BY » de la même
    journée.
    """
    from falkye.dedup_entreprises import LIMITE_CANDIDATS
    from falkye.sources.req import candidats_par_nom
    from outils.trace_un_appariement import BORNE_MOTEUR
    import inspect

    assert BORNE_MOTEUR != LIMITE_CANDIDATS, "les deux bornes ont convergé — ce test a vieilli"
    defaut = inspect.signature(candidats_par_nom).parameters["limite"].default
    assert BORNE_MOTEUR == defaut, (
        f"le diagnostic annonce {BORNE_MOTEUR} et le moteur borne à {defaut} : "
        "la trace mentirait sur la borne qu'elle diagnostique"
    )


def test_le_classement_des_familles_vient_du_MOTEUR():
    """⚠️ **Le critère précédent présélectionnait le résultat.**

    Il retenait les dossiers dont le nom existait par correspondance EXACTE dans
    le miroir — *ceux dont il avait déjà démontré qu'ils devaient réussir*. Trois
    cas tracés, trois scores de 100, **et aucun dossier qui échoue regardé.**

    *Un critère de sélection qui présélectionne le résultat n'échantillonne pas
    une population : il illustre une conclusion.*

    Ici le classement passe par `neq_retenu`, la fonction du produit.
    """
    from dataclasses import dataclass

    from falkye.resolution import SEUIL_AMBIGUITE_ECART_MIN, SEUIL_RESOLUTION_CONFIANTE
    from outils.trace_un_appariement import _famille

    @dataclass
    class M:
        score: float

    haut = SEUIL_RESOLUTION_CONFIANTE + 1
    assert _famille([], None) == "aucun_candidat"
    assert _famille([M(haut)], "1111111111") == "resoluble"
    assert _famille([M(SEUIL_RESOLUTION_CONFIANTE - 1)], None) == "trop_faible"
    # Assez sûr, pas assez détaché : le moteur rend None, et c'est « ambigu ».
    assert _famille([M(haut), M(haut - SEUIL_AMBIGUITE_ECART_MIN + 1)], None) == "ambigu"


def test_une_famille_inconnue_est_refusee():
    """*Une faute de frappe dans `--familles` rendrait un échantillon vide qui se
    lirait comme « cette famille n'existe pas dans la population ».*"""
    import pytest as _pytest

    from outils import trace_un_appariement

    with _pytest.raises(SystemExit):
        trace_un_appariement.main(["--par-famille", "1", "--familles", "nimporte_quoi"])


def test_aucun_compte_perime_ne_traine_dans_le_fichier():
    """**Un périmètre qui annonce une population non définie ne borne rien.**

    Le bloc de portée citait `4 873` trois fois — un compte du 15 septembre qui
    n'est plus dans aucune ventilation. *Et cette fois le chiffre était dans le
    texte qui existe précisément pour dire ce que la mesure couvre.*
    """
    import re
    from pathlib import Path

    source = Path(__file__).resolve().parent.parent / "outils" / "trace_un_appariement.py"
    texte = source.read_text(encoding="utf-8")
    # ⚠️ **Resserrée après un premier jet trop large** — il attrapait les années
    # (`2026`) et les fragments de NEQ (`9309-3927`). *Une garde qui crie pour un
    # millésime finit par être ignorée* : c'est le cas 34 dans la garde
    # elle-même.
    #
    # Ce qu'on refuse est la FORME d'un compte humain : quatre chiffres ou plus
    # avec un séparateur de milliers — « 4 873 », « 8 931 ». *Une année ne
    # s'écrit jamais avec un séparateur, et un NEQ non plus.* Les bornes et les
    # seuils (`2000`, `500`, `92`) s'écrivent sans séparateur et vivent dans des
    # constantes nommées.
    suspects = re.findall(r"(?<![\d\-])\d[\u202f ]\d{3}(?![\d\-])", texte)
    restants = sorted(set(suspects))
    assert not restants, (
        f"comptes de population écrits en dur : {restants}. "
        "Un compte recopié se périme, et dans un bloc de portée il fait croire "
        "que la mesure borne une population qui n'existe plus."
    )
