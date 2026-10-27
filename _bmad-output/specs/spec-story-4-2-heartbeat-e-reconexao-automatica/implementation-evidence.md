# Implementação — Story 4.2

27/10/2026. Evidência de implementação/testes focados; não é code review, deploy ou smoke Render. A autorização atual de build supera as notas históricas de sessão somente documental dos companions.

## Mudanças

- `backend/app/lot_room.py`: ping/pong JSON exatos, IDs seguros/sequenciais, silêncio monotônico de 60 s, um sender/fila 8 para snapshot/eventos/pong e deadline individual de 10 s em send/close (inclusive recusa pré-accept). Cleanup cobre cancelamento antes/depois do subscribe; leitura SQL já iniciada termina com Session própria, mantendo a vaga no limiter 4 até concluir, sem registrar subscriber tardio.
- `frontend/src/lotConnection.ts`: máquina sem dependência nova, relógio/scheduler/socket/RNG injetáveis, A=30 s, H=20 s entre envios, P=10 s, backoff exponencial 1–30 s/equal jitter e reset só snapshot+pong. Uma geração autoritativa e tokens de timers; offline suspende e online abre uma vez sem aguardar CLOSED. Visible recalcula uma ação, sem replay de ticks. Terminal/disposed invalidam tudo.
- `LotPage.tsx`/`LotBidPanel.tsx`: integração preserva arbitragem pública e coordenação privada; snapshot comprova conexão mesmo quando dados mais antigos são descartados. Diagnóstico REST é coalescido e único por episódio, 404 genérico terminal; snapshot invalida diagnóstico antigo. Dados, campo e foco permanecem durante recuperação. Refresh manual não declara WS conectado. `shouldApplyRoom`/`sameRoomState` permanecem intactos.
- README descreve parâmetros e limitações aprovadas. Sem mudanças de domínio financeiro, migrações, stack ou 4.3.

## Execuções finais focadas

| Comando | Resultado |
| --- | --- |
| `cd frontend && npm test` | exit 0; 175 testes (12 novos da máquina) |
| `cd frontend && npm run lint` | exit 0 |
| `cd frontend && npm run typecheck` | exit 0 |
| `cd backend && uv run --no-env-file ruff check app/lot_room.py tests/test_lot_room.py tests/integration/test_lot_room_ws.py` | exit 0 |
| `cd backend && uv run --no-env-file ruff format app/lot_room.py tests/test_lot_room.py tests/integration/test_lot_room_ws.py` | exit 0; arquivos já formatados |
| `cd backend && uv run --no-env-file pytest tests/test_lot_room.py tests/integration/test_lot_room_ws.py -q` | exit 0; 70 testes em PostgreSQL real `_test`; warning preexistente de depreciação Starlette/httpx |
| `cd frontend && npx playwright test e2e/lot-room-ws.spec.ts --workers=2` | exit 0; 22 testes Chromium com WS/REST simulados; build Vite incluído pelo webServer |

Backend usou somente a configuração pública local autorizada de `compose.yaml`, `APP_ORIGIN=http://localhost:5173` e cache UV em `/tmp`; execução elevada foi necessária para loopback. Nenhum Git ou arquivo `.env*`/credencial foi lido. Primeiras tentativas sem banco/loopback foram recusadas pela guarda/sandbox; nenhuma guarda foi removida. Falhas intermediárias de fixtures/timer de teste foram corrigidas e os gates acima repetidos com sucesso.

## Rastreabilidade dos cenários aprovados

Nomes abaixo são os testes efetivamente executados, não testes futuros. `F` refere-se principalmente a `frontend/src/lotConnection.test.ts`; `R` aos três testes existentes de `lotRoomSocket.test.ts`; `E` a `frontend/e2e/lot-room-ws.spec.ts`; `B` a `backend/tests/test_lot_room.py`; `PG` a `backend/tests/integration/test_lot_room_ws.py`.

