# ── Build stage ──────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build tools
RUN pip install --no-cache-dir setuptools wheel

# Copy and install the shared library first (layer caching)
COPY backend/shared/ /build/shared/
RUN pip install --no-cache-dir /build/shared

# Copy and install the gateway service
COPY microservices/gateway/ /build/gateway/
RUN sed -i 's|ai-routing-shared @ file:///${PROJECT_ROOT}/backend/shared|ai-routing-shared|' /build/gateway/pyproject.toml
RUN pip install --no-cache-dir /build/gateway

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source
COPY microservices/gateway/src /app/src

ENV PYTHONPATH=/app/src
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
