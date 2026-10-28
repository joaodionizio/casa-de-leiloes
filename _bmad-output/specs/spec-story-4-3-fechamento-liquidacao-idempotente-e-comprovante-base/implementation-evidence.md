# Evidência de implementação da Story 4.3 — 27/10/2026

## Fechamento formal aprovado

Story e sprint: **done**; SPEC: **done**; Epic 4: **in-progress**. Review
independente aprovado, sem HIGH, MEDIUM ou defeito funcional de produção; os
LOWs F43-01 e F43-02 foram resolvidos por cobertura específica. Validação final
registrada: **83 testes da Story 4.3**, **2166 backend**, **175 frontend** e
`./verify.sh` **exit 0**. Produção permaneceu inalterada após o review. As
referências abaixo a review ou aceite pendentes descrevem estados históricos.

## Ajuste posterior dos LOWs de cobertura

F43-01 cria sold válido com ALICE, altera apenas o vencedor persistido para BOB
existente e verifica conflito `settlement_mismatch`, SQL sem escrita e snapshot
completo inalterado. F43-02 cria unsold válido, altera apenas `ends_at` para uma
hora após o settlement e verifica o mesmo conflito e ausência de escrita no
retry e no cancelamento. A Session do cancelamento é nova e revertida. O
usuário confirmou essa interpretação do cenário do review, pois settlement de
lote previamente cancelado não é uma transição válida.

Os dois testes isolados passaram: **2 passed, 1 warning in 0.41s**. A suíte
PG01–35 com os novos casos passou isoladamente: **83 passed, 1 warning in
12.05s**. Mutações focais separadas em memória foram detectadas: retirar a
comparação do vencedor produziu `already_settled`; retirar a guarda terminal
do cancelamento produziu `CancelledLot`. Ambos os testes falharam como esperado.
Não houve alteração de código de produção; story permanece em review.

`./verify.sh` terminou com exit 0 e `verify.sh: todas as etapas passaram.`:
backend **2166 passed, 1 warning in 117.98s**, frontend **175 passed**; Ruff,
format, lint, typecheck, build frontend e Docker aprovados. Playwright não foi
executado. Uma primeira execução do verify foi interrompida para evitar uso
concorrente do banco pela suíte da story; esta foi repetida isoladamente antes
do verify final. O warning é a depreciação Starlette/httpx já conhecida.

## Escopo entregue

Implementei somente o comando interno `settle_lot`, o preparo transacional
`prepare_settlement`, modelos `LotSettlement`/`Receipt`, DTOs imutáveis e readers
por `lot_id`. Criei a migration `0007_lot_settlement.py` sobre `0006`, com PKs UUID,
unicidade por lote, receipt único por settlement, FKs compostas para o lance e
para o settlement do mesmo lote, além de CHECKs locais. Não alterei `bids` ou
canonical bid v1. Não executei Git nem fiz deploy.

Decidi manter a contabilidade do Epic 3: superados já foram liberados. Para F,
vencedor `(T,C,A)` vira `(T−F,C−F,A)` e leiloeiro `(T+F,C,A+F)`, com soma dos
totais conservada. Atualizo T/C do vencedor juntos, respeitando CHECK imediata.
Preservo outras reservas e o teto `9007199254740991`. Teto/reserva/invariante
inválidos falham de forma tipada e revertem toda a transação. Carteira ausente
permanece `MissingWalletError`, sem criação tardia.

A sequência é lot lock com releitura → clock_timestamp → settlement/receipt →
prazo ou revalidação → gate integral → carteiras ordenadas por user_id →
transferência → settlement → receipt só sold → commit único → retorno.
`transitioned=true` só é construído após commit confirmado. Retry íntegro não
trava carteiras nem escreve; inconsistente retorna `IntegrityConflict` sem reparo.
Os readers usam uma projeção em um statement, sem autoflush de alterações do
chamador, e detectam incoerência estrutural sem se apresentarem como auditoria.

Protegi terminais persistidos contra novo lance/cancelamento, inclusive com
`ends_at` adulterado. Não criei rota, scheduler/catch-up/gatilho, evento/publicação
WS, painel, link, auditoria pública nem alteração de UI/phase/máquina 4.2.
Story 4.4 não foi iniciada; code review não executado, por instrução humana.

## Testes direcionados PG01–35

Comando executado no backend, com defaults locais fictícios do verify e guardas
externas contra dotenv: `uv run pytest tests/integration/test_lot_settlement.py
tests/integration/test_lot_settlement_concurrency.py --junitxml=.../pg01-35.xml`.
Resultado consolidado após restauração das mutações: **81 passed, 1 warning in
11.82s**, exit 0. Todos os PG01–35 abaixo têm casos executados; parametrizações
representam variantes adicionais, não 35 comandos distintos.

