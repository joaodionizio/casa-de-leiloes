#!/bin/sh
# Inicialização da imagem (D1): migra o banco e só então sobe o servidor.
# Se o alembic falhar, o `set -e` encerra o script e o uvicorn nunca inicia.
set -eu

cd "$(dirname "$0")/.."

alembic upgrade head

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
