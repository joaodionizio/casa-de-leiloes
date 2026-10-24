# Story 2.1 — Formato de erros + validação de Origin

Status: done

Chave do sprint: `2-1-formato-de-erros-e-validacao-de-origin`
Épico: 2. Data de criação: 24/10/2026.

## Story e objetivo

Como usuário da aplicação, quero receber falhas da API em um formato previsível,
com mensagens claras e sem detalhes internos, e impedir que requisições de outra
origem alterem estado, para ter uma base de segurança HTTP antes da autenticação.

Nesta story delimito somente o contrato de erros e a proteção HTTP por
Origin/Referer e conteúdo JSON. Não antecipo autenticação. O status
`ready-for-dev` indicava o artefato criado; as escolhas foram resolvidas comigo
no Plan Mode antes da implementação (seção “Decisões”). A story está em `review`.

## Fontes e base real

Uso `CLAUDE.md`, `docs/ARQUITETURA.md` (especialmente AD-19, AD-29 e AD-30),
`_bmad-output/planning-artifacts/epics.md` (2.1 e limites com 2.2/4.1),
`sprint-status.yaml` e as stories anteriores somente como contexto da fundação.

- Considero o Epic 1 concluído conforme a instrução desta sessão. O YAML ainda
  registra `epic-1: in-progress` e 1.4 como `review`; não reavalio nem altero
  esses registros históricos nesta criação. As stories 1.2 e 1.3 estão `done`.
- Não encontrei artefato separado da Story 1.1. Uso os registros de dependências
  nas stories 1.2/1.3 e os arquivos existentes para entender essa base, sem
  inventar evidência de conclusão ou execução de testes.
- `backend/app/main.py` expõe `create_app`, `/health`, Swagger em `/api/docs`,
  schema em `/api/openapi.json`; Redoc e redirect OAuth2 estão desativados.
- PostgreSQL, SQLAlchemy síncrono, Alembic e Docker já existem. `/health` é
  liveness estático, sem banco; importar/criar a app não deve exigir banco.
- `backend/app/spa.py` registra o fallback por último, somente GET/HEAD;
  `/api` e `/api/*` nunca viram `index.html`. Assets ausentes retornam 404.
- `frontend/vite.config.ts` encaminha `/api` e `/health` ao uvicorn em
  `http://127.0.0.1:8000`; a origem vista pelo navegador é a do Vite. O proxy
  usa o atalho em string, que liga `changeOrigin: true` no Vite 8.3.5: isso troca
  o `Host` para `127.0.0.1:8000`, mas não o `Origin`, que chega ao backend como o
  navegador o enviou (`http://localhost:5173`). Corrigi aqui a suposição anterior;
  como a comparação usa `APP_ORIGIN` e não o `Host`, o desenho não muda. A porta
  5173 é o padrão do Vite; a D4 a fixou com `strictPort`. A imagem serve o build pelo FastAPI, na
  mesma origem da API.
- A 1.4 registra deploy público no Render em
  `https://casa-de-leiloes-i1xr.onrender.com` (README). `backend/scripts/start.sh`
  executa migrations e uvicorn, sem `--proxy-headers`/`--forwarded-allow-ips`.
  A decisão P8 rejeitou confiar preventivamente em qualquer IP; a P10 rejeitou
  `APP_ENV` e deixou `Secure=false` local para a 2.2. Uma configuração de origem
  nesta story seria a primeira dependente de ambiente, e a 2.2 vai precisar
  distinguir dev/produção para o cookie: registro a relação, sem decidir aqui.
- Versões instaladas (`backend/uv.lock`): FastAPI 0.162.0 e Starlette 1.9.0.
  Conferi no código instalado: `strict_content_type` vem ligado por padrão;
  corpo sem `Content-Type` não é lido como JSON, e só `application/json` ou
  `application/*+json` são lidos como JSON. Isso vale apenas para rotas que
  declaram corpo, onde o resultado é 422 de validação, não 415. Uma rota de
  escrita sem corpo declarado (como um futuro logout ou DELETE) ignora corpo e
  `Content-Type`. JSON malformado vira `RequestValidationError` com
  `type: "json_invalid"`, e o erro padrão inclui `input` e `ctx`.
- No Starlette, um handler para `Exception` roda no `ServerErrorMiddleware`,
  que envia a resposta e relança a exceção (o log do servidor a registra); o
  `TestClient` só mostra o 500 com `raise_server_exceptions=False`. Uma
  `HTTPException` levantada dentro de um middleware HTTP fica fora do
  `ExceptionMiddleware` e não passa pelos handlers: a camada de proteção
  precisa produzir ela mesma a resposta no formato único.
- `GET /api/infra-check/cookie` emite `__Host-infra_check=1`, sem usuário,
  JWT ou estado no servidor, e retorna `cookie_received`. É sempre Secure,
  HttpOnly, SameSite=Lax, Path=/, sem Domain, com Max-Age=600 e no-store.
