# Contrato do back-end — Story 2.2

Referência das decisões: P1–P16 e OQ-1–OQ-3, todas aprovadas (SPEC.md).
Nomes de módulos e funções são a proposta desta spec; o `bmad-build` pode
ajustar nomes internos, nunca o contrato externo (rotas, códigos, cookie, tabela).

## 1. Estado atual (conferido nos arquivos, 24/10/2026)

| Item | Real |
| --- | --- |
| Versões | FastAPI 0.162.0, Starlette 1.9.0, Pydantic 2.14.1, pydantic-settings 2.16.1, SQLAlchemy 2.1.6, Alembic 1.20.1, psycopg 3.3.6, Python 3.13. Sem PyJWT nem argon2-cffi. |
| Factory | `create_app(spa_dist_dir=None, app_origin=None)` em `app/main.py`; `app = create_app()` roda **no import** do módulo. |
| Erros | `app/errors.py`: `CODE_BY_STATUS`, `MESSAGES`, `error_response(status, code, details=, headers=)`; `HTTPException.detail` nunca sai; `unauthorized`/`forbidden` já existem. |
| Guard | `ApiWriteGuardMiddleware` (ASGI puro, `app/csrf.py`): POST/PUT/PATCH/DELETE sob `/api` exigem `Origin` (ou `Referer`) = `APP_ORIGIN` e `Content-Type: application/json`, antes do roteamento, sem ler corpo. |
| Config | `Settings` (`DATABASE_URL`, `TEST_DATABASE_URL`), `SpaSettings`, `OriginSettings` (`APP_ORIGIN` canônica, `hide_input_in_errors=True`); cada uma com `get_*` em `lru_cache`. |
| Banco | `app/db.py`: `Base` com naming convention, `create_db_engine(url)` (`pool_pre_ping=True`, sem `hide_parameters`), `create_session_factory`. Sem sessão por requisição. |
| Migrations | `0001_baseline` vazia; `migrations/env.py` aceita URL em `config.attributes["database_url"]`. |
| Start | `backend/scripts/start.sh`: `alembic upgrade head` → `exec uvicorn`. Dockerfile copia `app/`, `migrations/`, `alembic.ini`, `scripts/start.sh`; venv no `PATH`. |
| Infra 1.4 | `app/infra_check.py`: `GET /api/infra-check/cookie` (`__Host-infra_check`) e `/api/infra-check/ws`, router com `include_in_schema=False`. |
| Testes | `conftest.py` recria o schema `_test` uma vez por sessão e aplica migrations; `synthetic_api.py` (precedente de rotas só de teste); `test_openapi.py` fixa `paths == ["/health"]`; `test_database.py` fixa `tables == ["alembic_version"]`. |
| Roteamento 0.162 | `include_router` deixa um `_IncludedRouter` (classe privada) em `app.routes`, sem achatar as rotas. Enumerar rotas incluídas exigiria API não documentada; por isso a app real deixa de usar `include_router` e registra toda rota diretamente na app (§9). `app.add_api_route` e `app.add_api_websocket_route` colocam `APIRoute`/`APIWebSocketRoute` direto em `app.routes`. Verificado com script local. |

## 2. Fluxo completo

1. A SPA carrega e chama `GET /api/me` (mesma origem; o navegador envia o cookie se existir).
2. Sem sessão → 401 `unauthorized` → a tela mostra o formulário.
3. O usuário envia e-mail e senha → `POST /api/auth/login`, `Content-Type: application/json`; o navegador envia `Origin`.
4. O guard da 2.1 valida `Origin` e `Content-Type` antes do roteamento (falha → 403/415, handler não roda).
5. O handler normaliza o e-mail, busca o usuário, verifica Argon2 (ou o hash de referência), emite o JWT e devolve 200 `{email, role}` com `Set-Cookie`.
6. A SPA guarda só `{email, role}` em estado React e mostra o cabeçalho da conta.
7. Ao recarregar, o passo 1 devolve 200 `{email, role}` (cookie válido): continua logado.
8. "Sair" → `POST /api/auth/logout` (mesmo guard) → 204 com `Set-Cookie` de expiração → a SPA volta ao formulário.
9. Um JWT copiado antes do logout continua válido até `exp` (AD-29; README).

