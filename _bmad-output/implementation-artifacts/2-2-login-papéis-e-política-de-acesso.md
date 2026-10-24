# Story 2.2 — Login, papéis e política de acesso

Status: done

Chave do sprint: `2-2-login-papéis-e-política-de-acesso`
Épico: 2. Data de criação: 24/10/2026.

## Story e objetivo

Como leiloeiro ou licitante semeado,
quero entrar e sair com a minha conta e ter acesso só ao que o meu papel permite,
para que o leiloeiro nunca dê lances, o licitante nunca crie lotes e nenhuma rota
fique aberta por esquecimento.

Nesta story entrego: a tabela `users`, as três contas semeadas (1 `AUCTIONEER`,
2 `BIDDER`), senha com Argon2, login e logout com JWT em cookie HttpOnly, o
endpoint do usuário atual, a política de acesso declarada em toda rota (com teste
que reprova rota sem política), o 401/403 no formato único da 2.1, a tela de login
em português e a remoção do cookie técnico da 1.4. Não antecipo carteira, lotes,
museu, lances nem a sala.

O status `ready-for-dev` indica que o artefato está criado. As questões P1 a P16
(seção "Questões abertas") são decididas por mim no Plan Mode, antes de qualquer
código, e registradas nesta story.

## Fontes e base real

Uso `CLAUDE.md`, `docs/ARQUITETURA.md` (AD-11, AD-17, AD-19, AD-24, AD-27, AD-29,
AD-30), `_bmad-output/planning-artifacts/epics.md` (Story 2.2, D2 = A, pendência da
1.4), `sprint-status.yaml`, a Story 2.1 (só como fundação) e as decisões P10/P11
da Story 1.4.

**Título e escopo conferidos no `epics.md`.** O título real é **"Login, papéis e
política de acesso"**. Divergências em relação ao que eu esperava:

- O título não tem "com usuários semeados", mas o escopo tem: o primeiro critério
  da story é o seed das três contas (FR1 e a parte de usuários do FR19).
- O `epics.md` inclui **interface**: "Dado a interface, Quando acesso a tela de
  login, Então consigo entrar e sair, com mensagens em português". A story tem
  trabalho de front-end, não só de API.
- O `epics.md` registra a dependência de **Q10** (nome da variável do segredo do
  JWT). Ela vira a P1.
- Não há rota real restrita a um papel nesta story (criar lote é 2.4, depósito é
  3.1, lance é 3.4), mas o critério de 403 por papel existe aqui. Ver P10.

**Base existente (conferida nos arquivos, sem git):**

- `backend/app/main.py`: `create_app(spa_dist_dir, app_origin)`, `/health` sem
  banco, Swagger em `/api/docs`, schema em `/api/openapi.json`, handlers de erro
  e `ApiWriteGuardMiddleware`; SPA registrada por último.
- `backend/app/errors.py`: contrato `{status, code, message[, details]}`, catálogo
  `CODE_BY_STATUS` + `MESSAGES`, `error_response()`. Já existem `unauthorized`
  (401, "Autenticação necessária.") e `forbidden` (403, "Acesso negado."). O
  `detail` de `HTTPException` nunca chega ao cliente (2.1 D3): a mensagem vem do
  catálogo pelo status. Um código específico (ex.: credenciais inválidas) exige
  mecanismo próprio (P6).
- `backend/app/csrf.py`: escritas (POST/PUT/PATCH/DELETE) sob `/api` exigem
  `Origin` (ou `Referer`) igual a `APP_ORIGIN` e `Content-Type: application/json`,
  antes do roteamento e sem ler o corpo. Consequência aceita na 2.1: **toda
  escrita exige `Content-Type: application/json`, mesmo sem corpo** (inclui o
  logout).
- `backend/app/config.py`: `Settings` (`DATABASE_URL`, `TEST_DATABASE_URL`),
  `SpaSettings`, `OriginSettings` (`APP_ORIGIN`, obrigatória, valida e falha na
  criação da app: 2.1 D2). Não há noção de ambiente (`APP_ENV` foi descartado na
  1.3 e na 1.4 P10; a 1.4 P10 deixou `Secure=false` local para a 2.2).
- `backend/app/db.py`: `Base` com naming convention, `create_db_engine()` (sem
  `hide_parameters`), `create_session_factory()`. Ainda **não há dependência de
  `Session` por requisição** e a criação da app não toca no banco.
- `backend/migrations/versions/0001_baseline.py`: revisão vazia. Nenhuma tabela
  de domínio existe.
- `backend/scripts/start.sh`: `alembic upgrade head` e depois `uvicorn`. Não há
  seed.
- `backend/app/infra_check.py`: `GET /api/infra-check/cookie` (cookie
  `__Host-infra_check`, sempre `Secure`) e `/api/infra-check/ws`, fora do
  OpenAPI. A docstring já diz que o cookie sai na 2.2 e o WebSocket na 4.1.
- `backend/tests/conftest.py`: recria o schema do banco `_test` uma vez por sessão
  e aplica as migrations; exige `APP_ORIGIN`. Não há isolamento por teste (nenhum
  teste grava dados ainda).
- `backend/tests/test_openapi.py` fixa `paths == ["/health"]`: muda nesta story.
- `backend/tests/synthetic_api.py`: rotas só de teste (precedente da 2.1).
- Front-end: `App.tsx` só mostra o estado do `/health`; `src/api/health.ts`. Sem
  roteador, sem biblioteca de testes (Q10: "ferramenta de teste do front" segue
  aberta). Dependências: só `react` e `react-dom`.
- Back-end: sem biblioteca de JWT nem de Argon2 em `pyproject.toml`.
- `deferred-work.md`: avaliar `hide_parameters=True` no engine "quando houver
  dados de usuário (a partir da 2.2)". Ver P16.
- O `sprint-status.yaml` registra a 2.1 como `done`; o arquivo da 2.1 ainda diz
  `Status: review`. Considero a 2.1 concluída, conforme a instrução desta sessão,
  e não altero o arquivo dela.
- Não localizei a skill `bmad-create-story` instalada; sigo a estrutura dos
  artefatos existentes e as instruções desta solicitação.

## Critérios de aceitação

1. **CA1 — Contas semeadas.** Dado a aplicação iniciando, quando o seed roda
   (mecanismo da P12), então existem exatamente um `AUCTIONEER` e dois `BIDDER`,
   com IDs fixos versionados (P13). Rodar o seed de novo não duplica nem altera
   esses usuários (nenhuma coluna muda, inclusive o hash). As senhas ficam
   armazenadas só como hash Argon2 (`$argon2id$...`), nunca em texto. O seed não
   consulta API externa e não cria lote (lote demo é 2.4). Não existe rota de
   cadastro.
2. **CA2 — Login válido.** Dado credenciais válidas, quando faço `POST` na rota de
   login (P5) com JSON, então recebo um JWT de 8 h num cookie `HttpOnly`,
   `SameSite=Lax`, `Path=/`, sem `Domain`, com `Secure` e prefixo `__Host-` em
   produção (P4). O token não contém dados pessoais desnecessários (sem e-mail,
   nome nem hash; claims na P3). O token nunca aparece no corpo da resposta, na
   URL nem em `localStorage`.
