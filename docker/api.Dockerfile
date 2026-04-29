FROM python:3.11-slim-bookworm AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# Trust host-provided CA bundle (for TLS-intercepting build environments).
COPY docker/ca-bundle.crt /usr/local/share/ca-certificates/host-ca-bundle.crt
RUN if [ -s /usr/local/share/ca-certificates/host-ca-bundle.crt ]; then \
      cat /usr/local/share/ca-certificates/host-ca-bundle.crt >> /etc/ssl/certs/ca-certificates.crt; \
    fi \
 && pip install --no-cache-dir uv

FROM base AS deps
WORKDIR /build
COPY app/api/pyproject.toml app/api/uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project 2>/dev/null \
 || uv sync --no-dev --no-install-project

FROM base AS runtime
WORKDIR /srv
COPY --from=deps /opt/venv /opt/venv
COPY app/api/pyproject.toml app/api/alembic.ini ./
COPY app/api/alembic ./alembic
COPY app/api/app ./app

RUN useradd --system --uid 1001 fleet && chown -R fleet:fleet /srv
USER fleet

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=5 \
  CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://localhost:8000/health',timeout=2); sys.exit(0)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