## 3. Rotas

| Método e caminho | Política | Corpo | Sucesso | Erros |
| --- | --- | --- | --- | --- |
| `POST /api/auth/login` | PUBLIC | `LoginRequest` | 200 `CurrentUser` + `Set-Cookie` sessão | 401 `invalid_credentials`; 422 `validation_error`; 403 `csrf_*`; 415 |
| `POST /api/auth/logout` | PUBLIC | nenhum (ignorado) | 204 + `Set-Cookie` de expiração | 403 `csrf_*`; 415 |
| `GET /api/me` | AUTHENTICATED | — | 200 `CurrentUser` | 401 `unauthorized` |
| `GET /health` | PUBLIC | — | inalterada | — |
| SPA `GET/HEAD /{full_path:path}` | PUBLIC | — | inalterada | — |
| WS `/api/infra-check/ws` | PUBLIC | — | inalterado | — |
| `/api/docs`, `/api/openapi.json` | allowlist do framework (§9) | — | inalteradas | — |

- Login, logout e `/api/me` respondem com `Cache-Control: no-store` (sucesso e erro do próprio handler/dependência).
- GET/HEAD/OPTIONS em login/logout → 405 JSON do contrato, sem cookie. `HEAD /api/me` → 405 (rota só GET).
- Não existe rota de cadastro nem `/api/users`.

## 4. Schemas

`LoginRequest` (Pydantic, `extra` ignorado):

| Campo | Tipo | Regra |
| --- | --- | --- |
| `email` | `str` | `strip()` + `lower()`; depois disso 1..254 caracteres, senão 422. Formato não validado (inválido → 401 pelo caminho normal); sem `email-validator`. |
| `password` | `str` | 1..1024 caracteres, sem `strip`; fora disso 422. |

`CurrentUser` (resposta de login e `/api/me`): `{"email": str, "role": "AUCTIONEER" | "BIDDER"}`. Nada mais.

`ErrorResponse` (só documentação, em `app/errors.py`): `status: int`, `code: str`,
`message: str`, `details: list[ErrorDetail] | None` (omitido em runtime quando
vazio); `ErrorDetail`: `loc: list[str | int]`, `type: str`. Não é `response_model`
de nenhuma rota.

## 5. Modelo `users` e migration `0002`

`backend/migrations/versions/0002_users.py`, `revision="0002"`, `down_revision="0001"`:

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | `UUID` | PK `pk_users`; sem default no banco (IDs do seed fixos) |
| `email` | `VARCHAR(254)` | `NOT NULL`, `uq_users_email`, `ck_users_email_lowercase CHECK (email = lower(email))` |
| `password_hash` | `TEXT` | `NOT NULL` |
| `role` | `VARCHAR(16)` | `NOT NULL`, `ck_users_role CHECK (role IN ('AUCTIONEER','BIDDER'))` |

- Nomes de constraint explícitos (`op.f(...)`) compatíveis com a `NAMING_CONVENTION`.
- `downgrade()`: `drop_table("users")`.
- Sem enum nativo, sem `created_at`, sem `display_name`, sem carteira.
- Modelo SQLAlchemy `User` (`app/users.py`) espelha a migration; `UserRole(StrEnum)` com `AUCTIONEER`/`BIDDER`. O esquema dos testes vem da migration, nunca de `create_all`.

## 6. Cookie de sessão (P4, OQ-1 = a)

Derivado da `APP_ORIGIN` canônica, uma vez, em `create_app()`; sem `APP_ENV`:

| `APP_ORIGIN` | Nome | `Secure` |
| --- | --- | --- |
| `https://...` | `__Host-auction_session` | sim |
| `http://` com host `localhost`, `127.0.0.1` ou `::1` (comparação pelo host canônico de `parse_origin`, qualquer porta) | `auction_session` | não |
| `http://` com outro host | — | `create_app()` levanta `ValueError` com mensagem fixa ("APP_ORIGIN must use https unless the host is localhost, 127.0.0.1 or ::1"), sem ecoar a origem; o boot não acontece |

`OriginSettings` continua aceitando qualquer origem válida (seus testes da 2.1 não
mudam); a recusa de `http` remoto acontece na derivação do cookie, dentro de
`create_app()`.

Sempre: `HttpOnly`, `SameSite=Lax`, `Path=/`, sem `Domain`, `Max-Age=28800`
(igual à vida do token). Logout: `delete_cookie(nome, path="/", secure=<modo>,
httponly=True, samesite="lax")` (Starlette 1.9 emite `Max-Age=0` e `expires`
no passado). A dependência de autenticação lê só o nome do modo atual; nunca
`Authorization`. Um 401 não apaga cookie.

## 7. Senha (P2, P6)

- `argon2.PasswordHasher()` com os parâmetros padrão da biblioteca (Argon2id); uma instância por processo.
- `hash_password(plain) -> str`; `verify_password(hash, plain) -> bool`: `VerifyMismatchError` → `False`; `InvalidHashError`/outros erros → propagam (500 genérico; hash corrompido não vira 401 silencioso).
- Hash de referência: calculado uma vez por processo, sob demanda, com o mesmo `PasswordHasher` sobre um valor aleatório (`secrets`); o resultado da verificação contra ele é sempre ignorado e o login devolve 401.
- Nenhuma senha ou hash em log, resposta ou mensagem de exceção.

## 8. JWT (P1, P3)

- Emissão: `jwt.encode({"sub": str(user.id), "role": user.role, "iat": now, "exp": now + 8 h}, secret, algorithm="HS256")`, com `now` do relógio da aplicação em UTC (o AD-6 rege lance e fechamento, não sessão).
- Validação num único ponto, `resolve_session_user(request, session) -> User | None` (em `app/access.py`), que devolve `None` em qualquer falha, nesta ordem:
  1. cookie do modo ausente;
  2. `jwt.decode(token, secret, algorithms=["HS256"], options={"require": ["sub", "role", "iat", "exp"]}, leeway=0)` levanta qualquer `jwt.InvalidTokenError` (assinatura, `alg` diferente ou `none`, expirado, `iat` futuro, malformado, claim ausente);
  3. `sub` não é UUID ou `role` fora de `UserRole`;
  4. `session.get(User, uuid)` ausente;
  5. `user.role != claims["role"]` (banco é a autoridade);
  6. senão, devolve o `User`.
- `require_user` transforma `None` em `HTTPException(401)` → `unauthorized` pelo catálogo, sem `WWW-Authenticate`; `optional_user` devolve o resultado como está (§9).

## 9. Políticas de acesso (P8, P9, OQ-2 = a) e meta-teste

### Dependências (`app/access.py`, todas síncronas)

| `AccessPolicy` | Dependência | Comportamento |
| --- | --- | --- |
| `PUBLIC` | `public()` | no-op |
| `OPTIONAL` | `optional_user()` → `User \| None` | `resolve_session_user`; cookie ausente, inválido, expirado, de usuário inexistente ou com papel incoerente → `None` (anônimo), sem 401 e sem apagar cookie; válido → `User`. Nunca concede dado protegido sem sessão válida. |
| `AUTHENTICATED` | `require_user()` → `User` | `None` → 401 |
| `AUCTIONEER` | `require_auctioneer()` → `User` | `Depends(require_user)` + papel ≠ `AUCTIONEER` → `HTTPException(403)` |
| `BIDDER` | `require_bidder()` → `User` | `Depends(require_user)` + papel ≠ `BIDDER` → `HTTPException(403)` |

`POLICY_DEPENDENCIES: dict[AccessPolicy, Callable]` liga cada política à sua
dependência. A lógica de autenticação existe só em `resolve_session_user`.

