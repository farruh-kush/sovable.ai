FROM python:3.11-slim AS builder
WORKDIR /build
RUN pip install --no-cache-dir setuptools wheel
COPY shared/ /build/shared/
RUN pip install --no-cache-dir /build/shared
COPY services/billing/ /build/billing/
RUN sed -i 's|ai-routing-shared @ file:///${PROJECT_ROOT}/shared|ai-routing-shared|' /build/billing/pyproject.toml
RUN pip install --no-cache-dir /build/billing

FROM python:3.11-slim AS runtime
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY services/billing/src /app/src
COPY services/billing/alembic.ini /app/alembic.ini
COPY services/billing/alembic /app/alembic
ENV PYTHONPATH=/app/src
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
EXPOSE 8004
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8004/health')"
ENTRYPOINT ["sh", "-c", "alembic upgrade head && uvicorn billing.main:app --host 0.0.0.0 --port 8004 --workers 2"]