- `/api/infra-check/ws` faz um eco técnico e fecha. Sua checagem atual permite
  Origin ausente e compara host quando presente. Não reutilizo essa política
  limitada como definição de mesma origem para HTTP.
- Ainda não há usuários, autenticação, JWT, roles, política de acesso nem
  padronização própria de erros. Há respostas padrão FastAPI/Starlette.
- Não localizei skill/comando local `bmad-create-story`; sigo a estrutura dos
  artefatos existentes e as instruções explícitas desta solicitação.

## Critérios de aceitação

1. **CA1 — Contrato único e mínimo.** Dado um erro HTTP da API, quando respondo,
   uso JSON estruturado capaz de representar status HTTP, código técnico
   estável em inglês, mensagem em português e detalhes opcionais. O status
   representado coincide com o status da resposta. O cliente não precisa
   interpretar a mensagem para identificar o erro. Fecho nomes, tipos e
   envelope em P1/P2, sem framework novo ou hierarquia extensa de exceções.
2. **CA2 — Erros previstos e roteamento.** Dadas exceções HTTP previstas,
   preservo o status e cabeçalhos necessários, como `Allow`, e aplico o
   contrato inclusive a 404 de rota desconhecida sob `/api` e 405. O mecanismo
   representa 400, 401, 403, 404 e 409 sem criar rotas de negócio para provocá-los.
   401 é somente compatibilidade futura; não verifico identidade ou permissão.
3. **CA3 — Validação 422.** Dada entrada inválida em uma rota de teste com
   validação FastAPI, respondo 422 no mesmo envelope, com detalhes úteis e
   sanitizados sobre os campos. Não devolvo automaticamente corpo recebido,
   `input`, contexto interno ou valores sensíveis. Defino em P6 o mapeamento
   das mensagens e de JSON malformado; erros internos de validação de resposta
   não são atribuídos ao cliente como 422.
4. **CA4 — Falha inesperada.** Dada exceção inesperada antes do envio da
   resposta HTTP da API, respondo 500 genérico em português, sem stack trace,
   SQL, caminhos internos, credenciais ou texto bruto da exceção. Registro a
   falha no servidor para diagnóstico sem registrar cookies, headers de
   autenticação ou corpos sensíveis. Cubro também a integração com a camada
   de proteção; erros gerados por ela não escapam do contrato. Não prometo
   reescrever respostas já iniciadas, falhas de boot ou erros do proxy Render.
5. **CA5 — Métodos de escrita.** Para POST, PUT, PATCH e DELETE das APIs,
   aplico a proteção antes da execução do handler e independentemente de
   existir cookie. Aceito Origin da origem esperada e rejeito estrangeiro com
   403 estruturado, sem executar a ação. A futura rota de login também usará
   esta proteção, mesmo sendo pública; não crio exceção de autenticação agora.
6. **CA6 — Comparação e fallback.** Comparo origem por esquema, host e porta
   efetiva, com parsing e normalização definidos no planejamento, nunca por
   substring, sufixo de domínio ou somente host. Se Origin está presente, ele
   tem precedência: valor estrangeiro, `null`, malformado ou ambíguo não é
   resgatado por Referer válido. Se Origin falta, posso aceitar Referer válido
   da mesma origem, extraindo sua origem e ignorando caminho/query. Referer
   estrangeiro ou inválido é recusado. Quando ambos faltam, recuso com 403 (P4);
   não há liberação implícita.
7. **CA7 — Origem confiável e ambientes.** Uso a origem configurada exigida
   pelo AD-29. O planejamento define a fonte, o nome da configuração e a
   validação. Host, Forwarded e X-Forwarded-* arbitrários não podem escolher
   a origem aceita. Distingo HTTPS público do Render do HTTP interno e a
   origem externa do Vite do destino do proxy. Não habilito CORS nem wildcard.
8. **CA8 — Conteúdo JSON.** Conforme o critério original de 2.1 no Epic 2,
   recuso conteúdo não JSON nas operações de escrita no formato único, sem
   executar o handler. P7 define status/código, media types aceitos, corpo
   vazio e JSON malformado, sem inventar regras para endpoints de negócio.
   GET/HEAD/OPTIONS não exigem corpo ou Content-Type JSON.
9. **CA9 — Métodos seguros.** GET, HEAD e OPTIONS nunca recebem bloqueio CSRF
   por origem ausente/estrangeira ou por conteúdo. Preservo os resultados do
   roteador (inclusive 404/405), sem transformar todos em 200 ou adicionar
   suporte CORS. HEAD permanece sem corpo. Nenhuma leitura passa a gravar no
   banco, autenticar, liquidar lotes ou iniciar mutação de negócio.
