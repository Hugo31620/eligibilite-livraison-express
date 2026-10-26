# syntax=docker/dockerfile:1
#
# Image de l'API (ADR-0003), construite en trois étapes (build multi-stage) :
#
#   build ──► test  : roues + dépendances de test + tests  → pytest et ruff DANS l'image
#     │         │
#     └─────────┴──► prod : roues de l'application uniquement, non-root, sans pip
#
#   docker build --target test .   # rejoue les tests dans l'environnement exact de prod
#   docker build .                 # image de production (dernière étape)
#
# Base : python:3.12-slim (Debian). Alpine a été écartée : scikit-learn, numpy et pandas
# n'y ont pas de roues musl fiables, il faudrait les compiler (image plus grosse au final).

ARG PYTHON_IMAGE=python:3.12-slim

# ───────────────────────── 1. build : compile les roues ─────────────────────────
FROM ${PYTHON_IMAGE} AS build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
# Roue de l'application + roues de toutes ses dépendances d'exécution.
RUN pip wheel --wheel-dir /wheels .

# ──────────────── 2. test : même roues + outils de test, puis on teste ────────────────
FROM ${PYTHON_IMAGE} AS test
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=build /wheels /wheels
# On installe la roue (pas le code source) : on teste exactement ce qui part en prod.
RUN pip install --find-links /wheels "$(ls /wheels/eligibilite_livraison_express-*.whl)[dev]"
COPY pyproject.toml openapi.yml ./
COPY tests ./tests
RUN ruff check tests \
    && pytest -q -p no:cacheprovider \
    && touch /tests-passed

# ───────────────────── 3. prod : image minimale et durcie ─────────────────────
FROM ${PYTHON_IMAGE} AS prod
ARG VERSION=dev
ARG VCS_REF=unknown
LABEL org.opencontainers.image.title="eligibilite-livraison-express" \
      org.opencontainers.image.description="API de prédiction d'éligibilité à la livraison express" \
      org.opencontainers.image.source="https://github.com/Hugo31620/eligibilite-livraison-express" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}"

# Aucun secret ici : clés d'API, chaînes de connexion… sont fournies à l'exécution
# (docker run -e / secrets montés). Jamais de .env dans l'image (exclu par .dockerignore).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=dev \
    ARTIFACTS_DIR=/app/artifacts \
    ORDERS_DB_PATH=/app/data/orders.db \
    API_KEYS_FILE=/run/secrets/api_keys.json \
    EXPOSE_API_DOCS=false

# L'image de prod n'existe que si les tests de l'étape « test » sont passés.
COPY --from=test /tests-passed /tmp/tests-passed

# --mount : les roues ne sont jamais écrites dans une couche de l'image finale.
# pip/setuptools sont ensuite désinstallés : moins de code embarqué, moins de surface d'attaque.
RUN --mount=type=bind,from=build,source=/wheels,target=/wheels \
    pip install --no-cache-dir --no-index --find-links /wheels eligibilite-livraison-express \
    && pip uninstall -y pip setuptools wheel \
    && find /usr/local -depth -name '__pycache__' -type d -exec rm -rf {} + \
    && rm -f /tmp/tests-passed \
    && useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app \
    && mkdir -p /app/artifacts /app/data \
    && chown app:app /app/artifacts /app/data

WORKDIR /app
# Rootless : un attaquant qui prendrait la main sur le processus n'aurait aucun droit root.
USER 10001:10001

# Seul port ouvert, publié vers le reverse proxy uniquement, jamais vers Internet (ADR-0006).
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"]

CMD ["uvicorn", "eligibilite_livraison.api.app:create_app", "--factory", \
     "--host", "0.0.0.0", "--port", "8000", "--no-server-header", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
