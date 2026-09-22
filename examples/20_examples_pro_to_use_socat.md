# 20 exemples professionnels, approfondis et réellement utiles avec `socat`

> **Compatibilité OS**
> `socat` est natif sur **Linux** et **macOS**. Sur **Windows 11**, le chemin le plus fiable est **WSL2** (Ubuntu/Debian).
> Toutes les commandes fonctionnent telles quelles en **Linux/macOS** et en **Windows 11 via WSL2**.
> Alternative Windows : MSYS2/Cygwin, mais certains exemples `OPENSSL:` / TTY peuvent varier.

## Installation rapide

- **Linux (Debian/Ubuntu)** : `sudo apt-get install socat`
- **Linux (Fedora/RHEL)** : `sudo dnf install socat`
- **macOS (Homebrew)** : `brew install socat`
- **Windows 11 (WSL2 Ubuntu)** :

  ```bash
  sudo apt-get update && sudo apt-get install socat
  ```

  Accès fichiers Windows depuis WSL : `C:\` → `/mnt/c/`

---

## 1) Relais TCP "production" : timeouts, keepalive, ACL locale et logs persistants

**Objectif :** exposer un port local et relayer vers un service distant avec des garde-fous (timeout, keepalive, filtrage IP) et une journalisation exploitable.

```bash
socat -d -d -lf ./socat_relay_8080.log \
  TCP4-LISTEN:8080,bind=127.0.0.1,reuseaddr,fork,backlog=128,\
keepalive,nodelay,range=127.0.0.1/32 \
  TCP4:example.com:80,connect-timeout=5
```

**Explication :**

| Option | Rôle |
| --- | --- |
| `bind=127.0.0.1` | Écoute uniquement en local (pas d'exposition accidentelle) |
| `range=127.0.0.1/32` | ACL réseau intégrée : seul localhost peut se connecter |
| `fork` | Un processus fils par connexion entrante |
| `keepalive,nodelay` | Sockets robustes : détection d'échec + latence réduite |
| `connect-timeout=5` | Évite de "pendre" si le backend est indisponible |
| `-lf ./socat_relay_8080.log` | Persiste les logs dans un fichier exploitable |

**Usage pratique :**
Remplacez `example.com:80` par une IP ou un service interne. Ajoutez un firewall OS en complément plutôt que d'exposer `0.0.0.0` sans contrôle.

---

## 2) Basculement automatique "Blue/Green" : failover entre deux backends

**Objectif :** assurer la continuité de service en basculant automatiquement sur un backend de secours si le backend principal est indisponible.

```bash
socat -d -d -ly -lf socat_failover.log \
  TCP4-LISTEN:9000,bind=127.0.0.1,reuseaddr,fork \
  SYSTEM:'(socat - TCP4:10.0.0.11:9000,connect-timeout=1 \
    || socat - TCP4:10.0.0.12:9000,connect-timeout=1)'
```

**Explication :**

- `SYSTEM:` exécute un sous-shell pour chaque connexion entrante.
- Le shell tente d'abord le **backend A** (`10.0.0.11`) ; en cas d'échec (timeout ou refus), il bascule immédiatement sur le **backend B** (`10.0.0.12`).
- Le basculement est **par connexion**, pas en cours de session.

**Usage pratique :**
Tes clients pointent toujours sur `127.0.0.1:9000`. Tu assures la continuité pendant une maintenance ou un déploiement Blue/Green sans reconfigurer les clients.

> **Note :** c'est un failover par connexion, pas un load-balancer. Simple et efficace.

---

## 3) Transfert de répertoire propre : flux `tar` + contrôle d'intégrité SHA-256

**Objectif :** transférer un dossier complet avec permissions et vérifier l'intégrité, sans bricolage fichier par fichier.

### Côté réception — démarrer en premier

```bash
mkdir -p ./restore
socat -d -d TCP4-LISTEN:8888,reuseaddr - \
  | tee archive.tgz \
  | sha256sum > archive.tgz.sha256
```

### Côté envoi — lancer ensuite

```bash
tar -czf - mon_dossier/ \
  | socat -d -d - TCP4:IP_RECEPTEUR:8888,connect-timeout=5