10. **CA10 — Regressão da aplicação.** Com e sem SPA montada, mantenho
    `GET /health` → 200 e exatamente `{"status":"ok"}`, sem banco; Swagger
    HTML e schema JSON funcionais; raiz, rotas de cliente e assets funcionais
    quando há build. `/api` desconhecida e escritas nunca retornam a SPA.
    O fallback continua por último. Não transformo respostas de sucesso HTML,
    arquivos, OpenAPI ou health em envelopes de erro.
11. **CA11 — Infraestrutura temporária.** Preservo o contrato e atributos do
    cookie técnico da 1.4 até sua remoção/substituição na 2.2; sua emissão em
    GET é apenas a verificação temporária herdada, sem mutação no servidor,
    e não precedente para implementar login/logout por GET. Preservo o
    WebSocket técnico até 4.1, sem aplicar envelope HTTP às mensagens nem
    alterar sua política de handshake. A 2.2 o classificará como público.
12. **CA12 — Verificação.** Testes cobrem CA1–CA11 e a matriz abaixo; executo
    `./verify.sh` e registro a saída real (seção "Registro e status").

## Escopo dos status e do contrato

| Status | Tratamento previsto nesta story |
| --- | --- |
| 400 | Representação de requisição inválida/exceção HTTP; não forçar toda validação FastAPI para 400. Teste sintético se não há produtor real. |
| 401 | Suportado pelo mecanismo genérico e teste de contrato; produtor real de autenticação só na 2.2. Preservar cabeçalhos pertinentes se fornecidos. |
| 403 | Produtor real: recusa de Origin/Referer. Não significa autorização por papel nesta story. |
| 404 | Padronizar os erros reais da API, inclusive os gerados pelo fallback que reserva `/api`. |
| 409 | Suportar conflito por exceção HTTP/teste sintético; não criar conflito de domínio nem mapear genericamente qualquer erro do banco para 409. |
| 422 | Adaptar validação de entrada do FastAPI ao envelope, preservando utilidade e sanitização. |
| 500 | Tratar falhas inesperadas da API com mensagem genérica e log do servidor. |
| 405 e recusa de conteúdo | Preservar status/cabeçalhos do roteamento; media type recusado é 415 (P7). Não criar classes por status. |

Os nomes dos códigos e campos estão fechados em P1/P2. Rotas sintéticas existem
apenas nas fixtures, nunca na aplicação publicada ou no OpenAPI real.

## Rotas excluídas ou especiais

| Rota/área | Limite para a implementação |
| --- | --- |
| `/health` | GET público sem banco, sem exigir Origin/Referer. HEAD atualmente retorna 405 com Allow: GET; preservar. |
| `/api/docs`, `/api/openapi.json` | Leituras sem bloqueio CSRF; manter Swagger e schema. Futuras escritas via “Try it out” obedecem à política normal. |
| SPA e assets | Sucessos HTML/arquivo preservados; métodos seguros livres de CSRF; nenhum fallback de escrita. |
| `/api/infra-check/cookie` | GET técnico preservado até 2.2; não liberar POST/PUT/PATCH/DELETE por prefixo `infra-check`. |
| `/api/infra-check/ws` | Escopo WebSocket excluído da nova proteção HTTP; conservar testes e comportamento atual. GET HTTP nesse caminho continua erro JSON. |
| Futuro login | Não existe ainda. A proteção deve alcançar sua futura escrita pública sem depender de JWT/cookie. |

P5/P8 definem a ordem entre roteamento, proteção e handlers, inclusive a
precedência de 403/recusa de conteúdo versus 404/405 em escritas inválidas.
Com origem/conteúdo válidos, métodos não suportados mantêm 404/405. Não uso uma
exceção ampla de prefixo para manter Swagger ou infraestrutura funcionando.

## Tarefas e subtarefas

- [x] **T1 — Planejar comigo (CA1–CA12).** Resolver P1–P8 com opções,
  consequências e recomendação; registrar decisões nesta story antes de código.
- [x] **T2 — Contrato de erros (CA1–CA4).** Criar representação/helper mínimo;
  integrar erros HTTP, validação de entrada e falhas inesperadas; preservar
  headers; sanitizar detalhes e logs; manter produtores futuros fora do escopo.
- [x] **T3 — Configuração e proteção (CA5–CA9).** Configurar origem esperada;
  validar parsing/normalização; aplicar Origin prioritário e fallback Referer;
  implementar a política aprovada de ausência e conteúdo; não afetar WebSocket.
- [x] **T4 — Integrar com app/SPA (CA10–CA11).** Respeitar factory, ordem das
  rotas e independência do banco; manter rotas técnicas e documentação; revisar
  a fronteira entre erros do roteador e da proteção.
- [x] **T5 — Testar (CA1–CA12).** Criar testes unitários/HTTP com fixtures
  sintéticas, executar matriz de regressão e validar o caminho pelo proxy Vite
  e a configuração equivalente ao Render, sem publicar endpoints de teste.
