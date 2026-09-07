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

⚠️ **L'ordre compte, et il n'est pas intuitif.** Les unités systemd pointent vers
`/opt/falkye/venv`, que la chaîne crée; la chaîne, elle, démarre une unité à la
fin. Ni l'un ni l'autre ne peut être premier. La séquence ci-dessous casse ce
nœud en quatre temps, dont un déploiement **volontairement incomplet**.

### Temps 1 — root, sur l'hôte

```bash
# 1.1 Les paquets. `python3-venv` n'est pas installé par défaut sur une image
#     Debian minimale; `rsync` et `curl` sont utilisés par la chaîne elle-même.
apt-get update
apt-get install -y python3-venv rsync curl

# 1.2 L'utilisateur de service. `--system` : pas de mot de passe, pas de
#     connexion interactive possible. `--no-create-home` puis mkdir explicite,
#     pour que les permissions ne dépendent pas des défauts de l'outil.
adduser --system --group --home /opt/falkye --no-create-home falkye

# 1.3 Les dossiers
mkdir -p /opt/falkye/code /opt/falkye/import /var/lib/falkye

#     /opt/falkye : la chaîne y crée le venv et version.env, donc le groupe
#     `falkye` doit pouvoir y écrire. Le bit setgid (2) fait hériter le groupe
#     aux fichiers créés dedans — sans lui, le venv appartiendrait au groupe de
#     `deploy` et le service ne pourrait pas l'exécuter.
chown falkye:falkye /opt/falkye
chmod 2775 /opt/falkye

#     Le code : écrit par la chaîne, lu par le service.
chown deploy:falkye /opt/falkye/code
chmod 2775 /opt/falkye/code

#     Le dépôt d'archives : la chaîne y écrit, l'unité d'import y lit. Séparé de
#     /var/lib/falkye à dessein — `deploy` n'a rien à écrire là où vivent les
#     bases.
chown deploy:falkye /opt/falkye/import
chmod 2750 /opt/falkye/import

#     Les bases et le journal de repli : le service SEUL y écrit.
chown falkye:falkye /var/lib/falkye
chmod 0750 /var/lib/falkye

# 1.4 Les deux appartenances de groupe de `deploy`
#     `falkye` : pour écrire dans /opt/falkye et /opt/falkye/code.
#     `systemd-journal` : pour LIRE le journal des unités — la chaîne rapporte
#     le résultat d'un import de 33 minutes, et sans ce groupe elle ne verrait
#     rien. Lecture seule, et rien d'autre que le journal.
usermod -aG falkye,systemd-journal deploy

# 1.5 La variable des miroirs dans le fichier d'environnement (qui existe déjà)
#     QUATRE barres obliques : le chemin est absolu.
printf 'FALKYE_MIROIR_DB_URL=sqlite:////var/lib/falkye/miroirs.sqlite3\n' \
    >> /etc/falkye/falkye.env
chmod 600 /etc/falkye/falkye.env
```

**Vérifier avant de continuer** — chaque commande doit répondre :

```bash
id falkye        # uid=… (falkye) gid=… (falkye) groups=… (falkye)
id deploy        # doit contenir (falkye) ET (systemd-journal)
ls -ld /opt/falkye /opt/falkye/code /opt/falkye/import /var/lib/falkye
                 # drwxrwsr-x falkye falkye   /opt/falkye
                 # drwxrwsr-x deploy falkye   /opt/falkye/code
                 # drwxr-s--- deploy falkye   /opt/falkye/import
                 # drwxr-x---  falkye falkye   /var/lib/falkye
grep MIROIR /etc/falkye/falkye.env    # la ligne, avec quatre barres
python3 --version                      # 3.11 ou plus
```

Le `s` dans `drwxrwsr-x` est le bit setgid : il est attendu, pas une anomalie.

### Temps 2 — un premier déploiement, qui ÉCHOUERA à la dernière étape

Déclencher le flux **Déploiement** depuis GitHub. Il va envoyer le code, créer
le venv et installer les dépendances — puis échouer sur
`sudo systemctl start falkye-migration.service`, parce que ni l'unité ni la
permission n'existent encore.

