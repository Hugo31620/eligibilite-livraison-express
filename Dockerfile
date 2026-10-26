# Image de production de l'API (ADR-0003). Construite en deux étapes : seul le paquet
# installé arrive dans l'image finale, sans tests, notebook, ADR ni outils de build.

FROM python:3.12-slim AS build
WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip wheel --no-cache-dir --wheel-dir /wheels .

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=dev \
    ARTIFACTS_DIR=/app/artifacts \
    ORDERS_DB_PATH=/app/data/orders.db \
    API_KEYS_FILE=/run/secrets/api_keys.json \
    EXPOSE_API_DOCS=false

COPY --from=build /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl \
    && rm -rf /wheels \
    && useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app \
    && mkdir -p /app/artifacts /app/data \
    && chown app:app /app/artifacts /app/data

WORKDIR /app
# Jamais root : un attaquant qui prendrait la main sur le processus resterait confiné.
USER app

# Port interne : il n'est publié que vers le reverse proxy, jamais vers Internet (ADR-0006).
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

CMD ["uvicorn", "eligibilite_livraison.api.app:create_app", "--factory", \
     "--host", "0.0.0.0", "--port", "8000", "--no-server-header", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
