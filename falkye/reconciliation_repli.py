"""Rapatrier le journal de repli dans la base, quand elle répond à nouveau.

**Pourquoi la base ne peut pas être la source de vérité ici.** Les lignes
d'exécution restées `en_cours` sont ouvertes *parce que* la base était
injoignable au moment d'écrire leur fin. Elle est donc, par construction, le
seul témoin qui ne sait rien. Un mécanisme qui reconstruirait la vérité en
l'interrogeant conclurait que le run tourne encore.

Le 2026-09-08 en donne la preuve : le minuteur s'est déclenché à 14 h 17 UTC
pendant le blocage du quota de lectures. Ce déclenchement n'a laissé **aucune**
trace en base. Ses deux lignes — début, puis échec avec sa cause — n'existent
que dans `/var/lib/falkye/journal-repli.jsonl`.

Ça déplace `falkye/exploitation.py` de « filet de sécurité » à **source de
vérité de la réconciliation**. Quatre règles en découlent, posées avec la
décision plutôt que découvertes après :

1. **Le format devient un contrat.** Chaque ligne porte sa version
   (`FORMAT_REPLI`). Une ligne illisible est sautée, comptée et signalée —
   jamais une interruption. Une réconciliation que son propre fichier d'entrée
   peut tuer ne sert à rien le jour où on en a besoin.
2. **Elle tourne au début du cycle suivant**, comme `reconcilier_livraisons` :
   même place, même raison — c'est le premier moment où la base répond.
3. **Marquer, jamais faire tourner le fichier.** Il est le seul témoin des
   pannes où la base était muette; le consommer en le détruisant supprimerait
   la preuve au moment où l'on s'en sert. Le marquage est l'identifiant de
   ligne retrouvé en base, ce qui rend la reprise relançable sans perte si elle
   échoue à mi-parcours. Une rotation par âge ou par taille reste possible,
   mais comme geste d'exploitation séparé — jamais comme effet de bord d'une
   lecture.
4. **Un fichier absent et un fichier vide ne disent pas la même chose.** Vide :
   « rien à réconcilier ». Absent : « je ne sais pas » — disque plein, chemin
   changé, permissions. Les confondre ferait de la réconciliation un cycle qui
   réussit à vide, et on connaît le motif.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from falkye.exploitation import FORMAT_REPLI, chemin_repli
from falkye.models.journal_exploitation import EvenementExploitation, JournalExploitation

logger = logging.getLogger(__name__)

#: Les versions de format que ce lecteur sait interpréter. Une ligne SANS champ
#: `format` est de version 1 — celui d'avant le chantier 2, dont des lignes
#: existent déjà sur l'hôte. Les rejeter perdrait exactement la preuve pour
#: laquelle ce fichier existe.
FORMATS_LUS = frozenset({1, FORMAT_REPLI})


class EtatJournal(str, Enum):
    """Ce que la lecture du fichier a trouvé — trois états, jamais deux.

    `INTROUVABLE` n'est pas un échec de la réconciliation : c'est un état normal
    sur une machine où la base n'est jamais tombée. Mais ce n'est pas non plus
    `VIDE`, et c'est toute la distinction : l'un dit « rien à reprendre »,
    l'autre dit « je n'ai pas pu regarder ».
    """

    INTROUVABLE = "introuvable"
    VIDE = "vide"
    LU = "lu"


@dataclass
class RapportRepli:
    etat: EtatJournal
    chemin: Path
    raison: str | None = None
    lignes_lues: int = 0
    lignes_illisibles: int = 0
    lignes_format_inconnu: int = 0
    lignes_reprises: int = 0
    lignes_deja_reprises: int = 0
    #: Lignes de format 1, sans identifiant propre, à qui la lecture en a
    #: DÉRIVÉ un depuis leur contenu. Compté à part : leur idempotence tient à
    #: la stabilité de leur contenu, pas à une identité écrite à la source.
    lignes_identifiees_par_empreinte: int = 0
    #: Les identifiants des lignes illisibles ne peuvent pas exister — c'est
    #: leur numéro dans le fichier qui les nomme, pour qu'on puisse aller voir.
    numeros_illisibles: list[int] = field(default_factory=list)

    @property
    def a_repris_quelque_chose(self) -> bool:
        return self.lignes_reprises > 0

    def resume_lisible(self) -> str:
        if self.etat is EtatJournal.INTROUVABLE:
            return f"journal de repli INTROUVABLE ({self.chemin}) — {self.raison}"
        if self.etat is EtatJournal.VIDE:
            return f"journal de repli vide ({self.chemin}) — rien à reprendre"
        parts = [
            f"{self.lignes_lues} ligne(s) lue(s)",
            f"{self.lignes_reprises} reprise(s)",
            f"{self.lignes_deja_reprises} déjà reprise(s)",
        ]
        if self.lignes_illisibles:
            parts.append(f"{self.lignes_illisibles} ILLISIBLE(S) aux lignes "
                         f"{', '.join(str(n) for n in self.numeros_illisibles)}")
        if self.lignes_identifiees_par_empreinte:
            parts.append(
                f"{self.lignes_identifiees_par_empreinte} identifiée(s) par empreinte "
                "(format 1)"
            )
        if self.lignes_format_inconnu:
            parts.append(f"{self.lignes_format_inconnu} de format inconnu")
        return "journal de repli : " + ", ".join(parts)


def _lire_lignes(chemin: Path, rapport: RapportRepli) -> list[dict]:
    """Les lignes exploitables. Une ligne cassée n'emporte jamais les autres."""
    lignes = []
    with chemin.open("r", encoding="utf-8", errors="replace") as fichier:
        for numero, brute in enumerate(fichier, start=1):
            brute = brute.strip()
            if not brute:
                continue
            rapport.lignes_lues += 1
            try:
                ligne = json.loads(brute)
                if not isinstance(ligne, dict):
                    raise ValueError("la ligne n'est pas un objet")
            except (json.JSONDecodeError, ValueError):
                # Le cas nominal : une écriture interrompue tronque la DERNIÈRE
                # ligne. Une seule est perdue, et on dit laquelle.
                rapport.lignes_illisibles += 1
                rapport.numeros_illisibles.append(numero)
                continue
            if ligne.get("format", 1) not in FORMATS_LUS:
                # Une version PLUS RÉCENTE que ce lecteur : ne pas deviner. La
                # compter et la laisser dans le fichier, elle sera reprise par
                # un lecteur qui la comprend.
                rapport.lignes_format_inconnu += 1
                continue
            lignes.append(ligne)
    return lignes