- [x] **T6 — Verificar e documentar (CA12).** Executar `./verify.sh` completo
  na implementação, incluindo a integração PostgreSQL já existente; documentar
  configuração e limitações no README, decisões/evidências na story e uso de
  IA no registro existente. Parar na 2.1.

### Review Findings

Code review de 24/10/2026 (bmad-code-review, 4 camadas: Blind Hunter, Edge Case
Hunter, Verification Gap, Acceptance Auditor). Sem git: o conteúdo revisado foi o
estado atual dos arquivos. Severidades na escala BLOCKER/HIGH/MEDIUM/LOW.

- [x] [Review][Decision] MEDIUM — Escrita válida em `/api` inexistente com a SPA montada responde 405 `Allow: GET, HEAD`, não 404 — **Resolvido: escolhi (a).** Aceito o 405, mantenho o fallback da 1.3, fixei nos testes status/`code`/`Allow` reais e anotei que a evidência anterior de 404 pelo proxy foi em dev, sem SPA. Em produção (SPA sempre montada), o fallback `/{full_path:path}` (só GET/HEAD) casa parcialmente com `POST /api/nao-existe`: 405 `method_not_allowed`, `Allow: GET, HEAD`, embora o GET do mesmo caminho dê 404 (reproduzido com `create_app(dist)`). `test_valid_write_on_unknown_api_path_keeps_the_router_404` só roda sem SPA; `test_spa.py::test_post_on_unknown_api_path_is_json_error` aceita `(404, 405)`; a evidência pelo proxy é sem SPA. Opções: (a) aceitar o 405 e fixar status/`code`/`Allow` exatos com SPA, renomear o teste e anotar a evidência como "dev, sem SPA" (recomendado); (b) mudar o fallback da SPA (conflito com a decisão da 1.3 "outros métodos caem no 405 JSON do roteador").
- [x] [Review][Decision] MEDIUM — Arquivo modificado fora da lista da story — **Resolvido:** conferi o diff; a mudança é de infraestrutura, não pertence à 2.1, fica intocada e fora do commit desta story.
- [x] [Review][Patch] MEDIUM — A proteção decide por `scope["path"]` cru; com `root_path` configurado, escrita estrangeira em `/<prefixo>/api/...` executa o handler sem checagem (reproduzido com `TestClient(root_path="/prefix")`). Hoje não há `root_path` (latente). Correção: usar o mesmo caminho do roteador (sem `root_path`) e testar com `root_path` [backend/app/csrf.py:116]
- [x] [Review][Patch] MEDIUM — README: a tabela "Configuração usada" do Render apresenta `APP_ORIGIN` como usada, mas ela ainda não foi configurada no painel; "Como validar" não tem checagens pós-deploy da proteção (403 estrangeiro, 403 sem origem, 415) [README.md:118]
- [x] [Review][Patch] LOW — README não diz que escrita da mesma origem sem JSON recebe 415 antes do 404/405 (só cita o 403) [README.md:231]
- [x] [Review][Patch] LOW — Frases da fase de criação contradizem a story implementada: CA12 "Nesta criação não implemento…", "Os nomes dos códigos e campos permanecem propostas de P1/P2", T6 "Não alterar essas fontes nesta criação", Fora de escopo "não altero código" [2-1-formato-de-erros-e-validacao-de-origin.md:145]
- [x] [Review][Patch] LOW — CA4/matriz pede "log é capturado"; o teste só prova o relançamento. Verificado no review com uvicorn real: um único `Exception in ASGI application` com o traceback, resposta 500 genérica. Registrar essa evidência (ou um teste em subprocesso) [backend/tests/test_errors.py:187]
- [x] [Review][Patch] LOW — "Local real" incompleto: a prova pelo Vite usou só rota inexistente; nenhuma escrita aceita chegou a um handler pelo proxy. Registrar como parcial ou executar com rota de harness [2-1-formato-de-erros-e-validacao-de-origin.md:313]
- [x] [Review][Patch] LOW — Testes estruturais de rotas de escrita olham só `APIRoute` (Route/Mount escapariam); `test_real_app_has_no_write_route_outside_api` recebe `monkeypatch` sem usar e não neutraliza `SPA_DIST_DIR` [backend/tests/test_csrf.py:459]
- [x] [Review][Patch] LOW — `test_write_outside_api_is_not_guarded_and_gets_the_router_405` aceita `(404, 405)`; sem SPA é sempre 404 [backend/tests/test_csrf.py:414]
- [x] [Review][Patch] LOW — Teste de métodos seguros não confere `Allow` nem o corpo do contrato nos 405 de OPTIONS/HEAD [backend/tests/test_csrf.py:436]
- [x] [Review][Patch] LOW — `test_invalid_app_origin_is_rejected_without_echoing_it` só confere `"pw@"`; os outros 11 valores não são verificados quanto a eco [backend/tests/test_config.py:105]
- [x] [Review][Patch] LOW — `assert_contract` compara `message` com o próprio `MESSAGES`; nenhum teste fixa um texto literal em português (CA1) [backend/tests/test_errors.py:45]
- [x] [Review][Defer] Log do 500 pode conter parâmetros SQL; `hide_parameters=True` não avaliado [backend/app/db.py] — deferred: pré-existente (1.2), relevante a partir da 2.2 (usuários)
- [x] [Review][Defer] `loc` do 422 pode ecoar chaves enviadas pelo cliente (modelos `dict`/`extra="forbid"`) e `details` não tem limite [backend/app/errors.py:89] — deferred: inalcançável com as rotas atuais; mudar o `loc` seria conflito com D1
- [x] [Review][Defer] `sprint-status.yaml` mantém `epic-1: in-progress` e 1.4 `review` — deferred: pré-existente; a story optou por não alterar registros históricos