3. **CA3 — Login inválido.** Dado e-mail inexistente ou senha errada, quando tento
   login, então recebo erro no formato único (P6), sem `Set-Cookie` de sessão, e
   as duas situações são indistinguíveis: mesmo status, mesmo código, mesma
   mensagem e mesmo corpo. O e-mail informado não é ecoado.
4. **CA4 — Usuário atual.** Dado estar logado, quando consulto o endpoint do
   usuário atual (P5), então recebo meu papel (`AUCTIONEER` ou `BIDDER`); na
   interface aparece "Leiloeiro" ou "Licitante". Sem login, recebo 401.
5. **CA5 — Logout.** Dado estar logado, quando faço logout (`POST`, P7), então o
   cookie é apagado (mesmo nome, `Path` e atributos, expiração imediata). O README
   declara que um token copiado antes continua válido até o `exp` (AD-29).
6. **CA6 — Política de acesso declarada.** Dado todas as rotas registradas na
   aplicação (inclusive `/health`, documentação, SPA e o WebSocket técnico),
   quando o teste de política roda, então ele reprova qualquer rota sem política
   declarada (pública, autenticada ou por papel). Um teste prova que o verificador
   de fato reprova uma rota sem política (mecanismo na P9).
7. **CA7 — 401 e 403.** Dado uma rota autenticada ou restrita a um papel, quando
   um visitante sem login, com token expirado, adulterado, com outro algoritmo ou
   malformado a chama, então recebe 401; quando um usuário do outro papel a chama,
   recebe 403. Ambos no formato único, com a precedência da P8.
8. **CA8 — Integração com a proteção da 2.1.** Login e logout passam pela
   proteção de `Origin`/`Referer` e `Content-Type` sem exceção: origem estrangeira
   ou ausente → 403 `csrf_*`; sem JSON → 415; em nenhum desses casos o handler
   roda ou emite cookie. GET/HEAD/OPTIONS nunca autenticam, nunca emitem cookie de
   sessão e nunca alteram estado (AD-19). Nenhum cabeçalho CORS é introduzido.
9. **CA9 — Infraestrutura temporária.** O cookie técnico da 1.4
   (`GET /api/infra-check/cookie`, `__Host-infra_check`) é removido, com seus
   testes e a seção do README; a rota passa a responder 404 no formato único. O
   WebSocket técnico `/api/infra-check/ws` continua igual, classificado como
   público na política, até a 4.1.
10. **CA10 — Interface.** Dado a tela de login, quando entro e saio, então vejo
    mensagens em português (inclusive para credenciais inválidas e erro de rede),
    o papel como "Leiloeiro" ou "Licitante" e a opção "Sair". O JavaScript nunca
    lê o token (cookie HttpOnly) e nada de sessão vai para `localStorage`. Ao
    recarregar a página logado, a interface recupera o usuário pelo endpoint do
    usuário atual.
11. **CA11 — Migração e independência do banco.** A tabela `users` nasce numa nova
    revisão Alembic (esquema na P11), com `downgrade`. Os testes recebem o esquema
    das migrations. `GET /health` continua 200 sem banco e criar/importar a
    aplicação continua sem exigir conexão com o banco.
12. **CA12 — Segredo do JWT.** O segredo vem só de variável de ambiente (nome e
    validação na P1), nunca é versionado, logado, ecoado em erro de configuração
    nem devolvido em resposta. Nenhum valor real aparece em código, testes,
    README, story ou `docs/uso_de_ia.md`. Eu configuro o valor no Render e no meu
    `backend/.env` manualmente.
13. **CA13 — Verificação.** Os testes de login, seed e papel rodam em PostgreSQL
    real (nunca SQLite). Executo `./verify.sh` completo e registro a saída real.
    README e `docs/uso_de_ia.md` atualizados. Paro na 2.2.

## Decisões já fechadas pela arquitetura e pelo `epics.md`

Não reabro nenhuma delas.

| Fonte | O que já está decidido |
| --- | --- |
| AD-11 | JWT em cookie HttpOnly, mesma origem; senhas com Argon2; papéis `AUCTIONEER`/`BIDDER` como `UserRole.AUCTIONEER`/`UserRole.BIDDER`; "Leiloeiro"/"Licitante" só na interface; sem refresh token; logout remove o cookie; sem dados pessoais desnecessários no JWT. Descartados: `localStorage`, JWT na URL, sessão no banco, nomes em português. |
| AD-29 | JWT de 8 h; produção `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/`, sem `Domain`, `__Host-` quando possível; desenvolvimento (localhost) `HttpOnly`, `Secure=false`, `SameSite=Lax`; logout apaga o cookie e o README declara que o token copiado vale até o `exp`; CSRF por JSON + `Origin`/`Referer`; sem CORS permissivo. |
| AD-24 | Seed idempotente na inicialização; usuários com IDs fixos, nunca recriados se já existirem. |
| AD-19 | GET/HEAD/OPTIONS nunca alteram estado: login e logout são `POST` (a 2.1 CA11 já disse que o cookie técnico em GET não é precedente). |
| AD-30 | Inglês em código, banco e API (`users`, `/api/...`); mensagens em português. |
| AD-17, AD-27 | Testes de login e papel em PostgreSQL real; `verify` fail-fast. |
| `epics.md` D2 = A | Sem cadastro público; só as contas semeadas. |
| `epics.md` 2.2 | Login por e-mail ("sem revelar se o e-mail existe"); três categorias de política: pública, autenticada, por papel; 401 sem login, 403 do outro papel. |
| 1.4 P11 / `epics.md` | O cookie técnico sai nesta story; o WebSocket técnico fica público até a 4.1. |
| 2.1 | Formato único de erro, catálogo de mensagens, proteção de escrita por `Origin`/`Referer` e `Content-Type`, `APP_ORIGIN` obrigatória. |
| `CLAUDE.md` | AUCTIONEER não dá lance, BIDDER não cria lote; toda rota declara sua política e um teste reprova rota sem política. |

**Classificação prevista das rotas** (sujeita às P5, P7 e P9):

| Rota | Política |
| --- | --- |
| `GET /health` | pública |
| `/api/docs`, `/api/openapi.json` | pública (documentação) |
| SPA (`/`, rotas do cliente, assets) | pública |
| `/api/infra-check/ws` (WebSocket técnico, até a 4.1) | pública |
| login | pública (protegida pela 2.1 como toda escrita) |
| logout | P7 |
| usuário atual | autenticada |
| rota restrita a papel | nenhuma real nesta story (P10) |

## Questões abertas (decidir no Plan Mode, antes do código)

Cada questão tem no máximo três opções. As recomendações são propostas; a decisão
é minha.

### P1 — Nome, validação e origem do segredo do JWT (Q10)

**Problema.** A Q10 deixou o nome em aberto. Também falta decidir se a ausência
derruba a aplicação e como os testes obtêm um segredo sem que eu versione valor.

- **(a)** `JWT_SECRET`, obrigatória, com tamanho mínimo (ex.: 32 bytes); ausente
  ou curta derruba a criação da aplicação, como a `APP_ORIGIN` (2.1 D2), sem
  ecoar o valor. Nos testes, o `conftest` gera um valor aleatório em tempo de
  execução (`secrets`), antes de importar a app; nada fica escrito.
- **(b)** Igual a (a), mas o `verify.sh` exporta um valor fictício fixo, como já
  faz com `DATABASE_URL` locais.
- **(c)** Opcional: sem segredo, a app sobe e só o login falha (500/503).

