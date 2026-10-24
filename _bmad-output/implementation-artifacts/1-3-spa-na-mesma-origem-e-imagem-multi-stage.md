# Story 1.3: SPA na mesma origem e imagem multi-stage

Status: review

Chave do sprint: `1-3-spa-na-mesma-origem-e-imagem-multi-stage`
Épico: 1 (Fundação e aplicação publicada), Dia 2 (23/10) do cronograma
("Dockerfile multi-stage", "frontend mínimo"). O primeiro deploy é da 1.4.
Decisões D1 a D7 fechadas por mim em 24/10/2026 (seção "Decisões registradas").

## Story

Como desenvolvedor,
quero uma única imagem que sirva a API e a SPA na mesma origem, com as
migrations aplicadas antes do tráfego,
para que o mesmo artefato rode localmente e no Render, como base dos cookies do
AD-11.

## Objetivo e contexto

As Stories 1.1 e 1.2 entregaram um FastAPI com `GET /health`, um front-end
React + Vite + TypeScript que só builda, PostgreSQL 18 local com Alembic e
`verify.sh` fail-fast com integração em PostgreSQL real. Hoje o front-end e o
back-end não se conhecem: não há proxy, o FastAPI não serve o `dist` e não
existe `Dockerfile`.

Esta story faz só o empacotamento de produção:

- o FastAPI serve o build do Vite na mesma origem da API (AD-11, AD-14, AD-28),
  a partir de `SPA_DIST_DIR` (D3);
- rotas do cliente devolvem a SPA; nada sob `/api` devolve HTML; `/health`
  nunca é capturado pelo fallback (D4); a documentação OpenAPI passa para
  `/api/docs` e `/api/openapi.json` (D5);
- em desenvolvimento, o front-end fala com a API pelo proxy do Vite, sem CORS
  (D2, AD-29);
- uma página mínima em português mostra o estado do `GET /health`, com o
  contrato tipado em TypeScript (AD-4);
- `Dockerfile` multi-stage na raiz (D7): estágio `node:24-slim` com o build do
  Vite; estágio `python:3.13-slim` com `uv` fixo que copia o `dist` (AD-28);
- um script de inicialização aplica as migrations e só então executa o uvicorn
  com `exec` (D1); a porta vem de `PORT`;
- o `verify.sh` passa a construir a imagem (D6); um smoke test real da imagem
  fecha a story.

Ela prepara a 1.4: o Render só precisará construir esta imagem e fornecer
`DATABASE_URL` e `PORT`.

## Critérios de aceite

CA1 a CA8 vêm do `epics.md` (texto preservado, com o detalhe das decisões).
CA9 a CA14 explicitam as decisões D1 a D7.

1. **CA1 – SPA na raiz.** Dado o build de produção do front-end e
   `SPA_DIST_DIR` apontando para ele, quando acesso `/`, então o FastAPI devolve
   o `index.html` da SPA (200, `text/html`), com uma página mínima em português
   que mostra o estado do `GET /health`.
2. **CA2 – Fallback de rotas do cliente.** Dada uma rota do cliente sem extensão
   no último segmento (por exemplo, `/lots/qualquer-coisa`), quando a acesso
   diretamente com GET ou HEAD, então recebo o `index.html` (200, `text/html`),
   não um 404.
3. **CA3 – `/api` nunca é SPA; `/health` intocado.** Dado `/api` ou um caminho
   inexistente sob `/api/`, quando o chamo com GET ou HEAD, então recebo 404 JSON
   da API (formato padrão do FastAPI; o formato único é da 2.1), nunca HTML; com
   outros métodos, recebo 404 ou 405 JSON, nunca HTML. `GET /health` continua
   200 com exatamente `{"status": "ok"}`, com ou sem SPA configurada.
4. **CA4 – Desenvolvimento sem CORS.** Dado o ambiente de desenvolvimento, quando
   o front-end do servidor do Vite chama `/health` ou `/api/...`, então a
   chamada passa pelo proxy do Vite até o uvicorn local, sem CORS; o back-end não
   registra `CORSMiddleware` em nenhuma configuração.
5. **CA5 – Multi-stage.** Dada a raiz do repositório, quando construo a imagem
   com o `Dockerfile`, então um estágio `node:24-slim` instala as dependências
   pelo `package-lock.json` (`npm ci`) e gera o build do Vite, e o estágio final
   `python:3.13-slim` instala o back-end com `uv` em versão fixa
   (`uv sync --frozen --no-dev`) e copia o `dist`. Não há imagem Alpine.
6. **CA6 – Migrations antes do tráfego.** Dado o contêiner iniciado com a URL de
   um PostgreSQL, quando ele sobe, então o script de inicialização executa
   `alembic upgrade head` e, só se ela terminar com sucesso, executa o uvicorn
   com `exec`; `GET /health` e a SPA respondem; ele escuta em `0.0.0.0` na porta
   de `PORT` (padrão `8000` só quando `PORT` não existe). Se a migration falhar,
   o contêiner termina com código não zero e o uvicorn nunca inicia.