```

### Vérifier l'intégrité après transfert

```bash
sha256sum archive.tgz
cat archive.tgz.sha256
```

**Explication :**

- `tar -czf - .` produit un flux `tar.gz` sur stdout, envoyé directement dans `socat`.
- Côté réception, `tee` écrit le fichier sur disque **et** calcule simultanément le hash SHA-256.
- Les permissions, sous-répertoires et liens symboliques sont préservés par `tar`.

> Pour chiffrer le transport, combinez avec l'exemple **8** (TLS).

---

## 4) Accéder à un service remote "localhost-only" via SSH + `socat` (sans `nc`)

**Objectif :** atteindre un service distant qui n'écoute que sur `127.0.0.1` (base de données, admin UI, etc.) en exposant un port local.

```bash
socat TCP4-LISTEN:15432,reuseaddr,fork \
  EXEC:'ssh -o ExitOnForwardFailure=yes user@serveur_distant -W 127.0.0.1:5432'
```

**Explication :**

- `ssh -W host:port` demande à SSH de relayer stdin/stdout vers `host:port` **sur la machine distante**.
- `socat` transforme une connexion TCP locale en flux stdin/stdout pour SSH.
- Très pratique quand on veut un pont sans configuration SSH persistante (`~/.ssh/config`).

**Windows 11 :**
Fonctionne via WSL2 avec le SSH Linux. Peut fonctionner avec OpenSSH Windows natif si `socat` est côté POSIX (WSL/MSYS2).

---

## 5) Collecteur UDP avec horodatage : recevoir des datagrammes et les archiver

**Objectif :** collecter des messages UDP (logs applicatifs, métriques, événements) et les archiver avec un timestamp ISO-8601.

```bash
socat -u UDP4-RECV:5514,reuseaddr \
  SYSTEM:'while IFS= read -r line; do \
    printf "%s %s\n" "$(date -Is)" "$line"; \
  done >> ./udp_events.log'
```

**Explication :**

| Option | Rôle |
| --- | --- |
| `-u` | Mode unidirectionnel (UDP → fichier), simple et robuste |
| `UDP4-RECV:5514` | Reçoit les datagrammes UDP sur le port 5514 |
| `SYSTEM:` | Ajoute un timestamp ISO-8601 et append dans le fichier log |

**Tester en local :**

```bash
echo "test event" | socat - UDP4-SENDTO:127.0.0.1:5514
```

> UDP ne garantit ni l'ordre ni la livraison. Pour des logs critiques, préférez TCP/TLS (exemple 8).

---

## 6) Proxy de debug TCP avec dump hexadécimal : analyser un protocole inconnu

**Objectif :** intercaler un proxy transparent entre un client et un serveur pour analyser ce qui transite réellement sur le fil.

```bash
socat -v -x -d -d -lf ./wire_5000.log \
  TCP4-LISTEN:5000,bind=127.0.0.1,reuseaddr,fork \
  TCP4:serveur_backend:5001,connect-timeout=5
```

**Lire les logs en temps réel :**

```bash
tail -f ./wire_5000.log
```

**Explication :**

| Option | Rôle |
| --- | --- |
| `-v` | Log les données transférées en texte lisible |
| `-x` | Dump hexadécimal (indispensable pour les protocoles binaires) |
| `-lf ./wire_5000.log` | Persiste tous les échanges dans un fichier daté |

**Usage pratique :**
Lance le backend sur `:5001`, pointe le client vers `:5000` : tu obtiens un sniffer applicatif sans Wireshark. Utile pour analyser un framing, repérer des `\r\n` manquants, des timeouts, ou tout comportement inattendu.

> **Avertissement :** réservé à tes propres environnements de développement et de test. Intercepter du trafic sans autorisation est illégal.

---

## 7) Pont TCP ↔ Socket Unix : exposer un service IPC local en TCP

**Objectif :** transformer un service qui écoute sur un **Unix Domain Socket** (UDS) en port TCP local, pour des outils qui ne savent parler qu'en TCP.

```bash
socat TCP4-LISTEN:15432,bind=127.0.0.1,reuseaddr,fork \
  UNIX-CONNECT:/var/run/postgresql/.s.PGSQL.5432
