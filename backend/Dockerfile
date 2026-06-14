FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends build-essential gcc && rm -rf /var/lib/apt/lists/*

# Copy backend sources
COPY . /app

# Upgrade pip and install editable package with dev extras
RUN pip install --upgrade pip setuptools wheel
RUN pip install -e ".[dev]"
# Ensure multipart for FastAPI forms
RUN pip install python-multipart

# Default: run tests
CMD ["pytest", "-v", "tests"]