7. **CA7 – Imagem sem segredo e sem estado.** Dada a imagem, quando a reviso,
   então nenhum segredo está embutido (nenhum `.env*`, nenhuma URL de banco em
   `ENV`/`ARG`), não há `node_modules`, `.venv` de desenvolvimento, `.git`,
   caches nem dependências do grupo dev; o processo roda como usuário não root;
   não há `VOLUME` nem arquivo de estado gravado pela aplicação.
8. **CA8 – Testes no `verify.sh`.** Dado `verify.sh`, quando o executo, então há
   testes para a entrega da SPA, o fallback de rotas do cliente e o 404 sob
   `/api/`, e a etapa `docker build` constrói a imagem de produção, falhando o
   `verify` se o build falhar.
9. **CA9 – Assets e `Content-Type`.** Dado um arquivo existente no build
   (`/assets/<hash>.js`, `/assets/<hash>.css`, `/favicon.svg`), quando o peço
   com GET ou HEAD, então recebo o arquivo com o `Content-Type` correto
   (JavaScript, `text/css`, `image/svg+xml`). Dado um caminho cujo último
   segmento tem extensão e que não existe no build (por exemplo,
   `/assets/velho.js`, `/robots.txt`, `/openapi.json`), então recebo 404, nunca
   o `index.html`. Nenhum caminho fora de `SPA_DIST_DIR` é servido (`..` ou
   equivalente codificado).
10. **CA10 – Só leitura.** Dado o fallback da SPA, quando recebe GET ou HEAD,
    então responde sem efeito colateral; POST, PUT, PATCH e DELETE numa rota do
    cliente não devolvem `index.html` (404 ou 405 JSON) (AD-19, AD-29).
11. **CA11 – `SPA_DIST_DIR`.** Dado `SPA_DIST_DIR` ausente, quando a aplicação é
    importada e iniciada, então a API, o `/health` e os testes do back-end
    funcionam normalmente e as rotas da SPA respondem 404; importar `app.main`
    não exige `SPA_DIST_DIR`. Dado `SPA_DIST_DIR` definido, quando o diretório
    não existe, não é diretório ou não contém `index.html`, então a aplicação
    falha na inicialização com mensagem clara e o processo não aceita tráfego. O
    código da aplicação não contém nenhum caminho do Docker; quem define o valor
    na imagem é o `Dockerfile`.
12. **CA12 – OpenAPI em `/api`.** Dada a aplicação, quando acesso `/api/docs` e
    `/api/openapi.json`, então recebo a documentação e o esquema; `/redoc` não
    existe como rota da API; `/docs` e `/openapi.json` na raiz não são mais da
    API (caem nas regras do D4).
13. **CA13 – Página de saúde tipada.** Dada a página mínima, quando o
    `GET /health` responde ok, falha ou ainda não respondeu, então ela mostra
    texto em português para cada estado (não só cor), com URL relativa
    (`/health`) e uma `interface` TypeScript para o contrato
    `{ status: "ok" }` (AD-4, AD-15).
14. **CA14 – Smoke test real da imagem (fechamento).** Dada a imagem construída,
    quando a executo uma vez contra o PostgreSQL local da Story 1.2, então
    registro na story a saída real que prova: o contêiner inicia; as migrations
    rodam antes do uvicorn (ordem dos logs); o servidor escuta na porta de
    `PORT` (valor diferente de `8000`); `GET /health` → 200; `GET /` → SPA;
    rota de cliente → `index.html`; `GET /api/<inexistente>` → 404 JSON; um
    asset real → `Content-Type` adequado; `SPA_DIST_DIR` inválido → falha na
    inicialização; migration impossível → saída não zero sem uvicorn. Nenhum
    contêiner do smoke fica rodando e nada da infraestrutura muda de forma
    persistente.

## ADs aplicáveis

- **AD-4:** React + Vite + TypeScript simples; contrato do `/health` tipado.
- **AD-11:** mesma origem: o FastAPI serve a API e o build do Vite (base dos
  cookies HttpOnly das stories 1.4 e 2.2). Nenhum cookie nesta story.
- **AD-14:** um único Web Service (FastAPI + API + SPA; WebSocket na 1.4/4.1);
  `GET /health`; imagem pronta para o Render gratuito, sem Pre-Deploy Command.
- **AD-28:** monorepo, `uv`, `Dockerfile` multi-stage (Node → Python), FastAPI
  serve a SPA, nenhum estado no filesystem do contêiner.
- **AD-29:** sem CORS permissivo (nem específico de desenvolvimento);
  GET/HEAD/OPTIONS sem efeito colateral.
- **AD-30:** código e rotas em inglês, endpoints técnicos sob `/api`; interface
  em português.
- **AD-2/AD-25 (restrição):** nenhuma rota desta story usa o banco; a entrega de
  arquivos não bloqueia o event loop.
- **AD-27 (restrição):** o `verify.sh` continua fail-fast e ganha só a etapa
  `docker build`.

Nenhuma AD foi alterada.

## Dependências das Stories 1.1 e 1.2 (estado real lido no código)

- `backend/app/main.py`: `app = FastAPI(title="Casa de Leilões")` com `GET /health`
  → `{"status": "ok"}`, sem banco (D6 da 1.2: contrato intocável). `/docs`,
  `/redoc` e `/openapi.json` estão hoje na raiz (mudam pelo D5).