```

**Explication :**

- `UNIX-CONNECT:` se connecte directement au fichier socket Unix.
- `bind=127.0.0.1` : exposition **uniquement locale** — bonne pratique systématique.
- Applicable à tout service utilisant des UDS : PostgreSQL, Docker daemon, Redis, etc.

**Usage pratique :**
Un SDK ou un conteneur qui ne parle qu'en TCP peut désormais atteindre PostgreSQL même si celui-ci n'est disponible que via socket Unix. Très utile en CI/CD ou en environnement containerisé.

**Windows 11 :**
Via WSL2 uniquement. Les UDS Windows natifs ont un comportement différent.

---

## 8) Terminaison TLS devant un service HTTP interne : HTTPS sans nginx

**Objectif :** chiffrer une application qui ne supporte pas TLS en terminant TLS avec `socat`, puis en relayant en local.

### Étape 1 — Générer un certificat de test

```bash
openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
  -keyout server.key -out server.crt -subj "/CN=localhost"
```

### Étape 2 — Lancer la terminaison TLS

```bash
socat -d -d -ly -lf socat_tls.log \
  OPENSSL-LISTEN:8443,cert=server.crt,key=server.key,reuseaddr,fork,verify=0 \
  TCP4:127.0.0.1:8080
```

### Étape 3 — Tester

```bash
curl -vk https://localhost:8443/
```

**Explication :**

| Option | Rôle |
| --- | --- |
| `OPENSSL-LISTEN:8443` | Écoute et négocie TLS sur le port 8443 |
| `cert/key` | Certificat et clé privée du serveur |
| `verify=0` | Pas de vérification du certificat client (OK en dev) |
| `TCP4:127.0.0.1:8080` | Relaie le trafic déchiffré vers le service HTTP interne |

> En production, remplacez `verify=0` par `cafile=ca.crt` et `verify=1` pour une vérification stricte.

---

## 9) Client mTLS : accéder localement à un service exigeant un certificat client

**Objectif :** brancher un outil local (legacy, script, SDK) sur une API exigeant du **mTLS**, sans modifier l'application elle-même.

```bash
socat -d -d -ly -lf socat_mtls.log \
  TCP4-LISTEN:9443,bind=127.0.0.1,reuseaddr,fork \
  OPENSSL:api.exemple-interne.local:443,\
cert=client.crt,key=client.key,cafile=ca.crt,\
verify=1,servername=api.exemple-interne.local
```

**Explication :**

- Ton application locale parle à `127.0.0.1:9443` en TCP simple.
- `socat` prend en charge la négociation TLS sortante en présentant `client.crt` et `client.key`.
- `cafile` + `verify=1` : vérifie rigoureusement le certificat du serveur.
- `servername=` : active le **SNI** — obligatoire sur les services TLS modernes.

**Usage pratique :**
Évite d'embarquer la logique mTLS dans chaque outil ou script. `socat` devient le **proxy de certificats** unique et centralisé.

---

## 10) Pont série ↔ TCP : accéder à un équipement série à distance

**Objectif :** rendre un équipement série (automate, capteur, console réseau) accessible à distance via TCP.

```bash
socat TCP4-LISTEN:2001,reuseaddr,fork \
  FILE:/dev/ttyUSB0,raw,b115200,cs8,parenb=0,cstopb=0,echo=0,crtscts
```

**Se connecter depuis une machine distante :**

```bash
socat - TCP4:IP_SERVEUR_SERIE:2001
```

**Explication :**

| Option | Rôle |
| --- | --- |
| `raw` | Désactive les transformations de ligne du TTY |
| `echo=0` | Supprime l'écho parasite |
| `b115200` | Vitesse en bauds (adaptez à votre matériel) |
| `crtscts` | Contrôle de flux matériel RTS/CTS |

**Windows 11 :**
Le plus fiable : WSL2 + passage USB via `usbipd-win` pour faire apparaître le device en `/dev/ttyUSB0`. Alternative : MSYS2 avec `/dev/ttyS*`, mais le comportement est plus variable.

---

## 11) Endpoint de diagnostic HTTP : healthcheck sans serveur web

**Objectif :** fournir un healthcheck applicatif dynamique (hostname, date) sans installer nginx, Python ou Node.js.

```bash
socat -d -d \
  TCP4-LISTEN:9100,bind=127.0.0.1,reuseaddr,fork \
  EXEC:'/bin/sh -c \
    "printf \"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n\"; \
     printf \"{\\\"host\\\":\\\"%s\\\",\\\"time\\\":\\\"%s\\\"}\\n\" \
     \"$(hostname)\" \"$(date -Iseconds)\""'
