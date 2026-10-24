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
export APP_ORIGIN=http://localhost:5173
```

`APP_ORIGIN` é a origem pública que a API aceita nas escritas (veja "Erros e
proteção das escritas"). Sem ela, a aplicação não inicia e o `pytest` encerra com
mensagem clara.

`JWT_SECRET` assina o token de sessão (veja "Login e sessão"). Sem ele, com menos
de 32 caracteres, ou com uma `APP_ORIGIN` `http://` fora de `localhost`,
`127.0.0.1` e `::1`, a aplicação não inicia. Eu o ponho no meu `backend/.env`
(a linha `JWT_SECRET=` está em `backend/.env.example`, sem valor); nunca vai para o
repositório. Os testes geram um valor aleatório a cada execução e não usam o do
`.env`.

Aplicar as migrations e semear as contas de demonstração no banco de
desenvolvimento (o seed só precisa de `DATABASE_URL`):

```bash
cd backend && uv run alembic upgrade head
cd backend && uv run python -m app.seed
```

O seed é idempotente: cria só as contas que faltam e nunca altera uma conta que já
existe (nem o hash da senha). Veja "Contas de demonstração".

Rodar os testes (o banco `_test` é recriado a cada sessão) e a verificação completa:

```bash
cd backend && uv run pytest
./verify.sh
```

O `./verify.sh` fornece valores locais padrão para `DATABASE_URL`,
`TEST_DATABASE_URL` e `APP_ORIGIN` (`http://localhost:5173`) quando eles não estão
definidos no ambiente; valores já exportados no shell têm precedência. Por isso o verify não depende de
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
cd backend && APP_ORIGIN=http://localhost:5173 uv run uvicorn app.main:app --port 8000
cd frontend && npm run dev
```

O `JWT_SECRET` vem do `backend/.env` (veja "Banco de dados local"). Sem as contas
semeadas, o login não tem com quem entrar.

O Vite roda na porta fixa 5173 (`strictPort`): se ela estiver ocupada, ele falha
em vez de subir em outra porta, porque o backend só aceita escritas vindas de
`APP_ORIGIN`. Abra o front em `http://localhost:5173`, não em `127.0.0.1`.

A documentação da API fica em `/api/docs` e o esquema em `/api/openapi.json`.

Para servir o build do Vite pelo próprio FastAPI (como em produção), gere o
build e aponte `SPA_DIST_DIR` para ele. Sem a variável, a API sobe normalmente e
a SPA não é servida; com ela apontando para um diretório inválido (inexistente,
arquivo ou sem `index.html`), a aplicação não inicia. Um caminho relativo em
`SPA_DIST_DIR` é resolvido contra o diretório `backend/`, não contra o diretório
atual do processo; na imagem, o valor é absoluto:

```bash
cd frontend && npm run build
cd ../backend && APP_ORIGIN=http://localhost:8000 SPA_DIST_DIR=../frontend/dist uv run uvicorn app.main:app --port 8000
```

## Contas de demonstração

O seed cria três contas, com IDs fixos. **A senha é pública** (qualquer pessoa
entra nas contas demo da URL pública; isso é inerente ao desafio) e igual para as
três:

| E-mail | Papel | Interface |
| --- | --- | --- |
| `auctioneer@example.com` | `AUCTIONEER` | Leiloeiro |
| `bidder1@example.com` | `BIDDER` | Licitante |
| `bidder2@example.com` | `BIDDER` | Licitante |

Senha: `Demo123!`. Não existe cadastro, troca nem recuperação de senha. Para
mudar a senha de uma conta que já existe é preciso agir direto no banco: o seed
nunca altera uma conta existente.

## Login e sessão

`POST /api/auth/login` (e-mail e senha em JSON) devolve `{email, role}` e põe o
token JWT (HS256, 8 horas) num cookie `HttpOnly`, `SameSite=Lax`, `Path=/`, sem
`Domain`, `Max-Age=28800`. O token nunca vai no corpo, na URL nem em
`localStorage`, e o cabeçalho `Authorization` não é aceito. `GET /api/me` devolve
quem está logado e `POST /api/auth/logout` apaga o cookie.

O nome do cookie vem só da `APP_ORIGIN`, sem variável de ambiente nova:

| `APP_ORIGIN` | Cookie | `Secure` |
| --- | --- | --- |
| `https://...` (Render) | `__Host-auction_session` | sim |
| `http://localhost`, `127.0.0.1` ou `[::1]` (desenvolvimento) | `auction_session` | não |
| `http://` com outro host | a aplicação não inicia | |

Cada rota declara uma política de acesso (`PUBLIC`, `OPTIONAL`, `AUTHENTICATED`,
`AUCTIONEER` ou `BIDDER`) pelos helpers de `backend/app/access.py`; um teste
reprova qualquer rota sem política. Sem sessão válida, as rotas autenticadas e por
papel respondem 401; com a sessão do outro papel, 403. Um `AUCTIONEER` nunca dá
lance e um `BIDDER` nunca cria lote.

**Limitações declaradas:**

- O logout só apaga o cookie no navegador. Não há sessão no banco nem revogação:
  um token copiado antes do logout continua válido até o `exp` (8 horas, AD-29).
- Não há limite de tentativas de login nem bloqueio por força bruta.
- Se o `GET /api/me` falhar por indisponibilidade do servidor, a tela mostra o
  formulário com a mensagem de erro; o login só funciona quando o servidor volta.

## Imagem de produção

Um `Dockerfile` multi-stage na raiz (Node 24 para o build do Vite, Python 3.13
com `uv` para a API) gera uma única imagem que serve API e SPA na mesma origem.
O script `backend/scripts/start.sh` roda `alembic upgrade head`, depois
`python -m app.seed` e, só se os dois passarem, executa o uvicorn em `0.0.0.0` na
porta de `PORT` (padrão `8000`). A imagem não contém `.env`, nem segredos, nem testes. Contra o
PostgreSQL do Compose:

```bash
docker build -t casa-de-leiloes .
docker run --rm --network casa-de-leiloes_default -p 127.0.0.1:9000:9000 \
  -e PORT=9000 \
  -e APP_ORIGIN=http://localhost:9000 \
  -e JWT_SECRET=<um-valor-aleatorio-com-32-ou-mais-caracteres> \
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
| Variáveis de ambiente | `DATABASE_URL` (Internal Database URL, colada no painel) |

**Pré-requisitos do próximo deploy (Stories 2.1 e 2.2, ainda não feitos):**
adicionar no painel `APP_ORIGIN=https://casa-de-leiloes-i1xr.onrender.com` e
`JWT_SECRET` (um valor aleatório de pelo menos 32 caracteres, que só existe no
painel e no meu `.env`). Sem qualquer uma das duas a criação da aplicação falha e o
serviço não inicia. `APP_ORIGIN` não é segredo; `JWT_SECRET` é. A branch
configurada no painel ainda é `epic-1`.

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
curl -sS -i "$URL/api/openapi.json"       # 200, JSON, rotas /health, /api/auth/* e /api/me
curl -sS -i "$URL/api/nao-existe"         # 404, JSON (nunca HTML)
```

No navegador, a página inicial mostra "Serviço no ar". Um asset real de
`/assets/` (nome lido do `index.html`) responde 200 com `text/javascript` (JS) e
`text/css` (CSS).

**Cookie de sessão** (Story 2.2; a validar depois do próximo deploy). O cookie
técnico da 1.4 (`__Host-infra_check`) foi removido: `GET /api/infra-check/cookie`
agora responde 404 JSON. Na URL pública, depois de entrar numa conta demo:

```bash
curl -sS -i -c cookies.txt -X POST -H "Origin: $URL" -H 'Content-Type: application/json' \
  -d '{"email":"bidder1@example.com","password":"Demo123!"}' "$URL/api/auth/login"