**Cet échec est attendu et il est le but de ce temps :** amener les fichiers
d'unité sur l'hôte, où le temps 3 va les installer. Ce qui compte est que les
étapes *avant* celle-là aient réussi :

```bash
ls /opt/falkye/venv/bin/falkye        # doit exister
ls /opt/falkye/code/deploiement/      # les .service et le .timer
```

### Temps 3 — root, installer les unités et la permission

```bash
cd /opt/falkye/code

# 3.1 Les unités du système
cp deploiement/falkye-*.service deploiement/falkye-*.timer /etc/systemd/system/
systemctl daemon-reload

# 3.2 La permission étroite de la chaîne — `visudo -c` VALIDE le fichier.
#     Une erreur de syntaxe dans /etc/sudoers.d peut rendre sudo inutilisable
#     sur toute la machine : ne pas sauter cette vérification.
install -m 0440 deploiement/falkye-deploiement.sudoers /etc/sudoers.d/falkye-deploiement
visudo -c

# 3.3 Créer le schéma, puis démarrer
systemctl start falkye-migration.service
systemctl enable --now falkye-web.service
```

**Le minuteur n'est PAS activé ici, et c'est délibéré.** Sans miroir REQ chargé,
un cycle ne résout aucun NEQ, ne produit aucune notification et livre un résumé
vide — la seule chose qu'il enverrait est un courriel qui décrédibilise le
produit. L'activation vient au temps 5, après qu'un cycle ait été vu tourner.

**Vérifier :**

```bash
systemctl status falkye-web.service      # active (running)
curl -sf http://127.0.0.1:8000/sante     # ok
sudo -u deploy sudo -n /usr/bin/systemctl status falkye-web.service >/dev/null \
    && echo "permission de la chaîne : ok"
```

### Temps 4 — relancer le déploiement

Le même flux, qui doit cette fois aller jusqu'au bout et confirmer que le point
d'entrée répond. **C'est ce passage-là qui prouve la chaîne**, pas le premier.

**Ajouter une unité plus tard demandera de refaire le temps 3.** C'est assumé :
installer une unité est un geste de root, et donner ce pouvoir à la chaîne
annulerait la séparation que le reste construit.

### Temps 5 — charger le miroir, voir un cycle, PUIS activer le minuteur

Trois gestes, dans cet ordre, et le troisième dépend de ce que montre le second.

1. **Charger le miroir REQ** — flux **« Charger le miroir REQ »**, avec
   l'étiquette de la release portant `JeuDonnees.zip`. Sans lui, la résolution
   NEQ échoue et le cycle n'a rien à dire (voir `docs/MIROIRS.md`).

2. **Lancer un cycle à la main, sans livraison** — flux **« Lancer un cycle sans
   livraison »**. Il démarre `falkye-cycle-sans-livraison.service`, qui exécute
   `falkye cycle --sans-livraison` : réconciliation et détection réelles, aucun
   résumé généré ni envoyé. C'est ce passage qui donne la **durée réelle** d'un
   cycle sur l'hôte.

3. **Régler le délai, puis activer le minuteur** — `TimeoutStartSec` de
   `falkye-cycle.service` vaut 3 600 s, un chiffre posé avant toute mesure. Le
   corriger à partir de la durée observée, puis :

   ```bash
   systemctl daemon-reload                    # si le délai a changé
   systemctl enable --now falkye-cycle.timer
   systemctl list-timers falkye-cycle.timer   # prochain mardi 8 h
   ```

**Pourquoi le cycle d'observation ne livre pas.** Deux raisons qui se cumulent :
le réglage de désabonnement du flux de diffusion n'est pas débloqué chez le
fournisseur (rien ne doit partir), et un premier cycle sert à voir ce que la
détection produit avant qu'un destinataire le reçoive. La coupure est dans le
code, avant la génération des résumés, et trois tests la verrouillent
(`tests/test_cycle.py`). L'unité qui livre, `falkye-cycle.service`, n'est pas
dans le fichier de sudoers : la chaîne de déploiement ne peut pas la démarrer.

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
