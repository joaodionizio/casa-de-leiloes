---
id: SPEC-story-2-2-login-papeis-politica-de-acesso
companions:
  - backend-contract.md
  - frontend-login.md
  - test-plan.md
  - implementation-map.md
  - ../../planning-artifacts/DESIGN.md
  - ../../planning-artifacts/EXPERIENCE.md
  - ../../../docs/FRONTEND-WORKFLOW.md
  - ../../../docs/ARQUITETURA.md
sources:
  - ../../implementation-artifacts/2-2-login-papéis-e-política-de-acesso.md
---

> **Contrato canônico.** Esta SPEC e os arquivos em `companions:` são o contrato
> completo da Story 2.2. A story em `sources:` fica só para rastreio. P1 a P16,
> OQ-1 a OQ-3, as suposições e a estratégia do meta-teste foram aprovadas pelo
> Joaodionizio em 24/10/2026. Nenhuma decisão aberta.

# Story 2.2: login, papéis e política de acesso

## Why

Mandato do desafio (FR1, FR19, AR8): as contas semeadas (1 `AUCTIONEER`, 2
`BIDDER`) precisam entrar e sair, e o papel tem de ser imposto pelo servidor antes
das stories que criam lote (2.4), depósito (3.1) e lance (3.4). Sem uma política
declarada em toda rota e testada, uma rota futura pode nascer aberta por
esquecimento. É também a primeira tela com ação do usuário: define como o front
fala com a API autenticada e substitui o cookie técnico da 1.4 pelo real.

## Capabilities

- **CAP-1**
  - **intent:** O sistema garante as três contas de demonstração com IDs fixos, sem nunca recriar nem alterar contas existentes.
  - **success:** Em banco vazio o seed cria exatamente 1 `AUCTIONEER` e 2 `BIDDER` com hash `$argon2id$`; uma segunda execução deixa todas as colunas idênticas; o seed roda isolado (`python -m app.seed`) e no `start.sh` entre migrations e uvicorn; não existe rota de cadastro.
- **CAP-2**
  - **intent:** Um usuário semeado entra com e-mail e senha e recebe uma sessão de 8 h num cookie HttpOnly da mesma origem.
  - **success:** `POST /api/auth/login` válido → 200 com `{email, role}` e um `Set-Cookie` com nome e atributos do modo da `APP_ORIGIN` (backend-contract §6), `Max-Age=28800`, `Cache-Control: no-store`; o JWT decodificado tem só `sub`, `role`, `iat`, `exp` e nunca aparece no corpo.
- **CAP-3**
  - **intent:** Credenciais inválidas são recusadas sem revelar se o e-mail existe.
  - **success:** E-mail inexistente e senha errada dão 401 `invalid_credentials` com corpo byte a byte igual, sem `Set-Cookie` e sem ecoar o e-mail; o caminho de e-mail inexistente executa uma verificação Argon2 contra hash de referência.
- **CAP-4**
  - **intent:** Um usuário logado consulta quem é e qual o seu papel.
  - **success:** `GET /api/me` com sessão válida → 200 `{email, role}` com `no-store`; sem cookie, token malformado, adulterado, expirado, com outro algoritmo, usuário inexistente ou papel do token diferente do banco → 401 `unauthorized`.
- **CAP-5**
  - **intent:** Um usuário sai e o navegador descarta o cookie de sessão.
  - **success:** `POST /api/auth/logout` → 204 com `Set-Cookie` de expiração imediata, mesmo nome, `Path`, `Secure`, `HttpOnly` e `SameSite`, com ou sem sessão válida; depois dele `/api/me` → 401.
- **CAP-6**
  - **intent:** Toda rota da aplicação declara exatamente uma política de acesso e uma rota sem política reprova o `verify`.
  - **success:** Toda rota é registrada por um helper nosso que grava a política no endpoint e aplica a dependência correspondente; o teste percorre `app.routes` recursivamente (inclusive `Mount` e WebSocket) da app real, com e sem SPA, e confere a política esperada de cada rota, inclusive o WebSocket técnico como `PUBLIC`; o meta-teste prova que uma rota sem política, uma rota incluída por `include_router` e uma rota dentro de `Mount` sem política reprovam; só `/api/docs` e `/api/openapi.json` ficam na allowlist; nenhuma função interna ou não documentada de FastAPI/Starlette é importada.
