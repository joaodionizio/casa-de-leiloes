# Plano de testes — Story 2.2

Nenhum teste existente é afrouxado. Mudam só pelo escopo: os testes do cookie
técnico saem (CA9), `test_openapi.py` passa a listar as rotas novas e
`test_database.py` passa a esperar `["alembic_version", "users"]`.

## 1. Infraestrutura de teste

- `conftest.py`, no topo do módulo (antes de qualquer import de `app.main` pela coleta): `os.environ["JWT_SECRET"] = secrets.token_urlsafe(48)`, sempre sobrescrevendo (os testes nunca usam o segredo do `backend/.env`). Valor nunca impresso.
- Fixture `db_session_factory` (sessão `_test`) e fixture `clean_users` que faz `TRUNCATE users` no banco `_test` antes de cada teste que grava, pela mesma guarda de banco de teste (`assert_connection_is_test_database`).
- Helper `build_client(origin, *, with_db=True)`: `create_app(app_origin=origin)` sem SPA (padrão de `synthetic_api.build_app`), `dependency_overrides[get_session]` para o `_test`, `TestClient(base_url=origin)`. Modo https: `origin="https://testserver"`; modo http: `origin="http://localhost:5173"`. O `httpx` só reenvia cookie `Secure` em `https`.
- Usuários de teste: criados pelo `seed_users` (mesmas contas) ou por helper que usa `hash_password`.
- Rotas sintéticas (P10) em `tests/synthetic_api.py`, registradas pelo helper `api_route` (mesma convenção da app real) só na app de teste: `/api/test/auctioneer-only` (`AUCTIONEER`), `/api/test/bidder-only` (`BIDDER`), `/api/test/optional` (`OPTIONAL`, devolve `{"email": ...}` ou `{"anonymous": true}`). As rotas sintéticas da 2.1 (`build_router` + `include_router`) continuam como estão: só existem em apps de teste e nunca passam pelo verificador.

## 2. Testes sem banco

| Arquivo | Casos |
| --- | --- |
| `test_config.py` | `JWT_SECRET` ausente, vazio, 31 caracteres → `ValidationError` sem o valor na mensagem; 32 aceito; lido do ambiente; `create_app(jwt_secret="curto")` falha. Modo do cookie: `https://casa.example` → `__Host-auction_session`, `Secure`; `http://localhost:5173`, `http://127.0.0.1:8000`, `http://[::1]:5173` → `auction_session`, sem `Secure`; `create_app(app_origin="http://casa.example")` e `"http://192.168.0.10:8000"` → erro na criação, mensagem sem a origem; `OriginSettings` continua aceitando essas origens (testes da 2.1 inalterados). |
| `test_security.py` | `hash_password` começa com `$argon2id$` e difere do texto; `verify_password` certo/errado; hash inválido propaga. JWT: emitido decodifica com exatamente `{sub, role, iat, exp}`, `exp - iat == 28800`, sem e-mail; recusa (via dependência) outro segredo, `alg: none`, HS512/HS384, sem `exp`/`sub`/`role`/`iat`, expirado (`exp` no passado), `iat` futuro, lixo, `sub` não-UUID, `role` desconhecido. |
| `test_access_policy.py` | App real sem SPA e com SPA (`dist` temporário): `policy_problems(app.routes) == []`; `policy_by_route(app)` igual à tabela exata `/health` PUBLIC, SPA `/{full_path:path}` PUBLIC, `/api/infra-check/ws` PUBLIC, `/api/auth/login` PUBLIC, `/api/auth/logout` PUBLIC, `/api/me` AUTHENTICATED; allowlist exatamente `{"/api/docs", "/api/openapi.json"}` e ambas presentes. Meta-teste (cada caso numa app nova, sobre a app real): `@app.get` sem helper → "sem política" naquele caminho; `@app.websocket` sem helper → reporta; `include_router` de um `APIRouter` → "tipo de rota não suportado"; `app.mount("/sub", sub_app)` com rota sem política → reporta `/sub/...` (prova a recursão); `app.mount("/static", StaticFiles(directory=tmp))` → "mount sem rotas inspecionáveis"; função com `access_policy` que não é `AccessPolicy` → reporta. **Regressões do M1** (a metadata só vale se a rota carrega a dependência da política, via `route.dependencies`; 6 testes): (1) rota registrada pelo helper continua passando e aparece em `policy_by_route` com a política declarada; (2) WebSocket técnico `PUBLIC` continua passando; (3) endpoint protegido (`AUCTIONEER`) reutilizado por `@app.get` empilhado → o verificador reporta "política AUCTIONEER sem a dependência" só no caminho reaproveitado, a rota original continua na tabela e a reaproveitada fica de fora, e o mesmo teste demonstra por HTTP que a rota protegida responde 401 sem login e a reaproveitada sem proteção responde 200, isto é, o meta-teste detecta a inconsistência real; (4) `app.add_api_route` reutilizando endpoint protegido (`BIDDER`) → reporta "política BIDDER sem a dependência" e fica fora da tabela; (5) endpoint `AUCTIONEER` reutilizado com `dependencies=[Depends(require_user)]` (dependência diferente da declarada) → reporta; (6) `Route` e `WebSocketRoute` puras do Starlette com `access_policy` válida na função → reportam "política PUBLIC sem a dependência". Helper: endpoint reutilizado com outra política → `ValueError`; rota `PUBLIC` com `Depends(require_user)` na assinatura → `ValueError`; `require_user` declarado na política e na assinatura roda uma vez por requisição. Busca textual nas linhas `import`/`from ... import` de `app/` e `tests/`: nenhuma traz `iter_route_contexts`, `_IncludedRouter` ou módulo/nome `_`-prefixado de `fastapi`/`starlette`. Sem cadastro: `POST /api/auth/register`, `POST /api/users`, `GET /api/users` → 404/405 JSON; nenhum caminho com `register`, `signup` ou `users`. |
| `test_csrf_auth.py` (ou em `test_csrf.py`) | Login e logout com `Origin` estrangeiro, sem `Origin`/`Referer`, `Referer` estrangeiro → 403 `csrf_*`; sem `Content-Type` ou `text/plain` → 415; em todos: sem `Set-Cookie` e handler não executado (contador ou patch da função de login). `GET`/`HEAD`/`OPTIONS` em `/api/auth/login` e `/api/auth/logout` → 405 sem `Set-Cookie`. Nenhuma resposta tem `access-control-*`. |
| `test_openapi.py` | `paths` = `["/health", "/api/auth/login", "/api/auth/logout", "/api/me"]` (ordem de registro); login 401 e 422 e `/api/me` 401 com `$ref` para `ErrorResponse`; `HTTPValidationError` ausente de `components.schemas`; infra fora. |
| `test_infra_check.py` | Remover os testes do cookie; acrescentar `GET /api/infra-check/cookie` → 404 JSON; testes do WebSocket inalterados. |
| `test_health.py`, `test_spa.py`, `test_errors.py` | Inalterados e verdes (criar a app sem banco continua possível). |