curl -sS -i -b cookies.txt "$URL/api/me"
```

O login responde 200 com `{"email":"bidder1@example.com","role":"BIDDER"}` e um
`Set-Cookie` de `__Host-auction_session` com `HttpOnly`, `Secure`, `SameSite=lax`,
`Path=/`, `Max-Age=28800` e sem `Domain`. No navegador, o cookie aparece em
Application → Cookies com `Secure`, e `document.cookie` não o mostra.

**WebSocket técnico** (`/api/infra-check/ws`, removido na Story 4.1; é uma rota
`PUBLIC` na política de acesso até lá). No
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

A rota técnica fica fora do OpenAPI e não lê nem grava dados.

**Proteção das escritas** (Story 2.1; a validar depois do próximo deploy, ainda
não executado no Render). Respostas esperadas, pela seção "Erros e proteção das
escritas":

```bash
curl -sS -i -X POST -H 'Origin: https://evil.example' -H 'Content-Type: application/json' -d '{}' "$URL/api/nao-existe"  # 403 csrf_origin_mismatch
curl -sS -i -X POST "$URL/api/nao-existe"                                                                  # 403 csrf_origin_missing
curl -sS -i -X POST -H "Origin: $URL" -H 'Content-Type: text/plain' -d x "$URL/api/nao-existe"             # 415 unsupported_media_type
curl -sS -i -X POST -H "Origin: $URL" -H 'Content-Type: application/json' -d '{}' "$URL/api/nao-existe"    # 405 method_not_allowed (SPA montada)
```

### Limitações observadas

- **O PostgreSQL gratuito expira em 23/11/2026**, data mostrada pelo painel do
  Render.
- Cold start não observado nesta validação. Não houve espera artificial.

## Erros e proteção das escritas

Todo erro da API tem o mesmo formato JSON: `status` (igual ao status HTTP),
`code` (técnico, estável, em inglês) e `message` (em português). Quando há o que
detalhar (hoje, só no 422), há também `details`, uma lista de `{"loc", "type"}`;
sem detalhes, o campo é omitido. A mensagem vem sempre de um catálogo: o texto de
uma exceção nunca é devolvido. O 500 é genérico e o traceback fica só no log do
servidor.

```json
{"status": 403, "code": "csrf_origin_mismatch", "message": "Origem da requisição não permitida."}
```

Em toda escrita (`POST`, `PUT`, `PATCH`, `DELETE`) sob `/api`, antes do roteamento:

1. `Origin` ou `Referer` tem de ser a origem configurada em `APP_ORIGIN` (esquema,
   host e porta; nunca `Host` nem `X-Forwarded-*`). `Origin` presente tem
   precedência; só sem ele o `Referer` é considerado. Sem os dois, 403
   `csrf_origin_missing`. Outra origem, `null` ou valor malformado, 403
   `csrf_origin_mismatch`.
2. `Content-Type` tem de ser `application/json` (aceita `charset`); senão, 415
   `unsupported_media_type`.

`GET`, `HEAD` e `OPTIONS` nunca passam por essa checagem. Não há CORS.

### Comportamentos que podem surpreender

- Toda escrita exige `Content-Type: application/json`, mesmo sem corpo (o logout,
  por exemplo). Um `curl -X POST` sem `-H 'Content-Type: application/json'` e sem
  `Origin` recebe 403.
- Em desenvolvimento, escritas só funcionam pela origem do Vite
  (`http://localhost:5173`, não `127.0.0.1`). O Swagger pelo mesmo caminho,
  `http://localhost:5173/api/docs`, também; direto na porta 8000 as escritas dão 403.
- A proteção vem antes do roteamento. Uma escrita de outra origem em rota
  inexistente recebe 403. Uma escrita da mesma origem sem `Content-Type:
  application/json` em rota inexistente recebe 415. Nos dois casos, a resposta
  vem antes do 404/405.
- Com a SPA montada (imagem/produção), uma escrita válida em rota `/api`
  inexistente recebe 405 `method_not_allowed`, com `Allow` contendo `GET` e `HEAD`,
  e não 404. Isso acontece porque o fallback da SPA (só GET/HEAD) casa com qualquer
  caminho. O `GET` do mesmo caminho continua 404. Sem a SPA (desenvolvimento com o
  Vite), a mesma escrita recebe 404.
- O Swagger documenta o envelope real (`ErrorResponse`) no 401 e no 422 das rotas de
  autenticação, e o schema `HTTPValidationError` do FastAPI não existe. Uma rota
  futura com corpo precisa declarar `error_responses(..., 422)`; um teste reprova
  quem esquecer.
- O traceback de um 500 pode conter texto de exceções do SQLAlchemy, incluindo
  parâmetros da consulta; ele fica apenas no log do servidor.
