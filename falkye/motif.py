"""Le motif du repérage — pourquoi CETTE entreprise, dit par les faits.

**Ce que ce module remplace.** Le moteur écrivait
`signal.titre_ou_description or "Signal détecté"`. Quand la source ne fournit
aucun libellé, le motif devenait donc « Signal détecté » — une phrase qui ne dit
rien et se répète à l'identique sur chaque ligne. C'est ce qu'a produit le
premier envoi réel du 2026-09-06 : 306 lignes portant toutes le même texte, alors
que chaque signal portait un montant distinct, de 112 500 $ à 5 000 000 $, déjà
en base et jamais regardé.

Le mandat du chantier 28 demande « le motif du repérage **tiré de la structure de
faits** ». La structure de faits, ce n'est pas seulement le libellé de la source :
c'est aussi ce que le signal porte de typé. Ce module va le chercher.

**Trois règles, dans cet ordre.**

1. *Les mots de la source d'abord.* Quand elle décrit l'événement, on la reprend
   telle quelle — personne ne dit mieux qu'elle ce qui s'est passé.
2. *Sinon, les faits typés.* Le montant associé au signal est le seul fait que
   TOUS les signaux portent de la même façon, quelle que soit la source. Il se
   rend sans interprétation : un nombre et une devise.
3. *Sinon, rien.* Pas de phrase de remplissage. Un bloc qui affiche sa catégorie
   sans motif dit exactement ce qu'on sait; « Signal détecté » prétend dire
   quelque chose de plus. La charte (section 16) interdit l'encouragement non
   mérité, et une ligne qui se répète à l'identique 306 fois en est une.

**Ce que ce module ne fait PAS, délibérément.**

*Il ne rend aucun champ libre de `Signal.champs`.* Ces clés sont propres à chaque
source et leur contenu aussi : `programme: "Investissement Québec"` y nomme la
source, que la neutralité des libellés (charte section 6) interdit précisément de
faire apparaître. Rendre `champs` en vrac ferait fuir ce nom dans le courriel
sans que personne l'ait décidé.

*Il n'affiche aucune date.* `Signal.detected_at` vaut l'heure de l'ingestion pour
les sources qui ne datent pas leurs événements — écrire « financé le 6 septembre »
à partir de là énoncerait un fait faux. Une date n'entrera que lorsqu'une source
en fournira une vraie, et il faudra alors savoir laquelle.

*Il n'interprète pas.* « Ce financement suggère un projet d'expansion » est une
ligne d'interprétation, et elle appartient au chantier 21, par gabarit lié au
couple signal × sphère. La place lui est déjà réservée dans le résumé.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from falkye.models.signal import Signal

# Espace insécable (U+00A0), écrit en clair parce qu'un espace ordinaire est
# indiscernable à la lecture du code. Il sépare les milliers et précède le
# symbole de devise : un retour à la ligne au milieu d'un montant, ou juste
# avant le « $ », rendrait le chiffre pénible à lire dans un client de
# messagerie qui replie les lignes lui-même.
ESPACE_INSECABLE = "\u00a0"


def montant_lisible(valeur: float | None) -> str | None:
    """Un montant en dollars canadiens, lisible par un humain francophone.

    Espaces insécables comme séparateur de milliers et devise après le nombre —
    la convention d'ici. Les cents ne sont rendus que s'ils existent : « 350 000 $
    » plutôt que « 350 000,00 $ », qui donne au chiffre une précision qu'il n'a
    pas.
    """
    if valeur is None:
        return None
    entier = int(valeur)
    if valeur == entier:
        corps = f"{entier:,}".replace(",", ESPACE_INSECABLE)
    else:
        corps = f"{valeur:,.2f}".replace(",", ESPACE_INSECABLE).replace(".", ",")
    return f"{corps}{ESPACE_INSECABLE}$"


def motif_du_reperage(signal: "Signal") -> str:
    """Le motif, ou une chaîne vide quand les faits n'en portent aucun.

    Chaîne vide plutôt que None : `NotificationSignal.justification` est
    obligatoire, et le vide y dit la vérité — « rien au-delà de la catégorie ».
    Le rendu saute alors la ligne au lieu d'afficher un texte creux.
    """
    libelle = (signal.titre_ou_description or "").strip()
    if libelle:
        return libelle

    montant = montant_lisible(signal.valeur_associee)
    if montant:
        return f"Montant associé : {montant}"

    return ""


def motif_avec_mots_cles(signal: "Signal", mots_cles: list[str]) -> str:
    """Le motif, suivi des mots-clés du profil qui ont mordu.

    Les mots-clés sont un fait sur la CORRESPONDANCE, pas sur l'entreprise : ils
    disent pourquoi ce signal est arrivé chez ce profil-ci. Ils se rattachent donc
    au motif au lieu de le remplacer — et quand il n'y en a pas, ils tiennent
    seuls plutôt que d'ouvrir la ligne par un tiret orphelin, ce que faisait la
    version précédente.
    """
    motif = motif_du_reperage(signal)
    if not mots_cles:
        return motif
    correspondance = f"correspond aux mots-clés : {', '.join(mots_cles)}"
    return f"{motif} — {correspondance}" if motif else correspondance.capitalize()
