# Mapa de implementação — Story 2.4

## 1. Requisito → arquivo/função

| Requisito | Arquivo | Função/elemento |
| --- | --- | --- |
| CAP-11 tabela | `backend/migrations/versions/0003_lots.py` | `upgrade`, `downgrade` (`database-schema.md` §6), CHECKs de faixa com o literal `9007199254740991` |
| CAP-11 modelo | `backend/app/lots.py` | `class Lot(Base)` (CHECKs usando `MAX_CENTS`) |
| CAP-2 snapshot | `backend/app/lots.py` | `ArtworkSnapshot`, `snapshot_from_detail` |
| CAP-2, CAP-3 nível externo | `backend/app/lots.py` | `ArtworkRefusal`, `resolve_artwork_for_lot(client, external_id)` — **só** a rota de criação o chama |
| CAP-4 dinheiro (API/serviço) | `backend/app/lots.py` | `MAX_CENTS`, `Cents`, `LotTerms` |
| CAP-5 horário | `backend/app/lots.py` | `API_DATETIME_PATTERN`, `ApiDatetime`, `ScheduleViolation`, `Schedule`, `ends_not_after_scheduled_start`, `resolve_schedule`, `database_now` |
| CAP-1, CAP-7 persistência compartilhada | `backend/app/lots.py` | `create_lot(session, *, snapshot, terms, auctioneer_id, now, is_demo)` (sem rede), `lot_response` |
| CAP-1, CAP-3, CAP-6, CAP-7 rota | `backend/app/lots.py` | `register_lot_routes` → `create` (`POST /api/lots`) |
| CAP-8 rota | `backend/app/lots.py` | `register_lot_routes` → `my_lots` (`GET /api/lots/mine`, todos os lotes do dono, sem limite) |
| CAP-3 erro | `backend/app/errors.py` | `ARTWORK_NOT_ELIGIBLE`, `MESSAGES[...]` |
| registro | `backend/app/main.py` | `register_lot_routes(app)` depois de `register_catalog_routes(app)` |
| CAP-9 seed | `backend/app/seed.py` | `SEED_ADVISORY_LOCK_KEY`, `DEMO_*`, `load_demo_artwork`, `acquire_seed_lock`, `seed_demo_lot`, `run_seed`, `main` — chama `create_lot`, nunca `resolve_artwork_for_lot` |
| CAP-9 fixture | `backend/app/seed_data/demo_artwork.json` | `seed-plan.md` §1 |
| CAP-4 dinheiro (front) | `frontend/src/money.ts` | `parseReaisToCents`, `formatCents`, `MAX_CENTS` |
| CAP-4 teste (Q1) | `frontend/src/money.test.ts` | `node:test` (`test-plan.md` §8) |
| Q1 infraestrutura | `frontend/package.json` | `"test": "node --test \"src/**/*.test.ts\""`; `"typecheck": "tsc --noEmit -p tsconfig.app.json && tsc --noEmit -p tsconfig.node.json"` |
| Q1 infraestrutura | `frontend/tsconfig.app.json`, `frontend/tsconfig.node.json` | `exclude` / `include` de `src/**/*.test.ts` |
| Q1 infraestrutura | `verify.sh` | etapa "Frontend: test" (`npm test`) entre "typecheck" e "build" |
| CAP-5 horário (front) | `frontend/src/lotTime.ts` | `localInputToIso`, `formatDateTime`, `browserTimeZone` |
| CAP-10 cliente | `frontend/src/api/lots.ts` | tipos, `isLotResponse`, `createLot`, `fetchMyLots` |
| CAP-10 fluxo | `frontend/src/LotCreation.tsx`, `LotForm.tsx`, `LotReview.tsx`, `LotCreated.tsx` | etapas `frontend-lot-creation.md` §7 |
| CAP-8 tela | `frontend/src/MyLots.tsx` | §7.5 |
| CAP-10 entrada | `frontend/src/ArtworkDetailPanel.tsx`, `CatalogSearch.tsx` | `onCreateLot` + botão |
| navegação | `frontend/src/SiteHeader.tsx`, `App.tsx` | `auctioneerView`, `<nav>` |
| estilo | `frontend/src/App.css` | 3 seções novas |
| testes back-end | `backend/tests/...` | `test-plan.md` §1–§7 |

