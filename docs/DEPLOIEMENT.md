# Déploiement — préparation de l'hôte et chaîne automatique

Deux moitiés, séparées volontairement.

**Ce que fait la chaîne, à chaque poussée** : envoyer le code, installer les
dépendances, créer le schéma manquant, redémarrer les services, et **vérifier
que le point d'entrée répond** avant de se déclarer réussie.

**Ce qui se fait UNE FOIS, à la main, en root** : créer l'utilisateur, les
dossiers, poser les secrets, installer les unités du système et le mandataire
inverse. Ces gestes demandent des privilèges que la chaîne n'a pas — et ne doit
pas avoir. Ils sont ci-dessous.

## Pourquoi la chaîne existe

Le port 22 est bloqué depuis l'environnement de développement, et les API des
hébergeurs y sont refusées au CONNECT. **L'hôte ne peut être administré que
depuis un coureur d'intégration continue**, qui atteint le port 22 sans
difficulté. Ce n'est pas un confort d'automatisation : c'est le seul chemin.

## Ce que la chaîne ne peut pas faire, et pourquoi

L'utilisateur `deploy` écrit dans `/opt/falkye/code`, et peut redémarrer trois
unités nommées. Il **ne peut pas lire `/etc/falkye/falkye.env`**, où vivent le
jeton de la base distante et la clé d'envoi.

La création du schéma passe donc par une unité (`falkye-migration.service`) qui,
elle, tourne avec les secrets. Une chaîne compromise peut interrompre le
service; elle ne peut pas lire la base.

## Préparation de l'hôte — une seule fois, en root

```bash
# 1. L'utilisateur de service et les dossiers
adduser --system --group --home /opt/falkye falkye
mkdir -p /opt/falkye/code /var/lib/falkye
chown -R falkye:falkye /opt/falkye /var/lib/falkye
# Le dépôt d'archives de la chaîne — elle y écrit, l'unité d'import y lit.
# Séparé de /var/lib/falkye à dessein : `deploy` n'a rien à écrire là où vivent
# les bases.
install -d -o deploy -g falkye -m 0750 /opt/falkye/import

# 2. L'utilisateur de déploiement écrit le code, sans être le service
usermod -aG falkye deploy
chown -R deploy:falkye /opt/falkye/code
chmod 2775 /opt/falkye/code

# 3. Les secrets — voir .env.example pour la liste. Mode 600, root seul.
install -d -m 0750 /etc/falkye
${EDITOR:-nano} /etc/falkye/falkye.env
chmod 600 /etc/falkye/falkye.env

# 4. Les unités du système
cp deploiement/falkye-*.service deploiement/falkye-*.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now falkye-web.service
systemctl enable --now falkye-cycle.timer

# 5. La permission étroite de la chaîne
install -m 0440 deploiement/falkye-deploiement.sudoers /etc/sudoers.d/falkye-deploiement
visudo -c
```

**La base des miroirs a sa propre variable, et elle est obligatoire sur
l'hôte.** `/etc/falkye/falkye.env` doit porter :

```
FALKYE_MIROIR_DB_URL=sqlite:////var/lib/falkye/miroirs.sqlite3
```

Quatre barres obliques : le chemin est ABSOLU. Sans cette variable, le défaut
est le chemin relatif `./data/miroirs.sqlite3`, qui se résout dans le répertoire
de travail de l'unité — hors des chemins que `ProtectSystem=strict` autorise en
écriture. `outils/import_miroir_req.py` refuse alors de démarrer en nommant la
variable, plutôt que de laisser tomber une erreur de permissions qui enverrait
chercher au mauvais endroit. Voir docs/MIROIRS.md.

**Ajouter une unité plus tard demandera de refaire l'étape 4.** C'est assumé :
installer une unité est un geste de root, et donner ce pouvoir à la chaîne
annulerait la séparation que les étapes précédentes construisent.

## Le mandataire inverse

L'application sert en clair sur `127.0.0.1:8000`. Le certificat vit devant.
Avec Caddy, la configuration entière tient en trois lignes et le renouvellement
est automatique :

```
lien.falkye.com {
    reverse_proxy 127.0.0.1:8000
}
```

Deux conditions déjà vérifiées le 5 septembre 2026 : `lien.falkye.com` pointe
vers l'hôte, et **aucun enregistrement CAA** ne borne l'émission du certificat.
Les ports 80 et 443 doivent être joignables — le 80 sert à la validation.

## Récupérer le journal de repli

Le fichier `/var/lib/falkye/journal-repli.jsonl` ne s'écrit que si la base est
muette. Il vit sur un hôte injoignable depuis l'environnement de développement :
c'est un filet qui capture sans pouvoir livrer.

Le flux **« Récupérer le journal de repli »**, déclenché à la demande depuis
GitHub, le rapatrie et le publie comme artefact. Un fichier vide est le cas
NORMAL — il veut dire que la base a répondu à chaque écriture.

## Vérifier un déploiement

La chaîne le fait déjà : elle interroge `/sante` jusqu'à trente fois et échoue
si le point d'entrée ne répond pas. Un redémarrage accepté n'est pas un service
qui répond.

À la main, sur l'hôte :

```bash
systemctl status falkye-web.service
systemctl list-timers falkye-cycle.timer
curl -sf http://127.0.0.1:8000/sante
```

Et le journal d'exploitation, qui dit si le cycle a tourné :

```bash
sudo -u falkye /opt/falkye/venv/bin/falkye ...   # (lecture directe en base)
```

Trois lectures possibles, et c'est le point : **aucune ligne** veut dire que le
cycle n'a pas démarré, **un début sans fin** qu'il s'est interrompu, **un début
et une fin à zéro** qu'il a tourné sans rien à signaler.