**Rejeitados:**
- Métodos fora de POST/PUT/PATCH/DELETE não são protegidos — LOW improvável; o conjunto é a P8/CA5 e o roteador recusa verbos sem rota.
- `HTTPException` 3xx vira `internal_error` — ninguém levanta 3xx como exceção (redirects são `RedirectResponse`); fallback é a D3.
- 413/429/503 com mensagens genéricas — comportamento definido pela D3.
- `APP_ORIGIN` IDN/ponto final/IPv6 não canônico — falha fechada (toda escrita 403), visível na hora.
- `Origin`/`APP_ORIGIN` com TAB, porta vazia ou porta 0 aceitos — só normaliza para a própria origem permitida; não é bypass; com porta 0 falha fechada.
- `app/config.py` importa de `app/csrf.py` (camadas) — dano improvável; correção é refatoração.

## Matriz de testes esperados

| Grupo | Casos e evidência necessária |
| --- | --- |
| Erro previsto | 400/401/403/404/409 por fixture ou produtor real; mesmo envelope, status coerente, código estável e mensagem em português. |
| Validação | 422 real de validação FastAPI; localização útil do campo, sem valores sensíveis; JSON malformado conforme P6/P7. |
| Erro inesperado | Exceção forçada em fixture; cliente recebe 500 genérico e log é capturado. Configurar cliente para observar a resposta 500, não apenas relançar exceção. |
| Métodos de escrita | Parametrizar POST/PUT/PATCH/DELETE: origem válida executa handler; estrangeira recusa e contador/spy prova que handler não executou. |
| Origin | Mesma origem; outro host, esquema ou porta; domínio parecido; portas padrão; null, formato inválido e headers ambíguos conforme P3. |
| Referer | Sem Origin: mesma origem com path/query aceita, estrangeiro/malformado recusa; Origin inválido/estrangeiro com Referer válido continua recusado. |
| Ausência | Ambos ausentes seguem P4 em cada método de escrita; sem cookie também protege; sem bypass por User-Agent ou suposto cliente CLI. |
| Conteúdo | JSON válido, não JSON (form/text), media type ausente, corpo vazio e JSON malformado conforme P7; recusa não executa ação. |
| Métodos seguros | GET/HEAD/OPTIONS com headers ausentes, estrangeiros ou inválidos não geram recusa CSRF; preservar status/Allow e ausência de corpo HEAD. |
| Proxy/config | HTTPS externo com HTTP interno; headers Host/Forwarded/X-Forwarded-* forjados não autorizam estrangeiro; configuração ausente/inválida segue P3. |
| SPA | Factory com/sem dist; API desconhecida JSON 404; raiz/rota cliente/asset válidos; asset ausente; escrita nunca HTML; fallback final e caminhos normalizados. |
| Rotas existentes | Health sem banco; docs/schema; cookie e atributos; WebSocket e política atual intactos; nenhum header CORS introduzido. |
| Local real | Exercitar requisição pela origem do Vite até backend usando rota só de fixture/harness; não confundir teste direto do backend com prova do proxy. |

Não preciso criar tabelas nem testes transacionais novos para esta camada HTTP.
Os testes PostgreSQL existentes continuam no verify. Asserções antigas sobre
`detail` em `test_spa.py` e `test_infra_check.py` podem mudar apenas para refletir
o contrato aprovado; preservo as garantias de status, headers e não retorno de
HTML. Não enfraqueço testes para acomodar regressão.

## Decisões herdadas

- **AD-19:** mantenho GET/HEAD/OPTIONS sem mutação de estado; descartei tratar
  leitura como gatilho de alteração de negócio.
- **AD-29:** mantenho origem configurada, fallback Referer quando suportado,
  JSON e ausência de CORS permissivo. JWT em cookie e seus atributos já são
  arquitetura futura, não implementação desta story. A AD não registrou uma
  alternativa descartada; não invento uma decisão histórica.
