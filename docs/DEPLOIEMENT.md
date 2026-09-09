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

> **⚠️ L'ordre du geste, appris le 7 septembre 2026.** La recopie en root lit
> `/opt/falkye/code/deploiement/`, que **le déploiement remplit**. Elle doit donc
> venir *après* que le flux Déploiement soit VERT, jamais dès qu'il est lancé.
>
> Fait dans le mauvais ordre, on recopie les unités de la version précédente. Et
> ça ne se voit pas : `systemctl daemon-reload` réussit, l'unité démarre, le
> cycle tourne — il perd simplement toutes les sources que la correction devait
> sauver. Cinq sur neuf, ce jour-là. **Vérifier plutôt que supposer :**
>
> ```bash
> systemctl cat falkye-cycle-sans-livraison.service | grep -i cache
> ```

### Temps 5 — charger le miroir, voir un cycle, PUIS activer le minuteur

Trois gestes, dans cet ordre, et le troisième dépend de ce que montre le second.

1. **Charger le miroir REQ** — flux **« Charger le miroir REQ »**, avec
   l'étiquette de la release portant `JeuDonnees.zip`. Sans lui, la résolution
   NEQ échoue et le cycle n'a rien à dire (voir `docs/MIROIRS.md`).

2. **Lancer un cycle à la main, sans livraison** — flux **« Lancer un cycle sans
   livraison »**. Il démarre `falkye-cycle-sans-livraison.service`, qui exécute
   `falkye cycle --sans-livraison` : réconciliation et détection réelles, aucun
   résumé généré ni envoyé.

   **Le flux lance et rend la main; il ne supervise pas.** Un travail sur coureur
   hébergé par GitHub est plafonné à six heures, et un premier passage dure plus
   que ça — celui du 7 septembre 2026 a été tué à 3 h sur la troisième source de
   neuf, alors qu'il travaillait encore. Un flux qui attendrait serait tué
   pendant que l'unité continue : un flux en échec à côté d'un cycle vivant, deux
   signaux contradictoires pour un seul fait. L'hôte possède l'exécution, bornée
   par `TimeoutStartSec` de l'unité.

   L'avancement se lit avec le flux **« État du cycle sans livraison »**, qui ne
   demande aucun privilège et se déclenche autant de fois qu'on veut. Le détail
   PAR SOURCE, lui, vit dans `SourceRunLog`, donc en base : le coureur n'a pas
   les identifiants pour la lire, et c'est délibéré.

   **Le premier passage n'est pas un cycle ordinaire.** Il amorce l'état de diff
   sur tout l'historique des sources; un cycle hebdomadaire ne verra ensuite que
   les lignes neuves. Régler le minuteur sur l'amorçage serait l'erreur
   symétrique de l'heure ronde.