## 3. Testes em PostgreSQL real (`tests/integration/`)

| Arquivo | Casos |
| --- | --- |
| `test_users_migration.py` | Em `head`, `users` existe com colunas, `pk_users`, `uq_users_email`, `ck_users_role`, `ck_users_email_lowercase`; INSERT com `role='ADMIN'`, com e-mail maiúsculo e e-mail duplicado → `IntegrityError`; `downgrade` para `0001` remove a tabela e `upgrade head` a recria (no fim, banco de volta em `head`). |
| `test_database.py` | `tables == ["alembic_version", "users"]`; `engine.hide_parameters is True`; erro de UNIQUE com um marcador sensível no parâmetro `password_hash` (não na chave violada) não contém o marcador em `str(error)`. O marcador **não** fica no e-mail: o PostgreSQL escreve a chave duplicada (o e-mail) no `DETAIL` da própria mensagem, e `hide_parameters` não controla isso. O objetivo do teste é provar o comportamento do SQLAlchemy (não renderizar os valores dos parâmetros), não prometer sanitização das mensagens do PostgreSQL. |
| `test_seed.py` | Banco vazio → 3 linhas com IDs, e-mails e papéis esperados, hashes `$argon2id$` que verificam `Demo123!`; segunda execução devolve 0 e as linhas (todas as colunas, incluindo hash) ficam idênticas; usuário semeado com `role` alterado manualmente não é revertido; e-mail semeado já usado por outro `id` → falha; `python -m app.seed` como subprocesso (`runpy.run_module('app.seed', run_name='__main__')`, como o `-m` faria) com `DATABASE_URL` do `_test` e sem `APP_ORIGIN`/`JWT_SECRET` no ambiente → sai 0, e o subprocesso sai com 42 se `'app.main' in sys.modules` ao terminar, isto é, o teste verifica `'app.main' not in sys.modules` após a execução do seed. Tirar as variáveis do ambiente não bastaria: as configurações também leem o `backend/.env`; o que prova que o seed não depende do boot completo da aplicação é `app.main` não ter sido importado. *Nota (observação opcional, não implementada):* se o `__main__` do seed passar a chamar `sys.exit(...)`, a checagem de `sys.modules` no fim do subprocesso deixa de rodar; reavaliar nesse caso. |
| `test_auth_flow.py` (modo https e modo http) | Login válido → 200 `{email, role}` exato, `Set-Cookie` único com nome do modo, `HttpOnly`, `SameSite=lax`, `Path=/`, sem `Domain`, `Max-Age=28800`, `Secure` só em https; token ausente do corpo; `no-store`. E-mail `"  Bidder1@Example.COM "` entra. Login inválido: e-mail inexistente e senha errada → 401, corpos `bytes` iguais, `code=invalid_credentials`, sem `Set-Cookie`, e-mail ausente do corpo, `no-store`; e-mail inexistente chama `security.verify_password` com exatamente o hash de referência (`$argon2id$`) e a senha enviada (spy com `wraps`: a verificação Argon2 real roda), enquanto e-mail existente a chama com o hash do usuário, nunca o de referência. Campos ausentes, vazios, e-mail > 254, senha > 1024, JSON malformado → 422 sem `input`. `/api/me` com cookie → 200 e `no-store`; sem cookie, adulterado, expirado (token forjado com `exp` passado e o segredo de teste), usuário apagado depois do login, `role` alterado no banco depois do login → 401 `unauthorized`. Logout com sessão → 204 e `Set-Cookie` de expiração (mesmo nome, `Path=/`, `HttpOnly`, `SameSite`, `Secure` conforme modo, `Max-Age=0`); depois `/api/me` → 401; logout sem cookie e com cookie inválido → 204; cookie `__Host-` não é aceito no modo http e vice-versa. |
| `test_roles.py` | Sobre as rotas sintéticas: AUCTIONEER → 200 em `auctioneer-only`, 403 `forbidden` em `bidder-only`; BIDDER o inverso; sem sessão → 401 nas duas; `optional`: sem cookie → anônimo; sessão válida → e-mail do usuário; cookie adulterado, expirado, de usuário apagado e com papel alterado no banco → anônimo, status 200, sem `Set-Cookie`; as mesmas quatro situações em `auctioneer-only`/`bidder-only` → 401. |