**Consequências.** (a) e (b) repetem o risco da 2.1: o Render não sobe se eu não
configurar a variável antes do deploy; eu também preciso pôr a linha no meu
`backend/.env` (eu edito o `.env.example`, como na 2.1 D6). (b) versiona um valor,
ainda que fictício. (c) esconde erro de configuração até o primeiro login.

**Recomendação:** (a), com o nome `JWT_SECRET`.

### P2 — Bibliotecas de JWT e de Argon2 (dependências novas)

**Problema.** Não há biblioteca de JWT nem de Argon2 no projeto.

- **(a)** `PyJWT` (HS256) + `argon2-cffi` (`PasswordHasher` com os parâmetros
  padrão da biblioteca, Argon2id).
- **(b)** `PyJWT` + `pwdlib[argon2]` (camada acima do `argon2-cffi`).
- **(c)** `joserfc` ou `authlib` + `argon2-cffi`.

**Consequências.** (a) é a combinação mais direta e fácil de explicar; os
parâmetros padrão do Argon2id (64 MiB por hash) cabem no Render gratuito para a
carga do desafio e deixam cada login perto de dezenas de milissegundos. (b) traz
uma abstração que não uso. (c) tem API maior que o necessário. Descarto `passlib`
(sem manutenção) e `python-jose`. Versões fixadas pelo `uv.lock`.

**Recomendação:** (a).

### P3 — Claims, algoritmo, relógio e origem do papel

**Problema.** Definir o conteúdo mínimo do token e se o papel é confiado ao token
ou relido do banco.

- **(a)** Claims `sub` (id do usuário), `role`, `iat`, `exp`. A autorização usa só
  o token, sem consulta ao banco.
- **(b)** Claims `sub`, `iat`, `exp`. A dependência de autenticação carrega o
  usuário pelo `sub` a cada requisição autenticada (consulta por chave primária);
  usuário inexistente → 401; o papel vem do banco.
- **(c)** Como (b), mas com `role` também no token, só informativo.

Em todas: algoritmo fixo HS256 na decodificação (rejeita `none` e qualquer outro),
`exp` e `iat` obrigatórios, tolerância de relógio zero, relógio da aplicação
(UTC) para emitir e validar. O AD-6 trata a hora do banco para lance e
fechamento, não para expiração de sessão; registro essa leitura em vez de
estendê-la.

**Consequências.** (a) não toca o banco para autorizar, mas um token cujo
usuário não existe mais (ex.: banco recriado) passa na autenticação e quebra mais
adiante. (b) mantém uma única fonte de verdade e o mínimo de dados no token, ao
custo de uma consulta curta, que as rotas autenticadas futuras fariam de qualquer
forma; a dependência precisa ser síncrona (`def`) para rodar no threadpool, nunca
no event loop. (c) duplica a informação sem uso.

**Recomendação:** (b).

### P4 — Nome do cookie, `Secure` local × produção e noção de ambiente

**Problema.** O AD-29 exige `Secure` + `__Host-` em produção e `Secure=false` no
localhost. `__Host-` exige `Secure`. A aplicação não sabe em que ambiente está.

- **(a)** Derivar do esquema da `APP_ORIGIN`, sem variável nova: `https` → cookie
  `__Host-session`, `Secure`; `http` → cookie `session`, sem `Secure`, aceito só
  se o host for `localhost` ou `127.0.0.1` (outro host com `http` derruba a
  criação da app).
- **(b)** Criar `APP_ENV` (`development`/`production`) e decidir por ela.
- **(c)** Sempre `__Host-session` com `Secure`, inclusive local (os navegadores
  tratam `http://localhost` como contexto seguro, com diferenças entre eles).

Em todas: `HttpOnly`, `SameSite=Lax`, `Path=/`, sem `Domain`, `Max-Age` igual à
duração do token (8 h) e `Cache-Control: no-store` nas respostas de login,
logout e usuário atual.

**Consequências.** (a) reaproveita a configuração que já distingue o Render
(`https://...onrender.com`) do Vite (`http://localhost:5173`); o nome muda por
ambiente e o código precisa ler/apagar o nome certo. (b) cria a variável que a
1.3 e a 1.4 descartaram e abre combinações inconsistentes (`production` com
`http`). (c) contraria o AD-29 para desenvolvimento e depende do navegador; o
`curl` local em `http` não reenviaria o cookie.

**Recomendação:** (a). O nome `session` é proposta; posso escolher outro (ex.:
`casa_session`).

### P5 — Rotas e formato das respostas

**Problema.** A Q10 não nomeou as rotas de autenticação; o AD-30 já usa
`/api/me/wins`.

- **(a)** `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/me`.
- **(b)** Recurso de sessão: `POST /api/session` (login), `DELETE /api/session`
  (logout), `GET /api/session` (usuário atual).
- **(c)** `POST /api/login`, `POST /api/logout`, `GET /api/me`.

Corpo do login: `{"email": "...", "password": "..."}`. Resposta do login e de
`/api/me`: o mesmo objeto do usuário atual. Proposta: `{"email", "display_name",
"role"}` (sem `id`, que nenhuma tela usa ainda; o pseudônimo por lote vem na 3.5).

**Consequências.** (a) combina com `/api/me/wins` e é fácil de ler no Swagger.
(b) é mais REST, mas `DELETE` sem corpo ainda exige `Content-Type: application/json`
(consequência da 2.1), o que é estranho para o cliente. (c) mistura ações na raiz
da API.

**Recomendação:** (a), com o objeto proposto; login responde 200 com o usuário.

### P6 — Login inválido: status, código, mensagem, mecanismo e anti-enumeração

**Problema.** O critério pede formato único sem revelar se o e-mail existe. O
contrato da 2.1 escolhe o código pelo status e nunca expõe `detail` (D3); a 2.1
P2 descartou subclasses de exceção por erro.

- **(a)** 401 com código novo `invalid_credentials` e mensagem "E-mail ou senha
  inválidos.", devolvido pela rota com `error_response()` (sem exceção nova).
- **(b)** Como (a), mas por uma única exceção genérica `ApiError(status, code)`
  tratada pelo handler (uma classe, não uma por erro).
- **(c)** 401 com o código genérico `unauthorized` ("Autenticação necessária.").

Em todas: e-mail inexistente e senha errada seguem o mesmo caminho; quando o
e-mail não existe, verifico a senha contra um hash Argon2 fixo de referência para
o tempo de resposta ser comparável; e-mail normalizado (`strip` + minúsculas)
antes da busca; campos obrigatórios, `str` com limite de tamanho (ex.: e-mail até
254, senha até 1024, para não dar ao Argon2 entrada gigante); formato do e-mail
não validado (formato inválido → mesmo 401, sem dependência `email-validator`);
campo ausente ou vazio → 422 da 2.1. Sem limite de tentativas nesta story (ver
fora de escopo).

**Consequências.** (a) é o menor passo e mantém a 2.1 intacta, mas espalha
respostas de erro montadas à mão quando outras rotas precisarem de códigos
específicos (lances, na 3.4, terão vários). (b) cria o mecanismo reutilizável
agora, ao custo de uma classe e de um ajuste no handler. (c) dá mensagem ruim na
tela de login.

**Recomendação:** (b), com `invalid_credentials`. Se eu preferir adiar o
mecanismo, (a).

### P7 — Logout: política e status

**Problema.** Logout de quem tem token expirado ou inválido.