```

**Tester l'endpoint :**

```bash
curl -s http://127.0.0.1:9100/
# {"host":"mon-serveur","time":"2026-02-24T10:30:00+01:00"}
```

**Explication :**

- `EXEC:` exécute un sous-shell pour chaque connexion et renvoie sa sortie standard au client TCP.
- Le shell construit une réponse HTTP valide (statut 200 + JSON) à la volée.
- La réponse est **dynamique** : hostname et timestamp sont recalculés à chaque appel.

**Usage pratique :**
Probes Kubernetes, checks de supervision Nagios/Zabbix, ou simple vérification de vie d'un hôte depuis un script.

> **Sécurité :** ne jamais exposer un `EXEC:` sur le réseau. `bind=127.0.0.1` est impératif ici.

---

## 12) Mini service TCP orienté ops : état machine en texte avec timeout d'inactivité

**Objectif :** fournir un endpoint TCP léger renvoyant l'état de la machine (hostname, date, uptime, charge), avec coupure automatique en cas d'inactivité.

```bash
socat -T 15 TCP4-LISTEN:9001,bind=127.0.0.1,reuseaddr,fork \
  SYSTEM:'printf "host=%s\ndate=%s\nuptime=%s\nload=%s\n" \
    "$(hostname)" \
    "$(date -Is)" \
    "$(uptime | tr -s " ")" \
    "$(uptime | awk -F\"load averages?: \" \"{print \$2}\")"'
```

**Tester :**

```bash
socat - TCP4:127.0.0.1:9001
# host=mon-serveur
# date=2026-02-24T10:30:00+01:00
# uptime= 10:30:00 up 5 days, ...
# load=0.42, 0.38, 0.35
```

**Explication :**

- `-T 15` : timeout d'inactivité de 15 secondes — évite les connexions zombies.
- `SYSTEM:` compose la réponse via le shell.

> Ce pattern est complémentaire de l'exemple 11 (HTTP) : ici la réponse est en texte brut, adapté aux sondes TCP pures ou aux scripts `socat`/`nc`.

---

## 13) Encapsulation UDP dans TCP : traverser des réseaux hostiles

**Objectif :** transporter un flux UDP (syslog, télémétrie, protocole custom) via un lien où seul TCP est autorisé ou fiable.

### Côté A — Entrée UDP, sortie TCP

```bash
socat -d -d -u \
  UDP4-RECVFROM:6000,reuseaddr,fork \
  TCP4:IP_DU_SITE_B:7000
```

### Côté B — Entrée TCP, sortie UDP

```bash
socat -d -d -u \
  TCP4-LISTEN:7000,reuseaddr,fork \
  UDP4-SENDTO:127.0.0.1:6000
```

**Explication :**

| Option | Rôle |
| --- | --- |
| `-u` | Mode unidirectionnel (adapté aux flux UDP non bidirectionnels) |
| `UDP4-RECVFROM` | Reçoit les datagrammes UDP entrants |
| `TCP4:IP_DU_SITE_B:7000` | Encapsule le flux dans un tunnel TCP vers le site B |
| `UDP4-SENDTO` | Réémet en UDP local après réception TCP |

> Cette encapsulation ne recrée pas les propriétés natives d'UDP (ordre, pertes). Elle est utile pour le **contournement réseau**, pas pour la performance brute.

---

## 14) Redirection UDP vers DNS : tester un résolveur alternatif sans reconfiguration système

**Objectif :** rediriger le trafic DNS local vers un résolveur alternatif (ex. `9.9.9.9`) sans modifier `/etc/resolv.conf` ni la config réseau.

```bash
socat -d -d -ly -lf socat_dns.log \
  UDP4-LISTEN:5353,reuseaddr,fork \
  UDP4:9.9.9.9:53
