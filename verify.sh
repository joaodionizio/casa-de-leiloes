#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "=== Backend: Ruff check ==="
cd "$REPO_ROOT/backend"
uv run ruff check .

echo "=== Backend: Ruff format --check ==="
uv run ruff format --check .

echo "=== Infra: Docker e PostgreSQL ==="
if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
  echo "verify.sh: Docker não está instalado ou o daemon não está rodando." >&2
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "verify.sh: Docker Compose v2 (docker compose) não está disponível." >&2
  exit 1
fi
cd "$REPO_ROOT"
if ! docker compose up -d --wait postgres; then
  echo "verify.sh: o PostgreSQL não subiu ou não ficou saudável." >&2
  exit 1
fi

# Defaults locais fictícios (compose.yaml); valores já definidos no ambiente vencem.
export DATABASE_URL="${DATABASE_URL:-postgresql://casa:casa_local_dev@127.0.0.1:5432/casa_de_leiloes_dev}"
export TEST_DATABASE_URL="${TEST_DATABASE_URL:-postgresql://casa:casa_local_dev@127.0.0.1:5432/casa_de_leiloes_test}"

echo "=== Backend: pytest ==="
cd "$REPO_ROOT/backend"
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
