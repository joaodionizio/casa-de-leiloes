# Evidência da correção isolada da AD-5 — 27/10/2026

## Decisão e escopo

Recebi decisão humana nova e vinculante: voltar à extensão cumulativa sobre o
fim vigente. Descartei a decisão intermediária de renovar a partir do instante
do lance. Implementei `new_ends_at = current_ends_at + 2 minutos` para lance válido
em `0 < remaining <= 2 minutos`, inclusive exatamente 2:00 (flag verdadeira).
`now >= ends_at` continua recusado, sem extensão ou reabertura.

Atualizei primeiro `docs/ARQUITETURA.md`, depois o apoio documental e somente
então código e testes. Registrei a decisão intermediária como história revogada
na AD-5. Nos artefatos históricos acrescentei nota datada, sem remover o texto
original. Na auditoria final detectei que o glob de Markdown também inseriu a
nota em três `.memlog.md` (companions de 3.2, 3.4 e 3.5). Desfiz somente a inserção
exata nesses três arquivos: o conteúdo original ficou restaurado; o timestamp
local foi tocado. Não mantive nenhuma nota nem mudança no histórico desses logs.
Na 4.2 não encontrei descrição concreta da
fórmula a alterar; mantive story/spec e arquitetura de conexão.

## Validação executada

- Testes direcionados de regras, serviço, rotas e concorrência PostgreSQL:
  primeira rodada 1 failed, 436 passed (expectativa antiga de horário ambíguo);
  corrigi a expectativa e obtive **437 passed, 1 warning in 20.00s**.
- Playwright direcionado: **2 passed (4.0s)**. O exemplo usa fim 12:01:10,
  lance 12:00:09 e fim confirmado 12:03:10: countdown **03:01 → 03:00**.
- Mutação temporária: troquei somente a base da soma por `eligible.now` e rodei
  testes de cumulatividade pura, base do término e persistência de três lances.
  Resultado: **3 failed, 1 warning in 0.26s**, exit 1 esperado. Restaurei o
  código cumulativo integralmente em `finally` antes de seguir.
- Acrescentei depois a concorrência fora da nova janela ao teste parametrizado
  e adaptei a expectativa antiga de `placed_at + 2 min` no teste de transporte WS.
- Rodada direcionada final, incluindo WebSocket e os dois casos de concorrência:
  **470 passed, 1 warning in 26.90s** (exit 0).
- `./verify.sh`: primeira rodada **1 failed, 2081 passed in 102.65s**. Carregou a
  expectativa WS antiga antes da edição. Rodada final **exit 0**:
  **2083 passed, 1 warning in 105.06s**, frontend **175 tests / 175 pass / 0 fail**;
  Ruff, format (91 arquivos), ESLint, tsc, Vite e Docker build aprovados.
  Saída final: `verify.sh: todas as etapas passaram.`
- `VERIFY_E2E=1 ./verify.sh`: **exit 0**, **2083 passed, 1 warning in 103.10s**;
  frontend **175 tests / 175 pass / 0 fail**; Playwright **222 passed (24.3s),
  5 skipped**. Ruff, format, ESLint, tsc, Vite e Docker build aprovados.
  Saída final: `verify.sh: todas as etapas passaram.`
  Mantive os skips existentes; não os converti em alegação de cobertura.

O primeiro comando uv encontrou cache fora da área gravável; usei
`UV_CACHE_DIR=/private/tmp/casa-uv-cache`. O sandbox bloqueou o acesso inicial ao
PostgreSQL local; repeti os testes com a permissão de execução concedida pelo
ambiente. Não alterei verify.sh para contornar falhas.

## Concorrência e integridade

Usei PostgreSQL real e a sobreposição existente: A segura a trava do lote,
B aguarda `SELECT FOR UPDATE`, a observação de bloqueio é real e só então A
confirma. No caso cumulativo, espero o término original passar com pg_sleep no
observador enquanto B está bloqueado; B lê o clock_timestamp autoritativo após
adquirir a trava e opera sobre o fim confirmado por A. Não simulo ordem de locks
ou relógio nesse teste. No caso imediato B fica fora da nova janela e preserva
a extensão de A. O serviço é o mesmo em ambos.

Comparei os módulos com cópias anteriores à primeira alteração, sem Git:
`bids.py`, `bid_integrity.py`, `wallet.py`, `lot_time.py`, `lot_room.py`,
`LotPage.tsx` e `lotRoomSocket.ts` permanecem idênticos. A única mudança de
produção no backend é na regra pura. Assim, preservo canonical bid v1, cadeia
SHA-256, âncora HMAC, final_hash, pseudônimo, carteira, compromisso financeiro e
ordem de locks. `ends_at` permanece fora do lance canônico. Não há migration,
modificação de schema ou dados históricos de negócio; as suítes usam o banco
dedicado de testes e suas migrations existentes. Não reparei lotes legados.

Não alterei heartbeat, pong, backoff, reconexão, gerações, shouldApplyRoom,
sameRoomState ou stale público/privado. Frontend aplica somente ends_at recebido;
o cálculo da extensão aparece apenas no backend e na simulação E2E da API.

## Arquivos alterados