### Declaração: helpers de registro (metadata nossa)

Toda rota da app real entra por um destes helpers de `app/access.py`, que são o
único lugar onde a política é declarada:

- `api_route(app, path, *, methods, policy, **kwargs)` → decorador que:
  1. recusa (`ValueError`) se o endpoint já tem outra política (função reutilizada);
  2. recusa (`ValueError`) se algum parâmetro da assinatura (`inspect.signature`) tem como default um `Depends` de uma dependência de `POLICY_DEPENDENCIES` diferente da declarada (ex.: rota `PUBLIC` com `Depends(require_user)`); só o estilo `= Depends(...)` é usado na assinatura, nunca `Annotated`;
  3. grava a metadata: `endpoint.access_policy = policy` (atributo do nosso código na função);
  4. registra com `app.add_api_route(path, endpoint, methods=methods, dependencies=[Depends(POLICY_DEPENDENCIES[policy])], **kwargs)`.
- `websocket_route(app, path, *, policy)` → mesmo fluxo com `app.add_api_websocket_route(path, endpoint, dependencies=[...])`.

O handler que precisa do usuário repete a mesma dependência no parâmetro
(`user: User = Depends(require_user)`); o cache de dependências do FastAPI
(`use_cache` padrão) a executa uma vez por requisição (verificado no 0.162).

Consequências na app real:

- Sem `APIRouter`/`include_router`: `auth.py` expõe `register_auth_routes(app)`, `infra_check.py` expõe `register_infra_check_routes(app)`, como já faz `register_spa_routes(app, dist)`.
- `/health` (em `main.py`), SPA (`spa.py`, `methods=["GET", "HEAD"]`, `include_in_schema=False`, `response_model=None`), login, logout, `/api/me` e o WebSocket técnico usam os helpers. Rotas de infra mantêm `include_in_schema=False`.

### Verificador e meta-teste (`tests/access_policy.py`)

`policy_problems(routes, prefix="") -> list[str]`, só com estruturas públicas
(`app.routes`, `.path`, `.endpoint`, `.dependencies`, `Mount.routes`; classes
importadas de `fastapi.routing` — `APIRoute`, `APIWebSocketRoute` — e
`starlette.routing` — `Route`, `WebSocketRoute`, `Mount`).

A metadata `access_policy` do endpoint diz a política **declarada**, mas sozinha
não prova nada: a mesma função pode ser registrada de novo fora do helper (`@app.get`
empilhado sobre o endpoint, `app.add_api_route`) e a nova rota nasceria aberta
carregando a marca de protegida (achado M1 do code review). Por isso uma política
declarada só vale se a **própria rota** a aplica: a dependência
`POLICY_DEPENDENCIES[política]` precisa estar em `route.dependencies`
(comparação por identidade com o `.dependency` de cada item). `Route` e
`WebSocketRoute` puras do Starlette não têm `dependencies`, então nunca aplicam
uma política: uma dessas com metadata `access_policy` é reprovada.

1. `Mount` → recursão em `mount.routes` com `prefix + mount.path`; um `Mount` sem rotas inspecionáveis (`routes` vazio, ex.: `StaticFiles`) é problema "mount sem rotas inspecionáveis", para que nenhuma área pública entre sem decisão explícita. A app real não tem `Mount` hoje.
2. `APIRoute`, `APIWebSocketRoute`, `Route`, `WebSocketRoute` → caminho completo `prefix + route.path`, depois:
   - `getattr(route.endpoint, "access_policy", None)` não é um `AccessPolicy`: ok se o caminho está em `FRAMEWORK_ROUTES = {"/api/docs", "/api/openapi.json"}`; senão problema "sem política: <caminho>";
   - é um `AccessPolicy`, mas a rota não é `APIRoute`/`APIWebSocketRoute` ou `route.dependencies` não contém `POLICY_DEPENDENCIES[política]` (inclui o caso de uma dependência **diferente** da declarada, como `require_user` numa rota declarada `AUCTIONEER`): problema "política <POLÍTICA> sem a dependência: <caminho>";
   - é um `AccessPolicy` e a dependência correspondente está em `route.dependencies`: ok.
