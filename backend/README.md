# AI Routing Layer - Backend Service

Professional microservice-based LLM routing platform backend.

## Quick Start

```bash
# Setup virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Set environment
cp .env.example .env.local
export ENVIRONMENT=local

# Run development server
uvicorn ai_routing_layer.main:app --reload
```

## Environment Configurations

- `.env.example` - Template with all available options
- `.env.local` - Local development (SQLite, mock providers)
- `.env.staging` - Staging environment (PostgreSQL, real APIs)
- `.env.production` - Production environment (RDS, ElastiCache, secrets)

## Project Structure

```
backend/
├── src/ai_routing_layer/
│   ├── services/         # Microservices
│   ├── shared/           # Shared libraries
│   └── infrastructure/   # Infrastructure & config
├── tests/                # Test suite
├── docker/               # Docker configs
├── scripts/              # Helper scripts
├── pyproject.toml        # Python project config
├── .env.example          # Environment template
├── .env.local            # Local dev (git ignored)
└── .gitignore            # Git ignore rules
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

## Docker

```bash
# Build
docker build -f docker/Dockerfile -t routing-layer:latest .

# Run
docker run -p 8000:8000 --env-file .env.local routing-layer:latest
```

## Documentation

See `/docs` folder for:
- Architecture guides
- API reference
- Deployment procedures
- Migration guides