| Cenário | Evidência executada |
| --- | --- |
| F01 | F `opening requires its own valid snapshot and one total 30s deadline`; E `opening timeout and navigation...` |
| F02 | F `opening requires...`: pong/bid/terminal/outro lote/inválido antes de snapshot |
| F03 | F `pong at the exact deadline fails once...`; F `first ping is immediate...` |
| F04 | F `pong at the exact deadline...` error+close duplicados; `constructor exception...`; `repeated snapshot-only recoveries...` send exception |
| F05 | F `equal jitter saturates without overflow`; `error without close retries...` |
| F06 | F `error without close retries...`; `repeated snapshot-only recoveries...` preserva k offline e reset aprovado |
| F07 | F `offline mounts no socket and flapping online deduplicates without waiting for CLOSED`; callbacks antigos após novo snapshot |
| F08 | Mesmo teste F07; E `offline closes current generation...` |
| F09 | F `cancelled retry and disposed callbacks stay inert, including remount`; E `opening timeout and navigation...` |
| F10 | F `cancelled retry...` cria nova instância após stop; E `WS during pending POST and remount...` e `opening timeout and navigation...`. Cobre efeitos do remount; não afirma ter executado o ciclo duplo de efeitos do React em build de desenvolvimento, pois Playwright usa produção. |
| F11 | E `manual room newer than reconnect snapshot...`, `old REST cannot replace WS...`, `201 N after WS N+1...` |
| F12 | R `count orders bids, timestamp only breaks ties, terminal and lot identity prevail`; R `validated discriminated payload...`; E regressões de GET/201 |
| F13 | R `same public state ignores only as_of...`; E `snapshots replace state, preserve input/focus, coalesce duplicates...` |
| F14 | F `terminal delivery stops all activity...`; F `offline mounts no socket...` terminal aposentado; E `lot_cancelled is terminal...` e diagnóstico 404 |
| F15 | F `constructor exception gets one recovery timer and one diagnostic per episode`; E `one diagnostic per recovery episode...`; `snapshot invalidates an old coalesced diagnostic 404...` |
| F16 | F `visible reevaluates one expired deadline or send, never catches up missed ticks`: H, P e retry com timers cancelados executados adversarialmente |
| F17 | F `all old generation messages including the current ping id are powerless...`; `terminal delivery stops all activity...` |
| F18 | F `cancelled retry and disposed callbacks stay inert...` executa timer cancelado após online |
| F19 | F `repeated snapshot-only recoveries grow backoff...`; `error without close retries...` |
| F20 | F `first ping is immediate; pong does not move the next send from t=20s` |
| B01 | B `test_ping_pong_snapshot_first_without_database_work`; PG `test_real_commits_inverted_signals_and_initial_read_barrier` |
| B02 | B `test_only_exact_sequential_safe_positive_ping_is_accepted` (11 payloads); `test_binary_and_internal_failure_are_generic`; `test_public_snapshot_origin_and_commands` |
| B03 | B `test_silence_and_late_ping_expire_at_exact_deadline` prova watchdog e rejeição de ping tardio no limite S, sem sleeps. Cleanup de handler/isolamento de outro assinante é exercitado separadamente pelos testes B06/fila. |
| B04 | B `test_send_and_close_are_individually_bounded`; `test_pong_queue_full_stops_only_its_subscriber`; PG `test_full_queue_evicts_only_the_slow_client_through_real_posts` preserva POST/cliente saudável |
| B05 | B `test_ping_pong_snapshot_first_without_database_work`; PG `test_public_real_snapshot_is_one_pure_query_and_closes_session` conta statements SQL e pool durante três ciclos reais ping/pong |
| B06 | B `test_cancelling_the_handler_cleans_up_and_propagates`, `test_sender_failure_closes_generic_1011_and_cleans_manager`, `test_abandoned_subscribe_discards_late_worker_result`, `test_completed_subscribe_cancelled_before_handler_claims_result`, `test_abandoned_read_retains_limiter_lease_until_worker_finishes`; PG05 abaixo. Cancelamento ASGI é exercitado; restart de processo/proxy é smoke separado. |
| B07 | B `test_bad_origin_rejected_before_read`, `test_repeated_origin_header_is_refused_while_a_single_one_connects`, `test_origin_policy_alone_decides_for_an_existing_lot`, públicos sem cookie/inválido; PG snapshots verificam lista estrita de campos e ausência de dados privados |
| PG01 | Novo `test_reconnect_after_committed_write_loses_transport_before_publication`: barreira após commit confirmado em Session independente, transporte sai antes de liberar publicação, um POST e snapshot de recuperação |
| PG02 | Novo `test_reconnect_recovers_missed_window_and_total_without_replay`: desconecta, 51 POSTs alternados entre dois licitantes, snapshot count=51 e janela=50; próximo frame solicitado é pong, sem replay |
| PG03 | Novo `test_disconnected_cancellation_recovers_only_generic_public_404`: desconecta visitante, cancela, limpa cookie, WS recusado e GET público404 sem cancelled_at |
| PG04 | `test_commit_barrier_two_clients_isolation_and_ant_sniping`, `test_real_commits_inverted_signals_and_initial_read_barrier`, `test_failure_or_rollback_never_signals` e barreiras de cancelamento da 4.1, preservados e executados |
| PG05 | Novo `test_abandon_during_real_sql_releases_session_and_registration`: SQL real retido em before_cursor_execute com conexão checkedout=1; cancela handler, registro desaparece sem esperar SQL; libera barreira e verifica pool=0/nenhum subscriber |
| E01 | `open awaits snapshot, lost pong reconnects automatically...`; `opening timeout and navigation...` |
| E02 | `snapshots replace state, preserve input/focus...`; `failed manual refresh keeps the last valid state locally...` |
| E03 | `old REST cannot replace WS...`; `201 N after WS N+1...`; novo `manual room newer than reconnect snapshot...` |
| E04 | `offline closes current generation...`; `open awaits snapshot, lost pong reconnects automatically...` |
| E05 | `opening timeout and navigation invalidate pending retries across lots and back remount`; unitários F17/F18 disparam callbacks de socket/timer aposentado explicitamente |
| E06 | `lot_cancelled is terminal and moves focus...`; `one diagnostic per recovery episode; 503 retries WS while confirmed 404 is terminal` |
| E07 | `snapshots replace state...coalesce duplicates...`; `WS invalidates private position while mine is delayed or fails...`; os três testes de resposta privada substituída/ambígua |
| E08 | `recovery status and keyboard refresh remain accessible at 320px/375px/1280px`: status textual, teclado, foco e overflow; E06 verifica foco h1 no cancelamento |