3. Qualquer outro tipo (ex.: o objeto que `include_router` deixa em `app.routes`, `Host`) → problema "tipo de rota não suportado: <nome da classe>". Nenhum tipo privado é importado; o teste só observa que o objeto não é de um tipo conhecido.

`policy_by_route(app) -> dict[(path, kind), AccessPolicy]` (mesma travessia)
alimenta a tabela esperada do teste e só contém rotas que **declaram e de fato
aplicam** a política: uma rota reprovada pelo critério acima (por exemplo, o
endpoint protegido reaproveitado sem a dependência) fica de fora da tabela, em
vez de aparecer como protegida.

Só atributos e classes públicos: o verificador não usa `route.dependant`, não
importa `iter_route_contexts`, `_IncludedRouter` nem qualquer `_`-prefixado de
FastAPI/Starlette (o teste de imports de `app/` e `tests/` garante). Isso amplia
a lista de estruturas públicas lidas (agora com `.dependencies`), sem mudar o
P9: a política continua metadata nossa gravada pelos helpers.

### Outros

- Configuração da sessão (segredo, nome do cookie, `Secure`) fica em `app.state` (ex.: `app.state.session_cookie`), preenchida por `create_app()`; as dependências leem `request.app.state`. Assim apps de teste com origens diferentes convivem no mesmo processo.
- Sem middleware de autenticação e sem ordem global 401 → 403 → 422 (P8). Observado no 0.162: uma dependência que levanta 401 responde antes da validação do corpo; não é requisito nem teste.

## 10. Sessão de banco e engine (P16, CA11)

- `create_db_engine(url)` passa `hide_parameters=True`. O que isso garante: o SQLAlchemy não renderiza os valores dos parâmetros SQL na mensagem das suas exceções. O que não garante: o `DETAIL` escrito pelo próprio PostgreSQL pode conter valores (violação de UNIQUE mostra a chave, ou seja, o e-mail; violação de CHECK mostra a linha inteira, inclusive o `password_hash`). Não há sanitização global de `DETAIL` nesta story. Hoje nenhum caminho do código viola as CHECKs de `users`.
- `get_engine()` com `lru_cache`, a partir de `get_settings().database_url`, criado só na primeira requisição que precisa de banco.
- `get_session()`: dependência `def` com `yield` de `Session` curta, fechada no fim; sem commit automático (login e `/api/me` só leem).
- Testes: `app.dependency_overrides[get_session]` aponta para o banco `_test`.

## 11. Seed (P12, P13) e `start.sh`

`app/seed.py`:

- Constantes versionadas: `SEED_USERS` = três `(UUID fixo, email, UserRole)`; UUIDs gerados uma vez na implementação (não são segredo). `DEMO_PASSWORD = "Demo123!"` com comentário: credencial pública de demonstração, documentada no README, não é segredo.
  - `auctioneer@example.com` → `AUCTIONEER`; `bidder1@example.com`, `bidder2@example.com` → `BIDDER`.
- `seed_users(session) -> int`: numa transação, lê quais IDs semeados já existem; calcula Argon2 só para os ausentes; `INSERT ... ON CONFLICT (id) DO NOTHING`; nunca `UPDATE`; devolve quantos inseriu. E-mail semeado já usado por outro `id` → a `IntegrityError` de `uq_users_email` propaga (o processo sai com erro). O `DETAIL` do PostgreSQL mostra a chave duplicada, então o e-mail semeado, que é público (P13), aparece no log; `hide_parameters` não controla essa mensagem (§10).
- `python -m app.seed`: lê `DATABASE_URL` (`Settings`), roda `seed_users`, faz commit, loga só a contagem; código de saída ≠ 0 em falha. Não importa `app.main` (não exige `APP_ORIGIN` nem `JWT_SECRET`). Não cria lote nem consulta API externa.
- `start.sh`: `alembic upgrade head` → `python -m app.seed` → `exec uvicorn ...`; `set -eu` mantém o servidor parado se o seed falhar. Comentário do script atualizado.

