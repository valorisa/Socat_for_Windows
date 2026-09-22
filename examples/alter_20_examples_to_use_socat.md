# 20 exemples **professionnels, approfondis et réellement utiles** avec `socat` (Linux / macOS / Windows 11)

> **Compatibilité OS (important)**  
> `socat` est natif sur **Linux** et **macOS**. Sur **Windows 11**, le chemin le plus fiable pour une compatibilité “100% socat” est **WSL2** (Ubuntu/Debian, etc.).  
> Tous les exemples ci-dessous fonctionnent en **Linux/macOS** et en **Windows 11 via WSL2**.  
> (Alternative Windows : MSYS2/Cygwin, mais certaines fonctions `OPENSSL:` / TTY / UDS peuvent varier.)

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

## 1) Relais TCP avec **ACL IP** (allowlist) + redémarrage propre

**Objectif :** exposer un port local, relayer vers un backend, mais **n’autoriser** que certaines plages IP (contrôle d’accès simple côté `socat`).

```bash
socat -d -d -lf ./relay_acl.log \
  TCP-LISTEN:8080,reuseaddr,fork,range=192.168.1.0/24 \
  TCP:backend.local:80,connect-timeout=5
```

**Points clés :**

- `range=...` : filtre les clients autorisés (très utile en réseau interne).
- `fork` : une connexion = un processus (évite de bloquer tout le monde).
- Complétez avec un firewall : défense en profondeur.

---

## 2) Serveur TCP “one-shot” : bannière + fermeture propre (anti-ressources zombies)

**Objectif :** répondre rapidement (banner/version/notice) puis fermer, sans laisser traîner des connexions.

```bash
socat -T 5 TCP-LISTEN:2323,reuseaddr,fork \
  SYSTEM:'printf "Service=demo\nDate=%s\nBye.\n" "$(date -Is)"'
```

**Points clés :**

- `-T 5` coupe si le client ne lit/écrit rien (évite les clients “accrochés”).
- **Bon réflexe sécurité :** si vous faites du `SYSTEM:`/`EXEC:`, gardez `bind=127.0.0.1` si ce n’est pas strictement nécessaire d’exposer sur le LAN.

---

## 3) Transfert de fichier **compressé à la volée** (gain de temps + bande passante)

**Objectif :** envoyer un gros fichier texte/log en compressant côté émetteur, décompresser côté récepteur.

### Récepteur

```bash
socat -d -d TCP-LISTEN:7777,reuseaddr,fork \
  SYSTEM:'gzip -dc > received.log'
```

### Émetteur

```bash
gzip -c ./big.log | socat -d -d - TCP:IP_RECEVEUR:7777,connect-timeout=5
```

**Points clés :**

- Rapide, simple, et souvent plus efficace qu’un transfert brut.
- Pour de la vérification, ajoutez un `sha256sum` avant/après.

---

## 4) “Téléporter” un **Unix Domain Socket distant** en TCP local (via SSH + socat)

**Objectif :** accéder à un service distant qui écoute sur un **socket Unix** (ex: PostgreSQL, Docker, etc.) depuis votre machine, via un port TCP local.

```bash
socat TCP-LISTEN:15432,bind=127.0.0.1,reuseaddr,fork \
  EXEC:'ssh user@serveur_distant socat - UNIX-CONNECT:/var/run/postgresql/.s.PGSQL.5432'
```

**Points clés :**

- Nécessite `socat` côté serveur distant aussi.
- `bind=127.0.0.1` : exposition locale uniquement (recommandé).

---

## 5) Passerelle UDP → TCP (centraliser des événements UDP vers un collecteur TCP)

**Objectif :** recevoir des datagrammes UDP et les relayer vers un collecteur TCP (ex: ingestion applicative).

```bash
socat -u UDP-RECVFROM:5514,reuseaddr,fork \
  TCP:collector.local:5515,connect-timeout=3
```

**Points clés :**