```

**Tester :**

```bash
dig @127.0.0.1 -p 5353 example.com
```

**Explication :**

- `UDP4-LISTEN:5353` : écoute localement sur le port 5353 (non privilégié, contrairement au 53).
- `UDP4:9.9.9.9:53` : relaie vers Quad9 sur le port DNS standard.
- Utile pour tester un résolveur DNS sans toucher à la configuration système ou pour logguer les requêtes DNS d'une application.

---

## 15) Test "sérieux" de débit TCP : sink serveur + émission contrôlée

**Objectif :** mesurer rapidement un débit TCP brut sans dépendre d'outils spécialisés comme `iperf3`.

### Côté serveur — "trou noir"

```bash
socat -d -d -u TCP4-LISTEN:9000,reuseaddr,fork /dev/null
```

### Côté client — envoi 512 Mio + mesure

```bash
time dd if=/dev/zero bs=1M count=512 2>/dev/null \
  | socat -d -d -u - TCP4:IP_SERVEUR:9000,connect-timeout=5
```

**Explication :**

- Serveur : tout ce qui arrive est redirigé vers `/dev/null` — pas d'I/O disque, mesure réseau pure.
- Client : `dd` génère un flux constant de zéros ; `time` mesure la durée totale.
- `-u` : unidirectionnel, pas de retour de données — test de débit upload pur.

**Usage pratique :**
Valider rapidement le débit réel d'un VPN, d'un tunnel WireGuard, ou comparer deux chemins réseau. Deux machines, deux commandes, aucune dépendance.

> **macOS :** si `bs=1M` échoue, utilisez `bs=1048576`.

---

## 16) Connectivité applicative avec timeout strict : détecter les connexions qui "pendent"

**Objectif :** tester la connectivité vers un service avec un timeout d'inactivité précis, pour identifier les flux qui s'établissent mais ne répondent jamais.

```bash
socat -d -d -T 2 TCP4:serveur.exemple.local:443 -
```

**Combiner avec une boucle de surveillance :**

```bash
while true; do
  echo "--- $(date -Is) ---"
  socat -T 2 TCP4:serveur.exemple.local:443 - <<< "HEAD / HTTP/1.0\r\n\r\n"
  sleep 30
done
```

**Explication :**

- `-T 2` : timeout d'inactivité I/O de 2 secondes.
- Les logs `-d -d` indiquent précisément si la connexion TCP s'est établie et à quelle étape elle échoue.
- La boucle permet une **supervision continue** sans outil dédié.

**Usage pratique :**
Diagnostiquer un firewall qui accepte le TCP (`SYN/ACK`) mais ne laisse pas passer les données applicatives — un cas classique difficile à détecter avec un simple `ping`.

---

## 17) Exposer temporairement un fichier unique en HTTP (one-shot server)

**Objectif :** partager un fichier ponctuellement sur le réseau local via HTTP, sans serveur web, avec arrêt automatique après le premier téléchargement.

```bash
FILE="mon_fichier.tar.gz"
FILENAME=$(basename "$FILE")
FILESIZE=$(stat -c%s "$FILE" 2>/dev/null || stat -f%z "$FILE")

socat -d -d TCP4-LISTEN:8000,reuseaddr \
  SYSTEM:"printf 'HTTP/1.1 200 OK\r\nContent-Disposition: attachment; filename=\"${FILENAME}\"\r\nContent-Length: ${FILESIZE}\r\nContent-Type: application/octet-stream\r\n\r\n'; cat '${FILE}'"
```

**Télécharger depuis une autre machine :**

```bash
curl -O http://IP_SERVEUR:8000/
```

**Explication :**

- Pas de `fork` : le serveur accepte **une seule connexion** puis s'arrête automatiquement.
- `Content-Length` et `Content-Disposition` garantissent un téléchargement propre avec `curl` ou un navigateur.
- `stat -c%s` (Linux) / `stat -f%z` (macOS) assure la compatibilité cross-platform.

> **Sécurité :** usage ponctuel sur réseau de confiance uniquement. Pas de chiffrement, pas d'authentification.

---

## 18) Multiplexeur de logs : diffuser un flux de logs vers plusieurs destinations simultanées

**Objectif :** envoyer un flux de logs (stdout d'une application) vers plusieurs destinations en parallèle : fichier local, service distant, et console.

```bash
mon_application | \
  socat -u - \
  SYSTEM:'tee ./local.log | socat -u - TCP4:logserver.exemple.local:5000'
```

**Variante avec `socat` seul (fichier + réseau) :**

```bash
socat -u - \
  SYSTEM:'tee /dev/stderr | socat -u - TCP4:logserver.exemple.local:5000' \
  < <(mon_application)
