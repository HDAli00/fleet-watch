# Multi-stage build — slim production image
FROM python:3.11-slim AS builder

WORKDIR /app

# Install uv for fast dependency resolution
RUN pip install --no-cache-dir uv==0.4.10

COPY pyproject.toml .
# Generate lockfile and install to a local prefix (no virtualenv in container)
RUN uv export --no-dev --no-hashes -o requirements.txt && \
    pip install --no-cache-dir -r requirements.txt --target /install

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

# ── Production stage ─────────────────────────────────────────────────────────
FROM python:3.11-slim

# Security: non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app
COPY --from=builder /install /usr/local/lib/python3.11/site-packages
COPY --from=builder /app /app

USER appuser

EXPOSE 8000

# Health check — ALB needs this to pass before routing traffic
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