- **CAP-7**
  - **intent:** Rotas por papel recusam o outro papel e rotas autenticadas recusam visitantes.
  - **success:** Em rotas sintéticas só de teste, sobre PostgreSQL real: `AUCTIONEER` passa na rota de `AUCTIONEER` e recebe 403 `forbidden` na de `BIDDER`, e o inverso; sem sessão ou com sessão inválida → 401 `unauthorized`; na rota `OPTIONAL`, sessão válida expõe o usuário e cookie ausente, inválido, expirado, de usuário inexistente ou com papel incoerente vira visitante anônimo, sem 401; tudo no formato único da 2.1.
- **CAP-8**
  - **intent:** Login e logout continuam sob a proteção de escrita da 2.1, sem exceção.
  - **success:** Origem estrangeira ou ausente → 403 `csrf_*`; sem `application/json` → 415; em nenhum caso o handler roda nem sai cookie; GET/HEAD/OPTIONS nunca criam nem removem sessão; nenhum cabeçalho CORS.
- **CAP-9**
  - **intent:** O cookie técnico da 1.4 deixa de existir; o WebSocket técnico continua igual, como rota pública.
  - **success:** `GET /api/infra-check/cookie` → 404 JSON do contrato; constantes, testes e seção do README do cookie removidos; os testes do WebSocket passam inalterados.
- **CAP-10**
  - **intent:** Pela interface, o usuário entra, vê quem é e o seu papel em português e sai, sem o JavaScript tocar no token.
  - **success:** O roteiro manual (test-plan §5) passa no navegador: credenciais inválidas e servidor indisponível mostram mensagens em português; logado mostra e-mail e "Leiloeiro"/"Licitante" e "Sair"; recarregar mantém a sessão via `/api/me`; `document.cookie` não contém a sessão; `localStorage` e `sessionStorage` ficam vazios; a tela respeita frontend-login.md.
- **CAP-11**
  - **intent:** A tabela `users` nasce por migration reversível e a aplicação continua subindo sem banco.
  - **success:** `0002` cria `users` com as CHECKs e a UNIQUE e o `downgrade` a remove; os testes recebem o esquema das migrations; `GET /health` → 200 e `create_app()` funciona sem conexão; o engine usa `hide_parameters=True`, de modo que o SQLAlchemy não renderiza os valores dos parâmetros na mensagem do erro (o `DETAIL` escrito pelo próprio PostgreSQL pode conter valores; sem sanitização nesta story).
- **CAP-12**
  - **intent:** O segredo do JWT vem só do ambiente e a aplicação recusa subir sem ele.
  - **success:** `JWT_SECRET` ausente ou com menos de 32 caracteres derruba `create_app()` sem ecoar o valor; `APP_ORIGIN` em `http://` com host diferente de `localhost`, `127.0.0.1` ou `::1` também derruba `create_app()` com erro claro, sem ecoar a origem; nenhum valor real aparece em código, testes, README, story, spec ou `docs/uso_de_ia.md`.
- **CAP-13**
  - **intent:** O Swagger documenta o envelope de erro real das rotas novas.
  - **success:** No `/api/openapi.json`, o 401 e o 422 do login e o 401 do `/api/me` referenciam `ErrorResponse`; `HTTPValidationError` não existe em `components.schemas`; sem override de `app.openapi()`.
- **CAP-14**
  - **intent:** A entrega fica verificada e documentada para o avaliador.
  - **success:** `./verify.sh` completo passa, com a saída real registrada; README (contas demo, seed, `JWT_SECRET` no Render, limitação do logout, cookie real), `docs/uso_de_ia.md`, story e `sprint-status.yaml` atualizados.

## Constraints

