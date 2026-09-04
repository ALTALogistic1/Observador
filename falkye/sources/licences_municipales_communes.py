"""Logique commune aux connecteurs de licences d'affaires municipales
(Vancouver, Toronto — spec section 7, Signal registre_corporatif).

Le vrai bogue à éviter ici (même famille que REQ/Corporations Canada avant
leurs propres corrections de calibration, voir docs/STATUT_RESEAU.md) : au
tout premier scan d'une municipalité, TOUTE ligne rencontrée serait "nouvelle"
au sens de `LicenceMunicipaleEntry` (le miroir est vide) — produire un signal
pour chacune traiterait potentiellement des dizaines de milliers de licences
déjà anciennes comme des "nouveaux établissements". `detecter_nouvelles_licences`
gère donc explicitement le cas "premier scan" (miroir vide pour cette
municipalité) : la population initiale du miroir ne produit AUCUNE nouvelle
licence candidate, exactement comme `ingest_snapshot` pour Corporations
Canada. Seuls les scans SUIVANTS peuvent produire des candidats.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from falkye.models.licence_municipale_entry import LicenceMunicipaleEntry
from falkye.sources.column_mapping import normaliser


@dataclass
class LicenceBrute:
    """Une ligne source déjà extraite/nettoyée par le connecteur d'une ville —
    format commun avant le diff, indépendant du schéma réel de chaque
    portail municipal."""

    nom: str
    adresse: str | None
    type_entreprise: str | None
    identifiant_source: str  # pour source_ref — pas la clé de diff (voir module)


def _cle(municipalite: str, nom: str, adresse: str | None) -> str:
    return f"{normaliser(nom)}|{normaliser(adresse or '')}"


# Rebranchement sur le moteur de diff générique (Chantier 1, suivi
# 2026-09-04) — vocabulaire logique PARTAGÉ par licences_toronto.py et
# licences_vancouver.py (registry/sources.yaml, mêmes champs_pertinents pour
# les deux villes). La clé du moteur générique, elle, N'EST PAS partagée
# (voir SourceDef.cle_naturelle par ville) — Toronto : identifiant_licence
# (persistant) ; Vancouver : composite nom+adresse (le numéro de licence y
# est réattribué chaque année, voir docs/ARCHITECTURE.md).
CHAMPS_PERTINENTS_MUNIC = {"nom_entreprise", "adresse", "type_entreprise", "date_emission"}


def colonnes_vues_depuis_lignes(lignes_brutes: list[dict], mapping: dict[str, str]) -> dict[str, str]:
    """`colonnes_vues` pour le moteur générique — présentes seulement quand
    la colonne API/CSV brute dont dépend le champ logique existe réellement
    dans les lignes récupérées CE run (même principe que req.py::
    _colonnes_entreprise_vues)."""
    presentes: set[str] = set()
    for row in lignes_brutes:
        presentes.update(row.keys())
    return {logique: "str" for logique, brute in mapping.items() if brute in presentes}


def detecter_nouvelles_licences(
    db_session: Session, municipalite: str, lignes: list[LicenceBrute]
) -> list[LicenceBrute]:
    """Met à jour le miroir local pour `municipalite` et retourne les lignes
    qui représentent un ÉTABLISSEMENT GENUINEMENT NOUVEAU (jamais vu à cette
    adresse sous ce nom lors d'un scan précédent) — PAS un signal en soi
    (voir docstring du module pour le cas "premier scan"), juste la liste des
    candidates. Le connecteur appelant les combine ensuite avec la
    vérification croisée Corporations Canada avant de produire un RawSignal
    (voir sources.yaml:licences_affaires_municipales, "NON NÉGOCIABLE").

    Note : le "premier scan" est déterminé par l'état du miroir (au moins
    UNE ligne déjà présente pour cette municipalité), pas par un compteur
    d'appels — un appel avec `lignes=[]` ne peuple rien et ne "consomme"
    donc pas le statut de premier scan (couvert par les tests)."""
    premier_scan = (
        db_session.execute(
            select(LicenceMunicipaleEntry.id).where(LicenceMunicipaleEntry.municipalite == municipalite).limit(1)
        ).scalar_one_or_none()
        is None
    )

    nouvelles: list[LicenceBrute] = []
    for ligne in lignes:
        cle = _cle(municipalite, ligne.nom, ligne.adresse)
        existing = db_session.execute(
            select(LicenceMunicipaleEntry).where(
                LicenceMunicipaleEntry.municipalite == municipalite,
                LicenceMunicipaleEntry.cle_entreprise == cle,
            )
        ).scalar_one_or_none()

        if existing is None:
            db_session.add(
                LicenceMunicipaleEntry(
                    municipalite=municipalite,
                    cle_entreprise=cle,
                    nom=ligne.nom,
                    adresse=ligne.adresse,
                    type_entreprise=ligne.type_entreprise,
                )
            )
            if not premier_scan:
                nouvelles.append(ligne)
        else:
            existing.nom = ligne.nom
            existing.type_entreprise = ligne.type_entreprise

    return nouvelles
