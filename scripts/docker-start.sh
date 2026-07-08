#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: Docker is not installed or not in PATH."
    exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
    echo "ERROR: Docker Compose v2 is not available."
    exit 1
fi

ENV_FILE="$ROOT/multiagentchat/.env"
ENV_EXAMPLE="$ROOT/multiagentchat/.env.example"

if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$ENV_EXAMPLE" ]; then
        echo "Creating multiagentchat/.env from .env.example..."
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        echo "IMPORTANT: Edit multiagentchat/.env and set OPENAI_API_KEY before crew runs."
    else
        echo "ERROR: multiagentchat/.env.example not found."
        exit 1
    fi
fi

PROFILE="${1:-}"
if [ "$PROFILE" = "observability" ]; then
    echo "Starting with observability profile..."
    docker compose --profile observability up --build -d
else
    docker compose up --build -d
fi

echo ""
echo "Services starting. Validate with:"
echo "  curl http://localhost:8000/health"
echo "  curl http://localhost:3000/api/health"
echo "  open http://localhost:3000"
echo ""
echo "Logs: docker compose logs -f backend frontend"