- **(a)** Rota pública e idempotente: sempre `204` e sempre apaga o cookie,
  com ou sem sessão válida.
- **(b)** Rota autenticada: sem sessão válida → 401 e o cookie não é apagado.

**Consequências.** (a) permite limpar um cookie expirado e nunca prende o usuário;
não revela nada. (b) deixa um cookie inválido no navegador até expirar. Em ambas,
o logout é `POST` com `Content-Type: application/json` (corpo `{}` ou vazio, P7 da
2.1) e protegido por `Origin`.

**Recomendação:** (a).

### P8 — Detalhes de 401 e 403

**Problema.** Códigos, precedência e efeitos colaterais.

- **(a)** Toda falha de autenticação (sem cookie, malformado, assinatura errada,
  expirado, algoritmo diferente, usuário inexistente) → 401 `unauthorized`;
  papel errado → 403 `forbidden`. Sem `WWW-Authenticate` (não há esquema
  padronizado para cookie). A resposta 401 não apaga o cookie.
- **(b)** Como (a), mas com código separado `session_expired` para token
  expirado, para a interface dizer "Sua sessão expirou".
- **(c)** Como (a), e todo 401 também apaga o cookie.

Precedência proposta, em todas: proteção da 2.1 (403 `csrf_*` / 415) → 401 →
403 de papel → 422 de validação → handler. Confiro no FastAPI instalado que
dependências que levantam erro vencem a validação do corpo e cubro com teste.

**Consequências.** (a) é a mais simples e não revela o motivo. (b) melhora a
mensagem, mas diferencia "expirado" de "adulterado". (c) faz uma leitura (GET)
alterar o estado do cliente; não fere o AD-19 (estado do servidor), mas mistura
responsabilidades.

**Recomendação:** (a).

### P9 — Mecanismo de declaração da política e teste

**Problema.** "Toda rota declara sua política" precisa de uma forma verificável,
incluindo rotas que não são `APIRoute` (documentação, SPA, WebSocket técnico).

- **(a)** Dependências marcadoras nas rotas: `Depends(public)`,
  `Depends(require_user)`, `Depends(require_role(UserRole.BIDDER))`; o teste
  percorre `app.routes` e exige exatamente uma marcação por `APIRoute` e
  `APIWebSocketRoute`; as rotas do framework e da SPA (`Route`/`Mount`) ficam numa
  lista explícita e nomeada de públicas, e qualquer outra rota fora dela reprova.
- **(b)** Um `APIRouter` por política (`public_router`, `authenticated_router`,
  `auctioneer_router`, `bidder_router`) com a dependência no router; o teste exige
  que toda rota tenha vindo de um deles.
- **(c)** Tabela central `(método, caminho) → política`, comparada pelo teste com
  `app.routes`.

**Consequências.** (a) deixa a política visível na própria rota e é fácil de
explicar; a marcação pública é um no-op. (b) concentra a política, mas rotas do
mesmo recurso ficam em routers diferentes e a origem da rota é mais difícil de
inspecionar. (c) separa a política da rota, e esquecer a tabela vira o mesmo
problema que o teste quer evitar.

**Recomendação:** (a), com um meta-teste que monta uma app com uma rota sem
política e prova que o verificador a reprova.

### P10 — Como testar 403 por papel sem rota de negócio

**Problema.** Nenhuma rota real desta story é restrita a um papel.

- **(a)** Rotas só de teste em `tests/synthetic_api.py` (precedente da 2.1), uma
  por papel, montadas numa app de teste com o banco de teste real.
- **(b)** Criar já uma rota real restrita (ex.: um esqueleto do painel do
  leiloeiro).

**Consequências.** (a) não publica nada novo e prova o mecanismo; o 403 real em
rotas de negócio é testado em cada story que as cria (2.3, 2.4, 3.1, 3.4, 3.6).
(b) antecipa funcionalidade fora do escopo.

**Recomendação:** (a).

### P11 — Estrutura mínima da tabela `users`

**Problema.** Tipo do id, normalização do e-mail, tipo do papel e colunas.

- **(a)** `id UUID PK` (sem default no banco: os IDs do seed são fixos),
  `email VARCHAR(254) NOT NULL UNIQUE` com `CHECK (email = lower(email))`,
  `password_hash TEXT NOT NULL`, `role VARCHAR(16) NOT NULL` com
  `CHECK (role IN ('AUCTIONEER','BIDDER'))`, `display_name VARCHAR(100) NOT NULL`,
  `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`.
- **(b)** Igual a (a), mas `role` como `ENUM` nativo do PostgreSQL (`user_role`).
- **(c)** Igual a (a), mas `id BIGINT` identidade.

**Consequências.** (a) usa UUID, coerente com a representação canônica do AD-21
(UUID em minúsculas) e com o AD-8 (ordem crescente de `user_id` funciona com
UUID); `VARCHAR + CHECK` é simples de migrar. (b) dá tipo forte no banco, mas
`ENUM` com Alembic exige cuidado em criação/remoção e alteração futura. (c)
expõe IDs sequenciais e diverge do UUID dos lotes. `display_name` serve para o
cabeçalho da interface; ele nunca aparece em auditoria nem comprovante (AD-20).
Carteira não entra aqui: nasce na 3.1 para todos os usuários existentes.

**Recomendação:** (a).

### P12 — Onde e quando o seed roda

**Problema.** O AD-24 quer seed na inicialização; a 2.1 garante que criar a app
não exige banco.

- **(a)** Passo próprio no `start.sh`, depois do `alembic upgrade head` e antes do
  `uvicorn` (ex.: `python -m app.seed`), com a função de seed testável
  isoladamente; `set -e` impede o servidor de subir se o seed falhar.
- **(b)** No `lifespan` do FastAPI.
- **(c)** Como migração de dados do Alembic.

Idempotência proposta, em todas: `INSERT ... ON CONFLICT (id) DO NOTHING`, numa
transação; nunca `UPDATE`. Se um e-mail semeado já existir com outro id, o seed
falha com erro claro (sem ecoar dados).

**Consequências.** (a) mantém `/health` e a criação da app sem banco, deixa claro
no log a ordem migrations → seed → tráfego e prepara a Q4 da 2.4/4.4 (catch-up
antes do seed). (b) faz cada `TestClient` tentar o banco e acopla a app ao banco
na subida. (c) mistura esquema com dados e roda uma vez só, contrariando "seed na
inicialização". Localmente, o README passa a mostrar o comando do seed.

**Recomendação:** (a).

### P13 — Contas e credenciais de demonstração

**Problema.** O avaliador precisa entrar na URL pública, então as senhas das
contas demo serão públicas de qualquer forma (README/roteiro). Ao mesmo tempo,
nada de segredo real pode ser versionado.

- **(a)** Senhas demo fixas, tratadas como credenciais públicas de demonstração
  (não segredos), definidas por mim, versionadas como constantes do seed e
  publicadas no README; o hash Argon2 é calculado na hora do seed.
- **(b)** Senhas lidas de variáveis de ambiente (ex.: `SEED_AUCTIONEER_PASSWORD`,
  `SEED_BIDDER_PASSWORD`), configuradas por mim no Render e no `.env`; o README
  diz onde o avaliador as encontra (entrega/README).
- **(c)** Hashes Argon2 pré-calculados versionados; senhas só no README.