## Limites preservados

Testes Playwright acima simulam WS/REST; PostgreSQL/ASGI não prova TCP/proxy/wss/Render. O teste PG01 injeta perda entre commit e sinal, sem reiniciar o processo. Não há medição de capacidade, teto novo de conexões ou deadline da publicação pós-commit; continuam adiamentos QH-11/12. Nenhum code review foi executado nesta sessão por instrução humana.


## Gates finais executados pelo coordenador

Todos os comandos abaixo terminaram exit 0 na execução final, em 27/10/2026.
Usei os valores públicos locais de Compose para DATABASE_URL/TEST_DATABASE_URL,
APP_ORIGIN=http://localhost:5173 e UV_CACHE_DIR=/tmp/atrio-story42-uv-cache.

| Comando | Saída real final |
| --- | --- |
| `./verify.sh` | `2079 passed, 1 warning in 100.30s`; `ℹ tests 175`, `ℹ pass 175`, `ℹ fail 0`; Ruff/format (91 arquivos), ESLint, tsc, Vite e Docker passaram |
| `npx playwright test e2e/lot-room.spec.ts e2e/lot-room-ws.spec.ts --workers=2` | `66 passed (15.2s)`; ESLint e tsc também passaram após os terminais REST |
| `VERIFY_E2E=1 ./verify.sh` (final) | `2079 passed, 1 warning in 96.24s`; `ℹ tests 175`, `ℹ pass 175`, `ℹ fail 0`; `213 passed (23.9s)`, `5 skipped`; Ruff/format, ESLint, tsc, Vite e Docker passaram; `verify.sh: todas as etapas passaram.` |
| `E2E_REAL_BASE_URL=http://127.0.0.1:15173 npx playwright test e2e/real-stack.spec.ts --workers=1` | `5 passed (3.0s)`; API/PostgreSQL reais, via Vite de desenvolvimento; não é FastAPI servindo o build nem Render |
| `node /tmp/atrio-story42-smoke/smoke.mjs` | exit 0; nove verificações reais descritas abaixo; banco temporário removido ao finalizar |