- `backend/app/config.py`: `Settings` com `pydantic-settings`, `DATABASE_URL`
  obrigatória, `TEST_DATABASE_URL` opcional, normalização para
  `postgresql+psycopg`, leitura de `backend/.env` se existir.
- `backend/alembic.ini` + `backend/migrations/env.py`: URL vem de
  `DATABASE_URL`; `alembic upgrade head` executado a partir de `backend/` (onde
  está o `alembic.ini`). Revisão `0001_baseline` vazia. É o comando do script de
  inicialização (D1). Os logs `INFO [alembic...]` saem em stderr pelo
  `alembic.ini`, o que torna a ordem visível no smoke test.
- `backend/tests/conftest.py`: `pytest_sessionstart` exige `TEST_DATABASE_URL`
  e PostgreSQL de pé e recria o banco `_test`. Os testes novos rodam nessa
  sessão sem tocar no banco.
- `backend/tests/test_health.py`: importa `app` de `app.main`; continua
  passando sem alteração.
- `backend/pyproject.toml` / `uv.lock`: deps de runtime `fastapi`,
  `uvicorn[standard]`, `sqlalchemy`, `alembic`, `psycopg[binary]`,
  `pydantic-settings`; grupo dev (`pytest`, `httpx`, `ruff`) fica fora da imagem.
- `frontend/`: React 19, Vite 8, TypeScript 6; `npm run build` = `tsc -b && vite
  build` gera `frontend/dist/`; `vite.config.ts` sem `server.proxy`; `App.tsx`
  só com título e slogan; `index.html` já referencia `/favicon.svg`; sem
  ferramenta de teste do front (Q10).
- `verify.sh`: Ruff → format → Docker/PostgreSQL → `pytest` → lint → typecheck →
  build do Vite. Já exige Docker (1.2).
- `compose.yaml`: só o serviço `postgres` (127.0.0.1:5432, credenciais
  fictícias), na rede padrão do projeto Compose. `.gitignore` já ignora `dist/`,
  `node_modules/`, `.venv/`, `.env*`.
- Versões locais observadas: Node 24.22.1, npm 11.19.1, uv 0.13.5, Docker 29.5.3.

## Tarefas e subtarefas

- [x] **T1 – `SPA_DIST_DIR` (CA11; D3)**
  - [x] T1.1 Ler `SPA_DIST_DIR` (opcional) pela configuração central com
        `pydantic-settings`, de forma que importar `app.main` não passe a exigir
        `DATABASE_URL` nem `SPA_DIST_DIR`.
  - [x] T1.2 Ausente → a SPA não é montada; rotas da SPA respondem 404; log
        informativo de que a SPA não está configurada.
  - [x] T1.3 Definido → validar na criação da aplicação: existe, é diretório e
        contém `index.html`; senão, erro claro (com o motivo, sem segredos) que
        impede o uvicorn de iniciar.
  - [x] T1.4 Nenhum caminho do Docker no código da aplicação.
- [x] **T2 – Entrega da SPA no FastAPI (CA1, CA2, CA3, CA9, CA10; D4)**
  - [x] T2.1 Fábrica `create_app(...)` que recebe o diretório (para os testes) e
        `app = create_app()` em `app/main.py` (para o uvicorn e o
        `test_health.py`).
  - [x] T2.2 Registrar a entrega da SPA depois do `/health` e de qualquer rota
        `/api`, sem sombrear rotas registradas.
  - [x] T2.3 Só GET e HEAD. `/api` e `/api/...` nunca entram no fallback:
        404 JSON (GET/HEAD), 404 ou 405 JSON (outros métodos).
  - [x] T2.4 Arquivo existente dentro de `SPA_DIST_DIR` → servido com o
        `Content-Type` adequado (`FileResponse`/`StaticFiles` do Starlette).
  - [x] T2.5 Último segmento com extensão e arquivo inexistente → 404.
  - [x] T2.6 Último segmento sem extensão → `index.html`.
  - [x] T2.7 Caminho resolvido fora de `SPA_DIST_DIR` (inclusive codificado) →
        nunca servido.
- [x] **T3 – OpenAPI (CA12; D5)**
  - [x] T3.1 `docs_url="/api/docs"`, `openapi_url="/api/openapi.json"`,
        `redoc_url=None`.
- [x] **T4 – Front-end (CA4, CA13; D2)**
  - [x] T4.1 `server.proxy` no `vite.config.ts` para `/api` e `/health`,
        apontando para o uvicorn local (`http://127.0.0.1:8000`).
  - [x] T4.2 `interface HealthResponse` e `fetchHealth(): Promise<HealthResponse>`
        com URL relativa, em um módulo de API simples.
  - [x] T4.3 `App.tsx` mostra "Verificando o serviço…", "Serviço no ar" ou
        "Não foi possível falar com o servidor", em texto.
