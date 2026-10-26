# Plano de testes — Story 3.1

Nenhum número aqui é resultado: toda contagem vem do `verify` desta story. Banco:
PostgreSQL `_test` real, nunca SQLite; a guarda de rede do `conftest.py` continua ativa.

## 1. Apoio

- `tests/conftest.py`: `clean_users` → `TRUNCATE wallets, lots, users` (sem `CASCADE`,
  mesma guarda de banco `_test`); docstring atualizada. Novo `clean_wallets` só se algum
  teste precisar esvaziar só `wallets`.
- `tests/wallet_support.py` (novo):
  - `seed_users_with_wallets(factory)`: `seed_users` + `ensure_wallets` + commit;
  - `wallet_row(factory, user_id) -> tuple | None` (as três colunas por SQL);
  - `wallet_rows(factory)` (todas, ordenadas por `user_id`);
  - `set_wallet(factory, user_id, total, committed)` e `delete_wallet(factory, user_id)`
    por SQL direto (estados que a API não cria);
  - `wait_for_blocked_lock(engine, timeout=10)`: poll de
    `SELECT count(*) FROM pg_locks WHERE NOT granted` até > 0 (padrão do
    `wait_for_blocked_advisory_lock` da 2.4), senão `AssertionError`;
  - `naive_deposit(factory, user_id, amount, barrier)`: leitura sem trava, `barrier.wait()`,
    `UPDATE ... SET total = :lido + :amount`, commit — **só** para o controle negativo.
- Reuso: `build_client`, `login`, `json_headers`, `forge_token`, `seeded_id`,
  `BIDDER_EMAIL`, `OTHER_BIDDER_EMAIL`, `AUCTIONEER_EMAIL` (`auth_support.py`);
  `statement_recorder` (`lot_support.py`).

## 2. Migration e esquema — `tests/integration/test_wallets_migration.py`

| Caso | Esperado |
| --- | --- |
| Colunas | `list(columns)` = `user_id`, `total_balance_cents`, `committed_balance_cents`; nenhuma `id`, `available_balance_cents`, `created_at`, `updated_at` |
| Tipos reais | `information_schema`: `uuid`, `bigint`, `bigint`; todas `NOT NULL`; defaults dos saldos `0` |
| Nomes | `pk_wallets`, `fk_wallets_user_id_users`; CHECKs exatamente as três de `database-schema.md` §2 |
| FK | `ondelete` = `RESTRICT` no inspector; `user_id` inexistente → `IntegrityError` com o nome da FK; `DELETE FROM users` do dono → `IntegrityError` |
| 1:1 | segunda linha do mesmo `user_id` → `IntegrityError` (`pk_wallets`) |
| CHECKs (parâmetros inteiros, nunca `float`) | total `-1` → `ck_wallets_total_range`; comprometido `-1` → `ck_wallets_committed_range`; `committed = total + 1` → `ck_wallets_committed_within_total`; `committed = total` aceito; `0`/`0` aceito; total `MAX_CENTS` aceito, `MAX_CENTS + 1` recusado; comprometido `MAX_CENTS` com total `MAX_CENTS` aceito, `MAX_CENTS + 1` recusado; `UPDATE` direto que viola é recusado |
| Literal único (CAP-3) | `pg_get_constraintdef` das CHECKs de faixa de `wallets` **e** de `lots` contém `str(app.money.MAX_CENTS)`; `app.money.MAX_CENTS == 2**53 - 1` |
| Cenário A (backfill) | `clean_users`; `downgrade 0003`; inserir 3 usuários por SQL (`BIDDER`, `BIDDER`, `AUCTIONEER`); `upgrade head` → 3 carteiras `0`/`0`, uma por usuário; linhas de `users` idênticas |
| Downgrade | `downgrade 0003` remove `wallets` e mantém `users` e `lots`; `upgrade head` recria (fixture `back_at_head`, como 2.2/2.4) |
| Lista de tabelas | `test_database.py`: `["alembic_version", "lots", "users", "wallets"]` |

## 3. Regra pura e contrato monetário — `tests/test_wallet_rules.py` (sem banco)

