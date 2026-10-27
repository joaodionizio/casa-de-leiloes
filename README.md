# ÁTRIO — Leilões de Arte

> Em 25/10/2026 o produto recebeu o nome ÁTRIO (nome de trabalho anterior: "Casa de
> Leilões"). Só a interface mudou de nome: repositório, bancos (`casa_de_leiloes_*`),
> módulos Python e `/api/*` continuam como estão.

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

`AUDIT_HMAC_SECRET` e `PSEUDONYM_SECRET` protegem o histórico de lances (veja
"Lances"). Cada um precisa ter **pelo menos 32 bytes em UTF-8**, os dois precisam ser
**diferentes entre si e diferentes do `JWT_SECRET`**; 32 bytes não garantem entropia, então
use valores aleatórios fortes (por exemplo `python -c "import secrets;
print(secrets.token_urlsafe(48))"`, uma vez para cada). Sem eles, ou inválidos, a
aplicação não inicia e a mensagem nunca mostra o valor. Ficam no meu `backend/.env`
(as linhas `AUDIT_HMAC_SECRET=` e `PSEUDONYM_SECRET=` entram sem valor em
`backend/.env.example`, que eu edito); nunca vão para o repositório, para o banco, para
log, resposta ou payload. Os testes geram valores aleatórios a cada execução.

Aplicar as migrations e semear as contas de demonstração no banco de
desenvolvimento (o seed precisa de `DATABASE_URL` e `AUDIT_HMAC_SECRET`, que assina a
âncora vazia do lote demo; ele não lê `PSEUDONYM_SECRET`):

```bash
cd backend && uv run alembic upgrade head
cd backend && uv run python -m app.seed
```

O seed é idempotente: cria só as contas que faltam e nunca altera uma conta que já
existe (nem o hash da senha). Também garante uma carteira zerada para todo usuário que
ainda não tem uma, sem nunca alterar um saldo (veja "Carteira"), e um lote demo aberto
(veja "Lotes"). Veja "Contas de demonstração".

Rodar os testes (o banco `_test` é recriado a cada sessão) e a verificação completa:

```bash
cd backend && uv run pytest
./verify.sh
```

O `./verify.sh` fornece valores locais padrão para `DATABASE_URL`,
`TEST_DATABASE_URL` e `APP_ORIGIN` (`http://localhost:5173`) quando eles não estão
definidos no ambiente; valores já exportados no shell têm precedência. Por isso o verify não depende de
`backend/.env`.

O `verify` roda, em ordem e parando na primeira falha: Ruff (lint e formato),
`pytest` (inclui a integração em PostgreSQL real), ESLint, `tsc --noEmit`,
`npm test` (testes da lógica pura do front, `node --test`, sem dependência nova: dinheiro, horários, a checagem do rascunho do lote, as rotas, os rótulos de fase, a vitrine, a linha de atualização e a validação das respostas públicas), o
build do Vite e o `docker build`. Para rodar só os testes do front:
`cd frontend && npm test`. Os testes de navegador (Playwright) ficam fora do `verify`
padrão; veja "Testes de navegador".

### Testes de navegador (Playwright)

`npm test` cobre a lógica pura; o que só um navegador real prova (History API, foco,
layout em viewports reais, imagem quebrada) é do Playwright, em `frontend/e2e/`. É uma
camada pequena e separada, não substitui os outros testes.

```bash
cd frontend
npm install
npx playwright install chromium   # uma vez; baixa ~100 MB para ~/Library/Caches/ms-playwright
npm run test:e2e
```

- A API é **simulada por interceptação de rede** (`e2e/support/mockApi.ts`): nenhum
  banco, nenhuma AIC e nenhum dado persistente são tocados. O servidor é o `vite preview`
  do build de produção, que o próprio Playwright sobe (porta 4173).
- Cobertura: visitante sem login; deep-link com recarga; vitrine → lote → Back →
  Forward; login com retorno ao lote (e `returnTo` externo ignorado) e logout; header de
  `BIDDER` e `AUCTIONEER`; "Mostrar mais encerrados" sem novo pedido à API; imagem
  quebrada → placeholder; Tab, foco visível e foco no `h1`; layout em 1440×900, 375×812
  e 320×812 (sem rolagem horizontal, destaque em duas colunas no desktop e empilhado no
  celular, container centrado, densidade dos rails); marca ÁTRIO (títulos da aba, nome
  acessível do link da marca, tagline só no desktop, header sem sobreposição em 1440, 375 e
  320 px para anônimo, `BIDDER` e `AUCTIONEER`); alvos de toque de ~44 px no header e em
  "← Vitrine"; contorno de foco do rail sem corte; `returnTo` interno após reload. Os asserts usam estrutura e caixas
  delimitadoras com tolerância; não há comparação de screenshot. Em falha, o Playwright
  guarda screenshot e trace em `frontend/test-results/` só para depuração.
- **Fora do `./verify.sh` padrão**, de propósito: exige o Chromium do Playwright e sobe um
  servidor, o que o `verify` (Docker e Node) não precisa. Para incluí-lo:
  `VERIFY_E2E=1 ./verify.sh`. Rode-o antes de mexer em navegação, foco ou layout.
- **Pilha real (opcional).** `e2e/real-stack.spec.ts` só roda com `E2E_REAL_BASE_URL` e
  prova o que a simulação não pode: `/api/*` nunca cai no fallback da SPA e as rotas
  públicas reais respondem JSON. Com o PostgreSQL de teste no ar (nunca o de
  desenvolvimento), as migrations e o seed aplicados nele, e o build gerado:

  ```bash
  cd backend && DATABASE_URL='<url-do-banco-test>' APP_ORIGIN=http://localhost:8765 \
    JWT_SECRET='<placeholder-jwt>' AUDIT_HMAC_SECRET='<placeholder-audit>' \
    PSEUDONYM_SECRET='<placeholder-pseudonym>' SPA_DIST_DIR=../frontend/dist \
    uv run uvicorn app.main:app --port 8765
  cd frontend && E2E_REAL_BASE_URL=http://localhost:8765 npm run test:e2e -- real-stack
  ```

  Não rode junto com o `pytest`, que recria o banco de teste a cada sessão.

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

Cada conta nasce com uma **carteira zerada** (veja "Carteira"): o seed não
pré-carrega saldo. Para demonstrar, entre como `bidder1@example.com` e deposite pela
tela "Carteira".

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
- Se o `GET /api/me` falhar por indisponibilidade do servidor, a vitrine abre
  normalmente como visitante e a tela de login (`/login`) mostra a mensagem de erro; o
  login só funciona quando o servidor volta.

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
  -e JWT_SECRET='<um-valor-aleatorio-com-32-ou-mais-caracteres>' \
  -e AUDIT_HMAC_SECRET='<placeholder-sintetico-audit-substituir>' \
  -e PSEUDONYM_SECRET='<placeholder-sintetico-pseudonym-substituir>' \
  -e DATABASE_URL=postgresql://casa:casa_local_dev@postgres:5432/casa_de_leiloes_dev \
  casa-de-leiloes
```

Substitua os dois placeholders sintéticos por segredos aleatórios fortes, cada um
com **pelo menos 32 bytes em UTF-8**, **diferentes entre si e de `JWT_SECRET`**.

O `./verify.sh` constrói a imagem (`docker build`), mas não a executa.

## Deploy no Render

**Estado documental em 27/10/2026: Epic 3 entregue e encerrado.** O primeiro
deploy e redeploy foram validados na Story 1.4. O deploy do Epic 2 foi postergado
por falha de processo e **recuperado agora pelo deploy conjunto dos Epics 2 + 3**.
Registrei os reviews retrospectivos dos Epics 1/2 e o review agregado do Epic 3,
com F-01 MEDIUM corrigido, re-review aprovado e LOW opcional de cobertura aceito.
O verify completo final anterior ao merge ficou verde. Fiz manualmente o merge,
o push da `main`, a configuração do Render, o deploy de recuperação e o smoke
público; confirmei a aplicação publicada funcionando.

Produção usa **`main`**, commit publicado **`3d3ea97`**, em
<https://casa-de-leiloes-i1xr.onrender.com>.
O [registro de recuperação e evidências](docs/DEPLOY-RECUPERACAO-EPICS-2-3.md)
distingue minha confirmação manual dos itens não individualizados. A IA não
acessou o painel nem repetiu deploy/smoke neste fechamento documental.
O [processo canônico](docs/FECHAMENTO-DE-EPICO.md) continua regendo os gates.
WebSocket da sala, liquidação e comprovante (Epic 4), auditoria pública (Epic 5)
e demais funcionalidades futuras continuam fora desta entrega.

### Configuração de produção

| Item | Configuração |
| --- | --- |
| Serviço | Web Service Docker existente; `Dockerfile` da raiz, um processo uvicorn, SPA + API na mesma origem |
| Banco | PostgreSQL existente do Render; validade do plano não individualizada na evidência manual |
| Branch de produção | **`main`**, commit publicado **`3d3ea97`**, conforme confirmação manual |
| Auto-Deploy | Desabilitado no roteiro; opção efetiva não individualizada na evidência manual |
| Publicação | Deploy de recuperação 2+3 executado manualmente pelo usuário; opção exata do painel não individualizada |
| Health Check Path | `/health`, conforme roteiro; resposta individual não registrada neste fechamento |
| Startup | `CMD` da imagem (`./scripts/start.sh`), sem Docker Command próprio, sem Pre-Deploy Command, conforme contrato documentado |

Referência operacional: [Deploying on Render](https://render.com/docs/deploys).
Região Virginia (US East), PostgreSQL 18 e planos Free são o registro do primeiro
deploy, sem nova inspeção da conta pela IA.

### Variáveis operacionais atuais

| Nome | Requisito |
| --- | --- |
| `DATABASE_URL` | Obrigatória: Internal Database URL, configurada só no painel. Não copiar seu valor para documentação/logs. |
| `APP_ORIGIN` | Obrigatória: origem HTTPS exata da URL pública acima, sem barra final, caminho, query ou credenciais. |
| `JWT_SECRET` | Obrigatória: aleatório forte, pelo menos 32 caracteres. |
| `AUDIT_HMAC_SECRET` | Obrigatória desde 3.4: aleatório forte, pelo menos 32 bytes UTF-8; usada também pelo seed. |
| `PSEUDONYM_SECRET` | Obrigatória desde 3.4: aleatório forte, pelo menos 32 bytes UTF-8. |
| `PORT` | Injetada pelo Render; `start.sh` escuta em `0.0.0.0` nessa porta (padrão local 8000). |
| `SPA_DIST_DIR` | Definida na imagem: `/app/frontend-dist`; não sobrescrever com caminho inválido. |

Os três segredos precisam ser **distintos entre si**. Verifico/configuro os
nomes obrigatórios **antes** do deploy e preservo os valores operacionais já
usados; rotação de segredos de integridade não é suportada. Não há variável de
CORS, `APP_ENV` ou credencial AIC exigida pelo código. `TEST_DATABASE_URL`,
`VERIFY_E2E` e `E2E_REAL_BASE_URL` pertencem aos testes, não ao serviço de produção.
Fonte dos nomes/regras: `backend/app/config.py`, `main.py`, `seed.py`,
`backend/scripts/start.sh` e `Dockerfile`, sem consulta a `.env*`.

### Migrations, seed e startup

O `start.sh` usa `set -eu`: executa **`alembic upgrade head` →
`python -m app.seed` → uvicorn**. Erro em migration ou seed impede o servidor;
configuração inválida também pode falhar no import de `app.main` depois do seed.
Não há scheduler/catch-up/liquidação nesta versão; são escopo do Epic 4.

Migrations atuais: `0001` baseline, `0002` users, `0003` lots, `0004` wallets,
`0005` bids e `0006` lot_cancellation (**head esperado: `0006`**). No deploy,
acompanho upgrades ainda necessários sem exigir reaplicação dos já concluídos.
Não executo downgrade, limpeza de dados ou reassinatura de histórico em produção.

O seed precisa de `DATABASE_URL` e `AUDIT_HMAC_SECRET`; usa fixture local, sem
consultar a AIC. Cria contas ausentes (um leiloeiro e dois licitantes), completa
carteiras ausentes com zero e preserva contas, senhas, saldos e históricos
existentes. Cria demo novo quando não encontra demo com fim futuro, não cancelado
e `anchor_hmac` não nula. Demo legado sem âncora não é reautenticado: fica intacto
e não impede o novo demo assinado. Não cria lances nem pré-carrega saldo.

### Validação pública e limites

Confirmei manualmente o smoke público dos fluxos entregues e a aplicação
funcionando. Resultados individuais do checklist: **não individualizado na
evidência manual**; não atribuo sucesso a cada cenário. O roteiro cobre
`/health`, SPA/JS/CSS/deep-link,
API JSON, login/logout/cookie/papéis, criação de lote, vitrine, carteira/depósito,
lances/recusas, saldos entre dois bidders, anti-sniping, histórico recente e
cancelamento sem lances. O histórico da sala não verifica a cadeia; a auditoria
pública integral ainda pertence à Story 5.1. Não testo UI futura de WebSocket,
liquidação, comprovante ou meus arremates neste fechamento.

`/health` responde 200 `{"status":"ok"}` e **não consulta o banco**; por isso
não substitui smoke de API com dados, autenticação e frontend publicados.
Sem sessão/papel/origem corretos, requests de escrita podem ser recusados antes
do domínio. A SPA usa o cookie `__Host-auction_session` em HTTPS; o cookie técnico
da 1.4 já foi removido na 2.2. O WebSocket técnico `/api/infra-check/ws` ainda
existe até a 4.1; não é uma sala ao vivo.

O primeiro deploy registrou Alembic `0001`, uvicorn na porta fornecida, serviço
`Live`, HTTP/cookie/WebSocket e redeploy sem reaplicar a migration. O WebSocket
público teve fechamento `1006`, sem causa determinada; cold start não foi
observado nem medido. As evidências originais e limitações estão na
[Story 1.4](_bmad-output/implementation-artifacts/1-4-primeiro-deploy-no-render.md).
Não as apresento como validação dos Epics 2/3.

O plano gratuito pode ter cold start; só registro tempo após medição real.
O primeiro painel mostrou expiração do PostgreSQL em 23/11/2026: confirmar a
situação atual manualmente. Persistem limites reais: sala sem atualização
entre navegadores até Epic 4, imagens externas com placeholder, ausência de
idempotência de POST e de rotação de segredos de integridade; detalhes nas
seções de cada fluxo e em "Comportamentos que podem surpreender".

## Catálogo do Art Institute of Chicago

O leiloeiro (`AUCTIONEER`) escolhe a obra que vai virar lote num catálogo real de
domínio público. A busca e o detalhe só **leem e mostram**: não gravam nada no banco.
Quem cria o lote a partir da obra escolhida é `POST /api/lots` (veja "Lotes").

- `GET /api/catalog/artworks?q=termo`: até 20 obras mais relevantes, só
  `is_public_domain=true` e com imagem. Sem paginação. O termo tem de 1 a 100
  caracteres depois de `strip`. O acervo está em inglês.
- `GET /api/catalog/artworks/{external_id}`: o detalhe com os campos que `POST /api/lots`
  copia para o lote como snapshot. Obra inexistente, fora do domínio público ou sem imagem
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
respondeu". Login, `/health` e o resto da aplicação seguem normais. A AIC só é usada na
busca e na seleção: ao criar o lote, os campos da obra são gravados como snapshot no
PostgreSQL, e vitrine, detalhe e leilão leem esse registro sem nova consulta à AIC. Um
lote criado continua funcionando mesmo se a AIC ficar indisponível depois (AD-12); só a
imagem vem do museu.

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

## Lotes

O leiloeiro cria um lote a partir de uma obra do catálogo e acompanha os seus em
"Meus lotes". Valores em **centavos inteiros** (`BIGINT`, sufixo `_cents`), horários
em `TIMESTAMPTZ`, tudo no PostgreSQL. Depois de criado, o lote não depende mais da AIC
para nenhum dado de negócio; só a imagem continua vindo do museu, pelo proxy da nossa
origem.

**Criar** (`POST /api/lots`, só `AUCTIONEER`): o corpo leva `external_id`,
`starting_bid_cents`, `min_increment_cents`, `starts_at` (opcional) e `ends_at`.
Qualquer outro campo, como `title`, `image_id` ou `auctioneer_id`, é recusado com 422.
O servidor **consulta a AIC de novo** e grava o que ele mesmo obteve (11 campos da obra,
sem `image_url` e sem bytes de imagem), então editar o corpo no DevTools não adultera o
snapshot. O dono do lote é sempre o usuário da sessão. Respostas: `201` com o lote;
`422 artwork_not_eligible` (obra inexistente, fora do domínio público ou sem imagem, sem
dizer qual); `503 catalog_unavailable` (AIC fora: nada é gravado); `422
validation_error` com `details` para dinheiro e horários; 401 sem login e 403 para
`BIDDER`, ambos sem chamar a AIC. A chamada à AIC acontece **antes** da transação de
escrita; a transação só lê o relógio do banco, insere e confirma.

**Dinheiro:** de `1` a `9007199254740991` centavos (`Number.MAX_SAFE_INTEGER`, o maior
inteiro que o JavaScript representa sem perda; limite técnico, não comercial, ou seja,
R$ 90.071.992.547.409,91). A mesma faixa vale na API, no serviço, no front e nas CHECKs
do banco. Número com casa decimal, texto ou booleano é recusado. Na tela, o valor é
digitado em reais (`10`, `1234,56`, `1.234,56`) e convertido para centavos por texto,
sem `float`; a revisão mostra o valor formatado a partir dos centavos.

**Horários:** ISO 8601 com fuso obrigatório (`Z` ou `-03:00`); a resposta sai sempre em
UTC com `Z`. `starts_at` ausente ou `null` significa "assim que eu publicar": vale a hora
do **PostgreSQL** (`clock_timestamp()`), nunca a do navegador. Início agendado precisa
ser futuro; o término precisa ser posterior ao início efetivo. Não há duração mínima nem
horizonte máximo.
A tela também confere, só de forma preventiva e com o relógio do navegador, que o término
não passou e que um início agendado é futuro; o servidor repete a regra com a hora do banco
e é quem decide. "Revisar lote" revalida os horários antes da revisão.
No dinheiro, `655.3` é recusado com a dica de usar vírgula (`655,30`): o ponto só vale como
milhar.

**Meus lotes** (`GET /api/lots/mine`, só `AUCTIONEER`): `{as_of, items}` com todos os lotes
do leiloeiro da sessão, **inclusive os cancelados**, do mais recente para o mais antigo,
sem paginação e sem limite. É leitura pura (só `SELECT`) e não consulta a AIC. Cada item
traz, além dos campos da criação, `cancelled_at`, `bid_count` (contagem persistida, só uma
dica de tela) e `phase` (`scheduled`, `live` ou `ended`), calculada no servidor com o
`as_of` do banco. Um lote cancelado mostra o selo "Cancelado" no lugar da fase.

### Lote demo

`python -m app.seed` (rodado antes do servidor pelo `start.sh`) garante um lote demo
aberto: a obra 27992 ("A Sunday on La Grande Jatte — 1884"), de uma fixture versionada
em `backend/app/seed_data/demo_artwork.json`, **sem consultar a AIC**. Começa na hora do
banco e dura 72 horas, com lance inicial de R$ 100,00 e incremento de R$ 10,00, ligado ao
leiloeiro semeado. "Aberto" quer dizer `is_demo`, `ends_at` no futuro, `anchor_hmac`
não nulo (Story 3.4) **e `cancelled_at` nulo** (Story 3.6). Um demo anterior à 3.4, sem
âncora, não conta e não recebe lance; um demo cancelado também não conta, e o seed nunca o
reativa. Em ambos os casos o seed cria um demo novo e autenticado e deixa o antigo
exatamente como estava. Se já existe um demo aberto, nada é criado; se nenhum está aberto
(todos encerrados, cancelados ou sem âncora), nasce um novo. O seed só faz `INSERT`
em `lots`: nunca altera nem apaga um lote antigo. Uma trava consultiva do PostgreSQL
(`pg_advisory_xact_lock`) faz dois seeds simultâneos criarem no máximo um demo.

## Lances

`POST /api/lots/{lot_id}/bids` (só `BIDDER`; o `AUCTIONEER` recebe 403 sem tocar no lote).
Corpo `{"amount_cents": n}`, inteiro de `1` a `9007199254740991`; qualquer outro campo, ou
`float`, texto e booleano, é 422 `validation_error`. Um lance aceito é **uma única
transação do PostgreSQL**: trava o lote (`SELECT ... FOR UPDATE`), lê **um** instante
`clock_timestamp()` do banco (o navegador nunca decide a hora), autentica o histórico
anterior, aplica as regras, trava as carteiras em `user_id` crescente, reserva o saldo do
novo líder, devolve o do anterior, aplica o anti-sniping, grava o lance e a nova âncora, e
confirma. Qualquer falha desfaz tudo.

| Resposta | Quando |
| --- | --- |
| `201` | `{bid: {sequence, bidder_alias, amount_cents, placed_at}, lot: {current_bid_cents, ends_at, anti_sniping_applied}, wallet: {total, committed, available}}`. Nunca `bidder_id`, hashes, HMAC nem segredos. |
| `422` + código | recusa de negócio, na precedência: `lot_not_started`, `lot_ended`, `below_minimum`, `already_winning`, `insufficient_balance`. Nada é gravado. |
| `409 lot_integrity_conflict` | o histórico do lote não se autentica. Mensagem única; nada é gravado, reparado ou reassinado. |
| `404` | lote inexistente. |

Comportamentos que podem surpreender (lances):

- **Anti-sniping renovável e sem teto:** um lance aceito com `0 < restante <= 2 min` leva o
  fim a **`now` + 2 minutos**, com o mesmo instante `clock_timestamp()` lido sob a trava
  (AD-5, revisada em 27/10/2026); cada novo lance válido na janela renova o prazo a partir
  de si. Com exatamente 2 minutos restantes o fim não muda e `anti_sniping_applied` fica
  falso. Lance recusado nunca altera o fim. Depois do fim, o lote nunca reabre; o lance
  recebe `lot_ended`. Lotes e lances anteriores a esta revisão não foram alterados. Esta
  etapa só recusa: não fecha nem liquida (isso é da Story 4.3/4.4).
- **409 de integridade:** antes de qualquer regra, o servidor reconstrói a cadeia SHA-256
  do lote, confere a âncora HMAC e vincula o líder e o lance atual ao último lance. Qualquer
  adulteração (alteração, inserção, remoção do meio, truncamento, recálculo sem o segredo)
  responde 409, mesmo que a regra de negócio recusaria o lance por outro motivo.
- **Lotes anteriores à 3.4** ficam com `anchor_hmac` nulo: aparecem na vitrine, mas todo
  lance neles responde 409 (inclusive o demo antigo, até vencer). Nenhum caminho (lance,
  boot, seed, migration) assina o estado encontrado no banco; um comando manual de
  autenticação de lotes legados não existe nesta entrega.
- **Segredos no Render:** `AUDIT_HMAC_SECRET` e `PSEUDONYM_SECRET` precisam existir no
  painel **antes** do deploy de recuperação 2+3. Sem o de auditoria o seed falha e o servidor não sobe.
  O seed não compara os três segredos; se dois forem iguais, o servidor falha logo depois.
  Corrija trocando `PSEUDONYM_SECRET` ou `JWT_SECRET`.
- **Rotação de segredos não é suportada.** Trocar `AUDIT_HMAC_SECRET` invalida todas as
  âncoras já assinadas (todo lote, inclusive o demo, passa a responder 409; o demo continua
  contando como "aberto" até vencer). Trocar `PSEUDONYM_SECRET` depois de existirem lances
  também bloqueia esses lotes. Trocar o `JWT_SECRET` só derruba as sessões.
- **Falha de rede depois do commit:** se a conexão cair depois de o servidor enviar o
  `COMMIT`, o resultado é indeterminado para o cliente: o lance pode ter sido aceito.
  Repetir pode responder `already_winning`. Não há chave de idempotência.
- **Limites da âncora:** ela protege o histórico de lances. Restaurar a cadeia **e** a
  âncora antigas e válidas não é detectado (não há âncora externa), e a âncora não cobre os
  termos do lote (`ends_at`, lance inicial, incremento) nem os saldos das carteiras.
- **Estado de lance no lote:** as colunas `current_bid_cents`, `current_leader_id`,
  `bid_count`, `final_hash` e `anchor_hmac` só mudam num lance aceito. `downgrade` da
  migration `0005` perde lances e esse estado (só desenvolvimento).
- A leitura da cadeia a cada tentativa é O(n) e a fila na trava do lote não tem
  `lock_timeout`: aceitável na escala do desafio.

### A sala do lote (Story 3.5)

Duas leituras alimentam a sala, ambas só de leitura (sem trava, sem escrita, sem autenticar
a cadeia; um lote legado sem âncora é lido normalmente, e o `POST` dele continua 409):

- `GET /api/lots/{lot_id}/bids` (público): `as_of`, `phase`, `ends_at`, `current_bid_cents`,
  `minimum_next_bid_cents` (`null` só se nenhum valor até o teto o alcança), `bid_count`
  (total do lote) e `bids`: os **50 mais recentes**, `sequence` decrescente, cada um com
  `sequence`, `bidder_alias`, `amount_cents` e `placed_at`. Uma única instrução SQL, com um
  só `clock_timestamp()`. O limite de 50 é só da sala; a auditoria (5.1) mantém o histórico
  completo. Nunca expõe `bidder_id`, nome, e-mail, hashes nem HMAC.
- `GET /api/lots/{lot_id}/bids/mine` (só `BIDDER`): `bidder_alias`, `my_bid_count` (todos os
  lances daquele alias no lote, mesmo fora dos 50) e `last_bid_cents`. A posição
  (ganhando, superado ou neutro) é derivada no front destes dois retornos.

Comportamentos que podem surpreender (sala):

- **O contador é uma estimativa visual** baseada no último estado lido, com relógio
  monotônico do navegador; pode superestimar o tempo restante. **O servidor continua sendo
  a autoridade** para aceitar ou recusar o lance: chegar a `0:00` não bloqueia o envio e
  causa uma única releitura por valor de `ends_at`.
- **A sala não atualiza sozinha** (não há polling nem WebSocket até o Épico 4): outra pessoa
  só aparece depois de "Atualizar sala", do zero da contagem ou do seu próprio lance. A linha
  "Situação atualizada às HH:MM:SS" mostra a hora do `/bids` lido.
- Depois de um `201`, a tela mostra na hora o valor, o novo fim e a carteira da resposta e
  faz **uma** releitura para o histórico, o mínimo e a posição; se ela falhar, o aceite
  continua mostrado.
- **Erro de rede ou 5xx no envio** é resultado incerto: a tela não afirma se o lance entrou,
  faz uma releitura e nunca reenvia sozinha. Como não há chave de idempotência, repetir à mão
  ainda pode gravar outro lance.
- O formulário só valida o **formato** do valor; abaixo do mínimo ou acima do saldo o pedido
  vai ao servidor, que decide.

### Cancelar lote (Story 3.6)

`POST /api/lots/{lot_id}/cancel` (só `AUCTIONEER`, **sem corpo**; a identidade é a da
sessão) cancela um lote **seu**, que **ainda não recebeu lances** e **ainda não terminou**.
Responde `200 {id, cancelled_at}`. Em transação própria, seguindo o mesmo protocolo de
trava do lote → hora do banco → dono → integridade → regras, escreve só `lots.cancelled_at`: não
toca em carteiras, em lances nem na âncora. Cancelar de novo um lote íntegro devolve o
mesmo `200` com o instante original, sem nova escrita. Recusas: `403` (outro leiloeiro ou
`BIDDER`), `404`, `409 lot_integrity_conflict`, `422 lot_has_bids`, `422 lot_ended`.

Comportamentos que podem surpreender (cancelamento):

- **Cancelado some do público.** Fora da vitrine, e `GET /api/lots/{id}`, `/bids` e
  `/bids/mine` respondem `404`. O dono continua vendo o lote em "Meus lotes", com o selo
  "Cancelado". Não existe `phase = cancelled`: a fase continua sendo só temporal.
- **Lote anterior à 3.4 (sem âncora autenticada) não é cancelável:** a decisão "sem lances"
  usa a contagem autenticada pelo mesmo gate do lance, e esse lote responde `409`. Não há
  reparo, reassinatura nem comando administrativo nesta entrega; ele fica na vitrine até
  vencer. Cancelar o lote demo faz o próximo boot criar outro.
- **`cancelled_at` não é autenticado pela âncora v1** (como `ends_at` e o dono). Quem edita
  o banco à mão pode esconder ou reexibir um lote; isso não move saldo.
- **Sem aviso em tempo real:** a sala já aberta não é avisada (não há WebSocket até o Épico
  4). Um lance em lote cancelado responde `422 lot_cancelled` e a tela diz "Este lote foi
  cancelado."; uma leitura pública **posterior** (atualizar ou voltar à sala) responde `404`
  e pode mostrar "Lote não encontrado.". Isso não significa que o cancelamento falhou.
- **Erro de rede ou 5xx no cancelamento** é resultado incerto: a tela não afirma sucesso nem
  falha, relê a lista uma vez e nunca reenvia sozinha.

## Vitrine e página do lote

Qualquer pessoa, **sem login**, vê os lotes separados em ao vivo, próximos (agendados) e
encerrados, e abre a página de cada um. O estado de cada lote é derivado **no servidor**,
com a hora do PostgreSQL; o navegador só o apresenta.

- `GET /api/lots`: `{as_of, live, scheduled, ended}` com **todos** os lotes (sem
  paginação nem limite), cada item com `phase` (`scheduled`, `live` ou `ended`).
  `GET /api/lots/{lot_id}`: `{as_of, lot}`. Ambas são públicas (a resposta não depende de
  quem pede), `Cache-Control: no-store` e só leem: nenhum `INSERT`, `UPDATE`, `DELETE`,
  `FOR UPDATE`, nem liquidação ou seed (AD-19). `lot_id` fora do formato UUID dá 422; UUID
  válido inexistente dá 404 (`not_found`).
- **Fase:** `now < starts_at` agendado; `starts_at <= now < ends_at` ao vivo; `now >=
  ends_at` encerrado, exata em microssegundos. Não existe coluna de estado: a fase é
  calculada na leitura por `lot_phase`.
- **Um instante, um snapshot.** Cada rota executa um único statement (`WITH clock AS
  MATERIALIZED (SELECT clock_timestamp() AS as_of) SELECT … FROM clock LEFT OUTER JOIN
  lots …`): `as_of` e as linhas saem do mesmo snapshot do PostgreSQL, e todos os lotes da
  resposta são classificados com o mesmo `as_of`. Duas consultas independentes dariam dois
  snapshots em `READ COMMITTED`. Sem lotes, a resposta continua tendo `as_of` e três listas
  vazias.
- **Ordem:** ao vivo por `ends_at` crescente; agendados por `starts_at` crescente;
  encerrados por `ends_at` decrescente; `id` crescente desempata. O destaque da vitrine é
  o primeiro ao vivo, senão o primeiro agendado.
- **Dados públicos só do nosso banco:** título, artista, data, técnica, dimensões,
  departamento, tipo, crédito, fonte, valores e horários vêm do snapshot gravado no lote;
  as rotas não chamam a AIC. Só a imagem vem do museu, pelo proxy da nossa origem. Não
  saem `auctioneer_id`, `is_demo`, `created_at`, o `image_id` solto nem dado de usuário.
- **Endereços do front:** `/` (vitrine), `/lots/{uuid}`, `/login`, `/auctioneer/lots/new`
  (Criar lote) e `/auctioneer/lots` (Meus lotes). A navegação usa a History API, sem
  React Router: clique, Back, Forward, recarregar e link direto funcionam, e o servidor
  devolve a SPA para esses caminhos. "Entrar" abre `/login`; depois do login a pessoa
  volta à página pública de onde veio (o destino fica em `history.state`, só rotas
  conhecidas valem, nunca uma URL externa). "Sair" leva à vitrine.

Como validar (com a aplicação rodando):

```bash
curl -sS -i http://localhost:8000/api/lots            # 200, no-store, {"as_of":…,"live":[…]}
curl -sS -i http://localhost:8000/api/lots/<uuid>      # 200, ou 404 se o UUID não existe
curl -sS -i http://localhost:8000/api/lots/abc         # 422 validation_error
curl -sS -i http://localhost:8000/lots/<uuid>          # 200, text/html (SPA montada)
```

## Carteira

O licitante vê o próprio saldo e faz um **depósito simulado** (valor fictício, sem
dinheiro real). Valores em **centavos inteiros** (`BIGINT`, sufixo `_cents`), sem `float`.

| Rota | Quem | O que faz |
| --- | --- | --- |
| `GET /api/wallet` | só `BIDDER` | `{total_balance_cents, committed_balance_cents, available_balance_cents}`, `Cache-Control: no-store`. Só lê: nenhum `INSERT`, `UPDATE` nem trava (AD-19). |
| `POST /api/wallet/deposit` | só `BIDDER` | corpo `{"amount_cents": n}`; soma `n` ao total da **própria** carteira e devolve `200` com os mesmos três valores. |

- **Saldo:** o disponível é sempre `total - comprometido`, calculado no servidor, e nunca
  é gravado. O comprometido é alterado só pelo lance (Story 3.4, veja
  "Lances"): sobe com o lance do líder e volta ao disponível quando ele é superado. O `AUCTIONEER` recebe 403 nas duas rotas e não tem tela de carteira.
- **Entrada estrita:** `amount_cents` é um inteiro de `1` a `9007199254740991`. Zero,
  negativo, `100.5`, `1e2`, texto, booleano, ausente, campo extra (inclusive `user_id`) e
  valor acima do teto dão 422 `validation_error`. A carteira alterada é sempre a do
  usuário da sessão.
- **Teto do saldo:** o total da carteira também não passa de `9007199254740991` centavos
  (`R$ 90.071.992.547.409,91`, o inteiro seguro do JavaScript; limite técnico, não
  comercial). Um depósito válido que ultrapassaria esse total recebe 422
  `balance_limit_exceeded` ("O depósito ultrapassaria o limite de saldo da carteira."),
  sem `details`, e nada é gravado. O banco impede o mesmo por CHECK, com o mesmo literal da
  aplicação (`app/money.py`).
- **Concorrência:** o depósito é uma transação curta que trava a linha da carteira
  (`SELECT ... FOR UPDATE`), **lê o saldo depois da trava**, confere o teto, atualiza e
  confirma. Dois depósitos simultâneos na mesma carteira somam os dois, e perto do teto o
  segundo decide sobre o saldo que o primeiro confirmou.
- **Carteira para todo usuário:** a migration `0004` cria `wallets` e uma carteira zerada
  para cada usuário que já existe; o seed completa quem faltar (todo usuário sem carteira,
  só `INSERT`, nunca altera saldo). Um usuário autenticado sem carteira é violação de
  invariante: `GET` e `POST` respondem 500 genérico e **nunca criam a carteira**.
- **Tela:** `/bidder/wallet` ("Carteira" no header do licitante), com o disponível em
  destaque, o total e o comprometido, e o depósito. O `AUCTIONEER` que digita o endereço
  vê "Área do licitante", e a página nem chama a API. O anônimo vai a `/login` e, depois
  de entrar como licitante, volta à carteira.

Como validar (com a aplicação rodando; as escritas exigem `Origin` e JSON, veja
"Erros e proteção das escritas"):

```bash
# Entrar como bidder1 e guardar o cookie de sessão
curl -sS -c /tmp/cookies -X POST http://localhost:5173/api/auth/login \
  -H 'Origin: http://localhost:5173' -H 'Content-Type: application/json' \
  -d '{"email":"bidder1@example.com","password":"Demo123!"}'
curl -sS -b /tmp/cookies http://localhost:5173/api/wallet           # 200, tudo 0 numa carteira nova
curl -sS -b /tmp/cookies -X POST http://localhost:5173/api/wallet/deposit \
  -H 'Origin: http://localhost:5173' -H 'Content-Type: application/json' \
  -d '{"amount_cents": 125000}'                                       # 200, R$ 1.250,00 disponíveis
```

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
- Criar um lote **depende da AIC** (o servidor reconfere a obra): com o museu fora do
  ar, `POST /api/lots` responde 503 e nenhum lote é criado. Os lotes já criados e o
  seed não dependem dela.
- Não há deduplicação de envio no servidor. Se a rede cair depois de o servidor gravar
  o lote, a tela diz que não foi possível confirmar e manda conferir "Meus lotes" antes
  de tentar de novo; repetir às cegas pode criar dois lotes. A mesma obra também pode
  estar em vários lotes.
- Um lote de duração mínima é aceito (basta o término ser posterior ao início): um lote
  de um segundo já nasce dentro da janela de anti-sniping de 2 minutos.
- "Começar agora" usa a hora do servidor; um início agendado "daqui a poucos segundos"
  pode ser recusado se, ao chegar, o servidor já considerar que passou.
- O lote demo vencido só é substituído na próxima inicialização do serviço (o seed roda
  no boot), então, entre o fim das 72 horas e o próximo boot, pode não haver demo
  aberto. Crie um lote para demonstrar.
- Os valores são limitados a R$ 90.071.992.547.409,91 por limite técnico (inteiro seguro
  do JavaScript), não comercial.
- A carteira não tem histórico de depósitos nem de movimentos: só o estado atual (total,
  comprometido, disponível). Cada depósito apenas soma ao total.
- Não há deduplicação de depósito no servidor (sem `Idempotency-Key`). A tela bloqueia o
  botão enquanto o envio está pendente e **nunca reenvia sozinha**; se a rede cair ou o
  servidor responder 5xx, ela faz uma única releitura do saldo e, sem poder confirmar,
  não afirma que o depósito entrou. Mas um timeout **depois** do commit, seguido de uma
  nova tentativa **manual** sua, ainda pode duplicar o depósito: confira o saldo antes de
  repetir.
- O total da carteira é limitado a R$ 90.071.992.547.409,91 por limite técnico (inteiro
  seguro do JavaScript), não comercial; depósitos acima disso são recusados.
- Qualquer pessoa pode depositar nas contas demo da URL pública (a senha é pública), então
  o saldo de `bidder1` e `bidder2` pode não ser o que você deixou. Se uma delas já
  estiver no teto e o depósito for recusado ("O depósito ultrapassaria o limite de saldo
  da carteira."), use a outra conta de licitante: o seed nunca zera um saldo existente.
- Reverter a migration `0004` (`alembic downgrade 0003`) apaga a tabela `wallets` e, com
  ela, os saldos: aceitável no desafio, mas irreversível.
- "Meus lotes" lista todos os lotes, sem paginação, e cada miniatura é uma chamada do
  servidor à AIC (sem cache), então uma lista muito longa pode esbarrar no limite de
  60 req/min e mostrar o placeholder.
- Cada imagem exibida custa uma chamada do servidor à AIC (sem cache): uma busca com
  20 resultados dispara até 20, contra o limite de 60 req/min por IP. Excedido, o
  restante das imagens cai no placeholder até a janela passar.
- A situação do lote é uma **fotografia** do `as_of` mostrado na página ("Situação
  atualizada às HH:mm"): na vitrine, um lote não passa sozinho de agendado a ao
  vivo nem de ao vivo a encerrado; um novo carregamento atualiza a fase. Na sala
  da 3.5 há contagem regressiva visual e releitura no zero de cada `ends_at`,
  em "Atualizar sala" e depois do próprio lance. Ainda não há polling nem
  WebSocket de sala; o servidor sempre decide a fase e a aceitação do lance.
- Todo lote encerrado aparece como "Encerrado, apurando resultado" até a liquidação
  existir (Story 4.3). Hoje isso é só texto de interface: não há vencedor, valor final
  nem comprovante, e nenhuma leitura liquida lote.
- A vitrine traz todos os lotes, sem paginação, e os lotes demo encerrados se acumulam a
  cada 72 horas de inicialização. "Mostrar mais encerrados" revela mais 6 por clique, só
  no navegador, sem nova chamada à API.
- Qualquer caminho desconhecido do front responde 200 com a SPA, e a tela mostra "Página
  não encontrada" (o servidor não distingue rota do cliente de rota inexistente); `/api/*`
  nunca recebe HTML.
- A API aceita o UUID do lote também em maiúsculas ou sem hífens (o Pydantic é
  tolerante); o front só gera e só reconhece o formato minúsculo com hífens.
- Depois do login, o botão Voltar do navegador passa pela página de origem antes de sair:
  o destino substitui `/login` no histórico.
