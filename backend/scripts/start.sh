#!/bin/sh
# Inicialização da imagem (D1): migra o banco, semeia as contas de demonstração e
# só então sobe o servidor. Se o alembic ou o seed falhar, o `set -e` encerra o
# script e o uvicorn nunca inicia.
set -eu

cd "$(dirname "$0")/.."

alembic upgrade head
python -m app.seed

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
