FROM python:3.11-slim AS builder
WORKDIR /build
RUN pip install --no-cache-dir setuptools wheel
COPY backend/shared/ /build/shared/
RUN pip install --no-cache-dir /build/shared
COPY microservices/provider/ /build/provider/
RUN sed -i 's|ai-routing-shared @ file:///${PROJECT_ROOT}/shared|ai-routing-shared|' /build/provider/pyproject.toml
RUN pip install --no-cache-dir /build/provider

FROM python:3.11-slim AS runtime
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY microservices/provider/src /app/src
ENV PYTHONPATH=/app/src
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
EXPOSE 8003
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8003/adapt/health')"
CMD ["uvicorn", "provider.main:app", "--host", "0.0.0.0", "--port", "8003", "--workers", "4"]