| Caso | Esperado |
| --- | --- |
| `available_cents` | `(0,0)=0`, `(1000,0)=1000`, `(1000,400)=600`, `(MAX,MAX)=0` |
| `apply_deposit` | `(0,1)=1`; `(100,50)=150`; `(MAX−10, 10)=MAX`; `(MAX−10, 11)` → `BALANCE_LIMIT_EXCEEDED`; `(MAX, 1)` → recusa |
| `DepositRequest` | `1` e `MAX` ok; `0`/`-1` → `greater_than`; `MAX+1` → `less_than_equal`; `100.0`, `100.5`, `"100"`, `True`, `1e2` → `int_type`; extra → `extra_forbidden` |
| `app.money` | `MAX_CENTS == 2**53 − 1`; `app.lots.MAX_CENTS is app.money.MAX_CENTS`; `app.lots.Cents is app.money.Cents`; `app/lots.py` não contém atribuição `MAX_CENTS =` nem `Cents =` (checagem por AST) |
| Fronteira de import | AST de `app/wallet.py` não importa `app.lots`, `app.catalog`, `app.artic`, `app.main`, `httpx` |

## 4. Serviço e seed — `tests/integration/test_wallet_service.py` e `test_seed.py` (ampliado)

| Caso | Esperado |
| --- | --- |
| `ensure_wallets` | 3 usuários sem carteira → devolve 3; segunda chamada → 0; usuário extra sem carteira → 1; carteira com `set_wallet(…, 500, 200)` intacta depois |
| Seed banco limpo | `run_seed` → `(3, True)` (inalterado); 3 carteiras `0`/`0`; nenhum log de carteira antes do commit (desvio de D10, `seed-plan.md` §1) |
| Seed idempotente | segunda execução → `(0, False)`; `wallet_rows` idênticas; `statement_recorder` sem `UPDATE`/`DELETE` em `wallets` |
| Equivalência A = B | `wallet_rows` do cenário A (§2) e do banco limpo + seed, para os mesmos três IDs, iguais |
| Seed não altera | carteira com saldo alterado por SQL, `run_seed` → mesma linha |
| Subprocesso (2.2/2.4) | `test_module_runs_alone_with_only_database_url` ganha a asserção de 3 carteiras zeradas e da **ausência** de log de carteira (desvio de D10); continua sem `APP_ORIGIN`, `JWT_SECRET`, `app.main` |
| Lote demo | testes da 2.4 verdes; demo criado e antigos intactos |
| Rollback | `deposit` seguido de exceção forçada antes do commit (patch de `Session.commit`) → linha igual à de antes |
| Carteira ausente | `read_wallet`/`lock_wallet` de usuário sem carteira → `MissingWalletError`; nenhuma linha criada |

## 5. HTTP — `tests/integration/test_wallet_routes.py`

Cliente: `build_client(..., session_factory=…)`; `seed_users_with_wallets`; `clean_users`.

| Grupo | Casos |
| --- | --- |
| Leitura | `BIDDER` → 200, chaves exatas, `0`/`0`/`0`, `no-store`; com `set_wallet(…, 1000, 400)` → `available 600`; o `statement_recorder` só vê `SELECT` e nenhum `FOR UPDATE` |
| Leitura: acesso | sem cookie, cookie adulterado, expirado → 401 `no-store`; `AUCTIONEER` → 403 |
| Depósito | `50000` → 200 `{50000, 0, 50000}`, `no-store`; segundo `25000` → `75000`; linha = resposta; comprometido inalterado; carteira do `bidder2` inalterada |
| Dono da sessão | corpo com `user_id` do `bidder2` → 422 `extra_forbidden`, nada muda |
| `validation_error` | cada valor de `backend-contract.md` §5 → 422 `validation_error` com `details` `[{"loc": ["body", "amount_cents"], "type": <real>}]` (JSON malformado com o `loc` real), linha inalterada |
| `balance_limit_exceeded` | `set_wallet(MAX − 10)`; `11` → 422, corpo exatamente `{"status": 422, "code": "balance_limit_exceeded", "message": "<catálogo>"}`, `no-store`, linha inalterada; `10` → 200 com total `MAX` |
| Papéis | anônimo → 401; `AUCTIONEER` → 403, nenhuma carteira muda |
| Proteção 2.1 | `Origin` estrangeiro, sem `Origin`/`Referer`, `text/plain` → 403 `csrf_origin_mismatch` / `csrf_origin_missing` / 415; `wallet_rows` inalteradas |
| Métodos | `GET`/`PUT`/`DELETE /api/wallet/deposit` e `POST`/`PUT`/`DELETE /api/wallet` com origem e JSON válidos → 405 |
| Carteira ausente | `delete_wallet` do `bidder1`; `GET` e `POST` com `raise_server_exceptions=False` → 500 `{status, code: "internal_error", message}`; nenhuma carteira criada |

