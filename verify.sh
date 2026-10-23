#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "=== Backend: Ruff check ==="
cd "$REPO_ROOT/backend"
uv run ruff check .

echo "=== Backend: Ruff format --check ==="
uv run ruff format --check .

echo "=== Backend: pytest ==="
uv run pytest

echo "=== Frontend: lint ==="
cd "$REPO_ROOT/frontend"
npm run lint

echo "=== Frontend: typecheck ==="
npm run typecheck

echo "=== Frontend: build ==="
npm run build

echo ""
echo "verify.sh: todas as etapas passaram."
