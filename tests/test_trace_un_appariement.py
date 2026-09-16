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
