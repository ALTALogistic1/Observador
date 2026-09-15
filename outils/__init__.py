"""Les outils d'exploitation de FALKYE — **un paquet, et il y a une raison.**

**Le fait qui a créé ce fichier** *(2026-09-16, cas 26 pour la deuxième fois)*.
`outils/import_miroir_req.py` importait `outils.archives_req` pour lire la date de
l'archive. **Lancé à la main, il marchait; lancé par systemd, il mourait à la
première seconde** :

    ModuleNotFoundError: No module named 'outils'

**Pourquoi.** `python outils/import_miroir_req.py` met **`outils/` lui-même** en
tête de `sys.path`, jamais la racine du dépôt — *donc `import outils.x` ne trouve
rien.* `import falkye.x` marchait, lui, parce que `falkye` est **installé dans le
venv** et ne dépend pas du répertoire courant. **Deux familles d'imports dans le
même fichier, dont une seule survit à l'unité.**

**Le correctif est dans la FORME D'INVOCATION, pas dans un chemin à poser.**
`python -m outils.import_miroir_req` met le **répertoire courant** en tête de
`sys.path` — et `WorkingDirectory=/opt/falkye/code` le rend juste. *Aucun
`sys.path.insert` à recopier en tête de chaque script, aucun `PYTHONPATH` à tenir
à jour dans chaque unité : une règle, vérifiée par un test.*

⚠️ **La règle, et `tests/test_unites_systemd.py` la fait respecter** : *toute unité
qui lance un script de ce dépôt l'invoque par `-m`.* **Un `ExecStart` en
`python outils/x.py` fait rougir le test**, avec le motif écrit dedans.
"""