```

**Explication :**

- `tee` duplique le flux : une copie va dans `local.log`, l'autre continue vers le `socat` interne.
- Le `socat` interne envoie le flux vers un serveur de logs distant en TCP.
- `-u` : mode unidirectionnel pour chaque étape.

**Usage pratique :**
Observer les logs en temps réel sur la console **et** les envoyer simultanément vers un SIEM, un agrégateur de logs ou un fichier d'audit, sans modifier l'application source.

---

## 19) Tunnel inverse : exposer un service local derrière NAT via une machine "relais"

**Objectif :** rendre accessible un service local (derrière NAT/firewall) depuis l'extérieur, via une machine relais publique accessible en SSH.

### Sur la machine relais publique — démarrer en premier

```bash
socat TCP4-LISTEN:8080,reuseaddr,fork TCP4:127.0.0.1:9090
```

### Sur la machine locale (derrière NAT) — établir le tunnel

```bash
ssh -R 9090:127.0.0.1:3000 user@machine_relais_publique \
  "socat TCP4-LISTEN:9090,reuseaddr,fork TCP4:127.0.0.1:3000"
```

**Variante autonome (sans SSH, si les deux machines se voient) :**

```bash
# Sur la machine locale
socat TCP4-LISTEN:9090,reuseaddr,fork TCP4:127.0.0.1:3000

# Sur la machine relais
socat TCP4-LISTEN:8080,reuseaddr,fork TCP4:IP_MACHINE_LOCALE:9090
```

**Explication :**

- Le service local tourne sur `:3000` (ex : serveur de développement).
- La machine relais expose `:8080` publiquement et relaie vers `:9090`.
- Le tunnel SSH `-R` fait le lien entre les deux.

**Usage pratique :**
Exposer temporairement un serveur de dev local pour un client, un webhook entrant, ou une démonstration — sans VPN ni configuration NAT.

---

## 20) Proxy SOCKS5 applicatif : relayer une connexion TCP via un proxy SOCKS

**Objectif :** faire transiter une connexion TCP locale à travers un proxy SOCKS5, sans modifier l'application cliente.

```bash
socat -d -d -ly -lf socat_socks5.log \
  TCP4-LISTEN:8080,bind=127.0.0.1,reuseaddr,fork \
  SOCKS4A:proxy.exemple.local:target.exemple.local:80,socksport=1080
```

**Explication :**

| Option | Rôle |
| --- | --- |
| `SOCKS4A:` | Utilise le protocole SOCKS4A (résolution DNS côté proxy) |
| `proxy.exemple.local` | Adresse du proxy SOCKS |
| `target.exemple.local:80` | Destination finale (résolue par le proxy) |
| `socksport=1080` | Port du proxy SOCKS |

**Usage pratique :**
Une application qui ne supporte pas nativement les proxies peut être redirigée à travers un proxy SOCKS5 d'entreprise ou un tunnel SSH (`ssh -D 1080`) via ce pont local. Utile pour des tests d'accès réseau ou pour contourner des restrictions en environnement de lab.

> **Note :** `socat` supporte `SOCKS4A` nativement. Pour SOCKS5, utilisez `PROXY:` avec les options appropriées ou enchaînez avec `ssh -D`.

---

## Mémo des options clés

| Option | Effet |
| --- | --- |
| `bind=127.0.0.1` | Limite l'écoute à localhost |
| `range=x.x.x.x/mask` | ACL réseau intégrée (filtre les IP autorisées) |
| `reuseaddr` | Évite "Address already in use" au redémarrage |
| `fork` | Multi-connexions simultanées (un fils par client) |
| `keepalive` | Keepalive TCP (survie aux NAT/firewalls) |
| `nodelay` | Désactive Nagle (réduit la latence) |
| `connect-timeout=N` | Timeout de connexion sortante en secondes |
| `-T N` | Timeout d'inactivité I/O en secondes |
| `-d -d` | Logs de debug verbeux (sur stderr) |
| `-v -x` | Dump texte + hexadécimal du trafic |
| `-ly -lf fichier.log` | Redirige les logs vers un fichier horodaté |
| `-u` | Mode unidirectionnel (source → destination) |