- `UDP-RECVFROM:...,fork` : gère plusieurs sources UDP.
- Limite : la **source IP/port** n’est pas “préservée” dans le flux TCP (si vous en avez besoin, logguez côté passerelle).

---

## 6) “Maintenance mode” HTTP : renvoyer un **503** propre (sans serveur web)

**Objectif :** remplacer temporairement un service HTTP par une réponse maintenance (incident, migration, tests).

```bash
socat TCP-LISTEN:8080,reuseaddr,fork SYSTEM:'printf "HTTP/1.1 503 Service Unavailable\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nMaintenance. Reessayez plus tard.\n"'
```

**Points clés :**

- Très utile pour couper proprement un port en prod tout en gardant une réponse lisible.
- Ajoutez `bind=127.0.0.1` si c’est juste pour du local.

---

## 7) Écriture “journal” : append avec normalisation CRLF/LF (pratique multi-OS)

**Objectif :** collecter des lignes envoyées par TCP et les écrire dans un fichier en **append**, en normalisant les fins de ligne.

```bash
socat TCP-LISTEN:6000,reuseaddr,fork,crlf \
  OPEN:events.txt,creat,append
```

**Points clés :**

- `crlf` aide quand des clients Windows envoient `\r\n`.
- `append` évite d’écraser le fichier.

---

## 8) Port “portier” : limiter la pression (anti-storm) avec `max-children`

**Objectif :** éviter qu’un afflux de connexions ne crée trop de processus (et n’épuise la machine).

```bash
socat -d -d -lf ./limits.log \
  TCP-LISTEN:9090,reuseaddr,fork,max-children=30 \
  TCP:backend.local:9091,connect-timeout=5
```

**Points clés :**

- `max-children=30` met un plafond simple et efficace.
- Combinez avec un reverse proxy/ratelimit si vous avez besoin de finesse.

---

## 9) Traverser un **proxy SOCKS5** (accès réseau contraint)

**Objectif :** joindre une cible TCP via un proxy SOCKS5 (environnements d’entreprise, bastion, lab).

```bash
socat TCP-LISTEN:8443,bind=127.0.0.1,reuseaddr,fork \
  SOCKS5:proxy.corp.local:target.example.com:443,socksport=1080
```

**Points clés :**

- Vous ouvrez `127.0.0.1:8443` en local, et ça sort via SOCKS5 vers `target:443`.
- Parfait pour tester un client “qui ne sait pas SOCKS”.

---

## 10) Pont IPv6 → IPv4 (ou l’inverse) pour compatibilité progressive

**Objectif :** accepter des connexions IPv6 et relayer vers un backend IPv4 (migration dual-stack).

```bash
socat TCP6-LISTEN:8080,reuseaddr,fork \
  TCP4:127.0.0.1:8081,connect-timeout=5
```

**Points clés :**

- Utile quand le frontend est IPv6-ready mais que le backend ne l’est pas encore.

---

# Les 10 suivants = vos exemples “pro” (conservés et intégrés), numérotés 11 → 20

## 11) Relais TCP “production” (timeouts + keepalive + logs lisibles)

**Objectif :** exposer un port local et relayer vers un service distant, avec des garde-fous et une journalisation exploitable.

```bash
socat -d -d -lf ./socat_relay_8080.log \
  TCP-LISTEN:8080,reuseaddr,fork,keepalive,nodelay \
  TCP:example.com:80,connect-timeout=5
```

**Explication :**

- `-d -d` : logs de diagnostic.
- `-lf ...` : fichier de log.
- `reuseaddr,fork` : redémarrage rapide + multi-clients.
- `keepalive,nodelay` : sockets plus robustes et réactives.
- `connect-timeout=5` : évite de rester bloqué.

---

## 12) Mini service TCP orienté ops : endpoint “healthcheck” (timeout d’inactivité)

```bash
socat -T 15 TCP-LISTEN:9001,reuseaddr,fork \
  SYSTEM:'printf "host=%s\ndate=%s\nuptime=%s\nload=%s\n" "$(hostname)" "$(date -Is)" "$(uptime | tr -s " ")" "$(uptime | awk -F"load averages?: " "{print \$2}")"'
```

