# Mapa de implementação — Story 2.2

## 1. Arquivos

| Área | Arquivo | Ação |
| --- | --- | --- |
| Back | `backend/pyproject.toml`, `backend/uv.lock` | `uv add pyjwt argon2-cffi` (versões fixadas pelo lock) |
| Back | `backend/app/config.py` | `AuthSettings` + `get_auth_settings`; derivação do modo do cookie a partir da origem canônica |
| Back | `backend/app/db.py` | `hide_parameters=True`; `get_engine` sob demanda; dependência `get_session` |
| Back | `backend/app/errors.py` | `invalid_credentials` no catálogo; `ErrorResponse`/`ErrorDetail`; `error_responses()` |
| Back | `backend/app/users.py` | novo: `UserRole`, `User` |
| Back | `backend/app/security.py` | novo: Argon2 (hash, verificação, hash de referência) e JWT (emissão, decodificação) |
| Back | `backend/app/access.py` | novo: `AccessPolicy`, `resolve_session_user`, dependências de política, `POLICY_DEPENDENCIES`, helpers `api_route` e `websocket_route` |
| Back | `backend/app/auth.py` | novo: `register_auth_routes(app)` (login, logout, `GET /api/me`), schemas `LoginRequest`/`CurrentUser`, cookie |
| Back | `backend/app/seed.py` | novo: `SEED_USERS`, `DEMO_PASSWORD`, `seed_users`, `__main__` |
| Back | `backend/app/main.py` | `jwt_secret` em `create_app`; recusa `http` não local; `app.state` da sessão; `/health` via `api_route(..., PUBLIC)`; chama `register_auth_routes` e `register_infra_check_routes`; sem `include_router` |
| Back | `backend/app/spa.py` | só troca `@app.api_route` por `api_route(app, ..., policy=PUBLIC)`; lógica intacta |
| Back | `backend/app/infra_check.py` | remove o cookie e o `APIRouter`; `register_infra_check_routes(app)` com `websocket_route(..., PUBLIC)`; docstring |
| Migração | `backend/migrations/versions/0002_users.py` | novo |
| Infra | `backend/scripts/start.sh` | passo `python -m app.seed` entre Alembic e uvicorn |
| Testes | `backend/tests/conftest.py` | `JWT_SECRET` de teste; fixtures de sessão e `clean_users` |
| Testes | `backend/tests/synthetic_api.py` | rotas sintéticas por papel e `optional` |
| Testes | `backend/tests/access_policy.py` | novo: `policy_problems`, `policy_by_route`, `FRAMEWORK_ROUTES` (travessia recursiva, só API pública) |
| Testes | `test_config.py`, `test_openapi.py`, `test_infra_check.py`, `integration/test_database.py` | alterados (test-plan §2–3) |
| Testes | `test_security.py`, `test_access_policy.py`, `test_csrf_auth.py`, `integration/test_users_migration.py`, `integration/test_seed.py`, `integration/test_auth_flow.py`, `integration/test_roles.py` | novos |
| Front | `frontend/src/index.css`, `App.tsx`, `App.css` | alterados |
| Front | `frontend/src/api/auth.ts`, `LoginForm.tsx`, `SiteHeader.tsx` | novos |
| Docs | `README.md` | contas demo e senha pública; `python -m app.seed`; `JWT_SECRET` (local e Render, sem valor); `-e JWT_SECRET=...` no `docker run` com placeholder; seção do cookie técnico trocada pela verificação do cookie de sessão; limitação do logout (token vale até `exp`); sem limite de tentativas de login |
| Docs | `docs/ARQUITETURA.md` | Q10: registrar `JWT_SECRET` e rotas de autenticação resolvidas na 2.2; ferramenta de teste do front continua aberta; nenhuma AD alterada |
| Docs | `docs/uso_de_ia.md` | entrada da 2.2 |
| BMAD | story 2.2 (decisões P1–P16 e OQ-1–3 em primeira pessoa, com descartadas; status `review`), `sprint-status.yaml` (`review`), `deferred-work.md` (retira o item `hide_parameters`) | alterados |
| Usuário | `backend/.env.example` (linha `JWT_SECRET=` sem valor), `backend/.env`, painel do Render | o usuário edita |
| Intocados | `Dockerfile`, `compose.yaml`, `verify.sh`, `app/csrf.py`, `0001_baseline.py`, `test_health.py`, `test_spa.py`, `test_errors.py`, `vite.config.ts`, `package.json` | — |
| `CLAUDE.md` | item 10 das questões | só se o usuário pedir |

