# Casa de Leilões

Leilões online (Desafio Elite Dev, Verzel). Este README ainda é parcial: cobre o
desenvolvimento local, o PostgreSQL local, a imagem Docker e a preparação do deploy
no Render. O roteiro completo de avaliação vem em story futura.

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

## Deploy no Render

O primeiro deploy foi feito na Story 1.4, pelo painel do Render
(sem `render.yaml`): um Web Service Docker e um PostgreSQL, ambos no plano
gratuito e na região Virginia (US East).

URL pública: <https://casa-de-leiloes-i1xr.onrender.com>

### Configuração usada

| Item | Valor |
| --- | --- |
| Banco | PostgreSQL 18, `casa-de-leiloes-db`, plano Free |
| Web Service | runtime Docker, `Dockerfile` da raiz, plano Free |
| Branch | `epic-1` (trocar para `main` depois do merge do épico) |
| Auto-Deploy | Off: todo deploy é manual (Manual Deploy → Deploy latest commit) |
| Health Check Path | `/health` |
| Variáveis de ambiente | só `DATABASE_URL` (Internal Database URL, colada no painel) |

O valor de `DATABASE_URL` existe apenas no painel do Render. `PORT` é injetada
pelo Render e `SPA_DIST_DIR` já vem da imagem. Não há CORS (API, SPA e WebSocket
usam a mesma origem), disco persistente, Pre-Deploy Command nem Docker Command:
vale o `CMD` da imagem, que roda `alembic upgrade head` e só depois o uvicorn.

No primeiro deploy, o log mostrou o build da imagem, o Alembic conectando ao
PostgreSQL e aplicando `0001` (baseline) antes de o uvicorn subir em
`0.0.0.0:10000`; o serviço ficou `Live` e `/health` respondeu 200. Em um
redeploy manual do mesmo commit, o Alembic rodou de novo sem reaplicar a `0001`.

### Como validar

Com `URL=https://casa-de-leiloes-i1xr.onrender.com`:

```bash
curl -sS -i "$URL/health"                 # 200, {"status":"ok"}
curl -sS -i "$URL/"                       # 200, text/html (SPA)
curl -sS -i "$URL/lots/qualquer-coisa"    # 200, text/html (index.html)
curl -sS -i "$URL/api/docs"               # 200, Swagger
curl -sS -i "$URL/api/openapi.json"       # 200, JSON, só /health no schema
curl -sS -i "$URL/api/nao-existe"         # 404, JSON (nunca HTML)
```

No navegador, a página inicial mostra "Serviço no ar". Um asset real de
`/assets/` (nome lido do `index.html`) responde 200 com `text/javascript` (JS) e
`text/css` (CSS).

**Cookie técnico** (`__Host-infra_check`, removido na Story 2.2). A primeira
chamada responde `{"cookie_received": false}` com o `Set-Cookie`; a segunda, no
mesmo cliente, responde `true`:

```bash
curl -sS -i -c cookies.txt "$URL/api/infra-check/cookie"
curl -sS -i -b cookies.txt "$URL/api/infra-check/cookie"
```

O cookie vem com `HttpOnly`, `Secure`, `SameSite=lax`, `Path=/`, `Max-Age=600`
e sem `Domain`. O cabeçalho real emitido pelo Starlette é `SameSite=lax`, em
minúsculas; para o navegador o atributo não diferencia maiúsculas de
minúsculas, então equivale a `Lax`. Por ser `HttpOnly`,
`document.cookie.includes('__Host-infra_check')` dá `false`.

**WebSocket técnico** (`/api/infra-check/ws`, removido na Story 4.1). No
console do navegador, na própria URL pública:

```js
const ws = new WebSocket(`wss://${location.host}/api/infra-check/ws`)
ws.onopen = () => ws.send('ping')
ws.onmessage = (e) => console.log('recebido:', e.data)
ws.onclose = (e) => console.log('fechado:', e.code)
```

Ou pelo terminal, com o pacote `websockets` que já vem com o `uvicorn[standard]`:

```bash
cd backend && uv run python -c "
import asyncio, websockets
async def main(url):
    async with websockets.connect(url) as ws:
        await ws.send('ping'); print(await ws.recv())
asyncio.run(main('wss://casa-de-leiloes-i1xr.onrender.com/api/infra-check/ws'))"
```

Os dois imprimem `echo:ping`. Na validação pública, o handshake `wss://` abriu
(HTTP 101) e o tráfego funcionou nos dois sentidos. Nos dois clientes
(console do Edge e `websockets`), o encerramento foi observado como `1006`,
sem motivo, embora o código envie `close(1000)` depois do eco e, nos testes
locais, o fechamento seja `1000`. Não determinei a causa dessa diferença e não
a trato como comportamento garantido do Render.

As duas rotas técnicas ficam fora do OpenAPI e não leem nem gravam dados.

### Limitações observadas

- **O PostgreSQL gratuito expira em 23/11/2026**, data mostrada pelo painel do
  Render.
- Cold start não observado nesta validação. Não houve espera artificial.