PostgreSQL real com migrations reais, banco dedicado `_test`. Concorrência usa
conexões/sessions independentes, barreiras e observador que comprova PID B
bloqueado especificamente por PID A via `pg_blocking_pids`. Inclui ambas as
ordens bid×close, dois closers sold/unsold com commit/rollback de A, dois lotes
compartilhando leiloeiro/reservas e teto, depósito concorrente e cancelamento.
PG05/35 espera o fim original passar sob lock e prova E+2min, depois E+4min.

PG22 injeta constraint trigger diferida restrita ao teste: PostgreSQL aborta o
COMMIT real, snapshot completo permanece anterior. PG34 delega ao COMMIT real e
só então lança perda sintética de confirmação: outra conexão prova resultado
completo e retry retorna `already_settled`, sem repetir a transferência. Falhas
intermediárias são injeções sintéticas antes de statements reais; não alego
queda física de rede como prova. Constraints temporariamente suspensas em PG33
e fixtures de adulteração são restauradas em finally, só no banco de teste.

| PG | Testes executados (nomes dos casos) | Resultado |
| --- | --- | --- |
| PG01 | `test_lot_settlement.py::test_pg01_25_28_sold_consumes_reserved_funds_once` | passou |
| PG02 | `test_lot_settlement.py::test_pg02_27_unsold_has_authoritative_record_without_receipt` | passou |
| PG03 | `test_lot_settlement.py::test_pg03_not_due_locks_then_reads_clock_without_writes`<br>`test_lot_settlement.py::test_u01_pg03_exact_end_is_due_under_real_lock` | passou |
| PG04 | `test_lot_settlement_concurrency.py::test_pg04_preloaded_lot_is_refreshed_after_lock_wait` | passou |
| PG05 | `test_lot_settlement_concurrency.py::test_pg05_pg35_bid_first_cumulative_extension_blocks_closer` | passou |
| PG06 | `test_lot_settlement_concurrency.py::test_pg06_closer_first_prevents_bid_without_reopening` | passou |
| PG07 | `test_lot_settlement_concurrency.py::test_pg07_two_closers_serialize_and_only_one_transfer` | passou |
| PG08 | `test_lot_settlement.py::test_pg08_retry_preserves_originals_and_never_touches_wallets` | passou |
| PG09 | `test_lot_settlement.py::test_pg09_26_other_reservations_and_loser_remain_intact` | passou |
| PG10 | `test_lot_settlement.py::test_pg10_30_financial_boundaries_are_atomic` | passou |
| PG11 | `test_lot_settlement.py::test_pg11_failure_at_each_stage_rolls_back_all_entities` | passou |
| PG12 | `test_lot_settlement.py::test_pg12_schema_keys_types_and_foreign_keys`<br>`test_lot_settlement.py::test_pg12_real_constraints_reject_invalid_rows` | passou |
| PG13 | `test_lot_settlement.py::test_pg13_tampering_is_rejected_before_effects`<br>`test_lot_settlement.py::test_pg13_insertion_removal_truncation_rehash_and_operational_binding` | passou |
| PG14 | `test_lot_settlement.py::test_pg14_legacy_or_wrong_lot_anchor_never_repaired` | passou |
| PG15 | `test_lot_settlement.py::test_pg15_full_history_beyond_recent_window` | passou |
| PG16 | `test_lot_settlement.py::test_pg16_29_receipt_whitelist_schema_dto_and_logs` | passou |
| PG17 | `test_lot_settlement_concurrency.py::test_pg17_existing_http_reads_never_settle_pending_expired_lot` | passou |
| PG18 | `test_lot_settlement_concurrency.py::test_pg18_expired_handshake_reconnect_and_heartbeat_remain_pure` | passou |
| PG19 | `test_lot_settlement_concurrency.py::test_pg19_deposit_and_close_use_confirmed_wallet_balance`<br>`test_lot_settlement_concurrency.py::test_pg19_two_lots_serialize_shared_seller_preserving_other_reserves` | passou |
| PG20 | `test_lot_settlement_concurrency.py::test_pg20_command_success_is_not_visible_before_real_commit` | passou |
| PG21 | `test_lot_settlement_concurrency.py::test_pg21_cancel_first_prevents_unsold_and_close_first_prevents_cancel` | passou |
| PG22 | `test_lot_settlement.py::test_pg22_real_postgresql_commit_abort_leaves_nothing` | passou |
| PG23 | `test_lot_settlement.py::test_pg23_31_inconsistent_retry_is_conflict_without_repair` | passou |
| PG24 | `test_lot_settlement.py::test_pg24_terminal_future_end_never_reopens` | passou |
| PG25 | `test_lot_settlement.py::test_pg01_25_28_sold_consumes_reserved_funds_once` | passou |
| PG26 | `test_lot_settlement.py::test_pg09_26_other_reservations_and_loser_remain_intact` | passou |
| PG27 | `test_lot_settlement.py::test_pg02_27_unsold_has_authoritative_record_without_receipt` | passou |
| PG28 | `test_lot_settlement.py::test_pg01_25_28_sold_consumes_reserved_funds_once` | passou |
| PG29 | `test_lot_settlement.py::test_pg16_29_receipt_whitelist_schema_dto_and_logs` | passou |
| PG30 | `test_lot_settlement.py::test_pg10_30_financial_boundaries_are_atomic` | passou |
| PG31 | `test_lot_settlement.py::test_pg23_31_inconsistent_retry_is_conflict_without_repair` | passou |
| PG32 | `test_lot_settlement.py::test_pg32_sold_missing_receipt_is_never_recreated` | passou |
| PG33 | `test_lot_settlement.py::test_pg33_unsold_intrusive_receipt_is_not_removed` | passou |
| PG34 | `test_lot_settlement.py::test_pg34_commit_happens_before_lost_confirmation_and_retry` | passou |
| PG35 | `test_lot_settlement_concurrency.py::test_pg05_pg35_bid_first_cumulative_extension_blocks_closer` | passou |

