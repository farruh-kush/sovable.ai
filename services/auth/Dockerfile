# ── Build stage ──────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

RUN pip install --no-cache-dir setuptools wheel

COPY shared/ /build/shared/
RUN pip install --no-cache-dir /build/shared

COPY services/auth/ /build/auth/
RUN sed -i 's|ai-routing-shared @ file:///${PROJECT_ROOT}/shared|ai-routing-shared|' /build/auth/pyproject.toml
RUN pip install --no-cache-dir /build/auth

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY services/auth/src /app/src
COPY services/auth/alembic.ini /app/alembic.ini
COPY services/auth/alembic /app/alembic

ENV PYTHONPATH=/app/src
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')"

# Phase 1 — Task 1.4: Run Alembic migrations before starting the application
ENTRYPOINT ["sh", "-c", "alembic upgrade head && uvicorn auth.main:app --host 0.0.0.0 --port 8001 --workers 2"]