E-mails propostos em domínio reservado (RFC 2606): `leiloeiro@example.com`,
`licitante1@example.com`, `licitante2@example.com`; nomes de exibição definidos
por mim; UUIDs fixos gerados uma vez na implementação e versionados (não são
segredos).

**Consequências.** (a) é a mais simples e reproduzível, e deixa explícito que
qualquer pessoa entra nas contas demo da URL pública (inerente ao desafio). (b)
evita senha no repositório, mas, se for para o README, o ganho some; acrescenta
variáveis e um modo de falha no deploy. (c) não esconde nada (a senha está no
README) e dificulta trocar a senha. Em todas, como o seed nunca altera usuário,
trocar a senha de uma conta existente exige ação manual no banco.

**Recomendação:** (a), com os valores escolhidos por mim no Plan Mode. Não
escrevo nenhuma senha nesta story.

### P14 — OpenAPI: 422 e respostas de erro

**Problema.** A 2.1 aceitou (P6, sem override de `app.openapi()`) que o schema
`HTTPValidationError` diverge do envelope real quando surgir a primeira rota com
parâmetros. O login é essa rota.

- **(a)** Aceitar e documentar a divergência, como previsto na 2.1.
- **(b)** Declarar `responses=` por rota com um modelo do envelope de erro
  (`ErrorResponse`) para 401/403/422. Quando a rota declara 422, o FastAPI não
  acrescenta o `HTTPValidationError` padrão; não há override global.

**Consequências.** (a) zero custo agora; o Swagger mostra um 422 que não existe.
(b) documentação fiel, ao custo de um modelo e de um dicionário de respostas
compartilhado; precisa ser aplicado às rotas futuras e o teste de OpenAPI passa a
conferir isso. Em ambas, `test_openapi.py` deixa de fixar `paths == ["/health"]`
e passa a listar as rotas novas.

**Recomendação:** (b), confirmando o comportamento no FastAPI 0.162 instalado;
se não se confirmar sem override, (a).

### P15 — Front-end: estrutura, mensagens e testes

**Problema.** O `epics.md` pede tela de login. Não há roteador nem ferramenta de
teste de front (Q10 aberta).

- **(a)** Sem dependência nova: `App.tsx` decide entre o formulário de login e
  um cabeçalho com nome, papel ("Leiloeiro"/"Licitante") e "Sair", a partir de
  `GET /api/me` ao carregar; cliente tipado em `src/api/auth.ts`; mensagens de
  erro em português mapeadas pelo `code` do contrato; validação manual pelo Vite e
  no deploy, registrada na story; sem testes de front nesta story.
- **(b)** Como (a), mais um roteador (`react-router`) com rota `/login`.
- **(c)** Como (a), mais a ferramenta de testes do front (ex.: Vitest + Testing
  Library), fechando essa parte da Q10.

**Consequências.** (a) entrega o critério com o mínimo e deixa roteador para a
2.5 (vitrine e página do lote), que precisa dele de verdade. (b) antecipa decisão
de navegação. (c) aumenta o escopo e o `verify`, mas cria a base de testes do
front mais cedo.

**Recomendação:** (a). Mensagens pelo `code` (não pelo texto do servidor), para
a interface controlar o português exibido.

### P16 — `hide_parameters=True` no engine (`deferred-work.md`)

**Problema.** A partir desta story há e-mail e hash no banco; um traceback do
SQLAlchemy no log pode trazer parâmetros da consulta.

- **(a)** Ligar `hide_parameters=True` em `create_db_engine()` agora, com teste.
- **(b)** Manter adiado.

**Consequências.** (a) custo mínimo e reduz exposição no log do Render; o
diagnóstico de erro perde os valores dos parâmetros. (b) mantém o risco já
registrado.

**Recomendação:** (a), e retirar o item do `deferred-work.md`.

### Orientação técnica (não é decisão nova)

- Sessão de banco por requisição: dependência síncrona com `Session` curta, engine
  criada sob demanda (não na criação da app), para manter `/health` e o import
  sem banco. Nos testes, a dependência aponta para o banco `_test`.
- Isolamento entre testes que gravam usuários: limpar ou reverter por teste no
  banco `_test`; nunca tocar no banco de desenvolvimento. O mecanismo exato é
  escolhido no plano técnico.

## Tarefas e subtarefas

- [x] **T1 — Planejar comigo (todas as CAs).** Decidir P1 a P16 no Plan Mode e
  registrá-las nesta story, em primeira pessoa e com a alternativa descartada,
  antes de qualquer código. Registrar a resolução da parte da Q10 (segredo do JWT
  e rotas de autenticação) em `docs/ARQUITETURA.md`, seção de questões e
  histórico, sem alterar AD.
- [x] **T2 — Dependências e configuração (CA12, P1, P2, P4).** Adicionar as
  bibliotecas aprovadas com `uv`; configuração do segredo e do modo do cookie,
  validada e sem eco. Eu acrescento a linha do segredo no `backend/.env.example`
  e no meu `.env`.
- [x] **T3 — Migração e modelo (CA11, P11, P16).** Revisão Alembic `users`
  com `downgrade`; modelo SQLAlchemy; `UserRole`; ajuste do engine se P16 (a).
- [x] **T4 — Senha e token (CA2, CA3, CA7, P2, P3, P6).** Hash/verificação Argon2,
  hash de referência para e-mail inexistente; emissão e validação do JWT com
  algoritmo fixo e claims obrigatórias.
- [x] **T5 — Política de acesso (CA6, CA7, P8, P9, P10).** Dependências de
  política; classificação de todas as rotas existentes (`/health`, docs, SPA,
  WebSocket técnico); teste de política e meta-teste.
- [x] **T6 — Rotas (CA2–CA5, CA8, P5, P6, P7, P14).** Login, logout e usuário
  atual; cookie com atributos por ambiente; `no-store`; códigos de erro novos no
  catálogo; OpenAPI conforme P14.
- [x] **T7 — Seed (CA1, P12, P13).** Função idempotente de seed, ponto de entrada
  e passo no `start.sh`; constantes de IDs/e-mails/nomes; sem rota de cadastro.
- [x] **T8 — Remover o cookie técnico (CA9).** Rota, constantes, testes e seção do
  README; docstring do `infra_check.py` atualizada; WebSocket técnico intacto e
  marcado como público.
- [x] **T9 — Interface (CA10, P15).** Tela de login, estado do usuário, "Sair",
  mensagens em português, tipos dos contratos; validação manual pelo proxy do Vite.
- [x] **T10 — Testes (CA13).** Matriz abaixo, em PostgreSQL real onde houver banco.
- [x] **T11 — Verificar e documentar (CA13).** `./verify.sh` completo com a saída
  real; README (login local, comando do seed, contas demo conforme P13, variável
  nova no Render, limitação do logout, validação pós-deploy do cookie real);
  `docs/uso_de_ia.md`; esta story e `sprint-status.yaml` para `review`. Parar na
  2.2.

## Matriz de testes esperados

