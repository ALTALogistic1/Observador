"""Connecteur Globe and Mail Report on Business — Top Growing Companies
(spec section 7, Signal 1).

Découverte réelle (2026-09-01) : la page-hub stable
(theglobeandmail.com/business/rob-magazine/top-growing-companies/) liste les
articles annuels du classement ; le lien de l'année courante ("...-of-{année}/",
pas la variante "-provincial") est découvert dynamiquement (même discipline que
Deloitte Fast 50 — jamais une URL annuelle codée en dur).

L'article annuel lui-même est une page JS (CMS Fusion/Arc XP) dont le corps
visible est vide en HTML brut (`articleWordCount: 0`), MAIS le CMS embarque
tout l'article dans un bloc `Fusion.globalContent={...};` inline, y compris :
  - `content_restrictions.content_code` — l'indicateur officiel de paywall du
    Globe and Mail ("green" = accès libre ; confirmé "green" pour ce
    classement le 2026-09-01, PAS payant malgré la réputation générale du
    site — à re-vérifier si jamais autre chose que "green" est rencontré,
    voir le log ci-dessous).
  - un `<script>` embarqué qui révèle le vrai mécanisme de données : un
    identifiant Google Sheet (`sheetID`) chargé depuis un fichier JSON public
    hébergé sur S3
    (`https://google-sheets-prod-....s3.ca-central-1.amazonaws.com/{sheetID}.json`)
    — aucune authentification, aucun anti-bot rencontré (à la différence de
    canadianbusiness.com/Growth 500, bloqué par Cloudflare — voir
    docs/STATUT_RESEAU.md). Ce JSON contient le classement complet en clair
    (400 entreprises pour 2025 : rang, nom, description, croissance sur 3
    ans, fourchette de revenu, employés, ville/province, industrie).

`sheetID` change chaque année (nouvelle feuille Google Sheets) — découvert
dynamiquement depuis l'article de l'année courante, jamais codé en dur (même
principe que le nom de fichier du PDF Deloitte).

Champ ville/région : la colonne "Headquarters" du classement est
irrégulière — les grandes villes sont données seules ("Montreal", "Toronto",
"Calgary"...), les autres avec un suffixe de province ("Longueuil, Que.",
"Barrie, Ont."...). `_parse_ville_region` sépare les deux quand le suffixe
est présent ; sinon la région reste `None` (résolue via le REQ comme
n'importe quel champ absent — spec section 7, "principe de complétude").
"""
from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterator
from datetime import datetime, timezone

import requests

from falkye.sources.base import RawSignal, SourceConnector
from falkye.sources.ckan_client import DEFAULT_USER_AGENT

logger = logging.getLogger(__name__)

PAGE_HUB = "https://www.theglobeandmail.com/business/rob-magazine/top-growing-companies/"

_RE_LIEN_ANNEE = re.compile(
    r'href="(/business/rob-magazine/top-growing-companies/'
    r'article-ranking-canadas-top-growing-companies-of-(\d{4})/)"'
)
_RE_SHEET_ID = re.compile(r'const sheetID\s*=\s*"([A-Za-z0-9_-]+)"')

_URL_SHEET_JSON_TEMPLATE = "https://google-sheets-prod-dc5q4g5x5w7l.s3.ca-central-1.amazonaws.com/{sheet_id}.json"


def trouver_url_article_courant(session: requests.Session) -> tuple[str, int]:
    """Découvre dynamiquement l'article du classement de l'année courante
    depuis la page-hub stable — jamais une URL annuelle codée en dur (même
    discipline que Deloitte Fast 50). Choisit l'année la plus élevée trouvée
    (la page-hub garde aussi les liens des années précédentes)."""
    resp = session.get(PAGE_HUB, timeout=15)
    resp.raise_for_status()
    candidats = _RE_LIEN_ANNEE.findall(resp.text)
    if not candidats:
        raise RuntimeError(
            f"Aucun lien de classement annuel trouvé sur {PAGE_HUB!r} — la structure "
            "de la page a peut-être changé (vérifier manuellement)."
        )
    chemin, annee = max(candidats, key=lambda c: int(c[1]))
    return f"https://www.theglobeandmail.com{chemin}", int(annee)