Os 5 skipped do verify são o opt-in de pilha real, que foi executado separadamente.
O warning backend é o StarletteDeprecationWarning/httpx preexistente. Logs integrais
locais: `/tmp/atrio-story42-verify.log`, `/tmp/atrio-story42-verify-e2e-final.log`,
`/tmp/atrio-story42-real-stack.log` e `/tmp/atrio-story42-smoke/run.log`.

A primeira execução E2E completa falhou só em duas expectativas exatas do título 404
(brand/vitrine): esperavam o título antigo, mas o contrato aprovado exige o texto
genérico. Sincronizei essas duas expectativas e a correspondente de real-stack,
sem remover asserções. A repetição completa passou. Na rodada focada, corrigi a
fixture REST nova para HTTP 422/envelope real de lot_cancelled e isolei a suíte de
rodadas REST com navigator.onLine=false; suas contagens exatas/foco/POST único
permanecem. A suíte WS continua online e cobre as interações entre os transportes.
Os dois testes de quantidade de tentativas WS agora usam relógio pausado e contagens
exatas, incluindo avanço explícito para a segunda tentativa, em vez de desigualdade.

## Complemento de aceite REST

Concluí T17/T18 também no resultado do POST pendente: `lot_cancelled` confirma
cancelamento conhecido, fecha transporte, aborta leituras e foca h1; POST 404 encerra
como indisponível/não encontrado. O mesmo helper é usado pelo evento WS; terminal
não vira disposed. Testes E adicionais executados e aprovados no verify final:
`POST lot_cancelled during reconnect confirms terminal and prevents late recovery`,
`POST not_found during reconnect confirms terminal and prevents late recovery` e
`recusa lot_cancelled confirma terminal conhecido, com foco e sem releitura`.
Cobrindo E06/F14, mantêm um POST, zero releitura desnecessária e nenhuma reconexão
após online repetido/120 s de relógio controlado.

## Smoke local real via proxy Vite

Usei backend próprio na porta 18000, Vite na 15173 e um banco novo dedicado
`casa_42_smoke_1793126879551_test`, com migrations/seed e configurações fictícias
somente nos processos. O banco foi removido no finally; não encerrei os serviços
preexistentes em 8000/5173. Backend sem dotenv e Vite com envDir=false. A indisponibilidade
do navegador integrado exigiu Chromium/Playwright local. Abortei somente bytes de
imagem nos dois contextos; REST, handshake, frames WS, commits e PostgreSQL foram reais.

1. A/B receberam `room_snapshot` como primeiro frame da sala e pong com ID do ping.
   StrictMode de desenvolvimento construiu dois sockets por aba no setup/cleanup/setup;
   o instrumento registrou somente um handler autoritativo por aba. O observador
   filtra `/ws/lots/`: a tentativa inicial do harness misturava o WS de HMR do Vite,
   foi corrigida sem alterar o produto.
