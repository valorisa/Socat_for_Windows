# Runbook `socat` — 20 cas d'usage professionnels

**Version :** 1.0  
**Compatibilité :** Linux / macOS / Windows 11 (WSL2)  
**Dernière mise à jour :** Février 2026

---

## Table des matières

1. [Installation](#installation)
2. [Conventions du document](#conventions)
3. [Exemples 1–20](#exemple-1)
4. [Troubleshooting général](#troubleshooting)
5. [Aide-mémoire options](#aide-mémoire)

---

## Installation

```bash
# Debian / Ubuntu
sudo apt-get update && sudo apt-get install -y socat

# Fedora / RHEL
sudo dnf install -y socat

# macOS (Homebrew)
brew install socat

# Windows 11 (WSL2 Ubuntu)
wsl --install -d Ubuntu
# puis dans le terminal WSL :
sudo apt-get update && sudo apt-get install -y socat
```

---

## Conventions

```
┌──────────┐          ┌──────────┐          ┌──────────┐
│  CLIENT  │ ──────▶  │  SOCAT   │ ──────▶  │  CIBLE   │
└──────────┘          └──────────┘          └──────────┘
     A                     B                     C

A = source de la connexion
B = socat (relay / proxy / transformateur)
C = destination finale
```

**Légende des schémas :**

- `───▶` : flux TCP/UDP
- `═══▶` : flux chiffré (TLS)
- `┄┄┄▶` : flux série ou fichier

---

## Exemple 1

### Relais TCP avec ACL IP (allowlist)

**Objectif :** N'autoriser que certaines plages IP à se connecter.

**Schéma :**

```
┌────────────────┐        ┌─────────────────────────┐        ┌────────────┐
│ Client autorisé│──TCP──▶│ socat :8080             │──TCP──▶│ backend:80 │
│ 192.168.1.x    │        │ range=192.168.1.0/24    │        │            │
└────────────────┘        └─────────────────────────┘        └────────────┘

┌────────────────┐        ┌─────────────────────────┐
│ Client refusé  │──TCP──▶│ socat :8080             │ ✗ REJETÉ
│ 10.0.0.x       │        │                         │
└────────────────┘        └─────────────────────────┘
```

**Commande serveur :**

```bash
socat -d -d -lf ./relay_acl.log \
  TCP-LISTEN:8080,reuseaddr,fork,range=192.168.1.0/24 \
  TCP:backend.local:80,connect-timeout=5
```

**Test client (autorisé) :**

```bash
curl -v http://IP_SOCAT:8080/
```

**Test client (refusé) :**

```bash
# Depuis une IP hors plage : connexion refusée
curl -v http://IP_SOCAT:8080/
# Résultat attendu : "Connection refused" ou timeout
```

**Vérification :**

```bash
tail -f ./relay_acl.log
# Les connexions refusées apparaissent avec "range" mismatch
```

---

## Exemple 2

### Serveur TCP "one-shot" avec bannière

**Objectif :** Répondre avec une bannière puis fermer proprement.

**Schéma :**

```
┌──────────┐        ┌──────────────────┐
│  Client  │──TCP──▶│ socat :2323      │
│          │        │ SYSTEM: printf   │
│          │◀─texte─│ "Service=demo.." │
│          │        │ (fermeture)      │
└──────────┘        └──────────────────┘
```

**Commande serveur :**

```bash
socat -T 5 TCP-LISTEN:2323,reuseaddr,fork \
  SYSTEM:'printf "Service=demo\nDate=%s\nBye.\n" "$(date -Is)"'
```

**Test client :**

```bash
nc localhost 2323
# ou
socat - TCP:localhost:2323
```

**Sortie attendue :**

```
Service=demo
Date=2025-02-24T14:32:01+0100
Bye.
```

---

## Exemple 3

### Transfert de fichier compressé à la volée

**Objectif :** Économiser la bande passante lors d'un transfert.

**Schéma :**

```
┌──────────────┐        ┌────────────────┐        ┌──────────────┐
│   Émetteur   │        │    Réseau      │        │  Récepteur   │
│              │        │                │        │              │
│ big.log      │        │                │        │ received.log │
│   │          │        │                │        │   ▲          │
│   ▼          │        │                │        │   │          │
│ gzip -c ─────┼──TCP──▶│────────────────│──TCP──▶│ gzip -dc     │
│ (compressé)  │        │ flux compressé │        │ (décompressé)│
└──────────────┘        └────────────────┘        └──────────────┘
```

**Commande récepteur :**

```bash
socat -d -d TCP-LISTEN:7777,reuseaddr \
  SYSTEM:'gzip -dc > received.log && echo "OK: $(wc -c < received.log) octets"'
```

**Commande émetteur :**

```bash
gzip -c ./big.log | socat -d -d - TCP:IP_RECEVEUR:7777,connect-timeout=5
```

**Vérification :**

```bash
# Côté récepteur
sha256sum received.log

# Côté émetteur (pour comparer)
sha256sum big.log
```

---

## Exemple 4

### Accès à un socket Unix distant via SSH

**Objectif :** Accéder à un service distant écoutant sur socket Unix.

**Schéma :**

```
┌──────────┐       ┌──────────────────┐       ┌──────────────────┐       ┌─────────────┐
│  Client  │──TCP─▶│ socat :15432     │──SSH─▶│ serveur distant  │──UDS─▶│ PostgreSQL  │
│ localhost│       │ EXEC:ssh...      │       │ socat UNIX-CONN  │       │ .s.PGSQL.5432│
└──────────┘       └──────────────────┘       └──────────────────┘       └─────────────┘
```

**Commande (machine locale) :**

```bash
socat TCP-LISTEN:15432,bind=127.0.0.1,reuseaddr,fork \
  EXEC:'ssh user@serveur_distant socat - UNIX-CONNECT:/var/run/postgresql/.s.PGSQL.5432'
```

**Test client :**

```bash
psql -h 127.0.0.1 -p 15432 -U postgres
# ou
nc -v 127.0.0.1 15432
```

**Prérequis :**

- `socat` installé sur le serveur distant
- Accès SSH configuré (clé recommandée)

---

## Exemple 5

### Passerelle UDP → TCP

**Objectif :** Centraliser des événements UDP vers un collecteur TCP.

**Schéma :**

```
┌───────────┐       ┌────────────────┐       ┌────────────────┐
│ Source 1  │──UDP─▶│                │       │                │
└───────────┘       │                │       │                │
┌───────────┐       │ socat :5514    │──TCP─▶│ collector:5515 │
│ Source 2  │──UDP─▶│ UDP-RECVFROM   │       │                │
└───────────┘       │                │       │                │
┌───────────┐       │                │       │                │
│ Source N  │──UDP─▶│                │       │                │
└───────────┘       └────────────────┘       └────────────────┘
```

**Commande passerelle :**

```bash
socat -d -d UDP-RECVFROM:5514,reuseaddr,fork \
  TCP:collector.local:5515,connect-timeout=3
```

**Test client (simuler un envoi UDP) :**

```bash
echo "test event $(date)" | socat - UDP-SENDTO:IP_PASSERELLE:5514
```

---

## Exemple 6

### Mode maintenance HTTP (réponse 503)

**Objectif :** Afficher une page maintenance sans serveur web.

**Schéma :**

```
┌──────────┐        ┌──────────────────────┐
│ Browser  │──HTTP─▶│ socat :8080          │
│          │        │                      │
│          │◀─503───│ "Maintenance..."     │
└──────────┘        └──────────────────────┘
```

**Commande serveur :**

```bash
socat TCP-LISTEN:8080,reuseaddr,fork \
  SYSTEM:'printf "HTTP/1.1 503 Service Unavailable\r\nContent-Type: text/plain\r\nConnection: close\r\nContent-Length: 32\r\n\r\nMaintenance. Reessayez plus tard"'
```

**Test client :**

```bash
curl -i http://localhost:8080/
```

**Sortie attendue :**

```
HTTP/1.1 503 Service Unavailable
Content-Type: text/plain
Connection: close
Content-Length: 32

Maintenance. Reessayez plus tard
```

---

## Exemple 7

### Écriture journal avec normalisation CRLF

**Objectif :** Collecter des logs TCP multi-OS en append.

**Schéma :**

```
┌──────────┐        ┌──────────────────┐        ┌─────────────┐
│ Client 1 │──TCP──▶│                  │        │             │
│ (Linux)  │  LF    │                  │        │             │
└──────────┘        │ socat :6000      │───────▶│ events.txt  │
┌──────────┐        │ crlf, append     │        │ (append)    │
│ Client 2 │──TCP──▶│                  │        │             │
│ (Windows)│ CRLF   │                  │        │             │
└──────────┘        └──────────────────┘        └─────────────┘
```

**Commande serveur :**

```bash
socat TCP-LISTEN:6000,reuseaddr,fork,crlf \
  OPEN:events.txt,creat,append
```

**Test client :**

```bash
echo "Event from $(hostname) at $(date)" | socat - TCP:localhost:6000
```

**Vérification :**

```bash
tail -f events.txt
```

---

## Exemple 8

### Protection anti-storm avec `max-children`

**Objectif :** Limiter le nombre de connexions simultanées.

**Schéma :**

```
┌──────────┐        ┌────────────────────────┐        ┌──────────┐
│ Client 1 │──TCP──▶│                        │──TCP──▶│          │
├──────────┤        │ socat :9090            │        │          │
│ Client 2 │──TCP──▶│ max-children=30        │──TCP──▶│ backend  │
├──────────┤        │                        │        │ :9091    │
│    ...   │        │ (31e client = attente) │        │          │
├──────────┤        │                        │        │          │
│ Client 30│──TCP──▶│                        │──TCP──▶│          │
└──────────┘        └────────────────────────┘        └──────────┘
```

**Commande serveur :**

```bash
socat -d -d -lf ./limits.log \
  TCP-LISTEN:9090,reuseaddr,fork,max-children=30 \
  TCP:backend.local:9091,connect-timeout=5
```

**Test de charge :**

```bash
# Ouvrir 35 connexions simultanées
for i in $(seq 1 35); do
  (sleep 10 | nc localhost 9090) &
done
wait
```

**Vérification :**

```bash
# Compter les processus socat
pgrep -c socat
# Ne doit pas dépasser 31 (1 parent + 30 enfants)
```

---

## Exemple 9

### Traverser un proxy SOCKS5

**Objectif :** Atteindre une cible via SOCKS5 depuis un client non-SOCKS.

**Schéma :**

```
┌──────────┐        ┌──────────────────┐        ┌─────────────┐        ┌──────────┐
│  Client  │──TCP──▶│ socat :8443      │──SOCKS5▶│ proxy.corp  │──TCP──▶│ target   │
│ (curl)   │        │ bind=127.0.0.1   │        │ :1080       │        │ :443     │
└──────────┘        └──────────────────┘        └─────────────┘        └──────────┘
```

**Commande serveur :**

```bash
socat TCP-LISTEN:8443,bind=127.0.0.1,reuseaddr,fork \
  SOCKS5:proxy.corp.local:target.example.com:443,socksport=1080
```

**Test client :**

```bash
curl -v https://127.0.0.1:8443/ --resolve target.example.com:8443:127.0.0.1
```

---

## Exemple 10

### Pont IPv6 → IPv4

**Objectif :** Exposer un backend IPv4 sur une interface IPv6.

**Schéma :**

```
┌──────────────┐        ┌──────────────────┐        ┌──────────────┐
│ Client IPv6  │──TCP6─▶│ socat            │──TCP4─▶│ Backend IPv4 │
│              │        │ TCP6-LISTEN:8080 │        │ 127.0.0.1    │
│              │        │       ↓          │        │ :8081        │
│              │        │ TCP4:127.0.0.1   │        │              │
└──────────────┘        └──────────────────┘        └──────────────┘
```

**Commande serveur :**

```bash
socat TCP6-LISTEN:8080,reuseaddr,fork \
  TCP4:127.0.0.1:8081,connect-timeout=5
```

**Test client :**

```bash
curl -v -6 http://[::1]:8080/
```

---

## Exemple 11

### Relais TCP production (logs + keepalive + timeout)

**Objectif :** Relay robuste avec diagnostics.

**Schéma :**

```
┌──────────┐        ┌─────────────────────────────┐        ┌──────────────┐
│  Client  │──TCP──▶│ socat :8080                 │──TCP──▶│ example.com  │
│          │        │ -d -d -lf relay.log         │        │ :80          │
│          │        │ keepalive, nodelay          │        │              │
│          │        │ connect-timeout=5           │        │              │
└──────────┘        └─────────────────────────────┘        └──────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ relay.log        │
                    │ (diagnostic)     │
                    └──────────────────┘
```

**Commande serveur :**

```bash
socat -d -d -lf ./socat_relay_8080.log \
  TCP-LISTEN:8080,reuseaddr,fork,keepalive,nodelay \
  TCP:example.com:80,connect-timeout=5
```

**Test client :**

```bash
curl -v http://localhost:8080/
```

**Vérification :**

```bash
tail -f ./socat_relay_8080.log
```

---

## Exemple 12

### Endpoint healthcheck TCP

**Objectif :** Fournir un endpoint de supervision simple.

**Schéma :**

```
┌────────────┐        ┌──────────────────────────┐
│ Monitoring │──TCP──▶│ socat :9001              │
│ (Nagios,   │        │ SYSTEM: printf status    │
│  curl)     │◀─text──│ host, date, uptime, load │
└────────────┘        └──────────────────────────┘
```

**Commande serveur :**

```bash
socat -T 15 TCP-LISTEN:9001,reuseaddr,fork \
  SYSTEM:'printf "host=%s\ndate=%s\nuptime=%s\nload=%s\n" \
    "$(hostname)" "$(date -Is)" "$(uptime -p 2>/dev/null || uptime)" \
    "$(cat /proc/loadavg 2>/dev/null || sysctl -n vm.loadavg)"'
```

**Test client :**

```bash
nc localhost 9001
```

**Sortie attendue :**

```
host=myserver
date=2025-02-24T14:45:00+0100
uptime=up 3 days, 2 hours
load=0.15 0.10 0.05 1/234 5678
```

---

## Exemple 13

### Transfert répertoire avec tar + SHA-256

**Objectif :** Transférer un dossier complet avec vérification d'intégrité.

**Schéma :**

```
┌──────────────────┐        ┌────────────────┐        ┌──────────────────┐
│    ÉMETTEUR      │        │    Réseau      │        │    RÉCEPTEUR     │
│                  │        │                │        │                  │
│ data_to_send/    │        │                │        │ restore/         │
│   ├── file1.txt  │        │                │        │   ├── file1.txt  │
│   ├── file2.txt  │        │                │        │   ├── file2.txt  │
│   └── subdir/    │        │                │        │   └── subdir/    │
│         │        │        │                │        │         ▲        │
│         ▼        │        │                │        │         │        │
│     tar -cpf ────┼──TCP──▶│────────────────│──TCP──▶│     tar -xpf     │
│                  │        │   flux tar     │        │         │        │
│                  │        │                │        │         ▼        │
│                  │        │                │        │   sha256sum >    │
│                  │        │                │        │   restore.sha256 │
└──────────────────┘        └────────────────┘        └──────────────────┘
```

**Commande récepteur :**

```bash
mkdir -p ./restore
socat -d -d TCP-LISTEN:8888,reuseaddr \
  SYSTEM:'tar -xpf - -C ./restore && \
    (cd ./restore && find . -type f -print0 | sort -z | xargs -0 sha256sum) > restore.sha256 && \
    echo "Transfert OK: $(wc -l < restore.sha256) fichiers"'
```

**Commande émetteur :**

```bash
cd ./data_to_send
tar -cpf - . | socat -d -d - TCP:IP_RECEVEUR:8888,connect-timeout=10
```

**Vérification :**

```bash
cat restore.sha256
```

---

## Exemple 14

### Accès service "localhost-only" via SSH

**Objectif :** Exposer localement un service distant qui n'écoute que sur 127.0.0.1.

**Schéma :**

```
┌──────────┐       ┌────────────────────┐       ┌────────────────────┐
│  Client  │──TCP─▶│ socat :15432       │══SSH═▶│ serveur_distant    │
│ (psql)   │       │ EXEC:ssh -W        │       │ 127.0.0.1:5432     │
└──────────┘       └────────────────────┘       └────────────────────┘
```

**Commande :**

```bash
socat TCP-LISTEN:15432,reuseaddr,fork \
  EXEC:'ssh -o ExitOnForwardFailure=yes user@serveur_distant -W 127.0.0.1:5432'
```

**Test client :**

```bash
psql -h 127.0.0.1 -p 15432 -U myuser -d mydb
```

---

## Exemple 15

### Collecteur UDP avec horodatage

**Objectif :** Archiver des événements UDP avec timestamp.

**Schéma :**

```
┌───────────┐        ┌─────────────────────────┐        ┌────────────────┐
│ App/Syslog│──UDP──▶│ socat UDP-RECV:5514     │───────▶│ udp_events.log │
│           │        │ SYSTEM: date + append   │        │ (timestamped)  │
└───────────┘        └─────────────────────────┘        └────────────────┘
```

**Commande serveur :**

```bash
socat -u UDP-RECV:5514,reuseaddr \
  SYSTEM:'while IFS= read -r line; do printf "%s %s\n" "$(date -Is)" "$line"; done >> ./udp_events.log'
```

**Test client :**

```bash
echo "<14>Test syslog message" | socat - UDP-SENDTO:localhost:5514
```

**Vérification :**

```bash
tail -f ./udp_events.log
```

**Sortie attendue :**

```
2025-02-24T14:50:00+0100 <14>Test syslog message
```

---

## Exemple 16

### Proxy debug avec capture hex

**Objectif :** Analyser le trafic entre un client et un serveur.

**Schéma :**

```
┌──────────┐        ┌─────────────────────────┐        ┌──────────────┐
│  Client  │──TCP──▶│ socat :5000             │──TCP──▶│ backend:5001 │
│          │        │ -v -x (capture hex)     │        │              │
│          │◀──────▶│        │                │◀──────▶│              │
└──────────┘        │        ▼                │        └──────────────┘
                    │ ┌────────────────┐      │
                    │ │ wire_5000.log  │      │
                    │ │ (hex dump)     │      │
                    │ └────────────────┘      │
                    └─────────────────────────┘
```

**Commande serveur :**

```bash
socat -v -x -d -d -lf ./wire_5000.log \
  TCP-LISTEN:5000,reuseaddr,fork \
  TCP:backend.local:5001,connect-timeout=5
```

**Test client :**

```bash
echo "GET / HTTP/1.0\r\n\r\n" | socat - TCP:localhost:5000
```

**Analyse du log :**

```bash
cat ./wire_5000.log
# Affiche le dump hexadécimal des échanges
```

---

## Exemple 17

### Exposer socket Unix en TCP local

**Objectif :** Rendre un socket Unix accessible via TCP.

**Schéma :**

```
┌──────────┐        ┌─────────────────────────┐        ┌────────────────────┐
│  Client  │──TCP──▶│ socat :7000             │──UDS──▶│ /tmp/service.sock  │
│ (curl,nc)│        │ bind=127.0.0.1          │        │ (docker, app...)   │
└──────────┘        └─────────────────────────┘        └────────────────────┘
```

**Commande :**

```bash
socat TCP-LISTEN:7000,bind=127.0.0.1,reuseaddr,fork \
  UNIX-CONNECT:/tmp/mon_service.sock
```

**Test client :**

```bash
curl http://127.0.0.1:7000/health
# ou
echo "STATUS" | nc 127.0.0.1 7000
```

---

## Exemple 18

### TLS termination pour service legacy

**Objectif :** Ajouter TLS devant une application non sécurisée.

**Schéma :**

```
┌──────────┐        ┌─────────────────────────┐        ┌──────────────┐
│  Client  │══TLS══▶│ socat OPENSSL-LISTEN    │──TCP──▶│ backend HTTP │
│ (HTTPS)  │        │ :8443                   │        │ :8080 (clair)│
│          │        │ cert + key              │        │              │
└──────────┘        └─────────────────────────┘        └──────────────┘
```

**Préparer certificat :**

```bash
openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
  -keyout server.key -out server.crt -subj "/CN=localhost"
```

**Commande serveur :**

```bash
socat OPENSSL-LISTEN:8443,reuseaddr,fork,cert=server.crt,key=server.key,verify=0 \
  TCP:127.0.0.1:8080
```

**Test client :**

```bash
curl -k https://localhost:8443/
# ou
socat - OPENSSL:localhost:8443,verify=0
```

---

## Exemple 19

### Pont série ↔ TCP

**Objectif :** Accéder à un périphérique série via réseau.

**Schéma :**

```
┌──────────┐        ┌─────────────────────────┐        ┌────────────────┐
│  Client  │──TCP──▶│ socat :2001             │┄┄┄┄┄┄▶│ /dev/ttyUSB0   │
│ (telnet) │        │ FILE: raw, b115200      │        │ (Arduino, etc) │
│          │◀──────▶│                         │◀┄┄┄┄┄┄│                │
└──────────┘        └─────────────────────────┘        └────────────────┘
```

**Commande serveur :**

```bash
socat TCP-LISTEN:2001,reuseaddr,fork \
  FILE:/dev/ttyUSB0,raw,b115200,cs8,parenb=0,cstopb=0,echo=0
```

**Test client :**

```bash
# Connexion interactive
socat -,raw,echo=0 TCP:IP_SERVEUR:2001

# Ou envoyer une commande
echo "AT" | socat - TCP:IP_SERVEUR:2001
```

**Windows 11 (WSL2) :**

```bash
# Installer usbipd-win pour partager le port USB avec WSL2
# Puis dans WSL2, le device apparaît en /dev/ttyUSB0
```

---

## Exemple 20

### Test de débit TCP

**Objectif :** Mesurer le throughput réseau sans iperf.

**Schéma :**

```
┌──────────────────┐        ┌────────────────┐        ┌──────────────────┐
│    ÉMETTEUR      │        │    Réseau      │        │    RÉCEPTEUR     │
│                  │        │                │        │                  │
│ dd if=/dev/zero  │        │                │        │ socat :9000      │
│ bs=1M count=512  │──TCP──▶│ ══════════════▶│──TCP──▶│ OPEN:/dev/null   │
│        │         │        │   512 MiB      │        │ (sink)           │
│        ▼         │        │                │        │                  │
│    time (mesure) │        │                │        │                  │
└──────────────────┘        └────────────────┘        └──────────────────┘
```

**Commande récepteur (sink) :**

```bash
socat -d -d TCP-LISTEN:9000,reuseaddr,fork OPEN:/dev/null
```

**Commande émetteur + mesure :**

```bash
time sh -c 'dd if=/dev/zero bs=1M count=512 2>/dev/null | socat - TCP:IP_SERVEUR:9000'
```

**Calcul du débit :**

```bash
# Si le temps réel est de 4.2 secondes :
# Débit = 512 MiB / 4.2s ≈ 122 MiB/s ≈ 976 Mbit/s
```

---

## Troubleshooting

### Problèmes courants et solutions

| Symptôme | Cause probable | Solution |
| ---------- | ---------------- | ---------- |
| `Address already in use` | Port déjà occupé | `reuseaddr` ou vérifier avec `ss -tlnp` |
| `Connection refused` | Service cible down | Vérifier backend, firewall |
| `Connection timed out` | Firewall, route | Tester avec `nc -vz host port` |
| `Permission denied` | Port < 1024 sans root | Utiliser port > 1024 ou `sudo` |
| `Name or service not known` | DNS défaillant | Utiliser IP directement |
| Connexion coupe immédiatement | Pas de `fork` | Ajouter `fork` pour multi-clients |
| Données tronquées | Buffer trop petit | Vérifier côté application |
| SSL handshake failed | Certificat invalide | Vérifier cert/key, ou `verify=0` en test |

### Commandes de diagnostic

```bash
# Vérifier si socat écoute
ss -tlnp | grep socat
netstat -tlnp | grep socat  # alternative

# Tester la connectivité
nc -vz localhost 8080
socat /dev/null TCP:localhost:8080,connect-timeout=2 && echo OK

# Voir les processus socat
pgrep -af socat

# Logs en temps réel (si -lf utilisé)
tail -f ./socat.log

# Tuer tous les socat
pkill socat
```

### Debug verbeux

```bash
# Niveau 1 : infos basiques
socat -d ...

# Niveau 2 : détaillé (recommandé)
socat -d -d ...

# Niveau 3 : très verbeux
socat -d -d -d ...

# Avec dump hex (pour protocoles binaires)
socat -d -d -v -x ...
```

---

## Aide-mémoire

### Options globales fréquentes

| Option | Description |
| -------- | ------------- |
| `-d -d` | Mode debug (2 niveaux) |
| `-lf FILE` | Log dans un fichier |
| `-v` | Affiche les données transférées |
| `-x` | Dump hexadécimal |
| `-T SEC` | Timeout d'inactivité |
| `-u` | Mode unidirectionnel |

### Options d'adresse fréquentes

| Option | Description |
| -------- | ------------- |
| `reuseaddr` | Réutiliser le port immédiatement |
| `fork` | Un processus par connexion |
| `bind=IP` | Lier à une interface spécifique |
| `range=CIDR` | Restreindre les IP sources |
| `connect-timeout=SEC` | Timeout de connexion |
| `keepalive` | Activer TCP keepalive |
| `nodelay` | Désactiver Nagle (latence) |
| `max-children=N` | Limiter les connexions |

### Types d'adresses

| Type | Exemple | Usage |
| ------ | --------- | ------- |
| `TCP-LISTEN` | `TCP-LISTEN:8080` | Serveur TCP |
| `TCP` | `TCP:host:port` | Client TCP |
| `TCP4` / `TCP6` | `TCP6-LISTEN:8080` | Forcer IPv4/IPv6 |
| `UDP-RECV` | `UDP-RECV:5514` | Réception UDP |
| `UDP-SENDTO` | `UDP-SENDTO:host:port` | Envoi UDP |
| `UNIX-LISTEN` | `UNIX-LISTEN:/tmp/s.sock` | Serveur socket Unix |
| `UNIX-CONNECT` | `UNIX-CONNECT:/tmp/s.sock` | Client socket Unix |
| `OPENSSL-LISTEN` | `OPENSSL-LISTEN:443` | Serveur TLS |
| `OPENSSL` | `OPENSSL:host:443` | Client TLS |
| `EXEC` | `EXEC:'cmd'` | Exécuter une commande |
| `SYSTEM` | `SYSTEM:'cmd'` | Exécuter via shell |
| `FILE` | `FILE:/dev/ttyUSB0` | Fichier/device |
| `OPEN` | `OPEN:file.txt,creat` | Ouvrir/créer fichier |
| `SOCKS5` | `SOCKS5:proxy:target:port` | Via proxy SOCKS5 |

---

**Fin du runbook**