## Mutações efetivamente executadas

Executei uma mutação por vez no serviço e restaurei o conteúdo original em
`finally`, conferindo igualdade byte a byte. Os cinco mutantes falharam por
comportamento em testes coletados/executados, sem erro de sintaxe ou coleta.

| Mutante | Propriedade violada | Resultado real |
| --- | --- | --- |
| M1-extra-winner-debit | Segundo débito de F no total do vencedor/disponível | exit 1; 1 failed, 80 deselected, 1 warning in 0.27s |
| M2-prelock-ends-at | Usar ends_at lido antes do lock | exit 1; 1 failed, 80 deselected, 1 warning in 2.25s |
| M3-repeat-transfer | Transferir novamente no retry | exit 1; 1 failed, 80 deselected, 1 warning in 0.44s |
| M4-unsold-receipt | Tentar persistir receipt em unsold | exit 1; 1 failed, 80 deselected, 1 warning in 0.39s |
| M5-ignore-integrity | Ignorar autenticação da cadeia | exit 1; 5 failed, 76 deselected, 1 warning in 0.75s |

O mutante de unsold tenta inserir campos nulos no receipt; as constraints
rejeitam a escrita e o caso positivo exige unsold confirmado, detectando a
regressão. O mutante de retry injeta uma transferência e commit indevidos; o
oráculo exige zero escrita e saldos/IDs originais. Nenhuma mutação ficou no código.

## Ambiente e limites de evidência

O sandbox bloqueou o primeiro acesso ao Docker. PostgreSQL/testes/gates foram
executados com a permissão de acesso local concedida pelo ambiente e cache uv
em `/private/tmp`. Nenhum agente abriu arquivos `.env*` diretamente. A primeira
rodada exploratória do subagente começou sem guardas contra leitura implícita
de dotenv; não certifico ausência de leitura implícita nessa rodada. Rodadas
posteriores, mutações e validação final usam `UV_NO_ENV_FILE=1`,
`COMPOSE_DISABLE_ENV_FILE=1`, `sitecustomize.py` externo que desativa dotenv no
pydantic-settings e, nos verifies, guarda Node externa contra leitura de `.env*`.
Não alterei configuração do produto ou verify para isso.

Primeiras falhas dos testes novos foram de harness: fixture WS com forma
incorreta do frame e oráculo que rejeitava uma exceção esperada no PG19. Corrigi
as fixtures/oráculos mantendo o contrato; não afrouxei regra de produto.
O warning de Starlette/httpx é herdado. Review/aceite humanos e deploy ficam
pendentes; a 4.3 não integra resultado ao protocolo público.

Os logs reais, JUnit, script de mutações, smoke e baseline/diff locais estão em
`_bmad/.runtime/bmad-build/SPEC-story-4-3-fechamento-liquidacao-idempotente-e-comprovante-base/`.
Essa área é evidência local de execução, não dependência do serviço.

## Preservação conferida por comparação local

Comparei com a baseline sem Git: `bid_integrity.py`, `bid_rules.py`, `wallet.py`,
`lot_room.py`, `lot_time.py`, `lots.py`, `main.py` e `config.py` permaneceram
byte a byte idênticos. As ASTs das funções que registram rotas de lance e
cancelamento também permaneceram idênticas. As únicas mudanças nesses dois
serviços são categorias de integridade e proteção do terminal persistido.
Não há nova rota, campo de phase ou payload WS. Os testes existentes de
integridade/bytes canônicos, AD-5 e protocolo seguem nos verifies completos.