2. A offline: nenhuma nova tentativa (contador 2 permaneceu2); GET manual realmente
   falhou pela rede, exibindo aviso local sem apagar preço/histórico. B confirmou
   um POST 201 de 10000 centavos e recebeu count 1; A conservou count 0.
3. A online mais dois eventos online repetidos: contador 2→3, uma tentativa;
   snapshot recuperou count 1 sem refresh e sem POST de A (`postsA=0`).
4. Invoquei callbacks capturados do socket aposentado: snapshot sintético count 999,
   pong ID 1, open, error e close. A nova geração manteve preço/status e contador 3.
   Essa injeção é adversarial no browser com transporte real ao redor, não uma
   alegação de frame TCP enviado pelo servidor no socket já fechado.
5. Encerrei o processo backend do smoke. Ambas as salas ficaram em recuperação com
   count 1/preço/histórico preservados.
6. Reiniciei o backend mantendo o banco: A/B reconectaram por novos snapshots;
   contadores A=4/B=3 nesta execução, sem reenvio de comando.
7. Outro licitante confirmou POST 201 de 11000 centavos: ambas as abas receberam
   count 2 e convergiram à leitura pública PostgreSQL (count 2/preço 11000).
8. Abri terceiro cliente real sem ping de aplicação. Recebeu snapshot e o servidor
   fechou com 1011 após S=60 s; durante a espera, A/B permaneceram conectadas e A
   recebeu novos pongs. Complementa B03 com expulsão real e saudável ativo.
9. Viewport 320 px sem overflow horizontal. Fechei browser e processos próprios e
   removi o banco. Nenhum socket/processo de smoke foi deixado nas portas usadas.

Suspensão/retorno visible e bordas A/H/P/backoff foram comprovados com relógio
controlado, não com suspensão física do sistema operacional. F10 também ganhou
prova de StrictMode real de desenvolvimento neste smoke. Sem prova de wss/Render,
medição de capacidade, teto de conexões ou deadline pós-commit D-A. Não introduzi
migrações, Redis/broker/outbox, workers adicionais, replay ou parte da 4.3.
Não há divergência funcional conhecida em relação à spec; um scheduler/token único
coordena o próximo deadline de transporte, respeitando os limites de timers aprovados.

## Arquivos criados/alterados e alcance

- Backend: `backend/app/lot_room.py`, `backend/tests/test_lot_room.py`,
  `backend/tests/integration/test_lot_room_ws.py`.
- Frontend: novos `frontend/src/lotConnection.ts` e `frontend/src/lotConnection.test.ts`;
  alterados `LotPage.tsx`, `LotBidPanel.tsx`, `lotRoomSocket.ts` em `frontend/src/`.
- E2E: `frontend/e2e/lot-room-ws.spec.ts`, `frontend/e2e/lot-room.spec.ts`.
- Alterados fora da lista prevista: `frontend/e2e/brand.spec.ts`,
  `frontend/e2e/vitrine.spec.ts`, `frontend/e2e/real-stack.spec.ts` — somente expectativa
  exata do título 404 aprovado; nenhum teste excluído ou critério reduzido.
- Documentos: `README.md`, `docs/uso_de_ia.md`, esta evidência, `SPEC.md`, story 4.2
  e `_bmad-output/implementation-artifacts/sprint-status.yaml`.
- Artefato gerado fora da lista prevista: `frontend/test-results/.last-run.json`.
  Cópias locais de partida ficam em `_bmad/.runtime/bmad-build/SPEC/`, fora do produto.
- Checagem separada de nomes de arquivos de segredo alterados: nenhum encontrado;
  nenhum conteúdo de segredo foi lido ou comparado.

Comparei `shouldApplyRoom` e `sameRoomState` com as cópias iniciais: idênticas byte
a byte. Nenhum arquivo financeiro/auth/migration/dependência alterado. Epic 4 segue
in-progress e 4.3 backlog. Implementação/spec concluída; story em review, pronta para
meu teste manual, sem code review nesta sessão e sem aprovação humana final alegada.