| Grupo | Casos |
| --- | --- |
| Senha | Hash começa com `$argon2id$`; verificação certa e errada; senha nunca guardada em texto; hash de referência usado quando o e-mail não existe. |
| Token | Válido; expirado; assinatura com outro segredo; `alg: none`; outro algoritmo; sem `exp`/`sub`; malformado; `sub` de usuário inexistente (se P3 b); claims sem e-mail, nome ou hash. |
| Configuração | Segredo ausente/curto falha na criação da app sem ecoar o valor; modo do cookie por `APP_ORIGIN` (P4): `https` → `__Host-`+`Secure`; `http://localhost` → sem `Secure`; `http` com outro host recusado. |
| Login | 200 com o usuário; `Set-Cookie` com `HttpOnly`, `SameSite=Lax`, `Path=/`, sem `Domain`, `Max-Age` de 8 h e `Secure`/`__Host-` conforme o modo; token fora do corpo; `no-store`; e-mail com maiúsculas/espaços normalizado. |
| Login inválido | E-mail inexistente e senha errada: mesmo status, código, mensagem e corpo byte a byte; sem `Set-Cookie`; e-mail não ecoado; campos ausentes → 422 sem `input`; entrada acima do limite → 422. |
| Proteção 2.1 | Login e logout com `Origin` estrangeiro, sem `Origin`/`Referer` e sem JSON → 403/415 e nenhum cookie emitido nem handler executado; GET/HEAD/OPTIONS no login → 405 sem cookie; nenhum cabeçalho CORS. |
| Usuário atual | Com cookie válido → papel e dados do P5; sem cookie, expirado, adulterado → 401 no formato único; `no-store`. |
| Logout | Apaga o cookie com o mesmo nome e atributos; comportamento sem sessão conforme P7; depois do logout, sem cookie, `/api/me` → 401. |
| Papéis | Rotas sintéticas por papel (P10): BIDDER em rota de AUCTIONEER → 403, e o inverso; sem login → 401; precedência da P8 (CSRF antes de 401; 401 antes de 422). |
| Política | Toda rota da app real (com e sem SPA) tem política; meta-teste reprova app com rota sem política; nenhuma rota de cadastro (`/api/auth/register`, `/api/users` etc. → 404/405). |
| Seed (PostgreSQL) | Banco vazio → exatamente 3 usuários com IDs, papéis e e-mails esperados; segunda execução não muda nenhuma coluna (comparar linhas antes/depois); e-mail semeado com outro id → falha clara; senhas em Argon2. |
| Migração | `upgrade head` e `downgrade` da revisão nova no banco de teste; CHECKs de papel e e-mail recusam valores inválidos. |
| Regressão | `/health` 200 sem banco; criar a app sem banco; docs e schema; SPA e fallback; WebSocket técnico igual; `GET /api/infra-check/cookie` → 404 JSON; OpenAPI com as rotas novas (P14). |
| Front | `lint`, `tsc --noEmit` e build no `verify`; validação manual pelo Vite registrada (entrar, recarregar logado, credenciais inválidas, sair). Testes automatizados só se P15 (c). |

Não afrouxo nenhum teste existente; asserções sobre o cookie técnico saem junto
com a rota (CA9), não por enfraquecimento.

## Arquivos prováveis

| Área | Arquivo | Ação |
| --- | --- | --- |
| Back-end | `backend/app/main.py` | alterado (rotas, política, sessão) |
| Back-end | `backend/app/config.py` | alterado (segredo, modo do cookie) |
| Back-end | `backend/app/db.py` | alterado (sessão por requisição; P16) |
| Back-end | `backend/app/errors.py` | alterado (códigos novos; P6 b) |
| Back-end | módulos novos para usuários/modelo, senha+token, política de acesso, rotas de autenticação e seed (nomes no plano técnico) | novos |
| Back-end | `backend/app/infra_check.py` | alterado (remove o cookie) |
| Migração | `backend/migrations/versions/0002_*.py` | novo |
| Infra | `backend/scripts/start.sh` | alterado (seed, P12) |
| Infra | `backend/pyproject.toml`, `backend/uv.lock` | alterados (P2) |
| Infra | `verify.sh` | só se P1 (b) |
| Testes | `backend/tests/conftest.py`, `synthetic_api.py`, `test_infra_check.py`, `test_openapi.py`, `test_config.py` | alterados |
| Testes | testes novos de senha/token, política, login e seed (integração em `tests/integration/`) | novos |
| Front-end | `frontend/src/App.tsx`, `App.css`, `src/api/auth.ts` (novo) | alterados/novo |
| Docs | `README.md`, `docs/uso_de_ia.md`, `docs/ARQUITETURA.md` (resolução da Q10), `CLAUDE.md` (item 10, só se eu pedir) | alterados |
| BMAD | esta story, `sprint-status.yaml`, `deferred-work.md` (P16) | alterados |
| Eu | `backend/.env.example` e `backend/.env` (linha do segredo, sem valor real no exemplo) | editados por mim |
| Sem mudança | `Dockerfile`, `compose.yaml`, `app/spa.py`, `app/csrf.py`, `0001_baseline.py`, `test_health.py` | intocados |

## Segurança

- Nenhum valor de segredo em código, testes, README, story, logs ou respostas. O
  agente não lê nem altera `.env*`.
- Senhas só como Argon2id; nenhuma senha ou hash em log ou resposta.
- Token só no cookie HttpOnly; nunca no corpo, na URL ou em `localStorage`.
- Mensagem de login inválido idêntica para e-mail inexistente e senha errada.
- Sem CORS, sem rota de cadastro, sem endpoint de debug.
- Antes do próximo deploy, eu configuro a variável do segredo no Render (CA12); o
  agente não acessa o painel.

## Fora de escopo

- Carteira e depósito (3.1), lotes e lote demo (2.4), busca no museu (2.3),
  vitrine (2.5), lances (3.x), sala/WebSocket real e Q2 (4.1), pseudônimo (3.3).
- Cadastro público (D2 = A), troca e recuperação de senha, refresh token,
  revogação de token no servidor, sessão no banco, "lembrar de mim".
- Limite de tentativas de login / bloqueio por força bruta (registrar como
  limitação no README, se eu decidir).
- `check_needs_rehash` e troca de parâmetros do Argon2.
- Roteador e identidade visual do front (2.5 e 6.2), dark mode.
- Remoção do WebSocket técnico (4.1). Mudança no `Dockerfile` ou no deploy além
  da variável nova e do passo de seed.
- Não crio a Story 2.3 e não uso git.

## Decisões fechadas (P1 a P16, OQ-1 a OQ-3)

Decidi tudo antes do código, com a spec em
`_bmad-output/specs/spec-story-2-2-login-papeis-politica-de-acesso/`. Registro aqui
cada decisão e a alternativa que descartei.

