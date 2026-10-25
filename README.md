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

## Catálogo do Art Institute of Chicago

O leiloeiro (`AUCTIONEER`) escolhe a obra que vai virar lote num catálogo real de
domínio público. Esta etapa só **busca e mostra**: não cria lote nem grava nada no
banco (a criação vem na Story 2.4).

- `GET /api/catalog/artworks?q=termo`: até 20 obras mais relevantes, só
  `is_public_domain=true` e com imagem. Sem paginação. O termo tem de 1 a 100
  caracteres depois de `strip`. O acervo está em inglês.
- `GET /api/catalog/artworks/{external_id}`: o detalhe com os campos que a Story 2.4
  vai copiar para o lote. Obra inexistente, fora do domínio público ou sem imagem
  dá o mesmo `404 not_found`.
- A busca e o detalhe só aceitam o leiloeiro: sem login, 401; licitante, 403. Nos dois
  casos a AIC nem é chamada. A resposta nunca é o JSON da AIC, e sempre sai com
  `Cache-Control: no-store`.
- O servidor monta a consulta (`bool` com `multi_match`, domínio público e imagem
  existente como filtros). O termo digitado entra só como valor, nunca como
  estrutura de consulta. Cada obra recebida é reconferida no servidor antes de
  sair.

### Identificação enviada à AIC

Toda chamada do servidor à AIC (busca, detalhe e imagem) leva `User-Agent: casa-de-leiloes/1.0` e `AIC-User-Agent:
casa-de-leiloes (https://casa-de-leiloes-i1xr.onrender.com)`. A documentação
oficial da AIC recomenda se identificar; nos testes que fiz em 24/10/2026 o
Cloudflare da AIC devolveu 403 sem identificação adequada. Não é autenticação, não
há chave nem e-mail. A AIC documenta 60 requisições por minuto por IP anônimo; não
há cache nem nova tentativa automática.

### Se a AIC cair

A busca e o detalhe respondem `503 catalog_unavailable` (conexão, DNS, timeout de
3 s de conexão e 5 s de leitura, redirecionamento, 403 do Cloudflare, 429, 5xx,
JSON inválido ou fora do formato) e a interface mostra "O catálogo do museu não
respondeu". Login, `/health` e o resto da aplicação seguem normais. Lotes futuros
não dependem da AIC para os dados (AD-12); só a imagem vem do museu.

### Imagem

O navegador **não** carrega a imagem direto do IIIF: no teste manual de 24/10/2026
toda requisição `default.jpg` do navegador recebeu HTTP 403 do Cloudflare da AIC
(a tag `<img>` não envia a identificação). Por isso `image_url` aponta para um proxy
da nossa própria origem, `GET /api/catalog/images/{image_id}`, que busca
`https://www.artic.edu/iiif/2/{image_id}/full/843,/0/default.jpg` no servidor, com a
identificação, e devolve o JPEG. A rota é pública (obras de domínio público, sem dado
de conta; a vitrine da 2.5 usa as mesmas imagens), aceita só um `image_id` válido
(UUID minúsculo) e não é um proxy genérico: host, caminho, tamanho e formato são
fixos, não segue redirecionamento e limita o tamanho. Os bytes **não são
guardados**: ficam só em memória durante a resposta, sem arquivo, banco nem cache
(`Cache-Control: no-store`). Falha do IIIF vira 503 `catalog_unavailable` (404 se a
imagem não existir) e a interface mostra um placeholder local, com título e
metadados intactos.

### Smoke test contra a AIC real

Fora do `verify` (usa a internet; o `pytest` bloqueia qualquer acesso externo):

```bash
cd backend
uv run python -m scripts.smoke_artic
```

Imprime `PASS` ou `FAIL` para os seis itens do AD-23 e sai com 0 só se todos
passarem: busca (e termo sem correspondência → 0), detalhe, `is_public_domain=true`
(com controle negativo), imagem IIIF (e deriva da base fixa), campos usados e API
indisponível. Este último é uma falha simulada e determinística: o mesmo cliente
apontado para `127.0.0.1:9`. Não usa banco, login nem segredo e não grava nada.

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
- A busca do catálogo mostra só as 20 obras mais relevantes e não pagina: para
  encontrar outras, refine o termo.
- O firewall (Cloudflare) da AIC recusa alguns termos, como `<script>` ou aspas
  combinadas com `AND` e parênteses. Isso chega como "catálogo indisponível" (503),
  e a interface sugere tentar outro termo.
- A imagem da obra pode falhar (bloqueio do IIIF, 429, indisponibilidade) sem afetar
  os dados: aparece o placeholder e o resto continua.
- Cada imagem exibida custa uma chamada do servidor à AIC (sem cache): uma busca com
  20 resultados dispara até 20, contra o limite de 60 req/min por IP. Excedido, o
  restante das imagens cai no placeholder até a janela passar.