O primeiro verify encontrou somente a enumeração antiga de tabelas em
`test_database.py`: **1 failed, 2163 passed, 1 warning in 117.32s**, exit 1.
Atualizei a lista exata com `lot_settlements` e `receipts`, sem remover a
comparação ou aceitar tabelas arbitrárias, e repeti o gate completo.

## Gates finais realmente executados

| Comando | Saída real | Exit |
| --- | --- | --- |
| `./verify.sh` (repetição final) | `2164 passed, 1 warning in 116.14s`; frontend `tests 175`, `pass 175`, `fail 0` | 0 |
| `VERIFY_E2E=1 ./verify.sh` | `2164 passed, 1 warning in 115.82s`; frontend 175/175; Playwright `222 passed (25.0s)`, `5 skipped` | 0 |

Ambos terminaram com `verify.sh: todas as etapas passaram.` Ruff (`All checks
passed!`), `96 files already formatted`, ESLint, TypeScript, Vite e Docker build
aprovados. Mantive os cinco skips de `real-stack.spec.ts`: opt-in por
`E2E_REAL_BASE_URL`, não executado nesta story. O smoke abaixo chama diretamente
o serviço; não alego teste manual artificial de navegador nem prova no Render.

## Smoke transacional local

Executei o harness local `smoke.py` da área runtime com o serviço real e PostgreSQL
dedicado `_test`, guardas de banco/ambiente e novas Sessions para as observações.
Exit **0**. Preparei usuários/carteiras sintéticos, dois lotes com reservas reais
e um vazio; expirei apenas os alvos antes do fechamento. Preservei o outro lote.

| Carteira | T antes | C antes | A antes | T depois | C depois | A depois |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Vencedor | 80000 | 32000 | 48000 | 68000 | 20000 | 48000 |
| Leiloeiro | 5000 | 0 | 5000 | 17000 | 0 | 17000 |

F=12000; soma T antes/depois=85000; reserva alheia=20000 preservada.
Resultados `settled_sold`/`settled_unsold` com transição confirmada; repetições
`already_settled`/false, mantendo IDs, registros, saldos e receipt originais.
Receipt por sold=1, por unsold=0. Readers recuperaram as mesmas cópias.
O banco de teste fica com os dados sintéticos do smoke para inspeção; a próxima
sessão pytest recria seu schema. Nenhum dado de dev/produção foi alterado.

## Arquivos criados/alterados

- `backend/app/lot_settlement.py` (novo: modelos/DTOs/comando/helper/readers).
- `backend/app/bids.py` (categorias e proteção do terminal).
- `backend/app/lot_cancellation.py` (proteção do terminal).
- `backend/migrations/versions/0007_lot_settlement.py` (nova migration).
- `backend/tests/settlement_support.py` (novo harness).
- `backend/tests/integration/test_lot_settlement.py` (novos PG financeiros/integridade/schema/falhas).
- `backend/tests/integration/test_lot_settlement_concurrency.py` (novos PG concorrência/leituras).
- `backend/tests/conftest.py` (limpeza explícita das novas FKs).
- `backend/tests/bid_support.py` (limpeza e invariante excluindo reservas já consumidas).
- `backend/tests/integration/test_database.py` (enumeração exata das novas tabelas).
- `README.md` (serviço interno, fórmula, limites e head local 0007).
- `docs/uso_de_ia.md` (autorização, execução e resultados).
- `_bmad-output/implementation-artifacts/4-3-fechamento-liquidação-idempotente-e-comprovante-base.md`.
- `_bmad-output/implementation-artifacts/sprint-status.yaml`.
- `_bmad-output/specs/spec-story-4-3-fechamento-liquidacao-idempotente-e-comprovante-base/SPEC.md`.
- Este `implementation-evidence.md` (novo).

Alterado fora da lista prevista: `frontend/test-results/.last-run.json`,
artefato regenerado pelo Playwright, sem mudança em código de frontend.
A checagem final somente de nomes não detectou arquivo de segredo alterado
(`.env*`, chaves/credenciais e padrões protegidos). Nenhum conteúdo de segredo
entra no diff local. Inventário final: 17 arquivos, incluindo o artefato do
Playwright fora da lista prevista; não houve outro arquivo fora do escopo.

## Estado para aceite

Build/validações concluídos. Story 4.3 e sprint em **review**, SPEC em
**in-review**, Epic 4 **in-progress**. Story 4.4 permanece **backlog**, sem
implementação iniciada. Não executei code review: não há veredito de revisão
independente nesta entrega. Aceite/review humanos ficam pendentes, sem `done`.
