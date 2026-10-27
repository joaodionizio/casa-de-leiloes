# Decisões — Story 3.1

## 1. Decisões do Joaodionizio (P1 a P8, fechadas em 25/10/2026; não reabrir)

Registro completo, com as alternativas descartadas, em
`_bmad-output/implementation-artifacts/3-1-carteira-e-depósito-simulado.md`
("Decisões fechadas").

| # | Decisão | Descartado |
| --- | --- | --- |
| P1 | `wallets.user_id` PK e FK para `users.id`, `ON DELETE RESTRICT`; sem `wallets.id`; saldos `BIGINT NOT NULL DEFAULT 0`; **sem `created_at`/`updated_at`**: a carteira é o estado agregado atual, e timestamps não substituem histórico nem auditoria | `id` próprio + `UNIQUE`; saldos em `users`; `CASCADE`; timestamps |
| P2 | Backfill na `0004`; o seed garante carteira para **todo** usuário sem carteira, depois de criar os usuários, só `INSERT`; banco existente e limpo terminam iguais; carteira ausente em runtime = 500 genérico + log, sem criar em `GET`/`POST` | só seed; trigger; só os três IDs fixos; criar na leitura ou no depósito |
| P3 | `app/money.py` fonte única de `MAX_CENTS`; `lots.py` reutiliza; teto no `amount_cents` e no total resultante; literal nas migrations, testes provam igualdade; `amount_cents` fora da faixa → 422 `validation_error`; total excedido → 422 `balance_limit_exceeded` com mensagem no catálogo; CHECK de teto no total e no comprometido | importar de `app.lots`; constante duplicada; teto comercial; `details.type`; 409 |
| P4 | `SELECT ... FOR UPDATE` → relê sob a trava → teto → `UPDATE` → commit/rollback; testes determinísticos com duas sessões, perto do teto, controle negativo/mutação | `UPDATE` com teto no `WHERE`; confiar na CHECK; ler fora da trava |
| P5 | `GET /api/wallet` e `POST /api/wallet/deposit`, `BIDDER`; POST 200 com o snapshot; três valores, `available` calculado; `no-store`, envelope, CSRF | `/deposits`; `PATCH`; 201; `GET` `AUTHENTICATED` |
| P6 | Saldo inicial zero para todos | pré-carregar todos; só o `bidder1` |
| P7 | `/bidder/wallet`; "Carteira" só no header do `BIDDER`; `AUCTIONEER` em `/bidder/wallet` → "Área do licitante" sem `GET /api/wallet`; anônimo → `/login` com `returnTo`; depois do login só `BIDDER` volta, `AUCTIONEER` → vitrine; `session.spec.ts` atualizado por contrato; header a 375/320 px obrigatório | `/wallet`; React Router; chamar a API para o `AUCTIONEER` |
| P8 | Sem `Idempotency-Key`, ledger, tabela nem retry; botão bloqueado durante o `POST`; sucesso pela resposta; erro conhecido mostrado; erro ambíguo → uma releitura `GET`; releitura falhando não afirma o resultado nem repete o `POST`; `deferred-work.md` registra o risco residual | idempotência real; retry automático |

**Ajustes derivados, decididos:** `clean_users` → `TRUNCATE wallets, lots, users`
(sem `CASCADE`); sem ledger; sem lance; `committed_balance_cents` sempre 0 nesta story;
dívidas administrativas fora; nenhum número inventado.

## 2. Detalhamento técnico desta spec (D1 a D16)

Resolvidos na spec, dentro das decisões acima e das diretrizes do Joaodionizio de
25/10/2026 (mensagem curta e sem `details`; `Cents` só se for contrato reutilizável;
preferir log a mudar o retorno de `run_seed`; nomes pelos padrões existentes).