- `CLAUDE.md`
- `README.md`
- `_bmad-output/implementation-artifacts/3-2-regras-de-aceitação-do-lance-com-hora-injetada.md`
- `_bmad-output/implementation-artifacts/3-4-lance-transacional-com-travas-e-anti-sniping.md`
- `_bmad-output/implementation-artifacts/3-5-dar-lance-pela-sala-do-lote.md`
- `_bmad-output/implementation-artifacts/4-1-sala-ao-vivo-por-websocket-snapshot-e-atualizações.md`
- `_bmad-output/implementation-artifacts/code-review-epic-3.md`
- `_bmad-output/planning-artifacts/DESIGN.md`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/specs/spec-story-3-2-regras-aceitacao-lance/SPEC.md`
- `_bmad-output/specs/spec-story-3-2-regras-aceitacao-lance/decisions.md`
- `_bmad-output/specs/spec-story-3-2-regras-aceitacao-lance/domain-contract.md`
- `_bmad-output/specs/spec-story-3-2-regras-aceitacao-lance/implementation-map.md`
- `_bmad-output/specs/spec-story-3-2-regras-aceitacao-lance/test-plan.md`
- `_bmad-output/specs/spec-story-3-4-lance-transacional/SPEC.md`
- `_bmad-output/specs/spec-story-3-4-lance-transacional/current-state.md`
- `_bmad-output/specs/spec-story-3-4-lance-transacional/decisions.md`
- `_bmad-output/specs/spec-story-3-4-lance-transacional/implementation-map.md`
- `_bmad-output/specs/spec-story-3-4-lance-transacional/test-plan.md`
- `_bmad-output/specs/spec-story-3-4-lance-transacional/transaction-contract.md`
- `_bmad-output/specs/spec-story-3-5-dar-lance-pela-sala-do-lote/SPEC.md`
- `_bmad-output/specs/spec-story-3-5-dar-lance-pela-sala-do-lote/implementation-map.md`
- `_bmad-output/specs/spec-story-3-5-dar-lance-pela-sala-do-lote/test-plan.md`
- `backend/app/bid_rules.py`
- `backend/tests/integration/test_bid_concurrency.py`
- `backend/tests/integration/test_bid_routes.py`
- `backend/tests/integration/test_bid_service.py`
- `backend/tests/integration/test_lot_room_ws.py`
- `backend/tests/test_bid_rules.py`
- `docs/ARQUITETURA.md`
- `docs/DEPLOY-RECUPERACAO-EPICS-2-3.md`
- `docs/uso_de_ia.md`
- `frontend/e2e/lot-room.spec.ts`
- `frontend/e2e/support/mockApi.ts`
- `frontend/src/bidFeedback.test.ts`
- `frontend/src/bidFeedback.ts`

Arquivos novos: esta nota e
`_bmad-output/implementation-artifacts/spec-correcao-anti-sniping-cumulativo.md`.
Baseline/diff locais em `_bmad/.runtime/bmad-build/spec-correcao-anti-sniping-cumulativo/`.
Nenhum Git/commit; nenhuma parte da Story 4.3 foi iniciada. Review independente
ainda será feito pelo fluxo do dono antes de commit.

## Revisão interna

Revisor separado inspecionou o diff e os ajustes finais em leitura, sem Git,
testes ou edições. Nenhum defeito funcional confirmado. Sugestão LOW de cobrir
B imediatamente fora da nova janela incorporada ao teste concorrente e
reconferida sem novos achados. Não substitui o review independente do dono.

## Auditoria de arquivos fora da lista prevista

- `frontend/test-results/.last-run.json`: artefato gerado pelo Playwright;
  não é alteração de implementação.
- `.memlog.md` dos companions 3.2, 3.4 e 3.5: inserção documental acidental
  detectada e desfeita pela remoção do trecho exato; nenhum conteúdo histórico
  alterado no resultado final. Informo os nomes por terem timestamp recente.
- Checagem somente de nomes: nenhum arquivo de segredo alterado detectado.

Logs reais preservados na área local `_bmad/.runtime/bmad-build/spec-correcao-anti-sniping-cumulativo/logs/` (sem Git).

## Correção do LOW AS-01 do review independente — 27/10/2026

Corrigi somente a fixture e a expectativa do teste de precedência WS/REST em
`frontend/e2e/lot-room-ws.spec.ts`. O término anterior é
`14:31:01.123456`; substituí o término simulado `14:33:00.123456` (119 segundos
de extensão) por `14:33:01.123456`, exatamente o término vigente + 2 minutos.
Com o `as_of` do frame em `14:31:00.123456`, a nova âncora visual corresponde a
121 segundos: ajustei o countdown esperado de `02:00` para `02:01`.
Preservei a retenção/liberação da resposta REST e os asserts de precedência WS.
Não alterei código de produção, backend, máquina de conexão ou Story 4.3.

Validação real após a correção:

- `cd frontend && npm run test:e2e -- lot-room-ws.spec.ts`: **exit 0**, **33 passed
  (5.9s)**, incluindo o cenário corrigido.
- `UV_CACHE_DIR=/private/tmp/casa-uv-cache ./verify.sh`: **exit 0**;
  todas as etapas passaram, incluindo pytest, lint/formatação, tipos, testes
  frontend, build Vite e build Docker.
- `UV_CACHE_DIR=/private/tmp/casa-uv-cache VERIFY_E2E=1 ./verify.sh`: **exit 0**;
  **2083 passed, 1 warning in 102.90s**, frontend **175 tests / 175 pass**,
  Playwright **222 passed (24.7s), 5 skipped**. Todas as etapas passaram.
  Log desta rodada em `/private/tmp/casa-as01-verify-e2e.log`.

As primeiras tentativas no sandbox falharam por infraestrutura: o E2E não pôde
abrir `127.0.0.1:4173` (EPERM) e o verify não pôde acessar o Docker. Reexecutei
com a permissão concedida pelo ambiente; os resultados aprovados acima são
dessas execuções. Não executei Git nem abri arquivos `.env*`.