**Explication :**

- `-T 15` : coupe sur inactivité.
- `SYSTEM:` : compose une réponse lisible, utile pour supervision ad hoc.

---

## 13) Transfert de répertoire propre (préserve droits) via `tar` + contrôle d’intégrité (SHA-256)

### Côté réception (serveur)

```bash
mkdir -p ./restore
socat -d -d TCP-LISTEN:8888,reuseaddr,fork \
  SYSTEM:'tar -xpf - -C ./restore && (cd ./restore && find . -type f -print0 | sort -z | xargs -0 sha256sum) > restore.sha256'
```

### Côté envoi (client)

```bash
cd ./data_to_send
tar -cpf - . | socat -d -d - TCP:IP_RECEVEUR:8888,connect-timeout=5
```

---

## 14) Accéder à un service remote “localhost-only” via SSH + `socat` (sans `nc`)

```bash
socat TCP-LISTEN:15432,reuseaddr,fork \
  EXEC:'ssh -o ExitOnForwardFailure=yes user@serveur_distant -W 127.0.0.1:5432'
```

---

## 15) Collecteur UDP : recevoir et archiver avec horodatage

```bash
socat -u UDP-RECV:5514,reuseaddr \
  SYSTEM:'while IFS= read -r line; do printf "%s %s\n" "$(date -Is)" "$line"; done >> ./udp_events.log'
```

---

## 16) Proxy de debug TCP avec capture hex + payload

```bash
socat -v -x -d -d -lf ./wire_5000.log \
  TCP-LISTEN:5000,reuseaddr,fork \
  TCP:serveur_backend:5001,connect-timeout=5
```

---

## 17) Exposer un socket Unix (IPC local) en TCP local

```bash
socat TCP-LISTEN:7000,bind=127.0.0.1,reuseaddr,fork \
  UNIX-CONNECT:/tmp/mon_service.sock
```

---

## 18) Ajouter du TLS devant un service legacy en clair (TLS termination)

### Préparer un certificat (test)

```bash
openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
  -keyout server.key -out server.crt -subj "/CN=localhost"
```

### Serveur (terminaison TLS)

```bash
socat OPENSSL-LISTEN:8443,reuseaddr,fork,cert=server.crt,key=server.key,verify=0 \
  TCP:127.0.0.1:8080
```

### Client (test)

```bash
socat - OPENSSL:127.0.0.1:8443,verify=0
```

---

## 19) Pont série ↔ TCP robuste (baudrate + raw + flow control)

```bash
socat TCP-LISTEN:2001,reuseaddr,fork \
  FILE:/dev/ttyUSB0,raw,b115200,cs8,parenb=0,cstopb=0,echo=0,crtscts
```

**Windows 11 :** le plus fiable est WSL2 + passage USB (ex: `usbipd-win`) pour obtenir `/dev/ttyUSB0`.

---

## 20) Test “sérieux” de débit : sink serveur + émission contrôlée

### Serveur (réception / “trou noir”)

```bash
socat -d -d TCP-LISTEN:9000,reuseaddr,fork OPEN:/dev/null
```

### Client (envoi 512 MiB) + mesure de temps

```bash
time dd if=/dev/zero bs=1m count=512 2>/dev/null | socat - TCP:IP_SERVEUR:9000,connect-timeout=5
```

---

## Notes “qualité pro” (pour les 20)

- **Sécurité** : évitez d’exposer `SYSTEM:`/`EXEC:` sur une interface publique. Préférez `bind=127.0.0.1` + SSH/VPN, et un firewall.
- **Résilience** : ajoutez `connect-timeout=...`, `-T ...`, `keepalive`, `max-children=...`, et des logs (`-lf`, `-d -d`) pour diagnostiquer vite.
- **Debug** : `-v -x` est excellent pour comprendre un protocole ou une panne côté applicatif.