| Questão | Decidi | Descartei |
| --- | --- | --- |
| P1 segredo do JWT | `JWT_SECRET`, obrigatório, mínimo de 32 caracteres, derruba `create_app()` sem ecoar o valor; os testes geram um valor aleatório a cada execução | segredo fictício fixo no `verify.sh`; segredo opcional com falha só no primeiro login |
| P2 bibliotecas | `PyJWT` e `argon2-cffi` (Argon2id, parâmetros padrão) | `pwdlib`; `joserfc`/`authlib`; `passlib` e `python-jose` (sem manutenção) |
| P3 claims | `sub`, `role`, `iat`, `exp`, HS256 fixo, tolerância zero; o banco é a autoridade do papel (usuário ausente ou papel diferente invalida a sessão) | confiar só no token; guardar o papel no token só como informação |
| P4 cookie | sem `APP_ENV`: `https` usa `__Host-auction_session` com `Secure`; `http` só em localhost, sem `Secure` | criar `APP_ENV`; sempre `__Host-` com `Secure`, inclusive local |
| P5 rotas | `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/me`; resposta `{email, role}` | `/api/session`; `/api/login`; devolver `display_name` ou `id` |
| P6 login inválido | 401 `invalid_credentials`, "E-mail ou senha inválidos.", corpo idêntico; Argon2 contra hash de referência quando o e-mail não existe | código genérico `unauthorized`; hierarquia de exceções |
| P7 logout | `POST` público e idempotente, sempre 204 e sempre apaga o cookie | exigir sessão válida para sair |
| P8 401 e 403 | 401 `unauthorized` para qualquer sessão inválida, 403 `forbidden` para papel errado; sem `WWW-Authenticate`; 401 não apaga cookie; sem ordem global 401, 403, 422 nem middleware de autenticação | código `session_expired`; apagar o cookie em todo 401 |
| P9 política | metadata nossa gravada pelos helpers `api_route`/`websocket_route`; app real sem `include_router` nem `APIRouter`; meta-teste percorre `app.routes` só com API pública | dependências marcadoras com `iter_route_contexts` (não documentada); um `APIRouter` por política; tabela central |
| P10 papéis sem rota de negócio | rotas sintéticas só nos testes | criar já uma rota real restrita |
| P11 `users` | `id UUID`, `email` minúsculo único, `password_hash`, `role` com CHECK; sem `display_name` nem `created_at` | `ENUM` nativo; `id` sequencial |
| P12 seed | `python -m app.seed` entre as migrations e o uvicorn no `start.sh`; `ON CONFLICT DO NOTHING`, nunca `UPDATE` | seed no `lifespan`; seed como migration de dados |
| P13 contas demo | `auctioneer@example.com`, `bidder1@example.com`, `bidder2@example.com`, senha pública de demonstração documentada no README | senhas em variáveis de ambiente; hashes pré-calculados |
| P14 OpenAPI | `responses=error_responses(...)` por rota, sem override de `app.openapi()`; `HTTPValidationError` some do schema | aceitar a divergência do 422 |
| P15 front | sem dependência nova, sem roteador, sem biblioteca de testes; mensagens mapeadas pelo `code`, nunca pelo texto do servidor | `react-router`; Vitest com Testing Library |
| P16 engine | `hide_parameters=True` agora | manter adiado |
| OQ-1 | `http` só com `localhost`, `127.0.0.1` ou `::1`; outro host impede o boot | aceitar `http` remoto com cookie sem `Secure` |
| OQ-2 | `OPTIONAL` trata sessão ausente ou inválida como anônima | responder 401 em rota opcional |
| OQ-3 | `error_response(401, "invalid_credentials")` na própria rota | `ApiError` genérico |

## Registro de implementação (24/10/2026)

Implementei a partir da spec, sem git, sem deploy e sem ler `.env*`.

**Back-end.** `app/users.py` e a migration `0002_users.py`; `app/security.py`
(Argon2id, hash de referência, JWT HS256); `app/access.py` (políticas, helpers,
`resolve_session_user`); `app/auth.py` (login, logout, `/api/me`); `app/seed.py`;
`AuthSettings` e a derivação do cookie em `app/config.py`; `hide_parameters`,
`get_engine` e `get_session` em `app/db.py`; `invalid_credentials`,
`ErrorResponse` e `error_responses()` em `app/errors.py`; `main.py`, `spa.py` e
`infra_check.py` passam a registrar tudo pelos helpers; o cookie técnico da 1.4
saiu e o WebSocket técnico ficou igual, como rota pública; `start.sh` roda o seed.

**Front-end.** `api/auth.ts`, `LoginForm.tsx`, `SiteHeader.tsx`, `App.tsx`,
`App.css` e `index.css` (tokens do DESIGN.md), sem dependência nova. A linha de
estado do `/health` ficou como texto discreto no rodapé.

### Desvios e correções durante a implementação

- **`rowcount` do seed.** O `INSERT` multilinha do psycopg devolvia `-1`; os testes
  de seed pegaram isso. Passei a contar as linhas do `RETURNING id`.
- **Teste de `hide_parameters`.** A spec pedia um e-mail marcador na violação de
  UNIQUE. O PostgreSQL escreve a chave duplicada (o e-mail) no `DETAIL` da própria
  mensagem de erro, e `hide_parameters` não controla isso. Mantive a intenção do
  teste (os valores dos parâmetros não aparecem): o marcador vai no
  `password_hash`, que não é a chave violada. Consequência: numa colisão de e-mail
  no seed, o e-mail semeado (público) aparece no log. **Correção do code review
  (L1):** `hide_parameters` só impede o SQLAlchemy de renderizar os valores dos
  parâmetros; o `DETAIL` escrito pelo próprio PostgreSQL pode conter valores. Numa
  violação de UNIQUE ele mostra a chave (o e-mail); numa violação de CHECK mostra a
  linha inteira, inclusive o `password_hash` (reproduzido no review). Hoje nenhum
  caminho do código viola as CHECKs de `users` (o seed só grava constantes válidas
  e não há outra escrita). Corrigi o comentário de `app/db.py`; não criei
  sanitização de exceções do PostgreSQL nesta story.
- **`tests/test_errors.py`.** O teste fixa o catálogo de mensagens por igualdade
  exata. Acrescentei a entrada `invalid_credentials` (exigida pela spec) e mantive
  a igualdade exata; a spec previa o arquivo inalterado.
- **`backend/migrations/env.py`.** O Ruff reprovava a ordem dos imports (já no
  estado anterior à story, reproduzi com a árvore do baseline). Reordenei os
  imports; nenhuma mudança de comportamento. Arquivo fora da lista prevista.
- **`pyproject.toml`.** Além das duas dependências, configurei
  `extend-immutable-calls = ["fastapi.Depends"]` no Ruff, para o estilo
  `= Depends(...)` que a spec adotou não acionar a regra B008.
- **Testes de tabelas.** `get_table_names` não vem ordenado; o teste de
  `test_database.py` compara `sorted(...)`.

### Evidências (comandos executados)

`./verify.sh` completo, exit 0:

- `ruff check`: All checks passed!
- `ruff format --check`: 39 files already formatted
- `pytest`: 568 passed, 1 warning in 9.71s (PostgreSQL real, banco `_test`)
- ESLint, `tsc --noEmit` e build do Vite: sem erros (21 módulos; CSS 3,02 kB, JS 225,43 kB)
- `docker build`: ok; "verify.sh: todas as etapas passaram."

Verificações extras, fora do `verify.sh`:

- `uvicorn` com o build da SPA e o banco `_test`: login errado 401
  `invalid_credentials`; login válido 200 com `Set-Cookie` (`HttpOnly`, `Max-Age=28800`,
  `Path=/`, `SameSite=lax`, sem `Secure` em `http://localhost`); `GET /api/me` 200;
  logout 204 com `Max-Age=0`; `/api/me` 401 depois; `GET /api/infra-check/cookie`
  404 JSON; logout sem `Content-Type` JSON 415.
- Imagem Docker contra o banco `_test` do Compose: o log mostrou o Alembic, depois
  `seed: 3 user(s) inserted`, depois o uvicorn; `/health` 200, login 200, `/api/me`
  200, `/favicon.svg` 200.

**Ainda não feito (é meu):** o roteiro manual no navegador (test-plan §5) e a
repetição dos passos 5 a 8 na URL pública depois de pôr `JWT_SECRET` no Render.