## 4. Front-end (sem biblioteca nova)

- `verify`: `npm run lint`, `npm run typecheck`, `npm run build` (já existentes).
- Revisão estática no review: nenhum `localStorage`, `sessionStorage` ou `document.cookie` em `src/` (busca textual); nenhuma dependência nova em `package.json`; textos de §5 de `frontend-login.md`.

## 5. Roteiro manual obrigatório no navegador (eu executo)

Preparação local: `docker compose up -d --wait postgres`; em `backend/`, `alembic upgrade head` e `python -m app.seed`; `JWT_SECRET` no meu `backend/.env`; `APP_ORIGIN=http://localhost:5173 uv run uvicorn app.main:app --port 8000`; `npm run dev`; abrir `http://localhost:5173`.

1. Carrega: "Verificando sua sessão…" e depois o formulário "Entrar"; sem link morto no header.
2. Enviar vazio → "Informe e-mail e senha." sem requisição (aba Network).
3. `bidder1@example.com` + senha errada → "E-mail ou senha inválidos."; e-mail mantido, senha vazia, foco na senha.
4. `ninguem@example.com` + qualquer senha → mesma mensagem.
5. `  Bidder1@Example.com ` + `Demo123!` → header com o e-mail, "Licitante" e "Sair".
6. DevTools → Application → Cookies: `auction_session` com HttpOnly, SameSite Lax, Path `/`, sem Secure; Console `document.cookie` não mostra a sessão; Local/Session Storage vazios.
7. Recarregar → continua logado (Network: `GET /api/me` 200).
8. "Sair" → formulário, foco no e-mail; cookie sumiu; recarregar → formulário.
9. `auctioneer@example.com` → "Leiloeiro".
10. Parar o uvicorn e tentar entrar → "Não foi possível falar com o servidor. Tente novamente."; religar.
11. Só teclado: Tab, Enter, foco visível em campos e botões.
12. Largura 320 px e desktop largo: sem rolagem horizontal; e-mail longo truncado no header; formulário não estica.
13. Visual contra frontend-login §6: sem card, sombra, pill, gradiente, roxo de fundo.

Depois do deploy (eu, com `JWT_SECRET` já no Render): repetir 5–8 na URL pública e conferir `__Host-auction_session` com `Secure`.
