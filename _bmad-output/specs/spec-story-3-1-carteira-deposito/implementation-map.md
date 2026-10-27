# Mapa de implementação — Story 3.1

## 1. Arquivos a criar

| Arquivo | Conteúdo |
| --- | --- |
| `backend/app/money.py` | `MAX_CENTS`, `Cents` (`backend-contract.md` §2) |
| `backend/app/wallet.py` | `Wallet`, `MissingWalletError`, `DepositRefusal`, `available_cents`, `apply_deposit`, `ensure_wallets`, `read_wallet`, `lock_wallet`, `deposit`, `DepositRequest`, `WalletResponse`, `wallet_response`, `register_wallet_routes` |
| `backend/migrations/versions/0004_wallets.py` | `database-schema.md` §3 |
| `backend/tests/wallet_support.py` | `test-plan.md` §1 |
| `backend/tests/test_wallet_rules.py` | `test-plan.md` §3 |
| `backend/tests/integration/test_wallets_migration.py` | §2 |
| `backend/tests/integration/test_wallet_service.py` | §4 |
| `backend/tests/integration/test_wallet_routes.py` | §5 |
| `backend/tests/integration/test_wallet_concurrency.py` | §6 |
| `frontend/src/api/wallet.ts`, `frontend/src/api/wallet.test.ts` | `frontend-wallet.md` §4 |
| `frontend/src/walletFeedback.ts`, `frontend/src/walletFeedback.test.ts` | §5 |
| `frontend/src/WalletPage.tsx` | §6 |
| `frontend/e2e/wallet.spec.ts` | `test-plan.md` §9 |

## 2. Arquivos a modificar

| Arquivo | Mudança |
| --- | --- |
| `backend/app/lots.py` | remover `MAX_CENTS` e `Cents`; `from app.money import MAX_CENTS, Cents`; nada mais |
| `backend/app/errors.py` | `BALANCE_LIMIT_EXCEEDED` e a mensagem |
| `backend/app/main.py` | `register_wallet_routes(app)` depois de `register_lot_routes` |
| `backend/app/seed.py` | `ensure_wallets` em `run_seed` + log (`seed-plan.md`) |
| `backend/tests/conftest.py` | `clean_users` → `TRUNCATE wallets, lots, users` |
| `backend/tests/integration/test_database.py` | tabela `wallets` na lista |
| `backend/tests/integration/test_seed.py` | asserções de carteiras (subprocesso, idempotência) |
| `backend/tests/test_openapi.py` | paths e schemas novos (`test-plan.md` §7) |
| `backend/tests/test_errors.py` | entrada nova de `MESSAGES` |
| `backend/tests/test_access_policy.py` | `EXPECTED_POLICIES` |
| `frontend/src/route.ts`, `route.test.ts` | rota `wallet`, `isBidderRoute`, `isRestrictedRoute`, `safeReturnPath` |
| `frontend/src/App.tsx` | vista `wallet`, `BidderOnly`, redirecionamento e sessão expirada por `isRestrictedRoute`, título |
| `frontend/src/SiteHeader.tsx` | "Carteira" para `BIDDER`; comentário |
| `frontend/src/App.css` | seção "Carteira" (tokens existentes) |
| `frontend/e2e/support/mockApi.ts` | rotas da carteira |
| `frontend/e2e/session.spec.ts`, `touch-targets.spec.ts` | asserção escopada; caso `BIDDER` com "Carteira" |
| `README.md` | seção "Carteira"; seed com carteiras; "Comportamentos que podem surpreender" (sem histórico; nova tentativa manual após timeout pode duplicar; limite técnico do total; downgrade perde saldos) |
| `docs/uso_de_ia.md` | seção da 3.1 |
| `_bmad-output/implementation-artifacts/deferred-work.md` | risco residual da P8 (timeout depois do commit + nova tentativa manual pode duplicar; idempotência exige mecanismo próprio) |
| Story 3.1 e `sprint-status.yaml` | registro de implementação, evidências, status |

**Intocados:** `app/access.py`, `app/csrf.py`, `app/auth.py`, `app/users.py`,
`app/security.py`, `app/config.py`, `app/db.py`, `app/catalog.py`, `app/artic.py`,
`app/spa.py`, `app/infra_check.py`, migrations `0001` a `0003`, `tests/access_policy.py`,
`tests/auth_support.py`, `tests/lot_support.py`, `scripts/start.sh`, `Dockerfile`,
`compose.yaml`, `verify.sh`, `pyproject.toml`, `uv.lock`, `package.json`,
`package-lock.json`, `money.ts`, `MoneyField.tsx`, `navigation.ts`, `AppLink.tsx`,
`api/auth.ts`, telas da 2.4 e 2.5, `docs/ARQUITETURA.md`, `CLAUDE.md`.

