"""Détection d'expansion inter-provinciale — spec Radar+, point 7 ("nouvelle
capacité générale, pas liée à une seule sphère"), plan confirmé le 2026-09-03.

LIMITE HONNÊTE, documentée avant tout code (exigence explicite d'Alexandre) :
aucun identifiant unique n'est partagé entre le REQ et les registres/licences
des autres provinces — le seul rapprochement possible est PAR NOM, une
heuristique imparfaite (faux positifs : deux entreprises différentes, nom
similaire ; faux négatifs : même entreprise, raison sociale différente d'une
province à l'autre). Deux garde-fous, jamais un seul :
  1. STRUCTUREL — le bonus de confiance qui en découle (voir evaluer_pour_
     company ci-dessous) est plafonné à BONUS_MAX (15 points sur 100), jamais
     assez pour faire à lui seul basculer un signal faible en confiance
     élevée.
  2. TEXTUEL — falkye/engine.py inclut toujours un libellé explicitement
     hedgé ("à valider") dans la justification de la notification, jamais
     présenté comme un fait acquis.

Ne fusionne JAMAIS deux Company — les dossiers restent distincts et
traçables (voir falkye/models/expansion_interprovinciale.py), seul le LIEN
est stocké.

D'où vient "quelle province" pour une source : `SourceDef.province_code`
(registry/sources.yaml), un champ délibérément DISTINCT de `SourceDef.region`
(texte libre, granularité incohérente — "Vancouver" vs "Québec" vs "Canada",
impropre à une comparaison programmatique). Seules les sources dont le
territoire est une province précise et vérifiable le portent (req -> qc,
licences_vancouver -> bc, licences_toronto -> on, contrats_nouvelle_ecosse ->
ns) — tout le reste (fédéral, national, classements pancanadiens) reste
`None`, jamais deviné, simplement exclu du mécanisme.

Rapprochement par `rapidfuzz.fuzz.WRatio` — même scorer déjà utilisé dans
falkye/resolution.py et falkye/sources/req.py, pour rester cohérent avec
l'unique algorithme de correspondance floue du projet plutôt que d'en
introduire un deuxième. Seuil plancher SEUIL_RAPPROCHEMENT=80 pour même
enregistrer un lien candidat — plus bas que les 92 de
resolution.py::SEUIL_RESOLUTION_CONFIANTE (ici le rapprochement se fait par
nom SEUL, entre deux registres différents, jamais confirmé par un
identifiant commun comme le NEQ — donc structurellement plus faible), mais
reste une vraie barre, pas n'importe quelle ressemblance.

GATING : réservé au plan RADAR minimum (jamais Écho) — décision produit
d'Alexandre (2026-09-03), pas une contrainte de coût technique (aucun appel
externe ici, seulement du calcul local) : "un bonus qui améliore réellement
la qualité d'un résultat déjà présent est un enrichissement, et notre
principe est qu'aucun enrichissement de résultat ne reste dans Écho, peu
importe son coût de calcul." Le gating est appliqué par l'appelant
(falkye/engine.py) — ce module lui-même reste agnostique du plan, comme
falkye/ponderation.py/falkye/pertinence.py le sont déjà pour leurs propres
mécanismes Radar+.

Tourne en PASSE PAR LOT (falkye/engine.py::run_veille_continue, greffée en
fin d'ingestion, AVANT la génération des notifications puisque le bonus en
dépend — voir docstring de run_veille_continue), jamais à l'ingestion d'un
signal individuel : comparer un nouveau Company contre tout le reste de la
table à chaque signal serait disproportionné. Rattrapage manuel disponible
via `falkye scan detecter-expansions` (balaye tout le dossier cumulatif,
utile après l'activation initiale ou l'ajout d'une nouvelle source
provinciale)."""
from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz, process
from sqlalchemy import select
from sqlalchemy.orm import Session

from falkye.models.company import Company
from falkye.models.expansion_interprovinciale import LienInterprovincial
from falkye.registry.loader import Registry

SEUIL_RAPPROCHEMENT = 80.0
BONUS_MAX = 15.0

NOMS_PROVINCES = {
    "qc": "Québec",
    "on": "Ontario",
    "bc": "Colombie-Britannique",
    "ns": "Nouvelle-Écosse",
}


def _provinces_pour_company(company: Company, registry: Registry) -> set[str]:
    """Provinces distinctes couvertes par les signaux de CE company, d'après
    SourceDef.province_code — jamais devinées, seulement celles que le
    registre associe explicitement à une source."""
    provinces = set()
    for signal in company.signals:
        source_def = registry.sources.get(signal.source_id)
        if source_def is not None and source_def.province_code:
            provinces.add(source_def.province_code)
    return provinces