**Intocados:** `app/catalog.py`, `app/artic.py`, `app/access.py`, `app/csrf.py`,
`app/auth.py`, `app/security.py`, `app/config.py`, `app/db.py`, `app/users.py`,
`app/spa.py`, `app/infra_check.py`, migrations `0001`/`0002`, `Dockerfile`,
`.dockerignore`, `compose.yaml`, `scripts/start.sh`, `pyproject.toml`, `uv.lock`,
`package-lock.json` (nenhuma dependência nova), `eslint.config.js`, `vite.config.ts`,
`LoginForm.tsx`, `ArtworkImage.tsx`, `api/catalog.ts`, `api/auth.ts`.

## 2. Ordem sugerida (com dependências)

1. **Migration + modelo** (`0003_lots.py`, `Lot`, CHECKs de faixa) + `clean_users`/`clean_lots` + `test_lots_migration.py` + lista de tabelas em `test_database.py`. Rodar a suíte inteira aqui: prova que o ajuste do `TRUNCATE` não quebrou a 2.2.
2. **Regra pura e schemas** (`LotTerms`, `ApiDatetime`, `ArtworkSnapshot`, `resolve_schedule`) + `test_lot_rules.py`.
3. **Persistência compartilhada** (`database_now`, `create_lot`, `lot_response`). Depende de 1 e 2.
4. **Nível externo** (`ArtworkRefusal`, `resolve_artwork_for_lot`) + seus testes sem banco. Depende de 2.
5. **Erro** `artwork_not_eligible` + `test_errors.py`.
6. **Rotas** e registro em `main.py` + `test_lot_creation.py`, `test_my_lots.py`, `test_openapi.py`, `test_access_policy.py`. Depende de 3, 4 e 5.
7. **Seed** (fixture, `run_seed`, `main`) + `test_seed.py` ampliado (inclui "não passa pelo catálogo") + `test_seed_fixture.py`. Depende só de 3; pode correr em paralelo com 4–6.
8. **Front: lógica pura e teste** (`money.ts`, `money.test.ts`, scripts e `tsconfig`, etapa no `verify.sh`; `lotTime.ts`, `api/lots.ts`). Rodar `npm test` e `npm run typecheck` aqui.
9. **Front: telas** (`LotForm`, `LotReview`, `LotCreated`, `LotCreation`, `MyLots`, navegação, botão no detalhe, CSS). Depende de 6 (contrato) e 8.
10. **Docs** (§4) e `./verify.sh` completo.
11. Parar; o roteiro manual (`test-plan.md` §9) é do Joaodionizio; depois `bmad-code-review` em sessão nova.

## 3. Plano em até 8 linhas (para o `bmad-build` mostrar antes de editar)

Arquivos do §1; `lots` na `0003` com FK RESTRICT, faixa `1..2^53−1` em CHECK e demais
CHECKs; `app/lots.py` com regra pura (`now` injetado), `resolve_artwork_for_lot` (AIC, só
o `POST`) e `create_lot` (sem rede, compartilhado com o seed); `POST /api/lots` e
`GET /api/lots/mine` (`AUCTIONEER`, todos os lotes); `artwork_not_eligible`; seed com trava
consultiva e fixture em `app/seed_data/`; front com navegação, formulário → revisão →
confirmação e "Meus lotes"; `money.test.ts` por `node --test` no `verify`; testes de
`test-plan.md`; `verify`.

## 4. Documentação (na implementação)

- **Story 2.4:** P1–P9, D1–D14, Q1 e A2–A4 em primeira pessoa, com a alternativa
  descartada (o limite de 100 e a faixa só na API aparecem como versões anteriores
  revisadas); tarefas marcadas; desvios; saídas reais; status `review` (nunca `done` antes
  do code review e da conferência de coerência).
- **`sprint-status.yaml`:** `in-progress` no início do build, `review` no fim.
- **README:** seção "Lotes" (criar, revisão, "Meus lotes", o que vem da AIC e quando);
  seção do seed (lote demo, 72 h, R$ 100,00/R$ 10,00, recriado só no boot quando todos
  encerraram, trava consultiva, sem rede); `verify` com a etapa "Frontend: test";
  "Comportamentos que podem surpreender": criar lote depende da AIC (503 sem lote);
  duplo envio sem deduplicação no servidor e erro de rede com resultado incerto (P7); a
  mesma obra pode estar em vários lotes; lote de 1 µs aceito (cai na janela de
  anti-sniping); "começar agora" usa a hora do servidor; demo vencido só é substituído no
  próximo boot; valores limitados a R$ 90.071.992.547.409,91 por limite técnico, não
  comercial; "Meus lotes" lista todos os lotes, sem paginação, e as miniaturas consomem a
  cota da AIC (D1 da 2.3).