## 3. Sequência recomendada

1. **`app/money.py`** e refatoração de `lots.py`; rodar a suíte da 2.4 (nada muda).
2. **Migration `0004` + modelo `Wallet`**; `clean_users`; `test_database.py`;
   `test_wallets_migration.py` (inclui cenário A e literal único).
3. **Regra pura e schemas** + `test_wallet_rules.py`.
4. **Serviço** (`ensure_wallets`, `read_wallet`, `lock_wallet`, `deposit`) +
   `test_wallet_service.py`.
5. **Seed** + ampliação de `test_seed.py`; conferir equivalência A = B.
6. **Rotas, `MESSAGES`, registro em `main.py`** + `test_wallet_routes.py`,
   `test_openapi.py`, `test_errors.py`, `test_access_policy.py`. Rodar a suíte inteira.
7. **Concorrência** (`test_wallet_concurrency.py`) e a mutação temporária, com o
   resultado registrado na story.
8. **Front, lógica pura**: `route.ts`, `api/wallet.ts`, `walletFeedback.ts` + testes;
   `npm test`, `npm run typecheck`.
9. **Front, telas**: `App.tsx`, `SiteHeader.tsx`, `WalletPage.tsx`, `App.css`.
10. **Playwright**: `mockApi.ts`, `wallet.spec.ts`, `session.spec.ts`,
    `touch-targets.spec.ts`; `VERIFY_E2E=1 ./verify.sh`.
11. **Documentação**: README, `docs/uso_de_ia.md`, `deferred-work.md`, story,
    `sprint-status.yaml` (`review`). Parar.

## 4. Estratégia transacional (resumo)

- Leitura: um `SELECT` sem trava, `rollback` antes da resposta.
- Depósito: uma transação curta — `SELECT ... FOR UPDATE` (relê) → regra pura →
  `UPDATE` → `commit`; recusa → `rollback` imediato; exceção → a `Session` fecha com
  rollback. Uma única carteira travada, nenhum lote, nenhuma chamada externa.
- Seed: dentro da transação existente, sob a trava consultiva, só `INSERT … ON CONFLICT
  DO NOTHING`.
- Banco: CHECKs imediatas como última barreira (faixa e `committed <= total`).

## 5. Riscos

| Risco | Mitigação |
| --- | --- |
| Lost update | `FOR UPDATE` + C1, controle negativo C6 e mutação |
| Total acima de `2^53 − 1` (quebra `formatCents`) | teto checado sob a trava + CHECK; C2/C3 |
| Releitura stale do ORM dentro da sessão | `populate_existing` em `lock_wallet` |
| Usuário sem carteira | backfill + seed genérico; runtime → 500 (CAP-9) |
| Duplo depósito por nova tentativa manual | P8; `deferred-work.md` e README |
| Header do `BIDDER` a 320 px | regra `< 30rem` existente; testes de sobreposição e alvo |
| Teste de concorrência instável | espera por `pg_locks`, sem `sleep` como prova; `join` com timeout só como rede de segurança |
| Violação de CHECK no log | `DETAIL` do PostgreSQL mostra a linha (2.2 L1); nenhum caminho previsto viola |
| Testes que mudam por contrato | lista fechada em SPEC (Constraints); nada além dela |

## 6. Critérios objetivos de conclusão

A 3.1 está pronta para review quando **todos** valem:

1. Os 13 CAPs da SPEC têm teste ou passo de roteiro que os decide, todos verdes.
2. `./verify.sh` termina com exit 0 e `VERIFY_E2E=1 ./verify.sh` também, com a saída real
   registrada na story (contagens só dessas execuções).
3. A mutação temporária do `FOR UPDATE` foi executada, falhou como esperado, foi
   revertida, e o resultado está na story.
4. `app/lots.py` não define `MAX_CENTS` nem `Cents`; `app/money.py` é a única definição.
5. Nenhum `UPDATE` em `wallets` fora de `deposit`; nenhum `INSERT` em `wallets` fora da
   `0004` e de `ensure_wallets`.
6. Nenhum arquivo da lista "Intocados" mudou, salvo justificativa registrada na story.
7. README, `docs/uso_de_ia.md` e `deferred-work.md` atualizados; story e
   `sprint-status.yaml` em `review`.
8. Nenhum ledger, nenhuma lógica de lance, nenhuma rota além das duas, nenhum item da
   3.2 em diante.
