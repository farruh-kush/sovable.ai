#!/bin/bash
set -e

echo "🚀 Setting up AI Routing Layer..."

# Setup backend
echo "📦 Setting up backend..."
cd backend
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env.local
cd ..

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. cd backend && source venv/bin/activate"
echo "2. uvicorn ai_routing_layer.main:app --reload"