## 6. Concorrência — `tests/integration/test_wallet_concurrency.py` (PostgreSQL real)

| # | Caso | Esperado |
| --- | --- | --- |
| C1 | **Determinístico.** Sessão A: `deposit(A, uid, 300)` (trava e atualiza), sem commit. Thread B: `deposit(B, uid, 500)` + commit em sessão própria. `wait_for_blocked_lock`. A faz commit; `B.join(timeout=10)` | B terminou sem erro; total = inicial + 800; comprometido 0 |
| C2 | **Perto do teto, recusa.** `set_wallet(MAX − 10)`; A deposita 6 sem commit; B (6) bloqueia; A commita | B devolve `BALANCE_LIMIT_EXCEEDED` (decidido sobre `MAX − 4`); total final `MAX − 4` |
| C3 | **Perto do teto, aceite.** Mesmo arranjo, B = 4 | B aceito; total final `MAX` |
| C4 | **HTTP, perto do teto.** Mesmo arranjo de C2 com B por `POST` numa thread (cliente próprio logado como `bidder1`) | B recebe 422 `balance_limit_exceeded`; total `MAX − 4` |
| C5 | **Corrida livre.** Duas threads com `threading.Barrier(2)` fazendo `POST` (clientes próprios), 5 repetições | sempre 200 nos dois e total = soma |
| C6 | **Controle negativo (no teste).** Duas threads com `naive_deposit` e `Barrier(2)` entre leitura e escrita | total = inicial + um só valor: o arranjo de C5/C1 detectaria a perda |
| C7 | **Leitura não espera.** A segura a trava de um depósito; `GET /api/wallet` noutra thread | responde 200 com o valor confirmado (MVCC), sem esperar a trava |

**Mutação temporária (registrar na story, não versionar):** tirar `with_for_update()` de
`lock_wallet` → B lê o total antigo sem esperar, calcula em Python e só bloqueia no
`UPDATE`; quando A confirma, B sobrescreve: C1 falha porque o total final perde os 300 de
A, e C2 falha porque B é aceito sobre o total antigo (`MAX − 4`, perdendo o depósito de
A, em vez da recusa). Restaurar e rodar de novo.

## 7. Contrato e regressão (sem banco)

- `test_openapi.py`: lista completa de `paths` ganha `/api/wallet` e `/api/wallet/deposit`
  no fim; o teste de ordem passa a conferir `[LOTS, MINE, DETAIL]` imediatamente antes de
  `[WALLET, DEPOSIT]`; `GET /api/wallet` 200 → `WalletResponse`, 401/403 → `ErrorResponse`;
  `POST /api/wallet/deposit` 200 → `WalletResponse`, 401/403/422 → `ErrorResponse`, corpo
  `DepositRequest`; `sorted(properties)` exatos dos dois; `set(paths[WALLET]) == {"get"}`,
  `set(paths[DEPOSIT]) == {"post"}`; `HTTPValidationError` ausente.
- `test_errors.py`: `MESSAGES ==` ganha `balance_limit_exceeded` com o texto exato.
- `test_access_policy.py`: `EXPECTED_POLICIES` ganha `("/api/wallet", "GET", "http")` e
  `("/api/wallet/deposit", "POST", "http")` como `BIDDER`; verificador e meta-testes
  inalterados.
- `create_app()` sem banco e sem rede; `/health` 200; suítes da 2.1 a 2.5 verdes.

## 8. Front — `node --test`