def detecter_expansions(
    db_session: Session, registry: Registry, companies: list[Company] | None = None
) -> list[LienInterprovincial]:
    """Cherche des rapprochements inter-provinciaux par nom pour `companies`
    (défaut : TOUS les Company de la base, utile pour un rattrapage complet —
    voir `falkye scan detecter-expansions`) contre le reste du dossier
    cumulatif. Idempotent : ne recrée jamais un lien déjà enregistré pour la
    même paire (company_id_a, company_id_b)."""
    tous = db_session.execute(select(Company)).scalars().all()
    provinces_par_company = {c.id: _provinces_pour_company(c, registry) for c in tous}

    # Seuls les Company avec au moins une province connue peuvent participer,
    # des deux côtés de la comparaison — les autres n'ont simplement rien à
    # rapprocher (aucune source à province_code parmi leurs signaux).
    pool = [c for c in tous if provinces_par_company[c.id]]
    pool_par_id = {c.id: c for c in pool}

    a_verifier = companies if companies is not None else pool
    a_verifier = [c for c in a_verifier if provinces_par_company.get(c.id)]

    liens_existants = {
        (l.company_id_a, l.company_id_b)
        for l in db_session.execute(select(LienInterprovincial)).scalars().all()
    }

    nouveaux_liens: list[LienInterprovincial] = []
    for company in a_verifier:
        provinces_company = provinces_par_company[company.id]
        # Candidats : au moins une province QUI DIFFÈRE de toutes celles de
        # `company` — une correspondance dans la MÊME province n'est pas une
        # expansion inter-provinciale (et relève déjà, pour le REQ, de la
        # résolution NEQ existante, falkye/resolution.py).
        candidats = [
            c
            for c in pool
            if c.id != company.id and (provinces_par_company[c.id] - provinces_company)
        ]
        if not candidats:
            continue

        choices = {c.id: c.nom_detecte_normalise for c in candidats}
        ranked = process.extract(company.nom_detecte_normalise, choices, scorer=fuzz.WRatio, limit=3)

        for _, score, autre_id in ranked:
            if score < SEUIL_RAPPROCHEMENT:
                continue
            id_a, id_b = sorted((company.id, autre_id))
            if (id_a, id_b) in liens_existants:
                continue
            province_company = min(provinces_company)
            province_autre = min(provinces_par_company[autre_id])
            province_a = province_company if company.id == id_a else province_autre
            province_b = province_autre if company.id == id_a else province_company
            lien = LienInterprovincial(
                company_id_a=id_a,
                company_id_b=id_b,
                province_a=province_a,
                province_b=province_b,
                score_correspondance=score,
            )
            db_session.add(lien)
            liens_existants.add((id_a, id_b))
            nouveaux_liens.append(lien)

    db_session.flush()
    return nouveaux_liens


@dataclass(frozen=True)
class EvaluationExpansion:
    """Résultat prêt à consommer par falkye/scoring.py et falkye/engine.py —
    un seul aller-retour DB (evaluer_pour_company) plutôt que deux fonctions
    séparées qui interrogeraient la même table."""

    bonus: float  # 0.0 si aucun lien
    texte_hedge: str | None  # None si aucun lien — toujours hedgé, jamais un fait


def evaluer_pour_company(db_session: Session, company: Company) -> EvaluationExpansion:
    """Bonus de confiance (mise à l'échelle linéaire entre SEUIL_RAPPROCHEMENT,
    score 80 -> bonus 0, et 100 -> bonus BONUS_MAX, jamais davantage — voir
    garde-fou structurel dans la docstring du module) et libellé hedgé pour
    `company`, à partir du lien le plus fort s'il y en a plusieurs. Ne
    vérifie PAS le plan du profil — voir docstring du module, le gating est
    la responsabilité de l'appelant (falkye/engine.py)."""
    liens = (
        db_session.execute(
            select(LienInterprovincial).where(
                (LienInterprovincial.company_id_a == company.id)
                | (LienInterprovincial.company_id_b == company.id)
            )
        )
        .scalars()
        .all()
    )
    if not liens:
        return EvaluationExpansion(bonus=0.0, texte_hedge=None)

    meilleur = max(liens, key=lambda l: l.score_correspondance)
    fraction = (meilleur.score_correspondance - SEUIL_RAPPROCHEMENT) / (100.0 - SEUIL_RAPPROCHEMENT)
    bonus = max(0.0, min(BONUS_MAX, fraction * BONUS_MAX))

    autre_province = meilleur.province_b if meilleur.company_id_a == company.id else meilleur.province_a
    nom_province = NOMS_PROVINCES.get(autre_province, autre_province.upper())
    texte = (
        f"présence possible en {nom_province} (nom similaire à "
        f"{meilleur.score_correspondance:.0f}% — à valider)"
    )
    return EvaluationExpansion(bonus=round(bonus, 1), texte_hedge=texte)