## 2. Riscos

| Risco | Mitigação |
| --- | --- |
| Deploy cai se `JWT_SECRET` não estiver no Render antes do próximo deploy | README e story avisam; o usuário configura antes. |
| Alguém registra rota fora dos helpers (`@app.get`, `include_router`) numa story futura | O verificador reprova "sem política" ou "tipo de rota não suportado"; a convenção fica no docstring de `app/access.py`. |
| Metadata no endpoint diverge da dependência aplicada | Só o helper grava a metadata e aplica a dependência, na mesma chamada; recusa endpoint reutilizado com outra política e `Depends` de política diferente na assinatura. |
| Sem `APIRouter`, cada módulo repete o prefixo do caminho | Aceito: poucos endpoints; o caminho completo fica legível em cada rota. |
| Atualização do FastAPI muda a forma de `app.routes` | O verificador só usa API pública (`app.routes`, `.path`, `.endpoint`, `Mount.routes`); tipo inesperado reprova alto em vez de passar em silêncio. |
| Teste importa `app.main` antes do `JWT_SECRET` | Definir no topo do `conftest.py`; a coleta falha visivelmente se faltar. |
| Argon2 padrão (64 MiB por hash) no Render gratuito | Seed calcula hash só de usuário ausente; login é sequencial e raro na carga do desafio. |
| Timing de e-mail inexistente × existente | Hash de referência reduz a diferença; não prometo defesa perfeita (P6). |
| Cookie `Secure` não volta no `TestClient` em http | Testes do modo https usam `base_url="https://testserver"`. |
| TRUNCATE entre testes no banco errado | Mesma guarda de banco `_test` do `reset_test_database`. |
| `hide_parameters` reduz diagnóstico de erro | Aceito (P16); a mensagem do erro e o SQL continuam no log. |
| Credenciais demo públicas na URL pública | Inerente ao desafio (P13); README declara. |
| Token copiado sobrevive ao logout | Limitação aceita do AD-29; README. |

## 3. Verificação de contradições (P1–P16 × fontes vinculantes)

Nenhuma decisão contraria AD-1 a AD-30, `epics.md`, `FRONTEND-WORKFLOW.md`,
`DESIGN.md` ou `EXPERIENCE.md`. Divergências só com o texto da story, que as
decisões resolvem:

| Ponto | Story | Decisão | Por que não é conflito |
| --- | --- | --- | --- |
| Categorias de política | `epics.md`: "pública, autenticada ou por papel" | P9 acrescenta `OPTIONAL` | Em acesso, `OPTIONAL` é pública; o critério (toda rota declara) continua. |
| Precedência | CA7/matriz: "401 antes de 422" | P8 remove a ordem global | Não há AD nem critério do `epics.md` sobre essa ordem. |
| Nome do usuário | P15 (a): cabeçalho com nome | P11 sem `display_name` | `epics.md` só exige o papel; o e-mail identifica. |
| E-mails demo | `leiloeiro@...` | P13 `auctioneer@...` | A story deixava a escolha ao usuário; AD-30 não rege dados. |
| Tamanho do segredo | 32 bytes | 32 caracteres | Detalhe da story, sem AD. |

## 4. Fora de escopo (detalhe operacional)

Não criar a Story 2.3; não executar git; não tocar no WebSocket técnico além da
marcação; não alterar `Dockerfile`; não ler nem editar `.env*`.