### Riscos e limitações restantes

- O próximo deploy no Render falha se `JWT_SECRET` (e `APP_ORIGIN`) não estiverem
  no painel antes.
- Token copiado antes do logout vale até o `exp` (AD-29); sem limite de tentativas
  de login.
- Colisão de e-mail no seed mostra o e-mail semeado no log; uma violação de CHECK
  mostraria a linha inteira no `DETAIL` do PostgreSQL (ver desvios).
- A hora da sessão é a da aplicação, não a do banco (o AD-6 rege lance e
  fechamento).
- O teste de política protege só rotas registradas pelos helpers; quem usar
  `@app.get` direto reprova no `pytest`, que é o desejado.
- Sem testes automatizados de front-end (Q10 segue aberta); a tela só foi
  verificada por lint, tipos, build e pelas chamadas HTTP acima.

## Ajuste visual após o teste manual (24/10/2026)

Meu teste manual no navegador aprovou o comportamento (login inválido, as três
contas demo, papel em português, refresh, logout e `/health`), mas encontrei um
problema visual em desktop: o formulário ficava deslocado para a esquerda, com
espaço vazio excessivo, e header, conteúdo e rodapé não pareciam do mesmo grid.

**Causa.** O header usava a largura inteira da janela, enquanto o `main` e o
rodapé ficavam num container de 72rem; dentro do `main`, o formulário de 22rem
ficava alinhado à esquerda desse container.

**Decidi** uma só estrutura horizontal, `.page-container` (largura máxima de
72rem, margens laterais de 1rem e, a partir de 48rem, de 2rem), usada pelo
conteúdo do header, pelo `main` e pelo rodapé. O divisor do header continua de
borda a borda. O shell `.app` é uma coluna flex com altura mínima da janela; o
`main` ocupa o espaço entre header e rodapé (`flex: 1`, também coluna flex), e a
coluna do login (`.main-column`, 24rem) usa `margin: auto`, o que a centraliza na
horizontal e na vertical sem recortar o conteúdo quando falta altura. O texto
dentro da coluna segue alinhado à esquerda. (Correção do code review, L5: uma
versão anterior deste parágrafo citava `clamp`, que não está no CSS final.) Mudei só `App.css`, `SiteHeader.tsx` (um `div` interno) e as
classes de `main` e rodapé em `App.tsx`; nenhum estado, texto ou comportamento mudou.

**Descartei** colocar o formulário num card com sombra ou fundo (o DESIGN.md pede
formulário como campos e divisores) e centralizar também o texto dentro da coluna.

**Verificação:** lint, `tsc --noEmit` e build sem erros; `./verify.sh` completo,
exit 0 (Ruff ok, 39 arquivos formatados, 568 testes passaram em 9.35s, ESLint,
tipos, build do Vite e `docker build` ok). A conferência visual em desktop largo e
em 320 px continua sendo minha, no navegador.

## Correções do code review (24/10/2026)

O `bmad-code-review` (Opus, sessão separada) não encontrou BLOCKER nem HIGH;
apontou 1 MEDIUM e 5 LOW. Aprovei a correção de todos, sem mudar decisão da spec
nem AD.

- **M1 — a política declarada precisa estar aplicada na rota.** O verificador
  confiava só na metadata da função: um endpoint marcado `AUCTIONEER` e
  reaproveitado por `@app.get` empilhado ou `app.add_api_route` virava uma rota
  aberta (200 sem login) que `policy_problems` não acusava e `policy_by_route`
  mostrava como `AUCTIONEER`. Mantive a metadata e o desenho dos helpers (P9); em
  `tests/access_policy.py` o verificador agora também confere `route.dependencies`
  (atributo público, nunca `route.dependant`): a rota precisa carregar a
  dependência de `POLICY_DEPENDENCIES` da política declarada. Rota sem ela, ou
  `Route`/`WebSocketRoute` puras com metadata (que não carregam dependências),
  reprovam com "política X sem a dependência", e saem de `policy_by_route`.
  Regressões em `test_access_policy.py`: decoradores empilhados (a rota protegida
  passa, a aberta reprova, e o teste confirma 401 numa e 200 na outra);
  `add_api_route` reaproveitando endpoint `BIDDER`; endpoint `AUCTIONEER`
  reaproveitado com `require_user` (dependência diferente da declarada); `Route` e
  `WebSocketRoute` puras com metadata; rota registrada pelo helper continua
  passando; WebSocket técnico `PUBLIC` continua passando. Isso amplia a lista de
  estruturas públicas que o verificador lê (backend-contract §9), sem mudar a
  decisão.
- **L1 — `hide_parameters`.** Comentário de `app/db.py` corrigido; nota nos
  desvios e nos riscos acima.
- **L2 — hash de referência.** O teste do e-mail inexistente observa
  `security.verify_password` (com `wraps`, a verificação Argon2 real roda) e
  confere que ela recebe exatamente o hash de referência (`$argon2id$`) e a senha
  enviada; com e-mail existente, recebe o hash do usuário, nunca o de referência.
  Produção inalterada.
- **L3 — seed independente.** O subprocesso roda `app.seed` como `__main__` (via
  `runpy`, como `python -m`) e sai com 42 se `app.main` estiver em `sys.modules`.
  Tirar `APP_ORIGIN`/`JWT_SECRET` do ambiente não provava nada sozinho, porque as
  configurações também leem o `backend/.env`.
- **L4 — `aria-invalid`.** Em `LoginForm.tsx`, os campos só ficam com
  `aria-invalid="true"` (e a borda de erro, que o CSS liga a esse atributo) em
  validação e `invalid_credentials`; servidor indisponível e recusa (`rejected`)
  mostram a mensagem, ligada por `aria-describedby`, sem marcar os campos. Nenhum
  texto, layout ou CSS mudou.
- **L5 — documentação visual.** O parágrafo do ajuste visual agora descreve o CSS
  real (`margin: auto` no shell flex), não `clamp`.
- **Fora desta story:** `websocket_route` com política diferente de `PUBLIC` quebra
  (as dependências esperam `Request`); registrei em `deferred-work.md` para a 4.1.

**Evidências (comandos executados):**

- Testes direcionados (`test_access_policy.py`, `integration/test_auth_flow.py`,
  `integration/test_seed.py`, `integration/test_database.py`,
  `test_infra_check.py`): 116 passed, 1 warning in 5.13s.
- Front: `npm run lint`, `npm run typecheck` e `npm run build` sem erros (21
  módulos; CSS 3,17 kB, JS 225,64 kB).
- `./verify.sh` completo, exit 0: `ruff check` "All checks passed!"; `ruff format
  --check` "39 files already formatted"; `pytest` "574 passed, 1 warning in 9.40s"
  (PostgreSQL real; o aviso é a depreciação de `httpx` no `starlette.testclient`,
  sem relação com a story); ESLint, `tsc --noEmit` e build do Vite ok; `docker
  build` ok; "verify.sh: todas as etapas passaram."

Não refiz o teste manual no navegador depois do L4 (é meu): conferir que, com o
uvicorn parado, "Não foi possível falar com o servidor. Tente novamente." aparece
sem borda vermelha nos campos, e que senha errada continua marcando os campos.

## Registro e status

Status: **done**. Implementada em 24/10/2026; correções do code review aplicadas
no mesmo dia. Não marco `done` antes do re-review final.
