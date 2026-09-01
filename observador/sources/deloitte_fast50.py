"""Connecteur Deloitte Technology Fast 50 (Canada) — spec section 7, Signal 1.

Découverte réelle (2026-09-01) : la page d'atterrissage
(https://www.deloitte.com/ca/en/Industries/technology/research/fast50-winners.html)
est stable d'une année à l'autre, mais elle ne contient PAS le classement complet
en HTML — seulement un résumé du #1 par catégorie. Le classement complet est
dans un PDF téléchargeable dont le NOM DE FICHIER change chaque année (ex.
"ca-fast-50-winners-2025-en-aoda.pdf") : le lien est donc découvert
dynamiquement à chaque appel plutôt que codé en dur, même principe que les
autres sources de ce projet (ne jamais assumer qu'une URL annuelle reste stable
— voir REQ, SEAO pour la même discipline).

Structure réelle du PDF (confirmée par inspection du fichier 2025, 6 pages) :
trois classements distincts, chacun sur sa propre page, identifiée par une
ligne titre au format "AAAA <Catégorie> ranking" (ex. "2025 Technology Fast
50 ranking") — PAS le nombre de gagnants toujours égal à 50 : en 2025,
Technology Fast 50 en a 50, Enterprise—Industry Leaders en a 17,
Companies-to-Watch en a 15 (le nombre de gagnants varie d'année en année dans
ces deux catégories secondaires). La catégorie principale est présentée sur
DEUX colonnes (ex. rangs 1-25 puis 26-50 sur la même ligne visuelle) ; le texte
extrait conserve les deux entrées sur une seule ligne — le motif d'extraction
gère ça en cherchant toutes les occurrences du motif par ligne, pas une seule.

Aucun champ "secteur d'activité" dans ce PDF (seulement nom, ville, province,
taux de croissance, rang) — résolu via le REQ comme les autres sources qui ne
le fournissent pas directement (spec section 7, "principe de complétude").
"""
from __future__ import annotations

import io
import logging
import re
from collections.abc import Iterator
from datetime import datetime, timezone
from urllib.parse import urljoin

import pdfplumber
import requests

from observador.sources.base import RawSignal, SourceConnector
from observador.sources.ckan_client import DEFAULT_USER_AGENT

logger = logging.getLogger(__name__)

PAGE_ATTERRISSAGE = "https://www.deloitte.com/ca/en/Industries/technology/research/fast50-winners.html"

_RE_PDF_HREF = re.compile(r'href="([^"]*fast[-_]?50[^"]*\.pdf)"', re.IGNORECASE)
_RE_TITRE_PAGE = re.compile(r"^(20\d{2}) (.+?) ranking[ \t]*$", re.MULTILINE)
_RE_ENTREE = re.compile(
    r"(?P<rang>\d+)\s+(?P<nom>.+?)\s+[–—-]\s+(?P<ville>.+?)\s+(?P<province>[A-Z]{2})\s+(?P<croissance>[\d,]+)%"
)


def trouver_url_pdf(session: requests.Session) -> str:
    """Découvre dynamiquement le lien vers le PDF du classement en cours,
    plutôt que de coder en dur un nom de fichier annuel (voir docstring du
    module)."""
    resp = session.get(PAGE_ATTERRISSAGE, timeout=15)
    resp.raise_for_status()
    m = _RE_PDF_HREF.search(resp.text)
    if not m:
        raise RuntimeError(
            f"Aucun lien PDF trouvé sur {PAGE_ATTERRISSAGE!r} — la structure de la page a "
            "peut-être changé (vérifier manuellement)."
        )
    return urljoin(PAGE_ATTERRISSAGE, m.group(1))


def _categorie_et_annee(texte_page: str) -> tuple[str, int] | None:
    m = _RE_TITRE_PAGE.search(texte_page)
    if not m:
        return None
    return m.group(2).strip(), int(m.group(1))


def _iter_entrees(texte_page: str) -> Iterator[dict]:
    for ligne in texte_page.split("\n"):
        for m in _RE_ENTREE.finditer(ligne):
            d = m.groupdict()
            yield {
                "rang": int(d["rang"]),
                "nom": d["nom"].strip(),
                "ville": d["ville"].strip(),
                "province": d["province"],
                "taux_croissance": float(d["croissance"].replace(",", "")),
            }


def iter_classement(session: requests.Session) -> Iterator[tuple[str, int, dict]]:
    """Générateur (catégorie, année, entrée) pour tout le PDF — factorisé pour
    être appelé aussi bien par le connecteur que par des tests/diagnostics."""
    pdf_url = trouver_url_pdf(session)
    resp = session.get(pdf_url, timeout=30)
    resp.raise_for_status()

    with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
        for page in pdf.pages:
            texte = page.extract_text() or ""
            categorie_annee = _categorie_et_annee(texte)
            if categorie_annee is None:
                continue  # page de garde, description des catégories, ou disclaimer légal
            categorie, annee = categorie_annee
            for entree in _iter_entrees(texte):
                yield categorie, annee, entree


class DeloitteFast50Connector(SourceConnector):
    def detect(self, since, db_session) -> Iterator[RawSignal]:
        session = requests.Session()
        session.headers.setdefault("User-Agent", DEFAULT_USER_AGENT)

        try:
            entrees = list(iter_classement(session))
        except (requests.RequestException, RuntimeError) as exc:
            logger.warning("Deloitte Fast 50: échec de la récupération du classement: %s", exc)
            return

        now = datetime.now(timezone.utc)
        for categorie, annee, entree in entrees:
            yield RawSignal(
                signal_type_id="classement_croissance",
                nom_entreprise=entree["nom"],
                detected_at=now,
                source_ref=f"deloitte_fast50:{annee}:{categorie}:{entree['rang']}",
                ville=entree["ville"],
                region=entree["province"],
                titre_ou_description=f"{categorie} {annee} — rang {entree['rang']} ({entree['taux_croissance']:.0f}% croissance)",
                champs={
                    "rang": entree["rang"],
                    "taux_croissance": entree["taux_croissance"],
                    "categorie": categorie,
                    "annee_publication": annee,
                },
            )


CONNECTOR_CLASS = DeloitteFast50Connector
