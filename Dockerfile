# Imagem de produção (AD-28): um só artefato serve a API e a SPA na mesma origem.

# --- Estágio 1: build do front-end -------------------------------------------
FROM node:24-slim AS frontend

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Estágio 2: runtime ------------------------------------------------------
FROM python:3.13-slim AS runtime

# uv com versão fixa (nunca latest).
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /usr/local/bin/uv

# Bytecode compilado no build: em execução a aplicação não grava nada em disco.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/backend/.venv/bin:$PATH"

WORKDIR /app/backend

# Dependências primeiro (camada reaproveitada enquanto os lockfiles não mudam).
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend/app ./app
COPY backend/migrations ./migrations
COPY backend/alembic.ini ./alembic.ini
COPY --chmod=755 backend/scripts/start.sh ./scripts/start.sh

# Build da SPA; o valor de SPA_DIST_DIR é definido aqui, não no código.
COPY --from=frontend /build/frontend/dist /app/frontend-dist
ENV SPA_DIST_DIR=/app/frontend-dist

RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app
USER app

# A porta vem de PORT (Render); o padrão 8000 está no start.sh.
CMD ["./scripts/start.sh"]
