# Casa de Leilões

Leilões online (Desafio Elite Dev, Verzel). Este README ainda é mínimo: cobre só
o banco local. O roteiro completo de avaliação vem em story futura.

## Banco de dados local

Requer Docker com Compose v2. Um contêiner PostgreSQL 18 com dois bancos,
`casa_de_leiloes_dev` e `casa_de_leiloes_test`:

```bash
docker compose up -d --wait postgres
```

Variáveis (veja `backend/.env.example`, valores fictícios):

```bash
export DATABASE_URL=postgresql://casa:casa_local_dev@127.0.0.1:5432/casa_de_leiloes_dev
export TEST_DATABASE_URL=postgresql://casa:casa_local_dev@127.0.0.1:5432/casa_de_leiloes_test
```

Aplicar as migrations no banco de desenvolvimento:

```bash
cd backend && uv run alembic upgrade head
```

Rodar os testes (o banco `_test` é recriado a cada sessão) e a verificação completa:

```bash
cd backend && uv run pytest
./verify.sh
```

O `./verify.sh` fornece URLs locais padrão para `DATABASE_URL` e
`TEST_DATABASE_URL` quando elas não estão definidas no ambiente; valores já
exportados no shell têm precedência. Por isso o verify não depende de
`backend/.env`.

Recriar o volume do zero (apaga os dois bancos; o script de criação só roda com
volume vazio):

```bash
docker compose down -v
```

## Rodar em desenvolvimento

API e front-end em dois terminais. O Vite faz proxy de `/api` e `/health` para
`http://127.0.0.1:8000`, então o navegador vê uma só origem e não há CORS:

```bash
cd backend && uv run uvicorn app.main:app --port 8000
cd frontend && npm run dev
```

A documentação da API fica em `/api/docs` e o esquema em `/api/openapi.json`.

Para servir o build do Vite pelo próprio FastAPI (como em produção), gere o
build e aponte `SPA_DIST_DIR` para ele. Sem a variável, a API sobe normalmente e
a SPA não é servida; com ela apontando para um diretório inválido (inexistente,
arquivo ou sem `index.html`), a aplicação não inicia. Um caminho relativo em
`SPA_DIST_DIR` é resolvido contra o diretório `backend/`, não contra o diretório
atual do processo; na imagem, o valor é absoluto:

```bash
cd frontend && npm run build
cd ../backend && SPA_DIST_DIR=../frontend/dist uv run uvicorn app.main:app --port 8000
```

## Imagem de produção

Um `Dockerfile` multi-stage na raiz (Node 24 para o build do Vite, Python 3.13
com `uv` para a API) gera uma única imagem que serve API e SPA na mesma origem.
O script `backend/scripts/start.sh` roda `alembic upgrade head` e, só se a
migration passar, executa o uvicorn em `0.0.0.0` na porta de `PORT` (padrão
`8000`). A imagem não contém `.env`, nem segredos, nem testes. Contra o
PostgreSQL do Compose:

```bash
docker build -t casa-de-leiloes .
docker run --rm --network casa-de-leiloes_default -p 127.0.0.1:9000:9000 \
  -e PORT=9000 \
  -e DATABASE_URL=postgresql://casa:casa_local_dev@postgres:5432/casa_de_leiloes_dev \
  casa-de-leiloes
```

O `./verify.sh` constrói a imagem (`docker build`), mas não a executa.