- [x] **T5 – Imagem (CA5, CA6, CA7, CA11; D1, D7)**
  - [x] T5.1 `Dockerfile` na raiz. Estágio `frontend`: `node:24-slim`,
        `npm ci` com o `package-lock.json` existente, `npm run build`.
  - [x] T5.2 Estágio final: `python:3.13-slim`; binário do `uv` copiado de
        `ghcr.io/astral-sh/uv:<versão fixa>` (preferência: a mesma versão local,
        0.13.5); `uv sync --frozen --no-dev` usando `pyproject.toml` e
        `uv.lock`; código de `backend/` (app, migrations, `alembic.ini`, script);
        `dist` copiado do estágio `frontend`.
  - [x] T5.3 `ENV SPA_DIST_DIR=<diretório para onde o dist foi copiado>`;
        nenhuma URL de banco nem segredo em `ENV`/`ARG`.
  - [x] T5.4 Usuário não root; sem `VOLUME`; nada gravado pela aplicação no
        filesystem.
  - [x] T5.5 Script de inicialização (por exemplo, `backend/scripts/start.sh`),
        com `set -eu`: `alembic upgrade head` a partir de `backend/`; depois
        `exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"`.
        Falha da migration encerra o script com código não zero. Sem migration
        no `lifespan`.
  - [x] T5.6 `.dockerignore` na raiz: `.env*`, `.git`, `**/node_modules`,
        `**/.venv`, `**/dist`, caches (`__pycache__`, `.pytest_cache`,
        `.ruff_cache`), `_bmad`, `_bmad-output`, `.claude`, `docs`, `.DS_Store`.
- [x] **T6 – Testes (CA2, CA3, CA8, CA9, CA10, CA11, CA12)** — ver "Testes
      esperados".
- [x] **T7 – `verify.sh` (CA8; D6)**
  - [x] T7.1 Nova etapa `=== Imagem: docker build ===` depois do build do Vite,
        a partir da raiz, com tag local fixa (por exemplo,
        `casa-de-leiloes:verify`); falha do build falha o `verify`.
  - [x] T7.2 Sem `docker run` no `verify.sh`; demais etapas e ordem mantidas.
- [x] **T8 – Documentação**
  - [x] T8.1 `README.md`: rodar API (uvicorn) + front (Vite com proxy) em
        desenvolvimento; `SPA_DIST_DIR` para servir o build pelo FastAPI;
        construir e rodar a imagem contra o PostgreSQL do Compose; mecanismo das
        migrations (script de inicialização). README completo segue na 1.4/6.3.
  - [x] T8.2 `docs/uso_de_ia.md` com a Story 1.3.
- [x] **T9 – Fechamento**
  - [x] T9.1 Verificação manual do proxy do Vite (uvicorn + `npm run dev`):
        `/health` e `/api/<inexistente>` pela porta do Vite chegam ao FastAPI;
        saída real registrada.
  - [x] T9.2 `verify.sh` completo com a saída real, incluindo o `docker build`.
  - [x] T9.3 Smoke test real da imagem (CA14), conforme "Smoke test de
        fechamento", com a saída real registrada nesta story.
  - [x] T9.4 Confirmar que nenhum contêiner do smoke ficou rodando
        (`docker ps`).
  - [x] T9.5 Parar e avisar. Sem git.

## Arquivos e áreas esperados

| Área | Arquivo | Ação |
| --- | --- | --- |
| App | `backend/app/main.py` | alterado (fábrica, D5, montagem da SPA) |
| App | `backend/app/spa.py` (ou nome equivalente) | novo (validação de `SPA_DIST_DIR` e fallback) |
| Config | `backend/app/config.py` | alterado (`SPA_DIST_DIR`) |
| Script | `backend/scripts/start.sh` (ou nome equivalente) | novo (D1) |
| Testes | `backend/tests/test_spa.py` (e, se separado, `test_openapi.py`) | novo |
| Testes | `backend/tests/test_health.py` | intocado |
| Front | `frontend/src/App.tsx`, `frontend/src/App.css`, `frontend/src/api/health.ts` (ou equivalente) | alterado / novo |
| Front | `frontend/vite.config.ts` | alterado (proxy) |
| Imagem | `Dockerfile`, `.dockerignore` (raiz) | novo |
| Verify | `verify.sh` | alterado (`docker build`) |
| Docs | `README.md`, `docs/uso_de_ia.md` | alterado |
| Story | este arquivo, `sprint-status.yaml` | alterado no fechamento |
| Sem mudança | `compose.yaml`, `backend/migrations/**`, `backend/tests/conftest.py`, `backend/pyproject.toml`, `backend/uv.lock`, `frontend/package*.json` | intocados (nenhuma dependência nova prevista) |

## Testes esperados

Unitários com `TestClient` e um `dist` temporário criado pelo teste
(`index.html`, `assets/app.js`, `assets/app.css`, `favicon.svg`), sem depender
do build real nem do banco:

| Teste | Prova |
| --- | --- |
| `GET /` → 200 `text/html` com o conteúdo do `index.html` | CA1 |
| `GET /lots/qualquer-coisa` e `GET /lots/1/audit` → 200 `index.html` | CA2 |
| `HEAD /lots/qualquer-coisa` → 200 sem corpo | CA2, CA10 |
| `GET /api`, `GET /api/nao-existe`, `GET /api/lots/x/y` → 404 JSON, sem HTML | CA3 |
| `POST /api/nao-existe` → 404 ou 405 JSON, sem HTML | CA3 |
| `GET /health` → 200 `{"status": "ok"}` com a SPA montada e sem SPA | CA3 |
| `GET /assets/app.js` → 200 com `Content-Type` JavaScript | CA9 |
| `GET /assets/app.css` → 200 `text/css`; `GET /favicon.svg` → `image/svg+xml` | CA9 |
| `GET /assets/velho.js`, `GET /robots.txt`, `GET /openapi.json` → 404, sem HTML | CA9, CA12 |
| `GET /%2e%2e/...` / `..` codificado → nunca serve arquivo fora do `dist` | CA9 |
| `POST`/`PUT`/`PATCH`/`DELETE /lots/x` → 404 ou 405, nunca `index.html` | CA10 |
| `SPA_DIST_DIR` ausente: app criada, `/health` 200, `GET /` e `/lots/x` → 404 | CA11 |
| `SPA_DIST_DIR` inexistente, apontando para arquivo, ou sem `index.html` → erro claro na criação da app | CA11 |
| Importar `app.main` sem `SPA_DIST_DIR` não falha | CA11 |
| `GET /api/docs` → 200 HTML; `GET /api/openapi.json` → 200 JSON; `GET /redoc` não é a doc | CA12 |
| `test_health.py` existente, sem alteração | CA3 |

Verificações executadas (saída real registrada nesta story):

| Verificação | Como | Prova |
| --- | --- | --- |
| ESLint, `tsc --noEmit`, build do Vite com a página nova | `verify.sh` (existente) | CA13 |
| `docker build` da imagem de produção | `verify.sh` (etapa nova) | CA5, CA8 |
| Proxy do Vite | manual, T9.1 | CA4 |
| Smoke test real da imagem | manual, T9.3 | CA6, CA7, CA11, CA14 |

Nenhum teste automatizado de front-end novo (ferramenta segue indefinida, Q10).

## Alterações no `verify.sh`

```
Backend:  Ruff check
Backend:  Ruff format --check
Infra:    docker compose up -d --wait postgres
Backend:  pytest            ← inclui os testes novos da SPA, sem etapa nova
Frontend: lint → typecheck → build
Imagem:   docker build      ← nova (D6); sem docker run
```

## Smoke test de fechamento (CA14)

Executado uma vez pelo agente, com a saída real colada nesta story:

1. `docker compose up -d --wait postgres` (infra da 1.2, sem alteração).
2. Rodar a imagem com `docker run --rm` na rede padrão do projeto Compose,
   `DATABASE_URL` apontando para `postgres:5432/casa_de_leiloes_dev`
   (credenciais fictícias do `compose.yaml`; só `upgrade`, como na 1.2),
   `PORT` diferente de `8000` (por exemplo, `9000`) publicada em `127.0.0.1`.
3. Logs: linhas do Alembic antes de "Started server process"/"Uvicorn running
   on http://0.0.0.0:<PORT>".
4. `curl -i`: `/health` (200 JSON), `/` (200 `text/html`), `/lots/x` (200
   `index.html`), `/api/nao-existe` (404 JSON), um asset real de
   `/assets/...` (`Content-Type` adequado), `/api/docs` (200).
5. Negativos: (a) `SPA_DIST_DIR` apontando para diretório inexistente → saída
   não zero com mensagem clara; (b) `DATABASE_URL` para um banco inexistente
   ou host inalcançável → saída não zero, sem linha do uvicorn.
6. Parar o contêiner principal; `docker ps` sem contêineres do smoke. Nenhuma
   alteração em `compose.yaml`, volumes ou rede persistente.

## Fora de escopo

- Deploy no Render, `render.yaml`, variáveis no painel, cold start (Story 1.4).
- WebSocket (verificação de infraestrutura na 1.4; sala na 4.1) e proxy do
  WebSocket no Vite (entra com a rota, Q10). Cookie de verificação (1.4).
  `--proxy-headers`/`forwarded-allow-ips` do uvicorn: avaliar na 1.4.
- Autenticação, JWT, papéis, seed, lotes, carteira, lances, scheduler,
  catch-up. Q4 continua aberta: o `lifespan` fica livre para o catch-up e o
  seed rodarem antes do tráfego no futuro.
- Formato único de erro e validação de `Origin` (2.1).
- Roteador do cliente (React Router ou similar): entra com a primeira tela com
  rota.
- Cabeçalhos de cache e compressão dos assets; identidade visual (6.2).
- Ferramenta de teste do front-end (Q10).
- `docker run` dentro do `verify.sh`; aplicação dentro do `compose.yaml`.
- `StarletteDeprecationWarning` herdado.

## Questões da arquitetura (Q1 a Q10) nesta story

Nenhuma foi respondida aqui. Q4 só existe quando houver catch-up e seed (o D1
mantém o `lifespan` livre para isso). Os itens da Q10 ainda abertos (rota do
WebSocket, rotas do comprovante, segredo do JWT, ferramenta de teste do front)
não são usados nesta story.

## Decisões registradas

Todas tomadas por mim em 24/10/2026.