| # | Decisão | Por quê | Descartado |
| --- | --- | --- | --- |
| D1 | Módulo único `app/wallet.py`: modelo, schemas, regra pura, serviço e rotas (como `lots.py`). Importa `app.money`, `app.access`, `app.db`, `app.errors`, `app.users`; **nunca** `app.lots`, `app.catalog` nem `app.main` | o seed o importa sem rede nem `APP_ORIGIN`; a carteira não depende de lotes | pacote `app/wallet/`; serviço no `seed.py` |
| D2 | `app/money.py` guarda `MAX_CENTS` **e** `Cents = Annotated[StrictInt, Field(gt=0, le=MAX_CENTS)]`. `lots.py` importa os dois (os nomes `app.lots.MAX_CENTS` e `app.lots.Cents` continuam importáveis) | `Cents` não depende de lotes: serve a lance inicial, incremento, depósito e ao lance da 3.4; deixá-lo em `lots.py` obrigaria a carteira a importar lotes | mover só a constante (duas definições do mesmo tipo) |
| D3 | `0004_wallets.py` com `create_table`, backfill por `op.execute("INSERT INTO wallets (user_id) SELECT id FROM users")` e `downgrade` = `drop_table`. CHECKs `ck_wallets_total_range`, `ck_wallets_committed_range`, `ck_wallets_committed_within_total` | padrão `op.f(...)` e `_range` da `0003` | backfill com dados do seed; trigger |
| D4 | Regra pura: `available_cents(total, committed) -> int` e `apply_deposit(total, amount) -> int | DepositRefusal` (`DepositRefusal.BALANCE_LIMIT_EXCEEDED`) | testável sem banco; a 3.4 reaproveita o cálculo do disponível | regra dentro da rota |
| D5 | Serviço: `ensure_wallets(session) -> int`, `read_wallet(session, user_id)`, `lock_wallet(session, user_id)` (`with_for_update()` + `populate_existing`), `deposit(session, user_id, amount) -> Wallet | DepositRefusal`; nenhum faz commit | a rota decide commit/rollback (como `create_lot`); `populate_existing` garante a releitura sob a trava | `UPDATE` direto sem objeto |
| D6 | Carteira ausente: `read_wallet`/`lock_wallet` levantam `MissingWalletError`; a rota não captura; o handler global responde 500 `internal_error` e o uvicorn registra o traceback | um caminho só de 500 genérico (2.1, D5); a `Session` fecha com rollback | `error_response(500)` montado à mão; 404; criar a carteira |
| D7 | Fluxo do `POST` em uma transação curta (`backend-contract.md` §4); recusa por teto: `session.rollback()` e 422 com `NO_STORE` | libera a trava antes de responder | segurar a trava até o fim da requisição |
| D8 | `balance_limit_exceeded`: "O depósito ultrapassaria o limite de saldo da carteira." 422 **sem `details`** | curta, explica sem jargão; precedente `artwork_not_eligible` | citar o valor do limite; `details` |
| D9 | `register_wallet_routes(app)` depois de `register_lot_routes` e antes de `register_infra_check_routes`; `GET` antes do `POST` | ordem cronológica das stories; o OpenAPI termina nas rotas da carteira | registrar antes dos lotes para preservar `paths[-3:]` (esconderia a mudança de contrato) |
| D10 | `run_seed` chama `ensure_wallets` depois de `seed_users` e antes de `database_now`; retorno `(users, created)` inalterado; `main()` mantém a sua linha. *(Desvio na implementação: a spec previa `run_seed` logar `"seed: %d wallet(s) inserted"`; tirei o log porque ele sairia antes do commit. Ver `seed-plan.md` §1.)* | as asserções `(3, True)`/`(0, False)` e o subprocesso da 2.2/2.4 ficam intactos; o log só afirma o que o commit confirmou | mudar a tupla; `NamedTuple`; logar a contagem antes do commit |
| D11 | Testes: `tests/wallet_support.py` (`seed_users_with_wallets`, `wallet_row`, `set_wallet`, `delete_wallet`, `wait_for_blocked_lock`, `naive_deposit`); `seed_demo_users` da 2.2 intocado | os testes da 2.2/2.4 não mudam | mudar `seed_demo_users` |
| D12 | Concorrência determinística com o serviço real nas duas sessões; perto do teto com `MAX_CENTS − 10`; controle negativo no próprio teste; mutação temporária registrada na story | prova sem sorte e prova que o teste detecta a ausência da trava | `sleep`; só corrida livre |
| D13 | Front: `{kind: 'wallet'}` em `/bidder/wallet`, `isBidderRoute`, `isRestrictedRoute`; `safeReturnPath` recusa a carteira para quem não é `BIDDER`; vista `BidderOnly` ("Área do licitante") sem montar `WalletPage`; `documentTitle('Carteira')` | espelha D9 da 2.5; "sem chamar a API" vira estrutural | checar o papel dentro de `WalletPage` |
| D14 | `api/wallet.ts` com `fetchWallet` e `depositToWallet` e resultados tipados; `src/walletFeedback.ts` puro com os textos e a decisão pós-depósito | testável por `node --test`; mensagens pelo `code`, nunca pelo `message` | lógica de feedback no componente |
| D15 | `WalletPage`: disponível em destaque, total e comprometido como apoio (`dl`); `MoneyField` "Valor do depósito"; botão "Depositar"; sem checagem preventiva do teto do total no front | o servidor decide o teto com a linha travada; menos lógica duplicada | prever o teto no front |
| D16 | `mockApi.ts` ganha estado de carteira e modos de depósito/releitura com atraso opcional; spec novo `e2e/wallet.spec.ts`; `session.spec.ts` passa a conferir `/carteira/i` só no `main` e "Carteira" no header | API simulada como na 2.5 | testar pela pilha real |

## 3. Incompatibilidades reais com o código existente e adaptação mínima

| Decisão | Código hoje | Adaptação |
| --- | --- | --- |
| P2 (todo usuário com carteira) | `clean_users` faz `TRUNCATE lots, users` sem `CASCADE`: com a FK de `wallets` ele falha | `TRUNCATE wallets, lots, users` (decidido) |
| P3 (fonte única) | `MAX_CENTS` e `Cents` definidos em `app/lots.py`; `test_lots_migration.py` importa `MAX_CENTS` de `app.lots` | `lots.py` importa de `app.money`; o import do teste continua válido; o teste novo compara as CHECKs com `app.money.MAX_CENTS` |
| P3 (código próprio) | `test_errors.py` fixa `MESSAGES` por igualdade | acrescentar a entrada exata |
| P5 (rotas novas) | `test_openapi.py` fixa a lista completa de `paths` e `paths[-3:] == [LOTS, MINE, DETAIL]` | lista ganha `/api/wallet`, `/api/wallet/deposit` no fim; o teste de ordem passa a conferir lotes antes da carteira |
| P7 (header) | `session.spec.ts` afirma zero `/carteira/i` na página do `BIDDER` | escopo no `main` + asserção positiva do link no header |
| P7 (`returnTo=/bidder/wallet`) | `returnTo` vive em `history.state` da entrada `/login`, nunca na query (2.5 D8) | o valor `/bidder/wallet` vai no `state`, como nas áreas do leiloeiro; nada muda na URL |
| P2 (seed nos testes HTTP) | `seed_demo_users` só cria usuários | os testes da carteira usam `seed_users_with_wallets` |

Nenhuma é bloqueante.
