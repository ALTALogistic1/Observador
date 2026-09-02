"""Carte géographique interactive — spec section 4bis : "vue carte, pastilles de
pertinence positionnées par territoire, alternative à la vue liste du tableau de
bord — même donnée, présentation différente." Réservé aux plans Radar/Radar+
comme le reste du tableau de bord (falkye/cli.py::_verifier_plan_dashboard).

Produit un fichier HTML AUTONOME (Leaflet.js chargé depuis un CDN public) —
même philosophie que les notifications courriel : un livrable qui n'exige aucun
serveur web côté FALKYE, ouvert directement dans le navigateur de l'utilisateur.
Le géocodage (falkye/geocoding.py) est fait séparément, en amont — cette page ne
fait AUCUN appel réseau elle-même au-delà de charger Leaflet et les tuiles de
carte (le navigateur de l'UTILISATEUR final, pas cet environnement de
développement)."""
from __future__ import annotations

import html
import json
from dataclasses import dataclass

_COULEUR_PAR_NIVEAU = {
    "AAA": "#1a7f37",  # vert soutenu — le plus prioritaire
    "AA": "#d4a017",  # ambre
    "A": "#8a8f98",  # gris — repéré, mais l'attente la plus modeste
}
_COULEUR_DEFAUT = "#3388ff"


@dataclass
class PointCarte:
    notification_id: int
    nom_entreprise: str
    latitude: float
    longitude: float
    niveau_pertinence: str | None  # "A" / "AA" / "AAA" / None (historique)
    niveau_confiance: str
    ville: str | None = None


def generer_carte_html(points: list[PointCarte], titre: str = "FALKYE — Carte des prospects") -> str:
    """Logique PURE (aucun accès DB/réseau ici) — testable directement contre des
    points fabriqués. La géolocalisation et la requête DB restent dans
    falkye/cli.py::dashboard_carte."""
    if points:
        centre_lat = sum(p.latitude for p in points) / len(points)
        centre_lon = sum(p.longitude for p in points) / len(points)
    else:
        centre_lat, centre_lon = 56.0, -96.0  # centre approximatif du Canada — vue par défaut, carte vide

    marqueurs = [
        {
            "lat": p.latitude,
            "lon": p.longitude,
            "couleur": _COULEUR_PAR_NIVEAU.get(p.niveau_pertinence or "", _COULEUR_DEFAUT),
            "popup": (
                f"<strong>{html.escape(p.nom_entreprise)}</strong><br>"
                f"Pertinence : {html.escape(p.niveau_pertinence or 'n/d')} · "
                f"Confiance : {html.escape(p.niveau_confiance)}"
                + (f"<br>{html.escape(p.ville)}" if p.ville else "")
            ),
        }
        for p in points
    ]

    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>{html.escape(titre)}</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
  html, body {{ margin: 0; height: 100%; font-family: system-ui, sans-serif; }}
  #carte {{ height: 100%; width: 100%; }}
  .legende {{
    position: absolute; bottom: 20px; right: 20px; z-index: 1000;
    background: white; padding: 10px 14px; border-radius: 8px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.3); font-size: 13px;
  }}
  .legende span {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; }}
</style>
</head>
<body>
<div id="carte"></div>
<div class="legende">
  <div><span style="background:{_COULEUR_PAR_NIVEAU['AAA']}"></span>AAA — Sur mesure</div>
  <div><span style="background:{_COULEUR_PAR_NIVEAU['AA']}"></span>AA — Aligné</div>
  <div><span style="background:{_COULEUR_PAR_NIVEAU['A']}"></span>A — Repéré</div>
</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
  const marqueurs = {json.dumps(marqueurs)};
  const carte = L.map('carte').setView([{centre_lat}, {centre_lon}], {5 if points else 3});
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    attribution: '&copy; OpenStreetMap contributors'
  }}).addTo(carte);
  marqueurs.forEach(m => {{
    L.circleMarker([m.lat, m.lon], {{
      radius: 8, color: m.couleur, fillColor: m.couleur, fillOpacity: 0.8
    }}).addTo(carte).bindPopup(m.popup);
  }});
</script>
</body>
</html>
"""