## 12. Configuração do segredo (P1)

- `AuthSettings` (separada de `Settings`, como `OriginSettings`; `hide_input_in_errors=True`, `env_file=ENV_FILE`): `jwt_secret: SecretStr`, validador `len >= 32` caracteres com mensagem fixa sem o valor.
- `create_app(..., jwt_secret: str | None = None)`: sem argumento, lê `get_auth_settings()`; com argumento, valida pela mesma classe (`_env_file=None`), como `app_origin`. Ausente/curto → `ValidationError` na criação, sem ecoar.
- `SecretStr` em todo lugar; nunca logado nem em resposta. `backend/.env.example` é editado pelo usuário.

## 13. Erros (P6, P8, OQ-3 = a)

- `errors.py`: novo código `INVALID_CREDENTIALS = "invalid_credentials"` em `MESSAGES` ("E-mail ou senha inválidos."). `CODE_BY_STATUS[401]` continua `unauthorized`.
- A rota de login devolve `error_response(401, INVALID_CREDENTIALS, headers={"Cache-Control": "no-store"})` nos dois casos (e-mail inexistente e senha errada). Sem `ApiError`, sem hierarquia de exceções, sem mudança nos handlers.
- 401 `unauthorized` e 403 `forbidden` saem de `HTTPException` pelo handler existente.
- Base aprovada: `no-store`; `Max-Age=28800`; `leeway=0`; relógio da aplicação UTC para `exp`; e-mail `strip`+`lower`; limites 254/1024; formato do e-mail não validado; seed com `ON CONFLICT DO NOTHING` e sem `UPDATE`; colisão de e-mail falha; 401 não apaga cookie; sem `WWW-Authenticate`; `CHECK (email = lower(email))`.

## 14. OpenAPI (P14)

- Verificado no FastAPI 0.162: `responses={422: {"model": ErrorResponse}}` na rota substitui o `HTTPValidationError` dela; quando nenhuma rota do schema o usa, `HTTPValidationError` e `ValidationError` somem de `components.schemas`. SPA e infra estão fora do schema.
- `errors.py` expõe `error_responses(*statuses) -> dict` (dicionário simples `{status: {"model": ErrorResponse}}`).
- Login: `responses=error_responses(401, 422)`; `/api/me`: `error_responses(401)`; logout: só 204 (`status_code=204`, sem corpo). 403/415 do guard não são documentados por rota (README da 2.1 já os descreve). Sem override de `app.openapi()`.
- Limite registrado: rotas futuras com corpo precisam declarar `error_responses(..., 422)`; o teste de OpenAPI (`HTTPValidationError` ausente) reprova quem esquecer.

## 15. Integração com a proteção da 2.1

- `csrf.py` intocado. Login e logout passam pelo guard como qualquer escrita; o front envia `Content-Type: application/json` também no logout sem corpo.
- Nenhum `CORSMiddleware`, nenhum `Access-Control-*`.

## 16. Remoção do cookie técnico (CA9)

- `infra_check.py`: remover `cookie_check`, `COOKIE_NAME`, `COOKIE_VALUE`, `COOKIE_MAX_AGE_SECONDS`, o `APIRouter` e imports sem uso; expor `register_infra_check_routes(app)`; docstring passa a dizer que só o WebSocket técnico resta, público, até a 4.1.
- `GET /api/infra-check/cookie` → 404 JSON do contrato (pelo roteador ou pelo fallback da SPA que recusa `/api`).
- WebSocket técnico: mesmo caminho (`/api/infra-check/ws`) e mesmo corpo do handler, registrado por `websocket_route(app, ..., policy=AccessPolicy.PUBLIC)`; seus testes passam inalterados.