### D1 – Migrations por script de inicialização da imagem
**Decidi** que a imagem tem um script de inicialização que executa
`alembic upgrade head` e, só se a migration terminar com sucesso, executa o
uvicorn com `exec`. Se a migration falhar, o processo encerra e o servidor nunca
começa a aceitar tráfego.
**Por quê:** a falha da migration aparece antes de abrir a porta, o uvicorn vira
o processo principal do contêiner e a mesma imagem migra sozinha localmente e no
Render. O `lifespan` do FastAPI fica livre para o catch-up e o seed (Q4).
**Descartei:** migration no `lifespan` do FastAPI (importar ou iniciar a app nos
testes passaria a migrar o banco, e o log do Alembic se misturaria ao do
uvicorn) e o Pre-Deploy Command do Render (o serviço gratuito que escolhi não
oferece esse recurso, e a imagem local não migraria sozinha).

### D2 – Proxy do Vite em desenvolvimento
**Decidi** usar o proxy do Vite para `/api` e `/health`. Não adiciono CORS
permissivo nem CORS específico de desenvolvimento. Em produção, SPA e API ficam
na mesma origem.
**Por quê:** o navegador vê uma só origem também em desenvolvimento, mantenho o
hot reload e o back-end não ganha nenhum caminho de CORS que possa vazar para
produção ou complicar os cookies `SameSite` (AD-29).
**Descartei:** só usar o build servido pelo FastAPI em desenvolvimento (sem hot
reload) e CORS restrito a `localhost:5173` em desenvolvimento.

### D3 – `SPA_DIST_DIR`, opcional em desenvolvimento e obrigatório na imagem
**Decidi** configurar o build da SPA por `SPA_DIST_DIR`, sem caminho do Docker
codificado na aplicação. Quando a variável não existe (desenvolvimento e
testes), a API, o `/health` e os testes funcionam normalmente e as rotas da SPA
podem responder 404, sem quebrar imports. Quando ela existe, o diretório e o
`index.html` são obrigatórios: se estiverem ausentes ou inválidos, a aplicação
falha claramente na inicialização. O `Dockerfile` define `SPA_DIST_DIR` para o
diretório onde copia o build do Vite.
**Por quê:** não quero que uma imagem de produção sem SPA seja considerada
saudável só com um aviso no log. A presença da variável é o que distingue os
casos, sem criar uma noção de ambiente (`APP_ENV`) que ainda não existe.
**Descartei:** variável com padrão local `frontend/dist` e apenas aviso quando o
diretório falta (produção quebrada pareceria saudável); exigir o build sempre
(o `pytest` e o uvicorn local dependeriam do build do front); caminho fixo no
código.
**Consequência:** a validação acontece depois das migrations no script do D1;
se `SPA_DIST_DIR` estiver errado, a migration já terá rodado, mas o processo não
atende tráfego. Na imagem, o `COPY` do `dist` já falha o build se o diretório
não existir.

### D4 – Fallback só para GET e HEAD, com 404 para arquivo inexistente
**Decidi:** fallback só para GET e HEAD; `/api` e `/api/*` nunca entram no
fallback; `/health` continua a rota explícita existente; arquivo existente no
build é servido com o `Content-Type` correto; caminho com extensão e inexistente
→ 404; rota de cliente sem extensão → `index.html`; métodos de escrita nunca
recebem `index.html`.
**Por quê:** um asset ausente depois de um deploy aparece como 404 real, não como
HTML com tipo errado; o namespace da API nunca devolve HTML; leituras não têm
efeito colateral (AD-19, AD-29).
**Descartei:** devolver `index.html` para tudo que não fosse `/api` nem arquivo
existente (um `.js` ausente receberia HTML e o navegador mostraria erro de MIME
confuso).

### D5 – OpenAPI em `/api`
**Decidi** usar `/api/docs` e `/api/openapi.json` e desativar o Redoc.
**Por quê:** os endpoints técnicos da API ficam dentro de `/api`, a raiz pertence
à SPA (exceto `/health`) e evito conflito futuro com rotas do cliente.
**Descartei:** manter `/docs`, `/redoc` e `/openapi.json` na raiz e desligar a
documentação em produção (exigiria noção de ambiente e tiraria uma ferramenta
útil do avaliador; a 6.1 pode reavaliar a exposição).

### D6 – `docker build` no `verify.sh` e smoke test real no fechamento
**Decidi** acrescentar ao `verify.sh` uma etapa `docker build`, para provar
continuamente que a imagem de produção constrói. Não coloco `docker run` no
`verify.sh` nesta story. Antes de concluir a story, o agente executa uma vez um
smoke test real da imagem contra o PostgreSQL local da 1.2, registra a saída e
não deixa contêineres rodando.
**Por quê:** um `Dockerfile` quebrado não pode passar despercebido até o build do
Render, mas o ciclo de vida e a rede de um contêiner em toda execução do
`verify` acrescentariam complexidade e fragilidade.
**Descartei:** só passo manual, sem `docker build` no `verify` (o `Dockerfile`
quebraria sem eu perceber), e `docker run` completo no `verify` (lento, frágil,
migraria o banco de dev a cada execução).

