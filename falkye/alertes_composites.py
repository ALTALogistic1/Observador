"""Alertes composites préconfigurées par cas d'usage — spec section 4bis,
remplace la fonctionnalité "pondération du moteur de score personnalisable"
d'origine (jugée trop abstraite pour un usage réel, décision d'Alexandre du
2026-09-02) : "plutôt qu'un curseur générique de pondération, des modèles
concrets ancrés dans des croisements de signaux déjà identifiés."

Le mécanisme sous-jacent (falkye/pertinence.py::PonderationValeurs,
falkye/models/ponderation_personnalisee.py::PonderationPersonnalisee,
falkye/ponderation.py::ponderation_pour_profil) reste EXACTEMENT le même —
seule la façon de l'exposer à l'utilisateur change : au lieu de six leviers
numériques bruts (`ponderation definir --base-a/--bonus-velocite-max/...`,
retiré de la CLI), trois presets nommés qui appliquent un bundle de valeurs
déjà réfléchi pour un cas d'usage précis.

LIMITE HONNÊTE, À NE PAS PASSER SOUS SILENCE : les trois cas d'usage nommés
mentionnent tous une composante "entreprise jeune" (âge de l'entreprise) —
ex. "alerte cautionnement : contrat public + JEUNE entreprise". Aucune donnée
d'âge/date de fondation n'est captée nulle part dans le pipeline actuel
(`Company` n'a que `first_detected_at`, la date où FALKYE a REPÉRÉ
l'entreprise — pas sa date de fondation réelle ; le miroir REQ,
`falkye/models/req_entry.py`, ne capture pas non plus de date d'immatriculation
réelle). Les presets ci-dessous approximent donc chaque cas d'usage avec les
SEULS leviers que falkye/pertinence.py modélise aujourd'hui — poids par palier
de correspondance (A/AA/AAA), bonus signal-par-absence, bonus de vélocité —
PAS un filtre réel sur l'âge de l'entreprise. Ajouter un vrai facteur d'âge
demanderait de capturer une donnée supplémentaire (et de confirmer que le
vrai fichier REQ la contient — non vérifiable dans cet environnement de
développement, accès réseau à registreentreprises.gouv.qc.ca bloqué), pas
seulement un ajustement de pondération : scope à discuter séparément si
l'approximation ci-dessous ne suffit pas en usage réel.
"""
from __future__ import annotations

from dataclasses import dataclass

from falkye.pertinence import PonderationValeurs


@dataclass(frozen=True)
class AlerteCompositeDef:
    id: str
    nom: str
    description: str
    ponderation: PonderationValeurs


ALERTE_CAUTIONNEMENT = AlerteCompositeDef(
    id="alerte_cautionnement",
    nom="Alerte cautionnement",
    description=(
        "Contrat public décroché + entreprise jeune (approximé — voir limite honnête "
        "en tête du module) : une entreprise qui vient de décrocher un contrat public a "
        "typiquement besoin d'un cautionnement rapidement. Favorise la VÉLOCITÉ (un "
        "contrat frais, rapproché d'autres signaux, pèse plus lourd) plutôt que "
        "l'absence ou la précision de sphère."
    ),
    ponderation=PonderationValeurs(bonus_velocite_max=40.0, bonus_velocite_par_signal=15.0),
)

ALERTE_FINANCEMENT_PRECOCE = AlerteCompositeDef(
    id="alerte_financement_precoce",
    nom="Alerte financement précoce",
    description=(
        "Croissance visible sans subvention ni classement encore visible — le cas "
        "d'origine du principe de signal par absence (spec section 6, persona "
        "investisseur providentiel). Double le poids du bonus d'absence par rapport à "
        "la valeur par défaut : c'est le levier central de ce cas d'usage."
    ),
    ponderation=PonderationValeurs(bonus_absence=30.0),
)

ALERTE_ACQUISITION = AlerteCompositeDef(
    id="alerte_acquisition",
    nom="Alerte acquisition",
    description=(
        "Classement de croissance + subvention + entreprise jeune (approximé) — un "
        "profil de cible d'acquisition mature. Favorise une correspondance de sphère "
        "PRÉCISE (paliers A/AA/AAA relevés) et la vélocité (plusieurs signaux forts "
        "rapprochés), plutôt que l'absence."
    ),
    ponderation=PonderationValeurs(
        base_a=40.0, base_aa=70.0, base_aaa=100.0, bonus_absence=5.0,
        bonus_velocite_max=35.0, bonus_velocite_par_signal=12.0,
    ),
)

ALERTES_COMPOSITES: dict[str, AlerteCompositeDef] = {
    a.id: a for a in [ALERTE_CAUTIONNEMENT, ALERTE_FINANCEMENT_PRECOCE, ALERTE_ACQUISITION]
}


def alerte_composite(preset_id: str) -> AlerteCompositeDef | None:
    return ALERTES_COMPOSITES.get(preset_id)