- AD-11/AD-29: JWT só em cookie HttpOnly; nunca no corpo, na URL, em `localStorage`/`sessionStorage` nem no cabeçalho `Authorization` (nem aceito, nem emitido).
- AD-30: identificadores em inglês (`users`, `UserRole.AUCTIONEER`); "Leiloeiro"/"Licitante" e todas as mensagens só na interface, em português.
- AD-19: GET/HEAD/OPTIONS nunca alteram estado nem emitem ou apagam cookie de sessão; login e logout são POST.
- AD-2/AD-25: dependências de sessão e de autenticação são `def` síncronas (threadpool), nunca no event loop; `Session` curta por requisição.
- CA11 da story: criar ou importar a aplicação não abre conexão; o engine é criado sob demanda.
- `app.seed` não importa `app.main` (que exige `APP_ORIGIN` e `JWT_SECRET`); o seed precisa só de `DATABASE_URL`.
- Contrato de erro da 2.1 intacto: mensagem sempre do catálogo, `detail` nunca exposto; o guard da 2.1 não muda. `invalid_credentials` sai por `error_response` na própria rota; sem `ApiError` nem hierarquia de exceções.
- Sem `APP_ENV`: o modo do cookie vem só da `APP_ORIGIN`.
- Política de acesso é metadata nossa: na app real, rotas só entram pelos helpers de `app/access.py`; `include_router`, `@app.get` direto e `APIRouter` ficam fora da app real (o meta-teste os reprova). Nenhum import de função interna ou não documentada de FastAPI/Starlette (`iter_route_contexts`, `_IncludedRouter`, `starlette._utils` etc.).
- `OPTIONAL` nunca concede informação protegida sem sessão válida; `AUTHENTICATED`, `AUCTIONEER` e `BIDDER` respondem 401 a sessão ausente ou inválida.
- AD-17: login, seed, papéis e migration testados em PostgreSQL real, nunca SQLite; o banco de dev nunca é tocado pelos testes.
- O agente nunca lê nem edita `.env*` (inclui `backend/.env.example`); o usuário acrescenta a linha de `JWT_SECRET`.
- Front: AD-4 (TypeScript simples), DESIGN.md, EXPERIENCE.md e FRONTEND-WORKFLOW.md vinculantes no escopo; nenhuma dependência nova no front.
- Nunca afrouxar teste existente; testes que mudam (cookie técnico, OpenAPI, tabelas) mudam pelo escopo, não para passar.

## Non-goals

- Carteira (3.1), lotes e lote demo (2.4), busca no museu (2.3), vitrine e roteador (2.5), lances (3.x), sala/WebSocket real e Q2 (4.1).
- Cadastro, troca/recuperação de senha, refresh token, revogação no servidor, sessão no banco, "lembrar de mim".
- Limite de tentativas/bloqueio por força bruta (só registrado como limitação no README).
- `check_needs_rehash` e ajuste de parâmetros do Argon2.
- Biblioteca de testes do front, React Router, identidade visual completa (6.2), dark mode (6.7).
- Rota real restrita a papel; endpoint de debug; credenciais demo exibidas na tela.
- Remover o WebSocket técnico; mudar `Dockerfile`, `compose.yaml`, `csrf.py`, `spa.py` (exceto registrar a rota pelo helper de política) ou `0001_baseline.py`.

## Success signal

- Em `./verify.sh` verde e no navegador local: `bidder1@example.com` / `Demo123!` entra, vê "Licitante", recarrega e continua logado, sai e volta ao formulário; uma senha errada mostra "E-mail ou senha inválidos."; adicionar uma rota sem política faz o `pytest` falhar.

## Assumptions

Aprovadas junto com a spec em 24/10/2026 (registro, não pendência):

- Testes obtêm `JWT_SECRET` aleatório gerado pelo `conftest` em tempo de execução (story P1 a); `verify.sh` não muda.
- O CA8 da story ("GET nunca autenticam") significa "GET nunca cria nem remove sessão"; `GET /api/me` lê o cookie.

## Decisões fechadas nesta revisão (24/10/2026)

- **OQ-1 = (a).** `http://` só com host `localhost`, `127.0.0.1` ou `::1` (cookie `auction_session`, `Secure=false`); `https://` usa `__Host-auction_session`, `Secure=true`; `http://` com outro host impede o boot com erro claro. Descartei aceitar `http` remoto com cookie sem `Secure`.
- **OQ-2 = (a).** `OPTIONAL`: cookie ausente, inválido, expirado, de usuário inexistente ou com papel incoerente → anônimo; válido → usuário. Descartei 401 em rota opcional.
- **OQ-3 = (a).** A rota de login usa `error_response(401, "invalid_credentials")`, mensagem "E-mail ou senha inválidos.". Descartei `ApiError`.
- **Suposições aprovadas:** login e `/api/me` devolvem só `{email, role}`; `Cache-Control: no-store` nas respostas de autenticação; `Max-Age=28800`; e-mail `strip` + minúsculas, até 254; senha até 1024; `CHECK (email = lower(email))`; seed com `ON CONFLICT DO NOTHING`, nunca `UPDATE`; a linha de estado do `/health` permanece.
- **Meta-teste reprojetado.** Política como metadata nossa gravada pelo helper de registro e lida por travessia recursiva de estruturas públicas. Descartei `fastapi.routing.iter_route_contexts` (não documentada).