- **`docs/uso_de_ia.md`:** seção "Story 2.4" (spec, ajustes da aprovação, build, review; o
  que eu decidi; o que revisei; números só de comando).
- **`docs/ARQUITETURA.md`** (questões e histórico, nenhuma AD alterada):
  - Questão 4: "**Resolvida em parte na Story 2.4**: demo realmente aberto =
    `is_demo AND ends_at > clock_timestamp()` lido depois de `pg_advisory_xact_lock`; ordem
    migrations → seed → servidor; o catch-up da 4.4 entra antes do seed; a 3.6 acrescenta
    'não cancelado'".
  - Questão 10: "**Ferramenta de teste do front-end, em parte (Story 2.4):** `node:test`
    nativo do Node 24 para lógica pura sem DOM (`npm test`, etapa do `verify`); descartei
    Vitest com Testing Library; componentes seguem sem teste automatizado".
- **`deferred-work.md`:** `Idempotency-Key` (P7); paginação de "Meus lotes" quando houver
  volume (A2); `GET /api/lots/{lot_id}` registrada depois de `/api/lots/mine` (2.5); teste
  automatizado de componentes do front.
- **`CLAUDE.md`:** só se um resumo ficar desatualizado (candidatos: item 4 → "parcial na
  2.4"; item 10 → ferramenta de teste do front em parte); nada mais.
- **`epics.md`:** sem mudança.

Antes de `done`, a conferência de coerência da seção "Fechamento" da story, preservando
decisão → motivo → alternativa descartada → evidência/mudança de plano → decisão revisada
→ limitação/adiamento.

## 5. Riscos

| # | Risco | Mitigação |
| --- | --- | --- |
| R1 | Acessar `user` depois do `rollback()` recarrega o objeto e abre transação antes da AIC. | Guardar `user.id` antes (passo 4a); teste da fronteira (`pg_stat_activity`). |
| R2 | `AwareDatetime` aceitar número como timestamp Unix. | `BeforeValidator` com regex (D2); casos em `test_lot_rules.py`. |
| R3 | Sessão do seed em `REPEATABLE READ` faria o segundo seed não ver o demo do primeiro. | Nível padrão; teste `SHOW transaction_isolation`. |
| R4 | `clean_users` com FK novo quebrar testes da 2.2. | `TRUNCATE lots, users` no passo 1, suíte inteira rodada. |
| R5 | `/api/lots/mine` sombreada pela futura `/api/lots/{lot_id}`. | Ordem de registro documentada para a 2.5 (`deferred-work.md`). |
| R6 | Timeout depois do commit gera lote duplicado em nova tentativa. | Mensagem "confira em Meus lotes" (P7); README. |
| R7 | "Meus lotes" sem limite, com dezenas de miniaturas, estoura 60 req/min da AIC. | `loading="lazy"`; placeholder; item D1 da 2.3 em `deferred-work.md`. |
| R8 | `clock_timestamp()` volta no fuso da sessão do PostgreSQL. | `astimezone(UTC)` em `database_now` e `lot_response`; teste exige `Z`. |
| R9 | Teste de concorrência do seed pendurar. | Poll com timeout de 10 s, `join(timeout)`, rollback da conexão A no `finally`. |
| R10 | O tipo exato de erro do Pydantic para data impossível variar. | O teste fixa o tipo real observado e registra. |
| R11 | Literal da CHECK divergir de `MAX_CENTS`. | Teste lê `pg_get_constraintdef` e compara com `str(MAX_CENTS)`. |
| R12 | Alguém fazer o seed chamar a AIC no futuro. | Teste com os pontos de integração trocados por falhas e checagem da AST de `seed.py`. |
| R13 | O Node imprimir aviso de type stripping ou mudar o comportamento numa versão futura. | O aviso não falha o comando; `node:24-slim` e Node local 24.22 conferidos; se mudar, relatar em vez de afrouxar. |
