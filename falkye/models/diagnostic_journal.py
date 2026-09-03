"""Journal de diagnostic généralisé — spec section 8bis (2026-09-03),
remplace `CandidatSphere` (falkye/models/candidat_sphere.py, retiré).

Un seul mécanisme plutôt que trois séparés, avec un discriminant
`type_diagnostic` :
  - `candidat_sphere`       : le Niveau 2 n'a pu rattacher une description à
                              AUCUNE sphère existante (ancien rôle de
                              CandidatSphere, inchangé).
  - `candidat_client_cible` : le Niveau 2 n'a pu rattacher une description de
                              clientèle cible à AUCUNE catégorie existante NI
                              reconnaître un "aucune_restriction" — même
                              garde-fou (falkye/assistance_client_cible_ia.py).
  - `source_manquante`      : une source de données qui devrait exister mais
                              n'existe pas encore dans le registre, trouvée en
                              diagnostiquant un cas précis (ex. un organisme
                              public absent du REQ, un fonds de financement
                              découvert en creusant un persona) — journalisée
                              MANUELLEMENT par Alexandre (mode opérateur,
                              `falkye diagnostic ajouter-source-manquante`),
                              jamais par un appel Niveau 2 (ce n'est pas une
                              classification de texte, c'est une observation
                              produit).

`profile_id` NULLABLE : un `source_manquante` trouvé en explorant un persona
en général n'est pas toujours rattaché à un profil précis — jamais forcé
(principe directeur #1, "jamais fabriquer une valeur").

Garde-fou non négociable, préservé structurellement pour candidat_sphere ET
candidat_client_cible (voir falkye/assistance_sphere_ia.py /
falkye/assistance_client_cible_ia.py) : le Niveau 2 ne crée JAMAIS lui-même
une nouvelle sphère ou catégorie dans le registre officiel — un cas non
résolu est journalisé ici, à examiner par Alexandre, exactement comme la
sphère "Financement / accès au capital" a été ajoutée par décision humaine,
jamais automatiquement."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from falkye.models.base import Base, utcnow


class TypeDiagnostic(str, enum.Enum):
    CANDIDAT_SPHERE = "candidat_sphere"
    CANDIDAT_CLIENT_CIBLE = "candidat_client_cible"
    SOURCE_MANQUANTE = "source_manquante"


class DiagnosticJournal(Base):
    __tablename__ = "journal_diagnostic"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type_diagnostic: Mapped[TypeDiagnostic] = mapped_column(
        Enum(TypeDiagnostic, native_enum=False), nullable=False
    )
    profile_id: Mapped[int | None] = mapped_column(ForeignKey("profiles.id"), nullable=True)

    # Description libre TELLE QUE saisie — jamais reformulée à cette étape
    # (principe directeur #1) : la valeur brute est ce qu'Alexandre doit voir
    # pour juger. Pour un candidat_sphere/candidat_client_cible, c'est le
    # texte de l'utilisateur ; pour un source_manquante, la note d'Alexandre
    # décrivant la source absente.
    texte_description: Mapped[str] = mapped_column(Text, nullable=False)

    # Raisonnement du Niveau 2 — absent (None) pour un source_manquante,
    # journalisé manuellement sans appel modèle.
    resume_niveau2: Mapped[str | None] = mapped_column(Text, nullable=True)

    # "a_examiner" (défaut) | "sphere_creee"/"categorie_creee" |
    # "rattache_existant" | "source_ajoutee" | "ecarte" — mis à jour
    # manuellement par Alexandre après examen, jamais par le système.
    statut: Mapped[str] = mapped_column(String(20), nullable=False, default="a_examiner")

    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    profile = relationship("Profile")