- **AD-30:** mantenho identificadores/códigos em inglês, mensagens em português
  e APIs sob `/api`; descartei misturar idiomas nos identificadores técnicos.
- **AD-14/AD-28 e 1.3 D2–D5:** mantenho um serviço Render e mesma origem,
  proxy Vite local, fallback final e OpenAPI sob `/api`; descartei CORS de dev
  e servir `index.html` para API ou métodos de escrita.
- **1.4 P8–P11:** mantenho a fronteira de confiança do proxy sem wildcard
  preventivo, o cookie até 2.2 e o WebSocket até 4.1. A comparação apenas de
  host na verificação WebSocket não substitui AD-29 para novas escritas HTTP.
- **AD-27:** mantenho verify e banco de testes isolado; não substituo a
  integração existente por SQLite.

## Decisões (fechadas no Plan Mode antes da implementação)

Decidi P1 a P8 e D1 a D6 no Plan Mode, antes de qualquer código. O plano com as
alternativas está em `~/.claude/plans/` (fora do repositório); resumo do que
vale, com a alternativa que descartei:

| ID | Decisão | Descartei |
| --- | --- | --- |
| P1 | Objeto plano `{status, code, message}`; `details` omitido quando não há. | Envelope `error` aninhado e `details: null`. |
| P2 | Catálogo pequeno por status (`bad_request`, `unauthorized`, `forbidden`, `not_found`, `method_not_allowed`, `conflict`, `unsupported_media_type`, `validation_error`, `internal_error`) e dois específicos da proteção (`csrf_origin_missing`, `csrf_origin_mismatch`). | Subclasses de exceção por erro. |
| P3 | Uma origem explícita em `APP_ORIGIN`, normalizada e validada; nada de `Host`/`Forwarded`/`X-Forwarded-*`. | `RENDER_EXTERNAL_URL`, lista de origens, derivar do proxy, `*`. |
| P4 | Sem `Origin` e sem `Referer`: 403. `Origin` presente (vazio, `null`, inválido) nunca cai no `Referer`. | Liberar clientes sem cabeçalho (CLI). |
| P5 | Origem configurada por execução; no dev é `http://localhost:5173`. | Várias origens locais; tratar `localhost` e `127.0.0.1` como iguais. |
| P6 | Três handlers separados (`HTTPException` do Starlette, `RequestValidationError`, `Exception`); sem override de `app.openapi()`. | Um handler único; limitar por rota. |
| P7 | Verificação própria de `Content-Type` na camada comum: só `application/json` (com `charset`), exatamente um cabeçalho; senão 415. JSON malformado vira 422 na validação do FastAPI. | Confiar só em `strict_content_type`; aceitar `+json`. |
| P8 | Middleware ASGI puro (`ApiWriteGuardMiddleware`), só HTTP, só escritas sob `/api`, sem ler o corpo. | `BaseHTTPMiddleware`; dependência global (leria o corpo antes). |
| D1 | `details` do 422 = `[{"loc": [...], "type": "..."}]`, sem `msg` (inglês), `input`, `ctx`, `url`. | Incluir `msg` do Pydantic. |
| D2 | `APP_ORIGIN` ausente ou inválida derruba a criação da aplicação; `verify.sh` e `conftest` fornecem/validam. | Subir e recusar toda escrita. |
| D3 | A mensagem vem sempre do catálogo; `HTTPException.detail` nunca é exposto. Status fora do catálogo: 4xx `bad_request`, 5xx `internal_error`. | Repassar `detail`. |
| D4 | Vite com `port: 5173` e `strictPort: true`. | Manter o padrão implícito. |
| D5 | O log do 500 é o relançamento do `ServerErrorMiddleware` (o uvicorn registra uma vez). | Logar também no handler (duplicaria). |
| D6 | Eu mesmo editei `backend/.env.example` (`APP_ORIGIN=http://localhost:5173`). | Autorizar a IA a editar `.env*`. |

Consequências que aceitei: escrita estrangeira em rota `/api` inexistente recebe
403 antes do 404/405; toda escrita exige `Content-Type: application/json`, mesmo
sem corpo; o schema `HTTPValidationError` do OpenAPI diverge do envelope real
quando a primeira rota com parâmetros existir (sem override).

## Arquivos criados e alterados

**Criados:** `backend/app/errors.py`, `backend/app/csrf.py`,
`backend/tests/synthetic_api.py` (rotas só de teste), `backend/tests/test_errors.py`,
`backend/tests/test_csrf.py`.