def _extraire_bloc_json(html: str, marqueur: str) -> dict | None:
    """Extrait un objet JSON inline (`marqueur{...};`) par appariement
    d'accolades — un simple regex non-gourmand échoue dès qu'une chaîne à
    l'intérieur contient elle-même des accolades (courant dans ce CMS, ex.
    des blobs CSS/JS imbriqués)."""
    debut = html.find(marqueur)
    if debut == -1:
        return None
    debut = html.find("{", debut)
    if debut == -1:
        return None
    profondeur = 0
    dans_chaine = False
    echappement = False
    i = debut
    while i < len(html):
        c = html[i]
        if dans_chaine:
            if echappement:
                echappement = False
            elif c == "\\":
                echappement = True
            elif c == '"':
                dans_chaine = False
        else:
            if c == '"':
                dans_chaine = True
            elif c == "{":
                profondeur += 1
            elif c == "}":
                profondeur -= 1
                if profondeur == 0:
                    i += 1
                    break
        i += 1
    try:
        return json.loads(html[debut:i])
    except json.JSONDecodeError:
        return None


def _parse_ville_region(hq: str | None) -> tuple[str | None, str | None]:
    """Sépare "Longueuil, Que." en ("Longueuil", "Que.") ; laisse la région à
    None pour les grandes villes données seules ("Montreal") — voir docstring
    du module."""
    if not hq:
        return None, None
    hq = hq.strip()
    if "," in hq:
        ville, region = hq.rsplit(",", 1)
        return ville.strip() or None, region.strip() or None
    return hq or None, None


def recuperer_classement(session: requests.Session) -> tuple[int, list[dict]]:
    """Récupère le classement complet de l'année courante — factorisé pour
    être appelé aussi bien par le connecteur que par des tests/diagnostics."""
    url_article, annee = trouver_url_article_courant(session)
    resp = session.get(url_article, timeout=20)
    resp.raise_for_status()

    contenu = _extraire_bloc_json(resp.text, "Fusion.globalContent=")
    if contenu is None:
        raise RuntimeError(f"Impossible d'extraire Fusion.globalContent depuis {url_article!r}.")

    restriction = (contenu.get("content_restrictions") or {}).get("content_code")
    if restriction and restriction != "green":
        logger.warning(
            "Globe and Mail Top Growing Companies: content_code=%r (pas 'green') sur %r "
            "— possiblement payant cette année, à vérifier manuellement.",
            restriction,
            url_article,
        )

    sheet_id = None
    for element in contenu.get("content_elements") or []:
        m = _RE_SHEET_ID.search(element.get("content") or "")
        if m:
            sheet_id = m.group(1)
            break
    if sheet_id is None:
        raise RuntimeError(f"Aucun sheetID trouvé dans l'article {url_article!r}.")

    resp = session.get(_URL_SHEET_JSON_TEMPLATE.format(sheet_id=sheet_id), timeout=20)
    resp.raise_for_status()
    data = resp.json()
    feuille = data["data"][0]
    header = feuille["header"]
    lignes = [dict(zip(header, ligne, strict=False)) for ligne in feuille["rows"]]
    return annee, lignes


def _parse_float(raw) -> float | None:
    if raw in (None, ""):
        return None
    try:
        return float(str(raw).replace(",", "").replace("%", "").strip())
    except ValueError:
        return None


def _parse_int(raw) -> int | None:
    if raw in (None, ""):
        return None
    try:
        return int(float(str(raw).replace(",", "").strip()))
    except ValueError:
        return None


class RobTopGrowingConnector(SourceConnector):
    def detect(self, since: datetime | None, db_session) -> Iterator[RawSignal]:
        session = requests.Session()
        session.headers.setdefault("User-Agent", DEFAULT_USER_AGENT)

        try:
            annee, lignes = recuperer_classement(session)
        except (requests.RequestException, RuntimeError) as exc:
            logger.warning("Globe and Mail Top Growing Companies: échec de la récupération: %s", exc)
            return

        now = datetime.now(timezone.utc)
        for ligne in lignes:
            nom = (ligne.get("Company") or "").strip()
            rang = _parse_int(ligne.get("Rank"))
            if not nom or rang is None:
                continue

            croissance = _parse_float(ligne.get("3-year revenue growth (%)"))
            ville, region = _parse_ville_region(ligne.get("Headquarters"))
            secteur = (ligne.get("Industry") or "").strip() or None

            yield RawSignal(
                signal_type_id="classement_croissance",
                nom_entreprise=nom,
                detected_at=now,
                source_ref=f"rob_top_growing:{annee}:{rang}",
                ville=ville,
                region=region,
                secteur_activite=secteur,
                titre_ou_description=(
                    f"Top Growing Companies {annee} — rang {rang}"
                    + (f" ({croissance:.0f}% croissance sur 3 ans)" if croissance is not None else "")
                ),
                champs={
                    "rang": rang,
                    "taux_croissance": croissance,
                    "annee_publication": annee,
                    "description": ligne.get("Description"),
                    "revenu": ligne.get("Revenue"),
                    "employes": _parse_int(ligne.get("Employees")),
                },
            )


CONNECTOR_CLASS = RobTopGrowingConnector
