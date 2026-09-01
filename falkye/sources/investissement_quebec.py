"""Connecteur Investissement Québec — divulgation publique (spec section 7,
Signal 2).

ACCÈS RÉEL CONFIRMÉ (URL) le 2026-08-31, mais PAS le format interne : la liste
de divulgation est publiée en PDF, pas en CSV/API structuré, directement sur
`www.investquebec.com` — DOMAINE NON ENCORE AUTORISÉ dans l'environnement au
moment de l'écriture (voir docs/STATUT_RESEAU.md), donc ce connecteur n'a pas
pu être exécuté contre le vrai fichier. URL réelle trouvée par recherche :

    https://www.investquebec.com/sites/default/files/2026-02/investissement-quebec-interventions-financieres-2025.pdf

("Liste de divulgation 2024-2025 — Nom de l'entreprise, Montant de
financement"). Mise à jour annuelle, à un chemin qui change chaque année (le
mois/l'année dans le chemin varient) — `URL_PAR_DEFAUT` ci-dessous devra donc
être ajustée à la main une fois par an, ou passée explicitement au connecteur ;
aucune découverte dynamique possible (pas de portail CKAN pour cette source).

Le parsing extrait les tableaux du PDF (via pdfplumber) et cherche la ligne
d'en-tête par correspondance de colonnes (nom d'entreprise, montant) plutôt que
de supposer une mise en page fixe — mais reste NON VALIDÉ contre le vrai
fichier. `resolve_columns` échoue explicitement si la structure ne correspond
pas, plutôt que de mal interpréter les données.
"""
from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from datetime import datetime, timezone

import pdfplumber
import requests

from falkye.sources.base import RawSignal, SourceConnector
from falkye.sources.ckan_client import DEFAULT_USER_AGENT
from falkye.sources.column_mapping import normaliser, resolve_columns

logger = logging.getLogger(__name__)

URL_PAR_DEFAUT = (
    "https://www.investquebec.com/sites/default/files/2026-02/"
    "investissement-quebec-interventions-financieres-2025.pdf"
)

COLUMN_ALIASES: dict[str, list[str]] = {
    "entreprise": ["nom_de_l_entreprise", "entreprise", "beneficiaire"],
    "montant": ["montant_de_financement", "montant"],
}


def _telecharger(url: str, dest_path) -> None:
    session = requests.Session()
    session.headers.setdefault("User-Agent", DEFAULT_USER_AGENT)
    resp = session.get(url, timeout=60)
    resp.raise_for_status()
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(resp.content)


def _parse_montant(raw) -> float | None:
    if raw is None:
        return None
    texte = str(raw).replace("\xa0", "").replace(" ", "").replace(",", ".").replace("$", "")
    texte = "".join(c for c in texte if c.isdigit() or c == ".")
    if not texte:
        return None
    try:
        return float(texte)
    except ValueError:
        return None


class InvestissementQuebecConnector(SourceConnector):
    def __init__(self, source_def, url: str | None = None, limit: int | None = None):
        super().__init__(source_def)
        self.url = url or os.environ.get("FALKYE_IQ_PDF_URL") or URL_PAR_DEFAUT
        self.limit = limit

    def detect(self, since, db_session) -> Iterator[RawSignal]:
        from pathlib import Path

        from falkye.sources.ckan_client import CACHE_DIR

        import hashlib

        digest = hashlib.sha256(self.url.encode()).hexdigest()[:16]
        dest = Path(CACHE_DIR) / f"{digest}.pdf"
        if not dest.exists():
            try:
                _telecharger(self.url, dest)
            except requests.RequestException as exc:
                logger.warning("Investissement Québec: échec du téléchargement (%s): %s", self.url, exc)
                return

        n = 0
        columns: dict[str, str] | None = None
        now = datetime.now(timezone.utc)

        with pdfplumber.open(dest) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables() or []:
                    if not table or not table[0]:
                        continue
                    header = [str(c or "").strip() for c in table[0]]
                    if columns is None:
                        try:
                            columns = resolve_columns(header, COLUMN_ALIASES)
                        except ValueError:
                            continue  # ce tableau n'est pas le bon (ex. légende/notes)

                    for row in table[1:]:
                        if self.limit is not None and n >= self.limit:
                            return
                        row_dict = dict(zip(header, row, strict=False))
                        entreprise = str(row_dict.get(columns["entreprise"]) or "").strip()
                        montant = _parse_montant(row_dict.get(columns["montant"]))
                        if not entreprise or montant is None:
                            continue
                        n += 1

                        yield RawSignal(
                            signal_type_id="financement_expansion",
                            nom_entreprise=entreprise,
                            detected_at=now,  # le PDF ne donne pas de date par ligne, seulement l'année de la liste
                            source_ref=f"investissement_quebec:{self.url}:{entreprise}:{montant}",
                            valeur_associee=montant,
                            champs={"programme": "Investissement Québec", "montant": montant},
                        )


CONNECTOR_CLASS = InvestissementQuebecConnector
