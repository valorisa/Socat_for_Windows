# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.14.3
FROM python:${PYTHON_VERSION}-slim-bookworm AS base

# Avoid Python .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System deps needed to build socat and Python packages
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    build-essential \
    libssl-dev \
    bash \
 && rm -rf /var/lib/apt/lists/*

# Build and install socat 1.8.1.3 from official source
ARG SOCAT_VERSION=1.8.1.3
RUN wget http://www.dest-unreach.org/socat/download/socat-${SOCAT_VERSION}.tar.gz \
 && tar -xzf socat-${SOCAT_VERSION}.tar.gz \
 && cd socat-${SOCAT_VERSION} \
 && ./configure \
 && make \
 && make install \
 && cd .. \
 && rm -rf socat-${SOCAT_VERSION} socat-${SOCAT_VERSION}.tar.gz

# Non‑root user for running the app
ARG VALORISA_UID=10002
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/bin/bash" \
    --no-create-home \
    --uid "${VALORISA_UID}" \
    valorisa

# Python dependencies
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --no-cache-dir -r requirements.txt

# Application source
COPY . .

# App port
EXPOSE 8181

# Run as non‑root user
USER valorisa

# Start gunicorn app
CMD ["gunicorn", "socat.example:app", "--bind=0.0.0.0:8181"]