| Arquivo | Casos |
| --- | --- |
| `src/route.test.ts` | `/bidder/wallet` → `wallet`; `/bidder/wallet/`, `/bidder`, `/bidder/x` → not-found; ida e volta; `isBidderRoute`; `isRestrictedRoute` para as três rotas restritas; `safeReturnPath('/bidder/wallet', 'BIDDER') === '/bidder/wallet'`; `(…, 'AUCTIONEER') === '/'`; casos da 2.5 intactos |
| `src/api/wallet.test.ts` | `isWalletResponse` aceita `{0,0,0}`, `{MAX,0,MAX}`; recusa `1.5`, `-1`, `'100'`, `MAX+1`, chave ausente, `committed > total`, `available` incoerente |
| `src/walletFeedback.test.ts` | `depositSuccessText(125000)` = "Depósito de R$ 1.250,00 confirmado."; `depositFailureNotice('ambiguous') === 'reread'`; texto de cada outra falha; `rereadNotice` ok e falha (nenhum afirma sucesso) |

## 9. Front — Playwright (opt-in, API simulada; `e2e/wallet.spec.ts`)

`mockApi.ts` ganha: `wallet?: {total, committed}` por sessão `BIDDER`;
`GET /api/wallet` (401/403/200 conforme a sessão; `reread: 'ok' | 'fail'` para a segunda
leitura); `POST /api/wallet/deposit` com `deposit: 'ok' | 'limit' | 'validation' |
'server_error' | 'network'` e `depositDelayMs` opcional; `ok` soma ao estado.

| Caso | Esperado |
| --- | --- |
| Header `BIDDER` | link "Carteira" visível; em `/bidder/wallet`, `aria-current="page"` |
| Header anônimo/`AUCTIONEER` | nenhum link "Carteira" |
| `AUCTIONEER` em `/bidder/wallet` | `h1` "Área do licitante"; `api.count('GET /api/wallet') === 0` |
| Anônimo | `/bidder/wallet` → `/login`; entrar como `BIDDER` → `/bidder/wallet` com a carteira; entrar como `AUCTIONEER` → `/` |
| Deep-link e refresh | `/bidder/wallet` direto e Cmd+R mantêm a carteira |
| Leitura | os três rótulos e valores formatados; disponível antes do total no DOM |
| Depósito ok | "1.250,00" → status "Depósito de R$ 1.250,00 confirmado." e os saldos novos; campo limpo |
| Duplo envio | `depositDelayMs` alto, dois cliques e Enter → `api.count('POST /api/wallet/deposit') === 1`; botão `disabled` durante o envio |
| Recusas | `limit` → mensagem do teto no campo; `validation` → mensagem; saldos inalterados |
| Ambíguo + releitura ok | `server_error` ou `network` → exatamente um `GET` a mais, saldo da releitura, texto "Não foi possível confirmar o depósito…"; nenhum segundo `POST` |
| Ambíguo + releitura falha | texto "Não foi possível confirmar se o depósito foi feito…"; nenhum segundo `POST`; nenhum texto de sucesso |
| Layout | 1440, 375, 320 px: sem rolagem horizontal na carteira com `MAX_CENTS`; header do `BIDDER` sem sobreposição entre marca, Vitrine, Carteira e conta (padrão de `brand.spec.ts`); alvo de "Carteira" ~44 px (`touch-targets.spec.ts` ganha o caso `BIDDER`) |
| `session.spec.ts` | a asserção `getByText(/carteira/i)` passa a valer só em `page.locator('main')` na página do lote; mais a asserção positiva do link "Carteira" no header |

O Playwright não substitui os testes transacionais da §6.

## 10. Roteiro manual (meu, antes do review)

1. Banco de desenvolvimento em `head` + seed; `bidder1`: "Carteira" no header, `R$ 0,00`.
2. Depositar `1.250,00`, `0,50`, `10`; valores inválidos (`0`, `abc`, `10.5`, `1,234`).
3. Duplo clique rápido em "Depositar" → um `POST` na aba Rede.
4. Uvicorn parado durante o depósito → mensagem de resultado incerto, sem novo `POST`.
5. `auctioneer`: sem "Carteira"; `/bidder/wallet` → "Área do licitante", sem `GET /api/wallet` na aba Rede.
6. Anônimo em `/bidder/wallet` → login `bidder1` → volta à carteira.
7. 375 e 320 px: header e carteira sem rolagem horizontal; teclado: Tab até "Depositar", Enter envia, foco visível.

Registro só o que eu observar.
