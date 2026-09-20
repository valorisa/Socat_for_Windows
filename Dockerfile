# syntax=docker/dockerfile:1

# =============================================================================
# Stage 1 : builder
# Compile socat depuis les sources. Ce stage est jeté à la fin du build ;
# seul le binaire compilé est récupéré dans le stage final.
# =============================================================================
ARG PYTHON_VERSION=3.14.5
FROM python:${PYTHON_VERSION}-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    build-essential \
    libssl-dev \
 && rm -rf /var/lib/apt/lists/*

ARG SOCAT_VERSION=1.8.1.3
WORKDIR /build

# Téléchargement + vérification du checksum officiel avant compilation
RUN wget -q "http://www.dest-unreach.org/socat/download/socat-${SOCAT_VERSION}.tar.gz" \
 && wget -q "http://www.dest-unreach.org/socat/download.sha256sum" \
 && grep "socat-${SOCAT_VERSION}.tar.gz" download.sha256sum | sha256sum -c - \
 && tar -xzf "socat-${SOCAT_VERSION}.tar.gz" \
 && cd "socat-${SOCAT_VERSION}" \
 && ./configure \
 && make -j"$(nproc)" \
 && make install DESTDIR=/build/out

# =============================================================================
# Stage 2 : runtime
# Image finale allégée : pas d'outils de build, utilisateur non-root.
# =============================================================================
FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# libssl3 : dépendance runtime du binaire socat compilé avec OpenSSL
RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl3 \
 && rm -rf /var/lib/apt/lists/*

# Récupération du binaire socat compilé dans le stage builder
COPY --from=builder /build/out/usr/local/bin/socat  /usr/local/bin/socat
COPY --from=builder /build/out/usr/local/bin/filan   /usr/local/bin/filan
COPY --from=builder /build/out/usr/local/bin/procan  /usr/local/bin/procan

# Utilisateur de service non-root, non-loggable
ARG VALORISA_UID=10002
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/usr/sbin/nologin" \
    --no-create-home \
    --uid "${VALORISA_UID}" \
    valorisa

# Dépendances Python (installées en root, avant le passage en non-root)
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --no-cache-dir -r requirements.txt

# Code applicatif, appartenant à l'utilisateur d'exécution
COPY --chown=valorisa:valorisa . .

EXPOSE 8181

USER valorisa

# TODO : remplacer "app:app" par le vrai chemin module:callable de
# l'application WSGI (ex. "myproject.wsgi:app"). "socat.example:app" dans le
# fichier d'origine ne correspond à aucun module Python réel.
CMD ["gunicorn", "app:app", "--bind=0.0.0.0:8181"]