**Alterados:** `backend/app/main.py`, `backend/app/config.py`,
`backend/tests/conftest.py`, `backend/tests/test_config.py`,
`backend/tests/test_spa.py`, `backend/tests/test_infra_check.py`,
`backend/tests/test_openapi.py`, `verify.sh`, `frontend/vite.config.ts`,
`README.md`, `docs/uso_de_ia.md`, esta story e o `sprint-status.yaml`.
`backend/.env.example` foi editado por mim (D6). Sem mudança: `app/spa.py`,
`app/infra_check.py`, `Dockerfile`, `start.sh`, migrations, `test_health.py`.
Nenhuma dependência nova. O code review criou
`_bmad-output/implementation-artifacts/deferred-work.md` (itens adiados).

## Fora de escopo

Usuários, senhas, Argon2, JWT, login, logout, roles, política de acesso,
banco de usuários, seed, lotes, museu, carteira, lances, WebSocket real da sala,
CORS, frontend novo, cadastro público, alteração do deploy, refatoração geral
ou framework de erros. Não removo o cookie técnico agora e não altero a política
do WebSocket técnico. Não crio a Story 2.2 e não uso git.

## Registro e status

Status: **done**. Implementei só a 2.1; a 2.2 não foi iniciada.

### Evidências (saídas reais)

**Implementação (antes do code review).** `./verify.sh` completo, exit code 0:
`pytest` **399 passed, 1 warning in 1.31s**. Casos por arquivo naquela execução:
`test_errors.py` 21, `test_csrf.py` 201, `test_config.py` 31, `test_spa.py` 73,
`test_infra_check.py` 56, `test_openapi.py` 6, `test_health.py` 1.

Verificação manual pelo proxy real naquela fase: uvicorn com
`APP_ORIGIN=http://localhost:5173` e `npm run dev`, requisições com `curl` a
`http://localhost:5173`, rota inexistente. **Foi em desenvolvimento, sem a SPA
montada**: o 404 abaixo vale só nesse ambiente. Com a SPA montada (imagem/produção),
a mesma escrita válida recebe 405 (ver "Correções do code review").

| Requisição | Resultado |
| --- | --- |
| `POST /api/nao-existe`, `Origin: http://localhost:5173`, JSON | 404 `not_found` (dev, sem SPA; prova que o proxy não troca o `Origin`) |
| mesmo, `Origin: https://evil.example` | 403 `csrf_origin_mismatch` |
| mesmo, sem `Origin` | 403 `csrf_origin_missing` |
| mesmo, `Content-Type: text/plain` | 415 `unsupported_media_type` |
| `GET /api/nao-existe` | 404 `not_found` |
| `GET /health`, `GET /api/docs` | 200 |

**Correções do code review (24/10/2026).** Corrigi os achados 3 a 13 da seção
"Review Findings", com as decisões 1(a) e 2 (acima). Nenhuma mudança em P1–P8 ou
D1–D6, no fallback da SPA ou em código fora da lista desta story.

- **`root_path`:** a proteção passou a decidir pelo mesmo caminho do roteador
  (função local `effective_path`, só com o `scope` ASGI, sem o `root_path`; ver
  "Ajuste final antes do commit"), em `backend/app/csrf.py`. Escrevi 9 testes com `TestClient(root_path="/prefix")`.
  Rodados contra a lógica antiga (`scope["path"]` cru, simulada só naquela
  execução por um plugin fora do repositório), 8 falharam e 1 passou: o caso
  válido, que passa nos dois. Com a correção, os 9 passam.
- **405 com a SPA:** `test_spa.py` fixa 405 `method_not_allowed` e `Allow` com
  exatamente `GET` e `HEAD` para POST/PUT/PATCH/DELETE em `/api/nao-existe` e em
  `/lots/x`. Comparo o `Allow` como conjunto, porque o Starlette o monta a partir
  de um `set` e a ordem não é garantida. Em `test_csrf.py`, o teste sem SPA passou
  a se chamar `..._without_spa_is_the_router_404` e confere o corpo inteiro.
- **Testes fortalecidos:**
  - estruturais: verificam rota de qualquer tipo e `Mount`, com um teste que
    prova que eles pegam um `Route` comum e um `Mount`; a versão com a app real
    monta a SPA;
  - escrita fora de `/api`: 404 exato;
  - métodos seguros: `Allow` e corpo do contrato nos 405;
  - `APP_ORIGIN`: nenhum valor inválido é ecoado;
  - catálogo de mensagens: fixado em texto literal em português.

  Nenhuma asserção foi afrouxada.

Verificação real pelo proxy do Vite com rota de harness. O harness ficou fora do
repositório, com `create_app(app_origin="http://localhost:5173")`, sem SPA, mais
`POST /api/test/write` (contador) e `GET /api/test/boom`. Rodou sob uvicorn em
`127.0.0.1:8000` e `npm run dev`, com uma requisição `curl` por caso a
`http://localhost:5173`:

| Requisição | Resultado |
| --- | --- |
| `POST /api/test/write`, `Origin: http://localhost:5173`, JSON | 200 `{"handler_calls":1}` |
| mesmo, `Origin: https://evil.example` | 403 `csrf_origin_mismatch` |
| mesmo, sem `Origin` e sem `Referer` | 403 `csrf_origin_missing` |
| mesmo, só `Referer: http://localhost:5173/lots/1?x=1` | 200 `{"handler_calls":2}` (as recusas não executaram o handler) |
| mesmo, `Origin` válido, `Content-Type: text/plain` | 415 `unsupported_media_type` |
| `GET /api/test/boom` | 500 `{"status":500,"code":"internal_error","message":"Erro interno. Tente novamente mais tarde."}` |
| `GET /health` | 200 `{"status":"ok"}` |

**Log real do 500 (CA4, D5).** Na mesma execução, o log do uvicorn registrou a
linha de acesso `"GET /api/test/boom HTTP/1.1" 500`, um único
`ERROR: Exception in ASGI application` e o traceback, terminando em
`RuntimeError: SEGREDO-NA-EXCECAO`. O texto da exceção ficou só no log; a resposta
foi a genérica acima. Nenhuma linha do log contém `cookie` ou `authorization`.

`./verify.sh` completo depois das correções, exit code 0:
- Ruff check: "All checks passed!".
- `ruff format --check`: "24 files already formatted".
- `pytest`: **413 passed, 1 warning in 1.28s**, incluindo `tests/integration`
  em PostgreSQL.
- ESLint, `tsc --noEmit`, build do Vite e `docker build`.
- Linha final: `verify.sh: todas as etapas passaram.`.

O único warning é o `StarletteDeprecationWarning` do `httpx`, que já existia.

Casos por arquivo: `test_csrf.py` 211, `test_errors.py` 22, `test_spa.py` 76,
`test_config.py` 31, `test_infra_check.py` 56, `test_openapi.py` 6,
`test_health.py` 1, `test_db_guard.py` 6, `integration/test_database.py` 4. Os 14
casos a mais vêm só de testes novos: +9 de `root_path`, +1 da checagem estrutural,
+1 do catálogo literal e +3 da parametrização do 405 com SPA. Nenhum foi removido.

Não executei a prova no navegador (`fetch` no console) nem `docker run` da
imagem; o `verify.sh` só constrói a imagem.

### Limitações e riscos que permanecem

- **O Render quebra no próximo deploy se `APP_ORIGIN` não estiver no painel**
  (D2). Auto-Deploy está desligado; a configuração no painel é ação minha e não
  fiz deploy nem mexi no Render.
- Quem rodar `pytest` ou `uvicorn` fora do `verify.sh` precisa de `APP_ORIGIN`
  no ambiente ou em `backend/.env`.
- Abrir o front em `127.0.0.1:5173` ou o Swagger direto na porta 8000 dá 403 nas
  escritas (aceito em P5; documentado no README).
- O schema 422 do OpenAPI diverge do envelope real a partir da primeira rota com
  parâmetros (P6, sem override).
- O traceback de um 500 fica no log do servidor e pode conter texto de exceção do
  SQLAlchemy.
- A origem `APP_ORIGIN` não aceita barra final nem caminho; o erro de configuração
  descreve o formato esperado.
- Com a SPA montada, escrita válida em rota `/api` inexistente recebe 405 com
  `Allow` `GET, HEAD`, não 404 (decisão 1(a) do review; fallback da 1.3 mantido).

### Ajuste final antes do commit

Troquei o import de `get_route_path` (de `starlette._utils`, módulo privado) por
`effective_path` em `backend/app/csrf.py`, que deriva o caminho só do `scope`
ASGI: usa `scope["route_path"]` se existir; senão `scope["path"]` sem o
`root_path`, e só quando ele é prefixo por segmento (igual ao caminho, ou seguido
de `/`); `/pre` não é prefixo de `/prefix/api`. Sem `root_path`, o caminho não
muda. Nenhuma biblioteca nova e nenhum código copiado do Starlette. Com isso, a
limitação sobre `starlette._utils` deixou de existir.

Acrescentei 9 testes unitários de `effective_path` (`test_csrf.py`); os testes
HTTP de `root_path` existentes seguem iguais. Direcionados (`-k "root_path or
effective_path"`): 18 passed. `./verify.sh` completo, exit 0: Ruff check e
`format --check` ("24 files already formatted") passaram, `pytest` **422 passed,
1 warning in 1.30s** (`test_csrf.py` 220, `test_errors.py` 22, `test_spa.py` 76,
`test_config.py` 31, `test_infra_check.py` 56, `test_openapi.py` 6), ESLint,
`tsc --noEmit`, build do Vite e `docker build` passaram, com a linha final
`verify.sh: todas as etapas passaram.`. Os 9 casos a mais em relação aos 413
anteriores vêm só dos testes novos. Status mantido em `review`.
