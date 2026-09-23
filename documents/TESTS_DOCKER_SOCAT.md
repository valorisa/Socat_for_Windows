# Docker tests for socat 1.8.1.0

## 1. Build the Docker image

In the directory containing `Dockerfile` and `requirements.txt`:

```bash
docker build -t socat-api:1.8.1.0 .
```

## 2. Run the Flask/gunicorn demo app

Start the container:

```bash
docker run --rm -p 8181:8181 --name socat-api socat-api:1.8.1.0
```

Then, in another terminal (PowerShell):

```powershell
curl http://127.0.0.1:8181/
# or
Invoke-WebRequest http://127.0.0.1:8181/ -UseBasicParsing
```

Expected response:

```text
socat 1.8.1.0 Docker demo
```

If you need to rerun the container and the name is still taken:

```powershell
docker rm socat-api
docker run --rm -p 8181:8181 --name socat-api socat-api:1.8.1.0
```

## 3. Check socat version inside the image

Run socat directly as the container entrypoint:

```bash
docker run --rm --entrypoint socat socat-api:1.8.1.0 -V
```

Expected output (simplified):

```text
socat version 1.8.1.0
...
WITH_SOCKS4 1
WITH_SOCKS4A 1
WITH_SOCKS5 1
WITH_OPENSSL 1
```

## 4. Simple TCP echo test with socat + telnet/netcat

### 4.1. Echo server inside Docker (optional variant)

You can run a quick socat echo server directly in a container:

```bash
docker run --rm -p 9000:9000 --name socat-test socat-api:1.8.1.0 \
  socat -v TCP-LISTEN:9000,reuseaddr,fork SYSTEM:"cat"
```

Then, from the host or another shell, connect with telnet or netcat:

```bash
telnet 127.0.0.1 9000
# type text and press Enter to see it echoed
```

### 4.2. Echo server on Cygwin host + netcat

In one Cygwin terminal (server):

```bash
socat -v TCP-LISTEN:9000,reuseaddr,fork EXEC:/bin/cat
```

In another Cygwin terminal (client, after installing netcat):

```bash
nc 127.0.0.1 9000
# type text and press Enter to see each line echoed back
```

## 5. Helper: sample Python app for gunicorn

Directory structure:

```text
Install_from_dockerfile/
├── Dockerfile
├── requirements.txt
└── socat/
    ├── __init__.py
    └── example.py
```

`requirements.txt`:

```text
Flask
gunicorn
```

`socat/example.py`:

```python
from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return "socat 1.8.1.0 Docker demo\n"
```

The Dockerfile ends with:

```dockerfile
EXPOSE 8181
USER valorisa
CMD ["gunicorn", "socat.example:app", "--bind=0.0.0.0:8181"]
```

***