### D7 – Imagem `node:24-slim` + `python:3.13-slim` com `uv` fixo
**Decidi:**
- build do front em `node:24-slim` (Node 24, linha LTS escolhida), com
  instalação reprodutível pelo lockfile existente (`npm ci`) e build de produção
  do Vite;
- runtime em `python:3.13-slim`, só com as dependências da aplicação
  (`uv sync --frozen --no-dev`), `uv` com versão fixada explicitamente no
  `Dockerfile` (nunca `latest`), usuário não root, porta `${PORT:-8000}` (sem
  codificar a porta do Render), `.dockerignore`;
- nenhum `.env`, segredo, `node_modules` ou artefato desnecessário na imagem;
  nenhum estado persistente da aplicação no filesystem do contêiner.

**Por quê:** imagem enxuta e reproduzível pelos lockfiles, com as mesmas versões
principais do desenvolvimento (Node 24, Python 3.13).
**Descartei:** Alpine (com `musl`, wheels como a do `psycopg[binary]` podem
falhar ou exigir compilação) e `uv` instalado por `pip` ou em `latest` (versão
não controlada).

## Notas para o desenvolvedor

- Não acrescente dependências: `FileResponse`/`StaticFiles` vêm do Starlette.
- Ao resolver caminhos, compare o caminho resolvido com o `SPA_DIST_DIR`
  resolvido; não confie só em checagem de string.
- O `Content-Type` depende do módulo `mimetypes`; confirme `.js`, `.css` e
  `.svg` no smoke test, porque a imagem `slim` pode não ter `/etc/mime.types`.
- `alembic upgrade head` precisa rodar no diretório do `alembic.ini`
  (`prepend_sys_path = .` resolve `app.*`).
- Nunca logar `DATABASE_URL`. Nunca ler, imprimir nem copiar `.env*` reais.
- `backend/.env` local pode definir `SPA_DIST_DIR`; os testes passam o diretório
  pela fábrica e não dependem disso.
- `SPA_DIST_DIR` relativo é resolvido contra `BACKEND_DIR` (validador de
  `SpaSettings`), nunca contra o diretório atual do processo; caminho absoluto, como
  o da imagem, fica como está.

## Referências

- `_bmad-output/planning-artifacts/epics.md`, Story 1.3.
- `docs/ARQUITETURA.md`: AD-4, AD-11, AD-14, AD-19, AD-27, AD-28, AD-29, AD-30;
  questões 4 e 10.
- `docs/CRONOGRAMA.md`: Dia 2.
- `_bmad-output/implementation-artifacts/1-2-postgresql-com-bancos-isolados-e-migrations.md`
  (D4, D6, D8).

## Registro do desenvolvedor (implementação, 24/10/2026)

### Arquivos
Criados: `backend/app/spa.py`, `backend/scripts/start.sh`,
`backend/tests/test_spa.py`, `backend/tests/test_openapi.py`,
`frontend/src/api/health.ts`, `Dockerfile`, `.dockerignore`.
Alterados: `backend/app/config.py` (`BACKEND_DIR`, `ENV_FILE`, `SpaSettings`,
`get_spa_settings`), `backend/app/main.py` (`create_app`, D5), `frontend/vite.config.ts`
(proxy), `frontend/src/App.tsx`, `frontend/src/App.css`, `verify.sh`, `README.md`,
`docs/uso_de_ia.md`. Intocados: `compose.yaml`, migrations, `conftest.py`,
`test_health.py`, `pyproject.toml`, `uv.lock`, `package*.json`.

### Desvios e observações
- `create_app(spa_dist_dir=None)` lê `get_spa_settings()` quando recebe `None`; os
  testes de "SPA ausente" substituem `get_spa_settings` em `app.main`.
- Os dois negativos do smoke rodaram em contêineres sem `--rm` (nome fixo, `docker rm`
  explícito) para poder ler os logs depois da saída. O negativo A foi repetido uma
  vez só para capturar as linhas do Alembic, que a primeira captura (`tail`) cortou.
- `docker stop` do contêiner principal terminou com exit code 0 e as linhas
  "Shutting down / Application shutdown complete".
- Uma resposta a HEAD não tem corpo; o teste de `HEAD /health` confere o
  `Content-Type` JSON e o `Allow: GET`, não o corpo.

### Proxy do Vite (T9.1, CA4)
uvicorn em `127.0.0.1:8000` e `npm run dev` em `127.0.0.1:5173`; `curl` pela porta do Vite:
`/health` → `200 application/json {"status":"ok"}`; `/api/nao-existe` →
`404 application/json {"detail":"Not Found"}`; `/api/docs` → `200`. Os três pedidos
aparecem no log do uvicorn. Os dois processos foram encerrados e as portas ficaram livres.

### Smoke test da imagem (T9.3, CA14)
Rede do PostgreSQL do Compose: `casa-de-leiloes_default` (alias `postgres`, `healthy`).
`DATABASE_URL=postgresql://casa:***@postgres:5432/casa_de_leiloes_dev`, `PORT=9000`.