def identifiant_de(ligne: dict) -> tuple[str, bool]:
    """(identifiant, dérivé) — l'identité d'une ligne de repli.

    **Le format 1 n'avait pas prévu sa propre relecture.** Ses lignes n'ont pas
    d'identifiant, et deux d'entre elles existent sur l'hôte : celles du
    déclenchement du 2026-09-08 à 14 h 17 UTC, la seule trace de ce
    déclenchement où que ce soit. Les sauter faute d'identité perdrait
    exactement la preuve pour laquelle ce fichier existe; les reprendre sans
    identité créerait un doublon à chaque cycle.

    L'identité se dérive donc de leur contenu. Ces lignes sont ajoutées en fin
    de fichier et jamais réécrites : leur contenu est stable, donc leur
    empreinte l'est aussi. Le coût assumé : deux lignes rigoureusement
    identiques — même microseconde, même événement, même détail, même cause —
    seraient prises pour une seule. Perdre le doublon d'une trace vaut mieux
    que reprendre la trace en boucle.
    """
    identifiant = ligne.get("id")
    if identifiant:
        return identifiant, False
    empreinte = hashlib.sha256(
        json.dumps(
            [
                ligne.get("moment"),
                ligne.get("evenement"),
                ligne.get("detail"),
                ligne.get("cause_du_repli"),
            ],
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:32]
    return empreinte, True


def _en_ligne_de_journal(ligne: dict, identifiant: str) -> JournalExploitation | None:
    """Convertit une ligne de repli en ligne de journal, ou None si le contenu
    ne permet pas de le faire honnêtement."""
    try:
        evenement = EvenementExploitation(ligne["evenement"])
    except (KeyError, ValueError):
        return None

    moment = None
    brut = ligne.get("moment")
    if brut:
        try:
            moment = datetime.fromisoformat(brut)
            if moment.tzinfo is not None:
                moment = moment.replace(tzinfo=None)
        except ValueError:
            moment = None

    detail = ligne.get("detail")
    cause = ligne.get("cause_du_repli")
    if cause:
        # La cause du repli VOYAGE avec la ligne : sans elle, une ligne
        # rapatriée serait indiscernable d'une ligne écrite normalement, et
        # « la base était muette à ce moment-là » se perdrait.
        detail = f"{detail} — [repli : {cause}]" if detail else f"[repli : {cause}]"

    return JournalExploitation(
        evenement=evenement,
        detail=detail,
        version=ligne.get("version"),
        moment=moment,
        repli_id=identifiant,
    )


def reconcilier_journal_repli(db_session: Session, chemin: Path | None = None) -> RapportRepli:
    """Rapatrie les lignes du journal de repli. Ne lève jamais.

    Ne lève pas, par le même raisonnement que `journaliser` : une panne
    d'observation ne doit pas devenir une panne de production. Mais elle est
    RAPPORTÉE — un rapport qui dit « je n'ai pas pu » n'est pas un silence.
    """
    chemin = chemin or chemin_repli()
    rapport = RapportRepli(etat=EtatJournal.INTROUVABLE, chemin=chemin)

    try:
        if not chemin.exists():
            rapport.raison = "le fichier n'existe pas"
            return rapport
        if chemin.stat().st_size == 0:
            rapport.etat = EtatJournal.VIDE
            return rapport
        lignes = _lire_lignes(chemin, rapport)
    except OSError as exc:
        # Disque plein, permissions, chemin devenu un répertoire. « Je ne sais
        # pas » — surtout pas « rien à réconcilier ».
        rapport.raison = f"{type(exc).__name__}: {exc}"
        return rapport

    rapport.etat = EtatJournal.LU

    identites = [identifiant_de(ligne) for ligne in lignes]
    identifiants = [identifiant for identifiant, _ in identites]
    deja = set()
    if identifiants:
        deja = {
            valeur
            for (valeur,) in db_session.execute(
                select(JournalExploitation.repli_id).where(
                    JournalExploitation.repli_id.in_(identifiants)
                )
            ).all()
        }

    for ligne, (identifiant, derive) in zip(lignes, identites):
        if identifiant in deja:
            rapport.lignes_deja_reprises += 1
            continue
        objet = _en_ligne_de_journal(ligne, identifiant)
        if objet is None:
            rapport.lignes_illisibles += 1
            continue
        db_session.add(objet)
        rapport.lignes_reprises += 1
        if derive:
            rapport.lignes_identifiees_par_empreinte += 1
        # Deux lignes identiques DANS LE MÊME fichier auraient la même
        # empreinte : la seconde doit être vue comme déjà reprise, sans quoi
        # l'insertion violerait la contrainte d'unicité et emporterait tout le
        # lot avec elle.
        deja.add(identifiant)

    if rapport.lignes_reprises:
        db_session.commit()
    return rapport