3. **Le délai est réglé — reste à activer le minuteur.** `TimeoutStartSec` de
   `falkye-cycle.service` vaut **5 400 s**, dimensionné le 8 septembre 2026 sur
   une mesure du RÉGIME : un cycle hebdomadaire ordinaire prend **29 min 10 s**,
   8 sources sur 8 en succès, 396 Mo de pic. Marge de 3,1.

   Les deux valeurs précédentes ont chacune tué un cycle : 3 600 s (une heure
   ronde, aucune mesure) et 10 800 s (dimensionné sur l'amorçage). Régler sur
   l'amorçage était l'erreur symétrique de l'heure ronde — un minuteur
   hebdomadaire ne verra jamais que le régime.

   Puis :

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

## La base distante et les transactions longues — mesuré le 7 septembre 2026

**Une transaction qui porte une écriture non validée meurt en moins de dix
secondes d'inactivité.** Le message du serveur est explicite :

    interactive transaction was rolled back because the stream was idle
    for too long

| Transaction ouverte | Inactivité | Verdict |
|---|---|---|
| Lecture seule | 180 s | survit |
| Portant une écriture | 5 s | survit |
| Portant une écriture | **10 s** | **morte** |
| Portant une écriture | 20 s et au-delà | flux disparu (`stream not found`) |

**Ce que ça interdit.** Tenir une écriture non validée pendant quoi que ce soit
de lent — un téléchargement, une résolution contre le miroir, un appel
d'enrichissement. La première opération qui suit échoue, **y compris le
`rollback()` du gestionnaire d'erreur**, et l'exception emporte alors tout ce qui
l'entoure. C'est ce qui a tué le premier cycle réel sur l'hôte : une source est
tombée, son annulation a levé sur un flux mort, et huit sources saines n'ont
jamais été essayées.

**Ce qui est corrigé.** La ligne d'exécution d'une source est validée avant le
travail réseau, et `ingest_source` ne lève plus jamais : une connexion morte
coûte une source, pas le cycle (`tests/test_ingestion_resiliente.py`).

**La boucle de détection valide à chaque signal**, décision du 7 septembre 2026.
Un `flush()` y laissait une écriture ouverte pendant la résolution NEQ du signal
suivant — 0,32 s par appel de repli, sans borne sur le nombre d'appels.

*Ce que ça coûte* : un aller-retour facturé par signal neuf. Le run de référence
en a consommé 3,47 M sur les 10 M du forfait mensuel, et un cycle ordinaire en
écrit quelques centaines. Quelques milliers d'écritures contre une classe de
panne silencieuse est un bon échange, et le quota est à coût constant.

*Ce que ça change aussi, et qui est voulu* : une source qui tombe à mi-chemin
garde ce qu'elle a déjà trouvé. La déduplication par `source_ref` fait que la
reprise ramasse le reste sans doublon. Avant, l'annulation jetait tout.

**Règle générale à retenir.** Sur la base distante, ne jamais tenir une écriture
non validée pendant quoi que ce soit dont la durée n'est pas bornée. Ni un appel
réseau, ni une résolution contre le miroir, ni une boucle sur des milliers de
lignes.

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

Quatre lectures possibles, et c'est le point : **aucune ligne** veut dire que le
cycle n'a pas démarré, **un début sans fin** qu'il s'est interrompu, **une fin
portant « N source(s) en erreur »** qu'il a tourné mais n'a rien pu observer, et
**un début et une fin à zéro sans mention de source** qu'il a tourné sans rien à
signaler.

La troisième lecture manquait jusqu'au 7 septembre 2026 : une source en panne
écrivait bien son échec dans `SourceRunLog`, mais la ligne de fin annonçait
« 0 notification créée » — mot pour mot ce qu'annonce une semaine calme.

**Une panne partielle ne fait pas sortir l'unité en échec** : une source sur neuf
ne doit pas passer pour un cycle qui n'a pas tourné. Elle se dit, elle ne crie
pas. **Une panne totale, si** — quand toutes les sources tentées tombent, la
ligne porte « AUCUNE OBSERVATION » et l'unité sort en échec, parce que là c'est
bien le cycle qui n'a rien fait et que `systemctl list-units --failed` doit le
dire. Les sources sans connecteur (`a_developper`) ne comptent pas au
dénominateur : elles n'ont pas échoué, elles n'ont pas été tentées.

## Les états qu'on croit éteints — cinq occurrences, et la règle qui en sort

Le 8 septembre 2026, le minuteur du cycle a livré un vrai courriel à un vrai
destinataire pendant que tout le monde le croyait éteint :

```
2026-09-08 08:03:50 UTC  CYCLE_DEBUT  e6308aa
2026-09-08 08:31:44 UTC  CYCLE_FIN    1 profil(s), 0 notification(s), 1 résumé(s) envoyé(s)
```

`systemctl is-enabled` répondait `disabled`, et c'est ce qu'on avait vérifié.
Mais **`disabled` ne veut pas dire arrêté** : le lien symbolique d'activation
n'existait plus, et l'unité tournait quand même — `enable` gouverne le
DÉMARRAGE AU PROCHAIN AMORÇAGE, pas l'état courant. La seule lecture qui
répond à « est-ce que ça peut se déclencher maintenant » est `is-active`.

Trois mécanismes se sont enchaînés, chacun correct pris seul :

1. `OnCalendar=Tue *-*-* 08:00:00` s'évalue dans le fuseau LOCAL de l'hôte.
   L'hôte était en UTC, donc le créneau tombait à 4 h du matin à Montréal —
   pas l'heure « où la personne peut agir » que la charte demande.
2. `timedatectl set-timezone` fait recalculer les minuteurs de calendrier.
   Le recalcul a vu un créneau désormais passé.
3. `Persistent=true` rattrape un créneau manqué **immédiatement**. Il est là
   pour ne pas perdre une livraison parce que l'hôte était éteint; il a fait
   exactement ça.

Le fichier `/var/lib/systemd/timers/stamp-<unité>.timer` est la mémoire de ce
mécanisme. systemd l'écrit au DÉMARRAGE d'un minuteur persistant qui n'en a pas
— précisément pour qu'un minuteur neuf ne se déclenche pas d'un coup. Sa date
est donc une information : un horodatage d'il y a une minute garantit qu'aucun
rattrapage ne peut partir, puisque le prochain créneau calculé après lui est
forcément dans le futur. **Ne pas le supprimer** : c'est lui la garantie.

### Avant d'activer un minuteur, les quatre lectures

```bash
timedatectl                                    # Time zone: America/Toronto, pas UTC
systemctl is-active  falkye-cycle.timer        # la seule qui dit s'il peut partir
systemctl is-enabled falkye-cycle.timer        # ne dit QUE le prochain amorçage
stat /var/lib/systemd/timers/stamp-falkye-cycle.timer
```

### La règle

C'est la **cinquième** fois que ce projet rencontre un état qu'il croyait
éteint : la source qui tombe sans le dire, les cinq sources mortes sur le cache
lues comme une semaine calme, les deux lignes d'exécution restées `en_cours`,
l'index unique dont le planificateur croit qu'il rend une ligne, et ce
minuteur. À chaque fois, la même forme : **une valeur qu'on croit connaître
tient lieu de la valeur qu'on n'a pas lue.**

Un état d'exécution ne se déduit pas d'un état de configuration, ni d'un
souvenir de ce qu'on a fait. Il se lit. Et ce qui livre — un courriel, une
écriture en base, une facture — se lit AVANT le geste, pas après.

Ce qui a sauvé la trace, ici : le journal de repli. Le déclenchement de
14 h 17 UTC est tombé pendant le blocage du quota de lectures; la base ne
pouvait rien écrire, et les deux lignes — début, puis échec avec sa cause —
n'existent que dans `/var/lib/falkye/journal-repli.jsonl`. Sans lui, ce
déclenchement-là n'aurait laissé aucune trace nulle part.

## Le déploiement migre le schéma tout seul — sixième occurrence du motif

**Le fait, avant tout le reste.** Une fusion sur la branche principale déclenche
le déploiement, et le déploiement applique les migrations de schéma sur les DEUX
bases, sans que personne le demande. Il n'y a pas de geste manuel à faire après :
il est déjà fait quand on y pense.

```
fusion → push sur la branche principale
       → .github/workflows/deploiement.yml   (on: push: branches: [<principale>])
       → sudo systemctl start falkye-migration.service
           → falkye init-db                        # les TABLES manquantes (create_all)
           → outils/migration_colonnes.py --appliquer
                                                   # les COLONNES puis les INDEX manquants,
                                                   # base du produit ET base des miroirs
```

Mesuré le 2026-09-08 : le déploiement démarre **quatre secondes** après le
commit de fusion. Sur cinq fusions consécutives (#7 à #11), cinq déploiements,
cinq migrations.

### Il n'existe plus de fusion inoffensive

**Une demande de fusion qui ne change qu'un document déploie exactement comme
les autres.** Le déclencheur est `push` sur la branche principale : il ne
regarde pas ce que le commit contient. Un correctif de coquille dans un fichier
Markdown envoie le code, redémarre le service web, redémarre le minuteur du
cycle, et applique les migrations de schéma sur les deux bases.

Ce n'est pas une note d'exploitation, **c'est ce qui change la façon de
décider.** Tant qu'on croyait à des fusions sans conséquence, une PR de
documentation se fusionnait sans y penser — le raisonnement « c'est juste un
document » est faux ici, et il l'est depuis le premier jour où ce flux existe.

Concrètement : le passage à blanc de l'étape 1 ci-dessous vaut pour **toute**
fusion, y compris celles qui ne touchent aucun code.

### Pourquoi c'est consigné ici plutôt que laissé dans l'unité

Le mécanisme était déjà écrit dans `deploiement/falkye-migration.service` et dans
le flux de déploiement. Il y était depuis le 2026-09-06. Et pendant une journée
entière, ni l'opérateur ni l'assistant ne l'avaient en tête : on a cru pendant
cinq passages qu'une migration attendait un geste manuel, alors qu'elle était
faite avant qu'on en parle, et on a cherché l'auteur humain d'une écriture de
schéma que la chaîne avait posée.

**Un mécanisme documenté à un seul endroit est un mécanisme qu'on redécouvre.**
C'est la sixième fois que ce projet rencontre un dispositif actif qu'il croyait
au repos — après le minuteur armé depuis l'installation, l'index unique qui
trompait le planificateur, et les quatre occurrences déjà listées plus haut.

### L'ordre qu'on s'était donné était inapplicable

On disait : *fusion, déploiement, PUIS migration sur l'hôte avec `is-active`
revérifié juste avant.* Il n'existe aucune fenêtre entre le déploiement et la
migration — **le déploiement EST la migration**. Le garde-fou qu'on croyait
poser avant arrivait systématiquement après coup.

**La vraie séquence sûre, le point de contrôle déplacé avant la fusion :**

```bash
# 1. AVANT de fusionner — c'est le dernier moment où on décide encore.
systemctl is-active falkye-cycle.timer      # doit répondre inactive
systemctl is-active falkye-cycle.service    # aucun cycle en vol
python outils/migration_colonnes.py         # ce que la fusion VA appliquer, en lecture seule

# 2. La fusion. À partir d'ici tout s'enchaîne, sans point d'arrêt.

# 3. APRÈS — vérifier, pas supposer.
python outils/migration_colonnes.py         # « aucune colonne ni index manquant »
```

`is-active` se lit donc **avant la fusion**, jamais entre le déploiement et la
migration : cet entre-deux n'existe pas. Et le passage à blanc de l'étape 1 est
la seule occasion de voir ce que la chaîne va écrire avant qu'elle l'écrive.

### Ce que la chaîne ne fait toujours pas

Elle **ajoute** : tables, colonnes, index. Elle ne renomme rien, ne supprime
rien, ne change aucun type — ces gestes perdent de la donnée et exigent une
décision humaine. Une migration destructive reste un passage manuel, et celle-là
a besoin de la fenêtre de restauration, contrairement aux migrations additives
dont le retour arrière est `DROP INDEX` puis `DROP COLUMN`.

### Pourquoi la vérification de fusion ne parle pas à la base de production

Le passage à blanc de l'étape 1 répond en fait à **deux questions**, et les
confondre a coûté une journée :

| | ce qu'il faut pour y répondre |
|---|---|
| **(1)** Qu'est-ce que **cette fusion** ajoutera au schéma ? | rien — les modèles de deux révisions suffisent |
| **(2)** Qu'est-ce qui manque **à la production** ? | les identifiants de la base durable |

Seule la **(1)** se pose au moment de fusionner, et elle est gratuite : c'est
`.github/workflows/schema-fusion.yml`, qui compare les modèles de la demande à
ceux de sa base et affiche le résultat dans la demande elle-même.

**La (2) est écartée, et ce refus est une décision, pas un oubli.** Y répondre
depuis un flux demanderait de mettre `FALKYE_DB_URL` et `FALKYE_DB_AUTH_TOKEN`
dans les secrets du dépôt. La chaîne n'a aujourd'hui que quatre secrets — clé
SSH, empreinte de l'hôte, hôte, utilisateur — et **aucun identifiant de base**.
C'est exactement pourquoi la migration passe par une unité root plutôt que par
un appel direct : **une chaîne compromise peut redémarrer le service, jamais
lire la base.** Ajouter ces deux secrets défait cette propriété, qui est l'une
des deux raisons d'être de l'architecture des secrets du chantier 29 — l'autre
étant qu'une restauration change l'adresse et le jeton, et qu'on doit pouvoir
basculer sans redéployer, au pire moment possible.

**On n'échange pas cette propriété contre une commodité de vérification.** Si
quelqu'un reprend cette question dans six mois, c'est cette phrase qui répond.

La (2) reste donc une question d'exploitation, et le déploiement y répond déjà
après coup, par `migration_colonnes.py` sur l'hôte.

**Deux autres chemins, écartés eux aussi.**

*Une unité de vérification sur l'hôte* préserverait les identifiants, mais
`migration_colonnes.py` compare les modèles **du code depuis lequel il tourne** :
sur l'hôte, c'est le code DÉPLOYÉ. Pour une demande qui ajoute une colonne, elle
afficherait « rien à faire » — précisément dans le cas où elle devait servir. La
corriger demanderait d'envoyer du code non fusionné sur l'hôte à chaque demande.

*Un instantané de schéma* pris à chaque déploiement répondrait à la (2) sans
identifiants. Gardé en réserve, pas construit — et s'il revient, il porte sa
révision et sa date, et la vérification **échoue** plutôt que de passer quand
l'instantané est plus vieux que la tête de branche. Un instantané sans
provenance est une vérité périmée, et on en a déjà eu une : la table de prix du
coût de lecture, vraie le matin et fausse l'après-midi.

*Une vérification qui exigerait la sortie du passage à blanc dans le corps de la
demande* vérifierait qu'un texte **existe**, pas qu'il est **vrai**.