Ordem dos logs (migration antes do uvicorn; o banco de dev já estava no `head`):
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:9000 (Press CTRL+C to quit)
```
Respostas (`curl -i`):
- `GET /health` → `200`, `application/json`, `{"status":"ok"}`
- `GET /` → `200`, `text/html; charset=utf-8` (469 bytes, o `index.html` do build)
- `GET` e `HEAD /lots/x` → `200`, `text/html; charset=utf-8`
- `GET /api/nao-existe` → `404`, `application/json`, `{"detail":"Not Found"}`
- `HEAD /health` → `405`, `allow: GET`, `application/json`
- `/assets/index-Du5uwTvN.js` → `200`, `text/javascript; charset=utf-8`
- `/assets/index-Bd_ia25c.css` → `200`, `text/css; charset=utf-8`
- `/favicon.svg` → `200`, `image/svg+xml`
- `/assets/velho.js` → `404`, `application/json`
- `/api/docs` → `200`, `text/html`; `/api/openapi.json` → `200`, `application/json`

Imagem (`docker exec` / `docker image inspect`): processo 1 é
`/app/backend/.venv/bin/uvicorn`, `uid=10001(app)`; `User=app`, `Volumes=map[]`;
`ENV` só com `SPA_DIST_DIR=/app/frontend-dist` e variáveis de build/Python, sem URL de
banco; nenhum `.env*`, `tests`, `node_modules` ou `.git` encontrado; `import pytest` e
`import ruff` falham (grupo dev fora); a SPA é legível pelo usuário `app`, e
`touch` em `/app/frontend-dist` e `/app/backend` dá `Permission denied`.
`docker stop` → exit code 0, "Shutting down" … "Finished server process [1]".

Negativo A (`SPA_DIST_DIR=/nao/existe`, banco válido): exit code 1; linhas do Alembic
primeiro; depois `app.spa.SpaConfigError: SPA_DIST_DIR does not exist: /nao/existe`;
nenhuma linha "Uvicorn running" nem "Application startup complete".

Negativo B (banco `banco_que_nao_existe`, SPA válida): exit code 1;
`sqlalchemy.exc.OperationalError ... database "banco_que_nao_existe" does not exist`;
zero ocorrências de "Uvicorn", "Started server" ou `SpaConfigError`.

Cleanup: `docker ps -a --filter name=casa-smoke` vazio; só o `postgres` do Compose segue
rodando. `compose.yaml`, volumes e rede não foram alterados.

### `./verify.sh` final (T9.2)
Uma única execução completa. Ruff, format, PostgreSQL, `pytest` (69 passed, 1 warning:
`StarletteDeprecationWarning` herdado), ESLint, `tsc --noEmit`, build do Vite e
`docker build -t casa-de-leiloes:verify .` passaram; última linha:
`verify.sh: todas as etapas passaram.` O código de saída não foi capturado
separadamente (o `echo` de status foi mal escrito para o zsh); a mensagem final só é
impressa com `set -euo pipefail` se nenhuma etapa falhou.

### Correções do review (24/10/2026)
Três findings aprovados, sem mudança de escopo nem de AD:

1. **`SPA_DIST_DIR` relativo.** Em `backend/app/config.py`, um validador de `SpaSettings`
   prefixa `BACKEND_DIR` a caminhos relativos; caminhos absolutos (o da imagem) e a
   variável ausente não mudam. `SPA_DIST_DIR=../frontend/dist` aponta para o mesmo lugar
   de onde quer que o uvicorn seja iniciado. O `verify.sh` não define `SPA_DIST_DIR` e o
   teste novo muda o cwd de propósito, então nada depende do diretório atual.
2. **Normalização antes das guardas do fallback.** Em `backend/app/spa.py`,
   `normalize_route_path` (`posixpath.normpath` sobre o caminho com `/` na frente) decide
   se o pedido é `api`, `api/*` ou `health`. `/health/` e `/lots/../api/x` passaram a dar
   404 JSON em vez de `index.html`; `HEAD /health` continua 405 com `Allow: GET`; sem
   redirecionamento. O arquivo continua sendo procurado pelo caminho original dentro de
   `resolve_inside`, então a proteção contra traversal e symlink não mudou.
3. **Fallback é a última rota.** `SPA_FALLBACK_PATH` é usado no decorador e em um teste
   que exige exatamente uma rota com esse caminho e que ela seja a última de `app.routes`;
   sem SPA configurada ela não existe.

Testes escritos antes das correções: 9 falharam no código anterior (`/health/` GET e
HEAD, três variantes de `/api` normalizado em GET e em HEAD, e o caminho relativo). Depois
das correções, `test_spa.py`, `test_openapi.py`, `test_health.py` e `test_config.py`:
87 passed. Os dois arquivos novos têm 77 testes (49 + 28 do review); o "50" do registro
da `uso_de_ia.md` contava também o `test_health.py`.

`./verify.sh` completo, uma única execução depois das correções: código de saída 0 (agora
capturado), Ruff check e format ok, `pytest` 97 passed e 1 warning (o mesmo
`StarletteDeprecationWarning`), ESLint, `tsc --noEmit`, build do Vite e `docker build`
passaram; última linha `verify.sh: todas as etapas passaram.` Não rodei o smoke da imagem
de novo: o `Dockerfile` e o `start.sh` não mudaram, só o código Python da aplicação.
Não alterei o caso `"/../secret.txt"`.
